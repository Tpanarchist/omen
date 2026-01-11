"""Tests for semantic memory module."""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from omen.memory.semantic import (
    Belief,
    SemanticMemory,
    InMemorySemanticStore,
    SQLiteSemanticStore,
    create_semantic_store,
)


class TestBelief:
    """Test Belief data class."""
    
    def test_creation(self):
        """Test creating a belief."""
        belief = Belief(
            belief_id="test-123",
            domain="market_dynamics",
            claim="Jita is the most liquid market",
            confidence=0.95,
            evidence_refs=["esi_data_12345"],
            formed_from=["episode-uuid-1"],
        )
        
        assert belief.belief_id == "test-123"
        assert belief.domain == "market_dynamics"
        assert belief.confidence == 0.95
        assert len(belief.evidence_refs) == 1
    
    def test_serialization(self):
        """Test to_dict and from_dict."""
        original = Belief(
            belief_id="test-456",
            domain="combat",
            claim="PvP requires fast reactions",
            confidence=0.8,
        )
        
        data = original.to_dict()
        restored = Belief.from_dict(data)
        
        assert restored.belief_id == original.belief_id
        assert restored.claim == original.claim
        assert restored.confidence == original.confidence


class TestInMemorySemanticStore:
    """Test in-memory semantic store."""
    
    def test_save_and_load(self):
        """Test saving and loading beliefs."""
        store = InMemorySemanticStore()
        
        belief = Belief(
            belief_id="test-1",
            domain="testing",
            claim="Tests are important",
            confidence=1.0,
        )
        
        store.save(belief)
        loaded = store.load("test-1")
        
        assert loaded is not None
        assert loaded.belief_id == "test-1"
        assert loaded.claim == "Tests are important"
    
    def test_load_nonexistent(self):
        """Test loading nonexistent belief."""
        store = InMemorySemanticStore()
        loaded = store.load("nonexistent")
        assert loaded is None
    
    def test_query_by_domain(self):
        """Test querying by domain."""
        store = InMemorySemanticStore()
        
        store.save(Belief(
            belief_id="b1",
            domain="market",
            claim="Markets are volatile",
            confidence=0.8,
        ))
        store.save(Belief(
            belief_id="b2",
            domain="combat",
            claim="Combat is risky",
            confidence=0.9,
        ))
        store.save(Belief(
            belief_id="b3",
            domain="market",
            claim="Volume indicates activity",
            confidence=0.7,
        ))
        
        results = store.query(domain="market")
        assert len(results) == 2
        assert all(b.domain == "market" for b in results)
    
    def test_query_by_confidence(self):
        """Test querying by minimum confidence."""
        store = InMemorySemanticStore()
        
        store.save(Belief(
            belief_id="b1",
            domain="test",
            claim="Low confidence",
            confidence=0.3,
        ))
        store.save(Belief(
            belief_id="b2",
            domain="test",
            claim="High confidence",
            confidence=0.9,
        ))
        
        results = store.query(min_confidence=0.5)
        assert len(results) == 1
        assert results[0].confidence >= 0.5
    
    def test_query_by_text(self):
        """Test text search in claims."""
        store = InMemorySemanticStore()
        
        store.save(Belief(
            belief_id="b1",
            domain="test",
            claim="The market is efficient",
            confidence=0.8,
        ))
        store.save(Belief(
            belief_id="b2",
            domain="test",
            claim="Combat requires skill",
            confidence=0.9,
        ))
        
        results = store.query(query_text="market")
        assert len(results) == 1
        assert "market" in results[0].claim.lower()
    
    def test_query_sorted_by_confidence(self):
        """Test that results are sorted by confidence."""
        store = InMemorySemanticStore()
        
        store.save(Belief(belief_id="b1", domain="test", claim="Low", confidence=0.3))
        store.save(Belief(belief_id="b2", domain="test", claim="High", confidence=0.9))
        store.save(Belief(belief_id="b3", domain="test", claim="Med", confidence=0.6))
        
        results = store.query()
        assert results[0].confidence >= results[1].confidence
        assert results[1].confidence >= results[2].confidence
    
    def test_count(self):
        """Test counting beliefs."""
        store = InMemorySemanticStore()
        assert store.count() == 0
        
        store.save(Belief(belief_id="b1", domain="test", claim="Test", confidence=0.5))
        assert store.count() == 1
    
    def test_clear(self):
        """Test clearing all beliefs."""
        store = InMemorySemanticStore()
        
        store.save(Belief(belief_id="b1", domain="test", claim="Test", confidence=0.5))
        assert store.count() == 1
        
        store.clear()
        assert store.count() == 0


class TestSemanticMemory:
    """Test SemanticMemory operations."""
    
    def test_add_belief(self):
        """Test adding a new belief."""
        store = InMemorySemanticStore()
        memory = SemanticMemory(store)
        
        belief = memory.add_belief(
            domain="test",
            claim="Testing works",
            confidence=0.9,
            evidence_refs=["test-data"],
        )
        
        assert belief.belief_id is not None
        assert belief.domain == "test"
        assert belief.confidence == 0.9
        
        # Verify it was saved
        loaded = store.load(belief.belief_id)
        assert loaded is not None
    
    def test_update_belief(self):
        """Test updating an existing belief."""
        store = InMemorySemanticStore()
        memory = SemanticMemory(store)
        
        # Create initial belief
        belief = memory.add_belief(
            domain="test",
            claim="Initial claim",
            confidence=0.5,
        )
        
        original_version = belief.version
        
        # Update it
        updated = memory.update_belief(
            belief_id=belief.belief_id,
            confidence=0.9,
            new_evidence=["new-data"],
            new_episode="episode-123",
        )
        
        assert updated is not None
        assert updated.confidence == 0.9
        assert "new-data" in updated.evidence_refs
        assert "episode-123" in updated.formed_from
        assert updated.version == original_version + 1
    
    def test_update_nonexistent_belief(self):
        """Test updating nonexistent belief returns None."""
        store = InMemorySemanticStore()
        memory = SemanticMemory(store)
        
        result = memory.update_belief("nonexistent", confidence=0.9)
        assert result is None
    
    def test_get_domain_beliefs(self):
        """Test getting beliefs for a domain."""
        store = InMemorySemanticStore()
        memory = SemanticMemory(store)
        
        memory.add_belief(domain="market", claim="Claim 1", confidence=0.8)
        memory.add_belief(domain="market", claim="Claim 2", confidence=0.6)
        memory.add_belief(domain="combat", claim="Claim 3", confidence=0.9)
        
        market_beliefs = memory.get_domain_beliefs("market")
        assert len(market_beliefs) == 2
        assert all(b.domain == "market" for b in market_beliefs)
    
    def test_get_domain_beliefs_with_min_confidence(self):
        """Test filtering by confidence."""
        store = InMemorySemanticStore()
        memory = SemanticMemory(store)
        
        memory.add_belief(domain="test", claim="Low", confidence=0.3)
        memory.add_belief(domain="test", claim="High", confidence=0.9)
        
        high_confidence = memory.get_domain_beliefs("test", min_confidence=0.5)
        assert len(high_confidence) == 1
        assert high_confidence[0].confidence >= 0.5


class TestSQLiteSemanticStore:
    """Test SQLite semantic store."""
    
    def test_save_and_load(self):
        """Test SQLite save and load."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        try:
            store = SQLiteSemanticStore(db_path)
            
            belief = Belief(
                belief_id="test-1",
                domain="test",
                claim="SQLite works",
                confidence=0.95,
            )
            
            store.save(belief)
            loaded = store.load("test-1")
            
            assert loaded is not None
            assert loaded.belief_id == "test-1"
            assert loaded.claim == "SQLite works"
        finally:
            Path(db_path).unlink(missing_ok=True)
    
    def test_persistence(self):
        """Test data persists across instances."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        try:
            # Save with first instance
            store1 = SQLiteSemanticStore(db_path)
            store1.save(Belief(
                belief_id="persist-1",
                domain="test",
                claim="Persistent",
                confidence=0.9,
            ))
            
            # Load with second instance
            store2 = SQLiteSemanticStore(db_path)
            loaded = store2.load("persist-1")
            
            assert loaded is not None
            assert loaded.claim == "Persistent"
        finally:
            Path(db_path).unlink(missing_ok=True)
    
    def test_query(self):
        """Test SQLite query."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        try:
            store = SQLiteSemanticStore(db_path)
            
            store.save(Belief(belief_id="b1", domain="market", claim="A", confidence=0.8))
            store.save(Belief(belief_id="b2", domain="market", claim="B", confidence=0.6))
            store.save(Belief(belief_id="b3", domain="combat", claim="C", confidence=0.9))
            
            results = store.query(domain="market", min_confidence=0.7)
            assert len(results) == 1
            assert results[0].confidence >= 0.7
        finally:
            Path(db_path).unlink(missing_ok=True)


class TestSemanticStoreFactory:
    """Test factory function."""
    
    def test_create_memory_store(self):
        """Test creating in-memory store."""
        store = create_semantic_store("memory")
        assert isinstance(store, InMemorySemanticStore)
    
    def test_create_sqlite_store(self):
        """Test creating SQLite store."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        try:
            store = create_semantic_store("sqlite", db_path)
            assert isinstance(store, SQLiteSemanticStore)
        finally:
            Path(db_path).unlink(missing_ok=True)
    
    def test_invalid_backend(self):
        """Test invalid backend raises error."""
        with pytest.raises(ValueError):
            create_semantic_store("invalid")
