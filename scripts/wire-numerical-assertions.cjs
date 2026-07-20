const fs = require("node:fs");
const path = require("node:path");

const BENCH_ROOT = path.resolve(__dirname, "..");
const SCENARIOS_DIR = path.join(BENCH_ROOT, "scenarios");
const TRUTH_FILE = path.join(BENCH_ROOT, "fixtures", "opensees-ground-truth.json");
const ELIGIBLE_FAMILIES = new Set(["standard_workflow", "multimodal_reverse_engineering"]);

function collectJsonFiles(directory) {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const fullPath = path.join(directory, entry.name);
    if (entry.isDirectory()) return collectJsonFiles(fullPath);
    return entry.isFile() && entry.name.endsWith(".json") ? [fullPath] : [];
  }).sort();
}

function assertionGroups(scenario) {
  const groups = [];
  if (Array.isArray(scenario.expect?.assertions)) groups.push(scenario.expect.assertions);
  for (const turn of scenario.turns || []) {
    if (Array.isArray(turn.assertions)) groups.push(turn.assertions);
  }
  return groups;
}

function wireScenario(scenario, truthIds) {
  if (!ELIGIBLE_FAMILIES.has(scenario.taskFamily)) return { changed: false, eligible: 0 };
  let changed = false;
  let eligible = 0;
  for (const assertions of assertionGroups(scenario)) {
    if (!assertions.some((assertion) => assertion.type === "has_analysis")) continue;
    const modelAssertions = assertions.filter((assertion) => assertion.type === "model_matches");
    for (const modelAssertion of modelAssertions) {
      eligible += 1;
      if (!truthIds.has(modelAssertion.groundTruthId)) {
        throw new Error(`${scenario.id}: numerical truth is missing '${modelAssertion.groundTruthId}'`);
      }
      const alreadyPresent = assertions.some((assertion) => (
        assertion.type === "numerical_matches"
        && assertion.groundTruthId === modelAssertion.groundTruthId
      ));
      if (alreadyPresent) continue;
      const modelIndex = assertions.indexOf(modelAssertion);
      assertions.splice(modelIndex + 1, 0, {
        type: "numerical_matches",
        groundTruthId: modelAssertion.groundTruthId,
        tolerances: {
          ...(modelAssertion.tolerances || {}),
          numeric: 0.01,
          numericAbsolute: 1e-8,
        },
      });
      changed = true;
    }
  }
  if (eligible > 0 && !scenario.evaluationFocus.includes("numerical_match")) {
    scenario.evaluationFocus.push("numerical_match");
    changed = true;
  }
  return { changed, eligible };
}

function main() {
  const write = process.argv.slice(2).includes("--write");
  if (!fs.existsSync(TRUTH_FILE)) {
    throw new Error("Numerical assertions cannot be wired before a complete OpenSees truth file exists");
  }
  const truth = JSON.parse(fs.readFileSync(TRUTH_FILE, "utf8"));
  const truthIds = new Set((truth.models || []).map((entry) => entry.modelId));
  const files = collectJsonFiles(SCENARIOS_DIR);
  let eligible = 0;
  const changedFiles = [];
  for (const file of files) {
    const scenario = JSON.parse(fs.readFileSync(file, "utf8"));
    const result = wireScenario(scenario, truthIds);
    eligible += result.eligible;
    if (!result.changed) continue;
    changedFiles.push(path.relative(BENCH_ROOT, file).replace(/\\/g, "/"));
    if (write) fs.writeFileSync(file, `${JSON.stringify(scenario, null, 2)}\n`, "utf8");
  }
  if (!write && changedFiles.length > 0) {
    throw new Error(
      `${changedFiles.length} scenario files are missing numerical assertions; run npm run truth:wire`,
    );
  }
  process.stdout.write(
    `${write ? "Wired" : "Verified"} ${eligible} numerical assertion targets across ${files.length} scenarios.\n`,
  );
}

if (require.main === module) {
  try {
    main();
  } catch (error) {
    process.stderr.write(`${error.stack || error.message || String(error)}\n`);
    process.exitCode = 1;
  }
}

module.exports = { wireScenario };
