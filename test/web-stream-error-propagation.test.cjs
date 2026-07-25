const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");

const {
  calculateProviderRateLimitBackoffMs,
  runAgentLikeWeb,
  runAgentWebTurn,
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

test("web-stream execution stops on a tool-wrapped LLM infrastructure error", async () => {
  let snapshotRead = false;
  let streamClosed = false;
  const service = {
    async *runStream() {
      try {
        yield {
          type: "step_upsert",
          step: {
            output: "LLM_PARAM_EXTRACTOR_INFRASTRUCTURE_ERROR: network error: terminated",
          },
        };
        yield { type: "done" };
      } finally {
        streamClosed = true;
      }
    },
    async getConversationSessionSnapshot() {
      snapshotRead = true;
      return { state: { model: null } };
    },
  };

  await assert.rejects(
    runAgentLikeWeb(service, { conversationId: "extractor-network-error", context: { locale: "en" } }),
    /LLM_PARAM_EXTRACTOR_INFRASTRUCTURE_ERROR/,
  );
  assert.equal(streamClosed, true);
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

test("web-stream multi-turn execution resumes a pending clarification interrupt", async () => {
  const calls = [];
  let state = { draftState: { criticalMissing: ["lengthM"] } };
  const service = {
    async *runStream(input) {
      calls.push(["run", input.message]);
      yield {
        type: "interaction_update",
        content: { resumeRequired: true },
      };
    },
    async *resumeStream(conversationId, resumeValue) {
      calls.push(["resume", conversationId, resumeValue]);
      state = { model: { nodes: [], elements: [] } };
      yield { type: "done" };
    },
    async getConversationSessionSnapshot() {
      return { state };
    },
  };

  const first = await runAgentWebTurn(service, {
    message: "Analyze a simply supported beam.",
    conversationId: "multi-turn-case",
    context: { locale: "en" },
  });
  const second = await runAgentWebTurn(service, {
    message: "The span is 6 m.",
    conversationId: "multi-turn-case",
    context: { locale: "en" },
  }, { resume: first.resumeRequired });

  assert.equal(first.resumeRequired, true);
  assert.equal(second.resumeRequired, false);
  assert.deepEqual(calls, [
    ["run", "Analyze a simply supported beam."],
    ["resume", "multi-turn-case", "The span is 6 m."],
  ]);
  assert.equal(second.state, state);
});
