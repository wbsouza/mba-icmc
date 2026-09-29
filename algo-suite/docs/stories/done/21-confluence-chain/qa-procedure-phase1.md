# Story 21 — Phase 1 QA procedure (T1..T5: chain contracts)

You are a person operating the system. Prove that each Phase 1 component works
through its real interfaces: the pytest-bdd selections, the Python REPL and the
`algo-backtest` CLI. Every step names the command, where to run it and what you
must observe. A step whose expected outcome you do not observe is a failure to
report, not a step to skip. Nothing here runs LEAN or touches NAS data.

Setup (every shell):

```sh
export TMPDIR=/home/wellington/.cache/claude-tmp; mkdir -p "$TMPDIR"
cd /tmp/mba-impl-21/algo-suite          # branch feat/21-confluence-chain
uv sync --all-packages
```

Phase 1 does not register any new strategy or YAML key with the loader
(`strategies.py`, `chain/wiring.py` are integration-owned, T11/T12), so
`algo-backtest explain-strategy` cannot yet show `momentum_context`,
`intensity_relative`, `agreement` or `exit_after_bars`. Steps 11 and 12 use the CLI
only as the legacy-compatibility probe. Every REPL example below constructs the new
collaborators directly, the way `chain/wiring.py` will after T12.

## Step 1 — Baseline and collection sanity

```sh
uv run pytest algo-backtest/tests -q --co -m 'not integration' | tail -1
uv run pytest algo-backtest/tests/steps/test_confluence_agreement.py \
  algo-backtest/tests/steps/test_confluence_momentum.py \
  algo-backtest/tests/steps/test_confluence_history.py \
  algo-backtest/tests/steps/test_confluence_relative_intensity.py \
  algo-backtest/tests/steps/test_confluence_capital_plan.py -q --co | tail -1
```

Expected: the first line prints the pre-phase baseline count recorded in
`progress.md` plus the five new step files' cases. The second selection collects
exactly 45 + 38 + 32 + 40 + 25 = 180 cases (the feature files' scenario plus
Examples-row counts: agreement 45, momentum 38, history 32, relative intensity 40,
capital plan 25) and exits 0. A count of 0 or an import error means a step file is missing.

## Step 2 — T1: the agreement terminal (pytest)

```sh
uv run pytest algo-backtest/tests/steps/test_confluence_agreement.py -q
```

Expected: all collected cases pass, 0 failed, 0 skipped. Then open
`algo-backtest/tests/features/confluence_agreement.feature` and confirm the four
`F5 and F6 vetoes short-circuit` rows ran (they appear in `-v` output as
`test_..._the_gates_pass_...`, `..._f5_vetoes_...`, `..._f6_vetoes_...`).

## Step 3 — T1: the agreement terminal (REPL)

```sh
uv run python - <<'EOF'
from datetime import UTC, datetime
from algo_backtest.chain.model import ExecutionState, FilterResult, Recommendation as R
from algo_backtest.chain.terminal import AgreementTerminalDecision

voters = {"f1_trend": "F1_trend", "f2_indicator": "F2_indicator",
          "f3_pattern": "F3_pattern", "f4_news_context": "f4_news_context"}
terminal = AgreementTerminalDecision(required_filters=("f1_trend", "f4_news_context"),
                                     voter_name_map=voters)
def state(*votes):
    s = ExecutionState(timestamp=datetime(2016, 4, 5, 10, tzinfo=UTC), pair="EURUSD", features={})
    s.filter_results = [FilterResult(filter_name=n, recommendation=R(v), reason="qa") for n, v in votes]
    return s
print(terminal.decide(state(("F1_trend", "SELL"), ("f4_news_context", "SELL"), ("f5_risk_guard", "ABSTAIN"))))
print(terminal.decide(state(("F1_trend", "BUY"), ("f4_news_context", "SELL"))))
print(terminal.decide(state(("F1_trend", "BUY"), ("f4_news_context", "BUY"), ("F2_indicator", "HOLD"))))
print(terminal.decide(state(("F1_trend", "ABSTAIN"), ("f4_news_context", "NEUTRAL"))))
try:
    AgreementTerminalDecision(required_filters=("f1_trend", "f5_risk_guard"), voter_name_map=voters)
except ValueError as exc:
    print("rejected:", exc)
try:
    terminal.decide(state(("F1_trend", "BUY")))
except ValueError as exc:
    print("rejected:", exc)
EOF
```

Expected, in order: `Decision.SELL`, `Decision.HOLD`, `Decision.HOLD`,
`Decision.HOLD`; then a `rejected:` line naming `'f5_risk_guard'` as a gate; then a
`rejected:` line saying `required voter 'f4_news_context' ... did not run` and listing
`filters that ran: ['F1_trend']`. No traceback escapes.

## Step 4 — T2: the momentum context (pytest)

```sh
uv run pytest algo-backtest/tests/steps/test_confluence_momentum.py -q
uv run pytest algo-backtest/tests/steps/test_f1_trend.py -q
```

Expected: both selections pass with 0 failed. The second proves the original
three-feature F1 is untouched (its own feature file is unchanged in `git diff`).

## Step 5 — T2: the momentum context (REPL)

```sh
uv run python - <<'EOF'
from datetime import UTC, datetime, timedelta
from algo_backtest.chain.filters.f1_trend import (
    MomentumHistory, parse_momentum_context_config, F1MomentumContextFilter)
from algo_backtest.chain.model import ExecutionState

config = parse_momentum_context_config({"lookback_bars": 480}, strategy="qa")
history = MomentumHistory(lookback_bars=config.lookback_bars)
t0 = datetime(2016, 3, 1, tzinfo=UTC)
f = F1MomentumContextFilter(config=config, history=history)
def apply(at):
    return f.apply(ExecutionState(timestamp=at, pair="EURUSD", features={}))
for k in range(480):                       # 480 closes: one short of L+1
    history.push(t0 + timedelta(hours=k), 1.2 if 0 < k else 1.1)
r = apply(t0 + timedelta(hours=479)); print(r.recommendation, r.metadata["momentum_status"], r.reason)
history.push(t0 + timedelta(hours=480), 1.1055)   # close[t] / close[t-480] - 1 = 0.005
r = apply(t0 + timedelta(hours=480)); print(r.recommendation, r.veto, r.enrichment["momentum_return"])
try:
    history.push(t0 + timedelta(hours=480), 1.2)
except ValueError as exc:
    print("rejected:", exc)
EOF
```

Expected: first line `Recommendation.ABSTAIN WARMUP momentum_context WARMUP: 480 of 481 closes collected; ...`;
second line `Recommendation.BUY False 0.005` (allow `0.004999999...` from float
rounding; the feature asserts with `approx`); third line a `rejected:` message that
says the duplicate close_time `is not after the last close`.

## Step 6 — T3: monthly intensity snapshots (pytest)

```sh
uv run pytest algo-backtest/tests/steps/test_confluence_history.py -q
```

Expected: all cases pass, 0 failed. Look at `-v` output for the case names
`reference_daily_archive_gives_q10_0_195_and_q90_1_355`, `mid_month_start`,
`rows_that_arrive_after_the_snapshot_froze`, `gap_inside_a_documented_market_closure`
and `collection_that_started_inside_the_window_reports_warmup`.

## Step 7 — T3: hand-checked quantiles (REPL)

The archive: 30 daily bars closing 00:00 UTC on 2016-03-02..2016-03-31, every
multiple of 0.05 from 0.05 to 1.50 exactly once. Sorted, linear interpolation at
index (n-1)·q: index 2.9 between 0.15 and 0.20 gives q10 = 0.195; index 26.1 between
1.35 and 1.40 gives q90 = 1.355.

```sh
uv run python - <<'EOF'
from datetime import UTC, datetime, timedelta
import json, numpy as np
from algo_backtest.chain.intensity_history import IntensityHistory, IntensityObservation

values = [0.05 * k for k in (30,5,22,1,18,29,12,3,26,8,15,20,4,25,7,2,28,11,19,6,24,14,9,27,17,13,23,10,21,16)]
history = IntensityHistory(clock_minutes=1440, collection_started_at=datetime(2016, 1, 1, tzinfo=UTC))
for i, v in enumerate(values):
    closed = datetime(2016, 3, 2, tzinfo=UTC) + timedelta(days=i)
    history.record(IntensityObservation(bar_closed_at=closed, available_at=closed, intensity=v, source_id="qa"))
snap = history.snapshot_for(datetime(2016, 4, 17, 10, tzinfo=UTC))
print(snap.status, snap.cutoff, snap.window_start, snap.sample_count, snap.q_low, snap.q_high)
print("numpy agrees:", np.quantile(values, 0.10, method="linear"), np.quantile(values, 0.90, method="linear"))
again = history.snapshot_for(datetime(2016, 4, 1, tzinfo=UTC))
print("frozen:", again == snap, len(snap.source_hash))
print(json.dumps(snap.as_mapping(), sort_keys=True)[:120], "...")
EOF
```

Expected: `READY 2016-04-01 00:00:00+00:00 2016-03-02 00:00:00+00:00 30 0.195 1.355`
(the two quantiles may print as `0.19500000000000003` / `1.355` — compare with the
numpy line, which must agree to 1e-12); `frozen: True 64`; a JSON mapping whose keys
are the twelve provenance fields listed in the feature file.

## Step 8 — T4: relative F4 (pytest)

```sh
uv run pytest algo-backtest/tests/steps/test_confluence_relative_intensity.py -q
uv run pytest algo-backtest/tests/steps/test_f4_news_context.py -q
```

Expected: both pass with 0 failed. The second is the story-14 regression suite for
the static and sentiment modes; the only permitted diff in its feature file is the
`unknown source` example's choices list now reading
`['intensity', 'intensity_relative', 'sentiment']` (see the gap list in the
specifier report). Any other change to `f4_news_context.feature` is a finding.

## Step 9 — T4: relative F4 (REPL)

```sh
uv run python - <<'EOF'
from datetime import UTC, datetime
from algo_backtest.chain.filters.f4_news_context import (
    F4NewsContextFilter, NewsContextIndex, parse_news_context_config)
from algo_backtest.chain.intensity_history import IntensitySnapshot
from algo_backtest.chain.model import ExecutionState

config = parse_news_context_config({"event_intensity_veto_threshold": -0.5,
    "sentiment_direction_threshold": None, "direction_source": "intensity_relative",
    "intensity_sign": -1}, strategy="qa")
at = datetime(2016, 4, 5, 10, tzinfo=UTC)
def run(intensity, q_low, q_high, status="READY"):
    snapshot = IntensitySnapshot(cutoff=datetime(2016, 4, 1, tzinfo=UTC),
        window_start=datetime(2016, 3, 2, tzinfo=UTC), clock_minutes=60, q_low=q_low, q_high=q_high,
        sample_count=30, max_closed_at=datetime(2016, 3, 31, 23, tzinfo=UTC),
        max_available_at=datetime(2016, 3, 31, 23, tzinfo=UTC), source_hash="ab12",
        quantile_method="linear", schema_version=1, status=status)
    index = NewsContextIndex(event_intensity={at: intensity}, sentiment_polarity={}, sentiment_source_present=False)
    f = F4NewsContextFilter(index=index, config=config, snapshots={snapshot.cutoff: snapshot},
                            availability={at: at})
    r = f.apply(ExecutionState(timestamp=at, pair="EURUSD", features={}))
    return r.recommendation.value, r.veto
print(run(0.8, 0.2, 0.8), run(0.2, 0.2, 0.8), run(0.5, 0.2, 0.8))
print(run(0.4, 0.5, 0.5), run(0.6, 0.5, 0.5))
print(run(5.0, None, None, status="WARMUP"))
print(run(-0.7, 0.2, 0.8))
EOF
```

Expected lines: `('SELL', False) ('BUY', False) ('NEUTRAL', False)`;
`('HOLD', False) ('HOLD', False)`; `('HOLD', False)`; `('ABSTAIN', True)` (the veto
still fires first). If the constructor's keyword names differ from the ones the
coder chose, read the module docstring of `f4_news_context.py`, adjust only the
keyword names, and record the actual names in the QA report.

## Step 10 — T5: the F6 bar-count plan (pytest)

```sh
uv run pytest algo-backtest/tests/steps/test_confluence_capital_plan.py -q
uv run pytest algo-backtest/tests/steps/test_f6_capital_mgmt.py -q
```

Expected: both pass with 0 failed; `f6_capital_mgmt.feature` is unchanged in
`git diff` (legacy plan byte for byte).

## Step 11 — T5: the F6 bar-count plan (REPL)

```sh
uv run python - <<'EOF'
import algo_backtest.chain.filters.f6_capital_mgmt as f6
from algo_backtest.chain.filters.f6_capital_mgmt import capital_mgmt_mapping, parse_capital_mgmt_config
base = {"risk_per_trade": 0.03, "stop_loss_pips": 20.0, "pip_value_per_lot": 10.0,
        "lot_notional_units": 100000, "assumed_leverage": 30}
legacy = parse_capital_mgmt_config(base, strategy="qa")
print("legacy:", legacy.exit_after_bars, capital_mgmt_mapping(legacy)["targets"])
timed = parse_capital_mgmt_config({**base, "stop_distance_source": "atr", "atr_multiplier": 2.0,
        "targets": [], "trail_stops": [], "exit_after_bars": 4}, strategy="qa")
print("timed:", timed.exit_after_bars, timed.targets, timed.trail_stops, timed.min_reward_risk)
for bad in (True, 4.5, 0, -4, "four"):
    try:
        parse_capital_mgmt_config({**base, "exit_after_bars": bad}, strategy="qa")
    except ValueError as exc:
        print("rejected:", exc)
print("open of bar t+N" in f6.__doc__, "close of bar t+N-1" in f6.__doc__)
EOF
```

Expected: `legacy: None [{'at_level_ratio': 2.0, 'close_fraction': 1.0}]`;
`timed: 4 () () None`; five `rejected:` lines each containing
`capital_mgmt.exit_after_bars must be a positive integer` and `got <value>`;
finally `True True`.

## Step 12 — Legacy CLI and strategies untouched (CC-20)

```sh
uv run algo-backtest explain-strategy news-rule | head -40
uv run algo-backtest explain-strategy hybrid | grep -c capital_mgmt
uv run pytest algo-backtest/tests/steps/test_filter_chain_mechanics.py \
  algo-backtest/tests/steps/test_chain_wiring.py \
  algo-backtest/tests/steps/test_strategy_explain.py \
  algo-backtest/tests/steps/test_strategies.py -q
git -C /tmp/mba-impl-21 diff --stat main -- algo-suite/algo-backtest/src/algo_backtest/strategies.py \
  algo-suite/algo-backtest/src/algo_backtest/chain/wiring.py algo-suite/algo-backtest/src/algo_backtest/engine
```

Expected: `explain-strategy news-rule` prints the story-14 resolved config with
`direction_source: intensity` and no `intensity_relative`, `momentum_context`,
`agreement` or `exit_after_bars` line; the `grep -c` prints a nonzero count (the
CLI still resolves `capital_mgmt`); the regression selection passes; the `diff
--stat` prints nothing (Phase 1 changed no integration-owned file).

## Step 13 — Quality gates for the touched packages

```sh
uv run ruff check algo-backtest/src/algo_backtest/chain algo-backtest/tests/steps
uv run ruff check --select C901 algo-backtest/src/algo_backtest/chain
uv run mypy --strict algo-backtest/src/algo_backtest/chain
make lint type
uv run pytest algo-backtest/tests -q -m 'not integration' | tail -3
```

Expected: ruff and mypy report no findings on `algo-backtest`; the full offline
run reports 0 failed and a passed count equal to the Step 1 baseline plus the
Phase 1 cases (record both numbers in the QA report; do not sum overlapping
selections). Known at the Phase 1 close-out (2026-09-28): the workspace-wide
`make lint type` fails on pre-existing files outside `algo-backtest`
(`docs/stories/done/**`, `scripts/bigquery_*.py`, `tools/mutation_harness.py`,
an `algo-viewer` fixture); a separate chore commit on the integration branch owns
that. A finding *inside* `algo-backtest` is a Phase 1 failure; a finding outside it
is not.

## Checklist (fill in the QA report, one line per task)

| Task | Component | Steps | Pass criterion |
| --- | --- | --- | --- |
| T1 | `AgreementTerminalDecision` in `chain/terminal.py` | 2, 3 | unanimity BUY/SELL, every HOLD path, empty/duplicate/unknown/gate names and missing/duplicate results rejected, F5/F6 veto through `FilterChain.run` (terminal consulted 0 times) |
| T2 | `momentum_context` variant in `chain/filters/f1_trend.py` | 4, 5 | sign votes at L=480 and L=120, WARMUP below L+1, malformed closes rejected, original F1 tests still green |
| T3 | `chain/intensity_history.py` | 6, 7 | q10 0.195 / q90 1.355 on the reference archive, cutoff/window rules, frozen month, WARMUP vs. failure, provenance round trip |
| T4 | `intensity_relative` in `chain/filters/f4_news_context.py` | 8, 9 | sign -1 mapping with boundaries, degenerate HOLD, WARMUP HOLD, late availability raises, static/sentiment modes unchanged |
| T5 | `exit_after_bars` in `chain/filters/f6_capital_mgmt.py` | 10, 11 | legacy round trip, invalid N rejected with remediation, time plan without targets or reward:risk veto, floors/spread/sizing/margin still applied, docstring records D5 |
| all | legacy CLI, wiring, gates | 12, 13 | no integration-owned file changed; lint/type/full offline suite green |
