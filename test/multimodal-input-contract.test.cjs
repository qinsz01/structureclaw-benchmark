const assert = require("node:assert/strict");
const test = require("node:test");

const {
  attachVisionSummariesToMessage,
  buildVisionPrompt,
} = require("../runner.cjs");

test("vision prompt receives neither the user task nor attachment identity", () => {
  const prompt = buildVisionPrompt("en");

  assert.match(prompt, /Extract only information visible in the image/);
  assert.doesNotMatch(prompt, /User task|Attachment|5m|drawing-001/i);
});

test("agent input keeps image evidence, engineering specification, and task in separate sections", () => {
  const message = attachVisionSummariesToMessage(
    "Build and analyze the model.",
    [{
      imageIndex: 1,
      model: "vision-model-not-for-agent",
      attachmentName: "semantic-file-name.png",
      summary: '{"geometry":["5 m + 6 m"]}',
    }],
    "en",
    "Material Q345; section B1.",
  );

  assert.match(message, /\[Benchmark vision attachment summaries\]/);
  assert.match(message, /\[Engineering specification\]\nMaterial Q345; section B1\./);
  assert.match(message, /\[User task\]\nBuild and analyze the model\./);
  assert.doesNotMatch(message, /vision-model-not-for-agent|semantic-file-name/);
});

test("non-image tasks retain their original message", () => {
  assert.equal(
    attachVisionSummariesToMessage("Original task", [], "en", ""),
    "Original task",
  );
});
