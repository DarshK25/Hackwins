"""
Finance Agent - Handles financial operations and strategic planning
MVP: Operational tools only (CRUD)
v2.0: Strategic features (health scoring, recommendations, forecasting)
"""
from typing import Dict, Any, List, Optional
from decimal import Decimal
from datetime import datetime, timedelta
import time


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
        
        # Balance Check Tool
        check_balance_tool = Tool(
            name="check_balance",
            description="Get current account balance",
            category="finance",
            mvp_ready=True,
            parameters=[],
            handler=self._handle_check_balance
        )
        
        # Invoice Update Tool
        update_invoice_tool = Tool(
            name="update_invoice",
            description="Update fields on an existing invoice (e.g. due date, notes, status)",
            category="finance",
            mvp_ready=True,
            requires_confirmation=True,
            parameters=[
                ToolParameters(
                    name="invoice_id",
                    type="string",
                    description="ID of the invoice to update",
                    required=True
                ),
                ToolParameters(
                    name="due_date",
                    type="string",
                    description="New due date (ISO format)",
                    required=False
                ),
                ToolParameters(
                    name="notes",
                    type="string",
                    description="Updated notes",
                    required=False
                ),
                ToolParameters(
                    name="status",
                    type="string",
                    description="New status",
                    required=False,
                    enum=["DRAFT", "SENT", "PAID", "CANCELLED"]
                ),
            ],
            handler=self._handle_update_invoice
        )

        # Register MVP tools
        tool_registry.register_tools([
            create_invoice_tool,
            query_invoices_tool,
            update_invoice_tool,
            record_payment_tool,
            check_balance_tool,
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

    async def _handle_update_invoice(
        self,
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle invoice updates (due_date, notes, status, etc.)"""
        org_id = context.get("org_id", "default_org") if context else "default_org"
        auth_token = context.get("auth_token") if context else None

        invoice_id = params.get("invoice_id")
        if not invoice_id:
            raise Exception(
                "I need the invoice number to update it. "
                "Which invoice should I update?"
            )

        updates: Dict[str, Any] = {}
        if params.get("due_date"):
            updates["dueDate"] = params["due_date"]
        if params.get("notes"):
            updates["notes"] = params["notes"]
        if params.get("status"):
            updates["status"] = params["status"]

        if not updates:
            raise Exception(
                "I didn't catch what you'd like to change on the invoice. "
                "Please tell me the field and new value."
            )

        response = await self.backend.update_invoice(
            invoice_id=invoice_id,
            updates=updates
        )

        if response.success:
            changed = ", ".join(updates.keys())
            return {
                "invoice_id": invoice_id,
                "updated_fields": list(updates.keys()),
                "status": "updated",
                "message": f"Invoice {invoice_id} updated successfully ({changed}).",
            }
        else:
            raise Exception(response.error or f"Failed to update invoice {invoice_id}")

    
    async def _handle_create_invoice(
        self,
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle invoice creation.
        
        Accepts either:
        - Structured: params with 'items', 'subtotal', 'total' pre-built
        - Flat voice entities: params with 'amount', 'client_name', optionally 'entity_name' for item description
        """
        org_id = context.get("org_id", "default_org") if context else "default_org"
        user_id = context.get("user_id") if context else None
        # Per-request JWT forwarded from the voice session / frontend
        auth_token = context.get("auth_token") if context else None

        # Graceful fallback: use org_id when user_id is absent (unauthenticated voice)
        if not user_id or user_id == "unknown":
            logger.warning("user_id_missing_falling_back_to_org_id")
            user_id = org_id

        # ── Build items/subtotal/total from flat voice entities if not pre-built ──
        if "items" not in params or not params.get("items"):

            def _to_float(val, default=0.0) -> float:
                """Safely coerce a value to float; handles int, float, and numeric strings."""
                if val is None:
                    return default
                try:
                    return float(val)
                except (ValueError, TypeError):
                    return default

            # Amount may come as int/float or as a string like "80000"
            amount = _to_float(
                params.get("amount") or params.get("total") or params.get("unit_price")
            )

            # Item description — after entity_extractor fix, stored as "item_description"
            # Fall back to old "entity_name" key and then a generic label
            item_description = (
                params.get("item_description")
                or params.get("entity_name")
                or "Services"
            )

            # Quantity — now stored as "quantity" (after entity_extractor fix)
            quantity = _to_float(params.get("quantity"), default=1.0) or 1.0

            # Unit price — if the user gave us unit_price + quantity, derive total amount
            unit_price_override = _to_float(params.get("unit_price"))
            if unit_price_override and quantity and not _to_float(params.get("amount")):
                amount = unit_price_override * quantity

            unit_price = (amount / quantity) if quantity else amount

            params["items"] = [{
                "description": item_description,
                "quantity": quantity,
                "unitPrice": unit_price,
                "amount": amount,
            }]
            params["subtotal"] = amount
            params["tax"] = _to_float(params.get("tax"))
            params["total"] = amount + _to_float(params.get("tax"))

        # ── Require client_name ──
        client_name = params.get("client_name")
        if not client_name:
            raise Exception("I need a client name to create the invoice. Who should I bill?")

        # ── Due date — LLM stores it as "time_period" (mapped via DUE_DATE → TIME_PERIOD)
        #    Also accept "due_date" for backward compatibility
        due_date_raw = (
            params.get("due_date")
            or params.get("time_period")
        )
        if not due_date_raw:
            due_date = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")
        else:
            # Normalize if it looks like an ISO date, else pass through (backend handles it)
            due_date = str(due_date_raw)


        # 1. Lookup Client ID by Name — forward auth_token so backend doesn't 401
        client_resp = await self.backend.get_client_by_name(org_id, client_name, auth_token=auth_token)

        if not client_resp.success:
            raise Exception(f"Could not find client '{client_name}'. Please check the name and try again.")

        clients = client_resp.data
        if isinstance(clients, list):
            if not clients:
                raise Exception(f"No client named '{client_name}' found. Please create the client first.")
            client_id = clients[0].get("id")
        elif isinstance(clients, dict):
            client_id = clients.get("id")
        else:
            raise Exception(f"Unexpected response looking up client '{client_name}'.")

        if not client_id:
            raise Exception(f"Could not get an ID for client '{client_name}'.")

        # Generate required fields
        invoice_number = f"INV-{int(time.time())}"
        issue_date = datetime.now().strftime("%Y-%m-%d")
        # due_date already resolved above (reads "due_date" or "time_period" with 14-day fallback)

        # 2. Create Invoice — forward auth_token so backend doesn't 401
        response = await self.backend.create_invoice(
            org_id=org_id,
            user_id=user_id,
            client_id=client_id,
            invoice_number=invoice_number,
            issue_date=issue_date,
            items=params["items"],
            subtotal=float(params["subtotal"]),
            tax=float(params.get("tax", 0.0)),
            total=float(params["total"]),
            due_date=due_date,
            notes=params.get("notes"),
            auth_token=auth_token,
        )

        if response.success:
            invoice_data = response.data or {}
            return {
                "invoice_id": invoice_data.get("id"),
                "client_name": client_name,
                "total": params["total"],
                "status": "created",
                "message": f"Invoice created successfully for {client_name}",
            }
        else:
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
            Intent.INVOICE_UPDATE: "update_invoice",   # mapped — tool registered below
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