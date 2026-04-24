"""
Shared market intelligence service used by both the Market Research page and
voice/agent flows.
"""
import asyncio
import re
from datetime import datetime
from typing import Any, Dict, Optional

from app.adapters.backend_adapter import get_backend_adapter
from app.tools.market_intelligence import (
    fetch_competitor_intelligence,
    fetch_growth_opportunities,
    fetch_market_news,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)
backend = get_backend_adapter()

_market_cache: Dict[str, Dict[str, Any]] = {}


async def get_business_snapshot(org_uuid: str, business_id: int = 1, user_id: str = "") -> Dict[str, Any]:
    try:
        metrics_task = backend.get_finance_metrics(str(business_id), org_uuid, user_id or None)
        invoices_task = backend._request("GET", "/api/invoices", org_id=org_uuid, user_id=user_id or None)
        clients_task = backend.get_clients(org_uuid, user_id=user_id or None)

        metrics_resp, invoices_resp, clients = await asyncio.gather(
            metrics_task,
            invoices_task,
            clients_task,
            return_exceptions=True,
        )

        metrics = {}
        if not isinstance(metrics_resp, Exception) and getattr(metrics_resp, "success", False):
            metrics = metrics_resp.data or {}

        invoices = []
        if not isinstance(invoices_resp, Exception) and getattr(invoices_resp, "success", False):
            invoices = invoices_resp.data or []

        client_list = clients if not isinstance(clients, Exception) else []

        overdue = [item for item in invoices if item.get("status") == "OVERDUE"]
        paid = [item for item in invoices if item.get("status") == "PAID"]
        pending = [item for item in invoices if item.get("status") in ("DRAFT", "SENT")]

        return {
            "revenue": metrics.get("revenue", 0),
            "expenses": metrics.get("expenses", 0),
            "net_profit": metrics.get("netProfit", 0),
            "total_clients": len(client_list or []),
            "total_invoices": len(invoices),
            "paid_count": len(paid),
            "pending_count": len(pending),
            "overdue_count": len(overdue),
            "overdue_amount": sum(float(item.get("totalAmount", 0) or 0) for item in overdue),
            "profit_margin": round(
                (metrics.get("netProfit", 0) / metrics.get("revenue", 1)) * 100, 1
            ) if metrics.get("revenue", 0) > 0 else 0,
        }
    except Exception as exc:
        logger.error({"event": "business_snapshot_error", "error": str(exc)})
        return {}


def _normalize_cache_fragment(text: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", (text or "").lower()).strip("_")
    return normalized[:80] or "default"


def _infer_market_topic(user_query: str = "", topic: Optional[str] = None) -> str:
    if topic:
        return topic

    text = (user_query or "").lower()
    if any(keyword in text for keyword in ("news", "headline", "latest", "live", "current update", "war", "crude oil", "oil price")):
        return "news"
    if any(keyword in text for keyword in ("growth", "opportunit", "expand", "scale")):
        return "growth"
    return "overview"


def _build_cache_key(org_uuid: str, topic: str, user_query: str = "") -> str:
    if topic == "overview":
        return f"{org_uuid}:overview"
    return f"{org_uuid}:{topic}:{_normalize_cache_fragment(user_query)}"


def _build_market_news_query(user_query: str, topic: str) -> str:
    cleaned = (user_query or "").strip()
    if cleaned:
        return cleaned
    if topic == "news":
        return "India market news crude oil war inflation business"
    if topic == "growth":
        return "professional services India growth opportunities and market trends"
    return "professional services India business 2026"


async def _fetch_market_data(snapshot: Dict[str, Any], user_query: str, topic: str) -> Dict[str, Any]:
    revenue = snapshot.get("revenue", 0)
    total_clients = snapshot.get("total_clients", 0)
    news_query = _build_market_news_query(user_query, topic)

    if topic == "news":
        news = await fetch_market_news(news_query)
        return {
            "timestamp": datetime.now().isoformat(),
            "industry": "professional services",
            "news": news,
            "competitors": {},
            "opportunities": {},
            "geopolitical": {},
        }

    if topic == "growth":
        news, competitors, opportunities = await asyncio.gather(
            fetch_market_news(news_query),
            fetch_competitor_intelligence("professional services", "SME", "India"),
            fetch_growth_opportunities("professional services", revenue, total_clients),
        )
        return {
            "timestamp": datetime.now().isoformat(),
            "industry": "professional services",
            "news": news,
            "competitors": competitors,
            "opportunities": opportunities,
            "geopolitical": {},
        }

    news, competitors, opportunities = await asyncio.gather(
        fetch_market_news("professional services India business 2026"),
        fetch_competitor_intelligence("professional services", "SME", "India"),
        fetch_growth_opportunities("professional services", revenue, total_clients),
    )
    return {
        "timestamp": datetime.now().isoformat(),
        "industry": "professional services",
        "news": news,
        "competitors": competitors,
        "opportunities": opportunities,
        "geopolitical": {},
    }


def get_cached_market_intelligence(cache_key: str) -> Optional[Dict[str, Any]]:
    return _market_cache.get(cache_key) or _market_cache.get(f"{cache_key}:overview")


def set_cached_market_intelligence(cache_key: str, market_data: Dict[str, Any]) -> None:
    _market_cache[cache_key] = market_data
    if ":" not in cache_key:
        _market_cache[f"{cache_key}:overview"] = market_data


async def get_market_intelligence_payload(
    org_uuid: str,
    business_id: int = 1,
    user_id: str = "",
    force_refresh: bool = False,
    user_query: str = "",
    topic: Optional[str] = None,
) -> Dict[str, Any]:
    snapshot = await get_business_snapshot(org_uuid=org_uuid, business_id=business_id, user_id=user_id)

    effective_topic = _infer_market_topic(user_query=user_query, topic=topic)
    cache_key = _build_cache_key(org_uuid, effective_topic, user_query if effective_topic != "overview" else "")

    cached = None if force_refresh else get_cached_market_intelligence(cache_key)
    if cached:
        market_data = cached
    else:
        market_data = await _fetch_market_data(snapshot, user_query, effective_topic)
        set_cached_market_intelligence(cache_key, market_data)

    return {
        "success": True,
        "snapshot": snapshot,
        "market": market_data,
        "cached": cached is not None,
        "timestamp": market_data.get("timestamp"),
        "topic": effective_topic,
    }
