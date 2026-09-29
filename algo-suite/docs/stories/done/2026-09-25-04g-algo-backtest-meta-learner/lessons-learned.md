# Lessons learned — Spec 04g: F7 meta-learner

**Fit a stacked combiner on data its base models never saw.** The first version fit the
logistic combiner on `split.train`, the same rows the per-family LightGBM models were fit on.
That leaks in-sample overfit into the calibration of p̂ₜ. After review (`e04de19`) it is fit
on `split.validation`, `split.test` stays reserved for evaluation, and a single-class
validation span fails fast.

**Pickled models don't survive a version gap between training and serving.** The LEAN
container ships older sklearn/LightGBM/numpy than the workspace, so a pickled model trained on
the host fails to load inside it. It was found during Spec 04h and fixed there with a
portable JSON model document (`chain/filters/f7_model_io.py`).

**Mutation testing a real fitting path is slow.** 74 of 180 mutants timed out, because every
mutant re-runs real LightGBM/LogisticRegression fits. This is tracked as TD-50: it needs a
file-scoped mutmut timeout or a seam around the fit, not more scenarios.
