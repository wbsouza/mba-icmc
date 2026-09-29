/**
 * `algo-viewer` backend entry point.
 *
 *   node dist-server/server/main.js --db results.sqlite [--static dist] [--port 8787] [--host 127.0.0.1]
 *
 * Serves the JSON API over the results database and, with --static, the built React app
 * from the same origin so the page needs no proxy.
 */

import { pathToFileURL } from "node:url";
import { openResultsDatabase } from "./db.js";
import { startServer } from "./http.js";

export interface CliOptions {
  db: string;
  static: string | undefined;
  port: number;
  host: string;
}

/** Parse `--key value` pairs; fail fast on an unknown flag or a missing --db. */
export function parseArgs(argv: string[]): CliOptions {
  const options: CliOptions = { db: "", static: undefined, port: 8787, host: "127.0.0.1" };
  for (let i = 0; i < argv.length; i += 2) {
    const flag = argv[i];
    const value = argv[i + 1];
    if (value === undefined) throw new Error(`flag ${String(flag)} needs a value`);
    switch (flag) {
      case "--db": options.db = value; break;
      case "--static": options.static = value; break;
      case "--port": options.port = Number(value); break;
      case "--host": options.host = value; break;
      default: throw new Error(`unknown flag ${String(flag)}; known: --db --static --port --host`);
    }
  }
  if (options.db === "") throw new Error("--db <results.sqlite> is required (build one with `algo-analyze results-db build`)");
  if (!Number.isInteger(options.port) || options.port < 0) throw new Error(`--port must be a non-negative integer, got ${String(options.port)}`);
  return options;
}

async function main(): Promise<void> {
  const options = parseArgs(process.argv.slice(2));
  const db = openResultsDatabase(options.db);
  const running = await startServer({ db, staticDir: options.static, host: options.host, port: options.port });
  console.log(`algo-viewer: ${options.db} -> ${running.url}${options.static === undefined ? "/api/runs (API only)" : "/"}`);
  const stop = () => { void running.close().then(() => { db.close(); process.exit(0); }); };
  process.on("SIGINT", stop);
  process.on("SIGTERM", stop);
}

// Only run when executed as a program (not when the tests import parseArgs).
const entry = process.argv[1];
if (entry !== undefined && import.meta.url === pathToFileURL(entry).href) {
  main().catch((error: unknown) => {
    console.error(`error: ${error instanceof Error ? error.message : String(error)}`);
    process.exit(2);
  });
}
