"""
Finance Agent - Handles financial operations and strategic planning
Consolidated v2.1: Absorbed StrategyAgent logic
"""
import uuid
import time
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from app.agents.base_agent import BaseAgent, ToolDefinition, AgentResponse
from app.models.draft import InvoiceDraft
from app.schemas.intents import Intent, AgentType
from app.adapters.backend_adapter import get_backend_adapter
from app.tools.tool_registry import Tool, tool_registry
from app.utils.logger import get_logger

logger = get_logger(__name__)

class FinanceAgent(BaseAgent):
    def __init__(self):
        self.backend = get_backend_adapter()
        # Initialize base AFTER setting up backend
        super().__init__()
        # Also register with the legacy tool_registry for compatibility
        self._register_legacy_tools()

    def get_agent_type(self) -> AgentType:
        return AgentType.FINANCE_AGENT

    def get_supported_intents(self) -> List[Intent]:
        return [
            Intent.INVOICE_CREATE,
            Intent.INVOICE_QUERY,
            Intent.BUSINESS_HEALTH_CHECK,
            Intent.PROBLEM_DIAGNOSIS,
            Intent.ANALYTICS_QUERY,
            Intent.BALANCE_CHECK,
            Intent.PAYMENT_RECORD,
        ]

    def get_tools(self) -> List[ToolDefinition]:
        """Return tools defined for this agent following BaseAgent pattern"""
        return [
            ToolDefinition(
                name="query_invoices",
                description="Search/list invoices",
                parameters={},
                mvp_ready=True
            ),
            ToolDefinition(
                name="check_balance",
                description="Get balance summary",
                parameters={},
                mvp_ready=True
            ),
            ToolDefinition(
                name="analytics_query",
                description="Financial metrics",
                parameters={},
                mvp_ready=True
            ),
            ToolDefinition(
                name="calculate_business_health_score",
                description="Calculate comprehensive business health score /100",
                parameters={},
                mvp_ready=True
            )
        ]

    def _register_legacy_tools(self):
        """Register with the legacy tool_registry handler-based system"""
        tool_registry.register_tools([
            Tool(name="query_invoices", description="Search/list invoices", category="finance", mvp_ready=True, handler=self._handle_query_invoices),
            Tool(name="check_balance", description="Get balance summary", category="finance", mvp_ready=True, handler=self._handle_check_balance),
            Tool(name="analytics_query", description="Financial metrics", category="finance", mvp_ready=True, handler=self._handle_analytics_query),
            Tool(name="calculate_business_health_score", description="Strategic health score", category="finance", mvp_ready=True, handler=self._handle_business_health_score)
        ])

    async def handle_invoice_create(self, context) -> AgentResponse:
        from app.state.session_manager import session_manager
        # context.user_id = clerk_user_id, context.org_uuid = internal_uuid (if resolved)
        session = session_manager.get_session(context.session_id, context.user_id, context.org_uuid)
        
        draft = session.invoice_draft
        if draft is None:
            draft = InvoiceDraft(draft_id=str(uuid.uuid4()), session_id=context.session_id)
        
        # Merge entities into EMPTY fields only — never overwrite
        logger.info({"entities": context.extracted_entities, "current_due": draft.due_date, "event": "PRE_MERGE_DEBUG"})
        for entity in (context.extracted_entities or []):
            etype = (entity.get("type") or "").lower().strip()
            val = entity.get("value")
            if not etype or val is None or val == "": continue
                
            if etype in ("client_name", "client", "company_name") and not draft.client_id:
                # Always allow overwrite if not resolved yet (user clarification)
                draft.client_name = val 
                client = await self._resolve_client(val, context.org_uuid)
                if client:
                    draft.client_id = client.get("id")
                    draft.client_name = client.get("name")
            elif etype in ("amount", "total"):
                try: 
                    new_val = float(str(val).replace(",", "").replace("₹", "").replace("rupees", "").strip())
                    # Safeguard: Don't let day numbers (1-31) or small fragments 
                    # overwrite an existing significant amount.
                    if draft.amount is None or new_val > 100 or new_val > draft.amount * 0.5:
                        draft.amount = new_val
                except: 
                    pass
            elif etype in ("due_date", "time_period", "date", "deadline"):
                if draft.due_date is None or draft.due_date == "" or draft.due_date == "null":
                    v_str = str(val).strip()
                    # Basic YYYY-MM-DD validation
                    if len(v_str) == 10 and v_str[4] == "-" and v_str[7] == "-":
                        draft.due_date = v_str
                        logger.info({"merged_due_date": draft.due_date, "from": etype, "event": "due_date_merged"})
            elif etype in ("due_days", "entity_name", "days", "duration") and not draft.due_date:
                # Handle "15 days" → compute actual date
                try:
                    days_str = str(val).lower().replace("days", "").strip()
                    days = int(days_str)
                    if 1 <= days <= 365:
                        due = datetime.now() + timedelta(days=days)
                        draft.due_date = due.strftime("%Y-%m-%d")
                        logger.info({"merged_due_days": days, "computed": draft.due_date, "event": "due_date_from_days"})
                except: pass
            elif etype in ("gst_percent", "gst", "tax_percent", "percentage", "gst_percentage") and draft.gst_percent is None:
                try: 
                    v_str = str(val).replace("%", "").strip()
                    if v_str.lower() != "null" and v_str != "":
                        draft.gst_percent = float(v_str)
                except: 
                    pass
        
        session.invoice_draft = draft
        session.locked_intent = "INVOICE_CREATE"
        session_manager.save_session(session)
        
        logger.info({"client": draft.client_name, "amount": draft.amount, "due": draft.due_date, "event": "draft_merged"})

        if not draft.client_id:
            logger.info({"context_org_uuid": context.org_uuid, "event": "DEBUG_org_context"})
            clients = await self.backend.get_clients(context.org_uuid)
            if not clients:
                return AgentResponse(
                    message="I couldn't load your client list. Please say the client name again.",
                    success=True,
                    ui_event={"type": "toast", "variant": "warning", "title": "Loading clients...", "message": "Retrying client lookup"},
                    agent_type=self.get_agent_type()
                )
            
            # Re-check resolution if we have a name
            # Re-check resolution if we have a name but no ID
            if draft.client_name and not draft.client_id:
                client = await self._resolve_client(draft.client_name, context.org_uuid)
                if client:
                    draft.client_id = client.get("id")
                    draft.client_name = client.get("name")
                    session.invoice_draft = draft
                    session_manager.save_session(session)
                    # Don't return, fall through to check next missing field (e.g. amount)
                else:
                    names = [c.get("name") for c in clients[:6]]
                    return AgentResponse(
                        message=f"I couldn't find a client called '{draft.client_name}'. Your existing clients are: {', '.join(filter(None, names))}. Which one, or should I create a new one?",
                        success=True,
                        ui_event={"type": "toast", "variant": "warning", "title": "Client Not Found", "message": f"No match for '{draft.client_name}'"},
                        agent_type=self.get_agent_type()
                    )
            
            if not draft.client_id:
                names = [c.get("name") for c in clients[:6]]
                return AgentResponse(
                    message=f"Which client? You have: {', '.join(filter(None, names))}.",
                    success=True,
                    ui_event={"type": "progress", "variant": "info", "title": "Creating Invoice", "message": "Step 1 — Select client"},
                    agent_type=self.get_agent_type()
                )
        
        if draft.amount is None:
            return AgentResponse(
                message=f"What's the amount for {draft.client_name}?",
                success=True,
                ui_event={"type": "progress", "variant": "info", "title": "Creating Invoice", "message": f"Client: {draft.client_name} ✓ — What's the amount?"},
                agent_type=self.get_agent_type()
            )
        
        if not draft.due_date:
            return AgentResponse(
                message="What's the due date?",
                success=True,
                ui_event={"type": "progress", "variant": "info", "title": "Creating Invoice", "message": f"₹{draft.amount:,.0f} for {draft.client_name} ✓ — Due date?"},
                agent_type=self.get_agent_type()
            )
        
        if draft.gst_percent is None:
            total_with_gst = draft.amount * 1.18
            return AgentResponse(
                message=f"Add 18% GST? Total would be ₹{total_with_gst:,.0f}.",
                success=True,
                ui_event={
                    "type": "confirmation", 
                    "variant": "warning", 
                    "title": "Confirm GST", 
                    "message": f"Add 18% GST → Total ₹{total_with_gst:,.0f}?"
                },
                agent_type=self.get_agent_type()
            )

        if not draft.service_description:
            return AgentResponse(
                message=f"What's this invoice for? For example: 'web development services' or 'consulting for March'.",
                success=True,
                ui_event={
                    "type": "progress", 
                    "variant": "info", 
                    "title": "Creating Invoice", 
                    "message": "What service are you billing for?"
                },
                agent_type=self.get_agent_type()
            )

        if not draft.confirmed:
            gst_total = round(draft.amount * (draft.gst_percent / 100), 2)
            total = round(draft.amount + gst_total, 2)
            return AgentResponse(
                message=f"Ready to create: {draft.service_description} for {draft.client_name}, ₹{draft.amount:,.0f} + {draft.gst_percent}% GST = ₹{total:,.0f}, due {draft.due_date}. Shall I proceed?",
                success=True,
                ui_event={
                    "type": "confirmation", 
                    "variant": "warning", 
                    "title": "Confirm Invoice", 
                    "message": f"{draft.client_name} · ₹{total:,.0f} due {draft.due_date}", 
                    "actions": [{"label": "Yes, create"}, {"label": "Cancel"}]
                },
                agent_type=self.get_agent_type()
            )

        return await self._finalize_and_create_invoice(draft, context)

    async def _finalize_and_create_invoice(self, draft: InvoiceDraft, context) -> AgentResponse:
        from app.state.session_manager import session_manager
        try:
            subtotal = draft.amount
            gst_rate = (draft.gst_percent or 0) / 100
            gst_total = round(subtotal * gst_rate, 2)
            total_amount = round(subtotal + gst_total, 2)

            # Build a default line item (Backend requires at least one item)
            line_items = [
                {
                    "type": "SERVICE",
                    "description": draft.service_description or f"Services for {draft.client_name}",
                    "quantity": None, # Must be null for SERVICE items in backend
                    "rate": subtotal,
                    "gstPercent": draft.gst_percent or 0,
                    "lineSubtotal": subtotal,
                    "lineGst": gst_total,
                    "lineTotal": total_amount
                }
            ]

            # Map to InvoiceDto fields exactly as Spring Boot expects
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
                "items": line_items,
                "notes": "Created via Voice Ops"
            }
            
            logger.info({"payload": payload, "event": "creating_invoice_payload"})
            resp = await self.backend.create_invoice_direct(context.org_uuid, context.user_id, payload)
            if not resp.success: raise Exception(resp.error)
            
            invoice = resp.data
            invoice_number = invoice.get("invoiceNumber", "N/A")
            invoice_id = invoice.get("id", "")

            # Clear draft and unlock intent
            session = session_manager.get_session(context.session_id, context.user_id, context.org_uuid)
            session.invoice_draft = None
            session.locked_intent = None
            session_manager.save_session(session)
            
            return AgentResponse(
                message=f"Invoice {invoice_number} created for {draft.client_name}. Total ₹{total_amount:,.0f} including GST, due {draft.due_date}.",
                success=True,
                ui_event={
                    "type": "invoice_created",
                    "invoice_id": invoice_id,
                    "invoice_number": invoice_number,
                    "client_name": draft.client_name,
                    "total": total_amount,
                    "due_date": draft.due_date
                },
                agent_type=self.get_agent_type()
            )
        except Exception as e:
            return self._build_error_response(str(e))

    async def _resolve_client(self, spoken_name: str, org_uuid: str) -> Optional[Dict]:
        clients = await self.backend.get_clients(org_uuid)
        if not clients or not spoken_name: return None

        def normalize(s):
            return re.sub(r'[^a-z0-9]', '', str(s).lower())

        spoken_norm = normalize(spoken_name)
        
        # Pass 1: exact normalized match
        for c in clients:
            if normalize(c.get("name") or "") == spoken_norm: return c
            
        # Pass 2: substring match
        for c in clients:
            c_norm = normalize(c.get("name") or "")
            if spoken_norm in c_norm or c_norm in spoken_norm: return c
            
        # Pass 3: word overlap
        spoken_words = set(spoken_name.lower().split())
        best, best_score = None, 0
        for c in clients:
            client_words = set((c.get("name") or "").lower().split())
            score = len(spoken_words & client_words)
            if score > best_score:
                best_score = score
                best = c
        
        return best if best_score >= 1 else None

    # Handler stubs for other intents
    async def _handle_business_health_score(self, params, context=None): 
        org_uuid = context.get("org_uuid") or context.get("org_id")
        business_id = context.get("business_id", 1)
        user_id = context.get("user_id")
        
        resp = await self.backend.get_finance_metrics(business_id, org_uuid, user_id)
        if resp.success and resp.data:
            m = resp.data
            revenue = m.get("revenue", 0)
            expenses = m.get("expenses", 0)
            profit = m.get("netProfit", 0)
            # Simple heuristic score
            score = 75 # default
            if revenue > 0:
                profit_margin = (profit / revenue) * 100
                score = min(100, max(0, int(50 + profit_margin)))
            
            return {"message": f"Your business health score is {score}/100. Your net profit margin is sitting at {profit_margin:.1f}% based on recent revenue of ₹{revenue:,.0f}."}
        return {"message": "I couldn't calculate your health score right now."}

    async def _handle_query_invoices(self, params, context=None): 
        org_uuid = context.get("org_uuid") or context.get("org_id")
        user_id = context.get("user_id")
        resp = await self.backend._request("GET", "/api/invoices", org_id=org_uuid, user_id=user_id)
        if resp.success and isinstance(resp.data, list):
            count = len(resp.data)
            return {"message": f"You have {count} total invoices in the system."}
        return {"message": "I couldn't fetch your invoices right now."}

    async def _handle_check_balance(self, params, context=None): 
        org_uuid = context.get("org_uuid") or context.get("org_id")
        user_id = context.get("user_id")
        resp = await self.backend.get_financial_summary(org_uuid, user_id)
        if resp.success and resp.data:
            summary = resp.data
            income = summary.get("totalIncome", 0)
            expense = summary.get("totalExpense", 0)
            net = summary.get("netProfit", 0)
            return {"message": f"Your current cash balance summary shows total income of ₹{income:,.2f} and total expenses of ₹{expense:,.2f}, leaving a net balance of ₹{net:,.2f}."}
        return {"message": "I couldn't check your balance right now."}

    async def _handle_analytics_query(self, params, context=None): 
        org_uuid = context.get("org_uuid") or context.get("org_id")
        business_id = context.get("business_id", 1)
        user_id = context.get("user_id")
        
        resp = await self.backend.get_finance_metrics(business_id, org_uuid, user_id)
        if resp.success and resp.data:
            m = resp.data
            revenue = m.get("revenue", 0)
            expenses = m.get("expenses", 0)
            profit = m.get("netProfit", 0)
            return {"message": f"Revenue for this period is ₹{revenue:,.0f} with expenses of ₹{expenses:,.0f}, resulting in a net profit of ₹{profit:,.0f}."}
        return {"message": "I couldn't retrieve your analytics data at the moment."}

    async def process(self, intent: Intent, entities: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        if intent == Intent.INVOICE_CREATE:
            from app.voice_processor import VoiceContext
            safe_context = context or {}
            ctx = VoiceContext(
                session_id=safe_context.get("session_id", "fallback"), 
                user_id=safe_context.get("user_id", "unknown"), 
                org_uuid=safe_context.get("org_id", "unknown")
            )
            ctx.extracted_entities = [{"type": k, "value": v} for k, v in entities.items()]
            return await self.handle_invoice_create(ctx)
        
        tool_name = {
            Intent.BALANCE_CHECK: "check_balance",
            Intent.ANALYTICS_QUERY: "analytics_query",
            Intent.BUSINESS_HEALTH_CHECK: "calculate_business_health_score",
        }.get(intent)
        
        if tool_name:
            result = await tool_registry.execute_tool(tool_name, entities, context)
            return self._build_success_response(
                message=result.result.get("message", "Success"),
                tool_used=tool_name
            )
        
        return self._build_success_response("I can help with that soon.")

finance_agent = FinanceAgent()