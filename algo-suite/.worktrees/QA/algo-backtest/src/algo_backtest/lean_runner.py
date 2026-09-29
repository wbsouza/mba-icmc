"""Run a LEAN backtest in the pinned container — the narrow production run path.

Replicates the wiring the `lean` CLI applies to the pinned `quantconnect/lean` image
(mounts + launcher config) programmatically via testcontainers, so the suite needs no
`lean` CLI and no QuantConnect account. The image's default entrypoint is already
`dotnet QuantConnect.Lean.Launcher.dll` with workdir `/Lean/Launcher/bin/Debug`, so
only the four mounts are needed:

  host algo dir  -> /LeanCLI                              (rw, holds main.py)
  host results   -> /Results                             (rw, LEAN result JSON)
  generated cfg  -> /Lean/Launcher/bin/Debug/config.json (ro, secret-free)
  data overlays  -> /Lean/Data/<subpath>                 (ro, over the baked DBs)

The launcher config is held here as a secret-free dict (no QC credentials — a local
backtest with DefaultDataProvider + LocalDisk*FileProvider needs no API) and written
per run with any injected `parameters`. Deliberately minimal: no general runner
framework, just enough to run one algorithm and collect /Results.
"""

from __future__ import annotations

import contextlib
import copy
import json
import os
import shutil
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from testcontainers.core.container import DockerContainer

LEAN_IMAGE = "quantconnect/lean:17748"

_ALGO_MNT = "/LeanCLI"
_DATA_ROOT = "/Lean/Data"
_RESULTS_MNT = "/Results"
_CONFIG_MNT = "/Lean/Launcher/bin/Debug/config.json"

# Generous default for a cold run (first pull is ~10 GB); override via LEAN_TEST_TIMEOUT.
DEFAULT_TIMEOUT_S = int(os.environ.get("LEAN_TEST_TIMEOUT", "600"))

# Secret-free LEAN launcher config (no api-access-token / organization-id / job-user-id).
_LAUNCHER_CONFIG: dict[str, Any] = {
    "data-folder": _DATA_ROOT,
    "results-destination-folder": _RESULTS_MNT,
    "object-store-root": "/Storage",
    "algorithm-type-name": "main",
    "algorithm-language": "Python",
    "algorithm-location": f"{_ALGO_MNT}/main.py",
    "environment": "backtesting",
    "close-automatically": True,
    "debugging": False,
    "show-missing-data-logs": True,
    "log-handler": "QuantConnect.Logging.CompositeLogHandler",
    "messaging-handler": "QuantConnect.Messaging.Messaging",
    "job-queue-handler": "QuantConnect.Queues.JobQueue",
    "api-handler": "QuantConnect.Api.Api",
    "map-file-provider": "QuantConnect.Data.Auxiliary.LocalDiskMapFileProvider",
    "factor-file-provider": "QuantConnect.Data.Auxiliary.LocalDiskFactorFileProvider",
    "data-provider": "QuantConnect.Lean.Engine.DataFeeds.DefaultDataProvider",
    "object-store": "QuantConnect.Lean.Engine.Storage.LocalObjectStore",
    "data-aggregator": "QuantConnect.Lean.Engine.DataFeeds.AggregationManager",
    "environments": {
        "backtesting": {
            "live-mode": False,
            "setup-handler": "QuantConnect.Lean.Engine.Setup.BacktestingSetupHandler",
            "result-handler": "QuantConnect.Lean.Engine.Results.BacktestingResultHandler",
            "data-feed-handler": "QuantConnect.Lean.Engine.DataFeeds.FileSystemDataFeed",
            "real-time-handler": "QuantConnect.Lean.Engine.RealTime.BacktestingRealTimeHandler",
            "history-provider": [
                "QuantConnect.Lean.Engine.HistoricalData.SubscriptionDataReaderHistoryProvider"
            ],
            "transaction-handler": (
                "QuantConnect.Lean.Engine.TransactionHandlers.BacktestingTransactionHandler"
            ),
            "data-provider": "QuantConnect.Lean.Engine.DataFeeds.DefaultDataProvider",
        }
    },
}


@dataclass(frozen=True)
class LeanRun:
    """Outcome of one containerized LEAN backtest."""

    exit_code: int
    logs: str
    results_dir: Path

    def grep(self, needle: str) -> list[str]:
        """Log lines containing `needle` (LEAN prints algorithm Debug() output to stdout)."""
        return [line for line in self.logs.splitlines() if needle in line]


def _write_config(dest_dir: Path, parameters: Mapping[str, str] | None) -> Path:
    """Write the secret-free launcher config (+ injected `parameters`) into `dest_dir`."""
    config = copy.deepcopy(_LAUNCHER_CONFIG)
    config["parameters"] = dict(parameters or {})
    path = dest_dir / "config.json"
    path.write_text(json.dumps(config, indent=2))
    return path


def run_lean(
    algo_dir: Path,
    results_dir: Path,
    data_mounts: Mapping[str, Path] | None = None,
    parameters: Mapping[str, str] | None = None,
    timeout: int = DEFAULT_TIMEOUT_S,
) -> LeanRun:
    """Run one LEAN backtest in the pinned image; return its exit code, logs, results dir.

    Args:
        algo_dir: dir holding `main.py` (class `main`). Copied to a private temp dir
            before mounting rw, so the engine's write-backs never touch the source.
        results_dir: dir mounted at /Results; LEAN writes its result JSON here.
        data_mounts: {subpath-under-/Lean/Data: host dir} overlays onto the image's
            baked Data tree (keeping the baked market-hours/symbol-properties DBs).
        parameters: backtest parameters exposed to the algorithm via get_parameter().
        timeout: seconds to wait for the backtest to exit.

    Raises:
        FileNotFoundError: if `algo_dir` has no `main.py` (fail fast — misconfigured run).
    """
    if not (algo_dir / "main.py").is_file():
        raise FileNotFoundError(
            f"algo_dir {algo_dir} has no main.py; the LEAN launcher expects "
            f"algorithm-location=/LeanCLI/main.py (a main.py with class `main`)."
        )

    work = Path(tempfile.mkdtemp(prefix="lean-algo-"))
    shutil.copytree(algo_dir, work, dirs_exist_ok=True)
    cfg_dir = Path(tempfile.mkdtemp(prefix="lean-cfg-"))
    config_path = _write_config(cfg_dir, parameters)
    container = DockerContainer(LEAN_IMAGE)
    container.with_volume_mapping(str(work), _ALGO_MNT, "rw")
    container.with_volume_mapping(str(results_dir), _RESULTS_MNT, "rw")
    container.with_volume_mapping(str(config_path), _CONFIG_MNT, "ro")
    for subpath, host_dir in (data_mounts or {}).items():
        container.with_volume_mapping(str(host_dir), f"{_DATA_ROOT}/{subpath}", "ro")

    try:
        # start() is inside the try so a pull/start failure still cleans the temp dirs.
        container.start()
        wrapped = container.get_wrapped_container()
        outcome = wrapped.wait(timeout=timeout)
        logs = wrapped.logs().decode("utf-8", "replace")
    finally:
        with contextlib.suppress(Exception):  # best-effort teardown (may never have started)
            container.stop()
        shutil.rmtree(work, ignore_errors=True)  # engine writes __pycache__ as root
        shutil.rmtree(cfg_dir, ignore_errors=True)

    return LeanRun(exit_code=int(outcome["StatusCode"]), logs=logs, results_dir=results_dir)
