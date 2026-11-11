"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { createHash } = require("node:crypto");
const { NativeJobClient, buildEnvelope, validateEnvelope, inspectEnvelope, manifestSha256,
  canonicalJson, validateCollection, collectEvidence, verifyEvidenceDirectory, INPUT_LIMIT_BYTES,
  ARTIFACT_LIMIT_BYTES, REMOTE_COMMAND } = require("./native-job.cjs");

const sha = (bytes) => createHash("sha256").update(bytes).digest("hex");
const model = () => ({ format: "native-numeric-v1", tables: {
  nodes: [[1, 0, 0, 0], [2, 0, 0, 3]], elements: [[1, 1, 2]], settings: [[true, false, null, 1e-8]],
} });
const clone = (value) => JSON.parse(JSON.stringify(value));
const envelope = () => buildEnvelope({ engine: "OpenSees", model: model() });

function temporary(t) {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "native-client-test-"));
  t.after(() => fs.rmSync(directory, { recursive: true, force: true }));
  return directory;
}

function sampleCollection({ state = "succeeded", extra = {} } = {}) {
  const payload = envelope();
  const files = { "model.json": Buffer.from(payload.files[0].contentBase64, "base64"),
    "stdout.log": Buffer.from("synthetic worker completed\n"), "stderr.log": Buffer.alloc(0),
    ...(state === "succeeded" ? { "result.json": Buffer.from('{"synthetic":true,"displacement":-0.0001}') } : {}), ...extra };
  const artifacts = Object.entries(files).map(([name, bytes]) => ({ path: name, size: bytes.length,
    sha256: sha(bytes), contentBase64: bytes.toString("base64") }));
  const expected = { jobId: "0123456789abcdef0123456789abcdef", engine: payload.engine,
    modelSha256: payload.modelSha256, manifestSha256: manifestSha256(payload) };
  const receipt = { schemaVersion: 1, ...expected, state, executed: true,
    exitCode: state === "succeeded" ? 0 : state === "cancelled" ? null : 1,
    executableSha256: "a".repeat(64), artifacts: artifacts.map(({ contentBase64, ...metadata }) => metadata),
    nativeTruthStatus: "pending-independent-review" };
  return { expected, collection: { receipt, receiptSha256: sha(canonicalJson(receipt)), artifacts } };
}

function rehash(collection) {
  collection.receiptSha256 = sha(canonicalJson(collection.receipt));
  return collection;
}

test("numeric envelope is deterministic and inspection never returns model contents", () => {
  const first = envelope();
  const second = buildEnvelope({ engine: "OpenSees", model: { tables: model().tables, format: "native-numeric-v1" } });
  assert.deepEqual(first, second);
  assert.equal(validateEnvelope(first).tables.nodes.length, 2);
  const inspection = inspectEnvelope(first);
  assert.equal(inspection.tables.nodes.rows, 2);
  assert.equal(inspection.manifestSha256, manifestSha256(first));
  assert.equal(JSON.stringify(inspection).includes("contentBase64"), false);
  assert.equal(JSON.stringify(inspection).includes("native-numeric-v1"), false);
  const { contentBase64, ...metadata } = first.files[0];
  assert.equal(inspection.manifestSha256, sha(canonicalJson({ ...first, files: [metadata] })));
});

test("numeric model rejects text, objects, hidden metadata, malformed values, and unsupported engines", () => {
  for (const value of ["prompt", { answer: 42 }, undefined, NaN, Infinity, -Infinity, 1e101, () => 1, 1n]) {
    const input = model();
    input.tables.nodes.push(value);
    assert.throws(() => buildEnvelope({ engine: "OpenSees", model: input }), /numeric|finite/);
  }
  for (const input of [
    { ...model(), prompt: "not transferable" },
    { format: "native-numeric-v1", tables: { nodes: [], elements: [] } },
    { format: "native-numeric-v1", tables: { ...model().tables, answers: [] } },
    { format: "native-numeric-v1", tables: { ...model().tables, nodes: {} } },
  ]) assert.throws(() => buildEnvelope({ engine: "OpenSees", model: input }));
  for (const engine of ["opensees", "shell", "YJK; pwd", null]) assert.throws(() => buildEnvelope({ engine, model: model() }), /engine/);
  assert.throws(() => buildEnvelope({ engine: "OpenSees", model: '{"format":"bad","format":"native-numeric-v1","tables":{"nodes":[],"elements":[],"settings":[]}}' }), /duplicate/);
  assert.throws(() => buildEnvelope({ engine: "OpenSees", model: Buffer.from([0xff]) }), /UTF-8/);
  assert.throws(() => buildEnvelope({ engine: "OpenSees", model: Buffer.alloc(INPUT_LIMIT_BYTES + 1) }), /size limit/);
  const sparse = model();
  sparse.tables.nodes = new Array(2);
  assert.throws(() => buildEnvelope({ engine: "OpenSees", model: sparse }), /dense/);
  const nested = model();
  nested.tables.nodes = 1;
  for (let depth = 0; depth < 34; depth += 1) nested.tables.nodes = [nested.tables.nodes];
  assert.throws(() => buildEnvelope({ engine: "OpenSees", model: nested }), /depth/);
});

test("envelope binds exact path, byte size, canonical base64, and both content hashes", () => {
  for (const change of [
    (item) => { item.files[0].path = "../model.json"; },
    (item) => { item.files[0].size += 1; },
    (item) => { item.files[0].contentBase64 += "\n"; },
    (item) => { item.files[0].sha256 = "b".repeat(64); },
    (item) => { item.modelSha256 = "c".repeat(64); },
    (item) => { item.files.push(item.files[0]); },
    (item) => { item.files.toJSON = () => ["hidden instructions"]; },
    (item) => { item.secret = "hidden"; },
  ]) {
    const input = envelope();
    change(input);
    assert.throws(() => validateEnvelope(input));
  }
  const input = envelope();
  const bytes = Buffer.from('{"format":"native-numeric-v1","tables":{"nodes":[],"elements":[],"settings":[],"settings":[]}}');
  Object.assign(input.files[0], { sha256: sha(bytes), size: bytes.length, contentBase64: bytes.toString("base64") });
  input.modelSha256 = sha(bytes);
  assert.throws(() => validateEnvelope(input), /duplicate/);
});

test("collection checks explicit engine, job, model, manifest, and immutable review status", () => {
  const { collection, expected } = sampleCollection();
  assert.equal(validateCollection(collection, expected).decoded.get("model.json").length, collection.artifacts[0].size);
  for (const [key, value] of Object.entries({ jobId: "f".repeat(32), engine: "YJK", modelSha256: "e".repeat(64), manifestSha256: "d".repeat(64) })) {
    assert.throws(() => validateCollection(collection, { ...expected, [key]: value }), /expected job/);
  }
  assert.throws(() => validateCollection(collection), /plain object/);
  const falsePass = clone(collection);
  falsePass.receipt.nativeTruthStatus = "passed";
  assert.throws(() => validateCollection(rehash(falsePass), expected), /independent review/);
  for (const change of [(r) => { r.executed = false; }, (r) => { r.exitCode = 1; }, (r) => { r.executableSha256 = null; }]) {
    const invalid = clone(collection);
    change(invalid.receipt);
    assert.throws(() => validateCollection(rehash(invalid), expected));
  }
});

test("collection rejects tampering, missing and duplicate files, path traversal, and oversized artifacts", () => {
  const { collection, expected } = sampleCollection();
  for (const change of [
    (c) => { c.artifacts[1].contentBase64 = Buffer.from("tampered").toString("base64"); },
    (c) => { c.receiptSha256 = "f".repeat(64); },
    (c) => { c.artifacts.pop(); },
    (c) => { c.artifacts[1] = clone(c.artifacts[0]); },
    (c) => { c.receipt.artifacts[0].path = "../model.json"; rehash(c); },
    (c) => { c.receipt.artifacts.push(clone(c.receipt.artifacts[0])); rehash(c); },
    (c) => { c.receipt.artifacts[1].size = ARTIFACT_LIMIT_BYTES; rehash(c); },
    (c) => { c.receipt.artifacts = c.receipt.artifacts.filter((a) => a.path !== "result.json"); c.artifacts = c.artifacts.filter((a) => a.path !== "result.json"); rehash(c); },
  ]) {
    const invalid = clone(collection);
    change(invalid);
    assert.throws(() => validateCollection(invalid, expected));
  }
  const forged = clone(collection);
  forged.receipt.manifestSha256 = "9".repeat(64);
  rehash(forged);
  assert.throws(() => validateCollection(forged, { ...expected, manifestSha256: "9".repeat(64) }), /expected manifest/);
});

test("optional native input, output, settings and version are retained without granting acceptance", () => {
  const { collection, expected } = sampleCollection({ extra: {
    "native-input.dat": Buffer.from("synthetic native input"), "native-output.dat": Buffer.from("synthetic native output"),
    "settings.json": Buffer.from("{}"), "solver-version.json": Buffer.from('{"version":"synthetic"}'),
  } });
  const result = validateCollection(collection, expected);
  assert.equal(result.decoded.size, 8);
  assert.equal(result.receipt.nativeTruthStatus, "pending-independent-review");
});

test("collector publishes private verified evidence and only then acknowledges cleanup", async (t) => {
  const root = temporary(t);
  const destination = path.join(root, "evidence");
  const { collection, expected } = sampleCollection();
  let cleaned = false;
  const client = {
    async collect(jobId) { assert.equal(jobId, expected.jobId); return collection; },
    async cleanup(jobId, receiptHash) {
      assert.equal(jobId, expected.jobId);
      assert.equal(receiptHash, collection.receiptSha256);
      assert.equal(verifyEvidenceDirectory(destination, expected).receiptSha256, receiptHash);
      cleaned = true;
      return { jobId, cleaned: true };
    },
  };
  const result = await collectEvidence({ client, jobId: expected.jobId, expected, destination, cleanup: true });
  assert.equal(cleaned, true);
  assert.equal(result.nativeTruthStatus, "pending-independent-review");
  assert.equal(fs.statSync(destination).mode & 0o777, 0o700);
  for (const name of fs.readdirSync(destination)) assert.equal(fs.statSync(path.join(destination, name)).mode & 0o777, 0o600);
  fs.appendFileSync(path.join(destination, "stdout.log"), "changed");
  assert.throws(() => verifyEvidenceDirectory(destination, expected), /mismatch/);
});

test("stale evidence never creates a destination or sends cleanup", async (t) => {
  const root = temporary(t);
  const { collection, expected } = sampleCollection();
  const destination = path.join(root, "stale");
  let cleanupCalls = 0;
  const client = { async collect() { return collection; }, async cleanup() { cleanupCalls += 1; } };
  await assert.rejects(collectEvidence({ client, jobId: expected.jobId, expected: { ...expected, engine: "PKPM" }, destination, cleanup: true }), /expected job/);
  assert.equal(fs.existsSync(destination), false);
  assert.equal(cleanupCalls, 0);
});

test("collector refuses existing destinations, symlink ancestors, and later artifact symlinks", async (t) => {
  const root = temporary(t);
  const { collection, expected } = sampleCollection();
  const client = { async collect() { return collection; } };
  const existing = path.join(root, "existing");
  fs.mkdirSync(existing);
  await assert.rejects(collectEvidence({ client, jobId: expected.jobId, expected, destination: existing }), /already exists/);
  const link = path.join(root, "linked");
  fs.symlinkSync(existing, link, "dir");
  await assert.rejects(collectEvidence({ client, jobId: expected.jobId, expected, destination: path.join(link, "new") }), /symlink/);
  const destination = path.join(root, "safe");
  await collectEvidence({ client, jobId: expected.jobId, expected, destination });
  fs.unlinkSync(path.join(destination, "stdout.log"));
  fs.symlinkSync(path.join(destination, "stderr.log"), path.join(destination, "stdout.log"));
  assert.throws(() => verifyEvidenceDirectory(destination, expected), /regular/);
});

test("cleanup failure preserves verified evidence and identifies its path", async (t) => {
  const root = temporary(t);
  const { collection, expected } = sampleCollection();
  const destination = path.join(root, "evidence");
  const client = { async collect() { return collection; }, async cleanup() { throw new Error("cleanup denied"); } };
  await assert.rejects(collectEvidence({ client, jobId: expected.jobId, expected, destination, cleanup: true }), (error) => error.message === "cleanup denied" && error.evidenceDirectory === destination);
  assert.equal(verifyEvidenceDirectory(destination, expected).receiptSha256, collection.receiptSha256);
});

test("artifact changed at publication is detected before cleanup", async (t) => {
  const root = temporary(t);
  const { collection, expected } = sampleCollection();
  const destination = path.join(root, "evidence");
  let cleanups = 0;
  const client = { async collect() { return collection; }, async cleanup() { cleanups += 1; } };
  const rename = fs.renameSync;
  t.mock.method(fs, "renameSync", (source, target) => {
    rename(source, target);
    fs.appendFileSync(path.join(target, "stdout.log"), "tampered during publication");
  });
  await assert.rejects(collectEvidence({ client, jobId: expected.jobId, expected, destination, cleanup: true }), /mismatch/);
  assert.equal(cleanups, 0);
  assert.equal(fs.existsSync(destination), true);
});

test("default remote transport is inspection-only and its command cannot be supplied by callers", async () => {
  const client = new NativeJobClient({ remoteCommand: "unexpected command" });
  const result = await client.submit(envelope());
  assert.equal(result.dryRun, true);
  assert.equal(client._process, null);
  assert.equal(result.transport.routeVerified, false);
  assert.equal(result.transport.args.at(-1), REMOTE_COMMAND);
  assert.equal(JSON.stringify(result).includes("contentBase64"), false);
  assert.throws(() => new NativeJobClient({ dryRun: false }), /allowRemote/);
  await client.close();
});

function fakeBroker(t, behavior = "normal") {
  const directory = temporary(t);
  const fixture = path.join(directory, "fixture.py");
  const data = sampleCollection();
  fs.writeFileSync(path.join(directory, "collection.json"), JSON.stringify(data.collection));
  fs.writeFileSync(fixture, `
import hashlib, json, os, pathlib, sys
root = pathlib.Path(sys.argv[sys.argv.index('--root') + 1])
collection = json.loads((root / 'collection.json').read_text())
status = {**collection['receipt'], 'processId': os.getpid()}
behavior = ${JSON.stringify(behavior)}
for line in sys.stdin:
    request = json.loads(line)
    with (root / 'requests.jsonl').open('a') as log:
        log.write(line)
    if behavior == 'timeout':
        continue
    if behavior == 'malformed':
        print('not-json', flush=True)
        continue
    if behavior == 'wrong-id':
        request['requestId'] += 10
    if behavior == 'wrong-engine':
        status['engine'] = 'YJK'
    if behavior == 'stale-status' and request['op'] == 'status':
        status['engine'] = 'YJK'
    if behavior == 'stale-collection' and request['op'] == 'collect':
        collection['receipt']['engine'] = 'YJK'
        payload = json.loads((root / 'requests.jsonl').read_text().splitlines()[0])['payload']
        payload['engine'] = 'YJK'
        payload['files'] = [{key: value for key, value in item.items() if key != 'contentBase64'} for item in payload['files']]
        collection['receipt']['manifestSha256'] = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        collection['receiptSha256'] = hashlib.sha256(json.dumps(collection['receipt'], sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    result = collection if request['op'] == 'collect' else {'jobId': request['jobId'], 'cleaned': True} if request['op'] == 'cleanup' else status
    response = {'schemaVersion': 1, 'requestId': request['requestId'], 'ok': False, 'error': {'code': 'fixture-error', 'message': 'Cancellation fixture failure'}} if request['op'] == 'cancel' else {'schemaVersion': 1, 'requestId': request['requestId'], 'ok': True, 'result': result}
    data = json.dumps(response) + '\\n'
    sys.stdout.write(data[:13])
    sys.stdout.flush()
    sys.stdout.write(data[13:])
    sys.stdout.flush()
`);
  const client = new NativeJobClient({ transport: "local", dryRun: false,
    workerPath: fixture, root: directory, registry: path.join(directory, "unused.json"), requestTimeoutMs: behavior === "timeout" ? 150 : 3000 });
  t.after(() => client.close());
  return { directory, client, ...data };
}

test("local transport retains one JSON-lines process, matches request ids, and surfaces structured errors", async (t) => {
  const { directory, client, expected } = fakeBroker(t);
  const submitted = await client.submit(envelope());
  const [first, second] = await Promise.all([client.status(expected.jobId), client.status(expected.jobId)]);
  assert.equal(first.processId, submitted.processId);
  assert.equal(first.processId, second.processId);
  await assert.rejects(client.cancel(expected.jobId), { code: "fixture-error" });
  assert.equal((await client.status(expected.jobId)).processId, first.processId);
  const output = await collectEvidence({ client, jobId: expected.jobId, expected, destination: path.join(directory, "downloaded"), cleanup: true });
  assert.equal(output.cleanupResult.cleaned, true);
  const requests = fs.readFileSync(path.join(directory, "requests.jsonl"), "utf8").trim().split("\n").map(JSON.parse);
  assert.deepEqual(requests.map((request) => request.requestId), [1, 2, 3, 4, 5, 6, 7]);
  assert.deepEqual(requests.map((request) => request.op), ["submit", "status", "status", "cancel", "status", "collect", "cleanup"]);
  assert.deepEqual(Object.keys(requests[0]).sort(), ["schemaVersion", "requestId", "op", "payload"].sort());
  await client.close();
  await assert.rejects(client.status(expected.jobId), { code: "client-closed" });
});

for (const behavior of ["malformed", "wrong-id", "wrong-engine", "timeout"]) {
  test(`local transport rejects ${behavior} broker responses`, async (t) => {
    const { client } = fakeBroker(t, behavior);
    const expectedCode = { malformed: "invalid-native-data", "wrong-id": "broker-protocol-error", "wrong-engine": "stale-native-evidence", timeout: "broker-timeout" }[behavior];
    await assert.rejects(client.submit(envelope()), { code: expectedCode });
    assert.notEqual(client._failure, null);
  });
}

for (const operation of ["status", "collect"]) {
  test(`same-session ${operation} rejects a different engine despite a self-consistent response`, async (t) => {
    const { client } = fakeBroker(t, operation === "status" ? "stale-status" : "stale-collection");
    const submitted = await client.submit(envelope());
    await assert.rejects(client[operation](submitted.jobId), { code: "stale-native-evidence" });
  });
}

test("explicit local dry-run never launches its configured executable or writes collection output", async (t) => {
  const root = temporary(t);
  const client = new NativeJobClient({ transport: "local", python: path.join(root, "does-not-exist"), workerPath: "worker.py", root, registry: "registry.json" });
  assert.equal((await client.submit(envelope())).dryRun, true);
  const { expected } = sampleCollection();
  const destination = path.join(root, "output");
  assert.equal((await collectEvidence({ client, jobId: expected.jobId, expected, destination, cleanup: true })).dryRun, true);
  assert.equal(fs.existsSync(destination), false);
  assert.equal(client._process, null);
  await client.close();
});

test("real Python broker and JS client agree on hashes, lifecycle, evidence and cleanup", { skip: process.platform === "win32" }, async (t) => {
  const directory = temporary(t);
  const jobs = path.join(directory, "jobs");
  const driver = path.join(directory, "native-opensees-worker");
  // This harmless synthetic process exercises transport only, never a solver.
  const bytes = Buffer.from(`#!/usr/bin/env python3
import json, pathlib, time
model = json.loads(pathlib.Path('model.json').read_text())
settings = model['tables']['settings']
if settings and isinstance(settings[0], (int, float)):
    time.sleep(settings[0])
pathlib.Path('result.json').write_text(json.dumps({'syntheticTransportFixture': True, 'nodeCount': len(model['tables']['nodes'])}))
print('synthetic transport fixture', flush=True)
`);
  fs.writeFileSync(driver, bytes, { mode: 0o700 });
  const driverHash = sha(bytes);
  const lease = path.join(directory, "lease.json");
  fs.writeFileSync(lease, JSON.stringify({ schemaVersion: 1, engine: "OpenSees", executableSha256: driverHash,
    isolated: true, expiresAt: Date.now() / 1000 + 120 }));
  const registry = path.join(directory, "registry.json");
  fs.writeFileSync(registry, JSON.stringify({ schemaVersion: 1, engines: { OpenSees: {
    enabled: true, executable: driver, sha256: driverHash, independentCompilerReviewed: true,
    isolationVerified: true, isolationLease: lease,
  } } }));
  const client = new NativeJobClient({ transport: "local", dryRun: false,
    workerPath: path.resolve(__dirname, "../scripts/research300/native_worker.py"), root: jobs, registry });
  t.after(() => client.close());
  const input = envelope();
  const submitted = await client.submit(input);
  const expected = { jobId: submitted.jobId, engine: input.engine,
    modelSha256: input.modelSha256, manifestSha256: manifestSha256(input) };
  let status = submitted;
  const deadline = Date.now() + 5000;
  while (status.state === "running" && Date.now() < deadline) {
    await new Promise((resolve) => setTimeout(resolve, 10));
    status = await client.status(submitted.jobId);
  }
  assert.equal(status.state, "succeeded");
  const destination = path.join(directory, "collected");
  const result = await collectEvidence({ client, jobId: submitted.jobId, expected, destination, cleanup: true });
  assert.equal(result.receipt.executableSha256, driverHash);
  assert.equal(result.receipt.nativeTruthStatus, "pending-independent-review");
  assert.equal(result.cleanupResult.cleaned, true);
  assert.deepEqual(JSON.parse(fs.readFileSync(path.join(destination, "result.json"))), { syntheticTransportFixture: true, nodeCount: 2 });
  assert.equal(fs.existsSync(path.join(jobs, submitted.jobId)), false);
  await assert.rejects(client.status(submitted.jobId), { code: "not-found" });
  const delayed = model();
  delayed.tables.settings = [5];
  const second = await client.submit(buildEnvelope({ engine: "OpenSees", model: delayed }));
  assert.notEqual(second.jobId, submitted.jobId);
  assert.equal((await client.cancel(second.jobId)).state, "cancelled");
  assert.equal((await client.collect(second.jobId)).receipt.state, "cancelled");
  await client.close();
});
