"""
Voice API endpoint.
Processes voice input: Intent classification -> Entity extraction -> Agent routing.
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Dict, Any, List

from app.orchestrator.intent_classifier import IntentClassifier
from app.orchestrator.entity_extractor import EntityExtractor
from app.orchestration.agent_router import agent_router
from app.utils.logger import get_logger

from app.orchestration.agent_router import agent_router
from app.utils.logger import get_logger
from app.config import settings
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


@router.get("/voice/token")
async def get_voice_token(user_id: str = "user", room_name: str = None):
    """
    Generate a LiveKit access token for voice chat
    """
    try:
        if not settings.LIVEKIT_API_KEY or not settings.LIVEKIT_API_SECRET:
            raise HTTPException(status_code=500, detail="LiveKit not configured on server")

        # Generate a unique room name if not provided
        if not room_name:
            room_name = f"voice-{user_id}-{str(uuid.uuid4())[:8]}"

        # Create access token
        token = AccessToken(settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET) \
            .with_identity(user_id) \
            .with_name(user_id) \
            .with_grants(VideoGrants(
                room_join=True,
                room=room_name,
            ))

        return {
            "token": token.to_jwt(),
            "url": settings.LIVEKIT_URL,
            "room_name": room_name
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

        extracted_entities = await entity_extractor.extract(
            user_input=request.text,
            intent=intent,
            context=context,
        )

        entities_dict: Dict[str, Any] = {}
        for entity in extracted_entities.entities:
            entities_dict[entity.entity_type.value] = entity.value

        logger.info(
            "entities_extracted",
            entity_count=extracted_entities.total_entities,
            entities=list(entities_dict.keys()),
        )

        agent_response = await agent_router.route(
            intent=intent,
            entities=entities_dict,
            context=context,
        )

        response_text = agent_response.message
        max_length = context.get("max_response_length", 200)
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
