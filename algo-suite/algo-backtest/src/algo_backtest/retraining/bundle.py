"""Immutable epoch bundles (Story 19, T7; RWT-11, RWT-15).

One epoch bundle wraps one portable F7 model document (`f7_model_io`, pickle-free) in a
validated, content-addressed, immutable artifact with its complete provenance:

    <registry>/<bundle_id>/manifest.json     the manifest (provenance + identity)
    <registry>/<bundle_id>/model.json        the f7_model_io document

`hashes.model_sha256` is the sha256 of `model.json`'s bytes: the semantic model payload
hash (RWT-30), computed with an empty `f7_model_io` provenance so it depends only on the
fitted booster/coefficients, never on which policy or thresholds a bundle records. `bundle_id`
is the sha256 of the canonical JSON (sorted keys, no whitespace) of every manifest field
except the volatile ones (`published_at`, `training_duration_seconds`, `host`); two
publications of identical content at different wall times share a `bundle_id`. Publication
stages the manifest and model into `.staging-<bundle_id>-<nonce>` inside the registry,
validates the staged bytes there (the model is reloaded and must reproduce the in-memory
model's p_hat on a set of probe feature rows; the checksum is recomputed), then renames the
staging directory to `<bundle_id>` in one atomic rename. Anything that fails before the
rename leaves no published bundle. Publishing content that is already published returns the
existing artifact untouched (identical reuse); an identity that exists on disk with
different model bytes is a conflict, left as found, never repaired (RWT-15).
"""

from __future__ import annotations

import hashlib
import json
import os
import socket
import sys
import tempfile
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import lightgbm
import numpy
import sklearn

from algo_backtest.chain.filters import f7_model_io
from algo_backtest.chain.filters.f7_meta_learner import TrainedMetaLearner
from algo_backtest.retraining.utc import iso_utc

_MODULE = "retraining.bundle"
_MANIFEST_FILE = "manifest.json"
_MODEL_FILE = "model.json"
_SCHEMA_VERSION = 1

_VOLATILE_FIELDS = frozenset({"published_at", "training_duration_seconds", "host"})
_NON_IDENTITY_FIELDS = frozenset({"bundle_id"}) | _VOLATILE_FIELDS

_REQUIRED_FIELDS = (
    "schema_version",
    "bundle_id",
    "policy",
    "seed",
    "families",
    "spans.family",
    "spans.combiner",
    "spans.threshold",
    "spans.deployment",
    "activation_boundary",
    "ledger_watermark",
    "stages.family",
    "stages.combiner",
    "stages.threshold",
    "thresholds",
    "hashes.model_sha256",
    "hashes.rows_sha256",
    "hashes.data_sha256",
    "hashes.config_sha256",
    "hashes.protocol_sha256",
    "runtime",
    "published_at",
    "training_duration_seconds",
    "host",
)

_PROBE_FEATURES: tuple[Mapping[str, object], ...] = (
    {
        "trend_direction": 1.0,
        "trend_strength": 62.0,
        "higher_tf_trend_direction": 1.0,
        "rsi": 58.0,
        "macd_hist": 0.00015,
        "candlestick_pattern": "hammer",
        "news_event_intensity": 0.4,
        "news_sentiment_score": 0.15,
    },
    {
        "trend_direction": -1.0,
        "trend_strength": 28.0,
        "higher_tf_trend_direction": -1.0,
        "rsi": 34.0,
        "macd_hist": -0.00012,
        "candlestick_pattern": "shooting_star",
        "news_event_intensity": 0.2,
        "news_sentiment_score": -0.25,
    },
    {},
)

_MISSING = object()


@dataclass(frozen=True)
class BundleDescription:
    """Every identity-bearing manifest field the caller supplies (`publish` fills in the
    semantic model payload hash, `bundle_id`, and the volatile wall-clock fields).

    `spans` carries one `{"start": datetime, "end": datetime}` mapping per key `family`,
    `combiner`, `threshold`, `deployment`. `stages` carries one provenance mapping per key
    `family`, `combiner`, `threshold` (design.md "EpochBundle": weighting, half_life_days,
    rows, per_class, n_eff, raw_weight_min, raw_weight_max for family/combiner; rows only
    for threshold) — passed through verbatim, this module does not interpret its contents.
    """

    policy: str
    seed: int
    spans: Mapping[str, Mapping[str, datetime]]
    activation_boundary: datetime
    ledger_watermark: datetime
    stages: Mapping[str, Mapping[str, object]]
    theta_low: float
    theta_high: float
    rows_sha256: str
    data_sha256: str
    config_sha256: str
    protocol_sha256: str
    training_duration_seconds: float


@dataclass(frozen=True)
class PublishResult:
    """The outcome of one `publish` call: its identity, whether it was newly written, and
    where its files live."""

    bundle_id: str
    reused: bool
    manifest: Mapping[str, Any]
    model_path: Path
    manifest_path: Path


@dataclass(frozen=True)
class LoadedBundle:
    """A validated, reloaded bundle: the rebuilt model plus its manifest and thresholds."""

    model: TrainedMetaLearner
    manifest: Mapping[str, Any]
    theta_low: float
    theta_high: float


def _canonical_json(obj: object) -> bytes:
    """Sorted-key, whitespace-free JSON bytes: the manifest's content-addressing form."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _pretty_json(obj: object) -> bytes:
    """Human-readable JSON bytes for the files written to disk."""
    return (json.dumps(obj, indent=1, sort_keys=True) + "\n").encode("utf-8")


def _runtime_versions() -> dict[str, str]:
    """The installed library versions the model was fitted and bundled with."""
    version = sys.version_info
    return {
        "python": f"{version.major}.{version.minor}.{version.micro}",
        "lightgbm": lightgbm.__version__,
        "scikit-learn": sklearn.__version__,
        "numpy": numpy.__version__,
    }


def _model_document_bytes(model: TrainedMetaLearner) -> bytes:
    """The `f7_model_io` document's bytes for `model`, with empty provenance so the bytes
    (and their sha256, RWT-30's semantic payload hash) depend only on the fitted model."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / _MODEL_FILE
        f7_model_io.dump_model(model, path, {})
        return path.read_bytes()


def _identity_manifest(
    model: TrainedMetaLearner, description: BundleDescription, model_sha256: str
) -> dict[str, Any]:
    """Every identity-bearing manifest field, ready for canonical-JSON hashing or writing."""
    return {
        "schema_version": _SCHEMA_VERSION,
        "policy": description.policy,
        "seed": description.seed,
        "families": [family.value for family in model.families],
        "spans": {
            name: {"start": iso_utc(bounds["start"]), "end": iso_utc(bounds["end"])}
            for name, bounds in description.spans.items()
        },
        "activation_boundary": iso_utc(description.activation_boundary),
        "ledger_watermark": iso_utc(description.ledger_watermark),
        "stages": {name: dict(stage) for name, stage in description.stages.items()},
        "thresholds": {"theta_low": description.theta_low, "theta_high": description.theta_high},
        "hashes": {
            "model_sha256": model_sha256,
            "rows_sha256": description.rows_sha256,
            "data_sha256": description.data_sha256,
            "config_sha256": description.config_sha256,
            "protocol_sha256": description.protocol_sha256,
        },
        "runtime": _runtime_versions(),
    }


def _write_model_file(path: Path, data: bytes) -> None:
    """Write the staged `model.json` bytes; a seam tests patch to inject staged corruption."""
    path.write_bytes(data)


def _write_manifest_file(path: Path, data: bytes) -> None:
    """Write the staged `manifest.json` bytes."""
    path.write_bytes(data)


def _rename(src: Path, dst: Path) -> None:
    """Atomically publish staged content; a seam tests patch to inject rename failures."""
    os.replace(src, dst)


def _validate_staged(staging_dir: Path, model: TrainedMetaLearner, bundle_id: str) -> None:
    """Reload the staged model and confirm it reproduces `model`'s predictions and checksum.

    Raises:
        ValueError: naming "validat" and `bundle_id`, wrapping whatever underlying failure
            (bad JSON, missing keys, a checksum or prediction mismatch) caused it.
    """
    model_path = staging_dir / _MODEL_FILE
    try:
        reloaded = f7_model_io.load_model(model_path)
        actual_sha256 = hashlib.sha256(model_path.read_bytes()).hexdigest()
        manifest = json.loads((staging_dir / _MANIFEST_FILE).read_text())
        expected_sha256 = manifest["hashes"]["model_sha256"]
        if actual_sha256 != expected_sha256:
            raise ValueError(
                f"recomputed model.json sha256 {actual_sha256} does not match the staged "
                f"manifest's {expected_sha256}"
            )
        for probe in _PROBE_FEATURES:
            if reloaded.predict(probe) != model.predict(probe):
                raise ValueError(
                    "the reloaded model does not reproduce the in-memory model's p_hat on a "
                    "probe row"
                )
    except Exception as exc:
        raise ValueError(
            f"{_MODULE}: staged bundle {bundle_id} failed validation ({exc}); nothing is published"
        ) from exc


def _reuse_or_conflict(final_dir: Path, bundle_id: str, model_bytes: bytes) -> PublishResult:
    """The existing bundle at `bundle_id`, if its model bytes match; a conflict otherwise."""
    manifest: dict[str, Any] = json.loads((final_dir / _MANIFEST_FILE).read_text())
    on_disk_model_bytes = (final_dir / _MODEL_FILE).read_bytes()
    if on_disk_model_bytes != model_bytes:
        raise ValueError(
            f"{_MODULE}: bundle {bundle_id} is a conflict: the registry already holds "
            "different model bytes under this identity; a colliding bundle_id is left "
            "untouched, never repaired"
        )
    return PublishResult(
        bundle_id=bundle_id,
        reused=True,
        manifest=manifest,
        model_path=final_dir / _MODEL_FILE,
        manifest_path=final_dir / _MANIFEST_FILE,
    )


def _default_clock() -> datetime:
    """The real wall-clock UTC instant."""
    return datetime.now(UTC)


def publish(
    model: TrainedMetaLearner,
    description: BundleDescription,
    registry: Path,
    *,
    clock: Callable[[], datetime] = _default_clock,
    host: str | None = None,
) -> PublishResult:
    """Publish `model` plus `description` as one immutable, content-addressed bundle.

    Raises:
        ValueError: `description.theta_low` is not strictly below `theta_high`; the
            registry already holds this identity with different model bytes (conflict);
            the staged content fails validation; or the atomic rename fails.
    """
    if description.theta_low >= description.theta_high:
        raise ValueError(
            f"{_MODULE}: theta_low {description.theta_low} must be strictly below "
            f"theta_high {description.theta_high}; F7's HOLD band cannot be empty"
        )
    registry.mkdir(parents=True, exist_ok=True)
    model_bytes = _model_document_bytes(model)
    model_sha256 = hashlib.sha256(model_bytes).hexdigest()
    identity = _identity_manifest(model, description, model_sha256)
    bundle_id = hashlib.sha256(_canonical_json(identity)).hexdigest()
    final_dir = registry / bundle_id
    if final_dir.exists():
        return _reuse_or_conflict(final_dir, bundle_id, model_bytes)

    staging_dir = registry / f".staging-{bundle_id}-{uuid.uuid4().hex}"
    staging_dir.mkdir()
    _write_model_file(staging_dir / _MODEL_FILE, model_bytes)
    manifest = dict(identity)
    manifest["bundle_id"] = bundle_id
    manifest["published_at"] = iso_utc(clock())
    manifest["training_duration_seconds"] = description.training_duration_seconds
    manifest["host"] = host if host is not None else socket.gethostname()
    _write_manifest_file(staging_dir / _MANIFEST_FILE, _pretty_json(manifest))

    _validate_staged(staging_dir, model, bundle_id)
    try:
        _rename(staging_dir, final_dir)
    except OSError as exc:
        raise ValueError(
            f"{_MODULE}: atomic rename of staged bundle {bundle_id} into the registry "
            f"failed ({exc}); nothing is published, retry when the failure clears"
        ) from exc
    return PublishResult(
        bundle_id=bundle_id,
        reused=False,
        manifest=manifest,
        model_path=final_dir / _MODEL_FILE,
        manifest_path=final_dir / _MANIFEST_FILE,
    )


def _get_dotted(payload: Mapping[str, Any], dotted: str) -> Any:
    """The value at a dotted path (`"spans.family"`) inside a nested mapping, or `_MISSING`."""
    node: Any = payload
    for part in dotted.split("."):
        if not isinstance(node, Mapping) or part not in node:
            return _MISSING
        node = node[part]
    return node


def _require_schema_version(manifest: Mapping[str, Any], bundle_id: str) -> None:
    """Reject a manifest schema version this module does not know how to read."""
    version = manifest.get("schema_version")
    if version != _SCHEMA_VERSION:
        raise ValueError(
            f"{_MODULE}: bundle {bundle_id} has schema_version {version!r}, expected "
            f"{_SCHEMA_VERSION}; load it with a compatible version of retraining.bundle"
        )


def _require_fields(manifest: Mapping[str, Any], bundle_id: str) -> None:
    """Reject a manifest missing any required (non-null) field, naming the field."""
    for field in _REQUIRED_FIELDS:
        value = _get_dotted(manifest, field)
        if value is _MISSING or value is None:
            raise ValueError(
                f"{_MODULE}: bundle {bundle_id} manifest is missing required field "
                f"{field!r}; every manifest field must be present and non-null"
            )


def list_bundles(registry: Path) -> tuple[str, ...]:
    """The ids of every published bundle in `registry`; staging directories are never listed."""
    if not registry.exists():
        return ()
    return tuple(
        sorted(
            entry.name
            for entry in registry.iterdir()
            if entry.is_dir()
            and not entry.name.startswith(".staging-")
            and (entry / _MANIFEST_FILE).exists()
        )
    )


def load(
    registry: Path, bundle_id: str, *, strategy_families: Sequence[str] | None = None
) -> LoadedBundle:
    """Load and validate the bundle `bundle_id` from `registry` (RWT-15).

    Raises:
        ValueError: the id is not a published bundle ("missing"); the manifest's
            `schema_version` is unsupported; a required manifest field is absent; the
            model.json bytes do not match `hashes.model_sha256` ("sha256"); the manifest's
            content does not hash to its own `bundle_id` ("bundle_id"); the manifest's
            `families` disagree with the model document's own families ("families"); or
            `strategy_families` is given and does not match the model's families.
    """
    final_dir = registry / bundle_id
    manifest_path = final_dir / _MANIFEST_FILE
    if not manifest_path.exists():
        raise ValueError(
            f"{_MODULE}: bundle {bundle_id!r} is missing from registry {registry}; no "
            "bundle with this id was published"
        )
    manifest: dict[str, Any] = json.loads(manifest_path.read_text())
    _require_schema_version(manifest, bundle_id)
    _require_fields(manifest, bundle_id)

    model_path = final_dir / _MODEL_FILE
    model_bytes = model_path.read_bytes()
    actual_sha256 = hashlib.sha256(model_bytes).hexdigest()
    expected_sha256 = manifest["hashes"]["model_sha256"]
    if actual_sha256 != expected_sha256:
        raise ValueError(
            f"{_MODULE}: bundle {bundle_id} model.json sha256 mismatch: manifest records "
            f"{expected_sha256}, computed {actual_sha256}; the file is corrupt"
        )

    identity = {k: v for k, v in manifest.items() if k not in _NON_IDENTITY_FIELDS}
    recomputed_id = hashlib.sha256(_canonical_json(identity)).hexdigest()
    if recomputed_id != manifest["bundle_id"]:
        raise ValueError(
            f"{_MODULE}: bundle {bundle_id} manifest content hashes to {recomputed_id}, but "
            f"its recorded bundle_id is {manifest['bundle_id']}; the manifest was tampered with"
        )

    model = f7_model_io.load_model(model_path)
    manifest_families = sorted(manifest["families"])
    model_families = sorted(family.value for family in model.families)
    if manifest_families != model_families:
        raise ValueError(
            f"{_MODULE}: bundle {bundle_id} manifest families {manifest_families} disagree "
            f"with the model document's families {model_families}; the bundle is incompatible"
        )
    if strategy_families is not None:
        f7_model_io.require_families(model.families, strategy_families, where=f"bundle {bundle_id}")

    thresholds = manifest["thresholds"]
    return LoadedBundle(
        model=model,
        manifest=manifest,
        theta_low=float(thresholds["theta_low"]),
        theta_high=float(thresholds["theta_high"]),
    )
