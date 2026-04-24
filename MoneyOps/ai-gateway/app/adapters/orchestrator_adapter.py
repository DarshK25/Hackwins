"""
Orchestrator adapter: logs activities and voice conversations to backend.
Called by the voice processor after each successful agent action.
"""
from typing import Optional, List
from app.utils.logger import get_logger
from app.adapters.backend_adapter import get_backend_adapter

logger = get_logger(__name__)

# Maps voice intent → human-readable agent name
INTENT_TO_AGENT = {
    "INVOICE_CREATE": "Finance Agent",
    "INVOICE_UPDATE": "Finance Agent",
    "INVOICE_QUERY": "Finance Agent",
    "BALANCE_CHECK": "Finance Agent",
    "ANALYTICS_QUERY": "Finance Agent",
    "BUSINESS_HEALTH_CHECK": "Finance Agent",
    "PAYMENT_RECORD": "Finance Agent",
    "EXPENSE_CREATE": "Finance Agent",
    "EXPENSE_QUERY": "Finance Agent",
    "CLIENT_CREATE": "Sales Agent",
    "CLIENT_QUERY": "Sales Agent",
    "CLIENT_HISTORY": "Sales Agent",
    "GENERAL_QUERY": "General Agent",
    "MARKET_NEWS": "Market Agent",
    "TREND_ANALYSIS": "Market Agent",
    "GROWTH_STRATEGY": "Market Agent",
    "COMPLIANCE_CHECK": "Compliance Agent",
    "UNKNOWN": "Orchestrator",
    "ERROR": "Orchestrator",
}

# Maps intent → activity type
INTENT_TO_TYPE = {
    "INVOICE_CREATE": "INVOICE_CREATED",
    "INVOICE_UPDATE": "INVOICE_UPDATED",
    "INVOICE_QUERY": "QUERY_ANSWERED",
    "BALANCE_CHECK": "QUERY_ANSWERED",
    "ANALYTICS_QUERY": "QUERY_ANSWERED",
    "BUSINESS_HEALTH_CHECK": "QUERY_ANSWERED",
    "PAYMENT_RECORD": "PAYMENT_RECORDED",
    "EXPENSE_CREATE": "EXPENSE_CREATED",
    "EXPENSE_QUERY": "QUERY_ANSWERED",
    "CLIENT_CREATE": "CLIENT_CREATED",
    "CLIENT_QUERY": "QUERY_ANSWERED",
    "CLIENT_HISTORY": "QUERY_ANSWERED",
    "GENERAL_QUERY": "QUERY_ANSWERED",
    "MARKET_NEWS": "QUERY_ANSWERED",
    "TREND_ANALYSIS": "QUERY_ANSWERED",
    "GROWTH_STRATEGY": "QUERY_ANSWERED",
    "COMPLIANCE_CHECK": "QUERY_ANSWERED",
}


class OrchestratorAdapter:
    """Thin async client to log orchestrator activities and voice conversations."""

    def _adapter(self):
        return get_backend_adapter()

    async def log_activity(
        self,
        org_id: str,
        user_id: str,
        intent: str,
        description: str,
        status: str = "COMPLETED",
        session_id: Optional[str] = None,
    ) -> bool:
        """Fire-and-forget: log an agent action as an activity."""
        try:
            resp = await self._adapter().report_orchestrator_activity(
                org_id=org_id,
                user_id=user_id,
                intent=intent,
                description=description,
                status=status,
                session_id=session_id,
                agent_name=INTENT_TO_AGENT.get(intent, "Orchestrator"),
                activity_type=INTENT_TO_TYPE.get(intent, "QUERY_ANSWERED"),
            )
            if not resp.success:
                logger.warning("orchestrator_activity_log_failed", error=resp.error, intent=intent)
            return resp.success
        except Exception as e:
            logger.error("orchestrator_activity_log_error", error=str(e))
            return False

    async def start_conversation(self, org_id: str, user_id: str, session_id: str) -> bool:
        """Called when a voice session begins."""
        try:
            resp = await self._adapter()._request(
                "POST",
                "/api/orchestrator/conversations/start",
                data={"sessionId": session_id},
                org_id=org_id,
                user_id=user_id,
            )
            return resp.success
        except Exception as e:
            logger.error("orchestrator_start_conversation_error", error=str(e))
            return False

    async def add_message(
        self,
        org_id: str,
        user_id: str,
        session_id: str,
        role: str,
        content: str,
        intent: Optional[str] = None,
    ) -> bool:
        """Append a single turn (user or assistant) to the conversation record."""
        try:
            resp = await self._adapter()._request(
                "POST",
                "/api/orchestrator/conversations/message",
                data={
                    "sessionId": session_id,
                    "role": role,
                    "content": content,
                    "intent": intent,
                },
                org_id=org_id,
                user_id=user_id,
            )
            return resp.success
        except Exception as e:
            logger.error("orchestrator_add_message_error", error=str(e))
            return False

    async def end_conversation(
        self,
        org_id: str,
        user_id: str,
        session_id: str,
        summary: Optional[str],
        tasks_generated: Optional[List[str]] = None,
    ) -> bool:
        """Called when the voice session disconnects."""
        try:
            resp = await self._adapter()._request(
                "POST",
                "/api/orchestrator/conversations/end",
                data={
                    "sessionId": session_id,
                    "summary": summary or "Voice conversation completed",
                    "tasksGenerated": tasks_generated or [],
                },
                org_id=org_id,
                user_id=user_id,
            )
            return resp.success
        except Exception as e:
            logger.error("orchestrator_end_conversation_error", error=str(e))
            return False


# Singleton
orchestrator_adapter = OrchestratorAdapter()
