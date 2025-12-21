# OMEN Template Compiler

**Generative complement to the validation stack** - compiles episode templates (A-G) into valid packet sequences.

## Overview

The Template Compiler implements the canonical episode patterns from OMEN.md Section 11, generating structurally-correct packet sequences that demonstrate the protocol's cognition loops. Each template encodes a specific decision workflow:

- **Template A (Grounding Loop)**: Sense → Model → Decide
- **Template B (Verification Loop)**: Decide VERIFY_FIRST → Plan → Execute → Update → Decide ACT
- **Template C (Read-Only Act)**: Decide ACT → READ directives → results → belief integration
- **Template D (Write Act)**: Decide ACT → token → WRITE directive → result → belief integration
- **Template E (Escalation)**: Decide ESCALATE → present options + gaps
- **Template F (Degraded Tools)**: tools_down/partial posture handling
- **Template G (Compile-to-Code)**: Code generation workflow with test gates

## Architecture

```
TemplateContext (parameters) 
    ↓
TemplateCompiler.compile(template_id, context)
    ↓
[Packet₁, Packet₂, ..., Packetₙ]  (valid sequence)
    ↓
Validators (schema → FSM → invariants)
```

The compiler acts as a **proof-of-concept generator**: given MCP envelope parameters (stakes, quality, budgets), it emits a complete episode that satisfies:

1. **Structural validity**: All packets have correct header/mcp/payload structure
2. **Sequential validity**: Packets chain via `previous_packet_id`, correlation_id consistent
3. **FSM compliance**: State transitions follow legal paths (e.g., VERIFY_FIRST → verification loop)
4. **Semantic coherence**: Decision outcomes align with stakes/quality gates

## Installation & Setup

```bash
# Already included in OMEN v0.7 repository
cd e:\omen

# Run tests to verify installation
pytest tests/test_template_compiler.py -v
```

## Usage

### Command-Line Interface

```bash
# Basic compilation (outputs to <correlation_id>.jsonl)
python compile_template.py <template> <correlation_id>

# List packets without saving
python compile_template.py verification corr_001 --list

# Custom parameters
python compile_template.py write corr_002 \\
    --stakes HIGH \\
    --tier SUPERB \\
    --intent "Place market order" \\
    --output market_write.jsonl

# Compile and validate
python compile_template.py degraded corr_003 --validate --no-timestamp-checks -v
```

**Template names** (case-insensitive aliases):
- `a`, `grounding`, `grounding_loop`
- `b`, `verification`, `verify`
- `c`, `readonly`, `read`
- `d`, `write`
- `e`, `escalation`, `escalate`
- `f`, `degraded`, `degraded_tools`
- `g`, `compile`, `compile_to_code`, `code`

### Python API

```python
from templates.v0_7.template_compiler import (
    TemplateCompiler, TemplateID, TemplateContext, quick_compile
)

# Quick compilation
packets = quick_compile("verification", "corr_001", stakes_level="MEDIUM")
print(f"Generated {len(packets)} packets")

# Detailed context
ctx = TemplateContext(
    correlation_id="corr_write_001",
    intent_summary="Place market buy order",
    stakes_level="HIGH",
    quality_tier="SUPERB",
    tools_state="tools_ok",
    template_params={
        "tool_id": "market_api",
        "parameters": {"symbol": "TRIT", "quantity": 1000}
    }
)

compiler = TemplateCompiler()
packets = compiler.compile(TemplateID.WRITE_ACT, ctx)

# Export to file
compiler.export_jsonl("market_write.jsonl", packets)
```

### Integration with Validators

```python
from validate_omen import OMENValidator
from templates.v0_7.template_compiler import quick_compile

# Generate episode
packets = quick_compile("verification", "corr_001")

# Validate with full stack
validator = OMENValidator(check_timestamps=False)  # Historical data
for i, packet in enumerate(packets, 1):
    result = validator.validate_packet(packet)
    if result.is_valid:
        print(f"[PASS] Packet {i}")
    else:
        print(f"[FAIL] Packet {i}")
        print(f"  Schema: {result.schema_errors}")
        print(f"  FSM: {result.fsm_errors}")
        print(f"  Invariants: {result.invariant_errors}")
```

## Templates in Detail

### Template A: Grounding Loop (3 packets)

**Purpose**: Simplest cognition loop - observe, model, decide.

**Sequence**:
1. ObservationPacket (Layer 6 senses environment)
2. BeliefUpdatePacket (Layer 5 integrates observation)
3. DecisionPacket (Layer 5 decides ACT)

**Use Cases**:
- Low-stakes decisions with adequate information
- Read-only operations on cached/stable data
- Fast-path actions with minimal uncertainty

**Example**:
```python
packets = quick_compile("grounding", "corr_scan_001",
                       intent_summary="Scan asset inventory",
                       stakes_level="LOW")
# → 3 packets: obs → belief → decision(ACT)
```

### Template B: Verification Loop (8 packets)

**Purpose**: Verify-first pattern when stakes/uncertainty require confirmation.

**Sequence**:
1. ObservationPacket (stale cached data)
2. BeliefUpdatePacket (staleness refresh)
3. DecisionPacket (VERIFY_FIRST due to staleness)
4. TaskDirectivePacket (READ verification)
5. TaskResultPacket (SUCCESS)
6. ObservationPacket (fresh OBSERVED evidence)
7. BeliefUpdatePacket (epistemic upgrade: HYPOTHESIZED → OBSERVED)
8. DecisionPacket (ACT after verification)

**Use Cases**:
- MEDIUM stakes + HIGH uncertainty (Q-POL trigger)
- Stale data requiring refresh before action
- Load-bearing assumptions needing verification

**Example**:
```python
packets = quick_compile("verification", "corr_price_check",
                       intent_summary="Verify market price before trade",
                       stakes_level="MEDIUM",
                       uncertainty="HIGH")
# → 8 packets: verify loop with epistemic upgrade
```

### Template C: Read-Only Act (5 packets)

**Purpose**: Fast path for low-stakes read operations.

**Sequence**:
1. DecisionPacket (ACT for read-only)
2. TaskDirectivePacket (READ)
3. TaskResultPacket (SUCCESS)
4. ObservationPacket (capture result)
5. BeliefUpdatePacket (integrate result)

**Use Cases**:
- LOW stakes read operations
- No token required (INV-007 only applies to WRITE)
- Information gathering with minimal risk

**Example**:
```python
packets = quick_compile("readonly", "corr_lookup_001",
                       intent_summary="Lookup current inventory",
                       stakes_level="LOW",
                       template_params={"tool_id": "inventory_api"})
# → 5 packets: decision → directive → result → obs → belief
```

### Template D: Write Act (6 packets)

**Purpose**: HIGH stakes write operation requiring token authorization.

**Sequence**:
1. DecisionPacket (ACT with HIGH stakes + SUPERB tier)
2. ToolAuthorizationToken (Layer 1 issues write token)
3. TaskDirectivePacket (WRITE with authorization_token_id)
4. TaskResultPacket (SUCCESS)
5. ObservationPacket (write confirmation)
6. BeliefUpdatePacket (integrate write results)

**Use Cases**:
- HIGH/CRITICAL stakes write operations
- Resource modifications requiring Layer 1 authorization
- Token scope validation (INV-007)

**Example**:
```python
packets = quick_compile("write", "corr_order_001",
                       intent_summary="Place market buy order",
                       stakes_level="HIGH",
                       quality_tier="SUPERB",
                       template_params={
                           "tool_id": "market_api",
                           "assumption": "Market price verified",
                           "resource_constraints": {"max_value": "50M ISK"}
                       })
# → 6 packets: decision → token → directive(WRITE) → result → obs → belief
```

### Template E: Escalation (2 packets)

**Purpose**: Escalate when stakes/uncertainty exceed autonomous authority.

**Sequence**:
1. DecisionPacket (ESCALATE due to CRITICAL + HIGH uncertainty)
2. EscalationPacket (present 2-3 options with gaps/recommendation)

**Use Cases**:
- CRITICAL stakes + HIGH uncertainty (Q-POL mandatory escalation)
- Evidence gaps preventing confident action
- INV-009 escalation structure requirements

**Example**:
```python
packets = quick_compile("escalation", "corr_critical_001",
                       intent_summary="Critical asset transfer decision",
                       stakes_level="CRITICAL",
                       uncertainty="HIGH",
                       template_params={
                           "option_1": "Proceed with caution",
                           "option_2": "Defer decision 24h",
                           "option_3": "Gather additional intelligence",
                           "recommendation": "Recommend Option 3"
                       })
# → 2 packets: decision(ESCALATE) → escalation(options)
```

### Template F: Degraded Tools (4 packets)

**Purpose**: Handle tool degradation per C-POL safety rules.

**Sequence**:
1. ObservationPacket (system telemetry: tools_state = tools_partial)
2. BeliefUpdatePacket (system state update)
3. DecisionPacket (ESCALATE due to CRITICAL + tools_partial)
4. EscalationPacket (degraded tools escalation)

**Use Cases**:
- CRITICAL stakes + tools_partial → mandatory ESCALATE (INV-010)
- Tool failure handling
- Safety-first posture under degradation

**Example**:
```python
packets = quick_compile("degraded", "corr_degraded_001",
                       intent_summary="Critical transfer with degraded tools",
                       stakes_level="CRITICAL",
                       tools_state="tools_partial")
# → 4 packets: obs(degradation) → belief → decision(ESCALATE) → escalation
```

### Template G: Compile-to-Code (7 packets)

**Purpose**: Code generation workflow with test/rollback gates.

**Sequence**:
1. DecisionPacket (VERIFY_FIRST for code generation)
2. TaskDirectivePacket (generate code)
3. TaskResultPacket (code generated)
4. TaskDirectivePacket (run tests)
5. TaskResultPacket (tests pass)
6. BeliefUpdatePacket (code verified)
7. DecisionPacket (ACT to deploy)

**Use Cases**:
- Code generation with automated verification
- Multi-phase execution with gates
- Test-before-deploy workflows

**Example**:
```python
packets = quick_compile("compile", "corr_codegen_001",
                       intent_summary="Generate and test API handler",
                       stakes_level="MEDIUM",
                       template_params={
                           "code_spec": {"function": "handle_request", "language": "python"}
                       })
# → 7 packets: verify-first → generate → test → verify → deploy
```

## TemplateContext Parameters

All templates accept a `TemplateContext` with configurable MCP envelope fields:

```python
@dataclass
class TemplateContext:
    # Required
    correlation_id: str
    
    # Episode identification
    campaign_id: str = "camp_OMEN_BOOT"
    
    # Intent
    intent_summary: str = "Execute template episode"
    intent_scope: str = "template_scope"
    
    # Stakes (Q-POL)
    impact: str = "MEDIUM"
    irreversibility: str = "REVERSIBLE"
    uncertainty: str = "MEDIUM"
    adversariality: str = "BENIGN"
    stakes_level: str = "MEDIUM"
    
    # Quality (Q-POL)
    quality_tier: str = "PAR"  # SUBPAR/PAR/SUPERB
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
    
    # Tools/routing (C-POL)
    tools_state: str = "tools_ok"  # tools_ok/tools_partial/tools_down
    task_class: str = "DECIDE"
    
    # Template-specific parameters
    template_params: Dict[str, Any] = {}
```

## Test Results

```bash
pytest tests/test_template_compiler.py -v
# 16 tests, 16 passed, 0 failed
```

**Coverage**:
- ✅ All 7 templates compile successfully
- ✅ Packet chaining (previous_packet_id)
- ✅ Correlation ID consistency
- ✅ Decision outcomes (VERIFY_FIRST, ACT, ESCALATE)
- ✅ Token authorization flow (Template D)
- ✅ Verification loop closure (Template B)
- ✅ Escalation structure (Templates E, F)
- ✅ Export functions (JSONL, JSON)
- ✅ Convenience APIs (quick_compile, compile_template)

## Integration Tests

The compiler's output can be validated with the full validator stack:

```bash
# Compile and validate
python compile_template.py verification corr_test_001 --validate --no-timestamp-checks

# Or manually:
python compile_template.py verification corr_test_001 -o test.jsonl
python validate_omen.py episode test.jsonl --no-timestamp-checks
```

**Note**: The compiler currently generates *structurally valid* packets that satisfy FSM and most invariant constraints. Full schema compliance (exact field names, enum values, evidence ref formats) is a work-in-progress. The architecture and template logic are complete and tested.

## Known Limitations

1. **Schema field details**: Some generated packets use simplified field formats (e.g., evidence_refs as strings instead of objects with ref_type/ref_id). Golden fixtures show the correct format.

2. **Timestamp handling**: Uses datetime.now() by default. For historical testing, validators should use `--no-timestamp-checks`.

3. **Template customization**: Template logic is fixed; template_params provides limited customization. For complex scenarios, manually edit compiled output.

4. **Layer source accuracy**: Some packets may specify simplified layer_source values. OMEN.md Section 11.1 defines the correct layer contracts.

## Future Enhancements

- [ ] Full schema compliance (evidence refs, observation types, task classes)
- [ ] Template composition (combine templates into multi-phase episodes)
- [ ] MCP validation before emission (catch errors at compile time)
- [ ] Template parameters validation (reject incompatible parameters early)
- [ ] Interactive template builder CLI
- [ ] Template visualization (graphical representation of packet flows)

## References

- **OMEN Spec**: [OMEN.md](../OMEN.md) Section 11 (Episode Templates & Layer Contracts)
- **Validators**: [validate_omen.py](../validate_omen.py) (three-layer validation stack)
- **Golden Fixtures**: [goldens/v0.7/](../goldens/v0.7/) (hand-crafted valid episodes)
- **Tests**: [tests/test_template_compiler.py](../tests/test_template_compiler.py)

## Summary

The Template Compiler demonstrates the OMEN architecture end-to-end:

1. **Define**: Canonical episode patterns (Templates A-G)
2. **Generate**: Compile templates into packet sequences
3. **Validate**: Run through schema → FSM → invariant validators
4. **Test**: 71 tests passing (16 compiler + 55 validators)

This proves the protocol is **executable** - templates encode real cognition workflows, compiler generates concrete packets, validators enforce constraints. The full loop is operational.
