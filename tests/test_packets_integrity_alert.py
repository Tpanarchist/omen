"""
Tests for IntegrityAlertPacket schema.

Validates structure matches OMEN.md §9.3, §12, §13.
"""

import json
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from omen.schemas import IntegrityAlertPacket, IntegrityAlertPayload
from omen.schemas.packets.integrity_alert import AffectedComponent, RecommendedAction
from omen.vocabulary import PacketType, LayerSource


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def valid_affected_component() -> dict:
    return {
        "component_type": "layer",
        "component_id": "layer_2",
        "status": "degraded",
        "details": {"contradiction_rate": 0.15}
    }


@pytest.fixture
def valid_recommended_action() -> dict:
    return {
        "action_id": "safe_mode",
        "action_type": "safe_mode",
        "description": "Enter read-only safe mode",
        "auto_executable": True,
        "requires_approval": True,
        "target_component": "layer_2"
    }


@pytest.fixture
def valid_alert_payload(valid_affected_component, valid_recommended_action) -> dict:
    return {
        "alert_id": "alert_001",
        "alert_type": "drift",
        "severity": "WARNING",
        "summary": "Elevated contradiction rate detected",
        "detected_at": "2025-12-21T11:39:55Z",
        "detection_method": "contradiction_rate_monitor",
        "affected_components": [valid_affected_component],
        "metrics": {"contradiction_rate": 0.15, "threshold": 0.10},
        "threshold_violated": "contradiction_rate > 0.10",
        "recommended_actions": [valid_recommended_action],
        "requires_immediate_attention": False
    }


@pytest.fixture
def valid_header() -> dict:
    return {
        "packet_type": "IntegrityAlertPacket",
        "created_at": "2025-12-21T11:40:00Z",
        "layer_source": "Integrity",
        "correlation_id": str(uuid4())
    }


@pytest.fixture
def valid_mcp() -> dict:
    return {
        "intent": {"summary": "Report system issue", "scope": "system_health"},
        "stakes": {
            "impact": "MEDIUM",
            "irreversibility": "REVERSIBLE",
            "uncertainty": "LOW",
            "adversariality": "BENIGN",
            "stakes_level": "MEDIUM"
        },
        "quality": {
            "quality_tier": "PAR",
            "satisficing_mode": False,
            "definition_of_done": {"text": "Alert delivered", "checks": []},
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
            "confidence": 0.95,
            "calibration_note": "System self-observation",
            "freshness_class": "REALTIME",
            "stale_if_older_than_seconds": 60,
            "assumptions": []
        },
        "evidence": {
            "evidence_refs": [],
            "evidence_absent_reason": "System monitoring"
        },
        "routing": {"task_class": "CREATE", "tools_state": "tools_ok"}
    }


# =============================================================================
# AFFECTED COMPONENT TESTS
# =============================================================================

class TestAffectedComponent:
    """Tests for AffectedComponent structure."""

    def test_valid_component(self, valid_affected_component):
        component = AffectedComponent(**valid_affected_component)
        assert component.component_type == "layer"
        assert component.component_id == "layer_2"

    def test_component_minimal(self):
        component = AffectedComponent(
            component_type="tool",
            component_id="esi_api",
            status="offline"
        )
        assert component.details is None

    def test_component_types(self):
        for comp_type in ["layer", "bus", "tool", "model"]:
            component = AffectedComponent(
                component_type=comp_type,
                component_id="test",
                status="degraded"
            )
            assert component.component_type == comp_type


# =============================================================================
# RECOMMENDED ACTION TESTS
# =============================================================================

class TestRecommendedAction:
    """Tests for RecommendedAction structure."""

    def test_valid_action(self, valid_recommended_action):
        action = RecommendedAction(**valid_recommended_action)
        assert action.action_id == "safe_mode"
        assert action.auto_executable is True

    def test_action_minimal(self):
        action = RecommendedAction(
            action_id="act",
            action_type="restart",
            description="Restart the component"
        )
        assert action.auto_executable is False
        assert action.requires_approval is True

    def test_action_types(self):
        for action_type in ["restart", "rollback", "safe_mode", "revoke_token"]:
            action = RecommendedAction(
                action_id="test",
                action_type=action_type,
                description=f"Execute {action_type}"
            )
            assert action.action_type == action_type


# =============================================================================
# INTEGRITY ALERT PAYLOAD TESTS
# =============================================================================

class TestIntegrityAlertPayload:
    """Tests for IntegrityAlertPayload structure."""

    def test_valid_payload(self, valid_alert_payload):
        payload = IntegrityAlertPayload(**valid_alert_payload)
        assert payload.alert_id == "alert_001"
        assert payload.severity == "WARNING"

    def test_payload_severity_levels(self, valid_alert_payload):
        for severity in ["INFO", "WARNING", "ERROR", "CRITICAL"]:
            valid_alert_payload["severity"] = severity
            payload = IntegrityAlertPayload(**valid_alert_payload)
            assert payload.severity == severity

    def test_payload_alert_types(self, valid_alert_payload):
        for alert_type in ["drift", "budget_exceeded", "tool_failure", "contradiction"]:
            valid_alert_payload["alert_type"] = alert_type
            payload = IntegrityAlertPayload(**valid_alert_payload)
            assert payload.alert_type == alert_type

    def test_payload_minimal(self):
        payload = IntegrityAlertPayload(
            alert_id="alert",
            alert_type="info",
            severity="INFO",
            summary="System status normal",
            detected_at="2025-01-01T00:00:00Z",
            detection_method="periodic_check"
        )
        assert payload.affected_components == []
        assert payload.recommended_actions == []

    def test_payload_with_auto_action(self, valid_alert_payload):
        valid_alert_payload["auto_action_taken"] = "Increased monitoring frequency"
        payload = IntegrityAlertPayload(**valid_alert_payload)
        assert payload.auto_action_taken is not None

    def test_payload_with_related_ids(self, valid_alert_payload):
        ep_id = str(uuid4())
        pkt_id = str(uuid4())
        valid_alert_payload["related_episode_id"] = ep_id
        valid_alert_payload["related_packet_ids"] = [pkt_id]
        payload = IntegrityAlertPayload(**valid_alert_payload)
        assert len(payload.related_packet_ids) == 1


# =============================================================================
# COMPLETE PACKET TESTS
# =============================================================================

class TestIntegrityAlertPacket:
    """Tests for complete IntegrityAlertPacket."""

    def test_valid_packet(self, valid_header, valid_mcp, valid_alert_payload):
        packet = IntegrityAlertPacket(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_alert_payload
        )
        assert packet.header.packet_type == PacketType.INTEGRITY_ALERT
        assert packet.payload.alert_id == "alert_001"

    def test_packet_enforces_packet_type(self, valid_header, valid_mcp, valid_alert_payload):
        valid_header["packet_type"] = "DecisionPacket"
        packet = IntegrityAlertPacket(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_alert_payload
        )
        assert packet.header.packet_type == PacketType.INTEGRITY_ALERT

    def test_packet_from_integrity_overlay(self, valid_header, valid_mcp, valid_alert_payload):
        """Alerts come from Integrity overlay."""
        packet = IntegrityAlertPacket(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_alert_payload
        )
        assert packet.header.layer_source == LayerSource.INTEGRITY

    def test_packet_serialization(self, valid_header, valid_mcp, valid_alert_payload):
        packet = IntegrityAlertPacket(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_alert_payload
        )
        json_str = packet.model_dump_json()
        parsed = json.loads(json_str)
        assert "alert_id" in parsed["payload"]
        assert "severity" in parsed["payload"]

    def test_packet_roundtrip(self, valid_header, valid_mcp, valid_alert_payload):
        packet1 = IntegrityAlertPacket(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_alert_payload
        )
        json_str = packet1.model_dump_json()
        packet2 = IntegrityAlertPacket.model_validate_json(json_str)
        assert packet1.payload.alert_id == packet2.payload.alert_id
        assert packet1.payload.severity == packet2.payload.severity


class TestIntegrityFailureModes:
    """Tests for failure modes per §13."""

    def test_drift_detection(self, valid_header, valid_mcp, valid_alert_payload):
        """Drift detection per §13."""
        valid_alert_payload["alert_type"] = "drift"
        valid_alert_payload["metrics"] = {"contradiction_rate": 0.15}
        packet = IntegrityAlertPacket(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_alert_payload
        )
        assert packet.payload.alert_type == "drift"

    def test_budget_exceeded(self, valid_header, valid_mcp, valid_alert_payload):
        valid_alert_payload["alert_type"] = "budget_exceeded"
        valid_alert_payload["summary"] = "Token budget exceeded"
        valid_alert_payload["threshold_violated"] = "tokens > budget"
        packet = IntegrityAlertPacket(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_alert_payload
        )
        assert packet.payload.alert_type == "budget_exceeded"

    def test_tool_failure(self, valid_header, valid_mcp, valid_alert_payload):
        valid_alert_payload["alert_type"] = "tool_failure"
        valid_alert_payload["summary"] = "ESI API unresponsive"
        valid_alert_payload["affected_components"] = [{
            "component_type": "tool",
            "component_id": "esi_api",
            "status": "offline"
        }]
        packet = IntegrityAlertPacket(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_alert_payload
        )
        assert packet.payload.affected_components[0].status == "offline"

    def test_requires_immediate_attention(self, valid_header, valid_mcp, valid_alert_payload):
        valid_alert_payload["severity"] = "CRITICAL"
        valid_alert_payload["requires_immediate_attention"] = True
        packet = IntegrityAlertPacket(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_alert_payload
        )
        assert packet.payload.requires_immediate_attention is True
