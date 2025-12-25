"""
Tests for TaskDirectivePacket schema.

Validates structure matches OMEN.md §9.3, §7.2, §10.4, §11.1.
"""

import json
from uuid import uuid4

import pytest
from pydantic import ValidationError

from omen.schemas import TaskDirectivePacket, TaskDirectivePayload
from omen.schemas.packets.task_directive import ToolSpec, DirectiveConstraints
from omen.vocabulary import PacketType, LayerSource, TaskClass, ToolSafety


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def valid_tool_spec() -> dict:
    return {
        "tool_id": "intel_api",
        "tool_safety": "READ",
        "parameters": {"system_id": 30000142},
        "timeout_seconds": 10
    }


@pytest.fixture
def valid_constraints() -> dict:
    return {
        "max_tool_calls": 2,
        "max_time_seconds": 60,
        "require_authorization_token": False
    }


@pytest.fixture
def valid_directive_payload(valid_tool_spec, valid_constraints) -> dict:
    return {
        "directive_id": "dir_001",
        "task_class": "LOOKUP",
        "task_description": "Query current threat level",
        "instructions": "Call intel API with system_id",
        "tools": [valid_tool_spec],
        "constraints": valid_constraints,
        "success_criteria": "Valid threat data returned"
    }


@pytest.fixture
def valid_header() -> dict:
    return {
        "packet_type": "TaskDirectivePacket",
        "created_at": "2025-12-21T11:33:00Z",
        "layer_source": "5",
        "correlation_id": str(uuid4())
    }


@pytest.fixture
def valid_mcp() -> dict:
    return {
        "intent": {"summary": "Execute task", "scope": "execution"},
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
            "definition_of_done": {"text": "Task complete", "checks": []},
            "verification_requirement": "OPTIONAL"
        },
        "budgets": {
            "token_budget": 100,
            "tool_call_budget": 2,
            "time_budget_seconds": 60,
            "risk_budget": {"envelope": "minimal", "max_loss": 0}
        },
        "epistemics": {
            "status": "DERIVED",
            "confidence": 0.9,
            "calibration_note": "Directive from plan",
            "freshness_class": "REALTIME",
            "stale_if_older_than_seconds": 120,
            "assumptions": []
        },
        "evidence": {
            "evidence_refs": [],
            "evidence_absent_reason": "Directive precedes execution"
        },
        "routing": {"task_class": "LOOKUP", "tools_state": "tools_ok"}
    }


# =============================================================================
# TOOL SPEC TESTS
# =============================================================================

class TestToolSpec:
    """Tests for ToolSpec structure."""

    def test_valid_tool_spec(self, valid_tool_spec):
        spec = ToolSpec(**valid_tool_spec)
        assert spec.tool_id == "intel_api"
        assert spec.tool_safety == ToolSafety.READ

    def test_tool_spec_minimal(self):
        spec = ToolSpec(tool_id="test", tool_safety="READ")
        assert spec.parameters == {}
        assert spec.timeout_seconds is None

    def test_tool_spec_all_safeties(self):
        for safety in ToolSafety:
            spec = ToolSpec(tool_id="test", tool_safety=safety.value)
            assert spec.tool_safety == safety

    def test_tool_spec_timeout_positive(self):
        with pytest.raises(ValidationError):
            ToolSpec(tool_id="test", tool_safety="READ", timeout_seconds=0)


# =============================================================================
# DIRECTIVE CONSTRAINTS TESTS
# =============================================================================

class TestDirectiveConstraints:
    """Tests for DirectiveConstraints structure."""

    def test_valid_constraints(self, valid_constraints):
        constraints = DirectiveConstraints(**valid_constraints)
        assert constraints.max_tool_calls == 2
        assert constraints.max_time_seconds == 60

    def test_constraints_with_whitelist(self, valid_constraints):
        valid_constraints["allowed_tool_ids"] = ["tool_a", "tool_b"]
        constraints = DirectiveConstraints(**valid_constraints)
        assert len(constraints.allowed_tool_ids) == 2

    def test_constraints_with_blacklist(self, valid_constraints):
        valid_constraints["forbidden_tool_ids"] = ["dangerous_tool"]
        constraints = DirectiveConstraints(**valid_constraints)
        assert "dangerous_tool" in constraints.forbidden_tool_ids

    def test_constraints_with_auth_token(self, valid_constraints):
        token_id = uuid4()
        valid_constraints["require_authorization_token"] = True
        valid_constraints["authorization_token_id"] = str(token_id)
        constraints = DirectiveConstraints(**valid_constraints)
        assert constraints.require_authorization_token is True

    def test_constraints_time_positive(self, valid_constraints):
        valid_constraints["max_time_seconds"] = 0
        with pytest.raises(ValidationError):
            DirectiveConstraints(**valid_constraints)


# =============================================================================
# DIRECTIVE PAYLOAD TESTS
# =============================================================================

class TestTaskDirectivePayload:
    """Tests for TaskDirectivePayload structure."""

    def test_valid_payload(self, valid_directive_payload):
        payload = TaskDirectivePayload(**valid_directive_payload)
        assert payload.directive_id == "dir_001"
        assert payload.task_class == TaskClass.LOOKUP

    def test_payload_all_task_classes(self, valid_directive_payload):
        for task_class in TaskClass:
            valid_directive_payload["task_class"] = task_class.value
            payload = TaskDirectivePayload(**valid_directive_payload)
            assert payload.task_class == task_class

    def test_payload_without_tools(self, valid_constraints):
        payload = TaskDirectivePayload(
            directive_id="dir_no_tools",
            task_class="CREATE",
            task_description="Create a plan",
            instructions="Generate plan based on inputs",
            tools=[],
            constraints=valid_constraints,
            success_criteria="Valid plan produced"
        )
        assert len(payload.tools) == 0

    def test_payload_with_verification_link(self, valid_directive_payload):
        valid_directive_payload["parent_verification_target_id"] = "verify_threat"
        payload = TaskDirectivePayload(**valid_directive_payload)
        assert payload.parent_verification_target_id == "verify_threat"


# =============================================================================
# COMPLETE PACKET TESTS
# =============================================================================

class TestTaskDirectivePacket:
    """Tests for complete TaskDirectivePacket."""

    def test_valid_packet(self, valid_header, valid_mcp, valid_directive_payload):
        packet = TaskDirectivePacket(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_directive_payload
        )
        assert packet.header.packet_type == PacketType.TASK_DIRECTIVE
        assert packet.payload.directive_id == "dir_001"

    def test_packet_enforces_packet_type(self, valid_header, valid_mcp, valid_directive_payload):
        valid_header["packet_type"] = "DecisionPacket"
        packet = TaskDirectivePacket(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_directive_payload
        )
        assert packet.header.packet_type == PacketType.TASK_DIRECTIVE

    def test_packet_from_layer_5(self, valid_header, valid_mcp, valid_directive_payload):
        """Directives come from Layer 5 (Cognitive Control)."""
        packet = TaskDirectivePacket(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_directive_payload
        )
        assert packet.header.layer_source == LayerSource.LAYER_5

    def test_write_tools_require_auth_when_flagged(self, valid_header, valid_mcp, valid_constraints):
        """WRITE tools with require_authorization_token need token_id."""
        valid_constraints["require_authorization_token"] = True
        # No authorization_token_id set
        payload = {
            "directive_id": "dir_write",
            "task_class": "CREATE",
            "task_description": "Write data",
            "instructions": "Execute write",
            "tools": [{"tool_id": "write_api", "tool_safety": "WRITE"}],
            "constraints": valid_constraints,
            "success_criteria": "Data written"
        }
        with pytest.raises(ValidationError) as exc_info:
            TaskDirectivePacket(header=valid_header, mcp=valid_mcp, payload=payload)
        assert "authorization_token_id" in str(exc_info.value)

    def test_read_tools_no_auth_required(self, valid_header, valid_mcp, valid_directive_payload):
        """READ tools don't require authorization token."""
        packet = TaskDirectivePacket(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_directive_payload
        )
        assert packet.payload.constraints.require_authorization_token is False

    def test_packet_serialization(self, valid_header, valid_mcp, valid_directive_payload):
        packet = TaskDirectivePacket(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_directive_payload
        )
        json_str = packet.model_dump_json()
        parsed = json.loads(json_str)
        assert "directive_id" in parsed["payload"]
        assert "tools" in parsed["payload"]

    def test_packet_roundtrip(self, valid_header, valid_mcp, valid_directive_payload):
        packet1 = TaskDirectivePacket(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_directive_payload
        )
        json_str = packet1.model_dump_json()
        packet2 = TaskDirectivePacket.model_validate_json(json_str)
        assert packet1.payload.directive_id == packet2.payload.directive_id
        assert len(packet1.payload.tools) == len(packet2.payload.tools)
