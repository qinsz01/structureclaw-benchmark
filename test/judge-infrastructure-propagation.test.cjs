const assert = require("node:assert/strict");
const test = require("node:test");

const { evaluateScenario } = require("../lib/evaluate.cjs");

test("judge infrastructure failures abort evaluation instead of counting as model failures", async () => {
  const previousJudgeKey = process.env.LLM_JUDGE_API_KEY;
  const previousPrimaryKey = process.env.LLM_API_KEY;
  delete process.env.LLM_JUDGE_API_KEY;
  delete process.env.LLM_API_KEY;

  try {
    await assert.rejects(
      evaluateScenario({
        id: "judge-infrastructure-contract",
        expect: {
          assertions: [{
            type: "natural_language",
            description: "The response should satisfy a semantic criterion.",
          }],
        },
      }, {}),
      /LLM_JUDGE_INFRASTRUCTURE_ERROR/,
    );
  } finally {
    if (previousJudgeKey === undefined) delete process.env.LLM_JUDGE_API_KEY;
    else process.env.LLM_JUDGE_API_KEY = previousJudgeKey;
    if (previousPrimaryKey === undefined) delete process.env.LLM_API_KEY;
    else process.env.LLM_API_KEY = previousPrimaryKey;
  }
});
