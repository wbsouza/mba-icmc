# Lessons learned — Spec 04g (F7 meta-learner)

## What actually happened

The spec's DoD was scoped to "walk-forward training reproducible" and F7 implementing the
`Filter` interface — both landed, but the shape of the sub-model ensemble deviated from a
literal reading of the spec: the "market-activity" feature family named in `PRD.md` §1 has
no filter that produces it yet (no F-something currently emits market-activity features
into `state.features`), so it was intentionally excluded from the per-family LightGBM
ensemble rather than trained against zero/placeholder data — tracked as TD-29, not silently
dropped.

## Vs. the spec

- "LightGBM sub-models per feature family" was implemented as trend/indicator/pattern/news
  (four families, matching F1/F2/F3/F4's real outputs), not all families PRD.md's abstract
  description implies — the concrete filter chain, not the PRD's idealized list, is the
  actual source of truth for which families exist to train on.
- The logistic combiner (`sklearn.linear_model.LogisticRegression`) and the terminal
  threshold rule (`apply()` comparing `p̂ₜ` against `theta_high`/`theta_low` plus the trend
  regime, F7 never vetoing) both matched the spec's intent without needing amendment.

## What would be done differently

Mutation testing on `f7_meta_learner.py` surfaced a real, project-specific limit rather than
a test gap: 74 of 180 mutants timed out because they mutate code paths inside real
LightGBM/LogisticRegression `.fit()` calls, and a mutated fit can be dramatically slower or
just hang under mutmut's default timeout — this is orthogonal to whether the behavior is
actually tested. Recorded as TD-50 (deferred: needs either a file-scoped mutmut timeout
override or a fit-seam refactor to make the model-training boundary mockable for mutation
purposes) rather than burning the story's differential-pass budget chasing timeouts that
aren't real behavioral gaps. Next time a story wraps a real ML `.fit()` call: budget for
this timeout class up front instead of discovering it mid-gauntlet-pass, and consider
whether the fit call itself needs a seam (an injectable trainer) before running mutmut, not
after. Of the mutants that did run to completion, 101/180 were killed and 5 were confirmed
non-gaps (3 message-text canaries in the TD-49 pattern, 2 confirmed-equivalent `"neutral"`
string literals with no observable behavioral difference) — those 5 needed no new tests,
only documentation, which is the right outcome for a genuinely equivalent mutant.
