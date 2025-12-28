"""
Episode Record — Persistent representation of completed episodes.

Captures the full episode lifecycle for storage and replay.

Spec: OMEN.md §10.5
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from omen.vocabulary import StakesLevel, QualityTier, ToolsState


@dataclass
class PacketRecord:
    """
    Record of a packet emitted during episode execution.
    """
    packet_id: str
    packet_type: str
    source_layer: str
    timestamp: datetime
    payload: dict[str, Any]
    correlation_id: str
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "packet_id": self.packet_id,
            "packet_type": self.packet_type,
            "source_layer": self.source_layer,
            "timestamp": self.timestamp.isoformat(),
            "payload": self.payload,
            "correlation_id": self.correlation_id,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PacketRecord":
        return cls(
            packet_id=data["packet_id"],
            packet_type=data["packet_type"],
            source_layer=data["source_layer"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            payload=data["payload"],
            correlation_id=data["correlation_id"],
        )


@dataclass
class StepRecord:
    """
    Record of a step executed during episode.
    """
    step_id: str
    sequence_number: int
    layer: str
    fsm_state: str
    packet_type: str | None
    started_at: datetime
    completed_at: datetime
    success: bool
    packets_emitted: list[str] = field(default_factory=list)  # Packet IDs
    error: str | None = None
    raw_llm_response: str = ""
    token_usage: dict[str, int] = field(default_factory=dict)
    
    @property
    def duration_seconds(self) -> float:
        return (self.completed_at - self.started_at).total_seconds()
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "sequence_number": self.sequence_number,
            "layer": self.layer,
            "fsm_state": self.fsm_state,
            "packet_type": self.packet_type,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "success": self.success,
            "packets_emitted": self.packets_emitted,
            "error": self.error,
            "raw_llm_response": self.raw_llm_response,
            "token_usage": self.token_usage,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StepRecord":
        return cls(
            step_id=data["step_id"],
            sequence_number=data["sequence_number"],
            layer=data["layer"],
            fsm_state=data["fsm_state"],
            packet_type=data.get("packet_type"),
            started_at=datetime.fromisoformat(data["started_at"]),
            completed_at=datetime.fromisoformat(data["completed_at"]),
            success=data["success"],
            packets_emitted=data.get("packets_emitted", []),
            error=data.get("error"),
            raw_llm_response=data.get("raw_llm_response", ""),
            token_usage=data.get("token_usage", {}),
        )


@dataclass
class EpisodeRecord:
    """
    Complete record of an executed episode.
    
    Captures everything needed to understand what happened
    and potentially replay the episode.
    """
    # Identity
    correlation_id: UUID
    template_id: str
    campaign_id: str | None = None
    
    # Lifecycle
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None
    
    # Outcome
    success: bool = False
    final_step: str | None = None
    errors: list[str] = field(default_factory=list)
    
    # Policy context
    stakes_level: str = "LOW"
    quality_tier: str = "PAR"
    tools_state: str = "TOOLS_OK"
    
    # Execution details
    steps: list[StepRecord] = field(default_factory=list)
    packets: list[PacketRecord] = field(default_factory=list)
    
    # Budget tracking
    budget_allocated: dict[str, int] = field(default_factory=dict)
    budget_consumed: dict[str, int] = field(default_factory=dict)
    
    # Evidence and assumptions
    evidence_refs: list[dict[str, Any]] = field(default_factory=list)
    assumptions: list[dict[str, Any]] = field(default_factory=list)
    
    # Integrity
    contradictions: list[str] = field(default_factory=list)
    
    @property
    def duration_seconds(self) -> float:
        if self.completed_at is None:
            return 0.0
        return (self.completed_at - self.started_at).total_seconds()
    
    @property
    def step_count(self) -> int:
        return len(self.steps)
    
    @property
    def packet_count(self) -> int:
        return len(self.packets)
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for storage."""
        return {
            "correlation_id": str(self.correlation_id),
            "template_id": self.template_id,
            "campaign_id": self.campaign_id,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "success": self.success,
            "final_step": self.final_step,
            "errors": self.errors,
            "stakes_level": self.stakes_level,
            "quality_tier": self.quality_tier,
            "tools_state": self.tools_state,
            "steps": [s.to_dict() for s in self.steps],
            "packets": [p.to_dict() for p in self.packets],
            "budget_allocated": self.budget_allocated,
            "budget_consumed": self.budget_consumed,
            "evidence_refs": self.evidence_refs,
            "assumptions": self.assumptions,
            "contradictions": self.contradictions,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EpisodeRecord":
        """Deserialize from dictionary."""
        return cls(
            correlation_id=UUID(data["correlation_id"]),
            template_id=data["template_id"],
            campaign_id=data.get("campaign_id"),
            started_at=datetime.fromisoformat(data["started_at"]),
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            success=data["success"],
            final_step=data.get("final_step"),
            errors=data.get("errors", []),
            stakes_level=data.get("stakes_level", "LOW"),
            quality_tier=data.get("quality_tier", "PAR"),
            tools_state=data.get("tools_state", "TOOLS_OK"),
            steps=[StepRecord.from_dict(s) for s in data.get("steps", [])],
            packets=[PacketRecord.from_dict(p) for p in data.get("packets", [])],
            budget_allocated=data.get("budget_allocated", {}),
            budget_consumed=data.get("budget_consumed", {}),
            evidence_refs=data.get("evidence_refs", []),
            assumptions=data.get("assumptions", []),
            contradictions=data.get("contradictions", []),
        )
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        import json
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> "EpisodeRecord":
        """Deserialize from JSON string."""
        import json
        return cls.from_dict(json.loads(json_str))
