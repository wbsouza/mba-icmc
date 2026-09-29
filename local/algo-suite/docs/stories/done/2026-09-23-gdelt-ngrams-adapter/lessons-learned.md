# Lessons learned — GDELT Web News NGrams 3.0 raw adapter (TD-28)

This story has no `spec.md` here — it was never one of the numbered
`docs/stories` specs. It was discovered mid-session as a way to close
[`technical-debt.md`](../../../technical-debt.md) TD-28 (Spec 02 found no free article-text source behind
GDELT's raw Events table, blocking algo-score's text-sentiment path). Its
spec lives inline in [`algo-download/SPEC.md`](../../../../algo-download/SPEC.md); its build history is entirely
in the specifier → coder → cleaner → hardener → QA commits on
`algo-score-event-features` (`bb26537`, `9e4dc03`, `c7c8b8d`, `cbfc632`,
`63c1c23`).

**A blocked-debt ledger with a concrete trigger pays for itself.** TD-28 was
logged the moment Spec 02 found the gap (no article text in GDELT's raw
Events scope), with a specific trigger ("the free, public fix for algo-score's
FinBERT/LM text-sentiment path, found via research"). That trigger firing is
what turned into this same-day adapter — the debt entry did its job by being
concrete enough to act on later without re-deriving the problem from scratch.

**Differential mutation testing scopes hardening effort to what actually
changed.** `cbfc632`'s hardener pass ran mutmut across the tool's full
adapter surface (684 mutants, 166 survivors) but only closed the ~40 in this
task's own diff (`gdelt_ngrams/source.py`+`paths.py` fetch/throttle/retry
paths, `cli.py`'s new flag-priority scenarios). The remaining ~124 survivors
in sibling adapters (`gdelt`/`gpr`/`dukascopy`/`raw_http.py`) were logged as
debt (TD-31/32/33) rather than closed opportunistically — fixing unrelated
survivors while touching a file is scope creep even when the fix is easy.

**Don't force an artificial test to kill a mutant that represents dead or
equivalent code.** `cbfc632` documented specific mutants left alive on
purpose: `paths.py`'s `removeprefix`-vs-`removesuffix` front-slice case and
`cli.py`'s dead "unknown request shape" branch. Recording *why* a survivor
is acceptable (equivalent mutant / unreachable branch) is different from
silently ignoring it, and keeps the next hardening pass from re-litigating
the same mutant.
