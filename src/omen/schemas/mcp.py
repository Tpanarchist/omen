"""
MCP Envelope — Mandatory Compliance Payload.

The structural "mind over matter" gate that every consequential packet carries.
Enforces policy compliance through required fields.

Spec: OMEN.md §9.2
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from omen.vocabulary import (
    EpistemicStatus,
    FreshnessClass,
    EvidenceRefType,
    ImpactLevel,
    Irreversibility,
    UncertaintyLevel,
    Adversariality,
    StakesLevel,
    QualityTier,
    VerificationRequirement,
    TaskClass,
    ToolsState,
)


# =============================================================================
# ATOMIC STRUCTURES (Level 3 in ontology)
# =============================================================================

class Intent(BaseModel):
    """
    What we're trying to accomplish.
    
    Spec: OMEN.md §9.2 "intent"
    """
    summary: str = Field(..., description="Brief description of intent")
    scope: str | dict[str, Any] = Field(..., description="Scope of the intent (string or structured)")


class Stakes(BaseModel):
    """
    Stakes classification across four axes.
    
    Spec: OMEN.md §8.2.1, §9.2 "stakes"
    """
    impact: ImpactLevel
    irreversibility: Irreversibility
    uncertainty: UncertaintyLevel
    adversariality: Adversariality
    stakes_level: StakesLevel


class DefinitionOfDone(BaseModel):
    """
    Success criteria for a task.
    
    Spec: OMEN.md §9.2 "definition_of_done"
    """
    text: str = Field(..., description="Human-readable definition of done")
    checks: list[str] = Field(default_factory=list, description="Specific checkable criteria")


class Quality(BaseModel):
    """
    Quality tier and verification requirements.
    
    Spec: OMEN.md §8.2.2, §8.2.3, §9.2 "quality"
    """
    quality_tier: QualityTier
    satisficing_mode: bool = Field(..., description="If true, good-enough is acceptable")
    definition_of_done: DefinitionOfDone
    verification_requirement: VerificationRequirement


class RiskBudget(BaseModel):
    """
    Risk exposure limits.
    
    Spec: OMEN.md §9.2 "risk_budget"
    """
    envelope: str = Field(..., description="Risk envelope identifier or description")
    max_loss: str | int | float = Field(..., description="Maximum acceptable loss")


class Budgets(BaseModel):
    """
    Resource budget constraints.
    
    Spec: OMEN.md §8.2.4, §9.2 "budgets"
    """
    token_budget: int = Field(..., ge=0, description="Maximum tokens to spend")
    tool_call_budget: int = Field(..., ge=0, description="Maximum tool calls allowed")
    time_budget_seconds: int = Field(..., ge=0, description="Maximum time in seconds")
    risk_budget: RiskBudget


class Epistemics(BaseModel):
    """
    Epistemic status and confidence of claims.
    
    Spec: OMEN.md §8.1, §9.2 "epistemics"
    """
    status: EpistemicStatus
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0-1")
    calibration_note: str = Field(..., description="Explanation of confidence assessment")
    freshness_class: FreshnessClass
    stale_if_older_than_seconds: int = Field(..., ge=0, description="Staleness threshold")
    assumptions: list[str] = Field(default_factory=list, description="Explicit assumptions")


class EvidenceRef(BaseModel):
    """
    Reference to evidence backing a claim.
    
    Spec: OMEN.md §8.1 "Evidence references", §9.2
    """
    ref_type: EvidenceRefType
    ref_id: str = Field(..., description="Unique identifier for the evidence")
    timestamp: datetime = Field(..., description="When evidence was captured")
    reliability_score: float | None = Field(
        default=None, 
        ge=0.0, 
        le=1.0, 
        description="Optional reliability assessment"
    )


class Evidence(BaseModel):
    """
    Evidence backing claims in the packet.
    
    Spec: OMEN.md §8.1, §9.2 "evidence"
    """
    evidence_refs: list[EvidenceRef] = Field(
        default_factory=list, 
        description="References to supporting evidence"
    )
    evidence_absent_reason: str | None = Field(
        default=None, 
        description="Explanation if evidence is absent"
    )
    
    @field_validator("evidence_absent_reason")
    @classmethod
    def require_reason_if_no_refs(cls, v: str | None, info) -> str | None:
        """If no evidence refs, require an explanation."""
        # Note: Cross-field validation handled in MCP model
        return v


class Routing(BaseModel):
    """
    Task routing information.
    
    Spec: OMEN.md §8.3.2, §8.3.7, §9.2 "routing"
    """
    task_class: TaskClass
    tools_state: ToolsState


# =============================================================================
# MCP ENVELOPE (Level 4 in ontology)
# =============================================================================

class MCP(BaseModel):
    """
    Mandatory Compliance Payload.
    
    Every consequential packet MUST include this envelope.
    This is the structural "mind over matter" gate.
    
    Spec: OMEN.md §9.2
    """
    intent: Intent
    stakes: Stakes
    quality: Quality
    budgets: Budgets
    epistemics: Epistemics
    evidence: Evidence
    routing: Routing
    
    @field_validator("evidence")
    @classmethod
    def validate_evidence_completeness(cls, v: Evidence) -> Evidence:
        """Ensure evidence has refs OR an explanation for absence."""
        if not v.evidence_refs and not v.evidence_absent_reason:
            raise ValueError(
                "Evidence must have either evidence_refs or evidence_absent_reason"
            )
        return v
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "intent": {
                        "summary": "Decide whether to verify intel before acting",
                        "scope": "intel_update"
                    },
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
                        "definition_of_done": {
                            "text": "Have at least one fresh observation for the key unknown",
                            "checks": ["fresh evidence collected"]
                        },
                        "verification_requirement": "VERIFY_ONE"
                    },
                    "budgets": {
                        "token_budget": 900,
                        "tool_call_budget": 2,
                        "time_budget_seconds": 90,
                        "risk_budget": {
                            "envelope": "low",
                            "max_loss": "small"
                        }
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
                    "routing": {
                        "task_class": "VERIFY",
                        "tools_state": "tools_ok"
                    }
                }
            ]
        }
    }
