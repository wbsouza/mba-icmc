/** The fixture database: tests/fixtures/results.sqlite, built by build_fixture.py. */

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import type { Database } from "sql.js";
import { openDatabase } from "../../src/db/loader";

export const FIXTURE_RUN_ID = "20260928T010000-fixture";

export function fixturePath(): string {
  return join(dirname(fileURLToPath(import.meta.url)), "..", "fixtures", "results.sqlite");
}

export function fixtureBytes(): Uint8Array {
  return new Uint8Array(readFileSync(fixturePath()));
}

let cached: Promise<Database> | null = null;

/** One open handle per test process (the database is read-only for the scenarios). */
export function fixtureDatabase(): Promise<Database> {
  cached ??= openDatabase(fixtureBytes());
  return cached;
}
