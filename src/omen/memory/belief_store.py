"""
Belief Store — Persistence layer for belief records.

Provides storage backends for saving, loading, and querying beliefs.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field, replace
from datetime import datetime
from pathlib import Path
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class BeliefEntry:
    """
    Immutable belief entry with versioning metadata.
    """
    belief_id: str
    domain: str
    claim: str
    confidence: float
    evidence_refs: list[str] = field(default_factory=list)
    version: int = 1
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_json(self) -> str:
        """Serialize the belief entry as JSON."""
        return json.dumps({
            "belief_id": self.belief_id,
            "domain": self.domain,
            "claim": self.claim,
            "confidence": self.confidence,
            "evidence_refs": self.evidence_refs,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        })

    @classmethod
    def from_row(cls, row: tuple) -> "BeliefEntry":
        """Create a belief entry from a SQLite row."""
        (
            belief_id,
            version,
            domain,
            claim,
            confidence,
            evidence_refs,
            created_at,
            updated_at,
        ) = row
        return cls(
            belief_id=belief_id,
            domain=domain,
            claim=claim,
            confidence=confidence,
            evidence_refs=json.loads(evidence_refs),
            version=version,
            created_at=datetime.fromisoformat(created_at),
            updated_at=datetime.fromisoformat(updated_at),
        )


@runtime_checkable
class BeliefStore(Protocol):
    """
    Protocol for belief storage backends.
    """

    def create(self, belief: BeliefEntry) -> BeliefEntry:
        """Create a new belief entry."""
        ...

    def load(self, belief_id: str, version: int | None = None) -> BeliefEntry | None:
        """Load a belief by ID (and optional version)."""
        ...

    def update(
        self,
        belief_id: str,
        *,
        domain: str | None = None,
        claim: str | None = None,
        confidence: float | None = None,
        evidence_refs: list[str] | None = None,
    ) -> BeliefEntry | None:
        """Update a belief by ID, returning the new version."""
        ...

    def exists(self, belief_id: str) -> bool:
        """Check if a belief exists."""
        ...

    def delete(self, belief_id: str) -> bool:
        """Delete a belief. Returns True if deleted."""
        ...

    def query(
        self,
        *,
        domain: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 100,
    ) -> list[BeliefEntry]:
        """Query beliefs with filters (latest versions only)."""
        ...


class InMemoryBeliefStore:
    """
    In-memory belief store for testing.

    Beliefs are lost when process terminates.
    """

    def __init__(self) -> None:
        self._beliefs: dict[str, list[BeliefEntry]] = {}

    def create(self, belief: BeliefEntry) -> BeliefEntry:
        if belief.belief_id in self._beliefs:
            raise ValueError(f"Belief already exists: {belief.belief_id}")
        normalized = replace(
            belief,
            version=1,
        )
        self._beliefs[belief.belief_id] = [normalized]
        return normalized

    def load(self, belief_id: str, version: int | None = None) -> BeliefEntry | None:
        versions = self._beliefs.get(belief_id)
        if not versions:
            return None
        if version is None:
            return versions[-1]
        for entry in versions:
            if entry.version == version:
                return entry
        return None

    def update(
        self,
        belief_id: str,
        *,
        domain: str | None = None,
        claim: str | None = None,
        confidence: float | None = None,
        evidence_refs: list[str] | None = None,
    ) -> BeliefEntry | None:
        latest = self.load(belief_id)
        if latest is None:
            return None
        now = datetime.utcnow()
        updated = BeliefEntry(
            belief_id=belief_id,
            domain=domain or latest.domain,
            claim=claim or latest.claim,
            confidence=confidence if confidence is not None else latest.confidence,
            evidence_refs=evidence_refs if evidence_refs is not None else list(latest.evidence_refs),
            version=latest.version + 1,
            created_at=latest.created_at,
            updated_at=now,
        )
        self._beliefs[belief_id].append(updated)
        return updated

    def exists(self, belief_id: str) -> bool:
        return belief_id in self._beliefs

    def delete(self, belief_id: str) -> bool:
        if belief_id in self._beliefs:
            del self._beliefs[belief_id]
            return True
        return False

    def query(
        self,
        *,
        domain: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 100,
    ) -> list[BeliefEntry]:
        results = []
        for versions in self._beliefs.values():
            entry = versions[-1]
            if domain and entry.domain != domain:
                continue
            if since and entry.updated_at < since:
                continue
            if until and entry.updated_at > until:
                continue
            results.append(entry)
            if len(results) >= limit:
                break
        return sorted(results, key=lambda e: e.updated_at, reverse=True)

    def clear(self) -> None:
        """Clear all beliefs (testing helper)."""
        self._beliefs.clear()


class SQLiteBeliefStore:
    """
    SQLite-backed belief store for persistence.

    Stores beliefs in a local SQLite database.
    """

    def __init__(self, db_path: str | Path = "omen_beliefs.db") -> None:
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS beliefs (
                    belief_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    domain TEXT NOT NULL,
                    claim TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    evidence_refs TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (belief_id, version)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_beliefs_domain
                ON beliefs(domain)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_beliefs_updated_at
                ON beliefs(updated_at)
            """)
            conn.commit()

    def create(self, belief: BeliefEntry) -> BeliefEntry:
        if self.exists(belief.belief_id):
            raise ValueError(f"Belief already exists: {belief.belief_id}")
        now = datetime.utcnow()
        normalized = replace(
            belief,
            version=1,
            created_at=belief.created_at or now,
            updated_at=belief.updated_at or now,
        )
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO beliefs (
                    belief_id, version, domain, claim, confidence,
                    evidence_refs, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                normalized.belief_id,
                normalized.version,
                normalized.domain,
                normalized.claim,
                normalized.confidence,
                json.dumps(normalized.evidence_refs),
                normalized.created_at.isoformat(),
                normalized.updated_at.isoformat(),
            ))
            conn.commit()
        return normalized

    def load(self, belief_id: str, version: int | None = None) -> BeliefEntry | None:
        with sqlite3.connect(self.db_path) as conn:
            if version is None:
                cursor = conn.execute("""
                    SELECT belief_id, version, domain, claim, confidence,
                           evidence_refs, created_at, updated_at
                    FROM beliefs
                    WHERE belief_id = ?
                    ORDER BY version DESC
                    LIMIT 1
                """, (belief_id,))
            else:
                cursor = conn.execute("""
                    SELECT belief_id, version, domain, claim, confidence,
                           evidence_refs, created_at, updated_at
                    FROM beliefs
                    WHERE belief_id = ? AND version = ?
                """, (belief_id, version))
            row = cursor.fetchone()
        if row:
            return BeliefEntry.from_row(row)
        return None

    def update(
        self,
        belief_id: str,
        *,
        domain: str | None = None,
        claim: str | None = None,
        confidence: float | None = None,
        evidence_refs: list[str] | None = None,
    ) -> BeliefEntry | None:
        latest = self.load(belief_id)
        if latest is None:
            return None
        now = datetime.utcnow()
        updated = BeliefEntry(
            belief_id=belief_id,
            domain=domain or latest.domain,
            claim=claim or latest.claim,
            confidence=confidence if confidence is not None else latest.confidence,
            evidence_refs=evidence_refs if evidence_refs is not None else list(latest.evidence_refs),
            version=latest.version + 1,
            created_at=latest.created_at,
            updated_at=now,
        )
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO beliefs (
                    belief_id, version, domain, claim, confidence,
                    evidence_refs, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                updated.belief_id,
                updated.version,
                updated.domain,
                updated.claim,
                updated.confidence,
                json.dumps(updated.evidence_refs),
                updated.created_at.isoformat(),
                updated.updated_at.isoformat(),
            ))
            conn.commit()
        return updated

    def exists(self, belief_id: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT 1 FROM beliefs WHERE belief_id = ?",
                (belief_id,),
            )
            return cursor.fetchone() is not None

    def delete(self, belief_id: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM beliefs WHERE belief_id = ?",
                (belief_id,),
            )
            conn.commit()
            return cursor.rowcount > 0

    def query(
        self,
        *,
        domain: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 100,
    ) -> list[BeliefEntry]:
        conditions = []
        params: list[object] = []

        if domain:
            conditions.append("beliefs.domain = ?")
            params.append(domain)
        if since:
            conditions.append("beliefs.updated_at >= ?")
            params.append(since.isoformat())
        if until:
            conditions.append("beliefs.updated_at <= ?")
            params.append(until.isoformat())

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        params.append(limit)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(f"""
                SELECT beliefs.belief_id, beliefs.version, beliefs.domain,
                       beliefs.claim, beliefs.confidence, beliefs.evidence_refs,
                       beliefs.created_at, beliefs.updated_at
                FROM beliefs
                INNER JOIN (
                    SELECT belief_id, MAX(version) AS max_version
                    FROM beliefs
                    GROUP BY belief_id
                ) latest
                ON beliefs.belief_id = latest.belief_id
                AND beliefs.version = latest.max_version
                WHERE {where_clause}
                ORDER BY beliefs.updated_at DESC
                LIMIT ?
            """, params)
            return [BeliefEntry.from_row(row) for row in cursor.fetchall()]

    def clear(self) -> None:
        """Clear all beliefs (testing helper)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM beliefs")
            conn.commit()


def create_memory_store() -> InMemoryBeliefStore:
    """Factory for in-memory belief store."""
    return InMemoryBeliefStore()


def create_sqlite_store(db_path: str | Path = "omen_beliefs.db") -> SQLiteBeliefStore:
    """Factory for SQLite belief store."""
    return SQLiteBeliefStore(db_path)
