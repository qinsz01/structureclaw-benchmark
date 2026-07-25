const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const { compareStructuralModels } = require("../lib/model-fidelity.cjs");

const BENCH_ROOT = path.resolve(__dirname, "..");
const SCLAW_ROOT = path.resolve(BENCH_ROOT, "../..");
const SCENARIOS_ROOT = path.join(BENCH_ROOT, "scenarios");
const PRODUCTION_ROOT = path.join(SCLAW_ROOT, "backend", "src");
const BACKEND_TEST_ROOT = path.join(SCLAW_ROOT, "backend", "tests");
const EVALUATOR_ROOT = path.join(BENCH_ROOT, "lib");
const SOURCE_EXTENSIONS = new Set([".cjs", ".js", ".json", ".md", ".mjs", ".py", ".ts", ".yaml", ".yml"]);

function walkFiles(root, shouldSkip = () => false) {
  const files = [];
  for (const entry of fs.readdirSync(root, { withFileTypes: true })) {
    const fullPath = path.join(root, entry.name);
    if (shouldSkip(fullPath, entry)) continue;
    if (entry.isDirectory()) {
      files.push(...walkFiles(fullPath, shouldSkip));
    } else if (SOURCE_EXTENSIONS.has(path.extname(entry.name))) {
      files.push(fullPath);
    }
  }
  return files;
}

function loadScenarios() {
  return walkFiles(SCENARIOS_ROOT)
    .filter((filePath) => path.extname(filePath) === ".json")
    .map((filePath) => ({
      filePath,
      scenario: JSON.parse(fs.readFileSync(filePath, "utf8")),
    }));
}

function scenarioMessages(scenario) {
  if (Array.isArray(scenario.turns)) {
    return scenario.turns.map((turn, index) => ({
      label: `${scenario.id}#turn${index + 1}`,
      text: String(turn.message ?? ""),
    }));
  }
  return [{ label: scenario.id, text: String(scenario.message ?? "") }];
}

function findScenarioIdLeaks(files, scenarioIds) {
  const leaks = [];
  for (const filePath of files) {
    const content = fs.readFileSync(filePath, "utf8");
    for (const scenarioId of scenarioIds) {
      if (content.includes(scenarioId)) {
        leaks.push(`${path.relative(SCLAW_ROOT, filePath)} -> ${scenarioId}`);
      }
    }
  }
  return leaks;
}

function normalizeWords(value) {
  return (String(value).toLowerCase().match(/[a-z0-9][a-z0-9._/-]*/g) || []).join(" ");
}

function normalizeCharacters(value) {
  return String(value).toLowerCase().replace(/[^\p{L}\p{N}]+/gu, "");
}

function distinctivePromptFragments() {
  const fragments = [];
  for (const { scenario } of loadScenarios()) {
    for (const message of scenarioMessages(scenario)) {
      const words = normalizeWords(message.text).split(" ").filter(Boolean);
      for (let index = 0; index + 14 <= words.length; index += 1) {
        fragments.push({
          label: message.label,
          kind: "word",
          text: words.slice(index, index + 14).join(" "),
        });
      }
      const characters = normalizeCharacters(message.text);
      if (/[\u3400-\u9fff]/u.test(characters)) {
        for (let index = 0; index + 36 <= characters.length; index += 6) {
          fragments.push({
            label: message.label,
            kind: "character",
            text: characters.slice(index, index + 36),
          });
        }
      }
    }
  }
  return fragments;
}

test("production agent behavior contains no benchmark scenario ids", () => {
  const scenarioIds = loadScenarios().map(({ scenario }) => scenario.id);
  const productionFiles = walkFiles(
    PRODUCTION_ROOT,
    (fullPath, entry) => entry.isDirectory() && path.basename(fullPath) === "__tests__",
  );

  assert.deepEqual(findScenarioIdLeaks(productionFiles, scenarioIds), []);
});

test("benchmark evaluators contain no per-scenario id branches", () => {
  const scenarioIds = loadScenarios().map(({ scenario }) => scenario.id);
  const evaluatorFiles = walkFiles(EVALUATOR_ROOT);

  assert.deepEqual(findScenarioIdLeaks(evaluatorFiles, scenarioIds), []);
});

test("agent regression tests do not copy benchmark prompts verbatim", () => {
  const benchmarkMessages = loadScenarios()
    .flatMap(({ scenario }) => scenarioMessages(scenario))
    .filter(({ text }) => text.length >= 30);
  const testFiles = [
    ...walkFiles(PRODUCTION_ROOT)
      .filter((filePath) => filePath.includes(`${path.sep}__tests__${path.sep}`)),
    ...walkFiles(BACKEND_TEST_ROOT),
  ];
  const leaks = [];
  for (const filePath of testFiles) {
    const content = fs.readFileSync(filePath, "utf8");
    for (const message of benchmarkMessages) {
      if (content.includes(message.text)) {
        leaks.push(`${path.relative(SCLAW_ROOT, filePath)} -> ${message.label}`);
      }
    }
  }

  assert.deepEqual(leaks, []);
});

test("production behavior does not copy distinctive benchmark prompt fragments", () => {
  const productionFiles = walkFiles(
    PRODUCTION_ROOT,
    (fullPath, entry) => entry.isDirectory() && path.basename(fullPath) === "__tests__",
  );
  const normalizedProduction = productionFiles.map((filePath) => {
    const content = fs.readFileSync(filePath, "utf8");
    return {
      filePath,
      word: normalizeWords(content),
      character: normalizeCharacters(content),
    };
  });
  const leaks = [];
  for (const fragment of distinctivePromptFragments()) {
    for (const production of normalizedProduction) {
      if (production[fragment.kind].includes(fragment.text)) {
        leaks.push(
          `${path.relative(SCLAW_ROOT, production.filePath)} -> ${fragment.label}: ${fragment.text}`,
        );
      }
    }
  }

  assert.deepEqual(leaks, []);
});

test("unusual magnitudes allow either justified clarification or execution", () => {
  const affected = loadScenarios()
    .filter(({ scenario }) => scenario.category === "unrealistic-values");

  assert.ok(affected.length > 0);
  for (const { filePath, scenario } of affected) {
    const assertions = scenario.expect?.assertions ?? [];
    const assertionTypes = assertions.map((assertion) => assertion.type);
    assert.ok(
      assertionTypes.includes("analysis_or_interaction"),
      `${path.relative(BENCH_ROOT, filePath)} must not force abstention based only on magnitude`,
    );
    assert.ok(
      !assertionTypes.includes("should_not_analyze"),
      `${path.relative(BENCH_ROOT, filePath)} must permit a supported, self-consistent analysis`,
    );
  }
});

test("structural scoring remains strict under unseen geometric and load perturbations", () => {
  const fixtures = JSON.parse(fs.readFileSync(
    path.join(BENCH_ROOT, "fixtures", "ground-truth-models.json"),
    "utf8",
  ));
  const base = structuredClone(fixtures.find((entry) => entry.id === "beam-simple-6m").model);
  const expected = structuredClone(base);
  const coordinateScale = 1.137;
  const loadScale = 1.731;
  for (const node of expected.nodes) {
    node.x *= coordinateScale;
    node.y *= coordinateScale;
    node.z *= coordinateScale;
  }
  for (const loadCase of expected.load_cases) {
    for (const load of loadCase.loads) {
      for (const key of ["magnitude", "fx", "fy", "fz", "mx", "my", "mz", "wx", "wy", "wz"]) {
        if (Number.isFinite(load[key])) load[key] *= loadScale;
      }
      if (Number.isFinite(load.x)) load.x *= coordinateScale;
      if (Number.isFinite(load.start)) load.start *= coordinateScale;
      if (Number.isFinite(load.end)) load.end *= coordinateScale;
    }
  }

  assert.equal(compareStructuralModels(structuredClone(expected), expected).pass, true);

  const staleGeometry = structuredClone(expected);
  staleGeometry.nodes.at(-1).x = base.nodes.at(-1).x;
  const geometryComparison = compareStructuralModels(staleGeometry, expected);
  assert.equal(geometryComparison.pass, false);
  assert.ok(geometryComparison.failures.includes("nodes"));

  const staleLoad = structuredClone(expected);
  staleLoad.load_cases[0].loads[0].wz /= loadScale;
  const loadComparison = compareStructuralModels(staleLoad, expected);
  assert.equal(loadComparison.pass, false);
  assert.ok(loadComparison.failures.includes("loads"));

  const wrongRestraint = structuredClone(expected);
  wrongRestraint.nodes[0].restraints[0] = !wrongRestraint.nodes[0].restraints[0];
  const restraintComparison = compareStructuralModels(wrongRestraint, expected);
  assert.equal(restraintComparison.pass, false);
  assert.ok(restraintComparison.failures.includes("restraints"));
});
