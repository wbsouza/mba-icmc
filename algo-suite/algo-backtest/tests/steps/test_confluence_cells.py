"""Steps for confluence_cells.feature — the fourteen-cell manifest generator (story 21, T10).

`experiments/confluence-chain/make_cells.py` is a standalone script outside the
`algo_backtest` package, loaded here by file path (same pattern as T8/T9's steps).
"""

from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType

import pytest
import yaml
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/confluence_cells.feature")

_SCRIPT_PATH = (
    Path(__file__).resolve().parents[3] / "experiments" / "confluence-chain" / "make_cells.py"
)


def _load_script(path: Path) -> ModuleType:
    """Load a standalone script file as an importable module, by file path."""
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None and spec.loader is not None, f"cannot load {path}"
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


mc = _load_script(_SCRIPT_PATH)


@dataclass
class _CellsCtx:
    """Per-scenario context: the job directory, the generated cells, or an error."""

    job_dir: Path | None = None
    cells: list[object] = field(default_factory=list)
    second_cells: list[object] = field(default_factory=list)
    second_job_dir: Path | None = None
    error: Exception | None = None


@pytest.fixture
def cells_ctx(tmp_path: Path) -> _CellsCtx:
    """A fresh per-scenario context with its own job directory."""
    return _CellsCtx(job_dir=tmp_path / "job")


def _cells_by_arm(cells_ctx: _CellsCtx, arm: str) -> list[object]:
    matches = [cell for cell in cells_ctx.cells if cell.arm == arm]  # type: ignore[attr-defined]
    assert matches, f"no cell for arm {arm!r}"
    return matches


# --- Background ---


@given("a caller-selected job directory")
def _job_dir(cells_ctx: _CellsCtx) -> None:
    assert cells_ctx.job_dir is not None


# --- Generation ---


@when("the fourteen-cell manifest is generated")
def _generate(cells_ctx: _CellsCtx) -> None:
    assert cells_ctx.job_dir is not None
    cells_ctx.cells = mc.generate_manifest(cells_ctx.job_dir)


@when("the fourteen-cell manifest is generated again into a second job directory")
def _generate_again(cells_ctx: _CellsCtx) -> None:
    assert cells_ctx.job_dir is not None
    cells_ctx.second_job_dir = cells_ctx.job_dir.parent / "job2"
    cells_ctx.second_cells = mc.generate_manifest(cells_ctx.second_job_dir)


@when(
    parsers.parse('the fourteen-cell manifest is generated with an extra arm "{arm}" and it fails')
)
def _generate_extra_arm(cells_ctx: _CellsCtx, arm: str) -> None:
    assert cells_ctx.job_dir is not None
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        mc.generate_manifest(cells_ctx.job_dir, arms=(*mc.ARMS, arm))
    cells_ctx.error = exc_info.value


@when(
    parsers.parse(
        "the fourteen-cell manifest is generated with an extra clock {clock:d} and it fails"
    )
)
def _generate_extra_clock(cells_ctx: _CellsCtx, clock: int) -> None:
    assert cells_ctx.job_dir is not None
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        mc.generate_manifest(cells_ctx.job_dir, clock_minutes=(*mc.CLOCK_LOOKBACK, clock))
    cells_ctx.error = exc_info.value


# --- Assertions: manifest shape ---


@then(parsers.parse("the manifest lists exactly {n:d} cells"))
def _lists_exactly(cells_ctx: _CellsCtx, n: int) -> None:
    assert len(cells_ctx.cells) == n


@then("every cell ID in the manifest is unique")
def _ids_unique(cells_ctx: _CellsCtx) -> None:
    ids = [cell.cell_id for cell in cells_ctx.cells]  # type: ignore[attr-defined]
    assert len(ids) == len(set(ids)), ids


@then(parsers.parse('the "{arm}" cell on clock {clock:d} minutes has cell ID "{cell_id}"'))
def _cell_id_exact(cells_ctx: _CellsCtx, arm: str, clock: int, cell_id: str) -> None:
    (cell,) = [c for c in cells_ctx.cells if c.arm == arm and c.clock_minutes == clock]  # type: ignore[attr-defined]
    assert cell.cell_id == cell_id  # type: ignore[attr-defined]


@then(parsers.parse('the manifest\'s arms are exactly "{arms}"'))
def _arms_exactly(cells_ctx: _CellsCtx, arms: str) -> None:
    expected = [token.strip() for token in arms.split(",")]
    actual = sorted({cell.arm for cell in cells_ctx.cells})  # type: ignore[attr-defined]
    assert actual == sorted(expected), actual


@then("each arm appears exactly once on clock 60 minutes and once on clock 240 minutes")
def _each_arm_once_per_clock(cells_ctx: _CellsCtx) -> None:
    for arm in mc.ARMS:
        clocks = sorted(cell.clock_minutes for cell in _cells_by_arm(cells_ctx, arm))  # type: ignore[attr-defined]
        assert clocks == [60, 240], (arm, clocks)


@then(parsers.parse('every "{clock_label}" cell has clock_minutes {clock_minutes:d}'))
def _clock_minutes(cells_ctx: _CellsCtx, clock_label: str, clock_minutes: int) -> None:
    expected = {"H1": 60, "H4": 240}[clock_label]
    assert expected == clock_minutes
    matches = [cell for cell in cells_ctx.cells if cell.clock_minutes == clock_minutes]  # type: ignore[attr-defined]
    assert len(matches) == 7, matches


@then(parsers.parse('every "{clock_label}" cell has momentum lookback_bars {lookback:d}'))
def _lookback(cells_ctx: _CellsCtx, clock_label: str, lookback: int) -> None:
    clock_minutes = {"H1": 60, "H4": 240}[clock_label]
    matches = [cell for cell in cells_ctx.cells if cell.clock_minutes == clock_minutes]  # type: ignore[attr-defined]
    assert matches
    for cell in matches:
        assert cell.config["momentum_context"]["lookback_bars"] == lookback  # type: ignore[attr-defined]


# --- Assertions: per-arm required voters ---


@then(parsers.parse('every "{arm}" cell requires exactly the voters "{required_voters}"'))
def _required_voters(cells_ctx: _CellsCtx, arm: str, required_voters: str) -> None:
    expected = [token.strip() for token in required_voters.split(",")]
    for cell in _cells_by_arm(cells_ctx, arm):
        assert cell.required_voters() == expected  # type: ignore[attr-defined]


# --- Assertions: news_context ---


@then(parsers.parse('no "{arm}" cell\'s config declares a "news_context" section'))
def _no_news_section(cells_ctx: _CellsCtx, arm: str) -> None:
    for cell in _cells_by_arm(cells_ctx, arm):
        assert "news_context" not in cell.config  # type: ignore[attr-defined]


@then(
    parsers.parse(
        'every "{arm}" cell\'s config declares a "news_context" section with '
        'direction_source "{direction_source}" and intensity_sign {sign:d}'
    )
)
def _news_section(cells_ctx: _CellsCtx, arm: str, direction_source: str, sign: int) -> None:
    for cell in _cells_by_arm(cells_ctx, arm):
        news = cell.config["news_context"]  # type: ignore[attr-defined]
        assert news["direction_source"] == direction_source
        assert news["intensity_sign"] == sign


# --- Assertions: capital_mgmt / execution fields ---


def _capital_mgmt_value(cells_ctx: _CellsCtx, arm: str, key: str, raw: str) -> None:
    expected = yaml.safe_load(raw)
    for cell in _cells_by_arm(cells_ctx, arm):
        actual = cell.config["capital_mgmt"][key]  # type: ignore[attr-defined]
        assert actual == expected, (arm, key, actual, expected)


@then(parsers.parse('every "{arm}" cell\'s config has capital_mgmt targets []'))
def _targets_empty(cells_ctx: _CellsCtx, arm: str) -> None:
    _capital_mgmt_value(cells_ctx, arm, "targets", "[]")


@then(parsers.parse('every "{arm}" cell\'s config has capital_mgmt trail_stops []'))
def _trail_stops_empty(cells_ctx: _CellsCtx, arm: str) -> None:
    _capital_mgmt_value(cells_ctx, arm, "trail_stops", "[]")


@then(parsers.parse('every "{arm}" cell\'s config has capital_mgmt exit_after_bars {value:d}'))
def _exit_after_bars(cells_ctx: _CellsCtx, arm: str, value: int) -> None:
    _capital_mgmt_value(cells_ctx, arm, "exit_after_bars", str(value))


@then(parsers.parse('every "{arm}" cell\'s config has execution min_hold_bars {value:d}'))
def _min_hold_bars(cells_ctx: _CellsCtx, arm: str, value: int) -> None:
    for cell in _cells_by_arm(cells_ctx, arm):
        assert cell.config["execution"]["min_hold_bars"] == value  # type: ignore[attr-defined]


@then(parsers.parse('every "{arm}" cell\'s config has capital_mgmt risk_per_trade {value:g}'))
def _risk_per_trade(cells_ctx: _CellsCtx, arm: str, value: float) -> None:
    _capital_mgmt_value(cells_ctx, arm, "risk_per_trade", repr(value))


@then(parsers.parse('every "{arm}" cell\'s config has capital_mgmt stop_distance_source "{value}"'))
def _stop_distance_source(cells_ctx: _CellsCtx, arm: str, value: str) -> None:
    _capital_mgmt_value(cells_ctx, arm, "stop_distance_source", f'"{value}"')


@then(parsers.parse('every "{arm}" cell\'s config has capital_mgmt atr_multiplier {value:g}'))
def _atr_multiplier(cells_ctx: _CellsCtx, arm: str, value: float) -> None:
    _capital_mgmt_value(cells_ctx, arm, "atr_multiplier", repr(value))


@then(parsers.parse('every "{arm}" cell\'s config has capital_mgmt stop_loss_shrink {value:g}'))
def _stop_loss_shrink(cells_ctx: _CellsCtx, arm: str, value: float) -> None:
    _capital_mgmt_value(cells_ctx, arm, "stop_loss_shrink", repr(value))


@then(parsers.parse('every "{arm}" cell\'s config has capital_mgmt min_stop_pips {value:g}'))
def _min_stop_pips(cells_ctx: _CellsCtx, arm: str, value: float) -> None:
    _capital_mgmt_value(cells_ctx, arm, "min_stop_pips", repr(value))


@then(parsers.parse('every "{arm}" cell\'s config has capital_mgmt min_stop_factor {value:g}'))
def _min_stop_factor(cells_ctx: _CellsCtx, arm: str, value: float) -> None:
    _capital_mgmt_value(cells_ctx, arm, "min_stop_factor", repr(value))


@then(parsers.parse('every "{arm}" cell\'s config has capital_mgmt min_reward_risk {value:g}'))
def _min_reward_risk(cells_ctx: _CellsCtx, arm: str, value: float) -> None:
    _capital_mgmt_value(cells_ctx, arm, "min_reward_risk", repr(value))


@then(
    parsers.re(
        r'every "(?P<arm>[^"]+)" cell\'s config has capital_mgmt targets '
        r"(?P<raw>\[.*\])$"
    )
)
def _targets_list(cells_ctx: _CellsCtx, arm: str, raw: str) -> None:
    _capital_mgmt_value(cells_ctx, arm, "targets", raw)


@then(
    parsers.re(
        r'every "(?P<arm>[^"]+)" cell\'s config has capital_mgmt trail_stops '
        r"(?P<raw>\[.*\])$"
    )
)
def _trail_stops_list(cells_ctx: _CellsCtx, arm: str, raw: str) -> None:
    _capital_mgmt_value(cells_ctx, arm, "trail_stops", raw)


@then(parsers.parse('no "{arm}" cell\'s config declares capital_mgmt exit_after_bars'))
def _no_exit_after_bars(cells_ctx: _CellsCtx, arm: str) -> None:
    for cell in _cells_by_arm(cells_ctx, arm):
        assert "exit_after_bars" not in cell.config["capital_mgmt"]  # type: ignore[attr-defined]


# --- Assertions: A-plan vs A ---


@then('the "A" and "A-plan" cells on clock 60 minutes require the same voters')
def _a_aplan_same_voters(cells_ctx: _CellsCtx) -> None:
    (a,) = [c for c in cells_ctx.cells if c.arm == "A" and c.clock_minutes == 60]  # type: ignore[attr-defined]
    (a_plan,) = [c for c in cells_ctx.cells if c.arm == "A-plan" and c.clock_minutes == 60]  # type: ignore[attr-defined]
    assert a.required_voters() == a_plan.required_voters()


@then('the "A" and "A-plan" cells on clock 60 minutes have different capital_mgmt sections')
def _a_aplan_different_capital_mgmt(cells_ctx: _CellsCtx) -> None:
    (a,) = [c for c in cells_ctx.cells if c.arm == "A" and c.clock_minutes == 60]  # type: ignore[attr-defined]
    (a_plan,) = [c for c in cells_ctx.cells if c.arm == "A-plan" and c.clock_minutes == 60]  # type: ignore[attr-defined]
    assert a.config["capital_mgmt"] != a_plan.config["capital_mgmt"]  # type: ignore[attr-defined]


# --- Assertions: invariants across all cells ---


@then(parsers.parse('every cell\'s config has pair "{pair}"'))
def _pair(cells_ctx: _CellsCtx, pair: str) -> None:
    for cell in cells_ctx.cells:
        assert cell.config["pair"] == pair  # type: ignore[attr-defined]


@then(parsers.parse("every cell's config has account_balance {value:d}"))
def _account_balance(cells_ctx: _CellsCtx, value: int) -> None:
    for cell in cells_ctx.cells:
        assert cell.config["account_balance"] == value  # type: ignore[attr-defined]


@then("every cell's config has execution spread/commission matching the pinned OANDA costs")
def _oanda_costs(cells_ctx: _CellsCtx) -> None:
    for cell in cells_ctx.cells:
        execution = cell.config["execution"]  # type: ignore[attr-defined]
        assert execution["spread_pips"] == 1.0
        assert execution["commission_per_lot"] == 0.0
        assert execution["broker_stop_level_pips"] == 0.0


def _risk_guard_value(cells_ctx: _CellsCtx, key: str, value: object) -> None:
    for cell in cells_ctx.cells:
        assert cell.config["risk_guard"][key] == value  # type: ignore[attr-defined]


@then(parsers.parse("every cell's config has risk_guard portfolio_at_risk_cap {value:g}"))
def _portfolio_at_risk_cap(cells_ctx: _CellsCtx, value: float) -> None:
    _risk_guard_value(cells_ctx, "portfolio_at_risk_cap", value)


@then(parsers.parse("every cell's config has risk_guard daily_drawdown_limit {value:g}"))
def _daily_drawdown_limit(cells_ctx: _CellsCtx, value: float) -> None:
    _risk_guard_value(cells_ctx, "daily_drawdown_limit", value)


@then(parsers.parse("every cell's config has risk_guard weekly_drawdown_limit {value:g}"))
def _weekly_drawdown_limit(cells_ctx: _CellsCtx, value: float) -> None:
    _risk_guard_value(cells_ctx, "weekly_drawdown_limit", value)


@then(
    parsers.parse("every cell's config has risk_guard max_concurrent_trades_per_account {value:d}")
)
def _max_concurrent(cells_ctx: _CellsCtx, value: int) -> None:
    _risk_guard_value(cells_ctx, "max_concurrent_trades_per_account", value)


@then(parsers.parse("every cell's config has risk_guard max_leverage {value:d}"))
def _max_leverage(cells_ctx: _CellsCtx, value: int) -> None:
    _risk_guard_value(cells_ctx, "max_leverage", value)


@then(parsers.parse('every cell\'s study window is "{start}".."{end}"'))
def _study_window(cells_ctx: _CellsCtx, start: str, end: str) -> None:
    for cell in cells_ctx.cells:
        assert cell.config["window"] == {"start": start, "end": end}  # type: ignore[attr-defined]


# --- Assertions: disallowed content / registry refusal ---


@then(parsers.parse('no cell\'s config declares filter "{disallowed_filter}"'))
def _no_disallowed_filter(cells_ctx: _CellsCtx, disallowed_filter: str) -> None:
    for cell in cells_ctx.cells:
        assert disallowed_filter not in cell.config["filters"]  # type: ignore[attr-defined]


@then(parsers.parse('the cell-manifest failure names "{fragment}"'))
def _failure_names(cells_ctx: _CellsCtx, fragment: str) -> None:
    assert cells_ctx.error is not None, "expected a failure but none was raised"
    assert fragment in str(cells_ctx.error), str(cells_ctx.error)


# --- Assertions: hashes and determinism ---


@then("every manifest row has a non-empty config_hash")
def _non_empty_hash(cells_ctx: _CellsCtx) -> None:
    for cell in cells_ctx.cells:
        assert cell.config_hash  # type: ignore[attr-defined]


@then("no two manifest rows share the same config_hash")
def _hashes_unique(cells_ctx: _CellsCtx) -> None:
    hashes = [cell.config_hash for cell in cells_ctx.cells]  # type: ignore[attr-defined]
    assert len(hashes) == len(set(hashes)), hashes


@then("every manifest row's config_hash is a 64-character hex SHA-256 digest")
def _hash_is_sha256(cells_ctx: _CellsCtx) -> None:
    for cell in cells_ctx.cells:
        digest = cell.config_hash  # type: ignore[attr-defined]
        assert len(digest) == 64, digest
        int(digest, 16)  # raises ValueError if not valid hexadecimal


@then("the two manifests list the same 14 cell IDs in the same order")
def _same_ids_same_order(cells_ctx: _CellsCtx) -> None:
    first_ids = [cell.cell_id for cell in cells_ctx.cells]  # type: ignore[attr-defined]
    second_ids = [cell.cell_id for cell in cells_ctx.second_cells]  # type: ignore[attr-defined]
    assert first_ids == second_ids


@then("every cell's config_hash is identical between the two manifests")
def _identical_hashes(cells_ctx: _CellsCtx) -> None:
    first = {cell.cell_id: cell.config_hash for cell in cells_ctx.cells}  # type: ignore[attr-defined]
    second = {cell.cell_id: cell.config_hash for cell in cells_ctx.second_cells}  # type: ignore[attr-defined]
    assert first == second


@then("the job directory has exactly 14 config.yaml files, one per cell")
def _fourteen_config_files(cells_ctx: _CellsCtx) -> None:
    assert cells_ctx.job_dir is not None
    found = list(cells_ctx.job_dir.glob("*/config.yaml"))
    assert len(found) == 14, found


@then("the job directory has one manifest file listing all 14 rows")
def _manifest_file(cells_ctx: _CellsCtx) -> None:
    assert cells_ctx.job_dir is not None
    manifest_path = cells_ctx.job_dir / "manifest.json"
    assert manifest_path.is_file()
    rows = json.loads(manifest_path.read_text())
    assert len(rows) == 14, rows
