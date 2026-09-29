import { useEffect, useRef } from "react";
import { createChart, LineSeries, type IChartApi, type LineData, type UTCTimestamp } from "lightweight-charts";
import { canRenderCharts, chartColors, toTime } from "./support";

export interface LineSeriesSpec {
  id: string;
  label: string;
  color: string;
  points: { time: string; value: number }[];
}

interface Props {
  series: LineSeriesSpec[];
  dark: boolean;
  /** Fraction of the height reserved for a secondary pane, e.g. the drawdown. */
  small?: boolean;
  priceFormat?: "price" | "percent";
}

/** Several lines on one time axis (equity overlays, drawdown). */
export function LineChart({ series, dark, small = false, priceFormat = "price" }: Props) {
  const host = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const element = host.current;
    if (element === null || !canRenderCharts()) return;
    const colors = chartColors(dark);
    const chart: IChartApi = createChart(element, {
      autoSize: true,
      layout: { background: { color: colors.bg }, textColor: colors.text, attributionLogo: false },
      grid: { vertLines: { color: colors.grid }, horzLines: { color: colors.grid } },
      timeScale: { timeVisible: true, secondsVisible: false },
      rightPriceScale: { borderColor: colors.grid },
      localization: priceFormat === "percent" ? { priceFormatter: (v: number) => `${v.toFixed(2)}%` } : {},
    });
    for (const spec of series) {
      const line = chart.addSeries(LineSeries, { color: spec.color, lineWidth: 2, title: spec.label, priceLineVisible: false, lastValueVisible: false });
      const data: LineData<UTCTimestamp>[] = dedupe(spec.points).map((p) => ({ time: toTime(p.time), value: p.value }));
      line.setData(data);
    }
    chart.timeScale().fitContent();
    return () => chart.remove();
  }, [series, dark, priceFormat]);
  if (!canRenderCharts()) {
    return <div className="chart-fallback" data-testid="chart-fallback">Chart unavailable in this host ({series.length} series).</div>;
  }
  return <div ref={host} className={small ? "chart small" : "chart"} />;
}

/** lightweight-charts wants strictly increasing times; keep the last sample of each second. */
function dedupe(points: { time: string; value: number }[]): { time: string; value: number }[] {
  const out: { time: string; value: number }[] = [];
  let last = Number.NEGATIVE_INFINITY;
  for (const p of points) {
    const t = toTime(p.time);
    if (t > last) {
      out.push(p);
      last = t;
    } else {
      out[out.length - 1] = p;
    }
  }
  return out;
}
