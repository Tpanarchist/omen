# FSM Transition Validator Specification v0.7

**Normative Document:** Episode State Machine & Legal Transitions (OMEN.md Section 10, Lines 805-815)

---

## Overview

Episodes follow a finite state machine (FSM) controlling packet sequence validity. This spec defines:

1. **State definitions** (what each state means)
2. **Legal transitions** (allowed packet type sequences)
3. **State-packet mappings** (which packets move between states)
4. **Enforcement rules** (how validators check sequences)

---

## FSM States

Per OMEN.md Lines 805-815:

### S0_IDLE
**Semantics:** Episode has not begun processing; waiting for initial stimulus.

**Entry conditions:**
- Episode created with correlation_id allocated
- No packets yet emitted

**Legal next states:** S1_SENSE

---

### S1_SENSE
**Semantics:** Gathering observations from tools, sensors, or user input.

**Entry conditions:**
- From S0_IDLE: initial observation triggers episode start
- From S7_REVIEW: new observation triggers another cycle

**Legal next states:** S2_MODEL, S9_SAFEMODE

**Typical packets in this state:**
- ObservationPacket (sensor/tool reads, user observations)

---

### S2_MODEL
**Semantics:** Updating world model based on observations; belief revision.

**Entry conditions:**
- From S1_SENSE: observations require belief integration
- From S4_VERIFY: verification results require belief updates

**Legal next states:** S3_DECIDE, S9_SAFEMODE

**Typical packets in this state:**
- BeliefUpdatePacket (belief changes, contradiction resolution, confidence adjustments)

---

### S3_DECIDE
**Semantics:** Layer 5 arbitration and decision-making.

**Entry conditions:**
- From S2_MODEL: beliefs updated, ready for decision
- From S4_VERIFY: re-deciding after verification complete

**Legal next states:** S4_VERIFY, S5_AUTHORIZE, S6_EXECUTE, S8_ESCALATED, S9_SAFEMODE

**Typical packets in this state:**
- DecisionPacket (VERIFY_FIRST, ACT, ESCALATE, DEFER, CANCEL)

**Transition rules:**
- `decision_outcome = VERIFY_FIRST` → S4_VERIFY
- `decision_outcome = ACT` + tool_safety_class = WRITE → S5_AUTHORIZE
- `decision_outcome = ACT` + tool_safety_class = READ → S6_EXECUTE
- `decision_outcome = ESCALATE` → S8_ESCALATED
- `decision_outcome = DEFER` → S7_REVIEW
- `decision_outcome = CANCEL` → S7_REVIEW

---

### S4_VERIFY
**Semantics:** Executing verification plan; gathering evidence for load-bearing assumptions.

**Entry conditions:**
- From S3_DECIDE: DecisionPacket with decision_outcome = VERIFY_FIRST

**Legal next states:** S6_EXECUTE, S2_MODEL, S9_SAFEMODE

**Typical packets in this state:**
- VerificationPlanPacket (defines what to verify)
- TaskDirectivePacket (READ operations only)
- TaskResultPacket (verification results)
- ObservationPacket (evidence collected)

**Required sequence before leaving S4_VERIFY:**
1. VerificationPlanPacket MUST appear
2. At least one TaskDirectivePacket with tool_safety_class = READ MUST appear
3. At least one TaskResultPacket with result_status = SUCCESS MUST appear (when tools_state = tools_ok)
4. At least one ObservationPacket with epistemic_status = OBSERVED MUST appear
5. Transition to S2_MODEL MUST occur with BeliefUpdatePacket referencing verification evidence

**Enforcement:** Validator MUST reject any transition from S4_VERIFY to S3_DECIDE unless all required packets present.

---

### S5_AUTHORIZE
**Semantics:** Issuing authorization token for WRITE/MIXED tool usage.

**Entry conditions:**
- From S3_DECIDE: DecisionPacket with decision_outcome = ACT + directive requires tool_safety_class = WRITE or MIXED

**Legal next states:** S6_EXECUTE, S9_SAFEMODE

**Typical packets in this state:**
- ToolAuthorizationToken (token issuance with scope, expiry, max_usage_count)

**Required sequence before leaving S5_AUTHORIZE:**
1. ToolAuthorizationToken MUST be emitted
2. Token MUST have valid scope, expiry, max_usage_count
3. Token expiry MUST be in the future
4. Token revoked MUST be false

**Enforcement:** Validator MUST reject any transition to S6_EXECUTE with WRITE directive unless valid token exists in episode ledger.

---

### S6_EXECUTE
**Semantics:** Layer 6 execution of tool calls, computations, or read operations.

**Entry conditions:**
- From S3_DECIDE: ACT decision with READ operations
- From S5_AUTHORIZE: ACT decision with WRITE operations and token issued
- From S4_VERIFY: verification directives ready for execution

**Legal next states:** S7_REVIEW, S2_MODEL, S9_SAFEMODE

**Typical packets in this state:**
- TaskDirectivePacket (tool/code/llm execution directives)
- TaskResultPacket (execution results)
- ObservationPacket (result data as observations)

**Required sequence before leaving S6_EXECUTE:**
1. Every TaskDirectivePacket MUST have corresponding TaskResultPacket
2. TaskResultPacket MUST have result_status ∈ {SUCCESS, FAILURE, CANCELLED}
3. If tool_safety_class = WRITE: authorization_token_id MUST reference valid token in ledger
4. Token usage_count MUST NOT exceed max_usage_count

**Enforcement:** Validator MUST reject dangling directives (TaskDirective without TaskResult).

---

### S7_REVIEW
**Semantics:** Post-execution review; logging outcomes, updating doctrine, closing episode.

**Entry conditions:**
- From S6_EXECUTE: execution complete
- From S3_DECIDE: DEFER or CANCEL outcome

**Legal next states:** S0_IDLE, S1_SENSE (if triggering new cycle), S9_SAFEMODE

**Typical packets in this state:**
- BeliefUpdatePacket (lessons learned, doctrine updates)
- IntegrityAlertPacket (if anomalies detected)

**Episode closure:** Episodes MAY close from S7_REVIEW if definition_of_done satisfied.

---

### S8_ESCALATED
**Semantics:** Human decision or Layer 1 override required; waiting for external input.

**Entry conditions:**
- From S3_DECIDE: DecisionPacket with decision_outcome = ESCALATE

**Legal next states:** S3_DECIDE (after human input), S9_SAFEMODE

**Typical packets in this state:**
- EscalationPacket (options, gaps, recommendation)

**Required sequence before leaving S8_ESCALATED:**
1. EscalationPacket MUST be emitted
2. top_options MUST contain 2-3 options
3. evidence_gaps MUST be non-empty
4. recommended_next_step MUST be present

**Enforcement:** Validator MUST wait for user input before allowing transition back to S3_DECIDE.

---

### S9_SAFEMODE
**Semantics:** Emergency halt; all operations suspended pending Integrity override.

**Entry conditions:**
- From ANY state: IntegrityAlertPacket with severity = CRITICAL
- From ANY state: budget overrun detected
- From ANY state: constitutional violation detected

**Legal next states:** S0_IDLE (after recovery), S7_REVIEW (if episode cancelled)

**Typical packets in this state:**
- IntegrityAlertPacket (reason for safe mode)

**Enforcement:** NO packets except IntegrityAlertPacket and BeliefUpdatePacket (for logging) allowed in S9_SAFEMODE.

---

## Transition Table (Normative)

| From State     | Packet Type                  | To State       | Conditions                                                                 |
|----------------|------------------------------|----------------|---------------------------------------------------------------------------|
| S0_IDLE        | ObservationPacket            | S1_SENSE       | Initial observation                                                       |
| S1_SENSE       | ObservationPacket            | S1_SENSE       | Multiple observations allowed                                             |
| S1_SENSE       | BeliefUpdatePacket           | S2_MODEL       | Observations trigger belief update                                        |
| S2_MODEL       | BeliefUpdatePacket           | S2_MODEL       | Multiple belief updates allowed                                           |
| S2_MODEL       | DecisionPacket               | S3_DECIDE      | Beliefs ready for decision                                                |
| S3_DECIDE      | DecisionPacket (VERIFY_FIRST)| S4_VERIFY      | Decision requires verification                                            |
| S3_DECIDE      | ToolAuthorizationToken       | S5_AUTHORIZE   | Decision = ACT + WRITE directive                                          |
| S3_DECIDE      | TaskDirectivePacket (READ)   | S6_EXECUTE     | Decision = ACT + READ directive                                           |
| S3_DECIDE      | EscalationPacket             | S8_ESCALATED   | Decision = ESCALATE                                                       |
| S3_DECIDE      | BeliefUpdatePacket           | S7_REVIEW      | Decision = DEFER or CANCEL                                                |
| S4_VERIFY      | VerificationPlanPacket       | S4_VERIFY      | Plan emitted; still in verify state                                       |
| S4_VERIFY      | TaskDirectivePacket (READ)   | S4_VERIFY      | Verification directives                                                   |
| S4_VERIFY      | TaskResultPacket             | S4_VERIFY      | Verification results                                                      |
| S4_VERIFY      | ObservationPacket            | S4_VERIFY      | Evidence collected                                                        |
| S4_VERIFY      | BeliefUpdatePacket           | S2_MODEL       | Verification complete; beliefs updated                                    |
| S5_AUTHORIZE   | ToolAuthorizationToken       | S5_AUTHORIZE   | Token issued; still in authorize state                                    |
| S5_AUTHORIZE   | TaskDirectivePacket (WRITE)  | S6_EXECUTE     | Token valid; proceed to execution                                         |
| S6_EXECUTE     | TaskDirectivePacket          | S6_EXECUTE     | Multiple directives allowed                                               |
| S6_EXECUTE     | TaskResultPacket             | S6_EXECUTE     | Results streaming                                                         |
| S6_EXECUTE     | ObservationPacket            | S6_EXECUTE     | Result observations                                                       |
| S6_EXECUTE     | BeliefUpdatePacket           | S7_REVIEW      | Execution complete; integrate results                                     |
| S6_EXECUTE     | BeliefUpdatePacket           | S2_MODEL       | Execution partial; need re-decision                                       |
| S7_REVIEW      | BeliefUpdatePacket           | S7_REVIEW      | Doctrine updates                                                          |
| S7_REVIEW      | (episode close)              | S0_IDLE        | Episode complete                                                          |
| S8_ESCALATED   | EscalationPacket             | S8_ESCALATED   | Escalation presented                                                      |
| S8_ESCALATED   | (user input)                 | S3_DECIDE      | User provides decision                                                    |
| ANY            | IntegrityAlertPacket (CRITICAL)| S9_SAFEMODE  | Emergency halt                                                            |
| S9_SAFEMODE    | IntegrityAlertPacket (clear) | S7_REVIEW      | Recovery or cancellation                                                  |

---

## Enforcement Rules

### Rule E1: No Decision Without Model
DecisionPacket MUST be preceded by at least one BeliefUpdatePacket in the episode (unless episode just started and initial beliefs exist from prior context).

### Rule E2: No Action Without Decision
TaskDirectivePacket MUST be preceded by DecisionPacket with decision_outcome = ACT within same episode.

### Rule E3: Verification Loop Must Complete
If DecisionPacket has decision_outcome = VERIFY_FIRST:
1. VerificationPlanPacket MUST appear before any TaskDirective
2. At least one TaskDirective with tool_safety_class = READ MUST execute
3. At least one TaskResult with result_status = SUCCESS MUST appear (if tools_ok)
4. BeliefUpdatePacket MUST appear referencing verification evidence
5. Second DecisionPacket MUST appear (re-decide post-verification)

### Rule E4: Write Requires Token
TaskDirectivePacket with tool_safety_class = WRITE or MIXED MUST:
1. Be preceded by ToolAuthorizationToken in same episode
2. authorization_token_id MUST match token_id from ToolAuthorizationToken
3. Token expiry MUST NOT be in the past
4. Token revoked MUST be false
5. Token usage_count < max_usage_count

### Rule E5: Escalation Must Present Options
EscalationPacket MUST contain:
1. top_options with 2-3 items
2. evidence_gaps with at least 1 item
3. recommended_next_step

### Rule E6: Task Closure
Every TaskDirectivePacket MUST eventually have corresponding TaskResultPacket (SUCCESS, FAILURE, or CANCELLED) within time_budget_seconds or trigger timeout escalation.

### Rule E7: Safe Mode Lockdown
In S9_SAFEMODE: only IntegrityAlertPacket and BeliefUpdatePacket (logging) allowed. No TaskDirectives or Decisions permitted.

---

## Validator Implementation Notes

**Stateful validation required:** FSM validator must track:
- Current state per episode (correlation_id)
- Open TaskDirectives awaiting results
- Active tokens with usage counts
- Verification loops in progress (awaiting completion before allowing re-decide)

**Validation sequence:**
1. **Schema validation** (JSON Schema per packet type)
2. **FSM transition check** (is this packet_type legal from current state?)
3. **Sequence invariant check** (are required predecessors present? e.g., token for WRITE)
4. **State update** (move to next state; update ledger)

**Failure handling:**
- Invalid transition → reject packet; emit validation error
- Missing prerequisite (e.g., token) → reject with specific error
- Dangling directive → timeout warning; eventual escalation

---

## References

- OMEN.md Section 10.2: FSM States (Lines 805-815)
- OMEN.md Section 10.3: Legal Transitions (Lines 817-820)
- OMEN.md Section 10.4: Lifecycle Rules (Lines 835-867)
