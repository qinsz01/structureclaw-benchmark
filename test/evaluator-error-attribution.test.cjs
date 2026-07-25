const assert = require("node:assert/strict");
const test = require("node:test");

const { evaluateScenario } = require("../lib/evaluate.cjs");

test("unexpected evaluator exceptions are not counted as model failures", async () => {
  const tolerances = new Proxy({}, {
    get() {
      throw new Error("synthetic comparator failure");
    },
  });

  await assert.rejects(
    evaluateScenario({
      id: "evaluator-failure",
      expect: {
        assertions: [{
          type: "model_matches",
          groundTruthId: "beam-simple-6m",
          tolerances,
        }],
      },
    }, {
      model: {
        nodes: [],
      },
    }, 0),
    /BENCHMARK_EVALUATOR_ERROR.*synthetic comparator failure/,
  );
});

test("unknown assertion types are benchmark configuration errors", async () => {
  await assert.rejects(
    evaluateScenario({
      id: "unknown-assertion",
      expect: {
        assertions: [{ type: "not-a-real-assertion" }],
      },
    }, {}, 0),
    /BENCHMARK_EVALUATOR_ERROR.*unsupported assertion type/,
  );
});
