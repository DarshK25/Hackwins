from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from enum import Enum

from app.schemas.intents import AgentType, Intent, ComplexityLevel

class AgentCapability(str, Enum):
    """Agent Capabilities"""
    CRUD_OPERATIONS = "crud_operations"
    ANALYTICS_= "analytics"
    STRATEGIC_PLANNING = "strategic_planning"
    FORECASTING = "forecasting"
    RECOMMENDATIONS = "recommendations"

class ToolDefinition:
    """Definition of a tool that an agent can use"""
    name: str
    description: str
    parameters: Dict[str, Any]
    required_params: List[str] = []
    enabled: bool = True
    mvp_ready: bool = True

class AgentResponse(BaseModel):
    """Standard response from an agent"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

    #tool execution details
    tool_used: Optional[str] = None
    tool_calls: List[str] = []

    #Agent metadata
    agent_type: AgentType
    confidence: float = 1.0

    #Strategic features for v2.0
    recommendations: List[str] = []
    next_steps: List[str] = []

    #Error handling
    error: Optional[str] = None
    needs_clarification: bool = False
    clarification_question : Optional[str] = None

    #V2.0
    implemented: bool = True

class BaseAgent: 
    """Abstract base class for all agents in MoneyOps
    All agents must implement:
    -get_agent_type()
    -get_supported_intents()
    -get_tools()
    -process()
    """
    def __init__ (self):
        self.name = self.__class__.__name__
        self._tools: Dict[str, ToolDefinition] = {}
        self._initialize_tools()

    @abstractmethod
    def get_agent_type(self) -> AgentType:
        """Return agent type"""
        pass
    
    @abstractmethod
    def get_supported_intents(self) -> List[Intent]:
        """Return list of intents this agent can handle"""
        pass

    @abstractmethod
    def get_tools(self) -> List[ToolDefinition]:
        """Return list of tools this agent has access to"""
        pass

    @abstractmethod
    async def process(
        self,
        intent: Intent,
        entities: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """
        Process a request
        Args:
            intent: Classified user intent
            entities: Extracted entities
            context: Additional context (conversation history, user prefs,etc.)
        
        Returns:
            AgentResponse with results
        """
        pass

    def _initialize_tools(self):
        """
        Initialize tools - called in __init__
        Subclasses can override to populate self._tools
        """
        tools = self.get_tools()
        for tool in tools:
            self._tools[tool.name] = tool
        
    def get_tool(self, tool_name: str) -> List[ToolDefinition]:
        """Get a specific tool by name"""
        return self._tools.get(tool_name)

    def get_enabled_tools(self) -> List[ToolDefinition]:
        """Get only enabled tools (respects feature flags)"""   
        return [t for t in self._tools.values() if t.enabled]
    
    def get_mvp_tools(self) -> List[ToolDefinition]:
        return [t for t in self._tools.values() if t.mvp_ready and t.enabled]

    def supports_intent(self, intent: Intent) -> bool:
        """Check if this agent supports a given intent"""
        return intent in self.get_supported_intents()
    
    def _build_success_response(
            self,
            message: str,
            data: Optional[Dict[str, Any]] = None,
            tool_used : Optional[str] = None,
            confidence: float = 1.0
    ) -> AgentResponse:
        """Helper to build success response"""
        return AgentResponse(
            success=True,
            message=message,
            tool_used=tool_used,
            agent_type=self.get_agent_type(),
            confidence=confidence,
            implemented=True
        )

    def _build_error_response(
        self,
        error: str,
        needs_clarification: bool = False,
        clarification_question: Optional[str] = None
    ) -> AgentResponse:
        """Helper to build error response"""
        return AgentResponse(
            success=False,
            message=f"Error:{error}",
            error=error,
            needs_clarification=needs_clarification,
            clarification_question=clarification_question,
            agent_type=self.get_agent_type(),
            implemented=True
        )

    def _build_stub_response(
        self,
        feature_name: str,
        available_in: str = "v2.0"
    ) -> AgentResponse: 
        """Helper to build stub response for unimplemented features"""
        return AgentResponse(
            success=False,
            message=f"Feature {feature_name} is not available in {available_in}",
            agent_type=self.get_agent_type(),
            implemented=False,
            recommendations=[
                f"{feature_name} is expected to be available in {available_in}"
            ]
        )

    def __repr__(self) -> str :
        return f"<{self.name} agent_type={self.get_agent_type().value}>"