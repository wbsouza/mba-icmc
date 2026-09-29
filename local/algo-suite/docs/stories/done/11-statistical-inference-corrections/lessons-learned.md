# Lessons learned — Story 11

What happened that the spec did not anticipate, and what to do differently.

## A confident review comment was wrong, and the fix made it worse

The first review asserted from memory that LEAN stamps equity candlesticks at
the bucket start and asked for the candle `open`. The follow-up applied that.
Reading LEAN's source (`SampleEquity(time)` is documented as the candlestick
*end* time; the bar accumulates every equity update since the previous sample;
a scheduled "Daily Sampling" fires at midnight) and checking LEAN's own daily
`Return` series against both candidates showed the `close` was right all
along. Lesson: an engine-contract claim needs the engine's source or an
independent engine output, never recollection. The `Return` cross-check now
makes the wrong choice a hard error instead of a silent one.

## Preregistration produced a negative result, and that is the result

Two block-length rules were registered before running at the window lengths
the thesis can actually observe. Both failed the size gate: cube-root blocks
are too short for AR(1) dependence, and the maximal length under the ten-block
guard is liberal even without dependence because ten blocks are too few. The
temptation to try a third rule was real and was declined; a rule chosen after
seeing results is not registered. The consequence for the manuscript is a
stated limitation, not a workaround.

## "No defaults" applies to selection history too

The ledger form initially defaulted provenance, frequency and interim looks
when absent. Those are exactly the fields whose absence should stop an
inference. Every declared field is now required in both forms.

## Contracts need producers

`inference-inputs.json` was specified as a hand-written file inside a
read-only run directory. A contract nobody emits is a contract someone will
type. `algo-backtest run` now writes it with the resolved brokerage model and
hashes it into `run.json`.

## Test channels are part of the contract

Scenarios that accepted either an error or an unavailable report could not
catch a regression that turned invalid data into a quiet "unavailable". Every
malformed-input row now names its channel.

## A second reviewer found what the first missed

A third review reproduced four defects the first two rounds had not: producer
provenance recorded but never verified, malformed `Return` containers escaping
as programming exceptions, a malformed ledger falling back to declared values,
and a suite that stayed green when the computed dispersion was replaced by a
constant. Each was a missing invariant, not a wrong formula. Lesson: a test
that checks shape (a label, a count, a bound) is not a test of the statistic;
pin the independently computed value. And the mutation operators in use do
not cover call replacement, so "all mutants killed" must be quoted with its
operator scope.

## Cost of the gauntlet

The full loop (registered method, coder, cleaner, hardener with 161 mutants,
QA, two simulation studies) took most of a day for four small modules. It
found a boundary rounding bug, a regression introduced by review, and a
scientific limitation of the planned design. That is what it is for.
