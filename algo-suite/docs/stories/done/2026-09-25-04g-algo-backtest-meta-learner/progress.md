# Progress — Spec 04g (F7 meta-learner)

- [x] Add `lightgbm` dependency to `algo-backtest/pyproject.toml` (also `scikit-learn` for the
      logistic meta-learner combiner, `numpy` for feature vectors — all workspace deps, not just
      declared)
- [x] LightGBM sub-models per feature family (trend/indicator/pattern/news — market-activity
      family intentionally excluded, no filter consumer yet per TD-29)
- [x] Logistic meta-learner combining sub-models into `p̂ₜ` (`sklearn.linear_model.LogisticRegression`)
- [x] Walk-forward split training (`PRD.md` §4) — `walk_forward_split()`, chronological
      train/validation/test, fail-fast on out-of-order boundaries or an empty span
- [x] F7 filter (`chain/filters/f7_meta_learner.py`) implements `Filter` interface — terminal
      threshold rule (monografia §"deterministic execution as a filter chain"): BUY/SELL/HOLD
      from p̂ₜ vs. theta_high/theta_low and the trend regime; never vetoes
- [x] `make check` green (algo-backtest + algo-score scoped run: 260 passed, 19 deselected
      network/integration; full-workspace run pending final pass — see final report)
- [x] Gauntlet (differential mutmut, `uncle-bob-agent-gauntlet`): 101/180 killed + 5 confirmed
      non-gaps (3 message-text canaries, TD-49 pattern; 2 confirmed-equivalent `"neutral"`
      string mutants) after adding boundary scenarios (`_regime`'s `>`/`<`/`==0.0`, `apply()`'s
      `theta_high`/`theta_low` boundaries), full `FilterResult` field assertions, a
      call-capturing stub proving `state.features` is wired straight through to the
      meta-learner, and `load_f7_config()` coverage (closed 19 "no tests" outright). 74
      mutants timed out (real LightGBM/LogisticRegression fits under mutation are slow/
      variable-latency) — new debt TD-50, deferred (needs a file-scoped mutmut timeout or a
      fit-seam refactor, out of this story's differential-pass budget).
- [x] `lessons-learned.md` written, story moved to `docs/stories/done/`

## Closure (recorded 2026-09-26)

Definition of done met by `a1e7b8b` (2026-09-25): `lightgbm` declared in
`algo-backtest/pyproject.toml`, F7 implements `Filter`
(`algo-backtest/src/algo_backtest/chain/filters/f7_meta_learner.py`), walk-forward split training
covered by `algo-backtest/tests/features/f7_meta_learner.feature`. The story folder stayed in
`planned/` by oversight and was moved to `done/` on 2026-09-26.

Later changes to F7 (not part of this story, listed so this record isn't read as current):
- `e04de19` (2026-09-25, PR #25 review): the logistic combiner is now fit on `split.validation`,
  not on the family models' own training rows (that was in-sample leakage). It fails fast when
  the validation span is single-class.
- Spec 04h (`../2026-09-26-04h-algo-backtest-hybrid-integration/`, PR #40): models are
  persisted as portable, pickle-free JSON (`chain/filters/f7_model_io.py`,
  `tests/features/f7_model_io.feature`), because the LEAN container's library versions can't
  load a pickle. They are trained by `algo-backtest/scripts/train_{baseline,hybrid}_meta_learner.py`
  and loaded by `algos/{baseline,hybrid}/main.py`. `walk_forward_split` now drops rows whose
  15-minute label crosses a split boundary (`176fb2b`).
