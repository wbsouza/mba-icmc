# Lessons learned — Spec 04i (trail_stop_to_level formula fix)

**What the spec didn't anticipate:** the formula fix itself was straightforward once the real
the EJB and Spring versions' source was in hand. What the spec's original draft got wrong was
diagnosing a *local environment* problem as an *unresolved code/test defect* — the spec's first
version stated the test suite was "failing" and "untrusted," reproduced twice (once via `uv run`,
once bypassing it with the venv's `pytest` binary directly), and treated that as strong enough
evidence of a real bug to write up as an open problem for a future debugging session.

**What actually happened:** the failures were caused by a stale/corrupted long-lived shared
`.venv`, reused across several parallel story worktrees on this machine. Bypassing `uv run`
wasn't enough to catch it, because the *venv itself* — not the `uv run` wrapper — was the actual
variable. Two independent PR reviewers (a Codex session and a separate Claude session), each
running the identical suite in a disposable worktree with a fresh `uv sync`, got a clean 7/7 pass
immediately — contradicting the spec's own documented "unresolved" status and forcing a
correction pass on both `spec.md` and `progress.md` before the PR could be considered accurate.

**Takeaway for next time:** reproducing a failure twice on the same machine, even via two
different invocation paths, is not the same as reproducing it in a clean environment. When a test
failure's actual "Obtained" values don't match *any* plausible version of the code under test
(the tell here: a BUY scenario's result equaling the *SELL* scenario's expected value), that
specific symptom — cross-contaminated-looking output — should raise the shared/stale-environment
hypothesis earlier, before writing up a multi-hypothesis debugging plan as if the code or test
framework were suspect. `rm -rf .venv && uv sync` is a five-second check that should come before,
not after, drafting a systematic-debugging story for a test-runner mystery.

**Also corrected during review:** the original spec cited the EJB and Spring versions' formula
source only in prose, with no path/line/commit reference a future reader could verify — added
exact commit SHAs and approximate line numbers per reviewer feedback. And the zero-factor/
zero-spread edge-case scenarios were originally BUY-only, breaking this test file's own
BUY/SELL-mirror convention — SELL mirrors added.
