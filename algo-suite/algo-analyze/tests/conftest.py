"""Test path setup for the restored algo-analyze package."""

from __future__ import annotations

import sys
from pathlib import Path


def pytest_configure() -> None:
    """Make the package's src layout importable when pytest runs from this tool dir."""
    src = Path(__file__).resolve().parents[1] / "src"
    sys.path.insert(0, str(src))
