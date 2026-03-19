"""
Market Intelligence Tools — Tavily + NewsAPI + Alpha Vantage
"""
import os
import asyncio
from typing import Dict, Any, Optional
from tavily import TavilyClient
from newsapi import NewsApiClient
from app.utils.logger import get_logger

logger = get_logger(__name__)

tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
newsapi = NewsApiClient(api_key=os.getenv("NEWS_API_KEY"))


async def fetch_market_news(query: str, max_results: int = 5) -> Dict[str, Any]:
    """Fetch real-time market news via Tavily + NewsAPI"""
    try:
        loop = asyncio.get_event_loop()

        # Tavily deep search
        tavily_result = await loop.run_in_executor(
            None,
            lambda: tavily.search(
                query=f"{query} India business 2026",
                search_depth="advanced",
                max_results=max_results,
                include_answer=True,
                include_raw_content=False,
            )
        )

        # NewsAPI recent headlines
        news_result = await loop.run_in_executor(
            None,
            lambda: newsapi.get_everything(
                q=query,
                language="en",
                sort_by="publishedAt",
                page_size=5
            )
        )

        headlines = [
            f"{a['title']} ({a['source']['name']})"
            for a in (news_result.get("articles") or [])[:5]
        ]

        return {
            "answer": tavily_result.get("answer", ""),
            "sources": [r.get("url", "") for r in tavily_result.get("results", [])],
            "news": headlines,
            "raw_results": tavily_result.get("results", []),
        }
    except Exception as e:
        logger.error({"event": "market_news_fetch_error", "error": str(e)})
        return {"answer": "", "sources": [], "news": [], "raw_results": []}


async def fetch_competitor_intelligence(
    industry: str,
    business_type: str,
    region: str = "India"
) -> Dict[str, Any]:
    """Identify and analyze competitors"""
    try:
        loop = asyncio.get_event_loop()

        # Search for competitors
        competitor_result = await loop.run_in_executor(
            None,
            lambda: tavily.search(
                query=f"top {industry} {business_type} companies competitors {region} 2026",
                search_depth="advanced",
                max_results=7,
                include_answer=True,
            )
        )

        # Search for competitor recent moves
        moves_result = await loop.run_in_executor(
            None,
            lambda: tavily.search(
                query=f"{industry} {business_type} competitor pricing strategy funding news {region} 2026",
                search_depth="basic",
                max_results=5,
                include_answer=True,
            )
        )

        return {
            "competitors_answer": competitor_result.get("answer", ""),
            "recent_moves": moves_result.get("answer", ""),
            "sources": [r.get("url", "") for r in competitor_result.get("results", [])],
        }
    except Exception as e:
        logger.error({"event": "competitor_intel_error", "error": str(e)})
        return {"competitors_answer": "", "recent_moves": "", "sources": []}


async def fetch_geopolitical_impact(
    event_query: str,
    business_type: str
) -> Dict[str, Any]:
    """Check geopolitical/regulatory events affecting the business"""
    try:
        loop = asyncio.get_event_loop()

        result = await loop.run_in_executor(
            None,
            lambda: tavily.search(
                query=f"{event_query} impact {business_type} India SME business 2026",
                search_depth="advanced",
                max_results=5,
                include_answer=True,
            )
        )

        news = await loop.run_in_executor(
            None,
            lambda: newsapi.get_everything(
                q=f"{event_query} India business",
                language="en",
                sort_by="publishedAt",
                page_size=3
            )
        )

        headlines = [a["title"] for a in (news.get("articles") or [])[:3]]

        return {
            "impact_summary": result.get("answer", ""),
            "news": headlines,
            "sources": [r.get("url", "") for r in result.get("results", [])],
        }
    except Exception as e:
        logger.error({"event": "geopolitical_fetch_error", "error": str(e)})
        return {"impact_summary": "", "news": [], "sources": []}


async def fetch_growth_opportunities(
    industry: str,
    current_revenue: float,
    client_count: int,
    region: str = "India"
) -> Dict[str, Any]:
    """Find specific growth opportunities for this business"""
    try:
        loop = asyncio.get_event_loop()

        opp_result = await loop.run_in_executor(
            None,
            lambda: tavily.search(
                query=f"{industry} growth opportunities emerging markets {region} SME 2026",
                search_depth="advanced",
                max_results=5,
                include_answer=True,
            )
        )

        trend_result = await loop.run_in_executor(
            None,
            lambda: tavily.search(
                query=f"{industry} market trends demand forecast {region} 2026",
                search_depth="basic",
                max_results=4,
                include_answer=True,
            )
        )

        return {
            "opportunities": opp_result.get("answer", ""),
            "trends": trend_result.get("answer", ""),
            "sources": [r.get("url", "") for r in opp_result.get("results", [])],
        }
    except Exception as e:
        logger.error({"event": "growth_opp_fetch_error", "error": str(e)})
        return {"opportunities": "", "trends": "", "sources": []}
