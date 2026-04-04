"""
Intelligent Agent Orchestrator - The Brain
Combines all agents with function calling capabilities
Routes requests intelligently and provides context-aware responses
"""

import os
import json
import asyncio
from typing import Any, Dict, List, Optional
import httpx

from app.agents.base_agent import AgentResponse
from app.agents.function_calling_agent import (
    function_calling_agent,
    FunctionCallingAgent,
)
from app.agents.enhanced_market_agent import enhanced_market_agent
from app.agents.enhanced_finance_agent import enhanced_finance_agent
from app.schemas.intents import Intent, AgentType
from app.memory.persistent_memory import persistent_memory
from app.tools.multi_source_search import multi_source_search
from app.adapters.backend_adapter import get_backend_adapter
from app.utils.logger import get_logger

logger = get_logger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.3-70b-versatile"


async def groq_chat(
    prompt: str, max_tokens: int = 500, system: Optional[str] = None
) -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                json={
                    "model": GROQ_MODEL,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": 0.4,
                },
            )
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.error({"event": "groq_chat_error", "error": str(e)})
        return "I'm having trouble processing that right now."


class IntelligentAgent:
    """
    The Brain - Unified agent orchestrator with function calling.

    Capabilities:
    - Routes requests to specialized agents
    - Can call functions/tools dynamically
    - Maintains conversation context
    - Learns from interactions (persistent memory)
    - Multi-source web search integration
    """

    def __init__(self):
        self.backend = get_backend_adapter()
        self.function_agent = function_calling_agent
        self.market_agent = enhanced_market_agent
        self.finance_agent = enhanced_finance_agent
        self.conversation_turn = 0
        logger.info({"event": "intelligent_agent_initialized"})

    async def process(
        self,
        user_message: str,
        context: Dict[str, Any],
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Main entry point - processes user message with full context.
        Returns response + any UI events + function call results.
        """
        self.conversation_turn += 1

        session_id = context.get("session_id", "default")
        org_id = context.get("org_id", context.get("org_uuid", ""))
        user_id = context.get("user_id")

        persistent_memory.add_conversation_turn(
            session_id=session_id,
            role="user",
            content=user_message,
            intent=None,
            metadata={"turn": self.conversation_turn},
        )

        intent = self._classify_intent(user_message)

        context_for_agent = {
            **context,
            "org_uuid": org_id,
            "org_id": org_id,
            "user_id": user_id,
            "session_id": session_id,
            "turn": self.conversation_turn,
        }

        history = conversation_history or []
        history.append({"role": "user", "content": user_message})

        if intent in self._market_intents():
            result = await self._handle_market_query(
                user_message, context_for_agent, history
            )
        elif intent in self._finance_intents():
            result = await self._handle_finance_query(
                user_message, context_for_agent, history, intent
            )
        elif intent in self._compliance_intents():
            result = await self._handle_compliance_query(
                user_message, context_for_agent
            )
        elif intent in self._voice_intents():
            result = await self._handle_voice_command(user_message, context_for_agent)
        else:
            result = await self._handle_general_query(
                user_message, context_for_agent, history
            )

        history.append({"role": "assistant", "content": result.get("message", "")})

        persistent_memory.add_conversation_turn(
            session_id=session_id,
            role="assistant",
            content=result.get("message", ""),
            intent=intent.value if intent else "general",
            metadata={
                "turn": self.conversation_turn,
                "agent": result.get("agent_type"),
            },
        )

        return result

    def _classify_intent(self, message: str) -> Intent:
        message_lower = message.lower()

        if any(
            w in message_lower
            for w in [
                "market",
                "competition",
                "industry",
                "trend",
                "opportunity",
                "growth",
            ]
        ):
            return Intent.GENERAL_QUERY
        elif any(
            w in message_lower
            for w in [
                "revenue",
                "profit",
                "expense",
                "money",
                "balance",
                "financial",
                "cash",
            ]
        ):
            return Intent.ANALYTICS_QUERY
        elif any(
            w in message_lower
            for w in ["invoice", "payment", "due", "overdue", "pending"]
        ):
            return Intent.INVOICE_QUERY
        elif any(
            w in message_lower for w in ["client", "customer", "lead", "prospect"]
        ):
            return Intent.CLIENT_QUERY
        elif any(
            w in message_lower for w in ["compliance", "tds", "deadline", "gst", "tax"]
        ):
            return Intent.COMPLIANCE_CHECK
        elif any(
            w in message_lower for w in ["create invoice", "new invoice", "add invoice"]
        ):
            return Intent.INVOICE_CREATE
        elif any(
            w in message_lower
            for w in ["health", "how are we", "how's business", "status"]
        ):
            return Intent.BUSINESS_HEALTH_CHECK
        else:
            return Intent.GENERAL_QUERY

    def _market_intents(self) -> set:
        return {
            Intent.GENERAL_QUERY,
            Intent.GROWTH_STRATEGY,
            Intent.MARKET_EXPANSION,
            Intent.SCALING_ADVICE,
            Intent.COMPETITIVE_POSITIONING,
            Intent.SWOT_ANALYSIS,
            Intent.TREND_ANALYSIS,
        }

    def _finance_intents(self) -> set:
        return {
            Intent.ANALYTICS_QUERY,
            Intent.BALANCE_CHECK,
            Intent.BUSINESS_HEALTH_CHECK,
            Intent.FORECAST_REQUEST,
            Intent.PROBLEM_DIAGNOSIS,
        }

    def _compliance_intents(self) -> set:
        return {
            Intent.COMPLIANCE_CHECK,
        }

    def _voice_intents(self) -> set:
        return {
            Intent.INVOICE_CREATE,
            Intent.INVOICE_UPDATE,
            Intent.INVOICE_QUERY,
            Intent.CLIENT_CREATE,
            Intent.CLIENT_QUERY,
            Intent.PAYMENT_RECORD,
        }

    async def _handle_market_query(
        self, message: str, context: Dict[str, Any], history: List[Dict[str, Any]]
    ):
        class Ctx:
            org_uuid = context.get("org_uuid", "")
            user_id = context.get("user_id")
            business_id = context.get("business_id", "default")

        result = await self.market_agent.handle_market_query(message, Ctx(), history)

        return {
            "message": result.message,
            "success": result.success,
            "agent_type": result.agent_type.value
            if result.agent_type
            else "market_agent",
            "ui_event": result.ui_event,
        }

    async def _handle_finance_query(
        self,
        message: str,
        context: Dict[str, Any],
        history: List[Dict[str, Any]],
        intent: Intent,
    ):
        class Ctx:
            org_uuid = context.get("org_uuid", context.get("org_id", ""))
            org_id = context.get("org_id", context.get("org_uuid", ""))
            user_id = context.get("user_id")
            business_id = context.get("business_id", "default")

        if intent == Intent.BALANCE_CHECK or intent == Intent.ANALYTICS_QUERY:
            result = await self.finance_agent.handle_balance_check(Ctx())
        elif intent == Intent.BUSINESS_HEALTH_CHECK:
            result = await self.finance_agent.handle_health_check(Ctx())
        elif intent == Intent.FORECAST_REQUEST:
            result = await self.finance_agent.handle_cash_flow_forecast(Ctx())
        elif intent == Intent.PROBLEM_DIAGNOSIS:
            result = await self.finance_agent.handle_payment_analysis(Ctx())
        else:
            result = await self.finance_agent.handle_invoice_query(Ctx())

        return {
            "message": result.message,
            "success": result.success,
            "agent_type": result.agent_type.value
            if result.agent_type
            else "finance_agent",
            "ui_event": result.ui_event,
        }

    async def _handle_compliance_query(self, message: str, context: Dict[str, Any]):
        org_id = context.get("org_id", context.get("org_uuid", ""))
        user_id = context.get("user_id")

        response = await self.backend._request(
            "GET", "/api/compliance/deadlines", org_id=org_id, user_id=user_id
        )

        if response.success and response.data:
            deadlines = response.data.get("upcoming", [])

            if not deadlines:
                message = "You have no upcoming compliance deadlines. Your compliance is up to date."
            else:
                items = []
                for d in deadlines[:3]:
                    items.append(
                        f"{d.get('name', 'Deadline')}: {d.get('dueDate', 'TBD')}"
                    )
                message = f"Upcoming deadlines: {', '.join(items)}"
        else:
            message = "I couldn't fetch your compliance data right now. Please check back later."

        return {"message": message, "success": True, "agent_type": "compliance_agent"}

    async def _handle_voice_command(self, message: str, context: Dict[str, Any]):
        decision = await self.function_agent.decide_and_execute(
            user_message=message,
            context=context,
            conversation_history=[],
            max_iterations=2,
        )

        return {
            "message": decision.get("response", "I've processed that request."),
            "success": True,
            "agent_type": "function_agent",
            "function_results": decision.get("function_calls", []),
        }

    async def _handle_general_query(
        self, message: str, context: Dict[str, Any], history: List[Dict[str, Any]]
    ):
        org_id = context.get("org_id", context.get("org_uuid", ""))

        stored_knowledge = persistent_memory.get_knowledge(org_id)

        market_search = await multi_source_search.search(
            message, max_results_per_source=3
        )

        search_context = market_search.get("synthesized_answer", "")

        business_context = ""
        if org_id:
            metrics_resp = await self.backend.get_finance_metrics(
                "default", org_id, context.get("user_id")
            )
            if metrics_resp.success and metrics_resp.data:
                m = metrics_resp.data
                business_context = f"\n\nBusiness context: Revenue ₹{m.get('revenue', 0):,.0f}, Profit ₹{m.get('netProfit', 0):,.0f}"

        prompt = f"""You are a knowledgeable financial assistant. Answer the user's question helpfully.

USER QUESTION: {message}

{search_context}

{business_context}

Provide a helpful, accurate response. If you don't have specific information, say so honestly.
Keep it 3-4 sentences. Be conversational and helpful."""

        response = await groq_chat(prompt)

        return {
            "message": response,
            "success": True,
            "agent_type": "intelligent_agent",
            "sources": market_search.get("sources", [])[:2],
        }

    async def get_conversation_context(
        self, session_id: str, max_turns: int = 10
    ) -> List[Dict[str, Any]]:
        return persistent_memory.get_conversation_history(session_id, max_turns)

    async def learn_from_interaction(
        self,
        org_id: str,
        category: str,
        key: str,
        value: Any,
        outcome: Optional[str] = None,
    ):
        knowledge = {"value": value}
        if outcome:
            knowledge["outcome"] = outcome

        persistent_memory.store_knowledge(
            org_id=org_id,
            category=category,
            key=key,
            value=knowledge,
            confidence=0.8,
            source="conversation",
        )


intelligent_agent = IntelligentAgent()
