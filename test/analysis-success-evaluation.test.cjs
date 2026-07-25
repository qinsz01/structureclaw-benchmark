const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const { evaluateScenario } = require("../lib/evaluate.cjs");

const groundTruthModels = JSON.parse(fs.readFileSync(
  path.join(__dirname, "..", "fixtures", "ground-truth-models.json"),
  "utf8",
));
const numericalTruth = JSON.parse(fs.readFileSync(
  path.join(__dirname, "..", "fixtures", "opensees-ground-truth.json"),
  "utf8",
));

test("explicitly failed analysis artifacts do not pass presence checks with stale values", async () => {
  const result = await evaluateScenario({
    id: "failed-analysis-presence",
    expect: { assertions: [{ type: "has_analysis" }] },
  }, {
    analysisResult: {
      success: false,
      data: { displacements: { N1: { ux: 0.001 } } },
    },
    messages: [],
  }, 0);

  const metric = result.metrics.find((item) => item.metric === "has_analysis");
  assert.equal(metric.pass, false);
  assert.match(metric.actual, /unsuccessful/);
});

test("explicitly failed analysis artifacts cannot pass numerical ground truth", async () => {
  const modelId = "beam-simple-6m";
  const model = structuredClone(
    groundTruthModels.find((entry) => entry.id === modelId).model,
  );
  const truth = structuredClone(
    numericalTruth.models.find((entry) => entry.modelId === modelId).result,
  );
  const result = await evaluateScenario({
    id: "failed-analysis-numerical",
    expect: {
      assertions: [{
        type: "numerical_matches",
        groundTruthId: modelId,
        tolerances: {
          coordinate: 0.05,
          load: 0.05,
          numeric: 0.01,
          numericAbsolute: 1e-8,
        },
      }],
    },
  }, {
    model,
    analysisResult: { success: false, data: truth },
    messages: [],
  }, 0);

  const metric = result.metrics.find((item) => item.metric === "numerical_matches");
  assert.equal(metric.pass, false);
  assert.match(metric.actual, /unsuccessful/);
});

test("successful commercial per-case results satisfy analysis presence", async () => {
  const result = await evaluateScenario({
    id: "commercial-analysis-presence",
    expect: { assertions: [{ type: "has_analysis" }] },
  }, {
    analysisResult: {
      data: {
        status: "success",
        caseResults: {
          DL: {
            status: "success",
            displacements: { N1: { ux: 0.001 } },
          },
        },
      },
    },
    messages: [],
  }, 0);

  const metric = result.metrics.find((item) => item.metric === "has_analysis");
  assert.equal(metric.pass, true, metric.actual);
});

test("analysis-or-interaction accepts a completed analysis without requiring abstention", async () => {
  const result = await evaluateScenario({
    id: "unusual-but-executable-input",
    expect: { assertions: [{ type: "analysis_or_interaction" }] },
  }, {
    analysisResult: {
      success: true,
      data: { displacements: { N1: { ux: 0.002 } } },
    },
    messages: [],
  }, 0);

  const metric = result.metrics.find((item) => item.metric === "analysis_or_interaction");
  assert.equal(metric.pass, true, metric.actual);
  assert.equal(metric.actual, "analysis present");
});
