# Lessons learned — Spec 04h (hybrid strategy integration, final)

## What actually happened

This story closed across two sessions with a real gap in between: an earlier pass built
`algos/baseline/main.py` and proved the F1+F2+F3+F5+F6+F7 chain wired correctly against
the real pinned LEAN container, but deliberately deferred `algos/hybrid/main.py` and the
`decisions.parquet`↔`trades.json` join to avoid NAS I/O contention with an unrelated
concurrent backfill. This final session closed both remaining items and, in doing so,
found three real production bugs that only surface once a chain-driven algorithm
actually exercises these code paths for the first time inside the real container —
none of which any amount of pure-Python unit testing could have caught, because they
are all container-environment-specific:

1. **`algo_core.repository`'s package `__init__.py` eagerly imported `DuckDBRepository`**
   (and therefore the real `duckdb` package) as a side effect of importing anything in
   that package, including `ParquetRepository`. The pinned LEAN container ships
   `pyarrow` but not `duckdb` — confirmed by TD-51's own earlier package-set check,
   which never had a reason to test `duckdb` because nothing had imported it inside the
   container before. The very first real `algos/baseline/main.py` run (once it started
   writing `decisions.parquet` via the new `DecisionRecorder`) failed immediately with
   `No module named 'duckdb'`. Fixed with a lazy `__getattr__` (PEP 562) — `Repository`
   and `ParquetRepository` stay eager; `DuckDBRepository` resolves on first access.
2. **An all-empty `enrichment`/`metadata` batch crashes pyarrow's Parquet writer.**
   `FilterResult`'s dataclass default for both fields is `{}` — the common case, since
   most filters (F1/F2/F3/F5/F6) never set either. pyarrow infers a *childless* struct
   type from an all-empty-dict column, and its own writer refuses to write that type
   ("Cannot write struct type 'metadata' with no child field to Parquet"). This was
   invisible in every prior unit test because `audit.feature`'s own fixtures
   deliberately used non-empty dicts to sidestep exactly this pyarrow limitation (see
   that file's own comments) — a real production input shape was never actually
   exercised through the real writer until this session's first real run. Fixed by
   mapping an empty dict to `None` at the `FilterResultRow` boundary, verified
   empirically against the real pyarrow writer (all-`None` infers a `null` column;
   mixed `None`/populated infers a real struct with per-row nulls — both writable)
   before landing the fix.
3. **`lean_runner.py` never copied `algo_score` into the container.** F4 imports
   `algo_score.events.models`/`.paths` to read the real Spec 03 news Parquet; no
   previous algorithm (`baseline`, `baseline_ma`, `experiment_zero/*`) ever imported
   `algo_score`, so this gap was invisible until `hybrid` — the first algorithm to use
   F4 — actually ran. Fixed by copying `algo_score`'s source tree in unconditionally,
   same pattern as `algo_core`/`algo_backtest`.

## Vs. the spec

- The spec's own remaining-scope framing (`docs/technical-debt.md` TD-51, written by
  the prior session) correctly identified "the LEAN-container integration layer" as the
  single largest remaining piece, but underestimated its shape: it expected the work to
  be mostly *additive* (write two `main.py` files, wire indicators), not also
  *diagnostic* (three real, previously-invisible cross-cutting bugs in already-shipped
  shared infrastructure — `algo_core.repository`, `chain/audit.py`, `lean_runner.py`).
  This matches a general pattern worth naming: the first real end-to-end run of any
  layered system tends to surface integration bugs that no amount of testing each layer
  in isolation catches, because the bug lives at the boundary between layers, not inside
  either one.
- The user explicitly descoped the GPR corpus and GDELT-ngrams sentiment ingestion for
  this pass (time pressure ahead of a 2026-09-29 deadline), which the original 04h spec
  had listed as open items (`docs/technical-debt.md` TD-56's own "GPR lane... has never
  been run at all" note). This is a legitimate scope narrowing, not a shortcut: TD-56's
  own coverage-rule caveat already anticipated a single-corpus fallback
  ("if coverage thins out, we report a narrower, honestly-justified window"), and
  running `algo-transform coverage` against the real single-GDELT-corpus window
  confirmed it reports `selected window: none` — the coverage rule's automated window
  selector does not (yet) gracefully degrade to one corpus. The manually-chosen
  2015-02-02→2015-02-06 window (matching `baseline`'s own prior real run, for direct
  comparability) is honestly documented as manually chosen, not derived from the
  coverage rule, consistent with `baseline`'s own precedent.
- `decisions.parquet`'s `trade_id` join was originally scoped against `trades.parquet`
  (a name TD-47 had already corrected to the real `trades.json` ledger) — the actual
  join key that emerged during implementation is LEAN's own `orderIds[0]` (the entry
  order id), not a UUID or a newly-invented identifier. This wasn't specified in advance
  because no one had looked at a real `trades.json` file's actual shape until this
  session — the spec described the *concept* of a join, not its concrete mechanism.

## What would be done differently

- **Mutation-testing scope expansion surfaces pre-existing debt, and that's a feature,
  not a bug — but it needs to be budgeted for.** Adding `run.py` to `only_mutate` for
  the first time (needed to cover the new `_validate_hybrid`) swept in every other
  strategy's validator and shared helper, most never mutation-tested before. This
  surfaced a real, pre-existing `_check_keys` logic gap (`or`→`and` would silently admit
  invalid params) that was fixed on the spot because it's directly reachable by
  `hybrid`'s own new validation path — but ~70 other survivors (message-text canaries
  plus two `lean_data_covers`/`validate_run_inputs` boundary-condition bugs) were
  deliberately left as documented debt (TD-57) rather than absorbed into this story's
  diff. Next time a file is added to mutation scope for the first time, budget review
  time for "does this file already have pre-existing survivors unrelated to my change,"
  and decide the fix/defer line explicitly rather than either chasing everything or
  ignoring everything found.
- **mutmut's own result cache silently returned stale data twice** after new test
  scenarios were added but the mutated source didn't change — `mutants/mutmut-stats.json`
  needed to be cleared (`rm -rf mutants/`, gitignored, fully regenerated) to force a
  genuine re-run. Anyone re-running a differential mutmut pass after only touching test
  files (not source) should clear this cache first rather than trusting an
  instant/identical-looking rerun.
- **A test's exit-code-only assertion masked a real behavioral bug.** The pre-existing
  "an unknown param is rejected" scenario asserted only `exit code == 2`, which stayed
  true under the `_check_keys` `or`→`and` mutation because the same fresh, unmaterialized
  test data root *also* fails the unrelated "no lean-data" check with the same exit
  code — two independent failure paths coincidentally producing the same code. The fix
  (asserting the actual `"params must be exactly"` message substring) is a small,
  general lesson: an exit-code-only assertion on a CLI command with multiple possible
  failure paths is a real, not hypothetical, source of false test confidence.
- **The venv's console-script shebangs went stale after a directory rename** (`mba-tlc`
  → `mba-main`), breaking `uv run mutmut` with a misleading "Failed to spawn" error
  while leaving compiled-binary tools (`ruff`) and `uv run python -m <tool>` unaffected.
  Diagnosed and worked around (module invocation) rather than rebuilding the shared
  venv mid-session, per TD-54's own "don't `rm -rf` immediately, capture diagnostics
  first" precedent — documented as TD-58 for whoever eventually rebuilds this venv.
