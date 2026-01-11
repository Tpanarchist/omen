"""Integration test for memory-aware orchestrator."""

from uuid import uuid4

import pytest

from omen.orchestrator import Orchestrator, OrchestratorConfig
from omen.episode import InMemoryStore as EpisodeStore
from omen.vocabulary import TemplateID, StakesLevel, QualityTier
from omen.layers import MockLLMClient


@pytest.mark.skip(reason="Requires full orchestrator setup")
class TestMemoryAwareOrchestrator:
    """Test orchestrator with memory systems enabled."""
    
    def test_orchestrator_with_memory_disabled(self):
        """Test orchestrator runs without memory (baseline)."""
        episode_store = EpisodeStore()
        config = OrchestratorConfig(
            llm_client=MockLLMClient(),
            episode_store=episode_store,
            enable_memory=False,
        )
        
        orchestrator = Orchestrator(config=config)
        
        assert orchestrator.memory_manager is None
        assert orchestrator.get_memory_stats() is None
    
    def test_orchestrator_with_memory_enabled(self):
        """Test orchestrator with memory systems enabled."""
        episode_store = EpisodeStore()
        config = OrchestratorConfig(
            llm_client=MockLLMClient(),
            episode_store=episode_store,
            enable_memory=True,
            memory_backend="memory",
            auto_consolidate=True,
            consolidation_threshold=2,
        )
        
        orchestrator = Orchestrator(config=config)
        
        assert orchestrator.memory_manager is not None
        
        # Check initial stats
        stats = orchestrator.get_memory_stats()
        assert stats is not None
        assert "episodic_memories" in stats
        assert "beliefs" in stats
        assert "self_model_aspects" in stats
        assert stats["self_model_aspects"] > 0  # Should have bootstrap
    
    def test_memory_consolidation_after_threshold(self):
        """Test that memories consolidate after threshold."""
        episode_store = EpisodeStore()
        config = OrchestratorConfig(
            llm_client=MockLLMClient(),
            episode_store=episode_store,
            enable_memory=True,
            auto_consolidate=True,
            consolidation_threshold=2,
        )
        
        orchestrator = Orchestrator(config=config)
        
        # Initial state
        stats_before = orchestrator.get_memory_stats()
        assert stats_before["episodic_memories"] == 0
        
        # Run multiple episodes (would need proper templates)
        # This would trigger consolidation after threshold
        
        # For now, just verify the manager exists and can consolidate
        result = orchestrator.consolidate_memories()
        assert result is not None
    
    def test_memory_context_injection(self):
        """Test that memory context is injected into episodes."""
        episode_store = EpisodeStore()
        config = OrchestratorConfig(
            llm_client=MockLLMClient(),
            episode_store=episode_store,
            enable_memory=True,
            inject_memory_context=True,
        )
        
        orchestrator = Orchestrator(config=config)
        
        # Memory context should include self-model
        context = orchestrator.memory_manager.retrieve_context()
        assert len(context.self_model) > 0
        
        # Should be convertible to observation packets
        packets = context.to_observation_packets()
        assert len(packets) > 0
        assert any(p["observation_type"] == "self_model" for p in packets)


class TestMemoryManagerAccessors:
    """Test memory manager accessor methods."""
    
    def test_get_memory_stats_without_memory(self):
        """Test getting stats when memory disabled."""
        config = OrchestratorConfig(
            llm_client=MockLLMClient(),
            enable_memory=False,
        )
        
        orchestrator = Orchestrator(config=config)
        stats = orchestrator.get_memory_stats()
        
        assert stats is None
    
    def test_consolidate_memories_without_memory(self):
        """Test consolidation when memory disabled."""
        config = OrchestratorConfig(
            llm_client=MockLLMClient(),
            enable_memory=False,
        )
        
        orchestrator = Orchestrator(config=config)
        result = orchestrator.consolidate_memories()
        
        assert result is None
    
    def test_get_memory_stats_with_memory(self):
        """Test getting stats when memory enabled."""
        episode_store = EpisodeStore()
        config = OrchestratorConfig(
            llm_client=MockLLMClient(),
            episode_store=episode_store,
            enable_memory=True,
        )
        
        orchestrator = Orchestrator(config=config)
        stats = orchestrator.get_memory_stats()
        
        assert stats is not None
        assert isinstance(stats, dict)
        assert "episodic_memories" in stats
        assert "beliefs" in stats
        assert "self_model_aspects" in stats
        assert "episodes_total" in stats
