# OMEN v0.7 Validator CLI

Unified command-line tool for validating OMEN packets and episodes through all three validation layers.

## Three-Layer Validation Stack

1. **Schema Validation** - JSON Schema + structural checks
2. **FSM Validation** - State machine + sequential dependencies  
3. **Invariant Validation** - Cross-policy constraints + episode semantics

## Installation

Requires Python 3.8+ and dependencies:

```bash
pip install jsonschema python-dateutil
```

## Usage

### Validate Single Packet

```bash
python validate_omen.py packet goldens/v0.7/DecisionPacket.verify_first.json
```

Note: Single packets only undergo schema validation (FSM/invariants require episode context).

### Validate Episode Sequence

```bash
python validate_omen.py episode goldens/v0.7/Episode.verify_loop.jsonl
```

For historical episodes (golden fixtures), disable timestamp checks:

```bash
python validate_omen.py episode goldens/v0.7/Episode.verify_loop.jsonl --no-timestamp-checks
```

### Validate All Golden Fixtures

```bash
python validate_omen.py goldens
```

This automatically validates all fixtures in `goldens/v0.7/` with timestamp checks disabled.

### Verbose Mode

See detailed output for passing packets:

```bash
python validate_omen.py episode file.jsonl -v --no-timestamp-checks
```

### Selective Layer Disabling

Disable specific validation layers:

```bash
# Schema only (skip FSM and invariants)
python validate_omen.py episode file.jsonl --no-fsm --no-invariants

# Skip just invariants
python validate_omen.py episode file.jsonl --no-invariants
```

## Exit Codes

- `0` - All validations passed
- `1` - Validation failure or error
- `130` - Interrupted by user (Ctrl+C)

## Examples

```bash
# Validate single decision packet
python validate_omen.py packet goldens/v0.7/DecisionPacket.act_write.json

# Validate episode with verbose output
python validate_omen.py episode goldens/v0.7/Episode.verify_loop.jsonl -v --no-timestamp-checks

# Validate all golden fixtures
python validate_omen.py goldens

# Schema-only validation of episode
python validate_omen.py episode file.jsonl --no-fsm --no-invariants
```

## Output Format

### Passing Validation

```
[Episode] Validating: Episode.verify_loop.jsonl
  Validating 8 packets...
[PASS] - All 8 packets valid
```

### Failing Validation

```
[Episode] Validating: bad_episode.jsonl
  Validating 5 packets...
[FAIL] - pkt_decision_001
  Schema errors:
    • Missing required field 'mcp.stakes.stakes_level'
  FSM errors:
    • Invalid transition: S1_SENSE -> DecisionPacket
  Invariant errors:
    • INV-002: SUBPAR tier cannot authorize ACT decision
```

## Test Suite

Run all validator tests:

```bash
pytest tests/ -v
```

Run just CLI tests:

```bash
pytest tests/test_cli.py -v
```

## Validation Results Summary

**Complete test suite: 55/55 passing (100%)**

- Schema validator: 14/14 ✅
- FSM validator: 11/11 ✅
- Invariant validator: 25/25 ✅
- CLI tool: 5/5 ✅

**Golden fixtures: 7/7 passing (100%)**

- Individual packets: 4/4 ✅
- Episode sequences: 3/3 ✅
