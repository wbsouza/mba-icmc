"""Adaptive recency-weighted retraining (Story 19).

Host-side components of the consume -> mature -> fit -> validate -> publish cycle:
`ingestion` (availability watermark and label maturity), `schedule` (exact-UTC monthly
epochs and stage spans), `weights` (exponential recency weights and support checks),
`bundle` (immutable, content-addressed epoch bundles), `thresholds` (separate-span
q10 threshold calibration), `trainer` (orchestrates one policy epoch end to end) and
`cycle` (the checkpointed consume -> mature -> fit -> validate -> publish coordinator).
The frozen protocol lives in
`docs/stories/in-progress/19-adaptive-recency-retraining/method-design.md`.
"""
