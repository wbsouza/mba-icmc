# Story 17 — F5/F6 risk and money-management review

Status: planned. Requested September 28, 2026. Owner: unassigned.
Inspected code baseline: `main` at `f438156`.

Priority: **high — capital-preservation review before strategy promotion**.
The user explicitly prioritizes risk and money management over adding entry/exit
ideas. Complete the core F5/F6 correctness review and resolve relevant critical
findings before relying on new composition results for paper/live promotion.
Stories 15/16 can continue source review, but must consume this risk contract.
Do not interrupt running simulations; quarantine or qualify their conclusions
if the review reveals a defect affecting them. Management experiments come
after correctness, not instead of it.

## User story

As a researcher, I want to review our risk guard (F5), capital management (F6)
and execution boundary using Noble DraKoln's *Trade Like a Pro* and complementary
sources, so that we measure actual exposure, size positions consistently and
compare management policies without changing the entry hypothesis.

Central question: do we control the risk actually taken, or only the risk
intended in a configuration? A stop price is not a guaranteed execution price.
Separate correctness, economic performance and operational readiness.

This story is planning only. Do not change strategy defaults, running jobs,
historical artifacts or live accounts when creating it. Implementation starts
in a separate feature worktree with explicit ownership and an updated progress
record. Existing Story 15/16 planning files must be preserved.

## 1. Source review without single-author bias

Use [reading-list.md](reading-list.md). The primary book is *Trade Like a Pro:
15 High-Profit Trading Strategies*, Noble DraKoln, Wiley, 2009, ISBN
`978-0-470-28735-4`. Read-only PDF:

`related-work/books/books-forex-trading/Trade Like a Pro - 15 High-Profit Trading Strategies 2009.pdf`

SHA-256: `b2496600255bcdffd822e197bdac22c9db82caf1a680c02a823945423a16ebda`.
The file has 288 PDF pages; printed Arabic page +14 matches the sections checked.
Verify each locator. Preparation inspected contents/preface and selected stop,
collar and spread sections; this is not a completed book review.

The book's emphasis includes options-based risk structures. Use its arguments
to question our assumptions, not as authority to remove stops or implement
unavailable hedges. Required review outputs:

1. `review-matrix.md`: question, source/page, claim, assumptions, applicable
   instruments, current code/test evidence, conflict/counterexample, proposed
   disposition and acceptance scenario.
2. For each major policy decision, compare at least two relevant independent
   authors where available. Do not count editions or copied references as
   independent evidence. Where there is only one source, flag that limitation.
3. Distinguish facts/invariants, author prescriptions, our adaptations and
empirical hypotheses. Author agreement does not prove an edge; disagreement
   must not be resolved by choosing the highest in-sample return.
4. Record adopted, rejected, experiment-only and deferred ideas with reasons.
   Do not import recommended percentages, Kelly fractions or leverage limits
   as defaults without a separately reviewed protocol.

## 2. Scope and repository boundaries

Review these paths under `algo-backtest/src/algo_backtest/`:

- F5 and `rules/risk_guard.py`: eligibility and account-level limits.
- F6 and `rules/risk_math.py`: stop economics, sizing, margin and trade plans.
- `chain/wiring.py`: account/position data, currency units and calendar anchors.
- `engine/order_executor.py` and its collaborators: actual orders/fills,
  protective quantities, partial exits, trailing and OCO behavior.
- Configuration, artifact/audit and test consumers of those contracts.

Reuse the existing chain and risk engine. Do not add another parallel money-
management engine. No options, naked option writing, collars, synthetic futures,
multi-leg hedges or new instrument-data pipelines are in this story. No new
entry strategy or automated live deployment is included.

## 3. Review work packages

### A. Define the risk contract before changing formulas

Specify balance, equity, free margin, used margin, realized/unrealized P&L,
gross/net exposure, planned loss to stop, pending-order risk and stress loss.
State currency, denominator, sign and timestamp for every field. Distinguish
entry-to-stop original risk from remaining mark-to-stop exposure; explicitly
define treatment of profitable positions and stops beyond break-even.

Observed review leads, not completed findings or approved fixes:

- `account_features` currently supplies `abs(unrealized_profit) / equity` as
  `account_portfolio_at_risk`, and 0/1 from `invested` as the open-trade count.
  Test whether these representations satisfy their declared account contracts.
  Zero P&L at entry is not evidence of zero exposure to an adverse move.
- Cash feeds the field named `account_balance`; pip value and leverage are
  configured inputs. Trace account-currency conversion and brokerage semantics.
- F5 consumes existing account state before F6 proposes quantity. Verify how
  proposed and pending exposure is checked before submission, not just current
  exposure. If needed, add a final admission check without weakening F5's veto.
- F6 sizes against the wider long/short stop and reviews both sides. Determine
  whether this is a documented conservative policy or an unintended restriction
  when the candidate direction is already known. Do not change it silently.

### B. F5: portfolio admission and loss controls

Review exact boundary behavior for loss, leverage, position-count and aggregate
risk caps. Include the candidate and outstanding reservations where relevant.
Two candidates must not independently consume the same remaining budget.
Distinguish gross exposure from offsets and shared-currency concentration;
do not claim diversification from opposite signs or assume correlations are
stable. Unsupported multi-position/account cases must be explicit.

Specify daily/weekly equity anchors, time zone, deposit/withdrawal treatment,
restart persistence and reset behavior. Define entry halt, cancel-pending,
reduce-only and liquidation as separate policies. A veto is not automatically
a liquidation command and cannot stop protection of existing positions.
Missing/stale/invalid account state blocks unsafe admission with an explicit
reason; do not quietly turn nonpositive equity or missing stops into zero risk.

### C. F6: quantity and protective-plan consistency

Trace risk budget through actual entry/stop distance, costs, pip/tick value,
account currency, contract multiplier, lot step, minimum quantity and margin.
Round quantity conservatively; veto when the minimum tradable size exceeds
budget. Reconcile approved quantity with submitted and filled quantity.

Review fixed, ATR and structural stops, their floors/shrinking rules and actual
side-specific execution prices. A smaller stop cannot silently invalidate the
entry setup. Define spread accounting so costs are neither omitted nor counted
twice. Planned risk and scenario/stress risk must remain separate; neither is
an unconditional maximum-loss guarantee.

Specify partial-target fractions against original or remaining quantity,
remaining protective coverage, trailing-stop monotonicity and price rounding.
Recompute risk after partial fills, stop changes and gaps. A first target's
nominal reward/risk ratio is not net expectancy for a multi-exit trade.

### D. Execution and adverse-case verification

Review stop rejection, delayed cancellation, duplicate events, gap-through
fills, unavailable prices and simultaneous stop/target crossings. Never assume
favorable order of intrabar prices or immediate broker acknowledgments.
Review TD-66/67/68/70/71 (order roles, financing, broker minimums, provenance and
OCO). Confirm current status before relying on old debt descriptions.
Relevant unresolved defects block performance/readiness claims, not just tests.

## 4. Acceptance criteria

Write Gherkin first and implement pytest-bdd steps. Expected controls and
malformed-state errors require exact outcomes, not error-or-veto disjunctions.

| ID | Required proof |
| --- | --- |
| AC1 | Review matrix compares sources, exposes disagreement and maps each proposed change to evidence and a test |
| AC2 | A newly opened zero-P&L position still contributes its defined risk; profitable positions are not counted as loss solely because P&L is positive |
| AC3 | Current, pending and proposed exposure obey exact budget boundaries; concurrent candidates cannot over-reserve risk |
| AC4 | Multiple positions, gross/net exposure, missing protection and unsupported account states have explicit behavior |
| AC5 | Balance/equity/currency conversion, pip/tick units, lot steps and margin produce independently verified quantities; minimum size can veto |
| AC6 | Fixed/ATR/structural stops preserve declared semantics; spread, fees and adverse fills reconcile planned versus realized loss |
| AC7 | Partial exits leave correctly sized protection; trailing updates never loosen a stop unintentionally; OCO cannot create an unexplained reverse position |
| AC8 | Daily/week rollover, market gaps and restart state preserve limits; an entry veto leaves protective management active |
| AC9 | Native LEAN lifecycle and offline risk calculations agree on fixtures; malformed/nonfinite/stale inputs fail with actionable diagnostics |
| AC10 | Old configurations/artifact readers are preserved or migrated explicitly; corrections that affect results are versioned and old runs remain untouched |
| AC11 | Policy comparisons freeze entry logic and distinguish changed opportunity counts, sizing effects, cost effects and true expectancy changes |
| AC12 | Report, parameter appendix, QA procedure and handoff support independent takeover; no inference or live-readiness claim exceeds evidence |

## 5. Correctness repairs versus a contest of policies

First publish review findings by severity and classification. Implement agreed
in-scope correctness repairs with regression/native evidence. Do not disguise
a correctness fix as an optional performance optimization or preserve an unsafe
bug as the recommended control. Archive old results and clearly label affected
comparisons invalid where appropriate.

Then create `method-design.md` before new outcomes. Register a small comparison
budget: fixed/volatility/structural protection, single versus partial exits, or
a time exit are candidate adaptations, not yet selected settings. Freeze entry
filter configuration, candidate timestamps, data, clock, costs and starting
capital. Keep risk budget fixed unless sizing itself is the registered variable.

Different exits alter holdings and later eligibility, so fixed entry logic does
not promise identical executed trades. Report both the candidate stream and
executable portfolio results. If using isolated per-candidate diagnostics, label
them counterfactual and never present overlapping independent trades as one
funded account. Log vetoes and missed/re-entered opportunities by reason.

Record all trials, chronological development/validation splits, an untouched
evaluation or explicit exploratory label, primary metric, drawdown constraints,
cost stresses and statistical prerequisites. Compare account-currency outcomes
and initial-risk-normalized returns together; favorable R-multiples alone do
not establish a deployable advantage. No post-hoc tuning on the final period.

Each result includes full F5/F6/exit settings, entry configuration hash, proposed
versus realized risk, exposure/margin, net returns, drawdown, time underwater,
trade counts, loss streaks, stop slippage, rejected orders and uncertainty.
Use valid paired daily-equity inference only when its calibration/sample-size
requirements hold. Resampling must respect dependence; a book's IID example
does not override Story 11's contracts. A no-improvement result is valid.

## 6. Delivery and completion

Deliver review matrix, agreed repairs or explicit follow-up dispositions,
test/native/mutation evidence, frozen experiment protocol and results,
parameter appendix, `qa-procedure.md` and maintained `progress.md`.
Review quality/dependency gates and disclose inherited failures. Update tool
SPEC/README/PRD with shipped changes and the monograph only with verified
evidence and correct citations. Commit/push coherent batches when permitted.

The core review is independent of Stories 15/16; its shared contracts support
their later filter combinations. Coordinate changes instead of duplicating
risk work. Paper/live-readiness uses Story 16's separate gate; no recommended
live risk fraction or broker action follows from this story. Move to done only
after agreed deliverables are verified, committed and accompanied by lessons
learned; deferred performance work must not be labeled completed experiments.
