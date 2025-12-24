"""
Packet Header — Common fields for all packet types.

Every packet carries this header for identification, routing, and traceability.

Spec: OMEN.md §9.1
"""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from omen.vocabulary import PacketType, LayerSource


class PacketHeader(BaseModel):
    """
    Common header for all packets.
    
    Provides:
    - Identification (packet_id, packet_type)
    - Timing (created_at)
    - Origin (layer_source)
    - Correlation (correlation_id for episode grouping)
    - Chaining (previous_packet_id for sequence)
    - Campaign context (campaign_id for macro grouping)
    
    Spec: OMEN.md §9.1 "Packet header (required)"
    """
    
    packet_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this packet"
    )
    
    packet_type: PacketType = Field(
        ...,
        description="The type of packet (one of 9 canonical types)"
    )
    
    created_at: datetime = Field(
        ...,
        description="When this packet was created (ISO 8601)"
    )
    
    layer_source: LayerSource = Field(
        ...,
        description="Which layer originated this packet (1-6 or Integrity)"
    )
    
    correlation_id: UUID = Field(
        ...,
        description="Episode identifier grouping related packets"
    )
    
    campaign_id: UUID | None = Field(
        default=None,
        description="Optional macro-level campaign grouping"
    )
    
    previous_packet_id: UUID | None = Field(
        default=None,
        description="Optional reference to previous packet in chain"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "packet_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "packet_type": "DecisionPacket",
                    "created_at": "2025-12-21T11:32:00-05:00",
                    "layer_source": "5",
                    "correlation_id": "77a88b99-c0d1-e2f3-4567-890abcdef012",
                    "campaign_id": "deadbeef-cafe-babe-1234-567890abcdef",
                    "previous_packet_id": None
                }
            ]
        }
    }
