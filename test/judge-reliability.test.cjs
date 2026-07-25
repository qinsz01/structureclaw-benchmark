const test = require("node:test");
const assert = require("node:assert/strict");

const {
  buildJudgeRequestBody,
  evaluateNaturalLanguage,
  judgeChatCompletionsUrl,
  judgeChatCompletionsUrls,
} = require("../lib/judge.cjs");

test("natural-language judge retries a non-JSON response", async () => {
  let calls = 0;
  const prompts = [];
  const result = await evaluateNaturalLanguage(
    "The response should explain the engineering consequence.",
    {},
    {
      callJudgeApi: async (prompt) => {
        calls += 1;
        prompts.push(prompt);
        return calls === 1 ? "The criterion is clearly met." : '{"pass":true}';
      },
    },
  );

  assert.equal(calls, 2);
  assert.equal(result.pass, true);
  assert.doesNotMatch(prompts[0], /previous response violated/i);
  assert.match(prompts[1], /previous response violated/i);
  assert.match(prompts[1], /only one valid JSON object/i);
});

test("semantic assertions always use the configured judge", async () => {
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

  assert.equal(calls, 1);
  assert.equal(result.pass, false);
});

test("unrelated evidence cannot pass without the judge approving it", async () => {
  let calls = 0;
  const result = await evaluateNaturalLanguage(
    "Analysis results should include deflection at the overhanging end and the explicitly requested full-length midpoint",
    { analysisResult: { displacements: [{ node: "unrelated", uz: -0.1 }] } },
    {
      callJudgeApi: async () => {
        calls += 1;
        return '{"pass":false,"reason":"requested locations are absent"}';
      },
    },
  );

  assert.equal(calls, 1);
  assert.equal(result.pass, false);
});

test("persistent judge protocol failures are infrastructure errors", async () => {
  let calls = 0;
  await assert.rejects(
    evaluateNaturalLanguage(
      "The response should explain the engineering consequence.",
      {},
      {
        callJudgeApi: async () => {
          calls += 1;
          return "not JSON";
        },
      },
    ),
    /LLM_JUDGE_INFRASTRUCTURE_ERROR/,
  );
  assert.equal(calls, 3);
});

test("judge evidence includes LangChain and serialized assistant messages", async () => {
  const prompts = [];
  const result = await evaluateNaturalLanguage(
    "The agent should ask for the missing span.",
    {
      messages: [
        {
          _getType() {
            return "ai";
          },
          content: "Please provide the missing span.",
          tool_calls: [],
        },
        {
          id: ["langchain_core", "messages", "AIMessage"],
          kwargs: {
            content: "The support condition is also required.",
            tool_calls: [],
          },
        },
      ],
    },
    {
      callJudgeApi: async (prompt) => {
        prompts.push(prompt);
        return '{"pass":true}';
      },
    },
  );

  assert.equal(result.pass, true);
  assert.match(prompts[0], /Please provide the missing span/);
  assert.match(prompts[0], /support condition is also required/);
});

test("judge evidence includes structured tool-call arguments", async () => {
  const prompts = [];
  const result = await evaluateNaturalLanguage(
    "The agent should request either a genuine 3-D model or a supported alternative.",
    {
      messages: [{
        id: ["langchain_core", "messages", "AIMessage"],
        kwargs: {
          content: "Let me ask how you would like to proceed.",
          tool_calls: [{
            name: "ask_user_clarification",
            args: {
              question: "Please provide a genuine 3-D model or choose the supported built-in solver.",
              optionsJson: "[\"Provide 3-D model\", \"Use built-in solver\"]",
            },
          }],
        },
      }],
    },
    {
      callJudgeApi: async (prompt) => {
        prompts.push(prompt);
        return '{"pass":true}';
      },
    },
  );

  assert.equal(result.pass, true);
  assert.match(prompts[0], /ask_user_clarification/);
  assert.match(prompts[0], /genuine 3-D model/);
  assert.match(prompts[0], /supported built-in solver/);
});

test("judge evidence states analysis units and coordinate metadata explicitly", async () => {
  const prompts = [];
  const result = await evaluateNaturalLanguage(
    "The response should report the midspan vertical deflection with a consistent value and unit.",
    {
      analysisResult: {
        success: true,
        data: {
          displacements: {
            "2": { uz: -0.0164634146 },
          },
          meta: {
            coordinateSemantics: "global-z-up",
            dimension: "2d",
            plane: "xz",
            nodalResultFrame: "global",
            units: {
              displacement: "m",
              force: "kN",
              moment: "kN.m",
            },
          },
        },
      },
      messages: [{
        role: "assistant",
        content: "The midspan vertical deflection is -16.46 mm.",
      }],
    },
    {
      callJudgeApi: async (prompt) => {
        prompts.push(prompt);
        return '{"pass":true}';
      },
    },
  );

  assert.equal(result.pass, true);
  assert.match(prompts[0], /Analysis result units: \{"displacement":"m","force":"kN","moment":"kN\.m"\}/);
  assert.match(prompts[0], /Analysis result coordinate metadata: .*"coordinateSemantics":"global-z-up"/);
  assert.match(prompts[0], /"nodalResultFrame":"global"/);
});

test("judge distinguishes structural inputs from computed solver results", async () => {
  const prompts = [];
  const result = await evaluateNaturalLanguage(
    "The agent must not report numerical analysis results after an adapter capability refusal.",
    {
      model: {
        nodes: [{ id: "1", x: 0, y: 0, z: 0 }],
        elements: [],
        materials: [{ id: "steel", E: 2.06e8 }],
        sections: [{ id: "column", properties: { A: 0.02 } }],
        load_cases: [{ id: "DL", loads: [{ type: "nodal", node: "1", fz: -10 }] }],
      },
      analysisResult: {
        success: false,
        error_code: "ENGINE_INPUT_UNSUPPORTED",
        data: {},
      },
    },
    {
      callJudgeApi: async (prompt) => {
        prompts.push(prompt);
        return '{"pass":true}';
      },
    },
  );

  assert.equal(result.pass, true);
  assert.match(prompts[0], /Structural model input \(not a computed solver result\)/);
  assert.match(prompts[0], /Analysis attempt outcome: success=false, error_code=ENGINE_INPUT_UNSUPPORTED/);
  assert.match(prompts[0], /applied loads in the structural model are input data, not computed analysis results/);
});

test("late clarification evidence is retained after a long tool trace", async () => {
  const prompts = [];
  const earlierCalls = Array.from({ length: 12 }, (_, index) => ({
    name: "calculate",
    args: { expression: `${index}+1`, padding: "x".repeat(2500) },
  }));
  const result = await evaluateNaturalLanguage(
    "The agent should ask which support condition applies.",
    {
      messages: [{
        role: "assistant",
        content: "",
        tool_calls: [
          ...earlierCalls,
          {
            name: "ask_user_clarification",
            args: { question: "Should the right support be pinned or a roller?" },
          },
        ],
      }],
    },
    {
      callJudgeApi: async (prompt) => {
        prompts.push(prompt);
        return '{"pass":true}';
      },
    },
  );

  assert.equal(result.pass, true);
  assert.match(prompts[0], /Should the right support be pinned or a roller/);
});

test("judge accepts base URLs with or without a versioned chat-completions path", () => {
  assert.equal(
    judgeChatCompletionsUrl("https://provider.example/v1"),
    "https://provider.example/v1/chat/completions",
  );
  assert.equal(
    judgeChatCompletionsUrl("https://provider.example/api/paas/v4/"),
    "https://provider.example/api/paas/v4/chat/completions",
  );
  assert.equal(
    judgeChatCompletionsUrl("https://provider.example/v1/chat/completions"),
    "https://provider.example/v1/chat/completions",
  );
  assert.deepEqual(
    judgeChatCompletionsUrls("https://provider.example"),
    [
      "https://provider.example/v1/chat/completions",
      "https://provider.example/chat/completions",
    ],
  );
});

test("judge requests a deterministic JSON object without replacing semantic evaluation", () => {
  const body = buildJudgeRequestBody("judge-model", "criterion and evidence");

  assert.equal(body.model, "judge-model");
  assert.equal(body.temperature, 0);
  assert.equal(body.max_tokens, 4096);
  assert.deepEqual(body.response_format, { type: "json_object" });
  assert.match(body.messages[0].content, /JSON object/);
  assert.equal(body.messages[1].content, "criterion and evidence");
});

test("GLM judges disable thinking for reliable structured verdicts", () => {
  const glmBody = buildJudgeRequestBody("GLM-5.2", "criterion and evidence");
  const openAiBody = buildJudgeRequestBody("gpt-5", "criterion and evidence");

  assert.deepEqual(glmBody.thinking, { type: "disabled" });
  assert.equal(openAiBody.thinking, undefined);
});
