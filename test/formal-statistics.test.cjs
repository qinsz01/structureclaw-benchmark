const test = require("node:test");
const assert = require("node:assert/strict");

const {
  aggregateFormalRows,
  bootstrapMean,
  failureStage,
  holmAdjust,
  summarizeCondition,
} = require("../lib/formal-statistics.cjs");

function row({ scenario, repeat, mode, pass, model = "model-a", metrics = [] }) {
  return {
    scenarioId: `${scenario}#${mode}`,
    baseScenarioId: scenario,
    taskFamily: "standard_workflow",
    modelId: model,
    visionModelId: null,
    repeatId: repeat,
    mode,
    allPassed: pass,
    durationMs: 100,
    metrics,
  };
}

test("scenario bootstrap keeps repeats clustered within the scenario unit", () => {
  const rows = [
    row({ scenario: "a", repeat: 1, mode: "auto", pass: true }),
    row({ scenario: "a", repeat: 2, mode: "auto", pass: true }),
    row({ scenario: "a", repeat: 3, mode: "auto", pass: false }),
    row({ scenario: "b", repeat: 1, mode: "auto", pass: false }),
    row({ scenario: "b", repeat: 2, mode: "auto", pass: false }),
    row({ scenario: "b", repeat: 3, mode: "auto", pass: false }),
  ];
  const summary = summarizeCondition(rows, { seed: "test" });
  assert.equal(summary.scenarios, 2);
  assert.equal(summary.mean, 1 / 3);
  assert.equal(summary.stableSuccess, 0);
  assert.equal(summary.unstable, 1);
  assert.equal(summary.stableFailure, 1);
});

test("auto lift uses paired common-core outcomes and Holm correction", () => {
  const rows = [];
  for (const scenario of ["a", "b"]) {
    for (const repeat of [1, 2, 3]) {
      rows.push(row({
        scenario,
        repeat,
        mode: "auto",
        pass: true,
        metrics: [{ metric: "model_matches", pass: true }],
      }));
      rows.push(row({
        scenario,
        repeat,
        mode: "generic-only",
        pass: false,
        metrics: [{ metric: "model_matches", pass: false }],
      }));
    }
  }
  const summary = aggregateFormalRows(rows);
  assert.equal(summary.standardAutoLift.length, 1);
  assert.equal(summary.standardAutoLift[0].effect, 1);
  assert.equal(summary.standardAutoLift[0].holmAdjustedPValue, summary.standardAutoLift[0].pValue);
});

test("failure stage uses the first failed required metric", () => {
  assert.equal(failureStage({
    allPassed: false,
    metrics: [
      { metric: "toolCalls", pass: true },
      { metric: "model_matches", pass: false },
      { metric: "numerical_matches", pass: false },
    ],
  }), "structural-correctness");
});

test("bootstrap and Holm outputs are deterministic", () => {
  assert.deepEqual(
    bootstrapMean([0, 0.5, 1], { seed: "fixed", iterations: 100 }),
    bootstrapMean([0, 0.5, 1], { seed: "fixed", iterations: 100 }),
  );
  assert.deepEqual(
    holmAdjust([
      { id: "a", pValue: 0.01 },
      { id: "b", pValue: 0.04 },
    ]),
    [
      { id: "a", pValue: 0.01, holmAdjustedPValue: 0.02 },
      { id: "b", pValue: 0.04, holmAdjustedPValue: 0.04 },
    ],
  );
});
