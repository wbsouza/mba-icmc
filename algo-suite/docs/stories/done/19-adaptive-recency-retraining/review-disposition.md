# Story 19 review disposition for the parallel plan

Status: proposed September 28, 2026; all ten dispositions accepted as proposed
by the user on September 28, 2026 (implementation handoff). The original
[review](review.md) remains unchanged as review history. T1 records this
approved resolution in the frozen protocol.

| Review item | Proposed disposition | Task / approval boundary |
| --- | --- | --- |
| 1: precomputed bundles first | Keep prepared replay as a parity/reproduction path. The requested consume/train/load cycle remains in scope; moving native coordination out requires explicit approval. | T10/T12 feasibility gate; no invented LEAN pause API. |
| 2: F equals session 2 | Keep the separate calibration spans for every matched policy. Treat session 2 as an external reproduction control, not silently rename it F. Changing only F would confound threshold refresh with calibration differences. | T1 records the choice; a shared historical initial epoch requires a revised all-policy schedule. |
| 3: H4 second base | Defer from the five-run primary matrix. An H4 replication can be separately approved and budgeted, not selected because its observed loss was smaller. | T1 decision; no ten-run claim until amended. |
| 4: prediction quality | Register E/U log-loss, Brier and directional accuracy on common mature rows as secondary model endpoints; paired daily equity remains primary. | T1 definitions, T16 report; do not restrict to winners or executed trades. |
| 5: concrete data inputs | Name complete M1 partitions, feature cache identities and per-source availability watermarks. On-disk month completion never overrides the simulated row cutoff. GDELT is not a prerequisite for the price-only lane. | T2; news requires a separate registered extension. |
| 6: effective N comparison | Show E effective N beside R row counts for each fitting stage/epoch, without calling either independent observations. | T4/T16. |
| 7: compute budget | Freeze measured resource limits at T1 after read-only host/container inventory. Historical fit/run timings are estimates, not a deadline or permission to occupy six containers. | One shared semaphore across the three studies; no benchmark run now. |
| 8: determinism | Require equal semantic model and decision payloads for pinned inputs. Keep wall-clock duration and run IDs as auditable volatile fields outside the equality digest. | T9/T12 regression cases; do not promise identical full manifests with different timestamps. |
| 9: epoch UI | Defer new chart markers and viewer controls. Existing model/entry-epoch records and tabular reports are the first delivery; expanding the viewer needs new atomic tasks before execution. | T13/T16 remain required; Story 22 viewer work is not evidence for this request. |
| 10: epoch thresholds | Persist and report both actual thresholds, row counts and changes by epoch. Charts can be added to T16's report only when they use those same archived values. | T8/T16; threshold jumps are diagnostics, not evidence of drift. |

This disposition distinguishes safe evidence refinements from changes to the
research question. No review request is silently treated as implemented or
approved. If a different lifecycle/control/H4/UI choice is selected, revise
specification, design, traceability, tasks and trial budget together before code.
