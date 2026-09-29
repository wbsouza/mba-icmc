"""Step definitions for config.feature (pytest-bdd)."""

from __future__ import annotations

from typing import Any

import pytest
from algo_core.config import ConfigError, Impact, LoadResult, ParameterSpec, load
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/config.feature")

# A small representative schema for the loader policy under test.
SCHEMA = (
    ParameterSpec(name="risk_math.risk_per_trade", impact=Impact.TRADING, reference_value=0.03),
    ParameterSpec(name="operational.log_level", impact=Impact.OPERATIONAL, default="INFO"),
    ParameterSpec(name="risk_guard.max_leverage", impact=Impact.TRADING, nullable=True),
)
CURRENT_VERSION = 2


@pytest.fixture
def raw() -> dict[str, Any]:
    return {}


@pytest.fixture
def outcome() -> dict[str, object]:
    return {}


def _set(node: dict[str, Any], dotted: str, value: object) -> None:
    parts = dotted.split(".")
    for part in parts[:-1]:
        node = node.setdefault(part, {})
    node[parts[-1]] = value


def _delete(node: dict[str, Any], dotted: str) -> None:
    parts = dotted.split(".")
    for part in parts[:-1]:
        node = node[part]
    node.pop(parts[-1], None)


def _result(outcome: dict[str, object]) -> LoadResult:
    result = outcome["result"]
    assert isinstance(result, LoadResult)
    return result


def _error(outcome: dict[str, object]) -> ConfigError:
    error = outcome.get("error")
    assert isinstance(error, ConfigError)
    return error


@given("a baseline strategy config")
def _baseline(raw: dict[str, Any]) -> None:
    raw.update(
        {
            "schema_version": CURRENT_VERSION,
            "risk_math": {"risk_per_trade": 0.02},
            "operational": {"log_level": "DEBUG"},
            "risk_guard": {"max_leverage": 20},
        }
    )


@given(parsers.parse('the config omits "{dotted}"'))
def _omit(raw: dict[str, Any], dotted: str) -> None:
    _delete(raw, dotted)


@given(parsers.parse('the config sets "{dotted}" to null'))
def _null(raw: dict[str, Any], dotted: str) -> None:
    _set(raw, dotted, None)


@given(parsers.parse("the config sets schema_version to {version:d}"))
def _version(raw: dict[str, Any], version: int) -> None:
    raw["schema_version"] = version


@given(parsers.parse('the config has an unknown key "{dotted}"'))
def _unknown_key(raw: dict[str, Any], dotted: str) -> None:
    _set(raw, dotted, "x")


@when("the loader validates it")
def _validate(raw: dict[str, Any], outcome: dict[str, object]) -> None:
    try:
        outcome["result"] = load(raw, SCHEMA, current_version=CURRENT_VERSION)
    except ConfigError as error:
        outcome["error"] = error


@then("it fails to load")
def _failed(outcome: dict[str, object]) -> None:
    assert isinstance(outcome.get("error"), ConfigError)


@then(parsers.parse("it fails to load with exit code {code:d}"))
def _failed_code(outcome: dict[str, object], code: int) -> None:
    assert _error(outcome).exit_code == code


@then("it loads successfully")
def _ok(outcome: dict[str, object]) -> None:
    assert "error" not in outcome
    assert isinstance(outcome.get("result"), LoadResult)


@then(
    parsers.parse(
        'the error names "{name}", section "{section}" and reference value {reference:g}'
    )
)
def _names(outcome: dict[str, object], name: str, section: str, reference: float) -> None:
    message = str(_error(outcome))
    assert name in message
    assert section in message
    assert str(reference) in message


@then("the error hints to run the config_generator")
def _hint_generator(outcome: dict[str, object]) -> None:
    assert "config_generator" in str(_error(outcome))


@then(parsers.parse('the error hints to run "{text}"'))
def _hint(outcome: dict[str, object], text: str) -> None:
    assert text in str(_error(outcome))


@then(parsers.parse('the provenance log contains "{line}"'))
def _provenance(outcome: dict[str, object], line: str) -> None:
    assert any(line in entry for entry in _result(outcome).provenance)
