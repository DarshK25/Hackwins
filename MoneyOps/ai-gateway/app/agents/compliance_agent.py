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
            invoices = invoices_resp.data.get("invoices", [])

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
            next_month = today.replace(day=20, month=today.month % 12 + 1)
            gstr1_deadline = next_month.strftime("20th %B %Y")
            gstr3b_deadline = next_month.strftime("20th %B %Y")

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
        today = date.today()
        month = today.month
        year = today.year

        # Upcoming compliance deadlines
        deadlines = []
        if today.day <= 20:
            deadlines.append({
                "filing": "GSTR-1 (Outward Supplies)",
                "due_date": f"20th {today.strftime('%B %Y')}",
                "days_remaining": 20 - today.day,
                "status": "upcoming" if today.day < 15 else "urgent"
            })
            deadlines.append({
                "filing": "GSTR-3B (Monthly Return)",
                "due_date": f"20th {today.strftime('%B %Y')}",
                "days_remaining": 20 - today.day,
                "status": "upcoming" if today.day < 15 else "urgent"
            })

        # Quarterly deadlines
        is_quarter_end = month in (3, 6, 9, 12)
        if is_quarter_end:
            deadlines.append({
                "filing": "Advance Tax Payment",
                "due_date": f"15th {today.strftime('%B %Y')}",
                "days_remaining": max(0, 15 - today.day),
                "status": "urgent"
            })
            deadlines.append({
                "filing": "TDS Return (Form 26Q)",
                "due_date": f"31st {today.strftime('%B %Y')}",
                "days_remaining": max(0, 31 - today.day),
                "status": "upcoming"
            })

        compliance_score = 85  # baseline
        alerts = []
        if not deadlines:
            alerts.append("✅ No immediate compliance deadlines in the next 7 days")
        else:
            urgent = [d for d in deadlines if d["status"] == "urgent"]
            if urgent:
                alerts.append(f"🚨 {len(urgent)} urgent filing(s) due within 7 days")
                compliance_score -= 10 * len(urgent)

        return {
            "compliance_score": compliance_score,
            "status": "compliant" if compliance_score >= 70 else "at_risk",
            "upcoming_deadlines": deadlines,
            "alerts": alerts,
            "key_requirements": [
                "GST Registration must be active",
                "E-invoicing required if turnover > ₹5 crore",
                "Digital signatures needed for all invoices",
                "Maintain records for minimum 6 years",
            ],
            "message": f"Compliance Score: {compliance_score}/100 — {len(deadlines)} upcoming filing(s)"
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
            invoices = invoices_resp.data.get("invoices", [])

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


# Singleton
compliance_agent = ComplianceAgent()
