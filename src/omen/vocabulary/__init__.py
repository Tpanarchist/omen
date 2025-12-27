"""
Vocabulary — Enumerated types forming the shared language of the system.

All enums referenced by packets, policies, and validators are defined here.
"""

from omen.vocabulary.enums import (
    # E-POL (Epistemic)
    EpistemicStatus,
    FreshnessClass,
    EvidenceRefType,
    # Q-POL (Quality/Stakes)
    ImpactLevel,
    Irreversibility,
    UncertaintyLevel,
    Adversariality,
    StakesLevel,
    QualityTier,
    VerificationRequirement,
    # C-POL (Compute)
    TaskClass,
    ToolsState,
    ToolSafety,
    # Packets
    PacketType,
    LayerSource,
    # FSM
    FSMState,
    # Decisions
    DecisionOutcome,
    TaskResultStatus,
    # Templates
    TemplateID,
    IntentClass,
)

__all__ = [
    # E-POL
    "EpistemicStatus",
    "FreshnessClass",
    "EvidenceRefType",
    # Q-POL
    "ImpactLevel",
    "Irreversibility",
    "UncertaintyLevel",
    "Adversariality",
    "StakesLevel",
    "QualityTier",
    "VerificationRequirement",
    # C-POL
    "TaskClass",
    "ToolsState",
    "ToolSafety",
    # Packets
    "PacketType",
    "LayerSource",
    # FSM
    "FSMState",
    # Decisions
    "DecisionOutcome",
    "TaskResultStatus",
    # Templates
    "TemplateID",
    "IntentClass",
]
