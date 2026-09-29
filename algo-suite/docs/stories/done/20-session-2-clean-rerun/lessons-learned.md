# Lessons learned — story 20 (session 2: clean re-run, both sides in one simulation)

**What the spec did not anticipate.** Two script defects cost two calibration passes: the trainer
resolves `--strategies-dir` without the packaged fallback the run command has (so `news-only` was
"unknown" until the packaged configs were copied into the job), and a wrong attribute name in the
calibration script. Both were found by the job failing fast, as designed; both are recorded in the
scripts as run.

**What went as planned.** Reproduction was exact: twelve retrained models identical outside the
provenance block, fifteen cells byte-identical to session 1, the primary test at the same
p = 0.149. Determinism from training through LEAN to the bootstrap is now a demonstrated property,
not an assumption, and it makes the adaptive-retraining study (story 19) auditable.

**What we learned.** Letting the learned chains trade both sides multiplied trades and losses
(H1 q10 pair −44 % / −33 % on about 515 trades each); the regime gate halved the trades and lost
more. The fixed-threshold cells of session 1 were long-only in effect, so "both sides" was not a
refinement but a different experiment, and it was worse. Five of six sub-hour cells stopped at the
statement step on TD-71; a strategy that re-enters within minutes of every exit trips it every
time. The monthly prediction-quality table (log-loss at the coin-flip value in every month) showed
that the frozen model never had skill to lose, which reframed the retraining question.

**What took less.** One evening: twelve fits in about two minutes in parallel, 26 year-long cells
in under an hour on six LEAN slots, the viewer database from the finished cells.

**What to do differently.** Read the trade counts before the returns: 500 trades at 3 % risk on
a coin-flip model is a drawdown machine whatever the sign. Register the prediction-quality
endpoint with the trading endpoint. Keep the reproduction cells out of the viewer (they duplicate
the reported ones) and keep the archive of the previous session intact; the comparison script is
only as good as the artifacts it can read.
