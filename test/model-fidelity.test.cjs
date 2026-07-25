const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const { compareStructuralModels } = require("../lib/model-fidelity.cjs");
const { evaluateScenario } = require("../lib/evaluate.cjs");

const fixtures = JSON.parse(fs.readFileSync(
  path.join(__dirname, "..", "fixtures", "ground-truth-models.json"),
  "utf8",
));

function clone(value) {
  return structuredClone(value);
}

function fixture(id = "beam-simple-6m") {
  return clone(fixtures.find((entry) => entry.id === id).model);
}

test("all committed ground-truth models match themselves", () => {
  for (const entry of fixtures) {
    const comparison = compareStructuralModels(entry.model, entry.model);
    assert.equal(comparison.pass, true, `${entry.id}: ${comparison.summary}`);
  }
});

test("ground-truth models do not contain duplicate elements", () => {
  for (const entry of fixtures) {
    const endpoints = new Set();
    for (const element of entry.model.elements) {
      const key = [...element.nodes].sort().join("::");
      assert.equal(endpoints.has(key), false, `${entry.id}: duplicate element at ${key}`);
      endpoints.add(key);
    }
  }
});

test("concrete frame section shear modulus matches its material grade", () => {
  for (const grade of ["c30", "c40"]) {
    const model = fixture(`concrete-frame-2s2b-6m-10k-${grade}`);
    const material = model.materials.find((item) => item.category === "concrete");
    const expectedG = material.E / (2 * (1 + material.nu));
    for (const section of model.sections) {
      assert.ok(
        Math.abs(section.properties.G - expectedG) <= 1e-9,
        `${grade} ${section.id}: expected G=${expectedG}, got ${section.properties.G}`,
      );
    }
  }
});

test("entity identifiers may differ when engineering relationships are preserved", () => {
  const expected = fixture();
  const actual = fixture();
  const nodeIds = new Map(actual.nodes.map((node, index) => [node.id, `node-${index + 1}`]));
  const elementIds = new Map(actual.elements.map((element, index) => [element.id, `member-${index + 1}`]));
  actual.nodes.forEach((node) => { node.id = nodeIds.get(node.id); });
  actual.elements.forEach((element) => {
    const oldId = element.id;
    element.id = elementIds.get(oldId);
    element.nodes = element.nodes.map((id) => nodeIds.get(id));
    element.material = "material-a";
    element.section = "section-a";
  });
  actual.materials[0].id = "material-a";
  actual.sections[0].id = "section-a";
  for (const loadCase of actual.load_cases) {
    for (const load of loadCase.loads) {
      if (load.node !== undefined) load.node = nodeIds.get(load.node);
      if (load.element !== undefined) load.element = elementIds.get(load.element);
    }
  }

  assert.equal(compareStructuralModels(actual, expected).pass, true);
});

test("extra entities fail strict precision", () => {
  const expected = fixture();
  const actual = fixture();
  actual.nodes.push({ id: "extra", x: 100, y: 0, z: 0 });
  const comparison = compareStructuralModels(actual, expected);
  assert.equal(comparison.pass, false);
  assert.ok(comparison.failures.includes("nodes"));
  assert.ok(comparison.metrics.nodes.precision < 1);
});

test("model comparison summary distinguishes actual, expected, and matched entity counts", () => {
  const expected = fixture("truss-pratt-15m-top10");
  const actual = fixture("truss-pratt-15m-top10");
  actual.elements[actual.elements.length - 1].nodes = ["B0", "T1"];

  const comparison = compareStructuralModels(actual, expected);

  assert.match(
    comparison.summary,
    /elements actual=\d+, expected=\d+, matched=\d+ \(P=/,
  );
});

test("incorrect connectivity fails topology even when counts and spans agree", () => {
  const expected = fixture();
  const actual = fixture();
  actual.elements[0].nodes = ["1", "3"];
  const comparison = compareStructuralModels(actual, expected);
  assert.equal(comparison.pass, false);
  assert.ok(comparison.failures.includes("topology"));
});

test("incorrect restraint degrees of freedom fail", () => {
  const expected = fixture();
  const actual = fixture();
  actual.nodes[2].restraints[0] = true;
  const comparison = compareStructuralModels(actual, expected);
  assert.equal(comparison.pass, false);
  assert.ok(comparison.failures.includes("restraints"));
});

test("assigned material and section properties are checked", () => {
  const expected = fixture();
  const wrongMaterial = fixture();
  wrongMaterial.materials[0].E *= 0.5;
  const wrongSection = fixture();
  wrongSection.sections[0].properties.Iy *= 2;

  assert.ok(compareStructuralModels(wrongMaterial, expected).failures.includes("properties"));
  assert.ok(compareStructuralModels(wrongSection, expected).failures.includes("properties"));
});

test("parametric section shape and element-local modifiers are checked", () => {
  const expected = fixture("frame-simple-1s1b");
  const wrongShape = fixture("frame-simple-1s1b");
  const shapedSection = wrongShape.sections.find((section) => section.shape);
  shapedSection.shape.H *= 0.5;
  const unexpectedRelease = fixture("frame-simple-1s1b");
  unexpectedRelease.elements[0].releases = { i_ry: true };
  const unexpectedRotation = fixture("frame-simple-1s1b");
  unexpectedRotation.elements[0].rotation_angle = 15;

  assert.ok(compareStructuralModels(wrongShape, expected).failures.includes("properties"));
  assert.ok(compareStructuralModels(unexpectedRelease, expected).failures.includes("element modifiers"));
  assert.ok(compareStructuralModels(unexpectedRotation, expected).failures.includes("element modifiers"));
});

test("equivalent section aliases and unconstrained engineering metadata are accepted", () => {
  const expected = fixture("concrete-frame-2s1b-6m-12k");
  const actual = fixture("concrete-frame-2s1b-6m-12k");
  actual.sections.forEach((section) => { section.type = "rectangular"; });
  actual.elements.forEach((element) => {
    element.concrete_grade = "C30";
    element.rebar_grade = "HRB400";
  });
  actual.metadata.elementReferenceVectors = Object.fromEntries(
    actual.elements.map((element) => [element.id, [0, 1, 0]]),
  );

  assert.equal(compareStructuralModels(actual, expected).pass, true);

  expected.elements[0].concrete_grade = "C35";
  assert.ok(compareStructuralModels(actual, expected).failures.includes("element modifiers"));
});

test("schema and unit contracts are part of engineering fidelity", () => {
  const expected = fixture();
  const wrongSchema = fixture();
  wrongSchema.schema_version = "1.0.0";
  const wrongUnits = fixture();
  wrongUnits.unit_system = "US";
  const conflictingMetadata = fixture();
  conflictingMetadata.metadata.frameDimension = "3d";

  assert.ok(compareStructuralModels(wrongSchema, expected).failures.includes("schema version"));
  assert.ok(compareStructuralModels(wrongUnits, expected).failures.includes("unit system"));
  assert.match(compareStructuralModels(conflictingMetadata, expected).summary, /metadata dimension conflicts/);
});

test("artifact integrity rejects malformed ids, references, DOFs, restraints, and numeric fields", () => {
  const expected = fixture();
  const duplicateNode = fixture();
  duplicateNode.nodes[1].id = duplicateNode.nodes[0].id;
  const invalidElementReference = fixture();
  invalidElementReference.elements[0].material = "missing-material";
  const invalidLoadReference = fixture();
  invalidLoadReference.load_cases[0].loads[0].element = "missing-element";
  const extraDof = fixture();
  extraDof.coordinate_system.dof_order.push("warp");
  const stringCoordinate = fixture();
  stringCoordinate.nodes[0].x = "0";
  const stringRestraint = fixture();
  stringRestraint.nodes[0].restraints[0] = "true";
  const invalidLoadValue = fixture();
  invalidLoadValue.load_cases[0].loads[0].wz = "not-a-number";
  const invalidForceVector = fixture();
  invalidForceVector.load_cases[0].loads[0].forces = [0, 0, -20];
  const stringShape = fixture("frame-simple-1s1b");
  stringShape.sections[0].shape.H = "300";
  const stringStory = fixture("frame-simple-1s1b");
  stringStory.stories[0].height = "4.5";

  for (const actual of [
    duplicateNode,
    invalidElementReference,
    invalidLoadReference,
    stringCoordinate,
    stringRestraint,
    invalidLoadValue,
    invalidForceVector,
    stringShape,
    stringStory,
  ]) {
    const comparison = compareStructuralModels(actual, expected);
    assert.equal(comparison.pass, false);
    assert.ok(comparison.failures.includes("artifact integrity"));
  }
  assert.equal(compareStructuralModels(extraDof, expected).pass, false);
});

test("load direction and member location are checked independently of total load", () => {
  const expected = fixture();
  const wrongDirection = fixture();
  wrongDirection.load_cases[0].loads[0].wx = wrongDirection.load_cases[0].loads[0].wz;
  wrongDirection.load_cases[0].loads[0].wz = 0;
  const wrongLocation = fixture();
  wrongLocation.load_cases[0].loads[0].element = "2";

  assert.ok(compareStructuralModels(wrongDirection, expected).failures.includes("loads"));
  assert.ok(compareStructuralModels(wrongLocation, expected).failures.includes("loads"));
});

test("equivalent nodal load components may be split or combined at the same target", () => {
  const expected = fixture("column-concrete-4p2-600-30");
  const actual = fixture("column-concrete-4p2-600-30");
  actual.load_cases[0].type = "dead";
  actual.load_cases[0].loads = [{
    type: "nodal",
    node: "N2",
    fx: 30,
    fz: -600,
    reference_frame: "global",
  }];

  assert.equal(compareStructuralModels(actual, expected).pass, true);
});

test("load magnitudes use a unified five-percent default tolerance", () => {
  const expected = fixture();
  const withinTolerance = fixture();
  withinTolerance.load_cases[0].loads[0].wz *= 1.04;
  const outsideTolerance = fixture();
  outsideTolerance.load_cases[0].loads[0].wz *= 1.06;

  assert.equal(compareStructuralModels(withinTolerance, expected).pass, true);
  assert.ok(compareStructuralModels(outsideTolerance, expected).failures.includes("loads"));
});

test("load-combination factors are checked", () => {
  const expected = fixture("frame3d-simple");
  const actual = fixture("frame3d-simple");
  actual.load_combinations[0].factors.D = 1.2;
  const comparison = compareStructuralModels(actual, expected);
  assert.equal(comparison.pass, false);
  assert.ok(comparison.failures.includes("load combinations"));
});

test("equivalent load-case partitions match when their factored physical loads are identical", () => {
  const expected = fixture("frame-3s2b-6m-10k-wind");
  const actual = fixture("frame-3s2b-6m-10k-wind");
  const originalFactors = actual.load_combinations[0].factors;
  const splitFactors = {};
  actual.load_cases = actual.load_cases.flatMap((loadCase) => loadCase.loads.map((load, index) => {
    const id = `${loadCase.id}_${index}`;
    splitFactors[id] = originalFactors[loadCase.id];
    return { id, type: loadCase.type, loads: [load] };
  }));
  actual.load_combinations = [{ id: "ULS", factors: splitFactors }];

  assert.equal(compareStructuralModels(actual, expected).pass, true);

  const windCase = actual.load_cases.find((loadCase) => loadCase.type === "wind");
  actual.load_combinations[0].factors[windCase.id] = 1.2;
  const mismatch = compareStructuralModels(actual, expected);
  assert.ok(mismatch.failures.includes("load combinations"));
});

test("load-combination matching is independent of load-case ordering", () => {
  const expected = fixture("frame-3s2b-6m-10k-wind");
  const actual = fixture("frame-3s2b-6m-10k-wind");
  actual.load_cases.reverse();
  actual.load_combinations[0].factors = Object.fromEntries(
    Object.entries(actual.load_combinations[0].factors).reverse(),
  );

  assert.equal(compareStructuralModels(actual, expected).pass, true);
});

test("unspecified load categories are compatible without weakening explicit categories", () => {
  const expected = fixture();
  const actual = fixture();
  expected.load_cases[0].type = "other";
  assert.equal(compareStructuralModels(actual, expected).pass, true);

  expected.load_cases[0].type = "dead";
  actual.load_cases[0].type = "live";
  const explicitMismatch = compareStructuralModels(actual, expected);
  assert.ok(explicitMismatch.failures.includes("loads"));
  assert.ok(explicitMismatch.failures.includes("load combinations"));
});

test("canonical story loads match legacy fields and replace derived solver loads", () => {
  const expected = fixture("frame3d-simple");
  const actual = fixture("frame3d-simple");
  actual.stories = actual.stories.map((story) => ({
    id: story.id,
    height: story.height,
    elevation: story.elevation,
    floorLoad: story.floor_loads.find((load) => load.type === "dead").value,
    floorLoadUnit: "kN/m2",
  }));
  actual.load_cases[0].loads = [
    { type: "distributed", element: "BX9", wz: -25, story: "F1", source: "story_floor_loads", load_kind: "dead", reference_frame: "global" },
    { type: "distributed", element: "BX10", wz: -25, story: "F1", source: "story_floor_loads", load_kind: "dead", reference_frame: "global" },
    { type: "distributed", element: "BX11", wz: -25, story: "F2", source: "story_floor_loads", load_kind: "dead", reference_frame: "global" },
    { type: "distributed", element: "BX12", wz: -25, story: "F2", source: "story_floor_loads", load_kind: "dead", reference_frame: "global" },
  ];
  assert.equal(compareStructuralModels(actual, expected).pass, true);
  actual.stories[0].floorLoad *= 1.1;
  assert.ok(compareStructuralModels(actual, expected).failures.includes("stories"));
});

test("unconstrained story metadata is ignored when ground truth declares no stories", () => {
  const expected = fixture("portal-complex-ds");
  const actual = fixture("portal-complex-ds");
  actual.stories = [{ id: "F1", height: 9, elevation: 0 }];

  assert.equal(compareStructuralModels(actual, expected).pass, true);

  actual.stories[0].floor_loads = [{ type: "dead", value: 5 }];
  assert.ok(compareStructuralModels(actual, expected).failures.includes("stories"));
});

test("2-D canonical story line loads match equivalent explicit beam loads", () => {
  const expected = fixture("frame-2s1b-6m-10k");
  const actual = fixture("frame-2s1b-6m-10k");
  actual.load_cases[0].loads = [];
  actual.stories = actual.stories.map((story, index) => ({
    ...story,
    elevation: index * story.height,
    floor_loads: [{ type: "dead", value: 60 }],
    dead_load: 60,
  }));

  assert.equal(compareStructuralModels(actual, expected).pass, true);
  actual.stories[0].floor_loads[0].value = 50;
  actual.stories[0].dead_load = 50;
  assert.ok(compareStructuralModels(actual, expected).failures.includes("loads"));
});

test("explicit beam loads do not require duplicate story load metadata", () => {
  const expected = fixture("frame-simple-1s1b");
  const actual = fixture("frame-simple-1s1b");
  actual.stories = actual.stories.map((story) => ({ id: story.id, height: story.height, elevation: 0 }));

  assert.equal(compareStructuralModels(actual, expected).pass, true);
  actual.load_cases[0].loads[0].wz = -40;
  assert.ok(compareStructuralModels(actual, expected).failures.includes("loads"));
});

test("story definitions and entity assignments are checked", () => {
  const expected = fixture("frame3d-simple");
  const wrongDefinition = fixture("frame3d-simple");
  wrongDefinition.stories[0].height += 1;
  const wrongAssignment = fixture("frame3d-simple");
  const assignedElement = wrongAssignment.elements.find((element) => element.story === "F1");
  assignedElement.story = "F2";

  assert.ok(compareStructuralModels(wrongDefinition, expected).failures.includes("stories"));
  assert.ok(compareStructuralModels(wrongAssignment, expected).failures.includes("stories"));
});

test("story array ordering is not treated as engineering semantics", () => {
  const expected = fixture("frame3d-simple");
  const actual = fixture("frame3d-simple");
  actual.stories.reverse();

  assert.equal(compareStructuralModels(actual, expected).pass, true);
});

test("declared story elevations are checked", () => {
  const expected = fixture("frame3d-simple");
  const actual = fixture("frame3d-simple");
  actual.stories[1].elevation += 0.5;

  const mismatch = compareStructuralModels(actual, expected);
  assert.ok(mismatch.failures.includes("stories"));
  assert.match(mismatch.diagnostics.storyFailures.join(" "), /F2: elevation/);
});

test("coordinate tolerance is explicit and does not weaken entity precision", () => {
  const expected = fixture();
  const actual = fixture();
  actual.nodes[1].x += 0.1;

  assert.equal(compareStructuralModels(actual, expected, { coordinate: 0.2 }).pass, true);
  assert.ok(compareStructuralModels(actual, expected, { coordinate: 0.01 }).failures.includes("nodes"));
});

test("scenario evaluation defaults to strict matching while archived v1 remains reproducible", async () => {
  const actual = fixture();
  actual.nodes.push({ id: "extra", x: 3, y: 0, z: 0 });
  const baseAssertion = { type: "model_matches", groundTruthId: "beam-simple-6m" };
  const strict = await evaluateScenario(
    { id: "strict", expect: { assertions: [baseAssertion] } },
    { model: actual },
    0,
  );
  const archived = await evaluateScenario(
    { id: "archived", expect: { assertions: [{ ...baseAssertion, matcherVersion: "v1" }] } },
    { model: actual },
    0,
  );
  assert.equal(strict.metrics.find((metric) => metric.metric === "model_matches").pass, false);
  assert.equal(archived.metrics.find((metric) => metric.metric === "model_matches").pass, true);
});
