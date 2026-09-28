"""Reproduction check: session-2 cells and models against the archived session-1 artifacts (same parameters, clean names)."""
import csv, glob, hashlib, json, pathlib, sys
JOB = pathlib.Path(sys.argv[1]); A = pathlib.Path("/home/wellington/workspace/mba-agents/experiment-test-archives/pre-rename-session-1")
RUNS = pathlib.Path("/home/wellington/workspace/mba-agents/mba-main/algo-suite/data/training/2026-09-28-broad-window-h4/data/runs"); ARUNS = A / "broad-window-h4-runs"
CELLS = {"h1-q05-base": "h1-q05-base", "h4-q10-base": "q10-vol-off", "h4-q10-hybrid": "q10-hybrid-vol-off", "h4-q10-atr-stop": "q10-atr-stop", "news-only-h1-q10": "news-only-h1-q10", "news-only-h4-q10": "news-only-h4-q10", "news-rule-h1-plus": "news-rule-h1-plus", "news-rule-h1-minus": "news-rule-h1-minus", "news-rule-h4-plus": "news-rule-h4-plus", "news-rule-h4-minus": "news-rule-h4-minus", "always-short-h1": "always-short-h1", "always-short-h4": "always-short-h4", "h1-fixed-base": "h1-candle-vol-off", "h1-fixed-hybrid": "h1-hybrid-vol-off", "h1-fixed-vol-0.8": "h1-vol-0.8"}
MODELS = {"h1-baseline": "2026-09-28-tf-sweep/models/h1-baseline-talib.json", "h1-hybrid": "2026-09-28-tf-sweep/models/h1-hybrid-talib.json", "h4-baseline": "2026-09-28-h4-tuning-sweep/models/A-baseline-talib.json", "h4-hybrid": "2026-09-28-h4-tuning-sweep/models/C-hybrid-talib.json", "m5-baseline": "2026-09-28-tf-year/models/m5-baseline.json", "m5-hybrid": "2026-09-28-tf-year/models/m5-hybrid.json", "m15-baseline": "2026-09-28-tf-year/models/m15-baseline.json", "m15-hybrid": "2026-09-28-tf-year/models/m15-hybrid.json", "m30-baseline": "2026-09-28-tf-year/models/m30-baseline.json", "m30-hybrid": "2026-09-28-tf-year/models/m30-hybrid.json", "news-only-h1": "2026-09-28-news-only/models/news-only-h1.json", "news-only-h4": "2026-09-28-news-only/models/news-only-h4.json"}
sha = lambda p: hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()[:12]
def strip(o):
    if isinstance(o, dict): return {k: strip(v) for k, v in o.items() if k not in ("trained_at", "strategy", "source", "path", "created", "provenance")}
    if isinstance(o, list): return [strip(x) for x in o]
    return o
print("## Models (session 2 vs session 1)\n\n| model | sha256 s2 | sha256 s1 | identical bytes | identical after dropping provenance | differing keys (outside provenance) |\n|---|---|---|---|---|---|")
for m, old in MODELS.items():
    n, o = JOB / "models" / f"{m}.json", A / old
    if not n.exists() or not o.exists(): print(f"| {m} | {'—' if not n.exists() else sha(n)} | {'—' if not o.exists() else sha(o)} | n/a | n/a | missing file |"); continue
    jn, jo = json.load(open(n)), json.load(open(o)); same = strip(jn) == strip(jo)
    diff = [k for k in set(jn) | set(jo) if strip(jn.get(k)) != strip(jo.get(k))]
    print(f"| {m} | {sha(n)} | {sha(o)} | {'yes' if sha(n) == sha(o) else 'no'} | {'yes' if same else 'no'} | {', '.join(sorted(diff)) or '—'} |")
def latest(root, name):
    d = [x for x in sorted(glob.glob(f"{root}/{name}/*/")) if pathlib.Path(x, "equity.csv").exists()]; return pathlib.Path(d[-1]) if d else None
def summary(d):
    rows = list(csv.DictReader(open(d / "equity.csv"))); tr = [t for t in json.load(open(d / "trades.json")) if t.get("orderIds")]
    return {"trades": len(tr), "final": float(rows[-1]["equity"]), "equity_sha": sha(d / "equity.csv"), "pl": [round(t["profitLoss"], 2) for t in tr]}
print("\n## Cells (session 2 vs session 1)\n\n| session-2 cell | session-1 cell | trades s2 | trades s1 | final equity s2 | final equity s1 | equity.csv identical | trade P/L identical |\n|---|---|---:|---:|---:|---:|---|---|")
for new, old in CELLS.items():
    dn, do = latest(RUNS, new), latest(ARUNS, old)
    if not dn or not do or not (dn / "equity.csv").exists() or not (do / "equity.csv").exists(): print(f"| {new} | {old} | — | — | — | — | missing run | — |"); continue
    sn, so = summary(dn), summary(do)
    print(f"| {new} | {old} | {sn['trades']} | {so['trades']} | {sn['final']:.2f} | {so['final']:.2f} | {'yes' if sn['equity_sha'] == so['equity_sha'] else 'NO'} | {'yes' if sn['pl'] == so['pl'] else 'NO'} |")
