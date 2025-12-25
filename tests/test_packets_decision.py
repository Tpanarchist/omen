"""
Tests for DecisionPacket schema.

Validates structure matches OMEN.md §9.3, §15.2.
"""

import json
from uuid import uuid4

import pytest
from pydantic import ValidationError

from omen.schemas import DecisionPacket, DecisionPayload
from omen.schemas.packets.decision import RejectedAlternative
from omen.vocabulary import PacketType, LayerSource, DecisionOutcome


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def valid_rejected_alternative() -> dict:
    return {
        "option_id": "alt_001",
        "summary": "Alternative approach",
        "rejection_reason": "Too risky",
        "stage_rejected": "tradeoff"
    }


@pytest.fixture
def valid_decision_payload_act() -> dict:
    return {
        "decision_outcome": "ACT",
        "decision_summary": "Proceed with the planned action",
        "chosen_option_id": "option_001",
        "rationale": "All conditions met, low risk",
        "assumptions": ["Resources available", "Time window open"],
        "load_bearing_assumptions": ["Target system is accessible"],
        "rejected_alternatives": []
    }


@pytest.fixture
def valid_decision_payload_verify_first() -> dict:
    return {
        "decision_outcome": "VERIFY_FIRST",
        "decision_summary": "Verify threat level before proceeding",
        "rationale": "Uncertainty is high, verification cost is low",
        "assumptions": ["Tools available"],
        "load_bearing_assumptions": ["Threat level is acceptable"],
        "required_verifications": ["Check current threat level"]
    }


@pytest.fixture
def valid_decision_payload_escalate() -> dict:
    return {
        "decision_outcome": "ESCALATE",
        "decision_summary": "Escalate to human operator",
        "rationale": "Stakes too high for autonomous decision",
        "assumptions": [],
        "load_bearing_assumptions": [],
        "escalation_reason": "Critical stakes with high uncertainty"
    }


@pytest.fixture
def valid_decision_payload_defer() -> dict:
    return {
        "decision_outcome": "DEFER",
        "decision_summary": "Defer action until market stabilizes",
        "rationale": "Current volatility too high",
        "assumptions": [],
        "load_bearing_assumptions": [],
        "defer_until": "Market volatility < 5%"
    }


@pytest.fixture
def valid_header() -> dict:
    return {
        "packet_type": "DecisionPacket",
        "created_at": "2025-12-21T11:32:00Z",
        "layer_source": "5",
        "correlation_id": str(uuid4())
    }


@pytest.fixture
def valid_mcp() -> dict:
    return {
        "intent": {"summary": "Make decision", "scope": "action"},
        "stakes": {
            "impact": "MEDIUM",
            "irreversibility": "REVERSIBLE",
            "uncertainty": "MEDIUM",
            "adversariality": "BENIGN",
            "stakes_level": "MEDIUM"
        },
        "quality": {
            "quality_tier": "PAR",
            "satisficing_mode": True,
            "definition_of_done": {"text": "Decision made", "checks": []},
            "verification_requirement": "VERIFY_ONE"
        },
        "budgets": {
            "token_budget": 500,
            "tool_call_budget": 2,
            "time_budget_seconds": 60,
            "risk_budget": {"envelope": "medium", "max_loss": 1000}
        },
        "epistemics": {
            "status": "DERIVED",
            "confidence": 0.75,
            "calibration_note": "Based on available evidence",
            "freshness_class": "OPERATIONAL",
            "stale_if_older_than_seconds": 300,
            "assumptions": []
        },
        "evidence": {
            "evidence_refs": [{
                "ref_type": "tool_output",
                "ref_id": "obs_123",
                "timestamp": "2025-12-21T11:31:00Z"
            }],
            "evidence_absent_reason": None
        },
        "routing": {"task_class": "CREATE", "tools_state": "tools_ok"}
    }


# =============================================================================
# REJECTED ALTERNATIVE TESTS
# =============================================================================

class TestRejectedAlternative:
    """Tests for RejectedAlternative structure."""

    def test_valid_alternative(self, valid_rejected_alternative):
        alt = RejectedAlternative(**valid_rejected_alternative)
        assert alt.option_id == "alt_001"
        assert alt.stage_rejected == "tradeoff"

    def test_alternative_without_stage(self):
        alt = RejectedAlternative(
            option_id="alt",
            summary="Test",
            rejection_reason="Not viable"
        )
        assert alt.stage_rejected is None

    def test_alternative_requires_core_fields(self):
        with pytest.raises(ValidationError):
            RejectedAlternative(option_id="test")


# =============================================================================
# DECISION PAYLOAD TESTS
# =============================================================================

class TestDecisionPayload:
    """Tests for DecisionPayload structure."""

    def test_valid_act_payload(self, valid_decision_payload_act):
        payload = DecisionPayload(**valid_decision_payload_act)
        assert payload.decision_outcome == DecisionOutcome.ACT
        assert payload.chosen_option_id == "option_001"

    def test_valid_verify_first_payload(self, valid_decision_payload_verify_first):
        payload = DecisionPayload(**valid_decision_payload_verify_first)
        assert payload.decision_outcome == DecisionOutcome.VERIFY_FIRST
        assert len(payload.required_verifications) == 1

    def test_valid_escalate_payload(self, valid_decision_payload_escalate):
        payload = DecisionPayload(**valid_decision_payload_escalate)
        assert payload.decision_outcome == DecisionOutcome.ESCALATE
        assert payload.escalation_reason is not None

    def test_valid_defer_payload(self, valid_decision_payload_defer):
        payload = DecisionPayload(**valid_decision_payload_defer)
        assert payload.decision_outcome == DecisionOutcome.DEFER
        assert payload.defer_until is not None

    def test_all_decision_outcomes_valid(self):
        for outcome in DecisionOutcome:
            payload_data = {
                "decision_outcome": outcome.value,
                "decision_summary": f"Test {outcome.value}",
                "rationale": "Test rationale"
            }
            # Add required fields for specific outcomes
            if outcome == DecisionOutcome.VERIFY_FIRST:
                payload_data["required_verifications"] = ["test"]
            if outcome == DecisionOutcome.ESCALATE:
                payload_data["escalation_reason"] = "test"
            
            payload = DecisionPayload(**payload_data)
            assert payload.decision_outcome == outcome

    def test_payload_with_rejected_alternatives(self, valid_decision_payload_act, valid_rejected_alternative):
        valid_decision_payload_act["rejected_alternatives"] = [valid_rejected_alternative]
        payload = DecisionPayload(**valid_decision_payload_act)
        assert len(payload.rejected_alternatives) == 1

    def test_payload_requires_decision_outcome(self):
        with pytest.raises(ValidationError):
            DecisionPayload(
                decision_summary="Test",
                rationale="Test"
            )


# =============================================================================
# COMPLETE PACKET TESTS
# =============================================================================

class TestDecisionPacket:
    """Tests for complete DecisionPacket."""

    def test_valid_act_packet(self, valid_header, valid_mcp, valid_decision_payload_act):
        packet = DecisionPacket(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_decision_payload_act
        )
        assert packet.header.packet_type == PacketType.DECISION
        assert packet.payload.decision_outcome == DecisionOutcome.ACT

    def test_valid_verify_first_packet(self, valid_header, valid_mcp, valid_decision_payload_verify_first):
        packet = DecisionPacket(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_decision_payload_verify_first
        )
        assert packet.payload.decision_outcome == DecisionOutcome.VERIFY_FIRST

    def test_verify_first_requires_verifications(self, valid_header, valid_mcp):
        """VERIFY_FIRST must specify what to verify."""
        payload = {
            "decision_outcome": "VERIFY_FIRST",
            "decision_summary": "Verify first",
            "rationale": "Need to check"
            # Missing required_verifications
        }
        with pytest.raises(ValidationError) as exc_info:
            DecisionPacket(header=valid_header, mcp=valid_mcp, payload=payload)
        assert "required_verifications" in str(exc_info.value)

    def test_escalate_requires_reason(self, valid_header, valid_mcp):
        """ESCALATE must specify why."""
        payload = {
            "decision_outcome": "ESCALATE",
            "decision_summary": "Escalate",
            "rationale": "Too complex"
            # Missing escalation_reason
        }
        with pytest.raises(ValidationError) as exc_info:
            DecisionPacket(header=valid_header, mcp=valid_mcp, payload=payload)
        assert "escalation_reason" in str(exc_info.value)

    def test_packet_enforces_packet_type(self, valid_header, valid_mcp, valid_decision_payload_act):
        valid_header["packet_type"] = "ObservationPacket"
        packet = DecisionPacket(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_decision_payload_act
        )
        assert packet.header.packet_type == PacketType.DECISION

    def test_packet_from_layer_5(self, valid_header, valid_mcp, valid_decision_payload_act):
        """Decisions come from Layer 5 (Cognitive Control)."""
        packet = DecisionPacket(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_decision_payload_act
        )
        assert packet.header.layer_source == LayerSource.LAYER_5

    def test_packet_serialization(self, valid_header, valid_mcp, valid_decision_payload_act):
        packet = DecisionPacket(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_decision_payload_act
        )
        json_str = packet.model_dump_json()
        parsed = json.loads(json_str)
        assert "decision_outcome" in parsed["payload"]
        assert parsed["payload"]["decision_outcome"] == "ACT"

    def test_packet_roundtrip(self, valid_header, valid_mcp, valid_decision_payload_act):
        packet1 = DecisionPacket(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_decision_payload_act
        )
        json_str = packet1.model_dump_json()
        packet2 = DecisionPacket.model_validate_json(json_str)
        assert packet1.payload.decision_outcome == packet2.payload.decision_outcome
        assert packet1.payload.decision_summary == packet2.payload.decision_summary


class TestDecisionPacketSpecExample:
    """Test against canonical example from OMEN.md §15.2."""

    def test_spec_example_validates(self):
        """The exact example from §15.2 should validate."""
        spec_example = {
            "header": {
                "packet_type": "DecisionPacket",
                "created_at": "2025-12-21T11:32:00-05:00",
                "layer_source": "5",
                "correlation_id": "77a88b99-c0d1-e2f3-4567-890abcdef012",
                "campaign_id": "deadbeef-cafe-babe-1234-567890abcdef"
            },
            "mcp": {
                "intent": {"summary": "Decide whether to verify intel before acting", "scope": "intel_update"},
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
                    "definition_of_done": {"text": "Have at least one fresh observation for the key unknown", "checks": ["fresh evidence collected"]},
                    "verification_requirement": "VERIFY_ONE"
                },
                "budgets": {
                    "token_budget": 900,
                    "tool_call_budget": 2,
                    "time_budget_seconds": 90,
                    "risk_budget": {"envelope": "low", "max_loss": "small"}
                },
                "epistemics": {
                    "status": "HYPOTHESIZED",
                    "confidence": 0.45,
                    "calibration_note": "Uncertainty high; no fresh observation yet",
                    "freshness_class": "OPERATIONAL",
                    "stale_if_older_than_seconds": 1800,
                    "assumptions": ["Local threat level is low enough to proceed"]
                },
                "evidence": {
                    "evidence_refs": [],
                    "evidence_absent_reason": "No tool read executed yet in this episode"
                },
                "routing": {"task_class": "VERIFY", "tools_state": "tools_ok"}
            },
            "payload": {
                "decision_outcome": "VERIFY_FIRST",
                "decision_summary": "Verify the load-bearing assumption with one tool read before any action.",
                "rationale": "Uncertainty is high and we have tool access",
                "assumptions": [],
                "load_bearing_assumptions": ["Local threat level is low enough to proceed"],
                "required_verifications": ["Confirm current threat level"]
            }
        }
        
        packet = DecisionPacket(**spec_example)
        assert packet.payload.decision_outcome == DecisionOutcome.VERIFY_FIRST
        assert packet.mcp.epistemics.confidence == 0.45
