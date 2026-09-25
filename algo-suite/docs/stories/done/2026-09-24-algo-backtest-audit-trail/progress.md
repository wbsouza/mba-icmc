# Progress — Spec 04f (decisions.parquet audit trail)

Own worktree/branch (`feat/04f-audit-trail`), disjoint files from 04c/04d — safe to run
fully in parallel with them.

Reuse `algo_core`'s `ParquetRepository[M]` (pydantic-generic Parquet writer,
`algo-core/src/algo_core/repository/parquet.py`) rather than writing pyarrow ad hoc — define
a pydantic `DecisionRow` model for the §11.3.4 column set and map `ChainOutcome`/
`ExecutionState`/`FilterResult` (plain dataclasses) onto it explicitly.

`trades.parquet` doesn't exist yet (Spec 04a, in flight elsewhere) — the join-by-`trade_id`
scenario below proves the *schema* is join-ready (a `trade_id`-keyed row shape), not an
actual join against a real `trades.parquet`; the real join is Spec 04h's integration test.

- [x] T1 — `chain/audit.py`: `DecisionRow` pydantic model, full §11.3.4 columns (`timestamp`,
      `pair`, `features_hash`, `filter_results` (list[struct]), `final_decision`,
      `vetoed_by`), plus a `trade_id` key field for the future join
- [x] T2 — `chain/audit.py`: conversion function `ChainOutcome` (+ pair/trade_id context) →
      `DecisionRow`, `features_hash` computed over `outcome.state.features` at write time
      (documented: this is the accumulated feature set at chain completion, since
      `ChainOutcome` doesn't preserve a separate pre-chain snapshot — see 04b's aliasing note)
- [x] T3 — `chain/audit.py`: writer function using `ParquetRepository[DecisionRow]`
- [x] T4 — `tests/features/audit.feature`: scenario — one audit row persisted per chain
      decision, with the full column set; scenario — a veto's `vetoed_by` is recorded;
      scenario — the row's `trade_id` key makes it join-ready (schema-level proof only)
- [x] T5 — gate: `make check` green; mutation pass on `chain/audit.py`
- [x] `lessons-learned.md` written, story moved to `docs/stories/done/`
