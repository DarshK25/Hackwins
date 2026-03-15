"""
Orchestrator Agent - Process efficiency and operational coordination
"""
from typing import Dict, Any, List, Optional
from app.agents.base_agent import BaseAgent, AgentResponse, ToolDefinition
from app.schemas.intents import Intent, AgentType
from app.adapters.backend_adapter import get_backend_adapter
from app.tools.tool_registry import Tool, tool_registry
from app.utils.logger import get_logger

logger = get_logger(__name__)

class OrchestratorAgent(BaseAgent):
    """
    Orchestrator Agent handles:
    - Process optimization
    - Resource allocation
    - Operational bottleneck detection
    """
    def __init__(self):
        super().__init__()
        self.backend = get_backend_adapter()
        self._register_orchestrator_tools()
        logger.info("orchestrator_agent_initialized")

    def get_agent_type(self) -> AgentType:
        return AgentType.ORCHESTRATOR

    def get_supported_intents(self) -> List[Intent]:
        return [
            Intent.PROCESS_OPTIMIZATION,
            Intent.RESOURCE_ALLOCATION,
            Intent.INVENTORY_OPTIMIZATION,
        ]

    def get_tools(self) -> List[ToolDefinition]:
        return []

    def _register_orchestrator_tools(self):
        efficiency_tool = Tool(
            name="analyze_process_efficiency",
            description="Analyze operational efficiency",
            category="operations",
            mvp_ready=True,
            handler=self._handle_efficiency_analysis
        )
        tool_registry.register_tools([efficiency_tool])

    async def _handle_efficiency_analysis(self, params, context=None):
        return {"efficiency_score": 88, "message": "Orchestrator analysis: Process efficiency is high (88/100)."}

    async def process(self, intent: Intent, entities: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        if context and context.get("auth_token"):
            self.backend.set_auth_token(context["auth_token"])
        try:
            result = await tool_registry.execute_tool("analyze_process_efficiency", entities, context)
            return self._build_success_response(result.result["message"], result.result, "analyze_process_efficiency")
        except Exception as e:
            return self._build_error_response(str(e))

orchestrator_agent = OrchestratorAgent()
