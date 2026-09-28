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
import { priceDecimals } from "../model/format";

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

/** The ±N bars around the entry with the entry, stop, targets, trail moves and exit marked. */
export function CandleChart({ bars, trade, plan, trailMoves, dark }: Props) {
  const host = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const element = host.current;
    if (element === null || !canRenderCharts() || bars.length === 0) return;
    const colors = chartColors(dark);
    const chart: IChartApi = createChart(element, {
      autoSize: true,
      layout: { background: { color: colors.bg }, textColor: colors.text, attributionLogo: false },
      grid: { vertLines: { color: colors.grid }, horzLines: { color: colors.grid } },
      timeScale: { timeVisible: true, secondsVisible: false },
      rightPriceScale: { borderColor: colors.grid },
    });
    const decimals = priceDecimals(trade.entry_price);
    const candles = chart.addSeries(CandlestickSeries, {
      upColor: "#1a8f4a", downColor: "#c0392b", borderVisible: false, wickUpColor: "#1a8f4a", wickDownColor: "#c0392b",
      priceLineVisible: false, lastValueVisible: false,
      priceFormat: { type: "price", precision: decimals, minMove: 10 ** -decimals },
    });
    candles.setData(bars.map((b) => ({ time: toTime(b.time), open: b.open, high: b.high, low: b.low, close: b.close })));
    candles.createPriceLine({ price: trade.entry_price, color: "#1f6feb", lineWidth: 2, lineStyle: LineStyle.Solid, title: "entry" });
    candles.createPriceLine({ price: trade.exit_price, color: "#8e5ea2", lineWidth: 1, lineStyle: LineStyle.Dashed, title: "exit" });
    if (plan) {
      candles.createPriceLine({ price: plan.stop_loss, color: "#c0392b", lineWidth: 1, lineStyle: LineStyle.Dotted, title: "stop" });
      plan.targets.forEach((target, i) => {
        candles.createPriceLine({ price: target.price, color: "#1a8f4a", lineWidth: 1, lineStyle: LineStyle.Dotted, title: `T${i + 1}` });
      });
    }
    for (const move of trailMoves) {
      candles.createPriceLine({ price: move.to_stop, color: "#e9a23b", lineWidth: 1, lineStyle: LineStyle.SparseDotted, title: "trail" });
    }
    const markers: SeriesMarker<UTCTimestamp>[] = [];
    const entryBar = bars.find((b) => b.offset === 0);
    if (entryBar) {
      markers.push({
        time: toTime(entryBar.time), position: trade.direction === "buy" ? "belowBar" : "aboveBar",
        color: "#1f6feb", shape: trade.direction === "buy" ? "arrowUp" : "arrowDown", text: `${trade.direction} @ ${trade.entry_price}`,
      });
    }
    const exitBar = barAt(bars, trade.exit_time, barMinutesOf(bars));
    if (exitBar) {
      markers.push({ time: toTime(exitBar.time), position: "aboveBar", color: "#8e5ea2", shape: "circle", text: `exit ${trade.exit_kind}` });
    }
    createSeriesMarkers(candles, markers);
    chart.timeScale().fitContent();
    return () => chart.remove();
  }, [bars, trade, plan, trailMoves, dark]);
  if (bars.length === 0) {
    return <div className="chart-fallback" data-testid="no-bars">No entry bars stored for this run (build the database with --bars-root).</div>;
  }
  if (!canRenderCharts()) {
    return <div className="chart-fallback" data-testid="chart-fallback">Candlestick chart unavailable in this host ({bars.length} bars).</div>;
  }
  return <div ref={host} className="chart" />;
}

function barMinutesOf(bars: EntryBar[]): number {
  const a = bars[0];
  const b = bars[1];
  if (a === undefined || b === undefined) return 60;
  return Math.max(1, Math.round((new Date(b.time).getTime() - new Date(a.time).getTime()) / 60_000));
}
