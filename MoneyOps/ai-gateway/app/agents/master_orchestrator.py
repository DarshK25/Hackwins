"""
Master Orchestrator - Routes to TRUE executors using LLM-driven selection.
Replaces keyword matching with intelligent routing for agent-native execution.
"""
from typing import Dict, Any, List, Optional
import asyncio
import time

from app.agents.base_executor import (
    FinanceExecutor,
    ComplianceExecutor,
    CollectionsExecutor,
    TReDSExecutor,
    ExecutionState,
    AgentRole,
)
from app.llm.multi_provider import llm_client
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MasterOrchestrator:
    """
    TRUE agent-native orchestrator that routes to executors based on LLM analysis.
    Executors make REAL API calls - no simulations.
    """

    def __init__(self):
        self.executors = {
            AgentRole.FINANCE_OPS: FinanceExecutor(),
            AgentRole.COMPLIANCE: ComplianceExecutor(),
            AgentRole.COLLECTIONS: CollectionsExecutor(),
            AgentRole.TREDS: TReDSExecutor(),
        }
        self.llm = llm_client
        logger.info(
            "master_orchestrator_initialized",
            executors=list(self.executors.keys()),
        )

    async def _select_executor_llm(self, user_message: str) -> AgentRole:
        """
        Use LLM to determine which executor should handle the request.
        Replaces keyword matching with intelligent routing.
        """
        system_prompt = """You are a routing agent for a financial SaaS platform.
Determine which executor should handle the user's request.

Executors:
- finance_ops: Invoices, payments, expenses, financial summaries, balances
- compliance: GST filing, tax compliance, TDS, invoice templates
- collections: Payment reminders, WhatsApp/SMS collections, overdue invoices
- treds: Invoice discounting, working capital, TReDS registration

Respond with ONLY the executor name (finance_ops, compliance, collections, or treds)."""

        try:
            response = await self.llm.agenerate(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                max_tokens=20,
                temperature=0.1,
            )
            executor_name = response.strip().lower()

            # Map to AgentRole
            role_map = {
                "finance_ops": AgentRole.FINANCE_OPS,
                "compliance": AgentRole.COMPLIANCE,
                "collections": AgentRole.COLLECTIONS,
                "treds": AgentRole.TREDS,
            }

            return role_map.get(executor_name, AgentRole.FINANCE_OPS)
        except Exception as e:
            logger.error("llm_routing_error", error=str(e))
            # Fallback to keyword-based routing
            return self._select_executor_fallback(user_message)

    def _select_executor_fallback(self, user_message: str) -> AgentRole:
        """Fallback keyword-based routing if LLM fails."""
        msg = user_message.lower()

        if any(w in msg for w in ["gst", "tax", "compliance", "tds", "file"]):
            return AgentRole.COMPLIANCE
        elif any(w in msg for w in ["remind", "collect", "overdue", "whatsapp", "sms"]):
            return AgentRole.COLLECTIONS
        elif any(w in msg for w in ["discount", "treds", "working capital", "invoice discount"]):
            return AgentRole.TREDS
        else:
            return AgentRole.FINANCE_OPS

    async def process(
        self,
        user_message: str,
        context: Dict[str, Any],
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Process user request by routing to appropriate executor.

        Args:
            user_message: User's request text
            context: Execution context (org_id, user_id, etc.)
            conversation_history: Previous conversation messages

        Returns:
            Dict with success, message, agent_type, and any data
        """
        start_time = time.time()

        try:
            # Determine which executor should handle this
            executor_role = await self._select_executor_llm(user_message)
            executor = self.executors[executor_role]

            logger.info(
                "executor_selected",
                executor=executor.name,
                role=executor.role,
                message_preview=user_message[:100],
            )

            # Create execution state
            state = ExecutionState(
                user_request=user_message,
                org_id=context.get("org_id", ""),
                user_id=context.get("user_id"),
                business_id=context.get("business_id", "1"),
                thread_id=context.get("session_id", "default"),
            )

            # Execute
            result_state = await executor.execute(state)

            # Format response
            executor_output = result_state.agent_outputs.get(executor.name, {})

            response = {
                "success": True,
                "message": executor_output.get("message", "Operation completed"),
                "agent_type": executor.role,
                "executor": executor.name,
                "data": executor_output.get("data"),
                "execution_time_ms": int((time.time() - start_time) * 1000),
            }

            logger.info(
                "execution_complete",
                executor=executor.name,
                success=True,
                execution_time_ms=response["execution_time_ms"],
            )

            return response

        except Exception as e:
            logger.error(
                "orchestrator_error",
                error=str(e),
                user_message=user_message[:100],
            )
            return {
                "success": False,
                "message": f"Execution failed: {str(e)}",
                "agent_type": None,
                "error": str(e),
            }


# Singleton instance
master_orchestrator = MasterOrchestrator()
