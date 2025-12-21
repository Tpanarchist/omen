"""
OMEN v0.7 Template Compiler

Compiles episode templates (A-G) into valid packet sequences that satisfy
schema, FSM, and invariant constraints. Acts as the "generative" complement
to the validation stack.

Templates:
- A: Grounding Loop (Sense → Model → Decide)
- B: Verification Loop (Decide VERIFY_FIRST → Plan → Execute → Update → Decide)
- C: Read-Only Act (Decide ACT → READ directives → results → belief integration)
- D: Write Act (Decide ACT → token → WRITE directive → result → belief integration)
- E: Escalation (Decide ESCALATE → present options + gaps)
- F: Degraded Tools (tools_down/partial posture handling)
- G: Compile-to-Code (explicit compile request with test/rollback gates)

Spec Reference: OMEN.md Section 11 (Lines 866-920)

Usage:
    from templates.v0.7.template_compiler import TemplateCompiler, TemplateID, TemplateContext
    
    # Create context
    ctx = TemplateContext(
        correlation_id="corr_001",
        intent_summary="Test verification loop",
        stakes_level="MEDIUM"
    )
    
    # Compile template
    compiler = TemplateCompiler()
    packets = compiler.compile(TemplateID.VERIFICATION_LOOP, ctx)
    
    # Export to JSONL
    compiler.export_jsonl("episode.jsonl", packets)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
import json
import uuid


class TemplateID(str, Enum):
    """Canonical episode templates"""
    GROUNDING_LOOP = "template_a_grounding_loop"
    VERIFICATION_LOOP = "template_b_verification_loop"
    READONLY_ACT = "template_c_readonly_act"
    WRITE_ACT = "template_d_write_act"
    ESCALATION = "template_e_escalation"
    DEGRADED_TOOLS = "template_f_degraded_tools"
    COMPILE_TO_CODE = "template_g_compile_to_code"


@dataclass
class TemplateContext:
    """Parameters for template compilation"""
    # Episode identification
    correlation_id: str
    campaign_id: str = "camp_OMEN_BOOT"
    
    # MCP envelope fields
    intent_summary: str = "Execute template episode"
    intent_scope: str = "template_scope"
    
    # Stakes (affects decision logic)
    impact: str = "MEDIUM"
    irreversibility: str = "REVERSIBLE"
    uncertainty: str = "MEDIUM"
    adversariality: str = "BENIGN"
    stakes_level: str = "MEDIUM"
    
    # Quality
    quality_tier: str = "PAR"
    satisficing_mode: bool = False
    verification_requirement: str = "OPTIONAL"
    
    # Budgets
    token_budget: int = 1000
    tool_call_budget: int = 3
    time_budget_seconds: int = 120
    risk_envelope: str = "low"
    risk_max_loss: str = "minimal"
    
    # Epistemics
    initial_status: str = "HYPOTHESIZED"
    initial_confidence: float = 0.70
    freshness_class: str = "OPERATIONAL"
    stale_if_older_than_seconds: int = 1800
    
    # Tools/routing
    tools_state: str = "tools_ok"
    task_class: str = "DECIDE"
    
    # Template-specific parameters
    template_params: Dict[str, Any] = field(default_factory=dict)
    
    # Timestamp control
    base_timestamp: Optional[datetime] = None


@dataclass
class EpisodeLedger:
    """Tracks episode state during compilation"""
    correlation_id: str
    packets_emitted: List[Dict] = field(default_factory=list)
    current_timestamp: datetime = field(default_factory=datetime.now)
    previous_packet_id: Optional[str] = None
    
    # Stateful tracking
    evidence_refs: List[str] = field(default_factory=list)
    assumptions: List[Dict] = field(default_factory=list)
    active_tokens: List[str] = field(default_factory=list)
    open_directives: List[str] = field(default_factory=list)
    
    # Budget burn tracking
    tokens_spent: int = 0
    tool_calls_made: int = 0
    time_spent_seconds: float = 0.0
    
    def advance_timestamp(self, seconds: float = 10.0) -> datetime:
        """Move timestamp forward by delta"""
        self.current_timestamp += timedelta(seconds=seconds)
        return self.current_timestamp
    
    def emit_packet(self, packet: Dict) -> None:
        """Record emitted packet"""
        self.packets_emitted.append(packet)
        self.previous_packet_id = packet["header"]["packet_id"]
    
    def add_evidence_ref(self, ref: str) -> None:
        """Track evidence reference"""
        if ref not in self.evidence_refs:
            self.evidence_refs.append(ref)
    
    def add_assumption(self, assumption: Dict) -> None:
        """Track load-bearing assumption"""
        self.assumptions.append(assumption)
    
    def issue_token(self, token_id: str) -> None:
        """Track active token"""
        self.active_tokens.append(token_id)
    
    def open_directive(self, directive_id: str) -> None:
        """Track open directive"""
        self.open_directives.append(directive_id)
    
    def close_directive(self, directive_id: str) -> None:
        """Mark directive complete"""
        if directive_id in self.open_directives:
            self.open_directives.remove(directive_id)
    
    def burn_budget(self, tokens: int = 0, tool_calls: int = 0, time_seconds: float = 0.0) -> None:
        """Track budget consumption"""
        self.tokens_spent += tokens
        self.tool_calls_made += tool_calls
        self.time_spent_seconds += time_seconds


class TemplateCompiler:
    """Compiles episode templates into valid packet sequences"""
    
    def __init__(self):
        self.ledger: Optional[EpisodeLedger] = None
        self.context: Optional[TemplateContext] = None
    
    def compile(self, template_id: TemplateID, context: TemplateContext) -> List[Dict]:
        """
        Compile template into packet sequence
        
        Args:
            template_id: Which template to compile (A-G)
            context: Template parameters and MCP envelope fields
        
        Returns:
            List of packets in emission order
        
        Raises:
            ValueError: If template_id unknown or context invalid
        """
        # Initialize compilation state
        self.context = context
        self.ledger = EpisodeLedger(
            correlation_id=context.correlation_id,
            current_timestamp=context.base_timestamp or datetime.now()
        )
        
        # Route to template implementation
        if template_id == TemplateID.GROUNDING_LOOP:
            return self._compile_template_a()
        elif template_id == TemplateID.VERIFICATION_LOOP:
            return self._compile_template_b()
        elif template_id == TemplateID.READONLY_ACT:
            return self._compile_template_c()
        elif template_id == TemplateID.WRITE_ACT:
            return self._compile_template_d()
        elif template_id == TemplateID.ESCALATION:
            return self._compile_template_e()
        elif template_id == TemplateID.DEGRADED_TOOLS:
            return self._compile_template_f()
        elif template_id == TemplateID.COMPILE_TO_CODE:
            return self._compile_template_g()
        else:
            raise ValueError(f"Unknown template_id: {template_id}")
    
    # ========== MCP Envelope Builder ==========
    
    def _build_mcp(self, overrides: Optional[Dict] = None) -> Dict:
        """Build MCP envelope from context with optional overrides"""
        ctx = self.context
        mcp = {
            "intent": {
                "summary": ctx.intent_summary,
                "scope": ctx.intent_scope
            },
            "stakes": {
                "impact": ctx.impact,
                "irreversibility": ctx.irreversibility,
                "uncertainty": ctx.uncertainty,
                "adversariality": ctx.adversariality,
                "stakes_level": ctx.stakes_level
            },
            "quality": {
                "quality_tier": ctx.quality_tier,
                "satisficing_mode": ctx.satisficing_mode,
                "definition_of_done": {
                    "text": "Template step complete",
                    "checks": ["step_executed"]
                },
                "verification_requirement": ctx.verification_requirement
            },
            "budgets": {
                "token_budget": ctx.token_budget,
                "tool_call_budget": ctx.tool_call_budget,
                "time_budget_seconds": ctx.time_budget_seconds,
                "risk_budget": {
                    "envelope": ctx.risk_envelope,
                    "max_loss": ctx.risk_max_loss
                }
            },
            "epistemics": {
                "status": ctx.initial_status,
                "confidence": ctx.initial_confidence,
                "calibration_note": "Template-generated packet",
                "freshness_class": ctx.freshness_class,
                "stale_if_older_than_seconds": ctx.stale_if_older_than_seconds,
                "assumptions": []
            },
            "evidence": {
                "evidence_refs": [],
                "evidence_absent_reason": "Template initialization"
            },
            "routing": {
                "task_class": ctx.task_class,
                "tools_state": ctx.tools_state
            }
        }
        
        # Apply overrides
        if overrides:
            self._deep_update(mcp, overrides)
        
        return mcp
    
    def _deep_update(self, target: Dict, updates: Dict) -> None:
        """Deep merge updates into target dict"""
        for key, value in updates.items():
            if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                self._deep_update(target[key], value)
            else:
                target[key] = value
    
    # ========== Packet Builders ==========
    
    def _build_header(self, packet_type: str, layer_source: int) -> Dict:
        """Build packet header"""
        packet_id = f"pkt_{packet_type.lower().replace('packet', '')}_{uuid.uuid4().hex[:8]}"
        header = {
            "packet_id": packet_id,
            "packet_type": packet_type,
            "created_at": self.ledger.current_timestamp.isoformat(),
            "layer_source": layer_source,
            "correlation_id": self.context.correlation_id,
            "campaign_id": self.context.campaign_id
        }
        
        if self.ledger.previous_packet_id:
            header["previous_packet_id"] = self.ledger.previous_packet_id
        
        return header
    
    def _emit_observation(self, mcp_overrides: Dict, payload: Dict, time_delta: float = 5.0) -> Dict:
        """Emit ObservationPacket"""
        self.ledger.advance_timestamp(time_delta)
        
        packet = {
            "header": self._build_header("ObservationPacket", layer_source=6),
            "mcp": self._build_mcp(mcp_overrides),
            "payload": payload
        }
        
        self.ledger.emit_packet(packet)
        return packet
    
    def _emit_belief_update(self, mcp_overrides: Dict, payload: Dict, time_delta: float = 3.0) -> Dict:
        """Emit BeliefUpdatePacket"""
        self.ledger.advance_timestamp(time_delta)
        
        packet = {
            "header": self._build_header("BeliefUpdatePacket", layer_source=5),
            "mcp": self._build_mcp(mcp_overrides),
            "payload": payload
        }
        
        self.ledger.emit_packet(packet)
        return packet
    
    def _emit_decision(self, mcp_overrides: Dict, payload: Dict, time_delta: float = 10.0) -> Dict:
        """Emit DecisionPacket"""
        self.ledger.advance_timestamp(time_delta)
        
        packet = {
            "header": self._build_header("DecisionPacket", layer_source=5),
            "mcp": self._build_mcp(mcp_overrides),
            "payload": payload
        }
        
        self.ledger.emit_packet(packet)
        return packet
    
    def _emit_token(self, mcp_overrides: Dict, payload: Dict, time_delta: float = 2.0) -> Dict:
        """Emit ToolAuthorizationToken"""
        self.ledger.advance_timestamp(time_delta)
        
        packet = {
            "header": self._build_header("ToolAuthorizationToken", layer_source=1),
            "mcp": self._build_mcp(mcp_overrides),
            "payload": payload
        }
        
        token_id = packet["header"]["packet_id"]
        self.ledger.issue_token(token_id)
        self.ledger.emit_packet(packet)
        return packet
    
    def _emit_directive(self, mcp_overrides: Dict, payload: Dict, time_delta: float = 5.0) -> Dict:
        """Emit TaskDirectivePacket"""
        self.ledger.advance_timestamp(time_delta)
        
        packet = {
            "header": self._build_header("TaskDirectivePacket", layer_source=5),
            "mcp": self._build_mcp(mcp_overrides),
            "payload": payload
        }
        
        directive_id = packet["header"]["packet_id"]
        self.ledger.open_directive(directive_id)
        self.ledger.emit_packet(packet)
        return packet
    
    def _emit_result(self, directive_id: str, mcp_overrides: Dict, payload: Dict, time_delta: float = 8.0) -> Dict:
        """Emit TaskResultPacket"""
        self.ledger.advance_timestamp(time_delta)
        
        packet = {
            "header": self._build_header("TaskResultPacket", layer_source=6),
            "mcp": self._build_mcp(mcp_overrides),
            "payload": payload
        }
        
        self.ledger.close_directive(directive_id)
        self.ledger.emit_packet(packet)
        return packet
    
    def _emit_escalation(self, mcp_overrides: Dict, payload: Dict, time_delta: float = 15.0) -> Dict:
        """Emit EscalationPacket"""
        self.ledger.advance_timestamp(time_delta)
        
        packet = {
            "header": self._build_header("EscalationPacket", layer_source=5),
            "mcp": self._build_mcp(mcp_overrides),
            "payload": payload
        }
        
        self.ledger.emit_packet(packet)
        return packet
    
    # ========== Template A: Grounding Loop ==========
    
    def _compile_template_a(self) -> List[Dict]:
        """
        Template A: Grounding Loop (Sense → Model → Decide)
        
        Simplest template: observe → update beliefs → decide on action.
        Used for low-stakes decisions with adequate information.
        """
        packets = []
        
        # Step 1: ObservationPacket (Layer 6 senses environment)
        obs = self._emit_observation(
            mcp_overrides={
                "intent": {"summary": "Sense current state", "scope": self.context.intent_scope},
                "epistemics": {"status": "OBSERVED", "confidence": 0.90, "freshness_class": "REALTIME"},
                "evidence": {"evidence_refs": [], "evidence_absent_reason": "Direct observation"}
            },
            payload={
                "observation_type": "sensor_reading",
                "tool_id": "sensor_api",
                "data_summary": "Current state captured",
                "structured_data": {"reading": "nominal"}
            }
        )
        packets.append(obs)
        
        # Step 2: BeliefUpdatePacket (Layer 5 integrates observation)
        belief = self._emit_belief_update(
            mcp_overrides={
                "intent": {"summary": "Update beliefs from observation", "scope": self.context.intent_scope},
                "epistemics": {"status": "OBSERVED", "confidence": 0.88, "freshness_class": "REALTIME"},
                "evidence": {"evidence_refs": [obs["header"]["packet_id"]], "evidence_absent_reason": None}
            },
            payload={
                "update_type": "observation_integration",
                "belief_delta": {"state": "updated from observation"},
                "prior_refs": [],
                "contradictions_detected": False
            }
        )
        packets.append(belief)
        
        # Step 3: DecisionPacket (Layer 5 decides action)
        decision = self._emit_decision(
            mcp_overrides={
                "intent": {"summary": self.context.intent_summary, "scope": self.context.intent_scope},
                "epistemics": {
                    "status": "OBSERVED",
                    "confidence": 0.85,
                    "freshness_class": "REALTIME",
                    "assumptions": []
                },
                "evidence": {
                    "evidence_refs": [obs["header"]["packet_id"], belief["header"]["packet_id"]],
                    "evidence_absent_reason": None
                }
            },
            payload={
                "decision_outcome": "ACT",
                "decision_summary": f"Execute {self.context.intent_summary} based on grounded observation",
                "chosen_option": {
                    "option_id": "opt_act",
                    "description": "Proceed with action",
                    "expected_value": 0.80,
                    "risk_profile": self.context.risk_envelope
                },
                "rejected_alternatives": [],
                "constraints_satisfied": {
                    "constitutional_check": True,
                    "budget_check": True,
                    "tool_availability": True
                },
                "rationale": "Grounding loop complete, stakes permit action"
            }
        )
        packets.append(decision)
        
        return packets
    
    # ========== Template B: Verification Loop ==========
    
    def _compile_template_b(self) -> List[Dict]:
        """
        Template B: Verification Loop
        
        Decide VERIFY_FIRST → Plan → Execute reads → Update beliefs → Decide ACT
        
        Used when uncertainty or stakes require verification before action.
        Demonstrates epistemic upgrade path: HYPOTHESIZED → OBSERVED.
        """
        packets = []
        
        # Step 1: ObservationPacket (stale cached data)
        obs1 = self._emit_observation(
            mcp_overrides={
                "intent": {"summary": "Retrieve cached state", "scope": self.context.intent_scope},
                "epistemics": {"status": "REMEMBERED", "confidence": 0.60, "freshness_class": "STRATEGIC"},
                "evidence": {"evidence_refs": [], "evidence_absent_reason": "Cache read, no fresh observation"}
            },
            payload={
                "observation_type": "cache_read",
                "tool_id": "memory_cache",
                "data_summary": "Stale cached data retrieved",
                "structured_data": {"data_age_seconds": 3600}
            }
        )
        packets.append(obs1)
        
        # Step 2: BeliefUpdatePacket (staleness refresh)
        belief1 = self._emit_belief_update(
            mcp_overrides={
                "intent": {"summary": "Integrate cached data, note staleness", "scope": self.context.intent_scope},
                "epistemics": {"status": "HYPOTHESIZED", "confidence": 0.55, "freshness_class": "OPERATIONAL"},
                "evidence": {"evidence_refs": [obs1["header"]["packet_id"]], "evidence_absent_reason": None}
            },
            payload={
                "update_type": "staleness_detected",
                "belief_delta": {"state": "requires_verification"},
                "prior_refs": [],
                "contradictions_detected": False
            }
        )
        packets.append(belief1)
        
        # Step 3: DecisionPacket (VERIFY_FIRST)
        assumption_id = f"assume_{uuid.uuid4().hex[:8]}"
        decision1 = self._emit_decision(
            mcp_overrides={
                "intent": {"summary": "Decide whether to verify before action", "scope": self.context.intent_scope},
                "epistemics": {
                    "status": "HYPOTHESIZED",
                    "confidence": 0.50,
                    "freshness_class": "OPERATIONAL",
                    "assumptions": [{
                        "assumption_id": assumption_id,
                        "text": "Cached data still accurate",
                        "load_bearing": True,
                        "verified": False
                    }]
                },
                "evidence": {"evidence_refs": [obs1["header"]["packet_id"], belief1["header"]["packet_id"]]}
            },
            payload={
                "decision_outcome": "VERIFY_FIRST",
                "decision_summary": "Verify assumptions before committing to action",
                "chosen_option": {
                    "option_id": "opt_verify",
                    "description": "Execute verification read",
                    "expected_value": 0.85,
                    "risk_profile": "minimal"
                },
                "rejected_alternatives": [
                    {
                        "option_id": "opt_act_now",
                        "rejection_reason": f"Stakes {self.context.stakes_level} + uncertainty {self.context.uncertainty} + stale data = verify-first per Q-POL"
                    }
                ],
                "constraints_satisfied": {
                    "constitutional_check": True,
                    "budget_check": True,
                    "tool_availability": True
                },
                "rationale": "Q-POL requires verification when stakes/uncertainty exceed threshold with stale data"
            }
        )
        packets.append(decision1)
        
        # Step 4: TaskDirectivePacket (READ verification)
        directive = self._emit_directive(
            mcp_overrides={
                "intent": {"summary": "Execute verification read", "scope": self.context.intent_scope},
                "epistemics": {"status": "HYPOTHESIZED", "confidence": 0.50},
                "evidence": {"evidence_refs": [decision1["header"]["packet_id"]]}
            },
            payload={
                "tool_id": "verify_api",
                "operation": "read_current_state",
                "tool_safety_class": "READ",
                "parameters": {"verification_target": "current_state"},
                "expected_duration_seconds": 5,
                "failure_modes": ["api_timeout", "network_error"]
            }
        )
        packets.append(directive)
        directive_id = directive["header"]["packet_id"]
        
        # Step 5: TaskResultPacket (SUCCESS)
        result = self._emit_result(
            directive_id=directive_id,
            mcp_overrides={
                "intent": {"summary": "Verification read complete", "scope": self.context.intent_scope},
                "epistemics": {"status": "OBSERVED", "confidence": 0.95, "freshness_class": "REALTIME"}
            },
            payload={
                "directive_packet_id": directive_id,
                "result_status": "SUCCESS",
                "result_summary": "Fresh observation obtained",
                "structured_output": {"state": "verified_current"},
                "execution_metadata": {
                    "execution_time_ms": 450,
                    "tokens_used": 150,
                    "tool_calls": 1
                }
            }
        )
        packets.append(result)
        
        # Step 6: ObservationPacket (fresh OBSERVED evidence)
        obs2 = self._emit_observation(
            mcp_overrides={
                "intent": {"summary": "Fresh observation from verification", "scope": self.context.intent_scope},
                "epistemics": {"status": "OBSERVED", "confidence": 0.95, "freshness_class": "REALTIME"},
                "evidence": {"evidence_refs": [result["header"]["packet_id"]], "evidence_absent_reason": None}
            },
            payload={
                "observation_type": "tool_result",
                "tool_id": "verify_api",
                "data_summary": "Fresh verified state",
                "structured_data": {"verified": True}
            }
        )
        packets.append(obs2)
        
        # Step 7: BeliefUpdatePacket (epistemic upgrade)
        belief2 = self._emit_belief_update(
            mcp_overrides={
                "intent": {"summary": "Integrate verification, upgrade epistemic status", "scope": self.context.intent_scope},
                "epistemics": {"status": "OBSERVED", "confidence": 0.92, "freshness_class": "REALTIME"},
                "evidence": {"evidence_refs": [result["header"]["packet_id"], obs2["header"]["packet_id"]]}
            },
            payload={
                "update_type": "verification_complete",
                "belief_delta": {"state": "epistemic_upgrade_to_observed"},
                "prior_refs": [belief1["header"]["packet_id"]],
                "contradictions_detected": False
            }
        )
        packets.append(belief2)
        
        # Step 8: DecisionPacket (ACT after verification)
        decision2 = self._emit_decision(
            mcp_overrides={
                "intent": {"summary": self.context.intent_summary, "scope": self.context.intent_scope},
                "epistemics": {
                    "status": "OBSERVED",
                    "confidence": 0.90,
                    "freshness_class": "REALTIME",
                    "assumptions": [{
                        "assumption_id": assumption_id,
                        "text": "Cached data still accurate",
                        "load_bearing": True,
                        "verified": True,
                        "verification_packet_id": result["header"]["packet_id"]
                    }]
                },
                "evidence": {
                    "evidence_refs": [obs2["header"]["packet_id"], belief2["header"]["packet_id"], result["header"]["packet_id"]]
                }
            },
            payload={
                "decision_outcome": "ACT",
                "decision_summary": f"Execute {self.context.intent_summary} after successful verification",
                "chosen_option": {
                    "option_id": "opt_act",
                    "description": "Proceed with action",
                    "expected_value": 0.88,
                    "risk_profile": self.context.risk_envelope
                },
                "rejected_alternatives": [],
                "constraints_satisfied": {
                    "constitutional_check": True,
                    "budget_check": True,
                    "tool_availability": True
                },
                "rationale": "Verification complete, assumptions verified, epistemic status upgraded to OBSERVED"
            }
        )
        packets.append(decision2)
        
        return packets
    
    # ========== Template C: Read-Only Act ==========
    
    def _compile_template_c(self) -> List[Dict]:
        """
        Template C: Read-Only Act
        
        Decide ACT → READ directives → results → belief integration
        
        Fast path for low-stakes read-only operations.
        No token required (INV-007 only applies to WRITE).
        """
        packets = []
        
        # Step 1: DecisionPacket (ACT for read-only operation)
        decision = self._emit_decision(
            mcp_overrides={
                "intent": {"summary": self.context.intent_summary, "scope": self.context.intent_scope},
                "stakes": {"impact": "LOW", "uncertainty": "LOW", "stakes_level": "LOW"},
                "epistemics": {
                    "status": "DERIVED",
                    "confidence": 0.85,
                    "freshness_class": "OPERATIONAL",
                    "assumptions": []
                },
                "evidence": {"evidence_refs": [], "evidence_absent_reason": "Low-stakes fast path"}
            },
            payload={
                "decision_outcome": "ACT",
                "decision_summary": f"Execute read-only {self.context.intent_summary}",
                "chosen_option": {
                    "option_id": "opt_read",
                    "description": "Execute read operation",
                    "expected_value": 0.82,
                    "risk_profile": "minimal"
                },
                "rejected_alternatives": [],
                "constraints_satisfied": {
                    "constitutional_check": True,
                    "budget_check": True,
                    "tool_availability": True
                },
                "rationale": "LOW stakes + READ operation → fast path authorized"
            }
        )
        packets.append(decision)
        
        # Step 2: TaskDirectivePacket (READ)
        directive = self._emit_directive(
            mcp_overrides={
                "intent": {"summary": "Execute read operation", "scope": self.context.intent_scope},
                "evidence": {"evidence_refs": [decision["header"]["packet_id"]]}
            },
            payload={
                "tool_id": self.context.template_params.get("tool_id", "read_api"),
                "operation": "read",
                "tool_safety_class": "READ",
                "parameters": self.context.template_params.get("parameters", {}),
                "expected_duration_seconds": 5,
                "failure_modes": ["api_timeout", "network_error"]
            }
        )
        packets.append(directive)
        directive_id = directive["header"]["packet_id"]
        
        # Step 3: TaskResultPacket (SUCCESS)
        result = self._emit_result(
            directive_id=directive_id,
            mcp_overrides={
                "intent": {"summary": "Read complete", "scope": self.context.intent_scope},
                "epistemics": {"status": "OBSERVED", "confidence": 0.90, "freshness_class": "REALTIME"}
            },
            payload={
                "directive_packet_id": directive_id,
                "result_status": "SUCCESS",
                "result_summary": "Read operation successful",
                "structured_output": self.context.template_params.get("result_data", {"data": "retrieved"}),
                "execution_metadata": {
                    "execution_time_ms": 350,
                    "tokens_used": 100,
                    "tool_calls": 1
                }
            }
        )
        packets.append(result)
        
        # Step 4: ObservationPacket (capture result)
        obs = self._emit_observation(
            mcp_overrides={
                "intent": {"summary": "Capture read result", "scope": self.context.intent_scope},
                "epistemics": {"status": "OBSERVED", "confidence": 0.92, "freshness_class": "REALTIME"},
                "evidence": {"evidence_refs": [result["header"]["packet_id"]]}
            },
            payload={
                "observation_type": "tool_result",
                "tool_id": self.context.template_params.get("tool_id", "read_api"),
                "data_summary": "Read result captured",
                "structured_data": self.context.template_params.get("result_data", {"data": "retrieved"})
            }
        )
        packets.append(obs)
        
        # Step 5: BeliefUpdatePacket (integrate result)
        belief = self._emit_belief_update(
            mcp_overrides={
                "intent": {"summary": "Integrate read result", "scope": self.context.intent_scope},
                "epistemics": {"status": "OBSERVED", "confidence": 0.88, "freshness_class": "REALTIME"},
                "evidence": {"evidence_refs": [result["header"]["packet_id"], obs["header"]["packet_id"]]}
            },
            payload={
                "update_type": "observation_integration",
                "belief_delta": {"state": "updated_from_read"},
                "prior_refs": [],
                "contradictions_detected": False
            }
        )
        packets.append(belief)
        
        return packets
    
    # ========== Template D: Write Act ==========
    
    def _compile_template_d(self) -> List[Dict]:
        """
        Template D: Write Act
        
        Decide ACT → token → WRITE directive → result → belief integration
        
        HIGH stakes write operation requiring token authorization.
        Demonstrates INV-007 token scope validation.
        """
        packets = []
        
        # Step 1: DecisionPacket (ACT for write operation - requires HIGH stakes + SUPERB)
        assumption_id = f"assume_{uuid.uuid4().hex[:8]}"
        decision = self._emit_decision(
            mcp_overrides={
                "intent": {"summary": self.context.intent_summary, "scope": self.context.intent_scope},
                "stakes": {"impact": "HIGH", "uncertainty": "LOW", "stakes_level": "HIGH"},
                "quality": {"quality_tier": "SUPERB", "verification_requirement": "VERIFY_ALL"},
                "epistemics": {
                    "status": "OBSERVED",
                    "confidence": 0.90,
                    "freshness_class": "REALTIME",
                    "assumptions": [{
                        "assumption_id": assumption_id,
                        "text": self.context.template_params.get("assumption", "Write operation is safe"),
                        "load_bearing": True,
                        "verified": True,
                        "verification_packet_id": "pkt_verify_prev"  # Assume prior verification
                    }]
                },
                "evidence": {"evidence_refs": ["pkt_verify_prev"], "evidence_absent_reason": None}
            },
            payload={
                "decision_outcome": "ACT",
                "decision_summary": f"Execute HIGH stakes {self.context.intent_summary}",
                "chosen_option": {
                    "option_id": "opt_write",
                    "description": "Execute write operation",
                    "expected_value": 0.88,
                    "risk_profile": "medium"
                },
                "rejected_alternatives": [],
                "constraints_satisfied": {
                    "constitutional_check": True,
                    "budget_check": True,
                    "tool_availability": True
                },
                "rationale": "HIGH stakes + SUPERB tier + verified assumptions → write authorized per INV-003"
            }
        )
        packets.append(decision)
        
        # Step 2: ToolAuthorizationToken (Layer 1 issues write token)
        tool_id = self.context.template_params.get("tool_id", "write_api")
        token = self._emit_token(
            mcp_overrides={
                "intent": {"summary": "Authorize write operation", "scope": self.context.intent_scope},
                "stakes": {"impact": "HIGH", "stakes_level": "HIGH"},
                "quality": {"quality_tier": "SUPERB"},
                "epistemics": {"status": "DERIVED", "confidence": 0.95}
            },
            payload={
                "authorized_scope": {
                    "tool_ids": [tool_id],
                    "operation_types": ["write"],
                    "resource_constraints": self.context.template_params.get("resource_constraints", {})
                },
                "expires_at": (self.ledger.current_timestamp + timedelta(minutes=10)).isoformat(),
                "max_usage_count": 1,
                "current_usage_count": 0,
                "revoked": False,
                "issuing_decision_id": decision["header"]["packet_id"]
            }
        )
        packets.append(token)
        token_id = token["header"]["packet_id"]
        
        # Step 3: TaskDirectivePacket (WRITE with token)
        directive = self._emit_directive(
            mcp_overrides={
                "intent": {"summary": "Execute write operation", "scope": self.context.intent_scope},
                "stakes": {"impact": "HIGH", "stakes_level": "HIGH"},
                "evidence": {"evidence_refs": [decision["header"]["packet_id"], token_id]}
            },
            payload={
                "tool_id": tool_id,
                "operation": "write",
                "tool_safety_class": "WRITE",
                "parameters": self.context.template_params.get("parameters", {}),
                "expected_duration_seconds": 10,
                "failure_modes": ["api_timeout", "write_error", "authorization_failed"],
                "authorization_token_id": token_id
            }
        )
        packets.append(directive)
        directive_id = directive["header"]["packet_id"]
        
        # Step 4: TaskResultPacket (SUCCESS)
        result = self._emit_result(
            directive_id=directive_id,
            mcp_overrides={
                "intent": {"summary": "Write complete", "scope": self.context.intent_scope},
                "epistemics": {"status": "OBSERVED", "confidence": 0.95, "freshness_class": "REALTIME"}
            },
            payload={
                "directive_packet_id": directive_id,
                "result_status": "SUCCESS",
                "result_summary": "Write operation successful",
                "structured_output": self.context.template_params.get("result_data", {"write_confirmed": True}),
                "execution_metadata": {
                    "execution_time_ms": 850,
                    "tokens_used": 200,
                    "tool_calls": 1
                }
            }
        )
        packets.append(result)
        
        # Step 5: ObservationPacket (capture write confirmation)
        obs = self._emit_observation(
            mcp_overrides={
                "intent": {"summary": "Capture write confirmation", "scope": self.context.intent_scope},
                "epistemics": {"status": "OBSERVED", "confidence": 0.95, "freshness_class": "REALTIME"},
                "evidence": {"evidence_refs": [result["header"]["packet_id"]]}
            },
            payload={
                "observation_type": "tool_result",
                "tool_id": tool_id,
                "data_summary": "Write confirmed",
                "structured_data": self.context.template_params.get("result_data", {"write_confirmed": True})
            }
        )
        packets.append(obs)
        
        # Step 6: BeliefUpdatePacket (integrate write results)
        belief = self._emit_belief_update(
            mcp_overrides={
                "intent": {"summary": "Integrate write results", "scope": self.context.intent_scope},
                "epistemics": {"status": "OBSERVED", "confidence": 0.92, "freshness_class": "REALTIME"},
                "evidence": {"evidence_refs": [result["header"]["packet_id"], obs["header"]["packet_id"]]}
            },
            payload={
                "update_type": "write_confirmation",
                "belief_delta": {"state": "write_completed"},
                "prior_refs": [],
                "contradictions_detected": False
            }
        )
        packets.append(belief)
        
        return packets
    
    # ========== Template E: Escalation ==========
    
    def _compile_template_e(self) -> List[Dict]:
        """
        Template E: Escalation
        
        Decide ESCALATE → present options + gaps
        
        Used when stakes/uncertainty exceed autonomous authority.
        Demonstrates INV-009 escalation structure requirements.
        """
        packets = []
        
        # Step 1: DecisionPacket (ESCALATE)
        decision = self._emit_decision(
            mcp_overrides={
                "intent": {"summary": self.context.intent_summary, "scope": self.context.intent_scope},
                "stakes": {"impact": "CRITICAL", "uncertainty": "HIGH", "stakes_level": "CRITICAL"},
                "quality": {"quality_tier": "SUPERB"},
                "epistemics": {
                    "status": "INFERRED",
                    "confidence": 0.35,
                    "freshness_class": "OPERATIONAL",
                    "assumptions": []
                },
                "evidence": {"evidence_refs": [], "evidence_absent_reason": "High uncertainty precludes autonomous action"}
            },
            payload={
                "decision_outcome": "ESCALATE",
                "decision_summary": f"Escalate {self.context.intent_summary} due to CRITICAL stakes + HIGH uncertainty",
                "chosen_option": {
                    "option_id": "opt_escalate",
                    "description": "Present options to higher authority",
                    "expected_value": 0.0,
                    "risk_profile": "deferred"
                },
                "rejected_alternatives": [
                    {
                        "option_id": "opt_act",
                        "rejection_reason": "CRITICAL stakes + HIGH uncertainty exceeds autonomous authority per Q-POL"
                    }
                ],
                "constraints_satisfied": {
                    "constitutional_check": True,
                    "budget_check": True,
                    "tool_availability": True
                },
                "rationale": "CRITICAL + HIGH uncertainty mandates escalation per Q-POL"
            }
        )
        packets.append(decision)
        
        # Step 2: EscalationPacket (present options)
        escalation = self._emit_escalation(
            mcp_overrides={
                "intent": {"summary": "Present escalation options", "scope": self.context.intent_scope},
                "stakes": {"impact": "CRITICAL", "uncertainty": "HIGH", "stakes_level": "CRITICAL"},
                "epistemics": {"status": "INFERRED", "confidence": 0.35}
            },
            payload={
                "escalation_trigger": "high_stakes_high_uncertainty",
                "blocking_decision_packet_id": decision["header"]["packet_id"],
                "top_options": [
                    {
                        "option_id": "opt_1",
                        "description": self.context.template_params.get("option_1", "Option 1: Proceed with caution"),
                        "pros": ["Maintains progress"],
                        "cons": ["Risk of failure"],
                        "risk_summary": "medium"
                    },
                    {
                        "option_id": "opt_2",
                        "description": self.context.template_params.get("option_2", "Option 2: Defer decision"),
                        "pros": ["Minimizes risk"],
                        "cons": ["Delays outcome"],
                        "risk_summary": "low"
                    },
                    {
                        "option_id": "opt_3",
                        "description": self.context.template_params.get("option_3", "Option 3: Gather more information"),
                        "pros": ["Better informed decision"],
                        "cons": ["Time/budget cost"],
                        "risk_summary": "low"
                    }
                ],
                "evidence_gaps": [
                    {
                        "gap_description": "Uncertainty about outcome",
                        "impact_if_unknown": "high"
                    }
                ],
                "recommended_next_step": {
                    "step_description": self.context.template_params.get("recommendation", "Recommend Option 3: gather information"),
                    "rationale": "Reduces uncertainty before CRITICAL decision"
                }
            }
        )
        packets.append(escalation)
        
        return packets
    
    # ========== Template F: Degraded Tools ==========
    
    def _compile_template_f(self) -> List[Dict]:
        """
        Template F: Degraded Tools
        
        tools_down/partial posture handling
        
        Demonstrates C-POL degraded mode rules (INV-010).
        CRITICAL stakes + tools_partial → mandatory ESCALATE.
        """
        packets = []
        
        # Step 1: ObservationPacket (system telemetry showing degradation)
        obs = self._emit_observation(
            mcp_overrides={
                "intent": {"summary": "System telemetry showing tool degradation", "scope": "system_health"},
                "stakes": {"impact": "MEDIUM", "stakes_level": "LOW"},
                "epistemics": {"status": "OBSERVED", "confidence": 0.98, "freshness_class": "REALTIME"},
                "evidence": {"evidence_refs": [], "evidence_absent_reason": "Direct system observation"},
                "routing": {"tools_state": "tools_partial"}
            },
            payload={
                "observation_type": "system_telemetry",
                "tool_id": "system_monitor",
                "data_summary": "Tool degradation detected",
                "structured_data": {"tools_state": "tools_partial", "degraded_services": ["write_api"]}
            }
        )
        packets.append(obs)
        
        # Step 2: BeliefUpdatePacket (system state update)
        belief = self._emit_belief_update(
            mcp_overrides={
                "intent": {"summary": "Update system state belief", "scope": "system_health"},
                "epistemics": {"status": "OBSERVED", "confidence": 0.95},
                "evidence": {"evidence_refs": [obs["header"]["packet_id"]]},
                "routing": {"tools_state": "tools_partial"}
            },
            payload={
                "update_type": "system_state_change",
                "belief_delta": {"tools_state": "tools_partial"},
                "prior_refs": [],
                "contradictions_detected": False
            }
        )
        packets.append(belief)
        
        # Step 3: DecisionPacket (ESCALATE due to degraded + CRITICAL)
        decision = self._emit_decision(
            mcp_overrides={
                "intent": {"summary": self.context.intent_summary, "scope": self.context.intent_scope},
                "stakes": {"impact": "CRITICAL", "uncertainty": "HIGH", "stakes_level": "CRITICAL"},
                "quality": {"quality_tier": "SUPERB"},
                "epistemics": {"status": "INFERRED", "confidence": 0.40},
                "evidence": {"evidence_refs": [obs["header"]["packet_id"], belief["header"]["packet_id"]]},
                "routing": {"tools_state": "tools_partial"}
            },
            payload={
                "decision_outcome": "ESCALATE",
                "decision_summary": "Escalate CRITICAL decision due to degraded tools",
                "chosen_option": {
                    "option_id": "opt_escalate",
                    "description": "Escalate to higher authority",
                    "expected_value": 0.0,
                    "risk_profile": "deferred"
                },
                "rejected_alternatives": [
                    {
                        "option_id": "opt_act",
                        "rejection_reason": "CRITICAL stakes + tools_partial → no ACT per C-POL INV-010"
                    }
                ],
                "constraints_satisfied": {
                    "constitutional_check": True,
                    "budget_check": True,
                    "tool_availability": False
                },
                "rationale": "C-POL degraded mode rules: CRITICAL + tools_partial → escalate"
            }
        )
        packets.append(decision)
        
        # Step 4: EscalationPacket (degraded tools escalation)
        escalation = self._emit_escalation(
            mcp_overrides={
                "intent": {"summary": "Escalate critical decision due to degraded tools", "scope": self.context.intent_scope},
                "stakes": {"impact": "CRITICAL", "uncertainty": "HIGH", "stakes_level": "CRITICAL"},
                "epistemics": {"status": "INFERRED", "confidence": 0.40},
                "routing": {"tools_state": "tools_partial"}
            },
            payload={
                "escalation_trigger": "tools_degraded_critical",
                "blocking_decision_packet_id": decision["header"]["packet_id"],
                "top_options": [
                    {
                        "option_id": "opt_defer",
                        "description": "Defer decision until tools_ok restored",
                        "pros": ["Safe", "Wait for full capability"],
                        "cons": ["Delayed outcome"],
                        "risk_summary": "minimal"
                    },
                    {
                        "option_id": "opt_proceed_degraded",
                        "description": "Proceed with degraded tools (read-only)",
                        "pros": ["Some progress possible"],
                        "cons": ["Limited capability", "Risky"],
                        "risk_summary": "high"
                    }
                ],
                "evidence_gaps": [
                    {
                        "gap_description": "Full tool restoration timeline unknown",
                        "impact_if_unknown": "medium"
                    }
                ],
                "recommended_next_step": {
                    "step_description": "Defer until tools_ok restored",
                    "rationale": "CRITICAL stakes require full tool capability"
                }
            }
        )
        packets.append(escalation)
        
        return packets
    
    # ========== Template G: Compile-to-Code ==========
    
    def _compile_template_g(self) -> List[Dict]:
        """
        Template G: Compile-to-Code
        
        Explicit compile request with test/rollback gates
        
        Meta-template for code generation workflows.
        Demonstrates multi-phase execution with verification gates.
        """
        packets = []
        
        # Step 1: DecisionPacket (VERIFY_FIRST for code generation)
        decision1 = self._emit_decision(
            mcp_overrides={
                "intent": {"summary": "Generate code with test gates", "scope": "code_generation"},
                "stakes": {"impact": "MEDIUM", "uncertainty": "MEDIUM", "stakes_level": "MEDIUM"},
                "epistemics": {"status": "HYPOTHESIZED", "confidence": 0.60}
            },
            payload={
                "decision_outcome": "VERIFY_FIRST",
                "decision_summary": "Generate code, then verify with tests",
                "chosen_option": {
                    "option_id": "opt_generate_and_test",
                    "description": "Generate code with test verification",
                    "expected_value": 0.80,
                    "risk_profile": "low"
                },
                "rejected_alternatives": [],
                "constraints_satisfied": {
                    "constitutional_check": True,
                    "budget_check": True,
                    "tool_availability": True
                },
                "rationale": "Code generation requires test verification gate"
            }
        )
        packets.append(decision1)
        
        # Step 2: TaskDirectivePacket (generate code)
        directive1 = self._emit_directive(
            mcp_overrides={
                "intent": {"summary": "Generate code", "scope": "code_generation"},
                "evidence": {"evidence_refs": [decision1["header"]["packet_id"]]}
            },
            payload={
                "tool_id": "code_generator",
                "operation": "generate",
                "tool_safety_class": "READ",
                "parameters": self.context.template_params.get("code_spec", {}),
                "expected_duration_seconds": 15,
                "failure_modes": ["generation_error", "invalid_syntax"]
            }
        )
        packets.append(directive1)
        directive1_id = directive1["header"]["packet_id"]
        
        # Step 3: TaskResultPacket (code generated)
        result1 = self._emit_result(
            directive_id=directive1_id,
            mcp_overrides={
                "intent": {"summary": "Code generation complete", "scope": "code_generation"},
                "epistemics": {"status": "DERIVED", "confidence": 0.70}
            },
            payload={
                "directive_packet_id": directive1_id,
                "result_status": "SUCCESS",
                "result_summary": "Code generated successfully",
                "structured_output": {"code": "...generated code...", "syntax_valid": True},
                "execution_metadata": {
                    "execution_time_ms": 2500,
                    "tokens_used": 800,
                    "tool_calls": 1
                }
            }
        )
        packets.append(result1)
        
        # Step 4: TaskDirectivePacket (run tests)
        directive2 = self._emit_directive(
            mcp_overrides={
                "intent": {"summary": "Run tests on generated code", "scope": "code_generation"},
                "evidence": {"evidence_refs": [result1["header"]["packet_id"]]}
            },
            payload={
                "tool_id": "test_runner",
                "operation": "test",
                "tool_safety_class": "READ",
                "parameters": {"test_suite": "unit_tests"},
                "expected_duration_seconds": 10,
                "failure_modes": ["test_failed", "runtime_error"]
            }
        )
        packets.append(directive2)
        directive2_id = directive2["header"]["packet_id"]
        
        # Step 5: TaskResultPacket (tests pass)
        result2 = self._emit_result(
            directive_id=directive2_id,
            mcp_overrides={
                "intent": {"summary": "Tests complete", "scope": "code_generation"},
                "epistemics": {"status": "OBSERVED", "confidence": 0.92, "freshness_class": "REALTIME"}
            },
            payload={
                "directive_packet_id": directive2_id,
                "result_status": "SUCCESS",
                "result_summary": "All tests passed",
                "structured_output": {"tests_passed": 12, "tests_failed": 0},
                "execution_metadata": {
                    "execution_time_ms": 1800,
                    "tokens_used": 200,
                    "tool_calls": 1
                }
            }
        )
        packets.append(result2)
        
        # Step 6: BeliefUpdatePacket (code verified)
        belief = self._emit_belief_update(
            mcp_overrides={
                "intent": {"summary": "Code verified by tests", "scope": "code_generation"},
                "epistemics": {"status": "OBSERVED", "confidence": 0.90},
                "evidence": {"evidence_refs": [result1["header"]["packet_id"], result2["header"]["packet_id"]]}
            },
            payload={
                "update_type": "verification_complete",
                "belief_delta": {"code_state": "verified"},
                "prior_refs": [],
                "contradictions_detected": False
            }
        )
        packets.append(belief)
        
        # Step 7: DecisionPacket (ACT to deploy)
        decision2 = self._emit_decision(
            mcp_overrides={
                "intent": {"summary": "Deploy verified code", "scope": "code_generation"},
                "epistemics": {"status": "OBSERVED", "confidence": 0.88},
                "evidence": {"evidence_refs": [result2["header"]["packet_id"], belief["header"]["packet_id"]]}
            },
            payload={
                "decision_outcome": "ACT",
                "decision_summary": "Deploy code after successful verification",
                "chosen_option": {
                    "option_id": "opt_deploy",
                    "description": "Deploy verified code",
                    "expected_value": 0.85,
                    "risk_profile": "low"
                },
                "rejected_alternatives": [],
                "constraints_satisfied": {
                    "constitutional_check": True,
                    "budget_check": True,
                    "tool_availability": True
                },
                "rationale": "All tests passed, code verified and ready for deployment"
            }
        )
        packets.append(decision2)
        
        return packets
    
    # ========== Export Functions ==========
    
    @staticmethod
    def export_jsonl(filepath: str, packets: List[Dict]) -> None:
        """
        Export packet sequence to JSONL file
        
        Args:
            filepath: Path to output JSONL file
            packets: List of packets to export
        """
        with open(filepath, 'w', encoding='utf-8') as f:
            for packet in packets:
                json.dump(packet, f, ensure_ascii=False)
                f.write('\n')
    
    @staticmethod
    def export_json(filepath: str, packets: List[Dict], indent: int = 2) -> None:
        """
        Export packet sequence to JSON file (pretty-printed)
        
        Args:
            filepath: Path to output JSON file
            packets: List of packets to export
            indent: Indentation level (default: 2)
        """
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(packets, f, ensure_ascii=False, indent=indent)
    
    def compile_and_export(self, template_id: TemplateID, context: TemplateContext, 
                          output_path: str, format: str = 'jsonl') -> List[Dict]:
        """
        Compile template and export to file in one step
        
        Args:
            template_id: Which template to compile
            context: Template parameters
            output_path: Output file path
            format: 'jsonl' or 'json' (default: 'jsonl')
        
        Returns:
            List of compiled packets
        """
        packets = self.compile(template_id, context)
        
        if format == 'jsonl':
            self.export_jsonl(output_path, packets)
        elif format == 'json':
            self.export_json(output_path, packets)
        else:
            raise ValueError(f"Unknown format: {format}. Use 'jsonl' or 'json'")
        
        return packets


# ========== Convenience Functions ==========

def compile_template(template_id: TemplateID, correlation_id: str, **kwargs) -> List[Dict]:
    """
    Convenience function to compile a template with minimal boilerplate
    
    Args:
        template_id: Which template to compile (A-G)
        correlation_id: Episode correlation ID
        **kwargs: Any TemplateContext fields to override
    
    Returns:
        List of compiled packets
    
    Example:
        packets = compile_template(
            TemplateID.VERIFICATION_LOOP,
            "corr_test_001",
            intent_summary="Test market price verification",
            stakes_level="MEDIUM"
        )
    """
    context = TemplateContext(correlation_id=correlation_id, **kwargs)
    compiler = TemplateCompiler()
    return compiler.compile(template_id, context)


def quick_compile(template_name: str, correlation_id: str, **kwargs) -> List[Dict]:
    """
    Quick compilation with string template names (case-insensitive)
    
    Args:
        template_name: Template name ('a', 'grounding', 'verification', etc.)
        correlation_id: Episode correlation ID
        **kwargs: Template context overrides
    
    Returns:
        List of compiled packets
    
    Example:
        packets = quick_compile("verification", "corr_001", stakes_level="HIGH")
    """
    template_map = {
        'a': TemplateID.GROUNDING_LOOP,
        'grounding': TemplateID.GROUNDING_LOOP,
        'grounding_loop': TemplateID.GROUNDING_LOOP,
        
        'b': TemplateID.VERIFICATION_LOOP,
        'verification': TemplateID.VERIFICATION_LOOP,
        'verification_loop': TemplateID.VERIFICATION_LOOP,
        'verify': TemplateID.VERIFICATION_LOOP,
        
        'c': TemplateID.READONLY_ACT,
        'readonly': TemplateID.READONLY_ACT,
        'readonly_act': TemplateID.READONLY_ACT,
        'read': TemplateID.READONLY_ACT,
        
        'd': TemplateID.WRITE_ACT,
        'write': TemplateID.WRITE_ACT,
        'write_act': TemplateID.WRITE_ACT,
        
        'e': TemplateID.ESCALATION,
        'escalation': TemplateID.ESCALATION,
        'escalate': TemplateID.ESCALATION,
        
        'f': TemplateID.DEGRADED_TOOLS,
        'degraded': TemplateID.DEGRADED_TOOLS,
        'degraded_tools': TemplateID.DEGRADED_TOOLS,
        
        'g': TemplateID.COMPILE_TO_CODE,
        'compile': TemplateID.COMPILE_TO_CODE,
        'compile_to_code': TemplateID.COMPILE_TO_CODE,
        'code': TemplateID.COMPILE_TO_CODE,
    }
    
    template_key = template_name.lower().strip()
    if template_key not in template_map:
        raise ValueError(f"Unknown template: {template_name}. Use: {', '.join(set(template_map.values()))}")
    
    return compile_template(template_map[template_key], correlation_id, **kwargs)
