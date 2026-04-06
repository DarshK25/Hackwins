"""
Intelligent Agent — unified ReAct reasoning loop for MoneyOps.
Single entry point for voice and text; calls backend tools via Groq.
"""

import os
import json
import asyncio
import re
import requests
from typing import Any, Optional
from app.adapters.backend_adapter import get_backend_adapter
from app.utils.logger import get_logger

logger = get_logger(__name__)

GROQ_KEY_PRIMARY = os.getenv("GROQ_API_KEY", "")
GROQ_KEY_FAST = os.getenv("GROQ_API_KEY_FAST", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_MODEL_FAST = "llama-3.1-8b-instant"
MAX_ITERATIONS = 2


class IntelligentAgent:
    def __init__(self):
        self.backend = get_backend_adapter()

    # ── Tool Registry ─────────────────────────────────────────────────────────

    @property
    def tools(self) -> dict:
        return {
            "get_financial_metrics": self._tool_get_financial_metrics,
            "get_overdue_invoices": self._tool_get_overdue_invoices,
            "get_all_invoices": self._tool_get_all_invoices,
            "get_daily_briefing": self._tool_get_daily_briefing,
            "send_invoice": self._tool_send_invoice,
            "send_invoice_followup": self._tool_send_invoice_followup,
            "get_clients": self._tool_get_clients,
            "get_verification_status": self._tool_get_verification_status,
            "record_transaction": self._tool_record_transaction,
        }

    @property
    def tool_schemas(self) -> list:
        return [
            {
                "name": "get_financial_metrics",
                "description": "Revenue, expenses, profit, invoice counts",
                "parameters": {
                    "type": "object",
                    "properties": {"business_id": {"type": "string"}},
                    "required": [],
                },
            },
            {
                "name": "get_overdue_invoices",
                "description": "All overdue invoices",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
            {
                "name": "get_all_invoices",
                "description": "All invoices (optional status filter)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "enum": ["DRAFT", "SENT", "PAID", "OVERDUE"],
                        }
                    },
                    "required": [],
                },
            },
            {
                "name": "get_daily_briefing",
                "description": "Daily briefing: overdue, agenda, metrics",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
            {
                "name": "send_invoice",
                "description": "Email invoice to client (marks DRAFT->SENT)",
                "parameters": {
                    "type": "object",
                    "properties": {"invoice_id": {"type": "string"}},
                    "required": ["invoice_id"],
                },
            },
            {
                "name": "send_invoice_followup",
                "description": "Send follow-up for overdue invoice",
                "parameters": {
                    "type": "object",
                    "properties": {"invoice_id": {"type": "string"}},
                    "required": ["invoice_id"],
                },
            },
            {
                "name": "get_clients",
                "description": "All clients with basic info",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
            {
                "name": "get_verification_status",
                "description": "Verification tier (UNVERIFIED/BASIC/GST_VERIFIED)",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
            {
                "name": "record_transaction",
                "description": "Record INCOME or EXPENSE",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string", "enum": ["INCOME", "EXPENSE"]},
                        "amount": {"type": "number"},
                        "description": {"type": "string"},
                    },
                    "required": ["type", "amount", "description"],
                },
            },
        ]

    write_tools = {"send_invoice", "send_invoice_followup", "record_transaction"}

    # ── Public Entry Point ──────────────────────────────────────────────────────

    async def process(
        self,
        message: str,
        org_id: str,
        user_id: Optional[str] = None,
        business_id: str = "default",
        session_id: str = "default",
    ) -> dict:
        ctx = {"org_id": org_id, "user_id": user_id, "business_id": business_id}
        history: list[dict] = []

        for iteration in range(MAX_ITERATIONS):
            thought = await self._reason(message, ctx, history)
            logger.info(
                {
                    "event": "agent_iteration",
                    "iter": iteration + 1,
                    "thought": str(thought)[:200],
                }
            )

            action = str(thought.get("action", "")).split("|")[0].strip()

            if action == "respond":
                return self._format_response(
                    thought.get("response", ""), thought.get("ui_event")
                )

            tool_name = thought.get("tool")
            if not tool_name:
                return self._format_response(
                    thought.get("response", "I'm not sure how to help with that."),
                    thought.get("ui_event"),
                )

            tool_fn = self.tools.get(tool_name)
            if not tool_fn:
                history.append(
                    {
                        "role": "tool",
                        "tool": tool_name,
                        "content": f"Error: unknown tool '{tool_name}'",
                    }
                )
                continue

            args = thought.get("tool_args", {})
            args.setdefault("org_id", org_id)
            if user_id:
                args.setdefault("user_id", user_id)

            try:
                result = await tool_fn(args)
            except Exception as e:
                logger.error(
                    {"event": "tool_error", "tool": tool_name, "error": str(e)}
                )
                result = f"Tool error: {e}"

            history.append(
                {"role": "tool", "tool": tool_name, "content": str(result)[:1000]}
            )

            if iteration == 0:
                history_str = self._format_history(history)
                tool_result_text = history[-1]["content"]
                response_prompt = (
                    f"User asked: {message}\n"
                    f"Tool result: {tool_result_text}\n"
                    f"Respond to the user with the tool data. Be concise and factual.\n"
                    f'{{"action": "respond", "tool": null, "tool_args": {{}}, "response": "your answer", "ui_event": null}}'
                )
                thought2 = await self._reason(response_prompt, ctx, [])
                action2 = str(thought2.get("action", "")).split("|")[0].strip()
                if action2 == "respond":
                    return self._format_response(
                        thought2.get("response", tool_result_text),
                        thought2.get("ui_event"),
                    )
                return self._format_response(tool_result_text, None)

        return self._format_response(
            "I've gathered the information. Here's what I found: "
            + self._summarize_history(history),
            None,
        )

    # ── ReAct Reasoning ────────────────────────────────────────────────────────

    async def _reason(self, message: str, ctx: dict, history: list) -> dict:
        history_str = self._format_history(history)
        tools_str = "\n".join(
            f"- {t['name']}: {t['description']}" for t in self.tool_schemas
        )

        prompt = f"""You are a financial assistant for a small business in India. Be direct and decisive.

User: {message}
History: {history_str or "(empty)"}

Available tools:
{tools_str}

RULES:
- If history has a tool result (starts with "[TOOL via"), respond with action="respond" and summarize the data for the user. DO NOT call the same tool again.
- If NO tool result in history yet: call the right tool for the user's request.
  - "overdue"/"unpaid"/"past due" → get_overdue_invoices
  - "revenue"/"profit"/"expenses" → get_financial_metrics
  - "invoices" list → get_all_invoices
  - "briefing"/"morning"/"summary" → get_daily_briefing
  - "clients" → get_clients
  - "verification" tier → get_verification_status
  - "send"/"email" invoice → send_invoice (invoice_id if provided, else ask)
  - "remind"/"follow up" → send_invoice_followup (invoice_id if provided, else ask)
  - "record" transaction → record_transaction (needs type, amount, description)
- NEVER call the same tool twice in a row. If you just called a tool, RESPOND with the result.
- If tool result is "Error" or "Could not fetch", say you couldn't get the data and why.

JSON only, no markdown:
{{"action": "tool", "tool": "tool_name", "tool_args": {{}}, "response": "", "ui_event": null}}
OR
{{"action": "respond", "tool": null, "tool_args": {{}}, "response": "Your answer", "ui_event": null}}
"""

        for attempt, (key, model) in enumerate(
            [(GROQ_KEY_PRIMARY, GROQ_MODEL), (GROQ_KEY_FAST, GROQ_MODEL_FAST)]
        ):
            if not key:
                continue
            try:
                return await self._call_groq(prompt, key, model)
            except Exception as e:
                logger.warning(
                    {"event": "groq_retry", "attempt": attempt + 1, "error": str(e)}
                )
                if attempt == 0 and GROQ_KEY_FAST:
                    continue
                return {
                    "action": "respond",
                    "response": "I'm having trouble reasoning right now. Please try again.",
                }
        return {"action": "respond", "response": "No LLM keys configured."}

    async def _call_groq(self, prompt: str, api_key: str, model: str) -> dict:
        def _sync_call():
            resp = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 600,
                    "temperature": 0.3,
                },
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            if not content:
                raise ValueError(
                    f"Groq returned empty content (finish_reason={data['choices'][0].get('finish_reason')})"
                )
            return content

        try:
            content = await asyncio.to_thread(_sync_call)
        except requests.HTTPError as e:
            raise ValueError(f"Groq HTTP error: {e}")
        except ValueError:
            raise

        for prefix in ["```json", "```"]:
            if content.startswith(prefix):
                content = content[len(prefix) :]
            suffix = prefix.rstrip("`")
            if suffix and content.endswith(suffix):
                content = content[: -len(suffix)]

        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Invalid JSON from Groq: {e}. Content: {repr(content[:200])}"
            )

    # ── Tools ─────────────────────────────────────────────────────────────────

    async def _tool_get_financial_metrics(self, ctx: dict) -> str:
        r = await self.backend.get_finance_metrics(
            ctx.get("business_id", "default"), ctx["org_id"], ctx.get("user_id")
        )
        if not r.success or not r.data:
            return f"Could not fetch metrics: {r.error or 'unknown error'}"
        d = r.data
        return (
            f"Revenue: INR {d.get('revenue', 0):,.2f} | "
            f"Expenses: INR {d.get('expenses', 0):,.2f} | "
            f"Net Profit: INR {d.get('netProfit', 0):,.2f} | "
            f"Overdue: {d.get('overdueCount', 0)} invoices totalling INR {d.get('overdueAmount', 0):,.2f}"
        )

    async def _tool_get_overdue_invoices(self, ctx: dict) -> str:
        r = await self.backend._request(
            "GET",
            "/api/invoices/overdue",
            org_id=ctx["org_id"],
            user_id=ctx.get("user_id"),
        )
        if not r.success:
            return f"Error: {r.error}"
        invs = r.data if isinstance(r.data, list) else []
        if not invs:
            return "No overdue invoices."
        lines = []
        for inv in invs[:10]:
            amt = inv.get("totalAmount", 0)
            num = inv.get("invoiceNumber", "?")
            client = inv.get("clientName", "Unknown")
            due = inv.get("dueDate", "?")
            lines.append(f"- {num} | {client} | INR {amt:,.2f} | due {due}")
        total = sum(i.get("totalAmount", 0) for i in invs)
        return f"{len(invs)} overdue invoice(s), total INR {total:,.2f}:\n" + "\n".join(
            lines
        )

    async def _tool_get_all_invoices(self, ctx: dict) -> str:
        params = {"limit": ctx.get("limit", 20)}
        if ctx.get("status"):
            params["status"] = ctx["status"]
        r = await self.backend._request(
            "GET",
            "/api/invoices",
            params=params,
            org_id=ctx["org_id"],
            user_id=ctx.get("user_id"),
        )
        if not r.success:
            return f"Error: {r.error}"
        invs = r.data if isinstance(r.data, list) else []
        if not invs:
            return "No invoices found."
        by_status: dict[str, int] = {}
        for inv in invs:
            s = inv.get("status", "UNKNOWN")
            by_status[s] = by_status.get(s, 0) + 1
        return f"{len(invs)} invoice(s): " + ", ".join(
            f"{k}={v}" for k, v in by_status.items()
        )

    async def _tool_get_daily_briefing(self, ctx: dict) -> str:
        r_metrics = await self.backend.get_finance_metrics(
            ctx.get("business_id", "default"), ctx["org_id"], ctx.get("user_id")
        )
        r_overdue = await self.backend._request(
            "GET",
            "/api/invoices/overdue",
            org_id=ctx["org_id"],
            user_id=ctx.get("user_id"),
        )

        overdue_invs = (
            r_overdue.data
            if (r_overdue.success and isinstance(r_overdue.data, list))
            else []
        )
        overdue_total = sum(i.get("totalAmount", 0) for i in overdue_invs)
        overdue_count = len(overdue_invs)

        metrics = r_metrics.data if (r_metrics.success and r_metrics.data) else {}
        revenue = metrics.get("revenue", 0)
        expenses = metrics.get("expenses", 0)
        profit = metrics.get("netProfit", 0)

        agenda = []
        if overdue_count > 0:
            agenda.append(
                f"ACTION: Follow up on {overdue_count} overdue invoice(s) totalling INR {overdue_total:,.2f}"
            )
        if profit < 0:
            agenda.append("ALERT: Your business is currently operating at a loss")
        if revenue > 0:
            margin = (profit / revenue * 100) if revenue > 0 else 0
            if margin < 10:
                agenda.append(
                    f"NOTE: Profit margin is {margin:.1f}% — consider reviewing expenses"
                )
        if not agenda:
            agenda.append("Everything looks good — no urgent actions today")

        return (
            f"DAILY BRIEFING\n"
            f"Revenue: INR {revenue:,.2f} | Expenses: INR {expenses:,.2f} | Net: INR {profit:,.2f}\n"
            f"Overdue: {overdue_count} invoice(s) = INR {overdue_total:,.2f}\n"
            f"Today's Agenda:\n" + "\n".join(f"  • {a}" for a in agenda)
        )

    async def _tool_send_invoice(self, ctx: dict) -> str:
        if not ctx.get("invoice_id"):
            return "Error: invoice_id is required to send an invoice."
        r = await self.backend._request(
            "PATCH",
            f"/api/invoices/{ctx['invoice_id']}/send",
            org_id=ctx["org_id"],
            user_id=ctx.get("user_id"),
        )
        if not r.success:
            return f"Failed to send invoice: {r.error}"
        inv = r.data.get("data") if isinstance(r.data, dict) else r.data
        return f"Invoice {inv.get('invoiceNumber', ctx['invoice_id'])} sent successfully to {inv.get('clientEmail', 'the client')}."

    async def _tool_send_invoice_followup(self, ctx: dict) -> str:
        if not ctx.get("invoice_id"):
            return "Error: invoice_id is required to send a follow-up."
        r = await self.backend._request(
            "POST",
            f"/api/invoices/{ctx['invoice_id']}/send-followup",
            org_id=ctx["org_id"],
            user_id=ctx.get("user_id"),
        )
        if not r.success:
            return f"Failed to send follow-up: {r.error}"
        return "Follow-up email sent successfully."

    async def _tool_get_clients(self, ctx: dict) -> str:
        clients = await self.backend.get_clients(
            ctx["org_id"], user_id=ctx.get("user_id")
        )
        if not clients:
            return "No clients found."
        lines = [
            f"{c.get('display_name', c.get('name', '?'))} ({c.get('email', 'no email')}) [{c.get('status', '?')}]"
            for c in clients[:15]
        ]
        return f"{len(clients)} client(s):\n" + "\n".join(f"  • {l}" for l in lines)

    async def _tool_get_verification_status(self, ctx: dict) -> str:
        r = await self.backend._request(
            "GET",
            "/api/org/verify/status",
            org_id=ctx["org_id"],
            user_id=ctx.get("user_id"),
        )
        if not r.success:
            return f"Could not fetch verification status: {r.error}"
        data = r.data.get("data") if isinstance(r.data, dict) else r.data
        tier = (
            data.get("verificationTier", "UNVERIFIED")
            if isinstance(data, dict)
            else "UNKNOWN"
        )
        return f"Verification tier: {tier}"

    async def _tool_record_transaction(self, ctx: dict) -> str:
        r = await self.backend._request(
            "POST",
            "/api/transactions",
            data={
                "type": ctx["type"],
                "amount": ctx["amount"],
                "category": ctx.get("category", "General"),
                "description": ctx["description"],
                "currency": ctx.get("currency", "INR"),
            },
            org_id=ctx["org_id"],
            user_id=ctx.get("user_id"),
        )
        if not r.success:
            return f"Failed to record transaction: {r.error}"
        return f"Transaction recorded: {ctx['type']} of INR {ctx['amount']:,.2f}"

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _format_history(self, history: list) -> str:
        if not history:
            return ""
        return "\n".join(
            f"[{h['role'].upper()} via {h.get('tool', 'chat')}]: {h['content'][:300]}"
            for h in history[-6:]
        )

    def _summarize_history(self, history: list) -> str:
        if not history:
            return "No information available."
        return " ".join(h["content"][:200] for h in history[-3:])

    def _format_response(self, message: str, ui_event: Optional[dict]) -> dict:
        return {
            "message": message,
            "success": True,
            "agent_type": "intelligent_agent",
            "ui_event": ui_event,
        }


intelligent_agent = IntelligentAgent()
