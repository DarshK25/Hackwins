import pytest
from unittest.mock import AsyncMock, MagicMock
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

@pytest.fixture
def mock_groq_response():
    """Helper to create a mock Groq response"""
    def _create_response(content):
        mock_choice = MagicMock()
        mock_choice.message.content = content
        mock_choice.finish_reason = "stop"
        
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage.model_dump.return_value = {"total_tokens": 100}
        return mock_response
    return _create_response

@pytest.mark.asyncio
async def test_simple_prompt(mocker, mock_groq_response):
    # Mock parameters
    request = PromptRequest(
        prompt="What is GST in India?",
        temperature=0.2
    )
    
    # Setup mock
    expected_content = "GST is a tax in India"
    mock_response = mock_groq_response(expected_content)
    
    # We patch the underlying chat_completion method to avoid network calls
    mocker.patch.object(
        groq_client, 
        'chat_completion', 
        new=AsyncMock(return_value=mock_response)
    )

    response = await groq_client.simple_completion(
        prompt=request.prompt,
        temperature=request.temperature,
    )

    assert response == expected_content
    # Verify call arguments
    groq_client.chat_completion.assert_called_once()
    call_args = groq_client.chat_completion.call_args
    assert call_args.kwargs['messages'][0]['content'] == request.prompt

@pytest.mark.asyncio
async def test_intent_classification(mocker, mock_groq_response):
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
    
    # Mock JSON response
    mock_content = '{"intent": "tax_check_status", "confidence": 0.95}'
    mock_response = mock_groq_response(mock_content)
    
    mocker.patch.object(
        groq_client, 
        'chat_completion', 
        new=AsyncMock(return_value=mock_response)
    )

    messages = [
        {"role": "system", "content": "You are an intent classifier."},
        {"role": "user", "content": prompt},
    ]

    response = await groq_client.chat_completion_with_json(
        messages=messages,
        temperature=0.3,
    )

    assert response["intent"] == "tax_check_status"
    assert response["confidence"] == 0.95

@pytest.mark.asyncio
async def test_entity_extraction(mocker, mock_groq_response):
    request = EntityExtractionRequest(
        user_input="I paid ₹50,000 rent in January",
        intent="expense_tracking"
    )
    
    # Mock JSON response with markdown wrapper to test sanitization
    mock_content = '''```json
    {
        "amounts": [{"value": 50000, "currency": "INR"}],
        "dates": [{"value": "January"}]
    }
    ```'''
    mock_response = mock_groq_response(mock_content)
    
    mocker.patch.object(
        groq_client, 
        'chat_completion', 
        new=AsyncMock(return_value=mock_response)
    )

    prompt = ENTITY_EXTRACTION_PROMPT.render(
        user_input=request.user_input,
        intent=request.intent,
        current_date="2024-01-01",
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

    assert response["amounts"][0]["value"] == 50000
    assert response["amounts"][0]["currency"] == "INR"
