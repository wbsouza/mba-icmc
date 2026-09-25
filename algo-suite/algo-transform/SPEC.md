# Spec — algo-transform

## 1. Purpose & scope

`algo-transform` is the second pipeline stage: it reads the provider-native **raw
payloads** written by `algo-download` and normalizes them into the **canonical
Parquet store**, partitioned `year=YYYY/month=MM/`. It derives minute QuoteBars
from ticks and (later) builds the data-coverage matrix that drives the
training-window decision.

It does **not** download (that is `algo-download`) and does **not** score
sentiment (that is `algo-score`). Keeping fetch and normalize separate lets
either be re-run independently; re-deriving Parquet never re-hits the network.

This stage exists for **backtest performance**: transform once into the columnar,
compute-ready Parquet that every simulation reuses, so backtests never decode
`.bi5` or re-fetch. Parquet is the canonical reusable layer; `algo-backtest`
further regenerates a RAM-resident LEAN-zip cache from it for the engine's fast
path. Transform once, simulate many.

**Phased delivery** (the price path first, end to end, before breadth):

| Slice | Scope | Output |
|---|---|---|
| 1 (now) | Dukascopy `.bi5` → **validated decoded ticks** | `Tick` value objects + a quarantine path; no Parquet yet |
| 2 | ticks → **minute QuoteBar Parquet** (resample, UTC, completeness-gated idempotency) | `parquet/forex/<pair>/.../minute/` + tick Parquet |
| 3 | coverage matrix, GDELT/GPR event normalization | `parquet/_meta/*`, event datasets |

The rest of this spec defines the contracts for all three; **only slice 1 is
built first**. **Currency-strength deferred** (`technical-debt.md` TD-29): no
F1–F7 filter in `algo-backtest/SPEC.md` §10 consumes it yet — it is a planned
addition to the extended filter set, not part of the baseline chain — so it is
not built until a filter actually reads it (`specs.md` §11.3.2 has no
`currency_strength` "source of input" entry).

## 2. Inputs & outputs

| Direction | Item | Form |
|---|---|---|
| In | raw payloads | `raw/{source}/...` (`.bi5`, `.csv.zip`, `.xls`) |
| Out (slice 2) | minute QuoteBars | `parquet/forex/<pair>/.../minute/year=/month=/data.parquet` |
| Out (slice 2) | ticks (slippage) | `parquet/forex/<pair>/.../tick/year=/month=/data.parquet` |
| Out (slice 3) | GDELT event dataset | `parquet/events/gdelt/year=/month=/data.parquet` (one row per event, verbatim from the Events table — **no article-text column**; `algo-download`'s confirmed GDELT scope, SPEC §7a.1, is Events-table-only) |
| Out (TD-28) | GDELT NGrams news dataset | `parquet/news/gdelt/year=/month=/data.parquet` (one row per reconstructed article — `id`/`text`/`publish_ts`, matching `algo_score.scorers.models.NewsArticle` exactly. Reconstructed via `gdeltnews` from `algo-download`'s `raw/gdelt_ngrams/...` — see §9b) |
| Out (slice 3) | GPR event dataset | `parquet/events/gpr/data.parquet` (whole-window, one row per period, no forward-fill — `algo-score/SPEC.md` §6.2 owns forward-fill) |
| Out (slice 3) | coverage matrix | `parquet/_meta/coverage.parquet` + a thesis figure |

**`parquet/news/{source}/...` is written only for `gdelt_ngrams` (TD-28), not
`gdelt`.** The raw GDELT Events payload (`--source gdelt`, per `algo-download`
§7a.1) carries no article text, only event metadata + `SOURCEURL`; writing an
empty/fabricated `news/` partition from it would violate the fail-fast,
no-fabricated-data rule. The separate `gdelt_ngrams` source (Web News NGrams
3.0, §7a.3) is the actual text source, reconstructed by `gdeltnews` into real
article text — that is what populates `parquet/news/gdelt/...`. `sentiment/`
remains `algo-score`'s output, not this tool's, unchanged from the prior
contract.

(The `tick/` vs `minute/` resolution segment under the price path lives in
`algo-core` `layout`; slice 2 writes the `minute/` partition. The Dukascopy raw
path contract — `TickFile` / `dukascopy_raw_path` / `parse_dukascopy_raw_path` —
also lives in `algo-core`, shared by the downloader that writes it and the reader
that consumes it.)

## 3. The Dukascopy `.bi5` decoder (slice 1)

The raw layer stays as Dukascopy `.bi5` (LZMA-compressed binary ticks: a compact,
faithful archive). `algo-transform` decodes it with the Python standard library
(`lzma` + `struct`); the format was **confirmed against the real feed** (see
algo-download SPEC §7a): an LZMA stream of 20-byte big-endian `>IIIff` records:

```
ms_offset (uint32, ms since the file's hour) | ask (uint32, points) |
bid (uint32, points) | ask_volume (float32) | bid_volume (float32)
```

No third-party Dukascopy client is used: such libraries return decoded
DataFrames, which would pull normalization back into a dependency and blur the
raw-only boundary the download stage holds.

**Three-state input handling (first-class).** A raw hour file is one of:

1. **non-empty** → LZMA-decompress, unpack 20-byte records, decode → ticks;
2. **0-byte** → the durable **MISSING marker** `algo-download` persists for a
   provider no-data hour (weekend/holiday/gap); decode yields **zero ticks**, and
   it is **not** an error;
3. **decode error** (LZMA failure, or byte length not a multiple of 20) →
   **corrupt**: the file is **quarantined** and reported; the run continues.

This distinction is non-negotiable: without it a known gap (state 2) would be
mistaken for corruption (state 3).

**Price scaling — `price_increment`, not `unit_size`.** Raw `ask`/`bid` are
integer points; the real price is `points × price_increment`, where
`price_increment = 10^(-digits)` (EUR/USD `digits=5` → `1e-5`; USD/JPY `digits=3`
→ `1e-3`). This is **not** `unit_size`, which is the **pip** (`1e-4` / `1e-2`).
`algo-core` `Instrument` gains a `price_increment` property so the decoder never
hard-codes a factor and the pip/increment trap is closed.

**Timestamp.** A tick's UTC time is the file's hour (from the raw path,
`parse_raw_path`) plus `ms_offset`. All timestamps are UTC.

### 3.1 Decoded `Tick` contract (slice 1 output)

A frozen value object (in `algo-core`, alongside `QuoteBar`):

| Field | Type | Notes |
|---|---|---|
| `timestamp` | datetime (UTC) | hour base + `ms_offset` |
| `bid` | float | `bid_points × price_increment` |
| `ask` | float | `ask_points × price_increment` |
| `bid_volume` | float | provider tick volume |
| `ask_volume` | float | provider tick volume |

`decode_bi5(payload: bytes, hour: TickFile, price_increment: float) -> list[Tick]`:
empty payload → `[]` (no-data); corrupt payload → raises `DecodeError` (caller
quarantines).

## 4. Libraries

- **stdlib `lzma` + `struct`** — the bi5 decoder (slice 1).
- **polars** — tick→minute resampling on 5–10 GB of ticks (slice 2; lazy,
  memory-efficient).
- **pyarrow** — Parquet write (zstd), schema enforcement, partitioning (slice 2).
- **duckdb** — coverage-matrix aggregation (slice 3).
- **algo-core** — `Instrument` (`digits`, `price_increment`), `Tick`/`QuoteBar`,
  canonical layout, `Repository`, logging.

```
algo_transform/
├── cli.py                # algo-transform --source ... [--symbol] [--month/range]
├── decoders/
│   ├── bi5.py            # slice 1: .bi5 → list[Tick] (stdlib lzma+struct, >IIIff)
│   ├── gdelt.py          # slice 3
│   └── gpr.py            # slice 3
├── resample.py           # slice 2: ticks → minute QuoteBar (UTC)
├── writer.py             # slice 2: canonical Parquet writer via Repository
└── coverage.py           # slice 3: months × sources coverage matrix + figure
```

## 5. CLI surface

```
algo-transform run --source dukascopy --symbol EURUSD --month 2020-01
             [--from --to] [--timeframe m1|m5|m15|m30|h1|h4|d1] [--rebuild]
algo-transform run --source gdelt --month 2020-01 [--from --to] [--rebuild]
algo-transform run --source gdelt_ngrams --month 2020-01 [--from --to] [--rebuild]
algo-transform run --source gpr [--rebuild]
algo-transform coverage
```

**Per-source flag applicability** (mirrors `algo-download`'s own table, §5):

| Source | `--symbol` | `--month`/`--from`/`--to` | Notes |
|---|---|---|---|
| `dukascopy` | required | one of them required | per-instrument, date-partitioned |
| `gdelt` | **rejected** | one of them required | global feed, date-partitioned (§6.4) |
| `gdelt_ngrams` | **rejected** | one of them required | global feed, date-partitioned (TD-28), same contract as `gdelt` |
| `gpr` | **rejected** | **rejected** | whole-window, single output file (§6.5) |

`gdelt`/`gpr` rejecting `--symbol` and `gpr` rejecting the date flags fail
fast naming the rejected flag (`cli-gdelt-01`, `cli-gpr-01`). `coverage` takes
no flags: it scans the data root for every ingested source's completeness and
prints the selected training window (§6.2).

- `--timeframe` (default `m1`) chooses the bar frequency from the standard Forex
  set (`Timeframe`: m1, m5, m15, m30, h1, h4, d1); ticks are aggregated directly
  to that bar (floor anchored at midnight UTC, every supported timeframe divides a
  day), written under the matching `parquet/forex/<pair>/<timeframe>/` partition.
  The strategy is multi-timeframe: each filter reads its own timeframe, so the
  transform pre-materializes every timeframe a strategy needs ahead of the
  simulation sweep (a missing one is computed once on demand and reused).

- **Completeness-gated, write-only-when-complete.** A month is written **only**
  when its raw month is **complete** — every expected hour present on disk as data
  **or** a 0-byte MISSING marker (no absent/FAILED hour). An incomplete month
  yields status `INCOMPLETE` and **writes nothing** (so a half-downloaded month is
  never frozen as a partial partition); re-run after the download finishes.
  Because a partition is only ever written from a complete month, an existing
  partition is **skipped** (`SKIPPED`) unless `--rebuild`. Expected-hour
  enumeration lives in one place (the reader) so completeness and loading cannot
  diverge.
- **Corrupt is fatal for the partition, not silently partial.** If any raw hour
  fails to decode, the reader quarantines it (logged) and the month is reported
  `CORRUPT` with **nothing written** — a truncated month is never produced. The
  fix is to re-download the quarantined hours and re-run.
- Exit code: `0` for `WRITTEN`/`SKIPPED`; non-zero for `INCOMPLETE` (input not
  ready) or `CORRUPT` (a raw hour failed to decode). Either way, nothing is
  written.

## 6. Data contracts

### 6.1 QuoteBar (slice 2; `parquet/forex/<pair>/<timeframe>/`)

Bars are produced at the chosen `--timeframe` (`Timeframe`: m1/m5/m15/m30/h1/h4/d1),
ticks aggregated directly to the bar boundary. Canonical price is
**bid OHLC + ask OHLC + tick count** (LEAN-native, lossless; mid and spread are
derived downstream, never stored ambiguously):

| Column | Type | Notes |
|---|---|---|
| `timestamp` | datetime (UTC) | minute open (start of the minute) |
| `bid_open/bid_high/bid_low/bid_close` | float | rounded to `Instrument.digits` |
| `ask_open/ask_high/ask_low/ask_close` | float | rounded to `Instrument.digits` |
| `tick_count` | int | ticks in the minute (the FX activity proxy) |

Partition: `.../minute/year=YYYY/month=MM/`. No `mid`/`configurable` column: a
consumer that wants mid computes `(bid_close + ask_close) / 2` on read.

### 6.2 Coverage matrix (slice 3; `parquet/_meta/coverage.parquet`)

Per `(month, source)`, with **completeness metrics for price sources** (not a bare
`present` bool, which cannot tell a one-hour month from a full one):

| Column | Type | Notes |
|---|---|---|
| `month` | date | YYYY-MM |
| `source` | string | dukascopy, yfinance, gdelt, gpr, … |
| `units_expected` | int | hours in month for price; 1 for a monthly index |
| `units_present` | int | hours present as data (MISSING markers excluded) |
| `coverage_ratio` | float | `units_present / units_expected` |
| `resolution` | string | `minute`/`tick` (dukascopy) or `daily` (yfinance) |
| `backtestable` | bool | false for daily-only price months and for low-coverage months |

`backtestable` is therefore auditable, not binary-by-accident. Drives the
training-window rule (MVP: largest contiguous span where GDELT covers ≥ 80 % of
months; tightened to ≥ 2 corpora later). Published as a thesis figure.

**Window-selection tie-break.** When two or more contiguous ≥80%-coverage spans
tie for longest, the rule prefers the **later** span — a more recent window is
more representative of the current market regime. Ties are never resolved by
scan order (an implementation accident); the selected window is always printed
by `algo-transform coverage`, never silently applied (Chapter 4 cites it).

**Price fallback.** A month covered only by the `yfinance` daily fallback is
written at `resolution=daily`, `backtestable=false`, and **no** minute bars are
synthesised from it. The minute backtest reads only `backtestable=true` months;
the fallback never injects fabricated intrabar structure.

### 6.3 Currency strength by volume (slice 3; `parquet/_meta/currency_strength.parquet`)

Cross-pair daily relative tick-volume per currency (FX is OTC, no consolidated
true volume; tick-volume is the activity proxy). Universe-aware; strengthens as
the pair universe grows. Computed here (the per-pair LEAN algorithm cannot see
other pairs); consumed by `algo-backtest`'s volume filter.

| Column | Type | Notes |
|---|---|---|
| `date` | date | trading day |
| `currency` | string | EUR / USD / JPY / … |
| `rel_strength` | float | share of total tick-volume that day |
| `rank` | int | 1 = most active currency |

**Deferred** — `technical-debt.md` TD-29. No F1–F7 filter consumes this yet;
not built until the extended filter set adds the volume/strength context
filter (`algo-backtest/SPEC.md` §10).

### 6.4 GDELT event rows (slice 3; `parquet/events/gdelt/year=/month=/data.parquet`)

One row per event, verbatim from the raw Events-table CSV (`algo-download`
SPEC §7a.1) — no aggregation, no normalization, no article text:

| Column | Type | Notes |
|---|---|---|
| `global_event_id` | int | GDELT's own event id |
| `event_date` | date | UTC, from the slot the event was published in |
| `event_code` | string | CAMEO event code |
| `goldstein_scale` | float | event impact, GDELT's own scale |
| `avg_tone` | float | GDELT's own document-tone score (not FinBERT — an
  event-derived proxy; `algo-score` labels features from this column as such,
  never as "sentiment") |
| `actor1_code` / `actor2_code` | string | CAMEO actor codes |
| `num_mentions` / `num_sources` / `num_articles` | int | raw counts, for
  `algo-score`'s `event_intensity` aggregation (`algo-score/SPEC.md` §6.2) |
| `source_url` | string | carried through unmodified; the join key a future
  text-fetch adapter (`technical-debt.md` TD-28) would use |

### 6.5 GPR index rows (slice 3; `parquet/events/gpr/data.parquet`)

Whole-window, no `year=/month=` partitioning (one raw file in, one output
file out). One row per period in the raw file, **verbatim** — no forward-fill,
no assumed resolution:

| Column | Type | Notes |
|---|---|---|
| `period` | date | whatever resolution the raw file actually uses (monthly
  vs daily is **unconfirmed** — `algo-download` SPEC §7a.2 confirmed only the
  URL and file format, not the internal column layout; read the real file at
  implementation time rather than assume) |
| `gpr` | float | the headline Caldara–Iacoviello GPR index value |

Only the headline index is decoded — sub-indices (`GPR_ACT`, `GPR_THREAT`,
`GPR_COUNTRY`, …) have no current consumer (`algo-score/SPEC.md` §6.2 wants a
single `gpr` float column); if a later spec needs them, add as a new column,
never a guess now.

## 7. Error handling

- **0-byte raw file** → no-data marker → zero ticks for that hour (not an error).
- **Corrupt/truncated `.bi5`** (LZMA error or length not ÷ 20) → the reader keeps
  scanning the remaining hours and collects every quarantined file (logged with
  its path); the orchestrator then refuses to write the month (`CORRUPT`,
  non-zero) rather than emit a partial partition.
- DST / timezone → all timestamps UTC; resampling (slice 2) is DST-safe.
- Minutes with no ticks → **no bar emitted** (gap), never forward-filled here.
- Duplicate ticks → de-duplicated by `(timestamp, bid, ask)` (slice 2).
- Schema drift in a source → fail the partition with a clear schema-mismatch error.
- **GDELT 0-byte MISSING marker** → zero event rows for that slot (not an
  error) — same three-state contract as Dukascopy (§3), mirrored per slot
  instead of per hour.
- **GDELT corrupt slot** (not a valid zip, or a CSV row with the wrong column
  count) → quarantined, month reported `CORRUPT`, nothing written.
- **GPR empty or malformed raw file** → `DecodeError` naming the file. GPR's
  raw fetch is one whole-window unit (`algo-download` §7a.2, no per-period
  MISSING marker), so an empty payload here means the fetch never completed,
  not a "no data this period" gap — always an error, never zero rows.

## 8. Test scenarios (Gherkin)

Canonical, mutation-tested source — not duplicated here to avoid drift:
`tests/features/gdelt_decode.feature`, `tests/features/gpr_decode.feature`
(pure decoders, slice-1-style), `tests/features/gdelt_transform.feature`,
`tests/features/gpr_transform.feature` (completeness-gated orchestration),
`tests/features/coverage.feature` (the coverage matrix + training-window
rule, pure functions), `tests/features/cli.feature` scenarios `cli-gdelt-*`,
`cli-gpr-*`, `cli-coverage-*` (end-to-end CLI surface).

## 8a. Test scenarios — slice 1 (decoder)

The decoder is a binary codec, so these behaviors are verified by **unit tests**
(`tests/unit/test_bi5.py`, synthetic LZMA payloads of known `>IIIff` records,
offline) per the suite's unit/property-test allowance; the Gherkin below
documents the contract. Higher-level file→bars behavior gets `.feature` scenarios
in slice 2.

```gherkin
Feature: Decode Dukascopy .bi5 into validated ticks
  Scenario: A real-format payload decodes to scaled UTC ticks
    Given an LZMA bi5 payload of known >IIIff records for EURUSD 2020-01-02 14h
    When I decode it with the EURUSD price increment
    Then each tick timestamp is the hour base plus its ms offset, in UTC
    And each bid/ask equals points times 1e-5 (price_increment, not the pip)
    And the tick count equals the number of records

  Scenario: USDJPY uses its own increment
    When I decode a USDJPY payload
    Then prices are points times 1e-3, not 1e-5 and not the pip 1e-2

  Scenario: A 0-byte MISSING marker decodes to zero ticks, not an error
    Given an empty raw payload (the download no-data marker)
    When I decode it
    Then it yields zero ticks
    And no error is raised

  Scenario: A corrupt payload is a decode error (to be quarantined)
    Given a non-empty payload that is not valid LZMA / not a multiple of 20 bytes
    When I decode it
    Then a DecodeError is raised
```

(Resample/idempotency/coverage scenarios land with slices 2 and 3.)

## 9. Acceptance criteria (slice 1)

- A real `.bi5` payload decodes to ticks whose prices match the validated feed
  (EUR/USD ≈ 1.1197 for 2020-01-02 14h) using `price_increment = 10^-digits`.
- The three input states (data / 0-byte no-data / corrupt) are handled distinctly:
  ticks / empty / `DecodeError`.
- `Instrument.price_increment` exists and the decoder uses it (never `unit_size`).
- BDD + unit tests; ruff + mypy-strict + coverage gate green.

## 9a. Acceptance criteria (slice 3 — GDELT/GPR/coverage, Spec 02)

- `algo-transform run --source gdelt --month ...` and `--source gpr` produce
  `parquet/events/gdelt/...` and `parquet/events/gpr/data.parquet` respectively
  — no `parquet/news/gdelt/...` (no article text in the raw source, §2).
- The three-state GDELT contract (data / MISSING / corrupt) is handled per
  slot, mirroring Dukascopy's per-hour contract.
- `algo-transform coverage` computes the coverage matrix and prints the
  selected training window (traceable to a command + run, `experiments.md` §5),
  writing both `parquet/_meta/coverage.parquet` and a vector-PDF figure.
- Currency-strength stays unbuilt (§6.3, TD-29) — no filter consumes it yet.

## 9b. Acceptance criteria (TD-28 — GDELT NGrams article text)

- `algo-transform run --source gdelt_ngrams --month ...` produces
  `parquet/news/gdelt/year=/month=/data.parquet` with real reconstructed article
  text (`id`/`text`/`publish_ts`, matching `algo_score.scorers.models.NewsArticle`
  exactly) — not `parquet/events/gdelt/...` (Spec 02's separate dataset).
- Reconstruction is `gdeltnews`'s job (n-gram-based text recovery over the raw
  `.webngrams.json.gz` bytes `algo-download` already fetched); this tool only
  adapts its file-in/file-out API to the project's in-memory decoder contract.
- The three-state contract (data / MISSING / corrupt) is handled per UTC minute,
  mirroring the other sources' per-slot/per-hour contract. Verified against the
  real library, not assumed: only a payload that is not valid gzip is a decode
  error; a malformed JSON line or a line missing a required field is silently
  skipped by `gdeltnews` itself, yielding zero rows for that minute, not an error.
- A month where every minute is a durable MISSING marker still writes an
  empty-but-valid partition (complete information, not an error).
- BDD tests for every scenario above; ruff + mypy-strict + coverage gate green.

## 10. Open items

- Resolved (slices 1–2): bi5 decoder (3-state, `price_increment` scaling); `Tick`
  + `QuoteBar` value objects (bid/ask OHLC); resolution segment + shared raw-path
  contract in `algo-core`; `resample_minute`; completeness-gated, write-only-when-
  complete orchestrator (incomplete → `INCOMPLETE`, corrupt → `CORRUPT`, both write
  nothing and exit non-zero); runnable CLI `run`.
- Slice 3 (Spec 02, built 2026-09-23): GDELT/GPR event decoders + coverage
  matrix + training-window rule — implemented and covered by Gherkin (§8).
  Deferred within slice 3: tick Parquet write (slippage), currency-strength
  (TD-29). GDELT text-sentiment source gap tracked as TD-28, not this tool's
  job to close (a new `algo-download` unit kind).
- Resample is pure-Python over a tick list; a `polars` path is an optimization if
  a full-month load proves slow (the canonical correctness lives in the tests).
- The `parquet → LEAN-zip` conversion lives in `algo-backtest` (LEAN-specific).
