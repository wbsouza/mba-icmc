# Story 11 — Human acceptance procedure

Operate the analyzer as a researcher reviewing two completed strategy runs.
Use disposable copies of artifacts for malformed-input checks. Never edit a
raw run or frozen model to make an analysis succeed. Save the exact commands,
exit codes, output JSON, and input hashes with the validation evidence.

The selected contract is exact UTC midnight calendar-day equity endpoints and
paired stationary bootstrap resampling. See [method registration](method-design.md)
for inferential assumptions and simulation settings, and the analyzer README
for the explicit `inference-inputs.json` and selection-manifest schemas. This
document does not select settings from observed results. The executable pytest-bdd scenarios are the automated
acceptance specification; the checks below exercise the researcher-facing path.

The executable researcher check is [evidence/qa_cli.py](evidence/qa_cli.py).
Run `uv run python docs/stories/done/11-statistical-inference-corrections/evidence/qa_cli.py`
from `algo-suite` after the completed story is moved. Its archived
[qa-results.json](evidence/qa-results.json) contains 14 actual subprocess CLI
invocations, exit statuses, and outputs. Disposable fixtures use predeclared
expected block lengths 4 and 8, 199 draws, and seed 123. The script independently
evaluates DSR through `erf` and bisection, without importing analyzer code.
It checks the researcher path; library Gherkin tests and the separately archived
simulation study cover internal resampling structure and calibration.

## Preparation

1. Read the analyzer's CLI help and method contract. Identify the command for
   metrics, the default paired comparison, and the migration/inventory path.
2. Prepare two saved LEAN runs with actual timestamped portfolio equity,
   including open-position valuation, and identical pair and evaluation window.
   Give the runs different trade counts and ensure their equity-derived returns
   differ from their per-trade notional returns. Include genuine flat periods.
3. Prepare a documented selection history, including effective independent
   trial count and across-trial Sharpe dispersion for the multi-trial fixture.
   Keep a separate fixture explicitly registered as a single trial.
4. Record hashes of original artifacts. Declare bootstrap seeds, block settings,
   simulation sample sizes, effect sizes, and Monte Carlo tolerances before
   examining the corresponding analysis outputs.

## Researcher-facing checks

| Action | Required observable result |
| --- | --- |
| Request metrics for a valid run and complete selection inputs. | Versioned output separates descriptive headline Sharpe from `deflated_sharpe_probability`; the probability lies in [0, 1]. Return-source hashes, frequency, timezone, costs, risk-free convention, annualization, coverage, and selection provenance are auditable. |
| Change only the descriptive headline Sharpe or closed-trade count in a disposable fixture. | Inferential inputs and probability stay unchanged because they come from the same portfolio-return series. |
| Request metrics without selection history, then without required multi-trial dispersion. | DSR is explicitly unavailable with actionable reasons; neither case silently becomes a one-trial experiment. |
| Check the published-method fixture with a nonzero selection threshold. | DSR matches an independently calculated frozen value within the documented tolerance. The reference is not calculated by the production function. |
| Check registered single-trial fixtures. | SR equal to the zero threshold yields 0.5; a second nonzero-SR fixture matches independent PSR and does not return raw SR. |
| Increase independent-trial count while holding positive across-trial dispersion fixed. | The specified reference fixture's probability decreases. |
| Compare valid runs having unequal trade counts. | Comparison aligns actual portfolio returns by timestamp and succeeds when the declared history is adequate. Trade index and minimum array length do not define pairing. |
| Repeat the comparison with identical settings and seed. | Effect, interval, p-value, and method metadata reproduce. Output states the mean-return estimand, null, sidedness, resample count, block rule, observation/block counts, and assumptions. It makes no Sharpe-superiority claim. |
| Inspect resampling of a labeled synthetic paired series. | Each sampled pair uses the same original timestamp; within each sampled block the declared ordering is preserved. The default does not pool and shuffle individual trades. |
| Execute all predeclared sensitivity block settings. | Every setting and result is retained; no setting is selected because it gives the smallest evaluation p-value. |
| Analyze identical or constant-difference series and inadequate block history. | Explicit documented degenerate/unavailable behavior occurs; zero estimated variability does not manufacture confident evidence. |
| Remove an interior equity observation, duplicate a timestamp, insert a nonfinite value, or mismatch pair/window. | Each case is rejected or explicitly unavailable with a specific diagnostic. Missing history is never silently dropped or converted into flat returns. |
| Supply invalid counts, moments, variance, or selection parameters. | An actionable validation error occurs; there is no plausible-looking default statistic. |
| Inventory and, where inputs permit, reanalyze historical outputs. | Old fields remain identifiable as legacy/exploratory; new output has a distinct schema and probability field. Missing source/history is listed. Original artifact hashes remain unchanged. |

## Statistical and integration evidence

Run the predeclared simulation study on autocorrelated paired null series and
paired alternatives. Archive the configuration, seed, observed rejection rates,
Monte Carlo uncertainty, power at every specified effect size, and IID-method
comparison. Judge calibration against tolerances fixed before simulation; do
not require every seeded null realization to be nonsignificant. Inspect that
the confidence-interval construction and two-sided p-value target the same
estimand and null.

Reanalyze a completed six-month pilot run, or a saved representative LEAN run
if the pilot is unavailable. Preserve the exact command and output, including
unavailable-data diagnostics. This is an integration check and does not establish
profitability or H1. Rerun simulations only when the required source equity is
absent; correcting analysis alone does not require model retraining.

## Completion checklist

- [x] Return contract and published DSR reference are documented and reviewed.
- [x] Gherkin scenarios cover every observable case above and pass.
- [x] Analyzer `make check` passes; applicable backtest checks pass.
- [x] `make audit` is reviewed and its outcome recorded.
- [x] Cleaner complexity/coverage review and hardener mutation gate are recorded.
- [x] QA automation executes the researcher-facing procedure with deterministic
      pass/fail assertions rather than merely recording successful exits.
- [x] Independent formula and simulation evidence are archived with this story.
- [x] Real-artifact smoke output and legacy migration inventory are archived.
- [x] Analyzer SPEC/README/help, experiment plan, Chapter 4 deliverables,
      workflow/readiness, PRD, technical debt, and monograph agree with the code.
- [x] No DSR-probability cutoff uses Sharpe-scale bands such as values above 2;
      classical DSR's serial-dependence limitation remains explicit.
- [x] Manuscript build and citation/reference checks pass after LaTeX edits.
- [x] Trial variants and interim looks are retained; unrelated readiness work
      is not marked complete by this story.
- [x] Story and global plan are updated only after all required evidence passes,
      and the completed story is moved to `done` with links repaired.
