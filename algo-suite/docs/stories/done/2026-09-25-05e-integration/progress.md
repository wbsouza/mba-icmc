# Progress — Spec 05e (integration, consolidates 05a–05d)

**Do not start until 05a, 05b, 05c, 05d are all merged.**

- [x] Confirm 05a, 05b, 05c, 05d all merged into the same base. 05a (deflated Sharpe) was
  **not** actually merged despite its checkbox — recovered from an unmerged branch
  (preserved only inside `.worktrees/QA/algo-analyze/`) and landed for real
  (2026-09-25). 05b/05c/05d were genuinely already on `main`.
- [x] Wire `deflated.py`, `significance.py`, `ablation.py`, `figures.py`, `summary.py`
  into `cli.py` — all five commands (`summary`, `metrics`, `significance`, `ablation`,
  `figures`) built, matching `docs/experiments.md` §2/§3 exactly (`--runs` as a
  repeatable Click/Typer option, e.g. `--runs a --runs b` — the doc's illustrative
  `--runs a b` shorthand isn't literal Click syntax; `docs/experiments.md`'s example
  commands were corrected to match).
- [x] End-to-end check: `tests/features/cli.feature` + `tests/steps/test_cli.py` exercise
  every command through the real Typer `CliRunner`, not just the underlying library
  call — deflation happening, the too-few-trades note, the implausible-Sharpe
  plausibility flag (`docs/experiments.md` §7.1), the two-run requirement for
  `significance`, the ablation delta + `--figure` output, both figure PDFs, and the
  fail-fast paths for missing artifacts.
- [x] `make check` green (ruff, mypy strict, 73/73 pytest-bdd scenarios).
- [x] `make audit` green (no known vulnerabilities; no new third-party dependency added).
- [x] `algo-analyze/SPEC.md` written fresh — the previous one existed only on an
  unmerged branch and was never actually present on `main` to update.
- [x] `docs/stories/00-PLAN.md` §1/§2 updated: Spec 05 (all lanes) marked done, Spec 06
  unblocked.

**Incidental fixes made along the way (both real, pre-existing, blocking `make check`,
neither caused by this task):**
- `.venv/bin/pytest`'s console-script shebang pointed at a *different* sibling repo's
  venv (`mba-tlc/algo-suite/.venv`) — a stale artifact from however this venv was
  created. Fixed via `uv sync --reinstall-package pytest`; scanned all of `.venv/bin/*`
  for the same issue, found no others.
- `pyproject.toml`'s `[tool.mypy]` had no override for `matplotlib` (ships no
  `py.typed`) — added, matching the existing `testcontainers`/`docker`/`gdeltnews`
  pattern.
