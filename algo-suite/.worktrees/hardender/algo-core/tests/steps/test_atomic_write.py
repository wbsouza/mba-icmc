"""Steps for atomic_write.feature — atomic text writes."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest
from algo_core.atomicio import write_text_atomic
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/atomic_write.feature")


@pytest.fixture
def actx(tmp_path: Path) -> dict[str, Any]:
    """Holds the tmp directory + the target path under test."""
    return {"dir": tmp_path}


@given("a target path in a not-yet-existing directory")
def _nested_target(actx: dict[str, Any]) -> None:
    actx["path"] = actx["dir"] / "nested" / "deep" / "out.txt"


@given(parsers.parse('an existing file containing "{content}"'))
def _existing(actx: dict[str, Any], content: str) -> None:
    path = actx["dir"] / "out.txt"
    path.write_text(content)
    actx["path"] = path


@given("the replace step will fail")
def _replace_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*_: object, **__: object) -> None:
        raise OSError("replace failed")

    monkeypatch.setattr(os, "replace", boom)


@when(parsers.parse('I atomically write "{text}"'))
def _write(actx: dict[str, Any], text: str) -> None:
    write_text_atomic(actx["path"], text)


@when(parsers.parse('I atomically write "{text}" expecting failure'))
def _write_failing(actx: dict[str, Any], text: str) -> None:
    with pytest.raises(OSError):  # noqa: PT011 - behaviour asserted in Then
        write_text_atomic(actx["path"], text)


@then(parsers.parse('the file exists with content "{content}"'))
def _exists(actx: dict[str, Any], content: str) -> None:
    assert actx["path"].read_text() == content


@then(parsers.parse('the file still contains "{content}"'))
def _still(actx: dict[str, Any], content: str) -> None:
    assert actx["path"].read_text() == content


@then("no temporary files remain in the directory")
def _no_temp(actx: dict[str, Any]) -> None:
    leftovers = [p.name for p in actx["path"].parent.iterdir() if p.name != "out.txt"]
    assert leftovers == [], leftovers
