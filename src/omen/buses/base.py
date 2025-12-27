"""
Bus Infrastructure — Inter-layer packet routing.

Buses carry packets between ACE layers:
- Northbound: telemetry up (L6→L1)
- Southbound: directives down (L1→L6)

Spec: OMEN.md §7, ACE_Framework.md
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable
from uuid import UUID

from omen.vocabulary import LayerSource, PacketType

logger = logging.getLogger(__name__)


@dataclass
class BusMessage:
    """
    Message wrapper for bus transport.
    
    Wraps a packet with routing metadata.
    """
    packet: Any  # The actual packet (Observation, Decision, etc.)
    source_layer: LayerSource
    target_layer: LayerSource | None  # None = broadcast to all eligible
    correlation_id: UUID
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def packet_type(self) -> PacketType | None:
        """Extract packet type from wrapped packet, or None if not available."""
        try:
            return self.packet.header.packet_type
        except AttributeError:
            return None


@dataclass
class DeliveryFailure:
    """Record of a failed message delivery to a layer."""
    layer: LayerSource
    exception: Exception
    timestamp: datetime = field(default_factory=datetime.now)


class Bus(ABC):
    """
    Abstract base for inter-layer buses.
    
    Handles message routing, filtering, and delivery.
    """
    
    def __init__(self):
        self._subscribers: dict[LayerSource, Callable[[BusMessage], None]] = {}
        self._message_log: list[BusMessage] = []
    
    @abstractmethod
    def direction(self) -> str:
        """Return 'northbound' or 'southbound'."""
        pass
    
    @abstractmethod
    def can_route(self, from_layer: LayerSource, to_layer: LayerSource) -> bool:
        """Check if routing from source to target is valid for this bus."""
        pass
    
    def subscribe(
        self, 
        layer: LayerSource, 
        handler: Callable[[BusMessage], None]
    ) -> None:
        """Subscribe a layer to receive messages."""
        self._subscribers[layer] = handler
    
    def unsubscribe(self, layer: LayerSource) -> None:
        """Unsubscribe a layer."""
        self._subscribers.pop(layer, None)
    
    def publish(
        self, 
        message: BusMessage
    ) -> tuple[list[LayerSource], list[DeliveryFailure]]:
        """
        Publish a message to the bus.
        
        Returns tuple of (delivered_to, failures).
        Failing handlers are logged but don't halt delivery to other layers.
        """
        delivered_to: list[LayerSource] = []
        failures: list[DeliveryFailure] = []
        self._message_log.append(message)
        
        for layer, handler in self._subscribers.items():
            # Check if this layer should receive the message
            if message.target_layer is not None:
                # Targeted message
                if layer != message.target_layer:
                    continue
            
            # Check routing validity
            if not self.can_route(message.source_layer, layer):
                continue
            
            # Deliver with error handling
            try:
                handler(message)
                delivered_to.append(layer)
            except Exception as exc:
                failure = DeliveryFailure(layer=layer, exception=exc)
                failures.append(failure)
                logger.error(
                    f"Failed to deliver message to {layer.name}: {exc}",
                    exc_info=True
                )
        
        return delivered_to, failures
    
    def get_messages(
        self,
        correlation_id: UUID | None = None,
        source_layer: LayerSource | None = None,
        packet_type: PacketType | None = None,
    ) -> list[BusMessage]:
        """Query message log with optional filters."""
        messages = self._message_log
        
        if correlation_id is not None:
            messages = [m for m in messages if m.correlation_id == correlation_id]
        if source_layer is not None:
            messages = [m for m in messages if m.source_layer == source_layer]
        if packet_type is not None:
            messages = [m for m in messages if m.packet_type == packet_type]
        
        return messages
    
    def clear_log(self) -> None:
        """Clear message log."""
        self._message_log.clear()
