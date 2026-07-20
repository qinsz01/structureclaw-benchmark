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

function syntheticCommercialResult(engine, model, metrics) {
  const nodes = new Map(model.nodes.map((node) => [String(node.id), node]));
  const baseZ = Math.min(...model.nodes.map((node) => Number(node.z || 0)));
  const baseNodes = model.nodes.filter((node) => Number(node.z || 0) === baseZ);
  const upperNodes = model.nodes.filter((node) => Number(node.z || 0) !== baseZ);
  const bottomColumns = model.elements.filter((element) => element.type === "column"
    && element.nodes.some((id) => Number(nodes.get(String(id))?.z || 0) === baseZ));
  const beams = model.elements.filter((element) => element.type === "beam");
  const remainingAxial = metrics.bottomColumnAxialSum - metrics.maxBottomColumnAxial;
  const otherAxial = bottomColumns.length > 1 ? remainingAxial / (bottomColumns.length - 1) : 0;
  const forces = {};
  bottomColumns.forEach((element, index) => {
    forces[element.id] = {
      N: -(index === 0 ? metrics.maxBottomColumnAxial : otherAxial),
      V: 0,
      M: index === 0 ? metrics.maxBottomColumnMoment : 0,
    };
  });
  beams.forEach((element, index) => {
    forces[element.id] = {
      N: 0,
      V: index === 0 ? metrics.maxBeamShear : 0,
      M: index === 0 ? metrics.maxBeamMoment : 0,
    };
  });
  const displacements = Object.fromEntries(upperNodes.map((node, index) => [node.id, {
    uz: index === 0 ? -metrics.maxVerticalDisplacement : 0,
  }]));
  const reactions = { [baseNodes[0].id]: { fz: metrics.totalGravity } };
  const loadCase = { status: "success", forces, displacements, reactions };
  if (engine === "pkpm") return { status: "success", caseResults: { DL: loadCase } };
  return {
    status: "success",
    summary: { load_cases: [{ id: 1, key: "lc_1", name: "恒载", kind: 1 }] },
    caseResults: { lc_1: loadCase },
  };
}

for (const engine of ["pkpm", "yjk"]) {
  test(`${engine} assertions compare directly with frozen same-engine ground truth`, async () => {
    const entry = validation.cases[0];
    const modelId = entry.provenance.sourceModelId;
    const model = models.find((candidate) => candidate.id === modelId).model;
    const rawResult = syntheticCommercialResult(engine, model, entry.engines[engine].metrics);
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
