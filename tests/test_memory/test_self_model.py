"""Tests for self-model module."""

import tempfile
from pathlib import Path

import pytest

from omen.memory.self_model import (
    SelfModelAspect,
    SelfModel,
    InMemorySelfModelStore,
    SQLiteSelfModelStore,
    create_self_model_store,
)


class TestSelfModelAspect:
    """Test SelfModelAspect data class."""
    
    def test_creation(self):
        """Test creating a self-model aspect."""
        aspect = SelfModelAspect(
            aspect="capabilities",
            content="Can execute Template A efficiently",
            confidence=0.8,
            formed_from=["episode-1", "episode-2"],
        )
        
        assert aspect.aspect == "capabilities"
        assert aspect.confidence == 0.8
        assert len(aspect.formed_from) == 2
    
    def test_serialization(self):
        """Test to_dict and from_dict."""
        original = SelfModelAspect(
            aspect="limitations",
            content="Struggles with complex market analysis",
            confidence=0.6,
        )
        
        data = original.to_dict()
        restored = SelfModelAspect.from_dict(data)
        
        assert restored.aspect == original.aspect
        assert restored.content == original.content
        assert restored.confidence == original.confidence


class TestInMemorySelfModelStore:
    """Test in-memory self-model store."""
    
    def test_save_and_load(self):
        """Test saving and loading aspects."""
        store = InMemorySelfModelStore()
        
        aspect = SelfModelAspect(
            aspect="capabilities",
            content="Can process data",
            confidence=0.9,
        )
        
        store.save(aspect)
        loaded = store.load("capabilities")
        
        assert loaded is not None
        assert loaded.aspect == "capabilities"
        assert loaded.content == "Can process data"
    
    def test_load_nonexistent(self):
        """Test loading nonexistent aspect."""
        store = InMemorySelfModelStore()
        loaded = store.load("nonexistent")
        assert loaded is None
    
    def test_get_all(self):
        """Test getting all aspects."""
        store = InMemorySelfModelStore()
        
        store.save(SelfModelAspect(aspect="capabilities", content="A", confidence=0.8))
        store.save(SelfModelAspect(aspect="limitations", content="B", confidence=0.7))
        store.save(SelfModelAspect(aspect="purpose", content="C", confidence=0.9))
        
        all_aspects = store.get_all()
        assert len(all_aspects) == 3
        aspects_dict = {a.aspect: a for a in all_aspects}
        assert "capabilities" in aspects_dict
        assert "limitations" in aspects_dict
        assert "purpose" in aspects_dict
    
    def test_count(self):
        """Test counting aspects."""
        store = InMemorySelfModelStore()
        assert store.count() == 0
        
        store.save(SelfModelAspect(aspect="capabilities", content="Test", confidence=0.5))
        assert store.count() == 1
    
    def test_clear(self):
        """Test clearing all aspects."""
        store = InMemorySelfModelStore()
        
        store.save(SelfModelAspect(aspect="capabilities", content="Test", confidence=0.5))
        assert store.count() == 1
        
        store.clear()
        assert store.count() == 0
    
    def test_update_aspect(self):
        """Test updating an existing aspect."""
        store = InMemorySelfModelStore()
        
        aspect1 = SelfModelAspect(
            aspect="capabilities",
            content="Initial",
            confidence=0.5,
        )
        store.save(aspect1)
        
        # Update with new content
        aspect2 = SelfModelAspect(
            aspect="capabilities",
            content="Updated",
            confidence=0.9,
        )
        store.save(aspect2)
        
        loaded = store.load("capabilities")
        assert loaded is not None
        assert loaded.content == "Updated"
        assert loaded.confidence == 0.9


class TestSelfModel:
    """Test SelfModel operations."""
    
    def test_update_aspect_new(self):
        """Test updating a new aspect."""
        store = InMemorySelfModelStore()
        model = SelfModel(store)
        
        aspect = model.update_aspect(
            aspect="capabilities",
            content="Can analyze data",
            confidence=0.8,
            episode_id="ep-123",
        )
        
        assert aspect.aspect == "capabilities"
        assert aspect.content == "Can analyze data"
        assert aspect.confidence == 0.8
        assert "ep-123" in aspect.formed_from
        
        # Verify it was saved
        loaded = store.load("capabilities")
        assert loaded is not None
    
    def test_update_aspect_existing(self):
        """Test updating an existing aspect."""
        store = InMemorySelfModelStore()
        model = SelfModel(store)
        
        # Create initial aspect
        model.update_aspect(
            aspect="capabilities",
            content="Initial",
            confidence=0.5,
            episode_id="ep-1",
        )
        
        # Update it
        updated = model.update_aspect(
            aspect="capabilities",
            content="Updated",
            confidence=0.9,
            episode_id="ep-2",
        )
        
        assert updated.content == "Updated"
        assert updated.confidence == 0.9
        assert "ep-1" in updated.formed_from
        assert "ep-2" in updated.formed_from
        assert len(updated.formed_from) == 2
    
    def test_get_aspect(self):
        """Test getting a specific aspect."""
        store = InMemorySelfModelStore()
        model = SelfModel(store)
        
        model.update_aspect(
            aspect="purpose",
            content="To assist and learn",
            confidence=0.95,
        )
        
        aspect = model.get_aspect("purpose")
        assert aspect is not None
        assert aspect.content == "To assist and learn"
    
    def test_get_aspect_nonexistent(self):
        """Test getting nonexistent aspect returns None."""
        store = InMemorySelfModelStore()
        model = SelfModel(store)
        
        aspect = model.get_aspect("nonexistent")
        assert aspect is None
    
    def test_get_current_model(self):
        """Test getting current model as dictionary."""
        store = InMemorySelfModelStore()
        model = SelfModel(store)
        
        model.update_aspect(aspect="capabilities", content="Can process", confidence=0.8)
        model.update_aspect(aspect="limitations", content="Limited memory", confidence=0.7)
        model.update_aspect(aspect="purpose", content="To help", confidence=0.9)
        
        current = model.get_current_model()
        assert len(current) == 3
        assert current["capabilities"] == "Can process"
        assert current["limitations"] == "Limited memory"
        assert current["purpose"] == "To help"


class TestSQLiteSelfModelStore:
    """Test SQLite self-model store."""
    
    def test_save_and_load(self):
        """Test SQLite save and load."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        try:
            store = SQLiteSelfModelStore(db_path)
            
            aspect = SelfModelAspect(
                aspect="capabilities",
                content="SQLite works",
                confidence=0.95,
            )
            
            store.save(aspect)
            loaded = store.load("capabilities")
            
            assert loaded is not None
            assert loaded.aspect == "capabilities"
            assert loaded.content == "SQLite works"
        finally:
            Path(db_path).unlink(missing_ok=True)
    
    def test_persistence(self):
        """Test data persists across instances."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        try:
            # Save with first instance
            store1 = SQLiteSelfModelStore(db_path)
            store1.save(SelfModelAspect(
                aspect="purpose",
                content="Persistent",
                confidence=0.9,
            ))
            
            # Load with second instance
            store2 = SQLiteSelfModelStore(db_path)
            loaded = store2.load("purpose")
            
            assert loaded is not None
            assert loaded.content == "Persistent"
        finally:
            Path(db_path).unlink(missing_ok=True)
    
    def test_get_all(self):
        """Test getting all aspects from SQLite."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        try:
            store = SQLiteSelfModelStore(db_path)
            
            store.save(SelfModelAspect(aspect="capabilities", content="A", confidence=0.8))
            store.save(SelfModelAspect(aspect="limitations", content="B", confidence=0.7))
            
            all_aspects = store.get_all()
            assert len(all_aspects) == 2
        finally:
            Path(db_path).unlink(missing_ok=True)


class TestSelfModelStoreFactory:
    """Test factory function."""
    
    def test_create_memory_store(self):
        """Test creating in-memory store."""
        store = create_self_model_store("memory")
        assert isinstance(store, InMemorySelfModelStore)
    
    def test_create_sqlite_store(self):
        """Test creating SQLite store."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        try:
            store = create_self_model_store("sqlite", db_path)
            assert isinstance(store, SQLiteSelfModelStore)
        finally:
            Path(db_path).unlink(missing_ok=True)
    
    def test_invalid_backend(self):
        """Test invalid backend raises error."""
        with pytest.raises(ValueError):
            create_self_model_store("invalid")
