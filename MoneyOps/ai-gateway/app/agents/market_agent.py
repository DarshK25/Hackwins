"""
Market Agent — Real-time market market_agent with competitor intelligence,
growth strategy, and geopolitical impact analysis.
Fully connected to voice via orchestrator.
"""
import os
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.agents.base_agent import BaseAgent, AgentResponse, ToolDefinition
from app.schemas.intents import Intent, AgentType
from app.adapters.backend_adapter import get_backend_adapter
from app.tools.tool_registry import Tool, tool_registry
from app.tools.market_intelligence import (
    fetch_market_news,
    fetch_competitor_intelligence,
    fetch_geopolitical_impact,
    fetch_growth_opportunities,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

# ── Groq client reuse ──────────────────────────────────────────────
import httpx
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.3-70b-versatile"

CURRENT_WORLD_CONTEXT = """
CURRENT GLOBAL SITUATION (March 2026):
- US-China trade war escalating: 145% tariffs on Chinese goods, India positioned as key beneficiary
- India GDP growth 6.5%: strongest emerging market, FDI hitting record highs
- RBI held repo rate at 6.25%: cheap borrowing window open for Indian businesses
- India renewable energy boom: ₹2.8L crore government push, highest sector growth
- Global supply chain reshoring: companies moving manufacturing to India
- Rupee stable at ~83-84/USD: favorable for service exports
- SME credit access improved: MSME loans up 22% YoY
"""


async def _groq_chat(prompt: str, max_tokens: int = 400) -> str:
    """Lightweight Groq call for market synthesis"""
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
                }
            )
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.error({"event": "groq_market_error", "error": str(e)})
        return "I couldn't generate market analysis right now. Please try again."


# ── In-memory market_agent cache ───────────────────────────────────────
# Stores latest market snapshots per org_uuid
_market_cache: Dict[str, Dict[str, Any]] = {}


class MarketAgent(BaseAgent):
    """
    Market Agent — market_agent + Voice-connected intelligence engine.

    Capabilities:
    - Real-time market monitoring (APScheduler every 30 mins)
    - Competitor identification and movement tracking
    - Geopolitical/regulatory impact analysis
    - Growth opportunity detection
    - Full business context injection (your invoices + metrics)
    - Voice response via LiveKit data channel
    """

    def __init__(self):
        super().__init__()
        self.backend = get_backend_adapter()
        self._register_market_tools()
        self._scheduler = AsyncIOScheduler()
        logger.info({"event": "market_agent_initialized"})

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
            Intent.PROBLEM_DIAGNOSIS,
            Intent.SWOT_ANALYSIS,
            Intent.TREND_ANALYSIS,
            Intent.BENCHMARK_COMPARISON,
        ]

    def get_tools(self) -> List[ToolDefinition]:
        return [
            ToolDefinition(
                name="market_intelligence",
                description="Real-time market intelligence via Tavily + NewsAPI",
                parameters={},
                mvp_ready=True
            ),
            ToolDefinition(
                name="competitor_analysis",
                description="Identify and track competitors",
                parameters={},
                mvp_ready=True
            ),
            ToolDefinition(
                name="growth_opportunities",
                description="Find growth opportunities",
                parameters={},
                mvp_ready=True
            ),
            ToolDefinition(
                name="geopolitical_impact",
                description="Geopolitical and regulatory impact analysis",
                parameters={},
                mvp_ready=True
            ),
        ]

    def _register_market_tools(self):
        tool_registry.register_tools([
            Tool(
                name="market_intelligence",
                description="Real-time market intelligence",
                category="market",
                mvp_ready=True,
                handler=self._tool_market_intelligence
            ),
            Tool(
                name="competitor_analysis",
                description="Competitor identification and tracking",
                category="market",
                mvp_ready=True,
                handler=self._tool_competitor_analysis
            ),
            Tool(
                name="growth_opportunities",
                description="Growth opportunity detection",
                category="market",
                mvp_ready=True,
                handler=self._tool_growth_opportunities
            ),
            Tool(
                name="geopolitical_impact",
                description="Geopolitical impact analysis",
                category="market",
                mvp_ready=True,
                handler=self._tool_geopolitical_impact
            ),
        ])

    # ── market monitoring Scheduler ─────────────────────────────────────────

    def start_market_monitor(self, org_uuid: str, business_id: int, industry: str = "fintech services"):
        """Start background market monitoring for an org — call this on session start"""
        job_id = f"market_monitor_{org_uuid}"

        # Avoid duplicate jobs
        if self._scheduler.get_job(job_id):
            return

        if not self._scheduler.running:
            self._scheduler.start()

        self._scheduler.add_job(
            func=self._market_monitor_tick,
            trigger=IntervalTrigger(minutes=30),
            id=job_id,
            args=[org_uuid, business_id, industry],
            next_run_time=datetime.now() + timedelta(seconds=5),  # first run in 5s
            replace_existing=True,
            misfire_grace_time=60,
        )

        logger.info({
            "event": "market_monitor_started",
            "org_uuid": org_uuid,
            "interval_minutes": 30
        })

    def stop_market_monitor(self, org_uuid: str):
        """Stop market monitoring for an org"""
        job_id = f"market_monitor_{org_uuid}"
        if self._scheduler.get_job(job_id):
            self._scheduler.remove_job(job_id)
            logger.info({"event": "market_monitor_stopped", "org_uuid": org_uuid})

    async def _market_monitor_tick(self, org_uuid: str, business_id: int, industry: str):
        """Background job — fetch market data every 30 mins, cache it"""
        logger.info({"event": "market_monitor_tick", "org_uuid": org_uuid})
        try:
            # Fetch in parallel
            news_task = fetch_market_news(f"{industry} India market")
            competitor_task = fetch_competitor_intelligence(industry, "SME", "India")
            geo_task = fetch_market_news("India economy regulatory policy 2026")

            results = await asyncio.gather(
                news_task, competitor_task, geo_task,
                return_exceptions=True
            )
            
            news = results[0]
            competitors = results[1]
            geo = results[2]

            # Cache result
            _market_cache[org_uuid] = {
                "timestamp": datetime.now().isoformat(),
                "industry": industry,
                "news": news if not isinstance(news, Exception) else {},
                "competitors": competitors if not isinstance(competitors, Exception) else {},
                "geopolitical": geo if not isinstance(geo, Exception) else {},
            }

            logger.info({
                "event": "market_cache_updated",
                "org_uuid": org_uuid,
                "timestamp": _market_cache[org_uuid]["timestamp"]
            })

        except Exception as e:
            logger.error({"event": "market_monitor_tick_error", "error": str(e)})

    def get_cached_intelligence(self, org_uuid: str) -> Optional[Dict]:
        """Get latest cached market data for an org"""
        return _market_cache.get(org_uuid)

    # ── Business Context Fetcher ───────────────────────────────────

    async def _get_business_snapshot(self, context) -> Dict[str, Any]:
        """Fetch all business data in parallel for context injection"""
        try:
            org_uuid = context.org_uuid if hasattr(context, 'org_uuid') else context.get("org_uuid", "")
            user_id = context.user_id if hasattr(context, 'user_id') else context.get("user_id", "")
            business_id = context.business_id if hasattr(context, 'business_id') else context.get("business_id", 1)

            metrics_task = self.backend.get_finance_metrics(business_id, org_uuid, user_id)
            invoices_task = self.backend._request("GET", "/api/invoices", org_id=org_uuid, user_id=user_id)
            clients_task = self.backend.get_clients(org_uuid)

            results = await asyncio.gather(
                metrics_task, invoices_task, clients_task,
                return_exceptions=True
            )
            
            metrics_resp = results[0]
            invoices_resp = results[1]
            clients = results[2]

            m = {}
            if not isinstance(metrics_resp, Exception) and metrics_resp.success:
                m = metrics_resp.data or {}

            invoices = []
            if not isinstance(invoices_resp, Exception) and invoices_resp.success:
                invoices = invoices_resp.data or []

            clients_list = clients if not isinstance(clients, Exception) else []

            overdue = [i for i in invoices if i.get("status") == "OVERDUE"]
            paid = [i for i in invoices if i.get("status") == "PAID"]
            pending = [i for i in invoices if i.get("status") in ("DRAFT", "SENT")]

            return {
                "revenue": m.get("revenue", 0),
                "expenses": m.get("expenses", 0),
                "net_profit": m.get("netProfit", 0),
                "total_clients": len(clients_list or []),
                "total_invoices": len(invoices),
                "paid_count": len(paid),
                "pending_count": len(pending),
                "overdue_count": len(overdue),
                "overdue_amount": sum(float(i.get("totalAmount", 0)) for i in overdue),
                "profit_margin": round(
                    (m.get("netProfit", 0) / m.get("revenue", 1)) * 100, 1
                ) if m.get("revenue", 0) > 0 else 0,
            }
        except Exception as e:
            logger.error({"event": "business_snapshot_error", "error": str(e)})
            return {}

    async def handle_market_query(self, text: str, context, conversation_history: list = None) -> AgentResponse:
        """Main entry point for strategic market queries in voice path"""
        org_uuid = context.org_uuid if hasattr(context, 'org_uuid') else context.get("org_uuid", "")
        
        # Add conversation context to prompt
        history_str = ""
        if conversation_history:
            recent = conversation_history[-4:]  # last 2 turns
            history_str = "\nCONVERSATION SO FAR:\n" + "\n".join(
                f"{'User' if t['role'] == 'user' else 'Agent'}: {t['content']}"
                for t in recent
            )

        # 1. Start or check background monitor
        business_id = context.business_id if hasattr(context, 'business_id') else context.get("business_id", 1)
        self.start_market_monitor(org_uuid, business_id)

        # 2. Get business snapshot
        snapshot = await self._get_business_snapshot(context)

        # 3. Get cached market data
        market_data = self._market_cache.get(org_uuid, {})

        # 4. Synthesize strategy response
        prompt = self._build_strategy_prompt(text, snapshot, market_data, history_str)

        # Synthesize via Groq
        response_text = await _groq_chat(prompt, max_tokens=350)

        return AgentResponse(
            success=True,
            message=response_text,
            agent_type=self.get_agent_type(),
            ui_event={
                "type": "market_insight",
                "variant": "info",
                "title": "Market Intelligence",
                "message": "Live market analysis complete",
                "duration": 5000,
            }
        )

    def _detect_industry(self, snapshot: Dict, text: str) -> str:
        """Heuristic industry detection from text + business data"""
        text_lower = text.lower()
        if any(w in text_lower for w in ["construction", "build", "infrastructure"]):
            return "construction"
        if any(w in text_lower for w in ["tech", "software", "saas", "digital"]):
            return "technology"
        if any(w in text_lower for w in ["export", "import", "trade"]):
            return "export trade"
        if any(w in text_lower for w in ["consulting", "advisory", "strategy"]):
            return "consulting"
        if any(w in text_lower for w in ["retail", "shop", "store"]):
            return "retail"
        # Default from client names if available
        return "professional services"

    def _build_strategy_prompt(self, user_query, snapshot, market_data, history_str=""):
        """Construct the prompt for Groq strategy synthesis"""
        news_answer = market_data.get("news", {}).get("answer", "No recent news found.")
        news_list = market_data.get("news", {}).get("news", [])
        competitor_answer = market_data.get("competitors", {}).get("competitors_answer", "No specific competitor analysis available.")
        competitor_moves = market_data.get("competitors", {}).get("recent_moves", "No specific competitor moves detected.")
        geo_answer = market_data.get("geopolitical", {}).get("answer", "No specific geopolitical data available.")
        opportunities = market_data.get("opportunities", {}).get("opportunities", "No specific opportunities detected.")

        return f"""
ROLE: You are the MoneyOps Market Intelligence Agent. You provide world-class, McKinsey-level strategic advice based on LIVE market data and EXACT business metrics.

BUSINESS METRICS (Real-time):
- Revenue: ₹{snapshot.get('revenue', 0):,.0f}
- Expenses: ₹{snapshot.get('expenses', 0):,.0f}
- Net Profit: ₹{snapshot.get('net_profit', 0):,.0f}
- Margin: {snapshot.get('profit_margin', 0)}%
- Clients: {snapshot.get('total_clients', 0)}
- Total Invoices: {snapshot.get('total_invoices', 0)} ({snapshot.get('paid_count', 0)} paid, {snapshot.get('pending_count', 0)} pending, {snapshot.get('overdue_count', 0)} overdue)
- Overdue Amount: ₹{snapshot.get('overdue_amount', 0):,.0f}

{CURRENT_WORLD_CONTEXT}

LIVE MARKET INTELLIGENCE:
{news_answer}

RECENT HEADLINES:
{chr(10).join(f'• {h}' for h in news_list[:4])}

COMPETITOR LANDSCAPE:
{competitor_answer}

COMPETITOR RECENT MOVES:
{competitor_moves}

MACRO/GEOPOLITICAL CONTEXT:
{geo_answer}

STRATEGIC OPPORTUNITIES:
{opportunities}

{history_str}

USER QUESTION: {user_query}

INSTRUCTIONS:
- Give a direct, specific, actionable response using the EXACT business numbers above.
- Identify the top 1-2 concrete opportunities or risks.
- Suggest specific next steps this business should take THIS WEEK.
- Keep it under 4 sentences — this will be spoken via voice.
- Do NOT say "based on the data provided" — speak as if you know this business intimately.
- Be direct, confident, and professional.
"""

    # ── Intent-specific handlers ───────────────────────────────────

    async def handle_competitor_analysis(self, text: str, context) -> AgentResponse:
        snapshot = await self._get_business_snapshot(context)
        industry = self._detect_industry(snapshot, text)

        competitors = await fetch_competitor_intelligence(industry, "services", "India")

        prompt = f"""You are a competitive intelligence analyst.

Business: Revenue ₹{snapshot.get('revenue', 0):,}, {snapshot.get('total_clients', 0)} clients, {snapshot.get('profit_margin', 0)}% margin.

Competitor landscape: {competitors.get('competitors_answer', '')}
Recent competitor moves: {competitors.get('recent_moves', '')}

User asked: {text}

In 3-4 sentences, identify the top competitors, their recent moves, and one specific action this business should take to gain competitive advantage. Speak for voice output."""

        response = await _groq_chat(prompt, max_tokens=300)

        return AgentResponse(
            success=True,
            message=response,
            agent_type=self.get_agent_type(),
            ui_event={
                "type": "toast",
                "variant": "info",
                "title": "Competitor Analysis",
                "message": f"Analyzed {industry} competitive landscape",
                "duration": 4000,
            }
        )

    async def handle_growth_opportunities(self, text: str, context) -> AgentResponse:
        snapshot = await self._get_business_snapshot(context)
        industry = self._detect_industry(snapshot, text)

        opportunities = await fetch_growth_opportunities(
            industry,
            snapshot.get("revenue", 0),
            snapshot.get("total_clients", 0)
        )

        prompt = f"""You are a growth strategist.

Business snapshot: Revenue ₹{snapshot.get('revenue', 0):,}, {snapshot.get('total_clients', 0)} clients, {snapshot.get('overdue_count', 0)} overdue invoices worth ₹{snapshot.get('overdue_amount', 0):,.0f}.

Growth opportunities in market: {opportunities.get('opportunities', '')}
Market trends: {opportunities.get('trends', '')}

User asked: {text}

Identify the top 2 specific growth opportunities this business can act on in the next 30 days. Be concrete with numbers where possible. 3-4 sentences max, voice-friendly."""

        response = await _groq_chat(prompt, max_tokens=300)

        return AgentResponse(
            success=True,
            message=response,
            agent_type=self.get_agent_type(),
            ui_event={
                "type": "toast",
                "variant": "success",
                "title": "Growth Opportunities",
                "message": "New opportunities identified",
                "duration": 4000,
            }
        )

    async def handle_geopolitical_impact(self, text: str, context) -> AgentResponse:
        snapshot = await self._get_business_snapshot(context)
        industry = self._detect_industry(snapshot, text)

        geo = await fetch_geopolitical_impact(text, industry)

        prompt = f"""You are a geopolitical risk analyst for businesses.

Business: Revenue ₹{snapshot.get('revenue', 0):,}, industry: {industry}.

Impact analysis: {geo.get('impact_summary', '')}
Related news: {chr(10).join(geo.get('news', []))}

User asked: {text}

Explain the specific impact on this business and give one protective action to take. 3 sentences max, voice-friendly."""

        # Fixed typo: max_tokens=250 instead of max_tokens(250)
        response = await _groq_chat(prompt, max_tokens=250)

        return AgentResponse(
            success=True,
            message=response,
            agent_type=self.get_agent_type(),
            ui_event={
                "type": "toast",
                "variant": "warning",
                "title": "Market Alert",
                "message": "Geopolitical impact analyzed",
                "duration": 5000,
            }
        )

    # ── Tool handlers (for tool_registry) ─────────────────────────

    async def _tool_market_intelligence(self, params, context=None):
        query = params.get("query", "India business market 2026")
        result = await fetch_market_news(query)
        return {"message": result.get("answer", "No data available"), "data": result}

    async def _tool_competitor_analysis(self, params, context=None):
        industry = params.get("industry", "professional services")
        result = await fetch_competitor_intelligence(industry, "SME", "India")
        return {"message": result.get("competitors_answer", ""), "data": result}

    async def _tool_growth_opportunities(self, params, context=None):
        industry = params.get("industry", "professional services")
        result = await fetch_growth_opportunities(industry, 0, 0)
        return {"message": result.get("opportunities", ""), "data": result}

    async def _tool_geopolitical_impact(self, params, context=None):
        query = params.get("query", "India economy 2026")
        result = await fetch_geopolitical_impact(query, "services")
        return {"message": result.get("impact_summary", ""), "data": result}

    # ── BaseAgent.process (router fallback) ───────────────────────

    async def process(
        self,
        intent: Intent,
        entities: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """Called by agent_router for non-voice paths"""
        query = entities.get("query", str(intent.value).replace("_", " ").lower())

        # Build a minimal context object
        class _Ctx:
            org_uuid = (context or {}).get("org_uuid", "")
            user_id = (context or {}).get("user_id", "")
            business_id = (context or {}).get("business_id", 1)

        ctx = _Ctx()

        if intent in (Intent.COMPETITIVE_POSITIONING, Intent.BENCHMARK_COMPARISON):
            return await self.handle_competitor_analysis(query, ctx)
        elif intent in (Intent.GROWTH_STRATEGY, Intent.MARKET_EXPANSION, Intent.SCALING_ADVICE):
            return await self.handle_growth_opportunities(query, ctx)
        elif intent in (Intent.RISK_ASSESSMENT,):
            return await self.handle_geopolitical_impact(query, ctx)
        else:
            return await self.handle_market_query(query, ctx)


market_agent_instance = MarketAgent()
