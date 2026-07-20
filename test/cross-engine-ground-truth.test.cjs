const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const {
  assessCrossEngine,
  extractEngineMetrics,
  relativeDifference,
} = require("../lib/cross-engine-ground-truth.cjs");
const {
  classifyCrossEngineSupport,
  deriveCommonModel,
  geometricArea,
  openSeesModel,
  storyFloorLoads,
} = require("../scripts/generate-cross-engine-ground-truth.cjs");

const model = {
  nodes: [
    { id: "N0", z: 0 },
    { id: "N1", z: 3 },
    { id: "N2", z: 3 },
  ],
  elements: [
    { id: "C1", type: "column", nodes: ["N0", "N1"] },
    { id: "B1", type: "beam", nodes: ["N1", "N2"] },
  ],
};

function commercialCase(axial, shear, moment, displacement, reaction = 0) {
  return {
    status: "success",
    displacements: { N1: { uz: -displacement }, N2: { uz: -displacement / 2 } },
    forces: {
      C1: { N: -axial, V: 1, M: 2 },
      B1: { N: 0, V: shear, M: moment },
    },
    reactions: reaction ? { N0: { fz: reaction } } : {},
  };
}

test("normalizes equivalent OpenSees and commercial dead-load results", () => {
  const openSees = {
    status: "success",
    displacements: { N0: { uz: 0 }, N1: { uz: -0.01 }, N2: { uz: -0.005 } },
    forces: {
      C1: { axial: 100, n1: { N: 100, V: 1, M: 2 }, n2: { N: -99, V: 1, M: 2 } },
      B1: { n1: { N: 0, V: 20, M: 30 }, n2: { N: 0, V: 20, M: -30 } },
    },
    reactions: { N0: { fz: 100 } },
  };
  const pkpm = { status: "success", caseResults: { DL: commercialCase(100, 20, 30, 0.01) } };
  const yjk = {
    status: "success",
    summary: { load_cases: [{ id: 1, key: "lc_1", name: "恒载", kind: 1 }] },
    caseResults: { lc_1: commercialCase(100, 20, 30, 0.01, 100) },
  };
  assert.equal(extractEngineMetrics("opensees", model, openSees).totalGravity, 100);
  assert.equal(extractEngineMetrics("pkpm", model, pkpm).totalGravity, 100);
  assert.equal(extractEngineMetrics("yjk", model, yjk).maxBeamMoment, 30);
  assert.equal(extractEngineMetrics("yjk", model, yjk).maxBottomColumnMoment, 2);
});

test("assesses only the engines declared comparable for each metric", () => {
  const metrics = {
    opensees: { load: 100, displacement: 0.01 },
    pkpm: { load: 101, displacement: 0.02 },
    yjk: { load: 99, displacement: 0.0105 },
  };
  const result = assessCrossEngine(metrics, {
    load: { tier: "equilibrium", relativeTolerance: 0.03 },
    displacement: { tier: "response", engines: ["opensees", "yjk"], relativeTolerance: 0.1 },
  });
  assert.equal(result.pass, true);
  assert.equal(result.status, "fully_validated");
  assert.deepEqual(result.metrics.displacement.excludedEngines, ["pkpm"]);
});

test("fails when any required pair exceeds tolerance or a value is missing", () => {
  assert.ok(relativeDifference(100, 80) > 0.1);
  const divergent = assessCrossEngine({
    opensees: { load: 100 },
    pkpm: { load: 80 },
    yjk: { load: 100 },
  }, { load: { relativeTolerance: 0.1 } });
  assert.equal(divergent.pass, false);
  const missing = assessCrossEngine({
    opensees: { load: 100 },
    pkpm: {},
    yjk: { load: 100 },
  }, { load: { relativeTolerance: 0.1 } });
  assert.equal(missing.pass, false);
});

test("distinguishes equilibrium validation from full response validation", () => {
  const result = assessCrossEngine({
    opensees: { load: 100, response: 10 },
    pkpm: { load: 100, response: 20 },
    yjk: { load: 100, response: 20 },
  }, {
    load: { tier: "equilibrium", relativeTolerance: 0.01 },
    response: { tier: "response", relativeTolerance: 0.1 },
  });
  assert.equal(result.pass, false);
  assert.equal(result.status, "equilibrium_validated");
  assert.equal(result.tiers.equilibrium.pass, true);
  assert.equal(result.tiers.response.pass, false);
});

test("derives a commercial-compatible model and an OpenSees-only self-weight variant", () => {
  const source = {
    project: { name: "source" },
    stories: [{ id: "F1", height: 3, floorLoad: 9, floorLoadUnit: "kN/m2" }],
    materials: [{ id: "M", rho: 7850 }],
    sections: [{
      id: "S",
      type: "H",
      shape: { kind: "H", H: 300, B: 200, tw: 10, tf: 15 },
      properties: { A: 999 },
    }],
    nodes: [{ id: "N0", z: 0 }, { id: "N1", z: 3 }],
    elements: [{ id: "C1", type: "column", nodes: ["N0", "N1"], material: "M", section: "S" }],
    load_cases: [{ id: "old", loads: [{ node: "N1", fz: -1 }] }],
    load_combinations: [{ id: "old", factors: { old: 1 } }],
  };
  const common = deriveCommonModel(source, "case");
  assert.equal(common.stories[0].elevation, 0);
  assert.equal(common.stories[0].dead_load, 9);
  assert.deepEqual(common.load_cases, []);
  assert.ok(Math.abs(geometricArea(source.sections[0]) - 0.0087) < 1e-12);
  const openSees = openSeesModel(common);
  assert.equal(common.load_cases.length, 0);
  assert.equal(openSees.load_cases[1].loads.length, 1);
  assert.equal(openSees.load_combinations[0].factors.SELF_WEIGHT, 1);
});

test("automatically selects every losslessly representable three-engine ground-truth model", () => {
  const models = JSON.parse(fs.readFileSync(
    path.join(__dirname, "..", "fixtures", "ground-truth-models.json"),
    "utf8",
  ));
  const supported = models
    .filter((entry) => classifyCrossEngineSupport(entry).supported)
    .map((entry) => entry.id);
  assert.deepEqual(supported, [
    "frame3d-simple",
    "frame3d-complex",
    "frame3d-concrete",
    "frame3d-concrete-2s-2x1y-12k",
    "frame3d-steel-2s-2x1y-8k",
    "frame3d-steel-3s-1x2y-10k",
  ]);
});

test("committed cross-engine results cover the complete supported set", () => {
  const validation = JSON.parse(fs.readFileSync(
    path.join(__dirname, "..", "fixtures", "cross-engine-ground-truth-validation.json"),
    "utf8",
  ));
  const eligible = validation.supportAudit.models
    .filter((entry) => entry.supported)
    .map((entry) => `cross-${entry.sourceModelId}`)
    .sort();
  assert.deepEqual(validation.cases.map((entry) => entry.caseId).sort(), eligible);
  assert.equal(validation.supportAudit.totalGroundTruthModels, 47);
});

test("supported cases preserve each source story's explicit gravity resultant", () => {
  const models = JSON.parse(fs.readFileSync(
    path.join(__dirname, "..", "fixtures", "ground-truth-models.json"),
    "utf8",
  ));
  for (const entry of models.filter((item) => classifyCrossEngineSupport(item).supported)) {
    const model = entry.model;
    const nodes = new Map(model.nodes.map((node) => [String(node.id), node]));
    const elements = new Map(model.elements.map((element) => [String(element.id), element]));
    const x = model.nodes.map((node) => Number(node.x));
    const y = model.nodes.map((node) => Number(node.y));
    const planArea = (Math.max(...x) - Math.min(...x)) * (Math.max(...y) - Math.min(...y));
    let storyTop = 0;
    for (const story of model.stories) {
      storyTop += Number(story.height);
      const explicitResultant = model.load_cases
        .flatMap((loadCase) => loadCase.loads || [])
        .filter((load) => load.type === "distributed")
        .reduce((sum, load) => {
          const element = elements.get(String(load.element));
          const ends = element.nodes.map((id) => nodes.get(String(id)));
          if (Math.abs(Math.max(...ends.map((node) => Number(node.z))) - storyTop) > 1e-9) return sum;
          const length = Math.hypot(
            Number(ends[1].x) - Number(ends[0].x),
            Number(ends[1].y) - Number(ends[0].y),
            Number(ends[1].z) - Number(ends[0].z),
          );
          return sum + Math.abs(Number(load.wz || 0)) * length;
        }, 0);
      const declaredResultant = storyFloorLoads(story)
        .reduce((sum, load) => sum + Number(load.value), 0) * planArea;
      assert.ok(Math.abs(explicitResultant - declaredResultant) <= 1e-9, `${entry.id}/${story.id}`);
    }
  }
});
