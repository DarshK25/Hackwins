"""
Market Agent - Market research, growth strategy, and competitive intelligence
"""
from typing import Dict, Any, List, Optional
from app.agents.base_agent import BaseAgent, AgentResponse, ToolDefinition
from app.schemas.intents import Intent, AgentType
from app.adapters.backend_adapter import get_backend_adapter
from app.tools.tool_registry import Tool, tool_registry
from app.utils.logger import get_logger

logger = get_logger(__name__)

class MarketAgent(BaseAgent):
    """
    Market Agent handles:
    - Market expansion planning
    - Growth strategy
    - Competitive intelligence
    - Scaling advice
    """
    def __init__(self):
        super().__init__()
        self.backend = get_backend_adapter()
        self._register_market_tools()
        logger.info("market_agent_initialized")

    def get_agent_type(self) -> AgentType:
        return AgentType.MARKET_AGENT

    def get_supported_intents(self) -> List[Intent]:
        return [
            Intent.GROWTH_STRATEGY,
            Intent.MARKET_EXPANSION,
            Intent.PRODUCT_STRATEGY,
            Intent.SCALING_ADVICE,
            Intent.PARTNERSHIP_OPPORTUNITIES,
        ]

    def get_tools(self) -> List[ToolDefinition]:
        return []

    def _register_market_tools(self):
        growth_tool = Tool(
            name="analyze_growth_opportunities",
            description="Analyze market growth opportunities",
            category="market",
            mvp_ready=True,
            handler=self._handle_growth_analysis
        )
        tool_registry.register_tools([growth_tool])

    async def _handle_growth_analysis(self, params, context=None):
        return {"opportunities": ["New sector expansion"], "message": "Market analysis complete. Expansion into IT sector recommended."}

    async def process(self, intent: Intent, entities: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        if context and context.get("auth_token"):
            self.backend.set_auth_token(context["auth_token"])
        try:
            result = await tool_registry.execute_tool("analyze_growth_opportunities", entities, context)
            return self._build_success_response(result.result["message"], result.result, "analyze_growth_opportunities")
        except Exception as e:
            return self._build_error_response(str(e))

market_agent = MarketAgent()
