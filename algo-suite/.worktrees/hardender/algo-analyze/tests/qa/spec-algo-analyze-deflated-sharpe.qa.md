# QA procedure — algo-analyze: deflated Sharpe ratio

Scope note: unlike every other QA doc in this repo, this one is **not**
CLI-driven. Per the task boundary, this lane builds
`algo_analyze.deflated_sharpe.deflated_sharpe()` (or `algo_analyze.deflated`
per `algo-analyze/SPEC.md`'s module tree — the implementer resolves that
naming; see the note in the spec commit) as a **pure, importable function
only** — `cli.py` is explicitly out of scope here (wired later by the
integration lane, Spec 05e). There is no user-facing command to drive yet, so
"the user interface" for this lane is the Python public function signature
itself. Convert each check below into an executable script per
`swarmforge/roles/QA.prompt` once 05e lands the CLI; until then, run these as
a small driver script that imports and calls the function directly (not a
dig into private internals — the one public entry point is itself the
interface under test).

Executable script: `run_deflated_sharpe_qa.py`.

## 1. Deflation penalizes many trials (golden value)

1. Call the function with an observed Sharpe of `0.5` computed from 100 trade
   returns, `skew=0.0`, `kurtosis=3.0`, `n_trials=50`.
2. Expect: return value `0.2573452749201449` (tolerance `1e-9`) — per the
   formula in `tests/features/deflated_sharpe.feature`.
3. Expect: the returned value is strictly less than the observed Sharpe
   (`0.5`).

## 2. A single trial is an exact no-op

1. Call the function with the same inputs as §1 but `n_trials=1`.
2. Expect: return value exactly `0.5` (the expected-max-of-one-draw term is
   `0`, so no haircut is applied — this must hold exactly, not just
   approximately, since it is a direct algebraic consequence of the formula).

## 3. Zero-variance returns fail fast

1. Call the function with a `returns` array where every value is identical
   (sample variance `0`).
2. Expect: a raised exception (not a silently returned `NaN`/`inf`/`0.0`)
   whose message names the zero-variance input and explains the fix
   (per repo house rule: fail fast, state what failed/why/how to fix).

## 4. Determinism

1. Call the function twice with identical inputs.
2. Expect: byte-identical floating-point return value both times (no
   non-determinism from any internal random component — there should be
   none, since this is closed-form math, not simulation).

## 5. Handed to Spec 05e (not this lane's QA)

Documented for traceability, not executed here: once the integration lane
wires `algo-analyze significance --run <id>` to this function, QA gains a
real CLI-driven end-to-end procedure (SPEC.md §8's "Feature: Deflated Sharpe
ratio" scenarios, `algo-analyze/SPEC.md` §7's "`n_trials < 2` → report
undeflated with an explicit note" wrapping behavior). That reporting/caveat
behavior is explicitly out of scope for this pure-function lane — see the
05a lane spec's note that Spec 05e owns wiring the plausibility-band flag.
