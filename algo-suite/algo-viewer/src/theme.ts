/** Light by default, dark on request; the choice is a per-browser convenience only. */

export type Theme = "light" | "dark";
const KEY = "algo-viewer-theme";

export function initialTheme(): Theme {
  try {
    const saved = window.localStorage.getItem(KEY);
    if (saved === "dark" || saved === "light") return saved;
  } catch {
    // storage may be unavailable (private window); fall through to the default
  }
  return "light";
}

export function applyTheme(theme: Theme): void {
  document.documentElement.dataset["theme"] = theme;
  try {
    window.localStorage.setItem(KEY, theme);
  } catch {
    // a blocked storage just means the choice is not remembered
  }
}
