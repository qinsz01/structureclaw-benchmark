const fs = require("node:fs");
const path = require("node:path");
const { createHash } = require("node:crypto");
const { spawn, spawnSync } = require("node:child_process");

const BENCH_ROOT = path.resolve(__dirname, "..");
const SCLAW_ROOT = path.resolve(BENCH_ROOT, "../..");
const EXPERIMENT_SCRIPT = path.join(__dirname, "run-llm-experiment.cjs");
const DEFAULT_MATRIX_PATH = path.join(BENCH_ROOT, "experiments", "formal-matrix.json");
const DEFAULT_CONFIG_PATH = path.join(BENCH_ROOT, "experiments", "llm-experiments.local.json");

function usage() {
  return [
    "Usage:",
    "  node scripts/run-formal-matrix.cjs --run-id <freeze-id> --repeats 1,2,3",
    "",
    "Options:",
    "  --matrix <file>          Executable formal-matrix JSON.",
    "  --config <file>          Provider/model configuration JSON.",
    "  --run-id <id>            Stable freeze/run identifier. Required unless --dry-run.",
    "  --repeat <1|2|3>         Add one repeat. Can be repeated.",
    "  --repeats <1,2,3>        Select repeats. Defaults to the matrix.",
    "  --family <name>          standard, interactive, multimodal, or all.",
    "  --concurrency <n>        Concurrent model batches. Defaults to the matrix.",
    "  --output-dir <dir>       Defaults to results/formal/<run-id>.",
    "  --resume                 Skip already complete, eligible matching outputs.",
    "  --dry-run                Resolve every batch without calling a model.",
  ].join("\n");
}

function requireValue(argv, index, flag) {
  const value = argv[index];
  if (!value || value.startsWith("--")) throw new Error(`Missing value for ${flag}`);
  return value;
}

function splitList(value) {
  return String(value).split(",").map((item) => item.trim()).filter(Boolean);
}

function parseArgs(argv) {
  const options = {
    matrixPath: DEFAULT_MATRIX_PATH,
    configPath: DEFAULT_CONFIG_PATH,
    runId: null,
    repeats: [],
    family: "all",
    concurrency: null,
    outputDir: null,
    resume: false,
    dryRun: false,
  };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--help" || arg === "-h") {
      process.stdout.write(`${usage()}\n`);
      process.exit(0);
    } else if (arg === "--matrix") {
      options.matrixPath = path.resolve(requireValue(argv, ++index, arg));
    } else if (arg === "--config") {
      options.configPath = path.resolve(requireValue(argv, ++index, arg));
    } else if (arg === "--run-id") {
      options.runId = requireValue(argv, ++index, arg);
    } else if (arg === "--repeat") {
      options.repeats.push(Number(requireValue(argv, ++index, arg)));
    } else if (arg === "--repeats") {
      options.repeats.push(...splitList(requireValue(argv, ++index, arg)).map(Number));
    } else if (arg === "--family") {
      options.family = requireValue(argv, ++index, arg);
    } else if (arg === "--concurrency") {
      options.concurrency = Number(requireValue(argv, ++index, arg));
    } else if (arg === "--output-dir") {
      options.outputDir = path.resolve(requireValue(argv, ++index, arg));
    } else if (arg === "--resume") {
      options.resume = true;
    } else if (arg === "--dry-run") {
      options.dryRun = true;
    } else {
      throw new Error(`Unknown option: ${arg}\n\n${usage()}`);
    }
  }
  if (!options.runId && !options.dryRun) {
    throw new Error("--run-id is required for formal execution");
  }
  if (!["all", "standard", "interactive", "multimodal"].includes(options.family)) {
    throw new Error("--family must be standard, interactive, multimodal, or all");
  }
  return options;
}

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function fileSha256(filePath) {
  return createHash("sha256").update(fs.readFileSync(filePath)).digest("hex");
}

function gitRevision(root) {
  const result = spawnSync("git", ["rev-parse", "HEAD"], {
    cwd: root,
    encoding: "utf8",
    windowsHide: true,
  });
  if (result.status !== 0) {
    throw new Error(`Cannot resolve git revision for ${root}`);
  }
  return result.stdout.trim();
}

function prepareFormalBackend(dryRun) {
  if (dryRun) return { prepared: false, reason: "dry-run" };
  const npmCli = [
    process.env.npm_execpath,
    path.join(path.dirname(process.execPath), "node_modules", "npm", "bin", "npm-cli.js"),
  ].find((candidate) => candidate && fs.existsSync(candidate));
  const command = npmCli ? process.execPath : "npm";
  const args = [
    ...(npmCli ? [npmCli] : []),
    "run",
    "build",
    "--prefix",
    path.join(SCLAW_ROOT, "backend"),
  ];
  const startedAt = new Date().toISOString();
  const result = spawnSync(
    command,
    args,
    {
      cwd: SCLAW_ROOT,
      encoding: "utf8",
      shell: process.platform === "win32" && !npmCli,
      windowsHide: true,
      maxBuffer: 20 * 1024 * 1024,
    },
  );
  if (result.error || result.status !== 0) {
    const detail = [result.stderr, result.stdout, result.error?.message]
      .filter(Boolean)
      .join("\n")
      .trim();
    throw new Error(`Formal backend prebuild failed:\n${detail}`);
  }
  return {
    prepared: true,
    startedAt,
    finishedAt: new Date().toISOString(),
  };
}

function runtimePrerequisites(config) {
  const sourceValue = config.environment?.SCLAW_BENCHMARK_SOURCE_DATA_DIR
    || process.env.SCLAW_BENCHMARK_SOURCE_DATA_DIR
    || process.env.SCLAW_DATA_DIR;
  if (!sourceValue) {
    throw new Error(
      "Formal execution requires SCLAW_BENCHMARK_SOURCE_DATA_DIR in the local config or environment",
    );
  }
  const sourceDataDir = path.resolve(String(sourceValue));
  const settingsPath = path.join(sourceDataDir, "settings.json");
  if (!fs.existsSync(settingsPath)) {
    throw new Error(`Formal source settings are missing: ${settingsPath}`);
  }
  const settings = readJson(settingsPath);
  const pythonBin = settings.analysis?.pythonBin
    || path.join(
      sourceDataDir,
      ".venv",
      process.platform === "win32" ? "Scripts" : "bin",
      process.platform === "win32" ? "python.exe" : "python",
    );
  const pkpmCyclePath = settings.pkpm?.cyclePath;
  const yjkInstallRoot = settings.yjk?.installRoot;
  const yjkExePath = settings.yjk?.exePath
    || (yjkInstallRoot ? path.join(yjkInstallRoot, "yjks.exe") : null);
  const yjkPythonBin = settings.yjk?.pythonBin;
  const requiredPaths = [
    ["analysis Python", pythonBin],
    ["PKPM cycle executable", pkpmCyclePath],
    ["YJK install root", yjkInstallRoot],
    ["YJK executable", yjkExePath],
    ["YJK Python", yjkPythonBin],
  ];
  const missing = requiredPaths.filter(([, value]) => !value || !fs.existsSync(value));
  if (missing.length > 0) {
    throw new Error(
      `Formal runtime prerequisites are missing:\n`
      + missing.map(([label, value]) => `- ${label}: ${value || "(unset)"}`).join("\n"),
    );
  }
  return {
    sourceDataDir,
    settingsPath,
    pythonBin,
    pkpmCyclePath,
    yjkInstallRoot,
    yjkExePath,
    yjkPythonBin,
  };
}

function sanitize(value) {
  return String(value || "unset")
    .toLowerCase()
    .replace(/[^a-z0-9._-]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "") || "unset";
}

function rotate(values, offset) {
  if (values.length === 0) return [];
  const normalized = ((offset % values.length) + values.length) % values.length;
  return [...values.slice(normalized), ...values.slice(0, normalized)];
}

function assertMatrix(matrix, config) {
  if (matrix.schemaVersion !== "structureclaw-formal-matrix/v1") {
    throw new Error(`Unsupported formal matrix schema: ${matrix.schemaVersion}`);
  }
  const configuredModels = new Set(Object.keys(config.models || {}));
  const requiredModels = new Set([
    ...(matrix.textModels || []),
    matrix.judgeModel,
    ...(matrix.multimodalConfigurations || []).flatMap((item) => [
      item.agentModel,
      item.visionModel,
    ]),
  ]);
  const missing = [...requiredModels].filter((model) => !configuredModels.has(model));
  if (missing.length > 0) {
    throw new Error(`Formal matrix references unconfigured models: ${missing.join(", ")}`);
  }
  const repeats = matrix.repeats || [];
  if (repeats.length !== 3 || ![1, 2, 3].every((repeat) => repeats.includes(repeat))) {
    throw new Error("Formal matrix must declare repeats 1, 2, and 3");
  }
  const standard = matrix.families?.standard;
  const interactive = matrix.families?.interactive;
  const multimodal = matrix.families?.multimodal;
  const calculated =
    standard.scenarioCount * matrix.textModels.length * standard.modes.length * repeats.length
    + interactive.scenarioCount * matrix.textModels.length * interactive.modes.length * repeats.length
    + multimodal.scenarioCount
      * matrix.multimodalConfigurations.length
      * multimodal.modes.length
      * repeats.length;
  if (calculated !== matrix.expectedAtomicRuns || calculated !== 5400) {
    throw new Error(
      `Formal matrix must contain exactly 5400 atomic runs; calculated ${calculated}`,
    );
  }
  if (!Number.isSafeInteger(matrix.yjkCooldownMs) || matrix.yjkCooldownMs <= 0) {
    throw new Error("Formal matrix requires a positive yjkCooldownMs");
  }
  if (
    matrix.multimodalConfigurations.some(
      (configuration) => ![null, 0, 1].includes(configuration.visionTemperature),
    )
  ) {
    throw new Error("Every multimodal configuration requires visionTemperature null, 0, or 1");
  }
}

function selectedRepeats(options, matrix) {
  const repeats = options.repeats.length > 0 ? [...new Set(options.repeats)] : matrix.repeats;
  if (repeats.some((repeat) => ![1, 2, 3].includes(repeat))) {
    throw new Error("Repeats must be selected from 1, 2, and 3");
  }
  return repeats.sort();
}

function buildJobs(options, matrix) {
  const jobs = [];
  const repeats = selectedRepeats(options, matrix);
  const families = options.family === "all"
    ? ["standard", "interactive", "multimodal"]
    : [options.family];
  for (const repeat of repeats) {
    const textModels = rotate(matrix.textModels, (repeat - 1) * 3);
    if (families.includes("standard")) {
      const modes = repeat % 2 === 0
        ? [...matrix.families.standard.modes].reverse()
        : matrix.families.standard.modes;
      for (const model of textModels) {
        for (const mode of modes) {
          jobs.push({ family: "standard", suite: "standard", model, visionModel: null, mode, repeat });
        }
      }
    }
    if (families.includes("interactive")) {
      for (const model of rotate(textModels, repeat)) {
        jobs.push({
          family: "interactive",
          suite: "interactive",
          model,
          visionModel: null,
          mode: "auto",
          repeat,
        });
      }
    }
    if (families.includes("multimodal")) {
      const configurations = rotate(matrix.multimodalConfigurations, repeat - 1);
      for (const configuration of configurations) {
        jobs.push({
          family: "multimodal",
          suite: "multimodal",
          model: configuration.agentModel,
          visionModel: configuration.visionModel,
          visionTemperature: configuration.visionTemperature,
          configurationId: configuration.id,
          mode: "auto",
          repeat,
        });
      }
    }
  }
  return jobs.map((job) => ({
    ...job,
    id: [
      `r${job.repeat}`,
      job.family,
      job.mode,
      job.configurationId || job.model,
    ].map(sanitize).join("__"),
  }));
}

function outputPathForJob(outputDir, job) {
  return path.join(
    outputDir,
    `r${job.repeat}`,
    job.family,
    `${job.id}.json`,
  );
}

function jobArgs(options, matrix, job, outputPath) {
  const args = [
    EXPERIMENT_SCRIPT,
    "--config", options.configPath,
    "--suite", job.suite,
    "--model", job.model,
    "--judge-model", matrix.judgeModel,
    "--mode", job.mode,
    "--repeat-id", String(job.repeat),
    "--scenario-order-seed", job.id,
    "--case-timeout-ms", String(matrix.caseTimeoutMs),
    "--output", outputPath,
    "--supervise",
    "--formal",
  ];
  if (job.visionModel) args.push("--multimodal-model", job.visionModel);
  if (options.dryRun) args.push("--dry-run");
  return args;
}

function matchingCompleteOutput(outputPath, job, expected = {}) {
  if (!fs.existsSync(outputPath)) return false;
  try {
    const record = readJson(outputPath);
    return record.run?.validity?.paperEligible === true
      && record.run?.repeatId === job.repeat
      && record.run?.selection?.mode === job.mode
      && record.run?.models?.primary?.configId === job.model
      && (job.visionModel
        ? record.run?.models?.vision?.configId === job.visionModel
        : record.run?.models?.vision == null)
      && (!expected.runId || record.run?.runId === expected.runId)
      && (!expected.formalJobId
        || record.run?.protocol?.formalJobId === expected.formalJobId)
      && (!expected.matrixSha256
        || record.run?.protocol?.formalMatrixSha256 === expected.matrixSha256)
      && (!expected.structureclawRevision
        || record.run?.revisions?.structureclaw?.revision === expected.structureclawRevision)
      && (!expected.benchmarkRevision
        || record.run?.revisions?.benchmark?.revision === expected.benchmarkRevision)
      && (!expected.scenarioCount
        || (
          record.run?.plannedScenarioCount === expected.scenarioCount
          && record.run?.completedScenarioCount === expected.scenarioCount
          && record.scenarios?.length === expected.scenarioCount
        ));
  } catch {
    return false;
  }
}

function archiveExistingOutput(outputPath) {
  if (!fs.existsSync(outputPath)) return null;
  const archived = `${outputPath}.incomplete-${new Date().toISOString().replace(/[:.]/g, "-")}`;
  fs.renameSync(outputPath, archived);
  return archived;
}

function expectedOutputMetadata(options, matrix, job, freeze) {
  return {
    runId: `${sanitize(options.runId || "dry-run")}__${job.id}`,
    formalJobId: job.id,
    matrixSha256: freeze.matrixSha256,
    structureclawRevision: freeze.structureclawRevision,
    benchmarkRevision: freeze.benchmarkRevision,
    scenarioCount: matrix.families[job.family].scenarioCount,
  };
}

function terminateChild(child) {
  if (!child?.pid || child.exitCode !== null) return;
  if (process.platform === "win32") {
    spawnSync("taskkill", ["/PID", String(child.pid), "/T"], {
      stdio: "ignore",
      windowsHide: true,
    });
  }
  try {
    child.kill("SIGTERM");
  } catch {
    // The process may have exited between the status check and termination.
  }
}

function runJob(options, matrix, outputDir, job, logDir, freeze, signal) {
  if (signal?.aborted) {
    return Promise.resolve({ ...job, status: "cancelled", error: "formal run interrupted" });
  }
  const outputPath = outputPathForJob(outputDir, job);
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  const expected = expectedOutputMetadata(options, matrix, job, freeze);
  if (options.resume && matchingCompleteOutput(outputPath, job, expected)) {
    return Promise.resolve({ ...job, outputPath, status: "skipped-complete" });
  }
  const archivedOutput = archiveExistingOutput(outputPath);
  const logPath = path.join(logDir, `${job.id}.log`);
  const log = fs.createWriteStream(logPath, { flags: "a" });
  const args = jobArgs(options, matrix, job, outputPath);
  const runtimeId = `${sanitize(options.runId || "dry-run")}__${job.id}`;
  const startedAt = new Date().toISOString();
  process.stdout.write(`[${startedAt}] BEGIN ${job.id}\n`);
  return new Promise((resolve) => {
    const child = spawn(process.execPath, args, {
      cwd: BENCH_ROOT,
      env: {
        ...process.env,
        SCLAW_BENCHMARK_RUNTIME_ID: runtimeId,
        SCLAW_BENCHMARK_SOLVER_GATE: matrix.solverGate,
        SCLAW_BENCHMARK_YJK_COOLDOWN_MS: String(matrix.yjkCooldownMs),
        ...(job.visionModel
          ? {
              LLM_VISION_OMIT_TEMPERATURE: job.visionTemperature === null ? "1" : "0",
              LLM_VISION_TEMPERATURE:
                job.visionTemperature === null ? "" : String(job.visionTemperature),
            }
          : {}),
        SCLAW_BENCHMARK_FORMAL_JOB_ID: job.id,
        SCLAW_BENCHMARK_FORMAL_MATRIX_SHA256: freeze.matrixSha256,
        SCLAW_BENCHMARK_BACKEND_PREBUILT: options.dryRun ? "0" : "1",
        LLM_BENCHMARK_RUN_ID: expected.runId,
      },
      stdio: ["ignore", "pipe", "pipe"],
      windowsHide: true,
    });
    const onAbort = () => terminateChild(child);
    signal?.addEventListener("abort", onAbort, { once: true });
    child.stdout.pipe(log);
    child.stderr.pipe(log);
    child.on("error", (error) => {
      signal?.removeEventListener("abort", onAbort);
      log.end();
      resolve({
        ...job,
        outputPath,
        logPath,
        archivedOutput,
        status: "failed",
        error: error.message,
        startedAt,
        finishedAt: new Date().toISOString(),
      });
    });
    child.on("exit", (code, exitSignal) => {
      signal?.removeEventListener?.("abort", onAbort);
      log.end();
      const completed = !options.dryRun && matchingCompleteOutput(outputPath, job, expected);
      const status = options.dryRun
        ? (code === 0 ? "dry-run" : "failed")
        : completed
          ? "completed"
          : exitSignal
            ? "cancelled"
            : "failed";
      const finishedAt = new Date().toISOString();
      process.stdout.write(
        `[${finishedAt}] END ${job.id} status=${status} exit=${code ?? "none"} signal=${exitSignal || "none"}\n`,
      );
      resolve({
        ...job,
        outputPath,
        logPath,
        archivedOutput,
        status,
        exitCode: code,
        signal: exitSignal || null,
        startedAt,
        finishedAt,
      });
    });
  });
}

async function runPool(items, concurrency, worker, onUpdate, signal) {
  let nextIndex = 0;
  const results = new Array(items.length);
  const take = async () => {
    while (true) {
      if (signal?.aborted) return;
      const index = nextIndex;
      nextIndex += 1;
      if (index >= items.length) return;
      results[index] = await worker(items[index]);
      onUpdate?.(results);
    }
  };
  await Promise.all(Array.from({ length: Math.min(concurrency, items.length) }, take));
  return results;
}

async function main(argv) {
  const options = parseArgs(argv);
  const matrix = readJson(options.matrixPath);
  const config = readJson(options.configPath);
  assertMatrix(matrix, config);
  const prerequisites = runtimePrerequisites(config);
  const freeze = {
    matrixSha256: fileSha256(options.matrixPath),
    structureclawRevision: gitRevision(SCLAW_ROOT),
    benchmarkRevision: gitRevision(BENCH_ROOT),
  };
  const jobs = buildJobs(options, matrix);
  const backendPreparation = prepareFormalBackend(options.dryRun);
  const abortController = new AbortController();
  const interrupt = () => {
    if (!abortController.signal.aborted) {
      process.stderr.write("Formal matrix interruption requested; stopping active batches...\n");
      abortController.abort(new Error("formal matrix interrupted"));
    }
  };
  process.once("SIGINT", interrupt);
  process.once("SIGTERM", interrupt);
  const concurrency = options.concurrency || matrix.maxConcurrency;
  if (!Number.isSafeInteger(concurrency) || concurrency <= 0) {
    throw new Error("--concurrency must be a positive integer");
  }
  const outputDir = options.outputDir
    || path.join(BENCH_ROOT, "results", "formal", sanitize(options.runId || "dry-run"));
  const logDir = path.join(outputDir, "logs");
  fs.mkdirSync(logDir, { recursive: true });
  const summaryPath = path.join(outputDir, "matrix-summary.json");
  const summary = {
    schemaVersion: matrix.schemaVersion,
    runId: options.runId || "dry-run",
    matrixPath: options.matrixPath,
    configPath: options.configPath,
    family: options.family,
    repeats: selectedRepeats(options, matrix),
    concurrency,
    plannedBatchJobs: jobs.length,
    plannedAtomicRuns: jobs.reduce(
      (total, job) => total + matrix.families[job.family].scenarioCount,
      0,
    ),
    expectedFullMatrixAtomicRuns: matrix.expectedAtomicRuns,
    matrixSha256: freeze.matrixSha256,
    structureclawRevision: freeze.structureclawRevision,
    benchmarkRevision: freeze.benchmarkRevision,
    sourceDataDir: prerequisites.sourceDataDir,
    backendPreparation,
    startedAt: new Date().toISOString(),
    finishedAt: null,
    jobs: jobs.map((job) => ({ ...job, status: "pending" })),
  };
  const writeSummary = (results = []) => {
    for (let index = 0; index < results.length; index += 1) {
      if (results[index]) summary.jobs[index] = results[index];
    }
    fs.writeFileSync(summaryPath, `${JSON.stringify(summary, null, 2)}\n`);
  };
  writeSummary();
  try {
    const results = await runPool(
      jobs,
      concurrency,
      (job) => runJob(
        options,
        matrix,
        outputDir,
        job,
        logDir,
        freeze,
        abortController.signal,
      ),
      writeSummary,
      abortController.signal,
    );
    for (let index = 0; index < jobs.length; index += 1) {
      if (!results[index]) {
        results[index] = {
          ...jobs[index],
          status: "cancelled",
          error: "formal run interrupted before launch",
        };
      }
    }
    summary.finishedAt = new Date().toISOString();
    writeSummary(results);
    const failures = results.filter((job) => job.status === "failed");
    const cancelled = results.filter((job) => job.status === "cancelled");
    process.stdout.write(
      `Formal matrix finished: jobs=${results.length} failures=${failures.length}`
      + ` cancelled=${cancelled.length} summary=${summaryPath}\n`,
    );
    if (abortController.signal.aborted) return 130;
    return failures.length === 0 ? 0 : 1;
  } finally {
    process.removeListener("SIGINT", interrupt);
    process.removeListener("SIGTERM", interrupt);
  }
}

if (require.main === module) {
  main(process.argv.slice(2))
    .then((code) => {
      process.exitCode = code;
    })
    .catch((error) => {
      console.error(error instanceof Error ? error.message : error);
      process.exit(1);
    });
}

module.exports = {
  assertMatrix,
  buildJobs,
  matchingCompleteOutput,
  parseArgs,
  runtimePrerequisites,
  prepareFormalBackend,
};
