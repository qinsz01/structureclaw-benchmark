const assert = require("node:assert/strict");
const test = require("node:test");

const { evaluateScenario } = require("../lib/evaluate.cjs");

const scenario = {
  id: "report-consistency",
  expect: { assertions: [{ type: "report_numerical_consistency" }] },
};

test("report consistency accepts the exact current analysis artifact", async () => {
  const analysisResult = {
    success: true,
    displacements: { N1: { ux: 0.001, uz: -0.002 } },
    forces: { E1: { n1: { N: 12.5, M: 3.2 } } },
  };
  const result = await evaluateScenario(scenario, {
    analysisResult,
    report: { json: { analysis: structuredClone(analysisResult) } },
    messages: [],
  }, 0);
  const metric = result.metrics.find((item) => item.metric === "report_numerical_consistency");
  assert.equal(metric.pass, true, metric.actual);
  assert.equal(metric.details.comparedNumbers, 4);
});

test("report consistency rejects stale or changed analysis values", async () => {
  const analysisResult = { success: true, displacements: { N1: { ux: 0.001 } } };
  const result = await evaluateScenario(scenario, {
    analysisResult,
    report: { json: { analysis: { success: true, displacements: { N1: { ux: 0.01 } } } } },
    messages: [],
  }, 0);
  const metric = result.metrics.find((item) => item.metric === "report_numerical_consistency");
  assert.equal(metric.pass, false);
  assert.match(metric.actual, /displacements/);
});
