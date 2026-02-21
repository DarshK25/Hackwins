"""
Strategy Agent - Executive-level strategic intelligence and multi-agent synthesis
Handles SWOT, competitive analysis, growth planning, and cross-agent synthesis
"""
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.agents.base_agent import BaseAgent, AgentResponse, ToolDefinition
from app.schemas.intents import Intent, AgentType
from app.adapters.backend_adapter import get_backend_adapter
from app.tools.tool_registry import Tool, ToolParameters, tool_registry
from app.utils.logger import get_logger
from app.intelligence.benchmarks import benchmark_service

logger = get_logger(__name__)


class StrategyAgent(BaseAgent):
    """
    Strategy Agent - The executive-level brain of MoneyOps.
    Synthesizes insights from all agents to deliver boardroom-quality advice.

    Responsibilities:
    - Multi-agent data synthesis
    - SWOT analysis
    - Competitive positioning
    - Growth strategy recommendations
    - Business health scoring
    - Problem root-cause diagnosis
    """

    def __init__(self):
        super().__init__()
        self.backend = get_backend_adapter()
        self._register_strategy_tools()
        logger.info("strategy_agent_initialized")

    def get_agent_type(self) -> AgentType:
        return AgentType.STRATEGY_AGENT

    def get_supported_intents(self) -> List[Intent]:
        return [
            Intent.BUSINESS_HEALTH_CHECK,
            Intent.PROBLEM_DIAGNOSIS,
            Intent.GROWTH_STRATEGY,
            Intent.MARKET_EXPANSION,
            Intent.SCALING_ADVICE,
            Intent.SWOT_ANALYSIS,
            Intent.SCENARIO_PLANNING,
            Intent.GOAL_SETTING,
            Intent.COMPETITIVE_POSITIONING,
            Intent.PARTNERSHIP_OPPORTUNITIES,
            Intent.RISK_ASSESSMENT,
            Intent.PROFIT_OPTIMIZATION,
            Intent.INVESTMENT_ADVICE,
            Intent.DEBT_MANAGEMENT,
            Intent.BUDGET_OPTIMIZATION,
            Intent.CASH_FLOW_PLANNING,
            Intent.PRODUCT_STRATEGY,
        ]

    def get_tools(self) -> List[ToolDefinition]:
        tools = tool_registry.get_tools_by_category("strategy")
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

    def _register_strategy_tools(self):
        health_score_tool = Tool(
            name="calculate_business_health_score",
            description="Calculate comprehensive business health score /100 with component breakdown",
            category="strategy",
            mvp_ready=True,
            parameters=[],
            handler=self._handle_business_health_score
        )

        swot_tool = Tool(
            name="perform_swot_analysis",
            description="Generate SWOT analysis based on financial data",
            category="strategy",
            mvp_ready=True,
            parameters=[],
            handler=self._handle_swot_analysis
        )

        growth_tool = Tool(
            name="generate_growth_strategies",
            description="Generate tailored growth strategies with estimated impact",
            category="strategy",
            mvp_ready=True,
            parameters=[],
            handler=self._handle_growth_strategies
        )

        diagnose_tool = Tool(
            name="diagnose_business_problem",
            description="Diagnose business problems with root cause analysis and recommendations",
            category="strategy",
            mvp_ready=True,
            parameters=[
                ToolParameters(name="problem", type="string", description="Problem to diagnose", required=False)
            ],
            handler=self._handle_problem_diagnosis
        )

        competitive_tool = Tool(
            name="analyze_competitive_position",
            description="Analyze competitive position vs industry benchmarks",
            category="strategy",
            mvp_ready=True,
            parameters=[],
            handler=self._handle_competitive_analysis
        )

        tool_registry.register_tools([
            health_score_tool,
            swot_tool,
            growth_tool,
            diagnose_tool,
            competitive_tool,
        ])

    async def _handle_business_health_score(
        self,
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Calculate comprehensive business health score"""
        org_id = context.get("org_id", "default_org") if context else "default_org"

        # Fetch real data
        invoices_resp = await self.backend.get_invoices(org_id=org_id, limit=200)
        balance_resp = await self.backend.get_balance(org_id=org_id)

        invoices = []
        if invoices_resp.success and invoices_resp.data:
            invoices = invoices_resp.data.get("invoices", [])

        total_revenue = sum(i.get("totalAmount", 0) for i in invoices if i.get("status") == "PAID")
        overdue = [i for i in invoices if i.get("status") == "OVERDUE"]
        paid = [i for i in invoices if i.get("status") == "PAID"]
        total = len(invoices)

        # Component scores (0-100 each)
        # 1. Cash Flow Health
        balance = 0
        if balance_resp.success and balance_resp.data:
            balance = balance_resp.data.get("balance", 0)
        cash_flow_score = min(100, max(0, 50 + (balance / 10000)))

        # 2. Collection Efficiency
        collection_rate = (len(paid) / total * 100) if total > 0 else 0
        overdue_rate = (len(overdue) / total * 100) if total > 0 else 0
        collection_score = max(0, collection_rate - overdue_rate * 2)

        # 3. Revenue Growth (estimate)
        recent_invoices = sorted(invoices, key=lambda x: x.get("issueDate", ""), reverse=True)
        if len(recent_invoices) >= 2:
            recent_half = recent_invoices[:len(recent_invoices)//2]
            older_half = recent_invoices[len(recent_invoices)//2:]
            recent_rev = sum(i.get("totalAmount", 0) for i in recent_half if i.get("status") == "PAID")
            older_rev = sum(i.get("totalAmount", 0) for i in older_half if i.get("status") == "PAID")
            growth_rate = ((recent_rev - older_rev) / older_rev * 100) if older_rev > 0 else 0
            growth_score = min(100, max(0, 50 + growth_rate * 2))
        else:
            growth_score = 50

        # 4. Profitability
        profitability_score = min(100, max(0, collection_score * 0.7 + growth_score * 0.3))

        # Overall weighted score
        overall_score = (
            cash_flow_score * 0.30 +
            collection_score * 0.35 +
            growth_score * 0.25 +
            profitability_score * 0.10
        )
        overall_score = round(overall_score)

        status = "excellent" if overall_score >= 80 else "healthy" if overall_score >= 65 else "warning" if overall_score >= 45 else "critical"

        recommendations = []
        if collection_score < 60:
            recommendations.append("⚠️ Collection efficiency is low. Implement automated payment reminders and offer early-payment incentives.")
        if len(overdue) > 0:
            overdue_value = sum(i.get("totalAmount", 0) for i in overdue)
            recommendations.append(f"🚨 ₹{overdue_value:,.0f} overdue across {len(overdue)} invoices. Prioritize collection immediately.")
        if growth_score < 50:
            recommendations.append("📈 Revenue growth below target. Review pricing strategy and expand to new customer segments.")
        if overall_score >= 75:
            recommendations.append("✅ Business health is strong. Consider reinvesting surplus into growth initiatives.")

        return {
            "health_score": overall_score,
            "status": status,
            "components": {
                "cash_flow": {"score": round(cash_flow_score), "label": "Cash Flow Health"},
                "collections": {"score": round(collection_score), "label": "Collection Efficiency"},
                "growth": {"score": round(growth_score), "label": "Revenue Growth"},
                "profitability": {"score": round(profitability_score), "label": "Profitability"},
            },
            "recommendations": recommendations,
            "raw_metrics": {
                "total_revenue": round(total_revenue),
                "current_balance": round(balance),
                "collection_rate": round(collection_rate, 1),
                "overdue_count": len(overdue),
                "total_invoices": total,
            },
            "last_calculated": datetime.now().isoformat(),
            "message": f"Business Health Score: {overall_score}/100 ({status})"
        }

    async def _handle_swot_analysis(
        self,
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate SWOT analysis from financial data"""
        org_id = context.get("org_id", "default_org") if context else "default_org"
        industry = context.get("industry", "IT & Software") if context else "IT & Software"

        invoices_resp = await self.backend.get_invoices(org_id=org_id, limit=200)
        invoices = []
        if invoices_resp.success and invoices_resp.data:
            invoices = invoices_resp.data.get("invoices", [])

        paid = [i for i in invoices if i.get("status") == "PAID"]
        overdue = [i for i in invoices if i.get("status") == "OVERDUE"]
        total_rev = sum(i.get("totalAmount", 0) for i in paid)
        collection_rate = (len(paid) / len(invoices) * 100) if invoices else 0
        overdue_value = sum(i.get("totalAmount", 0) for i in overdue)

        strengths = []
        weaknesses = []
        opportunities = []
        threats = []

        if collection_rate > 80:
            strengths.append(f"High collection rate ({collection_rate:.0f}%) indicates strong client relationships")
        if total_rev > 100000:
            strengths.append(f"Solid revenue base of ₹{total_rev:,.0f}")
        if len(paid) > 5:
            strengths.append(f"Diversified client base with {len(paid)} successful transactions")

        if overdue_value > 0:
            weaknesses.append(f"₹{overdue_value:,.0f} in overdue receivables hurting cash flow")
        if collection_rate < 70:
            weaknesses.append("Low collection efficiency impacting working capital")
        if len(invoices) < 10:
            weaknesses.append("Small invoice volume suggests limited market penetration")

        opportunities.append("Expand to enterprise clients for higher deal sizes")
        opportunities.append("Implement subscription/retainer models for recurring revenue")
        opportunities.append(f"{industry} sector growing — right time to scale")
        opportunities.append("Cross-sell additional services to existing clients")

        threats.append("Rising competition in the market segment")
        threats.append("Customer concentration risk if top 3 clients exceed 50% of revenue")
        threats.append("Economic slowdown could delay payments further")

        return {
            "swot": {
                "strengths": strengths,
                "weaknesses": weaknesses,
                "opportunities": opportunities,
                "threats": threats,
            },
            "strategic_priority": "Focus on converting overdue receivables to cash while expanding enterprise pipeline",
            "message": f"SWOT Analysis complete: {len(strengths)} strengths, {len(weaknesses)} weaknesses identified"
        }

    async def _handle_growth_strategies(
        self,
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate tailored growth strategies"""
        org_id = context.get("org_id", "default_org") if context else "default_org"

        invoices_resp = await self.backend.get_invoices(org_id=org_id, limit=200)
        invoices = []
        if invoices_resp.success and invoices_resp.data:
            invoices = invoices_resp.data.get("invoices", [])

        total_rev = sum(i.get("totalAmount", 0) for i in invoices if i.get("status") == "PAID")
        avg_deal = total_rev / len([i for i in invoices if i.get("status") == "PAID"]) if invoices else 45000

        strategies = [
            {
                "strategy": "Enterprise Upsell",
                "description": "Target clients with deal sizes 3x your current average",
                "estimated_impact": "+35% revenue in 6 months",
                "effort": "Medium",
                "priority": 1,
                "actions": [
                    "Identify top 20% of clients by revenue",
                    "Develop premium service tier",
                    "Create dedicated enterprise sales process"
                ]
            },
            {
                "strategy": "Recurring Revenue Model",
                "description": "Convert project-based clients to retainer/subscription",
                "estimated_impact": "+25% revenue predictability + 15% total revenue",
                "effort": "Low",
                "priority": 2,
                "actions": [
                    "Package services into monthly retainer options",
                    "Offer 10% discount for annual commitments",
                    "Start with your 5 longest-standing clients"
                ]
            },
            {
                "strategy": "Accelerate Collections",
                "description": "Reduce DSO from 35 to 21 days through automation",
                "estimated_impact": "+20% working capital freed",
                "effort": "Low",
                "priority": 3,
                "actions": [
                    "Enable automated invoice reminders at 7, 14, 21 days",
                    "Offer 2% early-payment discount",
                    "Require 30% advance for new clients"
                ]
            },
            {
                "strategy": "Referral Program Launch",
                "description": "Turn existing clients into a sales channel",
                "estimated_impact": "+15 new clients in 90 days",
                "effort": "Low",
                "priority": 4,
                "actions": [
                    "Launch referral incentive (10% commission or service credit)",
                    "Create referral tracking system",
                    "Brief top 10 clients on the program"
                ]
            }
        ]

        return {
            "growth_strategies": strategies,
            "current_baseline": {
                "monthly_revenue": round(total_rev / 3),
                "average_deal_size": round(avg_deal),
            },
            "90_day_target": {
                "revenue_increase": "30-40%",
                "new_clients": "10-15",
                "focus": "Enterprise + Recurring Revenue"
            },
            "message": f"4 growth strategies identified with combined potential of +50% revenue in 90 days"
        }

    async def _handle_problem_diagnosis(
        self,
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Diagnose business problems with root cause analysis"""
        org_id = context.get("org_id", "default_org") if context else "default_org"
        problem_hint = params.get("problem", "general performance")

        invoices_resp = await self.backend.get_invoices(org_id=org_id, limit=200)
        balance_resp = await self.backend.get_balance(org_id=org_id)

        invoices = []
        if invoices_resp.success and invoices_resp.data:
            invoices = invoices_resp.data.get("invoices", [])

        paid = [i for i in invoices if i.get("status") == "PAID"]
        overdue = [i for i in invoices if i.get("status") == "OVERDUE"]
        total_rev = sum(i.get("totalAmount", 0) for i in paid)
        overdue_val = sum(i.get("totalAmount", 0) for i in overdue)
        collection_rate = (len(paid) / len(invoices) * 100) if invoices else 0

        balance = 0
        if balance_resp.success and balance_resp.data:
            balance = balance_resp.data.get("balance", 0)

        # Build diagnosis
        root_causes = []
        impact_analysis = []
        recommendations = []

        if overdue_val > total_rev * 0.2:
            root_causes.append(f"High overdue receivables (₹{overdue_val:,.0f}) — {overdue_val/total_rev*100:.0f}% of total revenue")
            impact_analysis.append("Cash flow constrained — cannot fund operations or growth reliably")
            recommendations.append({
                "action": "Immediate collections blitz",
                "details": f"Contact all {len(overdue)} overdue clients within 48 hours",
                "expected_impact": f"Recover ₹{overdue_val*0.6:,.0f} within 30 days",
                "timeline": "Week 1-2"
            })

        if collection_rate < 75:
            root_causes.append(f"Poor collection rate ({collection_rate:.0f}%) — payment process broken")
            impact_analysis.append("Working capital erosion affecting your ability to pay vendors and staff")
            recommendations.append({
                "action": "Overhaul payment terms",
                "details": "Require 50% upfront + milestone payments instead of net-30",
                "expected_impact": "+25% working capital within 60 days",
                "timeline": "Week 2-4"
            })

        if balance < 50000:
            root_causes.append(f"Low cash balance (₹{balance:,.0f}) — runway risk")
            impact_analysis.append("Less than 1 month operating buffer — high business risk")
            recommendations.append({
                "action": "Emergency cash acceleration",
                "details": "Offer 10% discount for immediate payment on all outstanding invoices",
                "expected_impact": f"Generate ₹{overdue_val*0.9*0.9:,.0f} cash within 2 weeks",
                "timeline": "Immediate"
            })

        if not root_causes:
            root_causes.append("No critical issues detected in current financial data")
            recommendations.append({
                "action": "Growth focus",
                "details": "Business fundamentals healthy — focus on scaling revenue",
                "expected_impact": "+20% growth in next quarter",
                "timeline": "Q2"
            })

        return {
            "diagnosis": {
                "problem_identified": problem_hint,
                "root_causes": root_causes,
                "impact_analysis": impact_analysis,
                "severity": "critical" if len(root_causes) > 2 else "moderate" if len(root_causes) > 0 else "healthy",
            },
            "action_plan": recommendations,
            "key_metrics": {
                "total_revenue": round(total_rev),
                "overdue_receivables": round(overdue_val),
                "collection_rate": f"{collection_rate:.1f}%",
                "cash_balance": round(balance),
            },
            "message": f"Diagnosis complete: {len(root_causes)} root cause(s) identified with {len(recommendations)} action recommendations"
        }

    async def _handle_competitive_analysis(
        self,
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Competitive positioning vs industry benchmarks"""
        org_id = context.get("org_id", "default_org") if context else "default_org"
        industry = context.get("industry", "IT & Software") if context else "IT & Software"

        invoices_resp = await self.backend.get_invoices(org_id=org_id, limit=200)
        invoices = []
        if invoices_resp.success and invoices_resp.data:
            invoices = invoices_resp.data.get("invoices", [])

        paid = [i for i in invoices if i.get("status") == "PAID"]
        total_rev = sum(i.get("totalAmount", 0) for i in paid)
        collection_rate = (len(paid) / len(invoices)) if invoices else 0

        # Your metrics
        your_metrics = {
            "gross_margin": 0.65,  # estimated
            "collection_efficiency": round(collection_rate, 2),
            "revenue_growth_rate": 0.15,  # estimated
        }

        competitive_position = benchmark_service.generate_competitive_position(
            your_metrics, industry
        )

        return {
            "competitive_position": competitive_position,
            "industry": industry,
            "your_metrics": your_metrics,
            "message": f"Competitive position: {competitive_position.get('position', 'N/A')} in {industry} sector"
        }

    async def process(
        self,
        intent: Intent,
        entities: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """Process strategy-related intents"""
        logger.info("strategy_agent_processing", intent=intent.value)

        if context and context.get("auth_token"):
            self.backend.set_auth_token(context["auth_token"])

        intent_to_tool = {
            Intent.BUSINESS_HEALTH_CHECK: "calculate_business_health_score",
            Intent.PROBLEM_DIAGNOSIS: "diagnose_business_problem",
            Intent.GROWTH_STRATEGY: "generate_growth_strategies",
            Intent.MARKET_EXPANSION: "generate_growth_strategies",
            Intent.SCALING_ADVICE: "generate_growth_strategies",
            Intent.SWOT_ANALYSIS: "perform_swot_analysis",
            Intent.SCENARIO_PLANNING: "perform_swot_analysis",
            Intent.GOAL_SETTING: "generate_growth_strategies",
            Intent.COMPETITIVE_POSITIONING: "analyze_competitive_position",
            Intent.PARTNERSHIP_OPPORTUNITIES: "generate_growth_strategies",
            Intent.RISK_ASSESSMENT: "diagnose_business_problem",
            Intent.PROFIT_OPTIMIZATION: "calculate_business_health_score",
            Intent.INVESTMENT_ADVICE: "generate_growth_strategies",
            Intent.DEBT_MANAGEMENT: "diagnose_business_problem",
            Intent.BUDGET_OPTIMIZATION: "calculate_business_health_score",
            Intent.CASH_FLOW_PLANNING: "calculate_business_health_score",
            Intent.PRODUCT_STRATEGY: "generate_growth_strategies",
        }

        tool_name = intent_to_tool.get(intent, "calculate_business_health_score")

        try:
            result = await tool_registry.execute_tool(
                tool_name=tool_name,
                parameters=entities,
                context=context
            )

            if result.success:
                return self._build_success_response(
                    message=result.result.get("message", "Strategic analysis complete"),
                    data=result.result,
                    tool_used=tool_name
                )
            else:
                return self._build_error_response(result.error or "Strategy tool failed")

        except Exception as e:
            logger.error("strategy_agent_error", error=str(e))
            return self._build_error_response(str(e))


# Singleton
strategy_agent = StrategyAgent()
