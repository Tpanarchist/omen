"""
Template Models — Data structures for episode templates.

Spec: OMEN.md §11.2 "Episode template artifact"
"""

from typing import Any
from pydantic import BaseModel, Field, field_validator, model_validator

from omen.vocabulary import (
    TemplateID,
    IntentClass,
    LayerSource,
    FSMState,
    PacketType,
    QualityTier,
    ToolsState,
)


class TemplateStep(BaseModel):
    """
    Single step in an episode template.
    
    Represents one packet emission in the cognitive flow.
    Spec: OMEN.md §11.2 "steps[] with owner layer and bindings"
    """
    step_id: str = Field(..., description="Unique identifier within template")
    owner_layer: LayerSource = Field(..., description="Layer responsible for this step")
    fsm_state: FSMState = Field(..., description="FSM state this step occupies")
    packet_type: PacketType | None = Field(
        ..., 
        description="Packet type emitted (None for terminal states)"
    )
    next_steps: list[str] = Field(
        default_factory=list,
        description="Possible next step_ids (empty for exit steps)"
    )
    bindings: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional MCP field bindings for compilation"
    )
    
    @field_validator("step_id")
    @classmethod
    def step_id_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("step_id cannot be empty")
        return v


class TemplateConstraints(BaseModel):
    """
    Preconditions for template execution.
    
    Spec: OMEN.md §11.2 "constraints (min tier, tools state, write allowed)"
    """
    min_tier: QualityTier = Field(
        ..., 
        description="Minimum quality tier required to execute"
    )
    tools_state: list[ToolsState] = Field(
        ...,
        description="Acceptable tools states for execution"
    )
    write_allowed: bool = Field(
        ...,
        description="Whether template can issue WRITE directives"
    )
    
    @field_validator("tools_state")
    @classmethod
    def tools_state_not_empty(cls, v: list[ToolsState]) -> list[ToolsState]:
        if not v:
            raise ValueError("tools_state must contain at least one state")
        return v


class EpisodeTemplate(BaseModel):
    """
    Recipe for a canonical cognitive pattern.
    
    Templates define valid episode flows through the FSM.
    Spec: OMEN.md §11.2 "Episode template artifact", §11.3 "Canonical templates"
    """
    template_id: TemplateID = Field(..., description="Canonical template identifier")
    name: str = Field(..., description="Human-readable template name")
    description: str = Field(..., description="What this template does")
    intent_class: IntentClass = Field(..., description="Primary intent classification")
    constraints: TemplateConstraints = Field(..., description="Execution preconditions")
    steps: list[TemplateStep] = Field(..., description="Ordered list of template steps")
    entry_step: str = Field(..., description="Starting step_id")
    exit_steps: list[str] = Field(..., description="Valid termination step_ids")
    
    @field_validator("steps")
    @classmethod
    def steps_not_empty(cls, v: list[TemplateStep]) -> list[TemplateStep]:
        if not v:
            raise ValueError("Template must have at least one step")
        return v
    
    @field_validator("exit_steps")
    @classmethod
    def exit_steps_not_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("Template must have at least one exit step")
        return v
    
    @model_validator(mode="after")
    def validate_step_references(self) -> "EpisodeTemplate":
        """Validate that entry_step and exit_steps reference existing steps."""
        step_ids = {step.step_id for step in self.steps}
        
        if self.entry_step not in step_ids:
            raise ValueError(f"entry_step '{self.entry_step}' not found in steps")
        
        for exit_id in self.exit_steps:
            if exit_id not in step_ids:
                raise ValueError(f"exit_step '{exit_id}' not found in steps")
        
        return self
    
    def get_step(self, step_id: str) -> TemplateStep | None:
        """Get a step by its ID."""
        for step in self.steps:
            if step.step_id == step_id:
                return step
        return None
    
    def get_step_ids(self) -> set[str]:
        """Get all step IDs in this template."""
        return {step.step_id for step in self.steps}
