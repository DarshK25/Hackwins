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
        logger.error("voice_process_failed", error=str(e), exc_info=True)
        return {
            "response_text": "I'm having trouble processing that right now. Could you repeat?", 
            "success": False,
            "intent": "ERROR"
        }
 