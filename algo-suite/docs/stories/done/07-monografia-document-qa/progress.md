# Progress — Spec 07 (monografia document QA)

**§1 (content items) must wait until Spec 06 lands. §2 (build hygiene) has no dependency.**

- [x] §2 build-hygiene pass, done 2026-09-25 (recorded in `../../00-PLAN.md` §1):
      `make pt-scan` clean, `make verify` clean (86 pages, 0 undefined
      citations/references), `make rebuild` succeeds from a clean `build/`, and
      `\includepdf` for catalog-card/approval-sheet is confirmed still commented out.
      Fixed on the way: `monografia/main.tex` now loads `amsmath` and no longer
      loads `chemmacros`. Re-run `make verify`/`make rebuild` once Spec 06 adds
      Chapter 4 content (spec §2).
- [ ] §1: review `chapters/01-introduction.tex:64` and `chapters/03-methodology.tex:257`
      against the final Chapter 4 (blocked on Spec 06)

- [ ] Read Spec 06's finished Chapter 4 for QA scope
- [ ] Define QA checklist (TBD — read `spec.md` for specifics not yet captured here)
- [ ] `make verify` + `make pt-scan` clean (from `monografia/`)

## Closed, 2026-09-28

Moved to `done/` for what actually shipped: the §2 build-hygiene pass, plus
repeated ad-hoc `make verify`/`make rebuild` checks throughout tonight's
Chapter 4/5 work (0 undefined citations, 153 pages, clean every time).

The §1 content-consistency review and a written, reusable QA checklist are
real, wanted, planned work — not abandoned. It continues as
`../../planned/27-monografia-formal-qa-checklist/spec.md`.
