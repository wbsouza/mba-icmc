/** One backend per test process, serving the fixture database on a free port. */

import { AfterAll, BeforeAll } from "@cucumber/cucumber";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { ApiClient } from "../../src/api/client";
import { openResultsDatabase, type Queryable } from "../../server/db";
import { startServer, type RunningServer } from "../../server/http";

export const FIXTURE_RUN_ID = "20260928T010000-fixture";

export function fixturePath(): string {
  return join(dirname(fileURLToPath(import.meta.url)), "..", "fixtures", "results.sqlite");
}

let db: Queryable | null = null;
let running: RunningServer | null = null;

export function backendUrl(): string {
  if (running === null) throw new Error("the fixture backend is not running");
  return running.url;
}

export function fixtureDb(): Queryable {
  if (db === null) throw new Error("the fixture database is not open");
  return db;
}

export function apiClient(): ApiClient {
  return new ApiClient(backendUrl());
}

BeforeAll(async function () {
  db = openResultsDatabase(fixturePath());
  running = await startServer({ db, port: 0 });
});

AfterAll(async function () {
  await running?.close();
  db?.close();
});
