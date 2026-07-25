const fs = require("node:fs");
const path = require("node:path");

const BENCH_ROOT = path.resolve(__dirname, "..");
const DEFAULT_MATRIX = path.join(BENCH_ROOT, "experiments", "formal-matrix.json");
const DEFAULT_CONFIG = path.join(BENCH_ROOT, "experiments", "llm-experiments.local.json");
const DEFAULT_IMAGE = path.join(BENCH_ROOT, "fixtures", "frame-sketch.png");

function usage() {
  return [
    "Usage:",
    "  node scripts/smoke-formal-models.cjs [options]",
    "",
    "Options:",
    "  --matrix <file>       Defaults to experiments/formal-matrix.json.",
    "  --config <file>       Defaults to experiments/llm-experiments.local.json.",
    "  --output <file>       Optional JSON result file.",
    "  --concurrency <n>     Defaults to 4.",
    "  --timeout-ms <n>      Per-request timeout; defaults to 180000.",
    "  --dry-run             Validate configuration without network requests.",
  ].join("\n");
}

function requireValue(argv, index, flag) {
  const value = argv[index];
  if (!value || value.startsWith("--")) throw new Error(`Missing value for ${flag}`);
  return value;
}

function parseArgs(argv) {
  const options = {
    matrixPath: DEFAULT_MATRIX,
    configPath: DEFAULT_CONFIG,
    outputPath: null,
    concurrency: 4,
    timeoutMs: 180_000,
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
    } else if (arg === "--output") {
      options.outputPath = path.resolve(requireValue(argv, ++index, arg));
    } else if (arg === "--concurrency") {
      options.concurrency = Number(requireValue(argv, ++index, arg));
    } else if (arg === "--timeout-ms") {
      options.timeoutMs = Number(requireValue(argv, ++index, arg));
    } else if (arg === "--dry-run") {
      options.dryRun = true;
    } else {
      throw new Error(`Unknown option: ${arg}\n\n${usage()}`);
    }
  }
  if (!Number.isSafeInteger(options.concurrency) || options.concurrency <= 0) {
    throw new Error("--concurrency must be a positive integer");
  }
  if (!Number.isSafeInteger(options.timeoutMs) || options.timeoutMs <= 0) {
    throw new Error("--timeout-ms must be a positive integer");
  }
  return options;
}

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function chatCompletionUrls(baseUrl) {
  const trimmed = String(baseUrl || "").replace(/\/+$/, "");
  if (/\/chat\/completions$/i.test(trimmed)) return [trimmed];
  if (/\/v\d+$/i.test(trimmed)) return [`${trimmed}/chat/completions`];
  const parsed = new URL(trimmed);
  if (parsed.pathname && parsed.pathname !== "/") return [`${trimmed}/v1/chat/completions`];
  return [`${trimmed}/v1/chat/completions`, `${trimmed}/chat/completions`];
}

function buildSmokeJobs(matrix) {
  return [
    ...matrix.textModels.map((modelId) => ({
      id: `text:${modelId}`,
      kind: "text",
      modelId,
      configurationId: null,
    })),
    ...matrix.multimodalConfigurations.map((configuration) => ({
      id: `vision:${configuration.id}`,
      kind: "vision",
      modelId: configuration.visionModel,
      agentModelId: configuration.agentModel,
      configurationId: configuration.id,
    })),
    {
      id: `judge:${matrix.judgeModel}`,
      kind: "judge",
      modelId: matrix.judgeModel,
      configurationId: null,
    },
  ];
}

function assertConfiguredJobs(jobs, config) {
  const missing = [...new Set(jobs.map((job) => job.modelId))]
    .filter((modelId) => !config.models?.[modelId]);
  if (missing.length > 0) {
    throw new Error(`Smoke matrix references unconfigured models: ${missing.join(", ")}`);
  }
  const invalid = jobs.filter((job) => {
    const model = config.models[job.modelId];
    return !model.model || !model.baseUrl || !model.apiKeyEnv;
  });
  if (invalid.length > 0) {
    throw new Error(`Incomplete model configuration: ${invalid.map((job) => job.modelId).join(", ")}`);
  }
}

function requestBody(job, model, imageDataUri) {
  const body = {
    model: model.model,
    max_tokens: job.kind === "judge" ? 4096 : 512,
    messages: [],
  };
  const omittedTemperatureModels = String(model.extraEnv?.LLM_OMIT_TEMPERATURE_MODELS || "")
    .split(",")
    .map((value) => value.trim().toLowerCase())
    .filter(Boolean);
  if (job.kind === "vision" && model.extraEnv?.LLM_VISION_TEMPERATURE !== undefined) {
    body.temperature = Number(model.extraEnv.LLM_VISION_TEMPERATURE);
  } else if (!omittedTemperatureModels.includes(String(model.model).toLowerCase())) {
    body.temperature = 0;
  }
  if (/^glm-(?:4\.[5-9]|5(?:[.-]|$))/i.test(model.model)) {
    body.thinking = { type: "disabled" };
  }
  if (job.kind === "vision") {
    body.messages.push({
      role: "user",
      content: [
        { type: "image_url", image_url: { url: imageDataUri } },
        { type: "text", text: "Connectivity check. Reply with the single word READY." },
      ],
    });
  } else if (job.kind === "judge") {
    body.response_format = { type: "json_object" };
    body.messages.push(
      { role: "system", content: "Return exactly one JSON object." },
      { role: "user", content: '{"pass": true} must be returned for this connectivity check.' },
    );
  } else {
    body.messages.push({
      role: "user",
      content: "Connectivity check. Reply with the single word READY.",
    });
  }
  return body;
}

function messageText(message) {
  if (typeof message?.content === "string") return message.content.trim();
  if (Array.isArray(message?.content)) {
    return message.content
      .map((item) => typeof item === "string" ? item : item?.text || "")
      .join("")
      .trim();
  }
  return String(message?.reasoning_content || "").trim();
}

async function requestWithTimeout(url, init, timeoutMs) {
  const controller = new AbortController();
  const timeout = setTimeout(() => {
    controller.abort(new Error(`request timed out after ${timeoutMs}ms`));
  }, timeoutMs);
  try {
    return await fetch(url, { ...init, signal: controller.signal });
  } finally {
    clearTimeout(timeout);
  }
}

async function runJob(job, config, imageDataUri, timeoutMs) {
  const model = config.models[job.modelId];
  const apiKey = process.env[model.apiKeyEnv];
  const startedAt = new Date().toISOString();
  const started = Date.now();
  if (!apiKey) {
    return {
      ...job,
      provider: model.provider || null,
      configuredModel: model.model,
      startedAt,
      durationMs: Date.now() - started,
      pass: false,
      error: `missing environment variable ${model.apiKeyEnv}`,
    };
  }
  let lastError = null;
  for (const url of chatCompletionUrls(model.baseUrl)) {
    try {
      const response = await requestWithTimeout(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${apiKey}`,
        },
        body: JSON.stringify(requestBody(job, model, imageDataUri)),
      }, timeoutMs);
      const responseText = await response.text();
      if (!response.ok) {
        lastError = `HTTP ${response.status}: ${responseText.slice(0, 300)}`;
        if (response.status === 404) continue;
        break;
      }
      let payload;
      try {
        payload = JSON.parse(responseText);
      } catch {
        lastError = `non-JSON response: ${responseText.slice(0, 300)}`;
        break;
      }
      const text = messageText(payload.choices?.[0]?.message);
      if (!text) {
        lastError = "response has no assistant message content";
        break;
      }
      if (job.kind === "judge") {
        try {
          const verdict = JSON.parse(text);
          if (verdict.pass !== true) {
            lastError = `judge returned unexpected verdict: ${text.slice(0, 300)}`;
            break;
          }
        } catch {
          lastError = `judge returned invalid JSON: ${text.slice(0, 300)}`;
          break;
        }
      }
      return {
        ...job,
        provider: model.provider || null,
        configuredModel: model.model,
        endpoint: new URL(url).host,
        startedAt,
        finishedAt: new Date().toISOString(),
        durationMs: Date.now() - started,
        pass: true,
        finishReason: payload.choices?.[0]?.finish_reason || null,
      };
    } catch (error) {
      lastError = error instanceof Error ? error.message : String(error);
    }
  }
  return {
    ...job,
    provider: model.provider || null,
    configuredModel: model.model,
    startedAt,
    finishedAt: new Date().toISOString(),
    durationMs: Date.now() - started,
    pass: false,
    error: lastError || "request failed",
  };
}

async function runPool(items, concurrency, worker) {
  let nextIndex = 0;
  const results = new Array(items.length);
  const take = async () => {
    while (true) {
      const index = nextIndex;
      nextIndex += 1;
      if (index >= items.length) return;
      results[index] = await worker(items[index]);
      const result = results[index];
      process.stdout.write(
        `${result.pass ? "PASS" : "FAIL"} ${result.id}`
        + ` ${result.durationMs ?? 0}ms${result.error ? ` ${result.error}` : ""}\n`,
      );
    }
  };
  await Promise.all(Array.from({ length: Math.min(concurrency, items.length) }, take));
  return results;
}

async function main(argv) {
  const options = parseArgs(argv);
  const matrix = readJson(options.matrixPath);
  const config = readJson(options.configPath);
  const jobs = buildSmokeJobs(matrix);
  assertConfiguredJobs(jobs, config);
  const glmPair = matrix.multimodalConfigurations
    .find((configuration) => configuration.agentModel === "glm-5.2-paratera");
  if (!matrix.textModels.includes("glm-5.2-paratera") || !glmPair) {
    throw new Error("Formal smoke must use glm-5.2-paratera for the nighttime Paratera run");
  }
  if (matrix.textModels.includes("glm-5.2-mine")) {
    throw new Error("Formal smoke must not use glm-5.2-mine");
  }
  if (options.dryRun) {
    process.stdout.write(`Formal model smoke dry-run: ${jobs.length} jobs\n`);
    for (const job of jobs) process.stdout.write(`  ${job.id}\n`);
    return 0;
  }
  const imageDataUri = `data:image/png;base64,${fs.readFileSync(DEFAULT_IMAGE).toString("base64")}`;
  const startedAt = new Date().toISOString();
  const results = await runPool(
    jobs,
    options.concurrency,
    (job) => runJob(job, config, imageDataUri, options.timeoutMs),
  );
  const output = {
    schemaVersion: "structureclaw-formal-model-smoke/v1",
    startedAt,
    finishedAt: new Date().toISOString(),
    matrixPath: options.matrixPath,
    textModelCount: matrix.textModels.length,
    multimodalConfigurationCount: matrix.multimodalConfigurations.length,
    judgeModel: matrix.judgeModel,
    passed: results.filter((result) => result.pass).length,
    failed: results.filter((result) => !result.pass).length,
    results,
  };
  if (options.outputPath) {
    fs.mkdirSync(path.dirname(options.outputPath), { recursive: true });
    fs.writeFileSync(options.outputPath, `${JSON.stringify(output, null, 2)}\n`);
  }
  process.stdout.write(
    `Formal model smoke: passed=${output.passed}/${results.length}`
    + `${options.outputPath ? ` output=${options.outputPath}` : ""}\n`,
  );
  return output.failed === 0 ? 0 : 1;
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
  assertConfiguredJobs,
  buildSmokeJobs,
  chatCompletionUrls,
  parseArgs,
  requestBody,
};
