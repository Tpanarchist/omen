"""
Tests for TaskResultPacket schema.

Validates structure matches OMEN.md §9.3, §7.1, §10.4.
"""

import json
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from omen.schemas import TaskResultPacket, TaskResultPayload
from omen.schemas.packets.task_result import ToolCallRecord, ResourceUsage
from omen.vocabulary import PacketType, LayerSource, TaskResultStatus


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def valid_tool_call_record() -> dict:
    return {
        "tool_id": "intel_api",
        "call_timestamp": "2025-12-21T11:33:05Z",
        "parameters": {"system_id": 30000142},
        "duration_ms": 450,
        "success": True,
        "output_ref": "output_001"
    }


@pytest.fixture
def valid_resource_usage() -> dict:
    return {
        "tool_calls_made": 1,
        "time_elapsed_seconds": 0.5,
        "tokens_consumed": 25
    }


@pytest.fixture
def valid_result_payload_success(valid_tool_call_record, valid_resource_usage) -> dict:
    return {
        "result_id": "res_001",
        "directive_id": "dir_001",
        "status": "SUCCESS",
        "status_reason": "Task completed successfully",
        "output": {"threat_level": "LOW"},
        "output_type": "threat_assessment",
        "tool_calls": [valid_tool_call_record],
        "resource_usage": valid_resource_usage,
        "execution_started_at": "2025-12-21T11:33:00Z",
        "execution_completed_at": "2025-12-21T11:33:15Z"
    }


@pytest.fixture
def valid_result_payload_failure(valid_resource_usage) -> dict:
    return {
        "result_id": "res_002",
        "directive_id": "dir_002",
        "status": "FAILURE",
        "status_reason": "API returned error",
        "error_code": "API_TIMEOUT",
        "error_details": "Request timed out after 30 seconds",
        "tool_calls": [],
        "resource_usage": valid_resource_usage,
        "execution_started_at": "2025-12-21T11:33:00Z",
        "execution_completed_at": "2025-12-21T11:33:30Z"
    }


@pytest.fixture
def valid_header() -> dict:
    return {
        "packet_type": "TaskResultPacket",
        "created_at": "2025-12-21T11:33:15Z",
        "layer_source": "6",
        "correlation_id": str(uuid4())
    }


@pytest.fixture
def valid_mcp() -> dict:
    return {
        "intent": {"summary": "Report result", "scope": "execution"},
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
            "definition_of_done": {"text": "Result reported", "checks": []},
            "verification_requirement": "OPTIONAL"
        },
        "budgets": {
            "token_budget": 50,
            "tool_call_budget": 0,
            "time_budget_seconds": 5,
            "risk_budget": {"envelope": "minimal", "max_loss": 0}
        },
        "epistemics": {
            "status": "OBSERVED",
            "confidence": 0.99,
            "calibration_note": "Direct execution result",
            "freshness_class": "REALTIME",
            "stale_if_older_than_seconds": 60,
            "assumptions": []
        },
        "evidence": {
            "evidence_refs": [{
                "ref_type": "tool_output",
                "ref_id": "output_001",
                "timestamp": "2025-12-21T11:33:10Z"
            }],
            "evidence_absent_reason": None
        },
        "routing": {"task_class": "LOOKUP", "tools_state": "tools_ok"}
    }


# =============================================================================
# TOOL CALL RECORD TESTS
# =============================================================================

class TestToolCallRecord:
    """Tests for ToolCallRecord structure."""

    def test_valid_record(self, valid_tool_call_record):
        record = ToolCallRecord(**valid_tool_call_record)
        assert record.tool_id == "intel_api"
        assert record.success is True
        assert record.duration_ms == 450

    def test_record_minimal(self):
        record = ToolCallRecord(
            tool_id="test",
            call_timestamp="2025-01-01T00:00:00Z",
            success=True
        )
        assert record.duration_ms is None
        assert record.error_message is None

    def test_record_failed_with_error(self):
        record = ToolCallRecord(
            tool_id="test",
            call_timestamp="2025-01-01T00:00:00Z",
            success=False,
            error_message="Connection refused"
        )
        assert record.success is False
        assert record.error_message == "Connection refused"


# =============================================================================
# RESOURCE USAGE TESTS
# =============================================================================

class TestResourceUsage:
    """Tests for ResourceUsage structure."""

    def test_valid_usage(self, valid_resource_usage):
        usage = ResourceUsage(**valid_resource_usage)
        assert usage.tool_calls_made == 1
        assert usage.time_elapsed_seconds == 0.5

    def test_usage_minimal(self):
        usage = ResourceUsage(tool_calls_made=0, time_elapsed_seconds=0.1)
        assert usage.tokens_consumed is None

    def test_usage_no_negative_values(self):
        with pytest.raises(ValidationError):
            ResourceUsage(tool_calls_made=-1, time_elapsed_seconds=0.1)


# =============================================================================
# RESULT PAYLOAD TESTS
# =============================================================================

class TestTaskResultPayload:
    """Tests for TaskResultPayload structure."""

    def test_valid_success_payload(self, valid_result_payload_success):
        payload = TaskResultPayload(**valid_result_payload_success)
        assert payload.status == TaskResultStatus.SUCCESS
        assert payload.output is not None

    def test_valid_failure_payload(self, valid_result_payload_failure):
        payload = TaskResultPayload(**valid_result_payload_failure)
        assert payload.status == TaskResultStatus.FAILURE
        assert payload.error_code == "API_TIMEOUT"

    def test_cancelled_status(self, valid_resource_usage):
        payload = TaskResultPayload(
            result_id="res_cancel",
            directive_id="dir_cancel",
            status="CANCELLED",
            status_reason="User requested cancellation",
            resource_usage=valid_resource_usage,
            execution_started_at="2025-01-01T00:00:00Z",
            execution_completed_at="2025-01-01T00:00:05Z"
        )
        assert payload.status == TaskResultStatus.CANCELLED

    def test_all_result_statuses(self, valid_resource_usage):
        for status in TaskResultStatus:
            payload_data = {
                "result_id": f"res_{status.value.lower()}",
                "directive_id": "dir_test",
                "status": status.value,
                "status_reason": f"Status is {status.value}",
                "resource_usage": valid_resource_usage,
                "execution_started_at": "2025-01-01T00:00:00Z",
                "execution_completed_at": "2025-01-01T00:00:01Z"
            }
            if status == TaskResultStatus.FAILURE:
                payload_data["error_code"] = "TEST_ERROR"
            payload = TaskResultPayload(**payload_data)
            assert payload.status == status

    def test_payload_tracks_directive_id(self, valid_result_payload_success):
        payload = TaskResultPayload(**valid_result_payload_success)
        assert payload.directive_id == "dir_001"

    def test_payload_with_observations(self, valid_result_payload_success):
        obs_id = uuid4()
        valid_result_payload_success["observations_generated"] = [obs_id]
        payload = TaskResultPayload(**valid_result_payload_success)
        assert len(payload.observations_generated) == 1


# =============================================================================
# COMPLETE PACKET TESTS
# =============================================================================

class TestTaskResultPacket:
    """Tests for complete TaskResultPacket."""

    def test_valid_success_packet(self, valid_header, valid_mcp, valid_result_payload_success):
        packet = TaskResultPacket(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_result_payload_success
        )
        assert packet.header.packet_type == PacketType.TASK_RESULT
        assert packet.payload.status == TaskResultStatus.SUCCESS

    def test_valid_failure_packet(self, valid_header, valid_mcp, valid_result_payload_failure):
        packet = TaskResultPacket(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_result_payload_failure
        )
        assert packet.payload.status == TaskResultStatus.FAILURE

    def test_failure_requires_error_info(self, valid_header, valid_mcp, valid_resource_usage):
        """FAILURE status must have error_code or error_details."""
        payload = {
            "result_id": "res_fail",
            "directive_id": "dir_fail",
            "status": "FAILURE",
            "status_reason": "Something went wrong",
            # No error_code or error_details
            "resource_usage": valid_resource_usage,
            "execution_started_at": "2025-01-01T00:00:00Z",
            "execution_completed_at": "2025-01-01T00:00:01Z"
        }
        with pytest.raises(ValidationError) as exc_info:
            TaskResultPacket(header=valid_header, mcp=valid_mcp, payload=payload)
        assert "error" in str(exc_info.value).lower()

    def test_packet_enforces_packet_type(self, valid_header, valid_mcp, valid_result_payload_success):
        valid_header["packet_type"] = "DecisionPacket"
        packet = TaskResultPacket(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_result_payload_success
        )
        assert packet.header.packet_type == PacketType.TASK_RESULT

    def test_packet_from_layer_6(self, valid_header, valid_mcp, valid_result_payload_success):
        """Results come from Layer 6 (Task Prosecution)."""
        packet = TaskResultPacket(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_result_payload_success
        )
        assert packet.header.layer_source == LayerSource.LAYER_6

    def test_packet_serialization(self, valid_header, valid_mcp, valid_result_payload_success):
        packet = TaskResultPacket(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_result_payload_success
        )
        json_str = packet.model_dump_json()
        parsed = json.loads(json_str)
        assert "result_id" in parsed["payload"]
        assert "directive_id" in parsed["payload"]
        assert "resource_usage" in parsed["payload"]

    def test_packet_roundtrip(self, valid_header, valid_mcp, valid_result_payload_success):
        packet1 = TaskResultPacket(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_result_payload_success
        )
        json_str = packet1.model_dump_json()
        packet2 = TaskResultPacket.model_validate_json(json_str)
        assert packet1.payload.result_id == packet2.payload.result_id
        assert packet1.payload.status == packet2.payload.status


class TestTaskClosure:
    """Tests for task closure semantics per §10.4."""

    def test_result_references_directive(self, valid_header, valid_mcp, valid_result_payload_success):
        """Result must reference the directive it closes."""
        packet = TaskResultPacket(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_result_payload_success
        )
        assert packet.payload.directive_id is not None
        assert packet.payload.directive_id == "dir_001"

    def test_result_has_timestamps(self, valid_header, valid_mcp, valid_result_payload_success):
        """Result tracks execution timing."""
        packet = TaskResultPacket(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_result_payload_success
        )
        assert packet.payload.execution_started_at is not None
        assert packet.payload.execution_completed_at is not None

    def test_result_tracks_resource_usage(self, valid_header, valid_mcp, valid_result_payload_success):
        """Result reports resource consumption."""
        packet = TaskResultPacket(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_result_payload_success
        )
        assert packet.payload.resource_usage.tool_calls_made >= 0
