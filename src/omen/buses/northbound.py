"""
Northbound Bus — Telemetry from lower to higher layers.

Carries: observations, results, belief updates, contradictions, budget burn.
Direction: L6 → L5 → L4 → L3 → L2 → L1

Spec: OMEN.md §7.1
"""

from omen.vocabulary import LayerSource
from omen.buses.base import Bus


# Layer ordering for northbound (lower number = higher in hierarchy)
LAYER_ORDER = {
    LayerSource.LAYER_6: 6,
    LayerSource.LAYER_5: 5,
    LayerSource.LAYER_4: 4,
    LayerSource.LAYER_3: 3,
    LayerSource.LAYER_2: 2,
    LayerSource.LAYER_1: 1,
    LayerSource.INTEGRITY: 0,  # Integrity sees everything
}


class NorthboundBus(Bus):
    """
    Northbound bus for telemetry traveling up the layer hierarchy.
    
    Messages flow from lower layers (L6) to higher layers (L1).
    Each layer can see telemetry from layers below it.
    """
    
    def direction(self) -> str:
        return "northbound"
    
    def can_route(self, from_layer: LayerSource, to_layer: LayerSource) -> bool:
        """
        Check if northbound routing is valid.
        
        Valid when target is higher in hierarchy (lower number) than source.
        Integrity can receive from any layer.
        """
        if to_layer == LayerSource.INTEGRITY:
            return True  # Integrity monitors all
        
        from_order = LAYER_ORDER.get(from_layer, 99)
        to_order = LAYER_ORDER.get(to_layer, 99)
        
        # Northbound: messages go UP (to lower-numbered layers)
        return to_order < from_order


def create_northbound_bus() -> NorthboundBus:
    """Factory for northbound bus."""
    return NorthboundBus()
