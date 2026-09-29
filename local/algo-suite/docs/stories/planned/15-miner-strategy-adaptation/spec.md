# Story 15 — Miner-inspired strategy review and adaptation

Status: planned. Requested September 28, 2026. Owner: unassigned.
Code baseline inspected: `f438156` on `main`.

## User story and objective

As a researcher, I want to review Robert C. Miner's *High Probability Trading
Strategies* against our existing filter-chain engine, adapt compatible components,
and implement the missing causal rules, so that I can evaluate a traceable
Miner-inspired strategy without replacing the engine or confusing book concepts
with our own extensions.

Creating this story does not authorize starting experiments now. Preserve ongoing
simulations, their configurations, input data, and output directories. Move this
story to `in-progress` only when its implementation is taken up.

## 1. Primary source and review boundary

The user supplied a readable 290-page PDF:

`/media/nas/wellington/mba/related-work/books/books-forex-trading/High Probability Trading Strategies - Entry to Exit Tactics for the Forex, Futures, and Stock Markets 2008.pdf`

SHA-256: `71a358f67b70b6f023db57df831a9f85449344a1aecc885ecf00647569cbe2d8`.
ISBN: `978-0-470-18166-9`. The filename says 2008; the copyright page says 2009.
Resolve the edition/year explicitly when adding the bibliography entry.
Printed Arabic page numbers map to one-based PDF pages by adding 14 in the
sections checked. Record both in the rule ledger; verify each locator.
Keep the PDF read-only and outside Git. Commit original paraphrases and locators,
not copied chapters or a full extracted text.

Story preparation inspected the contents, printed pp. 43–47 and 140–142.
This is not a completed review of the book. Implementers must review the relevant
chapter text and charts before freezing any rule:

| Chapter | Printed pages | Review purpose |
| --- | --- | --- |
| 2 | 9–47 | Dual-timeframe momentum, indicator-specific reversals and extreme zones |
| 3 | 49–82 | Trend/correction structure, overlap, ABC and five-wave interpretation |
| 4 | 83–108 | Internal/external retracements and alternate price projections |
| 5 | 111–137 | Time retracements, projections, target zones and bands |
| 6 | 139–162 | Trailing one-bar and swing entries, invalidation stops and position size |
| 7 | 163–197 | Multi-unit exits and ongoing management |
| 8 | 201 onward | Selected worked examples for independent bar-by-bar rule review |

Publisher reference: [book and chapter catalog](https://onlinelibrary.wiley.com/doi/book/10.1002/9781119197430).

Produce `rule-mapping.md` before coding. Each rule needs an ID, source locator,
paraphrase, required inputs, when each input becomes knowable, decision/state
transition, edge cases, owning component, BDD scenario, and disposition:
`reuse`, `adapt`, `new`, or `defer-with-reason`. Label fidelity separately as
`book-derived`, `deterministic adaptation`, or `project extension`.
Ambiguous chart interpretation must not become an undocumented code assumption.

## 2. Reuse-first compatibility review

Paths below are relative to `algo-backtest/src/algo_backtest/`.

| Existing component | Reuse opportunity | Required review or extension |
| --- | --- | --- |
| `chain/filters/f1_trend.py` | Directional context | EMA context is not automatically higher-timeframe momentum; decide its role without adding contradictory gates |
| `chain/filters/f2_indicator.py` | Momentum calculation/confirmation | Existing RSI/MACD agreement is not a temporal reversal; add explicit dual-timeframe semantics |
| `chain/filters/f3_pattern.py` | Existing candlestick signal | Preserve it; swing/ABC structure is a distinct concept and separately auditable capability |
| `perception/bar_clock.py` | Closed UTC bar aggregation | Synchronize two clocks with explicit availability, same-close ordering and gap policy |
| `chain/filters/f5_risk_guard.py` | Portfolio eligibility | Reuse risk checks, including pending exposure where relevant |
| `chain/filters/f6_capital_mgmt.py` | Sizing and trade plans | Preserve structural invalidation; do not silently shrink a book-derived stop using inherited settings |
| `chain/terminal.py` | Rule-only terminal seam | No F7 required; current last-filter direction alone does not prove agreement among setup stages |
| `engine/order_executor.py` | Orders, stops, partial exits and trailing | Audit pending entry/update/cancel support and intrabar fill behavior before reuse |
| `chain/filters/volume_strength.py` | Optional quote-activity veto | Project extension, not traded volume or an assumed Miner rule |
| F4 news / F7 meta-learner | Optional later comparison | Disabled in the initial deterministic strategy; do not require model training |

Keep perception pure, setup orchestration in the chain, and order lifecycle in
execution. Reuse current configuration, auditing and reporting contracts; add
versioned fields only where necessary. Do not fork a second risk/execution engine.

## 3. Behavior and correctness requirements

### Momentum eligibility and shared direction

Use actual completed higher- and lower-timeframe bars, not an EMA period renamed
as a higher timeframe. Define oscillator, settings, reversal event, equality,
extreme zones, readiness and signal age in configuration and the rule ledger.
Stochastic is a source-supported candidate (Table 2.2); retaining MACD requires
an explicit adaptation of its reversal/extreme semantics. Do not invent a DTosc
formula or assume an indicator package reproduces it.

Review all four higher-timeframe conditions in Tables 2.1/2.2 (pp. 44 and 46).
The book allows consideration of opposite-direction setups at extremes; this is
not an unconditional countertrend order. A continuation-only first slice must
be labeled a subset, with those branches explicitly deferred rather than silently
replaced. The entry candidate has one direction; conflicting mandatory conditions
cannot pass because separate filters merely avoided vetoing.

### Veto-filter composition

Use the existing veto mechanism for mandatory setup eligibility: momentum,
direction agreement, enabled structure/price/time conditions, optional enabled
candlestick/quote-activity confirmation, and portfolio risk. Each gate evaluates
the same candidate and records its parameters, observed values and reason.
Passing every gate permits a setup to be armed; it is not an immediate BUY/SELL.
The separate trigger/lifecycle component controls pending entry and execution.

Distinguish `pass`, `veto` and expected `not-ready` in the audit contract, mapping
them explicitly to existing engine result types. A mandatory not-ready input
blocks a new entry; a disabled optional filter is not a failed condition.
Malformed configuration or corrupt data raises a remediation-rich error rather
than being hidden as an ordinary market veto. Register whether each condition
is captured at setup creation or rechecked while pending; always recheck risk
where execution requires it. A pending setup's invalidation cancels its entry
order, never its existing position's protective stop. Do not automatically turn
all book observations into hard gates: choose and justify each gate in the ledger.

### Causal structure, price and time

Define deterministic swing confirmation and record both pivot time and confirmation
time. Never backdate a decision to the pivot. Future bars must not change already
emitted decisions. Treat evolving/unconfirmed structures as such.
Specify anchor selection, ratios, rounding, zone tolerance, overlap/conflict
handling and invalidation for price projections. For time projections, define
whether duration means elapsed time or observed bars, including weekends/gaps.
Do not claim a chart-perfect Elliott-wave reproduction from heuristic pivots.

### Setup and order lifecycle

Separate eligibility from execution with explicit states such as idle, eligible,
pending, filled, canceled and expired. Register allowed transitions, re-entry and
duplicate-trigger behavior. A setup cannot create a fill on the completed bar
that first made its inputs available.

Review both Chapter 6 entry methods; implement trailing one-bar entry first,
then swing entry as a separately selectable method. Pending stop entries update
from completed bars and cancel when the registered setup conditions fail.
An optional maximum age is our adaptation unless supported by the source.
Offsets use the instrument's minimum price increment, not an assumed FX pip.
Initial protective stops follow the setup's invalidation; sizing uses actual
entry-to-stop distance and configured costs/margin. Revalidate risk on entry
updates and fills. Gaps may exceed intended risk and must be represented honestly.

An entry veto must not disable protection of an existing position. Higher-timeframe
overbought status alone is not an automatic long exit in the reviewed text.
Register stop adjustments, partial exits and final exits separately from entries.
Address same-minute entry/stop/target ambiguity and OCO behavior in native LEAN;
never assume favorable intrabar sequencing from OHLC bars.

## 4. Delivery phases and scope control

1. **Review:** complete the source-to-code ledger, inspect execution debt, choose
   the first exact rule subset and record unresolved interpretation decisions.
2. **Minimum runnable slice:** actual dual-timeframe momentum, trailing one-bar
   pending entry/cancellation, structural stop, existing risk/sizing and an
   explicit exit policy. Label this a Miner-inspired subset, not the full method.
3. **Complete the selected framework:** causal structure, price zones, time
   analysis, swing entry and reviewed management rules. Stage these additions
   independently; document whether each acts as a hard gate or descriptive context.
   Any scope reduction requires an explicit amendment, not a silent completion.
4. **Verification and evaluation:** freeze a reviewed strategy, then run the
   registered comparison and publish all outcomes and limitations.

Proposed strategy identifier: `miner-inspired`, subject to repository conventions.
Existing strategies retain their behavior and defaults. No live/paper deployment,
new NLP model, GPU work, broad parameter search or automatic main/PR merge belongs
to this story. Optional news/F7 comparisons require a later protocol amendment.

## 5. Acceptance criteria and tests

Write executable Gherkin before implementing each behavior; use pytest-bdd steps.
The following is the minimum scenario inventory, not evidence of tests already run:

| ID | Required behavioral proof |
| --- | --- |
| AC1 | Every implemented rule has a verified source locator or explicit adaptation, configuration and test mapping |
| AC2 | Partial/future higher-timeframe bars cannot affect lower-timeframe decisions; same-close ordering and missing-bar policies are deterministic |
| AC3 | All momentum cases, equality/extreme boundaries, stale reversal and warm-up conditions have exact expected eligibility outcomes |
| AC4 | Conflicting candidate directions and mandatory not-ready states block entry; optional disablement is explicit; passing all gates only arms a setup |
| AC5 | Pivot confirmation delay is respected; appending future bars leaves all earlier decisions unchanged |
| AC6 | Price/time projections use only available anchors, honor tolerance boundaries and reject malformed parameters |
| AC7 | Long and short pending entries update, fill, cancel and expire correctly; invalidation and duplicate events never create extra orders |
| AC8 | Tick/pip distinctions, gap fills, structural stops, margin and pending exposure affect sizing correctly; existing positions remain protected after veto |
| AC9 | Native LEAN reproduces offline signals and proves entry/exit lifecycle, including bars crossing multiple order levels and partial-fill/OCO handling |
| AC10 | Disabled new capabilities preserve existing strategy behavior; configuration and artifact contracts remain backward-compatible |
| AC11 | Each run archives resolved parameters for every filter, source/code/data hashes, rule version, veto/setup funnel, orders, equity and exact failure outcome |
| AC12 | Independent review, scoped quality/mutation gates and real-data evidence support the stated subset; no profitability or fidelity claim exceeds evidence |

Expected unavailable/warm-up states and malformed-input errors must have distinct,
asserted outcomes. Never test an error-or-unavailable disjunction. Synthetic
fixtures prove mechanics, not financial performance. Validate chart examples
against the PDF visually; do not infer precise hidden OHLC values from a picture.

## 6. Experimental protocol to register before execution

Create `method-design.md` after data/implementation review, before observing new
outcomes. This story does not preselect dates or pretend previously viewed months
are untouched. Inventory data coverage and prior evaluation/search history first.

- Freeze one base rule set, timeframe pair, warm-up, entry/exit policy, risk,
  costs and evaluation window. H4 context/H1 execution is a candidate, not a
  registered choice. Use prior causal warm-up history consistently.
- Compare the current price-only reference and the Miner-inspired base under
  matched economics, documenting unavoidable differences.
- Around the frozen Miner base, run a 2×2 candlestick disabled/enabled × relative
  quote-activity disabled/enabled matrix. Specify whether candle confirmation
  is a veto, trigger or feature; do not reuse model-path semantics accidentally.
- Register the primary comparison, trial ledger, any sensitivity cells, sample
  adequacy and multiplicity treatment. Record all failed and zero-trade cells.
  Do not select momentum settings or Fibonacci zones on evaluation returns.
- Use paired daily-equity analysis only when its sample-size and calibration
  prerequisites hold. Infeasible inference remains unavailable; do not change
  block length after viewing outcomes to obtain significance.
- Publish each run's full parameters beside returns, drawdown, trade count,
  costs, exposure and setup/veto/entry counts. Include open-position valuation,
  equity plots and long/short controls where needed to distinguish market drift.

## 7. Dependencies, handoff and definition of done

Reuse Stories 12/13/14 implementation only after verifying current ancestry.
Apply Story 10 readiness and Story 11 inference constraints. Review technical
debt TD-71 (same-bar OCO), TD-67 (financing), TD-59 (news availability if news
is later introduced) and TD-70 (code provenance). A relevant unresolved execution
defect blocks claims that rely on the affected behavior; do not assume its fix.

Maintain `progress.md` with worktree/branch/agent ownership, commands, results,
commits and next action. Add `qa-procedure.md`, the rule ledger, frozen protocol,
evidence and run-level parameter appendix during delivery. Update the tool SPEC,
README and PRD when behavior lands, and the monograph only with verified evidence
and correct book attribution. Explain what changed and why in each commit.

Before completion: run scoped Ruff, strict mypy, BDD, relevant native tests,
architecture/complexity and targeted mutation checks; attempt workspace
`make check` and `make audit` and report any inherited failures separately.
Build/verify the monograph if changed. Independent review must check causal timing
and order semantics, not just indicator arithmetic. Move to `done` only when all
agreed deliverables are committed, verified and documented with lessons learned.
