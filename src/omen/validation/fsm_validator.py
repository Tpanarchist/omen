"""
FSM Validator — Legal state transitions for episodes.

Second validation gate. Ensures cognitive flow is correct:
- Cannot EXECUTE before DECIDE
- VERIFY_FIRST forces verification loop
- WRITE actions require AUTHORIZE
- SAFEMODE can be entered from any state

Spec: OMEN.md §10.2, §10.3, §15.4
"""

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from omen.vocabulary import FSMState, PacketType, DecisionOutcome, ToolSafety
from omen.validation.schema_validator import ValidationResult, Packet


# =============================================================================
# TRANSITION TABLE
# =============================================================================

# Legal transitions: from_state -> set of legal to_states
# S9_SAFEMODE is reachable from any state (Integrity override)
LEGAL_TRANSITIONS: dict[FSMState, set[FSMState]] = {
    FSMState.S0_IDLE: {
        FSMState.S1_SENSE,      # Begin sensing
        FSMState.S9_SAFEMODE,   # Emergency
    },
    FSMState.S1_SENSE: {
        FSMState.S2_MODEL,      # Update world model
        FSMState.S3_DECIDE,     # Skip model, immediate decision (degraded mode)
        FSMState.S1_SENSE,      # Continue sensing
        FSMState.S9_SAFEMODE,
    },
    FSMState.S2_MODEL: {
        FSMState.S3_DECIDE,     # Make decision
        FSMState.S1_SENSE,      # Need more data
        FSMState.S7_REVIEW,     # Review beliefs, no new decision needed
        FSMState.S0_IDLE,       # Model stable, return to idle
        FSMState.S9_SAFEMODE,
    },
    FSMState.S3_DECIDE: {
        FSMState.S4_VERIFY,     # VERIFY_FIRST outcome
        FSMState.S5_AUTHORIZE,  # Need token for WRITE
        FSMState.S6_EXECUTE,    # ACT with READ-only
        FSMState.S7_REVIEW,     # DEFER outcome - review decision, no execution
        FSMState.S8_ESCALATED,  # ESCALATE outcome
        FSMState.S0_IDLE,       # DEFER outcome - skip review
        FSMState.S9_SAFEMODE,
    },
    FSMState.S4_VERIFY: {
        FSMState.S2_MODEL,      # Update beliefs from verification
        FSMState.S5_AUTHORIZE,  # Verification passed, request token for write
        FSMState.S6_EXECUTE,    # Execute verification reads
        FSMState.S8_ESCALATED,  # Verification impossible, escalate
        FSMState.S9_SAFEMODE,
    },
    FSMState.S5_AUTHORIZE: {
        FSMState.S6_EXECUTE,    # Token issued, proceed
        FSMState.S8_ESCALATED,  # Authorization denied
        FSMState.S9_SAFEMODE,
    },
    FSMState.S6_EXECUTE: {
        FSMState.S7_REVIEW,     # Review results
        FSMState.S2_MODEL,      # Update beliefs from results
        FSMState.S6_EXECUTE,    # Continue execution
        FSMState.S9_SAFEMODE,
    },
    FSMState.S7_REVIEW: {
        FSMState.S2_MODEL,      # Update model from results
        FSMState.S0_IDLE,       # Episode complete
        FSMState.S3_DECIDE,     # Need another decision
        FSMState.S9_SAFEMODE,
    },
    FSMState.S8_ESCALATED: {
        FSMState.S3_DECIDE,     # Human provided direction
        FSMState.S0_IDLE,       # Human chose to abort
        FSMState.S9_SAFEMODE,
    },
    FSMState.S9_SAFEMODE: {
        FSMState.S0_IDLE,       # Exit safe mode to idle
        FSMState.S9_SAFEMODE,   # Stay in safe mode
    },
}


# =============================================================================
# PACKET TO STATE MAPPING
# =============================================================================

def packet_implies_state(packet: Packet) -> FSMState | None:
    """
    Determine what FSM state a packet implies we're entering.
    
    Returns None if packet doesn't imply a state transition.
    """
    packet_type = packet.header.packet_type
    
    if packet_type == PacketType.OBSERVATION:
        return FSMState.S1_SENSE
    
    elif packet_type == PacketType.BELIEF_UPDATE:
        return FSMState.S2_MODEL
    
    elif packet_type == PacketType.DECISION:
        # Decision outcome determines state
        # (Note: actual validation handles two-phase transition)
        outcome = packet.payload.decision_outcome
        if outcome == DecisionOutcome.VERIFY_FIRST:
            return FSMState.S4_VERIFY
        elif outcome == DecisionOutcome.ESCALATE:
            return FSMState.S8_ESCALATED
        elif outcome == DecisionOutcome.DEFER:
            return FSMState.S0_IDLE
        else:  # ACT
            return FSMState.S3_DECIDE
    
    elif packet_type == PacketType.VERIFICATION_PLAN:
        return FSMState.S4_VERIFY
    
    elif packet_type == PacketType.TOOL_AUTHORIZATION:
        return FSMState.S5_AUTHORIZE
    
    elif packet_type == PacketType.TASK_DIRECTIVE:
        return FSMState.S6_EXECUTE
    
    elif packet_type == PacketType.TASK_RESULT:
        return FSMState.S7_REVIEW
    
    elif packet_type == PacketType.ESCALATION:
        return FSMState.S8_ESCALATED
    
    elif packet_type == PacketType.INTEGRITY_ALERT:
        # Integrity alerts can trigger safe mode
        if packet.payload.requires_immediate_attention:
            return FSMState.S9_SAFEMODE
        return None  # Informational alert, no state change
    
    return None


# =============================================================================
# EPISODE STATE TRACKER
# =============================================================================

@dataclass
class EpisodeState:
    """
    Tracks FSM state for an episode.
    
    Maintains:
    - Current state
    - State history
    - Pending requirements (e.g., must verify before act)
    """
    episode_id: UUID
    current_state: FSMState = FSMState.S0_IDLE
    state_history: list[FSMState] = field(default_factory=list)
    
    # Pending requirements
    requires_verification: bool = False  # VERIFY_FIRST was issued
    has_executed_since_verify_first: bool = False  # Executed verification tasks
    requires_authorization: bool = False  # WRITE action pending
    pending_decision_id: UUID | None = None  # Decision awaiting verification
    
    def transition_to(self, new_state: FSMState) -> None:
        """Record state transition."""
        self.state_history.append(self.current_state)
        self.current_state = new_state


# =============================================================================
# FSM VALIDATOR
# =============================================================================

class FSMValidator:
    """
    Validates FSM state transitions for episodes.
    
    Tracks episode state and validates that packet sequences
    follow legal cognitive flow.
    
    Spec: OMEN.md §10.3, §15.4
    """
    
    def __init__(self):
        self._episodes: dict[UUID, EpisodeState] = {}
    
    def get_or_create_episode(self, episode_id: UUID) -> EpisodeState:
        """Get existing episode state or create new one."""
        if episode_id not in self._episodes:
            self._episodes[episode_id] = EpisodeState(episode_id=episode_id)
        return self._episodes[episode_id]
    
    def validate_transition(self, packet: Packet) -> ValidationResult:
        """
        Validate that a packet represents a legal state transition.
        
        Returns validation result with errors if transition is illegal.
        """
        errors = []
        warnings = []
        
        episode_id = packet.header.correlation_id
        episode = self.get_or_create_episode(episode_id)
        
        # Special handling for Decision packets - they transition through S3_DECIDE
        if packet.header.packet_type == PacketType.DECISION:
            return self._validate_decision_transition(packet, episode)
        
        # Determine implied state
        implied_state = packet_implies_state(packet)
        if implied_state is None:
            # Packet doesn't imply state change
            return ValidationResult.success()
        
        # Check if transition is legal
        current = episode.current_state
        legal_next_states = LEGAL_TRANSITIONS.get(current, set())
        
        if implied_state not in legal_next_states:
            errors.append(
                f"Illegal FSM transition: {current.value} -> {implied_state.value}"
            )
            return ValidationResult.failure(errors, warnings)
        
        # Additional semantic checks
        result = self._validate_semantic_constraints(packet, episode)
        if not result.valid:
            return result
        
        # Update state
        self._apply_state_update(packet, episode, implied_state)
        
        return ValidationResult(valid=True, errors=[], warnings=warnings)
    
    def _validate_decision_transition(
        self, packet: Packet, episode: EpisodeState
    ) -> ValidationResult:
        """
        Validate Decision packet transition (special two-phase handling).
        
        Decision packets first transition to S3_DECIDE, then outcome determines next state.
        """
        errors = []
        warnings = []
        current = episode.current_state
        
        # Phase 1: Validate transition to S3_DECIDE
        if current != FSMState.S3_DECIDE:
            legal_next_states = LEGAL_TRANSITIONS.get(current, set())
            if FSMState.S3_DECIDE not in legal_next_states:
                errors.append(
                    f"Illegal FSM transition: {current.value} -> S3_DECIDE"
                )
                return ValidationResult.failure(errors, warnings)
            
            # Transition to S3_DECIDE
            episode.transition_to(FSMState.S3_DECIDE)
        
        # Phase 2: Determine outcome-based next state
        outcome = packet.payload.decision_outcome
        outcome_state = None
        
        if outcome == DecisionOutcome.VERIFY_FIRST:
            outcome_state = FSMState.S4_VERIFY
        elif outcome == DecisionOutcome.ESCALATE:
            outcome_state = FSMState.S8_ESCALATED
        elif outcome == DecisionOutcome.DEFER:
            outcome_state = FSMState.S0_IDLE
        # ACT stays in S3_DECIDE
        
        # Apply decision state tracking
        self._apply_decision_state_update(packet, episode, outcome_state)
        
        # If outcome requires state change, validate and apply it
        if outcome_state and outcome_state != FSMState.S3_DECIDE:
            legal_from_decide = LEGAL_TRANSITIONS.get(FSMState.S3_DECIDE, set())
            if outcome_state not in legal_from_decide:
                errors.append(
                    f"Illegal FSM transition: S3_DECIDE -> {outcome_state.value}"
                )
                return ValidationResult.failure(errors, warnings)
            
            episode.transition_to(outcome_state)
        
        return ValidationResult(valid=True, errors=[], warnings=warnings)
    
    def _validate_semantic_constraints(
        self, packet: Packet, episode: EpisodeState
    ) -> ValidationResult:
        """
        Validate semantic constraints beyond simple state transitions.
        
        - VERIFY_FIRST must complete verification before ACT
        - WRITE tools require AUTHORIZE state
        """
        errors = []
        warnings = []
        packet_type = packet.header.packet_type
        
        # Check: Cannot execute without deciding first
        if packet_type == PacketType.TASK_DIRECTIVE:
            if FSMState.S3_DECIDE not in episode.state_history and episode.current_state != FSMState.S3_DECIDE:
                errors.append("Cannot EXECUTE (TaskDirective) without prior DECIDE")
        
        # Check: VERIFY_FIRST must complete verification before acting
        if packet_type == PacketType.TASK_DIRECTIVE and episode.requires_verification:
            # Check if this is a verification task (READ) or action task
            payload = packet.payload
            has_write_tools = any(
                tool.tool_safety in (ToolSafety.WRITE, ToolSafety.MIXED)
                for tool in payload.tools
            )
            if has_write_tools:
                errors.append(
                    "VERIFY_FIRST requires verification before WRITE action. "
                    "Complete verification loop first."
                )
        
        # Check: WRITE/MIXED tools require authorization
        if packet_type == PacketType.TASK_DIRECTIVE:
            payload = packet.payload
            has_write_tools = any(
                tool.tool_safety in (ToolSafety.WRITE, ToolSafety.MIXED)
                for tool in payload.tools
            )
            if has_write_tools:
                if episode.current_state != FSMState.S5_AUTHORIZE:
                    # Check if we've been through authorize
                    if FSMState.S5_AUTHORIZE not in episode.state_history:
                        errors.append(
                            "WRITE/MIXED tools require AUTHORIZE state before EXECUTE"
                        )
        
        return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)
    
    def _apply_decision_state_update(
        self, packet: Packet, episode: EpisodeState, outcome_state: FSMState | None
    ) -> None:
        """Apply decision-specific state tracking."""
        outcome = packet.payload.decision_outcome
        
        if outcome == DecisionOutcome.VERIFY_FIRST:
            episode.requires_verification = True
            episode.has_executed_since_verify_first = False
            episode.pending_decision_id = packet.header.packet_id  # Track by packet ID
        elif outcome == DecisionOutcome.ACT:
            episode.requires_verification = False
            episode.has_executed_since_verify_first = False
    
    def _apply_state_update(
        self, packet: Packet, episode: EpisodeState, new_state: FSMState
    ) -> None:
        """Apply state transition and update episode tracking."""
        packet_type = packet.header.packet_type
        
        # Track execution during verification
        if packet_type == PacketType.TASK_DIRECTIVE and episode.requires_verification:
            episode.has_executed_since_verify_first = True
        
        # Clear verification requirement after belief update (if verification was executed)
        if packet_type == PacketType.BELIEF_UPDATE:
            if episode.requires_verification and episode.has_executed_since_verify_first:
                # Verification loop complete: VERIFY_FIRST → EXECUTE → REVIEW → MODEL
                episode.requires_verification = False
                episode.has_executed_since_verify_first = False
        
        # Track authorization for WRITE tools
        if packet_type == PacketType.TOOL_AUTHORIZATION:
            episode.requires_authorization = False  # Authorized
        
        episode.transition_to(new_state)
    
    def reset_episode(self, episode_id: UUID) -> None:
        """Reset episode state (e.g., after completion or error)."""
        if episode_id in self._episodes:
            del self._episodes[episode_id]
    
    def get_current_state(self, episode_id: UUID) -> FSMState:
        """Get current state for an episode."""
        episode = self.get_or_create_episode(episode_id)
        return episode.current_state


# Convenience function for creating validator instances
def create_fsm_validator() -> FSMValidator:
    """Create a new FSM validator instance."""
    return FSMValidator()
