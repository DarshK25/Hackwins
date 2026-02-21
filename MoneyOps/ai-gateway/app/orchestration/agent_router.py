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
        
        # Finance Agent (always on)
        if feature_flags.ENABLE_FINANCE_AGENT:
            self._agents[AgentType.FINANCE_AGENT] = finance_agent
        
        # Sales Agent
        if feature_flags.ENABLE_SALES_AGENT:
            try:
                from app.agents.sales_agent import sales_agent
                self._agents[AgentType.SALES_AGENT] = sales_agent
                logger.info("sales_agent_registered")
            except Exception as e:
                logger.error("sales_agent_registration_failed", error=str(e))
        
        # Strategy Agent
        if feature_flags.ENABLE_STRATEGY_AGENT:
            try:
                from app.agents.strategy_agent import strategy_agent
                self._agents[AgentType.STRATEGY_AGENT] = strategy_agent
                logger.info("strategy_agent_registered")
            except Exception as e:
                logger.error("strategy_agent_registration_failed", error=str(e))
        
        # Compliance Agent
        if feature_flags.ENABLE_COMPLIANCE_AGENT:
            try:
                from app.agents.compliance_agent import compliance_agent
                self._agents[AgentType.COMPLIANCE_AGENT] = compliance_agent
                logger.info("compliance_agent_registered")
            except Exception as e:
                logger.error("compliance_agent_registration_failed", error=str(e))
        
        # Customer Agent
        if feature_flags.ENABLE_CUSTOMER_AGENT:
            try:
                from app.agents.customer_agent import customer_agent
                self._agents[AgentType.CUSTOMER_AGENT] = customer_agent
                logger.info("customer_agent_registered")
            except Exception as e:
                logger.error("customer_agent_registration_failed", error=str(e))
        
        # Growth Agent
        if feature_flags.ENABLE_GROWTH_AGENT:
            try:
                from app.agents.growth_agent import growth_agent
                self._agents[AgentType.GROWTH_AGENT] = growth_agent
                logger.info("growth_agent_registered")
            except Exception as e:
                logger.error("growth_agent_registration_failed", error=str(e))
        
        # Operations Agent
        if feature_flags.ENABLE_OPERATIONS_AGENT:
            try:
                from app.agents.operations_agent import operations_agent
                self._agents[AgentType.OPERATIONS_AGENT] = operations_agent
                logger.info("operations_agent_registered")
            except Exception as e:
                logger.error("operations_agent_registration_failed", error=str(e))

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
        
        # Fallback: if primary agent not available, try strategy or finance
        primary_agent = self.get_agent(primary_agent_type)
        
        if not primary_agent:
            # Try strategy agent as fallback for strategic/analytical queries
            if self.is_agent_available(AgentType.STRATEGY_AGENT):
                primary_agent = self.get_agent(AgentType.STRATEGY_AGENT)
                primary_agent_type = AgentType.STRATEGY_AGENT
                logger.info("agent_fallback_to_strategy", original_agent=requirements.primary_agent.value)
            elif self.is_agent_available(AgentType.FINANCE_AGENT):
                primary_agent = self.get_agent(AgentType.FINANCE_AGENT)
                primary_agent_type = AgentType.FINANCE_AGENT
                logger.info("agent_fallback_to_finance", original_agent=requirements.primary_agent.value)
            else:
                return self._build_agent_unavailable_response(primary_agent_type, intent)
        
        # Check if primary agent supports this intent
        if not primary_agent.supports_intent(intent):
            logger.warning(
                "agent_does_not_support_intent",
                agent=primary_agent_type.value,
                intent=intent.value
            )
            # Still try to execute — strategy agent can handle many intents
        
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
        """Execute a single agent"""
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
        """
        import asyncio
        
        # Get supporting agents
        supporting_agents = [
            self.get_agent(agent_type)
            for agent_type in supporting_agent_types
            if self.is_agent_available(agent_type)
        ]
        
        if supporting_agents:
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
                    "response": result.model_dump() if isinstance(result, AgentResponse) else str(result)
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
            message=f"No agents available to handle this request. Please check agent configuration.",
            agent_type=agent_type,
            implemented=False,
            recommendations=[
                "Ensure at least one agent is enabled in feature flags",
                "Check agent initialization logs for errors"
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
    
    def get_all_agents_status(self) -> Dict[str, Any]:
        """Get status of all registered agents"""
        all_agent_types = [
            AgentType.FINANCE_AGENT,
            AgentType.SALES_AGENT,
            AgentType.STRATEGY_AGENT,
            AgentType.COMPLIANCE_AGENT,
            AgentType.CUSTOMER_AGENT,
            AgentType.GROWTH_AGENT,
            AgentType.OPERATIONS_AGENT,
        ]
        
        return {
            "registered": [at.value for at in self._agents.keys()],
            "total_registered": len(self._agents),
            "total_possible": len(all_agent_types),
            "agents": {
                at.value: {
                    "available": at in self._agents,
                    "info": self.get_agent_info(at) if at in self._agents else None
                }
                for at in all_agent_types
            }
        }


# Global singleton
agent_router = AgentRouter()