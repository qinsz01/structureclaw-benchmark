const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const {
  canonicalJson,
  compareNumericalResults,
  crossValidateRuns,
  sha256,
} = require("../lib/numerical-ground-truth.cjs");
const {
  checkStaticEquilibrium,
  validateOpenSeesTruthInput,
} = require("../lib/opensees-truth-validation.cjs");
const { checkAnalyticalOracle } = require("../lib/analytical-oracle.cjs");
const { compareAnalysisResults } = require("../lib/analysis-fidelity.cjs");
const {
  INDEPENDENT_SOLVER_VERSION,
  solveIndependentLinearModel,
} = require("../lib/independent-linear-solver.cjs");

const BENCH_ROOT = path.resolve(__dirname, "..");
const SCLAW_ROOT = path.resolve(BENCH_ROOT, "../..");
const MODELS_FILE = path.join(BENCH_ROOT, "fixtures", "ground-truth-models.json");
const DEFAULT_OUTPUT = path.join(BENCH_ROOT, "fixtures", "opensees-ground-truth.json");
const WORKER = path.join(__dirname, "opensees-ground-truth-worker.py");
const REQUIREMENTS = path.join(
  SCLAW_ROOT,
  "backend", "src", "agent-skills", "analysis", "runtime", "requirements.txt",
);
const NUMERIC_TOLERANCES = { absolute: 1e-10, relative: 1e-10 };
const INDEPENDENT_TOLERANCES = { numericAbsolute: 1e-7, numeric: 1e-6 };

function parseArgs(argv) {
  const options = {
    verify: false,
    runs: 2,
    output: DEFAULT_OUTPUT,
    auditOutput: null,
    python: null,
    modelIds: [],
  };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--verify") options.verify = true;
    else if (arg === "--python") options.python = argv[++index];
    else if (arg === "--runs") options.runs = Number(argv[++index]);
    else if (arg === "--output") options.output = path.resolve(argv[++index]);
    else if (arg === "--audit-output") options.auditOutput = path.resolve(argv[++index]);
    else if (arg === "--model") options.modelIds.push(argv[++index]);
    else throw new Error(`Unknown argument: ${arg}`);
  }
  if (!Number.isInteger(options.runs) || options.runs < 2) {
    throw new Error("--runs must be an integer >= 2; single-run truth generation is forbidden");
  }
  return options;
}

function pinnedPackageVersion() {
  const requirements = fs.readFileSync(REQUIREMENTS, "utf8");
  const match = requirements.match(/^openseespy==([^\s]+)$/m);
  if (!match) throw new Error(`Pinned openseespy version not found in ${REQUIREMENTS}`);
  return match[1];
}

function pythonCandidates(explicit) {
  if (explicit) return [explicit];
  const executable = process.platform === "win32" ? "python.exe" : "python";
  return [
    process.env.SCLAW_ANALYSIS_PYTHON,
    path.join(SCLAW_ROOT, "backend", ".venv", process.platform === "win32" ? "Scripts" : "bin", executable),
    process.env.USERPROFILE
      ? path.join(process.env.USERPROFILE, ".structureclaw", ".venv", process.platform === "win32" ? "Scripts" : "bin", executable)
      : null,
    "python3",
    "python",
  ].filter(Boolean);
}

function probePython(candidate) {
  const probe = spawnSync(candidate, [
    "-c",
    "import importlib.metadata, json; import openseespy.opensees as ops; "
      + "print(json.dumps({'packageVersion': importlib.metadata.version('openseespy'), 'version': str(ops.version())}))",
  ], { encoding: "utf8", windowsHide: true, timeout: 30_000 });
  if (probe.status !== 0) return null;
  try {
    const lines = probe.stdout.trim().split(/\r?\n/);
    return JSON.parse(lines.at(-1));
  } catch {
    return null;
  }
}

function resolvePython(explicit, expectedPackageVersion) {
  const mismatches = [];
  for (const candidate of pythonCandidates(explicit)) {
    const version = probePython(candidate);
    if (!version) continue;
    if (version.packageVersion !== expectedPackageVersion) {
      mismatches.push(`${candidate}=${version.packageVersion}`);
      if (explicit) {
        throw new Error(
          `OpenSeesPy package ${version.packageVersion} at '${candidate}' does not match pinned ${expectedPackageVersion}`,
        );
      }
      continue;
    }
    return { command: candidate, ...version };
  }
  throw new Error(
    "No usable pinned OpenSeesPy Python was found. Pass --python or set SCLAW_ANALYSIS_PYTHON; "
      + `truth values were not written.${mismatches.length ? ` Mismatches: ${mismatches.join(", ")}` : ""}`,
  );
}

function runWorker(python, input, output) {
  const child = spawnSync(python, [
    WORKER,
    "--sclaw-root", SCLAW_ROOT,
    "--input", input,
    "--output", output,
  ], {
    cwd: BENCH_ROOT,
    encoding: "utf8",
    windowsHide: true,
    timeout: 5 * 60 * 1000,
    maxBuffer: 10 * 1024 * 1024,
  });
  if (child.error) throw child.error;
  if (child.status !== 0) {
    const detail = [child.stderr, child.stdout].filter(Boolean).join("\n").trim();
    throw new Error(`OpenSees worker failed (${child.status}): ${detail}`);
  }
  if (!fs.existsSync(output)) throw new Error("OpenSees worker completed without an output file");
  return JSON.parse(fs.readFileSync(output, "utf8"));
}

function reordered(values, runIndex) {
  if (!Array.isArray(values) || runIndex === 0 || values.length < 2) return values;
  if (runIndex === 1) return [...values].reverse();
  const offset = runIndex % values.length;
  return [...values.slice(offset), ...values.slice(0, offset)];
}

function executionVariant(model, runIndex) {
  const variant = structuredClone(model);
  for (const field of ["nodes", "elements", "materials", "sections", "load_cases", "load_combinations"]) {
    variant[field] = reordered(variant[field], runIndex);
  }
  variant.load_cases = (variant.load_cases || []).map((loadCase) => ({
    ...loadCase,
    loads: reordered(loadCase.loads, runIndex),
  }));
  variant.load_combinations = (variant.load_combinations || []).map((combination) => ({
    ...combination,
    factors: Object.fromEntries(reordered(Object.entries(combination.factors || {}), runIndex)),
  }));
  return {
    name: runIndex === 0 ? "canonical-order" : `reordered-${runIndex}`,
    model: variant,
  };
}

function calculateModel(entry, options, tempRoot, pinnedVersion) {
  const preflight = validateOpenSeesTruthInput(entry.model);
  if (!preflight.pass) {
    throw new Error(`${entry.id}: OpenSees input preflight failed: ${preflight.issues.join("; ")}`);
  }
  const modelDir = path.join(tempRoot, entry.id.replace(/[^a-zA-Z0-9_.-]/g, "_"));
  fs.mkdirSync(modelDir);
  const runs = [];
  for (let runIndex = 0; runIndex < options.runs; runIndex += 1) {
    const variant = executionVariant(entry.model, runIndex);
    const inputPath = path.join(modelDir, `input-${runIndex + 1}.json`);
    fs.writeFileSync(inputPath, canonicalJson({
      modelId: entry.id,
      executionVariant: variant.name,
      model: variant.model,
    }), "utf8");
    const outputPath = path.join(modelDir, `run-${runIndex + 1}.json`);
    const run = runWorker(options.python.command, inputPath, outputPath);
    if (run.modelId !== entry.id) throw new Error(`Worker returned wrong model id for ${entry.id}`);
    if (run.solver?.packageVersion !== pinnedVersion) {
      throw new Error(`${entry.id}: worker used unpinned OpenSeesPy ${run.solver?.packageVersion}`);
    }
    runs.push(run);
  }
  if (new Set(runs.map((run) => run.executionVariant)).size !== runs.length) {
    throw new Error(`${entry.id}: independent runs did not use distinct execution variants`);
  }
  if (new Set(runs.map((run) => canonicalJson(run.solverConfiguration))).size < 2) {
    throw new Error(`${entry.id}: independent runs did not use at least two OpenSees solver configurations`);
  }
  const verification = crossValidateRuns(runs, NUMERIC_TOLERANCES);
  if (runs.some((run) => canonicalJson(run.analysisSelection) !== canonicalJson(runs[0].analysisSelection))) {
    throw new Error(`${entry.id}: independent runs used different analysis selections`);
  }
  const equilibrium = runs.map((run, index) => {
    const check = checkStaticEquilibrium(entry.model, run.result, run.analysisSelection);
    if (!check.pass) {
      throw new Error(
        `${entry.id}: run ${index + 1} failed equilibrium: ${check.failures.join("; ")}; `
          + `forceResidual=${JSON.stringify(check.forceResidual)}, `
          + `externalMoment=${JSON.stringify(check.externalMoment)}, `
          + `reactionMoment=${JSON.stringify(check.reactionMoment)}, `
          + `momentResidual=${JSON.stringify(check.momentResidual)}`,
      );
    }
    return check;
  });
  const analytical = runs.map((run, index) => {
    const check = checkAnalyticalOracle(entry.id, entry.model, run.result);
    if (!check.pass) {
      throw new Error(`${entry.id}: run ${index + 1} failed analytical oracle: ${check.failures.join("; ")}`);
    }
    return check;
  });
  let independentLinearSolver = null;
  if (entry.model.coordinate_system?.dimension === "2d") {
    const independentResult = solveIndependentLinearModel(entry.model);
    const comparison = compareAnalysisResults(
      independentResult,
      runs[0].result,
      {
        nodeMapping: Object.fromEntries(entry.model.nodes.map((node) => [String(node.id), String(node.id)])),
        elementMapping: Object.fromEntries(
          entry.model.elements.map((element) => [String(element.id), String(element.id)]),
        ),
        elementOrientation: Object.fromEntries(
          entry.model.elements.map((element) => [String(element.id), "same"]),
        ),
      },
      INDEPENDENT_TOLERANCES,
    );
    if (!comparison.pass) {
      throw new Error(
        `${entry.id}: independent direct-stiffness solution disagrees: ${comparison.failures.slice(0, 5).join("; ")}`,
      );
    }
    independentLinearSolver = {
      name: "Independent direct-stiffness linear solver",
      version: INDEPENDENT_SOLVER_VERSION,
      method: entry.model.elements.every((element) => element.type === "truss")
        ? "2-D linear truss direct stiffness"
        : "2-D Euler-Bernoulli frame direct stiffness",
      implementation: "lib/independent-linear-solver.cjs",
      inputSha256: sha256(entry.model),
      outputSha256: sha256(independentResult),
      comparedValues: comparison.comparedValues,
      maxAbsoluteDifference: comparison.maxAbsoluteDifference,
      maxRelativeDifference: comparison.maxRelativeDifference,
      tolerances: comparison.tolerances,
    };
  }
  return {
    modelId: entry.id,
    inputSha256: sha256(entry.model),
    solver: runs[0].solver,
    analysisSelection: runs[0].analysisSelection,
    verification: {
      ...verification,
      executionVariants: runs.map((run) => run.executionVariant),
      solverConfigurations: runs.map((run) => run.solverConfiguration),
      equilibrium,
      analytical,
      independentLinearSolver,
    },
    result: runs[0].result,
  };
}

function validateFixtureIds(entries) {
  const ids = entries.map((entry) => entry.id);
  if (ids.length !== new Set(ids).size) throw new Error("Ground-truth model ids must be unique");
  if (ids.length === 0) throw new Error("No ground-truth models found");
}

function verifyCommitted(committed, generated, sourceHash) {
  if (committed.schemaVersion !== 1) throw new Error("Unsupported committed numerical truth schema");
  if (committed.sourceModelFileSha256 !== sourceHash) {
    throw new Error("Committed numerical truth was generated from a different ground-truth model file");
  }
  const expectedById = new Map(committed.models.map((entry) => [entry.modelId, entry]));
  if (expectedById.size !== generated.models.length || committed.models.length !== generated.models.length) {
    throw new Error("Committed and regenerated numerical truth model sets differ");
  }
  for (const actual of generated.models) {
    const expected = expectedById.get(actual.modelId);
    if (!expected) throw new Error(`Committed numerical truth is missing ${actual.modelId}`);
    if (expected.inputSha256 !== actual.inputSha256) throw new Error(`${actual.modelId}: input hash changed`);
    if (canonicalJson(expected.solver) !== canonicalJson(actual.solver)) {
      throw new Error(`${actual.modelId}: solver identity changed`);
    }
    if (canonicalJson(expected.analysisSelection) !== canonicalJson(actual.analysisSelection)) {
      throw new Error(`${actual.modelId}: analysis selection changed`);
    }
    if (canonicalJson(expected.verification?.independentLinearSolver)
      !== canonicalJson(actual.verification?.independentLinearSolver)) {
      throw new Error(`${actual.modelId}: independent linear-solver verification changed`);
    }
    const comparison = compareNumericalResults(expected.result, actual.result, NUMERIC_TOLERANCES);
    if (!comparison.pass) {
      throw new Error(`${actual.modelId}: committed truth disagrees: ${comparison.failures.slice(0, 5).join("; ")}`);
    }
  }
}

function main() {
  const options = parseArgs(process.argv.slice(2));
  const pinnedVersion = pinnedPackageVersion();
  options.python = resolvePython(options.python, pinnedVersion);
  const entries = JSON.parse(fs.readFileSync(MODELS_FILE, "utf8"));
  validateFixtureIds(entries);
  const requestedIds = new Set(options.modelIds);
  const selectedEntries = requestedIds.size > 0
    ? entries.filter((entry) => requestedIds.has(entry.id))
    : entries;
  if (requestedIds.size > 0 && selectedEntries.length !== requestedIds.size) {
    const known = new Set(entries.map((entry) => entry.id));
    const missing = [...requestedIds].filter((id) => !known.has(id));
    throw new Error(`Unknown ground-truth model id(s): ${missing.join(", ")}`);
  }
  if (options.verify && requestedIds.size > 0) {
    throw new Error("--verify always covers the complete model set and cannot be combined with --model");
  }
  const sourceHash = sha256(entries);
  const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), "structureclaw-opensees-truth-"));
  try {
    const models = [];
    const failures = [];
    for (const entry of selectedEntries) {
      process.stdout.write(`[OpenSees truth] ${entry.id} (${options.runs} independent runs)\n`);
      try {
        models.push(calculateModel(entry, options, tempRoot, pinnedVersion));
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        failures.push({ modelId: entry.id, message });
        process.stderr.write(`[OpenSees truth] ${entry.id} FAILED: ${message}\n`);
      }
    }
    if (options.auditOutput) {
      const audit = {
        schemaVersion: 1,
        sourceModelFileSha256: sourceHash,
        solver: options.python,
        requestedIndependentRuns: options.runs,
        totalModels: selectedEntries.length,
        successfulModelIds: models.map((entry) => entry.modelId),
        failures,
      };
      fs.writeFileSync(options.auditOutput, `${JSON.stringify(audit, null, 2)}\n`, "utf8");
    }
    if (failures.length > 0) {
      throw new Error(
        `${failures.length}/${selectedEntries.length} OpenSees truth models failed; no new truth file was written. `
          + failures.map((failure) => failure.modelId).join(", "),
      );
    }
    const generated = {
      schemaVersion: 1,
      sourceModelFileSha256: sourceHash,
      requiredIndependentRuns: options.runs,
      numericTolerances: NUMERIC_TOLERANCES,
      models,
    };
    if (requestedIds.size > 0) {
      process.stdout.write(
        `Smoke-verified ${models.length} selected model(s); canonical truth file was not written.\n`,
      );
      return;
    }
    if (options.verify) {
      if (!fs.existsSync(options.output)) throw new Error(`No committed truth file at ${options.output}`);
      verifyCommitted(JSON.parse(fs.readFileSync(options.output, "utf8")), generated, sourceHash);
      process.stdout.write(`Verified ${models.length} models against ${options.output}\n`);
      return;
    }
    fs.writeFileSync(options.output, `${JSON.stringify(generated, null, 2)}\n`, "utf8");
    process.stdout.write(`Wrote ${models.length} cross-validated models to ${options.output}\n`);
  } finally {
    fs.rmSync(tempRoot, { recursive: true, force: true });
  }
}

if (require.main === module) {
  try {
    main();
  } catch (error) {
    process.stderr.write(`${error.stack || error.message || String(error)}\n`);
    process.exitCode = 1;
  }
}

module.exports = { executionVariant };
