"""
Tests for BeliefUpdatePacket schema.

Validates structure matches OMEN.md §9.3, §8.1.
"""

import json
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from omen.schemas import BeliefUpdatePacket, BeliefUpdatePayload
from omen.schemas.packets.belief_update import BeliefState, ContradictionRef
from omen.vocabulary import PacketType, LayerSource, EpistemicStatus


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def valid_belief_state() -> dict:
    return {
        "claim": "Character is in Jita",
        "status": "OBSERVED",
        "confidence": 0.95,
        "supporting_evidence": ["esi_loc_123"],
        "metadata": {"solar_system_id": 30000142}
    }


@pytest.fixture
def valid_belief_update_payload(valid_belief_state) -> dict:
    return {
        "belief_id": "character_location_12345",
        "belief_domain": "character_state",
        "prior_state": valid_belief_state,
        "new_state": {
            "claim": "Character is in Amarr",
            "status": "OBSERVED",
            "confidence": 0.98,
            "supporting_evidence": ["esi_loc_456"],
            "metadata": {"solar_system_id": 30002187}
        },
        "update_reason": "New observation from ESI",
        "triggering_observation_id": str(uuid4()),
        "contradiction_detected": False,
        "contradiction_refs": []
    }


@pytest.fixture
def valid_header() -> dict:
    return {
        "packet_type": "BeliefUpdatePacket",
        "created_at": "2025-12-21T11:31:00Z",
        "layer_source": "2",
        "correlation_id": str(uuid4())
    }


@pytest.fixture
def valid_mcp() -> dict:
    return {
        "intent": {"summary": "Update belief", "scope": "world_model"},
        "stakes": {
            "impact": "LOW",
            "irreversibility": "REVERSIBLE",
            "uncertainty": "LOW",
            "adversariality": "BENIGN",
            "stakes_level": "LOW"
        },
        "quality": {
            "quality_tier": "PAR",
            "satisficing_mode": True,
            "definition_of_done": {"text": "Belief updated", "checks": []},
            "verification_requirement": "OPTIONAL"
        },
        "budgets": {
            "token_budget": 50,
            "tool_call_budget": 0,
            "time_budget_seconds": 2,
            "risk_budget": {"envelope": "minimal", "max_loss": 0}
        },
        "epistemics": {
            "status": "DERIVED",
            "confidence": 0.95,
            "calibration_note": "Derived from observation",
            "freshness_class": "REALTIME",
            "stale_if_older_than_seconds": 60,
            "assumptions": []
        },
        "evidence": {
            "evidence_refs": [{
                "ref_type": "tool_output",
                "ref_id": "esi_456",
                "timestamp": "2025-12-21T11:30:00Z"
            }],
            "evidence_absent_reason": None
        },
        "routing": {"task_class": "CREATE", "tools_state": "tools_ok"}
    }


@pytest.fixture
def valid_belief_update_packet(valid_header, valid_mcp, valid_belief_update_payload) -> dict:
    return {
        "header": valid_header,
        "mcp": valid_mcp,
        "payload": valid_belief_update_payload
    }


# =============================================================================
# BELIEF STATE TESTS
# =============================================================================

class TestBeliefState:
    """Tests for BeliefState structure."""

    def test_valid_belief_state(self, valid_belief_state):
        state = BeliefState(**valid_belief_state)
        assert state.claim == "Character is in Jita"
        assert state.status == EpistemicStatus.OBSERVED
        assert state.confidence == 0.95

    def test_belief_state_minimal(self):
        state = BeliefState(
            claim="Test claim",
            status="HYPOTHESIZED",
            confidence=0.5
        )
        assert state.supporting_evidence == []
        assert state.metadata is None

    def test_belief_state_confidence_bounds(self):
        with pytest.raises(ValidationError):
            BeliefState(
                claim="Test",
                status="OBSERVED",
                confidence=1.5
            )

    def test_belief_state_all_epistemic_statuses(self):
        for status in EpistemicStatus:
            state = BeliefState(
                claim="Test",
                status=status.value,
                confidence=0.5
            )
            assert state.status == status


# =============================================================================
# CONTRADICTION REF TESTS
# =============================================================================

class TestContradictionRef:
    """Tests for ContradictionRef structure."""

    def test_valid_contradiction_ref(self):
        ref = ContradictionRef(
            contradicting_belief_id="belief_xyz",
            contradiction_type="direct",
            description="New location contradicts cached location"
        )
        assert ref.contradiction_type == "direct"

    def test_contradiction_ref_requires_all_fields(self):
        with pytest.raises(ValidationError):
            ContradictionRef(contradicting_belief_id="test")


# =============================================================================
# BELIEF UPDATE PAYLOAD TESTS
# =============================================================================

class TestBeliefUpdatePayload:
    """Tests for BeliefUpdatePayload structure."""

    def test_valid_payload(self, valid_belief_update_payload):
        payload = BeliefUpdatePayload(**valid_belief_update_payload)
        assert payload.belief_id == "character_location_12345"
        assert payload.belief_domain == "character_state"
        assert payload.new_state.claim == "Character is in Amarr"

    def test_payload_new_belief_no_prior(self, valid_belief_state):
        """New beliefs can have None for prior_state."""
        payload = BeliefUpdatePayload(
            belief_id="new_belief_123",
            belief_domain="intel",
            prior_state=None,
            new_state=valid_belief_state,
            update_reason="First observation of this entity"
        )
        assert payload.prior_state is None

    def test_payload_with_contradiction(self, valid_belief_state):
        payload = BeliefUpdatePayload(
            belief_id="test_belief",
            belief_domain="test",
            new_state=valid_belief_state,
            update_reason="Contradiction found",
            contradiction_detected=True,
            contradiction_refs=[{
                "contradicting_belief_id": "other_belief",
                "contradiction_type": "logical",
                "description": "Cannot be in two places at once"
            }]
        )
        assert payload.contradiction_detected is True
        assert len(payload.contradiction_refs) == 1

    def test_payload_requires_belief_id(self, valid_belief_state):
        with pytest.raises(ValidationError):
            BeliefUpdatePayload(
                belief_domain="test",
                new_state=valid_belief_state,
                update_reason="Test"
            )

    def test_payload_requires_new_state(self):
        with pytest.raises(ValidationError):
            BeliefUpdatePayload(
                belief_id="test",
                belief_domain="test",
                update_reason="Test"
            )


# =============================================================================
# COMPLETE PACKET TESTS
# =============================================================================

class TestBeliefUpdatePacket:
    """Tests for complete BeliefUpdatePacket."""

    def test_valid_packet(self, valid_belief_update_packet):
        packet = BeliefUpdatePacket(**valid_belief_update_packet)
        assert packet.header.packet_type == PacketType.BELIEF_UPDATE
        assert packet.payload.belief_id == "character_location_12345"

    def test_packet_requires_all_sections(self, valid_header, valid_mcp):
        with pytest.raises(ValidationError):
            BeliefUpdatePacket(header=valid_header, mcp=valid_mcp)

    def test_packet_enforces_packet_type(self, valid_belief_update_packet):
        """Packet type is enforced to be BeliefUpdatePacket."""
        valid_belief_update_packet["header"]["packet_type"] = "DecisionPacket"
        packet = BeliefUpdatePacket(**valid_belief_update_packet)
        assert packet.header.packet_type == PacketType.BELIEF_UPDATE

    def test_packet_serialization(self, valid_belief_update_packet):
        packet = BeliefUpdatePacket(**valid_belief_update_packet)
        json_str = packet.model_dump_json()
        parsed = json.loads(json_str)
        assert "header" in parsed
        assert "mcp" in parsed
        assert "payload" in parsed
        assert "belief_id" in parsed["payload"]

    def test_packet_roundtrip(self, valid_belief_update_packet):
        packet1 = BeliefUpdatePacket(**valid_belief_update_packet)
        json_str = packet1.model_dump_json()
        packet2 = BeliefUpdatePacket.model_validate_json(json_str)
        assert packet1.payload.belief_id == packet2.payload.belief_id
        assert packet1.payload.new_state.claim == packet2.payload.new_state.claim

    def test_packet_can_originate_from_multiple_layers(self, valid_belief_update_packet):
        """Belief updates can come from Layers 2-5."""
        for layer in ["2", "3", "4", "5"]:
            valid_belief_update_packet["header"]["layer_source"] = layer
            packet = BeliefUpdatePacket(**valid_belief_update_packet)
            assert packet.header.layer_source.value == layer

    def test_packet_tracks_triggering_observation(self, valid_belief_update_packet):
        """Can track which observation triggered the update."""
        packet = BeliefUpdatePacket(**valid_belief_update_packet)
        assert packet.payload.triggering_observation_id is not None


class TestBeliefUpdateContradictionHandling:
    """Tests for contradiction handling per OMEN.md §8.1."""

    def test_contradiction_detected_with_refs(self, valid_header, valid_mcp, valid_belief_state):
        payload = {
            "belief_id": "test",
            "belief_domain": "test",
            "new_state": valid_belief_state,
            "update_reason": "Contradiction",
            "contradiction_detected": True,
            "contradiction_refs": [{
                "contradicting_belief_id": "other",
                "contradiction_type": "direct",
                "description": "Direct contradiction"
            }]
        }
        packet = BeliefUpdatePacket(
            header=valid_header,
            mcp=valid_mcp,
            payload=payload
        )
        assert packet.payload.contradiction_detected is True
        assert len(packet.payload.contradiction_refs) == 1

    def test_no_contradiction(self, valid_belief_update_packet):
        packet = BeliefUpdatePacket(**valid_belief_update_packet)
        assert packet.payload.contradiction_detected is False
        assert packet.payload.contradiction_refs == []
