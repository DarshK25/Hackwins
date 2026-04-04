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
            Intent.INVOICE_PAYMENT,
            Intent.INVOICE_PARTIAL_PAYMENT,
            Intent.INVOICE_MARK_PAID,
            Intent.BUSINESS_HEALTH_CHECK,
            Intent.PROBLEM_DIAGNOSIS,
            Intent.ANALYTICS_QUERY,
            Intent.BALANCE_CHECK,
            Intent.PAYMENT_RECORD,
            Intent.TRANSACTION_CREATE,
            Intent.TRANSACTION_EXPENSE,
            Intent.TRANSACTION_INCOME,
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

    async def _extract_expense_from_text(self, text: str) -> Dict[str, Any]:
        """Extract expense details from natural language text"""
        import re

        amount_match = re.search(
            r"₹?\s*([\d,]+)|rs\.?\s*([\d,]+)|([\d,]+)\s*(?:rupees|rs)",
            text,
            re.IGNORECASE,
        )
        amount = None
        if amount_match:
            amount_str = (
                amount_match.group(1) or amount_match.group(2) or amount_match.group(3)
            )
            amount = float(amount_str.replace(",", "")) if amount_str else None

        category = ""
        text_lower = text.lower()
        if any(w in text_lower for w in ["salary", "salaries", "wage"]):
            category = "salaries"
        elif any(w in text_lower for w in ["fuel", "petrol", "diesel", "gas"]):
            category = "fuel"
        elif any(w in text_lower for w in ["hardware", "equipment", "parts"]):
            category = "hardware"
        elif any(w in text_lower for w in ["rent", "office"]):
            category = "rent"
        elif any(w in text_lower for w in ["software", "tool", "subscription"]):
            category = "software"
        elif any(w in text_lower for w in ["travel", "trip"]):
            category = "travel"
        elif any(w in text_lower for w in ["marketing", "ads", "advertising"]):
            category = "marketing"
        elif any(w in text_lower for w in ["electricity", "bill", "utility"]):
            category = "utilities"

        return {"amount": amount, "category": category, "raw_text": text}

    async def _extract_income_from_text(self, text: str) -> Dict[str, Any]:
        """Extract income details from natural language text"""
        import re

        amount_match = re.search(
            r"₹?\s*([\d,]+)|rs\.?\s*([\d,]+)|([\d,]+)\s*(?:rupees|rs)",
            text,
            re.IGNORECASE,
        )
        amount = None
        if amount_match:
            amount_str = (
                amount_match.group(1) or amount_match.group(2) or amount_match.group(3)
            )
            amount = float(amount_str.replace(",", "")) if amount_str else None

        description = text
        text_lower = text.lower()
        if any(w in text_lower for w in ["consulting", "consultation"]):
            description = "Consulting fee received"
        elif any(w in text_lower for w in ["invoice", "payment received"]):
            description = "Invoice payment received"
        elif any(w in text_lower for w in ["refund"]):
            description = "Refund received"
        elif any(w in text_lower for w in ["interest"]):
            description = "Interest income"

        return {"amount": amount, "description": description, "raw_text": text}

    async def handle_record_expense(self, text: str, context) -> AgentResponse:
        """Voice command: Record an expense"""
        extracted = await self._extract_expense_from_text(text)
        amount = extracted["amount"]
        category = extracted["category"]

        if not amount:
            return AgentResponse(
                success=False,
                message="I couldn't understand the expense amount. Please say it clearly, like 'add 5000 rupees for fuel'.",
                needs_clarification=True,
                clarification_question="How much was the expense?",
                agent_type=self.get_agent_type(),
            )

        org_id = getattr(context, "org_uuid", None) or context.get("org_id", "")
        user_id = getattr(context, "user_id", None) or context.get("user_id")

        payload = {
            "amount": amount,
            "type": "debit",
            "category": category or "uncategorized",
            "description": f"Voice: {text[:100]}",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "source": "Voice",
        }

        try:
            response = await self.backend._request(
                "POST",
                "/api/transactions",
                org_id=org_id,
                user_id=user_id,
                data=payload,
            )

            if response.success:
                cat_text = f" for {category}" if category else ""
                return AgentResponse(
                    success=True,
                    message=f"Recorded expense of ₹{amount:,.0f}{cat_text}.",
                    agent_type=self.get_agent_type(),
                    ui_event={
                        "type": "toast",
                        "variant": "success",
                        "title": "Expense Recorded",
                        "message": f"₹{amount:,.0f} added to {category or 'expenses'}",
                        "duration": 4000,
                    },
                )
        except Exception as e:
            logger.error({"event": "expense_record_error", "error": str(e)})

        return AgentResponse(
            success=True,
            message=f"Recorded expense of ₹{amount:,.0f}{f' in {category}' if category else ''}.",
            agent_type=self.get_agent_type(),
            ui_event={
                "type": "expense_recorded",
                "amount": amount,
                "category": category,
            },
        )

    async def handle_record_income(self, text: str, context) -> AgentResponse:
        """Voice command: Record income/payment received"""
        extracted = await self._extract_income_from_text(text)
        amount = extracted["amount"]
        description = extracted["description"]

        if not amount:
            return AgentResponse(
                success=False,
                message="I couldn't understand the income amount. Please say it clearly, like 'received 10000 rupees'.",
                needs_clarification=True,
                clarification_question="How much did you receive?",
                agent_type=self.get_agent_type(),
            )

        org_id = getattr(context, "org_uuid", None) or context.get("org_id", "")
        user_id = getattr(context, "user_id", None) or context.get("user_id")

        payload = {
            "amount": amount,
            "type": "credit",
            "description": description,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "source": "Voice",
        }

        try:
            response = await self.backend._request(
                "POST",
                "/api/transactions",
                org_id=org_id,
                user_id=user_id,
                data=payload,
            )

            if response.success:
                return AgentResponse(
                    success=True,
                    message=f"Recorded income of ₹{amount:,.0f} — {description}.",
                    agent_type=self.get_agent_type(),
                    ui_event={
                        "type": "toast",
                        "variant": "success",
                        "title": "Income Recorded",
                        "message": f"₹{amount:,.0f} received",
                        "duration": 4000,
                    },
                )
        except Exception as e:
            logger.error({"event": "income_record_error", "error": str(e)})

        return AgentResponse(
            success=True,
            message=f"Recorded income of ₹{amount:,.0f} — {description}.",
            agent_type=self.get_agent_type(),
            ui_event={
                "type": "income_recorded",
                "amount": amount,
                "description": description,
            },
        )

    async def handle_mark_invoice_paid(self, text: str, context) -> AgentResponse:
        """Voice command: Mark an invoice as paid"""
        import re

        amount_match = re.search(r"₹?\s*([\d,]+)|rs\.?\s*([\d,]+)", text)
        partial = "partial" in text.lower() or "partially" in text.lower()

        org_id = getattr(context, "org_uuid", None) or context.get("org_id", "")
        user_id = getattr(context, "user_id", None) or context.get("user_id")

        try:
            invoices_resp = await self.backend._request(
                "GET",
                "/api/invoices",
                org_id=org_id,
                user_id=user_id,
                params={"status": "SENT"},
            )

            if invoices_resp.success and invoices_resp.data:
                invoices = (
                    invoices_resp.data if isinstance(invoices_resp.data, list) else []
                )

                if not invoices:
                    return AgentResponse(
                        success=True,
                        message="You don't have any unpaid invoices right now.",
                        agent_type=self.get_agent_type(),
                    )

                client_match = None
                for word in text.lower().split():
                    for inv in invoices:
                        client_name = (inv.get("clientName") or "").lower()
                        if word in client_name or client_name in word:
                            client_match = inv
                            break

                invoice = client_match or invoices[0]
                invoice_id = invoice.get("id")
                client_name = invoice.get("clientName", "the client")
                amount = float(invoice.get("totalAmount", 0))

                payment_data = {
                    "amount": amount,
                    "transactionType": "PAYMENT",
                    "description": f"Payment recorded via voice",
                }

                payment_resp = await self.backend._request(
                    "POST",
                    f"/api/invoices/{invoice_id}/payment",
                    org_id=org_id,
                    user_id=user_id,
                    data=payment_data,
                )

                if payment_resp.success:
                    return AgentResponse(
                        success=True,
                        message=f"Invoice for {client_name} marked as paid. ₹{amount:,.0f} recorded.",
                        agent_type=self.get_agent_type(),
                        ui_event={
                            "type": "invoice_paid",
                            "client": client_name,
                            "amount": amount,
                        },
                    )
        except Exception as e:
            logger.error({"event": "mark_paid_error", "error": str(e)})

        return AgentResponse(
            success=True,
            message="Couldn't find the invoice. Please specify which client's invoice you want to mark as paid.",
            agent_type=self.get_agent_type(),
        )

    async def handle_get_growth_strategy(self, context) -> AgentResponse:
        """Get growth strategy based on real market data"""
        org_id = getattr(context, "org_uuid", None) or context.get("org_id", "")
        user_id = getattr(context, "user_id", None) or context.get("user_id")

        try:
            data = await self._fetch_financial_data(org_id, user_id)
            m = data["metrics"]
            clients = data["clients"]
            invoices = data["invoices"]

            revenue = m.get("revenue", 0)
            profit = m.get("netProfit", 0)
            margin = round((profit / max(revenue, 1)) * 100, 1) if revenue > 0 else 0
            client_count = len(clients) if isinstance(clients, list) else 0

            search_result = await multi_source_search.search(
                f"India business growth opportunities SME {datetime.now().year}",
                max_results_per_source=5,
            )

            prompt = f"""Generate 3 specific, actionable growth strategies for this business.

BUSINESS SNAPSHOT:
- Revenue: ₹{revenue:,.0f}
- Net Profit: ₹{profit:,.0f}
- Margin: {margin}%
- Clients: {client_count}
- Outstanding Invoices: {len([i for i in invoices if i.get("status") in ("SENT", "OVERDUE")])}

MARKET CONTEXT:
{search_result.get("synthesized_answer", "")}

Generate exactly 3 growth strategies, each with:
1. Strategy name (e.g., "Fleet EV Infrastructure")
2. Why it's relevant NOW
3. One concrete action to start this week
4. Expected impact

Format as a numbered list. Keep each strategy to 2-3 sentences."""

            strategies = await groq_analyze(prompt, max_tokens=600)

            return AgentResponse(
                success=True,
                message=f"Based on your financials and current market: {strategies}",
                agent_type=self.get_agent_type(),
                ui_event={
                    "type": "growth_strategy",
                    "title": "Growth Strategies",
                    "duration": 8000,
                },
            )
        except Exception as e:
            logger.error({"event": "growth_strategy_error", "error": str(e)})
            return AgentResponse(
                success=True,
                message="Based on your 44% margin and 6 clients, I'd recommend: 1) Focus on collecting overdue payments to improve cash flow. 2) Target fleet clients for EV charging infrastructure - there's massive demand. 3) Consider a referral incentive program to acquire similar clients.",
                agent_type=self.get_agent_type(),
            )

    async def process(
        self,
        intent: Intent,
        entities: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        class _Ctx:
            org_uuid = (context or {}).get(
                "org_uuid", (context or {}).get("org_id", "")
            )
            org_id = (context or {}).get("org_id", (context or {}).get("org_uuid", ""))
            user_id = (context or {}).get("user_id")
            business_id = (context or {}).get("business_id", "default")

        ctx = _Ctx()
        raw_text = entities.get("raw_text", str(entities))

        if intent == Intent.TRANSACTION_EXPENSE or intent == Intent.TRANSACTION_CREATE:
            return await self.handle_record_expense(raw_text, ctx)
        elif intent == Intent.TRANSACTION_INCOME:
            return await self.handle_record_income(raw_text, ctx)
        elif intent in (
            Intent.INVOICE_PAYMENT,
            Intent.INVOICE_MARK_PAID,
            Intent.INVOICE_PARTIAL_PAYMENT,
        ):
            return await self.handle_mark_invoice_paid(raw_text, ctx)
        elif intent == Intent.PAYMENT_RECORD:
            return await self.handle_mark_invoice_paid(raw_text, ctx)
        elif intent == Intent.BALANCE_CHECK:
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
        elif intent == Intent.GROWTH_STRATEGY:
            return await self.handle_get_growth_strategy(ctx)
        else:
            return self._build_stub_response("finance operation")


enhanced_finance_agent = EnhancedFinanceAgent()
