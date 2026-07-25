const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

const {
  benchmarkConversationId,
  chatCompletionsUrl,
  classifyInfrastructureEvaluation,
  contentTextFromOpenAiMessage,
  copyAttachmentsToRuntimeUploads,
  fetchWithAbortSignal,
  findBenchmarkInfrastructureError,
  findBenchmarkPolicyViolation,
  normalizeScenarioMetadata,
  parseVisionSummary,
  selectBenchmarkToolIds,
} = require("../runner.cjs");
const {
  benchmarkControlEnv,
  mergeRunnerArgs,
  syncRuntimeSettings,
} = require("../scripts/run-llm-experiment.cjs");

function evaluation(metric, actual, expected = "no error") {
  return {
    metrics: [{ metric, pass: false, expected, actual }],
  };
}

test("scenario metadata records the default and explicit analysis engines", () => {
  const defaultTarget = normalizeScenarioMetadata({
    id: "default-engine",
    taskFamily: "standard_workflow",
  });
  const explicitTarget = normalizeScenarioMetadata({
    id: "commercial-engine",
    taskFamily: "standard_workflow",
    analysisSkillTarget: "yjk-static",
    analysisEngineTarget: "builtin-yjk",
  });

  assert.equal(defaultTarget.analysisSkillTarget, "opensees-static");
  assert.equal(defaultTarget.analysisEngineTarget, "builtin-opensees");
  assert.equal(explicitTarget.analysisSkillTarget, "yjk-static");
  assert.equal(explicitTarget.analysisEngineTarget, "builtin-yjk");
});

test("classifies retryable provider and judge infrastructure failures", () => {
  assert.deepEqual(
    classifyInfrastructureEvaluation(evaluation("execution", "Vision API returned HTTP 524")),
    { kind: "provider-transient", retryable: true },
  );
  assert.deepEqual(
    classifyInfrastructureEvaluation(evaluation("execution", "TimeoutError: request exceeded provider deadline")),
    { kind: "provider-transient", retryable: true },
  );
  assert.deepEqual(
    classifyInfrastructureEvaluation(evaluation("execution", "524 status code (no body)")),
    { kind: "provider-transient", retryable: true },
  );
  assert.deepEqual(
    classifyInfrastructureEvaluation(evaluation("execution", "error: LLM_JUDGE_INFRASTRUCTURE_ERROR")),
    { kind: "judge-infrastructure", retryable: true },
  );
  assert.deepEqual(
    classifyInfrastructureEvaluation(evaluation("execution", "MODEL_RATE_LIMIT: HTTP 429")),
    { kind: "provider-rate-limit", retryable: true },
  );
  assert.deepEqual(
    classifyInfrastructureEvaluation(evaluation(
      "execution",
      "LLM_PARAM_EXTRACTOR_INFRASTRUCTURE_ERROR: terminated",
    )),
    { kind: "provider-transient", retryable: true },
  );
  assert.deepEqual(
    classifyInfrastructureEvaluation(evaluation(
      "execution",
      "LLM_STRUCTURAL_ROUTER_INFRASTRUCTURE_ERROR: socket hang up",
    )),
    { kind: "provider-transient", retryable: true },
  );
});

test("does not mistake engineering values in expected output for provider errors", () => {
  assert.equal(
    classifyInfrastructureEvaluation(evaluation("numerical_matches", "actual moment=10", "moment=500")),
    null,
  );
  assert.equal(
    classifyInfrastructureEvaluation(evaluation("numerical_matches", "actual reaction=429 kN")),
    null,
  );
  assert.equal(
    classifyInfrastructureEvaluation(evaluation("natural_language", "The agent incorrectly claimed a rate limit timeout")),
    null,
  );
});

test("keeps case timeouts as measured outcomes but aborts other execution failures", () => {
  assert.equal(
    classifyInfrastructureEvaluation(evaluation("execution", "case timed out after 900000ms")),
    null,
  );
  assert.deepEqual(
    classifyInfrastructureEvaluation(evaluation("execution", "TypeError: cannot read properties of undefined")),
    { kind: "benchmark-execution", retryable: false },
  );
  assert.equal(
    classifyInfrastructureEvaluation(evaluation(
      "execution",
      "LLM_PARAM_EXTRACTOR_INVALID_OUTPUT: response was not usable JSON",
    )),
    null,
  );
  assert.equal(
    classifyInfrastructureEvaluation(evaluation(
      "execution",
      "LLM_STRUCTURAL_ROUTER_INVALID_OUTPUT: response was not usable JSON",
    )),
    null,
  );
  assert.equal(
    classifyInfrastructureEvaluation(evaluation(
      "execution",
      "VISION_MODEL_INVALID_OUTPUT: response was not usable JSON",
    )),
    null,
  );
});

test("experiment processes require LLM routing and extraction without deterministic fallback", () => {
  assert.deepEqual(benchmarkControlEnv(), {
    SCLAW_BENCHMARK_LLM_ONLY: "1",
    SCLAW_BENCHMARK_MAX_TOKENS: "16384",
    SCLAW_BENCHMARK_SOLVER_GATE: "per-engine",
    SCLAW_BENCHMARK_YJK_COOLDOWN_MS: "5000",
  });
});

test("surfaces benchmark-only routing and extraction infrastructure errors wrapped by ToolNode", () => {
  assert.equal(
    findBenchmarkInfrastructureError({
      messages: [{
        lc: 1,
        id: ["langchain_core", "messages", "ToolMessage"],
        kwargs: {
          content: "Error: LLM_PARAM_EXTRACTOR_INFRASTRUCTURE_ERROR: network error: terminated",
        },
      }],
    }),
    "Error: LLM_PARAM_EXTRACTOR_INFRASTRUCTURE_ERROR: network error: terminated",
  );
  assert.equal(
    findBenchmarkInfrastructureError({
      messages: [{
        type: "tool",
        content: "Error: LLM_STRUCTURAL_ROUTER_INFRASTRUCTURE_ERROR: network error: HTTP 503",
      }],
    }),
    "Error: LLM_STRUCTURAL_ROUTER_INFRASTRUCTURE_ERROR: network error: HTTP 503",
  );
  assert.equal(
    findBenchmarkInfrastructureError({
      messages: [{
        type: "tool",
        content: "Error: LLM_PARAM_EXTRACTOR_INVALID_OUTPUT: unusable JSON",
      }],
    }),
    null,
  );
});

test("rejects deterministic routing and extraction payloads in LLM-only benchmark runs", () => {
  assert.equal(
    findBenchmarkPolicyViolation({
      messages: [{
        type: "tool",
        content: JSON.stringify({
          structuralTypeMatch: { routingSource: "explicit-keyword" },
          extractionMode: "llm",
        }),
      }],
    }),
    "routingSource=explicit-keyword",
  );
  assert.equal(
    findBenchmarkPolicyViolation({
      messages: [{
        type: "tool",
        content: JSON.stringify({
          routingSource: "llm-suggested",
          extractionMode: "deterministic",
        }),
      }],
    }),
    "extractionMode=deterministic",
  );
  assert.equal(
    findBenchmarkPolicyViolation({
      messages: [{
        type: "tool",
        content: JSON.stringify({
          routingSource: "llm-suggested",
          extractionMode: "not-applicable",
        }),
      }],
    }),
    null,
  );
  assert.equal(
    findBenchmarkPolicyViolation({
      messages: [{
        type: "tool",
        content: JSON.stringify({
          routingSource: "current-state",
          extractionMode: "preserved",
        }),
      }],
    }),
    null,
  );
});

test("classifies authentication failures as non-retryable configuration errors", () => {
  assert.deepEqual(
    classifyInfrastructureEvaluation(evaluation("execution", "Model API returned HTTP 401")),
    { kind: "provider-configuration", retryable: false },
  );
  assert.deepEqual(
    classifyInfrastructureEvaluation(evaluation("execution", "401 status code (no body)")),
    { kind: "provider-configuration", retryable: false },
  );
  assert.deepEqual(
    classifyInfrastructureEvaluation(evaluation(
      "execution",
      "error: LLM_JUDGE_INFRASTRUCTURE_ERROR: Judge API returned HTTP 401",
    )),
    { kind: "provider-configuration", retryable: false },
  );
  assert.equal(
    classifyInfrastructureEvaluation(evaluation(
      "natural_language",
      "The agent incorrectly claimed HTTP 401 authentication failure",
    )),
    null,
  );
});

test("normalizes versioned and unversioned vision API base URLs", () => {
  assert.equal(
    chatCompletionsUrl("https://provider.example/v1"),
    "https://provider.example/v1/chat/completions",
  );
  assert.equal(
    chatCompletionsUrl("https://provider.example/api/paas/v4/"),
    "https://provider.example/api/paas/v4/chat/completions",
  );
  assert.equal(
    chatCompletionsUrl("https://provider.example"),
    "https://provider.example/v1/chat/completions",
  );
  assert.equal(
    chatCompletionsUrl("https://provider.example/v1/chat/completions"),
    "https://provider.example/v1/chat/completions",
  );
});

test("vision provider requests enforce the recorded provider timeout", async () => {
  const originalFetch = global.fetch;
  global.fetch = async (_url, init) => new Promise((_resolve, reject) => {
    init.signal.addEventListener("abort", () => reject(init.signal.reason), { once: true });
  });
  try {
    await assert.rejects(
      fetchWithAbortSignal("https://provider.example/v1/chat/completions", {}, null, 5),
      /provider request timed out after 5ms/,
    );
  } finally {
    global.fetch = originalFetch;
  }
});

test("benchmark conversation ids are opaque and cannot leak scenario identity into attachment paths", () => {
  const id = benchmarkConversationId();
  assert.match(id, /^bench-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
  assert.doesNotMatch(id, /beam|frame|portal|truss|scenario/i);
});

test("runtime attachment identity cannot reveal a static fixture or scenario name", () => {
  const previousDataDir = process.env.SCLAW_DATA_DIR;
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), "sclaw-bench-attachment-"));
  process.env.SCLAW_DATA_DIR = dataDir;
  try {
    const attachments = copyAttachmentsToRuntimeUploads([{
      fileId: "re-dxf-beam-simple",
      originalName: "drawing-042.dxf",
      relPath: "fixtures/drawings/beam-simple-6m.dxf",
      mimeType: "application/dxf",
    }], "bench-00000000-0000-4000-8000-000000000000");

    assert.equal(attachments[0].originalName, "attachment-1.dxf");
    assert.doesNotMatch(attachments[0].relPath, /beam|simple|drawing-042/i);
    assert.match(attachments[0].relPath, /attachment-1\.dxf$/);
  } finally {
    if (previousDataDir === undefined) delete process.env.SCLAW_DATA_DIR;
    else process.env.SCLAW_DATA_DIR = previousDataDir;
    fs.rmSync(dataDir, { recursive: true, force: true });
  }
});

test("uses vision reasoning content when the ordinary content field is empty", () => {
  assert.equal(
    contentTextFromOpenAiMessage({
      content: "",
      reasoning_content: '{"structuralType":"frame"}',
    }),
    '{"structuralType":"frame"}',
  );
  assert.equal(
    contentTextFromOpenAiMessage({
      content: [],
      provider_specific_fields: {
        reasoning_content: '{"structuralType":"truss"}',
      },
    }),
    '{"structuralType":"truss"}',
  );
});

test("vision summaries require exact JSON and the declared field schema", () => {
  const summary = parseVisionSummary({
    content: JSON.stringify({
      structuralType: "truss",
      coordinateSystem: "XZ",
      nodes: ["N1", "N2"],
      members: ["N1-N2"],
      geometry: ["span=6m"],
      loads: [],
      supports: ["N1 pin"],
      materialsOrSections: [],
      missingOrUnclear: [],
      notes: [],
    }),
  }, "stop");
  assert.deepEqual(JSON.parse(summary), {
    structuralType: "truss",
    coordinateSystem: "XZ",
    nodes: ["N1", "N2"],
    members: ["N1-N2"],
    geometry: ["span=6m"],
    loads: [],
    supports: ["N1 pin"],
    materialsOrSections: [],
    missingOrUnclear: [],
    notes: [],
  });
  assert.deepEqual(
    JSON.parse(parseVisionSummary({
      content: JSON.stringify({
        structuralType: "frame",
        coordinateSystem: "XYZ",
        nodes: [{ id: "N1", coordinates: [0, 0, 0] }],
        members: [],
        geometry: [],
        loads: [],
        supports: [{ node: "N1", type: "fixed" }],
        materialsOrSections: [],
        missingOrUnclear: [],
        notes: [],
      }),
    }, "stop")).supports,
    [{ node: "N1", type: "fixed" }],
  );

  assert.throws(
    () => parseVisionSummary({
      content: '```json\n{"structuralType":"truss"}\n```',
    }, "stop"),
    /VISION_MODEL_INVALID_OUTPUT:.*finishReason=stop/u,
  );
  assert.throws(
    () => parseVisionSummary({
      content: '{"structuralType":"truss"',
    }, "length"),
    /VISION_MODEL_INVALID_OUTPUT:.*finishReason=length/u,
  );
  assert.throws(
    () => parseVisionSummary({
      content: JSON.stringify({
        structuralType: "truss",
        coordinateSystem: "XZ",
        nodes: "N1, N2",
        members: [],
        geometry: [],
        loads: [],
        supports: [],
        materialsOrSections: [],
        missingOrUnclear: [],
        notes: [],
      }),
    }, "stop"),
    /VISION_MODEL_INVALID_OUTPUT:.*schema/u,
  );
});

test("benchmark tool scope excludes unscored calculators, code checks, workspace, memory, and shell access", () => {
  const definitions = [
    "detect_structure_type",
    "extract_draft_params",
    "build_model",
    "validate_model",
    "run_analysis",
    "run_code_check",
    "generate_report",
    "calculate",
    "ask_user_clarification",
    "set_session_config",
    "analyze_file",
    "memory",
    "glob_files",
    "grep_files",
    "read_file",
    "write_file",
    "replace_in_file",
    "move_path",
    "delete_path",
    "shell",
  ].map((name) => ({ name, defaultEnabled: true }));

  assert.deepEqual(selectBenchmarkToolIds(definitions), [
    "detect_structure_type",
    "extract_draft_params",
    "build_model",
    "validate_model",
    "run_analysis",
    "generate_report",
    "ask_user_clarification",
    "set_session_config",
    "analyze_file",
  ]);
});

test("explicit runner filters replace suite defaults instead of emitting duplicate flags", () => {
  assert.deepEqual(
    mergeRunnerArgs(
      ["--scenario", "std-beam-4m-point-mid", "--mode", "auto", "--supervise"],
      ["--scenario", "beam-overhanging-static", "--case-timeout-ms", "900000"],
    ),
    [
      "--mode", "auto",
      "--supervise",
      "--scenario", "beam-overhanging-static",
      "--case-timeout-ms", "900000",
    ],
  );
});

test("runtime settings never copy primary or vision API keys from source data", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "sclaw-bench-settings-"));
  const sourceDir = path.join(root, "source");
  const runtimeDir = path.join(root, "runtime");
  fs.mkdirSync(sourceDir, { recursive: true });
  fs.writeFileSync(path.join(sourceDir, "settings.json"), JSON.stringify({
    llm: {
      apiKey: "source-primary-secret",
      model: "old-primary",
    },
    vision: {
      apiKey: "source-vision-secret",
      model: "old-vision",
    },
  }));

  try {
    syncRuntimeSettings(
      runtimeDir,
      sourceDir,
      { model: "test-primary", baseUrl: "https://provider.example/v1" },
      900000,
    );
    const runtime = JSON.parse(fs.readFileSync(path.join(runtimeDir, "settings.json"), "utf8"));

    assert.equal(runtime.llm.apiKey, undefined);
    assert.equal(runtime.vision.apiKey, undefined);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});
