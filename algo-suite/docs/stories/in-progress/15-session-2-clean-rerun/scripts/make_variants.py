"""Post-calibration cells: symmetric January-2016 quantile thresholds so BUY and SELL both fire in one run."""
import json, pathlib, sys
JOB = pathlib.Path(sys.argv[1]); cal = json.load(open(JOB / "calibration.json")); inten = json.load(open(JOB / "intensity-calibration.json"))
root = JOB / "strategies"; V = {}
def th(model, share):
    g = next(x for x in cal[model]["grid"] if abs(x["share_per_side"] - share) < 1e-9); return g["theta_high"], g["theta_low"]
def w(name, base, model, share, extra="", note=""):
    hi, lo = th(model, share)
    (root / name).mkdir(exist_ok=True)
    (root / name / "config.yaml").write_text(f"# {note} thresholds = January-2016 validation quantiles, {int(share*100)} % per side.\nschema_version: 2\nextends: {base}\nmeta_learner:\n  theta_high: {hi}\n  theta_low: {lo}\n{extra}")
    V[name] = model
w("h1-q05-base", "h1-base-vol-on", "h1-baseline", 0.05, note="H1 price-only, activity on;")
w("h1-q05-hybrid", "h1-hybrid-vol-on", "h1-hybrid", 0.05, note="H1 hybrid, activity on;")
w("h1-q10-base", "h1-base", "h1-baseline", 0.10, note="H1 price-only, activity off;")
w("h1-q10-hybrid", "h1-hybrid", "h1-hybrid", 0.10, note="H1 hybrid, activity off;")
w("h1-q10-gate-base", "h1-base", "h1-baseline", 0.10, extra="  regime_gate: true\n", note="H1 price-only, regime gate on;")
w("h1-q10-gate-hybrid", "h1-hybrid", "h1-hybrid", 0.10, extra="  regime_gate: true\n", note="H1 hybrid, regime gate on;")
w("h4-q10-base", "heikin-ashi-h4-talib-volume-off", "h4-baseline", 0.10, note="H4 price-only, activity off;")
w("h4-q10-hybrid", "heikin-ashi-h4-hybrid-talib-volume-off", "h4-hybrid", 0.10, note="H4 hybrid, activity off;")
w("h4-q10-atr-stop", "heikin-ashi-h4-talib-volume-on", "h4-baseline", 0.10, extra="capital_mgmt:\n  stop_distance_source: atr\n  atr_multiplier: 2.0\n  min_stop_pips: 10.0\n  stop_loss_shrink: 0.0\n", note="H4 price-only, ATR stop;")
for tf in ("m5", "m15", "m30"):
    w(f"{tf}-q10-base", f"{tf}-base", f"{tf}-baseline", 0.10, note=f"{tf.upper()} price-only;")
    w(f"{tf}-q10-hybrid", f"{tf}-hybrid", f"{tf}-hybrid", 0.10, note=f"{tf.upper()} hybrid;")
w("news-only-h1-q10", "news-only", "news-only-h1", 0.10, note="H1 news-only (F7 on the news family);")
w("news-only-h4-q10", "news-only-h4", "news-only-h4", 0.10, note="H4 news-only;")
q = inten["h1"]["quantiles"]; hi, lo = q["0.9"], q["0.1"]
for c, base in (("h1", "news-rule"), ("h4", "news-rule-h4")):
    for sign, tag in ((1, "plus"), (-1, "minus")):
        n = f"news-rule-{c}-{tag}"; (root / n).mkdir(exist_ok=True)
        (root / n / "config.yaml").write_text(f"# {c.upper()} rule: F4 direction from the event intensity (January-2016 90/10 % quantiles), sign {sign:+d}, no F7.\nschema_version: 2\nextends: {base}\nnews_context:\n  direction_source: intensity\n  intensity_buy_threshold: {hi}\n  intensity_sell_threshold: {lo}\n  intensity_sign: {sign}\n")
        V[n] = ""
for n in ("always-short-h1", "always-short-h4", "h1-fixed-base", "h1-fixed-hybrid", "h1-fixed-vol-0.8"):
    V[n] = {"h1-fixed-base": "h1-baseline", "h1-fixed-hybrid": "h1-hybrid", "h1-fixed-vol-0.8": "h1-baseline"}.get(n, "")
(JOB / "model-map.json").write_text(json.dumps(V, indent=1)); (JOB / "variants.txt").write_text("\n".join(V) + "\n"); print(len(V), "cells")
