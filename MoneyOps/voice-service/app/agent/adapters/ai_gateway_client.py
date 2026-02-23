"""
AI Gateway HTTP Client
Calls your teammate's AI Gateway service

Changes (2026-02):
  - Separate connect_timeout vs read_timeout: connect failures surface in 3s,
    but we give the AI pipeline up to 15s to respond (voice requests can be slow)
  - Retry removed from process_voice_input: retrying a slow AI call just doubles
    latency. Instead, we fail fast with a friendly message and let the user retry naturally.
  - health_check timeout reduced to 3s
"""
import httpx
from typing import Dict, Any, Optional, List

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AIGatewayClient:
    """Client for AI Gateway service"""

    def __init__(self):
        self.base_url = settings.AI_GATEWAY_URL

        # Use separate connect vs read timeouts:
        #   - connect: 5s — detect unreachable gateway quickly
        #   - read: AI_GATEWAY_TIMEOUT — give pipeline time to respond
        #   - write: 5s — request payloads are small
        timeout = httpx.Timeout(
            connect=5.0,
            read=float(settings.AI_GATEWAY_TIMEOUT),
            write=5.0,
            pool=5.0,
        )

        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            # Keep connections alive between turns — avoids TCP handshake on each turn
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )

    async def process_voice_input(
        self,
        text: str,
        user_id: str,
        org_id: str,
        session_id: str,
        conversation_history: Optional[List[Dict]] = None,
        auth_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send voice input to AI Gateway, forwarding the user's JWT if available.

        NOTE: No retry here — retrying a slow AI call adds latency on top of latency.
        If the gateway is unreachable, we fall back immediately with a voice-friendly message.
        """
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

        headers = {}
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"

        try:
            response = await self.client.post(
                "/api/v1/voice/process",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            result = response.json()

            logger.info(
                "ai_gateway_response",
                intent=result.get("intent"),
                confidence=result.get("confidence"),
            )

            return result

        except httpx.ConnectError:
            logger.error("ai_gateway_unreachable", url=self.base_url)
            return self._error_fallback("I'm having trouble connecting right now. Please try again in a moment.")

        except httpx.TimeoutException:
            logger.error("ai_gateway_timeout", timeout=settings.AI_GATEWAY_TIMEOUT)
            return self._error_fallback("That took too long. Could you try again?")

        except httpx.HTTPStatusError as e:
            logger.error("ai_gateway_http_error", status=e.response.status_code)
            return self._error_fallback()

        except Exception as e:
            logger.error("ai_gateway_error", error=str(e))
            return self._error_fallback()

    def _error_fallback(self, message: str = "I'm having trouble right now. Please try again.") -> Dict[str, Any]:
        """Return a voice-friendly fallback response"""
        return {
            "response_text": message,
            "intent": "ERROR",
            "confidence": 0.0,
        }

    async def health_check(self) -> bool:
        """Check if AI Gateway is healthy"""
        try:
            response = await self.client.get("/api/v1/health", timeout=3.0)
            return response.status_code == 200
        except Exception:
            return False

    async def close(self):
        """Cleanup"""
        await self.client.aclose()


# Singleton
ai_gateway_client = AIGatewayClient()