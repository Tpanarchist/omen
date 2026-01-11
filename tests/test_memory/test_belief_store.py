"""Tests for belief store."""

import pytest
from datetime import datetime, timedelta
from pathlib import Path

from omen.memory.belief_store import (
    BeliefEntry,
    InMemoryBeliefStore,
    SQLiteBeliefStore,
    create_memory_store,
    create_sqlite_store,
)


class TestInMemoryBeliefStore:
    """Tests for in-memory belief store."""
    
    @pytest.fixture
    def store(self):
        return create_memory_store()
    
    @pytest.fixture
    def sample_belief(self):
        return BeliefEntry(
            belief_id="belief_001",
            domain="test_domain",
            claim="Sample claim for testing",
            confidence=0.85,
            evidence_refs=["evidence_1", "evidence_2"],
        )
    
    def test_create_belief(self, store, sample_belief):
        """Create a new belief entry."""
        created = store.create(sample_belief)
        
        assert created is not None
        assert created.belief_id == sample_belief.belief_id
        assert created.version == 1
        assert created.domain == sample_belief.domain
        assert created.claim == sample_belief.claim
        assert created.confidence == sample_belief.confidence
    
    def test_create_duplicate_raises_error(self, store, sample_belief):
        """Creating duplicate belief raises ValueError."""
        store.create(sample_belief)
        
        with pytest.raises(ValueError, match="Belief already exists"):
            store.create(sample_belief)
    
    def test_load_belief(self, store, sample_belief):
        """Load a belief by ID."""
        store.create(sample_belief)
        loaded = store.load(sample_belief.belief_id)
        
        assert loaded is not None
        assert loaded.belief_id == sample_belief.belief_id
        assert loaded.domain == sample_belief.domain
    
    def test_load_nonexistent(self, store):
        """Load nonexistent belief returns None."""
        loaded = store.load("nonexistent_id")
        assert loaded is None
    
    def test_load_specific_version(self, store, sample_belief):
        """Load a specific version of a belief."""
        store.create(sample_belief)
        store.update(sample_belief.belief_id, claim="Updated claim")
        
        # Load version 1
        v1 = store.load(sample_belief.belief_id, version=1)
        assert v1 is not None
        assert v1.version == 1
        assert v1.claim == sample_belief.claim
        
        # Load version 2
        v2 = store.load(sample_belief.belief_id, version=2)
        assert v2 is not None
        assert v2.version == 2
        assert v2.claim == "Updated claim"
    
    def test_load_latest_version(self, store, sample_belief):
        """Load without version returns latest version."""
        store.create(sample_belief)
        store.update(sample_belief.belief_id, claim="Updated claim")
        store.update(sample_belief.belief_id, claim="Another update")
        
        latest = store.load(sample_belief.belief_id)
        assert latest is not None
        assert latest.version == 3
        assert latest.claim == "Another update"
    
    def test_update_belief_creates_new_version(self, store, sample_belief):
        """Update creates a new version."""
        store.create(sample_belief)
        
        updated = store.update(
            sample_belief.belief_id,
            claim="Updated claim",
            confidence=0.95,
        )
        
        assert updated is not None
        assert updated.version == 2
        assert updated.claim == "Updated claim"
        assert updated.confidence == 0.95
        assert updated.domain == sample_belief.domain  # unchanged
    
    def test_update_nonexistent_returns_none(self, store):
        """Update nonexistent belief returns None."""
        result = store.update("nonexistent_id", claim="New claim")
        assert result is None
    
    def test_update_preserves_created_at(self, store, sample_belief):
        """Update preserves the original created_at timestamp."""
        created = store.create(sample_belief)
        original_created_at = created.created_at
        
        updated = store.update(sample_belief.belief_id, claim="Updated")
        
        assert updated.created_at == original_created_at
        assert updated.updated_at > created.updated_at
    
    def test_update_evidence_refs(self, store, sample_belief):
        """Update evidence references."""
        store.create(sample_belief)
        
        new_evidence = ["evidence_3", "evidence_4", "evidence_5"]
        updated = store.update(sample_belief.belief_id, evidence_refs=new_evidence)
        
        assert updated is not None
        assert updated.evidence_refs == new_evidence
    
    def test_exists(self, store, sample_belief):
        """Check belief existence."""
        assert store.exists(sample_belief.belief_id) is False
        
        store.create(sample_belief)
        assert store.exists(sample_belief.belief_id) is True
    
    def test_delete_belief(self, store, sample_belief):
        """Delete a belief."""
        store.create(sample_belief)
        assert store.exists(sample_belief.belief_id) is True
        
        result = store.delete(sample_belief.belief_id)
        assert result is True
        assert store.exists(sample_belief.belief_id) is False
    
    def test_delete_nonexistent(self, store):
        """Delete nonexistent belief returns False."""
        result = store.delete("nonexistent_id")
        assert result is False
    
    def test_delete_removes_all_versions(self, store, sample_belief):
        """Delete removes all versions of a belief."""
        store.create(sample_belief)
        store.update(sample_belief.belief_id, claim="Version 2")
        store.update(sample_belief.belief_id, claim="Version 3")
        
        store.delete(sample_belief.belief_id)
        
        # All versions should be gone
        assert store.load(sample_belief.belief_id) is None
        assert store.load(sample_belief.belief_id, version=1) is None
        assert store.load(sample_belief.belief_id, version=2) is None
    
    def test_query_all(self, store):
        """Query all beliefs."""
        belief1 = BeliefEntry(belief_id="b1", domain="domain1", claim="Claim 1", confidence=0.8)
        belief2 = BeliefEntry(belief_id="b2", domain="domain2", claim="Claim 2", confidence=0.9)
        
        store.create(belief1)
        store.create(belief2)
        
        results = store.query()
        assert len(results) == 2
    
    def test_query_by_domain(self, store):
        """Query beliefs by domain."""
        belief1 = BeliefEntry(belief_id="b1", domain="domain1", claim="Claim 1", confidence=0.8)
        belief2 = BeliefEntry(belief_id="b2", domain="domain2", claim="Claim 2", confidence=0.9)
        belief3 = BeliefEntry(belief_id="b3", domain="domain1", claim="Claim 3", confidence=0.7)
        
        store.create(belief1)
        store.create(belief2)
        store.create(belief3)
        
        results = store.query(domain="domain1")
        assert len(results) == 2
        assert all(b.domain == "domain1" for b in results)
    
    def test_query_with_since_filter(self, store):
        """Query beliefs updated since a certain time."""
        now = datetime.utcnow()
        past = now - timedelta(days=2)
        
        belief1 = BeliefEntry(
            belief_id="b1",
            domain="domain1",
            claim="Old belief",
            confidence=0.8,
            created_at=past,
            updated_at=past,
        )
        belief2 = BeliefEntry(
            belief_id="b2",
            domain="domain1",
            claim="New belief",
            confidence=0.9,
            created_at=now,
            updated_at=now,
        )
        
        store.create(belief1)
        store.create(belief2)
        
        recent = store.query(since=now - timedelta(days=1))
        assert len(recent) == 1
        assert recent[0].belief_id == "b2"
    
    def test_query_with_until_filter(self, store):
        """Query beliefs updated until a certain time."""
        now = datetime.utcnow()
        past = now - timedelta(days=2)
        
        belief1 = BeliefEntry(
            belief_id="b1",
            domain="domain1",
            claim="Old belief",
            confidence=0.8,
            created_at=past,
            updated_at=past,
        )
        belief2 = BeliefEntry(
            belief_id="b2",
            domain="domain1",
            claim="New belief",
            confidence=0.9,
            created_at=now,
            updated_at=now,
        )
        
        store.create(belief1)
        store.create(belief2)
        
        old_beliefs = store.query(until=now - timedelta(days=1))
        assert len(old_beliefs) == 1
        assert old_beliefs[0].belief_id == "b1"
    
    def test_query_with_limit(self, store):
        """Query respects limit."""
        for i in range(10):
            belief = BeliefEntry(
                belief_id=f"belief_{i}",
                domain="test",
                claim=f"Claim {i}",
                confidence=0.8,
            )
            store.create(belief)
        
        results = store.query(limit=5)
        assert len(results) == 5
    
    def test_query_returns_latest_versions_only(self, store):
        """Query returns only the latest version of each belief."""
        belief = BeliefEntry(belief_id="b1", domain="domain1", claim="Original", confidence=0.8)
        store.create(belief)
        store.update("b1", claim="Updated v2")
        store.update("b1", claim="Updated v3")
        
        results = store.query()
        assert len(results) == 1
        assert results[0].version == 3
        assert results[0].claim == "Updated v3"
    
    def test_query_sorted_by_updated_at(self, store):
        """Query returns results sorted by updated_at descending."""
        now = datetime.utcnow()
        
        belief1 = BeliefEntry(
            belief_id="b1",
            domain="test",
            claim="First",
            confidence=0.8,
            created_at=now - timedelta(days=3),
            updated_at=now - timedelta(days=3),
        )
        belief2 = BeliefEntry(
            belief_id="b2",
            domain="test",
            claim="Second",
            confidence=0.8,
            created_at=now - timedelta(days=2),
            updated_at=now - timedelta(days=2),
        )
        belief3 = BeliefEntry(
            belief_id="b3",
            domain="test",
            claim="Third",
            confidence=0.8,
            created_at=now - timedelta(days=1),
            updated_at=now - timedelta(days=1),
        )
        
        # Create in non-sorted order
        store.create(belief2)
        store.create(belief1)
        store.create(belief3)
        
        results = store.query()
        assert len(results) == 3
        assert results[0].belief_id == "b3"  # most recent
        assert results[1].belief_id == "b2"
        assert results[2].belief_id == "b1"  # oldest
    
    def test_clear(self, store, sample_belief):
        """Clear all beliefs."""
        store.create(sample_belief)
        belief2 = BeliefEntry(belief_id="b2", domain="test", claim="Another", confidence=0.7)
        store.create(belief2)
        
        assert len(store.query()) == 2
        
        store.clear()
        
        assert len(store.query()) == 0
        assert store.exists(sample_belief.belief_id) is False


class TestSQLiteBeliefStore:
    """Tests for SQLite belief store."""
    
    @pytest.fixture
    def store(self, tmp_path):
        db_path = tmp_path / "test_beliefs.db"
        return create_sqlite_store(db_path)
    
    @pytest.fixture
    def sample_belief(self):
        return BeliefEntry(
            belief_id="belief_001",
            domain="test_domain",
            claim="Sample claim for testing",
            confidence=0.85,
            evidence_refs=["evidence_1", "evidence_2"],
        )
    
    def test_create_belief(self, store, sample_belief):
        """Create a new belief entry."""
        created = store.create(sample_belief)
        
        assert created is not None
        assert created.belief_id == sample_belief.belief_id
        assert created.version == 1
    
    def test_create_duplicate_raises_error(self, store, sample_belief):
        """Creating duplicate belief raises ValueError."""
        store.create(sample_belief)
        
        with pytest.raises(ValueError, match="Belief already exists"):
            store.create(sample_belief)
    
    def test_load_belief(self, store, sample_belief):
        """Load a belief by ID."""
        store.create(sample_belief)
        loaded = store.load(sample_belief.belief_id)
        
        assert loaded is not None
        assert loaded.belief_id == sample_belief.belief_id
        assert loaded.domain == sample_belief.domain
    
    def test_load_nonexistent(self, store):
        """Load nonexistent belief returns None."""
        loaded = store.load("nonexistent_id")
        assert loaded is None
    
    def test_persistence(self, tmp_path, sample_belief):
        """Data persists across store instances."""
        db_path = tmp_path / "persist.db"
        
        # Save with one instance
        store1 = create_sqlite_store(db_path)
        store1.create(sample_belief)
        
        # Load with another instance
        store2 = create_sqlite_store(db_path)
        loaded = store2.load(sample_belief.belief_id)
        
        assert loaded is not None
        assert loaded.belief_id == sample_belief.belief_id
        assert loaded.domain == sample_belief.domain
    
    def test_load_specific_version(self, store, sample_belief):
        """Load a specific version of a belief."""
        store.create(sample_belief)
        store.update(sample_belief.belief_id, claim="Updated claim")
        
        # Load version 1
        v1 = store.load(sample_belief.belief_id, version=1)
        assert v1 is not None
        assert v1.version == 1
        assert v1.claim == sample_belief.claim
        
        # Load version 2
        v2 = store.load(sample_belief.belief_id, version=2)
        assert v2 is not None
        assert v2.version == 2
        assert v2.claim == "Updated claim"
    
    def test_update_belief_creates_new_version(self, store, sample_belief):
        """Update creates a new version."""
        store.create(sample_belief)
        
        updated = store.update(
            sample_belief.belief_id,
            claim="Updated claim",
            confidence=0.95,
        )
        
        assert updated is not None
        assert updated.version == 2
        assert updated.claim == "Updated claim"
        assert updated.confidence == 0.95
    
    def test_update_nonexistent_returns_none(self, store):
        """Update nonexistent belief returns None."""
        result = store.update("nonexistent_id", claim="New claim")
        assert result is None
    
    def test_update_preserves_created_at(self, store, sample_belief):
        """Update preserves the original created_at timestamp."""
        created = store.create(sample_belief)
        original_created_at = created.created_at
        
        updated = store.update(sample_belief.belief_id, claim="Updated")
        
        assert updated.created_at == original_created_at
        assert updated.updated_at > created.updated_at
    
    def test_exists(self, store, sample_belief):
        """Check belief existence."""
        assert store.exists(sample_belief.belief_id) is False
        
        store.create(sample_belief)
        assert store.exists(sample_belief.belief_id) is True
    
    def test_delete_belief(self, store, sample_belief):
        """Delete a belief."""
        store.create(sample_belief)
        assert store.exists(sample_belief.belief_id) is True
        
        result = store.delete(sample_belief.belief_id)
        assert result is True
        assert store.exists(sample_belief.belief_id) is False
    
    def test_delete_nonexistent(self, store):
        """Delete nonexistent belief returns False."""
        result = store.delete("nonexistent_id")
        assert result is False
    
    def test_query_by_domain(self, store):
        """Query beliefs by domain."""
        belief1 = BeliefEntry(belief_id="b1", domain="domain1", claim="Claim 1", confidence=0.8)
        belief2 = BeliefEntry(belief_id="b2", domain="domain2", claim="Claim 2", confidence=0.9)
        belief3 = BeliefEntry(belief_id="b3", domain="domain1", claim="Claim 3", confidence=0.7)
        
        store.create(belief1)
        store.create(belief2)
        store.create(belief3)
        
        results = store.query(domain="domain1")
        assert len(results) == 2
        assert all(b.domain == "domain1" for b in results)
    
    def test_query_with_since_filter(self, store):
        """Query beliefs updated since a certain time."""
        now = datetime.utcnow()
        past = now - timedelta(days=2)
        
        belief1 = BeliefEntry(
            belief_id="b1",
            domain="domain1",
            claim="Old belief",
            confidence=0.8,
            created_at=past,
            updated_at=past,
        )
        belief2 = BeliefEntry(
            belief_id="b2",
            domain="domain1",
            claim="New belief",
            confidence=0.9,
            created_at=now,
            updated_at=now,
        )
        
        store.create(belief1)
        store.create(belief2)
        
        recent = store.query(since=now - timedelta(days=1))
        assert len(recent) == 1
        assert recent[0].belief_id == "b2"
    
    def test_query_with_until_filter(self, store):
        """Query beliefs updated until a certain time."""
        now = datetime.utcnow()
        past = now - timedelta(days=2)
        
        belief1 = BeliefEntry(
            belief_id="b1",
            domain="domain1",
            claim="Old belief",
            confidence=0.8,
            created_at=past,
            updated_at=past,
        )
        belief2 = BeliefEntry(
            belief_id="b2",
            domain="domain1",
            claim="New belief",
            confidence=0.9,
            created_at=now,
            updated_at=now,
        )
        
        store.create(belief1)
        store.create(belief2)
        
        old_beliefs = store.query(until=now - timedelta(days=1))
        assert len(old_beliefs) == 1
        assert old_beliefs[0].belief_id == "b1"
    
    def test_query_with_limit(self, store):
        """Query respects limit."""
        for i in range(10):
            belief = BeliefEntry(
                belief_id=f"belief_{i}",
                domain="test",
                claim=f"Claim {i}",
                confidence=0.8,
            )
            store.create(belief)
        
        results = store.query(limit=5)
        assert len(results) == 5
    
    def test_query_returns_latest_versions_only(self, store):
        """Query returns only the latest version of each belief."""
        belief = BeliefEntry(belief_id="b1", domain="domain1", claim="Original", confidence=0.8)
        store.create(belief)
        store.update("b1", claim="Updated v2")
        store.update("b1", claim="Updated v3")
        
        results = store.query()
        assert len(results) == 1
        assert results[0].version == 3
        assert results[0].claim == "Updated v3"
    
    def test_query_sorted_by_updated_at(self, store):
        """Query returns results sorted by updated_at descending."""
        now = datetime.utcnow()
        
        belief1 = BeliefEntry(
            belief_id="b1",
            domain="test",
            claim="First",
            confidence=0.8,
            created_at=now - timedelta(days=3),
            updated_at=now - timedelta(days=3),
        )
        belief2 = BeliefEntry(
            belief_id="b2",
            domain="test",
            claim="Second",
            confidence=0.8,
            created_at=now - timedelta(days=2),
            updated_at=now - timedelta(days=2),
        )
        belief3 = BeliefEntry(
            belief_id="b3",
            domain="test",
            claim="Third",
            confidence=0.8,
            created_at=now - timedelta(days=1),
            updated_at=now - timedelta(days=1),
        )
        
        # Create in non-sorted order
        store.create(belief2)
        store.create(belief1)
        store.create(belief3)
        
        results = store.query()
        assert len(results) == 3
        assert results[0].belief_id == "b3"  # most recent
        assert results[1].belief_id == "b2"
        assert results[2].belief_id == "b1"  # oldest
    
    def test_clear(self, store, sample_belief):
        """Clear all beliefs."""
        store.create(sample_belief)
        belief2 = BeliefEntry(belief_id="b2", domain="test", claim="Another", confidence=0.7)
        store.create(belief2)
        
        assert len(store.query()) == 2
        
        store.clear()
        
        assert len(store.query()) == 0
        assert store.exists(sample_belief.belief_id) is False
    
    def test_multiple_updates_preserve_all_versions(self, store, sample_belief):
        """Multiple updates create and preserve all versions in database."""
        store.create(sample_belief)
        store.update(sample_belief.belief_id, claim="Version 2")
        store.update(sample_belief.belief_id, claim="Version 3")
        
        # All versions should be accessible
        v1 = store.load(sample_belief.belief_id, version=1)
        v2 = store.load(sample_belief.belief_id, version=2)
        v3 = store.load(sample_belief.belief_id, version=3)
        
        assert v1 is not None and v1.claim == sample_belief.claim
        assert v2 is not None and v2.claim == "Version 2"
        assert v3 is not None and v3.claim == "Version 3"


class TestBeliefEntry:
    """Tests for BeliefEntry dataclass."""
    
    def test_to_json(self):
        """Serialize belief entry to JSON."""
        belief = BeliefEntry(
            belief_id="b1",
            domain="test",
            claim="Test claim",
            confidence=0.9,
            evidence_refs=["e1", "e2"],
        )
        
        json_str = belief.to_json()
        
        assert "belief_id" in json_str
        assert "b1" in json_str
        assert "test" in json_str
        assert "Test claim" in json_str
    
    def test_from_row(self):
        """Create belief entry from SQLite row."""
        now = datetime.utcnow()
        row = (
            "belief_001",  # belief_id
            2,  # version
            "test_domain",  # domain
            "Test claim",  # claim
            0.85,  # confidence
            '["e1", "e2"]',  # evidence_refs (JSON string)
            now.isoformat(),  # created_at
            now.isoformat(),  # updated_at
        )
        
        belief = BeliefEntry.from_row(row)
        
        assert belief.belief_id == "belief_001"
        assert belief.version == 2
        assert belief.domain == "test_domain"
        assert belief.claim == "Test claim"
        assert belief.confidence == 0.85
        assert belief.evidence_refs == ["e1", "e2"]
        assert isinstance(belief.created_at, datetime)
        assert isinstance(belief.updated_at, datetime)
    
    def test_immutability(self):
        """BeliefEntry is immutable (frozen dataclass)."""
        belief = BeliefEntry(
            belief_id="b1",
            domain="test",
            claim="Test",
            confidence=0.8,
        )
        
        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            belief.claim = "Modified"
