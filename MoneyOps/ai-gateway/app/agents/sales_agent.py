"""
Sales Agent - Strategic sales intelligence and CRM analytics
Handles CAC/LTV analysis, pipeline health, deal velocity, lead scoring
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import random

from app.agents.base_agent import BaseAgent, AgentResponse, ToolDefinition
from app.schemas.intents import Intent, AgentType
from app.adapters.backend_adapter import get_backend_adapter
from app.tools.tool_registry import Tool, ToolParameters, tool_registry
from app.utils.logger import get_logger
from app.intelligence.benchmarks import benchmark_service

logger = get_logger(__name__)


class SalesAgent(BaseAgent):
    """
    Sales Agent handles:
    - Customer Acquisition Cost (CAC) analysis
    - Lifetime Value (LTV) calculation
    - Sales pipeline health
    - Deal velocity tracking
    - Revenue forecasting
    - Lead scoring & prioritization
    """

    def __init__(self):
        super().__init__()
        self.backend = get_backend_adapter()
        self._register_sales_tools()
        logger.info("sales_agent_initialized")

    def get_agent_type(self) -> AgentType:
        return AgentType.SALES_AGENT

    def get_supported_intents(self) -> List[Intent]:
        return [
            Intent.SALES_STRATEGY,
            Intent.CUSTOMER_ACQUISITION,
            Intent.PRICING_STRATEGY,
            Intent.MARKETING_OPTIMIZATION,
            Intent.FORECAST_REQUEST,
            Intent.BENCHMARK_COMPARISON,
            Intent.TREND_ANALYSIS,
        ]

    def get_tools(self) -> List[ToolDefinition]:
        tools = tool_registry.get_tools_by_category("sales")
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

    def _register_sales_tools(self):
        """Register sales intelligence tools"""

        calculate_customer_metrics_tool = Tool(
            name="calculate_customer_metrics",
            description="Calculate CAC, LTV, and customer metrics",
            category="sales",
            mvp_ready=True,
            parameters=[
                ToolParameters(name="period", type="string", description="Analysis period", required=False, default="QUARTER")
            ],
            handler=self._handle_customer_metrics
        )

        analyze_sales_pipeline_tool = Tool(
            name="analyze_sales_pipeline",
            description="Analyze current sales pipeline health and deal velocity",
            category="sales",
            mvp_ready=True,
            parameters=[],
            handler=self._handle_pipeline_analysis
        )

        forecast_sales_tool = Tool(
            name="forecast_sales",
            description="Forecast sales revenue for next 3, 6, or 12 months",
            category="sales",
            mvp_ready=True,
            parameters=[
                ToolParameters(name="months", type="number", description="Forecast horizon in months", required=False, default=3)
            ],
            handler=self._handle_sales_forecast
        )

        tool_registry.register_tools([
            calculate_customer_metrics_tool,
            analyze_sales_pipeline_tool,
            forecast_sales_tool,
        ])

    async def _handle_customer_metrics(
        self,
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Calculate CAC, LTV, and related customer metrics"""
        org_id = context.get("org_id", "default_org") if context else "default_org"
        industry = context.get("industry", "IT & Software") if context else "IT & Software"

        # Fetch real data from backend
        invoices_resp = await self.backend.get_invoices(org_id=org_id, limit=100)
        payments_resp = await self.backend.get_payments(org_id=org_id, limit=100)

        invoices = []
        total_revenue = 0
        if invoices_resp.success and invoices_resp.data:
            invoices = invoices_resp.data.get("invoices", [])
            total_revenue = sum(inv.get("totalAmount", 0) for inv in invoices if inv.get("status") == "PAID")

        unique_clients = len(set(inv.get("clientId") for inv in invoices if inv.get("clientId")))
        paid_invoices = [inv for inv in invoices if inv.get("status") == "PAID"]

        # Calculate metrics
        avg_deal_size = (total_revenue / len(paid_invoices)) if paid_invoices else 45000
        # Estimate CAC (marketing spend not tracked, use heuristic)
        estimated_cac = avg_deal_size * 0.15 if avg_deal_size > 0 else 1850
        # Estimate LTV assuming 18-month average customer lifespan
        avg_monthly_revenue = avg_deal_size / 3  # assumptions
        estimated_ltv = avg_monthly_revenue * 18

        ltv_cac_ratio = estimated_ltv / estimated_cac if estimated_cac > 0 else 0

        # Benchmark comparison
        benchmarks = benchmark_service.get_industry_benchmarks(industry)
        cac_status = "good" if estimated_cac <= benchmarks.get("cac", 1200) else "high"

        return {
            "customer_metrics": {
                "total_clients": unique_clients,
                "total_revenue": round(total_revenue),
                "average_deal_size": round(avg_deal_size),
                "estimated_cac": round(estimated_cac),
                "estimated_ltv": round(estimated_ltv),
                "ltv_cac_ratio": round(ltv_cac_ratio, 2),
                "industry_avg_cac": benchmarks.get("cac", 1200),
                "industry_avg_ltv": benchmarks.get("ltv", 5000),
                "cac_health": cac_status,
            },
            "insights": [
                f"Your LTV:CAC ratio of {ltv_cac_ratio:.1f}x {'is healthy (>3x is good)' if ltv_cac_ratio >= 3 else 'needs improvement (target >3x)'}",
                f"Average deal size ₹{avg_deal_size:,.0f} vs industry avg ₹{benchmarks.get('ltv', 5000)/4:,.0f}",
                f"CAC is {'within' if cac_status == 'good' else 'above'} industry benchmark of ₹{benchmarks.get('cac', 1200):,}",
            ],
            "message": f"Customer metrics analyzed. LTV:CAC ratio: {ltv_cac_ratio:.1f}x, CAC: ₹{estimated_cac:,.0f}"
        }

    async def _handle_pipeline_analysis(
        self,
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyze sales pipeline health"""
        org_id = context.get("org_id", "default_org") if context else "default_org"

        invoices_resp = await self.backend.get_invoices(org_id=org_id, limit=100)
        invoices = []
        if invoices_resp.success and invoices_resp.data:
            invoices = invoices_resp.data.get("invoices", [])

        # Categorize pipeline stages
        draft = [i for i in invoices if i.get("status") == "DRAFT"]
        unpaid = [i for i in invoices if i.get("status") in ("UNPAID", "SENT")]
        overdue = [i for i in invoices if i.get("status") == "OVERDUE"]
        paid = [i for i in invoices if i.get("status") == "PAID"]

        pipeline_value = sum(i.get("totalAmount", 0) for i in unpaid + draft)
        at_risk_value = sum(i.get("totalAmount", 0) for i in overdue)
        won_value = sum(i.get("totalAmount", 0) for i in paid)

        conversion_rate = (len(paid) / len(invoices) * 100) if invoices else 0

        return {
            "pipeline": {
                "total_deals": len(invoices),
                "open_pipeline_value": round(pipeline_value),
                "at_risk_value": round(at_risk_value),
                "won_value": round(won_value),
                "conversion_rate": round(conversion_rate, 1),
                "stages": {
                    "draft": {"count": len(draft), "value": sum(i.get("totalAmount", 0) for i in draft)},
                    "pending": {"count": len(unpaid), "value": sum(i.get("totalAmount", 0) for i in unpaid)},
                    "overdue": {"count": len(overdue), "value": at_risk_value},
                    "won": {"count": len(paid), "value": won_value},
                }
            },
            "health_indicators": {
                "overdue_risk": "HIGH" if len(overdue) > len(invoices) * 0.2 else "LOW",
                "pipeline_velocity": "FAST" if conversion_rate > 70 else "SLOW",
            },
            "message": f"Pipeline: ₹{pipeline_value:,.0f} open, {conversion_rate:.0f}% conversion, ₹{at_risk_value:,.0f} at risk"
        }

    async def _handle_sales_forecast(
        self,
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Forecast revenue for next N months"""
        org_id = context.get("org_id", "default_org") if context else "default_org"
        months = int(params.get("months", 3))

        invoices_resp = await self.backend.get_invoices(org_id=org_id, limit=200)
        invoices = []
        if invoices_resp.success and invoices_resp.data:
            invoices = invoices_resp.data.get("invoices", [])

        paid = [i for i in invoices if i.get("status") == "PAID"]
        total_revenue = sum(i.get("totalAmount", 0) for i in paid)

        # Calculate monthly average (assume data covers last 3 months)
        monthly_avg = total_revenue / 3 if total_revenue > 0 else 250000
        # Apply growth rate assumption of 8% MoM
        growth_rate = 0.08

        forecast = []
        current_date = datetime.now()
        for i in range(1, months + 1):
            month_date = current_date + timedelta(days=30 * i)
            projected = monthly_avg * ((1 + growth_rate) ** i)
            forecast.append({
                "month": month_date.strftime("%B %Y"),
                "projected_revenue": round(projected),
                "growth_vs_current": round(((projected - monthly_avg) / monthly_avg) * 100, 1)
            })

        total_forecast = sum(f["projected_revenue"] for f in forecast)

        return {
            "forecast": {
                "horizon_months": months,
                "monthly_baseline": round(monthly_avg),
                "assumed_growth_rate": f"{growth_rate * 100:.0f}% MoM",
                "monthly_projections": forecast,
                "total_projected_revenue": round(total_forecast),
            },
            "message": f"{months}-month revenue forecast: ₹{total_forecast:,.0f} total projected"
        }

    async def process(
        self,
        intent: Intent,
        entities: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """Process sales-related intents"""
        logger.info("sales_agent_processing", intent=intent.value)

        if context and context.get("auth_token"):
            self.backend.set_auth_token(context["auth_token"])

        intent_to_tool = {
            Intent.SALES_STRATEGY: "analyze_sales_pipeline",
            Intent.CUSTOMER_ACQUISITION: "calculate_customer_metrics",
            Intent.PRICING_STRATEGY: "calculate_customer_metrics",
            Intent.MARKETING_OPTIMIZATION: "calculate_customer_metrics",
            Intent.FORECAST_REQUEST: "forecast_sales",
            Intent.BENCHMARK_COMPARISON: "calculate_customer_metrics",
            Intent.TREND_ANALYSIS: "analyze_sales_pipeline",
        }

        tool_name = intent_to_tool.get(intent)
        if not tool_name:
            return self._build_error_response(f"No tool for intent: {intent.value}")

        try:
            tool = tool_registry.get_tool(tool_name)
            if not tool:
                return self._build_error_response(f"Tool {tool_name} not found")

            result = await tool_registry.execute_tool(
                tool_name=tool_name,
                parameters=entities,
                context=context
            )

            if result.success:
                return self._build_success_response(
                    message=result.result.get("message", "Analysis complete"),
                    data=result.result,
                    tool_used=tool_name
                )
            else:
                return self._build_error_response(result.error or "Tool execution failed")

        except Exception as e:
            logger.error("sales_agent_error", error=str(e))
            return self._build_error_response(str(e))


# Singleton
sales_agent = SalesAgent()
