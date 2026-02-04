from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.orchestration.agent_router import agent_router
from app.schemas.intents import Intent
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


class AgentExecuteRequest(BaseModel):
    intent: str
    entities: Optional[Dict[str, Any]] = {}
    context: Optional[Dict[str, Any]] = {}


@router.post("/test/agents/execute")
async def execute_agent(request: AgentExecuteRequest, fastapi_request: Request):
    """Execute an agent for a given intent (test endpoint)"""
    try:
        # Extract token if present
        auth_header = fastapi_request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            if not request.context:
                request.context = {}
            request.context["auth_token"] = token

        # Validate intent
        try:
            intent_enum = Intent(request.intent)
        except Exception:
            raise HTTPException(status_code=400, detail=f"Invalid intent: {request.intent}")

        # Route to agent
        response = await agent_router.route(
            intent=intent_enum,
            entities=request.entities or {},
            context=request.context or {},
        )

        # AgentResponse is a pydantic model — return as dict
        return response.dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error("execute_agent_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Agent execution failed")
