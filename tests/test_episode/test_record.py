"""Tests for episode records."""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from omen.episode import (
    PacketRecord,
    StepRecord,
    EpisodeRecord,
)


class TestPacketRecord:
    """Tests for PacketRecord."""
    
    def test_to_dict(self):
        """Serializes to dict."""
        record = PacketRecord(
            packet_id="pkt_123",
            packet_type="OBSERVATION",
            source_layer="6",
            timestamp=datetime.now(),
            payload={"data": "test"},
            correlation_id="cid_456",
        )
        
        d = record.to_dict()
        assert d["packet_id"] == "pkt_123"
        assert d["packet_type"] == "OBSERVATION"
    
    def test_round_trip(self):
        """Serializes and deserializes."""
        original = PacketRecord(
            packet_id="pkt_123",
            packet_type="DECISION",
            source_layer="5",
            timestamp=datetime.now(),
            payload={"outcome": "ACT"},
            correlation_id="cid_456",
        )
        
        d = original.to_dict()
        restored = PacketRecord.from_dict(d)
        
        assert restored.packet_id == original.packet_id
        assert restored.packet_type == original.packet_type
        assert restored.payload == original.payload


class TestStepRecord:
    """Tests for StepRecord."""
    
    def test_duration_calculation(self):
        """Calculates duration from timestamps."""
        start = datetime.now()
        end = start + timedelta(seconds=5)
        
        record = StepRecord(
            step_id="step_1",
            sequence_number=0,
            layer="5",
            fsm_state="S3_DECIDE",
            packet_type="DECISION",
            started_at=start,
            completed_at=end,
            success=True,
        )
        
        assert record.duration_seconds >= 4.9
        assert record.duration_seconds <= 5.1
    
    def test_to_dict(self):
        """Serializes to dict."""
        record = StepRecord(
            step_id="step_1",
            sequence_number=0,
            layer="5",
            fsm_state="S3_DECIDE",
            packet_type="DECISION",
            started_at=datetime.now(),
            completed_at=datetime.now(),
            success=True,
            packets_emitted=["pkt_1", "pkt_2"],
        )
        
        d = record.to_dict()
        assert d["step_id"] == "step_1"
        assert d["layer"] == "5"
        assert len(d["packets_emitted"]) == 2
    
    def test_round_trip(self):
        """Serializes and deserializes."""
        original = StepRecord(
            step_id="step_1",
            sequence_number=0,
            layer="5",
            fsm_state="S3_DECIDE",
            packet_type="DECISION",
            started_at=datetime.now(),
            completed_at=datetime.now(),
            success=True,
            error="test error",
            raw_llm_response="test response",
            token_usage={"prompt": 10, "completion": 20},
        )
        
        d = original.to_dict()
        restored = StepRecord.from_dict(d)
        
        assert restored.step_id == original.step_id
        assert restored.success == original.success
        assert restored.error == original.error
        assert restored.token_usage == original.token_usage


class TestEpisodeRecord:
    """Tests for EpisodeRecord."""
    
    @pytest.fixture
    def sample_record(self):
        return EpisodeRecord(
            correlation_id=uuid4(),
            template_id="TEMPLATE_A",
            started_at=datetime.now(),
            success=True,
            stakes_level="LOW",
            quality_tier="PAR",
        )
    
    def test_to_json(self, sample_record):
        """Serializes to JSON."""
        json_str = sample_record.to_json()
        assert "TEMPLATE_A" in json_str
        assert "correlation_id" in json_str
    
    def test_from_json(self, sample_record):
        """Deserializes from JSON."""
        json_str = sample_record.to_json()
        restored = EpisodeRecord.from_json(json_str)
        
        assert restored.correlation_id == sample_record.correlation_id
        assert restored.template_id == sample_record.template_id
    
    def test_step_count(self, sample_record):
        """Counts steps."""
        assert sample_record.step_count == 0
        
        sample_record.steps.append(StepRecord(
            step_id="s1",
            sequence_number=0,
            layer="5",
            fsm_state="S3",
            packet_type="DECISION",
            started_at=datetime.now(),
            completed_at=datetime.now(),
            success=True,
        ))
        
        assert sample_record.step_count == 1
    
    def test_packet_count(self, sample_record):
        """Counts packets."""
        assert sample_record.packet_count == 0
        
        sample_record.packets.append(PacketRecord(
            packet_id="pkt_1",
            packet_type="OBSERVATION",
            source_layer="6",
            timestamp=datetime.now(),
            payload={},
            correlation_id=str(sample_record.correlation_id),
        ))
        
        assert sample_record.packet_count == 1
    
    def test_duration_seconds_incomplete(self, sample_record):
        """Duration is zero when incomplete."""
        sample_record.completed_at = None
        assert sample_record.duration_seconds == 0.0
    
    def test_duration_seconds_complete(self, sample_record):
        """Duration calculated when complete."""
        sample_record.completed_at = sample_record.started_at + timedelta(seconds=10)
        assert sample_record.duration_seconds >= 9.9
        assert sample_record.duration_seconds <= 10.1
    
    def test_full_round_trip(self):
        """Complete serialization round trip."""
        original = EpisodeRecord(
            correlation_id=uuid4(),
            template_id="TEMPLATE_B",
            campaign_id="campaign_123",
            started_at=datetime.now(),
            completed_at=datetime.now() + timedelta(seconds=5),
            success=True,
            final_step="step_final",
            errors=["error1", "error2"],
            stakes_level="HIGH",
            quality_tier="SUPERB",
            tools_state="TOOLS_OK",
            budget_allocated={"tokens": 1000},
            budget_consumed={"tokens": 500},
            evidence_refs=[{"ref_id": "ev_1"}],
            assumptions=[{"text": "assumption"}],
            contradictions=["contra_1"],
        )
        
        # Add a step
        original.steps.append(StepRecord(
            step_id="s1",
            sequence_number=0,
            layer="5",
            fsm_state="S3",
            packet_type="DECISION",
            started_at=original.started_at,
            completed_at=original.completed_at,
            success=True,
        ))
        
        # Add a packet
        original.packets.append(PacketRecord(
            packet_id="pkt_1",
            packet_type="OBSERVATION",
            source_layer="6",
            timestamp=original.started_at,
            payload={"data": "test"},
            correlation_id=str(original.correlation_id),
        ))
        
        # Serialize and deserialize
        json_str = original.to_json()
        restored = EpisodeRecord.from_json(json_str)
        
        assert restored.correlation_id == original.correlation_id
        assert restored.template_id == original.template_id
        assert restored.campaign_id == original.campaign_id
        assert restored.success == original.success
        assert restored.step_count == 1
        assert restored.packet_count == 1
        assert len(restored.errors) == 2
        assert restored.budget_consumed["tokens"] == 500
