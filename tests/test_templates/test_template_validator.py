"""Tests for template validator."""

import pytest

from omen.vocabulary import (
    TemplateID,
    IntentClass,
    LayerSource,
    FSMState,
    PacketType,
    QualityTier,
    ToolsState,
)
from omen.templates import (
    EpisodeTemplate,
    TemplateStep,
    TemplateConstraints,
    TemplateValidator,
    create_template_validator,
    get_all_templates,
    LAYER_PACKET_CONTRACTS,
)


@pytest.fixture
def validator():
    """Create validator instance."""
    return create_template_validator()


@pytest.fixture
def valid_template():
    """A minimal valid template."""
    return EpisodeTemplate(
        template_id=TemplateID.TEMPLATE_A,
        name="Test",
        description="Test template",
        intent_class=IntentClass.SENSE,
        constraints=TemplateConstraints(
            min_tier=QualityTier.PAR,
            tools_state=[ToolsState.TOOLS_OK],
            write_allowed=False,
        ),
        steps=[
            TemplateStep(
                step_id="start",
                owner_layer=LayerSource.LAYER_6,
                fsm_state=FSMState.S0_IDLE,
                packet_type=None,
                next_steps=["sense"],
            ),
            TemplateStep(
                step_id="sense",
                owner_layer=LayerSource.LAYER_6,
                fsm_state=FSMState.S1_SENSE,
                packet_type=PacketType.OBSERVATION,
                next_steps=["model"],
            ),
            TemplateStep(
                step_id="model",
                owner_layer=LayerSource.LAYER_6,
                fsm_state=FSMState.S2_MODEL,
                packet_type=PacketType.BELIEF_UPDATE,
                next_steps=["end"],
            ),
            TemplateStep(
                step_id="end",
                owner_layer=LayerSource.LAYER_5,
                fsm_state=FSMState.S0_IDLE,
                packet_type=None,
                next_steps=[],
            ),
        ],
        entry_step="start",
        exit_steps=["end"],
    )


class TestValidatorBasics:
    """Basic validator functionality."""
    
    def test_create_validator(self):
        """Factory creates validator."""
        v = create_template_validator()
        assert isinstance(v, TemplateValidator)
    
    def test_valid_template_passes(self, validator, valid_template):
        """Valid template passes validation."""
        result = validator.validate(valid_template)
        assert result.valid is True
        assert len(result.errors) == 0
    
    def test_validate_all(self, validator):
        """validate_all checks multiple templates."""
        templates = get_all_templates()
        results = validator.validate_all(templates)
        assert len(results) == 7
        for tid, result in results.items():
            assert result.template_id == tid


class TestStepConnectivity:
    """Tests for step connectivity validation."""
    
    def test_broken_next_step_reference(self, validator):
        """Detects invalid next_steps reference."""
        template = EpisodeTemplate(
            template_id=TemplateID.TEMPLATE_A,
            name="Broken",
            description="Has broken reference",
            intent_class=IntentClass.SENSE,
            constraints=TemplateConstraints(
                min_tier=QualityTier.PAR,
                tools_state=[ToolsState.TOOLS_OK],
                write_allowed=False,
            ),
            steps=[
                TemplateStep(
                    step_id="start",
                    owner_layer=LayerSource.LAYER_5,
                    fsm_state=FSMState.S0_IDLE,
                    packet_type=None,
                    next_steps=["nonexistent"],  # Broken!
                ),
            ],
            entry_step="start",
            exit_steps=["start"],
        )
        result = validator.validate(template)
        assert result.valid is False
        assert any(e.rule == "step_connectivity" for e in result.errors)


class TestEntryExit:
    """Tests for entry/exit validation."""
    
    def test_exit_step_has_next_steps(self, validator):
        """Exit step with next_steps is an error."""
        template = EpisodeTemplate(
            template_id=TemplateID.TEMPLATE_A,
            name="Bad Exit",
            description="Exit has next steps",
            intent_class=IntentClass.SENSE,
            constraints=TemplateConstraints(
                min_tier=QualityTier.PAR,
                tools_state=[ToolsState.TOOLS_OK],
                write_allowed=False,
            ),
            steps=[
                TemplateStep(
                    step_id="start",
                    owner_layer=LayerSource.LAYER_5,
                    fsm_state=FSMState.S0_IDLE,
                    packet_type=None,
                    next_steps=["end"],
                ),
                TemplateStep(
                    step_id="end",
                    owner_layer=LayerSource.LAYER_5,
                    fsm_state=FSMState.S0_IDLE,
                    packet_type=None,
                    next_steps=["start"],  # Exit shouldn't have next!
                ),
            ],
            entry_step="start",
            exit_steps=["end"],
        )
        result = validator.validate(template)
        assert result.valid is False
        assert any(e.rule == "exit_valid" for e in result.errors)


class TestFSMCompliance:
    """Tests for FSM transition validation."""
    
    def test_illegal_transition(self, validator):
        """Catches illegal FSM transition."""
        template = EpisodeTemplate(
            template_id=TemplateID.TEMPLATE_A,
            name="Illegal FSM",
            description="IDLE to EXECUTE is illegal",
            intent_class=IntentClass.SENSE,
            constraints=TemplateConstraints(
                min_tier=QualityTier.PAR,
                tools_state=[ToolsState.TOOLS_OK],
                write_allowed=False,
            ),
            steps=[
                TemplateStep(
                    step_id="start",
                    owner_layer=LayerSource.LAYER_5,
                    fsm_state=FSMState.S0_IDLE,
                    packet_type=None,
                    next_steps=["bad_execute"],
                ),
                TemplateStep(
                    step_id="bad_execute",
                    owner_layer=LayerSource.LAYER_6,
                    fsm_state=FSMState.S6_EXECUTE,  # Can't go IDLE→EXECUTE!
                    packet_type=PacketType.TASK_RESULT,
                    next_steps=[],
                ),
            ],
            entry_step="start",
            exit_steps=["bad_execute"],
        )
        result = validator.validate(template)
        assert result.valid is False
        assert any(e.rule == "fsm_compliance" for e in result.errors)


class TestLayerContracts:
    """Tests for layer contract validation."""
    
    def test_layer_emits_wrong_packet(self, validator):
        """Catches layer emitting disallowed packet type."""
        template = EpisodeTemplate(
            template_id=TemplateID.TEMPLATE_A,
            name="Wrong Packet",
            description="L6 can't emit Decision",
            intent_class=IntentClass.SENSE,
            constraints=TemplateConstraints(
                min_tier=QualityTier.PAR,
                tools_state=[ToolsState.TOOLS_OK],
                write_allowed=False,
            ),
            steps=[
                TemplateStep(
                    step_id="start",
                    owner_layer=LayerSource.LAYER_5,
                    fsm_state=FSMState.S0_IDLE,
                    packet_type=None,
                    next_steps=["bad_decision"],
                ),
                TemplateStep(
                    step_id="bad_decision",
                    owner_layer=LayerSource.LAYER_6,  # L6 can't emit Decision!
                    fsm_state=FSMState.S3_DECIDE,
                    packet_type=PacketType.DECISION,
                    next_steps=[],
                ),
            ],
            entry_step="start",
            exit_steps=["bad_decision"],
        )
        result = validator.validate(template)
        assert result.valid is False
        assert any(e.rule == "layer_contract" for e in result.errors)
    
    def test_all_layer_contracts_defined(self):
        """All layers have defined contracts."""
        for layer in LayerSource:
            assert layer in LAYER_PACKET_CONTRACTS


class TestReachability:
    """Tests for step reachability validation."""
    
    def test_orphaned_step(self, validator):
        """Catches unreachable step."""
        template = EpisodeTemplate(
            template_id=TemplateID.TEMPLATE_A,
            name="Orphan",
            description="Has unreachable step",
            intent_class=IntentClass.SENSE,
            constraints=TemplateConstraints(
                min_tier=QualityTier.PAR,
                tools_state=[ToolsState.TOOLS_OK],
                write_allowed=False,
            ),
            steps=[
                TemplateStep(
                    step_id="start",
                    owner_layer=LayerSource.LAYER_5,
                    fsm_state=FSMState.S0_IDLE,
                    packet_type=None,
                    next_steps=["end"],
                ),
                TemplateStep(
                    step_id="orphan",  # Not referenced by anyone!
                    owner_layer=LayerSource.LAYER_5,
                    fsm_state=FSMState.S0_IDLE,
                    packet_type=None,
                    next_steps=[],
                ),
                TemplateStep(
                    step_id="end",
                    owner_layer=LayerSource.LAYER_5,
                    fsm_state=FSMState.S0_IDLE,
                    packet_type=None,
                    next_steps=[],
                ),
            ],
            entry_step="start",
            exit_steps=["end"],
        )
        result = validator.validate(template)
        assert result.valid is False
        assert any(
            e.rule == "reachability" and "orphan" in e.message 
            for e in result.errors
        )


class TestDeadEnds:
    """Tests for dead end detection (warnings)."""
    
    def test_dead_end_warning(self, validator):
        """Non-exit step with no next_steps generates warning."""
        template = EpisodeTemplate(
            template_id=TemplateID.TEMPLATE_A,
            name="Dead End",
            description="Non-exit with no next",
            intent_class=IntentClass.SENSE,
            constraints=TemplateConstraints(
                min_tier=QualityTier.PAR,
                tools_state=[ToolsState.TOOLS_OK],
                write_allowed=False,
            ),
            steps=[
                TemplateStep(
                    step_id="start",
                    owner_layer=LayerSource.LAYER_5,
                    fsm_state=FSMState.S0_IDLE,
                    packet_type=None,
                    next_steps=["dead"],
                ),
                TemplateStep(
                    step_id="dead",
                    owner_layer=LayerSource.LAYER_5,
                    fsm_state=FSMState.S0_IDLE,
                    packet_type=None,
                    next_steps=[],  # Dead end but not marked as exit
                ),
                TemplateStep(
                    step_id="end",
                    owner_layer=LayerSource.LAYER_5,
                    fsm_state=FSMState.S0_IDLE,
                    packet_type=None,
                    next_steps=[],
                ),
            ],
            entry_step="start",
            exit_steps=["end"],
        )
        result = validator.validate(template)
        # Dead end is warning, not error
        assert any(w.rule == "dead_end" for w in result.warnings)


class TestCanonicalTemplatesValidation:
    """Validate all canonical templates pass."""
    
    def test_all_canonical_templates_valid(self, validator):
        """All 7 canonical templates pass validation."""
        templates = get_all_templates()
        for template in templates:
            result = validator.validate(template)
            assert result.valid is True, (
                f"Template {template.template_id} failed: "
                f"{[e.message for e in result.errors]}"
            )
    
    def test_no_warnings_in_canonical(self, validator):
        """Canonical templates should have no warnings."""
        templates = get_all_templates()
        for template in templates:
            result = validator.validate(template)
            assert len(result.warnings) == 0, (
                f"Template {template.template_id} has warnings: "
                f"{[w.message for w in result.warnings]}"
            )
