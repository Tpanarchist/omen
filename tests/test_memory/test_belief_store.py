"""Tests for belief store."""

import pytest
from datetime import datetime, timedelta
from pathlib import Path

from omen.memory import (
    BeliefEntry,
    InMemoryBeliefStore,
    SQLiteBeliefStore,
    create_memory_store,
    create_sqlite_store,
)


class TestInMemoryBeliefStore:
    """Tests for in-memory belief storage."""
    
    @pytest.fixture
    def store(self):
        return create_memory_store()
    
    @pytest.fixture
    def sample_belief(self):
        return BeliefEntry(
            belief_id="belief_001",
            domain="test_domain",
            claim="Test claim",
            confidence=0.95,
            evidence_refs=["evidence_1", "evidence_2"],
        )
    
    def test_create_and_load(self, store, sample_belief):
        """Create and load belief."""
        created = store.create(sample_belief)
        loaded = store.load(sample_belief.belief_id)
        
        assert loaded is not None
        assert loaded.belief_id == sample_belief.belief_id
        assert loaded.domain == sample_belief.domain
        assert loaded.claim == sample_belief.claim
        assert loaded.confidence == sample_belief.confidence
        assert loaded.evidence_refs == sample_belief.evidence_refs
        assert loaded.version == 1
    
    def test_create_duplicate_raises_error(self, store, sample_belief):
        """Creating duplicate belief raises ValueError."""
        store.create(sample_belief)
        with pytest.raises(ValueError, match="Belief already exists"):
            store.create(sample_belief)
    
    def test_load_nonexistent(self, store):
        """Load nonexistent belief returns None."""
        loaded = store.load("nonexistent_id")
        assert loaded is None
    
    def test_exists(self, store, sample_belief):
        """Check existence."""
        assert store.exists(sample_belief.belief_id) is False
        store.create(sample_belief)
        assert store.exists(sample_belief.belief_id) is True
    
    def test_update(self, store, sample_belief):
        """Update belief creates new version."""
        store.create(sample_belief)
        
        updated = store.update(
            sample_belief.belief_id,
            claim="Updated claim",
            confidence=0.98,
        )
        
        assert updated is not None
        assert updated.version == 2
        assert updated.claim == "Updated claim"
        assert updated.confidence == 0.98
        assert updated.domain == sample_belief.domain  # unchanged
        assert updated.belief_id == sample_belief.belief_id
    
    def test_update_nonexistent(self, store):
        """Update nonexistent belief returns None."""
        updated = store.update("nonexistent_id", claim="New claim")
        assert updated is None
    
    def test_versioning(self, store, sample_belief):
        """Test version history."""
        # Create initial version
        v1 = store.create(sample_belief)
        assert v1.version == 1
        
        # Update to create version 2
        v2 = store.update(sample_belief.belief_id, claim="Version 2")
        assert v2.version == 2
        
        # Update to create version 3
        v3 = store.update(sample_belief.belief_id, claim="Version 3")
        assert v3.version == 3
        
        # Load without version returns latest
        latest = store.load(sample_belief.belief_id)
        assert latest.version == 3
        assert latest.claim == "Version 3"
        
        # Load specific versions
        loaded_v1 = store.load(sample_belief.belief_id, version=1)
        assert loaded_v1.version == 1
        assert loaded_v1.claim == sample_belief.claim
        
        loaded_v2 = store.load(sample_belief.belief_id, version=2)
        assert loaded_v2.version == 2
        assert loaded_v2.claim == "Version 2"
    
    def test_load_nonexistent_version(self, store, sample_belief):
        """Load nonexistent version returns None."""
        store.create(sample_belief)
        loaded = store.load(sample_belief.belief_id, version=99)
        assert loaded is None
    
    def test_delete(self, store, sample_belief):
        """Delete belief."""
        store.create(sample_belief)
        assert store.delete(sample_belief.belief_id) is True
        assert store.exists(sample_belief.belief_id) is False
    
    def test_delete_nonexistent(self, store):
        """Delete nonexistent returns False."""
        assert store.delete("nonexistent_id") is False
    
    def test_query_by_domain(self, store):
        """Query by domain."""
        b1 = BeliefEntry(belief_id="b1", domain="domain_a", claim="Claim A", confidence=0.9)
        b2 = BeliefEntry(belief_id="b2", domain="domain_b", claim="Claim B", confidence=0.9)
        b3 = BeliefEntry(belief_id="b3", domain="domain_a", claim="Claim A2", confidence=0.9)
        
        store.create(b1)
        store.create(b2)
        store.create(b3)
        
        results = store.query(domain="domain_a")
        assert len(results) == 2
        assert all(b.domain == "domain_a" for b in results)
    
    def test_query_by_since(self, store):
        """Query by since filter."""
        now = datetime.utcnow()
        old_time = now - timedelta(days=7)
        
        # Create belief with old timestamp
        b1 = BeliefEntry(
            belief_id="b1",
            domain="test",
            claim="Old",
            confidence=0.9,
            created_at=old_time,
            updated_at=old_time,
        )
        store.create(b1)
        
        # Create belief with current timestamp
        b2 = BeliefEntry(belief_id="b2", domain="test", claim="New", confidence=0.9)
        store.create(b2)
        
        # Query for recent beliefs
        recent = store.query(since=now - timedelta(days=1))
        assert len(recent) == 1
        assert recent[0].belief_id == "b2"
        
        # Query for all beliefs
        all_beliefs = store.query(since=old_time - timedelta(days=1))
        assert len(all_beliefs) == 2
    
    def test_query_by_until(self, store):
        """Query by until filter."""
        now = datetime.utcnow()
        future = now + timedelta(days=1)
        
        b = BeliefEntry(belief_id="b1", domain="test", claim="Test", confidence=0.9)
        store.create(b)
        
        # Should include the belief
        results = store.query(until=future)
        assert len(results) == 1
        
        # Should exclude the belief
        results = store.query(until=now - timedelta(days=1))
        assert len(results) == 0
    
    def test_query_limit(self, store):
        """Query respects limit."""
        for i in range(10):
            b = BeliefEntry(
                belief_id=f"belief_{i}",
                domain="test",
                claim=f"Claim {i}",
                confidence=0.9,
            )
            store.create(b)
        
        results = store.query(limit=5)
        assert len(results) == 5
    
    def test_query_sorted_by_updated_at(self, store):
        """Query returns results sorted by updated_at descending."""
        old = datetime.utcnow() - timedelta(days=2)
        mid = datetime.utcnow() - timedelta(days=1)
        new = datetime.utcnow()
        
        b1 = BeliefEntry(
            belief_id="b1",
            domain="test",
            claim="Old",
            confidence=0.9,
            created_at=old,
            updated_at=old,
        )
        b2 = BeliefEntry(
            belief_id="b2",
            domain="test",
            claim="Mid",
            confidence=0.9,
            created_at=mid,
            updated_at=mid,
        )
        b3 = BeliefEntry(
            belief_id="b3",
            domain="test",
            claim="New",
            confidence=0.9,
            created_at=new,
            updated_at=new,
        )
        
        # Create in random order
        store.create(b2)
        store.create(b1)
        store.create(b3)
        
        results = store.query()
        assert len(results) == 3
        assert results[0].updated_at >= results[1].updated_at
        assert results[1].updated_at >= results[2].updated_at
    
    def test_clear(self, store, sample_belief):
        """Clear all beliefs."""
        store.create(sample_belief)
        assert store.exists(sample_belief.belief_id) is True
        
        store.clear()
        assert store.exists(sample_belief.belief_id) is False
    
    def test_update_preserves_created_at(self, store, sample_belief):
        """Update preserves original created_at timestamp."""
        created = store.create(sample_belief)
        original_created_at = created.created_at
        
        updated = store.update(sample_belief.belief_id, claim="Updated")
        assert updated.created_at == original_created_at
        assert updated.updated_at > original_created_at
    
    def test_update_evidence_refs(self, store, sample_belief):
        """Update evidence references."""
        store.create(sample_belief)
        
        new_evidence = ["new_evidence_1", "new_evidence_2", "new_evidence_3"]
        updated = store.update(sample_belief.belief_id, evidence_refs=new_evidence)
        
        assert updated.evidence_refs == new_evidence
    
    def test_query_returns_latest_version_only(self, store, sample_belief):
        """Query returns only the latest version of beliefs."""
        store.create(sample_belief)
        store.update(sample_belief.belief_id, claim="Version 2")
        store.update(sample_belief.belief_id, claim="Version 3")
        
        results = store.query()
        assert len(results) == 1
        assert results[0].version == 3
        assert results[0].claim == "Version 3"


class TestSQLiteBeliefStore:
    """Tests for SQLite belief storage."""
    
    @pytest.fixture
    def store(self, tmp_path):
        db_path = tmp_path / "test_beliefs.db"
        return create_sqlite_store(db_path)
    
    @pytest.fixture
    def sample_belief(self):
        return BeliefEntry(
            belief_id="belief_001",
            domain="test_domain",
            claim="Test claim",
            confidence=0.95,
            evidence_refs=["evidence_1", "evidence_2"],
        )
    
    def test_database_initialization(self, tmp_path):
        """Database and schema are initialized correctly."""
        db_path = tmp_path / "init_test.db"
        store = create_sqlite_store(db_path)
        
        # Verify database file exists
        assert db_path.exists()
        
        # Verify we can create a belief (schema exists)
        belief = BeliefEntry(
            belief_id="test",
            domain="test",
            claim="Test",
            confidence=0.9,
        )
        created = store.create(belief)
        assert created is not None
    
    def test_create_and_load(self, store, sample_belief):
        """Create and load with SQLite."""
        created = store.create(sample_belief)
        loaded = store.load(sample_belief.belief_id)
        
        assert loaded is not None
        assert loaded.belief_id == sample_belief.belief_id
        assert loaded.domain == sample_belief.domain
        assert loaded.claim == sample_belief.claim
        assert loaded.confidence == sample_belief.confidence
        assert loaded.evidence_refs == sample_belief.evidence_refs
        assert loaded.version == 1
    
    def test_create_duplicate_raises_error(self, store, sample_belief):
        """Creating duplicate belief raises ValueError."""
        store.create(sample_belief)
        with pytest.raises(ValueError, match="Belief already exists"):
            store.create(sample_belief)
    
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
        assert loaded.claim == sample_belief.claim
    
    def test_exists(self, store, sample_belief):
        """Check existence."""
        assert store.exists(sample_belief.belief_id) is False
        store.create(sample_belief)
        assert store.exists(sample_belief.belief_id) is True
    
    def test_update(self, store, sample_belief):
        """Update belief creates new version."""
        store.create(sample_belief)
        
        updated = store.update(
            sample_belief.belief_id,
            claim="Updated claim",
            confidence=0.98,
        )
        
        assert updated is not None
        assert updated.version == 2
        assert updated.claim == "Updated claim"
        assert updated.confidence == 0.98
        assert updated.domain == sample_belief.domain  # unchanged
    
    def test_update_nonexistent(self, store):
        """Update nonexistent belief returns None."""
        updated = store.update("nonexistent_id", claim="New claim")
        assert updated is None
    
    def test_versioning(self, store, sample_belief):
        """Test version history with SQLite."""
        # Create initial version
        v1 = store.create(sample_belief)
        assert v1.version == 1
        
        # Update to create version 2
        v2 = store.update(sample_belief.belief_id, claim="Version 2")
        assert v2.version == 2
        
        # Update to create version 3
        v3 = store.update(sample_belief.belief_id, claim="Version 3")
        assert v3.version == 3
        
        # Load without version returns latest
        latest = store.load(sample_belief.belief_id)
        assert latest.version == 3
        assert latest.claim == "Version 3"
        
        # Load specific versions
        loaded_v1 = store.load(sample_belief.belief_id, version=1)
        assert loaded_v1.version == 1
        assert loaded_v1.claim == sample_belief.claim
        
        loaded_v2 = store.load(sample_belief.belief_id, version=2)
        assert loaded_v2.version == 2
        assert loaded_v2.claim == "Version 2"
    
    def test_load_nonexistent_version(self, store, sample_belief):
        """Load nonexistent version returns None."""
        store.create(sample_belief)
        loaded = store.load(sample_belief.belief_id, version=99)
        assert loaded is None
    
    def test_delete(self, store, sample_belief):
        """Delete belief."""
        store.create(sample_belief)
        assert store.delete(sample_belief.belief_id) is True
        assert store.exists(sample_belief.belief_id) is False
    
    def test_delete_nonexistent(self, store):
        """Delete nonexistent returns False."""
        assert store.delete("nonexistent_id") is False
    
    def test_query_by_domain(self, store):
        """Query by domain with SQLite."""
        b1 = BeliefEntry(belief_id="b1", domain="domain_a", claim="Claim A", confidence=0.9)
        b2 = BeliefEntry(belief_id="b2", domain="domain_b", claim="Claim B", confidence=0.9)
        b3 = BeliefEntry(belief_id="b3", domain="domain_a", claim="Claim A2", confidence=0.9)
        
        store.create(b1)
        store.create(b2)
        store.create(b3)
        
        results = store.query(domain="domain_a")
        assert len(results) == 2
        assert all(b.domain == "domain_a" for b in results)
    
    def test_query_by_since(self, store):
        """Query by since filter with SQLite."""
        now = datetime.utcnow()
        old_time = now - timedelta(days=7)
        
        # Create belief with old timestamp
        b1 = BeliefEntry(
            belief_id="b1",
            domain="test",
            claim="Old",
            confidence=0.9,
            created_at=old_time,
            updated_at=old_time,
        )
        store.create(b1)
        
        # Create belief with current timestamp
        b2 = BeliefEntry(belief_id="b2", domain="test", claim="New", confidence=0.9)
        store.create(b2)
        
        # Query for recent beliefs
        recent = store.query(since=now - timedelta(days=1))
        assert len(recent) == 1
        assert recent[0].belief_id == "b2"
        
        # Query for all beliefs
        all_beliefs = store.query(since=old_time - timedelta(days=1))
        assert len(all_beliefs) == 2
    
    def test_query_by_until(self, store):
        """Query by until filter with SQLite."""
        now = datetime.utcnow()
        future = now + timedelta(days=1)
        
        b = BeliefEntry(belief_id="b1", domain="test", claim="Test", confidence=0.9)
        store.create(b)
        
        # Should include the belief
        results = store.query(until=future)
        assert len(results) == 1
        
        # Should exclude the belief
        results = store.query(until=now - timedelta(days=1))
        assert len(results) == 0
    
    def test_query_with_multiple_filters(self, store):
        """Query with multiple filters combined."""
        now = datetime.utcnow()
        old = now - timedelta(days=7)
        
        b1 = BeliefEntry(
            belief_id="b1",
            domain="domain_a",
            claim="Old A",
            confidence=0.9,
            created_at=old,
            updated_at=old,
        )
        b2 = BeliefEntry(belief_id="b2", domain="domain_b", claim="New B", confidence=0.9)
        b3 = BeliefEntry(belief_id="b3", domain="domain_a", claim="New A", confidence=0.9)
        
        store.create(b1)
        store.create(b2)
        store.create(b3)
        
        # Query for domain_a beliefs updated in the last day
        results = store.query(
            domain="domain_a",
            since=now - timedelta(days=1),
        )
        assert len(results) == 1
        assert results[0].belief_id == "b3"
    
    def test_query_limit(self, store):
        """Query respects limit with SQLite."""
        for i in range(10):
            b = BeliefEntry(
                belief_id=f"belief_{i}",
                domain="test",
                claim=f"Claim {i}",
                confidence=0.9,
            )
            store.create(b)
        
        results = store.query(limit=5)
        assert len(results) == 5
    
    def test_query_sorted_by_updated_at(self, store):
        """Query returns results sorted by updated_at descending."""
        old = datetime.utcnow() - timedelta(days=2)
        mid = datetime.utcnow() - timedelta(days=1)
        new = datetime.utcnow()
        
        b1 = BeliefEntry(
            belief_id="b1",
            domain="test",
            claim="Old",
            confidence=0.9,
            created_at=old,
            updated_at=old,
        )
        b2 = BeliefEntry(
            belief_id="b2",
            domain="test",
            claim="Mid",
            confidence=0.9,
            created_at=mid,
            updated_at=mid,
        )
        b3 = BeliefEntry(
            belief_id="b3",
            domain="test",
            claim="New",
            confidence=0.9,
            created_at=new,
            updated_at=new,
        )
        
        # Create in random order
        store.create(b2)
        store.create(b1)
        store.create(b3)
        
        results = store.query()
        assert len(results) == 3
        assert results[0].updated_at >= results[1].updated_at
        assert results[1].updated_at >= results[2].updated_at
    
    def test_clear(self, store, sample_belief):
        """Clear all beliefs."""
        store.create(sample_belief)
        assert store.exists(sample_belief.belief_id) is True
        
        store.clear()
        assert store.exists(sample_belief.belief_id) is False
    
    def test_update_preserves_created_at(self, store, sample_belief):
        """Update preserves original created_at timestamp."""
        created = store.create(sample_belief)
        original_created_at = created.created_at
        
        updated = store.update(sample_belief.belief_id, claim="Updated")
        assert updated.created_at == original_created_at
        assert updated.updated_at > original_created_at
    
    def test_update_evidence_refs(self, store, sample_belief):
        """Update evidence references with SQLite."""
        store.create(sample_belief)
        
        new_evidence = ["new_evidence_1", "new_evidence_2", "new_evidence_3"]
        updated = store.update(sample_belief.belief_id, evidence_refs=new_evidence)
        
        assert updated.evidence_refs == new_evidence
    
    def test_query_returns_latest_version_only(self, store, sample_belief):
        """Query returns only the latest version of beliefs."""
        store.create(sample_belief)
        store.update(sample_belief.belief_id, claim="Version 2")
        store.update(sample_belief.belief_id, claim="Version 3")
        
        results = store.query()
        assert len(results) == 1
        assert results[0].version == 3
        assert results[0].claim == "Version 3"
    
    def test_version_persistence(self, tmp_path, sample_belief):
        """Version history persists across store instances."""
        db_path = tmp_path / "version_persist.db"
        
        # Create and update with first instance
        store1 = create_sqlite_store(db_path)
        store1.create(sample_belief)
        store1.update(sample_belief.belief_id, claim="Version 2")
        store1.update(sample_belief.belief_id, claim="Version 3")
        
        # Load versions with second instance
        store2 = create_sqlite_store(db_path)
        v1 = store2.load(sample_belief.belief_id, version=1)
        v2 = store2.load(sample_belief.belief_id, version=2)
        v3 = store2.load(sample_belief.belief_id, version=3)
        latest = store2.load(sample_belief.belief_id)
        
        assert v1.version == 1
        assert v2.version == 2
        assert v3.version == 3
        assert latest.version == 3
        assert v1.claim == sample_belief.claim
        assert v2.claim == "Version 2"
        assert v3.claim == "Version 3"
