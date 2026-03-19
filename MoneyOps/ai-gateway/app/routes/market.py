from fastapi import APIRouter, Query
from app.agents.market_agent import market_agent_instance
from app.adapters.backend_adapter import get_backend_adapter

router = APIRouter(prefix="/api/v1/market", tags=["market"])
backend = get_backend_adapter()

@router.get("/intelligence")
async def get_market_intelligence(
    org_uuid: str = Query(...),
    business_id: int = Query(default=1),
    user_id: str = Query(default="")
):
    # Build a minimal context
    class Ctx:
        pass
    ctx = Ctx()
    ctx.org_uuid = org_uuid
    ctx.user_id = user_id
    ctx.business_id = business_id

    # Get business snapshot
    snapshot = await market_agent_instance._get_business_snapshot(ctx)

    # Get cached or fetch fresh
    cached = market_agent_instance.get_cached_intelligence(org_uuid)
    if not cached:
        from app.tools.market_intelligence import (
            fetch_market_news,
            fetch_competitor_intelligence,
            fetch_growth_opportunities
        )
        import asyncio
        news, competitors, opportunities = await asyncio.gather(
            fetch_market_news("professional services India business 2026"),
            fetch_competitor_intelligence("professional services", "SME", "India"),
            fetch_growth_opportunities("professional services", snapshot.get("revenue", 0), snapshot.get("total_clients", 0))
        )
        market_data = {"news": news, "competitors": competitors, "opportunities": opportunities}
    else:
        market_data = cached

    return {
        "success": True,
        "snapshot": snapshot,
        "market": market_data,
        "cached": cached is not None,
        "timestamp": cached.get("timestamp") if cached else None
    }
