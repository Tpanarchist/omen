# OMEN Architecture Guide

This document provides detailed technical documentation for OMEN's architecture, component interactions, and design decisions.

## Table of Contents

1. [Design Philosophy](#design-philosophy)
2. [Component Overview](#component-overview)
3. [Layer Architecture](#layer-architecture)
4. [Packet System](#packet-system)
5. [Episode Lifecycle](#episode-lifecycle)
6. [Validation Stack](#validation-stack)
7. [Tool Execution](#tool-execution)
8. [Integrity System](#integrity-system)
9. [Data Flow](#data-flow)
10. [Extension Points](#extension-points)

---

## Design Philosophy

### Cognition-First

OMEN treats LLM instances as **first-class cognitive entities** rather than simple API endpoints. Each ACE layer is a distinct "brain" with:

- Its own system prompt defining identity and responsibilities
- Contracts specifying what packets it can emit/receive
- Stateless invocation (fresh context each time)

The orchestrator manages state; layers provide cognition.

### Brain-in-a-Vat

OMEN's reality is bounded by the **vat boundary**:

- **Sensorium** (inbound): Tools and observations cross into cognition
- **Effectors** (outbound): Actions and commands cross out to reality
- **Internal**: Everything else is modeling and self-management

This separation enables:
- Clear evidence grounding for observations
- Explicit authorization for consequential actions
- Auditable decision trails

### Packet Grammar

All inter-layer communication uses **structured packets** with:

- MCP envelope (correlation ID, timestamps, routing)
- Type-specific payloads
- Epistemic status tracking
- Evidence references

This enables:
- Compile-time type safety
- Runtime validation
- Post-hoc auditability

---

## Component Overview

### Dependency Graph

```
vocabulary (enums)
    │
    ├── schemas (packet definitions)
    │       │
    │       └── validation (schema → fsm → invariant)
    │               │
    │               └── templates (canonical patterns)
    │                       │
    │                       └── compiler (context binding)
    │
    ├── buses (routing)
    │
    ├── layers (cognition)
    │       │
    │       └── contracts (emission/reception rules)
    │
    └── tools (reality interface)

orchestrator
    ├── ledger (state tracking)
    ├── pool (layer management)
    ├── runner (execution)
    └── orchestrator (unified API)

episode (persistence)
integrity (safety)
observability (logging/metrics)
clients (LLM APIs)
```

### Module Responsibilities

| Module | Responsibility | Key Types |
|--------|---------------|-----------|
| `vocabulary` | Type definitions | 18 enums (LayerSource, PacketType, etc.) |
| `schemas` | Packet models | MCPEnvelope, PacketHeader, 9 packet types |
| `validation` | Correctness checking | SchemaValidator, FSMValidator, InvariantValidator |
| `templates` | Episode patterns | EpisodeTemplate, TEMPLATE_A through TEMPLATE_H |
| `compiler` | Context binding | TemplateCompiler, CompilationContext, CompiledEpisode |
| `layers` | Cognition | Layer, LayerContract, LAYER_PROMPTS |
| `buses` | Routing | NorthboundBus, SouthboundBus |
| `tools` | Reality interface | Tool, ToolRegistry, ToolResult |
| `orchestrator` | Coordination | Orchestrator, EpisodeRunner, EpisodeLedger |
| `episode` | Persistence | EpisodeRecord, SQLiteStore |
| `integrity` | Safety | IntegrityMonitor, SafeMode |
| `observability` | Operations | Logging, Metrics, Debug |
| `clients` | LLM APIs | OpenAIClient |

---

## Layer Architecture

### The 6-Layer Hierarchy

```
┌─────────────────────────────────────────────────────────────────┐
│ L1: ASPIRATIONAL                                                │
│ Constitutional oversight, mission posture, ethical alignment    │
│ Outputs: IntegrityAlert, BeliefUpdate                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ L2: GLOBAL STRATEGY                                             │
│ Strategic direction, campaign framing, long-term planning       │
│ Outputs: BeliefUpdate (strategy), Escalation                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ L3: AGENT MODEL                                                 │
│ Self-awareness, capability assessment, tool readiness          │
│ Outputs: BeliefUpdate (capabilities)                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ L4: EXECUTIVE FUNCTION                                          │
│ Planning, budgets, Definition of Done, feasibility             │
│ Outputs: BeliefUpdate (plans), TaskDirective                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ L5: COGNITIVE CONTROL                                           │
│ Decision-making, task arbitration, token issuance              │
│ Outputs: Decision, VerificationPlan, ToolAuthorization         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ L6: TASK PROSECUTION                                            │
│ Execution, reality grounding, tool invocation                  │
│ Outputs: Observation, TaskResult                               │
└─────────────────────────────────────────────────────────────────┘
```

### Layer Contracts

Each layer has explicit contracts:

```python
@dataclass(frozen=True)
class LayerContract:
    layer: LayerSource
    can_emit: frozenset[PacketType]
    can_receive: frozenset[PacketType]
    description: str
```

Example (L5 Cognitive Control):

```python
L5_CONTRACT = LayerContract(
    layer=LayerSource.LAYER_5,
    can_emit=frozenset({
        PacketType.DECISION,
        PacketType.VERIFICATION_PLAN,
        PacketType.TOOL_AUTHORIZATION,
        PacketType.TASK_DIRECTIVE,
        PacketType.ESCALATION,
    }),
    can_receive=frozenset({
        PacketType.OBSERVATION,
        PacketType.TASK_RESULT,
        PacketType.BELIEF_UPDATE,
    }),
    description="Decision-making and task arbitration",
)
```

### Layer Invocation

Layers are stateless. Each invocation:

1. **Receives** `LayerInput` (packets, correlation_id, context)
2. **Builds** context from packets into user message
3. **Calls** LLM with system prompt + user message
4. **Parses** response into packets
5. **Validates** output against emission contract
6. **Returns** `LayerOutput` (packets, raw_response, errors)

```python
class Layer(ABC):
    def invoke(self, input: LayerInput) -> LayerOutput:
        # 1. Filter by reception contract
        filtered = self._filter_input(input)
        
        # 2. Build LLM context
        context = self.build_context(filtered)
        
        # 3. Call LLM
        response = self.llm_client.complete(
            self.system_prompt,
            context,
        )
        
        # 4. Parse response
        packets = self.parse_response(response, input)
        
        # 5. Validate output
        valid_packets, errors = self._validate_output(packets)
        
        # 6. Return output
        return LayerOutput(
            layer=self.layer_id,
            packets=valid_packets,
            raw_response=response,
            errors=errors,
            ...
        )
```

---

## Packet System

### MCP Envelope

Every packet has a common envelope:

```python
@dataclass
class MCPEnvelope:
    correlation_id: UUID           # Episode identifier
    causation_id: UUID | None      # Parent packet (tracing)
    timestamp: datetime            # Creation time
    source_layer: LayerSource      # Originating layer
    target_layer: LayerSource | None  # Destination (None = broadcast)
    routing: RoutingInfo           # Bus routing metadata
```

### Packet Header

Type-specific header:

```python
@dataclass
class PacketHeader:
    packet_type: PacketType        # OBSERVATION, DECISION, etc.
    packet_id: UUID                # Unique identifier
    schema_version: str            # "0.5.0"
```

### Packet Structure

```python
@dataclass
class SomePacket:
    envelope: MCPEnvelope
    header: PacketHeader
    payload: SomePayload           # Type-specific data
    epistemics: EpistemicMetadata  # Confidence, status, freshness
    evidence: EvidenceMetadata     # References, absent reasons
```

### The 9 Packet Types

| Type | Source | Purpose |
|------|--------|---------|
| `OBSERVATION` | L6 | Reports from reality |
| `BELIEF_UPDATE` | L1-L6 | Epistemic state changes |
| `DECISION` | L5 | Decision outcomes |
| `VERIFICATION_PLAN` | L5 | Information gathering plans |
| `TOOL_AUTHORIZATION` | L5 | WRITE tool permissions |
| `TASK_DIRECTIVE` | L4, L5 | Execution instructions |
| `TASK_RESULT` | L6 | Execution outcomes |
| `ESCALATION` | L2-L5 | Human handoff requests |
| `INTEGRITY_ALERT` | L1, Integrity | System health warnings |

---

## Episode Lifecycle

### Compilation

Templates compile to executable episodes:

```
EpisodeTemplate
      │
      ▼ (CompilationContext: stakes, quality, budgets)
TemplateCompiler.compile()
      │
      ▼
CompiledEpisode
  ├── correlation_id
  ├── template_id
  ├── entry_step
  ├── exit_steps
  └── steps[]
        ├── step_id
        ├── owner_layer
        ├── packet_type
        ├── mcp_bindings (pre-filled envelope fields)
        └── next_steps[]
```

### Execution

The runner executes steps:

```python
def run(episode, ledger, initial_packets):
    current_step = episode.entry_step
    current_packets = initial_packets
    
    while current_step and not at_exit:
        step = episode.get_step(current_step)
        
        # Mark step started
        ledger.start_step(current_step)
        
        # Invoke owning layer
        output = layer_pool.invoke_layer(
            step.owner_layer,
            LayerInput(packets=current_packets, ...)
        )
        
        # Route packets via buses
        route_packets(output.packets)
        
        # Update ledger
        ledger.complete_step(current_step)
        
        # Select next step
        current_step = step.next_steps[0]
        current_packets = output.packets
    
    return EpisodeResult(...)
```

### State Machine

Episodes follow FSM states:

```
S0_IDLE → S1_SENSE → S2_MODEL → S3_DECIDE
                                    │
           ┌────────────────────────┼────────────────────────┐
           ▼                        ▼                        ▼
       S4_VERIFY               S5_AUTHORIZE              S6_ACT
           │                        │                        │
           └────────────────────────┴────────────────────────┘
                                    │
                                    ▼
                               S7_REVIEW → S0_IDLE
```

Legal transitions are enforced at compilation and runtime.

---

## Validation Stack

Three-layer validation ensures correctness:

### 1. Schema Validator

Structural correctness via Pydantic:

```python
validator = SchemaValidator()
result = validator.validate(packet)
# Checks: required fields, types, enum values
```

### 2. FSM Validator

State machine compliance:

```python
validator = FSMValidator()
result = validator.validate(packet, current_state)
# Checks: legal state transitions, terminal states
```

### 3. Invariant Validator

Business rules:

```python
validator = InvariantValidator()
result = validator.validate(packet, context)
# Checks: freshness windows, evidence requirements, budget limits
```

### Combined Validation

```python
from omen.validation import create_validator

validator = create_validator()  # All three combined
result = validator.validate(packet, state, context)
```

---

## Tool Execution

### Tool Protocol

```python
class Tool(Protocol):
    @property
    def name(self) -> str: ...
    
    @property
    def description(self) -> str: ...
    
    @property
    def safety(self) -> ToolSafety: ...  # READ, WRITE, MIXED
    
    def execute(self, params: dict) -> ToolResult: ...
```

### Tool Safety

```python
class ToolSafety(Enum):
    READ = "READ"      # No side effects, freely available
    WRITE = "WRITE"    # Side effects, requires authorization
    MIXED = "MIXED"    # Context-dependent
```

### Authorization Flow

```
L5 issues ToolAuthorizationToken
           │
           ▼
    ActiveToken in Ledger
           │
           ▼
L6 requests tool execution
           │
           ▼
Registry.execute(tool, params, token)
           │
    ┌──────┴──────┐
    │             │
READ tool    WRITE tool
    │             │
    ▼             ▼
Execute      Check token
directly     ├── Valid? Execute
             └── Invalid? UnauthorizedToolError
```

### Evidence Grounding

Every tool execution creates evidence:

```python
result = registry.execute("clock", {})

result.evidence_ref:
  ref_id: "ev_a1b2c3d4e5f6"
  ref_type: "tool_output"
  tool_name: "clock"
  timestamp: 2024-...
  reliability_score: 0.95
  raw_data: {"current_time": "..."}
```

Observations should reference this evidence.

---

## Integrity System

### Safe Modes

Progressive safety states:

```
NORMAL → CAUTIOUS → RESTRICTED → HALTED
  │         │            │          │
  │         │            │          └── No execution
  │         │            └── No WRITE operations
  │         └── Verify everything
  └── Full operation
```

### Budget Enforcement

```python
monitor = IntegrityMonitor()

# Check budget
event = monitor.check_budget(ledger)
if event and event.alert_type == AlertType.BUDGET_EXCEEDED:
    # Tokens revoked, execution halted
    pass

# Thresholds
# 80% consumed → WARNING
# 100% consumed → CRITICAL, halt execution
```

### Constitutional Veto

L1 can halt execution:

```python
# L1 emits IntegrityAlertPacket with alert_type="CONSTITUTIONAL_VETO"
# Monitor detects and:
#   1. Revokes all active tokens
#   2. Transitions to HALTED mode
#   3. Emits CRITICAL event
```

### Token Revocation

```python
# Individual revocation
monitor.revoke_token(ledger, "tok_123", "Policy violation")

# Bulk revocation (on budget exceed)
monitor._revoke_all_tokens(ledger)
```

---

## Data Flow

### Northbound Bus (Telemetry)

```
L6 → L5 → L4 → L3 → L2 → L1 → (Integrity)

Packet types:
- OBSERVATION (L6 reports)
- TASK_RESULT (execution outcomes)
- BELIEF_UPDATE (state changes)
- ESCALATION (handoff requests)
- INTEGRITY_ALERT (warnings)
```

### Southbound Bus (Directives)

```
L1 → L2 → L3 → L4 → L5 → L6

Packet types:
- DECISION (action selection)
- VERIFICATION_PLAN (info gathering)
- TOOL_AUTHORIZATION (permissions)
- TASK_DIRECTIVE (instructions)
```

### Integrity Overlay

```
            ┌─────────────────┐
            │    INTEGRITY    │
            │     MONITOR     │
            └────────┬────────┘
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
   Northbound    Southbound    Ledger
      Bus           Bus        Updates
```

The Integrity Monitor:
- Subscribes to both buses
- Monitors all traffic
- Can trigger alerts and safe mode transitions
- Receives L1 vetoes

---

## Extension Points

### Custom Tools

```python
from omen.tools import BaseTool, ToolResult, ToolSafety

class MyTool(BaseTool):
    @property
    def name(self) -> str:
        return "my_tool"
    
    @property
    def description(self) -> str:
        return "Does something useful"
    
    @property
    def safety(self) -> ToolSafety:
        return ToolSafety.READ
    
    def execute(self, params: dict) -> ToolResult:
        # Implementation
        return ToolResult.ok(data={"result": "..."}, tool_name=self.name)

# Register
registry.register(MyTool())
```

### Custom Templates

```python
from omen.templates import EpisodeTemplate, TemplateStep

CUSTOM_TEMPLATE = EpisodeTemplate(
    template_id=TemplateID.TEMPLATE_A,  # Or custom ID
    name="Custom Flow",
    description="My custom episode pattern",
    steps=[
        TemplateStep(
            step_id="step_1",
            fsm_state=FSMState.S1_SENSE,
            owner_layer=LayerSource.LAYER_6,
            packet_type=PacketType.OBSERVATION,
            next_steps=["step_2"],
        ),
        # ... more steps
    ],
    entry_step="step_1",
    exit_steps=["final_step"],
    constraints=TemplateConstraints(...),
)
```

### Custom Storage

```python
from omen.episode import EpisodeStore, EpisodeRecord

class PostgresStore:
    """PostgreSQL-backed episode storage."""
    
    def save(self, episode: EpisodeRecord) -> None:
        # Implementation
        pass
    
    def load(self, correlation_id: UUID) -> EpisodeRecord | None:
        # Implementation
        pass
    
    # ... other methods

# Use with orchestrator
orchestrator = create_orchestrator(episode_store=PostgresStore(...))
```

### Custom LLM Client

```python
from omen.layers import LLMClient

class AnthropicClient:
    """Anthropic Claude client."""
    
    def complete(self, system_prompt: str, user_message: str, **kwargs) -> str:
        # Implementation using anthropic SDK
        pass

# Use with layer pool
pool = create_layer_pool(llm_client=AnthropicClient())
```

---

## Performance Considerations

### LLM Latency

- Average layer invocation: 1-2 seconds
- Full episode (6 steps): 10-15 seconds
- Consider parallel invocation for independent layers (future enhancement)

### Memory Usage

- Layers are stateless; context built fresh each invocation
- Episode records grow with step count
- Consider archiving old episodes in production

### Cost Optimization

- Use `gpt-4o-mini` for development/testing (~$0.0004/call)
- Reserve `gpt-4o` for production/critical decisions
- Budget enforcement prevents runaway costs

---

## Testing Strategy

### Unit Tests (~800)

- Each component tested in isolation
- Mocked dependencies
- Fast execution (<10s for full unit suite)

### Integration Tests (~35)

- Real LLM calls
- End-to-end episode execution
- Requires `OPENAI_API_KEY`
- Marked with `@pytest.mark.integration`

### Test Organization

```
tests/
├── test_vocabulary/      # Enum tests
├── test_schemas/         # Packet schema tests
├── test_validation/      # Validator tests
├── test_templates/       # Template tests
├── test_compiler/        # Compiler tests
├── test_layers/          # Layer tests
├── test_buses/           # Bus tests
├── test_orchestrator/    # Orchestrator tests
├── test_tools/           # Tool tests
├── test_episode/         # Persistence tests
├── test_integrity/       # Integrity tests
├── test_observability/   # Observability tests
└── integration/          # Integration tests
```

---

## Troubleshooting

### Common Issues

**"Layer not found in pool"**
- Check layer is registered: `pool.has_layer(LayerSource.LAYER_5)`
- Ensure `create_layer_pool()` includes the layer

**"Contract violation"**
- Layer emitting packet type it's not allowed to
- Check `LayerContract.can_emit` for the layer

**"Budget exceeded"**
- Increase token/tool budget in context
- Or handle gracefully with overrun approval

**"Template validation failed"**
- Check FSM transitions are legal
- Verify packet types match layer contracts

### Debug Mode

```python
from omen.observability import enable_debug

enable_debug(output_dir="./debug")
# Run episode
# Check ./debug/*.json for full LLM interactions
```

### Logging

```python
from omen.observability import configure_logging
import logging

configure_logging(level=logging.DEBUG)
# Detailed logs for all components
```
