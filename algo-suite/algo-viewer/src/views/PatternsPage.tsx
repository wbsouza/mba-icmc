import { PATTERNS } from "../model/patterns";
import { PatternCard } from "./PatternCard";

/** The static reference page: every pattern F3 can name, with its card. */
export function PatternsPage() {
  return (
    <section className="panel" aria-label="Patterns">
      <h2>Candlestick patterns F3 recognises</h2>
      <p className="muted">
        The chain's F3 filter names one of these six patterns on a closed bar (TA-Lib detectors, see
        perception/candlestick.py); the trade drawer shows the same card when a pattern was part of an entry.
      </p>
      <div className="pattern-grid">
        {PATTERNS.map((p) => <PatternCard key={p.name} pattern={p} />)}
      </div>
    </section>
  );
}
