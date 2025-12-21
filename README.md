# OMEN v0.7 Protocol Implementation

**Schema-First Implementation: JSON Schemas, Golden Fixtures, and Validator Specifications**

---

## What's Been Built

This implementation breaks ground on OMEN protocol v0.7 per the "schemas + goldens first" principle. Everything downstream (FSM validators, template compilers, tool adapters) is now mechanically constrained by these artifacts.

### 1. JSON Schemas (`schema/v0.7/`)

**Base Components:**
- `header/PacketHeader.schema.json` — Identity, routing, correlation (OMEN.md §9.1)
- `mcp/MCP.schema.json` — Mandatory Compliance Payload: E-POL, Q-POL, C-POL enforcement (OMEN.md §9.2)
- `packets/PacketBase.schema.json` — All packets extend header + mcp + payload

**Core Packet Types:**
- `ObservationPacket.schema.json` — Sensory input (tools, user obs, telemetry)
- `BeliefUpdatePacket.schema.json` — World model updates, contradiction resolution
- `DecisionPacket.schema.json` — Layer 5 decisions (VERIFY_FIRST, ACT, ESCALATE, etc.)
- `TaskDirectivePacket.schema.json` — Execution directives with tool safety classification
- `TaskResultPacket.schema.json` — Execution results (SUCCESS/FAILURE/CANCELLED)
- `ToolAuthorizationToken.schema.json` — WRITE authorization with scope/expiry/usage limits
- `EscalationPacket.schema.json` — Human escalation with options/gaps/recommendation

All schemas use JSON Schema Draft 2020-12 with full enum constraints, patterns, and required field enforcement per OMEN.md specification.

---

### 2. Golden Fixtures (`goldens/v0.7/`)

**Valid Single Packets:**
- `DecisionPacket.verify_first.json` — MEDIUM stakes + HIGH uncertainty → verify-first
- `DecisionPacket.act_readonly.json` — LOW stakes read-only fast path
- `DecisionPacket.act_write.json` — HIGH stakes post-verification with SUPERB tier
- `EscalationPacket.high_stakes_uncertainty.json` — CRITICAL + tools_partial escalation

**Invalid Test Case:**
- `DecisionPacket.subpar_blocks_action.INVALID.json` — Negative test: SUBPAR attempting ACT (INV-002 violation)

**Valid Episode Sequences (JSONL):**
- `Episode.verify_loop.jsonl` — Template B: 8-packet verification loop with epistemic upgrade
- `Episode.degraded_tools_high_stakes.jsonl` — Template F: CRITICAL stakes + tools_partial → mandatory escalation
- `Episode.write_with_token.jsonl` — Template D: Token authorization → WRITE directive → result integration

Each fixture demonstrates specific policy compliance, FSM transitions, and invariant satisfaction.

---

### 3. Validator Specifications (`validators/v0.7/`)

**FSM Transition Validator (`fsm_transitions.md`):**
- 9 FSM states (S0_IDLE through S9_SAFEMODE) with entry conditions
- Legal transition table (40+ transitions)
- Enforcement rules (verification loop closure, token gating, task closure, etc.)
- State-packet mappings
- Deterministic rules for state machine validation

**Cross-Policy Invariant Rules (`invariant_rules.md`):**
- 12 normative invariants (INV-001 through INV-012)
- Each with: policy source, condition, assertion, enforcement pseudocode, failure mode
- Covers:
  - MCP completeness (INV-001)
  - SUBPAR blocks ACT (INV-002)
  - HIGH/CRITICAL verification requirements (INV-003)
  - Evidence grounding (INV-004)
  - Budget enforcement (INV-005)
  - Token scope validation (INV-007)
  - Verification loop closure (INV-008)
  - Degraded tools policy (INV-010)
  - Task closure (INV-011)

Both specs written as deterministic algorithms ready for implementation in any language (Python/TypeScript/Rust).

---

### 4. Documentation (`docs/v0.7/`)

**Schema Index (`schema_index.md`):**
- Complete field catalog for all schemas
- Enum reference (all 12+ enumerations)
- Required vs optional field summary
- Context-dependent requirements
- Validation order specification

**Golden Catalog (`golden_catalog.md`):**
- Manifest of all fixtures with descriptions
- Test purpose and expected validation results
- Coverage matrix mapping fixtures to invariants
- Usage guidelines for schema/FSM/invariant validators
- Fixture naming conventions
- Planned future fixtures

---

## What This Enables

### Immediate Capabilities

1. **Schema Validation:**
   - Load any packet JSON
   - Validate against JSON Schema
   - Get deterministic pass/fail with specific error messages

2. **Test-Driven Protocol Development:**
   - Golden fixtures provide acceptance tests
   - Invalid fixtures test error handling
   - Episode sequences test FSM compliance

3. **Documentation Reference:**
   - Field catalog for implementers
   - Enum definitions for all protocol elements
   - Concrete examples of every packet type

### Next Implementation Steps

The schemas + goldens force specific next steps:

1. **Schema Validator Implementation:**
   - Python/TypeScript code to load and validate against JSON Schema
   - Reference: `schema_index.md` for validation order

2. **FSM Validator Implementation:**
   - Stateful validator tracking correlation_id → state
   - Reference: `fsm_transitions.md` for transition table
   - Test against: `Episode.*.jsonl` fixtures

3. **Invariant Validator Implementation:**
   - Episode ledger (budgets, tokens, evidence, open directives)
   - Deterministic checks per `invariant_rules.md`
   - Test against: invalid fixtures (expected failures)

4. **Template Compiler:**
   - Input: Template recipe (A-G from OMEN.md §11)
   - Output: Valid packet sequence passing all validators
   - Constraint: Must satisfy schemas + FSM + invariants

5. **Tool Adapters (EVE Sensorium):**
   - Input: Tool results (market data, intel, asset state)
   - Output: ObservationPacket with proper MCP fields
   - Evidence refs use URI scheme: `tool://`, `obs://`, `mem://`

---

## Architecture Constraints Now Enforced

### Fractal Consistency
Same packet grammar (header + mcp + payload) at every scale. Episode sequences are just streams of these packets.

### Policy Compliance by Construction
- SUBPAR physically cannot authorize ACT (schema + INV-002)
- WRITE requires token with valid scope (schema + INV-007)
- HIGH/CRITICAL requires verification (INV-003) or escalation (INV-009)
- Verification loops must close with observed evidence (INV-008)

### Auditability from Day One
Every packet has:
- Unique ID + timestamp + layer_source
- correlation_id for episode tracing
- evidence_refs or explicit absence reason
- MCP envelope with intent, stakes, tier, budgets, epistemics

### Brain-in-a-Vat Boundary
- ObservationPacket = sensorium (what crosses the vat boundary in)
- TaskDirectivePacket = effectors (what crosses out, with safety gates)
- Evidence refs enforce grounding constraint
- Tools state (ok/partial/down) forces posture changes

---

## File Tree

```
e:\omen\
├── OMEN.md                          # Canonical specification
├── ACE_Framework.md                 # ACE layer definitions
├── schema\v0.7\
│   ├── header\
│   │   └── PacketHeader.schema.json
│   ├── mcp\
│   │   └── MCP.schema.json
│   └── packets\
│       ├── PacketBase.schema.json
│       ├── ObservationPacket.schema.json
│       ├── BeliefUpdatePacket.schema.json
│       ├── DecisionPacket.schema.json
│       ├── TaskDirectivePacket.schema.json
│       ├── TaskResultPacket.schema.json
│       ├── ToolAuthorizationToken.schema.json
│       └── EscalationPacket.schema.json
├── goldens\v0.7\
│   ├── DecisionPacket.verify_first.json
│   ├── DecisionPacket.act_readonly.json
│   ├── DecisionPacket.act_write.json
│   ├── EscalationPacket.high_stakes_uncertainty.json
│   ├── DecisionPacket.subpar_blocks_action.INVALID.json
│   ├── Episode.verify_loop.jsonl
│   ├── Episode.degraded_tools_high_stakes.jsonl
│   └── Episode.write_with_token.jsonl
├── validators\v0.7\
│   ├── fsm_transitions.md
│   └── invariant_rules.md
└── docs\v0.7\
    ├── schema_index.md
    └── golden_catalog.md
```

---

## Next Session Recommendations

### If focusing on validation implementation:
**Task:** Implement schema validator in Python
**Dependencies:** `jsonschema` library, schema files
**Deliverable:** `validators/v0.7/schema_validator.py` that loads schemas and validates packets
**Test:** Run against all golden fixtures; expect documented pass/fail results

### If focusing on FSM implementation:
**Task:** Implement FSM validator as stateful class
**Dependencies:** `fsm_transitions.md`, episode JSONL files
**Deliverable:** `validators/v0.7/fsm_validator.py` with state tracking
**Test:** Process episode sequences; verify state transitions match spec

### If focusing on protocol testing:
**Task:** Create validator test suite
**Dependencies:** All schemas + goldens + validator specs
**Deliverable:** `tests/v0.7/test_protocol.py` using pytest
**Test:** Validate all fixtures; check invalid ones fail with correct errors

### If focusing on EVE integration:
**Task:** Design EVE sensorium adapter
**Dependencies:** ObservationPacket schema, evidence ref URI scheme
**Deliverable:** `adapters/eve/market_observer.py` (example)
**Test:** Generate ObservationPacket from mock EVE market data

---

## Verification

To verify this implementation is complete and correct:

1. **Schema Coverage:**
   - ✅ All MCP fields present (intent, stakes, quality, budgets, epistemics, evidence, routing)
   - ✅ All required packet types (7 core types from OMEN.md §9.3)
   - ✅ All enums defined (epistemic status, freshness, quality tiers, etc.)

2. **Golden Coverage:**
   - ✅ Template A (Grounding): verify_loop includes sense → model → decide
   - ✅ Template B (Verification): verify_loop shows complete cycle
   - ✅ Template D (Write Act): write_with_token shows token → directive → result
   - ✅ Template F (Degraded): degraded_tools_high_stakes shows tools_partial handling
   - ✅ Invalid case: subpar_blocks_action demonstrates INV-002

3. **Validator Specs:**
   - ✅ FSM states (9 states with entry conditions and legal transitions)
   - ✅ Invariants (12 normative rules with enforcement pseudocode)
   - ✅ Deterministic (no ambiguity; ready for code translation)

4. **Documentation:**
   - ✅ Schema index (field catalog, enum reference)
   - ✅ Golden catalog (fixture manifest, coverage matrix)
   - ✅ README (this file: architecture overview, next steps)

---

## References

- **OMEN.md:** Canonical specification (brain-in-a-vat AGI, ACE layers, policy suite, packet grammar)
- **ACE_Framework.md:** Layer definitions and responsibilities
- **JSON Schema Draft 2020-12:** [https://json-schema.org/draft/2020-12/schema](https://json-schema.org/draft/2020-12/schema)

---

**Implementation Status:** Phase 1 (Schema + Goldens) complete. Phase 2 (Validators) specified and ready for code implementation.
