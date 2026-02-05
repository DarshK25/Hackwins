"""
Tool registry for centralized tool mgmt and executn
"""
from typing import List, Dict, Any, Optional, Callable, Awaitable
from pydantic import BaseModel, Field
import asyncio
from app.utils.logger import get_logger

logger = get_logger(__name__)

class ToolParameters(BaseModel):
    """Parameter definition for a tool"""
    name: str
    type: str  # "string", "number", "boolean", "object", "array" etc
    description: str
    required: bool = False
    default: Optional[Any] = None
    enum: Optional[List[Any]] = None  # For fixed choices

class Tool(BaseModel):
    """Complete tool definition with handler"""
    name: str
    description: str
    parameters: List[ToolParameters] = Field(default_factory=list)

    #handler function not serialized
    handler: Optional[Callable] = Field(default=None, exclude=True)

    #Feature flags
    enabled: bool = True
    mvp_ready: bool = True
    
    #metadata
    category: str="general" #"invoice", "payment", "analytics", etc
    requires_confirmation: bool = False
    estimated_time_seconds: int = 2
    
    class Config:
        arbitrary_types_allowed = True

class ToolExecutionResult(BaseModel):
    """Result of tool execution"""
    success: bool
    tool_name : str
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: Optional[int] = None

class ToolRegistry:
    """Central registry for all agent tools
    Manages tool registration, validation, execution
    """
    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        logger.info("tool_registry_initialized")

    def register_tool(self, tool: Tool):
        """Register a tool"""
        if tool.name in self._tools :
            logger.warning("tool_already_registered", tool = tool.name)

        self._tools[tool.name ] = tool
        logger.debug("tool_registered", tool=tool.name, category=tool.category)

    def register_tools(self, tools:List[Tool]):
        """Register multiple tools"""
        for tool in tools:
            self.register_tool(tool)

    def get_tool(self, tool_name: str) -> Optional[Tool]:
        """Get a tool by name"""
        return self._tools.get(tool_name)

    def get_enabled_tools(self) -> List[Tool]:
        """Get all enabled tools"""
        return [t for t in self._tools.values() if t.enabled]
    
    def get_mvp_tools(self) -> List[Tool]:
        """Get MVP-ready enabled tools"""
        return [t for t in self._tools.values() if t.mvp_ready and t.enabled]
    
    def get_tools_by_category(self, category: str) -> List[Tool]:
        """Get tools by category"""
        return [t for t in self._tools.values() if t.category == category and t.enabled]
    
    def validate_parameters(
        self,
        tool_name:str,
        parameters: Dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """
        Validate parameters for a tool
        
        Returns:
            (isValid, error_message)
        """
        tool = self.get_tool(tool_name)
        if not tool:
            return False, f"Tool '{tool_name}' not found"
        
        # Check required parameters
        for param in tool.parameters:
            if param.required and param.name not in (parameters or {}):
                return False, f"Missing required parameter: '{param.name}'"
            
        # Type validations
        for param in tool.parameters:
            if param.name in (parameters or {}):
                value = parameters[param.name]

                # enum validation
                if param.enum and value not in param.enum:
                    return False, f"Parameter '{param.name}' must be one of {param.enum}"
                
        return True, None
    
    async def execute_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Execute a tool with given parameters
        
        Args: 
            tool_name: Name of the tool to execute
            parameters: Parameters for the tool
            context: Additional context like user_id, org_id, etc
        Returns 
            ToolExecutionResult
        """
        import time
        start_time = time.time()

        #Get tool
        tool = self.get_tool(tool_name)
        if not tool:
            return ToolExecutionResult(
                success=False,
                tool_name=tool_name,
                error=f"Tool {tool_name} not found"
            )
        
        #Check if enabled
        if not tool.enabled:
            return ToolExecutionResult(
                success=False,
                tool_name=tool_name,
                error=f"Tool '{tool_name} is disabled"
            )
        
        #validate parameters
        is_valid, error_msg = self.validate_parameters(tool_name, parameters)
        if not is_valid:
            return ToolExecutionResult(
                success=False,
                tool_name=tool_name,
                error=error_msg
            )

        # Execute handler
        if not tool.handler:
            return ToolExecutionResult(
                success=False,
                tool_name=tool_name,
                error=f"Tool '{tool_name}' has no handler function"
            )
        
        try:
            #call handler(supports both sync and async)
            if asyncio.iscoroutinefunction(tool.handler):
                result = await tool.handler(parameters, context) 
            else:
                result = tool.handler(parameters, context)

            execution_time = int((time.time() - start_time) * 1000)

            logger.info(
                "tool_executed",
                tool=tool_name,
                success=True,
                execution_time_ms=execution_time
            )

            return ToolExecutionResult(
                success=True,
                tool_name=tool_name,

                result=result,
                execution_time_ms = execution_time
            )
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)

            logger.error(
                "tool_execution_failed",
                tool=tool_name,
                error=str(e),
                execution_time_ms=execution_time
            )
            return ToolExecutionResult(
                success=False,
                tool_name=tool_name,
                error=str(e),
                execution_time_ms=execution_time
            )

    def list_tools(self, enabled_only: bool = True) -> List[str]:
        """List all tool names"""
        if enabled_only:
            return [name for name, tool in self._tools.items() if tool.enabled]
        return list(self._tools.keys())

    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get human-readable tool info"""
        tool = self.get_tool(tool_name)
        if not tool:
            return None

        return {
            "name": tool.name,
            "description": tool.description,
            "category": tool.category,
            "parameters": [
                {
                    "name": p.name,
                    "type": p.type,
                    "description": p.description,
                    "required": p.required,
                    "default": p.default
                }
                for p in tool.parameters
            ],
            "enabled": tool.enabled,
            "mvp_ready": tool.mvp_ready,
            "requires_confirmation":tool.requires_confirmation,
            "estimate_time_seconds": tool.estimated_time_seconds
        }
    
#Global Singleton
tool_registry = ToolRegistry()