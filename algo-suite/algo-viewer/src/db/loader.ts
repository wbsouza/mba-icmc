/**
 * Opening a results database in the browser (or under Node for the tests) with sql.js.
 *
 * The WASM binary is located by the caller: the browser entry passes the bundled asset
 * URL, the tests pass nothing and sql.js finds it next to its own module.
 */

import initSqlJs from "sql.js";
import type { BindParams, Database, SqlJsStatic } from "sql.js";
import { SCHEMA_VERSION } from "../model/types";

let sqlJs: Promise<SqlJsStatic> | null = null;

export type LocateFile = (file: string) => string;

function engine(locateFile?: LocateFile): Promise<SqlJsStatic> {
  sqlJs ??= initSqlJs(locateFile ? { locateFile } : {});
  return sqlJs;
}

/** Column/value result -> array of plain objects typed by the caller. */
export function rows<T>(db: Database, sql: string, params?: BindParams): T[] {
  const result = db.exec(sql, params);
  const first = result[0];
  if (first === undefined) return [];
  return first.values.map((values) => {
    const out: Record<string, unknown> = {};
    first.columns.forEach((column, i) => {
      out[column] = values[i];
    });
    return out as T;
  });
}

/** Open the bytes of a results.sqlite, refusing any other schema version. */
export async function openDatabase(bytes: Uint8Array, locateFile?: LocateFile): Promise<Database> {
  const SQL = await engine(locateFile);
  const db = new SQL.Database(bytes);
  let versions: { version: number }[];
  try {
    versions = rows<{ version: number }>(db, "SELECT version FROM schema_version");
  } catch (error) {
    db.close();
    throw new Error(
      `This file is not a results database (no schema_version table): ${String(error)}. ` +
        "Build one with `algo-analyze results-db build`.",
    );
  }
  const version = versions[0]?.version;
  if (version !== SCHEMA_VERSION) {
    db.close();
    throw new Error(
      `results database schema version ${String(version)} is not the ${SCHEMA_VERSION} this viewer reads; ` +
        "rebuild it with the matching algo-analyze.",
    );
  }
  return db;
}

/**
 * The `results.sqlite` published next to index.html, or null when there is none
 * (a 404, an HTML fallback page, or a file:// origin where fetch is refused).
 */
export async function fetchBundledDatabase(url = "./results.sqlite"): Promise<Uint8Array | null> {
  try {
    const response = await fetch(url);
    if (!response.ok) return null;
    const type = response.headers.get("content-type") ?? "";
    if (type.includes("text/html")) return null;
    const buffer = await response.arrayBuffer();
    return buffer.byteLength > 0 ? new Uint8Array(buffer) : null;
  } catch {
    return null;
  }
}
