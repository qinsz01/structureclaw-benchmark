const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawn } = require("node:child_process");

const { installSolverGate } = require("../lib/solver-gate.cjs");

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function serviceWithClient(client) {
  return { engineClient: client };
}

function runLockChild(modulePath, lockRoot, group, holdMs, outputPath) {
  const script = [
    `const { acquireDirectoryLock } = require(${JSON.stringify(modulePath)});`,
    "(async () => {",
    "  const lock = await acquireDirectoryLock({",
    `    lockRoot: ${JSON.stringify(lockRoot)},`,
    `    group: ${JSON.stringify(group)},`,
    "    pollMs: 5,",
    "    timeoutMs: 5000,",
    "  });",
    "  const acquiredAt = Date.now();",
    `  await new Promise((resolve) => setTimeout(resolve, ${holdMs}));`,
    "  const releasedAt = Date.now();",
    "  lock.release();",
    `  require("node:fs").writeFileSync(${JSON.stringify(outputPath)}, JSON.stringify({ acquiredAt, releasedAt, queueWaitMs: lock.queueWaitMs }));`,
    "})().catch((error) => { console.error(error); process.exit(1); });",
  ].join("\n");
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, ["-e", script], {
      stdio: ["ignore", "ignore", "pipe"],
      windowsHide: true,
    });
    let stderr = "";
    child.stderr.on("data", (chunk) => {
      stderr += chunk;
    });
    child.on("error", reject);
    child.on("exit", (code) => {
      if (code !== 0) {
        reject(new Error(`lock child failed (${code}): ${stderr}`));
        return;
      }
      resolve();
    });
  });
}

test("serializes the same solver across independent benchmark processes", async () => {
  const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), "structureclaw-solver-process-"));
  const lockRoot = path.join(tempRoot, "locks");
  const modulePath = path.join(__dirname, "..", "lib", "solver-gate.cjs");
  const firstOutput = path.join(tempRoot, "first.json");
  const secondOutput = path.join(tempRoot, "second.json");
  try {
    await Promise.all([
      runLockChild(modulePath, lockRoot, "builtin-yjk", 150, firstOutput),
      runLockChild(modulePath, lockRoot, "builtin-yjk", 150, secondOutput),
    ]);
    const intervals = [firstOutput, secondOutput]
      .map((file) => JSON.parse(fs.readFileSync(file, "utf8")))
      .sort((left, right) => left.acquiredAt - right.acquiredAt);

    assert.ok(intervals[1].acquiredAt >= intervals[0].releasedAt);
    assert.ok(intervals.some((interval) => interval.queueWaitMs >= 100));
  } finally {
    fs.rmSync(tempRoot, { recursive: true, force: true });
  }
});

test("serializes concurrent analysis calls for the same engine", async () => {
  const lockRoot = fs.mkdtempSync(path.join(os.tmpdir(), "structureclaw-solver-gate-"));
  let active = 0;
  let maxActive = 0;
  const client = {
    async get() {
      return { data: null };
    },
    async post() {
      active += 1;
      maxActive = Math.max(maxActive, active);
      await delay(80);
      active -= 1;
      return { data: { success: true } };
    },
  };
  const firstService = serviceWithClient(client);
  const secondService = serviceWithClient(client);
  const firstGate = installSolverGate(firstService, {
    mode: "per-engine", lockRoot, pollMs: 5, yjkCooldownMs: 1,
  });
  const secondGate = installSolverGate(secondService, {
    mode: "per-engine", lockRoot, pollMs: 5, yjkCooldownMs: 1,
  });
  try {
    await Promise.all([
      firstService.engineClient.post("/analyze", { engineId: "builtin-yjk" }),
      secondService.engineClient.post("/analyze", { engineId: "builtin-yjk" }),
    ]);
    assert.equal(maxActive, 1);
    const events = [...firstGate.snapshot(), ...secondGate.snapshot()];
    assert.equal(events.length, 2);
    assert.ok(events.some((event) => event.queueWaitMs >= 50));
    assert.ok(events.every((event) => event.success));
    assert.ok(events.every((event) => event.cooldownMs >= 1));
  } finally {
    firstGate.restore();
    secondGate.restore();
    fs.rmSync(lockRoot, { recursive: true, force: true });
  }
});

test("allows different engines to execute concurrently in per-engine mode", async () => {
  const lockRoot = fs.mkdtempSync(path.join(os.tmpdir(), "structureclaw-solver-engines-"));
  let active = 0;
  let maxActive = 0;
  const client = {
    async get() {
      return { data: null };
    },
    async post() {
      active += 1;
      maxActive = Math.max(maxActive, active);
      await delay(60);
      active -= 1;
      return { data: { success: true } };
    },
  };
  const firstService = serviceWithClient(client);
  const secondService = serviceWithClient(client);
  const firstGate = installSolverGate(firstService, {
    mode: "per-engine", lockRoot, pollMs: 5, yjkCooldownMs: 1,
  });
  const secondGate = installSolverGate(secondService, {
    mode: "per-engine", lockRoot, pollMs: 5, yjkCooldownMs: 1,
  });
  try {
    await Promise.all([
      firstService.engineClient.post("/analyze", { engineId: "builtin-yjk" }),
      secondService.engineClient.post("/analyze", { engineId: "builtin-opensees" }),
    ]);
    assert.equal(maxActive, 2);
  } finally {
    firstGate.restore();
    secondGate.restore();
    fs.rmSync(lockRoot, { recursive: true, force: true });
  }
});

test("global mode serializes different engines", async () => {
  const lockRoot = fs.mkdtempSync(path.join(os.tmpdir(), "structureclaw-solver-global-"));
  let active = 0;
  let maxActive = 0;
  const client = {
    async get() {
      return { data: null };
    },
    async post() {
      active += 1;
      maxActive = Math.max(maxActive, active);
      await delay(50);
      active -= 1;
      return { data: { success: true } };
    },
  };
  const firstService = serviceWithClient(client);
  const secondService = serviceWithClient(client);
  const firstGate = installSolverGate(firstService, {
    mode: "global", lockRoot, pollMs: 5, yjkCooldownMs: 1,
  });
  const secondGate = installSolverGate(secondService, {
    mode: "global", lockRoot, pollMs: 5, yjkCooldownMs: 1,
  });
  try {
    await Promise.all([
      firstService.engineClient.post("/analyze", { engineId: "builtin-pkpm" }),
      secondService.engineClient.post("/analyze", { engineId: "builtin-opensees" }),
    ]);
    assert.equal(maxActive, 1);
  } finally {
    firstGate.restore();
    secondGate.restore();
    fs.rmSync(lockRoot, { recursive: true, force: true });
  }
});
