from urllib import response
from groq import Groq, AsyncGroq
from groq.types.chat import ChatCompletion
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from typing import Optional, List, Dict, Any
import json
import re

from app.config import Settings
from app.utils.logger import get_logger

def extract_json(content: str) -> str:
    """
    Extract JSON from markdown code blocks or raw string
    """
    content = content.strip()
    
    # Try to find JSON block in markdown
    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
    if json_match:
        return json_match.group(1)
        
    return content

logger = get_logger(__name__)
settings = Settings()

class GroqClient:
    """
    A client for interacting with the Groq LLM API with retry and structured output.
    """
    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.async_client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        self.model = settings.GROQ_MODEL
        self.model_complex = settings.GROQ_MODEL_COMPLEX

    @retry(
        stop=stop_after_attempt(settings.LLM_MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Exception,)),
        before_sleep=lambda retry_state: logger.warning(
            "retrying_groq_call",
            attempt=retry_state.attempt_number,
            error=str(retry_state.outcome.exception()) if retry_state.outcome else None,
        ),
    )
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, str]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        use_complex_model: bool = False,
    ) -> ChatCompletion:
        """
        Call Groq chat completion API
        """
        model = self.model_complex if use_complex_model else self.model

        params = {
            "model": model,
            "messages": messages,
            "temperature": temperature or settings.LLM_TEMPERATURE,
            "max_tokens": max_tokens or settings.LLM_MAX_TOKENS,
        }
        
        if response_format:
            params["response_format"] = response_format

        if tools:
            params["tools"] = tools
        
        try:
            response = await self.async_client.chat.completions.create(**params)
            logger.info(
                "groq_response",
                finish_reason=response.choices[0].finish_reason,
                usage=response.usage.model_dump() if response.usage else None,
            )
            return response

        except Exception as e:
            logger.error(
                "groq_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise
    
    async def chat_completion_with_json(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Call Groq and parse JSON response
        """
        response = await self.chat_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        
        try:
            cleaned_content = extract_json(content)
            return json.loads(cleaned_content)
        except json.JSONDecodeError as e:
            logger.error(
                "groq_json_parse_error",
                error=str(e),
                content=content,
            )
            raise ValueError(f"Failed to parse JSON from LLM: {e}")
    
    async def chat_completion_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        tool_choice: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> ChatCompletion:
        """
        Call Groq with function calling (tools)
        """
        return await self.chat_completion(
            messages=messages,
            temperature=temperature,
            tools=tools,
            tool_choice=tool_choice,
        )
    
    async def simple_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Simple completion for quick tasks
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
            
        messages.append({"role": "user", "content": prompt})
        
        response = await self.chat_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return response.choices[0].message.content


# Singleton instance
groq_client = GroqClient()