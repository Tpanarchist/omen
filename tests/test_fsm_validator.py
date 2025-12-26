"""
Tests for FSM validator.

Validates state transition rules per OMEN.md §10.2, §10.3, §15.4.
"""

import pytest
from uuid import uuid4
from datetime import datetime, timezone, timedelta

from omen.validation import (
    FSMValidator,
    EpisodeState,
    FSMState,
    LEGAL_TRANSITIONS,
    packet_implies_state,
    create_fsm_validator,
)
from omen.schemas import (
    ObservationPacket,
    BeliefUpdatePacket,
    DecisionPacket,
    VerificationPlanPacket,
    TaskDirectivePacket,
    TaskResultPacket,
    ToolAuthorizationToken,
    EscalationPacket,
    IntegrityAlertPacket,
)
from omen.vocabulary import DecisionOutcome, ToolSafety


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def validator() -> FSMValidator:
    return FSMValidator()


@pytest.fixture
def episode_id():
    return uuid4()


@pytest.fixture
def base_header(episode_id):
    def _make_header(packet_type: str):
        return {
            "packet_id": str(uuid4()),
            "packet_type": packet_type,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "layer_source": "5",
            "correlation_id": str(episode_id),
        }
    return _make_header


@pytest.fixture
def base_mcp():
    return {
        "intent": {"summary": "Test", "scope": "test"},
        "stakes": {
            "impact": "LOW",
            "irreversibility": "REVERSIBLE",
            "uncertainty": "LOW",
            "adversariality": "BENIGN",
            "stakes_level": "LOW",
        },
        "quality": {
            "quality_tier": "PAR",
            "satisficing_mode": True,
            "definition_of_done": {"text": "Done", "checks": []},
            "verification_requirement": "OPTIONAL",
        },
        "budgets": {
            "token_budget": 100,
            "tool_call_budget": 5,
            "time_budget_seconds": 60,
            "risk_budget": {"envelope": "minimal", "max_loss": 0},
        },
        "epistemics": {
            "status": "OBSERVED",
            "confidence": 0.8,
            "calibration_note": "Test",
            "freshness_class": "OPERATIONAL",
            "stale_if_older_than_seconds": 300,
            "assumptions": [],
        },
        "evidence": {
            "evidence_refs": [],
            "evidence_absent_reason": "Test",
        },
        "routing": {"task_class": "VERIFY", "tools_state": "tools_ok"},
    }


@pytest.fixture
def valid_observation_payload():
    return {
        "observation_id": str(uuid4()),
        "source": {"source_type": "test", "source_id": "test_source"},
        "observation_type": "test_observation",
        "content": {"data": "test"},
        "observed_at": datetime.now(timezone.utc).isoformat(),
    }


@pytest.fixture
def valid_belief_update_payload():
    return {
        "update_id": str(uuid4()),
        "belief_id": "test_belief",
        "belief_domain": "test_domain",
        "new_state": {
            "claim": "Test claim",
            "status": "OBSERVED",
            "confidence": 0.9,
            "supporting_evidence": [],
        },
        "update_reason": "Test",
        "beliefs_added": [],
        "beliefs_modified": [],
        "beliefs_removed": [],
    }


@pytest.fixture
def valid_task_directive_payload():
    return {
        "directive_id": str(uuid4()),
        "task_class": "VERIFY",
        "task_description": "Test task",
        "instructions": "Do something",
        "tools": [],
        "constraints": {
            "max_tool_calls": 5,
            "max_time_seconds": 60,
            "require_authorization_token": False,
        },
        "success_criteria": "Done",
    }


@pytest.fixture
def valid_task_result_payload():
    return {
        "result_id": str(uuid4()),
        "directive_id": str(uuid4()),
        "status": "SUCCESS",
        "status_reason": "Completed successfully",
        "observations": [],
        "summary": "Task completed",
        "tool_calls": [],
        "resource_usage": {
            "tool_calls_made": 1,
            "time_elapsed_seconds": 0.5,
            "tokens_consumed": 25,
        },
        "execution_started_at": datetime.now(timezone.utc).isoformat(),
        "execution_completed_at": datetime.now(timezone.utc).isoformat(),
    }


# =============================================================================
# TRANSITION TABLE TESTS
# =============================================================================

class TestTransitionTable:
    """Tests for FSM transition table completeness."""

    def test_all_states_have_transitions(self):
        """Every state must have defined transitions."""
        for state in FSMState:
            assert state in LEGAL_TRANSITIONS, f"Missing transitions for {state}"

    def test_safemode_reachable_from_all(self):
        """S9_SAFEMODE must be reachable from every state."""
        for state in FSMState:
            assert FSMState.S9_SAFEMODE in LEGAL_TRANSITIONS[state], \
                f"SAFEMODE not reachable from {state}"

    def test_idle_is_initial_state(self):
        """S0_IDLE should be the starting state."""
        episode = EpisodeState(episode_id=uuid4())
        assert episode.current_state == FSMState.S0_IDLE

    def test_decide_precedes_execute(self):
        """S6_EXECUTE should only be reachable after decision paths."""
        # S6_EXECUTE should come from S3_DECIDE, S4_VERIFY, or S5_AUTHORIZE
        states_that_lead_to_execute = [
            state for state, transitions in LEGAL_TRANSITIONS.items()
            if FSMState.S6_EXECUTE in transitions
        ]
        assert FSMState.S3_DECIDE in states_that_lead_to_execute
        assert FSMState.S4_VERIFY in states_that_lead_to_execute
        assert FSMState.S5_AUTHORIZE in states_that_lead_to_execute


# =============================================================================
# PACKET TO STATE MAPPING TESTS
# =============================================================================

class TestPacketImpliesState:
    """Tests for packet_implies_state function."""

    def test_observation_implies_sense(self, base_header, base_mcp, valid_observation_payload):
        packet = ObservationPacket(
            header=base_header("ObservationPacket"),
            mcp=base_mcp,
            payload=valid_observation_payload,
        )
        assert packet_implies_state(packet) == FSMState.S1_SENSE

    def test_belief_update_implies_model(self, base_header, base_mcp, valid_belief_update_payload):
        packet = BeliefUpdatePacket(
            header=base_header("BeliefUpdatePacket"),
            mcp=base_mcp,
            payload=valid_belief_update_payload,
        )
        assert packet_implies_state(packet) == FSMState.S2_MODEL

    def test_decision_verify_first_implies_verify(self, base_header, base_mcp):
        packet = DecisionPacket(
            header=base_header("DecisionPacket"),
            mcp=base_mcp,
            payload={
                "decision_id": str(uuid4()),
                "decision_outcome": "VERIFY_FIRST",
                "decision_summary": "Verify first",
                "rationale": "Need verification",
                "required_verifications": ["verify_x"],
            },
        )
        assert packet_implies_state(packet) == FSMState.S4_VERIFY

    def test_decision_escalate_implies_escalated(self, base_header, base_mcp):
        packet = DecisionPacket(
            header=base_header("DecisionPacket"),
            mcp=base_mcp,
            payload={
                "decision_id": str(uuid4()),
                "decision_outcome": "ESCALATE",
                "decision_summary": "Escalate",
                "rationale": "Need human",
                "escalation_reason": "High stakes",
            },
        )
        assert packet_implies_state(packet) == FSMState.S8_ESCALATED

    def test_decision_defer_implies_idle(self, base_header, base_mcp):
        packet = DecisionPacket(
            header=base_header("DecisionPacket"),
            mcp=base_mcp,
            payload={
                "decision_id": str(uuid4()),
                "decision_outcome": "DEFER",
                "decision_summary": "Defer",
                "rationale": "Not ready",
            },
        )
        assert packet_implies_state(packet) == FSMState.S0_IDLE

    def test_decision_act_stays_decide(self, base_header, base_mcp):
        """ACT decision stays in S3_DECIDE (next packet determines state)."""
        packet = DecisionPacket(
            header=base_header("DecisionPacket"),
            mcp=base_mcp,
            payload={
                "decision_id": str(uuid4()),
                "decision_outcome": "ACT",
                "decision_summary": "Act",
                "rationale": "Ready to act",
            },
        )
        assert packet_implies_state(packet) == FSMState.S3_DECIDE

    def test_task_directive_implies_execute(self, base_header, base_mcp, valid_task_directive_payload):
        packet = TaskDirectivePacket(
            header=base_header("TaskDirectivePacket"),
            mcp=base_mcp,
            payload=valid_task_directive_payload,
        )
        assert packet_implies_state(packet) == FSMState.S6_EXECUTE


# =============================================================================
# LEGAL TRANSITION TESTS
# =============================================================================

class TestLegalTransitions:
    """Tests for legal FSM transitions."""

    def test_idle_to_sense(self, validator, base_header, base_mcp, episode_id, valid_observation_payload):
        """Can transition from IDLE to SENSE."""
        packet = ObservationPacket(
            header=base_header("ObservationPacket"),
            mcp=base_mcp,
            payload=valid_observation_payload,
        )
        result = validator.validate_transition(packet)
        assert result.valid is True

    def test_sense_to_model(self, validator, base_header, base_mcp, episode_id, valid_observation_payload, valid_belief_update_payload):
        """Can transition from SENSE to MODEL."""
        # First go to SENSE
        obs = ObservationPacket(
            header=base_header("ObservationPacket"),
            mcp=base_mcp,
            payload=valid_observation_payload,
        )
        validator.validate_transition(obs)
        
        # Then go to MODEL
        belief = BeliefUpdatePacket(
            header=base_header("BeliefUpdatePacket"),
            mcp=base_mcp,
            payload=valid_belief_update_payload,
        )
        result = validator.validate_transition(belief)
        assert result.valid is True

    def test_model_to_decide(self, validator, base_header, base_mcp, episode_id, valid_observation_payload, valid_belief_update_payload):
        """Can transition from MODEL to DECIDE."""
        # Setup: IDLE -> SENSE -> MODEL
        obs = ObservationPacket(
            header=base_header("ObservationPacket"),
            mcp=base_mcp,
            payload=valid_observation_payload,
        )
        validator.validate_transition(obs)
        
        belief = BeliefUpdatePacket(
            header=base_header("BeliefUpdatePacket"),
            mcp=base_mcp,
            payload=valid_belief_update_payload,
        )
        validator.validate_transition(belief)
        
        # Now MODEL -> DECIDE
        decision = DecisionPacket(
            header=base_header("DecisionPacket"),
            mcp=base_mcp,
            payload={
                "decision_id": str(uuid4()),
                "decision_outcome": "ACT",
                "decision_summary": "Proceed",
                "rationale": "Safe to proceed",
            },
        )
        result = validator.validate_transition(decision)
        assert result.valid is True


# =============================================================================
# ILLEGAL TRANSITION TESTS
# =============================================================================

class TestIllegalTransitions:
    """Tests for illegal FSM transitions."""

    def test_cannot_execute_from_idle(self, validator, base_header, base_mcp, episode_id, valid_task_directive_payload):
        """Cannot go directly from IDLE to EXECUTE."""
        directive = TaskDirectivePacket(
            header=base_header("TaskDirectivePacket"),
            mcp=base_mcp,
            payload=valid_task_directive_payload,
        )
        result = validator.validate_transition(directive)
        assert result.valid is False
        assert any("Illegal FSM transition" in e for e in result.errors)

    def test_cannot_decide_from_idle(self, validator, base_header, base_mcp, episode_id):
        """Cannot decide without sensing first."""
        decision = DecisionPacket(
            header=base_header("DecisionPacket"),
            mcp=base_mcp,
            payload={
                "decision_id": str(uuid4()),
                "decision_outcome": "ACT",
                "decision_summary": "Proceed",
                "rationale": "Test",
            },
        )
        result = validator.validate_transition(decision)
        assert result.valid is False


# =============================================================================
# VERIFY_FIRST LOOP TESTS
# =============================================================================

class TestVerifyFirstLoop:
    """Tests for VERIFY_FIRST verification loop enforcement."""

    def test_verify_first_sets_requirement(self, validator, base_header, base_mcp, episode_id, valid_observation_payload, valid_belief_update_payload):
        """VERIFY_FIRST decision sets verification requirement."""
        # Setup: IDLE -> SENSE -> MODEL
        obs = ObservationPacket(
            header=base_header("ObservationPacket"),
            mcp=base_mcp,
            payload=valid_observation_payload,
        )
        validator.validate_transition(obs)
        
        belief = BeliefUpdatePacket(
            header=base_header("BeliefUpdatePacket"),
            mcp=base_mcp,
            payload=valid_belief_update_payload,
        )
        validator.validate_transition(belief)
        
        # VERIFY_FIRST decision
        decision = DecisionPacket(
            header=base_header("DecisionPacket"),
            mcp=base_mcp,
            payload={
                "decision_id": str(uuid4()),
                "decision_outcome": "VERIFY_FIRST",
                "decision_summary": "Verify",
                "rationale": "Need verification",
                "required_verifications": ["check_x"],
            },
        )
        validator.validate_transition(decision)
        
        # Check requirement is set
        episode = validator.get_or_create_episode(episode_id)
        assert episode.requires_verification is True

    def test_verify_first_blocks_write_until_complete(self, validator, base_header, base_mcp, episode_id, valid_observation_payload, valid_belief_update_payload, valid_task_directive_payload):
        """VERIFY_FIRST blocks WRITE actions until verification completes."""
        # Setup: Path to VERIFY_FIRST
        obs = ObservationPacket(
            header=base_header("ObservationPacket"),
            mcp=base_mcp,
            payload=valid_observation_payload,
        )
        validator.validate_transition(obs)
        
        belief = BeliefUpdatePacket(
            header=base_header("BeliefUpdatePacket"),
            mcp=base_mcp,
            payload=valid_belief_update_payload,
        )
        validator.validate_transition(belief)
        
        decision = DecisionPacket(
            header=base_header("DecisionPacket"),
            mcp=base_mcp,
            payload={
                "decision_id": str(uuid4()),
                "decision_outcome": "VERIFY_FIRST",
                "decision_summary": "Verify",
                "rationale": "Need verification",
                "required_verifications": ["check_x"],
            },
        )
        validator.validate_transition(decision)
        
        # Try to execute WRITE action (should fail)
        payload = {**valid_task_directive_payload, "tools": [{
            "tool_id": "write_tool",
            "tool_safety": "WRITE",
            "parameters": {},
        }]}
        directive = TaskDirectivePacket(
            header=base_header("TaskDirectivePacket"),
            mcp=base_mcp,
            payload=payload,
        )
        result = validator.validate_transition(directive)
        assert result.valid is False
        assert any("VERIFY_FIRST" in e for e in result.errors)

    def test_verify_first_allows_read_execution(self, validator, base_header, base_mcp, episode_id, valid_observation_payload, valid_belief_update_payload, valid_task_directive_payload):
        """VERIFY_FIRST allows READ tool execution for verification."""
        # Setup: Path to VERIFY_FIRST
        obs = ObservationPacket(
            header=base_header("ObservationPacket"),
            mcp=base_mcp,
            payload=valid_observation_payload,
        )
        validator.validate_transition(obs)
        
        belief = BeliefUpdatePacket(
            header=base_header("BeliefUpdatePacket"),
            mcp=base_mcp,
            payload=valid_belief_update_payload,
        )
        validator.validate_transition(belief)
        
        decision = DecisionPacket(
            header=base_header("DecisionPacket"),
            mcp=base_mcp,
            payload={
                "decision_id": str(uuid4()),
                "decision_outcome": "VERIFY_FIRST",
                "decision_summary": "Verify",
                "rationale": "Need verification",
                "required_verifications": ["check_x"],
            },
        )
        validator.validate_transition(decision)
        
        # Execute READ action (should succeed)
        payload = {**valid_task_directive_payload, "tools": [{
            "tool_id": "read_tool",
            "tool_safety": "READ",
            "parameters": {},
        }]}
        directive = TaskDirectivePacket(
            header=base_header("TaskDirectivePacket"),
            mcp=base_mcp,
            payload=payload,
        )
        result = validator.validate_transition(directive)
        assert result.valid is True

    def test_verification_loop_completion_clears_requirement(self, validator, base_header, base_mcp, episode_id, valid_observation_payload, valid_belief_update_payload, valid_task_directive_payload, valid_task_result_payload):
        """Completing verification loop clears requirement."""
        # Setup: IDLE -> SENSE -> MODEL -> VERIFY_FIRST
        obs = ObservationPacket(
            header=base_header("ObservationPacket"),
            mcp=base_mcp,
            payload=valid_observation_payload,
        )
        validator.validate_transition(obs)
        
        belief = BeliefUpdatePacket(
            header=base_header("BeliefUpdatePacket"),
            mcp=base_mcp,
            payload=valid_belief_update_payload,
        )
        validator.validate_transition(belief)
        
        decision = DecisionPacket(
            header=base_header("DecisionPacket"),
            mcp=base_mcp,
            payload={
                "decision_id": str(uuid4()),
                "decision_outcome": "VERIFY_FIRST",
                "decision_summary": "Verify",
                "rationale": "Need verification",
                "required_verifications": ["check_x"],
            },
        )
        validator.validate_transition(decision)
        
        # Execute verification (READ)
        payload = {**valid_task_directive_payload, "tools": [{
            "tool_id": "read_tool",
            "tool_safety": "READ",
            "parameters": {},
        }]}
        directive = TaskDirectivePacket(
            header=base_header("TaskDirectivePacket"),
            mcp=base_mcp,
            payload=payload,
        )
        validator.validate_transition(directive)
        
        # Review results
        result_payload = {**valid_task_result_payload, "directive_id": directive.payload.directive_id}
        result_packet = TaskResultPacket(
            header=base_header("TaskResultPacket"),
            mcp=base_mcp,
            payload=result_payload,
        )
        validator.validate_transition(result_packet)
        
        # Update beliefs (clears requirement)
        belief2 = BeliefUpdatePacket(
            header=base_header("BeliefUpdatePacket"),
            mcp=base_mcp,
            payload=valid_belief_update_payload,
        )
        validator.validate_transition(belief2)
        
        # Check requirement is cleared
        episode = validator.get_or_create_episode(episode_id)
        assert episode.requires_verification is False


# =============================================================================
# AUTHORIZATION TESTS
# =============================================================================

class TestAuthorizationRequired:
    """Tests for WRITE tool authorization requirement."""

    def test_write_tools_require_authorization(self, validator, base_header, base_mcp, episode_id, valid_observation_payload, valid_belief_update_payload, valid_task_directive_payload):
        """WRITE tools require going through AUTHORIZE state."""
        # Setup: Valid path to DECIDE
        obs = ObservationPacket(
            header=base_header("ObservationPacket"),
            mcp=base_mcp,
            payload=valid_observation_payload,
        )
        validator.validate_transition(obs)
        
        belief = BeliefUpdatePacket(
            header=base_header("BeliefUpdatePacket"),
            mcp=base_mcp,
            payload=valid_belief_update_payload,
        )
        validator.validate_transition(belief)
        
        decision = DecisionPacket(
            header=base_header("DecisionPacket"),
            mcp=base_mcp,
            payload={
                "decision_id": str(uuid4()),
                "decision_outcome": "ACT",
                "decision_summary": "Act",
                "rationale": "Safe",
            },
        )
        validator.validate_transition(decision)
        
        # Try to execute WRITE tool without authorization
        payload = {**valid_task_directive_payload, "tools": [{
            "tool_id": "write_tool",
            "tool_safety": "WRITE",
            "parameters": {},
        }]}
        directive = TaskDirectivePacket(
            header=base_header("TaskDirectivePacket"),
            mcp=base_mcp,
            payload=payload,
        )
        result = validator.validate_transition(directive)
        assert result.valid is False
        assert any("AUTHORIZE" in e for e in result.errors)

    def test_read_tools_dont_require_authorization(self, validator, base_header, base_mcp, episode_id, valid_observation_payload, valid_belief_update_payload, valid_task_directive_payload):
        """READ tools don't require authorization."""
        # Setup: Valid path to DECIDE
        obs = ObservationPacket(
            header=base_header("ObservationPacket"),
            mcp=base_mcp,
            payload=valid_observation_payload,
        )
        validator.validate_transition(obs)
        
        belief = BeliefUpdatePacket(
            header=base_header("BeliefUpdatePacket"),
            mcp=base_mcp,
            payload=valid_belief_update_payload,
        )
        validator.validate_transition(belief)
        
        decision = DecisionPacket(
            header=base_header("DecisionPacket"),
            mcp=base_mcp,
            payload={
                "decision_id": str(uuid4()),
                "decision_outcome": "ACT",
                "decision_summary": "Act",
                "rationale": "Safe",
            },
        )
        validator.validate_transition(decision)
        
        # Execute READ tool (should succeed)
        payload = {**valid_task_directive_payload, "tools": [{
            "tool_id": "read_tool",
            "tool_safety": "READ",
            "parameters": {},
        }]}
        directive = TaskDirectivePacket(
            header=base_header("TaskDirectivePacket"),
            mcp=base_mcp,
            payload=payload,
        )
        result = validator.validate_transition(directive)
        assert result.valid is True


# =============================================================================
# SAFEMODE TESTS
# =============================================================================

class TestSafeMode:
    """Tests for safe mode transitions."""

    def test_safemode_from_any_state(self, validator, base_header, base_mcp, episode_id, valid_observation_payload):
        """SAFEMODE can be entered from any state."""
        # Go to SENSE
        obs = ObservationPacket(
            header=base_header("ObservationPacket"),
            mcp=base_mcp,
            payload=valid_observation_payload,
        )
        validator.validate_transition(obs)
        
        # Critical alert should trigger SAFEMODE
        alert = IntegrityAlertPacket(
            header=base_header("IntegrityAlertPacket"),
            mcp=base_mcp,
            payload={
                "alert_id": "alert_001",
                "alert_type": "critical",
                "severity": "CRITICAL",
                "summary": "Critical issue",
                "detected_at": datetime.now(timezone.utc).isoformat(),
                "detection_method": "monitor",
                "requires_immediate_attention": True,
            },
        )
        result = validator.validate_transition(alert)
        assert result.valid is True
        
        episode = validator.get_or_create_episode(episode_id)
        assert episode.current_state == FSMState.S9_SAFEMODE


# =============================================================================
# EPISODE STATE TESTS
# =============================================================================

class TestEpisodeState:
    """Tests for episode state tracking."""

    def test_creates_new_episode(self, validator, episode_id):
        """Creates new episode state on first packet."""
        episode = validator.get_or_create_episode(episode_id)
        assert episode.episode_id == episode_id
        assert episode.current_state == FSMState.S0_IDLE

    def test_tracks_state_history(self, validator, base_header, base_mcp, episode_id, valid_observation_payload):
        """Tracks state transition history."""
        obs = ObservationPacket(
            header=base_header("ObservationPacket"),
            mcp=base_mcp,
            payload=valid_observation_payload,
        )
        validator.validate_transition(obs)
        
        episode = validator.get_or_create_episode(episode_id)
        assert FSMState.S0_IDLE in episode.state_history
        assert episode.current_state == FSMState.S1_SENSE

    def test_reset_episode(self, validator, base_header, base_mcp, episode_id, valid_observation_payload):
        """Can reset episode state."""
        obs = ObservationPacket(
            header=base_header("ObservationPacket"),
            mcp=base_mcp,
            payload=valid_observation_payload,
        )
        validator.validate_transition(obs)
        
        validator.reset_episode(episode_id)
        episode = validator.get_or_create_episode(episode_id)
        assert episode.current_state == FSMState.S0_IDLE
        assert len(episode.state_history) == 0


# =============================================================================
# FACTORY FUNCTION TESTS
# =============================================================================

class TestFactoryFunction:
    """Tests for create_fsm_validator function."""

    def test_creates_validator(self):
        validator = create_fsm_validator()
        assert isinstance(validator, FSMValidator)
