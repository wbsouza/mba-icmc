# Progress — Spec 06 (monografia Chapter 4)

**Do not start until Specs 01–05 (all lanes) and Spec 04h are landed.**

**Update September 26, 2026:** setup and pilot limitations are now drafted.
Chapter 3 separates the target protocol from current execution and documents
all twelve workflow stages. Chapter 4 records the fitting/calibration/test
split and the baseline zero-trade replay without claiming a scientific result.
Chapter 5 now limits conclusions to demonstrated evidence. Paired results,
coverage analysis, ablations, and statistical validation remain incomplete.
See Tasks 09–11 and the experimental workflow.

- [x] §sec:experimental-setup rewritten with current pilot status (final archive review remains)
- [ ] §sec:coverage-results written (Spec 02 coverage matrix + derived window)
- [ ] §sec:baseline-results written with real price-only numbers
- [ ] §sec:hybrid-results written with real hybrid numbers (needs Spec 04h)
- [ ] §sec:ablations written (needs Spec 05c)
- [ ] §sec:zhang-comparison written
- [ ] §sec:experimental-threats written
- [ ] `make verify` + `make pt-scan` clean (from `monografia/`)

## Documentation validation — September 26, 2026

- `make verify`: 90-page PDF, no undefined citations or references.
- `make pt-scan`: reviewed as a language inventory; front matter, original-language
  bibliography titles, and proper names remain. New chapter prose is English.
- New and edited Markdown local links resolve; `git diff --check` passed.
- Rendered Chapter 4 split table visually checked. Existing manuscript layout
  warnings remain outside this workflow update; no claim of full final QA.
- Scientific Agent Skills and the primary DSR paper are cited in the manuscript;
  the review does not replace statistical validation or a complete source audit.
