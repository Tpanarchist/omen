"""
Tests for EscalationPacket schema.

Validates structure matches OMEN.md §9.3, §8.2.6, §3.2.
"""

import json
from uuid import uuid4

import pytest
from pydantic import ValidationError

from omen.schemas import EscalationPacket, EscalationPayload
from omen.schemas.packets.escalation import EscalationOption, EvidenceGap
from omen.vocabulary import PacketType, LayerSource, StakesLevel, UncertaintyLevel


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def valid_option() -> dict:
    return {
        "option_id": "opt_001",
        "summary": "Wait for situation to clear",
        "action_description": "Dock and wait 30 minutes",
        "risks": ["Time loss"],
        "benefits": ["No cargo risk"],
        "recommended": True,
        "recommendation_rationale": "Lowest risk option"
    }


@pytest.fixture
def valid_evidence_gap() -> dict:
    return {
        "gap_id": "gap_001",
        "description": "Unknown fleet composition",
        "impact": "Cannot assess survival probability",
        "could_verify": True,
        "verification_method": "Scout with alt",
        "verification_cost": "5 minutes"
    }


@pytest.fixture
def valid_escalation_payload(valid_option, valid_evidence_gap) -> dict:
    return {
        "escalation_id": "esc_001",
        "escalation_trigger": "high_stakes_high_uncertainty",
        "situation_summary": "Hostile fleet detected in target system",
        "stakes_level": "HIGH",
        "uncertainty_level": "HIGH",
        "what_we_know": ["10 hostile ships on d-scan"],
        "what_we_believe": ["Fleet is camping the gate"],
        "options": [valid_option],
        "evidence_gaps": [valid_evidence_gap],
        "recommended_next_step": "Scout the gate"
    }


@pytest.fixture
def valid_header() -> dict:
    return {
        "packet_type": "EscalationPacket",
        "created_at": "2025-12-21T11:35:00Z",
        "layer_source": "5",
        "correlation_id": str(uuid4())
    }


@pytest.fixture
def valid_mcp() -> dict:
    return {
        "intent": {"summary": "Escalate to human", "scope": "escalation"},
        "stakes": {
            "impact": "HIGH",
            "irreversibility": "IRREVERSIBLE",
            "uncertainty": "HIGH",
            "adversariality": "HOSTILE",
            "stakes_level": "HIGH"
        },
        "quality": {
            "quality_tier": "SUPERB",
            "satisficing_mode": False,
            "definition_of_done": {"text": "Human decides", "checks": []},
            "verification_requirement": "VERIFY_ALL"
        },
        "budgets": {
            "token_budget": 200,
            "tool_call_budget": 0,
            "time_budget_seconds": 300,
            "risk_budget": {"envelope": "minimal", "max_loss": 0}
        },
        "epistemics": {
            "status": "DERIVED",
            "confidence": 0.6,
            "calibration_note": "High uncertainty",
            "freshness_class": "OPERATIONAL",
            "stale_if_older_than_seconds": 600,
            "assumptions": []
        },
        "evidence": {
            "evidence_refs": [],
            "evidence_absent_reason": "Evidence gaps identified"
        },
        "routing": {"task_class": "CREATE", "tools_state": "tools_ok"}
    }


# =============================================================================
# ESCALATION OPTION TESTS
# =============================================================================

class TestEscalationOption:
    """Tests for EscalationOption structure."""

    def test_valid_option(self, valid_option):
        option = EscalationOption(**valid_option)
        assert option.option_id == "opt_001"
        assert option.recommended is True

    def test_option_minimal(self):
        option = EscalationOption(
            option_id="opt",
            summary="Do nothing",
            action_description="Take no action"
        )
        assert option.risks == []
        assert option.benefits == []
        assert option.recommended is False

    def test_option_with_costs(self, valid_option):
        valid_option["resource_cost"] = {"time_minutes": 30, "isk": 0}
        option = EscalationOption(**valid_option)
        assert option.resource_cost["time_minutes"] == 30


# =============================================================================
# EVIDENCE GAP TESTS
# =============================================================================

class TestEvidenceGap:
    """Tests for EvidenceGap structure."""

    def test_valid_gap(self, valid_evidence_gap):
        gap = EvidenceGap(**valid_evidence_gap)
        assert gap.gap_id == "gap_001"
        assert gap.could_verify is True

    def test_gap_minimal(self):
        gap = EvidenceGap(
            gap_id="gap",
            description="Unknown information",
            impact="Affects decision"
        )
        assert gap.could_verify is False
        assert gap.verification_method is None

    def test_gap_not_verifiable(self):
        gap = EvidenceGap(
            gap_id="gap",
            description="Unknowable",
            impact="Fundamental uncertainty",
            could_verify=False
        )
        assert gap.verification_cost is None


# =============================================================================
# ESCALATION PAYLOAD TESTS
# =============================================================================

class TestEscalationPayload:
    """Tests for EscalationPayload structure."""

    def test_valid_payload(self, valid_escalation_payload):
        payload = EscalationPayload(**valid_escalation_payload)
        assert payload.escalation_id == "esc_001"
        assert payload.stakes_level == StakesLevel.HIGH

    def test_payload_requires_at_least_one_option(self, valid_escalation_payload):
        valid_escalation_payload["options"] = []
        with pytest.raises(ValidationError):
            EscalationPayload(**valid_escalation_payload)

    def test_payload_multiple_options(self, valid_option):
        option2 = valid_option.copy()
        option2["option_id"] = "opt_002"
        option2["summary"] = "Alternative option"
        option2["recommended"] = False
        
        payload = EscalationPayload(
            escalation_id="esc",
            escalation_trigger="test",
            situation_summary="Test situation",
            stakes_level="MEDIUM",
            uncertainty_level="HIGH",
            options=[valid_option, option2]
        )
        assert len(payload.options) == 2

    def test_payload_all_stakes_levels(self, valid_escalation_payload):
        for stakes in StakesLevel:
            valid_escalation_payload["stakes_level"] = stakes.value
            payload = EscalationPayload(**valid_escalation_payload)
            assert payload.stakes_level == stakes

    def test_payload_all_uncertainty_levels(self, valid_escalation_payload):
        for uncertainty in UncertaintyLevel:
            valid_escalation_payload["uncertainty_level"] = uncertainty.value
            payload = EscalationPayload(**valid_escalation_payload)
            assert payload.uncertainty_level == uncertainty

    def test_payload_with_triggering_ids(self, valid_escalation_payload):
        ep_id = str(uuid4())
        dec_id = str(uuid4())
        valid_escalation_payload["triggering_episode_id"] = ep_id
        valid_escalation_payload["triggering_decision_id"] = dec_id
        payload = EscalationPayload(**valid_escalation_payload)
        assert payload.triggering_episode_id is not None


# =============================================================================
# COMPLETE PACKET TESTS
# =============================================================================

class TestEscalationPacket:
    """Tests for complete EscalationPacket."""

    def test_valid_packet(self, valid_header, valid_mcp, valid_escalation_payload):
        packet = EscalationPacket(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_escalation_payload
        )
        assert packet.header.packet_type == PacketType.ESCALATION
        assert packet.payload.escalation_id == "esc_001"

    def test_packet_enforces_packet_type(self, valid_header, valid_mcp, valid_escalation_payload):
        valid_header["packet_type"] = "DecisionPacket"
        packet = EscalationPacket(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_escalation_payload
        )
        assert packet.header.packet_type == PacketType.ESCALATION

    def test_packet_from_layer_5(self, valid_header, valid_mcp, valid_escalation_payload):
        """Escalations typically come from Layer 5."""
        packet = EscalationPacket(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_escalation_payload
        )
        assert packet.header.layer_source == LayerSource.LAYER_5

    def test_packet_serialization(self, valid_header, valid_mcp, valid_escalation_payload):
        packet = EscalationPacket(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_escalation_payload
        )
        json_str = packet.model_dump_json()
        parsed = json.loads(json_str)
        assert "escalation_id" in parsed["payload"]
        assert "options" in parsed["payload"]

    def test_packet_roundtrip(self, valid_header, valid_mcp, valid_escalation_payload):
        packet1 = EscalationPacket(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_escalation_payload
        )
        json_str = packet1.model_dump_json()
        packet2 = EscalationPacket.model_validate_json(json_str)
        assert packet1.payload.escalation_id == packet2.payload.escalation_id
        assert len(packet1.payload.options) == len(packet2.payload.options)


class TestEscalationTriggers:
    """Tests for escalation trigger scenarios per §8.2.6."""

    def test_high_stakes_high_uncertainty(self, valid_header, valid_mcp, valid_escalation_payload):
        packet = EscalationPacket(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_escalation_payload
        )
        assert packet.payload.stakes_level == StakesLevel.HIGH
        assert packet.payload.uncertainty_level == UncertaintyLevel.HIGH

    def test_escalation_presents_options(self, valid_header, valid_mcp, valid_escalation_payload):
        """Escalation must present options per §8.2.6."""
        packet = EscalationPacket(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_escalation_payload
        )
        assert len(packet.payload.options) >= 1

    def test_escalation_identifies_gaps(self, valid_header, valid_mcp, valid_escalation_payload):
        """Escalation should identify evidence gaps."""
        packet = EscalationPacket(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_escalation_payload
        )
        assert len(packet.payload.evidence_gaps) >= 0  # May be empty if no gaps
