import json, os, random

BASE = "/home/wellington/workspace/mba-agents/mba-main/algo-suite/data/runs"
PATTERNS = [
    "bearish_counterattack_line", "bearish_engulfing", "bearish_harami", "bearish_kicker",
    "bullish_counterattack_line", "bullish_engulfing", "bullish_harami", "bullish_kicker",
    "dark_cloud_cover", "doji", "doji_dragonfly", "doji_gravestone", "doji_long_legged",
    "evening_star", "hammer", "hanging_man", "inverted_hammer", "methods_rising",
    "morning_star", "piercing_line", "shooting_star", "spinning_top",
]

groups = {}
for p in PATTERNS:
    d = f"{BASE}/candles-solo-{p}"
    run_dir = sorted(os.listdir(d))[-1]
    with open(f"{d}/{run_dir}/trades.json") as f:
        trades = json.load(f)
    groups[p] = [t["profitLoss"] for t in trades]

sizes = [len(v) for v in groups.values()]
sums = {p: sum(v) for p, v in groups.items()}
observed_max = max(sums.values())
observed_best = max(sums, key=sums.get)
pooled = [pl for v in groups.values() for pl in v]

random.seed(20260928)
trials = 20000
hits = 0
for _ in range(trials):
    shuffled = pooled[:]
    random.shuffle(shuffled)
    idx = 0
    max_sum = -1e18
    for n in sizes:
        s = sum(shuffled[idx:idx+n])
        idx += n
        if s > max_sum:
            max_sum = s
    if max_sum >= observed_max:
        hits += 1

p_value = hits / trials
print(f"22 patterns, pooled n={len(pooled)}, observed best={observed_best} sum={observed_max:.2f}")
print(f"permutation p-value (max-of-22 >= observed): {p_value:.4f} ({hits}/{trials})")
