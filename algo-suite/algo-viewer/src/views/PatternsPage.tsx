import type { ApiClient } from "../api/client";
import { PATTERNS } from "../model/patterns";
import { PatternCard } from "./PatternCard";

/** The reference page: every pattern F3 can name, with its card and real examples. */
export function PatternsPage({ api }: { api?: ApiClient | undefined }) {
  return (
    <section className="panel" aria-label="Patterns">
      <h2>Candlestick patterns F3 recognises</h2>
      <p className="muted">
        The chain's F3 filter names one of these six patterns on a closed bar (TA-Lib detectors, see
        perception/candlestick.py); the trade drawer shows the same card when a pattern was part of an entry.
      </p>
      <div className="pattern-grid">
        {PATTERNS.map((p) => <PatternCard key={p.name} pattern={p} api={api} />)}
      </div>
    </section>
  );
}
