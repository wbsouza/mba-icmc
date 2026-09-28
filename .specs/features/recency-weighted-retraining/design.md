# Adaptive recency-weighted training design

Status: draft for review. [Requirements](spec.md), [decisions](context.md).
Planning only. The requested full consume/train/use cycle is in scope.

## Architecture Overview

Use a host-side coordinator with an explicit data-availability clock. It owns
ingestion, label maturity, retraining triggers and immutable publication.
LEAN owns orders, account state and on-demand model loading. Do not put a
training library or a network model service in the trading callback.

```text
Local market data -> validated watermark -> pending/mature labeled observations
                                              |
Registered refresh boundary -> fit -> validate -> publish immutable bundle
                                              |
                     on-demand loader -> future F7 decisions -> audit
                                              |
                   existing account and protective orders remain continuous
```

This is a full adaptive-cycle contract, not just a weight parameter on a
one-time fit. Monthly cadence is the first proposed policy; a configurable
schedule does not mean arbitrary unregistered adaptive triggers.

Alternative: run fitting inside LEAN at boundaries. That delivers the same
cycle but duplicates training dependencies and complicates timeout/latency
handling. Recommended separation is provisional until interface feasibility
is verified. No currently working native pause/host-training API is claimed.

## Baseline and code reuse

Paths below are relative to algo-suite.

| Component | Existing source | Proposed use |
| --- | --- | --- |
| Causal features/labels | algo-backtest/src/algo_backtest/training.py:311 | Reuse canonical signals and label_time; expose closed-bar availability explicitly. |
| Chronological split | algo-backtest/src/algo_backtest/chain/filters/f7_meta_learner.py:180 | Preserve old date-based API; new exact-UTC epoch splitter applies stricter boundaries. |
| Family fit | algo-backtest/src/algo_backtest/chain/filters/f7_meta_learner.py:328 | Add optional sample weights without changing omitted-weight behavior. |
| Combiner fit | algo-backtest/src/algo_backtest/chain/filters/f7_meta_learner.py:264 | Apply independent stage weights to out-of-sample family scores. |
| Portable artifacts | algo-backtest/src/algo_backtest/chain/filters/f7_model_io.py:89 | Wrap existing JSON model in a validated epoch bundle. |
| Native lifecycle | algo-backtest/src/algo_backtest/engine/chain_algorithm.py:160 | Replace startup-only model choice with an optional lazy provider. |
| Protection | algo-backtest/src/algo_backtest/engine/chain_algorithm.py:361 | Preserve minute management and calendar PnL ordering. |
| Statistical reporting | algo-analyze/src/algo_analyze/reports.py | Reuse strict daily-equity alignment and paired stationary bootstrap. |

Existing session-2 registration is in PR 74 at commit 4be718a, under
algo-suite/docs/stories/in-progress/15-session-2-clean-rerun/registration.md.
It is not yet in this checkout. Reference its immutable source; do not assume a
merge or copy its simulation output into new evidence.

## Proposed study matrix

One strategy configuration: session-2 H1 q10 price-only, EUR/USD. T1 must resolve
the exact config and data hashes. Keep all filters, candle/activity switches,
capital, brokerage/costs, exits and sizing identical across the five policies.

| ID | Family and combiner fitting | Thresholds |
| --- | --- | --- |
| F | Fit initial expanding uniform model once, then freeze | Freeze initial q10 thresholds |
| Q | Same exact initial model as F | Refresh q10 monthly |
| R | Refit monthly, uniform trailing 180-day family span | Refresh q10 monthly |
| U | Refit monthly, uniform expanding family span | Refresh q10 monthly |
| E | Same row support as U, exponential weights with 60-day half-life | Refresh q10 monthly, unweighted |

E versus U isolates recency weighting. R versus U measures history truncation;
Q versus F isolates threshold updates. F and U share the first bundle.
The old archived session-2 model is an external historical reference, not a
matched control: this study separates combiner fitting and threshold selection.

Budget: five policy configurations and five continuous year-long backtests.
A twelve-month schedule has at most 36 distinct model fits (initial shared F/Q/U,
11 later U fits, 12 R and 12 E fits), with duplicate artifacts reused. Retries
are logged attempts, not new independent evidence. No half-life sweep, hidden
extra seed, early efficacy stopping or strategy expansion without amendment.

## Exact proposed temporal contract

Let D be the UTC first-of-month deployment boundary and C = D minus one day.
For each adaptive epoch:

- Family fit ends at C minus 60 elapsed days; R starts 180 days before that end,
  while U/E start at 2015-03-02 00:00 UTC.
- Combiner span is [C-60 days, C-30 days).
- Threshold span is [C-30 days, C).
- Deployment is [D, next month's D); initial March 2016 to March 2017 exclusive.

Assign rows by feature availability (bar close), not their stored bucket-start
timestamp. Require label_time < the end of the assigned fitting/calibration span.
Do not assume a null label_time means instant maturity in this new path.
Keep earlier bars for causal indicator warmup, but do not fit excluded rows.
An outcome must never leak across a fitting/calibration/deployment boundary.
Past-only feature history can overlap across boundaries; that is not permission
to include future labels or fitted transforms. Fit preprocessing on fitting data.

All eligible observations are used, including observations where the strategy
would veto an entry. Trade profits and executed-trade selection do not define
training eligibility. Current labels predict price direction, not trade profit.

Raw weights are w_i = 2^(-(cutoff - available_at_i)/86400/h).
Normalize separately per family-fit and combiner-fit span:
w'_i = n*w_i/sum(w). Thus regularization is not inadvertently changed simply by
shrinking total weight. Record n_eff = sum(w)^2/sum(w^2); it describes weight
concentration, not independent observations or statistical power.

Reject non-finite, negative-age, non-positive half-life, unrepresentable or
zero-total-weight configurations rather than silently changing the half-life.
Use numerically stable relative exponents where necessary; test the analytic
half-life ratios and normalized-weight identities. Retain raw-weight summaries.

No time weights on threshold quantiles in this first comparison. Use separate
q=0.10/0.90 linear empirical quantiles and existing strict BUY/SELL inequalities.
The combiner is learned probability combination, not guaranteed calibration;
report Brier score/calibration diagnostics rather than claiming calibrated output.

## Components and data models

New paths below are proposed components in
algo-backtest/src/algo_backtest/retraining/, not existing APIs.

| Component | Contract |
| --- | --- |
| ingestion.py | Validate keyed source batches; persist monotonically advancing availability watermark and pending/mature label state. |
| schedule.py | Produce ordered epoch spans and row membership without reading outcomes from later spans. |
| weights.py | Produce uniform/exponential row-aligned weights and feasibility summaries. |
| bundle.py | Publish/validate immutable model+threshold+provenance bundle using existing portable model IO. |
| thresholds.py | Compute separate-span quantiles with explicit ties/failure behavior. |
| trainer.py | Build one epoch using only cutoff-visible data; never require future test labels to fit. |
| cycle.py | Consume -> mature -> fit -> validate -> publish, idempotent per policy/boundary. |
| provider.py | Load eligible bundle on demand, atomically switch model+threshold pair, bounded cache (proposed capacity 2). |

A CycleRequest includes policy ID, protocol hash, cutoff, requested activation
boundary, source watermark and prior registry identity. An EpochBundle includes
all span bounds, seed/runtime/library versions, model/config/data/row hashes,
feature-family order, stage weight parameters/counts/n_eff, actual thresholds,
training duration and publication/activation event times. Preserve real wall
timestamps separately from simulated timestamps.

A cycle ID is content-addressed by immutable inputs and policy. Identical retry
returns the same published artifact. Conflicting content is a failure. Temporary
files remain unpublished until validation and atomic rename complete. A failed
cycle has no eligible manifest. The active bundle stays pinned in cache; evict
only inactive deserialized models, never immutable artifact files.

## Native coordination and future-only activation

Replay may request a cycle when simulated time reaches its preparation boundary.
A local run-scoped request/response exchange with the host coordinator can pause
historical event advancement while fitting. Validate feasibility against the
actual Docker/LEAN lifecycle before committing to its mechanics. Bound the wait
with an explicit registered timeout and record every failed request. Do not
invent a hot-reload API or call an unbounded worker from on_data.

The historical clock resumes only after validation. Activation is no earlier
than D, on the first subsequent eligible decision event; no earlier prediction
is rewritten. Wall-clock fitting delay is reported, and this idealized replay
barrier is explicitly not proof that training finishes within a live deadline.
Live late-model handling and broker recovery remain out of scope.

One LEAN process/account per policy spans all months. Switch only the provider's
model/threshold pair. Do not reconstruct F5/F6, indicators, PnLWindows or existing
positions. Existing orders continue on the minute callback before entry
evaluation. New model decisions may affect behavior only under the unchanged
registered exit/veto policy; the swap itself never closes a trade.

Immutable prepared-cycle replay is a secondary reproducibility path. It must
match causal-cycle decisions but does not replace tests of ingestion, training
triggers, request failure and on-demand loading.

## Failure and audit

Preflight checks manifest structure, registered coverage and source availability.
Do not deserialize every future model during preflight. At activation, verify
hashes, signal/family contracts and timestamps. Missing or invalid responses stop
the backtest with a failed-attempt artifact, not a last-good-model fallback.
Never equate this backtest stop with safe recovery on a live account.

Decision records identify current epoch and entry epoch separately. Run manifests
list every filter's effective parameters, including disabled filters, plus all
refresh settings and model versions. Preserve old schemas and single-model runs.

## Analysis and monograph

Proposed primary endpoint: mean paired UTC-daily net return difference E-U,
over common full-year endpoints. Primary stationary block length 4 days,
sensitivity 2 days, 9999 resamples, seed 42, two-sided alpha 0.05; T1 checks the
current analyzer contract and n >= 10L feasibility before freezing these values.
Do not treat monthly epochs or overlapping trades as independent samples.

Secondary comparisons R-U and Q-F are descriptive. Report all five policies:
net return, drawdown, trade count, win rate, average win/loss, expectancy in
money and initial-risk units where defined, turnover/costs, veto reasons,
prediction quality and monthly/model-age diagnostics with sample counts.
Weight effective N is not a correction for serial dependence.

This is a matched historical simulation, not randomized causal evidence or a
power-certified study. Prior inspected periods remain exploratory. A genuinely
unseen period is needed for a later confirmatory evaluation; repeated seeds
on this same price path are not new market replications.

T17 updates Chapter 3 with methodology and limitations before experiments.
T18 records executed evidence and failures. T19 updates Chapter 4 only from
verified artifacts. No results or profitability claims are written this turn.

## Risks & Concerns

| Concern | Location | Impact | Mitigation |
| --- | --- | --- | --- |
| Date-only split and optional label_time | f7_meta_learner.py:150 | Boundary leakage under intraday refresh | T3 exact-UTC splitter; reject missing maturity in adaptive path. |
| Bucket-start TrainingRow timestamp | training.py:380 | Artificially early availability | T2/T3 explicit close time and prefix tests. |
| Trainer requires test span in old split structure | f7_meta_learner.py:180 | Future-data dependency in preparation | T9 training-only orchestration; retain old API compatibility. |
| Single startup model, stateful chain | chain_algorithm.py:160 | Accidental reset during reload | T11/T12 replace only provider; native open-position fixture. |
| Stage weights absent | f7_meta_learner.py:306 and :336 | One stage ignores recency | T5/T6 direct argument probes plus real fitted examples. |
| Same-bar OCO defect | docs/technical-debt.md TD-71 | Invalid trade evidence | Mark affected candidates failed; never patch results or change costs mid-study. |
| Existing evaluation dates inspected | PR 74 registration/results | Selection bias | T1/T16/T19 exploratory labels and no holdout claim. |
| Host synchronization not established | chain_algorithm.py:361 | Deadlock or late activation | T10/T12 bounded protocol tests; stop for design review if native handshake is infeasible. |

## API sources

Both existing fitting libraries expose sample_weight; verify installed locked
versions before implementation rather than upgrading by assumption:
[LightGBM classifier](https://lightgbm.readthedocs.io/en/stable/pythonapi/lightgbm.LGBMClassifier.html)
and [scikit-learn logistic regression](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html).
The experimental-design skill guided control selection and the distinction
between repeated measurements and independent replication. No market success
claim is derived from these software references.
