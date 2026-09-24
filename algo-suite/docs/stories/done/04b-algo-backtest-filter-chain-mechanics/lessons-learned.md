# Lessons learned — Spec 04b: algo-backtest filter-chain mechanics

**Sourced from the coder → hardener pipeline commits on
`feat/04b-filter-chain-mechanics`** (`2bdc3bd`, `3053266`, `3863df5`).

**A test double that ignores its own argument hides real mutants.** The
hardener pass (`3053266`) found 3 of 13 mutants survived — all three were
argument-replacement mutations (`apply(state)` → `apply(None)`,
`decide(state)` → `decide(None)`, `ChainOutcome(state=state)` →
`state=None`) that the stub `Filter`/`TerminalDecision` test doubles never
noticed because they didn't read the `state` they were handed. A stub that
returns a constant regardless of input proves the chain *calls* its
collaborators but not that it passes them anything real. Fix: make stubs
record what they actually received and assert on it — a test double should
honor its interface's contract (a `Filter` reads state; a decision-maker
interprets it), not just satisfy its type signature.

**`ChainOutcome` (a real dataclass) over a bare `tuple[Decision,
ExecutionState]`.** `specs.md`'s illustrative pseudocode for `FilterChain.run()`
returns a tuple; `algo-backtest/SPEC.md`'s own architecture diagram and dir-layout
comment already named a `ChainOutcome` return value. Reconciling the two in
favor of the tool's own SPEC.md (and CLAUDE.md's single-return-value-object
rule) cost nothing extra to implement and reads better at every call site.
When a parent spec's pseudocode and the tool's own architecture doc disagree
on a return shape, the tool's own SPEC.md wins — it's the more specific,
more current source for that tool's actual API surface.

**ABSTAIN needs no special-case branch.** `specs.md` §11.3.1 describes
ABSTAIN as "no opinion this bar" — implemented as just another
non-veto `FilterResult`; the existing veto check already handles it correctly
without any `if recommendation == ABSTAIN` logic. Naming a Decision/Recommendation
value in the enum doesn't obligate the chain loop to branch on it — sometimes
the absence of a branch **is** the correct implementation of a documented case.

**First mutation-hardening pass on a package needs its own `[tool.mutmut]`
scope block.** `algo-backtest/pyproject.toml` had no `only_mutate` scoping
before this story (it's this package's first hardener pass); every other
tool (`algo-score`, `algo-download`, `algo-analyze`) already carries one from
their own first pass. Adding it is expected boilerplate on a tool's first
mutation-testing story, not scope creep — future hardener passes on this
tool won't need to repeat it.

**Two independent reviewers, two disjoint finding sets — both were right.**
Post-merge review of PR #4 by two separate sessions caught non-overlapping
gaps: one flagged a false sense of `ChainOutcome(frozen=True)` immutability
and an untested veto-with-enrichment ordering; the other flagged that
`FilterResult.confidence` and `ExecutionState.timestamp` had no invariant
enforcement at all despite being the future `decisions.parquet` audit-trail
contract (`specs.md` §11.3.4). `3863df5` fixed the concrete, checkable ones
(confidence range, UTC timestamp, veto-enrichment survival) via
`__post_init__` fail-fast validation + new Gherkin coverage; the
frozen-but-aliased `ChainOutcome.state` issue was left as-is per the first
reviewer's own recommendation (no live caller yet to trigger the risk —
fixing it speculatively would guess at Wave 2's actual needs). Lesson: a
single review pass has a detection ceiling even when thorough; a second,
independently-reasoning pass over the same diff finds a different slice of
real issues, not just noise or duplicate findings.

**Boundary-condition mutants need boundary-value tests, not just
out-of-range ones.** Testing `confidence` rejection with `1.5`/`-0.1` alone
left 3 mutants alive that shifted the `<=`/`<` operators at the `0.0`/`1.0`
edges (e.g. `0.0 <= x <= 1.0` → `0.0 <= x < 1.0`) — those mutants still
correctly rejected `1.5`/`-0.1`, they only misbehaved exactly at the
boundary. Killed by adding a `Scenario Outline` asserting `0.0` and `1.0`
are *accepted*. A closed-interval spec (`[0, 1]`) needs both an
outside-the-range negative test and an on-the-boundary positive test to
pin down the operator, not just the former.

**Message-text mutants are a known, accepted debt class (TD-34), not a bug
to chase per-instance.** The UTC-timestamp error message had 3 surviving
mutants purely from string-wrapping/casing, because the `Then` step does a
substring check (`"UTC" in str(error)`) that the mutated text still
satisfies. Rather than rewrite that one assertion to exact-match (a
one-off fix out of step with every other substring-based `Then` in the
suite), logged as TD-36 alongside the pre-existing TD-34 — consistent
handling of the same failure class beats a piecemeal fix on whichever file
happens to hit it next.

**Note (unrelated, flagged not fixed):** `algo-suite/uv.lock` was already
missing an `algo-analyze` entry on disk before this story started (that
workspace member currently has no `pyproject.toml` in this checkout,
apparently mid-scaffold in another concurrent session). `uv sync` during
this story's setup surfaced that drift as an unstaged `uv.lock` diff; left
untouched and uncommitted — it belongs to whoever owns the `algo-analyze`
lane, not to Spec 04b.

## Retrospective (post-merge, `3b900af`)

**The orchestrator's job here was arbitration, not typing.** Every line of
`chain/model.py` and its tests was written by sub-agents (coder, hardener);
the orchestrating session's actual contribution was sequencing (coder before
hardener, never parallel, because the boundary was one file), verifying each
agent's claims against real command output instead of trusting the report
text, reconciling two conflicting spec sources (`specs.md`'s tuple vs.
`SPEC.md`'s `ChainOutcome`) into one decision, and later triaging two
reviewers' overlapping-but-not-identical findings into a single fix list.
None of that was "write code" — it was deciding what counted as done and
catching the two places (uv.lock drift, a stray `principal_mba_tlc_pr_review_prompt.md`
file from an unrelated session) where "keep going" would have quietly swept
someone else's in-flight work into this branch.

**Verification cost less than it looked like it would.** Independently
re-running `pytest`/`ruff`/`mypy`/`mutmut` after each sub-agent's report added
maybe two tool calls per stage — cheap insurance against a report that
oversold itself. It never actually caught a fabricated claim in this story
(both agents' summaries held up), but that's the point of trust-but-verify:
the cost is small and constant, the payoff is avoiding a merge on the one
time a report is wrong.

**Gauntlet stage names map cleanly onto this session's own sub-agent
dispatch**, independent of `swarmforge`'s tmux/worktree pipeline (which was
busy on Spec 04a throughout this story). Coder → Hardener → (fresh-eyes
Verifier, here supplied by two independently-reasoning reviewers rather than
a single scripted Verifier) is the same shape whether the mechanism is a
tmux pane per role or an `Agent` tool call per stage. The value isn't the
infrastructure, it's fresh context per stage and an author-≠-verifier split.

**Process friction worth remembering for next time:** this Forgejo instance
returns 405 on threaded PR-comment replies and thread-resolve — both
`reply_comment` and `resolve_thread` are dead ends here, so review responses
have to land as one consolidated top-level comment instead. Not a code
issue, just a platform capability gap worth not re-discovering mid-review
next time.
