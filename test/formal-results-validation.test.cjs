const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const {
  expectedBatches,
  validateRecords,
} = require("../scripts/aggregate-formal-results.cjs");

const matrix = JSON.parse(fs.readFileSync(
  path.join(__dirname, "..", "experiments", "formal-matrix.json"),
  "utf8",
));

function formalRecord(batch, index) {
  return {
    file: `batch-${index}.json`,
    record: {
      run: {
        repeatId: batch.repeatId,
        selection: { mode: batch.mode },
        models: {
          primary: { configId: batch.modelId },
          vision: batch.visionModelId ? { configId: batch.visionModelId } : null,
          judge: { configId: matrix.judgeModel },
        },
        revisions: {
          structureclaw: { revision: "sut-commit", dirty: false },
          benchmark: { revision: "bench-commit", dirty: false },
        },
        protocol: {
          formalJobId: [
            `r${batch.repeatId}`,
            batch.family,
            batch.mode,
            batch.configurationId || batch.modelId,
          ].map((value) => String(value).toLowerCase()).join("__"),
          formalMatrixSha256: "matrix-hash",
        },
        fingerprints: {
          scenarioHash: `scenarios-${batch.family}`,
          scenarioOrderHash: `order-${batch.family}-${index}`,
          attachmentHash: `attachments-${batch.family}`,
          promptAndToolHash: "prompt-and-tool",
          evaluationHash: "evaluation",
          runtimeConfigHash: `runtime-${index}`,
        },
        validity: { paperEligible: true },
      },
      scenarios: Array.from({ length: batch.scenarioCount }, (_, scenarioIndex) => ({
        scenarioId: `${batch.taskFamily}-${scenarioIndex}-${batch.mode}`,
        baseScenarioId: `${batch.taskFamily}-${scenarioIndex}`,
        taskFamily: batch.taskFamily,
        mode: batch.mode,
        allPassed: true,
        metrics: [],
      })),
    },
  };
}

test("formal result validation accepts exactly the declared 108 batches and 5,400 runs", () => {
  const records = expectedBatches(matrix).map(formalRecord);
  const validation = validateRecords(records, matrix);

  assert.deepEqual(validation.errors, []);
  assert.equal(records.length, 108);
  assert.equal(validation.rows.length, 5400);
});

test("formal result validation rejects a duplicated condition replacing a missing condition", () => {
  const batches = expectedBatches(matrix);
  const records = batches.map(formalRecord);
  records[1] = formalRecord(batches[0], 1);

  const validation = validateRecords(records, matrix);

  assert.ok(validation.errors.some((error) => error.includes("duplicate formal batch")));
  assert.ok(validation.errors.some((error) => error.includes("missing formal batch")));
  assert.equal(validation.rows.length, 5400);
});

test("formal result validation rejects dirty or inconsistent frozen revisions", () => {
  const records = expectedBatches(matrix).map(formalRecord);
  records[0].record.run.revisions.benchmark.dirty = true;
  records[1].record.run.revisions.structureclaw.revision = "different-commit";

  const validation = validateRecords(records, matrix);

  assert.ok(validation.errors.some((error) => error.includes("benchmark revision is dirty")));
  assert.ok(validation.errors.some((error) => error.includes("inconsistent structureclaw revision")));
});
