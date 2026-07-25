const fs = require("node:fs");
const path = require("node:path");
const { createHash } = require("node:crypto");

const { aggregateFormalRows } = require("../lib/formal-statistics.cjs");

const BENCH_ROOT = path.resolve(__dirname, "..");
const DEFAULT_MATRIX = path.join(BENCH_ROOT, "experiments", "formal-matrix.json");

function usage() {
  return [
    "Usage:",
    "  node scripts/aggregate-formal-results.cjs --input-dir <formal-results> --output <summary.json>",
    "",
    "Options:",
    "  --matrix <file>       Defaults to experiments/formal-matrix.json.",
    "  --allow-incomplete    Produce diagnostics without accepting the result set as complete.",
  ].join("\n");
}

function requireValue(argv, index, flag) {
  const value = argv[index];
  if (!value || value.startsWith("--")) throw new Error(`Missing value for ${flag}`);
  return value;
}

function parseArgs(argv) {
  const options = {
    inputDir: null,
    outputPath: null,
    matrixPath: DEFAULT_MATRIX,
    allowIncomplete: false,
  };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--help" || arg === "-h") {
      process.stdout.write(`${usage()}\n`);
      process.exit(0);
    } else if (arg === "--input-dir") {
      options.inputDir = path.resolve(requireValue(argv, ++index, arg));
    } else if (arg === "--output") {
      options.outputPath = path.resolve(requireValue(argv, ++index, arg));
    } else if (arg === "--matrix") {
      options.matrixPath = path.resolve(requireValue(argv, ++index, arg));
    } else if (arg === "--allow-incomplete") {
      options.allowIncomplete = true;
    } else {
      throw new Error(`Unknown option: ${arg}\n\n${usage()}`);
    }
  }
  if (!options.inputDir || !options.outputPath) {
    throw new Error(`--input-dir and --output are required\n\n${usage()}`);
  }
  return options;
}

function collectJsonFiles(directory) {
  return fs.readdirSync(directory, { withFileTypes: true })
    .sort((a, b) => a.name.localeCompare(b.name))
    .flatMap((entry) => {
      const fullPath = path.join(directory, entry.name);
      if (entry.isDirectory()) return collectJsonFiles(fullPath);
      return entry.isFile() && entry.name.endsWith(".json") ? [fullPath] : [];
    });
}

function loadFormalRecords(inputDir) {
  const records = [];
  for (const file of collectJsonFiles(inputDir)) {
    let record;
    try {
      record = JSON.parse(fs.readFileSync(file, "utf8"));
    } catch {
      continue;
    }
    if (!Array.isArray(record.scenarios) || !record.run) continue;
    records.push({ file, record });
  }
  return records;
}

const TASK_FAMILY_BY_MATRIX_FAMILY = {
  standard: "standard_workflow",
  interactive: "interactive_robustness",
  multimodal: "multimodal_reverse_engineering",
};

function batchKey({ family, modelId, visionModelId = null, mode, repeatId }) {
  return [family, modelId, visionModelId || "", mode, repeatId].join("\0");
}

function sanitize(value) {
  return String(value || "unset")
    .toLowerCase()
    .replace(/[^a-z0-9._-]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "") || "unset";
}

function formalJobId(batch) {
  return [
    `r${batch.repeatId}`,
    batch.family,
    batch.mode,
    batch.configurationId || batch.modelId,
  ].map(sanitize).join("__");
}

function expectedBatches(matrix) {
  const batches = [];
  for (const repeatId of matrix.repeats || []) {
    for (const modelId of matrix.textModels || []) {
      for (const mode of matrix.families?.standard?.modes || []) {
        batches.push({
          family: "standard",
          taskFamily: TASK_FAMILY_BY_MATRIX_FAMILY.standard,
          modelId,
          visionModelId: null,
          mode,
          repeatId,
          scenarioCount: matrix.families.standard.scenarioCount,
        });
      }
      for (const mode of matrix.families?.interactive?.modes || []) {
        batches.push({
          family: "interactive",
          taskFamily: TASK_FAMILY_BY_MATRIX_FAMILY.interactive,
          modelId,
          visionModelId: null,
          mode,
          repeatId,
          scenarioCount: matrix.families.interactive.scenarioCount,
        });
      }
    }
    for (const configuration of matrix.multimodalConfigurations || []) {
      for (const mode of matrix.families?.multimodal?.modes || []) {
        batches.push({
          family: "multimodal",
          taskFamily: TASK_FAMILY_BY_MATRIX_FAMILY.multimodal,
          modelId: configuration.agentModel,
          visionModelId: configuration.visionModel,
          configurationId: configuration.id,
          mode,
          repeatId,
          scenarioCount: matrix.families.multimodal.scenarioCount,
        });
      }
    }
  }
  return batches;
}

function stableValue(value) {
  if (Array.isArray(value)) return value.map(stableValue);
  if (!value || typeof value !== "object") return value;
  return Object.fromEntries(
    Object.entries(value)
      .sort(([left], [right]) => left.localeCompare(right))
      .map(([key, item]) => [key, stableValue(item)]),
  );
}

function comparableRevision(revision) {
  return JSON.stringify(stableValue({
    revision: revision?.revision || null,
    dirty: revision?.dirty ?? null,
  }));
}

function validateRecords(records, matrix, options = {}) {
  const errors = [];
  const rows = [];
  const fingerprints = new Map();
  const uniqueKeys = new Set();
  const actualBatches = new Map();
  const expected = expectedBatches(matrix);
  const expectedByKey = new Map(expected.map((batch) => [batchKey(batch), batch]));
  const familyScenarioSets = new Map();
  const familyFingerprints = new Map();
  const revisions = new Map();
  for (const { file, record } of records) {
    if (record.run.validity?.paperEligible !== true) {
      errors.push(`${file}: output is not paper-eligible`);
      continue;
    }
    if (![1, 2, 3].includes(record.run.repeatId)) {
      errors.push(`${file}: missing valid repeatId`);
      continue;
    }
    if (!record.run.protocol?.formalJobId) {
      errors.push(`${file}: missing formalJobId`);
    }
    if (!record.run.protocol?.formalMatrixSha256) {
      errors.push(`${file}: missing formalMatrixSha256`);
    } else if (
      options.matrixSha256
      && record.run.protocol.formalMatrixSha256 !== options.matrixSha256
    ) {
      errors.push(`${file}: formalMatrixSha256 does not match the selected matrix`);
    }
    for (const key of [
      "scenarioHash",
      "attachmentHash",
      "promptAndToolHash",
      "evaluationHash",
      "runtimeConfigHash",
    ]) {
      if (!record.run.fingerprints?.[key]) errors.push(`${file}: missing ${key}`);
    }
    for (const key of ["promptAndToolHash", "evaluationHash"]) {
      const value = record.run.fingerprints?.[key];
      if (!value) continue;
      if (!fingerprints.has(key)) fingerprints.set(key, value);
      else if (fingerprints.get(key) !== value) errors.push(`${file}: inconsistent ${key}`);
    }
    const modelId = record.run.models?.primary?.configId;
    const visionModelId = record.run.models?.vision?.configId || null;
    const taskFamilies = [...new Set(record.scenarios.map((scenario) => scenario.taskFamily))];
    if (taskFamilies.length !== 1) {
      errors.push(`${file}: output must contain exactly one task family`);
      continue;
    }
    const taskFamily = taskFamilies[0];
    const family = Object.entries(TASK_FAMILY_BY_MATRIX_FAMILY)
      .find(([, value]) => value === taskFamily)?.[0];
    if (!family) {
      errors.push(`${file}: unexpected task family ${taskFamily}`);
      continue;
    }
    const mode = record.run.selection?.mode;
    const actualBatch = {
      family,
      taskFamily,
      modelId,
      visionModelId,
      mode,
      repeatId: record.run.repeatId,
    };
    const actualBatchKey = batchKey(actualBatch);
    const expectedBatch = expectedByKey.get(actualBatchKey);
    if (!expectedBatch) {
      errors.push(`${file}: unexpected formal batch ${actualBatchKey.replaceAll("\0", "/")}`);
    } else if (record.scenarios.length !== expectedBatch.scenarioCount) {
      errors.push(
        `${file}: expected ${expectedBatch.scenarioCount} scenarios, found ${record.scenarios.length}`,
      );
    } else if (record.run.protocol?.formalJobId !== formalJobId(expectedBatch)) {
      errors.push(`${file}: formalJobId does not match its declared batch`);
    }
    if (actualBatches.has(actualBatchKey)) {
      errors.push(`${file}: duplicate formal batch ${actualBatchKey.replaceAll("\0", "/")}`);
    } else {
      actualBatches.set(actualBatchKey, file);
    }
    if (record.run.models?.judge?.configId !== matrix.judgeModel) {
      errors.push(`${file}: judge must be ${matrix.judgeModel}`);
    }
    const scenarioIds = record.scenarios
      .map((scenario) => scenario.baseScenarioId || scenario.scenarioId)
      .sort();
    const scenarioSet = JSON.stringify(scenarioIds);
    if (!familyScenarioSets.has(family)) familyScenarioSets.set(family, scenarioSet);
    else if (familyScenarioSets.get(family) !== scenarioSet) {
      errors.push(`${file}: scenario set differs from other ${family} batches`);
    }
    for (const key of ["scenarioHash", "attachmentHash"]) {
      const mapKey = `${family}\0${key}`;
      const value = record.run.fingerprints?.[key];
      if (!value) continue;
      if (!familyFingerprints.has(mapKey)) familyFingerprints.set(mapKey, value);
      else if (familyFingerprints.get(mapKey) !== value) {
        errors.push(`${file}: inconsistent ${key} for ${family}`);
      }
    }
    for (const repository of ["structureclaw", "benchmark"]) {
      const value = comparableRevision(record.run.revisions?.[repository]);
      if (!revisions.has(repository)) revisions.set(repository, value);
      else if (revisions.get(repository) !== value) {
        errors.push(`${file}: inconsistent ${repository} revision`);
      }
      if (record.run.revisions?.[repository]?.dirty !== false) {
        errors.push(`${file}: ${repository} revision is dirty`);
      }
    }
    for (const scenario of record.scenarios) {
      const row = {
        ...scenario,
        repeatId: record.run.repeatId,
        modelId,
        visionModelId,
        mode: scenario.mode || mode,
      };
      const key = [
        row.taskFamily,
        row.modelId,
        row.visionModelId || "",
        row.mode,
        row.repeatId,
        row.baseScenarioId || row.scenarioId,
      ].join("\0");
      if (uniqueKeys.has(key)) errors.push(`${file}: duplicate atomic run ${key.replaceAll("\0", "/")}`);
      uniqueKeys.add(key);
      rows.push(row);
    }
  }
  for (const [key] of expectedByKey) {
    if (!actualBatches.has(key)) {
      errors.push(`missing formal batch ${key.replaceAll("\0", "/")}`);
    }
  }
  if (records.length !== expected.length) {
    errors.push(`expected ${expected.length} batch outputs, found ${records.length}`);
  }
  if (rows.length !== matrix.expectedAtomicRuns) {
    errors.push(`expected ${matrix.expectedAtomicRuns} atomic runs, found ${rows.length}`);
  }
  return { errors, rows };
}

function main(argv) {
  const options = parseArgs(argv);
  const matrixBuffer = fs.readFileSync(options.matrixPath);
  const matrix = JSON.parse(matrixBuffer.toString("utf8"));
  const records = loadFormalRecords(options.inputDir);
  const validation = validateRecords(records, matrix, {
    matrixSha256: createHash("sha256").update(matrixBuffer).digest("hex"),
  });
  if (validation.errors.length > 0 && !options.allowIncomplete) {
    throw new Error(`Formal result validation failed:\n${validation.errors.map((item) => `- ${item}`).join("\n")}`);
  }
  const output = {
    schemaVersion: "structureclaw-formal-summary/v1",
    generatedAt: new Date().toISOString(),
    inputDir: options.inputDir,
    matrixPath: options.matrixPath,
    complete: validation.errors.length === 0,
    validationErrors: validation.errors,
    ...aggregateFormalRows(validation.rows),
  };
  fs.mkdirSync(path.dirname(options.outputPath), { recursive: true });
  fs.writeFileSync(options.outputPath, `${JSON.stringify(output, null, 2)}\n`);
  process.stdout.write(
    `Formal summary written: ${options.outputPath} complete=${output.complete} atomicRuns=${output.atomicRuns}\n`,
  );
}

if (require.main === module) {
  try {
    main(process.argv.slice(2));
  } catch (error) {
    console.error(error instanceof Error ? error.message : error);
    process.exit(1);
  }
}

module.exports = {
  expectedBatches,
  loadFormalRecords,
  validateRecords,
};
