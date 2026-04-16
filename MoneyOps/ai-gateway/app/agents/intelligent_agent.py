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
from app.adapters.backend_adapter import get_backend_adapter, normalize_business_id
from app.config import settings
from app.state.session_manager import session_manager
from app.utils.logger import get_logger
from app.utils.tts_sanitizer import sanitize_for_tts

logger = get_logger(__name__)

GROQ_KEY_PRIMARY = settings.GROQ_API_KEY
GROQ_KEY_FAST = settings.GROQ_API_KEY_FAST or ""
GROQ_MODEL = settings.GROQ_MODEL or "llama-3.3-70b-versatile"
GROQ_MODEL_FAST = "llama-3.1-8b-instant"
MAX_ITERATIONS = 2


class IntelligentAgent:
    def __init__(self):
        self.backend = get_backend_adapter()

    @staticmethod
    def _clean_business_value(value: Any) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        if text.lower() in {"not set", "none", "null", "unknown", "n/a"}:
            return None
        return text

    def _extract_business_profile(self, payload: dict) -> dict[str, Optional[str]]:
        business = payload.get("business", {}) if isinstance(payload, dict) else {}
        business = business if isinstance(business, dict) else {}
        source = business or (payload if isinstance(payload, dict) else {})

        return {
            "name": self._clean_business_value(
                source.get("legalName")
                or source.get("businessName")
                or source.get("tradingName")
                or source.get("name")
            ),
            "industry": self._clean_business_value(source.get("industry")),
            "sector": self._clean_business_value(
                source.get("targetMarket")
                or source.get("market")
                or source.get("customerType")
            ),
            "services": self._clean_business_value(
                source.get("primaryActivity")
                or source.get("keyProducts")
                or source.get("services")
                or source.get("offerings")
            ),
            "gstin": self._clean_business_value(
                source.get("gstin") or source.get("gstNumber")
            ),
        }

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
            "record_payment": self._tool_record_payment,
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
                "name": "record_payment",
                "description": "Record payment against the most relevant invoice",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "invoice_id": {"type": "string"},
                        "client_name": {"type": "string"},
                        "amount": {"type": "number"},
                    },
                    "required": [],
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
        "record_payment",
        "record_transaction",
        "create_client",
    }

    async def process(
        self,
        message: str,
        org_id: str,
        user_id: Optional[str] = None,
        business_id: str = "1",
        session_id: str = "default",
        channel: str = "voice",
    ) -> dict:
        normalized_business_id = normalize_business_id(business_id)
        ctx = {
            "org_id": org_id,
            "user_id": user_id,
            "business_id": normalized_business_id,
            "session_id": session_id,
            "raw_text": message,
        }
        msg_lower = message.lower()

        session = session_manager.get_session(
            session_id,
            user_id or "unknown",
            org_id,
            int(normalized_business_id) if str(normalized_business_id).isdigit() else 1,
        )
        business_context = await self._get_business_context_for_prompt(org_id, user_id)
        memory_context = await self._get_memory_context(org_id)
        recent_history = session.history[-10:]
        tool_name, args = self._route_query(msg_lower, session)

        ui_event = None
        result_text = None
        if tool_name:
            tool_fn = self.tools.get(tool_name)
            if not tool_fn:
                result_text = "I could not route that request correctly."
            else:
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

                if isinstance(result, tuple) and len(result) == 2:
                    response_text, ui_event = result
                    result_text = self._format_tool_result(message, response_text, tool_name)
                else:
                    result_text = self._format_tool_result(message, result, tool_name)
        else:
            result_text = self._generate_direct_response(message, msg_lower)

        response = await self._synthesize_final_response(
            user_message=message,
            tool_name=tool_name,
            tool_result=result_text,
            business_context=business_context,
            memory_context=memory_context,
            history=recent_history,
        )

        session.last_tool = tool_name
        session.history.append({"role": "user", "content": message, "intent": tool_name})
        session.history.append({"role": "assistant", "content": response, "intent": tool_name})
        if len(session.history) > 20:
            session.history = session.history[-20:]
        session_manager.save_session(session)

        if channel == "voice" and isinstance(response, str):
            response = sanitize_for_tts(response)
        return self._format_response(response, ui_event)

    def _route_query(self, msg: str, session=None) -> tuple[Optional[str], dict]:
        """Route query to appropriate tool based on keywords."""
        args = {}

        if self._is_business_context_followup(msg, session):
            return "get_business_context", args
        if self._is_market_followup(msg, session):
            return "search_market", {"query": msg, "followup": True}
        if self._is_invoice_followup(msg, session):
            return "get_all_invoices", self._invoice_followup_args(msg, session)

        if self._should_continue_locked_invoice(msg, session):
            return "create_invoice", args
        if any(
            phrase in msg
            for phrase in [
                "send invoice",
                "email invoice",
                "share invoice",
                "send the invoice",
                "email the invoice",
                "send overdue invoice",
                "email overdue invoice",
                "send the overview invoice",
                "send the overdue invoice",
            ]
        ):
            return "send_invoice", {"client_name": self._extract_client_name_hint(msg, session), "status": "OVERDUE" if any(k in msg for k in ["overdue", "overview"]) else None}
        if any(
            phrase in msg
            for phrase in [
                "send reminder",
                "remind",
                "follow up",
                "follow-up",
                "alert them to pay",
                "email them to pay",
            ]
        ):
            return "send_invoice_followup", {"client_name": self._extract_client_name_hint(msg, session)}
        if any(
            phrase in msg
            for phrase in [
                "mark paid",
                "record payment",
                "invoice is paid",
                "they paid",
            ]
        ):
            parsed_amount = self._extract_amount(msg)
            return "record_payment", {
                "client_name": self._extract_client_name_hint(msg, session),
                "amount": parsed_amount,
            }
        if any(
            phrase in msg
            for phrase in [
                "how is my business doing",
                "how is our business doing",
                "how are we doing",
                "how is business doing",
                "how is my business doing so far",
            ]
        ):
            return "get_daily_briefing", args
        if any(
            phrase in msg
            for phrase in [
                "what does my business do",
                "what does our business do",
                "what do we do",
                "what do you know about my business",
                "services it provides",
            ]
        ):
            return "get_business_context", args
        if any(
            k in msg for k in ["revenue", "profit", "expenses", "financial metrics"]
        ):
            if "invoice" in msg or "paid invoice" in msg:
                invoice_args = self._invoice_followup_args(msg, session)
                invoice_args["metric"] = "revenue"
                return "get_all_invoices", invoice_args
            return "get_financial_metrics", args
        if any(k in msg for k in ["overdue", "unpaid", "past due"]):
            return "get_overdue_invoices", args
        if "create" in msg and "invoice" in msg:
            return "create_invoice", args
        if "create" in msg and ("client" in msg or "customer" in msg):
            return "create_client", args
        if any(k in msg for k in ["invoice", "invoices"]):
            return "get_all_invoices", self._invoice_followup_args(msg, session)
        if any(k in msg for k in ["briefing", "morning", "summary", "daily"]):
            return "get_daily_briefing", args
        if any(
            k in msg
            for k in [
                "market",
                "trend",
                "competitor",
                "sector news",
                "market updates",
                "industry updates",
            ]
        ):
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
            if any(k in msg for k in ["add expense", "record expense", "expense of", "rent expense", "salary expense"]):
                parsed_amount = self._extract_amount(msg)
                category = self._infer_expense_category(msg)
                return "record_transaction", {
                    "type": "EXPENSE",
                    "amount": parsed_amount or 0,
                    "category": category,
                    "description": self._extract_transaction_description(msg, category),
                }
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

    def _is_business_context_followup(self, msg: str, session) -> bool:
        if not session or session.last_tool != "get_business_context":
            return False

        business_followup_phrases = [
            "what sector",
            "which sector",
            "what industry",
            "which industry",
            "actually",
            "what exactly",
            "what does that mean",
            "tell me again",
        ]
        return any(phrase in msg for phrase in business_followup_phrases)

    def _is_market_followup(self, msg: str, session) -> bool:
        if not session or session.last_tool != "search_market":
            return False

        market_followup_phrases = [
            "and how",
            "how will this affect",
            "how does this affect",
            "what does this mean",
            "what should i do",
            "what should we do",
            "why does this matter",
        ]
        return any(phrase in msg for phrase in market_followup_phrases)

    def _is_invoice_followup(self, msg: str, session) -> bool:
        if not session or session.last_tool not in {
            "get_all_invoices",
            "get_overdue_invoices",
            "send_invoice",
            "send_invoice_followup",
        }:
            return False

        invoice_followup_phrases = [
            "are there",
            "how many",
            "paid invoices",
            "sent invoices",
            "draft invoices",
            "overdue invoices",
            "which client",
            "which clients",
            "what's my revenue",
            "what is my revenue",
            "email it",
            "send it",
            "send that",
            "email that",
        ]
        return any(phrase in msg for phrase in invoice_followup_phrases) or len(msg.split()) <= 4

    def _invoice_followup_args(self, msg: str, session) -> dict:
        args: dict[str, Any] = {}
        if "paid" in msg:
            args["status"] = "PAID"
        elif "draft" in msg:
            args["status"] = "DRAFT"
        elif "sent" in msg:
            args["status"] = "SENT"
        elif "overdue" in msg or (session and session.last_tool == "get_overdue_invoices"):
            args["status"] = "OVERDUE"

        if "revenue" in msg or "total amount" in msg or "worth" in msg:
            args["metric"] = "revenue"
        if "how many" in msg or "are there" in msg:
            args["metric"] = args.get("metric") or "count"
        return args

    def _extract_client_name_hint(self, msg: str, session) -> Optional[str]:
        if session and session.last_invoice_results:
            if len(session.last_invoice_results) == 1:
                return session.last_invoice_results[0].get("clientName")
        return None

    def _extract_amount(self, msg: str) -> Optional[float]:
        match = re.search(r"(\d[\d,]*(?:\.\d+)?)", msg)
        if not match:
            return None
        try:
            return float(match.group(1).replace(",", ""))
        except ValueError:
            return None

    def _infer_expense_category(self, msg: str) -> str:
        mapping = {
            "salary": "SALARY",
            "rent": "RENT",
            "utility": "UTILITIES",
            "electricity": "UTILITIES",
            "hardware": "HARDWARE",
            "fuel": "FUEL",
            "software": "SOFTWARE",
            "legal": "LEGAL",
        }
        for token, category in mapping.items():
            if token in msg:
                return category
        return "MISC"

    def _extract_transaction_description(self, msg: str, category: str) -> str:
        cleaned = re.sub(r"(\d[\d,]*(?:\.\d+)?)", "", msg).strip()
        cleaned = re.sub(r"\b(add|record|expense|of|for|rupees|inr)\b", "", cleaned).strip()
        return cleaned or category.replace("_", " ").title()

    def _should_continue_locked_invoice(self, msg: str, session) -> bool:
        if not session or session.locked_intent != "INVOICE_CREATE":
            return False

        if session.invoice_draft is None:
            return False

        short_follow_up = len(msg.split()) <= 8
        invoice_stage_words = [
            "yes",
            "no",
            "cancel",
            "product",
            "service",
            "gst",
            "quantity",
            "due",
            "tomorrow",
            "today",
            "amount",
            "rupees",
        ]
        has_digits = any(ch.isdigit() for ch in msg)

        return short_follow_up or has_digits or any(word in msg for word in invoice_stage_words)

    def _generate_direct_response(self, message: str, msg_lower: str) -> str:
        """Generate direct response for greetings and simple queries."""
        if any(k in msg_lower for k in ["hi", "hello", "hey"]):
            return "Hello. I can help with your revenue, invoices, clients, and a quick view of how the business is doing."
        if any(k in msg_lower for k in ["thanks", "thank you"]):
            return "You're welcome! Let me know if you need anything else."
        if any(k in msg_lower for k in ["help", "what can you do"]):
            return "I can help with revenue, expenses, invoices, clients, transactions, and a quick business summary."
        return "Ask me about invoices, revenue, clients, market changes, compliance, or your business overview."

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
            r = None
            if user_id:
                r = await self.backend.get_my_organization(user_id)
            if not r or not r.success or not r.data:
                r = await self.backend.get_onboarding_status(user_id or org_id)
            if r.success and r.data:
                profile = self._extract_business_profile(
                    r.data if isinstance(r.data, dict) else {}
                )
                name = profile["name"] or "your business"
                industry = profile["industry"] or "general"
                sector = profile["sector"] or "B2B"
                services = profile["services"] or "business services"
                gstin = profile["gstin"] or "not registered"
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

    async def _call_groq_text(self, prompt: str, api_key: str, model: str) -> str:
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
                    "max_tokens": 500,
                    "temperature": 0.2,
                },
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            return (data["choices"][0]["message"].get("content") or "").strip()

        return await asyncio.to_thread(_sync_call)

    async def _synthesize_final_response(
        self,
        user_message: str,
        tool_name: Optional[str],
        tool_result: str,
        business_context: str,
        memory_context: str,
        history: list,
    ) -> str:
        history_lines = []
        for turn in history[-10:]:
            role = "User" if turn.get("role") == "user" else "Assistant"
            content = (turn.get("content") or "").strip()
            if content:
                history_lines.append(f"{role}: {content}")
        history_text = "\n".join(history_lines) if history_lines else "No prior conversation."

        prompt = f"""You are the AI financial intelligence layer for this business.
You have full access to all business data and can answer any business question.
You never refuse by saying you only handle certain topics.
If the user asks a follow-up fragment, resolve it from the recent conversation.
All amounts are Indian Rupees. Never say dollars.
Express large numbers in Indian business speech when natural.
Never use markdown, bullets, code, tool names, or internal identifiers.
Keep the reply under 3 sentences for voice. Be direct. Use real numbers.

{business_context}
{memory_context}

Recent conversation:
{history_text}

Current user message:
{user_message}

Resolved tool:
{tool_name or "none"}

Fetched data or drafted answer:
{tool_result}

Write the final answer for the user now."""

        for key, model in (
            (GROQ_KEY_PRIMARY, GROQ_MODEL),
            (GROQ_KEY_FAST, GROQ_MODEL_FAST),
        ):
            if not key:
                continue
            try:
                response = await self._call_groq_text(prompt, key, model)
                if response:
                    return response
            except Exception as e:
                logger.warning({"event": "groq_text_retry", "tool": tool_name, "error": str(e)})

        return tool_result

    async def _tool_get_financial_metrics(self, ctx: dict) -> str:
        r = await self.backend.get_finance_metrics(
            ctx.get("business_id", "default"), ctx["org_id"], ctx.get("user_id")
        )
        if not r.success or not r.data:
            return f"Could not fetch metrics: {r.error or 'unknown error'}"
        d = r.data
        revenue = d.get("revenue", 0)
        expenses = d.get("expenses", 0)
        profit = d.get("netProfit", 0)
        overdue_count = d.get("overdueCount", 0)
        overdue_amount = d.get("overdueAmount", 0)
        return (
            f"Right now, your revenue is INR {revenue:,.2f}, your expenses are INR {expenses:,.2f}, "
            f"and your net profit is INR {profit:,.2f}. "
            f"You also have {overdue_count} overdue invoices worth INR {overdue_amount:,.2f}."
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
        session = session_manager.get_session(
            ctx.get("session_id", "default"),
            ctx.get("user_id") or "unknown",
            ctx["org_id"],
        )
        session.last_invoice_results = invs[:20]
        session_manager.save_session(session)

        def compute_days_overdue(inv: dict) -> int:
            explicit = inv.get("daysOverdue")
            if isinstance(explicit, int) and explicit > 0:
                return explicit
            due = str(inv.get("dueDate") or "")[:10]
            if not due:
                return 0
            try:
                from datetime import date

                due_date = date.fromisoformat(due)
                return max(0, (date.today() - due_date).days)
            except Exception:
                return 0

        enriched = []
        for inv in invs:
            total_amount = float(inv.get("totalAmount") or 0)
            paid_amount = float(inv.get("paidAmount") or 0)
            outstanding = max(0.0, total_amount - paid_amount)
            enriched.append(
                {
                    **inv,
                    "outstandingAmount": outstanding,
                    "computedDaysOverdue": compute_days_overdue(inv),
                }
            )

        total = sum(i["outstandingAmount"] for i in enriched)
        top = enriched[:3]
        details = []
        for inv in top:
            due = str(inv.get("dueDate") or "")[:10]
            due_text = due or "the due date on file"
            details.append(
                f"{inv.get('clientName', 'Unknown client')} on invoice {inv.get('invoiceNumber', '?')} for INR {inv['outstandingAmount']:,.2f}, due {due_text}, now {inv['computedDaysOverdue']} days overdue"
            )

        if len(enriched) == 1:
            return f"You have 1 overdue invoice worth INR {total:,.2f}. It belongs to {details[0]}."

        summary = f"You have {len(enriched)} overdue invoices worth INR {total:,.2f} in total."
        if details:
            return summary + " The overdue clients are " + "; ".join(details) + "."
        return summary

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
        session = session_manager.get_session(
            ctx.get("session_id", "default"),
            ctx.get("user_id") or "unknown",
            ctx["org_id"],
        )
        session.last_invoice_results = invs[:20]
        session_manager.save_session(session)
        by_status: dict[str, int] = {}
        for inv in invs:
            s = inv.get("status", "UNKNOWN")
            by_status[s] = by_status.get(s, 0) + 1
        requested_status = ctx.get("status")
        metric = ctx.get("metric")

        if metric == "revenue":
            total_amount = sum(float(inv.get("totalAmount") or 0) for inv in invs)
            if requested_status == "PAID":
                return f"Your paid invoices add up to INR {total_amount:,.2f} across {len(invs)} invoices."
            return f"Those invoices add up to INR {total_amount:,.2f} across {len(invs)} invoices."

        if requested_status:
            status_label = requested_status.lower()
            total_amount = sum(float(inv.get("totalAmount") or 0) for inv in invs)
            client_names = [
                inv.get("clientName", "Unknown client")
                for inv in invs[:5]
                if inv.get("clientName")
            ]
            if metric == "count" or "how many" in str(ctx.get("raw_text", "")).lower():
                response = f"You have {len(invs)} {status_label} invoice"
                response += "s" if len(invs) != 1 else ""
                response += "."
                if client_names:
                    response += " They are for " + ", ".join(client_names) + "."
                return response
            return f"You have {len(invs)} {status_label} invoices worth INR {total_amount:,.2f}."

        summary_bits = [f"{k.lower()} {v}" for k, v in sorted(by_status.items())]
        return f"You have {len(invs)} invoices in total: " + ", ".join(summary_bits) + "."

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
            agenda.append("Everything looks good and there is nothing urgent right now")

        return (
            f"So far, your revenue is INR {revenue:,.2f}, your expenses are INR {expenses:,.2f}, "
            f"and your net profit is INR {profit:,.2f}. "
            f"You have {overdue_count} overdue invoices worth INR {overdue_total:,.2f}. "
            f"The main takeaway is: {agenda[0]}."
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
        invoice_id = ctx.get("invoice_id")
        if not invoice_id:
            r_list = await self.backend._request(
                "GET",
                "/api/invoices",
                params={"limit": 100},
                org_id=ctx["org_id"],
                user_id=ctx.get("user_id"),
            )
            if not r_list.success:
                return f"Failed to find an invoice to send: {r_list.error}"

            invoices = r_list.data if isinstance(r_list.data, list) else []
            client_name = (ctx.get("client_name") or "").strip().lower()
            if client_name:
                invoices = [
                    inv
                    for inv in invoices
                    if client_name in str(inv.get("clientName") or "").lower()
                ]

            if ctx.get("status"):
                invoices = [
                    inv
                    for inv in invoices
                    if str(inv.get("status") or "").upper() == str(ctx["status"]).upper()
                ]

            if not invoices:
                return "I could not find a matching invoice to send."
            if len(invoices) > 1 and not client_name:
                client_names = [
                    inv.get("clientName", "Unknown client")
                    for inv in invoices[:5]
                ]
                return (
                    "I found multiple matching invoices. Tell me the client name and I will send the right one. "
                    f"The matching clients are {', '.join(client_names)}."
                )

            invoices.sort(
                key=lambda inv: (
                    str(inv.get("status") or "") not in {"OVERDUE", "SENT"},
                    str(inv.get("dueDate") or ""),
                )
            )
            invoice_id = invoices[0].get("id")
            if not invoice_id:
                return "I found a matching invoice, but it does not have a valid id yet."
        r = await self.backend._request(
            "PATCH",
            f"/api/invoices/{invoice_id}/send",
            org_id=ctx["org_id"],
            user_id=ctx.get("user_id"),
        )
        if not r.success:
            return f"Failed to send invoice: {r.error}"
        inv = r.data.get("data") if isinstance(r.data, dict) else r.data
        return f"Invoice {inv.get('invoiceNumber', invoice_id)} has been sent to {inv.get('clientEmail', 'the client')}."

    async def _tool_send_invoice_followup(self, ctx: dict) -> str:
        invoice_id = ctx.get("invoice_id")
        client_name = (ctx.get("client_name") or "").strip().lower()

        if not invoice_id:
            invoices_resp = await self.backend.get_invoices(
                ctx["org_id"],
                status="OVERDUE",
                user_id=ctx.get("user_id"),
            )
            invoices = invoices_resp.data if invoices_resp.success and isinstance(invoices_resp.data, list) else []
            if client_name:
                invoices = [
                    inv for inv in invoices
                    if client_name in str(inv.get("clientName") or "").lower()
                ]
            if not invoices:
                return "I could not find an overdue invoice to send a reminder for."
            target = invoices[0]
            invoice_id = target.get("id")
        else:
            target_resp = await self.backend._request(
                "GET",
                f"/api/invoices/{invoice_id}",
                org_id=ctx["org_id"],
                user_id=ctx.get("user_id"),
            )
            target = target_resp.data if target_resp.success and isinstance(target_resp.data, dict) else {}

        if not invoice_id:
            return "I could not resolve the invoice for that reminder."

        result = await self.backend.send_collection_email(
            invoice_id=invoice_id,
            client_email=str(target.get("clientEmail") or ""),
            client_name=str(target.get("clientName") or "the client"),
            invoice_number=str(target.get("invoiceNumber") or invoice_id),
            amount=float(target.get("totalAmount") or 0),
            due_date=str(target.get("dueDate") or ""),
            org_id=ctx["org_id"],
            user_id=ctx.get("user_id"),
        )
        if not result.get("sent"):
            return f"Failed to send follow-up: {result.get('error') or 'unknown error'}"
        return f"Reminder sent to {target.get('clientEmail', 'the client email')} for invoice {target.get('invoiceNumber', invoice_id)}."

    async def _tool_record_payment(self, ctx: dict) -> str:
        invoice_id = ctx.get("invoice_id")
        client_name = (ctx.get("client_name") or "").strip().lower()

        if not invoice_id:
            invoices_resp = await self.backend.get_invoices(
                ctx["org_id"],
                limit=100,
                user_id=ctx.get("user_id"),
            )
            invoices = invoices_resp.data if invoices_resp.success and isinstance(invoices_resp.data, list) else []
            invoices = [
                inv for inv in invoices
                if str(inv.get("status") or "").upper() in {"OVERDUE", "SENT", "PARTIALLY_PAID"}
            ]
            if client_name:
                invoices = [
                    inv for inv in invoices
                    if client_name in str(inv.get("clientName") or "").lower()
                ]
            if not invoices:
                return "I could not find an unpaid invoice to record that payment against."
            target = invoices[0]
            invoice_id = target.get("id")
        else:
            detail_resp = await self.backend._request(
                "GET",
                f"/api/invoices/{invoice_id}",
                org_id=ctx["org_id"],
                user_id=ctx.get("user_id"),
            )
            target = detail_resp.data if detail_resp.success and isinstance(detail_resp.data, dict) else {}

        total_amount = float(target.get("totalAmount") or 0)
        paid_amount = float(target.get("paidAmount") or 0)
        outstanding = max(0.0, total_amount - paid_amount)
        amount = float(ctx.get("amount") or outstanding)
        if amount <= 0:
            return "I could not determine the payment amount for that invoice."

        payment_payload = {
            "amount": amount,
            "type": "INCOME",
            "description": f"Payment for {target.get('invoiceNumber', invoice_id)}",
            "paymentMethod": "BANK_TRANSFER",
        }
        result = await self.backend._request(
            "POST",
            f"/api/invoices/{invoice_id}/payment",
            data=payment_payload,
            org_id=ctx["org_id"],
            user_id=ctx.get("user_id"),
        )
        if not result.success:
            return f"Failed to record payment: {result.error}"
        return f"Payment of INR {amount:,.2f} recorded for invoice {target.get('invoiceNumber', invoice_id)} for {target.get('clientName', 'the client')}."

    async def _tool_get_clients(self, ctx: dict) -> str:
        clients = await self.backend.get_clients(
            ctx["org_id"], user_id=ctx.get("user_id")
        )
        if not clients:
            return "No clients found."
        names = [
            c.get("display_name") or c.get("displayName") or c.get("name") or "Unknown client"
            for c in clients[:5]
        ]
        sample = ", ".join(names)
        if len(clients) > 5:
            return f"You currently have {len(clients)} clients. A few of them are {sample}."
        return f"You currently have {len(clients)} clients: {sample}."

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
            session = session_manager.get_session(
                ctx.get("session_id", "default"),
                ctx.get("user_id") or "unknown",
                ctx.get("org_id", "unknown"),
            )
            raw_text = (ctx.get("raw_text") or "").lower()
            last_profile = (
                session.last_business_profile
                if isinstance(session.last_business_profile, dict)
                else {}
            )

            if last_profile and any(
                phrase in raw_text
                for phrase in ["what sector", "which sector", "what industry", "which industry"]
            ):
                sector = last_profile.get("sector") or last_profile.get("industry")
                business_name = last_profile.get("name") or "your business"
                if sector:
                    return f"{business_name} sits in {sector}."

            r = None
            if ctx.get("user_id"):
                r = await self.backend.get_my_organization(ctx["user_id"])
            if not r or not r.success or not r.data:
                r = await self.backend.get_onboarding_status(
                    ctx.get("user_id") or ctx["org_id"]
                )
            if r.success and r.data:
                profile = self._extract_business_profile(
                    r.data if isinstance(r.data, dict) else {}
                )
                session.last_business_profile = profile
                session_manager.save_session(session)
                business_name = profile["name"] or "your business"
                details = []
                if profile["industry"]:
                    details.append(f"you're in {profile['industry']}")
                if profile["sector"]:
                    details.append(f"you mainly serve {profile['sector']}")
                if profile["services"]:
                    details.append(f"your main offering is {profile['services']}")

                if details:
                    if len(details) == 1:
                        detail_text = details[0]
                    elif len(details) == 2:
                        detail_text = f"{details[0]}, and {details[1]}"
                    else:
                        detail_text = f"{details[0]}, {details[1]}, and {details[2]}"
                    return (
                        f"From what I can see, your business is {business_name}, and {detail_text}."
                    )

                return (
                    f"I can see your account is linked to {business_name}, "
                    "but the detailed business profile is still missing. "
                    "Add your industry, target market, and primary activity in Settings to get a richer business summary."
                )
        except Exception as e:
            logger.warning({"event": "business_context_error", "error": str(e)})
        return "Could not load business context."

    async def _tool_search_market(self, ctx: dict) -> str:
        try:
            session = session_manager.get_session(
                ctx.get("session_id", "default"),
                ctx.get("user_id") or "unknown",
                ctx.get("org_id", "unknown"),
            )
            raw_text = (ctx.get("raw_text") or "").lower()
            followup = bool(ctx.get("followup"))

            if followup and session.last_market_results:
                business_profile = (
                    session.last_business_profile
                    if isinstance(session.last_business_profile, dict)
                    else {}
                )
                business_name = business_profile.get("name") or "your business"
                services = business_profile.get("services") or "your offering"
                market = business_profile.get("sector") or business_profile.get("industry") or "your market"
                first = session.last_market_results[0]
                second = session.last_market_results[1] if len(session.last_market_results) > 1 else None
                if second:
                    return (
                        f"For {business_name}, this matters because changes in {market} can affect demand, pricing, and buyer urgency for {services}. "
                        f"In practical terms, signals like {first} and {second} can change how quickly customers approve projects, what budgets they release, and which opportunities move first."
                    )
                return (
                    f"For {business_name}, this matters because shifts in {market} can directly affect demand and client priorities for {services}. "
                    f"The main thing to watch is {first}, because it can change customer timing, budgets, or implementation plans."
                )

            from app.tools.multi_source_search import MultiSourceSearch

            searcher = MultiSourceSearch()
            query = ctx.get("query", "")
            if ctx.get("user_id"):
                org_resp = await self.backend.get_my_organization(ctx["user_id"])
                if org_resp.success and isinstance(org_resp.data, dict):
                    profile = self._extract_business_profile(org_resp.data)
                    session.last_business_profile = profile
                    session_manager.save_session(session)
                    business_hint = " ".join(
                        value for value in [profile.get("industry"), profile.get("services"), profile.get("sector")] if value
                    )
                    if business_hint and "my business" in query.lower():
                        query = f"{query} {business_hint}"

            results = await searcher.search(query, max_results=5)
            if results and isinstance(results, dict):
                articles = results.get("results", [])[:3]
                if articles:
                    insights = []
                    for article in articles:
                        snippet = (article.get("snippet") or article.get("title") or "").strip()
                        if not snippet:
                            continue
                        cleaned = re.sub(r"\s+", " ", snippet)
                        cleaned = cleaned.replace("...", "")
                        insights.append(cleaned[:180].rstrip(" .,"))
                    if not insights:
                        insights = [a.get("title", "Untitled") for a in articles[:3]]
                    session.last_market_query = query
                    session.last_market_results = insights
                    session_manager.save_session(session)
                    business_name = (
                        session.last_business_profile.get("name")
                        if isinstance(session.last_business_profile, dict)
                        else "your business"
                    ) or "your business"
                    if len(insights) == 1:
                        return f"One market signal that stands out for {business_name} is this: {insights[0]}."
                    if len(insights) == 2:
                        return f"Two market signals stand out for {business_name}. First, {insights[0]}. Second, {insights[1]}."
                    return f"Three market signals stand out for {business_name}. First, {insights[0]}. Second, {insights[1]}. Third, {insights[2]}."
        except Exception as e:
            logger.warning({"event": "market_search_failed", "error": str(e)})
        return "Could not fetch market information."

    async def _tool_check_compliance(self, ctx: dict) -> str:
        check_type = ctx.get("check_type", "deadlines")
        if check_type == "deadlines":
            return (
                "The main compliance dates to stay on top of are these. "
                "GSTR-1 is due on the 10th of next month. "
                "GSTR-3B is due on the 20th of next month. "
                "TDS deposit is due on the 7th of next month. "
                "Income tax filing is due by July 31st for individuals and October 31st for businesses."
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
