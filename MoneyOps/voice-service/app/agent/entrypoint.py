"""
LiveKit Voice Agent - Main Entrypoint
Direct AI Gateway Integration - Terminal Test Mode Supported
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
    Voice-first financial assistant
    Direct AI Gateway integration - routes user speech directly to AI Gateway
    """

    def __init__(self, user_context: dict = None):
        self.user_context = user_context or {}
        self.session_id = None
        self.conversation_history = []

        # Use full MoneyOps instructions with user context
        instructions = get_dynamic_instructions(self.user_context)

        super().__init__(instructions=instructions)

    async def on_function_call(self, function_name: str, arguments: dict, call_context: Any) -> str:
        """
        Fallback: Handle function calls from LLM (if LLM tries to use tools)
        Routes to AI Gateway for processing
        """
        logger.info(
            "function_called",
            function=function_name,
            args=arguments,
        )

        if function_name == "process_financial_request":
            # Call AI Gateway
            user_request = arguments.get("user_request", "")

            response = await ai_gateway_client.process_voice_input(
                text=user_request,
                user_id=self.user_context.get("user_id", "unknown"),
                org_id=self.user_context.get("org_id", "unknown"),
                session_id=self.session_id or "unknown",
                conversation_history=self.conversation_history,
            )

            return response.get("response_text", "Done.")

        return "I couldn't process that request."


# ==================== SERVER ====================
server = AgentServer()


@server.rtc_session()
async def voice_session(ctx: JobContext):
    """
    Voice session handler
    Called for each new LiveKit room connection
    """
    # Extract user context from room metadata
    user_context = _extract_user_context(ctx)

    logger.info(
        "voice_session_starting",
        user_id=user_context.get("user_id"),
        room_name=ctx.room.name,
    )

    # Create agent
    agent = LedgerTalkAgent(user_context=user_context)

    # Generate session ID
    agent.session_id = str(uuid.uuid4())

    # Create agent session
    session = AgentSession(
        # STT: AssemblyAI for speech recognition
        stt=assemblyai.STT(
            api_key=settings.ASSEMBLYAI_API_KEY,
        ),

        # LLM: Groq - uses MoneyOps instructions from instructions.py
        llm=groq.LLM(
            model=settings.GROQ_MODEL,
            api_key=settings.GROQ_API_KEY,
            temperature=0.3,
        ),

        # TTS: Cartesia for voice generation
        tts=cartesia.TTS(api_key=settings.CARTESIA_API_KEY),

        # VAD: Silero for voice activity detection
        vad=silero.VAD.load(
            min_speech_duration=settings.VAD_MIN_SPEECH_DURATION,
            min_silence_duration=settings.VAD_MIN_SILENCE_DURATION,
        ),
    )

    # Track whether we are actively handling a speech event via AI gateway.
    # This flag prevents the session's internal LLM from speaking while we
    # are already generating a response through our custom pipeline.
    _processing_lock = asyncio.Lock()

    # Add event handlers BEFORE starting session
    async def _handle_user_speech(ev):
        """Handle user speech - route directly to AI Gateway"""
        # Only act on final transcripts, not interim/preflight ones
        if not ev.is_final:
            return

        # Prevent concurrent handling of overlapping speech events
        if _processing_lock.locked():
            logger.debug("skipping_overlapping_speech_event", session_id=agent.session_id)
            return

        async with _processing_lock:
            try:
                user_text = ev.transcript
                logger.info(
                    "user_speech_recognized",
                    text=user_text,
                    session_id=agent.session_id,
                )

                # Interrupt any in-progress LLM/TTS response from the session's
                # internal pipeline before we speak our AI gateway response.
                # This prevents the double-response race condition.
                try:
                    await session.interrupt()
                except Exception:
                    pass  # interrupt() may not be available in all SDK versions — safe to ignore

                # Call AI Gateway directly, forwarding the user's JWT
                response = await ai_gateway_client.process_voice_input(
                    text=user_text,
                    user_id=user_context.get("user_id", "unknown"),
                    org_id=user_context.get("org_id", "unknown"),
                    session_id=agent.session_id,
                    conversation_history=agent.conversation_history,
                    auth_token=user_context.get("auth_token") or None,
                )

                response_text = response.get("response_text", "I didn't understand that.")

                # Update conversation history — include intent + entities for cross-turn accumulation
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

                # ── Sync the session's internal LLM chat context ───────────────
                # AgentSession's Groq LLM auto-fires on user_input_transcribed.
                # If the last message in the chat history ends with 'assistant',
                # the next LLM call crashes with "last message role must be 'user'".
                # We push user+assistant into session.history so the internal LLM
                # always sees a valid alternating user→assistant sequence.
                try:
                    chat_ctx = session.history  # returns session._chat_ctx
                    if chat_ctx is not None:
                        chat_ctx.insert(
                            llm.ChatMessage(role="user", content=[user_text])
                        )
                        chat_ctx.insert(
                            llm.ChatMessage(role="assistant", content=[response_text])
                        )
                except Exception:
                    pass  # Defensive — don't break speech if history API changes


                # Speak the response back into the room via the session's TTS
                await session.say(response_text, allow_interruptions=False)
            except Exception as exc:
                logger.exception("user_speech_handler_failed", error=str(exc), session_id=agent.session_id)


    @session.on("user_input_transcribed")
    def on_user_speech(ev):
        asyncio.create_task(_handle_user_speech(ev))

    @session.on("agent_speech_committed")
    def on_agent_speech(msg):
        logger.info(
            "agent_response",
            text=msg.text,
            session_id=agent.session_id,
        )

    # Start session
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
        # Run terminal test mode
        from app.cli.test_terminal import main as test_main
        import asyncio
        asyncio.run(test_main())
    else:
        # Run LiveKit agent server
        from livekit.agents import cli

        logger.info(
            "starting_voice_agent",
            app_name=settings.APP_NAME,
            groq_model=settings.GROQ_MODEL,
            ai_gateway_url=settings.AI_GATEWAY_URL,
        )

        cli.run_app(server)
