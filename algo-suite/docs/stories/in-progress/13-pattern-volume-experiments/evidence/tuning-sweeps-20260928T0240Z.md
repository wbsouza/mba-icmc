# Tuning sweeps after story 13: candlesticks, quote activity, thresholds, plans, stops, timeframes (20260928T0240Z)

Exploratory. One-year splits for every model (fit 2015-03-02..2015-12-31, combiner calibrated on January 2016, February 2016 held out); one continuous $10,000 account per variant over 2016-03-01..2016-11-30; selection rule declared before viewing: rank on March..October, November (the only month untouched by any earlier decision) read last. Fifty-one trials in total (14 + 11 + 9 + 9 + 8) plus the eight registered broad-window cells. Win% = closed trades with positive P/L. Every variant's complete resolved parameters with provenance are in the companion appendix `tuning-sweeps-parameters-20260928T0240Z.md`; job directories under `algo-suite/data/training/2026-09-28-*` (local) hold models, logs, statements, reports and equity CSVs.

## H4 fixed thresholds 0.55/0.45 (14 variants) — job `2026-09-28-h4-tuning-sweep`

| variant | run id | trades | win% | Mar–Oct | Nov | full | max DD | 03 | 04 | 05 | 06 | 07 | 08 | 09 | 10 | 11 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| t01-base | `t01-base/20260928T014702-917d4f8883f1` | 0 | 0 | +0.00% | +0.00% | +0.00% | 0.0% | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 |
| t02-vol-1.2 | `t02-vol-1.2/20260928T014702-917d49866b98` | 0 | 0 | +0.00% | +0.00% | +0.00% | 0.0% | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 |
| t03-vol-0.8 | `t03-vol-0.8/20260928T014702-917d5088dfd2` | 1 | 0 | -3.00% | +0.00% | -3.00% | 4.0% | +0.0 | -3.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 |
| t04-vol-lb10 | `t04-vol-lb10/20260928T014702-917d4f31710a` | 0 | 0 | +0.00% | +0.00% | +0.00% | 0.0% | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 |
| t05-theta-60-40 | `t05-theta-60-40/20260928T014702-917d5042911b` | 0 | 0 | +0.00% | +0.00% | +0.00% | 0.0% | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 |
| t06-theta-52-48 | `t06-theta-52-48/20260928T014702-917d4fd6c89f` | 56 | 18 | -14.60% | -5.01% | -19.01% | 22.5% | +1.6 | +1.0 | -4.3 | -2.0 | -3.2 | -0.7 | +2.9 | -10.4 | -5.0 |
| t07-gate-on | `t07-gate-on/20260928T014804-918bb85c89bf` | 0 | 0 | +0.00% | +0.00% | +0.00% | 0.0% | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 |
| t08-plan-1r2r | `t08-plan-1r2r/20260928T014816-918eb6cd6922` | 0 | 0 | +0.00% | +0.00% | +0.00% | 0.0% | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 |
| t09-atr-stop | `t09-atr-stop/20260928T014818-918f2940cc43` | 0 | 0 | +0.00% | +0.00% | +0.00% | 0.0% | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 |
| t10-order-vol-first | `t10-order-vol-first/20260928T014818-918f304bd087` | 0 | 0 | +0.00% | +0.00% | +0.00% | 0.0% | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 |
| t11-nocandle-vol-on | `t11-nocandle-vol-on/20260928T014835-919312a70746` | 0 | 0 | +0.00% | +0.00% | +0.00% | 0.0% | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 |
| t12-hybrid-base | `t12-hybrid-base/20260928T014911-919b78c0368e` | 0 | 0 | +0.00% | +0.00% | +0.00% | 0.0% | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 |
| t13-hybrid-theta-60-40 | `t13-hybrid-theta-60-40/20260928T014934-91a0e06abe32` | 0 | 0 | +0.00% | +0.00% | +0.00% | 0.0% | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 |
| t14-candle-vol-off | `t14-candle-vol-off/20260928T014924-919e7b9a9ea4` | 1 | 0 | -3.00% | +0.00% | -3.00% | 4.0% | +0.0 | -3.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 |

Models: 
```
a7c4ef2e48ce6f9eb137a5efd3ab7252642f944a0534e1395f56e28f56977bdc  /home/wellington/workspace/mba-agents/mba-main/algo-suite/data/training/2026-09-28-h4-tuning-sweep/models/A-baseline-talib.json
0e7da0be00b53027fc4350abe5ffbcb0ac0a7f67ec3345d9dfd0c1c4403155b4  /home/wellington/workspace/mba-agents/mba-main/algo-suite/data/training/2026-09-28-h4-tuning-sweep/models/B-baseline-disabled.json
52ef933b8a5eb367e664585b590ae940bd4945d6fb13158663fbd66e7b5996fa  /home/wellington/workspace/mba-agents/mba-main/algo-suite/data/training/2026-09-28-h4-tuning-sweep/models/C-hybrid-talib.json
```

## H4 calibrated thresholds (11 variants) — job `2026-09-28-h4-tuning-sweep-q`

| variant | run id | trades | win% | Mar–Oct | Nov | full | max DD | 03 | 04 | 05 | 06 | 07 | 08 | 09 | 10 | 11 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| q10-base | `q10-base/20260928T015629-9201540dd070` | 100 | 32 | -12.10% | -1.33% | -13.27% | 21.0% | -0.7 | -2.6 | -1.0 | -9.1 | -4.6 | -2.1 | +7.9 | +0.2 | -1.3 |
| q10-vol-off | `q10-vol-off/20260928T015629-92015632ba0b` | 185 | 36 | -8.48% | -0.80% | -9.21% | 16.8% | -0.9 | -5.5 | -2.5 | -5.4 | +4.2 | -2.5 | +5.9 | -1.5 | -0.8 |
| q05-base | `q05-base/20260928T015629-920150be316a` | 87 | 30 | -8.92% | -4.09% | -12.65% | 18.4% | -0.7 | -3.0 | +2.0 | -9.1 | -4.6 | -2.1 | +5.6 | +3.5 | -4.1 |
| q15-base | `q15-base/20260928T015629-92015eaf2311` | 133 | 32 | -4.79% | -1.71% | -6.42% | 20.5% | -0.8 | -1.5 | -3.4 | -7.9 | -7.6 | +10.2 | +3.7 | +3.7 | -1.7 |
| q10-gate-on | `q10-gate-on/20260928T015629-9201570df1a9` | 16 | 25 | -20.23% | -4.76% | -23.98% | 26.1% | +0.8 | -4.4 | +3.4 | -9.7 | -1.6 | -5.7 | -7.7 | +3.5 | -4.8 |
| q10-plan-1r2r | `q10-plan-1r2r/20260928T015629-92015a2799cb` | 0 | 0 | +0.00% | +0.00% | +0.00% | 0.0% | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 |
| q10-atr-stop | `q10-atr-stop/20260928T015935-922ca17ded10` | 65 | 46 | +9.04% | -6.03% | +2.27% | 25.0% | -4.2 | +0.7 | -12.4 | +12.8 | +2.3 | -1.9 | +21.8 | -6.4 | -6.0 |
| q10-vol-0.8 | `q10-vol-0.8/20260928T020015-92361c5b236c` | 134 | 34 | -8.56% | -0.29% | -8.82% | 19.1% | -0.9 | -3.9 | -2.1 | -6.9 | -5.6 | +6.9 | +7.0 | -2.4 | -0.3 |
| q10-nocandle | `q10-nocandle/20260928T020143-924a7ef07eae` | 104 | 32 | -12.31% | -1.08% | -13.26% | 22.9% | -0.7 | -6.2 | -1.7 | -5.9 | -6.4 | -1.3 | +5.6 | +4.2 | -1.1 |
| q10-hybrid | `q10-hybrid/20260928T020319-9260c65844e9` | 109 | 34 | -15.81% | -1.16% | -16.79% | 22.9% | -0.7 | -6.2 | -1.3 | -7.7 | -6.1 | +0.7 | +4.7 | +0.2 | -1.2 |
| q10-hybrid-vol-off | `q10-hybrid-vol-off/20260928T020425-9270347ba8b3` | 199 | 39 | -8.33% | -0.62% | -8.90% | 19.7% | -0.7 | -8.6 | -2.7 | -5.6 | +3.3 | +3.2 | +2.7 | +0.5 | -0.6 |

Models: 
```
a7c4ef2e48ce6f9eb137a5efd3ab7252642f944a0534e1395f56e28f56977bdc  /home/wellington/workspace/mba-agents/mba-main/algo-suite/data/training/2026-09-28-h4-tuning-sweep-q/models/A-baseline-talib.json
0e7da0be00b53027fc4350abe5ffbcb0ac0a7f67ec3345d9dfd0c1c4403155b4  /home/wellington/workspace/mba-agents/mba-main/algo-suite/data/training/2026-09-28-h4-tuning-sweep-q/models/B-baseline-disabled.json
52ef933b8a5eb367e664585b590ae940bd4945d6fb13158663fbd66e7b5996fa  /home/wellington/workspace/mba-agents/mba-main/algo-suite/data/training/2026-09-28-h4-tuning-sweep-q/models/C-hybrid-talib.json
```

## Timeframes M15 / H1 / H2, fixed thresholds (9 variants) — job `2026-09-28-tf-sweep`

| variant | run id | trades | win% | Mar–Oct | Nov | full | max DD | 03 | 04 | 05 | 06 | 07 | 08 | 09 | 10 | 11 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| m15-candle-vol-on | `m15-candle-vol-on/20260928T015003-91a77837ef48` | 58 | 16 | -13.98% | -1.15% | -14.97% | 18.0% | -5.3 | +2.1 | +0.0 | -5.1 | -2.5 | -5.6 | +1.8 | +0.0 | -1.2 |
| m15-candle-vol-off | `m15-candle-vol-off/20260928T015003-91a775bf4315` | 69 | 19 | -14.82% | -1.15% | -15.81% | 18.8% | -8.0 | +2.1 | +0.0 | -6.1 | -2.5 | -2.8 | +1.8 | +0.0 | -1.2 |
| m15-hybrid-candle-vol-on | `m15-hybrid-candle-vol-on/20260928T015035-91af1515f2c4` | 58 | 16 | -13.98% | -1.15% | -14.97% | 18.0% | -5.3 | +2.1 | +0.0 | -5.1 | -2.5 | -5.6 | +1.8 | +0.0 | -1.2 |
| h1-candle-vol-on | `h1-candle-vol-on/20260928T015003-91a77811f738` | 18 | 44 | +11.45% | -2.46% | +8.71% | 8.0% | +4.8 | -5.0 | -1.0 | -1.3 | +5.5 | +9.8 | -0.9 | -0.3 | -2.5 |
| h1-candle-vol-off | `h1-candle-vol-off/20260928T015003-91a7788611df` | 33 | 39 | +8.06% | -2.62% | +5.23% | 11.9% | +3.0 | -0.4 | -2.3 | -1.2 | +5.5 | +8.5 | -0.2 | -4.5 | -2.6 |
| h1-hybrid-candle-vol-on | `h1-hybrid-candle-vol-on/20260928T015035-91af059f03ed` | 17 | 47 | +13.55% | -2.46% | +10.76% | 7.4% | +4.8 | -3.2 | -1.0 | -1.3 | +5.5 | +9.8 | -0.9 | -0.3 | -2.5 |
| h2-candle-vol-on | `h2-candle-vol-on/20260928T015551-91f890b7ef0d` | 0 | 0 | +0.00% | +0.00% | +0.00% | 0.0% | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 |
| h2-candle-vol-off | `h2-candle-vol-off/20260928T015641-92043d4cb4f6` | 0 | 0 | +0.00% | +0.00% | +0.00% | 0.0% | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 |
| h2-hybrid-candle-vol-on | `h2-hybrid-candle-vol-on/20260928T015909-92269eb06231` | 15 | 40 | +1.15% | -0.09% | +1.06% | 14.4% | +7.4 | +2.7 | +2.5 | -6.2 | +8.4 | -6.3 | -6.0 | +0.0 | -0.1 |

Models: 
```
80f012b99b7923784733f7ad6fc042ec14e3fac1b0da863593fe155c06dcac68  /home/wellington/workspace/mba-agents/mba-main/algo-suite/data/training/2026-09-28-tf-sweep/models/h1-baseline-talib.json
4220696d32cfd2c60f9821a2c5944f406b7f391b68fccd155ab498459a124d9a  /home/wellington/workspace/mba-agents/mba-main/algo-suite/data/training/2026-09-28-tf-sweep/models/h1-hybrid-talib.json
0cd126924f240314bd473763b7ad51297a99b257a6e94d113af407114a011511  /home/wellington/workspace/mba-agents/mba-main/algo-suite/data/training/2026-09-28-tf-sweep/models/h2-baseline-talib.json
cc19839fa4c5a0409078822a0167f572c7bf8b1a53f22387b4abbbe9dbde9aa7  /home/wellington/workspace/mba-agents/mba-main/algo-suite/data/training/2026-09-28-tf-sweep/models/h2-hybrid-talib.json
33f5cec038b8bdaa3fd18af44dfd3b3092c6e09a3f0b64ab9ac96c637d6f8758  /home/wellington/workspace/mba-agents/mba-main/algo-suite/data/training/2026-09-28-tf-sweep/models/m15-baseline-talib.json
e07a4b6e893aa381d7c134bf2358814f9d3e1152eeaa66c32b003226697addf4  /home/wellington/workspace/mba-agents/mba-main/algo-suite/data/training/2026-09-28-tf-sweep/models/m15-hybrid-talib.json
```

## H1 fixed-threshold variants (9) — job `2026-09-28-h1-tuning-sweep`

| variant | run id | trades | win% | Mar–Oct | Nov | full | max DD | 03 | 04 | 05 | 06 | 07 | 08 | 09 | 10 | 11 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| h1-atr-stop | `h1-atr-stop/20260928T021518-93082ce76869` | 11 | 18 | -7.11% | -1.63% | -8.99% | 22.5% | +12.1 | -6.2 | -6.3 | -1.1 | +2.0 | -0.5 | +2.1 | -8.0 | -1.6 |
| h1-atr-stop-hybrid | `h1-atr-stop-hybrid/20260928T022009-934c0d9e00bf` | 10 | 20 | -4.20% | -1.63% | -6.14% | 20.2% | +12.1 | -3.3 | -6.3 | -1.1 | +2.0 | -0.5 | +2.1 | -8.0 | -1.6 |
| h1-hybrid-vol-off | `h1-hybrid-vol-off/20260928T021550-930fa65aa410` | 31 | 45 | +15.01% | -2.62% | +12.01% | 10.7% | +3.0 | +1.5 | -2.3 | -1.2 | +5.6 | +8.5 | -0.2 | -0.3 | -2.6 |
| h1-gate-on | `h1-gate-on/20260928T021518-93082d4fbca9` | 3 | 67 | +3.12% | +0.00% | +3.12% | 5.9% | +0.0 | -3.2 | +0.1 | +0.0 | +0.0 | +6.3 | +0.0 | +0.0 | +0.0 |
| h1-theta-53-47 | `h1-theta-53-47/20260928T021518-93082eba325f` | 209 | 25 | -23.33% | -3.51% | -26.26% | 48.7% | +23.7 | +2.0 | -15.1 | -12.1 | -1.6 | +1.8 | -4.9 | -14.4 | -3.5 |
| h1-theta-57-43 | `h1-theta-57-43/20260928T021518-93082c234704` | 0 | 0 | +0.00% | +0.00% | +0.00% | 0.0% | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 |
| h1-plan-1r2r | `h1-plan-1r2r/20260928T021518-93082dbbe3f9` | 20 | 50 | +4.48% | -1.35% | +3.07% | 5.6% | -0.5 | -5.0 | +5.2 | -1.3 | +4.1 | +2.4 | +0.0 | -0.3 | -1.4 |
| h1-vol-0.8 | `h1-vol-0.8/20260928T021931-9343415445c7` | 21 | 52 | +14.80% | -2.46% | +11.98% | 8.0% | +4.8 | -4.9 | -1.0 | -1.3 | +5.5 | +9.8 | +2.0 | -0.3 | -2.5 |
| h1-vol-1.2 | `h1-vol-1.2/20260928T021935-934438479cdf` | 14 | 36 | +4.74% | -2.46% | +2.17% | 3.8% | +4.8 | -1.8 | -1.1 | -0.3 | +1.5 | +3.0 | -0.9 | -0.3 | -2.5 |

Models: 
```
80f012b99b7923784733f7ad6fc042ec14e3fac1b0da863593fe155c06dcac68  /home/wellington/workspace/mba-agents/mba-main/algo-suite/data/training/2026-09-28-h1-tuning-sweep/models/h1-baseline-talib.json
4220696d32cfd2c60f9821a2c5944f406b7f391b68fccd155ab498459a124d9a  /home/wellington/workspace/mba-agents/mba-main/algo-suite/data/training/2026-09-28-h1-tuning-sweep/models/h1-hybrid-talib.json
0cd126924f240314bd473763b7ad51297a99b257a6e94d113af407114a011511  /home/wellington/workspace/mba-agents/mba-main/algo-suite/data/training/2026-09-28-h1-tuning-sweep/models/h2-baseline-talib.json
cc19839fa4c5a0409078822a0167f572c7bf8b1a53f22387b4abbbe9dbde9aa7  /home/wellington/workspace/mba-agents/mba-main/algo-suite/data/training/2026-09-28-h1-tuning-sweep/models/h2-hybrid-talib.json
33f5cec038b8bdaa3fd18af44dfd3b3092c6e09a3f0b64ab9ac96c637d6f8758  /home/wellington/workspace/mba-agents/mba-main/algo-suite/data/training/2026-09-28-h1-tuning-sweep/models/m15-baseline-talib.json
e07a4b6e893aa381d7c134bf2358814f9d3e1152eeaa66c32b003226697addf4  /home/wellington/workspace/mba-agents/mba-main/algo-suite/data/training/2026-09-28-h1-tuning-sweep/models/m15-hybrid-talib.json
```

## H1 calibrated thresholds (8) — job `2026-09-28-h1-tuning-sweep-q`

| variant | run id | trades | win% | Mar–Oct | Nov | full | max DD | 03 | 04 | 05 | 06 | 07 | 08 | 09 | 10 | 11 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| h1-q05-base | `h1-q05-base/20260928T021822-933331dc1072` | 114 | 38 | +3.08% | -8.01% | -5.17% | 20.9% | +3.5 | -5.5 | -2.7 | -10.4 | +14.0 | +1.9 | +9.2 | -4.8 | -8.0 |
| h1-q10-base | `h1-q10-base/20260928T021822-933337cf84d4` | 196 | 33 | -26.59% | -4.59% | -29.96% | 41.2% | +15.2 | -4.9 | -7.9 | -17.7 | -2.3 | -5.5 | +15.7 | -17.3 | -4.6 |
| h1-q15-base | `h1-q15-base/20260928T022353-938044933b97` | 316 | 31 | -51.13% | -8.78% | -55.42% | 59.0% | +7.1 | -8.3 | +3.4 | -20.5 | +1.2 | -20.1 | +5.4 | -28.9 | -8.8 |
| h1-q10-vol-off | `h1-q10-vol-off/20260928T021822-93333008f294` | 392 | 37 | -47.41% | -2.56% | -48.99% | 56.1% | +13.2 | -18.0 | +6.1 | -24.2 | -8.3 | -12.5 | +15.0 | -23.7 | -2.6 |
| h1-q05-hybrid | `h1-q05-hybrid/20260928T021856-933b1e127597` | 117 | 36 | -1.94% | -8.29% | -10.07% | 21.7% | +0.5 | -4.7 | +4.2 | -13.1 | +8.7 | +1.3 | +6.0 | -3.1 | -8.3 |
| h1-q10-hybrid | `h1-q10-hybrid/20260928T021856-933afffc9174` | 204 | 33 | -19.86% | -7.54% | -25.91% | 38.4% | +15.5 | -12.0 | +0.9 | -15.9 | +5.7 | -11.8 | +20.2 | -17.2 | -7.5 |
| h1-q15-hybrid | `h1-q15-hybrid/20260928T022543-9399df1d512b` | 327 | 31 | -58.72% | -5.57% | -61.02% | 63.3% | +4.6 | -12.4 | +3.8 | -31.9 | -5.6 | -18.7 | +13.6 | -26.9 | -5.6 |
| h1-q10-hybrid-vol-off | `h1-q10-hybrid-vol-off/20260928T021857-933b2cdd0f8f` | 388 | 39 | -35.74% | -7.98% | -41.15% | 46.6% | +7.8 | -18.5 | +9.9 | -25.8 | +1.6 | -12.9 | +20.2 | -15.5 | -8.0 |

Models: 
```
80f012b99b7923784733f7ad6fc042ec14e3fac1b0da863593fe155c06dcac68  /home/wellington/workspace/mba-agents/mba-main/algo-suite/data/training/2026-09-28-h1-tuning-sweep-q/models/h1-baseline-talib.json
4220696d32cfd2c60f9821a2c5944f406b7f391b68fccd155ab498459a124d9a  /home/wellington/workspace/mba-agents/mba-main/algo-suite/data/training/2026-09-28-h1-tuning-sweep-q/models/h1-hybrid-talib.json
0cd126924f240314bd473763b7ad51297a99b257a6e94d113af407114a011511  /home/wellington/workspace/mba-agents/mba-main/algo-suite/data/training/2026-09-28-h1-tuning-sweep-q/models/h2-baseline-talib.json
cc19839fa4c5a0409078822a0167f572c7bf8b1a53f22387b4abbbe9dbde9aa7  /home/wellington/workspace/mba-agents/mba-main/algo-suite/data/training/2026-09-28-h1-tuning-sweep-q/models/h2-hybrid-talib.json
33f5cec038b8bdaa3fd18af44dfd3b3092c6e09a3f0b64ab9ac96c637d6f8758  /home/wellington/workspace/mba-agents/mba-main/algo-suite/data/training/2026-09-28-h1-tuning-sweep-q/models/m15-baseline-talib.json
e07a4b6e893aa381d7c134bf2358814f9d3e1152eeaa66c32b003226697addf4  /home/wellington/workspace/mba-agents/mba-main/algo-suite/data/training/2026-09-28-h1-tuning-sweep-q/models/m15-hybrid-talib.json
```

## Registered broad-window matrices through the immutable runner (plan-broad-window.yaml, fixed 0.55/0.45)

| cell | trades | return | max DD |
|---|---:|---:|---:|
| heikin-ashi-h4-disabled-volume-off | 1 | -3.00% | 4.0% |
| heikin-ashi-h4-disabled-volume-on | 0 | +0.00% | 0.0% |
| heikin-ashi-h4-talib-volume-off | 1 | -3.00% | 4.0% |
| heikin-ashi-h4-talib-volume-on | 0 | +0.00% | 0.0% |

Final immutable-input check (baseline): ok=True, errors=[]

| heikin-ashi-h4-hybrid-disabled-volume-off | 1 | -3.00% | 4.0% |
| heikin-ashi-h4-hybrid-disabled-volume-on | 0 | +0.00% | 0.0% |
| heikin-ashi-h4-hybrid-talib-volume-off | 1 | -3.00% | 4.0% |
| heikin-ashi-h4-hybrid-talib-volume-on | 0 | +0.00% | 0.0% |

Final immutable-input check (hybrid): ok=True, errors=[]

## Threshold calibration

H4 models: p_hat on the 99 January-2016 validation bars spans 0.517–0.539 (`2026-09-28-h4-tuning-sweep/h4-threshold-calibration.json`); H1 models 0.504–0.556 on 440 bars; H2 0.532–0.546; M15 0.466–0.530 (`2026-09-28-tf-sweep/tf-threshold-calibration.json`). Fixed 0.55/0.45 therefore never fires on H4 and fires long-only on about 2 % of H1 bars. Quantile thresholds (5/10/15 % per side of the validation distribution) were registered before any 2016-03+ outcome was viewed.

## Reading

- No variant is profitable on the untouched month, November 2016. Every variant that traded in November lost (−0.1 % to −8.8 %); the two zero-trade H2 cells and the gated H1 cell were flat.
- The only positive March..October returns are small-sample, low-frequency settings: H1 with fixed thresholds (17–33 long-only trades, +8 to +15 %) and the H4 ATR-stop variant (65 trades, +9 %). Each lost in November (−2.5 % and −6.0 %). Making the same H1 models trade more through calibrated symmetric thresholds turns the sign: 114 trades −5 %, 196 trades −30 %, 316 trades −55 %. Loss grows monotonically with trade count at every timeframe.
- The TA-Lib detector does not move the outcome: candle-on and candle-off pairs differ by less than 0.1 % at H4 and M15 (identical pattern-family probability ranges). The quote-activity gate reduces trades; at H4 it worsens every pair, at H1 (fixed thresholds) it removes a few losing trades.
- The regime gate is the worst or emptiest setting at every timeframe. The 1R/2R template plan is viable only with `min_reward_risk` 1.0 (H1: 20 trades, +4.5 % Mar..Oct, −1.4 % Nov); with 2.0 it vetoes every entry.
- Filter order (`t10-order-vol-first`) changes nothing: vetoes compose, so the same bars are blocked whichever filter blocks first.
- Picking the best March..October variant and reading November is the pre-declared test; it fails for the H4 pick (q10-atr-stop −6.0 %) and for the H1 pick (h1-hybrid-vol-off −2.6 %). With 51 trials, one or two positive development-window results are expected under the null.
