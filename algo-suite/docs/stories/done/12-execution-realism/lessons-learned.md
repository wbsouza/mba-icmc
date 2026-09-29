# Lessons learned — story 12 (execution realism)

**What the spec did not anticipate.** Making execution realistic changed the results more than any
model change: with a trade plan (stop, sized lot, targets, trail) and a spread, the September and
October 2015 confirmation reruns lost more than half the deposit, and the one-year protocol lost
88 % per arm. The spec framed execution realism as plumbing; it was the experiment.

**What took longer.** Nine LEAN integration scenarios (stop fill, partial target, trail move,
spread cost) against a sine fixture: the planned-stop scenario needed a 1-pip stop and a 2-pip
tolerance because the fixture's range was smaller than a 2-pip stop. The statement and report
tooling (`statement.md`, `report.html`, `equity.csv`, consolidated curves) grew into a viewer of
its own (later stories); the "pipette precision" bug in prices surfaced only when a human read
the statement.

**What took less.** Parallel worktrees for the seven wave-1 lanes; merging by union was routine
once each lane owned its files.

**What we learned about the engine.** A stop-market and a limit target can both fill inside one
minute bar, leaving an unplanned reverse position (TD-71). It appeared once in a control run and
then blocked five of six sub-hour cells in session 2. Every strategy that re-enters right after an
exit will trip it; it must be fixed before any sub-hour result.

**What to do differently.** Define the exit horizon with the signal, not from a template: the
trading-year checks showed a four-hour tilt in the news signal that a multi-day plan turns into
drift. Keep the QA procedure (`evidence/qa-procedure.md`, `qa_check.py`) as the operator's test of
every job, and run the mutation pass before, not after, the experiment that depends on the code.
