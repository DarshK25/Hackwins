"""
Enhanced Finance Agent - Proactive financial intelligence
Handles invoices, payments, analytics with intelligent context awareness
"""

import os
import re
import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import httpx

from app.agents.base_agent import BaseAgent, AgentResponse, ToolDefinition
from app.schemas.intents import Intent, AgentType
from app.models.draft import InvoiceDraft
from app.adapters.backend_adapter import get_backend_adapter
from app.tools.multi_source_search import multi_source_search
from app.memory.persistent_memory import persistent_memory
from app.utils.logger import get_logger

logger = get_logger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.3-70b-versatile"


async def groq_analyze(prompt: str, max_tokens: int = 400) -> str:
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                json={
                    "model": GROQ_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens,
                    "temperature": 0.3,
                },
            )
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.error({"event": "groq_analyze_error", "error": str(e)})
        return "I couldn't analyze your data right now."


class EnhancedFinanceAgent(BaseAgent):
    """
    Enhanced Finance Agent with:
    - Real-time financial analytics
    - Proactive alerts and recommendations
    - Invoice intelligence with smart defaults
    - Payment prediction
    """

    def __init__(self):
        self.backend = get_backend_adapter()
        super().__init__()
        self._register_tools()

    def get_agent_type(self) -> AgentType:
        return AgentType.FINANCE_AGENT

    def get_supported_intents(self) -> List[Intent]:
        return [
            Intent.INVOICE_CREATE,
            Intent.INVOICE_UPDATE,
            Intent.INVOICE_QUERY,
            Intent.INVOICE_STATUS_CHECK,
            Intent.PAYMENT_RECORD,
            Intent.BALANCE_CHECK,
            Intent.BUSINESS_HEALTH_CHECK,
            Intent.ANALYTICS_QUERY,
            Intent.FORECAST_REQUEST,
            Intent.PROBLEM_DIAGNOSIS,
        ]

    def get_tools(self) -> List[ToolDefinition]:
        return [
            ToolDefinition(
                name="get_financial_summary",
                description="Get complete financial summary",
                parameters={},
                mvp_ready=True,
            ),
            ToolDefinition(
                name="get_invoice_breakdown",
                description="Get detailed invoice analysis",
                parameters={},
                mvp_ready=True,
            ),
            ToolDefinition(
                name="get_payment_insights",
                description="Analyze payment patterns",
                parameters={},
                mvp_ready=True,
            ),
            ToolDefinition(
                name="predict_cash_flow",
                description="Predict future cash flow",
                parameters={},
                mvp_ready=True,
            ),
        ]

    def _register_tools(self):
        from app.tools.tool_registry import Tool, tool_registry

        tool_registry.register_tools(
            [
                Tool(
                    name="get_financial_summary",
                    description="Complete financial summary",
                    category="finance",
                    handler=self._tool_financial_summary,
                    mvp_ready=True,
                ),
                Tool(
                    name="get_invoice_breakdown",
                    description="Invoice breakdown",
                    category="finance",
                    handler=self._tool_invoice_breakdown,
                    mvp_ready=True,
                ),
                Tool(
                    name="get_payment_insights",
                    description="Payment pattern analysis",
                    category="finance",
                    handler=self._tool_payment_insights,
                    mvp_ready=True,
                ),
                Tool(
                    name="predict_cash_flow",
                    description="Cash flow prediction",
                    category="finance",
                    handler=self._tool_cash_flow,
                    mvp_ready=True,
                ),
            ]
        )

    async def _fetch_financial_data(
        self, org_id: str, user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        tasks = [
            self.backend.get_finance_metrics("default", org_id, user_id),
            self.backend._request(
                "GET", "/api/invoices", org_id=org_id, user_id=user_id
            ),
            self.backend.get_clients(org_id, user_id=user_id),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        metrics = results[0] if not isinstance(results[0], Exception) else None
        invoices_resp = results[1] if not isinstance(results[1], Exception) else None
        clients = results[2] if not isinstance(results[2], Exception) else []

        m_data = metrics.data if metrics and metrics.success else {}
        invoices = invoices_resp.data if invoices_resp and invoices_resp.success else []
        clients = clients if isinstance(clients, list) else []

        return {"metrics": m_data, "invoices": invoices, "clients": clients}

    async def _generate_financial_summary(
        self, org_id: str, user_id: Optional[str] = None
    ) -> str:
        data = await self._fetch_financial_data(org_id, user_id)

        m = data["metrics"]
        invoices = data["invoices"]

        revenue = m.get("revenue", 0)
        expenses = m.get("expenses", 0)
        profit = m.get("netProfit", 0)

        overdue = [i for i in invoices if i.get("status") == "OVERDUE"]
        pending = [i for i in invoices if i.get("status") in ("DRAFT", "SENT")]
        paid = [i for i in invoices if i.get("status") == "PAID"]

        overdue_amount = sum(float(i.get("totalAmount", 0)) for i in overdue)
        pending_amount = sum(float(i.get("totalAmount", 0)) for i in pending)
        margin = round((profit / max(revenue, 1)) * 100, 1) if revenue > 0 else 0

        urgent_invoices = []
        for inv in overdue:
            due_date_str = inv.get("dueDate", "")
            try:
                due_date = datetime.strptime(due_date_str, "%Y-%m-%d")
                days_overdue = (datetime.now() - due_date).days
                if days_overdue > 7:
                    urgent_invoices.append(
                        {
                            "client": inv.get("clientName", "Unknown"),
                            "amount": float(inv.get("totalAmount", 0)),
                            "days_overdue": days_overdue,
                        }
                    )
            except:
                pass

        prompt = f"""Summarize this business's financial health clearly.

REVENUE: ₹{revenue:,.0f}
EXPENSES: ₹{expenses:,.0f}
NET PROFIT: ₹{profit:,.0f}
MARGIN: {margin}%

INVOICES:
- Paid: {len(paid)} invoices
- Pending: {len(pending)} invoices worth ₹{pending_amount:,.0f}
- Overdue: {len(overdue)} invoices worth ₹{overdue_amount:,.0f}

URGENT (>7 days overdue):
{chr(10).join([f"- {i['client']}: ₹{i['amount']:,.0f} ({i['days_overdue']} days)" for i in urgent_invoices]) or "None"}

Write 3-4 sentences that:
1. Give the financial snapshot (revenue, profit, margin)
2. Highlight any cash flow concerns
3. Recommend one specific action

Be direct and use actual numbers. This is for voice response."""

        return await groq_analyze(prompt)

    async def _generate_invoice_report(
        self, org_id: str, user_id: Optional[str] = None
    ) -> str:
        data = await self._fetch_financial_data(org_id, user_id)
        invoices = data["invoices"]
        clients = data["clients"]

        by_status = {"DRAFT": [], "SENT": [], "PAID": [], "OVERDUE": []}
        for inv in invoices:
            status = inv.get("status", "UNKNOWN")
            if status in by_status:
                by_status[status].append(inv)

        report_lines = ["**Invoice Report**\n"]

        for status, invs in by_status.items():
            if invs:
                total = sum(float(i.get("totalAmount", 0)) for i in invs)
                report_lines.append(
                    f"**{status}**: {len(invs)} invoices, ₹{total:,.0f}"
                )

        prompt = f"""Analyze these invoices and give key insights:

{chr(10).join(report_lines)}

CLIENTS: {len(clients)} total

Give 2-3 actionable insights about:
1. Which clients owe money
2. Payment patterns
3. One recommendation

Keep it concise for voice."""

        return await groq_analyze(prompt)

    async def _analyze_payment_patterns(
        self, org_id: str, user_id: Optional[str] = None
    ) -> str:
        data = await self._fetch_financial_data(org_id, user_id)
        invoices = data["invoices"]

        payment_days = []
        for inv in invoices:
            if inv.get("status") == "PAID":
                try:
                    issued = datetime.strptime(inv.get("issueDate", ""), "%Y-%m-%d")
                    paid_date = (
                        datetime.strptime(inv.get("paidDate", ""), "%Y-%m-%d")
                        if inv.get("paidDate")
                        else datetime.now()
                    )
                    days = (paid_date - issued).days
                    if 0 < days < 180:
                        payment_days.append(days)
                except:
                    pass

        avg_days = sum(payment_days) / len(payment_days) if payment_days else 0

        overdue = [i for i in invoices if i.get("status") == "OVERDUE"]

        prompt = f"""Payment pattern analysis:

Average time to payment: {avg_days:.0f} days
Invoices analyzed: {len(payment_days)}
Currently overdue: {len(overdue)} invoices

OVERDUE DETAILS:
{chr(10).join([f"- {i.get('clientName', 'Unknown')}: ₹{float(i.get('totalAmount', 0)):,.0f}" for i in overdue[:5]]) or "None"}

Give:
1. Assessment of payment behavior
2. Which clients pay on time vs delayed
3. One recommendation to improve collections

Keep it 4-5 sentences, voice-friendly."""

        return await groq_analyze(prompt)

    async def _predict_cash_flow(
        self, org_id: str, user_id: Optional[str] = None
    ) -> str:
        data = await self._fetch_financial_data(org_id, user_id)
        m = data["metrics"]

        revenue = m.get("revenue", 0)
        pending = [i for i in data["invoices"] if i.get("status") in ("DRAFT", "SENT")]
        pending_amount = sum(float(i.get("totalAmount", 0)) for i in pending)

        monthly_revenue = revenue
        monthly_expenses = m.get("expenses", 0)

        prompt = f"""Cash flow prediction:

Monthly Revenue Run Rate: ₹{monthly_revenue:,.0f}
Monthly Expenses: ₹{monthly_expenses:,.0f}
Net Monthly: ₹{monthly_revenue - monthly_expenses:,.0f}

Pending Invoices (expected cash): ₹{pending_amount:,.0f}
Count: {len(pending)}

Give a 30-day cash flow outlook:
1. Expected cash inflows
2. Expected outflows
3. Net position
4. One action to improve cash flow

Keep it 4-5 sentences for voice."""

        return await groq_analyze(prompt)

    async def handle_balance_check(self, context) -> AgentResponse:
        org_id = getattr(context, "org_uuid", None) or context.get("org_id", "")
        user_id = getattr(context, "user_id", None) or context.get("user_id")

        summary = await self._generate_financial_summary(org_id, user_id)

        return AgentResponse(
            success=True,
            message=summary,
            agent_type=self.get_agent_type(),
            ui_event={
                "type": "financial_summary",
                "variant": "info",
                "title": "Financial Summary",
                "duration": 5000,
            },
        )

    async def handle_invoice_query(self, context) -> AgentResponse:
        org_id = getattr(context, "org_uuid", None) or context.get("org_id", "")
        user_id = getattr(context, "user_id", None) or context.get("user_id")

        report = await self._generate_invoice_report(org_id, user_id)

        return AgentResponse(
            success=True, message=report, agent_type=self.get_agent_type()
        )

    async def handle_payment_analysis(self, context) -> AgentResponse:
        org_id = getattr(context, "org_uuid", None) or context.get("org_id", "")
        user_id = getattr(context, "user_id", None) or context.get("user_id")

        analysis = await self._analyze_payment_patterns(org_id, user_id)

        return AgentResponse(
            success=True, message=analysis, agent_type=self.get_agent_type()
        )

    async def handle_cash_flow_forecast(self, context) -> AgentResponse:
        org_id = getattr(context, "org_uuid", None) or context.get("org_id", "")
        user_id = getattr(context, "user_id", None) or context.get("user_id")

        forecast = await self._predict_cash_flow(org_id, user_id)

        return AgentResponse(
            success=True, message=forecast, agent_type=self.get_agent_type()
        )

    async def handle_health_check(self, context) -> AgentResponse:
        org_id = getattr(context, "org_uuid", None) or context.get("org_id", "")
        user_id = getattr(context, "user_id", None) or context.get("user_id")

        data = await self._fetch_financial_data(org_id, user_id)
        m = data["metrics"]

        revenue = m.get("revenue", 0)
        profit = m.get("netProfit", 0)
        overdue = [i for i in data["invoices"] if i.get("status") == "OVERDUE"]

        score = 75
        margin = (profit / max(revenue, 1)) * 100 if revenue > 0 else 0

        if margin > 30:
            score += 15
        elif margin > 15:
            score += 5
        elif margin < 5:
            score -= 20

        if len(overdue) > 3:
            score -= 15
        elif len(overdue) > 0:
            score -= 5

        score = max(0, min(100, score))

        status = (
            "Excellent"
            if score >= 80
            else "Good"
            if score >= 60
            else "Needs Attention"
            if score >= 40
            else "Critical"
        )

        message = f"Your business health score is {score}/100 ({status}). "

        if status == "Excellent":
            message += "You're doing great! Consider investing in growth."
        elif status == "Good":
            message += "You're stable. Focus on collections and margins."
        elif status == "Needs Attention":
            message += "Review your cash flow and collect overdue payments."
        else:
            message += "Take immediate action on overdue invoices and expenses."

        return AgentResponse(
            success=True,
            message=message,
            agent_type=self.get_agent_type(),
            data={"score": score, "status": status, "margin": margin},
        )

    async def _tool_financial_summary(self, params, context=None) -> Dict[str, Any]:
        org_id = context.get("org_id", context.get("org_uuid", "")) if context else ""
        user_id = context.get("user_id") if context else None
        return {"summary": await self._generate_financial_summary(org_id, user_id)}

    async def _tool_invoice_breakdown(self, params, context=None) -> Dict[str, Any]:
        org_id = context.get("org_id", context.get("org_uuid", "")) if context else ""
        user_id = context.get("user_id") if context else None
        return {"report": await self._generate_invoice_report(org_id, user_id)}

    async def _tool_payment_insights(self, params, context=None) -> Dict[str, Any]:
        org_id = context.get("org_id", context.get("org_uuid", "")) if context else ""
        user_id = context.get("user_id") if context else None
        return {"analysis": await self._analyze_payment_patterns(org_id, user_id)}

    async def _tool_cash_flow(self, params, context=None) -> Dict[str, Any]:
        org_id = context.get("org_id", context.get("org_uuid", "")) if context else ""
        user_id = context.get("user_id") if context else None
        return {"forecast": await self._predict_cash_flow(org_id, user_id)}

    async def process(
        self,
        intent: Intent,
        entities: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        class _Ctx:
            org_uuid = (context or {}).get("org_uuid", context or {}).get("org_id", "")
            user_id = (context or {}).get("user_id")
            business_id = (context or {}).get("business_id", "default")

        ctx = _Ctx()

        if intent == Intent.BALANCE_CHECK:
            return await self.handle_balance_check(ctx)
        elif intent in (Intent.INVOICE_QUERY, Intent.INVOICE_STATUS_CHECK):
            return await self.handle_invoice_query(ctx)
        elif intent == Intent.ANALYTICS_QUERY:
            return await self.handle_invoice_query(ctx)
        elif intent == Intent.BUSINESS_HEALTH_CHECK:
            return await self.handle_health_check(ctx)
        elif intent == Intent.FORECAST_REQUEST:
            return await self.handle_cash_flow_forecast(ctx)
        elif intent == Intent.PROBLEM_DIAGNOSIS:
            return await self.handle_payment_analysis(ctx)
        else:
            return self._build_stub_response("finance operation")


enhanced_finance_agent = EnhancedFinanceAgent()
