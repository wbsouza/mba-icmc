"""Shared fixtures for repo-root generic tooling's BDD suites (e.g.
tools/mutation_harness.py). `pythonpath = ["tools"]` in the workspace
root pyproject.toml makes those standalone tools importable by name here."""

from __future__ import annotations

import mutation_harness as mh
import pytest


@pytest.fixture
def harness():
    """The module under test, importable by its short name in step files."""
    return mh


@pytest.fixture
def fake_repo(tmp_path, monkeypatch, harness):
    """An isolated fake workspace root; REPO_ROOT is redirected here so no
    scenario ever touches the real repository tree. Lives under pytest's own
    tmp_path (system tmp, cleaned up by pytest's retention policy) — nothing
    persists past the test run."""
    monkeypatch.setattr(harness, "REPO_ROOT", tmp_path)
    return tmp_path


@pytest.fixture
def context():
    """Free-form scratch dict steps use to pass state between Given/When/Then."""
    return {}
