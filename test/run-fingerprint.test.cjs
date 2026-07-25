const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

const {
  hashAttachments,
  hashCanonical,
  hashFiles,
} = require("../lib/run-fingerprint.cjs");

test("canonical hashes ignore object key insertion order", () => {
  assert.equal(
    hashCanonical({ b: 2, a: { d: 4, c: 3 } }),
    hashCanonical({ a: { c: 3, d: 4 }, b: 2 }),
  );
});

test("file hashes change with file content and not directory enumeration order", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "structureclaw-fingerprint-"));
  try {
    fs.mkdirSync(path.join(dir, "nested"));
    fs.writeFileSync(path.join(dir, "b.txt"), "b");
    fs.writeFileSync(path.join(dir, "nested", "a.txt"), "a");
    const before = hashFiles(dir, ["nested", "b.txt"]);
    assert.equal(before, hashFiles(dir, ["b.txt", "nested"]));
    fs.writeFileSync(path.join(dir, "nested", "a.txt"), "changed");
    assert.notEqual(before, hashFiles(dir, ["nested", "b.txt"]));
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test("attachment hashes are content-addressed and de-duplicate repeated references", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "structureclaw-attachments-"));
  try {
    fs.writeFileSync(path.join(dir, "drawing.dxf"), "first");
    const scenarios = [{
      attachments: [{ relPath: "drawing.dxf" }],
      turns: [{ attachments: [{ relPath: "drawing.dxf" }] }],
    }];
    const before = hashAttachments(dir, scenarios);
    fs.writeFileSync(path.join(dir, "drawing.dxf"), "second");
    assert.notEqual(before, hashAttachments(dir, scenarios));
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});
