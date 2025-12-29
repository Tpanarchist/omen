# OMEN Quick Start Guide

Get up and running with OMEN in 5 minutes.

## Prerequisites

- Python 3.12+
- OpenAI API key (for real LLM usage)

## Installation

```bash
# Clone repository
git clone https://github.com/Tpanarchist/omen.git
cd omen

# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install with dev dependencies
pip install -e ".[dev]"

# Verify installation
pytest tests/test_vocabulary/ -v
```

## Your First Episode

### 1. Simple Mock Execution

Start without an API key using mock responses:

```python
from omen.orchestrator import create_mock_orchestrator
from omen.vocabulary import TemplateID

# Create orchestrator with mock LLM
orchestrator = create_mock_orchestrator()

# Run Template A (Grounding Loop)
result = orchestrator.run_template(TemplateID.TEMPLATE_A)

print(f"Success: {result.success}")
print(f"Steps: {result.step_count}")
print(f"Final step: {result.final_step}")
```

### 2. Real LLM Execution

Set your API key and use real inference:

```bash
export OPENAI_API_KEY=sk-your-key-here
```

```python
from omen.orchestrator import create_orchestrator
from omen.vocabulary import TemplateID, StakesLevel, QualityTier
from omen.clients import create_openai_client

# Create orchestrator with real LLM
orchestrator = create_orchestrator(
    llm_client=create_openai_client(),
)

# Run episode with explicit context
result = orchestrator.run_template(
    TemplateID.TEMPLATE_A,
    stakes_level=StakesLevel.LOW,
    quality_tier=QualityTier.PAR,
)

print(f"Success: {result.success}")
print(f"Duration: {result.total_duration_seconds:.1f}s")

# Inspect individual steps
for step in result.steps_completed:
    print(f"  {step.step_id}: {step.layer.value} - success={step.success}")
    if step.output:
        print(f"    Response: {step.output.raw_response[:100]}...")
```

## Working with Templates

### Available Templates

```python
from omen.vocabulary import TemplateID

# List all template IDs
for t in TemplateID:
    print(f"  {t.value}")

# Output:
#   TEMPLATE_A  - Grounding Loop
#   TEMPLATE_B  - Verification Loop  
#   TEMPLATE_C  - Read-Only Act
#   TEMPLATE_D  - Write Act
#   TEMPLATE_E  - Escalation
#   TEMPLATE_F  - Degraded Tools
#   TEMPLATE_G  - Compile-to-Code
#   TEMPLATE_H  - Full-Stack Mission
```

### Template Constraints

Some templates have requirements:

```python
from omen.vocabulary import QualityTier, ToolsState

# Template D requires SUPERB tier (consequential actions)
result = orchestrator.run_template(
    TemplateID.TEMPLATE_D,
    quality_tier=QualityTier.SUPERB,
)

# Template F requires TOOLS_PARTIAL (degraded mode)
result = orchestrator.run_template(
    TemplateID.TEMPLATE_F,
    tools_state=ToolsState.TOOLS_PARTIAL,
)
```

## Adding Persistence

Save episodes to SQLite:

```python
from omen.orchestrator import create_orchestrator
from omen.episode import create_sqlite_store
from omen.clients import create_openai_client

# Create store
store = create_sqlite_store("my_episodes.db")

# Create orchestrator with persistence
orchestrator = create_orchestrator(
    llm_client=create_openai_client(),
    episode_store=store,
)

# Run episode (auto-saved)
result = orchestrator.run_template(TemplateID.TEMPLATE_A)

# Query history
history = orchestrator.list_episodes(limit=10)
for ep in history:
    print(f"{ep.correlation_id}: {ep.template_id} - success={ep.success}")

# Load specific episode
episode = orchestrator.get_episode(result.correlation_id)
print(f"Steps: {episode.step_count}")
print(f"Tokens used: {episode.budget_consumed.get('tokens', 0)}")
```

## Using Tools

### Built-in Tools

```python
from omen.tools import create_default_registry

registry = create_default_registry()

# List available tools
for tool in registry.list_tools():
    print(f"  {tool.name} ({tool.safety.value}): {tool.description}")

# Execute a READ tool (no authorization needed)
result = registry.execute("clock", {})
print(result.data)  # {"current_time": "...", "timezone": "UTC"}

# Read a file
result = registry.execute("file_read", {"path": "README.md"})
print(f"Content length: {result.data['size_bytes']} bytes")
```

### WRITE Tools Require Authorization

```python
from datetime import datetime, timedelta
from omen.orchestrator.ledger import ActiveToken

# Create authorization token
token = ActiveToken(
    token_id="tok_write_001",
    scope={"action": "write"},
    issued_at=datetime.now(),
    expires_at=datetime.now() + timedelta(hours=1),
    max_uses=5,
    uses_remaining=5,
)

# Now WRITE tool works
result = registry.execute(
    "file_write",
    {"path": "/tmp/test.txt", "content": "Hello OMEN!"},
    token=token,
)
print(f"Wrote {result.data['bytes_written']} bytes")
```

## Monitoring with Integrity

```python
from omen.integrity import create_monitor, SafeMode
from omen.orchestrator import create_ledger, BudgetState

# Create ledger with budget
ledger = create_ledger(
    correlation_id=result.correlation_id,
    budget=BudgetState(token_budget=1000, tool_call_budget=10),
)

# Create monitor
monitor = create_monitor()
monitor.register_ledger(ledger)

# Simulate consumption
ledger.budget.consume(tokens=850)  # 85% consumed

# Check budget
event = monitor.check_budget(ledger)
if event:
    print(f"Alert: {event.alert_type.value} - {event.message}")
    # Alert: budget_warning - Budget warning: tokens=85%

# Check safe mode
print(f"Safe mode: {monitor.safe_mode.value}")  # normal
```

## Observability

### Structured Logging

```python
import logging
from omen.observability import configure_logging, LogContext, get_logger

# Configure logging
configure_logging(level=logging.INFO)

logger = get_logger("my_app")

# Log with correlation ID
with LogContext(result.correlation_id):
    logger.info("Processing complete")
    # INFO    [a1b2c3d4] omen.my_app: Processing complete
```

### Metrics

```python
from omen.observability import get_metrics

metrics = get_metrics()

# Track custom events
metrics.episodes_total.inc()
metrics.tokens_consumed.inc(result.ledger_summary.get("budget", {}).get("tokens_consumed", 0))

# Export all metrics
print(metrics.to_dict())
```

### Debug Mode

```python
from omen.observability import enable_debug, get_debug_recorder

# Enable debug capture
enable_debug(output_dir="./debug_output")

# Run episode
result = orchestrator.run_template(TemplateID.TEMPLATE_A)

# Get captures
captures = get_debug_recorder().get_captures()
for c in captures:
    print(f"Layer {c.layer}: {len(c.raw_response)} chars")
    print(f"  Packets parsed: {len(c.parsed_packets)}")

# Check ./debug_output/ for full JSON captures
```

## Running Tests

```bash
# All tests
pytest

# Specific component
pytest tests/test_orchestrator/ -v

# With coverage
pytest --cov=omen --cov-report=html

# Integration tests (requires API key)
pytest -m integration -v -s
```

## Common Patterns

### Custom Template Execution

```python
from omen.templates import TEMPLATE_A

# Run with custom template
result = orchestrator.run_episode(
    template=TEMPLATE_A,
    stakes_level=StakesLevel.MEDIUM,
    token_budget=2000,
)
```

### Compilation Only

```python
# Compile without executing
compilation = orchestrator.compile_template(
    TemplateID.TEMPLATE_A,
    quality_tier=QualityTier.PAR,
)

if compilation.success:
    episode = compilation.episode
    print(f"Entry step: {episode.entry_step}")
    print(f"Total steps: {len(episode.steps)}")
else:
    for error in compilation.errors:
        print(f"Error: {error.message}")
```

### Layer Inspection

```python
# Access layer pool
pool = orchestrator.get_layer_pool()

# Check layer availability
from omen.vocabulary import LayerSource
print(f"Has L5: {pool.has_layer(LayerSource.LAYER_5)}")

# Get all layers
for source, layer in pool.get_all_layers().items():
    print(f"  {source.value}: {layer}")
```

## Next Steps

1. **Read the Architecture Guide** — [ARCHITECTURE.md](ARCHITECTURE.md)
2. **Explore Templates** — Understand Template A-H patterns
3. **Create Custom Tools** — Extend L6 capabilities
4. **Build Domain Binding** — Connect to your specific use case

## Getting Help

- **Tests as Documentation**: `tests/` contains examples of every feature
- **Debug Mode**: Enable verbose logging to trace issues
- **GitHub Issues**: Report bugs or request features
