"""
Episode Storage — Persistence layer for episode records.

Provides storage backends for saving, loading, and querying episodes.
"""

import json
import sqlite3
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol, runtime_checkable
from uuid import UUID

from omen.episode.record import EpisodeRecord


@runtime_checkable
class EpisodeStore(Protocol):
    """
    Protocol for episode storage backends.
    """
    
    def save(self, episode: EpisodeRecord) -> None:
        """Save an episode record."""
        ...
    
    def load(self, correlation_id: UUID) -> EpisodeRecord | None:
        """Load an episode by correlation ID."""
        ...
    
    def exists(self, correlation_id: UUID) -> bool:
        """Check if an episode exists."""
        ...
    
    def delete(self, correlation_id: UUID) -> bool:
        """Delete an episode. Returns True if deleted."""
        ...
    
    def query(
        self,
        template_id: str | None = None,
        campaign_id: str | None = None,
        success: bool | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 100,
    ) -> list[EpisodeRecord]:
        """Query episodes with filters."""
        ...
    
    def count(self) -> int:
        """Count total episodes."""
        ...


class InMemoryStore:
    """
    In-memory episode store for testing.
    
    Episodes are lost when process terminates.
    """
    
    def __init__(self):
        self._episodes: dict[UUID, EpisodeRecord] = {}
    
    def save(self, episode: EpisodeRecord) -> None:
        self._episodes[episode.correlation_id] = episode
    
    def load(self, correlation_id: UUID) -> EpisodeRecord | None:
        return self._episodes.get(correlation_id)
    
    def exists(self, correlation_id: UUID) -> bool:
        return correlation_id in self._episodes
    
    def delete(self, correlation_id: UUID) -> bool:
        if correlation_id in self._episodes:
            del self._episodes[correlation_id]
            return True
        return False
    
    def query(
        self,
        template_id: str | None = None,
        campaign_id: str | None = None,
        success: bool | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 100,
    ) -> list[EpisodeRecord]:
        results = []
        
        for episode in self._episodes.values():
            if template_id and episode.template_id != template_id:
                continue
            if campaign_id and episode.campaign_id != campaign_id:
                continue
            if success is not None and episode.success != success:
                continue
            if since and episode.started_at < since:
                continue
            if until and episode.started_at > until:
                continue
            results.append(episode)
            if len(results) >= limit:
                break
        
        return sorted(results, key=lambda e: e.started_at, reverse=True)
    
    def count(self) -> int:
        return len(self._episodes)
    
    def clear(self) -> None:
        """Clear all episodes (testing helper)."""
        self._episodes.clear()


class SQLiteStore:
    """
    SQLite-backed episode store for persistence.
    
    Stores episodes in a local SQLite database.
    """
    
    def __init__(self, db_path: str | Path = "omen_episodes.db"):
        self.db_path = Path(db_path)
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS episodes (
                    correlation_id TEXT PRIMARY KEY,
                    template_id TEXT NOT NULL,
                    campaign_id TEXT,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    success INTEGER NOT NULL,
                    duration_seconds REAL,
                    step_count INTEGER,
                    data TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_template_id 
                ON episodes(template_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_campaign_id 
                ON episodes(campaign_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_started_at 
                ON episodes(started_at)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_success 
                ON episodes(success)
            """)
            conn.commit()
    
    def save(self, episode: EpisodeRecord) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO episodes 
                (correlation_id, template_id, campaign_id, started_at, 
                 completed_at, success, duration_seconds, step_count, data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(episode.correlation_id),
                episode.template_id,
                episode.campaign_id,
                episode.started_at.isoformat(),
                episode.completed_at.isoformat() if episode.completed_at else None,
                1 if episode.success else 0,
                episode.duration_seconds,
                episode.step_count,
                episode.to_json(),
            ))
            conn.commit()
    
    def load(self, correlation_id: UUID) -> EpisodeRecord | None:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT data FROM episodes WHERE correlation_id = ?",
                (str(correlation_id),)
            )
            row = cursor.fetchone()
            if row:
                return EpisodeRecord.from_json(row[0])
            return None
    
    def exists(self, correlation_id: UUID) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT 1 FROM episodes WHERE correlation_id = ?",
                (str(correlation_id),)
            )
            return cursor.fetchone() is not None
    
    def delete(self, correlation_id: UUID) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM episodes WHERE correlation_id = ?",
                (str(correlation_id),)
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def query(
        self,
        template_id: str | None = None,
        campaign_id: str | None = None,
        success: bool | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 100,
    ) -> list[EpisodeRecord]:
        conditions = []
        params = []
        
        if template_id:
            conditions.append("template_id = ?")
            params.append(template_id)
        if campaign_id:
            conditions.append("campaign_id = ?")
            params.append(campaign_id)
        if success is not None:
            conditions.append("success = ?")
            params.append(1 if success else 0)
        if since:
            conditions.append("started_at >= ?")
            params.append(since.isoformat())
        if until:
            conditions.append("started_at <= ?")
            params.append(until.isoformat())
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        params.append(limit)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(f"""
                SELECT data FROM episodes 
                WHERE {where_clause}
                ORDER BY started_at DESC
                LIMIT ?
            """, params)
            
            return [EpisodeRecord.from_json(row[0]) for row in cursor.fetchall()]
    
    def count(self) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM episodes")
            return cursor.fetchone()[0]
    
    def clear(self) -> None:
        """Clear all episodes (testing helper)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM episodes")
            conn.commit()


def create_memory_store() -> InMemoryStore:
    """Factory for in-memory store."""
    return InMemoryStore()


def create_sqlite_store(db_path: str | Path = "omen_episodes.db") -> SQLiteStore:
    """Factory for SQLite store."""
    return SQLiteStore(db_path)
