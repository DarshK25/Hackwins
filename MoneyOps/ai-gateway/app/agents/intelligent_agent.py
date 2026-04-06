"""
Intelligent Agent — unified reasoning agent for MoneyOps.
Handles voice and text queries with memory, business context, and tool execution.
"""

import os
import json
import asyncio
import re
import requests
from typing import Any, Optional
from app.adapters.backend_adapter import get_backend_adapter
from app.utils.logger import get_logger
from app.utils.tts_sanitizer import sanitize_for_tts

logger = get_logger(__name__)

GROQ_KEY_PRIMARY = os.getenv("GROQ_API_KEY", "")
GROQ_KEY_FAST = os.getenv("GROQ_API_KEY_FAST", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_MODEL_FAST = "llama-3.1-8b-instant"
MAX_ITERATIONS = 2


class IntelligentAgent:
    def __init__(self):
        self.backend = get_backend_adapter()

    @property
    def tools(self) -> dict:
        return {
            "get_financial_metrics": self._tool_get_financial_metrics,
            "get_overdue_invoices": self._tool_get_overdue_invoices,
            "get_all_invoices": self._tool_get_all_invoices,
            "get_daily_briefing": self._tool_get_daily_briefing,
            "create_invoice": self._tool_create_invoice,
            "send_invoice": self._tool_send_invoice,
            "send_invoice_followup": self._tool_send_invoice_followup,
            "get_clients": self._tool_get_clients,
            "create_client": self._tool_create_client,
            "get_client_details": self._tool_get_client_details,
            "get_verification_status": self._tool_get_verification_status,
            "record_transaction": self._tool_record_transaction,
            "get_transactions": self._tool_get_transactions,
            "get_invoice_details": self._tool_get_invoice_details,
            "get_business_context": self._tool_get_business_context,
            "search_market": self._tool_search_market,
            "check_compliance": self._tool_check_compliance,
            "recall": self._tool_recall,
            "remember": self._tool_remember,
            "draft_followup_email": self._tool_draft_followup_email,
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
                "name": "get_invoice_details",
                "description": "Full details of a specific invoice",
                "parameters": {
                    "type": "object",
                    "properties": {"invoice_id": {"type": "string"}},
                    "required": ["invoice_id"],
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
                "description": "List all clients",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
            {
                "name": "get_client_details",
                "description": "Full details of a specific client including payment history",
                "parameters": {
                    "type": "object",
                    "properties": {"client_id": {"type": "string"}},
                    "required": ["client_id"],
                },
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
                        "category": {"type": "string"},
                    },
                    "required": ["type", "amount", "description"],
                },
            },
            {
                "name": "get_transactions",
                "description": "Get transaction history (income/expense)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string", "enum": ["INCOME", "EXPENSE"]},
                        "limit": {"type": "integer"},
                    },
                    "required": [],
                },
            },
            {
                "name": "get_business_context",
                "description": "Get business info from onboarding: industry, sector, services, target market",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
            {
                "name": "search_market",
                "description": "Search market news and trends relevant to business",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            },
            {
                "name": "check_compliance",
                "description": "Check GST/TDS deadlines and liability",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "check_type": {
                            "type": "string",
                            "enum": [
                                "deadlines",
                                "gst_liability",
                                "tds_reconciliation",
                            ],
                        }
                    },
                    "required": ["check_type"],
                },
            },
            {
                "name": "recall",
                "description": "Search past conversation memory for relevant context",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            },
            {
                "name": "remember",
                "description": "Save important fact to long-term memory",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string"},
                        "type": {
                            "type": "string",
                            "enum": ["business_fact", "user_preference", "reminder"],
                        },
                        "tags": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["content", "type"],
                },
            },
            {
                "name": "draft_followup_email",
                "description": "Draft a professional follow-up email for overdue invoice",
                "parameters": {
                    "type": "object",
                    "properties": {"invoice_id": {"type": "string"}},
                    "required": ["invoice_id"],
                },
            },
            {
                "name": "create_invoice",
                "description": "Start creating a new invoice - initiates guided invoice creation flow",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "client_id": {"type": "string"},
                        "amount": {"type": "number"},
                        "description": {"type": "string"},
                    },
                    "required": [],
                },
            },
            {
                "name": "create_client",
                "description": "Add a new client to the organization",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "email": {"type": "string"},
                        "phone": {"type": "string"},
                        "gst_number": {"type": "string"},
                    },
                    "required": ["name"],
                },
            },
        ]

    write_tools = {
        "send_invoice",
        "send_invoice_followup",
        "record_transaction",
        "create_client",
    }

    async def process(
        self,
        message: str,
        org_id: str,
        user_id: Optional[str] = None,
        business_id: str = "default",
        session_id: str = "default",
        channel: str = "voice",
    ) -> dict:
        ctx = {
            "org_id": org_id,
            "user_id": user_id,
            "business_id": business_id,
            "session_id": session_id,
            "raw_text": message,
        }
        msg_lower = message.lower()

        tool_name, args = self._route_query(msg_lower)

        if not tool_name:
            response = self._generate_direct_response(message, msg_lower)
            if channel == "voice":
                response = sanitize_for_tts(response)
            return self._format_response(response, None)

        tool_fn = self.tools.get(tool_name)
        if not tool_fn:
            return self._format_response(f"I don't have a tool for that.", None)

        args.setdefault("org_id", org_id)
        if user_id:
            args.setdefault("user_id", user_id)
        args.setdefault("session_id", session_id)
        args.setdefault("raw_text", message)

        try:
            result = await tool_fn(args)
        except Exception as e:
            logger.error({"event": "tool_error", "tool": tool_name, "error": str(e)})
            result = f"Error: {e}"

        ui_event = None
        if isinstance(result, tuple) and len(result) == 2:
            response_text, ui_event = result
            response = self._format_tool_result(message, response_text, tool_name)
        else:
            response = self._format_tool_result(message, result, tool_name)

        if channel == "voice" and isinstance(response, str):
            response = sanitize_for_tts(response)
        return self._format_response(response, ui_event)

    def _route_query(self, msg: str) -> tuple[Optional[str], dict]:
        """Route query to appropriate tool based on keywords."""
        args = {}

        if any(
            k in msg for k in ["revenue", "profit", "expenses", "financial metrics"]
        ):
            return "get_financial_metrics", args
        if any(k in msg for k in ["overdue", "unpaid", "past due"]):
            return "get_overdue_invoices", args
        if "create" in msg and "invoice" in msg:
            return "create_invoice", args
        if "create" in msg and ("client" in msg or "customer" in msg):
            return "create_client", args
        if any(k in msg for k in ["invoice", "invoices"]):
            if "all" in msg or "list" in msg:
                return "get_all_invoices", args
            return "get_all_invoices", args
        if any(k in msg for k in ["briefing", "morning", "summary", "daily"]):
            return "get_daily_briefing", args
        if any(k in msg for k in ["market", "trend", "competitor", "sector news"]):
            return "search_market", {"query": msg}
        if any(
            k in msg
            for k in ["remember that", "save this", "note that", "don't forget"]
        ):
            return "remember", {
                "content": msg,
                "type": "user_preference",
                "tags": ["preference"],
            }
        if any(
            k in msg
            for k in ["what do you remember", "what did i tell you", "do you recall"]
        ):
            return "recall", {"query": msg}
        if any(k in msg for k in ["client", "customers"]):
            if "create" in msg:
                return "create_client", args
            return "get_clients", args
        if any(
            k in msg
            for k in ["business", "sector", "industry", "services", "what do i do"]
        ):
            return "get_business_context", args
        if any(k in msg for k in ["transaction", "expense", "income"]):
            return "get_transactions", args
        if any(k in msg for k in ["verification", "tier", "trust"]):
            return "get_verification_status", args
        if any(k in msg for k in ["compliance", "gst", "tds", "deadline", "filing"]):
            if "gst" in msg and "liability" in msg:
                args["check_type"] = "gst_liability"
            elif "tds" in msg:
                args["check_type"] = "tds_reconciliation"
            else:
                args["check_type"] = "deadlines"
            return "check_compliance", args

        return None, {}

    def _generate_direct_response(self, message: str, msg_lower: str) -> str:
        """Generate direct response for greetings and simple queries."""
        if any(k in msg_lower for k in ["hi", "hello", "hey"]):
            return "Hello! I'm your financial assistant. Ask me about your revenue, invoices, clients, or anything about your business."
        if any(k in msg_lower for k in ["thanks", "thank you"]):
            return "You're welcome! Let me know if you need anything else."
        if any(k in msg_lower for k in ["help", "what can you do"]):
            return "I can help you with: revenue and profit, overdue invoices, client management, daily briefings, transactions, and compliance checks."
        return "I'm not sure I understand. Try asking about your revenue, invoices, clients, or business overview."

    def _format_tool_result(
        self, original_msg: str, result: str, tool_name: str
    ) -> str:
        """Format tool result into a natural response."""
        if "Error" in result or "could not" in result.lower():
            return result
        if tool_name == "get_financial_metrics":
            return result
        if tool_name == "get_overdue_invoices":
            return result
        if tool_name == "get_all_invoices":
            return result
        if tool_name == "get_daily_briefing":
            return result
        if tool_name == "get_clients":
            return result
        if tool_name == "get_business_context":
            return result
        if tool_name == "get_transactions":
            return result
        if tool_name == "get_verification_status":
            return result
        if tool_name == "check_compliance":
            return result
        if tool_name == "search_market":
            return result
        if tool_name == "recall":
            return result
        return result

    async def _get_business_context_for_prompt(
        self, org_id: str, user_id: Optional[str]
    ) -> str:
        try:
            r = await self.backend.get_onboarding_status(user_id or org_id)
            if r.success and r.data:
                data = r.data if isinstance(r.data, dict) else {}
                business = data.get("business", {})
                if not business:
                    business = data
                name = (
                    business.get("legalName")
                    or business.get("businessName")
                    or "your business"
                )
                industry = business.get("industry") or "general"
                sector = business.get("targetMarket") or "B2B"
                services = business.get("primaryActivity") or "business services"
                gstin = business.get("gstin") or "not registered"
                return (
                    f"BUSINESS: {name}\n"
                    f"Industry: {industry}\n"
                    f"Sector: {sector}\n"
                    f"Services: {services}\n"
                    f"GSTIN: {gstin}"
                )
        except Exception as e:
            logger.warning({"event": "business_context_load_failed", "error": str(e)})
        return "Business information not available"

    async def _get_memory_context(self, org_id: str) -> str:
        try:
            resp = requests.get(
                f"http://127.0.0.1:8000/api/memory/{org_id}?limit=5",
                headers={"X-Org-Id": org_id},
                timeout=5,
            )
            if resp.status_code == 200:
                memories = resp.json()
                if memories:
                    lines = [
                        f"- {m.get('content', '')}"
                        for m in memories[:5]
                        if m.get("content")
                    ]
                    return "\n\nWHAT I REMEMBER:\n" + "\n".join(lines)
        except Exception:
            pass
        return ""

    async def _reason(
        self,
        message: str,
        ctx: dict,
        history: list,
        business_context: str,
        memory_context: str,
    ) -> dict:
        history_str = (
            "\n".join(
                f"- {h['content'][:100]}" for h in history[-4:] if h.get("content")
            )
            if history
            else "(empty)"
        )

        tools_str = "\n".join(
            f"- {t['name']}: {t['description']}" for t in self.tool_schemas
        )

        prompt = f"""User: {message}

Always call a tool when the user asks about business data.

Tools: {tools_str}

Examples:
- "revenue/profit/expenses" -> get_financial_metrics
- "overdue/unpaid" -> get_overdue_invoices
- "invoices" -> get_all_invoices
- "clients/customers" -> get_clients
- "briefing/morning/summary" -> get_daily_briefing
- "business/sector/industry" -> get_business_context
- "transactions/expenses/income" -> get_transactions

JSON only:
{{"action": "tool", "tool": "TOOL_NAME", "tool_args": {{}}}}
OR
{{"action": "respond", "response": "text"}}
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
                    f"Empty response (finish_reason={data['choices'][0].get('finish_reason')})"
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
            raise ValueError(f"Invalid JSON: {e}. Content: {repr(content[:200])}")

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
            days_over = inv.get("daysOverdue", 0)
            lines.append(
                f"- {num} | {client} | INR {amt:,.2f} | due {due} | {days_over} days overdue"
            )
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

    async def _tool_get_invoice_details(self, ctx: dict) -> str:
        if not ctx.get("invoice_id"):
            return "Error: invoice_id is required"
        r = await self.backend._request(
            "GET",
            f"/api/invoices/{ctx['invoice_id']}",
            org_id=ctx["org_id"],
            user_id=ctx.get("user_id"),
        )
        if not r.success:
            return f"Error: {r.error}"
        inv = r.data if isinstance(r.data, dict) else {}
        return (
            f"Invoice {inv.get('invoiceNumber', '?')} for {inv.get('clientName', 'Unknown')}: "
            f"INR {inv.get('totalAmount', 0):,.2f}, Status: {inv.get('status', '?')}, "
            f"Due: {inv.get('dueDate', '?')}, "
            f"Paid: INR {inv.get('paidAmount', 0):,.2f}"
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

    async def _tool_create_invoice(self, ctx: dict) -> tuple:
        from app.voice_processor import VoiceContext
        from app.agents.finance_agent import finance_agent

        session_id = ctx.get("session_id", "default")
        user_id = ctx.get("user_id")
        org_id = ctx["org_id"]

        voice_ctx = VoiceContext(
            session_id=session_id,
            user_id=user_id or "unknown",
            org_uuid=org_id,
            business_id=1,
        )
        voice_ctx.raw_text = ctx.get("raw_text", "")
        voice_ctx.extracted_entities = []

        result = await finance_agent.handle_invoice_create(voice_ctx)
        return result.message, result.ui_event

    async def _tool_create_client(self, ctx: dict) -> str:
        name = ctx.get("name", "")
        email = ctx.get("email", "")
        phone = ctx.get("phone", "")
        gst = ctx.get("gst_number", "")
        raw_text = ctx.get("raw_text", "")

        if not name and raw_text:
            name = self._extract_name_from_text(raw_text)

        if not name:
            return "To create a client, please tell me the client name. You can also add email, phone, and GST number."

        payload = {
            "displayName": name,
            "email": email if email else None,
            "phone": phone if phone else None,
            "gstNumber": gst if gst else None,
            "status": "ACTIVE",
        }

        r = await self.backend.create_client(
            org_id=ctx["org_id"],
            user_id=ctx.get("user_id"),
            payload=payload,
        )

        if not r.success:
            return f"Failed to create client: {r.error}"

        client = r.data if isinstance(r.data, dict) else {}
        client_name = client.get("displayName", name)
        return f"Client '{client_name}' has been created successfully."

    def _extract_name_from_text(self, text: str) -> str:
        text_lower = text.lower()
        match = re.search(
            r"named\s+([A-Za-z0-9\s]+?)(?:\s+with|\s+and|\s+email|$)",
            text,
            re.IGNORECASE,
        )
        if match:
            return match.group(1).strip()
        match = re.search(
            r"client\s+(?:named\s+)?([A-Za-z0-9\s]+?)(?:\s+with|\s+and|$)",
            text,
            re.IGNORECASE,
        )
        if match:
            return match.group(1).strip()
        match = re.search(
            r"create\s+(?:a\s+)?(?:new\s+)?client\s+(?:named\s+)?([A-Za-z0-9\s]+?)(?:\s+with|\s+and|$)",
            text,
            re.IGNORECASE,
        )
        if match:
            return match.group(1).strip()
        words = text.split()
        if len(words) > 2:
            name_start = -1
            for i, w in enumerate(words):
                if w.lower() in ["named", "client", "customer"]:
                    name_start = i + 1
                    break
            if name_start > 0 and name_start < len(words):
                name_words = []
                for w in words[name_start:]:
                    if w.lower() in ["with", "and", "email", "phone", "gst"]:
                        break
                    name_words.append(w)
                if name_words:
                    return " ".join(name_words).strip()
        return ""

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

    async def _tool_get_client_details(self, ctx: dict) -> str:
        if not ctx.get("client_id"):
            return "Error: client_id is required"
        r = await self.backend._request(
            "GET",
            f"/api/clients/{ctx['client_id']}",
            org_id=ctx["org_id"],
            user_id=ctx.get("user_id"),
        )
        if not r.success:
            return f"Error: {r.error}"
        client = r.data if isinstance(r.data, dict) else {}
        return (
            f"Client: {client.get('display_name', client.get('name', '?'))}\n"
            f"Email: {client.get('email', 'not available')}\n"
            f"Phone: {client.get('phone', 'not available')}\n"
            f"Status: {client.get('status', '?')}\n"
            f"GST: {client.get('gstNumber', 'not available')}"
        )

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
                "currency": "INR",
            },
            org_id=ctx["org_id"],
            user_id=ctx.get("user_id"),
        )
        if not r.success:
            return f"Failed to record transaction: {r.error}"
        return f"Transaction recorded: {ctx['type']} of INR {ctx['amount']:,.2f}"

    async def _tool_get_transactions(self, ctx: dict) -> str:
        params = {"limit": ctx.get("limit", 20)}
        if ctx.get("type"):
            params["type"] = ctx["type"]
        r = await self.backend._request(
            "GET",
            "/api/transactions",
            params=params,
            org_id=ctx["org_id"],
            user_id=ctx.get("user_id"),
        )
        if not r.success:
            return f"Error: {r.error}"
        txns = r.data if isinstance(r.data, list) else []
        if not txns:
            return "No transactions found."
        lines = []
        for t in txns[:10]:
            amt = t.get("amount", 0)
            typ = t.get("type", "?")
            desc = t.get("description", "?")
            date = t.get("createdAt", "?")[:10] if t.get("createdAt") else "?"
            lines.append(f"- {typ}: INR {amt:,.2f} | {desc} | {date}")
        return f"{len(txns)} transaction(s):\n" + "\n".join(lines)

    async def _tool_get_business_context(self, ctx: dict) -> str:
        try:
            r = await self.backend.get_onboarding_status(
                ctx.get("user_id") or ctx["org_id"]
            )
            if r.success and r.data:
                data = r.data if isinstance(r.data, dict) else {}
                business = data.get("business", {})
                if not business:
                    business = data
                return (
                    f"Business: {business.get('legalName', business.get('businessName', 'Not set'))}\n"
                    f"Industry: {business.get('industry', 'Not set')}\n"
                    f"Sector: {business.get('targetMarket', 'Not set')}\n"
                    f"Services: {business.get('primaryActivity', 'Not set')}\n"
                    f"GSTIN: {business.get('gstin', 'Not registered')}"
                )
        except Exception as e:
            logger.warning({"event": "business_context_error", "error": str(e)})
        return "Could not load business context."

    async def _tool_search_market(self, ctx: dict) -> str:
        try:
            from app.tools.multi_source_search import MultiSourceSearch

            searcher = MultiSourceSearch()
            results = await searcher.search(ctx.get("query", ""), max_results=5)
            if results and isinstance(results, dict):
                articles = results.get("articles", []) or results.get("results", [])[:3]
                if articles:
                    lines = [f"- {a.get('title', 'Untitled')}" for a in articles[:3]]
                    sources = [a.get("url", "") for a in articles[:2] if a.get("url")]
                    return (
                        f"Market insights:\n"
                        + "\n".join(lines)
                        + "\n\nSources: "
                        + ", ".join(sources[:2])
                    )
        except Exception as e:
            logger.warning({"event": "market_search_failed", "error": str(e)})
        return "Could not fetch market information."

    async def _tool_check_compliance(self, ctx: dict) -> str:
        check_type = ctx.get("check_type", "deadlines")
        if check_type == "deadlines":
            return (
                "Compliance deadlines:\n"
                "- GSTR-1: 10th of next month\n"
                "- GSTR-3B: 20th of next month\n"
                "- TDS deposit: 7th of next month\n"
                "- ITR filing: July 31st (individuals) / October 31st (businesses)"
            )
        elif check_type == "gst_liability":
            r = await self.backend._request(
                "GET",
                "/api/invoices",
                params={"limit": 100},
                org_id=ctx["org_id"],
                user_id=ctx.get("user_id"),
            )
            if r.success and isinstance(r.data, list):
                total = sum(i.get("totalAmount", 0) for i in r.data)
                gst = sum(i.get("gstAmount", 0) for i in r.data)
                return f"GST collected: approximately INR {gst:,.2f} on total invoiced INR {total:,.2f}. Net liability depends on input tax credit from expenses."
            return "Could not calculate GST liability."
        elif check_type == "tds_reconciliation":
            return "TDS reconciliation: Check your Form 26AS for TDS credits from enterprise clients like Infosys, TCS, etc. These appear as credit in your ITR."
        return "Unknown compliance check type."

    async def _tool_recall(self, ctx: dict) -> str:
        try:
            resp = requests.get(
                f"http://127.0.0.1:8000/api/memory/{ctx['org_id']}?query={ctx.get('query', '')}&limit=3",
                headers={"X-Org-Id": ctx["org_id"]},
                timeout=5,
            )
            if resp.status_code == 200:
                memories = resp.json()
                if memories:
                    lines = [
                        f"- {m.get('content', '')}"
                        for m in memories
                        if m.get("content")
                    ]
                    return "What I remember: " + " | ".join(lines)
        except Exception as e:
            logger.warning({"event": "recall_failed", "error": str(e)})
        return "I don't have any relevant memories stored."

    async def _tool_remember(self, ctx: dict) -> str:
        try:
            resp = requests.post(
                f"http://127.0.0.1:8000/api/memory/{ctx['org_id']}",
                headers={"X-Org-Id": ctx["org_id"], "Content-Type": "application/json"},
                json={
                    "content": ctx["content"],
                    "type": ctx.get("type", "business_fact"),
                    "tags": ctx.get("tags", []),
                },
                timeout=5,
            )
            if resp.status_code in (200, 201):
                return "I've remembered that."
        except Exception as e:
            logger.warning({"event": "remember_failed", "error": str(e)})
        return "Could not save to memory."

    async def _tool_draft_followup_email(self, ctx: dict) -> str:
        if not ctx.get("invoice_id"):
            return "Error: invoice_id is required to draft follow-up email."
        r = await self.backend._request(
            "GET",
            f"/api/invoices/{ctx['invoice_id']}",
            org_id=ctx["org_id"],
            user_id=ctx.get("user_id"),
        )
        if not r.success:
            return f"Could not get invoice details: {r.error}"
        inv = r.data if isinstance(r.data, dict) else {}
        client = inv.get("clientName", "Client")
        amount = inv.get("totalAmount", 0)
        inv_num = inv.get("invoiceNumber", "?")
        due = inv.get("dueDate", "?")
        days_over = inv.get("daysOverdue", 0)
        return (
            f"Follow-up email draft for {client}:\n\n"
            f"Subject: Payment Reminder - Invoice {inv_num} | INR {amount:,.2f}\n\n"
            f"Dear {client},\n\n"
            f"This is a friendly reminder that Invoice {inv_num} for INR {amount:,.2f} "
            f"(dated {due}) is {days_over} days overdue.\n\n"
            f"We kindly request you to process the payment at your earliest convenience. "
            f"If you have already made the payment, please disregard this reminder.\n\n"
            f"Best regards"
        )

    def _format_response(self, message: str, ui_event: Optional[dict]) -> dict:
        return {
            "message": message,
            "success": True,
            "agent_type": "intelligent_agent",
            "ui_event": ui_event,
        }


intelligent_agent = IntelligentAgent()
