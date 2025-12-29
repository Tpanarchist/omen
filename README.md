# OMEN — Operational Monitoring & Engagement Nexus

[![Tests](https://img.shields.io/badge/tests-833%20passing-brightgreen)]()
[![Python](https://img.shields.io/badge/python-3.12%2B-blue)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()

An Extended ACE (Autonomous Cognitive Entity) Framework implementation for building LLM-substrate cognitive agents with constitutional sovereignty, epistemic hygiene, and auditable decision-making.

## Overview

OMEN implements a **cognition-first AGI architecture** based on Dave Shapiro's ACE Framework, treating LLM instances as first-class cognitive entities rather than simple API endpoints. The framework provides:

- **6-Layer Cognitive Hierarchy** — From constitutional oversight (L1) to task execution (L6)
- **Structured Packet Communication** — Type-safe MCP envelopes for inter-layer messaging
- **Episode State Machine** — Canonical templates (A-H) for common cognitive patterns
- **Budget & Token Management** — Resource tracking with authorization enforcement
- **Integrity Overlay** — Safe modes, constitutional vetoes, and budget enforcement
- **Full Observability** — Structured logging, metrics collection, debug capture

## Quick Start

```bash
# Clone and setup
git clone https://github.com/Tpanarchist/omen.git
cd omen
python3.12 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest                           # All 833 tests
pytest -m "not integration"      # Unit tests only (~800 tests, fast)
pytest -m integration            # Integration tests (requires OPENAI_API_KEY)
```

## Basic Usage

```python
from omen.orchestrator import create_orchestrator
from omen.vocabulary import TemplateID, StakesLevel, QualityTier
from omen.clients import create_openai_client
from omen.episode import create_sqlite_store

# Create orchestrator with real LLM
orchestrator = create_orchestrator(
    llm_client=create_openai_client(),
    episode_store=create_sqlite_store("episodes.db"),
)

# Run an episode using Template A (Grounding Loop)
result = orchestrator.run_template(
    TemplateID.TEMPLATE_A,
    stakes_level=StakesLevel.LOW,
    quality_tier=QualityTier.PAR,
)

print(f"Success: {result.success}")
print(f"Steps executed: {result.step_count}")
print(f"Duration: {result.total_duration_seconds:.1f}s")

# Query episode history
history = orchestrator.list_episodes(template_id="TEMPLATE_A", limit=10)
```

## Architecture

```
                              User Request
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          ORCHESTRATOR                               │
│  • Template selection    • Compilation    • Execution               │
│  • Episode persistence   • Metrics hooks  • Debug capture           │
└─────────────────────────────────────────────────────────────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              ▼                    ▼                    ▼
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│     COMPILER     │    │      RUNNER      │    │   LAYER POOL     │
│ Template → Steps │    │  Step execution  │    │  L1-L6 + LLM     │
└──────────────────┘    └──────────────────┘    └──────────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              ▼                    ▼                    ▼
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│      BUSES       │    │      LEDGER      │    │      TOOLS       │
│  North/South     │    │  Budget/Tokens   │    │  5 built-in      │
└──────────────────┘    └──────────────────┘    └──────────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              ▼                    ▼                    ▼
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│    INTEGRITY     │    │   PERSISTENCE    │    │  OBSERVABILITY   │
│   Safe modes     │    │  SQLite store    │    │  Logs/Metrics    │
└──────────────────┘    └──────────────────┘    └──────────────────┘
```

## Core Components

### ACE Layers (L1-L6)

Each layer is an LLM instance with specific responsibilities and contracts:

| Layer | Name | Role | Key Outputs |
|-------|------|------|-------------|
| L1 | Aspirational | Constitutional oversight, mission posture | IntegrityAlert, BeliefUpdate |
| L2 | Global Strategy | Strategic direction, campaign framing | BeliefUpdate (strategy) |
| L3 | Agent Model | Self-awareness, capability assessment | BeliefUpdate (capabilities) |
| L4 | Executive Function | Planning, budgets, Definition of Done | BeliefUpdate (plans) |
| L5 | Cognitive Control | Decision-making, task arbitration | Decision, ToolAuthorization |
| L6 | Task Prosecution | Execution, reality grounding | Observation, TaskResult |

### Episode Templates

Canonical patterns for common cognitive workflows:

| Template | Name | Purpose | Key Pattern |
|----------|------|---------|-------------|
| A | Grounding Loop | Base sensing cycle | Sense → Model → Decide |
| B | Verification Loop | Gather info before acting | VERIFY_FIRST handling |
| C | Read-Only Act | Safe read operations | ACT with READ tools |
| D | Write Act | Consequential actions | ACT with WRITE + authorization |
| E | Escalation | Human handoff | ESCALATE flow |
| F | Degraded Tools | Partial tool availability | TOOLS_PARTIAL handling |
| G | Compile-to-Code | Code generation | Multi-step compilation |
| H | Full-Stack Mission | All 6 layers | Complete cognitive cycle |

### Packet Types

9 structured packet types for inter-layer communication:

- **ObservationPacket** — L6 reports from reality
- **BeliefUpdatePacket** — Epistemic state changes
- **DecisionPacket** — L5 decision outcomes (ACT, VERIFY_FIRST, ESCALATE, DEFER)
- **VerificationPlanPacket** — Information gathering plans
- **ToolAuthorizationToken** — WRITE tool permissions
- **TaskDirectivePacket** — Execution instructions
- **TaskResultPacket** — Execution outcomes
- **EscalationPacket** — Human handoff requests
- **IntegrityAlertPacket** — System health warnings

## Project Structure

```
src/omen/
├── vocabulary/        # 18 enumerated types (enums.py)
├── schemas/           # Pydantic models for all packet types
│   ├── mcp_envelope.py
│   ├── packet_header.py
│   └── packets/       # 9 packet type schemas
├── validation/        # 3-layer validation stack
│   ├── schema_validator.py
│   ├── fsm_validator.py
│   └── invariant_validator.py
├── templates/         # Episode templates A-H
│   ├── canonical.py
│   └── validator.py
├── compiler/          # Template → CompiledEpisode
│   ├── context.py
│   ├── compiled.py
│   └── compiler.py
├── layers/            # ACE layer implementations
│   ├── base.py
│   ├── contracts.py
│   └── prompts/       # System prompts for L1-L6
├── buses/             # Inter-layer communication
│   ├── northbound.py  # Telemetry (L6→L1)
│   └── southbound.py  # Directives (L1→L6)
├── orchestrator/      # Execution coordination
│   ├── ledger.py      # Budget/token tracking
│   ├── pool.py        # Layer instance management
│   ├── runner.py      # Step-by-step execution
│   └── orchestrator.py # Unified API
├── tools/             # L6 tool execution
│   ├── base.py        # Tool protocol
│   ├── registry.py    # Tool management
│   └── builtin.py     # 5 built-in tools
├── clients/           # LLM client implementations
│   └── openai_client.py
├── episode/           # Persistence
│   ├── record.py      # Episode/Step/Packet records
│   └── storage.py     # InMemory + SQLite stores
├── integrity/         # Safety overlay
│   └── monitor.py     # Budget enforcement, vetoes
└── observability/     # Logging, metrics, debug
    ├── logging.py
    ├── metrics.py
    └── debug.py
```

## Built-in Tools

L6 can execute these tools with proper authorization:

| Tool | Safety | Description |
|------|--------|-------------|
| `clock` | READ | Current date/time |
| `file_read` | READ | Read local files |
| `file_write` | WRITE | Write files (requires token) |
| `http_get` | READ | Fetch URLs |
| `env_read` | READ | Safe environment variables |

```python
from omen.tools import create_default_registry

registry = create_default_registry()
result = registry.execute("clock", {})
print(result.data)  # {"current_time": "2024-...", "timezone": "UTC"}
```

## Integrity & Safety

The Integrity Monitor enforces system constraints:

```python
from omen.integrity import create_monitor, SafeMode

monitor = create_monitor()

# Budget enforcement
event = monitor.check_budget(ledger)  # Returns alert if >80% consumed

# Safe mode transitions
monitor.transition_safe_mode(SafeMode.RESTRICTED, "Budget warning")

# Constitutional veto (from L1)
if monitor.is_halted:
    print("Execution blocked by integrity layer")
```

Safe modes: `NORMAL` → `CAUTIOUS` → `RESTRICTED` → `HALTED`

## Observability

### Structured Logging

```python
from omen.observability import configure_logging, LogContext, get_logger

configure_logging(level=logging.INFO, json_format=True)
logger = get_logger("my_component")

with LogContext(correlation_id):
    logger.info("Processing episode")  # Includes correlation_id
```

### Metrics

```python
from omen.observability import get_metrics

metrics = get_metrics()
metrics.episodes_total.inc()
metrics.episode_duration_seconds.observe(5.5)

# Export all metrics
print(metrics.to_dict())
```

### Debug Mode

```python
from omen.observability import enable_debug, get_debug_recorder

enable_debug(output_dir="./debug_captures")

# After execution
captures = get_debug_recorder().get_captures(layer="5")
for c in captures:
    print(c.raw_response)  # Full LLM response
```

## Testing

```bash
# Full test suite (833 tests)
pytest

# By category
pytest tests/test_vocabulary/       # Enums and types
pytest tests/test_schemas/          # Packet schemas
pytest tests/test_validation/       # Validation stack
pytest tests/test_templates/        # Episode templates
pytest tests/test_compiler/         # Template compilation
pytest tests/test_layers/           # Layer infrastructure
pytest tests/test_buses/            # Bus routing
pytest tests/test_orchestrator/     # Execution coordination
pytest tests/test_tools/            # Tool execution
pytest tests/test_episode/          # Persistence
pytest tests/test_integrity/        # Safety overlay
pytest tests/test_observability/    # Logging/metrics

# Integration tests (requires OPENAI_API_KEY)
pytest -m integration -v -s
```

## Configuration

### Environment Variables

```bash
OPENAI_API_KEY=sk-...  # Required for integration tests and real LLM usage
```

### Orchestrator Configuration

```python
from omen.orchestrator import OrchestratorConfig, Orchestrator

config = OrchestratorConfig(
    default_stakes=StakesLevel.LOW,
    default_quality=QualityTier.PAR,
    default_token_budget=1000,
    default_tool_call_budget=10,
    max_steps=100,
    validate_templates=True,
    auto_save=True,
)

orchestrator = Orchestrator(config=config)
```

## Cost Estimation

Using `gpt-4o-mini` (default):
- Per layer invocation: ~$0.0004
- Per episode (Template A, 6 steps): ~$0.002
- Full test suite integration: ~$0.40

## Documentation

- [OMEN Specification](docs/spec/OMEN.md) — Full framework specification
- [ACE Framework](docs/spec/ACE_Framework.md) — Foundational cognitive architecture
- [Architecture Guide](docs/ARCHITECTURE.md) — Detailed component documentation

## Roadmap

- [x] **Phase 1**: Full Layer Integration (Template H, all 6 layers validated)
- [x] **Phase 2**: Real Tool Execution (5 tools, authorization enforcement)
- [x] **Phase 3**: Persistence (SQLite storage, episode records)
- [x] **Phase 4**: Integrity Overlay (safe modes, vetoes, budget enforcement)
- [x] **Phase 5**: Observability (logging, metrics, debug capture)
- [ ] **Phase 6**: EVE Online Domain Binding (ESI client, market tools)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Ensure all tests pass (`pytest`)
4. Submit a pull request

## License

MIT License — See [LICENSE](LICENSE) for details.

## Acknowledgments

- [Dave Shapiro](https://github.com/daveshap) — ACE Framework creator
- [Anthropic](https://anthropic.com) — Claude AI assistance in development
