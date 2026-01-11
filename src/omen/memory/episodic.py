"""
Episodic Memory — Autobiographical memory of past episodes.

Stores summaries of executed episodes for retrieval and learning.
Analogous to hippocampal episodic memory in neuroscience.

Spec: Based on problem statement requirements for episodic memory.
"""

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Protocol, runtime_checkable
from uuid import UUID


@dataclass
class EpisodicMemory:
    """
    Summary of a past episode for long-term memory.
    
    Stores key information about what happened, outcomes, and lessons learned.
    """
    episode_id: UUID
    timestamp: datetime
    template_id: str
    summary: str
    key_events: list[str] = field(default_factory=list)
    outcome: str = ""  # "success", "failure", "partial"
    lessons_learned: list[str] = field(default_factory=list)
    context_tags: list[str] = field(default_factory=list)
    domain: str | None = None
    duration_seconds: float = 0.0
    success: bool = False
    
    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "episode_id": str(self.episode_id),
            "timestamp": self.timestamp.isoformat(),
            "template_id": self.template_id,
            "summary": self.summary,
            "key_events": self.key_events,
            "outcome": self.outcome,
            "lessons_learned": self.lessons_learned,
            "context_tags": self.context_tags,
            "domain": self.domain,
            "duration_seconds": self.duration_seconds,
            "success": self.success,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "EpisodicMemory":
        """Deserialize from dictionary."""
        return cls(
            episode_id=UUID(data["episode_id"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            template_id=data["template_id"],
            summary=data["summary"],
            key_events=data.get("key_events", []),
            outcome=data.get("outcome", ""),
            lessons_learned=data.get("lessons_learned", []),
            context_tags=data.get("context_tags", []),
            domain=data.get("domain"),
            duration_seconds=data.get("duration_seconds", 0.0),
            success=data.get("success", False),
        )


@runtime_checkable
class EpisodicMemoryStore(Protocol):
    """Protocol for episodic memory storage."""
    
    def save(self, memory: EpisodicMemory) -> None:
        """Save an episodic memory."""
        ...
    
    def load(self, episode_id: UUID) -> EpisodicMemory | None:
        """Load a specific episode memory."""
        ...
    
    def search(
        self,
        query: str | None = None,
        domain: str | None = None,
        tags: list[str] | None = None,
        since: datetime | None = None,
        limit: int = 10,
    ) -> list[EpisodicMemory]:
        """Search for relevant episode memories."""
        ...
    
    def count(self) -> int:
        """Count total memories."""
        ...
    
    def clear(self) -> None:
        """Clear all memories (testing helper)."""
        ...


class InMemoryEpisodicStore:
    """In-memory episodic memory store."""
    
    def __init__(self):
        self._memories: dict[UUID, EpisodicMemory] = {}
    
    def save(self, memory: EpisodicMemory) -> None:
        self._memories[memory.episode_id] = memory
    
    def load(self, episode_id: UUID) -> EpisodicMemory | None:
        return self._memories.get(episode_id)
    
    def search(
        self,
        query: str | None = None,
        domain: str | None = None,
        tags: list[str] | None = None,
        since: datetime | None = None,
        limit: int = 10,
    ) -> list[EpisodicMemory]:
        results = []
        
        for memory in self._memories.values():
            # Filter by domain
            if domain and memory.domain != domain:
                continue
            
            # Filter by tags
            if tags and not any(tag in memory.context_tags for tag in tags):
                continue
            
            # Filter by timestamp
            if since and memory.timestamp < since:
                continue
            
            # Simple text search in summary and key events
            if query:
                search_text = query.lower()
                searchable = (
                    memory.summary.lower() + 
                    " ".join(memory.key_events).lower() +
                    " ".join(memory.lessons_learned).lower()
                )
                if search_text not in searchable:
                    continue
            
            results.append(memory)
            if len(results) >= limit:
                break
        
        # Sort by timestamp, most recent first
        return sorted(results, key=lambda m: m.timestamp, reverse=True)
    
    def count(self) -> int:
        return len(self._memories)
    
    def clear(self) -> None:
        self._memories.clear()


class SQLiteEpisodicStore:
    """SQLite-backed episodic memory store."""
    
    def __init__(self, db_path: str | Path = "omen_memory.db"):
        self.db_path = Path(db_path)
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS episodic_memory (
                    episode_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    template_id TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    outcome TEXT,
                    domain TEXT,
                    duration_seconds REAL,
                    success INTEGER,
                    data TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_episodic_timestamp
                ON episodic_memory(timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_episodic_domain
                ON episodic_memory(domain)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_episodic_template
                ON episodic_memory(template_id)
            """)
            conn.commit()
    
    def save(self, memory: EpisodicMemory) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO episodic_memory
                (episode_id, timestamp, template_id, summary, outcome,
                 domain, duration_seconds, success, data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(memory.episode_id),
                memory.timestamp.isoformat(),
                memory.template_id,
                memory.summary,
                memory.outcome,
                memory.domain,
                memory.duration_seconds,
                1 if memory.success else 0,
                json.dumps(memory.to_dict()),
            ))
            conn.commit()
    
    def load(self, episode_id: UUID) -> EpisodicMemory | None:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT data FROM episodic_memory WHERE episode_id = ?",
                (str(episode_id),)
            )
            row = cursor.fetchone()
            if row:
                return EpisodicMemory.from_dict(json.loads(row[0]))
            return None
    
    def search(
        self,
        query: str | None = None,
        domain: str | None = None,
        tags: list[str] | None = None,
        since: datetime | None = None,
        limit: int = 10,
    ) -> list[EpisodicMemory]:
        conditions = []
        params = []
        
        if domain:
            conditions.append("domain = ?")
            params.append(domain)
        
        if since:
            conditions.append("timestamp >= ?")
            params.append(since.isoformat())
        
        # For text search and tags, we need to load and filter
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        params.append(limit * 2)  # Get more to filter
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(f"""
                SELECT data FROM episodic_memory
                WHERE {where_clause}
                ORDER BY timestamp DESC
                LIMIT ?
            """, params)
            
            results = []
            for row in cursor.fetchall():
                memory = EpisodicMemory.from_dict(json.loads(row[0]))
                
                # Filter by tags
                if tags and not any(tag in memory.context_tags for tag in tags):
                    continue
                
                # Filter by query text
                if query:
                    search_text = query.lower()
                    searchable = (
                        memory.summary.lower() +
                        " ".join(memory.key_events).lower() +
                        " ".join(memory.lessons_learned).lower()
                    )
                    if search_text not in searchable:
                        continue
                
                results.append(memory)
                if len(results) >= limit:
                    break
            
            return results
    
    def count(self) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM episodic_memory")
            return cursor.fetchone()[0]
    
    def clear(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM episodic_memory")
            conn.commit()


def create_episodic_store(
    backend: str = "memory",
    db_path: str | Path | None = None,
) -> EpisodicMemoryStore:
    """
    Factory for creating episodic memory stores.
    
    Args:
        backend: "memory" or "sqlite"
        db_path: Path to SQLite database (only for sqlite backend)
    
    Returns:
        EpisodicMemoryStore instance
    """
    if backend == "memory":
        return InMemoryEpisodicStore()
    elif backend == "sqlite":
        return SQLiteEpisodicStore(db_path or "omen_memory.db")
    else:
        raise ValueError(f"Unknown backend: {backend}")
