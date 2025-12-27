"""
Buses — Inter-layer communication infrastructure.

- NorthboundBus: telemetry up (L6→L1)
- SouthboundBus: directives down (L1→L6)

Spec: OMEN.md §7
"""

from omen.buses.base import Bus, BusMessage, DeliveryFailure
from omen.buses.northbound import NorthboundBus, create_northbound_bus, LAYER_ORDER
from omen.buses.southbound import SouthboundBus, create_southbound_bus

__all__ = [
    "Bus",
    "BusMessage",
    "DeliveryFailure",
    "NorthboundBus",
    "create_northbound_bus",
    "SouthboundBus",
    "create_southbound_bus",
    "LAYER_ORDER",
]
