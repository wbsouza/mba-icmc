import "./dom";
import { After } from "@cucumber/cucumber";
import { cleanup } from "@testing-library/react";

After(() => {
  cleanup();
  window.location.hash = "";
});
