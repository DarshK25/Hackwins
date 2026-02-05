"""
AI Gateway HTTP Client
Calls your teammate's AI Gateway service
"""
import httpx
from typing import Dict, Any, Optional, List

from app.config import settings
from app.utils.logger import get_logger
from app.utils.retry import retry_on_http_error

logger = get_logger(__name__)


class AIGatewayClient:
    """Client for AI Gateway service"""
    
    def __init__(self):
        self.base_url = settings.AI_GATEWAY_URL
        self.timeout = settings.AI_GATEWAY_TIMEOUT
        
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
        )
    
    @retry_on_http_error(max_attempts=3)
    async def process_voice_input(
        self,
        text: str,
        user_id: str,
        org_id: str,
        session_id: str,
        conversation_history: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """Send voice input to AI Gateway"""
        logger.info(
            "calling_ai_gateway",
            text_preview=text[:100],
            user_id=user_id,
        )
        
        payload = {
            "user_id": user_id,
            "org_id": org_id,
            "text": text,
            "session_id": session_id,
            "context": {
                "channel": "voice",
                "prefer_short_response": True,
                "max_response_length": 200,
            },
            "conversation_history": conversation_history or [],
        }
        
        try:
            response = await self.client.post(
                "/api/v1/voice/process",
                json=payload,
            )
            
            response.raise_for_status()
            result = response.json()
            
            logger.info(
                "ai_gateway_response",
                intent=result.get("intent"),
                confidence=result.get("confidence"),
            )
            
            return result
            
        except httpx.TimeoutException:
            logger.error("ai_gateway_timeout")
            return self._timeout_fallback(text)
        
        except httpx.HTTPStatusError as e:
            logger.error(
                "ai_gateway_http_error",
                status=e.response.status_code,
            )
            return self._error_fallback()
        
        except Exception as e:
            logger.error("ai_gateway_error", error=str(e))
            return self._error_fallback()
    
    def _timeout_fallback(self, text: str) -> Dict[str, Any]:
        """Fallback when AI Gateway times out"""
        return {
            "response_text": "Processing your request. Please hold on.",
            "intent": "TIMEOUT",
            "confidence": 0.0,
        }
    
    def _error_fallback(self) -> Dict[str, Any]:
        """Fallback when AI Gateway fails"""
        return {
            "response_text": "I'm having trouble right now. Please try again.",
            "intent": "ERROR",
            "confidence": 0.0,
        }
    
    async def health_check(self) -> bool:
        """Check if AI Gateway is healthy"""
        try:
            response = await self.client.get("/health", timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False
    
    async def close(self):
        """Cleanup"""
        await self.client.aclose()


# Singleton
ai_gateway_client = AIGatewayClient()