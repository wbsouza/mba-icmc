/**
 * The results database on the server: Node's built-in SQLite (`node:sqlite`, read-only).
 *
 * `Queryable` is the one seam the query layer needs, so `queries.ts` stays free of the
 * binding and the scenarios can exercise it over the fixture file exactly as production
 * does over a real build.
 */

import { DatabaseSync, type SQLInputValue } from "node:sqlite";
import { existsSync } from "node:fs";
import { SCHEMA_VERSION } from "../src/model/types.js";

export interface Queryable {
  rows<T>(sql: string, params?: SQLInputValue[]): T[];
  close(): void;
}

class NodeSqlite implements Queryable {
  constructor(private readonly db: DatabaseSync) {}

  rows<T>(sql: string, params: SQLInputValue[] = []): T[] {
    return this.db.prepare(sql).all(...params) as T[];
  }

  close(): void {
    this.db.close();
  }
}

/** Open a results.sqlite read-only, refusing a missing file or another schema version. */
export function openResultsDatabase(path: string): Queryable {
  if (!existsSync(path)) {
    throw new Error(`results database ${path} does not exist; build it with \`algo-analyze results-db build --out ${path}\``);
  }
  const db = new NodeSqlite(new DatabaseSync(path, { readOnly: true }));
  let versions: { version: number }[];
  try {
    versions = db.rows<{ version: number }>("SELECT version FROM schema_version");
  } catch (error) {
    db.close();
    throw new Error(`${path} is not a results database (no schema_version table): ${String(error)}`);
  }
  const version = versions[0]?.version;
  if (version !== SCHEMA_VERSION) {
    db.close();
    throw new Error(
      `results database schema version ${String(version)} is not the ${SCHEMA_VERSION} this server reads; rebuild it with the matching algo-analyze`,
    );
  }
  return db;
}
