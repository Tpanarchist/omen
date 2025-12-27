"""Tests for template compiler."""

import pytest
from uuid import UUID

from omen.vocabulary import (
    TemplateID,
    QualityTier,
    StakesLevel,
    ToolsState,
    FSMState,
    PacketType,
    LayerSource,
)
from omen.templates import (
    TEMPLATE_A,
    TEMPLATE_B,
    TEMPLATE_C,
    TEMPLATE_D,
    TEMPLATE_E,
    TEMPLATE_F,
    TEMPLATE_G,
    create_template_validator,
    get_all_templates,
)
from omen.compiler import (
    CompilationContext,
    StakesContext,
    QualityContext,
    BudgetContext,
    create_context,
    CompiledStep,
    CompiledEpisode,
    TemplateCompiler,
    create_compiler,
    CompilationResult,
)


class TestCompilationContext:
    """Tests for compilation context."""
    
    def test_default_context(self):
        """Default context has sensible defaults."""
        ctx = CompilationContext()
        assert isinstance(ctx.correlation_id, UUID)
        assert ctx.stakes.stakes_level == StakesLevel.LOW
        assert ctx.quality.quality_tier == QualityTier.PAR
        assert ctx.tools_state == ToolsState.TOOLS_OK
    
    def test_create_context_factory(self):
        """Factory creates context with overrides."""
        ctx = create_context(
            stakes_level=StakesLevel.HIGH,
            quality_tier=QualityTier.SUPERB,
            tools_state=ToolsState.TOOLS_PARTIAL,
        )
        assert ctx.stakes.stakes_level == StakesLevel.HIGH
        assert ctx.quality.quality_tier == QualityTier.SUPERB
        assert ctx.tools_state == ToolsState.TOOLS_PARTIAL
    
    def test_with_correlation_id(self):
        """with_correlation_id creates copy with new ID."""
        ctx1 = CompilationContext()
        new_id = UUID('12345678-1234-5678-1234-567812345678')
        ctx2 = ctx1.with_correlation_id(new_id)
        
        assert ctx2.correlation_id == new_id
        assert ctx1.correlation_id != new_id  # Original unchanged
    
    def test_stakes_context_defaults(self):
        """StakesContext has proper defaults."""
        stakes = StakesContext()
        assert stakes.impact == "LOW"
        assert stakes.irreversibility == "REVERSIBLE"
        assert stakes.uncertainty == "LOW"
        assert stakes.adversariality == "BENIGN"
        assert stakes.stakes_level == StakesLevel.LOW
    
    def test_quality_context_defaults(self):
        """QualityContext has proper defaults."""
        quality = QualityContext()
        assert quality.quality_tier == QualityTier.PAR
        assert quality.satisficing_mode is True
        assert quality.definition_of_done["text"] == "Episode completed successfully"
    
    def test_budget_context_defaults(self):
        """BudgetContext has proper defaults."""
        budgets = BudgetContext()
        assert budgets.token_budget == 1000
        assert budgets.tool_call_budget == 5
        assert budgets.time_budget_seconds == 120


class TestCompiledEpisode:
    """Tests for compiled episode structure."""
    
    @pytest.fixture
    def sample_episode(self):
        """Create sample compiled episode."""
        return CompiledEpisode(
            correlation_id=UUID('12345678-1234-5678-1234-567812345678'),
            template_id=TemplateID.TEMPLATE_A,
            steps=[
                CompiledStep(
                    step_id="start",
                    sequence_number=0,
                    owner_layer=LayerSource.LAYER_5,
                    fsm_state=FSMState.S0_IDLE,
                    packet_type=None,
                    next_steps=["sense"],
                ),
                CompiledStep(
                    step_id="sense",
                    sequence_number=1,
                    owner_layer=LayerSource.LAYER_6,
                    fsm_state=FSMState.S1_SENSE,
                    packet_type=PacketType.OBSERVATION,
                    next_steps=["end"],
                ),
                CompiledStep(
                    step_id="end",
                    sequence_number=2,
                    owner_layer=LayerSource.LAYER_5,
                    fsm_state=FSMState.S0_IDLE,
                    packet_type=None,
                    next_steps=[],
                ),
            ],
            entry_step="start",
            exit_steps=["end"],
        )
    
    def test_get_step(self, sample_episode):
        """get_step returns correct step."""
        step = sample_episode.get_step("sense")
        assert step is not None
        assert step.step_id == "sense"
        assert step.packet_type == PacketType.OBSERVATION
    
    def test_get_step_missing(self, sample_episode):
        """get_step returns None for missing step."""
        assert sample_episode.get_step("nonexistent") is None
    
    def test_get_next_steps_from_start(self, sample_episode):
        """get_next_steps returns entry when current is None."""
        sample_episode.current_step = None
        next_steps = sample_episode.get_next_steps()
        assert len(next_steps) == 1
        assert next_steps[0].step_id == "start"
    
    def test_get_next_steps_from_middle(self, sample_episode):
        """get_next_steps returns next from current position."""
        sample_episode.current_step = "sense"
        next_steps = sample_episode.get_next_steps()
        assert len(next_steps) == 1
        assert next_steps[0].step_id == "end"
    
    def test_get_next_steps_at_end(self, sample_episode):
        """get_next_steps returns empty at exit."""
        sample_episode.current_step = "end"
        next_steps = sample_episode.get_next_steps()
        assert len(next_steps) == 0


class TestTemplateCompiler:
    """Tests for template compilation."""
    
    @pytest.fixture
    def compiler(self):
        """Compiler without validator."""
        return create_compiler()
    
    @pytest.fixture
    def validating_compiler(self):
        """Compiler with validator."""
        return create_compiler(validator=create_template_validator())
    
    def test_compile_template_a(self, compiler):
        """Compile Template A successfully."""
        ctx = create_context()
        result = compiler.compile(TEMPLATE_A, ctx)
        
        assert result.success is True
        assert result.episode is not None
        assert result.episode.template_id == TemplateID.TEMPLATE_A
        assert len(result.episode.steps) == len(TEMPLATE_A.steps)
    
    def test_compile_preserves_correlation_id(self, compiler):
        """Compiled episode has context's correlation_id."""
        ctx = create_context()
        result = compiler.compile(TEMPLATE_A, ctx)
        
        assert result.episode.correlation_id == ctx.correlation_id
    
    def test_compile_binds_mcp_fields(self, compiler):
        """Steps have MCP bindings from context."""
        ctx = create_context(
            stakes_level=StakesLevel.HIGH,
            quality_tier=QualityTier.SUPERB,
        )
        result = compiler.compile(TEMPLATE_A, ctx)
        
        step = result.episode.get_step("sense")
        assert step.mcp_bindings["stakes"]["stakes_level"] == "HIGH"
        assert step.mcp_bindings["quality"]["quality_tier"] == "SUPERB"
    
    def test_compile_includes_epistemics_defaults(self, compiler):
        """Compiled steps include epistemics defaults."""
        ctx = create_context()
        result = compiler.compile(TEMPLATE_A, ctx)
        
        step = result.episode.get_step("sense")
        assert "epistemics" in step.mcp_bindings
        assert step.mcp_bindings["epistemics"]["status"] == "HYPOTHESIZED"
        assert step.mcp_bindings["epistemics"]["confidence"] == 0.5
        assert step.mcp_bindings["epistemics"]["calibration_note"] == "Pre-execution estimate"
    
    def test_compile_includes_evidence_defaults(self, compiler):
        """Compiled steps include evidence defaults."""
        ctx = create_context()
        result = compiler.compile(TEMPLATE_A, ctx)
        
        step = result.episode.get_step("sense")
        assert "evidence" in step.mcp_bindings
        assert step.mcp_bindings["evidence"]["evidence_refs"] == []
        assert step.mcp_bindings["evidence"]["evidence_absent_reason"] == "Step not yet executed"
    
    def test_compile_applies_step_bindings(self, compiler):
        """Step-specific bindings override context."""
        # Template B has decision_outcome binding
        ctx = create_context()
        result = compiler.compile(TEMPLATE_B, ctx)
        
        entry_step = result.episode.get_step("decide_verify")
        assert entry_step.mcp_bindings.get("decision_outcome") == "VERIFY_FIRST"
    
    def test_compile_with_validation(self, validating_compiler):
        """Compiler validates template before compilation."""
        ctx = create_context()
        result = validating_compiler.compile(TEMPLATE_A, ctx)
        assert result.success is True
    
    def test_compile_step_sequence_numbers(self, compiler):
        """Compiled steps have correct sequence numbers."""
        ctx = create_context()
        result = compiler.compile(TEMPLATE_A, ctx)
        
        for i, step in enumerate(result.episode.steps):
            assert step.sequence_number == i
    
    def test_compile_preserves_entry_exit(self, compiler):
        """Compiled episode preserves entry and exit steps."""
        ctx = create_context()
        result = compiler.compile(TEMPLATE_A, ctx)
        
        assert result.episode.entry_step == TEMPLATE_A.entry_step
        assert result.episode.exit_steps == TEMPLATE_A.exit_steps
    
    def test_compile_creates_context_snapshot(self, compiler):
        """Compiled episode includes context snapshot."""
        ctx = create_context(
            stakes_level=StakesLevel.HIGH,
            quality_tier=QualityTier.SUPERB,
        )
        result = compiler.compile(TEMPLATE_A, ctx)
        
        snapshot = result.episode.context_snapshot
        assert snapshot["stakes_level"] == "HIGH"
        assert snapshot["quality_tier"] == "SUPERB"
        assert "compiled_at" in snapshot


class TestConstraintChecking:
    """Tests for template constraint validation."""
    
    @pytest.fixture
    def compiler(self):
        return create_compiler()
    
    def test_tier_too_low(self, compiler):
        """Fails when context tier below template requirement."""
        # Template D requires SUPERB
        ctx = create_context(quality_tier=QualityTier.PAR)
        result = compiler.compile(TEMPLATE_D, ctx)
        
        assert result.success is False
        assert any("tier" in e.message.lower() for e in result.errors)
    
    def test_tier_meets_requirement(self, compiler):
        """Succeeds when context tier meets requirement."""
        ctx = create_context(quality_tier=QualityTier.SUPERB)
        result = compiler.compile(TEMPLATE_D, ctx)
        
        assert result.success is True
    
    def test_tier_exceeds_requirement(self, compiler):
        """Succeeds when context tier exceeds requirement."""
        # Template A requires PAR
        ctx = create_context(quality_tier=QualityTier.SUPERB)
        result = compiler.compile(TEMPLATE_A, ctx)
        
        assert result.success is True
    
    def test_tools_state_not_allowed(self, compiler):
        """Fails when tools state not in allowed list."""
        # Template D requires TOOLS_OK only
        ctx = create_context(
            quality_tier=QualityTier.SUPERB,
            tools_state=ToolsState.TOOLS_PARTIAL,
        )
        result = compiler.compile(TEMPLATE_D, ctx)
        
        assert result.success is False
        assert any("tools" in e.message.lower() for e in result.errors)
    
    def test_escalation_allows_any_tools(self, compiler):
        """Template E allows any tools state."""
        ctx = create_context(tools_state=ToolsState.TOOLS_DOWN)
        result = compiler.compile(TEMPLATE_E, ctx)
        
        assert result.success is True
    
    def test_multiple_constraint_violations(self, compiler):
        """Multiple constraint violations reported together."""
        # Template D requires SUPERB + TOOLS_OK
        ctx = create_context(
            quality_tier=QualityTier.PAR,
            tools_state=ToolsState.TOOLS_DOWN,
        )
        result = compiler.compile(TEMPLATE_D, ctx)
        
        assert result.success is False
        assert len(result.errors) >= 2


class TestCompilationResult:
    """Tests for compilation result structure."""
    
    def test_success_has_episode(self):
        """Successful result has episode, no errors."""
        compiler = create_compiler()
        result = compiler.compile(TEMPLATE_A, create_context())
        
        assert result.success is True
        assert result.episode is not None
        assert len(result.errors) == 0
    
    def test_failure_has_errors(self):
        """Failed result has errors, no episode."""
        compiler = create_compiler()
        ctx = create_context(quality_tier=QualityTier.PAR)
        result = compiler.compile(TEMPLATE_D, ctx)  # Needs SUPERB
        
        assert result.success is False
        assert result.episode is None
        assert len(result.errors) > 0
    
    def test_error_structure(self):
        """Errors have step_id and message."""
        compiler = create_compiler()
        ctx = create_context(quality_tier=QualityTier.PAR)
        result = compiler.compile(TEMPLATE_D, ctx)
        
        error = result.errors[0]
        assert hasattr(error, "step_id")
        assert hasattr(error, "message")
        assert isinstance(error.message, str)


class TestAllCanonicalTemplates:
    """Test compilation of all canonical templates."""
    
    @pytest.fixture
    def compiler(self):
        return create_compiler()
    
    def test_compile_all_templates(self, compiler):
        """All canonical templates can compile with appropriate contexts."""
        # Template A: PAR tier, TOOLS_OK or TOOLS_PARTIAL
        ctx_a = create_context(quality_tier=QualityTier.PAR, tools_state=ToolsState.TOOLS_OK)
        result_a = compiler.compile(TEMPLATE_A, ctx_a)
        assert result_a.success is True, f"Template A failed: {result_a.errors}"
        
        # Template B: PAR tier, TOOLS_OK
        ctx_b = create_context(quality_tier=QualityTier.PAR, tools_state=ToolsState.TOOLS_OK)
        result_b = compiler.compile(TEMPLATE_B, ctx_b)
        assert result_b.success is True, f"Template B failed: {result_b.errors}"
        
        # Template C: PAR tier, TOOLS_OK or TOOLS_PARTIAL
        ctx_c = create_context(quality_tier=QualityTier.PAR, tools_state=ToolsState.TOOLS_OK)
        result_c = compiler.compile(TEMPLATE_C, ctx_c)
        assert result_c.success is True, f"Template C failed: {result_c.errors}"
        
        # Template D: SUPERB tier, TOOLS_OK only
        ctx_d = create_context(quality_tier=QualityTier.SUPERB, tools_state=ToolsState.TOOLS_OK)
        result_d = compiler.compile(TEMPLATE_D, ctx_d)
        assert result_d.success is True, f"Template D failed: {result_d.errors}"
        
        # Template E: SUBPAR tier, any tools
        ctx_e = create_context(quality_tier=QualityTier.SUBPAR, tools_state=ToolsState.TOOLS_OK)
        result_e = compiler.compile(TEMPLATE_E, ctx_e)
        assert result_e.success is True, f"Template E failed: {result_e.errors}"
        
        # Template F: PAR tier, TOOLS_PARTIAL or TOOLS_DOWN
        ctx_f = create_context(quality_tier=QualityTier.PAR, tools_state=ToolsState.TOOLS_PARTIAL)
        result_f = compiler.compile(TEMPLATE_F, ctx_f)
        assert result_f.success is True, f"Template F failed: {result_f.errors}"
        
        # Template G: SUPERB tier, TOOLS_OK only
        ctx_g = create_context(quality_tier=QualityTier.SUPERB, tools_state=ToolsState.TOOLS_OK)
        result_g = compiler.compile(TEMPLATE_G, ctx_g)
        assert result_g.success is True, f"Template G failed: {result_g.errors}"
    
    def test_all_templates_have_steps(self, compiler):
        """All compiled episodes have steps."""
        templates = [
            (TEMPLATE_A, QualityTier.PAR, ToolsState.TOOLS_OK),
            (TEMPLATE_B, QualityTier.PAR, ToolsState.TOOLS_OK),
            (TEMPLATE_C, QualityTier.PAR, ToolsState.TOOLS_OK),
            (TEMPLATE_D, QualityTier.SUPERB, ToolsState.TOOLS_OK),
            (TEMPLATE_E, QualityTier.SUBPAR, ToolsState.TOOLS_OK),
            (TEMPLATE_F, QualityTier.PAR, ToolsState.TOOLS_PARTIAL),
            (TEMPLATE_G, QualityTier.SUPERB, ToolsState.TOOLS_OK),
        ]
        
        for template, tier, tools_state in templates:
            ctx = create_context(quality_tier=tier, tools_state=tools_state)
            result = compiler.compile(template, ctx)
            assert result.success is True
            assert len(result.episode.steps) > 0
            assert len(result.episode.steps) == len(template.steps)
