const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");

const {
  calculateProviderRateLimitBackoffMs,
  runAgentLikeWeb,
  supervisedOutputPath,
} = require("../runner.cjs");

test("provider rate-limit retries use capped exponential backoff", () => {
  assert.equal(calculateProviderRateLimitBackoffMs(1, 30_000, 120_000), 30_000);
  assert.equal(calculateProviderRateLimitBackoffMs(2, 30_000, 120_000), 60_000);
  assert.equal(calculateProviderRateLimitBackoffMs(3, 30_000, 120_000), 120_000);
  assert.equal(calculateProviderRateLimitBackoffMs(5, 30_000, 120_000), 120_000);
});

test("supervised case output paths are absolute across child working directories", () => {
  const output = supervisedOutputPath("results/run.json", { id: "beam-case#auto" });

  assert.equal(
    output,
    path.resolve(__dirname, "..", "results", "run.json.cases", "beam-case-auto.json"),
  );
});

test("web-stream execution propagates provider errors instead of evaluating a partial checkpoint", async () => {
  let snapshotRead = false;
  const service = {
    async *runStream() {
      yield { type: "start" };
      yield { type: "error", error: "429 MODEL_RATE_LIMIT" };
    },
    async getConversationSessionSnapshot() {
      snapshotRead = true;
      return { state: { model: null } };
    },
  };

  await assert.rejects(
    runAgentLikeWeb(service, { conversationId: "rate-limit-case", context: { locale: "en" } }),
    /429 MODEL_RATE_LIMIT/,
  );
  assert.equal(snapshotRead, false);
});

test("web-stream execution still returns the final checkpoint after normal completion", async () => {
  const state = { model: { nodes: [], elements: [] } };
  const service = {
    async *runStream() {
      yield { type: "start" };
      yield { type: "done" };
    },
    async getConversationSessionSnapshot() {
      return { state };
    },
  };

  assert.equal(
    await runAgentLikeWeb(service, { conversationId: "normal-case", context: { locale: "en" } }),
    state,
  );
});
