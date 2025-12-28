"""
Tools — L6 tool execution infrastructure.

Provides tools for interacting with external reality:
- Clock: Current time
- FileRead/FileWrite: Local filesystem
- HttpGet: Web requests
- EnvRead: Environment variables

Spec: OMEN.md §5 (Vat Boundary)
"""

from omen.tools.base import (
    ToolSafety,
    EvidenceRef,
    ToolResult,
    Tool,
    BaseTool,
)
from omen.tools.registry import (
    ToolRegistry,
    ToolNotFoundError,
    UnauthorizedToolError,
    create_registry,
)
from omen.tools.builtin import (
    ClockTool,
    FileReadTool,
    FileWriteTool,
    HttpGetTool,
    EnvironmentTool,
    create_default_registry,
)

__all__ = [
    # Base
    "ToolSafety",
    "EvidenceRef",
    "ToolResult",
    "Tool",
    "BaseTool",
    # Registry
    "ToolRegistry",
    "ToolNotFoundError",
    "UnauthorizedToolError",
    "create_registry",
    # Built-in tools
    "ClockTool",
    "FileReadTool",
    "FileWriteTool",
    "HttpGetTool",
    "EnvironmentTool",
    "create_default_registry",
]
