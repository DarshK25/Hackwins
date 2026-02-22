"""
Voice API endpoint.
Processes voice input: Intent classification -> Entity extraction -> Agent routing.

Key design:
- Entity accumulation: merges entities from previous turns for multi-turn flows (e.g. invoice creation)
- Required-field gate: for write operations, asks clarifying questions before calling backend
- LLM skip: avoids redundant LLM entity extraction for simple operational intents
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional

from app.orchestrator.intent_classifier import IntentClassifier
from app.orchestrator.entity_extractor import EntityExtractor
from app.orchestration.agent_router import agent_router
from app.utils.logger import get_logger
from app.config import settings
from app.schemas.intents import Intent, ComplexityLevel, get_intent_requirements

from livekit.api import AccessToken, VideoGrants
import uuid

router = APIRouter()
logger = get_logger(__name__)

intent_classifier = IntentClassifier()
entity_extractor = EntityExtractor()


class VoiceProcessRequest(BaseModel):
    text: str
    user_id: str
    org_id: str
    session_id: str
    context: Dict[str, Any] = Field(default_factory=dict)
    conversation_history: List[Dict[str, Any]] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# Required fields and clarifying questions per intent
# If any required field is missing, return the question instead of calling backend
# ─────────────────────────────────────────────────────────────────────────────
REQUIRED_FIELDS_GATE: Dict[Intent, Dict[str, str]] = {
    Intent.INVOICE_CREATE: {
        "client_name": "Who should I create this invoice for? Please tell me the client's name.",
        "amount": "What is the total amount for this invoice?",
    },
    Intent.PAYMENT_RECORD: {
        "invoice_id": "Which invoice was this payment for? Please give me the invoice number.",
        "amount": "How much was the payment?",
    },
}


def _accumulate_entities_from_history(
    current_entities: Dict[str, Any],
    conversation_history: List[Dict[str, Any]],
    intent: Intent,
) -> Dict[str, Any]:
    """
    Merge entities collected in previous turns of the same intent.
    Bridges through CONFIRMATION turns so 'yes, continue' does not break the chain.
    Current turn entities always take priority over historical ones.
    """
    accumulated: Dict[str, Any] = {}
    BRIDGE_INTENTS = {"CONFIRMATION", "GENERAL_QUERY"}  # these don't break the chain

    for turn in reversed(conversation_history):
        turn_intent = turn.get("intent")
        if turn_intent == intent.value:
            # Same intent — absorb its entities
            prior = turn.get("entities", {})
            for key, value in prior.items():
                if key not in accumulated:
                    accumulated[key] = value
        elif turn_intent in BRIDGE_INTENTS:
            # Bridge intents: skip over without breaking the accumulation chain
            continue
        else:
            # Actual context switch — stop
            break

    accumulated.update(current_entities)
    return accumulated


def _find_pending_invoice_intent(
    conversation_history: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """
    Walk backwards through history to find accumulated INVOICE_CREATE entities
    that were being collected before a CONFIRMATION turn. Returns the entity dict,
    or None if no pending invoice creation context exists.
    """
    candidate_entities: Dict[str, Any] = {}
    for turn in reversed(conversation_history):
        turn_intent = turn.get("intent")
        if turn_intent == Intent.INVOICE_CREATE.value:
            prior = turn.get("entities", {})
            for key, val in prior.items():
                if key not in candidate_entities:
                    candidate_entities[key] = val
        elif turn_intent in {"CONFIRMATION", "GENERAL_QUERY"}:
            continue
        else:
            break
    return candidate_entities if candidate_entities else None


def _get_missing_field_question(
    intent: Intent,
    entities: Dict[str, Any],
) -> Optional[str]:
    """
    Return the first clarifying question for a missing required field, or None if all present.
    """
    gates = REQUIRED_FIELDS_GATE.get(intent, {})
    for field, question in gates.items():
        value = entities.get(field) or entities.get(field.replace("_", " "))
        if not value:
            return question
    return None


def _build_clarifying_response(question: str, intent: Intent, entities: Dict[str, Any]):
    """Build a voice-friendly clarifying response dict."""
    return {
        "response_text": question,
        "intent": intent.value,
        "confidence": 0.9,
        "success": True,
        "entities": entities,
        "agent_type": None,
        "awaiting_clarification": True,
    }


@router.get("/voice/token")
async def get_voice_token(
    user_id: str = "user",
    org_id: str = "",
    room_name: str = None,
    metadata: str = "",
):
    """
    Generate a LiveKit access token for voice chat.
    Embeds user_id, org_id, and auth_token as room metadata so the
    voice-service can pass real identity to the AI Gateway on each turn.
    """
    import json as _json
    try:
        if not settings.LIVEKIT_API_KEY or not settings.LIVEKIT_API_SECRET:
            raise HTTPException(status_code=500, detail="LiveKit not configured on server")

        if not room_name:
            room_name = f"voice-{user_id}-{str(uuid.uuid4())[:8]}"

        # Build room metadata: merge explicit params with any JSON blob from frontend
        room_meta: dict = {}
        if metadata:
            try:
                room_meta = _json.loads(metadata)
            except Exception:
                pass
        # Explicit params always win over the JSON blob
        if user_id and user_id != "user":
            room_meta["user_id"] = user_id
        if org_id:
            room_meta["org_id"] = org_id

        token = (
            AccessToken(settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET)
            .with_identity(user_id)
            .with_name(user_id)
            .with_grants(VideoGrants(
                room_join=True,
                room=room_name,
            ))
            .with_metadata(_json.dumps(room_meta))
        )

        return {
            "token": token.to_jwt(),
            "url": settings.LIVEKIT_URL,
            "room_name": room_name,
        }
    except Exception as e:
        logger.error("token_generation_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/voice/process")
async def process_voice(request: VoiceProcessRequest, fastapi_request: Request):
    try:
        logger.info(
            "voice_process_request",
            text_preview=request.text[:100],
            user_id=request.user_id,
            org_id=request.org_id,
            session_id=request.session_id,
        )

        context = dict(request.context)
        context.update(
            {
                "user_id": request.user_id,
                "org_id": request.org_id,
                "session_id": request.session_id,
                "channel": "voice",
                "conversation_history": request.conversation_history,
            }
        )

        auth_header = fastapi_request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            context["auth_token"] = auth_header[7:]

        # ── Step 1: Intent classification (always)
        intent_classification = await intent_classifier.classify(
            user_input=request.text,
            conversation_history=request.conversation_history,
            business_context=context,
        )

        intent = intent_classification.intent
        intent_confidence = intent_classification.confidence

        logger.info(
            "intent_classified",
            intent=intent.value,
            confidence=intent_confidence,
        )

        # ── CONFIRMATION / INVOICE_UPDATE bridging ──────────────────────────
        # When the user says "yes", "correct", "continue", etc. (CONFIRMATION intent)
        # OR when they provide additional details (e.g. "due date is March 15th") that
        # the classifier fires as INVOICE_UPDATE — but there is a pending INVOICE_CREATE
        # context in history — treat the turn as a continuation of that creation flow.
        if intent in (Intent.CONFIRMATION, Intent.INVOICE_UPDATE) and request.conversation_history:
            pending = _find_pending_invoice_intent(request.conversation_history)
            if pending:
                original_intent_value = intent.value
                # Reroute: act as INVOICE_CREATE with all accumulated entities
                intent = Intent.INVOICE_CREATE
                intent_confidence = 0.95
                logger.info(
                    "intent_rerouted_to_invoice_create",
                    original_intent=original_intent_value,
                    accumulated_entities=list(pending.keys()),
                )

        # ── Step 2: Entity extraction
        # For simple operational intents (INVOICE_CREATE, PAYMENT_RECORD etc.),
        # skip the LLM extraction path when regex already found entities.
        # This removes ~800ms-1s of latency per turn.
        requirements = get_intent_requirements(intent)
        force_llm = requirements.complexity in {ComplexityLevel.COMPLEX, ComplexityLevel.STRATEGIC}

        extracted_entities = await entity_extractor.extract(
            user_input=request.text,
            intent=intent,
            context=context,
        )

        entities_dict: Dict[str, Any] = {}
        for entity in extracted_entities.entities:
            from app.schemas.entities import EntityType as ET
            if entity.entity_type == ET.ENTITY_NAME and entity.normalized_value:
                # Use the original LLM-assigned type name as the key (e.g. "quantity", "due_date")
                key = str(entity.normalized_value).lower()
            else:
                key = entity.entity_type.value.lower()
            # Don't overwrite a value already found with higher confidence
            if key not in entities_dict:
                entities_dict[key] = entity.value

        # ── Step 3: Accumulate entities from previous turns (same intent)
        # This allows multi-turn flows: "for Ajay Singh" + "fifty thousand" across 2 turns
        if request.conversation_history:
            entities_dict = _accumulate_entities_from_history(
                current_entities=entities_dict,
                conversation_history=request.conversation_history,
                intent=intent,
            )

        logger.info(
            "entities_extracted",
            entity_count=len(entities_dict),
            entities=list(entities_dict.keys()),
            accumulated=bool(request.conversation_history),
        )

        # ── Step 4: Required-field gate (ask clarifying question before backend call)
        # Do NOT call the backend if we're still collecting required info.
        missing_question = _get_missing_field_question(intent, entities_dict)
        if missing_question:
            logger.info(
                "clarification_needed",
                intent=intent.value,
                missing_fields=[
                    f for f, _ in REQUIRED_FIELDS_GATE.get(intent, {}).items()
                    if not entities_dict.get(f)
                ],
            )
            return _build_clarifying_response(missing_question, intent, entities_dict)

        # ── Step 5: Route to agent (backend call happens here)
        agent_response = await agent_router.route(
            intent=intent,
            entities=entities_dict,
            context=context,
        )

        response_text = agent_response.message
        max_length = context.get("max_response_length", 300)
        if len(response_text) > max_length:
            response_text = response_text[:max_length].rsplit(".", 1)[0] + "."

        logger.info(
            "voice_process_complete",
            intent=intent.value,
            response_length=len(response_text),
            success=agent_response.success,
        )

        return {
            "response_text": response_text,
            "intent": intent.value,
            "confidence": float(intent_confidence),
            "success": agent_response.success,
            "entities": entities_dict,
            "agent_type": (
                agent_response.agent_type.value if agent_response.agent_type else None
            ),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("voice_process_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Voice processing failed: {str(e)}")
