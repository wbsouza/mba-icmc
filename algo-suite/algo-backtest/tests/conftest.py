"""Shared fixtures for the algo-backtest BDD suite.

The containerized LEAN run path now lives in production code
(`algo_backtest.lean_runner.run_lean`); this conftest only adds the test-side glue:
a Docker-availability skip, the probe-log parser used by the timezone/parquet
round-trip features, and a per-scenario context dict. Living at the `tests/` root makes
these visible to every step module under `tests/steps/`.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from algo_backtest.lean_runner import LeanRun, run_lean

# A run callable: (algo_dir, results_dir, data_mounts, parameters, timeout) -> LeanRun.
LeanBacktest = Callable[..., LeanRun]


@dataclass(frozen=True)
class ProbeLog:
    """Parser for the integration probe algorithm's PROBE_* log lines (shared by steps)."""

    @staticmethod
    def _field(line: str, key: str) -> str:
        """The value of `key=...` in a pipe-delimited PROBE log line."""
        return line.split(f"{key}=", 1)[1].split("|", 1)[0].strip()

    def bars(self, logs: str) -> list[tuple[str, float, float]]:
        """(utc_endtime, bid_close, ask_close) per PROBE_BAR line, in order.

        `utc` is `self.UtcTime` at delivery (= the bar's UTC EndTime), the authoritative
        timing observable; bid/ask close prove the payload mapping survived the round-trip.
        """
        out = []
        for line in logs.splitlines():
            if "PROBE_BAR|" not in line:
                continue
            out.append(
                (self._field(line, "utc"), round(float(self._field(line, "bidc")), 5),
                 round(float(self._field(line, "askc")), 5))
            )
        return out

    def done_count(self, logs: str) -> int | None:
        """The bar count from the PROBE_DONE line, or None if it never printed."""
        for line in logs.splitlines():
            if "PROBE_DONE|count=" in line:
                return int(self._field(line + "|", "count"))
        return None


@pytest.fixture(scope="session")
def require_docker() -> None:
    """Skip the scenario if Docker is unreachable (the `@integration` features are opt-in).

    Skips with a clear message instead of failing with a raw DockerException.
    """
    try:
        import docker  # provided transitively by testcontainers

        docker.from_env().ping()
    except Exception as exc:  # noqa: BLE001 — any docker init failure means "skip"
        pytest.skip(f"Docker unavailable for integration tests: {exc}")


@pytest.fixture(scope="session")
def lean_backtest(require_docker: None) -> LeanBacktest:
    """Provide the production LEAN runner (skips first if Docker is unreachable)."""
    return run_lean


@pytest.fixture
def probe_log() -> ProbeLog:
    """Parser for the probe algorithm's PROBE_BAR / PROBE_DONE log lines."""
    return ProbeLog()


@pytest.fixture
def ctx() -> dict[str, Any]:
    """Mutable per-scenario context shared across BDD steps."""
    return {}


@pytest.fixture(scope="session")
def native_dsha_probe(lean_backtest, tmp_path_factory):
    """Run all native HA acceptance checks once per pytest session."""
    results_dir = tmp_path_factory.mktemp("dsha-native")
    result = lean_backtest(
        algo_dir=Path(__file__).parent / "algos" / "double_smoothed_heikin_ashi",
        results_dir=results_dir,
    )
    assert result.exit_code == 0, result.logs[-8000:]
    assert "DSHA|DONE" in result.logs, result.logs[-8000:]
    assert "ERROR::" not in result.logs, result.logs[-8000:]
    return json.loads((results_dir / "perception-native-observations.json").read_text())
