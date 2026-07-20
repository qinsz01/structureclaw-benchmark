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

test("schema and unit contracts are part of engineering fidelity", () => {
  const expected = fixture();
  const wrongSchema = fixture();
  wrongSchema.schema_version = "1.0.0";
  const wrongUnits = fixture();
  wrongUnits.unit_system = "US";

  assert.ok(compareStructuralModels(wrongSchema, expected).failures.includes("schema version"));
  assert.ok(compareStructuralModels(wrongUnits, expected).failures.includes("unit system"));
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

test("load-combination factors are checked", () => {
  const expected = fixture("frame3d-simple");
  const actual = fixture("frame3d-simple");
  actual.load_combinations[0].factors.D = 1.0;
  const comparison = compareStructuralModels(actual, expected);
  assert.equal(comparison.pass, false);
  assert.ok(comparison.failures.includes("load combinations"));
});

test("story definitions and entity assignments are checked", () => {
  const expected = fixture("frame-simple-1s1b");
  const wrongDefinition = fixture("frame-simple-1s1b");
  wrongDefinition.stories[0].height += 1;
  const wrongAssignment = fixture("frame-simple-1s1b");
  const assignedElement = wrongAssignment.elements.find((element) => element.story);
  assignedElement.story = "wrong-story";

  assert.ok(compareStructuralModels(wrongDefinition, expected).failures.includes("stories"));
  assert.ok(compareStructuralModels(wrongAssignment, expected).failures.includes("stories"));
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
