# Lessons learned — Spec 05f: normalized trade returns

**Sourced from:** two independent PR #11 reviews of Spec 05d figures, one requesting
changes because the producer contract was still missing.

**A consumer-side fail-fast guard is not the same as a producer contract.**
Spec 05d correctly refused to guess a fractional return from LEAN's raw
`profitLoss`, but that only makes the failure safe — it does not make real
completed-run figures possible. The two are separate deliverables, and a
reviewer correctly distinguished "safe to merge" from "usable on real data."

**Land the boundary fix in the same PR when the story otherwise can't be
verified end to end.** This was originally scoped as a separate backlog story
(#12) so it could be reviewed independently. In practice, no BDD scenario
could prove `algo_analyze.figures` works against a *real* completed run
without it, so the honest move was to land both together rather than merge a
figures lane that can only be proven against hand-written fixtures.

**Compute the return from data you already trust, not from a guessed field
name.** The previous implementation scanned four candidate field names
(`return`, `returns`, `trade_return`, `realized_return`) and used the first
match — a silent-precedence bug flagged in review. Replacing that with one
canonical `return` field, computed once at the producer boundary from
`entryPrice` / `quantity` / `profitLoss`, removes the ambiguity entirely
instead of trying to detect conflicts among guesses.

**A missing field should stay missing, not become a fabricated value.** When
a raw trade lacks pricing data (or the cost basis is zero), `_normalize_trade`
leaves it exactly as LEAN reported it. The existing consumer-side fail-fast
check in `algo_analyze.figures` then does its job — the fix doesn't have to
also predict every downstream failure mode.

**Physical bounds on a computed metric are cheap insurance.** A fractional
return below -100% is not representable as a real loss without margin-call
modeling this codebase doesn't have; rejecting it in `_trade_return` turns a
future silently-wrong equity curve into an explicit error today.
