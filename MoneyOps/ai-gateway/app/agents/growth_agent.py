"""
Growth Agent - Market expansion, pricing optimization, revenue modeling
Handles pricing strategy, market segments, growth opportunity mapping
"""
from typing import Dict, Any, List, Optional

from app.agents.base_agent import BaseAgent, AgentResponse, ToolDefinition
from app.schemas.intents import Intent, AgentType
from app.adapters.backend_adapter import get_backend_adapter
from app.tools.tool_registry import Tool, ToolParameters, tool_registry
from app.utils.logger import get_logger
from app.intelligence.benchmarks import benchmark_service

logger = get_logger(__name__)


class GrowthAgent(BaseAgent):
    """
    Growth Agent handles:
    - Market expansion analysis
    - Pricing optimization
    - New revenue stream identification  
    - Segment opportunity mapping
    - Product/service recommendations
    """

    def __init__(self):
        super().__init__()
        self.backend = get_backend_adapter()
        self._register_growth_tools()
        logger.info("growth_agent_initialized")

    def get_agent_type(self) -> AgentType:
        return AgentType.GROWTH_AGENT

    def get_supported_intents(self) -> List[Intent]:
        return [
            Intent.MARKET_EXPANSION,
            Intent.PRICING_STRATEGY,
            Intent.PRODUCT_STRATEGY,
            Intent.SCALING_ADVICE,
        ]

    def get_tools(self) -> List[ToolDefinition]:
        tools = tool_registry.get_tools_by_category("growth")
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

    def _register_growth_tools(self):
        pricing_tool = Tool(
            name="optimize_pricing",
            description="Analyze and optimize pricing strategy based on deal data",
            category="growth",
            mvp_ready=True,
            parameters=[],
            handler=self._handle_pricing_optimization
        )

        market_tool = Tool(
            name="analyze_market_expansion",
            description="Identify market expansion opportunities",
            category="growth",
            mvp_ready=True,
            parameters=[],
            handler=self._handle_market_expansion
        )

        tool_registry.register_tools([pricing_tool, market_tool])

    async def _handle_pricing_optimization(
        self,
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Optimize pricing strategy from deal data"""
        org_id = context.get("org_id", "default_org") if context else "default_org"
        industry = context.get("industry", "IT & Software") if context else "IT & Software"

        invoices_resp = await self.backend.get_invoices(org_id=org_id, limit=200)
        invoices = []
        if invoices_resp.success and invoices_resp.data:
            invoices = invoices_resp.data.get("invoices", [])

        paid = [i for i in invoices if i.get("status") == "PAID"]
        amounts = [i.get("totalAmount", 0) for i in paid if i.get("totalAmount", 0) > 0]

        avg_deal = sum(amounts) / len(amounts) if amounts else 45000
        min_deal = min(amounts) if amounts else 10000
        max_deal = max(amounts) if amounts else 150000
        
        benchmarks = benchmark_service.get_industry_benchmarks(industry)
        industry_ltv = benchmarks.get("ltv", 50000)

        # Pricing recommendations
        tiers = [
            {
                "tier": "Starter",
                "price_range": f"₹{min_deal:,.0f} – ₹{avg_deal*0.6:,.0f}",
                "target": "SMB clients, project-based",
                "strategy": "High volume, low friction"
            },
            {
                "tier": "Growth",
                "price_range": f"₹{avg_deal*0.6:,.0f} – ₹{avg_deal*1.2:,.0f}",
                "target": "Mid-market, retainer-based",
                "strategy": "Your current sweet spot — maximize with upsells"
            },
            {
                "tier": "Enterprise",
                "price_range": f"₹{avg_deal*1.5:,.0f}+",
                "target": "Large organizations, long-term contracts",
                "strategy": "High margin, relationship-driven — expand here"
            }
        ]

        return {
            "pricing_analysis": {
                "current_avg_deal": round(avg_deal),
                "min_deal": round(min_deal),
                "max_deal": round(max_deal),
                "industry_avg_ltv": industry_ltv,
                "pricing_gap": f"₹{max(0, industry_ltv/4 - avg_deal):,.0f} below market for mid-tier"
            },
            "recommended_tiers": tiers,
            "pricing_recommendations": [
                f"Your avg deal ₹{avg_deal:,.0f} is {'above' if avg_deal > industry_ltv/4 else 'below'} industry benchmark",
                "Introduce annual contract pricing with 15-20% discount to lock in revenue",
                "Bundle complementary services to increase avg deal size by 25-30%",
                "Test premium pricing for enterprise accounts — often 2-3x more",
            ],
            "message": f"Pricing Analysis: Avg deal ₹{avg_deal:,.0f}, {len(tiers)} tier strategy recommended"
        }

    async def _handle_market_expansion(
        self,
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Market expansion opportunity analysis"""
        industry = context.get("industry", "IT & Software") if context else "IT & Software"

        opportunities = [
            {
                "segment": "Enterprise Clients",
                "market_size": "Large",
                "entry_difficulty": "Medium",
                "revenue_potential": "+40-60% per deal",
                "timeline": "3-6 months",
                "actions": ["Build case studies from existing wins", "Hire dedicated enterprise sales rep", "Create enterprise-grade SLA documentation"]
            },
            {
                "segment": "Geographic Expansion",
                "market_size": "Very Large",
                "entry_difficulty": "High",
                "revenue_potential": "+2x addressable market",
                "timeline": "6-12 months",
                "actions": ["Identify Tier 2 cities with growing startup ecosystem", "Local partnerships for initial traction", "Adapt pricing for regional purchasing power"]
            },
            {
                "segment": "Adjacent Industry Verticals",
                "market_size": "Medium",
                "entry_difficulty": "Low",
                "revenue_potential": "+20-30% new revenue",
                "timeline": "1-3 months",
                "actions": ["Map your current service to adjacent verticals", "Create vertical-specific case studies", "Test with 2-3 pilot clients per vertical"]
            },
            {
                "segment": "Platform/Product Offering",
                "market_size": "Large",
                "entry_difficulty": "High",
                "revenue_potential": "10x long-term",
                "timeline": "12-24 months",
                "actions": ["Identify recurring pain points across client base", "Package know-how into SaaS product", "Start with internal tools, productize later"]
            }
        ]

        return {
            "expansion_opportunities": opportunities,
            "recommended_priority": "Enterprise clients offer the fastest path to significant revenue increase with lowest operational risk",
            "90_day_playbook": [
                "Week 1-2: Audit existing clients to identify enterprise expansion potential",
                "Week 3-4: Develop enterprise pitch deck and case studies",
                "Week 5-8: Launch outbound to 50 enterprise prospects",
                "Week 9-12: Close first 2-3 enterprise deals, measure and refine"
            ],
            "message": f"Market Expansion: 4 high-potential growth vectors identified for {industry}"
        }

    async def process(
        self,
        intent: Intent,
        entities: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        logger.info("growth_agent_processing", intent=intent.value)

        if context and context.get("auth_token"):
            self.backend.set_auth_token(context["auth_token"])

        intent_to_tool = {
            Intent.PRICING_STRATEGY: "optimize_pricing",
            Intent.MARKET_EXPANSION: "analyze_market_expansion",
            Intent.PRODUCT_STRATEGY: "analyze_market_expansion",
            Intent.SCALING_ADVICE: "analyze_market_expansion",
        }

        tool_name = intent_to_tool.get(intent, "analyze_market_expansion")

        try:
            result = await tool_registry.execute_tool(tool_name=tool_name, parameters=entities, context=context)
            if result.success:
                return self._build_success_response(
                    message=result.result.get("message", "Growth analysis complete"),
                    data=result.result,
                    tool_used=tool_name
                )
            return self._build_error_response(result.error or "Growth tool failed")
        except Exception as e:
            logger.error("growth_agent_error", error=str(e))
            return self._build_error_response(str(e))


# Singleton
growth_agent = GrowthAgent()
