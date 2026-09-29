import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The React app only talks to the backend's JSON API (server/). In development Vite
// proxies /api to it; in production the backend serves dist/ and the API from one origin.
export default defineConfig({
  base: "./",
  plugins: [react()],
  server: { proxy: { "/api": process.env["ALGO_VIEWER_API"] ?? "http://127.0.0.1:8787" } },
  build: { target: "es2022", sourcemap: false },
});
