# Spec 07 — monografia: chapters 1/2/3/5 finalization + whole-document QA pass

**Target:** `monografia/chapters/{01-introduction,02-theoretical-foundation,
03-methodology,05-conclusion}.tex`, front/back matter, `bib/references.bib`.
**Status:** these chapters are written and frozen per
`tcc-evaluation-and-direction.md`; this spec is a **finalization pass**, not
new writing. Small scope, deliberately — do not expand it.
**Depends on:** the two content items in §1 depend on Spec 06 (Chapter 4)
being drafted, since they need to state what was actually built vs deferred.
The bibliography/build-hygiene items in §2 have no dependency and can run
now, in parallel with anything else.
**Governing contract:** none new — this spec is grounded directly in what
was found reading the actual `.tex` source (see §0), not in a tool SPEC.md.

## 0. What was actually checked (2026-09-22, read directly, not assumed)

- `grep -rniE "TODO|FIXME|placeholder|to be added|XXX|TBD"` across
  `chapters/*.tex pre/*.tex pos/*.tex`: only two real hits outside Chapter 4
  (which Spec 06 already owns) — one comment block each in
  `chapters/01-introduction.tex:64` and `chapters/03-methodology.tex:257`.
  Both are honest, already-hedged forward-pointers ("subject to revision
  based on ablation results", "keep in sync with Chapter 3"), not silent
  gaps — but they should be resolved to a definite statement once Chapter 4
  is written, not left open in the final submission.
- Bibliography: verified in `bib/references.bib` — `caldara2022geopolitical`,
  `dong2024fnspid`, `baumgartner2020pushshift`, `zhang2025macroalpha`,
  `aronson2007evidence`, `kirtac2024sentiment`, `iacovides2025findpo`,
  `liu2024gprcurrency`, `melone2026geopolitical`, and `xiao2024tradingagents`
  (cited in `02-theoretical-foundation.tex:76,108` and
  `05-conclusion.tex:43`) are all present. **No bibliography gap found** —
  do not spend time on this; it was a false lead from a stale note in
  [`specs.md`](../../../../specs.md)'s archive text (which used the key `xiao2025tradingagents`,
  a typo relative to the actual `xiao2024tradingagents`).
- `pre/errata.tex` and `pre/acknowledgments.tex` are unfilled ABNT template
  boilerplate, but **both are already commented out** in `main.tex`
  (lines 281, 293) — not live in the build. **No action needed** unless the
  user decides to add real acknowledgments text, which is a personal-content
  decision for the user, not an agent task.
- `pre/dedication.tex` and `pre/epigraph.tex` are genuinely finished (real
  content, not template text).
- `pre/abstract.tex` and `pre/resumo.tex` are genuinely finished (this
  corrects the stale [`CLAUDE.md`](../../../../CLAUDE.md) note that called the abstract a
  placeholder — it is not, as of this check).
- `pre/catalog-card.tex` and `pre/approval-sheet.tex` exist as `.tex` but
  their compiled PDFs are correctly deferred (`main.tex` lines 270-271,
  284-285 — `\includepdf` commented out, waiting on the library/defense).
  **Not a deposit blocker** — confirm this understanding still holds (ask
  the program/library if a pre-defense deposit needs these; if not, leave
  as-is).

## 1. Content items (depend on Spec 06)

- **`chapters/01-introduction.tex:64`** — once Chapter 4 states the actual
  delivered scope (Medium: price-only baseline; hybrid deferred to future
  work per Spec 06 §4), update this objective's note to reflect what
  actually shipped, or leave the hedge if the language already accommodates
  a Medium outcome without edit (it currently reads as aspirational-but-
  honest — re-read it after Chapter 4 is drafted and decide, don't edit
  blind).
- **`chapters/03-methodology.tex:257`** — same treatment: the five-sub-model/
  F1–F7 decomposition is the *full* (Full-scope) target; if Medium ships,
  confirm this section's language still correctly describes the target
  architecture (design-level, asset-agnostic) without overclaiming it was
  *evaluated* — Chapter 4 and Chapter 5 (future work) carry the "what
  actually ran" claim, Chapter 3 stays a methodology specification. Usually
  this means: no edit needed, just verify the framing still holds once
  Chapter 4's real content exists next to it.
- Do not turn this into a rewrite pass — Chapters 1–3 and 5 are frozen for a
  reason (advisor feedback already incorporated, see the `monografia-
  clarify-literature`/`monografia-abstract-tighten` PR history in `git log`).
  Touch only what Chapter 4's actual content requires for consistency.

## 2. Build-hygiene items (no dependency, can run now)

- `make pt-scan` across the whole document — confirm no accidental
  Portuguese leaked outside `pre/resumo.tex` (the one intentional pt-BR
  section, ABNT-required).
- `make verify` — page count, undefined-citation scan, chapter-start pages.
  Run this now on the current (Chapter-4-placeholder) build to catch any
  pre-existing issue early, then again after Spec 06 lands Chapter 4
  content, since that's the highest-risk chapter for a new undefined
  citation or formatting break.
- `make rebuild` (distclean + full rebuild) at least once before the
  2026-09-25 professor-send date (per [`00-PLAN.md`](../../00-PLAN.md)'s schedule) — a stale
  `build/` directory silently masking a real compile error is the last thing
  you want discovered on submission day.
- Confirm `\includepdf` for catalog-card/approval-sheet stay correctly
  commented out (don't accidentally enable them without the real PDFs —
  that would break the build, not silently degrade it, so this is a
  fail-fast check LaTeX gives for free, but worth a deliberate look before
  the final `make rebuild`).

## 3. Definition of done

- `chapters/01-introduction.tex:64` and `chapters/03-methodology.tex:257`
  reviewed against the final Chapter 4 content and either left as correctly
  hedged or updated — a deliberate decision, recorded (even just in the PR
  description), not a silent skip.
- `make pt-scan` clean.
- `make verify` clean (no undefined citations, page count sane).
- `make rebuild` succeeds from a clean `build/`.
- [`00-PLAN.md`](../../00-PLAN.md) §1 updated to note this pass is done, ahead of the
  2026-09-25 professor-send checkpoint in the 7-day schedule.
