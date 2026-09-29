# Lessons learned — Story 23 (Bigalow extended candlestick signals)

Scoping to the four fully-computable items (Counterattack Line pair, Methods
Rising, Fibonacci confluence) and explicitly deferring Tweezer Top/Bottom and
the two unresolved book conventions was the right call: it kept every
delivered rule backed by an unambiguous, citable geometry rather than a
best-guess interpretation of ambiguous book prose. Naming the deferral in
`spec.md`'s Out of Scope table up front (not discovered mid-task) meant T1-T4
closed clean with no scope creep.

Admitting the three new rules into `CATALOG`/`ADMITTED_RULES` while keeping
them out of `DEFAULT_ENABLED_RULES` (the frozen Story 22 19-rule set) is the
pattern that let every existing `candle_catalog.feature`/`candle_context.feature`
scenario pass unmodified. That admitted-vs-default split is worth carrying
into any future rule addition to this catalog: it decouples "the engine knows
about this rule" from "this rule is live by default," so extending the
catalog never silently changes existing backtest behavior.

The cleaner/hardener pass found real complexity the task log didn't flag:
`fibonacci_evidence` (cc=14) and `FibonacciEvidence.__post_init__` (cc=9) were
both over the repo's complexity threshold despite passing every functional
test. Splitting them (`_swing`/`_nearest_level`, `_validate_swings`/
`_validate_level`) and the hardener's 5 mutation survivors (all in the same
two areas: counterattack midpoint boundary, methods-rising pullback
enforcement, Fibonacci tie-breaks) both point the same direction: geometry
code with several boundary conditions needs deliberate mutation testing, not
just coverage, to catch off-by-one and tie-break bugs that a green test suite
alone won't surface.

What would be done differently: budget the cleaner/hardener passes as part of
the task estimate from the start for any geometry-heavy rule (this story's
complexity findings were all in the two most arithmetic-dense functions),
rather than treating them as a late-stage check that might turn up nothing.
