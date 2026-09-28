/** Shared chart plumbing: whether the host can draw, colours, and time conversion. */

import type { UTCTimestamp } from "lightweight-charts";

/** lightweight-charts needs a 2D canvas; jsdom (the test host) has none. */
export function canRenderCharts(): boolean {
  if (typeof document === "undefined") return false;
  try {
    const canvas = document.createElement("canvas");
    return typeof canvas.getContext === "function" && canvas.getContext("2d") !== null;
  } catch {
    return false;
  }
}

export function toTime(iso: string): UTCTimestamp {
  return Math.floor(new Date(iso).getTime() / 1000) as UTCTimestamp;
}

export const SERIES_COLORS = [
  "#1f6feb", "#d1495b", "#2a9d8f", "#e9a23b", "#8e5ea2", "#3f88c5", "#f4845f", "#5c946e",
];

export function seriesColor(index: number): string {
  return SERIES_COLORS[index % SERIES_COLORS.length] ?? "#1f6feb";
}

export function chartColors(dark: boolean): { text: string; grid: string; bg: string } {
  return dark
    ? { text: "#9aa7b5", grid: "#2a3441", bg: "#171e27" }
    : { text: "#5b6573", grid: "#e6e9ee", bg: "#ffffff" };
}
