# Changelog

All notable changes to OMEN are documented in this file.

## [0.1.0] - 2024-12-29

### 🎉 Initial Release — Production-Ready Core

OMEN reaches production-ready status with 833 passing tests across all core components.

---

## Development Phases

### Phase 0-4: Foundation (Levels 0-4)

**Tests: ~350**

#### Level 0: Vocabulary
- 18 enumerated types for type safety
- `LayerSource`, `PacketType`, `FSMState`, `EpistemicStatus`, etc.
- Foundation for all type-safe operations

#### Level 1: MCP Envelope
- `MCPEnvelope` with correlation_id, causation_id, timestamps
- `RoutingInfo` for bus routing metadata
- Serialization/deserialization support

#### Level 2: Core Schemas
- `PacketHeader` with packet_type, packet_id, schema_version
- `EpistemicMetadata` for confidence and status tracking
- `EvidenceMetadata` for grounding claims

#### Level 3: Packet Schemas
- 9 packet types fully specified:
  - `ObservationPacket` — L6 reality reports
  - `BeliefUpdatePacket` — Epistemic state changes
  - `DecisionPacket` — L5 action selection
  - `VerificationPlanPacket` — Information gathering
  - `ToolAuthorizationToken` — WRITE permissions
  - `TaskDirectivePacket` — Execution instructions
  - `TaskResultPacket` — Execution outcomes
  - `EscalationPacket` — Human handoff
  - `IntegrityAlertPacket` — System warnings

#### Level 4: Validation Stack
- Three-layer validation:
  - `SchemaValidator` — Pydantic structural validation
  - `FSMValidator` — State machine compliance
  - `InvariantValidator` — Business rules
- Combined validator factory

---

### Phase 5: Templates (Level 5)

**Tests: ~425**

#### Canonical Templates A-G
- Template A: Grounding Loop (Sense → Model → Decide)
- Template B: Verification Loop (VERIFY_FIRST handling)
- Template C: Read-Only Act (READ tool operations)
- Template D: Write Act (WRITE with authorization)
- Template E: Escalation (Human handoff)
- Template F: Degraded Tools (TOOLS_PARTIAL handling)
- Template G: Compile-to-Code (Multi-step generation)

#### Template Validator
- 7 validation rules for template correctness
- FSM transition verification
- Layer contract enforcement

---

### Phase 6: Compiler (Level 6)

**Tests: ~460**

#### Template Compilation
- `CompilationContext` with stakes, quality, budgets
- `CompiledEpisode` with executable steps
- MCP field binding at compile time
- Constraint validation before execution

#### Context Factories
- `create_context()` for default contexts
- Stakes/quality/tools state configuration
- Budget allocation

---

### Phase 7: ACE Layers (Level 7)

**Tests: ~580**

#### Bus Infrastructure
- `NorthboundBus` — Telemetry L6→L1
- `SouthboundBus` — Directives L1→L6
- `BusMessage` wrapper with routing
- Resilient delivery (log errors, continue)

#### Layer Contracts
- 7 contracts (L1-L6 + Integrity)
- Emit/receive validation
- O(1) set lookups for performance

#### Layer Base Class
- `Layer` abstract base with 6-step invoke
- `LLMClient` protocol for swappable clients
- `MockLLMClient` for testing
- `ConfigurableLayer` for prompt injection

#### System Prompts
- L1: Constitutional oversight (18 imperatives)
- L2: Strategic direction
- L3: Self-awareness and capabilities
- L4: Planning and budgets
- L5: Decision-making (4 outcomes)
- L6: Task execution (vat boundary)

---

### Phase 8: Orchestrator (Level 8)

**Tests: ~680**

#### Episode Ledger
- `BudgetState` — Token/tool/time tracking
- `ActiveToken` — Authorization with expiry
- `OpenDirective` — Task tracking
- Evidence and assumption management
- Contradiction detection

#### Layer Pool
- `LayerPool` — Layer instance management
- `create_layer_pool()` — Production factory
- `create_mock_layer_pool()` — Test factory
- Per-layer prompt/parser configuration

#### Episode Runner
- `EpisodeRunner` — Step-by-step execution
- `StepResult` / `EpisodeResult` — Outcome tracking
- Bus routing for packet distribution
- Ledger integration for state updates

#### Orchestrator API
- `Orchestrator` — Unified public interface
- `run_template()` — Execute by template ID
- `run_episode()` — Execute custom templates
- `compile_template()` — Compile without execution
- Configuration via `OrchestratorConfig`

---

### Phase 9: Integration Testing

**Tests: ~700**

#### OpenAI Client
- `OpenAIClient` implementing `LLMClient` protocol
- Environment variable authentication
- Retry logic for rate limits
- Token usage tracking

#### Integration Tests
- All 7 templates validated with real LLM
- Template H (Full-Stack) added for all 6 layers
- Northbound/southbound flow validation
- ~$0.40 total cost for full suite

#### Parser Enhancement
- `_infer_packet_type()` from payload signatures
- Handles LLM variability in output format
- Graceful error handling

---

### Phase 10: Tool Execution (Phase 2)

**Tests: ~730**

#### Tool Protocol
- `Tool` protocol with name, description, safety
- `ToolSafety` enum (READ, WRITE, MIXED)
- `ToolResult` with evidence refs
- `EvidenceRef` for grounding

#### Tool Registry
- `ToolRegistry` for registration/discovery
- Authorization enforcement for WRITE tools
- `UnauthorizedToolError` / `ToolNotFoundError`

#### Built-in Tools
- `ClockTool` (READ) — Current time
- `FileReadTool` (READ) — Read files
- `FileWriteTool` (WRITE) — Write files
- `HttpGetTool` (READ) — Fetch URLs
- `EnvironmentTool` (READ) — Safe env vars

#### L6 Integration
- Tool registry injection to ConfigurableLayer
- `execute_tool()` method on layers
- Token validation before WRITE execution

---

### Phase 11: Persistence (Phase 3)

**Tests: ~770**

#### Episode Records
- `EpisodeRecord` — Complete episode data
- `StepRecord` — Step execution details
- `PacketRecord` — Emitted packet data
- JSON serialization/deserialization

#### Storage Backends
- `EpisodeStore` protocol
- `InMemoryStore` — Testing
- `SQLiteStore` — Persistence
- Query API with filtering

#### Orchestrator Integration
- Auto-save on episode completion
- `get_episode()` / `list_episodes()` queries
- Configurable via `OrchestratorConfig`

---

### Phase 12: Integrity Overlay (Phase 4)

**Tests: ~800**

#### Safe Modes
- `SafeMode` enum: NORMAL → CAUTIOUS → RESTRICTED → HALTED
- Progressive safety escalation
- `check_safe_mode()` for operation blocking

#### Integrity Monitor
- `IntegrityMonitor` watching both buses
- Budget enforcement (80% warning, 100% halt)
- Token revocation on violations
- Constitutional veto processing

#### Alert System
- `IntegrityEvent` tracking
- `AlertType` and `AlertSeverity` enums
- Query API for event history
- Optional callback on alerts

---

### Phase 13: Observability (Phase 5)

**Tests: 833**

#### Structured Logging
- `ContextVar`-based correlation ID propagation
- `JSONFormatter` for production
- `ReadableFormatter` for development
- `LogContext` manager for scoped tracking

#### Metrics Collection
- `Counter` — Monotonically increasing
- `Gauge` — Up/down values
- `Histogram` — Distributions
- `MetricsRegistry` — Global singleton

#### Debug Mode
- `DebugCapture` — Full LLM interaction data
- `DebugRecorder` — Capture management
- File persistence option
- Query by correlation_id/layer

#### OpenAI Client Enhancement
- `on_usage` callback for token tracking
- Enables real-time metrics integration

---

## Summary

| Component | Tests | Status |
|-----------|-------|--------|
| Vocabulary | ~30 | ✅ Complete |
| Schemas | ~120 | ✅ Complete |
| Validation | ~80 | ✅ Complete |
| Templates | ~85 | ✅ Complete |
| Compiler | ~35 | ✅ Complete |
| Layers | ~140 | ✅ Complete |
| Buses | ~30 | ✅ Complete |
| Orchestrator | ~100 | ✅ Complete |
| Tools | ~30 | ✅ Complete |
| Persistence | ~45 | ✅ Complete |
| Integrity | ~30 | ✅ Complete |
| Observability | ~31 | ✅ Complete |
| Integration | ~35 | ✅ Complete |
| **Total** | **833** | ✅ Production Ready |

---

## Roadmap

### Planned
- [ ] EVE Online domain binding (ESI client, market tools)
- [ ] Anthropic Claude client
- [ ] Campaign orchestration (multi-episode)
- [ ] Parallel layer invocation
- [ ] Step branching based on decision outcomes
- [ ] Prometheus metrics export
- [ ] PostgreSQL storage backend

### Under Consideration
- [ ] Web UI for episode inspection
- [ ] Real-time dashboard
- [ ] A/B testing for prompts
- [ ] Multi-agent coordination
