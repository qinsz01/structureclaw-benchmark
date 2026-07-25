const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

const { buildSummary, writeJsonOutput } = require("../lib/report.cjs");
const {
  buildRunMetadata,
  detectOpenSeesRuntime,
  formalRunViolations,
} = require("../runner.cjs");
const { syncRuntimeSettings } = require("../scripts/run-llm-experiment.cjs");

function result(id) {
  return {
    scenarioId: id,
    allPassed: true,
    metrics: [],
    durationMs: 1,
    retries: { attempts: 1, passAt1: true },
  };
}

test("marks incremental output incomplete and final output complete only at planned count", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "structureclaw-report-"));
  const output = path.join(dir, "result.json");
  const runMetadata = {
    schemaVersion: "structureclaw-benchmark-run/v2",
    runId: "test-run",
    plannedScenarioCount: 2,
  };
  try {
    writeJsonOutput(output, [result("one")], {
      quiet: true,
      runMetadata,
      completed: false,
    });
    let record = JSON.parse(fs.readFileSync(output, "utf8"));
    assert.equal(record.run.completedScenarioCount, 1);
    assert.equal(record.run.completed, false);
    assert.equal(record.run.finishedAt, null);

    writeJsonOutput(output, [result("one"), result("two")], {
      quiet: true,
      runMetadata,
      completed: true,
    });
    record = JSON.parse(fs.readFileSync(output, "utf8"));
    assert.equal(record.run.completedScenarioCount, 2);
    assert.equal(record.run.completed, true);
    assert.match(record.run.finishedAt, /^\d{4}-\d{2}-\d{2}T/);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test("multimodal summaries separate complete reconstruction from safe clarification", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "structureclaw-report-input-"));
  const output = path.join(dir, "result.json");
  try {
    writeJsonOutput(output, [
      { ...result("complete"), inputCompleteness: "complete" },
      { ...result("incomplete"), inputCompleteness: "intentionally-incomplete" },
    ], { quiet: true });
    const record = JSON.parse(fs.readFileSync(output, "utf8"));
    assert.equal(record.by.inputCompleteness.complete.total, 1);
    assert.equal(record.by.inputCompleteness["intentionally-incomplete"].total, 1);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test("mode comparison reports a shared common core independently of routing assertions", () => {
  const summary = buildSummary([
    {
      ...result("auto"),
      mode: "auto",
      allPassed: false,
      metrics: [
        { metric: "structural_type", pass: false },
        { metric: "skill_match", pass: false },
        { metric: "model_matches", pass: true },
        { metric: "numerical_matches", pass: true },
      ],
      retries: {
        attempts: 1,
        passAt1: false,
        rounds: [{
          metrics: [
            { metric: "structural_type", pass: false },
            { metric: "skill_match", pass: false },
            { metric: "model_matches", pass: true },
            { metric: "numerical_matches", pass: true },
          ],
        }],
      },
    },
    {
      ...result("oracle"),
      mode: "oracle-specialist",
      metrics: [
        { metric: "model_matches", pass: true },
        { metric: "numerical_matches", pass: true },
      ],
    },
  ]);

  assert.equal(summary.passed, 1);
  assert.equal(summary.commonCorePassed, 2);
  assert.equal(summary.commonCorePassAt1, 2);
  assert.equal(summary.by.mode.auto.commonCorePassed, 1);
  assert.equal(summary.by.mode["oracle-specialist"].commonCorePassed, 1);
});

test("formal protocol rejects targeted, retried, unsupervised, dirty, or unrecorded runs", () => {
  const baseOptions = {
    formal: true,
    scenarioId: null,
    outputPath: "result.json",
    supervise: true,
    repeatId: 1,
  };
  const cleanRevisions = {
    structureclaw: { revision: "sut-revision", dirty: false },
    benchmark: { revision: "benchmark-revision", dirty: false },
  };
  const previousRuntimeId = process.env.SCLAW_BENCHMARK_RUNTIME_ID;
  const previousSolverGate = process.env.SCLAW_BENCHMARK_SOLVER_GATE;
  const previousFormalJobId = process.env.SCLAW_BENCHMARK_FORMAL_JOB_ID;
  const previousMatrixHash = process.env.SCLAW_BENCHMARK_FORMAL_MATRIX_SHA256;
  const previousYjkCooldown = process.env.SCLAW_BENCHMARK_YJK_COOLDOWN_MS;
  process.env.SCLAW_BENCHMARK_RUNTIME_ID = "formal-test";
  process.env.SCLAW_BENCHMARK_SOLVER_GATE = "per-engine";
  process.env.SCLAW_BENCHMARK_FORMAL_JOB_ID = "r1__standard__auto__test";
  process.env.SCLAW_BENCHMARK_FORMAL_MATRIX_SHA256 = "a".repeat(64);
  process.env.SCLAW_BENCHMARK_YJK_COOLDOWN_MS = "5000";
  try {
    assert.deepEqual(
      formalRunViolations(baseOptions, [{ id: "one", maxRetries: 0 }], cleanRevisions),
      [],
    );
  } finally {
    if (previousRuntimeId === undefined) delete process.env.SCLAW_BENCHMARK_RUNTIME_ID;
    else process.env.SCLAW_BENCHMARK_RUNTIME_ID = previousRuntimeId;
    if (previousSolverGate === undefined) delete process.env.SCLAW_BENCHMARK_SOLVER_GATE;
    else process.env.SCLAW_BENCHMARK_SOLVER_GATE = previousSolverGate;
    if (previousFormalJobId === undefined) delete process.env.SCLAW_BENCHMARK_FORMAL_JOB_ID;
    else process.env.SCLAW_BENCHMARK_FORMAL_JOB_ID = previousFormalJobId;
    if (previousMatrixHash === undefined) delete process.env.SCLAW_BENCHMARK_FORMAL_MATRIX_SHA256;
    else process.env.SCLAW_BENCHMARK_FORMAL_MATRIX_SHA256 = previousMatrixHash;
    if (previousYjkCooldown === undefined) delete process.env.SCLAW_BENCHMARK_YJK_COOLDOWN_MS;
    else process.env.SCLAW_BENCHMARK_YJK_COOLDOWN_MS = previousYjkCooldown;
  }

  const violations = formalRunViolations(
    {
      ...baseOptions,
      scenarioId: "one",
      outputPath: null,
      supervise: false,
      repeatId: null,
    },
    [{ id: "one", maxRetries: 1 }],
    {
      structureclaw: { revision: "sut-revision", dirty: true },
      benchmark: { revision: null, dirty: null },
    },
  );
  assert.ok(violations.some((item) => item.includes("single scenario")));
  assert.ok(violations.some((item) => item.includes("--output")));
  assert.ok(violations.some((item) => item.includes("--supervise")));
  assert.ok(violations.some((item) => item.includes("--repeat-id")));
  assert.ok(violations.some((item) => item.includes("SCLAW_BENCHMARK_RUNTIME_ID")));
  assert.ok(violations.some((item) => item.includes("solver gate")));
  assert.ok(violations.some((item) => item.includes("FORMAL_JOB_ID")));
  assert.ok(violations.some((item) => item.includes("FORMAL_MATRIX_SHA256")));
  assert.ok(violations.some((item) => item.includes("YJK solver cooldown")));
  assert.ok(violations.some((item) => item.includes("maxRetries=0")));
  assert.ok(violations.some((item) => item.includes("structureclaw worktree must be clean")));
  assert.ok(violations.some((item) => item.includes("benchmark revision is unavailable")));
});

test("only completed formal outputs are marked paper-eligible", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "structureclaw-formal-report-"));
  const output = path.join(dir, "result.json");
  try {
    const formalMetadata = {
      schemaVersion: "structureclaw-benchmark-run/v3",
      runId: "formal-run",
      repeatId: 1,
      plannedScenarioCount: 1,
      protocol: {
        phase: "formal",
        targeted: false,
        formalJobId: "r1__standard__auto__test",
        formalMatrixSha256: "a".repeat(64),
      },
      fingerprints: {
        scenarioHash: "scenario",
        attachmentHash: "attachment",
        promptAndToolHash: "prompt",
        evaluationHash: "evaluation",
        runtimeConfigHash: "runtime",
      },
    };
    writeJsonOutput(output, [result("one")], {
      quiet: true,
      runMetadata: formalMetadata,
      completed: true,
    });
    let record = JSON.parse(fs.readFileSync(output, "utf8"));
    assert.equal(record.run.validity.paperEligible, true);

    writeJsonOutput(output, [result("one")], {
      quiet: true,
      runMetadata: {
        ...formalMetadata,
        protocol: { phase: "development", targeted: false },
      },
      completed: true,
    });
    record = JSON.parse(fs.readFileSync(output, "utf8"));
    assert.equal(record.run.validity.paperEligible, false);
    assert.match(record.run.validity.reason, /development run/);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test("run metadata records the fixed sampling and retry protocol", () => {
  const previous = {
    model: process.env.LLM_MODEL,
    visionModel: process.env.LLM_VISION_MODEL,
    visionTemperature: process.env.LLM_VISION_TEMPERATURE,
    providerRequestTimeout: process.env.LLM_BENCHMARK_PROVIDER_REQUEST_TIMEOUT_MS,
    benchmarkLlmOnly: process.env.SCLAW_BENCHMARK_LLM_ONLY,
    primaryConfigId: process.env.LLM_BENCHMARK_PRIMARY_CONFIG_ID,
    judgeConfigId: process.env.LLM_BENCHMARK_JUDGE_CONFIG_ID,
    visionConfigId: process.env.LLM_BENCHMARK_VISION_CONFIG_ID,
    benchmarkMaxTokens: process.env.SCLAW_BENCHMARK_MAX_TOKENS,
  };
  process.env.LLM_MODEL = "primary-test-model";
  process.env.LLM_VISION_MODEL = "vision-test-model";
  process.env.LLM_VISION_TEMPERATURE = "0.1";
  process.env.LLM_BENCHMARK_PROVIDER_REQUEST_TIMEOUT_MS = "5000";
  process.env.SCLAW_BENCHMARK_LLM_ONLY = "1";
  process.env.LLM_BENCHMARK_PRIMARY_CONFIG_ID = "primary-provider-a";
  process.env.LLM_BENCHMARK_JUDGE_CONFIG_ID = "judge-provider-b";
  process.env.LLM_BENCHMARK_VISION_CONFIG_ID = "vision-provider-c";
  process.env.SCLAW_BENCHMARK_MAX_TOKENS = "16384";
  try {
    const metadata = buildRunMetadata(
      {
        scenarioId: null,
        taskFamily: null,
        split: null,
        mode: "auto",
        execution: "web-stream",
        supervise: true,
        caseTimeoutMs: 12345,
        repeatId: 2,
        scenarioOrderSeed: "order-seed",
      },
      path.resolve(__dirname, "../../.."),
      [{ id: "one" }],
    );

    assert.equal(metadata.models.primary.temperature, 0);
    assert.equal(metadata.models.primary.configId, "primary-provider-a");
    assert.equal(metadata.models.primary.providerMaxRetries, 0);
    assert.equal(metadata.models.primary.maxTokens, 16384);
    assert.equal(metadata.models.primary.timeoutMs, 5000);
    assert.equal(metadata.models.judge.temperature, 0);
    assert.equal(metadata.models.judge.configId, "judge-provider-b");
    assert.equal(metadata.models.judge.maxTokens, 4096);
    assert.equal(metadata.models.judge.maxAttempts, 3);
    assert.equal(metadata.models.vision.temperature, 0.1);
    assert.equal(metadata.models.vision.configId, "vision-provider-c");
    assert.equal(metadata.models.vision.providerMaxRetries, 0);
    assert.equal(metadata.models.vision.maxTokens, 16384);
    assert.equal(metadata.models.vision.timeoutMs, 5000);
    assert.equal(metadata.runtime.llmRoutingAndExtractionOnly, true);
    assert.equal(metadata.protocol.phase, "development");
    assert.equal(metadata.protocol.targeted, false);
    assert.equal(metadata.repeatId, 2);
    assert.equal(metadata.selection.scenarioOrderSeed, "order-seed");
    assert.equal(metadata.protocol.commonCoreComparison, true);
    assert.match(metadata.fingerprints.scenarioHash, /^[a-f0-9]{64}$/);
    assert.match(metadata.fingerprints.attachmentHash, /^[a-f0-9]{64}$/);
    assert.match(metadata.fingerprints.promptAndToolHash, /^[a-f0-9]{64}$/);
    assert.match(metadata.fingerprints.evaluationHash, /^[a-f0-9]{64}$/);
    assert.match(metadata.fingerprints.runtimeConfigHash, /^[a-f0-9]{64}$/);
    assert.match(metadata.measurement.primaryTokens, /includes nested routing and parameter extraction/);
    assert.equal(metadata.measurement.judgeTokens, "excluded from agent-efficiency metrics");
    assert.equal(metadata.measurement.totalApiCostAvailable, false);
  } finally {
    for (const [key, value] of Object.entries({
      LLM_MODEL: previous.model,
      LLM_VISION_MODEL: previous.visionModel,
      LLM_VISION_TEMPERATURE: previous.visionTemperature,
      LLM_BENCHMARK_PROVIDER_REQUEST_TIMEOUT_MS: previous.providerRequestTimeout,
      SCLAW_BENCHMARK_LLM_ONLY: previous.benchmarkLlmOnly,
      LLM_BENCHMARK_PRIMARY_CONFIG_ID: previous.primaryConfigId,
      LLM_BENCHMARK_JUDGE_CONFIG_ID: previous.judgeConfigId,
      LLM_BENCHMARK_VISION_CONFIG_ID: previous.visionConfigId,
      SCLAW_BENCHMARK_MAX_TOKENS: previous.benchmarkMaxTokens,
    })) {
      if (value === undefined) delete process.env[key];
      else process.env[key] = value;
    }
  }
});

test("run metadata derives commercial solver versions from copied runtime settings", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "structureclaw-run-metadata-"));
  const previous = {
    dataDir: process.env.SCLAW_DATA_DIR,
    yjkVersion: process.env.YJK_VERSION,
    pkpmVersion: process.env.PKPM_VERSION,
  };
  fs.writeFileSync(
    path.join(dir, "settings.json"),
    JSON.stringify({
      yjk: { version: "8.0.0" },
      pkpm: { cyclePath: path.join(dir, "PKPM2025R2.5", "PkpmCycle", "JWSCYCLE.exe") },
    }),
  );
  process.env.SCLAW_DATA_DIR = dir;
  delete process.env.YJK_VERSION;
  delete process.env.PKPM_VERSION;
  try {
    const metadata = buildRunMetadata(
      {
        scenarioId: null,
        taskFamily: "standard_workflow",
        split: null,
        mode: "auto",
        execution: "web-stream",
        supervise: true,
        caseTimeoutMs: 12345,
      },
      path.resolve(__dirname, "../../.."),
      [{ id: "one" }],
    );
    assert.equal(metadata.runtime.yjkVersion, "8.0.0");
    assert.equal(metadata.runtime.pkpmVersion, "PKPM2025R2.5");
  } finally {
    if (previous.dataDir === undefined) delete process.env.SCLAW_DATA_DIR;
    else process.env.SCLAW_DATA_DIR = previous.dataDir;
    if (previous.yjkVersion === undefined) delete process.env.YJK_VERSION;
    else process.env.YJK_VERSION = previous.yjkVersion;
    if (previous.pkpmVersion === undefined) delete process.env.PKPM_VERSION;
    else process.env.PKPM_VERSION = previous.pkpmVersion;
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test("OpenSees metadata probes the configured analysis runtime", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "structureclaw-opensees-metadata-"));
  const previousDataDir = process.env.SCLAW_DATA_DIR;
  fs.writeFileSync(
    path.join(dir, "settings.json"),
    JSON.stringify({ analysis: { pythonBin: "configured-python" } }),
  );
  process.env.SCLAW_DATA_DIR = dir;
  try {
    const metadata = detectOpenSeesRuntime(
      path.resolve(__dirname, "../../.."),
      (command, args, options) => {
        assert.equal(command, "configured-python");
        assert.equal(args[0], "-c");
        assert.equal(options.timeout, 30_000);
        return {
          status: 0,
          stdout: `${JSON.stringify({
            packageVersion: "3.7.1.2",
            runtimePackage: "openseespywin",
            runtimePackageVersion: "3.8.0.0",
            engineVersion: "3.8.0",
          })}\n`,
        };
      },
    );
    assert.deepEqual(metadata, {
      packageVersion: "3.7.1.2",
      runtimePackage: "openseespywin",
      runtimePackageVersion: "3.8.0.0",
      engineVersion: "3.8.0",
    });
  } finally {
    if (previousDataDir === undefined) delete process.env.SCLAW_DATA_DIR;
    else process.env.SCLAW_DATA_DIR = previousDataDir;
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test("experiment runtime disables inherited provider retries", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "structureclaw-experiment-"));
  const sourceDir = path.join(dir, "source");
  const runtimeDir = path.join(dir, "runtime");
  fs.mkdirSync(sourceDir);
  fs.writeFileSync(
    path.join(sourceDir, "settings.json"),
    JSON.stringify({ llm: { maxRetries: 7 } }),
  );
  try {
    syncRuntimeSettings(
      runtimeDir,
      sourceDir,
      { model: "test-model", baseUrl: "https://provider.example/v1" },
      900000,
    );
    const settings = JSON.parse(fs.readFileSync(path.join(runtimeDir, "settings.json"), "utf8"));
    assert.equal(settings.llm.maxRetries, 0);
    assert.equal(settings.llm.timeoutMs, 300000);
    assert.equal(
      settings.database.url,
      `file:${path.join(runtimeDir, "data", "structureclaw.db")}`,
    );
    assert.equal(settings.pkpm.workDir, path.join(runtimeDir, "analysis", "pkpm"));
    assert.equal(settings.yjk.workDir, path.join(runtimeDir, "analysis", "yjk"));
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});
