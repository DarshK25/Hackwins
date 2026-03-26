"""
Voice API endpoint.
Processes voice input: Intent classification -> Entity extraction -> Agent routing.
Supports multi-turn conversation: tracks missing entities and asks follow-up questions.
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, Any, List, Optional, Literal
import uuid
import time
import re
import datetime
from enum import Enum

from app.orchestration.intent_classifier import IntentClassifier
from app.orchestration.entity_extractor import EntityExtractor
from app.utils.logger import get_logger
from app.config import settings
from app.adapters.backend_adapter import get_backend_adapter

try:
    from livekit.api.access_token import AccessToken, VideoGrants
    _LIVEKIT_AVAILABLE = True
except ImportError:
    _LIVEKIT_AVAILABLE = False

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

@router.get("/voice/token")
async def get_voice_token(
    user_id: str = "user",
    org_id: Optional[str] = None,
    room_name: Optional[str] = None,
):
    """Generate a LiveKit access token for voice chat."""
    try:
        if not _LIVEKIT_AVAILABLE:
            raise HTTPException(status_code=503, detail="LiveKit SDK not installed")

        if not settings.LIVEKIT_API_KEY or not settings.LIVEKIT_API_SECRET:
            raise HTTPException(status_code=500, detail="LiveKit credentials missing")

        actual_room = room_name or f"voice-{user_id}-{str(uuid.uuid4())[:8]}"
        
        token = AccessToken(settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET) \
            .with_identity(user_id) \
            .with_metadata(re.sub(r'\s+', '', f'{{"user_id":"{user_id}","org_id":"{org_id or "default"}","room":"{actual_room}"}}')) \
            .with_grants(VideoGrants(room_join=True, room=actual_room))

        return {
            "token": token.to_jwt(),
            "url": settings.LIVEKIT_URL,
            "room_name": actual_room,
        }
    except Exception as e:
        logger.error("token_generation_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/voice/process")
async def process_voice(request: VoiceProcessRequest, fastapi_request: Request):
    """
    Main voice processing pipeline.
    Routes to VoiceProcessor for intent locking and multi-turn handling.
    """
    from app.voice_processor import voice_processor, VoiceContext
    
    try:
        context = VoiceContext(
            session_id=request.session_id,
            user_id=request.user_id,
            org_uuid=request.org_id, # Default to clerk org ID, process() will resolve
            clerk_org_id=request.org_id,
            raw_text=request.text,
        )
        
        result = await voice_processor.process(request.text, context)
        return result
    except Exception as e:
        import traceback
        err_msg = traceback.format_exc()
        logger.error("voice_process_failed", error=str(e), exc_info=True)
        return {
            "response_text": f"DEBUG_ERROR: {str(e)}", 
            "success": False,
            "intent": "ERROR"
        }

@router.post("/voice/dialog-response")
async def dialog_response(request: Request):
    """Handle UI-submitted data form for drafts (Invoices or Clients)."""
    payload = await request.json()
    session_id = payload.get("session_id")
    dialog_id = payload.get("dialog_id")
    
    from app.state.session_manager import session_manager
    session = session_manager.get_session(session_id)
    
    if not session:
        return {"success": False, "message": "Session expired."}
    
    form_fields = payload.get("fields", payload)
    
    # Identify which draft we are updating
    # Logic: Prefer dialog_id or locked_intent
    is_invoice = (dialog_id == "invoice_preview_form" or session.locked_intent == "INVOICE_CREATE")
    
    if is_invoice and session.invoice_draft:
        from app.voice_processor import VoiceContext
        from app.agents.finance_agent import finance_agent

        draft = session.invoice_draft
        # Update invoice fields
        for k, v in form_fields.items():
            if v is None: continue
            if k == "amount" or k == "total_amount": 
                try: draft.amount = float(v)
                except: pass
            elif k == "gst_percent":
                try: draft.gst_percent = float(v)
                except: pass
            elif k == "gst_applicable":
                draft.gst_applicable = str(v).lower() in ("true", "yes", "1")
            elif k == "due_date": draft.due_date = v
            elif k == "description" or k == "item_description" or k == "service_description": draft.item_description = v
            elif k == "item_type": draft.item_type = str(v).upper()
            elif k == "quantity":
                try: draft.quantity = int(v)
                except: pass
            elif k == "client_name": draft.client_name = v
            elif k == "client_id": draft.client_id = v
            elif k == "teamActionCode" or k == "team_action_code":
                draft.team_action_code = v
            
        session.invoice_draft = draft
        session_manager.save_session(session)
        voice_context = VoiceContext(
            session_id=session.session_id,
            user_id=session.user_id,
            org_uuid=session.org_id,
            business_id=session.business_id,
            raw_text="",
            extracted_entities=[],
        )
        follow_up = await finance_agent.handle_invoice_create(voice_context)
        message = follow_up.message if follow_up and follow_up.message else "Invoice draft updated."
        title = "Invoice Draft Updated"
        ui_event = follow_up.ui_event if follow_up and hasattr(follow_up, "ui_event") else None
    else:
        # Fallback to client
        if session.client_draft is None:
            session.client_draft = {}
        
        for key in ["name", "client_name", "company_name", "phone", "gst_number", "email", "address", "taxId", "phoneNumber", "teamActionCode"]:
            if key in form_fields and form_fields[key]:
                if key in ("name", "client_name", "company_name"): session.client_draft["client_name"] = form_fields[key]
                elif key in ("phoneNumber", "phone"): session.client_draft["phone"] = form_fields[key]
                elif key in ("taxId", "gst_number"): session.client_draft["gst_number"] = form_fields[key]
                else: session.client_draft[key] = form_fields[key]
        
        session_manager.save_session(session)
        message = "Client draft updated. Tell me 'Save Client' to finalize."
        title = "Client Draft Updated"
        ui_event = None

    session.dialog_pending = False
    session.dialog_id = None
    session_manager.save_session(session)
    
    return {
        "success": True,
        "message": message,
        "ui_event": ui_event or {
            "type": "toast",
            "variant": "success",
            "title": title,
            "message": message
        }
    }
 
