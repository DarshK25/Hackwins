"""
Voice API endpoint.
Processes voice input: Intent classification -> Entity extraction -> Agent routing.
Supports multi-turn conversation: tracks missing entities and asks follow-up questions.
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import uuid
import time

from app.orchestration.intent_classifier import IntentClassifier
from app.orchestration.entity_extractor import EntityExtractor
from app.orchestration.agent_router import agent_router
from app.utils.logger import get_logger
from app.config import settings

try:
    from livekit.api.access_token import AccessToken, VideoGrants
    _LIVEKIT_AVAILABLE = True
except ImportError:
    _LIVEKIT_AVAILABLE = False

router = APIRouter()
logger = get_logger(__name__)

intent_classifier = IntentClassifier()
entity_extractor = EntityExtractor()


from enum import Enum

class InvoiceStage(Enum):
    COLLECT_CLIENT = "COLLECT_CLIENT"
    COLLECT_AMOUNT = "COLLECT_AMOUNT"
    COLLECT_DUE_DATE = "COLLECT_DUE_DATE"
    COLLECT_GST = "COLLECT_GST"
    CONFIRMATION = "CONFIRMATION"

class ClientStage(Enum):
    COLLECT_NAME = "COLLECT_NAME"
    COLLECT_EMAIL = "COLLECT_EMAIL"
    COLLECT_PHONE = "COLLECT_PHONE"
    COLLECT_COMPANY = "COLLECT_COMPANY"
    CONFIRMATION = "CONFIRMATION"

class InvoiceDraft:
    """Session-based draft for multi-turn invoice creation."""
    def __init__(self, intent_value: str):
        self.intent_value = intent_value
        self.stage = InvoiceStage.COLLECT_CLIENT
        self.accumulated_entities: Dict[str, Any] = {
            "client_name": None,
            "amount": None,
            "total": None,
            "subtotal": None,
            "due_date": None,
            "gst_percent": None,  # Strictly None, no default 0.0
            "items": [],
            "notes": None
        }
        self.updated_at = time.time()

    def update(self, fresh_entities: Dict[str, Any]):
        """Merge new entities into draft, prioritized."""
        for k, v in fresh_entities.items():
            if v is not None:
                self.accumulated_entities[k] = v
        self.updated_at = time.time()
        self._advance_stage()

    def _advance_stage(self):
        """Automatically advance the stage based on collected data."""
        acc = self.accumulated_entities
        if acc.get("client_name") is None:
            self.stage = InvoiceStage.COLLECT_CLIENT
        elif acc.get("total") is None and acc.get("amount") is None:
            self.stage = InvoiceStage.COLLECT_AMOUNT
        elif acc.get("due_date") is None:
            self.stage = InvoiceStage.COLLECT_DUE_DATE
        elif acc.get("gst_percent") is None:
            self.stage = InvoiceStage.COLLECT_GST
        else:
            self.stage = InvoiceStage.CONFIRMATION

    def is_complete_for_execution(self) -> bool:
        """Fully validated for backend submission."""
        acc = self.accumulated_entities
        # Ensure 'amount' is mapped to 'total'
        if acc.get("amount") and not acc.get("total"):
            acc["total"] = acc["amount"]
            acc["subtotal"] = acc["amount"]
            
        return all([
            acc.get("client_name"),
            acc.get("total"),
            acc.get("due_date"),
            acc.get("gst_percent") is not None
        ])


class ClientDraft:
    """Session-based draft for multi-turn client creation."""
    def __init__(self, intent_value: str):
        self.intent_value = intent_value
        self.stage = ClientStage.COLLECT_NAME
        self.accumulated_entities: Dict[str, Any] = {
            "name": None,
            "email": None,
            "phone_number": None,
            "company": None,
            "address": None,
            "tax_id": None
        }
        self.updated_at = time.time()

    def update(self, fresh_entities: Dict[str, Any]):
        # Map some common variations
        if "client_name" in fresh_entities: fresh_entities["name"] = fresh_entities["client_name"]
        if "phone" in fresh_entities: fresh_entities["phone_number"] = fresh_entities["phone"]

        for k, v in fresh_entities.items():
            if v is not None and k in self.accumulated_entities:
                self.accumulated_entities[k] = v
        self.updated_at = time.time()
        self._advance_stage()

    def _advance_stage(self):
        acc = self.accumulated_entities
        if acc.get("name") is None:
            self.stage = ClientStage.COLLECT_NAME
        elif acc.get("email") is None:
            self.stage = ClientStage.COLLECT_EMAIL
        elif acc.get("phone_number") is None:
            self.stage = ClientStage.COLLECT_PHONE
        else:
            self.stage = ClientStage.CONFIRMATION

    def is_complete_for_execution(self) -> bool:
        acc = self.accumulated_entities
        return all([
            acc.get("name"),
            acc.get("email"),
            acc.get("phone_number")
        ])

# ── In-memory conversation state store ───────────────────────────────────────
# Key: session_id → Draft object (InvoiceDraft or ClientDraft)
_conversation_state: Dict[str, Any] = {}
_STATE_TTL_SECONDS = 300  # 5 minutes


def _cleanup_old_states():
    """Remove conversation states older than TTL."""
    now = time.time()
    expired = [k for k, v in _conversation_state.items() if now - v.updated_at > _STATE_TTL_SECONDS]
    for k in expired:
        del _conversation_state[k]


def _get_follow_up_question(missing_fields: List[str]) -> str:
    """Return a natural follow-up question for the first missing field."""
    questions = {
        "client_name": "Who should I create this invoice for? Please tell me the client's name.",
        "amount": "What is the total amount for this invoice?",
        "total": "What is the total amount for this invoice?",
        "subtotal": "What is the subtotal amount?",
        "items": "What services or products should I include in the invoice?",
        "due_date": "What is the due date for this invoice? Examples: 'today', 'next Friday', or 'in 10 days'.",
        "gst_percent": "Should I apply GST or any tax? If yes, what is the percentage?",
        "name": "What is the client's name?",
        "email": "What is the client's email address?",
        "phone_number": "What is the client's phone number?",
        "company": "Which company do they work for?",
    }
    for field in missing_fields:
        if field in questions:
            return questions[field]
    return f"I still need: {', '.join(missing_fields)}. Could you please provide those?"


def _get_required_for_intent(intent_value: str) -> List[str]:
    """Return required entity keys for a given intent."""
    from app.schemas.intents import Intent, get_intent_requirements
    try:
        intent = Intent[intent_value]
        reqs = get_intent_requirements(intent)
        return reqs.required_entities or []
    except Exception:
        return []


# ── Request / Response Models ─────────────────────────────────────────────────

class VoiceProcessRequest(BaseModel):
    text: str
    user_id: str
    org_id: str
    session_id: str
    context: Dict[str, Any] = Field(default_factory=dict)
    conversation_history: List[Dict[str, Any]] = Field(default_factory=list)


# ── Token Endpoint ────────────────────────────────────────────────────────────

@router.get("/voice/token")
async def get_voice_token(
    user_id: str = "user",
    org_id: Optional[str] = None,
    room_name: Optional[str] = None,
):
    """
    Generate a LiveKit access token for voice chat.
    Embeds user_id and org_id in room metadata so the voice agent
    can identify which account to save invoices/data to.
    """
    import json as _json

    try:
        if not _LIVEKIT_AVAILABLE:
            raise HTTPException(status_code=503, detail="LiveKit SDK not installed on server")

        if not settings.LIVEKIT_API_KEY or not settings.LIVEKIT_API_SECRET:
            raise HTTPException(status_code=500, detail="LiveKit not configured on server")

        actual_room = room_name or f"voice-{user_id}-{str(uuid.uuid4())[:8]}"

        # If user_id starts with 'user_', it's a Clerk ID. Resolve it to local Mongo UUIDs.
        resolved_user_id = user_id
        resolved_org_id = org_id or "default_org"

        if user_id.startswith("user_"):
            try:
                from app.adapters.backend_adapter import BackendHttpAdapter
                adapter = BackendHttpAdapter()
                resp = await adapter.get_onboarding_status(user_id)
                if resp.success and resp.data:
                    # OnboardingStatusResponse structure: {userId: uuid, organizationId: uuid, ...}
                    data = resp.data
                    resolved_user_id = data.get("userId") or user_id
                    resolved_org_id = data.get("organizationId") or org_id or "default_org"
                    logger.info("resolved_clerk_id", clerk_id=user_id, user_uuid=resolved_user_id, org_uuid=resolved_org_id)
                else:
                    logger.warning("clerk_id_resolution_failed", clerk_id=user_id, error=resp.error)
            except Exception as e:
                logger.error("error_resolving_clerk_id", clerk_id=user_id, error=str(e))

        # Both participant metadata AND room metadata carry user_id/org_id.
        # The voice-service agent reads participant metadata first, but falls back
        # to room metadata — having both guarantees it's always available.
        context_metadata = _json.dumps({
            "user_id": resolved_user_id,
            "org_id": resolved_org_id,
        })

        token = AccessToken(settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET) \
            .with_identity(user_id) \
            .with_name(user_id) \
            .with_metadata(context_metadata) \
            .with_grants(VideoGrants(
                room_join=True,
                room=actual_room,
                room_create=True,
            ))

        return {
            "token": token.to_jwt(),
            "url": settings.LIVEKIT_URL,
            "room_name": actual_room,
            "user_id": user_id,
            "org_id": org_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("token_generation_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ── Voice Process Endpoint ────────────────────────────────────────────────────

@router.post("/voice/process")
async def process_voice(request: VoiceProcessRequest, fastapi_request: Request):
    """
    Main voice processing pipeline:
    1. Classify intent
    2. Extract entities (LLM-powered for invoice intents)
    3. Merge with accumulated conversation state (multi-turn support)
    4. If required fields still missing → return a follow-up question
    5. Otherwise → route to agent → execute action → return result
    """
    try:
        _cleanup_old_states()

        logger.info(
            "voice_process_request",
            text_preview=request.text[:100],
            user_id=request.user_id,
            session_id=request.session_id,
        )

        # Build context dict passed to agents
        # resolve Clerk IDs if necessary
        resolved_user_id = request.user_id
        resolved_org_id = request.org_id

        if request.user_id.startswith("user_"):
            try:
                from app.adapters.backend_adapter import BackendHttpAdapter
                adapter = BackendHttpAdapter()
                resp = await adapter.get_onboarding_status(request.user_id)
                if resp.success and resp.data:
                    data = resp.data
                    resolved_user_id = data.get("userId") or request.user_id
                    resolved_org_id = data.get("organizationId") or request.org_id
                    logger.info("resolved_clerk_id_manual", clerk_id=request.user_id, user_uuid=resolved_user_id, org_uuid=resolved_org_id)
            except Exception as e:
                logger.error("error_resolving_clerk_id_manual", clerk_id=request.user_id, error=str(e))

        context = dict(request.context)
        context.update({
            "user_id": resolved_user_id,
            "org_id": resolved_org_id,
            "session_id": request.session_id,
            "channel": "voice",
            "conversation_history": request.conversation_history,
        })

        # Pass auth token through if present
        auth_header = fastapi_request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            context["auth_token"] = auth_header[7:]

        # ── 1. State Retrieval & Initial Handling ─────────────────────────────
        draft = _conversation_state.get(request.session_id)
        from app.schemas.intents import Intent as IntentEnum

        # Pre-process: Is this a cancellation? (Global override)
        # We still run classification just to see if user wants to cancel
        temp_classification = await intent_classifier.classify(request.text, request.conversation_history, context)
        if temp_classification.intent == IntentEnum.CANCELLATION:
            _conversation_state.pop(request.session_id, None)
            return {
                "response_text": "Okay, I've canceled that process. How else can I help?",
                "intent": "CANCELLATION",
                "success": True,
                "needs_more_info": False
            }

        # ── 2. Handle ACTIVE Confirmation Stage ──────────────────────────────
        if draft and draft.stage in {InvoiceStage.CONFIRMATION, ClientStage.CONFIRMATION}:
            # LOCKED STAGE: Only accept Yes/No (Confirmation/Cancellation)
            if temp_classification.intent == IntentEnum.CONFIRMATION:
                # Proceed to execution
                intent = IntentEnum[draft.intent_value]
                accumulated = draft.accumulated_entities
                logger.info("confirmation_received_executing", intent=intent.value)
            else:
                # User said something else while we were waiting for 'Yes'
                if isinstance(draft, InvoiceDraft):
                    msg = "I'm currently waiting for your confirmation for the invoice. Please say 'Yes' to proceed or 'Cancel' to stop."
                else:
                    msg = f"I'm ready to create client {draft.accumulated_entities.get('name')}. Please say 'Yes' to confirm or 'Cancel' to stop."
                
                return {
                    "response_text": msg,
                    "intent": "CONFIRMATION",
                    "success": True,
                    "needs_more_info": True,
                    "entities": draft.accumulated_entities
                }
        else:
            # ── 3. Normal Data Collection Flow ────────────────────────────────
            if draft:
                # Session is ACTIVE: Lock intent, skip classification
                intent = IntentEnum[draft.intent_value]
                intent_confidence = 1.0
                logger.info("multi_turn_locked_stage", stage=draft.stage.value, intent=intent.value)
            else:
                # Session is NEW: Run classification
                intent = temp_classification.intent
                intent_confidence = temp_classification.confidence
                if intent == IntentEnum.INVOICE_CREATE:
                    draft = InvoiceDraft(intent_value=intent.value)
                    _conversation_state[request.session_id] = draft
                elif intent == IntentEnum.CLIENT_CREATE:
                    draft = ClientDraft(intent_value=intent.value)
                    _conversation_state[request.session_id] = draft

            # ── 4. Extract & Update ───────────────────────────────────────────
            # Always extract if we are not in the confirmation loop
            extracted_entities = await entity_extractor.extract(request.text, intent, context)
            fresh_entities = {}
            if extracted_entities.amount: fresh_entities["amount"] = float(extracted_entities.amount)
            if extracted_entities.client_name: fresh_entities["client_name"] = extracted_entities.client_name
            if extracted_entities.gst_percent is not None: fresh_entities["gst_percent"] = extracted_entities.gst_percent
            if extracted_entities.time_period: fresh_entities["due_date"] = extracted_entities.time_period
            
            for entity in extracted_entities.entities:
                key = entity.entity_type.value.lower()
                if key not in fresh_entities: fresh_entities[key] = entity.value

            if draft:
                draft.update(fresh_entities)
                accumulated = draft.accumulated_entities
            else:
                accumulated = fresh_entities

        # ── 5. Decision Loop (Follow-up vs Review vs Execute) ────────────────
        if draft:
            if not draft.is_complete_for_execution():
                # Still missing data
                missing_fields = []
                acc = draft.accumulated_entities
                if isinstance(draft, InvoiceDraft):
                    if not acc.get("client_name"): missing_fields.append("client_name")
                    elif not (acc.get("total") or acc.get("amount")): missing_fields.append("amount")
                    elif not acc.get("due_date"): missing_fields.append("due_date")
                    elif acc.get("gst_percent") is None: missing_fields.append("gst_percent")
                else:
                    # Client Draft
                    if not acc.get("name"): missing_fields.append("name")
                    elif not acc.get("email"): missing_fields.append("email")
                    elif not acc.get("phone_number"): missing_fields.append("phone_number")

                follow_up = _get_follow_up_question(missing_fields)
                return {
                    "response_text": follow_up,
                    "intent": draft.intent_value,
                    "success": True,
                    "needs_more_info": True,
                    "entities": accumulated,
                }
            
            # All data present but not confirmed yet
            if draft.stage in {InvoiceStage.CONFIRMATION, ClientStage.CONFIRMATION} and temp_classification.intent != IntentEnum.CONFIRMATION:
                # Ask for confirmation
                if isinstance(draft, InvoiceDraft):
                    client = accumulated.get("client_name") or "the client"
                    amount = accumulated.get("total") or accumulated.get("amount")
                    due = accumulated.get("due_date")
                    gst = accumulated.get("gst_percent")
                    summary = f"I'm ready to create an invoice for {client} for ₹{amount}, due on {due}, with {gst}% GST. Should I proceed?"
                else:
                    # Client summary
                    name = accumulated.get("name")
                    email = accumulated.get("email")
                    summary = f"I'm ready to create client {name} with email {email}. Should I proceed?"

                return {
                    "response_text": summary,
                    "intent": draft.intent_value,
                    "success": True,
                    "needs_more_info": True,
                    "entities": accumulated,
                }

        # ── 6. Final Execution ────────────────────────────────────────────────
        # If we reached here, either it was a generic intent or draft is confirmed
        if draft:
            _conversation_state.pop(request.session_id, None)

        agent_response = await agent_router.route(
            intent=intent,
            entities=accumulated,
            context=context,
        )

        response_text = agent_response.message
        # Shorten for voice
        if len(response_text) > 250:
            response_text = response_text[:250].rsplit(".", 1)[0] + "."

        return {
            "response_text": response_text,
            "intent": intent.value,
            "success": agent_response.success,
            "needs_more_info": agent_response.needs_clarification,
            "action_result": agent_response.data if not agent_response.needs_clarification else None,
            "entities": accumulated,
            "agent_type": agent_response.agent_type.value if agent_response.agent_type else None,
        }

        logger.info(
            "voice_process_complete",
            intent=intent.value,
            success=agent_response.success,
            response=response_text[:120],
        )

        return {
            "response_text": response_text,
            "intent": intent.value,
            "confidence": float(intent_confidence),
            "success": agent_response.success,
            "needs_more_info": agent_response.needs_clarification,
            "action_result": agent_response.data if not agent_response.needs_clarification else None,
            "entities": accumulated,
            "agent_type": (
                agent_response.agent_type.value if agent_response.agent_type else None
            ),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("voice_process_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Voice processing failed: {str(e)}")
