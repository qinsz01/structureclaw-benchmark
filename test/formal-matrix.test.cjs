const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

const {
  assertMatrix,
  buildJobs,
  matchingCompleteOutput,
  prepareFormalBackend,
  runtimePrerequisites,
} = require("../scripts/run-formal-matrix.cjs");

const matrix = require("../experiments/formal-matrix.json");

function configuredModels() {
  const keys = new Set([
    ...matrix.textModels,
    matrix.judgeModel,
    ...matrix.multimodalConfigurations.flatMap((item) => [
      item.agentModel,
      item.visionModel,
    ]),
  ]);
  return { models: Object.fromEntries([...keys].map((key) => [key, { model: key }])) };
}

test("formal matrix contains exactly 5,400 runs without oracle mode", () => {
  assert.doesNotThrow(() => assertMatrix(matrix, configuredModels()));
  const jobs = buildJobs(
    { repeats: [], family: "all" },
    matrix,
  );
  assert.equal(jobs.length, 108);
  assert.equal(
    jobs.reduce((total, job) => total + matrix.families[job.family].scenarioCount, 0),
    5400,
  );
  assert.ok(jobs.every((job) => job.mode !== "oracle-specialist"));
  assert.ok(matrix.textModels.includes("glm-5.2-paratera"));
  assert.ok(!matrix.textModels.includes("glm-5.2-mine"));
});

test("formal jobs use 60 standard, 30 interactive, and 18 multimodal batches", () => {
  const jobs = buildJobs({ repeats: [], family: "all" }, matrix);
  assert.equal(jobs.filter((job) => job.family === "standard").length, 60);
  assert.equal(jobs.filter((job) => job.family === "interactive").length, 30);
  assert.equal(jobs.filter((job) => job.family === "multimodal").length, 18);
  assert.equal(new Set(jobs.map((job) => job.id)).size, jobs.length);
});

test("resume accepts only matching complete formal outputs", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "structureclaw-formal-resume-"));
  const output = path.join(dir, "result.json");
  const job = {
    repeat: 2,
    mode: "auto",
    model: "glm-5.2-paratera",
    visionModel: null,
  };
  try {
    fs.writeFileSync(output, JSON.stringify({
      run: {
        runId: "freeze__job",
        repeatId: 2,
        plannedScenarioCount: 50,
        completedScenarioCount: 50,
        selection: { mode: "auto" },
        models: {
          primary: { configId: "glm-5.2-paratera" },
          vision: null,
        },
        revisions: {
          structureclaw: { revision: "sut" },
          benchmark: { revision: "bench" },
        },
        protocol: {
          formalJobId: "job",
          formalMatrixSha256: "a".repeat(64),
        },
        validity: { paperEligible: true },
      },
      scenarios: Array.from({ length: 50 }, (_, index) => ({ scenarioId: `s${index}` })),
    }));
    const expected = {
      runId: "freeze__job",
      formalJobId: "job",
      matrixSha256: "a".repeat(64),
      structureclawRevision: "sut",
      benchmarkRevision: "bench",
      scenarioCount: 50,
    };
    assert.equal(matchingCompleteOutput(output, job, expected), true);
    assert.equal(
      matchingCompleteOutput(output, job, { ...expected, benchmarkRevision: "changed" }),
      false,
    );
    job.repeat = 3;
    assert.equal(matchingCompleteOutput(output, job, expected), false);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test("formal runtime preflight requires all three solver installations", () => {
  const sourceDataDir = fs.mkdtempSync(path.join(os.tmpdir(), "structureclaw-formal-runtime-"));
  const pythonBin = path.join(
    sourceDataDir,
    ".venv",
    process.platform === "win32" ? "Scripts" : "bin",
    process.platform === "win32" ? "python.exe" : "python",
  );
  const pkpmCyclePath = path.join(sourceDataDir, "pkpm", "JWSCYCLE.exe");
  const yjkInstallRoot = path.join(sourceDataDir, "yjk");
  const yjkExePath = path.join(yjkInstallRoot, "yjks.exe");
  const yjkPythonBin = path.join(yjkInstallRoot, "python.exe");
  for (const file of [pythonBin, pkpmCyclePath, yjkExePath, yjkPythonBin]) {
    fs.mkdirSync(path.dirname(file), { recursive: true });
    fs.writeFileSync(file, "");
  }
  fs.writeFileSync(path.join(sourceDataDir, "settings.json"), JSON.stringify({
    pkpm: { cyclePath: pkpmCyclePath },
    yjk: {
      installRoot: yjkInstallRoot,
      exePath: yjkExePath,
      pythonBin: yjkPythonBin,
    },
  }));
  try {
    const result = runtimePrerequisites({
      environment: { SCLAW_BENCHMARK_SOURCE_DATA_DIR: sourceDataDir },
    });
    assert.equal(result.sourceDataDir, sourceDataDir);
    fs.rmSync(pkpmCyclePath);
    assert.throws(
      () => runtimePrerequisites({
        environment: { SCLAW_BENCHMARK_SOURCE_DATA_DIR: sourceDataDir },
      }),
      /PKPM cycle executable/,
    );
  } finally {
    fs.rmSync(sourceDataDir, { recursive: true, force: true });
  }
});

test("formal backend preparation is side-effect free during matrix dry-runs", () => {
  assert.deepEqual(prepareFormalBackend(true), {
    prepared: false,
    reason: "dry-run",
  });
});
