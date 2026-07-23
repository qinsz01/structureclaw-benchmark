const assert = require("node:assert/strict");
const test = require("node:test");

const { evaluateScenario } = require("../lib/evaluate.cjs");

function scenario(assertions) {
  return {
    id: "unsupported-commercial-adapter",
    expect: { assertions },
  };
}

test("concrete-frame accepts the reinforced-concrete-frame routing alias", async () => {
  const result = await evaluateScenario(
    scenario([{ type: "structural_type", expected: "concrete-frame" }]),
    { structuralTypeKey: "reinforced-concrete-frame" },
  );

  assert.equal(result.allPassed, true);
});

test("safe non-execution accepts an explicit pre-solver dimensional rejection", async () => {
  const result = await evaluateScenario(
    scenario([{ type: "safe_non_execution", reasonIncludes: "canonical 3-D" }]),
    {
      analysisResult: {
        success: false,
        error_code: "ANALYSIS_EXECUTION_FAILED",
        message: "PKPM floor-model conversion requires a genuine canonical 3-D model",
        data: {},
      },
      messages: [{ name: "run_analysis", content: "rejected" }],
    },
  );

  assert.equal(result.allPassed, true);
});

test("interaction questions recognize LangChain AIMessage instances", async () => {
  const result = await evaluateScenario(
    scenario([{ type: "has_interaction_questions" }]),
    {
      messages: [{
        _getType() {
          return "ai";
        },
        content: "Would you like me to use OpenSees, or rebuild the model in 3D for PKPM?",
        tool_calls: [],
      }],
    },
  );

  assert.equal(result.allPassed, true);
});

test("safe non-execution rejects numerical output and unrelated failures", async () => {
  const assertions = [{ type: "safe_non_execution", reasonIncludes: "canonical 3-D" }];
  const numerical = await evaluateScenario(scenario(assertions), {
    analysisResult: {
      success: false,
      message: "canonical 3-D input rejected after calculation",
      data: { displacements: [{ node: "1", ux: 0.1 }] },
    },
    messages: [{ name: "run_analysis", content: "failed" }],
  });
  const unrelated = await evaluateScenario(scenario(assertions), {
    analysisResult: {
      success: false,
      message: "license initialization failed",
      data: {},
    },
    messages: [{ name: "run_analysis", content: "failed" }],
  });

  assert.equal(numerical.allPassed, false);
  assert.equal(unrelated.allPassed, false);
});
