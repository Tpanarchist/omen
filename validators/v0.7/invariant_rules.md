# Cross-Policy Invariant Rules v0.7

**Normative Document:** Cross-Policy Invariants (OMEN.md Section 8.4, Lines 694-709)

---

## Overview

These are **deterministic checks** that validators MUST enforce across packet sequences. They implement E-POL, Q-POL, and C-POL constraints that JSON Schema alone cannot express.

Each invariant has:
1. **Rule ID** (unique identifier)
2. **Policy source** (which policy this enforces)
3. **Condition** (when the check applies)
4. **Assertion** (what must be true)
5. **Enforcement** (how validators detect violations)
6. **Failure mode** (what happens if violated)

---

## Invariant Catalog

### INV-001: MCP Completeness
**Policy:** E-POL, Q-POL, C-POL (OMEN.md Line 695)

**Condition:** Every consequential packet (Decision, TaskDirective, Authorization, Escalation)

**Assertion:** MCP envelope MUST be fully populated with:
- intent.summary, intent.scope
- stakes (all four axes + stakes_level)
- quality (tier, satisficing_mode, definition_of_done, verification_requirement)
- budgets (token, tool_call, time, risk)
- epistemics (status, confidence, calibration_note, freshness_class, assumptions)
- evidence (refs or absent_reason)
- routing (task_class, tools_state)

**Enforcement:**
```python
def check_inv_001(packet):
    if packet.header.packet_type not in CONSEQUENTIAL_TYPES:
        return True  # N/A
    
    required_fields = [
        "mcp.intent.summary", "mcp.intent.scope",
        "mcp.stakes.impact", "mcp.stakes.irreversibility", 
        "mcp.stakes.uncertainty", "mcp.stakes.adversariality", "mcp.stakes.stakes_level",
        "mcp.quality.quality_tier", "mcp.quality.satisficing_mode",
        "mcp.quality.definition_of_done.text", "mcp.quality.definition_of_done.checks",
        "mcp.quality.verification_requirement",
        "mcp.budgets.token_budget", "mcp.budgets.tool_call_budget",
        "mcp.budgets.time_budget_seconds", "mcp.budgets.risk_budget",
        "mcp.epistemics.status", "mcp.epistemics.confidence",
        "mcp.epistemics.calibration_note", "mcp.epistemics.freshness_class",
        "mcp.epistemics.assumptions",
        "mcp.evidence.evidence_refs",
        "mcp.routing.task_class", "mcp.routing.tools_state"
    ]
    
    for field_path in required_fields:
        if not has_field(packet, field_path):
            return ValidationError(f"INV-001: Missing required field {field_path}")
    
    # Special case: evidence_absent_reason required if evidence_refs empty
    if len(packet.mcp.evidence.evidence_refs) == 0:
        if not packet.mcp.evidence.evidence_absent_reason:
            return ValidationError("INV-001: evidence_absent_reason required when evidence_refs empty")
    
    return True
```

**Failure:** Reject packet with INV-001 violation.

---

### INV-002: SUBPAR Never Authorizes Action
**Policy:** Q-POL (OMEN.md Line 697)

**Condition:** DecisionPacket with quality_tier = SUBPAR

**Assertion:** decision_outcome MUST NOT be ACT

**Enforcement:**
```python
def check_inv_002(decision_packet):
    if decision_packet.mcp.quality.quality_tier == "SUBPAR":
        if decision_packet.payload.decision_outcome == "ACT":
            return ValidationError("INV-002: SUBPAR tier cannot authorize ACT decision")
    return True
```

**Rationale:** SUBPAR outputs are speculative/exploratory; cannot commit to external actions.

**Failure:** Reject DecisionPacket; episode must escalate, verify, or defer.

---

### INV-003: HIGH/CRITICAL Requires Verification or Escalation
**Policy:** Q-POL (OMEN.md Line 699)

**Condition:** DecisionPacket with stakes_level ∈ {HIGH, CRITICAL}

**Assertion:** One of:
1. decision_outcome = VERIFY_FIRST, OR
2. decision_outcome = ESCALATE, OR
3. quality_tier = SUPERB AND all load_bearing_assumptions verified=true, OR
4. Layer 1 explicit emergency override (recorded in rationale)

**Enforcement:**
```python
def check_inv_003(decision_packet, episode_ledger):
    stakes = decision_packet.mcp.stakes.stakes_level
    if stakes not in ["HIGH", "CRITICAL"]:
        return True  # N/A
    
    outcome = decision_packet.payload.decision_outcome
    tier = decision_packet.mcp.quality.quality_tier
    
    if outcome in ["VERIFY_FIRST", "ESCALATE"]:
        return True  # Compliant
    
    if outcome == "ACT":
        if tier != "SUPERB":
            return ValidationError("INV-003: HIGH/CRITICAL stakes require SUPERB tier for ACT")
        
        # Check all load-bearing assumptions verified
        assumptions = decision_packet.payload.get("load_bearing_assumptions", [])
        for assumption in assumptions:
            if not assumption.get("verified"):
                return ValidationError(f"INV-003: Unverified assumption '{assumption['assumption']}' at HIGH/CRITICAL stakes")
        
        return True
    
    # DEFER or CANCEL allowed but should have rationale
    return True
```

**Failure:** Reject DecisionPacket; force VERIFY_FIRST or ESCALATE.

---

### INV-004: LLM Cannot Claim Live Truth Without Evidence
**Policy:** E-POL (OMEN.md Line 701)

**Condition:** Any packet with epistemic_status ∈ {INFERRED, HYPOTHESIZED, UNKNOWN}

**Assertion:** If asserting current state (freshness_class ∈ {REALTIME, OPERATIONAL}), evidence_refs MUST contain at least one tool_output or user_observation from recent time window.

**Enforcement:**
```python
def check_inv_004(packet):
    status = packet.mcp.epistemics.status
    freshness = packet.mcp.epistemics.freshness_class
    
    if status in ["OBSERVED", "DERIVED", "REMEMBERED"]:
        return True  # These are grounded
    
    if status in ["INFERRED", "HYPOTHESIZED", "UNKNOWN"]:
        if freshness in ["REALTIME", "OPERATIONAL"]:
            refs = packet.mcp.evidence.evidence_refs
            has_recent_evidence = any(
                ref.ref_type in ["tool_output", "user_observation"]
                for ref in refs
            )
            if not has_recent_evidence:
                return ValidationError("INV-004: Cannot infer/hypothesize current state without tool evidence")
    
    return True
```

**Failure:** Downgrade epistemic status or require verification.

---

### INV-005: Budget Overruns Require Approval
**Policy:** Q-POL (OMEN.md Line 703)

**Condition:** Episode cumulative resource usage exceeds budgets

**Assertion:** If any budget exceeded:
- tokens_used > token_budget
- tool_calls_used > tool_call_budget
- time_elapsed > time_budget_seconds
- risk_spent > risk_budget

Then either:
1. EscalationPacket with escalation_trigger = "budget_insufficient", OR
2. Layer 1 approval (ToolAuthorizationToken or IntegrityAlertPacket with override rationale)

**Enforcement:**
```python
def check_inv_005(episode_ledger):
    budgets = episode_ledger.initial_budgets
    usage = episode_ledger.cumulative_usage
    
    overruns = []
    if usage.tokens > budgets.token_budget:
        overruns.append(f"tokens: {usage.tokens} > {budgets.token_budget}")
    if usage.tool_calls > budgets.tool_call_budget:
        overruns.append(f"tool_calls: {usage.tool_calls} > {budgets.tool_call_budget}")
    if usage.time_seconds > budgets.time_budget_seconds:
        overruns.append(f"time: {usage.time_seconds} > {budgets.time_budget_seconds}")
    
    if overruns:
        has_escalation = any(
            p.header.packet_type == "EscalationPacket"
            for p in episode_ledger.recent_packets
        )
        has_override = any(
            p.header.layer_source == 1 and "budget override" in str(p.payload)
            for p in episode_ledger.recent_packets
        )
        
        if not (has_escalation or has_override):
            return ValidationError(f"INV-005: Budget overrun without approval: {overruns}")
    
    return True
```

**Failure:** Halt episode; force escalation or safe mode.

---

### INV-006: Drive Arbitration Sequence
**Policy:** Drive Arbitration (OMEN.md Lines 705-709)

**Condition:** DecisionPacket following a conflict (multiple viable options)

**Assertion:** Decision MUST document:
1. Stage 1 veto check (constitutional_check = true)
2. Stage 2 feasibility check (budget_check = true)
3. Stage 3 tradeoff policy applied (rationale references policy: safety-first, risk-adjusted, min-regret)

**Enforcement:**
```python
def check_inv_006(decision_packet):
    constraints = decision_packet.payload.get("constraints_satisfied", {})
    
    if not constraints.get("constitutional_check"):
        return ValidationError("INV-006: Stage 1 veto failed; decision invalid")
    
    if not constraints.get("budget_check"):
        return ValidationError("INV-006: Stage 2 feasibility failed; decision invalid")
    
    # Stage 3: decision_summary should reference tradeoff policy
    summary = decision_packet.payload.get("decision_summary", "")
    has_tradeoff_rationale = any(
        keyword in summary.lower()
        for keyword in ["safety", "risk-adjusted", "min-regret", "expected value"]
    )
    
    if not has_tradeoff_rationale:
        return ValidationWarning("INV-006: Stage 3 tradeoff policy not documented in decision_summary")
    
    return True
```

**Failure:** Reject decision; require explicit tradeoff rationale.

---

### INV-007: WRITE Requires Token Scope Containment
**Policy:** C-POL (OMEN.md Lines 661-668)

**Condition:** TaskDirectivePacket with tool_safety_class ∈ {WRITE, MIXED}

**Assertion:**
1. authorization_token_id MUST reference valid ToolAuthorizationToken in episode
2. Token expiry MUST be in future
3. Token revoked MUST be false
4. Token usage_count < max_usage_count
5. Directive scope ⊆ token scope:
   - tool_id ∈ token.authorized_scope.tool_ids
   - operation ∈ token.authorized_scope.operation_types
   - resource constraints satisfied

**Enforcement:**
```python
def check_inv_007(directive_packet, episode_ledger):
    if directive_packet.payload.tool_safety_class not in ["WRITE", "MIXED"]:
        return True  # N/A
    
    token_id = directive_packet.payload.get("authorization_token_id")
    if not token_id:
        return ValidationError("INV-007: WRITE directive requires authorization_token_id")
    
    token = episode_ledger.find_token(token_id)
    if not token:
        return ValidationError(f"INV-007: Token {token_id} not found in episode")
    
    if token.payload.revoked:
        return ValidationError(f"INV-007: Token {token_id} revoked")
    
    if token.payload.usage_count >= token.payload.max_usage_count:
        return ValidationError(f"INV-007: Token {token_id} usage exhausted")
    
    now = datetime.utcnow()
    if parse_datetime(token.payload.expiry) < now:
        return ValidationError(f"INV-007: Token {token_id} expired")
    
    # Scope containment
    tool_id = directive_packet.payload.execution_method.tool_id
    if tool_id not in token.payload.authorized_scope.tool_ids:
        return ValidationError(f"INV-007: Tool {tool_id} not in token scope")
    
    # More checks for operation_types, resource_constraints...
    
    return True
```

**Failure:** Reject TaskDirective; require valid token.

---

### INV-008: Verification Loop Closure
**Policy:** E-POL, Q-POL (OMEN.md Section 10.4.2, Lines 841-849)

**Condition:** Episode in S4_VERIFY state

**Assertion:** Before transitioning back to S3_DECIDE:
1. VerificationPlanPacket MUST exist
2. At least one TaskDirective with tool_safety_class = READ executed
3. At least one TaskResult with result_status = SUCCESS (if tools_state = tools_ok)
4. At least one ObservationPacket with status = OBSERVED
5. BeliefUpdatePacket MUST reference verification evidence

**Enforcement:**
```python
def check_inv_008(episode_ledger, new_decision_packet):
    if episode_ledger.current_state != "S4_VERIFY":
        return True  # N/A
    
    packets = episode_ledger.packets_since_verify_start
    
    has_plan = any(p.header.packet_type == "VerificationPlanPacket" for p in packets)
    if not has_plan:
        return ValidationError("INV-008: No VerificationPlanPacket in verify loop")
    
    has_read_directive = any(
        p.header.packet_type == "TaskDirectivePacket" and
        p.payload.tool_safety_class == "READ"
        for p in packets
    )
    if not has_read_directive:
        return ValidationError("INV-008: No READ TaskDirective in verify loop")
    
    if episode_ledger.tools_state == "tools_ok":
        has_success_result = any(
            p.header.packet_type == "TaskResultPacket" and
            p.payload.result_status == "SUCCESS"
            for p in packets
        )
        if not has_success_result:
            return ValidationError("INV-008: No successful TaskResult in verify loop with tools_ok")
    
    has_observation = any(
        p.header.packet_type == "ObservationPacket" and
        p.mcp.epistemics.status == "OBSERVED"
        for p in packets
    )
    if not has_observation:
        return ValidationError("INV-008: No OBSERVED evidence in verify loop")
    
    has_belief_update = any(
        p.header.packet_type == "BeliefUpdatePacket" and
        len(set(p.payload.evidence_integration) & {pkt.header.packet_id for pkt in packets}) > 0
        for p in packets
    )
    if not has_belief_update:
        return ValidationError("INV-008: No BeliefUpdate referencing verification evidence")
    
    return True
```

**Failure:** Reject decision; force completion of verification loop.

---

### INV-009: Escalation Must Present Options
**Policy:** Q-POL (OMEN.md Lines 527-537)

**Condition:** EscalationPacket

**Assertion:**
1. top_options MUST contain 2-3 items
2. Each option MUST have: option_id, description, pros[], cons[]
3. evidence_gaps MUST be non-empty
4. recommended_next_step MUST be present

**Enforcement:**
```python
def check_inv_009(escalation_packet):
    options = escalation_packet.payload.get("top_options", [])
    if not (2 <= len(options) <= 3):
        return ValidationError("INV-009: Escalation requires 2-3 top_options")
    
    for opt in options:
        required = ["option_id", "description", "pros", "cons"]
        for field in required:
            if field not in opt:
                return ValidationError(f"INV-009: Option missing field {field}")
    
    gaps = escalation_packet.payload.get("evidence_gaps", [])
    if not gaps:
        return ValidationError("INV-009: Escalation requires evidence_gaps")
    
    if not escalation_packet.payload.get("recommended_next_step"):
        return ValidationError("INV-009: Escalation requires recommended_next_step")
    
    return True
```

**Failure:** Reject EscalationPacket; force completion.

---

### INV-010: Degraded Tools Policy
**Policy:** C-POL (OMEN.md Lines 681-690)

**Condition:** tools_state ∈ {tools_partial, tools_down}

**Assertion:** Decision behavior depends on stakes:
- tools_down + stakes ∈ {HIGH, CRITICAL} → decision_outcome MUST be ESCALATE or CANCEL (not ACT)
- tools_partial + stakes = MEDIUM → decision MAY proceed with increased uncertainty labeling
- tools_ok → normal rules apply

**Enforcement:**
```python
def check_inv_010(decision_packet):
    tools_state = decision_packet.mcp.routing.tools_state
    stakes = decision_packet.mcp.stakes.stakes_level
    outcome = decision_packet.payload.decision_outcome
    
    if tools_state == "tools_down" and stakes in ["HIGH", "CRITICAL"]:
        if outcome == "ACT":
            return ValidationError("INV-010: tools_down + HIGH/CRITICAL stakes cannot ACT")
    
    if tools_state == "tools_partial" and stakes == "MEDIUM":
        # Check that uncertainty is acknowledged
        if decision_packet.mcp.epistemics.uncertainty != "HIGH":
            return ValidationWarning("INV-010: tools_partial should increase uncertainty labeling")
    
    return True
```

**Failure:** Reject ACT decision at high stakes with degraded tools.

---

### INV-011: Task Closure
**Policy:** Lifecycle Rules (OMEN.md Line 837)

**Condition:** TaskDirectivePacket emitted

**Assertion:** Within time_budget_seconds, a TaskResultPacket with matching task_id and result_status ∈ {SUCCESS, FAILURE, CANCELLED} MUST appear.

**Enforcement:**
```python
def check_inv_011(episode_ledger):
    open_directives = episode_ledger.open_directives
    now = datetime.utcnow()
    
    for directive in open_directives:
        elapsed = (now - directive.header.created_at).total_seconds()
        timeout = directive.payload.get("timeout_seconds", directive.mcp.budgets.time_budget_seconds)
        
        if elapsed > timeout:
            return ValidationError(f"INV-011: TaskDirective {directive.payload.task_id} timed out without result")
    
    return True
```

**Failure:** Emit timeout warning; eventual escalation if critical.

---

### INV-012: Stakes Consistency
**Policy:** Q-POL (OMEN.md Lines 475-483)

**Condition:** All packets with stakes

**Assertion:** stakes_level MUST be consistent with component axes:
- stakes_level = CRITICAL → at least one axis CRITICAL or (impact HIGH + irreversibility IRREVERSIBLE + uncertainty HIGH)
- stakes_level = HIGH → at least two axes HIGH or one CRITICAL
- stakes_level = MEDIUM → at least one axis MEDIUM or HIGH
- stakes_level = LOW → all axes LOW or one MEDIUM

**Enforcement:**
```python
def check_inv_012(packet):
    stakes = packet.mcp.stakes
    level = stakes.stakes_level
    axes = [stakes.impact, stakes.irreversibility, stakes.uncertainty, stakes.adversariality]
    
    if level == "CRITICAL":
        if not ("CRITICAL" in axes or (stakes.impact == "HIGH" and stakes.irreversibility == "IRREVERSIBLE")):
            return ValidationWarning("INV-012: stakes_level CRITICAL but axes don't justify it")
    
    # More checks for other levels...
    
    return True
```

**Failure:** Warning (soft constraint); flag for review.

---

## Validator Integration

**Order of checks:**
1. JSON Schema validation (structure, types, enums)
2. FSM transition check (legal packet sequence)
3. Invariant checks (cross-policy rules)
4. Ledger update (evidence refs, budgets, tokens)

**Failure handling:**
- Schema violation → reject immediately
- FSM violation → reject immediately
- Invariant ERROR → reject immediately
- Invariant WARNING → log but allow (flag for review)

---

## References

- OMEN.md Section 8.4: Cross-Policy Invariants (Lines 694-709)
- OMEN.md Section 8.1: E-POL (Lines 408-479)
- OMEN.md Section 8.2: Q-POL (Lines 475-537)
- OMEN.md Section 8.3: C-POL (Lines 539-690)
- OMEN.md Section 10.4: Lifecycle Rules (Lines 835-867)
