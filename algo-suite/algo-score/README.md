# algo-score

Scores sentiment and events into the feature Parquet. Pipeline step 2:
download → transform → **score** → backtest → analyze.

## What it does

- Runs the sentiment scorers over the news corpora: a deterministic
  **Loughran–McDonald** dictionary baseline now, with **FinBERT** planned, and
  with **per-currency attribution** so EUR and USD tone can be differenced into
  a pair signal.
- Produces **event features** (e.g. GPR regime, macro-calendar context).
- Writes minute-bucketed feature Parquet under `parquet/sentiment/` and
  `parquet/events/`.
- Expensive inference goes through `algo-core`'s **read-through `Cache` port**,
  keyed by article id, publish time, text hash, and `model_version`, so a model
  is never re-run on text it already scored.

## Inputs and outputs

| Direction | Item |
|---|---|
| In | `parquet/news/<source>/...`, optional `parquet/price_minutes/...` |
| Out | `parquet/sentiment/...`, `parquet/events/...` |

## CLI

```bash
uv run algo-score --help
uv run algo-score version
uv run algo-score --scorer lm --source gdelt --month 2020-01
uv run algo-score events --kind gpr --from 2020-01-05 --to 2020-01-07
uv run algo-score events --kind gdelt --month 2020-01
```

## Config (optional)

`../conf/score.yaml` (model choice, batch size, GPU); cross-cutting from
`../conf/algo.yaml` or `ALGO_*` env.

## Status

LM sentiment is implemented for article fixtures shaped as `id`, `text`, and
UTC `publish_ts`. `algo-score --scorer lm` writes minute sentiment under
`parquet/sentiment/lm/...`, per-article cacheable scores under
`parquet/sentiment/lm_articles/...`, per-currency rows under
`parquet/sentiment/lm_currency/...`, and derived EURUSD/USDJPY rows under
`parquet/sentiment/lm_symbol/...`.

Event-feature slice implemented: `algo-score events --kind gpr|gdelt` reads the
canonical event Parquet from `algo-transform`, forward-fills daily values onto
the minute grid with a **one-day publication lag** (day D's value first appears at
00:00 UTC on D+1, so no bar sees a same-day aggregate), and writes provider-specific
feature partitions under `parquet/events/_features/<kind>/...`. A `--from/--to`
build over part of a month merges into the existing monthly partition, keeping its
rows outside the range. The GDELT `event_intensity` feature is
the unweighted daily mean of `goldstein_scale`; `avg_tone` is kept out of this
feature. FinBERT remains planned. CPU path always works.

Spec: [`SPEC.md`](SPEC.md).
