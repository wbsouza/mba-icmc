# Lessons learned — Spec 04f: algo-backtest decisions.parquet audit trail

**A pydantic nested model round-trips through `ParquetRepository`, but only with a
uniform dict shape across rows.** `DecisionRow.filter_results: list[FilterResultRow]`
(a `list[BaseModel]` field) dumps to a Parquet `list<struct<...>>` column exactly as
expected — no surprises there. The surprise was `FilterResultRow`'s `enrichment`/
`metadata: dict[str, object]` fields: `algo_core.repository.serde.to_table` builds the
Arrow table via `pa.Table.from_pylist`, which infers **one struct schema per column
across the whole table** from the python dicts it sees. Two concrete failures fell out
of this: (1) an empty `{}` in one row next to a non-empty `{"k": True}` in another
silently round-trips as `{"k": None}` — data corruption, not a crash; (2) an empty `{}`
with *no* sibling non-empty dict anywhere in the batch infers a **childless struct
type**, which pyarrow's Parquet writer rejects outright (`ArrowNotImplementedError:
Cannot write struct type 'enrichment' with no child field`). Both are pre-existing
`algo_core.repository.serde` limitations, not something Spec 04f owns or should fix
(out of this story's `chain/audit.py`-only boundary) — worked around by giving every
`FilterResult` in the test suite a non-empty, identically-shaped `enrichment`/
`metadata`. A future filter (F1-F7) that legitimately emits no enrichment, or filters
with differently-shaped enrichment dicts in the same batch, will hit this for real;
not logged as a new TD entry only because no real filter exists yet to hit it — Wave 2
filter work should watch for it.

**`features_hash`'s determinism needed its own dedicated scenarios, not just an
equality check against the same code path.** The first-draft `Then` step asserted
`row.features_hash == _hash_features(audit_ctx.features)` — calling the *same*
function under test to build the expected value. Under mutation testing this is
nearly worthless: a mutant that makes `_hash_features` ignore its argument (hash
`None` unconditionally) or drop `sort_keys=True` produces the *same* wrong value on
both sides of that assertion, so it always passes. Three standalone property
scenarios actually pin the contract: same content in a different key order hashes
identically (kills `sort_keys` removal), different content hashes differently (kills
argument-ignoring mutants), and a non-JSON-native value (a `set`) hashes without
raising (kills `default=str` removal). 7 of 9 `audit.py` mutmut survivors were closed
this way; the other 2 are logged as `TD-37`/`TD-38` (technical-debt.md) —
`"utf-8"` vs `"UTF-8"` is a confirmed-equivalent mutation (Python's codec registry is
case-insensitive), and `ParquetRepository(None, path)` survives because `put()`
never reads `self._model` (only `read_all()` does), so `write_decisions`'s write-only
path can't observe the swap without touching `algo_core` itself.

**`trade_id` is not in `specs.md` §11.3.4's table but was added anyway, per the
task brief's own design decision** — Spec 04h (hybrid integration) and Spec 05c
(ablation) need to join `decisions.parquet` against the future `trades.parquet` by
trade, and §11.3.4 assumes that join key without naming a column for it. The
`trade_id`-carries-through scenario in `audit.feature` proves the schema shape only
(no real `trades.parquet` exists yet to join against — that join is Spec 04h's job).

**`ChainOutcome.state`'s own aliasing caveat (Spec 04b) mattered immediately.**
`decision_row_from_outcome` hashes `outcome.state.features` as found — the
accumulated feature set at chain completion — because `ChainOutcome` keeps no
separate pre-chain snapshot to hash instead. Documented in the conversion
function's docstring rather than worked around, since a caller needing a pre-chain
snapshot would need to capture one itself before calling `FilterChain.run()` — not
something `chain/audit.py` can retroactively reconstruct.
