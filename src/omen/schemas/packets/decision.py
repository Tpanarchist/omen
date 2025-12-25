"""
DecisionPacket — Action decisions from cognitive processing.

Decisions represent the output of the deliberation process.
Layer 5 (Cognitive Control) produces decisions after arbitration.

Spec: OMEN.md §9.3, §15.2, §4.3
"""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from omen.vocabulary import PacketType, DecisionOutcome
from omen.schemas.header import PacketHeader
from omen.schemas.mcp import MCP


class RejectedAlternative(BaseModel):
    """
    A considered but rejected option.
    
    Tracking rejected alternatives supports auditability
    and helps explain why the chosen path was preferred.
    """
    option_id: str = Field(
        ...,
        description="Identifier for this alternative"
    )
    
    summary: str = Field(
        ...,
        description="Brief description of the alternative"
    )
    
    rejection_reason: str = Field(
        ...,
        description="Why this option was not chosen"
    )
    
    stage_rejected: str | None = Field(
        default=None,
        description="Arbitration stage where rejected (e.g., 'constitutional_veto', 'budget_feasibility', 'tradeoff')"
    )


class DecisionPayload(BaseModel):
    """
    Payload for DecisionPacket.
    
    Contains the decision outcome and supporting rationale.
    
    Spec: OMEN.md §9.3 "DecisionPacket", §15.2
    """
    decision_outcome: DecisionOutcome = Field(
        ...,
        description="The decision result: ACT, VERIFY_FIRST, ESCALATE, or DEFER"
    )
    
    decision_summary: str = Field(
        ...,
        description="Human-readable summary of the decision"
    )
    
    chosen_option_id: str | None = Field(
        default=None,
        description="Identifier of the chosen option (if ACT)"
    )
    
    rationale: str = Field(
        ...,
        description="Explanation of why this decision was made"
    )
    
    assumptions: list[str] = Field(
        default_factory=list,
        description="Assumptions underlying this decision"
    )
    
    load_bearing_assumptions: list[str] = Field(
        default_factory=list,
        description="Assumptions that if false would flip the decision"
    )
    
    rejected_alternatives: list[RejectedAlternative] = Field(
        default_factory=list,
        description="Options considered but not chosen"
    )
    
    required_verifications: list[str] | None = Field(
        default=None,
        description="What must be verified (if VERIFY_FIRST)"
    )
    
    escalation_reason: str | None = Field(
        default=None,
        description="Why escalating (if ESCALATE)"
    )
    
    defer_until: str | None = Field(
        default=None,
        description="Condition or time to revisit (if DEFER)"
    )
    
    @field_validator("required_verifications")
    @classmethod
    def validate_verify_first_has_requirements(cls, v, info):
        """VERIFY_FIRST should specify what to verify."""
        # Note: Cross-field validation - we check in DecisionPacket
        return v


class DecisionPacket(BaseModel):
    """
    Complete DecisionPacket.
    
    Represents the output of deliberation/arbitration.
    Layer 5 produces these after processing beliefs and constraints.
    
    Spec: OMEN.md §9.3, §15.2
    """
    header: PacketHeader = Field(
        ...,
        description="Packet identification and routing"
    )
    
    mcp: MCP = Field(
        ...,
        description="Mandatory Compliance Payload"
    )
    
    payload: DecisionPayload = Field(
        ...,
        description="Decision content"
    )
    
    def __init__(self, **data):
        # Ensure packet_type is correct
        if "header" in data and isinstance(data["header"], dict):
            data["header"]["packet_type"] = PacketType.DECISION.value
        super().__init__(**data)
    
    @field_validator("payload")
    @classmethod
    def validate_outcome_consistency(cls, v: DecisionPayload) -> DecisionPayload:
        """Validate outcome-specific fields are present."""
        if v.decision_outcome == DecisionOutcome.VERIFY_FIRST:
            if not v.required_verifications:
                raise ValueError(
                    "VERIFY_FIRST decision must specify required_verifications"
                )
        if v.decision_outcome == DecisionOutcome.ESCALATE:
            if not v.escalation_reason:
                raise ValueError(
                    "ESCALATE decision must specify escalation_reason"
                )
        return v
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "header": {
                        "packet_type": "DecisionPacket",
                        "created_at": "2025-12-21T11:32:00-05:00",
                        "layer_source": "5",
                        "correlation_id": "77a88b99-c0d1-e2f3-4567-890abcdef012",
                        "campaign_id": "deadbeef-cafe-babe-1234-567890abcdef"
                    },
                    "mcp": {
                        "intent": {"summary": "Decide whether to verify intel before acting", "scope": "intel_update"},
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
                            "definition_of_done": {"text": "Have at least one fresh observation for the key unknown", "checks": ["fresh evidence collected"]},
                            "verification_requirement": "VERIFY_ONE"
                        },
                        "budgets": {
                            "token_budget": 900,
                            "tool_call_budget": 2,
                            "time_budget_seconds": 90,
                            "risk_budget": {"envelope": "low", "max_loss": "small"}
                        },
                        "epistemics": {
                            "status": "HYPOTHESIZED",
                            "confidence": 0.45,
                            "calibration_note": "Uncertainty high; no fresh observation yet",
                            "freshness_class": "OPERATIONAL",
                            "stale_if_older_than_seconds": 1800,
                            "assumptions": ["Local threat level is low enough to proceed"]
                        },
                        "evidence": {
                            "evidence_refs": [],
                            "evidence_absent_reason": "No tool read executed yet in this episode"
                        },
                        "routing": {"task_class": "VERIFY", "tools_state": "tools_ok"}
                    },
                    "payload": {
                        "decision_outcome": "VERIFY_FIRST",
                        "decision_summary": "Verify the load-bearing assumption with one tool read before any action.",
                        "rationale": "Uncertainty is high and we have tool access. Cost of verification is low.",
                        "assumptions": ["Tools are available", "Time budget allows verification"],
                        "load_bearing_assumptions": ["Local threat level is low enough to proceed"],
                        "rejected_alternatives": [
                            {
                                "option_id": "act_immediately",
                                "summary": "Proceed without verification",
                                "rejection_reason": "Uncertainty too high for stakes",
                                "stage_rejected": "tradeoff"
                            }
                        ],
                        "required_verifications": ["Confirm current threat level via intel tool"]
                    }
                }
            ]
        }
    }
