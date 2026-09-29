# Confluence chain — registered 14-cell protocol (story 21)

Status: registration frozen for review 2026-09-28, before any cell is launched.
Source spec: `algo-suite/docs/stories/in-progress/21-confluence-chain/spec.md`
(primary, unchanged). Planning companion:
`.specs/features/confluence-chain/{spec,design,tasks}.md`. This file is copied
byte-for-byte into each job directory `run_cells.py` (T17) creates, before that
job's first cell attempt.

This is an **exploratory, previously inspected** study, not a confirmatory test
or an untouched-data result. Both the full study window and its Nov–Feb tail
were already viewed while diagnosing the session-2 rule cells (see "Windows and
labels" below); registering the protocol now cannot retroactively make either
window untouched.

## Accepted decisions (D1–D11)

All eleven planning decisions were resolved by the user on 2026-09-28. D1–D4 and
D6–D11 are accepted as drafted in `.specs/features/confluence-chain/spec.md`.
D5 is **not** the draft's alternative — it is the source spec's own bar-open
timing:

- **D5 (accepted wording).** Let `t` be the signal bar during which an entry
  fills. The exit is due at the close of bar `t+N-1`, which is the open of bar
  `t+N`. The engine submits one market closure on the first tradable event at
  or after that open, using actual fill prices — never a synthetic historical
  open. `N=4`.
- **D1** trailing month: fixed 30 calendar days before each UTC month start,
  frozen for the whole month including a mid-month start.
- **D2** quantile sample/availability: one observation per completed signal
  bar; linear quantile interpolation; close time and availability time both
  strictly before the cutoff.
- **D3** trigger sign: `intensity_sign: -1` (high q90 crossing = SELL, low q10
  crossing = BUY, equal cutoffs = HOLD).
- **D4** agreement: a nonempty named required-voter set; all required votes
  directional and identical; any other directional voter disagreeing forces
  HOLD; explicit HOLD blocks; optional ABSTAIN/NEUTRAL do not.
- **D6** exit precedence: reconcile stop fills, then expiry, then configured
  veto closure, then entry/reversal; no re-entry on the expiry-submission
  event; same-side signals do not reset age.
- **D7** evidence protocol: H1 A vs T-only on Nov–Feb is primary; H4 and other
  contrasts secondary; stationary bootstrap block 4, sensitivity 2, 999
  resamples, seed 42, alpha .05.
- **D8** completeness/warmup: a full 30-day history and `L+1` complete closes
  required; documented closures excluded; missing expected data hard-fails;
  normal initial collection is WARMUP/HOLD.
- **D9** controls/risk: explicit constant-direction controls; same F5 caps and
  F6 time plan as A; no artificial intensity thresholds.
- **D10** audit compatibility: existing decision/trade-plan schemas preserved;
  a versioned exit-event sidecar added through integration-owned recorder code.
- **D11** entry/expiry interaction: `min_hold_bars: 4` on time-exit arms;
  A-plan uses its own pinned reference plan; `close_on_veto` stays explicit.

## The 14 registered cells

Generated deterministically by `make_cells.py generate_manifest()`; each cell's
`config.yaml` and the run's `manifest.json` (`{cell_id, arm, clock_minutes,
config_hash}` per row) are written under a caller-supplied job directory at
generation time. **Config hashes are not recorded here** — `config_hash` is a
SHA-256 over the canonical sorted-key JSON of each cell's actual generated
config, computed by `make_cells.py` at generation time, not invented ahead of a
run. Re-running the generator against unchanged inputs reproduces the same 14
IDs and hashes (verified in QA, see `qa-report-phase2.md` step 11: 14/14/14,
deterministic across two runs).

| # | Cell ID | Arm | Clock | Required voters | Exit |
| - | --- | --- | --- | --- | --- |
| 1 | `a-h1` | A | H1 | momentum, relative F4 | time (N=4) + ATR stop |
| 2 | `a-h4` | A | H4 | momentum, relative F4 | time (N=4) + ATR stop |
| 3 | `b-h1` | B | H1 | momentum, relative F4, F2 | time (N=4) + ATR stop |
| 4 | `b-h4` | B | H4 | momentum, relative F4, F2 | time (N=4) + ATR stop |
| 5 | `a-plan-h1` | A-plan | H1 | momentum, relative F4 | pinned Heikin-Ashi H4 reference plan (4R/6R, trail) |
| 6 | `a-plan-h4` | A-plan | H4 | momentum, relative F4 | pinned Heikin-Ashi H4 reference plan (4R/6R, trail) |
| 7 | `t-only-h1` | T-only | H1 | relative F4 | time (N=4) + ATR stop |
| 8 | `t-only-h4` | T-only | H4 | relative F4 | time (N=4) + ATR stop |
| 9 | `m-only-h1` | M-only | H1 | momentum | time (N=4) + ATR stop |
| 10 | `m-only-h4` | M-only | H4 | momentum | time (N=4) + ATR stop |
| 11 | `always-short-h1` | always-short | H1 | constant SELL | time (N=4) + ATR stop |
| 12 | `always-short-h4` | always-short | H4 | constant SELL | time (N=4) + ATR stop |
| 13 | `always-long-h1` | always-long | H1 | constant BUY | time (N=4) + ATR stop |
| 14 | `always-long-h4` | always-long | H4 | constant BUY | time (N=4) + ATR stop |

Every cell: EUR/USD, USD 10,000 account, pinned OANDA execution economics
(spread 1.0 pip, 0 commission per lot, 0 broker stop-level floor above the
existing spread-aware stop math), F5 caps (daily −5%, weekly −15%, 2 concurrent,
leverage 30, portfolio-at-risk 0.18), window 2016-03-01..2017-02-28 inclusive.
`close_on_veto: false` on all 14 cells (verified against `make_cells.py`'s
`_execution_for`) — see "Known constraints" below for why this matters.

## Windows and labels (exploratory, already inspected)

Both windows are labeled exploratory on every cell and every report:

- **Full year, 2016-03-01..2017-02-28.** Already inspected while diagnosing the
  session-2 one-sidedness (see the source spec's decision-log table and the
  outlier finding in `evidence/signal-horizon-check.md`).
- **Nov–Feb.** Already inspected as part of the same year; it is not a held-out
  or untouched slice. It carries the primary contrast (below) precisely because
  it was already looked at, not despite it — no claim of a confirmatory or
  untouched-data result attaches to either window.

Clocks: H1 momentum lookback `L=480` closed bars; H4 momentum lookback `L=120`
closed bars. Both describe 480 scheduled trading hours of history, not 20
calendar days — market gaps extend elapsed time. The time-exit horizon is 4
completed bars on both clocks: 4 scheduled hours on H1, 16 scheduled hours on
H4. H4's matching contrast is a secondary extrapolation, not independent
confirmation of the H1 finding.

## Contrasts

- **Primary**: H1 `A` vs `T-only`, Nov–Feb, paired UTC calendar-day net
  portfolio returns.
- **Secondary**: the matching H4 `A` vs `T-only` contrast; `A` vs `A-plan`
  (exit-policy comparison); `B` vs `A` (F2 confirmation); `A` vs each drift
  control (`always-short`, `always-long`). `M-only` is a reported ablation, not
  a basis for selecting a new winning cell.
- No claim of multiplicity-corrected or confirmatory inference is made from a
  single nominal p-value; the fixed 14-cell family and every prior exploratory
  look are recorded alongside the result.

## Statistical protocol

Stationary bootstrap: block length 4, sensitivity check at block length 2, 999
resamples, seed 42, alpha 0.05 (D7). Prediction endpoint: next-four-completed-bar
directional hit rate on entry-eligible decisions; a zero return counts as a
miss; an incomplete forward horizon is counted and reported as an exclusion, not
folded into the hit rate. Overlapping horizons are not treated as independent
samples for a confidence interval. Trade-based equity and the prediction hit
rate are reported as distinct endpoints.

## Population source and costs

Price population: **EUR/USD, Dukascopy tick data** (the repository's primary
price source per `algo-suite/PRD.md` §7), aggregated to closed H1/H4 bars
through the existing `ClosedBarClock`. Any month covered only by the yfinance
daily fallback is flagged in the coverage matrix and excluded from this
minute-resolution study, per `PRD.md`'s stated policy — it is never
interpolated up to synthetic minute bars. **OANDA** enters this study only as
the pinned execution-cost/broker-floor model (`_OANDA_EXECUTION` in
`make_cells.py`: spread, commission, broker stop-level floor); it is not the
historical price source. Do not conflate the two.

Preflight (T9, `preflight.py`) reconciles, per (pair, clock, window):
calendar-expanded slots, documented weekly FX-closure slots, expected valid
slots, warmup bars and missing bars before any cell is launched;
`ready_count = expected_valid_count - warmup_count - missing_count`. A missing
expected bar is a hard failure, never a soft count. File presence or a `.done`
marker proves nothing by itself.

## No model dependency

None of the 14 cells depends on a Story 19 adaptive/retrained model (no F7
requirement). All seven arms are deterministic rule chains over F1
momentum-context, F4 (static or relative), optional F2, F5 and F6, exactly as
listed above.

## Attempt policy

One initial attempt per cell. No automatic outcome-based retry: a cell that
fails, produces zero trades, or hits a preflight gate is recorded with that
outcome and is not silently relaunched to seek a different result. A rejected
or crashed attempt is retried only through an explicit, separately authorized
re-run of that one cell — never an automatic loop inside the harness.

## Known constraints on this run (disclosed, not silently worked around)

Two engine-level gaps were found and recorded during Story 21 Phase 3
integration (`algo-suite/docs/stories/parallel-19-21-22.md`, "Story 21 Phase 3
(T11–T15) integration log", integration branch `feat/integrate-19-21-22` at
`581d1c0`, read-only):

1. **`intensity_relative` is wired but not fed live data.**
   `algo_score.events.models.GdeltFeature` has no `available_at` field, so
   `chain_algorithm.initialize()` refuses the `direction_source:
   intensity_relative` option combination rather than fabricate availability
   provenance (this is CC-13's own contract, not a bug). **Any cell whose
   config sets `news_context.direction_source: intensity_relative` is
   UNAVAILABLE until that data gap is resolved — it is not silently
   substituted with a static or sentiment mode.** Per `make_cells.py`
   (`_NEWS_ARMS`), that is arms `A`, `B`, `A-plan` and `T-only` on both clocks:

   | Launch-ready today (no news dependency) | Blocked pending GDELT `available_at` provenance |
   | --- | --- |
   | `m-only-h1`, `m-only-h4` | `a-h1`, `a-h4` |
   | `always-short-h1`, `always-short-h4` | `b-h1`, `b-h4` |
   | `always-long-h1`, `always-long-h4` | `a-plan-h1`, `a-plan-h4` |
   | | `t-only-h1`, `t-only-h4` |

   Six cells can launch today, subject only to the population/price-history
   gate above. Eight cells — including the primary contrast's `A` arm — remain
   blocked until GDELT (or an equivalent source) carries verifiable
   publication/availability timestamps.

2. **`exit_after_bars` + `close_on_veto: true` together also fails fast** at
   `initialize()` (`chain/time_exit.py`'s `TimeExitLifecycle` has no
   veto-closure event, so wiring both would desynchronize the lifecycle from
   the real position). Checked against `make_cells.py`'s `_execution_for`:
   every one of the 14 registered cells sets `close_on_veto: false`
   explicitly, so **none of the 14 cells is affected** by this refusal.

3. **A separate, narrower gap found while writing this registration**
   (`preflight.py`'s `compute_arm_ledger`, not the engine): its two arm
   registries, `_NEWS_REQUIRED_ARMS = {"A", "B", "T-only"}` and
   `_NO_NEWS_ARMS = {"M-only", "always-short", "always-long"}`, do not include
   `"A-plan"` in either set. `A-plan` shares `A`'s required voters
   (`f1_trend`, `f4_news_context`) and its generated config does set
   `news_context.direction_source: intensity_relative` — so by the same rule
   it should require an availability sidecar — but calling
   `compute_arm_ledger("A-plan", ...)` today raises `ValueError: unknown arm`
   instead. This is a T9 script gap, confirmed by its own feature file
   (`confluence_preflight.feature`'s two arm-ledger rules list only `A`, `B`
   and `T-only`; no scenario exercises `A-plan`), not a project decision. It
   is recorded here as found, not fixed under this documentation-only task;
   `A-plan` remains blocked by finding 1 above regardless (engine-level
   `initialize()` refuses `intensity_relative` before the arm ledger would
   even run), so it does not change which cells can launch, but the harness
   (T17) or preflight (T9) will need this registry corrected before `A-plan`
   can be preflighted through this exact script.

## Resource cap

`algo-suite/docs/stories/parallel-19-21-22.md` ("Experiments: parallel
resources, separate attribution") records the policy — one coordinator owns a
global CPU/memory/LEAN-slot semaphore, no worker assumes slots independently,
and the coordinator measures availability and sets an explicit total cap and
timeouts at registration — but does not itself record specific numbers.
The coordinator (main) communicated a cap of 3 concurrent LEAN containers, a
per-host fit of 8 threads, and a 30-minute timeout per cell for this
registration; that measurement is recorded here as communicated, not yet
written into a repository doc as of this file's freeze. T17's harness must
enforce whatever cap is authoritative at actual launch time, re-confirmed with
the coordinator rather than assumed from this line.

## Source revision

This registration was written against:

- Story 21 branch `feat/21-confluence-chain`, this commit (see the commit that
  adds this file for its exact SHA).
- Integration branch `feat/integrate-19-21-22` at `581d1c0` (Phase 3 T11–T15
  log consulted read-only; not merged into this worktree).
- Planning baseline `main` at `35a0dc9` (PR #87).

No approval, resource number, or hash beyond what is cited above is asserted as
established fact by this file.
