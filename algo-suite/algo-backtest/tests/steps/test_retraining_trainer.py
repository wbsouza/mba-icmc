"""Steps for retraining_trainer.feature: one epoch's weighted training and publication."""

from __future__ import annotations

import dataclasses
import hashlib
import math
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from algo_backtest.chain.filters import f7_meta_learner as f7
from algo_backtest.chain.filters.f7_meta_learner import FeatureFamily, family_vector
from algo_backtest.retraining import bundle as bundle_module
from algo_backtest.retraining.bundle import load
from algo_backtest.retraining.ingestion import Batch, Ledger, SourceRow, consume
from algo_backtest.retraining.schedule import Epoch, monthly_epochs
from algo_backtest.retraining.trainer import EpochResult, TrainingSettings, train_epoch
from algo_backtest.retraining.weights import REGISTERED_MINIMA, SupportMinima
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/retraining_trainer.feature")

_POLICIES = ("F", "Q", "R", "U", "E")
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


class _RecordingClassifier:
    """Records every `fit` call, then really fits via the real `LGBMClassifier`."""

    observed: list[_ObservedFit] = []

    def __init__(self, *args: object, **kwargs: object) -> None:
        from lightgbm import LGBMClassifier

        self._inner = LGBMClassifier(*args, **kwargs)

    def fit(self, *args: object, **kwargs: object) -> Any:
        _RecordingClassifier.observed.append(
            _ObservedFit(has_sample_weight="sample_weight" in kwargs)
        )
        return self._inner.fit(*args, **kwargs)

    def predict_proba(self, *args: object, **kwargs: object) -> Any:
        return self._inner.predict_proba(*args, **kwargs)


@dataclass
class _TrainerCtx:
    """Per-scenario state for the trainer orchestration feature."""

    base_dir: Path
    settings: TrainingSettings | None = None
    epochs: tuple[Epoch, ...] = ()
    registry: Path = field(init=False)
    ledger_dir: Path = field(init=False)
    features: dict[str, dict[str, object]] = field(default_factory=dict)
    batches: dict[str, Batch] = field(default_factory=dict)
    results: dict[str, EpochResult] = field(default_factory=dict)
    all_results: list[EpochResult] = field(default_factory=list)
    last: EpochResult | None = None
    error: Exception | None = None
    remembered: dict[str, object] = field(default_factory=dict)
    remembered_registry_bytes: dict[str, bytes] = field(default_factory=dict)
    trade_context_keys: set[str] = field(default_factory=set)
    shared_features: dict[str, object] | None = None
    registry_counter: int = 0
    ledger_counter: int = 0

    def __post_init__(self) -> None:
        self.registry = self.base_dir / "registry"
        self.ledger_dir = self.base_dir / "ledger"


@pytest.fixture
def tr_ctx(tmp_path: Path) -> _TrainerCtx:
    return _TrainerCtx(base_dir=tmp_path)


def _iso(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def _cells(datatable: list[list[str]]) -> list[dict[str, str]]:
    header, *rows = datatable
    return [dict(zip(header, row, strict=True)) for row in rows]


def _epoch_by_start(tr_ctx: _TrainerCtx, start: str) -> Epoch:
    target = _iso(start)
    for epoch in tr_ctx.epochs:
        if epoch.start == target:
            return epoch
    raise AssertionError(f"no registered epoch starts at {start}")


def _registry_bytes(registry: Path) -> dict[str, bytes]:
    if not registry.exists():
        return {}
    return {str(path): path.read_bytes() for path in registry.rglob("*") if path.is_file()}


def _fresh_registry(tr_ctx: _TrainerCtx) -> Path:
    tr_ctx.registry_counter += 1
    path = tr_ctx.base_dir / f"registry-{tr_ctx.registry_counter}"
    return path


# --- Given -----------------------------------------------------------------------------------


@given("the test training settings")
def _settings(tr_ctx: _TrainerCtx, datatable: list[list[str]]) -> None:
    values = {cell["setting"]: cell["value"] for cell in _cells(datatable)}
    families = tuple(FeatureFamily(name.strip()) for name in values["families"].split(","))
    tr_ctx.settings = TrainingSettings(
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
def _schedule(tr_ctx: _TrainerCtx, start: str, end: str) -> None:
    tr_ctx.epochs = monthly_epochs(_iso(start), _iso(end))


@given("an empty bundle registry directory")
def _empty_registry(tr_ctx: _TrainerCtx) -> None:
    assert not tr_ctx.registry.exists()


@given("an empty ledger directory")
def _empty_ledger(tr_ctx: _TrainerCtx) -> None:
    assert not tr_ctx.ledger_dir.exists()


@given(parsers.parse('the source batch "{name}" carries the rows'))
def _source_batch(tr_ctx: _TrainerCtx, name: str, datatable: list[list[str]]) -> None:
    rows = []
    for cell in _cells(datatable):
        key = cell["key"]
        rows.append(
            SourceRow(
                key=key,
                available_at=_iso(cell["available_at"]),
                label_time=_iso(cell["label_time"]),
                label=int(cell["label"]),
            )
        )
        tr_ctx.features[key] = {column: float(cell[column]) for column in _FAMILY_COLUMNS}
    tr_ctx.batches[name] = Batch(partition=name, rows=tuple(rows))


@given(parsers.parse('the batches "{names}" are consumed into the ledger'))
def _consume_into_ledger(tr_ctx: _TrainerCtx, names: str) -> None:
    for name in (n.strip() for n in names.split(",")):
        consume(tr_ctx.ledger_dir, tr_ctx.batches[name])


@given(parsers.parse('the batches "{names}" are consumed into a fresh ledger'))
def _consume_into_fresh_ledger(tr_ctx: _TrainerCtx, names: str) -> None:
    tr_ctx.ledger_counter += 1
    fresh = tr_ctx.base_dir / f"ledger-{tr_ctx.ledger_counter}"
    for name in (n.strip() for n in names.split(",")):
        consume(fresh, tr_ctx.batches[name])
    tr_ctx.ledger_dir = fresh


@given(parsers.parse('the batch "{name}" is consumed into the ledger'))
def _consume_one_into_ledger(tr_ctx: _TrainerCtx, name: str) -> None:
    consume(tr_ctx.ledger_dir, tr_ctx.batches[name])


@given("the training settings use the registered support minima")
def _use_registered_minima(tr_ctx: _TrainerCtx) -> None:
    assert tr_ctx.settings is not None
    tr_ctx.settings = dataclasses.replace(
        tr_ctx.settings,
        family_minima=REGISTERED_MINIMA["family"],
        combiner_minima=REGISTERED_MINIMA["combiner"],
        threshold_min_rows=REGISTERED_MINIMA["threshold"].min_rows,
    )


@given("the training settings set combiner_min_per_class to none")
def _null_combiner_per_class(tr_ctx: _TrainerCtx) -> None:
    assert tr_ctx.settings is not None
    tr_ctx.settings = dataclasses.replace(
        tr_ctx.settings,
        combiner_minima=dataclasses.replace(tr_ctx.settings.combiner_minima, min_per_class=None),
    )


@given("LightGBM fits are observed")
def _observe_lgbm(tr_ctx: _TrainerCtx, monkeypatch: pytest.MonkeyPatch) -> None:
    _RecordingClassifier.observed = []
    monkeypatch.setattr(f7, "LGBMClassifier", _RecordingClassifier)


@given(parsers.parse('the LightGBM fit is made to raise "{message}"'))
def _lgbm_raises(tr_ctx: _TrainerCtx, message: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(f7, "LGBMClassifier", _RaisingClassifier(message))


@given(parsers.parse('the batch "{name}" is replaced by the same rows all labeled 1'))
def _relabel_all_ones(tr_ctx: _TrainerCtx, name: str) -> None:
    original = tr_ctx.batches[name]
    new_rows = tuple(dataclasses.replace(row, label=1) for row in original.rows)
    tr_ctx.batches[name] = dataclasses.replace(original, rows=new_rows)


@given(
    parsers.parse(
        'the batch "{name}" is replaced by rows sharing identical features, labeled {labels} '
        "from oldest to newest"
    )
)
def _replace_identical_features(tr_ctx: _TrainerCtx, name: str, labels: str) -> None:
    original = tr_ctx.batches[name]
    label_values = [int(part.strip()) for part in labels.split(",")]
    assert len(label_values) == len(original.rows)
    shared = {"trend_direction": 1.0, "trend_strength": 50.0, "higher_tf_trend_direction": 1.0}
    new_rows = tuple(
        dataclasses.replace(row, label=label_values[i]) for i, row in enumerate(original.rows)
    )
    tr_ctx.batches[name] = dataclasses.replace(original, rows=new_rows)
    for row in new_rows:
        # Only the TREND columns become identical (what the probe below reads); the
        # INDICATOR columns (rsi/macd_hist) keep their original per-row variation so the
        # indicator family and the downstream combiner/threshold fit stay non-degenerate.
        tr_ctx.features[row.key] = {**tr_ctx.features[row.key], **shared}
    tr_ctx.shared_features = shared


@given("the trade context attached to the rows")
def _trade_context(tr_ctx: _TrainerCtx, datatable: list[list[str]]) -> None:
    for cell in _cells(datatable):
        key = cell["key"]
        pnl = None if cell["trade_pnl"] == "none" else float(cell["trade_pnl"])
        tr_ctx.features[key] = {
            **tr_ctx.features[key],
            "vetoed": cell["vetoed"] == "yes",
            "traded": cell["traded"] == "yes",
            "trade_pnl": pnl,
        }
        tr_ctx.trade_context_keys.add(key)


# --- When ------------------------------------------------------------------------------------


@when(parsers.parse("the epoch starting {start} is trained for policy {policy}"))
def _train(tr_ctx: _TrainerCtx, start: str, policy: str) -> None:
    assert tr_ctx.settings is not None
    epoch = _epoch_by_start(tr_ctx, start)
    ledger = Ledger.open(tr_ctx.ledger_dir)
    result = train_epoch(policy, epoch, ledger, tr_ctx.features, tr_ctx.registry, tr_ctx.settings)
    tr_ctx.last = result
    tr_ctx.results[policy] = result
    tr_ctx.all_results.append(result)


@when(parsers.parse("the epoch starting {start} is trained for each policy F, Q, R, U, E"))
def _train_all_policies(tr_ctx: _TrainerCtx, start: str) -> None:
    assert tr_ctx.settings is not None
    epoch = _epoch_by_start(tr_ctx, start)
    ledger = Ledger.open(tr_ctx.ledger_dir)
    for policy in _POLICIES:
        result = train_epoch(
            policy, epoch, ledger, tr_ctx.features, tr_ctx.registry, tr_ctx.settings
        )
        tr_ctx.results[policy] = result
        tr_ctx.all_results.append(result)
        tr_ctx.last = result


@when(parsers.parse("training the epoch starting {start} for policy {policy} fails"))
def _train_fails(tr_ctx: _TrainerCtx, start: str, policy: str) -> None:
    assert tr_ctx.settings is not None
    epoch = _epoch_by_start(tr_ctx, start)
    ledger = Ledger.open(tr_ctx.ledger_dir)
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011
        train_epoch(policy, epoch, ledger, tr_ctx.features, tr_ctx.registry, tr_ctx.settings)
    tr_ctx.error = exc_info.value


@when("the epoch's bundle_id, hashes.model_sha256, thresholds and row keys are remembered")
def _remember_all(tr_ctx: _TrainerCtx) -> None:
    assert tr_ctx.last is not None
    r = tr_ctx.last
    tr_ctx.remembered = {
        "bundle_id": r.bundle_id,
        "model_sha256": r.manifest["hashes"]["model_sha256"],
        "thresholds": (r.theta_low, r.theta_high),
        "row_keys": (r.family.row_keys, r.combiner.row_keys, r.threshold_row_keys),
    }


@when("the epoch's bundle_id and row keys are remembered")
def _remember_bundle_and_rows(tr_ctx: _TrainerCtx) -> None:
    assert tr_ctx.last is not None
    r = tr_ctx.last
    tr_ctx.remembered = {
        "bundle_id": r.bundle_id,
        "row_keys": (r.family.row_keys, r.combiner.row_keys, r.threshold_row_keys),
    }


@when("the published bundle's file bytes are remembered")
def _remember_registry_bytes(tr_ctx: _TrainerCtx) -> None:
    tr_ctx.remembered_registry_bytes = _registry_bytes(tr_ctx.registry)


@when(
    parsers.parse(
        'the batch "{name}" is consumed into the ledger with every feature value doubled and '
        "every label flipped"
    )
)
def _consume_mutated(tr_ctx: _TrainerCtx, name: str) -> None:
    original = tr_ctx.batches[name]
    flipped_rows = tuple(dataclasses.replace(row, label=1 - row.label) for row in original.rows)
    consume(tr_ctx.ledger_dir, dataclasses.replace(original, rows=flipped_rows))
    for row in original.rows:
        doubled = {
            column: value * 2 if isinstance(value, float) else value
            for column, value in tr_ctx.features[row.key].items()
        }
        tr_ctx.features[row.key] = doubled


@when(
    parsers.parse(
        "the epoch starting {start} is trained again for policy {policy} into a fresh registry"
    )
)
def _train_again_fresh(tr_ctx: _TrainerCtx, start: str, policy: str) -> None:
    assert tr_ctx.settings is not None
    epoch = _epoch_by_start(tr_ctx, start)
    ledger = Ledger.open(tr_ctx.ledger_dir)
    fresh = _fresh_registry(tr_ctx)
    result = train_epoch(policy, epoch, ledger, tr_ctx.features, fresh, tr_ctx.settings)
    tr_ctx.last = result
    tr_ctx.results[policy] = result
    tr_ctx.all_results.append(result)


@when(parsers.parse("the epoch starting {start} is trained again for policy {policy}"))
def _train_again_same(tr_ctx: _TrainerCtx, start: str, policy: str) -> None:
    assert tr_ctx.settings is not None
    epoch = _epoch_by_start(tr_ctx, start)
    ledger = Ledger.open(tr_ctx.ledger_dir)
    result = train_epoch(policy, epoch, ledger, tr_ctx.features, tr_ctx.registry, tr_ctx.settings)
    tr_ctx.last = result
    tr_ctx.results[policy] = result
    tr_ctx.all_results.append(result)


@when(
    parsers.parse(
        "every trade context field is flipped and the epoch starting {start} is trained again "
        "for policy {policy} into a fresh registry"
    )
)
def _flip_context_and_retrain(tr_ctx: _TrainerCtx, start: str, policy: str) -> None:
    assert tr_ctx.settings is not None
    for key in tr_ctx.trade_context_keys:
        current = tr_ctx.features[key]
        tr_ctx.features[key] = {
            **current,
            "vetoed": not current["vetoed"],
            "traded": not current["traded"],
            "trade_pnl": None if current["trade_pnl"] is not None else 999.0,
        }
    epoch = _epoch_by_start(tr_ctx, start)
    ledger = Ledger.open(tr_ctx.ledger_dir)
    fresh = _fresh_registry(tr_ctx)
    result = train_epoch(policy, epoch, ledger, tr_ctx.features, fresh, tr_ctx.settings)
    tr_ctx.last = result


# --- Then ----------------------------------------------------------------------------------


@then(parsers.parse('a bundle is published for policy "{policy}"'))
def _bundle_published(tr_ctx: _TrainerCtx, policy: str) -> None:
    result = tr_ctx.results[policy]
    assert result.bundle_id in bundle_module.list_bundles(tr_ctx.registry)


@then(parsers.parse('the epoch\'s family row keys are "{keys}"'))
def _family_row_keys(tr_ctx: _TrainerCtx, keys: str) -> None:
    assert tr_ctx.last is not None
    expected = tuple(key.strip() for key in keys.split(","))
    assert tr_ctx.last.family.row_keys == expected


@then(parsers.parse('the epoch\'s combiner row keys are "{keys}"'))
def _combiner_row_keys(tr_ctx: _TrainerCtx, keys: str) -> None:
    assert tr_ctx.last is not None
    expected = tuple(key.strip() for key in keys.split(","))
    assert tr_ctx.last.combiner.row_keys == expected


@then(parsers.parse('the epoch\'s threshold row keys are "{keys}"'))
def _threshold_row_keys(tr_ctx: _TrainerCtx, keys: str) -> None:
    assert tr_ctx.last is not None
    expected = tuple(key.strip() for key in keys.split(","))
    assert tr_ctx.last.threshold_row_keys == expected


def _parse_floats(text: str) -> list[float]:
    return [float(part.strip()) for part in text.split(",")]


def _assert_close(actual: tuple[float, ...], expected: list[float]) -> None:
    assert len(actual) == len(expected)
    for a, e in zip(actual, expected, strict=True):
        assert math.isclose(a, e, rel_tol=1e-9, abs_tol=1e-12), f"{a} != {e}"


@then(parsers.parse("the epoch's family weights are {weights}"))
def _family_weights(tr_ctx: _TrainerCtx, weights: str) -> None:
    assert tr_ctx.last is not None
    _assert_close(tr_ctx.last.family.weights, _parse_floats(weights))


@then(parsers.parse("the epoch's combiner weights are {weights}"))
def _combiner_weights(tr_ctx: _TrainerCtx, weights: str) -> None:
    assert tr_ctx.last is not None
    _assert_close(tr_ctx.last.combiner.weights, _parse_floats(weights))


@then(parsers.parse("the epoch's raw family weights are {weights}"))
def _raw_family_weights(tr_ctx: _TrainerCtx, weights: str) -> None:
    assert tr_ctx.last is not None
    _assert_close(tr_ctx.last.family.raw_weights, _parse_floats(weights))


@then(parsers.parse("the epoch's raw combiner weights are {weights}"))
def _raw_combiner_weights(tr_ctx: _TrainerCtx, weights: str) -> None:
    assert tr_ctx.last is not None
    _assert_close(tr_ctx.last.combiner.raw_weights, _parse_floats(weights))


@then(parsers.parse("the epoch's family n_eff is {value:g}"))
def _family_n_eff(tr_ctx: _TrainerCtx, value: float) -> None:
    assert tr_ctx.last is not None
    assert math.isclose(tr_ctx.last.family.n_eff, value, rel_tol=1e-9)


@then(parsers.parse("the epoch's combiner n_eff is {value:g}"))
def _combiner_n_eff(tr_ctx: _TrainerCtx, value: float) -> None:
    assert tr_ctx.last is not None
    assert math.isclose(tr_ctx.last.combiner.n_eff, value, rel_tol=1e-9)


@then(parsers.parse('the epoch\'s family weighting is "{weighting}"'))
def _family_weighting(tr_ctx: _TrainerCtx, weighting: str) -> None:
    assert tr_ctx.last is not None
    assert tr_ctx.last.family.weighting == weighting


@then(parsers.parse("the epoch's family half-life is {value:g} days"))
def _family_half_life(tr_ctx: _TrainerCtx, value: float) -> None:
    assert tr_ctx.last is not None
    assert tr_ctx.last.family.half_life_days == value


@then(parsers.parse("the epoch's combiner half-life is {value:g} days"))
def _combiner_half_life(tr_ctx: _TrainerCtx, value: float) -> None:
    assert tr_ctx.last is not None
    assert tr_ctx.last.combiner.half_life_days == value


@then("the epoch's thresholds are strictly inside (0, 1) with theta_low below theta_high")
def _thresholds_valid(tr_ctx: _TrainerCtx) -> None:
    assert tr_ctx.last is not None
    assert 0.0 < tr_ctx.last.theta_low < tr_ctx.last.theta_high < 1.0


@then(
    "the epoch's thresholds equal the 0.10 and 0.90 linear quantiles of the published "
    "model's p_hat over the threshold rows"
)
def _thresholds_equal_quantiles(tr_ctx: _TrainerCtx) -> None:
    assert tr_ctx.last is not None
    loaded = load(tr_ctx.registry, tr_ctx.last.bundle_id)
    scores = [loaded.model.predict(tr_ctx.features[key]) for key in tr_ctx.last.threshold_row_keys]
    assert math.isclose(float(np.quantile(scores, 0.10)), tr_ctx.last.theta_low, rel_tol=1e-9)
    assert math.isclose(float(np.quantile(scores, 0.90)), tr_ctx.last.theta_high, rel_tol=1e-9)


@then(parsers.parse("the epoch's ledger watermark is {stamp}"))
def _ledger_watermark(tr_ctx: _TrainerCtx, stamp: str) -> None:
    assert tr_ctx.last is not None
    assert tr_ctx.last.ledger_watermark == _iso(stamp)


@then(parsers.parse("the epoch's seed is {value:d}"))
def _epoch_seed(tr_ctx: _TrainerCtx, value: int) -> None:
    assert tr_ctx.last is not None
    assert tr_ctx.last.seed == value


@then(parsers.parse("the epoch's deployment span is [{start}, {end})"))
def _deployment_span(tr_ctx: _TrainerCtx, start: str, end: str) -> None:
    assert tr_ctx.last is not None
    assert tr_ctx.last.deployment.start == _iso(start)
    assert tr_ctx.last.deployment.end == _iso(end)


@then(parsers.parse("the epoch's activation boundary is {stamp}"))
def _activation_boundary(tr_ctx: _TrainerCtx, stamp: str) -> None:
    assert tr_ctx.last is not None
    assert tr_ctx.last.activation_boundary == _iso(stamp)


@then("the policies F, Q and U have the same hashes.model_sha256")
def _fqu_same_model(tr_ctx: _TrainerCtx) -> None:
    hashes = {
        policy: tr_ctx.results[policy].manifest["hashes"]["model_sha256"]
        for policy in ("F", "Q", "U")
    }
    assert len(set(hashes.values())) == 1, hashes


@then("the policies F, Q and U have the same thresholds")
def _fqu_same_thresholds(tr_ctx: _TrainerCtx) -> None:
    thresholds = {
        policy: (tr_ctx.results[policy].theta_low, tr_ctx.results[policy].theta_high)
        for policy in ("F", "Q", "U")
    }
    assert len(set(thresholds.values())) == 1, thresholds


@then("the policy R's hashes.model_sha256 differs from U's")
def _r_differs_from_u(tr_ctx: _TrainerCtx) -> None:
    r_hash = tr_ctx.results["R"].manifest["hashes"]["model_sha256"]
    u_hash = tr_ctx.results["U"].manifest["hashes"]["model_sha256"]
    assert r_hash != u_hash


@then("the policy E's hashes.model_sha256 differs from U's")
def _e_differs_from_u(tr_ctx: _TrainerCtx) -> None:
    e_hash = tr_ctx.results["E"].manifest["hashes"]["model_sha256"]
    u_hash = tr_ctx.results["U"].manifest["hashes"]["model_sha256"]
    assert e_hash != u_hash


@then(parsers.parse("the registry lists {count:d} published bundle"))
@then(parsers.parse("the registry lists {count:d} published bundles"))
def _registry_lists(tr_ctx: _TrainerCtx, count: int) -> None:
    assert len(bundle_module.list_bundles(tr_ctx.registry)) == count


@then(parsers.parse("the ledger holds no row available at or after {stamp}"))
def _no_row_at_or_after(tr_ctx: _TrainerCtx, stamp: str) -> None:
    cutoff = _iso(stamp)
    ledger = Ledger.open(tr_ctx.ledger_dir)
    # visible_keys(cutoff) is inclusive; if the ledger has no row exactly at/after cutoff,
    # visible_keys(cutoff) must already contain everything the ledger holds.
    visible = ledger.visible_keys(cutoff)
    all_visible = ledger.visible_keys(datetime(2100, 1, 1, tzinfo=cutoff.tzinfo))
    assert set(visible) == set(all_visible)


@then(
    parsers.re(
        r"^(?P<policy>[UE])'s published trend family P\(up\) for the shared features is "
        r"(?P<relation>above|below) (?P<bound>[\d.]+)$"
    )
)
def _shared_feature_p_up(tr_ctx: _TrainerCtx, policy: str, relation: str, bound: str) -> None:
    result = tr_ctx.results[policy]
    loaded = load(tr_ctx.registry, result.bundle_id)
    assert tr_ctx.shared_features is not None
    p_up = loaded.model.family_models[FeatureFamily.TREND].predict_proba_up(
        family_vector(FeatureFamily.TREND, tr_ctx.shared_features)
    )
    limit = float(bound)
    if relation == "above":
        assert p_up > limit
    else:
        assert p_up < limit


@then(parsers.parse("the epoch's hashes.model_sha256 {relation} F's first-epoch payload hash"))
def _payload_relation(tr_ctx: _TrainerCtx, relation: str) -> None:
    assert tr_ctx.last is not None
    f_hash = tr_ctx.results["F"].manifest["hashes"]["model_sha256"]
    last_hash = tr_ctx.last.manifest["hashes"]["model_sha256"]
    if relation == "equals":
        assert last_hash == f_hash
    else:
        assert relation == "differs from"
        assert last_hash != f_hash


@then(parsers.parse("the epoch's thresholds {relation} F's first-epoch thresholds"))
def _thresholds_relation_to_f(tr_ctx: _TrainerCtx, relation: str) -> None:
    assert tr_ctx.last is not None
    f_result = tr_ctx.results["F"]
    last_thresholds = (tr_ctx.last.theta_low, tr_ctx.last.theta_high)
    f_thresholds = (f_result.theta_low, f_result.theta_high)
    if relation == "equals":
        assert last_thresholds == f_thresholds
    else:
        assert relation == "differs from"
        assert last_thresholds != f_thresholds


@then(parsers.parse('the training failure names "{fragment}"'))
def _failure_names(tr_ctx: _TrainerCtx, fragment: str) -> None:
    assert tr_ctx.error is not None
    assert fragment in str(tr_ctx.error)


@then(parsers.parse("{count:d} LightGBM fits were observed"))
def _lgbm_fit_count(tr_ctx: _TrainerCtx, count: int) -> None:
    assert len(_RecordingClassifier.observed) == count


@then("no manifest.json exists in the registry outside a staging directory")
def _no_manifest_outside_staging(tr_ctx: _TrainerCtx) -> None:
    for path in tr_ctx.registry.rglob("manifest.json"):
        assert path.parent.name.startswith(".staging-"), f"unexpected published manifest {path}"


@then(parsers.parse('the row "{key}" is mature in the ledger'))
def _row_mature(tr_ctx: _TrainerCtx, key: str) -> None:
    assert Ledger.open(tr_ctx.ledger_dir).maturity(key) == "mature"


@then(parsers.parse('the row "{key}" is pending in the ledger'))
def _row_pending(tr_ctx: _TrainerCtx, key: str) -> None:
    assert Ledger.open(tr_ctx.ledger_dir).maturity(key) == "pending"


@then(
    parsers.parse(
        "the epoch's stage row counts are family {family:d}, combiner {combiner:d}, "
        "threshold {threshold:d}"
    )
)
def _stage_row_counts(tr_ctx: _TrainerCtx, family: int, combiner: int, threshold: int) -> None:
    assert tr_ctx.last is not None
    assert tr_ctx.last.family.rows == family
    assert tr_ctx.last.combiner.rows == combiner
    assert len(tr_ctx.last.threshold_row_keys) == threshold


@then("the epoch's bundle_id is unchanged")
def _bundle_id_unchanged(tr_ctx: _TrainerCtx) -> None:
    assert tr_ctx.last is not None
    assert tr_ctx.last.bundle_id == tr_ctx.remembered["bundle_id"]


@then("the epoch's hashes.model_sha256 is unchanged")
def _model_sha256_unchanged(tr_ctx: _TrainerCtx) -> None:
    assert tr_ctx.last is not None
    assert tr_ctx.last.manifest["hashes"]["model_sha256"] == tr_ctx.remembered["model_sha256"]


@then("the epoch's thresholds are unchanged")
def _thresholds_unchanged(tr_ctx: _TrainerCtx) -> None:
    assert tr_ctx.last is not None
    assert (tr_ctx.last.theta_low, tr_ctx.last.theta_high) == tr_ctx.remembered["thresholds"]


@then("the epoch's row keys are unchanged")
def _row_keys_unchanged(tr_ctx: _TrainerCtx) -> None:
    assert tr_ctx.last is not None
    actual = (
        tr_ctx.last.family.row_keys,
        tr_ctx.last.combiner.row_keys,
        tr_ctx.last.threshold_row_keys,
    )
    assert actual == tr_ctx.remembered["row_keys"]


@then("both epochs have the same bundle_id")
def _both_same_bundle_id(tr_ctx: _TrainerCtx) -> None:
    first, second = tr_ctx.all_results[-2], tr_ctx.all_results[-1]
    assert first.bundle_id == second.bundle_id


@then("both epochs have the same hashes.model_sha256")
def _both_same_model_sha256(tr_ctx: _TrainerCtx) -> None:
    first, second = tr_ctx.all_results[-2], tr_ctx.all_results[-1]
    assert first.manifest["hashes"]["model_sha256"] == second.manifest["hashes"]["model_sha256"]


@then("both epochs have the same thresholds")
def _both_same_thresholds(tr_ctx: _TrainerCtx) -> None:
    first, second = tr_ctx.all_results[-2], tr_ctx.all_results[-1]
    assert (first.theta_low, first.theta_high) == (second.theta_low, second.theta_high)


@then("both epochs record a published_at UTC instant and a non-negative training_duration_seconds")
def _both_record_wall_time(tr_ctx: _TrainerCtx) -> None:
    for result in tr_ctx.all_results[-2:]:
        published_at = result.manifest["published_at"]
        assert published_at.endswith("Z")
        datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        assert result.manifest["training_duration_seconds"] >= 0.0


@then("the volatile fields are outside the bundle_id")
def _volatile_outside_bundle_id(tr_ctx: _TrainerCtx) -> None:
    assert tr_ctx.last is not None
    manifest = tr_ctx.last.manifest
    identity = {k: v for k, v in manifest.items() if k not in bundle_module._NON_IDENTITY_FIELDS}
    recomputed = hashlib.sha256(bundle_module._canonical_json(identity)).hexdigest()
    assert recomputed == tr_ctx.last.bundle_id


@then("the second training reports the bundle as reused")
def _second_reused(tr_ctx: _TrainerCtx) -> None:
    assert tr_ctx.last is not None
    assert tr_ctx.last.reused is True


@then("the published bundle's file bytes are unchanged")
def _registry_bytes_unchanged(tr_ctx: _TrainerCtx) -> None:
    assert _registry_bytes(tr_ctx.registry) == tr_ctx.remembered_registry_bytes
