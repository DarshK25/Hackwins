from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from app.agents.compliance_agent import compliance_agent
from app.schemas.intents import Intent
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/compliance", tags=["Compliance"])

@router.get("/status")
async def get_compliance_status(
    org_uuid: str = Query(..., description="Organization UUID"),
    business_id: str = Query(None),
    user_id: Optional[str] = Query(None)
):
    try:
        # Run the agent logic with aggregation
        response = await compliance_agent.get_compliance_dashboard_data(
            org_id=org_uuid,
            context={"user_id": user_id, "business_id": business_id}
        )
        
        if response.success:
            return {
                "success": True,
                "data": response.data,
                "cached": False
            }
        
        return {
            "success": False,
            "error": response.message,
            "data": None
        }
            
    except Exception as e:
        logger.error("compliance_route_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
