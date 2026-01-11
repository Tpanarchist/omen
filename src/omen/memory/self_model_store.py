"""
Self-Model Store — Tracks self-model entries and provenance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol, runtime_checkable
from uuid import UUID


@dataclass
class SelfModelEntry:
    """Represents a consolidated self-model entry."""
    entry_id: str
    summary: str
    patterns: list[str]
    episode_ids: list[UUID] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class SelfModelStore(Protocol):
    """Protocol for self-model persistence."""

    def add_entry(self, entry: SelfModelEntry) -> None:
        ...

    def list_entries(self) -> list[SelfModelEntry]:
        ...


class InMemorySelfModelStore:
    """Simple in-memory self-model store."""

    def __init__(self) -> None:
        self._entries: list[SelfModelEntry] = []

    def add_entry(self, entry: SelfModelEntry) -> None:
        self._entries.append(entry)

    def list_entries(self) -> list[SelfModelEntry]:
        return list(self._entries)


def create_memory_self_model_store() -> InMemorySelfModelStore:
    """Factory for in-memory self-model store."""
    return InMemorySelfModelStore()
