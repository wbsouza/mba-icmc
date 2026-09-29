# Spec 03 — algo-score: sentiment + event features (build the whole tool)

**Tool:** `algo-suite/algo-score/` · **Status:** not started (only a `cli.py`
stub exists — zero scorers, zero events, zero bucketing) · **Blocks:** Spec 04
**Depends on:** Spec 02 landed — real `parquet/news/gdelt/...` and
`parquet/events/{gdelt,gpr}/...` on disk with the schema Spec 02 committed to.
**Governing contract:** [`algo-suite/algo-score/SPEC.md`](../../../../algo-score/SPEC.md) — this is the most
complete and detailed tool spec in the repo (data contracts, sequence/state
diagrams, 20+ Gherkin scenarios already drafted, known limitations already
documented in §8.1). **Read it in full before writing any code; it is
authoritative over anything summarized here.**

## 1. Objective

Build `algo-score` from scratch per its existing SPEC.md: two sentiment scorers
(FinBERT-class transformer + Loughran–McDonald dictionary baseline) and event
features (GDELT aggregate + GPR), all bucketed to the minute grid, all cached
via `algo-core`'s `Cache` port, all keyed for reproducibility (`model_version`).

This is the single largest remaining engineering item and the true critical
path per [`PRD.md`](../../../../PRD.md) §6 gantt (`crit, b1, after a1b, 16d` — 16 days budgeted,
the longest of any remaining task). Do not shortcut the caching/determinism
requirements to save time — a non-reproducible sentiment score breaks the
Chapter 4 reproducibility claim ([`experiments.md`](../../../experiments.md) §5) for every downstream
number.

## 2. Build order (within this spec, to get a demoable slice early)

The tool SPEC.md doesn't mandate an internal sequence, but building
bottom-up de-risks the expensive part last:

1. **`scorers/base.py`** — the `Scorer` ABC and `ScoreResult` value object
   (polarity, confidence). Pure interface, no model.
2. **`scorers/lexicon.py`** (Loughran–McDonald) first, not FinBERT first. It's
   deterministic, no GPU, no model download, no cache-warming step — it proves
   the bucketing/attribution/caching machinery end-to-end on a cheap scorer
   before paying for transformer inference. The tool SPEC.md explicitly frames
   LM as "the fallback" and "even coarser" than FinBERT (§8.1) but that's an
   accuracy statement, not a build-order statement — build it first anyway.
3. **`events/gpr.py`** and **`events/gdelt.py`** — the event-feature side,
   independent of the sentiment side, can be built in parallel with step 2 by
   a second agent if concurrency is available.
4. **`bucket.py`** — per-article scores → minute grid via DuckDB, per the
   tool SPEC.md §3 sequence diagram. This is the piece both sentiment and
   event features route through; get it right once, both scorers use it.
5. **Per-currency attribution** (`§6.1`/the "Feature: Per-currency
   attribution" Gherkin block in the tool SPEC.md) — the ECB→EUR/Fed→USD/
   BOJ→JPY routing rule, plus the ambiguous multi-currency case. This is
   FX-domain logic worth its own focused implementation pass and its own
   review — it's the piece most likely to have subtle bugs (a headline
   mentioning both the ECB and the Fed, opposite tone, must not be forced
   to one side — tool SPEC.md §7 "Multi-currency opposite-tone headline").
6. **`scorers/finbert.py`** last — model download (`models-fetch` CLI
   command first, per tool SPEC.md §5), batched inference, cache-checked
   before every inference call, fixed seed. This is the expensive,
   GPU-or-slow-CPU part; do not let it block steps 1–5 from being
   demoable and tested.

## 3. Non-negotiables from the tool SPEC.md (repeated here because they're
easy to accidentally violate under time pressure)

- **Determinism.** Same input + same `model_version` ⇒ identical output,
  always. If any inference path is non-deterministic (e.g. an unpinned
  `torch` nondeterministic op), the tool SPEC.md §7 says **fail loudly**, not
  silently accept drift. This is the project's fail-fast rule applied
  specifically to model inference.
- **ABSTAIN, not a crash, not a fabricated score.** Empty text, non-English
  text, an unattributable article, an empty minute bucket — all of these
  produce an explicit ABSTAIN / `n_articles=0` / dropped-with-report outcome.
  None of them raise, and none of them silently score as neutral (0.0) —
  ABSTAIN is a distinct signal the downstream filter chain (Spec 04, filter
  F4) reads as "no opinion this bar," per [`specs.md`](../../../../specs.md) §11.3.1's
  VETO-vs-ABSTAIN distinction. Do not collapse ABSTAIN into a numeric zero.
- **Cache correctness over cache speed.** A `model_version` bump must
  re-score, never silently mix versions in one output partition (tool
  SPEC.md §7). Get the cache key right (`article_id`, `model`, `version`)
  before optimizing for hit rate.
- **No random-init fallback.** Missing model weights is a hard stop with a
  `models-fetch` hint — never silently proceed with an untrained model
  (tool SPEC.md §7). This one is easy to get wrong if someone adds a
  try/except around model loading "to be safe" — don't; that's exactly the
  silent-fallback pattern the project's CLAUDE.md fail-fast rule forbids.

## 4. Test requirements

The tool SPEC.md §8 already contains ~20 Gherkin scenarios covering exactly
this tool's behavior (happy path, empty-batch-abstains, deterministic
scoring, cache-hit/cache-miss/version-bump, non-English-abstains, ambiguous
multi-currency, per-currency attribution outline, USD-macro-feeds-both-pairs,
missing-weights-hint, GPR-forward-fill, LM-runs-alongside-FinBERT). **Use
those scenarios as the `.feature` files directly** (adapt file names/paths to
the actual repo layout) rather than re-deriving new ones — they're already
correct and already reviewed into the spec. Add steps under
`tests/steps/test_<name>.py`, fixtures/mocks for model inference (do not
require a real FinBERT download in the offline gate — mock the scorer
interface for BDD, reserve a real-model smoke test as `@network` or an
equivalent opt-in marker if the model download itself needs validating once).

## 5. Definition of done

- Both scorers (`finbert`, `lm`) run over a real month of Spec-02-produced
  GDELT news Parquet and produce minute-bucketed sentiment for EUR/USD/JPY,
  matching the acceptance criteria in tool SPEC.md §9.
- Event features (GDELT event-intensity, GPR forward-filled) built and
  aligned to price minutes.
- Per-pair derived sentiment (`{scorer}_symbol/...`) computed and written —
  this is the actual feature the hybrid strategy (Spec 04) consumes.
- All ~20 Gherkin scenarios from the tool SPEC.md green.
- `make check`, `make audit` green.
- Tool SPEC.md §10 "Open items" resolved or explicitly deferred to
  [`technical-debt.md`](../../../technical-debt.md) with a real trigger (e.g. onnxruntime-vs-torch,
  FinBERT-variant-choice — these are legitimate "decide after inventory"
  items, not excuses to skip).
- [`00-PLAN.md`](../../00-PLAN.md) §1 updated; Spec 04 unblocked with real sentiment/event
  Parquet on disk for at least one month, ideally the full window if time
  allows within the 16-day budget.
