# Story 26 — Confluence chain registered fourteen-cell study

Status: planned. Continuation of Story 21 (confluence chain), closed
2026-09-28 for what it actually delivered: the full engine (named agreement
terminal, F1 momentum-context variant, causal monthly intensity-quantile
snapshots, F4 relative-intensity trigger mode, F6 bar-count exit, the pure
bar-count expiry lifecycle, drift controls, the horizon-unit re-derivation
tool, the data-population/point-in-time-availability preflight gate, and the
deterministic fourteen-cell manifest generator), hardened across three
mutation-testing passes, with a real, traced production bug found and fixed
in the preflight gate's data-layout check. See
`../../done/21-confluence-chain/progress.md` for the full record.

## Problem statement

The engine and its manifest generator are done and gated (native LEAN
integration scenarios genuinely green). The registered study itself — T19,
actually launching all fourteen cells (seven arms × two clocks) over the
registered window and running the paired statistical comparison — was not
completed, and neither was T18 (`compare.py`, the comparison report) or the
Chapter 4/5 write-up.

## Goals

- [ ] Confirm the news-intensity trigger's point-in-time availability
      gap is actually closed (the `available_at` provenance fix, PR #95,
      merged 2026-09-28) before launching any news-dependent arm — the
      engine correctly refused to fabricate this earlier rather than run
      ungated.
- [ ] Launch all fourteen registered cells for real (this session's
      `run/21-launch-2026-09-28` worktree already exercised the launch
      harness end to end and found/fixed four real bugs in
      `preflight.py`/`make_cells.py`/`run_cells.py` along the way — reuse
      that proven harness, don't rebuild it).
- [ ] Build `compare.py` (T18) and run the registered paired comparison
      against the drift/single-signal controls.
- [ ] Feed the result into Chapter 4/5.

## Out of scope

- Anything already delivered by Story 21 (the engine, the manifest
  generator, the preflight gate, the hardening passes) — this story only
  picks up the actual registered run and its comparison report.

## Notes

Every other filter/pattern combination tested this session (candlesticks,
trend, momentum, news alone) underperformed a plain baseline once actually
gated and tested for real, rather than assumed. The honest expectation for
this confluence chain is the same: it may well not beat its drift control
either. That is a legitimate result to register, not a reason to skip
running it.
