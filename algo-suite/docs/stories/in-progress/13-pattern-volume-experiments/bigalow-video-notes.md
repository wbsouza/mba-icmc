# Bigalow webinar: timestamped research notes

Status: source-review notes, September 28, 2026; not executable specifications.
Parent: [candlestick extension](candlestick-extension.md).

Source: [Stephen Bigalow webinar supplied by the user](https://www.youtube.com/watch?v=1fB3EF7XeXU).
The user supplied a timestamped transcript spanning 00:18–1:22:57. These notes
paraphrase that transcript; no independent audio or chart-frame verification has
been performed. Exact video title, channel, and publication date remain to be
verified for the bibliography. Do not assume this video is the January 2023 CMT
presentation. The transcript contains recognition errors and apparent spoken
corrections. Cosmetic typos are acceptable; rule-changing ambiguities are not.

## Durable local transcript

The user subsequently supplied this read-only file:
`/media/nas/wellington/mba/related-work/books/books-forex-trading/high-profit-trades-found-with-candlestic-breakout-patterns.txt`.

- SHA-256: `18e042d80a31cfaaed1699459be62f6165d48c5d970a20aaf0bb531a1f614691`.
- Size: 69,774 bytes; 1,450 newline-delimited lines.
- The header identifies video `1fB3EF7XeXU`; the inspected opening matches the
  supplied discussion transcript. This is a local source for the same webinar,
  not a second independent presentation or a verified manual transcription.
- Read this file during source review so the next agent does not depend on chat
  history. Preserve its original text and path spelling; store corrections in
  the rule ledger with timestamps rather than modifying the reference.

## Candidate rule ledger

These are the speaker's proposals, not measured probabilities or recommended
live-trading settings. Resolve each row into a versioned rule and acceptance
examples before using it as a deterministic rule or training label.

| Transcript time | Candidate concept | Implementation/review requirement |
| --- | --- | --- |
| 07:34–09:23 | Doji variants and spinning tops express indecision; interpretation depends on preceding trend and later confirmation. | Define body/range tolerances and causal trend context. Do not assign every doji a fixed bullish/bearish label. |
| 09:56–10:23; 50:17–51:23 | Stochastic settings 12,3,3; overbought above 80 and oversold below 20; later clarification mentions simple averaging. | Specify exact fast/slow K/D mapping, smoothing, equality behavior, warm-up, and zero-range handling before choosing library arguments. |
| 10:49–11:27; 26:54–27:07; 1:14:00–1:14:12 | T-line is an eight-period exponential moving average; long management combines a buy signal/close above it and later a sell signal/close below it. | EMA(8) is supported by repeated transcript statements. Price input, initialization, equality, and signal timing still require explicit definitions. Preserve protective stops independently. |
| 14:45–14:52; 1:14:00–1:14:17 | SMA(20), SMA(50), and SMA(200) provide context levels. | Daily lookbacks cannot silently become H1/H4 periods. An earlier apparent mention of 15 at 10:16 requires verification rather than inclusion by default. |
| 11:14–14:30 | A reversal signal far from the T-line motivates profit-taking. | Define distance and threshold using a registered rule, not visual hindsight; compare this exit policy separately from entry filtering. |
| 15:08–18:24; 21:00–23:55 | Doji followed by directional opening/gap and context confirmation. | Separate next-bar opening information from next-bar closing confirmation. Register gap semantics and Forex session handling; review the conflicting wording near 23:38. |
| 24:13–25:24; 27:51–28:15 | Left/right combinations join a doji with bullish or bearish engulfing; engulfing concerns the body rather than necessarily the full range. | Treat as a sequence/context candidate; compare book definition and TA-Lib geometry, including equal boundaries. |
| 28:28–29:05; 35:56–36:18 | Intrabar profit-protection stops depend on the opening price and subsequent movement. | The referenced prior close/high and tick offsets are unclear across passages. Verify charts/audio and execution timing; do not infer same-bar event order from OHLC. |
| 30:14–31:08; 33:17–34:03; 38:39–39:25; 41:06–41:28 | Hammer/hanging-man and inverted-hammer/shooting-star interpretations depend on trend and confirmation; hammer discussion gives a two-to-one tail/body relationship. | Specify ratio boundary, upper shadow, zero-body handling, and causal trend. Clarify what the signal's head means for invalidation; distinguish close-based exits from stop orders. |
| 34:22–35:36; 48:28–50:03 | Piercing and morning/evening-star patterns use gap/midpoint relationships and confirmation. | Resolve body versus range midpoint and the apparent morning/evening naming error near 48:36 against the original source. Do not assume TA-Lib defaults reproduce the book. |
| 39:39–40:26 | Lower-timeframe observations can warn of a reversal within a higher-timeframe setup. | Only use higher-timeframe bars available at the decision time; document partial versus closed bars and test alignment. |
| 42:59–48:21 | Harami formations interpreted as a pause or possible change, with trend/level context and confirmation. | Separate geometry, contextual eligibility, and execution; preserve ambiguous or absent confirmation. |
| 51:29–52:55 | Visual interpretation includes trend direction, stage, and duration beyond the isolated candle shape. | Motivation for the optional Laya context experiment, not evidence that Laya already learns these relationships or that explicit rules cannot work. |
| 53:08–55:28 | Kicker and a doji-interrupted variant indicate an abrupt directional change in the speaker's framework. | Verify gap and body requirements, the uncertain variant name, and TA-Lib equivalence. Do not inherit claims that it is the strongest signal as model probabilities. |
| 56:46–58:59; 1:01:57–1:02:15 | J-hook pullback/resumption, fry pan bottom, and dumpling top provide broader formation candidates. | Define bounded windows, causal curvature/pivots, breakout/confirmation, and invalidation. Future breakout cannot label an earlier window as already confirmed. |
| 59:11–59:41 | T-line crunch describes price/support compression toward resistance and a possible breakout. | Specify causal resistance and compression criteria, then separate a developing setup from confirmed breakout. |

## Ambiguities and evidence boundaries

- At 23:38 the transcript says overbought in a bullish gap discussion otherwise
  describing oversold conditions. Preserve this as unresolved, not an automatic
  correction or an instruction to train on contradictory labels.
- At 26:26–26:48 body gaps and full-range gaps are discussed ambiguously. Define
  opening gaps, body separation, and full-range separation as distinct features.
- Around 48:36 a formation called evening star is described with bullish
  morning-star geometry; the later examples distinguish the two. Verify before
  assigning the disputed passage to a class.
- At 46:19–46:50 T-line management and a reference to closing below the 50 occur
  near one another. Do not silently replace EMA(8) with SMA(50), or vice versa.
- The 51:29 discussion questions formula-only implementations, while 1:09:30
  describes ongoing MetaStock formula work. This motivates reviewing context;
  it does not prove algorithmic recognition is impossible or requires ML.
- References to tops/bottoms and selected successful charts risk hindsight bias.
  Construct labels from information available at the decision, not subsequent
  peaks, valleys, or returns. Incomplete setups must remain distinguishable.
- The speaker's win-rate estimate at 1:11:47–1:12:08 and historical profitability
  claims are anecdotes, not audited results, acceptance targets, or priors for
  Laya. Book, slides, and this video are related-author sources, not three
  independent validations.
- Exclude promotional offers, testimonials, and unrelated anecdotes from the
  rule/label dataset. Do not train on the transcript as if it were labeled OHLC.

## Next review actions

1. Check the rule-bearing video frames/audio and link matching book/slide pages.
2. Mark each ledger row confirmed, adapted for Forex, unresolved, or deferred.
3. Specify time of availability and known input units for every feature.
4. Create independently reviewed positive, negative, and boundary examples.
5. Compare explicit rules with a frozen Laya context model under the extension's
   registered recognition and trading-evaluation protocol. Keep risk controls
   independent and archive full per-filter settings beside every result.

No runtime defaults, model weights, or experiment outcomes changed with these
notes. Full source review and implementation remain unchecked in
[progress.md](progress.md).
