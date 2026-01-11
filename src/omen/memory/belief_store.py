"""
Belief Store — Tracks belief entries updated via consolidation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol, runtime_checkable
from uuid import UUID


@dataclass
class BeliefEntry:
    """Represents a belief and its provenance."""
    belief_id: str
    domain: str
    statement: str
    confidence: float
    episode_ids: list[UUID] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    updated_at: datetime = field(default_factory=datetime.now)


@runtime_checkable
class BeliefStore(Protocol):
    """Protocol for belief persistence."""

    def get(self, belief_id: str) -> BeliefEntry | None:
        ...

    def upsert(self, entry: BeliefEntry) -> None:
        ...

    def list_entries(self) -> list[BeliefEntry]:
        ...


class InMemoryBeliefStore:
    """Simple in-memory belief store."""

    def __init__(self) -> None:
        self._entries: dict[str, BeliefEntry] = {}

    def get(self, belief_id: str) -> BeliefEntry | None:
        return self._entries.get(belief_id)

    def upsert(self, entry: BeliefEntry) -> None:
        self._entries[entry.belief_id] = entry

    def list_entries(self) -> list[BeliefEntry]:
        return list(self._entries.values())


def create_memory_belief_store() -> InMemoryBeliefStore:
    """Factory for in-memory belief store."""
    return InMemoryBeliefStore()
