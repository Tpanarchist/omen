"""
BeliefUpdatePacket — World model updates.

Belief updates propagate changes to the agent's understanding of reality.
They track what changed, why, and whether contradictions were detected.

Spec: OMEN.md §9.3, §8.1
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from omen.vocabulary import PacketType, EpistemicStatus
from omen.schemas.header import PacketHeader
from omen.schemas.mcp import MCP


class BeliefState(BaseModel):
    """
    Represents a belief state (prior or new).
    
    Captures what is believed and with what epistemic status.
    """
    claim: str = Field(
        ...,
        description="The propositional content of the belief"
    )
    
    status: EpistemicStatus = Field(
        ...,
        description="Epistemic classification of this belief"
    )
    
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence in this belief (0-1)"
    )
    
    supporting_evidence: list[str] = Field(
        default_factory=list,
        description="Reference IDs to evidence supporting this belief"
    )
    
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Additional structured data about the belief"
    )


class ContradictionRef(BaseModel):
    """
    Reference to a detected contradiction.
    
    Spec: OMEN.md §8.1 "Contradictions & belief updates"
    """
    contradicting_belief_id: str = Field(
        ...,
        description="ID of the belief that contradicts"
    )
    
    contradiction_type: str = Field(
        ...,
        description="Type of contradiction (e.g., 'direct', 'temporal', 'logical')"
    )
    
    description: str = Field(
        ...,
        description="Human-readable description of the contradiction"
    )


class BeliefUpdatePayload(BaseModel):
    """
    Payload for BeliefUpdatePacket.
    
    Tracks the transition from prior belief to new belief,
    including the reason for update and any contradictions.
    
    Spec: OMEN.md §9.3 "BeliefUpdatePacket", §8.1
    """
    belief_id: str = Field(
        ...,
        description="Unique identifier for this belief (stable across updates)"
    )
    
    belief_domain: str = Field(
        ...,
        description="Domain/category of belief (e.g., 'character_state', 'market', 'threat')"
    )
    
    prior_state: BeliefState | None = Field(
        default=None,
        description="Previous belief state (None if new belief)"
    )
    
    new_state: BeliefState = Field(
        ...,
        description="Updated belief state"
    )
    
    update_reason: str = Field(
        ...,
        description="Why this belief was updated"
    )
    
    triggering_observation_id: UUID | None = Field(
        default=None,
        description="Packet ID of observation that triggered this update"
    )
    
    contradiction_detected: bool = Field(
        default=False,
        description="Whether this update detected contradictions"
    )
    
    contradiction_refs: list[ContradictionRef] = Field(
        default_factory=list,
        description="Details of any detected contradictions"
    )
    
    @field_validator("contradiction_refs")
    @classmethod
    def validate_contradiction_consistency(cls, v, info):
        """If contradiction_detected is True, should have refs (warning, not error)."""
        # This is informational - we don't enforce because contradictions
        # might be detected without specific refs in some cases
        return v


class BeliefUpdatePacket(BaseModel):
    """
    Complete BeliefUpdatePacket.
    
    Propagates world model updates through the cognitive layers.
    Tracks belief transitions and contradiction detection.
    
    Spec: OMEN.md §9.3
    """
    header: PacketHeader = Field(
        ...,
        description="Packet identification and routing"
    )
    
    mcp: MCP = Field(
        ...,
        description="Mandatory Compliance Payload"
    )
    
    payload: BeliefUpdatePayload = Field(
        ...,
        description="Belief update content"
    )
    
    def __init__(self, **data):
        # Ensure packet_type is correct
        if "header" in data and isinstance(data["header"], dict):
            data["header"]["packet_type"] = PacketType.BELIEF_UPDATE.value
        super().__init__(**data)
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "header": {
                        "packet_type": "BeliefUpdatePacket",
                        "created_at": "2025-12-21T11:31:00Z",
                        "layer_source": "2",
                        "correlation_id": "77a88b99-c0d1-e2f3-4567-890abcdef012",
                        "previous_packet_id": "obs-packet-uuid-here"
                    },
                    "mcp": {
                        "intent": {"summary": "Update character location belief", "scope": "world_model"},
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
                            "definition_of_done": {"text": "Belief updated", "checks": []},
                            "verification_requirement": "OPTIONAL"
                        },
                        "budgets": {
                            "token_budget": 50,
                            "tool_call_budget": 0,
                            "time_budget_seconds": 2,
                            "risk_budget": {"envelope": "minimal", "max_loss": 0}
                        },
                        "epistemics": {
                            "status": "DERIVED",
                            "confidence": 0.95,
                            "calibration_note": "Derived from fresh observation",
                            "freshness_class": "REALTIME",
                            "stale_if_older_than_seconds": 60,
                            "assumptions": []
                        },
                        "evidence": {
                            "evidence_refs": [{
                                "ref_type": "tool_output",
                                "ref_id": "esi_location_12345",
                                "timestamp": "2025-12-21T11:30:00Z",
                                "reliability_score": 0.99
                            }],
                            "evidence_absent_reason": None
                        },
                        "routing": {"task_class": "CREATE", "tools_state": "tools_ok"}
                    },
                    "payload": {
                        "belief_id": "character_location_12345",
                        "belief_domain": "character_state",
                        "prior_state": {
                            "claim": "Character is in Jita",
                            "status": "OBSERVED",
                            "confidence": 0.99,
                            "supporting_evidence": ["esi_location_old"],
                            "metadata": {"solar_system_id": 30000142}
                        },
                        "new_state": {
                            "claim": "Character is in Amarr",
                            "status": "OBSERVED",
                            "confidence": 0.99,
                            "supporting_evidence": ["esi_location_12345"],
                            "metadata": {"solar_system_id": 30002187}
                        },
                        "update_reason": "New observation from ESI location endpoint",
                        "triggering_observation_id": "obs-packet-uuid-here",
                        "contradiction_detected": False,
                        "contradiction_refs": []
                    }
                }
            ]
        }
    }
