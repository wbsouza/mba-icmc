import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// sql.js ships a UMD bundle plus the WASM binary; the binary is imported as an asset
// (see src/main.tsx) so the built dist/ is self-contained — nothing is fetched from a CDN.
export default defineConfig({
  base: "./",
  plugins: [react()],
  optimizeDeps: { exclude: ["sql.js"] },
  build: { target: "es2022", sourcemap: false },
});
