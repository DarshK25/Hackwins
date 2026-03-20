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
            clerk_org_id=request.org_id
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
    """Handle UI-submitted client data form."""
    payload = await request.json()
    session_id = payload.get("session_id")
    
    from app.state.session_manager import session_manager
    from app.voice_processor import voice_processor
    
    session = session_manager.get_session(session_id)
    # Check if session is brand new (missing metadata we set in process())
    if not session or not session.client_draft:
        logger.warning(f"dialog_response_failed_session_missing_or_draft_null: {session_id}")
        return {
            "success": False, 
            "message": "Session expired or Gateway reloaded. Please try again.",
            "error": "SESSION_EXPIRED"
        }
    
    # Merge form fields into draft (robust check for both flat and nested payloads)
    if session.client_draft is None:
        session.client_draft = {}
    
    form_fields = payload.get("fields", payload)
    # Support both flat and nested keys
    for key in ["phone", "gst_number", "email", "address", "description", "taxId", "phoneNumber"]:
        if key in form_fields and form_fields[key]:
            # Map canonical keys
            if key == "phoneNumber": session.client_draft["phone"] = form_fields[key]
            elif key == "taxId": session.client_draft["gst_number"] = form_fields[key]
            else: session.client_draft[key] = form_fields[key]
    
    session.dialog_pending = False
    session.dialog_id = None
    session_manager.save_session(session)
    
    # Finalize creation
    result = await voice_processor.finalize_client_create(session)
    
    return {
        "success": result.get("success", False),
        "message": result.get("response_text", "Client saved."),
        "ui_event": result.get("ui_event")
    }
 