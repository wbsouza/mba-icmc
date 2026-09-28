import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import wasmUrl from "sql.js/dist/sql-wasm.wasm?url";
import { App } from "./App";
import "./styles.css";

// The WASM binary is a bundled asset, so the built page never reaches for a CDN.
const root = document.getElementById("root");
if (root === null) throw new Error("index.html has no #root element");
createRoot(root).render(
  <StrictMode>
    <App locateFile={() => wasmUrl} />
  </StrictMode>,
);
