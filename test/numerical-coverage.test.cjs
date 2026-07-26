const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

function collectJsonFiles(directory) {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const fullPath = path.join(directory, entry.name);
    if (entry.isDirectory()) return collectJsonFiles(fullPath);
    return entry.isFile() && entry.name.endsWith(".json") ? [fullPath] : [];
  });
}

test("every analyzable model target is numerically scored", () => {
  const scenarios = collectJsonFiles(path.join(__dirname, "..", "scenarios"))
    .map((file) => JSON.parse(fs.readFileSync(file, "utf8")));
  const targets = scenarios.flatMap((scenario) => [
    scenario.expect?.assertions,
    ...(scenario.turns || []).map((turn) => turn.assertions),
  ]).filter(Array.isArray).filter((assertions) => (
    assertions.some((assertion) => assertion.type === "has_analysis")
      && assertions.some((assertion) => assertion.type === "model_matches")
  ));
  assert.equal(targets.length, 114);
  assert.equal(
    targets.filter((assertions) => assertions.some(
      (assertion) => assertion.type === "numerical_matches",
    )).length,
    targets.length,
  );
  assert.equal(
    scenarios.filter((scenario) => scenario.tags?.includes("unsupported-2d-commercial-adapter")).length,
    0,
  );
});
