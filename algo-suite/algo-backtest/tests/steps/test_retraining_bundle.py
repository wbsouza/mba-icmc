"""Steps for retraining_bundle.feature: immutable, content-addressed epoch bundles."""

from __future__ import annotations

import dataclasses
import hashlib
import json
import random
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from algo_backtest.chain.filters.f7_meta_learner import (
    FeatureFamily,
    TrainedMetaLearner,
    TrainingRow,
    WalkForwardSplit,
    train_meta_learner,
)
from algo_backtest.chain.filters.f7_model_io import BoosterFamilyModel, LogisticCombiner
from algo_backtest.retraining import bundle as bundle_module
from algo_backtest.retraining.bundle import (
    BundleDescription,
    LoadedBundle,
    PublishResult,
    list_bundles,
    load,
    publish,
)
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/retraining_bundle.feature")

_TWO_FAMILIES = (FeatureFamily.TREND, FeatureFamily.INDICATOR)
_PROBE_ROWS: tuple[dict[str, object], ...] = (
    {
        "trend_direction": 1.0,
        "trend_strength": 70.0,
        "higher_tf_trend_direction": 1.0,
        "rsi": 65.0,
        "macd_hist": 0.0002,
    },
    {
        "trend_direction": -1.0,
        "trend_strength": 25.0,
        "higher_tf_trend_direction": -1.0,
        "rsi": 32.0,
        "macd_hist": -0.0002,
    },
    {},
)


class _FakeClock:
    """A mutable wall clock the tests advance explicitly."""

    def __init__(self, start: datetime) -> None:
        self._now = start

    def __call__(self) -> datetime:
        return self._now

    def advance(self, delta: timedelta) -> None:
        self._now += delta


@dataclass
class _BundleCtx:
    """Per-scenario state: the registry, the model, the description and every observable."""

    registry: Path
    model: TrainedMetaLearner | None = None
    description: BundleDescription | None = None
    result: PublishResult | None = None
    loaded: LoadedBundle | None = None
    error: Exception | None = None
    remembered_model_bytes: bytes | None = None
    remembered_registry_bytes: dict[str, bytes] = field(default_factory=dict)
    results: list[PublishResult] = field(default_factory=list)
    clock: _FakeClock = field(default_factory=lambda: _FakeClock(datetime(2026, 1, 1, tzinfo=UTC)))


@pytest.fixture
def bundle_ctx(tmp_path: Path) -> _BundleCtx:
    """A fresh context with an empty (not-yet-created) registry directory."""
    return _BundleCtx(registry=tmp_path / "registry")


def _synthetic_rows(seed: int = 11) -> list[TrainingRow]:
    """72 seeded hourly rows whose label leans on trend, for a small trend+indicator fit."""
    rng = random.Random(seed)
    rows = []
    for i in range(72):
        direction = rng.choice([-1.0, 1.0])
        features: dict[str, object] = {
            "trend_direction": direction,
            "trend_strength": rng.uniform(20.0, 80.0),
            "higher_tf_trend_direction": rng.choice([-1.0, 0.0, 1.0]),
            "rsi": (65.0 if direction > 0 else 35.0) + rng.uniform(-5.0, 5.0),
            "macd_hist": direction * rng.uniform(0.0, 1e-4),
        }
        label = 1 if direction > 0 and rng.random() < 0.85 else (1 if rng.random() < 0.15 else 0)
        rows.append(
            TrainingRow(
                timestamp=datetime(2024, 1, 1, tzinfo=UTC) + timedelta(hours=i),
                features=features,
                label=label,
            )
        )
    return rows


def _default_spans() -> dict[str, dict[str, datetime]]:
    return {
        "family": {
            "start": datetime(2015, 3, 2, tzinfo=UTC),
            "end": datetime(2015, 12, 31, tzinfo=UTC),
        },
        "combiner": {
            "start": datetime(2015, 12, 31, tzinfo=UTC),
            "end": datetime(2016, 1, 30, tzinfo=UTC),
        },
        "threshold": {
            "start": datetime(2016, 1, 30, tzinfo=UTC),
            "end": datetime(2016, 2, 29, tzinfo=UTC),
        },
        "deployment": {
            "start": datetime(2016, 3, 1, tzinfo=UTC),
            "end": datetime(2016, 4, 1, tzinfo=UTC),
        },
    }


def _default_stages() -> dict[str, dict[str, object]]:
    return {
        "family": {
            "weighting": "uniform",
            "half_life_days": None,
            "rows": 1200,
            "per_class": {"0": 600, "1": 600},
            "n_eff": 1200.0,
            "raw_weight_min": 1.0,
            "raw_weight_max": 1.0,
        },
        "combiner": {
            "weighting": "uniform",
            "half_life_days": None,
            "rows": 150,
            "per_class": {"0": 75, "1": 75},
            "n_eff": 150.0,
            "raw_weight_min": 1.0,
            "raw_weight_max": 1.0,
        },
        "threshold": {"rows": 120},
    }


def _default_description(
    *, policy: str, theta_low: float, theta_high: float, activation_boundary: datetime
) -> BundleDescription:
    return BundleDescription(
        policy=policy,
        seed=42,
        spans=_default_spans(),
        activation_boundary=activation_boundary,
        ledger_watermark=datetime(2016, 2, 25, tzinfo=UTC),
        stages=_default_stages(),
        theta_low=theta_low,
        theta_high=theta_high,
        rows_sha256="a" * 64,
        data_sha256="b" * 64,
        config_sha256="c" * 64,
        protocol_sha256="d" * 64,
        training_duration_seconds=12.5,
    )


def _iso(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


# --- Given ---------------------------------------------------------------------------------


@given("a meta-learner trained on seeded synthetic rows with the trend and indicator families")
def _trained_model(bundle_ctx: _BundleCtx) -> None:
    rows = _synthetic_rows()
    split = WalkForwardSplit(
        train=tuple(rows[:48]), validation=tuple(rows[48:60]), test=tuple(rows[60:])
    )
    bundle_ctx.model = train_meta_learner(list(_TWO_FAMILIES), split)


@given("an empty bundle registry directory")
def _empty_registry(bundle_ctx: _BundleCtx) -> None:
    assert not bundle_ctx.registry.exists()


@given(
    parsers.re(
        r'^a bundle description for policy "(?P<policy>[A-Z])" with thresholds theta_low '
        r"(?P<theta_low>[\d.]+) and theta_high (?P<theta_high>[\d.]+) and activation boundary "
        r"(?P<boundary>\S+)$"
    )
)
def _bundle_description(
    bundle_ctx: _BundleCtx, policy: str, theta_low: str, theta_high: str, boundary: str
) -> None:
    bundle_ctx.description = _default_description(
        policy=policy,
        theta_low=float(theta_low),
        theta_high=float(theta_high),
        activation_boundary=_iso(boundary),
    )


def _do_publish(bundle_ctx: _BundleCtx) -> None:
    assert bundle_ctx.model is not None
    assert bundle_ctx.description is not None
    result = publish(
        bundle_ctx.model, bundle_ctx.description, bundle_ctx.registry, clock=bundle_ctx.clock
    )
    bundle_ctx.result = result
    bundle_ctx.results.append(result)


@given("the bundle is published")
@when("the bundle is published")
def _publish(bundle_ctx: _BundleCtx) -> None:
    _do_publish(bundle_ctx)


@given("the published bundle's file bytes are remembered")
@when("the published bundle's file bytes are remembered")
def _remember_bytes(bundle_ctx: _BundleCtx) -> None:
    assert bundle_ctx.result is not None
    bundle_ctx.remembered_model_bytes = bundle_ctx.result.model_path.read_bytes()
    bundle_ctx.remembered_registry_bytes = {
        str(path): path.read_bytes() for path in bundle_ctx.registry.rglob("*") if path.is_file()
    }


@given("the published model.json is overwritten on disk with different bytes")
def _overwrite_model(bundle_ctx: _BundleCtx) -> None:
    assert bundle_ctx.result is not None
    bundle_ctx.result.model_path.write_bytes(b'{"format": "corrupted", "different": true}')


@given("one byte of the published model.json is flipped on disk")
def _flip_byte(bundle_ctx: _BundleCtx) -> None:
    assert bundle_ctx.result is not None
    data = bytearray(bundle_ctx.result.model_path.read_bytes())
    data[0] ^= 0xFF
    bundle_ctx.result.model_path.write_bytes(bytes(data))


def _load_manifest(bundle_ctx: _BundleCtx) -> dict[str, Any]:
    assert bundle_ctx.result is not None
    return json.loads(bundle_ctx.result.manifest_path.read_text())


def _write_manifest(bundle_ctx: _BundleCtx, manifest: dict[str, Any]) -> None:
    assert bundle_ctx.result is not None
    bundle_ctx.result.manifest_path.write_text(json.dumps(manifest, indent=1, sort_keys=True))


@given(parsers.parse('the published manifest\'s policy field is edited on disk to "{value}"'))
def _edit_policy(bundle_ctx: _BundleCtx, value: str) -> None:
    manifest = _load_manifest(bundle_ctx)
    manifest["policy"] = value
    _write_manifest(bundle_ctx, manifest)


@given(parsers.parse("the published manifest's schema_version is edited on disk to {value:d}"))
def _edit_schema_version(bundle_ctx: _BundleCtx, value: int) -> None:
    manifest = _load_manifest(bundle_ctx)
    manifest["schema_version"] = value
    _write_manifest(bundle_ctx, manifest)


@given(parsers.parse('the published manifest\'s field "{field}" is removed on disk'))
def _remove_field(bundle_ctx: _BundleCtx, field: str) -> None:
    manifest = _load_manifest(bundle_ctx)
    node = manifest
    parts = field.split(".")
    for part in parts[:-1]:
        node = node[part]
    del node[parts[-1]]
    _write_manifest(bundle_ctx, manifest)


@given(
    parsers.parse(
        'the published manifest\'s families are edited on disk to "{families}" with the '
        "bundle_id recomputed"
    )
)
def _edit_families(bundle_ctx: _BundleCtx, families: str) -> None:
    manifest = _load_manifest(bundle_ctx)
    manifest["families"] = [name.strip() for name in families.split(",")]
    identity = {k: v for k, v in manifest.items() if k not in bundle_module._NON_IDENTITY_FIELDS}
    manifest["bundle_id"] = hashlib.sha256(bundle_module._canonical_json(identity)).hexdigest()
    _write_manifest(bundle_ctx, manifest)


@given("the atomic rename of the staged bundle is made to fail")
def _break_rename(bundle_ctx: _BundleCtx, monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(src: Path, dst: Path) -> None:
        raise OSError("injected rename failure")

    monkeypatch.setattr(bundle_module, "_rename", _raise)


@given("the staged model.json is corrupted before validation")
def _corrupt_staged_model(bundle_ctx: _BundleCtx, monkeypatch: pytest.MonkeyPatch) -> None:
    def _write_garbage(path: Path, data: bytes) -> None:
        path.write_bytes(b"not valid json at all")

    monkeypatch.setattr(bundle_module, "_write_model_file", _write_garbage)


@given("a leftover staging directory in the registry")
def _leftover_staging(bundle_ctx: _BundleCtx) -> None:
    bundle_ctx.registry.mkdir(parents=True, exist_ok=True)
    (bundle_ctx.registry / f".staging-{'0' * 64}-leftover").mkdir()


# --- When ------------------------------------------------------------------------------------


@when("the bundle is loaded from the registry by its id")
@then("the bundle is loaded from the registry by its id")
def _load_by_id(bundle_ctx: _BundleCtx) -> None:
    assert bundle_ctx.result is not None
    bundle_ctx.loaded = load(bundle_ctx.registry, bundle_ctx.result.bundle_id)


@when(parsers.parse('loading the bundle "{bundle_id}" from the registry fails'))
def _load_missing_fails(bundle_ctx: _BundleCtx, bundle_id: str) -> None:
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011
        load(bundle_ctx.registry, bundle_id)
    bundle_ctx.error = exc_info.value


@when("loading the published bundle fails")
def _load_published_fails(bundle_ctx: _BundleCtx) -> None:
    assert bundle_ctx.result is not None
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011
        load(bundle_ctx.registry, bundle_ctx.result.bundle_id)
    bundle_ctx.error = exc_info.value


@when(parsers.parse('loading the published bundle for the strategy families "{families}" fails'))
def _load_wrong_strategy_fails(bundle_ctx: _BundleCtx, families: str) -> None:
    assert bundle_ctx.result is not None
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011
        load(
            bundle_ctx.registry,
            bundle_ctx.result.bundle_id,
            strategy_families=[name.strip() for name in families.split(",")],
        )
    bundle_ctx.error = exc_info.value


@when("publishing the bundle fails")
def _publish_fails(bundle_ctx: _BundleCtx) -> None:
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011
        _do_publish(bundle_ctx)
    bundle_ctx.error = exc_info.value


@when("publishing the same bundle description fails")
def _republish_fails(bundle_ctx: _BundleCtx) -> None:
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011
        _do_publish(bundle_ctx)
    bundle_ctx.error = exc_info.value


@when("the same bundle description is published again 1 hour of wall time later")
def _republish_later(bundle_ctx: _BundleCtx) -> None:
    bundle_ctx.clock.advance(timedelta(hours=1))
    _do_publish(bundle_ctx)


@when(parsers.parse('the same bundle description is published again for policy "{policy}"'))
def _republish_other_policy(bundle_ctx: _BundleCtx, policy: str) -> None:
    assert bundle_ctx.description is not None
    bundle_ctx.description = dataclasses.replace(bundle_ctx.description, policy=policy)
    _do_publish(bundle_ctx)


@when("the atomic rename works again and the bundle is published")
def _retry_publish(bundle_ctx: _BundleCtx, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bundle_module, "_rename", bundle_module.os.replace)
    _do_publish(bundle_ctx)


# --- Then ----------------------------------------------------------------------------------


@then("the loaded model's p_hat matches the published model's on every probe row")
def _predictions_match(bundle_ctx: _BundleCtx) -> None:
    assert bundle_ctx.loaded is not None
    assert bundle_ctx.model is not None
    for probe in _PROBE_ROWS:
        assert bundle_ctx.loaded.model.predict(probe) == bundle_ctx.model.predict(probe)


@then(
    parsers.parse("the loaded thresholds are theta_low {theta_low:g} and theta_high {theta_high:g}")
)
def _loaded_thresholds(bundle_ctx: _BundleCtx, theta_low: float, theta_high: float) -> None:
    assert bundle_ctx.loaded is not None
    assert bundle_ctx.loaded.theta_low == theta_low
    assert bundle_ctx.loaded.theta_high == theta_high


@then(parsers.parse('the loaded families are "{families}" in that order'))
def _loaded_families(bundle_ctx: _BundleCtx, families: str) -> None:
    assert bundle_ctx.loaded is not None
    expected = [name.strip() for name in families.split(",")]
    assert [family.value for family in bundle_ctx.loaded.model.families] == expected


@then("the loaded model carries no scikit-learn or pickled object")
def _no_sklearn_object(bundle_ctx: _BundleCtx) -> None:
    assert bundle_ctx.loaded is not None
    assert isinstance(bundle_ctx.loaded.model.meta_model, LogisticCombiner)
    for model in bundle_ctx.loaded.model.family_models.values():
        assert isinstance(model, BoosterFamilyModel)


@then(parsers.parse("the registry lists {count:d} published bundle"))
@then(parsers.parse("the registry lists {count:d} published bundles"))
def _registry_lists(bundle_ctx: _BundleCtx, count: int) -> None:
    assert len(list_bundles(bundle_ctx.registry)) == count


@then("the published manifest contains every required field")
def _manifest_has_fields(bundle_ctx: _BundleCtx, datatable: list[list[str]]) -> None:
    assert bundle_ctx.result is not None
    manifest = bundle_ctx.result.manifest
    header, *rows = datatable
    for (field_name,) in rows:
        node: Any = manifest
        for part in field_name.split("."):
            assert isinstance(node, dict) and part in node, f"missing field {field_name!r}"
            node = node[part]
        assert node is not None, f"field {field_name!r} is null"


@then(parsers.parse("the manifest's schema_version is {value:d}"))
def _manifest_schema_version(bundle_ctx: _BundleCtx, value: int) -> None:
    assert bundle_ctx.result is not None
    assert bundle_ctx.result.manifest["schema_version"] == value


@then(parsers.parse('the manifest\'s policy is "{value}"'))
def _manifest_policy(bundle_ctx: _BundleCtx, value: str) -> None:
    assert bundle_ctx.result is not None
    assert bundle_ctx.result.manifest["policy"] == value


@then(parsers.parse("the manifest's seed is {value:d}"))
def _manifest_seed(bundle_ctx: _BundleCtx, value: int) -> None:
    assert bundle_ctx.result is not None
    assert bundle_ctx.result.manifest["seed"] == value


@then(parsers.parse("the manifest's activation_boundary is {value}"))
def _manifest_activation_boundary(bundle_ctx: _BundleCtx, value: str) -> None:
    assert bundle_ctx.result is not None
    assert bundle_ctx.result.manifest["activation_boundary"] == value


@then("the manifest's published_at is a UTC instant with a Z suffix")
def _manifest_published_at(bundle_ctx: _BundleCtx) -> None:
    assert bundle_ctx.result is not None
    published_at = bundle_ctx.result.manifest["published_at"]
    assert published_at.endswith("Z")
    datetime.fromisoformat(published_at.replace("Z", "+00:00"))


@then("the manifest's runtime names the installed lightgbm, scikit-learn and numpy versions")
def _manifest_runtime(bundle_ctx: _BundleCtx) -> None:
    import lightgbm
    import numpy
    import sklearn

    assert bundle_ctx.result is not None
    runtime = bundle_ctx.result.manifest["runtime"]
    assert runtime["lightgbm"] == lightgbm.__version__
    assert runtime["scikit-learn"] == sklearn.__version__
    assert runtime["numpy"] == numpy.__version__


@then("the manifest's hashes.model_sha256 equals the sha256 of the published model.json bytes")
def _model_sha256_matches(bundle_ctx: _BundleCtx) -> None:
    assert bundle_ctx.result is not None
    actual = hashlib.sha256(bundle_ctx.result.model_path.read_bytes()).hexdigest()
    assert bundle_ctx.result.manifest["hashes"]["model_sha256"] == actual


@then(
    "the manifest's bundle_id equals the sha256 of the canonical manifest without its "
    "volatile fields"
)
def _bundle_id_matches(bundle_ctx: _BundleCtx) -> None:
    assert bundle_ctx.result is not None
    manifest = bundle_ctx.result.manifest
    identity = {k: v for k, v in manifest.items() if k not in bundle_module._NON_IDENTITY_FIELDS}
    expected = hashlib.sha256(bundle_module._canonical_json(identity)).hexdigest()
    assert manifest["bundle_id"] == expected


@then("the published bundle directory is named after the bundle_id")
def _directory_named_after_id(bundle_ctx: _BundleCtx) -> None:
    assert bundle_ctx.result is not None
    assert bundle_ctx.result.model_path.parent.name == bundle_ctx.result.bundle_id


@then("the second publication reports the bundle as reused")
def _second_reused(bundle_ctx: _BundleCtx) -> None:
    assert bundle_ctx.result is not None
    assert bundle_ctx.result.reused is True


@then("both publications have the same bundle_id")
def _same_bundle_id(bundle_ctx: _BundleCtx) -> None:
    first, second = bundle_ctx.results[-2], bundle_ctx.results[-1]
    assert first.bundle_id == second.bundle_id


@then("the published bundle's file bytes are unchanged")
def _bytes_unchanged(bundle_ctx: _BundleCtx) -> None:
    current = {
        str(path): path.read_bytes() for path in bundle_ctx.registry.rglob("*") if path.is_file()
    }
    assert current == bundle_ctx.remembered_registry_bytes


@then(parsers.parse('the bundle failure names "{fragment}"'))
def _failure_names(bundle_ctx: _BundleCtx, fragment: str) -> None:
    assert bundle_ctx.error is not None
    assert fragment in str(bundle_ctx.error)


@then("the bundle failure names the bundle_id")
def _failure_names_bundle_id(bundle_ctx: _BundleCtx) -> None:
    assert bundle_ctx.error is not None
    assert bundle_ctx.result is not None
    assert bundle_ctx.result.bundle_id in str(bundle_ctx.error)


@then("the two bundles have different bundle_ids")
def _different_bundle_ids(bundle_ctx: _BundleCtx) -> None:
    first, second = bundle_ctx.results[-2], bundle_ctx.results[-1]
    assert first.bundle_id != second.bundle_id


@then("the two bundles have the same hashes.model_sha256")
def _same_model_sha256(bundle_ctx: _BundleCtx) -> None:
    first, second = bundle_ctx.results[-2], bundle_ctx.results[-1]
    assert first.manifest["hashes"]["model_sha256"] == second.manifest["hashes"]["model_sha256"]


@then("no manifest.json exists in the registry outside a staging directory")
def _no_published_manifest(bundle_ctx: _BundleCtx) -> None:
    for path in bundle_ctx.registry.rglob("manifest.json"):
        assert path.parent.name.startswith(".staging-"), f"unexpected published manifest {path}"


@then(parsers.parse('loading the bundle by its would-be id fails naming "{fragment}"'))
def _load_would_be_id_fails(bundle_ctx: _BundleCtx, fragment: str) -> None:
    assert bundle_ctx.model is not None
    assert bundle_ctx.description is not None
    model_bytes = bundle_module._model_document_bytes(bundle_ctx.model)
    model_sha256 = hashlib.sha256(model_bytes).hexdigest()
    identity = bundle_module._identity_manifest(
        bundle_ctx.model, bundle_ctx.description, model_sha256
    )
    would_be_id = hashlib.sha256(bundle_module._canonical_json(identity)).hexdigest()
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011
        load(bundle_ctx.registry, would_be_id)
    assert fragment in str(exc_info.value)


@then("the leftover staging directory is not the listed bundle")
def _leftover_not_listed(bundle_ctx: _BundleCtx) -> None:
    listed = list_bundles(bundle_ctx.registry)
    assert all(not name.startswith(".staging-") for name in listed)
    assert f"{'0' * 64}-leftover" not in listed
