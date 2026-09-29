# Mutation testing — Story 21, Phase 3 (T16 registration README, T17 launch harness)

Manual behaviour-level mutation testing (no `mutmut` in the workspace; `tools/mutation_harness.py`
scopes to a tool's `src/` tree, not `experiments/`, so it does not apply here) of the Story 21
work since the Phase 2 hardening commit `f6c464a`: `experiments/confluence-chain/run_cells.py`
(T17), `experiments/confluence-chain/README.md` (T16), plus the one production function this
pass had to fix (`preflight.partition_path`, see "Production fix"). T18 (`compare.py`) had not
landed when this pass ran (progress.md: "Next: T18"), so it is out of scope. One mutation at a
time, in place in the worktree; each was backed up, applied, run against the covering step files
(`uv run pytest <files> -q -p no:cacheprovider -x`, `PYTHONDONTWRITEBYTECODE=1`, `__pycache__`
wiped first — the Phase 2 harness note), then restored, with `git status --porcelain` confirmed
identical to the pre-mutation baseline after every mutation (0 drift events). Covering step
files: `test_confluence_run_contract.py` (all three targets) and `test_confluence_preflight.py`
(`preflight.py`).

## Summary

| File | Mutations | Killed | Survived (justified equivalent / not executable) |
| --- | --- | --- | --- |
| `run_cells.py` | 78 | 74 | 4 (R4, R9, R13, R14 — equivalent) |
| `README.md` | 16 | 14 | 2 (D11, D12 — prose with no executable counterpart until T18) |
| `preflight.py` (`partition_path`) | 6 | 6 | 0 |
| **Total** | **100** | **94** | **6, all justified; 0 unjustified** |

Negative control: **R32** (`status.json` renamed `state.json`) — confirmed KILLED, proving the
harness detects faults. Also, the unmutated baseline was green before and after every run
(78 scenarios in `test_confluence_run_contract.py`).

The first pass over `run_cells.py` (existing 15 scenarios) killed only 10 of 66 mutations: the
Story 21 T17 tests always injected a permissive population gate and a fake runner, so the real
`population_gate`, `months_between`, `_real_runner`, `_git_sha`, `main()`, the recorded command
and status fields, the results-directory parsing, the README copy and the concurrency cap were
all unasserted. All 56 survivors were closed with new Gherkin (below); none by weakening an
existing scenario.

## `run_cells.py` (78 mutations)

| ID | Mutation | Result |
| --- | --- | --- |
| R1 | default timeout constant 1800→1801 | KILLED |
| R2 | default concurrency constant 3→4 | KILLED |
| R3 | A-plan alias target "A"→"M-only" | KILLED |
| R4 | cell-id clock label `60→h1`/else `h4` swapped | SURVIVED — equivalent (see below) |
| R5 | unregistered-generated-id check inverted | KILLED |
| R6 | missing-generated-id check inverted | KILLED |
| R7 | A-plan alias lookup removed (raw `cell.arm`) | KILLED |
| R8 | arm-ledger window start replaced by window end | KILLED |
| R9 | arm-ledger `clock_minutes` replaced by constant 60 | SURVIVED — equivalent (see below) |
| R10 | empty-cell gate returns→raises | KILLED |
| R11 | pair/window disagreement `or`→`and` | KILLED |
| R12 | `partition_exists` forced True | KILLED |
| R13 | gate looks up clock 60 partition for every clock | SURVIVED — equivalent (see below) |
| R14 | gate checks only the first clock | SURVIVED — equivalent (see below) |
| R15 | `months_between` `<=`→`<` (drops last month) | KILLED |
| R16 | December rollover `== 12`→`== 11` | KILLED |
| R17 | February month label mangled | KILLED |
| R18 | month last day off by one | KILLED |
| R19 | real runner drops stderr | KILLED |
| R20 | timeout exit code 124→125 | KILLED |
| R21 | spawn-failure exit code 127→126 | KILLED |
| R22 | real runner timeout +1s | KILLED |
| R23 | `_git_sha` `== 0`→`!= 0` | KILLED |
| R24 | `_git_sha` OSError returns `''` instead of None | KILLED |
| R25 | preflight.py dropped from code hashes | KILLED |
| R26 | `--strategy` uses arm not cell id | KILLED |
| R27 | `--from`/`--to` swapped | KILLED |
| R28 | `--timeout` hard-coded | KILLED |
| R29 | `run` subcommand →`backtest` | KILLED |
| R30 | results= parse keeps the marker text | KILLED |
| R31 | no-marker result `None`→`''` | KILLED |
| R32 | status file renamed `state.json` | KILLED (negative control) |
| R33 | runner cwd SUITE→HERE | KILLED |
| R34 | runner timeout +1 on pass-through | KILLED |
| R35 | runner-raise handler re-raises | KILLED |
| R36 | success test `== 0`→`<= 0` | KILLED |
| R37 | failure reason removed | KILLED |
| R38 | status `source_revision` dropped | KILLED |
| R39 | status `results_dir` dropped | KILLED |
| R40 | run.log written empty | KILLED |
| R41 | command.json `source_revision` dropped | KILLED |
| R42 | command.json `code_hashes` emptied | KILLED |
| R43 | recorded command truncated | KILLED |
| R44 | pre-run state "running"→"succeeded" | KILLED |
| R45 | `cell_ids is not None`→truthiness (empty list selects all) | KILLED |
| R46 | unregistered-id refusal removed | KILLED |
| R47 | rerun-not-requested refusal removed | KILLED |
| R48 | arm-ledger `== OK`→`!= OK` | KILLED |
| R49 | unavailable reason replaced by generic text | KILLED |
| R50 | unavailable status reason dropped | KILLED |
| R51 | `max_concurrent < 1`→`< 0` | KILLED |
| R52 | README copy condition inverted | KILLED |
| R53 | README copy written empty | KILLED |
| R54 | attempt filter `or`→`and` | KILLED |
| R55 | thread pool fixed at 1 worker | KILLED |
| R56 | resume status read-back removed | KILLED |
| R57 | result order reversed | KILLED |
| R58 | default data root hard-coded | KILLED |
| R59 | CLI exit code on failure →0 | KILLED |
| R60 | CLI exit code on refusal 2→1 | KILLED |
| R61 | CLI default timeout 1800→60 | KILLED |
| R62 | CLI ignores `--timeout` | KILLED |
| R63 | `mkdir(exist_ok=True)`→`False` | KILLED |
| R64 | manifest truncated to 13 cells | KILLED |
| R65 | `_read_json` object check `not isinstance`→`pass` | KILLED |
| R66 | `finished_at` dropped | KILLED |
| R67 | `_load_script` unloadable-file check removed | KILLED |
| R68 | `sys.modules` registration removed | KILLED |
| R69 | file digest sha256→md5 | KILLED |
| R70 | population window hard-coded to 2016-03 | KILLED |
| R71 | unexpected-id refusal removed | KILLED |
| R72 | missing-id refusal removed | KILLED |
| R73 | disagreement check ignores windows | KILLED |
| R74 | JSON-object check removed | KILLED |
| R75 | empty-cell early return removed | KILLED |
| R76 | month rollover skips a month | KILLED |
| R77 | `results=` marker test inverted | KILLED |
| R78 | arm-ledger reason dropped | KILLED |

### Equivalent mutants (traced)

- **R4** — `'h1' if clock == 60 else 'h4'` → `'h1' if clock == 240 else 'h4'`. `ALLOWED_CELL_IDS`
  is a `frozenset` built over *both* clocks of `mc.CLOCK_LOOKBACK` ({60, 240}); swapping which
  clock gets which label yields the identical set. Set semantics erase the pairing, and the
  id-to-clock mapping itself is pinned by `make_cells.py`'s exact-id assertions
  (`confluence_cells.feature`, Phase 2 E6) plus the README-table scenario added here.
- **R9** — `_arm_ledger_status` passes `clock_minutes=60` for every cell.
  `preflight.compute_arm_ledger` requires the keyword but never reads it (it reads only `arm`,
  `window_start` and `sidecar`), so no observable output can differ.
- **R13 / R14** — gate looks up clock 60 for every clock / checks only the first clock.
  After the production fix below, the required partition is the one M1 store every signal-bar
  clock is aggregated from, so the path is clock-independent by design; the per-clock loop is
  retained only so the failure message names the clock being checked. Both mutants read the
  same file, so the outcome is identical.

## `README.md` (16 mutations, T16)

The README is prose, so its *checkable* claims were bound to the code by new scenarios
(cell table vs `manifest.json`, launch-ready/blocked table vs the harness's behaviour, window /
pair / `close_on_veto` / `min_hold_bars` / constant-direction / spread vs every generated
`config.yaml`, resource caps vs `DEFAULT_*` constants, byte-for-byte copy into the job
directory).

| ID | Mutation | Result |
| --- | --- | --- |
| D1 | table row 9 cell id renamed | KILLED |
| D2 | table row 14 deleted | KILLED |
| D3 | row 5 arm A-plan→A | KILLED |
| D4 | row 2 clock H4→H1 | KILLED |
| D5 | window start 2016-03-01→03-02 | KILLED |
| D6 | `close_on_veto: false`→true | KILLED |
| D7 | concurrent cap 3→4 | KILLED |
| D8 | timeout 30→45 minutes | KILLED |
| D9 | launch-ready/blocked cells swapped | KILLED |
| D10 | pair EUR/USD→GBP/USD | KILLED |
| D11 | bootstrap block length 4→3 | SURVIVED — not executable (see below) |
| D12 | bootstrap resamples 999→499 | SURVIVED — not executable (see below) |
| D13 | `min_hold_bars: 4`→5 | KILLED |
| D14 | D5 horizon `N=4`→`N=5` | KILLED |
| D15 | row 12 constant SELL→BUY | KILLED |
| D16 | spread 1.0→2.0 pip | KILLED |

- **D11 / D12** — bootstrap block length and resample count are prose claims about the
  statistical protocol; nothing executable at this phase reads or enforces them (`compare.py`,
  T18, has not landed). Not killable without inventing a fake consumer. **Follow-up:** T18's
  scenarios should bind block length 4/2, 999 resamples, seed 42 and alpha .05 to the README so
  these two (and the other D7 numbers) become killable.

## `preflight.py::partition_path` (6 mutations)

| ID | Mutation | Result |
| --- | --- | --- |
| F1 | resolution segment `m1`→`m5` | KILLED |
| F2 | asset class segment `forex`→`fx` | KILLED |
| F3 | year/month values swapped | KILLED |
| F4 | file name `.parquet`→`.csv` | KILLED |
| F5 | pair hard-coded to EURUSD | KILLED |
| F6 | clock appended to the path | KILLED |

## Production fix (genuine finding, not an equivalent mutant)

Writing the real-gate scenarios exposed that the T9 `partition_path` — and therefore T17's
`population_gate` — pointed at a layout that does not exist:
`algo-suite/data/parquet/forex/<pair>/clock=<N>/<YYYY-MM>.parquet`, joined onto a `data_root`
that already *is* `algo-suite/data` (double prefix), and with a `clock=` / flat-file scheme
that `algo_core.layout` never writes. On real data the gate would have hard-failed for every
month, blocking any T19 run. The real layout (`algo_core.layout.price_path`, the store
`materialize.py` reads before writing LEAN data) is
`<data_root>/parquet/forex/<pair>/m1/year=YYYY/month=MM/data.parquet`, and H1/H4 bars are
aggregated from that one M1 store. Fixed minimally: `partition_path` now returns that
data-root-relative path (signature unchanged; the clock parameter is documented as unused),
the missing-partition message adds "(relative to the data root)". The unchanged T9 scenario
"an absent required source partition fails with a remediation naming the exact path" still
passes (it derives the expected path from `partition_path`). A new scenario cross-checks
`partition_path` against `algo_core.layout.price_path` for several pairs/clocks/months (kills
F1-F6), and the gate scenarios create their fixture files through `layout.price_path`
directly, not through `partition_path`. The file-existence-only scope of the gate is unchanged
(row-level reconciliation remains a caller responsibility).

## Killing scenarios added (all in `confluence_run_contract.feature`, feature first)

New Rules: registered caps and README agree; selection semantics; a generator that drifts from
the registration is refused; bounded concurrency; data root passed to the population gate; the
real population gate (per-month, disagreement, no cells); month enumeration; exact
`algo-backtest run` argv / cwd / timeout; before/during/after attempt records (running
snapshot, revision, code hashes, timestamps, run log, exit-code and reason table, runner raise,
results-dir parsing, unavailable record, non-object status refusal); the real child runner
(stdout+stderr, exit codes 3/124/127, timeout, cwd); git revision when git cannot answer; the
CLI entry point (defaults, explicit forwarding, exit codes 0/1/2 and output). 63 new
scenarios/examples (15 → 78), plus assertions added to none of the existing ones.

## Verification

- `uv run pytest algo-backtest/tests/steps/test_confluence_run_contract.py
  algo-backtest/tests/steps/test_confluence_preflight.py -q -p no:cacheprovider`: all pass.
- `uv run pytest algo-backtest/tests -q -p no:cacheprovider`: 2015 passed (was 1952).
- `uv run ruff check algo-backtest experiments`: clean.
- `uv run mypy --strict experiments/confluence-chain`: clean.

## Follow-up (not in scope here)

Comment #7845 on PR #91: reordering `self._decisions.on_fill(...)` before the time-exit
lifecycle block in `engine/chain_algorithm.py::on_order_event` broke 8 of 10 native scenarios,
so that call order is load-bearing. It belongs to the Phase 3 engine-integration hardening
pass (native/LEAN runs happen on the GPU workstation); no native run was attempted here.
