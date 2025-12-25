"""
TaskDirectivePacket — Execution commands from Layer 5 to Layer 6.

Directives flow southbound, commanding Layer 6 (Task Prosecution) to
perform specific actions. Each directive must eventually be closed
by a TaskResultPacket.

Spec: OMEN.md §9.3, §7.2, §10.4, §11.1
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from omen.vocabulary import PacketType, TaskClass, ToolSafety, ToolsState
from omen.schemas.header import PacketHeader
from omen.schemas.mcp import MCP


class ToolSpec(BaseModel):
    """
    Specification for a tool to be used.
    
    Describes which tool to invoke and with what parameters.
    """
    tool_id: str = Field(
        ...,
        description="Identifier of the tool to use"
    )
    
    tool_safety: ToolSafety = Field(
        ...,
        description="Safety classification (READ, WRITE, MIXED)"
    )
    
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters to pass to the tool"
    )
    
    timeout_seconds: int | None = Field(
        default=None,
        ge=1,
        description="Optional timeout for this specific tool call"
    )


class DirectiveConstraints(BaseModel):
    """
    Constraints on directive execution.
    
    Bounds what Layer 6 is allowed to do while executing.
    """
    max_tool_calls: int = Field(
        ...,
        ge=0,
        description="Maximum number of tool calls allowed"
    )
    
    max_time_seconds: int = Field(
        ...,
        ge=1,
        description="Maximum execution time"
    )
    
    allowed_tool_ids: list[str] | None = Field(
        default=None,
        description="Whitelist of allowed tools (None = all allowed per safety)"
    )
    
    forbidden_tool_ids: list[str] | None = Field(
        default=None,
        description="Blacklist of forbidden tools"
    )
    
    require_authorization_token: bool = Field(
        default=False,
        description="Whether a ToolAuthorizationToken is required"
    )
    
    authorization_token_id: UUID | None = Field(
        default=None,
        description="ID of the authorization token if required"
    )


class TaskDirectivePayload(BaseModel):
    """
    Payload for TaskDirectivePacket.
    
    Specifies what Layer 6 should do and under what constraints.
    
    Spec: OMEN.md §9.3 "TaskDirectivePacket", §8.3.2
    """
    directive_id: str = Field(
        ...,
        description="Unique identifier for this directive"
    )
    
    task_class: TaskClass = Field(
        ...,
        description="Semantic type of task (FIND, LOOKUP, SEARCH, CREATE, VERIFY, COMPILE)"
    )
    
    task_description: str = Field(
        ...,
        description="Human-readable description of what to do"
    )
    
    instructions: str = Field(
        ...,
        description="Detailed instructions for execution"
    )
    
    tools: list[ToolSpec] = Field(
        default_factory=list,
        description="Tools to use for this directive"
    )
    
    constraints: DirectiveConstraints = Field(
        ...,
        description="Execution constraints"
    )
    
    expected_output_type: str | None = Field(
        default=None,
        description="What kind of output is expected"
    )
    
    success_criteria: str = Field(
        ...,
        description="How to determine if the task succeeded"
    )
    
    on_success: str = Field(
        default="return_result",
        description="What to do on success"
    )
    
    on_failure: str = Field(
        default="return_error",
        description="What to do on failure"
    )
    
    parent_verification_target_id: str | None = Field(
        default=None,
        description="If this directive is part of a verification plan, which target"
    )
    
    @field_validator("tools")
    @classmethod
    def validate_write_tools_need_auth(cls, v: list[ToolSpec], info) -> list[ToolSpec]:
        """WRITE/MIXED tools should have authorization context."""
        # Note: Full validation with constraints happens at packet level
        return v


class TaskDirectivePacket(BaseModel):
    """
    Complete TaskDirectivePacket.
    
    Commands Layer 6 to execute a specific task.
    Must eventually be closed by a TaskResultPacket.
    
    Spec: OMEN.md §9.3, §10.4
    """
    header: PacketHeader = Field(
        ...,
        description="Packet identification and routing"
    )
    
    mcp: MCP = Field(
        ...,
        description="Mandatory Compliance Payload"
    )
    
    payload: TaskDirectivePayload = Field(
        ...,
        description="Directive content"
    )
    
    def __init__(self, **data):
        # Ensure packet_type is correct
        if "header" in data and isinstance(data["header"], dict):
            data["header"]["packet_type"] = PacketType.TASK_DIRECTIVE.value
        super().__init__(**data)
    
    @field_validator("payload")
    @classmethod
    def validate_write_authorization(cls, v: TaskDirectivePayload) -> TaskDirectivePayload:
        """WRITE/MIXED tools require authorization token."""
        has_write_tools = any(
            t.tool_safety in (ToolSafety.WRITE, ToolSafety.MIXED) 
            for t in v.tools
        )
        if has_write_tools and v.constraints.require_authorization_token:
            if not v.constraints.authorization_token_id:
                raise ValueError(
                    "WRITE/MIXED tools with require_authorization_token=True "
                    "must have authorization_token_id"
                )
        return v
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "header": {
                        "packet_type": "TaskDirectivePacket",
                        "created_at": "2025-12-21T11:33:00Z",
                        "layer_source": "5",
                        "correlation_id": "77a88b99-c0d1-e2f3-4567-890abcdef012"
                    },
                    "mcp": {
                        "intent": {"summary": "Query threat level", "scope": "verification"},
                        "stakes": {
                            "impact": "LOW",
                            "irreversibility": "REVERSIBLE",
                            "uncertainty": "MEDIUM",
                            "adversariality": "BENIGN",
                            "stakes_level": "LOW"
                        },
                        "quality": {
                            "quality_tier": "PAR",
                            "satisficing_mode": True,
                            "definition_of_done": {"text": "Threat data retrieved", "checks": []},
                            "verification_requirement": "OPTIONAL"
                        },
                        "budgets": {
                            "token_budget": 100,
                            "tool_call_budget": 1,
                            "time_budget_seconds": 30,
                            "risk_budget": {"envelope": "minimal", "max_loss": 0}
                        },
                        "epistemics": {
                            "status": "DERIVED",
                            "confidence": 0.9,
                            "calibration_note": "Directive from verification plan",
                            "freshness_class": "REALTIME",
                            "stale_if_older_than_seconds": 60,
                            "assumptions": []
                        },
                        "evidence": {
                            "evidence_refs": [],
                            "evidence_absent_reason": "Directive precedes execution"
                        },
                        "routing": {"task_class": "LOOKUP", "tools_state": "tools_ok"}
                    },
                    "payload": {
                        "directive_id": "dir_threat_001",
                        "task_class": "LOOKUP",
                        "task_description": "Query current threat level for target system",
                        "instructions": "Call intel API with system_id parameter",
                        "tools": [
                            {
                                "tool_id": "intel_threat_api",
                                "tool_safety": "READ",
                                "parameters": {"system_id": 30000142},
                                "timeout_seconds": 10
                            }
                        ],
                        "constraints": {
                            "max_tool_calls": 1,
                            "max_time_seconds": 30,
                            "require_authorization_token": False
                        },
                        "expected_output_type": "threat_assessment",
                        "success_criteria": "Valid threat level returned",
                        "on_success": "return_result",
                        "on_failure": "return_error",
                        "parent_verification_target_id": "verify_threat_level"
                    }
                }
            ]
        }
    }
