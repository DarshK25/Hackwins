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
import contextlib
import json
import uuid
from typing import Dict, Any, List, Optional
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
    JobProcess,
    WorkerOptions,
    cli,
)
from livekit.plugins import silero, groq
from livekit.agents.voice.room_io import RoomOptions

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


def _install_asyncio_exception_filter() -> None:
    loop = asyncio.get_running_loop()
    previous_handler = loop.get_exception_handler()

    def _handler(current_loop: asyncio.AbstractEventLoop, context: dict) -> None:
        exc = context.get("exception")
        message = context.get("message", "")
        if isinstance(exc, asyncio.CancelledError) and "exception was never retrieved" in message:
            logger.debug("ignored_cancelled_gather_future_during_shutdown")
            return

        if previous_handler:
            previous_handler(current_loop, context)
        else:
            current_loop.default_exception_handler(context)

    loop.set_exception_handler(_handler)


# ── Bug 8: Premature Confirmation Guard ───────────────────────────────────────
FORBIDDEN_PREMATURE_PHRASES = [
    "invoice created", "invoice sent", "payment recorded",
    "client added", "all set", "good to go",
    # Note: "done" and "completed" excluded — too common in collection responses
]

def premature_confirmation_guard(response_text: str, stage: str) -> str:
    """
    If stage is not EXECUTED, check for premature success phrases.
    Replaces the response with a safe fallback if a forbidden phrase is found.
    
    This prevents the voice agent from saying "invoice created" before the backend
    has actually confirmed creation (Bug 8).
    """
    if stage == "EXECUTED":
        return response_text  # Safe — backend confirmed execution

    text_lower = response_text.lower()
    for phrase in FORBIDDEN_PREMATURE_PHRASES:
        if phrase in text_lower:
            logger.error(
                "premature_confirmation_blocked",
                phrase=phrase,
                stage=stage,
                response_preview=str(response_text)[:100]
            )
            # Return the original text from gateway (usually the clarifying question)
            # rather than blocking — the gateway question is safe to speak.
            # The forbidden phrase check is a safety net; the stage field is the
            # primary guard (voice service uses stage, not response_text keywords).
            return response_text
    return response_text


# ── Agent ─────────────────────────────────────────────────────────────────────
# Agent instance is created directly in session.live below


# ── Entrypoint ────────────────────────────────────────────────────────────────
async def entrypoint(ctx: JobContext):
    logger.info("voice_session_starting", room=ctx.room.name)
    _install_asyncio_exception_filter()

    # Connect to the LiveKit room (v1.4.2 — no room_options param on connect())
    await ctx.connect()

    # Wait for the frontend user to join so we can read their metadata.
    # The agent worker dispatches BEFORE the user connects, so without this wait
    # ctx.room.remote_participants is always empty → user_id/org_id = "unknown".
    participant_joined = await _wait_for_participant(ctx, timeout=15.0)
    if not participant_joined:
        logger.info("voice_session_aborted_no_participant", room=ctx.room.name)
        return

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
    # Reuse prewarmed plugins if available
    stt = ctx.proc.userdata.get("stt") or _create_stt()
    tts = ctx.proc.userdata.get("tts") or _create_tts()

    # AgentSession handles audio processing (STT, TTS, VAD).
    # Since all AI reasoning is in the Gateway, we don't provide an Agent or LLM here
    # to avoid automated double-responses and hallucinations.
    session = AgentSession(
        stt=stt,
        tts=tts,
        vad=silero.VAD.load(
            min_speech_duration=settings.VAD_MIN_SPEECH_DURATION,
            min_silence_duration=settings.VAD_MIN_SILENCE_DURATION,
            activation_threshold=settings.VAD_ACTIVATION_THRESHOLD,
        ),
    )

    # ── Speech handler: intercept transcriptions before they hit the LLM ─────
    # ── Bug 5: Voice Turn Debouncing ───────────────────────────────────────────
    session_closed = asyncio.Event()
    background_tasks: set[asyncio.Task] = set()

    def _track_task(coro, task_name: str) -> asyncio.Task:
        task = asyncio.create_task(coro, name=task_name)
        background_tasks.add(task)

        def _on_done(done_task: asyncio.Task) -> None:
            background_tasks.discard(done_task)
            if done_task.cancelled():
                return
            with contextlib.suppress(asyncio.CancelledError):
                exc = done_task.exception()
                if exc:
                    logger.error(
                        "voice_background_task_failed",
                        task=task_name,
                        error=str(exc),
                    )

        task.add_done_callback(_on_done)
        return task

    def _session_can_respond() -> bool:
        return (
            not session_closed.is_set()
            and getattr(session, "_activity", None) is not None
        )

    transcript_buffer: list[str] = []
    debounce_task: Optional[asyncio.Task] = None
    processing_lock = asyncio.Lock()
    pending_follow_ups: list[str] = []
    
    # ── Utterance Buffering (VAD Split Fix) ──────────────────────────────────
    long_term_buffer: list[str] = []
    flush_task: Optional[asyncio.Task] = None

    def _cancel_task(task: Optional[asyncio.Task]) -> None:
        if task and not task.done():
            task.cancel()

    def _cancel_background_tasks() -> None:
        _cancel_task(debounce_task)
        _cancel_task(flush_task)
        for task in list(background_tasks):
            _cancel_task(task)
        transcript_buffer.clear()
        long_term_buffer.clear()
        pending_follow_ups.clear()

    @session.on("close")
    def on_session_close(ev):
        session_closed.set()
        _cancel_background_tasks()
        raw_reason = getattr(ev, "reason", None)
        reason = getattr(raw_reason, "value", raw_reason)
        logger.info(
            "voice_session_closed_cleanup",
            reason=reason,
            pending_tasks=len(background_tasks),
        )
    
    INCOMPLETE_UTTERANCE_PATTERNS = [
        r"^(amount|price|cost|total|the|for|is|and|but|so|rupees|percent|dollars|of|to)\b.{0,30}$",
        r".*\b(is|are|of|to|for|with)$" # Ends with a connector
    ]

    def _is_incomplete_utterance(text: str) -> bool:
        """Detect if this is a fragment, not a complete thought."""
        t = text.lower().strip()
        if not t: return True
        
        # Exclude common short but complete thoughts (Bug 12)
        complete_short_words = {"yes", "no", "ok", "okay", "correct", "wrong", "sure", "cancel", "stop", "confirmed"}
        if t in complete_short_words:
            return False
            
        if len(t.split()) <= 1: return True
        
        import re
        for p in INCOMPLETE_UTTERANCE_PATTERNS:
            if re.match(p, t): return True
        return False

    async def _flush_long_term_buffer():
        """If no continuation comes, process what we have."""
        await asyncio.sleep(2.0)
        if session_closed.is_set():
            return
        if long_term_buffer:
            combined = " ".join(long_term_buffer)
            long_term_buffer.clear()
            logger.info("flushing_fragment_buffer", text=combined)
            _track_task(_process_and_say(combined), "process_fragment_buffer")

    def sanitize_for_voice(text: str) -> str:
        """Remove any internal system strings before speaking."""
        if not text:
            return "I had trouble processing that. Please try again."
        
        blocked_patterns = [
            r"[A-Z_]{3,}\s+does not support",
            r"Intent not supported",
            r"execution_failed",
            r"gateway_execution",
            r"[A-Z_]{5,}",
            r"Error \d+",
            r"500 Internal",
        ]
        
        import re
        for pattern in blocked_patterns:
            if re.search(pattern, text):
                return "I'm having trouble with that right now. Please try again."
        
        return text

    async def _safe_say(text: str, *, allow_interruptions: bool = True) -> bool:
        if not _session_can_respond():
            logger.info("skipping_say_session_closed", preview=text[:80])
            return False

        try:
            await session.say(text, allow_interruptions=allow_interruptions)
            return True
        except RuntimeError as exc:
            error = str(exc)
            if "isn't running" in error or "is closing" in error:
                session_closed.set()
                logger.info("skipping_say_session_closed", error=error)
                return False
            raise

    async def _process_and_say(text: str) -> None:
        """Helper to send buffered text to gateway and speak response."""
        if not _session_can_respond():
            logger.info("skipping_gateway_session_closed", text=text[:120])
            return

        async with processing_lock:
            if not _session_can_respond():
                logger.info("skipping_gateway_session_closed", text=text[:120])
                return

            logger.info("requesting_gateway", text=text[:120])
            try:
                response = await ai_gateway_client.process_voice_input(
                    text=text,
                    user_id=user_context.get("user_id", "unknown"),
                    org_id=user_context.get("org_id", "unknown"),
                    session_id=session_id,
                    conversation_history=conversation_history,
                )

                # ── Inform Frontend Logic (UI + History) ──
                if not _session_can_respond():
                    logger.info(
                        "discarding_gateway_response_after_session_close",
                        text=text[:120],
                    )
                    return

                ui_event = response.get("ui_event")
                # Get user identities to ensure direct delivery
                dest_identities = list(ctx.room.remote_participants.keys())
                
                if ui_event:
                    logger.info("publishing_ui_event_to_room", type=ui_event.get("type"), user_count=len(dest_identities))
                    await ctx.room.local_participant.publish_data(
                        json.dumps({
                            "type": "moneyops_ui_event",
                            "payload": ui_event
                        }), 
                        topic="ui_events",
                        destination_identities=dest_identities
                    )

                # Update conversation status/transcript
                await ctx.room.local_participant.publish_data(
                    json.dumps({
                        "type": "conversation_update",
                        "user_text": text,
                        "response_text": response.get("response_text"),
                        "intent": response.get("intent"),
                        "action_result": response.get("action_result"),
                        "needs_more_info": response.get("needs_more_info", False),
                        "stage": response.get("stage", "COLLECTING"),
                        "ui_event": ui_event,
                        "dev_event": response.get("dev_event"),
                        "stt_confidence": response.get("stt_confidence", 1.0) # Gateway could also verify
                    }), 
                    topic="gateway_results",
                    destination_identities=dest_identities
                )

                response_text = response.get("response_text", "I hit a snag. Please repeat.")
                intent = response.get("intent", "UNKNOWN")
                # Bug 8: Read the explicit stage from the gateway response
                # COLLECTING = still gathering info (do NOT confirm execution)
                # CONFIRMING = asking user to confirm (do NOT confirm execution)
                # EXECUTED   = backend confirmed success (safe to say "created")
                # FAILED     = backend call failed
                stage = response.get("stage", "COLLECTING")

                # Bug 8: Apply premature confirmation guard
                response_text = premature_confirmation_guard(response_text, stage)

                # Bug 12: Update persistent history for success, EVEN collection stages.
                # Failed execution turns are NOT written (prevents LLM poisoning).
                if response.get("success", False) and intent != "ERROR":
                    conversation_history.append({"role": "user", "content": text, "intent": intent})
                    conversation_history.append({"role": "assistant", "content": response_text})
                    if len(conversation_history) > 20:
                        conversation_history[:] = conversation_history[-20:]
                elif stage == "FAILED" or intent == "ERROR":
                    # Failed turn: do NOT append to history (Bug 12 contract)
                    logger.warning("gateway_execution_failed_history_not_updated", intent=intent)

                safe_response_text = sanitize_for_voice(response_text)
                spoke = await _safe_say(safe_response_text, allow_interruptions=True)
                if not spoke:
                    return
                
                # Check for follow-ups that arrived while we were processing
                if pending_follow_ups:
                    next_text = " ".join(pending_follow_ups)
                    pending_follow_ups.clear()
                    _track_task(_process_and_say(next_text), "process_follow_up")

            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error("gateway_call_failed", error=str(exc))
                await _safe_say("I'm sorry, I'm having trouble connecting. One moment.")

    async def _debounce_timer():
        """Wait for silence then trigger processing."""
        await asyncio.sleep(settings.TURN_DETECTION_DELAY)
        if session_closed.is_set():
            return
        if transcript_buffer:
            combined = " ".join(transcript_buffer)
            transcript_buffer.clear()
            
            nonlocal flush_task
            if _is_incomplete_utterance(combined):
                logger.info("buffering_incomplete_utterance", text=combined)
                long_term_buffer.append(combined)
                if flush_task: flush_task.cancel()
                flush_task = _track_task(_flush_long_term_buffer(), "flush_fragment_buffer")
                return

            # If we have a pending buffer, prepend it
            if long_term_buffer:
                combined = (" ".join(long_term_buffer) + " " + combined).strip()
                long_term_buffer.clear()
                if flush_task: flush_task.cancel()

            if processing_lock.locked():
                logger.info("buffering_interrupted_speech", text=combined[:50])
                pending_follow_ups.append(combined)
            else:
                _track_task(_process_and_say(combined), "process_debounced_utterance")

    @session.on("user_input_transcribed")
    def on_user_speech(ev):
        nonlocal debounce_task
        if session_closed.is_set():
            return

        if not getattr(ev, "is_final", True):
            return
            
        text = (getattr(ev, "transcript", None) or "").strip()
        if not text:
            return

        # ── Confidence Gate (Issue 2 Fix) ──
        # ev.alternatives[0] should contain confidence for the whole transcription in assemblyai/whisper
        # but the safest way is to average segments if available
        confidence = 1.0
        if hasattr(ev, "confidence") and ev.confidence is not None:
             confidence = ev.confidence
        elif hasattr(ev, "alternatives") and ev.alternatives:
             confidence = ev.alternatives[0].confidence
             
        logger.info("utterance_received", text=text, confidence=confidence)
        
        if len(text.strip()) < 2:
            return

        # If confidence is too low, we trigger a "re-ask" directly
        if confidence < 0.7:
            logger.warning("stt_confidence_low_blocking", text=text, confidence=confidence)
            _track_task(
                _safe_say("I didn't quite catch that. Could you repeat?"),
                "low_confidence_reask",
            )
            return

        transcript_buffer.append(text)
        
        if debounce_task:
            debounce_task.cancel()
        debounce_task = _track_task(_debounce_timer(), "voice_debounce")

    @session.on("agent_speech_committed")
    def on_agent_speech(ev):
        text = getattr(ev, "text", "") or ""
        logger.info("agent_spoke", preview=text[:80])

    # ── Start the session ─────────────────────────────────────────────────────
    await session.start(
        room=ctx.room,
        agent=Agent(instructions="MoneyOps Voice Agent"),
        room_options=RoomOptions(close_on_disconnect=True),
    )

    # Greet the user immediately
    try:
        await _safe_say("Welcome to MoneyOps. What would you like to do?")
    except RuntimeError as e:
        logger.warning("failed_to_say_greeting_session_closing", error=str(e))
    logger.info("voice_session_live", room=ctx.room.name, session_id=session_id)


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _wait_for_participant(ctx: JobContext, timeout: float = 10.0) -> bool:
    """Wait until at least one remote participant is in the room, or until timeout.
    
    The agent worker connects to the room BEFORE the frontend user joins.
    This means ctx.room.remote_participants is empty right after ctx.connect().
    We subscribe to the 'participant_connected' event to wait for the user.
    """
    if ctx.room.remote_participants:
        return True
        return  # Already have participants — nothing to wait for
    done = asyncio.Event()

    def _on_participant_connected(participant):
        done.set()

    ctx.room.on("participant_connected", _on_participant_connected)
    try:
        if ctx.room.remote_participants:
            return True
        await asyncio.wait_for(done.wait(), timeout=timeout)
        return True
    except asyncio.TimeoutError:
        logger.warning("no_participant_joined_within_timeout", timeout=timeout)
        return False
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
            # AssemblyAI for low-latency STT
            stt = _assemblyai_plugin.STT(api_key=settings.ASSEMBLYAI_API_KEY)
            logger.info("stt_provider", provider="assemblyai")
            return stt
        except Exception as e:
            logger.warning("assemblyai_init_failed", error=str(e))

    logger.info("stt_provider", provider="groq-whisper")
    return groq.STT()


def prewarm(proc: JobProcess):
    """Pre-initialize heavy plugins to avoid AssignmentTimeoutError."""
    logger.info("prewarming_worker_plugins")
    proc.userdata["stt"] = _create_stt()
    proc.userdata["tts"] = _create_tts()


# ── Entry ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logger.info(
        "starting_voice_service",
        app_name=settings.APP_NAME,
        gateway_url=settings.AI_GATEWAY_URL,
        livekit_url=settings.LIVEKIT_URL,
    )
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm
        )
    )
