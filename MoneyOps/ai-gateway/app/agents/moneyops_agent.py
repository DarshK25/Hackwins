"""
MoneyOps Voice Processor — Complete Replacement
================================================
Drops the old classify → extract → route → handle pipeline entirely.
Wires directly to the new function-calling agent (moneyops_agent_v2_final.py).

Fixes all bugs observed in session logs:
- "2 thousand" spoken for years (2025, 2026) → fixed in sanitizer
- "INR 3.4 lakh.00" → fixed formatting
- "[2 thousand, 2, 25]" for dates → fixed date formatting
- "Sorry, that came through in a messy way" for fragment utterances → removed
- "I didn't quite get that" fallback responses → removed, context used instead
- "send invoice to client" not working → agent handles with context
- Compliance response was a bullet list → sanitizer strips bullets
- Market response was raw article titles → agent now speaks with context

Python 3.10 compatible.
"""

import json
import asyncio
import logging
import re
import os
import time
import httpx
import difflib
from datetime import datetime, date, timedelta
from dataclasses import dataclass, field
from typing import Optional, Any, Dict, List, Tuple
from groq import AsyncGroq
from app.utils.voice_text import sanitize_for_tts, format_inr_words as _inr_words
from app.config import settings

logger = logging.getLogger(__name__)

READ_TOOL_CACHE_TTL_SECONDS = 60
TDS_DEDUCTOR_HINTS = (
    "infosys", "tcs", "wipro", "hcl", "tech mahindra", "accenture",
    "cognizant", "lemon tree", "marriott", "hyatt", "bluedart",
    "blue dart", "dhl", "amazon", "flipkart",
)
_READ_TOOL_CACHE = {}
_GROQ_KEY_BACKOFF_UNTIL: Dict[str, float] = {}


def _sanitize_message_history(history: list) -> list:
    sanitized = []
    for msg in history or []:
        if not isinstance(msg, dict):
            continue
        role = msg.get("role")
        content = msg.get("content")
        if role in {"system", "user", "assistant", "tool"} and content is not None:
            clean = {"role": role, "content": content}
            if role == "tool" and msg.get("tool_call_id"):
                clean["tool_call_id"] = msg.get("tool_call_id")
            sanitized.append(clean)
    return sanitized


def _cache_key(org_id: str, business_id: str, tool_name: str, args: dict) -> str:
    return json.dumps(
        {
            "org_id": org_id,
            "business_id": business_id,
            "tool": tool_name,
            "args": args,
        },
        sort_keys=True,
        default=str,
    )


def _get_cached_read_tool(org_id: str, business_id: str, tool_name: str, args: dict) -> Optional[dict]:
    key = _cache_key(org_id, business_id, tool_name, args)
    entry = _READ_TOOL_CACHE.get(key)
    if not entry:
        return None
    if time.time() - entry["ts"] > READ_TOOL_CACHE_TTL_SECONDS:
        _READ_TOOL_CACHE.pop(key, None)
        return None
    return entry["value"]


def _set_cached_read_tool(org_id: str, business_id: str, tool_name: str, args: dict, value: dict) -> None:
    _READ_TOOL_CACHE[_cache_key(org_id, business_id, tool_name, args)] = {
        "ts": time.time(),
        "value": value,
    }
    if len(_READ_TOOL_CACHE) > 256:
        oldest_key = next(iter(_READ_TOOL_CACHE))
        _READ_TOOL_CACHE.pop(oldest_key, None)


def _clear_org_cache(org_id: str) -> None:
    stale_keys = [key for key in _READ_TOOL_CACHE if f'"org_id": "{org_id}"' in key]
    for key in stale_keys:
        _READ_TOOL_CACHE.pop(key, None)


# ════════════════════════════════════════════════════════════════════════════════
# SESSION STATE
# ════════════════════════════════════════════════════════════════════════════════

@dataclass
class AgentSession:
    session_id: str
    user_id: str
    org_uuid: str
    business_id: str = "1"
    clerk_org_id: Optional[str] = None
    history: list = field(default_factory=list)
    pending_invoice: Optional[dict] = None
    pending_client: Optional[dict] = None
    pending_expense: Optional[dict] = None
    pending_payment: Optional[dict] = None
    verified_team_code: Optional[str] = None
    team_code_attempts: int = 0
    business_snapshot: Optional[dict] = None
    client_cache: Optional[list] = None
    last_tool_called: Optional[str] = None
    last_client_mentioned: Optional[str] = None
    last_invoice_mentioned: Optional[str] = None
    last_response_context: Optional[str] = None
    briefing_given_today: bool = False
    last_invoice_results: Optional[list] = None
    last_client_results: Optional[list] = None
    last_market_query: Optional[str] = None
    last_market_results: Optional[list] = None


# ════════════════════════════════════════════════════════════════════════════════
# TOOL DEFINITIONS
# ════════════════════════════════════════════════════════════════════════════════

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_financial_summary",
            "description": "Get real-time P&L: revenue, expenses, net profit, margin, outstanding. Call for ANY financial question.",
            "parameters": {"type": "object", "properties": {
                "period": {"type": "string", "enum": ["current_month", "last_month", "quarter", "year"]}
            }, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_invoices",
            "description": "Get invoices with optional status or client filter. Call for ANY invoice question — overdue, paid, pending, specific client.",
            "parameters": {"type": "object", "properties": {
                "status": {"type": "string", "enum": ["all", "PAID", "OVERDUE", "SENT", "DRAFT", "PARTIALLY_PAID", "CANCELLED"]},
                "client_name": {"type": "string"}
            }, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_clients",
            "description": "Get all clients ranked by revenue. Call for ANY client question.",
            "parameters": {"type": "object", "properties": {
                "sort_by": {"type": "string", "enum": ["revenue", "outstanding", "overdue", "newest"]}
            }, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_invoice",
            "description": "Create GST-compliant invoice. Need: client_name, line_items (description + unit_price), due_date, team_code. Collect missing fields one at a time.",
            "parameters": {"type": "object", "properties": {
                "client_name": {"type": "string"},
                "due_date": {"type": "string", "description": "YYYY-MM-DD or 'net30'"},
                "line_items": {"type": "array", "items": {"type": "object", "properties": {
                    "description": {"type": "string"},
                    "quantity": {"type": "number"},
                    "unit_price": {"type": "number"},
                    "gst_percent": {"type": "number"}
                }, "required": ["description", "unit_price"]}},
                "notes": {"type": "string"},
                "team_code": {"type": "string"}
            }, "required": ["client_name", "due_date", "line_items", "team_code"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_client",
            "description": "Add a new client. Need: name, email, phone, team_code. Never use placeholder names.",
            "parameters": {"type": "object", "properties": {
                "name": {"type": "string"},
                "email": {"type": "string"},
                "phone": {"type": "string"},
                "company_name": {"type": "string"},
                "gstin": {"type": "string"},
                "city": {"type": "string"},
                "credit_limit_days": {"type": "integer"},
                "is_tds_deductor": {"type": "boolean"},
                "team_code": {"type": "string"}
            }, "required": ["name", "email", "phone", "team_code"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "record_payment",
            "description": "Record a payment received. Auto-finds the invoice by client name if invoice_number not given. Detects TDS gaps.",
            "parameters": {"type": "object", "properties": {
                "client_name": {"type": "string"},
                "invoice_number": {"type": "string"},
                "amount_received": {"type": "number"},
                "payment_date": {"type": "string"},
                "payment_method": {"type": "string", "enum": ["NEFT", "RTGS", "IMPS", "UPI", "CHEQUE", "CASH", "DD"]},
                "utr_or_reference": {"type": "string"},
                "team_code": {"type": "string"}
            }, "required": ["client_name", "amount_received", "team_code"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "record_expense",
            "description": "Record a business expense with category and ITC flag.",
            "parameters": {"type": "object", "properties": {
                "description": {"type": "string"},
                "amount": {"type": "number"},
                "category": {"type": "string", "enum": ["HARDWARE", "SOFTWARE", "SALARIES", "FUEL", "RENT", "UTILITIES", "TRAVEL", "MARKETING", "PROFESSIONAL_FEES", "REPAIRS", "INSURANCE", "OTHER"]},
                "expense_date": {"type": "string"},
                "vendor_name": {"type": "string"},
                "vendor_gstin": {"type": "string"},
                "gst_percent": {"type": "number"},
                "team_code": {"type": "string"}
            }, "required": ["description", "amount", "category", "team_code"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_invoice_email",
            "description": "Email an invoice PDF to a client. Finds the invoice first, then sends. Use when user says 'send invoice to client', 'email the invoice', 'share invoice'.",
            "parameters": {"type": "object", "properties": {
                "client_name": {"type": "string", "description": "Client to send to"},
                "invoice_number": {"type": "string", "description": "Specific invoice, or omit to send the most recent overdue one"},
                "message": {"type": "string", "description": "Optional personal message to include"},
                "team_code": {"type": "string"}
            }, "required": ["client_name", "team_code"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_compliance",
            "description": "Get compliance deadlines, GST liability, and TDS status. Call for ANY compliance or tax question.",
            "parameters": {"type": "object", "properties": {
                "focus": {"type": "string", "enum": ["all", "gst", "tds", "income_tax"]}
            }, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_business_health_score",
            "description": "Comprehensive business health: 5-dimension score, key metrics, top recommendations. Call for overall business assessment.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_market_intelligence",
            "description": "Real-time market intelligence: industry trends, opportunities, regulatory changes, competitor activity. Always searches with full business context.",
            "parameters": {"type": "object", "properties": {
                "query": {"type": "string"},
                "focus": {"type": "string", "enum": ["opportunities", "competitors", "regulations", "trends", "funding", "risks"]}
            }, "required": ["query"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_cash_flow_forecast",
            "description": "30/60/90-day cash flow forecast with probability-weighted inflows and expense projection.",
            "parameters": {"type": "object", "properties": {
                "days_ahead": {"type": "integer", "enum": [30, 60, 90]}
            }, "required": ["days_ahead"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_collection_reminder",
            "description": "Send a payment reminder email to a client for overdue invoice. Three tones: gentle, firm, final.",
            "parameters": {"type": "object", "properties": {
                "client_name": {"type": "string"},
                "invoice_number": {"type": "string"},
                "tone": {"type": "string", "enum": ["gentle", "firm", "final"]},
                "team_code": {"type": "string"}
            }, "required": ["client_name", "tone", "team_code"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_overdue_action_plan",
            "description": "Prioritized collection action plan: which invoices to chase, in what order, with what action. Use when asked about collections or overdue follow-up.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_daily_briefing",
            "description": "Morning business briefing: revenue MTD, overdue count, compliance alerts, today's priorities.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
]


# ════════════════════════════════════════════════════════════════════════════════
# SYSTEM PROMPT
# ════════════════════════════════════════════════════════════════════════════════

def build_system_prompt(org_context: dict, session: AgentSession) -> str:
    today = datetime.now()
    today_str = today.strftime("%A, %B %d, %Y")
    business = org_context.get("business", {})
    name = business.get("legalName", "your company")
    industry = business.get("industry", "B2B services")
    gstin = business.get("gstin", "")
    city = business.get("city", "India")
    activity = business.get("primaryActivity", "B2B services")

    snap = session.business_snapshot or {}
    snapshot_text = ""
    if snap:
        snapshot_text = f"""
LIVE SNAPSHOT: Revenue {_inr_words(snap.get('revenue', 0))} rupees, expenses {_inr_words(snap.get('expenses', 0))} rupees, net profit {_inr_words(snap.get('netProfit', 0))} rupees. Outstanding: {_inr_words(snap.get('outstanding', 0))} rupees. Clients: {snap.get('clientCount', 0)}.
"""

    draft_text = ""
    if session.pending_invoice:
        draft_text += f"\nACTIVE INVOICE DRAFT: {json.dumps(session.pending_invoice)}"
    if session.pending_client:
        draft_text += f"\nACTIVE CLIENT ONBOARDING: {json.dumps(session.pending_client)}"

    context_text = ""
    if session.last_client_mentioned:
        context_text += f"\nLast client discussed: {session.last_client_mentioned}"
    if session.last_invoice_mentioned:
        context_text += f"\nLast invoice discussed: {session.last_invoice_mentioned}"
    if session.verified_team_code:
        context_text += f"\nTeam code already verified this session: YES — do NOT ask again"

    return f"""You are the embedded financial operating system for {name}.

TODAY: {today_str}
BUSINESS: {name} | {industry} | GSTIN: {gstin} | {city}
ACTIVITY: {activity}
{snapshot_text}{draft_text}{context_text}

Speak like a sharp CFO and operations lead who knows this business personally.
Use direct, natural voice responses with real numbers and no markdown, URLs, source names, tool names, or symbols-heavy formatting.
Use Indian number speech for currency and natural spoken dates.
Keep simple answers to 2 to 4 sentences and analytical answers to 5 to 7 sentences.
Never say you are an AI, never say you cannot access something, and never give customer-support style apologies.

Use tools instead of guessing.
Financial question means get_financial_summary.
Invoice question means get_invoices.
Client question means get_clients.
Business health means get_business_health_score.
Compliance or tax means check_compliance.
Collections means get_overdue_action_plan.
Cash flow means get_cash_flow_forecast.
Market or growth means search_market_intelligence using the real business context.

Treat fragments and follow-ups as continuations of the current conversation.
Reuse recent tool results from conversation history instead of repeating the same tool call when the answer is already available.
If the user asks to send an invoice or reminder, do the action and confirm what was sent.

For create_invoice, create_client, record_expense, and record_payment, ask for one missing field at a time.
If team code is already verified in this session, reuse it and do not ask again.
If a remaining amount is exactly a ten percent TDS pattern, treat it as Form 26AS credit and not a shortfall."""


def _resolved_groq_keys(primary_key: str) -> List[str]:
    keys = [
        primary_key,
        settings.GROQ_API_KEY_FAST,
        settings.GROQ_API_KEY_FALLBACK_1,
        settings.GROQ_API_KEY_FALLBACK_2,
    ]
    ordered: List[str] = []
    for key in keys:
        if key and key not in ordered:
            ordered.append(key)
    return ordered


def _mark_groq_key_backoff(api_key: str, error: Exception) -> None:
    now = time.monotonic()
    text = str(error).lower()
    seconds = 6.0
    if "429" in text or "rate limit" in text or "too many requests" in text:
        seconds = 20.0
    elif "timeout" in text:
        seconds = 5.0
    elif "500" in text or "502" in text or "503" in text or "504" in text:
        seconds = 8.0
    _GROQ_KEY_BACKOFF_UNTIL[api_key] = now + seconds


def _ordered_groq_keys(keys: List[str]) -> List[str]:
    now = time.monotonic()
    return sorted(keys, key=lambda key: _GROQ_KEY_BACKOFF_UNTIL.get(key, 0.0) > now)


def _compact_tool_result(tool_name: str, result: Any) -> Any:
    if not isinstance(result, dict):
        return result

    compact: Dict[str, Any] = {}
    for key in ("status", "message", "note", "speech", "_voice_hint"):
        if key in result:
            compact[key] = result[key]

    if tool_name == "get_invoices":
        compact.update({
            "total_count": result.get("total_count", 0),
            "paid_count": result.get("paid_count", 0),
            "overdue_count": result.get("overdue_count", 0),
            "total_outstanding_inr": result.get("total_outstanding_inr", 0),
            "invoices": [
                {
                    "invoice_number": invoice.get("invoice_number"),
                    "client": invoice.get("client"),
                    "status": invoice.get("status"),
                    "amount_inr": invoice.get("amount_inr"),
                    "paid_inr": invoice.get("paid_inr"),
                    "outstanding_inr": invoice.get("outstanding_inr"),
                    "days_overdue": invoice.get("days_overdue"),
                }
                for invoice in result.get("invoices", [])[:5]
                if isinstance(invoice, dict)
            ],
        })
        return compact

    if tool_name == "get_clients":
        compact.update({
            "total_clients": result.get("total_clients", 0),
            "total_revenue_inr": result.get("total_revenue_inr", 0),
            "clients": [
                {
                    "name": client.get("name"),
                    "company": client.get("company"),
                    "total_revenue_inr": client.get("total_revenue_inr"),
                    "outstanding_inr": client.get("outstanding_inr"),
                    "payment_health": client.get("payment_health"),
                }
                for client in result.get("clients", [])[:5]
                if isinstance(client, dict)
            ],
        })
        return compact

    if tool_name == "get_financial_summary":
        compact.update({
            "revenue_inr": result.get("revenue_inr", 0),
            "expenses_inr": result.get("expenses_inr", 0),
            "net_profit_inr": result.get("net_profit_inr", 0),
            "margin_percent": result.get("margin_percent", 0),
            "outstanding_inr": result.get("outstanding_inr", 0),
            "overdue_amount_inr": result.get("overdue_amount_inr", 0),
            "overdue_count": result.get("overdue_count", 0),
        })
        return compact

    if tool_name == "get_business_health_score":
        for key in ("overall_score", "collection_score", "profitability_score", "cash_flow_score", "speech"):
            if key in result:
                compact[key] = result[key]
        return compact

    for key, value in result.items():
        if isinstance(value, (str, int, float, bool)) or value is None:
            compact[key] = value
    return compact


def _fallback_from_tool_results(tool_results: List[Tuple[str, Any]]) -> Optional[str]:
    if not tool_results:
        return None

    first_tool, first_result = tool_results[-1]
    if isinstance(first_result, dict):
        if first_result.get("speech"):
            return str(first_result["speech"])
        if first_result.get("_voice_hint"):
            return str(first_result["_voice_hint"])
        if first_tool == "search_market_intelligence":
            synthesized_market = _synthesize_market_result(first_result)
            if synthesized_market:
                return synthesized_market

    if first_tool == "get_invoices" and isinstance(first_result, dict):
        total_count = int(first_result.get("total_count", 0) or 0)
        paid_count = int(first_result.get("paid_count", 0) or 0)
        overdue_count = int(first_result.get("overdue_count", 0) or 0)
        total_outstanding = float(first_result.get("total_outstanding_inr", 0) or 0)
        paid_total = sum(float(inv.get("paid_inr", 0) or 0) for inv in first_result.get("paid_invoices", []) if isinstance(inv, dict))
        if paid_total > 0:
            return (
                f"You have {total_count} invoices. "
                f"{paid_count} are paid, with total paid value of {_inr_words(paid_total)} rupees. "
                f"{overdue_count} are overdue, and total outstanding is {_inr_words(total_outstanding)} rupees."
            )
        return (
            f"You have {total_count} invoices. "
            f"{paid_count} are paid and {overdue_count} are overdue. "
            f"Total outstanding is {_inr_words(total_outstanding)} rupees."
        )

    if first_tool == "get_clients" and isinstance(first_result, dict):
        clients = [c for c in first_result.get("clients", []) if isinstance(c, dict)]
        if clients:
            top = clients[0]
            return (
                f"Your highest value client is {top.get('name')} from {top.get('company')}. "
                f"Total revenue from this client is {_inr_words(float(top.get('total_revenue_inr', 0) or 0))} rupees."
            )

    if first_tool == "get_financial_summary" and isinstance(first_result, dict):
        return (
            f"Current revenue is {_inr_words(float(first_result.get('revenue_inr', 0) or 0))} rupees. "
            f"Net profit is {_inr_words(float(first_result.get('net_profit_inr', 0) or 0))} rupees, "
            f"and outstanding receivables are {_inr_words(float(first_result.get('outstanding_inr', 0) or 0))} rupees."
        )

    return None


def _prefer_direct_tool_answer(tool_results: List[Tuple[str, Any]]) -> Optional[str]:
    if not tool_results:
        return None

    if len(tool_results) != 1:
        return None

    tool_name, result = tool_results[0]
    if not isinstance(result, dict):
        return None

    direct_tool_names = {
        "get_financial_summary",
        "get_invoices",
        "get_clients",
        "check_compliance",
        "get_business_health_score",
        "get_cash_flow_forecast",
        "get_overdue_action_plan",
        "get_daily_briefing",
        "search_market_intelligence",
    }
    if tool_name not in direct_tool_names:
        return None

    if result.get("status") in {"error", "validation_error"}:
        return None

    if tool_name == "search_market_intelligence":
        market_answer = _synthesize_market_result(result)
        if market_answer:
            return market_answer

    return str(result.get("speech") or result.get("_voice_hint") or "").strip() or _fallback_from_tool_results(tool_results)


def _groq_rate_limit_message(error: Exception) -> Optional[str]:
    raw = str(error or "")
    lowered = raw.lower()
    if "429" not in lowered and "rate limit" not in lowered and "too many requests" not in lowered:
        return None

    wait_match = re.search(r"try again in\s+([0-9]+m[0-9.]+s|[0-9.]+\s*seconds?)", raw, flags=re.I)
    wait_hint = "a few minutes"
    if wait_match:
        token = wait_match.group(1).strip().lower()
        total_seconds: Optional[int] = None
        compact_match = re.fullmatch(r"(\d+)m([0-9.]+)s", token)
        seconds_match = re.fullmatch(r"([0-9.]+)\s*seconds?", token)
        if compact_match:
            minutes = int(compact_match.group(1))
            seconds = round(float(compact_match.group(2)))
            total_seconds = minutes * 60 + seconds
        elif seconds_match:
            total_seconds = round(float(seconds_match.group(1)))

        if total_seconds is not None:
            total_seconds = max(1, total_seconds)
            minutes, seconds = divmod(total_seconds, 60)
            if minutes >= 3:
                wait_hint = f"{minutes} minute{'s' if minutes != 1 else ''}"
            elif minutes >= 1:
                wait_hint = (
                    f"{minutes} minute{'s' if minutes != 1 else ''} {seconds} second{'s' if seconds != 1 else ''}"
                    if seconds
                    else f"{minutes} minute{'s' if minutes != 1 else ''}"
                )
            else:
                wait_hint = f"{seconds} second{'s' if seconds != 1 else ''}"

    return (
        f"The voice model is rate-limited right now. Please wait about {wait_hint} and try again, "
        "or use the on-screen invoice and client actions in the meantime."
    )


def _answer_from_session_context(text: str, session: AgentSession) -> Optional[str]:
    lowered = (text or "").lower()

    if any(phrase in lowered for phrase in (
        "create a client",
        "create client",
        "add a client",
        "add new client",
        "add a new client",
        "new client",
    )):
        return None

    if session.last_invoice_results and "invoice" in lowered:
        invoices = [inv for inv in session.last_invoice_results if isinstance(inv, dict)]
        if invoices:
            paid = [inv for inv in invoices if str(inv.get("status", "")).upper() == "PAID"]
            overdue = [
                inv for inv in invoices
                if (
                    str(inv.get("status", "")).upper() == "OVERDUE" or
                    (
                        float(inv.get("outstanding_inr", 0) or 0) > 0 and
                        str(inv.get("status", "")).upper() not in ("PAID", "CANCELLED") and
                        int(inv.get("days_overdue", 0) or 0) > 0 and
                        not bool(inv.get("is_tds_gap"))
                    )
                )
            ]
            total_paid = sum(float(inv.get("paid_inr", 0) or 0) for inv in paid)
            total_outstanding = sum(
                float(inv.get("outstanding_inr", 0) or 0)
                for inv in invoices
                if str(inv.get("status", "")).upper() not in ("PAID", "CANCELLED")
            )

            if "paid" in lowered and ("how many" in lowered or "total" in lowered or "amount" in lowered):
                return (
                    f"You have {len(paid)} paid invoices. "
                    f"The total paid amount is {_inr_words(total_paid)} rupees."
                )
            if "overdue" in lowered:
                return (
                    f"You have {len(overdue)} overdue invoices. "
                    f"They total {_inr_words(sum(float(inv.get('outstanding_inr', 0) or 0) for inv in overdue))} rupees."
                )
            if "outstanding" in lowered:
                return f"Your total outstanding invoice amount is {_inr_words(total_outstanding)} rupees."
            if "how many" in lowered:
                return (
                    f"You have {len(invoices)} invoices in total. "
                    f"{len(paid)} are paid and {len(overdue)} are overdue."
                )

    if session.last_client_results and any(token in lowered for token in ("client", "customer", "highest value", "top client")):
        clients = [client for client in session.last_client_results if isinstance(client, dict)]
        if clients:
            top = max(clients, key=lambda item: float(item.get("total_revenue_inr", 0) or 0))
            return (
                f"Your highest value client is {top.get('name')} from {top.get('company')}. "
                f"Total revenue from this client is {_inr_words(float(top.get('total_revenue_inr', 0) or 0))} rupees."
            )

    if session.last_invoice_results and any(token in lowered for token in ("highest unpaid", "largest unpaid", "highest outstanding", "most unpaid")):
        invoices = [inv for inv in session.last_invoice_results if isinstance(inv, dict)]
        if invoices:
            by_client: Dict[str, float] = {}
            for inv in invoices:
                client = str(inv.get("client") or "").strip()
                if not client:
                    continue
                by_client[client] = by_client.get(client, 0.0) + float(inv.get("outstanding_inr", 0) or 0)
            if by_client:
                client, amount = max(by_client.items(), key=lambda item: item[1])
                return f"{client} has the highest unpaid amount right now at {_inr_words(amount)} rupees."

    if session.business_snapshot and any(token in lowered for token in ("revenue", "profit", "outstanding", "cash flow")):
        snap = session.business_snapshot
        if "revenue" in lowered:
            return f"Current revenue is {_inr_words(float(snap.get('revenue', 0) or 0))} rupees."
        if "profit" in lowered:
            return f"Current net profit is {_inr_words(float(snap.get('netProfit', 0) or 0))} rupees."
        if "outstanding" in lowered:
            return f"Current outstanding receivables are {_inr_words(float(snap.get('outstanding', 0) or 0))} rupees."

    if _is_market_scale_followup_query(text, session) and session.last_market_results:
        return _market_scale_guidance(session, {})

    if _is_market_action_followup_query(text, session) and session.last_market_results:
        return _market_action_guidance(text, session, {})

    return None


def _is_market_growth_query(text: str) -> bool:
    lowered = (text or "").lower()
    return any(phrase in lowered for phrase in (
        "growth opportunities",
        "business growth",
        "growth ideas",
        "market opportunities",
        "growth opportunity",
        "growth opportunity right now",
        "business opportunities",
        "opportunities for this month",
        "market update",
        "market updates",
        "market trend",
        "market trends",
        "industry update",
        "industry updates",
        "what changed in the market",
        "latest market update",
        "latest industry update",
        "what is happening in the market",
    ))


def _is_market_scale_followup_query(text: str, session: AgentSession) -> bool:
    lowered = (text or "").lower()
    followup_signals = (
        "scale our business",
        "scale the business",
        "scale business",
        "scale up",
        "how do we scale",
        "how should we scale",
        "what do we do",
        "what should we do",
        "what next",
        "next step",
        "next steps",
        "how do we grow",
        "how should we grow",
        "expand the business",
        "grow faster",
    )
    if not any(signal in lowered for signal in followup_signals):
        return False
    return session.last_tool_called == "search_market_intelligence" or bool(session.last_market_results)


def _is_market_action_followup_query(text: str, session: AgentSession) -> bool:
    lowered = (text or "").lower()
    followup_signals = (
        "how do we act on this",
        "how should we act on this",
        "how do we grab this opportunity",
        "how do we capture this opportunity",
        "what should we do to win",
        "how do we get the best out of it",
        "how should we escalate",
        "how do we escalate",
        "how do we avoid financial loss",
        "how do we avoid losses",
        "what is the escalation plan",
        "what is the action plan",
        "how do we protect margin",
        "what should we do right now",
        "how do we respond",
        "how do we mitigate the risk",
    )
    if not any(signal in lowered for signal in followup_signals):
        return False
    return session.last_tool_called == "search_market_intelligence" or bool(session.last_market_results)


def _is_growth_strategy_query(text: str) -> bool:
    lowered = (text or "").lower()
    return any(phrase in lowered for phrase in (
        "scale my business",
        "scale our business",
        "generate more revenue",
        "generate more income",
        "increase revenue",
        "increase income",
        "grow my business",
        "grow our business",
        "how do i scale",
        "how should i scale",
        "what should i do to scale",
        "what should i basically do",
    ))


def _is_create_client_query(text: str) -> bool:
    lowered = (text or "").lower()
    return any(phrase in lowered for phrase in (
        "create a client",
        "create client",
        "i want to create a client",
        "add a client",
        "add new client",
        "add a new client",
        "i want to add a client",
        "i want to add a new client",
        "new client",
    ))


def _is_create_invoice_query(text: str) -> bool:
    lowered = (text or "").lower()
    return any(phrase in lowered for phrase in (
        "create an invoice",
        "create invoice",
        "i want to create an invoice",
        "i would like to create an invoice",
        "make an invoice",
        "raise an invoice",
        "new invoice",
    )) or bool(re.search(r"^(?:an?\s+)?invoice\s+for\s+.+$", lowered.strip()))


def _is_delete_invoice_query(text: str) -> bool:
    lowered = (text or "").lower()
    return (
        "invoice" in lowered
        and any(token in lowered for token in ("delete", "remove", "cancel"))
    )


def _is_delete_confirmation(text: str) -> bool:
    lowered = (text or "").strip().lower()
    return lowered in {
        "yes",
        "yes delete",
        "confirm",
        "confirm delete",
        "delete it",
        "do it",
        "go ahead",
    }


def _is_cancel_query(text: str) -> bool:
    lowered = (text or "").strip().lower()
    return lowered in {"cancel", "cancel it", "never mind", "stop", "dont delete", "don't delete"}


def _is_client_list_query(text: str) -> bool:
    lowered = (text or "").lower()
    return any(phrase in lowered for phrase in (
        "list all clients",
        "list clients",
        "our clients",
        "who are our clients",
        "list of clients",
        "get me the list of clients",
        "show me the clients",
        "show clients",
        "client list",
        "customer list",
        "who are the clients",
        "newest to oldest",
    ))


def _is_unpaid_invoice_query(text: str) -> bool:
    lowered = (text or "").lower()
    return any(phrase in lowered for phrase in (
        "which invoices are still unpaid",
        "which invoices are unpaid",
        "show unpaid invoices",
        "unpaid invoices",
        "still unpaid",
        "pending invoices",
        "which invoices are pending",
    ))


def _is_salary_lookup_query(text: str) -> bool:
    lowered = (text or "").lower()
    return (
        "salary" in lowered or "salaries" in lowered or "employee salary" in lowered
    ) and any(
        token in lowered for token in ("last month", "this month", "quarter", "this quarter", "year", "paid", "payment", "expenses", "expense", "see any")
    )


def _is_income_transaction_query(text: str) -> bool:
    lowered = (text or "").lower()
    return any(
        phrase in lowered for phrase in (
            "income transaction",
            "income transactions",
            "show me all income",
            "show all income",
            "show me income",
            "show income transactions",
            "all income transactions",
        )
    )


def _is_record_expense_query(text: str) -> bool:
    lowered = (text or "").lower()
    return (
        "expense" in lowered
        and any(token in lowered for token in ("add", "record", "log", "create"))
        and not any(token in lowered for token in ("show", "list", "what did we spend", "how much did we spend"))
    )


def _is_partial_payment_query(text: str) -> bool:
    lowered = (text or "").lower()
    return any(phrase in lowered for phrase in (
        "partial payment",
        "part payment",
        "record partial payment",
        "record a partial payment",
        "advance payment",
    ))


def _is_record_payment_query(text: str) -> bool:
    lowered = (text or "").lower()
    return any(phrase in lowered for phrase in (
        "mark the invoice as paid",
        "mark invoice as paid",
        "mark as paid",
        "invoice paid",
        "record payment",
        "record a payment",
        "payment received",
        "received payment",
        "collect payment",
        "partial payment",
        "part payment",
    ))


def _normalize_intent_text(text: str) -> str:
    lowered = re.sub(r"[^a-z0-9\s']", " ", (text or "").lower())
    return re.sub(r"\s+", " ", lowered).strip()


def _has_any_phrase(text: str, phrases: Tuple[str, ...]) -> bool:
    return any(phrase in text for phrase in phrases)


def _has_all_tokens(text: str, token_groups: Tuple[Tuple[str, ...], ...]) -> bool:
    return all(any(token in text for token in group) for group in token_groups)


def _semantic_intent_score(text: str, positive_groups: Tuple[Tuple[str, ...], ...], negative_groups: Tuple[Tuple[str, ...], ...] = ()) -> float:
    normalized = _normalize_intent_text(text)
    if not normalized:
        return 0.0
    score = 0.0
    for group in positive_groups:
        matched = sum(1 for token in group if token in normalized)
        if matched:
            score += matched / max(len(group), 1)
    for group in negative_groups:
        if any(token in normalized for token in group):
            score -= 0.75
    return score


def _semantic_invoice_followup_intent(text: str, allowed: Tuple[str, ...]) -> Optional[str]:
    normalized = _normalize_intent_text(text)
    if not normalized:
        return None
    if "negative" in allowed and (
        "not send" in normalized
        or "not email" in normalized
        or "don't send" in normalized
        or "dont send" in normalized
        or "do not send" in normalized
    ):
        return "negative"

    intent_specs = {
        "negative": {
            "positive": (("no", "nope", "nah", "not", "not now", "skip", "later", "yet"), ("don't", "dont", "do not", "leave", "stop")),
            "negative": (("yes", "send", "email", "add", "another", "more"),),
        },
        "affirmative": {
            "positive": (("yes", "yeah", "yep", "sure", "okay", "ok", "go ahead"), ("send", "email", "mail", "do it")),
            "negative": (("no", "don't", "dont", "do not"),),
        },
        "add_item": {
            "positive": (("add", "include", "put"), ("another", "more", "extra", "next"), ("item", "line", "service", "charge")),
            "negative": (("no", "don't", "dont", "do not", "stop"),),
        },
        "set_quantity": {
            "positive": (("quantity", "qty", "units", "pieces", "chargers", "make it", "keep it"),),
            "negative": (("send", "email"),),
        },
    }

    scored = []
    for intent in allowed:
        spec = intent_specs.get(intent)
        if not spec:
            continue
        score = _semantic_intent_score(normalized, spec["positive"], spec.get("negative", ()))
        if score > 0:
            scored.append((score, intent))
    if not scored:
        return None
    scored.sort(reverse=True)
    if len(scored) > 1 and scored[0][0] - scored[1][0] < 0.35:
        return None
    return scored[0][1] if scored[0][0] >= 0.9 else None


def _is_affirmative_response_query(text: str) -> bool:
    lowered = _normalize_intent_text(text)
    return (
        lowered in {"yes", "yeah", "yep", "sure", "okay", "ok", "go ahead", "do it"}
        or _has_any_phrase(lowered, (
            "yes send it",
            "yes email it",
            "email it now",
            "send it now",
            "send this now",
            "send it immediately",
            "send this immediately",
            "go ahead and send",
            "please send it",
            "please email it",
            "send the invoice",
            "email the invoice",
        ))
    )


def _is_send_confirmation_query(text: str) -> bool:
    lowered = _normalize_intent_text(text)
    if _is_negative_response_query(lowered):
        return False
    return (
        _is_affirmative_response_query(lowered)
        or _has_all_tokens(lowered, (("send", "email", "mail"), ("invoice", "it", "this")))
    )


def _is_negative_response_query(text: str) -> bool:
    lowered = _normalize_intent_text(text)
    return (
        lowered in {
            "no",
            "nope",
            "nah",
            "not now",
            "no more",
            "no more items",
            "that's all",
            "that is all",
            "nothing else",
        }
        or _has_any_phrase(lowered, (
            "don't send it",
            "do not send it",
            "dont send it",
            "don't email it",
            "do not email it",
            "dont email it",
            "no don't send it",
            "no do not send it",
            "no thanks",
            "skip that",
            "leave it as is",
        ))
    )


def _is_add_invoice_item_query(text: str) -> bool:
    lowered = _normalize_intent_text(text)
    return (
        _has_any_phrase(lowered, (
            "add another item",
            "add one more item",
            "add one more line item",
            "add another line item",
            "add item",
            "another item",
            "one more item",
            "more items",
            "another line",
            "one more line",
        ))
        or _has_all_tokens(lowered, (("add", "include", "put"), ("another", "more", "extra"), ("item", "line item", "line")))
    )


def _extract_quantity_value(text: str) -> Optional[float]:
    raw = (text or "").strip().lower()
    if not raw:
        return None
    word_map = {
        "one": 1.0,
        "single": 1.0,
        "two": 2.0,
        "three": 3.0,
        "four": 4.0,
        "five": 5.0,
        "six": 6.0,
        "seven": 7.0,
        "eight": 8.0,
        "nine": 9.0,
        "ten": 10.0,
    }
    for token, value in word_map.items():
        if re.search(rf"\b(?:quantity\s+is\s+|make\s+it\s+|keep\s+it\s+at\s+|just\s+)?{token}\b", raw):
            return value

    # Avoid treating a plain spoken amount like "for 5000 rupees" as quantity.
    if re.search(r"\b(?:rupees?|rs|inr|amount|price|rate)\b", raw) and not re.search(
        r"\b(?:quantity|qty|units?|items?|chargers?|pieces?)\b",
        raw,
    ):
        return None

    match = re.search(
        r"\b(?:quantity\s+is\s+|qty\s+is\s+|make\s+it\s+|keep\s+it\s+at\s+|set\s+quantity\s+to\s+)(\d+(?:\.\d+)?)\b",
        raw,
    )
    if match:
        try:
            value = float(match.group(1))
        except ValueError:
            return None
        return value if value > 0 else None

    match = re.search(
        r"\b(\d+(?:\.\d+)?)\s*(?:units?|items?|chargers?|pieces?)\b",
        raw,
    )
    if match:
        try:
            value = float(match.group(1))
        except ValueError:
            return None
        return value if value > 0 else None
    return None


def _normalize_team_code_value(value: Any) -> Optional[str]:
    extracted = _extract_team_code(str(value or ""))
    if extracted:
        return extracted
    cleaned = str(value or "").strip()
    return cleaned or None


def _extract_invoice_item_rewrite(text: str) -> Optional[Tuple[int, str]]:
    raw = (text or "").strip()
    if not raw:
        return None
    ordinal_map = {
        "first": 0,
        "1st": 0,
        "second": 1,
        "2nd": 1,
        "third": 2,
        "3rd": 2,
    }
    patterns = (
        r"^(?:write|change|update|edit|make)\s+the\s+(first|1st|second|2nd|third|3rd)\s+(?:invoice\s+)?(?:line\s+)?item\s+(?:as|to)\s+(.+)$",
        r"^(?:write|change|update|edit|make)\s+(first|1st|second|2nd|third|3rd)\s+(?:invoice\s+)?(?:line\s+)?item\s+(?:as|to)\s+(.+)$",
    )
    for pattern in patterns:
        match = re.search(pattern, raw, flags=re.I)
        if not match:
            continue
        ordinal = match.group(1).lower()
        replacement = _clean_name_phrase(match.group(2))
        index = ordinal_map.get(ordinal)
        if index is not None and replacement:
            return index, replacement
    return None


def _extract_invoice_item_replacement_text(text: str) -> Optional[str]:
    raw = (text or "").strip()
    if not raw:
        return None
    patterns = (
        r"^(?:replace\s+(?:this|that|it)\s+with)\s+(.+)$",
        r"^(?:change\s+(?:this|that|it)\s+to)\s+(.+)$",
        r"^(?:make\s+(?:this|that|it))\s+(.+)$",
    )
    for pattern in patterns:
        match = re.search(pattern, raw, flags=re.I)
        if match:
            candidate = _clean_invoice_item_followup_text(match.group(1))
            if candidate:
                return candidate
    return None


def _next_invoice_missing_prompt(draft: dict) -> str:
    client_name = str(draft.get("client_name") or "this client").strip()
    if not draft.get("due_date"):
        return "What due date should I put on the invoice?"
    if not draft.get("team_code"):
        return "What is your team security code to finalize it?"
    if not draft.get("line_items"):
        return f"What should I bill {client_name} for, and what amount should I use?"
    return f"I've updated the invoice draft for {client_name}."


def _clean_invoice_item_followup_text(text: str) -> str:
    cleaned = (text or "").strip()
    cleaned = re.sub(r"^(?:add\s+)?(?:another|one\s+more|new)\s+(?:line\s+)?item(?:\s+(?:called|as|is))?\s*", "", cleaned, flags=re.I)
    cleaned = re.sub(r"^(?:another\s+item\s+name\s+is|item\s+name\s+is|name\s+is)\s+", "", cleaned, flags=re.I)
    cleaned = re.sub(r"^(?:this\s+is|it\s+is|is|for)\s+", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\b(?:at|for)\s+\d[\d,]*(?:\.\d+)?\s*(?:rupees?|rs|inr)?(?:\s+each)?\b.*$", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\b\d[\d,]*(?:\.\d+)?\b", "", cleaned)
    cleaned = re.sub(r"\b(?:rupees?|rs|inr|each|also|with|a|the)\b", " ", cleaned, flags=re.I)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .,-")
    blocked = {
        "",
        "this",
        "this is",
        "it",
        "it is",
        "also",
        "also with",
        "also with a",
        "with a",
        "item",
        "another item",
        "new item",
        "name is",
        "for",
    }
    if cleaned.lower() in blocked:
        return ""
    return cleaned


def _formalize_invoice_description(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", str(value or "").strip())
    if not cleaned:
        return ""
    cleaned = re.sub(r"^(?:i\s+basically\s+provided\s+them|i\s+provided\s+them|we\s+provided|we\s+did|it\s+was|this\s+was)\s+", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\bwhich\s+costs?\b.*$", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\bcost\s+for\b.*$", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\bfor\s+all\s+the\s+voltnest\s+services\b", "for EV charging services", cleaned, flags=re.I)
    cleaned = re.sub(r"\binfra(?:structural)?\b", "infrastructure", cleaned, flags=re.I)
    cleaned = re.sub(r"\bac\s+charger\s+adaption\b", "AC charger adaptation", cleaned, flags=re.I)
    cleaned = re.sub(r"\belectrical\s+ac\s*dc\s+charges\b", "AC/DC charging infrastructure", cleaned, flags=re.I)
    cleaned = re.sub(r"\bac\s*dc\s+charges\b", "AC/DC charging infrastructure", cleaned, flags=re.I)
    cleaned = re.sub(r"\bac\s*dc\s+chargers?\b", "AC/DC charging infrastructure", cleaned, flags=re.I)
    cleaned = re.sub(r"\badapting\s+to\b", "adaptation for", cleaned, flags=re.I)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .,-")

    lowered = cleaned.lower()
    if "consultation" in lowered and any(token in lowered for token in ("ac/dc", "electrical", "adaptation")):
        return "AC/DC charging infrastructure adaptation consultation"
    if "consultation" in lowered and any(token in lowered for token in ("infrastructure", "setup", "charger", "ev", "service")):
        return "EV charging infrastructure setup consultation"
    if "site inspection" in lowered and "navi mumbai" in lowered:
        return "Site inspection at Navi Mumbai"
    if cleaned:
        return cleaned[0].upper() + cleaned[1:]
    return cleaned


def _is_invoice_description_help_query(text: str) -> bool:
    lowered = _normalize_intent_text(text)
    return _has_any_phrase(
        lowered,
        (
            "what should we include for this description",
            "what should i include for this description",
            "what should we write for this description",
            "what should i write for this description",
            "what should we put for this description",
            "what should i put for this description",
            "what should we include",
            "what should i include",
            "what should we write",
            "what should i write",
            "how do we word this",
            "how should we word this",
            "how do i word this",
            "how should i word this",
            "word this in invoice",
            "word this for invoice",
            "describe description in invoice",
            "description in invoice",
            "help me write this description",
            "suggest a better description",
        ),
    )


def _merge_invoice_description_fragments(existing: str, fragment: str) -> str:
    existing_clean = str(existing or "").strip()
    fragment_clean = _clean_invoice_item_followup_text(fragment)
    if not fragment_clean:
        return existing_clean
    if not existing_clean:
        return _formalize_invoice_description(fragment_clean)

    existing_norm = re.sub(r"\s+", " ", existing_clean.lower())
    fragment_norm = re.sub(r"\s+", " ", fragment_clean.lower())
    if fragment_norm in existing_norm:
        return _formalize_invoice_description(existing_clean)
    if existing_norm in fragment_norm:
        return _formalize_invoice_description(fragment_clean)

    combined = f"{existing_clean} {fragment_clean}".strip()
    return _formalize_invoice_description(combined)


def _is_cancel_invoice_item_query(text: str) -> bool:
    lowered = _normalize_intent_text(text)
    return lowered in {"cancel", "cancel it", "never mind", "skip it", "drop it", "remove it"} or _has_any_phrase(
        lowered,
        ("cancel it", "cancel that", "skip this item", "skip that item", "never mind that item"),
    )


def _merge_additional_invoice_item_followup(text: str, draft: Optional[dict]) -> Tuple[dict, str]:
    merged = dict(draft or {})
    if _is_cancel_invoice_item_query(text):
        merged.pop("_awaiting_additional_item_description", None)
        merged.pop("_pending_additional_item_description", None)
        return merged, "cancelled"

    due_date_phrase = _extract_due_date_phrase(text)
    if due_date_phrase:
        merged["due_date"] = due_date_phrase
        merged.pop("_awaiting_additional_item_description", None)
        merged.pop("_pending_additional_item_description", None)
        return merged, "due_date"

    replacement_description = _extract_invoice_item_replacement_text(text)
    if replacement_description:
        merged["_pending_additional_item_description"] = _formalize_invoice_description(replacement_description)
        merged.pop("_awaiting_additional_item_description", None)
        return merged, "awaiting_amount"

    explicit_items = _extract_line_items_from_invoice_text(text)
    if explicit_items:
        existing = [item for item in (merged.get("line_items") or []) if isinstance(item, dict)]
        merged["line_items"] = existing + explicit_items
        merged.pop("_awaiting_additional_item_description", None)
        merged.pop("_pending_additional_item_description", None)
        return merged, "completed"

    pending_description = str(merged.get("_pending_additional_item_description") or "").strip()
    if pending_description and _is_invoice_description_help_query(text):
        return merged, "suggested_description"
    amount = _extract_amount_value(text)

    if pending_description and amount:
        existing = [item for item in (merged.get("line_items") or []) if isinstance(item, dict)]
        existing.append({
            "description": pending_description,
            "quantity": 1,
            "unit_price": float(amount),
            "gst_percent": 18,
            "type": "SERVICE",
        })
        merged["line_items"] = existing
        merged.pop("_awaiting_additional_item_description", None)
        merged.pop("_pending_additional_item_description", None)
        return merged, "completed"

    description = _clean_invoice_item_followup_text(text)
    if description and not amount:
        if pending_description:
            merged["_pending_additional_item_description"] = _merge_invoice_description_fragments(
                pending_description,
                description,
            )
        else:
            merged["_pending_additional_item_description"] = _formalize_invoice_description(description)
        merged.pop("_awaiting_additional_item_description", None)
        return merged, "awaiting_amount"

    if pending_description:
        return merged, "awaiting_amount"

    merged["_awaiting_additional_item_description"] = True
    return merged, "awaiting_description"


def _handle_invoice_item_review_followup(text: str, draft: Optional[dict]) -> Tuple[dict, Optional[str]]:
    merged = dict(draft or {})
    line_items = [item for item in (merged.get("line_items") or []) if isinstance(item, dict)]
    if not line_items:
        merged.pop("_awaiting_invoice_item_review", None)
        merged.pop("_awaiting_add_more_items_confirmation", None)
        return merged, None
    semantic_intent = _semantic_invoice_followup_intent(
        text,
        ("negative", "add_item", "set_quantity", "affirmative"),
    )

    if merged.get("_awaiting_invoice_item_review"):
        if _extract_amount_value(text) and any(token in (text or "").lower() for token in ("rupees", "rs", "inr", "amount", "price", "rate")):
            line_items[-1]["quantity"] = 1
            merged["line_items"] = line_items
            merged.pop("_awaiting_invoice_item_review", None)
            merged["_awaiting_add_more_items_confirmation"] = True
            return merged, "Got it. Do you want to add another item?"
        if _is_negative_response_query(text) or semantic_intent == "negative":
            line_items[-1]["quantity"] = 1
            merged["line_items"] = line_items
            merged.pop("_awaiting_invoice_item_review", None)
            merged["_awaiting_add_more_items_confirmation"] = True
            return merged, "Okay, I'll keep the quantity as 1. Do you want to add another item?"
        if _is_add_invoice_item_query(text) or semantic_intent == "add_item":
            merged.pop("_awaiting_invoice_item_review", None)
            merged["_awaiting_additional_item_description"] = True
            return merged, "Sure. Tell me the next item description."

        quantity = _extract_quantity_value(text)
        if quantity is None and semantic_intent == "set_quantity":
            quantity = 1.0 if "single" in _normalize_intent_text(text) else None
        if quantity:
            line_items[-1]["quantity"] = quantity
            merged["line_items"] = line_items
            merged.pop("_awaiting_invoice_item_review", None)
            merged["_awaiting_add_more_items_confirmation"] = True
            return merged, "Got it. Do you want to add another item?"

    if merged.get("_awaiting_add_more_items_confirmation"):
        if _is_negative_response_query(text) or semantic_intent == "negative":
            merged.pop("_awaiting_add_more_items_confirmation", None)
            return merged, _next_invoice_missing_prompt(merged)
        if _is_add_invoice_item_query(text) or semantic_intent in {"add_item", "affirmative"} or re.search(r"\b(?:yes|yeah|yep|sure|okay|ok)\b", (text or "").lower()):
            merged.pop("_awaiting_add_more_items_confirmation", None)
            merged["_awaiting_additional_item_description"] = True
            return merged, "Sure. Tell me the next item description."

    return merged, None


def _extract_expense_category_query(text: str) -> Optional[str]:
    lowered = (text or "").lower()
    category_tokens = {
        "rent": ("rent", "office rent"),
        "salaries": ("salary", "salaries", "payroll"),
        "travel": ("travel", "site visit", "site travel"),
        "fuel": ("fuel", "diesel", "petrol"),
        "hardware": ("hardware", "parts", "procurement", "charger hardware"),
        "software": ("software", "subscription", "cloud", "monitoring"),
        "utilities": ("utilities", "internet", "electricity"),
        "marketing": ("marketing", "lead generation", "tender outreach"),
    }
    if not any(token in lowered for token in ("expense", "expenses", "spend", "spent", "related")):
        return None
    for category, tokens in category_tokens.items():
        if any(token in lowered for token in tokens):
            return category
    return None


def _clean_name_phrase(value: str) -> str:
    cleaned = (value or "").strip()
    cleaned = re.sub(r"^(the\s+)?main\s+contact\s+person\s+name\s+is\s+", "", cleaned, flags=re.I)
    cleaned = re.sub(r"^(the\s+)?main\s+contact\s+person\s+is\s+", "", cleaned, flags=re.I)
    cleaned = re.sub(r"^(the\s+)?contact\s+person\s+name\s+is\s+", "", cleaned, flags=re.I)
    cleaned = re.sub(r"^(the\s+)?contact\s+person\s+is\s+", "", cleaned, flags=re.I)
    cleaned = re.sub(r"^(the\s+)?client'?s?\s+name\s+is\s+", "", cleaned, flags=re.I)
    cleaned = re.sub(r"^(name\s+is\s+)", "", cleaned, flags=re.I)
    cleaned = re.sub(r"^(for\s+)", "", cleaned, flags=re.I)
    cleaned = re.sub(r"^(client\s+is\s+)", "", cleaned, flags=re.I)
    cleaned = re.sub(r"^(?:i\s+would\s+like\s+to|i'?d\s+like\s+to|i\s+want\s+to)\s+(?:add|create)\s+(?:a\s+)?new?\s*client\s+", "", cleaned, flags=re.I)
    cleaned = re.sub(r"^(?:add|create)\s+(?:a\s+)?new?\s*client\s+", "", cleaned, flags=re.I)
    cleaned = re.sub(r"^(i\s+want\s+to\s+(?:add|create)\s+(?:a\s+)?new?\s*client\s*)$", "", cleaned, flags=re.I)
    cleaned = re.sub(r"^(i\s+want\s+to\s+create\s+an?\s+invoice\s+for\s+)", "", cleaned, flags=re.I)
    cleaned = re.sub(r"^[\"']|[\"']$", "", cleaned)
    return cleaned.strip(" .")


def _looks_like_company_name(value: str) -> bool:
    lowered = re.sub(r"\s+", " ", (value or "").lower()).strip(" .")
    if not lowered:
        return False
    legal_markers = (
        "private limited", "pvt ltd", "pvt. ltd", "limited", "ltd", "llp",
        "inc", "inc.", "corp", "corporation", "company", "co.", "co ",
    )
    business_markers = (
        "logistics", "technologies", "technology", "solutions", "enterprises",
        "industries", "systems", "services", "traders", "exports", "imports",
        "associates", "ventures", "agency", "group",
    )
    return any(marker in lowered for marker in legal_markers) or any(marker in lowered for marker in business_markers)


def _extract_company_name(text: str) -> Optional[str]:
    raw = (text or "").strip()
    if not raw:
        return None

    raw = re.sub(
        r"^(?:i\s+would\s+like\s+to|i'?d\s+like\s+to|i\s+want\s+to|please)\s+",
        "",
        raw,
        flags=re.I,
    )
    raw = re.sub(
        r"^(?:add|create)\s+(?:a\s+)?(?:new\s+)?client\s+",
        "",
        raw,
        flags=re.I,
    )

    create_client_match = re.search(
        r"(?:add|create)\s+(?:a\s+)?(?:new\s+)?client\s+(.+)$",
        raw,
        flags=re.I,
    )
    if create_client_match:
        candidate = _clean_name_phrase(create_client_match.group(1))
        if candidate and _looks_like_company_name(candidate):
            return candidate

    patterns = (
        r"(?:company\s+name\s+is|company\s+is|from\s+company)\s+(.+)$",
        r"(?:they\s+work\s+at|works\s+at|work\s+at|from)\s+(.+)$",
    )
    for pattern in patterns:
        match = re.search(pattern, raw, flags=re.I)
        if match:
            candidate = _clean_name_phrase(match.group(1))
            if candidate:
                return candidate

    candidate = _clean_name_phrase(raw)
    if _looks_like_company_name(candidate):
        return candidate
    return None


def _extract_email(text: str) -> Optional[str]:
    match = re.search(r"\b[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}\b", text or "", flags=re.I)
    if match:
        return match.group(0)

    lowered = (text or "").lower().strip()
    lowered = re.sub(r"^(email\s+(?:is|address\s+is)\s+)", "", lowered, flags=re.I)
    lowered = re.sub(r"\bact\b", "at", lowered)
    lowered = lowered.replace(" at the ", " @ ")
    lowered = lowered.replace(" at ", " @ ")
    lowered = lowered.replace(" dot ", " . ")
    lowered = lowered.replace(" underscore ", "_")
    lowered = lowered.replace(" hyphen ", "-")
    lowered = re.sub(r"\b(the|my|is)\b", " ", lowered)
    lowered = re.sub(r"\s+", " ", lowered).strip()

    if "@" in lowered or "." in lowered:
        candidate = lowered.replace(" ", "")
        candidate = re.sub(r"@+", "@", candidate)
        candidate = re.sub(r"\.+", ".", candidate)
        if "@" in candidate:
            local, _, domain = candidate.partition("@")
            if domain and "." not in domain:
                for suffix in ("com", "in", "org", "net", "co"):
                    if domain.endswith(suffix) and len(domain) > len(suffix):
                        domain = f"{domain[:-len(suffix)]}.{suffix}"
                        break
            candidate = f"{local}@{domain}"
        if re.fullmatch(r"[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}", candidate, flags=re.I):
            return candidate

    return None


def _looks_like_email_fragment(text: str) -> bool:
    lowered = (text or "").lower()
    if "@" in lowered:
        return True
    if re.search(r"\bemail\b", lowered):
        return True
    if re.search(r"\b(?:at|dot|underscore|hyphen)\b", lowered):
        return True
    if re.search(r"\b(?:com|org|net|co|io|edu)\b", lowered):
        return True
    return bool(re.fullmatch(r"[a-z]{2,6}", lowered.strip()))


def _try_build_email_from_fragment(fragment: str) -> Optional[str]:
    cleaned = (fragment or "").lower().strip()
    cleaned = re.sub(r"^(email\s+(?:is|address\s+is)\s+)", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\bact\b", "at", cleaned)
    cleaned = cleaned.replace(" at the ", " @ ")
    cleaned = cleaned.replace(" at ", " @ ")
    cleaned = cleaned.replace(" dot ", " . ")
    cleaned = re.sub(r"\b(the|my|is)\b", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    direct = _extract_email(cleaned)
    if direct:
        return direct

    tokens = [token for token in re.split(r"[\s.]+", cleaned) if token]
    if "@" not in cleaned and len(tokens) >= 2:
        local = tokens[0]
        if local in {"at", "dot", "underscore", "hyphen"}:
            return None
        domain = "".join(tokens[1:])
        for suffix in ("com", "in", "org", "net", "co"):
            if domain.endswith(suffix) and len(domain) > len(suffix):
                candidate = f"{local}@{domain[:-len(suffix)]}.{suffix}"
                if re.fullmatch(r"[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}", candidate, flags=re.I):
                    return candidate
        candidate = f"{local}@{domain}"
        if re.fullmatch(r"[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}", candidate, flags=re.I):
            return candidate
    return None


def _extract_phone(text: str) -> Optional[str]:
    raw = text or ""
    compact_match = re.search(r"(?:\+91[\s\-]?)?[6-9][\d\s\-]{8,14}", raw)
    if compact_match:
        digits = re.sub(r"\D", "", compact_match.group(0))
        if len(digits) == 12 and digits.startswith("91"):
            digits = digits[2:]
        if len(digits) == 10 and digits[0] in "6789":
            return digits

    all_digits = re.sub(r"\D", "", raw)
    if len(all_digits) == 12 and all_digits.startswith("91"):
        all_digits = all_digits[2:]
    if len(all_digits) == 10 and all_digits[0] in "6789":
        return all_digits
    return None


def _extract_phone_fragment(text: str) -> Optional[str]:
    raw = text or ""
    digits = re.sub(r"\D", "", raw)
    if digits.startswith("91") and len(digits) > 10:
        digits = digits[2:]
    if 6 <= len(digits) <= 10 and digits[0] in "6789":
        return digits
    return None


def _normalize_spoken_digits(text: str) -> str:
    lowered = (text or "").lower()
    token_map = {
        "zero": "0", "oh": "0", "o": "0",
        "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
        "six": "6", "seven": "7", "eight": "8", "nine": "9",
    }
    tokens = re.findall(r"[a-zA-Z]+|\d+", lowered)
    if not tokens:
        return ""
    converted = []
    for token in tokens:
        if token.isdigit():
            converted.append(token)
        elif token in token_map:
            converted.append(token_map[token])
        else:
            return ""
    return "".join(converted)


def _extract_team_code(text: str) -> Optional[str]:
    raw_text = (text or "").strip()
    lowered = raw_text.lower()
    patterns = (
        r"(?:team\s+(?:security\s+)?code\s+is\s+)([A-Za-z0-9\-\s]{4,40})",
        r"(?:code\s+is\s+)([A-Za-z0-9\-\s]{4,40})",
        r"(?:security\s+code\s+is\s+)([A-Za-z0-9\-\s]{4,40})",
        r"(?:it\s+is\s+)([A-Za-z0-9\-\s]{4,40})",
    )
    for pattern in patterns:
        match = re.search(pattern, lowered, flags=re.I)
        if match:
            candidate_raw = match.group(1).strip()
            candidate = re.sub(r"\s+", "", candidate_raw)
            if re.fullmatch(r"\d{4,8}", candidate):
                return candidate
            if re.fullmatch(r"(?=.*\d)[A-Za-z0-9\-]{4,20}", candidate):
                return candidate
            spoken_candidate = _normalize_spoken_digits(candidate_raw)
            if re.fullmatch(r"\d{4,8}", spoken_candidate):
                return spoken_candidate
    compact = re.sub(r"\s+", "", raw_text)
    if re.fullmatch(r"(?:\d{4,8}|(?=.*\d)[A-Za-z0-9\-]{4,20})", compact):
        return compact
    spoken_digits = _normalize_spoken_digits(raw_text)
    if re.fullmatch(r"\d{4,8}", spoken_digits):
        return spoken_digits
    return None


def _extract_client_name_for_invoice(text: str) -> Optional[str]:
    lowered = (text or "").lower()
    blocked_exact = {
        "client", "a client", "the client",
        "cancel", "cancel it", "stop", "never mind",
        "this is", "also with a", "with a", "also", "this",
    }
    item_markers = (
        "service", "item", "setup", "installation", "amc", "charger", "charges",
        "upgrade", "compliance", "system", "panel", "safety", "maintenance",
        "electrical", "supply", "smart load", "load management",
    )
    if "invoice" in lowered:
        match = re.search(r"(?:invoice\s+for\s+)(.+)$", text, flags=re.I)
        if match:
            candidate = _clean_name_phrase(match.group(1))
            raw_candidate = candidate.lower().strip()
            if raw_candidate in blocked_exact or _normalize_phrase_tokens(candidate) == "":
                return None
            return candidate
    if lowered.startswith("for "):
        candidate = _clean_name_phrase(text)
        raw_candidate = candidate.lower().strip()
        if raw_candidate in blocked_exact or _normalize_phrase_tokens(candidate) == "":
            return None
        return candidate
    candidate = _clean_name_phrase(text)
    raw_candidate = candidate.lower().strip()
    if (
        candidate
        and raw_candidate not in blocked_exact
        and _normalize_phrase_tokens(candidate) != ""
        and not _extract_team_code(text)
        and not _extract_due_date_phrase(text)
        and not _extract_amount_value(text)
        and not _extract_email(text)
        and not _extract_phone(text)
        and not _is_create_invoice_query(text)
        and not any(marker in raw_candidate for marker in item_markers)
    ):
        return candidate
    return None


def _extract_invoice_number(text: str) -> Optional[str]:
    match = re.search(r"\b(?:INV|VN)-[A-Z0-9-]+\b", (text or "").upper())
    return match.group(0) if match else None


def _extract_client_name_for_payment(text: str) -> Optional[str]:
    raw = (text or "").strip()
    lowered = raw.lower()
    blocked_exact = {
        "", "client", "the client", "invoice", "the invoice", "it", "this", "that",
        "mark paid", "mark as paid", "paid", "partial payment", "payment",
    }
    patterns = (
        r"(?:from)\s+(.+)$",
        r"(?:for)\s+(.+?)(?:\s+invoice)?$",
        r"(?:client\s+is)\s+(.+)$",
    )
    for pattern in patterns:
        match = re.search(pattern, raw, flags=re.I)
        if match:
            candidate = _clean_name_phrase(match.group(1))
            candidate = re.sub(
                r"\s+(?:by|via|through)\s+(?:neft|rtgs|imps|upi|cheque|check|cash|dd|demand\s+draft)\b.*$",
                "",
                candidate,
                flags=re.I,
            )
            candidate = re.sub(
                r"\s+(?:utr|reference|ref|transaction id|txn|transaction number|reference number)\b.*$",
                "",
                candidate,
                flags=re.I,
            )
            candidate = candidate.strip(" .,:;-")
            if candidate.lower().strip() not in blocked_exact:
                return candidate
    candidate = _clean_name_phrase(raw)
    if candidate.lower().strip() in blocked_exact:
        return None
    if _extract_amount_value(raw) or _extract_invoice_number(raw) or _extract_due_date_phrase(raw):
        return None
    return candidate or None


def _extract_payment_method(text: str) -> Optional[str]:
    lowered = (text or "").lower()
    mapping = (
        ("NEFT", (" by neft", " via neft", " through neft", " payment by neft", " neft payment")),
        ("RTGS", (" by rtgs", " via rtgs", " through rtgs", " payment by rtgs", " rtgs payment")),
        ("IMPS", (" by imps", " via imps", " through imps", " payment by imps", " imps payment")),
        ("UPI", (" by upi", " via upi", " through upi", " payment by upi", " upi payment")),
        ("CHEQUE", (" by cheque", " via cheque", " through cheque", " cheque payment", " check payment", " by check")),
        ("CASH", (" by cash", " via cash", " cash payment", " paid in cash")),
        ("DD", (" by dd", " via dd", " demand draft", " by demand draft")),
    )
    padded = f" {lowered} "
    for canonical, phrases in mapping:
        if any(phrase in padded for phrase in phrases):
            return canonical
    return None


def _extract_payment_reference(text: str) -> Optional[str]:
    raw = (text or "").strip()
    patterns = (
        r"(?:utr|reference|ref|transaction id|txn|transaction number|reference number)\s*(?:is|number|no\.?|#|:)?\s*([A-Za-z0-9\-_/]{4,})",
    )
    for pattern in patterns:
        match = re.search(pattern, raw, flags=re.I)
        if match:
            return match.group(1).strip(" .,:;")
    return None


def _merge_payment_draft_from_text(text: str, draft: Optional[dict]) -> dict:
    merged = dict(draft or {})
    client_name = _extract_client_name_for_payment(text)
    if client_name:
        merged["client_name"] = client_name

    amount = _extract_amount_value(text)
    if amount:
        merged["amount_received"] = float(amount)

    invoice_number = _extract_invoice_number(text)
    if invoice_number:
        merged["invoice_number"] = invoice_number

    payment_method = _extract_payment_method(text)
    if payment_method:
        merged["payment_method"] = payment_method

    payment_reference = _extract_payment_reference(text)
    if payment_reference:
        merged["utr_or_reference"] = payment_reference

    if _is_partial_payment_query(text):
        merged["is_partial_payment"] = True
    elif "mark" in (text or "").lower() and "paid" in (text or "").lower():
        merged["is_partial_payment"] = False

    return merged


def _month_bounds_for_query(text: str) -> Tuple[date, date, str]:
    today = date.today()
    lowered = (text or "").lower()
    if "all time" in lowered or ("all" in lowered and not any(token in lowered for token in ("last month", "this month", "quarter", "this quarter", "year", "this year"))):
        return date(2024, 1, 1), today, "all time"
    if "this quarter" in lowered or "quarter" in lowered:
        quarter_start_month = ((today.month - 1) // 3) * 3 + 1
        start_quarter = date(today.year, quarter_start_month, 1)
        return start_quarter, today, "this quarter"
    if "this year" in lowered or ("year" in lowered and "last year" not in lowered):
        start_year = date(today.year, 1, 1)
        return start_year, today, "this year"
    if "last month" in lowered:
        first_this_month = today.replace(day=1)
        end_last_month = first_this_month - timedelta(days=1)
        start_last_month = end_last_month.replace(day=1)
        return start_last_month, end_last_month, "last month"
    start_this_month = today.replace(day=1)
    return start_this_month, today, "this month"


def _extract_due_date_phrase(text: str) -> Optional[str]:
    raw = (text or "").strip()
    lowered = raw.lower()
    today = date.today()
    if "net30" in lowered or "net 30" in lowered or "30 day" in lowered:
        return "net30"
    if "net15" in lowered or "net 15" in lowered or "15 day" in lowered:
        return "net15"
    if "net45" in lowered or "net 45" in lowered or "45 day" in lowered:
        return "net45"
    iso_match = re.search(r"\b20\d{2}-\d{2}-\d{2}\b", raw)
    if iso_match:
        return iso_match.group(0)

    month_lookup = {
        "january": 1, "jan": 1,
        "february": 2, "feb": 2,
        "march": 3, "mar": 3,
        "april": 4, "apr": 4,
        "may": 5,
        "june": 6, "jun": 6,
        "july": 7, "jul": 7,
        "august": 8, "aug": 8,
        "september": 9, "sep": 9, "sept": 9,
        "october": 10, "oct": 10,
        "november": 11, "nov": 11,
        "december": 12, "dec": 12,
    }
    month = None
    for token, value in month_lookup.items():
        if re.search(rf"\b{token}\b", lowered):
            month = value
            break

    if month is not None:
        day_match = re.search(r"\b([12]?\d|3[01])(?:st|nd|rd|th)?\b", lowered)
        year_match = re.search(r"\b(20\d{2})\b", lowered)
        day = int(day_match.group(1)) if day_match else None
        explicit_year = year_match is not None
        year = int(year_match.group(1)) if year_match else today.year
        if day:
            try:
                candidate = date(year, month, day)
                if not explicit_year and candidate < today:
                    candidate = date(year + 1, month, day)
                return candidate.isoformat()
            except Exception:
                return None
    return None


def _extract_amount_value(text: str) -> Optional[float]:
    iso_free = re.sub(r"\b20\d{2}-\d{2}-\d{2}\b", " ", text or "")
    match = re.search(r"(\d[\d,\s]{2,})", iso_free)
    if not match:
        return None
    digits = re.sub(r"[^\d]", "", match.group(1))
    if not digits:
        return None
    try:
        return float(digits)
    except Exception:
        return None


def _extract_invoice_service_description(text: str) -> Optional[str]:
    raw = (text or "").strip()
    if not raw:
        return None

    patterns = (
        r"(?:the\s+first\s+invoice\s+item\s+is|the\s+invoice\s+item\s+is|invoice\s+item\s+is)\s+(.+)$",
        r"(?:the\s+first\s+line\s+item\s+is|the\s+line\s+item\s+is|line\s+item\s+is)\s+(.+)$",
        r"(?:the\s+service\s+is|service\s+is|item\s+is|description\s+is)\s+(.+)$",
        r"(?:for\s+service\s+of)\s+(.+)$",
        r"(?:add\s+service\s+as|add\s+item\s+as|add\s+line\s+item\s+as)\s+(.+)$",
        r"(?:add\s+service|add\s+item|add\s+line\s+item)\s+(.+)$",
    )
    for pattern in patterns:
        match = re.search(pattern, raw, flags=re.I)
        if match:
            candidate = match.group(1).strip(" .,-")
            candidate = re.sub(
                r"\b(?:at|for|fall)\s+\d[\d,\s]*(?:\.\d+)?\s*(?:rupees?|rs|inr)?\b.*$",
                "",
                candidate,
                flags=re.I,
            ).strip(" .,-")
            candidate = re.sub(r"\bwhich\s+costs?\b.*$", "", candidate, flags=re.I).strip(" .,-")
            candidate = re.sub(r"\bcost\s+for\b.*$", "", candidate, flags=re.I).strip(" .,-")
            if candidate:
                return _formalize_invoice_description(candidate)
    return None


def _is_invoice_item_intro_query(text: str) -> bool:
    lowered = _normalize_intent_text(text)
    return _has_any_phrase(
        lowered,
        (
            "the item is",
            "item is",
            "the first item is",
            "first item is",
            "the invoice item is",
            "invoice item is",
            "the first invoice item is",
            "first invoice item is",
            "the line item is",
            "line item is",
            "the first line item is",
            "first line item is",
        ),
    )


def _extract_invoice_description_update_target(text: str) -> Optional[str]:
    raw = (text or "").strip()
    if not raw:
        return None
    patterns = (
        r"(?:update|change|edit)\s+(.+?)\s+description\b",
        r"(?:update|change|edit)\s+description\s+(?:for|of)\s+(.+)$",
    )
    for pattern in patterns:
        match = re.search(pattern, raw, flags=re.I)
        if match:
            candidate = _clean_name_phrase(match.group(1))
            if candidate:
                return candidate
    return None


def _extract_expense_date_phrase(text: str, draft: Optional[dict] = None) -> Optional[str]:
    raw = (text or "").strip()
    lowered = raw.lower()
    iso_match = re.search(r"\b20\d{2}-\d{2}-\d{2}\b", raw)
    if iso_match:
        return iso_match.group(0)

    year = None
    draft_value = str((draft or {}).get("expense_date") or "")
    draft_year = re.search(r"\b(20\d{2})\b", draft_value)
    if draft_year:
        year = int(draft_year.group(1))
    else:
        explicit_year = re.search(r"\b(20\d{2})\b", lowered)
        if explicit_year:
            year = int(explicit_year.group(1))

    month_lookup = {
        "january": 1, "jan": 1,
        "february": 2, "feb": 2,
        "march": 3, "mar": 3,
        "april": 4, "apr": 4,
        "may": 5,
        "june": 6, "jun": 6,
        "july": 7, "jul": 7,
        "august": 8, "aug": 8,
        "september": 9, "sep": 9, "sept": 9,
        "october": 10, "oct": 10,
        "november": 11, "nov": 11,
        "december": 12, "dec": 12,
    }
    month = None
    for token, value in month_lookup.items():
        if re.search(rf"\b{token}\b", lowered):
            month = value
            break

    day_match = re.search(r"\b([12]?\d|3[01])(?:st|nd|rd|th)?\b", lowered)
    day = int(day_match.group(1)) if day_match else None

    if month and day:
        try:
            resolved_year = year or date.today().year
            return date(resolved_year, month, day).isoformat()
        except Exception:
            return None

    return None


def _infer_expense_category(text: str) -> Optional[str]:
    lowered = (text or "").lower()
    mapping = {
        "RENT": ("rent", "office rent"),
        "SALARIES": ("salary", "salaries", "payroll"),
        "TRAVEL": ("travel", "site visit", "site travel", "trip"),
        "FUEL": ("fuel", "diesel", "petrol"),
        "HARDWARE": ("hardware", "parts", "charger hardware", "procurement"),
        "SOFTWARE": ("software", "subscription", "cloud", "monitoring"),
        "UTILITIES": ("utility", "utilities", "internet", "electricity"),
        "MARKETING": ("marketing", "lead generation", "tender outreach"),
        "PROFESSIONAL_FEES": ("professional fee", "consultant", "legal fee", "audit fee"),
        "REPAIRS": ("repair", "maintenance repair"),
        "INSURANCE": ("insurance",),
    }
    for category, hints in mapping.items():
        if any(hint in lowered for hint in hints):
            return category
    return None


def _extract_expense_description(text: str) -> Optional[str]:
    cleaned = (text or "").strip()
    patterns = (
        r"(?:expense\s+of\s+[\d,\s]+\s+rupees?\s+for\s+)(.+?)(?:\s+on\s+.+)?$",
        r"(?:add\s+an?\s+expense\s+of\s+[\d,\s]+\s+for\s+)(.+?)(?:\s+on\s+.+)?$",
        r"(?:record\s+an?\s+expense\s+of\s+[\d,\s]+\s+for\s+)(.+?)(?:\s+on\s+.+)?$",
    )
    for pattern in patterns:
        match = re.search(pattern, cleaned, flags=re.I)
        if match:
            return match.group(1).strip(" .")
    if "expense" in cleaned.lower():
        stripped = re.sub(r"^(?:add|record|log|create)\s+an?\s+expense\s+", "", cleaned, flags=re.I)
        stripped = re.sub(r"\bof\s+[\d,\s]+\s+rupees?\b", "", stripped, flags=re.I)
        stripped = re.sub(r"\bon\s+20\d{2}.*$", "", stripped, flags=re.I)
        stripped = stripped.strip(" .")
        return stripped or None
    return None


def _merge_expense_draft_from_text(text: str, draft: Optional[dict]) -> dict:
    merged = dict(draft or {})
    amount = _extract_amount_value(text)
    if amount and not merged.get("amount"):
        merged["amount"] = amount

    description = _extract_expense_description(text)
    if description and not merged.get("description"):
        merged["description"] = description

    category = _infer_expense_category(text)
    if category and not merged.get("category"):
        merged["category"] = category

    expense_date = _extract_expense_date_phrase(text, merged)
    if expense_date:
        merged["expense_date"] = expense_date

    team_code = _extract_team_code(text)
    if team_code:
        merged["team_code"] = team_code

    vendor_match = re.search(r"(?:vendor\s+name\s+is|vendor\s+is|from)\s+(.+)$", text or "", flags=re.I)
    if vendor_match and not merged.get("vendor_name"):
        merged["vendor_name"] = vendor_match.group(1).strip(" .")

    return merged


def _build_client_form_ui_event(draft: Optional[dict]) -> dict:
    clean = {k: v for k, v in (draft or {}).items() if not str(k).startswith("_") and v not in (None, "", [], {})}
    return {
        "type": "open_client_form",
        "path": "/clients",
        "draft": clean,
    }


def _build_invoice_form_ui_event(draft: Optional[dict]) -> dict:
    clean = {k: v for k, v in (draft or {}).items() if not str(k).startswith("_") and v not in (None, "", [], {})}
    return {
        "type": "open_invoice_form",
        "path": "/invoices/new",
        "draft": clean,
    }


def _format_invoice_line_items_text(line_items: List[dict]) -> str:
    rows: List[str] = []
    for item in line_items or []:
        if not isinstance(item, dict):
            continue
        item_type = str(item.get("type") or ("SERVICE" if not item.get("quantity") else "PRODUCT")).upper()
        qty = item.get("quantity", 1)
        if item_type == "SERVICE":
            qty = 1
        rows.append(
            f"{item_type} | {item.get('description', '')} | {qty if qty not in (None, '') else '-'} | {item.get('unit_price', item.get('rate', 0))} | {item.get('gst_percent', item.get('gstPercent', 18))}"
        )
    return "\n".join(row for row in rows if row.strip())


def _parse_invoice_items_text(raw_text: str) -> List[dict]:
    items: List[dict] = []
    for line in (raw_text or "").splitlines():
        cleaned = line.strip()
        if not cleaned:
            continue
        parts = [part.strip() for part in cleaned.split("|")]
        if len(parts) < 4:
            continue
        item_type = "SERVICE"
        if len(parts) >= 5:
            item_type, description, quantity_text, rate_text, gst_text = parts[:5]
        else:
            description, quantity_text, rate_text, gst_text = parts[:4]
        normalized_type = str(item_type or "SERVICE").strip().upper()
        if normalized_type not in {"SERVICE", "PRODUCT"}:
            normalized_type = "SERVICE"
        amount_match = re.search(r"\d[\d,]*(?:\.\d+)?", rate_text)
        gst_match = re.search(r"\d[\d,]*(?:\.\d+)?", gst_text)
        if not amount_match:
            continue
        quantity_match = re.search(r"\d+(?:\.\d+)?", quantity_text or "")
        quantity_value = float(quantity_match.group(0)) if quantity_match else 1
        if normalized_type == "SERVICE":
            quantity_value = 1
        items.append(
            {
                "type": normalized_type,
                "description": description.strip(),
                "quantity": quantity_value,
                "unit_price": float(amount_match.group(0).replace(",", "")),
                "gst_percent": float(gst_match.group(0).replace(",", "")) if gst_match else 18,
            }
        )
    return items


def _build_invoice_preview_dialog_ui_event(session_id: str, draft: Optional[dict]) -> dict:
    clean = {k: v for k, v in (draft or {}).items() if not str(k).startswith("_") and v not in (None, "", [], {})}
    return {
        "type": "open_input_dialog",
        "session_id": session_id,
        "dialog_id": "invoice_preview_form",
        "title": "Live Invoice Preview",
        "message": "Review the invoice draft, edit line items if needed, or keep speaking to update it live.",
        "submit_endpoint": "/api/v1/voice/dialog-response",
        "submit_btn_label": "Update Invoice Draft",
        "fields": [
            {
                "id": "client_name",
                "label": "Client",
                "type": "text",
                "defaultValue": clean.get("client_name", ""),
            },
            {
                "id": "issue_date",
                "label": "Issue Date",
                "type": "date",
                "defaultValue": clean.get("issue_date", date.today().isoformat()),
            },
            {
                "id": "due_date",
                "label": "Due Date",
                "type": "date",
                "defaultValue": clean.get("due_date", ""),
            },
            {
                "id": "invoice_items_text",
                "label": "Line Items",
                "type": "textarea",
                "defaultValue": _format_invoice_line_items_text(clean.get("line_items", [])),
                "placeholder": "SERVICE | Service description | 1 | 50000 | 18",
            },
            {
                "id": "notes",
                "label": "Notes",
                "type": "textarea",
                "defaultValue": clean.get("notes", ""),
                "placeholder": "Optional notes",
            },
        ],
    }


def _build_invoice_client_picker_ui_event(session_id: str, clients: List[dict]) -> Optional[dict]:
    options = []
    for client in clients[:10]:
        if not isinstance(client, dict):
            continue
        name = str(client.get("name") or "").strip()
        company = str(client.get("company") or "").strip()
        if not name:
            continue
        label = f"{name} ({company})" if company and company.lower() != name.lower() else name
        options.append({"id": client.get("id"), "name": label})
    if not options:
        return None
    return {
        "type": "open_client_picker",
        "session_id": session_id,
        "title": "Select Client",
        "message": "Choose an existing client or continue by voice.",
        "clients": options,
    }


def _extract_line_items_from_invoice_text(text: str) -> List[dict]:
    raw = (text or "").strip()
    if not raw:
        return []
    normalized = re.sub(r"\bat the rate\b", "at", raw, flags=re.I)
    normalized = re.sub(r"\brupees only\b", "rupees", normalized, flags=re.I)
    normalized = re.sub(r"\s+", " ", normalized).strip()

    gst_percent = 18.0
    gst_match = re.search(r"\b(\d{1,2}(?:\.\d+)?)\s*%\s*(?:gst)?\b|\bgst\s*(\d{1,2}(?:\.\d+)?)\b", normalized, flags=re.I)
    if gst_match:
        try:
            gst_value = gst_match.group(1) or gst_match.group(2)
            gst_candidate = float(gst_value)
            if 0 <= gst_candidate <= 100:
                gst_percent = gst_candidate
        except ValueError:
            pass

    def _clean_spoken_invoice_description(value: str) -> str:
        cleaned = value
        patterns = (
            r"^(?:the\s+)?first\s+item\s+is\s+",
            r"^(?:the\s+)?next\s+item\s+is\s+",
            r"^(?:the\s+)?item\s+is\s+",
            r"^(?:the\s+)?service\s+is\s+",
            r"^(?:please\s+)?add\s+(?:the\s+)?(?:first\s+)?item\s+as\s+",
            r"^(?:please\s+)?add\s+service\s+as\s+",
        )
        for pattern in patterns:
            cleaned = re.sub(pattern, "", cleaned, flags=re.I)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" .,-")
        return cleaned

    def build_item(segment: str, inherited_gst: float) -> Optional[dict]:
        cleaned = segment.strip(" ,.;")
        if not cleaned:
            return None
        amount_match = re.search(
            r"\bat\s+(\d[\d,]*(?:\.\d+)?)\s*(?:rupees?|rs|inr)?(?:\s+each)?\b",
            cleaned,
            flags=re.I,
        )
        if not amount_match:
            amount_match = re.search(
                r"\bfor\s+(\d[\d,]*(?:\.\d+)?)\s*(?:rupees?|rs|inr)\b",
                cleaned,
                flags=re.I,
            )
        if not amount_match:
            return None
        amount = float(amount_match.group(1).replace(",", ""))
        description = re.sub(
            r"\bat\s+\d[\d,]*(?:\.\d+)?\s*(?:rupees?|rs|inr)?(?:\s+each)?\b.*$",
            "",
            cleaned,
            flags=re.I,
        )
        description = re.sub(
            r"\bfor\s+\d[\d,]*(?:\.\d+)?\s*(?:rupees?|rs|inr)\b.*$",
            "",
            description,
            flags=re.I,
        )
        description = re.sub(r"\bwith\s+\d{1,2}(?:\.\d+)?\s*%?\s*gst\b", "", description, flags=re.I)
        description = re.sub(r"\bgst\b", "", description, flags=re.I)
        description = _clean_spoken_invoice_description(re.sub(r"\s+", " ", description).strip(" .,-"))
        if not description:
            return None

        quantity = 1.0
        qty_source = cleaned
        qty_match = re.search(
            r"\b(?:for\s+)?(\d+(?:\.\d+)?)\s*(?:units?|chargers?|charges?|stations?|connectors?|bays?|points?)\b",
            qty_source,
            flags=re.I,
        )
        if qty_match:
            quantity = float(qty_match.group(1))
            description = re.sub(
                r"\b(?:for\s+)?\d+(?:\.\d+)?\s*(?:units?|chargers?|charges?|stations?|connectors?|bays?|points?)\b",
                "",
                description,
                count=1,
                flags=re.I,
            ).strip(" .,-")

        item_gst = inherited_gst
        item_gst_match = re.search(r"\b(\d{1,2}(?:\.\d+)?)\s*%\s*gst\b|\bgst\s*(\d{1,2}(?:\.\d+)?)\b", cleaned, flags=re.I)
        if item_gst_match:
            try:
                item_gst = float(item_gst_match.group(1) or item_gst_match.group(2))
            except ValueError:
                item_gst = inherited_gst

        return {
            "type": "SERVICE",
            "description": description,
            "quantity": quantity,
            "unit_price": amount,
            "gst_percent": item_gst,
        }

    items: List[dict] = []
    multi_pattern = re.compile(
        r"(.+?)\b(?:at|for)\s+\d[\d,]*(?:\.\d+)?\s*(?:rupees?|rs|inr)?\b(?:\s*(?:,|and|plus|also)\s*|\s*$)",
        flags=re.I,
    )
    segments = [match.group(0).strip() for match in multi_pattern.finditer(normalized)]

    if len(segments) >= 2:
        for segment in segments:
            item = build_item(segment, gst_percent)
            if item:
                items.append(item)
        if items:
            deduped: List[dict] = []
            for item in items:
                normalized_desc = re.sub(r"\s+", " ", str(item.get("description") or "").strip().lower())
                duplicate = next((
                    existing for existing in deduped
                    if abs(float(existing.get("unit_price", 0) or 0) - float(item.get("unit_price", 0) or 0)) < 0.01
                    and (
                        normalized_desc in re.sub(r"\s+", " ", str(existing.get("description") or "").strip().lower())
                        or re.sub(r"\s+", " ", str(existing.get("description") or "").strip().lower()) in normalized_desc
                    )
                ), None)
                if duplicate:
                    if len(normalized_desc) > len(str(duplicate.get("description") or "")):
                        duplicate.update(item)
                else:
                    deduped.append(item)
            return deduped

    single_item = build_item(normalized, gst_percent)
    return [single_item] if single_item else []


def _is_invoice_draft_status_query(text: str) -> bool:
    lowered = (text or "").lower().strip()
    return any(phrase in lowered for phrase in (
        "did you add",
        "did you add the first item",
        "what items",
        "what did you add",
        "show the draft",
        "what is in the invoice",
        "did you capture",
    ))


def _summarize_invoice_draft(draft: Optional[dict]) -> Optional[str]:
    line_items = [item for item in ((draft or {}).get("line_items") or []) if isinstance(item, dict)]
    if not line_items:
        return None
    snippets = []
    for item in line_items[:3]:
        description = str(item.get("description") or "item").strip()
        amount = float(item.get("unit_price", 0) or 0)
        snippets.append(f"{description} for {_inr_words(amount)} rupees")
    if len(line_items) == 1:
        return f"Yes. I currently have {snippets[0]} in the invoice draft."
    return f"Yes. I currently have {', '.join(snippets[:-1])}, and {snippets[-1]} in the invoice draft."


def _merge_client_draft_from_text(text: str, draft: Optional[dict]) -> dict:
    merged = dict(draft or {})
    pending_field = str(merged.get("_pending_field") or "").strip().lower()
    candidate = _clean_name_phrase(text)
    company_name = None if pending_field == "email" else _extract_company_name(text)
    if company_name and not merged.get("company_name"):
        merged["company_name"] = company_name
    elif pending_field == "company_name" and candidate and not merged.get("company_name"):
        lowered_candidate = candidate.lower()
        if lowered_candidate not in {"company", "company name", "the company"}:
            merged["company_name"] = candidate
    if candidate and not merged.get("name") and pending_field not in {"email", "phone", "team_code"}:
        lowered = candidate.lower()
        blocked = {
            "add a new client", "create a client", "create client", "new client",
            "what is the client's actual name", "what is the client actual name",
            "i want to add a new client", "i want to add a client", "i want to create a client",
        }
        looks_like_intent = "client" in lowered and any(word in lowered for word in ("add", "create", "want"))
        if (
            lowered not in blocked
            and not looks_like_intent
            and not company_name
            and "@" not in candidate
            and not re.fullmatch(r"(?:\+91[\s\-]?)?[6-9]\d{9}", candidate)
        ):
            merged["name"] = candidate

    email = _extract_email(text) if pending_field in {"", "email"} else None
    if email:
        merged["email"] = email
        merged.pop("_email_fragment", None)
    elif not merged.get("email") and (pending_field == "email" or _looks_like_email_fragment(text)):
        fragment_parts = [str(merged.get("_email_fragment") or "").strip(), _clean_name_phrase(text)]
        fragment = " ".join(part for part in fragment_parts if part).strip()
        inferred_email = _try_build_email_from_fragment(fragment)
        if inferred_email:
            merged["email"] = inferred_email
            merged.pop("_email_fragment", None)
        elif fragment:
            merged["_email_fragment"] = fragment

    phone = _extract_phone(text) if pending_field in {"", "phone"} else None
    if phone:
        merged["phone"] = phone
        merged.pop("_phone_fragment", None)
    elif not merged.get("phone") and pending_field in {"", "phone"}:
        fragment = _extract_phone_fragment(text)
        if fragment:
            prior = re.sub(r"\D", "", str(merged.get("_phone_fragment") or ""))
            combined = f"{prior}{fragment}"[:10]
            if len(combined) == 10 and combined[0] in "6789":
                merged["phone"] = combined
                merged.pop("_phone_fragment", None)
            else:
                merged["_phone_fragment"] = combined

    team_code = _extract_team_code(text) if pending_field in {"", "team_code"} else None
    if team_code:
        merged["team_code"] = team_code

    return merged


def _merge_invoice_draft_from_text(text: str, draft: Optional[dict]) -> dict:
    merged = dict(draft or {})
    raw_text = (text or "").strip()
    lowered = raw_text.lower()
    explicit_quantity = _extract_quantity_value(text)
    if _is_invoice_item_intro_query(text):
        service_description = _extract_invoice_service_description(text)
        if service_description:
            merged["_pending_line_item_description"] = _formalize_invoice_description(service_description)
            merged.pop("_awaiting_invoice_item_review", None)
            merged.pop("_awaiting_add_more_items_confirmation", None)
        else:
            merged["_awaiting_additional_item_description"] = True
        return merged

    direct_item_rewrite = _extract_invoice_item_rewrite(text)
    if direct_item_rewrite:
        index, replacement = direct_item_rewrite
        line_items = [item for item in (merged.get("line_items") or []) if isinstance(item, dict)]
        if 0 <= index < len(line_items):
            line_items[index]["description"] = _formalize_invoice_description(replacement)
            merged["line_items"] = line_items
            merged["_description_update_completed_message"] = (
                f"Updated the {['first', 'second', 'third'][index]} item to {line_items[index]['description']}."
            )
            merged.pop("_awaiting_invoice_item_review", None)
            merged.pop("_awaiting_add_more_items_confirmation", None)
            return merged

    if merged.get("_pending_description_update_index") is not None:
        replacement = _clean_name_phrase(text)
        if replacement and replacement.lower() not in {"as", "to", "description"}:
            line_items = [item for item in (merged.get("line_items") or []) if isinstance(item, dict)]
            update_index = int(merged.get("_pending_description_update_index"))
            if 0 <= update_index < len(line_items):
                line_items[update_index]["description"] = replacement
                merged["line_items"] = line_items
                merged["_description_update_completed_message"] = f"Updated the description to {replacement}."
            merged.pop("_pending_description_update_index", None)
            merged.pop("_pending_description_update_target", None)
            return merged

    update_target = _extract_invoice_description_update_target(text)
    if update_target:
        line_items = [item for item in (merged.get("line_items") or []) if isinstance(item, dict)]
        normalized_target = update_target.lower().strip()
        for index, item in enumerate(line_items):
            description = str(item.get("description") or "").lower()
            if normalized_target in description:
                merged["_pending_description_update_index"] = index
                merged["_pending_description_update_target"] = update_target
                merged["_description_update_prompt"] = f"What should I change the description to for {update_target}?"
                return merged

    has_client = bool(str(merged.get("client_name") or "").strip())
    client_name = None
    if not has_client:
        client_name = _extract_client_name_for_invoice(text)
    else:
        explicit_client_change = (
            "invoice for " in lowered
            or lowered.startswith("client is ")
            or lowered.startswith("customer is ")
            or lowered.startswith("change client to ")
            or lowered.startswith("for client ")
            or lowered.startswith("for customer ")
        )
        if explicit_client_change:
            client_name = _extract_client_name_for_invoice(text)
    if client_name:
        merged["client_name"] = client_name

    line_items = _extract_line_items_from_invoice_text(text)
    if line_items:
        merged.pop("_pending_line_item_amount", None)
        merged.pop("_awaiting_invoice_item_review", None)
        merged.pop("_awaiting_add_more_items_confirmation", None)
        existing = [item for item in (merged.get("line_items") or []) if isinstance(item, dict)]
        if existing and len(line_items) == 1:
            candidate = line_items[0]
            duplicate = next((
                item for item in existing
                if str(item.get("description") or "").strip().lower() == str(candidate.get("description") or "").strip().lower()
            ), None)
            if duplicate:
                duplicate.update(candidate)
                merged["line_items"] = existing
            else:
                merged["line_items"] = existing + line_items
        else:
            merged["line_items"] = line_items
        if len(line_items) == 1 and explicit_quantity is None and float(line_items[0].get("quantity", 1) or 1) == 1:
            merged["_awaiting_invoice_item_review"] = True
    else:
        amount_only = _extract_amount_value(text)
        if amount_only and any(token in lowered for token in ("amount", "rupees", "rs", "inr", "rate")):
            merged["_pending_line_item_amount"] = amount_only
            pending_description = str(merged.get("_pending_line_item_description") or "").strip()
            if pending_description:
                pending_fragment = _clean_invoice_item_followup_text(text)
                merged_description = _merge_invoice_description_fragments(
                    pending_description,
                    pending_fragment,
                ) if pending_fragment else pending_description
                existing = [item for item in (merged.get("line_items") or []) if isinstance(item, dict)]
                existing.append({
                    "description": merged_description,
                    "quantity": 1,
                    "unit_price": float(amount_only),
                    "gst_percent": 18,
                    "type": "SERVICE",
                })
                merged["line_items"] = existing
                merged.pop("_pending_line_item_amount", None)
                merged.pop("_pending_line_item_description", None)
                merged["_awaiting_invoice_item_review"] = True
        elif merged.get("_pending_line_item_amount") and lowered.startswith("for "):
            description = re.sub(r"^for\s+", "", raw_text, flags=re.I).strip(" .,-")
            if description:
                existing = [item for item in (merged.get("line_items") or []) if isinstance(item, dict)]
                existing.append({
                    "description": description,
                    "quantity": 1,
                    "unit_price": float(merged["_pending_line_item_amount"]),
                    "gst_percent": 18,
                    "type": "SERVICE",
                })
                merged["line_items"] = existing
                merged.pop("_pending_line_item_amount", None)
                merged["_awaiting_invoice_item_review"] = True

    service_description = _extract_invoice_service_description(text)
    amount_value = _extract_amount_value(text)
    if service_description and amount_value and any(token in lowered for token in ("amount", "cost", "price", "rupees", "rs", "inr", "rate")):
        existing = [item for item in (merged.get("line_items") or []) if isinstance(item, dict)]
        normalized_description = re.sub(
            r"\b(?:at|for|fall)\s+\d[\d,\s]*(?:\.\d+)?\s*(?:rupees?|rs|inr)?\b.*$",
            "",
            service_description.strip(),
            flags=re.I,
        ).strip(" .,-")
        normalized_description = _formalize_invoice_description(normalized_description)
        candidate_key = re.sub(r"\s+", " ", normalized_description.lower())
        duplicate = next((
            item for item in existing
            if re.sub(r"\s+", " ", str(item.get("description") or "").strip().lower()) == candidate_key
        ), None)
        payload = {
            "description": normalized_description,
            "quantity": 1,
            "unit_price": float(amount_value),
            "gst_percent": 18,
            "type": "SERVICE",
        }
        if duplicate:
            duplicate.update(payload)
        else:
            existing.append(payload)
        merged["line_items"] = existing
        merged.pop("_pending_line_item_amount", None)
        merged.pop("_awaiting_add_more_items_confirmation", None)
        merged["_awaiting_invoice_item_review"] = True
    elif service_description and merged.get("_pending_line_item_amount"):
        existing = [item for item in (merged.get("line_items") or []) if isinstance(item, dict)]
        existing.append({
            "description": service_description,
            "quantity": 1,
            "unit_price": float(merged["_pending_line_item_amount"]),
            "gst_percent": 18,
            "type": "SERVICE",
        })
        merged["line_items"] = existing
        merged.pop("_pending_line_item_amount", None)
        merged.pop("_awaiting_add_more_items_confirmation", None)
        merged["_awaiting_invoice_item_review"] = True
    elif service_description:
        merged["_pending_line_item_description"] = _formalize_invoice_description(service_description)

    due_date = _extract_due_date_phrase(text)
    if due_date:
        merged["due_date"] = due_date

    team_code = _extract_team_code(text)
    if team_code:
        merged["team_code"] = team_code

    return merged


async def _ensure_client_cache(session: AgentSession, org_context: dict, backend: Any) -> List[dict]:
    if session.client_cache:
        return [c for c in session.client_cache if isinstance(c, dict)]

    org_id = org_context.get("org_id") or session.org_uuid
    try:
        clients_r = await asyncio.wait_for(
            backend.get("/api/clients?limit=200", org_id=org_id, user_id=session.user_id),
            timeout=10.0,
        )
    except Exception:
        return []

    clients = clients_r if isinstance(clients_r, list) else []
    enriched = []
    for c in clients:
        if not isinstance(c, dict):
            continue
        enriched.append({
            "name": c.get("name") or "",
            "company": c.get("company") or c.get("companyName") or "",
            "email": c.get("email"),
            "phone": c.get("phone"),
            "id": c.get("id"),
        })
    session.client_cache = enriched
    return enriched


def _normalize_phrase_tokens(value: str) -> str:
    lowered = re.sub(r"[^a-z0-9\s]", " ", (value or "").lower())
    lowered = re.sub(r"\b(create|invoice|client|for|the|a|an|is|name|please|make|new)\b", " ", lowered)
    lowered = re.sub(r"\s+", " ", lowered).strip()
    return lowered


def _normalized_token_list(value: str) -> List[str]:
    return [token for token in _normalize_phrase_tokens(value).split() if token]


def _best_client_match(candidate: str, clients: List[dict]) -> Optional[dict]:
    norm_candidate = _normalize_phrase_tokens(candidate)
    if not norm_candidate or not clients:
        return None
    candidate_tokens = _normalized_token_list(candidate)
    if not candidate_tokens:
        return None

    scored: List[Tuple[float, dict]] = []
    for client in clients:
        name = str(client.get("name") or "").strip()
        company = str(client.get("company") or "").strip()
        haystacks = [name, company, f"{name} {company}".strip()]
        best = 0.0
        for haystack in haystacks:
            norm_hay = _normalize_phrase_tokens(haystack)
            if not norm_hay:
                continue
            ratio = difflib.SequenceMatcher(None, norm_candidate, norm_hay).ratio()
            if norm_candidate in norm_hay or norm_hay in norm_candidate:
                ratio = max(ratio, 0.93)

            hay_tokens = _normalized_token_list(haystack)
            if hay_tokens:
                token_scores = []
                for candidate_token in candidate_tokens:
                    best_token = max(
                        difflib.SequenceMatcher(None, candidate_token, hay_token).ratio()
                        for hay_token in hay_tokens
                    )
                    token_scores.append(best_token)

                token_avg = sum(token_scores) / len(token_scores)
                ratio = max(ratio, token_avg * 0.96)

                # Strong first-name preference for spoken client selection.
                first_token_score = difflib.SequenceMatcher(None, candidate_tokens[0], hay_tokens[0]).ratio()
                if candidate_tokens[0] == hay_tokens[0]:
                    ratio = max(ratio, 0.97)
                elif len(candidate_tokens) == 1 and len(candidate_tokens[0]) >= 4 and first_token_score >= 0.84:
                    ratio = max(ratio, 0.9)
                elif first_token_score >= 0.9:
                    ratio = max(ratio, 0.92)
            best = max(best, ratio)
        if best >= 0.72:
            scored.append((best, client))

    if not scored:
        return None
    scored.sort(key=lambda item: item[0], reverse=True)
    if len(scored) > 1 and scored[0][0] - scored[1][0] < 0.04:
        return None
    return scored[0][1]


async def _semantically_enrich_drafts(
    text: str,
    session: AgentSession,
    org_context: dict,
    backend: Any,
) -> None:
    if session.pending_invoice and not session.pending_invoice.get("client_name"):
        candidate = _extract_client_name_for_invoice(text) or _clean_name_phrase(text)
        if not candidate:
            return
        clients = await _ensure_client_cache(session, org_context, backend)
        match = _best_client_match(candidate, clients)
        if match:
            session.pending_invoice["client_name"] = match.get("name") or match.get("company") or candidate
            if match.get("name"):
                session.last_client_mentioned = match["name"]


def _is_highest_unpaid_client_query(text: str) -> bool:
    lowered = (text or "").lower()
    return any(phrase in lowered for phrase in (
        "highest unpaid",
        "largest unpaid",
        "highest outstanding",
        "most unpaid",
    ))


def _synthesize_market_result(tool_result: dict) -> Optional[str]:
    if not isinstance(tool_result, dict):
        return None

    query = str(tool_result.get("query") or "").strip()
    focus = str(tool_result.get("focus") or "trends").strip().lower()
    activity = str(tool_result.get("activity") or "this business").strip()
    business_name = str(tool_result.get("business_name") or "the business").strip()
    city = str(tool_result.get("city") or "your market").strip()
    fallback = (tool_result.get("fallback_text") or "").strip()
    snippets = [s.strip() for s in tool_result.get("raw_snippets", []) if isinstance(s, str) and s.strip()]
    if fallback:
        return fallback
    if not snippets:
        return None
    corpus = " ".join(snippets).lower()

    demand_signal = "commercial and institutional EV charging demand is still the best pocket to pursue"
    if any(token in corpus for token in ("fleet", "logistics", "depot", "warehouse")):
        demand_signal = "fleet depots, logistics operators, and warehouse campuses are the strongest near-term demand pocket"
    elif any(token in corpus for token in ("hotel", "hospitality", "mall", "retail", "real estate", "developer")):
        demand_signal = "hospitality, retail, and real-estate operators are the clearest near-term expansion accounts"
    elif any(token in corpus for token in ("government", "tender", "municipal", "public sector")):
        demand_signal = "public-sector and tender-led demand is opening, but it needs tighter bid discipline and slower cash assumptions"

    pressure_signal = "margin will slip if projects stay too custom and collections stay loose"
    if any(token in corpus for token in ("price war", "discount", "competition", "competitor")):
        pressure_signal = "competitive pricing pressure is rising, so margin will slip if you respond with blanket discounting"
    elif any(token in corpus for token in ("policy", "regulation", "compliance", "approval")):
        pressure_signal = "execution risk is higher around approvals and compliance, so timelines and cash flow need tighter control"
    elif any(token in corpus for token in ("import", "supply chain", "component", "hardware")):
        pressure_signal = "hardware and supply timing can hit delivery dates, so procurement discipline matters more right now"

    action_one = "prioritize the two buyer segments already moving and push a standard package instead of open-ended custom quotes"
    action_two = "attach AMC, monitoring, and electrical upgrade scope early so each win carries better margin and more recurring revenue"
    action_three = "review every live deal for collection terms, approval dependencies, and hardware lead times before you push volume"

    lowered_query = query.lower()
    if focus == "risks" or any(token in lowered_query for token in ("risk", "loss", "downside", "protect margin", "avoid")):
        action_one = "freeze low-margin quoting, tighten approval gates, and escalate only the accounts with clean payment terms and faster close potential"
        action_two = "move every at-risk project into a weekly exception review covering collections, procurement gaps, and approval blockers"
        action_three = "protect cash by collecting advance payments, reducing custom scope creep, and delaying inventory commitments until orders are firm"
    elif focus == "competitors" or "competitor" in lowered_query:
        action_one = "win on speed, project packaging, and maintenance coverage instead of trying to beat every competitor on headline price"
        action_two = "arm the sales team with vertical-specific offers for fleets, hospitality, and multi-site operators so proposals feel easier to approve"
        action_three = "track lost deals weekly and escalate only the objections that repeatedly block close, especially price, approvals, and uptime commitments"
    elif any(token in lowered_query for token in ("scale", "grow", "opportunity", "update", "trend")):
        action_one = "concentrate outbound and partnerships around the accounts where demand is already active, especially in and around " + city
        action_two = "standardize rollout, electrical upgrade, and AMC bundles so delivery stays repeatable as volume increases"
        action_three = "escalate larger multi-site and fleet accounts early to leadership so pricing, execution capacity, and collections are aligned before the deal moves"

    return (
        f"For {business_name}, the signal right now is that {demand_signal}. "
        f"The main caution is that {pressure_signal}. "
        f"To act on this, first {action_one}. "
        f"Second, {action_two}. "
        f"Third, {action_three}."
    )


def _market_scale_guidance(
    session: AgentSession,
    org_context: Dict[str, Any],
    tool_result: Optional[dict] = None,
) -> str:
    business = org_context.get("business", {}) if isinstance(org_context, dict) else {}
    activity = str(business.get("primaryActivity") or business.get("industry") or "this business").strip()
    city = str(business.get("city") or business.get("state") or business.get("country") or "").strip()

    snippets: List[str] = []
    if isinstance(tool_result, dict):
        snippets.extend([s.strip() for s in tool_result.get("raw_snippets", []) if isinstance(s, str) and s.strip()])
        fallback = str(tool_result.get("fallback_text") or "").strip()
        if fallback:
            snippets.append(fallback)
    if session.last_market_results:
        snippets.extend([s.strip() for s in session.last_market_results if isinstance(s, str) and s.strip()])

    corpus = " ".join(snippets).lower()
    location_hint = city or "the markets where you already have traction"
    demand_hint = "the customer segments showing the clearest demand signals"
    if any(token in corpus for token in ("enterprise", "corporate", "b2b", "commercial")):
        demand_hint = "enterprise and commercial buyers already increasing spend"
    elif any(token in corpus for token in ("institution", "government", "public sector", "tender")):
        demand_hint = "institutional and public-sector demand that is already opening up"

    offer_hint = "a more standardized offer with repeatable delivery"
    if any(token in corpus for token in ("maintenance", "amc", "subscription", "recurring", "service contract")):
        offer_hint = "bundled delivery plus recurring service contracts"
    elif any(token in corpus for token in ("implementation", "deployment", "rollout", "multi-site")):
        offer_hint = "repeatable rollout packages for larger accounts"

    channel_hint = "channel partners and referral sources that can bring repeat business"
    if any(token in corpus for token in ("developer", "operator", "aggregator", "epc", "reseller", "partner")):
        channel_hint = "the partner channels already active in this market"

    return (
        f"To scale {activity}, first concentrate on {demand_hint} in {location_hint}, where the market is already moving. "
        f"Second, package {offer_hint} so every new win is easier to deliver and more profitable to repeat. "
        f"Third, build a monthly pipeline around larger accounts, repeatable use cases, and faster-closing opportunities instead of scattered one-off work. "
        f"Fourth, strengthen {channel_hint} so lead flow grows without depending only on direct outbound."
    )


def _market_search_fallback(
    query: str,
    focus: str,
    business: Dict[str, Any],
) -> str:
    industry = str(business.get("industry") or "your industry").strip()
    activity = str(business.get("primaryActivity") or industry or "your core offering").strip()
    city = str(business.get("city") or business.get("state") or business.get("country") or "your market").strip()
    biz_name = str(business.get("legalName") or "your business").strip()
    lowered = f"{query} {industry} {activity} {focus}".lower()

    buyer_hint = "the buyer segments already showing active demand"
    if any(token in lowered for token in ("b2b", "enterprise", "commercial", "corporate")):
        buyer_hint = "enterprise and commercial buyers with active budgets"
    elif any(token in lowered for token in ("consumer", "retail", "d2c", "ecommerce")):
        buyer_hint = "high-intent customer segments with faster purchase cycles"
    elif any(token in lowered for token in ("institution", "government", "school", "hospital", "public")):
        buyer_hint = "institutional buyers and public-sector opportunities opening this quarter"

    offer_hint = "a repeatable offer that is easier to sell and deliver"
    if any(token in lowered for token in ("service", "maintenance", "support", "subscription", "amc", "saas")):
        offer_hint = "recurring service and support offers that increase lifetime value"
    elif any(token in lowered for token in ("project", "implementation", "installation", "deployment")):
        offer_hint = "standardized project packages that shorten the sales cycle"
    elif any(token in lowered for token in ("product", "manufacturing", "retail", "inventory")):
        offer_hint = "best-selling product lines and higher-margin bundles"

    route_hint = "channel and partnership routes that can scale faster than pure outbound"
    if any(token in lowered for token in ("partner", "reseller", "aggregator", "distributor", "marketplace")):
        route_hint = "partner-led and channel-led acquisition routes"
    elif any(token in lowered for token in ("local", city.lower())):
        route_hint = f"local partnerships and account expansion inside {city}"

    urgency_hint = "This month, the strongest move is to concentrate pipeline on the clearest demand pockets instead of spreading effort thin."
    if focus == "opportunities":
        urgency_hint = "This month, the strongest move is to focus on the most active demand pockets and offers that can close quickly."
    elif focus == "risks":
        urgency_hint = "This month, the strongest move is to protect margin and reduce dependence on slower-moving segments."
    elif focus == "competitors":
        urgency_hint = "This month, the strongest move is to differentiate on speed, packaging, and account coverage."

    return (
        f"Based on current signals for {biz_name} in {city}, demand is strongest where {buyer_hint}. "
        f"{urgency_hint} "
        f"For {activity}, the best growth move is to push {offer_hint} and build around {route_hint}. "
        f"That gives you a clearer path to scale without depending on one-off wins."
    )


def _synthesize_market_scale_followup(
    tool_result: dict,
    session: AgentSession,
    org_context: Dict[str, Any],
) -> Optional[str]:
    return _market_scale_guidance(session, org_context, tool_result)


def _market_action_guidance(
    text: str,
    session: AgentSession,
    org_context: Dict[str, Any],
    tool_result: Optional[dict] = None,
) -> str:
    business = org_context.get("business", {}) if isinstance(org_context, dict) else {}
    activity = str(business.get("primaryActivity") or business.get("industry") or "this business").strip()
    city = str(business.get("city") or business.get("state") or business.get("country") or "your core market").strip()

    snippets: List[str] = []
    if isinstance(tool_result, dict):
        snippets.extend([s.strip() for s in tool_result.get("raw_snippets", []) if isinstance(s, str) and s.strip()])
        fallback = str(tool_result.get("fallback_text") or "").strip()
        if fallback:
            snippets.append(fallback)
    if session.last_market_results:
        snippets.extend([s.strip() for s in session.last_market_results if isinstance(s, str) and s.strip()])

    corpus = " ".join(snippets).lower()
    lowered = (text or "").lower()

    buyer_focus = "multi-site commercial accounts and institutional buyers already budgeting for charging infrastructure"
    if any(token in corpus for token in ("fleet", "logistics", "warehouse", "depot")):
        buyer_focus = "fleet depots, logistics operators, and warehouse sites that need faster charger deployment"
    elif any(token in corpus for token in ("hotel", "hospitality", "retail", "mall")):
        buyer_focus = "hospitality and retail accounts where charger deployment can support footfall and guest experience"

    if any(token in lowered for token in ("avoid financial loss", "avoid losses", "mitigate", "protect margin", "risk", "downside")):
        return (
            f"To protect {activity} from financial loss, start by reviewing every live deal in {city} for three things: payment terms, approval risk, and hardware lead-time exposure. "
            f"Escalate any job with weak advance payment, stretched credit, or custom scope into a weekly exception review before it reaches procurement. "
            f"Hold margin by standardizing scope, limiting discounting to high-probability accounts, and attaching AMC or monitoring revenue wherever possible. "
            f"If a project still shows slow collections or execution risk after that review, slow it down instead of pushing volume into low-quality revenue."
        )

    if any(token in lowered for token in ("escalate", "escalation plan", "respond")):
        return (
            f"The right escalation path is simple. "
            f"First, move the opportunity or risk into a leadership review as soon as it affects pricing, delivery capacity, or collections. "
            f"Second, assign one owner for commercial closure, one for technical delivery, and one for payment follow-through so decisions do not get stuck between teams. "
            f"Third, escalate only when the account is strategically important, margin-positive, and realistically collectible, especially among {buyer_focus}. "
            f"If any of those conditions fail, de-prioritize the deal and protect cash."
        )

    return (
        f"To capture the upside here, focus first on {buyer_focus}. "
        f"Package the offer so it is easy to approve: charger deployment, electrical readiness, and AMC in one commercial story. "
        f"Then escalate the best accounts early when they are large, multi-site, or likely to expand, so pricing, project capacity, and collection terms stay aligned. "
        f"That is how you get the best out of the opportunity without letting execution risk erode margin."
    )


def _grounded_growth_plan(session: AgentSession, org_context: Dict[str, Any]) -> Optional[str]:
    business = org_context.get("business", {}) if isinstance(org_context, dict) else {}
    snap = session.business_snapshot or {}
    if not snap:
        return None

    revenue = float(snap.get("revenue", 0) or 0)
    expenses = float(snap.get("expenses", 0) or 0)
    net_profit = float(snap.get("netProfit", 0) or 0)
    outstanding = float(snap.get("outstanding", 0) or 0)
    client_count = int(snap.get("clientCount", 0) or 0)
    margin = (net_profit / revenue * 100) if revenue > 0 else 0.0

    top_client_line = ""
    concentration_line = ""
    clients = [client for client in (session.last_client_results or []) if isinstance(client, dict)]
    if clients:
        ranked = sorted(clients, key=lambda item: float(item.get("total_revenue_inr", 0) or 0), reverse=True)
        top = ranked[0]
        top_name = str(top.get("name") or "your top client").strip()
        top_revenue = float(top.get("total_revenue_inr", 0) or 0)
        share = (top_revenue / revenue * 100) if revenue > 0 else 0.0
        top_client_line = (
            f"Your strongest account today is {top_name} at about {_inr_words(top_revenue)} rupees of billed revenue."
        )
        if share >= 35:
            concentration_line = (
                f"That also means client concentration is high at roughly {round(share)} percent, "
                "so the next revenue move should be winning two or three more accounts in the same buying profile."
            )

    activity = str(
        business.get("primaryActivity")
        or business.get("industry")
        or "your core business"
    ).strip()
    city = str(business.get("city") or "your current market").strip()

    margin_line = (
        f"Your current margin is about {round(margin)} percent on revenue of {_inr_words(revenue)} rupees."
        if revenue > 0
        else "Revenue is still too thin to scale safely, so the next move should be tightening your offer and closing faster."
    )

    collections_line = (
        "Collections are under control right now, so you can push growth without cash being locked in receivables."
        if outstanding <= 0
        else f"You still have {_inr_words(outstanding)} rupees tied up in receivables, so collect that before pushing hard on volume."
    )

    if margin < 20:
        offer_line = (
            f"For {activity}, scale by standardizing proposals, limiting custom scope, and attaching AMC or service revenue to every installation in {city}."
        )
    else:
        offer_line = (
            f"For {activity}, the best growth move now is to package installation, electrical readiness, and annual maintenance as one repeatable commercial offer in {city}."
        )

    pipeline_line = (
        "This month, prioritize multi-site commercial buyers, repeat business from your strongest client profile, and channel partners who can bring recurring deployments."
    )

    team_line = (
        "If you want more income, do not chase every lead equally. Put weekly focus on faster-closing deals, larger ticket sizes, and repeatable rollout work."
    )

    parts = [margin_line, collections_line, top_client_line, concentration_line, offer_line, pipeline_line, team_line]
    return " ".join(part for part in parts if part)


async def _create_groq_clients(api_keys: List[str]) -> Dict[str, AsyncGroq]:
    clients: Dict[str, AsyncGroq] = {}
    for api_key in api_keys:
        clients[api_key] = AsyncGroq(
            api_key=api_key,
            max_retries=0,
            http_client=httpx.AsyncClient(timeout=httpx.Timeout(12.0, connect=4.0), trust_env=False),
        )
    return clients


async def _close_groq_clients(clients: Dict[str, AsyncGroq]) -> None:
    for client in clients.values():
        http_client = getattr(client, "_client", None)
        if http_client is not None:
            try:
                await http_client.aclose()
            except Exception:
                pass


async def _call_groq_with_failover(
    clients: Dict[str, AsyncGroq],
    api_keys: List[str],
    timeout_seconds: float,
    **kwargs: Any,
):
    last_error: Optional[Exception] = None
    for api_key in _ordered_groq_keys(api_keys):
        client = clients[api_key]
        try:
            return await asyncio.wait_for(
                client.chat.completions.create(**kwargs),
                timeout=timeout_seconds,
            )
        except Exception as exc:
            _mark_groq_key_backoff(api_key, exc)
            last_error = exc
            logger.warning({"event": "groq_failover_attempt_failed", "error": str(exc)})
            continue

    if last_error:
        raise last_error
    raise RuntimeError("No Groq API keys configured")


# ════════════════════════════════════════════════════════════════════════════════
# TOOL EXECUTORS
# ════════════════════════════════════════════════════════════════════════════════

async def execute_tool(name: str, args_json: str, session: AgentSession, org_context: dict, backend: Any) -> dict:
    """Execute tool call with complete data pipeline."""
    try:
        args = json.loads(args_json) if args_json else {}
    except Exception:
        args = {}
    if not isinstance(args, dict):
        args = {}

    for numeric_key in ("limit", "days_ahead", "amount", "amount_received", "quantity", "unit_price", "gst_percent"):
        if numeric_key in args and isinstance(args[numeric_key], str):
            raw_value = args[numeric_key].strip()
            try:
                args[numeric_key] = int(raw_value) if raw_value.isdigit() else float(raw_value)
            except ValueError:
                pass

    today = date.today()
    today_str = today.isoformat()
    org_id = session.org_uuid
    business_id = session.business_id or "1"

    logger.info({"event": "tool_execute", "tool": name, "session": session.session_id})

    try:
        cacheable_reads = {
            "get_financial_summary",
            "get_invoices",
            "get_clients",
            "check_compliance",
            "get_business_health_score",
            "get_cash_flow_forecast",
            "get_overdue_action_plan",
            "get_daily_briefing",
        }
        if name in cacheable_reads:
            cached = _get_cached_read_tool(org_id, business_id, name, args)
            if cached is not None:
                return cached

        if name == "get_financial_summary":
            result = await asyncio.wait_for(
                backend.get(
                    f"/api/finance-intelligence/metrics?businessId={business_id}",
                    org_id=org_id,
                    user_id=session.user_id,
                ),
                timeout=10.0
            )
            d = result if isinstance(result, dict) else {}
            revenue = float(d.get("revenue", 0))
            expenses = float(d.get("expenses", 0))
            net = float(d.get("netProfit", revenue - expenses))
            total_inv = float(d.get("totalInvoiced", 0))
            collected = float(d.get("collected", 0))
            outstanding = float(d.get("outstanding", total_inv - collected))
            overdue_amt = float(d.get("overdueAmount", 0))
            overdue_count = int(d.get("overdueCount", 0))
            margin = round((net / revenue * 100), 1) if revenue > 0 else 0

            session.business_snapshot = {
                "revenue": revenue, "expenses": expenses, "netProfit": net,
                "outstanding": outstanding, "overdueAmount": overdue_amt,
                "overdueCount": overdue_count, "clientCount": d.get("clientCount", 0)
            }

            response = {
                "status": "ok",
                "revenue_inr": revenue,
                "expenses_inr": expenses,
                "net_profit_inr": net,
                "margin_percent": margin,
                "total_invoiced_inr": total_inv,
                "collected_inr": collected,
                "outstanding_inr": outstanding,
                "overdue_amount_inr": overdue_amt,
                "overdue_count": overdue_count,
                "burn_per_day_inr": round(expenses / 30) if expenses > 0 else 0,
                "collection_rate_percent": round(collected / total_inv * 100, 1) if total_inv > 0 else 0,
                "note": "All amounts INR"
            }
            _set_cached_read_tool(org_id, business_id, name, args, response)
            return response

        elif name == "get_invoices":
            status = args.get("status", "all")
            params = "?limit=100"
            if status and status != "all":
                params += f"&status={status}"

            result = await asyncio.wait_for(
                backend.get(f"/api/invoices{params}", org_id=org_id, user_id=session.user_id),
                timeout=10.0,
            )
            invoices = [inv for inv in result if isinstance(inv, dict)] if isinstance(result, list) else []

            # Also try the dedicated overdue endpoint if status is OVERDUE
            if status == "OVERDUE" or status == "all":
                try:
                    overdue_result = await asyncio.wait_for(
                        backend.get("/api/invoices/overdue", org_id=org_id, user_id=session.user_id), timeout=8.0
                    )
                    if isinstance(overdue_result, list) and overdue_result:
                        # Merge, deduplicate by ID
                        existing_ids = {inv.get("id") for inv in invoices}
                        for inv in overdue_result:
                            if not isinstance(inv, dict):
                                continue
                            if inv.get("id") not in existing_ids:
                                invoices.append(inv)
                except Exception:
                    pass

            client_filter = (args.get("client_name") or "").lower()
            if client_filter:
                invoices = [i for i in invoices if client_filter in (i.get("clientName") or "").lower()]

            # Enrich with computed fields
            enriched = []
            for inv in invoices[:50]:
                amount = float(inv.get("totalAmount", 0))
                raw_status = str(inv.get("status") or "").upper()
                paid = float(inv.get("paidAmount", 0) or 0)
                if raw_status == "PAID" and amount > 0 and paid <= 0:
                    paid = amount
                paid = min(amount, paid)
                remaining = max(0.0, amount - paid)
                due = inv.get("dueDate", "")
                days_overdue = 0
                if due:
                    try:
                        due_date_obj = date.fromisoformat(due[:10])
                        days_overdue = max(0, (today - due_date_obj).days)
                    except Exception:
                        pass

                # TDS check
                client_name = inv.get("clientName", "")
                is_tds = any(d in client_name.lower() for d in TDS_DEDUCTOR_HINTS)
                expected_tds = amount * 0.10
                tds_gap = is_tds and abs(remaining - expected_tds) < max(500, amount * 0.005)

                enriched.append({
                    "id": inv.get("id"),
                    "invoice_number": inv.get("invoiceNumber"),
                    "client": client_name,
                    "amount_inr": amount,
                    "paid_inr": paid,
                    "outstanding_inr": remaining,
                    "status": raw_status,
                    "due_date": due[:10] if due else "",
                    "days_overdue": days_overdue,
                    "is_tds_gap": tds_gap,
                    "tds_note": "TDS deduction — Form 26AS credit, not a shortfall" if tds_gap else None
                })

            paid_invoices = [i for i in enriched if i["status"] == "PAID"]
            overdue_invoices = [
                i for i in enriched
                if i["status"] == "OVERDUE" or (
                    i["outstanding_inr"] > 0 and
                    i["status"] not in ("PAID", "CANCELLED") and
                    i["days_overdue"] > 0 and
                    not i["is_tds_gap"]
                )
            ]
            total_outstanding = sum(i["outstanding_inr"] for i in enriched if i["status"] not in ("PAID", "CANCELLED"))
            total_paid = sum(i["paid_inr"] for i in paid_invoices)

            # Track context
            if enriched:
                session.last_invoice_mentioned = enriched[0].get("invoice_number")
                if enriched[0].get("client"):
                    session.last_client_mentioned = enriched[0]["client"]
            session.last_invoice_results = enriched[:20]

            response = {
                "status": "ok",
                "total_count": len(enriched),
                "paid_count": len(paid_invoices),
                "overdue_count": len(overdue_invoices),
                "total_paid_inr": total_paid,
                "total_outstanding_inr": total_outstanding,
                "invoices": enriched[:20],
                "paid_invoices": paid_invoices[:10],
                "overdue_invoices": overdue_invoices[:10],
                "note": "All amounts INR. TDS gaps excluded from overdue count."
            }
            _set_cached_read_tool(org_id, business_id, name, args, response)
            return response

        elif name == "get_clients":
            sort_by = args.get("sort_by", "revenue")

            clients_r, invoices_r = await asyncio.gather(
                asyncio.wait_for(backend.get("/api/clients?limit=200", org_id=org_id, user_id=session.user_id), timeout=10.0),
                asyncio.wait_for(backend.get("/api/invoices?limit=200", org_id=org_id, user_id=session.user_id), timeout=10.0),
                return_exceptions=True
            )

            clients = [c for c in clients_r if isinstance(c, dict)] if isinstance(clients_r, list) else []
            invoices = [i for i in invoices_r if isinstance(i, dict)] if isinstance(invoices_r, list) else []

            # Build revenue map per client
            client_rev = {}
            client_meta = {}
            for inv in invoices:
                cn = inv.get("clientName", "")
                if not cn:
                    continue
                if cn not in client_rev:
                    client_rev[cn] = {"total": 0, "outstanding": 0, "overdue": 0, "count": 0}
                if cn not in client_meta:
                    client_meta[cn] = {
                        "company": inv.get("clientCompany", "") or "",
                        "email": inv.get("clientEmail", "") or "",
                        "phone": inv.get("clientPhone", "") or "",
                        "city": inv.get("city", "") or "",
                        "gstin": inv.get("gstin", "") or "",
                        "newest_marker": inv.get("issueDate") or "",
                    }
                amount = float(inv.get("totalAmount", 0))
                paid = float(inv.get("paidAmount", 0))
                client_rev[cn]["total"] += amount
                client_rev[cn]["outstanding"] += (amount - paid)
                client_rev[cn]["count"] += 1
                if inv.get("status") == "OVERDUE":
                    client_rev[cn]["overdue"] += (amount - paid)
                issue_date = str(inv.get("issueDate") or "")
                if issue_date and issue_date > str(client_meta[cn].get("newest_marker") or ""):
                    client_meta[cn]["newest_marker"] = issue_date

            enriched = []
            for c in clients:
                cn = c.get("name", "")
                rev = client_rev.get(cn, {})
                enriched.append({
                    "id": c.get("id"),
                    "name": cn,
                    "company": c.get("company") or c.get("companyName", ""),
                    "email": c.get("email"),
                    "phone": c.get("phone"),
                    "city": c.get("city", ""),
                    "gstin": c.get("gstin"),
                    "total_revenue_inr": rev.get("total", 0),
                    "outstanding_inr": rev.get("outstanding", 0),
                    "overdue_inr": rev.get("overdue", 0),
                    "invoice_count": rev.get("count", 0),
                    "payment_health": "excellent" if rev.get("overdue", 0) == 0 else "fair" if rev.get("overdue", 0) < rev.get("total", 1) * 0.2 else "poor"
                })

            # Fallback: derive client records from invoices when client master data is empty or incomplete.
            existing_names = {str(client.get("name") or "").strip().lower() for client in enriched}
            for cn, rev in client_rev.items():
                if cn.strip().lower() in existing_names:
                    continue
                meta = client_meta.get(cn, {})
                enriched.append({
                    "id": meta.get("newest_marker") or cn,
                    "name": cn,
                    "company": meta.get("company", ""),
                    "email": meta.get("email", ""),
                    "phone": meta.get("phone", ""),
                    "city": meta.get("city", ""),
                    "gstin": meta.get("gstin", ""),
                    "total_revenue_inr": rev.get("total", 0),
                    "outstanding_inr": rev.get("outstanding", 0),
                    "overdue_inr": rev.get("overdue", 0),
                    "invoice_count": rev.get("count", 0),
                    "payment_health": "excellent" if rev.get("overdue", 0) == 0 else "fair" if rev.get("overdue", 0) < rev.get("total", 1) * 0.2 else "poor",
                    "newest_marker": meta.get("newest_marker", ""),
                })

            sort_key = "total_revenue_inr"
            if sort_by == "outstanding":
                sort_key = "outstanding_inr"
            elif sort_by == "overdue":
                sort_key = "overdue_inr"
            elif sort_by == "newest":
                sort_key = "newest_marker"
            enriched.sort(key=lambda c: c.get(sort_key, 0) or 0, reverse=True)
            total_revenue = sum(c["total_revenue_inr"] for c in enriched)

            session.client_cache = enriched
            session.last_client_results = enriched[:15]

            response = {
                "status": "ok",
                "total_clients": len(enriched),
                "total_revenue_inr": total_revenue,
                "clients": enriched[:15],
                "note": f"Sorted by {sort_by}. All amounts INR."
            }
            _set_cached_read_tool(org_id, business_id, name, args, response)
            return response

        elif name == "create_client":
            name_val = (args.get("name") or "").strip()
            company_name = (args.get("company_name") or "").strip()
            bad = {"client", "a client", "new client", "test", "unknown", ""}
            if not name_val or name_val.lower() in bad:
                prompt = (
                    f"Who is the main contact person at {company_name}?"
                    if company_name
                    else "What is the client's actual name?"
                )
                return {"status": "validation_error", "missing_field": "name", "message": prompt}

            if not company_name:
                return {
                    "status": "validation_error",
                    "missing_field": "company_name",
                    "message": f"What company does {name_val} work at?",
                }

            if not args.get("email"):
                if args.get("_email_fragment"):
                    return {
                        "status": "validation_error",
                        "missing_field": "email",
                        "message": (
                            f"I still need {name_val}'s email in one complete format. "
                            "Please say it like accounts at company dot com."
                        ),
                    }
                return {"status": "validation_error", "missing_field": "email",
                        "message": f"What is {name_val}'s email address?"}

            if not args.get("phone"):
                return {"status": "validation_error", "missing_field": "phone",
                        "message": f"What is {name_val}'s phone number?"}

            team_code = _normalize_team_code_value(args.get("team_code") or session.verified_team_code)
            if not team_code:
                return {"status": "validation_error", "missing_field": "team_code",
                        "message": "What is your team security code?"}

            payload = {
                "name": name_val,
                "email": args["email"],
                "phone": args["phone"],
                "phoneNumber": args["phone"],
                "company": company_name or name_val,
                "gstin": args.get("gstin"),
                "notes": args.get("notes"),
                "paymentTerms": args.get("credit_limit_days", 30),
                "teamActionCode": team_code,
                "source": "VOICE",
                "orgId": org_id,
            }

            try:
                result = await asyncio.wait_for(
                    backend.post("/api/clients", payload=payload,
                                 headers={"X-Team-Code": team_code, "X-Org-Id": org_id},
                                 org_id=org_id, user_id=session.user_id),
                    timeout=10.0
                )
            except RuntimeError as exc:
                error_message = str(exc).strip()
                if "Team security code is required" in error_message:
                    return {
                        "status": "validation_error",
                        "missing_field": "team_code",
                        "message": "What is your team security code?",
                    }
                if "Invalid team security code" in error_message:
                    return {
                        "status": "validation_error",
                        "missing_field": "team_code",
                        "message": "That team security code was incorrect. Please say it again.",
                    }
                if "Due date cannot be before issue date" in error_message:
                    return {
                        "status": "validation_error",
                        "missing_field": "due_date",
                        "message": (
                            f"The due date cannot be before the issue date. "
                            f"Please give a date on or after {today.isoformat()}."
                        ),
                    }
                raise

            if isinstance(result, dict) and result.get("success") is False:
                return {"status": "error", "message": result.get("message", "Failed to create client")}

            session.pending_client = None
            session.verified_team_code = _normalize_team_code_value(team_code)
            session.last_client_mentioned = name_val
            _clear_org_cache(org_id)

            return {
                "status": "created",
                "id": result.get("id") if isinstance(result, dict) else None,
                "name": name_val,
                "company": company_name or name_val,
                "speech": (
                    f"{name_val} from {company_name} has been added as a new client."
                    if company_name
                    else f"{name_val} has been added as a new client."
                )
            }

        elif name == "create_invoice":
            from datetime import timedelta
            client_name = (args.get("client_name") or "").strip()
            requested_client_id = str(args.get("client_id") or "").strip()
            line_items = args.get("line_items", [])
            raw_due = args.get("due_date", "")
            provided_team_code = args.get("team_code")
            team_code = _normalize_team_code_value(provided_team_code or session.verified_team_code)

            if not client_name:
                return {"status": "validation_error", "missing_field": "client_name",
                        "message": "Which client is this invoice for?"}
            if not line_items:
                return {"status": "validation_error", "missing_field": "line_items",
                        "message": f"What services are you billing {client_name} for, and at what amount?"}
            if not raw_due:
                return {"status": "validation_error", "missing_field": "due_date",
                        "message": "What is the payment due date?"}
            if not team_code:
                return {"status": "validation_error", "missing_field": "team_code",
                        "message": "What is your team security code?"}

            clients = await _ensure_client_cache(session, org_context, backend)
            matched_client = None
            if requested_client_id:
                matched_client = next(
                    (
                        client for client in clients
                        if str(client.get("id") or "").strip() == requested_client_id
                    ),
                    None,
                )
            if matched_client is None:
                matched_client = _best_client_match(client_name, clients)
            client_id = str((matched_client or {}).get("id") or "").strip()
            resolved_client_name = str((matched_client or {}).get("name") or client_name).strip()
            if matched_client and matched_client.get("name"):
                client_name = resolved_client_name

            if not client_id:
                return {
                    "status": "validation_error",
                    "missing_field": "client_name",
                    "message": "I need you to pick an existing client before I can create this invoice.",
                }

            # Resolve due date
            due_str = raw_due
            if "net30" in raw_due.lower() or "30 day" in raw_due.lower():
                due_str = (today + timedelta(days=30)).isoformat()
            elif "net15" in raw_due.lower() or "15 day" in raw_due.lower():
                due_str = (today + timedelta(days=15)).isoformat()
            elif "net45" in raw_due.lower() or "45 day" in raw_due.lower():
                due_str = (today + timedelta(days=45)).isoformat()

            # Process line items
            cleaned_items = []
            total = 0
            for item in line_items:
                explicit_type = str(item.get("type") or "").strip().upper()
                qty = float(item.get("quantity", 1) or 1)
                price = float(item.get("unit_price", 0))
                if qty > 10000 and abs(qty - price) < 1:
                    qty = 1.0
                if price <= 0:
                    continue
                desc = item.get("description", "Service")
                gst_pct = float(item.get("gst_percent", 18))
                subtotal = qty * price
                gst_amount = subtotal * (gst_pct / 100)
                item_total = subtotal + gst_amount
                total += item_total
                item_type = explicit_type if explicit_type in {"SERVICE", "PRODUCT"} else ("SERVICE" if qty <= 1 else "PRODUCT")
                cleaned_items.append({
                    "type": item_type,
                    "description": desc,
                    "quantity": None if item_type == "SERVICE" else qty,
                    "rate": round(price, 2),
                    "gstPercent": round(gst_pct, 2),
                })

            payload = {
                "clientId": client_id,
                "clientName": client_name,
                "issueDate": today.isoformat(),
                "dueDate": due_str,
                "items": cleaned_items,
                "notes": args.get("notes", ""),
                "teamActionCode": team_code,
                "source": "VOICE",
                "status": "DRAFT",
                "orgId": org_id
            }

            try:
                result = await asyncio.wait_for(
                    backend.post("/api/invoices", payload=payload,
                                 headers={"X-Team-Code": team_code, "X-Org-Id": org_id},
                                 org_id=org_id, user_id=session.user_id),
                    timeout=10.0
                )
            except RuntimeError as exc:
                error_message = str(exc).strip()
                if "Team security code is required" in error_message:
                    return {
                        "status": "validation_error",
                        "missing_field": "team_code",
                        "message": "What is your team security code?",
                    }
                if "Invalid team security code" in error_message:
                    return {
                        "status": "validation_error",
                        "missing_field": "team_code",
                        "message": "That team security code was incorrect. Please say it again.",
                    }
                raise

            if isinstance(result, dict) and result.get("success") is False:
                return {"status": "error", "message": result.get("message", "Failed to create invoice")}

            session.pending_invoice = None
            session.verified_team_code = _normalize_team_code_value(team_code)
            _clear_org_cache(org_id)
            inv_data = result.get("data", result) if isinstance(result, dict) else {}
            invoice_id = inv_data.get("id")
            inv_num = inv_data.get("invoiceNumber", "INV-NEW")
            session.last_invoice_mentioned = inv_num
            session.last_client_mentioned = client_name
            session.last_response_context = json.dumps({
                "type": "invoice_send_offer",
                "client_name": client_name,
                "invoice_number": inv_num,
            })

            due_date_obj = date.fromisoformat(due_str)

            return {
                "status": "created",
                "id": invoice_id,
                "invoice_number": inv_num,
                "client": client_name,
                "total_inr": total,
                "due_date": due_str,
                "speech": (
                    f"Invoice {inv_num} created for {client_name}. "
                    f"Total amount is {_inr_words(total)} rupees, due on {due_date_obj.strftime('%B %d')}. "
                    f"Do you want me to email it to the client now?"
                )
            }

        elif name == "record_payment":
            client_name = (args.get("client_name") or session.last_client_mentioned or "").strip()
            amount = float(args.get("amount_received", 0))
            team_code = args.get("team_code") or session.verified_team_code

            if not team_code:
                return {"status": "validation_error", "missing_field": "team_code",
                        "message": "Team security code required."}
            if amount <= 0:
                return {"status": "validation_error", "missing_field": "amount_received",
                        "message": "How much was received?"}

            # Find the invoice
            invoice_num = args.get("invoice_number") or session.last_invoice_mentioned
            invoice_id = None

            if client_name:
                inv_result = await asyncio.wait_for(
                    backend.get("/api/invoices?limit=100", org_id=org_id, user_id=session.user_id),
                    timeout=10.0,
                )
                invoices = inv_result if isinstance(inv_result, list) else []
                cn = client_name.lower()
                candidates = [
                    i for i in invoices
                    if cn in (i.get("clientName") or "").lower()
                    and i.get("status") not in ("PAID", "CANCELLED")
                ]
                if candidates:
                    candidates.sort(key=lambda i: abs(
                        float(i.get("totalAmount", 0)) - float(i.get("paidAmount", 0)) - amount
                    ))
                    invoice_id = candidates[0].get("id")
                    invoice_num = candidates[0].get("invoiceNumber")

            payload = {
                "amount": amount,
                "transactionDate": args.get("payment_date", today_str),
                "paymentMethod": args.get("payment_method", "NEFT"),
                "referenceNumber": args.get("utr_or_reference", ""),
                "type": "PAYMENT",
                "invoiceId": invoice_id,
                "orgId": org_id
            }

            endpoint = f"/api/invoices/{invoice_id}/payment" if invoice_id else "/api/transactions"
            await asyncio.wait_for(
                backend.post(endpoint, payload=payload,
                             headers={"X-Team-Code": team_code, "X-Org-Id": org_id},
                             org_id=org_id, user_id=session.user_id),
                timeout=10.0
            )

            session.verified_team_code = _normalize_team_code_value(team_code)
            _clear_org_cache(org_id)

            return {
                "status": "recorded",
                "amount_inr": amount,
                "client": client_name,
                "invoice_number": invoice_num,
                "speech": f"Payment of {_inr_words(amount)} rupees from {client_name} recorded{' for invoice ' + invoice_num if invoice_num else ''}."
            }

        elif name == "record_expense":
            amount = float(args.get("amount", 0))
            team_code = _normalize_team_code_value(args.get("team_code") or session.verified_team_code)
            if not team_code:
                return {"status": "validation_error", "missing_field": "team_code",
                        "message": "Team security code required."}

            gst_pct = args.get("gst_percent", 0)
            gst_amount = amount * (gst_pct / (100 + gst_pct)) if gst_pct else 0
            vendor_gstin = args.get("vendor_gstin", "")
            itc = bool(vendor_gstin) and args.get("category", "") not in ("SALARIES", "FUEL")

            payload = {
                "amount": amount,
                "description": args.get("description"),
                "category": args.get("category", "OTHER"),
                "transactionDate": args.get("expense_date", today_str),
                "type": "EXPENSE",
                "vendorName": args.get("vendor_name", ""),
                "vendorGstin": vendor_gstin,
                "gstAmount": round(gst_amount, 2),
                "itcEligible": itc,
                "orgId": org_id
            }

            await asyncio.wait_for(
                backend.post("/api/transactions", payload=payload,
                             headers={"X-Team-Code": team_code, "X-Org-Id": org_id},
                             org_id=org_id, user_id=session.user_id),
                timeout=10.0
            )

            session.verified_team_code = _normalize_team_code_value(team_code)
            _clear_org_cache(org_id)

            return {
                "status": "recorded",
                "amount_inr": amount,
                "category": args.get("category"),
                "itc_claimable": itc,
                "speech": (
                    f"Expense of {_inr_words(amount)} rupees for {args.get('description', 'the purchase')} recorded under {args.get('category', 'other').lower().replace('_', ' ')}."
                    f"{' Input tax credit is claimable on this.' if itc and gst_amount > 0 else ''}"
                )
            }

        elif name == "send_invoice_email":
            client_name = args.get("client_name") or session.last_client_mentioned or ""
            team_code = _normalize_team_code_value(args.get("team_code") or session.verified_team_code)

            if not client_name:
                return {"status": "validation_error", "missing_field": "client_name",
                        "message": "Which client should I send the invoice to?"}
            if not team_code:
                return {"status": "validation_error", "missing_field": "team_code",
                        "message": "Team security code required."}

            # Find the invoice
            inv_result = await asyncio.wait_for(
                backend.get("/api/invoices?limit=100", org_id=org_id, user_id=session.user_id),
                timeout=10.0,
            )
            invoices = inv_result if isinstance(inv_result, list) else []

            cn = client_name.lower()
            invoice_num = args.get("invoice_number") or session.last_invoice_mentioned

            client_invoices = [
                i for i in invoices
                if cn in (i.get("clientName") or "").lower()
                and i.get("status") not in ("CANCELLED",)
            ]

            if not client_invoices:
                return {
                    "status": "not_found",
                    "message": f"No invoices found for {client_name}.",
                    "speech": f"I couldn't find any invoices for {client_name} in the system."
                }

            # Pick the right one
            target = None
            if invoice_num:
                target = next((i for i in client_invoices if invoice_num in (i.get("invoiceNumber") or "")), None)
            if not target:
                # Default to most recent unpaid, or most recent overall
                unpaid = [i for i in client_invoices if i.get("status") not in ("PAID",)]
                target = unpaid[0] if unpaid else client_invoices[0]

            amount = float(target.get("totalAmount", 0))
            inv_number = target.get("invoiceNumber", "")
            client_email = target.get("clientEmail", "")

            # Use Brevo/SMTP for sending (not Resend sandbox)
            send_payload = {
                "invoiceId": target.get("id"),
                "invoiceNumber": inv_number,
                "clientName": client_name,
                "clientEmail": client_email,
                "amount": amount,
                "message": args.get("message", f"Please find your invoice {inv_number} attached."),
                "orgId": org_id
            }

            try:
                await asyncio.wait_for(
                    backend.post("/api/notifications/send-invoice",
                                 payload=send_payload,
                                 headers={"X-Team-Code": team_code, "X-Org-Id": org_id},
                                 org_id=org_id, user_id=session.user_id),
                    timeout=10.0
                )
                sent = True
                error_message = ""
            except Exception as e:
                error_message = str(e)
                logger.warning({"event": "email_send_failed", "error": error_message})
                sent = False

            session.last_invoice_mentioned = inv_number
            session.verified_team_code = _normalize_team_code_value(team_code)

            if not sent:
                unavailable = any(
                    marker in error_message.lower()
                    for marker in ("mail server", "connection refused", "localhost, 1025", "failed to send email")
                )
                return {
                    "status": "error",
                    "invoice_number": inv_number,
                    "client": client_name,
                    "amount_inr": amount,
                    "speech": (
                        f"I found invoice {inv_number}, but I couldn't email it because the mail server is unavailable right now."
                        if unavailable else
                        f"I found invoice {inv_number}, but I couldn't email it right now."
                    ),
                }

            return {
                "status": "sent",
                "invoice_number": inv_number,
                "client": client_name,
                "amount_inr": amount,
                "speech": (
                    f"Invoice {inv_number} for {_inr_words(amount)} rupees has been emailed to {client_name}."
                )
            }

        elif name == "delete_invoice":
            invoice_number = str(args.get("invoice_number") or session.last_invoice_mentioned or "").strip()
            invoice_id = str(args.get("invoice_id") or "").strip()
            if not invoice_id:
                inv_result = await asyncio.wait_for(
                    backend.get("/api/invoices?limit=100", org_id=org_id, user_id=session.user_id),
                    timeout=10.0,
                )
                invoices = inv_result if isinstance(inv_result, list) else []
                target = None
                if invoice_number:
                    target = next(
                        (
                            inv for inv in invoices
                            if invoice_number.upper() == str(inv.get("invoiceNumber") or "").upper()
                        ),
                        None,
                    )
                if target is None and session.last_invoice_mentioned:
                    target = next(
                        (
                            inv for inv in invoices
                            if str(session.last_invoice_mentioned).upper() == str(inv.get("invoiceNumber") or "").upper()
                        ),
                        None,
                    )
                if target is None and invoices:
                    target = sorted(
                        [inv for inv in invoices if isinstance(inv, dict)],
                        key=lambda inv: str(inv.get("createdAt") or inv.get("issueDate") or ""),
                        reverse=True,
                    )[0]
                if target:
                    invoice_id = str(target.get("id") or "").strip()
                    invoice_number = str(target.get("invoiceNumber") or invoice_number).strip()
            if not invoice_id:
                return {
                    "status": "validation_error",
                    "missing_field": "invoice_number",
                    "message": "Which invoice should I delete?",
                }

            await asyncio.wait_for(
                backend.delete(
                    f"/api/invoices/{invoice_id}",
                    org_id=org_id,
                    user_id=session.user_id,
                ),
                timeout=10.0,
            )
            _clear_org_cache(org_id)
            session.last_invoice_mentioned = invoice_number or session.last_invoice_mentioned
            return {
                "status": "deleted",
                "invoice_number": invoice_number,
                "speech": (
                    f"I deleted invoice {invoice_number}."
                    if invoice_number
                    else "I deleted that invoice."
                ),
            }

        elif name == "check_compliance":
            focus = args.get("focus", "all")
            invoices_r, expenses_r = await asyncio.gather(
                asyncio.wait_for(backend.get("/api/invoices?limit=100", org_id=org_id, user_id=session.user_id), timeout=10.0),
                asyncio.wait_for(backend.get(f"/api/transactions?type=EXPENSE&month={today_str[:7]}", org_id=org_id, user_id=session.user_id), timeout=10.0),
                return_exceptions=True
            )

            invoices = invoices_r if isinstance(invoices_r, list) else []
            expenses = expenses_r if isinstance(expenses_r, list) else []

            month_invoices = [i for i in invoices if i.get("createdAt", "")[:7] == today_str[:7]]
            output_tax = sum(float(i.get("gstAmount", float(i.get("totalAmount", 0)) * 18 / 118)) for i in month_invoices)
            itc = sum(
                float(e.get("gstAmount", 0) or 0)
                for e in expenses
                if e.get("itcEligible")
                and e.get("vendorGstin")
                and str(e.get("category", "")).upper() not in ("SALARIES", "SALARY", "FUEL", "PERSONAL")
                and float(e.get("gstAmount", 0) or 0) > 0
            )
            net_gst = max(0, output_tax - itc)

            next_month = today.month % 12 + 1
            next_year = today.year if today.month < 12 else today.year + 1
            gstr1_date = date(next_year, next_month, 11)
            gstr3b_date = date(next_year, next_month, 20)
            tds_date = date(next_year, next_month, 7)
            gstr1_days = (gstr1_date - today).days
            gstr3b_days = (gstr3b_date - today).days
            tds_days = (tds_date - today).days

            deadlines = [
                {"name": "GSTR-1", "due": gstr1_date.strftime("%B %d"), "days": gstr1_days,
                 "urgency": "critical" if gstr1_days <= 3 else "warning" if gstr1_days <= 7 else "normal"},
                {"name": "GSTR-3B", "due": gstr3b_date.strftime("%B %d"), "days": gstr3b_days,
                 "liability_inr": round(net_gst),
                 "urgency": "critical" if gstr3b_days <= 3 else "warning" if gstr3b_days <= 7 else "normal"},
                {"name": "TDS deposit", "due": tds_date.strftime("%B %d"), "days": tds_days,
                 "urgency": "normal"},
                {"name": "ITR filing", "due": "July 31", "days": (date(today.year, 7, 31) - today).days,
                 "urgency": "normal"}
            ]

            critical = [d for d in deadlines if d["urgency"] == "critical"]
            warnings = [d for d in deadlines if d["urgency"] == "warning"]

            response = {
                "status": "ok",
                "net_gst_payable_inr": round(net_gst),
                "output_tax_inr": round(output_tax),
                "itc_inr": round(itc),
                "deadlines": deadlines,
                "critical_deadlines": critical,
                "warning_deadlines": warnings,
                "speech": (
                    f"{'URGENT: ' + critical[0]['name'] + ' is due in ' + str(critical[0]['days']) + ' days. ' if critical else ''}"
                    f"{'Warning: ' + warnings[0]['name'] + ' in ' + str(warnings[0]['days']) + ' days. ' if warnings else ''}"
                    f"GSTR-1 is due on {gstr1_date.strftime('%B %d')}, {gstr1_days} days from now. "
                    f"GSTR-3B is due on {gstr3b_date.strftime('%B %d')} with a net GST liability of {_inr_words(net_gst)} rupees. "
                    f"TDS deposit deadline is {tds_date.strftime('%B %d')}. "
                    f"And your ITR filing is due by July 31st."
                )
            }
            _set_cached_read_tool(org_id, business_id, name, args, response)
            return response

        elif name == "get_business_health_score":
            metrics_r, invoices_r, clients_r = await asyncio.gather(
                asyncio.wait_for(backend.get(f"/api/finance-intelligence/metrics?businessId={business_id}", org_id=org_id, user_id=session.user_id), timeout=10.0),
                asyncio.wait_for(backend.get("/api/invoices?limit=100", org_id=org_id, user_id=session.user_id), timeout=10.0),
                asyncio.wait_for(backend.get("/api/clients?limit=100", org_id=org_id, user_id=session.user_id), timeout=10.0),
                return_exceptions=True
            )
            metrics = metrics_r if isinstance(metrics_r, dict) else {}
            invoices = invoices_r if isinstance(invoices_r, list) else []
            clients = clients_r if isinstance(clients_r, list) else []

            revenue = float(metrics.get("revenue", 0))
            expenses = float(metrics.get("expenses", 0))
            net = float(metrics.get("netProfit", revenue - expenses))
            margin = (net / revenue * 100) if revenue > 0 else 0
            overdue = [i for i in invoices if i.get("status") == "OVERDUE"]
            overdue_total = sum(float(i.get("totalAmount", 0)) - float(i.get("paidAmount", 0)) for i in overdue)
            outstanding = sum(float(i.get("totalAmount", 0)) - float(i.get("paidAmount", 0))
                             for i in invoices if i.get("status") not in ("PAID", "CANCELLED"))

            def clamp(n): return max(0, min(100, n))
            margin_score = clamp(margin * 2)
            collection_score = clamp(100 - (overdue_total / max(outstanding, 1)) * 100)
            diversity_score = clamp(min(len(clients), 5) * 20)
            expense_score = clamp(100 - max(0, (expenses / max(revenue, 1) * 100) - 50))
            revenue_score = clamp(80 if revenue > 0 else 20)
            overall = round((margin_score + collection_score + diversity_score + expense_score + revenue_score) / 5)
            grade = "A" if overall >= 80 else "B" if overall >= 65 else "C" if overall >= 50 else "D"

            recs = []
            if overdue_total > revenue * 0.2:
                recs.append(f"Collections: {_inr_words(overdue_total)} rupees overdue needs immediate follow-up")
            if margin < 25:
                recs.append("Margin is low — review pricing or reduce costs")
            if len(clients) < 3:
                recs.append("Client concentration risk — acquire new clients")

            session.business_snapshot = {
                "revenue": revenue, "expenses": expenses, "netProfit": net,
                "outstanding": outstanding, "overdueAmount": overdue_total,
                "overdueCount": len(overdue), "clientCount": len(clients)
            }

            response = {
                "status": "ok",
                "overall_score": overall,
                "grade": grade,
                "revenue_inr": revenue,
                "margin_percent": round(margin, 1),
                "overdue_inr": overdue_total,
                "client_count": len(clients),
                "top_recommendation": recs[0] if recs else "Business is healthy — focus on growth",
                "speech": (
                    f"Business health score is {overall} out of 100, grade {grade}. "
                    f"Revenue is {_inr_words(revenue)} rupees at {round(margin)} percent margin. "
                    f"{'Outstanding collections concern: ' + _inr_words(overdue_total) + ' rupees overdue across ' + str(len(overdue)) + ' invoices. ' if overdue else 'No overdue invoices. '}"
                    f"You have {len(clients)} active clients. "
                    f"Top focus: {recs[0] if recs else 'maintain current momentum and pursue growth'}."
                )
            }
            _set_cached_read_tool(org_id, business_id, name, args, response)
            return response

        elif name == "search_market_intelligence":
            query = args.get("query", "")
            focus = args.get("focus", "trends")
            business = org_context.get("business", {})
            industry = business.get("industry", "B2B services")
            city = business.get("city", "India")
            activity = business.get("primaryActivity", "")
            biz_name = business.get("legalName", "")

            enriched_query = f"{query} {industry} India {city} 2026"

            try:
                from app.services.multi_source_search import MultiSourceSearch
                searcher = MultiSourceSearch()
                results = await asyncio.wait_for(searcher.search(enriched_query, max_results=5), timeout=15.0)
                snippets = []
                for r in (results or [])[:5]:
                    if isinstance(r, dict):
                        s = r.get("snippet") or r.get("content") or r.get("text") or ""
                        if s:
                            snippets.append(s[:400])

                return {
                    "status": "ok",
                    "query": query,
                    "industry": industry,
                    "city": city,
                    "focus": focus,
                    "raw_snippets": snippets,
                    "business_name": biz_name,
                    "activity": activity,
                    "_voice_summary": _synthesize_market_result({
                        "query": query,
                        "focus": focus,
                        "activity": activity,
                        "business_name": biz_name,
                        "city": city,
                        "raw_snippets": snippets,
                    }) or "",
                    "instruction": f"Synthesize these market signals into 3-4 sentences of natural speech. Connect each signal to how it specifically affects {biz_name}'s work in {activity}. Do NOT list article titles or URLs. Speak the insights directly.",
                    "note": "All amounts in INR if mentioned"
                }
            except Exception as e:
                generic_fallback = _market_search_fallback(query, focus, business)
                return {
                    "status": "partial",
                    "query": query,
                    "industry": industry,
                    "city": city,
                    "activity": activity,
                    "business_name": biz_name,
                    "fallback_text": generic_fallback,
                    "_voice_summary": generic_fallback,
                    "raw_snippets": [],
                    "instruction": "Speak the fallback_text naturally and connect it directly to the business context."
                }

        elif name == "get_cash_flow_forecast":
            from datetime import timedelta
            days = args.get("days_ahead", 30)
            cutoff = today + timedelta(days=days)
            expense_window_start = today - timedelta(days=89)

            invoices_r, transactions_r = await asyncio.gather(
                asyncio.wait_for(
                    backend.get("/api/invoices?limit=200", org_id=org_id, user_id=session.user_id),
                    timeout=10.0,
                ),
                asyncio.wait_for(
                    backend.get(
                        f"/api/transactions/range?startDate={expense_window_start.isoformat()}&endDate={today.isoformat()}",
                        org_id=org_id,
                        user_id=session.user_id,
                    ),
                    timeout=10.0,
                ),
            )
            invoices = invoices_r if isinstance(invoices_r, list) else []
            transactions = transactions_r if isinstance(transactions_r, list) else []

            expected_inflows = []
            for inv in invoices:
                if inv.get("status") in ("PAID", "CANCELLED"):
                    continue
                due = inv.get("dueDate", "")
                if not due:
                    continue
                try:
                    due_date = date.fromisoformat(due[:10])
                except Exception:
                    continue

                remaining = float(inv.get("totalAmount", 0)) - float(inv.get("paidAmount", 0))
                if remaining <= 0:
                    continue

                days_past = max(0, (today - due_date).days) if due_date < today else 0
                prob = 0.92 if days_past == 0 else 0.75 if days_past <= 10 else 0.55 if days_past <= 20 else 0.35 if days_past <= 30 else 0.12

                if due_date <= cutoff:
                    expected_inflows.append({
                        "client": inv.get("clientName"),
                        "invoice": inv.get("invoiceNumber"),
                        "amount_inr": remaining,
                        "weighted_inr": round(remaining * prob),
                        "probability": prob,
                        "expected_by": due_date.isoformat()
                    })

            total_expected = sum(i["weighted_inr"] for i in expected_inflows)
            total_possible = sum(i["amount_inr"] for i in expected_inflows)

            trailing_expenses = sum(
                float(txn.get("amount", 0) or 0)
                for txn in transactions
                if isinstance(txn, dict)
                and str(txn.get("type") or "").upper() == "EXPENSE"
            )
            daily_burn = trailing_expenses / 90 if trailing_expenses > 0 else 0
            period_burn = daily_burn * days
            net = total_expected - period_burn

            response = {
                "status": "ok",
                "days": days,
                "expected_collections_inr": total_expected,
                "possible_collections_inr": total_possible,
                "expected_expenses_inr": round(period_burn),
                "net_position_inr": round(net),
                "outlook": "positive" if net > 0 else "negative",
                "items": expected_inflows[:8],
                "speech": (
                    f"Over the next {days} days, you can expect about {_inr_words(total_expected)} rupees in collections based on payment probability. "
                    f"With expenses of {_inr_words(period_burn)} rupees expected, "
                    f"your net cash position looks {'positive at ' if net > 0 else 'negative by '}{_inr_words(abs(net))} rupees."
                )
            }
            _set_cached_read_tool(org_id, business_id, name, args, response)
            return response

        elif name == "send_collection_reminder":
            client_name = args.get("client_name") or session.last_client_mentioned or ""
            tone = args.get("tone", "firm")
            team_code = _normalize_team_code_value(args.get("team_code") or session.verified_team_code)

            if not client_name:
                return {"status": "validation_error", "missing_field": "client_name",
                        "message": "Which client should I send the reminder to?"}
            if not team_code:
                return {"status": "validation_error", "missing_field": "team_code",
                        "message": "Team security code required."}

            inv_result = await asyncio.wait_for(
                backend.get("/api/invoices?limit=100", org_id=org_id, user_id=session.user_id),
                timeout=10.0,
            )
            invoices = inv_result if isinstance(inv_result, list) else []
            cn = client_name.lower()
            client_invoices = [
                i for i in invoices
                if cn in (i.get("clientName") or "").lower()
                and i.get("status") not in ("PAID", "CANCELLED")
            ]

            if not client_invoices:
                return {
                    "status": "not_found",
                    "speech": f"No outstanding invoices found for {client_name}."
                }

            inv = client_invoices[0]
            amount = float(inv.get("totalAmount", 0)) - float(inv.get("paidAmount", 0))
            inv_num = inv.get("invoiceNumber", "")
            due = inv.get("dueDate", today_str)
            days_overdue = max(0, (today - date.fromisoformat(due[:10])).days)
            biz_name = org_context.get("business", {}).get("legalName", "Our Team")
            client_email = str(inv.get("clientEmail") or "").strip()
            if not client_email:
                clients = await _ensure_client_cache(session, org_context, backend)
                match = _best_client_match(client_name, clients)
                if match:
                    client_email = str(match.get("email") or "").strip()

            email_templates = {
                "gentle": f"Dear {client_name} Team,\n\nHope you are doing well. This is a friendly reminder that Invoice {inv_num} for {_inr_words(amount)} rupees is now due. Please arrange payment at your earliest convenience.\n\nIf payment has already been made, kindly share the UTR reference.\n\nWarm regards,\n{biz_name}",
                "firm": f"Dear {client_name} Team,\n\nThis is a follow-up regarding Invoice {inv_num} for {_inr_words(amount)} rupees, which is {days_overdue} days overdue. We request immediate processing of this payment.\n\nPlease share UTR/reference number upon payment. For disputes, contact us within 48 hours.\n\nRegards,\n{biz_name}",
                "final": f"Dear {client_name},\n\nDespite multiple reminders, Invoice {inv_num} for {_inr_words(amount)} rupees remains unpaid for {days_overdue} days. This is our final notice before initiating MSME Samadhaan proceedings.\n\nImmediate payment required.\n\n{biz_name}"
            }

            email_body = email_templates.get(tone, email_templates["firm"])

            try:
                if not client_email:
                    raise ValueError("Client email not found for reminder send")
                await asyncio.wait_for(
                    backend.post("/api/notifications/email", payload={
                        "type": "PAYMENT_REMINDER",
                        "recipientEmail": client_email,
                        "recipientName": client_name,
                        "templateData": {
                            "invoiceNumber": inv_num,
                            "businessName": biz_name,
                            "dueDate": due,
                            "amount": str(round(amount, 2)),
                        },
                    }, headers={"X-Team-Code": team_code, "X-Org-Id": org_id}, org_id=org_id, user_id=session.user_id),
                    timeout=8.0
                )
                sent = True
            except Exception:
                sent = False

            session.verified_team_code = _normalize_team_code_value(team_code)
            session.last_client_mentioned = client_name
            session.last_invoice_mentioned = inv_num
            session.last_response_context = json.dumps({
                "type": "collection_reminder",
                "client_name": client_name,
                "invoice_number": inv_num,
                "tone": tone,
            })

            return {
                "status": "sent" if sent else "draft_ready",
                "client": client_name,
                "invoice": inv_num,
                "amount_inr": amount,
                "tone": tone,
                "days_overdue": days_overdue,
                "speech": (
                    f"{'Payment reminder sent' if sent else 'Reminder drafted'} to {client_name} "
                    f"for invoice {inv_num}, {_inr_words(amount)} rupees, {days_overdue} days overdue. "
                    f"Tone is {tone}."
                )
            }

        elif name == "get_overdue_action_plan":
            inv_result = await asyncio.wait_for(
                backend.get("/api/invoices?limit=100", org_id=org_id, user_id=session.user_id),
                timeout=10.0,
            )
            invoices = inv_result if isinstance(inv_result, list) else []

            actions = []
            for inv in invoices:
                if inv.get("status") not in ("OVERDUE", "SENT", "PARTIALLY_PAID"):
                    continue
                amount = float(inv.get("totalAmount", 0))
                paid = float(inv.get("paidAmount", 0))
                remaining = amount - paid
                if remaining < 100:
                    continue

                client = inv.get("clientName", "")
                due = inv.get("dueDate", today_str)
                days_od = max(0, (today - date.fromisoformat(due[:10])).days)

                is_tds_gap = any(d in client.lower() for d in TDS_DEDUCTOR_HINTS) and abs(remaining - amount * 0.10) < 500
                if is_tds_gap:
                    continue

                action = (
                    "Call directly and send firm email" if days_od > 30 else
                    "Send gentle email reminder" if days_od <= 15 else
                    "Follow up call + written reminder"
                )
                actions.append({
                    "client": client,
                    "invoice": inv.get("invoiceNumber"),
                    "outstanding_inr": remaining,
                    "days_overdue": days_od,
                    "recommended_action": action,
                    "priority": "P1" if days_od > 45 else "P2" if days_od > 20 else "P3"
                })

            actions.sort(key=lambda a: (a["days_overdue"], a["outstanding_inr"]), reverse=True)
            total = sum(a["outstanding_inr"] for a in actions)

            response = {
                "status": "ok",
                "total_overdue_inr": total,
                "actions": actions[:8],
                "speech": (
                    f"{len(actions)} invoices need collection action totalling {_inr_words(total)} rupees. "
                    f"Most urgent: {actions[0]['client']} with {_inr_words(actions[0]['outstanding_inr'])} rupees overdue {actions[0]['days_overdue']} days. "
                    f"Recommended: {actions[0]['recommended_action'].lower()}."
                ) if actions else "No overdue invoices needing action."
            }
            _set_cached_read_tool(org_id, business_id, name, args, response)
            return response

        elif name == "get_daily_briefing":
            metrics_r, invoices_r = await asyncio.gather(
                asyncio.wait_for(backend.get(f"/api/finance-intelligence/metrics?businessId={business_id}", org_id=org_id, user_id=session.user_id), timeout=10.0),
                asyncio.wait_for(backend.get("/api/invoices?limit=100", org_id=org_id, user_id=session.user_id), timeout=10.0),
                return_exceptions=True
            )
            metrics = metrics_r if isinstance(metrics_r, dict) else {}
            invoices = invoices_r if isinstance(invoices_r, list) else []

            revenue = float(metrics.get("revenue", 0))
            overdue = [i for i in invoices if i.get("status") == "OVERDUE"]
            overdue_total = sum(float(i.get("totalAmount", 0)) - float(i.get("paidAmount", 0)) for i in overdue)
            next_month = today.month % 12 + 1
            next_year = today.year if today.month < 12 else today.year + 1
            gstr1_days = (date(next_year, next_month, 11) - today).days

            session.briefing_given_today = True

            response = {
                "status": "ok",
                "revenue_mtd_inr": revenue,
                "overdue_count": len(overdue),
                "overdue_total_inr": overdue_total,
                "top_priority": f"Chase {overdue[0].get('clientName')} for {_inr_words(float(overdue[0].get('totalAmount',0))-float(overdue[0].get('paidAmount',0)))} rupees" if overdue else "No overdue collections",
                "gstr1_days": gstr1_days,
                "speech": (
                    f"Good morning. Revenue this month so far is {_inr_words(revenue)} rupees. "
                    f"{'You have ' + str(len(overdue)) + ' overdue invoices totalling ' + _inr_words(overdue_total) + ' rupees that need follow-up. ' if overdue else 'No overdue collections right now. '}"
                    f"{'GSTR-1 is due in ' + str(gstr1_days) + ' days — prepare your invoices. ' if gstr1_days <= 7 else ''}"
                    f"Priority today: {overdue[0].get('clientName') + ' overdue invoice' if overdue else 'focus on client acquisition'}."
                )
            }
            _set_cached_read_tool(org_id, business_id, name, args, response)
            return response

        else:
            return {"status": "error", "message": f"Unknown tool: {name}"}

    except asyncio.TimeoutError:
        return {"status": "error", "message": f"Data fetch timed out for {name}"}
    except Exception as e:
        logger.error({"event": "tool_error", "tool": name, "error": str(e)}, exc_info=True)
        return {"status": "error", "message": f"{name} error: {str(e)[:80]}"}


# ════════════════════════════════════════════════════════════════════════════════
# MAIN PROCESS FUNCTION
# ════════════════════════════════════════════════════════════════════════════════

async def process(
    text: str,
    session: AgentSession,
    org_context: dict,
    groq_key: str,
    backend: Any,
    is_voice: bool = True
) -> dict:
    """
    Main agent loop. Every voice input goes here.
    No classify. No extract. No route. One LLM → tools → answer.
    """
    if not isinstance(session.history, list):
        session.history = []
    else:
        session.history = _sanitize_message_history(session.history)

    if _is_create_invoice_query(text):
        session.pending_client = None
        session.pending_invoice = None
        session.last_client_mentioned = None
    if _is_delete_invoice_query(text):
        session.pending_client = None
    if _is_create_client_query(text):
        session.last_client_mentioned = None
    if _is_record_payment_query(text):
        session.pending_invoice = None
        session.pending_client = None

    await _semantically_enrich_drafts(text, session, org_context, backend)

    if session.pending_client is not None or _is_create_client_query(text):
        merged_client = _merge_client_draft_from_text(text, session.pending_client)
        if session.verified_team_code and not merged_client.get("team_code"):
            merged_client["team_code"] = _normalize_team_code_value(session.verified_team_code)
        if _is_create_client_query(text) and session.pending_client is None and not merged_client:
            merged_client = {}
        tool_result = await execute_tool("create_client", json.dumps(merged_client), session, org_context, backend)
        ui_event = None
        if tool_result.get("status") == "validation_error":
            session.pending_client = {
                key: value for key, value in merged_client.items()
                if value not in (None, "", [], {})
            }
            if tool_result.get("missing_field"):
                session.pending_client["_pending_field"] = tool_result.get("missing_field")
            ui_event = _build_client_form_ui_event(session.pending_client)
        elif tool_result.get("status") == "created":
            if session.pending_invoice is not None:
                session.pending_invoice["client_name"] = tool_result.get("name") or tool_result.get("company") or session.pending_invoice.get("client_name")
                session.pending_invoice["client_id"] = tool_result.get("id")
            ui_event = {
                "type": "client_created",
                "client_id": tool_result.get("id"),
                "client_name": tool_result.get("name"),
                "message": tool_result.get("speech"),
            }
            if session.pending_invoice is not None:
                ui_event["next_ui_event"] = _build_invoice_preview_dialog_ui_event(session.session_id, session.pending_invoice)
                ui_event["resume_invoice"] = True
                ui_event["invoice_draft"] = {
                    key: value for key, value in session.pending_invoice.items()
                    if value not in (None, "", [], {})
                }
        final_answer = tool_result.get("speech") or tool_result.get("message") or "What is the client's actual name?"
        session.last_tool_called = "create_client"
        session.history.append({"role": "user", "content": text})
        session.history.append({"role": "assistant", "content": final_answer})
        if len(session.history) > 20:
            session.history = session.history[-20:]
        voice_response = sanitize_for_tts(final_answer) if is_voice else final_answer
        return {
            "response_text": voice_response,
            "raw_response": final_answer,
            "intent": "INTELLIGENT_QUERY",
            "success": True,
            "session_id": session.session_id,
            "tool_called": session.last_tool_called,
            "ui_event": ui_event,
        }

    if session.pending_invoice is not None or _is_create_invoice_query(text):
        merged_invoice = _merge_invoice_draft_from_text(text, session.pending_invoice)
        if session.pending_invoice is not None and _is_invoice_draft_status_query(text):
            draft_summary = _summarize_invoice_draft(merged_invoice)
            if draft_summary:
                session.pending_invoice = merged_invoice
                session.last_tool_called = "create_invoice"
                session.history.append({"role": "user", "content": text})
                session.history.append({"role": "assistant", "content": draft_summary})
                if len(session.history) > 20:
                    session.history = session.history[-20:]
                voice_response = sanitize_for_tts(draft_summary) if is_voice else draft_summary
                return {
                    "response_text": voice_response,
                    "raw_response": draft_summary,
                    "intent": "INTELLIGENT_QUERY",
                    "success": True,
                    "session_id": session.session_id,
                    "tool_called": session.last_tool_called,
                    "ui_event": _build_invoice_preview_dialog_ui_event(session.session_id, session.pending_invoice),
                }
        if merged_invoice.get("_description_update_prompt"):
            prompt = str(merged_invoice.pop("_description_update_prompt") or "").strip()
            session.pending_invoice = merged_invoice
            session.last_tool_called = "create_invoice"
            session.history.append({"role": "user", "content": text})
            session.history.append({"role": "assistant", "content": prompt})
            if len(session.history) > 20:
                session.history = session.history[-20:]
            voice_response = sanitize_for_tts(prompt) if is_voice else prompt
            return {
                "response_text": voice_response,
                "raw_response": prompt,
                "intent": "INTELLIGENT_QUERY",
                "success": True,
                "session_id": session.session_id,
                "tool_called": session.last_tool_called,
                "ui_event": _build_invoice_preview_dialog_ui_event(session.session_id, session.pending_invoice),
            }
        if merged_invoice.get("_description_update_completed_message"):
            final_answer = str(merged_invoice.pop("_description_update_completed_message") or "").strip()
            session.pending_invoice = merged_invoice
            session.last_tool_called = "create_invoice"
            session.history.append({"role": "user", "content": text})
            session.history.append({"role": "assistant", "content": final_answer})
            if len(session.history) > 20:
                session.history = session.history[-20:]
            voice_response = sanitize_for_tts(final_answer) if is_voice else final_answer
            return {
                "response_text": voice_response,
                "raw_response": final_answer,
                "intent": "INTELLIGENT_QUERY",
                "success": True,
                "session_id": session.session_id,
                "tool_called": session.last_tool_called,
                "ui_event": _build_invoice_preview_dialog_ui_event(session.session_id, session.pending_invoice),
            }
        if session.pending_invoice is not None and (
            merged_invoice.get("_awaiting_invoice_item_review")
            or merged_invoice.get("_awaiting_add_more_items_confirmation")
        ):
            merged_invoice, review_message = _handle_invoice_item_review_followup(text, merged_invoice)
            session.pending_invoice = merged_invoice
            if review_message:
                session.last_tool_called = "create_invoice"
                session.history.append({"role": "user", "content": text})
                session.history.append({"role": "assistant", "content": review_message})
                if len(session.history) > 20:
                    session.history = session.history[-20:]
                voice_response = sanitize_for_tts(review_message) if is_voice else review_message
                return {
                    "response_text": voice_response,
                    "raw_response": review_message,
                    "intent": "INTELLIGENT_QUERY",
                    "success": True,
                    "session_id": session.session_id,
                    "tool_called": session.last_tool_called,
                    "ui_event": _build_invoice_preview_dialog_ui_event(session.session_id, session.pending_invoice),
                }
        if session.pending_invoice is not None and _is_add_invoice_item_query(text):
            merged_invoice["_awaiting_additional_item_description"] = True
            session.pending_invoice = merged_invoice
            final_answer = "Sure. Tell me the next item description."
            session.last_tool_called = "create_invoice"
            session.history.append({"role": "user", "content": text})
            session.history.append({"role": "assistant", "content": final_answer})
            if len(session.history) > 20:
                session.history = session.history[-20:]
            voice_response = sanitize_for_tts(final_answer) if is_voice else final_answer
            return {
                "response_text": voice_response,
                "raw_response": final_answer,
                "intent": "INTELLIGENT_QUERY",
                "success": True,
                "session_id": session.session_id,
                "tool_called": session.last_tool_called,
                "ui_event": _build_invoice_preview_dialog_ui_event(session.session_id, session.pending_invoice),
            }

        due_date_supplied = bool(_extract_due_date_phrase(text))
        if due_date_supplied:
            merged_invoice.pop("_awaiting_additional_item_description", None)
            merged_invoice.pop("_pending_additional_item_description", None)
            session.pending_invoice = merged_invoice
        if session.pending_invoice is not None and (
            merged_invoice.get("_awaiting_additional_item_description")
            or merged_invoice.get("_pending_additional_item_description")
        ) and not due_date_supplied:
            merged_invoice, item_state = _merge_additional_invoice_item_followup(text, merged_invoice)
            session.pending_invoice = merged_invoice
            if item_state == "awaiting_description":
                final_answer = "Tell me the next item description."
            elif item_state == "awaiting_amount":
                item_desc = str(merged_invoice.get("_pending_additional_item_description") or "that item").strip()
                final_answer = f"I can use {item_desc} as the invoice description. What price should I use?"
            elif item_state == "suggested_description":
                item_desc = str(merged_invoice.get("_pending_additional_item_description") or "that item").strip()
                final_answer = f"I suggest {item_desc} as the invoice description. What price should I use?"
            elif item_state == "cancelled":
                final_answer = _next_invoice_missing_prompt(merged_invoice)
            elif item_state == "due_date":
                final_answer = _next_invoice_missing_prompt(merged_invoice)
            else:
                final_answer = "Added that item. You can add another one or keep going."
            session.last_tool_called = "create_invoice"
            session.history.append({"role": "user", "content": text})
            session.history.append({"role": "assistant", "content": final_answer})
            if len(session.history) > 20:
                session.history = session.history[-20:]
            voice_response = sanitize_for_tts(final_answer) if is_voice else final_answer
            return {
                "response_text": voice_response,
                "raw_response": final_answer,
                "intent": "INTELLIGENT_QUERY",
                "success": True,
                "session_id": session.session_id,
                "tool_called": session.last_tool_called,
                "ui_event": _build_invoice_preview_dialog_ui_event(session.session_id, session.pending_invoice),
            }

        clients = await _ensure_client_cache(session, org_context, backend)
        requested_client_id = str(merged_invoice.get("client_id") or "").strip()
        if requested_client_id:
            id_match = next(
                (
                    client for client in clients
                    if str(client.get("id") or "").strip() == requested_client_id
                ),
                None,
            )
            if id_match:
                merged_invoice["client_id"] = requested_client_id
                merged_invoice["client_name"] = id_match.get("name") or merged_invoice.get("client_name")
        if merged_invoice.get("client_name"):
            match = None
            if requested_client_id:
                match = next(
                    (
                        client for client in clients
                        if str(client.get("id") or "").strip() == requested_client_id
                    ),
                    None,
                )
            if match is None:
                match = _best_client_match(str(merged_invoice.get("client_name") or ""), clients)
            if match:
                merged_invoice["client_id"] = match.get("id") or merged_invoice.get("client_id")
                merged_invoice["client_name"] = match.get("name") or merged_invoice["client_name"]
                if match.get("name"):
                    session.last_client_mentioned = match["name"]
            elif clients and not any(
                phrase in (text or "").lower()
                for phrase in ("new client", "new customer", "create client", "add client")
            ):
                session.pending_invoice = {
                    key: value for key, value in merged_invoice.items()
                    if key != "client_name" and value not in (None, "", [], {})
                }
                picker_event = _build_invoice_client_picker_ui_event(session.session_id, clients)
                client_names = ", ".join(
                    str(client.get("name") or "").strip()
                    for client in clients[:5]
                    if str(client.get("name") or "").strip()
                )
                final_answer = "I couldn't match that name to an existing client."
                if client_names:
                    final_answer += f" Which client is this invoice for? Your existing clients are: {client_names}."
                session.last_tool_called = "create_invoice"
                session.history.append({"role": "user", "content": text})
                session.history.append({"role": "assistant", "content": final_answer})
                if len(session.history) > 20:
                    session.history = session.history[-20:]
                voice_response = sanitize_for_tts(final_answer) if is_voice else final_answer
                return {
                    "response_text": voice_response,
                    "raw_response": final_answer,
                    "intent": "INTELLIGENT_QUERY",
                    "success": True,
                    "session_id": session.session_id,
                    "tool_called": session.last_tool_called,
                    "ui_event": picker_event,
                }
        if session.verified_team_code and not merged_invoice.get("team_code"):
            merged_invoice["team_code"] = _normalize_team_code_value(session.verified_team_code)
        if _is_create_invoice_query(text) and session.pending_invoice is None and not merged_invoice:
            merged_invoice = {}
        tool_result = await execute_tool("create_invoice", json.dumps(merged_invoice), session, org_context, backend)
        ui_event = None
        if tool_result.get("status") == "validation_error":
            session.pending_invoice = {
                key: value for key, value in merged_invoice.items()
                if value not in (None, "", [], {})
            }
            ui_event = _build_invoice_preview_dialog_ui_event(session.session_id, session.pending_invoice)
            if tool_result.get("missing_field") == "client_name":
                clients = await _ensure_client_cache(session, org_context, backend)
                picker_event = _build_invoice_client_picker_ui_event(session.session_id, clients)
                if picker_event:
                    ui_event = picker_event
                    client_names = ", ".join(
                        str(client.get("name") or "").strip()
                        for client in clients[:6]
                        if str(client.get("name") or "").strip()
                    )
                    if client_names:
                        tool_result["message"] = (
                            f"Which client is this invoice for? Your existing clients are: {client_names}."
                        )
            elif tool_result.get("missing_field") == "line_items" and session.pending_invoice.get("client_name"):
                tool_result["message"] = (
                    f"I've opened a live invoice draft for {session.pending_invoice.get('client_name')}. "
                    "You can keep speaking with the item and amount."
                )
        elif tool_result.get("status") == "created":
            ui_event = {
                "type": "invoice_created",
                "invoice_id": tool_result.get("id"),
                "invoice_number": tool_result.get("invoice_number"),
                "client_name": tool_result.get("client"),
                "total": tool_result.get("total_inr"),
                "due_date": tool_result.get("due_date"),
                "path": f"/invoices/{tool_result.get('id')}" if tool_result.get("id") else None,
            }
        elif tool_result.get("status") == "error":
            session.pending_invoice = {
                key: value for key, value in merged_invoice.items()
                if value not in (None, "", [], {})
            }
            ui_event = _build_invoice_preview_dialog_ui_event(session.session_id, session.pending_invoice)
        final_answer = tool_result.get("speech") or tool_result.get("message") or "Which client is this invoice for?"
        session.last_tool_called = "create_invoice"
        session.history.append({"role": "user", "content": text})
        session.history.append({"role": "assistant", "content": final_answer})
        if len(session.history) > 20:
            session.history = session.history[-20:]
        voice_response = sanitize_for_tts(final_answer) if is_voice else final_answer
        return {
            "response_text": voice_response,
            "raw_response": final_answer,
            "intent": "INTELLIGENT_QUERY",
            "success": tool_result.get("status") != "error",
            "session_id": session.session_id,
            "tool_called": session.last_tool_called,
            "ui_event": ui_event,
        }

    delete_context = {}
    try:
        delete_context = json.loads(session.last_response_context or "{}")
    except Exception:
        delete_context = {}

    if delete_context.get("type") == "invoice_delete_confirmation":
        if _is_cancel_query(text):
            session.last_response_context = None
            final_answer = "Okay, I won't delete that invoice."
            session.history.append({"role": "user", "content": text})
            session.history.append({"role": "assistant", "content": final_answer})
            if len(session.history) > 20:
                session.history = session.history[-20:]
            voice_response = sanitize_for_tts(final_answer) if is_voice else final_answer
            return {
                "response_text": voice_response,
                "raw_response": final_answer,
                "intent": "INTELLIGENT_QUERY",
                "success": True,
                "session_id": session.session_id,
                "tool_called": session.last_tool_called,
            }
        if _is_delete_confirmation(text):
            tool_result = await execute_tool(
                "delete_invoice",
                json.dumps(
                    {
                        "invoice_id": delete_context.get("invoice_id"),
                        "invoice_number": delete_context.get("invoice_number"),
                    }
                ),
                session,
                org_context,
                backend,
            )
            session.last_response_context = None
            final_answer = tool_result.get("speech") or tool_result.get("message") or "I couldn't delete that invoice."
            session.last_tool_called = "delete_invoice"
            session.history.append({"role": "user", "content": text})
            session.history.append({"role": "assistant", "content": final_answer})
            if len(session.history) > 20:
                session.history = session.history[-20:]
            voice_response = sanitize_for_tts(final_answer) if is_voice else final_answer
            return {
                "response_text": voice_response,
                "raw_response": final_answer,
                "intent": "INTELLIGENT_QUERY",
                "success": tool_result.get("status") != "error",
                "session_id": session.session_id,
                "tool_called": session.last_tool_called,
            }

    if _is_delete_invoice_query(text):
        invoice_number = _extract_invoice_number(text) or session.last_invoice_mentioned
        invoices_r = await backend.get("/api/invoices?limit=100", org_id=session.org_uuid, user_id=session.user_id)
        invoices = invoices_r if isinstance(invoices_r, list) else []
        target = None
        if invoice_number:
            target = next(
                (
                    inv for inv in invoices
                    if invoice_number.upper() == str(inv.get("invoiceNumber") or "").upper()
                ),
                None,
            )
        if target is None and invoices:
            target = sorted(
                [inv for inv in invoices if isinstance(inv, dict)],
                key=lambda inv: str(inv.get("createdAt") or inv.get("issueDate") or ""),
                reverse=True,
            )[0]
            invoice_number = str(target.get("invoiceNumber") or invoice_number or "").strip()
        if target is None:
            final_answer = "I couldn't find the invoice to delete. Say the invoice number and I’ll remove it."
        else:
            client_name = str(target.get("clientName") or "").strip()
            session.last_response_context = json.dumps(
                {
                    "type": "invoice_delete_confirmation",
                    "invoice_id": target.get("id"),
                    "invoice_number": invoice_number,
                    "client_name": client_name,
                }
            )
            final_answer = (
                f"Do you want me to delete invoice {invoice_number} for {client_name}? Say confirm delete."
                if client_name
                else f"Do you want me to delete invoice {invoice_number}? Say confirm delete."
            )
        session.last_tool_called = "delete_invoice"
        session.history.append({"role": "user", "content": text})
        session.history.append({"role": "assistant", "content": final_answer})
        if len(session.history) > 20:
            session.history = session.history[-20:]
        voice_response = sanitize_for_tts(final_answer) if is_voice else final_answer
        return {
            "response_text": voice_response,
            "raw_response": final_answer,
            "intent": "INTELLIGENT_QUERY",
            "success": True,
            "session_id": session.session_id,
            "tool_called": session.last_tool_called,
        }

    if session.pending_payment is not None or _is_record_payment_query(text):
        merged_payment = _merge_payment_draft_from_text(text, session.pending_payment)
        clients = await _ensure_client_cache(session, org_context, backend)

        if merged_payment.get("client_name"):
            match = _best_client_match(str(merged_payment.get("client_name") or ""), clients)
            if match:
                merged_payment["client_name"] = match.get("name") or merged_payment["client_name"]
                if match.get("name"):
                    session.last_client_mentioned = match["name"]
            elif clients:
                session.pending_payment = {
                    key: value for key, value in merged_payment.items()
                    if value not in (None, "", [], {})
                }
                client_names = ", ".join(
                    str(client.get("name") or "").strip()
                    for client in clients[:5]
                    if str(client.get("name") or "").strip()
                )
                final_answer = "I couldn't match that client."
                if client_names:
                    final_answer += f" Which client is this payment for? Your existing clients are: {client_names}."
                session.last_tool_called = "record_payment"
                session.history.append({"role": "user", "content": text})
                session.history.append({"role": "assistant", "content": final_answer})
                if len(session.history) > 20:
                    session.history = session.history[-20:]
                voice_response = sanitize_for_tts(final_answer) if is_voice else final_answer
                return {
                    "response_text": voice_response,
                    "raw_response": final_answer,
                    "intent": "INTELLIGENT_QUERY",
                    "success": True,
                    "session_id": session.session_id,
                    "tool_called": session.last_tool_called,
                }

        if not merged_payment.get("client_name"):
            session.pending_payment = {
                key: value for key, value in merged_payment.items()
                if value not in (None, "", [], {})
            }
            final_answer = "Which client made this payment?"
            session.last_tool_called = "record_payment"
            session.history.append({"role": "user", "content": text})
            session.history.append({"role": "assistant", "content": final_answer})
            if len(session.history) > 20:
                session.history = session.history[-20:]
            voice_response = sanitize_for_tts(final_answer) if is_voice else final_answer
            return {
                "response_text": voice_response,
                "raw_response": final_answer,
                "intent": "INTELLIGENT_QUERY",
                "success": True,
                "session_id": session.session_id,
                "tool_called": session.last_tool_called,
            }

        invoices_r = await backend.get("/api/invoices?limit=100", org_id=session.org_uuid, user_id=session.user_id)
        invoices = [inv for inv in invoices_r if isinstance(inv, dict)] if isinstance(invoices_r, list) else []
        client_name = str(merged_payment.get("client_name") or "").strip()
        client_invoices = [
            inv for inv in invoices
            if client_name.lower() in str(inv.get("clientName") or "").lower()
            and str(inv.get("status") or "").upper() not in ("PAID", "CANCELLED")
        ]
        target_invoice = None
        requested_invoice_number = str(merged_payment.get("invoice_number") or "").strip()
        if requested_invoice_number:
            target_invoice = next(
                (
                    inv for inv in client_invoices
                    if requested_invoice_number.upper() == str(inv.get("invoiceNumber") or "").upper()
                ),
                None,
            )
        if target_invoice is None and client_invoices:
            client_invoices.sort(
                key=lambda inv: str(inv.get("createdAt") or inv.get("issueDate") or ""),
                reverse=True,
            )
            target_invoice = client_invoices[0]
            merged_payment["invoice_number"] = str(target_invoice.get("invoiceNumber") or "")

        if _is_partial_payment_query(text) or merged_payment.get("is_partial_payment"):
            merged_payment["is_partial_payment"] = True
            if not merged_payment.get("amount_received"):
                session.pending_payment = {
                    key: value for key, value in merged_payment.items()
                    if value not in (None, "", [], {})
                }
                item = str(client_name or merged_payment.get("invoice_number") or "that invoice")
                final_answer = f"How much payment was received for {item}?"
                session.last_tool_called = "record_payment"
                session.history.append({"role": "user", "content": text})
                session.history.append({"role": "assistant", "content": final_answer})
                if len(session.history) > 20:
                    session.history = session.history[-20:]
                voice_response = sanitize_for_tts(final_answer) if is_voice else final_answer
                return {
                    "response_text": voice_response,
                    "raw_response": final_answer,
                    "intent": "INTELLIGENT_QUERY",
                    "success": True,
                    "session_id": session.session_id,
                    "tool_called": session.last_tool_called,
                }
        elif not merged_payment.get("amount_received") and target_invoice is not None:
            total_amount = float(target_invoice.get("totalAmount", 0) or 0)
            paid_amount = float(
                target_invoice.get("paidAmount", target_invoice.get("amountPaid", 0)) or 0
            )
            outstanding = max(0.0, total_amount - paid_amount)
            if outstanding > 0:
                merged_payment["amount_received"] = outstanding

        if session.verified_team_code and not merged_payment.get("team_code"):
            merged_payment["team_code"] = _normalize_team_code_value(session.verified_team_code)

        tool_result = await execute_tool("record_payment", json.dumps(merged_payment), session, org_context, backend)
        if tool_result.get("status") == "validation_error":
            session.pending_payment = {
                key: value for key, value in merged_payment.items()
                if value not in (None, "", [], {})
            }
        else:
            session.pending_payment = None

        final_answer = tool_result.get("speech") or tool_result.get("message") or "I couldn't record that payment."
        session.last_tool_called = "record_payment"
        session.history.append({"role": "user", "content": text})
        session.history.append({"role": "assistant", "content": final_answer})
        if len(session.history) > 20:
            session.history = session.history[-20:]
        voice_response = sanitize_for_tts(final_answer) if is_voice else final_answer
        return {
            "response_text": voice_response,
            "raw_response": final_answer,
            "intent": "INTELLIGENT_QUERY",
            "success": tool_result.get("status") != "error",
            "session_id": session.session_id,
            "tool_called": session.last_tool_called,
        }

    if session.pending_expense is not None or _is_record_expense_query(text):
        merged_expense = _merge_expense_draft_from_text(text, session.pending_expense)
        if session.verified_team_code and not merged_expense.get("team_code"):
            merged_expense["team_code"] = _normalize_team_code_value(session.verified_team_code)
        if _is_record_expense_query(text) and session.pending_expense is None and not merged_expense:
            merged_expense = {}
        tool_result = await execute_tool("record_expense", json.dumps(merged_expense), session, org_context, backend)
        if tool_result.get("status") == "validation_error":
            session.pending_expense = {
                key: value for key, value in merged_expense.items()
                if value not in (None, "", [], {})
            }
        else:
            session.pending_expense = None
        final_answer = tool_result.get("speech") or tool_result.get("message") or "What expense should I record?"
        session.last_tool_called = "record_expense"
        session.history.append({"role": "user", "content": text})
        session.history.append({"role": "assistant", "content": final_answer})
        if len(session.history) > 20:
            session.history = session.history[-20:]
        voice_response = sanitize_for_tts(final_answer) if is_voice else final_answer
        return {
            "response_text": voice_response,
            "raw_response": final_answer,
            "intent": "INTELLIGENT_QUERY",
            "success": True,
            "session_id": session.session_id,
            "tool_called": session.last_tool_called,
        }

    if _is_create_client_query(text):
        tool_result = await execute_tool("create_client", "{}", session, org_context, backend)
        final_answer = tool_result.get("speech") or tool_result.get("message") or "What is the client's actual name?"
        session.last_tool_called = "create_client"
        session.history.append({"role": "user", "content": text})
        session.history.append({"role": "assistant", "content": final_answer})
        if len(session.history) > 20:
            session.history = session.history[-20:]
        voice_response = sanitize_for_tts(final_answer) if is_voice else final_answer
        return {
            "response_text": voice_response,
            "raw_response": final_answer,
            "intent": "INTELLIGENT_QUERY",
            "success": True,
            "session_id": session.session_id,
            "tool_called": session.last_tool_called,
            "ui_event": _build_client_form_ui_event(session.pending_client or {}),
        }

    if _is_client_list_query(text):
        sort_mode = "newest" if "newest" in text.lower() else "revenue"
        tool_result = await execute_tool("get_clients", json.dumps({"sort_by": sort_mode}), session, org_context, backend)
        clients = [client for client in tool_result.get("clients", []) if isinstance(client, dict)]
        if clients:
            preview = clients[:5]
            names = ", ".join(str(client.get("name") or "").strip() for client in preview if str(client.get("name") or "").strip())
            extra = len(clients) - len(preview)
            final_answer = (
                f"Your clients are {names}."
                if extra <= 0 else
                f"Your top clients are {names}, and {extra} more are on the books."
            )
        else:
            final_answer = "There are no clients on record yet."
        session.last_tool_called = "get_clients"
        session.history.append({"role": "user", "content": text})
        session.history.append({"role": "assistant", "content": final_answer})
        if len(session.history) > 20:
            session.history = session.history[-20:]
        voice_response = sanitize_for_tts(final_answer) if is_voice else final_answer
        return {
            "response_text": voice_response,
            "raw_response": final_answer,
            "intent": "INTELLIGENT_QUERY",
            "success": True,
            "session_id": session.session_id,
            "tool_called": session.last_tool_called,
        }

    if _is_unpaid_invoice_query(text):
        tool_result = await execute_tool("get_invoices", json.dumps({"status": "all"}), session, org_context, backend)
        invoices = [inv for inv in tool_result.get("invoices", []) if isinstance(inv, dict)]
        unpaid = [
            inv for inv in invoices
            if str(inv.get("status") or "").upper() not in ("PAID", "CANCELLED")
            and float(inv.get("outstanding_inr", 0) or 0) > 0
        ]
        if unpaid:
            unpaid.sort(key=lambda inv: float(inv.get("outstanding_inr", 0) or 0), reverse=True)
            preview = unpaid[:3]
            summary = ", ".join(
                f"{inv.get('invoice_number')} for {inv.get('client')} at {_inr_words(float(inv.get('outstanding_inr', 0) or 0))} rupees"
                for inv in preview
            )
            extra = len(unpaid) - len(preview)
            final_answer = (
                f"The unpaid invoices are {summary}."
                if extra <= 0 else
                f"The unpaid invoices are {summary}, and {extra} more are still open."
            )
        else:
            final_answer = "There are no unpaid invoices right now."
        session.last_tool_called = "get_invoices"
        session.history.append({"role": "user", "content": text})
        session.history.append({"role": "assistant", "content": final_answer})
        if len(session.history) > 20:
            session.history = session.history[-20:]
        voice_response = sanitize_for_tts(final_answer) if is_voice else final_answer
        return {
            "response_text": voice_response,
            "raw_response": final_answer,
            "intent": "INTELLIGENT_QUERY",
            "success": True,
            "session_id": session.session_id,
            "tool_called": session.last_tool_called,
        }

    if _is_income_transaction_query(text):
        start_date, end_date, period_label = _month_bounds_for_query("all time")
        txns = await asyncio.wait_for(
            backend.get(
                f"/api/transactions/range?startDate={start_date.isoformat()}&endDate={end_date.isoformat()}",
                org_id=org_context.get("org_id") or session.org_uuid,
                user_id=session.user_id,
            ),
            timeout=10.0,
        )
        transactions = [txn for txn in txns if isinstance(txn, dict)] if isinstance(txns, list) else []
        income_transactions = [
            txn for txn in transactions
            if str(txn.get("type") or "").upper() in ("INCOME", "PAYMENT")
            and float(txn.get("amount", 0) or 0) > 0
        ]
        total_income = sum(float(txn.get("amount", 0) or 0) for txn in income_transactions)
        if income_transactions:
            income_transactions.sort(key=lambda txn: str(txn.get("transactionDate") or ""), reverse=True)
            preview = income_transactions[:5]
            summary = ", ".join(
                f"{txn.get('description') or 'payment received'} at {_inr_words(float(txn.get('amount', 0) or 0))} rupees"
                for txn in preview
            )
            extra = len(income_transactions) - len(preview)
            final_answer = (
                f"Income transactions in {period_label} total {_inr_words(total_income)} rupees. Recent collections are {summary}."
                if extra <= 0 else
                f"Income transactions in {period_label} total {_inr_words(total_income)} rupees. Recent collections are {summary}, and {extra} more are on record."
            )
        else:
            final_answer = f"No income transactions were recorded in {period_label}."
        session.last_tool_called = "record_payment"
        session.history.append({"role": "user", "content": text})
        session.history.append({"role": "assistant", "content": final_answer})
        if len(session.history) > 20:
            session.history = session.history[-20:]
        voice_response = sanitize_for_tts(final_answer) if is_voice else final_answer
        return {
            "response_text": voice_response,
            "raw_response": final_answer,
            "intent": "INTELLIGENT_QUERY",
            "success": True,
            "session_id": session.session_id,
            "tool_called": session.last_tool_called,
        }

    if _is_salary_lookup_query(text):
        start_date, end_date, period_label = _month_bounds_for_query(text)
        txns = await asyncio.wait_for(
            backend.get(
                f"/api/transactions/range?startDate={start_date.isoformat()}&endDate={end_date.isoformat()}",
                org_id=org_context.get("org_id") or session.org_uuid,
                user_id=session.user_id,
            ),
            timeout=10.0,
        )
        transactions = [txn for txn in txns if isinstance(txn, dict)] if isinstance(txns, list) else []
        salary_transactions = [
            txn for txn in transactions
            if str(txn.get("type") or "").upper() == "EXPENSE"
            and str(txn.get("category") or "").upper() == "SALARIES"
        ]
        total_salary = sum(float(txn.get("amount", 0) or 0) for txn in salary_transactions)
        if salary_transactions:
            latest = max(
                salary_transactions,
                key=lambda txn: str(txn.get("transactionDate") or ""),
            )
            latest_date = str(latest.get("transactionDate") or "")
            final_answer = (
                f"Yes. Salary payments in {period_label} total {_inr_words(total_salary)} rupees. "
                f"The latest salary transaction was on {latest_date}."
            )
        else:
            final_answer = f"No salary payments were recorded in {period_label}."
        session.last_tool_called = "record_expense"
        session.history.append({"role": "user", "content": text})
        session.history.append({"role": "assistant", "content": final_answer})
        if len(session.history) > 20:
            session.history = session.history[-20:]
        voice_response = sanitize_for_tts(final_answer) if is_voice else final_answer
        return {
            "response_text": voice_response,
            "raw_response": final_answer,
            "intent": "INTELLIGENT_QUERY",
            "success": True,
            "session_id": session.session_id,
            "tool_called": session.last_tool_called,
        }

    expense_category = _extract_expense_category_query(text)
    if expense_category:
        start_date, end_date, period_label = _month_bounds_for_query(text)
        txns = await asyncio.wait_for(
            backend.get(
                f"/api/transactions/range?startDate={start_date.isoformat()}&endDate={end_date.isoformat()}",
                org_id=org_context.get("org_id") or session.org_uuid,
                user_id=session.user_id,
            ),
            timeout=10.0,
        )
        transactions = [txn for txn in txns if isinstance(txn, dict)] if isinstance(txns, list) else []
        matching_expenses = [
            txn for txn in transactions
            if str(txn.get("type") or "").upper() == "EXPENSE"
            and str(txn.get("category") or "").lower() == expense_category
        ]
        total_expense = sum(float(txn.get("amount", 0) or 0) for txn in matching_expenses)
        if matching_expenses:
            matching_expenses.sort(key=lambda txn: str(txn.get("transactionDate") or ""), reverse=True)
            preview = matching_expenses[:3]
            summary = ", ".join(
                f"{txn.get('description') or 'expense'} at {_inr_words(float(txn.get('amount', 0) or 0))} rupees"
                for txn in preview
            )
            extra = len(matching_expenses) - len(preview)
            final_answer = (
                f"{expense_category.capitalize()} expenses in {period_label} total {_inr_words(total_expense)} rupees. Recent items are {summary}."
                if extra <= 0 else
                f"{expense_category.capitalize()} expenses in {period_label} total {_inr_words(total_expense)} rupees. Recent items are {summary}, and {extra} more are on record."
            )
        else:
            final_answer = f"No {expense_category} expenses were recorded in {period_label}."
        session.last_tool_called = "record_expense"
        session.history.append({"role": "user", "content": text})
        session.history.append({"role": "assistant", "content": final_answer})
        if len(session.history) > 20:
            session.history = session.history[-20:]
        voice_response = sanitize_for_tts(final_answer) if is_voice else final_answer
        return {
            "response_text": voice_response,
            "raw_response": final_answer,
            "intent": "INTELLIGENT_QUERY",
            "success": True,
            "session_id": session.session_id,
            "tool_called": session.last_tool_called,
        }

    if _is_send_confirmation_query(text) and session.last_tool_called == "send_collection_reminder":
        reminder_context = {}
        try:
            reminder_context = json.loads(session.last_response_context or "{}")
        except Exception:
            reminder_context = {}
        args = {
            "client_name": reminder_context.get("client_name") or session.last_client_mentioned,
            "invoice_number": reminder_context.get("invoice_number") or session.last_invoice_mentioned,
            "tone": reminder_context.get("tone") or "firm",
            "team_code": session.verified_team_code,
        }
        tool_result = await execute_tool("send_collection_reminder", json.dumps(args), session, org_context, backend)
        final_answer = tool_result.get("speech") or tool_result.get("message") or "I could not send that reminder."
        session.history.append({"role": "user", "content": text})
        session.history.append({"role": "assistant", "content": final_answer})
        if len(session.history) > 20:
            session.history = session.history[-20:]
        voice_response = sanitize_for_tts(final_answer) if is_voice else final_answer
        return {
            "response_text": voice_response,
            "raw_response": final_answer,
            "intent": "INTELLIGENT_QUERY",
            "success": True,
            "session_id": session.session_id,
            "tool_called": "send_collection_reminder",
        }

    if _is_send_confirmation_query(text):
        send_context = {}
        try:
            send_context = json.loads(session.last_response_context or "{}")
        except Exception:
            send_context = {}
        if send_context.get("type") == "invoice_send_offer":
            args = {
                "client_name": send_context.get("client_name") or session.last_client_mentioned,
                "invoice_number": send_context.get("invoice_number") or session.last_invoice_mentioned,
                "team_code": session.verified_team_code,
            }
            tool_result = await execute_tool("send_invoice_email", json.dumps(args), session, org_context, backend)
            final_answer = tool_result.get("speech") or tool_result.get("message") or "I couldn't send that invoice."
            session.history.append({"role": "user", "content": text})
            session.history.append({"role": "assistant", "content": final_answer})
            if len(session.history) > 20:
                session.history = session.history[-20:]
            voice_response = sanitize_for_tts(final_answer) if is_voice else final_answer
            return {
                "response_text": voice_response,
                "raw_response": final_answer,
                "intent": "INTELLIGENT_QUERY",
                "success": tool_result.get("status") != "error",
                "session_id": session.session_id,
                "tool_called": "send_invoice_email",
            }

    if _is_negative_response_query(text):
        send_context = {}
        try:
            send_context = json.loads(session.last_response_context or "{}")
        except Exception:
            send_context = {}
        if send_context.get("type") == "invoice_send_offer":
            final_answer = "Okay, I won't email the invoice right now."
            session.last_response_context = None
            session.history.append({"role": "user", "content": text})
            session.history.append({"role": "assistant", "content": final_answer})
            if len(session.history) > 20:
                session.history = session.history[-20:]
            voice_response = sanitize_for_tts(final_answer) if is_voice else final_answer
            return {
                "response_text": voice_response,
                "raw_response": final_answer,
                "intent": "INTELLIGENT_QUERY",
                "success": True,
                "session_id": session.session_id,
                "tool_called": "create_invoice",
            }

    if _is_highest_unpaid_client_query(text):
        direct_answer = _answer_from_session_context(text, session)
        if direct_answer:
            session.last_tool_called = "get_invoices"
            session.history.append({"role": "user", "content": text})
            session.history.append({"role": "assistant", "content": direct_answer})
            if len(session.history) > 20:
                session.history = session.history[-20:]
            voice_response = sanitize_for_tts(direct_answer) if is_voice else direct_answer
            return {
                "response_text": voice_response,
                "raw_response": direct_answer,
                "intent": "INTELLIGENT_QUERY",
                "success": True,
                "session_id": session.session_id,
                "tool_called": session.last_tool_called,
            }
        tool_result = await execute_tool("get_clients", json.dumps({"sort_by": "outstanding"}), session, org_context, backend)
        clients = [client for client in tool_result.get("clients", []) if isinstance(client, dict)]
        if clients:
            top = clients[0]
            final_answer = (
                f"{top.get('name')} from {top.get('company')} has the highest unpaid amount right now at "
                f"{_inr_words(float(top.get('outstanding_inr', 0) or 0))} rupees."
            )
            session.last_tool_called = "get_clients"
            session.history.append({"role": "user", "content": text})
            session.history.append({"role": "assistant", "content": final_answer})
            if len(session.history) > 20:
                session.history = session.history[-20:]
            voice_response = sanitize_for_tts(final_answer) if is_voice else final_answer
            return {
                "response_text": voice_response,
                "raw_response": final_answer,
                "intent": "INTELLIGENT_QUERY",
                "success": True,
                "session_id": session.session_id,
                "tool_called": session.last_tool_called,
            }

    if _is_market_growth_query(text):
        args = json.dumps({"query": text, "focus": "opportunities"})
        tool_result = await execute_tool("search_market_intelligence", args, session, org_context, backend)
        final_answer = _synthesize_market_result(tool_result) or "I need a fresh market signal window before I answer that."
        session.last_tool_called = "search_market_intelligence"
        session.last_market_query = text
        session.last_market_results = list(tool_result.get("raw_snippets", []) or [])
        fallback_text = str(tool_result.get("fallback_text") or "").strip()
        if fallback_text:
            session.last_market_results = (session.last_market_results or []) + [fallback_text]
        session.history.append({"role": "user", "content": text})
        session.history.append({"role": "assistant", "content": final_answer})
        if len(session.history) > 20:
            session.history = session.history[-20:]
        voice_response = sanitize_for_tts(final_answer) if is_voice else final_answer
        return {
            "response_text": voice_response,
            "raw_response": final_answer,
            "intent": "INTELLIGENT_QUERY",
            "success": True,
            "session_id": session.session_id,
            "tool_called": session.last_tool_called,
        }

    if _is_growth_strategy_query(text):
        direct_growth_answer = _grounded_growth_plan(session, org_context)
        if direct_growth_answer:
            session.last_tool_called = "get_business_health_score"
            session.history.append({"role": "user", "content": text})
            session.history.append({"role": "assistant", "content": direct_growth_answer})
            if len(session.history) > 20:
                session.history = session.history[-20:]
            voice_response = sanitize_for_tts(direct_growth_answer) if is_voice else direct_growth_answer
            return {
                "response_text": voice_response,
                "raw_response": direct_growth_answer,
                "intent": "INTELLIGENT_QUERY",
                "success": True,
                "session_id": session.session_id,
                "tool_called": session.last_tool_called,
            }

    if _is_market_scale_followup_query(text, session):
        final_answer = _grounded_growth_plan(session, org_context)
        tool_result = None
        market_query = (
            f"{session.last_market_query}. Based on those signals, what concrete steps should this business take this month to scale?"
            if session.last_market_query
            else text
        )
        if not final_answer:
            args = json.dumps({"query": market_query, "focus": "opportunities"})
            tool_result = await execute_tool("search_market_intelligence", args, session, org_context, backend)
            final_answer = (
                _synthesize_market_scale_followup(tool_result, session, org_context)
                or _synthesize_market_result(tool_result)
                or "This month, focus on higher-density commercial corridors, recurring maintenance contracts, and multi-site corporate rollouts."
            )
            session.last_tool_called = "search_market_intelligence"
        else:
            session.last_tool_called = "get_business_health_score"
        session.last_market_query = market_query
        if isinstance(tool_result, dict):
            session.last_market_results = list(tool_result.get("raw_snippets", []) or [])
            fallback_text = str(tool_result.get("fallback_text") or "").strip()
            if fallback_text:
                session.last_market_results = (session.last_market_results or []) + [fallback_text]
        session.history.append({"role": "user", "content": text})
        session.history.append({"role": "assistant", "content": final_answer})
        if len(session.history) > 20:
            session.history = session.history[-20:]
        voice_response = sanitize_for_tts(final_answer) if is_voice else final_answer
        return {
            "response_text": voice_response,
            "raw_response": final_answer,
            "intent": "INTELLIGENT_QUERY",
            "success": True,
            "session_id": session.session_id,
            "tool_called": session.last_tool_called,
        }

    if _is_market_action_followup_query(text, session):
        market_query = (
            f"{session.last_market_query}. Based on those signals, what should this business do now to capture the opportunity, escalate correctly, and avoid financial loss?"
            if session.last_market_query
            else text
        )
        focus = "risks" if any(token in text.lower() for token in ("risk", "loss", "mitigate", "protect")) else "opportunities"
        args = json.dumps({"query": market_query, "focus": focus})
        tool_result = await execute_tool("search_market_intelligence", args, session, org_context, backend)
        final_answer = (
            _market_action_guidance(text, session, org_context, tool_result)
            or _synthesize_market_result(tool_result)
            or "Focus on the strongest demand pockets, protect payment terms, and escalate only the accounts that are worth the execution load."
        )
        session.last_tool_called = "search_market_intelligence"
        session.last_market_query = market_query
        session.last_market_results = list(tool_result.get("raw_snippets", []) or [])
        fallback_text = str(tool_result.get("fallback_text") or "").strip()
        if fallback_text:
            session.last_market_results = (session.last_market_results or []) + [fallback_text]
        session.history.append({"role": "user", "content": text})
        session.history.append({"role": "assistant", "content": final_answer})
        if len(session.history) > 20:
            session.history = session.history[-20:]
        voice_response = sanitize_for_tts(final_answer) if is_voice else final_answer
        return {
            "response_text": voice_response,
            "raw_response": final_answer,
            "intent": "INTELLIGENT_QUERY",
            "success": True,
            "session_id": session.session_id,
            "tool_called": session.last_tool_called,
        }

    direct_answer = _answer_from_session_context(text, session)
    if direct_answer:
        session.history.append({"role": "user", "content": text})
        session.history.append({"role": "assistant", "content": direct_answer})
        if len(session.history) > 20:
            session.history = session.history[-20:]
        voice_response = sanitize_for_tts(direct_answer) if is_voice else direct_answer
        return {
            "response_text": voice_response,
            "raw_response": direct_answer,
            "intent": "INTELLIGENT_QUERY",
            "success": True,
            "session_id": session.session_id,
            "tool_called": session.last_tool_called,
        }

    session.last_tool_called = None

    for proxy_var in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        os.environ.pop(proxy_var, None)
    os.environ["NO_PROXY"] = "*"
    os.environ["no_proxy"] = "*"

    api_keys = _resolved_groq_keys(groq_key)
    groq_clients = await _create_groq_clients(api_keys)
    system = build_system_prompt(org_context, session)

    messages = [{"role": "system", "content": system}]
    history_window = max(4, int(settings.GROQ_VOICE_HISTORY_MESSAGES or 8))
    messages.extend(_sanitize_message_history(session.history[-history_window:]))
    messages.append({"role": "user", "content": text})

    final_answer = None
    last_tool_results: List[Tuple[str, Any]] = []

    try:
        for round_num in range(max(1, int(settings.GROQ_VOICE_TOOL_ROUNDS or 3))):
            try:
                response = await _call_groq_with_failover(
                    groq_clients,
                    api_keys,
                    timeout_seconds=11.0,
                    model=settings.GROQ_VOICE_MODEL,
                    messages=messages,
                    tools=TOOLS,
                    tool_choice="auto",
                    max_tokens=300,
                    temperature=0.1,
                )
            except asyncio.TimeoutError:
                final_answer = _fallback_from_tool_results(last_tool_results) or "That took too long. Please try your question again."
                break
            except Exception as e:
                logger.error({"event": "groq_error", "round": round_num, "error": str(e)})
                final_answer = _fallback_from_tool_results(last_tool_results) or _groq_rate_limit_message(e) or "Could not process that. Please try again."
                break

            msg = response.choices[0].message

            if not msg.tool_calls:
                final_answer = msg.content or _fallback_from_tool_results(last_tool_results) or "Could you rephrase that?"
                break

            tc_list = [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in msg.tool_calls
            ]
            messages.append({"role": "assistant", "content": msg.content, "tool_calls": tc_list})

            results = await asyncio.gather(*[
                execute_tool(tc.function.name, tc.function.arguments, session, org_context, backend)
                for tc in msg.tool_calls
            ], return_exceptions=True)

            last_tool_results = []
            for tc, result in zip(msg.tool_calls, results):
                if isinstance(result, Exception):
                    result = {"status": "error", "message": str(result)}

                if isinstance(result, dict) and result.get("speech"):
                    result["_voice_hint"] = result["speech"]

                last_tool_results.append((tc.function.name, result))
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(_compact_tool_result(tc.function.name, result))
                })

            session.last_tool_called = msg.tool_calls[-1].function.name if msg.tool_calls else session.last_tool_called

            direct_tool_answer = _prefer_direct_tool_answer(last_tool_results)
            if direct_tool_answer:
                final_answer = direct_tool_answer
                break

        if final_answer is None:
            try:
                final_r = await _call_groq_with_failover(
                    groq_clients,
                    api_keys,
                    timeout_seconds=8.0,
                    model=settings.GROQ_VOICE_FINAL_MODEL,
                    messages=messages,
                    max_tokens=350,
                    temperature=0.1,
                )
                final_answer = final_r.choices[0].message.content or _fallback_from_tool_results(last_tool_results) or "Done."
            except Exception as e:
                logger.error({"event": "final_groq_error", "error": str(e)})
                final_answer = _fallback_from_tool_results(last_tool_results) or _groq_rate_limit_message(e) or "I have processed your request."
    finally:
        await _close_groq_clients(groq_clients)

    # Update history
    session.history.append({"role": "user", "content": text})
    session.history.append({"role": "assistant", "content": final_answer})
    if len(session.history) > 20:
        session.history = session.history[-20:]

    # TTS sanitize
    voice_response = sanitize_for_tts(final_answer) if is_voice else final_answer

    logger.info({
        "event": "voice_process_complete",
        "session_id": session.session_id,
        "success": True,
        "tool_called": session.last_tool_called,
        "response_words": len(voice_response.split())
    })

    return {
        "response_text": voice_response,
        "raw_response": final_answer,
        "intent": "INTELLIGENT_QUERY",
        "success": True,
        "session_id": session.session_id,
        "tool_called": session.last_tool_called
    }
