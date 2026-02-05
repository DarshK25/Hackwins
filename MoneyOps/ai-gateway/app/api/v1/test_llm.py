import pytest
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.llm.groq_client import groq_client
from app.prompts.base_prompts import (
    build_system_prompt,
    build_intent_classification_prompt,
    ENTITY_EXTRACTION_PROMPT,
)
from app.utils.logger import get_logger, logger

router = APIRouter()
logger = get_logger(__name__)

class PromptRequest(BaseModel):
    """Simple prompt test"""
    prompt: str
    temperature: Optional[float] = 0.3

class IntentRequest(BaseModel):
    """Intent classification test"""
    user_input: str
    industry: Optional[str] = "IT & Software"
    has_gst: Optional[bool] = True

class EntityExtractionRequest(BaseModel):
    """Entity extraction test"""
    user_input: str
    intent: str

@router.post("/test/simple-prompt")
@pytest.mark.asyncio
async def test_simple_prompt(request: PromptRequest):
    """
    Test basic Groq completion
    """
    try:
        response = await groq_client.simple_completion(
            prompt=request.prompt,
            temperature=request.temperature,
        )
        return {
            "success": True,
            "prompt": request.prompt,
            "response": response,
            "model": groq_client.model,
        }
    except Exception as e:
        logger.error("test_prompt_error", error=str(e))
        raise HTTPException(status_code=500, detail="Error processing prompt")
    
@router.post("/test/intent-classification")
@pytest.mark.asyncio
async def test_intent_classification(request: IntentRequest):
    """
    Test intent classification prompt
    """
    try:
        # Build prompt
        prompt = build_intent_classification_prompt(
            user_input=request.user_input,
            industry=request.industry,
            has_gst=request.has_gst,
        )
        # Call LLM
        messages = [
            {"role": "system", "content": "You are an intent classifier."},
            {"role": "user", "content": prompt},
        ]
        response = await groq_client.chat_completion_with_json(
            messages=messages,
            temperature=0.3,
        )
        return {
            "success": True,
            "user_input": request.user_input,
            "classification" : response,
        }
    except Exception as e:
        logger.error("test_intent_classification_error", error=str(e))
        raise HTTPException(status_code=500, detail="Error processing intent classification")
    
@router.post("/test/entity-extraction")
@pytest.mark.asyncio
async def test_entity_extraction(request: EntityExtractionRequest):
    """
    Test entity extraction prompt
    """
    try:
        # Build prompt
        prompt = ENTITY_EXTRACTION_PROMPT.render(
            user_input=request.user_input,
            intent=request.intent,
            current_date=datetime.now().strftime("%Y-%m-%d"),
            timezone="Asia/Kolkata",
        )
        logger.info("entity_extraction_prompt", prompt=prompt)
        
        # Call LLM
        messages = [
            {"role": "system", "content": "You are an entity extractor. Always respond with valid JSON."},
            {"role": "user", "content": prompt},
        ]
        response = await groq_client.chat_completion_with_json(
            messages=messages,
            temperature=0.3,
        )
        return {
            "success": True,
            "user_input": request.user_input,
            "extracted_entities" : response,
        }
    except Exception as e:
        logger.error("test_entity_extraction_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing entity extraction: {str(e)}")
    
@router.get("/test/health-llm")
async def health_check_llm():
    """
    Health check for LLM connectivity
    """
    try:
        response = await groq_client.simple_completion(
            prompt="Say 'OK' if you can hear me.",
            temperature=0,
            max_tokens=10,
        )
        return {
            "status": "healthy",
            "llm_response": response.strip(),
            "model": groq_client.model,
        }
    except Exception as e:
        logger.error("health_check_llm_error", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e),
        }