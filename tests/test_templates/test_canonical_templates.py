"""Tests for canonical template definitions."""

import pytest

from omen.vocabulary import (
    TemplateID,
    IntentClass,
    QualityTier,
    ToolsState,
    FSMState,
    PacketType,
)
from omen.templates import (
    TEMPLATE_A,
    TEMPLATE_B,
    TEMPLATE_C,
    TEMPLATE_D,
    TEMPLATE_E,
    TEMPLATE_F,
    TEMPLATE_G,
    CANONICAL_TEMPLATES,
    get_template,
    get_all_templates,
)


class TestTemplateRegistry:
    """Tests for template registry functions."""
    
    def test_all_templates_registered(self):
        """All 8 canonical templates are in registry (A-H)."""
        assert len(CANONICAL_TEMPLATES) == 8
        for tid in TemplateID:
            assert tid in CANONICAL_TEMPLATES
    
    def test_get_template(self):
        """get_template returns correct template."""
        template = get_template(TemplateID.TEMPLATE_A)
        assert template.template_id == TemplateID.TEMPLATE_A
        assert template.name == "Grounding Loop"
    
    def test_get_all_templates(self):
        """get_all_templates returns all 8 (A-H)."""
        templates = get_all_templates()
        assert len(templates) == 8
        ids = {t.template_id for t in templates}
        assert ids == set(TemplateID)


class TestTemplateA:
    """Tests for Template A: Grounding Loop."""
    
    def test_basic_properties(self):
        """Template A has correct metadata."""
        assert TEMPLATE_A.template_id == TemplateID.TEMPLATE_A
        assert TEMPLATE_A.name == "Grounding Loop"
        assert TEMPLATE_A.intent_class == IntentClass.SENSE
    
    def test_constraints(self):
        """Template A constraints allow sensing."""
        assert TEMPLATE_A.constraints.min_tier == QualityTier.PAR
        assert ToolsState.TOOLS_OK in TEMPLATE_A.constraints.tools_state
        assert TEMPLATE_A.constraints.write_allowed is False
    
    def test_fsm_path(self):
        """Template A follows S0→S1→S2→S3→S7→S0 path."""
        expected_states = [
            FSMState.S0_IDLE,   # idle_start
            FSMState.S1_SENSE,  # sense
            FSMState.S2_MODEL,  # model
            FSMState.S3_DECIDE, # decide
            FSMState.S7_REVIEW, # review
            FSMState.S0_IDLE,   # idle_end
        ]
        actual_states = [step.fsm_state for step in TEMPLATE_A.steps]
        assert actual_states == expected_states
    
    def test_step_connectivity(self):
        """All next_steps references are valid."""
        step_ids = TEMPLATE_A.get_step_ids()
        for step in TEMPLATE_A.steps:
            for next_id in step.next_steps:
                assert next_id in step_ids


class TestTemplateB:
    """Tests for Template B: Verification Loop."""
    
    def test_basic_properties(self):
        """Template B has correct metadata."""
        assert TEMPLATE_B.template_id == TemplateID.TEMPLATE_B
        assert TEMPLATE_B.intent_class == IntentClass.VERIFY
    
    def test_verify_first_binding(self):
        """Entry step has VERIFY_FIRST binding."""
        entry = TEMPLATE_B.get_step(TEMPLATE_B.entry_step)
        assert entry.bindings.get("decision_outcome") == "VERIFY_FIRST"
    
    def test_includes_verification_plan(self):
        """Template B includes VerificationPlan step."""
        packet_types = [s.packet_type for s in TEMPLATE_B.steps]
        assert PacketType.VERIFICATION_PLAN in packet_types
    
    def test_step_connectivity(self):
        """All next_steps references are valid."""
        step_ids = TEMPLATE_B.get_step_ids()
        for step in TEMPLATE_B.steps:
            for next_id in step.next_steps:
                assert next_id in step_ids


class TestTemplateC:
    """Tests for Template C: Read-Only Act."""
    
    def test_no_authorization_step(self):
        """Template C skips authorization (READ only)."""
        states = [s.fsm_state for s in TEMPLATE_C.steps]
        assert FSMState.S5_AUTHORIZE not in states
    
    def test_write_not_allowed(self):
        """Template C does not allow writes."""
        assert TEMPLATE_C.constraints.write_allowed is False
    
    def test_act_binding(self):
        """Entry step has ACT binding."""
        entry = TEMPLATE_C.get_step(TEMPLATE_C.entry_step)
        assert entry.bindings.get("decision_outcome") == "ACT"
    
    def test_step_connectivity(self):
        """All next_steps references are valid."""
        step_ids = TEMPLATE_C.get_step_ids()
        for step in TEMPLATE_C.steps:
            for next_id in step.next_steps:
                assert next_id in step_ids


class TestTemplateD:
    """Tests for Template D: Write Act."""
    
    def test_requires_authorization(self):
        """Template D includes authorization step."""
        states = [s.fsm_state for s in TEMPLATE_D.steps]
        assert FSMState.S5_AUTHORIZE in states
    
    def test_write_allowed(self):
        """Template D allows writes."""
        assert TEMPLATE_D.constraints.write_allowed is True
    
    def test_requires_superb(self):
        """Template D requires SUPERB tier."""
        assert TEMPLATE_D.constraints.min_tier == QualityTier.SUPERB
    
    def test_requires_full_tools(self):
        """Template D requires TOOLS_OK."""
        assert TEMPLATE_D.constraints.tools_state == [ToolsState.TOOLS_OK]
    
    def test_act_binding(self):
        """Entry step has ACT binding."""
        entry = TEMPLATE_D.get_step(TEMPLATE_D.entry_step)
        assert entry.bindings.get("decision_outcome") == "ACT"
    
    def test_step_connectivity(self):
        """All next_steps references are valid."""
        step_ids = TEMPLATE_D.get_step_ids()
        for step in TEMPLATE_D.steps:
            for next_id in step.next_steps:
                assert next_id in step_ids


class TestTemplateE:
    """Tests for Template E: Escalation."""
    
    def test_ends_in_escalated(self):
        """Template E terminates in S8_ESCALATED."""
        exit_step = TEMPLATE_E.get_step(TEMPLATE_E.exit_steps[0])
        assert exit_step.fsm_state == FSMState.S8_ESCALATED
    
    def test_allows_all_tools_states(self):
        """Template E works regardless of tools state."""
        assert ToolsState.TOOLS_DOWN in TEMPLATE_E.constraints.tools_state
    
    def test_allows_subpar(self):
        """Template E can execute at SUBPAR tier."""
        assert TEMPLATE_E.constraints.min_tier == QualityTier.SUBPAR
    
    def test_escalate_binding(self):
        """Entry step has ESCALATE binding."""
        entry = TEMPLATE_E.get_step(TEMPLATE_E.entry_step)
        assert entry.bindings.get("decision_outcome") == "ESCALATE"
    
    def test_step_connectivity(self):
        """All next_steps references are valid."""
        step_ids = TEMPLATE_E.get_step_ids()
        for step in TEMPLATE_E.steps:
            for next_id in step.next_steps:
                assert next_id in step_ids


class TestTemplateF:
    """Tests for Template F: Degraded Tools."""
    
    def test_only_degraded_tools(self):
        """Template F only applies to degraded tools states."""
        assert ToolsState.TOOLS_OK not in TEMPLATE_F.constraints.tools_state
        assert ToolsState.TOOLS_PARTIAL in TEMPLATE_F.constraints.tools_state
        assert ToolsState.TOOLS_DOWN in TEMPLATE_F.constraints.tools_state
    
    def test_no_writes(self):
        """Template F disallows writes when degraded."""
        assert TEMPLATE_F.constraints.write_allowed is False
    
    def test_ends_in_escalated(self):
        """Template F ends in escalation state."""
        exit_step = TEMPLATE_F.get_step(TEMPLATE_F.exit_steps[0])
        assert exit_step.fsm_state == FSMState.S8_ESCALATED
    
    def test_step_connectivity(self):
        """All next_steps references are valid."""
        step_ids = TEMPLATE_F.get_step_ids()
        for step in TEMPLATE_F.steps:
            for next_id in step.next_steps:
                assert next_id in step_ids


class TestTemplateG:
    """Tests for Template G: Compile-to-Code."""
    
    def test_compilation_intent(self):
        """Template G has COMPILE intent."""
        assert TEMPLATE_G.intent_class == IntentClass.COMPILE
    
    def test_requires_superb_and_tools(self):
        """Template G requires highest tier and full tools."""
        assert TEMPLATE_G.constraints.min_tier == QualityTier.SUPERB
        assert TEMPLATE_G.constraints.tools_state == [ToolsState.TOOLS_OK]
    
    def test_includes_verification_and_auth(self):
        """Template G includes verification planning and authorization."""
        states = [s.fsm_state for s in TEMPLATE_G.steps]
        assert FSMState.S4_VERIFY in states
        assert FSMState.S5_AUTHORIZE in states
    
    def test_write_allowed(self):
        """Template G allows writes (code generation)."""
        assert TEMPLATE_G.constraints.write_allowed is True
    
    def test_step_connectivity(self):
        """All next_steps references are valid."""
        step_ids = TEMPLATE_G.get_step_ids()
        for step in TEMPLATE_G.steps:
            for next_id in step.next_steps:
                assert next_id in step_ids
