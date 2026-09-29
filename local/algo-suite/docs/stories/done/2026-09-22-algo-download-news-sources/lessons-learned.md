# Lessons learned — Spec 01: algo-download GDELT + GPR raw adapters

**Sourced from the specifier → architect → coder → cleaner → hardener → QA
pipeline commits on `algo-score-event-features`** (`837399e`, `2605bc3`,
`909bdd7`, `de945ae`, `6535528`, `dedfbd8`, `cdff251`).

**Separate "confirmed real-feed fact" from "specifier judgment call."**
`2605bc3` had to walk back an overclaim in `SPEC.md`'s GDELT scope note: the
Events-vs-GKG table decision was written up as "confirmed" when it was
actually a specifier judgment call tied to Spec 02's stated schema, not
something verified against the live feed. State the rationale explicitly
instead of borrowing the confidence level of a real-feed check for a design
decision — the next reader needs to know which claims were empirically
verified and which were reasoned.

**mutmut/radon/symilar became the settled Python mutation/CRAP/DRY toolchain
this session** (`dedfbd8`), mirroring an answer already settled on a sibling
project (`odoo-oikofy-addons`) since the team constitution's language table
only covered Go/Clojure/Java. CRAP gate (complexity × (1-coverage), threshold
≤10) passed clean on first pass here — all touched functions graded A/B,
95-100% coverage. `symilar` (via pylint) flagged ~14% duplication across the
`dukascopy`/`gdelt`/`gpr` adapters' shared `__init__`/`fetch`/`_get`
boilerplate — logged as follow-up debt rather than fixed under the deadline
pressure (Sept 29 submission). Not every real finding needs fixing
immediately; logging it with a concrete trigger is a legitimate outcome.

**QA verification doesn't always mean a dedicated `.qa.md` procedure doc.**
Spec 01's QA pass (`cdff251`, "Finalize QA verification for raw adapters")
closed out via README updates and the offline BDD suite going green —
no standalone QA markdown was produced, unlike Spec 02/03/05a which each got
one. Don't assume a missing `tests/qa/*.qa.md` file means a spec wasn't
QA-verified; check the actual commit/README trail before concluding a gap.
