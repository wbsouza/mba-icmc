"""Steps for strategy_validation.feature — per-strategy run-input validation."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest
import yaml
from algo_backtest.run import resolve_strategy, validate_run_inputs
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/strategy_validation.feature")

_START, _END = date(2014, 5, 7), date(2014, 5, 9)


@pytest.fixture
def vctx() -> dict[str, Any]:
    """Holds the strategy + parsed params + the validation outcome/error."""
    return {}


@given(parsers.parse('strategy "{strategy}" with params {params}'))
def _given(vctx: dict[str, Any], strategy: str, params: str) -> None:
    vctx["strategy"] = strategy
    vctx["params"] = dict(token.split("=", 1) for token in params.split())


@given(parsers.parse('strategy "{strategy}" with no params'))
def _given_no_params(vctx: dict[str, Any], strategy: str) -> None:
    vctx["strategy"] = strategy
    vctx["params"] = {}


@when("I validate the run inputs")
def _validate(vctx: dict[str, Any]) -> None:
    validate_run_inputs(vctx["strategy"], vctx["params"], _START, _END)
    vctx["ok"] = True


@when("I validate the run inputs expecting failure")
def _validate_failing(vctx: dict[str, Any]) -> None:
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        validate_run_inputs(vctx["strategy"], vctx["params"], _START, _END)
    vctx["error"] = str(exc_info.value)


@when(parsers.parse('I validate the run inputs with outcome "{outcome}"'))
def _validate_outline(vctx: dict[str, Any], outcome: str) -> None:
    """An outline cell: `passes` = expect success, `expecting failure` = capture the error."""
    if outcome == "expecting failure":
        _validate_failing(vctx)
    else:
        assert outcome == "passes", outcome
        _validate(vctx)


@then(parsers.parse('the resolved strategy "{name}" loads no F7 model'))
def _no_model_file(name: str) -> None:
    assert resolve_strategy(name).model_file is None


@then(parsers.parse('the resolved strategy "{name}" loads the F7 model "{file}"'))
def _model_file(name: str, file: str) -> None:
    assert resolve_strategy(name).model_file == file


@then("validation passes")
def _passes(vctx: dict[str, Any]) -> None:
    assert vctx.get("ok") is True


@then("validation fails naming the unknown strategy")
def _unknown(vctx: dict[str, Any]) -> None:
    assert "unknown strategy" in vctx["error"] and "bogus" in vctx["error"]


@then("validation fails saying the params must be exactly the strategy's set")
def _wrong_keys(vctx: dict[str, Any]) -> None:
    assert "must be exactly" in vctx["error"]


@then("validation fails saying the band must be positive")
def _band(vctx: dict[str, Any]) -> None:
    assert "band" in vctx["error"] and "positive" in vctx["error"]


@then("validation fails saying the window must be at least 2")
def _window(vctx: dict[str, Any]) -> None:
    assert "window" in vctx["error"] and "at least 2" in vctx["error"]


@then(parsers.parse('validation fails naming "{word}"'))
def _fails_naming(vctx: dict[str, Any], word: str) -> None:
    assert word in vctx["error"]


@when(parsers.parse("I validate the run inputs for the window {first} to {last}"))
def _validate_window(vctx: dict[str, Any], first: str, last: str) -> None:
    from datetime import date

    validate_run_inputs(
        vctx["strategy"], vctx["params"], date.fromisoformat(first), date.fromisoformat(last)
    )
    vctx["ok"] = True


@when(
    parsers.parse("I validate the run inputs for the window {first} to {last} expecting failure")
)
def _validate_window_failing(vctx: dict[str, Any], first: str, last: str) -> None:
    from datetime import date

    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        validate_run_inputs(
            vctx["strategy"], vctx["params"], date.fromisoformat(first), date.fromisoformat(last)
        )
    vctx["error"] = str(exc_info.value)


@given(parsers.parse("materialized lean-data day-zips for EURUSD on {days}"))
def _day_zips(vctx: dict[str, Any], tmp_path: Any, days: str) -> None:
    from algo_core.instrument import build_instrument
    from algo_core.layout import lean_data_dir_for

    instrument = build_instrument("EURUSD")
    directory = lean_data_dir_for(tmp_path, instrument, "minute")
    directory.mkdir(parents=True)
    for day in days.split(","):
        (directory / f"{day.strip()}_quote.zip").write_bytes(b"")
    vctx["data_root"], vctx["instrument"] = tmp_path, instrument


@then(parsers.parse("lean-data covers {first} to {last} is {covered}"))
def _covers(vctx: dict[str, Any], first: str, last: str, covered: str) -> None:
    from datetime import date

    from algo_backtest.run import lean_data_covers

    result = lean_data_covers(
        vctx["data_root"], vctx["instrument"], date.fromisoformat(first), date.fromisoformat(last)
    )
    assert result is (covered == "true")


@given(
    parsers.parse("a baseline-family model file whose provenance price_features is {provenance}")
)
def _model_with_provenance(vctx: dict[str, Any], tmp_path: Path, provenance: str) -> None:
    """A minimal F7 model document: families + provenance are all validation reads.

    `absent` leaves `price_features` out of the recorded strategy config; `scalar` records a
    non-mapping strategy config (a pre-schema model), which must count as the defaults.
    """
    strategy_config: dict[str, Any] | str = {}
    if provenance == "scalar":
        strategy_config = "legacy"
    elif provenance != "absent":
        strategy_config = {"price_features": yaml.safe_load(provenance)}
    _write_model(vctx, tmp_path, strategy_config=strategy_config)


def _write_model(
    vctx: dict[str, Any],
    tmp_path: Path,
    *,
    strategy_config: dict[str, Any] | str | None = None,
    families: list[str] | None = None,
    horizon: int = 15,
) -> None:
    """Write a minimal F7 model document and point the scenario's run at it."""
    document = {
        "format": "algo-backtest/f7-meta-learner", "format_version": 1,
        "families": families if families is not None else ["trend", "indicator", "pattern"],
        "family_models": {}, "combiner": {},
        "provenance": {
            "strategy_config": strategy_config if strategy_config is not None else {},
            "horizon_minutes": horizon,
        },
    }
    vctx["model"] = tmp_path / "model.json"
    vctx["model"].write_text(json.dumps(document))
    vctx["strategy"] = "baseline"
    vctx["params"] = {"cash": "10000"}


@given(
    parsers.parse(
        "a baseline-family model file whose provenance strategy_config is {strategy_config} "
        "and horizon_minutes is {horizon:d}"
    )
)
def _model_with_horizon(
    vctx: dict[str, Any], tmp_path: Path, strategy_config: str, horizon: int
) -> None:
    """A model whose provenance carries any YAML `strategy_config` (a mapping, null or a
    scalar for a legacy document) and the given label horizon."""
    _write_model(vctx, tmp_path, strategy_config=yaml.safe_load(strategy_config), horizon=horizon)


@given(
    parsers.parse("a baseline-family model file trained with a {horizon:d}-minute label horizon")
)
def _model_with_horizon(vctx: dict[str, Any], tmp_path: Path, horizon: int) -> None:
    """A model whose provenance records the given label horizon, default periods otherwise."""
    _write_model(vctx, tmp_path, horizon=horizon)


@given(parsers.parse('a baseline-family model file whose families are "{families}"'))
def _model_with_families(vctx: dict[str, Any], tmp_path: Path, families: str) -> None:
    """A model fitted on a different family set than the strategy declares."""
    _write_model(vctx, tmp_path, families=[f.strip() for f in families.split(",")])


@given("a baseline-family model path that does not exist")
def _missing_model(vctx: dict[str, Any], tmp_path: Path) -> None:
    """A `--model` override pointing at nothing."""
    vctx["model"] = tmp_path / "missing-model.json"
    vctx["strategy"] = "baseline"
    vctx["params"] = {"cash": "10000"}


@when(parsers.parse('I validate the run inputs for strategy "{strategy}" with that model passes'))
def _validate_with_model(vctx: dict[str, Any], strategy: str) -> None:
    validate_run_inputs(strategy, vctx["params"], _START, _END, vctx["model"])
    vctx["ok"] = True


@when(
    parsers.parse(
        'I validate the run inputs for strategy "{strategy}" with that model expecting failure'
    )
)
def _validate_with_model_failing(vctx: dict[str, Any], strategy: str) -> None:
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        validate_run_inputs(strategy, vctx["params"], _START, _END, vctx["model"])
    vctx["error"] = str(exc_info.value)


@given(
    parsers.parse(
        'an external strategies directory holding "{name}" extending "{base}" with extra '
        '"{extra_yaml}"'
    )
)
def _external_dir(
    vctx: dict[str, Any], tmp_path: Path, name: str, base: str, extra_yaml: str
) -> None:
    """A variant YAML in a directory outside the package; its base stays bundled."""
    root = tmp_path / "strategies"
    (root / name).mkdir(parents=True)
    body: dict[str, Any] = {"extends": base, **(yaml.safe_load(extra_yaml) or {})}
    (root / name / "config.yaml").write_text(yaml.safe_dump(body))
    vctx["strategies_root"] = root


@when(parsers.parse('strategy "{name}" is resolved from that directory'))
def _resolve_external(vctx: dict[str, Any], name: str) -> None:
    vctx["spec"] = resolve_strategy(name, strategies_root=vctx["strategies_root"])


@when(parsers.parse('strategy "{name}" is resolved from the bundled directory'))
def _resolve_bundled(vctx: dict[str, Any], name: str) -> None:
    vctx["spec"] = resolve_strategy(name)


@when(parsers.parse('resolving strategy "{name}" from that directory fails'))
def _resolve_fails(vctx: dict[str, Any], name: str) -> None:
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        resolve_strategy(name, strategies_root=vctx["strategies_root"])
    vctx["error"] = str(exc_info.value)


@then(parsers.parse('the resolved strategy runs on algorithm "{algo_dir}" with news data {news}'))
def _resolved_spec(vctx: dict[str, Any], algo_dir: str, news: str) -> None:
    spec = vctx["spec"]
    assert spec.algo_dir == algo_dir
    assert spec.needs_news_data is (news == "true")


@then(
    parsers.parse(
        'validating strategy "{name}" with params {params} from that directory passes'
    )
)
def _validate_external(vctx: dict[str, Any], name: str, params: str) -> None:
    parsed = dict(token.split("=", 1) for token in params.split())
    validate_run_inputs(name, parsed, _START, _END, strategies_root=vctx["strategies_root"])


@then(parsers.parse('the resolution failure names "{fragment}"'))
def _resolution_failure(vctx: dict[str, Any], fragment: str) -> None:
    assert fragment in vctx["error"], vctx["error"]


@then("the resolution failure names the external strategies directory")
def _resolution_failure_names_root(vctx: dict[str, Any]) -> None:
    """The remediation lists every directory that was searched, the external one included."""
    assert str(vctx["strategies_root"]) in vctx["error"], vctx["error"]
