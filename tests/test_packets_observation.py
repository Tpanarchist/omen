"""
Tests for ObservationPacket schema.

Validates structure matches OMEN.md §9.3, §5.1.
"""

import json
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from omen.schemas import ObservationPacket, ObservationPayload, MCP, PacketHeader
from omen.schemas.packets.observation import ObservationSource
from omen.vocabulary import PacketType, LayerSource, EpistemicStatus


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def valid_observation_source() -> dict:
    return {
        "source_type": "esi_api",
        "source_id": "/characters/{character_id}/location/",
        "query_params": {"character_id": 12345}
    }


@pytest.fixture
def valid_observation_payload(valid_observation_source) -> dict:
    return {
        "source": valid_observation_source,
        "observation_type": "character_location",
        "observed_at": "2025-12-21T11:30:00Z",
        "content": {"solar_system_id": 30000142, "station_id": 60003760},
        "raw_ref": "esi_resp_abc123",
        "content_hash": "sha256:abcdef1234567890"
    }


@pytest.fixture
def valid_header() -> dict:
    return {
        "packet_type": "ObservationPacket",
        "created_at": "2025-12-21T11:30:00Z",
        "layer_source": "6",
        "correlation_id": str(uuid4())
    }


@pytest.fixture
def valid_mcp() -> dict:
    return {
        "intent": {"summary": "Report observation", "scope": "sensorium"},
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
            "definition_of_done": {"text": "Observation recorded", "checks": []},
            "verification_requirement": "OPTIONAL"
        },
        "budgets": {
            "token_budget": 100,
            "tool_call_budget": 0,
            "time_budget_seconds": 5,
            "risk_budget": {"envelope": "minimal", "max_loss": 0}
        },
        "epistemics": {
            "status": "OBSERVED",
            "confidence": 0.99,
            "calibration_note": "Direct API response",
            "freshness_class": "REALTIME",
            "stale_if_older_than_seconds": 60,
            "assumptions": []
        },
        "evidence": {
            "evidence_refs": [{
                "ref_type": "tool_output",
                "ref_id": "esi_12345",
                "timestamp": "2025-12-21T11:30:00Z"
            }],
            "evidence_absent_reason": None
        },
        "routing": {"task_class": "LOOKUP", "tools_state": "tools_ok"}
    }


@pytest.fixture
def valid_observation_packet(valid_header, valid_mcp, valid_observation_payload) -> dict:
    return {
        "header": valid_header,
        "mcp": valid_mcp,
        "payload": valid_observation_payload
    }


# =============================================================================
# OBSERVATION SOURCE TESTS
# =============================================================================

class TestObservationSource:
    """Tests for ObservationSource structure."""

    def test_valid_source(self, valid_observation_source):
        source = ObservationSource(**valid_observation_source)
        assert source.source_type == "esi_api"
        assert source.source_id == "/characters/{character_id}/location/"

    def test_source_without_query_params(self):
        source = ObservationSource(
            source_type="sensor",
            source_id="temp_sensor_1"
        )
        assert source.query_params is None

    def test_source_requires_type(self):
        with pytest.raises(ValidationError):
            ObservationSource(source_id="test")

    def test_source_requires_id(self):
        with pytest.raises(ValidationError):
            ObservationSource(source_type="test")


# =============================================================================
# OBSERVATION PAYLOAD TESTS
# =============================================================================

class TestObservationPayload:
    """Tests for ObservationPayload structure."""

    def test_valid_payload(self, valid_observation_payload):
        payload = ObservationPayload(**valid_observation_payload)
        assert payload.observation_type == "character_location"
        assert payload.content["solar_system_id"] == 30000142

    def test_payload_minimal(self, valid_observation_source):
        payload = ObservationPayload(
            source=valid_observation_source,
            observation_type="test",
            observed_at="2025-01-01T00:00:00Z",
            content={"key": "value"}
        )
        assert payload.raw_ref is None
        assert payload.content_hash is None

    def test_payload_requires_source(self):
        with pytest.raises(ValidationError):
            ObservationPayload(
                observation_type="test",
                observed_at="2025-01-01T00:00:00Z",
                content={}
            )

    def test_payload_requires_content(self, valid_observation_source):
        with pytest.raises(ValidationError):
            ObservationPayload(
                source=valid_observation_source,
                observation_type="test",
                observed_at="2025-01-01T00:00:00Z"
            )

    def test_payload_content_flexible(self, valid_observation_source):
        """Content can have any structure."""
        payload = ObservationPayload(
            source=valid_observation_source,
            observation_type="complex",
            observed_at="2025-01-01T00:00:00Z",
            content={
                "nested": {"deep": {"value": 42}},
                "array": [1, 2, 3],
                "mixed": ["a", 1, {"b": 2}]
            }
        )
        assert payload.content["nested"]["deep"]["value"] == 42


# =============================================================================
# COMPLETE PACKET TESTS
# =============================================================================

class TestObservationPacket:
    """Tests for complete ObservationPacket."""

    def test_valid_packet(self, valid_observation_packet):
        packet = ObservationPacket(**valid_observation_packet)
        assert packet.header.packet_type == PacketType.OBSERVATION
        assert packet.payload.observation_type == "character_location"

    def test_packet_requires_all_sections(self, valid_header, valid_mcp):
        with pytest.raises(ValidationError):
            ObservationPacket(header=valid_header, mcp=valid_mcp)

    def test_packet_enforces_packet_type(self, valid_observation_packet):
        """Packet type is enforced to be ObservationPacket."""
        valid_observation_packet["header"]["packet_type"] = "DecisionPacket"
        packet = ObservationPacket(**valid_observation_packet)
        # Should be overridden to ObservationPacket
        assert packet.header.packet_type == PacketType.OBSERVATION

    def test_packet_serialization(self, valid_observation_packet):
        packet = ObservationPacket(**valid_observation_packet)
        json_str = packet.model_dump_json()
        parsed = json.loads(json_str)
        assert "header" in parsed
        assert "mcp" in parsed
        assert "payload" in parsed

    def test_packet_roundtrip(self, valid_observation_packet):
        packet1 = ObservationPacket(**valid_observation_packet)
        json_str = packet1.model_dump_json()
        packet2 = ObservationPacket.model_validate_json(json_str)
        assert packet1.payload.observation_type == packet2.payload.observation_type
        assert packet1.payload.content == packet2.payload.content

    def test_packet_typically_from_layer_6(self, valid_observation_packet):
        """Observations typically originate from Layer 6."""
        packet = ObservationPacket(**valid_observation_packet)
        assert packet.header.layer_source == LayerSource.LAYER_6

    def test_packet_epistemics_typically_observed(self, valid_observation_packet):
        """Observation packets typically have OBSERVED epistemic status."""
        packet = ObservationPacket(**valid_observation_packet)
        assert packet.mcp.epistemics.status == EpistemicStatus.OBSERVED
