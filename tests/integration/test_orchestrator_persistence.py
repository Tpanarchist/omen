"""Integration tests for orchestrator episode persistence."""

import pytest
from uuid import uuid4

from omen.orchestrator import Orchestrator, OrchestratorConfig
from omen.episode import create_memory_store
from omen.vocabulary import TemplateID
from omen.layers import MockLLMClient


class TestOrchestratorPersistence:
    """Tests for orchestrator episode storage integration."""
    
    @pytest.fixture
    def orchestrator_with_storage(self):
        """Create orchestrator with in-memory storage."""
        store = create_memory_store()
        config = OrchestratorConfig(
            llm_client=MockLLMClient(),
            episode_store=store,
            auto_save=True,
        )
        return Orchestrator(config=config), store
    
    def test_auto_saves_episode(self, orchestrator_with_storage):
        """Orchestrator auto-saves completed episodes."""
        orch, store = orchestrator_with_storage
        
        # Run an episode
        result = orch.run_template(TemplateID.TEMPLATE_A)
        
        # Episode should be saved
        assert store.count() == 1
        
        # Should be loadable
        record = store.load(result.correlation_id)
        assert record is not None
        assert record.template_id == "TEMPLATE_A"
    
    def test_get_episode(self, orchestrator_with_storage):
        """Can retrieve saved episode via orchestrator."""
        orch, store = orchestrator_with_storage
        
        # Run an episode
        result = orch.run_template(TemplateID.TEMPLATE_A)
        
        # Get via orchestrator
        record = orch.get_episode(result.correlation_id)
        assert record is not None
        assert record.correlation_id == result.correlation_id
    
    def test_list_episodes(self, orchestrator_with_storage):
        """Can list saved episodes."""
        orch, store = orchestrator_with_storage
        
        # Run multiple episodes
        orch.run_template(TemplateID.TEMPLATE_A)
        orch.run_template(TemplateID.TEMPLATE_B)
        
        # List all
        episodes = orch.list_episodes()
        assert len(episodes) == 2
    
    def test_list_episodes_filtered(self, orchestrator_with_storage):
        """Can filter episodes by template."""
        orch, store = orchestrator_with_storage
        
        # Run different templates
        orch.run_template(TemplateID.TEMPLATE_A)
        orch.run_template(TemplateID.TEMPLATE_A)
        orch.run_template(TemplateID.TEMPLATE_B)
        
        # Filter by template
        template_a = orch.list_episodes(template_id="TEMPLATE_A")
        assert len(template_a) == 2
        
        template_b = orch.list_episodes(template_id="TEMPLATE_B")
        assert len(template_b) == 1
    
    def test_no_save_when_auto_save_disabled(self):
        """Episodes not saved when auto_save is False."""
        store = create_memory_store()
        config = OrchestratorConfig(
            llm_client=MockLLMClient(),
            episode_store=store,
            auto_save=False,
        )
        orch = Orchestrator(config=config)
        
        # Run an episode
        orch.run_template(TemplateID.TEMPLATE_A)
        
        # Should not be saved
        assert store.count() == 0
    
    def test_no_save_when_no_store(self):
        """No error when store not configured."""
        config = OrchestratorConfig(
            llm_client=MockLLMClient(),
            episode_store=None,
        )
        orch = Orchestrator(config=config)
        
        # Should run without error
        result = orch.run_template(TemplateID.TEMPLATE_A)
        assert result.correlation_id is not None
        
        # Get/list should return None/empty
        assert orch.get_episode(result.correlation_id) is None
        assert orch.list_episodes() == []
    
    def test_saved_record_has_metadata(self, orchestrator_with_storage):
        """Saved record includes policy and budget info."""
        orch, store = orchestrator_with_storage
        
        # Run with custom settings
        result = orch.run_template(
            TemplateID.TEMPLATE_A,
            campaign_id="test_campaign",
        )
        
        # Check saved record
        record = store.load(result.correlation_id)
        assert record is not None
        assert record.campaign_id == "test_campaign"
        assert record.stakes_level == "LOW"
        assert record.quality_tier == "PAR"
        assert "tokens" in record.budget_allocated
        assert "tokens" in record.budget_consumed
