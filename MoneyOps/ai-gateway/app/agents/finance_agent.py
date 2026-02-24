"""
Finance Agent - Handles financial operations and strategic planning
MVP: Operational tools only (CRUD)
v2.0: Strategic features (health scoring, recommendations, forecasting)
"""
from typing import Dict, Any, List, Optional
from decimal import Decimal
from datetime import datetime, timedelta
import time
import re


from app.agents.base_agent import BaseAgent, AgentResponse, ToolDefinition
from app.schemas.intents import Intent, AgentType
from app.adapters.backend_adapter import get_backend_adapter

from app.tools.tool_registry import Tool, ToolParameters, tool_registry
from app.features import feature_flags
from app.utils.logger import get_logger

logger = get_logger(__name__)


class FinanceAgent(BaseAgent):
    """
    Finance Agent handles:
    - MVP: Invoice, payment, transaction CRUD
    - v2.0: Health scoring, cash flow analysis, budget optimization
    """
    
    def __init__(self):
        super().__init__()
        # Lazy-get the backend adapter instance
        # Auth token will be set per request in process() method
        self.backend = get_backend_adapter()
        
        # Register tools with the global registry
        self._register_finance_tools()
        
        logger.info("finance_agent_initialized", mvp_tools=len(self.get_mvp_tools()))
    
    def get_agent_type(self) -> AgentType:
        return AgentType.FINANCE_AGENT
    
    def get_supported_intents(self) -> List[Intent]:
        """Intents this agent can handle"""
        return [
            # Operational (MVP)
            Intent.INVOICE_CREATE,
            Intent.INVOICE_QUERY,
            Intent.INVOICE_UPDATE,
            Intent.INVOICE_DELETE,
            Intent.CLIENT_CREATE,
            Intent.CLIENT_QUERY,
            Intent.PAYMENT_RECORD,
            Intent.PAYMENT_QUERY,
            Intent.BALANCE_CHECK,
            Intent.TRANSACTION_QUERY,
            Intent.ACCOUNT_STATEMENT,
            
            # Strategic (v2.0 - stubbed for now)
            Intent.BUSINESS_HEALTH_CHECK,
            Intent.BUDGET_OPTIMIZATION,
            Intent.CASH_FLOW_PLANNING,
            Intent.PROFIT_OPTIMIZATION,
        ]
    
    def get_tools(self) -> List[ToolDefinition]:
        """Return tool definitions (for compatibility with base class)"""
        # Convert Tool objects to ToolDefinition for base class
        tools = tool_registry.get_tools_by_category("finance")
        return [
            ToolDefinition(
                name=t.name,
                description=t.description,
                parameters={p.name: p.type for p in t.parameters},
                enabled=t.enabled,
                mvp_ready=t.mvp_ready
            )
            for t in tools
        ]
    
    def _register_finance_tools(self):
        """Register all finance tools in the global registry"""
        
        # ========================================
        # MVP TOOLS (Operational CRUD)
        # ========================================
        
        # Invoice Create Tool
        create_invoice_tool = Tool(
            name="create_invoice",
            description="Create a new invoice for a client",
            category="finance",
            mvp_ready=True,
            requires_confirmation=True,
            parameters=[
                ToolParameters(
                    name="client_name",
                    type="string",
                    description="Name of the client",
                    required=True
                ),
                ToolParameters(
                    name="items",
                    type="array",
                    description="List of line items",
                    required=True
                ),
                ToolParameters(
                    name="subtotal",
                    type="number",
                    description="Subtotal amount",
                    required=True
                ),
                ToolParameters(
                    name="tax",
                    type="number",
                    description="Tax amount",
                    required=False,
                    default=0.0
                ),
                ToolParameters(
                    name="total",
                    type="number",
                    description="Total amount",
                    required=True
                ),
                ToolParameters(
                    name="due_date",
                    type="string",
                    description="Due date (ISO format)",
                    required=False
                ),
                ToolParameters(
                    name="notes",
                    type="string",
                    description="Additional notes",
                    required=False
                ),
            ],
            handler=self._handle_create_invoice
        )
        
        # Invoice Query Tool
        query_invoices_tool = Tool(
            name="query_invoices",
            description="Search and list invoices",
            category="finance",
            mvp_ready=True,
            parameters=[
                ToolParameters(
                    name="status",
                    type="string",
                    description="Filter by status",
                    required=False,
                    enum=["PAID", "UNPAID", "OVERDUE", "CANCELLED"]
                ),
                ToolParameters(
                    name="client_name",
                    type="string",
                    description="Filter by client name",
                    required=False
                ),
                ToolParameters(
                    name="limit",
                    type="number",
                    description="Number of results",
                    required=False,
                    default=50
                ),
            ],
            handler=self._handle_query_invoices
        )
        
        # Payment Record Tool
        record_payment_tool = Tool(
            name="record_payment",
            description="Record a payment received for an invoice",
            category="finance",
            mvp_ready=True,
            requires_confirmation=True,
            parameters=[
                ToolParameters(
                    name="invoice_id",
                    type="string",
                    description="Invoice ID",
                    required=True
                ),
                ToolParameters(
                    name="amount",
                    type="number",
                    description="Payment amount",
                    required=True
                ),
                ToolParameters(
                    name="payment_method",
                    type="string",
                    description="Payment method",
                    required=False,
                    default="BANK_TRANSFER",
                    enum=["CASH", "BANK_TRANSFER", "CHEQUE", "UPI", "CARD"]
                ),
                ToolParameters(
                    name="notes",
                    type="string",
                    description="Payment notes",
                    required=False
                ),
            ],
            handler=self._handle_record_payment
        )
        
        # Client Create Tool
        create_client_tool = Tool(
            name="create_client",
            description="Create a new client in the system",
            category="finance",
            mvp_ready=True,
            requires_confirmation=True,
            parameters=[
                ToolParameters(name="client_name", type="string", description="Full name of the client", required=True),
                ToolParameters(name="email", type="string", description="Email address", required=True),
                ToolParameters(name="phone", type="string", description="Phone number", required=False),
                ToolParameters(name="tax_id", type="string", description="GST/PAN number", required=False),
                ToolParameters(name="address", type="string", description="Billing address", required=False),
                ToolParameters(name="company", type="string", description="Company Name", required=False),
            ],
            handler=self._handle_create_client
        )
        
        # Balance Check Tool
        check_balance_tool = Tool(
            name="check_balance",
            description="Get current account balance",
            category="finance",
            mvp_ready=True,
            parameters=[],
            handler=self._handle_check_balance
        )
        
        # Register MVP tools
        tool_registry.register_tools([
            create_invoice_tool,
            query_invoices_tool,
            record_payment_tool,
            check_balance_tool,
            create_client_tool,
        ])
        
        # ========================================
        # V2.0 TOOLS (Strategic - Stubbed)
        # ========================================
        
        if feature_flags.ENABLE_HEALTH_SCORING:
            # Real implementation in v2.0
            pass
        else:
            # Stub tool
            health_score_tool = Tool(
                name="calculate_health_score",
                description="Calculate business health score (v2.0 feature)",
                category="finance",
                mvp_ready=False,
                enabled=False,
                parameters=[],
                handler=self._stub_health_score
            )
            tool_registry.register_tool(health_score_tool)
    
    # ========================================
    # MVP TOOL HANDLERS (Operational)
    # ========================================
    
    async def _handle_create_client(
        self,
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle client creation"""
        org_id = context.get("org_id", "default_org") if context else "default_org"
        user_id = context.get("user_id") if context else None
        
        if not user_id:
            raise Exception("User ID is missing from context. Please ensure you are logged in.")

        response = await self.backend.create_client(
            org_id=org_id,
            user_id=user_id,
            name=params["client_name"],
            email=params["email"],
            phone=params.get("phone") or params.get("phone_number"),
            address=params.get("address"),
            tax_id=params.get("tax_id") or params.get("gst_number") or params.get("gst") or params.get("tax"),
            company=params.get("company") or params.get("company_name")
        )
        
        if response.success:
            client_data = response.data
            return {
                "client_id": client_data.get("id"),
                "name": client_data.get("name"),
                "status": "created",
                "message": f"Client '{client_data.get('name')}' created successfully."
            }
        else:
            raise Exception(response.error or "Failed to create client")

    async def _handle_create_invoice(
        self,
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle invoice creation"""
        org_id = context.get("org_id", "default_org") if context else "default_org"
        user_id = context.get("user_id")
        
        if not user_id:
            # Fallback for testing if not provided, though backend will likely reject null
            logger.warning("user_id_missing_in_context")
            # Try to proceed or raise? Backend adapter needs it.
            # If we don't have it, we can't create invoice securely.
            raise Exception("User ID is missing from context. Please ensure you are logged in.")

        # 1. Lookup Client ID by Name
        client_name_query = params["client_name"]
        logger.info("searching_client", query=client_name_query, org_id=org_id)
        
        client_resp = await self.backend.get_client_by_name(org_id, client_name_query)
        
        if not client_resp.success:
            raise Exception(f"Failed to lookup client: {client_resp.error}")
            
        clients = client_resp.data
        client_id = None
        matched_client_name = client_name_query

        if isinstance(clients, list) and clients:
            top_match = clients[0]
            client_id = top_match.get("id")
            matched_client_name = top_match.get("name", client_name_query)
            score = top_match.get("searchScore", 1.0) # Default 1.0 if not provided
            
            logger.info("client_match_details", name=matched_client_name, score=score)
            
            # Confidence threshold logic
            if score < 0.85:
                # Store potential match in state for next turn confirmation
                # (For now, just ask the user)
                return {
                    "status": "partial",
                    "needs_more_info": True,
                    "message": f"I found a close match for '{matched_client_name}'. Is that the correct client?",
                    "intent": "INVOICE_CREATE",
                    "accumulated_entities": {**params, "client_name": matched_client_name}
                }

        elif isinstance(clients, dict) and clients.get("id"):
             client_id = clients.get("id")
             matched_client_name = clients.get("name", client_name_query)
        
        # Update params with canonical name for voice response later
        params["client_name"] = matched_client_name

        if not client_id:
            raise Exception(f"Client '{client_name_query}' not found. Please ensure the client exists or create them first.")

        # 2. Build Invoice Data
        invoice_number = f"INV-{int(time.time())}"
        issue_date = datetime.now().strftime("%Y-%m-%d")
        
        # Expecting ISO date from voice.py / entity_extractor
        due_date = params.get("due_date")
        gst_percent = float(params.get("gst_percent", 0))

        # Normalize items
        # If no items provided (common in voice), we use the total/amount collected
        total_amount = float(params.get("total") or params.get("amount", 0))
        raw_items = params.get("items", [])
        
        if not raw_items:
            # Create a single default item using the collected total and GST
            subtotal = round(total_amount / (1 + gst_percent/100), 2)
            tax_amount = round(total_amount - subtotal, 2)
            
            normalized_items = [{
                "description": "General Service",
                "type": "SERVICE",
                "quantity": None,
                "rate": subtotal,
                "gstPercent": gst_percent,
                "lineSubtotal": subtotal,
                "lineGst": tax_amount,
                "lineTotal": total_amount,
            }]
            subtotal_final = subtotal
            tax_final = tax_amount
        else:
            # Process provided items
            normalized_items = []
            subtotal_final = 0
            tax_final = 0
            for item in raw_items:
                qty = float(item.get("quantity", 1))
                rate = float(item.get("unit_price") or item.get("rate") or item.get("amount", 0))
                item_gst = float(item.get("gstPercent", gst_percent))
                
                l_sub = round(qty * rate, 2)
                l_tax = round(l_sub * item_gst / 100, 2)
                l_tot = round(l_sub + l_tax, 2)
                
                is_service = item.get("type", "SERVICE") == "SERVICE"
                normalized_items.append({
                    "description": item.get("description", "Service"),
                    "type": "SERVICE" if is_service else "PRODUCT",
                    "quantity": None if is_service else int(qty),
                    "rate": rate,
                    "gstPercent": item_gst,
                    "lineSubtotal": l_sub,
                    "lineGst": l_tax,
                    "lineTotal": l_tot,
                })
                subtotal_final += l_sub
                tax_final += l_tax

        # 3. Create Invoice call
        try:
            logger.info("attempting_invoice_creation", client_id=client_id, total=total_amount, due_date=due_date)
            response = await self.backend.create_invoice(
                org_id=org_id,
                user_id=user_id,
                client_id=client_id,
                invoice_number=invoice_number,
                issue_date=issue_date,
                items=normalized_items,
                subtotal=subtotal_final,
                tax=tax_final,
                total=total_amount,
                due_date=due_date,
                notes=params.get("notes")
            )
        except Exception as e:
            logger.error("invoice_creation_api_crash", error=str(e), payload={
                "client_id": client_id,
                "due_date": due_date,
                "total": total_amount
            }, exc_info=True)
            raise Exception(f"Failed to reach billing service: {str(e)}")

        
        if response.success:
            invoice_data = response.data or {}
            inv_number = invoice_data.get("invoiceNumber") or invoice_data.get("id", "")
            total_val = params.get("total", 0)
            client = params["client_name"]
            logger.info(
                "invoice_created_successfully",
                invoice_id=invoice_data.get("id"),
                invoice_number=inv_number,
                client_name=client,
                total=total_val,
                user_id=user_id,
            )
            # Voice-friendly confirmation message
            try:
                formatted_total = f"₹{float(total_val):,.0f}"
            except Exception:
                formatted_total = str(total_val)
            voice_msg = f"Invoice for {formatted_total} created for {client}."
            if inv_number:
                voice_msg += f" Invoice number {inv_number}."
            return {
                "invoice_id": invoice_data.get("id"),
                "invoice_number": inv_number,
                "client_name": client,
                "total": total_val,
                "status": "created",
                "message": voice_msg,
            }
        else:
            logger.error(
                "invoice_creation_failed",
                error=response.error,
                client_name=params.get("client_name"),
                org_id=org_id,
                user_id=user_id,
            )
            raise Exception(response.error or "Failed to create invoice")
    
    async def _handle_query_invoices(
        self,
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle invoice queries"""
        org_id = context.get("org_id", "default_org") if context else "default_org"
        
        response = await self.backend.get_invoices(
            org_id=org_id,
            status=params.get("status"),
            client_name=params.get("client_name"),
            limit=int(params.get("limit", 50))
        )
        
        if response.success:
            invoices = response.data.get("invoices", []) if response.data else []
            return {
                "invoices": invoices,
                "count": len(invoices),
                "message": f"Found {len(invoices)} invoice(s)"
            }
        else:
            raise Exception(response.error or "Failed to query invoices")
    
    async def _handle_record_payment(
        self,
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle payment recording"""
        org_id = context.get("org_id", "default_org") if context else "default_org"
        
        response = await self.backend.record_payment(
            org_id=org_id,
            invoice_id=params["invoice_id"],
            amount=float(params["amount"]),
            payment_method=params.get("payment_method", "BANK_TRANSFER"),
            notes=params.get("notes")
        )
        
        if response.success:
            payment_data = response.data
            return {
                "payment_id": payment_data.get("id"),
                "invoice_id": params["invoice_id"],
                "amount": params["amount"],
                "status": "recorded",
                "message": f"Payment of ₹{params['amount']} recorded successfully"
            }
        else:
            raise Exception(response.error or "Failed to record payment")
    
    async def _handle_check_balance(
        self,
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle balance check"""
        org_id = context.get("org_id", "default_org") if context else "default_org"
        
        response = await self.backend.get_balance(org_id=org_id)
        
        if response.success:
            balance_data = response.data
            return {
                "balance": balance_data.get("balance", 0),
                "currency": "INR",
                "message": f"Current balance: ₹{balance_data.get('balance', 0)}"
            }
        else:
            raise Exception(response.error or "Failed to get balance")
    
    # ========================================
    # V2.0 STUB HANDLERS (Strategic)
    # ========================================
    
    async def _stub_health_score(
        self,
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Stub for health score (v2.0)"""
        return {
            "score": 75,
            "message": "Health scoring is coming in v2.0!",
            "implemented": False
        }
    
    # ========================================
    # MAIN PROCESS METHOD
    # ========================================
    
    async def process(
        self,
        intent: Intent,
        entities: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """
        Process a request based on intent and entities
        """
        logger.info("finance_agent_processing", intent=intent.value)

        # ── Pre-process entities for voice/simplified inputs ──────────────────
        if intent == Intent.INVOICE_CREATE:
            # Voice inputs: map 'amount' → 'total' and 'subtotal'
            amount_val = entities.get("amount") or entities.get("total") or entities.get("subtotal")
            if amount_val is not None:
                try:
                    amount_val = float(str(amount_val).replace(",", ""))
                except Exception:
                    pass
                entities.setdefault("total", amount_val)
                entities.setdefault("subtotal", amount_val)

            # Auto-generate line items from total if not provided
            if "items" not in entities or not entities["items"]:
                entities["items"] = [{
                    "description": "General Service",
                    "quantity": 1,
                    "unit_price": entities.get("total", 0),
                }]
            # Map synonyms for tax/gst
            if "gst_number" in entities and "tax_id" not in entities:
                entities["tax_id"] = entities["gst_number"]
            elif "gst" in entities and "tax_id" not in entities:
                entities["tax_id"] = entities["gst"]
            elif "tax" in entities and "tax_id" not in entities:
                entities["tax_id"] = entities["tax"]

        if intent == Intent.CLIENT_CREATE:
            # Map synonyms for tax/gst
            if "gst_number" in entities and "tax_id" not in entities:
                entities["tax_id"] = entities["gst_number"]
            elif "gst" in entities and "tax_id" not in entities:
                entities["tax_id"] = entities["gst"]
            elif "tax" in entities and "tax_id" not in entities:
                entities["tax_id"] = entities["tax"]
            
            # Map company_name to company
            if "company_name" in entities and "company" not in entities:
                entities["company"] = entities["company_name"]
        # ──────────────────────────────────────────────────────────────────────
        
        # Set auth token from context if available
        if context and context.get("auth_token"):
            self.backend.set_auth_token(context["auth_token"])
        
        # Route to appropriate tool based on intent
        tool_name = self._get_tool_for_intent(intent)
        
        if not tool_name:
            return self._build_error_response(
                f"No tool found for intent: {intent.value}"
            )
        
        # Check if tool is enabled
        tool = tool_registry.get_tool(tool_name)
        if not tool or not tool.enabled:
            if intent in self._get_strategic_intents():
                # Strategic feature - return stub
                return self._build_stub_response(
                    feature_name=intent.value.replace("_", " ").title(),
                    available_in="v2.0"
                )
            else:
                return self._build_error_response(
                    f"Tool '{tool_name}' is not available"
                )
        
        # Execute tool
        try:
            result = await tool_registry.execute_tool(
                tool_name=tool_name,
                parameters=entities,
                context=context
            )
            
            if result.success:
                status = result.result.get("status")
                if status == "partial":
                    return self._build_error_response(
                        error=result.result.get("message", "Partial match found"),
                        needs_clarification=True,
                        clarification_question=result.result.get("message")
                    )
                
                return self._build_success_response(
                    message=result.result.get("message", "Success"),
                    data=result.result,
                    tool_used=tool_name
                )
            else:
                return self._build_error_response(
                    error=result.error or "Tool execution failed"
                )
        
        except Exception as e:
            logger.error("finance_agent_error", error=str(e), intent=intent.value)
            return self._build_error_response(str(e))
    
    def _get_tool_for_intent(self, intent: Intent) -> Optional[str]:
        """Map intent to tool name"""
        intent_to_tool = {
            Intent.INVOICE_CREATE: "create_invoice",
            Intent.INVOICE_QUERY: "query_invoices",
            Intent.CLIENT_CREATE: "create_client",
            Intent.CLIENT_QUERY: "query_invoices",  # Shared query tool for now
            Intent.PAYMENT_RECORD: "record_payment",
            Intent.BALANCE_CHECK: "check_balance",
            
            # Strategic (v2.0)
            Intent.BUSINESS_HEALTH_CHECK: "calculate_health_score",
            Intent.CASH_FLOW_PLANNING: "analyze_cash_flow",
            Intent.BUDGET_OPTIMIZATION: "optimize_budget",
        }
        
        return intent_to_tool.get(intent)
    
    def _get_strategic_intents(self) -> List[Intent]:
        """Return list of strategic (v2.0) intents"""
        return [
            Intent.BUSINESS_HEALTH_CHECK,
            Intent.BUDGET_OPTIMIZATION,
            Intent.CASH_FLOW_PLANNING,
            Intent.PROFIT_OPTIMIZATION,
        ]


# Singleton instance
finance_agent = FinanceAgent()