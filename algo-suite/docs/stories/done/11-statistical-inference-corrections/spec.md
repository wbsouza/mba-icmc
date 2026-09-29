# Story 11 — Correct DSR and time-series significance inference

**Status:** done, September 27, 2026.
**Priority:** high; blocks statistical-significance claims in Chapter 4.
**Tools:** `algo-analyze`; `algo-backtest` only where additional return artifacts
are necessary. Training and pilot simulations can continue independently.
**Related:** [Global plan](../../00-PLAN.md),
[experiment plan](../../../experiments.md), and
[Chapter 4 deliverables](../../../ch04-deliverables.md).
The six-month training pilot and broader experiment-readiness review are
separate work; this story owns the statistical corrections.

## User story

As the researcher comparing the baseline and hybrid Forex strategies, I want
selection-bias correction and significance testing to use the published DSR
statistic and preserve the paired, time-dependent structure of returns, so that
reported evidence does not confuse a Sharpe adjustment with a probability or
inflate confidence by treating dependent trades as independent observations.

## Problem and verified evidence

The September 26 scientific review used the `experimental-design` and
`scientific-critical-thinking` skills and inspected the implementation. It found
these issues; this story records fixes, not a completed validation of H1.

1. `algo-analyze/src/algo_analyze/deflated.py::deflated_sharpe` returns
   `observed_sharpe - standard_error * expected_max_z`, and returns the observed
   Sharpe unchanged for one trial. For example,
   `deflated_sharpe(observed_sharpe=2, n_returns=100, n_trials=1)` returns `2`.
   This is not the probability-valued DSR in Bailey–López de Prado (2014), Eq. 2.
   Existing `deflated_sharpe.feature` scenarios encode the incorrect no-op
   single-trial contract; passing those tests does not validate the statistic.
2. `cli.py::metrics` combines LEAN's headline Sharpe with the number of closed
   trades, assumes skewness 0 and kurtosis 3, and defaults to one trial. It does
   not establish that Sharpe, sample count, and moments describe the same return
   series and frequency. Nor does it supply the across-trial Sharpe dispersion
   needed for the selection threshold.
3. `significance.py::mcp_test` pools the two trade-return samples and shuffles
   individual observations. This requires exchangeability that has not been
   established for these strategies. It discards market-time pairing and serial
   dependence; different holding periods and trading frequencies further change
   the sampling units. The concern is an unsupported inference assumption, not
   proof that every existing p-value is numerically wrong.
4. `figures.py` compounds per-trade notional returns and explicitly distinguishes
   them from portfolio equity. That trade-sequence curve must not be reused as
   a calendar-time portfolio-return source for this fix.
5. `docs/experiments.md` and the analyzer CLI apply Sharpe-scale bands, including
   values above 2, to the field called deflated Sharpe. Those bands cannot apply
   to a probability in [0, 1]. Related specs and monograph claims need migration.

## Scope and implementation contract

### A. Establish one auditable return-series contract

Read or emit timestamped portfolio equity and derive net portfolio returns on a
specified common time grid. Use actual engine equity, including open-position
valuation; closed-trade notional returns are not a substitute. Record source,
frequency, timezone, costs, risk-free convention, annualization factor, and
coverage. Both strategies must cover the same pair and evaluation period.

Align observations by timestamp, never by trade index or truncating arrays to
the shorter length. Keep genuine flat/no-position periods when the recorded
portfolio equity supports them; distinguish these from missing observations.
Unexpected gaps, duplicates, nonfinite values, or inadequate history must fail
with an actionable diagnostic or an explicitly unavailable statistic. Do not
silently fill missing market history with zero returns.

Headline annualized Sharpe may remain a separately labeled descriptive output.
All inputs to inferential calculations must use a consistent, documented
frequency and sample definition.

### B. Implement the published DSR probability

Implement Bailey–López de Prado (2014), Eq. 2, with a normal CDF, a documented
selection threshold, and consistently measured sample moments. In compact form:

`DSR = Phi((SR - SR0) * sqrt(T - 1) /
           sqrt(1 - skew * SR + (kurtosis - 1) * SR^2 / 4))`

Use nonannualized SR and Pearson kurtosis. The multi-trial threshold uses
across-trial Sharpe dispersion and the effective independent-trial count; do
not substitute a single strategy's standard error for that dispersion. Record
how these inputs were measured or explicitly supplied. For one registered trial
with a zero reference threshold, compute PSR against zero, not raw Sharpe.

Estimate moments from the selected return series with a stated estimator, or
accept explicit validated moments with provenance. An optional normal-moment
assumption must be labeled, not silently adopted. Reject invalid variance,
nonfinite values, invalid counts, and insufficient observations. If selection
history or dispersion is unavailable, report DSR as unavailable and explain the
missing inputs; do not invent a one-trial experiment.

The classical expression alone does not establish validity under arbitrary
serial dependence. Document its assumptions and keep any dependence-adjusted
extension distinct and independently validated. Correct DSR output must not be
advertised as solving the time-series uncertainty problem by itself.

### C. Replace the default pooled-trade test for strategy comparisons

Use paired, aligned calendar-time net portfolio returns. Define the estimand,
null hypothesis, sidedness, statistic, and resampling assumptions before
implementation. The existing mean-difference question can be retained on this
new sampling basis; it must not be described as a test of Sharpe superiority.

Select and document a dependence-aware method, such as a paired moving-block
or stationary bootstrap with an appropriately null-centered construction.
Preserve pairing by resampling corresponding time blocks together and retain
within-block order. If a block permutation or sign procedure is selected
instead, justify its exchangeability or symmetry assumptions explicitly.
Cite the primary methodological source for the selected method. Renaming the
existing shuffle or grouping rows arbitrarily does not satisfy this criterion.

Record block length/selection rule, sample interval, resample count, seed,
number of observations and blocks, and the method's validity assumptions.
Choose block settings from a declared rule or development data, not whichever
setting yields the smallest evaluation p-value. Check sensitivity over a
predeclared small set of block lengths. Provide an effect estimate and a
compatible confidence interval with the p-value. Define how insufficient
blocks and degenerate samples are handled; do not imply independence merely
because observations were aggregated to daily frequency.

An IID permutation implementation may remain only as an explicitly named,
opt-in method whose independence/exchangeability assumptions are documented.
It must not be the default inference path for the baseline/hybrid backtest.

### D. Migrate reporting and existing artifacts honestly

Version the corrected analysis output. Use unambiguous names such as
`deflated_sharpe_probability`, retain the descriptive Sharpe separately, and
publish method/input provenance and unavailable-statistic reasons. Do not
silently change the meaning of an existing field consumed by reports.

Preserve historical analysis artifacts. Mark the former Sharpe adjustment and
pooled-trade p-values as legacy/exploratory, regenerate analysis when adequate
source data and search history exist, and list results that cannot be corrected.
Model retraining is not required merely to correct analysis; rerun a simulation
only if its artifacts lack the required portfolio series.

Update `algo-analyze/SPEC.md`, CLI help/README, `docs/experiments.md`,
`docs/ch04-deliverables.md`, the workflow/readiness checklist, `PRD.md`, technical
debt, and the monograph's evaluation/significance descriptions. Remove claims
that Sharpe-scale plausibility bands are DSR-probability cutoffs. Retain the
actual number of tried variants and interim looks; two published runs need not
mean only two search trials.

## Acceptance criteria — Gherkin/pytest-bdd

1. **Published-method reference:** Given an independently calculated,
   source-documented fixture with a nonzero selection threshold, the DSR
   probability matches a frozen reference within a justified tolerance.
   Expected values must not be generated by the production function itself.
2. **Single-trial semantics:** Given one registered trial and SR equal to the
   zero reference threshold with valid variance, DSR equals 0.5. Given other
   valid single-trial inputs, it equals independently calculated PSR, stays in
   [0, 1], and is not a raw-Sharpe no-op.
3. **Selection inputs:** Increasing independent-trial count with fixed positive
   across-trial dispersion lowers DSR on a specified fixture. Missing selection
   history or dispersion produces an explicit unavailable result, not invented
   defaults. Invalid moments/counts and zero variance produce clear diagnostics.
4. **Frequency consistency:** All inferential inputs come from the same recorded
   return series/frequency. A fixture distinguishes portfolio returns from
   per-trade notional returns and catches mixing annualized SR with trade count.
5. **Alignment and coverage:** Unequal trade counts do not prevent matching
   calendar-time portfolio returns. Missing timestamps, duplicates, incompatible
   windows/pairs, and unexplained gaps cannot be silently dropped or zero-filled.
6. **Dependence and pairing:** On a labeled synthetic series, the resampling
   indices preserve paired observations and within-block order. Fixed inputs,
   seed, and settings reproduce the same output and method metadata.
7. **Independent statistical validation:** A predeclared simulation study uses
   autocorrelated null series and paired alternatives. Report rejection-rate
   uncertainty and power across specified effect sizes; compare to the IID
   method without requiring every seeded null case to be nonsignificant.
   Set tolerances from Monte Carlo uncertainty before seeing results. Include
   zero-difference, insufficient-block, and degenerate-series cases.
8. **CLI and migration:** Corrected CLI outputs probability, separate headline
   Sharpe, effect/interval, inference settings, and source hashes. Old output is
   identifiable and never relabeled as corrected. No rule compares DSR to 2.
9. **Real-artifact smoke test:** Reanalyze available six-month pilot runs after successful
   completion, or exercise saved representative LEAN artifacts if runs are not
   ready. Preserve exact commands and unavailable-data diagnostics. This proves
   integration, not profitability or rejection of H1's null hypothesis.

## Out of scope

CPCV/rolling-retraining orchestration, GDELT publication-date leakage repair,
feature/detector implementation, empirical execution-cost redesign, DSHA model
training, strategy tuning, and a claim that one month establishes H1. These
remain requirements of the broader experiment-readiness review; this story must not silently mark them complete.

## Definition of done

- Review and document the return basis, DSR reference fixture, and resampling
  method before treating corrected outputs as inferential evidence.
- Implement both statistical corrections and their CLI/artifact integration.
- Pass Gherkin acceptance scenarios, the analyzer's `make check`, relevant
  backtest checks if its artifacts change, and review `make audit`.
- Archive the independent formula checks and simulation-study configuration,
  results, seed, and uncertainty assessment with this story.
- Update all affected contracts and manuscript claims; run manuscript build and
  citation/reference checks after LaTeX changes.
- Reconcile old analysis outputs without overwriting raw runs or frozen models.
- Update `00-PLAN.md` and the experiment-readiness review. Mark done only when the two corrections and
  reporting migration are verified, not when the implementation merely runs.

## Sources and review provenance

- Bailey, D. H., and López de Prado, M. (2014),
  [The Deflated Sharpe Ratio](https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf),
  Eq. 2, pp. 8–9 of the author manuscript. This governs the DSR definition;
  existing project tests are not an independent scientific reference.
- [scikit-learn TimeSeriesSplit documentation](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html)
  supports chronological evaluation; it is not a specification of block
  resampling or CPCV.
- Scientific review assisted by `experimental-design` and
  `scientific-critical-thinking` from Kassis, T., Agarwal, V., He, Y., Patel, D.,
  and Brueckner, A. M. (2026),
  [Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents](https://doi.org/10.48550/arXiv.2609.00065).
  Author/year metadata verified against the current arXiv record. These skills
  structure the review; they do not independently validate the trading results.
