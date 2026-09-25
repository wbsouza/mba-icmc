# Progress — Spec 05 (parent: algo-analyze metrics, significance, ablation, figures)

Split into lanes per `spec.md`. Track each lane's own progress in its own folder.

- [x] 05a — deflated Sharpe (done: `docs/stories/done/2026-09-23-algo-analyze-deflated-sharpe/`).
  **Correction (2026-09-25):** despite this checkbox, `deflated.py` was never actually
  merged into `main` — it existed only on an unmerged branch, and its files survived
  solely inside an accidentally-committed swarm-worktree copy at `.worktrees/QA/...`.
  Recovered and landed for real in the 05e integration pass below.
- [x] 05b — Monte-Carlo Permutation Test (`../../done/2026-09-24-significance-mcp/progress.md`)
- [x] 05c — ablation table (`../../done/2026-09-24-ablation-table/progress.md`)
- [x] 05d — figures. `figures.py` (`equity_curve_figure`/`drawdown_curve_figure`/
  `ablation_bars_figure`) was already real and merged (`feat(algo-analyze): add thesis
  PDF figures`, `fix(spec-05d): ...`) — this checkbox was simply stale, never updated
  when the work landed.
- [x] 05e — integration, consolidate 05a–05d (2026-09-25). Recovered `config.py`,
  `summary.py`, `deflated.py` from unmerged prior work; built `cli.py` wiring
  `summary`/`metrics`/`significance`/`ablation`/`figures` per `docs/experiments.md`
  §2/§3; wrote `SPEC.md` fresh (the old one was lost from `main` without ever being
  deleted in its own history — orphaned on a branch that never merged); `make check`
  and `make audit` green. See `../../planned/05e-integration/progress.md` for the
  detailed checklist.
