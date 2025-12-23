"""
Verify project setup is correct.
"""

from pathlib import Path
import omen


def test_version_exists():
    """Package has version."""
    assert hasattr(omen, "__version__")
    assert omen.__version__ == "0.1.0"


def test_spec_docs_exist(spec_dir: Path):
    """Specification documents are in place."""
    assert (spec_dir / "ACE_Framework.md").exists()
    assert (spec_dir / "OMEN.md").exists()
