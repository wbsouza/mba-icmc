import { useEffect, useRef } from "react";
import { createChart, HistogramSeries, type IChartApi, type UTCTimestamp } from "lightweight-charts";
import { canRenderCharts, chartColors } from "./support";
import type { MonthlyReturn } from "../model/types";

const UP = "#1a8f4a";
const DOWN = "#c0392b";

export interface MonthlyBar {
  month: string;
  value: number;
  tone: "up" | "down";
}

/** Pure: one bar per month, coloured by the sign of the return (zero counts as up). */
export function monthlyBars(months: readonly MonthlyReturn[]): MonthlyBar[] {
  return months.map((m) => ({ month: m.month, value: m.return_pct, tone: m.return_pct >= 0 ? "up" : "down" }));
}

function monthTime(month: string): UTCTimestamp {
  return Math.floor(new Date(`${month}-01T00:00:00Z`).getTime() / 1000) as UTCTimestamp;
}

/** Month-by-month returns as a histogram: green above zero, red below. */
export function MonthlyBarsChart({ months, dark }: { months: MonthlyReturn[]; dark: boolean }) {
  const host = useRef<HTMLDivElement>(null);
  const bars = monthlyBars(months);
  useEffect(() => {
    const element = host.current;
    if (element === null || !canRenderCharts() || bars.length === 0) return;
    const colors = chartColors(dark);
    const chart: IChartApi = createChart(element, {
      autoSize: true,
      layout: { background: { color: colors.bg }, textColor: colors.text, attributionLogo: false, fontSize: 13 },
      grid: { vertLines: { color: colors.grid }, horzLines: { color: colors.grid } },
      timeScale: { timeVisible: false },
      rightPriceScale: { borderColor: colors.grid, scaleMargins: { top: 0.15, bottom: 0.15 } },
      localization: { priceFormatter: (v: number) => `${v.toFixed(2)}%` },
    });
    const series = chart.addSeries(HistogramSeries, { priceLineVisible: false, lastValueVisible: false, base: 0 });
    series.setData(bars.map((b) => ({ time: monthTime(b.month), value: b.value, color: b.tone === "up" ? UP : DOWN })));
    series.createPriceLine({ price: 0, color: colors.text, lineWidth: 1, axisLabelVisible: false, title: "" });
    chart.timeScale().fitContent();
    return () => chart.remove();
  }, [bars, dark]);
  if (!canRenderCharts()) {
    return (
      <ul className="chart-fallback" data-testid="monthly-bars">
        {bars.map((b) => <li key={b.month} data-tone={b.tone}>{b.month} {b.value >= 0 ? "+" : ""}{b.value.toFixed(2)}%</li>)}
      </ul>
    );
  }
  return <div ref={host} className="chart small" />;
}
