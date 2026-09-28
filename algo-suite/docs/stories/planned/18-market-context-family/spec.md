# Story 18 — exogenous market context family: intermarket and commodity signals (planned)

Status: planned, recorded 2026-09-28 for later experiments. Owner: unassigned. No code, data
download, model or simulation is part of this story yet. Baseline inspected: `main` at `f438156`.

## User story

As the researcher, I want a second exogenous feature family next to the news family, built from
other markets (gold, oil, equities, volatility, yields, agricultural and fertilizer inputs), so that
the thesis question "does an exogenous signal improve the price chain?" is answered for a signal
class with a documented causal channel to the currency, not only for news counts.

## Motivation

Laïdi (2008), *Currency Trading and Intermarket Analysis*, describes the channels: gold–dollar
inverse relation (ch. 1), oil and the dollar (ch. 2), risk appetite and carry (ch. 5), yield curves
and the gold/oil ratio (ch. 6), commodity cycles and commodity currencies (ch. 8). The session-2
result (story 15) is that the GDELT news family adds nothing measurable to the price chain at H1 or
H4; an intermarket family is the natural next test and reuses the whole F7 machinery (feature
families, training splits, January calibration, registered cells, paired bootstrap).

Agricultural inputs matter because food production depends on the three macronutrients (NPK):
nitrogen from natural gas, phosphate from rock, potash from mines. Soils under intensive use need
replenishment every season (FAO and World Bank reports on nutrient depletion and fertilizer
import dependence to be cited when the story is written up). The three legs have different price
drivers and different currency exposures, so they are not one index.

## Design

### Feature tiers, by data horizon (the horizon decides what F7 may consume)

| tier | series | frequency | source | role |
|---|---|---|---|---|
| A | gold, silver, copper, Brent, WTI, natural gas, S&P 500, DAX, VIX, AUD/JPY | hourly | Dukascopy CFDs and pairs (adapter exists) | F7 features: lagged 1-bar/1-day/5-day log returns, 60-day z-scores, gold/oil ratio and its 20-day change, sign agreement with EUR/USD |
| B | corn, wheat, soybeans, sugar, coffee, cocoa; CRB/GSCI; fertilizer producers (Nutrien, Mosaic, CF, Yara, K+S, ICL); US 2y/10y, DE 2y | daily | Stooq / Yahoo, FRED, ECB (new adapters) | daily-lagged context features (value known at the previous trading day's close) |
| C | urea, DAP, potash (World Bank Pink Sheet, FRED `PPOTASHUSDM`), FAO food index, IMF commodity indices, rare-earth quotes | monthly | World Bank, FAO, FRED, USGS | context plots and regime labels only; never F7 features (twelve observations per test year) |

### NPK, the three legs

| leg | made from | price driver | main exporters | currency exposure | tradable proxy at our horizon |
|---|---|---|---|---|---|
| N (urea, ammonia) | natural gas (Haber–Bosch) | gas price, plant outages, China export policy | Russia, Qatar, China, Egypt, US | RUB, QAR, USD; Europe as gas importer | natural gas hourly; CF Industries daily |
| P (DAP, MAP, rock) | phosphate rock + sulphur + ammonia | rock reserves (Morocco ≈ 70 %), sulphur, gas | Morocco, China, Russia, US | MAD, CNY, RUB | Mosaic daily |
| K (potash, KCl) | mined evaporites | annual contracts with China and India; cartel history (BPC break-up 2013) | Canada, Russia, Belarus | CAD, RUB, BYN | Nutrien daily |

Demand side for all three: planted acreage and grain prices (tier B), which lead fertilizer prices
by months. For EUR/USD only the N leg has a channel (Europe imports gas) and only in years when gas
moves the euro; 2016 is not such a year. Potash sat at the bottom of its cycle in 2016 (≈ 220 USD/t,
flat), so it is uninformative in the current test window.

### Causality rules

- Every feature is computed from bars or observations closed before the decision bar (same rule
  as the news family: value known at decision time, forward-filled, never the same bar).
- Daily and monthly series are aligned to their publication time, not their reference period.
- The training/validation/test split, the January-2016 quantile calibration and the untouched
  months are the session-2 protocol (story 15), unchanged.

### Arms (one registered cell set, both clocks)

| arm | families |
|---|---|
| price-only | trend, indicator, pattern (session-2 `h1-q10-base`, `h4-q10-base`) |
| price + context A | + intermarket (tier A) |
| price + context A+B | + intermarket (tiers A and B) |
| price + context + news | + intermarket + news |

Primary comparison: price + context A versus price-only at H1, paired daily equity on the untouched
months (stationary bootstrap, block 4/2, 999 resamples, seed 42). Everything else secondary. Trial
count registered before any cell runs.

### Commodity-currency follow-up (separate story when the prices are downloaded)

EUR/USD is not a commodity currency; the direct channels are CAD (oil, potash, lumber), AUD (iron
ore, copper, gold), NZD (dairy), NOK (oil), BRL (soybeans, iron ore, NPK import bill), ZAR (metals).
The same family applies to USD/CAD and AUD/USD first (Dukascopy M1, same pipeline as USD/JPY;
`pip_value_per_lot` in account currency).

## Out of scope

- Rare-earth prices: no liquid daily series (quarterly vendor quotes); literature mention only.
- Monthly fertilizer and food indices as F7 features (tier C): plotted, not modelled.
- Any live or paper trading decision.

## Acceptance (when the story is executed)

- Data inventory with exact instrument names, coverage 2015-03..2017-02 and checksums.
- Feature builder for the intermarket family with Gherkin scenarios (causality: a feature never
  reads a bar at or after the decision bar; alignment of daily/monthly series to publication time).
- Registration in the job README and Chapter 4 before any cell runs; results, paired inference and
  a reproduction check as in story 15.
- Chapter 2: one paragraph on intermarket channels and the NPK input chain with sources; Chapter 5:
  the family named as the next exogenous test, with Laïdi (2008) as the reference.

## References to add to the bibliography

- Laïdi, A. (2008). *Currency Trading and Intermarket Analysis: How to Profit from the Shifting
  Currents in Global Markets*. Wiley.
- World Bank Commodity Price Data (Pink Sheet), monthly fertilizer series.
- FAO, *The State of Food and Agriculture* / *World fertilizer trends and outlook* (nutrient
  depletion and fertilizer demand).
- FRED series for yields (`DGS2`, `DGS10`) and potash (`PPOTASHUSDM`).
