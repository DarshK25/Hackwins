"""
Multi-Provider LLM Client - Task-based routing to optimal providers.
Routes tasks based on provider strengths, with intelligent fallback.

Provider Capabilities:
- Groq: Fast inference (~2800 tokens/sec), best for real-time voice
- Cerebras: High volume (14,400/day), best for batch operations
- Gemini: 1M token context window, best for long documents/analysis
- GitHub Models: SOTA models (GPT-4o, Claude), best for complex reasoning
"""
from typing import Optional, List, Dict, Any, Tuple
import json
import re
import httpx
from enum import Enum
from dataclasses import dataclass, field
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from app.config import Settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = Settings()


class TaskType(str, Enum):
    """Task types for intelligent provider routing"""
    REALTIME = "realtime"        # Voice, quick responses (< 2s)
    HIGH_VOLUME = "high_volume"    # Batch ops, testing (many req/min)
    LONG_CONTEXT = "long_context"  # Long docs, big prompts (> 32K tokens)
    COMPLEX_REASONING = "complex"  # Strategic analysis, SOTA models
    JSON_PARSING = "json"          # Structured output tasks
    SIMPLE = "simple"            # Default completion


@dataclass
class ProviderCapability:
    """What a provider is good at"""
    name: str
    supports_json_mode: bool = False
    max_context_tokens: int = 8192
    avg_speed_tps: int = 100  # tokens per second
    daily_quota: int = 1000
    priority_for: List[TaskType] = field(default_factory=list)


class MultiProviderClient:
    """
    Intelligent LLM client that routes tasks to the best provider.
    
    Routing logic:
    - REALTIME → Groq (fastest inference)
    - HIGH_VOLUME → Cerebras (14,400/day)
    - LONG_CONTEXT → Gemini (1M token window)
    - COMPLEX_REASONING → GitHub Models (GPT-4o, Claude)
    - JSON_PARSING → Gemini (reliable structured output)
    - SIMPLE → Groq (default)
    """
    
    def __init__(self):
        self.providers: Dict[str, Dict[str, Any]] = {}
        self.capabilities: Dict[str, ProviderCapability] = {}
        self._http_client = httpx.AsyncClient(timeout=30.0)
        self._setup_providers()
        
    def _setup_providers(self):
        """Configure all available providers with their capabilities"""
        
        # Groq - Fastest inference
        if settings.GROQ_API_KEY:
            self.providers["groq"] = {
                "api_key": settings.GROQ_API_KEY,
                "base_url": "https://api.groq.com/openai/v1",
                "model": settings.GROQ_MODEL,
                "model_complex": settings.GROQ_MODEL_COMPLEX,
            }
            self.capabilities["groq"] = ProviderCapability(
                name="groq",
                supports_json_mode=True,
                max_context_tokens=8192,
                avg_speed_tps=2800,  # Fastest
                daily_quota=14400,
                priority_for=[TaskType.REALTIME, TaskType.SIMPLE],
            )
            
        # Cerebras - Highest quota
        cerebras_key = getattr(settings, "CEREBRAS_API_KEY", None)
        if cerebras_key:
            self.providers["cerebras"] = {
                "api_key": cerebras_key,
                "base_url": "https://api.cerebras.ai/v1",
                "model": "llama3.1-8b",
                "model_complex": "llama3.1-70b",
            }
            self.capabilities["cerebras"] = ProviderCapability(
                name="cerebras",
                supports_json_mode=True,
                max_context_tokens=8192,
                avg_speed_tps=1800,
                daily_quota=14400,  # Highest
                priority_for=[TaskType.HIGH_VOLUME],
            )
            
        # Gemini - Longest context
        gemini_key = getattr(settings, "GEMINI_API_KEY", None)
        if gemini_key:
            self.providers["gemini"] = {
                "api_key": gemini_key,
                "model": "gemini-1.5-flash",
                "model_complex": "gemini-1.5-pro",
            }
            self.capabilities["gemini"] = ProviderCapability(
                name="gemini",
                supports_json_mode=True,
                max_context_tokens=1_000_000,  # 1M tokens!
                avg_speed_tps=500,
                daily_quota=1500,
                priority_for=[TaskType.LONG_CONTEXT, TaskType.JSON_PARSING],
            )
            
        # GitHub Models - SOTA models
        github_key = getattr(settings, "GITHUB_API_KEY", None)
        if github_key:
            self.providers["github"] = {
                "api_key": github_key,
                "base_url": "https://models.inference.ai.azure.com",
                "model": "gpt-4o",
                "model_complex": "claude-3.5-sonnet",
            }
            self.capabilities["github"] = ProviderCapability(
                name="github",
                supports_json_mode=True,
                max_context_tokens=128000,
                avg_speed_tps=300,
                daily_quota=150,
                priority_for=[TaskType.COMPLEX_REASONING],
            )
            
        if not self.providers:
            raise RuntimeError(
                "No LLM providers configured. "
                "Set GROQ_API_KEY, CEREBRAS_API_KEY, GEMINI_API_KEY, or GITHUB_API_KEY"
            )
            
        logger.info(
            "multi_provider_initialized",
            providers=list(self.providers.keys()),
            routing_strategy="task_based",
        )
        
    def _get_providers_for_task(self, task_type: TaskType) -> List[str]:
        """
        Get providers sorted by suitability for task.
        First: primary provider for this task type.
        Then: fallback providers.
        """
        primary = []
        fallback = []
        
        for name, cap in self.capabilities.items():
            if task_type in cap.priority_for:
                primary.append(name)
            else:
                fallback.append(name)
                
        return primary + fallback
        
    def _classify_task(
        self,
        messages: List[Dict],
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict] = None,
    ) -> TaskType:
        """Automatically classify the task based on input"""
        
        # Check if JSON mode requested
        if response_format and response_format.get("type") == "json_object":
            return TaskType.JSON_PARSING
            
        # Estimate context size
        total_chars = sum(len(m.get("content", "")) for m in messages)
        if total_chars > 50000:  # ~12K tokens
            return TaskType.LONG_CONTEXT
            
        # Check for complex reasoning keywords
        full_text = " ".join(m.get("content", "") for m in messages).lower()
        complex_keywords = [
            "analyze", "strategy", "compare", "evaluate", "reasoning",
            "swot", "competitive", "forecast", "diagnose"
        ]
        if any(kw in full_text for kw in complex_keywords):
            return TaskType.COMPLEX_REASONING
            
        # High volume indicators (batch operations)
        if "batch" in full_text or max_tokens and max_tokens > 1000:
            return TaskType.HIGH_VOLUME
            
        # Default to simple (Groq fast)
        return TaskType.SIMPLE
        
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, str]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        use_complex_model: bool = False,
        task_type: Optional[TaskType] = None,
    ) -> Dict[str, Any]:
        """
        Chat completion with intelligent task-based routing.
        
        Args:
            task_type: Override automatic task classification
        """
        # Classify task if not specified
        if task_type is None:
            task_type = self._classify_task(messages, max_tokens, response_format)
            
        # Get providers sorted by suitability
        provider_names = self._get_providers_for_task(task_type)
        
        last_error = None
        for provider_name in provider_names:
            if provider_name not in self.providers:
                continue
                
            try:
                result = await self._call_provider(
                    provider_name=provider_name,
                    messages=messages,
                    temperature=temperature or 0.3,
                    max_tokens=max_tokens or 2000,
                    response_format=response_format,
                    use_complex=use_complex_model,
                )
                
                logger.info(
                    "llm_completion_success",
                    provider=provider_name,
                    task_type=task_type.value,
                )
                return result
                
            except Exception as e:
                error_str = str(e).lower()
                if "429" in error_str or "rate" in error_str:
                    logger.warning(
                        "llm_rate_limit",
                        provider=provider_name,
                        task_type=task_type.value,
                        error=str(e),
                    )
                    continue  # Try next provider
                    
                last_error = e
                logger.error(
                    "llm_error",
                    provider=provider_name,
                    error=str(e),
                )
                break  # Different error, don't fallback
                
        # All providers failed
        if last_error:
            raise last_error
        raise RuntimeError(f"All providers failed for task type: {task_type.value}")
        
    async def _call_provider(
        self,
        provider_name: str,
        messages: List[Dict],
        temperature: float,
        max_tokens: int,
        response_format: Optional[Dict],
        use_complex: bool,
    ) -> Dict[str, Any]:
        """Call specific provider"""
        
        if provider_name == "gemini":
            return await self._call_gemini(
                messages, temperature, max_tokens, response_format, use_complex
            )
        elif provider_name == "github":
            return await self._call_openai_compatible(
                provider_name, messages, temperature, max_tokens, response_format, use_complex
            )
        else:
            # Groq, Cerebras (OpenAI-compatible)
            return await self._call_openai_compatible(
                provider_name, messages, temperature, max_tokens, response_format, use_complex
            )
            
    async def _call_openai_compatible(
        self,
        provider_name: str,
        messages: List[Dict],
        temperature: float,
        max_tokens: int,
        response_format: Optional[Dict],
        use_complex: bool,
    ) -> Dict[str, Any]:
        """Call OpenAI-compatible API (Groq, Cerebras, GitHub)"""
        provider = self.providers[provider_name]
        model = provider["model_complex"] if use_complex else provider["model"]
        
        url = f"{provider['base_url']}/chat/completions"
        headers = {
            "Authorization": f"Bearer {provider['api_key']}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        if response_format:
            payload["response_format"] = response_format
            
        resp = await self._http_client.post(url, headers=headers, json=payload, timeout=30.0)
        resp.raise_for_status()
        return resp.json()
        
    async def _call_gemini(
        self,
        messages: List[Dict],
        temperature: float,
        max_tokens: int,
        response_format: Optional[Dict],
        use_complex: bool,
    ) -> Dict[str, Any]:
        """Call Gemini API and convert to OpenAI format"""
        provider = self.providers["gemini"]
        model = provider["model_complex"] if use_complex else provider["model"]
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={provider['api_key']}"
        
        # Convert messages to Gemini format
        contents = []
        system_prompt = ""
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                system_prompt = content
            elif role == "user":
                parts = []
                if system_prompt:
                    parts.append({"text": f"[System: {system_prompt}]"})
                    system_prompt = ""
                parts.append({"text": content})
                contents.append({"role": "user", "parts": parts})
            elif role == "assistant":
                contents.append({"role": "model", "parts": [{"text": content}]})
                
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            }
        }
        
        resp = await self._http_client.post(url, json=payload, timeout=30.0)
        resp.raise_for_status()
        gemini_resp = resp.json()
        
        # Convert to OpenAI format
        try:
            text = gemini_resp["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            text = ""
            
        return {
            "choices": [{
                "message": {"role": "assistant", "content": text},
                "finish_reason": "stop",
            }],
            "model": model,
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }
        
    async def chat_completion_with_json(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        task_type: Optional[TaskType] = None,
    ) -> Dict[str, Any]:
        """Call LLM and parse JSON response"""
        # Force JSON parsing task type
        task_type = TaskType.JSON_PARSING
        
        try:
            response = await self.chat_completion(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
                task_type=task_type,
            )
        except Exception:
            # Fallback: ask for JSON in prompt
            json_messages = messages.copy()
            if json_messages:
                last_msg = json_messages[-1]
                last_msg["content"] = f"{last_msg.get('content', '')}\n\nRespond with valid JSON only."
            response = await self.chat_completion(
                messages=json_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                task_type=task_type,
            )
            
        content = response["choices"][0]["message"]["content"]
        
        try:
            cleaned_content = extract_json(content)
            return json.loads(cleaned_content)
        except json.JSONDecodeError as e:
            logger.error("llm_json_parse_error", error=str(e), content=content)
            raise ValueError(f"Failed to parse JSON from LLM: {e}")
            
    async def chat_completion_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        tool_choice: Optional[str] = None,
        temperature: Optional[float] = None,
        task_type: Optional[TaskType] = None,
    ) -> Dict[str, Any]:
        """Call LLM with function calling"""
        return await self.chat_completion(
            messages=messages,
            temperature=temperature,
            tools=tools,
            tool_choice=tool_choice,
            task_type=task_type or TaskType.SIMPLE,
        )
        
    async def simple_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        task_type: Optional[TaskType] = None,
    ) -> str:
        """Simple completion for quick tasks"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = await self.chat_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            task_type=task_type or TaskType.SIMPLE,
        )
        
        return response["choices"][0]["message"]["content"]


def extract_json(content: str) -> str:
    """Extract JSON from markdown code blocks or raw string"""
    content = content.strip()
    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
    if json_match:
        return json_match.group(1)
    return content


# Singleton instance
llm_client = MultiProviderClient()
