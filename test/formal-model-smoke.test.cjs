const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const {
  assertConfiguredJobs,
  buildSmokeJobs,
  chatCompletionUrls,
  requestBody,
} = require("../scripts/smoke-formal-models.cjs");

const matrix = JSON.parse(fs.readFileSync(
  path.join(__dirname, "..", "experiments", "formal-matrix.json"),
  "utf8",
));

test("formal smoke covers ten text models, six vision combinations, and one judge", () => {
  const jobs = buildSmokeJobs(matrix);

  assert.equal(jobs.filter((job) => job.kind === "text").length, 10);
  assert.equal(jobs.filter((job) => job.kind === "vision").length, 6);
  assert.equal(jobs.filter((job) => job.kind === "judge").length, 1);
  assert.ok(jobs.some((job) => job.id === "text:glm-5.2-paratera"));
  assert.ok(jobs.some((job) => job.id === "judge:glm-5.2-paratera"));
  assert.equal(
    jobs.find((job) => job.id === "vision:kimi-k2.6-native").temperature,
    1,
  );
  assert.equal(
    jobs.find((job) => job.id === "vision:claude-opus-4-8-native").temperature,
    null,
  );
  assert.ok(
    jobs
      .filter(
        (job) =>
          job.kind === "vision"
          && !["vision:kimi-k2.6-native", "vision:claude-opus-4-8-native"].includes(job.id),
      )
      .every((job) => job.temperature === 0),
  );
  assert.ok(!jobs.some((job) => job.modelId === "glm-5.2-mine"));
});

test("formal smoke requires every referenced provider configuration", () => {
  const jobs = buildSmokeJobs(matrix);
  const config = {
    models: Object.fromEntries(
      [...new Set(jobs.map((job) => job.modelId))]
        .map((modelId) => [modelId, {
          model: modelId,
          baseUrl: "https://example.com/v1",
          apiKeyEnv: "TEST_KEY",
        }]),
    ),
  };

  assert.doesNotThrow(() => assertConfiguredJobs(jobs, config));
  delete config.models[matrix.judgeModel];
  assert.throws(() => assertConfiguredJobs(jobs, config), /unconfigured models/);
});

test("chat completion URLs and multimodal request bodies match the production contract", () => {
  assert.deepEqual(
    chatCompletionUrls("https://example.com/v1"),
    ["https://example.com/v1/chat/completions"],
  );
  const body = requestBody(
    { kind: "vision" },
    {
      model: "GLM-4.6V",
      extraEnv: { LLM_VISION_TEMPERATURE: "0" },
    },
    "data:image/png;base64,abc",
  );

  assert.equal(body.model, "GLM-4.6V");
  assert.equal(body.messages[0].content[0].type, "image_url");
  assert.equal(body.temperature, 0);
  assert.deepEqual(body.thinking, { type: "disabled" });
});

test("formal smoke omits incompatible text temperature and honors vision configuration", () => {
  const model = {
    model: "kimi-k2.6",
    extraEnv: {
      LLM_OMIT_TEMPERATURE_MODELS: "kimi-k2.6",
      LLM_VISION_TEMPERATURE: "1",
    },
  };

  const textBody = requestBody({ kind: "text" }, model, null);
  const visionBody = requestBody(
    { kind: "vision", temperature: 1 },
    model,
    "data:image/png;base64,abc",
  );
  assert.equal(Object.hasOwn(textBody, "temperature"), false);
  assert.equal(visionBody.temperature, 1);

  const claudeVisionBody = requestBody(
    { kind: "vision", temperature: null },
    { model: "claude-opus-4-8" },
    "data:image/png;base64,abc",
  );
  assert.equal(Object.hasOwn(claudeVisionBody, "temperature"), false);
});
