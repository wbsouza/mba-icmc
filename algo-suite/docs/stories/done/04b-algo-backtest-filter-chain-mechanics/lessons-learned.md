# Lessons learned — Spec 04b: algo-backtest filter-chain mechanics

**Sourced from the coder → hardener pipeline commits on
`feat/04b-filter-chain-mechanics`** (`2bdc3bd`, `3053266`).

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

**Note (unrelated, flagged not fixed):** `algo-suite/uv.lock` was already
missing an `algo-analyze` entry on disk before this story started (that
workspace member currently has no `pyproject.toml` in this checkout,
apparently mid-scaffold in another concurrent session). `uv sync` during
this story's setup surfaced that drift as an unstaged `uv.lock` diff; left
untouched and uncommitted — it belongs to whoever owns the `algo-analyze`
lane, not to Spec 04b.
