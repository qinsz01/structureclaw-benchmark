const assert = require("node:assert/strict");
const test = require("node:test");

const { wireScenario } = require("../scripts/wire-numerical-assertions.cjs");

function scenario(taskFamily = "standard_workflow") {
  return {
    id: "synthetic",
    taskFamily,
    evaluationFocus: ["modeling", "model_match", "analysis"],
    expect: {
      assertions: [
        {
          type: "model_matches",
          groundTruthId: "beam-simple-6m",
          tolerances: { coordinate: 0.1, property: 0.02 },
        },
        { type: "has_analysis" },
      ],
    },
  };
}

test("numerical assertion wiring is explicit, strict, and idempotent", () => {
  const target = scenario();
  const first = wireScenario(target, new Set(["beam-simple-6m"]));
  assert.equal(first.changed, true);
  assert.equal(first.eligible, 1);
  const model = target.expect.assertions.find((assertion) => assertion.type === "model_matches");
  assert.deepEqual(model.tolerances, {
    property: 0.02,
    coordinate: 0.05,
    load: 0.05,
  });
  const numerical = target.expect.assertions.find((assertion) => assertion.type === "numerical_matches");
  assert.deepEqual(numerical, {
    type: "numerical_matches",
    groundTruthId: "beam-simple-6m",
    tolerances: {
      property: 0.02,
      coordinate: 0.05,
      load: 0.05,
      numeric: 0.01,
      numericAbsolute: 1e-8,
    },
  });
  assert.ok(target.evaluationFocus.includes("numerical_match"));

  const second = wireScenario(target, new Set(["beam-simple-6m"]));
  assert.equal(second.changed, false);
  assert.equal(target.expect.assertions.filter((assertion) => assertion.type === "numerical_matches").length, 1);
});

test("wiring refuses missing truth and covers analyzable robustness cases", () => {
  assert.throws(
    () => wireScenario(scenario(), new Set()),
    /numerical truth is missing/,
  );
  const robustness = scenario("interactive_robustness");
  const result = wireScenario(robustness, new Set(["beam-simple-6m"]));
  assert.deepEqual(result, { changed: true, eligible: 1 });
});

test("commercial scenarios are scored only when same-engine truth exists", () => {
  const target = scenario();
  target.analysisEngineTarget = "builtin-pkpm";
  const unavailable = wireScenario(target, new Set(["beam-simple-6m"]));
  assert.deepEqual(unavailable, { changed: true, eligible: 0 });
  assert.equal(target.expect.assertions.some((assertion) => assertion.type === "numerical_matches"), false);

  const available = scenario();
  available.analysisEngineTarget = "builtin-pkpm";
  const crossTruth = {
    cases: [{
      provenance: { sourceModelId: "beam-simple-6m" },
      engines: { pkpm: { metrics: {} } },
    }],
  };
  assert.deepEqual(wireScenario(available, new Set(["beam-simple-6m"]), crossTruth), {
    changed: true,
    eligible: 1,
  });
  assert.equal(
    available.expect.assertions.find((assertion) => assertion.type === "numerical_matches").engineId,
    "builtin-pkpm",
  );
});
