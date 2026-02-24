"""
MoneyOps Voice Service - Agent Entrypoint
==========================================
Architecture (livekit-agents 1.4.2):
  User speaks → VAD → STT (Groq Whisper)
             → [user_input_transcribed event]
             → AI Gateway /voice/process
             → [Intent + Entity extraction + DB action]
             → Response text → TTS → User hears reply

The AI Gateway is the BRAIN — voice-service only handles audio I/O.
The LLM in AgentSession is required by the framework but is effectively
bypassed: we intercept UserInputTranscribedEvent before it reaches the LLM.
"""
import asyncio
import json
import uuid
from pathlib import Path
from dotenv import load_dotenv

# Load shared .env before any app imports
load_dotenv(dotenv_path=Path(__file__).resolve().parents[4] / ".env", override=True)

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# ── livekit-agents 1.4.2 imports ─────────────────────────────────────────────
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    RoomInputOptions,
    WorkerOptions,
    cli,
)
from livekit.plugins import silero, groq

# Move optional plugin imports to top level to satisfy plugin registration
# which must happen on the main thread.
try:
    from livekit.plugins import cartesia as _cartesia_plugin
    HAS_CARTESIA = True
except ImportError:
    HAS_CARTESIA = False

try:
    from livekit.plugins import assemblyai as _assemblyai_plugin
    HAS_ASSEMBLYAI = True
except ImportError:
    HAS_ASSEMBLYAI = False

from app.agent.adapters import ai_gateway_client
from app.config import settings
from app.utils.logger import setup_logging, get_logger

setup_logging(settings.LOG_LEVEL)
logger = get_logger(__name__)


# ── Agent ─────────────────────────────────────────────────────────────────────
class MoneyOpsVoiceAgent(Agent):
    """
    Minimal pass-through agent.
    All reasoning is handled by the AI Gateway.
    The system_prompt here is minimal because the agent won't generate
    its own responses — we intercept via user_input_transcribed.
    """
    def __init__(self):
        super().__init__(
            instructions=(
                "You are MoneyOps AI, a financial voice assistant. "
                "Keep all responses brief and action-focused."
            )
        )


# ── Entrypoint ────────────────────────────────────────────────────────────────
async def entrypoint(ctx: JobContext):
    logger.info("voice_session_starting", room=ctx.room.name)

    # Connect to the LiveKit room (v1.4.2 — no room_options param on connect())
    await ctx.connect()

    # Wait for the frontend user to join so we can read their metadata.
    # The agent worker dispatches BEFORE the user connects, so without this wait
    # ctx.room.remote_participants is always empty → user_id/org_id = "unknown".
    await _wait_for_participant(ctx, timeout=15.0)

    # Extract user/org identifiers from room or participant metadata
    user_context = _extract_user_context(ctx)
    logger.info(
        "user_context_loaded",
        user_id=user_context.get("user_id"),
        org_id=user_context.get("org_id"),
    )

    session_id = str(uuid.uuid4())
    conversation_history: list = []

    # ── Build STT, TTS, LLM ──────────────────────────────────────────────────
    stt = _create_stt()
    tts = _create_tts()

    # AgentSession REQUIRES an llm in livekit-agents 1.4.x.
    # We pass one but override the speech pipeline via user_input_transcribed.
    llm = groq.LLM(model=settings.GROQ_MODEL, api_key=settings.GROQ_API_KEY)

    session = AgentSession(
        stt=stt,
        llm=llm,
        tts=tts,
        vad=silero.VAD.load(
            min_speech_duration=settings.VAD_MIN_SPEECH_DURATION,
            min_silence_duration=settings.VAD_MIN_SILENCE_DURATION,
        ),
    )

    # ── Speech handler: intercept transcriptions before they hit the LLM ─────
    async def _handle_user_speech(ev) -> None:
        """
        Fires after STT produces a final transcript.
        We send it to the AI Gateway instead of letting the LLM handle it.
        The response from the Gateway is spoken via session.say().
        """
        # Only act on final (committed) transcriptions
        if not getattr(ev, "is_final", True):
            return

        user_text = (getattr(ev, "transcript", None) or "").strip()
        if not user_text:
            return

        logger.info("user_speech_received", text=user_text[:120], session_id=session_id)

        try:
            # ► Call AI Gateway — intent classification + entity extraction + DB action
            response = await ai_gateway_client.process_voice_input(
                text=user_text,
                user_id=user_context.get("user_id", "unknown"),
                org_id=user_context.get("org_id", "unknown"),
                session_id=session_id,
                conversation_history=conversation_history,
            )

            # ► Send result to Frontend via Data Channel
            # This allows the dashboard to show transcripts and refresh lists
            try:
                await ctx.room.local_participant.publish_data(
                    json.dumps({
                        "type": "conversation_update",
                        "user_text": user_text,
                        "response_text": response.get("response_text"),
                        "intent": response.get("intent"),
                        "action_result": response.get("action_result"),
                        "needs_more_info": response.get("needs_more_info", False),
                    }), 
                    topic="gateway_results"
                )
            except Exception as e:
                logger.warning("failed_to_publish_data", error=str(e))

            response_text = response.get(
                "response_text", "I'm not sure how to help with that."
            )
            intent = response.get("intent", "UNKNOWN")
            action_result = response.get("action_result")
            needs_more = response.get("needs_more_info", False)

            # Log clearly so you can see exactly what happened in the terminal
            logger.info(
                "gateway_response",
                intent=intent,
                needs_more_info=needs_more,
                response=response_text[:120],
                action_result=action_result,
                session_id=session_id,
            )

            if action_result and not needs_more:
                logger.info(
                    "✅ ACTION_EXECUTED",
                    intent=intent,
                    result=str(action_result)[:200],
                )

            # Keep rolling conversation history (capped at 20 turns)
            conversation_history.append({"role": "user", "content": user_text, "intent": intent})
            conversation_history.append({"role": "assistant", "content": response_text})
            if len(conversation_history) > 20:
                conversation_history[:] = conversation_history[-20:]

            # ► Speak the AI Gateway's response
            try:
                await session.say(response_text, allow_interruptions=True)
            except RuntimeError as e:
                logger.warning("failed_to_say_response_session_closing", error=str(e))

        except Exception as exc:
            logger.error("speech_handler_failed", error=str(exc), exc_info=True)
            try:
                await session.say(
                    "I'm sorry, something went wrong. Please try again.",
                    allow_interruptions=True,
                )
            except RuntimeError as e:
                logger.warning("failed_to_say_error_message_session_closing", error=str(e))

    # Register the event handler BEFORE starting the session
    @session.on("user_input_transcribed")
    def on_user_speech(ev):
        # Spawn a task so we don't block the event loop
        asyncio.create_task(_handle_user_speech(ev))

    @session.on("agent_speech_committed")
    def on_agent_speech(ev):
        text = getattr(ev, "text", "") or ""
        logger.info("agent_spoke", preview=text[:80])

    # ── Start the session ─────────────────────────────────────────────────────
    await session.start(
        room=ctx.room,
        agent=MoneyOpsVoiceAgent(),
        room_input_options=RoomInputOptions(),
    )

    # Greet the user immediately
    try:
        await session.say(
            "Hello! MoneyOps AI is ready. You can say things like "
            "'Create an invoice for Tanoosh Jain for 10,000 rupees'. How can I help?",
            allow_interruptions=True,
        )
    except RuntimeError as e:
        logger.warning("failed_to_say_greeting_session_closing", error=str(e))
    logger.info("voice_session_live", room=ctx.room.name, session_id=session_id)


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _wait_for_participant(ctx: JobContext, timeout: float = 10.0) -> None:
    """Wait until at least one remote participant is in the room, or until timeout.
    
    The agent worker connects to the room BEFORE the frontend user joins.
    This means ctx.room.remote_participants is empty right after ctx.connect().
    We subscribe to the 'participant_connected' event to wait for the user.
    """
    if ctx.room.remote_participants:
        return  # Already have participants — nothing to wait for
    done = asyncio.Event()

    def _on_participant_connected(participant):
        done.set()

    ctx.room.on("participant_connected", _on_participant_connected)
    try:
        await asyncio.wait_for(done.wait(), timeout=timeout)
    except asyncio.TimeoutError:
        logger.warning("no_participant_joined_within_timeout", timeout=timeout)
    finally:
        ctx.room.off("participant_connected", _on_participant_connected)


def _extract_user_context(ctx: JobContext) -> dict:
    """Extract user_id / org_id from room or participant metadata.
    
    The LiveKit access-token embeds a JSON metadata string:
        {"user_id": "<mongo_user_id>", "org_id": "<mongo_org_id>"}
    via .with_metadata(...) on the participant token.
    We try participant metadata first, then room metadata as fallback.
    """
    participant = next(iter(ctx.room.remote_participants.values()), None)
    metadata: dict = {}

    # Try participant metadata first (set by with_metadata() in token generation)
    raw_meta = None
    if participant and participant.metadata:
        raw_meta = participant.metadata
    elif ctx.room.metadata:
        raw_meta = ctx.room.metadata

    if raw_meta:
        if isinstance(raw_meta, str):
            try:
                metadata = json.loads(raw_meta)
            except Exception:
                logger.warning("failed_to_parse_participant_metadata", raw=raw_meta[:200])
                metadata = {}
        elif isinstance(raw_meta, dict):
            metadata = raw_meta

    user_id = metadata.get("user_id")
    org_id = metadata.get("org_id")

    # Last-resort fallback: participant identity string  
    # (some flows encode user_id as identity, or "userId|orgId")
    if not user_id and participant and participant.identity:
        identity = participant.identity
        if "|" in identity:
            parts = identity.split("|", 1)
            user_id = parts[0].strip() or None
            org_id = org_id or (parts[1].strip() or None)
        else:
            user_id = identity

    result = {
        "user_id": user_id or "unknown",
        "org_id": org_id or "unknown",
        "currency": metadata.get("currency", "INR"),
    }
    logger.info(
        "user_context_extracted",
        user_id=result["user_id"],
        org_id=result["org_id"],
        participant_identity=participant.identity if participant else None,
    )
    return result


def _create_tts():
    """Try Cartesia first (better voice quality), fall back to Groq Orpheus."""
    if HAS_CARTESIA and settings.CARTESIA_API_KEY:
        try:
            tts = _cartesia_plugin.TTS(api_key=settings.CARTESIA_API_KEY)
            logger.info("tts_provider", provider="cartesia")
            return tts
        except Exception as e:
            logger.warning("cartesia_init_failed", error=str(e))

    # Groq Orpheus — requires accepting terms at console.groq.com/playground
    logger.info("tts_provider", provider="groq-orpheus")
    return groq.TTS(model="canopylabs/orpheus-v1-english", voice="autumn")


def _create_stt():
    """Try AssemblyAI first, fall back to Groq Whisper."""
    if HAS_ASSEMBLYAI and settings.ASSEMBLYAI_API_KEY:
        try:
            stt = _assemblyai_plugin.STT(api_key=settings.ASSEMBLYAI_API_KEY)
            logger.info("stt_provider", provider="assemblyai")
            return stt
        except Exception as e:
            logger.warning("assemblyai_init_failed", error=str(e))

    logger.info("stt_provider", provider="groq-whisper-large-v3-turbo")
    return groq.STT(model="whisper-large-v3-turbo")


# ── Entry ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logger.info(
        "starting_voice_service",
        app_name=settings.APP_NAME,
        gateway_url=settings.AI_GATEWAY_URL,
        livekit_url=settings.LIVEKIT_URL,
    )
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
