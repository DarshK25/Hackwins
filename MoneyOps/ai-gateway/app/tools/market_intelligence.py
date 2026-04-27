"""
Market Intelligence Tools - Tavily + NewsAPI + free-tier deep research helpers.
Gracefully degrades when API keys are missing.
"""
import os
import asyncio
import re
from html import unescape
from typing import Dict, Any

import httpx

from app.utils.logger import get_logger
from app.tools.multi_source_search import multi_source_search

logger = get_logger(__name__)

_tavily_key = os.getenv("TAVILY_API_KEY")
_newsapi_key = os.getenv("NEWS_API_KEY")

tavily = None
newsapi = None

if _tavily_key:
    try:
        from tavily import TavilyClient
        tavily = TavilyClient(api_key=_tavily_key)
        logger.info({"event": "tavily_initialized"})
    except Exception as e:
        logger.warning({"event": "tavily_init_failed", "error": str(e)})

if _newsapi_key:
    try:
        from newsapi import NewsApiClient
        newsapi = NewsApiClient(api_key=_newsapi_key)
        logger.info({"event": "newsapi_initialized"})
    except Exception as e:
        logger.warning({"event": "newsapi_init_failed", "error": str(e)})

if not tavily:
    logger.warning({"event": "tavily_not_available", "reason": "TAVILY_API_KEY not set"})
if not newsapi:
    logger.warning({"event": "newsapi_not_available", "reason": "NEWS_API_KEY not set"})

SCRAPE_BLOCKED_DOMAINS = (
    "linkedin.com",
    "facebook.com",
    "instagram.com",
    "twitter.com",
    "x.com",
    "pinterest.com",
)


def _normalize_tavily_results(results):
    normalized = []
    for item in results or []:
        normalized.append(
            {
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "content": item.get("content", ""),
                "score": item.get("score"),
            }
        )
    return normalized


def _normalize_news_articles(articles):
    normalized = []
    for article in articles or []:
        normalized.append(
            {
                "title": article.get("title", ""),
                "url": article.get("url", ""),
                "source": (article.get("source") or {}).get("name", ""),
                "description": article.get("description", ""),
                "published_at": article.get("publishedAt", ""),
            }
        )
    return normalized


def _strip_html(value: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?>.*?</\\1>", " ", value or "")
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _extract_html_title(value: str) -> str:
    match = re.search(r"(?is)<title[^>]*>(.*?)</title>", value or "")
    return _strip_html(match.group(1)) if match else ""


def _extract_meta_description(value: str) -> str:
    patterns = [
        r'(?is)<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']',
        r'(?is)<meta[^>]+property=["\']og:description["\'][^>]+content=["\'](.*?)["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, value or "")
        if match:
            return _strip_html(match.group(1))
    return ""


async def fetch_source_page_preview(url: str) -> Dict[str, Any]:
    if not url:
        return {"url": "", "status": "skipped", "summary": "", "title": "", "notes": "Missing URL"}

    lowered = url.lower()
    if any(blocked in lowered for blocked in SCRAPE_BLOCKED_DOMAINS):
        return {"url": url, "status": "blocked", "summary": "", "title": "", "notes": "Blocked low-signal or gated source"}

    try:
        async with httpx.AsyncClient(
            timeout=10,
            follow_redirects=True,
            headers={
                "User-Agent": "MoneyOpsResearchBot/1.0 (+https://moneyops.app)",
                "Accept-Language": "en-US,en;q=0.9",
            },
        ) as client:
            response = await client.get(url)
            response.raise_for_status()

        html = response.text or ""
        title = _extract_html_title(html)
        description = _extract_meta_description(html)
        body_text = _strip_html(html)
        summary = description or body_text[:900]
        return {
            "url": url,
            "status": "ok",
            "title": title,
            "summary": summary,
            "notes": "",
        }
    except Exception as exc:
        logger.warning({"event": "source_preview_failed", "url": url, "error": str(exc)})
        return {
            "url": url,
            "status": "error",
            "title": "",
            "summary": "",
            "notes": str(exc),
        }


def _clean_research_text(value: str, limit: int = 280) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= limit:
        return text
    clipped = text[:limit].rsplit(" ", 1)[0].strip()
    return f"{clipped}..."


def _classify_research_result(text: str) -> str:
    lowered = text.lower()
    if any(token in lowered for token in ("fame", "subsidy", "policy", "government", "tender", "regulation", "scheme")):
        return "policy_and_incentives"
    if any(token in lowered for token in ("competitor", "pricing", "operator", "provider", "funding", "expansion")):
        return "competitor_moves"
    return "buyer_demand"


async def run_deep_market_research(query: str, max_sources: int = 6) -> Dict[str, Any]:
    """
    Free-tier deep research path:
    - multi-source search via Tavily / NewsAPI / DuckDuckGo
    - direct page previews via plain HTTP fetch
    - source-backed sections for demand, competition, and policy
    """
    search_result = await multi_source_search.search(query, max_results_per_source=4, include_answer=True)
    ranked_results = [
        item
        for item in search_result.get("results", [])
        if item.get("url") and item.get("title")
    ][:max_sources]

    previews = await asyncio.gather(
        *(fetch_source_page_preview(item.get("url", "")) for item in ranked_results[:4]),
        return_exceptions=False,
    )
    preview_by_url = {item.get("url"): item for item in previews}

    sections = {
        "buyer_demand": [],
        "competitor_moves": [],
        "policy_and_incentives": [],
    }
    sources = []

    for result in ranked_results:
        url = result.get("url", "")
        preview = preview_by_url.get(url, {})
        summary = preview.get("summary") or result.get("snippet") or ""
        title = preview.get("title") or result.get("title") or "Source"
        domain = url.split("/")[2].replace("www.", "") if "://" in url else "source"
        item = {
            "title": title,
            "url": url,
            "source": domain,
            "summary": _clean_research_text(summary),
            "provider": result.get("provider", "search"),
            "preview_status": preview.get("status", "search_only"),
            "notes": preview.get("notes", ""),
        }
        section_key = _classify_research_result(f"{title} {summary}")
        sections[section_key].append(item)
        sources.append(item)

    research_sections = [
        {
            "id": "buyer_demand",
            "title": "Demand and buyer signals",
            "items": sections["buyer_demand"][:3],
        },
        {
            "id": "competitor_moves",
            "title": "Competitor and market moves",
            "items": sections["competitor_moves"][:3],
        },
        {
            "id": "policy_and_incentives",
            "title": "Policy, tenders, and incentives",
            "items": sections["policy_and_incentives"][:3],
        },
    ]

    return {
        "query": query,
        "summary": search_result.get("synthesized_answer", ""),
        "sections": research_sections,
        "sources": sources,
        "provider_mix": list({item.get("provider", "search") for item in sources}),
        "source_count": len(sources),
        "notes": "Built from Tavily, NewsAPI, DuckDuckGo, and direct page previews where accessible.",
    }


async def fetch_market_news(query: str, max_results: int = 5) -> Dict[str, Any]:
    """Fetch real-time market news via Tavily + NewsAPI"""
    result = {
        "answer": "",
        "sources": [],
        "news": [],
        "raw_results": [],
        "news_items": [],
    }

    try:
        loop = asyncio.get_event_loop()

        if tavily:
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
            raw_results = _normalize_tavily_results(tavily_result.get("results", []))
            result["answer"] = tavily_result.get("answer", "")
            result["sources"] = [r.get("url", "") for r in raw_results if r.get("url")]
            result["raw_results"] = raw_results

        if newsapi:
            news_result = await loop.run_in_executor(
                None,
                lambda: newsapi.get_everything(
                    q=query,
                    language="en",
                    sort_by="publishedAt",
                    page_size=5,
                )
            )
            news_items = _normalize_news_articles((news_result.get("articles") or [])[:5])
            result["news_items"] = news_items
            result["news"] = [
                f"{item['title']} ({item['source']})" if item.get("source") else item["title"]
                for item in news_items
                if item.get("title")
            ]

        return result
    except Exception as e:
        logger.error({"event": "market_news_fetch_error", "error": str(e)})
        return result


async def fetch_competitor_intelligence(
    industry: str,
    business_type: str,
    region: str = "India"
) -> Dict[str, Any]:
    """Identify and analyze competitors"""
    empty = {"competitors_answer": "", "recent_moves": "", "sources": [], "results": [], "moves_results": []}
    if not tavily:
        return empty

    try:
        loop = asyncio.get_event_loop()

        competitor_result = await loop.run_in_executor(
            None,
            lambda: tavily.search(
                query=f"top {industry} {business_type} companies competitors {region} 2026",
                search_depth="advanced",
                max_results=7,
                include_answer=True,
            )
        )

        moves_result = await loop.run_in_executor(
            None,
            lambda: tavily.search(
                query=f"{industry} {business_type} competitor pricing strategy funding news {region} 2026",
                search_depth="basic",
                max_results=5,
                include_answer=True,
            )
        )

        competitor_results = _normalize_tavily_results(competitor_result.get("results", []))
        move_results = _normalize_tavily_results(moves_result.get("results", []))

        return {
            "competitors_answer": competitor_result.get("answer", ""),
            "recent_moves": moves_result.get("answer", ""),
            "sources": [r.get("url", "") for r in competitor_results if r.get("url")],
            "results": competitor_results,
            "moves_results": move_results,
        }
    except Exception as e:
        logger.error({"event": "competitor_intel_error", "error": str(e)})
        return empty


async def fetch_geopolitical_impact(
    event_query: str,
    business_type: str
) -> Dict[str, Any]:
    """Check geopolitical/regulatory events affecting the business"""
    empty = {"impact_summary": "", "news": [], "sources": []}

    try:
        loop = asyncio.get_event_loop()

        if tavily:
            result = await loop.run_in_executor(
                None,
                lambda: tavily.search(
                    query=f"{event_query} impact {business_type} India SME business 2026",
                    search_depth="advanced",
                    max_results=5,
                    include_answer=True,
                )
            )
            empty["impact_summary"] = result.get("answer", "")
            empty["sources"] = [r.get("url", "") for r in _normalize_tavily_results(result.get("results", [])) if r.get("url")]

        if newsapi:
            news = await loop.run_in_executor(
                None,
                lambda: newsapi.get_everything(
                    q=f"{event_query} India business",
                    language="en",
                    sort_by="publishedAt",
                    page_size=3,
                )
            )
            empty["news"] = [a["title"] for a in (news.get("articles") or [])[:3]]

        return empty
    except Exception as e:
        logger.error({"event": "geopolitical_fetch_error", "error": str(e)})
        return empty


async def fetch_growth_opportunities(
    industry: str,
    current_revenue: float,
    client_count: int,
    region: str = "India"
) -> Dict[str, Any]:
    """Find specific growth opportunities for this business"""
    empty = {"opportunities": "", "trends": "", "sources": [], "results": [], "trend_results": []}
    if not tavily:
        return empty

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

        opportunity_results = _normalize_tavily_results(opp_result.get("results", []))
        trend_results = _normalize_tavily_results(trend_result.get("results", []))

        return {
            "opportunities": opp_result.get("answer", ""),
            "trends": trend_result.get("answer", ""),
            "sources": [r.get("url", "") for r in opportunity_results if r.get("url")],
            "results": opportunity_results,
            "trend_results": trend_results,
        }
    except Exception as e:
        logger.error({"event": "growth_opp_fetch_error", "error": str(e)})
        return empty
