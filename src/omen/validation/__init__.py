"""
Validation — Three-layer validation stack.

- Schema validator: structural correctness
- FSM validator: legal state transitions
- Invariant validator: cross-policy rules
"""

from omen.validation.schema_validator import (
    SchemaValidator,
    ValidationResult,
    validate_schema,
    Packet,
)

from omen.validation.fsm_validator import (
    FSMValidator,
    EpisodeState,
    FSMState,
    LEGAL_TRANSITIONS,
    packet_implies_state,
    create_fsm_validator,
)

__all__ = [
    # Schema validation
    "SchemaValidator",
    "ValidationResult",
    "validate_schema",
    "Packet",
    # FSM validation
    "FSMValidator",
    "EpisodeState",
    "FSMState",
    "LEGAL_TRANSITIONS",
    "packet_implies_state",
    "create_fsm_validator",
]
