"""
Compliance API Router - GST filing, TDS, tax compliance
Uses TRUE ComplianceExecutor for real API calls
"""
from fastapi import APIRouter, Request, HTTPException
from typing import Dict, Any, Optional
import asyncio

from app.agents.master_orchestrator import master_orchestrator
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/compliance/check")
async def check_compliance(request: Request) -> Dict[str, Any]:
    """
    Check compliance status for an organization
    Uses master_orchestrator → ComplianceExecutor
    """
    try:
        body = await request.json()
        org_id = body.get("org_id")
        user_id = body.get("user_id")

        if not org_id:
            raise HTTPException(status_code=400, detail="org_id is required")

        context = {
            "org_id": org_id,
            "user_id": user_id,
            "session_id": "compliance_check",
        }

        result = await master_orchestrator.process(
            user_message="check compliance status",
            context=context,
        )

        return result

    except Exception as e:
        logger.error("compliance_check_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compliance/gst/file")
async def file_gst(request: Request) -> Dict[str, Any]:
    """
    File GST returns
    Uses TRUE executor with real GST API integration
    """
    try:
        body = await request.json()
        org_id = body.get("org_id")
        period = body.get("period")  # YYYY-MM format

        if not org_id or not period:
            raise HTTPException(status_code=400, detail="org_id and period are required")

        context = {
            "org_id": org_id,
            "user_id": body.get("user_id"),
            "session_id": "gst_filing",
        }

        result = await master_orchestrator.process(
            user_message=f"file GST return for {period}",
            context=context,
        )

        return result

    except Exception as e:
        logger.error("gst_filing_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/compliance/tds/status")
async def tds_status(org_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Get TDS compliance status
    """
    try:
        context = {
            "org_id": org_id,
            "user_id": user_id,
            "session_id": "tds_status",
        }

        result = await master_orchestrator.process(
            user_message="check TDS status",
            context=context,
        )

        return result

    except Exception as e:
        logger.error("tds_status_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
