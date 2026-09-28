# Story 21 — Phase 2 QA procedure (T6..T10: independent helpers and study inputs)

You are a person operating the system. Prove that each Phase 2 component works
through its real interfaces: the pytest-bdd selections, the Python REPL and the
new `experiments/confluence-chain/` scripts. Every step names the command,
where to run it and what you must observe. A step whose expected outcome you do
not observe is a failure to report, not a step to skip. Nothing here runs LEAN,
Docker or touches NAS data — every Phase 2 module is pure/component and every
script's Gherkin scenario below is a small, hand-built fixture, not a
production re-derivation (that is the separately authorized Evidence gate in
`tasks.md`).

Setup (every shell):

```sh
export TMPDIR=/home/wellington/.cache/claude-tmp; mkdir -p "$TMPDIR"
cd /tmp/mba-impl-21/algo-suite          # branch feat/21-confluence-chain
uv sync --all-packages
```

Phase 2 does not touch any integration-owned file (`strategies.py`,
`chain/wiring.py`, `engine/chain_algorithm.py`, `chain/audit.py`,
`chain/decision_recorder.py` — Phase 3, T11–T15). Every module below is a new,
Story-21-private file; nothing here is reachable from the CLI or from an
existing strategy config yet.

## Step 1 — Baseline and collection sanity

```sh
uv run pytest algo-backtest/tests -q --co -m 'not integration' | tail -1
uv run pytest algo-backtest/tests/steps/test_confluence_time_exit.py \
  algo-backtest/tests/steps/test_confluence_controls.py \
  algo-backtest/tests/steps/test_confluence_horizon_units.py \
  algo-backtest/tests/steps/test_confluence_preflight.py \
  algo-backtest/tests/steps/test_confluence_cells.py -q --co | tail -1
```

Expected: the first line prints the pre-phase baseline count (Phase 1 close-out
plus whatever main has merged since). The second selection collects exactly
47 + 16 + 14 + 21 + 35 = 133 cases (the feature files' scenario-plus-Examples-row
counts: time exit 47, controls 16, horizon units 14, preflight 21, cells 35) and
exits 0. A count of 0 or an import error means a step file is missing.

## Step 2 — T6: the time-exit lifecycle (pytest)

```sh
uv run pytest algo-backtest/tests/steps/test_confluence_time_exit.py -q
```

Expected: all 47 collected cases pass, 0 failed, 0 skipped.

## Step 3 — T6: the time-exit lifecycle (REPL)

```sh
uv run python - <<'PYEOF'
from datetime import UTC, datetime
from algo_backtest.chain.time_exit import TimeExitLifecycle

lc = TimeExitLifecycle(clock_minutes=60, exit_after_bars=4)
lc.entry_filled("T1", datetime(2016, 3, 1, 10, 0, 30, tzinfo=UTC), quantity=1000)
for h in range(10, 14):
    lc.completed_candle(datetime(2016, 3, 1, h, tzinfo=UTC), datetime(2016, 3, 1, h + 1, tzinfo=UTC))
print(lc.state("T1"), lc.due_at("T1"))
closures = lc.tradable_event(datetime(2016, 3, 1, 14, 0, tzinfo=UTC))
print(closures)
print(lc.state("T1"))
PYEOF
```

Expected: `DUE 2016-03-01 14:00:00+00:00`; one requested closure of trade `T1`
for `-1000` units at `2016-03-01T14:00:00+00:00`; then `PENDING` (a live close
order is now implied and blocks a second request until the caller reports its
status — see the feature's "one live close order at a time" rule).

## Step 4 — T7: the constant-direction control filter (pytest)

```sh
uv run pytest algo-backtest/tests/steps/test_confluence_controls.py -q
```

Expected: all 16 collected cases pass, 0 failed, 0 skipped.

## Step 5 — T7: the constant-direction control filter (REPL)

```sh
uv run python - <<'PYEOF'
from datetime import UTC, datetime
from algo_backtest.chain.model import ExecutionState
from algo_backtest.chain.filters.constant_direction import ConstantDirectionFilter

short = ConstantDirectionFilter(direction="SELL")
state = ExecutionState(timestamp=datetime(2016, 3, 1, 10, tzinfo=UTC), pair="EURUSD", features={})
result = short.apply(state)
print(result.recommendation, result.veto, result.enrichment)
try:
    ConstantDirectionFilter(direction="HOLD")
except ValueError as exc:
    print("rejected:", exc)
PYEOF
```

Expected: `Recommendation.SELL False {}`; then a `rejected:` line containing
`direction must be 'BUY' or 'SELL', got 'HOLD'`. No traceback escapes.

## Step 6 — T8: the horizon unit re-derivation tool (pytest)

```sh
uv run pytest algo-backtest/tests/steps/test_confluence_horizon_units.py -q
```

Expected: all 14 collected cases pass, 0 failed, 0 skipped.

## Step 7 — T8: the horizon unit re-derivation tool (archive integrity)

```sh
ARCHIVE=docs/stories/in-progress/21-confluence-chain/evidence/signal-horizon-check.md
sha256sum "$ARCHIVE" > "$TMPDIR/before.sha256"
uv run python experiments/confluence-chain/rederive_horizon.py \
  --archive "$ARCHIVE" --out "$TMPDIR/horizon-units.json" || true
sha256sum "$ARCHIVE" > "$TMPDIR/after.sha256"
diff "$TMPDIR/before.sha256" "$TMPDIR/after.sha256"
sha256sum "$ARCHIVE" | awk '{print $1}'
```

Expected: the two `sha256sum` outputs are identical (`diff` prints nothing);
record the printed hash in the QA report as the archive's known-good hash.
Running the script without real source price Parquet is expected to fail with
an explicit missing-source message naming a remediation — that is BLOCKED, not
a Phase 2 defect, unless run against the fixture data the step file provides.

## Step 8 — T9: the population and availability preflight (pytest)

```sh
uv run pytest algo-backtest/tests/steps/test_confluence_preflight.py -q
```

Expected: all 21 collected cases pass, 0 failed, 0 skipped.

## Step 9 — T9: the population ledger (REPL)

```sh
uv run python - <<'PYEOF'
from datetime import date
from algo_backtest.experiments.confluence_chain.preflight import compute_population_ledger

ledger = compute_population_ledger(pair="EURUSD", clock_minutes=60,
                                    start=date(2016, 1, 1), end=date(2016, 1, 31))
print(ledger.calendar_expanded_count, ledger.market_closure_count, ledger.expected_valid_count)
assert ledger.calendar_expanded_count == ledger.market_closure_count + ledger.expected_valid_count
PYEOF
```

Expected: `744 240 504` and the assertion passes silently. (This step assumes
the module path T9 actually lands at; adjust the import to the real path
recorded in `progress.md` if it differs — report the discrepancy either way.)

## Step 10 — T10: the fourteen-cell manifest generator (pytest)

```sh
uv run pytest algo-backtest/tests/steps/test_confluence_cells.py -q
```

Expected: all 35 collected cases pass, 0 failed, 0 skipped.

## Step 11 — T10: the manifest generator (CLI/script)

```sh
rm -rf "$TMPDIR/confluence-job"
uv run python experiments/confluence-chain/make_cells.py --job-dir "$TMPDIR/confluence-job"
find "$TMPDIR/confluence-job" -name 'config.yaml' | wc -l
python3 -c "
import json, pathlib
manifest = json.loads((pathlib.Path('$TMPDIR/confluence-job') / 'manifest.json').read_text())
rows = manifest if isinstance(manifest, list) else manifest.get('cells', manifest)
print(len(rows))
print(len({row['config_hash'] for row in rows}))
"
```

Expected: `find` prints `14`; the manifest has 14 rows and 14 distinct
`config_hash` values (no two cells collide). Re-running the same command into a
second job directory and diffing the two `manifest.json` files shows identical
cell IDs and hashes.

## Step 12 — No integration-owned or Phase-1 file was touched

```sh
git -C /tmp/mba-impl-21 diff --stat main -- \
  algo-suite/algo-backtest/src/algo_backtest/strategies.py \
  algo-suite/algo-backtest/src/algo_backtest/chain/wiring.py \
  algo-suite/algo-backtest/src/algo_backtest/chain/audit.py \
  algo-suite/algo-backtest/src/algo_backtest/chain/decision_recorder.py \
  algo-suite/algo-backtest/src/algo_backtest/engine \
  algo-suite/algo-backtest/src/algo_backtest/chain/terminal.py \
  algo-suite/algo-backtest/src/algo_backtest/chain/filters/f1_trend.py \
  algo-suite/algo-backtest/src/algo_backtest/chain/filters/f4_news_context.py \
  algo-suite/algo-backtest/src/algo_backtest/chain/filters/f6_capital_mgmt.py \
  algo-suite/algo-backtest/src/algo_backtest/chain/intensity_history.py
```

Expected: nothing prints. Phase 2 adds new files only
(`chain/time_exit.py`, `chain/filters/constant_direction.py`,
`experiments/confluence-chain/rederive_horizon.py`,
`experiments/confluence-chain/preflight.py`,
`experiments/confluence-chain/make_cells.py`) and must not modify any Phase 1
or integration-owned module.

## Step 13 — Quality gates for the touched packages

```sh
uv run ruff check algo-backtest/src/algo_backtest/chain/time_exit.py \
  algo-backtest/src/algo_backtest/chain/filters/constant_direction.py \
  algo-backtest/tests/steps/test_confluence_time_exit.py \
  algo-backtest/tests/steps/test_confluence_controls.py \
  algo-backtest/tests/steps/test_confluence_horizon_units.py \
  algo-backtest/tests/steps/test_confluence_preflight.py \
  algo-backtest/tests/steps/test_confluence_cells.py
uv run ruff check --select C901 algo-backtest/src/algo_backtest/chain/time_exit.py \
  algo-backtest/src/algo_backtest/chain/filters/constant_direction.py
uv run mypy --strict algo-backtest/src/algo_backtest/chain/time_exit.py \
  algo-backtest/src/algo_backtest/chain/filters/constant_direction.py
uv run mypy --strict experiments/confluence-chain/rederive_horizon.py \
  experiments/confluence-chain/preflight.py experiments/confluence-chain/make_cells.py
uv run pytest algo-backtest/tests -q -m 'not integration' | tail -3
```

Expected: ruff and mypy report no findings; the full offline run reports 0
failed and a passed count equal to the Step 1 baseline plus 133 (record both
numbers in the QA report; do not sum overlapping selections).

## Checklist (fill in the QA report, one line per task)

| Task | Component | Steps | Pass criterion |
| --- | --- | --- | --- |
| T6 | `TimeExitLifecycle` in `chain/time_exit.py` | 2, 3 | bar-open timing at H1/H4, weekend gap, partial-bar refusal, idempotent repeats, same-side/reversal identity, full/partial stop precedence, live-order block and rejection retry, end-of-stream unresolved state |
| T7 | `ConstantDirectionFilter` in `chain/filters/constant_direction.py` | 4, 5 | constant BUY/SELL vote regardless of state, invalid direction rejected, real F5/F6 vetoes still apply through `FilterChain.run` |
| T8 | `experiments/confluence-chain/rederive_horizon.py` | 6, 7 | normalized-return vs. price-pip units diverge on matched closes, bad join key/missing horizon/missing price explicit, archive sha256 unchanged, output only to a new caller-specified path |
| T9 | `experiments/confluence-chain/preflight.py` | 8, 9 | calendar-expanded/closure/valid/warmup/missing reconcile on H1 and H4, file presence alone insufficient, absent source fails with remediation, M-only/controls need no news, news arms need a provenance sidecar or are reported unavailable |
| T10 | `experiments/confluence-chain/make_cells.py` | 10, 11 | exactly 14 unique cells, correct per-arm required voters, controls/M-only news-free, time plans pinned (targets/trail empty, N=4, min_hold_bars 4), A-plan pins the Heikin-Ashi reference plan, costs/caps/window invariant, disallowed arms/filters excluded, config hashes recorded and deterministic |
| all | no integration-owned or Phase-1 file changed | 12, 13 | clean diff on shared paths; lint/type/full offline suite green |

## Specifier gap list — Phase 2 (spec-precision gaps found, with pinned choices)

`spec.md`/`design.md`/`tasks.md` do not fix every value the Phase 2 feature files
needed. Each gap below states the pinned choice the feature files encode, so the
coder either confirms it or raises a deviation before implementing against it.

1. **Runtime name/config key for the drift-control filter (T7).** Neither
   `spec.md` nor `design.md` names the filter module's class or its canonical
   YAML voter id; `design.md` only gives the file path
   `chain/filters/constant_direction.py`. Pinned: class `ConstantDirectionFilter`,
   constructor parameter `direction: Literal["BUY", "SELL"]`, canonical voter id
   and runtime `filter_name` both `constant_direction` (lower snake case, like
   `f4_news_context`, since it is a new addition rather than a legacy F-numbered
   filter). `confluence_controls.feature` and `confluence_cells.feature` both
   assume this name; the required-voter list for always-short/always-long is
   `constant_direction` in both cells, distinguished only by each cell's own
   `constant_direction.direction` value, not by two different voter names.
2. **"Bad join key" vs. "missing future horizon"/"missing price" as hard-fail
   vs. explicit-per-row for T8.** `design.md`'s T8 "Done when" lists all three
   ("bad joins, missing future horizon and missing prices are explicit") without
   distinguishing which abort the run and which are recorded per row. Pinned:
   a structurally bad join key (off-grid or naive timestamp, or an ambiguous
   duplicate decision timestamp with conflicting archived closes) is a hard
   `raise` — it signals a bug in the archive or the join, not a data-availability
   gap. A missing future horizon row or a missing matched source price is a
   *data* gap on an otherwise well-formed key, so it is recorded per row with an
   explicit `unit_status` (`missing_future_horizon` / `missing_price`) and null
   pip values, mirroring CC-30's "incomplete forward horizons separately" and
   CC-32's "state the failure explicitly without... dropping". If the coder's
   read differs (e.g. missing price should also hard-fail the whole run), that
   is a one-line deviation to record in `progress.md`, not a silent rewrite of
   the feature file.
3. **H4 candle classification against market closures for T9's ledger (D2, D8).**
   Weekend closure (Friday 22:00 UTC–Sunday 22:00 UTC, the convention already
   implied by the H1 clock's hourly closed/open pattern) does not align to the
   H4 grid's 00/04/08/12/16/20 UTC boundaries — Friday 22:00 falls inside the
   20:00–24:00 H4 bucket. Neither `spec.md` nor `design.md` states whether such
   a straddling bucket counts as an "expected valid decision bar" or a
   "documented closure." Pinned (conservative): an H4 bucket is a documented
   closure if *any* of its four constituent H1 hours is closed; only a bucket
   whose all four hours are open is an "expected valid" H4 decision bar. This is
   the reading `confluence_preflight.feature`'s three-day worked example encodes
   (H4 `expected_valid_count` 5 of 18 buckets, `market_closure_count` 13,
   including the two straddling buckets) — it does not introduce a third
   "partial" ledger category. If the intended contract instead prorates a
   straddling bucket or gives it its own status, the numbers in that scenario
   need updating, not the underlying H1 numbers (verified independently by
   direct calendar arithmetic: January 2016 is 744 H1 hours, 240 closed,
   504 open).
4. **News-availability requirement per arm for T9 (CC-13, CC-24, CC-32).**
   `design.md` states A/B/T-only need the provenance sidecar and "M-only and
   both controls require no news input," but does not state this as a queryable
   ledger field. Pinned: the preflight ledger exposes a boolean
   `news_availability_required` per arm, true for A/B/T-only and false for
   M-only/always-short/always-long, and a missing sidecar for a
   `news_availability_required` arm yields per-cell `status: "unavailable"`
   with the cell still listed (CC-32), never a raised exception that would drop
   the whole ledger.
5. **`ready_count` as a named ledger field (T9).** The population ledger needs a
   fifth quantity beyond the four `design.md` names explicitly (calendar-expanded,
   closures, expected-valid, warmup, missing) to state how many bars are actually
   launch-ready after excluding warmup and missing from expected-valid. Pinned:
   a `ready_count` field with `expected_valid_count == warmup_count +
   missing_count + ready_count`. If the coder's chosen ledger shape names this
   differently (e.g. computed on demand rather than stored), the reconciliation
   *equation* in the last scenario of `confluence_preflight.feature` is the part
   that must hold, not the literal field name.
6. **A-plan's pinned fields for T10 (D11).** `design.md` says A-plan "pins every
   inherited exit setting" from "the pinned existing Heikin-Ashi H4 reference
   plan" without listing the fields. Pinned, taken from the actual reference
   config at `experiments/heikin-ashi-signals/strategies/heikin-ashi-h4-talib-volume-on/config.yaml`:
   `stop_distance_source: swing`, `stop_loss_shrink: 0.50`, `min_stop_pips: 5.0`,
   `min_stop_factor: 1.2`, `targets: [{4.0, 0.5}, {6.0, 0.5}]`,
   `trail_stops: [{2.0, 0.1}]`, `min_reward_risk: 2.0`, `atr_multiplier: 2.0`,
   `risk_per_trade: 0.03` (same risk as every other arm, D9's "no artificial
   intensity thresholds" cost-parity intent extended to risk-per-trade). A-plan
   has no `exit_after_bars` (the pinned plan's own target/trail exit governs
   instead), consistent with "the lifecycle decides which fires first" language
   already accepted for T5's coexistence scenario.
7. **`make_cells.py`'s CLI surface for refusing disallowed arms/clocks (T10).**
   `spec.md`/`design.md` state the fixed 14-cell family as a property of the
   generator's output, not as a CLI contract with arguments to reject. Pinned:
   the generator exposes an internal, closed arm/clock registry; the Gherkin
   scenarios that "request" an extra arm/clock model a caller attempting to
   extend that registry (however the coder's actual API takes it — a keyword
   argument, a second manifest-merge call, or a monkeypatched registry in the
   test) and assert it fails closed. The scenario text is intentionally CLI-agnostic
   ("is generated with an extra arm") so the step definitions can bind it to
   whatever the coder's real construction API turns out to be.
