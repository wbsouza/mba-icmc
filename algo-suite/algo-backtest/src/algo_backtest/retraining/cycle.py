"""The full adaptive-cycle coordinator (Story 19, T10; RWT-23, RWT-25, RWT-26, RWT-27).

Runs the registered consume -> mature -> fit -> validate -> publish state machine exactly
once per policy and boundary (RWT-25), checkpointing each completed stage so a retry
resumes without refitting, recording every failed attempt with its failed stage (RWT-27),
and never advancing anything a failed stage did not validate (RWT-23, RWT-26).

A `CycleRequest` carries: policy, protocol_hash, cutoff (C), activation_boundary (D),
source_watermark (the ledger watermark the requester built the request against, `None`
for an empty ledger), prior_bundle_id (the previously active bundle, `None` for the first
epoch), the source batches to consume, the training settings and the feature source. The
`cycle_id` is the sha256 of the canonical JSON of (policy, protocol_hash, cutoff,
activation_boundary, source_watermark, prior_bundle_id): content-addressed by the
immutable inputs and the policy — never by the batches, settings or features, which are
operational inputs, not identity.

On-disk records under the coordinator's directory:

    cycles/<cycle_id>/record.json     status, attempts (each with started/finished wall
                                       time, outcome, failed_stage, reason), completed
                                       stages, and the bundle_id once published
    cycles/<cycle_id>/checkpoints/    one directory per completed stage: consume/,
                                       mature/ (mature/pending keys), fit/ (the staged
                                       model document + description), validate/ (the
                                       staged bundle reference), publish/ (the bundle_id)

Request handling order: (1) an existing successful record for this cycle_id returns its
outcome without running any stage; (2) a successful record for the same policy and
boundary under a different cycle_id is a conflict (the boundary already ran); (3) the
activation boundary must be a registered, future-only UTC month start; (4) the ledger
watermark must equal source_watermark, else the request is rejected at stage "consume"
(watermark conflict); (5) stages run in order, each resumed from its checkpoint when one
exists. The registered timeout is a wall-clock budget for one attempt, measured on an
injectable clock and checked both on entering and on completing each stage; an attempt
over budget is recorded as failed with reason "timeout" at the stage that was running. A
failed attempt raises to the caller after being recorded; replay must stop, it never
falls back to another bundle.

The request/response exchange here is in-process; the native LEAN transport around it is
T12's.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from algo_backtest.chain.filters import f7_model_io
from algo_backtest.retraining import bundle as bundle_module
from algo_backtest.retraining.bundle import BundleDescription, StagedBundle
from algo_backtest.retraining.ingestion import Batch, Ledger, consume
from algo_backtest.retraining.schedule import Epoch, epoch_starting
from algo_backtest.retraining.trainer import TrainingSettings, prepare_epoch
from algo_backtest.retraining.utc import iso_utc

_MODULE = "retraining.cycle"
_RECORD_FILE = "record.json"


def _default_clock() -> datetime:
    """The real wall-clock UTC instant."""
    return datetime.now(UTC)


def _canonical_json(obj: object) -> bytes:
    """Sorted-key, whitespace-free JSON bytes."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _parse_iso(text: str) -> datetime:
    """The inverse of `iso_utc`."""
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def _is_month_start(value: datetime) -> bool:
    """Whether `value` is exactly 00:00:00 on the first day of a month."""
    return value == value.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _watermark_after(request: CycleRequest) -> datetime | None:
    """The ledger watermark that consuming exactly `request.batches` on top of
    `source_watermark` would produce — tolerating an independent cycle (a different
    policy at the same boundary) that replays the same, already-consumed batches; a
    genuinely stale `source_watermark` (RWT-23) still fails since it matches neither
    this nor the pre-consumption value."""
    watermark = request.source_watermark
    for batch in request.batches:
        for row in batch.rows:
            if watermark is None or row.available_at > watermark:
                watermark = row.available_at
    return watermark


@dataclass(frozen=True)
class CycleRequest:
    """One requested retraining cycle. `batches`, `settings` and `features` are
    operational inputs; only `policy`, `protocol_hash`, `cutoff`, `activation_boundary`,
    `source_watermark` and `prior_bundle_id` make up its content-addressed `cycle_id`."""

    policy: str
    protocol_hash: str
    cutoff: datetime
    activation_boundary: datetime
    source_watermark: datetime | None
    prior_bundle_id: str | None
    batches: tuple[Batch, ...]
    settings: TrainingSettings
    features: Mapping[str, Mapping[str, object]]


@dataclass(frozen=True)
class CycleResponse:
    """One successfully handled cycle's outcome."""

    status: str
    bundle_id: str
    activation_boundary: datetime


class _StageFailure(Exception):
    """One stage's failure, carrying the stage name for the attempt record."""

    def __init__(self, stage: str, message: str) -> None:
        super().__init__(message)
        self.stage = stage


def _cycle_id(request: CycleRequest) -> str:
    """sha256 of the canonical JSON of the request's identity fields."""
    payload = {
        "policy": request.policy,
        "protocol_hash": request.protocol_hash,
        "cutoff": iso_utc(request.cutoff),
        "activation_boundary": iso_utc(request.activation_boundary),
        "source_watermark": (
            None if request.source_watermark is None else iso_utc(request.source_watermark)
        ),
        "prior_bundle_id": request.prior_bundle_id,
    }
    return hashlib.sha256(_canonical_json(payload)).hexdigest()


def _serialize_description(description: BundleDescription) -> dict[str, Any]:
    """`description` as a JSON-ready dict (the "fit" checkpoint's provenance)."""
    return {
        "policy": description.policy,
        "seed": description.seed,
        "spans": {
            name: {"start": iso_utc(bounds["start"]), "end": iso_utc(bounds["end"])}
            for name, bounds in description.spans.items()
        },
        "activation_boundary": iso_utc(description.activation_boundary),
        "ledger_watermark": iso_utc(description.ledger_watermark),
        "stages": {name: dict(stage) for name, stage in description.stages.items()},
        "theta_low": description.theta_low,
        "theta_high": description.theta_high,
        "rows_sha256": description.rows_sha256,
        "data_sha256": description.data_sha256,
        "config_sha256": description.config_sha256,
        "protocol_sha256": description.protocol_sha256,
        "training_duration_seconds": description.training_duration_seconds,
    }


def _deserialize_description(payload: Mapping[str, Any]) -> BundleDescription:
    """The inverse of `_serialize_description`."""
    return BundleDescription(
        policy=payload["policy"],
        seed=payload["seed"],
        spans={
            name: {"start": _parse_iso(bounds["start"]), "end": _parse_iso(bounds["end"])}
            for name, bounds in payload["spans"].items()
        },
        activation_boundary=_parse_iso(payload["activation_boundary"]),
        ledger_watermark=_parse_iso(payload["ledger_watermark"]),
        stages=payload["stages"],
        theta_low=payload["theta_low"],
        theta_high=payload["theta_high"],
        rows_sha256=payload["rows_sha256"],
        data_sha256=payload["data_sha256"],
        config_sha256=payload["config_sha256"],
        protocol_sha256=payload["protocol_sha256"],
        training_duration_seconds=payload["training_duration_seconds"],
    )


class Coordinator:
    """One coordinator directory's consume -> mature -> fit -> validate -> publish
    state machine, registered against a fixed monthly `schedule` and timeout budget."""

    def __init__(
        self,
        directory: Path,
        epochs: Sequence[Epoch],
        *,
        timeout_seconds: float,
        clock: Callable[[], datetime] = _default_clock,
    ) -> None:
        self._directory = directory
        self._registry = directory / "registry"
        self._ledger_dir = directory / "ledger"
        self._cycles_dir = directory / "cycles"
        self._epochs = tuple(epochs)
        self._timeout_seconds = timeout_seconds
        self._clock = clock

    def handle(self, request: CycleRequest) -> CycleResponse:
        """Handle `request`, running or resuming its cycle's stages.

        Raises:
            ValueError: the boundary already ran under a different request; the
                activation boundary is not a registered future-only UTC month start; a
                stage failed (watermark conflict, insufficient support, a fit error, a
                validation failure, a publish failure or a timeout) — the failure is
                recorded before this raises.
        """
        cycle_id = _cycle_id(request)
        record = self._read_record(cycle_id)
        if record is not None and record["status"] == "ok":
            return CycleResponse(
                status="ok",
                bundle_id=record["bundle_id"],
                activation_boundary=request.activation_boundary,
            )
        self._require_no_boundary_conflict(request, cycle_id)
        epoch = self._require_future_activation(request)

        cycle_dir = self._cycles_dir / cycle_id
        checkpoints_dir = cycle_dir / "checkpoints"
        completed: list[str] = list(record["completed_stages"]) if record else []
        started_at = self._clock()
        try:
            self._run_consume(request, completed, checkpoints_dir, started_at)
            self._run_mature(request, completed, checkpoints_dir, started_at)
            model, description = self._run_fit(
                request, epoch, completed, checkpoints_dir, started_at
            )
            staged = self._run_validate(model, description, completed, checkpoints_dir, started_at)
            bundle_id = self._run_publish(staged, completed, checkpoints_dir, started_at)
        except _StageFailure as failure:
            self._append_attempt(
                cycle_id,
                cycle_dir,
                request,
                started_at,
                outcome="failed",
                failed_stage=failure.stage,
                reason=str(failure),
                completed=completed,
            )
            raise ValueError(str(failure)) from failure

        self._append_attempt(
            cycle_id,
            cycle_dir,
            request,
            started_at,
            outcome="ok",
            failed_stage=None,
            reason=None,
            completed=completed,
            bundle_id=bundle_id,
        )
        return CycleResponse(
            status="ok", bundle_id=bundle_id, activation_boundary=request.activation_boundary
        )

    def eligible_bundle(self, policy: str, activation_boundary: datetime) -> str:
        """The published bundle_id eligible for `policy` at `activation_boundary`.

        Raises:
            ValueError: no cycle is recorded for this (policy, boundary), or it failed
                (naming "failed" and the stage it failed at).
        """
        record = self._find_by_policy_boundary(policy, activation_boundary)
        if record is None:
            raise ValueError(
                f"{_MODULE}: no cycle recorded for policy {policy!r} at "
                f"{iso_utc(activation_boundary)}; nothing is eligible"
            )
        if record["status"] != "ok":
            last_attempt = record["attempts"][-1]
            raise ValueError(
                f"{_MODULE}: policy {policy!r} at {iso_utc(activation_boundary)} has a "
                f"failed cycle (stage {last_attempt['failed_stage']!r}); no eligible bundle"
            )
        return str(record["bundle_id"])

    # --- Stages ------------------------------------------------------------------------

    def _check_timeout(self, started_at: datetime, stage: str) -> None:
        """Raise a `_StageFailure` naming "timeout" if the attempt is over budget."""
        elapsed = (self._clock() - started_at).total_seconds()
        if elapsed > self._timeout_seconds:
            raise _StageFailure(
                stage,
                f"{_MODULE}: timeout: the attempt exceeded the registered "
                f"{self._timeout_seconds:g} second budget ({elapsed:g}s elapsed) during "
                f"stage {stage!r}",
            )

    def _run_consume(
        self,
        request: CycleRequest,
        completed: list[str],
        checkpoints_dir: Path,
        started_at: datetime,
    ) -> None:
        self._check_timeout(started_at, "consume")
        if "consume" not in completed:
            ledger = Ledger.open(self._ledger_dir)
            current = ledger.watermark
            acceptable = {request.source_watermark, _watermark_after(request)}
            if current not in acceptable:
                raise _StageFailure(
                    "consume",
                    f"{_MODULE}: watermark conflict: the ledger's watermark is "
                    f"{current and iso_utc(current)!r}, but the request was built "
                    f"against {request.source_watermark and iso_utc(request.source_watermark)!r}",
                )
            for batch in request.batches:
                consume(self._ledger_dir, batch)
            stage_dir = checkpoints_dir / "consume"
            stage_dir.mkdir(parents=True, exist_ok=True)
            (stage_dir / "done.json").write_text(json.dumps({"stage": "consume"}))
            completed.append("consume")
        self._check_timeout(started_at, "consume")

    def _run_mature(
        self,
        request: CycleRequest,
        completed: list[str],
        checkpoints_dir: Path,
        started_at: datetime,
    ) -> None:
        self._check_timeout(started_at, "mature")
        if "mature" not in completed:
            ledger = Ledger.open(self._ledger_dir)
            mature_keys = ledger.mature_keys(request.cutoff)
            visible_keys = ledger.visible_keys(request.cutoff)
            pending_keys = tuple(key for key in visible_keys if key not in set(mature_keys))
            stage_dir = checkpoints_dir / "mature"
            stage_dir.mkdir(parents=True, exist_ok=True)
            (stage_dir / "keys.json").write_text(
                json.dumps(
                    {"mature_keys": list(mature_keys), "pending_keys": list(pending_keys)},
                    indent=1,
                    sort_keys=True,
                )
            )
            completed.append("mature")
        self._check_timeout(started_at, "mature")

    def _run_fit(
        self,
        request: CycleRequest,
        epoch: Epoch,
        completed: list[str],
        checkpoints_dir: Path,
        started_at: datetime,
    ) -> tuple[Any, BundleDescription]:
        self._check_timeout(started_at, "fit")
        fit_dir = checkpoints_dir / "fit"
        if "fit" not in completed:
            ledger = Ledger.open(self._ledger_dir)
            try:
                prepared = prepare_epoch(
                    request.policy, epoch, ledger, request.features, request.settings
                )
            except ValueError as exc:
                raise _StageFailure("fit", str(exc)) from exc
            fit_dir.mkdir(parents=True, exist_ok=True)
            f7_model_io.dump_model(prepared.model, fit_dir / "model.json", {})
            (fit_dir / "description.json").write_text(
                json.dumps(_serialize_description(prepared.description), indent=1, sort_keys=True)
            )
            completed.append("fit")
        model = f7_model_io.load_model(fit_dir / "model.json")
        description = _deserialize_description(
            json.loads((fit_dir / "description.json").read_text())
        )
        self._check_timeout(started_at, "fit")
        return model, description

    def _run_validate(
        self,
        model: Any,
        description: BundleDescription,
        completed: list[str],
        checkpoints_dir: Path,
        started_at: datetime,
    ) -> StagedBundle:
        self._check_timeout(started_at, "validate")
        validate_dir = checkpoints_dir / "validate"
        if "validate" not in completed:
            try:
                staged = bundle_module.stage(model, description, self._registry, clock=self._clock)
            except ValueError as exc:
                raise _StageFailure("validate", str(exc)) from exc
            validate_dir.mkdir(parents=True, exist_ok=True)
            (validate_dir / "staged.json").write_text(
                json.dumps(
                    {
                        "bundle_id": staged.bundle_id,
                        "reused": staged.reused,
                        "staging_dir": str(staged.staging_dir) if staged.staging_dir else None,
                        "existing_dir": str(staged.existing_dir) if staged.existing_dir else None,
                        "manifest": staged.manifest,
                    },
                    indent=1,
                    sort_keys=True,
                )
            )
            completed.append("validate")
        payload = json.loads((validate_dir / "staged.json").read_text())
        result = StagedBundle(
            bundle_id=payload["bundle_id"],
            manifest=payload["manifest"],
            reused=payload["reused"],
            staging_dir=Path(payload["staging_dir"]) if payload["staging_dir"] else None,
            existing_dir=Path(payload["existing_dir"]) if payload["existing_dir"] else None,
        )
        self._check_timeout(started_at, "validate")
        return result

    def _run_publish(
        self,
        staged: StagedBundle,
        completed: list[str],
        checkpoints_dir: Path,
        started_at: datetime,
    ) -> str:
        self._check_timeout(started_at, "publish")
        publish_dir = checkpoints_dir / "publish"
        if "publish" not in completed:
            try:
                published = bundle_module.finalize(staged, self._registry)
            except ValueError as exc:
                raise _StageFailure("publish", str(exc)) from exc
            publish_dir.mkdir(parents=True, exist_ok=True)
            (publish_dir / "bundle_id.json").write_text(
                json.dumps({"bundle_id": published.bundle_id})
            )
            completed.append("publish")
            self._check_timeout(started_at, "publish")
            return published.bundle_id
        payload = json.loads((publish_dir / "bundle_id.json").read_text())
        self._check_timeout(started_at, "publish")
        return str(payload["bundle_id"])

    # --- Records -------------------------------------------------------------------------

    def _require_no_boundary_conflict(self, request: CycleRequest, cycle_id: str) -> None:
        """A different cycle_id that already succeeded for this (policy, boundary) is a
        conflict: the boundary already ran (RWT-25)."""
        if not self._cycles_dir.exists():
            return
        boundary_iso = iso_utc(request.activation_boundary)
        for entry in self._cycles_dir.iterdir():
            if entry.name == cycle_id or not entry.is_dir():
                continue
            record = self._read_record(entry.name)
            if (
                record is not None
                and record.get("status") == "ok"
                and record.get("policy") == request.policy
                and record.get("activation_boundary") == boundary_iso
            ):
                raise ValueError(
                    f"{_MODULE}: policy {request.policy!r} at {boundary_iso} already has a "
                    "successful cycle under a different request; the boundary already ran"
                )

    def _require_future_activation(self, request: CycleRequest) -> Epoch:
        """The activation boundary must be a registered, future-only UTC month start."""
        if request.activation_boundary <= request.cutoff:
            raise ValueError(
                f"{_MODULE}: activation_boundary {iso_utc(request.activation_boundary)} "
                f"must be after the cutoff {iso_utc(request.cutoff)} (future-only activation)"
            )
        if not _is_month_start(request.activation_boundary):
            raise ValueError(
                f"{_MODULE}: activation_boundary {iso_utc(request.activation_boundary)} "
                "must be a UTC month start"
            )
        try:
            return epoch_starting(self._epochs, request.activation_boundary)
        except ValueError as exc:
            raise ValueError(
                f"{_MODULE}: activation_boundary {iso_utc(request.activation_boundary)} is "
                f"not a registered epoch boundary ({exc})"
            ) from exc

    def _read_record(self, cycle_id: str) -> dict[str, Any] | None:
        path = self._cycles_dir / cycle_id / _RECORD_FILE
        if not path.exists():
            return None
        payload: dict[str, Any] = json.loads(path.read_text())
        return payload

    def _find_by_policy_boundary(
        self, policy: str, activation_boundary: datetime
    ) -> dict[str, Any] | None:
        if not self._cycles_dir.exists():
            return None
        boundary_iso = iso_utc(activation_boundary)
        for entry in self._cycles_dir.iterdir():
            if not entry.is_dir():
                continue
            record = self._read_record(entry.name)
            if (
                record is not None
                and record.get("policy") == policy
                and record.get("activation_boundary") == boundary_iso
            ):
                return record
        return None

    def _append_attempt(
        self,
        cycle_id: str,
        cycle_dir: Path,
        request: CycleRequest,
        started_at: datetime,
        *,
        outcome: str,
        failed_stage: str | None,
        reason: str | None,
        completed: list[str],
        bundle_id: str | None = None,
    ) -> None:
        finished_at = self._clock()
        record = self._read_record(cycle_id) or {
            "cycle_id": cycle_id,
            "policy": request.policy,
            "activation_boundary": iso_utc(request.activation_boundary),
            "attempts": [],
            "bundle_id": None,
        }
        record["completed_stages"] = list(completed)
        record["status"] = "ok" if outcome == "ok" else "failed"
        if outcome == "ok":
            record["bundle_id"] = bundle_id
        record["attempts"].append(
            {
                "started_at": iso_utc(started_at),
                "finished_at": iso_utc(finished_at),
                "outcome": outcome,
                "failed_stage": failed_stage,
                "reason": reason,
            }
        )
        cycle_dir.mkdir(parents=True, exist_ok=True)
        (cycle_dir / _RECORD_FILE).write_text(json.dumps(record, indent=1, sort_keys=True))
