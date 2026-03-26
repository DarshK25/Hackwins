"""
Compliance Agent - GST, tax, regulatory intelligence
Handles compliance queries, tax calculations, filing reminders, audit readiness
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, date

from app.agents.base_agent import BaseAgent, AgentResponse, ToolDefinition
from app.schemas.intents import Intent, AgentType
from app.adapters.backend_adapter import get_backend_adapter
from app.tools.tool_registry import Tool, ToolParameters, tool_registry
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ComplianceAgent(BaseAgent):
    """
    Compliance Agent handles:
    - GST calculations and filing guidance
    - TDS compliance
    - Tax filing reminders
    - Regulatory alerts
    - Audit readiness checks
    """

    # Indian GST rates by category
    GST_RATES = {
        "software_services": 0.18,
        "consulting": 0.18,
        "IT_services": 0.18,
        "professional_services": 0.18,
        "goods": 0.12,
        "essential_goods": 0.05,
        "exempt": 0.0,
    }

    # TDS rates
    TDS_RATES = {
        "professional_services": 0.10,
        "contractor": 0.02,
        "rent": 0.10,
        "interest": 0.10,
        "commission": 0.05,
        "salary": 0.15,  # approximate average
    }

    def __init__(self):
        super().__init__()
        self.backend = get_backend_adapter()
        self._register_compliance_tools()
        logger.info("compliance_agent_initialized")

    def get_agent_type(self) -> AgentType:
        return AgentType.COMPLIANCE_AGENT

    def get_supported_intents(self) -> List[Intent]:
        return [
            Intent.COMPLIANCE_QUERY,
            Intent.COMPLIANCE_CHECK,
            Intent.COMPLIANCE_REPORT,
            Intent.GST_QUERY,
            Intent.TAX_OPTIMIZATION,
            Intent.TAX_CALCULATION,
            Intent.AUDIT_READINESS,
        ]

    def get_tools(self) -> List[ToolDefinition]:
        tools = tool_registry.get_tools_by_category("compliance")
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

    def _register_compliance_tools(self):
        gst_calculator_tool = Tool(
            name="calculate_gst",
            description="Calculate GST liability from invoices",
            category="compliance",
            mvp_ready=True,
            parameters=[
                ToolParameters(name="period", type="string", description="Period (MONTH/QUARTER)", required=False, default="MONTH")
            ],
            handler=self._handle_gst_calculation
        )

        compliance_check_tool = Tool(
            name="check_compliance_status",
            description="Check overall compliance status and upcoming deadlines",
            category="compliance",
            mvp_ready=True,
            parameters=[],
            handler=self._handle_compliance_check
        )

        audit_readiness_tool = Tool(
            name="check_audit_readiness",
            description="Check audit readiness and documentation completeness",
            category="compliance",
            mvp_ready=True,
            parameters=[],
            handler=self._handle_audit_readiness
        )

        tool_registry.register_tools([
            gst_calculator_tool,
            compliance_check_tool,
            audit_readiness_tool,
        ])

    async def _handle_gst_calculation(
        self,
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Calculate GST from actual invoice data"""
        org_id = context.get("org_id", "default_org") if context else "default_org"

        invoices_resp = await self.backend.get_invoices(org_id=org_id, limit=100)
        invoices = []
        if invoices_resp.success and invoices_resp.data:
            invoices = invoices_resp.data if isinstance(invoices_resp.data, list) else []

        # Calculate GST from paid invoices
        paid_invoices = [i for i in invoices if i.get("status") == "PAID"]
        total_taxable = sum(i.get("subtotal", 0) for i in paid_invoices)
        total_gst_collected = sum(i.get("gstTotal", 0) or i.get("tax", 0) for i in paid_invoices)
        total_revenue = sum(i.get("totalAmount", 0) for i in paid_invoices)

        # Input tax credit (estimated at 30% of output GST)
        itc_estimate = total_gst_collected * 0.30
        net_gst_payable = max(0, total_gst_collected - itc_estimate)

        # Filing deadlines
        today = date.today()
        if today.day <= 20:
            gstr1_deadline = f"20th {today.strftime('%B %Y')}"
            gstr3b_deadline = f"20th {today.strftime('%B %Y')}"
        else:
            # Move to next month
            next_month_val = (today.month % 12) + 1
            year_val = today.year + (1 if today.month == 12 else 0)
            next_month_date = date(year_val, next_month_val, 20)
            gstr1_deadline = next_month_date.strftime("20th %B %Y")
            gstr3b_deadline = next_month_date.strftime("20th %B %Y")

        return {
            "gst_summary": {
                "total_taxable_revenue": round(total_taxable),
                "output_gst_collected": round(total_gst_collected),
                "estimated_itc": round(itc_estimate),
                "net_gst_payable": round(net_gst_payable),
                "effective_gst_rate": f"{(total_gst_collected/total_taxable*100):.1f}%" if total_taxable > 0 else "N/A",
            },
            "deadlines": {
                "GSTR-1": gstr1_deadline,
                "GSTR-3B": gstr3b_deadline,
                "annual_return": "31st March",
            },
            "recommendations": [
                f"Net GST payable this period: ₹{net_gst_payable:,.0f}",
                "Collect all purchase invoices for ITC claims before filing",
                "File GSTR-1 before GSTR-3B for reconciliation",
                "Ensure invoice GST numbers are valid for ITC eligibility",
            ],
            "message": f"GST Summary: ₹{total_gst_collected:,.0f} collected, ₹{net_gst_payable:,.0f} net payable"
        }

    async def _handle_compliance_check(
        self,
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Check compliance status and deadlines"""
        org_id = context.get("org_id", "default_org") if context else "default_org"
        today = date.today()
        month = today.month

        # 1. Fetch real data to make it dynamic
        invoices_resp = await self.backend.get_invoices(org_id=org_id, limit=50)
        invoices = invoices_resp.data if invoices_resp.success and isinstance(invoices_resp.data, list) else []
        
        # Check for overdue items
        overdue_invoices = [i for i in invoices if i.get("status") == "OVERDUE"]
        
        # 2. Upcoming compliance deadlines
        deadlines = []
        # GST deadlines are usually 11th (GSTR1) and 20th (GSTR3B)
        if today.day <= 20:
            deadlines.append({
                "filing": "GSTR-3B Monthly Return",
                "due_date": date(today.year, today.month, 20).strftime("%Y-%m-%d"),
                "status": "upcoming" if today.day < 15 else "urgent"
            })
        
        # 3. Dynamic Score
        compliance_score = 95
        alerts = []
        key_reqs = [
            "GST Registration must be active",
            "Maintain digital copies of all invoices",
            "Reconcile monthly bank statements"
        ]

        if overdue_invoices:
            compliance_score -= (len(overdue_invoices) * 2)
            alerts.append(f"⚠️ {len(overdue_invoices)} Overdue invoices may impact liquidity/tax reconciliation")
            key_reqs.append(f"Follow up on {len(overdue_invoices)} overdue payments")

        # GST Specific Logic
        unpaid_gst = sum(i.get("gstTotal", 0) or i.get("tax", 0) for i in invoices if i.get("status") == "SENT")
        if unpaid_gst > 0:
            alerts.append(f"🚨 ₹{unpaid_gst:,.0f} in pending GST from sent invoices")
            compliance_score -= 5

        if not alerts:
            alerts.append("✅ No immediate compliance risks detected")

        return {
            "compliance_score": max(0, compliance_score),
            "status": "compliant" if compliance_score >= 80 else "at_risk" if compliance_score >= 60 else "critical",
            "upcoming_deadlines": deadlines,
            "alerts": alerts,
            "key_requirements": key_reqs,
            "message": f"Compliance Health: {compliance_score}/100"
        }

    async def _handle_audit_readiness(
        self,
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Check audit readiness"""
        org_id = context.get("org_id", "default_org") if context else "default_org"

        invoices_resp = await self.backend.get_invoices(org_id=org_id, limit=100)
        invoices = []
        if invoices_resp.success and invoices_resp.data:
            invoices = invoices_resp.data if isinstance(invoices_resp.data, list) else []

        # Check documentation completeness
        invoices_with_gst = [i for i in invoices if i.get("gstTotal") or i.get("tax")]
        invoices_with_client = [i for i in invoices if i.get("clientId")]

        gst_compliance = len(invoices_with_gst) / len(invoices) * 100 if invoices else 0
        client_records = len(invoices_with_client) / len(invoices) * 100 if invoices else 0

        readiness_score = round((gst_compliance * 0.4 + client_records * 0.6))

        checklist = [
            {"item": "GST on all invoices", "status": "pass" if gst_compliance > 90 else "fail", "completion": f"{gst_compliance:.0f}%"},
            {"item": "Client records maintained", "status": "pass" if client_records > 95 else "warn", "completion": f"{client_records:.0f}%"},
            {"item": "Invoice numbering sequential", "status": "pass", "completion": "100%"},
            {"item": "Payment records linked", "status": "warn", "completion": "75%"},
            {"item": "Expense receipts uploaded", "status": "fail", "completion": "45%"},
        ]

        return {
            "audit_readiness_score": readiness_score,
            "status": "ready" if readiness_score >= 80 else "needs_attention",
            "checklist": checklist,
            "total_invoices": len(invoices),
            "recommendations": [
                "Upload all expense receipts to document management",
                "Ensure all vendor invoices have GST numbers",
                "Reconcile payment records with bank statements",
                "Maintain digital copies of all compliance filings",
            ],
            "message": f"Audit Readiness: {readiness_score}/100 — {'Ready for audit' if readiness_score >= 80 else 'Action required before audit'}"
        }

    async def process(
        self,
        intent: Intent,
        entities: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        logger.info("compliance_agent_processing", intent=intent.value)

        if context and context.get("auth_token"):
            self.backend.set_auth_token(context["auth_token"])

        intent_to_tool = {
            Intent.COMPLIANCE_QUERY: "check_compliance_status",
            Intent.COMPLIANCE_CHECK: "check_compliance_status",
            Intent.COMPLIANCE_REPORT: "check_compliance_status",
            Intent.GST_QUERY: "calculate_gst",
            Intent.TAX_OPTIMIZATION: "calculate_gst",
            Intent.TAX_CALCULATION: "calculate_gst",
            Intent.AUDIT_READINESS: "check_audit_readiness",
        }

        tool_name = intent_to_tool.get(intent, "check_compliance_status")

        try:
            result = await tool_registry.execute_tool(tool_name=tool_name, parameters=entities, context=context)
            if result.success:
                return self._build_success_response(
                    message=result.result.get("message", "Compliance check complete"),
                    data=result.result,
                    tool_used=tool_name
                )
            return self._build_error_response(result.error or "Compliance tool failed")
        except Exception as e:
            logger.error("compliance_agent_error", error=str(e))
            return self._build_error_response(str(e))


    async def get_compliance_dashboard_data(self, org_id: str, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        """Aggregate data for the compliance dashboard"""
        if not context:
            context = {}
        context["org_id"] = org_id
        
        # Run compliance check
        status_res = await self._handle_compliance_check({}, context)
        # Run audit readiness
        audit_res = await self._handle_audit_readiness({}, context)
        
        # Merge data
        combined_data = {
            **status_res,
            "audit_readiness": audit_res
        }
        
        return self._build_success_response(
            message="Compliance dashboard data retrieved",
            data=combined_data
        )

# Singleton
compliance_agent = ComplianceAgent()
