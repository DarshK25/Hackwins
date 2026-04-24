"""
Finance Agent - Handles financial operations and strategic planning.
"""
import re
import uuid
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from app.adapters.backend_adapter import get_backend_adapter
from app.agents.base_agent import BaseAgent, ToolDefinition, AgentResponse
from app.models.draft import InvoiceDraft
from app.schemas.intents import Intent, AgentType
from app.tools.tool_registry import Tool, tool_registry
from app.utils.date_parser import parse_relative_date
from app.utils.logger import get_logger

logger = get_logger(__name__)
GENERIC_ITEM_WORDS = {"product", "service", "invoice", "item", "goods"}
EXPENSE_CATEGORY_ALIASES = {
    "office supplies": "Office",
    "office": "Office",
    "supplies": "Office",
    "marketing": "Marketing",
    "advertising": "Marketing",
    "ads": "Marketing",
    "salary": "Salaries",
    "salaries": "Salaries",
    "payroll": "Salaries",
    "utilities": "Utilities",
    "utility": "Utilities",
    "electricity": "Utilities",
    "internet": "Utilities",
    "travel": "Travel",
    "trip": "Travel",
    "hotel": "Travel",
    "software": "Software",
    "subscription": "Software",
    "saas": "Software",
    "hardware": "Hardware",
    "laptop": "Hardware",
    "device": "Hardware",
    "legal": "Legal",
    "lawyer": "Legal",
    "taxes": "Taxes",
    "tax": "Taxes",
    "gst": "Taxes",
    "other": "Other",
}


class FinanceAgent(BaseAgent):
    def __init__(self):
        self.backend = get_backend_adapter()
        super().__init__()
        self._register_legacy_tools()

    def get_agent_type(self) -> AgentType:
        return AgentType.FINANCE_AGENT

    def get_supported_intents(self) -> List[Intent]:
        return [
            Intent.INVOICE_CREATE,
            Intent.INVOICE_UPDATE,
            Intent.INVOICE_QUERY,
            Intent.EXPENSE_CREATE,
            Intent.EXPENSE_QUERY,
            Intent.BUSINESS_HEALTH_CHECK,
            Intent.PROBLEM_DIAGNOSIS,
            Intent.ANALYTICS_QUERY,
            Intent.BALANCE_CHECK,
            Intent.PAYMENT_RECORD,
        ]

    def get_tools(self) -> List[ToolDefinition]:
        return [
            ToolDefinition(name="query_invoices", description="Search/list invoices", parameters={}, mvp_ready=True),
            ToolDefinition(name="query_expenses", description="Expense totals and category summaries", parameters={}, mvp_ready=True),
            ToolDefinition(name="check_balance", description="Get balance summary", parameters={}, mvp_ready=True),
            ToolDefinition(name="analytics_query", description="Financial metrics", parameters={}, mvp_ready=True),
            ToolDefinition(name="calculate_business_health_score", description="Calculate business health score", parameters={}, mvp_ready=True),
        ]

    def _register_legacy_tools(self):
        tool_registry.register_tools([
            Tool(name="query_invoices", description="Search/list invoices", category="finance", mvp_ready=True, handler=self._handle_query_invoices),
            Tool(name="query_expenses", description="Expense totals and category summaries", category="finance", mvp_ready=True, handler=self._handle_expense_query),
            Tool(name="check_balance", description="Get balance summary", category="finance", mvp_ready=True, handler=self._handle_check_balance),
            Tool(name="analytics_query", description="Financial metrics", category="finance", mvp_ready=True, handler=self._handle_analytics_query),
            Tool(name="calculate_business_health_score", description="Strategic health score", category="finance", mvp_ready=True, handler=self._handle_business_health_score),
        ])

    async def handle_invoice_create(self, context) -> AgentResponse:
        from app.state.session_manager import session_manager

        session = session_manager.get_session(context.session_id, context.user_id, context.org_uuid)
        draft = session.invoice_draft or InvoiceDraft(draft_id=str(uuid.uuid4()), session_id=context.session_id)
        draft.turn_count += 1

        # ── AGENT LOCKING: Lock this session to FINANCE_AGENT ────────────────────────
        if not session.locked_agent_type:
            session.locked_agent_type = "FINANCE_AGENT"
            logger.info({
                "event": "agent_locked_to_session",
                "session_id": context.session_id,
                "agent_type": "FINANCE_AGENT"
            })

        raw_text = (getattr(context, "raw_text", None) or "").strip()
        await self._merge_invoice_entities_and_text(draft, context, raw_text)

        session.invoice_draft = draft
        session.locked_intent = "INVOICE_CREATE"
        session_manager.save_session(session)

        logger.info({
            "event": "invoice_draft_state",
            "client_name": draft.client_name,
            "client_id": draft.client_id,
            "amount": draft.amount,
            "item_type": draft.item_type,
            "item_description": draft.item_description,
            "quantity": draft.quantity,
            "gst_percent": draft.gst_percent,
            "due_date": draft.due_date,
            "awaiting_confirmation": draft.awaiting_confirmation,
            "awaiting_team_code": draft.awaiting_team_code,
            "team_code_attempts": draft.team_code_attempts,
        })

        if draft.awaiting_confirmation:
            if self._is_negative_response(raw_text):
                session.invoice_draft = None
                session.locked_intent = None
                session_manager.save_session(session)
                return AgentResponse(
                    success=True,
                    message="Okay, I cancelled the invoice creation.",
                    agent_type=self.get_agent_type(),
                )

            if self._is_positive_response(raw_text):
                draft.confirmed = True
                draft.awaiting_confirmation = False
                draft.awaiting_team_code = True
                draft.last_question_asked = "team_code"
                session.invoice_draft = draft
                session_manager.save_session(session)
                return AgentResponse(
                    success=True,
                    message="Please tell me the team security code to create this invoice.",
                    ui_event={
                        "type": "progress",
                        "variant": "warning",
                        "title": "Team Security Code",
                        "message": "Waiting for team security code",
                    },
                    agent_type=self.get_agent_type(),
                )

            return AgentResponse(
                success=True,
                message="Please say yes to create the invoice or no to cancel it.",
                agent_type=self.get_agent_type(),
            )

        if draft.awaiting_team_code:
            return await self._finalize_and_create_invoice(draft, context)

        if not draft.client_id:
            clients = await self.backend.get_clients(context.org_uuid, user_id=context.user_id)
            if not clients:
                return AgentResponse(
                    success=False,
                    message="I could not load your client list right now. Please try again in a moment.",
                    ui_event={"type": "toast", "variant": "warning", "title": "Client lookup failed", "message": "Backend client list unavailable"},
                    agent_type=self.get_agent_type(),
                )

            names = [client.get("name") for client in clients[:6] if client.get("name")]
            if draft.client_name:
                return AgentResponse(
                    success=True,
                    message=f"I could not find a client named {draft.client_name}. I can create invoices only for existing clients. Please choose one of these clients: {', '.join(names)}.",
                    ui_event={
                        "type": "open_client_picker",
                        "session_id": context.session_id,
                        "title": "Select Client",
                        "message": "Choose an existing client or continue by voice.",
                        "clients": [{"id": client.get("id"), "name": client.get("name")} for client in clients[:10] if client.get("name")],
                    },
                    agent_type=self.get_agent_type(),
                )

            draft.last_question_asked = "client"
            session.invoice_draft = draft
            session_manager.save_session(session)
            return AgentResponse(
                success=True,
                message=f"Which client should I use for the invoice? Your existing clients are: {', '.join(names)}.",
                ui_event={
                    "type": "open_client_picker",
                    "session_id": context.session_id,
                    "title": "Select Client",
                    "message": "Choose an existing client or continue by voice.",
                    "clients": [{"id": client.get("id"), "name": client.get("name")} for client in clients[:10] if client.get("name")],
                },
                agent_type=self.get_agent_type(),
            )

        if draft.amount is None:
            draft.last_question_asked = "amount"
            session.invoice_draft = draft
            session_manager.save_session(session)
            return AgentResponse(
                success=True,
                message=f"What amount should I use for the invoice for {draft.client_name}?",
                ui_event={"type": "progress", "variant": "info", "title": "Create Invoice", "message": "Step 2 of 6: amount"},
                agent_type=self.get_agent_type(),
            )

        if not draft.item_type:
            draft.last_question_asked = "item_type"
            session.invoice_draft = draft
            session_manager.save_session(session)
            return AgentResponse(
                success=True,
                message="Is this invoice for a product or a service?",
                ui_event={"type": "progress", "variant": "info", "title": "Create Invoice", "message": "Step 3 of 6: product or service"},
                agent_type=self.get_agent_type(),
            )

        if not draft.item_description:
            draft.last_question_asked = "item_description"
            session.invoice_draft = draft
            session_manager.save_session(session)
            prompt = "Which service is this invoice for?" if draft.item_type == "SERVICE" else "What product is this invoice for?"
            return AgentResponse(
                success=True,
                message=prompt,
                ui_event={"type": "progress", "variant": "info", "title": "Create Invoice", "message": "Describe the billed item"},
                agent_type=self.get_agent_type(),
            )

        if draft.item_type == "PRODUCT" and (draft.quantity is None or draft.quantity <= 0):
            draft.last_question_asked = "quantity"
            session.invoice_draft = draft
            session_manager.save_session(session)
            return AgentResponse(
                success=True,
                message="What quantity should I use for this product invoice?",
                ui_event={"type": "progress", "variant": "info", "title": "Create Invoice", "message": "Quantity required"},
                agent_type=self.get_agent_type(),
            )

        if draft.gst_applicable is None:
            draft.last_question_asked = "gst"
            session.invoice_draft = draft
            session_manager.save_session(session)
            return AgentResponse(
                success=True,
                message="Should I apply GST to this invoice?",
                ui_event={"type": "progress", "variant": "info", "title": "Create Invoice", "message": "Step 4 of 6: GST"},
                agent_type=self.get_agent_type(),
            )

        if not draft.due_date:
            draft.last_question_asked = "due_date"
            session.invoice_draft = draft
            session_manager.save_session(session)
            return AgentResponse(
                success=True,
                message="What is the due date for this invoice?",
                ui_event={"type": "progress", "variant": "info", "title": "Create Invoice", "message": "Step 5 of 6: due date"},
                agent_type=self.get_agent_type(),
            )

        due_date_error = self._get_due_date_validation_error(draft.due_date)
        if due_date_error:
            return self._reprompt_for_due_date(draft, context, due_date_error)

        subtotal, gst_total, total_amount = self._calculate_invoice_totals(draft)
        summary = self._build_invoice_summary(draft, subtotal, gst_total, total_amount)
        draft.awaiting_confirmation = True
        draft.last_summary = summary
        session.invoice_draft = draft
        session_manager.save_session(session)

        return AgentResponse(
            success=True,
            message=summary + " Should I create this invoice?",
            ui_event={"type": "progress", "variant": "info", "title": "Create Invoice", "message": "Step 6 of 6: confirmation"},
            agent_type=self.get_agent_type(),
        )

    async def _finalize_and_create_invoice(self, draft: InvoiceDraft, context) -> AgentResponse:
        from app.state.session_manager import session_manager

        raw_text = (getattr(context, "raw_text", None) or "").strip()
        extracted_code = self._extract_team_code(raw_text)
        if extracted_code:
            draft.team_action_code = extracted_code

        due_date_error = self._get_due_date_validation_error(draft.due_date)
        if due_date_error:
            return self._reprompt_for_due_date(draft, context, due_date_error)

        if not draft.team_action_code:
            return AgentResponse(
                success=True,
                message="Please tell me the team security code to create this invoice.",
                ui_event={"type": "progress", "variant": "warning", "title": "Team Security Code", "message": "Waiting for team security code"},
                agent_type=self.get_agent_type(),
            )

        code_check = await self.backend.validate_team_action_code(context.org_uuid, context.user_id, draft.team_action_code)
        if not code_check.success:
            draft.team_code_attempts += 1
            draft.team_action_code = None

            if draft.team_code_attempts >= 2:
                session = session_manager.get_session(context.session_id, context.user_id, context.org_uuid)
                session.invoice_draft = None
                session.locked_intent = None
                session_manager.save_session(session)
                return AgentResponse(
                    success=True,
                    message="The team security code was incorrect again, so I cancelled the invoice creation.",
                    ui_event={"type": "toast", "variant": "error", "title": "Invoice cancelled", "message": "Two invalid code attempts"},
                    agent_type=self.get_agent_type(),
                )

            session = session_manager.get_session(context.session_id, context.user_id, context.org_uuid)
            session.invoice_draft = draft
            session.locked_intent = "INVOICE_CREATE"
            session_manager.save_session(session)
            return AgentResponse(
                success=True,
                message="That team security code was incorrect. Please say the code one more time.",
                ui_event={"type": "toast", "variant": "warning", "title": "Invalid code", "message": "One attempt remaining"},
                agent_type=self.get_agent_type(),
            )

        subtotal, gst_total, total_amount = self._calculate_invoice_totals(draft)
        payload = {
            "clientId": draft.client_id,
            "clientName": draft.client_name,
            "subtotal": subtotal,
            "gstTotal": gst_total,
            "totalAmount": total_amount,
            "dueDate": draft.due_date,
            "issueDate": datetime.now().strftime("%Y-%m-%d"),
            "status": "DRAFT",
            "currency": "INR",
            "items": [{
                "type": draft.item_type,
                "description": draft.item_description,
                "quantity": None if draft.item_type == "SERVICE" else draft.quantity,
                "rate": draft.amount,
                "gstPercent": draft.gst_percent or 0,
                "lineSubtotal": subtotal,
                "lineGst": gst_total,
                "lineTotal": total_amount,
            }],
            "notes": "Created via MoneyOps voice agent",
            "teamActionCode": draft.team_action_code,
            "source": "VOICE",
        }

        try:
            response = await self.backend.create_invoice_direct(context.org_uuid, context.user_id, payload)
            if not response.success:
                backend_error = response.error or "Invoice creation failed"
                if "due date cannot be before issue date" in backend_error.lower():
                    return self._reprompt_for_due_date(
                        draft,
                        context,
                        self._get_due_date_validation_error(draft.due_date)
                        or "That due date is before the invoice issue date. Please tell me a future due date.",
                    )
                raise RuntimeError(backend_error)

            invoice = response.data
            invoice_number = invoice.get("invoiceNumber", "N/A")
            invoice_id = invoice.get("id", "")

            session = session_manager.get_session(context.session_id, context.user_id, context.org_uuid)
            session.invoice_draft = None
            session.locked_intent = None
            session_manager.save_session(session)

            return AgentResponse(
                success=True,
                message=f"Invoice {invoice_number} was created for {draft.client_name}. Final amount is rupees {total_amount:,.0f} and the due date is {draft.due_date}.",
                ui_event={
                    "type": "invoice_created",
                    "invoice_id": invoice_id,
                    "invoice_number": invoice_number,
                    "client_name": draft.client_name,
                    "total": total_amount,
                    "due_date": draft.due_date,
                },
                agent_type=self.get_agent_type(),
            )
        except Exception as exc:
            logger.error("invoice_create_failed", error=str(exc))
            return self._build_error_response(str(exc))

    async def _merge_invoice_entities_and_text(self, draft: InvoiceDraft, context, raw_text: str) -> None:
        text_lower = raw_text.lower()

        if "service" in text_lower and "product" not in text_lower:
            draft.item_type = "SERVICE"
        elif "product" in text_lower:
            draft.item_type = "PRODUCT"

        if draft.gst_applicable is None:
            if draft.last_question_asked == "gst":
                if self._is_positive_response(raw_text):
                    draft.gst_applicable = True
                    draft.gst_percent = 18.0
                elif self._is_negative_response(raw_text):
                    draft.gst_applicable = False
                    draft.gst_percent = 0.0

        if draft.gst_applicable is None:
            if re.search(r"\b(no gst|without gst|dont apply gst|don't apply gst|no tax)\b", text_lower):
                draft.gst_applicable = False
                draft.gst_percent = 0.0
            elif re.search(r"\b(add gst|apply gst|with gst|yes gst)\b", text_lower):
                draft.gst_applicable = True
                draft.gst_percent = 18.0

        if draft.item_type == "PRODUCT" and draft.quantity is None:
            quantity_match = (
                re.search(r"\bquantity\s*(?:is\s*)?(\d+)\b", text_lower)
                or re.search(r"\b(\d+)\s+(?:units?|items?|pieces?|qty|quantity)\b", text_lower)
            )
            if quantity_match:
                draft.quantity = int(quantity_match.group(1))

        for entity in (context.extracted_entities or []):
            entity_type = (entity.get("type") or "").lower().strip()
            value = entity.get("value")
            if value is None or value == "":
                continue

            if entity_type in ("client_name", "client", "company_name") and not draft.client_id:
                draft.client_name = str(value).strip()
                draft.client_query = draft.client_name
            elif entity_type in ("amount", "total") and draft.amount is None:
                parsed_amount = self._extract_amount(value)
                if parsed_amount is not None:
                    draft.amount = parsed_amount
            elif entity_type in ("due_date", "date", "deadline", "time_period") and not draft.due_date:
                due_date = self._normalize_due_date(value, raw_text=raw_text)
                if due_date:
                    draft.due_date = due_date
            elif entity_type in ("due_days", "days", "duration") and not draft.due_date:
                due_date = self._due_date_from_days(value)
                if due_date:
                    draft.due_date = due_date
            elif entity_type in ("gst_percent", "gst", "tax_percent", "percentage", "gst_percentage") and draft.gst_applicable is None:
                try:
                    gst_value = float(str(value).replace("%", "").strip())
                    draft.gst_percent = gst_value
                    draft.gst_applicable = gst_value > 0
                except Exception:
                    pass

        if draft.last_question_asked == "amount" and draft.amount is None:
            parsed_amount = self._extract_amount(raw_text)
            if parsed_amount is not None:
                draft.amount = parsed_amount

        if draft.amount is None:
            draft.amount = self._extract_amount(raw_text)

        if not draft.due_date:
            draft.due_date = self._extract_due_date_from_text(text_lower)

        if draft.last_question_asked == "quantity" and draft.item_type == "PRODUCT" and draft.quantity is None:
            bare_number = self._extract_integer(raw_text)
            if bare_number is not None and bare_number > 0:
                draft.quantity = bare_number

        if draft.last_question_asked == "item_description" and not draft.item_description:
            cleaned = raw_text.strip(" .")
            if cleaned and not self._looks_like_noise(cleaned) and cleaned.lower() not in GENERIC_ITEM_WORDS:
                draft.item_description = cleaned

        if draft.item_type and not draft.item_description:
            draft.item_description = self._extract_item_description(raw_text, draft.item_type)

        if draft.awaiting_team_code and not draft.team_action_code:
            draft.team_action_code = self._extract_team_code(raw_text)

        if draft.client_name and not draft.client_id:
            client = await self._resolve_client(draft.client_name, context.org_uuid, context.user_id)
            if client:
                draft.client_id = client.get("id")
                draft.client_name = client.get("name")

    async def _resolve_client(self, spoken_name: str, org_uuid: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        clients = await self.backend.get_clients(org_uuid, user_id=user_id)
        if not clients or not spoken_name:
            return None

        def normalize(value: str) -> str:
            return re.sub(r"[^a-z0-9]", "", str(value).lower())

        spoken_norm = normalize(spoken_name)
        for client in clients:
            if normalize(client.get("name") or "") == spoken_norm:
                return client

        for client in clients:
            client_norm = normalize(client.get("name") or "")
            if spoken_norm in client_norm or client_norm in spoken_norm:
                return client

        spoken_words = set(spoken_name.lower().split())
        best_match = None
        best_score = 0
        for client in clients:
            client_words = set((client.get("name") or "").lower().split())
            score = len(spoken_words & client_words)
            if score > best_score:
                best_score = score
                best_match = client

        return best_match if best_score >= 1 else None

    def _extract_amount(self, value: Any) -> Optional[float]:
        if value is None:
            return None
        cleaned = re.sub(r"[^0-9.]", "", str(value))
        if not cleaned:
            return None
        try:
            amount = float(cleaned)
            return amount if amount > 0 else None
        except Exception:
            return None

    def _normalize_due_date(self, value: Any, raw_text: Optional[str] = None) -> Optional[str]:
        value_str = str(value).strip()
        raw_text = (raw_text or "").strip()

        if re.match(r"^\d{4}-\d{2}-\d{2}$", value_str):
            parsed = self._parse_iso_date(value_str)
            if parsed and parsed < datetime.now().date() and not self._raw_text_has_explicit_year(raw_text):
                future_from_raw = parse_relative_date(raw_text or value_str, prefer_future=True)
                if future_from_raw:
                    return future_from_raw
            return value_str

        parsed = parse_relative_date(value_str, prefer_future=True)
        if parsed:
            return parsed

        if raw_text:
            return parse_relative_date(raw_text, prefer_future=True)

        return None

    def _due_date_from_days(self, value: Any) -> Optional[str]:
        try:
            days = int(re.sub(r"[^0-9]", "", str(value)))
        except Exception:
            return None
        if days < 1 or days > 365:
            return None
        return (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")

    def _extract_due_date_from_text(self, text_lower: str) -> Optional[str]:
        parsed = parse_relative_date(text_lower, prefer_future=True)
        if parsed:
            return parsed

        if "tomorrow" in text_lower:
            return (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        match = re.search(r"\bin\s+(\d{1,3})\s+days?\b", text_lower)
        if match:
            return self._due_date_from_days(match.group(1))
        return None

    def _parse_iso_date(self, value: str) -> Optional[date]:
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            return None

    def _raw_text_has_explicit_year(self, raw_text: str) -> bool:
        return bool(re.search(r"\b\d{4}\b", raw_text or ""))

    def _get_due_date_validation_error(self, due_date: Optional[str]) -> Optional[str]:
        parsed_due_date = self._parse_iso_date(due_date or "")
        if not parsed_due_date:
            return "I could not understand the due date. Please tell me a specific future due date."

        today = datetime.now().date()
        if parsed_due_date < today:
            return (
                f"The due date {parsed_due_date.isoformat()} is before today {today.isoformat()}. "
                "Please tell me a future due date for this invoice."
            )

        return None

    def _reprompt_for_due_date(self, draft: InvoiceDraft, context, message: str) -> AgentResponse:
        from app.state.session_manager import session_manager

        draft.due_date = None
        draft.last_question_asked = "due_date"

        session = session_manager.get_session(context.session_id, context.user_id, context.org_uuid)
        session.invoice_draft = draft
        session.locked_intent = "INVOICE_CREATE"
        session_manager.save_session(session)

        return AgentResponse(
            success=True,
            message=message,
            ui_event={
                "type": "progress",
                "variant": "warning",
                "title": "Future Due Date Required",
                "message": "Please provide a due date on or after today.",
            },
            agent_type=self.get_agent_type(),
        )

    def _extract_item_description(self, raw_text: str, item_type: str) -> Optional[str]:
        if not raw_text:
            return None
        cleaned_text = raw_text.strip(" .")
        if cleaned_text.lower() in GENERIC_ITEM_WORDS:
            return None
        patterns = [
            r"\bfor\s+(?:a\s+|an\s+)?(?:product|service)\s+(?:called\s+)?(.+)$",
            r"\bservice\s+(?:is|for)\s+(.+)$",
            r"\bproduct\s+(?:is|for)\s+(.+)$",
            r"\bfor\s+(.+)$",
        ]
        for pattern in patterns:
            match = re.search(pattern, raw_text, flags=re.IGNORECASE)
            if not match:
                continue
            description = match.group(1).strip(" .")
            description = re.sub(r"\b(with gst|without gst|quantity\s+\d+|qty\s+\d+|due\s+.*)$", "", description, flags=re.IGNORECASE).strip(" .")
            if description and description.lower() not in GENERIC_ITEM_WORDS:
                return description

        if len(raw_text.split()) <= 8 and not self._looks_like_noise(raw_text) and cleaned_text.lower() not in GENERIC_ITEM_WORDS:
            return cleaned_text
        return None

    def _extract_team_code(self, raw_text: str) -> Optional[str]:
        if not raw_text:
            return None
        match = re.search(r"\b(?:code|pin|security code)\s*(?:is\s*)?([A-Za-z0-9-]{4,12})\b", raw_text, flags=re.IGNORECASE)
        if match:
            return match.group(1)
        compact = re.sub(r"\s+", "", raw_text)
        if re.fullmatch(r"[A-Za-z0-9-]{4,12}", compact):
            return compact
        return None

    def _extract_integer(self, raw_text: str) -> Optional[int]:
        if not raw_text:
            return None
        match = re.search(r"\b(\d+)\b", raw_text)
        if not match:
            return None
        try:
            return int(match.group(1))
        except Exception:
            return None

    def _looks_like_noise(self, raw_text: str) -> bool:
        return raw_text.strip().lower() in {"hello", "hi", "hey", "okay", "ok", "hmm", "huh"}

    def _calculate_invoice_totals(self, draft: InvoiceDraft) -> tuple[float, float, float]:
        quantity = draft.quantity if draft.item_type == "PRODUCT" else 1
        subtotal = round((draft.amount or 0) * quantity, 2)
        gst_total = round(subtotal * ((draft.gst_percent or 0) / 100), 2)
        total_amount = round(subtotal + gst_total, 2)
        return subtotal, gst_total, total_amount

    def _build_invoice_summary(self, draft: InvoiceDraft, subtotal: float, gst_total: float, total_amount: float) -> str:
        if draft.item_type == "SERVICE":
            item_text = f"for the service {draft.item_description}"
        else:
            item_text = f"for the product {draft.item_description}, quantity {draft.quantity}, at rupees {draft.amount:,.0f} each"
        gst_text = f"GST of rupees {gst_total:,.0f} is included" if gst_total > 0 else "GST is not applied"
        return (
            f"I have prepared an invoice for {draft.client_name} {item_text}. "
            f"The subtotal is rupees {subtotal:,.0f}, {gst_text}, the final amount is rupees {total_amount:,.0f}, and the due date is {draft.due_date}."
        )

    def _is_positive_response(self, raw_text: str) -> bool:
        return bool(re.search(r"\b(yes|yeah|yep|sure|okay|ok|go ahead|proceed|confirm)\b", raw_text.lower()))

    def _is_negative_response(self, raw_text: str) -> bool:
        return bool(re.search(r"\b(no|cancel|stop|abort|don't|dont|not now)\b", raw_text.lower()))

    async def handle_expense_create(self, context) -> AgentResponse:
        from app.state.session_manager import session_manager

        session = session_manager.get_session(context.session_id, context.user_id, context.org_uuid)
        draft = dict(session.expense_draft or {})
        raw_text = (getattr(context, "raw_text", None) or "").strip()

        if not session.locked_agent_type:
            session.locked_agent_type = "FINANCE_AGENT"

        self._merge_expense_entities_and_text(draft, context, raw_text)
        if not draft.get("date"):
            draft["date"] = datetime.now().strftime("%Y-%m-%d")

        session.expense_draft = draft
        session.locked_intent = "EXPENSE_CREATE"
        session_manager.save_session(session)

        if self._is_negative_response(raw_text):
            session.expense_draft = None
            session.locked_intent = None
            session_manager.save_session(session)
            return AgentResponse(
                success=True,
                message="Okay, I cancelled the expense entry.",
                agent_type=self.get_agent_type(),
            )

        if draft.get("amount") is None:
            draft["last_question_asked"] = "amount"
            session.expense_draft = draft
            session_manager.save_session(session)
            return AgentResponse(
                success=True,
                message="What amount should I record for this expense?",
                agent_type=self.get_agent_type(),
            )

        if not draft.get("category"):
            draft["last_question_asked"] = "category"
            session.expense_draft = draft
            session_manager.save_session(session)
            categories = ", ".join(sorted(set(EXPENSE_CATEGORY_ALIASES.values())))
            return AgentResponse(
                success=True,
                message=f"Which category should I use? You can say {categories}.",
                agent_type=self.get_agent_type(),
            )

        if not draft.get("description"):
            draft["last_question_asked"] = "description"
            session.expense_draft = draft
            session_manager.save_session(session)
            return AgentResponse(
                success=True,
                message=f"What short description should I save for this {draft.get('category')} expense?",
                agent_type=self.get_agent_type(),
            )

        if draft.get("awaiting_team_code") and not draft.get("teamActionCode"):
            draft["teamActionCode"] = self._extract_team_code(raw_text)

        if not draft.get("teamActionCode"):
            draft["awaiting_team_code"] = True
            draft["last_question_asked"] = "team_code"
            session.expense_draft = draft
            session_manager.save_session(session)
            return AgentResponse(
                success=True,
                message="Please tell me the team security code to record this expense.",
                ui_event={"type": "progress", "variant": "warning", "title": "Team Security Code", "message": "Waiting for team security code"},
                agent_type=self.get_agent_type(),
            )

        code_check = await self.backend.validate_team_action_code(context.org_uuid, context.user_id, draft.get("teamActionCode"))
        if not code_check.success:
            attempts = int(draft.get("team_code_attempts") or 0) + 1
            draft["team_code_attempts"] = attempts
            draft["teamActionCode"] = None

            if attempts >= 2:
                session.expense_draft = None
                session.locked_intent = None
                session_manager.save_session(session)
                return AgentResponse(
                    success=True,
                    message="The team security code was incorrect again, so I cancelled the expense entry.",
                    ui_event={"type": "toast", "variant": "error", "title": "Expense cancelled", "message": "Two invalid code attempts"},
                    agent_type=self.get_agent_type(),
                )

            session.expense_draft = draft
            session.locked_intent = "EXPENSE_CREATE"
            session_manager.save_session(session)
            return AgentResponse(
                success=True,
                message="That team security code was incorrect. Please say the code one more time.",
                ui_event={"type": "toast", "variant": "warning", "title": "Invalid code", "message": "One attempt remaining"},
                agent_type=self.get_agent_type(),
            )

        draft["awaiting_team_code"] = False
        session.expense_draft = draft
        session_manager.save_session(session)

        payload = {
            "amount": draft.get("amount"),
            "category": draft.get("category"),
            "description": draft.get("description"),
            "date": draft.get("date"),
            "paymentMethod": draft.get("payment_method"),
            "receiptUrl": draft.get("receipt_url"),
            "teamActionCode": draft.get("teamActionCode"),
            "voiceContext": {
                "sessionId": context.session_id,
                "recordedViaVoice": True,
                "transcript": raw_text or draft.get("description"),
            },
        }

        try:
            response = await self.backend.create_expense(context.org_uuid, context.user_id, payload)
            if not response.success:
                raise RuntimeError(response.error or "Expense creation failed")

            expense = response.data or {}
            session.expense_draft = None
            session.locked_intent = None
            session_manager.save_session(session)

            amount_text = f"Rs {float(draft.get('amount') or 0):,.0f}"
            description_text = draft.get("description") or draft.get("category") or "expense"
            return AgentResponse(
                success=True,
                message=f"I've recorded an expense of {amount_text} for {description_text}.",
                ui_event={
                    "type": "expense_created",
                    "expense_id": expense.get("id"),
                    "amount": draft.get("amount"),
                    "category": draft.get("category"),
                    "description": draft.get("description"),
                    "date": draft.get("date"),
                },
                agent_type=self.get_agent_type(),
            )
        except Exception as exc:
            logger.error("expense_create_failed", error=str(exc))
            return self._build_error_response(str(exc))

    def _merge_expense_entities_and_text(self, draft: Dict[str, Any], context, raw_text: str) -> None:
        text_lower = (raw_text or "").lower()

        for entity in (getattr(context, "extracted_entities", None) or []):
            entity_type = (entity.get("type") or "").lower().strip()
            value = entity.get("value")
            if value in (None, ""):
                continue

            if entity_type in ("amount", "total") and draft.get("amount") is None:
                parsed_amount = self._extract_amount(value)
                if parsed_amount is not None:
                    draft["amount"] = parsed_amount
            elif entity_type in ("date", "time_period", "due_date") and not draft.get("date"):
                parsed_date = self._normalize_expense_date(value, raw_text)
                if parsed_date:
                    draft["date"] = parsed_date

        if draft.get("last_question_asked") == "amount" and draft.get("amount") is None:
            parsed_amount = self._extract_amount(raw_text)
            if parsed_amount is not None:
                draft["amount"] = parsed_amount

        if draft.get("amount") is None:
            parsed_amount = self._extract_amount(raw_text)
            if parsed_amount is not None:
                draft["amount"] = parsed_amount

        if not draft.get("category"):
            draft["category"] = self._extract_expense_category(raw_text)
        if draft.get("last_question_asked") == "category" and not draft.get("category"):
            draft["category"] = self._normalize_expense_category(raw_text)

        if not draft.get("description"):
            draft["description"] = self._extract_expense_description(raw_text)
        if draft.get("last_question_asked") == "description" and not draft.get("description"):
            cleaned = raw_text.strip(" .")
            if cleaned and not self._looks_like_noise(cleaned):
                draft["description"] = cleaned

        if not draft.get("payment_method"):
            draft["payment_method"] = self._extract_payment_method(raw_text)
        if not draft.get("date"):
            draft["date"] = self._normalize_expense_date(raw_text, raw_text)

    def _normalize_expense_category(self, raw_text: str) -> Optional[str]:
        cleaned = (raw_text or "").strip().lower()
        if not cleaned:
            return None
        for alias, category in sorted(EXPENSE_CATEGORY_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
            if cleaned == alias or cleaned == category.lower():
                return category
        return None

    def _extract_expense_category(self, raw_text: str) -> Optional[str]:
        text_lower = (raw_text or "").lower()
        for alias, category in sorted(EXPENSE_CATEGORY_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
            if alias in text_lower:
                return category
        return None

    def _extract_expense_description(self, raw_text: str) -> Optional[str]:
        if not raw_text:
            return None

        patterns = [
            r"(?:expense|spent|record expense|add expense|log expense)\s+(?:of\s+)?(?:rupees|rs\.?|inr)?\s*[0-9,\.]+\s+(?:for|on)\s+(.+)$",
            r"(?:for|on)\s+(.+)$",
        ]
        for pattern in patterns:
            match = re.search(pattern, raw_text, flags=re.IGNORECASE)
            if not match:
                continue
            description = match.group(1).strip(" .")
            description = re.sub(r"\b(?:today|yesterday|tomorrow|this month|this quarter|this year|last month)\b.*$", "", description, flags=re.IGNORECASE).strip(" .")
            description = re.sub(r"\b(?:paid|payment)\s+(?:by|via)\s+.+$", "", description, flags=re.IGNORECASE).strip(" .")
            if description and not self._looks_like_noise(description):
                return description

        cleaned = raw_text.strip(" .")
        return cleaned if cleaned and len(cleaned.split()) <= 6 and not self._looks_like_noise(cleaned) else None

    def _normalize_expense_date(self, value: Any, raw_text: Optional[str] = None) -> Optional[str]:
        value_str = str(value or "").strip()
        raw = (raw_text or "").strip()

        if re.match(r"^\d{4}-\d{2}-\d{2}$", value_str):
            return value_str

        parsed = parse_relative_date(value_str, prefer_future=False)
        if parsed:
            return parsed

        if raw:
            return parse_relative_date(raw, prefer_future=False)

        return None

    def _extract_payment_method(self, raw_text: str) -> Optional[str]:
        if not raw_text:
            return None
        text_lower = raw_text.lower()
        if "upi" in text_lower:
            return "UPI"
        if "cash" in text_lower:
            return "CASH"
        if "card" in text_lower or "credit card" in text_lower or "debit card" in text_lower:
            return "CARD"
        if "bank transfer" in text_lower or "transfer" in text_lower or "neft" in text_lower or "rtgs" in text_lower:
            return "BANK_TRANSFER"
        return None

    async def _handle_expense_query(self, params, context=None):
        safe_context = context or {}
        org_uuid = safe_context.get("org_uuid") or safe_context.get("org_id")
        user_id = safe_context.get("user_id")
        raw_text = (safe_context.get("raw_text") or "").strip()

        if not org_uuid:
            return {"message": "I couldn't identify your business context for that expense query."}

        category = self._extract_expense_category(raw_text)
        period = self._extract_expense_period(raw_text)
        response = await self.backend.get_expense_summary(
            org_uuid,
            period=period,
            category=category,
            user_id=user_id,
        )
        if not response.success or not response.data:
            return {"message": "I couldn't retrieve your expense summary right now."}

        summary = response.data
        total_expenses = float(summary.get("totalExpenses") or 0)
        by_category = summary.get("byCategory") or []
        top_expense = summary.get("topExpense") or {}

        if total_expenses <= 0:
            if category:
                return {"message": f"You don't have any {category.lower()} expenses in {self._expense_period_label(period)}."}
            return {"message": f"You don't have any recorded expenses in {self._expense_period_label(period)}."}

        if category:
            category_row = next(
                (item for item in by_category if str(item.get("category") or "").lower() == category.lower()),
                None,
            )
            category_total = float(category_row.get("total") or total_expenses) if category_row else total_expenses
            category_count = int(category_row.get("count") or 0) if category_row else 0
            message = (
                f"You spent {self._format_rupees(category_total)} on {category} {self._expense_period_label(period)}"
            )
            if category_count > 0:
                message += f" across {category_count} expense{'s' if category_count != 1 else ''}"
            if top_expense.get("description") and top_expense.get("amount"):
                message += (
                    f". The biggest recorded item was {top_expense.get('description')} for "
                    f"{self._format_rupees(top_expense.get('amount'))}"
                )
            return {"message": message + "."}

        top_categories = ", ".join(
            f"{item.get('category')} at {self._format_rupees(item.get('total'))}"
            for item in by_category[:3]
        )
        message = f"Your total expenses for {self._expense_period_label(period)} are {self._format_rupees(total_expenses)}."
        if top_categories:
            message += f" Top spending categories are {top_categories}."
        if top_expense.get("description") and top_expense.get("amount"):
            message += f" Your biggest expense was {top_expense.get('description')} for {self._format_rupees(top_expense.get('amount'))}."
        return {"message": message}

    def _extract_expense_period(self, raw_text: str) -> str:
        text_lower = (raw_text or "").lower()
        if "this year" in text_lower or "yearly" in text_lower:
            return "yearly"
        if "this quarter" in text_lower or "quarterly" in text_lower:
            return "quarterly"
        return "monthly"

    def _expense_period_label(self, period: str) -> str:
        normalized = (period or "monthly").lower()
        if normalized == "yearly":
            return "this year"
        if normalized == "quarterly":
            return "this quarter"
        return "this month"

    async def _handle_business_health_score(self, params, context=None):
        org_uuid = context.get("org_uuid") or context.get("org_id")
        business_id = context.get("business_id", "default")
        user_id = context.get("user_id")

        response = await self.backend.get_finance_metrics(business_id, org_uuid, user_id)
        if response.success and response.data:
            metrics = response.data
            revenue = metrics.get("revenue", 0)
            expenses = metrics.get("expenses", 0)
            profit = metrics.get("netProfit", 0)
            score = 75
            profit_margin = 0.0
            if revenue > 0:
                profit_margin = (profit / revenue) * 100
                score = min(100, max(0, int(50 + profit_margin)))
            return {"message": f"Your business health score is {score}/100. Net profit margin is {profit_margin:.1f}% based on revenue of rupees {revenue:,.0f}."}
        return {"message": "I could not calculate your health score right now."}

    async def _handle_query_invoices(self, params, context=None):
        safe_context = context or {}
        org_uuid = safe_context.get("org_uuid") or safe_context.get("org_id")
        user_id = safe_context.get("user_id")
        raw_text = (safe_context.get("raw_text") or "").strip()
        response = await self.backend.get_invoices(org_uuid, limit=100, user_id=user_id)
        if response.success and isinstance(response.data, list):
            invoices = response.data
            client_hint = self._extract_client_hint(params)

            if self._looks_like_invoice_breakdown_query(raw_text):
                counts_by_client: Dict[str, int] = {}
                for invoice in invoices:
                    client_name = invoice.get("clientName") or "Unknown Client"
                    counts_by_client[client_name] = counts_by_client.get(client_name, 0) + 1

                if not counts_by_client:
                    return {"message": "You don't have any invoices in the system yet."}

                preview = ", ".join(
                    f"{name} has {count} invoice{'s' if count != 1 else ''}"
                    for name, count in sorted(counts_by_client.items(), key=lambda item: (-item[1], item[0]))[:5]
                )
                return {"message": f"Invoice counts by client: {preview}."}

            if client_hint or self._looks_like_client_invoice_query(raw_text):
                resolved_client = await self._resolve_client(client_hint or raw_text, org_uuid, user_id)
                if resolved_client:
                    matched_invoices = [
                        invoice for invoice in invoices
                        if self._invoice_matches_client(invoice, resolved_client)
                    ]
                    count = len(matched_invoices)
                    return {
                        "message": (
                            f"{resolved_client.get('name', 'That client')} has {count} "
                            f"invoice{'s' if count != 1 else ''} in the system."
                        )
                    }

            return {"message": f"You have {len(invoices)} total invoices in the system."}
        return {"message": "I could not fetch your invoices right now."}

    async def _handle_check_balance(self, params, context=None):
        org_uuid = context.get("org_uuid") or context.get("org_id")
        user_id = context.get("user_id")
        response = await self.backend.get_financial_summary(org_uuid, user_id)
        if response.success and response.data:
            summary = response.data
            income = summary.get("totalIncome", 0)
            expense = summary.get("totalExpense", 0)
            net = summary.get("netProfit", 0)
            return {"message": f"Current cash summary shows income of rupees {income:,.2f}, expenses of rupees {expense:,.2f}, and net balance of rupees {net:,.2f}."}
        return {"message": "I could not check your balance right now."}

    async def _handle_analytics_query(self, params, context=None):
        raw_text = ((context or {}).get("raw_text") or "").strip()
        if self._looks_like_client_revenue_query(raw_text, params):
            return await self._handle_client_revenue_query(params, context)
        if self._looks_like_collection_query(raw_text, params):
            return await self._handle_collection_query(params, context)

        org_uuid = context.get("org_uuid") or context.get("org_id")
        business_id = context.get("business_id", "default")
        user_id = context.get("user_id")
        response = await self.backend.get_finance_metrics(business_id, org_uuid, user_id)
        if response.success and response.data:
            metrics = response.data
            revenue = metrics.get("revenue", 0)
            expenses = metrics.get("expenses", 0)
            profit = metrics.get("netProfit", 0)
            return {"message": f"Revenue for this period is rupees {revenue:,.0f}, expenses are rupees {expenses:,.0f}, and net profit is rupees {profit:,.0f}."}
        return {"message": "I could not retrieve your analytics right now."}

    def _looks_like_client_revenue_query(self, raw_text: str, params: Optional[Dict[str, Any]] = None) -> bool:
        text = (raw_text or "").lower()
        hinted_client = self._extract_client_hint(params)

        revenue_keywords = (
            "revenue", "highest", "top client", "top clients", "most paying",
            "generated", "contributed", "given me", "gave me", "client contribution",
        )
        has_revenue_signal = any(keyword in text for keyword in revenue_keywords)
        return has_revenue_signal or (bool(hinted_client) and has_revenue_signal)

    def _looks_like_collection_query(self, raw_text: str, params: Optional[Dict[str, Any]] = None) -> bool:
        text = (raw_text or "").lower()
        collection_keywords = (
            "remain to collect",
            "remained to collect",
            "remaining to collect",
            "left to collect",
            "yet to collect",
            "outstanding",
            "balance due",
            "pending collection",
            "pending payment",
            "unpaid invoices",
            "receivable",
            "receivables",
            "collect from clients",
        )
        if any(keyword in text for keyword in collection_keywords):
            return True

        if "collect" in text and any(keyword in text for keyword in ("how much", "total", "money", "amount")):
            return True

        return False

    def _wants_ranked_client_revenue(self, raw_text: str) -> bool:
        text = (raw_text or "").lower()
        return any(
            keyword in text for keyword in (
                "highest", "top", "most", "best", "largest", "rank", "leader"
            )
        )

    def _format_rupees(self, value: Any) -> str:
        try:
            return f"rupees {float(value or 0):,.0f}"
        except Exception:
            return "rupees 0"

    def _extract_client_hint(self, params: Optional[Dict[str, Any]]) -> str:
        if not isinstance(params, dict):
            return ""
        candidate = str(params.get("client_name") or params.get("company_name") or "").strip()
        generic_values = {"", "business", "my business", "company", "my company", "statistics"}
        return "" if candidate.lower() in generic_values else candidate

    def _looks_like_invoice_breakdown_query(self, raw_text: str) -> bool:
        text = (raw_text or "").lower()
        return "which client" in text and "invoice" in text

    def _looks_like_client_invoice_query(self, raw_text: str) -> bool:
        text = (raw_text or "").lower().strip()
        if any(keyword in text for keyword in ("my invoices", "do i have", "total invoices")):
            return False
        return any(
            phrase in text for phrase in (
                "in the name of",
                "does ",
                "do sam",
                "does sam",
                "have invoices",
                "client has",
            )
        )

    def _invoice_matches_client(self, invoice: Dict[str, Any], client: Dict[str, Any]) -> bool:
        invoice_client_id = str(invoice.get("clientId") or "").strip()
        client_id = str(client.get("id") or "").strip()
        if invoice_client_id and client_id and invoice_client_id == client_id:
            return True

        def normalize(value: str) -> str:
            return re.sub(r"[^a-z0-9]", "", str(value).lower())

        return normalize(invoice.get("clientName") or "") == normalize(client.get("name") or "")

    async def _handle_client_revenue_query(self, params, context=None):
        safe_context = context or {}
        org_uuid = safe_context.get("org_uuid") or safe_context.get("org_id")
        business_id = safe_context.get("business_id", "default")
        user_id = safe_context.get("user_id")
        raw_text = (safe_context.get("raw_text") or "").strip()

        if not org_uuid:
            return {"message": "I couldn't identify your business context for that client revenue query."}

        hinted_name = self._extract_client_hint(params)

        if self._wants_ranked_client_revenue(raw_text):
            response = await self.backend.get_client_revenue_summary(str(business_id), org_uuid, limit=5, user_id=user_id)
            if response.success and response.data:
                top_clients = response.data.get("topClients", [])
                if not top_clients:
                    return {"message": "You don't have any client revenue data yet."}

                leader = top_clients[0]
                if any(keyword in raw_text.lower() for keyword in ("top 5", "top five", "top clients", "list")):
                    preview = ", ".join(
                        f"{item.get('clientName', 'Unknown Client')} at billed {self._format_rupees(item.get('billedRevenue'))}"
                        for item in top_clients[:3]
                    )
                    return {"message": f"Your top clients by billed revenue are {preview}."}

                return {
                    "message": (
                        f"Your highest revenue client is {leader.get('clientName', 'Unknown Client')}. "
                        f"They account for billed revenue of {self._format_rupees(leader.get('billedRevenue'))}, "
                        f"collected revenue of {self._format_rupees(leader.get('collectedRevenue'))}, "
                        f"and outstanding revenue of {self._format_rupees(leader.get('outstandingRevenue'))}."
                    )
                }
            return {"message": "I couldn't calculate your top client revenue right now."}

        resolved_client = await self._resolve_client(hinted_name or raw_text, org_uuid, user_id)
        if not resolved_client:
            clients = await self.backend.get_clients(org_uuid, user_id=user_id)
            if clients:
                names = ", ".join(client.get("name", "") for client in clients[:5] if client.get("name"))
                return {"message": f"I couldn't match that client exactly. Your current clients include {names}."}
            return {"message": "I couldn't find any clients to match that revenue query."}

        response = await self.backend.get_client_revenue_detail(
            str(business_id),
            resolved_client.get("id"),
            org_uuid,
            user_id=user_id,
        )
        if response.success and response.data:
            data = response.data
            return {
                "message": (
                    f"{data.get('clientName', resolved_client.get('name', 'That client'))} has generated "
                    f"billed revenue of {self._format_rupees(data.get('billedRevenue'))}, "
                    f"collected revenue of {self._format_rupees(data.get('collectedRevenue'))}, "
                    f"and outstanding revenue of {self._format_rupees(data.get('outstandingRevenue'))} "
                    f"across {data.get('invoiceCount', 0)} invoices."
                )
            }
        return {"message": f"I couldn't calculate revenue for {resolved_client.get('name', 'that client')} right now."}

    async def _handle_collection_query(self, params, context=None):
        safe_context = context or {}
        org_uuid = safe_context.get("org_uuid") or safe_context.get("org_id")
        user_id = safe_context.get("user_id")
        raw_text = (safe_context.get("raw_text") or "").lower()

        if not org_uuid:
            return {"message": "I couldn't identify your business context for that collections query."}

        response = await self.backend.get_invoices(org_uuid, limit=100, user_id=user_id)
        if not response.success or not isinstance(response.data, list):
            return {"message": "I couldn't calculate your outstanding collections right now."}

        invoices = response.data
        outstanding_invoices = []
        overdue_count = 0

        for invoice in invoices:
            try:
                balance_due = float(invoice.get("balanceDue") or 0)
            except Exception:
                balance_due = 0.0

            if balance_due > 0:
                outstanding_invoices.append(invoice)
                if str(invoice.get("status") or "").upper() == "OVERDUE":
                    overdue_count += 1

        total_outstanding = sum(float(item.get("balanceDue") or 0) for item in outstanding_invoices)

        if not outstanding_invoices:
            return {"message": "You don't have any money left to collect right now. All tracked invoices are settled."}

        if any(keyword in raw_text for keyword in ("overdue", "late")):
            return {
                "message": (
                    f"You have {overdue_count} overdue invoices, with overdue collections of "
                    f"{self._format_rupees(sum(float(item.get('balanceDue') or 0) for item in outstanding_invoices if str(item.get('status') or '').upper() == 'OVERDUE'))}."
                )
            }

        return {
            "message": (
                f"You still have {self._format_rupees(total_outstanding)} left to collect across "
                f"{len(outstanding_invoices)} unpaid invoices, including {overdue_count} overdue invoices."
            )
        }

    async def process(self, intent: Intent, entities: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        if intent in (Intent.INVOICE_CREATE, Intent.INVOICE_UPDATE, Intent.EXPENSE_CREATE):
            from app.voice_processor import VoiceContext

            safe_context = context or {}
            voice_context = VoiceContext(
                session_id=safe_context.get("session_id", "fallback"),
                user_id=safe_context.get("user_id", "unknown"),
                org_uuid=safe_context.get("org_uuid") or safe_context.get("org_id", "unknown"),
                raw_text=safe_context.get("raw_text"),
            )
            voice_context.extracted_entities = [{"type": key, "value": value} for key, value in entities.items()]
            if intent == Intent.EXPENSE_CREATE:
                return await self.handle_expense_create(voice_context)
            return await self.handle_invoice_create(voice_context)

        tool_name = {
            Intent.INVOICE_QUERY: "query_invoices",
            Intent.EXPENSE_QUERY: "query_expenses",
            Intent.BALANCE_CHECK: "check_balance",
            Intent.ANALYTICS_QUERY: "analytics_query",
            Intent.BUSINESS_HEALTH_CHECK: "calculate_business_health_score",
        }.get(intent)

        if tool_name:
            result = await tool_registry.execute_tool(tool_name, entities, context)
            return self._build_success_response(message=result.result.get("message", "Success"), tool_used=tool_name)

        return self._build_error_response("Unsupported finance intent")


finance_agent = FinanceAgent()
