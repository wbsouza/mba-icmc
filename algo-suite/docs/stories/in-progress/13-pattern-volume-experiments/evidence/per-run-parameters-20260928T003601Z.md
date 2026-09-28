# Per-run results and effective parameter appendix

Snapshot: 2026-09-28T00:36:01.988Z to 2026-09-28T00:36:02.274Z.
Clock tool confirmation: 2026-09-28 00:36:01 UTC.

Source values and SHA-256 hashes are archived in [the snapshot](snapshot-20260928T003601Z.json).
Each R reference joins one result, its own filter matrix, manifest, model hash,
configuration JSON/YAML, and parameter provenance. Values below are copied from
that run's archived JSON; missing means not archived, never a current default.
A configured filter or parameter does not prove its inputs existed or that the
engine enforced it. In these predecessor runs, F3 had no real detector.

The F1 EMA fields are upstream perception settings, and F2/F6 share upstream
price features. Runtime perception/model identity lines are listed separately.
An omitted F4 is explicitly inactive only when the archived filter list proves
it. Unknown activation is marked missing. YAML is preserved verbatim and hashed;
JSON is the source of the readable matrix. Full provenance is in the snapshot.
Historical YAML/provenance gaps are retained. No leverage claim is made from the
archived configuration fields.

## Result index

| Ref | Run | Status | Window | Closed trades | Return (%) | Max DD (%) |
| --- | --- | --- | --- | --- | --- | --- |
| [R01](#r01) | `a05-conservative/20260927T235638-8b7718142b17` | successful | 2015-09-01 to 2015-09-30 | 3 | -0.81 | 10.80 |
| [R02](#r02) | `a05-gated/20260927T235638-8b7715be556a` | running_no_final_manifest | missing final manifest; see process/script | missing | missing | missing |
| [R03](#r03) | `a05-risk1/20260927T235638-8b7718193cae` | successful | 2015-09-01 to 2015-09-30 | 552 | -55.28 | 55.40 |
| [R04](#r04) | `a05-selective/20260927T235638-8b7712414b28` | successful | 2015-09-01 to 2015-09-30 | 6 | -3.76 | 5.60 |
| [R05](#r05) | `a05-wide-stop/20260927T235638-8b771e83f1e0` | successful | 2015-09-01 to 2015-09-30 | 14 | -17.65 | 21.50 |
| [R06](#r06) | `baseline/20260927T044836-4cd12c922200` | successful | 2015-09-01 to 2015-09-30 | 0 | 0.00 | 0.00 |
| [R07](#r07) | `baseline/20260927T094856-5d34ecde9301` | successful | 2015-09-01 to 2015-09-30 | 1032 | -0.05 | 1.50 |
| [R08](#r08) | `baseline/20260927T234946-8b17461d5460` | successful | 2015-09-01 to 2015-09-30 | 320 | -52.57 | 53.80 |
| [R09](#r09) | `baseline/20260928T000257-8bcf7832dc99` | successful | 2015-10-01 to 2015-10-31 | 319 | -53.35 | 55.20 |
| [R10](#r10) | `baseline/20260928T001557-8c84def875ee` | running_no_final_manifest | missing final manifest; see process/script | missing | missing | missing |
| [R11](#r11) | `hybrid/20260927T053156-4f2ebf081eaf` | successful | 2015-09-01 to 2015-09-30 | 0 | 0.00 | 0.00 |
| [R12](#r12) | `hybrid/20260927T100447-5e124bec56dc` | successful | 2015-09-01 to 2015-09-30 | 1069 | 0.51 | 1.50 |
| [R13](#r13) | `hybrid/20260927T235410-8b548f4bfa30` | successful | 2015-09-01 to 2015-09-30 | 322 | -52.75 | 54.00 |
| [R14](#r14) | `hybrid/20260928T001007-8c33716e9a9f` | successful | 2015-10-01 to 2015-10-31 | 349 | -51.37 | 53.30 |
| [R15](#r15) | `ha-h1-template/20260928T000820-8c1aad8bf6ec` | successful | 2015-09-01 to 2015-09-30 | 144 | -53.47 | 55.80 |
| [R16](#r16) | `ha-h1-template-atr/20260928T000821-8c1ab34b3bea` | successful | 2015-09-01 to 2015-09-30 | 437 | -42.16 | 50.10 |
| [R17](#r17) | `ha-1r2r-template/20260928T000821-8c1ab730ce29` | successful | 2015-09-01 to 2015-09-30 | 0 | 0.00 | 0.00 |
| [R18](#r18) | `ha-setup-template/20260928T000821-8c1ab3550b58` | successful | 2015-09-01 to 2015-09-30 | 0 | 0.00 | 0.00 |
| [R19](#r19) | `baseline/20260928T000117-8bb8148c2302` | running_no_final_manifest | missing final manifest; see process/script | missing | missing | missing |
| [R20](#r20) | `hybrid/20260928T000142-8bbdd0d8fd2c` | running_no_final_manifest | missing final manifest; see process/script | missing | missing | missing |

## R01

Run: `a05-conservative/20260927T235638-8b7718142b17`.
Job: `2026-09-27-variant-sweep-sept`. Status: **successful**.

Result: 3 closed trades; return -0.81%; max drawdown 10.80%.
Run arguments: `{"cash":"10000"}`.

Model SHA-256 recorded by engine: `1a6fd37e96dee3a6f5d082c18afdf863909524636718d129f44eac8d6e4e831e`.
Job-selected model: `2026-09-26-six-month-pilot/baseline`, SHA-256
`1a6fd37e96dee3a6f5d082c18afdf863909524636718d129f44eac8d6e4e831e`. Engine identity matches the archived model.

| Artifact | Status | SHA-256 |
| --- | --- | --- |
| `run.json` | present | `3d8856722db39fd6fe3f520b448e9523126233e1b2827b7548cabd7d80283289` |
| `metrics.json` | present | `547333f8dab715d740cf1e214194bb47bb562a6c9ab9c7bf616e6d8035fecb52` |
| `strategy-config.json` | present | `ad0dd6643e351ae2ba60aa423114391a34bba042e8eed10ff5e423ebefc2b5d7` |
| `strategy-config.yaml` | present | `1c9664ee2f852143dda68aad384f5338906320ea10216b8ebd2c4a85e945b1a0` |
| `strategy-provenance.json` | present | `833ef66fb508f6da57bacefd8cf85172829e67d9f88b275cea7740f6e4f50159` |

| Filter | In archived chain | Effective values archived for this run | Missing fields |
| --- | --- | --- | --- |
| F1 (`f1_trend`) | yes | `{"price_features.ema_fast":3,"price_features.ema_slow":8,"price_features.ema_higher_tf":60}` | none in audited field list |
| F2 (`f2_indicator`) | yes | `{"indicator.macd_hist_threshold":0,"indicator.rsi_midline":50,"price_features.macd_fast":12,"price_features.macd_slow":26,"price_features.macd_signal":9,"price_features.rsi_period":14}` | none in audited field list |
| F3 (`f3_pattern`) | yes | `{"pattern.bearish_patterns":["bearish_engulfing","evening_star","shooting_star"],"pattern.bullish_patterns":["bullish_engulfing","hammer","morning_star"]}` | none in audited field list |
| F4 (`f4_news_context`) | no | missing (inactive) | news_context.event_intensity_veto_threshold, news_context.sentiment_direction_threshold |
| F5 (`f5_risk_guard`) | yes | `{"risk_guard.daily_drawdown_limit":-0.05,"risk_guard.weekly_drawdown_limit":-0.15,"risk_guard.max_concurrent_trades_per_account":2,"risk_guard.max_leverage":30,"risk_guard.portfolio_at_risk_cap":0.1}` | none in audited field list |
| F6 (`f6_capital_mgmt`) | yes | `{"capital_mgmt.assumed_leverage":30,"capital_mgmt.atr_multiplier":2,"capital_mgmt.lot_notional_units":100000,"capital_mgmt.min_reward_risk":2,"capital_mgmt.min_stop_factor":1.2,"capital_mgmt.min_stop_pips":10,"capital_mgmt.pip_value_per_lot":10,"capital_mgmt.risk_per_trade":0.01,"capital_mgmt.stop_distance_source":"atr","capital_mgmt.stop_loss_pips":20,"capital_mgmt.stop_loss_shrink":0,"capital_mgmt.targets":[{"at_level_ratio":2,"close_fraction":0.5}],"capital_mgmt.trail_stops":[{"at_level_ratio":0.5,"to_level_ratio":-0.66}],"price_features.atr_period":14,"price_features.swing_lookback_bars":60}` | none in audited field list |
| F7 (`f7_meta_learner`) | yes | `{"meta_learner.families":["trend","indicator","pattern"],"meta_learner.label_horizon_minutes":15,"meta_learner.regime_gate":false,"meta_learner.theta_high":0.6,"meta_learner.theta_low":0.4}` | none in audited field list |

Shared execution: `{"broker_stop_level_pips":0,"close_on_veto":false,"commission_per_lot":0,"min_hold_bars":15,"spread_pips":1}`.

Per-field provenance: `runs[reference=R01].files["strategy-provenance.json"].value` in the snapshot; each filter matrix also joins provenance by field.

Runtime identity evidence:

```text
2015-09-01 00:00:00 BASELINE_PERCEPTION_SOURCE=ema
2015-09-01 00:00:00 BASELINE_MODEL_SHA256=1a6fd37e96dee3a6f5d082c18afdf863909524636718d129f44eac8d6e4e831e
2026-09-28T00:16:02.8658520Z TRACE:: Debug: 2015-09-01 00:00:00 BASELINE_PERCEPTION_SOURCE=ema
2026-09-28T00:16:02.8658656Z TRACE:: Debug: 2015-09-01 00:00:00 BASELINE_MODEL_SHA256=1a6fd37e96dee3a6f5d082c18afdf863909524636718d129f44eac8d6e4e831e
```

## R02

Run: `a05-gated/20260927T235638-8b7715be556a`.
Job: `2026-09-27-variant-sweep-sept`. Status: **running_no_final_manifest**.

Result: missing final run.json and metrics.json; no provisional performance reported.
Run arguments: missing final manifest; launched arguments preserved in snapshot.processes.

Model SHA-256 recorded by engine: `1a6fd37e96dee3a6f5d082c18afdf863909524636718d129f44eac8d6e4e831e`.
Job-selected model: `2026-09-26-six-month-pilot/baseline`, SHA-256
`1a6fd37e96dee3a6f5d082c18afdf863909524636718d129f44eac8d6e4e831e`. Engine identity matches the archived model.

| Artifact | Status | SHA-256 |
| --- | --- | --- |
| `run.json` | missing | missing |
| `metrics.json` | missing | missing |
| `strategy-config.json` | present | `d5039f5b05fa716e2202e29f85ab8e7dde99bd0241029bbbe78f631567574cb4` |
| `strategy-config.yaml` | present | `5ea0edcd61d6f12a954fab8155331a3cfe28a6332d4ec67d2ddbcd55294b3cd7` |
| `strategy-provenance.json` | present | `88fd38e798785fac0a24e8c46912f4642697ccd93967c61d9fa11474e0f684ea` |

| Filter | In archived chain | Effective values archived for this run | Missing fields |
| --- | --- | --- | --- |
| F1 (`f1_trend`) | yes | `{"price_features.ema_fast":3,"price_features.ema_slow":8,"price_features.ema_higher_tf":60}` | none in audited field list |
| F2 (`f2_indicator`) | yes | `{"indicator.macd_hist_threshold":0,"indicator.rsi_midline":50,"price_features.macd_fast":12,"price_features.macd_slow":26,"price_features.macd_signal":9,"price_features.rsi_period":14}` | none in audited field list |
| F3 (`f3_pattern`) | yes | `{"pattern.bearish_patterns":["bearish_engulfing","evening_star","shooting_star"],"pattern.bullish_patterns":["bullish_engulfing","hammer","morning_star"]}` | none in audited field list |
| F4 (`f4_news_context`) | no | missing (inactive) | news_context.event_intensity_veto_threshold, news_context.sentiment_direction_threshold |
| F5 (`f5_risk_guard`) | yes | `{"risk_guard.daily_drawdown_limit":-0.05,"risk_guard.weekly_drawdown_limit":-0.15,"risk_guard.max_concurrent_trades_per_account":2,"risk_guard.max_leverage":30,"risk_guard.portfolio_at_risk_cap":0.1}` | none in audited field list |
| F6 (`f6_capital_mgmt`) | yes | `{"capital_mgmt.assumed_leverage":30,"capital_mgmt.atr_multiplier":2,"capital_mgmt.lot_notional_units":100000,"capital_mgmt.min_reward_risk":2,"capital_mgmt.min_stop_factor":1.2,"capital_mgmt.min_stop_pips":5,"capital_mgmt.pip_value_per_lot":10,"capital_mgmt.risk_per_trade":0.03,"capital_mgmt.stop_distance_source":"swing","capital_mgmt.stop_loss_pips":20,"capital_mgmt.stop_loss_shrink":0.2,"capital_mgmt.targets":[{"at_level_ratio":2,"close_fraction":0.5}],"capital_mgmt.trail_stops":[{"at_level_ratio":0.5,"to_level_ratio":-0.66}],"price_features.atr_period":14,"price_features.swing_lookback_bars":60}` | none in audited field list |
| F7 (`f7_meta_learner`) | yes | `{"meta_learner.families":["trend","indicator","pattern"],"meta_learner.label_horizon_minutes":15,"meta_learner.regime_gate":true,"meta_learner.theta_high":0.55,"meta_learner.theta_low":0.45}` | none in audited field list |

Shared execution: `{"broker_stop_level_pips":0,"close_on_veto":false,"commission_per_lot":0,"min_hold_bars":0,"spread_pips":1}`.

Per-field provenance: `runs[reference=R02].files["strategy-provenance.json"].value` in the snapshot; each filter matrix also joins provenance by field.

Runtime identity evidence:

```text
2026-09-28T00:32:06.2440719Z TRACE:: Debug: 2015-09-01 00:00:00 BASELINE_PERCEPTION_SOURCE=ema
2026-09-28T00:32:06.2440799Z TRACE:: Debug: 2015-09-01 00:00:00 BASELINE_MODEL_SHA256=1a6fd37e96dee3a6f5d082c18afdf863909524636718d129f44eac8d6e4e831e
```

## R03

Run: `a05-risk1/20260927T235638-8b7718193cae`.
Job: `2026-09-27-variant-sweep-sept`. Status: **successful**.

Result: 552 closed trades; return -55.28%; max drawdown 55.40%.
Run arguments: `{"cash":"10000"}`.

Model SHA-256 recorded by engine: `1a6fd37e96dee3a6f5d082c18afdf863909524636718d129f44eac8d6e4e831e`.
Job-selected model: `2026-09-26-six-month-pilot/baseline`, SHA-256
`1a6fd37e96dee3a6f5d082c18afdf863909524636718d129f44eac8d6e4e831e`. Engine identity matches the archived model.

| Artifact | Status | SHA-256 |
| --- | --- | --- |
| `run.json` | present | `2eb9c244e944763486165dd7bc34c653e1273efc787f66719bbd03fbac8767ca` |
| `metrics.json` | present | `db59a7d8050c10abb954eca19f3eaff0cb726152ede16dfb5f898abbda365cbf` |
| `strategy-config.json` | present | `eeaf99617c766d8d9f273957b83360dc875794cb1be69bb2b331f2c683e76b62` |
| `strategy-config.yaml` | present | `f8b3e953e069b78120d1dc4fed117410210a54322733fd89f0ca51f8a67486dc` |
| `strategy-provenance.json` | present | `9724d62cd6fafb1ce65a6020f203ce692acee6016f4d36a4e7ec9471c06e4c80` |

| Filter | In archived chain | Effective values archived for this run | Missing fields |
| --- | --- | --- | --- |
| F1 (`f1_trend`) | yes | `{"price_features.ema_fast":3,"price_features.ema_slow":8,"price_features.ema_higher_tf":60}` | none in audited field list |
| F2 (`f2_indicator`) | yes | `{"indicator.macd_hist_threshold":0,"indicator.rsi_midline":50,"price_features.macd_fast":12,"price_features.macd_slow":26,"price_features.macd_signal":9,"price_features.rsi_period":14}` | none in audited field list |
| F3 (`f3_pattern`) | yes | `{"pattern.bearish_patterns":["bearish_engulfing","evening_star","shooting_star"],"pattern.bullish_patterns":["bullish_engulfing","hammer","morning_star"]}` | none in audited field list |
| F4 (`f4_news_context`) | no | missing (inactive) | news_context.event_intensity_veto_threshold, news_context.sentiment_direction_threshold |
| F5 (`f5_risk_guard`) | yes | `{"risk_guard.daily_drawdown_limit":-0.05,"risk_guard.weekly_drawdown_limit":-0.15,"risk_guard.max_concurrent_trades_per_account":2,"risk_guard.max_leverage":30,"risk_guard.portfolio_at_risk_cap":0.1}` | none in audited field list |
| F6 (`f6_capital_mgmt`) | yes | `{"capital_mgmt.assumed_leverage":30,"capital_mgmt.atr_multiplier":2,"capital_mgmt.lot_notional_units":100000,"capital_mgmt.min_reward_risk":2,"capital_mgmt.min_stop_factor":1.2,"capital_mgmt.min_stop_pips":5,"capital_mgmt.pip_value_per_lot":10,"capital_mgmt.risk_per_trade":0.01,"capital_mgmt.stop_distance_source":"swing","capital_mgmt.stop_loss_pips":20,"capital_mgmt.stop_loss_shrink":0.2,"capital_mgmt.targets":[{"at_level_ratio":2,"close_fraction":0.5}],"capital_mgmt.trail_stops":[{"at_level_ratio":0.5,"to_level_ratio":-0.66}],"price_features.atr_period":14,"price_features.swing_lookback_bars":60}` | none in audited field list |
| F7 (`f7_meta_learner`) | yes | `{"meta_learner.families":["trend","indicator","pattern"],"meta_learner.label_horizon_minutes":15,"meta_learner.regime_gate":false,"meta_learner.theta_high":0.55,"meta_learner.theta_low":0.45}` | none in audited field list |

Shared execution: `{"broker_stop_level_pips":0,"close_on_veto":false,"commission_per_lot":0,"min_hold_bars":0,"spread_pips":1}`.

Per-field provenance: `runs[reference=R03].files["strategy-provenance.json"].value` in the snapshot; each filter matrix also joins provenance by field.

Runtime identity evidence:

```text
2015-09-01 00:00:00 BASELINE_PERCEPTION_SOURCE=ema
2015-09-01 00:00:00 BASELINE_MODEL_SHA256=1a6fd37e96dee3a6f5d082c18afdf863909524636718d129f44eac8d6e4e831e
2026-09-28T00:03:03.9261423Z TRACE:: Debug: 2015-09-01 00:00:00 BASELINE_PERCEPTION_SOURCE=ema
2026-09-28T00:03:03.9261483Z TRACE:: Debug: 2015-09-01 00:00:00 BASELINE_MODEL_SHA256=1a6fd37e96dee3a6f5d082c18afdf863909524636718d129f44eac8d6e4e831e
```

## R04

Run: `a05-selective/20260927T235638-8b7712414b28`.
Job: `2026-09-27-variant-sweep-sept`. Status: **successful**.

Result: 6 closed trades; return -3.76%; max drawdown 5.60%.
Run arguments: `{"cash":"10000"}`.

Model SHA-256 recorded by engine: `1a6fd37e96dee3a6f5d082c18afdf863909524636718d129f44eac8d6e4e831e`.
Job-selected model: `2026-09-26-six-month-pilot/baseline`, SHA-256
`1a6fd37e96dee3a6f5d082c18afdf863909524636718d129f44eac8d6e4e831e`. Engine identity matches the archived model.

| Artifact | Status | SHA-256 |
| --- | --- | --- |
| `run.json` | present | `d2ac3fff4ea24414ff308706c95499ddb2a065570611b2f9a5657e61cce0cf11` |
| `metrics.json` | present | `6117b64dd8ce7ec120cd3963aa08a85a2d0a6504d2d607d4dfe68b14c65c382f` |
| `strategy-config.json` | present | `e6d4fdb82649994d396bc6cdce10d78bba7902fbb741fe4aa413b3d865dc588b` |
| `strategy-config.yaml` | present | `effb98bb845c3447ffbd927458c6bb3848f7f8a1371e26963bc8c54fd95ebf9f` |
| `strategy-provenance.json` | present | `749a40cd6514af13d80f2dd158bcd1ce0af068138b3316d435979417335e6bb6` |

| Filter | In archived chain | Effective values archived for this run | Missing fields |
| --- | --- | --- | --- |
| F1 (`f1_trend`) | yes | `{"price_features.ema_fast":3,"price_features.ema_slow":8,"price_features.ema_higher_tf":60}` | none in audited field list |
| F2 (`f2_indicator`) | yes | `{"indicator.macd_hist_threshold":0,"indicator.rsi_midline":50,"price_features.macd_fast":12,"price_features.macd_slow":26,"price_features.macd_signal":9,"price_features.rsi_period":14}` | none in audited field list |
| F3 (`f3_pattern`) | yes | `{"pattern.bearish_patterns":["bearish_engulfing","evening_star","shooting_star"],"pattern.bullish_patterns":["bullish_engulfing","hammer","morning_star"]}` | none in audited field list |
| F4 (`f4_news_context`) | no | missing (inactive) | news_context.event_intensity_veto_threshold, news_context.sentiment_direction_threshold |
| F5 (`f5_risk_guard`) | yes | `{"risk_guard.daily_drawdown_limit":-0.05,"risk_guard.weekly_drawdown_limit":-0.15,"risk_guard.max_concurrent_trades_per_account":2,"risk_guard.max_leverage":30,"risk_guard.portfolio_at_risk_cap":0.1}` | none in audited field list |
| F6 (`f6_capital_mgmt`) | yes | `{"capital_mgmt.assumed_leverage":30,"capital_mgmt.atr_multiplier":2,"capital_mgmt.lot_notional_units":100000,"capital_mgmt.min_reward_risk":2,"capital_mgmt.min_stop_factor":1.2,"capital_mgmt.min_stop_pips":5,"capital_mgmt.pip_value_per_lot":10,"capital_mgmt.risk_per_trade":0.03,"capital_mgmt.stop_distance_source":"swing","capital_mgmt.stop_loss_pips":20,"capital_mgmt.stop_loss_shrink":0.2,"capital_mgmt.targets":[{"at_level_ratio":2,"close_fraction":0.5}],"capital_mgmt.trail_stops":[{"at_level_ratio":0.5,"to_level_ratio":-0.66}],"price_features.atr_period":14,"price_features.swing_lookback_bars":60}` | none in audited field list |
| F7 (`f7_meta_learner`) | yes | `{"meta_learner.families":["trend","indicator","pattern"],"meta_learner.label_horizon_minutes":15,"meta_learner.regime_gate":false,"meta_learner.theta_high":0.6,"meta_learner.theta_low":0.4}` | none in audited field list |

Shared execution: `{"broker_stop_level_pips":0,"close_on_veto":false,"commission_per_lot":0,"min_hold_bars":0,"spread_pips":1}`.

Per-field provenance: `runs[reference=R04].files["strategy-provenance.json"].value` in the snapshot; each filter matrix also joins provenance by field.

Runtime identity evidence:

```text
2015-09-01 00:00:00 BASELINE_PERCEPTION_SOURCE=ema
2015-09-01 00:00:00 BASELINE_MODEL_SHA256=1a6fd37e96dee3a6f5d082c18afdf863909524636718d129f44eac8d6e4e831e
2026-09-27T23:56:47.3701701Z TRACE:: Debug: 2015-09-01 00:00:00 BASELINE_PERCEPTION_SOURCE=ema
2026-09-27T23:56:47.3701792Z TRACE:: Debug: 2015-09-01 00:00:00 BASELINE_MODEL_SHA256=1a6fd37e96dee3a6f5d082c18afdf863909524636718d129f44eac8d6e4e831e
```

## R05

Run: `a05-wide-stop/20260927T235638-8b771e83f1e0`.
Job: `2026-09-27-variant-sweep-sept`. Status: **successful**.

Result: 14 closed trades; return -17.65%; max drawdown 21.50%.
Run arguments: `{"cash":"10000"}`.

Model SHA-256 recorded by engine: `1a6fd37e96dee3a6f5d082c18afdf863909524636718d129f44eac8d6e4e831e`.
Job-selected model: `2026-09-26-six-month-pilot/baseline`, SHA-256
`1a6fd37e96dee3a6f5d082c18afdf863909524636718d129f44eac8d6e4e831e`. Engine identity matches the archived model.

| Artifact | Status | SHA-256 |
| --- | --- | --- |
| `run.json` | present | `0d9f659db389fbb39605f4f6724d7f5daef2a8c92a9a819b74764b5cf2ad9608` |
| `metrics.json` | present | `9be3490221d41bf4d58e1c5c422131b26823da80f61d4117e702a2cd2f757d29` |
| `strategy-config.json` | present | `cf1e82705755338bc5146e76f76a1f2712d458a7d0bd2528b6de4b256633efb2` |
| `strategy-config.yaml` | present | `f11354891b3dd851777b5890bac72b2bbec9949df96c74abedb3cc029f885210` |
| `strategy-provenance.json` | present | `7536422bf2f31f931bc1c3a2564be94c9f3d39ab9e2184b1f92fffaae469ac67` |

| Filter | In archived chain | Effective values archived for this run | Missing fields |
| --- | --- | --- | --- |
| F1 (`f1_trend`) | yes | `{"price_features.ema_fast":3,"price_features.ema_slow":8,"price_features.ema_higher_tf":60}` | none in audited field list |
| F2 (`f2_indicator`) | yes | `{"indicator.macd_hist_threshold":0,"indicator.rsi_midline":50,"price_features.macd_fast":12,"price_features.macd_slow":26,"price_features.macd_signal":9,"price_features.rsi_period":14}` | none in audited field list |
| F3 (`f3_pattern`) | yes | `{"pattern.bearish_patterns":["bearish_engulfing","evening_star","shooting_star"],"pattern.bullish_patterns":["bullish_engulfing","hammer","morning_star"]}` | none in audited field list |
| F4 (`f4_news_context`) | no | missing (inactive) | news_context.event_intensity_veto_threshold, news_context.sentiment_direction_threshold |
| F5 (`f5_risk_guard`) | yes | `{"risk_guard.daily_drawdown_limit":-0.05,"risk_guard.weekly_drawdown_limit":-0.15,"risk_guard.max_concurrent_trades_per_account":2,"risk_guard.max_leverage":30,"risk_guard.portfolio_at_risk_cap":0.1}` | none in audited field list |
| F6 (`f6_capital_mgmt`) | yes | `{"capital_mgmt.assumed_leverage":30,"capital_mgmt.atr_multiplier":2,"capital_mgmt.lot_notional_units":100000,"capital_mgmt.min_reward_risk":2,"capital_mgmt.min_stop_factor":1.2,"capital_mgmt.min_stop_pips":10,"capital_mgmt.pip_value_per_lot":10,"capital_mgmt.risk_per_trade":0.03,"capital_mgmt.stop_distance_source":"atr","capital_mgmt.stop_loss_pips":20,"capital_mgmt.stop_loss_shrink":0,"capital_mgmt.targets":[{"at_level_ratio":2,"close_fraction":0.5}],"capital_mgmt.trail_stops":[{"at_level_ratio":0.5,"to_level_ratio":-0.66}],"price_features.atr_period":14,"price_features.swing_lookback_bars":60}` | none in audited field list |
| F7 (`f7_meta_learner`) | yes | `{"meta_learner.families":["trend","indicator","pattern"],"meta_learner.label_horizon_minutes":15,"meta_learner.regime_gate":false,"meta_learner.theta_high":0.55,"meta_learner.theta_low":0.45}` | none in audited field list |

Shared execution: `{"broker_stop_level_pips":0,"close_on_veto":false,"commission_per_lot":0,"min_hold_bars":0,"spread_pips":1}`.

Per-field provenance: `runs[reference=R05].files["strategy-provenance.json"].value` in the snapshot; each filter matrix also joins provenance by field.

Runtime identity evidence:

```text
2015-09-01 00:00:00 BASELINE_PERCEPTION_SOURCE=ema
2015-09-01 00:00:00 BASELINE_MODEL_SHA256=1a6fd37e96dee3a6f5d082c18afdf863909524636718d129f44eac8d6e4e831e
2026-09-28T00:07:00.8363711Z TRACE:: Debug: 2015-09-01 00:00:00 BASELINE_PERCEPTION_SOURCE=ema
2026-09-28T00:07:00.8363800Z TRACE:: Debug: 2015-09-01 00:00:00 BASELINE_MODEL_SHA256=1a6fd37e96dee3a6f5d082c18afdf863909524636718d129f44eac8d6e4e831e
```

## R06

Run: `baseline/20260927T044836-4cd12c922200`.
Job: `2026-09-26-six-month-pilot`. Status: **successful**.

Result: 0 closed trades; return 0.00%; max drawdown 0.00%.
Run arguments: `{"size":"0.5"}`.

Model SHA-256 recorded by engine: `1a6fd37e96dee3a6f5d082c18afdf863909524636718d129f44eac8d6e4e831e`.
Job-selected model: `2026-09-26-six-month-pilot/baseline`, SHA-256
`1a6fd37e96dee3a6f5d082c18afdf863909524636718d129f44eac8d6e4e831e`. Engine identity matches the archived model.

| Artifact | Status | SHA-256 |
| --- | --- | --- |
| `run.json` | present | `3aa195967b2f4354c87b35fe0be4062c1f1a228d5bc9f891c82c5cd83c9610ac` |
| `metrics.json` | present | `a9108757eec327723ea83d7b12588abe64febf7d45935f7f7b166d412d568908` |
| `strategy-config.json` | present | `ac87e0ee0ae3b3fdade7deec30bd4327c5f1b6a9c41d37198cf0f9f26172a66c` |
| `strategy-config.yaml` | missing | missing |
| `strategy-provenance.json` | missing | missing |

| Filter | In archived chain | Effective values archived for this run | Missing fields |
| --- | --- | --- | --- |
| F1 (`f1_trend`) | yes | missing | price_features.ema_fast, price_features.ema_slow, price_features.ema_higher_tf |
| F2 (`f2_indicator`) | yes | missing | indicator.macd_hist_threshold, indicator.rsi_midline, price_features.macd_fast, price_features.macd_slow, price_features.macd_signal, price_features.rsi_period |
| F3 (`f3_pattern`) | yes | missing | pattern.bearish_patterns, pattern.bullish_patterns |
| F4 (`f4_news_context`) | no | missing (inactive) | news_context.event_intensity_veto_threshold, news_context.sentiment_direction_threshold |
| F5 (`f5_risk_guard`) | yes | missing | risk_guard.daily_drawdown_limit, risk_guard.weekly_drawdown_limit, risk_guard.max_concurrent_trades_per_account, risk_guard.max_leverage, risk_guard.portfolio_at_risk_cap |
| F6 (`f6_capital_mgmt`) | yes | missing | capital_mgmt.assumed_leverage, capital_mgmt.atr_multiplier, capital_mgmt.lot_notional_units, capital_mgmt.min_reward_risk, capital_mgmt.min_stop_factor, capital_mgmt.min_stop_pips, capital_mgmt.pip_value_per_lot, capital_mgmt.risk_per_trade, capital_mgmt.stop_distance_source, capital_mgmt.stop_loss_pips, capital_mgmt.stop_loss_shrink, capital_mgmt.targets, capital_mgmt.trail_stops, price_features.atr_period, price_features.swing_lookback_bars |
| F7 (`f7_meta_learner`) | yes | `{"meta_learner.families":["trend","indicator","pattern"]}` | meta_learner.label_horizon_minutes, meta_learner.regime_gate, meta_learner.theta_high, meta_learner.theta_low |

Shared execution: missing.

Per-field provenance: missing; no reconstruction from present-day YAML.

Runtime identity evidence:

```text
2015-09-01 00:00:00 BASELINE_PERCEPTION_SOURCE=ema
2015-09-01 00:00:00 BASELINE_MODEL_SHA256=1a6fd37e96dee3a6f5d082c18afdf863909524636718d129f44eac8d6e4e831e
2026-09-27T04:48:43.2183576Z TRACE:: Debug: 2015-09-01 00:00:00 BASELINE_PERCEPTION_SOURCE=ema
2026-09-27T04:48:43.2183886Z TRACE:: Debug: 2015-09-01 00:00:00 BASELINE_MODEL_SHA256=1a6fd37e96dee3a6f5d082c18afdf863909524636718d129f44eac8d6e4e831e
```

## R07

Run: `baseline/20260927T094856-5d34ecde9301`.
Job: `2026-09-27-f7-ungated-september`. Status: **successful**.

Result: 1032 closed trades; return -0.05%; max drawdown 1.50%.
Run arguments: `{"size":"0.5","cash":"10000"}`.

Model SHA-256 recorded by engine: `1a6fd37e96dee3a6f5d082c18afdf863909524636718d129f44eac8d6e4e831e`.
Job-selected model: `2026-09-26-six-month-pilot/baseline`, SHA-256
`1a6fd37e96dee3a6f5d082c18afdf863909524636718d129f44eac8d6e4e831e`. Engine identity matches the archived model.

| Artifact | Status | SHA-256 |
| --- | --- | --- |
| `run.json` | present | `24562772308f1ef9a9037eceef75db4751864e6beec07e3898e5b6268c5e8b74` |
| `metrics.json` | present | `7f8462a201603af26a907b858bebfaf97cd5e4ff91795fe68cae7401a9b5e87b` |
| `strategy-config.json` | present | `a985dc786435b1b21bae41916da3e800356c1cd1094a90185fddd87bdf590470` |
| `strategy-config.yaml` | missing | missing |
| `strategy-provenance.json` | missing | missing |

| Filter | In archived chain | Effective values archived for this run | Missing fields |
| --- | --- | --- | --- |
| F1 (`f1_trend`) | yes | missing | price_features.ema_fast, price_features.ema_slow, price_features.ema_higher_tf |
| F2 (`f2_indicator`) | yes | missing | indicator.macd_hist_threshold, indicator.rsi_midline, price_features.macd_fast, price_features.macd_slow, price_features.macd_signal, price_features.rsi_period |
| F3 (`f3_pattern`) | yes | missing | pattern.bearish_patterns, pattern.bullish_patterns |
| F4 (`f4_news_context`) | no | missing (inactive) | news_context.event_intensity_veto_threshold, news_context.sentiment_direction_threshold |
| F5 (`f5_risk_guard`) | yes | `{"risk_guard.daily_drawdown_limit":-0.05,"risk_guard.weekly_drawdown_limit":-0.15,"risk_guard.max_concurrent_trades_per_account":5,"risk_guard.max_leverage":30,"risk_guard.portfolio_at_risk_cap":0.1}` | none in audited field list |
| F6 (`f6_capital_mgmt`) | yes | `{"capital_mgmt.assumed_leverage":30,"capital_mgmt.lot_notional_units":100000,"capital_mgmt.pip_value_per_lot":10,"capital_mgmt.risk_per_trade":0.03,"capital_mgmt.stop_loss_pips":20}` | capital_mgmt.atr_multiplier, capital_mgmt.min_reward_risk, capital_mgmt.min_stop_factor, capital_mgmt.min_stop_pips, capital_mgmt.stop_distance_source, capital_mgmt.stop_loss_shrink, capital_mgmt.targets, capital_mgmt.trail_stops, price_features.atr_period, price_features.swing_lookback_bars |
| F7 (`f7_meta_learner`) | yes | `{"meta_learner.families":["trend","indicator","pattern"],"meta_learner.regime_gate":false,"meta_learner.theta_high":0.55,"meta_learner.theta_low":0.45}` | meta_learner.label_horizon_minutes |

Shared execution: missing.

Per-field provenance: missing; no reconstruction from present-day YAML.

Runtime identity evidence:

```text
2015-09-01 00:00:00 BASELINE_PERCEPTION_SOURCE=ema
2015-09-01 00:00:00 BASELINE_MODEL_SHA256=1a6fd37e96dee3a6f5d082c18afdf863909524636718d129f44eac8d6e4e831e
2026-09-27T09:49:04.9081833Z TRACE:: Debug: 2015-09-01 00:00:00 BASELINE_PERCEPTION_SOURCE=ema
2026-09-27T09:49:04.9081919Z TRACE:: Debug: 2015-09-01 00:00:00 BASELINE_MODEL_SHA256=1a6fd37e96dee3a6f5d082c18afdf863909524636718d129f44eac8d6e4e831e
```

## R08

Run: `baseline/20260927T234946-8b17461d5460`.
Job: `2026-09-27-execution-realism`. Status: **successful**.

Result: 320 closed trades; return -52.57%; max drawdown 53.80%.
Run arguments: `{"cash":"10000"}`.

Model SHA-256 recorded by engine: `1a6fd37e96dee3a6f5d082c18afdf863909524636718d129f44eac8d6e4e831e`.
Job-selected model: `2026-09-26-six-month-pilot/baseline`, SHA-256
`1a6fd37e96dee3a6f5d082c18afdf863909524636718d129f44eac8d6e4e831e`. Engine identity matches the archived model.

| Artifact | Status | SHA-256 |
| --- | --- | --- |
| `run.json` | present | `cf7a288e6d566b6e724e9147fb72a80f520572b2023c00da6b345b96541d3f19` |
| `metrics.json` | present | `4258dc7035ecc94caddd9d14d8782aa6b26c5250dc5cffc8949f5aceab703560` |
| `strategy-config.json` | present | `8f03f137411e0484d42261c6ccff73f1964eb17fe3c0473b5ac16f0bf04a196a` |
| `strategy-config.yaml` | present | `28e0057a38da27e6e22bd0e05b893824d278ff88b35d2d950a21548af26cfbb5` |
| `strategy-provenance.json` | present | `0eaa1a0740d2a6d79c2b22027b0fabc3d2d77c24ef999fb0214370aaea35b0e3` |

| Filter | In archived chain | Effective values archived for this run | Missing fields |
| --- | --- | --- | --- |
| F1 (`f1_trend`) | yes | `{"price_features.ema_fast":3,"price_features.ema_slow":8,"price_features.ema_higher_tf":60}` | none in audited field list |
| F2 (`f2_indicator`) | yes | `{"indicator.macd_hist_threshold":0,"indicator.rsi_midline":50,"price_features.macd_fast":12,"price_features.macd_slow":26,"price_features.macd_signal":9,"price_features.rsi_period":14}` | none in audited field list |
| F3 (`f3_pattern`) | yes | `{"pattern.bearish_patterns":["bearish_engulfing","evening_star","shooting_star"],"pattern.bullish_patterns":["bullish_engulfing","hammer","morning_star"]}` | none in audited field list |
| F4 (`f4_news_context`) | no | missing (inactive) | news_context.event_intensity_veto_threshold, news_context.sentiment_direction_threshold |
| F5 (`f5_risk_guard`) | yes | `{"risk_guard.daily_drawdown_limit":-0.05,"risk_guard.weekly_drawdown_limit":-0.15,"risk_guard.max_concurrent_trades_per_account":2,"risk_guard.max_leverage":30,"risk_guard.portfolio_at_risk_cap":0.1}` | none in audited field list |
| F6 (`f6_capital_mgmt`) | yes | `{"capital_mgmt.assumed_leverage":30,"capital_mgmt.atr_multiplier":2,"capital_mgmt.lot_notional_units":100000,"capital_mgmt.min_reward_risk":2,"capital_mgmt.min_stop_factor":1.2,"capital_mgmt.min_stop_pips":5,"capital_mgmt.pip_value_per_lot":10,"capital_mgmt.risk_per_trade":0.03,"capital_mgmt.stop_distance_source":"swing","capital_mgmt.stop_loss_pips":20,"capital_mgmt.stop_loss_shrink":0.2,"capital_mgmt.targets":[{"at_level_ratio":2,"close_fraction":0.5}],"capital_mgmt.trail_stops":[{"at_level_ratio":0.5,"to_level_ratio":-0.66}],"price_features.atr_period":14,"price_features.swing_lookback_bars":60}` | none in audited field list |
| F7 (`f7_meta_learner`) | yes | `{"meta_learner.families":["trend","indicator","pattern"],"meta_learner.label_horizon_minutes":15,"meta_learner.regime_gate":false,"meta_learner.theta_high":0.55,"meta_learner.theta_low":0.45}` | none in audited field list |

Shared execution: `{"broker_stop_level_pips":0,"close_on_veto":false,"commission_per_lot":0,"min_hold_bars":0,"spread_pips":1}`.

Per-field provenance: `runs[reference=R08].files["strategy-provenance.json"].value` in the snapshot; each filter matrix also joins provenance by field.

Runtime identity evidence:

```text
2015-09-01 00:00:00 BASELINE_PERCEPTION_SOURCE=ema
2015-09-01 00:00:00 BASELINE_MODEL_SHA256=1a6fd37e96dee3a6f5d082c18afdf863909524636718d129f44eac8d6e4e831e
2026-09-27T23:49:55.6037702Z TRACE:: Debug: 2015-09-01 00:00:00 BASELINE_PERCEPTION_SOURCE=ema
2026-09-27T23:49:55.6037769Z TRACE:: Debug: 2015-09-01 00:00:00 BASELINE_MODEL_SHA256=1a6fd37e96dee3a6f5d082c18afdf863909524636718d129f44eac8d6e4e831e
```

## R09

Run: `baseline/20260928T000257-8bcf7832dc99`.
Job: `2026-09-27-execution-realism`. Status: **successful**.

Result: 319 closed trades; return -53.35%; max drawdown 55.20%.
Run arguments: `{"cash":"10000"}`.

Model SHA-256 recorded by engine: `1a6fd37e96dee3a6f5d082c18afdf863909524636718d129f44eac8d6e4e831e`.
Job-selected model: `2026-09-26-six-month-pilot/baseline`, SHA-256
`1a6fd37e96dee3a6f5d082c18afdf863909524636718d129f44eac8d6e4e831e`. Engine identity matches the archived model.

| Artifact | Status | SHA-256 |
| --- | --- | --- |
| `run.json` | present | `666022d2598a9f3681ff55887563213fc271e67b766f150febc5353eff310de0` |
| `metrics.json` | present | `5efc991729f79951b960d46f70b2fd6cae64495cee2e025d13ed8d429df2e415` |
| `strategy-config.json` | present | `8f03f137411e0484d42261c6ccff73f1964eb17fe3c0473b5ac16f0bf04a196a` |
| `strategy-config.yaml` | present | `28e0057a38da27e6e22bd0e05b893824d278ff88b35d2d950a21548af26cfbb5` |
| `strategy-provenance.json` | present | `0eaa1a0740d2a6d79c2b22027b0fabc3d2d77c24ef999fb0214370aaea35b0e3` |

| Filter | In archived chain | Effective values archived for this run | Missing fields |
| --- | --- | --- | --- |
| F1 (`f1_trend`) | yes | `{"price_features.ema_fast":3,"price_features.ema_slow":8,"price_features.ema_higher_tf":60}` | none in audited field list |
| F2 (`f2_indicator`) | yes | `{"indicator.macd_hist_threshold":0,"indicator.rsi_midline":50,"price_features.macd_fast":12,"price_features.macd_slow":26,"price_features.macd_signal":9,"price_features.rsi_period":14}` | none in audited field list |
| F3 (`f3_pattern`) | yes | `{"pattern.bearish_patterns":["bearish_engulfing","evening_star","shooting_star"],"pattern.bullish_patterns":["bullish_engulfing","hammer","morning_star"]}` | none in audited field list |
| F4 (`f4_news_context`) | no | missing (inactive) | news_context.event_intensity_veto_threshold, news_context.sentiment_direction_threshold |
| F5 (`f5_risk_guard`) | yes | `{"risk_guard.daily_drawdown_limit":-0.05,"risk_guard.weekly_drawdown_limit":-0.15,"risk_guard.max_concurrent_trades_per_account":2,"risk_guard.max_leverage":30,"risk_guard.portfolio_at_risk_cap":0.1}` | none in audited field list |
| F6 (`f6_capital_mgmt`) | yes | `{"capital_mgmt.assumed_leverage":30,"capital_mgmt.atr_multiplier":2,"capital_mgmt.lot_notional_units":100000,"capital_mgmt.min_reward_risk":2,"capital_mgmt.min_stop_factor":1.2,"capital_mgmt.min_stop_pips":5,"capital_mgmt.pip_value_per_lot":10,"capital_mgmt.risk_per_trade":0.03,"capital_mgmt.stop_distance_source":"swing","capital_mgmt.stop_loss_pips":20,"capital_mgmt.stop_loss_shrink":0.2,"capital_mgmt.targets":[{"at_level_ratio":2,"close_fraction":0.5}],"capital_mgmt.trail_stops":[{"at_level_ratio":0.5,"to_level_ratio":-0.66}],"price_features.atr_period":14,"price_features.swing_lookback_bars":60}` | none in audited field list |
| F7 (`f7_meta_learner`) | yes | `{"meta_learner.families":["trend","indicator","pattern"],"meta_learner.label_horizon_minutes":15,"meta_learner.regime_gate":false,"meta_learner.theta_high":0.55,"meta_learner.theta_low":0.45}` | none in audited field list |

Shared execution: `{"broker_stop_level_pips":0,"close_on_veto":false,"commission_per_lot":0,"min_hold_bars":0,"spread_pips":1}`.

Per-field provenance: `runs[reference=R09].files["strategy-provenance.json"].value` in the snapshot; each filter matrix also joins provenance by field.

Runtime identity evidence:

```text
2015-10-01 00:00:00 BASELINE_PERCEPTION_SOURCE=ema
2015-10-01 00:00:00 BASELINE_MODEL_SHA256=1a6fd37e96dee3a6f5d082c18afdf863909524636718d129f44eac8d6e4e831e
2026-09-28T00:07:37.7057583Z TRACE:: Debug: 2015-10-01 00:00:00 BASELINE_PERCEPTION_SOURCE=ema
2026-09-28T00:07:37.7057652Z TRACE:: Debug: 2015-10-01 00:00:00 BASELINE_MODEL_SHA256=1a6fd37e96dee3a6f5d082c18afdf863909524636718d129f44eac8d6e4e831e
```

## R10

Run: `baseline/20260928T001557-8c84def875ee`.
Job: `2026-09-27-execution-realism`. Status: **running_no_final_manifest**.

Result: missing final run.json and metrics.json; no provisional performance reported.
Run arguments: missing final manifest; launched arguments preserved in snapshot.processes.

Model SHA-256 recorded by engine: missing.
Job-selected model: `2026-09-26-six-month-pilot/baseline`, SHA-256
`1a6fd37e96dee3a6f5d082c18afdf863909524636718d129f44eac8d6e4e831e`. Job selection is not an engine confirmation.

| Artifact | Status | SHA-256 |
| --- | --- | --- |
| `run.json` | missing | missing |
| `metrics.json` | missing | missing |
| `strategy-config.json` | missing | missing |
| `strategy-config.yaml` | missing | missing |
| `strategy-provenance.json` | present | `0eaa1a0740d2a6d79c2b22027b0fabc3d2d77c24ef999fb0214370aaea35b0e3` |

| Filter | In archived chain | Effective values archived for this run | Missing fields |
| --- | --- | --- | --- |
| F1 (`f1_trend`) | missing | missing | price_features.ema_fast, price_features.ema_slow, price_features.ema_higher_tf |
| F2 (`f2_indicator`) | missing | missing | indicator.macd_hist_threshold, indicator.rsi_midline, price_features.macd_fast, price_features.macd_slow, price_features.macd_signal, price_features.rsi_period |
| F3 (`f3_pattern`) | missing | missing | pattern.bearish_patterns, pattern.bullish_patterns |
| F4 (`f4_news_context`) | missing | missing | news_context.event_intensity_veto_threshold, news_context.sentiment_direction_threshold |
| F5 (`f5_risk_guard`) | missing | missing | risk_guard.daily_drawdown_limit, risk_guard.weekly_drawdown_limit, risk_guard.max_concurrent_trades_per_account, risk_guard.max_leverage, risk_guard.portfolio_at_risk_cap |
| F6 (`f6_capital_mgmt`) | missing | missing | capital_mgmt.assumed_leverage, capital_mgmt.atr_multiplier, capital_mgmt.lot_notional_units, capital_mgmt.min_reward_risk, capital_mgmt.min_stop_factor, capital_mgmt.min_stop_pips, capital_mgmt.pip_value_per_lot, capital_mgmt.risk_per_trade, capital_mgmt.stop_distance_source, capital_mgmt.stop_loss_pips, capital_mgmt.stop_loss_shrink, capital_mgmt.targets, capital_mgmt.trail_stops, price_features.atr_period, price_features.swing_lookback_bars |
| F7 (`f7_meta_learner`) | missing | missing | meta_learner.families, meta_learner.label_horizon_minutes, meta_learner.regime_gate, meta_learner.theta_high, meta_learner.theta_low |

Shared execution: missing.

Per-field provenance: `runs[reference=R10].files["strategy-provenance.json"].value` in the snapshot; each filter matrix also joins provenance by field.

Runtime identity evidence:

```text
missing
```

## R11

Run: `hybrid/20260927T053156-4f2ebf081eaf`.
Job: `2026-09-26-six-month-pilot`. Status: **successful**.

Result: 0 closed trades; return 0.00%; max drawdown 0.00%.
Run arguments: `{"size":"0.5"}`.

Model SHA-256 recorded by engine: `a6dda4c2effc55868d7c4131b90c3343b624c6ae0432dd24903590f5306af9b7`.
Job-selected model: `2026-09-26-six-month-pilot/hybrid`, SHA-256
`a6dda4c2effc55868d7c4131b90c3343b624c6ae0432dd24903590f5306af9b7`. Engine identity matches the archived model.

| Artifact | Status | SHA-256 |
| --- | --- | --- |
| `run.json` | present | `31272cca1a9bdf58b4e175bd739a15902f778695e9ac682097ce586ea82d4ba9` |
| `metrics.json` | present | `a9108757eec327723ea83d7b12588abe64febf7d45935f7f7b166d412d568908` |
| `strategy-config.json` | present | `5481f40bc79e3734482f578f1eb8a3e76c136b20438b079282fe9117c9df64df` |
| `strategy-config.yaml` | missing | missing |
| `strategy-provenance.json` | missing | missing |

| Filter | In archived chain | Effective values archived for this run | Missing fields |
| --- | --- | --- | --- |
| F1 (`f1_trend`) | yes | missing | price_features.ema_fast, price_features.ema_slow, price_features.ema_higher_tf |
| F2 (`f2_indicator`) | yes | missing | indicator.macd_hist_threshold, indicator.rsi_midline, price_features.macd_fast, price_features.macd_slow, price_features.macd_signal, price_features.rsi_period |
| F3 (`f3_pattern`) | yes | missing | pattern.bearish_patterns, pattern.bullish_patterns |
| F4 (`f4_news_context`) | yes | missing | news_context.event_intensity_veto_threshold, news_context.sentiment_direction_threshold |
| F5 (`f5_risk_guard`) | yes | missing | risk_guard.daily_drawdown_limit, risk_guard.weekly_drawdown_limit, risk_guard.max_concurrent_trades_per_account, risk_guard.max_leverage, risk_guard.portfolio_at_risk_cap |
| F6 (`f6_capital_mgmt`) | yes | missing | capital_mgmt.assumed_leverage, capital_mgmt.atr_multiplier, capital_mgmt.lot_notional_units, capital_mgmt.min_reward_risk, capital_mgmt.min_stop_factor, capital_mgmt.min_stop_pips, capital_mgmt.pip_value_per_lot, capital_mgmt.risk_per_trade, capital_mgmt.stop_distance_source, capital_mgmt.stop_loss_pips, capital_mgmt.stop_loss_shrink, capital_mgmt.targets, capital_mgmt.trail_stops, price_features.atr_period, price_features.swing_lookback_bars |
| F7 (`f7_meta_learner`) | yes | `{"meta_learner.families":["trend","indicator","pattern","news"]}` | meta_learner.label_horizon_minutes, meta_learner.regime_gate, meta_learner.theta_high, meta_learner.theta_low |

Shared execution: missing.

Per-field provenance: missing; no reconstruction from present-day YAML.

Runtime identity evidence:

```text
2015-09-01 00:00:00 HYBRID_PERCEPTION_SOURCE=ema
2015-09-01 00:00:00 HYBRID_MODEL_SHA256=a6dda4c2effc55868d7c4131b90c3343b624c6ae0432dd24903590f5306af9b7
2026-09-27T05:32:05.0675385Z TRACE:: Debug: 2015-09-01 00:00:00 HYBRID_PERCEPTION_SOURCE=ema
2026-09-27T05:32:05.0675711Z TRACE:: Debug: 2015-09-01 00:00:00 HYBRID_MODEL_SHA256=a6dda4c2effc55868d7c4131b90c3343b624c6ae0432dd24903590f5306af9b7
```

## R12

Run: `hybrid/20260927T100447-5e124bec56dc`.
Job: `2026-09-27-f7-ungated-september`. Status: **successful**.

Result: 1069 closed trades; return 0.51%; max drawdown 1.50%.
Run arguments: `{"size":"0.5","cash":"10000"}`.

Model SHA-256 recorded by engine: `a6dda4c2effc55868d7c4131b90c3343b624c6ae0432dd24903590f5306af9b7`.
Job-selected model: `2026-09-26-six-month-pilot/hybrid`, SHA-256
`a6dda4c2effc55868d7c4131b90c3343b624c6ae0432dd24903590f5306af9b7`. Engine identity matches the archived model.

| Artifact | Status | SHA-256 |
| --- | --- | --- |
| `run.json` | present | `578fff3a67c3b1177429f4a0c54e74e960cf19c410e2d1f21161d3289a5c0b91` |
| `metrics.json` | present | `647939bad199478290eff77e27ad5c0bb43576a8eb01bf85c6b516618e3d3578` |
| `strategy-config.json` | present | `4c98a91ddaec72c626dfc2443cde3191a74bb075654d36e3b02909abbaa433f7` |
| `strategy-config.yaml` | missing | missing |
| `strategy-provenance.json` | missing | missing |

| Filter | In archived chain | Effective values archived for this run | Missing fields |
| --- | --- | --- | --- |
| F1 (`f1_trend`) | yes | missing | price_features.ema_fast, price_features.ema_slow, price_features.ema_higher_tf |
| F2 (`f2_indicator`) | yes | missing | indicator.macd_hist_threshold, indicator.rsi_midline, price_features.macd_fast, price_features.macd_slow, price_features.macd_signal, price_features.rsi_period |
| F3 (`f3_pattern`) | yes | missing | pattern.bearish_patterns, pattern.bullish_patterns |
| F4 (`f4_news_context`) | yes | `{"news_context.event_intensity_veto_threshold":-0.5,"news_context.sentiment_direction_threshold":0.15}` | none in audited field list |
| F5 (`f5_risk_guard`) | yes | `{"risk_guard.daily_drawdown_limit":-0.05,"risk_guard.weekly_drawdown_limit":-0.15,"risk_guard.max_concurrent_trades_per_account":5,"risk_guard.max_leverage":30,"risk_guard.portfolio_at_risk_cap":0.1}` | none in audited field list |
| F6 (`f6_capital_mgmt`) | yes | `{"capital_mgmt.assumed_leverage":30,"capital_mgmt.lot_notional_units":100000,"capital_mgmt.pip_value_per_lot":10,"capital_mgmt.risk_per_trade":0.03,"capital_mgmt.stop_loss_pips":20}` | capital_mgmt.atr_multiplier, capital_mgmt.min_reward_risk, capital_mgmt.min_stop_factor, capital_mgmt.min_stop_pips, capital_mgmt.stop_distance_source, capital_mgmt.stop_loss_shrink, capital_mgmt.targets, capital_mgmt.trail_stops, price_features.atr_period, price_features.swing_lookback_bars |
| F7 (`f7_meta_learner`) | yes | `{"meta_learner.families":["trend","indicator","pattern","news"],"meta_learner.regime_gate":false,"meta_learner.theta_high":0.55,"meta_learner.theta_low":0.45}` | meta_learner.label_horizon_minutes |

Shared execution: missing.

Per-field provenance: missing; no reconstruction from present-day YAML.

Runtime identity evidence:

```text
2015-09-01 00:00:00 HYBRID_PERCEPTION_SOURCE=ema
2015-09-01 00:00:00 HYBRID_MODEL_SHA256=a6dda4c2effc55868d7c4131b90c3343b624c6ae0432dd24903590f5306af9b7
2026-09-27T10:04:55.2351978Z TRACE:: Debug: 2015-09-01 00:00:00 HYBRID_PERCEPTION_SOURCE=ema
2026-09-27T10:04:55.2352047Z TRACE:: Debug: 2015-09-01 00:00:00 HYBRID_MODEL_SHA256=a6dda4c2effc55868d7c4131b90c3343b624c6ae0432dd24903590f5306af9b7
```

## R13

Run: `hybrid/20260927T235410-8b548f4bfa30`.
Job: `2026-09-27-execution-realism`. Status: **successful**.

Result: 322 closed trades; return -52.75%; max drawdown 54.00%.
Run arguments: `{"cash":"10000"}`.

Model SHA-256 recorded by engine: `a6dda4c2effc55868d7c4131b90c3343b624c6ae0432dd24903590f5306af9b7`.
Job-selected model: `2026-09-26-six-month-pilot/hybrid`, SHA-256
`a6dda4c2effc55868d7c4131b90c3343b624c6ae0432dd24903590f5306af9b7`. Engine identity matches the archived model.

| Artifact | Status | SHA-256 |
| --- | --- | --- |
| `run.json` | present | `c94c8020d01e651d54d792bc7ef876988c0947c54094adf60c60501a992012a8` |
| `metrics.json` | present | `1ac95a441bd5a2a7865c1d917d674ce1eb94014fa76b4b28530bb488fce2cb7c` |
| `strategy-config.json` | present | `8870dc6b0c7c33be5cba49ea2a3b99dd69fe7acc52ec4695a9cb3f58d4e4b97a` |
| `strategy-config.yaml` | present | `3351938f978d575d03349a9255955b8d09e17de96c67ccbef18e298d2ca82518` |
| `strategy-provenance.json` | present | `b552235daad5741ddb726031b6b5c0aabc16c5e4d2ac95d336ccda3f288f8f58` |

| Filter | In archived chain | Effective values archived for this run | Missing fields |
| --- | --- | --- | --- |
| F1 (`f1_trend`) | yes | `{"price_features.ema_fast":3,"price_features.ema_slow":8,"price_features.ema_higher_tf":60}` | none in audited field list |
| F2 (`f2_indicator`) | yes | `{"indicator.macd_hist_threshold":0,"indicator.rsi_midline":50,"price_features.macd_fast":12,"price_features.macd_slow":26,"price_features.macd_signal":9,"price_features.rsi_period":14}` | none in audited field list |
| F3 (`f3_pattern`) | yes | `{"pattern.bearish_patterns":["bearish_engulfing","evening_star","shooting_star"],"pattern.bullish_patterns":["bullish_engulfing","hammer","morning_star"]}` | none in audited field list |
| F4 (`f4_news_context`) | yes | `{"news_context.event_intensity_veto_threshold":-0.5,"news_context.sentiment_direction_threshold":0.15}` | none in audited field list |
| F5 (`f5_risk_guard`) | yes | `{"risk_guard.daily_drawdown_limit":-0.05,"risk_guard.weekly_drawdown_limit":-0.15,"risk_guard.max_concurrent_trades_per_account":2,"risk_guard.max_leverage":30,"risk_guard.portfolio_at_risk_cap":0.1}` | none in audited field list |
| F6 (`f6_capital_mgmt`) | yes | `{"capital_mgmt.assumed_leverage":30,"capital_mgmt.atr_multiplier":2,"capital_mgmt.lot_notional_units":100000,"capital_mgmt.min_reward_risk":2,"capital_mgmt.min_stop_factor":1.2,"capital_mgmt.min_stop_pips":5,"capital_mgmt.pip_value_per_lot":10,"capital_mgmt.risk_per_trade":0.03,"capital_mgmt.stop_distance_source":"swing","capital_mgmt.stop_loss_pips":20,"capital_mgmt.stop_loss_shrink":0.2,"capital_mgmt.targets":[{"at_level_ratio":2,"close_fraction":0.5}],"capital_mgmt.trail_stops":[{"at_level_ratio":0.5,"to_level_ratio":-0.66}],"price_features.atr_period":14,"price_features.swing_lookback_bars":60}` | none in audited field list |
| F7 (`f7_meta_learner`) | yes | `{"meta_learner.families":["trend","indicator","pattern","news"],"meta_learner.label_horizon_minutes":15,"meta_learner.regime_gate":false,"meta_learner.theta_high":0.55,"meta_learner.theta_low":0.45}` | none in audited field list |

Shared execution: `{"broker_stop_level_pips":0,"close_on_veto":false,"commission_per_lot":0,"min_hold_bars":0,"spread_pips":1}`.

Per-field provenance: `runs[reference=R13].files["strategy-provenance.json"].value` in the snapshot; each filter matrix also joins provenance by field.

Runtime identity evidence:

```text
2015-09-01 00:00:00 HYBRID_PERCEPTION_SOURCE=ema
2015-09-01 00:00:00 HYBRID_MODEL_SHA256=a6dda4c2effc55868d7c4131b90c3343b624c6ae0432dd24903590f5306af9b7
2026-09-27T23:54:18.7278846Z TRACE:: Debug: 2015-09-01 00:00:00 HYBRID_PERCEPTION_SOURCE=ema
2026-09-27T23:54:18.7279405Z TRACE:: Debug: 2015-09-01 00:00:00 HYBRID_MODEL_SHA256=a6dda4c2effc55868d7c4131b90c3343b624c6ae0432dd24903590f5306af9b7
```

## R14

Run: `hybrid/20260928T001007-8c33716e9a9f`.
Job: `2026-09-27-execution-realism`. Status: **successful**.

Result: 349 closed trades; return -51.37%; max drawdown 53.30%.
Run arguments: `{"cash":"10000"}`.

Model SHA-256 recorded by engine: `a6dda4c2effc55868d7c4131b90c3343b624c6ae0432dd24903590f5306af9b7`.
Job-selected model: `2026-09-26-six-month-pilot/hybrid`, SHA-256
`a6dda4c2effc55868d7c4131b90c3343b624c6ae0432dd24903590f5306af9b7`. Engine identity matches the archived model.

| Artifact | Status | SHA-256 |
| --- | --- | --- |
| `run.json` | present | `b55afe0cc6231384bd141487225ba038d3bef5d266535ae3dd14299c13018080` |
| `metrics.json` | present | `2641fab3a9fdc9e2303cc48976cce3711d129b634cc2640473649254b0fb22f3` |
| `strategy-config.json` | present | `8870dc6b0c7c33be5cba49ea2a3b99dd69fe7acc52ec4695a9cb3f58d4e4b97a` |
| `strategy-config.yaml` | present | `3351938f978d575d03349a9255955b8d09e17de96c67ccbef18e298d2ca82518` |
| `strategy-provenance.json` | present | `b552235daad5741ddb726031b6b5c0aabc16c5e4d2ac95d336ccda3f288f8f58` |

| Filter | In archived chain | Effective values archived for this run | Missing fields |
| --- | --- | --- | --- |
| F1 (`f1_trend`) | yes | `{"price_features.ema_fast":3,"price_features.ema_slow":8,"price_features.ema_higher_tf":60}` | none in audited field list |
| F2 (`f2_indicator`) | yes | `{"indicator.macd_hist_threshold":0,"indicator.rsi_midline":50,"price_features.macd_fast":12,"price_features.macd_slow":26,"price_features.macd_signal":9,"price_features.rsi_period":14}` | none in audited field list |
| F3 (`f3_pattern`) | yes | `{"pattern.bearish_patterns":["bearish_engulfing","evening_star","shooting_star"],"pattern.bullish_patterns":["bullish_engulfing","hammer","morning_star"]}` | none in audited field list |
| F4 (`f4_news_context`) | yes | `{"news_context.event_intensity_veto_threshold":-0.5,"news_context.sentiment_direction_threshold":0.15}` | none in audited field list |
| F5 (`f5_risk_guard`) | yes | `{"risk_guard.daily_drawdown_limit":-0.05,"risk_guard.weekly_drawdown_limit":-0.15,"risk_guard.max_concurrent_trades_per_account":2,"risk_guard.max_leverage":30,"risk_guard.portfolio_at_risk_cap":0.1}` | none in audited field list |
| F6 (`f6_capital_mgmt`) | yes | `{"capital_mgmt.assumed_leverage":30,"capital_mgmt.atr_multiplier":2,"capital_mgmt.lot_notional_units":100000,"capital_mgmt.min_reward_risk":2,"capital_mgmt.min_stop_factor":1.2,"capital_mgmt.min_stop_pips":5,"capital_mgmt.pip_value_per_lot":10,"capital_mgmt.risk_per_trade":0.03,"capital_mgmt.stop_distance_source":"swing","capital_mgmt.stop_loss_pips":20,"capital_mgmt.stop_loss_shrink":0.2,"capital_mgmt.targets":[{"at_level_ratio":2,"close_fraction":0.5}],"capital_mgmt.trail_stops":[{"at_level_ratio":0.5,"to_level_ratio":-0.66}],"price_features.atr_period":14,"price_features.swing_lookback_bars":60}` | none in audited field list |
| F7 (`f7_meta_learner`) | yes | `{"meta_learner.families":["trend","indicator","pattern","news"],"meta_learner.label_horizon_minutes":15,"meta_learner.regime_gate":false,"meta_learner.theta_high":0.55,"meta_learner.theta_low":0.45}` | none in audited field list |

Shared execution: `{"broker_stop_level_pips":0,"close_on_veto":false,"commission_per_lot":0,"min_hold_bars":0,"spread_pips":1}`.

Per-field provenance: `runs[reference=R14].files["strategy-provenance.json"].value` in the snapshot; each filter matrix also joins provenance by field.

Runtime identity evidence:

```text
2015-10-01 00:00:00 HYBRID_PERCEPTION_SOURCE=ema
2015-10-01 00:00:00 HYBRID_MODEL_SHA256=a6dda4c2effc55868d7c4131b90c3343b624c6ae0432dd24903590f5306af9b7
2026-09-28T00:12:22.0167284Z TRACE:: Debug: 2015-10-01 00:00:00 HYBRID_PERCEPTION_SOURCE=ema
2026-09-28T00:12:22.0167347Z TRACE:: Debug: 2015-10-01 00:00:00 HYBRID_MODEL_SHA256=a6dda4c2effc55868d7c4131b90c3343b624c6ae0432dd24903590f5306af9b7
```

## R15

Run: `ha-h1-template/20260928T000820-8c1aad8bf6ec`.
Job: `2026-09-27-variant-sweep-sept-b`. Status: **successful**.

Result: 144 closed trades; return -53.47%; max drawdown 55.80%.
Run arguments: `{"cash":"10000"}`.

Model SHA-256 recorded by engine: `1a6fd37e96dee3a6f5d082c18afdf863909524636718d129f44eac8d6e4e831e`.
Job-selected model: `2026-09-26-six-month-pilot/baseline`, SHA-256
`1a6fd37e96dee3a6f5d082c18afdf863909524636718d129f44eac8d6e4e831e`. Engine identity matches the archived model.

| Artifact | Status | SHA-256 |
| --- | --- | --- |
| `run.json` | present | `fde978510bc98629df7d38635102cc814ef5b149ec0fcf9bc54de7992d9a532b` |
| `metrics.json` | present | `99b753c01ac78eba57656d827a9988c5cd86851c718c4aadc07df06d40b5f1cd` |
| `strategy-config.json` | present | `ecee176de3a360c5f65576682b611b1ba7312ed12343e8ca5b6e684ed8b8c935` |
| `strategy-config.yaml` | present | `79076a8244c324c3474d2ad244bd7d060c69a01873c47ea2341808603d9c5722` |
| `strategy-provenance.json` | present | `a5b744ae67867958788bc10320455fc7782a51f888a1fc0ff32bd0c1fd1d2609` |

| Filter | In archived chain | Effective values archived for this run | Missing fields |
| --- | --- | --- | --- |
| F1 (`f1_trend`) | yes | `{"price_features.ema_fast":3,"price_features.ema_slow":8,"price_features.ema_higher_tf":60}` | none in audited field list |
| F2 (`f2_indicator`) | yes | `{"indicator.macd_hist_threshold":0,"indicator.rsi_midline":50,"price_features.macd_fast":12,"price_features.macd_slow":26,"price_features.macd_signal":9,"price_features.rsi_period":14}` | none in audited field list |
| F3 (`f3_pattern`) | yes | `{"pattern.bearish_patterns":["bearish_engulfing","evening_star","shooting_star"],"pattern.bullish_patterns":["bullish_engulfing","hammer","morning_star"]}` | none in audited field list |
| F4 (`f4_news_context`) | no | missing (inactive) | news_context.event_intensity_veto_threshold, news_context.sentiment_direction_threshold |
| F5 (`f5_risk_guard`) | yes | `{"risk_guard.daily_drawdown_limit":-0.05,"risk_guard.weekly_drawdown_limit":-0.15,"risk_guard.max_concurrent_trades_per_account":2,"risk_guard.max_leverage":30,"risk_guard.portfolio_at_risk_cap":0.1}` | none in audited field list |
| F6 (`f6_capital_mgmt`) | yes | `{"capital_mgmt.assumed_leverage":30,"capital_mgmt.atr_multiplier":2,"capital_mgmt.lot_notional_units":100000,"capital_mgmt.min_reward_risk":3,"capital_mgmt.min_stop_factor":1.2,"capital_mgmt.min_stop_pips":5,"capital_mgmt.pip_value_per_lot":10,"capital_mgmt.risk_per_trade":0.03,"capital_mgmt.stop_distance_source":"swing","capital_mgmt.stop_loss_pips":20,"capital_mgmt.stop_loss_shrink":0.5,"capital_mgmt.targets":[{"at_level_ratio":3,"close_fraction":1}],"capital_mgmt.trail_stops":[{"at_level_ratio":1,"to_level_ratio":-0.66},{"at_level_ratio":1.5,"to_level_ratio":0}],"price_features.atr_period":14,"price_features.swing_lookback_bars":60}` | none in audited field list |
| F7 (`f7_meta_learner`) | yes | `{"meta_learner.families":["trend","indicator","pattern"],"meta_learner.label_horizon_minutes":15,"meta_learner.regime_gate":false,"meta_learner.theta_high":0.55,"meta_learner.theta_low":0.45}` | none in audited field list |

Shared execution: `{"broker_stop_level_pips":0,"close_on_veto":false,"commission_per_lot":0,"min_hold_bars":0,"spread_pips":1}`.

Per-field provenance: `runs[reference=R15].files["strategy-provenance.json"].value` in the snapshot; each filter matrix also joins provenance by field.

Runtime identity evidence:

```text
2015-09-01 00:00:00 BASELINE_PERCEPTION_SOURCE=ema
2015-09-01 00:00:00 BASELINE_MODEL_SHA256=1a6fd37e96dee3a6f5d082c18afdf863909524636718d129f44eac8d6e4e831e
2026-09-28T00:10:36.5737232Z TRACE:: Debug: 2015-09-01 00:00:00 BASELINE_PERCEPTION_SOURCE=ema
2026-09-28T00:10:36.5737280Z TRACE:: Debug: 2015-09-01 00:00:00 BASELINE_MODEL_SHA256=1a6fd37e96dee3a6f5d082c18afdf863909524636718d129f44eac8d6e4e831e
```

## R16

Run: `ha-h1-template-atr/20260928T000821-8c1ab34b3bea`.
Job: `2026-09-27-variant-sweep-sept-b`. Status: **successful**.

Result: 437 closed trades; return -42.16%; max drawdown 50.10%.
Run arguments: `{"cash":"10000"}`.

Model SHA-256 recorded by engine: `1a6fd37e96dee3a6f5d082c18afdf863909524636718d129f44eac8d6e4e831e`.
Job-selected model: `2026-09-26-six-month-pilot/baseline`, SHA-256
`1a6fd37e96dee3a6f5d082c18afdf863909524636718d129f44eac8d6e4e831e`. Engine identity matches the archived model.

| Artifact | Status | SHA-256 |
| --- | --- | --- |
| `run.json` | present | `5b0be6696d8193f3a5e335bca079fb360d614e1958d5a8035c1adf110bbc8d55` |
| `metrics.json` | present | `a50c47014539770f3392d5cbd74984a0d58f92d8e9c5463f039900f01296a778` |
| `strategy-config.json` | present | `557b82527a4f3ad5e3456cb6fea437cab45de5ca2eac948b35048d8ed8fdfedc` |
| `strategy-config.yaml` | present | `3733d1a3e61082a368af370a5cb91ad6f82c11bf0964e475efb88b8292a6a129` |
| `strategy-provenance.json` | present | `9ba3871b94684948dd39e737a0e4681d3051957aa1ccebd07c378ccf4e1158c3` |

| Filter | In archived chain | Effective values archived for this run | Missing fields |
| --- | --- | --- | --- |
| F1 (`f1_trend`) | yes | `{"price_features.ema_fast":3,"price_features.ema_slow":8,"price_features.ema_higher_tf":60}` | none in audited field list |
| F2 (`f2_indicator`) | yes | `{"indicator.macd_hist_threshold":0,"indicator.rsi_midline":50,"price_features.macd_fast":12,"price_features.macd_slow":26,"price_features.macd_signal":9,"price_features.rsi_period":14}` | none in audited field list |
| F3 (`f3_pattern`) | yes | `{"pattern.bearish_patterns":["bearish_engulfing","evening_star","shooting_star"],"pattern.bullish_patterns":["bullish_engulfing","hammer","morning_star"]}` | none in audited field list |
| F4 (`f4_news_context`) | no | missing (inactive) | news_context.event_intensity_veto_threshold, news_context.sentiment_direction_threshold |
| F5 (`f5_risk_guard`) | yes | `{"risk_guard.daily_drawdown_limit":-0.05,"risk_guard.weekly_drawdown_limit":-0.15,"risk_guard.max_concurrent_trades_per_account":2,"risk_guard.max_leverage":30,"risk_guard.portfolio_at_risk_cap":0.1}` | none in audited field list |
| F6 (`f6_capital_mgmt`) | yes | `{"capital_mgmt.assumed_leverage":30,"capital_mgmt.atr_multiplier":4,"capital_mgmt.lot_notional_units":100000,"capital_mgmt.min_reward_risk":3,"capital_mgmt.min_stop_factor":1.2,"capital_mgmt.min_stop_pips":10,"capital_mgmt.pip_value_per_lot":10,"capital_mgmt.risk_per_trade":0.01,"capital_mgmt.stop_distance_source":"atr","capital_mgmt.stop_loss_pips":20,"capital_mgmt.stop_loss_shrink":0.5,"capital_mgmt.targets":[{"at_level_ratio":3,"close_fraction":1}],"capital_mgmt.trail_stops":[{"at_level_ratio":1,"to_level_ratio":-0.66},{"at_level_ratio":1.5,"to_level_ratio":0}],"price_features.atr_period":14,"price_features.swing_lookback_bars":60}` | none in audited field list |
| F7 (`f7_meta_learner`) | yes | `{"meta_learner.families":["trend","indicator","pattern"],"meta_learner.label_horizon_minutes":15,"meta_learner.regime_gate":false,"meta_learner.theta_high":0.55,"meta_learner.theta_low":0.45}` | none in audited field list |

Shared execution: `{"broker_stop_level_pips":0,"close_on_veto":false,"commission_per_lot":0,"min_hold_bars":0,"spread_pips":1}`.

Per-field provenance: `runs[reference=R16].files["strategy-provenance.json"].value` in the snapshot; each filter matrix also joins provenance by field.

Runtime identity evidence:

```text
2015-09-01 00:00:00 BASELINE_PERCEPTION_SOURCE=ema
2015-09-01 00:00:00 BASELINE_MODEL_SHA256=1a6fd37e96dee3a6f5d082c18afdf863909524636718d129f44eac8d6e4e831e
2026-09-28T00:10:07.6350575Z TRACE:: Debug: 2015-09-01 00:00:00 BASELINE_PERCEPTION_SOURCE=ema
2026-09-28T00:10:07.6350635Z TRACE:: Debug: 2015-09-01 00:00:00 BASELINE_MODEL_SHA256=1a6fd37e96dee3a6f5d082c18afdf863909524636718d129f44eac8d6e4e831e
```

## R17

Run: `ha-1r2r-template/20260928T000821-8c1ab730ce29`.
Job: `2026-09-27-variant-sweep-sept-b`. Status: **successful**.

Result: 0 closed trades; return 0.00%; max drawdown 0.00%.
Run arguments: `{"cash":"10000"}`.

Model SHA-256 recorded by engine: `1a6fd37e96dee3a6f5d082c18afdf863909524636718d129f44eac8d6e4e831e`.
Job-selected model: `2026-09-26-six-month-pilot/baseline`, SHA-256
`1a6fd37e96dee3a6f5d082c18afdf863909524636718d129f44eac8d6e4e831e`. Engine identity matches the archived model.

| Artifact | Status | SHA-256 |
| --- | --- | --- |
| `run.json` | present | `1116ac81b4ccd9895a8b0b418efe835cccd3999e756d9e8a9864ea91d3f0da1f` |
| `metrics.json` | present | `a9108757eec327723ea83d7b12588abe64febf7d45935f7f7b166d412d568908` |
| `strategy-config.json` | present | `f28e65bcc6d65813cd6d17db9543c6e16a1010ce9b9baf2cf4c964fd69f5e7dd` |
| `strategy-config.yaml` | present | `08110b936269dfdbb574b162d1ae9ff96a03bdfbf71e5913f95cb835b639e3fe` |
| `strategy-provenance.json` | present | `0477c5fa91de044447d90d4c2c0d82e906fd9d82433334b475c823b837f3005e` |

| Filter | In archived chain | Effective values archived for this run | Missing fields |
| --- | --- | --- | --- |
| F1 (`f1_trend`) | yes | `{"price_features.ema_fast":3,"price_features.ema_slow":8,"price_features.ema_higher_tf":60}` | none in audited field list |
| F2 (`f2_indicator`) | yes | `{"indicator.macd_hist_threshold":0,"indicator.rsi_midline":50,"price_features.macd_fast":12,"price_features.macd_slow":26,"price_features.macd_signal":9,"price_features.rsi_period":14}` | none in audited field list |
| F3 (`f3_pattern`) | yes | `{"pattern.bearish_patterns":["bearish_engulfing","evening_star","shooting_star"],"pattern.bullish_patterns":["bullish_engulfing","hammer","morning_star"]}` | none in audited field list |
| F4 (`f4_news_context`) | no | missing (inactive) | news_context.event_intensity_veto_threshold, news_context.sentiment_direction_threshold |
| F5 (`f5_risk_guard`) | yes | `{"risk_guard.daily_drawdown_limit":-0.05,"risk_guard.weekly_drawdown_limit":-0.15,"risk_guard.max_concurrent_trades_per_account":2,"risk_guard.max_leverage":30,"risk_guard.portfolio_at_risk_cap":0.1}` | none in audited field list |
| F6 (`f6_capital_mgmt`) | yes | `{"capital_mgmt.assumed_leverage":30,"capital_mgmt.atr_multiplier":2,"capital_mgmt.lot_notional_units":100000,"capital_mgmt.min_reward_risk":2,"capital_mgmt.min_stop_factor":1.2,"capital_mgmt.min_stop_pips":5,"capital_mgmt.pip_value_per_lot":10,"capital_mgmt.risk_per_trade":0.03,"capital_mgmt.stop_distance_source":"swing","capital_mgmt.stop_loss_pips":20,"capital_mgmt.stop_loss_shrink":0.5,"capital_mgmt.targets":[{"at_level_ratio":1,"close_fraction":0.5},{"at_level_ratio":2,"close_fraction":0.5}],"capital_mgmt.trail_stops":[{"at_level_ratio":1,"to_level_ratio":0}],"price_features.atr_period":14,"price_features.swing_lookback_bars":60}` | none in audited field list |
| F7 (`f7_meta_learner`) | yes | `{"meta_learner.families":["trend","indicator","pattern"],"meta_learner.label_horizon_minutes":15,"meta_learner.regime_gate":false,"meta_learner.theta_high":0.55,"meta_learner.theta_low":0.45}` | none in audited field list |

Shared execution: `{"broker_stop_level_pips":0,"close_on_veto":false,"commission_per_lot":0,"min_hold_bars":0,"spread_pips":1}`.

Per-field provenance: `runs[reference=R17].files["strategy-provenance.json"].value` in the snapshot; each filter matrix also joins provenance by field.

Runtime identity evidence:

```text
2015-09-01 00:00:00 BASELINE_PERCEPTION_SOURCE=ema
2015-09-01 00:00:00 BASELINE_MODEL_SHA256=1a6fd37e96dee3a6f5d082c18afdf863909524636718d129f44eac8d6e4e831e
2026-09-28T00:11:38.8222591Z TRACE:: Debug: 2015-09-01 00:00:00 BASELINE_PERCEPTION_SOURCE=ema
2026-09-28T00:11:38.8222691Z TRACE:: Debug: 2015-09-01 00:00:00 BASELINE_MODEL_SHA256=1a6fd37e96dee3a6f5d082c18afdf863909524636718d129f44eac8d6e4e831e
```

## R18

Run: `ha-setup-template/20260928T000821-8c1ab3550b58`.
Job: `2026-09-27-variant-sweep-sept-b`. Status: **successful**.

Result: 0 closed trades; return 0.00%; max drawdown 0.00%.
Run arguments: `{"cash":"10000"}`.

Model SHA-256 recorded by engine: `1a6fd37e96dee3a6f5d082c18afdf863909524636718d129f44eac8d6e4e831e`.
Job-selected model: `2026-09-26-six-month-pilot/baseline`, SHA-256
`1a6fd37e96dee3a6f5d082c18afdf863909524636718d129f44eac8d6e4e831e`. Engine identity matches the archived model.

| Artifact | Status | SHA-256 |
| --- | --- | --- |
| `run.json` | present | `6b41341de67e07c72688158490d3e1e941c2acccd7b9bd2a2fc2b61ef0c5aa48` |
| `metrics.json` | present | `a9108757eec327723ea83d7b12588abe64febf7d45935f7f7b166d412d568908` |
| `strategy-config.json` | present | `b0307b9fa66acfbad345359f99fa9bf1cf697f5d077fc48729a2440865d214fe` |
| `strategy-config.yaml` | present | `730f99e977ae1bff4cb30b1f3e39fc345f198079eef29f20dc5f8357ffeb277a` |
| `strategy-provenance.json` | present | `e690b2c59b53db9018248f0bf5b49cba77f45c57924bdf3805e0a533e5cdb5db` |

| Filter | In archived chain | Effective values archived for this run | Missing fields |
| --- | --- | --- | --- |
| F1 (`f1_trend`) | yes | `{"price_features.ema_fast":3,"price_features.ema_slow":8,"price_features.ema_higher_tf":60}` | none in audited field list |
| F2 (`f2_indicator`) | yes | `{"indicator.macd_hist_threshold":0,"indicator.rsi_midline":50,"price_features.macd_fast":12,"price_features.macd_slow":26,"price_features.macd_signal":9,"price_features.rsi_period":14}` | none in audited field list |
| F3 (`f3_pattern`) | yes | `{"pattern.bearish_patterns":["bearish_engulfing","evening_star","shooting_star"],"pattern.bullish_patterns":["bullish_engulfing","hammer","morning_star"]}` | none in audited field list |
| F4 (`f4_news_context`) | no | missing (inactive) | news_context.event_intensity_veto_threshold, news_context.sentiment_direction_threshold |
| F5 (`f5_risk_guard`) | yes | `{"risk_guard.daily_drawdown_limit":-0.05,"risk_guard.weekly_drawdown_limit":-0.15,"risk_guard.max_concurrent_trades_per_account":2,"risk_guard.max_leverage":30,"risk_guard.portfolio_at_risk_cap":0.1}` | none in audited field list |
| F6 (`f6_capital_mgmt`) | yes | `{"capital_mgmt.assumed_leverage":30,"capital_mgmt.atr_multiplier":2,"capital_mgmt.lot_notional_units":100000,"capital_mgmt.min_reward_risk":1.5,"capital_mgmt.min_stop_factor":1.2,"capital_mgmt.min_stop_pips":5,"capital_mgmt.pip_value_per_lot":10,"capital_mgmt.risk_per_trade":0.03,"capital_mgmt.stop_distance_source":"swing","capital_mgmt.stop_loss_pips":20,"capital_mgmt.stop_loss_shrink":0.5,"capital_mgmt.targets":[{"at_level_ratio":1,"close_fraction":0.5},{"at_level_ratio":1.5,"close_fraction":0.5}],"capital_mgmt.trail_stops":[{"at_level_ratio":0.5,"to_level_ratio":0}],"price_features.atr_period":14,"price_features.swing_lookback_bars":60}` | none in audited field list |
| F7 (`f7_meta_learner`) | yes | `{"meta_learner.families":["trend","indicator","pattern"],"meta_learner.label_horizon_minutes":15,"meta_learner.regime_gate":false,"meta_learner.theta_high":0.55,"meta_learner.theta_low":0.45}` | none in audited field list |

Shared execution: `{"broker_stop_level_pips":0,"close_on_veto":false,"commission_per_lot":0,"min_hold_bars":0,"spread_pips":1}`.

Per-field provenance: `runs[reference=R18].files["strategy-provenance.json"].value` in the snapshot; each filter matrix also joins provenance by field.

Runtime identity evidence:

```text
2015-09-01 00:00:00 BASELINE_PERCEPTION_SOURCE=ema
2015-09-01 00:00:00 BASELINE_MODEL_SHA256=1a6fd37e96dee3a6f5d082c18afdf863909524636718d129f44eac8d6e4e831e
2026-09-28T00:12:00.0602809Z TRACE:: Debug: 2015-09-01 00:00:00 BASELINE_PERCEPTION_SOURCE=ema
2026-09-28T00:12:00.0602877Z TRACE:: Debug: 2015-09-01 00:00:00 BASELINE_MODEL_SHA256=1a6fd37e96dee3a6f5d082c18afdf863909524636718d129f44eac8d6e4e831e
```

## R19

Run: `baseline/20260928T000117-8bb8148c2302`.
Job: `2026-09-28-one-year-protocol`. Status: **running_no_final_manifest**.

Result: missing final run.json and metrics.json; no provisional performance reported.
Run arguments: missing final manifest; launched arguments preserved in snapshot.processes.

Model SHA-256 recorded by engine: missing.
Job-selected model: `2026-09-28-one-year-protocol/baseline`, SHA-256
`0b41fd39ebf3f37e136e8a7f7a07500f139ee90e675eb7571b866aa7138ae431`. Job selection is not an engine confirmation.

| Artifact | Status | SHA-256 |
| --- | --- | --- |
| `run.json` | missing | missing |
| `metrics.json` | missing | missing |
| `strategy-config.json` | missing | missing |
| `strategy-config.yaml` | missing | missing |
| `strategy-provenance.json` | present | `0eaa1a0740d2a6d79c2b22027b0fabc3d2d77c24ef999fb0214370aaea35b0e3` |

| Filter | In archived chain | Effective values archived for this run | Missing fields |
| --- | --- | --- | --- |
| F1 (`f1_trend`) | missing | missing | price_features.ema_fast, price_features.ema_slow, price_features.ema_higher_tf |
| F2 (`f2_indicator`) | missing | missing | indicator.macd_hist_threshold, indicator.rsi_midline, price_features.macd_fast, price_features.macd_slow, price_features.macd_signal, price_features.rsi_period |
| F3 (`f3_pattern`) | missing | missing | pattern.bearish_patterns, pattern.bullish_patterns |
| F4 (`f4_news_context`) | missing | missing | news_context.event_intensity_veto_threshold, news_context.sentiment_direction_threshold |
| F5 (`f5_risk_guard`) | missing | missing | risk_guard.daily_drawdown_limit, risk_guard.weekly_drawdown_limit, risk_guard.max_concurrent_trades_per_account, risk_guard.max_leverage, risk_guard.portfolio_at_risk_cap |
| F6 (`f6_capital_mgmt`) | missing | missing | capital_mgmt.assumed_leverage, capital_mgmt.atr_multiplier, capital_mgmt.lot_notional_units, capital_mgmt.min_reward_risk, capital_mgmt.min_stop_factor, capital_mgmt.min_stop_pips, capital_mgmt.pip_value_per_lot, capital_mgmt.risk_per_trade, capital_mgmt.stop_distance_source, capital_mgmt.stop_loss_pips, capital_mgmt.stop_loss_shrink, capital_mgmt.targets, capital_mgmt.trail_stops, price_features.atr_period, price_features.swing_lookback_bars |
| F7 (`f7_meta_learner`) | missing | missing | meta_learner.families, meta_learner.label_horizon_minutes, meta_learner.regime_gate, meta_learner.theta_high, meta_learner.theta_low |

Shared execution: missing.

Per-field provenance: `runs[reference=R19].files["strategy-provenance.json"].value` in the snapshot; each filter matrix also joins provenance by field.

Runtime identity evidence:

```text
missing
```

## R20

Run: `hybrid/20260928T000142-8bbdd0d8fd2c`.
Job: `2026-09-28-one-year-protocol`. Status: **running_no_final_manifest**.

Result: missing final run.json and metrics.json; no provisional performance reported.
Run arguments: missing final manifest; launched arguments preserved in snapshot.processes.

Model SHA-256 recorded by engine: `b67ac32e1fc5a6cb9699b7ab96d770f84991c246a5a0b5977f481deb245f63e7`.
Job-selected model: `2026-09-28-one-year-protocol/hybrid`, SHA-256
`b67ac32e1fc5a6cb9699b7ab96d770f84991c246a5a0b5977f481deb245f63e7`. Engine identity matches the archived model.

| Artifact | Status | SHA-256 |
| --- | --- | --- |
| `run.json` | missing | missing |
| `metrics.json` | missing | missing |
| `strategy-config.json` | present | `8870dc6b0c7c33be5cba49ea2a3b99dd69fe7acc52ec4695a9cb3f58d4e4b97a` |
| `strategy-config.yaml` | present | `3351938f978d575d03349a9255955b8d09e17de96c67ccbef18e298d2ca82518` |
| `strategy-provenance.json` | present | `b552235daad5741ddb726031b6b5c0aabc16c5e4d2ac95d336ccda3f288f8f58` |

| Filter | In archived chain | Effective values archived for this run | Missing fields |
| --- | --- | --- | --- |
| F1 (`f1_trend`) | yes | `{"price_features.ema_fast":3,"price_features.ema_slow":8,"price_features.ema_higher_tf":60}` | none in audited field list |
| F2 (`f2_indicator`) | yes | `{"indicator.macd_hist_threshold":0,"indicator.rsi_midline":50,"price_features.macd_fast":12,"price_features.macd_slow":26,"price_features.macd_signal":9,"price_features.rsi_period":14}` | none in audited field list |
| F3 (`f3_pattern`) | yes | `{"pattern.bearish_patterns":["bearish_engulfing","evening_star","shooting_star"],"pattern.bullish_patterns":["bullish_engulfing","hammer","morning_star"]}` | none in audited field list |
| F4 (`f4_news_context`) | yes | `{"news_context.event_intensity_veto_threshold":-0.5,"news_context.sentiment_direction_threshold":0.15}` | none in audited field list |
| F5 (`f5_risk_guard`) | yes | `{"risk_guard.daily_drawdown_limit":-0.05,"risk_guard.weekly_drawdown_limit":-0.15,"risk_guard.max_concurrent_trades_per_account":2,"risk_guard.max_leverage":30,"risk_guard.portfolio_at_risk_cap":0.1}` | none in audited field list |
| F6 (`f6_capital_mgmt`) | yes | `{"capital_mgmt.assumed_leverage":30,"capital_mgmt.atr_multiplier":2,"capital_mgmt.lot_notional_units":100000,"capital_mgmt.min_reward_risk":2,"capital_mgmt.min_stop_factor":1.2,"capital_mgmt.min_stop_pips":5,"capital_mgmt.pip_value_per_lot":10,"capital_mgmt.risk_per_trade":0.03,"capital_mgmt.stop_distance_source":"swing","capital_mgmt.stop_loss_pips":20,"capital_mgmt.stop_loss_shrink":0.2,"capital_mgmt.targets":[{"at_level_ratio":2,"close_fraction":0.5}],"capital_mgmt.trail_stops":[{"at_level_ratio":0.5,"to_level_ratio":-0.66}],"price_features.atr_period":14,"price_features.swing_lookback_bars":60}` | none in audited field list |
| F7 (`f7_meta_learner`) | yes | `{"meta_learner.families":["trend","indicator","pattern","news"],"meta_learner.label_horizon_minutes":15,"meta_learner.regime_gate":false,"meta_learner.theta_high":0.55,"meta_learner.theta_low":0.45}` | none in audited field list |

Shared execution: `{"broker_stop_level_pips":0,"close_on_veto":false,"commission_per_lot":0,"min_hold_bars":0,"spread_pips":1}`.

Per-field provenance: `runs[reference=R20].files["strategy-provenance.json"].value` in the snapshot; each filter matrix also joins provenance by field.

Runtime identity evidence:

```text
2026-09-28T00:26:30.2978820Z TRACE:: Debug: 2016-03-01 00:00:00 HYBRID_PERCEPTION_SOURCE=ema
2026-09-28T00:26:30.2978886Z TRACE:: Debug: 2016-03-01 00:00:00 HYBRID_MODEL_SHA256=b67ac32e1fc5a6cb9699b7ab96d770f84991c246a5a0b5977f481deb245f63e7
```

## F01: historical failed launch

The pilot's `attempt-1-baseline-september.log` reports
`MissingTradingParameter` for `broker.adapter`. Its SHA-256 is
`7793c1f3d50d374417aa12c9f651fdeea624dae7db68aa6551fb461b01736cfd`. No successful run is attributed to
that attempt. Run ID, model identity recorded by engine, manifest, result,
and effective parameters F1/F2/F3/F4/F5/F6/F7 are **missing** for that attempt.
The later successful initial pilot runs are R06 and R11, not this failure.

## P01: planned but not started

The execution-realism script schedules the hybrid November-2015 replay after
R10. At the snapshot, that run has no observed log or directory. Results,
run ID, engine model identity, and effective F1/F2/F3/F4/F5/F6/F7 parameters
are **missing**, not inherited from R10 or another run.
