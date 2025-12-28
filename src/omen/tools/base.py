"""
Tool Infrastructure — Base protocol and types for L6 tool execution.

Tools are the mechanism by which L6 interacts with external reality.
All observations about current state should flow through tool execution.

Spec: OMEN.md §5 (Vat Boundary)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Protocol, runtime_checkable
from uuid import uuid4


class ToolSafety(Enum):
    """Tool safety classification."""
    READ = "READ"      # No side effects, freely available
    WRITE = "WRITE"    # Side effects, requires authorization
    MIXED = "MIXED"    # May have side effects depending on params


@dataclass
class EvidenceRef:
    """
    Reference to evidence supporting an observation.
    
    Links observations to their grounding in reality.
    """
    ref_id: str = field(default_factory=lambda: f"ev_{uuid4().hex[:12]}")
    ref_type: str = "tool_output"
    tool_name: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    reliability_score: float = 0.95
    raw_data: Any = None  # Original tool output
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "ref_id": self.ref_id,
            "ref_type": self.ref_type,
            "tool_name": self.tool_name,
            "timestamp": self.timestamp.isoformat(),
            "reliability_score": self.reliability_score,
        }


@dataclass
class ToolResult:
    """
    Result of tool execution.
    
    Contains the data returned and evidence reference for traceability.
    """
    success: bool
    data: Any = None
    error: str | None = None
    evidence_ref: EvidenceRef | None = None
    execution_time_ms: float = 0.0
    
    @classmethod
    def ok(cls, data: Any, tool_name: str, raw_data: Any = None) -> "ToolResult":
        """Create successful result with evidence."""
        return cls(
            success=True,
            data=data,
            evidence_ref=EvidenceRef(
                tool_name=tool_name,
                raw_data=raw_data or data,
            ),
        )
    
    @classmethod
    def fail(cls, error: str) -> "ToolResult":
        """Create failed result."""
        return cls(success=False, error=error)


@runtime_checkable
class Tool(Protocol):
    """
    Protocol for executable tools.
    
    Tools are the interface between OMEN and external reality.
    """
    
    @property
    def name(self) -> str:
        """Unique tool identifier."""
        ...
    
    @property
    def description(self) -> str:
        """Human-readable description for LLM context."""
        ...
    
    @property
    def safety(self) -> ToolSafety:
        """Safety classification."""
        ...
    
    def execute(self, params: dict[str, Any]) -> ToolResult:
        """Execute the tool with given parameters."""
        ...


class BaseTool(ABC):
    """
    Abstract base class for tool implementations.
    
    Provides common structure; subclasses implement execute().
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        pass
    
    @property
    def safety(self) -> ToolSafety:
        return ToolSafety.READ  # Default to safe
    
    @abstractmethod
    def execute(self, params: dict[str, Any]) -> ToolResult:
        pass
    
    def __repr__(self) -> str:
        return f"<Tool:{self.name} safety={self.safety.value}>"
