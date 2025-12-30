"""
Tests for Cognitive Transcript Generator.

Tests transcript generation from EpisodeResult, section completeness,
formatting utilities, and file export functionality.
"""

import tempfile
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pytest

from omen.orchestrator import EpisodeResult, StepResult, create_mock_orchestrator
from omen.vocabulary import LayerSource, TemplateID
from omen.demo import CognitiveTranscriptGenerator, EpisodeCapture, StepCapture
from omen.demo.formatting_utils import (
    format_progress_bar,
    format_duration,
    format_packet_summary,
    format_section_header,
    format_box_header,
    format_percentage,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_step_result() -> StepResult:
    """Create a mock StepResult for testing."""
    return StepResult(
        step_id="test_step_1",
        layer=LayerSource.LAYER_6,
        success=True,
        packets_emitted=2,
        duration_seconds=1.5,
        tokens_consumed=150,
        tool_calls_consumed=1,
        time_consumed=1.5,
        fsm_state="S1_SENSE",
        context_summary={"template_id": "TEMPLATE_A"},
    )


@pytest.fixture
def mock_episode_result(mock_step_result: StepResult) -> EpisodeResult:
    """Create a mock EpisodeResult for testing."""
    return EpisodeResult(
        correlation_id=uuid4(),
        template_id="TEMPLATE_A",
        success=True,
        steps_completed=[mock_step_result],
        final_step="test_step_1",
        total_duration_seconds=1.5,
        errors=[],
        ledger_summary={
            "budget": {
                "token_budget": 2000,
                "tokens_consumed": 150,
                "tool_call_budget": 5,
                "tool_calls_consumed": 1,
                "time_budget_seconds": 120,
            },
            "stakes_level": "MEDIUM",
            "quality_tier": "PAR",
            "tools_state": "TOOLS_OK",
            "initial_seed": "Test seed",
            "assumptions": ["Test assumption"],
            "evidence": [],
        },
    )


@pytest.fixture
def generator() -> CognitiveTranscriptGenerator:
    """Create a transcript generator for testing."""
    return CognitiveTranscriptGenerator(
        include_llm_reasoning=True,
        include_raw_prompts=False,
        max_content_length=200,
    )


# =============================================================================
# GENERATOR TESTS
# =============================================================================

def test_generator_initialization():
    """Generator initializes with correct default parameters."""
    generator = CognitiveTranscriptGenerator()
    
    assert generator.include_llm_reasoning is True
    assert generator.include_raw_prompts is False
    assert generator.max_content_length == 500
    assert generator.capture is None


def test_generator_from_episode_result(generator: CognitiveTranscriptGenerator, mock_episode_result: EpisodeResult):
    """Generator can process EpisodeResult."""
    generator.from_episode_result(mock_episode_result)
    
    assert generator.capture is not None
    assert generator.capture.correlation_id == mock_episode_result.correlation_id
    assert generator.capture.template_id == "TEMPLATE_A"
    assert generator.capture.success is True
    assert len(generator.capture.steps) == 1
    
    # Verify budget data captured
    assert generator.capture.token_budget == 2000
    assert generator.capture.token_consumed == 150
    assert generator.capture.tool_budget == 5
    assert generator.capture.tool_consumed == 1


def test_generator_converts_step_results(generator: CognitiveTranscriptGenerator, mock_episode_result: EpisodeResult):
    """Generator correctly converts StepResult to StepCapture."""
    generator.from_episode_result(mock_episode_result)
    
    step = generator.capture.steps[0]
    assert isinstance(step, StepCapture)
    assert step.step_id == "test_step_1"
    assert step.layer == LayerSource.LAYER_6
    assert step.fsm_state == "S1_SENSE"
    assert step.duration_seconds == 1.5
    assert step.tokens_consumed == 150
    assert step.tool_calls_consumed == 1
    assert step.success is True


def test_generator_without_capture_raises_error(generator: CognitiveTranscriptGenerator):
    """Generator raises error when generating transcript without capture."""
    with pytest.raises(ValueError, match="No episode captured"):
        generator.generate_transcript()


# =============================================================================
# TRANSCRIPT GENERATION TESTS
# =============================================================================

def test_transcript_generation(generator: CognitiveTranscriptGenerator, mock_episode_result: EpisodeResult):
    """Generator produces complete transcript."""
    generator.from_episode_result(mock_episode_result)
    transcript = generator.generate_transcript()
    
    assert isinstance(transcript, str)
    assert len(transcript) > 0
    assert "COGNITIVE EPISODE TRANSCRIPT" in transcript


def test_transcript_includes_all_sections(generator: CognitiveTranscriptGenerator, mock_episode_result: EpisodeResult):
    """Generated transcript has all required sections."""
    generator.from_episode_result(mock_episode_result)
    transcript = generator.generate_transcript()
    
    # Section 1: Header
    assert "COGNITIVE EPISODE TRANSCRIPT" in transcript
    assert "Episode ID" in transcript
    assert "Template" in transcript
    assert "Budgets:" in transcript
    
    # Section 2: Cognitive Flow
    assert "COGNITIVE FLOW" in transcript
    assert "STEP 1:" in transcript
    
    # Section 3: Packet Flow
    assert "PACKET FLOW TRACE" in transcript
    
    # Section 4: Budget Timeline
    assert "RESOURCE CONSUMPTION" in transcript
    assert "Token Budget" in transcript
    
    # Section 5: Epistemic Hygiene
    assert "EPISTEMIC HYGIENE" in transcript
    assert "Beliefs Created" in transcript
    
    # Section 6: Integrity Events
    assert "INTEGRITY MONITORING" in transcript
    assert "Alerts Generated" in transcript
    
    # Section 7: Summary
    assert "EPISODE SUMMARY" in transcript
    assert "Outcome:" in transcript
    assert "Efficiency:" in transcript
    assert "END OF TRANSCRIPT" in transcript


def test_transcript_shows_budget_consumption(generator: CognitiveTranscriptGenerator, mock_episode_result: EpisodeResult):
    """Transcript includes budget consumption details."""
    generator.from_episode_result(mock_episode_result)
    transcript = generator.generate_transcript()
    
    assert "2000 allocated" in transcript  # Token budget
    assert "150 consumed" in transcript  # Token consumed
    assert "5 allocated" in transcript  # Tool budget
    assert "1 consumed" in transcript  # Tool consumed


def test_transcript_shows_step_details(generator: CognitiveTranscriptGenerator, mock_episode_result: EpisodeResult):
    """Transcript includes step-level details."""
    generator.from_episode_result(mock_episode_result)
    transcript = generator.generate_transcript()
    
    assert "test_step_1" in transcript
    assert "LAYER_6" in transcript or "Task Prosecution" in transcript
    assert "S1_SENSE" in transcript
    assert "1.5s" in transcript or "1500ms" in transcript


# =============================================================================
# FILE EXPORT TESTS
# =============================================================================

def test_save_to_file(generator: CognitiveTranscriptGenerator, mock_episode_result: EpisodeResult):
    """Transcript saves to file with correct encoding."""
    generator.from_episode_result(mock_episode_result)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = Path(tmpdir) / "test_transcript.txt"
        generator.save(filepath)
        
        assert filepath.exists()
        
        # Read back and verify UTF-8 encoding
        content = filepath.read_text(encoding="utf-8")
        assert "COGNITIVE EPISODE TRANSCRIPT" in content
        assert len(content) > 0


def test_save_creates_parent_directories(generator: CognitiveTranscriptGenerator, mock_episode_result: EpisodeResult):
    """Save creates parent directories if they don't exist."""
    generator.from_episode_result(mock_episode_result)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = Path(tmpdir) / "nested" / "path" / "transcript.txt"
        generator.save(filepath)
        
        assert filepath.exists()


# =============================================================================
# FORMATTING UTILITIES TESTS
# =============================================================================

def test_format_progress_bar():
    """Progress bar renders correctly."""
    bar = format_progress_bar(75, 100, 20)
    
    assert "[" in bar
    assert "]" in bar
    assert "75.0%" in bar
    assert "█" in bar
    assert "-" in bar


def test_format_progress_bar_zero_total():
    """Progress bar handles zero total gracefully."""
    bar = format_progress_bar(0, 0, 20)
    
    assert "0.0%" in bar
    assert "-" * 20 in bar


def test_format_progress_bar_full():
    """Progress bar shows 100% correctly."""
    bar = format_progress_bar(100, 100, 20)
    
    assert "100.0%" in bar
    assert "█" * 20 in bar


def test_format_duration_milliseconds():
    """Duration formats milliseconds correctly."""
    assert format_duration(0.045) == "45ms"
    assert format_duration(0.001) == "1ms"
    assert format_duration(0.999) == "999ms"


def test_format_duration_seconds():
    """Duration formats seconds correctly."""
    assert format_duration(1.234) == "1.2s"
    assert format_duration(45.678) == "45.7s"


def test_format_duration_minutes():
    """Duration formats minutes correctly."""
    assert format_duration(135.0) == "2m 15.0s"
    assert format_duration(65.5) == "1m 5.5s"


def test_format_section_header():
    """Section header formats correctly."""
    header = format_section_header("TEST SECTION", 40, "=")
    
    assert "TEST SECTION" in header
    assert "=" * 40 in header


def test_format_box_header():
    """Box header formats correctly."""
    box = format_box_header("Test Box", 40)
    
    assert "┌" in box
    assert "└" in box
    assert "Test Box" in box


def test_format_percentage():
    """Percentage formats correctly."""
    assert format_percentage(0.75) == "75.0%"
    assert format_percentage(0.123, decimals=2) == "12.30%"
    assert format_percentage(1.0) == "100.0%"


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

def test_full_workflow_with_mock_orchestrator():
    """Complete workflow from episode to transcript."""
    # Create mock orchestrator
    orchestrator = create_mock_orchestrator()
    
    # Run episode
    result = orchestrator.run_template(
        template_id=TemplateID.TEMPLATE_A,
    )
    
    # Generate transcript
    generator = CognitiveTranscriptGenerator()
    generator.from_episode_result(result)
    transcript = generator.generate_transcript()
    
    # Verify transcript
    assert len(transcript) > 0
    assert "COGNITIVE EPISODE TRANSCRIPT" in transcript
    assert "TEMPLATE_A" in transcript
    
    # Save to file
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = Path(tmpdir) / "integration_test.txt"
        generator.save(filepath)
        assert filepath.exists()


def test_transcript_with_multiple_steps():
    """Transcript handles episodes with multiple steps."""
    # Create result with multiple steps
    steps = [
        StepResult(
            step_id=f"step_{i}",
            layer=LayerSource.LAYER_6,
            success=True,
            duration_seconds=1.0,
            tokens_consumed=100,
            tool_calls_consumed=0,
            fsm_state=f"S{i}_STATE",
        )
        for i in range(1, 4)
    ]
    
    result = EpisodeResult(
        correlation_id=uuid4(),
        template_id="TEMPLATE_A",
        success=True,
        steps_completed=steps,
        final_step="step_3",
        total_duration_seconds=3.0,
        ledger_summary={
            "budget": {
                "token_budget": 2000,
                "tokens_consumed": 300,
                "tool_call_budget": 5,
                "tool_calls_consumed": 0,
                "time_budget_seconds": 120,
            },
            "stakes_level": "MEDIUM",
            "quality_tier": "PAR",
        },
    )
    
    generator = CognitiveTranscriptGenerator()
    generator.from_episode_result(result)
    transcript = generator.generate_transcript()
    
    # Verify all steps appear
    assert "STEP 1:" in transcript
    assert "STEP 2:" in transcript
    assert "STEP 3:" in transcript
    assert "step_1" in transcript
    assert "step_2" in transcript
    assert "step_3" in transcript


def test_transcript_with_errors():
    """Transcript handles failed episodes correctly."""
    result = EpisodeResult(
        correlation_id=uuid4(),
        template_id="TEMPLATE_A",
        success=False,
        steps_completed=[],
        errors=["Test error occurred"],
        total_duration_seconds=0.5,
        ledger_summary={
            "budget": {
                "token_budget": 2000,
                "tokens_consumed": 0,
                "tool_call_budget": 5,
                "tool_calls_consumed": 0,
                "time_budget_seconds": 120,
            },
        },
    )
    
    generator = CognitiveTranscriptGenerator()
    generator.from_episode_result(result)
    transcript = generator.generate_transcript()
    
    assert "FAILED" in transcript
    assert "Status: FAILED" in transcript or "success: False" in transcript.lower()


# =============================================================================
# EDGE CASE TESTS
# =============================================================================

def test_generator_with_no_steps():
    """Generator handles episodes with no steps."""
    result = EpisodeResult(
        correlation_id=uuid4(),
        template_id="TEMPLATE_A",
        success=False,
        steps_completed=[],
        total_duration_seconds=0.0,
        ledger_summary={},
    )
    
    generator = CognitiveTranscriptGenerator()
    generator.from_episode_result(result)
    transcript = generator.generate_transcript()
    
    assert "No steps recorded" in transcript or "0 steps" in transcript.lower()


def test_generator_with_missing_ledger_data():
    """Generator handles missing ledger data gracefully."""
    result = EpisodeResult(
        correlation_id=uuid4(),
        template_id="TEMPLATE_A",
        success=True,
        steps_completed=[],
        ledger_summary={},  # Empty ledger
    )
    
    generator = CognitiveTranscriptGenerator()
    generator.from_episode_result(result)
    transcript = generator.generate_transcript()
    
    # Should not crash, should use defaults
    assert "COGNITIVE EPISODE TRANSCRIPT" in transcript


def test_generator_with_very_long_content():
    """Generator truncates very long content correctly."""
    generator = CognitiveTranscriptGenerator(max_content_length=50)
    
    # Create step with long content
    long_text = "x" * 1000
    step = StepResult(
        step_id="test",
        layer=LayerSource.LAYER_6,
        success=True,
        duration_seconds=1.0,
        system_prompt=long_text,
    )
    
    result = EpisodeResult(
        correlation_id=uuid4(),
        template_id="TEMPLATE_A",
        success=True,
        steps_completed=[step],
        total_duration_seconds=1.0,
        ledger_summary={},
    )
    
    generator.from_episode_result(result)
    transcript = generator.generate_transcript()
    
    # Should be truncated
    assert long_text not in transcript  # Full text should not appear
    assert "..." in transcript  # Truncation marker should appear
