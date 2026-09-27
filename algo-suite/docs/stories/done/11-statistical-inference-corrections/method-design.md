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
- 1,200 paired observations (original study; see the registered extension below
  for 90 and 180), burn-in 300, 499 bootstrap resamples per replication.
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
  Six fixtures: the five archived on September 27 plus the acceptance-suite
  constant (SR 0.2, T 100, skew 0, kurtosis 3, N 10, dispersion 0.1).

### Extension registered September 27, 2026 (review follow-up), before execution

- Purpose: size and power evidence at the window lengths the thesis can
  actually observe, under the deterministic rule `L = max(1, floor(n^(1/3)))`.
- Scenarios: n = 90 (L = 4) and n = 180 (L = 5); phi 0 and 0.6; mean effects
  0, 0.001, 0.002; same difference process, baseline, burn-in 300, 499
  resamples, 300 replications, seed construction `SeedSequence([20260927,
  scenario_index])` with scenario indices 6–17 so the original six scenarios
  reproduce unchanged.
- Settings evaluated per scenario: the rule length and the IID comparator L = 1.
- Gate: null rejection at the rule length <= 0.08775 for each (n, phi).
  Power is reported with Wilson intervals and is not gated: at n = 90 the
  standardized mean effect 0.002 / (0.01 / sqrt(90)) is about 1.9, so power
  near 0.5 is expected and would not be a software failure.
- The original n = 1200 rows keep their L = 20 primary gates.

Result (recorded after execution, September 27, 2026): the n = 1200 rows
reproduced exactly; the six formula fixtures passed; the `floor(n^(1/3))` rule
passed the null gate at phi = 0 (5.67%, 6.67%) and **failed** it at phi = 0.6
(13.67% at n = 90, 10.67% at n = 180). This is a genuine under-coverage of short
blocks, not a software defect: a stationary bootstrap with expected block length
L captures roughly `1 - 2*phi / ((1-phi)^2 * L * ((1+phi)/(1-phi)))` of the AR(1)
long-run variance, which predicts sizes near 15%, 12% and 6.3% for L = 4, 5, 20
under phi = 0.6, matching the observed 13.7%, 10.7% and 7.0%. The
`floor(n^(1/3))` rule is therefore **not** registered for confirmatory use at
90–180 observations.

### Second candidate rule, registered before execution (same day)

- Rule: the maximal feasible expected length under the ten-block guard,
  `L = max(1, floor(n / 10))`: 9 at n = 90, 18 at n = 180. Motivation: the
  bias expression above predicts sizes near 8.3% (n = 90) and 6.4% (n = 180)
  under phi = 0.6, and the Politis–White optimal length for phi = 0.6 is
  several times `n^(1/3)`, so the guard, not the cube root, is the binding
  constraint at these window lengths.
- Everything else as in the first extension; scenario indices 18–29 so both
  extension studies and the original study reproduce independently.
- Gate: null rejection <= 0.08775 at the rule length for each (n, phi). Power
  reported, not gated. Both extension studies are reported whatever the outcome;
  neither may be cited without the other.

Result (recorded after execution, same day): `floor(n/10)` **failed** the null
gate everywhere: 10.00% (n = 90, phi = 0), 14.00% (n = 90, phi = 0.6), 9.33%
(n = 180, phi = 0) and 9.33% (n = 180, phi = 0.6). With only ten expected
blocks the bootstrap distribution of the mean is itself too narrow, so the
guard, not the dependence, dominates at these window lengths. All 21,600
p-value/interval decisions remained coherent.

### Conclusion for the thesis windows (no further rule will be tried)

At 90–180 daily observations, no expected block length admissible under the
ten-block guard was size-calibrated for this procedure in this design, under
phi = 0 (maximal length) or phi = 0.6 (both rules). Confirmatory paired
inference therefore requires either a materially longer evaluation window
(the registered n = 1200, L = 20 setting passed at 6–7%) or a second-order
accurate procedure such as a studentized bootstrap-t or a fixed-b HAC t-test
(technical-debt TD-62, now `ready`). Two prospectively registered rules were
evaluated and both are reported; a third rule chosen after seeing these
results would not be a registered rule. `validate_inference.py` exits nonzero
because a registered gate failed; that exit status is the honest record.

Passing this finite study detects specified numerical/statistical failures; it
does not prove calibration for arbitrary financial return processes or H1.
