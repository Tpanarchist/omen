"""
Compiled Episode — Output of template compilation.

Represents a packet sequence skeleton ready for execution.
Spec: OMEN.md §11.4
"""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID
from typing import Any

from omen.vocabulary import (
    LayerSource,
    FSMState,
    PacketType,
    TemplateID,
)


@dataclass
class CompiledStep:
    """
    Single compiled step ready for execution.
    
    Contains the packet skeleton with MCP fields bound from context.
    """
    step_id: str
    sequence_number: int  # Order in episode
    owner_layer: LayerSource
    fsm_state: FSMState
    packet_type: PacketType | None
    
    # Bound MCP fields (from context + template bindings)
    mcp_bindings: dict[str, Any] = field(default_factory=dict)
    
    # From template
    next_steps: list[str] = field(default_factory=list)
    
    # Execution tracking
    executed: bool = False
    packet_id: str | None = None  # Assigned when packet emitted


@dataclass 
class CompiledEpisode:
    """
    Complete compiled episode ready for execution.
    
    Contains all steps with MCP bindings applied.
    """
    # Identity
    correlation_id: UUID
    template_id: TemplateID
    campaign_id: str | None = None
    
    # Compiled steps
    steps: list[CompiledStep] = field(default_factory=list)
    entry_step: str = ""
    exit_steps: list[str] = field(default_factory=list)
    
    # Compilation metadata
    compiled_at: datetime = field(default_factory=datetime.now)
    context_snapshot: dict[str, Any] = field(default_factory=dict)
    
    # Execution state
    current_step: str | None = None
    completed: bool = False
    
    def get_step(self, step_id: str) -> CompiledStep | None:
        """Get compiled step by ID."""
        for step in self.steps:
            if step.step_id == step_id:
                return step
        return None
    
    def get_next_steps(self) -> list[CompiledStep]:
        """Get possible next steps from current position."""
        if self.current_step is None:
            entry = self.get_step(self.entry_step)
            return [entry] if entry else []
        
        current = self.get_step(self.current_step)
        if current is None:
            return []
        
        return [
            self.get_step(sid) 
            for sid in current.next_steps 
            if self.get_step(sid)
        ]
