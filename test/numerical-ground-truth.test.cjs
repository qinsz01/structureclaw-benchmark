const assert = require("node:assert/strict");
const test = require("node:test");

const {
  compareNumericalResults,
  crossValidateRuns,
  sha256,
} = require("../lib/numerical-ground-truth.cjs");

function run(result, version = "3.7.1") {
  return {
    solver: {
      name: "OpenSeesPy",
      packageVersion: "3.7.1.2",
      runtimePackage: "openseespywin",
      runtimePackageVersion: "3.8.0.0",
      version,
    },
    result,
  };
}

test("canonical hashes ignore object insertion order", () => {
  assert.equal(sha256({ a: 1, b: 2 }), sha256({ b: 2, a: 1 }));
});

test("independent runs must agree within both numeric tolerances", () => {
  const first = { displacements: { N1: { ux: 1e-3 } }, status: "success" };
  const second = { status: "success", displacements: { N1: { ux: 1e-3 + 1e-13 } } };
  const verification = crossValidateRuns([run(first), run(second)]);
  assert.equal(verification.runCount, 2);
  assert.equal(verification.comparedNumbers, 1);
});

test("materially different solver results fail cross-validation", () => {
  const first = run({ reactions: { N1: { fz: 100 } } });
  const second = run({ reactions: { N1: { fz: 101 } } });
  assert.throws(() => crossValidateRuns([first, second]), /disagree/);
});

test("two runs and a stable OpenSees version are mandatory", () => {
  assert.throws(() => crossValidateRuns([run({ value: 1 })]), /At least two/);
  assert.throws(
    () => crossValidateRuns([run({ value: 1 }, "3.7.1"), run({ value: 1 }, "3.7.2")]),
    /same identified OpenSeesPy version/,
  );
});

test("shape and nonnumeric metadata differences are rejected", () => {
  const comparison = compareNumericalResults(
    { status: "success", values: [1, 2] },
    { status: "failed", values: [1] },
  );
  assert.equal(comparison.pass, false);
  assert.ok(comparison.failures.length >= 1);
});
