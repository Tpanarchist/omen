"""
Tests for packet header schema.

Validates structure matches OMEN.md §9.1.
"""

import json
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omen.schemas import PacketHeader
from omen.vocabulary import PacketType, LayerSource


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def valid_header_data() -> dict:
    """Minimal valid header data."""
    return {
        "packet_type": "DecisionPacket",
        "created_at": "2025-12-21T11:32:00-05:00",
        "layer_source": "5",
        "correlation_id": "77a88b99-c0d1-e2f3-4567-890abcdef012",
    }


@pytest.fixture
def full_header_data(valid_header_data) -> dict:
    """Header with all optional fields populated."""
    return {
        **valid_header_data,
        "packet_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "campaign_id": "deadbeef-cafe-babe-1234-567890abcdef",
        "previous_packet_id": "11112222-3333-4444-5555-666677778888",
    }


# =============================================================================
# BASIC VALIDATION TESTS
# =============================================================================

class TestPacketHeaderBasics:
    """Basic header validation tests."""

    def test_valid_minimal_header(self, valid_header_data):
        """Header with only required fields validates."""
        header = PacketHeader(**valid_header_data)
        assert header.packet_type == PacketType.DECISION
        assert header.layer_source == LayerSource.LAYER_5
        assert header.correlation_id == UUID("77a88b99-c0d1-e2f3-4567-890abcdef012")

    def test_valid_full_header(self, full_header_data):
        """Header with all fields validates."""
        header = PacketHeader(**full_header_data)
        assert header.packet_id == UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
        assert header.campaign_id == UUID("deadbeef-cafe-babe-1234-567890abcdef")
        assert header.previous_packet_id == UUID("11112222-3333-4444-5555-666677778888")

    def test_packet_id_auto_generated(self, valid_header_data):
        """packet_id is auto-generated if not provided."""
        header = PacketHeader(**valid_header_data)
        assert header.packet_id is not None
        assert isinstance(header.packet_id, UUID)

    def test_packet_id_unique_per_instance(self, valid_header_data):
        """Each header gets a unique packet_id."""
        header1 = PacketHeader(**valid_header_data)
        header2 = PacketHeader(**valid_header_data)
        assert header1.packet_id != header2.packet_id

    def test_optional_fields_default_none(self, valid_header_data):
        """Optional fields default to None."""
        header = PacketHeader(**valid_header_data)
        assert header.campaign_id is None
        assert header.previous_packet_id is None


# =============================================================================
# REQUIRED FIELD TESTS
# =============================================================================

class TestRequiredFields:
    """Tests for required fields."""

    def test_packet_type_required(self, valid_header_data):
        """packet_type is required."""
        del valid_header_data["packet_type"]
        with pytest.raises(ValidationError) as exc_info:
            PacketHeader(**valid_header_data)
        assert "packet_type" in str(exc_info.value)

    def test_created_at_required(self, valid_header_data):
        """created_at is required."""
        del valid_header_data["created_at"]
        with pytest.raises(ValidationError) as exc_info:
            PacketHeader(**valid_header_data)
        assert "created_at" in str(exc_info.value)

    def test_layer_source_required(self, valid_header_data):
        """layer_source is required."""
        del valid_header_data["layer_source"]
        with pytest.raises(ValidationError) as exc_info:
            PacketHeader(**valid_header_data)
        assert "layer_source" in str(exc_info.value)

    def test_correlation_id_required(self, valid_header_data):
        """correlation_id is required."""
        del valid_header_data["correlation_id"]
        with pytest.raises(ValidationError) as exc_info:
            PacketHeader(**valid_header_data)
        assert "correlation_id" in str(exc_info.value)


# =============================================================================
# PACKET TYPE TESTS
# =============================================================================

class TestPacketTypes:
    """Tests for packet_type field."""

    def test_all_packet_types_valid(self, valid_header_data):
        """All 9 packet types are accepted."""
        for packet_type in PacketType:
            valid_header_data["packet_type"] = packet_type.value
            header = PacketHeader(**valid_header_data)
            assert header.packet_type == packet_type

    def test_invalid_packet_type_rejected(self, valid_header_data):
        """Invalid packet type is rejected."""
        valid_header_data["packet_type"] = "InvalidPacket"
        with pytest.raises(ValidationError):
            PacketHeader(**valid_header_data)

    def test_packet_type_count(self):
        """There are exactly 9 packet types per spec."""
        assert len(PacketType) == 9


# =============================================================================
# LAYER SOURCE TESTS
# =============================================================================

class TestLayerSources:
    """Tests for layer_source field."""

    def test_all_layer_sources_valid(self, valid_header_data):
        """All 7 layer sources are accepted (6 layers + Integrity)."""
        for layer_source in LayerSource:
            valid_header_data["layer_source"] = layer_source.value
            header = PacketHeader(**valid_header_data)
            assert header.layer_source == layer_source

    def test_invalid_layer_source_rejected(self, valid_header_data):
        """Invalid layer source is rejected."""
        valid_header_data["layer_source"] = "7"
        with pytest.raises(ValidationError):
            PacketHeader(**valid_header_data)

    def test_integrity_layer_source(self, valid_header_data):
        """Integrity overlay can be a packet source."""
        valid_header_data["layer_source"] = "Integrity"
        header = PacketHeader(**valid_header_data)
        assert header.layer_source == LayerSource.INTEGRITY

    def test_layer_source_count(self):
        """There are exactly 7 layer sources per spec."""
        assert len(LayerSource) == 7


# =============================================================================
# TIMESTAMP TESTS
# =============================================================================

class TestTimestamps:
    """Tests for timestamp fields."""

    def test_created_at_iso_format(self, valid_header_data):
        """created_at accepts ISO 8601 format."""
        header = PacketHeader(**valid_header_data)
        assert header.created_at.year == 2025
        assert header.created_at.month == 12
        assert header.created_at.day == 21

    def test_created_at_with_timezone(self, valid_header_data):
        """created_at preserves timezone info."""
        valid_header_data["created_at"] = "2025-06-15T10:30:00Z"
        header = PacketHeader(**valid_header_data)
        assert header.created_at.tzinfo is not None

    def test_created_at_datetime_object(self, valid_header_data):
        """created_at accepts datetime objects."""
        valid_header_data["created_at"] = datetime.now(timezone.utc)
        header = PacketHeader(**valid_header_data)
        assert isinstance(header.created_at, datetime)


# =============================================================================
# UUID TESTS
# =============================================================================

class TestUUIDs:
    """Tests for UUID fields."""

    def test_correlation_id_accepts_string(self, valid_header_data):
        """correlation_id accepts UUID string."""
        header = PacketHeader(**valid_header_data)
        assert isinstance(header.correlation_id, UUID)

    def test_correlation_id_accepts_uuid_object(self, valid_header_data):
        """correlation_id accepts UUID object."""
        valid_header_data["correlation_id"] = uuid4()
        header = PacketHeader(**valid_header_data)
        assert isinstance(header.correlation_id, UUID)

    def test_invalid_uuid_rejected(self, valid_header_data):
        """Invalid UUID format is rejected."""
        valid_header_data["correlation_id"] = "not-a-uuid"
        with pytest.raises(ValidationError):
            PacketHeader(**valid_header_data)

    def test_campaign_id_accepts_uuid(self, valid_header_data):
        """campaign_id accepts valid UUID."""
        valid_header_data["campaign_id"] = "deadbeef-cafe-babe-1234-567890abcdef"
        header = PacketHeader(**valid_header_data)
        assert header.campaign_id == UUID("deadbeef-cafe-babe-1234-567890abcdef")

    def test_previous_packet_id_accepts_uuid(self, valid_header_data):
        """previous_packet_id accepts valid UUID."""
        valid_header_data["previous_packet_id"] = str(uuid4())
        header = PacketHeader(**valid_header_data)
        assert isinstance(header.previous_packet_id, UUID)


# =============================================================================
# SERIALIZATION TESTS
# =============================================================================

class TestSerialization:
    """Tests for JSON serialization."""

    def test_serializes_to_json(self, full_header_data):
        """Header serializes to JSON."""
        header = PacketHeader(**full_header_data)
        json_str = header.model_dump_json()
        parsed = json.loads(json_str)
        
        assert "packet_id" in parsed
        assert "packet_type" in parsed
        assert "created_at" in parsed
        assert "layer_source" in parsed
        assert "correlation_id" in parsed

    def test_roundtrip(self, full_header_data):
        """Header can be serialized and deserialized."""
        header1 = PacketHeader(**full_header_data)
        json_str = header1.model_dump_json()
        header2 = PacketHeader.model_validate_json(json_str)
        
        assert header1.packet_id == header2.packet_id
        assert header1.packet_type == header2.packet_type
        assert header1.layer_source == header2.layer_source
        assert header1.correlation_id == header2.correlation_id

    def test_json_schema_generation(self):
        """Header can generate JSON Schema."""
        schema = PacketHeader.model_json_schema()
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "packet_id" in schema["properties"]
        assert "packet_type" in schema["properties"]


# =============================================================================
# SPEC EXAMPLE TEST
# =============================================================================

class TestSpecExample:
    """Test against spec example from OMEN.md §15.2."""

    def test_spec_example_header(self):
        """Header from canonical Decision Packet example validates."""
        spec_header = {
            "packet_id": "a1b2c3d4-0123-4567-89ab-cdef01234567",
            "packet_type": "DecisionPacket",
            "created_at": "2025-12-21T11:32:00-05:00",
            "layer_source": "5",
            "correlation_id": "77a88b99-c0d1-e2f3-4567-890abcdef012",
            "campaign_id": "deadbeef-cafe-babe-1234-567890abcdef",
        }
        
        header = PacketHeader(**spec_header)
        
        assert header.packet_type == PacketType.DECISION
        assert header.layer_source == LayerSource.LAYER_5
        assert header.created_at.year == 2025
