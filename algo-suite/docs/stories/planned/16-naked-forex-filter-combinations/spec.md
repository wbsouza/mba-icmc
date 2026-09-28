# Story 16 — Naked Forex filters and a contest of combinations

Status: planned. Requested September 28, 2026. Owner: unassigned.
Inspected code baseline: `main` at `f438156`.

## User story

As a researcher, I want to translate selected ideas from Alex Nekritin and
Walter Peters' *Naked Forex* into reusable filters, combine them with existing
and Miner-inspired components, and compare competing configurations on fair
terms, so that evidence determines which combinations merit further testing
and whether any deserves a paper-trading or eventual live-account pilot.

This is a **contest of ideas**, not a mandate to adopt one author's complete
system. Filters are the reusable units; registered compositions are the
experimental contestants. A book-only or reduced chain is a comparison control,
not the required final architecture. More filters do not automatically mean
better evidence or a better strategy.

This request creates a new story, separate from
[Story 15](../15-miner-strategy-adaptation/spec.md). It does not implement code,
launch simulations, change ongoing jobs or authorize live orders now.

## 1. Primary source and review scope

Read-only reference supplied by the user:

`/media/nas/wellington/mba/related-work/books/books-forex-trading/Naked Forex - High-Probability Techniques for Trading Without Indicators 2012.pdf`

Authors: Alex Nekritin and Walter Peters. Wiley, 2012.
Print ISBN: `978-1-118-11401-8`. PDF: 290 pages.
SHA-256: `5039e34432a4f58cbe73483b72fb6e8c4c9818118c7d51cb8a5106a5274b7b72`.
Printed Arabic page numbers map to one-based PDF pages by adding 16 in the
sections checked; verify each citation. Do not commit the PDF or its full text.

Preparation inspected front matter, contents and selected passages in Chapters
4–6 and 8, including printed pp. 92–93, 109–110 and 133–134. Full chapter/chart
review is still required; the following is a review inventory, not a claim of
implemented or fully specified strategies.

| Chapter | Printed start | Concepts to map into components |
| --- | ---: | --- |
| 3 | 25 | Backtesting process and limitations |
| 4 | 39 | Support/resistance zones, history and repeated price interaction |
| 5 | 73 | Last Kiss: consolidation, breakout, retouch and conditional entry |
| 6 | 95 | Big Shadow: two-bar geometry plus location/context |
| 7 | 111 | Wammies and Moolahs: multi-touch setup rules |
| 8 | 131 | Kangaroo Tails: rejection-candle geometry plus location/context |
| 9 | 151 | Big Belt: source-specific setup and market/session assumptions |
| 10 | 163 | Trendy Kangaroo: trend-context variant |
| 11 | 177 | Exit choices and trade management |
| 13 and 16 | 209 and 249 | System construction, risk and operational discipline |

Create `rule-mapping.md` before implementation. Each rule needs: source locator,
original paraphrase, inputs and availability times, formula/state transition,
edge cases, owning component, configuration fields and Gherkin scenario.
Distinguish `book-derived`, `deterministic adaptation` and `project extension`;
classify work as `reuse`, `adapt`, `new` or `defer-with-reason`.
Separate mandatory rules from the authors' preferred/optimal characteristics.
Quantifying words such as near, large or clear is an adaptation unless the book
provides the exact bound. Resolve textual/arithmetic inconsistencies explicitly.

## 2. Composition contract: ideas compete as filter combinations

Reuse the existing `Filter`, `FilterResult`, enrichment, veto and terminal seams.
Proposed logical flow, not fixed class names or required filter order:

`causal observations → setup candidates → configured context/veto gates →
entry lifecycle → risk-checked execution and management`

- A candidate carries direction, setup ID, evidence timestamps, zone IDs,
  proposed entry/invalidation and rule version. Gates evaluate that candidate,
  not disconnected BUY/SELL votes for different setups.
- Setup detectors are alternatives. A Last Kiss does not require a simultaneous
  Big Shadow, Kangaroo Tail and Wammie. Compare families separately first;
  register any union and its conflict/priority rules before evaluation.
- A valid setup can still be vetoed by location, structure, configured momentum,
  quote activity, insufficient room to a target, or portfolio risk. Declare
  which conditions are mandatory and which are descriptive evidence.
- Passing gates only makes an entry eligible. Explicit trigger, expiration,
  invalidation and order-fill rules remain separate. A veto blocks/cancels an
  entry according to policy; it must not remove an open trade's protective stop.
- The current chain short-circuits on veto and does not treat ABSTAIN as veto.
  Mandatory not-ready evidence must block new entry explicitly. Log downstream
  gates as not evaluated, never as passing. Corrupt inputs are errors, not vetoes.
- Conflicting directions and duplicate same-direction candidates need a fixed
  arbitration rule and shared exposure budget. No hindsight choice of the
  candidate that would have won. Do not score duplicated price evidence as
  independent confirmations or interpret pattern strength as a probability.

Record the selected graph/order, resolved parameters, enabled/disabled gates,
candidate provenance and final decision for every run. Keep old strategy defaults
unchanged. A composition using momentum indicators is a hybrid experiment, not
an indicator-free reproduction of this book.

## 3. Reuse and new capabilities

| Component | Reuse/adaptation plan |
| --- | --- |
| Closed bars and OHLC validation | Reuse current perception/clock layer; freeze UTC/session conventions and available-at timestamps |
| F3 / TA-Lib detector | Reuse infrastructure, not automatic equivalence of book setups to library labels |
| Support/resistance zones | Add causal, versioned zone construction shared by eligible setup families |
| Setup detectors | Add independently selectable Last Kiss, Big Shadow and Kangaroo Tail candidates first |
| F1/F2 and Story 15 momentum | Optional context/veto components; preserve pure price-action comparison cells |
| F5/F6 and executor | Reuse risk/sizing/order machinery; adapt setup-specific stops/targets without replacing their meaning |
| Quote-activity filter | Optional project extension; label tick activity, not centralized traded volume |
| F4/F7 | Optional later registered extensions, not hidden dependencies of price-action filters |
| Story 15 lifecycle/structure primitives | Share if implemented and suitable; do not duplicate or assume planned code exists |

The standalone price-action slice must not wait for all of Story 15. Only a
composition consuming a Miner component depends on that component's verified
delivery. Inspect current ancestry and coordinate shared file ownership first.

### Zones and causal state

Specify how past reactions establish a price area: input price basis, touch
count/separation, width, lookback, confirmation delay, merging, role reversal,
invalidation and retention. Avoid choosing zones with future reactions or
moving a historical zone retrospectively to explain a winning trade.
Store immutable as-of zone snapshots; if a newly closed bar contributes to a
zone, define whether that updated zone may qualify the same bar's setup.

### Setup fidelity

Big Shadow is not simply TA-Lib engulfing: review full high/low geometry,
close location, relative range, zone context and space to the left. Kangaroo
Tail is not simply a hammer/shooting-star label: its source defines body
location and additional context. Preserve strict versus preferred conditions
and test threshold boundaries, zero-range bars and insufficient history.

Last Kiss needs a temporal sequence: established consolidation, breakout,
retouch and confirmation. It cannot enter on the initial breakout alone.
Review both its emergency protective stop and the separate close-back-inside
exit; do not replace them silently with inherited fixed-R settings. Use a
declared entry/stop buffer unit and realistic bid/ask execution.

Review all remaining setup families and document feasibility. Add Wammies,
Moolahs, Big Belt and Trendy Kangaroo as subsequent independently tested slices
or explicitly approved deferrals. Session/gap assumptions must fit actual FX
data; do not create artificial gaps or claim a full-book implementation when
only a subset exists.

### Execution and architecture

Keep numerical/shape detection pure, setup memory in orchestration and orders
in execution. Confirm cancellation, gaps, partial fills, pending exposure and
same-minute entry/stop/target behavior in native LEAN. Risk checks use actual
structural stop distance; default stop shrinking must not alter invalidation.
Continue minute-level protection when higher-timeframe setup gates veto.
Review TD-71 (OCO), TD-67 (financing) and TD-70 (code provenance) before results
depend on them. Unresolved relevant defects block readiness claims.

### Momentum-literature filters (Antonacci, *Dual Momentum Investing*, 2015)

Ideas to enter the contest as ordinary filter combinations, not as a standalone strategy
(added 2026-09-28; the book's evidence is monthly, on equity and bond indices, so every
claim below is a hypothesis to test on our clocks, not a result):

- **Absolute-momentum regime gate** (Appendix B): trade long only when the pair's
  trailing excess return over a long lookback is positive, short only when negative.
  Lookback candidates 6 and 12 months of daily closes (about 130 and 250 trading days;
  our data starts 2015-01, so 12 months is available from the first test bar). This is a
  time-series momentum filter at a horizon far above F1's higher-timeframe EMA (60 H4
  bars, about ten days), so it is a distinct component. Implementation shape: an F1
  variant or a second regime input to the F7 gate; the value is computed from bars
  closed before the decision bar.
- **Momentum crash guard** (Ch. 7): stand aside on the side opposite the long-lookback
  trend after a sharp reversal (e.g. the 20-day return against the 250-day sign exceeds a
  registered threshold), which is where momentum strategies take their largest losses.
- **Exposure by regime instead of lockout after loss**: an F5 alternative to compare
  in story 17: reduce `risk_per_trade` when absolute momentum is flat or against the
  side, rather than only after the daily/weekly drawdown limit has been hit.
- **Relative momentum across pairs** (Ch. 8–9): rank a G10 universe by 1–12-month
  returns and trade the leaders/laggards. Out of scope until more pairs are downloaded
  (only EUR/USD and USD/JPY exist locally); recorded for the commodity-currency
  follow-up of story 18.

Contest cells: baseline price-only; + absolute-momentum gate (6 and 12 months); + crash
guard; the F5 exposure variant belongs to story 17's comparison of management policies
with fixed entry logic. Same registration, ranking and untouched-months discipline as the
other combinations.

## 4. Acceptance criteria and verification

Write Gherkin scenarios before code; implement pytest-bdd steps, not plain tests.

| ID | Required proof |
| --- | --- |
| AC1 | Each enabled rule maps to the source or an explicit adaptation with parameters and tests |
| AC2 | Future bars cannot change prior zones, candidates or decisions; pivot confirmation time is respected |
| AC3 | Shape alone outside required context does not qualify; geometry/range/zone boundaries have exact expected outcomes |
| AC4 | Breakout without retouch never triggers Last Kiss; long/short lifecycle, cancellation and invalidation are tested |
| AC5 | Alternative detectors do not veto one another merely through absence; registered direction conflicts and duplicate candidates resolve deterministically |
| AC6 | Mandatory not-ready blocks entry; disabled optional gates and skipped-after-veto gates remain distinguishable; bad data raises errors |
| AC7 | Passing filters never causes a retroactive fill; protective orders remain active despite entry veto or setup expiration |
| AC8 | Native/offline parity, bid/ask costs, gap/partial fills and multi-level intrabar/OCO behavior are verified |
| AC9 | Existing strategy defaults, artifact readers and the legacy TA-Lib vocabulary remain compatible |
| AC10 | Every composition exports full settings, candidate/gate funnel, source/code/data hashes, orders, trades, equity and failures |
| AC11 | Ablations use registered matched controls and preserve all tried configurations; no evaluation-period tuning or unreported winner selection |
| AC12 | Final report gives an evidence-backed reject, insufficient-evidence or paper-candidate decision; no automatic live promotion |

Use independent hand-calculated fixtures for geometric rules and bar-by-bar
sequences. Inspect relevant PDF charts visually before using them as examples;
do not invent exact OHLC values hidden in an image. Synthetic fixtures are not
performance evidence. Add architecture, complexity and targeted mutation checks
for new modules and regression checks for reused components.

## 5. Contest design and reporting

Create `method-design.md` before inspecting new outcomes. Audit actual data
coverage, previously viewed windows and the candidate budget first. Dates,
timeframes, risk limits and test thresholds remain unset until this review.

1. Establish a frozen existing-chain control and reduced price-action controls
   for selected setup families, under matched execution/capital assumptions.
2. Register a small set of challengers combining those setups with existing
   filters. For one frozen candidate, a 2×2 momentum-context off/on × quote-
   activity off/on comparison is a possible design, not yet a registered matrix.
   Standalone Miner and combined configurations may be additional controls.
3. Avoid redundant confirmations: requiring generic engulfing as a second gate
   after Big Shadow detection needs a distinct hypothesis, not another vote.
   Register additive combinations and leave-one-filter-out comparisons that
   identify incremental contribution without an unbounded Cartesian search.
4. Choose candidates on development/validation data only. Freeze the shortlist
   before one final held-out evaluation. If all available periods were already
   inspected, call the results exploratory and require fresh forward evidence.
5. Prespecify primary comparison, minimum evidence, net-cost metric, drawdown
   constraints, trial count, multiplicity and uncertainty method. A highest
   return or hit rate alone does not win. Count failed and abandoned variants.
6. Report regimes, long/short exposure and suitable drift controls. Require
   sample-adequate, calibrated daily paired inference where claimed; unavailable
   inference stays unavailable. Do not change bootstrap settings to get a pass.
7. Stress spreads, commissions, slippage, financing and parameter sensitivity
   under registered assumptions. Archive models if any are introduced, source
   hashes, exact commands, logs, immutable data checks and failed attempts.

For every result show every filter's effective parameters, role/order and state,
returns, drawdown, exposure, trade count, costs, setup/veto counts and uncertainty.
Update the monograph with both positive and negative outcomes and explicit
selection history. No claim of superiority or profitability is required for
story completion: a well-supported no-go is a valid result.

## 6. Paper/live-readiness decision

The user wants to know whether results warrant eventually trying a live account.
Produce `readiness-review.md`; this story does not authorize broker access,
account funding, order submission or a live deployment. Retail FX leverage
magnifies losses as well as gains; see the
[CFTC forex risk advisory](https://www.cftc.gov/LearnAndProtect/AdvisoriesAndArticles/CustomerAdvisory_MustKnowForex.html).
Check the user's actual jurisdiction/product rules before any later deployment;
the cited US advisory does not establish local eligibility.

- **Backtest decision:** reject, insufficient evidence, or candidate for paper
  trading. Register numeric minimum sample/period, net-performance and drawdown
  limits before evaluation; do not invent favorable thresholds afterward.
- **Paper stage proposal:** same frozen logic/configuration, fresh data and a
  specified observation period/trade count. Compare intended versus actual
  timestamps, quotes, orders, fills, costs and positions. Paper fills do not
  establish live liquidity. Arrange this stage separately; never imply it ran.
- **Operational gate:** require tested kill switch, aggregate/pending exposure
  limits, stale-feed handling, restart recovery, duplicate-order prevention,
  broker reconciliation, alerts and documented emergency procedures. Missing
  deployment capabilities are follow-up work, not implied by backtest success.
- **Possible live pilot:** only after a separate explicit user decision and
  approval of broker/product, capital at risk, position limits, loss/drawdown
  stop rules, monitoring owner and rollback plan. Do not inherit historical
  3% research risk or leverage settings as live recommendations.

Neither statistical significance nor passing these gates guarantees profits.
Distinguish economic evidence, software correctness and operational readiness.

## 7. Delivery and handoff

Deliver `rule-mapping.md`, reusable implementations/configuration, BDD/native
evidence, `method-design.md`, per-run parameter/results appendix, QA/runbook,
`readiness-review.md` and updated documentation. Keep `progress.md` current with
worktree/agent ownership, exact commands, commits and next action.

Reuse the repository quality gates (Ruff, strict mypy, BDD, relevant native
tests, architecture/complexity, targeted mutation and dependency audit). Record
inherited workspace failures separately. Update tool SPEC/README/PRD when code
lands; verify the monograph when changed. Review debt and source fidelity
independently before moving to done. Commit coherent batches, preserve all
existing work, and write lessons learned when agreed delivery is complete.
