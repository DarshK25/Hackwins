"""
Compliance Agent - GST, tax, regulatory intelligence
Handles compliance queries, tax calculations, filing reminders, audit readiness
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, date
from urllib.parse import urlencode

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

        tds_obligations_tool = Tool(
            name="calculate_tds_obligations",
            description="Calculate vendor-side TDS obligations and client-side TDS credits",
            category="compliance",
            mvp_ready=True,
            parameters=[
                ToolParameters(name="financial_year", type="string", description="Financial year like 2026-27", required=False)
            ],
            handler=self._handle_tds_obligations
        )

        tool_registry.register_tools([
            gst_calculator_tool,
            compliance_check_tool,
            audit_readiness_tool,
            tds_obligations_tool,
        ])

    def _context_identity(self, context: Optional[Dict[str, Any]]) -> Dict[str, Optional[str]]:
        return {
            "org_id": context.get("org_id", "default_org") if context else "default_org",
            "user_id": context.get("user_id") if context else None,
        }

    async def _backend_get(self, path: str, context: Optional[Dict[str, Any]] = None) -> Any:
        identity = self._context_identity(context)
        return await self.backend.get(
            path,
            org_id=identity["org_id"],
            user_id=identity["user_id"],
        )

    async def _handle_gst_calculation(
        self,
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Calculate GST from the backend compliance engine."""
        period = params.get("period")
        query = f"?{urlencode({'period': period})}" if period else ""
        gst_summary = await self._backend_get(f"/api/compliance/gst/summary{query}", context)

        return {
            "gst_summary": gst_summary,
            "recommendations": [
                f"GSTR-1 should include all {gst_summary.get('invoicesReported', 0)} invoices raised in the period.",
                "Use claimable ITC only from expenses with GST amount, vendor GSTIN, and eligible category.",
                "Resolve ITC-risk items before filing GSTR-3B to avoid overstating net GST payable.",
            ],
            "message": (
                f"GSTR-3B net GST payable is ₹{float(gst_summary.get('netGstPayable', 0) or 0):,.0f} "
                f"for {gst_summary.get('period', 'this period')}."
            )
        }

    async def _handle_compliance_check(
        self,
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Fetch compliance status and filing issues from backend."""
        status = await self._backend_get("/api/compliance/status", context)
        next_deadline = status.get("nextDeadline") or {}
        gst_summary = status.get("gstSummary") or {}
        return {
            **status,
            "message": (
                f"Compliance score {status.get('complianceScore', 0)}/100. "
                f"{next_deadline.get('title', 'Next filing')} is due in {next_deadline.get('daysRemaining', '-') } days. "
                f"Net GST payable is ₹{float(gst_summary.get('netGstPayable', 0) or 0):,.0f}."
            )
        }

    async def _handle_audit_readiness(
        self,
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Get audit readiness from backend."""
        audit = await self._backend_get("/api/compliance/audit/readiness", context)
        return {
            **audit,
            "message": (
                f"Audit readiness is {audit.get('auditReadinessScore', 0)}/100. "
                f"{audit.get('message', 'Review the checklist before filing.')}"
            )
        }

    async def _handle_tds_obligations(
        self,
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        financial_year = params.get("financial_year")
        query = f"?{urlencode({'fy': financial_year})}" if financial_year else ""
        obligations = await self._backend_get(f"/api/compliance/tds/obligations{query}", context)
        return {
            **obligations,
            "message": (
                f"TDS to deduct is ₹{float(obligations.get('totalTdsToDeduct', 0) or 0):,.0f}. "
                f"Form 26AS-style credits identified: ₹{float(obligations.get('totalTdsCredits', 0) or 0):,.0f}."
            )
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
