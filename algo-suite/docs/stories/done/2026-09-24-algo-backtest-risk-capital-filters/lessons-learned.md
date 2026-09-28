# Lessons learned — Spec 04d: algo-backtest risk & capital-management filters (F5/F6)

**This is formula implementation + unit-level proof, not a legacy-code port.** The
original spec framed this story as "port the EJB version's ... into `rules/`" and its DoD
said "reproduces legacy decisions on identical synthetic input" — but the EJB version's
Java repo is not present in this checkout, only a reference (specs.md §14.5,
private repository). `progress.md`'s own correction
note (already recorded before this session started) flagged this and redirected the
work to implementing the formulas/constants specs.md states verbatim (§14.5–§14.8) with
hand-computed Gherkin expected values proving the arithmetic, rather than a diff against
inaccessible legacy code. The DoD's "reproduces legacy decisions" language is satisfied
here in the only way available: every formula scenario's expected value is computed
independently by hand from the stated formula (e.g. `lot_size = (10000*0.03)/(1.0*20) =
15.0`, verified before writing the `.feature`), not copied from a Java trace that can't
be run. This is a genuine scope deviation from the original spec.md wording, recorded
here per the team-lead's explicit instruction to say so plainly.

**The formulas' "±" sign is not uniform across all three trail-stop formulas.**
specs.md §14.5 writes `entry ± (...)` identically for `target_level`,
`trail_stop_at_level`, and `trail_stop_to_level`, which reads at first as "one sign,
resolved by trade direction, applied the same way to all three." But §14.7's own worked
description of the reference strategy ("trail-stop destination: entry − 66% × SL distance" for a
presumed long/BUY trade) only makes trading sense if `trail_stop_to_level` moves in the
*loss* direction from entry (a tightened stop-loss, still below entry for a BUY) while
`target_level` and `trail_stop_at_level` move in the *profit* direction (the take-profit
price, and the price excursion needed to arm the trail). Implemented with an explicit
`Direction` enum and a `_profit_sign()` helper, with the asymmetry documented in
`trail_stop.py`'s module docstring — this is an interpretive call against an ambiguous
notation, not something the (inaccessible) EJB version's source could disambiguate, so it's
recorded here rather than asserted as fact.

**Config resolution has a latent cross-schema gap this story didn't fix.**
`algo_core.config.resolve(tool, schema, version)` rejects any config key not in the
`schema` passed to *that* call (`_reject_unknown` in `algo-core/.../loader.py`). Both
`risk_guard.py`'s `load_risk_guard_caps()` and `f6_capital_mgmt.py`'s
`load_capital_mgmt_config()` call `resolve("backtest", ...)` independently, each with its
own partial schema — same tool namespace, same `conf/backtest.yaml`, as does
`algo-backtest/config.py`'s own `load_backtest_config()` (Spec 04b, `markets.oanda.data_tz`
only). If a real `conf/backtest.yaml` ever carried keys from more than one of these three
schemas at once, whichever `resolve()` call runs would reject the other schemas' keys as
unknown. This story's own boundary explicitly forbids touching `algo-backtest/config.py`
(not in the "only create" file list), so unifying the schema into one call is out of
scope here — each rule module resolves its own slice independently, per the task brief's
"your call how to thread it." Logged as **TD-43** (promoted from this prose note during
review — it fits the ledger's exact pattern, e.g. TD-27's identical split-brain-config
shape, and the ledger is the searchable place this belongs, not a per-story paragraph).

**Mutation testing found real boundary-condition gaps beyond the message-text-canary
class already known from TD-34/TD-36.** Of 380 mutants across the six new files (plus
`chain/model.py`'s pre-existing 3 survivors from Spec 04b), the first pass left 44
survivors; most were genuine gaps, not canaries — every RiskGuard cap's `>`/`>=`/`<`/`<=`
boundary needed an exact-at-cap scenario (a value *equal to* a cap must not breach it,
except `max_concurrent_trades_per_account` which breaches *at* the cap, not only past
it — the two caps have opposite boundary semantics by design: risk/leverage caps are
"don't exceed," the trade-count cap is "don't reach"), every `FilterResult`'s
`filter_name`/`recommendation` fields had no assertion at all, and F6's margin check
needed an exact-equal-to-available-margin scenario. Strengthening tests for these
(9 new/expanded scenarios across `risk_guard.feature`, `f5_risk_guard.feature`,
`f6_capital_mgmt.feature`, `close_portion.feature`) brought survivors down to 19 — killing
25 of the 44. Logged the remaining 19 as three new technical-debt items (TD-40 message-text
canaries — the same class as TD-34/TD-36; TD-41 confirmed-equivalent `veto=False`-kwarg
mutants, unkillable by construction since `FilterResult.veto` already defaults to `False`;
TD-42 an epsilon-tolerance boundary mutant impractical to hit with any meaningful
percentage ladder) rather than chasing them, per the team-lead brief's explicit guidance.

**Note (unrelated, flagged not fixed):** same pre-existing drift Spec 04b already noted —
`algo-analyze/` has no directory at all in this checkout (not just a missing
`pyproject.toml`), so `uv sync --group dev` during this story's setup regenerated
`algo-suite/uv.lock` without the `algo-analyze` workspace member (an 18-line diff dropping
its resolution-marker entry and package block). Left untouched and uncommitted; it
belongs to whoever owns the `algo-analyze` lane, not to Spec 04d.

**A single-element list join doesn't exercise a join separator.** The first mutation pass
left `f5_risk_guard.py`'s `"; ".join(...)` separator mutant alive because every existing
scenario had exactly one breach — joining a one-element iterable never touches the
separator. Added a two-simultaneous-breach scenario specifically to exercise it; it still
survives as a message-text canary (the mutated `"XX; XX"` separator still contains the
literal substring `"; "`), but the scenario itself was a real coverage gap worth closing
regardless of whether it fully kills that particular mutant.

## Post-review fixes (PR #8)

An independent review (Forgejo PR #8) found 4 real issues after the story was first marked
done; all fixed on the same branch before merge:

1. **`risk_math.risk_per_trade`, not `capital_mgmt.risk_per_trade`.** F6 registered a new
   config key under a namespace (`capital_mgmt.*`) this repo's own config contract never
   uses — `specs.md` §14.9.4's canonical sample YAML and startup-log trace both use
   `risk_math.risk_per_trade`. A config file written to the documented schema would have
   hard-stopped in F6 as "missing `capital_mgmt.risk_per_trade`." Renamed the schema key
   (and the fixture-writing test steps that constructed the old section name) to match.
2. **`trail_stop_to_level`'s sign convention didn't match the documented config value.**
   `specs.md` §14.9.4 carries `strategy_math.trail_stop_to_level_factor: -0.66` (negative)
   in its canonical sample config, but the scenarios here were passing a positive `0.66`
   and the function's `entry - profit_sign*offset` formula only produced the documented
   loss-side destination for that positive convention — passing the *actual* config value
   flipped the result to the profit side. Fixed by normalizing the factor to its magnitude
   inside `trail_stop_to_level` (`abs(trail_stop_to_level_factor)`) so a caller can pass
   the real signed config value and get the direction-correct result; updated both
   scenarios to pass `-0.66`, proving the normalization rather than an undocumented
   convention.
3. **`_require_int` silently truncated a fractional value via `int()`.** `state.features`
   gives no type guarantee, so an upstream filter could hand F5 a float
   `account_open_trade_count` (e.g. `2.9`), which `int()` would round away instead of
   rejecting — exactly the kind of silent coercion this module's own fail-fast convention
   elsewhere forbids. Changed to an `isinstance(value, int)` check (excluding `bool`, which
   is an `int` subclass in Python) raising `TypeError`, plus a new scenario proving a
   fractional count fails fast rather than truncating.
4. **Stale `SPEC.md` ownership comment.** `strategy_math.py`'s dir-tree line still credited
   it with "target ladder, trail-stop" after `trail_stop.py` (this story) actually
   implemented both — narrowed to "stop-level stretch" so a future reader isn't misled
   about which module owns what.

Re-ran the full gate after all four fixes: 121 passed (up from 120 — the new
fractional-open-trade-count scenario), ruff/mypy clean, mutmut re-run scoped to the same
files: 387 mutants (up from 380 — the new `_require_int` branch and `trail_stop`'s `abs()`
call), 365 killed (up from 361), 22 survived. All 22 verified individually: 0 are new
gaps — 16 are the existing message-text-canary class (TD-40, updated from 13 to include 3
new `_require_int` message-text mutants), 2 are the existing `veto=False`-equivalent class
(TD-41, unchanged), 1 is the existing epsilon-boundary-equivalent class (TD-42, unchanged),
3 are the pre-existing, unrelated `chain/model.py` TD-36 canaries. Net non-`chain/model.py`
survivor count held exactly at 19 before and after — the fixes redistributed which mutants
survive (my two new checks introduced their own small message-text-canary tails) without
introducing or hiding a real gap.

A separate reviewer finding on TD-43 (the config split-brain across F5/F6/`config.py`) was
**not** fixed here — the reviewer explicitly called it a fast-follow, not a blocker
("failure is loud... not requesting changes on this PR alone"), and fixing it means
touching `algo-backtest/config.py`, outside this story's file boundary and shared with
Spec 04b/04c's concurrent work.
