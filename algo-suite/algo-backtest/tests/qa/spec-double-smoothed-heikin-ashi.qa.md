# QA procedure — double-smoothed Heikin-Ashi F1 candidate

Operate the public CLI from `algo-suite`. The executable QA script should return
nonzero on a failed assertion and print the resulting run IDs and ablation output
paths. A successful no-trade backtest is valid; do not manufacture trades to make
the comparison look useful.

1. Run the focused acceptance feature and its step definitions. Require all
   scenarios to pass, including the hand-computed HA seed and recurrence, reversed
   extrema classification, tie-to-down, invalid configuration, both smoothing
   passes' readiness, and closed-bar higher-timeframe handling. The indicator tests
   must exercise native LEAN moving averages; test doubles alone do not establish
   the native smoothing contract.
2. Use fresh run directories and identical EURUSD minute bars with enough history
   for 7 completed hourly candles plus baseline warm-up. Use a deterministic fixture
   or existing historical archives; record the window and input hashes/provenance.
   The native acceptance fixture must cover changing prices and an unfinished
   hourly bucket. Materialize through `algo-backtest materialize` when using
   prepared raw data. Completed real CLI runs can be inspected without rerunning
   expensive backtests, provided their manifests and required artifacts are present.
3. Run `algo-backtest run --strategy baseline --symbol EURUSD --from <start>
   --to <end>` and the same command with `--strategy baseline-dsha`, using the
   identical fixture, account settings, and frozen model artifact. Require exit
   code zero, different run IDs, and complete run artifacts for each. Verify that
   the stored effective configuration identifies the requested perception source.
4. Inspect available decision artifacts. Before both candidate timeframes are
   ready, no candidate-derived F1 direction may be consumed as if ready. Once
   ready, the direction values must be either -1 or +1. Higher-timeframe features
   must use the last completed consolidated candle. Verify this timing invariant
   in the focused native integration scenario if decision artifacts do not expose
   the per-bar indicator state. The existing trend-strength calculation remains
   unchanged between configurations.
5. Run `algo-analyze ablation --runs <baseline-run-id> --runs <candidate-run-id>`
   with the same results directory. Require exit code zero and an ablation table
   containing exactly the two requested run IDs. Persist its CSV/Markdown outputs
   and the commands used as reproducible story evidence. This is an actual run
   comparison, not a table assembled from invented metrics.
6. Label the comparison explicitly as a perception-source ablation with the
   existing EMA-trained F7 model frozen. Do not describe it as a comparison of
   independently retrained models or as evidence of profitability. Record that
   smoothing pass 2 is the MT4 default of 2 (the historical Java system used 1),
   ties classify down, and LEAN warm-up/bar-boundary behavior may differ from MT4.
7. Run the repository's `make check`, the configured complexity/coverage gate,
   and mutation tests for the new perception logic. Capture command exit codes,
   measured scores, and survivor dispositions. Missing dependencies or unavailable
   historical data are explicit failures/limitations, never claimed passes.

## Executable artifact check

From `algo-suite`, after the paired runs finish:

```sh
uv run python algo-backtest/tests/qa/run_double_smoothed_heikin_ashi_qa.py \
  --data-root <data-root> \
  --runs baseline/<stamp> --runs baseline-dsha/<stamp> \
  --out <evidence-directory> --code-revision <clean-commit-used-for-both-runs>
```

This checks successful manifests, matching windows/parameters, actual engine model
hashes, source configuration provenance, consumed F1 directions, changed decisions,
unchanged comparable trend strength, and the public ablation CLI. It persists compact
real artifacts and input hashes. Both runs must contain `strategy-config.json`;
a missing engine artifact fails rather than falling back to a QA-generated snapshot.
It also requires a later first candidate decision and fewer candidate decision rows.
The exact native warm-up boundary is checked from measured native output by
`make check-perception`, since the default offline gate has no LEAN runtime.
Native integration tests and the workspace/complexity/mutation gates remain separate
mandatory stages; this script's pass does not claim those stages passed.
