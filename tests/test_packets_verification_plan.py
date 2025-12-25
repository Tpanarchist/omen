"""
Tests for VerificationPlanPacket schema.

Validates structure matches OMEN.md §9.3, §15.3.
"""

import json
from uuid import uuid4

import pytest
from pydantic import ValidationError

from omen.schemas import VerificationPlanPacket, VerificationPlanPayload
from omen.schemas.packets.verification_plan import VerificationTarget
from omen.vocabulary import PacketType, LayerSource, ToolSafety


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def valid_verification_target() -> dict:
    return {
        "target_id": "verify_threat",
        "description": "Check current threat level",
        "assumption_text": "Threat level is acceptable",
        "is_load_bearing": True,
        "verification_method": "tool_query",
        "tool_id": "intel_api",
        "tool_safety": "READ",
        "expected_evidence_type": "threat_assessment",
        "success_criteria": "Threat level <= MEDIUM",
        "failure_action": "escalate"
    }


@pytest.fixture
def valid_verification_plan_payload(valid_verification_target) -> dict:
    return {
        "plan_id": "vplan_001",
        "triggering_decision_id": str(uuid4()),
        "plan_summary": "Verify threat level before proceeding",
        "targets": [valid_verification_target],
        "execution_order": ["verify_threat"],
        "parallel_allowed": False,
        "max_verification_time_seconds": 60,
        "max_tool_calls": 1,
        "on_all_success": "proceed_to_act",
        "on_any_failure": "escalate",
        "partial_success_acceptable": False
    }


@pytest.fixture
def valid_header() -> dict:
    return {
        "packet_type": "VerificationPlanPacket",
        "created_at": "2025-12-21T11:32:30Z",
        "layer_source": "5",
        "correlation_id": str(uuid4())
    }


@pytest.fixture
def valid_mcp() -> dict:
    return {
        "intent": {"summary": "Plan verification", "scope": "verification"},
        "stakes": {
            "impact": "MEDIUM",
            "irreversibility": "REVERSIBLE",
            "uncertainty": "HIGH",
            "adversariality": "CONTESTED",
            "stakes_level": "MEDIUM"
        },
        "quality": {
            "quality_tier": "PAR",
            "satisficing_mode": True,
            "definition_of_done": {"text": "Plan created", "checks": []},
            "verification_requirement": "VERIFY_ONE"
        },
        "budgets": {
            "token_budget": 200,
            "tool_call_budget": 1,
            "time_budget_seconds": 30,
            "risk_budget": {"envelope": "minimal", "max_loss": 0}
        },
        "epistemics": {
            "status": "DERIVED",
            "confidence": 0.9,
            "calibration_note": "Plan derived from decision",
            "freshness_class": "REALTIME",
            "stale_if_older_than_seconds": 300,
            "assumptions": []
        },
        "evidence": {
            "evidence_refs": [],
            "evidence_absent_reason": "Plan precedes verification"
        },
        "routing": {"task_class": "VERIFY", "tools_state": "tools_ok"}
    }


# =============================================================================
# VERIFICATION TARGET TESTS
# =============================================================================

class TestVerificationTarget:
    """Tests for VerificationTarget structure."""

    def test_valid_target(self, valid_verification_target):
        target = VerificationTarget(**valid_verification_target)
        assert target.target_id == "verify_threat"
        assert target.is_load_bearing is True
        assert target.tool_safety == ToolSafety.READ

    def test_target_minimal(self):
        target = VerificationTarget(
            target_id="test",
            description="Test verification",
            assumption_text="Something is true",
            verification_method="user_confirm",
            success_criteria="User confirms"
        )
        assert target.tool_id is None
        assert target.tool_safety is None
        assert target.failure_action == "escalate"

    def test_target_requires_core_fields(self):
        with pytest.raises(ValidationError):
            VerificationTarget(target_id="test")

    def test_target_all_tool_safeties(self, valid_verification_target):
        for safety in ToolSafety:
            valid_verification_target["tool_safety"] = safety.value
            target = VerificationTarget(**valid_verification_target)
            assert target.tool_safety == safety


# =============================================================================
# VERIFICATION PLAN PAYLOAD TESTS
# =============================================================================

class TestVerificationPlanPayload:
    """Tests for VerificationPlanPayload structure."""

    def test_valid_payload(self, valid_verification_plan_payload):
        payload = VerificationPlanPayload(**valid_verification_plan_payload)
        assert payload.plan_id == "vplan_001"
        assert len(payload.targets) == 1

    def test_payload_requires_at_least_one_target(self):
        with pytest.raises(ValidationError):
            VerificationPlanPayload(
                plan_id="test",
                triggering_decision_id=str(uuid4()),
                plan_summary="Test",
                targets=[],  # Empty!
                max_verification_time_seconds=60,
                max_tool_calls=1
            )

    def test_payload_multiple_targets(self, valid_verification_target):
        target2 = valid_verification_target.copy()
        target2["target_id"] = "verify_resources"
        target2["description"] = "Check resource availability"
        
        payload = VerificationPlanPayload(
            plan_id="multi",
            triggering_decision_id=str(uuid4()),
            plan_summary="Multi-target verification",
            targets=[valid_verification_target, target2],
            execution_order=["verify_threat", "verify_resources"],
            max_verification_time_seconds=120,
            max_tool_calls=2
        )
        assert len(payload.targets) == 2

    def test_payload_parallel_allowed(self, valid_verification_plan_payload):
        valid_verification_plan_payload["parallel_allowed"] = True
        payload = VerificationPlanPayload(**valid_verification_plan_payload)
        assert payload.parallel_allowed is True

    def test_payload_time_budget_positive(self, valid_verification_plan_payload):
        valid_verification_plan_payload["max_verification_time_seconds"] = 0
        with pytest.raises(ValidationError):
            VerificationPlanPayload(**valid_verification_plan_payload)

    def test_payload_tool_budget_positive(self, valid_verification_plan_payload):
        valid_verification_plan_payload["max_tool_calls"] = 0
        with pytest.raises(ValidationError):
            VerificationPlanPayload(**valid_verification_plan_payload)


# =============================================================================
# COMPLETE PACKET TESTS
# =============================================================================

class TestVerificationPlanPacket:
    """Tests for complete VerificationPlanPacket."""

    def test_valid_packet(self, valid_header, valid_mcp, valid_verification_plan_payload):
        packet = VerificationPlanPacket(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_verification_plan_payload
        )
        assert packet.header.packet_type == PacketType.VERIFICATION_PLAN
        assert packet.payload.plan_id == "vplan_001"

    def test_packet_enforces_packet_type(self, valid_header, valid_mcp, valid_verification_plan_payload):
        valid_header["packet_type"] = "DecisionPacket"
        packet = VerificationPlanPacket(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_verification_plan_payload
        )
        assert packet.header.packet_type == PacketType.VERIFICATION_PLAN

    def test_packet_from_layer_5(self, valid_header, valid_mcp, valid_verification_plan_payload):
        """Verification plans come from Layer 5."""
        packet = VerificationPlanPacket(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_verification_plan_payload
        )
        assert packet.header.layer_source == LayerSource.LAYER_5

    def test_packet_serialization(self, valid_header, valid_mcp, valid_verification_plan_payload):
        packet = VerificationPlanPacket(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_verification_plan_payload
        )
        json_str = packet.model_dump_json()
        parsed = json.loads(json_str)
        assert "targets" in parsed["payload"]
        assert len(parsed["payload"]["targets"]) == 1

    def test_packet_roundtrip(self, valid_header, valid_mcp, valid_verification_plan_payload):
        packet1 = VerificationPlanPacket(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_verification_plan_payload
        )
        json_str = packet1.model_dump_json()
        packet2 = VerificationPlanPacket.model_validate_json(json_str)
        assert packet1.payload.plan_id == packet2.payload.plan_id
        assert len(packet1.payload.targets) == len(packet2.payload.targets)

    def test_packet_tracks_triggering_decision(self, valid_header, valid_mcp, valid_verification_plan_payload):
        """Plan tracks which decision triggered it."""
        packet = VerificationPlanPacket(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_verification_plan_payload
        )
        assert packet.payload.triggering_decision_id is not None


class TestVerificationPlanWorkflow:
    """Tests for verification workflow semantics."""

    def test_on_success_options(self, valid_header, valid_mcp, valid_verification_plan_payload):
        """on_all_success can specify different actions."""
        for action in ["proceed_to_act", "re_decide", "escalate"]:
            valid_verification_plan_payload["on_all_success"] = action
            packet = VerificationPlanPacket(
                header=valid_header,
                mcp=valid_mcp,
                payload=valid_verification_plan_payload
            )
            assert packet.payload.on_all_success == action

    def test_on_failure_options(self, valid_header, valid_mcp, valid_verification_plan_payload):
        """on_any_failure can specify different actions."""
        for action in ["escalate", "defer", "retry", "abort"]:
            valid_verification_plan_payload["on_any_failure"] = action
            packet = VerificationPlanPacket(
                header=valid_header,
                mcp=valid_mcp,
                payload=valid_verification_plan_payload
            )
            assert packet.payload.on_any_failure == action

    def test_partial_success_mode(self, valid_header, valid_mcp, valid_verification_plan_payload):
        """Can allow partial verification success."""
        valid_verification_plan_payload["partial_success_acceptable"] = True
        packet = VerificationPlanPacket(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_verification_plan_payload
        )
        assert packet.payload.partial_success_acceptable is True
