# Lessons learned — Spec 03: algo-score LM lexicon scorer + event features

**Sourced from the specifier → architect → coder → cleaner → hardener → QA
pipeline commits on `algo-score-event-features`** (`3fbbccf`, `874dfd7`,
`76eb2d6`, `4993799`, `e7a7d2a`, `e715757`, `95b6719`, `182282a`, `7f42d73`,
`102e650`, `b7d56f2`).

**Resolve a formula ambiguity with the operator before implementing, not
after.** `3fbbccf`'s spec shipped with the GDELT aggregation formula "pending
clarify"; `874dfd7` resolved the `event_intensity` formula per an explicit
operator answer before the spec was marked complete. Shipping a spec with a
flagged-but-unresolved formula is fine as an intermediate state as long as
nothing downstream starts building against it first.

**Split by responsibility, not by convenience, when a CRAP-gate function is
too complex.** The hardener pass (`102e650`) found `attribution.py`'s
`symbol_features` at cyclomatic complexity 17 (grade C, failing the ≤10 gate
regardless of coverage). Split into `symbol_features` (loop only),
`_pair_feature` (one currency pair's base/quote combination), and
`_polarity_or_zero`; max complexity dropped to 9 (grade B). Complexity
usually clusters around one un-abstracted concept (here: "what does one
pair contribute") — naming that concept is the fix, not just moving lines.

**A new CLI package can reach 90%+ line coverage on its features and still
have zero coverage on argument validation.** `102e650` found `algo-score/
cli.py` had no `cli.feature`-equivalent scenarios for its own argument
rejection paths (unknown scorer, `--month`/`--from` conflict, bad date
formats, `--from`-after-`--to`, missing month/range). Feature coverage and
CLI-surface coverage are different axes; a spec's Definition of Done should
check both explicitly, not infer one from the other.

**Full mutation coverage isn't always in-scope for a hardening pass.**
algo-score's mutmut run: 993 mutants, 161 survived. Rather than close all of
them, they were logged as [`technical-debt.md`](../../../technical-debt.md) TD-35 — closing ten files'
worth of first-pass mutation debt is out of proportion to a task scoped to
one behavior change (event features + LM scorer), and that diff was already
at 95-100% line coverage via `scoring.feature`/`event_features.feature`.
Matching remediation effort to what the task actually touched, and logging
the rest with a trigger, kept the day's schedule intact.
