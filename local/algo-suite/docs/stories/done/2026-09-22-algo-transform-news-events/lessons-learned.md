# Lessons learned — Spec 02: algo-transform GDELT/GPR decode + coverage matrix

**Sourced from the specifier → coder → cleaner → hardener → QA pipeline
commits on `algo-score-event-features`** (`92b4fab`, `341750c`, `ef2893e`,
`45b611d`, `77f76ae`, `28c2bfb`, `f2d4886`).

**Cross-tool scope decisions must be recorded where the downstream tool can
find them.** `92b4fab`'s spec had to resolve against algo-download's confirmed
real-feed facts (branch `spec-01-algo-download-gdelt-gpr`, not yet merged at
the time): GDELT's raw scope is Events-table only, no article text — so
algo-transform writes `parquet/events/{gdelt,gpr}/` only, never
`parquet/news/gdelt/`. That gap (no free text-sentiment source) became
[`technical-debt.md`](../../../technical-debt.md) TD-28, which is exactly what later justified building the
separate GDELT Web News NGrams 3.0 adapter (see the `gdelt-ngrams-adapter`
story) — a debt ledger with a concrete trigger paid off within the same day.

**Test real file formats, not just the fixtures you already have.** `28c2bfb`
found `decoders/gpr.py`'s CRAP gate failing because `_decode_xls` and
`_cell_value` sat at 0% coverage — every existing fixture was UTF-8 CSV/TSV,
but the production GPR distribution is a real binary BIFF `.xls` file that
`decode_gpr` only reaches once UTF-8 decoding fails. Built a real `.xls`
workbook with `xlwt` (xlrd's write-side counterpart) to actually exercise that
branch; coverage went 58% → 86%. A format-detection fallback path is
untested until you feed it the format it's supposed to fall back for.

**Renumber Gherkin scenarios immediately after outline consolidation**
(`341750c`): folding standalone rejection scenarios into one `Scenario
Outline` left a following scenario's id skipping two numbers for no reason.
A post-commit self-audit caught it same-day — cheap when caught immediately,
confusing for the next reader if left.
