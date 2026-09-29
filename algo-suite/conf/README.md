# conf/ — overrides only

**Convention over configuration.** The suite runs with no files here at all;
every setting has a sane default. A file in this directory exists *only* to
override a default.

## Resolution order (highest wins)

```
environment  >  conf/<tool>.yaml  >  conf/algo.yaml  >  convention defaults
```

Environment always wins, so a container overrides anything without editing a
mounted file.

## Convention-named files (all optional)

| File | Overrides |
|---|---|
| `algo.yaml` | global / cross-cutting (`data_root`, `log_level`, shared defaults) |
| `<tool>.yaml` | one tool, e.g. `download.yaml` (source list), `score.yaml` |
| `backtest.yaml` | `algo-backtest` settings (e.g. `markets.oanda.data_tz`, `broker.adapter`) |

Strategy definitions (filter chain, meta-learner families) are not here: they are
version-controlled with the code in
`algo-backtest/src/algo_backtest/strategies/<name>/config.yaml`.

`*.sample` files show what can be set. To activate, copy to the real name
(e.g. `cp algo.yaml.sample algo.yaml`) and adjust the values for your machine
(e.g. `data_root` to your own NAS/mount path). The real file is
machine-specific and gitignored — never commit it.

## Environment overrides

Prefix `ALGO_`, nested keys via `__`:

```
ALGO_DATA_ROOT=/data         # the data root (mount a volume here)
ALGO_LOG_LEVEL=DEBUG
ALGO_CONF_DIR=/conf          # relocate this dir (container mount)
ALGO_DOWNLOAD__SOURCES=...    # nested into the download tool
```

## In Docker (planned — TD-11; no tool ships a Dockerfile yet)

```
docker run --rm \
  -e ALGO_DATA_ROOT=/data -v /nas/tcc:/data \
  -e ALGO_CONF_DIR=/conf   -v "$PWD/conf:/conf:ro" \
  algo-download run --source dukascopy
```
