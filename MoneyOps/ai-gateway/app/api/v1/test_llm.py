"""
LLM and orchestration diagnostic endpoints used for integration testing.
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.llm.groq_client import groq_client
from app.orchestration.intent_classifier import IntentClassifier
from app.orchestration.entity_extractor import EntityExtractor
from app.schemas.intents import Intent
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)

intent_classifier = IntentClassifier()
entity_extractor = EntityExtractor()


class SimplePromptRequest(BaseModel):
    prompt: str
    temperature: Optional[float] = 0.3
    max_tokens: Optional[int] = 300


class IntentClassificationRequest(BaseModel):
    user_input: str
    conversation_history: List[Dict[str, Any]] = Field(default_factory=list)
    business_context: Dict[str, Any] = Field(default_factory=dict)


class EntityExtractionRequest(BaseModel):
    user_input: str
    intent: str
    context: Dict[str, Any] = Field(default_factory=dict)


@router.post("/test/simple-prompt")
async def test_simple_prompt(request: SimplePromptRequest):
    try:
        completion = await groq_client.simple_completion(
            prompt=request.prompt,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
        return {
            "success": True,
            "prompt": request.prompt,
            "completion": completion,
        }
    except Exception as e:
        logger.error("test_simple_prompt_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Simple prompt failed: {str(e)}")


@router.get("/test/health-llm")
async def test_health_llm():
    try:
        completion = await groq_client.simple_completion(
            prompt="Reply with exactly: OK",
            temperature=0.0,
            max_tokens=10,
        )
        return {
            "status": "healthy",
            "llm_response": completion.strip(),
            "model": groq_client.model,
        }
    except Exception as e:
        logger.error("test_health_llm_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=503, detail=f"LLM health check failed: {str(e)}")


@router.post("/test/intent-classification")
async def test_intent_classification(request: IntentClassificationRequest):
    try:
        classification = await intent_classifier.classify(
            user_input=request.user_input,
            conversation_history=request.conversation_history,
            business_context=request.business_context,
        )
        return {
            "success": True,
            "user_input": request.user_input,
            "classification": {
                "intent": classification.intent.value,
                "confidence": float(classification.confidence),
                "reasoning": classification.reasoning,
                "category": classification.category.value,
                "primary_agent": classification.primary_agent.value,
            },
        }
    except Exception as e:
        logger.error("test_intent_classification_error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Intent classification failed: {str(e)}",
        )


@router.post("/test/entity-extraction")
async def test_entity_extraction(request: EntityExtractionRequest):
    try:
        try:
            intent_enum = Intent(request.intent)
        except Exception:
            raise HTTPException(status_code=400, detail=f"Invalid intent: {request.intent}")

        extracted = await entity_extractor.extract(
            user_input=request.user_input,
            intent=intent_enum,
            context=request.context,
        )

        entities = [
            {
                "type": entity.entity_type.value,
                "value": entity.value,
                "confidence": float(entity.confidence),
                "method": entity.extraction_method,
            }
            for entity in extracted.entities
        ]

        return {
            "success": True,
            "user_input": request.user_input,
            "intent": intent_enum.value,
            "extracted_entities": {
                "entities": entities,
                "total": extracted.total_entities,
                "confidence_score": float(extracted.confidence_score),
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("test_entity_extraction_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Entity extraction failed: {str(e)}")
