interface Props {
  onFile: (file: File) => void;
  error: string | null;
  busy: boolean;
}

/** Shown when no results.sqlite sits next to index.html: pick one from disk. */
export function DbPicker({ onFile, error, busy }: Props) {
  return (
    <div className="picker panel">
      <h2>Open a results database</h2>
      <p>
        Build one with <code>algo-analyze results-db build --runs-root DIR --out results.sqlite</code>, then pick
        it here. Placing it next to <code>index.html</code> as <code>results.sqlite</code> loads it automatically.
      </p>
      <input type="file" accept=".sqlite,.db,.sqlite3" aria-label="Results database file" disabled={busy}
        onChange={(e) => { const f = e.target.files?.[0]; if (f) onFile(f); }} />
      {busy ? <p className="muted">Loading…</p> : null}
      {error ? <p className="error">{error}</p> : null}
    </div>
  );
}
