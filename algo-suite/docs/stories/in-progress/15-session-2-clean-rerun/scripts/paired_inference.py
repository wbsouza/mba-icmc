"""Paired stationary-bootstrap inference over daily net returns (challenger minus baseline).

Usage: python paired_inference.py RUNS_ROOT OUT_PREFIX PAIRS_JSON
PAIRS_JSON: [{"label": "...", "challenger": "<run name>", "baseline": "<run name>"}, ...]
Daily returns: calendar-day close equity from each run's equity.csv (last equity of the day,
forward-filled over 2016-03-01..2017-02-28), so the full year gives 364 returns and the untouched
window (2016-11-01..2017-02-28) 120. Untouched months use block lengths 4 and 2, the full year 5 and
3; 999 resamples, seed 42, alpha 0.05 (same registration as session 1).
"""
import csv, dataclasses, glob, json, sys
from datetime import date, timedelta
from pathlib import Path

from algo_analyze.significance import paired_block_test

RUNS, OUT, PAIRS = Path(sys.argv[1]), sys.argv[2], json.load(open(sys.argv[3]))
START, END, UNTOUCHED = date(2016, 3, 1), date(2017, 2, 28), date(2016, 11, 1)
WINDOWS = {"untouched Nov 2016-Feb 2017": (UNTOUCHED, (4, 2)), "full year Mar 2016-Feb 2017": (START + timedelta(days=1), (5, 3))}


def latest(name: str) -> Path:
    dirs = [d for d in sorted(glob.glob(f"{RUNS}/{name}/*/")) if (Path(d) / "equity.csv").exists()]
    if not dirs:
        raise FileNotFoundError(f"no run for {name} under {RUNS}")
    return Path(dirs[-1])


def daily_returns(name: str) -> dict[date, float]:
    close: dict[date, float] = {}
    for row in csv.DictReader(open(latest(name) / "equity.csv")):
        close[date.fromisoformat(row["time"][:10])] = float(row["equity"])
    series, last, d = {}, None, START
    while d <= END:
        last = close.get(d, last)
        if last is None:
            raise ValueError(f"{name}: no equity on or before {d}")
        series[d] = last
        d += timedelta(days=1)
    days = sorted(series)
    return {days[i]: series[days[i]] / series[days[i - 1]] - 1 for i in range(1, len(days))}


results, lines = {}, ["# Paired stationary-bootstrap inference, trading year (challenger minus baseline, mean daily net return; 999 resamples, seed 42, alpha 0.05)", "", "| comparison | window | n days | block | effect/day | 95% CI | p | reject |", "|---|---|---:|---:|---:|---|---:|---|"]
for pair in PAIRS:
    try:
        a, b = daily_returns(pair["challenger"]), daily_returns(pair["baseline"])  # test takes (baseline, challenger)
    except (FileNotFoundError, ValueError) as exc:
        lines.append(f"| {pair['label']} | — | — | — | — | not computed: {exc} | — | — |"); continue
    for window, (first_day, blocks) in WINDOWS.items():
        days = [d for d in sorted(a) if d >= first_day]
        ra, rb = [a[d] for d in days], [b[d] for d in days]
        for block in blocks:
            r = paired_block_test(rb, ra, block_length=block, n_resamples=999, seed=42)
            results[f"{pair['label']} | {window} | block {block}"] = dataclasses.asdict(r)
            lo, hi = r.confidence_interval
            lines.append(f"| {pair['label']} | {window} | {r.n_observations} | {block} | {r.effect*100:+.3f}% | [{lo*100:+.3f}%, {hi*100:+.3f}%] | {r.p_value:.3f} | {'yes' if r.reject_null else 'no'} |")
Path(OUT + ".json").write_text(json.dumps(results, indent=1))
Path(OUT + ".md").write_text("\n".join(lines) + "\n")
print("\n".join(lines))
