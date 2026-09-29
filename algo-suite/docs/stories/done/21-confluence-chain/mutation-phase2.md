# Mutation testing — Story 21, Phase 2

Manual behaviour-level mutation testing (no `mutmut` in the workspace) of the five
Phase-2 production modules against their covering pytest-bdd step files. One mutation
applied at a time, in place, in the actual worktree (`/tmp/mba-impl-21`); each mutation
was backed up, applied, run against its covering test file (`uv run pytest <file> -q -p
no:cacheprovider -x`), then restored, with `git status --porcelain` confirmed to match
the pre-mutation baseline after every mutation.

**Harness note:** the first pass showed intermittent, non-reproducible KILLED/SURVIVED
flips on `time_exit.py` mutations (M2, M3) across repeat runs. Root cause: rapid
rewrite/restore of the same source file collided on second-granularity mtimes, so
Python's import machinery sometimes reused a stale `__pycache__/*.pyc` compiled from a
*different* mutation instead of recompiling the file actually on disk. Fixed by wiping
`__pycache__` before the run and setting `PYTHONDONTWRITEBYTECODE=1` for every mutation
subprocess. Re-run three times after the fix with identical results (33 KILLED / 3
SURVIVED, same three IDs every time) — the numbers below are from that stable state.

## Summary

| File | Mutations | Killed | Survived |
| --- | --- | --- | --- |
| `chain/time_exit.py` | 11 | 8 | 3 (M2, M6, M7 — all equivalent, see below) |
| `chain/filters/constant_direction.py` | 6 | 6 | 0 |
| `experiments/confluence-chain/rederive_horizon.py` | 7 | 7 | 0 |
| `experiments/confluence-chain/preflight.py` | 6 | 6 | 0 |
| `experiments/confluence-chain/make_cells.py` | 6 | 6 | 0 |
| **Total** | **36** | **33** | **3** |

Negative controls (mutations expected to be trivially caught, to prove the harness
itself detects faults): **M11** and **H7**, both confirmed KILLED.

## `chain/time_exit.py` (11 mutations, target ≥8)

| ID | file:line | Operator | Original → Mutated | Result |
| --- | --- | --- | --- | --- |
| M1 | time_exit.py:345 | boundary `>=`→`>` | `start >= trade.bar_t_start` → `start > trade.bar_t_start` (in `_count_bar_toward_horizon`) | KILLED |
| M2 | time_exit.py:335 | boundary `<=`→`<` | `if end <= last_end:` → `if end < last_end:` (in `_is_repeat_of_last_candle`) | SURVIVED — equivalent, see below |
| M3 | time_exit.py:313 | comparison `!=`→`<` | `end - start != self._clock_delta` → `end - start < self._clock_delta` (in `_validate_candle_bounds`) | KILLED (after adding a killing scenario) |
| M4 | time_exit.py:357 | boundary `<`→`<=` | `at < self._last_time` → `at <= self._last_time` (causality check in `tradable_event`) | KILLED |
| M5 | time_exit.py:364 | removed idempotency check | `trade.last_requested_at == at` → `False` | KILLED |
| M6 | time_exit.py:424 | removed guard | `self._open_trade_id = None` → `pass` (in `stop_filled`, full-fill branch) | SURVIVED — equivalent, see below |
| M7 | time_exit.py:471 | removed guard | `self._open_trade_id = None` → `pass` (in `order_status_report`, FILLED branch) | SURVIVED — equivalent, see below |
| M8 | time_exit.py:288 | removed statement (contrast case for M6/M7) | `self._open_trade_id = trade_id` removed (in `entry_filled`) | KILLED |
| M9 | time_exit.py:348 | wrong constant (due_at timing) | `trade.due_at = end` → `trade.due_at = start` | KILLED |
| M10 | time_exit.py:274-278 | boolean `and`→`or` | idempotent-repeat check in `entry_filled` | KILLED |
| M11 | time_exit.py:418 | wrong constant (negative control) | `trade.reason = "stop"` → `"expiry"` | KILLED |

### The two removed guards (M6, M7) — traced, not assumed

The brief flagged these as the phase's highest-risk change and asked for an actual trace
of every caller path before concluding equivalence, not an assumption. Traced:

`self._open_trade_id` has exactly one reader in the whole module — `_open_trade()`
(time_exit.py:187-192), which already does:
```python
if self._open_trade_id is None:
    return None
trade = self._trades[self._open_trade_id]
return None if trade.status == CLOSED else trade
```
So `_open_trade()` filters out a CLOSED trade **by its own `status` field**, independent
of whether `_open_trade_id` still points at it. Every consumer of "the open trade"
(`entry_filled`'s reject-if-still-open check, `_count_bar_toward_horizon`,
`tradable_event`) goes through `_open_trade()`, so none of them can observe a stale
`_open_trade_id`.

The only two writers of `_open_trade_id` besides the two removed-guard lines are
`entry_filled` (time_exit.py:288, unconditional) and `reversal_filled`
(time_exit.py:400, unconditional) — both overwrite it to the *new* trade's id
regardless of the old value, so a stale id left behind by a skipped reset in
`stop_filled`/`order_status_report` is clobbered the moment a new identity opens.

`order_submitted`, `order_status_report` and `stop_filled` themselves all look up their
trade by the caller-supplied `trade_id` via `self._trades.get(trade_id)` /
`_known_trade(trade_id)` — never via `self._open_trade_id` — so a stale
`_open_trade_id` cannot misroute an event to the wrong trade either.

Conclusion: removing `self._open_trade_id = None` in `stop_filled` or
`order_status_report` is unobservable through every current public method and caller
path (confirmed for `stop_filled`, `order_status_report`, `entry_filled`,
`reversal_filled`, `order_submitted`, `tradable_event`, `completed_candle`) — a genuine
equivalent mutant, not an untested gap. As a contrast check, M8 (removing the
*assignment* in `entry_filled`, the one write that IS load-bearing) was injected the
same way and was cleanly KILLED by nearly the whole scenario suite — confirming the
field is real and observable when *set*, just redundant when *cleared* given the
CLOSED-status filter in `_open_trade()`.

Two regression scenarios were added anyway (not to kill M6/M7, which are truly
equivalent, but to lock in the invariant they document for future refactors — e.g. if
`_open_trade()`'s status filter is ever changed, these would then catch it):
"a brand new entry is accepted immediately after a full stop fill closes the prior
trade" and the equivalent case after `order_status_report`'s FILLED branch, both in
`tests/features/confluence_time_exit.feature`.

### M2 — also equivalent, same style of trace

`_is_repeat_of_last_candle` first checks `(start, end) == (last_start, last_end)` and
returns `True` immediately if so — *before* reaching the mutated `end <= last_end`
line. Every candle that ever reaches `_last_candle` was itself accepted by
`_validate_candle_bounds`, which enforces `end - start == self._clock_delta` exactly.
So if a new candle's `end == last_end`, its `start` is forced to `end -
self._clock_delta == last_end - self._clock_delta == last_start` — i.e. `end ==
last_end` without `start == last_start` is unreachable. The `end <= last_end` line is
therefore only ever reached with `end != last_end`, where `<=` and `<` agree. Confirmed
equivalent.

### M3 — genuine gap, killed with a new scenario

Unlike M2, `end - start != self._clock_delta` mutated to `<` does **not** stay
equivalent: a candle exactly 2x (or any multiple of) the clock length, with a
grid-aligned `end`, passes both the (mutated) length check and the separate off-grid
check, so it would be silently accepted as "one" completed bar. No existing scenario
covered a too-*long* candle (only a 58-minute too-*short* one). Added a
`120-minute double bucket` row to the existing "a candle that is not one complete
clock period is refused" Scenario Outline in `confluence_time_exit.feature` (start
2016-03-04T20:00:00Z, end 2016-03-04T22:00:00Z, both on the 60-minute grid) — kills M3.

## `chain/filters/constant_direction.py` (6 mutations, target ≥6)

| ID | file:line | Operator | Original → Mutated | Result |
| --- | --- | --- | --- | --- |
| C1 | :24 | swapped constants | `_DIRECTIONS = {"BUY": BUY, "SELL": SELL}` → `{"BUY": SELL, "SELL": BUY}` | KILLED |
| C2 | :40 | inverted boolean | `if self.direction not in _DIRECTIONS:` → `if ... in _DIRECTIONS:` | KILLED |
| C3 | :47 | wrong constant | `_DIRECTIONS[self.direction]` → `_DIRECTIONS["BUY"]` | KILLED |
| C4 | :49 | wrong constant (reason text) | `reason=f"...: {self.direction}"` → hardcoded `"...: BUY"` | KILLED (after adding a killing scenario) |
| C5 | :46 | wrong constant | `filter_name=FILTER_NAME` → `filter_name="wrong_name"` | KILLED |
| C6 | :46-49 | added veto | `FilterResult(...)` → `FilterResult(..., veto=True)` | KILLED |

C4 survived initially: no scenario asserted `FilterResult.reason`'s text. Added `And the
constant-direction result gives the reason "constant control direction: <direction>"`
to the existing Scenario Outline in `confluence_controls.feature` plus one new step —
kills C4.

## `experiments/confluence-chain/rederive_horizon.py` (7 mutations, target ≥6)

| ID | file:line | Operator | Original → Mutated | Result |
| --- | --- | --- | --- | --- |
| H1 | :131 | swapped operands | `(close_tk / close_t - 1) / 1e-4` → `(close_t / close_tk - 1) / 1e-4` | KILLED |
| H2 | :132 | sign flip | `(close_tk - close_t) / _PIP` → `(close_t - close_tk) / _PIP` | KILLED |
| H3 | :76 | boundary `>`→`>=` | `if at > self.series_end:` | KILLED (after adding a killing scenario) |
| H4 | :107 | `!=`→`==` | duplicate-close detection in `_check_no_ambiguous_duplicates` | KILLED |
| H5 | :155 | `!=`→`==` | grid-alignment check in `rederive_horizon` | KILLED |
| H6 | :181 | `==`→`!=` | overwrite-protection in `rederive_and_write` (safety-critical) | KILLED |
| H7 | :119 | boolean `or`→`and` (negative control) | `status = status_t or status_tk` | KILLED |

H3 survived initially: the docstring's own contract says "a lookup *at or before*
`series_end`" but absent is a gap (`missing_price`), only *beyond* `series_end` is
`missing_future_horizon`; no scenario put a gap exactly *at* `series_end`. Added "a gap
exactly at the source series boundary is still a missing price, not a future-horizon
overrun" to `confluence_horizon_units.feature` plus one new step — kills H3.

## `experiments/confluence-chain/preflight.py` (6 mutations, target ≥6)

| ID | file:line | Operator | Original → Mutated | Result |
| --- | --- | --- | --- | --- |
| P1 | :69 | boundary `>=`→`>` | Friday closure-hour check in `_hour_closed` | KILLED |
| P2 | :71 | boundary `<`→`<=` | Sunday closure-hour check in `_hour_closed` | KILLED |
| P3 | :246 | boundary `<`→`<=` | strict-precedence check in `compute_arm_ledger` | KILLED (after adding a killing scenario) |
| P4 | :78 | boolean `any`→`all` | H4-bucket closure rule in `_slot_closed` | KILLED |
| P5 | :174 | `-`→`+` | `expected_valid = len(slots) - closures` | KILLED |
| P6 | :37 | membership | `"M-only"` dropped from `_NO_NEWS_ARMS` | KILLED |

P3 survived initially: no scenario put `available_at == decision_time` exactly (only
strictly-before and strictly-after were covered). Added "a sidecar whose availability
timestamp exactly equals the decision timestamp is refused" to
`confluence_preflight.feature` plus one new step — kills P3.

## `experiments/confluence-chain/make_cells.py` (6 mutations, target ≥6)

| ID | file:line | Operator | Original → Mutated | Result |
| --- | --- | --- | --- | --- |
| E1 | :142 | swapped branch | `arm == "A-plan"` → `arm != "A-plan"` in `_capital_mgmt_for` | KILLED |
| E2 | :148 | swapped constants | `0 if arm == "A-plan" else 4` → `4 if ... else 0` in `_execution_for` | KILLED |
| E3 | :131 | inverted membership | `if arm in _NEWS_ARMS:` → `if arm not in _NEWS_ARMS:` | KILLED |
| E4 | :100-104 | removed validation raise | unregistered-arm `raise ValueError` removed from `_validate_registry` | KILLED |
| E5 | :156 | wrong algorithm | `hashlib.sha256` → `hashlib.md5` in `_config_hash` | KILLED (after adding a killing scenario) |
| E6 | :162 | swapped format | `f"{arm.lower()}-{clock_label}"` → `f"{clock_label}-{arm.lower()}"` in `_cell_id` | KILLED (after adding a killing scenario) |

E5 and E6 survived initially: the manifest tests only checked hash *uniqueness*/
non-emptiness and cell-ID *uniqueness*, never the documented SHA-256 algorithm or the
exact `<arm>-<clock>` id format. Added `every manifest row's config_hash is a
64-character hex SHA-256 digest` (kills E5) and three exact cell-ID assertions, e.g.
`the "A" cell on clock 60 minutes has cell ID "a-h1"` (kills E6), to
`confluence_cells.feature` plus two new steps.

## Verification after hardening

- `uv run pytest algo-backtest/tests -q -p no:cacheprovider`: 1937 passed, 53 deselected.
- `uv run ruff check algo-backtest experiments`: clean.
- `uv run mypy --strict algo-backtest experiments/confluence-chain`: clean (69 source
  files). `.mypy_cache` removed after the run.
- The five Phase-2 step files now collect 138 scenarios (134 + 4 new: the 120-minute
  double-bucket Example row, the gap-at-series-boundary scenario, the
  available_at-equals-decision_time scenario, and the new-entry-after-full-stop-fill
  invariant scenario; the reason-text, cell-ID and hash-format assertions, and the
  new-entry-after-order-fill invariant check, were added as extra steps on existing
  scenarios rather than new ones), all passing.
- No production code was changed by this hardener pass — only new Gherkin scenarios and
  their step definitions.
