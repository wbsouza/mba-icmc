"""Adaptive recency-weighted retraining (Story 19).

Host-side components of the consume -> mature -> fit -> validate -> publish cycle:
`ingestion` (availability watermark and label maturity), `schedule` (exact-UTC monthly
epochs and stage spans), `weights` (exponential recency weights and support checks) and
`bundle` (immutable, content-addressed epoch bundles). The frozen protocol lives in
`docs/stories/in-progress/19-adaptive-recency-retraining/method-design.md`.
"""
