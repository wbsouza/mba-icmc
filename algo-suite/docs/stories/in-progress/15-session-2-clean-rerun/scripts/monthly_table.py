"""Month-by-month table (markdown) for a list of run names under a runs root; first arg runs root, rest names."""
import json, sys, csv, glob, collections
R = sys.argv[1]; names = sys.argv[2:]
months = [f"2016-{m:02d}" for m in range(3, 13)] + ["2017-01", "2017-02"]
print("| variant | trades | win% | Mar–Oct | Nov | Dec | Jan | Feb | full | max DD | " + " | ".join(m[5:] for m in months) + " |")
print("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|" + "---:|" * len(months))
for n in names:
    dirs = sorted(glob.glob(f"{R}/{n}/*/"))
    if not dirs: print(f"| {n} | (no run) |"); continue
    d = dirs[-1]; rows = list(csv.DictReader(open(d + "equity.csv"))); trades = [t for t in json.load(open(d + "trades.json")) if t.get("orderIds")]
    met = json.load(open(d + "metrics.json")); by = collections.OrderedDict()
    for r in rows: by.setdefault(r["time"][:7], [float(r["equity"]), None])[1] = float(r["equity"])
    eq0 = float(rows[0]["equity"]); prev = eq0; mret = {}
    for ym, (first, last) in by.items(): mret[ym] = (last / prev - 1) * 100; prev = last
    oct_end = by.get("2016-10", [None, None])[1]; wins = sum(1 for t in trades if t["profitLoss"] > 0)
    print(f"| {n} | {len(trades)} | {100*wins/len(trades) if trades else 0:.0f} | {(oct_end/eq0-1)*100 if oct_end else 0:+.2f}% | {mret.get('2016-11',0):+.2f}% | {mret.get('2016-12',0):+.2f}% | {mret.get('2017-01',0):+.2f}% | {mret.get('2017-02',0):+.2f}% | {(float(rows[-1]['equity'])/eq0-1)*100:+.2f}% | {met['max_drawdown']*100:.1f}% | " + " | ".join(f"{mret[m]:+.1f}" if m in mret else "—" for m in months) + " |")
