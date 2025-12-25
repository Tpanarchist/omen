"""
TaskResultPacket — Execution outcomes from Layer 6 to Layer 5.

Results flow northbound, reporting the outcome of directive execution.
Every TaskDirectivePacket must eventually be closed by a TaskResultPacket.

Spec: OMEN.md §9.3, §7.1, §10.4
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from omen.vocabulary import PacketType, TaskResultStatus
from omen.schemas.header import PacketHeader
from omen.schemas.mcp import MCP


class ToolCallRecord(BaseModel):
    """
    Record of a tool call made during execution.
    
    Provides detailed audit trail of what was invoked.
    """
    tool_id: str = Field(
        ...,
        description="Which tool was called"
    )
    
    call_timestamp: datetime = Field(
        ...,
        description="When the call was made"
    )
    
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters passed to the tool"
    )
    
    duration_ms: int | None = Field(
        default=None,
        ge=0,
        description="How long the call took in milliseconds"
    )
    
    success: bool = Field(
        ...,
        description="Whether the tool call succeeded"
    )
    
    error_message: str | None = Field(
        default=None,
        description="Error message if call failed"
    )
    
    output_ref: str | None = Field(
        default=None,
        description="Reference to the tool output (if stored separately)"
    )


class ResourceUsage(BaseModel):
    """
    Resources consumed during execution.
    
    Enables budget tracking and optimization.
    """
    tool_calls_made: int = Field(
        ...,
        ge=0,
        description="Number of tool calls executed"
    )
    
    time_elapsed_seconds: float = Field(
        ...,
        ge=0,
        description="Wall clock time for execution"
    )
    
    tokens_consumed: int | None = Field(
        default=None,
        ge=0,
        description="Tokens used (if applicable)"
    )


class TaskResultPayload(BaseModel):
    """
    Payload for TaskResultPacket.
    
    Reports the outcome of a directive's execution.
    
    Spec: OMEN.md §9.3 "TaskResultPacket", §10.4
    """
    result_id: str = Field(
        ...,
        description="Unique identifier for this result"
    )
    
    directive_id: str = Field(
        ...,
        description="ID of the directive this result closes"
    )
    
    status: TaskResultStatus = Field(
        ...,
        description="Outcome status (SUCCESS, FAILURE, CANCELLED)"
    )
    
    status_reason: str = Field(
        ...,
        description="Human-readable explanation of the status"
    )
    
    output: dict[str, Any] | None = Field(
        default=None,
        description="The result data (if successful)"
    )
    
    output_type: str | None = Field(
        default=None,
        description="Type of the output data"
    )
    
    error_code: str | None = Field(
        default=None,
        description="Error code (if failed)"
    )
    
    error_details: str | None = Field(
        default=None,
        description="Detailed error information (if failed)"
    )
    
    tool_calls: list[ToolCallRecord] = Field(
        default_factory=list,
        description="Audit trail of tool calls made"
    )
    
    resource_usage: ResourceUsage = Field(
        ...,
        description="Resources consumed during execution"
    )
    
    observations_generated: list[UUID] = Field(
        default_factory=list,
        description="IDs of ObservationPackets generated during execution"
    )
    
    execution_started_at: datetime = Field(
        ...,
        description="When execution began"
    )
    
    execution_completed_at: datetime = Field(
        ...,
        description="When execution finished"
    )
    
    @field_validator("error_details")
    @classmethod
    def validate_failure_has_error(cls, v, info):
        """FAILURE status should have error details."""
        # Cross-field validation at packet level
        return v


class TaskResultPacket(BaseModel):
    """
    Complete TaskResultPacket.
    
    Reports the outcome of directive execution.
    Closes a TaskDirectivePacket per §10.4.
    
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
    
    payload: TaskResultPayload = Field(
        ...,
        description="Result content"
    )
    
    def __init__(self, **data):
        # Ensure packet_type is correct
        if "header" in data and isinstance(data["header"], dict):
            data["header"]["packet_type"] = PacketType.TASK_RESULT.value
        super().__init__(**data)
    
    @field_validator("payload")
    @classmethod
    def validate_status_consistency(cls, v: TaskResultPayload) -> TaskResultPayload:
        """Validate status-specific fields."""
        if v.status == TaskResultStatus.FAILURE:
            if not v.error_code and not v.error_details:
                raise ValueError(
                    "FAILURE status should have error_code or error_details"
                )
        if v.status == TaskResultStatus.SUCCESS:
            # Success typically has output, but not required
            pass
        return v
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "header": {
                        "packet_type": "TaskResultPacket",
                        "created_at": "2025-12-21T11:33:15Z",
                        "layer_source": "6",
                        "correlation_id": "77a88b99-c0d1-e2f3-4567-890abcdef012",
                        "previous_packet_id": "directive-packet-uuid"
                    },
                    "mcp": {
                        "intent": {"summary": "Report threat query result", "scope": "verification"},
                        "stakes": {
                            "impact": "LOW",
                            "irreversibility": "REVERSIBLE",
                            "uncertainty": "LOW",
                            "adversariality": "BENIGN",
                            "stakes_level": "LOW"
                        },
                        "quality": {
                            "quality_tier": "PAR",
                            "satisficing_mode": True,
                            "definition_of_done": {"text": "Result reported", "checks": []},
                            "verification_requirement": "OPTIONAL"
                        },
                        "budgets": {
                            "token_budget": 50,
                            "tool_call_budget": 0,
                            "time_budget_seconds": 5,
                            "risk_budget": {"envelope": "minimal", "max_loss": 0}
                        },
                        "epistemics": {
                            "status": "OBSERVED",
                            "confidence": 0.99,
                            "calibration_note": "Direct tool output",
                            "freshness_class": "REALTIME",
                            "stale_if_older_than_seconds": 60,
                            "assumptions": []
                        },
                        "evidence": {
                            "evidence_refs": [{
                                "ref_type": "tool_output",
                                "ref_id": "intel_threat_resp_001",
                                "timestamp": "2025-12-21T11:33:10Z",
                                "reliability_score": 0.99
                            }],
                            "evidence_absent_reason": None
                        },
                        "routing": {"task_class": "LOOKUP", "tools_state": "tools_ok"}
                    },
                    "payload": {
                        "result_id": "res_threat_001",
                        "directive_id": "dir_threat_001",
                        "status": "SUCCESS",
                        "status_reason": "Threat level successfully retrieved",
                        "output": {"threat_level": "LOW", "last_hostile_activity": None},
                        "output_type": "threat_assessment",
                        "tool_calls": [
                            {
                                "tool_id": "intel_threat_api",
                                "call_timestamp": "2025-12-21T11:33:05Z",
                                "parameters": {"system_id": 30000142},
                                "duration_ms": 450,
                                "success": True,
                                "output_ref": "intel_threat_resp_001"
                            }
                        ],
                        "resource_usage": {
                            "tool_calls_made": 1,
                            "time_elapsed_seconds": 0.5,
                            "tokens_consumed": 25
                        },
                        "observations_generated": [],
                        "execution_started_at": "2025-12-21T11:33:00Z",
                        "execution_completed_at": "2025-12-21T11:33:15Z"
                    }
                }
            ]
        }
    }
