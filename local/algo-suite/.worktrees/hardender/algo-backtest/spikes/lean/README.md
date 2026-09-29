# LEAN integration spike (throwaway)

> **SUPERSEDED (2026-05-25).** This spike is kept only as a de-risking log. The real
> work now lives in committed code: the materializer `../../src/algo_backtest/leandata.py`
> and the testcontainers suite `../../tests/integration/`. **Correction:** the spike's
> "data tz = America/New_York, **END**-indexed" inference was **wrong**. The
> testcontainers round-trip (`tests/integration/test_timezone_roundtrip.py`, summer +
> winter) proved LEAN stores forex (OANDA) minute data in **UTC**, **START**-indexed;
> the −4h/−8h offsets seen below were the NY exchange-tz stamping of `QuoteBar.EndTime`
> plus an end-vs-start slip, not the data tz. Trust `SPEC.md` §3.1, not the notes below.

**Goal:** prove the riskiest unknown of the backtest stage end to end — that one
day of our canonical minute Parquet becomes one day the LEAN engine reads
correctly (timestamps + OHLC + bar count match) and that a trivial order
executes — **before** building `algo-backtest` for real.

Exploratory and disposable. Findings become the basis of the real `parquet →
lean-data` materializer; nothing here is production code. The on-disk LEAN path is
**not** invented here: it is `algo_core.layout.lean_data_dir_for(...)` (already
lowercases the symbol) — the spike confirms LEAN's real convention against it.

## Pinned versions (Task 0)

| Tool | Version | How |
|---|---|---|
| `lean` CLI | **1.0.225** | `uvx --from lean lean ...` (ephemeral, cached) |
| Docker | **28.0.1** | host daemon reachable |
| `quantconnect/lean` image | **`17748`** = `latest` @ 2026-05-22 (same digests on Hub); **linux/amd64** digest `a39a2db90538` (13.08 GB compressed; arm64 is a different, 4.72 GB image) | pin the **numbered** tag, not `latest` (mutable): `lean config set engine-image quantconnect/lean:17748` (set ✓) |

## De-risking order (verify one thing per step; stop at the first red)

- [x] **Task 0 — pin versions.** lean CLI 1.0.225; Docker image **pinned to
      `quantconnect/lean:17748`** (numbered, immutable — `latest` floats). Enforce
      with `lean config set engine-image quantconnect/lean:17748` (and record the
      digest after the pull for belt-and-suspenders). Reproducibility: the thesis
      §3.10 backtest engine is this exact build.
- [x] **Task 1 — LEAN runs locally.** `lean init` + run a **bundled** sample
      algorithm. Proof: `lean backtest` completes via local Docker. Isolates env
      risk: Docker, CLI bootstrap/auth, local project wiring (not "license").
- [x] **Task 2a — discover the real lean-data forex-minute format.** Done from the
      **public open-source LEAN repo** (`Data/forex/`, no account needed); see the
      Evidence table + Log. Confirms our design (market oanda, lowercase symbol,
      bid+ask OHLC, gaps allowed). Remaining nuance (timezone of the file-date) is
      a 2b question.
- [x] **Task 2b — temporal semantics on a known day (THEIR data).** Done — the
      auto-proving algo measured (not assumed) the convention on 2014-05-07:
      - algorithm/data **timezone = `America/New_York`** (LEAN default for forex;
        no UTC→NY 4h shift on the bars → the file is read on the NY clock);
      - `bar.Time` = bar **start**, `bar.EndTime` = start + 1 min;
      - the CSV `ms_since_midnight` = the bar **END** time → `ms=0` is the bar
        `[23:59 of D-1, 00:00 of D)`; a day-D file holds bars **ending** in D.
      This is the central timezone risk, now pinned. Consequence below (Task 3a).
- [x] **Task 3a — materialize 1 day of OUR minute Parquet → 1 LEAN zip (artifact
      only).** Source: `parquet/forex/EURUSD/m1/year=YYYY/month=MM/data.parquet`
      (from `algo-transform`). Write **both bid and ask OHLC** (the LEAN
      minute-quote format requires both; our `QuoteBar` carries both). Path suffix
      from `lean_data_dir_for(...)` (no parallel convention). `materialize.py`
      fail-fasts on bars off-day or not minute-aligned. Proof: file at the exact
      expected path, structure matching 2a — verified byte-identical offline.
- [ ] **Task 3b — LEAN reads OUR day.** Minimal algorithm prints bar count
      (== the expected count for the day), first/last timestamp, and the OHLC of one
      **known** bar. Proof: our data is consumed identically to theirs.
- [ ] **Task 4 — trivial trade.** QCAlgorithm: `SetHoldings("EURUSD", 0.01)` at an
      early bar, liquidate later. Proof: one order event + one fill + a closed trade
      with non-zero PnL in the `orders`/`trades` output.

## Why this granularity (each boundary isolates one failure mode)

- **Task 0** — a behavior change between lean-CLI / image versions never
  masquerades as our bug. Cheapest insurance.
- **Task 1 alone (environment)** — "does LEAN even run here" before any data.
- **2a vs 2b (format vs semantics)** — the treacherous risk is **not** zip/CSV
  shape; it is timezone, naming and market mapping. 2a discovers the physical
  format; 2b proves the reading behavior (bar count + first/last). Apart, so a
  timezone bug can't hide as a format bug.
- **3a vs 3b (artifact vs consumption)** — 3a proves the conversion (right path,
  content like 2a) without LEAN; 3b proves the engine consumes it. A failure is
  localisable: bad file vs LEAN can't read.
- **Task 4** — execution/output is distinct from ingestion; any failure here is
  in the order path, not the data.

## Risks treated explicitly

- **Timezone** — the central risk; an explicit measured proof in 2b/3b (bar count
  + first/last), never implicit.
- **Symbol casing & market** — **LEAN decides**, not us: 2a reveals the real
  convention; the materializer conforms (our `lean_data_dir_for` lowercases and
  uses `oanda` — confirm both in 2a, correct if wrong).
- **Quote side** — the LEAN forex-minute format is a **quote** bar with **both**
  bid and ask OHLC (confirmed in 2a); we write both (our `QuoteBar` has both). FX
  volume columns are `0`.
- **Gaps** — confirm early that missing minutes do not break the replay.

## Out of scope for the spike (do NOT pull in yet)

`/dev/shm` tmpfs acceleration · the real read-through cache · strategy
`config.yaml` / config generator · a "real" baseline before the trivial trade.

## Known LEAN pitfalls

- Docker daemon must be running before `lean backtest`.
- `lean init` creates a workspace dir; run spike commands from **inside** it.
- The first `lean backtest` pulls the `quantconnect/lean` image, which is **~10.6
  GB** (much larger than typical) — budget 10–20 min on first run; cached after.
- The algorithm runs inside LEAN's own container (its bundled Python), not the uv
  workspace; the materializer (our Python) only writes files LEAN then reads.
- On failure, LEAN logs go to the container — `docker logs` / the CLI output.

## Success criteria (spike done when, with evidence)

LEAN runs locally · we know the real LEAN-native format · one day of our Parquet
→ one day LEAN reads · timestamps, OHLC **and bar count** match · a trivial order
executes.

**Evidence format:** each task appends a dated entry to the Log below with the
terminal output pasted inline (2a: directory tree + CSV excerpt; 2b/3b: the
algorithm's `Debug()` output). Everything in this one file. Fill the table:

| Task | Finding | ✓ |
|---|---|---|
| 2a | path `forex/oanda/minute/<sym-lower>/<YYYYMMDD>_quote.zip`; market **oanda**, symbol **lowercase** (matches `lean_data_dir_for`) | ✓ |
| 2a | inner `<YYYYMMDD>_<sym>_minute_quote.csv`; comma, **no header**; cols `ms_since_midnight, bidO,bidH,bidL,bidC, bidVol, askO,askH,askL,askC, askVol`; price **decimal** (5dp EURUSD), **no scaling**; FX volume `0`; gaps allowed (missing minutes, no fill) | ✓ |
| 2b | **measured**: tz=`America/New_York`; `bar.Time`=start, `EndTime`=+1min; CSV `ms`= bar **END** (ms=0 ⇒ `[23:59 D-1, 00:00 D)`); day-D file = bars ending in D | ✓ |
| 3a | **END-indexing confirmed** (safe to port): `materialize.py` indexes by bar **END** (`ms=end-since-midnight`, end=start+1min), groups by end-day; self-test: bar starting 23:59 → ms 0 in the next day's file (matches sample). **TZ NOT confirmed**: it writes in the spike's hard-coded NY tz, which 3b showed is wrong — tz is unresolved. | ◑ |
| 3b | LEAN reads our day: bar count + OHLC of a known bar match | ☐ |
| 4 | one closed trade with non-zero PnL | ☐ |

## Post-spike (after success)

- [ ] Move findings to `docs/lean-integration.md`; delete `spikes/lean/`.
- [ ] Implement the real `parquet → lean-data` materializer (in `algo-backtest`),
      porting `materialize.py`'s confirmed END-indexing + file-day semantics ONLY; the timezone handling must be re-proved (config-driven + winter/summer testcontainers tests), not ported.
- [ ] The **automated** LEAN integration test uses **testcontainers** (pinned
      `quantconnect/lean:17748` via a `DockerContainer` fixture; mount lean-data +
      algorithm, run the backtest, assert on the output) — not the `lean` CLI,
      which the spike used only for exploration. Mirrors `wise-cache` /
      `odoo-oikofy-addons`.
- [ ] Port the validated format understanding to the `algo-backtest` data reader.

## Log

- 2026-05-25: lean CLI 1.0.225 (uvx) + Docker 28.0.1 daemon OK.
  Image tag: _record after Task 1_.
- 2026-05-25 (Task 1, blocked): `lean init` requires QuantConnect credentials
  (user id + API token) to fetch its sample-data bundle — it aborts without them.
  Compute is fully local (public Docker image, no auth); only the CLI's *data
  fetch* wanted the account. We bring our own data (Dukascopy), so the account is
  not needed for the spike.
- 2026-05-25 (Task 2a, done — no account): fetched the format from the **public**
  LEAN repo:
  `git clone --depth 1 --filter=blob:none --sparse https://github.com/QuantConnect/Lean`
  then `git sparse-checkout set Data/forex`. Sample `oanda/minute/eurusd`:
  ```
  forex/oanda/minute/eurusd/20140501_quote.zip
   → 20140501_eurusd_minute_quote.csv  (comma, no header, 1362 rows; 1440 would be gapless)
  0,1.38676,1.38686,1.38669,1.38686,0,1.38686,1.38697,1.38680,1.38697,0
  60000,1.38688,1.38688,1.38685,1.38685,0,1.38700,1.38700,1.38696,1.38698,0
  ```
  Columns: `ms_since_midnight, bid O/H/L/C, bidVol(0), ask O/H/L/C, askVol(0)`.
  Open question for 2b: which timezone the file-date / midnight is in.
- Plan: bootstrap a known-good workspace + `lean.json` once (either a free QC
  account → `lean login`+`lean init`, or hand-written from the open-source
  defaults), then run **fully offline** with the `Data/` tree on a mounted Docker
  volume (`quantconnect/lean` is a public image).
- 2026-05-25: account created; `lean login` ✓ (credentials live only in the
  gitignored `ws/lean.json` — never committed); `lean init` in `ws/`
  (empty dir; it refuses a non-empty cwd) downloaded `lean.json` (646 lines) +
  `data/forex/oanda/minute/eurusd` sample (~210 MB). `quantconnect/lean` image is
  **~10.6 GB** (pull in progress). `lean backtest "Spike1"` (sample SPY) queued in
  the background — Task 1 proof pending the image.
- 2026-05-25 (offline prep while pulling): **Task 2b** algo written
  (`ws/Task2b_BarCount/`), expected **1405** bars for 2014-05-07. **Task 3a**
  materializer (`materialize.py`) self-tested **byte-identical** to the real
  sample — conversion de-risked without the engine.
- 2026-05-25 (review hardening): made the spike **auto-proving** (Codex review):
  Task 2b algo now **raises** on mismatch (expected count 1405, first ms 0, last ms
  86 340 000; `fill_forward=False` so it counts raw file bars, not LEAN's filled
  1440); `materialize.py` uses the central `lean_data_dir_for` suffix (no parallel
  path convention) and fail-fasts on off-day / non-minute-aligned bars; resolved
  the bid/ask drift (format is a quote bar with both sides — we write both). The
  generated `ws/` is gitignored (account ids + 210 MB sample); curated algos live
  in `algos/`.
- 2026-05-25 (Task 1 ✓ + Task 2b ✓): backtest runs locally on `quantconnect/lean:17748`
  (digest `sha256:4934c22c…`) via a **py3.11 venv with `setuptools<81`** — the lean
  CLI imports `pkg_resources`, which setuptools ≥81 removed, so `uvx` (and modern
  setuptools) break with `No module named 'pkg_resources'`. Sample SPY backtest
  produced statistics. Task 2b (auto-proving) then measured the real convention:
  ```
  BAR1 t=2014-05-06T23:59:00 e=2014-05-07T00:00:00   (file ms=0)
  BAR2 t=2014-05-07T00:00:00 e=2014-05-07T00:01:00   (file ms=60000)
  TZ = America/New_York
  ```
  ⇒ tz=NY; `bar.Time`=start, `EndTime`=start+1min; **CSV `ms` = bar END**, file day
  = END's day. `materialize.py` (written assuming ms=start/UTC) must be reworked
  accordingly before Task 3b.
- 2026-05-25 (Task 3b — tz, the decision point): `materialize.py` writes our 3 UTC
  bars (start 00:00/01/02) correctly, BUT LEAN reads them **shifted −4h**
  (BAR1 `t=2014-05-12T20:01`), even with `set_time_zone(UTC)` AND
  `MarketHoursDatabase.set_entry(..., TimeZones.UTC)` in `initialize`. So: the
  forex **data** is read in the market exchange tz (America/New_York) regardless;
  the algorithm tz only relabels, the programmatic MHDB override did not change the
  reader. **Two paths to resolve:**
  - **A (mirror LEAN):** materialize lean-data in the **market tz (NY)** like real
    LEAN data (canonical Parquet stays UTC; convert UTC→NY at the export boundary,
    DST-aware). Easiest mapping — the lean-data is byte-compatible with LEAN's.
  - **B (force UTC in LEAN):** ship a custom `market-hours-database.json` in the
    data folder setting the oanda-forex `dataTimeZone` to UTC, so our UTC files
    read 1:1 (no DST). Cleaner "UTC everywhere", but customises LEAN config; the
    programmatic override failed, the file-based one is untested.
  Decision pending (tension: "UTC everywhere" vs "use it like LEAN, easy mapping").
- 2026-05-25 (Task 3b, honest status): forcing UTC via MHDB override failed
  (option B out). Writing lean-data in NY (`materialize.py` UTC→NY, option A) did
  **not** yield UTC 1:1 either: our `00:01` UTC bar read back as `16:01` (−8h),
  while the no-conversion attempt was `−4h`. So LEAN's forex file↔algorithm tz
  conversion is **non-trivial** (direction/order unclear from two data points) and
  must be nailed **empirically with tests** (winter vs summer dates; testcontainers)
  in the **real** materializer — not reverse-engineered in this throwaway spike.
  **Decision:** the market/data tz is **config, never hard-coded** (the spike
  hard-codes `America/New_York` only as throwaway). Spike outcome: 0/1/2a/2b done
  (engine, format, END-indexing, and tz confirmed as the genuine risk); 3a
  mechanics done; **3b tz-exactness deferred to the real config-driven materializer**.
- **Finding (resolution naming):** lean-data dirs use LEAN resolution names
  (`minute`/`hour`/`daily`), NOT our `Timeframe` labels (`m1`/`h1`/`d1`). Mapping:
  `m1 → minute`, `h1 → hour`, `d1 → daily`; `m5/m15/m30/h4` are **not** LEAN base
  resolutions → derived in-engine by consolidators, so only the base resolution is
  materialized to lean-data. The path *suffix* (`forex/<market>/minute/<symbol>`)
  matches `layout.lean_data_dir_for`; only the root differs (LEAN's data folder).
