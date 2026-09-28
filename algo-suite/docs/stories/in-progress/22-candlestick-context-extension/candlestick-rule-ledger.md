# Story 22 — candlestick rule ledger (T1)

Status: frozen for Phase 1 on September 28, 2026 (Claude coder, lane C, task T1,
requirement CND-01). Every admitted rule below has a stable ID, a source citation,
an exact formula with named parameters and equality boundaries, a context
requirement, a confirmation rule, its TA-Lib relation, its Forex adaptation and
three integer OHLC examples (positive, negative, equality boundary). Rules that the
sources do not define computably are DEFERRED with a reason. No speaker or author
performance claim is a threshold, prior or acceptance target here.

Parent: [Story 22 brief](candlestick-extension.md); timestamped webinar notes:
[bigalow-video-notes.md](bigalow-video-notes.md). Canonical plan:
[spec](../../../../../.specs/features/candlestick-context/spec.md),
[design](../../../../../.specs/features/candlestick-context/design.md),
[tasks](../../../../../.specs/features/candlestick-context/tasks.md).

## 1. Sources read and verified

All four sources were readable on September 28, 2026 (`sha256sum` on each path).

| Source | Path | SHA-256 | Read with |
| --- | --- | --- | --- |
| Book: *High Profit Candlestick Patterns* (S. W. Bigalow), 411 PDF pages, scanned with an imperfect OCR layer | `/media/nas/wellington/mba/related-work/books/books-forex-trading/high-profit-candlestick-patterns.pdf` | `d962029526518201444cc0d19f52384df8bb095b98b4a6053a7159bfdb289751` | `pdftotext -layout` per page |
| Presentation: *Candlestick Patterns*, CMT presentation, January 2023, 60 slides | `/media/nas/wellington/mba/related-work/books/books-forex-trading/0104-Steve-Bigalow.pdf`; byte-identical local copy `/home/wellington/Downloads/0104-Steve-Bigalow.pdf` | `b1e6cdfc207854879d9563d036ab70e383a36026cfaf4df59bae57bbfbfe818b` (both copies) | `pdftotext -layout` per slide |
| Webinar transcript (video `1fB3EF7XeXU`), 1,450 lines | `/media/nas/wellington/mba/related-work/books/books-forex-trading/high-profit-trades-found-with-candlestic-breakout-patterns.txt` | `18e042d80a31cfaaed1699459be62f6165d48c5d970a20aaf0bb531a1f614691` | plain text; a timestamp line precedes each text line |
| Timestamped candidate notes | [bigalow-video-notes.md](bigalow-video-notes.md) | tracked in git | Markdown |

Citation conventions:

- **Book** citations give the printed page first and the PDF page second,
  `book p.<printed>/<pdf>`. In the major-signals chapter the PDF page equals the
  printed page plus 6; this offset was verified on every cited page by reading the
  page header (20/26, 21/27, 23/29, 24/30, 37/43, 38/44, 46/52, 47/53, 53/59, 54/60,
  60/66, 61/67, 65/71, 66/72, 70/76, 71/77, 75/81, 76/82, 80/86, 81/87, 87/93,
  88/94, 91/97, 92/98, 97/103, 98/104, 104/110, 105/111, 109/115, 110/116). The offset
  is **not** constant across the scan: in the chapter on high-profit patterns the
  PDF page equals the printed page plus 4 (220/224, 231/235). Deferred rows cite
  the page header actually read.
- **Slide** citations are PDF page numbers of the presentation.
- **Webinar** citations are transcript timestamps (`mm:ss`, or `h:mm:ss`).
- "Conventional" marks a numeric threshold that no source states; the sources
  say "same or very near", "small", "at least two times". Conventional values are
  catalog parameters (Section 2) so a later revision changes one number, not a rule.

## 2. Conventions shared by every rule

Per closed bar `t` (prices in the instrument's price units, all positive and finite):

| Quantity | Definition |
| --- | --- |
| `body` | `abs(close - open)` |
| `range` | `high - low` |
| `upper` | `high - max(open, close)` |
| `lower` | `min(open, close) - low` |
| bullish / bearish | `close > open` / `close < open`; a bar with `close == open` has no colour |
| `mid(prior)` | `(open[t-1] + close[t-1]) / 2`, the prior **body** midpoint |
| `net(k)` | `close[t-1] - close[t-1-k]`, the local trend proxy over `k` closed bars before `t` |
| flat bar | `range == 0`; matches **no** geometric rule (TA-Lib's `CDLDOJI` returns 100 on a flat bar; the catalog does not) |

Catalog version `"1"` parameters:

| Parameter | Value | Used by |
| --- | --- | --- |
| `doji_body_ratio` | 0.10 | doji family |
| `doji_shadow_ratio` | 0.10 | dragonfly, gravestone |
| `long_leg_ratio` | 0.30 | long-legged doji |
| `spinning_top_body_ratio` | 0.30 | spinning top |
| `umbrella_shadow_multiple` | 2 | hanging man, inverted hammer |
| `umbrella_opposite_ratio` | 0.10 | hanging man, inverted hammer |
| `trend_lookback` | 3 | hanging man, inverted hammer (`net(3)`) |

Lookback = closed bars needed, including the current one. Polarity: +1 bullish,
-1 bearish, 0 neutral. Every rule reports WARMUP until its lookback exists and a
WARMUP entry carries polarity 0. Equality boundaries are written with `<=` / `<`
(or `>=` / `>`) exactly as implemented; integer example prices make every boundary
exact in floating point. Two-bar examples use the **bearish prior**
`(1000, 1010, 890, 900)` or the **bullish prior** `(900, 1010, 890, 1000)`, both with
body 900..1000 and `mid = 950`. Legacy examples are preceded by 20 **context
candles** `(1000, 1060, 980, 1040)` because TA-Lib's averaged thresholds need
history; the TA-Lib scores quoted below were reproduced with `talib` 0.8.1 on those
exact bars.

## 3. Admitted rules

### 3.1 Summary

| ID | Polarity | Lookback | Origin | Primary source |
| --- | --- | --- | --- | --- |
| `doji` | 0 | 1 | new | book p.21/27, p.23/29; webinar 07:34–07:40 |
| `doji_long_legged` | 0 | 1 | new | webinar 07:48; book p.33/39 (mention) |
| `doji_dragonfly` | 0 | 1 | new | webinar 07:54; book p.64/70 (mention) |
| `doji_gravestone` | 0 | 1 | new | webinar 08:05 |
| `spinning_top` | 0 | 1 | new | book p.20/26–21/27; webinar 29:56 |
| `bullish_harami` | +1 | 2 | new | book p.75/81 description, p.76/82 criteria; webinar 42:59–48:21 |
| `bearish_harami` | -1 | 2 | new | book p.80/86 description, p.81/87 criteria |
| `piercing_line` | +1 | 2 | new | book p.65/71 description, p.66/72 criteria; webinar 34:33–34:52 |
| `dark_cloud_cover` | -1 | 2 | new | book p.70/76 description, p.71/77 criteria |
| `bullish_kicker` | +1 | 2 | new | book p.109/115 description, p.110/116 criteria; webinar 53:08–53:29; slide 6 |
| `bearish_kicker` | -1 | 2 | new | same |
| `hanging_man` | -1 | 5 | new | book p.60/66 description, p.61/67 criteria; webinar 30:14, 33:17–33:23 |
| `inverted_hammer` | +1 | 5 | new | book p.91/97 description, p.92/98 criteria; webinar 38:39–38:59 |
| `bullish_engulfing` | +1 | 3 | legacy | book p.37/43–38/44; webinar 24:19–25:24 |
| `bearish_engulfing` | -1 | 3 | legacy | book p.46/52–47/53; webinar 27:07 |
| `hammer` | +1 | 12 | legacy | book p.53/59–54/60; webinar 30:14–31:08 |
| `shooting_star` | -1 | 12 | legacy | book p.87/93–88/94; slide 7 |
| `morning_star` | +1 | 13 | legacy | book p.97/103–98/104; slide 7 |
| `evening_star` | -1 | 13 | legacy | book p.104/110–105/111; webinar 48:36 (disputed wording, Section 7) |

Legacy lookbacks are TA-Lib's lookback plus one (`CDLENGULFING` 2, `CDLHAMMER` and
`CDLSHOOTINGSTAR` 11, `CDLMORNINGSTAR` and `CDLEVENINGSTAR` 12).

### 3.2 Doji family (single bar, neutral)

Source text: "formed when the open and the close are the same or very near the
same. The lengths of the shadows can vary" (book p.21/27); criteria 1 "the open and
the close are the same or very near the same" (p.23/29). Webinar 07:34–08:05 names
the three variants: long-legged ("the price move during the day is big and it
closes right about where it opens"), dragonfly ("opens and closes at the top"),
gravestone ("opens at the bottom, comes up and goes back down").

| ID | Formula | Context / confirmation | TA-Lib | Forex |
| --- | --- | --- | --- | --- |
| `doji` | `range > 0 and body <= doji_body_ratio * range` (0.10, conventional) | Context is not part of the rule; the book reads a doji at the top of a trend as a sell alert and a doji in a downtrend as needing "a bullish day to confirm" (p.23/29). The next-bar confirmation is the T5 sequence, not this rule. | `CDLDOJI` differs: it compares the body with 0.1 x the **10-bar average range** and returns 100 on a flat bar. Not used. | No adaptation; intraday bars are evaluated identically. |
| `doji_long_legged` | `doji and min(upper, lower) >= long_leg_ratio * range` (0.30, conventional). The "2 x body" wording is rejected because a zero body would qualify any shadow. | as `doji` | `CDLLONGLEGGEDDOJI` differs: it fires whenever the 10-bar-average doji test holds and the shadows exceed an averaged threshold; on the ledger negative example it still returns 100. Not used. | none |
| `doji_dragonfly` | `doji and upper <= doji_shadow_ratio * range` (0.10) | as `doji`; book p.64/70 calls it "the ultimate Hanging Man" at a top, an interpretation left to context. | `CDLDRAGONFLYDOJI` uses the averaged doji body and a "very short" averaged upper shadow. Not used. | none |
| `doji_gravestone` | `doji and lower <= doji_shadow_ratio * range` (0.10) | as `doji` | `CDLGRAVESTONEDOJI`, same averaging difference. Not used. | none |

Variants are additional hits beside `doji`; dragonfly and gravestone cannot coexist
with long-legged on one bar (a shadow `<= 0.10 range` cannot also be `>= 0.30 range`).

Examples (open, high, low, close):

| ID | Positive | Negative | Equality boundary |
| --- | --- | --- | --- |
| `doji` | `(1000, 1060, 980, 1002)`: body 2 <= 8 | `(1000, 1075, 975, 1011)`: body 11 > 10 | `(1000, 1075, 975, 1010)`: body 10 == 0.10 x 100, hit |
| `doji_long_legged` | `(1000, 1050, 950, 1000)`: shadows 50/50 | `(1021, 1050, 950, 1021)`: upper 29 < 30 | `(1020, 1050, 950, 1020)`: upper 30 == 0.30 x 100, hit |
| `doji_dragonfly` | `(1050, 1050, 950, 1050)`: upper 0 | `(1039, 1050, 950, 1039)`: upper 11 > 10 | `(1040, 1050, 950, 1040)`: upper 10 == 0.10 x 100, hit |
| `doji_gravestone` | `(950, 1050, 950, 950)`: lower 0 | `(961, 1050, 950, 961)`: lower 11 > 10 | `(960, 1050, 950, 960)`: lower 10 == 0.10 x 100, hit |

### 3.3 Spinning top (single bar, neutral)

Source: "small bodies relative to the shadows ... The size of the shadow is not as
important as the size of the body" (book p.20/26–21/27); webinar 29:56 "the bodies
are very small and the tails are more predominant".

| Field | Value |
| --- | --- |
| Formula | `range > 0 and doji_body_ratio * range < body <= spinning_top_body_ratio * range and upper >= body and lower >= body` (0.10 < body/range <= 0.30, conventional) |
| Context / confirmation | None in the rule; the book calls it neutral in a sideways market (p.20/26). |
| TA-Lib | `CDLSPINNINGTOP` differs: body smaller than the 10-bar average body and shadows longer than the body; it returns 100 on the ledger's doji and "not spinning" examples alike. Not used. |
| Forex | none |
| Positive | `(1000, 1060, 960, 1020)`: body 20 of range 100, shadows 40/40 |
| Negative | `(1000, 1066, 965, 1031)`: body 31 > 0.30 x 101 = 30.3 |
| Equality boundary | `(1000, 1065, 965, 1030)`: body 30 == 0.30 x 100, hit; `(1000, 1040, 960, 1020)`: upper 20 == body 20, hit; a doji-sized body (`body <= 0.10 range`) is never a spinning top |

### 3.4 Harami (two bars)

Source, bullish: "the bulls open the price higher than the previous close ... The
price finishes higher for the day" (p.75/81); criteria 3 "opens higher than the
close of the previous day and closes lower than the open of the prior day";
criteria 4 "just the body needs to remain in the previous day's body" (p.76/82).
Bearish: criteria 3 "opens lower than the close of the previous day and closes
higher than the open of the prior day" (p.81/87). Webinar 42:59–48:21 reads the
harami as a pause needing context and confirmation.

| ID | Formula (strict edges; an equal edge is not a harami) | Context / confirmation | TA-Lib |
| --- | --- | --- | --- |
| `bullish_harami` | prior bearish, current bullish, `open > close[t-1] and close < open[t-1]` | Criteria 2 "the downtrend has been evident" is context (T4), not geometry. Criteria 5: further confirmation required; left to the policy. | `CDLHARAMI` differs: it requires a long prior body and a short current body by 10-bar averages and returns 0 on every ledger example. Not used. |
| `bearish_harami` | prior bullish, current bearish, `open < close[t-1] and close > open[t-1]` | mirrored | same |

Forex: no gap requirement exists in the source; none added. A doji inside the prior
body is a harami plus `doji` (the "harami cross"), both hits reported.

| ID | Positive | Negative | Equality boundary |
| --- | --- | --- | --- |
| `bullish_harami` | bearish prior, `(920, 990, 910, 980)` | bearish prior, `(980, 990, 910, 920)`: current is bearish | bearish prior, `(900, 990, 895, 980)`: open == prior close 900, **no hit** |
| `bearish_harami` | bullish prior, `(980, 990, 910, 920)` | bullish prior, `(920, 990, 910, 980)`: current is bullish | bullish prior, `(1000, 1005, 910, 920)`: open == prior close 1000, **no hit** |

### 3.5 Piercing line and dark cloud cover (two bars)

Source, piercing: "opening below the low of the previous day. It closes more than
midway up the black candle" (p.65/71); criteria 3–4 "opens lower than the trading
of the prior day ... closes more than half-way up the black candle" (p.66/72);
webinar 34:33–34:47 "opens below any of the trading of the previous day ... closes
more than one halfway up the previous day's candle". Dark cloud: "open price is
higher than the high of the previous day. It closes at least one-half the way down"
(p.70/76); criteria 3–4 (p.71/77).

| ID | Formula | Context / confirmation | TA-Lib |
| --- | --- | --- | --- |
| `piercing_line` | prior bearish, current bullish, `open < close[t-1] and close > mid(prior) and close < open[t-1]` | Criteria 2 downtrend is T4 context; the book requires "bullish confirmation the next day" (webinar 34:52), left to the policy. | `CDLPIERCING` requires `open < low[t-1]` and long bodies by 10-bar averages; it happens to return 100 on the positive example because that example also gaps below the prior low, but it returns 0 on the FX-adapted cases. Not used. |
| `dark_cloud_cover` | prior bullish, current bearish, `open > close[t-1] and close < mid(prior) and close > open[t-1]` | mirrored | `CDLDARKCLOUDCOVER` requires `open > high[t-1]`; same remark. Not used. |

Forex adaptation: spot FX has no daily opening gap inside a session, so the book's
"open below the prior LOW" / "above the prior HIGH" becomes "open beyond the prior
CLOSE". The midpoint is the prior **body** midpoint; the close must be strictly
beyond it; a close reaching the prior open is an engulfing, not a piercing line
(the book, p.65/71: "The Piercing pattern has almost the same elements as the
Bullish Engulfing signal"). The book's range-gap variant is DEFERRED (Section 5).

| ID | Positive | Negative | Equality boundary |
| --- | --- | --- | --- |
| `piercing_line` | bearish prior, `(880, 980, 870, 970)`: open 880 < 900, close 970 > 950, 970 < 1000 | bearish prior, `(880, 960, 870, 940)`: close 940 < mid 950 | bearish prior, `(880, 960, 870, 950)`: close == mid, **no hit**; `(900, 980, 890, 970)`: open == prior close, **no hit** |
| `dark_cloud_cover` | bullish prior, `(1020, 1030, 920, 930)` | bullish prior, `(1020, 1030, 940, 960)`: close 960 > mid | bullish prior, `(1020, 1030, 940, 950)`: close == mid, **no hit**; `(1000, 1030, 920, 930)`: open == prior close, **no hit** |

A close reaching the prior open: bearish prior then `(880, 1020, 870, 1000)` is
`bullish_engulfing` (TA-Lib score 80, one equal edge) and not `piercing_line`.

### 3.6 Kicker (two bars)

Source: "The first day's open and the second day's open are the same or gaps beyond
the previous open. The price movement is in opposite directions from the opening
price"; "The trend has no relevance" (criteria 1–2, p.110/116); "the bodies of the
candles are opposite colors" (p.110/116); webinar 53:08–53:29 "they gap it at or
above the previous day's open and start going the opposite direction"; slide 6
labels the kicker signal.

| ID | Formula | Context / confirmation | TA-Lib |
| --- | --- | --- | --- |
| `bullish_kicker` | prior bearish, current bullish, `open >= open[t-1]` (bodies touch or gap; no overlap) | None: "the trend has no relevance" and the book says the kicker "does not require confirmation" (p.109/115). The policy still applies its registered context. | `CDLKICKING` requires two marubozu and a full-range gap; it returns 0 on every ledger example. Not used. |
| `bearish_kicker` | prior bullish, current bearish, `open <= open[t-1]` | mirrored | same |

Forex adaptation: the daily gap becomes body non-overlap at the open; touching
opens qualify ("the same or gaps beyond"). Criteria 4 "the price never retraces
into the previous day's trading range" is intrabar information not available from
closed OHLC and is a DEFERRED variant (Section 5).

| ID | Positive | Negative | Equality boundary |
| --- | --- | --- | --- |
| `bullish_kicker` | bearish prior, `(1030, 1100, 1030, 1090)` | bearish prior, `(999, 1100, 999, 1090)`: bodies overlap by 1 | bearish prior, `(1000, 1100, 1000, 1090)`: open == prior open, hit |
| `bearish_kicker` | bullish prior, `(870, 870, 800, 810)` | bullish prior, `(901, 901, 800, 810)` | bullish prior, `(900, 900, 800, 810)`: open == prior open, hit |

### 3.7 Hanging man and inverted hammer (single bar plus trend precondition)

Source, hanging man: "requires a lower tail two times greater than the body ...
found at the top of a trend" (p.60/66); criteria (p.61/67) "1. The upper shadow
should be at least two times the length of the body. 2. The real body is at the
upper end of the trading range. 3. There should be no upper shadow or a very small
upper shadow." Criteria 1 reads "upper" in the OCR layer while the description and
criteria 2–3 describe a lower tail; the description is followed (Section 7).
Webinar 33:17–33:23 "the hanging man is the opposite of the hammer signal, the tails
to the downside and the head is up toward the top". Inverted hammer: criteria
(p.92/98) "1. The upper shadow should be at least two times the length of the body.
2. The real body is at the lower end of the trading range. 3. There should be no
lower shadow or a very small lower shadow"; webinar 38:39–38:59.

| ID | Formula | Context / confirmation | TA-Lib |
| --- | --- | --- | --- |
| `hanging_man` | `body > 0 and lower >= umbrella_shadow_multiple * body and upper <= umbrella_opposite_ratio * range and net(3) > 0` | "Top of a trend" is not computable from the sources; the catalog uses the local proxy `net(3) > 0` (conventional, lookback 5). `net(3) == 0` is no hit. This proxy never merges with the T4 trend evidence. Confirmation ("a black candle" next day, criteria 4) is left to the policy. | `CDLHANGINGMAN` uses 10-bar averaged body/shadow thresholds and a different trend test; on the ledger's positive example it returns 0 while `CDLHAMMER` returns 100. Not used. |
| `inverted_hammer` | `body > 0 and upper >= umbrella_shadow_multiple * body and lower <= umbrella_opposite_ratio * range and net(3) < 0` | mirrored (`net(3) < 0`) | `CDLINVERTEDHAMMER`, same averaging difference; on the positive example `CDLSHOOTINGSTAR` returns -100 instead. Not used. |

Forex: no gap requirement; none added. A zero body is a doji matter (dragonfly /
gravestone), never an umbrella hit. Examples use four prior bars `(c, c+10, c-10, c)`
closing at `c1..c4` so that `net(3) = c4 - c1`:

| ID | Positive | Negative | Equality boundary |
| --- | --- | --- | --- |
| `hanging_man` | priors 900, 1040, 1040, 1040 (`net(3) = +140`), then `(955, 962, 850, 960)`: body 5, lower 105 >= 10, upper 2 <= 11.2 | priors 1040, 1040, 1040, 1040 (`net(3) = 0`), same bar: no hit | priors as positive, `(940, 951, 920, 950)`: lower 20 == 2 x body 10, hit; `(940, 960, 860, 950)`: upper 10 == 0.10 x 100, hit; `(940, 951, 921, 950)`: lower 19 < 20, no hit |
| `inverted_hammer` | priors 1040, 900, 900, 900 (`net(3) = -140`), then `(960, 1070, 958, 955)`: body 5, upper 110 >= 10, lower 3 <= 11.2 | priors 900, 900, 900, 900 (`net(3) = 0`): no hit | priors as positive, `(950, 980, 949, 960)`: upper 20 == 2 x body 10, hit; `(950, 979, 949, 960)`: upper 19 < 20, no hit |

### 3.8 Legacy six (TA-Lib verbatim, byte-identical legacy behaviour)

The six existing labels stay exactly what `perception/candlestick.py` computes:
`CDLENGULFING` sign, `CDLHAMMER`, `CDLSHOOTINGSTAR`, `CDLMORNINGSTAR` and
`CDLEVENINGSTAR` with `penetration = 0.3`, default candle settings. The book
describes the same shapes; TA-Lib's averaged thresholds are kept so that legacy mode
reproduces every historical decision (CND-09). Where the book and TA-Lib differ the
difference is recorded, not resolved.

| ID | Book definition | TA-Lib rule kept | Difference recorded |
| --- | --- | --- | --- |
| `bullish_engulfing` | "opens lower than the previous day's close and closes higher than the previous day's open"; "can be formed with the open and the close of one end of the pattern being equal but not ... both" (p.37/43); criteria p.38/44 "shadows are not a consideration" | `CDLENGULFING > 0`: current bullish, prior bearish, body covers the prior body; one equal edge scores 80, none 100 | TA-Lib's engulfing needs no prior trend; the book's "definable down trend" is T4 context. |
| `bearish_engulfing` | mirrored (p.46/52, criteria p.47/53) | `CDLENGULFING < 0` | same |
| `hammer` | "the lower shadow or tail should be at least two times greater than the body" (p.53/59); criteria p.54/60: body at the upper end, no or very small upper shadow, next-day confirmation | `CDLHAMMER`: body shorter than the 10-bar average body, lower shadow **> body** (strict, factor 1.0), upper shadow very short by the 10-bar average, body near the prior low | The book's 2x tail ratio is **not** TA-Lib's 1x; the boundary example below is TA-Lib's. |
| `shooting_star` | "upper shadow at least two times greater than the body" (p.87/93); criteria p.88/94 | `CDLSHOOTINGSTAR`: short body, upper shadow > body (strict), very short lower shadow, body gapping above the prior body | same 2x versus 1x difference; TA-Lib also requires the upward gap. |
| `morning_star` | "close at least halfway up the black candle" (criteria 3, p.98/104); star day gaps optional | `CDLMORNINGSTAR(penetration=0.3)`: long bearish first bar, short star, bullish third bar closing **more than** 30 percent into the first body (strict) | Book halfway (0.5) versus TA-Lib 0.3 as configured historically; a 40 percent close fires at 0.3 and not at 0.5. |
| `evening_star` | "close at least halfway down the white candle" (criteria 3, p.105/111) | `CDLEVENINGSTAR(penetration=0.3)` | same |

Context: the book places every legacy signal at a trend end; that is T4 context.
Confirmation: the book asks for a next-day confirmation for hammer, shooting star and
the stars; left to the policy. Forex: no adaptation; the star gaps are optional in
TA-Lib's default settings, so intraday FX bars are evaluated unchanged.

Examples after 20 context candles `(1000, 1060, 980, 1040)`; TA-Lib scores verified:

| ID | Positive (score) | Negative (score 0) | Equality boundary |
| --- | --- | --- | --- |
| `bullish_engulfing` | `(1000, 1010, 890, 900)`, `(880, 1040, 870, 1030)` (100) | `(1000, 1010, 890, 900)`, `(890, 1040, 870, 990)`: close 990 < prior open | `(1000, 1010, 890, 900)`, `(900, 1040, 870, 1030)`: open == prior close, score 80, hit |
| `bearish_engulfing` | `(900, 1010, 890, 1000)`, `(1020, 1030, 870, 880)` (-100) | `(900, 1010, 890, 1000)`, `(1010, 1030, 870, 910)` | `(900, 1010, 890, 1000)`, `(1000, 1030, 870, 880)`: open == prior close, score -80, hit |
| `hammer` | `(970, 982, 850, 980)` (100) | `(960, 982, 945, 980)`: lower 15 < body 20 | `(960, 982, 940, 980)`: lower 20 == body 20, **no hit** (strict); `(960, 982, 939, 980)` hits |
| `shooting_star` | `(1060, 1200, 1058, 1070)` (-100) | `(1060, 1079, 1058, 1080)`: upper < body | `(1060, 1100, 1058, 1080)`: upper 20 == body 20, **no hit**; `(1060, 1101, 1058, 1080)` hits |
| `morning_star` | `(1000, 1010, 790, 800)`, `(750, 770, 740, 760)`, `(780, 950, 770, 940)` (100) | third bar closing 850 (25 percent into the body) | third bar closing 860 (exactly 30 percent), **no hit**; 861 hits; 880 (40 percent) hits at 0.3 and not at 0.5 |
| `evening_star` | `(1000, 1210, 990, 1200)`, `(1250, 1270, 1240, 1260)`, `(1220, 1230, 1050, 1060)` (-100) | third bar closing 1150 | third bar closing 1140 (exactly 30 percent), **no hit**; 1139 hits; 1120 (40 percent) hits at 0.3 and not at 0.5 |

Legacy label: `legacy_label(hits)` reproduces `select_pattern` over the six legacy
IDs only (lexical first within one polarity; opposing legacy hits abstain; new IDs and
WARMUP entries are ignored), so legacy mode stays equal to `detect_pattern`.

## 4. Context, trend and confirmation definitions

| Component | Definition | Source |
| --- | --- | --- |
| T-line, EMA(8) | `ema_period = 8`; seeded like `training.ema_series` (running simple mean of the first 8 closes, then `ema = close * k + ema_prev * (1 - k)`, `k = 2 / 9`); READY at 8 closed bars (value = plain mean); WARMUP before. `t_line_position`: ABOVE when `close > ema`, BELOW when `close < ema`, ON when equal. | webinar 10:49–11:07 "this is the 8 exponential moving average which is what we call the T line", 26:54, 1:14:00; slides 6–7 "a candlestick buy signal and a close above the t-line" |
| Stochastic 12,3,3 | `raw %K = 100 * (close - LL12) / (HH12 - LL12)` over the last 12 bars' highs and lows; `slow %K = SMA(3)` of raw; `%D = SMA(3)` of slow %K; READY at 12 / 14 / 16 bars. `HH12 == LL12` makes the raw value UNDEFINED (None, no NaN, no exception) and every smoothed value that consumes it UNDEFINED. Zones from `%D`: OVERBOUGHT when `%D > 80`, OVERSOLD when `%D < 20`, NEUTRAL otherwise (80 and 20 are NEUTRAL), UNDEFINED when `%D` is None. | webinar 10:03–10:09 "1233 ... overbought ... above 80 ... oversold ... below 20", 50:17 "stochastic period is 12 3 3", 51:23 "on the stochastics it's just simple moving average"; book p.24/30 "the stochastic settings for all the charts are 12,3,3" |
| SMA levels | `sma_periods = (20, 50, 200)`; `distance_m = (close - sma_m) / sma_m`, dimensionless; READY at `m` bars; a flat series gives exactly 0.0. | webinar 10:16–10:23, 14:45–14:52 "the 200 the 50 and the gray line is the 20, all simple moving averages", 1:14:06; book p.24/30 "50 day and 200 day simple moving averages" |
| Trend evidence | UP when `t_line_position` is ABOVE, DOWN when BELOW, FLAT when ON; WARMUP while the EMA is WARMUP. Separate from the catalog's `net(3)`. | derived from the T-line rule (slides 6–7) |
| Context status | READY when every indicator is READY, else WARMUP; UNDEFINED is a READY-time value state. | design.md evidence contract |
| Sequence confirmation | Catalog `doji` on bar `t` opens a CANDIDATE. The **next expected** closed bar confirms when its body engulfs the doji body inclusively with mandatory colour: bullish `close > open and open <= min(open_d, close_d) and close >= max(open_d, close_d)`; bearish mirrored. Direction = confirming bar colour; ids `doji_engulfing_bullish` (+1) / `doji_engulfing_bearish` (-1); `confirmation_time` = the confirming bar's close. Anything else expires the candidate (`not_engulfing`); a doji that ends a candidate opens a new one; a bar never confirms itself. | webinar 24:13–25:24 "a doji followed by a bullish engulfing signal ... engulfing the body of this candle not necessarily the shadows", 27:51–28:15 (bearish combo), 15:08 (doji "needs ... the next day"); book p.37/43 one equal edge allowed |
| Expected next bar | `candidate_close_time + timeframe` under the continuous calendar policy; under a scheduled closure `[from, to)` that contains the continuous expectation, the earliest timeframe-aligned close strictly after `to`. A bar closing later than expected expires the candidate with `missing_expected_bar` and never confirms it. | design.md timing section; the FX weekend policy content is registered by the T7 manifest owner |
| Policy eligibility | candidate directions = polarities of READY directional hits plus a sequence direction confirmed at this bar; +1 satisfied when context READY, T-line ABOVE, zone not OVERBOUGHT and not UNDEFINED; -1 mirrored with BELOW / OVERSOLD; eligible = exactly one satisfied candidate direction. Advisory never vetoes; required-entry vetoes with reason codes `warmup`, `neutral_only`, `conflicting`, `context`. SMA distances are informational only. | slides 6–7; webinar 10:49–11:27, 09:56–10:23; spec CND-11/12 |

## 5. Forex adaptation summary

| Source assumption | Adaptation |
| --- | --- |
| Daily bars with an overnight gap between close and open | Intraday spot-FX bars have no gap inside a session. Gap-based openings become body relations at the open: piercing/dark cloud "open beyond the prior close"; kicker "open at or beyond the prior open". Full-range gaps (open beyond the prior high/low) exist only across the weekend closure and are DEFERRED. |
| "Next day" confirmation | The next expected closed bar on the configured timeframe (Section 4). Scheduled closures are not missing bars; the calendar policy is a T5 input recorded by the T7 manifest. |
| Daily moving-average lookbacks (20/50/200 "day") | Periods are counted in closed bars of the configured timeframe; no silent conversion to days. |
| Volume "signal enhancements" | Not a rule input; spot-FX quote activity is a separately named optional factor. |
| Intrabar opening/stop tactics (webinar 28:28–29:05, 35:56–36:18) | Out of scope for closed-bar evidence. |

## 6. DEFERRED formations

| Candidate | Source | Reason deferred |
| --- | --- | --- |
| J-hook | book p.220/224 ff. (chapter on high-profit patterns); webinar 56:51 | Needs a bounded window, causal pivot and pullback geometry and breakout confirmation; the sources describe it visually ("pullback that starts to ..."); a future breakout cannot label an earlier window. Requires reviewed labels before any formula. |
| Fry-pan bottom | book p.231/235 ff.; slide 4; webinar 56:46 | Curvature over an unspecified window ("approximately one-half the distance"); subjective geometry, no computable criteria. |
| Dumpling top | slide 4; webinar 1:01:57–1:02:04 ("the opposite of the fry pan bottom") | Same as fry-pan; not found as a criteria page in the book index. |
| Cradle | book index p.252–255 (PDF 256–259); slide 4 | Multi-bar pattern with a "large dark candle" and a later reversal; no bounded, causal definition in the sources. |
| Scoop | book index p.237–243 (PDF 241–247); slide 4 | Same: visual pullback/resumption description without computable thresholds. |
| Belt-hold | slide 4 | Named only; no criteria in the sources read. Related to the closing/opening marubozu (book p.20/26) which is likewise not admitted. |
| Gap formations | book chapter "STAR AND GAP" (PDF 105 ff.), abandoned baby index p.99 (PDF 105); webinar 26:26–26:48 (body versus range gap wording), 33:10 ("abandoned baby"), 23:32–23:38; the book's range-gap piercing/dark cloud and kicker "never retraces" variants | Spot FX has no intraday gap; a gap definition needs the weekend calendar policy (T7) and the body-gap versus range-gap distinction the transcript leaves ambiguous (Section 7). |
| T-line crunch | webinar 59:11–59:41 | Needs a causal resistance and compression definition; setup versus confirmed breakout not separable from the description. |
| Kicker "true kicker" shadow variant and doji-interrupted variant | book p.110/116 criteria 4; webinar 54:02–55:28 | Criteria 4 is intrabar information; the variant name is uncertain in the transcript. |
| Hammer 2x / inverted-hammer confirmation exits, T-line distance profit-taking | webinar 11:14–11:27, 31:02–31:08 | Exit policy; Story 21 / a separate scope decision. |

## 7. Ambiguities preserved (not silently resolved)

1. **Hanging man criteria OCR line.** Book p.61/67 criteria 1 reads "The upper
   shadow should be at least two times the length of the body" while the
   description (p.60/66) and criteria 2–3 describe a lower tail with the body at the
   top. The ledger follows the description: `lower >= 2 x body`. Recorded, not corrected
   in the reference.
2. **Webinar 23:38** says "gap up from a doji in the overbought area" inside a
   discussion of buy signals that otherwise describes oversold conditions. Left
   unresolved; no rule uses it.
3. **Webinar 48:36** describes an "evening star" with morning-star geometry ("dark
   day, indecision and then the third day closes more than halfway up this dark
   candle"). The legacy stars follow the book (p.97/103, p.104/110), not this passage.
4. **Webinar 26:26–26:48** discusses gaps where "the candle bodies do not overlap, not
   necessarily the bodies but also your trading range". Body gap and range gap are
   kept distinct; only body relations are admitted (kicker, piercing, dark cloud).
5. **Webinar 10:16** mentions "the 200 the 50 and the 15 in the 20-day moving
   average"; 14:45 and 1:14:06 list 20/50/200. The catalog uses 20/50/200; the "15"
   is not adopted.
6. **Doji thresholds.** "Same or very near" carries no number; 0.10 of range is
   conventional and versioned (Section 2).

## 8. Reconciliation with the Phase 1 feature files

The feature files `candle_contract.feature`, `candle_catalog.feature`,
`candle_context.feature`, `candle_sequence.feature` and `f3_policy_modes.feature`
state the same formulas as this ledger. Every formula, boundary and parameter above is
adopted unchanged. Two citations were refined after reading the pages: the bullish
harami criteria are on printed page 76 (PDF 82), not 75, and the hanging-man
"upper shadow" OCR line is criteria 1 on printed page 61 (PDF 67), the description
being on page 60. Neither changes a formula or an example.

## 9. Non-claims

No win rate, "strongest signal" or profitability statement from the book, slides or
webinar is used as a threshold, prior or acceptance target. Synthetic examples prove
mechanics only. Nothing here authorizes live trading.
