# Lessons learned — Spec 05a: algo-analyze deflated Sharpe ratio

**Sourced from the specifier → architect → coder → cleaner → hardener → QA
pipeline commits on `algo-score-event-features`** (`d93aa6c`, `b6d8bd5`,
`73cbb05`, `cfd9015`, `102e650`, `2d3d247`, `be0abb6`).

**Leave a filename pick as an explicit, non-blocking note when two docs
disagree on it.** `d93aa6c`'s commit flagged that the 05a lane doc named the
module `deflated_sharpe.py` while `algo-analyze/SPEC.md`'s own file tree said
`deflated.py` — not a behavior conflict, so it was left as "implementer's
choice, SPEC.md's name is the recommended default" rather than blocking spec
completion on reconciling two docs. Not every inconsistency needs to be
resolved before work proceeds; some just need to be named so nobody trips
on them silently.

**Untested "obvious" branches are where the real bugs hide.** The hardener
pass (`102e650`) found `deflated_sharpe()`'s `returns=` raw-inference success
path, its own parameter defaults (skew/kurtosis/n_trials), and several
`_validated_inputs` boundary/message branches all untested. Closing them
surfaced two real logic gaps: `skew*sharpe` vs `skew/sharpe`, and
`n_returns<2` vs `n_returns<=2` — both boundary-condition bugs that a
golden-value fixture alone hadn't caught. Adding deflated-sharpe-06..10
(raw-returns inference, omitted-defaults, `n_returns=2` boundary,
`variance_term=0/1` boundary, non-zero-skew golden value) took mutmut
survivors on this file from 31 → 20.

**A build tool's scratch output can silently corrupt your own gate.**
`be0abb6` found that `mutmut`'s `mutants/` directory (a full per-package copy
of `src/`+`tests/`, regenerated every `mutmut run`) had no pytest exclusion —
so a plain `make check` from the workspace root recursed into it and
re-collected/re-ran every affected tool's whole test suite as if it were
real, duplicating results. Fixed with `norecursedirs` in the workspace
`pyproject.toml` (pytest's defaults + `"mutants"`); ruff/mypy already had
their own exclusion configured earlier in the same pass, but pytest didn't
inherit it — each tool in the chain (lint, type-check, test) needs its own
explicit exclusion; assuming one tool's ignore rule covers the others is how
this kind of gap gets in.
