"""
Tests for OMEN CLI validator

Tests the command-line interface for the unified validator.
"""

import subprocess
import sys
from pathlib import Path


def test_cli_help():
    """Test --help flag works"""
    result = subprocess.run(
        [sys.executable, "validate_omen.py", "--help"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert "OMEN v0.7 Unified Validator" in result.stdout


def test_cli_validate_episode():
    """Test episode validation"""
    result = subprocess.run(
        [sys.executable, "validate_omen.py", "episode", 
         "goldens/v0.7/Episode.verify_loop.jsonl", "--no-timestamp-checks"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert "PASS" in result.stdout


def test_cli_validate_goldens():
    """Test golden fixtures validation"""
    result = subprocess.run(
        [sys.executable, "validate_omen.py", "goldens"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert "7 passed, 0 failed" in result.stdout


def test_cli_invalid_file():
    """Test handling of non-existent file"""
    result = subprocess.run(
        [sys.executable, "validate_omen.py", "packet", "nonexistent.json"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 1
    assert "not found" in result.stdout.lower()


def test_cli_no_invariants():
    """Test disabling invariant validation"""
    result = subprocess.run(
        [sys.executable, "validate_omen.py", "episode",
         "goldens/v0.7/Episode.verify_loop.jsonl", "--no-invariants"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert "PASS" in result.stdout


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
