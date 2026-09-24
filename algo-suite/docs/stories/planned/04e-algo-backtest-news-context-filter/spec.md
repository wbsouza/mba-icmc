# Spec 04e — algo-backtest: news-context filter F4 (lane of Spec 04, Wave 2)

**Parent spec:** `04-algo-backtest-filter-chain-hybrid` — read its `spec.md` §4 step 4, and
`specs.md` §11.3.2 for full context.
**Depends on:** Spec 04b landed (`chain/model.py`) **and** an external check: confirm Spec 03's
sentiment/event Parquet is actually present on the NAS data root
(`/media/nas/wellington/mba/algo-suite/data`, not visible from a sandbox without the mount) before
starting. **Blocks:** Spec 04g (meta-learner) only.
**Order:** Wave 2, lane E — start once 04b merges and the Spec 03 data check passes; runs in
parallel with 04c, 04d, 04f.
**Boundary (avoid merge conflicts):** `algo-backtest/src/algo_backtest/chain/filters/f4_news_context.py`
only.

## Objective

F4 vetoes on active high-risk events from Spec 03's per-pair sentiment + event features
(`specs.md` §11.3.2). This is the one filter with a real external-data dependency — do not start
implementation until the Parquet is confirmed on disk, to avoid building against a fixture that
doesn't match the real contract.

## Definition of done

- F4 implements the `Filter` interface, reads real Spec 03 Parquet (not a synthetic fixture) in at
  least one integration scenario, VETO/ABSTAIN scenarios covered.
- `make check` green.
