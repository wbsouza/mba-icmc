# Lessons learned — story 09 (six-month training and September pilot)

**What the spec did not anticipate.** The spec assumed that a trained model plus a replay would
produce trades to evaluate. The first September replays produced zero trades, and the cause was not
data or code failure but a sign disagreement between the fitted combiner and the terminal rule: the
regime gate required BUY in a bull regime while the model, trained on a 15-minute label, had learned
mean reversion and put p̂ below 0.5 on every bull bar. Nothing in the pipeline could report that;
it took a hand-made diagnosis over the decision audit trail.

**What took longer.** Turning every filter parameter into configuration (three rounds in one day:
sections per filter, then defaults, then YAML-resolved strategies with provenance). It was worth it:
every later experiment lived in YAML, and `explain-strategy` made the "which parameters produced
this number" question answerable. Also the discovery that a file written inside the LEAN container
came out root-owned and unreadable; found only because the QA procedure read the run directory.

**What took less.** Calibrating thresholds from validation quantiles once the training rows could be
rebuilt offline; the machinery for that became the standard for every later job.

**What was wrong in the spec's framing.** Treating September as an untouched test month after the
gate decision was taken on September's outcome. The record says so, and the later stories moved
the untouched window forward each time a decision was taken on viewed data. The rule that
survived: register before viewing, in a file the run reads, and let file timestamps prove the order.

**What to do differently.** Ship a "why no trades" report with the run (funnel by filter, p̂
distribution against the thresholds) before the first replay, not after. Fix the $10,000 account
and the execution costs first; a pilot that trades at $100,000 with no spread teaches nothing about
economics. Never train once and evaluate for a year without measuring prediction quality per month
(story 20 later showed the model at coin-flip in every month).
