from fastapi import APIRouter, Query
from app.services.market_intelligence_service import get_market_intelligence_payload

router = APIRouter(prefix="/api/v1/market", tags=["market"])

@router.get("/intelligence")
async def get_market_intelligence(
    org_uuid: str = Query(...),
    business_id: int = Query(default=1),
    user_id: str = Query(default="")
):
    return await get_market_intelligence_payload(
        org_uuid=org_uuid,
        business_id=business_id,
        user_id=user_id,
    )
