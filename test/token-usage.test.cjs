const test = require("node:test");
const assert = require("node:assert/strict");

const { evaluateScenario } = require("../lib/evaluate.cjs");
const { appendVisionUsageMetrics } = require("../runner.cjs");

test("records primary-model token usage without double-counting fallback metadata", async () => {
  const result = await evaluateScenario(
    { id: "token-usage", expect: { assertions: [] } },
    {
      messages: [
        {
          usage_metadata: {
            input_tokens: 100,
            output_tokens: 20,
            total_tokens: 120,
          },
          response_metadata: {
            tokenUsage: {
              promptTokens: 100,
              completionTokens: 20,
              totalTokens: 120,
            },
          },
        },
        {
          response_metadata: {
            tokenUsage: {
              promptTokens: 50,
              completionTokens: 10,
              totalTokens: 60,
            },
          },
        },
        {
          kwargs: {
            usage_metadata: {
              input_tokens: 25,
              output_tokens: 5,
              total_tokens: 30,
            },
          },
        },
      ],
    },
    1,
  );

  const metrics = Object.fromEntries(result.metrics.map((metric) => [metric.metric, metric.actual]));
  assert.equal(metrics.inputTokens, "175");
  assert.equal(metrics.outputTokens, "35");
  assert.equal(metrics.totalTokens, "210");
  assert.equal(result.passed, 0);
  assert.equal(result.total, 0);
});

test("counts tool calls from serialized checkpoint messages", async () => {
  const result = await evaluateScenario(
    { id: "tool-usage", expect: { assertions: [] } },
    {
      messages: [{
        kwargs: {
          tool_calls: [
            { name: "extract_draft_params" },
            { function: { name: "build_model" } },
          ],
        },
      }],
    },
    1,
  );

  assert.equal(result.metrics.find((metric) => metric.metric === "toolCalls")?.actual, "2");
});

test("records vision-model token usage separately from primary-model usage", async () => {
  const result = await evaluateScenario(
    { id: "vision-token-usage", expect: { assertions: [] } },
    { messages: [] },
    1,
  );
  appendVisionUsageMetrics(result, [
    {
      usage: { inputTokens: 80, outputTokens: 20, totalTokens: 100 },
    },
    {
      usage: { inputTokens: 40, outputTokens: 10, totalTokens: 50 },
    },
  ]);

  const metrics = Object.fromEntries(result.metrics.map((metric) => [metric.metric, metric.actual]));
  assert.equal(metrics.visionInputTokens, "120");
  assert.equal(metrics.visionOutputTokens, "30");
  assert.equal(metrics.visionTotalTokens, "150");
  assert.equal(result.passed, 0);
  assert.equal(result.total, 0);
  assert.equal(result.allPassed, true);
});
