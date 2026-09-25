# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Final TCC for the MBA in Artificial Intelligence and Big Data (MBAIAe, ICMC/USP). Top-level pieces:

- `monografia/` — LaTeX thesis (USPSC/abntex2 class, English-only). Built with `latexmk` + `pdflatex` + `bibtex` (not biber) + `makeindex`. Bibliography style is `abntex2-alfeng-USPSC` (author-date, English).
- `news-downloader/` — original Python GDELT pipeline. **Now parked at `algo-suite/algo-download/reference-impl/`** as a read-only reference for migrating its GDELT adapter into `algo-download` (TD-12); excluded from the gate. The architecture notes below describe that reference. New work goes in `algo-suite/`, not here.
- `presentation.tex` — standalone Beamer deck (pt-BR, `aspectratio=169`, Madrid theme) for the *Workshop de Ideias*. Build with `pdflatex presentation.tex` from the repo root; output `presentation.pdf` and its aux files are `.gitignore`d at the root `build/` ignore (but the aux files are not yet pattern-ignored — leave them untracked).
- `related-work/` — reference PDFs of prior USP MBA TCCs downloaded from the library. Read-only references for positioning; do not edit.
- `monografia/tcc-evaluation-and-direction.md` — running notes on feedback received and direction; consult alongside `specs.md`.

`.gitignore` still has a stale `dissertacao/build/` entry (the directory was renamed to `monografia/` in commit `85aa695`). The real build-output ignore is the unscoped `build/` line at the bottom. Other paths (`Makefile`, `main.tex` `\include`s, README) already reflect `monografia/`.

`CLAUDE.md` and `specs.md` are both `.gitignore`d — they live locally per-clone, not in version control.

## Source of truth

- **Scope and assignment brief:** `monografia/Final Research Project.pdf`.
- **Architectural decisions for the empirical work:** `specs.md` at repo root. Every decision dated. Later decisions amend, never overwrite. Read this before designing any new component (currency pairs, time window, sentiment scorer, backtester, data layout). Do not contradict it without writing a new dated amendment.
- **Submission track:** TCC normal (Track a) — Introduction, Theoretical Foundation, Methodology/Proposal. Final submission 2026-05-25, scope freeze 2026-05-18.

## Common commands

### `monografia/` (LaTeX)

```bash
cd monografia
make           # incremental build → build/tcc.pdf
make watch     # latexmk -pvc rebuild on save
make rebuild   # distclean + full rebuild
make verify    # page count + undefined-citation scan + chapter pages
make pt-scan   # list leftover Portuguese-accented words (English text only)
make toc       # show pages where each chapter starts
make clean     # latex aux files (PDF kept)
make distclean # wipe build/
```

Output PDF is `build/tcc.pdf` (jobname=`tcc`, not `main`). Auxiliary files are mirrored under `build/{pre,chapters,pos,classe}/` — the Makefile creates those subdirs before invoking latexmk. Do **not** modify files under `monografia/classe/` — vendored from the USPSC distribution.

State of the manuscript (check `wc -l monografia/chapters/*.tex` before trusting this): chapters 01 (intro), 02 (theoretical foundation), and 03 (methodology, ~380 lines, eleven sections) are substantially written. Chapter 04 (experimental evaluation) is a "work in progress" skeleton — section plan only, no results yet, pending the engineering components becoming runnable. Chapter 05 (conclusion) has Final Remarks drafted. The abstract is a placeholder. Cataloguing card and approval sheet wait on PDFs from the library/defence (`\includepdf` lines in `main.tex` are commented out until those arrive).

### `news-downloader/` (Python) — parked reference at `algo-suite/algo-download/reference-impl/`

Legacy GDELT pipeline, kept read-only as a migration reference (TD-12); excluded
from the gate. To run the reference directly:

```bash
cd algo-suite/algo-download/reference-impl
pip install -r requirements.txt
python src/main.py                          # auto-finds config.yaml in this dir
python src/main.py --dry-run                # print plan, no downloads
python src/main.py --source gdelt           # run only one source
python src/main.py --config /path/to/config.yaml
```

Resume is automatic: `source.is_done(unit)` checks for the Parquet file on disk, so re-running skips completed `(table, year, month)` units. The `state:` block under each source in `config.yaml` is machine-managed — do not hand-edit it while a run is in flight.

## news-downloader architecture

Single port, many adapters. The orchestrator (`src/main.py`) depends only on the `NewsDataSource` abstraction (`src/adapters/base.py`).

Patterns in use:
- **Strategy + Adapter** — `NewsDataSource` ABC declares `plan() / unit_key() / is_done() / execute()`. Each concrete source adapts one external feed.
- **Registry + Factory Method** — `src/adapters/__init__.py` exposes `REGISTRY` and `build_data_source(name, cfg, root)`. Subclasses self-register via the `@register` class decorator at import time.
- **Value Object** — units of work are frozen dataclasses (e.g. `GdeltMonth`).
- **Repository** — `MasterFileIndex` caches the GDELT master list.
- **Coordinator** — the data-source class orchestrates downloader/writer collaborators rather than doing their work inline.

### Adding a new source

1. Create `src/adapters/<source>/data_source.py` with:
   ```python
   from .. import register
   from ..base import NewsDataSource

   @register
   class FooDataSource(NewsDataSource):
       name = "foo"
       # implement plan, unit_key, is_done, execute
   ```
2. Add a `foo:` block under `sources:` in `config.yaml` (must include `enabled: true` to run).
3. Add `from . import <source>` to `src/adapters/__init__.py` — import-for-side-effect triggers the `@register` decorator. No edits to any other adapter's files.

### On-disk layout under `data_root`

- Raw payloads: `raw/<source>/...`
- Parquet: `parquet/<source>/<table>/year=YYYY/month=MM/data.parquet`

`data_root` is typically a NAS mount (e.g. `/volume1/tcc`). The `data/`, `raw/`, `parquet/` paths at the repo root are `.gitignore`d.

## Working rules

- **New code lives under `algo-suite/`** (the uv workspace, code root), each tool its own member subdirectory: `algo-core/`, `algo-download/`, `algo-transform/`, `algo-score/`, `algo-backtest/`, `algo-analyze/`. Do not build new tools inside `algo-suite/algo-download/reference-impl/` (the legacy `news-downloader`, parked for migration — TD-12). The repo root holds the thesis (`monografia/`), `PRD.md`, `related-work/` and `algo-suite/`; the design corpus lives under `algo-suite/docs/`.
- **Config = convention over configuration.** Runs zero-config; `algo-suite/conf/*.yaml` exist only to override defaults. Precedence: env (`ALGO_*`) > `conf/<tool>.yaml` > `conf/algo.yaml` > defaults. Data root is `algo-suite/data/` by convention, relocatable via `ALGO_DATA_ROOT` (a mounted volume in Docker); `conf/` relocatable via `ALGO_CONF_DIR`.
- **Each tool's spec is colocated** as `algo-suite/algo-<tool>/SPEC.md` (not a central `docs/specs/`). The design corpus lives under `algo-suite/docs/`; only the product-level `PRD.md` stays at the repo root.
- **Every story gets a `progress.md`.** Before implementation starts, write `progress.md` next to that story's `spec.md` under `algo-suite/docs/stories/{planned,in-progress,done}/<story>/`: a TODO checklist of every deliverable. Mark each item `[x]` only once it is actually done (code committed, its test green) — never check an item ahead of the work, and update the checklist in the same commit that completes the item, not in a later batch. Stories move `planned/` → `in-progress/` → `done/` as work progresses (a plain directory move, same as the `planned/` → `in-progress/` move already done for Spec 08 this session). A story only moves to `done/` once every item in its `progress.md` is checked off, and the move adds a `lessons-learned.md` alongside `spec.md`/`progress.md` — what actually happened that the spec didn't anticipate, what took longer/shorter than planned, what would be done differently next time. Not a summary of the spec; a retrospective of the gap between the spec and reality.
- **🔴 EVERY test is described in Gherkin/Cucumber — NON-NEGOTIABLE, NO EXCEPTIONS.** This is a hard, user-mandated standard repeated from the start. **Never write a plain `def test_…()`** — not for integration, not for unit, not for "pure logic" encoders, not for anything. Every behaviour is a `.feature` `Scenario` (`Scenario Outline` + `Examples` for parametric cases; data tables for multi-row input) with `pytest-bdd` steps. Before writing any test, write the `.feature` FIRST, then implement the steps. Layout: `.feature` in `tests/features/`, steps in `tests/steps/test_<name>.py` (`scenarios("../features/<name>.feature")`), shared steps/fixtures in `tests/conftest.py` / `tests/steps/conftest.py`. Tag container/network features (`@integration`, `@network`) so pytest-bdd maps them to the marks deselected from `make check`. The graphical report is Allure (`make report`; needs the `allure` CLI). *(History: a `tests/unit/` plain-pytest allowance previously lived here and caused a violation — it is removed; pure-logic tests are Gherkin too. Any legacy plain-pytest tests in other tools, e.g. `algo-transform`, are debt to migrate to Gherkin, not a precedent to copy.)*
- **Code-quality gate** (`make check`): ruff (incl. `C901` mccabe, max-complexity 8) + mypy strict + pytest. Principles: clean code, SOLID, low cyclomatic complexity, DRY, KISS; single-return value objects; no fabricated data.
- **Docstrings on every function**, including private helpers (a one-line summary of intent suffices). The point is that the docstring conveys what a function does without reading its body. Document **arguments only when their meaning isn't obvious from name + type** (units, constraints, what a key encodes, a callable's contract, side effects) — code is mypy-strict, so an `Args:` block that merely restates types is redundant. Add `Raises:` where the failure modes matter.
- **Before moving to a new task, run a debt + vulnerability check.** Run `make audit` (dependency CVEs) and review leftover technical debt: every new code path has a covering BDD scenario (no untested branches), no silent fallbacks (fail-fast), no unused/dead dependencies, partitioning/concurrency/atomicity gaps surfaced. Confirm the gate (`make check`) is green and recommend committing.
- **Keep docs in sync with the implementation.** On completing any task, verify the documentation (`PRD.md`, `algo-suite/docs/*`, each tool's `SPEC.md` + `README.md`, the layout trees) still matches the code and the decisions actually made; update anything stale or missing. Docs that drift from the build mislead reviewers and future work.
- **Deferred-debt ledger: `algo-suite/docs/technical-debt.md`.** Debt that *can't* be solved yet (the depended-on code isn't written) goes here as a row with a blocker and an unblock **trigger** (never a bare "TODO"). **On completing any task, review this file** and do anything whose trigger is now met (mark it `ready`/`resolved`); add newly-discovered deferred items as they arise.
- **Fail fast — never hide errors behind defaults or fallbacks.** On an unexpected/missing/invalid input or state, **raise immediately** with a clear message; do not substitute a silent default, return a sentinel/`None`/empty, fall back to a guess (e.g. `Path.cwd()`), or swallow exceptions. A hidden wrong default (wrong `data_root`, wrong unit) corrupts results far from the cause. The **one** deliberate exception is the config loader's documented, logged "default-with-log for operational params" policy (trading-impactful params still hard-stop). Optional dependency-injection defaults (e.g. `memory: Cache | None = None → build_cache()`) are fine — that's injection, not error-hiding.
- **Every failure explains why and how to fix, and is logged.** Raise with a message that states **what** failed, **why**, and **how to fix it** (the remediation: which param/env var/command). The application boundary (each tool's CLI/orchestrator `main`) catches, **logs the failure via structlog** (so it lands in the log file) and exits with the error's exit code. Log at the boundary, not deep in the library, to avoid double-logging; library code raises remediation-rich exceptions.
- **Bulk-download once, query locally.** No live APIs in the hot path. Backtests read Parquet from local/NAS storage via DuckDB.
- **No assumed connectivity** to MetaTrader, broker APIs, news feeds, or LLM providers from this repo.
- **Stay inside this directory.** Do not modify sibling course modules (`../Quinzena 1/`, `../Quinzena 2/`, `../Tutorias/`).
- **English-only in the thesis body.** `make pt-scan` surfaces accidental Portuguese — proper nouns ("São", "Géron") are expected; everything else should be translated. The Resumo (`pre/resumo.tex`) is the one pt-BR section and is required by ABNT NBR 14724.
