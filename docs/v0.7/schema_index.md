# Schema Index v0.7

**OMEN Protocol Implementation: JSON Schema Catalog**

---

## Overview

This document catalogs all JSON schemas for OMEN v0.7 packet protocol, providing field references, enum values, and required/optional designations per OMEN.md specification.

---

## Schema Files

### Base Components

#### PacketHeader.schema.json
**Path:** `schema/v0.7/header/PacketHeader.schema.json`  
**Spec Reference:** OMEN.md Section 9.1 (Lines 678-684)

**Required Fields:**
- `packet_id` (string, pattern: `^pkt_[a-zA-Z0-9_-]+$`) — Unique packet identifier
- `packet_type` (enum) — One of 10 canonical packet types
- `created_at` (ISO 8601 datetime) — Packet creation timestamp
- `layer_source` (integer 1-6 or "Integrity") — Originating layer/overlay
- `correlation_id` (string, pattern: `^corr_[a-zA-Z0-9_-]+$`) — Episode identifier

**Optional Fields:**
- `campaign_id` (string, pattern: `^camp_[a-zA-Z0-9_-]+$`) — Macro context grouping
- `previous_packet_id` (string, pattern: `^pkt_[a-zA-Z0-9_-]+$`) — Explicit chaining reference

**Packet Type Enum:** ObservationPacket | BeliefUpdatePacket | DecisionPacket | VerificationPlanPacket | ToolAuthorizationToken | TaskDirectivePacket | TaskResultPacket | EscalationPacket | IntegrityAlertPacket | QueueUpdatePacket

---

#### MCP.schema.json
**Path:** `schema/v0.7/mcp/MCP.schema.json`  
**Spec Reference:** OMEN.md Section 9.2 (Lines 686-754), E-POL/Q-POL/C-POL

**All fields REQUIRED for consequential packets.**

**mcp.intent:**
- `summary` (string, minLength: 1) — Brief intent statement
- `scope` (string | object) — Bounded context

**mcp.stakes:** (4-axis decomposition)
- `impact` (enum: LOW | MEDIUM | HIGH | CRITICAL)
- `irreversibility` (enum: REVERSIBLE | PARTIAL | IRREVERSIBLE)
- `uncertainty` (enum: LOW | MEDIUM | HIGH)
- `adversariality` (enum: BENIGN | CONTESTED | HOSTILE)
- `stakes_level` (enum: LOW | MEDIUM | HIGH | CRITICAL) — Computed overall

**mcp.quality:**
- `quality_tier` (enum: SUBPAR | PAR | SUPERB)
- `satisficing_mode` (boolean) — Speed vs completeness optimization
- `definition_of_done` (object):
  - `text` (string, minLength: 1) — Human-readable completion criteria
  - `checks` (array of strings, minItems: 1) — Machine-checkable conditions
- `verification_requirement` (enum: OPTIONAL | VERIFY_ONE | VERIFY_ALL)

**mcp.budgets:**
- `token_budget` (integer, min: 0) — Max LLM tokens
- `tool_call_budget` (integer, min: 0) — Max tool invocations
- `time_budget_seconds` (integer, min: 0) — Max wall-clock time
- `risk_budget` (object):
  - `envelope` (string) — Risk posture descriptor
  - `max_loss` (string | number) — Maximum acceptable loss

**mcp.epistemics:** (E-POL compliance)
- `status` (enum: OBSERVED | DERIVED | REMEMBERED | INFERRED | HYPOTHESIZED | UNKNOWN)
- `confidence` (number, 0-1) — Calibrated confidence score
- `calibration_note` (string, minLength: 1) — Justification for confidence
- `freshness_class` (enum: REALTIME | OPERATIONAL | STRATEGIC | ARCHIVAL)
- `stale_if_older_than_seconds` (integer, min: 0, optional) — Staleness threshold
- `assumptions` (array of strings) — Explicit assumptions

**mcp.evidence:**
- `evidence_refs` (array of objects):
  - `ref_type` (enum: tool_output | user_observation | memory_item | derived_calc)
  - `ref_id` (string, minLength: 1) — URI or identifier
  - `timestamp` (ISO 8601 datetime)
  - `reliability_score` (number, 0-1, optional)
- `evidence_absent_reason` (string | null) — Required if evidence_refs empty

**mcp.routing:**
- `task_class` (enum: FIND | LOOKUP | SEARCH | CREATE | VERIFY | COMPILE)
- `tools_state` (enum: tools_ok | tools_partial | tools_down)

---

#### PacketBase.schema.json
**Path:** `schema/v0.7/packets/PacketBase.schema.json`

**Structure:** All packets extend this base
- `header` (ref: PacketHeader.schema.json)
- `mcp` (ref: MCP.schema.json)
- `payload` (object, type-specific)

---

### Packet Types

#### ObservationPacket.schema.json
**Path:** `schema/v0.7/packets/ObservationPacket.schema.json`  
**Spec Reference:** OMEN.md Section 9.3

**Payload Required Fields:**
- `observation_type` (enum: tool_output | user_input | system_telemetry | character_state | market_signal | intel_update)
- `data` (object, minProperties: 1) — Raw or normalized observation

**Payload Optional Fields:**
- `source_tool` (string) — Tool identifier if from tool execution
- `query_params` (object) — Parameters used to generate observation
- `reliability_metadata` (object):
  - `tool_success` (boolean)
  - `latency_ms` (number, min: 0)
  - `partial_result` (boolean)

---

#### BeliefUpdatePacket.schema.json
**Path:** `schema/v0.7/packets/BeliefUpdatePacket.schema.json`

**Payload Required Fields:**
- `update_type` (enum: new_belief | revision | contradiction_resolved | confidence_adjustment | staleness_refresh)
- `belief_changes` (array, minItems: 1):
  - `domain` (string) — Belief domain (e.g., 'market', 'threats')
  - `key` (string) — Specific belief identifier
  - `new_value` — Updated belief content
  - `prior_value` — Previous state (null if new)
  - `epistemic_upgrade` (boolean, optional) — True if status improved

**Payload Optional Fields:**
- `evidence_integration` (array of strings) — Packet IDs that motivated update
- `contradiction_details` (object, required if update_type = contradiction_resolved):
  - `conflicting_packet_ids` (array of strings)
  - `resolution_method` (enum: prefer_fresh | prefer_higher_reliability | escalated | manual_override)

---

#### DecisionPacket.schema.json
**Path:** `schema/v0.7/packets/DecisionPacket.schema.json`  
**Spec Reference:** OMEN.md Section 9.3, Section 15.2 (example)

**Payload Required Fields:**
- `decision_outcome` (enum: VERIFY_FIRST | ACT | ESCALATE | DEFER | CANCEL)
- `decision_summary` (string, minLength: 1) — Human-readable rationale
- `constraints_satisfied` (object):
  - `constitutional_check` (boolean) — Layer 1 veto passed
  - `budget_check` (boolean) — Feasible within budgets
  - `tier_check` (boolean) — Quality tier sufficient for stakes
  - `verification_check` (boolean, optional) — Verification level met

**Payload Optional Fields:**
- `chosen_option` (object):
  - `option_id`, `description`, `expected_value`, `risk_profile`
- `rejected_alternatives` (array):
  - `option_id`, `rejection_reason`
- `load_bearing_assumptions` (array):
  - `assumption`, `verified`, `verification_packet_id` (optional)
- `failure_modes` (array):
  - `mode`, `mitigation`

---

#### TaskDirectivePacket.schema.json
**Path:** `schema/v0.7/packets/TaskDirectivePacket.schema.json`

**Payload Required Fields:**
- `task_id` (string, pattern: `^task_[a-zA-Z0-9_-]+$`) — Unique task identifier
- `task_type` (enum: tool_read | tool_write | computation | verification | memory_lookup)
- `execution_method` (object):
  - `method` (enum: tool | code | llm_call | memory_query)
  - `tool_id` (string, required if method=tool)
  - `tool_params` (object, optional)
  - `code_ref` (string, required if method=code)
  - `code_params` (object, optional)

**Payload Optional Fields:**
- `tool_safety_class` (enum: READ | WRITE | MIXED)
- `authorization_token_id` (string, pattern: `^token_[a-zA-Z0-9_-]+$`) — Required if WRITE/MIXED
- `timeout_seconds` (integer, min: 1)
- `retry_policy` (object):
  - `max_retries`, `backoff_multiplier`

---

#### TaskResultPacket.schema.json
**Path:** `schema/v0.7/packets/TaskResultPacket.schema.json`

**Payload Required Fields:**
- `task_id` (string, pattern: `^task_[a-zA-Z0-9_-]+$`) — Matches TaskDirective
- `directive_packet_id` (string, pattern: `^pkt_[a-zA-Z0-9_-]+$`) — Originating directive
- `result_status` (enum: SUCCESS | FAILURE | CANCELLED)

**Payload Optional Fields:**
- `result_data` — Tool output or computation result (null if failed/cancelled)
- `error_details` (object, required if FAILURE):
  - `error_code`, `error_message`, `is_transient`, `retry_recommended`
- `execution_metadata` (object):
  - `execution_time_ms`, `tokens_used`, `tool_calls_used`, `retry_count`
- `observation_packet_id` (string) — Reference if result converted to observation

---

#### ToolAuthorizationToken.schema.json
**Path:** `schema/v0.7/packets/ToolAuthorizationToken.schema.json`

**Payload Required Fields:**
- `token_id` (string, pattern: `^token_[a-zA-Z0-9_-]+$`) — Unique token identifier
- `authorized_scope` (object):
  - `tool_ids` (array of strings, minItems: 1) — Allowed tools
  - `operation_types` (array, enum: read | write | delete | modify, minItems: 1)
  - `resource_constraints` (object, optional) — Bounds on affected resources
- `expiry` (ISO 8601 datetime) — Token invalidation timestamp
- `max_usage_count` (integer, min: 1) — Number of directives this authorizes
- `issuer_layer` (integer 1-6 or "Integrity") — Token issuing authority

**Payload Optional Fields:**
- `usage_count` (integer, min: 0, default: 0) — Current usage (incremented by Integrity)
- `revoked` (boolean, default: false) — True if Integrity revoked
- `rationale` (string, minLength: 1) — Audit trail explanation

---

#### EscalationPacket.schema.json
**Path:** `schema/v0.7/packets/EscalationPacket.schema.json`

**Payload Required Fields:**
- `escalation_trigger` (enum: high_stakes_high_uncertainty | constitutional_boundary | contradiction_unresolved | budget_insufficient | tools_degraded_critical | user_override_required)
- `top_options` (array, minItems: 2, maxItems: 3):
  - `option_id`, `description`, `pros` (array), `cons` (array), `risk_summary`
- `evidence_gaps` (array, minItems: 1):
  - `gap`, `impact_if_unknown`, `verification_method` (optional)
- `recommended_next_step` (object):
  - `step`, `rationale`, `estimated_cost` (optional: time_seconds, tokens, tool_calls)

**Payload Optional Fields:**
- `blocking_decision_packet_id` (string, pattern: `^pkt_[a-zA-Z0-9_-]+$`)

---

## Enum Reference

### Epistemic Status
OBSERVED | DERIVED | REMEMBERED | INFERRED | HYPOTHESIZED | UNKNOWN

### Freshness Classes
REALTIME (seconds-minutes) | OPERATIONAL (minutes-hours) | STRATEGIC (hours-days) | ARCHIVAL (days-months)

### Quality Tiers
SUBPAR (speculative, cannot authorize action) | PAR (verify one load-bearing assumption) | SUPERB (verify all)

### Verification Requirements
OPTIONAL | VERIFY_ONE | VERIFY_ALL

### Stakes Levels
LOW | MEDIUM | HIGH | CRITICAL

### Decision Outcomes
VERIFY_FIRST | ACT | ESCALATE | DEFER | CANCEL

### Task Result Status
SUCCESS | FAILURE | CANCELLED

### Tools State
tools_ok | tools_partial | tools_down

### Tool Safety Class
READ | WRITE | MIXED

---

## Required vs Optional Summary

**Always Required (Consequential Packets):**
- All PacketHeader fields except campaign_id, previous_packet_id
- All MCP fields (unless explicitly noted as optional like stale_if_older_than_seconds)
- Type-specific payload required fields per schema

**Commonly Optional:**
- evidence_refs may be empty if evidence_absent_reason provided
- Optional metadata fields (reliability_score, execution_metadata, etc.)
- Chaining/context fields (campaign_id, previous_packet_id)

**Context-Dependent Required:**
- authorization_token_id required if tool_safety_class = WRITE/MIXED
- evidence_absent_reason required if evidence_refs empty
- error_details required if result_status = FAILURE
- contradiction_details required if update_type = contradiction_resolved

---

## Schema Validation Order

1. **JSON Schema validation** (structure, types, enums, patterns)
2. **FSM transition check** (per fsm_transitions.md)
3. **Invariant checks** (per invariant_rules.md)
4. **Ledger update** (cumulative budgets, evidence refs, tokens)

---

## References

- OMEN.md Section 9: Protocol Specification (Lines 678-763)
- OMEN.md Section 8: Policy Suite (Lines 408-709)
- Individual schema files in `schema/v0.7/`
