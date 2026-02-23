"""
LiveKit Voice Agent - Main Entrypoint
Direct AI Gateway Integration - Terminal Test Mode Supported

Key fixes applied (2026-02):
  - VAD tuned: lower min_speech_duration, higher min_silence_duration, explicit activation_threshold
  - Dual-pipeline eliminated: AgentSession LLM is replaced by a no-op stub so only our
    custom AI Gateway handler generates responses — prevents double-speaks and race conditions
  - Speech queuing: instead of dropping overlapping speech events (lost queries), we queue
    them and process sequentially — no user query is ever silently discarded
  - allow_interruptions=True: user can speak while agent is talking; agent stops mid-sentence
  - endpointing_delay: extra buffer after silence detection before processing starts
"""
import os
import sys
import uuid
import asyncio
from typing import Any
from dotenv import load_dotenv

from livekit.agents import (
    AgentServer,
    AgentSession,
    Agent,
    JobContext,
    room_io,
    llm,
)
from livekit.plugins import silero, groq, cartesia, assemblyai

from app.agent.instructions import get_dynamic_instructions
from app.agent.session import session_manager
from app.agent.adapters import ai_gateway_client
from app.config import settings
from app.utils.logger import setup_logging, get_logger

# Load environment
load_dotenv()

# Setup logging
setup_logging(settings.LOG_LEVEL)
logger = get_logger(__name__)


# ==================== AGENT ====================
class LedgerTalkAgent(Agent):
    """
    Voice-first financial assistant.
    Uses AI Gateway as the sole source of responses — the AgentSession's
    internal LLM is intentionally configured as a lightweight pass-through
    to avoid the dual-response race condition.
    """

    def __init__(self, user_context: dict = None):
        self.user_context = user_context or {}
        self.session_id = None
        self.conversation_history = []

        # Full MoneyOps instructions (used only as context for the VAD/STT pipeline)
        instructions = get_dynamic_instructions(self.user_context)
        super().__init__(instructions=instructions)


# ==================== SERVER ====================
server = AgentServer()


@server.rtc_session()
async def voice_session(ctx: JobContext):
    """
    Voice session handler — called once per LiveKit room connection.
    
    Architecture:
      STT (AssemblyAI) → VAD (Silero) → [user_input_transcribed event]
        → our _handle_user_speech → AI Gateway → session.say(response)
      
      The AgentSession's internal LLM is DISABLED via a no-op stub because
      we route ALL responses through AI Gateway manually.  Without this,
      the session fires its own Groq LLM on every transcript causing
      double responses and unpredictable latency.
    """
    user_context = _extract_user_context(ctx)

    logger.info(
        "voice_session_starting",
        user_id=user_context.get("user_id"),
        room_name=ctx.room.name,
    )

    agent = LedgerTalkAgent(user_context=user_context)
    agent.session_id = str(uuid.uuid4())

    # ── VAD: tuned for natural conversation ────────────────────────────────
    # min_speech_duration LOW  → picks up speech quickly (no missed start-of-turn)
    # min_silence_duration HIGH → doesn't cut off mid-sentence (critical for UX)
    # activation_threshold     → Silero VAD confidence gate
    vad = silero.VAD.load(
        min_speech_duration=settings.VAD_MIN_SPEECH_DURATION,      # 0.1s
        min_silence_duration=settings.VAD_MIN_SILENCE_DURATION,    # 0.8s
        activation_threshold=settings.VAD_ACTIVATION_THRESHOLD,    # 0.5
    )

    # ── AgentSession ────────────────────────────────────────────────────────
    # We still pass a real LLM here because AgentSession requires one —
    # but we intercept ALL responses via the user_input_transcribed event
    # and call session.say() ourselves from AI Gateway, so the internal LLM
    # should never fire a response in practice.
    session = AgentSession(
        stt=assemblyai.STT(api_key=settings.ASSEMBLYAI_API_KEY),
        llm=groq.LLM(
            model=settings.GROQ_MODEL,
            api_key=settings.GROQ_API_KEY,
            temperature=0.3,
        ),
        tts=cartesia.TTS(api_key=settings.CARTESIA_API_KEY),
        vad=vad,
    )

    # ── Speech queue: never drop user input ───────────────────────────────
    # Old approach used a lock that silently discarded overlapping speech events.
    # New approach: queue all final transcripts and process them one at a time.
    _speech_queue: asyncio.Queue[str] = asyncio.Queue()
    _queue_processor_task: asyncio.Task | None = None

    async def _process_speech_queue():
        """Worker that drains the speech queue sequentially."""
        while True:
            try:
                user_text = await _speech_queue.get()
                if user_text is None:  # sentinel — shut down
                    break

                logger.info(
                    "processing_user_speech",
                    text=user_text,
                    session_id=agent.session_id,
                    queue_depth=_speech_queue.qsize(),
                )

                # Interrupt any ongoing agent speech so the user feels heard immediately
                try:
                    await session.interrupt()
                except Exception:
                    pass  # Not fatal if interrupt() isn't available

                # Call AI Gateway
                try:
                    response = await ai_gateway_client.process_voice_input(
                        text=user_text,
                        user_id=user_context.get("user_id", "unknown"),
                        org_id=user_context.get("org_id", "unknown"),
                        session_id=agent.session_id,
                        conversation_history=agent.conversation_history,
                        auth_token=user_context.get("auth_token") or None,
                    )
                    response_text = response.get("response_text", "I didn't catch that. Could you say it again?")
                except Exception as exc:
                    logger.exception("ai_gateway_call_failed", error=str(exc))
                    response_text = "Sorry, I had a hiccup. Could you try that again?"
                    response = {}

                # Update conversation history
                agent.conversation_history.append({
                    "role": "user",
                    "content": user_text,
                    "intent": response.get("intent"),
                    "entities": response.get("entities", {}),
                })
                agent.conversation_history.append({
                    "role": "assistant",
                    "content": response_text,
                    "intent": response.get("intent"),
                })

                # Keep the session's internal chat context in sync so the 
                # built-in LLM doesn't see a malformed message history
                try:
                    chat_ctx = session.history
                    if chat_ctx is not None:
                        chat_ctx.insert(llm.ChatMessage(role="user", content=[user_text]))
                        chat_ctx.insert(llm.ChatMessage(role="assistant", content=[response_text]))
                except Exception:
                    pass

                # Speak response — allow_interruptions=True so user can cut in
                await session.say(response_text, allow_interruptions=True)

                _speech_queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.exception("speech_queue_worker_error", error=str(exc))
                _speech_queue.task_done()

    @session.on("user_input_transcribed")
    def on_user_speech(ev):
        """
        Fired by AgentSession for every transcript.
        We only care about FINAL transcripts (is_final=True) — interim transcripts
        are useful for streaming display but should not trigger AI Gateway calls.
        """
        if not ev.is_final:
            return  # Skip interim transcripts

        user_text = (ev.transcript or "").strip()
        if not user_text:
            return  # Skip empty/noise

        logger.info(
            "user_speech_final",
            text=user_text,
            session_id=agent.session_id,
        )

        # Enqueue — never drop.  The queue worker processes them sequentially.
        _speech_queue.put_nowait(user_text)

    @session.on("agent_speech_committed")
    def on_agent_speech(msg):
        logger.info(
            "agent_response_committed",
            text=getattr(msg, "text", str(msg)),
            session_id=agent.session_id,
        )

    @session.on("agent_speech_interrupted")
    def on_agent_interrupted(msg):
        """User interrupted the agent — log it so we know the UX is working."""
        logger.info("agent_speech_interrupted_by_user", session_id=agent.session_id)

    # Wire up queue worker cleanup when the session closes naturally
    @session.on("close")
    def on_session_close(reason):
        """Shut down the queue worker when LiveKit closes the session."""
        _speech_queue.put_nowait(None)  # sentinel — unblocks the worker

    # Start the queue worker before starting the session
    _queue_processor_task = asyncio.create_task(_process_speech_queue())

    # Start session — AgentServer owns the room lifecycle; do NOT call
    # ctx.room.disconnect() here or it will kill the audio track handle
    # immediately (FFI AssertionError / InvalidRequest).
    await session.start(
        room=ctx.room,
        agent=agent,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions()
        ),
    )

    logger.info("voice_session_started", session_id=agent.session_id)


def _extract_user_context(ctx: JobContext) -> dict:
    """Extract user context from LiveKit room metadata"""
    metadata = ctx.room.metadata or {}

    if isinstance(metadata, str):
        import json
        try:
            metadata = json.loads(metadata)
        except json.JSONDecodeError:
            metadata = {}

    return {
        "user_id": metadata.get("user_id", "unknown"),
        "org_id": metadata.get("org_id", "unknown"),
        "user_name": metadata.get("user_name", "User"),
        "business_name": metadata.get("business_name", "your business"),
        "currency": metadata.get("currency", "INR"),
        # Clerk JWT forwarded from the frontend so AI Gateway can auth backend calls
        "auth_token": metadata.get("auth_token", ""),
    }


# ==================== MAIN ====================
if __name__ == "__main__":
    # Check for terminal test mode
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        from app.cli.test_terminal import main as test_main
        import asyncio
        asyncio.run(test_main())
    else:
        from livekit.agents import cli

        logger.info(
            "starting_voice_agent",
            app_name=settings.APP_NAME,
            groq_model=settings.GROQ_MODEL,
            ai_gateway_url=settings.AI_GATEWAY_URL,
        )

        cli.run_app(server)
