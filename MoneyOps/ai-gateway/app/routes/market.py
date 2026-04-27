from fastapi import APIRouter, Query
from app.agents.market_agent import market_agent_instance
from app.adapters.backend_adapter import get_backend_adapter
from app.tools.market_intelligence import run_deep_market_research

router = APIRouter(prefix="/api/v1/market", tags=["market"])
backend = get_backend_adapter()


def _first_value(payload, *keys):
    for key in keys:
        value = payload.get(key)
        if value not in (None, "", [], {}):
            return value
    return None


def _split_lines(value):
    if not value:
        return []
    if isinstance(value, list):
        items = value
    else:
        items = str(value).replace("\r", "\n").split("\n")
    cleaned = []
    for item in items:
        text = str(item).strip(" -\t")
        if text and text not in cleaned:
            cleaned.append(text)
    return cleaned


def _normalize_org_profile(org_profile):
    org_profile = org_profile or {}
    return {
        "legal_name": _first_value(org_profile, "legalName", "legal_name", "name"),
        "trading_name": _first_value(org_profile, "tradingName", "trading_name"),
        "business_type": _first_value(org_profile, "businessType", "business_type"),
        "industry": _first_value(org_profile, "industry", "businessIndustry"),
        "primary_activity": _first_value(org_profile, "primaryActivity", "primary_activity", "activity"),
        "target_market": _first_value(org_profile, "targetMarket", "target_market"),
        "state": _first_value(org_profile, "stateOfRegistration", "state", "registeredState"),
        "city": _first_value(org_profile, "city", "registeredCity"),
        "key_products_services": _split_lines(
            _first_value(
                org_profile,
                "keyProducts",
                "keyProductsServices",
                "key_products_services",
                "services",
            )
        ),
        "current_challenges": _split_lines(
            _first_value(org_profile, "currentChallenges", "current_challenges", "challenges")
        ),
    }


def _derive_search_tags(normalized):
    raw_terms = [
        *(normalized.get("key_products_services") or []),
        normalized.get("primary_activity"),
        normalized.get("industry"),
    ]

    tags = []
    for term in raw_terms:
        cleaned = str(term or "").strip()
        if not cleaned:
            continue
        lower = cleaned.lower()
        if lower not in [item.lower() for item in tags]:
            tags.append(cleaned)

    boosted = []
    keyword_map = {
        "ev charging": ["EV charging infrastructure", "EV charging stations"],
        "fleet": ["fleet charging", "electric fleet depots"],
        "amc": ["charger maintenance contracts"],
        "subsidy": ["EV subsidy consulting", "FAME incentives"],
        "audit": ["EV readiness audits"],
        "charger": ["commercial EV chargers"],
        "energy": ["energy infrastructure"],
    }
    combined = " ".join(tags).lower()
    for trigger, expansions in keyword_map.items():
        if trigger in combined:
            for expansion in expansions:
                if expansion.lower() not in [item.lower() for item in tags + boosted]:
                    boosted.append(expansion)

    return (boosted + tags)[:8]


def _build_market_profile(org_profile):
    normalized = _normalize_org_profile(org_profile)
    business_name = normalized["trading_name"] or normalized["legal_name"] or "This business"
    region_bits = [bit for bit in [normalized["city"], normalized["state"], "India"] if bit]
    region = ", ".join(dict.fromkeys(region_bits))
    industry = (normalized["industry"] or "").replace("_", " ").strip() or "business services"
    activity = normalized["primary_activity"] or industry
    services = normalized["key_products_services"][:5]
    search_tags = _derive_search_tags(normalized)

    unique_terms = []
    for term in [*search_tags, activity, industry, *services]:
        cleaned = str(term).strip()
        if cleaned and cleaned.lower() not in [item.lower() for item in unique_terms]:
            unique_terms.append(cleaned)

    business_type = normalized["target_market"] or normalized["business_type"] or "B2B"
    anchor_terms = unique_terms[:4]
    search_topic = " ".join(anchor_terms) or industry
    profile_signature = "|".join(
        [
            activity.lower(),
            industry.lower(),
            business_type.lower(),
            region.lower(),
            *[service.lower() for service in services],
            *[tag.lower() for tag in search_tags],
        ]
    )

    geography_hint = normalized["state"] or normalized["city"] or "India"
    news_query = f"{' '.join(anchor_terms[:3])} {geography_hint} EV charging fleet charging tenders policy incentives commercial buyers"
    opportunity_query = f"{' '.join(anchor_terms[:3])} {geography_hint} buyers hotels campuses fleet depots commercial real estate tenders"
    competitor_query = f"{' '.join(anchor_terms[:3])} {geography_hint} competitors maintenance operators charging providers pricing"
    research_query = f"{' '.join(anchor_terms[:4])} {geography_hint} EV charging commercial buyers tenders incentives fleet charging competitors"

    return {
        **normalized,
        "business_name": business_name,
        "region": region,
        "industry_label": industry,
        "activity_label": activity,
        "services": services,
        "search_tags": search_tags,
        "business_type": business_type,
        "search_topic": search_topic,
        "profile_signature": profile_signature,
        "news_query": news_query,
        "opportunity_query": opportunity_query,
        "competitor_query": competitor_query,
        "research_query": research_query,
    }


async def _load_profile(org_uuid: str, user_id: str):
    org_response = await backend.get_my_organization(user_id) if user_id else None
    org_profile = org_response.data if org_response and org_response.success else {}
    return _build_market_profile(org_profile)


@router.get("/intelligence")
async def get_market_intelligence(
    org_uuid: str = Query(...),
    business_id: int = Query(default=1),
    user_id: str = Query(default="")
):
    class Ctx:
        pass

    ctx = Ctx()
    ctx.org_uuid = org_uuid
    ctx.user_id = user_id
    ctx.business_id = business_id

    snapshot = await market_agent_instance._get_business_snapshot(ctx)
    market_profile = await _load_profile(org_uuid, user_id)

    cached = market_agent_instance.get_cached_intelligence(org_uuid)
    use_cached = bool(cached) and cached.get("profile_signature") == market_profile["profile_signature"]
    if not use_cached:
        from app.tools.market_intelligence import (
            fetch_market_news,
            fetch_competitor_intelligence,
            fetch_growth_opportunities,
        )
        import asyncio

        news, competitors, opportunities = await asyncio.gather(
            fetch_market_news(market_profile["news_query"]),
            fetch_competitor_intelligence(
                market_profile["competitor_query"],
                market_profile["business_type"],
                market_profile["region"],
            ),
            fetch_growth_opportunities(
                market_profile["opportunity_query"],
                snapshot.get("revenue", 0),
                snapshot.get("total_clients", 0),
                market_profile["region"],
            ),
        )
        market_data = {
            "news": news,
            "competitors": competitors,
            "opportunities": opportunities,
            "industry": market_profile["activity_label"],
            "profile_signature": market_profile["profile_signature"],
        }
    else:
        market_data = cached

    return {
        "success": True,
        "snapshot": snapshot,
        "profile": market_profile,
        "market": market_data,
        "cached": use_cached,
        "timestamp": cached.get("timestamp") if cached else None,
    }


@router.get("/deep-research")
async def get_market_deep_research(
    org_uuid: str = Query(...),
    business_id: int = Query(default=1),
    user_id: str = Query(default=""),
    query: str = Query(default=""),
):
    market_profile = await _load_profile(org_uuid, user_id)
    effective_query = query.strip() or market_profile["research_query"]
    research = await run_deep_market_research(effective_query)

    return {
        "success": True,
        "profile": market_profile,
        "research": research,
        "business_id": business_id,
    }
