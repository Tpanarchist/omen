"""Tests for episode storage."""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from pathlib import Path

from omen.episode import (
    EpisodeRecord,
    InMemoryStore,
    SQLiteStore,
    create_memory_store,
    create_sqlite_store,
)


class TestInMemoryStore:
    """Tests for in-memory storage."""
    
    @pytest.fixture
    def store(self):
        return create_memory_store()
    
    @pytest.fixture
    def sample_episode(self):
        return EpisodeRecord(
            correlation_id=uuid4(),
            template_id="TEMPLATE_A",
            started_at=datetime.now(),
            success=True,
        )
    
    def test_save_and_load(self, store, sample_episode):
        """Save and load episode."""
        store.save(sample_episode)
        loaded = store.load(sample_episode.correlation_id)
        
        assert loaded is not None
        assert loaded.correlation_id == sample_episode.correlation_id
    
    def test_load_nonexistent(self, store):
        """Load nonexistent episode returns None."""
        loaded = store.load(uuid4())
        assert loaded is None
    
    def test_exists(self, store, sample_episode):
        """Check existence."""
        assert store.exists(sample_episode.correlation_id) is False
        store.save(sample_episode)
        assert store.exists(sample_episode.correlation_id) is True
    
    def test_delete(self, store, sample_episode):
        """Delete episode."""
        store.save(sample_episode)
        assert store.delete(sample_episode.correlation_id) is True
        assert store.exists(sample_episode.correlation_id) is False
    
    def test_delete_nonexistent(self, store):
        """Delete nonexistent returns False."""
        assert store.delete(uuid4()) is False
    
    def test_query_by_template(self, store):
        """Query by template ID."""
        ep1 = EpisodeRecord(correlation_id=uuid4(), template_id="A", started_at=datetime.now(), success=True)
        ep2 = EpisodeRecord(correlation_id=uuid4(), template_id="B", started_at=datetime.now(), success=True)
        store.save(ep1)
        store.save(ep2)
        
        results = store.query(template_id="A")
        assert len(results) == 1
        assert results[0].template_id == "A"
    
    def test_query_by_success(self, store):
        """Query by success status."""
        ep1 = EpisodeRecord(correlation_id=uuid4(), template_id="A", started_at=datetime.now(), success=True)
        ep2 = EpisodeRecord(correlation_id=uuid4(), template_id="A", started_at=datetime.now(), success=False)
        store.save(ep1)
        store.save(ep2)
        
        successes = store.query(success=True)
        failures = store.query(success=False)
        
        assert len(successes) == 1
        assert len(failures) == 1
    
    def test_query_by_campaign(self, store):
        """Query by campaign ID."""
        ep1 = EpisodeRecord(correlation_id=uuid4(), template_id="A", campaign_id="campaign_1", started_at=datetime.now(), success=True)
        ep2 = EpisodeRecord(correlation_id=uuid4(), template_id="A", campaign_id="campaign_2", started_at=datetime.now(), success=True)
        store.save(ep1)
        store.save(ep2)
        
        results = store.query(campaign_id="campaign_1")
        assert len(results) == 1
        assert results[0].campaign_id == "campaign_1"
    
    def test_query_limit(self, store):
        """Query respects limit."""
        for i in range(10):
            ep = EpisodeRecord(
                correlation_id=uuid4(),
                template_id="A",
                started_at=datetime.now(),
                success=True,
            )
            store.save(ep)
        
        results = store.query(limit=5)
        assert len(results) == 5
    
    def test_count(self, store, sample_episode):
        """Count episodes."""
        assert store.count() == 0
        store.save(sample_episode)
        assert store.count() == 1
    
    def test_clear(self, store, sample_episode):
        """Clear all episodes."""
        store.save(sample_episode)
        assert store.count() == 1
        store.clear()
        assert store.count() == 0


class TestSQLiteStore:
    """Tests for SQLite storage."""
    
    @pytest.fixture
    def store(self, tmp_path):
        db_path = tmp_path / "test_episodes.db"
        return create_sqlite_store(db_path)
    
    @pytest.fixture
    def sample_episode(self):
        return EpisodeRecord(
            correlation_id=uuid4(),
            template_id="TEMPLATE_A",
            started_at=datetime.now(),
            completed_at=datetime.now(),
            success=True,
        )
    
    def test_save_and_load(self, store, sample_episode):
        """Save and load with SQLite."""
        store.save(sample_episode)
        loaded = store.load(sample_episode.correlation_id)
        
        assert loaded is not None
        assert loaded.template_id == sample_episode.template_id
    
    def test_load_nonexistent(self, store):
        """Load nonexistent episode returns None."""
        loaded = store.load(uuid4())
        assert loaded is None
    
    def test_persistence(self, tmp_path, sample_episode):
        """Data persists across store instances."""
        db_path = tmp_path / "persist.db"
        
        # Save with one instance
        store1 = create_sqlite_store(db_path)
        store1.save(sample_episode)
        
        # Load with another instance
        store2 = create_sqlite_store(db_path)
        loaded = store2.load(sample_episode.correlation_id)
        
        assert loaded is not None
        assert loaded.correlation_id == sample_episode.correlation_id
    
    def test_update_episode(self, store, sample_episode):
        """Update existing episode."""
        store.save(sample_episode)
        
        # Update the episode
        sample_episode.success = False
        sample_episode.errors.append("new error")
        store.save(sample_episode)
        
        # Load and verify update
        loaded = store.load(sample_episode.correlation_id)
        assert loaded.success is False
        assert "new error" in loaded.errors
    
    def test_exists(self, store, sample_episode):
        """Check existence."""
        assert store.exists(sample_episode.correlation_id) is False
        store.save(sample_episode)
        assert store.exists(sample_episode.correlation_id) is True
    
    def test_delete(self, store, sample_episode):
        """Delete episode."""
        store.save(sample_episode)
        assert store.delete(sample_episode.correlation_id) is True
        assert store.exists(sample_episode.correlation_id) is False
    
    def test_query_with_dates(self, store):
        """Query with date filters."""
        now = datetime.now()
        old = now - timedelta(days=7)
        
        ep_old = EpisodeRecord(correlation_id=uuid4(), template_id="A", started_at=old, success=True)
        ep_new = EpisodeRecord(correlation_id=uuid4(), template_id="A", started_at=now, success=True)
        store.save(ep_old)
        store.save(ep_new)
        
        recent = store.query(since=now - timedelta(days=1))
        assert len(recent) == 1
        
        all_time = store.query(since=old - timedelta(days=1))
        assert len(all_time) == 2
    
    def test_query_until(self, store):
        """Query with until filter."""
        now = datetime.now()
        future = now + timedelta(days=1)
        
        ep = EpisodeRecord(correlation_id=uuid4(), template_id="A", started_at=now, success=True)
        store.save(ep)
        
        results = store.query(until=future)
        assert len(results) == 1
        
        results = store.query(until=now - timedelta(days=1))
        assert len(results) == 0
    
    def test_query_limit(self, store):
        """Query respects limit."""
        for i in range(10):
            ep = EpisodeRecord(
                correlation_id=uuid4(),
                template_id="A",
                started_at=datetime.now(),
                success=True,
            )
            store.save(ep)
        
        results = store.query(limit=5)
        assert len(results) == 5
    
    def test_query_sorted_by_date(self, store):
        """Query returns results sorted by date descending."""
        old = datetime.now() - timedelta(days=2)
        mid = datetime.now() - timedelta(days=1)
        new = datetime.now()
        
        ep1 = EpisodeRecord(correlation_id=uuid4(), template_id="A", started_at=old, success=True)
        ep2 = EpisodeRecord(correlation_id=uuid4(), template_id="A", started_at=mid, success=True)
        ep3 = EpisodeRecord(correlation_id=uuid4(), template_id="A", started_at=new, success=True)
        
        # Save in random order
        store.save(ep2)
        store.save(ep1)
        store.save(ep3)
        
        results = store.query()
        assert len(results) == 3
        assert results[0].started_at >= results[1].started_at
        assert results[1].started_at >= results[2].started_at
    
    def test_count(self, store, sample_episode):
        """Count episodes."""
        assert store.count() == 0
        store.save(sample_episode)
        assert store.count() == 1
    
    def test_clear(self, store, sample_episode):
        """Clear all episodes."""
        store.save(sample_episode)
        assert store.count() == 1
        store.clear()
        assert store.count() == 0
