# Story 22 — Phase 1 QA procedure (T1–T6)

You are a person operating the system. Prove that Phase 1 works through its real
interfaces: files, `pytest` selections, the Python REPL and the repository gates.
Every step lists the command (cwd `algo-suite/` of the lane worktree unless noted),
what to look at, and the observable outcome that counts as PASS. A gate that cannot
run (no Docker, no NAS) is recorded as BLOCKED with the exact error, never as PASS.

Specification anchors: `.specs/features/candlestick-context/spec.md` (CND-01–09,
CND-11, CND-12), `design.md`, `tasks.md` (T1–T6). Feature files under
`algo-backtest/tests/features/`: `candle_contract.feature` (T2),
`candle_catalog.feature` (T3), `candle_context.feature` (T4),
`candle_sequence.feature` (T5), `f3_policy_modes.feature` (T6).

## 0. Baseline

| Step | Command / action | Expected observable outcome |
| --- | --- | --- |
| 0.1 | `git -C /tmp/mba-impl-22 log --oneline -8` | One `docs(candles): review and freeze the source-rule ledger` commit followed by five `feat(candles): ...` commits, one per task T2–T6, in order; each ends with the `Co-Authored-By: Claude Fable 5.1` trailer (`git log -1 --format=%B <sha>`). |
| 0.2 | `uv run pytest algo-backtest/tests/steps/test_candlestick_detector.py algo-backtest/tests/steps/test_f3_pattern.py -q` | All collected scenarios pass; the collected count is not lower than the count on `main` (record both). No scenario was removed or skipped. |
| 0.3 | `git diff main...HEAD --stat -- algo-backtest/src/algo_backtest/perception/candlestick.py algo-backtest/tests/features/candlestick_detector.feature algo-backtest/tests/features/f3_pattern.feature` | Empty output: the legacy detector and its feature files are byte-identical to `main`. |

## 1. T1 — Source-rule ledger checklist

File: `docs/stories/in-progress/22-candlestick-context-extension/candlestick-rule-ledger.md`.
Open it and tick every line; a missing item is a FAIL for T1.

- [ ] **Sources readable and identified.** The ledger states which sources were read
      with their checksums: book PDF (NAS path, SHA-256
      `d962029526518201444cc0d19f52384df8bb095b98b4a6053a7159bfdb289751`),
      presentation PDF (NAS or `~/Downloads/0104-Steve-Bigalow.pdf`, SHA-256
      `b1e6cdfc207854879d9563d036ab70e383a36026cfaf4df59bae57bbfbfe818b`),
      transcript `.txt` (SHA-256
      `18e042d80a31cfaaed1699459be62f6165d48c5d970a20aaf0bb531a1f614691`), and
      `bigalow-video-notes.md`. Verify with `sha256sum <path>` for each file you can reach;
      an unreachable NAS path is recorded in the ledger as unreadable, not silently skipped.
- [ ] **Every admitted rule has a row** with: stable snake_case ID; source citation
      (book printed page AND PDF page, slide number, or transcript time); exact geometry
      formula with named parameters (body, range, upper/lower shadow, ratios) and every
      equality boundary written with `<=` or `<`; context requirement; confirmation rule;
      TA-Lib equivalence or the specific difference; Forex adaptation; one positive, one
      negative and one equality-boundary OHLC example.
- [ ] **Admitted set covers at least:** doji, doji_long_legged, doji_dragonfly,
      doji_gravestone, spinning_top, bullish_harami, bearish_harami, hanging_man,
      inverted_hammer, piercing_line, dark_cloud_cover, bullish_kicker, bearish_kicker,
      plus the legacy six (bullish_engulfing, bearish_engulfing, hammer, shooting_star,
      morning_star, evening_star) documented as TA-Lib-equivalent with lookbacks
      3 / 3 / 12 / 12 / 13 / 13 bars.
- [ ] **Formulas agree with the feature files** (`candle_catalog.feature` description
      block) or the ledger records an explicit dispute AND the feature file was amended in
      the same T1/T3 commit: doji body <= 0.10 range; long-legged min shadow >= 0.30 range;
      dragonfly upper <= 0.10 range; gravestone lower <= 0.10 range; spinning top
      0.10 range < body <= 0.30 range with both shadows >= body; harami strictly inside
      the prior body with opposite colour; piercing/dark cloud open beyond the prior close
      (FX adaptation) and close strictly beyond the prior body midpoint but not reaching the
      prior open; kicker open at or beyond the prior open with opposite colours;
      hanging man / inverted hammer shadow >= 2 body, opposite shadow <= 0.10 range,
      body > 0, net(3) trend precondition.
- [ ] **Context definitions are explicit:** T-line = EMA(8) seeded like
      `training.ema_series`; stochastic 12,3,3 with simple smoothing, raw %K formula,
      readiness at 12/14/16 bars, zero-range = UNDEFINED; zones strict at 80/20;
      SMA 20/50/200 with distance `(close - sma) / sma`.
- [ ] **Confirmation:** doji then next-bar body engulfing (inclusive edges), confirmation
      dated at the confirming close, expiry rules, calendar-policy handling of missing bars.
- [ ] **Deferred list with reasons:** J-hook, fry-pan bottom, dumpling top, cradle, scoop,
      belt-hold, gap formations (book range-gap variants of piercing/dark cloud, abandoned
      baby, "best friend" gap-ups), T-line crunch. Each has a reason (subjective geometry,
      needs reviewed labels, or no intraday FX gap).
- [ ] **Ambiguities preserved, not resolved silently:** the 23:38 overbought/oversold slip,
      the 48:36 morning/evening naming slip, the 26:26 body-gap vs range-gap wording, the
      hanging-man "upper shadow" OCR line in the book criteria (printed page 60) versus its
      description (lower tail).
- [ ] **No speaker performance claims** (win rates, "strongest signal") appear as
      thresholds, priors or acceptance targets.
- [ ] **NDA:** the ledger never names the two earlier trading systems.
- [ ] **Docs gate:** `git diff --check` is clean; from the repo root
      `python3 /home/wellington/.claude/skills/tlc-spec-driven/scripts/validate_spec.py .specs/features/candlestick-context/spec.md --strict`
      and `... validate_tasks.py .specs/features/candlestick-context/tasks.md --strict`
      exit 0; the T1 checkboxes in `tasks.md` are `[x]` and CND-01 shows `Implemented (T1)`.

## 2. T2 — Contract (`candle_contract.py`)

| Step | Command / action | Expected observable outcome |
| --- | --- | --- |
| 2.1 | `uv run pytest algo-backtest/tests/steps/test_candle_contract.py -q` | Collected >= 100 items (18 templates, 112 rows expected), 0 failed, 0 skipped. |
| 2.2 | `uv run python -c "from algo_backtest.perception.candle_contract import CandleConfig; c = CandleConfig(); print(c.catalog_version, c.max_history, c.policy_mode, len(c.enabled_rules))"` | Prints `1 256 legacy 19`. |
| 2.3 | `uv run python -c "from algo_backtest.perception.candle_contract import CandleConfig; CandleConfig(max_history=257)"` | Exits non-zero with a `ValueError` whose message names `max_history`, the bound 256 and how to fix it. |
| 2.4 | `uv run python -c "from algo_backtest.perception.candle_contract import CandleConfig; CandleConfig(max_history=199)"` | `ValueError` naming the 200-bar SMA lookback (never silently shortened). |
| 2.5 | In a REPL, build the default config, assign `c.max_history = 1` | `FrozenInstanceError` (dataclass is frozen). |
| 2.6 | In a REPL, feed a `CandleHistory` (or the T2 history type) five valid hourly bars, then one with `low > high` | `ValueError` mentioning `ordering` and `repair`; `history_count` still 5; the next valid bar is accepted (`history_count` 6). |
| 2.7 | Same history: offer a bar whose `close_time` equals the last one | `ValueError` mentioning `duplicate`; count unchanged. |
| 2.8 | Same history: offer a bar with `close_time` at `10:30` on a 60-minute timeframe | `ValueError` mentioning alignment; count unchanged. |
| 2.9 | `uv run ruff check algo-backtest/src/algo_backtest/perception/candle_contract.py && uv run mypy --strict algo-backtest/src/algo_backtest/perception/candle_contract.py` | Both exit 0. |

## 3. T3 — Catalog (`candle_catalog.py`)

| Step | Command / action | Expected observable outcome |
| --- | --- | --- |
| 3.1 | `uv run pytest algo-backtest/tests/steps/test_candle_catalog.py -q` | Collected >= 100 items (17 scenario templates, 106 rows expected), 0 failed, 0 skipped. |
| 3.2 | REPL: evaluate the single bar `(1000, 1050, 950, 1000)` with the default catalog | Evidence `status == "WARMUP"`; hits contain `doji` and `doji_long_legged` with status READY and polarity 0, and every other enabled rule as WARMUP with polarity 0; ids strictly increasing. |
| 3.3 | REPL: 20 context bars `(1000, 1060, 980, 1040)`, then `(1000, 1010, 890, 900)`, then `(950, 980, 920, 952)` | Hits exactly `bullish_harami (+1), doji (0), doji_long_legged (0)`, all READY; status READY. |
| 3.4 | REPL: 8 x `(10, 10.6, 9.8, 10.4)`, `(10, 10.6, 8.9, 9.0)`, 3 x `(10, 10.6, 9.8, 10.4)`, `(9.55, 9.62, 8.5, 9.6)` | Hits exactly `doji (0)`, `doji_dragonfly (0)`, `hammer (+1)`, `hanging_man (-1)`, all READY, status READY (13 bars, so the stars are ready too); real TA-Lib hammer is 100; `legacy_label(hits) == "hammer"`. |
| 3.5 | REPL: the six legacy fixtures of `test_candlestick_detector.py` after 20 float context candles, evaluated by the catalog and by `perception.candlestick.detect_pattern` at every prefix | `legacy_label(catalog hits) == detect_pattern(prefix)` for every prefix of every fixture. |
| 3.6 | `grep -n "candle_" tools/perception_quality.py` | `candle_contract`, `candle_catalog` (and, after T4/T5, `candle_context`, `candle_sequence`) appear in the ALLOWED registry with their permitted imports; no `chain` or `engine` import allowed. |
| 3.7 | `uv run python tools/perception_quality.py --help` then the Pure gate: `make check-perception` | Exits 0 if Docker is available; otherwise record BLOCKED with the Docker error and run `uv run pytest algo-backtest/tests/steps/test_candle_catalog.py algo-backtest/tests/steps/test_candlestick_detector.py -q` as the host-side substitute (must pass). |
| 3.8 | `uv run pytest algo-backtest/tests/steps/test_candle_catalog.py --cov=algo_backtest.perception.candle_catalog --cov-report=term-missing -q` | 100% line coverage for the new pure module (record the actual figure). |

## 4. T4 — Context (`candle_context.py`)

| Step | Command / action | Expected observable outcome |
| --- | --- | --- |
| 4.1 | `uv run pytest algo-backtest/tests/steps/test_candle_context.py -q` | Collected >= 50 items (15 templates, 52 rows expected), 0 failed, 0 skipped. |
| 4.2 | REPL: closes 1..10 as hourly bars | EMA values None x7, then 4.5, 5.5, 6.5; `t_line_position == "ABOVE"` from bar 8. |
| 4.3 | REPL: 12 bars open 15 / high 20 / low 10 / close 15, then closes 18, 12, 19.5, 13.5 | At bar 16: raw %K 35, slow %K 50, %D 55, zone NEUTRAL; at bar 12: raw 50, slow None (WARMUP). |
| 4.4 | REPL: 16 flat bars `(1000, 1000, 1000, 1000)` | Stochastic status UNDEFINED, values None, no exception, no NaN anywhere (`math.isnan` on every float field is False). |
| 4.5 | REPL: 100 closes at 8 then 100 at 12 | Distances 20 -> 0.0, 50 -> 0.0, 200 -> 0.2; with 199 bars the 200 level is WARMUP and the context status is WARMUP. |
| 4.6 | REPL: `ContextConfig(ema_period=0)` (or the T4 config type) | `ValueError` naming `ema_period`. |
| 4.7 | `uv run ruff check --select C901 algo-backtest/src/algo_backtest/perception/candle_context.py` | Exit 0 (no function above complexity 8). |

## 5. T5 — Sequence (`candle_sequence.py`)

| Step | Command / action | Expected observable outcome |
| --- | --- | --- |
| 5.1 | `uv run pytest algo-backtest/tests/steps/test_candle_sequence.py -q` | Collected 20 items (15 templates), 0 failed, 0 skipped. |
| 5.2 | REPL: hourly bars `(1000, 1030, 990, 1020)`, `(1000, 1050, 950, 1000)`, `(990, 1060, 985, 1030)` from 01:00 UTC | States IDLE, CANDIDATE, CONFIRMED; `confirmed_direction == 1`; `confirmation_time == 03:00 UTC`; `candidate_close_time == 02:00 UTC`. |
| 5.3 | Same first two bars, third bar at 04:00 UTC (03:00 missing), continuous policy | State EXPIRED with reason `missing_expected_bar`; no confirmation. |
| 5.4 | REPL: doji at bar 2 then a doji again at bar 3 | Bar 3 is CANDIDATE with reason `not_engulfing`; its `candidate_close_time` is bar 3's close. |
| 5.5 | REPL: after a candidate, offer an invalid bar `low > high` | `ValueError`; state still CANDIDATE; the next valid engulfing confirms at its own close. |

## 6. T6 — F3 policy modes (`f3_pattern.py`)

| Step | Command / action | Expected observable outcome |
| --- | --- | --- |
| 6.1 | `uv run pytest algo-backtest/tests/steps/test_f3_policy_modes.py algo-backtest/tests/steps/test_f3_pattern.py -q` | Both files collected; f3_pattern count unchanged from step 0.2; 0 failed. |
| 6.2 | REPL: `parse_pattern_config({}, strategy="qa").mode` | `"legacy"`. |
| 6.3 | REPL: `parse_pattern_config({"mode": "required"}, strategy="qa")` | `ValueError` containing `pattern.mode must be one of legacy, advisory, required_entry`. |
| 6.4 | REPL: legacy config, `features={"candlestick_pattern": "hammer", "candle_evidence": <any READY bearish evidence>}` | `FilterResult(recommendation=BUY, veto=False, reason mentions "hammer")`: legacy ignores the evidence key. |
| 6.5 | REPL: `{"mode": "advisory"}` with evidence hits `hammer(+1)` and `hanging_man(-1)`, context READY/ABOVE/NEUTRAL | `ABSTAIN`, `veto False`, reason starts with `conflicting`. |
| 6.6 | REPL: `{"mode": "required_entry"}`, same evidence | `ABSTAIN`, `veto True`, reason starts with `conflicting`; `enrichment` records the hit ids, the mode and the veto reason. |
| 6.7 | REPL: `{"mode": "required_entry"}`, evidence `bullish_engulfing(+1)` READY, context READY/ABOVE/NEUTRAL | `BUY`, `veto False`. |
| 6.8 | REPL: `{"mode": "required_entry"}`, features without `candle_evidence` | `ValueError` naming `candle_evidence` and `required_entry`. |
| 6.9 | `grep -rn "candle_evidence" algo-backtest/src/algo_backtest/chain/filters/f3_pattern.py` | The key is documented in the module docstring's feature-key contract. |

## 7. Phase gate

| Step | Command / action | Expected observable outcome |
| --- | --- | --- |
| 7.1 | `make lint type` | Exit 0. |
| 7.2 | `uv run pytest algo-backtest/tests -q` | 0 failed; collected count = baseline (step 0.2 whole-suite figure recorded by the coder in `progress.md`) + the five new step files' counts. |
| 7.3 | `make check-perception-architecture` (or `uv run python tools/perception_quality.py` boundary check) | The four new perception modules import nothing from `chain`, `engine` or QuantConnect. |
| 7.4 | Open `progress.md` of this story | T1–T6 ticked in the same commits that delivered them; each entry has the gate command, cwd, exit status and collected/passed counts; BLOCKED gates named with their error. |
| 7.5 | Open `.specs/features/candlestick-context/tasks.md` and `spec.md` | T1–T6 "Done when" boxes are `[x]`; CND-01–09, CND-11, CND-12 statuses read `Implemented (Tn)`; the traceability coverage line still counts 21 active requirements. |
| 7.6 | `git -C /tmp/mba-impl-22 status --short` | Clean (everything committed); `git push -u origin feat/22-candlestick-rules` result recorded in `progress.md`. |

## Formulas assumed by the specifier

Stated in each feature file's description block; the T1 ledger adopts or disputes
each one explicitly. Per bar: body = |close − open|, range = high − low,
upper = high − max(open, close), lower = min(open, close) − low; a bar with
range == 0 matches no geometric rule. mid(prior) = (open[t−1] + close[t−1]) / 2.
net(3) = close[t−1] − close[t−4]. Book pages are printed pages (PDF page = printed
page + 6 in the major-signals chapter of the NAS scan); webinar times are transcript
timestamps.

| Rule / component | Formula | Source and status |
| --- | --- | --- |
| doji | body <= 0.10 × range | book 21 and 23 ("same or very near"); ratio conventional |
| doji_long_legged | doji and min(upper, lower) >= 0.30 × range | webinar 07:48; ratio conventional |
| doji_dragonfly | doji and upper <= 0.10 × range | webinar 07:54 |
| doji_gravestone | doji and lower <= 0.10 × range | webinar 08:05 |
| spinning_top | 0.10 × range < body <= 0.30 × range and upper >= body and lower >= body | book 20, webinar 29:56; ratios conventional |
| bullish_harami | prior bearish, current bullish, open > close[t−1] and close < open[t−1] (strict) | book 75 criteria 3 |
| bearish_harami | prior bullish, current bearish, open < close[t−1] and close > open[t−1] (strict) | book 81 criteria 3 |
| piercing_line | prior bearish, current bullish, open < close[t−1], close > mid(prior), close < open[t−1] | book 65, webinar 34:33; FX adaptation: open below prior close instead of prior low |
| dark_cloud_cover | prior bullish, current bearish, open > close[t−1], close < mid(prior), close > open[t−1] | book 70; same FX adaptation |
| bullish_kicker | prior bearish, current bullish, open >= open[t−1] | book 110 criteria 1, webinar 53:08; bodies touch or gap, no marubozu requirement |
| bearish_kicker | prior bullish, current bearish, open <= open[t−1] | same |
| hanging_man | body > 0, lower >= 2 × body, upper <= 0.10 × range, net(3) > 0 | book 60, webinar 30:14 and 33:17; net(3) conventional |
| inverted_hammer | body > 0, upper >= 2 × body, lower <= 0.10 × range, net(3) < 0 | book 91, webinar 38:39; net(3) conventional |
| legacy six | TA-Lib verbatim as in candlestick.py (CDLENGULFING sign, CDLHAMMER, CDLSHOOTINGSTAR, CDLMORNINGSTAR / CDLEVENINGSTAR penetration 0.3); lookbacks 3, 3, 12, 12, 13, 13 bars | book 37, 46, 53, 87, 97, 104; TA-Lib kept for byte-identical legacy behaviour |
| EMA(8) T-line | running SMA seed for the first 8 closes, then k = 2/9; READY at 8 bars; t_line_position ABOVE / BELOW / ON | webinar 10:49, 26:54; seeding from training.ema_series |
| Stochastic 12,3,3 | raw %K = 100 (close − LL12) / (HH12 − LL12); slow %K = SMA(3) of raw; %D = SMA(3) of slow; READY at 12 / 14 / 16 bars; HH == LL → UNDEFINED (None, no NaN); zones OVERBOUGHT %D > 80, OVERSOLD %D < 20, NEUTRAL otherwise (80 and 20 are NEUTRAL) | webinar 10:03, 50:17, 51:23 ("just simple moving average"); book 24 |
| SMA 20 / 50 / 200 | distance = (close − sma) / sma, per-period readiness | webinar 10:16, 14:45; book 24 |
| trend evidence | UP / DOWN / FLAT from t_line_position; WARMUP while the EMA is WARMUP | derived; separate from the catalog's net(3) |
| sequence confirmation | doji (catalog rule) → next expected bar whose body engulfs the doji body inclusively (open <= body low and close >= body high for bullish; mirrored for bearish); direction = confirming bar colour; confirmation_time = confirming close | webinar 24:13, 27:51; book 37 (one equal edge allowed) |
| expected next bar | candidate close + timeframe under the continuous policy; under a scheduled closure, the first aligned close strictly after the closure end; a later bar expires with missing_expected_bar | design.md timing section; policy content is a gap (see below) |
| F3 eligibility | candidate directions = polarities of READY directional hits ∪ direction of a sequence confirmed at this bar; +1 satisfied when context READY, t_line ABOVE, zone not OVERBOUGHT and not UNDEFINED; −1 mirrored with BELOW / OVERSOLD; eligible = exactly one satisfied candidate | slides 6–7, webinar 10:49–11:27 and 09:56–10:23 |
| F3 modes | advisory: BUY / SELL when eligible else ABSTAIN, veto always False; required_entry: same recommendation when eligible, otherwise ABSTAIN with veto True and reason code warmup / neutral_only / conflicting / context | spec CND-11, CND-12 |

TA-Lib is not used for the new rules: CDLDOJI, CDLHARAMI, CDLPIERCING,
CDLDARKCLOUDCOVER, CDLKICKING, CDLHANGINGMAN and CDLINVERTEDHAMMER use 10-bar
averaged thresholds, marubozu or range-gap conditions that differ from the table.

## Spec-precision gaps pinned by the specifier

Where spec.md, design.md or tasks.md do not define a precise outcome, the feature
files pin the choice below. The coder implements these choices; disputing one
requires amending the feature file and the ledger in the same commit.

1. **Engulfing lookback.** TA-Lib's CDLENGULFING lookback is 2, so the first output
   needs three bars. Choice: bullish/bearish engulfing lookback = 3 bars in the
   contract table and the warmup rows (not the 2 a two-candle shape suggests).
2. **WARMUP representation in hits.** The spec only says each hit has its own
   readiness. Choice: every enabled rule that is still warming appears in `hits` as a
   WARMUP entry with polarity 0; a READY rule that did not fire is omitted; evidence
   status is WARMUP while any enabled rule is WARMUP; READY hits are reported even then.
3. **Missing bars at the history layer.** design.md says unexplained missing bars
   invalidate the stream, but T5 must observe a missing expected bar to expire a
   candidate. Choice: the T2 history accepts a later aligned bar and reports the
   count of missing expected bars; T5 expires with `missing_expected_bar`; stream
   invalidation and the calendar policy belong to T7's manifest.
4. **Calendar policy content.** No policy is defined anywhere. Choice: T5 takes a
   policy object; the features use "continuous" and a generic scheduled-closure
   interval [from, to). The real FX weekend policy is registered by the T7 owner.
5. **Bar timestamp semantics.** `ClosedBarClock` emits the bucket start while the
   evidence contract needs a close time. Choice: `close_time` is the bucket END,
   aligned to the timeframe; T7 converts the clock's start timestamp.
6. **Trend precondition for hanging man and inverted hammer.** Neither source gives a
   computable "top/bottom of trend". Choice: net(3) = close[t−1] − close[t−4] inside
   the catalog (lookback 5 bars); equality (net = 0) is no hit; it is never merged
   with the T4 trend evidence.
7. **Doji family thresholds.** The sources say "same or very near". Choice:
   body <= 0.10 range; long-legged uses a range-relative 0.30 shadow threshold
   instead of the "2 × body" wording because a zero body makes any shadow qualify;
   variants are additional hits beside `doji`; dragonfly and gravestone are mutually
   exclusive with long-legged by construction.
8. **Spinning top thresholds.** Choice: body in (0.10, 0.30] of range with both
   shadows >= body; a doji-sized body is never a spinning top.
9. **Harami edges.** Book criteria are strict inequalities. Choice: an equal edge is
   not a harami (unlike TA-Lib CDLENGULFING's 80-score edge for engulfing).
10. **Piercing and dark cloud gap rule.** Spot FX has no intraday gaps. Choice: open
    beyond the prior CLOSE replaces the book's open beyond the prior LOW/HIGH; the
    midpoint is the prior BODY midpoint; close is strictly beyond it; a close reaching
    the prior open is engulfing, not piercing. The book range-gap variant is deferred.
11. **Kicker.** Choice: opposite colours with open at or beyond the prior open
    (bodies touch or gap); no marubozu, no "never retraces" intrabar condition;
    the book's true-kicker shadow rule is a deferred variant.
12. **Stochastic definition.** "12,3,3 with simple averaging" leaves the K mapping
    open. Choice: raw %K over 12 bars, slow %K = SMA(3), %D = SMA(3) of slow %K;
    zones from %D with strict 80/20; HH == LL is UNDEFINED, never NaN or an exception,
    and smoothed values consuming an undefined raw are UNDEFINED.
13. **EMA readiness.** `ema_series` produces values from the first bar. Choice: the
    context reports None/WARMUP until 8 closes exist, then the running-mean seed.
14. **Level distances.** Choice: (close − sma) / sma, dimensionless, 0.0 on a flat
    series; per-period readiness; SMA(200) needs max_history >= 200.
15. **max_history coverage.** "Never silently shorten a window" has no rule. Choice:
    max_history must be >= max(enabled rule lookbacks, ema_period,
    k + k_smooth + d − 2, every sma period), otherwise reject naming the offending
    lookback.
16. **Sequence engulfing definition.** Choice: body-only engulfing with inclusive
    edges and mandatory colour; a doji bar never confirms; a doji that ends a previous
    candidate reports state CANDIDATE with the reason of the previous candidate's end
    (`not_engulfing` or `missing_expected_bar`); the reason vocabulary is
    `confirmed`, `not_engulfing`, `missing_expected_bar`, None.
17. **Sequence ids and polarity.** Choice: `doji_engulfing_bullish` (+1) and
    `doji_engulfing_bearish` (−1); the sequence evaluator does not consult context.
18. **Required-entry context rule.** "Registered confirmation/context rules" are a T1
    output. Choice: only the T-line position and the stochastic zone gate eligibility
    (long: ABOVE and not OVERBOUGHT; short: BELOW and not OVERSOLD; ON or UNDEFINED
    blocks both); SMA distances are informational; a confirmed sequence adds a
    candidate direction and an opposite confirmation makes the evidence conflicting.
19. **Advisory semantics.** Choice: identical eligibility to required_entry, only the
    veto differs (always False); abstention reasons reuse the same codes.
20. **Veto reason codes and enrichment.** Choice: the reason's first token is one of
    `warmup`, `neutral_only`, `conflicting`, `context`; the reason also names the hit
    ids and the mode; the FilterResult enrichment records `candle_hits`, `candle_mode`
    and `candle_veto_reason`.
21. **Evidence feature key and failure mode.** Choice: `state.features["candle_evidence"]`
    holds a CandleEvidence; in advisory or required_entry mode a missing or non-evidence
    value raises ValueError naming `candle_evidence` and the mode; legacy mode ignores
    the key entirely and keeps reading `candlestick_pattern`.
22. **Config parse error text.** Choice: an invalid `pattern.mode` fails with
    `strategy '<name>': pattern.mode must be one of legacy, advisory, required_entry`;
    `pattern_mapping` gains a `mode` entry after `detector`.
23. **PatternHit validation depth.** Choice: the contract knows each rule's polarity
    and rejects a hit whose sign contradicts it (e.g. hammer −1), an unknown id, an
    empty rule_version, a WARMUP hit with non-zero polarity, and a status outside
    READY / WARMUP.
24. **Evidence status consistency.** Choice: READY evidence may not contain a WARMUP
    hit; WARMUP evidence must contain at least one; hits must be sorted by id and
    unique; history_count in [0, max_history].
25. **Book OCR conflict for the hanging man.** The criteria line on printed page 60
    reads "upper shadow" while the description says lower tail. Choice: follow the
    description (lower shadow >= 2 × body); the ledger records the OCR conflict.
26. **Boundary fixtures use integer prices.** Choice: all new-rule examples use
    integer OHLC so that every `<=` / `<` boundary is exact in floating point; the
    legacy fixtures keep their float values from test_candlestick_detector.py.
