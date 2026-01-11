"""
Self-Model — Persistent sense of self and capabilities.

Stores OMEN's understanding of itself, capabilities, and limitations.
Analogous to Default Mode Network self-representation in neuroscience.

Spec: Based on problem statement requirements for self-model.
"""

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Protocol, runtime_checkable


@dataclass
class SelfModelAspect:
    """
    An aspect of the self-model.
    
    Captures one dimension of self-understanding.
    """
    aspect: str  # "capabilities", "limitations", "purpose", "preferences"
    content: str
    formed_from: list[str] = field(default_factory=list)  # Episode IDs
    confidence: float = 0.5
    last_updated: datetime = field(default_factory=datetime.now)
    metadata: dict | None = None
    
    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "aspect": self.aspect,
            "content": self.content,
            "formed_from": self.formed_from,
            "confidence": self.confidence,
            "last_updated": self.last_updated.isoformat(),
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "SelfModelAspect":
        """Deserialize from dictionary."""
        return cls(
            aspect=data["aspect"],
            content=data["content"],
            formed_from=data.get("formed_from", []),
            confidence=data.get("confidence", 0.5),
            last_updated=datetime.fromisoformat(data["last_updated"]),
            metadata=data.get("metadata"),
        )


@runtime_checkable
class SelfModelStore(Protocol):
    """Protocol for self-model storage."""
    
    def save(self, aspect_data: SelfModelAspect) -> None:
        """Save or update a self-model aspect."""
        ...
    
    def load(self, aspect: str) -> SelfModelAspect | None:
        """Load a specific aspect of the self-model."""
        ...
    
    def get_all(self) -> list[SelfModelAspect]:
        """Get all aspects of the self-model."""
        ...
    
    def count(self) -> int:
        """Count aspects in self-model."""
        ...
    
    def clear(self) -> None:
        """Clear self-model (testing helper)."""
        ...


@dataclass
class SelfModel:
    """
    Persistent self-model for OMEN.
    
    Provides higher-level operations on self-model aspects.
    """
    store: SelfModelStore
    
    def update_aspect(
        self,
        aspect: str,
        content: str,
        confidence: float = 0.5,
        episode_id: str | None = None,
    ) -> SelfModelAspect:
        """Update a self-model aspect."""
        existing = self.store.load(aspect)
        
        if existing:
            existing.content = content
            existing.confidence = confidence
            existing.last_updated = datetime.now()
            if episode_id:
                existing.formed_from.append(episode_id)
            self.store.save(existing)
            return existing
        else:
            new_aspect = SelfModelAspect(
                aspect=aspect,
                content=content,
                confidence=confidence,
                formed_from=[episode_id] if episode_id else [],
            )
            self.store.save(new_aspect)
            return new_aspect
    
    def get_aspect(self, aspect: str) -> SelfModelAspect | None:
        """Get a specific aspect."""
        return self.store.load(aspect)
    
    def get_current_model(self) -> dict[str, str]:
        """Get current self-model as a simple dictionary."""
        aspects = self.store.get_all()
        return {a.aspect: a.content for a in aspects}


class InMemorySelfModelStore:
    """In-memory self-model store."""
    
    def __init__(self):
        self._aspects: dict[str, SelfModelAspect] = {}
    
    def save(self, aspect_data: SelfModelAspect) -> None:
        self._aspects[aspect_data.aspect] = aspect_data
    
    def load(self, aspect: str) -> SelfModelAspect | None:
        return self._aspects.get(aspect)
    
    def get_all(self) -> list[SelfModelAspect]:
        return list(self._aspects.values())
    
    def count(self) -> int:
        return len(self._aspects)
    
    def clear(self) -> None:
        self._aspects.clear()


class SQLiteSelfModelStore:
    """SQLite-backed self-model store."""
    
    def __init__(self, db_path: str | Path = "omen_memory.db"):
        self.db_path = Path(db_path)
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS self_model (
                    aspect TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    last_updated TEXT NOT NULL,
                    data TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_self_model_updated
                ON self_model(last_updated)
            """)
            conn.commit()
    
    def save(self, aspect_data: SelfModelAspect) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO self_model
                (aspect, content, confidence, last_updated, data)
                VALUES (?, ?, ?, ?, ?)
            """, (
                aspect_data.aspect,
                aspect_data.content,
                aspect_data.confidence,
                aspect_data.last_updated.isoformat(),
                json.dumps(aspect_data.to_dict()),
            ))
            conn.commit()
    
    def load(self, aspect: str) -> SelfModelAspect | None:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT data FROM self_model WHERE aspect = ?",
                (aspect,)
            )
            row = cursor.fetchone()
            if row:
                return SelfModelAspect.from_dict(json.loads(row[0]))
            return None
    
    def get_all(self) -> list[SelfModelAspect]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT data FROM self_model")
            return [
                SelfModelAspect.from_dict(json.loads(row[0]))
                for row in cursor.fetchall()
            ]
    
    def count(self) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM self_model")
            return cursor.fetchone()[0]
    
    def clear(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM self_model")
            conn.commit()


def create_self_model_store(
    backend: str = "memory",
    db_path: str | Path | None = None,
) -> SelfModelStore:
    """
    Factory for creating self-model stores.
    
    Args:
        backend: "memory" or "sqlite"
        db_path: Path to SQLite database (only for sqlite backend)
    
    Returns:
        SelfModelStore instance
    """
    if backend == "memory":
        return InMemorySelfModelStore()
    elif backend == "sqlite":
        return SQLiteSelfModelStore(db_path or "omen_memory.db")
    else:
        raise ValueError(f"Unknown backend: {backend}")
