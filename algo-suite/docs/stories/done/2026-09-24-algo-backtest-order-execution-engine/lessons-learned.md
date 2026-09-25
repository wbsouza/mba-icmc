# Lessons learned — Spec 04a: algo-backtest order-execution engine

Track A (Wave 1, lane A) of the larger `04-algo-backtest-filter-chain-hybrid`
story: `OrderExecutor`, the `QCAlgorithm` skeleton (`engine/algorithm.py`), and
the brokerage-adapter port, proven against the real pinned LEAN container
(`quantconnect/lean:17748`). Build history: specifier → architect → hardener →
QA on `spec/04a-order-execution-engine` (`597dd9f`, `51c9c1f`, `a57ac05`,
`4ca4aae`, `905e14d`).

**A QA procedure doc can drift from the implementation without anyone lying.**
`spec-algo-backtest-order-execution.qa.md` asserted against `trades.parquet`
in three of four sections. Nobody invented that requirement dishonestly —
`SPEC.md` genuinely documents `trades.parquet` as the eventual trade ledger
(§6.1, full 11-column schema), and `artifacts.py`'s own docstring is equally
honest that today's real ledger is the deliberately-minimal `trades.json`
("not the final trades.parquet schema... later work"). Two true statements,
written at different times, pointed QA at an artifact that doesn't exist.
The fix wasn't picking a side — it was finding both truths and updating the
QA doc to match current reality while logging the gap explicitly
([`technical-debt.md`](../../../technical-debt.md) TD-37) so the eventual parquet-ledger work isn't lost.

**Writing the QA script instead of just reading the doc surfaces real bugs.**
Converting `spec-algo-backtest-order-execution.qa.md` into an executable
`run_order_execution_qa.py` (rather than eyeballing the doc as "probably
fine") caught two genuine defects: the unknown-brokerage-adapter path failed
with the wrong assumed exit code (validated inside the LEAN run at algorithm
`initialize()` time, not by CLI pre-flight — exit 1, not exit 2), and
`RunResult` had no `error` field at all, so a CLI caller saw only
`success=False` with the actual reason buried in a raw result JSON nobody
was told to open. Both were fixed in the same pass (`RunResult.error` sourced
from LEAN's `state.RuntimeError`, echoed to stderr by `cli.py`).

**Concurrent container tests need resource caps, not just isolation.**
Each `run_lean()` call already got its own container, temp dir, and results
dir — no shared mutable state, so concurrent runs were never at risk of
*wrong* results. The unaddressed risk was *host* resource exhaustion: an
unthrottled parallel run could start N ~10GB-image, memory-hungry LEAN
containers at once and starve the desktop — the same failure class as this
session's separate mutation-harness freeze incident (orphaned `pytest`
processes from `subprocess.run(timeout=)`), just via containers instead of
subprocesses. Fixed with two independent, stdlib-only guards: a hard
per-container memory/CPU cap (`LEAN_CONTAINER_MEM_LIMIT`/`LEAN_CONTAINER_CPUS`)
and a cross-process `flock`-based slot limiter (`LEAN_MAX_CONCURRENT`)
bounding how many containers run at once, both env-overridable, with an
explicit OOM-killed error naming the fix rather than a silent/confusing exit
code.
