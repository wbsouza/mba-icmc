# Per-variant resolved parameters for the tuning sweeps (20260928T0240Z)

Output of `algo-backtest explain-strategy <variant> --strategies-dir <job>/strategies` at launch: every key with the file that set it. Models (SHA-256) per job in `model-hashes.txt`.

## t01-base (job `2026-09-28-h4-tuning-sweep`)

Variant YAML:
```yaml
# t01-base: Registered cell: TA-Lib on, activity on (lookback 20, 1.0), theta 0.55/0.45, gate off, Dragon08 plan.
# H4 tuning sweep 2026-09-28 (exploratory development window 2016-03..10; November 2016 read last).
schema_version: 2
extends: dragon08-h4-talib-volume-on
```

Resolved parameters:
```
capital_mgmt.assumed_leverage = 30.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.atr_multiplier = 2.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.lot_notional_units = 100000.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_reward_risk = 2.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_stop_factor = 1.2  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_stop_pips = 5.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.pip_value_per_lot = 10.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.risk_per_trade = 0.03  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_distance_source = "swing"  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_loss_pips = 20.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_loss_shrink = 0.5  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.targets = [{"at_level_ratio": 4.0, "close_fraction": 0.5}, {"at_level_ratio": 6.0, "close_fraction": 0.5}]  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.trail_stops = [{"at_level_ratio": 2.0, "to_level_ratio": 0.1}]  # dragon08-h4-talib-volume-on/config.yaml
execution.broker_stop_level_pips = 0.0  # dragon08-h4-talib-volume-on/config.yaml
execution.close_on_veto = false  # dragon08-h4-talib-volume-on/config.yaml
execution.commission_per_lot = 0.0  # dragon08-h4-talib-volume-on/config.yaml
execution.min_hold_bars = 0  # dragon08-h4-talib-volume-on/config.yaml
execution.spread_pips = 1.0  # dragon08-h4-talib-volume-on/config.yaml
filters = ["f1_trend", "f2_indicator", "f3_pattern", "volume_strength", "f5_risk_guard", "f6_capital_mgmt", "f7_meta_learner"]  # dragon08-h4-talib-volume-on/config.yaml
indicator.macd_hist_threshold = 0.0  # dragon08-h4-talib-volume-on/config.yaml
indicator.rsi_midline = 50.0  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.families = ["trend", "indicator", "pattern"]  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.label_horizon_minutes = 240  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.regime_gate = false  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.theta_high = 0.55  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.theta_low = 0.45  # dragon08-h4-talib-volume-on/config.yaml
pattern.bearish_patterns = ["bearish_engulfing", "evening_star", "shooting_star"]  # dragon08-h4-talib-volume-on/config.yaml
pattern.bullish_patterns = ["bullish_engulfing", "hammer", "morning_star"]  # dragon08-h4-talib-volume-on/config.yaml
pattern.detector = "talib"  # dragon08-h4-talib-volume-on/config.yaml
perception_source = "ema"  # dragon08-h4-talib-volume-on/config.yaml
price_features.atr_period = 14  # dragon08-h4-talib-volume-on/config.yaml
price_features.bar_minutes = 240  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_fast = 3  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_higher_tf = 60  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_slow = 8  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_fast = 12  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_signal = 9  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_slow = 26  # dragon08-h4-talib-volume-on/config.yaml
price_features.rsi_period = 14  # dragon08-h4-talib-volume-on/config.yaml
price_features.swing_lookback_bars = 60  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.daily_drawdown_limit = -0.05  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.max_concurrent_trades_per_account = 2  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.max_leverage = 30  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.portfolio_at_risk_cap = 0.18  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.weekly_drawdown_limit = -0.15  # dragon08-h4-talib-volume-on/config.yaml
schema_version = 2  # t01-base/config.yaml
volume_strength.lookback = 20  # dragon08-h4-talib-volume-on/config.yaml
volume_strength.min_relative_activity = 1.0  # dragon08-h4-talib-volume-on/config.yaml
```

## t02-vol-1.2 (job `2026-09-28-h4-tuning-sweep`)

Variant YAML:
```yaml
# t02-vol-1.2: Activity threshold 1.2 (stricter veto).
# H4 tuning sweep 2026-09-28 (exploratory development window 2016-03..10; November 2016 read last).
schema_version: 2
extends: dragon08-h4-talib-volume-on

volume_strength:
  lookback: 20
  min_relative_activity: 1.2
```

Resolved parameters:
```
capital_mgmt.assumed_leverage = 30.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.atr_multiplier = 2.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.lot_notional_units = 100000.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_reward_risk = 2.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_stop_factor = 1.2  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_stop_pips = 5.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.pip_value_per_lot = 10.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.risk_per_trade = 0.03  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_distance_source = "swing"  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_loss_pips = 20.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_loss_shrink = 0.5  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.targets = [{"at_level_ratio": 4.0, "close_fraction": 0.5}, {"at_level_ratio": 6.0, "close_fraction": 0.5}]  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.trail_stops = [{"at_level_ratio": 2.0, "to_level_ratio": 0.1}]  # dragon08-h4-talib-volume-on/config.yaml
execution.broker_stop_level_pips = 0.0  # dragon08-h4-talib-volume-on/config.yaml
execution.close_on_veto = false  # dragon08-h4-talib-volume-on/config.yaml
execution.commission_per_lot = 0.0  # dragon08-h4-talib-volume-on/config.yaml
execution.min_hold_bars = 0  # dragon08-h4-talib-volume-on/config.yaml
execution.spread_pips = 1.0  # dragon08-h4-talib-volume-on/config.yaml
filters = ["f1_trend", "f2_indicator", "f3_pattern", "volume_strength", "f5_risk_guard", "f6_capital_mgmt", "f7_meta_learner"]  # dragon08-h4-talib-volume-on/config.yaml
indicator.macd_hist_threshold = 0.0  # dragon08-h4-talib-volume-on/config.yaml
indicator.rsi_midline = 50.0  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.families = ["trend", "indicator", "pattern"]  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.label_horizon_minutes = 240  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.regime_gate = false  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.theta_high = 0.55  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.theta_low = 0.45  # dragon08-h4-talib-volume-on/config.yaml
pattern.bearish_patterns = ["bearish_engulfing", "evening_star", "shooting_star"]  # dragon08-h4-talib-volume-on/config.yaml
pattern.bullish_patterns = ["bullish_engulfing", "hammer", "morning_star"]  # dragon08-h4-talib-volume-on/config.yaml
pattern.detector = "talib"  # dragon08-h4-talib-volume-on/config.yaml
perception_source = "ema"  # dragon08-h4-talib-volume-on/config.yaml
price_features.atr_period = 14  # dragon08-h4-talib-volume-on/config.yaml
price_features.bar_minutes = 240  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_fast = 3  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_higher_tf = 60  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_slow = 8  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_fast = 12  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_signal = 9  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_slow = 26  # dragon08-h4-talib-volume-on/config.yaml
price_features.rsi_period = 14  # dragon08-h4-talib-volume-on/config.yaml
price_features.swing_lookback_bars = 60  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.daily_drawdown_limit = -0.05  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.max_concurrent_trades_per_account = 2  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.max_leverage = 30  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.portfolio_at_risk_cap = 0.18  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.weekly_drawdown_limit = -0.15  # dragon08-h4-talib-volume-on/config.yaml
schema_version = 2  # t02-vol-1.2/config.yaml
volume_strength.lookback = 20  # t02-vol-1.2/config.yaml
volume_strength.min_relative_activity = 1.2  # t02-vol-1.2/config.yaml
```

## t03-vol-0.8 (job `2026-09-28-h4-tuning-sweep`)

Variant YAML:
```yaml
# t03-vol-0.8: Activity threshold 0.8 (looser veto).
# H4 tuning sweep 2026-09-28 (exploratory development window 2016-03..10; November 2016 read last).
schema_version: 2
extends: dragon08-h4-talib-volume-on

volume_strength:
  lookback: 20
  min_relative_activity: 0.8
```

Resolved parameters:
```
capital_mgmt.assumed_leverage = 30.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.atr_multiplier = 2.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.lot_notional_units = 100000.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_reward_risk = 2.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_stop_factor = 1.2  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_stop_pips = 5.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.pip_value_per_lot = 10.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.risk_per_trade = 0.03  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_distance_source = "swing"  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_loss_pips = 20.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_loss_shrink = 0.5  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.targets = [{"at_level_ratio": 4.0, "close_fraction": 0.5}, {"at_level_ratio": 6.0, "close_fraction": 0.5}]  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.trail_stops = [{"at_level_ratio": 2.0, "to_level_ratio": 0.1}]  # dragon08-h4-talib-volume-on/config.yaml
execution.broker_stop_level_pips = 0.0  # dragon08-h4-talib-volume-on/config.yaml
execution.close_on_veto = false  # dragon08-h4-talib-volume-on/config.yaml
execution.commission_per_lot = 0.0  # dragon08-h4-talib-volume-on/config.yaml
execution.min_hold_bars = 0  # dragon08-h4-talib-volume-on/config.yaml
execution.spread_pips = 1.0  # dragon08-h4-talib-volume-on/config.yaml
filters = ["f1_trend", "f2_indicator", "f3_pattern", "volume_strength", "f5_risk_guard", "f6_capital_mgmt", "f7_meta_learner"]  # dragon08-h4-talib-volume-on/config.yaml
indicator.macd_hist_threshold = 0.0  # dragon08-h4-talib-volume-on/config.yaml
indicator.rsi_midline = 50.0  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.families = ["trend", "indicator", "pattern"]  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.label_horizon_minutes = 240  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.regime_gate = false  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.theta_high = 0.55  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.theta_low = 0.45  # dragon08-h4-talib-volume-on/config.yaml
pattern.bearish_patterns = ["bearish_engulfing", "evening_star", "shooting_star"]  # dragon08-h4-talib-volume-on/config.yaml
pattern.bullish_patterns = ["bullish_engulfing", "hammer", "morning_star"]  # dragon08-h4-talib-volume-on/config.yaml
pattern.detector = "talib"  # dragon08-h4-talib-volume-on/config.yaml
perception_source = "ema"  # dragon08-h4-talib-volume-on/config.yaml
price_features.atr_period = 14  # dragon08-h4-talib-volume-on/config.yaml
price_features.bar_minutes = 240  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_fast = 3  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_higher_tf = 60  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_slow = 8  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_fast = 12  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_signal = 9  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_slow = 26  # dragon08-h4-talib-volume-on/config.yaml
price_features.rsi_period = 14  # dragon08-h4-talib-volume-on/config.yaml
price_features.swing_lookback_bars = 60  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.daily_drawdown_limit = -0.05  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.max_concurrent_trades_per_account = 2  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.max_leverage = 30  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.portfolio_at_risk_cap = 0.18  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.weekly_drawdown_limit = -0.15  # dragon08-h4-talib-volume-on/config.yaml
schema_version = 2  # t03-vol-0.8/config.yaml
volume_strength.lookback = 20  # t03-vol-0.8/config.yaml
volume_strength.min_relative_activity = 0.8  # t03-vol-0.8/config.yaml
```

## t04-vol-lb10 (job `2026-09-28-h4-tuning-sweep`)

Variant YAML:
```yaml
# t04-vol-lb10: Activity lookback 10 bars, threshold 1.0.
# H4 tuning sweep 2026-09-28 (exploratory development window 2016-03..10; November 2016 read last).
schema_version: 2
extends: dragon08-h4-talib-volume-on

volume_strength:
  lookback: 10
  min_relative_activity: 1.0
```

Resolved parameters:
```
capital_mgmt.assumed_leverage = 30.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.atr_multiplier = 2.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.lot_notional_units = 100000.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_reward_risk = 2.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_stop_factor = 1.2  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_stop_pips = 5.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.pip_value_per_lot = 10.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.risk_per_trade = 0.03  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_distance_source = "swing"  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_loss_pips = 20.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_loss_shrink = 0.5  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.targets = [{"at_level_ratio": 4.0, "close_fraction": 0.5}, {"at_level_ratio": 6.0, "close_fraction": 0.5}]  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.trail_stops = [{"at_level_ratio": 2.0, "to_level_ratio": 0.1}]  # dragon08-h4-talib-volume-on/config.yaml
execution.broker_stop_level_pips = 0.0  # dragon08-h4-talib-volume-on/config.yaml
execution.close_on_veto = false  # dragon08-h4-talib-volume-on/config.yaml
execution.commission_per_lot = 0.0  # dragon08-h4-talib-volume-on/config.yaml
execution.min_hold_bars = 0  # dragon08-h4-talib-volume-on/config.yaml
execution.spread_pips = 1.0  # dragon08-h4-talib-volume-on/config.yaml
filters = ["f1_trend", "f2_indicator", "f3_pattern", "volume_strength", "f5_risk_guard", "f6_capital_mgmt", "f7_meta_learner"]  # dragon08-h4-talib-volume-on/config.yaml
indicator.macd_hist_threshold = 0.0  # dragon08-h4-talib-volume-on/config.yaml
indicator.rsi_midline = 50.0  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.families = ["trend", "indicator", "pattern"]  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.label_horizon_minutes = 240  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.regime_gate = false  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.theta_high = 0.55  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.theta_low = 0.45  # dragon08-h4-talib-volume-on/config.yaml
pattern.bearish_patterns = ["bearish_engulfing", "evening_star", "shooting_star"]  # dragon08-h4-talib-volume-on/config.yaml
pattern.bullish_patterns = ["bullish_engulfing", "hammer", "morning_star"]  # dragon08-h4-talib-volume-on/config.yaml
pattern.detector = "talib"  # dragon08-h4-talib-volume-on/config.yaml
perception_source = "ema"  # dragon08-h4-talib-volume-on/config.yaml
price_features.atr_period = 14  # dragon08-h4-talib-volume-on/config.yaml
price_features.bar_minutes = 240  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_fast = 3  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_higher_tf = 60  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_slow = 8  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_fast = 12  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_signal = 9  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_slow = 26  # dragon08-h4-talib-volume-on/config.yaml
price_features.rsi_period = 14  # dragon08-h4-talib-volume-on/config.yaml
price_features.swing_lookback_bars = 60  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.daily_drawdown_limit = -0.05  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.max_concurrent_trades_per_account = 2  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.max_leverage = 30  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.portfolio_at_risk_cap = 0.18  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.weekly_drawdown_limit = -0.15  # dragon08-h4-talib-volume-on/config.yaml
schema_version = 2  # t04-vol-lb10/config.yaml
volume_strength.lookback = 10  # t04-vol-lb10/config.yaml
volume_strength.min_relative_activity = 1.0  # t04-vol-lb10/config.yaml
```

## t05-theta-60-40 (job `2026-09-28-h4-tuning-sweep`)

Variant YAML:
```yaml
# t05-theta-60-40: F7 thresholds 0.60/0.40 (more selective).
# H4 tuning sweep 2026-09-28 (exploratory development window 2016-03..10; November 2016 read last).
schema_version: 2
extends: dragon08-h4-talib-volume-on

meta_learner:
  theta_high: 0.60
  theta_low: 0.40
```

Resolved parameters:
```
capital_mgmt.assumed_leverage = 30.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.atr_multiplier = 2.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.lot_notional_units = 100000.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_reward_risk = 2.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_stop_factor = 1.2  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_stop_pips = 5.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.pip_value_per_lot = 10.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.risk_per_trade = 0.03  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_distance_source = "swing"  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_loss_pips = 20.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_loss_shrink = 0.5  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.targets = [{"at_level_ratio": 4.0, "close_fraction": 0.5}, {"at_level_ratio": 6.0, "close_fraction": 0.5}]  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.trail_stops = [{"at_level_ratio": 2.0, "to_level_ratio": 0.1}]  # dragon08-h4-talib-volume-on/config.yaml
execution.broker_stop_level_pips = 0.0  # dragon08-h4-talib-volume-on/config.yaml
execution.close_on_veto = false  # dragon08-h4-talib-volume-on/config.yaml
execution.commission_per_lot = 0.0  # dragon08-h4-talib-volume-on/config.yaml
execution.min_hold_bars = 0  # dragon08-h4-talib-volume-on/config.yaml
execution.spread_pips = 1.0  # dragon08-h4-talib-volume-on/config.yaml
filters = ["f1_trend", "f2_indicator", "f3_pattern", "volume_strength", "f5_risk_guard", "f6_capital_mgmt", "f7_meta_learner"]  # dragon08-h4-talib-volume-on/config.yaml
indicator.macd_hist_threshold = 0.0  # dragon08-h4-talib-volume-on/config.yaml
indicator.rsi_midline = 50.0  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.families = ["trend", "indicator", "pattern"]  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.label_horizon_minutes = 240  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.regime_gate = false  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.theta_high = 0.6  # t05-theta-60-40/config.yaml
meta_learner.theta_low = 0.4  # t05-theta-60-40/config.yaml
pattern.bearish_patterns = ["bearish_engulfing", "evening_star", "shooting_star"]  # dragon08-h4-talib-volume-on/config.yaml
pattern.bullish_patterns = ["bullish_engulfing", "hammer", "morning_star"]  # dragon08-h4-talib-volume-on/config.yaml
pattern.detector = "talib"  # dragon08-h4-talib-volume-on/config.yaml
perception_source = "ema"  # dragon08-h4-talib-volume-on/config.yaml
price_features.atr_period = 14  # dragon08-h4-talib-volume-on/config.yaml
price_features.bar_minutes = 240  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_fast = 3  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_higher_tf = 60  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_slow = 8  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_fast = 12  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_signal = 9  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_slow = 26  # dragon08-h4-talib-volume-on/config.yaml
price_features.rsi_period = 14  # dragon08-h4-talib-volume-on/config.yaml
price_features.swing_lookback_bars = 60  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.daily_drawdown_limit = -0.05  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.max_concurrent_trades_per_account = 2  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.max_leverage = 30  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.portfolio_at_risk_cap = 0.18  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.weekly_drawdown_limit = -0.15  # dragon08-h4-talib-volume-on/config.yaml
schema_version = 2  # t05-theta-60-40/config.yaml
volume_strength.lookback = 20  # dragon08-h4-talib-volume-on/config.yaml
volume_strength.min_relative_activity = 1.0  # dragon08-h4-talib-volume-on/config.yaml
```

## t06-theta-52-48 (job `2026-09-28-h4-tuning-sweep`)

Variant YAML:
```yaml
# t06-theta-52-48: F7 thresholds 0.52/0.48 (less selective).
# H4 tuning sweep 2026-09-28 (exploratory development window 2016-03..10; November 2016 read last).
schema_version: 2
extends: dragon08-h4-talib-volume-on

meta_learner:
  theta_high: 0.52
  theta_low: 0.48
```

Resolved parameters:
```
capital_mgmt.assumed_leverage = 30.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.atr_multiplier = 2.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.lot_notional_units = 100000.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_reward_risk = 2.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_stop_factor = 1.2  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_stop_pips = 5.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.pip_value_per_lot = 10.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.risk_per_trade = 0.03  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_distance_source = "swing"  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_loss_pips = 20.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_loss_shrink = 0.5  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.targets = [{"at_level_ratio": 4.0, "close_fraction": 0.5}, {"at_level_ratio": 6.0, "close_fraction": 0.5}]  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.trail_stops = [{"at_level_ratio": 2.0, "to_level_ratio": 0.1}]  # dragon08-h4-talib-volume-on/config.yaml
execution.broker_stop_level_pips = 0.0  # dragon08-h4-talib-volume-on/config.yaml
execution.close_on_veto = false  # dragon08-h4-talib-volume-on/config.yaml
execution.commission_per_lot = 0.0  # dragon08-h4-talib-volume-on/config.yaml
execution.min_hold_bars = 0  # dragon08-h4-talib-volume-on/config.yaml
execution.spread_pips = 1.0  # dragon08-h4-talib-volume-on/config.yaml
filters = ["f1_trend", "f2_indicator", "f3_pattern", "volume_strength", "f5_risk_guard", "f6_capital_mgmt", "f7_meta_learner"]  # dragon08-h4-talib-volume-on/config.yaml
indicator.macd_hist_threshold = 0.0  # dragon08-h4-talib-volume-on/config.yaml
indicator.rsi_midline = 50.0  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.families = ["trend", "indicator", "pattern"]  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.label_horizon_minutes = 240  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.regime_gate = false  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.theta_high = 0.52  # t06-theta-52-48/config.yaml
meta_learner.theta_low = 0.48  # t06-theta-52-48/config.yaml
pattern.bearish_patterns = ["bearish_engulfing", "evening_star", "shooting_star"]  # dragon08-h4-talib-volume-on/config.yaml
pattern.bullish_patterns = ["bullish_engulfing", "hammer", "morning_star"]  # dragon08-h4-talib-volume-on/config.yaml
pattern.detector = "talib"  # dragon08-h4-talib-volume-on/config.yaml
perception_source = "ema"  # dragon08-h4-talib-volume-on/config.yaml
price_features.atr_period = 14  # dragon08-h4-talib-volume-on/config.yaml
price_features.bar_minutes = 240  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_fast = 3  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_higher_tf = 60  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_slow = 8  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_fast = 12  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_signal = 9  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_slow = 26  # dragon08-h4-talib-volume-on/config.yaml
price_features.rsi_period = 14  # dragon08-h4-talib-volume-on/config.yaml
price_features.swing_lookback_bars = 60  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.daily_drawdown_limit = -0.05  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.max_concurrent_trades_per_account = 2  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.max_leverage = 30  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.portfolio_at_risk_cap = 0.18  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.weekly_drawdown_limit = -0.15  # dragon08-h4-talib-volume-on/config.yaml
schema_version = 2  # t06-theta-52-48/config.yaml
volume_strength.lookback = 20  # dragon08-h4-talib-volume-on/config.yaml
volume_strength.min_relative_activity = 1.0  # dragon08-h4-talib-volume-on/config.yaml
```

## t07-gate-on (job `2026-09-28-h4-tuning-sweep`)

Variant YAML:
```yaml
# t07-gate-on: Dissertation regime gate on.
# H4 tuning sweep 2026-09-28 (exploratory development window 2016-03..10; November 2016 read last).
schema_version: 2
extends: dragon08-h4-talib-volume-on

meta_learner:
  regime_gate: true
```

Resolved parameters:
```
capital_mgmt.assumed_leverage = 30.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.atr_multiplier = 2.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.lot_notional_units = 100000.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_reward_risk = 2.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_stop_factor = 1.2  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_stop_pips = 5.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.pip_value_per_lot = 10.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.risk_per_trade = 0.03  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_distance_source = "swing"  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_loss_pips = 20.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_loss_shrink = 0.5  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.targets = [{"at_level_ratio": 4.0, "close_fraction": 0.5}, {"at_level_ratio": 6.0, "close_fraction": 0.5}]  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.trail_stops = [{"at_level_ratio": 2.0, "to_level_ratio": 0.1}]  # dragon08-h4-talib-volume-on/config.yaml
execution.broker_stop_level_pips = 0.0  # dragon08-h4-talib-volume-on/config.yaml
execution.close_on_veto = false  # dragon08-h4-talib-volume-on/config.yaml
execution.commission_per_lot = 0.0  # dragon08-h4-talib-volume-on/config.yaml
execution.min_hold_bars = 0  # dragon08-h4-talib-volume-on/config.yaml
execution.spread_pips = 1.0  # dragon08-h4-talib-volume-on/config.yaml
filters = ["f1_trend", "f2_indicator", "f3_pattern", "volume_strength", "f5_risk_guard", "f6_capital_mgmt", "f7_meta_learner"]  # dragon08-h4-talib-volume-on/config.yaml
indicator.macd_hist_threshold = 0.0  # dragon08-h4-talib-volume-on/config.yaml
indicator.rsi_midline = 50.0  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.families = ["trend", "indicator", "pattern"]  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.label_horizon_minutes = 240  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.regime_gate = true  # t07-gate-on/config.yaml
meta_learner.theta_high = 0.55  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.theta_low = 0.45  # dragon08-h4-talib-volume-on/config.yaml
pattern.bearish_patterns = ["bearish_engulfing", "evening_star", "shooting_star"]  # dragon08-h4-talib-volume-on/config.yaml
pattern.bullish_patterns = ["bullish_engulfing", "hammer", "morning_star"]  # dragon08-h4-talib-volume-on/config.yaml
pattern.detector = "talib"  # dragon08-h4-talib-volume-on/config.yaml
perception_source = "ema"  # dragon08-h4-talib-volume-on/config.yaml
price_features.atr_period = 14  # dragon08-h4-talib-volume-on/config.yaml
price_features.bar_minutes = 240  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_fast = 3  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_higher_tf = 60  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_slow = 8  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_fast = 12  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_signal = 9  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_slow = 26  # dragon08-h4-talib-volume-on/config.yaml
price_features.rsi_period = 14  # dragon08-h4-talib-volume-on/config.yaml
price_features.swing_lookback_bars = 60  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.daily_drawdown_limit = -0.05  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.max_concurrent_trades_per_account = 2  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.max_leverage = 30  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.portfolio_at_risk_cap = 0.18  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.weekly_drawdown_limit = -0.15  # dragon08-h4-talib-volume-on/config.yaml
schema_version = 2  # t07-gate-on/config.yaml
volume_strength.lookback = 20  # dragon08-h4-talib-volume-on/config.yaml
volume_strength.min_relative_activity = 1.0  # dragon08-h4-talib-volume-on/config.yaml
```

## t08-plan-dragon05 (job `2026-09-28-h4-tuning-sweep`)

Variant YAML:
```yaml
# t08-plan-dragon05: spockfx Dragon05 plan: 1R closes 50 %, 2R closes the rest, trail 1R -> breakeven, stop cut 50 %.
# H4 tuning sweep 2026-09-28 (exploratory development window 2016-03..10; November 2016 read last).
schema_version: 2
extends: dragon08-h4-talib-volume-on

capital_mgmt:
  stop_loss_shrink: 0.50
  targets:
    - {at_level_ratio: 1.0, close_fraction: 0.5}
    - {at_level_ratio: 2.0, close_fraction: 0.5}
  trail_stops:
    - {at_level_ratio: 1.0, to_level_ratio: 0.0}
  min_reward_risk: 2.0
```

Resolved parameters:
```
capital_mgmt.assumed_leverage = 30.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.atr_multiplier = 2.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.lot_notional_units = 100000.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_reward_risk = 2.0  # t08-plan-dragon05/config.yaml
capital_mgmt.min_stop_factor = 1.2  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_stop_pips = 5.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.pip_value_per_lot = 10.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.risk_per_trade = 0.03  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_distance_source = "swing"  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_loss_pips = 20.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_loss_shrink = 0.5  # t08-plan-dragon05/config.yaml
capital_mgmt.targets = [{"at_level_ratio": 1.0, "close_fraction": 0.5}, {"at_level_ratio": 2.0, "close_fraction": 0.5}]  # t08-plan-dragon05/config.yaml
capital_mgmt.trail_stops = [{"at_level_ratio": 1.0, "to_level_ratio": 0.0}]  # t08-plan-dragon05/config.yaml
execution.broker_stop_level_pips = 0.0  # dragon08-h4-talib-volume-on/config.yaml
execution.close_on_veto = false  # dragon08-h4-talib-volume-on/config.yaml
execution.commission_per_lot = 0.0  # dragon08-h4-talib-volume-on/config.yaml
execution.min_hold_bars = 0  # dragon08-h4-talib-volume-on/config.yaml
execution.spread_pips = 1.0  # dragon08-h4-talib-volume-on/config.yaml
filters = ["f1_trend", "f2_indicator", "f3_pattern", "volume_strength", "f5_risk_guard", "f6_capital_mgmt", "f7_meta_learner"]  # dragon08-h4-talib-volume-on/config.yaml
indicator.macd_hist_threshold = 0.0  # dragon08-h4-talib-volume-on/config.yaml
indicator.rsi_midline = 50.0  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.families = ["trend", "indicator", "pattern"]  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.label_horizon_minutes = 240  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.regime_gate = false  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.theta_high = 0.55  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.theta_low = 0.45  # dragon08-h4-talib-volume-on/config.yaml
pattern.bearish_patterns = ["bearish_engulfing", "evening_star", "shooting_star"]  # dragon08-h4-talib-volume-on/config.yaml
pattern.bullish_patterns = ["bullish_engulfing", "hammer", "morning_star"]  # dragon08-h4-talib-volume-on/config.yaml
pattern.detector = "talib"  # dragon08-h4-talib-volume-on/config.yaml
perception_source = "ema"  # dragon08-h4-talib-volume-on/config.yaml
price_features.atr_period = 14  # dragon08-h4-talib-volume-on/config.yaml
price_features.bar_minutes = 240  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_fast = 3  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_higher_tf = 60  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_slow = 8  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_fast = 12  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_signal = 9  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_slow = 26  # dragon08-h4-talib-volume-on/config.yaml
price_features.rsi_period = 14  # dragon08-h4-talib-volume-on/config.yaml
price_features.swing_lookback_bars = 60  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.daily_drawdown_limit = -0.05  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.max_concurrent_trades_per_account = 2  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.max_leverage = 30  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.portfolio_at_risk_cap = 0.18  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.weekly_drawdown_limit = -0.15  # dragon08-h4-talib-volume-on/config.yaml
schema_version = 2  # t08-plan-dragon05/config.yaml
volume_strength.lookback = 20  # dragon08-h4-talib-volume-on/config.yaml
volume_strength.min_relative_activity = 1.0  # dragon08-h4-talib-volume-on/config.yaml
```

## t09-atr-stop (job `2026-09-28-h4-tuning-sweep`)

Variant YAML:
```yaml
# t09-atr-stop: ATR stop: 2 x ATR14 on H4 bars, floor 10 pips, no shrink.
# H4 tuning sweep 2026-09-28 (exploratory development window 2016-03..10; November 2016 read last).
schema_version: 2
extends: dragon08-h4-talib-volume-on

capital_mgmt:
  stop_distance_source: atr
  atr_multiplier: 2.0
  min_stop_pips: 10.0
  stop_loss_shrink: 0.0
```

Resolved parameters:
```
capital_mgmt.assumed_leverage = 30.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.atr_multiplier = 2.0  # t09-atr-stop/config.yaml
capital_mgmt.lot_notional_units = 100000.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_reward_risk = 2.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_stop_factor = 1.2  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_stop_pips = 10.0  # t09-atr-stop/config.yaml
capital_mgmt.pip_value_per_lot = 10.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.risk_per_trade = 0.03  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_distance_source = "atr"  # t09-atr-stop/config.yaml
capital_mgmt.stop_loss_pips = 20.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_loss_shrink = 0.0  # t09-atr-stop/config.yaml
capital_mgmt.targets = [{"at_level_ratio": 4.0, "close_fraction": 0.5}, {"at_level_ratio": 6.0, "close_fraction": 0.5}]  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.trail_stops = [{"at_level_ratio": 2.0, "to_level_ratio": 0.1}]  # dragon08-h4-talib-volume-on/config.yaml
execution.broker_stop_level_pips = 0.0  # dragon08-h4-talib-volume-on/config.yaml
execution.close_on_veto = false  # dragon08-h4-talib-volume-on/config.yaml
execution.commission_per_lot = 0.0  # dragon08-h4-talib-volume-on/config.yaml
execution.min_hold_bars = 0  # dragon08-h4-talib-volume-on/config.yaml
execution.spread_pips = 1.0  # dragon08-h4-talib-volume-on/config.yaml
filters = ["f1_trend", "f2_indicator", "f3_pattern", "volume_strength", "f5_risk_guard", "f6_capital_mgmt", "f7_meta_learner"]  # dragon08-h4-talib-volume-on/config.yaml
indicator.macd_hist_threshold = 0.0  # dragon08-h4-talib-volume-on/config.yaml
indicator.rsi_midline = 50.0  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.families = ["trend", "indicator", "pattern"]  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.label_horizon_minutes = 240  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.regime_gate = false  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.theta_high = 0.55  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.theta_low = 0.45  # dragon08-h4-talib-volume-on/config.yaml
pattern.bearish_patterns = ["bearish_engulfing", "evening_star", "shooting_star"]  # dragon08-h4-talib-volume-on/config.yaml
pattern.bullish_patterns = ["bullish_engulfing", "hammer", "morning_star"]  # dragon08-h4-talib-volume-on/config.yaml
pattern.detector = "talib"  # dragon08-h4-talib-volume-on/config.yaml
perception_source = "ema"  # dragon08-h4-talib-volume-on/config.yaml
price_features.atr_period = 14  # dragon08-h4-talib-volume-on/config.yaml
price_features.bar_minutes = 240  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_fast = 3  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_higher_tf = 60  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_slow = 8  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_fast = 12  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_signal = 9  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_slow = 26  # dragon08-h4-talib-volume-on/config.yaml
price_features.rsi_period = 14  # dragon08-h4-talib-volume-on/config.yaml
price_features.swing_lookback_bars = 60  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.daily_drawdown_limit = -0.05  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.max_concurrent_trades_per_account = 2  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.max_leverage = 30  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.portfolio_at_risk_cap = 0.18  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.weekly_drawdown_limit = -0.15  # dragon08-h4-talib-volume-on/config.yaml
schema_version = 2  # t09-atr-stop/config.yaml
volume_strength.lookback = 20  # dragon08-h4-talib-volume-on/config.yaml
volume_strength.min_relative_activity = 1.0  # dragon08-h4-talib-volume-on/config.yaml
```

## t10-order-vol-first (job `2026-09-28-h4-tuning-sweep`)

Variant YAML:
```yaml
# t10-order-vol-first: Same filters, activity veto placed first in the chain (before F1).
# H4 tuning sweep 2026-09-28 (exploratory development window 2016-03..10; November 2016 read last).
schema_version: 2
extends: dragon08-h4-talib-volume-on

filters:
  - volume_strength
  - f1_trend
  - f2_indicator
  - f3_pattern
  - f5_risk_guard
  - f6_capital_mgmt
  - f7_meta_learner
```

Resolved parameters:
```
capital_mgmt.assumed_leverage = 30.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.atr_multiplier = 2.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.lot_notional_units = 100000.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_reward_risk = 2.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_stop_factor = 1.2  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_stop_pips = 5.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.pip_value_per_lot = 10.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.risk_per_trade = 0.03  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_distance_source = "swing"  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_loss_pips = 20.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_loss_shrink = 0.5  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.targets = [{"at_level_ratio": 4.0, "close_fraction": 0.5}, {"at_level_ratio": 6.0, "close_fraction": 0.5}]  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.trail_stops = [{"at_level_ratio": 2.0, "to_level_ratio": 0.1}]  # dragon08-h4-talib-volume-on/config.yaml
execution.broker_stop_level_pips = 0.0  # dragon08-h4-talib-volume-on/config.yaml
execution.close_on_veto = false  # dragon08-h4-talib-volume-on/config.yaml
execution.commission_per_lot = 0.0  # dragon08-h4-talib-volume-on/config.yaml
execution.min_hold_bars = 0  # dragon08-h4-talib-volume-on/config.yaml
execution.spread_pips = 1.0  # dragon08-h4-talib-volume-on/config.yaml
filters = ["volume_strength", "f1_trend", "f2_indicator", "f3_pattern", "f5_risk_guard", "f6_capital_mgmt", "f7_meta_learner"]  # t10-order-vol-first/config.yaml
indicator.macd_hist_threshold = 0.0  # dragon08-h4-talib-volume-on/config.yaml
indicator.rsi_midline = 50.0  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.families = ["trend", "indicator", "pattern"]  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.label_horizon_minutes = 240  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.regime_gate = false  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.theta_high = 0.55  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.theta_low = 0.45  # dragon08-h4-talib-volume-on/config.yaml
pattern.bearish_patterns = ["bearish_engulfing", "evening_star", "shooting_star"]  # dragon08-h4-talib-volume-on/config.yaml
pattern.bullish_patterns = ["bullish_engulfing", "hammer", "morning_star"]  # dragon08-h4-talib-volume-on/config.yaml
pattern.detector = "talib"  # dragon08-h4-talib-volume-on/config.yaml
perception_source = "ema"  # dragon08-h4-talib-volume-on/config.yaml
price_features.atr_period = 14  # dragon08-h4-talib-volume-on/config.yaml
price_features.bar_minutes = 240  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_fast = 3  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_higher_tf = 60  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_slow = 8  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_fast = 12  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_signal = 9  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_slow = 26  # dragon08-h4-talib-volume-on/config.yaml
price_features.rsi_period = 14  # dragon08-h4-talib-volume-on/config.yaml
price_features.swing_lookback_bars = 60  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.daily_drawdown_limit = -0.05  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.max_concurrent_trades_per_account = 2  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.max_leverage = 30  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.portfolio_at_risk_cap = 0.18  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.weekly_drawdown_limit = -0.15  # dragon08-h4-talib-volume-on/config.yaml
schema_version = 2  # t10-order-vol-first/config.yaml
volume_strength.lookback = 20  # dragon08-h4-talib-volume-on/config.yaml
volume_strength.min_relative_activity = 1.0  # dragon08-h4-talib-volume-on/config.yaml
```

## t11-nocandle-vol-on (job `2026-09-28-h4-tuning-sweep`)

Variant YAML:
```yaml
# t11-nocandle-vol-on: Control: detector disabled, activity on.
# H4 tuning sweep 2026-09-28 (exploratory development window 2016-03..10; November 2016 read last).
schema_version: 2
extends: dragon08-h4-disabled-volume-on
```

Resolved parameters:
```
capital_mgmt.assumed_leverage = 30.0  # dragon08-h4-disabled-volume-on/config.yaml
capital_mgmt.atr_multiplier = 2.0  # dragon08-h4-disabled-volume-on/config.yaml
capital_mgmt.lot_notional_units = 100000.0  # dragon08-h4-disabled-volume-on/config.yaml
capital_mgmt.min_reward_risk = 2.0  # dragon08-h4-disabled-volume-on/config.yaml
capital_mgmt.min_stop_factor = 1.2  # dragon08-h4-disabled-volume-on/config.yaml
capital_mgmt.min_stop_pips = 5.0  # dragon08-h4-disabled-volume-on/config.yaml
capital_mgmt.pip_value_per_lot = 10.0  # dragon08-h4-disabled-volume-on/config.yaml
capital_mgmt.risk_per_trade = 0.03  # dragon08-h4-disabled-volume-on/config.yaml
capital_mgmt.stop_distance_source = "swing"  # dragon08-h4-disabled-volume-on/config.yaml
capital_mgmt.stop_loss_pips = 20.0  # dragon08-h4-disabled-volume-on/config.yaml
capital_mgmt.stop_loss_shrink = 0.5  # dragon08-h4-disabled-volume-on/config.yaml
capital_mgmt.targets = [{"at_level_ratio": 4.0, "close_fraction": 0.5}, {"at_level_ratio": 6.0, "close_fraction": 0.5}]  # dragon08-h4-disabled-volume-on/config.yaml
capital_mgmt.trail_stops = [{"at_level_ratio": 2.0, "to_level_ratio": 0.1}]  # dragon08-h4-disabled-volume-on/config.yaml
execution.broker_stop_level_pips = 0.0  # dragon08-h4-disabled-volume-on/config.yaml
execution.close_on_veto = false  # dragon08-h4-disabled-volume-on/config.yaml
execution.commission_per_lot = 0.0  # dragon08-h4-disabled-volume-on/config.yaml
execution.min_hold_bars = 0  # dragon08-h4-disabled-volume-on/config.yaml
execution.spread_pips = 1.0  # dragon08-h4-disabled-volume-on/config.yaml
filters = ["f1_trend", "f2_indicator", "f3_pattern", "volume_strength", "f5_risk_guard", "f6_capital_mgmt", "f7_meta_learner"]  # dragon08-h4-disabled-volume-on/config.yaml
indicator.macd_hist_threshold = 0.0  # dragon08-h4-disabled-volume-on/config.yaml
indicator.rsi_midline = 50.0  # dragon08-h4-disabled-volume-on/config.yaml
meta_learner.families = ["trend", "indicator", "pattern"]  # dragon08-h4-disabled-volume-on/config.yaml
meta_learner.label_horizon_minutes = 240  # dragon08-h4-disabled-volume-on/config.yaml
meta_learner.regime_gate = false  # dragon08-h4-disabled-volume-on/config.yaml
meta_learner.theta_high = 0.55  # dragon08-h4-disabled-volume-on/config.yaml
meta_learner.theta_low = 0.45  # dragon08-h4-disabled-volume-on/config.yaml
pattern.bearish_patterns = ["bearish_engulfing", "evening_star", "shooting_star"]  # dragon08-h4-disabled-volume-on/config.yaml
pattern.bullish_patterns = ["bullish_engulfing", "hammer", "morning_star"]  # dragon08-h4-disabled-volume-on/config.yaml
pattern.detector = "disabled"  # dragon08-h4-disabled-volume-on/config.yaml
perception_source = "ema"  # dragon08-h4-disabled-volume-on/config.yaml
price_features.atr_period = 14  # dragon08-h4-disabled-volume-on/config.yaml
price_features.bar_minutes = 240  # dragon08-h4-disabled-volume-on/config.yaml
price_features.ema_fast = 3  # dragon08-h4-disabled-volume-on/config.yaml
price_features.ema_higher_tf = 60  # dragon08-h4-disabled-volume-on/config.yaml
price_features.ema_slow = 8  # dragon08-h4-disabled-volume-on/config.yaml
price_features.macd_fast = 12  # dragon08-h4-disabled-volume-on/config.yaml
price_features.macd_signal = 9  # dragon08-h4-disabled-volume-on/config.yaml
price_features.macd_slow = 26  # dragon08-h4-disabled-volume-on/config.yaml
price_features.rsi_period = 14  # dragon08-h4-disabled-volume-on/config.yaml
price_features.swing_lookback_bars = 60  # dragon08-h4-disabled-volume-on/config.yaml
risk_guard.daily_drawdown_limit = -0.05  # dragon08-h4-disabled-volume-on/config.yaml
risk_guard.max_concurrent_trades_per_account = 2  # dragon08-h4-disabled-volume-on/config.yaml
risk_guard.max_leverage = 30  # dragon08-h4-disabled-volume-on/config.yaml
risk_guard.portfolio_at_risk_cap = 0.18  # dragon08-h4-disabled-volume-on/config.yaml
risk_guard.weekly_drawdown_limit = -0.15  # dragon08-h4-disabled-volume-on/config.yaml
schema_version = 2  # t11-nocandle-vol-on/config.yaml
volume_strength.lookback = 20  # dragon08-h4-disabled-volume-on/config.yaml
volume_strength.min_relative_activity = 1.0  # dragon08-h4-disabled-volume-on/config.yaml
```

## t12-hybrid-base (job `2026-09-28-h4-tuning-sweep`)

Variant YAML:
```yaml
# t12-hybrid-base: Hybrid counterpart of t01 (F4 news context + news family).
# H4 tuning sweep 2026-09-28 (exploratory development window 2016-03..10; November 2016 read last).
schema_version: 2
extends: dragon08-h4-hybrid-talib-volume-on
```

Resolved parameters:
```
capital_mgmt.assumed_leverage = 30.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.atr_multiplier = 2.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.lot_notional_units = 100000.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.min_reward_risk = 2.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.min_stop_factor = 1.2  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.min_stop_pips = 5.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.pip_value_per_lot = 10.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.risk_per_trade = 0.03  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.stop_distance_source = "swing"  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.stop_loss_pips = 20.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.stop_loss_shrink = 0.5  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.targets = [{"at_level_ratio": 4.0, "close_fraction": 0.5}, {"at_level_ratio": 6.0, "close_fraction": 0.5}]  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.trail_stops = [{"at_level_ratio": 2.0, "to_level_ratio": 0.1}]  # dragon08-h4-hybrid-talib-volume-on/config.yaml
execution.broker_stop_level_pips = 0.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
execution.close_on_veto = false  # dragon08-h4-hybrid-talib-volume-on/config.yaml
execution.commission_per_lot = 0.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
execution.min_hold_bars = 0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
execution.spread_pips = 1.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
filters = ["f1_trend", "f2_indicator", "f3_pattern", "f4_news_context", "volume_strength", "f5_risk_guard", "f6_capital_mgmt", "f7_meta_learner"]  # dragon08-h4-hybrid-talib-volume-on/config.yaml
indicator.macd_hist_threshold = 0.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
indicator.rsi_midline = 50.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
meta_learner.families = ["trend", "indicator", "pattern", "news"]  # dragon08-h4-hybrid-talib-volume-on/config.yaml
meta_learner.label_horizon_minutes = 240  # dragon08-h4-hybrid-talib-volume-on/config.yaml
meta_learner.regime_gate = false  # dragon08-h4-hybrid-talib-volume-on/config.yaml
meta_learner.theta_high = 0.55  # dragon08-h4-hybrid-talib-volume-on/config.yaml
meta_learner.theta_low = 0.45  # dragon08-h4-hybrid-talib-volume-on/config.yaml
news_context.event_intensity_veto_threshold = -0.5  # dragon08-h4-hybrid-talib-volume-on/config.yaml
news_context.sentiment_direction_threshold = 0.15  # dragon08-h4-hybrid-talib-volume-on/config.yaml
pattern.bearish_patterns = ["bearish_engulfing", "evening_star", "shooting_star"]  # dragon08-h4-hybrid-talib-volume-on/config.yaml
pattern.bullish_patterns = ["bullish_engulfing", "hammer", "morning_star"]  # dragon08-h4-hybrid-talib-volume-on/config.yaml
pattern.detector = "talib"  # dragon08-h4-hybrid-talib-volume-on/config.yaml
perception_source = "ema"  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.atr_period = 14  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.bar_minutes = 240  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.ema_fast = 3  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.ema_higher_tf = 60  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.ema_slow = 8  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.macd_fast = 12  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.macd_signal = 9  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.macd_slow = 26  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.rsi_period = 14  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.swing_lookback_bars = 60  # dragon08-h4-hybrid-talib-volume-on/config.yaml
risk_guard.daily_drawdown_limit = -0.05  # dragon08-h4-hybrid-talib-volume-on/config.yaml
risk_guard.max_concurrent_trades_per_account = 2  # dragon08-h4-hybrid-talib-volume-on/config.yaml
risk_guard.max_leverage = 30  # dragon08-h4-hybrid-talib-volume-on/config.yaml
risk_guard.portfolio_at_risk_cap = 0.18  # dragon08-h4-hybrid-talib-volume-on/config.yaml
risk_guard.weekly_drawdown_limit = -0.15  # dragon08-h4-hybrid-talib-volume-on/config.yaml
schema_version = 2  # t12-hybrid-base/config.yaml
volume_strength.lookback = 20  # dragon08-h4-hybrid-talib-volume-on/config.yaml
volume_strength.min_relative_activity = 1.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
```

## t13-hybrid-theta-60-40 (job `2026-09-28-h4-tuning-sweep`)

Variant YAML:
```yaml
# t13-hybrid-theta-60-40: Hybrid with thresholds 0.60/0.40.
# H4 tuning sweep 2026-09-28 (exploratory development window 2016-03..10; November 2016 read last).
schema_version: 2
extends: dragon08-h4-hybrid-talib-volume-on

meta_learner:
  theta_high: 0.60
  theta_low: 0.40
```

Resolved parameters:
```
capital_mgmt.assumed_leverage = 30.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.atr_multiplier = 2.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.lot_notional_units = 100000.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.min_reward_risk = 2.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.min_stop_factor = 1.2  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.min_stop_pips = 5.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.pip_value_per_lot = 10.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.risk_per_trade = 0.03  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.stop_distance_source = "swing"  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.stop_loss_pips = 20.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.stop_loss_shrink = 0.5  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.targets = [{"at_level_ratio": 4.0, "close_fraction": 0.5}, {"at_level_ratio": 6.0, "close_fraction": 0.5}]  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.trail_stops = [{"at_level_ratio": 2.0, "to_level_ratio": 0.1}]  # dragon08-h4-hybrid-talib-volume-on/config.yaml
execution.broker_stop_level_pips = 0.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
execution.close_on_veto = false  # dragon08-h4-hybrid-talib-volume-on/config.yaml
execution.commission_per_lot = 0.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
execution.min_hold_bars = 0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
execution.spread_pips = 1.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
filters = ["f1_trend", "f2_indicator", "f3_pattern", "f4_news_context", "volume_strength", "f5_risk_guard", "f6_capital_mgmt", "f7_meta_learner"]  # dragon08-h4-hybrid-talib-volume-on/config.yaml
indicator.macd_hist_threshold = 0.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
indicator.rsi_midline = 50.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
meta_learner.families = ["trend", "indicator", "pattern", "news"]  # dragon08-h4-hybrid-talib-volume-on/config.yaml
meta_learner.label_horizon_minutes = 240  # dragon08-h4-hybrid-talib-volume-on/config.yaml
meta_learner.regime_gate = false  # dragon08-h4-hybrid-talib-volume-on/config.yaml
meta_learner.theta_high = 0.6  # t13-hybrid-theta-60-40/config.yaml
meta_learner.theta_low = 0.4  # t13-hybrid-theta-60-40/config.yaml
news_context.event_intensity_veto_threshold = -0.5  # dragon08-h4-hybrid-talib-volume-on/config.yaml
news_context.sentiment_direction_threshold = 0.15  # dragon08-h4-hybrid-talib-volume-on/config.yaml
pattern.bearish_patterns = ["bearish_engulfing", "evening_star", "shooting_star"]  # dragon08-h4-hybrid-talib-volume-on/config.yaml
pattern.bullish_patterns = ["bullish_engulfing", "hammer", "morning_star"]  # dragon08-h4-hybrid-talib-volume-on/config.yaml
pattern.detector = "talib"  # dragon08-h4-hybrid-talib-volume-on/config.yaml
perception_source = "ema"  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.atr_period = 14  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.bar_minutes = 240  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.ema_fast = 3  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.ema_higher_tf = 60  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.ema_slow = 8  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.macd_fast = 12  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.macd_signal = 9  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.macd_slow = 26  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.rsi_period = 14  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.swing_lookback_bars = 60  # dragon08-h4-hybrid-talib-volume-on/config.yaml
risk_guard.daily_drawdown_limit = -0.05  # dragon08-h4-hybrid-talib-volume-on/config.yaml
risk_guard.max_concurrent_trades_per_account = 2  # dragon08-h4-hybrid-talib-volume-on/config.yaml
risk_guard.max_leverage = 30  # dragon08-h4-hybrid-talib-volume-on/config.yaml
risk_guard.portfolio_at_risk_cap = 0.18  # dragon08-h4-hybrid-talib-volume-on/config.yaml
risk_guard.weekly_drawdown_limit = -0.15  # dragon08-h4-hybrid-talib-volume-on/config.yaml
schema_version = 2  # t13-hybrid-theta-60-40/config.yaml
volume_strength.lookback = 20  # dragon08-h4-hybrid-talib-volume-on/config.yaml
volume_strength.min_relative_activity = 1.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
```

## t14-candle-vol-off (job `2026-09-28-h4-tuning-sweep`)

Variant YAML:
```yaml
# t14-candle-vol-off: Registered cell: TA-Lib on, activity off.
# H4 tuning sweep 2026-09-28 (exploratory development window 2016-03..10; November 2016 read last).
schema_version: 2
extends: dragon08-h4-talib-volume-off
```

Resolved parameters:
```
capital_mgmt.assumed_leverage = 30.0  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.atr_multiplier = 2.0  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.lot_notional_units = 100000.0  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.min_reward_risk = 2.0  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.min_stop_factor = 1.2  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.min_stop_pips = 5.0  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.pip_value_per_lot = 10.0  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.risk_per_trade = 0.03  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.stop_distance_source = "swing"  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.stop_loss_pips = 20.0  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.stop_loss_shrink = 0.5  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.targets = [{"at_level_ratio": 4.0, "close_fraction": 0.5}, {"at_level_ratio": 6.0, "close_fraction": 0.5}]  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.trail_stops = [{"at_level_ratio": 2.0, "to_level_ratio": 0.1}]  # dragon08-h4-talib-volume-off/config.yaml
execution.broker_stop_level_pips = 0.0  # dragon08-h4-talib-volume-off/config.yaml
execution.close_on_veto = false  # dragon08-h4-talib-volume-off/config.yaml
execution.commission_per_lot = 0.0  # dragon08-h4-talib-volume-off/config.yaml
execution.min_hold_bars = 0  # dragon08-h4-talib-volume-off/config.yaml
execution.spread_pips = 1.0  # dragon08-h4-talib-volume-off/config.yaml
filters = ["f1_trend", "f2_indicator", "f3_pattern", "f5_risk_guard", "f6_capital_mgmt", "f7_meta_learner"]  # dragon08-h4-talib-volume-off/config.yaml
indicator.macd_hist_threshold = 0.0  # dragon08-h4-talib-volume-off/config.yaml
indicator.rsi_midline = 50.0  # dragon08-h4-talib-volume-off/config.yaml
meta_learner.families = ["trend", "indicator", "pattern"]  # dragon08-h4-talib-volume-off/config.yaml
meta_learner.label_horizon_minutes = 240  # dragon08-h4-talib-volume-off/config.yaml
meta_learner.regime_gate = false  # dragon08-h4-talib-volume-off/config.yaml
meta_learner.theta_high = 0.55  # dragon08-h4-talib-volume-off/config.yaml
meta_learner.theta_low = 0.45  # dragon08-h4-talib-volume-off/config.yaml
pattern.bearish_patterns = ["bearish_engulfing", "evening_star", "shooting_star"]  # dragon08-h4-talib-volume-off/config.yaml
pattern.bullish_patterns = ["bullish_engulfing", "hammer", "morning_star"]  # dragon08-h4-talib-volume-off/config.yaml
pattern.detector = "talib"  # dragon08-h4-talib-volume-off/config.yaml
perception_source = "ema"  # dragon08-h4-talib-volume-off/config.yaml
price_features.atr_period = 14  # dragon08-h4-talib-volume-off/config.yaml
price_features.bar_minutes = 240  # dragon08-h4-talib-volume-off/config.yaml
price_features.ema_fast = 3  # dragon08-h4-talib-volume-off/config.yaml
price_features.ema_higher_tf = 60  # dragon08-h4-talib-volume-off/config.yaml
price_features.ema_slow = 8  # dragon08-h4-talib-volume-off/config.yaml
price_features.macd_fast = 12  # dragon08-h4-talib-volume-off/config.yaml
price_features.macd_signal = 9  # dragon08-h4-talib-volume-off/config.yaml
price_features.macd_slow = 26  # dragon08-h4-talib-volume-off/config.yaml
price_features.rsi_period = 14  # dragon08-h4-talib-volume-off/config.yaml
price_features.swing_lookback_bars = 60  # dragon08-h4-talib-volume-off/config.yaml
risk_guard.daily_drawdown_limit = -0.05  # dragon08-h4-talib-volume-off/config.yaml
risk_guard.max_concurrent_trades_per_account = 2  # dragon08-h4-talib-volume-off/config.yaml
risk_guard.max_leverage = 30  # dragon08-h4-talib-volume-off/config.yaml
risk_guard.portfolio_at_risk_cap = 0.18  # dragon08-h4-talib-volume-off/config.yaml
risk_guard.weekly_drawdown_limit = -0.15  # dragon08-h4-talib-volume-off/config.yaml
schema_version = 2  # t14-candle-vol-off/config.yaml
```

## q10-base (job `2026-09-28-h4-tuning-sweep-q`)

Variant YAML:
```yaml
# q10-base: Calibrated thresholds, 10 % per side of the January validation quantiles; TA-Lib on, activity on.
# Thresholds from h4-threshold-calibration.json (January-2016 validation quantiles), registered 2026-09-28 02:15 UTC.
schema_version: 2
extends: dragon08-h4-talib-volume-on

meta_learner:
  theta_high: 0.5309
  theta_low: 0.52
```

Resolved parameters:
```
capital_mgmt.assumed_leverage = 30.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.atr_multiplier = 2.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.lot_notional_units = 100000.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_reward_risk = 2.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_stop_factor = 1.2  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_stop_pips = 5.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.pip_value_per_lot = 10.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.risk_per_trade = 0.03  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_distance_source = "swing"  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_loss_pips = 20.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_loss_shrink = 0.5  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.targets = [{"at_level_ratio": 4.0, "close_fraction": 0.5}, {"at_level_ratio": 6.0, "close_fraction": 0.5}]  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.trail_stops = [{"at_level_ratio": 2.0, "to_level_ratio": 0.1}]  # dragon08-h4-talib-volume-on/config.yaml
execution.broker_stop_level_pips = 0.0  # dragon08-h4-talib-volume-on/config.yaml
execution.close_on_veto = false  # dragon08-h4-talib-volume-on/config.yaml
execution.commission_per_lot = 0.0  # dragon08-h4-talib-volume-on/config.yaml
execution.min_hold_bars = 0  # dragon08-h4-talib-volume-on/config.yaml
execution.spread_pips = 1.0  # dragon08-h4-talib-volume-on/config.yaml
filters = ["f1_trend", "f2_indicator", "f3_pattern", "volume_strength", "f5_risk_guard", "f6_capital_mgmt", "f7_meta_learner"]  # dragon08-h4-talib-volume-on/config.yaml
indicator.macd_hist_threshold = 0.0  # dragon08-h4-talib-volume-on/config.yaml
indicator.rsi_midline = 50.0  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.families = ["trend", "indicator", "pattern"]  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.label_horizon_minutes = 240  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.regime_gate = false  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.theta_high = 0.5309  # q10-base/config.yaml
meta_learner.theta_low = 0.52  # q10-base/config.yaml
pattern.bearish_patterns = ["bearish_engulfing", "evening_star", "shooting_star"]  # dragon08-h4-talib-volume-on/config.yaml
pattern.bullish_patterns = ["bullish_engulfing", "hammer", "morning_star"]  # dragon08-h4-talib-volume-on/config.yaml
pattern.detector = "talib"  # dragon08-h4-talib-volume-on/config.yaml
perception_source = "ema"  # dragon08-h4-talib-volume-on/config.yaml
price_features.atr_period = 14  # dragon08-h4-talib-volume-on/config.yaml
price_features.bar_minutes = 240  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_fast = 3  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_higher_tf = 60  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_slow = 8  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_fast = 12  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_signal = 9  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_slow = 26  # dragon08-h4-talib-volume-on/config.yaml
price_features.rsi_period = 14  # dragon08-h4-talib-volume-on/config.yaml
price_features.swing_lookback_bars = 60  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.daily_drawdown_limit = -0.05  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.max_concurrent_trades_per_account = 2  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.max_leverage = 30  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.portfolio_at_risk_cap = 0.18  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.weekly_drawdown_limit = -0.15  # dragon08-h4-talib-volume-on/config.yaml
schema_version = 2  # q10-base/config.yaml
volume_strength.lookback = 20  # dragon08-h4-talib-volume-on/config.yaml
volume_strength.min_relative_activity = 1.0  # dragon08-h4-talib-volume-on/config.yaml
```

## q10-vol-off (job `2026-09-28-h4-tuning-sweep-q`)

Variant YAML:
```yaml
# q10-vol-off: As q10-base with the activity gate off.
# Thresholds from h4-threshold-calibration.json (January-2016 validation quantiles), registered 2026-09-28 02:15 UTC.
schema_version: 2
extends: dragon08-h4-talib-volume-off

meta_learner:
  theta_high: 0.5309
  theta_low: 0.52
```

Resolved parameters:
```
capital_mgmt.assumed_leverage = 30.0  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.atr_multiplier = 2.0  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.lot_notional_units = 100000.0  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.min_reward_risk = 2.0  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.min_stop_factor = 1.2  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.min_stop_pips = 5.0  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.pip_value_per_lot = 10.0  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.risk_per_trade = 0.03  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.stop_distance_source = "swing"  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.stop_loss_pips = 20.0  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.stop_loss_shrink = 0.5  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.targets = [{"at_level_ratio": 4.0, "close_fraction": 0.5}, {"at_level_ratio": 6.0, "close_fraction": 0.5}]  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.trail_stops = [{"at_level_ratio": 2.0, "to_level_ratio": 0.1}]  # dragon08-h4-talib-volume-off/config.yaml
execution.broker_stop_level_pips = 0.0  # dragon08-h4-talib-volume-off/config.yaml
execution.close_on_veto = false  # dragon08-h4-talib-volume-off/config.yaml
execution.commission_per_lot = 0.0  # dragon08-h4-talib-volume-off/config.yaml
execution.min_hold_bars = 0  # dragon08-h4-talib-volume-off/config.yaml
execution.spread_pips = 1.0  # dragon08-h4-talib-volume-off/config.yaml
filters = ["f1_trend", "f2_indicator", "f3_pattern", "f5_risk_guard", "f6_capital_mgmt", "f7_meta_learner"]  # dragon08-h4-talib-volume-off/config.yaml
indicator.macd_hist_threshold = 0.0  # dragon08-h4-talib-volume-off/config.yaml
indicator.rsi_midline = 50.0  # dragon08-h4-talib-volume-off/config.yaml
meta_learner.families = ["trend", "indicator", "pattern"]  # dragon08-h4-talib-volume-off/config.yaml
meta_learner.label_horizon_minutes = 240  # dragon08-h4-talib-volume-off/config.yaml
meta_learner.regime_gate = false  # dragon08-h4-talib-volume-off/config.yaml
meta_learner.theta_high = 0.5309  # q10-vol-off/config.yaml
meta_learner.theta_low = 0.52  # q10-vol-off/config.yaml
pattern.bearish_patterns = ["bearish_engulfing", "evening_star", "shooting_star"]  # dragon08-h4-talib-volume-off/config.yaml
pattern.bullish_patterns = ["bullish_engulfing", "hammer", "morning_star"]  # dragon08-h4-talib-volume-off/config.yaml
pattern.detector = "talib"  # dragon08-h4-talib-volume-off/config.yaml
perception_source = "ema"  # dragon08-h4-talib-volume-off/config.yaml
price_features.atr_period = 14  # dragon08-h4-talib-volume-off/config.yaml
price_features.bar_minutes = 240  # dragon08-h4-talib-volume-off/config.yaml
price_features.ema_fast = 3  # dragon08-h4-talib-volume-off/config.yaml
price_features.ema_higher_tf = 60  # dragon08-h4-talib-volume-off/config.yaml
price_features.ema_slow = 8  # dragon08-h4-talib-volume-off/config.yaml
price_features.macd_fast = 12  # dragon08-h4-talib-volume-off/config.yaml
price_features.macd_signal = 9  # dragon08-h4-talib-volume-off/config.yaml
price_features.macd_slow = 26  # dragon08-h4-talib-volume-off/config.yaml
price_features.rsi_period = 14  # dragon08-h4-talib-volume-off/config.yaml
price_features.swing_lookback_bars = 60  # dragon08-h4-talib-volume-off/config.yaml
risk_guard.daily_drawdown_limit = -0.05  # dragon08-h4-talib-volume-off/config.yaml
risk_guard.max_concurrent_trades_per_account = 2  # dragon08-h4-talib-volume-off/config.yaml
risk_guard.max_leverage = 30  # dragon08-h4-talib-volume-off/config.yaml
risk_guard.portfolio_at_risk_cap = 0.18  # dragon08-h4-talib-volume-off/config.yaml
risk_guard.weekly_drawdown_limit = -0.15  # dragon08-h4-talib-volume-off/config.yaml
schema_version = 2  # q10-vol-off/config.yaml
```

## q05-base (job `2026-09-28-h4-tuning-sweep-q`)

Variant YAML:
```yaml
# q05-base: Sensitivity: 5 % per side.
# Thresholds from h4-threshold-calibration.json (January-2016 validation quantiles), registered 2026-09-28 02:15 UTC.
schema_version: 2
extends: dragon08-h4-talib-volume-on

meta_learner:
  theta_high: 0.5338
  theta_low: 0.5189
```

Resolved parameters:
```
capital_mgmt.assumed_leverage = 30.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.atr_multiplier = 2.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.lot_notional_units = 100000.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_reward_risk = 2.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_stop_factor = 1.2  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_stop_pips = 5.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.pip_value_per_lot = 10.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.risk_per_trade = 0.03  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_distance_source = "swing"  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_loss_pips = 20.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_loss_shrink = 0.5  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.targets = [{"at_level_ratio": 4.0, "close_fraction": 0.5}, {"at_level_ratio": 6.0, "close_fraction": 0.5}]  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.trail_stops = [{"at_level_ratio": 2.0, "to_level_ratio": 0.1}]  # dragon08-h4-talib-volume-on/config.yaml
execution.broker_stop_level_pips = 0.0  # dragon08-h4-talib-volume-on/config.yaml
execution.close_on_veto = false  # dragon08-h4-talib-volume-on/config.yaml
execution.commission_per_lot = 0.0  # dragon08-h4-talib-volume-on/config.yaml
execution.min_hold_bars = 0  # dragon08-h4-talib-volume-on/config.yaml
execution.spread_pips = 1.0  # dragon08-h4-talib-volume-on/config.yaml
filters = ["f1_trend", "f2_indicator", "f3_pattern", "volume_strength", "f5_risk_guard", "f6_capital_mgmt", "f7_meta_learner"]  # dragon08-h4-talib-volume-on/config.yaml
indicator.macd_hist_threshold = 0.0  # dragon08-h4-talib-volume-on/config.yaml
indicator.rsi_midline = 50.0  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.families = ["trend", "indicator", "pattern"]  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.label_horizon_minutes = 240  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.regime_gate = false  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.theta_high = 0.5338  # q05-base/config.yaml
meta_learner.theta_low = 0.5189  # q05-base/config.yaml
pattern.bearish_patterns = ["bearish_engulfing", "evening_star", "shooting_star"]  # dragon08-h4-talib-volume-on/config.yaml
pattern.bullish_patterns = ["bullish_engulfing", "hammer", "morning_star"]  # dragon08-h4-talib-volume-on/config.yaml
pattern.detector = "talib"  # dragon08-h4-talib-volume-on/config.yaml
perception_source = "ema"  # dragon08-h4-talib-volume-on/config.yaml
price_features.atr_period = 14  # dragon08-h4-talib-volume-on/config.yaml
price_features.bar_minutes = 240  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_fast = 3  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_higher_tf = 60  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_slow = 8  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_fast = 12  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_signal = 9  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_slow = 26  # dragon08-h4-talib-volume-on/config.yaml
price_features.rsi_period = 14  # dragon08-h4-talib-volume-on/config.yaml
price_features.swing_lookback_bars = 60  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.daily_drawdown_limit = -0.05  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.max_concurrent_trades_per_account = 2  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.max_leverage = 30  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.portfolio_at_risk_cap = 0.18  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.weekly_drawdown_limit = -0.15  # dragon08-h4-talib-volume-on/config.yaml
schema_version = 2  # q05-base/config.yaml
volume_strength.lookback = 20  # dragon08-h4-talib-volume-on/config.yaml
volume_strength.min_relative_activity = 1.0  # dragon08-h4-talib-volume-on/config.yaml
```

## q15-base (job `2026-09-28-h4-tuning-sweep-q`)

Variant YAML:
```yaml
# q15-base: Sensitivity: 15 % per side.
# Thresholds from h4-threshold-calibration.json (January-2016 validation quantiles), registered 2026-09-28 02:15 UTC.
schema_version: 2
extends: dragon08-h4-talib-volume-on

meta_learner:
  theta_high: 0.5282
  theta_low: 0.5215
```

Resolved parameters:
```
capital_mgmt.assumed_leverage = 30.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.atr_multiplier = 2.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.lot_notional_units = 100000.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_reward_risk = 2.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_stop_factor = 1.2  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_stop_pips = 5.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.pip_value_per_lot = 10.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.risk_per_trade = 0.03  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_distance_source = "swing"  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_loss_pips = 20.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_loss_shrink = 0.5  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.targets = [{"at_level_ratio": 4.0, "close_fraction": 0.5}, {"at_level_ratio": 6.0, "close_fraction": 0.5}]  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.trail_stops = [{"at_level_ratio": 2.0, "to_level_ratio": 0.1}]  # dragon08-h4-talib-volume-on/config.yaml
execution.broker_stop_level_pips = 0.0  # dragon08-h4-talib-volume-on/config.yaml
execution.close_on_veto = false  # dragon08-h4-talib-volume-on/config.yaml
execution.commission_per_lot = 0.0  # dragon08-h4-talib-volume-on/config.yaml
execution.min_hold_bars = 0  # dragon08-h4-talib-volume-on/config.yaml
execution.spread_pips = 1.0  # dragon08-h4-talib-volume-on/config.yaml
filters = ["f1_trend", "f2_indicator", "f3_pattern", "volume_strength", "f5_risk_guard", "f6_capital_mgmt", "f7_meta_learner"]  # dragon08-h4-talib-volume-on/config.yaml
indicator.macd_hist_threshold = 0.0  # dragon08-h4-talib-volume-on/config.yaml
indicator.rsi_midline = 50.0  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.families = ["trend", "indicator", "pattern"]  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.label_horizon_minutes = 240  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.regime_gate = false  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.theta_high = 0.5282  # q15-base/config.yaml
meta_learner.theta_low = 0.5215  # q15-base/config.yaml
pattern.bearish_patterns = ["bearish_engulfing", "evening_star", "shooting_star"]  # dragon08-h4-talib-volume-on/config.yaml
pattern.bullish_patterns = ["bullish_engulfing", "hammer", "morning_star"]  # dragon08-h4-talib-volume-on/config.yaml
pattern.detector = "talib"  # dragon08-h4-talib-volume-on/config.yaml
perception_source = "ema"  # dragon08-h4-talib-volume-on/config.yaml
price_features.atr_period = 14  # dragon08-h4-talib-volume-on/config.yaml
price_features.bar_minutes = 240  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_fast = 3  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_higher_tf = 60  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_slow = 8  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_fast = 12  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_signal = 9  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_slow = 26  # dragon08-h4-talib-volume-on/config.yaml
price_features.rsi_period = 14  # dragon08-h4-talib-volume-on/config.yaml
price_features.swing_lookback_bars = 60  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.daily_drawdown_limit = -0.05  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.max_concurrent_trades_per_account = 2  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.max_leverage = 30  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.portfolio_at_risk_cap = 0.18  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.weekly_drawdown_limit = -0.15  # dragon08-h4-talib-volume-on/config.yaml
schema_version = 2  # q15-base/config.yaml
volume_strength.lookback = 20  # dragon08-h4-talib-volume-on/config.yaml
volume_strength.min_relative_activity = 1.0  # dragon08-h4-talib-volume-on/config.yaml
```

## q10-gate-on (job `2026-09-28-h4-tuning-sweep-q`)

Variant YAML:
```yaml
# q10-gate-on: q10 with the regime gate on.
# Thresholds from h4-threshold-calibration.json (January-2016 validation quantiles), registered 2026-09-28 02:15 UTC.
schema_version: 2
extends: dragon08-h4-talib-volume-on

meta_learner:
  theta_high: 0.5309
  theta_low: 0.52
  regime_gate: true
```

Resolved parameters:
```
capital_mgmt.assumed_leverage = 30.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.atr_multiplier = 2.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.lot_notional_units = 100000.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_reward_risk = 2.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_stop_factor = 1.2  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_stop_pips = 5.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.pip_value_per_lot = 10.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.risk_per_trade = 0.03  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_distance_source = "swing"  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_loss_pips = 20.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_loss_shrink = 0.5  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.targets = [{"at_level_ratio": 4.0, "close_fraction": 0.5}, {"at_level_ratio": 6.0, "close_fraction": 0.5}]  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.trail_stops = [{"at_level_ratio": 2.0, "to_level_ratio": 0.1}]  # dragon08-h4-talib-volume-on/config.yaml
execution.broker_stop_level_pips = 0.0  # dragon08-h4-talib-volume-on/config.yaml
execution.close_on_veto = false  # dragon08-h4-talib-volume-on/config.yaml
execution.commission_per_lot = 0.0  # dragon08-h4-talib-volume-on/config.yaml
execution.min_hold_bars = 0  # dragon08-h4-talib-volume-on/config.yaml
execution.spread_pips = 1.0  # dragon08-h4-talib-volume-on/config.yaml
filters = ["f1_trend", "f2_indicator", "f3_pattern", "volume_strength", "f5_risk_guard", "f6_capital_mgmt", "f7_meta_learner"]  # dragon08-h4-talib-volume-on/config.yaml
indicator.macd_hist_threshold = 0.0  # dragon08-h4-talib-volume-on/config.yaml
indicator.rsi_midline = 50.0  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.families = ["trend", "indicator", "pattern"]  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.label_horizon_minutes = 240  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.regime_gate = true  # q10-gate-on/config.yaml
meta_learner.theta_high = 0.5309  # q10-gate-on/config.yaml
meta_learner.theta_low = 0.52  # q10-gate-on/config.yaml
pattern.bearish_patterns = ["bearish_engulfing", "evening_star", "shooting_star"]  # dragon08-h4-talib-volume-on/config.yaml
pattern.bullish_patterns = ["bullish_engulfing", "hammer", "morning_star"]  # dragon08-h4-talib-volume-on/config.yaml
pattern.detector = "talib"  # dragon08-h4-talib-volume-on/config.yaml
perception_source = "ema"  # dragon08-h4-talib-volume-on/config.yaml
price_features.atr_period = 14  # dragon08-h4-talib-volume-on/config.yaml
price_features.bar_minutes = 240  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_fast = 3  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_higher_tf = 60  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_slow = 8  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_fast = 12  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_signal = 9  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_slow = 26  # dragon08-h4-talib-volume-on/config.yaml
price_features.rsi_period = 14  # dragon08-h4-talib-volume-on/config.yaml
price_features.swing_lookback_bars = 60  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.daily_drawdown_limit = -0.05  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.max_concurrent_trades_per_account = 2  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.max_leverage = 30  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.portfolio_at_risk_cap = 0.18  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.weekly_drawdown_limit = -0.15  # dragon08-h4-talib-volume-on/config.yaml
schema_version = 2  # q10-gate-on/config.yaml
volume_strength.lookback = 20  # dragon08-h4-talib-volume-on/config.yaml
volume_strength.min_relative_activity = 1.0  # dragon08-h4-talib-volume-on/config.yaml
```

## q10-plan-dragon05 (job `2026-09-28-h4-tuning-sweep-q`)

Variant YAML:
```yaml
# q10-plan-dragon05: q10 with the Dragon05 plan (1R/50 %, 2R rest, trail 1R -> breakeven).
# Thresholds from h4-threshold-calibration.json (January-2016 validation quantiles), registered 2026-09-28 02:15 UTC.
schema_version: 2
extends: dragon08-h4-talib-volume-on

meta_learner:
  theta_high: 0.5309
  theta_low: 0.52
capital_mgmt:
  stop_loss_shrink: 0.50
  targets:
    - {at_level_ratio: 1.0, close_fraction: 0.5}
    - {at_level_ratio: 2.0, close_fraction: 0.5}
  trail_stops:
    - {at_level_ratio: 1.0, to_level_ratio: 0.0}
  min_reward_risk: 2.0
```

Resolved parameters:
```
capital_mgmt.assumed_leverage = 30.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.atr_multiplier = 2.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.lot_notional_units = 100000.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_reward_risk = 2.0  # q10-plan-dragon05/config.yaml
capital_mgmt.min_stop_factor = 1.2  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_stop_pips = 5.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.pip_value_per_lot = 10.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.risk_per_trade = 0.03  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_distance_source = "swing"  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_loss_pips = 20.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_loss_shrink = 0.5  # q10-plan-dragon05/config.yaml
capital_mgmt.targets = [{"at_level_ratio": 1.0, "close_fraction": 0.5}, {"at_level_ratio": 2.0, "close_fraction": 0.5}]  # q10-plan-dragon05/config.yaml
capital_mgmt.trail_stops = [{"at_level_ratio": 1.0, "to_level_ratio": 0.0}]  # q10-plan-dragon05/config.yaml
execution.broker_stop_level_pips = 0.0  # dragon08-h4-talib-volume-on/config.yaml
execution.close_on_veto = false  # dragon08-h4-talib-volume-on/config.yaml
execution.commission_per_lot = 0.0  # dragon08-h4-talib-volume-on/config.yaml
execution.min_hold_bars = 0  # dragon08-h4-talib-volume-on/config.yaml
execution.spread_pips = 1.0  # dragon08-h4-talib-volume-on/config.yaml
filters = ["f1_trend", "f2_indicator", "f3_pattern", "volume_strength", "f5_risk_guard", "f6_capital_mgmt", "f7_meta_learner"]  # dragon08-h4-talib-volume-on/config.yaml
indicator.macd_hist_threshold = 0.0  # dragon08-h4-talib-volume-on/config.yaml
indicator.rsi_midline = 50.0  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.families = ["trend", "indicator", "pattern"]  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.label_horizon_minutes = 240  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.regime_gate = false  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.theta_high = 0.5309  # q10-plan-dragon05/config.yaml
meta_learner.theta_low = 0.52  # q10-plan-dragon05/config.yaml
pattern.bearish_patterns = ["bearish_engulfing", "evening_star", "shooting_star"]  # dragon08-h4-talib-volume-on/config.yaml
pattern.bullish_patterns = ["bullish_engulfing", "hammer", "morning_star"]  # dragon08-h4-talib-volume-on/config.yaml
pattern.detector = "talib"  # dragon08-h4-talib-volume-on/config.yaml
perception_source = "ema"  # dragon08-h4-talib-volume-on/config.yaml
price_features.atr_period = 14  # dragon08-h4-talib-volume-on/config.yaml
price_features.bar_minutes = 240  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_fast = 3  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_higher_tf = 60  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_slow = 8  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_fast = 12  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_signal = 9  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_slow = 26  # dragon08-h4-talib-volume-on/config.yaml
price_features.rsi_period = 14  # dragon08-h4-talib-volume-on/config.yaml
price_features.swing_lookback_bars = 60  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.daily_drawdown_limit = -0.05  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.max_concurrent_trades_per_account = 2  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.max_leverage = 30  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.portfolio_at_risk_cap = 0.18  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.weekly_drawdown_limit = -0.15  # dragon08-h4-talib-volume-on/config.yaml
schema_version = 2  # q10-plan-dragon05/config.yaml
volume_strength.lookback = 20  # dragon08-h4-talib-volume-on/config.yaml
volume_strength.min_relative_activity = 1.0  # dragon08-h4-talib-volume-on/config.yaml
```

## q10-atr-stop (job `2026-09-28-h4-tuning-sweep-q`)

Variant YAML:
```yaml
# q10-atr-stop: q10 with an ATR stop (2 x ATR14 H4, floor 10 pips, no shrink).
# Thresholds from h4-threshold-calibration.json (January-2016 validation quantiles), registered 2026-09-28 02:15 UTC.
schema_version: 2
extends: dragon08-h4-talib-volume-on

meta_learner:
  theta_high: 0.5309
  theta_low: 0.52
capital_mgmt:
  stop_distance_source: atr
  atr_multiplier: 2.0
  min_stop_pips: 10.0
  stop_loss_shrink: 0.0
```

Resolved parameters:
```
capital_mgmt.assumed_leverage = 30.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.atr_multiplier = 2.0  # q10-atr-stop/config.yaml
capital_mgmt.lot_notional_units = 100000.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_reward_risk = 2.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_stop_factor = 1.2  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_stop_pips = 10.0  # q10-atr-stop/config.yaml
capital_mgmt.pip_value_per_lot = 10.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.risk_per_trade = 0.03  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_distance_source = "atr"  # q10-atr-stop/config.yaml
capital_mgmt.stop_loss_pips = 20.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_loss_shrink = 0.0  # q10-atr-stop/config.yaml
capital_mgmt.targets = [{"at_level_ratio": 4.0, "close_fraction": 0.5}, {"at_level_ratio": 6.0, "close_fraction": 0.5}]  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.trail_stops = [{"at_level_ratio": 2.0, "to_level_ratio": 0.1}]  # dragon08-h4-talib-volume-on/config.yaml
execution.broker_stop_level_pips = 0.0  # dragon08-h4-talib-volume-on/config.yaml
execution.close_on_veto = false  # dragon08-h4-talib-volume-on/config.yaml
execution.commission_per_lot = 0.0  # dragon08-h4-talib-volume-on/config.yaml
execution.min_hold_bars = 0  # dragon08-h4-talib-volume-on/config.yaml
execution.spread_pips = 1.0  # dragon08-h4-talib-volume-on/config.yaml
filters = ["f1_trend", "f2_indicator", "f3_pattern", "volume_strength", "f5_risk_guard", "f6_capital_mgmt", "f7_meta_learner"]  # dragon08-h4-talib-volume-on/config.yaml
indicator.macd_hist_threshold = 0.0  # dragon08-h4-talib-volume-on/config.yaml
indicator.rsi_midline = 50.0  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.families = ["trend", "indicator", "pattern"]  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.label_horizon_minutes = 240  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.regime_gate = false  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.theta_high = 0.5309  # q10-atr-stop/config.yaml
meta_learner.theta_low = 0.52  # q10-atr-stop/config.yaml
pattern.bearish_patterns = ["bearish_engulfing", "evening_star", "shooting_star"]  # dragon08-h4-talib-volume-on/config.yaml
pattern.bullish_patterns = ["bullish_engulfing", "hammer", "morning_star"]  # dragon08-h4-talib-volume-on/config.yaml
pattern.detector = "talib"  # dragon08-h4-talib-volume-on/config.yaml
perception_source = "ema"  # dragon08-h4-talib-volume-on/config.yaml
price_features.atr_period = 14  # dragon08-h4-talib-volume-on/config.yaml
price_features.bar_minutes = 240  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_fast = 3  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_higher_tf = 60  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_slow = 8  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_fast = 12  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_signal = 9  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_slow = 26  # dragon08-h4-talib-volume-on/config.yaml
price_features.rsi_period = 14  # dragon08-h4-talib-volume-on/config.yaml
price_features.swing_lookback_bars = 60  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.daily_drawdown_limit = -0.05  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.max_concurrent_trades_per_account = 2  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.max_leverage = 30  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.portfolio_at_risk_cap = 0.18  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.weekly_drawdown_limit = -0.15  # dragon08-h4-talib-volume-on/config.yaml
schema_version = 2  # q10-atr-stop/config.yaml
volume_strength.lookback = 20  # dragon08-h4-talib-volume-on/config.yaml
volume_strength.min_relative_activity = 1.0  # dragon08-h4-talib-volume-on/config.yaml
```

## q10-vol-0.8 (job `2026-09-28-h4-tuning-sweep-q`)

Variant YAML:
```yaml
# q10-vol-0.8: q10 with activity threshold 0.8.
# Thresholds from h4-threshold-calibration.json (January-2016 validation quantiles), registered 2026-09-28 02:15 UTC.
schema_version: 2
extends: dragon08-h4-talib-volume-on

meta_learner:
  theta_high: 0.5309
  theta_low: 0.52
volume_strength:
  lookback: 20
  min_relative_activity: 0.8
```

Resolved parameters:
```
capital_mgmt.assumed_leverage = 30.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.atr_multiplier = 2.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.lot_notional_units = 100000.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_reward_risk = 2.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_stop_factor = 1.2  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_stop_pips = 5.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.pip_value_per_lot = 10.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.risk_per_trade = 0.03  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_distance_source = "swing"  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_loss_pips = 20.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_loss_shrink = 0.5  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.targets = [{"at_level_ratio": 4.0, "close_fraction": 0.5}, {"at_level_ratio": 6.0, "close_fraction": 0.5}]  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.trail_stops = [{"at_level_ratio": 2.0, "to_level_ratio": 0.1}]  # dragon08-h4-talib-volume-on/config.yaml
execution.broker_stop_level_pips = 0.0  # dragon08-h4-talib-volume-on/config.yaml
execution.close_on_veto = false  # dragon08-h4-talib-volume-on/config.yaml
execution.commission_per_lot = 0.0  # dragon08-h4-talib-volume-on/config.yaml
execution.min_hold_bars = 0  # dragon08-h4-talib-volume-on/config.yaml
execution.spread_pips = 1.0  # dragon08-h4-talib-volume-on/config.yaml
filters = ["f1_trend", "f2_indicator", "f3_pattern", "volume_strength", "f5_risk_guard", "f6_capital_mgmt", "f7_meta_learner"]  # dragon08-h4-talib-volume-on/config.yaml
indicator.macd_hist_threshold = 0.0  # dragon08-h4-talib-volume-on/config.yaml
indicator.rsi_midline = 50.0  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.families = ["trend", "indicator", "pattern"]  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.label_horizon_minutes = 240  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.regime_gate = false  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.theta_high = 0.5309  # q10-vol-0.8/config.yaml
meta_learner.theta_low = 0.52  # q10-vol-0.8/config.yaml
pattern.bearish_patterns = ["bearish_engulfing", "evening_star", "shooting_star"]  # dragon08-h4-talib-volume-on/config.yaml
pattern.bullish_patterns = ["bullish_engulfing", "hammer", "morning_star"]  # dragon08-h4-talib-volume-on/config.yaml
pattern.detector = "talib"  # dragon08-h4-talib-volume-on/config.yaml
perception_source = "ema"  # dragon08-h4-talib-volume-on/config.yaml
price_features.atr_period = 14  # dragon08-h4-talib-volume-on/config.yaml
price_features.bar_minutes = 240  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_fast = 3  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_higher_tf = 60  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_slow = 8  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_fast = 12  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_signal = 9  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_slow = 26  # dragon08-h4-talib-volume-on/config.yaml
price_features.rsi_period = 14  # dragon08-h4-talib-volume-on/config.yaml
price_features.swing_lookback_bars = 60  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.daily_drawdown_limit = -0.05  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.max_concurrent_trades_per_account = 2  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.max_leverage = 30  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.portfolio_at_risk_cap = 0.18  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.weekly_drawdown_limit = -0.15  # dragon08-h4-talib-volume-on/config.yaml
schema_version = 2  # q10-vol-0.8/config.yaml
volume_strength.lookback = 20  # q10-vol-0.8/config.yaml
volume_strength.min_relative_activity = 0.8  # q10-vol-0.8/config.yaml
```

## q10-nocandle (job `2026-09-28-h4-tuning-sweep-q`)

Variant YAML:
```yaml
# q10-nocandle: Control: detector disabled, activity on, calibrated thresholds of model B.
# Thresholds from h4-threshold-calibration.json (January-2016 validation quantiles), registered 2026-09-28 02:15 UTC.
schema_version: 2
extends: dragon08-h4-disabled-volume-on

meta_learner:
  theta_high: 0.531
  theta_low: 0.5209
```

Resolved parameters:
```
capital_mgmt.assumed_leverage = 30.0  # dragon08-h4-disabled-volume-on/config.yaml
capital_mgmt.atr_multiplier = 2.0  # dragon08-h4-disabled-volume-on/config.yaml
capital_mgmt.lot_notional_units = 100000.0  # dragon08-h4-disabled-volume-on/config.yaml
capital_mgmt.min_reward_risk = 2.0  # dragon08-h4-disabled-volume-on/config.yaml
capital_mgmt.min_stop_factor = 1.2  # dragon08-h4-disabled-volume-on/config.yaml
capital_mgmt.min_stop_pips = 5.0  # dragon08-h4-disabled-volume-on/config.yaml
capital_mgmt.pip_value_per_lot = 10.0  # dragon08-h4-disabled-volume-on/config.yaml
capital_mgmt.risk_per_trade = 0.03  # dragon08-h4-disabled-volume-on/config.yaml
capital_mgmt.stop_distance_source = "swing"  # dragon08-h4-disabled-volume-on/config.yaml
capital_mgmt.stop_loss_pips = 20.0  # dragon08-h4-disabled-volume-on/config.yaml
capital_mgmt.stop_loss_shrink = 0.5  # dragon08-h4-disabled-volume-on/config.yaml
capital_mgmt.targets = [{"at_level_ratio": 4.0, "close_fraction": 0.5}, {"at_level_ratio": 6.0, "close_fraction": 0.5}]  # dragon08-h4-disabled-volume-on/config.yaml
capital_mgmt.trail_stops = [{"at_level_ratio": 2.0, "to_level_ratio": 0.1}]  # dragon08-h4-disabled-volume-on/config.yaml
execution.broker_stop_level_pips = 0.0  # dragon08-h4-disabled-volume-on/config.yaml
execution.close_on_veto = false  # dragon08-h4-disabled-volume-on/config.yaml
execution.commission_per_lot = 0.0  # dragon08-h4-disabled-volume-on/config.yaml
execution.min_hold_bars = 0  # dragon08-h4-disabled-volume-on/config.yaml
execution.spread_pips = 1.0  # dragon08-h4-disabled-volume-on/config.yaml
filters = ["f1_trend", "f2_indicator", "f3_pattern", "volume_strength", "f5_risk_guard", "f6_capital_mgmt", "f7_meta_learner"]  # dragon08-h4-disabled-volume-on/config.yaml
indicator.macd_hist_threshold = 0.0  # dragon08-h4-disabled-volume-on/config.yaml
indicator.rsi_midline = 50.0  # dragon08-h4-disabled-volume-on/config.yaml
meta_learner.families = ["trend", "indicator", "pattern"]  # dragon08-h4-disabled-volume-on/config.yaml
meta_learner.label_horizon_minutes = 240  # dragon08-h4-disabled-volume-on/config.yaml
meta_learner.regime_gate = false  # dragon08-h4-disabled-volume-on/config.yaml
meta_learner.theta_high = 0.531  # q10-nocandle/config.yaml
meta_learner.theta_low = 0.5209  # q10-nocandle/config.yaml
pattern.bearish_patterns = ["bearish_engulfing", "evening_star", "shooting_star"]  # dragon08-h4-disabled-volume-on/config.yaml
pattern.bullish_patterns = ["bullish_engulfing", "hammer", "morning_star"]  # dragon08-h4-disabled-volume-on/config.yaml
pattern.detector = "disabled"  # dragon08-h4-disabled-volume-on/config.yaml
perception_source = "ema"  # dragon08-h4-disabled-volume-on/config.yaml
price_features.atr_period = 14  # dragon08-h4-disabled-volume-on/config.yaml
price_features.bar_minutes = 240  # dragon08-h4-disabled-volume-on/config.yaml
price_features.ema_fast = 3  # dragon08-h4-disabled-volume-on/config.yaml
price_features.ema_higher_tf = 60  # dragon08-h4-disabled-volume-on/config.yaml
price_features.ema_slow = 8  # dragon08-h4-disabled-volume-on/config.yaml
price_features.macd_fast = 12  # dragon08-h4-disabled-volume-on/config.yaml
price_features.macd_signal = 9  # dragon08-h4-disabled-volume-on/config.yaml
price_features.macd_slow = 26  # dragon08-h4-disabled-volume-on/config.yaml
price_features.rsi_period = 14  # dragon08-h4-disabled-volume-on/config.yaml
price_features.swing_lookback_bars = 60  # dragon08-h4-disabled-volume-on/config.yaml
risk_guard.daily_drawdown_limit = -0.05  # dragon08-h4-disabled-volume-on/config.yaml
risk_guard.max_concurrent_trades_per_account = 2  # dragon08-h4-disabled-volume-on/config.yaml
risk_guard.max_leverage = 30  # dragon08-h4-disabled-volume-on/config.yaml
risk_guard.portfolio_at_risk_cap = 0.18  # dragon08-h4-disabled-volume-on/config.yaml
risk_guard.weekly_drawdown_limit = -0.15  # dragon08-h4-disabled-volume-on/config.yaml
schema_version = 2  # q10-nocandle/config.yaml
volume_strength.lookback = 20  # dragon08-h4-disabled-volume-on/config.yaml
volume_strength.min_relative_activity = 1.0  # dragon08-h4-disabled-volume-on/config.yaml
```

## q10-hybrid (job `2026-09-28-h4-tuning-sweep-q`)

Variant YAML:
```yaml
# q10-hybrid: Hybrid, calibrated thresholds of model C, activity on.
# Thresholds from h4-threshold-calibration.json (January-2016 validation quantiles), registered 2026-09-28 02:15 UTC.
schema_version: 2
extends: dragon08-h4-hybrid-talib-volume-on

meta_learner:
  theta_high: 0.5308
  theta_low: 0.5208
```

Resolved parameters:
```
capital_mgmt.assumed_leverage = 30.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.atr_multiplier = 2.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.lot_notional_units = 100000.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.min_reward_risk = 2.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.min_stop_factor = 1.2  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.min_stop_pips = 5.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.pip_value_per_lot = 10.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.risk_per_trade = 0.03  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.stop_distance_source = "swing"  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.stop_loss_pips = 20.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.stop_loss_shrink = 0.5  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.targets = [{"at_level_ratio": 4.0, "close_fraction": 0.5}, {"at_level_ratio": 6.0, "close_fraction": 0.5}]  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.trail_stops = [{"at_level_ratio": 2.0, "to_level_ratio": 0.1}]  # dragon08-h4-hybrid-talib-volume-on/config.yaml
execution.broker_stop_level_pips = 0.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
execution.close_on_veto = false  # dragon08-h4-hybrid-talib-volume-on/config.yaml
execution.commission_per_lot = 0.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
execution.min_hold_bars = 0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
execution.spread_pips = 1.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
filters = ["f1_trend", "f2_indicator", "f3_pattern", "f4_news_context", "volume_strength", "f5_risk_guard", "f6_capital_mgmt", "f7_meta_learner"]  # dragon08-h4-hybrid-talib-volume-on/config.yaml
indicator.macd_hist_threshold = 0.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
indicator.rsi_midline = 50.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
meta_learner.families = ["trend", "indicator", "pattern", "news"]  # dragon08-h4-hybrid-talib-volume-on/config.yaml
meta_learner.label_horizon_minutes = 240  # dragon08-h4-hybrid-talib-volume-on/config.yaml
meta_learner.regime_gate = false  # dragon08-h4-hybrid-talib-volume-on/config.yaml
meta_learner.theta_high = 0.5308  # q10-hybrid/config.yaml
meta_learner.theta_low = 0.5208  # q10-hybrid/config.yaml
news_context.event_intensity_veto_threshold = -0.5  # dragon08-h4-hybrid-talib-volume-on/config.yaml
news_context.sentiment_direction_threshold = 0.15  # dragon08-h4-hybrid-talib-volume-on/config.yaml
pattern.bearish_patterns = ["bearish_engulfing", "evening_star", "shooting_star"]  # dragon08-h4-hybrid-talib-volume-on/config.yaml
pattern.bullish_patterns = ["bullish_engulfing", "hammer", "morning_star"]  # dragon08-h4-hybrid-talib-volume-on/config.yaml
pattern.detector = "talib"  # dragon08-h4-hybrid-talib-volume-on/config.yaml
perception_source = "ema"  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.atr_period = 14  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.bar_minutes = 240  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.ema_fast = 3  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.ema_higher_tf = 60  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.ema_slow = 8  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.macd_fast = 12  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.macd_signal = 9  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.macd_slow = 26  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.rsi_period = 14  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.swing_lookback_bars = 60  # dragon08-h4-hybrid-talib-volume-on/config.yaml
risk_guard.daily_drawdown_limit = -0.05  # dragon08-h4-hybrid-talib-volume-on/config.yaml
risk_guard.max_concurrent_trades_per_account = 2  # dragon08-h4-hybrid-talib-volume-on/config.yaml
risk_guard.max_leverage = 30  # dragon08-h4-hybrid-talib-volume-on/config.yaml
risk_guard.portfolio_at_risk_cap = 0.18  # dragon08-h4-hybrid-talib-volume-on/config.yaml
risk_guard.weekly_drawdown_limit = -0.15  # dragon08-h4-hybrid-talib-volume-on/config.yaml
schema_version = 2  # q10-hybrid/config.yaml
volume_strength.lookback = 20  # dragon08-h4-hybrid-talib-volume-on/config.yaml
volume_strength.min_relative_activity = 1.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
```

## q10-hybrid-vol-off (job `2026-09-28-h4-tuning-sweep-q`)

Variant YAML:
```yaml
# q10-hybrid-vol-off: Hybrid, calibrated thresholds of model C, activity off.
# Thresholds from h4-threshold-calibration.json (January-2016 validation quantiles), registered 2026-09-28 02:15 UTC.
schema_version: 2
extends: dragon08-h4-hybrid-talib-volume-off

meta_learner:
  theta_high: 0.5308
  theta_low: 0.5208
```

Resolved parameters:
```
capital_mgmt.assumed_leverage = 30.0  # dragon08-h4-hybrid-talib-volume-off/config.yaml
capital_mgmt.atr_multiplier = 2.0  # dragon08-h4-hybrid-talib-volume-off/config.yaml
capital_mgmt.lot_notional_units = 100000.0  # dragon08-h4-hybrid-talib-volume-off/config.yaml
capital_mgmt.min_reward_risk = 2.0  # dragon08-h4-hybrid-talib-volume-off/config.yaml
capital_mgmt.min_stop_factor = 1.2  # dragon08-h4-hybrid-talib-volume-off/config.yaml
capital_mgmt.min_stop_pips = 5.0  # dragon08-h4-hybrid-talib-volume-off/config.yaml
capital_mgmt.pip_value_per_lot = 10.0  # dragon08-h4-hybrid-talib-volume-off/config.yaml
capital_mgmt.risk_per_trade = 0.03  # dragon08-h4-hybrid-talib-volume-off/config.yaml
capital_mgmt.stop_distance_source = "swing"  # dragon08-h4-hybrid-talib-volume-off/config.yaml
capital_mgmt.stop_loss_pips = 20.0  # dragon08-h4-hybrid-talib-volume-off/config.yaml
capital_mgmt.stop_loss_shrink = 0.5  # dragon08-h4-hybrid-talib-volume-off/config.yaml
capital_mgmt.targets = [{"at_level_ratio": 4.0, "close_fraction": 0.5}, {"at_level_ratio": 6.0, "close_fraction": 0.5}]  # dragon08-h4-hybrid-talib-volume-off/config.yaml
capital_mgmt.trail_stops = [{"at_level_ratio": 2.0, "to_level_ratio": 0.1}]  # dragon08-h4-hybrid-talib-volume-off/config.yaml
execution.broker_stop_level_pips = 0.0  # dragon08-h4-hybrid-talib-volume-off/config.yaml
execution.close_on_veto = false  # dragon08-h4-hybrid-talib-volume-off/config.yaml
execution.commission_per_lot = 0.0  # dragon08-h4-hybrid-talib-volume-off/config.yaml
execution.min_hold_bars = 0  # dragon08-h4-hybrid-talib-volume-off/config.yaml
execution.spread_pips = 1.0  # dragon08-h4-hybrid-talib-volume-off/config.yaml
filters = ["f1_trend", "f2_indicator", "f3_pattern", "f4_news_context", "f5_risk_guard", "f6_capital_mgmt", "f7_meta_learner"]  # dragon08-h4-hybrid-talib-volume-off/config.yaml
indicator.macd_hist_threshold = 0.0  # dragon08-h4-hybrid-talib-volume-off/config.yaml
indicator.rsi_midline = 50.0  # dragon08-h4-hybrid-talib-volume-off/config.yaml
meta_learner.families = ["trend", "indicator", "pattern", "news"]  # dragon08-h4-hybrid-talib-volume-off/config.yaml
meta_learner.label_horizon_minutes = 240  # dragon08-h4-hybrid-talib-volume-off/config.yaml
meta_learner.regime_gate = false  # dragon08-h4-hybrid-talib-volume-off/config.yaml
meta_learner.theta_high = 0.5308  # q10-hybrid-vol-off/config.yaml
meta_learner.theta_low = 0.5208  # q10-hybrid-vol-off/config.yaml
news_context.event_intensity_veto_threshold = -0.5  # dragon08-h4-hybrid-talib-volume-off/config.yaml
news_context.sentiment_direction_threshold = 0.15  # dragon08-h4-hybrid-talib-volume-off/config.yaml
pattern.bearish_patterns = ["bearish_engulfing", "evening_star", "shooting_star"]  # dragon08-h4-hybrid-talib-volume-off/config.yaml
pattern.bullish_patterns = ["bullish_engulfing", "hammer", "morning_star"]  # dragon08-h4-hybrid-talib-volume-off/config.yaml
pattern.detector = "talib"  # dragon08-h4-hybrid-talib-volume-off/config.yaml
perception_source = "ema"  # dragon08-h4-hybrid-talib-volume-off/config.yaml
price_features.atr_period = 14  # dragon08-h4-hybrid-talib-volume-off/config.yaml
price_features.bar_minutes = 240  # dragon08-h4-hybrid-talib-volume-off/config.yaml
price_features.ema_fast = 3  # dragon08-h4-hybrid-talib-volume-off/config.yaml
price_features.ema_higher_tf = 60  # dragon08-h4-hybrid-talib-volume-off/config.yaml
price_features.ema_slow = 8  # dragon08-h4-hybrid-talib-volume-off/config.yaml
price_features.macd_fast = 12  # dragon08-h4-hybrid-talib-volume-off/config.yaml
price_features.macd_signal = 9  # dragon08-h4-hybrid-talib-volume-off/config.yaml
price_features.macd_slow = 26  # dragon08-h4-hybrid-talib-volume-off/config.yaml
price_features.rsi_period = 14  # dragon08-h4-hybrid-talib-volume-off/config.yaml
price_features.swing_lookback_bars = 60  # dragon08-h4-hybrid-talib-volume-off/config.yaml
risk_guard.daily_drawdown_limit = -0.05  # dragon08-h4-hybrid-talib-volume-off/config.yaml
risk_guard.max_concurrent_trades_per_account = 2  # dragon08-h4-hybrid-talib-volume-off/config.yaml
risk_guard.max_leverage = 30  # dragon08-h4-hybrid-talib-volume-off/config.yaml
risk_guard.portfolio_at_risk_cap = 0.18  # dragon08-h4-hybrid-talib-volume-off/config.yaml
risk_guard.weekly_drawdown_limit = -0.15  # dragon08-h4-hybrid-talib-volume-off/config.yaml
schema_version = 2  # q10-hybrid-vol-off/config.yaml
```

## m15-candle-vol-on (job `2026-09-28-tf-sweep`)

Variant YAML:
```yaml
# m15-candle-vol-on: Dragon08 plan and TA-Lib candles on 15-minute complete bars; label horizon = one bar.
# Timeframe sweep 2026-09-28 (exploratory; same splits and rules as the H4 tuning sweep).
schema_version: 2
extends: dragon08-h4-talib-volume-on

price_features:
  bar_minutes: 15
meta_learner:
  label_horizon_minutes: 15
```

Resolved parameters:
```
capital_mgmt.assumed_leverage = 30.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.atr_multiplier = 2.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.lot_notional_units = 100000.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_reward_risk = 2.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_stop_factor = 1.2  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_stop_pips = 5.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.pip_value_per_lot = 10.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.risk_per_trade = 0.03  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_distance_source = "swing"  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_loss_pips = 20.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_loss_shrink = 0.5  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.targets = [{"at_level_ratio": 4.0, "close_fraction": 0.5}, {"at_level_ratio": 6.0, "close_fraction": 0.5}]  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.trail_stops = [{"at_level_ratio": 2.0, "to_level_ratio": 0.1}]  # dragon08-h4-talib-volume-on/config.yaml
execution.broker_stop_level_pips = 0.0  # dragon08-h4-talib-volume-on/config.yaml
execution.close_on_veto = false  # dragon08-h4-talib-volume-on/config.yaml
execution.commission_per_lot = 0.0  # dragon08-h4-talib-volume-on/config.yaml
execution.min_hold_bars = 0  # dragon08-h4-talib-volume-on/config.yaml
execution.spread_pips = 1.0  # dragon08-h4-talib-volume-on/config.yaml
filters = ["f1_trend", "f2_indicator", "f3_pattern", "volume_strength", "f5_risk_guard", "f6_capital_mgmt", "f7_meta_learner"]  # dragon08-h4-talib-volume-on/config.yaml
indicator.macd_hist_threshold = 0.0  # dragon08-h4-talib-volume-on/config.yaml
indicator.rsi_midline = 50.0  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.families = ["trend", "indicator", "pattern"]  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.label_horizon_minutes = 15  # m15-candle-vol-on/config.yaml
meta_learner.regime_gate = false  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.theta_high = 0.55  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.theta_low = 0.45  # dragon08-h4-talib-volume-on/config.yaml
pattern.bearish_patterns = ["bearish_engulfing", "evening_star", "shooting_star"]  # dragon08-h4-talib-volume-on/config.yaml
pattern.bullish_patterns = ["bullish_engulfing", "hammer", "morning_star"]  # dragon08-h4-talib-volume-on/config.yaml
pattern.detector = "talib"  # dragon08-h4-talib-volume-on/config.yaml
perception_source = "ema"  # dragon08-h4-talib-volume-on/config.yaml
price_features.atr_period = 14  # dragon08-h4-talib-volume-on/config.yaml
price_features.bar_minutes = 15  # m15-candle-vol-on/config.yaml
price_features.ema_fast = 3  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_higher_tf = 60  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_slow = 8  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_fast = 12  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_signal = 9  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_slow = 26  # dragon08-h4-talib-volume-on/config.yaml
price_features.rsi_period = 14  # dragon08-h4-talib-volume-on/config.yaml
price_features.swing_lookback_bars = 60  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.daily_drawdown_limit = -0.05  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.max_concurrent_trades_per_account = 2  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.max_leverage = 30  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.portfolio_at_risk_cap = 0.18  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.weekly_drawdown_limit = -0.15  # dragon08-h4-talib-volume-on/config.yaml
schema_version = 2  # m15-candle-vol-on/config.yaml
volume_strength.lookback = 20  # dragon08-h4-talib-volume-on/config.yaml
volume_strength.min_relative_activity = 1.0  # dragon08-h4-talib-volume-on/config.yaml
```

## m15-candle-vol-off (job `2026-09-28-tf-sweep`)

Variant YAML:
```yaml
# m15-candle-vol-off: Dragon08 plan and TA-Lib candles on 15-minute complete bars; label horizon = one bar.
# Timeframe sweep 2026-09-28 (exploratory; same splits and rules as the H4 tuning sweep).
schema_version: 2
extends: dragon08-h4-talib-volume-off

price_features:
  bar_minutes: 15
meta_learner:
  label_horizon_minutes: 15
```

Resolved parameters:
```
capital_mgmt.assumed_leverage = 30.0  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.atr_multiplier = 2.0  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.lot_notional_units = 100000.0  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.min_reward_risk = 2.0  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.min_stop_factor = 1.2  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.min_stop_pips = 5.0  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.pip_value_per_lot = 10.0  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.risk_per_trade = 0.03  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.stop_distance_source = "swing"  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.stop_loss_pips = 20.0  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.stop_loss_shrink = 0.5  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.targets = [{"at_level_ratio": 4.0, "close_fraction": 0.5}, {"at_level_ratio": 6.0, "close_fraction": 0.5}]  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.trail_stops = [{"at_level_ratio": 2.0, "to_level_ratio": 0.1}]  # dragon08-h4-talib-volume-off/config.yaml
execution.broker_stop_level_pips = 0.0  # dragon08-h4-talib-volume-off/config.yaml
execution.close_on_veto = false  # dragon08-h4-talib-volume-off/config.yaml
execution.commission_per_lot = 0.0  # dragon08-h4-talib-volume-off/config.yaml
execution.min_hold_bars = 0  # dragon08-h4-talib-volume-off/config.yaml
execution.spread_pips = 1.0  # dragon08-h4-talib-volume-off/config.yaml
filters = ["f1_trend", "f2_indicator", "f3_pattern", "f5_risk_guard", "f6_capital_mgmt", "f7_meta_learner"]  # dragon08-h4-talib-volume-off/config.yaml
indicator.macd_hist_threshold = 0.0  # dragon08-h4-talib-volume-off/config.yaml
indicator.rsi_midline = 50.0  # dragon08-h4-talib-volume-off/config.yaml
meta_learner.families = ["trend", "indicator", "pattern"]  # dragon08-h4-talib-volume-off/config.yaml
meta_learner.label_horizon_minutes = 15  # m15-candle-vol-off/config.yaml
meta_learner.regime_gate = false  # dragon08-h4-talib-volume-off/config.yaml
meta_learner.theta_high = 0.55  # dragon08-h4-talib-volume-off/config.yaml
meta_learner.theta_low = 0.45  # dragon08-h4-talib-volume-off/config.yaml
pattern.bearish_patterns = ["bearish_engulfing", "evening_star", "shooting_star"]  # dragon08-h4-talib-volume-off/config.yaml
pattern.bullish_patterns = ["bullish_engulfing", "hammer", "morning_star"]  # dragon08-h4-talib-volume-off/config.yaml
pattern.detector = "talib"  # dragon08-h4-talib-volume-off/config.yaml
perception_source = "ema"  # dragon08-h4-talib-volume-off/config.yaml
price_features.atr_period = 14  # dragon08-h4-talib-volume-off/config.yaml
price_features.bar_minutes = 15  # m15-candle-vol-off/config.yaml
price_features.ema_fast = 3  # dragon08-h4-talib-volume-off/config.yaml
price_features.ema_higher_tf = 60  # dragon08-h4-talib-volume-off/config.yaml
price_features.ema_slow = 8  # dragon08-h4-talib-volume-off/config.yaml
price_features.macd_fast = 12  # dragon08-h4-talib-volume-off/config.yaml
price_features.macd_signal = 9  # dragon08-h4-talib-volume-off/config.yaml
price_features.macd_slow = 26  # dragon08-h4-talib-volume-off/config.yaml
price_features.rsi_period = 14  # dragon08-h4-talib-volume-off/config.yaml
price_features.swing_lookback_bars = 60  # dragon08-h4-talib-volume-off/config.yaml
risk_guard.daily_drawdown_limit = -0.05  # dragon08-h4-talib-volume-off/config.yaml
risk_guard.max_concurrent_trades_per_account = 2  # dragon08-h4-talib-volume-off/config.yaml
risk_guard.max_leverage = 30  # dragon08-h4-talib-volume-off/config.yaml
risk_guard.portfolio_at_risk_cap = 0.18  # dragon08-h4-talib-volume-off/config.yaml
risk_guard.weekly_drawdown_limit = -0.15  # dragon08-h4-talib-volume-off/config.yaml
schema_version = 2  # m15-candle-vol-off/config.yaml
```

## m15-hybrid-candle-vol-on (job `2026-09-28-tf-sweep`)

Variant YAML:
```yaml
# m15-hybrid-candle-vol-on: Dragon08 plan and TA-Lib candles on 15-minute complete bars; label horizon = one bar.
# Timeframe sweep 2026-09-28 (exploratory; same splits and rules as the H4 tuning sweep).
schema_version: 2
extends: dragon08-h4-hybrid-talib-volume-on

price_features:
  bar_minutes: 15
meta_learner:
  label_horizon_minutes: 15
```

Resolved parameters:
```
capital_mgmt.assumed_leverage = 30.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.atr_multiplier = 2.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.lot_notional_units = 100000.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.min_reward_risk = 2.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.min_stop_factor = 1.2  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.min_stop_pips = 5.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.pip_value_per_lot = 10.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.risk_per_trade = 0.03  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.stop_distance_source = "swing"  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.stop_loss_pips = 20.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.stop_loss_shrink = 0.5  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.targets = [{"at_level_ratio": 4.0, "close_fraction": 0.5}, {"at_level_ratio": 6.0, "close_fraction": 0.5}]  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.trail_stops = [{"at_level_ratio": 2.0, "to_level_ratio": 0.1}]  # dragon08-h4-hybrid-talib-volume-on/config.yaml
execution.broker_stop_level_pips = 0.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
execution.close_on_veto = false  # dragon08-h4-hybrid-talib-volume-on/config.yaml
execution.commission_per_lot = 0.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
execution.min_hold_bars = 0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
execution.spread_pips = 1.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
filters = ["f1_trend", "f2_indicator", "f3_pattern", "f4_news_context", "volume_strength", "f5_risk_guard", "f6_capital_mgmt", "f7_meta_learner"]  # dragon08-h4-hybrid-talib-volume-on/config.yaml
indicator.macd_hist_threshold = 0.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
indicator.rsi_midline = 50.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
meta_learner.families = ["trend", "indicator", "pattern", "news"]  # dragon08-h4-hybrid-talib-volume-on/config.yaml
meta_learner.label_horizon_minutes = 15  # m15-hybrid-candle-vol-on/config.yaml
meta_learner.regime_gate = false  # dragon08-h4-hybrid-talib-volume-on/config.yaml
meta_learner.theta_high = 0.55  # dragon08-h4-hybrid-talib-volume-on/config.yaml
meta_learner.theta_low = 0.45  # dragon08-h4-hybrid-talib-volume-on/config.yaml
news_context.event_intensity_veto_threshold = -0.5  # dragon08-h4-hybrid-talib-volume-on/config.yaml
news_context.sentiment_direction_threshold = 0.15  # dragon08-h4-hybrid-talib-volume-on/config.yaml
pattern.bearish_patterns = ["bearish_engulfing", "evening_star", "shooting_star"]  # dragon08-h4-hybrid-talib-volume-on/config.yaml
pattern.bullish_patterns = ["bullish_engulfing", "hammer", "morning_star"]  # dragon08-h4-hybrid-talib-volume-on/config.yaml
pattern.detector = "talib"  # dragon08-h4-hybrid-talib-volume-on/config.yaml
perception_source = "ema"  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.atr_period = 14  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.bar_minutes = 15  # m15-hybrid-candle-vol-on/config.yaml
price_features.ema_fast = 3  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.ema_higher_tf = 60  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.ema_slow = 8  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.macd_fast = 12  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.macd_signal = 9  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.macd_slow = 26  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.rsi_period = 14  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.swing_lookback_bars = 60  # dragon08-h4-hybrid-talib-volume-on/config.yaml
risk_guard.daily_drawdown_limit = -0.05  # dragon08-h4-hybrid-talib-volume-on/config.yaml
risk_guard.max_concurrent_trades_per_account = 2  # dragon08-h4-hybrid-talib-volume-on/config.yaml
risk_guard.max_leverage = 30  # dragon08-h4-hybrid-talib-volume-on/config.yaml
risk_guard.portfolio_at_risk_cap = 0.18  # dragon08-h4-hybrid-talib-volume-on/config.yaml
risk_guard.weekly_drawdown_limit = -0.15  # dragon08-h4-hybrid-talib-volume-on/config.yaml
schema_version = 2  # m15-hybrid-candle-vol-on/config.yaml
volume_strength.lookback = 20  # dragon08-h4-hybrid-talib-volume-on/config.yaml
volume_strength.min_relative_activity = 1.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
```

## h1-candle-vol-on (job `2026-09-28-tf-sweep`)

Variant YAML:
```yaml
# h1-candle-vol-on: Dragon08 plan and TA-Lib candles on 60-minute complete bars; label horizon = one bar.
# Timeframe sweep 2026-09-28 (exploratory; same splits and rules as the H4 tuning sweep).
schema_version: 2
extends: dragon08-h4-talib-volume-on

price_features:
  bar_minutes: 60
meta_learner:
  label_horizon_minutes: 60
```

Resolved parameters:
```
capital_mgmt.assumed_leverage = 30.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.atr_multiplier = 2.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.lot_notional_units = 100000.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_reward_risk = 2.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_stop_factor = 1.2  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_stop_pips = 5.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.pip_value_per_lot = 10.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.risk_per_trade = 0.03  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_distance_source = "swing"  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_loss_pips = 20.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_loss_shrink = 0.5  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.targets = [{"at_level_ratio": 4.0, "close_fraction": 0.5}, {"at_level_ratio": 6.0, "close_fraction": 0.5}]  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.trail_stops = [{"at_level_ratio": 2.0, "to_level_ratio": 0.1}]  # dragon08-h4-talib-volume-on/config.yaml
execution.broker_stop_level_pips = 0.0  # dragon08-h4-talib-volume-on/config.yaml
execution.close_on_veto = false  # dragon08-h4-talib-volume-on/config.yaml
execution.commission_per_lot = 0.0  # dragon08-h4-talib-volume-on/config.yaml
execution.min_hold_bars = 0  # dragon08-h4-talib-volume-on/config.yaml
execution.spread_pips = 1.0  # dragon08-h4-talib-volume-on/config.yaml
filters = ["f1_trend", "f2_indicator", "f3_pattern", "volume_strength", "f5_risk_guard", "f6_capital_mgmt", "f7_meta_learner"]  # dragon08-h4-talib-volume-on/config.yaml
indicator.macd_hist_threshold = 0.0  # dragon08-h4-talib-volume-on/config.yaml
indicator.rsi_midline = 50.0  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.families = ["trend", "indicator", "pattern"]  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.label_horizon_minutes = 60  # h1-candle-vol-on/config.yaml
meta_learner.regime_gate = false  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.theta_high = 0.55  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.theta_low = 0.45  # dragon08-h4-talib-volume-on/config.yaml
pattern.bearish_patterns = ["bearish_engulfing", "evening_star", "shooting_star"]  # dragon08-h4-talib-volume-on/config.yaml
pattern.bullish_patterns = ["bullish_engulfing", "hammer", "morning_star"]  # dragon08-h4-talib-volume-on/config.yaml
pattern.detector = "talib"  # dragon08-h4-talib-volume-on/config.yaml
perception_source = "ema"  # dragon08-h4-talib-volume-on/config.yaml
price_features.atr_period = 14  # dragon08-h4-talib-volume-on/config.yaml
price_features.bar_minutes = 60  # h1-candle-vol-on/config.yaml
price_features.ema_fast = 3  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_higher_tf = 60  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_slow = 8  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_fast = 12  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_signal = 9  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_slow = 26  # dragon08-h4-talib-volume-on/config.yaml
price_features.rsi_period = 14  # dragon08-h4-talib-volume-on/config.yaml
price_features.swing_lookback_bars = 60  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.daily_drawdown_limit = -0.05  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.max_concurrent_trades_per_account = 2  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.max_leverage = 30  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.portfolio_at_risk_cap = 0.18  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.weekly_drawdown_limit = -0.15  # dragon08-h4-talib-volume-on/config.yaml
schema_version = 2  # h1-candle-vol-on/config.yaml
volume_strength.lookback = 20  # dragon08-h4-talib-volume-on/config.yaml
volume_strength.min_relative_activity = 1.0  # dragon08-h4-talib-volume-on/config.yaml
```

## h1-candle-vol-off (job `2026-09-28-tf-sweep`)

Variant YAML:
```yaml
# h1-candle-vol-off: Dragon08 plan and TA-Lib candles on 60-minute complete bars; label horizon = one bar.
# Timeframe sweep 2026-09-28 (exploratory; same splits and rules as the H4 tuning sweep).
schema_version: 2
extends: dragon08-h4-talib-volume-off

price_features:
  bar_minutes: 60
meta_learner:
  label_horizon_minutes: 60
```

Resolved parameters:
```
capital_mgmt.assumed_leverage = 30.0  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.atr_multiplier = 2.0  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.lot_notional_units = 100000.0  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.min_reward_risk = 2.0  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.min_stop_factor = 1.2  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.min_stop_pips = 5.0  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.pip_value_per_lot = 10.0  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.risk_per_trade = 0.03  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.stop_distance_source = "swing"  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.stop_loss_pips = 20.0  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.stop_loss_shrink = 0.5  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.targets = [{"at_level_ratio": 4.0, "close_fraction": 0.5}, {"at_level_ratio": 6.0, "close_fraction": 0.5}]  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.trail_stops = [{"at_level_ratio": 2.0, "to_level_ratio": 0.1}]  # dragon08-h4-talib-volume-off/config.yaml
execution.broker_stop_level_pips = 0.0  # dragon08-h4-talib-volume-off/config.yaml
execution.close_on_veto = false  # dragon08-h4-talib-volume-off/config.yaml
execution.commission_per_lot = 0.0  # dragon08-h4-talib-volume-off/config.yaml
execution.min_hold_bars = 0  # dragon08-h4-talib-volume-off/config.yaml
execution.spread_pips = 1.0  # dragon08-h4-talib-volume-off/config.yaml
filters = ["f1_trend", "f2_indicator", "f3_pattern", "f5_risk_guard", "f6_capital_mgmt", "f7_meta_learner"]  # dragon08-h4-talib-volume-off/config.yaml
indicator.macd_hist_threshold = 0.0  # dragon08-h4-talib-volume-off/config.yaml
indicator.rsi_midline = 50.0  # dragon08-h4-talib-volume-off/config.yaml
meta_learner.families = ["trend", "indicator", "pattern"]  # dragon08-h4-talib-volume-off/config.yaml
meta_learner.label_horizon_minutes = 60  # h1-candle-vol-off/config.yaml
meta_learner.regime_gate = false  # dragon08-h4-talib-volume-off/config.yaml
meta_learner.theta_high = 0.55  # dragon08-h4-talib-volume-off/config.yaml
meta_learner.theta_low = 0.45  # dragon08-h4-talib-volume-off/config.yaml
pattern.bearish_patterns = ["bearish_engulfing", "evening_star", "shooting_star"]  # dragon08-h4-talib-volume-off/config.yaml
pattern.bullish_patterns = ["bullish_engulfing", "hammer", "morning_star"]  # dragon08-h4-talib-volume-off/config.yaml
pattern.detector = "talib"  # dragon08-h4-talib-volume-off/config.yaml
perception_source = "ema"  # dragon08-h4-talib-volume-off/config.yaml
price_features.atr_period = 14  # dragon08-h4-talib-volume-off/config.yaml
price_features.bar_minutes = 60  # h1-candle-vol-off/config.yaml
price_features.ema_fast = 3  # dragon08-h4-talib-volume-off/config.yaml
price_features.ema_higher_tf = 60  # dragon08-h4-talib-volume-off/config.yaml
price_features.ema_slow = 8  # dragon08-h4-talib-volume-off/config.yaml
price_features.macd_fast = 12  # dragon08-h4-talib-volume-off/config.yaml
price_features.macd_signal = 9  # dragon08-h4-talib-volume-off/config.yaml
price_features.macd_slow = 26  # dragon08-h4-talib-volume-off/config.yaml
price_features.rsi_period = 14  # dragon08-h4-talib-volume-off/config.yaml
price_features.swing_lookback_bars = 60  # dragon08-h4-talib-volume-off/config.yaml
risk_guard.daily_drawdown_limit = -0.05  # dragon08-h4-talib-volume-off/config.yaml
risk_guard.max_concurrent_trades_per_account = 2  # dragon08-h4-talib-volume-off/config.yaml
risk_guard.max_leverage = 30  # dragon08-h4-talib-volume-off/config.yaml
risk_guard.portfolio_at_risk_cap = 0.18  # dragon08-h4-talib-volume-off/config.yaml
risk_guard.weekly_drawdown_limit = -0.15  # dragon08-h4-talib-volume-off/config.yaml
schema_version = 2  # h1-candle-vol-off/config.yaml
```

## h1-hybrid-candle-vol-on (job `2026-09-28-tf-sweep`)

Variant YAML:
```yaml
# h1-hybrid-candle-vol-on: Dragon08 plan and TA-Lib candles on 60-minute complete bars; label horizon = one bar.
# Timeframe sweep 2026-09-28 (exploratory; same splits and rules as the H4 tuning sweep).
schema_version: 2
extends: dragon08-h4-hybrid-talib-volume-on

price_features:
  bar_minutes: 60
meta_learner:
  label_horizon_minutes: 60
```

Resolved parameters:
```
capital_mgmt.assumed_leverage = 30.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.atr_multiplier = 2.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.lot_notional_units = 100000.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.min_reward_risk = 2.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.min_stop_factor = 1.2  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.min_stop_pips = 5.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.pip_value_per_lot = 10.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.risk_per_trade = 0.03  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.stop_distance_source = "swing"  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.stop_loss_pips = 20.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.stop_loss_shrink = 0.5  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.targets = [{"at_level_ratio": 4.0, "close_fraction": 0.5}, {"at_level_ratio": 6.0, "close_fraction": 0.5}]  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.trail_stops = [{"at_level_ratio": 2.0, "to_level_ratio": 0.1}]  # dragon08-h4-hybrid-talib-volume-on/config.yaml
execution.broker_stop_level_pips = 0.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
execution.close_on_veto = false  # dragon08-h4-hybrid-talib-volume-on/config.yaml
execution.commission_per_lot = 0.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
execution.min_hold_bars = 0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
execution.spread_pips = 1.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
filters = ["f1_trend", "f2_indicator", "f3_pattern", "f4_news_context", "volume_strength", "f5_risk_guard", "f6_capital_mgmt", "f7_meta_learner"]  # dragon08-h4-hybrid-talib-volume-on/config.yaml
indicator.macd_hist_threshold = 0.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
indicator.rsi_midline = 50.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
meta_learner.families = ["trend", "indicator", "pattern", "news"]  # dragon08-h4-hybrid-talib-volume-on/config.yaml
meta_learner.label_horizon_minutes = 60  # h1-hybrid-candle-vol-on/config.yaml
meta_learner.regime_gate = false  # dragon08-h4-hybrid-talib-volume-on/config.yaml
meta_learner.theta_high = 0.55  # dragon08-h4-hybrid-talib-volume-on/config.yaml
meta_learner.theta_low = 0.45  # dragon08-h4-hybrid-talib-volume-on/config.yaml
news_context.event_intensity_veto_threshold = -0.5  # dragon08-h4-hybrid-talib-volume-on/config.yaml
news_context.sentiment_direction_threshold = 0.15  # dragon08-h4-hybrid-talib-volume-on/config.yaml
pattern.bearish_patterns = ["bearish_engulfing", "evening_star", "shooting_star"]  # dragon08-h4-hybrid-talib-volume-on/config.yaml
pattern.bullish_patterns = ["bullish_engulfing", "hammer", "morning_star"]  # dragon08-h4-hybrid-talib-volume-on/config.yaml
pattern.detector = "talib"  # dragon08-h4-hybrid-talib-volume-on/config.yaml
perception_source = "ema"  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.atr_period = 14  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.bar_minutes = 60  # h1-hybrid-candle-vol-on/config.yaml
price_features.ema_fast = 3  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.ema_higher_tf = 60  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.ema_slow = 8  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.macd_fast = 12  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.macd_signal = 9  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.macd_slow = 26  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.rsi_period = 14  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.swing_lookback_bars = 60  # dragon08-h4-hybrid-talib-volume-on/config.yaml
risk_guard.daily_drawdown_limit = -0.05  # dragon08-h4-hybrid-talib-volume-on/config.yaml
risk_guard.max_concurrent_trades_per_account = 2  # dragon08-h4-hybrid-talib-volume-on/config.yaml
risk_guard.max_leverage = 30  # dragon08-h4-hybrid-talib-volume-on/config.yaml
risk_guard.portfolio_at_risk_cap = 0.18  # dragon08-h4-hybrid-talib-volume-on/config.yaml
risk_guard.weekly_drawdown_limit = -0.15  # dragon08-h4-hybrid-talib-volume-on/config.yaml
schema_version = 2  # h1-hybrid-candle-vol-on/config.yaml
volume_strength.lookback = 20  # dragon08-h4-hybrid-talib-volume-on/config.yaml
volume_strength.min_relative_activity = 1.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
```

## h2-candle-vol-on (job `2026-09-28-tf-sweep`)

Variant YAML:
```yaml
# h2-candle-vol-on: Dragon08 plan and TA-Lib candles on 120-minute complete bars; label horizon = one bar.
# Timeframe sweep 2026-09-28 (exploratory; same splits and rules as the H4 tuning sweep).
schema_version: 2
extends: dragon08-h4-talib-volume-on

price_features:
  bar_minutes: 120
meta_learner:
  label_horizon_minutes: 120
```

Resolved parameters:
```
capital_mgmt.assumed_leverage = 30.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.atr_multiplier = 2.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.lot_notional_units = 100000.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_reward_risk = 2.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_stop_factor = 1.2  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_stop_pips = 5.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.pip_value_per_lot = 10.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.risk_per_trade = 0.03  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_distance_source = "swing"  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_loss_pips = 20.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_loss_shrink = 0.5  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.targets = [{"at_level_ratio": 4.0, "close_fraction": 0.5}, {"at_level_ratio": 6.0, "close_fraction": 0.5}]  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.trail_stops = [{"at_level_ratio": 2.0, "to_level_ratio": 0.1}]  # dragon08-h4-talib-volume-on/config.yaml
execution.broker_stop_level_pips = 0.0  # dragon08-h4-talib-volume-on/config.yaml
execution.close_on_veto = false  # dragon08-h4-talib-volume-on/config.yaml
execution.commission_per_lot = 0.0  # dragon08-h4-talib-volume-on/config.yaml
execution.min_hold_bars = 0  # dragon08-h4-talib-volume-on/config.yaml
execution.spread_pips = 1.0  # dragon08-h4-talib-volume-on/config.yaml
filters = ["f1_trend", "f2_indicator", "f3_pattern", "volume_strength", "f5_risk_guard", "f6_capital_mgmt", "f7_meta_learner"]  # dragon08-h4-talib-volume-on/config.yaml
indicator.macd_hist_threshold = 0.0  # dragon08-h4-talib-volume-on/config.yaml
indicator.rsi_midline = 50.0  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.families = ["trend", "indicator", "pattern"]  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.label_horizon_minutes = 120  # h2-candle-vol-on/config.yaml
meta_learner.regime_gate = false  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.theta_high = 0.55  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.theta_low = 0.45  # dragon08-h4-talib-volume-on/config.yaml
pattern.bearish_patterns = ["bearish_engulfing", "evening_star", "shooting_star"]  # dragon08-h4-talib-volume-on/config.yaml
pattern.bullish_patterns = ["bullish_engulfing", "hammer", "morning_star"]  # dragon08-h4-talib-volume-on/config.yaml
pattern.detector = "talib"  # dragon08-h4-talib-volume-on/config.yaml
perception_source = "ema"  # dragon08-h4-talib-volume-on/config.yaml
price_features.atr_period = 14  # dragon08-h4-talib-volume-on/config.yaml
price_features.bar_minutes = 120  # h2-candle-vol-on/config.yaml
price_features.ema_fast = 3  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_higher_tf = 60  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_slow = 8  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_fast = 12  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_signal = 9  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_slow = 26  # dragon08-h4-talib-volume-on/config.yaml
price_features.rsi_period = 14  # dragon08-h4-talib-volume-on/config.yaml
price_features.swing_lookback_bars = 60  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.daily_drawdown_limit = -0.05  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.max_concurrent_trades_per_account = 2  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.max_leverage = 30  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.portfolio_at_risk_cap = 0.18  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.weekly_drawdown_limit = -0.15  # dragon08-h4-talib-volume-on/config.yaml
schema_version = 2  # h2-candle-vol-on/config.yaml
volume_strength.lookback = 20  # dragon08-h4-talib-volume-on/config.yaml
volume_strength.min_relative_activity = 1.0  # dragon08-h4-talib-volume-on/config.yaml
```

## h2-candle-vol-off (job `2026-09-28-tf-sweep`)

Variant YAML:
```yaml
# h2-candle-vol-off: Dragon08 plan and TA-Lib candles on 120-minute complete bars; label horizon = one bar.
# Timeframe sweep 2026-09-28 (exploratory; same splits and rules as the H4 tuning sweep).
schema_version: 2
extends: dragon08-h4-talib-volume-off

price_features:
  bar_minutes: 120
meta_learner:
  label_horizon_minutes: 120
```

Resolved parameters:
```
capital_mgmt.assumed_leverage = 30.0  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.atr_multiplier = 2.0  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.lot_notional_units = 100000.0  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.min_reward_risk = 2.0  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.min_stop_factor = 1.2  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.min_stop_pips = 5.0  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.pip_value_per_lot = 10.0  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.risk_per_trade = 0.03  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.stop_distance_source = "swing"  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.stop_loss_pips = 20.0  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.stop_loss_shrink = 0.5  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.targets = [{"at_level_ratio": 4.0, "close_fraction": 0.5}, {"at_level_ratio": 6.0, "close_fraction": 0.5}]  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.trail_stops = [{"at_level_ratio": 2.0, "to_level_ratio": 0.1}]  # dragon08-h4-talib-volume-off/config.yaml
execution.broker_stop_level_pips = 0.0  # dragon08-h4-talib-volume-off/config.yaml
execution.close_on_veto = false  # dragon08-h4-talib-volume-off/config.yaml
execution.commission_per_lot = 0.0  # dragon08-h4-talib-volume-off/config.yaml
execution.min_hold_bars = 0  # dragon08-h4-talib-volume-off/config.yaml
execution.spread_pips = 1.0  # dragon08-h4-talib-volume-off/config.yaml
filters = ["f1_trend", "f2_indicator", "f3_pattern", "f5_risk_guard", "f6_capital_mgmt", "f7_meta_learner"]  # dragon08-h4-talib-volume-off/config.yaml
indicator.macd_hist_threshold = 0.0  # dragon08-h4-talib-volume-off/config.yaml
indicator.rsi_midline = 50.0  # dragon08-h4-talib-volume-off/config.yaml
meta_learner.families = ["trend", "indicator", "pattern"]  # dragon08-h4-talib-volume-off/config.yaml
meta_learner.label_horizon_minutes = 120  # h2-candle-vol-off/config.yaml
meta_learner.regime_gate = false  # dragon08-h4-talib-volume-off/config.yaml
meta_learner.theta_high = 0.55  # dragon08-h4-talib-volume-off/config.yaml
meta_learner.theta_low = 0.45  # dragon08-h4-talib-volume-off/config.yaml
pattern.bearish_patterns = ["bearish_engulfing", "evening_star", "shooting_star"]  # dragon08-h4-talib-volume-off/config.yaml
pattern.bullish_patterns = ["bullish_engulfing", "hammer", "morning_star"]  # dragon08-h4-talib-volume-off/config.yaml
pattern.detector = "talib"  # dragon08-h4-talib-volume-off/config.yaml
perception_source = "ema"  # dragon08-h4-talib-volume-off/config.yaml
price_features.atr_period = 14  # dragon08-h4-talib-volume-off/config.yaml
price_features.bar_minutes = 120  # h2-candle-vol-off/config.yaml
price_features.ema_fast = 3  # dragon08-h4-talib-volume-off/config.yaml
price_features.ema_higher_tf = 60  # dragon08-h4-talib-volume-off/config.yaml
price_features.ema_slow = 8  # dragon08-h4-talib-volume-off/config.yaml
price_features.macd_fast = 12  # dragon08-h4-talib-volume-off/config.yaml
price_features.macd_signal = 9  # dragon08-h4-talib-volume-off/config.yaml
price_features.macd_slow = 26  # dragon08-h4-talib-volume-off/config.yaml
price_features.rsi_period = 14  # dragon08-h4-talib-volume-off/config.yaml
price_features.swing_lookback_bars = 60  # dragon08-h4-talib-volume-off/config.yaml
risk_guard.daily_drawdown_limit = -0.05  # dragon08-h4-talib-volume-off/config.yaml
risk_guard.max_concurrent_trades_per_account = 2  # dragon08-h4-talib-volume-off/config.yaml
risk_guard.max_leverage = 30  # dragon08-h4-talib-volume-off/config.yaml
risk_guard.portfolio_at_risk_cap = 0.18  # dragon08-h4-talib-volume-off/config.yaml
risk_guard.weekly_drawdown_limit = -0.15  # dragon08-h4-talib-volume-off/config.yaml
schema_version = 2  # h2-candle-vol-off/config.yaml
```

## h2-hybrid-candle-vol-on (job `2026-09-28-tf-sweep`)

Variant YAML:
```yaml
# h2-hybrid-candle-vol-on: Dragon08 plan and TA-Lib candles on 120-minute complete bars; label horizon = one bar.
# Timeframe sweep 2026-09-28 (exploratory; same splits and rules as the H4 tuning sweep).
schema_version: 2
extends: dragon08-h4-hybrid-talib-volume-on

price_features:
  bar_minutes: 120
meta_learner:
  label_horizon_minutes: 120
```

Resolved parameters:
```
capital_mgmt.assumed_leverage = 30.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.atr_multiplier = 2.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.lot_notional_units = 100000.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.min_reward_risk = 2.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.min_stop_factor = 1.2  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.min_stop_pips = 5.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.pip_value_per_lot = 10.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.risk_per_trade = 0.03  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.stop_distance_source = "swing"  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.stop_loss_pips = 20.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.stop_loss_shrink = 0.5  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.targets = [{"at_level_ratio": 4.0, "close_fraction": 0.5}, {"at_level_ratio": 6.0, "close_fraction": 0.5}]  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.trail_stops = [{"at_level_ratio": 2.0, "to_level_ratio": 0.1}]  # dragon08-h4-hybrid-talib-volume-on/config.yaml
execution.broker_stop_level_pips = 0.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
execution.close_on_veto = false  # dragon08-h4-hybrid-talib-volume-on/config.yaml
execution.commission_per_lot = 0.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
execution.min_hold_bars = 0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
execution.spread_pips = 1.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
filters = ["f1_trend", "f2_indicator", "f3_pattern", "f4_news_context", "volume_strength", "f5_risk_guard", "f6_capital_mgmt", "f7_meta_learner"]  # dragon08-h4-hybrid-talib-volume-on/config.yaml
indicator.macd_hist_threshold = 0.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
indicator.rsi_midline = 50.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
meta_learner.families = ["trend", "indicator", "pattern", "news"]  # dragon08-h4-hybrid-talib-volume-on/config.yaml
meta_learner.label_horizon_minutes = 120  # h2-hybrid-candle-vol-on/config.yaml
meta_learner.regime_gate = false  # dragon08-h4-hybrid-talib-volume-on/config.yaml
meta_learner.theta_high = 0.55  # dragon08-h4-hybrid-talib-volume-on/config.yaml
meta_learner.theta_low = 0.45  # dragon08-h4-hybrid-talib-volume-on/config.yaml
news_context.event_intensity_veto_threshold = -0.5  # dragon08-h4-hybrid-talib-volume-on/config.yaml
news_context.sentiment_direction_threshold = 0.15  # dragon08-h4-hybrid-talib-volume-on/config.yaml
pattern.bearish_patterns = ["bearish_engulfing", "evening_star", "shooting_star"]  # dragon08-h4-hybrid-talib-volume-on/config.yaml
pattern.bullish_patterns = ["bullish_engulfing", "hammer", "morning_star"]  # dragon08-h4-hybrid-talib-volume-on/config.yaml
pattern.detector = "talib"  # dragon08-h4-hybrid-talib-volume-on/config.yaml
perception_source = "ema"  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.atr_period = 14  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.bar_minutes = 120  # h2-hybrid-candle-vol-on/config.yaml
price_features.ema_fast = 3  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.ema_higher_tf = 60  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.ema_slow = 8  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.macd_fast = 12  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.macd_signal = 9  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.macd_slow = 26  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.rsi_period = 14  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.swing_lookback_bars = 60  # dragon08-h4-hybrid-talib-volume-on/config.yaml
risk_guard.daily_drawdown_limit = -0.05  # dragon08-h4-hybrid-talib-volume-on/config.yaml
risk_guard.max_concurrent_trades_per_account = 2  # dragon08-h4-hybrid-talib-volume-on/config.yaml
risk_guard.max_leverage = 30  # dragon08-h4-hybrid-talib-volume-on/config.yaml
risk_guard.portfolio_at_risk_cap = 0.18  # dragon08-h4-hybrid-talib-volume-on/config.yaml
risk_guard.weekly_drawdown_limit = -0.15  # dragon08-h4-hybrid-talib-volume-on/config.yaml
schema_version = 2  # h2-hybrid-candle-vol-on/config.yaml
volume_strength.lookback = 20  # dragon08-h4-hybrid-talib-volume-on/config.yaml
volume_strength.min_relative_activity = 1.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
```

## h1-atr-stop (job `2026-09-28-h1-tuning-sweep`)

Variant YAML:
```yaml
# h1-atr-stop: H1 base with an ATR stop (2 x ATR14 H1, floor 10 pips, no shrink).
# H1 tuning sweep 2026-09-28 (exploratory; fixed thresholds 0.55/0.45 unless stated; same splits/rules as the H4 sweeps).
schema_version: 2
extends: h1-candle-vol-on

capital_mgmt:
  stop_distance_source: atr
  atr_multiplier: 2.0
  min_stop_pips: 10.0
  stop_loss_shrink: 0.0
```

Resolved parameters:
```
capital_mgmt.assumed_leverage = 30.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.atr_multiplier = 2.0  # h1-atr-stop/config.yaml
capital_mgmt.lot_notional_units = 100000.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_reward_risk = 2.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_stop_factor = 1.2  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_stop_pips = 10.0  # h1-atr-stop/config.yaml
capital_mgmt.pip_value_per_lot = 10.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.risk_per_trade = 0.03  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_distance_source = "atr"  # h1-atr-stop/config.yaml
capital_mgmt.stop_loss_pips = 20.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_loss_shrink = 0.0  # h1-atr-stop/config.yaml
capital_mgmt.targets = [{"at_level_ratio": 4.0, "close_fraction": 0.5}, {"at_level_ratio": 6.0, "close_fraction": 0.5}]  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.trail_stops = [{"at_level_ratio": 2.0, "to_level_ratio": 0.1}]  # dragon08-h4-talib-volume-on/config.yaml
execution.broker_stop_level_pips = 0.0  # dragon08-h4-talib-volume-on/config.yaml
execution.close_on_veto = false  # dragon08-h4-talib-volume-on/config.yaml
execution.commission_per_lot = 0.0  # dragon08-h4-talib-volume-on/config.yaml
execution.min_hold_bars = 0  # dragon08-h4-talib-volume-on/config.yaml
execution.spread_pips = 1.0  # dragon08-h4-talib-volume-on/config.yaml
filters = ["f1_trend", "f2_indicator", "f3_pattern", "volume_strength", "f5_risk_guard", "f6_capital_mgmt", "f7_meta_learner"]  # dragon08-h4-talib-volume-on/config.yaml
indicator.macd_hist_threshold = 0.0  # dragon08-h4-talib-volume-on/config.yaml
indicator.rsi_midline = 50.0  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.families = ["trend", "indicator", "pattern"]  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.label_horizon_minutes = 60  # h1-candle-vol-on/config.yaml
meta_learner.regime_gate = false  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.theta_high = 0.55  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.theta_low = 0.45  # dragon08-h4-talib-volume-on/config.yaml
pattern.bearish_patterns = ["bearish_engulfing", "evening_star", "shooting_star"]  # dragon08-h4-talib-volume-on/config.yaml
pattern.bullish_patterns = ["bullish_engulfing", "hammer", "morning_star"]  # dragon08-h4-talib-volume-on/config.yaml
pattern.detector = "talib"  # dragon08-h4-talib-volume-on/config.yaml
perception_source = "ema"  # dragon08-h4-talib-volume-on/config.yaml
price_features.atr_period = 14  # dragon08-h4-talib-volume-on/config.yaml
price_features.bar_minutes = 60  # h1-candle-vol-on/config.yaml
price_features.ema_fast = 3  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_higher_tf = 60  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_slow = 8  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_fast = 12  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_signal = 9  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_slow = 26  # dragon08-h4-talib-volume-on/config.yaml
price_features.rsi_period = 14  # dragon08-h4-talib-volume-on/config.yaml
price_features.swing_lookback_bars = 60  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.daily_drawdown_limit = -0.05  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.max_concurrent_trades_per_account = 2  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.max_leverage = 30  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.portfolio_at_risk_cap = 0.18  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.weekly_drawdown_limit = -0.15  # dragon08-h4-talib-volume-on/config.yaml
schema_version = 2  # h1-atr-stop/config.yaml
volume_strength.lookback = 20  # dragon08-h4-talib-volume-on/config.yaml
volume_strength.min_relative_activity = 1.0  # dragon08-h4-talib-volume-on/config.yaml
```

## h1-atr-stop-hybrid (job `2026-09-28-h1-tuning-sweep`)

Variant YAML:
```yaml
# h1-atr-stop-hybrid: H1 hybrid with the ATR stop.
# H1 tuning sweep 2026-09-28 (exploratory; fixed thresholds 0.55/0.45 unless stated; same splits/rules as the H4 sweeps).
schema_version: 2
extends: h1-hybrid-candle-vol-on

capital_mgmt:
  stop_distance_source: atr
  atr_multiplier: 2.0
  min_stop_pips: 10.0
  stop_loss_shrink: 0.0
```

Resolved parameters:
```
capital_mgmt.assumed_leverage = 30.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.atr_multiplier = 2.0  # h1-atr-stop-hybrid/config.yaml
capital_mgmt.lot_notional_units = 100000.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.min_reward_risk = 2.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.min_stop_factor = 1.2  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.min_stop_pips = 10.0  # h1-atr-stop-hybrid/config.yaml
capital_mgmt.pip_value_per_lot = 10.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.risk_per_trade = 0.03  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.stop_distance_source = "atr"  # h1-atr-stop-hybrid/config.yaml
capital_mgmt.stop_loss_pips = 20.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.stop_loss_shrink = 0.0  # h1-atr-stop-hybrid/config.yaml
capital_mgmt.targets = [{"at_level_ratio": 4.0, "close_fraction": 0.5}, {"at_level_ratio": 6.0, "close_fraction": 0.5}]  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.trail_stops = [{"at_level_ratio": 2.0, "to_level_ratio": 0.1}]  # dragon08-h4-hybrid-talib-volume-on/config.yaml
execution.broker_stop_level_pips = 0.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
execution.close_on_veto = false  # dragon08-h4-hybrid-talib-volume-on/config.yaml
execution.commission_per_lot = 0.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
execution.min_hold_bars = 0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
execution.spread_pips = 1.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
filters = ["f1_trend", "f2_indicator", "f3_pattern", "f4_news_context", "volume_strength", "f5_risk_guard", "f6_capital_mgmt", "f7_meta_learner"]  # dragon08-h4-hybrid-talib-volume-on/config.yaml
indicator.macd_hist_threshold = 0.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
indicator.rsi_midline = 50.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
meta_learner.families = ["trend", "indicator", "pattern", "news"]  # dragon08-h4-hybrid-talib-volume-on/config.yaml
meta_learner.label_horizon_minutes = 60  # h1-hybrid-candle-vol-on/config.yaml
meta_learner.regime_gate = false  # dragon08-h4-hybrid-talib-volume-on/config.yaml
meta_learner.theta_high = 0.55  # dragon08-h4-hybrid-talib-volume-on/config.yaml
meta_learner.theta_low = 0.45  # dragon08-h4-hybrid-talib-volume-on/config.yaml
news_context.event_intensity_veto_threshold = -0.5  # dragon08-h4-hybrid-talib-volume-on/config.yaml
news_context.sentiment_direction_threshold = 0.15  # dragon08-h4-hybrid-talib-volume-on/config.yaml
pattern.bearish_patterns = ["bearish_engulfing", "evening_star", "shooting_star"]  # dragon08-h4-hybrid-talib-volume-on/config.yaml
pattern.bullish_patterns = ["bullish_engulfing", "hammer", "morning_star"]  # dragon08-h4-hybrid-talib-volume-on/config.yaml
pattern.detector = "talib"  # dragon08-h4-hybrid-talib-volume-on/config.yaml
perception_source = "ema"  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.atr_period = 14  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.bar_minutes = 60  # h1-hybrid-candle-vol-on/config.yaml
price_features.ema_fast = 3  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.ema_higher_tf = 60  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.ema_slow = 8  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.macd_fast = 12  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.macd_signal = 9  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.macd_slow = 26  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.rsi_period = 14  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.swing_lookback_bars = 60  # dragon08-h4-hybrid-talib-volume-on/config.yaml
risk_guard.daily_drawdown_limit = -0.05  # dragon08-h4-hybrid-talib-volume-on/config.yaml
risk_guard.max_concurrent_trades_per_account = 2  # dragon08-h4-hybrid-talib-volume-on/config.yaml
risk_guard.max_leverage = 30  # dragon08-h4-hybrid-talib-volume-on/config.yaml
risk_guard.portfolio_at_risk_cap = 0.18  # dragon08-h4-hybrid-talib-volume-on/config.yaml
risk_guard.weekly_drawdown_limit = -0.15  # dragon08-h4-hybrid-talib-volume-on/config.yaml
schema_version = 2  # h1-atr-stop-hybrid/config.yaml
volume_strength.lookback = 20  # dragon08-h4-hybrid-talib-volume-on/config.yaml
volume_strength.min_relative_activity = 1.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
```

## h1-hybrid-vol-off (job `2026-09-28-h1-tuning-sweep`)

Variant YAML:
```yaml
# h1-hybrid-vol-off: H1 hybrid with the activity gate off (extends the H4 hybrid volume-off template).
# H1 tuning sweep 2026-09-28 (exploratory; fixed thresholds 0.55/0.45; same splits/rules as the H4 sweeps).
schema_version: 2
extends: dragon08-h4-hybrid-talib-volume-off

price_features:
  bar_minutes: 60
meta_learner:
  label_horizon_minutes: 60
```

Resolved parameters:
```
capital_mgmt.assumed_leverage = 30.0  # dragon08-h4-hybrid-talib-volume-off/config.yaml
capital_mgmt.atr_multiplier = 2.0  # dragon08-h4-hybrid-talib-volume-off/config.yaml
capital_mgmt.lot_notional_units = 100000.0  # dragon08-h4-hybrid-talib-volume-off/config.yaml
capital_mgmt.min_reward_risk = 2.0  # dragon08-h4-hybrid-talib-volume-off/config.yaml
capital_mgmt.min_stop_factor = 1.2  # dragon08-h4-hybrid-talib-volume-off/config.yaml
capital_mgmt.min_stop_pips = 5.0  # dragon08-h4-hybrid-talib-volume-off/config.yaml
capital_mgmt.pip_value_per_lot = 10.0  # dragon08-h4-hybrid-talib-volume-off/config.yaml
capital_mgmt.risk_per_trade = 0.03  # dragon08-h4-hybrid-talib-volume-off/config.yaml
capital_mgmt.stop_distance_source = "swing"  # dragon08-h4-hybrid-talib-volume-off/config.yaml
capital_mgmt.stop_loss_pips = 20.0  # dragon08-h4-hybrid-talib-volume-off/config.yaml
capital_mgmt.stop_loss_shrink = 0.5  # dragon08-h4-hybrid-talib-volume-off/config.yaml
capital_mgmt.targets = [{"at_level_ratio": 4.0, "close_fraction": 0.5}, {"at_level_ratio": 6.0, "close_fraction": 0.5}]  # dragon08-h4-hybrid-talib-volume-off/config.yaml
capital_mgmt.trail_stops = [{"at_level_ratio": 2.0, "to_level_ratio": 0.1}]  # dragon08-h4-hybrid-talib-volume-off/config.yaml
execution.broker_stop_level_pips = 0.0  # dragon08-h4-hybrid-talib-volume-off/config.yaml
execution.close_on_veto = false  # dragon08-h4-hybrid-talib-volume-off/config.yaml
execution.commission_per_lot = 0.0  # dragon08-h4-hybrid-talib-volume-off/config.yaml
execution.min_hold_bars = 0  # dragon08-h4-hybrid-talib-volume-off/config.yaml
execution.spread_pips = 1.0  # dragon08-h4-hybrid-talib-volume-off/config.yaml
filters = ["f1_trend", "f2_indicator", "f3_pattern", "f4_news_context", "f5_risk_guard", "f6_capital_mgmt", "f7_meta_learner"]  # dragon08-h4-hybrid-talib-volume-off/config.yaml
indicator.macd_hist_threshold = 0.0  # dragon08-h4-hybrid-talib-volume-off/config.yaml
indicator.rsi_midline = 50.0  # dragon08-h4-hybrid-talib-volume-off/config.yaml
meta_learner.families = ["trend", "indicator", "pattern", "news"]  # dragon08-h4-hybrid-talib-volume-off/config.yaml
meta_learner.label_horizon_minutes = 60  # h1-hybrid-vol-off/config.yaml
meta_learner.regime_gate = false  # dragon08-h4-hybrid-talib-volume-off/config.yaml
meta_learner.theta_high = 0.55  # dragon08-h4-hybrid-talib-volume-off/config.yaml
meta_learner.theta_low = 0.45  # dragon08-h4-hybrid-talib-volume-off/config.yaml
news_context.event_intensity_veto_threshold = -0.5  # dragon08-h4-hybrid-talib-volume-off/config.yaml
news_context.sentiment_direction_threshold = 0.15  # dragon08-h4-hybrid-talib-volume-off/config.yaml
pattern.bearish_patterns = ["bearish_engulfing", "evening_star", "shooting_star"]  # dragon08-h4-hybrid-talib-volume-off/config.yaml
pattern.bullish_patterns = ["bullish_engulfing", "hammer", "morning_star"]  # dragon08-h4-hybrid-talib-volume-off/config.yaml
pattern.detector = "talib"  # dragon08-h4-hybrid-talib-volume-off/config.yaml
perception_source = "ema"  # dragon08-h4-hybrid-talib-volume-off/config.yaml
price_features.atr_period = 14  # dragon08-h4-hybrid-talib-volume-off/config.yaml
price_features.bar_minutes = 60  # h1-hybrid-vol-off/config.yaml
price_features.ema_fast = 3  # dragon08-h4-hybrid-talib-volume-off/config.yaml
price_features.ema_higher_tf = 60  # dragon08-h4-hybrid-talib-volume-off/config.yaml
price_features.ema_slow = 8  # dragon08-h4-hybrid-talib-volume-off/config.yaml
price_features.macd_fast = 12  # dragon08-h4-hybrid-talib-volume-off/config.yaml
price_features.macd_signal = 9  # dragon08-h4-hybrid-talib-volume-off/config.yaml
price_features.macd_slow = 26  # dragon08-h4-hybrid-talib-volume-off/config.yaml
price_features.rsi_period = 14  # dragon08-h4-hybrid-talib-volume-off/config.yaml
price_features.swing_lookback_bars = 60  # dragon08-h4-hybrid-talib-volume-off/config.yaml
risk_guard.daily_drawdown_limit = -0.05  # dragon08-h4-hybrid-talib-volume-off/config.yaml
risk_guard.max_concurrent_trades_per_account = 2  # dragon08-h4-hybrid-talib-volume-off/config.yaml
risk_guard.max_leverage = 30  # dragon08-h4-hybrid-talib-volume-off/config.yaml
risk_guard.portfolio_at_risk_cap = 0.18  # dragon08-h4-hybrid-talib-volume-off/config.yaml
risk_guard.weekly_drawdown_limit = -0.15  # dragon08-h4-hybrid-talib-volume-off/config.yaml
schema_version = 2  # h1-hybrid-vol-off/config.yaml
```

## h1-gate-on (job `2026-09-28-h1-tuning-sweep`)

Variant YAML:
```yaml
# h1-gate-on: H1 base with the regime gate on.
# H1 tuning sweep 2026-09-28 (exploratory; fixed thresholds 0.55/0.45 unless stated; same splits/rules as the H4 sweeps).
schema_version: 2
extends: h1-candle-vol-on

meta_learner:
  regime_gate: true
```

Resolved parameters:
```
capital_mgmt.assumed_leverage = 30.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.atr_multiplier = 2.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.lot_notional_units = 100000.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_reward_risk = 2.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_stop_factor = 1.2  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_stop_pips = 5.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.pip_value_per_lot = 10.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.risk_per_trade = 0.03  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_distance_source = "swing"  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_loss_pips = 20.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_loss_shrink = 0.5  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.targets = [{"at_level_ratio": 4.0, "close_fraction": 0.5}, {"at_level_ratio": 6.0, "close_fraction": 0.5}]  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.trail_stops = [{"at_level_ratio": 2.0, "to_level_ratio": 0.1}]  # dragon08-h4-talib-volume-on/config.yaml
execution.broker_stop_level_pips = 0.0  # dragon08-h4-talib-volume-on/config.yaml
execution.close_on_veto = false  # dragon08-h4-talib-volume-on/config.yaml
execution.commission_per_lot = 0.0  # dragon08-h4-talib-volume-on/config.yaml
execution.min_hold_bars = 0  # dragon08-h4-talib-volume-on/config.yaml
execution.spread_pips = 1.0  # dragon08-h4-talib-volume-on/config.yaml
filters = ["f1_trend", "f2_indicator", "f3_pattern", "volume_strength", "f5_risk_guard", "f6_capital_mgmt", "f7_meta_learner"]  # dragon08-h4-talib-volume-on/config.yaml
indicator.macd_hist_threshold = 0.0  # dragon08-h4-talib-volume-on/config.yaml
indicator.rsi_midline = 50.0  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.families = ["trend", "indicator", "pattern"]  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.label_horizon_minutes = 60  # h1-candle-vol-on/config.yaml
meta_learner.regime_gate = true  # h1-gate-on/config.yaml
meta_learner.theta_high = 0.55  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.theta_low = 0.45  # dragon08-h4-talib-volume-on/config.yaml
pattern.bearish_patterns = ["bearish_engulfing", "evening_star", "shooting_star"]  # dragon08-h4-talib-volume-on/config.yaml
pattern.bullish_patterns = ["bullish_engulfing", "hammer", "morning_star"]  # dragon08-h4-talib-volume-on/config.yaml
pattern.detector = "talib"  # dragon08-h4-talib-volume-on/config.yaml
perception_source = "ema"  # dragon08-h4-talib-volume-on/config.yaml
price_features.atr_period = 14  # dragon08-h4-talib-volume-on/config.yaml
price_features.bar_minutes = 60  # h1-candle-vol-on/config.yaml
price_features.ema_fast = 3  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_higher_tf = 60  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_slow = 8  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_fast = 12  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_signal = 9  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_slow = 26  # dragon08-h4-talib-volume-on/config.yaml
price_features.rsi_period = 14  # dragon08-h4-talib-volume-on/config.yaml
price_features.swing_lookback_bars = 60  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.daily_drawdown_limit = -0.05  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.max_concurrent_trades_per_account = 2  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.max_leverage = 30  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.portfolio_at_risk_cap = 0.18  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.weekly_drawdown_limit = -0.15  # dragon08-h4-talib-volume-on/config.yaml
schema_version = 2  # h1-gate-on/config.yaml
volume_strength.lookback = 20  # dragon08-h4-talib-volume-on/config.yaml
volume_strength.min_relative_activity = 1.0  # dragon08-h4-talib-volume-on/config.yaml
```

## h1-theta-53-47 (job `2026-09-28-h1-tuning-sweep`)

Variant YAML:
```yaml
# h1-theta-53-47: H1 base with thresholds 0.53/0.47.
# H1 tuning sweep 2026-09-28 (exploratory; fixed thresholds 0.55/0.45 unless stated; same splits/rules as the H4 sweeps).
schema_version: 2
extends: h1-candle-vol-on

meta_learner:
  theta_high: 0.53
  theta_low: 0.47
```

Resolved parameters:
```
capital_mgmt.assumed_leverage = 30.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.atr_multiplier = 2.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.lot_notional_units = 100000.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_reward_risk = 2.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_stop_factor = 1.2  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_stop_pips = 5.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.pip_value_per_lot = 10.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.risk_per_trade = 0.03  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_distance_source = "swing"  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_loss_pips = 20.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_loss_shrink = 0.5  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.targets = [{"at_level_ratio": 4.0, "close_fraction": 0.5}, {"at_level_ratio": 6.0, "close_fraction": 0.5}]  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.trail_stops = [{"at_level_ratio": 2.0, "to_level_ratio": 0.1}]  # dragon08-h4-talib-volume-on/config.yaml
execution.broker_stop_level_pips = 0.0  # dragon08-h4-talib-volume-on/config.yaml
execution.close_on_veto = false  # dragon08-h4-talib-volume-on/config.yaml
execution.commission_per_lot = 0.0  # dragon08-h4-talib-volume-on/config.yaml
execution.min_hold_bars = 0  # dragon08-h4-talib-volume-on/config.yaml
execution.spread_pips = 1.0  # dragon08-h4-talib-volume-on/config.yaml
filters = ["f1_trend", "f2_indicator", "f3_pattern", "volume_strength", "f5_risk_guard", "f6_capital_mgmt", "f7_meta_learner"]  # dragon08-h4-talib-volume-on/config.yaml
indicator.macd_hist_threshold = 0.0  # dragon08-h4-talib-volume-on/config.yaml
indicator.rsi_midline = 50.0  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.families = ["trend", "indicator", "pattern"]  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.label_horizon_minutes = 60  # h1-candle-vol-on/config.yaml
meta_learner.regime_gate = false  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.theta_high = 0.53  # h1-theta-53-47/config.yaml
meta_learner.theta_low = 0.47  # h1-theta-53-47/config.yaml
pattern.bearish_patterns = ["bearish_engulfing", "evening_star", "shooting_star"]  # dragon08-h4-talib-volume-on/config.yaml
pattern.bullish_patterns = ["bullish_engulfing", "hammer", "morning_star"]  # dragon08-h4-talib-volume-on/config.yaml
pattern.detector = "talib"  # dragon08-h4-talib-volume-on/config.yaml
perception_source = "ema"  # dragon08-h4-talib-volume-on/config.yaml
price_features.atr_period = 14  # dragon08-h4-talib-volume-on/config.yaml
price_features.bar_minutes = 60  # h1-candle-vol-on/config.yaml
price_features.ema_fast = 3  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_higher_tf = 60  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_slow = 8  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_fast = 12  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_signal = 9  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_slow = 26  # dragon08-h4-talib-volume-on/config.yaml
price_features.rsi_period = 14  # dragon08-h4-talib-volume-on/config.yaml
price_features.swing_lookback_bars = 60  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.daily_drawdown_limit = -0.05  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.max_concurrent_trades_per_account = 2  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.max_leverage = 30  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.portfolio_at_risk_cap = 0.18  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.weekly_drawdown_limit = -0.15  # dragon08-h4-talib-volume-on/config.yaml
schema_version = 2  # h1-theta-53-47/config.yaml
volume_strength.lookback = 20  # dragon08-h4-talib-volume-on/config.yaml
volume_strength.min_relative_activity = 1.0  # dragon08-h4-talib-volume-on/config.yaml
```

## h1-theta-57-43 (job `2026-09-28-h1-tuning-sweep`)

Variant YAML:
```yaml
# h1-theta-57-43: H1 base with thresholds 0.57/0.43.
# H1 tuning sweep 2026-09-28 (exploratory; fixed thresholds 0.55/0.45 unless stated; same splits/rules as the H4 sweeps).
schema_version: 2
extends: h1-candle-vol-on

meta_learner:
  theta_high: 0.57
  theta_low: 0.43
```

Resolved parameters:
```
capital_mgmt.assumed_leverage = 30.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.atr_multiplier = 2.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.lot_notional_units = 100000.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_reward_risk = 2.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_stop_factor = 1.2  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_stop_pips = 5.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.pip_value_per_lot = 10.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.risk_per_trade = 0.03  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_distance_source = "swing"  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_loss_pips = 20.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_loss_shrink = 0.5  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.targets = [{"at_level_ratio": 4.0, "close_fraction": 0.5}, {"at_level_ratio": 6.0, "close_fraction": 0.5}]  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.trail_stops = [{"at_level_ratio": 2.0, "to_level_ratio": 0.1}]  # dragon08-h4-talib-volume-on/config.yaml
execution.broker_stop_level_pips = 0.0  # dragon08-h4-talib-volume-on/config.yaml
execution.close_on_veto = false  # dragon08-h4-talib-volume-on/config.yaml
execution.commission_per_lot = 0.0  # dragon08-h4-talib-volume-on/config.yaml
execution.min_hold_bars = 0  # dragon08-h4-talib-volume-on/config.yaml
execution.spread_pips = 1.0  # dragon08-h4-talib-volume-on/config.yaml
filters = ["f1_trend", "f2_indicator", "f3_pattern", "volume_strength", "f5_risk_guard", "f6_capital_mgmt", "f7_meta_learner"]  # dragon08-h4-talib-volume-on/config.yaml
indicator.macd_hist_threshold = 0.0  # dragon08-h4-talib-volume-on/config.yaml
indicator.rsi_midline = 50.0  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.families = ["trend", "indicator", "pattern"]  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.label_horizon_minutes = 60  # h1-candle-vol-on/config.yaml
meta_learner.regime_gate = false  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.theta_high = 0.57  # h1-theta-57-43/config.yaml
meta_learner.theta_low = 0.43  # h1-theta-57-43/config.yaml
pattern.bearish_patterns = ["bearish_engulfing", "evening_star", "shooting_star"]  # dragon08-h4-talib-volume-on/config.yaml
pattern.bullish_patterns = ["bullish_engulfing", "hammer", "morning_star"]  # dragon08-h4-talib-volume-on/config.yaml
pattern.detector = "talib"  # dragon08-h4-talib-volume-on/config.yaml
perception_source = "ema"  # dragon08-h4-talib-volume-on/config.yaml
price_features.atr_period = 14  # dragon08-h4-talib-volume-on/config.yaml
price_features.bar_minutes = 60  # h1-candle-vol-on/config.yaml
price_features.ema_fast = 3  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_higher_tf = 60  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_slow = 8  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_fast = 12  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_signal = 9  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_slow = 26  # dragon08-h4-talib-volume-on/config.yaml
price_features.rsi_period = 14  # dragon08-h4-talib-volume-on/config.yaml
price_features.swing_lookback_bars = 60  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.daily_drawdown_limit = -0.05  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.max_concurrent_trades_per_account = 2  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.max_leverage = 30  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.portfolio_at_risk_cap = 0.18  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.weekly_drawdown_limit = -0.15  # dragon08-h4-talib-volume-on/config.yaml
schema_version = 2  # h1-theta-57-43/config.yaml
volume_strength.lookback = 20  # dragon08-h4-talib-volume-on/config.yaml
volume_strength.min_relative_activity = 1.0  # dragon08-h4-talib-volume-on/config.yaml
```

## h1-plan-dragon05 (job `2026-09-28-h1-tuning-sweep`)

Variant YAML:
```yaml
# h1-plan-dragon05: H1 base with the Dragon05 plan (1R/50 %, 2R rest, trail 1R -> breakeven, min R:R 1).
# H1 tuning sweep 2026-09-28 (exploratory; fixed thresholds 0.55/0.45 unless stated; same splits/rules as the H4 sweeps).
schema_version: 2
extends: h1-candle-vol-on

capital_mgmt:
  stop_loss_shrink: 0.50
  targets:
    - {at_level_ratio: 1.0, close_fraction: 0.5}
    - {at_level_ratio: 2.0, close_fraction: 0.5}
  trail_stops:
    - {at_level_ratio: 1.0, to_level_ratio: 0.0}
  min_reward_risk: 1.0
```

Resolved parameters:
```
capital_mgmt.assumed_leverage = 30.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.atr_multiplier = 2.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.lot_notional_units = 100000.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_reward_risk = 1.0  # h1-plan-dragon05/config.yaml
capital_mgmt.min_stop_factor = 1.2  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_stop_pips = 5.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.pip_value_per_lot = 10.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.risk_per_trade = 0.03  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_distance_source = "swing"  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_loss_pips = 20.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_loss_shrink = 0.5  # h1-plan-dragon05/config.yaml
capital_mgmt.targets = [{"at_level_ratio": 1.0, "close_fraction": 0.5}, {"at_level_ratio": 2.0, "close_fraction": 0.5}]  # h1-plan-dragon05/config.yaml
capital_mgmt.trail_stops = [{"at_level_ratio": 1.0, "to_level_ratio": 0.0}]  # h1-plan-dragon05/config.yaml
execution.broker_stop_level_pips = 0.0  # dragon08-h4-talib-volume-on/config.yaml
execution.close_on_veto = false  # dragon08-h4-talib-volume-on/config.yaml
execution.commission_per_lot = 0.0  # dragon08-h4-talib-volume-on/config.yaml
execution.min_hold_bars = 0  # dragon08-h4-talib-volume-on/config.yaml
execution.spread_pips = 1.0  # dragon08-h4-talib-volume-on/config.yaml
filters = ["f1_trend", "f2_indicator", "f3_pattern", "volume_strength", "f5_risk_guard", "f6_capital_mgmt", "f7_meta_learner"]  # dragon08-h4-talib-volume-on/config.yaml
indicator.macd_hist_threshold = 0.0  # dragon08-h4-talib-volume-on/config.yaml
indicator.rsi_midline = 50.0  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.families = ["trend", "indicator", "pattern"]  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.label_horizon_minutes = 60  # h1-candle-vol-on/config.yaml
meta_learner.regime_gate = false  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.theta_high = 0.55  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.theta_low = 0.45  # dragon08-h4-talib-volume-on/config.yaml
pattern.bearish_patterns = ["bearish_engulfing", "evening_star", "shooting_star"]  # dragon08-h4-talib-volume-on/config.yaml
pattern.bullish_patterns = ["bullish_engulfing", "hammer", "morning_star"]  # dragon08-h4-talib-volume-on/config.yaml
pattern.detector = "talib"  # dragon08-h4-talib-volume-on/config.yaml
perception_source = "ema"  # dragon08-h4-talib-volume-on/config.yaml
price_features.atr_period = 14  # dragon08-h4-talib-volume-on/config.yaml
price_features.bar_minutes = 60  # h1-candle-vol-on/config.yaml
price_features.ema_fast = 3  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_higher_tf = 60  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_slow = 8  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_fast = 12  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_signal = 9  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_slow = 26  # dragon08-h4-talib-volume-on/config.yaml
price_features.rsi_period = 14  # dragon08-h4-talib-volume-on/config.yaml
price_features.swing_lookback_bars = 60  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.daily_drawdown_limit = -0.05  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.max_concurrent_trades_per_account = 2  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.max_leverage = 30  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.portfolio_at_risk_cap = 0.18  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.weekly_drawdown_limit = -0.15  # dragon08-h4-talib-volume-on/config.yaml
schema_version = 2  # h1-plan-dragon05/config.yaml
volume_strength.lookback = 20  # dragon08-h4-talib-volume-on/config.yaml
volume_strength.min_relative_activity = 1.0  # dragon08-h4-talib-volume-on/config.yaml
```

## h1-vol-0.8 (job `2026-09-28-h1-tuning-sweep`)

Variant YAML:
```yaml
# h1-vol-0.8: H1 base with activity threshold 0.8.
# H1 tuning sweep 2026-09-28 (exploratory; fixed thresholds 0.55/0.45 unless stated; same splits/rules as the H4 sweeps).
schema_version: 2
extends: h1-candle-vol-on

volume_strength:
  lookback: 20
  min_relative_activity: 0.8
```

Resolved parameters:
```
capital_mgmt.assumed_leverage = 30.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.atr_multiplier = 2.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.lot_notional_units = 100000.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_reward_risk = 2.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_stop_factor = 1.2  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_stop_pips = 5.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.pip_value_per_lot = 10.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.risk_per_trade = 0.03  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_distance_source = "swing"  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_loss_pips = 20.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_loss_shrink = 0.5  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.targets = [{"at_level_ratio": 4.0, "close_fraction": 0.5}, {"at_level_ratio": 6.0, "close_fraction": 0.5}]  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.trail_stops = [{"at_level_ratio": 2.0, "to_level_ratio": 0.1}]  # dragon08-h4-talib-volume-on/config.yaml
execution.broker_stop_level_pips = 0.0  # dragon08-h4-talib-volume-on/config.yaml
execution.close_on_veto = false  # dragon08-h4-talib-volume-on/config.yaml
execution.commission_per_lot = 0.0  # dragon08-h4-talib-volume-on/config.yaml
execution.min_hold_bars = 0  # dragon08-h4-talib-volume-on/config.yaml
execution.spread_pips = 1.0  # dragon08-h4-talib-volume-on/config.yaml
filters = ["f1_trend", "f2_indicator", "f3_pattern", "volume_strength", "f5_risk_guard", "f6_capital_mgmt", "f7_meta_learner"]  # dragon08-h4-talib-volume-on/config.yaml
indicator.macd_hist_threshold = 0.0  # dragon08-h4-talib-volume-on/config.yaml
indicator.rsi_midline = 50.0  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.families = ["trend", "indicator", "pattern"]  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.label_horizon_minutes = 60  # h1-candle-vol-on/config.yaml
meta_learner.regime_gate = false  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.theta_high = 0.55  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.theta_low = 0.45  # dragon08-h4-talib-volume-on/config.yaml
pattern.bearish_patterns = ["bearish_engulfing", "evening_star", "shooting_star"]  # dragon08-h4-talib-volume-on/config.yaml
pattern.bullish_patterns = ["bullish_engulfing", "hammer", "morning_star"]  # dragon08-h4-talib-volume-on/config.yaml
pattern.detector = "talib"  # dragon08-h4-talib-volume-on/config.yaml
perception_source = "ema"  # dragon08-h4-talib-volume-on/config.yaml
price_features.atr_period = 14  # dragon08-h4-talib-volume-on/config.yaml
price_features.bar_minutes = 60  # h1-candle-vol-on/config.yaml
price_features.ema_fast = 3  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_higher_tf = 60  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_slow = 8  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_fast = 12  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_signal = 9  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_slow = 26  # dragon08-h4-talib-volume-on/config.yaml
price_features.rsi_period = 14  # dragon08-h4-talib-volume-on/config.yaml
price_features.swing_lookback_bars = 60  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.daily_drawdown_limit = -0.05  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.max_concurrent_trades_per_account = 2  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.max_leverage = 30  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.portfolio_at_risk_cap = 0.18  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.weekly_drawdown_limit = -0.15  # dragon08-h4-talib-volume-on/config.yaml
schema_version = 2  # h1-vol-0.8/config.yaml
volume_strength.lookback = 20  # h1-vol-0.8/config.yaml
volume_strength.min_relative_activity = 0.8  # h1-vol-0.8/config.yaml
```

## h1-vol-1.2 (job `2026-09-28-h1-tuning-sweep`)

Variant YAML:
```yaml
# h1-vol-1.2: H1 base with activity threshold 1.2.
# H1 tuning sweep 2026-09-28 (exploratory; fixed thresholds 0.55/0.45 unless stated; same splits/rules as the H4 sweeps).
schema_version: 2
extends: h1-candle-vol-on

volume_strength:
  lookback: 20
  min_relative_activity: 1.2
```

Resolved parameters:
```
capital_mgmt.assumed_leverage = 30.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.atr_multiplier = 2.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.lot_notional_units = 100000.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_reward_risk = 2.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_stop_factor = 1.2  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_stop_pips = 5.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.pip_value_per_lot = 10.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.risk_per_trade = 0.03  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_distance_source = "swing"  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_loss_pips = 20.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_loss_shrink = 0.5  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.targets = [{"at_level_ratio": 4.0, "close_fraction": 0.5}, {"at_level_ratio": 6.0, "close_fraction": 0.5}]  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.trail_stops = [{"at_level_ratio": 2.0, "to_level_ratio": 0.1}]  # dragon08-h4-talib-volume-on/config.yaml
execution.broker_stop_level_pips = 0.0  # dragon08-h4-talib-volume-on/config.yaml
execution.close_on_veto = false  # dragon08-h4-talib-volume-on/config.yaml
execution.commission_per_lot = 0.0  # dragon08-h4-talib-volume-on/config.yaml
execution.min_hold_bars = 0  # dragon08-h4-talib-volume-on/config.yaml
execution.spread_pips = 1.0  # dragon08-h4-talib-volume-on/config.yaml
filters = ["f1_trend", "f2_indicator", "f3_pattern", "volume_strength", "f5_risk_guard", "f6_capital_mgmt", "f7_meta_learner"]  # dragon08-h4-talib-volume-on/config.yaml
indicator.macd_hist_threshold = 0.0  # dragon08-h4-talib-volume-on/config.yaml
indicator.rsi_midline = 50.0  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.families = ["trend", "indicator", "pattern"]  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.label_horizon_minutes = 60  # h1-candle-vol-on/config.yaml
meta_learner.regime_gate = false  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.theta_high = 0.55  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.theta_low = 0.45  # dragon08-h4-talib-volume-on/config.yaml
pattern.bearish_patterns = ["bearish_engulfing", "evening_star", "shooting_star"]  # dragon08-h4-talib-volume-on/config.yaml
pattern.bullish_patterns = ["bullish_engulfing", "hammer", "morning_star"]  # dragon08-h4-talib-volume-on/config.yaml
pattern.detector = "talib"  # dragon08-h4-talib-volume-on/config.yaml
perception_source = "ema"  # dragon08-h4-talib-volume-on/config.yaml
price_features.atr_period = 14  # dragon08-h4-talib-volume-on/config.yaml
price_features.bar_minutes = 60  # h1-candle-vol-on/config.yaml
price_features.ema_fast = 3  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_higher_tf = 60  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_slow = 8  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_fast = 12  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_signal = 9  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_slow = 26  # dragon08-h4-talib-volume-on/config.yaml
price_features.rsi_period = 14  # dragon08-h4-talib-volume-on/config.yaml
price_features.swing_lookback_bars = 60  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.daily_drawdown_limit = -0.05  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.max_concurrent_trades_per_account = 2  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.max_leverage = 30  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.portfolio_at_risk_cap = 0.18  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.weekly_drawdown_limit = -0.15  # dragon08-h4-talib-volume-on/config.yaml
schema_version = 2  # h1-vol-1.2/config.yaml
volume_strength.lookback = 20  # h1-vol-1.2/config.yaml
volume_strength.min_relative_activity = 1.2  # h1-vol-1.2/config.yaml
```

## h1-q05-base (job `2026-09-28-h1-tuning-sweep-q`)

Variant YAML:
```yaml
# h1-q05-base: H1 base with thresholds at 5 % per side of the January-2016 validation quantiles of h1-baseline-talib.
# H1 calibrated batch 2026-09-28 (exploratory; tf-threshold-calibration.json).
schema_version: 2
extends: h1-candle-vol-on

meta_learner:
  theta_high: 0.5434
  theta_low: 0.5127
```

Resolved parameters:
```
capital_mgmt.assumed_leverage = 30.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.atr_multiplier = 2.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.lot_notional_units = 100000.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_reward_risk = 2.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_stop_factor = 1.2  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_stop_pips = 5.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.pip_value_per_lot = 10.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.risk_per_trade = 0.03  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_distance_source = "swing"  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_loss_pips = 20.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_loss_shrink = 0.5  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.targets = [{"at_level_ratio": 4.0, "close_fraction": 0.5}, {"at_level_ratio": 6.0, "close_fraction": 0.5}]  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.trail_stops = [{"at_level_ratio": 2.0, "to_level_ratio": 0.1}]  # dragon08-h4-talib-volume-on/config.yaml
execution.broker_stop_level_pips = 0.0  # dragon08-h4-talib-volume-on/config.yaml
execution.close_on_veto = false  # dragon08-h4-talib-volume-on/config.yaml
execution.commission_per_lot = 0.0  # dragon08-h4-talib-volume-on/config.yaml
execution.min_hold_bars = 0  # dragon08-h4-talib-volume-on/config.yaml
execution.spread_pips = 1.0  # dragon08-h4-talib-volume-on/config.yaml
filters = ["f1_trend", "f2_indicator", "f3_pattern", "volume_strength", "f5_risk_guard", "f6_capital_mgmt", "f7_meta_learner"]  # dragon08-h4-talib-volume-on/config.yaml
indicator.macd_hist_threshold = 0.0  # dragon08-h4-talib-volume-on/config.yaml
indicator.rsi_midline = 50.0  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.families = ["trend", "indicator", "pattern"]  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.label_horizon_minutes = 60  # h1-candle-vol-on/config.yaml
meta_learner.regime_gate = false  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.theta_high = 0.5434  # h1-q05-base/config.yaml
meta_learner.theta_low = 0.5127  # h1-q05-base/config.yaml
pattern.bearish_patterns = ["bearish_engulfing", "evening_star", "shooting_star"]  # dragon08-h4-talib-volume-on/config.yaml
pattern.bullish_patterns = ["bullish_engulfing", "hammer", "morning_star"]  # dragon08-h4-talib-volume-on/config.yaml
pattern.detector = "talib"  # dragon08-h4-talib-volume-on/config.yaml
perception_source = "ema"  # dragon08-h4-talib-volume-on/config.yaml
price_features.atr_period = 14  # dragon08-h4-talib-volume-on/config.yaml
price_features.bar_minutes = 60  # h1-candle-vol-on/config.yaml
price_features.ema_fast = 3  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_higher_tf = 60  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_slow = 8  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_fast = 12  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_signal = 9  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_slow = 26  # dragon08-h4-talib-volume-on/config.yaml
price_features.rsi_period = 14  # dragon08-h4-talib-volume-on/config.yaml
price_features.swing_lookback_bars = 60  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.daily_drawdown_limit = -0.05  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.max_concurrent_trades_per_account = 2  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.max_leverage = 30  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.portfolio_at_risk_cap = 0.18  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.weekly_drawdown_limit = -0.15  # dragon08-h4-talib-volume-on/config.yaml
schema_version = 2  # h1-q05-base/config.yaml
volume_strength.lookback = 20  # dragon08-h4-talib-volume-on/config.yaml
volume_strength.min_relative_activity = 1.0  # dragon08-h4-talib-volume-on/config.yaml
```

## h1-q10-base (job `2026-09-28-h1-tuning-sweep-q`)

Variant YAML:
```yaml
# h1-q10-base: H1 base with thresholds at 10 % per side of the January-2016 validation quantiles of h1-baseline-talib.
# H1 calibrated batch 2026-09-28 (exploratory; tf-threshold-calibration.json).
schema_version: 2
extends: h1-candle-vol-on

meta_learner:
  theta_high: 0.5401
  theta_low: 0.5165
```

Resolved parameters:
```
capital_mgmt.assumed_leverage = 30.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.atr_multiplier = 2.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.lot_notional_units = 100000.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_reward_risk = 2.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_stop_factor = 1.2  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_stop_pips = 5.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.pip_value_per_lot = 10.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.risk_per_trade = 0.03  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_distance_source = "swing"  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_loss_pips = 20.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_loss_shrink = 0.5  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.targets = [{"at_level_ratio": 4.0, "close_fraction": 0.5}, {"at_level_ratio": 6.0, "close_fraction": 0.5}]  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.trail_stops = [{"at_level_ratio": 2.0, "to_level_ratio": 0.1}]  # dragon08-h4-talib-volume-on/config.yaml
execution.broker_stop_level_pips = 0.0  # dragon08-h4-talib-volume-on/config.yaml
execution.close_on_veto = false  # dragon08-h4-talib-volume-on/config.yaml
execution.commission_per_lot = 0.0  # dragon08-h4-talib-volume-on/config.yaml
execution.min_hold_bars = 0  # dragon08-h4-talib-volume-on/config.yaml
execution.spread_pips = 1.0  # dragon08-h4-talib-volume-on/config.yaml
filters = ["f1_trend", "f2_indicator", "f3_pattern", "volume_strength", "f5_risk_guard", "f6_capital_mgmt", "f7_meta_learner"]  # dragon08-h4-talib-volume-on/config.yaml
indicator.macd_hist_threshold = 0.0  # dragon08-h4-talib-volume-on/config.yaml
indicator.rsi_midline = 50.0  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.families = ["trend", "indicator", "pattern"]  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.label_horizon_minutes = 60  # h1-candle-vol-on/config.yaml
meta_learner.regime_gate = false  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.theta_high = 0.5401  # h1-q10-base/config.yaml
meta_learner.theta_low = 0.5165  # h1-q10-base/config.yaml
pattern.bearish_patterns = ["bearish_engulfing", "evening_star", "shooting_star"]  # dragon08-h4-talib-volume-on/config.yaml
pattern.bullish_patterns = ["bullish_engulfing", "hammer", "morning_star"]  # dragon08-h4-talib-volume-on/config.yaml
pattern.detector = "talib"  # dragon08-h4-talib-volume-on/config.yaml
perception_source = "ema"  # dragon08-h4-talib-volume-on/config.yaml
price_features.atr_period = 14  # dragon08-h4-talib-volume-on/config.yaml
price_features.bar_minutes = 60  # h1-candle-vol-on/config.yaml
price_features.ema_fast = 3  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_higher_tf = 60  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_slow = 8  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_fast = 12  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_signal = 9  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_slow = 26  # dragon08-h4-talib-volume-on/config.yaml
price_features.rsi_period = 14  # dragon08-h4-talib-volume-on/config.yaml
price_features.swing_lookback_bars = 60  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.daily_drawdown_limit = -0.05  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.max_concurrent_trades_per_account = 2  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.max_leverage = 30  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.portfolio_at_risk_cap = 0.18  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.weekly_drawdown_limit = -0.15  # dragon08-h4-talib-volume-on/config.yaml
schema_version = 2  # h1-q10-base/config.yaml
volume_strength.lookback = 20  # dragon08-h4-talib-volume-on/config.yaml
volume_strength.min_relative_activity = 1.0  # dragon08-h4-talib-volume-on/config.yaml
```

## h1-q15-base (job `2026-09-28-h1-tuning-sweep-q`)

Variant YAML:
```yaml
# h1-q15-base: H1 base with thresholds at 15 % per side of the January-2016 validation quantiles of h1-baseline-talib.
# H1 calibrated batch 2026-09-28 (exploratory; tf-threshold-calibration.json).
schema_version: 2
extends: h1-candle-vol-on

meta_learner:
  theta_high: 0.5353
  theta_low: 0.5192
```

Resolved parameters:
```
capital_mgmt.assumed_leverage = 30.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.atr_multiplier = 2.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.lot_notional_units = 100000.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_reward_risk = 2.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_stop_factor = 1.2  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.min_stop_pips = 5.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.pip_value_per_lot = 10.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.risk_per_trade = 0.03  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_distance_source = "swing"  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_loss_pips = 20.0  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.stop_loss_shrink = 0.5  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.targets = [{"at_level_ratio": 4.0, "close_fraction": 0.5}, {"at_level_ratio": 6.0, "close_fraction": 0.5}]  # dragon08-h4-talib-volume-on/config.yaml
capital_mgmt.trail_stops = [{"at_level_ratio": 2.0, "to_level_ratio": 0.1}]  # dragon08-h4-talib-volume-on/config.yaml
execution.broker_stop_level_pips = 0.0  # dragon08-h4-talib-volume-on/config.yaml
execution.close_on_veto = false  # dragon08-h4-talib-volume-on/config.yaml
execution.commission_per_lot = 0.0  # dragon08-h4-talib-volume-on/config.yaml
execution.min_hold_bars = 0  # dragon08-h4-talib-volume-on/config.yaml
execution.spread_pips = 1.0  # dragon08-h4-talib-volume-on/config.yaml
filters = ["f1_trend", "f2_indicator", "f3_pattern", "volume_strength", "f5_risk_guard", "f6_capital_mgmt", "f7_meta_learner"]  # dragon08-h4-talib-volume-on/config.yaml
indicator.macd_hist_threshold = 0.0  # dragon08-h4-talib-volume-on/config.yaml
indicator.rsi_midline = 50.0  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.families = ["trend", "indicator", "pattern"]  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.label_horizon_minutes = 60  # h1-candle-vol-on/config.yaml
meta_learner.regime_gate = false  # dragon08-h4-talib-volume-on/config.yaml
meta_learner.theta_high = 0.5353  # h1-q15-base/config.yaml
meta_learner.theta_low = 0.5192  # h1-q15-base/config.yaml
pattern.bearish_patterns = ["bearish_engulfing", "evening_star", "shooting_star"]  # dragon08-h4-talib-volume-on/config.yaml
pattern.bullish_patterns = ["bullish_engulfing", "hammer", "morning_star"]  # dragon08-h4-talib-volume-on/config.yaml
pattern.detector = "talib"  # dragon08-h4-talib-volume-on/config.yaml
perception_source = "ema"  # dragon08-h4-talib-volume-on/config.yaml
price_features.atr_period = 14  # dragon08-h4-talib-volume-on/config.yaml
price_features.bar_minutes = 60  # h1-candle-vol-on/config.yaml
price_features.ema_fast = 3  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_higher_tf = 60  # dragon08-h4-talib-volume-on/config.yaml
price_features.ema_slow = 8  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_fast = 12  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_signal = 9  # dragon08-h4-talib-volume-on/config.yaml
price_features.macd_slow = 26  # dragon08-h4-talib-volume-on/config.yaml
price_features.rsi_period = 14  # dragon08-h4-talib-volume-on/config.yaml
price_features.swing_lookback_bars = 60  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.daily_drawdown_limit = -0.05  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.max_concurrent_trades_per_account = 2  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.max_leverage = 30  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.portfolio_at_risk_cap = 0.18  # dragon08-h4-talib-volume-on/config.yaml
risk_guard.weekly_drawdown_limit = -0.15  # dragon08-h4-talib-volume-on/config.yaml
schema_version = 2  # h1-q15-base/config.yaml
volume_strength.lookback = 20  # dragon08-h4-talib-volume-on/config.yaml
volume_strength.min_relative_activity = 1.0  # dragon08-h4-talib-volume-on/config.yaml
```

## h1-q10-vol-off (job `2026-09-28-h1-tuning-sweep-q`)

Variant YAML:
```yaml
# h1-q10-vol-off: H1 vol-off with thresholds at 10 % per side of the January-2016 validation quantiles of h1-baseline-talib.
# H1 calibrated batch 2026-09-28 (exploratory; tf-threshold-calibration.json).
schema_version: 2
extends: h1-candle-vol-off

meta_learner:
  theta_high: 0.5401
  theta_low: 0.5165
```

Resolved parameters:
```
capital_mgmt.assumed_leverage = 30.0  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.atr_multiplier = 2.0  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.lot_notional_units = 100000.0  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.min_reward_risk = 2.0  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.min_stop_factor = 1.2  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.min_stop_pips = 5.0  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.pip_value_per_lot = 10.0  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.risk_per_trade = 0.03  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.stop_distance_source = "swing"  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.stop_loss_pips = 20.0  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.stop_loss_shrink = 0.5  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.targets = [{"at_level_ratio": 4.0, "close_fraction": 0.5}, {"at_level_ratio": 6.0, "close_fraction": 0.5}]  # dragon08-h4-talib-volume-off/config.yaml
capital_mgmt.trail_stops = [{"at_level_ratio": 2.0, "to_level_ratio": 0.1}]  # dragon08-h4-talib-volume-off/config.yaml
execution.broker_stop_level_pips = 0.0  # dragon08-h4-talib-volume-off/config.yaml
execution.close_on_veto = false  # dragon08-h4-talib-volume-off/config.yaml
execution.commission_per_lot = 0.0  # dragon08-h4-talib-volume-off/config.yaml
execution.min_hold_bars = 0  # dragon08-h4-talib-volume-off/config.yaml
execution.spread_pips = 1.0  # dragon08-h4-talib-volume-off/config.yaml
filters = ["f1_trend", "f2_indicator", "f3_pattern", "f5_risk_guard", "f6_capital_mgmt", "f7_meta_learner"]  # dragon08-h4-talib-volume-off/config.yaml
indicator.macd_hist_threshold = 0.0  # dragon08-h4-talib-volume-off/config.yaml
indicator.rsi_midline = 50.0  # dragon08-h4-talib-volume-off/config.yaml
meta_learner.families = ["trend", "indicator", "pattern"]  # dragon08-h4-talib-volume-off/config.yaml
meta_learner.label_horizon_minutes = 60  # h1-candle-vol-off/config.yaml
meta_learner.regime_gate = false  # dragon08-h4-talib-volume-off/config.yaml
meta_learner.theta_high = 0.5401  # h1-q10-vol-off/config.yaml
meta_learner.theta_low = 0.5165  # h1-q10-vol-off/config.yaml
pattern.bearish_patterns = ["bearish_engulfing", "evening_star", "shooting_star"]  # dragon08-h4-talib-volume-off/config.yaml
pattern.bullish_patterns = ["bullish_engulfing", "hammer", "morning_star"]  # dragon08-h4-talib-volume-off/config.yaml
pattern.detector = "talib"  # dragon08-h4-talib-volume-off/config.yaml
perception_source = "ema"  # dragon08-h4-talib-volume-off/config.yaml
price_features.atr_period = 14  # dragon08-h4-talib-volume-off/config.yaml
price_features.bar_minutes = 60  # h1-candle-vol-off/config.yaml
price_features.ema_fast = 3  # dragon08-h4-talib-volume-off/config.yaml
price_features.ema_higher_tf = 60  # dragon08-h4-talib-volume-off/config.yaml
price_features.ema_slow = 8  # dragon08-h4-talib-volume-off/config.yaml
price_features.macd_fast = 12  # dragon08-h4-talib-volume-off/config.yaml
price_features.macd_signal = 9  # dragon08-h4-talib-volume-off/config.yaml
price_features.macd_slow = 26  # dragon08-h4-talib-volume-off/config.yaml
price_features.rsi_period = 14  # dragon08-h4-talib-volume-off/config.yaml
price_features.swing_lookback_bars = 60  # dragon08-h4-talib-volume-off/config.yaml
risk_guard.daily_drawdown_limit = -0.05  # dragon08-h4-talib-volume-off/config.yaml
risk_guard.max_concurrent_trades_per_account = 2  # dragon08-h4-talib-volume-off/config.yaml
risk_guard.max_leverage = 30  # dragon08-h4-talib-volume-off/config.yaml
risk_guard.portfolio_at_risk_cap = 0.18  # dragon08-h4-talib-volume-off/config.yaml
risk_guard.weekly_drawdown_limit = -0.15  # dragon08-h4-talib-volume-off/config.yaml
schema_version = 2  # h1-q10-vol-off/config.yaml
```

## h1-q05-hybrid (job `2026-09-28-h1-tuning-sweep-q`)

Variant YAML:
```yaml
# h1-q05-hybrid: H1 hybrid with thresholds at 5 % per side of the January-2016 validation quantiles of h1-hybrid-talib.
# H1 calibrated batch 2026-09-28 (exploratory; tf-threshold-calibration.json).
schema_version: 2
extends: h1-hybrid-candle-vol-on

meta_learner:
  theta_high: 0.5434
  theta_low: 0.5127
```

Resolved parameters:
```
capital_mgmt.assumed_leverage = 30.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.atr_multiplier = 2.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.lot_notional_units = 100000.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.min_reward_risk = 2.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.min_stop_factor = 1.2  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.min_stop_pips = 5.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.pip_value_per_lot = 10.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.risk_per_trade = 0.03  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.stop_distance_source = "swing"  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.stop_loss_pips = 20.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.stop_loss_shrink = 0.5  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.targets = [{"at_level_ratio": 4.0, "close_fraction": 0.5}, {"at_level_ratio": 6.0, "close_fraction": 0.5}]  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.trail_stops = [{"at_level_ratio": 2.0, "to_level_ratio": 0.1}]  # dragon08-h4-hybrid-talib-volume-on/config.yaml
execution.broker_stop_level_pips = 0.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
execution.close_on_veto = false  # dragon08-h4-hybrid-talib-volume-on/config.yaml
execution.commission_per_lot = 0.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
execution.min_hold_bars = 0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
execution.spread_pips = 1.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
filters = ["f1_trend", "f2_indicator", "f3_pattern", "f4_news_context", "volume_strength", "f5_risk_guard", "f6_capital_mgmt", "f7_meta_learner"]  # dragon08-h4-hybrid-talib-volume-on/config.yaml
indicator.macd_hist_threshold = 0.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
indicator.rsi_midline = 50.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
meta_learner.families = ["trend", "indicator", "pattern", "news"]  # dragon08-h4-hybrid-talib-volume-on/config.yaml
meta_learner.label_horizon_minutes = 60  # h1-hybrid-candle-vol-on/config.yaml
meta_learner.regime_gate = false  # dragon08-h4-hybrid-talib-volume-on/config.yaml
meta_learner.theta_high = 0.5434  # h1-q05-hybrid/config.yaml
meta_learner.theta_low = 0.5127  # h1-q05-hybrid/config.yaml
news_context.event_intensity_veto_threshold = -0.5  # dragon08-h4-hybrid-talib-volume-on/config.yaml
news_context.sentiment_direction_threshold = 0.15  # dragon08-h4-hybrid-talib-volume-on/config.yaml
pattern.bearish_patterns = ["bearish_engulfing", "evening_star", "shooting_star"]  # dragon08-h4-hybrid-talib-volume-on/config.yaml
pattern.bullish_patterns = ["bullish_engulfing", "hammer", "morning_star"]  # dragon08-h4-hybrid-talib-volume-on/config.yaml
pattern.detector = "talib"  # dragon08-h4-hybrid-talib-volume-on/config.yaml
perception_source = "ema"  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.atr_period = 14  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.bar_minutes = 60  # h1-hybrid-candle-vol-on/config.yaml
price_features.ema_fast = 3  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.ema_higher_tf = 60  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.ema_slow = 8  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.macd_fast = 12  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.macd_signal = 9  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.macd_slow = 26  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.rsi_period = 14  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.swing_lookback_bars = 60  # dragon08-h4-hybrid-talib-volume-on/config.yaml
risk_guard.daily_drawdown_limit = -0.05  # dragon08-h4-hybrid-talib-volume-on/config.yaml
risk_guard.max_concurrent_trades_per_account = 2  # dragon08-h4-hybrid-talib-volume-on/config.yaml
risk_guard.max_leverage = 30  # dragon08-h4-hybrid-talib-volume-on/config.yaml
risk_guard.portfolio_at_risk_cap = 0.18  # dragon08-h4-hybrid-talib-volume-on/config.yaml
risk_guard.weekly_drawdown_limit = -0.15  # dragon08-h4-hybrid-talib-volume-on/config.yaml
schema_version = 2  # h1-q05-hybrid/config.yaml
volume_strength.lookback = 20  # dragon08-h4-hybrid-talib-volume-on/config.yaml
volume_strength.min_relative_activity = 1.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
```

## h1-q10-hybrid (job `2026-09-28-h1-tuning-sweep-q`)

Variant YAML:
```yaml
# h1-q10-hybrid: H1 hybrid with thresholds at 10 % per side of the January-2016 validation quantiles of h1-hybrid-talib.
# H1 calibrated batch 2026-09-28 (exploratory; tf-threshold-calibration.json).
schema_version: 2
extends: h1-hybrid-candle-vol-on

meta_learner:
  theta_high: 0.54
  theta_low: 0.5165
```

Resolved parameters:
```
capital_mgmt.assumed_leverage = 30.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.atr_multiplier = 2.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.lot_notional_units = 100000.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.min_reward_risk = 2.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.min_stop_factor = 1.2  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.min_stop_pips = 5.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.pip_value_per_lot = 10.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.risk_per_trade = 0.03  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.stop_distance_source = "swing"  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.stop_loss_pips = 20.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.stop_loss_shrink = 0.5  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.targets = [{"at_level_ratio": 4.0, "close_fraction": 0.5}, {"at_level_ratio": 6.0, "close_fraction": 0.5}]  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.trail_stops = [{"at_level_ratio": 2.0, "to_level_ratio": 0.1}]  # dragon08-h4-hybrid-talib-volume-on/config.yaml
execution.broker_stop_level_pips = 0.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
execution.close_on_veto = false  # dragon08-h4-hybrid-talib-volume-on/config.yaml
execution.commission_per_lot = 0.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
execution.min_hold_bars = 0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
execution.spread_pips = 1.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
filters = ["f1_trend", "f2_indicator", "f3_pattern", "f4_news_context", "volume_strength", "f5_risk_guard", "f6_capital_mgmt", "f7_meta_learner"]  # dragon08-h4-hybrid-talib-volume-on/config.yaml
indicator.macd_hist_threshold = 0.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
indicator.rsi_midline = 50.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
meta_learner.families = ["trend", "indicator", "pattern", "news"]  # dragon08-h4-hybrid-talib-volume-on/config.yaml
meta_learner.label_horizon_minutes = 60  # h1-hybrid-candle-vol-on/config.yaml
meta_learner.regime_gate = false  # dragon08-h4-hybrid-talib-volume-on/config.yaml
meta_learner.theta_high = 0.54  # h1-q10-hybrid/config.yaml
meta_learner.theta_low = 0.5165  # h1-q10-hybrid/config.yaml
news_context.event_intensity_veto_threshold = -0.5  # dragon08-h4-hybrid-talib-volume-on/config.yaml
news_context.sentiment_direction_threshold = 0.15  # dragon08-h4-hybrid-talib-volume-on/config.yaml
pattern.bearish_patterns = ["bearish_engulfing", "evening_star", "shooting_star"]  # dragon08-h4-hybrid-talib-volume-on/config.yaml
pattern.bullish_patterns = ["bullish_engulfing", "hammer", "morning_star"]  # dragon08-h4-hybrid-talib-volume-on/config.yaml
pattern.detector = "talib"  # dragon08-h4-hybrid-talib-volume-on/config.yaml
perception_source = "ema"  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.atr_period = 14  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.bar_minutes = 60  # h1-hybrid-candle-vol-on/config.yaml
price_features.ema_fast = 3  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.ema_higher_tf = 60  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.ema_slow = 8  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.macd_fast = 12  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.macd_signal = 9  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.macd_slow = 26  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.rsi_period = 14  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.swing_lookback_bars = 60  # dragon08-h4-hybrid-talib-volume-on/config.yaml
risk_guard.daily_drawdown_limit = -0.05  # dragon08-h4-hybrid-talib-volume-on/config.yaml
risk_guard.max_concurrent_trades_per_account = 2  # dragon08-h4-hybrid-talib-volume-on/config.yaml
risk_guard.max_leverage = 30  # dragon08-h4-hybrid-talib-volume-on/config.yaml
risk_guard.portfolio_at_risk_cap = 0.18  # dragon08-h4-hybrid-talib-volume-on/config.yaml
risk_guard.weekly_drawdown_limit = -0.15  # dragon08-h4-hybrid-talib-volume-on/config.yaml
schema_version = 2  # h1-q10-hybrid/config.yaml
volume_strength.lookback = 20  # dragon08-h4-hybrid-talib-volume-on/config.yaml
volume_strength.min_relative_activity = 1.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
```

## h1-q15-hybrid (job `2026-09-28-h1-tuning-sweep-q`)

Variant YAML:
```yaml
# h1-q15-hybrid: H1 hybrid with thresholds at 15 % per side of the January-2016 validation quantiles of h1-hybrid-talib.
# H1 calibrated batch 2026-09-28 (exploratory; tf-threshold-calibration.json).
schema_version: 2
extends: h1-hybrid-candle-vol-on

meta_learner:
  theta_high: 0.536
  theta_low: 0.5192
```

Resolved parameters:
```
capital_mgmt.assumed_leverage = 30.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.atr_multiplier = 2.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.lot_notional_units = 100000.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.min_reward_risk = 2.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.min_stop_factor = 1.2  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.min_stop_pips = 5.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.pip_value_per_lot = 10.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.risk_per_trade = 0.03  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.stop_distance_source = "swing"  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.stop_loss_pips = 20.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.stop_loss_shrink = 0.5  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.targets = [{"at_level_ratio": 4.0, "close_fraction": 0.5}, {"at_level_ratio": 6.0, "close_fraction": 0.5}]  # dragon08-h4-hybrid-talib-volume-on/config.yaml
capital_mgmt.trail_stops = [{"at_level_ratio": 2.0, "to_level_ratio": 0.1}]  # dragon08-h4-hybrid-talib-volume-on/config.yaml
execution.broker_stop_level_pips = 0.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
execution.close_on_veto = false  # dragon08-h4-hybrid-talib-volume-on/config.yaml
execution.commission_per_lot = 0.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
execution.min_hold_bars = 0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
execution.spread_pips = 1.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
filters = ["f1_trend", "f2_indicator", "f3_pattern", "f4_news_context", "volume_strength", "f5_risk_guard", "f6_capital_mgmt", "f7_meta_learner"]  # dragon08-h4-hybrid-talib-volume-on/config.yaml
indicator.macd_hist_threshold = 0.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
indicator.rsi_midline = 50.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
meta_learner.families = ["trend", "indicator", "pattern", "news"]  # dragon08-h4-hybrid-talib-volume-on/config.yaml
meta_learner.label_horizon_minutes = 60  # h1-hybrid-candle-vol-on/config.yaml
meta_learner.regime_gate = false  # dragon08-h4-hybrid-talib-volume-on/config.yaml
meta_learner.theta_high = 0.536  # h1-q15-hybrid/config.yaml
meta_learner.theta_low = 0.5192  # h1-q15-hybrid/config.yaml
news_context.event_intensity_veto_threshold = -0.5  # dragon08-h4-hybrid-talib-volume-on/config.yaml
news_context.sentiment_direction_threshold = 0.15  # dragon08-h4-hybrid-talib-volume-on/config.yaml
pattern.bearish_patterns = ["bearish_engulfing", "evening_star", "shooting_star"]  # dragon08-h4-hybrid-talib-volume-on/config.yaml
pattern.bullish_patterns = ["bullish_engulfing", "hammer", "morning_star"]  # dragon08-h4-hybrid-talib-volume-on/config.yaml
pattern.detector = "talib"  # dragon08-h4-hybrid-talib-volume-on/config.yaml
perception_source = "ema"  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.atr_period = 14  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.bar_minutes = 60  # h1-hybrid-candle-vol-on/config.yaml
price_features.ema_fast = 3  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.ema_higher_tf = 60  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.ema_slow = 8  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.macd_fast = 12  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.macd_signal = 9  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.macd_slow = 26  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.rsi_period = 14  # dragon08-h4-hybrid-talib-volume-on/config.yaml
price_features.swing_lookback_bars = 60  # dragon08-h4-hybrid-talib-volume-on/config.yaml
risk_guard.daily_drawdown_limit = -0.05  # dragon08-h4-hybrid-talib-volume-on/config.yaml
risk_guard.max_concurrent_trades_per_account = 2  # dragon08-h4-hybrid-talib-volume-on/config.yaml
risk_guard.max_leverage = 30  # dragon08-h4-hybrid-talib-volume-on/config.yaml
risk_guard.portfolio_at_risk_cap = 0.18  # dragon08-h4-hybrid-talib-volume-on/config.yaml
risk_guard.weekly_drawdown_limit = -0.15  # dragon08-h4-hybrid-talib-volume-on/config.yaml
schema_version = 2  # h1-q15-hybrid/config.yaml
volume_strength.lookback = 20  # dragon08-h4-hybrid-talib-volume-on/config.yaml
volume_strength.min_relative_activity = 1.0  # dragon08-h4-hybrid-talib-volume-on/config.yaml
```

## h1-q10-hybrid-vol-off (job `2026-09-28-h1-tuning-sweep-q`)

Variant YAML:
```yaml
# h1-q10-hybrid-vol-off: H1 hybrid-vol-off with thresholds at 10 % per side of the January-2016 validation quantiles of h1-hybrid-talib.
# H1 calibrated batch 2026-09-28 (exploratory; tf-threshold-calibration.json).
schema_version: 2
extends: h1-hybrid-vol-off

meta_learner:
  theta_high: 0.54
  theta_low: 0.5165
```

Resolved parameters:
```
capital_mgmt.assumed_leverage = 30.0  # dragon08-h4-hybrid-talib-volume-off/config.yaml
capital_mgmt.atr_multiplier = 2.0  # dragon08-h4-hybrid-talib-volume-off/config.yaml
capital_mgmt.lot_notional_units = 100000.0  # dragon08-h4-hybrid-talib-volume-off/config.yaml
capital_mgmt.min_reward_risk = 2.0  # dragon08-h4-hybrid-talib-volume-off/config.yaml
capital_mgmt.min_stop_factor = 1.2  # dragon08-h4-hybrid-talib-volume-off/config.yaml
capital_mgmt.min_stop_pips = 5.0  # dragon08-h4-hybrid-talib-volume-off/config.yaml
capital_mgmt.pip_value_per_lot = 10.0  # dragon08-h4-hybrid-talib-volume-off/config.yaml
capital_mgmt.risk_per_trade = 0.03  # dragon08-h4-hybrid-talib-volume-off/config.yaml
capital_mgmt.stop_distance_source = "swing"  # dragon08-h4-hybrid-talib-volume-off/config.yaml
capital_mgmt.stop_loss_pips = 20.0  # dragon08-h4-hybrid-talib-volume-off/config.yaml
capital_mgmt.stop_loss_shrink = 0.5  # dragon08-h4-hybrid-talib-volume-off/config.yaml
capital_mgmt.targets = [{"at_level_ratio": 4.0, "close_fraction": 0.5}, {"at_level_ratio": 6.0, "close_fraction": 0.5}]  # dragon08-h4-hybrid-talib-volume-off/config.yaml
capital_mgmt.trail_stops = [{"at_level_ratio": 2.0, "to_level_ratio": 0.1}]  # dragon08-h4-hybrid-talib-volume-off/config.yaml
execution.broker_stop_level_pips = 0.0  # dragon08-h4-hybrid-talib-volume-off/config.yaml
execution.close_on_veto = false  # dragon08-h4-hybrid-talib-volume-off/config.yaml
execution.commission_per_lot = 0.0  # dragon08-h4-hybrid-talib-volume-off/config.yaml
execution.min_hold_bars = 0  # dragon08-h4-hybrid-talib-volume-off/config.yaml
execution.spread_pips = 1.0  # dragon08-h4-hybrid-talib-volume-off/config.yaml
filters = ["f1_trend", "f2_indicator", "f3_pattern", "f4_news_context", "f5_risk_guard", "f6_capital_mgmt", "f7_meta_learner"]  # dragon08-h4-hybrid-talib-volume-off/config.yaml
indicator.macd_hist_threshold = 0.0  # dragon08-h4-hybrid-talib-volume-off/config.yaml
indicator.rsi_midline = 50.0  # dragon08-h4-hybrid-talib-volume-off/config.yaml
meta_learner.families = ["trend", "indicator", "pattern", "news"]  # dragon08-h4-hybrid-talib-volume-off/config.yaml
meta_learner.label_horizon_minutes = 60  # h1-hybrid-vol-off/config.yaml
meta_learner.regime_gate = false  # dragon08-h4-hybrid-talib-volume-off/config.yaml
meta_learner.theta_high = 0.54  # h1-q10-hybrid-vol-off/config.yaml
meta_learner.theta_low = 0.5165  # h1-q10-hybrid-vol-off/config.yaml
news_context.event_intensity_veto_threshold = -0.5  # dragon08-h4-hybrid-talib-volume-off/config.yaml
news_context.sentiment_direction_threshold = 0.15  # dragon08-h4-hybrid-talib-volume-off/config.yaml
pattern.bearish_patterns = ["bearish_engulfing", "evening_star", "shooting_star"]  # dragon08-h4-hybrid-talib-volume-off/config.yaml
pattern.bullish_patterns = ["bullish_engulfing", "hammer", "morning_star"]  # dragon08-h4-hybrid-talib-volume-off/config.yaml
pattern.detector = "talib"  # dragon08-h4-hybrid-talib-volume-off/config.yaml
perception_source = "ema"  # dragon08-h4-hybrid-talib-volume-off/config.yaml
price_features.atr_period = 14  # dragon08-h4-hybrid-talib-volume-off/config.yaml
price_features.bar_minutes = 60  # h1-hybrid-vol-off/config.yaml
price_features.ema_fast = 3  # dragon08-h4-hybrid-talib-volume-off/config.yaml
price_features.ema_higher_tf = 60  # dragon08-h4-hybrid-talib-volume-off/config.yaml
price_features.ema_slow = 8  # dragon08-h4-hybrid-talib-volume-off/config.yaml
price_features.macd_fast = 12  # dragon08-h4-hybrid-talib-volume-off/config.yaml
price_features.macd_signal = 9  # dragon08-h4-hybrid-talib-volume-off/config.yaml
price_features.macd_slow = 26  # dragon08-h4-hybrid-talib-volume-off/config.yaml
price_features.rsi_period = 14  # dragon08-h4-hybrid-talib-volume-off/config.yaml
price_features.swing_lookback_bars = 60  # dragon08-h4-hybrid-talib-volume-off/config.yaml
risk_guard.daily_drawdown_limit = -0.05  # dragon08-h4-hybrid-talib-volume-off/config.yaml
risk_guard.max_concurrent_trades_per_account = 2  # dragon08-h4-hybrid-talib-volume-off/config.yaml
risk_guard.max_leverage = 30  # dragon08-h4-hybrid-talib-volume-off/config.yaml
risk_guard.portfolio_at_risk_cap = 0.18  # dragon08-h4-hybrid-talib-volume-off/config.yaml
risk_guard.weekly_drawdown_limit = -0.15  # dragon08-h4-hybrid-talib-volume-off/config.yaml
schema_version = 2  # h1-q10-hybrid-vol-off/config.yaml
```

