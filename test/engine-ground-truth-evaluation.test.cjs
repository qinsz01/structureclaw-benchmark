const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const { evaluateScenario } = require("../lib/evaluate.cjs");

const fixtures = path.join(__dirname, "..", "fixtures");
const models = JSON.parse(fs.readFileSync(path.join(fixtures, "ground-truth-models.json"), "utf8"));
const validation = JSON.parse(fs.readFileSync(
  path.join(fixtures, "cross-engine-ground-truth-validation.json"),
  "utf8",
));

function commercialResultFromTruth(engine, response) {
  const loadCase = {
    status: "success",
    forces: response.forces,
    displacements: response.displacements,
    reactions: response.reactions,
  };
  if (engine === "pkpm") return { status: "success", caseResults: { DL: loadCase } };
  return {
    status: "success",
    summary: { load_cases: [{ id: 1, key: response.caseKey, name: "恒载", kind: 1 }] },
    caseResults: { [response.caseKey]: loadCase },
  };
}

for (const engine of ["pkpm", "yjk"]) {
  test(`${engine} assertions compare directly with frozen same-engine ground truth`, async () => {
    const entry = validation.cases[0];
    const modelId = entry.provenance.sourceModelId;
    const model = models.find((candidate) => candidate.id === modelId).model;
    const rawResult = commercialResultFromTruth(engine, entry.engines[engine].response);
    const scenario = {
      id: `same-engine-${engine}`,
      analysisEngineTarget: `builtin-${engine}`,
      expect: {
        assertions: [{
          type: "numerical_matches",
          groundTruthId: modelId,
          engineId: `builtin-${engine}`,
          tolerances: { coordinate: 0.05, load: 0.05, numeric: 0.01, numericAbsolute: 1e-8 },
        }],
      },
    };
    const evaluation = await evaluateScenario(scenario, {
      model,
      analysisResult: { meta: { engineId: `builtin-${engine}` }, data: rawResult },
      messages: [],
    }, 0);
    const numerical = evaluation.metrics.find((metric) => metric.metric === "numerical_matches");
    assert.equal(numerical.pass, true, numerical.actual);
    assert.equal(numerical.details.engine, engine);
  });
}

test("malformed commercial results fail diagnostically instead of aborting evaluation", async () => {
  const entry = validation.cases[0];
  const modelId = entry.provenance.sourceModelId;
  const model = models.find((candidate) => candidate.id === modelId).model;
  const evaluation = await evaluateScenario({
    id: "invalid-pkpm-result",
    analysisEngineTarget: "builtin-pkpm",
    expect: { assertions: [{ type: "numerical_matches", groundTruthId: modelId }] },
  }, { model, analysisResult: { status: "success" }, messages: [] }, 0);
  const numerical = evaluation.metrics.find((metric) => metric.metric === "numerical_matches");
  assert.equal(numerical.pass, false);
  assert.match(numerical.actual, /per-load-case results are required/);
});

test("a changed commercial response component fails numerical matching", async () => {
  const entry = validation.cases[0];
  const modelId = entry.provenance.sourceModelId;
  const model = models.find((candidate) => candidate.id === modelId).model;
  const response = structuredClone(entry.engines.yjk.response);
  const nodeId = Object.keys(response.displacements)[0];
  const component = Object.keys(response.displacements[nodeId])[0];
  response.displacements[nodeId][component] += 1;
  const evaluation = await evaluateScenario({
    id: "changed-yjk-response",
    analysisEngineTarget: "builtin-yjk",
    expect: { assertions: [{ type: "numerical_matches", groundTruthId: modelId }] },
  }, {
    model,
    analysisResult: commercialResultFromTruth("yjk", response),
    messages: [],
  }, 0);
  const numerical = evaluation.metrics.find((metric) => metric.metric === "numerical_matches");
  assert.equal(numerical.pass, false);
  assert.match(numerical.actual, /displacements/);
});
