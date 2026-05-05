"""
Test Agents Router - For testing TRUE executor functionality
Uses master_orchestrator with real API calls
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.agents.master_orchestrator import master_orchestrator
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


class AgentExecuteRequest(BaseModel):
    message: str
    org_id: str
    user_id: Optional[str] = None
    session_id: Optional[str] = "test_session"


@router.post("/test/agents/execute")
async def execute_agent(request: AgentExecuteRequest):
    """
    Test endpoint to execute agent with TRUE executors
    Uses master_orchestrator → real API calls
    """
    try:
        context = {
            "org_id": request.org_id,
            "user_id": request.user_id,
            "session_id": request.session_id or "test_session",
        }

        result = await master_orchestrator.process(
            user_message=request.message,
            context=context,
        )

        return result

    except Exception as e:
        logger.error("test_agent_execution_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/test/agents/health")
async def agents_health():
    """Check health of all executors"""
    return {
        "status": "healthy",
        "executors": ["finance_ops", "compliance", "collections", "treds"],
        "orchestrator": "master_orchestrator",
        "architecture": "TRUE agent-native with real API calls",
    }
