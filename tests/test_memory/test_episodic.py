"""Tests for episodic memory module."""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from omen.memory.episodic import (
    EpisodicMemory,
    InMemoryEpisodicStore,
    SQLiteEpisodicStore,
    create_episodic_store,
)


class TestEpisodicMemory:
    """Test EpisodicMemory data class."""
    
    def test_creation(self):
        """Test creating an episodic memory."""
        episode_id = uuid4()
        memory = EpisodicMemory(
            episode_id=episode_id,
            timestamp=datetime.now(),
            template_id="TEMPLATE_A",
            summary="Test episode summary",
            key_events=["Event 1", "Event 2"],
            outcome="success",
            lessons_learned=["Lesson 1"],
            context_tags=["test", "low_stakes"],
            domain="testing",
            duration_seconds=5.5,
            success=True,
        )
        
        assert memory.episode_id == episode_id
        assert memory.template_id == "TEMPLATE_A"
        assert memory.summary == "Test episode summary"
        assert len(memory.key_events) == 2
        assert memory.success is True
    
    def test_serialization(self):
        """Test to_dict and from_dict."""
        original = EpisodicMemory(
            episode_id=uuid4(),
            timestamp=datetime.now(),
            template_id="TEMPLATE_B",
            summary="Another test",
        )
        
        data = original.to_dict()
        restored = EpisodicMemory.from_dict(data)
        
        assert restored.episode_id == original.episode_id
        assert restored.template_id == original.template_id
        assert restored.summary == original.summary


class TestInMemoryEpisodicStore:
    """Test in-memory episodic store."""
    
    def test_save_and_load(self):
        """Test saving and loading memories."""
        store = InMemoryEpisodicStore()
        episode_id = uuid4()
        
        memory = EpisodicMemory(
            episode_id=episode_id,
            timestamp=datetime.now(),
            template_id="TEMPLATE_A",
            summary="Test memory",
        )
        
        store.save(memory)
        loaded = store.load(episode_id)
        
        assert loaded is not None
        assert loaded.episode_id == episode_id
        assert loaded.summary == "Test memory"
    
    def test_load_nonexistent(self):
        """Test loading nonexistent memory."""
        store = InMemoryEpisodicStore()
        loaded = store.load(uuid4())
        assert loaded is None
    
    def test_search_by_domain(self):
        """Test searching by domain."""
        store = InMemoryEpisodicStore()
        
        memory1 = EpisodicMemory(
            episode_id=uuid4(),
            timestamp=datetime.now(),
            template_id="TEMPLATE_A",
            summary="Market analysis",
            domain="market",
        )
        memory2 = EpisodicMemory(
            episode_id=uuid4(),
            timestamp=datetime.now(),
            template_id="TEMPLATE_B",
            summary="Combat simulation",
            domain="combat",
        )
        
        store.save(memory1)
        store.save(memory2)
        
        results = store.search(domain="market")
        assert len(results) == 1
        assert results[0].domain == "market"
    
    def test_search_by_tags(self):
        """Test searching by tags."""
        store = InMemoryEpisodicStore()
        
        memory1 = EpisodicMemory(
            episode_id=uuid4(),
            timestamp=datetime.now(),
            template_id="TEMPLATE_A",
            summary="Test 1",
            context_tags=["urgent", "combat"],
        )
        memory2 = EpisodicMemory(
            episode_id=uuid4(),
            timestamp=datetime.now(),
            template_id="TEMPLATE_B",
            summary="Test 2",
            context_tags=["routine", "market"],
        )
        
        store.save(memory1)
        store.save(memory2)
        
        results = store.search(tags=["combat"])
        assert len(results) == 1
        assert "combat" in results[0].context_tags
    
    def test_search_by_text(self):
        """Test text search in summary and events."""
        store = InMemoryEpisodicStore()
        
        memory1 = EpisodicMemory(
            episode_id=uuid4(),
            timestamp=datetime.now(),
            template_id="TEMPLATE_A",
            summary="Analyzed market trends",
            key_events=["Found arbitrage opportunity"],
        )
        memory2 = EpisodicMemory(
            episode_id=uuid4(),
            timestamp=datetime.now(),
            template_id="TEMPLATE_B",
            summary="Combat encounter",
        )
        
        store.save(memory1)
        store.save(memory2)
        
        results = store.search(query="market")
        assert len(results) == 1
        assert "market" in results[0].summary.lower()
    
    def test_search_limit(self):
        """Test search result limit."""
        store = InMemoryEpisodicStore()
        
        for i in range(20):
            memory = EpisodicMemory(
                episode_id=uuid4(),
                timestamp=datetime.now(),
                template_id="TEMPLATE_A",
                summary=f"Memory {i}",
            )
            store.save(memory)
        
        results = store.search(limit=5)
        assert len(results) == 5
    
    def test_count(self):
        """Test counting memories."""
        store = InMemoryEpisodicStore()
        assert store.count() == 0
        
        store.save(EpisodicMemory(
            episode_id=uuid4(),
            timestamp=datetime.now(),
            template_id="TEMPLATE_A",
            summary="Test",
        ))
        assert store.count() == 1
    
    def test_clear(self):
        """Test clearing all memories."""
        store = InMemoryEpisodicStore()
        
        store.save(EpisodicMemory(
            episode_id=uuid4(),
            timestamp=datetime.now(),
            template_id="TEMPLATE_A",
            summary="Test",
        ))
        
        assert store.count() == 1
        store.clear()
        assert store.count() == 0


class TestSQLiteEpisodicStore:
    """Test SQLite episodic store."""
    
    def test_save_and_load(self):
        """Test saving and loading with SQLite."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        try:
            store = SQLiteEpisodicStore(db_path)
            episode_id = uuid4()
            
            memory = EpisodicMemory(
                episode_id=episode_id,
                timestamp=datetime.now(),
                template_id="TEMPLATE_A",
                summary="SQLite test",
            )
            
            store.save(memory)
            loaded = store.load(episode_id)
            
            assert loaded is not None
            assert loaded.episode_id == episode_id
            assert loaded.summary == "SQLite test"
        finally:
            Path(db_path).unlink(missing_ok=True)
    
    def test_persistence(self):
        """Test that data persists across store instances."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        try:
            episode_id = uuid4()
            
            # Save with first instance
            store1 = SQLiteEpisodicStore(db_path)
            store1.save(EpisodicMemory(
                episode_id=episode_id,
                timestamp=datetime.now(),
                template_id="TEMPLATE_A",
                summary="Persistent data",
            ))
            
            # Load with second instance
            store2 = SQLiteEpisodicStore(db_path)
            loaded = store2.load(episode_id)
            
            assert loaded is not None
            assert loaded.summary == "Persistent data"
        finally:
            Path(db_path).unlink(missing_ok=True)
    
    def test_search_by_domain(self):
        """Test SQLite search by domain."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        try:
            store = SQLiteEpisodicStore(db_path)
            
            store.save(EpisodicMemory(
                episode_id=uuid4(),
                timestamp=datetime.now(),
                template_id="TEMPLATE_A",
                summary="Market",
                domain="market",
            ))
            store.save(EpisodicMemory(
                episode_id=uuid4(),
                timestamp=datetime.now(),
                template_id="TEMPLATE_B",
                summary="Combat",
                domain="combat",
            ))
            
            results = store.search(domain="market")
            assert len(results) == 1
            assert results[0].domain == "market"
        finally:
            Path(db_path).unlink(missing_ok=True)
    
    def test_count_and_clear(self):
        """Test counting and clearing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        try:
            store = SQLiteEpisodicStore(db_path)
            
            store.save(EpisodicMemory(
                episode_id=uuid4(),
                timestamp=datetime.now(),
                template_id="TEMPLATE_A",
                summary="Test",
            ))
            
            assert store.count() == 1
            store.clear()
            assert store.count() == 0
        finally:
            Path(db_path).unlink(missing_ok=True)


class TestEpisodicStoreFactory:
    """Test factory function."""
    
    def test_create_memory_store(self):
        """Test creating in-memory store."""
        store = create_episodic_store("memory")
        assert isinstance(store, InMemoryEpisodicStore)
    
    def test_create_sqlite_store(self):
        """Test creating SQLite store."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        try:
            store = create_episodic_store("sqlite", db_path)
            assert isinstance(store, SQLiteEpisodicStore)
        finally:
            Path(db_path).unlink(missing_ok=True)
    
    def test_invalid_backend(self):
        """Test invalid backend raises error."""
        with pytest.raises(ValueError):
            create_episodic_store("invalid")
