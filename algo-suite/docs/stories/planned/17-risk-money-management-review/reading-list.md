# Review reading list — risk, sizing and evaluation

Inventory checked September 28, 2026 in:
`/home/wellington/workspace/mba-agents/mba-main/related-work/books/books-forex-trading`.

These books are present locally. Authors and relevant contents were inspected
for the shortlist below; this is not a claim to have read or validated every
chapter. Printed page numbers below come from those contents. Verify source
edition, chapter text, chart and PDF page before implementing a rule.
Keep all references read-only; store original summaries, not extracted books.

## Core shortlist

| Source | Sections identified | Role in our review |
| --- | --- | --- |
| Noble DraKoln — *Trade Like a Pro* (2009) | Preface; Ch. 3, p. 47; Ch. 6, p. 103; Ch. 7, p. 113; Ch. 14, p. 217 | Challenge assumptions about protection and loss response; distinguish options hedging from stop-based FX management |
| Van K. Tharp — *Trade Your Way to Financial Freedom* | Local contents: Ch. 6 expectancy/R-multiples; Ch. 9 protection; Ch. 10 profit exits; Ch. 12 sizing | Separate entry quality, exit effects and sizing; evaluate F6 economics and normalized risk |
| Alexander Elder — *The New Trading for a Living* (2014) | Part 9, pp. 197–210; sections 53–54, pp. 215/219 | Compare per-trade and account-level limits, drawdown recovery, targets and stops |
| Adam Grimes — *The Art and Science of Technical Analysis* (2012) | Ch. 8, p. 231; Ch. 9, p. 263 | Connect structural stops, targets, active management, portfolio considerations and practical risks |
| Keith Fitschen — *Building Reliable Trading Systems* (2013) | Ch. 5 exits, p. 65; Ch. 6 filters, p. 89; Ch. 7 money-management feedback, p. 107; Ch. 11 onward, p. 175 | Examine interaction among filters, exits and account sizing; assess robustness rather than only fit |
| Ernest P. Chan — *Algorithmic Trading* (2013) | Ch. 1 backtesting/automated execution; Ch. 8 risk management, p. 169 | Check algorithmic implementation assumptions and risk methodology; review detailed rules before adopting them |
| David Aronson — *Evidence-Based Technical Analysis* (filename 2007; verify edition) | Ch. 1 objective rules, p. 15; Ch. 5 inference, p. 217; Ch. 6 data-mining bias, p. 255 | Challenge the experiment-selection process and guard against declaring a lucky policy the winner |

The local Tharp filenames claim a second edition from 2006, but the extracted
front matter does not establish that edition. Both local versions need a
bibliographic check before citation; use the verified local chapter names, not
assumed page numbers from another edition. Duplicate editions/annotations are
not independent sources.

## Exact local filenames

All paths below are relative to the inventory directory above:

- `Trade Like a Pro - 15 High-Profit Trading Strategies 2009.pdf`
- `Trade Your Way to Financial Freedom 2nd edition 2006.pdf`
  (also present: `Trade Your Way to Financial Freedom 2 edition 2006.pdf`).
- `The New Trading for a Living - Psychology, Discipline, Trading Tools and Systems, Risk Control, Trade Management 2014.pdf`
- `The Art and Science of Technical Analysis - Market Structure, Price Action, and Trading Strategies 2012.pdf`
- `Building Reliable Trading Systems - Tradable Strategies That Perform As They Backtest and Meet Your Risk-Reward Goals 2013.pdf`
- `Algorithmic Trading - Winning Strategies and Their Rationale 2013.pdf`
- `Evidence-Based Technical Analysis - Applying the Scientific Method and Statistical Inference to Trading Signals 2007.pdf`

## Further candidates, existence confirmed only

Do not treat these as reviewed recommendations or expand scope automatically:

- `Come Into My Trading Room - A Complete Guide to Trading 2002.pdf`
- `Trading for a Living - Psychology, Trading Tactics, Money Management 1993.pdf`
- `Way of the Turtle - The Secret Methods that Turned Ordinary People into Legendary Traders 2007.pdf`
- `The Sensible Guide to Forex - Safer, Smarter Ways to Survive and Prosper from the Start 2012.pdf`
- `When Genius Failed - The Rise and Fall of Long-Term Capital Management 2001.pdf`

## How to use the sources without replacing one bias with another

1. Start with a concrete contract question: for example, how to count risk on
   an open winning position or reserve risk for an unfilled order.
2. Compare applicable passages from two or more authors. Record market,
   timeframe, data and execution assumptions, plus counterexamples.
3. Separate arithmetic/safety invariants from empirical preferences. A formula
   can be verified; a favored exit or risk percentage needs a registered test.
4. Record disagreements rather than blending incompatible rules. Agree on a
   small hypothesis set before outcomes, not an unrestricted library search.
5. Check current broker/instrument constraints separately. Older books do not
   establish today's margin, financing, minimum-size or execution contracts.
6. Review the shortlist with an independent agent and preserve negative
   findings. Source diversity reduces single-author dependence, not all bias.

Elder's named percentage rules and sizing prescriptions elsewhere are subjects
for review, not automatic defaults or live-account recommendations. Likewise,
Aronson is a methodology reference, not permission to reinstate the legacy
pooled-trade IID permutation test rejected by Story 11.
