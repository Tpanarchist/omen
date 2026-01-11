"""Tests for memory manager module."""

from datetime import datetime, timedelta
from uuid import uuid4

from omen.episode import EpisodeRecord, InMemoryStore as EpisodeStore
from omen.memory.manager import (
    MemoryContext,
    MemoryManager,
    create_memory_manager,
)
from omen.memory.episodic import InMemoryEpisodicStore, EpisodicMemory
from omen.memory.semantic import InMemorySemanticStore
from omen.memory.self_model import InMemorySelfModelStore


class TestMemoryContext:
    """Test MemoryContext."""
    
    def test_to_observation_packets_empty(self):
        """Test converting empty context to packets."""
        context = MemoryContext(
            episodic_memories=[],
            domain_beliefs=[],
            self_model={},
        )
        
        packets = context.to_observation_packets()
        assert len(packets) == 0
    
    def test_to_observation_packets_with_memories(self):
        """Test converting context with episodic memories."""
        memory = EpisodicMemory(
            episode_id=uuid4(),
            timestamp=datetime.now(),
            template_id="TEMPLATE_A",
            summary="Test episode",
            outcome="success",
            lessons_learned=["Lesson 1"],
        )
        
        context = MemoryContext(
            episodic_memories=[memory],
            domain_beliefs=[],
            self_model={},
        )
        
        packets = context.to_observation_packets()
        assert len(packets) == 1
        assert packets[0]["observation_type"] == "autobiographical_memory"
        assert len(packets[0]["content"]["recent_episodes"]) == 1
    
    def test_to_observation_packets_with_self_model(self):
        """Test converting context with self-model."""
        context = MemoryContext(
            episodic_memories=[],
            domain_beliefs=[],
            self_model={"capabilities": "Can process data"},
        )
        
        packets = context.to_observation_packets()
        assert len(packets) == 1
        assert packets[0]["observation_type"] == "self_model"
        assert "capabilities" in packets[0]["content"]["aspects"]


class TestMemoryManager:
    """Test MemoryManager."""
    
    def test_initialization(self):
        """Test creating memory manager."""
        episode_store = EpisodeStore()
        manager = MemoryManager(episode_store=episode_store)
        
        assert manager.episode_store is episode_store
        assert manager.episodic_store is not None
        assert manager.semantic_store is not None
        assert manager.self_model_store is not None
    
    def test_retrieve_context_empty(self):
        """Test retrieving context with no memories."""
        episode_store = EpisodeStore()
        manager = MemoryManager(episode_store=episode_store)
        
        context = manager.retrieve_context()
        
        assert len(context.episodic_memories) == 0
        assert len(context.domain_beliefs) == 0
        # Self-model should have bootstrap values
        assert len(context.self_model) > 0
    
    def test_retrieve_context_with_domain(self):
        """Test retrieving context filtered by domain."""
        episode_store = EpisodeStore()
        episodic_store = InMemoryEpisodicStore()
        semantic_store = InMemorySemanticStore()
        self_model_store = InMemorySelfModelStore()
        
        manager = MemoryManager(
            episode_store=episode_store,
            episodic_store=episodic_store,
            semantic_store=semantic_store,
            self_model_store=self_model_store,
        )
        
        # Add episodic memory
        episodic_store.save(EpisodicMemory(
            episode_id=uuid4(),
            timestamp=datetime.now(),
            template_id="TEMPLATE_A",
            summary="Market analysis",
            domain="market",
        ))
        
        # Add belief
        from omen.memory.semantic import Belief
        semantic_store.save(Belief(
            belief_id="b1",
            domain="market",
            claim="Markets are efficient",
            confidence=0.8,
        ))
        
        # Retrieve with domain filter
        context = manager.retrieve_context(domain="market")
        
        assert len(context.episodic_memories) == 1
        assert context.episodic_memories[0].domain == "market"
        assert len(context.domain_beliefs) == 1
        assert context.domain_beliefs[0].domain == "market"
    
    def test_after_episode_auto_consolidate(self):
        """Test auto-consolidation after threshold."""
        episode_store = EpisodeStore()
        manager = MemoryManager(
            episode_store=episode_store,
            auto_consolidate=True,
            consolidation_threshold=2,
        )
        
        # Create episodes
        for i in range(3):
            episode = EpisodeRecord(
                correlation_id=uuid4(),
                template_id="TEMPLATE_A",
                started_at=datetime.now(),
                completed_at=datetime.now(),
                success=True,
            )
            episode_store.save(episode)
            manager.after_episode(episode)
        
        # Should have consolidated after 2 episodes
        assert manager._episodes_since_consolidation < 2
        assert manager.episodic_store.count() > 0
    
    def test_after_episode_no_auto_consolidate(self):
        """Test no auto-consolidation when disabled."""
        episode_store = EpisodeStore()
        manager = MemoryManager(
            episode_store=episode_store,
            auto_consolidate=False,
        )
        
        # Create episodes
        for i in range(10):
            episode = EpisodeRecord(
                correlation_id=uuid4(),
                template_id="TEMPLATE_A",
                started_at=datetime.now(),
                completed_at=datetime.now(),
                success=True,
            )
            episode_store.save(episode)
            manager.after_episode(episode)
        
        # Should not have consolidated
        assert manager._episodes_since_consolidation == 10
        assert manager.episodic_store.count() == 0
    
    def test_consolidate(self):
        """Test manual consolidation."""
        episode_store = EpisodeStore()
        manager = MemoryManager(
            episode_store=episode_store,
            auto_consolidate=False,
        )
        
        # Create episode
        episode = EpisodeRecord(
            correlation_id=uuid4(),
            template_id="TEMPLATE_A",
            started_at=datetime.now(),
            completed_at=datetime.now(),
            success=True,
        )
        episode_store.save(episode)
        
        # Manually consolidate
        result = manager.consolidate()
        
        assert result.episodes_processed > 0
        assert result.memories_created > 0
        assert manager._episodes_since_consolidation == 0
    
    def test_get_memory_stats(self):
        """Test getting memory statistics."""
        episode_store = EpisodeStore()
        manager = MemoryManager(episode_store=episode_store)
        
        stats = manager.get_memory_stats()
        
        assert "episodic_memories" in stats
        assert "beliefs" in stats
        assert "self_model_aspects" in stats
        assert "episodes_total" in stats
        assert "episodes_since_consolidation" in stats
    
    def test_bootstrap_self_model(self):
        """Test bootstrapping self-model."""
        episode_store = EpisodeStore()
        self_model_store = InMemorySelfModelStore()
        
        # Don't auto-bootstrap in constructor
        manager = MemoryManager(
            episode_store=episode_store,
            self_model_store=self_model_store,
        )
        
        # Manager auto-bootstraps, clear it
        self_model_store.clear()
        
        # Bootstrap with custom aspects
        manager.bootstrap_self_model({
            "purpose": "To test",
            "capabilities": "Testing",
        })
        
        assert self_model_store.count() == 2
        purpose = self_model_store.load("purpose")
        assert purpose is not None
        assert purpose.content == "To test"
    
    def test_bootstrap_self_model_default(self):
        """Test bootstrapping with default aspects."""
        episode_store = EpisodeStore()
        self_model_store = InMemorySelfModelStore()
        
        manager = MemoryManager(
            episode_store=episode_store,
            self_model_store=self_model_store,
        )
        
        manager.bootstrap_self_model()
        
        # Should have default aspects
        assert self_model_store.count() >= 3
        purpose = self_model_store.load("purpose")
        assert purpose is not None


class TestMemoryManagerFactory:
    """Test memory manager factory."""
    
    def test_create_memory_manager_memory_backend(self):
        """Test creating with memory backend."""
        episode_store = EpisodeStore()
        
        manager = create_memory_manager(
            episode_store=episode_store,
            backend="memory",
        )
        
        assert isinstance(manager, MemoryManager)
        # Should auto-bootstrap self-model
        assert manager.self_model_store.count() > 0
    
    def test_create_memory_manager_custom_threshold(self):
        """Test creating with custom consolidation threshold."""
        episode_store = EpisodeStore()
        
        manager = create_memory_manager(
            episode_store=episode_store,
            consolidation_threshold=10,
        )
        
        assert manager.consolidation_threshold == 10
    
    def test_create_memory_manager_no_auto_consolidate(self):
        """Test creating with auto-consolidation disabled."""
        episode_store = EpisodeStore()
        
        manager = create_memory_manager(
            episode_store=episode_store,
            auto_consolidate=False,
        )
        
        assert manager.auto_consolidate is False
