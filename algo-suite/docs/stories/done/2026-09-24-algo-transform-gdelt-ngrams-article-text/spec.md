# TD-28 — algo-transform: reconstruct GDELT NGrams article text

**Tool:** `algo-suite/algo-transform/` · **Status:** planned
2026-09-24 · **Blocks:** `algo-score`'s real FinBERT/LM text-sentiment path
(Spec 03 currently runs on event-derived proxies only).
**Depends on:** `algo-download`'s `gdelt_ngrams` raw adapter — landed
2026-09-23 (`algo_download.adapters.gdelt_ngrams`,
`raw/gdelt_ngrams/YYYY/MM/DD/YYYYMMDDHHMMSS.webngrams.json.gz`, one
UTC-minute unit, 0-byte payload = durable MISSING marker). No unmet
dependency.
**Governing contracts:**
[`algo-suite/algo-transform/SPEC.md`](../../../algo-transform/SPEC.md) §4
(slice-3 table, the `parquet/news/gdelt/...` line this closes) and
[`algo-suite/algo-score/SPEC.md`](../../../algo-score/SPEC.md) §2 (news
Parquet input contract: `parquet/news/{source}/...`, article text + publish
ts) — algo-score's contract is already fixed and published; this story's
output must match it, not the other way around.
**Tracked as:** [`technical-debt.md`](../../technical-debt.md) TD-28,
status `ready`.

## 1. Objective

Consume the raw GDELT Web News NGrams 3.0 minute payloads Spec 01 fetched
(`raw/gdelt_ngrams/...`) and reconstruct article text via the open-source
`gdeltnews` package's n-gram reconstruction (~95% similarity, Fronzetti
Colladon & Vestrelli 2026 — a local, deterministic operation over the
already-downloaded bytes, no network fetch, no scraping). Emit the
reconstructed rows as the canonical `parquet/news/gdelt/...` partition that
`algo-score` is already contracted to read. This is the last piece closing
the text-sentiment gap left open by Spec 02
([`2026-09-22-algo-transform-news-events`](../../done/2026-09-22-algo-transform-news-events/spec.md)),
which explicitly deferred it here as TD-28.

## 2. Scope

**In scope:**
- Add `gdeltnews` as an `algo-transform` dependency
  (`algo-suite/algo-transform/pyproject.toml`).
- `decoders/gdelt_ngrams.py` — decode one raw NGrams minute payload into zero
  or more reconstructed-article rows (url, publish timestamp, reconstructed
  text). Same decoder shape as `decoders/gdelt.py` (mirrors its 0-byte →
  empty, corrupt → `DecodeError` naming the slot contract).
- Orchestrator wiring — `algo-transform run --source gdelt_ngrams --month
  YYYY-MM [--from --to] [--rebuild]`, same completeness-gated,
  write-only-when-complete pattern as every other source (§5 of the tool
  SPEC.md): a month writes only when every expected UTC-minute unit is
  present as data or a durable MISSING marker; a genuinely missing minute
  (no data, no marker) or a corrupt minute writes nothing for that month.
- Output: `parquet/news/gdelt/year=YYYY/month=MM/data.parquet` — **not**
  `parquet/events/gdelt/...` (that is Spec 02's separate GDELT-events
  dataset; same provider, two distinct output datasets already established
  by the tool SPEC.md).
- Update `algo-transform/SPEC.md` §4's slice-3 table line and its "No
  `parquet/news/{source}/...` is written" note (§4, now false for GDELT) once
  built. Update `00-PLAN.md` §1 and `technical-debt.md` TD-28 (→ resolved)
  per the constitution's docs-in-sync rule.

**Out of scope:**
- Sentiment scoring, minute-grid bucketing, forward-fill — that is
  `algo-score`'s job (§2/§6 of its SPEC.md), unchanged.
- Deduplicating a URL that recurs across multiple minute files within a
  month — emit one row per occurrence; dedup (if ever needed) is a
  downstream `algo-score` concern, not this decoder's.
- Extending the coverage matrix (`algo-transform coverage`) to the news
  dataset. The matrix already tracks GDELT's *events* coverage; the news
  dataset shares the same raw provider and window, so it adds no new
  training-window information. Log a `technical-debt.md` row if a real gap
  is found once this ships, rather than building unused coverage output
  now.

## 3. Test requirements

Gherkin/pytest-bdd, mirroring `gdelt_decode.feature` / `gdelt_transform.feature`
style exactly (same house pattern, new source):
- Decoder: happy-path reconstruction (url + publish timestamp + text per
  row); 0-byte MISSING marker → zero rows, no error; corrupt payload (not
  gzip, invalid JSON-lines, missing required ngram field) → `DecodeError`
  naming the slot's raw path.
- Orchestrator: complete month → `parquet/news/gdelt` partition written;
  incomplete month (a minute with no data and no durable marker) → nothing
  written, reported `INCOMPLETE`; complete month with one corrupt minute →
  nothing written, reported `CORRUPT`, names the corrupt minute's raw path;
  already-written month → `SKIPPED` unless `--rebuild`; a month where every
  minute is a durable MISSING marker (provider published nothing) → still
  `WRITTEN`, an empty-but-valid partition, not an error (durable-missing is
  complete, not absent).
- CLI: `--source gdelt_ngrams` follows the same global-feed flag contract as
  `--source gdelt` (rejects `--symbol`, requires `--month`/`--from`+`--to`).

## 4. Definition of done

- `algo-transform run --source gdelt_ngrams --month ...` produces
  `parquet/news/gdelt/year=/month=/data.parquet` with reconstructed article
  text, matching `algo-score/SPEC.md` §2's declared input shape exactly (if
  it doesn't, fix the mismatch here — that contract is already fixed).
- `make check`, `make audit` green in `algo-transform`.
- `algo-transform/SPEC.md`, `00-PLAN.md` §1, `technical-debt.md` TD-28 all
  updated to reflect the landed dataset.
