"""
Function Calling Agent - OpenAI-style function calling for agents
Enables agents to make decisions and call tools dynamically
"""

import os
import json
import asyncio
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import httpx

from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class FunctionDefinition:
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Optional[Callable] = None
    category: str = "general"
    requires_confirmation: bool = False
    mvp_ready: bool = True


@dataclass
class FunctionCall:
    name: str
    arguments: Dict[str, Any]
    call_id: Optional[str] = None


@dataclass
class FunctionResult:
    name: str
    success: bool
    result: Any
    error: Optional[str] = None
    execution_time_ms: Optional[int] = None


class FunctionCallingAgent:
    """
    Agent with function calling capabilities - like OpenAI's function calling.
    Can dynamically decide to call functions based on user input.
    """

    def __init__(self, model: str = "llama-3.3-70b-versatile"):
        self.model = model
        self.groq_api_key = os.getenv("GROQ_API_KEY", "")
        self.functions: Dict[str, FunctionDefinition] = {}
        self._register_core_functions()
        logger.info({"event": "function_calling_agent_initialized"})

    def _register_core_functions(self):
        self.register_function(
            FunctionDefinition(
                name="search_web",
                description="Search the web for current information. Use when user asks about news, market trends, competitors, or anything requiring up-to-date data.",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "The search query"},
                        "category": {
                            "type": "string",
                            "enum": ["news", "market", "competitor", "general"],
                            "description": "Search category",
                        },
                    },
                    "required": ["query"],
                },
                handler=self._fn_search_web,
                category="search",
                mvp_ready=True,
            )
        )

        self.register_function(
            FunctionDefinition(
                name="get_financial_metrics",
                description="Get real-time financial metrics for the business including revenue, expenses, profit, and invoice status.",
                parameters={
                    "type": "object",
                    "properties": {
                        "org_id": {"type": "string", "description": "Organization ID"},
                        "user_id": {"type": "string", "description": "User ID"},
                    },
                    "required": ["org_id"],
                },
                handler=self._fn_get_financial_metrics,
                category="finance",
                mvp_ready=True,
            )
        )

        self.register_function(
            FunctionDefinition(
                name="get_clients",
                description="Get list of all clients with their details.",
                parameters={
                    "type": "object",
                    "properties": {
                        "org_id": {"type": "string", "description": "Organization ID"},
                        "user_id": {"type": "string", "description": "User ID"},
                    },
                    "required": ["org_id"],
                },
                handler=self._fn_get_clients,
                category="finance",
                mvp_ready=True,
            )
        )

        self.register_function(
            FunctionDefinition(
                name="get_invoices",
                description="Get list of invoices with optional status filter.",
                parameters={
                    "type": "object",
                    "properties": {
                        "org_id": {"type": "string", "description": "Organization ID"},
                        "user_id": {"type": "string", "description": "User ID"},
                        "status": {
                            "type": "string",
                            "enum": ["DRAFT", "SENT", "PAID", "OVERDUE"],
                            "description": "Filter by status",
                        },
                    },
                },
                handler=self._fn_get_invoices,
                category="finance",
                mvp_ready=True,
            )
        )

        self.register_function(
            FunctionDefinition(
                name="analyze_market",
                description="Perform deep market analysis combining business data with external market intelligence.",
                parameters={
                    "type": "object",
                    "properties": {
                        "org_id": {"type": "string", "description": "Organization ID"},
                        "query": {
                            "type": "string",
                            "description": "Specific market question",
                        },
                    },
                    "required": ["org_id", "query"],
                },
                handler=self._fn_analyze_market,
                category="intelligence",
                mvp_ready=True,
            )
        )

        self.register_function(
            FunctionDefinition(
                name="check_compliance",
                description="Check TDS compliance, upcoming deadlines, and regulatory requirements.",
                parameters={
                    "type": "object",
                    "properties": {
                        "org_id": {"type": "string", "description": "Organization ID"},
                        "user_id": {"type": "string", "description": "User ID"},
                    },
                    "required": ["org_id"],
                },
                handler=self._fn_check_compliance,
                category="compliance",
                mvp_ready=True,
            )
        )

        self.register_function(
            FunctionDefinition(
                name="calculate_health_score",
                description="Calculate business health score based on financial metrics and patterns.",
                parameters={
                    "type": "object",
                    "properties": {
                        "org_id": {"type": "string", "description": "Organization ID"},
                        "user_id": {"type": "string", "description": "User ID"},
                    },
                    "required": ["org_id"],
                },
                handler=self._fn_calculate_health_score,
                category="intelligence",
                mvp_ready=True,
            )
        )

        self.register_function(
            FunctionDefinition(
                name="send_notification",
                description="Send a notification to the user via email or in-app.",
                parameters={
                    "type": "object",
                    "properties": {
                        "org_id": {"type": "string", "description": "Organization ID"},
                        "message": {
                            "type": "string",
                            "description": "Notification message",
                        },
                        "type": {
                            "type": "string",
                            "enum": ["email", "in_app", "sms"],
                            "description": "Notification type",
                        },
                    },
                    "required": ["org_id", "message"],
                },
                handler=self._fn_send_notification,
                category="communication",
                mvp_ready=False,
            )
        )

    def register_function(self, function: FunctionDefinition):
        self.functions[function.name] = function
        logger.debug({"event": "function_registered", "name": function.name})

    def get_functions_for_llm(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": f.name,
                    "description": f.description,
                    "parameters": f.parameters,
                },
            }
            for f in self.functions.values()
            if f.mvp_ready
        ]

    async def decide_and_execute(
        self,
        user_message: str,
        context: Dict[str, Any],
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        max_iterations: int = 3,
    ) -> Dict[str, Any]:
        """
        Main loop: Agent thinks, decides to call functions, executes, responds.
        """
        iteration = 0
        function_results = []
        final_response = None

        while iteration < max_iterations:
            iteration += 1

            decision = await self._get_llm_decision(
                user_message, context, conversation_history or [], function_results
            )

            if not decision.get("should_call_function"):
                final_response = decision.get("response")
                break

            function_calls = decision.get("function_calls", [])

            for call in function_calls:
                result = await self._execute_function(call, context)
                function_results.append(result)

            response = await self._generate_response(
                user_message, context, conversation_history or [], function_results
            )

            if response.get("is_final"):
                final_response = response.get("message")
                break

            function_results.extend(response.get("new_function_calls", []))

        return {
            "response": final_response or "I need more time to process this.",
            "function_calls": function_results,
            "iterations": iteration,
        }

    async def _get_llm_decision(
        self,
        user_message: str,
        context: Dict[str, Any],
        history: List[Dict[str, Any]],
        previous_results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        functions_json = json.dumps(self.get_functions_for_llm(), indent=2)

        history_str = "\n".join(
            [
                f"{'User' if h['role'] == 'user' else 'Assistant'}: {h['content']}"
                for h in history[-6:]
            ]
        )

        results_str = (
            "\n".join(
                [
                    f"Function {r['name']}: {json.dumps(r['result']) if r.get('result') else r.get('error', 'No result')}"
                    for r in previous_results
                ]
            )
            if previous_results
            else "No previous function calls"
        )

        prompt = f"""You are an intelligent financial assistant. Analyze the user's request and decide if you need to call any functions.

USER MESSAGE: {user_message}

CONVERSATION HISTORY:
{history_str}

PREVIOUS FUNCTION RESULTS:
{results_str}

AVAILABLE FUNCTIONS:
{functions_json}

CONTEXT:
- Organization ID: {context.get("org_id", "unknown")}
- User ID: {context.get("user_id", "unknown")}
- Business ID: {context.get("business_id", "default")}

DECISION RULES:
1. If the user asks about financial metrics, revenue, expenses, profit - call get_financial_metrics
2. If the user asks about clients, customer list - call get_clients
3. If the user asks about invoices, payments, pending amounts - call get_invoices
4. If the user asks about market trends, competitors, news, industry - call search_web AND analyze_market
5. If the user asks about compliance, TDS, deadlines - call check_compliance
6. If the user asks about business health, how the business is doing - call calculate_health_score
7. For most queries, call 1-2 functions maximum. Prefer specific over general.

Respond ONLY with valid JSON:
{{
    "should_call_function": true/false,
    "function_calls": [
        {{"name": "function_name", "arguments": {{"param": "value"}}}}
    ],
    "response": "direct response if no function needed"
}}
"""

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.groq_api_key}"},
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 800,
                        "temperature": 0.3,
                    },
                )
                data = resp.json()
                content = data["choices"][0]["message"]["content"].strip()

                if content.startswith("```"):
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:]

                return json.loads(content)
        except Exception as e:
            logger.error({"event": "llm_decision_error", "error": str(e)})
            return {
                "should_call_function": False,
                "response": "I'm having trouble processing that request.",
            }

    async def _execute_function(
        self, call: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        import time

        start = time.time()

        name = call.get("name")
        args = call.get("arguments", {})

        if name not in self.functions:
            return {
                "name": name,
                "success": False,
                "error": f"Function {name} not found",
            }

        func = self.functions[name]

        if not func.mvp_ready:
            return {
                "name": name,
                "success": False,
                "error": f"Function {name} not yet available",
            }

        try:
            merged_context = {**context, **args}

            if asyncio.iscoroutinefunction(func.handler):
                result = await func.handler(merged_context)
            else:
                result = func.handler(merged_context)

            return {
                "name": name,
                "success": True,
                "result": result,
                "execution_time_ms": int((time.time() - start) * 1000),
            }
        except Exception as e:
            logger.error(
                {"event": "function_execution_error", "function": name, "error": str(e)}
            )
            return {
                "name": name,
                "success": False,
                "error": str(e),
                "execution_time_ms": int((time.time() - start) * 1000),
            }

    async def _generate_response(
        self,
        user_message: str,
        context: Dict[str, Any],
        history: List[Dict[str, Any]],
        function_results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        results_str = "\n".join(
            [
                f"**{r['name']}**:\n{json.dumps(r.get('result', r.get('error', 'No result')), indent=2)}"
                for r in function_results
            ]
        )

        history_str = "\n".join(
            [
                f"{'User' if h['role'] == 'user' else 'Assistant'}: {h['content']}"
                for h in history[-4:]
            ]
        )

        prompt = f"""You are a financial assistant. Based on the function results, generate a helpful, natural response.

USER'S ORIGINAL QUESTION: {user_message}

CONVERSATION HISTORY:
{history_str}

FUNCTION RESULTS:
{results_str}

INSTRUCTIONS:
- Respond naturally as a CFO-level assistant
- Use specific numbers and data from the function results
- Be concise but informative (3-5 sentences for voice, more for text)
- If results show issues (overdue invoices, low margins, etc.), address them proactively
- Give actionable recommendations when appropriate
- Return JSON: {{"message": "your response", "is_final": true/false}}
"""

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.groq_api_key}"},
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 500,
                        "temperature": 0.4,
                    },
                )
                data = resp.json()
                content = data["choices"][0]["message"]["content"].strip()

                if content.startswith("```"):
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:]

                return json.loads(content)
        except Exception as e:
            logger.error({"event": "response_generation_error", "error": str(e)})
            return {
                "message": "I've gathered the information. Let me summarize what I found.",
                "is_final": True,
            }

    async def _fn_search_web(self, context: Dict[str, Any]) -> Dict[str, Any]:
        from app.tools.multi_source_search import multi_source_search

        query = context.get("query", "")
        if not query:
            return {"error": "No search query provided"}

        result = await multi_source_search.search(query, max_results_per_source=5)
        return {
            "results_count": len(result.get("results", [])),
            "top_results": result.get("results", [])[:3],
            "synthesized_answer": result.get("synthesized_answer", ""),
            "sources": result.get("sources", [])[:5],
        }

    async def _fn_get_financial_metrics(
        self, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        from app.adapters.backend_adapter import get_backend_adapter

        backend = get_backend_adapter()
        org_id = context.get("org_id", "")
        user_id = context.get("user_id")
        business_id = context.get("business_id", "default")

        if not org_id:
            return {"error": "Organization ID required"}

        response = await backend.get_finance_metrics(business_id, org_id, user_id)

        if response.success and response.data:
            data = response.data
            return {
                "revenue": data.get("revenue", 0),
                "expenses": data.get("expenses", 0),
                "net_profit": data.get("netProfit", 0),
                "profit_margin": round(
                    (data.get("netProfit", 0) / max(data.get("revenue", 1), 1)) * 100, 1
                ),
                "overdue_count": data.get("overdueCount", 0),
                "overdue_amount": data.get("overdueAmount", 0),
            }

        return {"error": "Could not fetch financial metrics"}

    async def _fn_get_clients(self, context: Dict[str, Any]) -> Dict[str, Any]:
        from app.adapters.backend_adapter import get_backend_adapter

        backend = get_backend_adapter()
        org_id = context.get("org_id", "")
        user_id = context.get("user_id")

        if not org_id:
            return {"error": "Organization ID required"}

        clients = await backend.get_clients(org_id, user_id=user_id)

        if clients:
            return {
                "count": len(clients),
                "clients": [
                    {
                        "name": c.get("name"),
                        "email": c.get("email"),
                        "status": c.get("status"),
                    }
                    for c in clients[:10]
                ],
            }

        return {"count": 0, "clients": []}

    async def _fn_get_invoices(self, context: Dict[str, Any]) -> Dict[str, Any]:
        from app.adapters.backend_adapter import get_backend_adapter

        backend = get_backend_adapter()
        org_id = context.get("org_id", "")
        user_id = context.get("user_id")
        status = context.get("status")

        if not org_id:
            return {"error": "Organization ID required"}

        params = {}
        if status:
            params["status"] = status

        response = await backend._request(
            "GET", "/api/invoices", org_id=org_id, user_id=user_id, params=params
        )

        if response.success and isinstance(response.data, list):
            invoices = response.data
            by_status = {}
            for inv in invoices:
                s = inv.get("status", "UNKNOWN")
                by_status[s] = by_status.get(s, 0) + 1

            return {
                "total": len(invoices),
                "by_status": by_status,
                "total_pending": sum(
                    inv.get("totalAmount", 0)
                    for inv in invoices
                    if inv.get("status") in ("DRAFT", "SENT")
                ),
                "overdue_amount": sum(
                    inv.get("totalAmount", 0)
                    for inv in invoices
                    if inv.get("status") == "OVERDUE"
                ),
            }

        return {"error": "Could not fetch invoices"}

    async def _fn_analyze_market(self, context: Dict[str, Any]) -> Dict[str, Any]:
        from app.tools.multi_source_search import multi_source_search

        query = context.get("query", "")
        org_id = context.get("org_id", "")

        if not query:
            return {"error": "Market analysis query required"}

        metrics = await self._fn_get_financial_metrics(context)

        search_result = await multi_source_search.search(
            query, max_results_per_source=5
        )

        return {
            "business_metrics": metrics,
            "market_intelligence": {
                "answer": search_result.get("synthesized_answer", ""),
                "top_sources": search_result.get("sources", [])[:3],
            },
        }

    async def _fn_check_compliance(self, context: Dict[str, Any]) -> Dict[str, Any]:
        from app.adapters.backend_adapter import get_backend_adapter

        backend = get_backend_adapter()
        org_id = context.get("org_id", "")
        user_id = context.get("user_id")

        if not org_id:
            return {"error": "Organization ID required"}

        response = await backend._request(
            "GET", "/api/compliance/deadlines", org_id=org_id, user_id=user_id
        )

        if response.success and response.data:
            return {"deadlines": response.data}

        return {"message": "No compliance data available"}

    async def _fn_calculate_health_score(
        self, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        metrics = await self._fn_get_financial_metrics(context)

        if "error" in metrics:
            return metrics

        revenue = metrics.get("revenue", 0)
        profit = metrics.get("net_profit", 0)
        overdue = metrics.get("overdue_count", 0)
        overdue_amount = metrics.get("overdue_amount", 0)

        score = 70

        if profit > 0:
            margin = (profit / max(revenue, 1)) * 100
            if margin > 30:
                score += 20
            elif margin > 15:
                score += 10
            elif margin < 5:
                score -= 15

        if overdue > 3:
            score -= 15
        elif overdue > 0:
            score -= 5

        if overdue_amount > revenue * 0.3:
            score -= 10

        score = max(0, min(100, score))

        health_status = (
            "Excellent"
            if score >= 80
            else "Good"
            if score >= 60
            else "Needs Attention"
            if score >= 40
            else "Critical"
        )

        return {
            "score": score,
            "status": health_status,
            "factors": {
                "profit_margin": round((profit / max(revenue, 1)) * 100, 1)
                if revenue > 0
                else 0,
                "overdue_invoices": overdue,
                "overdue_amount": overdue_amount,
            },
            "recommendation": self._get_health_recommendation(score, metrics),
        }

    def _get_health_recommendation(self, score: int, metrics: Dict[str, Any]) -> str:
        if score >= 80:
            return "Your business is in excellent health. Consider investing in growth opportunities."
        elif score >= 60:
            return "Your business is stable. Focus on improving profit margins and collecting overdue payments."
        elif score >= 40:
            return "Your business needs attention. Prioritize collecting overdue invoices and reducing expenses."
        else:
            return "Urgent action needed. Review cash flow, cut unnecessary expenses, and aggressively collect payments."

    async def _fn_send_notification(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return {"message": "Notification feature coming soon", "status": "pending"}


function_calling_agent = FunctionCallingAgent()
