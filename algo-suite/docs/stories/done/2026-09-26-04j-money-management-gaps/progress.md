# Progress — Spec 04j (money-management port gaps)

- [x] `close_portion.py` remainder-to-last-target rounding fix implemented
- [x] `close_portion.feature` uneven-split scenario added (last rung remainder = 0.0 exactly)
- [x] `specs.md` §14.8 dated amendment added (the Spring version's risk-provider correction)
- [x] `make check` green (ruff clean; mypy clean for changed files — one pre-existing,
      unrelated `joblib` stub error in `scripts/train_baseline_meta_learner.py`; full
      suite 275 passed / 20 deselected integration/network)
- [x] `lessons-learned.md` written, story moved to `docs/stories/done/`
