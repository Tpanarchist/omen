"""Tests for orchestrator."""

import pytest
from uuid import uuid4

from omen.vocabulary import (
    LayerSource,
    TemplateID,
    QualityTier,
    StakesLevel,
    ToolsState,
)
from omen.orchestrator import (
    OrchestratorConfig,
    Orchestrator,
    create_orchestrator,
    create_mock_orchestrator,
    EpisodeResult,
    LayerPool,
)
from omen.layers import MockLLMClient
from omen.templates import TEMPLATE_A, TEMPLATE_D


class TestOrchestratorConfig:
    """Tests for orchestrator configuration."""
    
    def test_default_config(self):
        """Config has sensible defaults."""
        config = OrchestratorConfig()
        
        assert config.default_stakes == StakesLevel.LOW
        assert config.default_quality == QualityTier.PAR
        assert config.default_token_budget == 1000
        assert config.max_steps == 100
    
    def test_custom_config(self):
        """Can customize config."""
        config = OrchestratorConfig(
            default_stakes=StakesLevel.HIGH,
            default_quality=QualityTier.SUPERB,
            max_steps=50,
        )
        
        assert config.default_stakes == StakesLevel.HIGH
        assert config.max_steps == 50


class TestOrchestrator:
    """Tests for orchestrator."""
    
    @pytest.fixture
    def orchestrator(self):
        """Create mock orchestrator."""
        return create_mock_orchestrator()
    
    def test_run_template_by_id(self, orchestrator):
        """Can run template by ID."""
        result = orchestrator.run_template(TemplateID.TEMPLATE_A)
        
        assert isinstance(result, EpisodeResult)
        assert result.template_id == "TEMPLATE_A"
    
    def test_run_template_with_context(self, orchestrator):
        """Can provide context overrides."""
        result = orchestrator.run_template(
            TemplateID.TEMPLATE_A,
            stakes_level=StakesLevel.MEDIUM,
            quality_tier=QualityTier.SUPERB,
        )
        
        # Should still execute
        assert isinstance(result, EpisodeResult)
    
    def test_run_template_with_correlation_id(self, orchestrator):
        """Can provide correlation ID."""
        cid = uuid4()
        result = orchestrator.run_template(
            TemplateID.TEMPLATE_A,
            correlation_id=cid,
        )
        
        assert result.correlation_id == cid
    
    def test_run_template_invalid_id(self, orchestrator):
        """Handles invalid template ID."""
        # Try a template that doesn't exist
        # Note: All TemplateIDs should exist, so test constraint checking instead
        result = orchestrator.run_template(
            TemplateID.TEMPLATE_D,  # Needs SUPERB tier
            quality_tier=QualityTier.PAR,  # Insufficient
        )
        
        assert result.success is False
        assert any("tier" in e.lower() for e in result.errors)
    
    def test_run_episode_with_custom_template(self, orchestrator):
        """Can run with custom template."""
        result = orchestrator.run_episode(
            template=TEMPLATE_A,
            stakes_level=StakesLevel.LOW,
        )
        
        assert isinstance(result, EpisodeResult)
    
    def test_compile_template(self, orchestrator):
        """Can compile without running."""
        compilation = orchestrator.compile_template(
            TemplateID.TEMPLATE_A,
            quality_tier=QualityTier.PAR,
        )
        
        assert compilation.success is True
        assert compilation.episode is not None
    
    def test_get_layer_pool(self, orchestrator):
        """Can access layer pool."""
        pool = orchestrator.get_layer_pool()
        
        assert isinstance(pool, LayerPool)
        assert pool.has_layer(LayerSource.LAYER_5)
    
    def test_get_buses(self, orchestrator):
        """Can access buses."""
        north, south = orchestrator.get_buses()
        
        assert north.direction() == "northbound"
        assert south.direction() == "southbound"


class TestOrchestratorWithConfig:
    """Tests for orchestrator with custom config."""
    
    def test_custom_budgets(self):
        """Config budgets are applied."""
        config = OrchestratorConfig(
            default_token_budget=500,
            default_tool_call_budget=3,
        )
        orchestrator = Orchestrator(config=config)
        
        # The config should be used in context building
        assert orchestrator.config.default_token_budget == 500
    
    def test_validation_disabled(self):
        """Can disable template validation."""
        config = OrchestratorConfig(validate_templates=False)
        orchestrator = Orchestrator(config=config)
        
        assert orchestrator.validator is None
    
    def test_custom_llm_client(self):
        """Can provide custom LLM client."""
        client = MockLLMClient(responses=["custom response"])
        config = OrchestratorConfig(llm_client=client)
        orchestrator = Orchestrator(config=config)
        
        # Client should be used in layer pool
        result = orchestrator.run_template(TemplateID.TEMPLATE_A)
        assert isinstance(result, EpisodeResult)


class TestFactoryFunctions:
    """Tests for factory functions."""
    
    def test_create_orchestrator(self):
        """Factory creates orchestrator."""
        orch = create_orchestrator()
        
        assert isinstance(orch, Orchestrator)
    
    def test_create_orchestrator_with_client(self):
        """Factory accepts LLM client."""
        client = MockLLMClient()
        orch = create_orchestrator(llm_client=client)
        
        assert isinstance(orch, Orchestrator)
    
    def test_create_mock_orchestrator(self):
        """Mock factory creates orchestrator."""
        orch = create_mock_orchestrator()
        
        assert isinstance(orch, Orchestrator)
    
    def test_create_mock_with_responses(self):
        """Mock factory accepts per-layer responses."""
        responses = {
            LayerSource.LAYER_5: ["L5 response"],
        }
        orch = create_mock_orchestrator(responses=responses)
        
        # Should work
        result = orch.run_template(TemplateID.TEMPLATE_A)
        assert isinstance(result, EpisodeResult)


class TestEndToEndExecution:
    """End-to-end execution tests."""
    
    def test_template_a_grounding_loop(self):
        """Execute Template A (Grounding Loop)."""
        orch = create_mock_orchestrator()
        result = orch.run_template(TemplateID.TEMPLATE_A)
        
        assert result.step_count > 0
        assert result.template_id == "TEMPLATE_A"
    
    def test_template_d_requires_superb(self):
        """Template D requires SUPERB tier."""
        orch = create_mock_orchestrator()
        
        # Should fail with PAR
        result = orch.run_template(
            TemplateID.TEMPLATE_D,
            quality_tier=QualityTier.PAR,
        )
        assert result.success is False
        
        # Should work with SUPERB
        result = orch.run_template(
            TemplateID.TEMPLATE_D,
            quality_tier=QualityTier.SUPERB,
        )
        # May still have other issues in mock, but compilation succeeds
        assert "tier" not in str(result.errors).lower()
    
    def test_execution_tracks_duration(self):
        """Execution tracks total duration."""
        orch = create_mock_orchestrator()
        result = orch.run_template(TemplateID.TEMPLATE_A)
        
        assert result.total_duration_seconds >= 0
    
    def test_execution_provides_ledger_summary(self):
        """Execution provides ledger summary."""
        orch = create_mock_orchestrator()
        result = orch.run_template(TemplateID.TEMPLATE_A)
        
        assert "correlation_id" in result.ledger_summary
        assert "budget" in result.ledger_summary
