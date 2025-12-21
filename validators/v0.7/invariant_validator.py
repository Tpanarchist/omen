"""
OMEN v0.7 Invariant Validator

Enforces cross-policy invariants (INV-001 through INV-012) that JSON Schema
and FSM validators cannot express. These are semantic constraints spanning
multiple packets and requiring episode-level state tracking.

Based on: validators/v0.7/invariant_rules.md
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any
from datetime import datetime
from enum import Enum


@dataclass
class BudgetUsage:
    """Tracks cumulative resource usage"""
    tokens: int = 0
    tool_calls: int = 0
    time_seconds: float = 0.0
    risk_spent: float = 0.0


@dataclass
class EpisodeLedger:
    """Episode-level state for invariant checking"""
    correlation_id: str
    campaign_id: str
    
    # Budget tracking
    initial_budgets: Dict[str, Any] = field(default_factory=dict)
    cumulative_usage: BudgetUsage = field(default_factory=BudgetUsage)
    
    # State tracking
    current_state: str = "S0_IDLE"
    tools_state: str = "tools_ok"
    quality_tier: str = "PAR"
    stakes_level: str = "LOW"
    
    # Evidence and assumptions
    evidence_refs: Set[str] = field(default_factory=set)
    load_bearing_assumptions: List[Dict] = field(default_factory=list)
    
    # Token tracking
    active_tokens: Dict[str, Dict] = field(default_factory=dict)
    
    # Directive tracking
    open_directives: Dict[str, Dict] = field(default_factory=dict)
    
    # Verification tracking
    in_verification_loop: bool = False
    verification_start_time: Optional[datetime] = None
    verification_packets: List[Dict] = field(default_factory=list)
    
    # Packet history
    packets_seen: List[str] = field(default_factory=list)
    recent_packets: List[Dict] = field(default_factory=list)
    
    # Episode timing
    start_time: Optional[datetime] = None
    last_packet_time: Optional[datetime] = None


@dataclass
class InvariantValidationResult:
    """Result of invariant validation"""
    is_valid: bool
    packet_id: str
    violations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class InvariantValidator:
    """Validates cross-policy invariants across episode sequences"""
    
    CONSEQUENTIAL_TYPES = {
        "DecisionPacket",
        "TaskDirectivePacket",
        "ToolAuthorizationToken",
        "EscalationPacket"
    }
    
    def __init__(self, check_timestamps=True):
        """
        Initialize validator
        
        Args:
            check_timestamps: If False, skip time-based checks (for historical fixtures)
        """
        self.episodes: Dict[str, EpisodeLedger] = {}
        self.check_timestamps = check_timestamps
    
    def validate_packet(self, packet: Dict) -> InvariantValidationResult:
        """Validate single packet against all applicable invariants"""
        header = packet.get("header", {})
        packet_id = header.get("packet_id", "unknown")
        packet_type = header.get("packet_type")
        correlation_id = header.get("correlation_id")
        
        violations = []
        warnings = []
        
        # Get or create episode ledger
        if correlation_id not in self.episodes:
            self.episodes[correlation_id] = EpisodeLedger(
                correlation_id=correlation_id,
                campaign_id=header.get("campaign_id", "unknown")
            )
        
        episode = self.episodes[correlation_id]
        
        # Check invariants
        violations.extend(self._check_inv_001(packet, packet_type))
        violations.extend(self._check_inv_002(packet, packet_type))
        violations.extend(self._check_inv_003(packet, packet_type, episode))
        violations.extend(self._check_inv_004(packet, packet_type))
        violations.extend(self._check_inv_005(episode))
        violations.extend(self._check_inv_006(packet, packet_type))
        violations.extend(self._check_inv_007(packet, packet_type, episode))
        violations.extend(self._check_inv_008(packet, packet_type, episode))
        violations.extend(self._check_inv_009(packet, packet_type))
        violations.extend(self._check_inv_010(packet, packet_type, episode))
        violations.extend(self._check_inv_011(episode))
        violations.extend(self._check_inv_012(packet, packet_type))
        
        # Update episode state if valid
        if not violations:
            self._update_episode_ledger(episode, packet, packet_type)
        
        return InvariantValidationResult(
            is_valid=len(violations) == 0,
            packet_id=packet_id,
            violations=violations,
            warnings=warnings
        )
    
    def validate_episode_sequence(self, packets: List[Dict]) -> List[InvariantValidationResult]:
        """Validate full episode sequence"""
        results = []
        for packet in packets:
            result = self.validate_packet(packet)
            results.append(result)
            if not result.is_valid:
                break  # Stop on first violation
        return results
    
    def _check_inv_001(self, packet: Dict, packet_type: str) -> List[str]:
        """MCP Completeness"""
        if packet_type not in self.CONSEQUENTIAL_TYPES:
            return []
        
        errors = []
        mcp = packet.get("mcp", {})
        
        # Check required MCP sections
        required_sections = {
            "intent": ["summary", "scope"],
            "stakes": ["impact", "irreversibility", "uncertainty", "adversariality", "stakes_level"],
            "quality": ["quality_tier", "satisficing_mode", "definition_of_done", "verification_requirement"],
            "budgets": ["token_budget", "tool_call_budget", "time_budget_seconds", "risk_budget"],
            "epistemics": ["status", "confidence", "calibration_note", "freshness_class", "assumptions"],
            "evidence": ["evidence_refs"],
            "routing": ["task_class", "tools_state"]
        }
        
        for section, fields in required_sections.items():
            if section not in mcp:
                errors.append(f"INV-001: Missing MCP section '{section}'")
                continue
            
            for field in fields:
                if field not in mcp[section]:
                    errors.append(f"INV-001: Missing required field 'mcp.{section}.{field}'")
        
        # Special case: evidence_absent_reason required if evidence_refs empty
        evidence = mcp.get("evidence", {})
        evidence_refs = evidence.get("evidence_refs", [])
        if len(evidence_refs) == 0 and not evidence.get("evidence_absent_reason"):
            errors.append("INV-001: evidence_absent_reason required when evidence_refs empty")
        
        # Check definition_of_done has required fields
        if "quality" in mcp:
            dod = mcp["quality"].get("definition_of_done", {})
            if not dod.get("text"):
                errors.append("INV-001: definition_of_done.text is required")
            if not dod.get("checks"):
                errors.append("INV-001: definition_of_done.checks is required")
        
        return errors
    
    def _check_inv_002(self, packet: Dict, packet_type: str) -> List[str]:
        """SUBPAR Never Authorizes Action"""
        if packet_type != "DecisionPacket":
            return []
        
        mcp = packet.get("mcp", {})
        quality_tier = mcp.get("quality", {}).get("quality_tier")
        decision_outcome = packet.get("payload", {}).get("decision_outcome")
        
        if quality_tier == "SUBPAR" and decision_outcome == "ACT":
            return ["INV-002: SUBPAR tier cannot authorize ACT decision"]
        
        return []
    
    def _check_inv_003(self, packet: Dict, packet_type: str, episode: EpisodeLedger) -> List[str]:
        """HIGH/CRITICAL Requires Verification or Escalation"""
        if packet_type != "DecisionPacket":
            return []
        
        mcp = packet.get("mcp", {})
        stakes_level = mcp.get("stakes", {}).get("stakes_level")
        decision_outcome = packet.get("payload", {}).get("decision_outcome")
        quality_tier = mcp.get("quality", {}).get("quality_tier")
        
        if stakes_level not in ["HIGH", "CRITICAL"]:
            return []
        
        errors = []
        
        if decision_outcome == "ACT":
            # Require SUPERB tier for direct ACT at HIGH/CRITICAL stakes
            if quality_tier != "SUPERB":
                errors.append(
                    "INV-003: HIGH/CRITICAL stakes require SUPERB tier for ACT, "
                    f"got {quality_tier}"
                )
            
            # Check all load-bearing assumptions verified
            assumptions = packet.get("payload", {}).get("load_bearing_assumptions", [])
            for assumption in assumptions:
                if not assumption.get("verified"):
                    errors.append(
                        f"INV-003: Unverified assumption '{assumption.get('assumption')}' "
                        "at HIGH/CRITICAL stakes"
                    )
        
        elif decision_outcome not in ["VERIFY_FIRST", "ESCALATE", "DEFER", "CANCEL"]:
            errors.append(
                f"INV-003: HIGH/CRITICAL stakes require VERIFY_FIRST or ESCALATE, "
                f"got {decision_outcome}"
            )
        
        return errors
    
    def _check_inv_004(self, packet: Dict, packet_type: str) -> List[str]:
        """LLM Cannot Claim Live Truth Without Evidence"""
        mcp = packet.get("mcp", {})
        epistemics = mcp.get("epistemics", {})
        status = epistemics.get("status")
        freshness = epistemics.get("freshness_class")
        
        # Only applies to ungrounded statuses
        if status not in ["INFERRED", "HYPOTHESIZED", "UNKNOWN"]:
            return []
        
        # Only applies to claims about current state
        if freshness not in ["REALTIME", "OPERATIONAL"]:
            return []
        
        # Exception: DecisionPacket with VERIFY_FIRST is explicitly acknowledging
        # the need for verification, so HYPOTHESIZED is acceptable
        if packet_type == "DecisionPacket":
            decision_outcome = packet.get("payload", {}).get("decision_outcome")
            if decision_outcome == "VERIFY_FIRST":
                return []  # Allowed: decision acknowledges need for verification
        
        # Check for recent tool evidence
        evidence_refs = mcp.get("evidence", {}).get("evidence_refs", [])
        has_tool_evidence = any(
            ref.get("ref_type") in ["tool_output", "user_observation"]
            for ref in evidence_refs
        )
        
        if not has_tool_evidence:
            return [
                f"INV-004: Cannot claim {freshness} {status} without tool evidence. "
                "Must have tool_output or user_observation in evidence_refs."
            ]
        
        return []
    
    def _check_inv_005(self, episode: EpisodeLedger) -> List[str]:
        """Budget Overruns Require Approval"""
        if not episode.initial_budgets:
            return []
        
        budgets = episode.initial_budgets
        usage = episode.cumulative_usage
        
        overruns = []
        if usage.tokens > budgets.get("token_budget", float('inf')):
            overruns.append(f"tokens: {usage.tokens} > {budgets['token_budget']}")
        if usage.tool_calls > budgets.get("tool_call_budget", float('inf')):
            overruns.append(f"tool_calls: {usage.tool_calls} > {budgets['tool_call_budget']}")
        if usage.time_seconds > budgets.get("time_budget_seconds", float('inf')):
            overruns.append(f"time: {usage.time_seconds:.1f}s > {budgets['time_budget_seconds']}s")
        
        if not overruns:
            return []
        
        # Check for approval
        has_escalation = any(
            p.get("header", {}).get("packet_type") == "EscalationPacket"
            for p in episode.recent_packets
        )
        has_override = any(
            p.get("header", {}).get("layer_source") == 1
            for p in episode.recent_packets
        )
        
        if not (has_escalation or has_override):
            return [f"INV-005: Budget overrun without approval: {', '.join(overruns)}"]
        
        return []
    
    def _check_inv_006(self, packet: Dict, packet_type: str) -> List[str]:
        """Drive Arbitration Sequence"""
        if packet_type != "DecisionPacket":
            return []
        
        payload = packet.get("payload", {})
        constraints = payload.get("constraints_satisfied", {})
        
        errors = []
        
        if not constraints.get("constitutional_check"):
            errors.append("INV-006: Stage 1 veto failed (constitutional_check = false)")
        
        if not constraints.get("budget_check"):
            errors.append("INV-006: Stage 2 feasibility failed (budget_check = false)")
        
        # Stage 3 check is informational (tradeoff policy should be referenced)
        # Not enforcing strictly as it's in decision_summary/rationale
        
        return errors
    
    def _check_inv_007(self, packet: Dict, packet_type: str, episode: EpisodeLedger) -> List[str]:
        """WRITE Requires Token Scope Containment"""
        if packet_type != "TaskDirectivePacket":
            return []
        
        payload = packet.get("payload", {})
        safety_class = payload.get("tool_safety_class")
        
        if safety_class not in ["WRITE", "MIXED"]:
            return []
        
        errors = []
        token_id = payload.get("authorization_token_id")
        
        if not token_id:
            return ["INV-007: WRITE directive requires authorization_token_id"]
        
        if token_id not in episode.active_tokens:
            return [f"INV-007: Token {token_id} not found in episode"]
        
        token = episode.active_tokens[token_id]
        token_payload = token.get("payload", {})
        
        # Check token validity
        if token_payload.get("revoked"):
            errors.append(f"INV-007: Token {token_id} is revoked")
        
        if token_payload.get("usage_count", 0) >= token_payload.get("max_usage_count", 1):
            errors.append(f"INV-007: Token {token_id} usage exhausted")
        
        # Check expiry (skip for historical fixtures)
        if self.check_timestamps:
            expiry_str = token_payload.get("expiry", "")
            try:
                expiry = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
                now = datetime.now(expiry.tzinfo) if expiry.tzinfo else datetime.now()
                if now >= expiry:
                    errors.append(f"INV-007: Token {token_id} expired")
            except Exception:
                pass  # Skip if expiry parsing fails
        
        # Check scope containment
        execution_method = payload.get("execution_method", {})
        tool_id = execution_method.get("tool_id")
        authorized_scope = token_payload.get("authorized_scope", {})
        authorized_tool_ids = authorized_scope.get("tool_ids", [])
        
        if tool_id and tool_id not in authorized_tool_ids:
            errors.append(
                f"INV-007: Tool '{tool_id}' not in token scope {authorized_tool_ids}"
            )
        
        return errors
    
    def _check_inv_008(self, packet: Dict, packet_type: str, episode: EpisodeLedger) -> List[str]:
        """Verification Loop Closure"""
        # Check when re-deciding after verification loop
        if packet_type != "DecisionPacket" or not episode.in_verification_loop:
            return []
        
        errors = []
        packets = episode.verification_packets
        
        # Check for READ directive
        has_read_directive = any(
            p.get("header", {}).get("packet_type") == "TaskDirectivePacket" and
            p.get("payload", {}).get("tool_safety_class") == "READ"
            for p in packets
        )
        if not has_read_directive:
            errors.append("INV-008: No READ TaskDirective in verification loop")
        
        # Check for SUCCESS result (if tools available)
        if episode.tools_state == "tools_ok":
            has_success_result = any(
                p.get("header", {}).get("packet_type") == "TaskResultPacket" and
                p.get("payload", {}).get("result_status") == "SUCCESS"
                for p in packets
            )
            if not has_success_result:
                errors.append("INV-008: No successful TaskResult in verification loop")
        
        # Check for OBSERVED observation
        has_observation = any(
            p.get("header", {}).get("packet_type") == "ObservationPacket" and
            p.get("mcp", {}).get("epistemics", {}).get("status") == "OBSERVED"
            for p in packets
        )
        if not has_observation:
            errors.append("INV-008: No OBSERVED ObservationPacket in verification loop")
        
        # Check for belief update
        has_belief_update = any(
            p.get("header", {}).get("packet_type") == "BeliefUpdatePacket"
            for p in packets
        )
        if not has_belief_update:
            errors.append("INV-008: No BeliefUpdatePacket to close verification loop")
        
        return errors
    
    def _check_inv_009(self, packet: Dict, packet_type: str) -> List[str]:
        """Escalation Must Present Options"""
        if packet_type != "EscalationPacket":
            return []
        
        payload = packet.get("payload", {})
        errors = []
        
        top_options = payload.get("top_options", [])
        if len(top_options) < 2 or len(top_options) > 3:
            errors.append(
                f"INV-009: EscalationPacket must have 2-3 top_options, got {len(top_options)}"
            )
        
        evidence_gaps = payload.get("evidence_gaps", [])
        if not evidence_gaps:
            errors.append("INV-009: EscalationPacket must have at least one evidence_gap")
        
        if not payload.get("recommended_next_step"):
            errors.append("INV-009: EscalationPacket must have recommended_next_step")
        
        return errors
    
    def _check_inv_010(self, packet: Dict, packet_type: str, episode: EpisodeLedger) -> List[str]:
        """Degraded Tools Policy"""
        mcp = packet.get("mcp", {})
        tools_state = mcp.get("routing", {}).get("tools_state")
        
        if tools_state not in ["tools_partial", "tools_down"]:
            return []
        
        errors = []
        
        # If tools degraded and issuing directive, must be READ-only
        if packet_type == "TaskDirectivePacket":
            safety_class = packet.get("payload", {}).get("tool_safety_class")
            if safety_class in ["WRITE", "MIXED"]:
                errors.append(
                    f"INV-010: WRITE directives not allowed with tools_state={tools_state}"
                )
        
        # If tools down and decision is ACT, should escalate instead
        if packet_type == "DecisionPacket" and tools_state == "tools_down":
            decision_outcome = packet.get("payload", {}).get("decision_outcome")
            if decision_outcome == "ACT":
                errors.append(
                    "INV-010: ACT decision not recommended with tools_down, "
                    "should ESCALATE or DEFER"
                )
        
        return errors
    
    def _check_inv_011(self, episode: EpisodeLedger) -> List[str]:
        """Task Closure"""
        # Skip timeout checks for historical episodes
        if not self.check_timestamps:
            return []
        
        errors = []
        now = datetime.now()
        
        for directive_id, directive_info in episode.open_directives.items():
            created_at_str = directive_info.get("created_at", "")
            timeout = directive_info.get("timeout_seconds", 3600)
            
            try:
                created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                if created_at.tzinfo:
                    now = datetime.now(created_at.tzinfo)
                elapsed = (now - created_at).total_seconds()
                
                if elapsed > timeout:
                    task_id = directive_info.get("task_id", directive_id)
                    errors.append(
                        f"INV-011: TaskDirective '{task_id}' timed out after {elapsed:.1f}s "
                        f"(timeout: {timeout}s)"
                    )
            except Exception:
                pass  # Skip if datetime parsing fails
        
        return errors
    
    def _check_inv_012(self, packet: Dict, packet_type: str) -> List[str]:
        """Stakes Consistency"""
        mcp = packet.get("mcp", {})
        stakes = mcp.get("stakes", {})
        
        stakes_level = stakes.get("stakes_level")
        if not stakes_level:
            return []
        
        # Get axes values
        impact = stakes.get("impact", "LOW")
        irreversibility = stakes.get("irreversibility", "REVERSIBLE")
        uncertainty = stakes.get("uncertainty", "LOW")
        adversariality = stakes.get("adversariality", "BENIGN")
        
        # Define severity mapping
        severity_map = {
            "CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1,
            "IRREVERSIBLE": 4, "SEMI_REVERSIBLE": 2, "REVERSIBLE": 1,
            "CONTESTED": 3, "ADVERSARIAL": 4, "BENIGN": 1
        }
        
        axes_severities = [
            severity_map.get(impact, 1),
            severity_map.get(irreversibility, 1),
            severity_map.get(uncertainty, 1),
            severity_map.get(adversariality, 1)
        ]
        
        max_severity = max(axes_severities)
        count_high = sum(1 for s in axes_severities if s >= 3)
        count_medium = sum(1 for s in axes_severities if s >= 2)
        
        errors = []
        
        if stakes_level == "CRITICAL":
            if max_severity < 4 and not (impact == "HIGH" and irreversibility == "IRREVERSIBLE" and uncertainty == "HIGH"):
                errors.append(
                    "INV-012: CRITICAL stakes_level requires at least one CRITICAL axis "
                    "or (HIGH impact + IRREVERSIBLE + HIGH uncertainty)"
                )
        
        elif stakes_level == "HIGH":
            if count_high < 2 and max_severity < 4:
                errors.append(
                    "INV-012: HIGH stakes_level requires at least two HIGH axes or one CRITICAL"
                )
        
        elif stakes_level == "MEDIUM":
            if count_medium < 1:
                errors.append(
                    "INV-012: MEDIUM stakes_level requires at least one MEDIUM or higher axis"
                )
        
        elif stakes_level == "LOW":
            if max_severity > 2:
                errors.append(
                    "INV-012: LOW stakes_level cannot have HIGH or CRITICAL axes"
                )
        
        return errors
    
    def _update_episode_ledger(self, episode: EpisodeLedger, packet: Dict, packet_type: str):
        """Update episode ledger after successful validation"""
        header = packet.get("header", {})
        payload = packet.get("payload", {})
        mcp = packet.get("mcp", {})
        packet_id = header.get("packet_id")
        
        # Update packet tracking
        episode.packets_seen.append(packet_id)
        episode.recent_packets.append(packet)
        if len(episode.recent_packets) > 10:
            episode.recent_packets.pop(0)
        
        # Update timing
        created_at_str = header.get("created_at", "")
        try:
            created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
            if episode.start_time is None:
                episode.start_time = created_at
            episode.last_packet_time = created_at
        except Exception:
            pass
        
        # Update budgets
        if packet_type == "DecisionPacket" and not episode.initial_budgets:
            budgets = mcp.get("budgets", {})
            episode.initial_budgets = {
                "token_budget": budgets.get("token_budget", 0),
                "tool_call_budget": budgets.get("tool_call_budget", 0),
                "time_budget_seconds": budgets.get("time_budget_seconds", 0),
                "risk_budget": budgets.get("risk_budget", {})
            }
        
        # Update state
        routing = mcp.get("routing", {})
        episode.tools_state = routing.get("tools_state", episode.tools_state)
        
        quality = mcp.get("quality", {})
        episode.quality_tier = quality.get("quality_tier", episode.quality_tier)
        
        stakes = mcp.get("stakes", {})
        episode.stakes_level = stakes.get("stakes_level", episode.stakes_level)
        
        # Track evidence
        evidence = mcp.get("evidence", {})
        for ref in evidence.get("evidence_refs", []):
            ref_id = ref.get("ref_id")
            if ref_id:
                episode.evidence_refs.add(ref_id)
        
        # Track tokens
        if packet_type == "ToolAuthorizationToken":
            token_id = payload.get("token_id")
            if token_id:
                episode.active_tokens[token_id] = packet
        
        # Track directives
        if packet_type == "TaskDirectivePacket":
            task_id = payload.get("task_id")
            if task_id:
                episode.open_directives[packet_id] = {
                    "task_id": task_id,
                    "created_at": header.get("created_at"),
                    "timeout_seconds": payload.get("timeout_seconds", 
                                                  mcp.get("budgets", {}).get("time_budget_seconds", 3600))
                }
                episode.cumulative_usage.tool_calls += 1
        
        # Close directives
        if packet_type == "TaskResultPacket":
            directive_id = payload.get("directive_packet_id")
            if directive_id in episode.open_directives:
                del episode.open_directives[directive_id]
        
        # Verification loop tracking
        if packet_type == "DecisionPacket":
            decision_outcome = payload.get("decision_outcome")
            if decision_outcome == "VERIFY_FIRST":
                episode.in_verification_loop = True
                episode.verification_start_time = episode.last_packet_time
                episode.verification_packets = []
            elif episode.in_verification_loop:
                # Closing verification loop with new decision
                episode.in_verification_loop = False
                episode.verification_packets = []
        
        if episode.in_verification_loop:
            episode.verification_packets.append(packet)
        
        # Track assumptions
        if packet_type == "DecisionPacket":
            assumptions = payload.get("load_bearing_assumptions", [])
            episode.load_bearing_assumptions = assumptions
        
        # Update budget usage
        execution_metadata = payload.get("execution_metadata", {})
        tokens_used = execution_metadata.get("tokens_used", 0)
        episode.cumulative_usage.tokens += tokens_used
        
        # Time tracking: only count actual execution time from metadata, not wall clock
        # Don't use packet timestamp differences as episodes may span long periods
        time_used = execution_metadata.get("execution_time_ms", 0) / 1000.0
        if time_used > 0:
            episode.cumulative_usage.time_seconds += time_used
