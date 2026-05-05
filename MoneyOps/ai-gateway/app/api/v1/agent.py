"""
True Multi-Agent Orchestration API - Main brain endpoint
Provides unified access to all collaborative executor agents.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from app.agents.base_executor import master_orchestrator
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/agent", tags=["True Multi-Agent"])


class AgentRequest(BaseModel):
    message: str = Field(..., description="User message")
    session_id: str = Field(
        default="default", description="Session ID for conversation continuity"
    )
    org_id: str = Field(..., description="Organization ID")
    user_id: Optional[str] = Field(None, description="User ID")
    business_id: Optional[str] = Field("1", description="Business ID")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")


class AgentResponseModel(BaseModel):
    message: str
    success: bool
    agent_type: str = "executor_orchestrator"
    executors_used: Optional[List[str]] = None
    iterations: Optional[int] = None
    ui_event: Optional[Dict[str, Any]] = None
    errors: Optional[List[str]] = None


@router.post("/chat", response_model=AgentResponseModel)
async def chat_with_agent(request: AgentRequest):
    """
    True agent-native execution endpoint.
    Executors make REAL API calls to complete financial operations.
    """
    result = await master_orchestrator.execute(
        user_request=request.message,
        org_id=request.org_id,
        user_id=request.user_id,
        business_id=request.business_id or "1",
        thread_id=request.session_id,
    )

    return AgentResponseModel(
        message=result["result"],
        success=result["success"],
        executors_used=result.get("executors_used", []),
        iterations=0,
        errors=result.get("errors", []),
        ui_event={
            "type": "execution_result",
            "operation": result.get("operation"),
            "data": result.get("data"),
        },
    )


@router.get("/health")
async def health_check():
    """Check orchestrator health and list available executors"""
    return {
        "status": "healthy",
        "orchestrator": "executor_orchestrator",
        "executors": list(master_orchestrator.executors.keys()),
        "llm_providers": ["groq", "cerebras", "gemini"],
    }
