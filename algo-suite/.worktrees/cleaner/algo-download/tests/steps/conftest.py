"""Shared fixtures for the pytest-bdd step modules."""

from __future__ import annotations

import pytest


@pytest.fixture
def context() -> dict[str, object]:
    """A per-scenario scratch dict to carry state across Given/When/Then steps."""
    return {}
