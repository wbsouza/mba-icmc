# Lessons learned — story 13 (candlestick patterns and quote activity)

**What the spec did not anticipate.** The predecessor's experiments (Codex) had to be inventoried,
frozen and reproduced before anything new could be trusted; the handoff took a session of its
own, with snapshots, path maps and byte-identity checks of the intermediate figures. That
discipline paid back when the confidentiality rename moved every job directory: the evidence
survived because it was hashed.

**What took longer.** The H4 matrix on the September pilot: eight cells, identical paired outcomes
in pairs, because active patterns and event-augmented probabilities never crossed the fixed F7
boundary. It looked like a wiring bug and was not; proving that (parity scenarios, contract checks
on `--model`) took longer than the experiment. Fifty-one tuning variants across H4/H1/M15 followed,
none profitable on the one untouched month.

**What took less.** TA-Lib detection and the quote-activity veto themselves: small pure functions
with Gherkin outlines, wired identically into offline training and LEAN.

**What we learned about the patterns.** Six patterns at H1, read as continuation signals, lean the
wrong way (bearish engulfing: next bar up 61 % of the time). Read in context (after a fall, near
a swing low, with the trend against them) the bullish side shows 54–59 % at four hours on small
samples. The catalogue and its context rules are the planned story 22; the detector alone is not
a signal.

**What to do differently.** Register the matrix before the first cell and keep the counts (trial
count, cells viewed) in the README from the start; the tuning sweeps grew past fifty variants
before the count was written down. Measure prediction quality per cell, not only equity: a
"no difference" between arms is not "no effect" when the terminal rule never fires.
