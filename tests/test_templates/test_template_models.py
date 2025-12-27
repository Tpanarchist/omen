"""Tests for template data models."""

import pytest
from pydantic import ValidationError

from omen.vocabulary import (
    TemplateID,
    IntentClass,
    LayerSource,
    FSMState,
    PacketType,
    QualityTier,
    ToolsState,
)
from omen.templates import TemplateStep, TemplateConstraints, EpisodeTemplate


class TestTemplateStep:
    """Tests for TemplateStep model."""
    
    def test_valid_step(self):
        """Create a valid template step."""
        step = TemplateStep(
            step_id="sense",
            owner_layer=LayerSource.LAYER_6,
            fsm_state=FSMState.S1_SENSE,
            packet_type=PacketType.OBSERVATION,
            next_steps=["model"],
        )
        assert step.step_id == "sense"
        assert step.owner_layer == LayerSource.LAYER_6
        assert step.fsm_state == FSMState.S1_SENSE
        assert step.packet_type == PacketType.OBSERVATION
        assert step.next_steps == ["model"]
        assert step.bindings == {}
    
    def test_terminal_step_no_packet(self):
        """Terminal steps can have None packet_type."""
        step = TemplateStep(
            step_id="idle",
            owner_layer=LayerSource.LAYER_5,
            fsm_state=FSMState.S0_IDLE,
            packet_type=None,
            next_steps=[],
        )
        assert step.packet_type is None
        assert step.next_steps == []
    
    def test_step_with_bindings(self):
        """Steps can include MCP field bindings."""
        step = TemplateStep(
            step_id="decide",
            owner_layer=LayerSource.LAYER_5,
            fsm_state=FSMState.S3_DECIDE,
            packet_type=PacketType.DECISION,
            next_steps=["execute"],
            bindings={"quality_tier": "PAR", "verification_requirement": "VERIFY_ONE"},
        )
        assert step.bindings["quality_tier"] == "PAR"
    
    def test_empty_step_id_rejected(self):
        """Empty step_id is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            TemplateStep(
                step_id="",
                owner_layer=LayerSource.LAYER_6,
                fsm_state=FSMState.S1_SENSE,
                packet_type=PacketType.OBSERVATION,
            )
        assert "step_id cannot be empty" in str(exc_info.value)
    
    def test_whitespace_step_id_rejected(self):
        """Whitespace-only step_id is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            TemplateStep(
                step_id="   ",
                owner_layer=LayerSource.LAYER_6,
                fsm_state=FSMState.S1_SENSE,
                packet_type=PacketType.OBSERVATION,
            )
        assert "step_id cannot be empty" in str(exc_info.value)


class TestTemplateConstraints:
    """Tests for TemplateConstraints model."""
    
    def test_valid_constraints(self):
        """Create valid template constraints."""
        constraints = TemplateConstraints(
            min_tier=QualityTier.PAR,
            tools_state=[ToolsState.TOOLS_OK, ToolsState.TOOLS_PARTIAL],
            write_allowed=False,
        )
        assert constraints.min_tier == QualityTier.PAR
        assert ToolsState.TOOLS_OK in constraints.tools_state
        assert constraints.write_allowed is False
    
    def test_write_allowed_true(self):
        """Templates can allow writes."""
        constraints = TemplateConstraints(
            min_tier=QualityTier.SUPERB,
            tools_state=[ToolsState.TOOLS_OK],
            write_allowed=True,
        )
        assert constraints.write_allowed is True
    
    def test_empty_tools_state_rejected(self):
        """Empty tools_state list is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            TemplateConstraints(
                min_tier=QualityTier.PAR,
                tools_state=[],
                write_allowed=False,
            )
        assert "at least one state" in str(exc_info.value)


class TestEpisodeTemplate:
    """Tests for EpisodeTemplate model."""
    
    @pytest.fixture
    def minimal_template(self):
        """Minimal valid template with two steps."""
        return EpisodeTemplate(
            template_id=TemplateID.TEMPLATE_A,
            name="Test Template",
            description="A minimal test template",
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
                    fsm_state=FSMState.S1_SENSE,
                    packet_type=PacketType.OBSERVATION,
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
    
    def test_valid_template(self, minimal_template):
        """Create a valid episode template."""
        assert minimal_template.template_id == TemplateID.TEMPLATE_A
        assert minimal_template.name == "Test Template"
        assert len(minimal_template.steps) == 2
        assert minimal_template.entry_step == "start"
        assert minimal_template.exit_steps == ["end"]
    
    def test_get_step(self, minimal_template):
        """get_step returns correct step or None."""
        step = minimal_template.get_step("start")
        assert step is not None
        assert step.step_id == "start"
        
        missing = minimal_template.get_step("nonexistent")
        assert missing is None
    
    def test_get_step_ids(self, minimal_template):
        """get_step_ids returns all step IDs."""
        ids = minimal_template.get_step_ids()
        assert ids == {"start", "end"}
    
    def test_invalid_entry_step_rejected(self):
        """entry_step must reference existing step."""
        with pytest.raises(ValidationError) as exc_info:
            EpisodeTemplate(
                template_id=TemplateID.TEMPLATE_A,
                name="Bad Template",
                description="Entry step doesn't exist",
                intent_class=IntentClass.SENSE,
                constraints=TemplateConstraints(
                    min_tier=QualityTier.PAR,
                    tools_state=[ToolsState.TOOLS_OK],
                    write_allowed=False,
                ),
                steps=[
                    TemplateStep(
                        step_id="only_step",
                        owner_layer=LayerSource.LAYER_6,
                        fsm_state=FSMState.S1_SENSE,
                        packet_type=PacketType.OBSERVATION,
                        next_steps=[],
                    ),
                ],
                entry_step="nonexistent",
                exit_steps=["only_step"],
            )
        assert "entry_step" in str(exc_info.value)
        assert "not found" in str(exc_info.value)
    
    def test_invalid_exit_step_rejected(self):
        """exit_steps must reference existing steps."""
        with pytest.raises(ValidationError) as exc_info:
            EpisodeTemplate(
                template_id=TemplateID.TEMPLATE_A,
                name="Bad Template",
                description="Exit step doesn't exist",
                intent_class=IntentClass.SENSE,
                constraints=TemplateConstraints(
                    min_tier=QualityTier.PAR,
                    tools_state=[ToolsState.TOOLS_OK],
                    write_allowed=False,
                ),
                steps=[
                    TemplateStep(
                        step_id="only_step",
                        owner_layer=LayerSource.LAYER_6,
                        fsm_state=FSMState.S1_SENSE,
                        packet_type=PacketType.OBSERVATION,
                        next_steps=[],
                    ),
                ],
                entry_step="only_step",
                exit_steps=["nonexistent"],
            )
        assert "exit_step" in str(exc_info.value)
        assert "not found" in str(exc_info.value)
    
    def test_empty_steps_rejected(self):
        """Template must have at least one step."""
        with pytest.raises(ValidationError) as exc_info:
            EpisodeTemplate(
                template_id=TemplateID.TEMPLATE_A,
                name="Empty Template",
                description="No steps",
                intent_class=IntentClass.SENSE,
                constraints=TemplateConstraints(
                    min_tier=QualityTier.PAR,
                    tools_state=[ToolsState.TOOLS_OK],
                    write_allowed=False,
                ),
                steps=[],
                entry_step="start",
                exit_steps=["end"],
            )
        assert "at least one step" in str(exc_info.value)
    
    def test_empty_exit_steps_rejected(self):
        """Template must have at least one exit step."""
        with pytest.raises(ValidationError) as exc_info:
            EpisodeTemplate(
                template_id=TemplateID.TEMPLATE_A,
                name="No Exit Template",
                description="No exit steps",
                intent_class=IntentClass.SENSE,
                constraints=TemplateConstraints(
                    min_tier=QualityTier.PAR,
                    tools_state=[ToolsState.TOOLS_OK],
                    write_allowed=False,
                ),
                steps=[
                    TemplateStep(
                        step_id="only_step",
                        owner_layer=LayerSource.LAYER_6,
                        fsm_state=FSMState.S1_SENSE,
                        packet_type=PacketType.OBSERVATION,
                        next_steps=[],
                    ),
                ],
                entry_step="only_step",
                exit_steps=[],
            )
        assert "at least one exit step" in str(exc_info.value)


class TestTemplateSerialization:
    """Tests for template JSON serialization."""
    
    def test_step_to_dict(self):
        """TemplateStep serializes to dict."""
        step = TemplateStep(
            step_id="sense",
            owner_layer=LayerSource.LAYER_6,
            fsm_state=FSMState.S1_SENSE,
            packet_type=PacketType.OBSERVATION,
            next_steps=["model"],
        )
        data = step.model_dump()
        assert data["step_id"] == "sense"
        assert data["owner_layer"] == "6"
        assert data["fsm_state"] == "S1_SENSE"
    
    def test_step_from_dict(self):
        """TemplateStep deserializes from dict."""
        data = {
            "step_id": "sense",
            "owner_layer": "6",
            "fsm_state": "S1_SENSE",
            "packet_type": "ObservationPacket",
            "next_steps": ["model"],
        }
        step = TemplateStep.model_validate(data)
        assert step.step_id == "sense"
        assert step.owner_layer == LayerSource.LAYER_6
