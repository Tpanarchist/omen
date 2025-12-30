# Cognitive Process Visualizer & Transcript Exporter

## Overview

The Cognitive Transcript Generator makes OMEN's cognitive processes transparent and auditable by capturing episode execution and generating human-readable transcripts.

## Features

- **Seven-Section Transcript Format**:
  1. **Episode Header**: Metadata, budgets, policy context
  2. **Cognitive Flow**: Step-by-step layer reasoning with LLM outputs
  3. **Packet Flow Trace**: Causation chains showing information flow
  4. **Budget Timeline**: Resource consumption (tokens, tool calls, time)
  5. **Epistemic Hygiene**: Beliefs, evidence, assumptions tracking
  6. **Integrity Events**: Alerts and safe mode transitions
  7. **Summary**: Outcome, efficiency metrics, lessons learned

- **Multiple Output Formats**: Plain text (UTF-8 encoded)
- **Configurable Verbosity**: Include/exclude LLM reasoning and raw prompts
- **Automatic Budget Tracking**: Captures token, tool, and time consumption per step
- **Tool Execution Details**: Records all tool invocations with results

## Usage

### Basic Usage

```python
from omen.orchestrator import create_orchestrator
from omen.vocabulary import TemplateID
from omen.demo import CognitiveTranscriptGenerator

# Run an episode
orchestrator = create_orchestrator()
result = orchestrator.run_template(TemplateID.TEMPLATE_A)

# Generate transcript
generator = CognitiveTranscriptGenerator()
generator.from_episode_result(result)
transcript = generator.generate_transcript()

# Save to file
generator.save("transcripts/episode_001.txt")
```

### Configuration Options

```python
generator = CognitiveTranscriptGenerator(
    include_llm_reasoning=True,   # Extract reasoning from LLM responses
    include_raw_prompts=False,    # Include full prompts (verbose)
    max_content_length=500,       # Max chars for content summaries
)
```

### With Debug Captures

```python
# Enable debug mode for full LLM interaction capture
from omen.observability import enable_debug_mode

enable_debug_mode()

result = orchestrator.run_template(TemplateID.TEMPLATE_A)

# Pass debug captures to generator
generator.from_episode_result(
    result,
    debug_captures=get_debug_captures(),  # From DebugRecorder
)
```

## Demo Script

Run the demonstration:

```bash
python demos/cognitive_transcript_demo.py
```

This will:
1. Initialize a mock orchestrator
2. Run Template A (Grounding Loop)
3. Generate a complete transcript
4. Save to `transcripts/` directory
5. Display preview in console

## Output Example

```
================================================================================
COGNITIVE EPISODE TRANSCRIPT
================================================================================
  Episode ID: 6e8b4d85-e438-405e-b561-8f4c77904fde
  Template: TEMPLATE_A
  Started: 2025-12-30T08:47:33Z
  Completed: 2025-12-30T08:47:33Z
  Duration: 1.5s
  Status: SUCCESS
  Final Step: review

Context:
  Stakes Level: MEDIUM
  Quality Tier: PAR
  Tools State: TOOLS_OK

Budgets:
  Token: 2000 allocated → 1847 consumed (92.4%)
  Tool Calls: 5 allocated → 3 consumed (60.0%)
  Time: 120s allocated → 75s consumed (62.5%)
...
```

## Use Cases

### 1. Debugging Cognitive Processes
Understand why the system made specific decisions by reviewing step-by-step reasoning.

### 2. Auditing Decision Rationale
Generate reviewable transcripts for compliance, verification, or stakeholder presentations.

### 3. Documentation & Examples
Create examples for papers, presentations, or technical documentation.

### 4. Validation & Verification
Verify that layers are reasoning correctly according to their contracts.

### 5. Performance Analysis
Analyze budget consumption patterns to optimize resource allocation.

## Architecture

### Components

- **`CognitiveTranscriptGenerator`**: Main class for transcript generation
- **`EpisodeCapture`**: Data structure capturing complete episode execution
- **`StepCapture`**: Data structure capturing single step details
- **`formatting_utils`**: ASCII art, progress bars, text formatting

### Data Flow

```
EpisodeResult (from Orchestrator)
    ↓
CognitiveTranscriptGenerator.from_episode_result()
    ↓
EpisodeCapture (internal representation)
    ↓
generate_transcript() → Seven sections
    ↓
Plain text output (UTF-8)
```

## Testing

Run tests:

```bash
pytest tests/demo/test_transcript_generator.py -v
```

Test coverage:
- ✅ Generator initialization
- ✅ EpisodeResult conversion
- ✅ All seven sections generation
- ✅ Budget visualization
- ✅ File export with UTF-8 encoding
- ✅ Edge cases (no steps, missing data, errors)
- ✅ Integration with mock orchestrator

## Future Enhancements

### Planned Features

1. **HTML Output**: Interactive transcripts with collapsible sections
2. **JSON Export**: Programmatic analysis support
3. **Markdown Output**: For documentation integration
4. **Live Capture**: Real-time streaming via callback hooks
5. **Mermaid Diagrams**: Packet causation graphs
6. **Comparison View**: Side-by-side episode analysis
7. **Interactive TUI**: Terminal UI browser using Rich

### Phase 2: Live Capture

Currently post-hoc only. Future enhancement will add:

```python
generator = CognitiveTranscriptGenerator()

# Live capture via callbacks
result = orchestrator.run_template(
    TemplateID.TEMPLATE_A,
    on_step_complete=generator.capture_step,  # Hook
)

transcript = generator.generate_transcript()
```

## File Structure

```
src/omen/demo/
├── __init__.py                     # Module exports
├── transcript_generator.py         # Main implementation
└── formatting_utils.py             # ASCII art, helpers

demos/
└── cognitive_transcript_demo.py    # Demo script

tests/demo/
├── __init__.py
└── test_transcript_generator.py    # Comprehensive tests

transcripts/                         # Generated outputs (gitignored)
└── episode_*.txt
```

## API Reference

### CognitiveTranscriptGenerator

#### Constructor

```python
CognitiveTranscriptGenerator(
    include_llm_reasoning: bool = True,
    include_raw_prompts: bool = False,
    max_content_length: int = 500,
)
```

#### Methods

- **`from_episode_result(result, debug_captures=None, layer_prompts=None)`**: Build capture from EpisodeResult
- **`generate_transcript() -> str`**: Generate complete transcript
- **`save(filepath)`**: Save transcript to file (creates parent directories)

### Formatting Utilities

- **`format_progress_bar(consumed, total, width=20)`**: ASCII progress bar
- **`format_duration(seconds)`**: Human-readable duration
- **`format_packet_summary(packet, max_length=100)`**: Concise packet description
- **`format_section_header(title, width=80)`**: Section headers with borders
- **`format_box_header(title, width=77)`**: Box-style step headers
- **`format_percentage(value, decimals=1)`**: Float to percentage string
- **`truncate_text(text, max_length, suffix="...")`**: Text truncation

## Performance

- **Generation Time**: < 100ms for typical episodes (5-10 steps)
- **Memory Usage**: Minimal, processes EpisodeResult in-place
- **File Size**: ~5-10KB per episode (varies with verbosity)

## License

Part of the OMEN framework. See main project LICENSE.
