"""
Intelligent Agent API - Main brain endpoint
Provides unified access to all agent capabilities
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from app.agents.intelligent_orchestrator import intelligent_agent
from app.agents.function_calling_agent import function_calling_agent
from app.memory.persistent_memory import persistent_memory
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/agent", tags=["Intelligent Agent"])


class AgentRequest(BaseModel):
    message: str = Field(..., description="User message")
    session_id: str = Field(
        default="default", description="Session ID for conversation continuity"
    )
    org_id: str = Field(..., description="Organization ID")
    user_id: Optional[str] = Field(None, description="User ID")
    business_id: Optional[str] = Field("1", description="Business ID")


class AgentResponseModel(BaseModel):
    message: str
    success: bool
    agent_type: str
    ui_event: Optional[Dict[str, Any]] = None
    sources: Optional[List[str]] = None
    function_results: Optional[List[Dict[str, Any]]] = None


@router.post("/chat", response_model=AgentResponseModel)
async def chat_with_agent(request: AgentRequest):
    """
    Main chat endpoint - routes to appropriate agent and returns response.

    This is the unified entry point that:
    1. Classifies user intent
    2. Routes to market/finance/compliance agent
    3. Can call functions dynamically
    4. Maintains conversation context
    """
    context = {
        "session_id": request.session_id,
        "org_id": request.org_id,
        "org_uuid": request.org_id,
        "user_id": request.user_id,
        "business_id": request.business_id,
    }

    conversation_history = await intelligent_agent.get_conversation_context(
        request.session_id, max_turns=10
    )

    result = await intelligent_agent.process(
        user_message=request.message,
        context=context,
        conversation_history=conversation_history,
    )

    return AgentResponseModel(**result)


@router.post("/chat/function", response_model=AgentResponseModel)
async def chat_with_functions(request: AgentRequest):
    """
    Chat endpoint with function calling enabled.
    Uses OpenAI-style function calling for dynamic tool execution.
    """
    context = {
        "session_id": request.session_id,
        "org_id": request.org_id,
        "org_uuid": request.org_id,
        "user_id": request.user_id,
        "business_id": request.business_id,
    }

    conversation_history = await intelligent_agent.get_conversation_context(
        request.session_id, max_turns=10
    )

    decision = await function_calling_agent.decide_and_execute(
        user_message=request.message,
        context=context,
        conversation_history=conversation_history,
        max_iterations=3,
    )

    return AgentResponseModel(
        message=decision.get("response", "I've processed that."),
        success=True,
        agent_type="function_calling_agent",
        function_results=decision.get("function_calls", []),
    )


@router.get("/functions")
async def list_functions():
    """
    List all available functions/tools the agent can call.
    """
    functions = function_calling_agent.get_functions_for_llm()
    return {"functions": functions, "count": len(functions)}


@router.get("/history/{session_id}")
async def get_conversation_history(session_id: str, max_turns: int = 20):
    """
    Get conversation history for a session.
    """
    history = await intelligent_agent.get_conversation_context(session_id, max_turns)
    return {"session_id": session_id, "turns": len(history), "history": history}


@router.get("/knowledge/{org_id}")
async def get_agent_knowledge(org_id: str, category: Optional[str] = None):
    """
    Get knowledge stored by the agent for this organization.
    """
    knowledge = persistent_memory.get_knowledge(org_id, category)
    return {"org_id": org_id, "knowledge": knowledge}


@router.post("/learn/{org_id}")
async def store_knowledge(
    org_id: str, category: str, key: str, value: Any, confidence: float = 0.8
):
    """
    Store knowledge learned from interactions.
    """
    success = persistent_memory.store_knowledge(
        org_id=org_id,
        category=category,
        key=key,
        value=value,
        confidence=confidence,
        source="conversation",
    )

    return {"success": success, "org_id": org_id, "category": category, "key": key}
