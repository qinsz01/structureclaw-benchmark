const assert = require("node:assert/strict");
const test = require("node:test");

const { evaluateScenario } = require("../lib/evaluate.cjs");

function routedState(skillId) {
  return {
    messages: [{
      name: "detect_structure_type",
      content: JSON.stringify({ skillId, key: skillId }),
    }],
  };
}

function scenario(primary, mayAlsoMatch = []) {
  return {
    id: "routing-contract",
    expect: {
      assertions: [{
        type: "skill_match",
        primary,
        mayAlsoMatch,
      }],
    },
  };
}

test("generic fallback does not satisfy a specialist routing target", async () => {
  const result = await evaluateScenario(
    scenario("beam", ["generic"]),
    routedState("generic"),
  );

  assert.equal(result.allPassed, false);
  assert.equal(result.metrics[0].metric, "skill_match");
  assert.equal(result.metrics[0].pass, false);
  assert.equal(result.metrics[0].expected, "beam");
});

test("a declared specialist alias remains an accepted routing target", async () => {
  const result = await evaluateScenario(
    scenario("double-span-beam", ["beam", "generic"]),
    routedState("beam"),
  );

  assert.equal(result.allPassed, true);
  assert.equal(result.metrics[0].expected, "double-span-beam (or: beam)");
});

test("a generic-primary task may accept its declared specialist aliases", async () => {
  const result = await evaluateScenario(
    scenario("generic", ["frame", "portal-frame"]),
    routedState("frame"),
  );

  assert.equal(result.allPassed, true);
});

test("portal frames do not satisfy the distinct frame structural-type class", async () => {
  const result = await evaluateScenario(
    {
      id: "structural-type-contract",
      expect: {
        assertions: [{
          type: "structural_type",
          expected: "frame",
        }],
      },
    },
    { structuralTypeKey: "portal-frame" },
  );

  assert.equal(result.allPassed, false);
  assert.equal(result.metrics[0].metric, "structural_type");
  assert.equal(result.metrics[0].pass, false);
});
