"""January-2016 quantile thresholds for every session-2 model (never reads a 2016-03+ bar)."""
import json, os, sys
from datetime import date
from pathlib import Path
import numpy as np
from algo_backtest.chain.filters.f7_meta_learner import walk_forward_split
from algo_backtest.chain.filters.f7_model_io import load_model
from algo_backtest.strategies import load_strategy_chain_config
from algo_backtest.training import build_training_rows, load_event_intensity, load_m1_bars
from algo_core import layout
from algo_core.instrument import build_instrument
JOB = Path(os.environ["CALIB_JOB"]); root = JOB / "strategies"; data_root = layout.data_root(); instrument = build_instrument("EURUSD")
start, train_end, val_end, test_end = date(2015, 3, 2), date(2015, 12, 31), date(2016, 1, 31), date(2016, 2, 29)
bars = load_m1_bars(data_root, instrument, start, test_end); intensity = load_event_intensity(data_root, start, test_end)
MODELS = json.load(open(JOB / "train-map.json"))
SHARES = (0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40); out = {}
for model_name, strategy in MODELS.items():
    config = load_strategy_chain_config(strategy, root=root); assert config.f7 is not None
    uses_news = "news" in config.f7.families
    rows = build_training_rows(bars, intensity if uses_news else None, instrument=instrument, perception=config.perception, price_features_config=config.price_features, horizon_minutes=config.f7.label_horizon_minutes, pattern_config=config.pattern, volume_config=config.volume_strength)
    split = walk_forward_split(rows, train_end=train_end, validation_end=val_end, test_end=test_end)
    model = load_model(JOB / "models" / f"{model_name}.json")
    spans = {"validation_jan2016": split.validation, "heldout_feb2016": split.test}
    pred = {k: np.array([model.predict(r.features) for r in v]) for k, v in spans.items()}; lab = {k: np.array([r.label for r in v]) for k, v in spans.items()}
    pv = pred["validation_jan2016"]
    rec = {"strategy": strategy, "uses_news": uses_news, "rows": {k: int(len(v)) for k, v in spans.items()}, "p_quantiles": {k: {q: round(float(np.quantile(p, q)), 4) for q in (0.01, 0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99)} for k, p in pred.items()}, "grid": []}
    for s in SHARES:
        hi, lo = float(np.quantile(pv, 1 - s)), float(np.quantile(pv, s)); entry = {"share_per_side": s, "theta_high": round(hi, 4), "theta_low": round(lo, 4)}
        for k in spans:
            p, y = pred[k], lab[k]; buy, sell = p > hi, p < lo; n = int(buy.sum() + sell.sum()); hits = int((y[buy] == 1).sum() + (y[sell] == 0).sum())
            entry[k] = {"n_buy": int(buy.sum()), "n_sell": int(sell.sum()), "hit_buy": round(float(y[buy].mean()), 3) if buy.any() else None, "hit_sell": round(float(1 - y[sell].mean()), 3) if sell.any() else None, "hit_all": round(hits / n, 3) if n else None, "signal_share": round(n / len(p), 3)}
        rec["grid"].append(entry)
    out[model_name] = rec; print(model_name, "q10", rec["grid"][1]["theta_high"], rec["grid"][1]["theta_low"], file=sys.stderr)
Path(sys.argv[1]).write_text(json.dumps(out, indent=1)); print("written", sys.argv[1])
