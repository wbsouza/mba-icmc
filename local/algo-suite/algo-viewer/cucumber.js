// Feature files first: every scenario lives in tests/features/*.feature; the TypeScript
// step definitions are loaded through tsx (`NODE_OPTIONS=--import=tsx`, see package.json;
// no build step) with jsdom set up in support/.
export default {
  paths: ["tests/features/**/*.feature"],
  import: ["tests/support/**/*.ts", "tests/steps/**/*.ts"],
  format: ["progress"],
  formatOptions: { snippetInterface: "async-await" },
};
