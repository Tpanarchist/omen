"""
ObservationPacket — Sensory data entering the cognitive system.

Observations flow northbound from Layer 6 (Task Prosecution) or directly
from the sensorium. They carry raw or processed data about external reality.

Spec: OMEN.md §9.3, §5.1, §7.1
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from omen.vocabulary import PacketType, LayerSource, EvidenceRefType
from omen.schemas.header import PacketHeader
from omen.schemas.mcp import MCP


class ObservationSource(BaseModel):
    """
    Where the observation came from.
    
    Spec: OMEN.md §5.1 "Sensorium"
    """
    source_type: str = Field(
        ...,
        description="Category of source (e.g., 'esi_api', 'user_input', 'tool_output', 'sensor')"
    )
    source_id: str = Field(
        ...,
        description="Specific identifier for the source (e.g., API endpoint, sensor ID)"
    )
    query_params: dict[str, Any] | None = Field(
        default=None,
        description="Parameters used to obtain this observation"
    )


class ObservationPayload(BaseModel):
    """
    Payload for ObservationPacket.
    
    Contains the actual observed data and metadata about its capture.
    
    Spec: OMEN.md §9.3 "ObservationPacket"
    """
    source: ObservationSource = Field(
        ...,
        description="Where this observation came from"
    )
    
    observation_type: str = Field(
        ...,
        description="Category of observation (e.g., 'character_state', 'market_data', 'wallet_delta')"
    )
    
    observed_at: datetime = Field(
        ...,
        description="When the observation was captured (may differ from packet created_at)"
    )
    
    content: dict[str, Any] = Field(
        ...,
        description="The actual observed data (structure varies by observation_type)"
    )
    
    raw_ref: str | None = Field(
        default=None,
        description="Reference/hash to raw data if stored separately"
    )
    
    content_hash: str | None = Field(
        default=None,
        description="Hash of content for integrity verification"
    )


class ObservationPacket(BaseModel):
    """
    Complete ObservationPacket.
    
    Carries sensory data from the sensorium into the cognitive system.
    Flows northbound, typically originating from Layer 6.
    
    Spec: OMEN.md §9.3
    """
    header: PacketHeader = Field(
        ...,
        description="Packet identification and routing"
    )
    
    mcp: MCP = Field(
        ...,
        description="Mandatory Compliance Payload"
    )
    
    payload: ObservationPayload = Field(
        ...,
        description="Observation-specific content"
    )
    
    def __init__(self, **data):
        # Ensure packet_type is correct
        if "header" in data and isinstance(data["header"], dict):
            data["header"]["packet_type"] = PacketType.OBSERVATION.value
        super().__init__(**data)
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "header": {
                        "packet_type": "ObservationPacket",
                        "created_at": "2025-12-21T11:30:00Z",
                        "layer_source": "6",
                        "correlation_id": "77a88b99-c0d1-e2f3-4567-890abcdef012"
                    },
                    "mcp": {
                        "intent": {"summary": "Report character location", "scope": "character_state"},
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
                            "definition_of_done": {"text": "Location recorded", "checks": []},
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
                                "ref_id": "esi_location_12345",
                                "timestamp": "2025-12-21T11:30:00Z",
                                "reliability_score": 0.99
                            }],
                            "evidence_absent_reason": None
                        },
                        "routing": {"task_class": "LOOKUP", "tools_state": "tools_ok"}
                    },
                    "payload": {
                        "source": {
                            "source_type": "esi_api",
                            "source_id": "/characters/{character_id}/location/",
                            "query_params": {"character_id": 12345}
                        },
                        "observation_type": "character_location",
                        "observed_at": "2025-12-21T11:30:00Z",
                        "content": {"solar_system_id": 30000142, "station_id": 60003760},
                        "raw_ref": "esi_resp_abc123",
                        "content_hash": "sha256:abcdef1234567890"
                    }
                }
            ]
        }
    }
