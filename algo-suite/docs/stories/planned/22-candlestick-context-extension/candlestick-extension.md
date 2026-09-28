# Story 13 extension: candlestick catalog and learned context

Status: planned extension, recorded September 28, 2026. No implementation,
training, model download, or new experiment is claimed by this document.
See [progress and handoff](progress.md) for ownership and delivery status.

This document is the source/research brief. The consolidated `tlc-spec-driven`
plan owns the implementation requirements and checklist:
[specification](../../../../../.specs/features/candlestick-context/spec.md),
[design](../../../../../.specs/features/candlestick-context/design.md), and
[24 pending tasks](../../../../../.specs/features/candlestick-context/tasks.md).
The user explicitly requested planning only; do not start implementation from
this brief or interpret historical Story 13 results as extension validation.

## Purpose

As a researcher, I want to expand candlestick recognition and evaluate a learned
context filter alongside explicit rules, so that the engine can test formations
and combinations beyond its current TA-Lib subset without sacrificing auditability.

The user proposes Laya as an open-weight alternative to Jev's bounded-decision
approach, not a generative chatbot or an autonomous trader. It complements
TA-Lib; it does not replace exact rules merely to reproduce them less precisely.
This is part of the contest of filter combinations, not a mandatory standalone
book strategy. The completed Story 13 experiments remain historical evidence.

## Existing implementation

The current [detector](../../../../algo-backtest/src/algo_backtest/perception/candlestick.py)
uses five TA-Lib functions to produce six labels: bullish/bearish engulfing,
hammer, shooting star, morning star, and evening star. It consumes closed midpoint
OHLC, retains 64 candles, and collapses detections to one lexical-priority label
within a polarity; opposing detections abstain. This is our selected subset, not
the full TA-Lib catalog or a context-aware implementation of Bigalow's method.

Review F3, F7 feature contracts, and viewer labels before extending that vocabulary.
Preserve old model compatibility explicitly; reject incompatible artifacts with a
retraining instruction. Do not silently reinterpret historical runs.

## References and source review

### Stephen W. Bigalow

Primary book: *High Profit Candlestick Patterns: Turning Investor Sentiment Into
Profits*, Stephen W. Bigalow. Verify the edition from the scan before creating a
formal bibliographic entry. The user also owns the physical book.

- Local, read-only source:
  `/media/nas/wellington/mba/related-work/books/books-forex-trading/high-profit-candlestick-patterns.pdf`.
- PDF pages: 411.
- SHA-256: `d962029526518201444cc0d19f52384df8bb095b98b4a6053a7159bfdb289751`.
- The scan has an imperfect OCR layer. Existing extraction is sufficient for
  initial reading; tolerate cosmetic typos. Check scanned pages when ambiguity
  changes a threshold, candle relationship, entry time, or stop placement.
- Review so far: contents and selected passages, not the whole book. Printed
  pages 15–17 emphasize major signals and their context. Do not convert the
  author's performance claims into empirical findings for this engine.
- Prioritize major signals, moving averages, gaps, technical-pattern context,
  entry/exit confirmation, and stops. Record printed and PDF page numbers for
  every proposed rule; do not assume one constant page offset across the scan.

Build a rule ledger: source page, precise definition, existing support,
implementation gap, data requirements, Forex adaptation, and acceptance example.
Separate candle geometry from trend/context and later confirmation. Daily stock
opening/gap rules need explicit adaptation before use on intraday Forex. Use
short paraphrases and local citations, not committed scans or full OCR text.

### Companion presentation supplied by the user

Local, read-only source:
`/media/nas/wellington/mba/related-work/books/books-forex-trading/0104-Steve-Bigalow.pdf`.

- Alternate user-supplied path:
  `/home/wellington/Downloads/0104-Steve-Bigalow.pdf`. SHA-256 comparison on
  September 28, 2026 confirms it is byte-identical to the NAS copy, not a new
  presentation or independent source.
- 60 PDF pages; title slide: *Candlestick Patterns*, CMT presentation, January
  2023. PDF metadata title: *Introduction to Advanced Candlestick Patterns*.
  Metadata names PAT JOHNSON as author; verify presenter attribution before
  the formal citation rather than treating export metadata as authorship proof.
- SHA-256: `b1e6cdfc207854879d9563d036ab70e383a36026cfaf4df59bae57bbfbfe818b`.
- Initial review: extracted slides 1–10, not a full slide/chart audit. Slide 4
  lists fry pan bottom, dumpling top, cradle, Jay-hook, scoop, belt-hold, and gap
  formations. These are candidates for the rule ledger, not implemented labels.
- Slides 6–7 combine candle signals with closes relative to a T-line for long
  and short management. The user-supplied video transcript below identifies
  the T-line repeatedly as EMA(8). Verify remaining computational and timing
  details before coding; the slides alone did not establish these details.

Compare presentation rules against the book, recording refinements or conflicts
instead of silently merging them. Broader formations may motivate a learned
context detector, but still need causal, reviewable labels and an explicit-rule
baseline. The presentation is not independent evidence of trading performance.

### Companion video and user-supplied transcript

- [Bigalow webinar](https://www.youtube.com/watch?v=1fB3EF7XeXU).
- [Timestamped candidate-rule ledger and ambiguity notes](bigalow-video-notes.md).
- Durable, read-only transcript supplied by the user:
  `/media/nas/wellington/mba/related-work/books/books-forex-trading/high-profit-trades-found-with-candlestic-breakout-patterns.txt`.
  Its header identifies the same webinar; see the notes for the checksum.

The transcript supplies EMA(8), stochastic 12,3,3 with 80/20 context levels,
SMA(20/50/200), confirmation sequences, and broader formation candidates.
These are research inputs, not newly enabled parameters. The video has not been
independently watched in this review; verify rule-changing inconsistencies in
the audio/charts. In particular, distinguish shape recognition from contextual
interpretation and from when an entry or exit can actually execute.

The context discussion around 51:29–52:55 motivates testing Laya beyond isolated
TA-Lib shapes. It neither validates Laya nor supplies a labeled temporal dataset.
Cross-reference book, slides, and video in the rule ledger without counting them
as independent performance evidence.

### Laya

- [Official model and weights](https://huggingface.co/convaiinnovations/laya).
- [Community explanation supplied by the user](https://huggingface.co/blog/sora-2/laya-ai-model-how-it-works-run-it-locally-and-eval).

The official card describes Apache-2.0 weights, a ModernBERT-based English
checkpoint, text/JSON inputs, typed decisions, and fine-tuning. It is not evidence
of candle-recognition capability. Recheck the pinned revision, license, runtime,
context limits, and known limitations before implementation. Use the native
Python runtime first; do not assume llama.cpp compatibility.

Non-generative outputs are not proof of correctness, calibrated confidence, or
bitwise reproducibility. Verify repeatability with frozen preprocessing, question
schemas, weights, runtime, and device settings. Record numerical tolerances and
test decision stability near thresholds. Adaptation means versioned retraining
between experiments, never changing weights or thresholds inside a frozen run.

### Additional comparison sources

- [TA-Lib pattern catalog](https://ta-lib.github.io/ta-lib-python/func_groups/pattern_recognition.html):
  distinguish unsupported patterns from functions we have simply not enabled.
- [EarnForex Candlestick-Pattern](https://github.com/EarnForex/Candlestick-Pattern):
  optional MQL4/5 port candidate suggested by the user. Verify exact source,
  licensing/attribution, indexing, unfinished-bar behavior, and parity before
  adoption. No port or source-logic audit is complete in this planning pass.

## Proposed filter contract

1. Keep explicit detectors as the reference for precisely defined geometry.
   Preserve all detections in audit output, including neutral and conflicting
   patterns, rather than silently discarding them through label priority.
2. Evaluate Laya on an ordered window of closed candles, normalized OHLC and
   body/wick proportions, with optional available-at-decision-time context.
   Candidate context includes causal trend and support/resistance measurements.
   Version units, normalization, window length, truncation checks, and field order.
3. Ask separate bounded questions for pattern presence and context compatibility.
   Allow multiple patterns, no pattern, and abstention. Do not force mutually
   exclusive labels for formations that can coexist. A match probability is not
   a profitable-trade probability.
4. Keep recognition, subsequent confirmation, recommendation, and final order
   action distinct. A confirmation candle becomes usable only after it closes;
   never backdate its evidence to the original formation.
5. Register optional advisory versus mandatory eligibility/veto behavior. An
   abstention is not implicitly a veto. Invalid inputs, missing required weights,
   and incompatible schemas fail explicitly rather than silently using TA-Lib.
   Existing position protection and F5/F6 limits remain authoritative.
6. Preserve offline-training/LEAN feature parity. Cache local model outputs only
   with complete input/model/schema keys; require no live model API in replay.
   Log detector, model revision/hash, inputs, pattern outputs, confidence,
   calibration, thresholds, abstention/veto reason, and final action.

Quote activity is a separately named optional input/filter, not centralized FX
traded volume. Compare with and without it; do not require every filter or every
alternative pattern to agree. Review the viewer so a detected bullish formation
is not presented as proof that the final chain placed a BUY order.

## Training and experiment design

Start with a bounded comparison registered before outcomes are inspected:

- Current six-label baseline.
- Expanded explicit-rule catalog with separately testable book-derived context.
- The same baseline plus a specialized Laya pattern/context filter.
- A small numerical sequence classifier as a simpler learned comparator, if the
  data and time budget allow; document deferral rather than claiming it was run.

Build labels from documented rules and independently reviewed real-data windows.
TA-Lib-generated labels are weak supervision or teacher-imitation targets, not
independent evidence of better recognition or trading performance. Include no-hit,
overlapping, contradictory, and near-boundary cases; adjudicate uncertain labels.

Separate training, calibration, and final evaluation chronologically. Prevent
overlapping windows and outcome horizons from crossing split boundaries. Fit
normalization on training data only. Record checkpoint vintage and unknown
pretraining exposure; modern-model historical replay is retrospective and cannot
be presented as an achievable 2015 deployment. Keep consumed-window/search
history visible and use the established experiment-readiness/inference gates.

Evaluate recognition first: per-pattern precision/recall, confusion or multilabel
errors, calibration, abstention coverage, repeatability, and latency. Evaluate
incremental trading value separately under frozen risk/cost/execution settings.
Register acceptance thresholds, baselines, window lengths, and trial budget before
testing; do not select winners from training accuracy or inspect-and-retune loops.

Publish every backtest's full effective filter settings beside its results,
including disabled filters, model/input/code hashes, seeds, thresholds, context
windows, training splits, and all attempted variants. Report losses and no-trade
outcomes. Update the monograph only with verified evidence, clearly separating
planned methods from observed results. No live-account promotion is authorized.

## Acceptance and takeover

Write Gherkin scenarios before implementation for closed-bar causality, future
prefix invariance, warm-up, normalization, missing/invalid inputs, truncation,
multiple/no/conflicting patterns, repeatability, model/schema incompatibility,
veto/abstention behavior, unchanged risk protection, and native/offline parity.
Verify old artifacts retain their original interpretation when the extension is
disabled. Archive exact test commands and expected outputs for the next agent.

Use [progress.md](progress.md) for the unchecked extension checklist. At kickoff,
refresh repository/worktree state, read the relevant book passages, and specify
the rule/label ledger before installing dependencies or starting a training run.
Coordinate combinations with Stories 15/16 and risk review with Story 17.
