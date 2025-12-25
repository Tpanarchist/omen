"""
Tests for schema validator.

Validates structural correctness checking per OMEN.md §15.4.
"""

import pytest
from uuid import uuid4
from datetime import datetime, timezone, timedelta

from omen.validation import SchemaValidator, ValidationResult, validate_schema
from omen.schemas import (
    DecisionPacket,
    TaskResultPacket,
    ToolAuthorizationToken,
    EscalationPacket,
    ObservationPacket,
)
from omen.vocabulary import DecisionOutcome, TaskResultStatus, QualityTier


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def validator() -> SchemaValidator:
    return SchemaValidator()


@pytest.fixture
def valid_header() -> dict:
    return {
        "packet_id": str(uuid4()),
        "packet_type": "DecisionPacket",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "layer_source": "5",
        "correlation_id": str(uuid4()),
    }


@pytest.fixture
def valid_mcp() -> dict:
    return {
        "intent": {"summary": "Test intent", "scope": "test"},
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
            "definition_of_done": {"text": "Test complete", "checks": []},
            "verification_requirement": "OPTIONAL",
        },
        "budgets": {
            "token_budget": 100,
            "tool_call_budget": 5,
            "time_budget_seconds": 60,
            "risk_budget": {"envelope": "low", "max_loss": "minimal"},
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
            "evidence_refs": [
                {
                    "ref_type": "tool_output",
                    "ref_id": "test_001",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            ],
            "evidence_absent_reason": None,
        },
        "routing": {"task_class": "VERIFY", "tools_state": "tools_ok"},
    }


@pytest.fixture
def valid_decision_payload() -> dict:
    return {
        "decision_id": str(uuid4()),
        "decision_outcome": "ACT",
        "decision_summary": "Proceed with action",
        "rationale": "Test rationale",
        "assumptions": ["Test assumption"],
        "load_bearing_assumptions": ["Test assumption"],
        "failure_modes": [],
        "rejected_alternatives": [],
    }


# =============================================================================
# VALIDATION RESULT TESTS
# =============================================================================

class TestValidationResult:
    """Tests for ValidationResult class."""

    def test_success(self):
        result = ValidationResult.success()
        assert result.valid is True
        assert result.errors == []
        assert result.warnings == []

    def test_failure(self):
        result = ValidationResult.failure(["error1", "error2"])
        assert result.valid is False
        assert len(result.errors) == 2

    def test_failure_with_warnings(self):
        result = ValidationResult.failure(["error"], ["warning"])
        assert result.valid is False
        assert len(result.warnings) == 1

    def test_merge_success(self):
        r1 = ValidationResult.success()
        r2 = ValidationResult.success()
        merged = r1.merge(r2)
        assert merged.valid is True

    def test_merge_failure_propagates(self):
        r1 = ValidationResult.success()
        r2 = ValidationResult.failure(["error"])
        merged = r1.merge(r2)
        assert merged.valid is False
        assert "error" in merged.errors

    def test_merge_combines_errors(self):
        r1 = ValidationResult.failure(["error1"])
        r2 = ValidationResult.failure(["error2"])
        merged = r1.merge(r2)
        assert len(merged.errors) == 2


# =============================================================================
# HEADER VALIDATION TESTS
# =============================================================================

class TestHeaderValidation:
    """Tests for header validation."""

    def test_valid_header(self, validator, valid_header, valid_mcp, valid_decision_payload):
        packet = DecisionPacket(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_decision_payload,
        )
        result = validator.validate(packet)
        assert result.valid is True

    def test_missing_packet_id(self, validator, valid_header, valid_mcp, valid_decision_payload):
        """Test that empty packet_id is caught by Pydantic."""
        valid_header["packet_id"] = ""
        # Pydantic should catch invalid UUID format
        with pytest.raises(Exception):
            packet = DecisionPacket(
                header=valid_header,
                mcp=valid_mcp,
                payload=valid_decision_payload,
            )

    def test_missing_correlation_id(self, validator, valid_header, valid_mcp, valid_decision_payload):
        """Test that missing correlation_id is caught by Pydantic."""
        valid_header["correlation_id"] = None
        # Pydantic should catch None for required UUID field
        with pytest.raises(Exception):
            packet = DecisionPacket(
                header=valid_header,
                mcp=valid_mcp,
                payload=valid_decision_payload,
            )


# =============================================================================
# MCP VALIDATION TESTS
# =============================================================================

class TestMCPValidation:
    """Tests for MCP envelope validation."""

    def test_valid_mcp(self, validator, valid_header, valid_mcp, valid_decision_payload):
        packet = DecisionPacket(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_decision_payload,
        )
        result = validator.validate(packet)
        assert result.valid is True

    def test_empty_intent_summary(self, validator, valid_header, valid_mcp, valid_decision_payload):
        valid_mcp["intent"]["summary"] = ""
        packet = DecisionPacket(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_decision_payload,
        )
        result = validator.validate(packet)
        assert result.valid is False
        assert any("intent.summary" in e for e in result.errors)

    def test_evidence_requires_refs_or_reason(self, validator, valid_header, valid_mcp, valid_decision_payload):
        valid_mcp["evidence"] = {"evidence_refs": [], "evidence_absent_reason": None}
        # This should fail at Pydantic level, but validator would catch it too
        with pytest.raises(Exception):  # Pydantic validation
            packet = DecisionPacket(
                header=valid_header,
                mcp=valid_mcp,
                payload=valid_decision_payload,
            )

    def test_zero_budgets_warning(self, validator, valid_header, valid_mcp, valid_decision_payload):
        valid_mcp["budgets"]["token_budget"] = 0
        valid_mcp["budgets"]["tool_call_budget"] = 0
        packet = DecisionPacket(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_decision_payload,
        )
        result = validator.validate(packet)
        assert any("budget" in w.lower() for w in result.warnings)

    def test_confidence_one_warning(self, validator, valid_header, valid_mcp, valid_decision_payload):
        """Test that confidence of 1.0 triggers epistemic warning."""
        valid_mcp["epistemics"]["confidence"] = 1.0
        packet = DecisionPacket(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_decision_payload,
        )
        result = validator.validate(packet)
        assert result.valid is True  # Warning, not error
        assert any("1.0" in w and "rarely justified" in w for w in result.warnings)

    def test_confidence_zero_no_warning(self, validator, valid_header, valid_mcp, valid_decision_payload):
        """Test that confidence of 0.0 does NOT trigger warning (valid for UNKNOWN)."""
        valid_mcp["epistemics"]["confidence"] = 0.0
        valid_mcp["epistemics"]["status"] = "UNKNOWN"
        packet = DecisionPacket(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_decision_payload,
        )
        result = validator.validate(packet)
        # Should not have confidence warning
        assert not any("confidence" in w.lower() and "0.0" in w for w in result.warnings)


# =============================================================================
# DECISION PAYLOAD VALIDATION TESTS
# =============================================================================

class TestDecisionPayloadValidation:
    """Tests for DecisionPacket payload validation."""

    def test_verify_first_requires_verifications(self, validator, valid_header, valid_mcp, valid_decision_payload):
        """Test that VERIFY_FIRST without verifications is caught by Pydantic."""
        valid_decision_payload["decision_outcome"] = "VERIFY_FIRST"
        valid_decision_payload["required_verifications"] = []
        # Pydantic already validates this rule
        with pytest.raises(Exception):
            packet = DecisionPacket(
                header=valid_header,
                mcp=valid_mcp,
                payload=valid_decision_payload,
            )

    def test_verify_first_with_verifications(self, validator, valid_header, valid_mcp, valid_decision_payload):
        valid_decision_payload["decision_outcome"] = "VERIFY_FIRST"
        valid_decision_payload["required_verifications"] = ["verify_target"]
        packet = DecisionPacket(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_decision_payload,
        )
        result = validator.validate(packet)
        assert result.valid is True

    def test_escalate_requires_reason(self, validator, valid_header, valid_mcp, valid_decision_payload):
        """Test that ESCALATE without reason is caught by Pydantic."""
        valid_decision_payload["decision_outcome"] = "ESCALATE"
        valid_decision_payload["escalation_reason"] = None
        # Pydantic already validates this rule
        with pytest.raises(Exception):
            packet = DecisionPacket(
                header=valid_header,
                mcp=valid_mcp,
                payload=valid_decision_payload,
            )

    def test_escalate_with_reason(self, validator, valid_header, valid_mcp, valid_decision_payload):
        valid_decision_payload["decision_outcome"] = "ESCALATE"
        valid_decision_payload["escalation_reason"] = "High stakes, need human input"
        packet = DecisionPacket(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_decision_payload,
        )
        result = validator.validate(packet)
        assert result.valid is True

    def test_load_bearing_assumptions_warning(self, validator, valid_header, valid_mcp, valid_decision_payload):
        """Test that load_bearing_assumptions with empty assumptions triggers warning."""
        valid_decision_payload["load_bearing_assumptions"] = ["critical assumption"]
        valid_decision_payload["assumptions"] = []
        packet = DecisionPacket(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_decision_payload,
        )
        result = validator.validate(packet)
        assert result.valid is True  # Warning, not error
        assert any("load_bearing_assumptions" in w and "empty" in w for w in result.warnings)


# =============================================================================
# TASK RESULT VALIDATION TESTS
# =============================================================================

class TestTaskResultValidation:
    """Tests for TaskResultPacket payload validation."""

    @pytest.fixture
    def valid_task_result_payload(self) -> dict:
        return {
            "result_id": str(uuid4()),
            "directive_id": str(uuid4()),
            "status": "SUCCESS",
            "status_reason": "Task completed successfully",
            "output": {"data": "result"},
            "resource_usage": {
                "tool_calls_made": 1,
                "time_elapsed_seconds": 5,
            },
            "execution_started_at": datetime.now(timezone.utc).isoformat(),
            "execution_completed_at": datetime.now(timezone.utc).isoformat(),
        }

    def test_failure_requires_error_info(self, validator, valid_header, valid_mcp, valid_task_result_payload):
        """Test that FAILURE without error info is caught by Pydantic."""
        valid_header["packet_type"] = "TaskResultPacket"
        valid_task_result_payload["status"] = "FAILURE"
        valid_task_result_payload["status_reason"] = "Task failed"
        valid_task_result_payload["error_code"] = None
        valid_task_result_payload["error_details"] = None
        # Pydantic already validates this rule
        with pytest.raises(Exception):
            packet = TaskResultPacket(
                header=valid_header,
                mcp=valid_mcp,
                payload=valid_task_result_payload,
            )

    def test_failure_with_error_code(self, validator, valid_header, valid_mcp, valid_task_result_payload):
        """Test that FAILURE with error_code passes validation."""
        valid_header["packet_type"] = "TaskResultPacket"
        valid_task_result_payload["status"] = "FAILURE"
        valid_task_result_payload["status_reason"] = "Task failed due to timeout"
        valid_task_result_payload["error_code"] = "TIMEOUT"
        packet = TaskResultPacket(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_task_result_payload,
        )
        result = validator.validate(packet)
        assert result.valid is True

    def test_success_without_output_warning(self, validator, valid_header, valid_mcp, valid_task_result_payload):
        """Test that SUCCESS without output triggers warning."""
        valid_header["packet_type"] = "TaskResultPacket"
        valid_task_result_payload["output"] = None
        packet = TaskResultPacket(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_task_result_payload,
        )
        result = validator.validate(packet)
        # Still valid, but should warn
        assert result.valid is True
        assert any("output" in w.lower() for w in result.warnings)


# =============================================================================
# TOKEN VALIDATION TESTS
# =============================================================================

class TestTokenValidation:
    """Tests for ToolAuthorizationToken payload validation."""

    @pytest.fixture
    def valid_token_payload(self) -> dict:
        return {
            "token_id": "tok_001",
            "issued_for_episode": str(uuid4()),
            "issued_by_layer": "5",
            "authorization_reason": "Test authorization",
            "stakes_level": "MEDIUM",
            "scope": {
                "allowed_tool_ids": ["tool_1"],
                "allowed_tool_safeties": ["WRITE"],
            },
            "limits": {
                "max_uses": 3,
                "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            },
        }

    def test_revoked_requires_timestamp_and_reason(self, validator, valid_header, valid_mcp, valid_token_payload):
        """Test that revoked token without reason is caught by Pydantic."""
        valid_header["packet_type"] = "ToolAuthorizationToken"
        valid_token_payload["revoked"] = True
        valid_token_payload["revoked_at"] = datetime.now(timezone.utc).isoformat()
        valid_token_payload["revoked_reason"] = None
        # Pydantic already validates this rule
        with pytest.raises(Exception):
            packet = ToolAuthorizationToken(
                header=valid_header,
                mcp=valid_mcp,
                payload=valid_token_payload,
            )

    def test_empty_scope_error(self, validator, valid_header, valid_mcp, valid_token_payload):
        """Test that empty scope is caught by Pydantic."""
        valid_header["packet_type"] = "ToolAuthorizationToken"
        valid_token_payload["scope"]["allowed_tool_ids"] = []
        # Pydantic min_length validation catches this
        with pytest.raises(Exception):
            packet = ToolAuthorizationToken(
                header=valid_header,
                mcp=valid_mcp,
                payload=valid_token_payload,
            )


# =============================================================================
# ESCALATION VALIDATION TESTS
# =============================================================================

class TestEscalationValidation:
    """Tests for EscalationPacket payload validation."""

    @pytest.fixture
    def valid_escalation_payload(self) -> dict:
        return {
            "escalation_id": "esc_001",
            "escalation_trigger": "test_trigger",
            "situation_summary": "Test situation",
            "stakes_level": "HIGH",
            "uncertainty_level": "HIGH",
            "options": [
                {
                    "option_id": "opt_1",
                    "summary": "Do nothing",
                    "action_description": "Take no action",
                }
            ],
        }

    def test_must_have_options(self, validator, valid_header, valid_mcp, valid_escalation_payload):
        valid_header["packet_type"] = "EscalationPacket"
        valid_escalation_payload["options"] = []
        # Pydantic min_length=1 should catch this
        with pytest.raises(Exception):
            packet = EscalationPacket(
                header=valid_header,
                mcp=valid_mcp,
                payload=valid_escalation_payload,
            )

    def test_no_knowledge_warning(self, validator, valid_header, valid_mcp, valid_escalation_payload):
        valid_header["packet_type"] = "EscalationPacket"
        valid_escalation_payload["what_we_know"] = []
        valid_escalation_payload["what_we_believe"] = []
        packet = EscalationPacket(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_escalation_payload,
        )
        result = validator.validate(packet)
        assert any("what_we_know" in w or "what_we_believe" in w for w in result.warnings)


# =============================================================================
# CONVENIENCE FUNCTION TESTS
# =============================================================================

class TestConvenienceFunction:
    """Tests for validate_schema function."""

    def test_validate_schema_function(self, valid_header, valid_mcp, valid_decision_payload):
        packet = DecisionPacket(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_decision_payload,
        )
        result = validate_schema(packet)
        assert result.valid is True
