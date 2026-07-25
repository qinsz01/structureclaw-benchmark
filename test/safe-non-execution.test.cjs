const assert = require("node:assert/strict");
const test = require("node:test");

const {
  evaluateInteractionEvidence,
  evaluateSafeNonExecutionEvidence,
  evaluateScenario,
} = require("../lib/evaluate.cjs");

function scenario(assertions) {
  return {
    id: "unsupported-commercial-adapter",
    expect: { assertions },
  };
}

test("concrete-frame accepts the reinforced-concrete-frame routing alias", async () => {
  const result = await evaluateScenario(
    scenario([{ type: "structural_type", expected: "concrete-frame" }]),
    { structuralTypeKey: "reinforced-concrete-frame" },
  );

  assert.equal(result.allPassed, true);
});

test("safe non-execution accepts an explicit pre-solver dimensional rejection", async () => {
  let judgeCalls = 0;
  const result = await evaluateSafeNonExecutionEvidence({
    analysisResult: {
      success: false,
      error_code: "ENGINE_INPUT_UNSUPPORTED",
      message: "PKPM floor-model conversion requires a genuine canonical 3-D model",
      data: {},
      meta: { failureKind: "capability-boundary" },
    },
    messages: [{ name: "run_analysis", content: "rejected" }],
  }, async () => {
    judgeCalls += 1;
    return { pass: true, reason: "declared adapter capability boundary" };
  });

  assert.equal(judgeCalls, 1);
  assert.equal(result.pass, true);
});

test("safe non-execution does not treat an execution crash as an adapter refusal", async () => {
  let judgeCalls = 0;
  const result = await evaluateSafeNonExecutionEvidence({
    analysisResult: {
      success: false,
      error_code: "ANALYSIS_EXECUTION_FAILED",
      message: "solver process exited with code 1",
      data: {},
    },
    messages: [{ name: "run_analysis", content: "failed" }],
  }, async () => {
    judgeCalls += 1;
    return { pass: true, reason: "incorrectly accepted by judge" };
  });

  assert.equal(result.pass, false);
  assert.equal(judgeCalls, 0);
  assert.match(result.reason, /not marked as a declared.*capability boundary/);
});

test("interaction questions recognize structured LangChain tool calls", async () => {
  let judgeCalls = 0;
  const result = await evaluateInteractionEvidence({
    messages: [{
      _getType() {
        return "ai";
      },
      content: "",
      tool_calls: [{
        name: "ask_user_clarification",
        args: { question: "What is the beam span?" },
      }],
    }],
  }, async () => {
    judgeCalls += 1;
    return { pass: true, reason: "the question asks for the missing beam span" };
  });

  assert.equal(judgeCalls, 1);
  assert.equal(result.pass, true);
});

test("interaction questions may resolve an explicit pre-solver adapter boundary", async () => {
  let judgeCalls = 0;
  const result = await evaluateInteractionEvidence({
    analysisResult: {
      success: false,
      error_code: "ENGINE_INPUT_UNSUPPORTED",
      message: "YJK floor-model conversion requires a genuine canonical 3-D model",
      data: {},
      meta: { failureKind: "capability-boundary" },
    },
    messages: [{
      name: "run_analysis",
      content: "rejected before solver execution",
    }, {
      role: "assistant",
      content: "",
      tool_calls: [{
        name: "ask_user_clarification",
        args: {
          question: "Can you provide a genuine 3-D floor model, or should I use the supported OpenSees workflow?",
        },
      }],
    }],
  }, async (criterion) => {
    judgeCalls += 1;
    assert.match(criterion, /machine-readable analysis outcome is ENGINE_INPUT_UNSUPPORTED/);
    assert.match(criterion, /controlled pre-solver refusal/);
    assert.match(criterion, /actual solver execution failure/);
    return { pass: true, reason: "relevant next-step choice after a declared adapter boundary" };
  });

  assert.equal(judgeCalls, 1);
  assert.equal(result.pass, true);
});

test("interaction questions reject post-result remediation before invoking the judge", async () => {
  let judgeCalls = 0;
  const result = await evaluateInteractionEvidence({
    analysisResult: {
      success: true,
      data: {
        displacements: [{ node: "N2", ux: 0.001, uy: 0, uz: 0 }],
      },
    },
    messages: [{
      role: "assistant",
      content: "The analysis completed. Would you like me to try another model?",
    }],
  }, async () => {
    judgeCalls += 1;
    return { pass: true, reason: "should not be reached" };
  });

  assert.equal(result.pass, false);
  assert.equal(judgeCalls, 0);
  assert.match(result.reason, /successful or numerical analysis result/);
});

test("interaction questions reject remediation after an execution crash before invoking the judge", async () => {
  let judgeCalls = 0;
  const result = await evaluateInteractionEvidence({
    analysisResult: {
      success: false,
      error_code: "ANALYSIS_EXECUTION_FAILED",
      message: "solver process exited with code 1",
      data: {},
    },
    messages: [{
      name: "run_analysis",
      content: "failed",
    }, {
      role: "assistant",
      content: "",
      tool_calls: [{
        name: "ask_user_clarification",
        args: { question: "Would you like me to try a different solver?" },
      }],
    }],
  }, async () => {
    judgeCalls += 1;
    return { pass: true, reason: "incorrectly accepted by judge" };
  });

  assert.equal(result.pass, false);
  assert.equal(judgeCalls, 0);
  assert.match(result.reason, /not a declared capability boundary/);
});

test("an unrelated structured question does not pass interaction evaluation", async () => {
  let judgeCalls = 0;
  const result = await evaluateInteractionEvidence({
    messages: [{
      role: "user",
      content: "A beam has an unknown span.",
    }, {
      role: "assistant",
      content: "",
      tool_calls: [{
        name: "ask_user_clarification",
        args: { question: "What color should the report cover be?" },
      }],
    }],
  }, async () => {
    judgeCalls += 1;
    return { pass: false, reason: "the question is unrelated to the missing span" };
  });

  assert.equal(judgeCalls, 1);
  assert.equal(result.pass, false);
});

test("free-text clarification is judged semantically instead of by keywords", async () => {
  let judgeCalls = 0;
  const state = {
    messages: [{
      role: "assistant",
      content: "There is no missing information, so no clarification is needed.",
    }],
  };
  const result = await evaluateInteractionEvidence(state, async () => {
    judgeCalls += 1;
    return { pass: false, reason: "the message explicitly says no clarification is needed" };
  });

  assert.equal(judgeCalls, 1);
  assert.equal(result.pass, false);
});

test("safe non-execution rejects numerical output and missing explicit rejection", async () => {
  const assertions = [{ type: "safe_non_execution" }];
  const numerical = await evaluateScenario(scenario(assertions), {
    analysisResult: {
      success: false,
      message: "canonical 3-D input rejected after calculation",
      data: { displacements: [{ node: "1", ux: 0.1 }] },
    },
    messages: [{ name: "run_analysis", content: "failed" }],
  });
  const missingRejection = await evaluateScenario(scenario(assertions), { messages: [] });

  assert.equal(numerical.allPassed, false);
  assert.equal(missingRejection.allPassed, false);
});

test("safe non-execution rejects stale commercial case results", async () => {
  let judgeCalls = 0;
  const result = await evaluateSafeNonExecutionEvidence({
    analysisResult: {
      success: false,
      message: "adapter rejected the request after returning stale output",
      caseResults: {
        D: {
          displacements: { N2: { ux: 0.01, uy: 0, uz: 0 } },
        },
      },
    },
    messages: [{ name: "run_analysis", content: "failed" }],
  }, async () => {
    judgeCalls += 1;
    return { pass: true, reason: "should not be reached" };
  });

  assert.equal(result.pass, false);
  assert.equal(judgeCalls, 0);
});

test("safe non-execution rejects an irrelevant pre-analysis question", async () => {
  let judgeCalls = 0;
  const result = await evaluateSafeNonExecutionEvidence({
    messages: [{
      role: "assistant",
      content: "",
      tool_calls: [{
        name: "ask_user_clarification",
        args: { question: "Would you like a blue report cover?" },
      }],
    }],
  }, async () => {
    judgeCalls += 1;
    return { pass: false, reason: "the question is unrelated to engineering input" };
  });

  assert.equal(judgeCalls, 1);
  assert.equal(result.pass, false);
});

test("should-not-analyze detects a serialized analysis tool invocation without a tool result", async () => {
  const result = await evaluateScenario(
    scenario([{ type: "should_not_analyze" }]),
    {
      messages: [{
        id: ["langchain_core", "messages", "AIMessage"],
        kwargs: {
          content: "",
          tool_calls: [{ function: { name: "run_analysis" } }],
        },
      }],
    },
  );

  assert.equal(result.allPassed, false);
  assert.match(
    result.metrics.find((metric) => metric.metric === "should_not_analyze").actual,
    /run_analysis called/,
  );
});
