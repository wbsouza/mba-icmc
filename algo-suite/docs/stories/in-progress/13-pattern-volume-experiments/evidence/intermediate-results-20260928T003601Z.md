# Intermediate results: frozen read-only snapshot

Evidence collected from 2026-09-28T00:36:01.988Z through
2026-09-28T00:36:02.274Z; clock tool confirmation:
**2026-09-28 00:36:01 UTC** (September 27 in America/Vancouver).

This is an exploratory intermediate report. Later completion of active jobs
does not change this snapshot. No source run was restarted, killed, regenerated,
or edited. The candidate Story 13 candle/quote-activity experiment is not part
of these predecessor results.

## Evidence and joins

- [Frozen JSON snapshot](snapshot-20260928T003601Z.json): artifact contents,
  source paths, SHA-256 hashes, job scripts/status/log excerpts, model metadata,
  and live-process evidence.
- [Per-run result and F1–F7 parameter appendix](per-run-parameters-20260928T003601Z.md):
  every run R01–R20 joins its result to its own effective configuration, model,
  manifest hash, and field provenance. F01 is the failed historical launch;
  P01 is the planned November hybrid.
- [Chapter 04](../../../../../../monografia/chapters/04-experimental-evaluation.tex)
  and [Chapter 05](../../../../../../monografia/chapters/05-conclusion.tex)
  carry the narrow intermediate-results update.
- [Figure generator](render_intermediate_figures.py) and
  [BDD feature](tests/features/intermediate_figures.feature) are confined to this
  evidence directory. They add no dependencies and do not write to source runs.
- [Verification record](verification-20260928.md),
  [figure hashes and input groups](figure-provenance-20260928T005036Z.json), and
  [later runtime-resource intervention](runtime-resource-addendum-20260928T004916Z.md)
  document checks and the separate operational addendum.

The primary source root is
`/home/wellington/workspace/mba-agents/mba-main/algo-suite/data/training/`.
The old result root is
`2026-09-26-six-month-pilot/data/runs/`; annual-protocol runs are under
`2026-09-28-one-year-protocol/data/runs/`.

All 14 archived JSON/YAML configuration pairs were parsed and compared:
they agree. Four historical runs (R06/R07/R11/R12) lack configuration YAML
and parameter provenance. Two running runs (R10/R19) lack configuration
JSON/YAML, although provenance filenames exist. Missing effective values
remain **missing**. A current default or another run's descriptor never fills
these gaps. Every present engine model hash matches its job-selected model.
The manifest's `inference_inputs_sha256` is **not** a model hash.

The compact monograph table covers every filter; the appendix includes all
archived F1–F7 fields, shared execution fields, and missing-field lists for
each run, plus complete raw configurations/provenance in JSON.
Archived leverage-related fields are preserved as configuration data only;
they support no claim about effective leverage or the cause of losses.

## Job status at the snapshot

| Job | Completed manifests | Active or pending | Execution revision |
| --- | --- | --- | --- |
| 2026-09-27-f7-ungated-september | R07, R12 successful | none | 709b9bd4bdcf75731a785b97d1a3055884d61e35 plus recorded uncommitted changes |
| 2026-09-27-execution-realism | R08/R13 September; R09/R14 October successful | R10 baseline November running; P01 hybrid November not started | 7165308778fd650a7474824ae03cd043cefe9e97 |
| 2026-09-27-variant-sweep-sept | R01/R03/R04/R05 successful | R02 gated running | 7165308778fd650a7474824ae03cd043cefe9e97 |
| 2026-09-27-variant-sweep-sept-b | R15–R18 successful | none | 7165308778fd650a7474824ae03cd043cefe9e97 |
| 2026-09-28-one-year-protocol | both training artifacts saved; no successful final replay manifest | R19/R20 simulations running | 7165308778fd650a7474824ae03cd043cefe9e97 |

Including historical R06/R11, there are **16 successful final manifests,
zero failed final manifests, and four running runs without final manifests**.
The separate initial launch F01 failed on missing `broker.adapter`; the
failure log and its hash are archived, without inventing a run ID or result.
A successful execution can lose money or trade zero times.

Both sweep scripts and the annual script use bare `wait`, which does not
propagate each background child's failure as a checked per-child result.
The template-sweep status string also says five variants, although the loop launches
four. Neither that string nor `exit_code=0` is treated as a result manifest.
Every completed row here was individually checked for `run.json.success=true`.
An incomplete directory or an engine `main.json` is insufficient.

## Observed completed results

Return and drawdown are the stored `metrics.json` values converted to percent;
closed trades come from `run.json`. These are engine-reported summaries,
not a fresh economic reconciliation or corrected statistical inference.

| Runs / window | Closed trades baseline / hybrid | Return baseline / hybrid | Max DD baseline / hybrid |
| --- | --- | --- | --- |
| R07/R12 ungated September 2015 | 1,032 / 1,069 | -0.05% / +0.51% | 1.5% / 1.5% |
| R08/R13 execution model September 2015 | 320 / 322 | -52.57% / -52.75% | 53.8% / 54.0% |
| R09/R14 execution model October 2015 | 319 / 349 | -53.35% / -51.37% | 55.2% / 53.3% |

The eight completed sweep returns are R01 -0.81%, R03 -55.28%,
R04 -3.76%, R05 -17.65%, R15 -53.47%, R16 -42.16%, R17 0.00%,
and R18 0.00%. R17/R18 each have zero trades; R02 is still running.
See the appendix for each full run ID, all filter parameters, and result hash.
Losses and zero-trade cases are retained without selecting a favorable subset.
No annual performance or November result is reported.

## Model identity and reproducibility

| Model ID | SHA-256 of actual model bytes | Recorded training revision |
| --- | --- | --- |
| `2026-09-26-six-month-pilot/baseline` | `1a6fd37e96dee3a6f5d082c18afdf863909524636718d129f44eac8d6e4e831e` | `37b756a48695c317160f7a323175bfdbe6c8d9d7` |
| `2026-09-26-six-month-pilot/hybrid` | `a6dda4c2effc55868d7c4131b90c3343b624c6ae0432dd24903590f5306af9b7` | `37b756a48695c317160f7a323175bfdbe6c8d9d7-dirty` |
| `2026-09-28-one-year-protocol/baseline` | `0b41fd39ebf3f37e136e8a7f7a07500f139ee90e675eb7571b866aa7138ae431` | `7165308778fd650a7474824ae03cd043cefe9e97` |
| `2026-09-28-one-year-protocol/hybrid` | `b67ac32e1fc5a6cb9699b7ab96d770f84991c246a5a0b5977f481deb245f63e7` | `7165308778fd650a7474824ae03cd043cefe9e97` |

The pilot and annual training windows are distinct. Pilot fitting ends
June 2015 and combiner calibration ends July; annual fitting ends December
2015 and calibration ends January 2016. Model provenance preserves exact
splits, row counts, packages, and input hashes. The hybrid pilot training
revision is explicitly dirty, and the ungated replay also records a dirty
worktree. A Git hash without the missing patch cannot reproduce that state.

The inspected execution worktree `/tmp/mba-story12` was clean at revision
`7165308778fd650a7474824ae03cd043cefe9e97`. Source hashes for the inspected
wiring and engine are in `snapshot.execution_source`.
The Claude chapter prewrite `/tmp/mba-ch04` at
`ad227e9a93603d870504d4dc6a7c3c50c6a77d91` was inspected read-only.
It was not copied or overwritten. Its pending annual figures and language
about untouched 2016 data are not evidence of a completed experiment.

## Anti-alignment and selection history

In January calibration, baseline upward-direction mean probability is 0.4791
in bull regimes and 0.5149 in bear regimes; hybrid is 0.4794/0.5148.
At 0.55/0.45 thresholds, each gated model produces only two sell signals;
ungated counts are 1,242 baseline and 1,125 hybrid, with recorded label hit
rates 0.569 and 0.564. These are diagnostic, overlapping fifteen-minute
label observations, not independent trade outcomes.

The calibration script's actual dates override its stale July/August docstring:
it reads January **and February 2016**, with eight threshold pairs, two gate
settings, two models, and two partitions (64 recorded combinations).
February remains excluded from fitting but has been inspected diagnostically.
The code comment claiming the grid never uses 2016 data is false.
There is no claim here that all 2016 data remain untouched.

Anti-alignment does not establish a mechanism for the observed losses, a
profitable reversed signal, or the value/absence of news. September has been
reused for diagnosis, gate and execution changes, and nine named variants.
All such choices, plus inspected threshold grids and any future revisions,
belong in the exploratory selection history. The 64 grid entries are not
asserted to be an effective independent-trial count for DSR.
No paired test, DSR, confidence interval, rolling retraining, or CPCV result
is calculated here. Historical pilots are not promoted to OOS confirmation.

## The reference templates versus the M1 adaptations

The reference is the author's Spring version
(unpublished). Its template settings are recorded as YAML values in the
experiment plan; the snapshot embeds no copies of its configuration files.

| Aspect | Reference template | Inspected sweep evidence |
| --- | --- | --- |
| Timeframe | selector period 60 (H1); deployment templates period 240 (H4) | M1 inputs and EMA perception; 60-period minute EMA is not an H1/H4 bar series |
| Stop cut | selector stop cut 20 %; deployment templates 50 % | template-derived variants use `stop_loss_shrink=0.5` |
| Entry and stop signal | the templates' indicator buffers and trend/bias rules | predecessor EMA/F7 chain; no actual candle detector or quote-activity gate |
| ATR variant R16 | no proof of an equivalent H4 setting | archived multiplier 4.0, shrink 0.5, minimum 10 pips, risk 0.01; comment says 2 x ATR14 |

The comparison is a partial plan adaptation, not a reproduction of the full
reference system. No inference about the Spring version's profitability follows.
The legacy F3 names in the configurations coexist with
`candlestick_pattern=None` in the inspected predecessor wiring.

## Figures and reproduction

The user-requested
[trading-visualization skill](https://raw.githubusercontent.com/agiprolabs/claude-trading-skills/main/skills/trading-visualization/SKILL.md),
[chart recipes](https://raw.githubusercontent.com/agiprolabs/claude-trading-skills/main/skills/trading-visualization/references/chart_recipes.md),
and [styling guide](https://raw.githubusercontent.com/agiprolabs/claude-trading-skills/main/skills/trading-visualization/references/styling_guide.md)
were read fully. Only their software presentation guidance is adapted:
Matplotlib equity/drawdown panels in a 2:1 ratio, a dark screen palette,
shared date axis, explicit labels, and export styling. They supply no
performance claims or market data.

The generator reuses `algo_analyze.equity.read_equity_csv`,
`algo_backtest.statement.drawdowns`, and the existing thesis plotting style.
Each input manifest, metric, configuration, and CSV is hash-checked against
the frozen snapshot before plotting. It uses only real, completed source
runs and preserves all observations without interpolation, resampling,
monthly chaining, synthetic data, or changing the original run directory.
Drawdown is plotted as negative percent below the sampled running peak;
engine maximum drawdown can differ due to sampling/rounding.

| Group (selection by job/window, not performance) | References | Dark PNG | Print PDF |
| --- | --- | --- | --- |
| September execution model | R08/R13 | [screen](figures/execution-september-dark.png) | [print](figures/execution-september-print.pdf) |
| October execution model | R09/R14 | [screen](figures/execution-october-dark.png) | [print](figures/execution-october-print.pdf) |
| Completed reference-plan sweep | R01/R03/R04/R05 | [screen](figures/reference-sweep-september-dark.png) | [print](figures/reference-sweep-september-print.pdf) |
| Completed template-derived sweep | R15/R16/R17/R18 | [screen](figures/plan-sweep-september-dark.png) | [print](figures/plan-sweep-september-print.pdf) |

Legend R references link to their parameter appendix entries in standalone
PDFs; the PNG carries the same human-readable references. The appendix
contains every filter, including unchanged fields. R17/R18 zero-trade curves
overlap at 10,000 and are both retained with different line styles.
Historical R06/R07/R11/R12 lack `equity.csv` in the snapshot and are not
graphed. R02/R10/R19/R20 are excluded as unfinished, not because of outcomes.
The monograph embeds the September print figure and references the full set.

Run from `/tmp/mba-pattern-volume` with the existing environment:

```sh
PYTHONDONTWRITEBYTECODE=1 algo-suite/.venv/bin/python -B \
  algo-suite/docs/stories/in-progress/13-pattern-volume-experiments/evidence/render_intermediate_figures.py
PYTHONDONTWRITEBYTECODE=1 algo-suite/.venv/bin/python -B -m pytest -q -p no:cacheprovider \
  algo-suite/docs/stories/in-progress/13-pattern-volume-experiments/evidence/tests/steps/test_intermediate_figures.py
make -C monografia verify
```

## Separate coordination note

After this frozen snapshot, the user reported that native M1/H1/H4 signal
parity tests passed in 59 seconds, including an RSI fix, and that the
candidate experiment had not launched. That is a coordination report from
the main owner, not independently audited here and not a performance result.
It does not alter the frozen predecessor configurations or model identities.

The user subsequently identified local FinBERT sentiment as a separate future
factor, pending real text inputs and model-vintage verification. It is not
part of the present event-intensity comparison. The four baseline plus four
hybrid candlestick/volume candidate launches remain pending runner readiness,
as reported by the main owner; no candidate result is implied by native parity.
