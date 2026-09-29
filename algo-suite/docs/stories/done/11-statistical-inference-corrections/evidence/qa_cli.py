"""Execute disposable researcher-facing CLI acceptance checks without analyzer imports."""

from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

EVIDENCE = Path(__file__).resolve().parent
SUITE = next(path for path in EVIDENCE.parents if path.name == "algo-suite")


def write(path: Path, value: object) -> None:
    """Write deterministic disposable JSON artifacts."""
    path.write_text(json.dumps(value, sort_keys=True) + "\n")


def digest(path: Path) -> str:
    """Independently hash input bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> dict[str, Any]:
    """Read a fixture object for an isolated mutation."""
    result: dict[str, Any] = json.loads(path.read_text())
    return result


def fixture(root: Path, name: str, challenger: bool = False) -> list[float]:
    """Create engine-equity fixtures with different trade counts and flat periods."""
    run = root / "runs" / name
    run.mkdir(parents=True, exist_ok=True)
    start = datetime(2015, 1, 1, tzinfo=UTC)
    returns = [(-0.01, 0.0, 0.012, 0.003)[i % 4] for i in range(120)]
    if challenger:
        returns = [r + (0.002 if i % 3 else -0.001) for i, r in enumerate(returns)]
    equity = 100_000.0
    values = [[int(start.timestamp()), equity]]
    for i, value in enumerate(returns, 1):
        equity *= 1 + value
        values.append([int((start + timedelta(days=i)).timestamp()), equity])
    write(
        run / "main.json",
        {"charts": {"Strategy Equity": {"series": {"Equity": {"values": values}}}}},
    )
    write(
        run / "run.json",
        {
            "success": True,
            "symbol": "EURUSD",
            "start": "2015-01-01",
            "end": "2015-04-30",
            "closed_trades": 3 if challenger else 1,
        },
    )
    write(
        run / "metrics.json",
        {"sharpe": 9.0, "total_return": 0.1, "hit_rate": 0.5, "max_drawdown": -0.1},
    )
    write(run / "trades.json", [{"return": 0.99}] * (3 if challenger else 1))
    write(
        run / "inference-inputs.json",
        {
            "source": "main.json",
            "frequency": "calendar-day",
            "timezone": "UTC",
            "annualization": 365,
            "risk_free_daily": 0,
            "costs": "fixture engine fees and slippage included",
            "symbol": "EURUSD",
            "start": "2015-01-01",
            "end": "2015-05-01",
        },
    )
    return returns


def inverse_normal(probability: float) -> float:
    """Invert erf by bisection independently of production NormalDist.inv_cdf."""
    left, right = -12.0, 12.0
    for _ in range(100):
        middle = (left + right) / 2
        if (1 + math.erf(middle / math.sqrt(2))) / 2 < probability:
            left = middle
        else:
            right = middle
    return (left + right) / 2


def expected_dsr(values: list[float]) -> float:
    """Evaluate Eq2 directly from prescribed returns and independent erf inversion."""
    n = len(values)
    mean = math.fsum(values) / n
    centered = [value - mean for value in values]
    m2 = math.fsum(value**2 for value in centered) / n
    skew = math.fsum(value**3 for value in centered) / n / m2**1.5
    kurtosis = math.fsum(value**4 for value in centered) / n / m2**2
    sharpe = mean / math.sqrt(m2 * n / (n - 1))
    gamma = 0.5772156649015329
    threshold = 0.02 * (
        (1 - gamma) * inverse_normal(0.9) + gamma * inverse_normal(1 - 1 / (10 * math.e))
    )
    z = (sharpe - threshold) * math.sqrt(n - 1)
    z /= math.sqrt(1 - skew * sharpe + (kurtosis - 1) * sharpe**2 / 4)
    return (1 + math.erf(z / math.sqrt(2))) / 2


class Researcher:
    """Record subprocess commands and results with stable temporary-path aliases."""

    def __init__(self, root: Path) -> None:
        """Isolate shared application configuration and preserve execution evidence."""
        self.root = root
        self.records: list[dict[str, Any]] = []
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("ALGO_")}
        self.env.update(ALGO_DATA_ROOT=str(root), ALGO_CONF_DIR=str(root / "conf"))

    def invoke(self, *args: str, exit_code: int = 0) -> dict[str, Any]:
        """Run the installed console entry point and assert its expected exit status."""
        command = [str(SUITE / ".venv/bin/algo-analyze"), *args]
        result = subprocess.run(
            command, env=self.env, cwd=SUITE, text=True, capture_output=True, check=False
        )
        assert result.returncode == exit_code, result.stderr
        stdout = result.stdout.replace(str(self.root), "$QA_DATA_ROOT")
        stderr = result.stderr.replace(str(self.root), "$QA_DATA_ROOT")
        self.records.append(
            {
                "command": [a.replace(str(self.root), "$QA_DATA_ROOT") for a in command],
                "exit_code": result.returncode,
                "stdout": stdout,
                "stderr": stderr,
            }
        )
        if exit_code:
            assert "Traceback" not in stderr
            return {"diagnostic": stderr}
        payload: dict[str, Any] = json.loads(stdout)
        assert payload["schema_version"] == 2
        return payload

    def compare(self, **kwargs: int) -> dict[str, Any]:
        """Use declared primary/sensitivity settings across CLI checks."""
        return self.invoke(
            "significance",
            "--runs",
            "base",
            "--runs",
            "challenger",
            "--block-length",
            "4",
            "--block-length",
            "8",
            "--block-rule",
            "qa-predeclared",
            "--resamples",
            "199",
            "--seed",
            "123",
            **kwargs,
        )


def verify_available(qa: Researcher, values: list[float]) -> dict[str, Any]:
    """Check probability, source hashes, frequency, paired effect, and reproducibility."""
    selection = qa.root / "selection.json"
    write(
        selection,
        {
            "n_trials": 10,
            "trial_count": 20,
            "interim_looks": 2,
            "trial_sharpe_std": 0.02,
            "frequency": "calendar-day",
            "provenance": "disposable QA candidate ledger",
        },
    )
    result = qa.invoke("metrics", "--run", "base", "--selection", str(selection))
    assert result["status"] == "available"
    assert abs(result["deflated_sharpe_probability"] - expected_dsr(values)) < 1e-12
    assert result["descriptive_metrics"]["sharpe"] == 9
    assert result["moments"]["n_returns"] == 120
    portfolio = result["portfolio"]
    assert portfolio["n_observations"] == 120
    assert portfolio["frequency"] == "calendar-day" and portfolio["timezone"] == "UTC"
    assert portfolio["annualization"] == 365 and portfolio["risk_free_daily"] == 0
    assert portfolio["start"] == "2015-01-01" and portfolio["end"] == "2015-05-01"
    assert portfolio["costs"] and portfolio["equity_basis"] == "engine portfolio mark-to-market"
    for key, name in (
        ("source_sha256", "main.json"),
        ("contract_sha256", "inference-inputs.json"),
        ("manifest_sha256", "run.json"),
    ):
        assert portfolio[key] == digest(qa.root / "runs/base" / name)
    assert result["selection"]["source_sha256"] == digest(selection)
    paired = qa.compare()
    assert paired == qa.compare()
    assert paired["portfolio_a"]["source_sha256"] == digest(qa.root / "runs/base/main.json")
    assert paired["portfolio_b"]["source_sha256"] == digest(qa.root / "runs/challenger/main.json")
    primary = paired["primary"]
    assert primary["method"] == "paired_stationary_bootstrap"
    assert abs(primary["effect"] - 0.001) < 1e-14
    assert primary["n_observations"] == 120 and primary["expected_blocks"] == 30
    assert primary["seed"] == 123 and primary["n_resamples"] == 199
    assert paired["prespecified_block_lengths"] == [4, 8]
    assert paired["sensitivity"][0]["block_length"] == 8
    lower, upper = primary["confidence_interval"]
    assert lower <= primary["effect"] <= upper
    assert primary["reject_null"] == (primary["p_value"] < primary["alpha"])
    assert primary["reject_null"] == (lower > 0 or upper < 0)
    assert primary["sidedness"] == "two-sided" and primary["assumptions"]
    return result


def verify_invariance(qa: Researcher, original: dict[str, Any]) -> None:
    """Change descriptive/trade artifacts while holding actual portfolio equity fixed."""
    run = qa.root / "runs/base"
    headline = read(run / "metrics.json")
    headline["sharpe"] = -11
    write(run / "metrics.json", headline)
    manifest = read(run / "run.json")
    manifest["closed_trades"] = 999
    write(run / "run.json", manifest)
    write(run / "trades.json", [{"return": -0.9}] * 999)
    result = qa.invoke("metrics", "--run", "base", "--selection", str(qa.root / "selection.json"))
    assert result["deflated_sharpe_probability"] == original["deflated_sharpe_probability"]
    assert result["moments"] == original["moments"]
    assert result["descriptive_metrics"]["sharpe"] == -11


def verify_bad_inputs(qa: Researcher) -> None:
    """Exercise absent prerequisites, coverage gaps, duplicates, and incompatible pairs."""
    result = qa.invoke("metrics", "--run", "base")
    assert result["status"] == "unavailable" and "selection history" in result["reason"]
    run = qa.root / "runs/base"
    contract_path = run / "inference-inputs.json"
    contract = contract_path.read_bytes()
    contract_path.unlink()
    result = qa.invoke("metrics", "--run", "base")
    assert result["status"] == "unavailable" and "inference-inputs.json" in result["reason"]
    contract_path.write_bytes(contract)
    engine_path = run / "main.json"
    engine = read(engine_path)
    points = engine["charts"]["Strategy Equity"]["series"]["Equity"]["values"]
    saved = engine_path.read_bytes()
    del points[20]
    write(engine_path, engine)
    result = qa.invoke("metrics", "--run", "base")
    assert result["status"] == "unavailable" and "endpoint" in result["reason"]
    points.insert(20, points[19])
    write(engine_path, engine)
    result = qa.invoke("metrics", "--run", "base", exit_code=2)
    assert "unique" in result["diagnostic"]
    engine_path.write_bytes(saved)
    for key, value in (("symbol", "GBPUSD"), ("start", "2015-01-02")):
        other = qa.root / "runs/challenger"
        for name in ("run.json", "inference-inputs.json"):
            path = other / name
            payload = read(path)
            payload[key] = value
            write(path, payload)
        result = qa.compare(exit_code=2)
        assert "incompatible" in result["diagnostic"]
        fixture(qa.root, "challenger", challenger=True)


def verify_inventory(qa: Researcher) -> None:
    """Assert inventory labels legacy results and leaves every source byte unchanged."""
    write(qa.root / "runs/base/legacy-analysis.json", {"deflated_sharpe": 2.4, "p_value": 0.01})
    before = {str(p.relative_to(qa.root)): digest(p) for p in qa.root.rglob("*.json")}
    report = qa.invoke("inference-inventory")
    assert len(report["runs"]) == 2
    assert "exploratory" in report["legacy_notice"]
    assert all(run["status"] == "unavailable" for run in report["runs"])
    assert all("selection history" in run["reason"] for run in report["runs"])
    after = {str(p.relative_to(qa.root)): digest(p) for p in qa.root.rglob("*.json")}
    assert before == after


def verify_degenerate(qa: Researcher) -> None:
    """Check missing dispersion, invalid equity, and zero-difference uncertainty."""
    selection = qa.root / "selection.json"
    original = selection.read_bytes()
    data = read(selection)
    data["trial_sharpe_std"] = None
    write(selection, data)
    result = qa.invoke("metrics", "--run", "base", "--selection", str(selection))
    assert result["status"] == "unavailable" and "dispersion" in result["reason"]
    selection.write_bytes(original)
    engine = qa.root / "runs/challenger/main.json"
    original = engine.read_bytes()
    data = read(engine)
    data["charts"]["Strategy Equity"]["series"]["Equity"]["values"][20][1] = "NaN"
    write(engine, data)
    result = qa.compare(exit_code=2)
    assert "numeric" in result["diagnostic"]
    engine.write_bytes((qa.root / "runs/base/main.json").read_bytes())
    result = qa.compare()
    assert result["status"] == "unavailable"
    assert "degenerate" in result["primary"]["reason"]
    engine.write_bytes(original)


def main() -> None:
    """Run all black-box checks and archive exact commands and deterministic outcomes."""
    with tempfile.TemporaryDirectory(prefix="story11-qa-") as temporary:
        root = Path(temporary)
        values = fixture(root, "base")
        fixture(root, "challenger", challenger=True)
        qa = Researcher(root)
        original = verify_available(qa, values)
        verify_invariance(qa, original)
        verify_bad_inputs(qa)
        verify_degenerate(qa)
        verify_inventory(qa)
        write(
            EVIDENCE / "qa-results.json",
            {
                "status": "passed",
                "command": "uv run python " + str(Path(__file__).relative_to(SUITE)),
                "working_directory": str(SUITE),
                "temporary_path_alias": "$QA_DATA_ROOT",
                "independent_dsr_expected": expected_dsr(values),
                "commands": qa.records,
            },
        )
        print(f"PASS: {len(qa.records)} subprocess CLI invocations")


if __name__ == "__main__":
    main()
