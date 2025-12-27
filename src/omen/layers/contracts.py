"""
Layer Contracts — Defines what each ACE layer can receive and emit.

Enforces layer responsibilities per OMEN.md §11.1.
"""

from dataclasses import dataclass

from omen.vocabulary import LayerSource, PacketType


# =============================================================================
# CONTRACT DEFINITIONS
# =============================================================================

@dataclass(frozen=True)
class LayerContract:
    """
    Contract defining a layer's allowed packet interactions.
    
    Immutable to prevent runtime modification.
    """
    layer: LayerSource
    can_emit: frozenset[PacketType]
    can_receive: frozenset[PacketType]
    description: str = ""
    
    def allows_emit(self, packet_type: PacketType) -> bool:
        """Check if this layer can emit the given packet type."""
        return packet_type in self.can_emit
    
    def allows_receive(self, packet_type: PacketType) -> bool:
        """Check if this layer can receive the given packet type."""
        return packet_type in self.can_receive


# =============================================================================
# CANONICAL CONTRACTS (§11.1)
# =============================================================================

# Layer 1: Aspirational — Law, posture, vetoes
# Cannot issue directives; provides constitutional oversight
LAYER_1_CONTRACT = LayerContract(
    layer=LayerSource.LAYER_1,
    description="Aspirational: Law, posture, vetoes. Constitutional oversight.",
    can_emit=frozenset({
        PacketType.INTEGRITY_ALERT,  # Vetoes, constitutional violations
        PacketType.BELIEF_UPDATE,    # Mission/value updates
    }),
    can_receive=frozenset({
        # Receives telemetry from all lower layers
        PacketType.OBSERVATION,
        PacketType.BELIEF_UPDATE,
        PacketType.DECISION,
        PacketType.TASK_RESULT,
        PacketType.ESCALATION,
        PacketType.INTEGRITY_ALERT,
    }),
)

# Layer 2: Global Strategy — Campaign framing, strategy
# Cannot issue write tools
LAYER_2_CONTRACT = LayerContract(
    layer=LayerSource.LAYER_2,
    description="Global Strategy: Campaign framing, strategic direction.",
    can_emit=frozenset({
        PacketType.BELIEF_UPDATE,  # Strategy updates
    }),
    can_receive=frozenset({
        PacketType.OBSERVATION,
        PacketType.BELIEF_UPDATE,
        PacketType.DECISION,
        PacketType.TASK_RESULT,
        PacketType.INTEGRITY_ALERT,
    }),
)

# Layer 3: Agent Model — Capability truth, tools state
# Cannot execute actions
LAYER_3_CONTRACT = LayerContract(
    layer=LayerSource.LAYER_3,
    description="Agent Model: Capability assessment, tools state truth.",
    can_emit=frozenset({
        PacketType.BELIEF_UPDATE,  # Capability assessments
    }),
    can_receive=frozenset({
        PacketType.OBSERVATION,
        PacketType.BELIEF_UPDATE,
        PacketType.TASK_RESULT,
        PacketType.INTEGRITY_ALERT,
    }),
)

# Layer 4: Executive Function — Budgets, DoD, feasibility
# Cannot perform write actions
LAYER_4_CONTRACT = LayerContract(
    layer=LayerSource.LAYER_4,
    description="Executive Function: Budgets, DoD, feasibility planning.",
    can_emit=frozenset({
        PacketType.BELIEF_UPDATE,  # Plans, budgets, DoD
    }),
    can_receive=frozenset({
        PacketType.OBSERVATION,
        PacketType.BELIEF_UPDATE,
        PacketType.DECISION,
        PacketType.VERIFICATION_PLAN,
        PacketType.TASK_RESULT,
        PacketType.INTEGRITY_ALERT,
    }),
)

# Layer 5: Cognitive Control — Orchestration, decisions
# Issues decisions, tokens, directives; cannot execute directly
LAYER_5_CONTRACT = LayerContract(
    layer=LayerSource.LAYER_5,
    description="Cognitive Control: Orchestration, decisions, token issuance.",
    can_emit=frozenset({
        PacketType.DECISION,
        PacketType.VERIFICATION_PLAN,
        PacketType.TOOL_AUTHORIZATION,
        PacketType.TASK_DIRECTIVE,
        PacketType.ESCALATION,
        PacketType.BELIEF_UPDATE,
    }),
    can_receive=frozenset({
        PacketType.OBSERVATION,
        PacketType.BELIEF_UPDATE,
        PacketType.TASK_RESULT,
        PacketType.INTEGRITY_ALERT,
    }),
)

# Layer 6: Task Prosecution — Execution, grounding
# Executes tasks, generates observations; cannot make policy decisions
LAYER_6_CONTRACT = LayerContract(
    layer=LayerSource.LAYER_6,
    description="Task Prosecution: Execution, grounding, observation.",
    can_emit=frozenset({
        PacketType.OBSERVATION,
        PacketType.TASK_RESULT,
        PacketType.BELIEF_UPDATE,
    }),
    can_receive=frozenset({
        PacketType.DECISION,
        PacketType.VERIFICATION_PLAN,
        PacketType.TOOL_AUTHORIZATION,
        PacketType.TASK_DIRECTIVE,
        PacketType.INTEGRITY_ALERT,
    }),
)

# Integrity Overlay — System health monitoring
# Can emit alerts and receive everything
INTEGRITY_CONTRACT = LayerContract(
    layer=LayerSource.INTEGRITY,
    description="Integrity Overlay: System health, budget enforcement, safe modes.",
    can_emit=frozenset({
        PacketType.INTEGRITY_ALERT,
    }),
    can_receive=frozenset({
        # Integrity monitors everything
        PacketType.OBSERVATION,
        PacketType.BELIEF_UPDATE,
        PacketType.DECISION,
        PacketType.VERIFICATION_PLAN,
        PacketType.TOOL_AUTHORIZATION,
        PacketType.TASK_DIRECTIVE,
        PacketType.TASK_RESULT,
        PacketType.ESCALATION,
        PacketType.INTEGRITY_ALERT,
    }),
)


# =============================================================================
# CONTRACT REGISTRY
# =============================================================================

LAYER_CONTRACTS: dict[LayerSource, LayerContract] = {
    LayerSource.LAYER_1: LAYER_1_CONTRACT,
    LayerSource.LAYER_2: LAYER_2_CONTRACT,
    LayerSource.LAYER_3: LAYER_3_CONTRACT,
    LayerSource.LAYER_4: LAYER_4_CONTRACT,
    LayerSource.LAYER_5: LAYER_5_CONTRACT,
    LayerSource.LAYER_6: LAYER_6_CONTRACT,
    LayerSource.INTEGRITY: INTEGRITY_CONTRACT,
}


def get_contract(layer: LayerSource) -> LayerContract:
    """Get the contract for a layer."""
    return LAYER_CONTRACTS[layer]


def get_all_contracts() -> list[LayerContract]:
    """Get all layer contracts."""
    return list(LAYER_CONTRACTS.values())


# =============================================================================
# CONTRACT ENFORCEMENT
# =============================================================================

@dataclass
class ContractViolation:
    """Record of a contract violation."""
    layer: LayerSource
    packet_type: PacketType
    violation_type: str  # "emit" or "receive"
    message: str


class ContractEnforcer:
    """
    Enforces layer contracts on packet operations.
    
    Used by buses and orchestrator to validate packet flow.
    """
    
    def __init__(self, contracts: dict[LayerSource, LayerContract] | None = None):
        self.contracts = contracts or LAYER_CONTRACTS
    
    def check_emit(
        self, 
        layer: LayerSource, 
        packet_type: PacketType
    ) -> ContractViolation | None:
        """
        Check if a layer can emit a packet type.
        
        Returns None if allowed, ContractViolation if not.
        """
        contract = self.contracts.get(layer)
        if contract is None:
            return ContractViolation(
                layer=layer,
                packet_type=packet_type,
                violation_type="emit",
                message=f"No contract defined for layer {layer.value}",
            )
        
        if not contract.allows_emit(packet_type):
            return ContractViolation(
                layer=layer,
                packet_type=packet_type,
                violation_type="emit",
                message=f"Layer {layer.value} cannot emit {packet_type.value}",
            )
        
        return None
    
    def check_receive(
        self,
        layer: LayerSource,
        packet_type: PacketType,
    ) -> ContractViolation | None:
        """
        Check if a layer can receive a packet type.
        
        Returns None if allowed, ContractViolation if not.
        """
        contract = self.contracts.get(layer)
        if contract is None:
            return ContractViolation(
                layer=layer,
                packet_type=packet_type,
                violation_type="receive",
                message=f"No contract defined for layer {layer.value}",
            )
        
        if not contract.allows_receive(packet_type):
            return ContractViolation(
                layer=layer,
                packet_type=packet_type,
                violation_type="receive",
                message=f"Layer {layer.value} cannot receive {packet_type.value}",
            )
        
        return None
    
    def validate_emission(
        self,
        layer: LayerSource,
        packet_type: PacketType,
    ) -> bool:
        """Check and return True if emission is valid."""
        return self.check_emit(layer, packet_type) is None
    
    def validate_reception(
        self,
        layer: LayerSource,
        packet_type: PacketType,
    ) -> bool:
        """Check and return True if reception is valid."""
        return self.check_receive(layer, packet_type) is None


def create_contract_enforcer() -> ContractEnforcer:
    """Factory for contract enforcer."""
    return ContractEnforcer()
