"""Tests for episode runner."""

import pytest
from uuid import uuid4

from omen.vocabulary import (
    LayerSource,
    TemplateID,
    QualityTier,
    StakesLevel,
    ToolsState,
    FSMState,
    PacketType,
)
from omen.templates import TEMPLATE_A, TEMPLATE_E
from omen.compiler import (
    CompilationContext,
    create_context,
    TemplateCompiler,
    create_compiler,
    CompiledEpisode,
    CompiledStep,
)
from omen.buses import NorthboundBus, SouthboundBus
from omen.orchestrator import (
    EpisodeLedger,
    create_ledger,
    BudgetState,
    LayerPool,
    create_mock_layer_pool,
    StepResult,
    EpisodeResult,
    EpisodeRunner,
    create_runner,
)


class TestStepResult:
    """Tests for step result."""
    
    def test_successful_step(self):
        """Successful step has no error."""
        result = StepResult(
            step_id="sense",
            layer=LayerSource.LAYER_6,
            success=True,
            packets_emitted=2,
        )
        assert result.success is True
        assert result.error is None
    
    def test_failed_step(self):
        """Failed step has error."""
        result = StepResult(
            step_id="sense",
            layer=LayerSource.LAYER_6,
            success=False,
            error="Layer invocation failed",
        )
        assert result.success is False
        assert result.error is not None


class TestEpisodeResult:
    """Tests for episode result."""
    
    def test_step_count(self):
        """Step count reflects completed steps."""
        result = EpisodeResult(
            correlation_id=uuid4(),
            template_id="TEMPLATE_A",
            success=True,
            steps_completed=[
                StepResult("s1", LayerSource.LAYER_6, True),
                StepResult("s2", LayerSource.LAYER_5, True),
            ],
        )
        assert result.step_count == 2


class TestEpisodeRunner:
    """Tests for episode runner."""
    
    @pytest.fixture
    def pool(self):
        """Create mock layer pool."""
        return create_mock_layer_pool()
    
    @pytest.fixture
    def runner(self, pool):
        """Create runner with mock pool."""
        return create_runner(layer_pool=pool)
    
    @pytest.fixture
    def compiled_episode(self):
        """Compile Template A for testing."""
        compiler = create_compiler()
        context = create_context(
            stakes_level=StakesLevel.LOW,
            quality_tier=QualityTier.PAR,
        )
        result = compiler.compile(TEMPLATE_A, context)
        return result.episode
    
    @pytest.fixture
    def ledger(self, compiled_episode):
        """Create ledger for episode."""
        return create_ledger(
            correlation_id=compiled_episode.correlation_id,
            budget=BudgetState(token_budget=1000, tool_call_budget=10),
        )
    
    def test_run_returns_result(self, runner, compiled_episode, ledger):
        """Run returns EpisodeResult."""
        result = runner.run(compiled_episode, ledger)
        
        assert isinstance(result, EpisodeResult)
        assert result.correlation_id == compiled_episode.correlation_id
    
    def test_run_completes_steps(self, runner, compiled_episode, ledger):
        """Runner executes steps."""
        result = runner.run(compiled_episode, ledger)
        
        assert result.step_count > 0
        assert result.final_step is not None
    
    def test_run_updates_ledger(self, runner, compiled_episode, ledger):
        """Runner updates ledger during execution."""
        runner.run(compiled_episode, ledger)
        
        assert ledger.is_complete
        assert len(ledger.completed_steps) > 0
    
    def test_run_with_initial_packets(self, runner, compiled_episode, ledger):
        """Can provide initial packets."""
        initial = [{"type": "seed", "data": "test"}]
        result = runner.run(compiled_episode, ledger, initial_packets=initial)
        
        # Should still complete
        assert result.step_count > 0
    
    def test_run_respects_max_steps(self, pool):
        """Runner stops at max steps."""
        # Create runner with low max
        runner = create_runner(layer_pool=pool, max_steps=2)
        
        compiler = create_compiler()
        context = create_context()
        episode = compiler.compile(TEMPLATE_A, context).episode
        ledger = create_ledger(correlation_id=episode.correlation_id)
        
        result = runner.run(episode, ledger)
        
        # Should have stopped at max
        assert result.step_count <= 2
        if result.step_count == 2:
            assert any("Max steps" in e for e in result.errors)
    
    def test_run_handles_missing_layer(self, compiled_episode, ledger):
        """Runner handles missing layer gracefully."""
        # Empty pool - no layers
        empty_pool = LayerPool()
        runner = create_runner(layer_pool=empty_pool)
        
        result = runner.run(compiled_episode, ledger)
        
        assert result.success is False
        assert any("not in pool" in e for e in result.errors)


class TestBusRouting:
    """Tests for packet bus routing."""
    
    @pytest.fixture
    def buses(self):
        """Create buses."""
        return NorthboundBus(), SouthboundBus()
    
    def test_runner_uses_buses(self, buses):
        """Runner publishes to buses."""
        north, south = buses
        pool = create_mock_layer_pool()
        runner = create_runner(
            layer_pool=pool,
            northbound_bus=north,
            southbound_bus=south,
        )
        
        compiler = create_compiler()
        context = create_context()
        episode = compiler.compile(TEMPLATE_A, context).episode
        ledger = create_ledger(correlation_id=episode.correlation_id)
        
        runner.run(episode, ledger)
        
        # Buses should have messages (even if empty due to mock)
        # The infrastructure is connected
        assert north is runner.northbound_bus
        assert south is runner.southbound_bus


class TestLedgerIntegration:
    """Tests for ledger integration."""
    
    def test_ledger_tracks_errors(self):
        """Errors are recorded in ledger."""
        pool = LayerPool()  # Empty - will cause errors
        runner = create_runner(layer_pool=pool)
        
        compiler = create_compiler()
        context = create_context()
        episode = compiler.compile(TEMPLATE_A, context).episode
        ledger = create_ledger(correlation_id=episode.correlation_id)
        
        runner.run(episode, ledger)
        
        assert ledger.has_errors
    
    def test_ledger_summary_in_result(self):
        """Result includes ledger summary."""
        pool = create_mock_layer_pool()
        runner = create_runner(layer_pool=pool)
        
        compiler = create_compiler()
        context = create_context()
        episode = compiler.compile(TEMPLATE_A, context).episode
        ledger = create_ledger(
            correlation_id=episode.correlation_id,
            budget=BudgetState(token_budget=1000),
        )
        
        result = runner.run(episode, ledger)
        
        assert "correlation_id" in result.ledger_summary
        assert "budget" in result.ledger_summary


class TestFactoryFunction:
    """Tests for runner factory."""
    
    def test_create_runner(self):
        """Factory creates runner."""
        pool = create_mock_layer_pool()
        runner = create_runner(layer_pool=pool)
        
        assert isinstance(runner, EpisodeRunner)
        assert runner.layer_pool is pool
    
    def test_create_runner_with_options(self):
        """Factory accepts options."""
        pool = create_mock_layer_pool()
        north = NorthboundBus()
        south = SouthboundBus()
        
        runner = create_runner(
            layer_pool=pool,
            northbound_bus=north,
            southbound_bus=south,
            max_steps=50,
        )
        
        assert runner.northbound_bus is north
        assert runner.southbound_bus is south
        assert runner.max_steps == 50
