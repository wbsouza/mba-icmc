# Lessons learned — Spec 04d: algo-backtest risk & capital-management filters (F5/F6)

**This is formula implementation + unit-level proof, not a legacy-code port.** The
original spec framed this story as "port `fx-manager`'s ... into `rules/`" and its DoD
said "reproduces legacy decisions on identical synthetic input" — but the `fx-manager`
Java repo is not present in this checkout, only a URL reference (specs.md §14.5,
`https://git.disposalqueen.com/algo-trading/fx-manager`). `progress.md`'s own correction
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
description of Strategy A05 ("trail-stop destination: entry − 66% × SL distance" for a
presumed long/BUY trade) only makes trading sense if `trail_stop_to_level` moves in the
*loss* direction from entry (a tightened stop-loss, still below entry for a BUY) while
`target_level` and `trail_stop_at_level` move in the *profit* direction (the take-profit
price, and the price excursion needed to arm the trail). Implemented with an explicit
`Direction` enum and a `_profit_sign()` helper, with the asymmetry documented in
`trail_stop.py`'s module docstring — this is an interpretive call against an ambiguous
notation, not something the (inaccessible) fx-manager source could disambiguate, so it's
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
