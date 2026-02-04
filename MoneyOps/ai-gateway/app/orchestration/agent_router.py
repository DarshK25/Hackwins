"""
Agent Router - Routes intents to the correct agent
Supports both single-agent and multi-agent orchestration
"""
from typing import Dict, Any, Optional, List
from app.schemas.intents import Intent, AgentType, get_intent_requirements
from app.agents.base_agent import BaseAgent, AgentResponse
from app.agents.finance_agent import finance_agent
from app.features import feature_flags
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AgentRouter:
    """
    Routes intents to appropriate agents
    Handles both MVP (single agent) and v2.0 (multi-agent orchestration)
    """
    
    def __init__(self):
        self._agents: Dict[AgentType, BaseAgent] = {}
        self._register_agents()
        
        logger.info(
            "agent_router_initialized",
            registered_agents=list(self._agents.keys())
        )
    
    def _register_agents(self):
        """Register all enabled agents"""
        
        # Finance Agent (MVP)
        if feature_flags.ENABLE_FINANCE_AGENT:
            self._agents[AgentType.FINANCE_AGENT] = finance_agent
        
        # Other agents (v2.0 - stubs for now)
        if feature_flags.ENABLE_SALES_AGENT:
            # self._agents[AgentType.SALES_AGENT] = sales_agent
            pass
        
        if feature_flags.ENABLE_STRATEGY_AGENT:
            # self._agents[AgentType.STRATEGY_AGENT] = strategy_agent
            pass
        
        # ... other agents
    
    def get_agent(self, agent_type: AgentType) -> Optional[BaseAgent]:
        """Get an agent by type"""
        return self._agents.get(agent_type)
    
    def is_agent_available(self, agent_type: AgentType) -> bool:
        """Check if an agent is available"""
        return agent_type in self._agents
    
    async def route(
        self,
        intent: Intent,
        entities: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """
        Route intent to appropriate agent(s)
        
        Args:
            intent: Classified intent
            entities: Extracted entities
            context: Additional context (org_id, user_id, etc.)
        
        Returns:
            AgentResponse from primary agent
        """
        # Get intent requirements (includes agent routing info)
        requirements = get_intent_requirements(intent)
        
        primary_agent_type = requirements.primary_agent
        supporting_agent_types = requirements.supporting_agents
        
        logger.info(
            "routing_intent",
            intent=intent.value,
            primary_agent=primary_agent_type.value,
            supporting_agents=[a.value for a in supporting_agent_types]
        )
        
        # Get primary agent
        primary_agent = self.get_agent(primary_agent_type)
        
        if not primary_agent:
            # Agent not available - return stub response
            return self._build_agent_unavailable_response(
                primary_agent_type,
                intent
            )
        
        # Check if primary agent supports this intent
        if not primary_agent.supports_intent(intent):
            logger.warning(
                "agent_does_not_support_intent",
                agent=primary_agent_type.value,
                intent=intent.value
            )
            return AgentResponse(
                success=False,
                message=f"{primary_agent_type.value} does not support {intent.value}",
                agent_type=primary_agent_type,
                error="Intent not supported by this agent"
            )
        
        # MVP: Single-agent execution
        if not feature_flags.ENABLE_MULTI_AGENT_ORCHESTRATION:
            return await self._execute_single_agent(
                primary_agent,
                intent,
                entities,
                context
            )
        
        # v2.0: Multi-agent orchestration
        else:
            return await self._execute_multi_agent(
                primary_agent,
                supporting_agent_types,
                intent,
                entities,
                context
            )
    
    async def _execute_single_agent(
        self,
        agent: BaseAgent,
        intent: Intent,
        entities: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> AgentResponse:
        """Execute a single agent (MVP mode)"""
        try:
            response = await agent.process(intent, entities, context)
            return response
        
        except Exception as e:
            logger.error(
                "agent_execution_error",
                agent=agent.get_agent_type().value,
                error=str(e)
            )
            return AgentResponse(
                success=False,
                message=f"Agent execution failed: {str(e)}",
                error=str(e),
                agent_type=agent.get_agent_type()
            )
    
    async def _execute_multi_agent(
        self,
        primary_agent: BaseAgent,
        supporting_agent_types: List[AgentType],
        intent: Intent,
        entities: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> AgentResponse:
        """
        Execute multi-agent orchestration (v2.0)
        
        Strategy:
        1. Execute supporting agents in parallel (gather data)
        2. Pass results to primary agent
        3. Primary agent synthesizes final response
        """
        import asyncio
        
        # Get supporting agents
        supporting_agents = [
            self.get_agent(agent_type)
            for agent_type in supporting_agent_types
            if self.is_agent_available(agent_type)
        ]
        
        # Execute supporting agents in parallel
        supporting_results = await asyncio.gather(*[
            agent.process(intent, entities, context)
            for agent in supporting_agents
        ], return_exceptions=True)
        
        # Add supporting results to context
        if context is None:
            context = {}
        
        context["supporting_agent_results"] = [
            {
                "agent": agent.get_agent_type().value,
                "response": result.dict() if isinstance(result, AgentResponse) else str(result)
            }
            for agent, result in zip(supporting_agents, supporting_results)
        ]
        
        # Execute primary agent with enriched context
        return await self._execute_single_agent(
            primary_agent,
            intent,
            entities,
            context
        )
    
    def _build_agent_unavailable_response(
        self,
        agent_type: AgentType,
        intent: Intent
    ) -> AgentResponse:
        """Build response for unavailable agent"""
        return AgentResponse(
            success=False,
            message=f"{agent_type.value} is not available yet. Coming in v2.0!",
            agent_type=agent_type,
            implemented=False,
            recommendations=[
                f"{agent_type.value} will be available post-MVP",
                "Enable it via feature flags when ready",
                "Focus on Finance Agent operations for now"
            ]
        )
    
    def list_available_agents(self) -> List[str]:
        """List all available agent types"""
        return [agent_type.value for agent_type in self._agents.keys()]
    
    def get_agent_info(self, agent_type: AgentType) -> Optional[Dict[str, Any]]:
        """Get information about an agent"""
        agent = self.get_agent(agent_type)
        if not agent:
            return None
        
        return {
            "agent_type": agent_type.value,
            "name": agent.name,
            "supported_intents": [i.value for i in agent.get_supported_intents()],
            "available_tools": len(agent.get_enabled_tools()),
            "mvp_tools": len(agent.get_mvp_tools())
        }


# Global singleton
agent_router = AgentRouter()