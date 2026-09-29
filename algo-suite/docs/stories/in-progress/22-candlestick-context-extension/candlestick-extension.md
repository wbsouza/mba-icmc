# Story 22: deterministic candlestick catalog and context

Status: planning amendment, September 28, 2026; directory is in-progress for
planning coordination only. Laya is explicitly DEFERRED. No implementation,
training, model download or new experiment is claimed by this document.
See [progress and handoff](progress.md) for ownership and delivery status.

This document is the source/research brief. The consolidated `tlc-spec-driven`
plan owns the implementation requirements and checklist:
[specification](../../../../../.specs/features/candlestick-context/spec.md),
[design](../../../../../.specs/features/candlestick-context/design.md), and
[19 active tasks and five deferred historical IDs](../../../../../.specs/features/candlestick-context/tasks.md).
The user explicitly requested planning only; do not start implementation from
this brief or interpret historical Story 13 results as extension validation.

The [parallel Stories 19/21/22 plan](../../parallel-19-21-22.md) owns shared
contracts, integration leases and handoff gates. Main coordinates Story 19; the
separate Story 21 lane owns confluence; lane C owns Story 22 rules/perception/F3.
No implementation worker or worktree is created by this amendment.

## Purpose

As a researcher, I want to expand deterministic candlestick recognition and
context evaluation so the engine can test formations beyond its current TA-Lib
subset while keeping causal inputs, auditability and frozen legacy behavior.
This remains part of the contest of filter combinations, not a mandatory
standalone book strategy. Completed Story 13 experiments remain historical evidence.

The earlier proposal included Laya as a bounded-decision complement. The user's
current amendment supersedes that scope: Laya and learned comparators are
DEFERRED, with no adapter, model training, cache, token budget or checkpoint-smoke
gate in the active plan. The historical source section below does not reactivate them.

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
instead of silently merging them. Broader formations need causal, reviewable
labels and exact geometry/context definitions before admission to the rule catalog. The presentation is not independent evidence of trading performance.

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

The context discussion around 51:29–52:55 historically motivated the Laya idea.
That proposal is now DEFERRED. The active use of this passage is source review
for deterministic context; it supplies neither model validation nor a labeled
temporal dataset. Cross-reference book, slides and video without counting them
as independent performance evidence. The linked webinar notes retain the earlier
proposal as source-review history; their Laya next steps are superseded here.

### Laya historical archive — DEFERRED, inactive

- [Official model and weights](https://huggingface.co/convaiinnovations/laya).
- [Community explanation supplied by the user](https://huggingface.co/blog/sora-2/laya-ai-model-how-it-works-run-it-locally-and-eval).

The earlier source review recorded the card as describing Apache-2.0 weights,
a ModernBERT-based English checkpoint, text/JSON inputs, typed decisions and
fine-tuning. These are archived findings, not a current upstream verification or
evidence of candle-recognition capability. The earlier proposal called for native
Python interface/license review, pinned weights/runtime/device, bounded schemas,
repeatability tolerances and versioned specialization between experiments.

All of that work is DEFERRED under T17–T21 and CND-20–24. Those IDs remain in
historical tables in the canonical plan; they are not optional tasks, acceptance
criteria or blockers for active rules work. Any future reactivation must revisit
upstream facts and pretraining/historical-replay limitations in a new scope decision.

### Additional comparison sources

- [TA-Lib pattern catalog](https://ta-lib.github.io/ta-lib-python/func_groups/pattern_recognition.html):
  distinguish unsupported patterns from functions we have simply not enabled.
- [EarnForex Candlestick-Pattern](https://github.com/EarnForex/Candlestick-Pattern):
  optional MQL4/5 port candidate suggested by the user. Verify exact source,
  licensing/attribution, indexing, unfinished-bar behavior, and parity before
  adoption. No port or source-logic audit is complete in this planning pass.

## Active deterministic filter contract

1. Preserve every admitted geometry detection, including neutral and conflicting
   patterns, with stable IDs and per-recognizer readiness. Keep the legacy six-label
   selector and its historical interpretation frozen in explicit legacy mode.
2. Evaluate causal trend/level context from closed candles only. Version units,
   normalization, history bounds and field order; reject invalid inputs before
   advancing state. No future candle or outcome label enters an earlier feature.
3. Keep geometry, context and sequence confirmation separately typed. Allow
   multiple/no patterns and abstention. Timestamp a doji/engulfing confirmation
   at the later candle close; expire the candidate if that next bar fails.
4. Keep detection, filter recommendation, entry veto and final action distinct.
   Advisory mode never vetoes; required mode permits entry only for exactly one
   confirmed direction meeting registered context. Existing protection and F5/F6
   continue independently on their original schedule.
5. Preserve offline-row/LEAN parity and fail on incompatible signal contracts.
   Normal F7 model/calibration provenance remains required when F7 is enabled;
   it is not a Laya requirement. Record rule/catalog versions, context, timing,
   policy, abstention/veto reason and final action.
6. Use the shared plan's serialized integration gates: Story 19's fitting changes
   in `f7_meta_learner.py` precede Story 22 T9's encoder; coordinator leases cover
   `training.py`, `signal_contract.py`, `market_signals.py`,
   `decision_recorder.py`, results schema and viewer. One editor owns monograph changes.

Quote activity remains a separately named optional factor, not centralized FX
traded volume. A bullish detected formation is never displayed as proof that the
chain placed a BUY order.

## Rules recognition and experiment design

Register three controlled comparisons before inspecting outcomes:

- Frozen current six-label baseline.
- Expanded deterministic geometry catalog.
- The same expanded catalog with separately testable context and confirmation.

Keep other filters, costs, risk and execution settings fixed. Do not introduce
Story 19 adaptive retraining or Story 21 exits into these cells; combined-feature
fixtures test software compatibility only. A combined study needs a new protocol.

CND-18 and CND-19 remain active without any learned model. Build a recognition
dataset from independently reviewed real-data windows and source definitions.
Keep rule-generated weak labels and ambiguous exclusions distinct from reviewed
truth. Include no-hit, overlapping, contradictory and near-boundary cases with
adjudication records.

Partition development, reserved threshold-calibration and final evaluation
chronologically. Purge overlapping input windows and outcome horizons across
boundaries. Fit any data-derived normalization on development only; calibration
here concerns rule thresholds, not learned probabilities. Keep consumed-window
and search history visible. The already inspected session-2 period remains
exploratory; registration cannot make it an untouched holdout.

T15 validates the dataset, T16 registers the protocol, T22 implements the rules
runner and recognition metrics, T23 publishes evidence, and T24 supplies the
single monograph editor. Register label support, precision/recall, multilabel
errors, readiness/abstention coverage, baselines, windows, thresholds, feasible
dependence-aware statistical inference and trial budget. Report cost-adjusted trading outcomes separately. Negative and no-trade
outcomes remain valid findings.

Publish each attempt's effective filter settings beside results, including
disabled filters, input/code/protocol hashes, ordinary F7 model provenance if
enabled, costs, seeds, thresholds and evaluation splits. Preserve failures and
exclusions. Update the monograph only from verified evidence.

## Acceptance and takeover

The canonical plan contains 19 active tasks: Phase 1 T1–T6; Phase 2 T7–T14;
Phase 3 T15–T16 plus T22–T24 (dataset, protocol, runner, evidence, monograph).
T22 depends on T16. T17–T21 and CND-20–24 remain DEFERRED historical IDs;
no active dependency or gate points to them.

Write Gherkin scenarios with each future implementation task for closed-bar
causality, prefix invariance, warmup, normalization, invalid inputs, multilabel
conflicts, actual confirmation timing, F7/schema compatibility, advisory/veto
semantics, independent protection, split leakage and native/offline parity.
Preserve old-artifact interpretation and historical omissions.

The [shared plan](../../parallel-19-21-22.md) controls kickoff, F7 and shared-file
handoffs, integrated legacy/parity/protection acceptance, separate study registration
and the single monograph editor. Record actual gates and evidence in
[progress.md](progress.md); the canonical tasks own completion checkboxes.
Main owns cross-story link checks and final planning validation. Publication is
blocked by read-only Git metadata and unavailable Forgejo approval; no new branch,
commit or PR is claimed. No implementation or study is authorized by this amendment.
