"""
OMEN v0.7 FSM Validator

Validates episode sequences against the Finite State Machine (FSM) specification.
Enforces legal state transitions, verification loop closure, token authorization,
and sequential dependencies per fsm_transitions.md.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime


class FSMState(Enum):
    """FSM states per fsm_transitions.md"""
    S0_IDLE = "S0_IDLE"
    S1_SENSE = "S1_SENSE"
    S2_MODEL = "S2_MODEL"
    S3_DECIDE = "S3_DECIDE"
    S4_VERIFY = "S4_VERIFY"
    S5_AUTHORIZE = "S5_AUTHORIZE"
    S6_EXECUTE = "S6_EXECUTE"
    S7_REVIEW = "S7_REVIEW"
    S8_ESCALATED = "S8_ESCALATED"
    S9_SAFEMODE = "S9_SAFEMODE"


@dataclass
class Token:
    """Tracks authorization token state"""
    token_id: str
    authorized_scope: Dict
    expiry: str
    max_usage_count: int
    usage_count: int
    revoked: bool
    issuer_layer: int
    
    def is_valid(self, current_time: datetime) -> bool:
        """Check if token is currently valid"""
        if self.revoked:
            return False
        if self.usage_count >= self.max_usage_count:
            return False
        
        # Parse expiry time (handle both naive and timezone-aware strings)
        expiry_str = self.expiry.replace('Z', '+00:00')
        expiry_time = datetime.fromisoformat(expiry_str)
        
        # Make both times timezone-aware for comparison
        from dateutil import tz
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=tz.UTC)
        if expiry_time.tzinfo is None:
            expiry_time = expiry_time.replace(tzinfo=tz.UTC)
            
        if current_time >= expiry_time:
            return False
        return True


@dataclass
class VerificationLoop:
    """Tracks verification loop state"""
    decision_packet_id: str
    plan_emitted: bool = False
    read_directives_issued: Set[str] = field(default_factory=set)
    successful_results: Set[str] = field(default_factory=set)
    observed_evidence: Set[str] = field(default_factory=set)
    belief_update_completed: bool = False
    
    def is_complete(self) -> bool:
        """Check if verification loop completed"""
        return (
            # plan_emitted is optional - not all verification loops emit explicit plans
            len(self.read_directives_issued) > 0 and
            len(self.successful_results) > 0 and
            len(self.observed_evidence) > 0 and
            self.belief_update_completed
        )


@dataclass
class EpisodeState:
    """Tracks state for a single episode (correlation_id)"""
    correlation_id: str
    current_state: FSMState = FSMState.S0_IDLE
    packets_seen: List[str] = field(default_factory=list)
    belief_updates_count: int = 0
    decisions_count: int = 0
    last_decision_outcome: Optional[str] = None
    last_decision_packet_id: Optional[str] = None
    
    # Token tracking
    active_tokens: Dict[str, Token] = field(default_factory=dict)
    
    # Task tracking
    open_directives: Dict[str, str] = field(default_factory=dict)  # directive_id -> task_id
    
    # Verification tracking
    active_verification: Optional[VerificationLoop] = None


@dataclass
class FSMValidationResult:
    """Result of FSM validation"""
    is_valid: bool
    correlation_id: str
    packet_id: str
    packet_type: str
    from_state: FSMState
    to_state: FSMState
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class FSMValidator:
    """
    Stateful validator for episode FSM transitions.
    
    Tracks episode state per correlation_id and validates:
    - Legal state transitions
    - Sequential dependencies (decision → directive)
    - Token authorization for WRITE operations
    - Verification loop closure
    - Task result closure
    """
    
    def __init__(self):
        """Initialize validator with empty episode state tracking"""
        self.episodes: Dict[str, EpisodeState] = {}
        
        # Transition table: (from_state, packet_type) → to_state
        self.transitions = self._build_transition_table()
    
    def _build_transition_table(self) -> Dict[Tuple[FSMState, str], FSMState]:
        """Build legal FSM transition table"""
        return {
            # From S0_IDLE
            (FSMState.S0_IDLE, "ObservationPacket"): FSMState.S1_SENSE,
            (FSMState.S0_IDLE, "ToolAuthorizationToken"): FSMState.S5_AUTHORIZE,  # Layer 1 pre-authorization
            
            # From S1_SENSE
            (FSMState.S1_SENSE, "ObservationPacket"): FSMState.S1_SENSE,
            (FSMState.S1_SENSE, "BeliefUpdatePacket"): FSMState.S2_MODEL,
            
            # From S2_MODEL
            (FSMState.S2_MODEL, "BeliefUpdatePacket"): FSMState.S2_MODEL,
            (FSMState.S2_MODEL, "DecisionPacket"): FSMState.S3_DECIDE,
            
            # From S3_DECIDE (conditional transitions handled separately)
            (FSMState.S3_DECIDE, "DecisionPacket"): FSMState.S3_DECIDE,  # Can re-decide
            
            # From S4_VERIFY
            (FSMState.S4_VERIFY, "VerificationPlanPacket"): FSMState.S4_VERIFY,
            (FSMState.S4_VERIFY, "TaskDirectivePacket"): FSMState.S4_VERIFY,
            (FSMState.S4_VERIFY, "TaskResultPacket"): FSMState.S4_VERIFY,
            (FSMState.S4_VERIFY, "ObservationPacket"): FSMState.S4_VERIFY,
            (FSMState.S4_VERIFY, "BeliefUpdatePacket"): FSMState.S2_MODEL,
            
            # From S5_AUTHORIZE
            (FSMState.S5_AUTHORIZE, "ToolAuthorizationToken"): FSMState.S5_AUTHORIZE,
            (FSMState.S5_AUTHORIZE, "TaskDirectivePacket"): FSMState.S6_EXECUTE,
            
            # From S6_EXECUTE
            (FSMState.S6_EXECUTE, "TaskDirectivePacket"): FSMState.S6_EXECUTE,
            (FSMState.S6_EXECUTE, "TaskResultPacket"): FSMState.S6_EXECUTE,
            (FSMState.S6_EXECUTE, "ObservationPacket"): FSMState.S6_EXECUTE,
            (FSMState.S6_EXECUTE, "BeliefUpdatePacket"): FSMState.S7_REVIEW,
            
            # From S7_REVIEW
            (FSMState.S7_REVIEW, "BeliefUpdatePacket"): FSMState.S7_REVIEW,
            (FSMState.S7_REVIEW, "ObservationPacket"): FSMState.S1_SENSE,  # New cycle
            
            # From S8_ESCALATED
            (FSMState.S8_ESCALATED, "EscalationPacket"): FSMState.S8_ESCALATED,
            (FSMState.S8_ESCALATED, "DecisionPacket"): FSMState.S3_DECIDE,  # After user input
            
            # From S9_SAFEMODE
            (FSMState.S9_SAFEMODE, "IntegrityAlertPacket"): FSMState.S9_SAFEMODE,
            (FSMState.S9_SAFEMODE, "BeliefUpdatePacket"): FSMState.S7_REVIEW,  # Recovery
        }
    
    def _get_episode_state(self, correlation_id: str) -> EpisodeState:
        """Get or create episode state"""
        if correlation_id not in self.episodes:
            self.episodes[correlation_id] = EpisodeState(correlation_id=correlation_id)
        return self.episodes[correlation_id]
    
    def validate_packet(self, packet: Dict) -> FSMValidationResult:
        """
        Validate single packet against FSM rules.
        
        Args:
            packet: Packet dictionary (must have header, mcp, payload)
        
        Returns:
            FSMValidationResult with validation outcome
        """
        header = packet["header"]
        mcp = packet["mcp"]
        payload = packet["payload"]
        
        packet_id = header["packet_id"]
        packet_type = header["packet_type"]
        correlation_id = header["correlation_id"]
        
        episode = self._get_episode_state(correlation_id)
        from_state = episode.current_state
        
        errors = []
        warnings = []
        
        # Determine target state
        to_state = self._determine_target_state(episode, packet_type, payload, errors)
        
        if to_state is None:
            # Invalid transition
            errors.append(
                f"Invalid transition: {from_state.value} -> {packet_type}. "
                f"No legal transition exists."
            )
            return FSMValidationResult(
                is_valid=False,
                correlation_id=correlation_id,
                packet_id=packet_id,
                packet_type=packet_type,
                from_state=from_state,
                to_state=from_state,  # Stay in current state on error
                errors=errors,
                warnings=warnings
            )
        
        # Apply enforcement rules
        self._enforce_rules(episode, packet_type, packet, to_state, errors, warnings)
        
        # Update episode state if valid
        if not errors:
            self._update_episode_state(episode, packet_type, packet, to_state)
        
        return FSMValidationResult(
            is_valid=len(errors) == 0,
            correlation_id=correlation_id,
            packet_id=packet_id,
            packet_type=packet_type,
            from_state=from_state,
            to_state=to_state if not errors else from_state,
            errors=errors,
            warnings=warnings
        )
    
    def _determine_target_state(
        self, 
        episode: EpisodeState, 
        packet_type: str, 
        payload: Dict,
        errors: List[str]
    ) -> Optional[FSMState]:
        """Determine target state based on packet type and payload"""
        from_state = episode.current_state
        
        # Special handling for DecisionPacket - outcome determines target state
        if packet_type == "DecisionPacket":
            decision_outcome = payload.get("decision_outcome")
            
            # From S2_MODEL or S3_DECIDE or S4_VERIFY (re-deciding)
            if from_state in [FSMState.S2_MODEL, FSMState.S3_DECIDE]:
                if decision_outcome == "VERIFY_FIRST":
                    return FSMState.S4_VERIFY
                elif decision_outcome == "ESCALATE":
                    return FSMState.S8_ESCALATED
                elif decision_outcome in ["DEFER", "CANCEL"]:
                    return FSMState.S7_REVIEW
                elif decision_outcome == "ACT":
                    # Stay in S3_DECIDE; next packet (token or directive) will transition
                    return FSMState.S3_DECIDE
            
            # From S8_ESCALATED (after user input)
            elif from_state == FSMState.S8_ESCALATED:
                return FSMState.S3_DECIDE
        
        # Special handling for ToolAuthorizationToken from S3_DECIDE
        if from_state == FSMState.S3_DECIDE and packet_type == "ToolAuthorizationToken":
            return FSMState.S5_AUTHORIZE
        
        # Special handling for TaskDirectivePacket
        if packet_type == "TaskDirectivePacket":
            if from_state == FSMState.S3_DECIDE:
                return FSMState.S6_EXECUTE
            elif from_state == FSMState.S4_VERIFY:
                return FSMState.S4_VERIFY  # Stay in VERIFY
            elif from_state == FSMState.S5_AUTHORIZE:
                return FSMState.S6_EXECUTE
        
        # Special handling for DecisionPacket from S5_AUTHORIZE (after token issued)
        if from_state == FSMState.S5_AUTHORIZE and packet_type == "DecisionPacket":
            return FSMState.S3_DECIDE
        
        # Standard transition table lookup
        transition_key = (from_state, packet_type)
        return self.transitions.get(transition_key)
    
    def _enforce_rules(
        self,
        episode: EpisodeState,
        packet_type: str,
        packet: Dict,
        to_state: FSMState,
        errors: List[str],
        warnings: List[str]
    ):
        """Apply FSM enforcement rules E1-E7"""
        payload = packet["payload"]
        
        # Rule E1: No Decision Without Model
        if packet_type == "DecisionPacket":
            if episode.belief_updates_count == 0 and episode.decisions_count == 0:
                warnings.append(
                    "First decision in episode without prior BeliefUpdate. "
                    "Ensure initial beliefs exist from context."
                )
        
        # Rule E2: No Action Without Decision
        if packet_type == "TaskDirectivePacket":
            # Allow directive if: (1) last decision was ACT, OR (2) in verification state
            if episode.last_decision_outcome not in ["ACT", "VERIFY_FIRST"]:
                errors.append(
                    f"TaskDirective requires prior DecisionPacket with outcome=ACT or VERIFY_FIRST. "
                    f"Last decision: {episode.last_decision_outcome or 'none'}"
                )
        
        # Rule E3: Verification Loop Must Complete
        if packet_type == "DecisionPacket" and episode.active_verification:
            if not episode.active_verification.is_complete():
                errors.append(
                    f"Re-decision attempted while verification loop incomplete. "
                    f"Started by: {episode.active_verification.decision_packet_id}"
                )
        
        # Rule E4: Write Requires Token
        if packet_type == "TaskDirectivePacket":
            safety_class = payload.get("tool_safety_class")
            if safety_class in ["WRITE", "MIXED"]:
                token_id = payload.get("authorization_token_id")
                if not token_id:
                    errors.append("WRITE directive missing authorization_token_id")
                elif token_id not in episode.active_tokens:
                    errors.append(f"Token {token_id} not found in episode ledger")
                else:
                    token = episode.active_tokens[token_id]
                    current_time = datetime.now()
                    if not token.is_valid(current_time):
                        errors.append(
                            f"Token {token_id} invalid: "
                            f"revoked={token.revoked}, "
                            f"usage={token.usage_count}/{token.max_usage_count}"
                        )
        
        # Rule E5: Escalation Must Present Options
        if packet_type == "EscalationPacket" and to_state == FSMState.S8_ESCALATED:
            top_options = payload.get("top_options", [])
            evidence_gaps = payload.get("evidence_gaps", [])
            recommended = payload.get("recommended_next_step")
            
            if len(top_options) < 2 or len(top_options) > 3:
                errors.append("EscalationPacket must have 2-3 top_options")
            if not evidence_gaps:
                errors.append("EscalationPacket must have at least one evidence_gap")
            if not recommended:
                errors.append("EscalationPacket must have recommended_next_step")
        
        # Rule E7: Safe Mode Lockdown
        if episode.current_state == FSMState.S9_SAFEMODE:
            if packet_type not in ["IntegrityAlertPacket", "BeliefUpdatePacket"]:
                errors.append(
                    f"In SAFEMODE, only IntegrityAlertPacket and BeliefUpdatePacket allowed. "
                    f"Got: {packet_type}"
                )
    
    def _update_episode_state(
        self,
        episode: EpisodeState,
        packet_type: str,
        packet: Dict,
        to_state: FSMState
    ):
        """Update episode state after successful validation"""
        header = packet["header"]
        payload = packet["payload"]
        packet_id = header["packet_id"]
        
        # Update state
        episode.current_state = to_state
        episode.packets_seen.append(packet_id)
        
        # Track packet-specific state
        if packet_type == "BeliefUpdatePacket":
            episode.belief_updates_count += 1
            
            # Check if this completes a verification loop
            if episode.active_verification and not episode.active_verification.belief_update_completed:
                episode.active_verification.belief_update_completed = True
        
        elif packet_type == "DecisionPacket":
            episode.decisions_count += 1
            episode.last_decision_outcome = payload.get("decision_outcome")
            episode.last_decision_packet_id = packet_id
            
            # Start verification loop if VERIFY_FIRST
            if episode.last_decision_outcome == "VERIFY_FIRST":
                episode.active_verification = VerificationLoop(
                    decision_packet_id=packet_id
                )
            
            # Clear verification loop if re-deciding after completion
            elif episode.active_verification and episode.active_verification.is_complete():
                episode.active_verification = None
        
        elif packet_type == "VerificationPlanPacket":
            if episode.active_verification:
                episode.active_verification.plan_emitted = True
        
        elif packet_type == "TaskDirectivePacket":
            task_id = payload.get("task_id")
            episode.open_directives[packet_id] = task_id
            
            # Track READ directives in verification loop
            if episode.active_verification:
                safety_class = payload.get("tool_safety_class")
                if safety_class == "READ":
                    episode.active_verification.read_directives_issued.add(packet_id)
            
            # Increment token usage for WRITE directives
            if payload.get("tool_safety_class") in ["WRITE", "MIXED"]:
                token_id = payload.get("authorization_token_id")
                if token_id and token_id in episode.active_tokens:
                    episode.active_tokens[token_id].usage_count += 1
        
        elif packet_type == "TaskResultPacket":
            directive_id = payload.get("directive_packet_id")
            if directive_id in episode.open_directives:
                del episode.open_directives[directive_id]
            
            # Track successful results in verification loop
            if episode.active_verification:
                result_status = payload.get("result_status")
                if result_status == "SUCCESS":
                    episode.active_verification.successful_results.add(packet_id)
        
        elif packet_type == "ObservationPacket":
            # Track OBSERVED evidence in verification loop
            if episode.active_verification:
                epistemic_status = packet["mcp"]["epistemics"].get("status")
                if epistemic_status == "OBSERVED":
                    episode.active_verification.observed_evidence.add(packet_id)
        
        elif packet_type == "ToolAuthorizationToken":
            token_id = payload["token_id"]
            episode.active_tokens[token_id] = Token(
                token_id=token_id,
                authorized_scope=payload["authorized_scope"],
                expiry=payload["expiry"],
                max_usage_count=payload["max_usage_count"],
                usage_count=payload["usage_count"],
                revoked=payload["revoked"],
                issuer_layer=payload["issuer_layer"]
            )
    
    def validate_episode_sequence(self, packets: List[Dict]) -> List[FSMValidationResult]:
        """
        Validate entire episode sequence.
        
        Args:
            packets: List of packet dictionaries
        
        Returns:
            List of validation results (one per packet)
        """
        results = []
        for packet in packets:
            result = self.validate_packet(packet)
            results.append(result)
            
            # Stop on first error for strict validation
            if not result.is_valid:
                break
        
        return results
    
    def get_episode_summary(self, correlation_id: str) -> Optional[Dict]:
        """Get current state summary for an episode"""
        if correlation_id not in self.episodes:
            return None
        
        episode = self.episodes[correlation_id]
        return {
            "correlation_id": correlation_id,
            "current_state": episode.current_state.value,
            "packets_seen": len(episode.packets_seen),
            "decisions_count": episode.decisions_count,
            "belief_updates_count": episode.belief_updates_count,
            "open_directives": len(episode.open_directives),
            "active_tokens": len(episode.active_tokens),
            "verification_active": episode.active_verification is not None,
            "verification_complete": (
                episode.active_verification.is_complete() 
                if episode.active_verification else None
            )
        }
