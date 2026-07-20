const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const {
  checkStaticEquilibrium,
  validateOpenSeesTruthInput,
} = require("../lib/opensees-truth-validation.cjs");
const { compareStructuralModels } = require("../lib/model-fidelity.cjs");
const { sha256 } = require("../lib/numerical-ground-truth.cjs");
const { validateNumericalTruthPayload } = require("../lib/validate-scenarios.cjs");
const { executionVariant } = require("../scripts/generate-opensees-ground-truth.cjs");

const fixtures = JSON.parse(fs.readFileSync(
  path.join(__dirname, "..", "fixtures", "ground-truth-models.json"),
  "utf8",
));

test("all committed models pass OpenSees truth-input preflight", () => {
  for (const entry of fixtures) {
    const validation = validateOpenSeesTruthInput(entry.model);
    assert.equal(validation.pass, true, `${entry.id}: ${validation.issues.join("; ")}`);
  }
});

test("the second solver run changes entity order without changing engineering meaning", () => {
  for (const entry of fixtures) {
    const canonical = executionVariant(entry.model, 0);
    const reordered = executionVariant(entry.model, 1);
    assert.equal(canonical.name, "canonical-order");
    assert.equal(reordered.name, "reordered-1");
    assert.equal(
      compareStructuralModels(reordered.model, canonical.model).pass,
      true,
      `${entry.id}: reordered model changed engineering meaning`,
    );
  }
});

function pointLoadModel() {
  return {
    coordinate_system: { dimension: "2d" },
    nodes: [
      { id: "A", x: 0, y: 0, z: 0 },
      { id: "B", x: 2, y: 0, z: 0 },
    ],
    elements: [{ id: "E", type: "beam", nodes: ["A", "B"], material: "M", section: "S" }],
    materials: [{ id: "M", E: 205000, nu: 0.3 }],
    sections: [{ id: "S", properties: { A: 0.01, Iy: 0.001 } }],
    load_cases: [{ id: "D", type: "dead", loads: [{ node: "B", fx: 0, fz: -10 }] }],
    load_combinations: [{ id: "ULS", factors: { D: 1 } }],
  };
}

test("force and moment equilibrium are independently checked", () => {
  const model = pointLoadModel();
  const selection = { loadCombinationId: "ULS", factors: { D: 1 } };
  const balanced = checkStaticEquilibrium(
    model,
    { reactions: { A: { fz: 10, my: -20 } } },
    selection,
  );
  assert.equal(balanced.pass, true, balanced.failures.join("; "));

  const wrongMoment = checkStaticEquilibrium(
    model,
    { reactions: { A: { fz: 10, my: 0 } } },
    selection,
  );
  assert.equal(wrongMoment.pass, false);
  assert.ok(wrongMoment.failures.some((failure) => failure.includes("moment")));
});

test("distributed loads use their member midpoint and loaded length", () => {
  const model = pointLoadModel();
  model.load_cases[0].loads = [{ element: "E", wx: 0, wy: 0, wz: -5, reference_frame: "global" }];
  const equilibrium = checkStaticEquilibrium(
    model,
    { reactions: { A: { fz: 10, my: -10 } } },
    { loadCombinationId: "ULS", factors: { D: 1 } },
  );
  assert.equal(equilibrium.pass, true, equilibrium.failures.join("; "));
});

test("preflight rejects unsupported truth inputs before solver execution", () => {
  const model = pointLoadModel();
  model.sections[0].properties.Iy = 0;
  model.load_cases[0].loads[0].reference_frame = "element-local";
  const validation = validateOpenSeesTruthInput(model);
  assert.equal(validation.pass, false);
  assert.ok(validation.issues.some((issue) => issue.includes("section Iy")));
  assert.ok(validation.issues.some((issue) => issue.includes("global reference frame")));
});

function validNumericalManifest() {
  const model = pointLoadModel();
  const groundTruth = [{ id: "synthetic-beam", model }];
  const result = {
    status: "success",
    analysisMode: "opensees_2d_frame",
    displacements: { A: { ux: 0, uz: 0 }, B: { ux: 0, uz: -0.01 } },
    reactions: { A: { fz: 10, my: -20 } },
    forces: { E: { axial: 0 } },
  };
  const tolerances = { absolute: 1e-10, relative: 1e-10 };
  return {
    groundTruth,
    payload: {
      schemaVersion: 1,
      sourceModelFileSha256: sha256(groundTruth),
      requiredIndependentRuns: 2,
      numericTolerances: tolerances,
      models: [{
        modelId: "synthetic-beam",
        inputSha256: sha256(model),
        solver: {
          name: "OpenSeesPy",
          packageVersion: "3.7.1.2",
          runtimePackage: "openseespywin",
          runtimePackageVersion: "3.8.0.0",
          version: "3.8.0",
        },
        analysisSelection: { loadCombinationId: "ULS", factors: { D: 1 } },
        result,
        verification: {
          runCount: 2,
          outputHashes: [sha256(result), sha256(result)],
          tolerances,
          executionVariants: ["canonical-order", "reordered-1"],
          solverConfigurations: [
            { system: "BandGeneral", numberer: "Plain", constraints: "Plain", algorithm: "Newton" },
            { system: "FullGeneral", numberer: "RCM", constraints: "Plain", algorithm: "Linear" },
          ],
          equilibrium: [{ pass: true }, { pass: true }],
          analytical: [{ applicable: false, pass: true }, { applicable: false, pass: true }],
        },
      }],
    },
  };
}

test("committed numerical manifests are independently revalidated", () => {
  const valid = validNumericalManifest();
  const errors = [];
  validateNumericalTruthPayload(valid.payload, valid.groundTruth, "3.7.1.2", errors);
  assert.deepEqual(errors, []);

  const corrupted = structuredClone(valid.payload);
  corrupted.models[0].solver.packageVersion = "3.7.0";
  corrupted.models[0].verification.executionVariants[1] = "canonical-order";
  corrupted.models[0].verification.solverConfigurations[1]
    = structuredClone(corrupted.models[0].verification.solverConfigurations[0]);
  corrupted.models[0].result.reactions.A.my = 0;
  const corruptedErrors = [];
  validateNumericalTruthPayload(corrupted, valid.groundTruth, "3.7.1.2", corruptedErrors);
  assert.ok(corruptedErrors.some((error) => error.includes("OpenSees identity")));
  assert.ok(corruptedErrors.some((error) => error.includes("stored result hash")));
  assert.ok(corruptedErrors.some((error) => error.includes("execution variants")));
  assert.ok(corruptedErrors.some((error) => error.includes("distinct solver configurations")));
  assert.ok(corruptedErrors.some((error) => error.includes("recomputed equilibrium")));
});
