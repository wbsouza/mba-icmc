import { useEffect, useState, type DependencyList } from "react";

export interface AsyncState<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
}

/** Run an async loader when `deps` change; a stale result never overwrites a newer one. */
export function useAsync<T>(load: () => Promise<T>, deps: DependencyList): AsyncState<T> {
  const [state, setState] = useState<AsyncState<T>>({ data: null, error: null, loading: true });
  useEffect(() => {
    let live = true;
    setState({ data: null, error: null, loading: true });
    load().then(
      (data) => { if (live) setState({ data, error: null, loading: false }); },
      (error: unknown) => { if (live) setState({ data: null, error: error instanceof Error ? error.message : String(error), loading: false }); },
    );
    return () => { live = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- deps are the caller's cache key
  }, deps);
  return state;
}

export function Pending({ state, label }: { state: AsyncState<unknown>; label: string }) {
  if (state.loading) return <p className="muted" data-testid="loading">Loading {label}…</p>;
  if (state.error !== null) return <p className="error">{label}: {state.error}</p>;
  return null;
}
