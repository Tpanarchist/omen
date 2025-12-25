"""
VerificationPlanPacket — Verification strategies before action.

When a decision is VERIFY_FIRST, a verification plan specifies
exactly what to verify and how. This enables structured verification loops.

Spec: OMEN.md §9.3, §15.3, §8.2.3
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from omen.vocabulary import PacketType, TaskClass, ToolSafety
from omen.schemas.header import PacketHeader
from omen.schemas.mcp import MCP


class VerificationTarget(BaseModel):
    """
    A specific item to verify.
    
    Each target represents one thing we need to check/confirm
    before proceeding with action.
    """
    target_id: str = Field(
        ...,
        description="Unique identifier for this verification target"
    )
    
    description: str = Field(
        ...,
        description="What we're trying to verify"
    )
    
    assumption_text: str = Field(
        ...,
        description="The assumption being tested"
    )
    
    is_load_bearing: bool = Field(
        default=True,
        description="If false, would this flip the decision?"
    )
    
    verification_method: str = Field(
        ...,
        description="How to verify (e.g., 'tool_query', 'user_confirm', 'calculation')"
    )
    
    tool_id: str | None = Field(
        default=None,
        description="Specific tool to use for verification"
    )
    
    tool_safety: ToolSafety | None = Field(
        default=None,
        description="Safety classification of the verification tool"
    )
    
    expected_evidence_type: str | None = Field(
        default=None,
        description="What kind of evidence we expect to receive"
    )
    
    success_criteria: str = Field(
        ...,
        description="How we know verification succeeded"
    )
    
    failure_action: str = Field(
        default="escalate",
        description="What to do if verification fails (escalate, defer, retry, abort)"
    )


class VerificationPlanPayload(BaseModel):
    """
    Payload for VerificationPlanPacket.
    
    Specifies what to verify, in what order, and constraints.
    
    Spec: OMEN.md §9.3 "VerificationPlanPacket", §15.3
    """
    plan_id: str = Field(
        ...,
        description="Unique identifier for this verification plan"
    )
    
    triggering_decision_id: UUID = Field(
        ...,
        description="The DecisionPacket that triggered this verification"
    )
    
    plan_summary: str = Field(
        ...,
        description="Human-readable summary of the verification plan"
    )
    
    targets: list[VerificationTarget] = Field(
        ...,
        min_length=1,
        description="List of verification targets (at least one required)"
    )
    
    execution_order: list[str] | None = Field(
        default=None,
        description="Order to execute verifications (target_ids). None = any order."
    )
    
    parallel_allowed: bool = Field(
        default=False,
        description="Whether verifications can run in parallel"
    )
    
    max_verification_time_seconds: int = Field(
        ...,
        ge=1,
        description="Time budget for entire verification plan"
    )
    
    max_tool_calls: int = Field(
        ...,
        ge=1,
        description="Maximum tool calls for verification"
    )
    
    on_all_success: str = Field(
        default="proceed_to_act",
        description="What to do when all verifications pass"
    )
    
    on_any_failure: str = Field(
        default="escalate",
        description="Default action when any verification fails"
    )
    
    partial_success_acceptable: bool = Field(
        default=False,
        description="Whether we can proceed with partial verification"
    )


class VerificationPlanPacket(BaseModel):
    """
    Complete VerificationPlanPacket.
    
    Specifies how to verify assumptions before acting.
    Follows a VERIFY_FIRST decision.
    
    Spec: OMEN.md §9.3, §15.3
    """
    header: PacketHeader = Field(
        ...,
        description="Packet identification and routing"
    )
    
    mcp: MCP = Field(
        ...,
        description="Mandatory Compliance Payload"
    )
    
    payload: VerificationPlanPayload = Field(
        ...,
        description="Verification plan content"
    )
    
    def __init__(self, **data):
        # Ensure packet_type is correct
        if "header" in data and isinstance(data["header"], dict):
            data["header"]["packet_type"] = PacketType.VERIFICATION_PLAN.value
        super().__init__(**data)
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "header": {
                        "packet_type": "VerificationPlanPacket",
                        "created_at": "2025-12-21T11:32:30Z",
                        "layer_source": "5",
                        "correlation_id": "77a88b99-c0d1-e2f3-4567-890abcdef012",
                        "previous_packet_id": "decision-packet-uuid"
                    },
                    "mcp": {
                        "intent": {"summary": "Verify threat level before action", "scope": "verification"},
                        "stakes": {
                            "impact": "MEDIUM",
                            "irreversibility": "REVERSIBLE",
                            "uncertainty": "HIGH",
                            "adversariality": "CONTESTED",
                            "stakes_level": "MEDIUM"
                        },
                        "quality": {
                            "quality_tier": "PAR",
                            "satisficing_mode": True,
                            "definition_of_done": {"text": "Threat level confirmed", "checks": ["tool response received", "belief updated"]},
                            "verification_requirement": "VERIFY_ONE"
                        },
                        "budgets": {
                            "token_budget": 500,
                            "tool_call_budget": 1,
                            "time_budget_seconds": 60,
                            "risk_budget": {"envelope": "minimal", "max_loss": 0}
                        },
                        "epistemics": {
                            "status": "DERIVED",
                            "confidence": 0.8,
                            "calibration_note": "Plan derived from decision requirements",
                            "freshness_class": "REALTIME",
                            "stale_if_older_than_seconds": 300,
                            "assumptions": []
                        },
                        "evidence": {
                            "evidence_refs": [],
                            "evidence_absent_reason": "Plan created before verification executed"
                        },
                        "routing": {"task_class": "VERIFY", "tools_state": "tools_ok"}
                    },
                    "payload": {
                        "plan_id": "vplan_threat_check_001",
                        "triggering_decision_id": "77a88b99-c0d1-e2f3-4567-890abcdef012",
                        "plan_summary": "Query intel tool for current threat level in target system",
                        "targets": [
                            {
                                "target_id": "verify_threat_level",
                                "description": "Check current threat level via intel endpoint",
                                "assumption_text": "Local threat level is low enough to proceed",
                                "is_load_bearing": True,
                                "verification_method": "tool_query",
                                "tool_id": "intel_threat_api",
                                "tool_safety": "READ",
                                "expected_evidence_type": "threat_assessment",
                                "success_criteria": "Threat level <= MEDIUM",
                                "failure_action": "escalate"
                            }
                        ],
                        "execution_order": ["verify_threat_level"],
                        "parallel_allowed": False,
                        "max_verification_time_seconds": 60,
                        "max_tool_calls": 1,
                        "on_all_success": "proceed_to_act",
                        "on_any_failure": "escalate",
                        "partial_success_acceptable": False
                    }
                }
            ]
        }
    }
