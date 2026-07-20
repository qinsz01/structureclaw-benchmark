const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const { compareAnalysisResults } = require("../lib/analysis-fidelity.cjs");

const mappings = {
  nodeMapping: { N1: "node-a" },
  elementMapping: { E1: "member-a" },
  elementOrientation: { E1: "same" },
};

function expectedResult() {
  return {
    displacements: { N1: { ux: 0.01, uz: -0.02 } },
    reactions: { N1: { fx: -10, fz: 20 } },
    forces: {
      E1: {
        axial: -5,
        n1: { N: -5, V: 3, M: 2 },
        n2: { N: 5, V: -3, M: 4 },
      },
    },
  };
}

test("analysis comparison follows model entity mappings", () => {
  const actual = {
    data: {
      displacements: { "node-a": { ux: 0.01, uz: -0.02 } },
      reactions: { "node-a": { fx: -10, fz: 20 } },
      forces: {
        "member-a": {
          axial: -5,
          n1: { N: -5, V: 3, M: 2 },
          n2: { N: 5, V: -3, M: 4 },
        },
      },
    },
  };
  assert.equal(compareAnalysisResults(actual, expectedResult(), mappings).pass, true);
});

test("signed end forces fail while a reversed element orientation is normalized", () => {
  const wrongSign = expectedResult();
  wrongSign.forces.E1.n1.M *= -1;
  assert.equal(compareAnalysisResults(wrongSign, expectedResult(), {
    nodeMapping: { N1: "N1" },
    elementMapping: { E1: "E1" },
    elementOrientation: { E1: "same" },
  }).pass, false);

  const reversed = {
    displacements: { "node-a": { ux: 0.01, uz: -0.02 } },
    reactions: { "node-a": { fx: -10, fz: 20 } },
    forces: {
      "member-a": {
        axial: -5,
        n1: { N: -5, V: 3, M: 4 },
        n2: { N: 5, V: -3, M: 2 },
      },
    },
  };
  assert.equal(compareAnalysisResults(reversed, expectedResult(), {
    ...mappings,
    elementOrientation: { E1: "reversed" },
  }).pass, true);
});

test("wrong response values and missing fields fail", () => {
  const wrong = {
    displacements: { "node-a": { ux: 0.5, uz: -0.02 } },
    reactions: {},
    forces: {},
  };
  const comparison = compareAnalysisResults(wrong, expectedResult(), mappings);
  assert.equal(comparison.pass, false);
  assert.ok(comparison.failures.some((failure) => failure.includes("displacements.N1.ux")));
  assert.ok(comparison.failures.some((failure) => failure.includes("reactions.N1")));
});

test("relative numerical tolerance is explicit", () => {
  const expected = { displacements: { N1: { ux: 1 } } };
  const actual = { displacements: { "node-a": { ux: 1.04 } } };
  assert.equal(compareAnalysisResults(actual, expected, mappings, { numeric: 0.05 }).pass, true);
  assert.equal(compareAnalysisResults(actual, expected, mappings, { numeric: 0.01 }).pass, false);
});

test("legacy OpenSees 2-D frame responses are normalized to global X-Y-Z signs", () => {
  const expected = {
    analysisMode: "opensees_2d_frame",
    responseCoordinateConvention: "global-xyz",
    displacements: { N1: { ry: 0.1 } },
    reactions: { N1: { my: -10 } },
  };
  const actual = {
    data: {
      analysisMode: "opensees_2d_frame",
      displacements: { "node-a": { ry: -0.1 } },
      reactions: { "node-a": { my: 10 } },
    },
  };
  assert.equal(compareAnalysisResults(actual, expected, mappings).pass, true);
});

test("all committed OpenSees truth responses pass signed self-comparison", () => {
  const payload = JSON.parse(fs.readFileSync(
    path.join(__dirname, "..", "fixtures", "opensees-ground-truth.json"),
    "utf8",
  ));
  for (const entry of payload.models) {
    const nodeIds = Object.keys(entry.result.displacements || {});
    const elementIds = Object.keys(entry.result.forces || {});
    const comparison = compareAnalysisResults(entry.result, entry.result, {
      nodeMapping: Object.fromEntries(nodeIds.map((id) => [id, id])),
      elementMapping: Object.fromEntries(elementIds.map((id) => [id, id])),
      elementOrientation: Object.fromEntries(elementIds.map((id) => [id, "same"])),
    }, { numeric: 0.01, numericAbsolute: 1e-8 });
    assert.equal(comparison.pass, true, `${entry.modelId}: ${comparison.failures.join("; ")}`);
  }
});
