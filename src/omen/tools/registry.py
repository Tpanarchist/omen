"""
Tool Registry — Manages available tools for L6 execution.

Provides tool discovery, authorization checking, and execution.
"""

from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

from omen.tools.base import Tool, ToolResult, ToolSafety

if TYPE_CHECKING:
    from omen.orchestrator.ledger import ActiveToken


class UnauthorizedToolError(Exception):
    """Raised when tool execution lacks required authorization."""
    pass


class ToolNotFoundError(Exception):
    """Raised when requested tool doesn't exist."""
    pass


@dataclass
class ToolRegistry:
    """
    Registry of available tools.
    
    Handles tool registration, discovery, and authorized execution.
    """
    _tools: dict[str, Tool] = field(default_factory=dict)
    
    def register(self, tool: Tool) -> None:
        """Register a tool."""
        self._tools[tool.name] = tool
    
    def unregister(self, name: str) -> Tool | None:
        """Unregister and return a tool."""
        return self._tools.pop(name, None)
    
    def get(self, name: str) -> Tool | None:
        """Get a tool by name."""
        return self._tools.get(name)
    
    def list_tools(self) -> list[Tool]:
        """List all registered tools."""
        return list(self._tools.values())
    
    def list_tool_names(self) -> list[str]:
        """List all tool names."""
        return list(self._tools.keys())
    
    def get_tool_descriptions(self) -> str:
        """Get formatted descriptions for LLM context."""
        lines = ["Available tools:"]
        for tool in self._tools.values():
            safety_note = "" if tool.safety == ToolSafety.READ else f" [{tool.safety.value}]"
            lines.append(f"  - {tool.name}{safety_note}: {tool.description}")
        return "\n".join(lines)
    
    def execute(
        self,
        tool_name: str,
        params: dict[str, Any],
        token: "ActiveToken | None" = None,
    ) -> ToolResult:
        """
        Execute a tool with authorization checking.
        
        Args:
            tool_name: Name of tool to execute
            params: Parameters for the tool
            token: Authorization token (required for WRITE/MIXED tools)
        
        Returns:
            ToolResult with data or error
        
        Raises:
            ToolNotFoundError: Tool doesn't exist
            UnauthorizedToolError: WRITE/MIXED tool without valid token
        """
        tool = self.get(tool_name)
        if tool is None:
            raise ToolNotFoundError(f"Tool not found: {tool_name}")
        
        # Check authorization for non-READ tools
        if tool.safety in {ToolSafety.WRITE, ToolSafety.MIXED}:
            if token is None:
                raise UnauthorizedToolError(
                    f"Tool '{tool_name}' requires authorization token"
                )
            if not token.is_valid:
                raise UnauthorizedToolError(
                    f"Token for tool '{tool_name}' is invalid or expired"
                )
            # Consume a use from the token
            if not token.use():
                raise UnauthorizedToolError(
                    f"Token for tool '{tool_name}' has no remaining uses"
                )
        
        # Execute tool
        try:
            return tool.execute(params)
        except Exception as e:
            return ToolResult.fail(f"Tool execution failed: {str(e)}")


def create_registry() -> ToolRegistry:
    """Factory for tool registry."""
    return ToolRegistry()
