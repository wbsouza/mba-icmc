# Spec 06 — monografia: write Chapter 4 (Experimental Evaluation)

**Target:** [`monografia/chapters/04-experimental-evaluation.tex`](../../../../../monografia/chapters/04-experimental-evaluation.tex)
**Status:** skeleton only — every results section is a `\textit{To be added in
the final version.}` placeholder; §sec:experimental-setup narrates the
implementation status as of the intermediate submission (2026-05-25), stale
once Specs 01–05 land.
**Depends on:** Specs 01–05 landed (or as many as the freeze date allows —
this spec's whole point is to make partial completion reportable honestly,
not to block on 100%).
**Governing contracts:** [`algo-suite/docs/experiments.md`](../../../experiments.md) (experiment →
command → Chapter 4 artifact — the literal section-by-section source for this
chapter), [`algo-suite/docs/ch04-deliverables.md`](../../../ch04-deliverables.md) (status tracker, update as
you go), [`monografia/chapters/03-methodology.tex`](../../../../../monografia/chapters/03-methodology.tex) (the protocol this chapter
reports results *against* — do not restate methodology, cite it).

## 1. Objective

Fill in the seven planned sections of Chapter 4 with real results, each
traceable to a `run-id` per the reproducibility discipline already established
([`experiments.md`](../../../experiments.md) §5). This is a writing task with a hard sourcing constraint:
**no number in this chapter may be written without a corresponding
`runs/<run-id>/` directory and command to reproduce it.** If a result isn't
run yet, the section stays a documented placeholder (as it already correctly
does today) — never a fabricated or estimated number. This mirrors the
project's fail-fast discipline applied to academic writing: an honest "not yet
run" beats a silently invented figure.

## 2. Section-by-section sourcing (do not deviate from this mapping)

| Ch04 section | Source | Do not write until |
|---|---|---|
| §sec:experimental-setup | Narrative — which adapters/scorers/strategies run end-to-end, exact data spans used | Specs 01–05's actual landed state (rewrite this section from scratch; the current text describes 2026-05-25 status and is now stale) |
| §sec:coverage-results | Spec 02's coverage-matrix figure + the empirical window it derives | Spec 02 done |
| §sec:baseline-results | Spec 05 `metrics --run <baseline-id>` table + equity-curve figure (Experiment 1) | Spec 04/05: a real baseline run + metrics command exist (may already be satisfiable today from the 2026-05-26 execution pass + Spec 05's metrics command) |
| §sec:hybrid-results | Spec 05 `ablation --runs baseline hybrid` (Experiment 2/3) | Specs 03+04+05 all landed |
| §sec:ablations | Spec 05 ablation across feature families (Experiment 4) and Core vs A–D (Experiment 6) | Spec 04's filter variants + Spec 05 ablation |
| §sec:zhang-comparison | Spec 05 deflated Sharpe vs `zhang2025macroalpha` (Experiment 5), read against the plausibility band in [`experiments.md`](../../../experiments.md) §7.1 | hybrid deflated Sharpe exists |
| §sec:experimental-threats | Discussion specialized to whatever was actually observed (not generic boilerplate — read the actual numbers before writing this) | all prior sections in this chapter are written |

## 3. Writing discipline (project-specific, from CLAUDE.md and `feedback_writing_style`)

- **American English**, mirror the established dissertation voice (see the
  project's writing-style memory if available to the writing agent; otherwise
  match Chapters 1–3's register — measured, evidence-led, no marketing tone).
- **Never call the user "the author."** Use impersonal third person ("this
  work", "the present study") or passive voice.
- **Never write "MBA programme"/"MBA program"** — "the MBA in Artificial
  Intelligence and Big Data" or "the MBA."
- **A negative/flat baseline Sharpe is reported as expected, not as a
  failure** — [`experiments.md`](../../../experiments.md) §7.2 gives the exact framing: unleveraged major-
  pair FX without an edge is expected to be flat/negative; the quantity that
  tests H1 is the hybrid-minus-baseline delta, not the absolute baseline
  level. Do not let the prose apologize for a negative baseline number.
- **A result that matches Zhang (2025) too closely is a flag, not a win** —
  [`experiments.md`](../../../experiments.md) §7/§7.1: treat a deflated Sharpe at/above 5.87/4.65 as
  something to investigate (leakage, cost-model error) before reporting it as
  a positive result. Say so explicitly in §sec:zhang-comparison if it happens.
- **Every table/figure caption cites its `run-id`** so any reader can
  reproduce it via the command in [`experiments.md`](../../../experiments.md) §2.
- **`make pt-scan`** after every edit (English-only rule; proper nouns like
  "São" excepted).

## 4. Partial-completion honesty (the Medium-fallback case)

The 2026-09-22 freeze already arrived with specs 01–04 incomplete (deferred to
future work, per [`00-PLAN.md`](../../00-PLAN.md)) — this chapter must
say so explicitly and specifically — which sections have real results, which
are deferred, and why — rather than silently truncating. This is the same
pattern the *current* skeleton already uses correctly (§sec:experimental-setup
in the existing intermediate version names exactly what's built and what
isn't); continue that pattern, updated to whatever the actual freeze-date
state is. [`PRD.md`](../../../../PRD.md) §2's Medium fallback ("methodology + ingestion + baseline;
hybrid documented as future work") is the literal fallback text to use if
Specs 03/04 didn't land in time — §sec:hybrid-results, §sec:ablations, and
§sec:zhang-comparison become "documented as future work" sections citing
Chapter 5, not empty placeholders and not apologies.

## 5. Definition of done

- Every section either has a real, `run-id`-traceable result, or an explicit,
  specific "deferred to future work" statement — never a placeholder left
  silently unresolved and never an invented number.
- `make pt-scan` clean; `make verify` (page count + undefined-citation scan)
  clean.
- [`algo-suite/docs/ch04-deliverables.md`](../../../ch04-deliverables.md) status column updated to ✅/🟡 for
  every row this spec touched.
- [`00-PLAN.md`](../../00-PLAN.md) §1 updated to reflect the chapter's actual final state.
- Cross-check every claimed number against [`experiments.md`](../../../experiments.md) §7.1's
  plausibility bands before submitting — a number outside the expected band
  gets investigated (per §3 above), not written up as-is.
