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
    coordinate: 0.1,
    property: 0.02,
    load: 0.05,
  });
  const numerical = target.expect.assertions.find((assertion) => assertion.type === "numerical_matches");
  assert.deepEqual(numerical, {
    type: "numerical_matches",
    groundTruthId: "beam-simple-6m",
    tolerances: {
      coordinate: 0.1,
      property: 0.02,
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

test("wiring refuses missing truth and ignores non-engineering robustness cases", () => {
  assert.throws(
    () => wireScenario(scenario(), new Set()),
    /numerical truth is missing/,
  );
  const robustness = scenario("interactive_robustness");
  assert.deepEqual(wireScenario(robustness, new Set()), { changed: false, eligible: 0 });
});
