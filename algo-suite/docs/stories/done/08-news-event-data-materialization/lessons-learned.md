# Lessons learned — Story 08 (news/event data materialization)

The original spec assumed the `algo-download`/`algo-transform`/`algo-score`
HTTP pipeline would be the materialization path. That approach was
superseded mid-story by a BigQuery CTAS-based one (full-table materialize
once, cheap per-batch/day extraction after) — cheaper and far more reliable
than re-scanning GDELT's public HTTP source repeatedly. The spec's original
architecture section is stale; the Assumptions table and Reproducibility
section (added mid-story) are the parts that actually reflect what shipped.

The real gap found wasn't in the download/materialization mechanics at
all — it was a provenance gap the original spec didn't anticipate: the
event model dropped GDELT's own `DATEADDED` column (when GDELT's pipeline
actually indexed an event) and kept only `event_date` (when the event
happened in the world). Nothing in the original acceptance criteria
required distinguishing these two timestamps, but their conflation is a
real look-ahead-bias risk for any downstream backtest — a data-contract
gap invisible until you actually asked "when did the strategy really have
this information," not "when did the event occur."

What would be done differently: write the point-in-time-availability
requirement into the spec from day one for any event-stream data source,
rather than discovering it as an afterthought once the perception layer was
already built against `event_date` alone. This class of bug (correct data,
wrong timestamp semantics) is easy to miss because every individual field
looks valid — it only shows up when someone asks specifically "could a
real trader have known this yet."

The 10-year full backfill and GPR's canonical layer took longer than a
single session allows, once the deadline moved up; scoping the *registered
study window* as the actual done-criterion (rather than the full historical
range) let the rest of the pipeline actually get proven working end to end
under real time pressure, instead of stalling on completeness. The
remaining range is real, wanted work — see
`../../planned/24-gdelt-gpr-full-materialization/spec.md` — not something
this closure quietly drops.
