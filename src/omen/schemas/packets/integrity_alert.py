"""
IntegrityAlertPacket — System health alerts from the Integrity overlay.

Integrity alerts report issues detected by the out-of-band monitoring system.
They can trigger safe modes, token revocations, or component restarts.

Spec: OMEN.md §9.3, §12, §13
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from omen.vocabulary import PacketType
from omen.schemas.header import PacketHeader
from omen.schemas.mcp import MCP


class AlertSeverity(str):
    """
    Severity levels for integrity alerts.
    
    Not an enum to allow extension, but canonical values defined.
    """
    INFO = "INFO"           # Informational, no action needed
    WARNING = "WARNING"     # Attention needed, not critical
    ERROR = "ERROR"         # Problem requiring intervention
    CRITICAL = "CRITICAL"   # Immediate action required


class AffectedComponent(BaseModel):
    """
    A component affected by the alert condition.
    """
    component_type: str = Field(
        ...,
        description="Type of component (e.g., 'layer', 'bus', 'tool', 'model')"
    )
    
    component_id: str = Field(
        ...,
        description="Identifier of the affected component"
    )
    
    status: str = Field(
        ...,
        description="Current status of the component"
    )
    
    details: dict[str, Any] | None = Field(
        default=None,
        description="Additional details about the component state"
    )


class RecommendedAction(BaseModel):
    """
    An action recommended by Integrity overlay.
    """
    action_id: str = Field(
        ...,
        description="Identifier for this action"
    )
    
    action_type: str = Field(
        ...,
        description="Type of action (e.g., 'restart', 'rollback', 'safe_mode', 'revoke_token')"
    )
    
    description: str = Field(
        ...,
        description="What the action would do"
    )
    
    auto_executable: bool = Field(
        default=False,
        description="Whether Integrity can execute this automatically"
    )
    
    requires_approval: bool = Field(
        default=True,
        description="Whether human approval is needed"
    )
    
    target_component: str | None = Field(
        default=None,
        description="Component this action targets"
    )


class IntegrityAlertPayload(BaseModel):
    """
    Payload for IntegrityAlertPacket.
    
    Reports system health issues detected by the Integrity overlay.
    
    Spec: OMEN.md §9.3 "IntegrityAlertPacket", §12, §13
    """
    alert_id: str = Field(
        ...,
        description="Unique identifier for this alert"
    )
    
    alert_type: str = Field(
        ...,
        description="Category of alert (e.g., 'drift', 'budget_exceeded', 'tool_failure', 'contradiction')"
    )
    
    severity: str = Field(
        ...,
        description="Alert severity (INFO, WARNING, ERROR, CRITICAL)"
    )
    
    summary: str = Field(
        ...,
        description="Human-readable summary of the issue"
    )
    
    detected_at: datetime = Field(
        ...,
        description="When the issue was detected"
    )
    
    detection_method: str = Field(
        ...,
        description="How the issue was detected"
    )
    
    affected_components: list[AffectedComponent] = Field(
        default_factory=list,
        description="Components affected by this issue"
    )
    
    metrics: dict[str, Any] | None = Field(
        default=None,
        description="Relevant metrics (e.g., contradiction_rate, drift_score)"
    )
    
    threshold_violated: str | None = Field(
        default=None,
        description="Which threshold was violated (if applicable)"
    )
    
    recommended_actions: list[RecommendedAction] = Field(
        default_factory=list,
        description="Actions recommended to address the issue"
    )
    
    auto_action_taken: str | None = Field(
        default=None,
        description="If Integrity already took automatic action"
    )
    
    related_episode_id: UUID | None = Field(
        default=None,
        description="Episode related to this alert"
    )
    
    related_packet_ids: list[UUID] = Field(
        default_factory=list,
        description="Packets related to this alert"
    )
    
    requires_immediate_attention: bool = Field(
        default=False,
        description="Whether immediate human attention is needed"
    )


class IntegrityAlertPacket(BaseModel):
    """
    Complete IntegrityAlertPacket.
    
    Reports system health issues from the Integrity overlay.
    Can trigger safe modes, restarts, or escalations.
    
    Spec: OMEN.md §9.3, §12
    """
    header: PacketHeader = Field(
        ...,
        description="Packet identification and routing"
    )
    
    mcp: MCP = Field(
        ...,
        description="Mandatory Compliance Payload"
    )
    
    payload: IntegrityAlertPayload = Field(
        ...,
        description="Alert content"
    )
    
    def __init__(self, **data):
        # Ensure packet_type is correct
        if "header" in data and isinstance(data["header"], dict):
            data["header"]["packet_type"] = PacketType.INTEGRITY_ALERT.value
        super().__init__(**data)
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "header": {
                        "packet_type": "IntegrityAlertPacket",
                        "created_at": "2025-12-21T11:40:00Z",
                        "layer_source": "Integrity",
                        "correlation_id": "00000000-0000-0000-0000-000000000000"
                    },
                    "mcp": {
                        "intent": {"summary": "Report drift detection", "scope": "system_health"},
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
                            "calibration_note": "Direct system observation",
                            "freshness_class": "REALTIME",
                            "stale_if_older_than_seconds": 60,
                            "assumptions": []
                        },
                        "evidence": {
                            "evidence_refs": [],
                            "evidence_absent_reason": "System self-observation"
                        },
                        "routing": {"task_class": "CREATE", "tools_state": "tools_ok"}
                    },
                    "payload": {
                        "alert_id": "alert_drift_001",
                        "alert_type": "drift",
                        "severity": "WARNING",
                        "summary": "Elevated contradiction rate detected in belief updates",
                        "detected_at": "2025-12-21T11:39:55Z",
                        "detection_method": "contradiction_rate_monitor",
                        "affected_components": [
                            {
                                "component_type": "layer",
                                "component_id": "layer_2",
                                "status": "degraded",
                                "details": {"contradiction_rate": 0.15}
                            }
                        ],
                        "metrics": {
                            "contradiction_rate": 0.15,
                            "threshold": 0.10,
                            "window_minutes": 5
                        },
                        "threshold_violated": "contradiction_rate > 0.10",
                        "recommended_actions": [
                            {
                                "action_id": "verify_beliefs",
                                "action_type": "verification",
                                "description": "Re-verify recent beliefs against fresh observations",
                                "auto_executable": True,
                                "requires_approval": False
                            },
                            {
                                "action_id": "safe_mode",
                                "action_type": "safe_mode",
                                "description": "Enter read-only safe mode",
                                "auto_executable": True,
                                "requires_approval": True,
                                "target_component": "layer_2"
                            }
                        ],
                        "requires_immediate_attention": False
                    }
                }
            ]
        }
    }
