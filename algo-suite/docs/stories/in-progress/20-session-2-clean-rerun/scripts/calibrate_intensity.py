"""January-2016 quantiles of the event-intensity feature at H1 and H4 decision bars, for the rule cells."""
import json, os, sys
from datetime import date, datetime, timedelta
from pathlib import Path
import numpy as np
from algo_backtest.training import load_event_intensity
from algo_core import layout
root = layout.data_root()
intensity = load_event_intensity(root, date(2016, 1, 1), date(2016, 1, 31))
out = {}
for clock, minutes in (("h1", 60), ("h4", 240)):
    vals = [v for t, v in sorted(intensity.items()) if (t.hour * 60 + t.minute) % minutes == 0]
    a = np.array(vals, dtype=float)
    out[clock] = {"n": int(len(a)), "quantiles": {q: round(float(np.quantile(a, q)), 4) for q in (0.05, 0.10, 0.25, 0.5, 0.75, 0.90, 0.95)}}
    print(clock, out[clock], file=sys.stderr)
Path(sys.argv[1]).write_text(json.dumps(out, indent=1))
