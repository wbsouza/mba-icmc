/** A tiny hash router: `#/runs`, `#/compare/<id,id>`, `#/run/<id>`, `#/run/<id>/trade/<tid>`. */

export type Route =
  | { view: "runs" }
  | { view: "compare"; runIds: string[] }
  | { view: "run"; runId: string; tradeId: string | null };

export function parseRoute(hash: string): Route {
  const parts = hash.replace(/^#\/?/, "").split("/").filter((p) => p !== "");
  const [head, a, b, c] = parts;
  if (head === "compare") return { view: "compare", runIds: a ? a.split(",").filter((s) => s !== "") : [] };
  if (head === "run" && a !== undefined) return { view: "run", runId: a, tradeId: b === "trade" && c !== undefined ? c : null };
  return { view: "runs" };
}

export function routeHash(route: Route): string {
  switch (route.view) {
    case "runs":
      return "#/runs";
    case "compare":
      return `#/compare/${route.runIds.join(",")}`;
    case "run":
      return route.tradeId === null ? `#/run/${route.runId}` : `#/run/${route.runId}/trade/${route.tradeId}`;
  }
}
