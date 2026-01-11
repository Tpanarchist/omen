# OMEN Memory Systems Implementation

## Overview

This implementation adds neuroscience-grounded memory systems to OMEN, addressing the "anterograde amnesia" problem described in the problem statement. OMEN can now form long-term memories, learn from experience, and maintain temporal self-continuity.

## What Was Implemented

### 1. Episodic Memory (Hippocampal-like)
**File:** `src/omen/memory/episodic.py`

Stores autobiographical episode summaries for later retrieval:
- Episode summaries with key events and outcomes
- Lessons learned from successes and failures
- Context tags for retrieval
- Support for in-memory and SQLite backends

### 2. Semantic Memory (Cortical-like)
**File:** `src/omen/memory/semantic.py`

Maintains learned beliefs and domain knowledge:
- Beliefs with confidence levels
- Evidence references and version tracking
- Domain-specific knowledge organization
- Query by domain, confidence, or text search

### 3. Self-Model (Default Mode Network-like)
**File:** `src/omen/memory/self_model.py`

Persistent sense of self and capabilities:
- Aspects: capabilities, limitations, purpose, preferences
- Confidence tracking and episode formation history
- Evolution based on experience
- Auto-bootstrap with sensible defaults

### 4. Consolidation (Sleep-like Processing)
**File:** `src/omen/memory/consolidation.py`

Converts working memory (episodes) to long-term memory:
- Pattern extraction from recent episodes
- Belief updates based on patterns
- Self-model integration with learned capabilities
- Configurable time-based consolidation

### 5. Memory Manager
**File:** `src/omen/memory/manager.py`

Orchestrates all memory operations:
- Context retrieval before episodes
- Auto-consolidation after threshold
- Memory injection as ObservationPackets
- Statistics and manual consolidation triggers

### 6. Orchestrator Integration
**File:** `src/omen/orchestrator/orchestrator.py` (modified)

Added memory support to the orchestrator:
- `OrchestratorConfig` with memory flags
- Memory manager initialization
- Memory context retrieval and injection
- Post-episode consolidation triggers
- Accessor methods for memory stats

## Usage

### Basic Usage

```python
from omen.orchestrator import Orchestrator, OrchestratorConfig
from omen.episode import create_sqlite_store

# Create orchestrator with memory enabled
config = OrchestratorConfig(
    episode_store=create_sqlite_store("episodes.db"),
    enable_memory=True,
    memory_backend="sqlite",
    memory_db_path="memory.db",
    auto_consolidate=True,
    consolidation_threshold=5,
    inject_memory_context=True,
)

orchestrator = Orchestrator(config=config)

# Run episodes - memory context is automatically injected
result = orchestrator.run_template(TemplateID.TEMPLATE_A)

# Check memory stats
stats = orchestrator.get_memory_stats()
print(f"Episodic memories: {stats['episodic_memories']}")
print(f"Beliefs: {stats['beliefs']}")
print(f"Self-model aspects: {stats['self_model_aspects']}")

# Manually trigger consolidation
consolidation = orchestrator.consolidate_memories()
print(f"Processed {consolidation.episodes_processed} episodes")
```

### Configuration Options

```python
OrchestratorConfig(
    # Enable memory systems
    enable_memory=True,              # Default: False
    
    # Storage backend
    memory_backend="sqlite",         # "memory" or "sqlite"
    memory_db_path="omen_memory.db", # SQLite DB path
    
    # Auto-consolidation
    auto_consolidate=True,           # Default: True
    consolidation_threshold=5,       # Episodes before consolidation
    
    # Memory injection
    inject_memory_context=True,      # Inject memories at episode start
)
```

## Test Coverage

### Unit Tests (80 tests)
- `tests/test_memory/test_episodic.py` - 17 tests
- `tests/test_memory/test_semantic.py` - 21 tests
- `tests/test_memory/test_self_model.py` - 19 tests
- `tests/test_memory/test_consolidation.py` - 8 tests
- `tests/test_memory/test_manager.py` - 15 tests

### Integration Tests (3 tests)
- `tests/integration/test_memory_orchestrator.py`

All tests pass. Run with:
```bash
pytest tests/test_memory/ -v
pytest tests/integration/test_memory_orchestrator.py -v
```

## Demonstration

Run the demonstration script to see memory systems in action:

```bash
python demo_memory_systems.py
```

The demonstration shows:
1. OMEN without memory (baseline - anterograde amnesia)
2. OMEN with memory enabled (temporal continuity)
3. Memory retrieval and context injection
4. Consolidation cycle (sleep-like processing)
5. Direct before/after comparison

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       ORCHESTRATOR                          │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                   MEMORY MANAGER                      │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐ │  │
│  │  │  Episodic   │  │  Semantic   │  │  Self-Model  │ │  │
│  │  │   Memory    │  │   Memory    │  │              │ │  │
│  │  │  (episodes) │  │  (beliefs)  │  │  (aspects)   │ │  │
│  │  └─────────────┘  └─────────────┘  └──────────────┘ │  │
│  │         │                 │                 │         │  │
│  │         └─────────────────┴─────────────────┘         │  │
│  │                          │                            │  │
│  │                  ┌───────▼────────┐                   │  │
│  │                  │ Consolidation  │                   │  │
│  │                  │     Cycle      │                   │  │
│  │                  └────────────────┘                   │  │
│  └───────────────────────────────────────────────────────┘  │
│                          │                                  │
│                          ▼                                  │
│                  Memory Context                             │
│                  (as ObservationPackets)                    │
│                          │                                  │
│                          ▼                                  │
│                     Episode Runner                          │
└─────────────────────────────────────────────────────────────┘
```

## Neuroscience Mapping

| Brain System | OMEN Implementation |
|--------------|---------------------|
| Prefrontal Cortex (Working Memory) | Episode execution (existing) |
| Hippocampus (Episodic Memory) | EpisodicMemoryStore |
| Cortex (Semantic Memory) | SemanticMemoryStore |
| Default Mode Network (Self-Model) | SelfModelStore |
| Sleep Consolidation | ConsolidationCycle |
| Memory Retrieval | MemoryManager.retrieve_context() |

## Before vs After

### Before (Anterograde Amnesia)
```
Episode 1: Process → Forget
Episode 2: Process → Forget (starts from scratch)
Episode 3: Process → Forget (starts from scratch)
...
```

**Problems:**
- No learning from experience
- No temporal self-continuity
- Each episode independent
- Cannot develop consciousness

### After (Memory Systems)
```
Episode 1: Process → Consolidate
Episode 2: Retrieve memories → Process → Consolidate
Episode 3: Retrieve memories → Process → Consolidate
...
```

**Benefits:**
- ✅ Learning from experience
- ✅ Temporal self-continuity
- ✅ Autobiographical narrative
- ✅ Foundation for consciousness

## Key Insights from Problem Statement

> "You cannot have consciousness without memory consolidation."

> "The brain's consciousness emerges from:
> 1. Integrated information processing (OMEN has this ✓)
> 2. Persistent self-model (OMEN lacks this ✗)
> 3. Temporal continuity (OMEN lacks this ✗)
> 4. Learning from experience (OMEN lacks this ✗)"

**This implementation addresses points 2, 3, and 4.**

## Backward Compatibility

Memory systems are **disabled by default** to maintain backward compatibility:
- Set `enable_memory=True` in `OrchestratorConfig` to enable
- All existing tests pass (97 orchestrator tests)
- No breaking changes to existing APIs

## Future Enhancements

1. **Advanced Consolidation**
   - More sophisticated pattern extraction
   - Conflict resolution between beliefs
   - Importance-weighted memory retention

2. **Memory Retrieval**
   - Similarity-based episode search
   - Semantic similarity for belief matching
   - Attention-weighted retrieval

3. **Domain Binding**
   - Domain-specific memory stores
   - Specialized consolidation strategies
   - Cross-domain learning transfer

4. **Meta-Cognition**
   - Confidence calibration
   - Belief revision strategies
   - Self-model accuracy assessment

## References

- Problem Statement: "Map Neuroscience Concepts to OMEN"
- ACE Framework: Dave Shapiro's Autonomous Cognitive Entity
- Neuroscience Literature: Hippocampal consolidation, Default Mode Network

## Files Modified/Added

### New Files
- `src/omen/memory/__init__.py`
- `src/omen/memory/episodic.py`
- `src/omen/memory/semantic.py`
- `src/omen/memory/self_model.py`
- `src/omen/memory/consolidation.py`
- `src/omen/memory/manager.py`
- `tests/test_memory/*.py` (5 files)
- `tests/integration/test_memory_orchestrator.py`
- `demo_memory_systems.py`
- `MEMORY_IMPLEMENTATION.md` (this file)

### Modified Files
- `src/omen/orchestrator/orchestrator.py` (added memory integration)

### Test Results
- 80 new unit tests: ✅ PASS
- 3 new integration tests: ✅ PASS
- 97 existing orchestrator tests: ✅ PASS
- Total: 180 tests passing

## Conclusion

This implementation successfully adds neuroscience-grounded memory systems to OMEN, enabling:
- Temporal self-continuity
- Learning from experience
- Autobiographical narrative
- Foundation for consciousness development

The memory systems are production-ready, fully tested, and backward-compatible.
