"""Pre-calibration strategies for session 2 (clean template names; parameters identical to session 1)."""
import pathlib, sys
root = pathlib.Path(sys.argv[1]) / "strategies"
def w(name, body):
    (root / name).mkdir(exist_ok=True); (root / name / "config.yaml").write_text(body)
clock = lambda minutes: f"price_features:\n  bar_minutes: {minutes}\nmeta_learner:\n  label_horizon_minutes: {minutes}\n"
# training/run templates per clock (H4 uses the heikin-ashi-h4-* templates directly)
w("h1-base-vol-on", "# H1 price-only, TA-Lib candles, activity veto on (trains h1-baseline).\nschema_version: 2\nextends: heikin-ashi-h4-talib-volume-on\n" + clock(60))
w("h1-hybrid-vol-on", "# H1 hybrid (news family + F4), activity veto on (trains h1-hybrid).\nschema_version: 2\nextends: heikin-ashi-h4-hybrid-talib-volume-on\n" + clock(60))
w("h1-base", "# H1 price-only, TA-Lib candles, activity veto off.\nschema_version: 2\nextends: heikin-ashi-h4-talib-volume-off\n" + clock(60))
w("h1-hybrid", "# H1 hybrid, activity veto off.\nschema_version: 2\nextends: heikin-ashi-h4-hybrid-talib-volume-off\n" + clock(60))
for tf, m in (("m5", 5), ("m15", 15), ("m30", 30)):
    w(f"{tf}-base", f"# {tf.upper()} price-only, TA-Lib candles, activity veto off.\nschema_version: 2\nextends: heikin-ashi-h4-talib-volume-off\n" + clock(m))
    w(f"{tf}-hybrid", f"# {tf.upper()} hybrid, activity veto off.\nschema_version: 2\nextends: heikin-ashi-h4-hybrid-talib-volume-off\n" + clock(m))
# session-1 reproduction cells (fixed 0.55/0.45 thresholds = template defaults)
w("h1-fixed-base", "# Reproduction of session-1 h1-candle-vol-off (fixed thresholds).\nschema_version: 2\nextends: h1-base\n")
w("h1-fixed-hybrid", "# Reproduction of session-1 h1-hybrid-vol-off (fixed thresholds).\nschema_version: 2\nextends: h1-hybrid\n")
w("h1-fixed-vol-0.8", "# Reproduction of session-1 h1-vol-0.8 (activity gate 0.8, fixed thresholds).\nschema_version: 2\nextends: h1-base-vol-on\nvolume_strength:\n  lookback: 20\n  min_relative_activity: 0.8\n")
# drift controls: F4 says BUY on every bar, sign -1 turns it into SELL -> short whenever flat
for c, base in (("h1", "news-rule"), ("h4", "news-rule-h4")):
    w(f"always-short-{c}", f"# Control: short whenever flat ({c.upper()} rule chain, no F7).\nschema_version: 2\nextends: {base}\nnews_context:\n  direction_source: intensity\n  intensity_buy_threshold: -99.0\n  intensity_sell_threshold: -100.0\n  intensity_sign: -1\n")
print("ok")
