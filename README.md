# OMEN — Operational Monitoring & Engagement Nexus

An Extended ACE (Autonomous Cognitive Entity) Framework implementation.

## Architecture

OMEN implements a cognition-first AGI architecture based on Dave Shapiro's ACE Framework,
extended with:

- Constitutional sovereignty (Layer 1 imperatives)
- Drives and homeostatic regulation
- Three-stage drive arbitration
- Epistemic, quality, and compute policies (E-POL, Q-POL, C-POL)
- Structured packet grammar with MCP envelopes
- Episode state machine with canonical templates
- System integrity overlay

## Project Structure

```
src/omen/
├── vocabulary/     # Enumerated types (epistemic status, stakes, tiers, etc.)
├── schemas/        # JSON Schemas and Pydantic models for packets
├── validation/     # Schema, FSM, and invariant validators
├── templates/      # Episode templates A-G and compiler
├── episode/        # Episode orchestrator and ledger
├── layers/         # ACE layer implementations
├── buses/          # Northbound and southbound bus implementations
├── integrity/      # System integrity overlay
└── bindings/       # Domain-specific adapters
    └── eve/        # EVE Online sensorium and effectors
```

## Setup

```bash
# Create virtual environment with Python 3.12
python3.12 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

## Documentation

- [ACE Framework](docs/spec/ACE_Framework.md) — Foundational cognitive architecture
- [OMEN Specification](docs/spec/OMEN.md) — Extended framework + protocol specification

## License

MIT
