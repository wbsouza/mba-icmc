# algo-transform

Turns raw payloads into the canonical Parquet store. Pipeline step 1 (with
`algo-download`): download → **transform** → score → backtest → analyze.

## What it does

- Decodes raw payloads (Dukascopy `.bi5` ticks via stdlib `lzma`+`struct`,
  scaling points by `price_increment = 10^-digits`) into validated `Tick`s,
  distinguishing data / 0-byte no-data marker / corrupt (quarantine).
- Resamples ticks into minute `QuoteBar` records (**bid OHLC + ask OHLC + tick
  count**; mid/spread derived downstream) and writes the canonical Parquet tree.
- Later: the **coverage matrix** of the corpora (with per-source completeness
  metrics) and the **currency-strength** feature.

Delivered in slices: (1) `.bi5` → validated ticks; (2) ticks → minute Parquet;
(3) coverage / currency-strength / GDELT / GPR.

## Inputs and outputs

| Direction | Item |
|---|---|
| In | `raw/<source>/...` |
| Out | `parquet/forex/<pair>/<timeframe>/year=YYYY/month=MM/`; later coverage + currency-strength |

## CLI

```bash
# decode raw Dukascopy ticks -> QuoteBar Parquet for a month
uv run algo-transform run --source dukascopy --symbol EURUSD --month 2020-01
# choose the bar frequency (default m1):
uv run algo-transform run --source dukascopy --symbol EURUSD --month 2020-01 --timeframe h4
# news/event sources (canonical event Parquet for algo-score), month or --from/--to range:
uv run algo-transform run --source gdelt --month 2015-02      # also: gpr, gdelt_ngrams
# GDELT coverage matrix + selected training window (CSV + figure):
uv run algo-transform coverage
```

Config file/env layering exists in `algo-core` (`config.resolve`, TD-3) but this tool
does not load config yet.

## Status

**Slices 1–2 runnable and gated.** bi5 decoder (3-state, `price_increment`
scaling) → `Tick`; `resample(ticks, timeframe)` → `QuoteBar` at any MT5 timeframe (m1..d1);
completeness-gated, write-only-when-complete orchestrator writing the canonical
`<timeframe>/` Parquet via `Repository`; CLI `run --timeframe`. End-to-end BDD
(raw `.bi5` → partition; incomplete or corrupt month writes nothing). ruff +
mypy-strict clean, ~99% coverage on the new code.
Slice 3 is partly built: GDELT, GDELT NGrams and GPR transforms
(`decoders/`, `readers/`, `events.py`) and the GDELT coverage matrix
(`coverage.py`, `coverage_artifacts.py`, `algo-transform coverage`).
Currency-strength and tick Parquet are not built yet.

Spec: [`SPEC.md`](SPEC.md).
