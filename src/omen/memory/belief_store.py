"""
Belief Store — minimal interface for persistent belief retrieval.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import json
from typing import Any, Protocol


@dataclass
class BeliefRecord:
    """
    Minimal representation of a stored belief.
    """
    belief_id: str
    domain: str
    summary: str
    details: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    updated_at: datetime = field(default_factory=datetime.now)


class BeliefStore(Protocol):
    """
    Protocol for belief storage backends.
    """

    def query(
        self,
        domain: str | None = None,
        tags: list[str] | None = None,
        keywords: list[str] | None = None,
        limit: int = 10,
    ) -> list[BeliefRecord]:
        """Query belief records."""
        ...


class InMemoryBeliefStore:
    """
    In-memory belief store for testing.
    """

    def __init__(self) -> None:
        self._beliefs: list[BeliefRecord] = []

    def add(self, record: BeliefRecord) -> None:
        """Add a belief record."""
        self._beliefs.append(record)

    def query(
        self,
        domain: str | None = None,
        tags: list[str] | None = None,
        keywords: list[str] | None = None,
        limit: int = 10,
    ) -> list[BeliefRecord]:
        normalized_tags = {t.lower() for t in tags or []}
        normalized_keywords = {k.lower() for k in keywords or []}
        results: list[BeliefRecord] = []

        for record in self._beliefs:
            matches_domain = domain is None or record.domain == domain
            matches_tags = (
                not normalized_tags
                or any(tag.lower() in normalized_tags for tag in record.tags)
            )
            matches_keywords = False
            if normalized_keywords:
                haystack = " ".join([
                    record.summary,
                    record.domain,
                    json.dumps(record.details, sort_keys=True),
                ]).lower()
                matches_keywords = any(keyword in haystack for keyword in normalized_keywords)

            if (matches_domain or matches_tags or matches_keywords):
                results.append(record)
            if len(results) >= limit:
                break

        return results
