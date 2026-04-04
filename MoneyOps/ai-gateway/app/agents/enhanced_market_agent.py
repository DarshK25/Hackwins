"""
Enhanced Market Agent - Real-time intelligence with multi-source search
Powered by function calling, provides McKinsey-level insights
"""

import os
import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime
import httpx

from app.agents.base_agent import BaseAgent, AgentResponse, ToolDefinition
from app.schemas.intents import Intent, AgentType
from app.tools.multi_source_search import multi_source_search
from app.adapters.backend_adapter import get_backend_adapter
from app.memory.persistent_memory import persistent_memory
from app.utils.logger import get_logger

logger = get_logger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.3-70b-versatile"

INDIA_BUSINESS_CONTEXT = """
India Business Environment - March 2026:
- India GDP growth: 6.5% (strongest among major economies)
- RBI Repo Rate: 6.25% (stable, favorable borrowing)
- PM E-DRIVE scheme: ₹10,900 crore for EV infrastructure (extended to 2028)
- Corporate ESG mandates: SEBI requiring top 1000 listed companies to report
- US-China trade tensions: India positioned as manufacturing alternative
- Digital India initiative driving SME digitization
- GST collections hitting record highs (₹1.68 lakh crore in Feb 2026)
- Manufacturing PLI schemes attracting FDI
"""


async def groq_synthesize(prompt: str, max_tokens: int = 500) -> str:
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                json={
                    "model": GROQ_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens,
                    "temperature": 0.4,
                },
            )
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.error({"event": "groq_synthesize_error", "error": str(e)})
        return "I couldn't generate analysis at this moment."


class EnhancedMarketAgent(BaseAgent):
    """
    Enhanced Market Intelligence Agent with:
    - Multi-source web search (Tavily, NewsAPI, DuckDuckGo, SerpAPI)
    - Real-time business context injection
    - Proactive opportunity detection
    - Structured market briefs
    """

    def __init__(self):
        self.backend = get_backend_adapter()
        super().__init__()
        self._register_tools()

    def get_agent_type(self) -> AgentType:
        return AgentType.MARKET_AGENT

    def get_supported_intents(self) -> List[Intent]:
        return [
            Intent.GROWTH_STRATEGY,
            Intent.MARKET_EXPANSION,
            Intent.PRODUCT_STRATEGY,
            Intent.SCALING_ADVICE,
            Intent.PARTNERSHIP_OPPORTUNITIES,
            Intent.COMPETITIVE_POSITIONING,
            Intent.RISK_ASSESSMENT,
            Intent.SALES_STRATEGY,
            Intent.CUSTOMER_ACQUISITION,
            Intent.PRICING_STRATEGY,
            Intent.SWOT_ANALYSIS,
            Intent.TREND_ANALYSIS,
            Intent.BUSINESS_HEALTH_CHECK,
            Intent.GENERAL_QUERY,
        ]

    def get_tools(self) -> List[ToolDefinition]:
        return [
            ToolDefinition(
                name="deep_market_research",
                description="Perform deep market research using multiple search sources",
                parameters={"query": "string"},
                mvp_ready=True,
            ),
            ToolDefinition(
                name="competitor_intelligence",
                description="Analyze competitors in your industry",
                parameters={"industry": "string", "region": "string"},
                mvp_ready=True,
            ),
            ToolDefinition(
                name="opportunity_detection",
                description="Detect new business opportunities based on market trends",
                parameters={},
                mvp_ready=True,
            ),
            ToolDefinition(
                name="risk_assessment",
                description="Assess business risks and threats",
                parameters={},
                mvp_ready=True,
            ),
        ]

    def _register_tools(self):
        from app.tools.tool_registry import Tool, tool_registry

        tool_registry.register_tools(
            [
                Tool(
                    name="deep_market_research",
                    description="Deep market research",
                    category="market",
                    handler=self._tool_deep_research,
                    mvp_ready=True,
                ),
                Tool(
                    name="competitor_intelligence",
                    description="Competitor analysis",
                    category="market",
                    handler=self._tool_competitor_intel,
                    mvp_ready=True,
                ),
                Tool(
                    name="opportunity_detection",
                    description="Find opportunities",
                    category="market",
                    handler=self._tool_opportunity,
                    mvp_ready=True,
                ),
                Tool(
                    name="risk_assessment",
                    description="Assess risks",
                    category="market",
                    handler=self._tool_risk,
                    mvp_ready=True,
                ),
            ]
        )

    async def _get_full_context(self, context) -> Dict[str, Any]:
        org_uuid = getattr(context, "org_uuid", None) or context.get("org_uuid", "")
        user_id = getattr(context, "user_id", None) or context.get("user_id", "")
        business_id = getattr(context, "business_id", None) or context.get(
            "business_id", "default"
        )

        tasks = [
            self.backend.get_finance_metrics(business_id, org_uuid, user_id),
            self.backend._request(
                "GET", "/api/invoices", org_id=org_uuid, user_id=user_id
            ),
            self.backend.get_clients(org_uuid, user_id=user_id),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        metrics = results[0] if not isinstance(results[0], Exception) else None
        invoices_resp = results[1] if not isinstance(results[1], Exception) else None
        clients = results[2] if not isinstance(results[2], Exception) else []

        m_data = metrics.data if metrics and metrics.success else {}
        invoices = invoices_resp.data if invoices_resp and invoices_resp.success else []
        clients = clients if isinstance(clients, list) else []

        overdue = [i for i in invoices if i.get("status") == "OVERDUE"]
        pending = [i for i in invoices if i.get("status") in ("DRAFT", "SENT")]

        client_names = [c.get("name", "Unknown") for c in clients[:5]]

        stored_knowledge = persistent_memory.get_knowledge(org_uuid)

        return {
            "business_metrics": {
                "revenue": m_data.get("revenue", 0),
                "expenses": m_data.get("expenses", 0),
                "net_profit": m_data.get("netProfit", 0),
                "profit_margin": round(
                    (m_data.get("netProfit", 0) / max(m_data.get("revenue", 1), 1))
                    * 100,
                    1,
                ),
                "overdue_count": len(overdue),
                "overdue_amount": sum(float(i.get("totalAmount", 0)) for i in overdue),
                "pending_count": len(pending),
                "pending_amount": sum(float(i.get("totalAmount", 0)) for i in pending),
            },
            "clients": {"total": len(clients), "names": client_names},
            "invoices": {
                "total": len(invoices),
                "overdue": overdue[:3],
                "pending": pending[:3],
            },
            "stored_knowledge": stored_knowledge,
            "org_id": org_uuid,
        }

    async def handle_market_query(
        self, text: str, context, conversation_history: Optional[List[Dict]] = None
    ) -> AgentResponse:
        org_uuid = getattr(context, "org_uuid", None) or context.get("org_uuid", "")

        full_context = await self._get_full_context(context)

        search_result = await multi_source_search.search(text, max_results_per_source=8)

        history_str = ""
        if conversation_history:
            recent = conversation_history[-4:]
            history_str = "\nRecent conversation:\n" + "\n".join(
                f"{'User' if t.get('role') == 'user' else 'Assistant'}: {t.get('content', '')[:100]}"
                for t in recent
            )

        business = full_context["business_metrics"]
        invoices = full_context["invoices"]
        clients = full_context["clients"]

        prompt = f"""Generate a McKinsey-level market intelligence brief.

CRITICAL: Use actual business data in your response. Reference specific numbers.

BUSINESS SNAPSHOT:
- Revenue: ₹{business.get("revenue", 0):,.0f}
- Expenses: ₹{business.get("expenses", 0):,.0f}
- Net Profit: ₹{business.get("net_profit", 0):,.0f}
- Margin: {business.get("profit_margin", 0)}%
- Total Clients: {clients.get("total", 0)}
- Pending Invoices: {business.get("pending_count", 0)} (₹{business.get("pending_amount", 0):,.0f})
- Overdue Invoices: {business.get("overdue_count", 0)} (₹{business.get("overdue_amount", 0):,.0f})

OVERDUE INVOICES (action needed):
{chr(10).join([f"- {i.get('clientName', 'Unknown')}: ₹{i.get('totalAmount', 0):,.0f} (status: {i.get('status', '')})" for i in invoices.get("overdue", [])]) or "None"}

CLIENTS:
{", ".join(clients.get("names", ["No clients yet"]))}

{INDIA_BUSINESS_CONTEXT}

MARKET INTELLIGENCE (from web):
Answer: {search_result.get("synthesized_answer", "No specific market data available")}

TOP SOURCES:
{chr(10).join([f"- {s}" for s in search_result.get("sources", [])[:3]])}

{history_str}

USER QUESTION: {text}

FORMAT YOUR RESPONSE AS:

**MARKET BRIEF** — {datetime.now().strftime("%B %d, %Y")}

**IMMEDIATE** (this week)
→ [Specific action item with deadline]

**OPPORTUNITY**
→ [1-2 concrete opportunities with numbers]

**RISK**
→ [Key risk with mitigation]

**MARKET INSIGHT**
→ [2-3 sentences on what this means for their business]

Keep it 4-6 sentences total. This will be spoken via voice. Be direct and actionable."""

        response_text = await groq_synthesize(prompt, max_tokens=600)

        persistent_memory.store_knowledge(
            org_id=org_uuid,
            category="market_brief",
            key=f"brief_{datetime.now().strftime('%Y%m%d')}",
            value={
                "query": text,
                "response": response_text,
                "sources": search_result.get("sources", [])[:3],
            },
            source="market_agent",
            confidence=0.9,
        )

        return AgentResponse(
            success=True,
            message=response_text,
            agent_type=self.get_agent_type(),
            ui_event={
                "type": "market_insight",
                "variant": "info",
                "title": "Market Intelligence",
                "sources": search_result.get("sources", [])[:3],
                "duration": 6000,
            },
        )

    async def handle_swot_analysis(self, context) -> AgentResponse:
        full_context = await self._get_full_context(context)
        business = full_context["business_metrics"]

        search_result = await multi_source_search.search(
            f"{business.get('industry', 'business')} industry trends India 2026",
            max_results_per_source=5,
        )

        prompt = f"""Generate a concise SWOT analysis for this business.

BUSINESS:
- Revenue: ₹{business.get("revenue", 0):,.0f}
- Margin: {business.get("profit_margin", 0)}%
- Clients: {business.get("total_clients", full_context["clients"].get("total", 0))}
- Overdue: {business.get("overdue_count", 0)} invoices worth ₹{business.get("overdue_amount", 0):,.0f}

MARKET CONTEXT:
{search_result.get("synthesized_answer", "")}

Format as:
**SWOT ANALYSIS**

Strengths:
• [1-2 key strengths]

Weaknesses:
• [1-2 weaknesses]

Opportunities:
• [2-3 opportunities from market]

Threats:
• [1-2 threats]

Keep it 8-10 sentences total, voice-friendly."""

        response_text = await groq_synthesize(prompt, max_tokens=400)

        return AgentResponse(
            success=True, message=response_text, agent_type=self.get_agent_type()
        )

    async def _tool_deep_research(self, params, context=None) -> Dict[str, Any]:
        query = params.get("query", "India business market 2026")
        result = await multi_source_search.search(query, max_results_per_source=10)
        return {
            "synthesized": result.get("synthesized_answer", ""),
            "results_count": len(result.get("results", [])),
            "top_results": result.get("results", [])[:5],
            "sources": result.get("sources", [])[:5],
        }

    async def _tool_competitor_intel(self, params, context=None) -> Dict[str, Any]:
        industry = params.get("industry", "professional services")
        region = params.get("region", "India")
        result = await multi_source_search.search(
            f"top competitors {industry} {region} 2026 market share",
            max_results_per_source=8,
        )
        return {
            "analysis": result.get("synthesized_answer", ""),
            "competitors": [r.get("title") for r in result.get("results", [])[:5]],
            "sources": result.get("sources", [])[:5],
        }

    async def _tool_opportunity(self, params, context=None) -> Dict[str, Any]:
        result = await multi_source_search.search(
            "emerging business opportunities India SME 2026 growth",
            max_results_per_source=8,
        )
        return {
            "opportunities": result.get("synthesized_answer", ""),
            "trends": [r.get("snippet") for r in result.get("results", [])[:3]],
        }

    async def _tool_risk(self, params, context=None) -> Dict[str, Any]:
        result = await multi_source_search.search(
            "business risks challenges India SME 2026", max_results_per_source=6
        )
        return {
            "risks": result.get("synthesized_answer", ""),
            "factors": [r.get("snippet") for r in result.get("results", [])[:3]],
        }

    async def process(
        self,
        intent: Intent,
        entities: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        query = entities.get("query", str(intent.value).replace("_", " ").lower())

        class _Ctx:
            org_uuid = (context or {}).get("org_uuid", "")
            user_id = (context or {}).get("user_id", "")
            business_id = (context or {}).get("business_id", "default")

        ctx = _Ctx()

        if intent == Intent.SWOT_ANALYSIS:
            return await self.handle_swot_analysis(ctx)

        return await self.handle_market_query(query, ctx)


enhanced_market_agent = EnhancedMarketAgent()
