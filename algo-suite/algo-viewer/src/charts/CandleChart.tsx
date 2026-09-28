import { useEffect, useRef } from "react";
import {
  CandlestickSeries,
  createChart,
  createSeriesMarkers,
  LineStyle,
  type IChartApi,
  type SeriesMarker,
  type UTCTimestamp,
} from "lightweight-charts";
import { canRenderCharts, chartColors, toTime } from "./support";
import type { EntryBar, TradePlan, TradeRow, TrailMove } from "../model/types";
import { EXIT_KIND_LABELS, money, price as fmtPrice, priceDecimals, when } from "../model/format";

interface Props {
  bars: EntryBar[];
  trade: TradeRow;
  plan: TradePlan | null;
  trailMoves: TrailMove[];
  dark: boolean;
}

/** Bar containing `iso`: the last bar whose start is at or before it (null when outside). */
export function barAt(bars: EntryBar[], iso: string, barMinutes: number): EntryBar | null {
  const t = new Date(iso).getTime();
  let hit: EntryBar | null = null;
  for (const bar of bars) {
    const start = new Date(bar.time).getTime();
    if (start <= t && t < start + barMinutes * 60_000) hit = bar;
  }
  return hit;
}

// Dark, saturated marker colours so the labels read on both themes.
const ENTRY_COLOR = "#0b4fbf";
const EXIT_COLOR = "#6a1b9a";

/** Bold plain-HTML entry/exit caption under the chart (readable whatever the canvas does). */
function ChartCaption({ trade }: { trade: TradeRow }) {
  const decimals = priceDecimals(trade.entry_price);
  return (
    <p className="chart-caption" data-testid="chart-caption">
      <span className="entry" style={{ color: ENTRY_COLOR }}>
        <b>Entry</b> {trade.direction} @ {fmtPrice(trade.entry_price, decimals)} on {when(trade.entry_time)}
      </span>
      <span className="exit" style={{ color: EXIT_COLOR }}>
        <b>Exit</b> {EXIT_KIND_LABELS[trade.exit_kind] ?? trade.exit_kind} @ {fmtPrice(trade.exit_price, decimals)} on {when(trade.exit_time)}
      </span>
      <span className={trade.profit >= 0 ? "up" : "down"}><b>P/L</b> {money(trade.profit)}</span>
    </p>
  );
}

/** The ±N bars around the entry with the entry, stop, targets, trail moves and exit marked. */
export function CandleChart({ bars, trade, plan, trailMoves, dark }: Props) {
  const host = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const element = host.current;
    if (element === null || !canRenderCharts() || bars.length === 0) return;
    const colors = chartColors(dark);
    const chart: IChartApi = createChart(element, {
      autoSize: true,
      layout: { background: { color: colors.bg }, textColor: colors.text, attributionLogo: false, fontSize: 13 },
      grid: { vertLines: { color: colors.grid }, horzLines: { color: colors.grid } },
      timeScale: { timeVisible: true, secondsVisible: false },
      // empty bands above and below the candles: the entry/exit labels are drawn there
      rightPriceScale: { borderColor: colors.grid, scaleMargins: { top: 0.22, bottom: 0.22 } },
    });
    const decimals = priceDecimals(trade.entry_price);
    const candles = chart.addSeries(CandlestickSeries, {
      upColor: "#1a8f4a", downColor: "#c0392b", borderVisible: false, wickUpColor: "#1a8f4a", wickDownColor: "#c0392b",
      priceLineVisible: false, lastValueVisible: false,
      priceFormat: { type: "price", precision: decimals, minMove: 10 ** -decimals },
    });
    candles.setData(bars.map((b) => ({ time: toTime(b.time), open: b.open, high: b.high, low: b.low, close: b.close })));
    candles.createPriceLine({ price: trade.entry_price, color: ENTRY_COLOR, lineWidth: 2, lineStyle: LineStyle.Solid, title: "entry" });
    candles.createPriceLine({ price: trade.exit_price, color: EXIT_COLOR, lineWidth: 2, lineStyle: LineStyle.Dashed, title: "exit" });
    if (plan) {
      candles.createPriceLine({ price: plan.stop_loss, color: "#c0392b", lineWidth: 1, lineStyle: LineStyle.Dotted, title: "stop" });
      plan.targets.forEach((target, i) => {
        candles.createPriceLine({ price: target.price, color: "#1a8f4a", lineWidth: 1, lineStyle: LineStyle.Dotted, title: `T${i + 1}` });
      });
    }
    for (const move of trailMoves) {
      candles.createPriceLine({ price: move.to_stop, color: "#e9a23b", lineWidth: 1, lineStyle: LineStyle.SparseDotted, title: "trail" });
    }
    // Labels live in the clear bands, never on a candle: the entry above the highest high
    // at its bar's time, the exit below the lowest low at its bar's time.
    const { top, bottom } = labelBands(bars);
    const markers: SeriesMarker<UTCTimestamp>[] = [];
    const entryBar = bars.find((b) => b.offset === 0);
    if (entryBar) {
      markers.push({
        time: toTime(entryBar.time), position: "atPriceMiddle", price: top, size: 2,
        color: ENTRY_COLOR, shape: trade.direction === "buy" ? "arrowUp" : "arrowDown",
        text: `ENTRY ${trade.direction.toUpperCase()} @ ${fmtPrice(trade.entry_price, decimals)}`,
      });
    }
    const exitBar = barAt(bars, trade.exit_time, barMinutesOf(bars));
    if (exitBar) {
      markers.push({
        time: toTime(exitBar.time), position: "atPriceMiddle", price: bottom, size: 2,
        color: EXIT_COLOR, shape: "circle",
        text: `EXIT ${(EXIT_KIND_LABELS[trade.exit_kind] ?? trade.exit_kind).toUpperCase()} @ ${fmtPrice(trade.exit_price, decimals)}`,
      });
    }
    createSeriesMarkers(candles, markers);
    chart.timeScale().fitContent();
    return () => chart.remove();
  }, [bars, trade, plan, trailMoves, dark]);
  if (bars.length === 0) {
    return <div className="chart-fallback" data-testid="no-bars">No entry bars stored for this run (build the database with --bars-root).</div>;
  }
  if (!canRenderCharts()) {
    return (
      <>
        <div className="chart-fallback" data-testid="chart-fallback">Candlestick chart unavailable in this host ({bars.length} bars).</div>
        <ChartCaption trade={trade} />
      </>
    );
  }
  return (
    <>
      <div ref={host} className="chart tall" />
      <ChartCaption trade={trade} />
    </>
  );
}

/** The prices at which the two labels sit: 12% of the bars' range above the highest high and below the lowest low. */
export function labelBands(bars: EntryBar[]): { top: number; bottom: number } {
  const highs = bars.map((b) => b.high);
  const lows = bars.map((b) => b.low);
  const high = Math.max(...highs);
  const low = Math.min(...lows);
  const pad = Math.max(high - low, Number.EPSILON) * 0.12;
  return { top: high + pad, bottom: low - pad };
}

function barMinutesOf(bars: EntryBar[]): number {
  const a = bars[0];
  const b = bars[1];
  if (a === undefined || b === undefined) return 60;
  return Math.max(1, Math.round((new Date(b.time).getTime() - new Date(a.time).getTime()) / 60_000));
}
