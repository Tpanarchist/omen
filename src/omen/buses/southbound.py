"""
Southbound Bus — Directives from higher to lower layers.

Carries: intent, constraints, stakes, quality tier, budgets, DoD.
Direction: L1 → L2 → L3 → L4 → L5 → L6

Spec: OMEN.md §7.2
"""

from omen.vocabulary import LayerSource
from omen.buses.base import Bus
from omen.buses.northbound import LAYER_ORDER


class SouthboundBus(Bus):
    """
    Southbound bus for directives traveling down the layer hierarchy.
    
    Messages flow from higher layers (L1) to lower layers (L6).
    Each layer receives directives from layers above it.
    """
    
    def direction(self) -> str:
        return "southbound"
    
    def can_route(self, from_layer: LayerSource, to_layer: LayerSource) -> bool:
        """
        Check if southbound routing is valid.
        
        Valid when target is lower in hierarchy (higher number) than source.
        Integrity can send to any layer.
        """
        if from_layer == LayerSource.INTEGRITY:
            return True  # Integrity can direct any layer
        
        from_order = LAYER_ORDER.get(from_layer, 99)
        to_order = LAYER_ORDER.get(to_layer, 99)
        
        # Southbound: messages go DOWN (to higher-numbered layers)
        return to_order > from_order


def create_southbound_bus() -> SouthboundBus:
    """Factory for southbound bus."""
    return SouthboundBus()
