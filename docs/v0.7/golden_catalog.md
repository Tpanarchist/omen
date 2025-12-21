# Golden Fixture Catalog v0.7

**OMEN Protocol Implementation: Test Fixture Manifest**

---

## Overview

This document catalogs all golden fixtures (test cases) for OMEN v0.7 packet protocol validation. Each fixture demonstrates valid/invalid packet structures and episode sequences per OMEN.md specification.

---

## Single-Packet Fixtures

### DecisionPacket.verify_first.json
**Path:** `goldens/v0.7/DecisionPacket.verify_first.json`  
**Type:** Valid  
**Spec Reference:** OMEN.md Section 15.2 (Lines 976-1040)

**Tests:**
- DecisionPacket with decision_outcome = VERIFY_FIRST
- MEDIUM stakes + HIGH uncertainty → verify-first per Q-POL
- PAR quality tier with verification_requirement = VERIFY_ONE
- Empty evidence_refs with explicit absence reason
- HYPOTHESIZED epistemic status (pre-verification)
- Load-bearing assumptions flagged as unverified

**Expected Validation:**
- Schema: PASS (all required fields present)
- FSM: PASS (legal from S2_MODEL to S3_DECIDE)
- Invariants: PASS (INV-001 through INV-012)

**Key Characteristics:**
- Demonstrates proper verification trigger
- Shows empty evidence_refs with justification
- Documents rejected alternatives with reasons

---

### DecisionPacket.act_readonly.json
**Path:** `goldens/v0.7/DecisionPacket.act_readonly.json`  
**Type:** Valid

**Tests:**
- DecisionPacket with decision_outcome = ACT
- LOW stakes + LOW uncertainty → immediate action permitted
- PAR tier (verification optional at low stakes)
- READ-only operation (no token required)
- DERIVED epistemic status with evidence from memory

**Expected Validation:**
- Schema: PASS
- FSM: PASS (leads to S6_EXECUTE with READ directive)
- Invariants: PASS

**Key Characteristics:**
- Shows low-stakes fast path
- Demonstrates read-only action authorization
- Evidence present from prior cached observation

---

### DecisionPacket.act_write.json
**Path:** `goldens/v0.7/DecisionPacket.act_write.json`  
**Type:** Valid

**Tests:**
- DecisionPacket with decision_outcome = ACT for WRITE operation
- HIGH stakes + LOW uncertainty (post-verification)
- SUPERB tier with all load-bearing assumptions verified
- OBSERVED epistemic status with fresh evidence
- Multiple evidence_refs from verification loop

**Expected Validation:**
- Schema: PASS
- FSM: PASS (requires S5_AUTHORIZE for token before S6_EXECUTE)
- Invariants: PASS (INV-003 compliance: HIGH stakes + verified assumptions + SUPERB)

**Key Characteristics:**
- Demonstrates HIGH stakes with successful verification
- All load-bearing assumptions have verification_packet_id
- Fresh REALTIME evidence within staleness window
- Proper failure mode documentation

---

### EscalationPacket.high_stakes_uncertainty.json
**Path:** `goldens/v0.7/EscalationPacket.high_stakes_uncertainty.json`  
**Type:** Valid

**Tests:**
- EscalationPacket with escalation_trigger = high_stakes_high_uncertainty
- CRITICAL stakes + HIGH uncertainty + HOSTILE adversariality
- 3 top_options with pros/cons/risk_summary
- Evidence gaps documented with impact_if_unknown
- Recommended next step with rationale
- INFERRED epistemic status (low confidence 0.35)
- tools_state = tools_partial

**Expected Validation:**
- Schema: PASS
- FSM: PASS (legal from S3_DECIDE to S8_ESCALATED)
- Invariants: PASS (INV-009: escalation structure requirements)

**Key Characteristics:**
- Shows mandatory escalation at CRITICAL + HIGH uncertainty
- Demonstrates proper option presentation (2-3 choices)
- Documents multiple evidence gaps
- Includes blocking_decision_packet_id for audit trail

---

### DecisionPacket.subpar_blocks_action.INVALID.json
**Path:** `goldens/v0.7/DecisionPacket.subpar_blocks_action.INVALID.json`  
**Type:** Invalid (expected failure)

**Tests:**
- DecisionPacket with SUBPAR tier attempting decision_outcome = ACT
- HIGH stakes + SUBPAR tier (policy violation)
- constraints_satisfied.constitutional_check = false

**Expected Validation:**
- Schema: PASS (structure valid)
- FSM: PASS (sequence valid)
- Invariants: FAIL (INV-002 violation: SUBPAR cannot authorize ACT)

**Key Characteristics:**
- Negative test case for INV-002
- Should fail with specific error: "SUBPAR tier cannot authorize ACT decision"
- Demonstrates policy enforcement over structural validity
- Includes `_validation_notes` documenting expected failure

---

## Episode Sequence Fixtures (JSONL)

### Episode.verify_loop.jsonl
**Path:** `goldens/v0.7/Episode.verify_loop.jsonl`  
**Type:** Valid  
**Template:** Template B (Verification Loop)  
**Spec Reference:** OMEN.md Section 15.3 (Lines 1042-1053)

**Sequence (8 packets):**
1. ObservationPacket (stale cache data)
2. BeliefUpdatePacket (staleness refresh)
3. DecisionPacket (VERIFY_FIRST due to staleness + uncertainty)
4. TaskDirectivePacket (READ verification)
5. TaskResultPacket (SUCCESS)
6. ObservationPacket (fresh OBSERVED evidence)
7. BeliefUpdatePacket (epistemic upgrade REMEMBERED → OBSERVED)
8. DecisionPacket (ACT after verification complete)

**Tests:**
- Complete verification loop closure (INV-008)
- Epistemic status progression: REMEMBERED → HYPOTHESIZED → OBSERVED
- Confidence calibration changes: 0.80 → 0.45 → 0.95 → 0.89
- Freshness class progression: STRATEGIC → OPERATIONAL → REALTIME
- Load-bearing assumption verification lifecycle
- Evidence_refs chaining across packets
- FSM state transitions: S1_SENSE → S2_MODEL → S3_DECIDE → S4_VERIFY → S6_EXECUTE → S1_SENSE → S2_MODEL → S3_DECIDE

**Expected Validation:**
- All packets: Schema PASS
- FSM: PASS (legal verification loop sequence)
- Invariants: PASS (INV-008: verification loop closure validated)

**Key Characteristics:**
- Demonstrates Template B canonical sequence
- Shows stale data triggering verification
- Documents epistemic upgrade path
- Proper task closure (directive → result pairing)

---

### Episode.degraded_tools_high_stakes.jsonl
**Path:** `goldens/v0.7/Episode.degraded_tools_high_stakes.jsonl`  
**Type:** Valid  
**Template:** Template F (Degraded Tools)

**Sequence (4 packets):**
1. ObservationPacket (system telemetry: tools_state = tools_partial)
2. BeliefUpdatePacket (system state update)
3. DecisionPacket (ESCALATE due to CRITICAL + tools_partial)
4. EscalationPacket (degraded tools escalation)

**Tests:**
- Degraded mode policy enforcement (INV-010)
- CRITICAL stakes + tools_partial → mandatory ESCALATE
- Proper escalation trigger: tools_degraded_critical
- Decision rationale referencing C-POL degraded mode rules
- Escalation options addressing degraded scenario

**Expected Validation:**
- Schema: PASS
- FSM: PASS (S1_SENSE → S2_MODEL → S3_DECIDE → S8_ESCALATED)
- Invariants: PASS (INV-010: tools_partial + CRITICAL → no ACT)

**Key Characteristics:**
- Shows Template F degraded tools handling
- Demonstrates safety-first posture under degradation
- Documents proper escalation trigger selection
- Options include "defer until tools_ok" recommendation

---

### Episode.write_with_token.jsonl
**Path:** `goldens/v0.7/Episode.write_with_token.jsonl`  
**Type:** Valid  
**Template:** Template D (Write Act)

**Sequence (7 packets):**
1. ToolAuthorizationToken (Layer 1 issues write authorization)
2. DecisionPacket (ACT with HIGH stakes, SUPERB tier, verified assumptions)
3. TaskDirectivePacket (WRITE operation with authorization_token_id)
4. TaskResultPacket (SUCCESS)
5. ObservationPacket (write confirmation)
6. BeliefUpdatePacket (integrate write results)

**Tests:**
- Token authorization flow (INV-007)
- Token issuance by Layer 1 with proper scope
- Token scope containment check (tool_id, operation_types, resource_constraints)
- Write directive requires valid token
- Token expiry validation (future timestamp)
- Token usage_count tracking (0 before use)
- HIGH stakes + SUPERB tier + verified assumptions → write permitted
- All load-bearing assumptions have verification_packet_id

**Expected Validation:**
- Schema: PASS
- FSM: PASS (S5_AUTHORIZE → S6_EXECUTE flow)
- Invariants: PASS (INV-007: token validation complete)

**Key Characteristics:**
- Shows Template D write authorization sequence
- Demonstrates token lifecycle (issue → use → result)
- Token includes rationale for audit trail
- Write operation produces observable outcome
- Belief integration closes the loop

---

## Fixture Usage Guidelines

### For Schema Validators
1. Load fixture JSON/JSONL
2. Parse each packet
3. Validate against appropriate schema (PacketHeader, MCP, packet-specific)
4. Check required field presence
5. Validate enums, patterns, ranges
6. Expect PASS/FAIL per fixture type

### For FSM Validators
1. Load episode sequence (JSONL)
2. Initialize FSM with S0_IDLE
3. Process packets in order
4. Check transitions against fsm_transitions.md
5. Track state changes
6. Expect legal sequence completion

### For Invariant Validators
1. Load episode sequence
2. Build episode ledger (budgets, tokens, open directives, evidence)
3. Apply invariant checks per invariant_rules.md
4. Check for specific violation codes (INV-001 through INV-012)
5. Invalid fixtures should fail with documented error

### For Integration Tests
1. Use valid episodes as happy-path tests
2. Use invalid fixtures as negative tests
3. Verify error messages match documented violations
4. Test budget tracking across episode
5. Test token lifecycle and scope validation
6. Test escalation option generation

---

## Fixture Naming Convention

**Single packets:**
`{PacketType}.{scenario}.json` or `{PacketType}.{scenario}.INVALID.json`

**Episode sequences:**
`Episode.{template_or_scenario}.jsonl`

**Examples:**
- Valid: `DecisionPacket.verify_first.json`
- Invalid: `DecisionPacket.subpar_blocks_action.INVALID.json`
- Sequence: `Episode.verify_loop.jsonl`

---

## Coverage Matrix

| Policy | Fixture(s) | Validation Point |
|--------|-----------|------------------|
| INV-001 (MCP completeness) | All valid fixtures | All fields present |
| INV-002 (SUBPAR blocks ACT) | subpar_blocks_action.INVALID | Expected failure |
| INV-003 (HIGH/CRITICAL verification) | act_write, degraded_tools | Verified assumptions |
| INV-004 (Evidence required) | verify_first | Evidence absence reason |
| INV-005 (Budget overruns) | — | (Future fixture) |
| INV-006 (Drive arbitration) | All decisions | Constraints satisfied |
| INV-007 (Token validation) | write_with_token | Token scope containment |
| INV-008 (Verification closure) | verify_loop | Complete loop sequence |
| INV-009 (Escalation structure) | high_stakes_uncertainty | Options + gaps + recommendation |
| INV-010 (Degraded tools) | degraded_tools_high_stakes | tools_partial → ESCALATE |
| INV-011 (Task closure) | All episodes with directives | Directive → Result pairing |
| INV-012 (Stakes consistency) | All valid fixtures | Stakes_level ↔ axes |

---

## Future Fixtures (Planned)

- `Episode.budget_overrun.jsonl` — Tests INV-005 budget enforcement
- `DecisionPacket.tier_mismatch.INVALID.json` — HIGH stakes with PAR tier (should fail)
- `TaskDirectivePacket.missing_token.INVALID.json` — WRITE without token
- `Episode.contradiction_resolution.jsonl` — Belief conflict handling
- `Episode.safe_mode_trigger.jsonl` — IntegrityAlertPacket → S9_SAFEMODE
- `ToolAuthorizationToken.expired.INVALID.json` — Token expiry enforcement
- `Episode.nested_episodes.jsonl` — Campaign with multiple sub-episodes

---

## References

- OMEN.md Section 10: Episode State Machine (Lines 805-867)
- OMEN.md Section 11: Episode Templates (Lines 869-920)
- OMEN.md Section 15: Appendices (Lines 976-1087)
- Individual fixture files in `goldens/v0.7/`
