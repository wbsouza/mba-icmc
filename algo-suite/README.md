# algo-suite

The trading-tools source tree for the TCC *"Algorithmic Trading Enhanced by AI"*
(MBA in AI & Big Data, ICMC/USP). A modular pipeline of self-describing
`algo-<action>` tools wired as a single [uv](https://docs.astral.sh/uv/)
workspace. The dissertation lives in `../monografia/`; product and design docs
in `PRD.md` and `docs/`.

The [experimental workflow](docs/experimental-workflow.md) documents all research
stages, including training, calibration, model freezing, replay, and evidence
review. The tool pipeline below is only the software layout.

## Pipeline

```
algo-download → algo-transform → algo-score → algo-backtest → algo-analyze
                          (all built on algo-core)
```

| Tool | Responsibility | Phase | CLI |
|---|---|---|---|
| [`algo-core`](algo-core/) | shared lib: `Instrument`, storage layout, DuckDB, config, Repository + Cache ports | base | — (library) |
| [`algo-download`](algo-download/) | bulk download per source (Dukascopy, GDELT, GPR) → `raw/` | 1 | `algo-download` |
| [`algo-transform`](algo-transform/) | raw → canonical Parquet; coverage + currency-strength | 1 | `algo-transform` |
| [`algo-score`](algo-score/) | Loughran–McDonald sentiment (per-currency; FinBERT planned) + GDELT/GPR events → feature Parquet | 2 | `algo-score` |
| [`algo-backtest`](algo-backtest/) | materialize `lean-data/`, LightGBM meta-learner, deterministic filter chain on LEAN | 3–4 | `algo-backtest` |
| [`algo-analyze`](algo-analyze/) | metrics, DSR probability, paired stationary-bootstrap mean-return test, ablations, figures, consolidated equity curves | 5 | `algo-analyze` |
| [`algo-viewer`](algo-viewer/) | results viewer over the SQLite file `algo-analyze results-db build` writes: a TypeScript backend (JSON API, `node:sqlite`) and a React page — runs, overlaid equity curves, trades and why the chain entered each one (`make viewer`, `make viewer-serve`) | 6 | `node dist-server/server/main.js` |

Each tool dir holds its own `SPEC.md` (technical spec, colocated with the code)
and a `tests/` tree of Gherkin features.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (>= 0.10)
- Python 3.11 (pinned in `.python-version`; matches the LEAN container)
- Docker (for LEAN backtests and the `integration`-marked tests; the pinned
  `quantconnect/lean:17748` image is ~10 GB)
- **Allure CLI** — *optional*, only for `make report` (the graphical BDD report).
  It is a Java tool; install via npm or the official tarball, **not** apt:
  ```bash
  sudo apt install default-jre          # Allure needs a JRE
  npm install -g allure-commandline      # then: allure --version
  ```
  Do **not** `apt install allure` — on Debian/Ubuntu that package is an unrelated
  roguelike game, not the report tool. Without the CLI, `make check` and
  `uv run pytest` still run the whole suite; only the HTML report needs it.

## Quickstart

```bash
make install          # uv sync --all-packages → single .venv at the workspace root
make check            # ruff + mypy(strict) + pytest (BDD)
make report           # run the BDD suite and open the Allure report (graphs)
uv run algo-download --help
```

Per-tool: each tool installs independently and ships its own `Makefile`. Note the
**default `data_root` assumes this workspace tree** (it locates `algo-suite/`
upward from the package); installed standalone, set `ALGO_DATA_ROOT` explicitly or
`data_root()` raises (fail-fast, by design — no silent wrong path).

Tests are **BDD** (pytest-bdd): `.feature` files live in each tool's
`tests/features/`, step implementations in `tests/steps/`, and plain
unit/property tests in `tests/unit/`. `make report` needs the
[`allure` CLI](https://allurereport.org/docs/install/) (a Java tool, separate
from the Python `allure-pytest` plugin); without it, `make check` and
`uv run pytest` still run the whole suite.

## Configuration (convention over configuration)

Runs **zero-config**: every setting has a sane default. A file under `conf/`
exists *only* to override one. Resolution order (highest wins):

```
environment (ALGO_*)  >  conf/<tool>.yaml  >  conf/algo.yaml  >  defaults
```

Env always wins, so a container overrides anything. See [`conf/README.md`](conf/README.md).

> **Status:** implemented as `algo_core.config.resolve` (TD-3): it reads/merges the
> YAML files, applies the `ALGO_*` env layer, then enforces the schema-driven
> **loader policy**. Consumers today: `algo-backtest` (`conf/backtest.yaml`) and
> `algo-analyze` (`conf/analyze.yaml`).

## Data

One data root for every tool, resolved by `algo-core` from `ALGO_DATA_ROOT`
(default `data/`):

```
data/{raw,parquet,lean-data,runs}/
```

Parquet is the canonical source of truth; the LEAN-native `lean-data/` execution
store and the feature cache are derived and read-through (materialized once,
reused across the sweep). See [`docs/parquet-evaluation.md`](docs/parquet-evaluation.md)
and [the storage design](docs/parquet-evaluation.md). Data contents are gitignored.

## Docker (planned — TD-11)

Each tool **will ship** a `Dockerfile` (none exist yet); the intended contract is
that config and data flow in by mount + env:

```bash
docker run --rm \
  -e ALGO_DATA_ROOT=/data -v /nas/tcc:/data \
  -e ALGO_CONF_DIR=/conf   -v "$PWD/conf:/conf:ro" \
  algo-download run --source dukascopy
```

LEAN runs locally (Apache 2.0); no QuantConnect cloud cost.

## Status

All six packages are implemented and tested (BDD): Dukascopy/GDELT/GPR download,
canonical Parquet transform, LM sentiment + GDELT/GPR event features, LEAN
backtests (price-only baselines plus the config.yaml-driven F1–F7 `baseline`/`hybrid`
filter-chain strategies with the reference trade plan and configured fill costs —
pilot runs, not yet the registered one-year experiment; see
`docs/ch04-deliverables.md`), and `algo-analyze`
metrics/significance/ablation/figures/equity-curves. Every strategy parameter is a key
of `strategies/<name>/config.yaml` with recorded provenance
(`algo-backtest/SPEC.md` §6.4.1). Current Chapter-4 status:
[`docs/ch04-deliverables.md`](docs/ch04-deliverables.md).

## Conventions

SOLID, clean code, single-return value objects, no magic numbers, GoF only where
it removes duplication (see `docs/architecture.md` §13). **All tests are
BDD** (Gherkin `.feature` + pytest-bdd).
