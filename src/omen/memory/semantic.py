"""
Semantic Memory — Learned beliefs and knowledge.

Stores facts, beliefs, and domain knowledge extracted from episodes.
Analogous to cortical semantic memory in neuroscience.

Spec: Based on problem statement requirements for semantic memory.
"""

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Protocol, runtime_checkable
from uuid import UUID, uuid4


@dataclass
class Belief:
    """
    A learned belief or piece of knowledge.
    
    Tracks what is believed, why, and how confidence evolves.
    """
    belief_id: str
    domain: str
    claim: str
    confidence: float
    evidence_refs: list[str] = field(default_factory=list)
    updated_at: datetime = field(default_factory=datetime.now)
    version: int = 1
    formed_from: list[str] = field(default_factory=list)  # Episode IDs
    metadata: dict | None = None
    
    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "belief_id": self.belief_id,
            "domain": self.domain,
            "claim": self.claim,
            "confidence": self.confidence,
            "evidence_refs": self.evidence_refs,
            "updated_at": self.updated_at.isoformat(),
            "version": self.version,
            "formed_from": self.formed_from,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Belief":
        """Deserialize from dictionary."""
        return cls(
            belief_id=data["belief_id"],
            domain=data["domain"],
            claim=data["claim"],
            confidence=data["confidence"],
            evidence_refs=data.get("evidence_refs", []),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            version=data.get("version", 1),
            formed_from=data.get("formed_from", []),
            metadata=data.get("metadata"),
        )


@runtime_checkable
class SemanticMemoryStore(Protocol):
    """Protocol for semantic memory (beliefs) storage."""
    
    def save(self, belief: Belief) -> None:
        """Save or update a belief."""
        ...
    
    def load(self, belief_id: str) -> Belief | None:
        """Load a specific belief."""
        ...
    
    def query(
        self,
        domain: str | None = None,
        min_confidence: float | None = None,
        query_text: str | None = None,
        limit: int = 100,
    ) -> list[Belief]:
        """Query beliefs with filters."""
        ...
    
    def count(self) -> int:
        """Count total beliefs."""
        ...
    
    def clear(self) -> None:
        """Clear all beliefs (testing helper)."""
        ...


@dataclass
class SemanticMemory:
    """
    Collection of beliefs for a domain.
    
    Provides higher-level operations on beliefs.
    """
    store: SemanticMemoryStore
    
    def add_belief(
        self,
        domain: str,
        claim: str,
        confidence: float,
        evidence_refs: list[str] | None = None,
        formed_from: list[str] | None = None,
    ) -> Belief:
        """Add a new belief."""
        belief = Belief(
            belief_id=str(uuid4()),
            domain=domain,
            claim=claim,
            confidence=confidence,
            evidence_refs=evidence_refs or [],
            formed_from=formed_from or [],
        )
        self.store.save(belief)
        return belief
    
    def update_belief(
        self,
        belief_id: str,
        confidence: float | None = None,
        new_evidence: list[str] | None = None,
        new_episode: str | None = None,
    ) -> Belief | None:
        """Update an existing belief."""
        belief = self.store.load(belief_id)
        if not belief:
            return None
        
        if confidence is not None:
            belief.confidence = confidence
        
        if new_evidence:
            belief.evidence_refs.extend(new_evidence)
        
        if new_episode:
            belief.formed_from.append(new_episode)
        
        belief.updated_at = datetime.now()
        belief.version += 1
        
        self.store.save(belief)
        return belief
    
    def get_domain_beliefs(self, domain: str, min_confidence: float = 0.0) -> list[Belief]:
        """Get all beliefs for a domain."""
        return self.store.query(domain=domain, min_confidence=min_confidence)


class InMemorySemanticStore:
    """In-memory semantic memory (beliefs) store."""
    
    def __init__(self):
        self._beliefs: dict[str, Belief] = {}
    
    def save(self, belief: Belief) -> None:
        self._beliefs[belief.belief_id] = belief
    
    def load(self, belief_id: str) -> Belief | None:
        return self._beliefs.get(belief_id)
    
    def query(
        self,
        domain: str | None = None,
        min_confidence: float | None = None,
        query_text: str | None = None,
        limit: int = 100,
    ) -> list[Belief]:
        results = []
        
        for belief in self._beliefs.values():
            # Filter by domain
            if domain and belief.domain != domain:
                continue
            
            # Filter by confidence
            if min_confidence is not None and belief.confidence < min_confidence:
                continue
            
            # Filter by query text
            if query_text:
                search_text = query_text.lower()
                if search_text not in belief.claim.lower():
                    continue
            
            results.append(belief)
            if len(results) >= limit:
                break
        
        # Sort by confidence descending
        return sorted(results, key=lambda b: b.confidence, reverse=True)
    
    def count(self) -> int:
        return len(self._beliefs)
    
    def clear(self) -> None:
        self._beliefs.clear()


class SQLiteSemanticStore:
    """SQLite-backed semantic memory (beliefs) store."""
    
    def __init__(self, db_path: str | Path = "omen_memory.db"):
        self.db_path = Path(db_path)
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS beliefs (
                    belief_id TEXT PRIMARY KEY,
                    domain TEXT NOT NULL,
                    claim TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    updated_at TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    data TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_beliefs_domain
                ON beliefs(domain)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_beliefs_confidence
                ON beliefs(confidence)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_beliefs_updated
                ON beliefs(updated_at)
            """)
            conn.commit()
    
    def save(self, belief: Belief) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO beliefs
                (belief_id, domain, claim, confidence, updated_at, version, data)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                belief.belief_id,
                belief.domain,
                belief.claim,
                belief.confidence,
                belief.updated_at.isoformat(),
                belief.version,
                json.dumps(belief.to_dict()),
            ))
            conn.commit()
    
    def load(self, belief_id: str) -> Belief | None:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT data FROM beliefs WHERE belief_id = ?",
                (belief_id,)
            )
            row = cursor.fetchone()
            if row:
                return Belief.from_dict(json.loads(row[0]))
            return None
    
    def query(
        self,
        domain: str | None = None,
        min_confidence: float | None = None,
        query_text: str | None = None,
        limit: int = 100,
    ) -> list[Belief]:
        conditions = []
        params = []
        
        if domain:
            conditions.append("domain = ?")
            params.append(domain)
        
        if min_confidence is not None:
            conditions.append("confidence >= ?")
            params.append(min_confidence)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        params.append(limit)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(f"""
                SELECT data FROM beliefs
                WHERE {where_clause}
                ORDER BY confidence DESC
                LIMIT ?
            """, params)
            
            results = []
            for row in cursor.fetchall():
                belief = Belief.from_dict(json.loads(row[0]))
                
                # Filter by query text (post-query filter)
                if query_text:
                    search_text = query_text.lower()
                    if search_text not in belief.claim.lower():
                        continue
                
                results.append(belief)
            
            return results
    
    def count(self) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM beliefs")
            return cursor.fetchone()[0]
    
    def clear(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM beliefs")
            conn.commit()


def create_semantic_store(
    backend: str = "memory",
    db_path: str | Path | None = None,
) -> SemanticMemoryStore:
    """
    Factory for creating semantic memory (beliefs) stores.
    
    Args:
        backend: "memory" or "sqlite"
        db_path: Path to SQLite database (only for sqlite backend)
    
    Returns:
        SemanticMemoryStore instance
    """
    if backend == "memory":
        return InMemorySemanticStore()
    elif backend == "sqlite":
        return SQLiteSemanticStore(db_path or "omen_memory.db")
    else:
        raise ValueError(f"Unknown backend: {backend}")
