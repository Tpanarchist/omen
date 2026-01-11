"""Tests for consolidation module."""

from datetime import datetime, timedelta
from uuid import uuid4

from omen.episode import EpisodeRecord, InMemoryStore as EpisodeStore
from omen.memory.episodic import InMemoryEpisodicStore
from omen.memory.semantic import InMemorySemanticStore
from omen.memory.self_model import InMemorySelfModelStore
from omen.memory.consolidation import (
    ConsolidationCycle,
    create_consolidation_cycle,
)


class TestConsolidationCycle:
    """Test consolidation cycle."""
    
    def test_consolidate_creates_episodic_memories(self):
        """Test that consolidation creates episodic memories from episodes."""
        episode_store = EpisodeStore()
        episodic_store = InMemoryEpisodicStore()
        semantic_store = InMemorySemanticStore()
        self_model_store = InMemorySelfModelStore()
        
        cycle = ConsolidationCycle(
            episode_store=episode_store,
            episodic_store=episodic_store,
            semantic_store=semantic_store,
            self_model_store=self_model_store,
        )
        
        # Create an episode
        episode_id = uuid4()
        episode = EpisodeRecord(
            correlation_id=episode_id,
            template_id="TEMPLATE_A",
            started_at=datetime.now(),
            completed_at=datetime.now(),
            success=True,
        )
        episode_store.save(episode)
        
        # Run consolidation
        result = cycle.consolidate()
        
        assert result.episodes_processed == 1
        assert result.memories_created == 1
        
        # Verify episodic memory was created
        memory = episodic_store.load(episode_id)
        assert memory is not None
        assert memory.episode_id == episode_id
        assert memory.template_id == "TEMPLATE_A"
    
    def test_consolidate_updates_beliefs(self):
        """Test that consolidation updates beliefs based on patterns."""
        episode_store = EpisodeStore()
        episodic_store = InMemoryEpisodicStore()
        semantic_store = InMemorySemanticStore()
        self_model_store = InMemorySelfModelStore()
        
        cycle = ConsolidationCycle(
            episode_store=episode_store,
            episodic_store=episodic_store,
            semantic_store=semantic_store,
            self_model_store=self_model_store,
        )
        
        # Create a successful episode
        episode = EpisodeRecord(
            correlation_id=uuid4(),
            template_id="TEMPLATE_A",
            started_at=datetime.now(),
            completed_at=datetime.now(),
            success=True,
        )
        episode_store.save(episode)
        
        # Run consolidation
        result = cycle.consolidate()
        
        assert result.beliefs_updated > 0
        
        # Verify beliefs were created
        beliefs = semantic_store.query()
        assert len(beliefs) > 0
    
    def test_consolidate_updates_self_model(self):
        """Test that consolidation updates self-model."""
        episode_store = EpisodeStore()
        episodic_store = InMemoryEpisodicStore()
        semantic_store = InMemorySemanticStore()
        self_model_store = InMemorySelfModelStore()
        
        cycle = ConsolidationCycle(
            episode_store=episode_store,
            episodic_store=episodic_store,
            semantic_store=semantic_store,
            self_model_store=self_model_store,
        )
        
        # Create a successful episode
        episode = EpisodeRecord(
            correlation_id=uuid4(),
            template_id="TEMPLATE_A",
            started_at=datetime.now(),
            completed_at=datetime.now(),
            success=True,
        )
        episode_store.save(episode)
        
        # Run consolidation
        result = cycle.consolidate()
        
        assert result.self_model_updates > 0
        
        # Verify self-model was updated
        aspects = self_model_store.get_all()
        assert len(aspects) > 0
    
    def test_consolidate_skips_already_consolidated(self):
        """Test that already consolidated episodes are skipped."""
        episode_store = EpisodeStore()
        episodic_store = InMemoryEpisodicStore()
        semantic_store = InMemorySemanticStore()
        self_model_store = InMemorySelfModelStore()
        
        cycle = ConsolidationCycle(
            episode_store=episode_store,
            episodic_store=episodic_store,
            semantic_store=semantic_store,
            self_model_store=self_model_store,
        )
        
        # Create an episode and manually add its memory
        episode_id = uuid4()
        episode = EpisodeRecord(
            correlation_id=episode_id,
            template_id="TEMPLATE_A",
            started_at=datetime.now(),
            completed_at=datetime.now(),
            success=True,
        )
        episode_store.save(episode)
        
        # Manually create the memory
        from omen.memory.episodic import EpisodicMemory
        memory = EpisodicMemory(
            episode_id=episode_id,
            timestamp=episode.started_at,
            template_id=episode.template_id,
            summary="Already consolidated",
        )
        episodic_store.save(memory)
        
        # Run consolidation
        result = cycle.consolidate()
        
        # Should process but not create new memory
        assert result.episodes_processed == 1
        assert result.memories_created == 0
    
    def test_consolidate_with_time_filter(self):
        """Test consolidation with time filter."""
        episode_store = EpisodeStore()
        episodic_store = InMemoryEpisodicStore()
        semantic_store = InMemorySemanticStore()
        self_model_store = InMemorySelfModelStore()
        
        cycle = ConsolidationCycle(
            episode_store=episode_store,
            episodic_store=episodic_store,
            semantic_store=semantic_store,
            self_model_store=self_model_store,
        )
        
        # Create an old episode
        old_episode = EpisodeRecord(
            correlation_id=uuid4(),
            template_id="TEMPLATE_A",
            started_at=datetime.now() - timedelta(hours=2),
            completed_at=datetime.now() - timedelta(hours=2),
            success=True,
        )
        episode_store.save(old_episode)
        
        # Create a recent episode
        recent_episode = EpisodeRecord(
            correlation_id=uuid4(),
            template_id="TEMPLATE_B",
            started_at=datetime.now() - timedelta(minutes=30),
            completed_at=datetime.now() - timedelta(minutes=30),
            success=True,
        )
        episode_store.save(recent_episode)
        
        # Consolidate only last hour
        result = cycle.consolidate(since=datetime.now() - timedelta(hours=1))
        
        assert result.episodes_processed == 1
        assert result.memories_created == 1
        
        # Verify only recent episode was consolidated
        memory = episodic_store.load(recent_episode.correlation_id)
        assert memory is not None
    
    def test_consolidate_failure_episode(self):
        """Test consolidation handles failed episodes."""
        episode_store = EpisodeStore()
        episodic_store = InMemoryEpisodicStore()
        semantic_store = InMemorySemanticStore()
        self_model_store = InMemorySelfModelStore()
        
        cycle = ConsolidationCycle(
            episode_store=episode_store,
            episodic_store=episodic_store,
            semantic_store=semantic_store,
            self_model_store=self_model_store,
        )
        
        # Create a failed episode
        episode = EpisodeRecord(
            correlation_id=uuid4(),
            template_id="TEMPLATE_A",
            started_at=datetime.now(),
            completed_at=datetime.now(),
            success=False,
            errors=["Timeout error", "Validation failed"],
        )
        episode_store.save(episode)
        
        # Run consolidation
        result = cycle.consolidate()
        
        assert result.episodes_processed == 1
        assert result.memories_created == 1
        
        # Verify memory captures failure
        memory = episodic_store.load(episode.correlation_id)
        assert memory is not None
        assert memory.outcome == "failure"
        assert len(memory.lessons_learned) > 0
    
    def test_consolidate_extracts_patterns(self):
        """Test pattern extraction from episodes."""
        episode_store = EpisodeStore()
        episodic_store = InMemoryEpisodicStore()
        semantic_store = InMemorySemanticStore()
        self_model_store = InMemorySelfModelStore()
        
        cycle = ConsolidationCycle(
            episode_store=episode_store,
            episodic_store=episodic_store,
            semantic_store=semantic_store,
            self_model_store=self_model_store,
        )
        
        # Create episode with budget info
        episode = EpisodeRecord(
            correlation_id=uuid4(),
            template_id="TEMPLATE_A",
            started_at=datetime.now(),
            completed_at=datetime.now(),
            success=True,
            budget_allocated={"token_budget": 1000},
            budget_consumed={"tokens": 300},
        )
        episode_store.save(episode)
        
        # Run consolidation
        result = cycle.consolidate()
        
        assert len(result.patterns_extracted) > 0
        # Should detect efficient token usage
        assert any("successful" in p for p in result.patterns_extracted)


class TestConsolidationFactory:
    """Test consolidation factory."""
    
    def test_create_consolidation_cycle(self):
        """Test creating consolidation cycle with factory."""
        episode_store = EpisodeStore()
        episodic_store = InMemoryEpisodicStore()
        semantic_store = InMemorySemanticStore()
        self_model_store = InMemorySelfModelStore()
        
        cycle = create_consolidation_cycle(
            episode_store=episode_store,
            episodic_store=episodic_store,
            semantic_store=semantic_store,
            self_model_store=self_model_store,
        )
        
        assert isinstance(cycle, ConsolidationCycle)
        assert cycle.episode_store is episode_store
        assert cycle.episodic_store is episodic_store
