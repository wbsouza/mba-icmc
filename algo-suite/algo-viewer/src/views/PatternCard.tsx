import type { PatternInfo } from "../model/patterns";
import { TALIB_FUNCTIONS_URL } from "../model/patterns";

/** One candlestick pattern: title, direction, description, reference and TA-Lib links. */
export function PatternCard({ pattern }: { pattern: PatternInfo }) {
  return (
    <div className="pattern-card" data-testid="pattern-card" data-pattern={pattern.name}>
      <div className="title">
        <span className="name">{pattern.title}</span>
        <span className={`badge ${pattern.direction === "bullish" ? "buy" : "sell"}`}>{pattern.direction}</span>
      </div>
      <p>{pattern.description}</p>
      <p className="links">
        <a href={pattern.reference_url} target="_blank" rel="noreferrer">Reference</a>
        {" · "}
        <a href={TALIB_FUNCTIONS_URL} target="_blank" rel="noreferrer">TA-Lib {pattern.talib_function}</a>
      </p>
    </div>
  );
}
