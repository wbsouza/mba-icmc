# Lessons learned — Spec 05d: algo-analyze thesis figures

**Sourced from the parallel Spec 05 analysis lanes opened as stacked PRs**
(05b significance, 05c ablation, 05d figures).

**Use the plotting library, not a hand-rolled PDF writer.** The first direction
nearly drifted toward custom PDF output; correcting the lane to matplotlib gave
proper vector PDFs, predictable LaTeX sizing, and much simpler tests.

**A shared style module is worth it once the second figure family is visible.**
`algo_analyze._style` centralizes the Agg backend, rcParams, colors, and figure
size so later thesis plots can reuse the same settings instead of duplicating
plot styling across modules.

**Validate PDF structure, not pixels.** The tests assert that a file is a
non-empty PDF with page structure and no embedded raster image subtype. That
checks the important contract for thesis figures while avoiding brittle pixel
snapshots.

**A stale virtualenv console script can masquerade as a missing dependency.**
`python -m pytest` saw matplotlib while the `pytest` console script did not; the
script shebang pointed at a different checkout. Reinstalling pytest through uv
repaired the script, and fresh worktrees passed normally.
