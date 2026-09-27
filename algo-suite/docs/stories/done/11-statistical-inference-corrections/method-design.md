# Method and validation registration

Registered before executing the simulation study. This defines the analysis
software contract; it does not register the trading experiment retroactively.

## Return basis

Use actual LEAN Strategy Equity observations (including open positions), with
explicit UTC daily boundaries and a declared source, cost treatment, zero daily
risk-free convention, annualization factor, pair and complete evaluation window.
Require each endpoint; no interpolation, forward filling, truncation, or use of
trade notional returns. Missing metadata/history makes inference unavailable.
Invalid observations fail validation. Record source and metadata SHA-256 hashes.
Annualized engine Sharpe remains descriptive; inference recomputes moments from
one nonannualized portfolio-return sample. Equal trade counts are unnecessary.

## Selection correction

Bailey and López de Prado (2014), Eq. 2, with Pearson kurtosis. The threshold is
across-trial Sharpe standard deviation multiplied by the expected maximum of
N independent standard-normal trials; N is an explicitly documented effective
count, not the number of published runs. One explicitly registered trial uses
threshold zero and returns PSR, including 0.5 at SR=0. Missing history does not
imply N=1. Record variants, interim looks and the source of trial assumptions.
Classical DSR does not account for arbitrary serial dependence.

## Paired time-series comparison

Use the stationary bootstrap of Politis and Romano (1994), JASA 89(428),
1303–1313, DOI 10.1080/01621459.1994.10476870. Draw circular contiguous blocks
whose lengths are geometric with declared expected length L; resample the same
indices for both strategies. The estimand is mean daily net return B minus A;
the null is zero, two-sided. Center differences under the null. The p-value is
the plus-one fraction of bootstrap absolute errors at least as large as the
observed absolute mean. A symmetric interval uses the corresponding absolute
error order statistic; this is not a test of Sharpe superiority.

Require at least 30 observations and 10 expected blocks (n/L). Constant paired
differences are unavailable because uncertainty cannot be estimated. Stationarity,
weak dependence and finite moments are assumptions, not effects of daily
aggregation. Structural breaks and long memory need separate assessment.

For the planned daily windows, register the deterministic rule
`L = max(1, floor(n^(1/3)))` before evaluation, with any fixed sensitivity
lengths declared alongside it. This yields feasible primary blocks at n≈90–180
while retaining the `n/L >= 10` guard. The L=20/10/40 settings below remain
illustrative development validation settings only and may not be chosen
retrospectively to minimize a p-value. The calibration study must include n=90
and n=180 before this rule is used for confirmatory claims.

## Independent validation study (registered configuration)

- Seed: 20260927; 300 replications per data-generating scenario.
- 1,200 paired observations, burn-in 300, 499 bootstrap resamples per replication.
- Difference process: stationary Gaussian AR(1), phi=0 and 0.6, unit marginal
  standard deviation scaled to 0.01; mean effects 0, 0.001, 0.002.
- Baseline: independent Gaussian mean-zero returns, SD 0.01; challenger adds
  the difference process. Pairing therefore includes a shared baseline shock.
- Block lengths 10,20,40; same replication seed across sensitivity settings.
- Comparator: paired IID centered bootstrap of the same differences (L=1),
  explicitly an invalid dependence assumption at phi=0.6, not confirmatory.
- Report binomial Wilson 95% intervals for every rejection rate/power estimate.
- Primary null gate: rejection <= 0.05 + 3*sqrt(0.05*0.95/300) = 0.08775
  at L=20, separately for each phi. The bound was chosen from Monte Carlo
  uncertainty before results. Report all sensitivity outcomes, even failures.
- Power gate: at effect 0.002, primary power > 0.80 at both phi settings;
  report the smaller effect without imposing a gate or tuning after inspection.
- Independent formula fixtures use high-precision mpmath CDF/inverse-erf,
  not the production normal-distribution implementation. Tolerance 1e-12.

Passing this finite study detects specified numerical/statistical failures; it
does not prove calibration for arbitrary financial return processes or H1.
