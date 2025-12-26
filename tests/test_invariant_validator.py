"""
Tests for invariant validator.

Validates cross-policy rules per OMEN.md §8.4, §15.4.
"""

import pytest
from uuid import uuid4
from datetime import datetime, timezone, timedelta

from omen.validation import (
    InvariantValidator,
    BudgetLedger,
    create_invariant_validator,
    ValidationResult,
)
from omen.schemas import (
    DecisionPacket,
    TaskDirectivePacket,
    ToolAuthorizationToken,
    ObservationPacket,
)
from omen.vocabulary import (
    QualityTier,
    StakesLevel,
    EpistemicStatus,
    DecisionOutcome,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def validator() -> InvariantValidator:
    return InvariantValidator()


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
    def _make_mcp(
        quality_tier: str = "PAR",
        stakes_level: str = "LOW",
        status: str = "OBSERVED",
        confidence: float = 0.8,
        has_evidence: bool = True,
    ):
        evidence = {
            "evidence_refs": [
                {
                    "ref_type": "tool_output",
                    "ref_id": "test_001",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            ] if has_evidence else [],
            "evidence_absent_reason": None if has_evidence else "Test",
        }
        return {
            "intent": {"summary": "Test", "scope": "test"},
            "stakes": {
                "impact": stakes_level,
                "irreversibility": "REVERSIBLE",
                "uncertainty": "LOW",
                "adversariality": "BENIGN",
                "stakes_level": stakes_level,
            },
            "quality": {
                "quality_tier": quality_tier,
                "satisficing_mode": True,
                "definition_of_done": {"text": "Done", "checks": []},
                "verification_requirement": "OPTIONAL",
            },
            "budgets": {
                "token_budget": 100,
                "tool_call_budget": 5,
                "time_budget_seconds": 60,
                "risk_budget": {"envelope": "low", "max_loss": "minimal"},
            },
            "epistemics": {
                "status": status,
                "confidence": confidence,
                "calibration_note": "Test",
                "freshness_class": "OPERATIONAL",
                "stale_if_older_than_seconds": 300,
                "assumptions": [],
            },
            "evidence": evidence,
            "routing": {"task_class": "VERIFY", "tools_state": "tools_ok"},
        }
    return _make_mcp


# =============================================================================
# INVARIANT 2: SUBPAR NO ACTION
# =============================================================================

class TestSubparNoAction:
    """Tests for Invariant 2: SUBPAR never authorizes external action."""

    def test_subpar_task_directive_fails(self, validator, base_header, base_mcp):
        """SUBPAR TaskDirective is rejected."""
        packet = TaskDirectivePacket(
            header=base_header("TaskDirectivePacket"),
            mcp=base_mcp(quality_tier="SUBPAR"),
            payload={
                "directive_id": str(uuid4()),
                "task_class": "VERIFY",
                "task_description": "Do something",
                "instructions": "Do something",
                "tools": [],
                "constraints": {
                    "max_tool_calls": 5,
                    "max_time_seconds": 60,
                },
                "success_criteria": "Done",
            },
        )
        result = validator.validate(packet)
        assert result.valid is False
        assert any("SUBPAR" in e for e in result.errors)

    def test_par_task_directive_passes(self, validator, base_header, base_mcp):
        """PAR TaskDirective is allowed."""
        packet = TaskDirectivePacket(
            header=base_header("TaskDirectivePacket"),
            mcp=base_mcp(quality_tier="PAR"),
            payload={
                "directive_id": str(uuid4()),
                "task_class": "VERIFY",
                "task_description": "Do something",
                "instructions": "Do something",
                "tools": [],
                "constraints": {
                    "max_tool_calls": 5,
                    "max_time_seconds": 60,
                },
                "success_criteria": "Done",
            },
        )
        result = validator.validate(packet)
        assert result.valid is True

    def test_subpar_decision_act_fails(self, validator, base_header, base_mcp):
        """SUBPAR Decision with ACT is rejected."""
        packet = DecisionPacket(
            header=base_header("DecisionPacket"),
            mcp=base_mcp(quality_tier="SUBPAR"),
            payload={
                "decision_id": str(uuid4()),
                "decision_outcome": "ACT",
                "decision_summary": "Proceed",
                "rationale": "Test",
            },
        )
        result = validator.validate(packet)
        assert result.valid is False
        assert any("SUBPAR" in e and "ACT" in e for e in result.errors)

    def test_subpar_decision_verify_first_passes(self, validator, base_header, base_mcp):
        """SUBPAR Decision with VERIFY_FIRST is allowed (not action)."""
        packet = DecisionPacket(
            header=base_header("DecisionPacket"),
            mcp=base_mcp(quality_tier="SUBPAR"),
            payload={
                "decision_id": str(uuid4()),
                "decision_outcome": "VERIFY_FIRST",
                "decision_summary": "Verify",
                "rationale": "Need verification",
                "required_verifications": ["check_x"],
            },
        )
        result = validator.validate(packet)
        assert result.valid is True


# =============================================================================
# INVARIANT 3: HIGH/CRITICAL VERIFICATION
# =============================================================================

class TestHighStakesVerification:
    """Tests for Invariant 3: HIGH/CRITICAL require verification."""

    def test_high_stakes_act_requires_superb(self, validator, base_header, base_mcp):
        """HIGH stakes ACT requires SUPERB tier."""
        packet = DecisionPacket(
            header=base_header("DecisionPacket"),
            mcp=base_mcp(quality_tier="PAR", stakes_level="HIGH"),
            payload={
                "decision_id": str(uuid4()),
                "decision_outcome": "ACT",
                "decision_summary": "Proceed",
                "rationale": "Test",
            },
        )
        result = validator.validate(packet)
        assert result.valid is False
        assert any("SUPERB" in e for e in result.errors)

    def test_high_stakes_act_with_superb_passes(self, validator, base_header, base_mcp):
        """HIGH stakes ACT with SUPERB and evidence passes."""
        packet = DecisionPacket(
            header=base_header("DecisionPacket"),
            mcp=base_mcp(quality_tier="SUPERB", stakes_level="HIGH", has_evidence=True),
            payload={
                "decision_id": str(uuid4()),
                "decision_outcome": "ACT",
                "decision_summary": "Proceed",
                "rationale": "Verified safe",
            },
        )
        result = validator.validate(packet)
        assert result.valid is True

    def test_critical_stakes_act_requires_superb(self, validator, base_header, base_mcp):
        """CRITICAL stakes ACT requires SUPERB tier."""
        packet = DecisionPacket(
            header=base_header("DecisionPacket"),
            mcp=base_mcp(quality_tier="PAR", stakes_level="CRITICAL"),
            payload={
                "decision_id": str(uuid4()),
                "decision_outcome": "ACT",
                "decision_summary": "Proceed",
                "rationale": "Test",
            },
        )
        result = validator.validate(packet)
        assert result.valid is False

    def test_high_stakes_escalate_allowed(self, validator, base_header, base_mcp):
        """HIGH stakes can ESCALATE instead of acting."""
        packet = DecisionPacket(
            header=base_header("DecisionPacket"),
            mcp=base_mcp(quality_tier="PAR", stakes_level="HIGH"),
            payload={
                "decision_id": str(uuid4()),
                "decision_outcome": "ESCALATE",
                "decision_summary": "Escalate",
                "rationale": "High stakes",
                "escalation_reason": "Need human input",
            },
        )
        result = validator.validate(packet)
        assert result.valid is True

    def test_high_stakes_act_without_evidence_warns(self, validator, base_header, base_mcp):
        """HIGH stakes ACT without evidence produces warning."""
        packet = DecisionPacket(
            header=base_header("DecisionPacket"),
            mcp=base_mcp(quality_tier="SUPERB", stakes_level="HIGH", has_evidence=False),
            payload={
                "decision_id": str(uuid4()),
                "decision_outcome": "ACT",
                "decision_summary": "Proceed",
                "rationale": "Test",
            },
        )
        result = validator.validate(packet)
        assert any("evidence" in w.lower() for w in result.warnings)


# =============================================================================
# INVARIANT 4: LIVE TRUTH GROUNDING
# =============================================================================

class TestLiveTruthGrounding:
    """Tests for Invariant 4: No live truth without tool evidence."""

    def test_observed_without_evidence_fails(self, validator, base_header, base_mcp):
        """OBSERVED status without evidence is rejected."""
        packet = ObservationPacket(
            header=base_header("ObservationPacket"),
            mcp=base_mcp(status="OBSERVED", has_evidence=False),
            payload={
                "observation_id": str(uuid4()),
                "source": {"source_type": "test", "source_id": "test"},
                "observation_type": "test_observation",
                "content": {"data": "test"},
                "observed_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        result = validator.validate(packet)
        assert result.valid is False
        assert any("OBSERVED" in e and "evidence" in e for e in result.errors)

    def test_observed_with_evidence_passes(self, validator, base_header, base_mcp):
        """OBSERVED status with evidence passes."""
        packet = ObservationPacket(
            header=base_header("ObservationPacket"),
            mcp=base_mcp(status="OBSERVED", has_evidence=True),
            payload={
                "observation_id": str(uuid4()),
                "source": {"source_type": "test", "source_id": "test"},
                "observation_type": "test_observation",
                "content": {"data": "test"},
                "observed_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        result = validator.validate(packet)
        assert result.valid is True

    def test_inferred_high_confidence_warns(self, validator, base_header, base_mcp):
        """INFERRED with high confidence produces warning."""
        packet = ObservationPacket(
            header=base_header("ObservationPacket"),
            mcp=base_mcp(status="INFERRED", confidence=0.9, has_evidence=True),
            payload={
                "observation_id": str(uuid4()),
                "source": {"source_type": "test", "source_id": "test"},
                "observation_type": "test_observation",
                "content": {"data": "test"},
                "observed_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        result = validator.validate(packet)
        assert any("overconfident" in w.lower() for w in result.warnings)

    def test_hypothesized_high_confidence_warns(self, validator, base_header, base_mcp):
        """HYPOTHESIZED with high confidence produces warning."""
        packet = ObservationPacket(
            header=base_header("ObservationPacket"),
            mcp=base_mcp(status="HYPOTHESIZED", confidence=0.85, has_evidence=True),
            payload={
                "observation_id": str(uuid4()),
                "source": {"source_type": "test", "source_id": "test"},
                "observation_type": "test_observation",
                "content": {"data": "test"},
                "observed_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        result = validator.validate(packet)
        assert any("overconfident" in w.lower() for w in result.warnings)


# =============================================================================
# INVARIANT 5: BUDGET OVERRUNS
# =============================================================================

class TestBudgetOverruns:
    """Tests for Invariant 5: Budget overruns require approval."""

    def test_no_overrun_passes(self, validator, base_header, base_mcp, episode_id):
        """No budget overrun passes."""
        packet = TaskDirectivePacket(
            header=base_header("TaskDirectivePacket"),
            mcp=base_mcp(),
            payload={
                "directive_id": str(uuid4()),
                "task_class": "VERIFY",
                "task_description": "Do something",
                "instructions": "Do something",
                "tools": [],
                "constraints": {
                    "max_tool_calls": 5,
                    "max_time_seconds": 60,
                },
                "success_criteria": "Done",
            },
        )
        result = validator.validate(packet)
        assert result.valid is True

    def test_overrun_at_high_stakes_fails(self, validator, base_header, base_mcp, episode_id):
        """Budget overrun at HIGH stakes without approval fails."""
        # First packet establishes budget
        packet1 = TaskDirectivePacket(
            header=base_header("TaskDirectivePacket"),
            mcp=base_mcp(stakes_level="HIGH"),
            payload={
                "directive_id": str(uuid4()),
                "task_class": "VERIFY",
                "task_description": "Do something",
                "instructions": "Do something",
                "tools": [],
                "constraints": {
                    "max_tool_calls": 5,
                    "max_time_seconds": 60,
                },
                "success_criteria": "Done",
            },
        )
        validator.validate(packet1)
        
        # Simulate overrun
        validator.update_budget_consumption(episode_id, tokens=150)
        
        # Second packet should fail
        packet2 = TaskDirectivePacket(
            header=base_header("TaskDirectivePacket"),
            mcp=base_mcp(stakes_level="HIGH"),
            payload={
                "directive_id": str(uuid4()),
                "task_class": "VERIFY",
                "task_description": "Continue",
                "instructions": "Continue",
                "tools": [],
                "constraints": {
                    "max_tool_calls": 5,
                    "max_time_seconds": 60,
                },
                "success_criteria": "Done",
            },
        )
        result = validator.validate(packet2)
        assert result.valid is False
        assert any("overrun" in e.lower() for e in result.errors)

    def test_overrun_with_approval_passes(self, validator, base_header, base_mcp, episode_id):
        """Budget overrun with approval passes."""
        # First packet establishes budget
        packet1 = TaskDirectivePacket(
            header=base_header("TaskDirectivePacket"),
            mcp=base_mcp(stakes_level="HIGH"),
            payload={
                "directive_id": str(uuid4()),
                "task_class": "VERIFY",
                "task_description": "Do something",
                "instructions": "Do something",
                "tools": [],
                "constraints": {
                    "max_tool_calls": 5,
                    "max_time_seconds": 60,
                },
                "success_criteria": "Done",
            },
        )
        validator.validate(packet1)
        
        # Simulate overrun
        validator.update_budget_consumption(episode_id, tokens=150)
        
        # Approve overrun
        validator.approve_budget_overrun(episode_id, "1")  # Layer 1
        
        # Second packet should pass
        packet2 = TaskDirectivePacket(
            header=base_header("TaskDirectivePacket"),
            mcp=base_mcp(stakes_level="HIGH"),
            payload={
                "directive_id": str(uuid4()),
                "task_class": "VERIFY",
                "task_description": "Continue",
                "instructions": "Continue",
                "tools": [],
                "constraints": {
                    "max_tool_calls": 5,
                    "max_time_seconds": 60,
                },
                "success_criteria": "Done",
            },
        )
        result = validator.validate(packet2)
        assert result.valid is True

    def test_overrun_at_low_stakes_warns(self, validator, base_header, base_mcp, episode_id):
        """Budget overrun at LOW stakes produces warning, not error."""
        packet1 = TaskDirectivePacket(
            header=base_header("TaskDirectivePacket"),
            mcp=base_mcp(stakes_level="LOW"),
            payload={
                "directive_id": str(uuid4()),
                "task_class": "VERIFY",
                "task_description": "Do something",
                "instructions": "Do something",
                "tools": [],
                "constraints": {
                    "max_tool_calls": 5,
                    "max_time_seconds": 60,
                },
                "success_criteria": "Done",
            },
        )
        validator.validate(packet1)
        
        validator.update_budget_consumption(episode_id, tokens=150)
        
        packet2 = TaskDirectivePacket(
            header=base_header("TaskDirectivePacket"),
            mcp=base_mcp(stakes_level="LOW"),
            payload={
                "directive_id": str(uuid4()),
                "task_class": "VERIFY",
                "task_description": "Continue",
                "instructions": "Continue",
                "tools": [],
                "constraints": {
                    "max_tool_calls": 5,
                    "max_time_seconds": 60,
                },
                "success_criteria": "Done",
            },
        )
        result = validator.validate(packet2)
        assert result.valid is True  # Still valid at low stakes
        assert any("overrun" in w.lower() for w in result.warnings)


# =============================================================================
# BUDGET LEDGER TESTS
# =============================================================================

class TestBudgetLedger:
    """Tests for BudgetLedger class."""

    def test_creates_ledger(self, validator, episode_id):
        ledger = validator.get_or_create_ledger(episode_id)
        assert ledger.episode_id == episode_id
        assert ledger.tokens_consumed == 0

    def test_tracks_consumption(self, validator, episode_id):
        validator.update_budget_consumption(
            episode_id, tokens=50, tool_calls=2, time_seconds=30
        )
        ledger = validator.get_or_create_ledger(episode_id)
        assert ledger.tokens_consumed == 50
        assert ledger.tool_calls_consumed == 2
        assert ledger.time_elapsed_seconds == 30

    def test_detects_overrun(self, episode_id):
        ledger = BudgetLedger(
            episode_id=episode_id,
            token_budget=100,
            tokens_consumed=150,
        )
        is_overrun, details = ledger.is_overrun()
        assert is_overrun is True
        assert "tokens" in details[0]

    def test_reset_episode(self, validator, episode_id):
        validator.update_budget_consumption(episode_id, tokens=50)
        validator.reset_episode(episode_id)
        ledger = validator.get_or_create_ledger(episode_id)
        assert ledger.tokens_consumed == 0


# =============================================================================
# FACTORY FUNCTION TESTS
# =============================================================================

class TestFactoryFunction:
    """Tests for create_invariant_validator function."""

    def test_creates_validator(self):
        validator = create_invariant_validator()
        assert isinstance(validator, InvariantValidator)
