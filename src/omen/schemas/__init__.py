"""
Schemas — JSON Schemas and Pydantic models for packet structures.

Defines:
- MCP envelope (Mandatory Compliance Payload)
- Packet header
- 9 packet type payloads
"""

from omen.schemas.mcp import (
    # Atomic structures
    Intent,
    Stakes,
    DefinitionOfDone,
    Quality,
    RiskBudget,
    Budgets,
    Epistemics,
    EvidenceRef,
    Evidence,
    Routing,
    # MCP envelope
    MCP,
)

from omen.schemas.header import PacketHeader

from omen.schemas.packets import (
    # Observation
    ObservationPacket,
    ObservationPayload,
    # Belief Update
    BeliefUpdatePacket,
    BeliefUpdatePayload,
    # Decision
    DecisionPacket,
    DecisionPayload,
    # Verification Plan
    VerificationPlanPacket,
    VerificationPlanPayload,
)

__all__ = [
    # Atomic structures
    "Intent",
    "Stakes",
    "DefinitionOfDone",
    "Quality",
    "RiskBudget",
    "Budgets",
    "Epistemics",
    "EvidenceRef",
    "Evidence",
    "Routing",
    # MCP envelope
    "MCP",
    # Packet header
    "PacketHeader",
    # Packets
    "ObservationPacket",
    "ObservationPayload",
    "BeliefUpdatePacket",
    "BeliefUpdatePayload",
    "DecisionPacket",
    "DecisionPayload",
    "VerificationPlanPacket",
    "VerificationPlanPayload",
]
