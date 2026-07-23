const test = require("node:test");
const assert = require("node:assert/strict");

const { evaluateNaturalLanguage } = require("../lib/judge.cjs");

test("natural-language judge retries a non-JSON response", async () => {
  let calls = 0;
  const result = await evaluateNaturalLanguage(
    "The response should explain the engineering consequence.",
    {},
    {
      callJudgeApi: async () => {
        calls += 1;
        return calls === 1 ? "The criterion is clearly met." : '{"pass":true}';
      },
    },
  );

  assert.equal(calls, 2);
  assert.equal(result.pass, true);
});

test("poor drawing readability is checked deterministically", async () => {
  let calls = 0;
  const result = await evaluateNaturalLanguage(
    "The agent should mention the image quality is poor or blurry and either try to extract what it can or ask the user to provide a clearer image or supplement with text",
    {
      messages: [{
        role: "assistant",
        content: "Drawing Readability Assessment: the drawing quality is insufficient. Please provide a clearer, higher-resolution image or the missing parameters in text.",
      }],
    },
    {
      callJudgeApi: async () => {
        calls += 1;
        return '{"pass":false}';
      },
    },
  );

  assert.equal(calls, 0);
  assert.equal(result.pass, true);
});
