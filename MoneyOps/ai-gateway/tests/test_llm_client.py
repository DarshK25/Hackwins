import pytest
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from app.llm.groq_client import groq_client
from app.prompts.base_prompts import (
    build_intent_classification_prompt,
    ENTITY_EXTRACTION_PROMPT,
)

# Test Models
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

@pytest.mark.asyncio
async def test_simple_prompt():
    request = PromptRequest(
        prompt="What is GST in India?",
        temperature=0.2
    )

    response = await groq_client.simple_completion(
        prompt=request.prompt,
        temperature=request.temperature,
    )

    assert response is not None
    assert isinstance(response, str)

@pytest.mark.asyncio
async def test_intent_classification():
    request = IntentRequest(
        user_input="How do I file GST?",
        industry="retail",
        has_gst=True
    )

    prompt = build_intent_classification_prompt(
        user_input=request.user_input,
        industry=request.industry,
        has_gst=request.has_gst,
    )

    messages = [
        {"role": "system", "content": "You are an intent classifier."},
        {"role": "user", "content": prompt},
    ]

    response = await groq_client.chat_completion_with_json(
        messages=messages,
        temperature=0.3,
    )

    assert response is not None
    assert isinstance(response, dict)

@pytest.mark.asyncio
async def test_entity_extraction():
    request = EntityExtractionRequest(
        user_input="I paid ₹50,000 rent in January",
        intent="expense_tracking"
    )

    prompt = ENTITY_EXTRACTION_PROMPT.render(
        user_input=request.user_input,
        intent=request.intent,
        current_date=datetime.now().strftime("%Y-%m-%d"),
        timezone="Asia/Kolkata",
    )

    messages = [
        {"role": "system", "content": "You are an entity extractor. Always respond with valid JSON."},
        {"role": "user", "content": prompt},
    ]

    response = await groq_client.chat_completion_with_json(
        messages=messages,
        temperature=0.3,
    )

    assert response is not None
    assert isinstance(response, dict)
