"use strict";

// This boundary deliberately knows no solver semantics. Only numeric tables may
// cross it; native receipts still require independent engineering review.
const fs = require("node:fs");
const path = require("node:path");
const { createHash } = require("node:crypto");
const { spawn } = require("node:child_process");
const { TextDecoder } = require("node:util");

const INPUT_LIMIT_BYTES = 8 * 1024 * 1024;
const ARTIFACT_LIMIT_BYTES = 32 * 1024 * 1024;
const MAX_RESPONSE_BYTES = Math.ceil(ARTIFACT_LIMIT_BYTES / 3) * 4 + 1024 * 1024;
const ENGINES = new Set(["OpenSees", "YJK", "PKPM"]);
const STATES = new Set(["running", "succeeded", "failed", "cancelled", "resource-busy"]);
const TABLES = new Set(["nodes", "elements", "materials", "sections", "supports", "loads", "loadCases", "loadCombinations", "settings", "outputRequests"]);
const ARTIFACT_NAMES = new Set(["model.json", "result.json", "stdout.log", "stderr.log", "native-input.dat", "native-output.dat", "settings.json", "solver-version.json"]);
const HASH = /^[a-f0-9]{64}$/;
const JOB_ID = /^[a-f0-9]{32}$/;
const REMOTE_COMMAND = "python G:/StructureClaw-NativeJobs/native_worker.py serve --root G:/StructureClaw-NativeJobs/jobs --registry G:/StructureClaw-NativeJobs/registry.json";
// Host details stay out of version control: set SCLAW_NATIVE_SSH_TARGET (and the optional
// SCLAW_NATIVE_SSH_JUMP) or keep them in the git-ignored native-host.local.json.
function localNativeHost() {
  try {
    return JSON.parse(fs.readFileSync(path.join(__dirname, "..", "native-host.local.json"), "utf8"));
  } catch {
    return {};
  }
}
const NATIVE_HOST = localNativeHost();
const SSH_TARGET = process.env.SCLAW_NATIVE_SSH_TARGET || NATIVE_HOST.sshTarget || "sclaw-native-worker";
const SSH_JUMP = process.env.SCLAW_NATIVE_SSH_JUMP || NATIVE_HOST.sshJump;
const SSH_ARGS = Object.freeze(["-o", "BatchMode=yes", "-T", ...(SSH_JUMP ? ["-J", SSH_JUMP] : []), SSH_TARGET, REMOTE_COMMAND]);

function fail(message, code = "invalid-native-data") {
  const error = new Error(message);
  error.code = code;
  throw error;
}

function object(value, label) {
  if (!value || typeof value !== "object" || Array.isArray(value) ||
      ![Object.prototype, null].includes(Object.getPrototypeOf(value))) fail(`${label} must be a plain object`);
  for (const key of Reflect.ownKeys(value)) {
    const descriptor = Object.getOwnPropertyDescriptor(value, key);
    if (typeof key !== "string" || !descriptor.enumerable || !Object.hasOwn(descriptor, "value")) fail(`${label} must contain JSON data properties only`);
  }
}

function exactKeys(value, keys, label) {
  object(value, label);
  const actual = Object.keys(value).sort();
  const wanted = [...keys].sort();
  if (actual.length !== wanted.length || actual.some((key, index) => key !== wanted[index])) fail(`${label} has unexpected or missing keys`);
}

function denseArray(value, label) {
  if (!Array.isArray(value) || Object.getPrototypeOf(value) !== Array.prototype || Reflect.ownKeys(value).length !== value.length + 1) fail(`${label} must be a dense JSON array`);
  for (let index = 0; index < value.length; index += 1) {
    const descriptor = Object.getOwnPropertyDescriptor(value, String(index));
    if (!descriptor || !descriptor.enumerable || !Object.hasOwn(descriptor, "value")) fail(`${label} must contain data values only`);
  }
}

function hash(value) {
  return createHash("sha256").update(value).digest("hex");
}

function canonicalJson(value) {
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(",")}]`;
  if (value && typeof value === "object") return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonicalJson(value[key])}`).join(",")}}`;
  return JSON.stringify(value);
}

function requireHash(value, label) {
  if (typeof value !== "string" || !HASH.test(value)) fail(`${label} must be a lowercase SHA256`);
}

function requireJobId(value) {
  if (typeof value !== "string" || !JOB_ID.test(value)) fail("jobId must be 32 lowercase hexadecimal characters");
}

function requireEngine(value) {
  if (!ENGINES.has(value)) fail("engine must be OpenSees, YJK, or PKPM");
}

// JSON.parse alone silently accepts duplicate keys. Scan its already-valid
// lexical structure so a later parser cannot interpret a different manifest.
function parseStrictJson(bytes, label) {
  let text;
  let parsed;
  try {
    text = new TextDecoder("utf-8", { fatal: true, ignoreBOM: true }).decode(bytes);
    parsed = JSON.parse(text);
  } catch {
    fail(`${label} must be valid UTF-8 JSON`);
  }
  const containers = [];
  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
    if (char === "{") containers.push(new Set());
    else if (char === "[") containers.push(null);
    else if (char === "}" || char === "]") containers.pop();
    else if (char === '"') {
      const start = index;
      index += 1;
      while (text[index] !== '"') {
        if (text[index] === "\\") index += 1;
        index += 1;
      }
      let next = index + 1;
      while (/\s/.test(text[next] || "x")) next += 1;
      if (text[next] === ":") {
        const key = JSON.parse(text.slice(start, index + 1));
        const keys = containers.at(-1);
        if (keys.has(key)) fail(`${label} contains a duplicate object key`);
        keys.add(key);
      }
    }
    if (containers.length > 64) fail(`${label} exceeds the maximum nesting depth`);
  }
  return parsed;
}

function validateNumericModel(model) {
  exactKeys(model, ["format", "tables"], "model");
  if (model.format !== "native-numeric-v1") fail("model format must be native-numeric-v1");
  object(model.tables, "model tables");
  for (const required of ["nodes", "elements", "settings"]) {
    if (!Object.hasOwn(model.tables, required)) fail(`model tables require ${required}`);
  }
  const pending = [];
  for (const [key, value] of Object.entries(model.tables)) {
    if (!TABLES.has(key)) fail("unsupported numeric table");
    if (!Array.isArray(value)) fail(`numeric table ${key} must be an array`);
    pending.push({ value, depth: 0 });
  }
  let count = 0;
  while (pending.length) {
    const { value, depth } = pending.pop();
    if (++count > INPUT_LIMIT_BYTES) fail("numeric model exceeds the input size limit");
    if (depth > 32) fail("numeric tables exceed the maximum nesting depth");
    if (Array.isArray(value)) {
      denseArray(value, "numeric arrays");
      for (let index = 0; index < value.length; index += 1) {
        pending.push({ value: value[index], depth: depth + 1 });
      }
    } else if (value !== null && typeof value !== "boolean" && !(typeof value === "number" && Number.isFinite(value) && Math.abs(value) <= 1e100)) {
      fail("numeric tables may contain only finite numbers within 1e100, booleans, null, and arrays");
    }
  }
  return model;
}

function decodeArtifact(file, label, limit) {
  exactKeys(file, ["path", "sha256", "size", "contentBase64"], label);
  requireHash(file.sha256, `${label} hash`);
  if (!Number.isSafeInteger(file.size) || file.size < 0 || file.size > limit) fail(`${label} size exceeds the allowed limit`);
  if (typeof file.contentBase64 !== "string" || file.contentBase64.length > Math.ceil(limit / 3) * 4 ||
      !/^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(file.contentBase64)) fail(`${label} content must be canonical base64`);
  const bytes = Buffer.from(file.contentBase64, "base64");
  if (bytes.toString("base64") !== file.contentBase64 || bytes.length !== file.size || hash(bytes) !== file.sha256) fail(`${label} size or SHA256 mismatch`);
  return bytes;
}

function validateEnvelope(envelope) {
  exactKeys(envelope, ["schemaVersion", "engine", "modelSha256", "files"], "envelope");
  if (envelope.schemaVersion !== 1) fail("unsupported envelope schemaVersion");
  requireEngine(envelope.engine);
  requireHash(envelope.modelSha256, "modelSha256");
  denseArray(envelope.files, "envelope files");
  if (!Array.isArray(envelope.files) || envelope.files.length !== 1 || envelope.files[0]?.path !== "model.json") fail("envelope must contain only model.json");
  const bytes = decodeArtifact(envelope.files[0], "model.json", INPUT_LIMIT_BYTES);
  if (hash(bytes) !== envelope.modelSha256) fail("modelSha256 does not match model.json");
  return validateNumericModel(parseStrictJson(bytes, "model.json"));
}

function envelopeManifest(envelope) {
  return { schemaVersion: envelope.schemaVersion, engine: envelope.engine, modelSha256: envelope.modelSha256,
    files: envelope.files.map(({ path: filePath, sha256, size }) => ({ path: filePath, sha256, size })) };
}

function manifestSha256(envelope) {
  validateEnvelope(envelope);
  return hash(canonicalJson(envelopeManifest(envelope)));
}

function buildEnvelope({ engine, model }) {
  requireEngine(engine);
  if (typeof model === "string" || Buffer.isBuffer(model) || model instanceof Uint8Array) {
    const bytes = Buffer.from(model);
    if (bytes.length > INPUT_LIMIT_BYTES) fail("model exceeds the input size limit");
    model = parseStrictJson(bytes, "model");
  }
  validateNumericModel(model);
  const bytes = Buffer.from(canonicalJson(model), "utf8");
  if (bytes.length > INPUT_LIMIT_BYTES) fail("model exceeds the input size limit");
  const sha256 = hash(bytes);
  return { schemaVersion: 1, engine, modelSha256: sha256,
    files: [{ path: "model.json", sha256, size: bytes.length, contentBase64: bytes.toString("base64") }] };
}

function inspectEnvelope(envelope) {
  const model = validateEnvelope(envelope);
  return { schemaVersion: 1, engine: envelope.engine, modelSha256: envelope.modelSha256,
    manifestSha256: hash(canonicalJson(envelopeManifest(envelope))),
    files: envelopeManifest(envelope).files,
    tables: Object.fromEntries(Object.entries(model.tables).map(([key, value]) => [key, { rows: value.length }])) };
}

function validateExpected(expected) {
  exactKeys(expected, ["jobId", "engine", "modelSha256", "manifestSha256"], "expected identity");
  requireJobId(expected.jobId);
  requireEngine(expected.engine);
  requireHash(expected.modelSha256, "expected modelSha256");
  requireHash(expected.manifestSha256, "expected manifestSha256");
}

function validateStatus(status, expected) {
  object(status, "job status");
  requireJobId(status.jobId);
  requireEngine(status.engine);
  requireHash(status.modelSha256, "status modelSha256");
  requireHash(status.manifestSha256, "status manifestSha256");
  if (!STATES.has(status.state) || typeof status.executed !== "boolean") fail("invalid native job status");
  for (const [key, value] of Object.entries(expected)) {
    if (status[key] !== value) fail(`native response ${key} does not match the expected job`, "stale-native-evidence");
  }
  return status;
}

function validateCollection(collection, expected) {
  validateExpected(expected);
  exactKeys(collection, ["receipt", "receiptSha256", "artifacts"], "collection");
  const receipt = collection.receipt;
  exactKeys(receipt, ["schemaVersion", "jobId", "engine", "manifestSha256", "modelSha256", "state", "executed", "exitCode", "executableSha256", "artifacts", "nativeTruthStatus"], "receipt");
  if (receipt.schemaVersion !== 1 || receipt.nativeTruthStatus !== "pending-independent-review") fail("receipt must remain pending independent review");
  validateStatus(receipt, expected);
  if (!["succeeded", "failed", "cancelled"].includes(receipt.state)) fail("can collect only a terminal executed job");
  if (receipt.exitCode !== null && !Number.isSafeInteger(receipt.exitCode)) fail("receipt exitCode must be an integer or null");
  if (receipt.executableSha256 !== null || receipt.executed) requireHash(receipt.executableSha256, "executableSha256");
  if (receipt.state === "succeeded" && (!receipt.executed || receipt.exitCode !== 0)) fail("succeeded receipt lacks successful execution evidence");
  requireHash(collection.receiptSha256, "receiptSha256");
  if (hash(canonicalJson(receipt)) !== collection.receiptSha256) fail("receipt SHA256 mismatch");
  if (!Array.isArray(receipt.artifacts) || !Array.isArray(collection.artifacts)) fail("receipt artifacts must be arrays");
  denseArray(receipt.artifacts, "receipt artifacts");
  denseArray(collection.artifacts, "collection artifacts");
  const metadata = new Map();
  let total = 0;
  for (const entry of receipt.artifacts) {
    exactKeys(entry, ["path", "sha256", "size"], "receipt artifact");
    if (!ARTIFACT_NAMES.has(entry.path) || metadata.has(entry.path)) fail("receipt contains an unsupported or duplicate artifact path");
    requireHash(entry.sha256, "artifact SHA256");
    if (!Number.isSafeInteger(entry.size) || entry.size < 0) fail("artifact size must be a nonnegative integer");
    total += entry.size;
    if (total > ARTIFACT_LIMIT_BYTES) fail("artifacts exceed the total size limit");
    metadata.set(entry.path, entry);
  }
  for (const required of ["model.json", "stdout.log", "stderr.log", ...(receipt.state === "succeeded" ? ["result.json"] : [])]) {
    if (!metadata.has(required)) fail(`receipt is missing ${required}`);
  }
  if (collection.artifacts.length !== metadata.size) fail("collection and receipt artifact sets differ");
  const decoded = new Map();
  for (const entry of collection.artifacts) {
    if (!entry || !metadata.has(entry.path) || decoded.has(entry.path)) fail("collection contains an unsupported or duplicate artifact path");
    const wanted = metadata.get(entry.path);
    if (entry.sha256 !== wanted.sha256 || entry.size !== wanted.size) fail("collection artifact metadata differs from receipt");
    decoded.set(entry.path, decodeArtifact(entry, entry.path, ARTIFACT_LIMIT_BYTES));
  }
  const modelBytes = decoded.get("model.json");
  if (modelBytes.length > INPUT_LIMIT_BYTES || hash(modelBytes) !== expected.modelSha256) fail("collected model differs from the submitted model");
  validateNumericModel(parseStrictJson(modelBytes, "collected model.json"));
  const reconstructed = { schemaVersion: 1, engine: expected.engine, modelSha256: expected.modelSha256,
    files: [{ path: "model.json", sha256: expected.modelSha256, size: modelBytes.length }] };
  if (hash(canonicalJson(reconstructed)) !== expected.manifestSha256) fail("collected model does not match the expected manifest");
  return { receipt, receiptSha256: collection.receiptSha256, decoded };
}

function realDirectory(directory, create = false) {
  const absolute = path.resolve(directory);
  const parsed = path.parse(absolute);
  let current = parsed.root;
  for (const component of absolute.slice(parsed.root.length).split(path.sep).filter(Boolean)) {
    current = path.join(current, component);
    let stat;
    try { stat = fs.lstatSync(current); } catch (error) {
      if (error.code !== "ENOENT" || !create) throw error;
      fs.mkdirSync(current, { mode: 0o700 });
      stat = fs.lstatSync(current);
    }
    if (stat.isSymbolicLink() || !stat.isDirectory()) fail("evidence directory contains a symlink or non-directory", "unsafe-evidence-path");
  }
  return absolute;
}

function writePrivate(filePath, bytes) {
  const descriptor = fs.openSync(filePath, fs.constants.O_WRONLY | fs.constants.O_CREAT | fs.constants.O_EXCL, 0o600);
  try {
    fs.writeFileSync(descriptor, bytes);
    fs.fsyncSync(descriptor);
  } finally { fs.closeSync(descriptor); }
}

function readPrivate(filePath, limit = ARTIFACT_LIMIT_BYTES) {
  const stat = fs.lstatSync(filePath);
  if (!stat.isFile() || stat.isSymbolicLink() || stat.nlink !== 1) fail("evidence artifact must be a regular unlinked file", "unsafe-evidence-path");
  if (stat.size > limit) fail("stored evidence size mismatch or limit exceeded");
  const descriptor = fs.openSync(filePath, fs.constants.O_RDONLY | (fs.constants.O_NOFOLLOW || 0));
  try {
    const opened = fs.fstatSync(descriptor);
    if (!opened.isFile() || opened.ino !== stat.ino || opened.dev !== stat.dev) fail("evidence artifact changed during collection");
    const bytes = Buffer.alloc(stat.size + 1);
    let offset = 0;
    while (offset < bytes.length) {
      const count = fs.readSync(descriptor, bytes, offset, bytes.length - offset, null);
      if (!count) break;
      offset += count;
    }
    if (offset !== stat.size) fail("stored evidence size mismatch");
    return bytes.subarray(0, offset);
  } finally { fs.closeSync(descriptor); }
}

function verifyEvidenceDirectory(directory, expected) {
  validateExpected(expected);
  const absolute = realDirectory(directory);
  const receiptBytes = readPrivate(path.join(absolute, "receipt.json"), 64 * 1024);
  const receipt = parseStrictJson(receiptBytes, "stored receipt");
  const receiptSha256 = readPrivate(path.join(absolute, "receipt.sha256"), 65).toString("utf8").trim();
  requireHash(receiptSha256, "stored receiptSha256");
  if (hash(receiptBytes) !== receiptSha256) fail("stored receipt SHA256 mismatch");
  if (!Array.isArray(receipt.artifacts) || receipt.artifacts.length > ARTIFACT_NAMES.size) fail("stored receipt artifacts must be a bounded array");
  let total = 0;
  for (const entry of receipt.artifacts) {
    exactKeys(entry, ["path", "sha256", "size"], "stored artifact metadata");
    if (!ARTIFACT_NAMES.has(entry.path) || !Number.isSafeInteger(entry.size) || entry.size < 0) fail("invalid stored artifact metadata");
    total += entry.size;
    if (total > ARTIFACT_LIMIT_BYTES) fail("stored artifacts exceed the total size limit");
  }
  const names = fs.readdirSync(absolute).sort();
  const wanted = ["receipt.json", "receipt.sha256", ...receipt.artifacts.map((entry) => entry.path)].sort();
  if (JSON.stringify(names) !== JSON.stringify(wanted)) fail("stored evidence contains missing or unexpected files");
  const artifacts = receipt.artifacts.map((entry) => {
    if (!ARTIFACT_NAMES.has(entry.path)) fail("stored receipt contains an unsupported artifact path");
    const bytes = readPrivate(path.join(absolute, entry.path), entry.size);
    return { ...entry, contentBase64: bytes.toString("base64") };
  });
  return validateCollection({ receipt, receiptSha256, artifacts }, expected);
}

async function collectEvidence({ client, jobId, expected, destination, cleanup = false }) {
  validateExpected(expected);
  if (jobId !== expected.jobId) fail("collection jobId does not match expected jobId");
  if (!client || typeof client.collect !== "function" || (cleanup && typeof client.cleanup !== "function")) fail("a native job client is required");
  if (typeof destination !== "string" || !destination) fail("an evidence destination is required");
  if (client.dryRun) return { dryRun: true, op: "collect", expected: { ...expected }, destination: path.resolve(destination), cleanupRequested: Boolean(cleanup) };
  const result = validateCollection(await client.collect(jobId), expected);
  const absolute = path.resolve(destination);
  const parent = realDirectory(path.dirname(absolute), true);
  if (fs.existsSync(absolute) || (() => { try { fs.lstatSync(absolute); return true; } catch (error) { if (error.code === "ENOENT") return false; throw error; } })()) fail("evidence destination already exists", "unsafe-evidence-path");
  const temporary = fs.mkdtempSync(path.join(parent, ".native-collection-"));
  fs.chmodSync(temporary, 0o700);
  let published = false;
  try {
    for (const [name, bytes] of result.decoded) writePrivate(path.join(temporary, name), bytes);
    writePrivate(path.join(temporary, "receipt.json"), canonicalJson(result.receipt));
    writePrivate(path.join(temporary, "receipt.sha256"), `${result.receiptSha256}\n`);
    verifyEvidenceDirectory(temporary, expected);
    realDirectory(parent);
    try { fs.lstatSync(absolute); fail("evidence destination already exists", "unsafe-evidence-path"); } catch (error) { if (error.code !== "ENOENT") throw error; }
    fs.renameSync(temporary, absolute);
    published = true;
    verifyEvidenceDirectory(absolute, expected);
    let cleanupResult = null;
    if (cleanup) cleanupResult = await client.cleanup(jobId, result.receiptSha256);
    return { directory: absolute, receipt: result.receipt, receiptSha256: result.receiptSha256,
      cleanupRequested: Boolean(cleanup), cleanupResult, nativeTruthStatus: "pending-independent-review" };
  } catch (error) {
    if (published) error.evidenceDirectory = absolute;
    throw error;
  } finally {
    if (!published) fs.rmSync(temporary, { recursive: true, force: true });
  }
}

class NativeJobClient {
  constructor({ transport = "ssh", dryRun = true, allowRemote = false, python = "python3", workerPath, root, registry, requestTimeoutMs = 30000 } = {}) {
    if (!["ssh", "local"].includes(transport)) fail("transport must be local or ssh");
    if (typeof dryRun !== "boolean" || typeof allowRemote !== "boolean") fail("dryRun and allowRemote must be booleans");
    if (!Number.isSafeInteger(requestTimeoutMs) || requestTimeoutMs < 1) fail("requestTimeoutMs must be a positive integer");
    if (transport === "local") {
      for (const [key, value] of Object.entries({ python, workerPath, root, registry })) {
        if (typeof value !== "string" || !value || value.includes("\0")) fail(`local transport requires ${key}`);
      }
    }
    if (transport === "ssh" && !dryRun && !allowRemote) fail("remote execution requires explicit allowRemote", "remote-not-authorized");
    this.transport = transport;
    this.dryRun = dryRun;
    this.allowRemote = allowRemote;
    this.command = transport === "ssh" ? "ssh" : python;
    this.args = Object.freeze(transport === "ssh" ? [...SSH_ARGS] : [workerPath, "serve", "--root", root, "--registry", registry]);
    this.requestTimeoutMs = requestTimeoutMs;
    this._nextId = 1;
    this._pending = new Map();
    this._identities = new Map();
    this._process = null;
    this._failure = null;
    this._closed = false;
    this._chunks = [];
    this._chunkBytes = 0;
    this._stderrBytes = 0;
  }

  inspect() {
    return { transport: this.transport, dryRun: this.dryRun, command: this.command, args: [...this.args],
      ...(this.transport === "ssh" ? { routeVerified: false, remoteAuthorized: this.allowRemote } : {}) };
  }

  _abort(error) {
    if (!this._failure) this._failure = error;
    for (const pending of this._pending.values()) {
      clearTimeout(pending.timer);
      pending.reject(error);
    }
    this._pending.clear();
    if (this._process && !this._process.killed) this._process.kill();
  }

  _start() {
    if (this._closed) fail("native client is closed", "client-closed");
    if (this._failure) throw this._failure;
    if (this._process) return;
    if (this.transport === "ssh" && !this.allowRemote) fail("remote execution requires explicit allowRemote", "remote-not-authorized");
    const child = spawn(this.command, this.args, { stdio: ["pipe", "pipe", "pipe"], shell: false, windowsHide: true });
    this._process = child;
    child.on("error", () => this._abort(Object.assign(new Error("native broker process could not start"), { code: "broker-process-error" })));
    child.stdin.on("error", () => this._abort(Object.assign(new Error("native broker input closed"), { code: "broker-process-error" })));
    child.stdout.on("data", (chunk) => {
      try {
        let start = 0;
        while (start < chunk.length) {
          const newline = chunk.indexOf(10, start);
          const part = chunk.subarray(start, newline < 0 ? chunk.length : newline);
          this._chunks.push(part);
          this._chunkBytes += part.length;
          if (this._chunkBytes > MAX_RESPONSE_BYTES) fail("native broker response exceeds the size limit", "broker-protocol-error");
          if (newline < 0) break;
          const line = Buffer.concat(this._chunks, this._chunkBytes);
          this._chunks = [];
          this._chunkBytes = 0;
          this._receive(line);
          start = newline + 1;
        }
      } catch (error) { this._abort(error); }
    });
    child.stderr.on("data", (chunk) => {
      this._stderrBytes += chunk.length;
      if (this._stderrBytes > 1024 * 1024) this._abort(Object.assign(new Error("native broker stderr exceeds the size limit"), { code: "broker-protocol-error" }));
    });
    child.on("close", () => {
      if (!this._closed || this._pending.size) this._abort(Object.assign(new Error("native broker closed before the client"), { code: "broker-process-error" }));
    });
  }

  _receive(line) {
    const response = parseStrictJson(line, "broker response");
    if (typeof response?.ok !== "boolean") fail("invalid broker response", "broker-protocol-error");
    exactKeys(response, ["schemaVersion", "requestId", "ok", response.ok ? "result" : "error"], "broker response");
    if (response.schemaVersion !== 1 || !Number.isSafeInteger(response.requestId) || response.requestId < 1 || !this._pending.has(response.requestId)) fail("unexpected broker response requestId", "broker-protocol-error");
    const pending = this._pending.get(response.requestId);
    let error = null;
    if (response.ok) pending.validate(response.result);
    else {
      exactKeys(response.error, ["code", "message"], "broker error");
      if (typeof response.error.code !== "string" || !response.error.code || response.error.code.length > 128 || typeof response.error.message !== "string" || response.error.message.length > 4096) fail("invalid broker error", "broker-protocol-error");
      error = Object.assign(new Error(response.error.message), { code: response.error.code });
    }
    this._pending.delete(response.requestId);
    clearTimeout(pending.timer);
    if (error) pending.reject(error);
    else pending.resolve(response.result);
  }

  _request(op, fields, validate) {
    if (this._closed) return Promise.reject(Object.assign(new Error("native client is closed"), { code: "client-closed" }));
    if (this.dryRun) return Promise.resolve({ dryRun: true, op, transport: this.inspect(),
      ...(fields.payload ? { envelope: inspectEnvelope(fields.payload) } : fields) });
    try { this._start(); } catch (error) { return Promise.reject(error); }
    const requestId = this._nextId++;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => this._abort(Object.assign(new Error("native broker request timed out"), { code: "broker-timeout" })), this.requestTimeoutMs);
      this._pending.set(requestId, { resolve, reject, timer, validate });
      const request = { schemaVersion: 1, requestId, op, ...fields };
      this._process.stdin.write(`${JSON.stringify(request)}\n`, (error) => { if (error) this._abort(error); });
    });
  }

  submit(envelope) {
    const summary = inspectEnvelope(envelope);
    return this._request("submit", { payload: envelope }, (result) => {
      const identity = { engine: summary.engine, modelSha256: summary.modelSha256, manifestSha256: summary.manifestSha256 };
      validateStatus(result, identity);
      this._identities.set(result.jobId, { jobId: result.jobId, ...identity });
    });
  }

  status(jobId) {
    requireJobId(jobId);
    return this._request("status", { jobId }, (result) => validateStatus(result, this._identities.get(jobId) || { jobId }));
  }

  collect(jobId) {
    requireJobId(jobId);
    return this._request("collect", { jobId }, (result) => validateCollection(result, this._identities.get(jobId) || {
      jobId, engine: result?.receipt?.engine, modelSha256: result?.receipt?.modelSha256, manifestSha256: result?.receipt?.manifestSha256 }));
  }

  cancel(jobId) {
    requireJobId(jobId);
    return this._request("cancel", { jobId }, (result) => validateStatus(result, this._identities.get(jobId) || { jobId }));
  }

  cleanup(jobId, receiptSha256) {
    requireJobId(jobId);
    requireHash(receiptSha256, "cleanup receiptSha256");
    return this._request("cleanup", { jobId, receiptSha256 }, (result) => {
      exactKeys(result, ["jobId", "cleaned"], "cleanup response");
      if (result.jobId !== jobId || result.cleaned !== true) fail("cleanup response does not confirm the expected job cleanup");
    });
  }

  async close() {
    if (this._closed) return;
    this._closed = true;
    if (!this._process) return;
    const child = this._process;
    for (const pending of this._pending.values()) {
      clearTimeout(pending.timer);
      pending.reject(Object.assign(new Error("native client closed"), { code: "client-closed" }));
    }
    this._pending.clear();
    if (child.exitCode !== null || child.signalCode !== null) return;
    child.stdin.end();
    await new Promise((resolve, reject) => {
      const terminate = setTimeout(() => child.kill("SIGTERM"), 5000);
      const timeout = setTimeout(() => {
        // Forced termination can orphan solver children. Leave the broker and
        // its host lock available for operator inspection if shutdown stalls.
        reject(Object.assign(new Error("native broker shutdown timed out; inspect the host job and lock"), { code: "broker-shutdown-timeout" }));
      }, 15000);
      child.once("close", () => { clearTimeout(terminate); clearTimeout(timeout); resolve(); });
    });
  }
}

module.exports = { INPUT_LIMIT_BYTES, ARTIFACT_LIMIT_BYTES, REMOTE_COMMAND, SSH_ARGS,
  canonicalJson, buildEnvelope, validateEnvelope, inspectEnvelope, manifestSha256,
  validateCollection, collectEvidence, verifyEvidenceDirectory, NativeJobClient };
