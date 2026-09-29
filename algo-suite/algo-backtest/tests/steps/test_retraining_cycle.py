"""Steps for retraining_cycle.feature: the full adaptive-cycle coordinator."""

from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from algo_backtest.chain.filters import f7_meta_learner as f7
from algo_backtest.chain.filters.f7_meta_learner import FeatureFamily
from algo_backtest.retraining import bundle as bundle_module
from algo_backtest.retraining.bundle import list_bundles, load
from algo_backtest.retraining.cycle import Coordinator, CycleRequest, CycleResponse
from algo_backtest.retraining.ingestion import Batch, Ledger, SourceRow
from algo_backtest.retraining.schedule import (
    Epoch,
    epoch_starting,
    monthly_epochs,
    select_rows,
    stage_spans,
)
from algo_backtest.retraining.trainer import TrainingSettings
from algo_backtest.retraining.weights import SupportMinima
from lightgbm import LGBMClassifier
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/retraining_cycle.feature")

_FAMILY_COLUMNS = (
    "trend_direction",
    "trend_strength",
    "higher_tf_trend_direction",
    "rsi",
    "macd_hist",
)


class _RaisingClassifier:
    """A stand-in for `LGBMClassifier` whose `fit` always raises."""

    def __init__(self, message: str) -> None:
        self._message = message

    def __call__(self, *args: object, **kwargs: object) -> _RaisingClassifier:
        return self

    def fit(self, *args: object, **kwargs: object) -> None:
        raise ValueError(self._message)


@dataclass(frozen=True)
class _ObservedFit:
    has_sample_weight: bool


class _RecordingClassifier(LGBMClassifier):  # type: ignore[misc]
    """An `LGBMClassifier` that records every `fit` call, then really fits."""

    observed: list[_ObservedFit] = []

    def fit(self, X: Any, y: Any, **kwargs: Any) -> Any:  # noqa: N803 - sklearn's name
        _RecordingClassifier.observed.append(
            _ObservedFit(has_sample_weight="sample_weight" in kwargs)
        )
        return super().fit(X, y, **kwargs)


class _FakeClock:
    """A mutable wall clock the tests advance explicitly."""

    def __init__(self, start: datetime) -> None:
        self._now = start

    def __call__(self) -> datetime:
        return self._now

    def advance(self, delta: timedelta) -> None:
        self._now += delta


@dataclass
class _CycleCtx:
    """Per-scenario state for the cycle coordinator feature."""

    base_dir: Path
    settings: TrainingSettings | None = None
    epochs: tuple[Epoch, ...] = ()
    batches: dict[str, Batch] = field(default_factory=dict)
    features: dict[str, dict[str, object]] = field(default_factory=dict)
    coordinator: Coordinator | None = None
    clock: _FakeClock = field(default_factory=lambda: _FakeClock(datetime(2026, 1, 1, tzinfo=UTC)))
    timeout_seconds: float = 1800.0
    requests: dict[str, CycleRequest] = field(default_factory=dict)
    responses: dict[str, CycleResponse] = field(default_factory=dict)
    response_history: list[CycleResponse] = field(default_factory=list)
    last_request_name: str | None = None
    error: Exception | None = None
    remembered_ledger_bytes: bytes | None = None
    remembered_registry_bytes: dict[str, bytes] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.coordinator_dir = self.base_dir / "coordinator"

    @property
    def ledger_dir(self) -> Path:
        return self.coordinator_dir / "ledger"

    @property
    def registry_dir(self) -> Path:
        return self.coordinator_dir / "registry"

    @property
    def cycles_dir(self) -> Path:
        return self.coordinator_dir / "cycles"


@pytest.fixture
def cy_ctx(tmp_path: Path) -> _CycleCtx:
    return _CycleCtx(base_dir=tmp_path)


def _iso(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def _cells(datatable: list[list[str]]) -> list[dict[str, str]]:
    header, *rows = datatable
    return [dict(zip(header, row, strict=True)) for row in rows]


def _field_value_table(datatable: list[list[str]]) -> dict[str, str]:
    header, *rows = datatable
    assert header == ["field", "value"]
    return {row[0]: row[1] for row in rows}


def _trainer_fixture_data() -> tuple[dict[str, Batch], dict[str, dict[str, object]]]:
    """The exact batches T9's trainer.feature Background uses."""
    definitions: dict[str, list[tuple[str, str, str, int, float, float, float, float, float]]] = {
        "history-2015": [
            (
                "fam-1",
                "2015-03-06T00:00:00Z",
                "2015-03-06T01:00:00Z",
                1,
                1.0,
                20.0,
                1.0,
                55.0,
                0.0001,
            ),
            (
                "fam-2",
                "2015-05-05T00:00:00Z",
                "2015-05-05T01:00:00Z",
                0,
                -1.0,
                30.0,
                0.0,
                45.0,
                -0.0001,
            ),
            (
                "fam-3",
                "2015-07-04T00:00:00Z",
                "2015-07-04T01:00:00Z",
                1,
                1.0,
                40.0,
                1.0,
                60.0,
                0.0002,
            ),
            (
                "fam-4",
                "2015-09-02T00:00:00Z",
                "2015-09-02T01:00:00Z",
                0,
                -1.0,
                50.0,
                -1.0,
                40.0,
                -0.0002,
            ),
            (
                "fam-5",
                "2015-11-01T00:00:00Z",
                "2015-11-01T01:00:00Z",
                1,
                1.0,
                60.0,
                1.0,
                65.0,
                0.0003,
            ),
        ],
        "jan-2016": [
            (
                "cmb-1",
                "2015-12-31T00:00:00Z",
                "2015-12-31T01:00:00Z",
                1,
                1.0,
                35.0,
                1.0,
                58.0,
                0.0001,
            ),
            (
                "cmb-2",
                "2016-01-10T00:00:00Z",
                "2016-01-10T01:00:00Z",
                0,
                -1.0,
                45.0,
                -1.0,
                42.0,
                -0.0001,
            ),
            (
                "cmb-3",
                "2016-01-20T00:00:00Z",
                "2016-01-20T01:00:00Z",
                1,
                1.0,
                55.0,
                1.0,
                62.0,
                0.0002,
            ),
            (
                "cmb-4",
                "2016-01-25T00:00:00Z",
                "2016-01-25T01:00:00Z",
                0,
                -1.0,
                65.0,
                0.0,
                38.0,
                -0.0002,
            ),
        ],
        "feb-2016": [
            (
                "thr-1",
                "2016-02-01T00:00:00Z",
                "2016-02-01T01:00:00Z",
                1,
                1.0,
                25.0,
                1.0,
                57.0,
                0.0001,
            ),
            (
                "thr-2",
                "2016-02-05T00:00:00Z",
                "2016-02-05T01:00:00Z",
                0,
                -1.0,
                35.0,
                -1.0,
                43.0,
                -0.0001,
            ),
            (
                "thr-3",
                "2016-02-10T00:00:00Z",
                "2016-02-10T01:00:00Z",
                1,
                1.0,
                45.0,
                0.0,
                61.0,
                0.0002,
            ),
            (
                "thr-4",
                "2016-02-15T00:00:00Z",
                "2016-02-15T01:00:00Z",
                0,
                -1.0,
                55.0,
                -1.0,
                39.0,
                -0.0002,
            ),
            (
                "thr-5",
                "2016-02-20T00:00:00Z",
                "2016-02-20T01:00:00Z",
                1,
                1.0,
                65.0,
                1.0,
                63.0,
                0.0003,
            ),
            (
                "thr-6",
                "2016-02-25T00:00:00Z",
                "2016-02-25T01:00:00Z",
                0,
                -1.0,
                75.0,
                0.0,
                37.0,
                -0.0003,
            ),
        ],
        "mar-2016": [
            (
                "mar-1",
                "2016-03-05T00:00:00Z",
                "2016-03-05T01:00:00Z",
                1,
                1.0,
                30.0,
                1.0,
                56.0,
                0.0001,
            ),
            (
                "mar-2",
                "2016-03-12T00:00:00Z",
                "2016-03-12T01:00:00Z",
                0,
                -1.0,
                40.0,
                -1.0,
                44.0,
                -0.0001,
            ),
            (
                "mar-3",
                "2016-03-19T00:00:00Z",
                "2016-03-19T01:00:00Z",
                1,
                1.0,
                50.0,
                1.0,
                59.0,
                0.0002,
            ),
            (
                "mar-4",
                "2016-03-26T00:00:00Z",
                "2016-03-26T01:00:00Z",
                0,
                -1.0,
                60.0,
                -1.0,
                41.0,
                -0.0002,
            ),
        ],
    }
    batches: dict[str, Batch] = {}
    features: dict[str, dict[str, object]] = {}
    for name, rows in definitions.items():
        source_rows = []
        for key, available, label_time, label, td, ts, htf, rsi, macd in rows:
            source_rows.append(
                SourceRow(
                    key=key, available_at=_iso(available), label_time=_iso(label_time), label=label
                )
            )
            features[key] = {
                "trend_direction": td,
                "trend_strength": ts,
                "higher_tf_trend_direction": htf,
                "rsi": rsi,
                "macd_hist": macd,
            }
        batches[name] = Batch(partition=name, rows=tuple(source_rows))
    return batches, features


def _get_coordinator(cy_ctx: _CycleCtx) -> Coordinator:
    if cy_ctx.coordinator is None:
        cy_ctx.coordinator = Coordinator(
            cy_ctx.coordinator_dir,
            cy_ctx.epochs,
            timeout_seconds=cy_ctx.timeout_seconds,
            clock=cy_ctx.clock,
        )
    return cy_ctx.coordinator


def _last_cycle_dir(cy_ctx: _CycleCtx) -> Path:
    from algo_backtest.retraining.cycle import _cycle_id

    request = cy_ctx.requests[cy_ctx.last_request_name]
    return cy_ctx.cycles_dir / _cycle_id(request)


def _cycle_dir_for(cy_ctx: _CycleCtx, name: str) -> Path:
    from algo_backtest.retraining.cycle import _cycle_id

    return cy_ctx.cycles_dir / _cycle_id(cy_ctx.requests[name])


def _read_record(cycle_dir: Path) -> dict[str, Any]:
    payload: dict[str, Any] = json.loads((cycle_dir / "record.json").read_text())
    return payload


def _last_record(cy_ctx: _CycleCtx) -> dict[str, Any]:
    return _read_record(_last_cycle_dir(cy_ctx))


def _parse_optional_iso(text: str) -> datetime | None:
    return None if text.strip().lower() == "none" else _iso(text.strip())


def _parse_optional_str(text: str) -> str | None:
    return None if text.strip().lower() == "none" else text.strip()


def _build_request(cy_ctx: _CycleCtx, values: dict[str, str]) -> CycleRequest:
    assert cy_ctx.settings is not None
    batch_names = [name.strip() for name in values["batches"].split(",")]
    batches = tuple(cy_ctx.batches[name] for name in batch_names)
    prior_raw = values["prior_bundle_id"]
    if prior_raw.startswith("the bundle_id of "):
        ref_name = prior_raw.split('"')[1]
        prior_bundle_id: str | None = cy_ctx.responses[ref_name].bundle_id
    else:
        prior_bundle_id = _parse_optional_str(prior_raw)
    return CycleRequest(
        policy=values["policy"],
        protocol_hash=values["protocol_hash"],
        cutoff=_iso(values["cutoff"]),
        activation_boundary=_iso(values["activation_boundary"]),
        source_watermark=_parse_optional_iso(values["source_watermark"]),
        prior_bundle_id=prior_bundle_id,
        batches=batches,
        settings=cy_ctx.settings,
        features=cy_ctx.features,
    )


# --- Given -----------------------------------------------------------------------------------


@given("the test training settings")
def _settings(cy_ctx: _CycleCtx, datatable: list[list[str]]) -> None:
    values = {cell["setting"]: cell["value"] for cell in _cells(datatable)}
    families = tuple(FeatureFamily(name.strip()) for name in values["families"].split(","))
    cy_ctx.settings = TrainingSettings(
        half_life_days=float(values["half_life_days"]),
        seed=int(values["seed"]),
        families=families,
        family_minima=SupportMinima(
            min_rows=int(values["family_min_rows"]),
            min_per_class=int(values["family_min_per_class"]),
            min_effective_n=float(values["family_min_effective_n"]),
        ),
        combiner_minima=SupportMinima(
            min_rows=int(values["combiner_min_rows"]),
            min_per_class=int(values["combiner_min_per_class"]),
            min_effective_n=float(values["combiner_min_effective_n"]),
        ),
        threshold_min_rows=int(values["threshold_min_rows"]),
        config_sha256="c" * 64,
        protocol_sha256="d" * 64,
    )


@given(parsers.parse("the registered monthly schedule from {start} to {end}"))
def _schedule(cy_ctx: _CycleCtx, start: str, end: str) -> None:
    cy_ctx.epochs = monthly_epochs(_iso(start), _iso(end))


@given('the trainer fixture batches "history-2015", "jan-2016", "feb-2016" and "mar-2016"')
def _fixture_batches(cy_ctx: _CycleCtx) -> None:
    batches, features = _trainer_fixture_data()
    cy_ctx.batches.update(batches)
    cy_ctx.features.update(features)


@given("an empty coordinator directory with an empty registry and an empty ledger")
def _empty_coordinator_dir(cy_ctx: _CycleCtx) -> None:
    assert not cy_ctx.coordinator_dir.exists()


@given(parsers.parse("a fake wall clock starting at {stamp}"))
def _fake_clock(cy_ctx: _CycleCtx, stamp: str) -> None:
    cy_ctx.clock = _FakeClock(_iso(stamp))


@given(parsers.parse("a registered cycle timeout of {seconds:d} seconds"))
def _timeout(cy_ctx: _CycleCtx, seconds: int) -> None:
    cy_ctx.timeout_seconds = float(seconds)


@given(parsers.parse('the cycle request "{name}"'))
def _cycle_request(cy_ctx: _CycleCtx, name: str, datatable: list[list[str]]) -> None:
    values = _field_value_table(datatable)
    cy_ctx.requests[name] = _build_request(cy_ctx, values)


@given(parsers.parse('the cycle request "{new_name}" equals "{base_name}" except {field} {value}'))
def _request_variant(
    cy_ctx: _CycleCtx, new_name: str, base_name: str, field: str, value: str
) -> None:
    base = cy_ctx.requests[base_name]
    raw = value.strip('"')
    if field == "protocol_hash":
        kwargs: dict[str, object] = {"protocol_hash": raw}
    elif field == "policy":
        kwargs = {"policy": raw}
    elif field == "source_watermark":
        kwargs = {"source_watermark": _parse_optional_iso(raw)}
    elif field == "activation_boundary":
        kwargs = {"activation_boundary": _iso(raw)}
    else:
        raise AssertionError(f"unsupported field {field!r}")
    cy_ctx.requests[new_name] = dataclasses.replace(base, **kwargs)  # type: ignore[arg-type]


@given("LightGBM fits are observed")
def _observe_lgbm(cy_ctx: _CycleCtx, monkeypatch: pytest.MonkeyPatch) -> None:
    _RecordingClassifier.observed = []
    monkeypatch.setattr(f7, "LGBMClassifier", _RecordingClassifier)


@given(parsers.parse('the LightGBM fit is made to raise "{message}"'))
def _lgbm_raises(cy_ctx: _CycleCtx, message: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(f7, "LGBMClassifier", _RaisingClassifier(message))


@given(parsers.parse("the fake wall clock advances {seconds:d} seconds during the fit stage"))
def _advance_during_fit(cy_ctx: _CycleCtx, seconds: int, monkeypatch: pytest.MonkeyPatch) -> None:
    delta = timedelta(seconds=seconds)
    clock = cy_ctx.clock

    class _AdvancingClassifier(LGBMClassifier):  # type: ignore[misc]
        def fit(self, X: Any, y: Any, **kwargs: Any) -> Any:  # noqa: N803
            clock.advance(delta)
            return super().fit(X, y, **kwargs)

    monkeypatch.setattr(f7, "LGBMClassifier", _AdvancingClassifier)


@given("the staged model is corrupted before the validate stage")
def _corrupt_staged_model(cy_ctx: _CycleCtx, monkeypatch: pytest.MonkeyPatch) -> None:
    def _write_garbage(path: Path, data: bytes) -> None:
        path.write_bytes(b"not valid json at all")

    monkeypatch.setattr(bundle_module, "_write_model_file", _write_garbage)


@given("the atomic rename of the staged bundle is made to fail")
def _break_rename(cy_ctx: _CycleCtx, monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(src: Path, dst: Path) -> None:
        raise OSError("injected rename failure")

    monkeypatch.setattr(bundle_module, "_rename", _raise)


@given(
    parsers.parse(
        "the fake wall clock advances {seconds:d} seconds when the bundle is renamed into "
        "the registry"
    )
)
def _advance_during_rename(
    cy_ctx: _CycleCtx, seconds: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    delta = timedelta(seconds=seconds)
    clock = cy_ctx.clock
    real_rename = bundle_module.os.replace

    def _advancing_rename(src: Path, dst: Path) -> None:
        real_rename(src, dst)
        clock.advance(delta)

    monkeypatch.setattr(bundle_module, "_rename", _advancing_rename)


@given("a coordinator with no injected clock")
def _coordinator_no_clock(cy_ctx: _CycleCtx) -> None:
    cy_ctx.coordinator = Coordinator(
        cy_ctx.coordinator_dir, cy_ctx.epochs, timeout_seconds=cy_ctx.timeout_seconds
    )


@given(
    parsers.parse(
        'the batch "{name}" additionally carries the row "{key}" available {available} with '
        "label_time {label_time} and label {label:d}"
    )
)
def _add_row_to_batch(
    cy_ctx: _CycleCtx, name: str, key: str, available: str, label_time: str, label: int
) -> None:
    original = cy_ctx.batches[name]
    new_row = SourceRow(
        key=key, available_at=_iso(available), label_time=_iso(label_time), label=label
    )
    updated = Batch(partition=original.partition, rows=(*original.rows, new_row))
    cy_ctx.batches[name] = updated
    cy_ctx.features[key] = {
        "trend_direction": 1.0,
        "trend_strength": 50.0,
        "higher_tf_trend_direction": 1.0,
        "rsi": 50.0,
        "macd_hist": 0.0,
    }
    # Requests built before this mutation captured the old `Batch` object by value; refresh
    # any that reference this partition so they see the additional row.
    for request_name, request in list(cy_ctx.requests.items()):
        if any(batch.partition == original.partition for batch in request.batches):
            cy_ctx.requests[request_name] = dataclasses.replace(
                request,
                batches=tuple(
                    updated if batch.partition == original.partition else batch
                    for batch in request.batches
                ),
            )


@given("the ledger's file bytes are remembered")
def _remember_ledger_bytes(cy_ctx: _CycleCtx) -> None:
    path = cy_ctx.ledger_dir / "ledger.json"
    cy_ctx.remembered_ledger_bytes = path.read_bytes() if path.exists() else None


# --- When ------------------------------------------------------------------------------------


@given(parsers.parse('the cycle request "{name}" is handled'))
@when(parsers.parse('the cycle request "{name}" is handled'))
@when(parsers.parse('the cycle request "{name}" is handled again'))
def _handle(cy_ctx: _CycleCtx, name: str) -> None:
    coordinator = _get_coordinator(cy_ctx)
    response = coordinator.handle(cy_ctx.requests[name])
    cy_ctx.responses[name] = response
    cy_ctx.response_history.append(response)
    cy_ctx.last_request_name = name


@when(
    parsers.parse(
        'a new coordinator is opened on the same directories and handles the cycle request "{name}"'
    )
)
def _handle_fresh_coordinator(cy_ctx: _CycleCtx, name: str) -> None:
    fresh = Coordinator(
        cy_ctx.coordinator_dir,
        cy_ctx.epochs,
        timeout_seconds=cy_ctx.timeout_seconds,
        clock=cy_ctx.clock,
    )
    response = fresh.handle(cy_ctx.requests[name])
    cy_ctx.responses[name] = response
    cy_ctx.response_history.append(response)
    cy_ctx.last_request_name = name


@given(parsers.parse('handling the cycle request "{name}" fails'))
@when(parsers.parse('handling the cycle request "{name}" fails'))
def _handle_fails(cy_ctx: _CycleCtx, name: str) -> None:
    coordinator = _get_coordinator(cy_ctx)
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011
        coordinator.handle(cy_ctx.requests[name])
    cy_ctx.error = exc_info.value
    cy_ctx.last_request_name = name


@when(parsers.parse('the atomic rename works again and the cycle request "{name}" is handled'))
def _retry_after_rename_fix(cy_ctx: _CycleCtx, name: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bundle_module, "_rename", bundle_module.os.replace)
    coordinator = _get_coordinator(cy_ctx)
    response = coordinator.handle(cy_ctx.requests[name])
    cy_ctx.responses[name] = response
    cy_ctx.response_history.append(response)
    cy_ctx.last_request_name = name


@when(parsers.parse('the LightGBM fit works again and the cycle request "{name}" is handled'))
def _retry_after_fit_fix(cy_ctx: _CycleCtx, name: str, monkeypatch: pytest.MonkeyPatch) -> None:
    from lightgbm import LGBMClassifier as _Real

    monkeypatch.setattr(f7, "LGBMClassifier", _Real)
    coordinator = _get_coordinator(cy_ctx)
    response = coordinator.handle(cy_ctx.requests[name])
    cy_ctx.responses[name] = response
    cy_ctx.response_history.append(response)
    cy_ctx.last_request_name = name


# --- Then ----------------------------------------------------------------------------------


@then(parsers.parse('the response status is "{status}"'))
def _response_status(cy_ctx: _CycleCtx, status: str) -> None:
    assert cy_ctx.responses[cy_ctx.last_request_name].status == status


@then("the response names a bundle_id")
def _response_names_bundle_id(cy_ctx: _CycleCtx) -> None:
    assert cy_ctx.responses[cy_ctx.last_request_name].bundle_id


@then(parsers.parse("the response activation_boundary is {stamp}"))
def _response_activation_boundary(cy_ctx: _CycleCtx, stamp: str) -> None:
    assert cy_ctx.responses[cy_ctx.last_request_name].activation_boundary == _iso(stamp)


@then("the response's bundle_id is actually present in the registry")
def _response_bundle_id_actually_published(cy_ctx: _CycleCtx) -> None:
    bundle_id = cy_ctx.responses[cy_ctx.last_request_name].bundle_id
    assert bundle_id in list_bundles(cy_ctx.registry_dir)


@then(parsers.parse('the cycle record lists the completed stages "{stages}"'))
def _completed_stages(cy_ctx: _CycleCtx, stages: str) -> None:
    expected = [stage.strip() for stage in stages.split(",")]
    assert _last_record(cy_ctx)["completed_stages"] == expected


@then(parsers.parse('the cycle record has {count:d} attempt with outcome "{outcome}"'))
@then(parsers.parse('the cycle record has {count:d} attempts with outcome "{outcome}"'))
def _attempt_count_outcome(cy_ctx: _CycleCtx, count: int, outcome: str) -> None:
    attempts = _last_record(cy_ctx)["attempts"]
    assert len(attempts) == count
    assert attempts[-1]["outcome"] == outcome


@then(
    parsers.parse(
        'the cycle record has {count:d} attempt with outcome "{outcome}" at stage "{stage}"'
    )
)
def _attempt_count_outcome_stage(cy_ctx: _CycleCtx, count: int, outcome: str, stage: str) -> None:
    attempts = _last_record(cy_ctx)["attempts"]
    assert len(attempts) == count
    assert attempts[-1]["outcome"] == outcome
    assert attempts[-1]["failed_stage"] == stage


@then(
    parsers.parse(
        'the cycle record has {count:d} attempts, the first "{outcome1}" at stage '
        '"{stage1}" and the second "{outcome2}"'
    )
)
def _two_attempts(cy_ctx: _CycleCtx, count: int, outcome1: str, stage1: str, outcome2: str) -> None:
    attempts = _last_record(cy_ctx)["attempts"]
    assert len(attempts) == count
    assert attempts[0]["outcome"] == outcome1
    assert attempts[0]["failed_stage"] == stage1
    assert attempts[-1]["outcome"] == outcome2


@then(
    parsers.parse(
        'the cycle record of "{name}" still has {count:d} attempt with outcome "{outcome}"'
    )
)
@then(parsers.parse('the cycle record of "{name}" has {count:d} attempt with outcome "{outcome}"'))
def _named_record_attempt_count(cy_ctx: _CycleCtx, name: str, count: int, outcome: str) -> None:
    record = _read_record(_cycle_dir_for(cy_ctx, name))
    assert len(record["attempts"]) == count
    assert record["attempts"][-1]["outcome"] == outcome


@then(
    parsers.parse(
        'the cycle record of "{name}" has {count:d} attempt with outcome "{outcome}" at '
        'stage "{stage}"'
    )
)
def _named_record_attempt_count_stage(
    cy_ctx: _CycleCtx, name: str, count: int, outcome: str, stage: str
) -> None:
    record = _read_record(_cycle_dir_for(cy_ctx, name))
    assert len(record["attempts"]) == count
    assert record["attempts"][-1]["outcome"] == outcome
    assert record["attempts"][-1]["failed_stage"] == stage


@then(parsers.parse('the cycle record\'s failed attempt reason names "{fragment}"'))
def _failed_attempt_reason(cy_ctx: _CycleCtx, fragment: str) -> None:
    attempts = _last_record(cy_ctx)["attempts"]
    assert fragment in (attempts[-1]["reason"] or "")


@then(parsers.parse("the ledger watermark is {stamp}"))
def _ledger_watermark(cy_ctx: _CycleCtx, stamp: str) -> None:
    ledger = Ledger.open(cy_ctx.ledger_dir)
    expected = None if stamp.strip().lower() == "none" else _iso(stamp)
    assert ledger.watermark == expected


@then(
    parsers.parse(
        "the cycle's mature stage recorded {mature:d} mature keys and {pending:d} pending keys"
    )
)
def _mature_stage_counts(cy_ctx: _CycleCtx, mature: int, pending: int) -> None:
    payload = json.loads(
        (_last_cycle_dir(cy_ctx) / "checkpoints" / "mature" / "keys.json").read_text()
    )
    assert len(payload["mature_keys"]) == mature
    assert len(payload["pending_keys"]) == pending


@then(parsers.parse('the cycle\'s pending keys are "{keys}"'))
def _pending_keys(cy_ctx: _CycleCtx, keys: str) -> None:
    payload = json.loads(
        (_last_cycle_dir(cy_ctx) / "checkpoints" / "mature" / "keys.json").read_text()
    )
    expected = tuple(key.strip() for key in keys.split(","))
    assert tuple(payload["pending_keys"]) == expected


@then(parsers.parse('the fitted epoch\'s threshold row keys are "{keys}"'))
def _fitted_threshold_keys(cy_ctx: _CycleCtx, keys: str) -> None:
    request = cy_ctx.requests[cy_ctx.last_request_name]
    epoch = epoch_starting(cy_ctx.epochs, request.activation_boundary)
    spans = stage_spans(epoch, request.policy)
    ledger = Ledger.open(cy_ctx.ledger_dir)
    mature_rows = ledger.rows(ledger.mature_keys(request.cutoff))
    admitted = select_rows(mature_rows, spans.threshold)
    expected = tuple(key.strip() for key in keys.split(","))
    assert tuple(row.key for row in admitted) == expected


@then(parsers.parse("{count:d} LightGBM fits were observed"))
def _lgbm_fit_count(cy_ctx: _CycleCtx, count: int) -> None:
    assert len(_RecordingClassifier.observed) == count


@then(parsers.parse("the registry lists {count:d} published bundle"))
@then(parsers.parse("the registry lists {count:d} published bundles"))
def _registry_lists(cy_ctx: _CycleCtx, count: int) -> None:
    assert len(bundle_module.list_bundles(cy_ctx.registry_dir)) == count


@then("no manifest.json exists in the registry outside a staging directory")
def _no_manifest_outside_staging(cy_ctx: _CycleCtx) -> None:
    for path in cy_ctx.registry_dir.rglob("manifest.json"):
        assert path.parent.name.startswith(".staging-"), f"unexpected published manifest {path}"


@then(
    parsers.parse(
        'the eligible bundle for policy "{policy}" at {stamp} is the response\'s bundle_id'
    )
)
def _eligible_is_response(cy_ctx: _CycleCtx, policy: str, stamp: str) -> None:
    coordinator = _get_coordinator(cy_ctx)
    eligible = coordinator.eligible_bundle(policy, _iso(stamp))
    assert eligible == cy_ctx.responses[cy_ctx.last_request_name].bundle_id


def _last_eligible_bundle_id(cy_ctx: _CycleCtx) -> str:
    request = cy_ctx.requests[cy_ctx.last_request_name]
    coordinator = _get_coordinator(cy_ctx)
    return coordinator.eligible_bundle(request.policy, request.activation_boundary)


@then(parsers.parse("the eligible bundle's manifest activation_boundary is {stamp}"))
def _eligible_manifest_activation_boundary(cy_ctx: _CycleCtx, stamp: str) -> None:
    loaded = load(cy_ctx.registry_dir, _last_eligible_bundle_id(cy_ctx))
    assert loaded.manifest["activation_boundary"] == stamp


@then(parsers.parse("the eligible bundle's manifest published_at is {stamp} by the fake clock"))
def _eligible_manifest_published_at(cy_ctx: _CycleCtx, stamp: str) -> None:
    loaded = load(cy_ctx.registry_dir, _last_eligible_bundle_id(cy_ctx))
    assert loaded.manifest["published_at"] == stamp


@then(parsers.parse("the eligible bundle's deployment span is [{start}, {end})"))
def _eligible_deployment_span(cy_ctx: _CycleCtx, start: str, end: str) -> None:
    loaded = load(cy_ctx.registry_dir, _last_eligible_bundle_id(cy_ctx))
    assert loaded.manifest["spans"]["deployment"] == {"start": start, "end": end}


@then(parsers.parse("the cycle record's attempt started at {stamp} by the fake clock"))
def _attempt_started_at(cy_ctx: _CycleCtx, stamp: str) -> None:
    assert _last_record(cy_ctx)["attempts"][-1]["started_at"] == stamp


@then(
    parsers.parse(
        "the cycle record's attempt started within {minutes:d} minutes of the real "
        "wall-clock instant"
    )
)
def _attempt_started_near_real_clock(cy_ctx: _CycleCtx, minutes: int) -> None:
    started_at = datetime.fromisoformat(
        _last_record(cy_ctx)["attempts"][-1]["started_at"].replace("Z", "+00:00")
    )
    assert abs((datetime.now(UTC) - started_at).total_seconds()) < minutes * 60


@then("both responses name the same bundle_id")
def _both_responses_same_bundle_id(cy_ctx: _CycleCtx) -> None:
    first, second = cy_ctx.response_history[-2], cy_ctx.response_history[-1]
    assert first.bundle_id == second.bundle_id


@then(parsers.parse('the cycle failure names "{fragment}"'))
def _cycle_failure_names(cy_ctx: _CycleCtx, fragment: str) -> None:
    assert cy_ctx.error is not None
    assert fragment in str(cy_ctx.error)


@then(
    parsers.parse(
        'the eligible bundle for policy "{policy1}" at {stamp} differs from the eligible '
        'bundle for policy "{policy2}"'
    )
)
def _eligible_differs_policy(cy_ctx: _CycleCtx, policy1: str, stamp: str, policy2: str) -> None:
    coordinator = _get_coordinator(cy_ctx)
    boundary = _iso(stamp)
    assert coordinator.eligible_bundle(policy1, boundary) != coordinator.eligible_bundle(
        policy2, boundary
    )


@then(
    parsers.parse(
        'the eligible bundle for policy "{policy}" at {stamp1} differs from the eligible '
        "bundle at {stamp2}"
    )
)
def _eligible_differs_boundary(cy_ctx: _CycleCtx, policy: str, stamp1: str, stamp2: str) -> None:
    coordinator = _get_coordinator(cy_ctx)
    assert coordinator.eligible_bundle(policy, _iso(stamp1)) != coordinator.eligible_bundle(
        policy, _iso(stamp2)
    )


@then(parsers.parse('the eligible bundle for policy "{policy}" at {stamp} is unchanged'))
def _eligible_unchanged(cy_ctx: _CycleCtx, policy: str, stamp: str) -> None:
    coordinator = _get_coordinator(cy_ctx)
    current = coordinator.eligible_bundle(policy, _iso(stamp))
    assert current == cy_ctx.responses["first-U"].bundle_id


@then(
    parsers.parse(
        'looking up the eligible bundle for policy "{policy}" at {stamp} fails naming "{fragment}"'
    )
)
def _eligible_lookup_fails(cy_ctx: _CycleCtx, policy: str, stamp: str, fragment: str) -> None:
    coordinator = _get_coordinator(cy_ctx)
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011
        coordinator.eligible_bundle(policy, _iso(stamp))
    assert fragment in str(exc_info.value)


def _registry_bytes(registry: Path) -> dict[str, bytes]:
    if not registry.exists():
        return {}
    return {str(path): path.read_bytes() for path in registry.rglob("*") if path.is_file()}


@given("the registry's file bytes are remembered")
def _remember_registry_bytes(cy_ctx: _CycleCtx) -> None:
    cy_ctx.remembered_registry_bytes = _registry_bytes(cy_ctx.registry_dir)


@then("the registry's file bytes are unchanged")
def _registry_bytes_unchanged(cy_ctx: _CycleCtx) -> None:
    assert _registry_bytes(cy_ctx.registry_dir) == cy_ctx.remembered_registry_bytes


@then("the ledger's file bytes are unchanged")
def _ledger_bytes_unchanged(cy_ctx: _CycleCtx) -> None:
    path = cy_ctx.ledger_dir / "ledger.json"
    current = path.read_bytes() if path.exists() else None
    assert current == cy_ctx.remembered_ledger_bytes
