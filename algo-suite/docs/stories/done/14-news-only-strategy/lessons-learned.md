# Lessons learned — story 14 (news-only and rule-only strategies)

**What the spec did not anticipate.** Two things. First, the learned news-only combiner is almost
constant (p̂ within 0.525–0.529 on validation), so fixed 0.55/0.45 thresholds never fire and the
cells had to run on quantile thresholds registered from the January validation distribution.
Second, the rule cells were one-sided by accident: the event intensity never returned to the
January-2016 level of its low cut during the trading year (minimum +0.02 against a cut of −0.005),
so the registered sign was long-only and the reversed sign short-only in effect. Absolute cuts
taken from one month do not survive a level shift; thresholds must be relative or refreshed.

**What took longer.** The controls. The first short-when-flat control was mis-specified (sign −1
turned SELL-on-every-bar into BUY) and became a long-whenever-flat control by accident; it exposed
TD-71 and had to be kept and reported as what it was. The corrected always-short control then
matched the reversed-sign rule month by month on the untouched months, which is the finding.

**What took less.** The chain without F7 (`terminal_filter`) and the intensity-direction rule in F4:
small, and they reused every parameter mechanism of story 09.

**What we learned.** A positive cell in a registered pair of opposite signs is what the null
predicts; the always-short control turned "+12 %" into "the euro fell 5 % with leverage". The
paired test against the control (p = 0.92 at both clocks) is the sentence that closes the story.
The offline check later found a four-hour tilt on the signal bars (about 4 pips) that the
multi-day exit template never captured: the signal was not empty, it was traded on the wrong
horizon. That is story 21.

**What to do differently.** Write the registration paragraph before the launch command, in the
file the run reads, and let the file timestamps prove it (the timestamp audit of the trading-year
job is in the evidence). Build the drift control into the design from the start: any directional
rule gets its always-on-that-side twin as a registered cell.
