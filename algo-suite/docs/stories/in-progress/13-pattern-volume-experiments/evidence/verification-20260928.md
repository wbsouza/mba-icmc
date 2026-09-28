# Intermediate-results documentation verification

Final artifact checks completed after the clock confirmation at
**2026-09-28 00:50:36 UTC**. Experiment status remains frozen at the separate
00:36:01–00:36:02 UTC observation interval.

## Monograph

`make verify` in `/tmp/mba-pattern-volume/monografia` completed with exit 0:

```text
Pages:           94
File size:       1080169 bytes
Undefined citations / references: none
Chapter 04 starts on page 77
Chapter 05 starts on page 85
```

PDF: `monografia/build/tcc.pdf`, SHA-256:
`27eab3825ccfe95ae865846c81c0dc236cd78aa280c29f51c713d3ac1a7cfb92`.
The final log was checked directly for undefined references/citations.
Chapter 04 has zero overfull boxes after local line-break adjustments.
The build still emits duplicate-destination warnings in the document and
layout warnings elsewhere; `make verify` is not a claim of globally clean
typesetting. Vendored classes and other chapters were not changed.

## Evidence and figures

- 16 successful final manifests and four running entries are archived.
  The historical failed launch and planned unstarted replay remain explicit.
- All 14 available archived JSON/YAML pairs agree structurally.
- Every present engine model hash matches its job-selected model.
- 88 completed-run/model artifact hashes were rechecked against source bytes:
  all unchanged. Active logs were deliberately not required to remain frozen.
- Local Markdown links in the result synopsis, parameter appendix, and resource
  addendum resolved during verification.
- All four dark figures were visually reviewed; the monograph's print figure
  and surrounding text were inspected in the rendered PDF text/layout.
- Eight figure artifacts (four dark PNG, four print PDF) have hashes in
  `figure-provenance-20260928T005036Z.json`.

## Scoped generator checks

The three Gherkin scenarios passed against real source artifacts:
`3 passed in 0.47s`. They check sample preservation (including original CSV
drawdown values), 2:1 panel geometry, parameter links, unfinished-run rejection,
and source-hash mismatch rejection. No synthetic performance fixture is used.

Ruff on the generator and its BDD steps: `All checks passed!`.
Strict mypy on the generator with explicit workspace source resolution:
`Success: no issues found in 1 source file`.

```sh
MYPYPATH=algo-analyze/src:algo-backtest/src:algo-core/src \
  .venv/bin/mypy --strict --follow-imports=silent \
  --cache-dir=/tmp/mba-pattern-volume/monografia/build/story13-mypy-cache \
  docs/stories/in-progress/13-pattern-volume-experiments/evidence/render_intermediate_figures.py
```

The command runs from `/tmp/mba-pattern-volume/algo-suite`. The first isolated
mypy invocation lacked these workspace paths and reported untyped package
imports; resolving the actual workspace sources removes those diagnostics.
The `DateFormatter` constructor has a documented, call-local
`type: ignore[no-untyped-call]` for its missing external signature, as requested.
No module-wide suppression or dependency change was added.

The main owner reported 60 remaining whole-workspace mypy errors in four
pre-existing files. This task does not claim a clean whole-workspace gate,
nor rerun unrelated experiments or change those files.

## Scope and handoff

This task changed only chapters 04/05 and the uniquely named Story 13 evidence,
figure generator, and BDD files. All original data and Claude worktrees were
read-only. The task created no commit or push, installed no dependency, and
did not kill, restart, or launch a backtest. Existing code changes by the main
owner were preserved. No Story 13 implementation checklist item was marked
committed or complete on the basis of this documentation work.

The `docs-writer` workflow shaped the source/result joins and explicit missing
fields. `clean-code` guided the isolated generator and BDD verification.
The explicitly requested `trading-visualization` skill supplied the 2:1 chart
composition and screen/print styling; its linked software guidance is not
used as financial evidence.

FinBERT remains a separate future factor requiring real text and model-vintage
verification. The eight candlestick/volume candidates remain pending launch;
their future outcomes must receive a new snapshot rather than replace this one.
