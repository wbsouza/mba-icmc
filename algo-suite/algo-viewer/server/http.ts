/** The HTTP server: `/api/*` to the dispatcher, everything else static files (SPA fallback). */

import { createServer, type IncomingMessage, type Server, type ServerResponse } from "node:http";
import { createReadStream, existsSync, statSync } from "node:fs";
import { extname, join, normalize, resolve } from "node:path";
import type { AddressInfo } from "node:net";
import type { Queryable } from "./db.js";
import { handleApi } from "./api.js";

const MIME: Record<string, string> = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".ico": "image/x-icon",
  ".map": "application/json",
  ".woff2": "font/woff2",
};

export interface ServerOptions {
  db: Queryable;
  /** Directory of the built frontend (dist/); omit to serve the API only. */
  staticDir?: string | undefined;
  host?: string | undefined;
  port?: number | undefined;
}

export interface RunningServer {
  server: Server;
  port: number;
  url: string;
  close(): Promise<void>;
}

function sendJson(response: ServerResponse, status: number, body: unknown): void {
  response.writeHead(status, { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" });
  response.end(JSON.stringify(body));
}

function sendFile(response: ServerResponse, path: string): void {
  response.writeHead(200, { "content-type": MIME[extname(path)] ?? "application/octet-stream" });
  createReadStream(path).pipe(response);
}

function staticPath(staticDir: string, urlPath: string): string | null {
  const root = resolve(staticDir);
  const candidate = normalize(join(root, decodeURIComponent(urlPath)));
  if (!candidate.startsWith(root)) return null;
  if (existsSync(candidate) && statSync(candidate).isFile()) return candidate;
  const index = join(root, "index.html");
  return existsSync(index) ? index : null; // SPA fallback: the hash router owns the rest
}

function handle(options: ServerOptions, request: IncomingMessage, response: ServerResponse): void {
  const url = new URL(request.url ?? "/", "http://localhost");
  if (url.pathname.startsWith("/api")) {
    try {
      const { status, body } = handleApi(options.db, request.method ?? "GET", url.pathname);
      sendJson(response, status, body);
    } catch (error) {
      sendJson(response, 500, { error: error instanceof Error ? error.message : String(error) });
    }
    return;
  }
  const file = options.staticDir === undefined ? null : staticPath(options.staticDir, url.pathname);
  if (file === null) {
    sendJson(response, 404, { error: `no such file ${url.pathname}` });
    return;
  }
  sendFile(response, file);
}

/** Start listening (port 0 = any free port) and resolve once the socket is bound. */
export function startServer(options: ServerOptions): Promise<RunningServer> {
  const server = createServer((request, response) => handle(options, request, response));
  const host = options.host ?? "127.0.0.1";
  return new Promise((resolvePromise, reject) => {
    server.once("error", reject);
    server.listen(options.port ?? 0, host, () => {
      const { port } = server.address() as AddressInfo;
      resolvePromise({
        server,
        port,
        url: `http://${host}:${port}`,
        close: () => new Promise<void>((done, fail) => server.close((e) => (e ? fail(e) : done()))),
      });
    });
  });
}
