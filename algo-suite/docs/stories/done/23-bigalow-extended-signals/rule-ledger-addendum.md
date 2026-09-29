# Story 23 — bigalow extended-signals rule ledger addendum (T1)

Status: frozen for Story 23 on September 28, 2026 (coder, task T1, requirement
BEXT-01, BEXT-02, BEXT-07). Addendum to the Story 22 rule ledger
([candlestick-rule-ledger.md](../22-candlestick-context-extension/candlestick-rule-ledger.md),
read-only reference, not edited here). Four items admitted, all citations from
`~/.claude/skills/bigalow-candlestick-patterns/references/book-only-material.md`
(full-book read by `book-mining`, 2026-09-28). No win-rate/probability figure
from the book is repeated as an established fact; only computable geometry.

## 1. Conventions this addendum adds

Reuses every Story 22 per-bar quantity (`body`, `range`, `upper`, `lower`,
bullish/bearish, `mid(prior)`) unchanged. Two new conventions, both user
decisions recorded in `spec.md`'s Assumptions table (2026-09-28):

| Convention | Value | Rationale |
| --- | --- | --- |
| "at or near the previous day's close" (Meeting Line / Counterattack Line) | `abs(close[t] - close[t-1]) <= 0.10 * range[t]` (same 0.10 fraction as `doji_body_ratio`, a new named constant `COUNTERATTACK_TOLERANCE` so the two rules can diverge later without coupling) | No numeric bound is given in the book; reuses the catalog's existing near-equal convention style, not a new invented number. |
| Fibonacci "a sustained trough and peak" | The causal swing high/low over a configurable `fibonacci_lookback_bars` (default 60, matching `price_features.PriceFeatureConfig.swing_lookback_bars`'s default — the same rolling-window convention the perception layer already uses for F6's stop distance, reimplemented locally since `candle_context.py` cannot import chain code) | The book gives no swing-selection rule; reusing the same window size and rolling max(high)/min(low) mechanism avoids a second, uncoordinated swing definition. |
| Fibonacci zone width | Same 0.10-of-`range[t]` tolerance as the Counterattack Line convention above (`FIB_TOLERANCE_RATIO`) | One tolerance convention across this batch instead of two magic numbers. |
| Fibonacci trend-leg direction (implementation-only, not in spec.md's Assumptions table) | Whichever of the swing high/low occurred more recently (ties resolved to the high) fixes the leg: high more recent -> rising leg, retracement descends from the high; low more recent -> falling leg, retracement ascends from the low | The book anchors retracement to "a sustained trough and peak" but does not state which extreme is more recent; the swing itself is the only causal signal available, so the more-recent extreme is used as the trend anchor per the Assumptions table's "reuse the swing as the trend anchor" framing. |

## 2. Meeting Line / Counterattack Line (two-bar, both polarities)

Book (PDF p.318, lines 12008-12018): "The Bearish Counterattack Line stops
at, or near, the previous day's close," ranked shallower than Dark Cloud
Cover ("closes well into the previous day's bar") and Bearish Engulfing
("engulfs the entire body"); bullish mirror named at line 12020. Worked
decision-tree passage (PDF p.368-369, lines 14022-14028): after a gap-up
open in an overbought condition, "a close back at the previous day's close
will form a Meeting Line Signal," distinguished there from Shooting Star,
Dark Cloud, and Bearish Engulfing by where the close lands. Glossary: PDF
p.399 ("Meeting lines"), p.404 ("Bearish Counterattack (Meeting) Line
pattern").

| ID | Polarity | Lookback | Formula |
| --- | --- | --- | --- |
| `bearish_counterattack_line` | -1 | 2 | prior bullish, `open[t] > close[t-1]` (gaps up past the prior close, continuing the bullish trend), `close[t] > mid(prior)` (stays above the dark-cloud-cover threshold), `abs(close[t] - close[t-1]) <= COUNTERATTACK_TOLERANCE * range[t]` |
| `bullish_counterattack_line` | +1 | 2 | prior bearish, `open[t] < close[t-1]` (gaps down past the prior close, continuing the bearish trend), `close[t] < mid(prior)` (stays below the piercing-line threshold), `abs(close[t] - close[t-1]) <= COUNTERATTACK_TOLERANCE * range[t]` |

**Mutual exclusivity with `piercing_line`/`dark_cloud_cover` (BEXT-03):**
`bearish_counterattack_line` requires a bullish prior (like `dark_cloud_cover`)
but requires `close[t] > mid(prior)`, the exact complement of
`dark_cloud_cover`'s `close[t] < mid(prior)` — the two conditions cannot both
hold for the same bar. `bullish_counterattack_line` requires a bearish prior
(like `piercing_line`) but requires `close[t] < mid(prior)`, the complement
of `piercing_line`'s `close[t] > mid(prior)`. Against the opposite-prior
kicker rules: `bearish_counterattack_line`'s `open[t] > close[t-1] > open[t-1]`
(prior bullish, so `close[t-1] > open[t-1]`) already contradicts
`bearish_kicker`'s `open[t] <= open[t-1]`; the mirror holds for
`bullish_counterattack_line` against `bullish_kicker`. No shared-bar overlap
with `piercing_line`/`dark_cloud_cover` is possible by construction (the two
rules never share a prior polarity), so the guard that actually matters is
the `mid(prior)` complement above.

Examples (open, high, low, close; using the Story 22 bullish prior
`(900, 1010, 890, 1000)` and bearish prior `(1000, 1010, 890, 900)`, both
body 900..1000, `mid = 950`):

| ID | Positive | Negative | Boundary |
| --- | --- | --- | --- |
| `bearish_counterattack_line` | bullish prior, then `(1020, 1025, 995, 1002)`: gaps to 1020 > 1000, closes 1002, `\|1002-1000\|=2 <= 0.10*30=3` | bullish prior, then `(995, 1010, 985, 999)`: `open 995` does not gap past `close[t-1] 1000` | bullish prior, then `(1020, 1020, 980, 1004)`: `\|1004-1000\|=4 == 0.10*40`, hit; `(1020, 1020, 980, 1005)` with `\|1005-1000\|=5 > 4` misses |
| `bullish_counterattack_line` | bearish prior, then `(880, 905, 875, 902)`: gaps to 880 < 900, closes 902, `\|902-900\|=2 <= 0.10*30=3` | bearish prior, then `(905, 920, 880, 898)`: `open 905` does not gap past `close[t-1] 900` | bearish prior, then `(880, 900, 860, 896)`: `\|896-900\|=4 == 0.10*40`, hit; `(880, 900, 860, 895)` with `\|895-900\|=5 > 4` misses |

## 3. Methods Rising Pattern (multi-bar bullish continuation)

Book, PDF p.260-261, lines 9679-9714, the most concretely specified new
formation:

> 1. ...once a bullish candle is formed, three pullback days are seen before
>    the next bullish candle. 2. ...an extension... having 3, 4, 5, or 6
>    indecisive pullback days... 3. The pullback days are usually
>    indecisive... Doji's or Spinning Tops... 4. The final pullback day does
>    not close below the open of the last bullish candle. 5. The final day
>    opens higher than the close of the previous day and finally closes
>    above the close of the last bullish candle.

Criterion 3's shape wording ("usually indecisive") is descriptive, not a
hard numeric test, and is not part of the computable geometry (consistent
with `book-only-material.md`'s "fully computable" framing, which extracts
only criteria 1, 2, 4 and 5). Criteria 4 and 5 both describe the *same*
final bar (the last of the `n` pullback bars doubles as "the final day"),
which is why the window is `n + 1` bars, not `n + 2`: this resolves
`spec.md`'s BEXT-04 "up to 7 bars: 1 signal + up to 6 pullback bars" exactly
(`1 + 6 = 7`).

| ID | Polarity | Lookback | Formula |
| --- | --- | --- | --- |
| `methods_rising` | +1 | 4 (the `n=3` minimum window; `n` up to 6 is tried whenever enough history exists) | signal bar `B` bullish; for some `n` in `{3,4,5,6}` with `B` at `bars[-(n+1)]`: every one of the `n` bars in `bars[-n:]` closes `>= open(B)`; the last of those `n` bars opens above the second-to-last one's close and closes above `close(B)` |

No bearish mirror exists: `book-mining` grepped the full text for "falling
method"/"bearish method"/"methods falling" and found zero hits.

Examples (open, high, low, close), `n=3` unless noted:

- **Positive** (`n=3`): `B=(1000, 1025, 995, 1020)`,
  `P1=(1015, 1018, 1002, 1005)`, `P2=(1008, 1010, 1000, 1003)`,
  `P3=(1010, 1030, 1005, 1025)`. Every pullback closes `>= open(B)=1000`
  (1005, 1003, 1025); `P3.open=1010 > P2.close=1003`; `P3.close=1025 >
  close(B)=1020`. Fires.
- **Negative** (`n=3`, criterion 5 violated): same `B`, `P1`, `P2`, then
  `P3=(1010, 1022, 1005, 1018)` — `close=1018` is not `> close(B)=1020`.
  Does not fire.
- **Boundary** (`n=3`, criterion 4's `>=` at equality): same `B`, `P1`, then
  `P2=(1005, 1008, 998, 1000)` — `close=1000 == open(B)=1000`, the inclusive
  edge — then `P3=(1010, 1030, 1005, 1025)`. Fires (equality is admitted,
  not rejected).
- **Rejected `n=2`**: `B` then only two pullback bars, the second satisfying
  criterion 5 on its own — no `n in {3..6}` window fits a 3-bar total
  history (`lookback=4` is not yet reached), so the rule is WARMUP, never a
  false READY-and-fired.
- **Rejected `n=7`**: `B` then seven pullback bars all closing
  `>= open(B)`, the seventh satisfying criterion 5 — `n=7` is outside
  `{3,4,5,6}` so it is never tried; the fixture's first pullback bar is
  built non-bullish so no shorter in-range `n` (e.g. `n=6` reading the
  first pullback as a new signal bar) spuriously matches either.
- **Boundary `n=6`** (the maximum window): `B` then six pullback bars, each
  closing `>= open(B)`, the sixth opening above the fifth's close and
  closing above `close(B)`. Fires with the full 7-bar window.

## 4. Fibonacci retracement confluence (context field, not a catalog rule)

Book, PDF p.220-221, lines 8141-8167: a candlestick reversal signal forming
at/near the 38.2%/50%/61.8% retracement of "a sustained trough and peak" is
additional confirmation, structurally the same role the T-line and
stochastic zone already play in `candle_context.py`.

- **Field**: `FibonacciEvidence` on `ContextEvidence.fibonacci` (only present
  when `ContextConfig.fibonacci_enabled` is `True`; `None` otherwise —
  BEXT-10).
- **Swing**: `swing_high = max(high)` / `swing_low = min(low)` over the last
  `fibonacci_lookback_bars` closed bars (causal, ends at the evaluated bar).
- **Levels**: `high - ratio * (high - low)` for a rising leg (high more
  recent), `low + ratio * (high - low)` for a falling leg (low more
  recent), `ratio` in `{0.382, 0.5, 0.618}` (`FIBONACCI_LEVELS`).
- **"At" a level**: `abs(close[t] - level_price) <= FIB_TOLERANCE_RATIO *
  range[t]` (same 0.10 fraction as the Counterattack Line).
- **Degenerate** (BEXT-08): `swing_high == swing_low` reports `status =
  "UNDEFINED"` and `level = None`; `swing_high`/`swing_low` stay `READY`
  (each is individually a finite reading, only their difference is
  degenerate) — never a division by zero, never a fabricated level.
- **Warmup** (BEXT-09): fewer than `fibonacci_lookback_bars` closed bars ->
  `status = "WARMUP"`, `swing_high`/`swing_low` both `WARMUP`, `level =
  None`.

Examples (rising leg, swing low older than swing high; a 5-bar lookback for
brevity): swing low `900` at the oldest bar, swing high `1000` at the most
recent bar before the evaluated one, `range = 100`.

| Level | Ratio | Price | Within-tolerance close (`range[t] = 20`, tolerance `2`) | Outside close |
| --- | --- | --- | --- | --- |
| 38.2% | 0.382 | `1000 - 0.382*100 = 961.8` | `962` (`\|962-961.8\|=0.2 <= 2`) | `970` |
| 50% | 0.5 | `950` | `949` | `970` |
| 61.8% | 0.618 | `938.2` | `939` | `970` |

Falling-leg mirror (swing high older than swing low, same `900`/`1000`
pair): `level = low + ratio*(high-low)`, e.g. 38.2% -> `900 + 38.2 =
938.2`, 61.8% -> `900 + 61.8 = 961.8` (levels mirror the rising leg's).

Zero-range degenerate example: 5 flat bars `(1000, 1000, 1000, 1000)` ->
`swing_high = swing_low = 1000`, `status = "UNDEFINED"`, `level = None`.
