import type { ApiClient, PatternExample } from "../api/client";
import { useAsync } from "../api/useAsync";
import type { PatternInfo } from "../model/patterns";
import { SCHEMATIC_HEIGHT, SCHEMATIC_WIDTH, schematicShapes, TALIB_FUNCTIONS_URL } from "../model/patterns";
import { money, when } from "../model/format";

/** The drawn schematic: one rect per candle body, one line per wick, in the card's colours. */
export function PatternSchematic({ pattern }: { pattern: PatternInfo }) {
  const shapes = schematicShapes(pattern.schematic);
  return (
    <figure className="schematic">
      <svg width={SCHEMATIC_WIDTH} height={SCHEMATIC_HEIGHT} viewBox={`0 0 ${SCHEMATIC_WIDTH} ${SCHEMATIC_HEIGHT}`} role="img" aria-label={`${pattern.title} schematic`}>
        {shapes.map((s, i) => (
          <g key={i} className={s.up ? "candle up" : "candle down"}>
            <line x1={s.wick.x} x2={s.wick.x} y1={s.wick.y1} y2={s.wick.y2} />
            <rect x={s.body.x} y={s.body.y} width={s.body.width} height={s.body.height} />
          </g>
        ))}
      </svg>
      <figcaption>{pattern.caption}</figcaption>
    </figure>
  );
}

function Examples({ api, pattern }: { api: ApiClient; pattern: PatternInfo }) {
  const state = useAsync<PatternExample[]>(() => api.patternExamples(pattern.name, 3), [api, pattern.name]);
  if (state.loading) return <p className="examples muted">Looking for examples…</p>;
  if (state.error !== null) return <p className="examples error">Examples: {state.error}</p>;
  const examples = state.data ?? [];
  return (
    <p className="examples" data-testid="pattern-examples">
      <span className="muted">Example from our runs: </span>
      {examples.length === 0 ? <span className="muted">no example in this database</span> : examples.map((e, i) => (
        <span key={`${e.run_id}/${e.trade_id}`}>
          {i > 0 ? " · " : ""}
          <a href={`#/run/${e.run_id}/trade/${e.trade_id}`}>
            {e.direction} {when(e.entry_time)} ({money(e.profit)})
          </a>
        </span>
      ))}
    </p>
  );
}

interface Props {
  pattern: PatternInfo;
  /** With a client the card also links real trades whose entry carried the pattern. */
  api?: ApiClient | undefined;
}

/** One candlestick pattern: schematic, title, direction, description, reference, TA-Lib and examples. */
export function PatternCard({ pattern, api }: Props) {
  return (
    <div className="pattern-card" data-testid="pattern-card" data-pattern={pattern.name}>
      <div className="row">
        <PatternSchematic pattern={pattern} />
        <div>
          <div className="title">
            <span className="name">{pattern.title}</span>
            <span className={`badge ${pattern.direction === "bullish" ? "buy" : "sell"}`}>{pattern.direction}</span>
          </div>
          <p>{pattern.description}</p>
        </div>
      </div>
      <p className="links">
        <a href={pattern.reference_url} target="_blank" rel="noreferrer">Reference</a>
        {" · "}
        <a href={TALIB_FUNCTIONS_URL} target="_blank" rel="noreferrer">TA-Lib {pattern.talib_function}</a>
      </p>
      {api ? <Examples api={api} pattern={pattern} /> : null}
    </div>
  );
}
