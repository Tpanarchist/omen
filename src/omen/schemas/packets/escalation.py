"""
EscalationPacket — Human escalation when autonomy limits are reached.

Escalations occur when the system cannot or should not proceed autonomously.
They present the human with options, evidence gaps, and recommendations.

Spec: OMEN.md §9.3, §8.2.6, §3.2
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from omen.vocabulary import PacketType, StakesLevel, UncertaintyLevel
from omen.schemas.header import PacketHeader
from omen.schemas.mcp import MCP


class EscalationOption(BaseModel):
    """
    A possible action the human can authorize.
    
    Escalations present 2-3 options with tradeoffs explained.
    """
    option_id: str = Field(
        ...,
        description="Unique identifier for this option"
    )
    
    summary: str = Field(
        ...,
        description="Brief description of the option"
    )
    
    action_description: str = Field(
        ...,
        description="What would happen if this option is chosen"
    )
    
    risks: list[str] = Field(
        default_factory=list,
        description="Risks associated with this option"
    )
    
    benefits: list[str] = Field(
        default_factory=list,
        description="Benefits of this option"
    )
    
    resource_cost: dict[str, Any] | None = Field(
        default=None,
        description="Estimated resource cost (time, ISK, etc.)"
    )
    
    recommended: bool = Field(
        default=False,
        description="Whether this is the recommended option"
    )
    
    recommendation_rationale: str | None = Field(
        default=None,
        description="Why this option is recommended (if recommended=True)"
    )


class EvidenceGap(BaseModel):
    """
    Information that is missing or uncertain.
    
    Helps the human understand what the system doesn't know.
    """
    gap_id: str = Field(
        ...,
        description="Identifier for this gap"
    )
    
    description: str = Field(
        ...,
        description="What information is missing"
    )
    
    impact: str = Field(
        ...,
        description="How this gap affects decision-making"
    )
    
    could_verify: bool = Field(
        default=False,
        description="Whether verification could fill this gap"
    )
    
    verification_method: str | None = Field(
        default=None,
        description="How to verify (if could_verify=True)"
    )
    
    verification_cost: str | None = Field(
        default=None,
        description="Estimated cost to verify"
    )


class EscalationPayload(BaseModel):
    """
    Payload for EscalationPacket.
    
    Presents the human with context, options, and gaps.
    
    Spec: OMEN.md §9.3 "EscalationPacket", §8.2.6
    """
    escalation_id: str = Field(
        ...,
        description="Unique identifier for this escalation"
    )
    
    escalation_trigger: str = Field(
        ...,
        description="What triggered the escalation (e.g., 'high_stakes_high_uncertainty')"
    )
    
    situation_summary: str = Field(
        ...,
        description="Human-readable summary of the current situation"
    )
    
    stakes_level: StakesLevel = Field(
        ...,
        description="Current stakes level"
    )
    
    uncertainty_level: UncertaintyLevel = Field(
        ...,
        description="Current uncertainty level"
    )
    
    what_we_know: list[str] = Field(
        default_factory=list,
        description="Key facts and verified beliefs"
    )
    
    what_we_believe: list[str] = Field(
        default_factory=list,
        description="Inferred or hypothesized beliefs"
    )
    
    options: list[EscalationOption] = Field(
        ...,
        min_length=1,
        description="Options for the human to choose from"
    )
    
    evidence_gaps: list[EvidenceGap] = Field(
        default_factory=list,
        description="Information gaps affecting the decision"
    )
    
    recommended_next_step: str | None = Field(
        default=None,
        description="System's recommended next verification or action"
    )
    
    time_sensitivity: str | None = Field(
        default=None,
        description="How time-sensitive is this decision"
    )
    
    triggering_episode_id: UUID | None = Field(
        default=None,
        description="Episode that triggered this escalation"
    )
    
    triggering_decision_id: UUID | None = Field(
        default=None,
        description="Decision that triggered this escalation"
    )
    
    @field_validator("options")
    @classmethod
    def validate_has_options(cls, v: list[EscalationOption]) -> list[EscalationOption]:
        """Escalation must present at least one option."""
        if not v:
            raise ValueError("Escalation must have at least one option")
        return v


class EscalationPacket(BaseModel):
    """
    Complete EscalationPacket.
    
    Presents human with escalation context and options.
    Used when autonomy limits are reached.
    
    Spec: OMEN.md §9.3, §8.2.6
    """
    header: PacketHeader = Field(
        ...,
        description="Packet identification and routing"
    )
    
    mcp: MCP = Field(
        ...,
        description="Mandatory Compliance Payload"
    )
    
    payload: EscalationPayload = Field(
        ...,
        description="Escalation content"
    )
    
    def __init__(self, **data):
        # Ensure packet_type is correct
        if "header" in data and isinstance(data["header"], dict):
            data["header"]["packet_type"] = PacketType.ESCALATION.value
        super().__init__(**data)
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "header": {
                        "packet_type": "EscalationPacket",
                        "created_at": "2025-12-21T11:35:00Z",
                        "layer_source": "5",
                        "correlation_id": "77a88b99-c0d1-e2f3-4567-890abcdef012"
                    },
                    "mcp": {
                        "intent": {"summary": "Escalate high-stakes decision", "scope": "escalation"},
                        "stakes": {
                            "impact": "HIGH",
                            "irreversibility": "IRREVERSIBLE",
                            "uncertainty": "HIGH",
                            "adversariality": "HOSTILE",
                            "stakes_level": "HIGH"
                        },
                        "quality": {
                            "quality_tier": "SUPERB",
                            "satisficing_mode": False,
                            "definition_of_done": {"text": "Human decision received", "checks": []},
                            "verification_requirement": "VERIFY_ALL"
                        },
                        "budgets": {
                            "token_budget": 200,
                            "tool_call_budget": 0,
                            "time_budget_seconds": 300,
                            "risk_budget": {"envelope": "minimal", "max_loss": 0}
                        },
                        "epistemics": {
                            "status": "DERIVED",
                            "confidence": 0.6,
                            "calibration_note": "High uncertainty requires human judgment",
                            "freshness_class": "OPERATIONAL",
                            "stale_if_older_than_seconds": 600,
                            "assumptions": []
                        },
                        "evidence": {
                            "evidence_refs": [],
                            "evidence_absent_reason": "Evidence gaps identified"
                        },
                        "routing": {"task_class": "CREATE", "tools_state": "tools_ok"}
                    },
                    "payload": {
                        "escalation_id": "esc_001",
                        "escalation_trigger": "high_stakes_high_uncertainty",
                        "situation_summary": "Hostile fleet detected in target system. Trade route may be compromised.",
                        "stakes_level": "HIGH",
                        "uncertainty_level": "HIGH",
                        "what_we_know": [
                            "10 hostile ships detected on d-scan",
                            "Our cargo value: 500M ISK"
                        ],
                        "what_we_believe": [
                            "Fleet appears to be camping the gate",
                            "Alternative routes exist but are longer"
                        ],
                        "options": [
                            {
                                "option_id": "wait",
                                "summary": "Wait for situation to clear",
                                "action_description": "Dock and wait 30 minutes",
                                "risks": ["Time loss", "Market opportunity may expire"],
                                "benefits": ["No cargo risk"],
                                "recommended": True,
                                "recommendation_rationale": "Preserves assets, opportunity cost is lower than cargo value"
                            },
                            {
                                "option_id": "reroute",
                                "summary": "Take alternative route",
                                "action_description": "Route through lowsec, adds 15 jumps",
                                "risks": ["Lowsec exposure", "Longer travel time"],
                                "benefits": ["Avoids known hostiles"]
                            },
                            {
                                "option_id": "proceed",
                                "summary": "Proceed through gate",
                                "action_description": "Attempt to run the camp",
                                "risks": ["High probability of loss"],
                                "benefits": ["Fastest if successful"]
                            }
                        ],
                        "evidence_gaps": [
                            {
                                "gap_id": "fleet_comp",
                                "description": "Unknown fleet composition and capabilities",
                                "impact": "Cannot assess survival probability",
                                "could_verify": True,
                                "verification_method": "Scout with alt character",
                                "verification_cost": "5 minutes"
                            }
                        ],
                        "recommended_next_step": "Scout the gate with an alt before deciding",
                        "time_sensitivity": "Moderate - market window closes in 2 hours"
                    }
                }
            ]
        }
    }
