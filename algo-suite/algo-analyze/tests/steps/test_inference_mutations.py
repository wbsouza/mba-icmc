"""Hardener references derived independently using mpmath at 80 decimal digits."""

from typing import Any

import pytest
from algo_analyze.deflated import deflated_sharpe
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/inference_mutations.feature")

REFERENCES = {
    "zero": (0.0, 100, 0.0, 3.0, 1, None, 0.5),
    "single": (0.1, 252, 0.0, 3.0, 1, None, 0.94298686102436226844),
    "skewed": (0.15, 500, -0.5, 4.0, 20, 0.08, 0.48246557897367718752),
    "negative": (-0.05, 1200, 0.3, 5.0, 50, 0.04, 6.4279385097667885e-7),
    "many": (0.25, 1250, -1.0, 6.0, 100, 0.1, 0.46261501867133466043),
}


@given(parsers.parse("the independent DSR reference {fixture}"), target_fixture="reference")
def reference(fixture: str) -> tuple[Any, ...]:
    """Load literal expected values from the independent archived calculation."""
    return REFERENCES[fixture]


@when("the registered DSR equation is evaluated", target_fixture="probability")
def compute(reference: tuple[Any, ...]) -> float:
    """Exercise the public API with explicit selection and moment provenance."""
    sr, count, skew, kurtosis, trials, dispersion, _ = reference
    return deflated_sharpe(observed_sharpe=sr, n_returns=count, skew=skew,
                          kurtosis=kurtosis, n_trials=trials, trial_sharpe_std=dispersion,
                          provenance="independent 80-digit mpmath Eq2 fixture")


@then("its probability matches the frozen 80 digit value")
def matches(probability: float, reference: tuple[Any, ...]) -> None:
    """Require absolute tolerance only; relative tolerance must not relax the gate."""
    assert probability == pytest.approx(reference[-1], abs=1e-12, rel=0)


@given(parsers.parse("the asymmetric four observation sample scaled by {scale:g}"),
       target_fixture="sample")
def sample(scale: float) -> list[float]:
    """Preserve distributional shape over widely different units."""
    return [scale * value for value in (1, 2, 3, 6)]


@given("four huge distinct positive returns", target_fixture="sample")
def large_sample() -> list[float]:
    """Keep centered differences finite even when adding a mean would overflow."""
    return [1e308, 1.2e308, 1.4e308, 1.6e308]


@when("the portfolio moments are estimated", target_fixture="moments")
def moments(sample: list[float]) -> dict[str, float | int]:
    """Exercise scale-safe sample Sharpe and raw standardized central moments."""
    from algo_analyze.deflated import return_moments

    return return_moments(sample)


@then("the sample Sharpe skew and Pearson kurtosis match exact references")
def moment_references(moments: dict[str, float | int]) -> None:
    """Use hand-calculated central powers of [-2,-1,0,3], not production helpers."""
    assert moments["n_returns"] == 4
    assert moments["observed_sharpe"] == pytest.approx(1.3887301496588271, abs=1e-12, rel=0)
    assert moments["skew"] == pytest.approx(0.6872431934890912, abs=1e-12, rel=0)
    assert moments["kurtosis"] == pytest.approx(2.0, abs=1e-12, rel=0)


@then("the large return moments are finite and correct")
def large_references(moments: dict[str, float | int]) -> None:
    """Translation of equally spaced values has zero skew and Pearson kurtosis1.64."""
    assert moments["observed_sharpe"] == pytest.approx(5.034878350069643, abs=1e-12, rel=0)
    assert moments["skew"] == pytest.approx(0, abs=1e-12, rel=0)
    assert moments["kurtosis"] == pytest.approx(1.64, abs=1e-12, rel=0)


@given("a registered asymmetric paired time series", target_fixture="paired")
def paired() -> tuple[list[float], list[float]]:
    """Create a nonzero mean sample with unequal positive and negative changes."""
    import math

    baseline = [0.02 * math.sin(i * 0.31) for i in range(120)]
    challenger = [a + 0.007 * math.cos(i * 0.17) + 0.001 for i, a in enumerate(baseline)]
    return baseline, challenger


@when("the seeded stationary bootstrap is computed", target_fixture="block_result")
def block_result(paired: tuple[list[float], list[float]]) -> Any:
    """Use a registered ten-day mean block length and fixed Monte Carlo seed."""
    from algo_analyze.significance import paired_block_test

    return paired_block_test(*paired, block_length=10, n_resamples=200, seed=91)


def sequential_indices() -> list[list[int]]:
    """Use a sequential recurrence instead of production vectorized restart offsets."""
    import numpy as np

    rng = np.random.default_rng(91)
    starts = rng.integers(0, 120, size=(200, 120))
    restart = rng.random((200, 120)) < 0.1
    rows = []
    for row in range(200):
        indices = [int(starts[row, 0])]
        for column in range(1, 120):
            index = int(starts[row, column]) if restart[row, column] else (indices[-1] + 1) % 120
            indices.append(index)
        rows.append(indices)
    return rows


@then("its indices and inference match an independent sequential oracle")
def bootstrap_oracle(block_result: Any, paired: tuple[list[float], list[float]]) -> None:
    """Constrain all statistic terms with scalar sums and exact order-statistic inversion."""
    import math

    from algo_analyze.significance import stationary_indices

    rows = sequential_indices()
    assert stationary_indices(120, 10, 200, 91).tolist() == rows
    differences = [b - a for a, b in zip(*paired, strict=True)]
    effect = math.fsum(differences) / 120
    errors = [abs(math.fsum(differences[i] - effect for i in row) / 120) for row in rows]
    probability = (1 + sum(error >= abs(effect) for error in errors)) / 201
    radius = sorted(errors)[190]
    assert block_result.effect == pytest.approx(effect, abs=1e-15, rel=0)
    assert block_result.p_value == probability
    assert block_result.confidence_interval == pytest.approx(
        (effect - radius, effect + radius), abs=1e-15, rel=0
    )
    assert block_result.expected_blocks == 12
    assert block_result.reject_null == (probability < 0.05)


@given("DSR moments on the Pearson feasibility boundary", target_fixture="boundary")
def boundary() -> dict[str, Any]:
    """Permit rounding less than 1e-12 below kurtosis = 1 + skew squared."""
    return dict(observed_sharpe=0.1, n_returns=100, skew=1.0, kurtosis=2.0 - 5e-13,
                n_trials=1, trial_sharpe_std=None, provenance="rounded Pearson boundary")


@when("the boundary DSR equation is evaluated", target_fixture="boundary_probability")
def boundary_probability(boundary: dict[str, Any]) -> float:
    """Exercise the public feasibility validation with realistic rounding."""
    return deflated_sharpe(**boundary)


@then("it accepts moment rounding within the documented tolerance")
def boundary_accepted(boundary_probability: float) -> None:
    """A valid rounded moment set still yields a finite probability."""
    assert 0 < boundary_probability < 1


@given("a portfolio with exact daily equity of 100 110 110 99 100", target_fixture="equity_path")
def equity_path(tmp_path: Any) -> Any:
    """Record engine equity including a genuine flat daily period."""
    return _write_equity(tmp_path, [[1577836800 + i * 86400, value]
                                    for i, value in enumerate((100, 110, 110, 99, 100))])


@given("a portfolio with exact daily candles closing at 100 110 110 99 100",
       target_fixture="equity_path")
def candle_path(tmp_path: Any) -> Any:
    """Record LEAN-shaped end-stamped candles whose open is the previous day's close."""
    closes = (100, 110, 110, 99, 100)
    rows = []
    for i, close in enumerate(closes):
        open_ = closes[max(i - 1, 0)]
        rows.append([1577836800 + i * 86400, open_, max(open_, close) + 5,
                     min(open_, close) - 5, close])
    return _write_equity(tmp_path, rows)


def _write_equity(tmp_path: Any, values: list[list[float]]) -> Any:
    """Write a four-return run directory around the supplied equity rows."""
    import json

    metadata = dict(source="main.json", frequency="calendar-day", timezone="UTC",
                    annualization=365, risk_free_daily=0, costs="net", symbol="EURUSD",
                    start="2020-01-01", end="2020-01-05")
    (tmp_path / "inference-inputs.json").write_text(json.dumps(metadata))
    (tmp_path / "run.json").write_text(json.dumps(dict(
        success=True, symbol="EURUSD", start="2020-01-01", end="2020-01-04")))
    (tmp_path / "main.json").write_text(json.dumps({
        "charts": {"Strategy Equity": {"series": {"Equity": {"values": values}}}}}))
    return tmp_path


@when("its portfolio returns are loaded", target_fixture="daily_returns")
def daily_returns(equity_path: Any) -> tuple[float, ...]:
    """Read the full declared calendar rather than closed trade samples."""
    from algo_analyze.portfolio import load_portfolio_returns

    return load_portfolio_returns(equity_path).returns


@then("the four daily returns are 0.1 0 -0.1 and 1/99")
def exact_daily_returns(daily_returns: tuple[float, ...]) -> None:
    """Check return numerators, denominators and retention of unchanged equity."""
    assert daily_returns == pytest.approx((0.1, 0, -0.1, 1 / 99), abs=1e-15, rel=0)


@given("two portfolio series with identical metadata but different timestamps",
       target_fixture="shifted_pair")
def shifted_pair() -> tuple[Any, Any]:
    """Keep all conventions equal while shifting one observation timestamp."""
    from algo_analyze.portfolio import PortfolioReturns

    metadata = dict(symbol="EURUSD", start="2020-01-01", end="2020-01-04",
                    frequency="calendar-day", timezone="UTC", risk_free_daily=0, costs="net")
    return (PortfolioReturns((1, 2, 3), (0.1, 0.2, 0.3), metadata),
            PortfolioReturns((1, 2, 4), (0.1, 0.2, 0.3), metadata))


@when("the pair alignment is validated", target_fixture="alignment_error")
def alignment_error(shifted_pair: tuple[Any, Any]) -> str:
    """Require a mismatch diagnostic independent of metadata validation."""
    from algo_analyze.portfolio import align_portfolios

    with pytest.raises(ValueError) as error:
        align_portfolios(*shifted_pair)
    return str(error.value)


@then("pair alignment rejects the shifted calendar grid")
def shifted_rejected(alignment_error: str) -> None:
    """Expose a stable scientific-contract diagnostic."""
    assert "incompatible portfolio" in alignment_error


@given("large finite paired differences whose mean overflows", target_fixture="overflow_pair")
def overflow_pair() -> tuple[list[float], list[float]]:
    """Every difference is finite but NumPy's accumulated sample sum cannot be represented."""
    return [0.0] * 120, [1e307, 1.1e307, 0.9e307] * 40


@when("the large difference bootstrap is requested", target_fixture="overflow_error")
def overflow_error(overflow_pair: tuple[list[float], list[float]]) -> str:
    """Validate the mean separately from each finite paired observation."""
    from algo_analyze.significance import paired_block_test

    with pytest.raises(ValueError) as error:
        paired_block_test(*overflow_pair, block_length=5, n_resamples=199, seed=7)
    return str(error.value)


@then("it rejects the nonfinite mean before resampling")
def overflow_rejected(overflow_error: str) -> None:
    """Do not let a later interval failure conceal invalid mean handling."""
    assert "differences and their mean must be finite" in overflow_error


@given(parsers.parse("a valid bootstrap sample at the {boundary} boundary"),
       target_fixture="bootstrap_boundary")
def bootstrap_boundary(boundary: str) -> tuple[list[float], list[float], dict[str, Any]]:
    """Distinguish variance roundoff, tiny units and exact Monte Carlo alpha resolution."""
    sample = [0.9999999169877148] + [1.0] * 29
    alpha = 0.05
    if boundary == "tiny units":
        sample = [1e-200, -1e-200, 2e-200] * 10
    if boundary == "alpha resolution":
        sample = [0.01, -0.02, 0.015] * 10
        alpha = 0.01
    return [0.0] * 30, sample, dict(block_length=3, n_resamples=100, seed=7, alpha=alpha)


@when("the boundary bootstrap is computed", target_fixture="boundary_bootstrap")
def boundary_bootstrap(bootstrap_boundary: tuple[Any, ...]) -> Any:
    """Exercise public resampling without changing the numerical validity policy."""
    from algo_analyze.significance import paired_block_test

    baseline, challenger, settings = bootstrap_boundary
    return paired_block_test(baseline, challenger, **settings)


@then("the boundary inference remains available and finite")
def bootstrap_boundary_available(boundary_bootstrap: Any) -> None:
    """Require numerical support to survive changes of units and valid boundary settings."""
    import math

    assert 0 <= boundary_bootstrap.p_value <= 1
    assert all(math.isfinite(value) for value in boundary_bootstrap.confidence_interval)


@given("a finite bootstrap sample with an unrepresentable interval endpoint",
       target_fixture="extreme_pair")
def extreme_pair(monkeypatch: Any) -> tuple[list[float], list[float]]:
    """Control the resampled extreme while retaining finite sample mean and error radius."""
    import numpy as np
    from algo_analyze import significance

    values = ([1.79e308] * 8 + [-1.79e308] * 8) * 4
    values[-1] *= 0.8
    monkeypatch.setattr(significance, "stationary_indices",
                        lambda n, block_length, n_resamples, seed: np.full((n_resamples, n), 8))
    return [0.0] * 64, values


@when("the extreme interval is computed", target_fixture="interval_error")
def interval_error(extreme_pair: tuple[list[float], list[float]]) -> str:
    """A finite center and finite radius can still produce an infinite endpoint."""
    from algo_analyze.significance import paired_block_test

    with pytest.raises(ValueError) as error:
        paired_block_test(*extreme_pair, block_length=5, n_resamples=100, seed=7)
    return str(error.value)


@then("the interval endpoint overflow is rejected")
def interval_overflow_rejected(interval_error: str) -> None:
    """Require the specific interval diagnostic, not a prior unsupported sample failure."""
    assert "confidence interval endpoints must be finite" in interval_error


@when(parsers.parse("its selection history uses boolean {count}"), target_fixture="count_error")
def count_error(equity_path: Any, count: str) -> str:
    """Booleans must not silently stand in for actual counts or interim looks."""
    import json

    from algo_analyze.reports import metrics_report

    data = dict(n_trials=1, trial_count=1, interim_looks=1, trial_sharpe_std=None,
                frequency="calendar-day", provenance="registered fixture")
    data[count] = True
    selection = equity_path / "selection.json"
    selection.write_text(json.dumps(data))
    (equity_path / "metrics.json").write_text(json.dumps(dict(
        sharpe=1, total_return=0.0, max_drawdown=0.0, hit_rate=0.5)))
    with pytest.raises(ValueError) as error:
        metrics_report(equity_path, selection)
    return str(error.value)


@then("the selection count is rejected as a noninteger")
def count_rejected(count_error: str) -> None:
    """Require the count contract to fail before unrelated probability calculations."""
    assert "must be a positive integer" in count_error


@given("a bootstrap with exactly 6 extreme errors in 199 draws", target_fixture="alpha_pair")
def alpha_pair(monkeypatch: Any) -> tuple[list[float], list[float]]:
    """Control the Monte Carlo boundary where binary float multiplication rounds upward."""
    import numpy as np
    from algo_analyze import significance

    rows = np.tile(np.arange(100), (199, 1))
    rows[193:, :] = np.array([1] * 60 + [0] * 40)
    monkeypatch.setattr(significance, "stationary_indices",
                        lambda n, block_length, n_resamples, seed: rows)
    return [0.0] * 100, [-0.9, 1.1] * 50


@when("its paired interval is evaluated at alpha 0.035", target_fixture="alpha_result")
def alpha_result(alpha_pair: tuple[list[float], list[float]]) -> Any:
    """Exercise public strict p < alpha decision and its corresponding interval."""
    from algo_analyze.significance import paired_block_test

    return paired_block_test(*alpha_pair, block_length=5, n_resamples=199, seed=7, alpha=0.035)


@then("p equals alpha and its interval contains zero")
def alpha_compatible(alpha_result: Any) -> None:
    """A boundary nonrejection must never be paired with an interval excluding zero."""
    assert alpha_result.p_value == 0.035
    assert not alpha_result.reject_null
    lower, upper = alpha_result.confidence_interval
    assert lower <= 0 <= upper


@given("a bootstrap with 98 extreme errors in 100 draws", target_fixture="high_alpha_pair")
def high_alpha_pair(monkeypatch: Any) -> tuple[list[float], list[float]]:
    """Keep two small errors to distinguish upper Monte Carlo grid endpoints."""
    import numpy as np
    from algo_analyze import significance

    rows = np.tile(np.arange(100), (100, 1))
    rows[2:, :] = np.array([1] * 60 + [0] * 40)
    monkeypatch.setattr(significance, "stationary_indices",
                        lambda n, block_length, n_resamples, seed: rows)
    return [0.0] * 100, [-0.9, 1.1] * 50


@when("its paired interval is evaluated at alpha 0.99", target_fixture="high_alpha_result")
def high_alpha_result(high_alpha_pair: tuple[list[float], list[float]]) -> Any:
    """Exercise a supported high alpha rather than assuming a conventional threshold."""
    from algo_analyze.significance import paired_block_test

    return paired_block_test(*high_alpha_pair, block_length=5, n_resamples=100, seed=7, alpha=0.99)


@then("its rejected null agrees with an interval excluding zero")
def high_alpha_compatible(high_alpha_result: Any) -> None:
    """CI inversion must use every attainable Monte Carlo probability."""
    assert high_alpha_result.p_value == 99 / 101
    assert high_alpha_result.reject_null
    assert high_alpha_result.confidence_interval[0] > 0
