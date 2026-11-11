import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import { createResearchReader } from '../scripts/research-data.mjs';
const moduleFile = new URL('../scripts/native-displacements.mjs', import.meta.url);
const api = fs.existsSync(moduleFile) ? await import(moduleFile) : {};
const root = path.resolve(new URL('../..', import.meta.url).pathname);
const hash = (bytes) => crypto.createHash('sha256').update(bytes).digest('hex');
function context(id, state = 1, sourceRoot = root) {
  const reader = createResearchReader(sourceRoot),
    base = `corpora/research-300/cases/${id}`;
  const read = (name) => reader.json(`${base}/${name}`);
  const contract = read('contract.json'),
    acceptance = read('acceptance.json');
  const modelName = contract.modelStates[state - 1];
  const model = read(modelName),
    modelSource = reader.sources.get(`${base}/${modelName}`);
  const receipts = acceptance.sameEngineTruth.receipts
    .filter((r) => r.state === state)
    .map((r) => ({ ...read(r.path), source: `${base}/${r.path}`, sha256: r.sha256 }));
  return {
    reader,
    base,
    caseId: id,
    engine: contract.plannedEngine,
    sourceHash: acceptance.sourceHash,
    state,
    model,
    modelSource,
    selections: receipts.map((r) => r.selection),
    receipts,
  };
}
const extract = (c) => api.readNativeDisplacementFields?.(c) || [];

test('STD-001 and MM-001 recover all nodes and members from native evidence, beyond requested rows', () => {
  for (const id of ['STD-001', 'MM-001']) {
    const c = context(id),
      fields = extract(c);
    assert.equal(fields.length, c.selections.length, `${id}: native fields missing`);
    for (const f of fields) {
      assert.equal(f.coverage.completeNodes, c.model.nodes.length);
      assert.equal(f.coverage.completeElements, c.model.elements.length);
      assert.equal(f.quantities.length, c.model.nodes.length * 3);
      assert.ok(f.sources.some((s) => s.source.endsWith('/native-raw-responses.json')));
    }
  }
});
test('spatial OpenSees, PKPM and YJK retain exact engine-specific field provenance', () => {
  for (const [id, engine, file] of [
    ['INT-040', 'OpenSees', 'native-raw-responses.json'],
    ['INT-079', 'PKPM', 'sdk-results.json'],
    ['INT-081', 'YJK', 'read-results.json'],
    ['MM-079', 'YJK', 'read-results.json'],
    ['MM-085', 'YJK', 'read-results.json'],
  ]) {
    const c = context(id),
      f = extract(c)[0];
    assert.ok(f, `${id}: native field missing`);
    assert.equal(f.engine, engine);
    assert.equal(f.coverage.completeNodes, c.model.nodes.length);
    assert.equal(f.coverage.completeElements, c.model.elements.length);
    assert.ok(f.sources.some((s) => s.source.endsWith('/' + file)));
    if (engine !== 'OpenSees')
      assert.ok(f.sources.every((s) => !s.source.endsWith('/native-raw-responses.json')));
  }
});
test('PKPM sentinel is only replaced by explicitly supported fixed constraints; finite pin responses survive', () => {
  const f = extract(context('INT-079'))[0];
  assert.ok(f, 'native field missing');
  const fixed = f.quantities.filter((q) => q.location.id === 'n0-1-0');
  assert.equal(fixed.length, 3);
  assert.ok(fixed.every((q) => q.value === 0 && q.origin === 'explicit-constraint-zero'));
  assert.ok(fixed.every((q) => q.rawTrace.constraintSources.length >= 3));
  const pin = f.quantities.filter((q) => q.location.id === 'n0-0-0');
  assert.ok(pin.every((q) => q.origin === 'native-recorded'));
  assert.deepEqual(
    pin.map((q) => q.value),
    [0, 0, 0],
  );
  assert.ok(pin.every((q) => q.rawTrace.terms.every((t) => t.rawValue === 0)));
  assert.ok(f.quantities.every((q) => q.value !== -99999));
});
test('wrong state, engine, source hash, model, or selection cannot select native evidence', () => {
  const c = context('STD-001');
  assert.equal(typeof api.readNativeDisplacementFields, 'function');
  for (const wrong of [
    { state: 2 },
    { engine: 'PKPM' },
    { sourceHash: '0'.repeat(64) },
    { model: { ...c.model, nodes: [] } },
    { selections: [{ kind: 'combination', id: 'D' }] },
  ])
    assert.throws(
      () => api.readNativeDisplacementFields({ ...c, ...wrong }),
      /binding|model|receipt|selection/i,
    );
});
test('source corruption is rejected before field values are exported', (t) => {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'native-field-'));
  t.after(() => fs.rmSync(temp, { recursive: true, force: true }));
  const base = 'corpora/research-300/cases/STD-001';
  fs.mkdirSync(path.join(temp, base), { recursive: true });
  fs.cpSync(path.join(root, base), path.join(temp, base), { recursive: true });
  fs.appendFileSync(path.join(temp, base, 'native-raw-responses.json'), ' ');
  assert.equal(typeof api.readNativeDisplacementFields, 'function');
  assert.throws(() => api.readNativeDisplacementFields(context('STD-001', 1, temp)), /hash/i);
});
test('a missing native free component stays unavailable rather than becoming zero', (t) => {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'native-field-gap-'));
  t.after(() => fs.rmSync(temp, { recursive: true, force: true }));
  const base = 'corpora/research-300/cases/STD-001';
  fs.mkdirSync(path.join(temp, base), { recursive: true });
  fs.cpSync(path.join(root, base), path.join(temp, base), { recursive: true });
  const c = context('STD-001', 1, temp),
    file = path.join(temp, base, 'native-raw-responses.json');
  const raw = JSON.parse(fs.readFileSync(file));
  raw.runs[0].responses.nodes.N1.displacement[2] = null;
  fs.writeFileSync(file, JSON.stringify(raw));
  const receipt = c.receipts[0],
    body = JSON.parse(fs.readFileSync(path.join(temp, receipt.source)));
  body.artifacts.find((a) => a.path === 'native-raw-responses.json').sha256 = hash(
    fs.readFileSync(file),
  );
  fs.writeFileSync(path.join(temp, receipt.source), JSON.stringify(body));
  c.receipts = [
    {
      ...body,
      source: receipt.source,
      sha256: hash(fs.readFileSync(path.join(temp, receipt.source))),
    },
  ];
  c.reader = createResearchReader(temp);
  const f = extract(c)[0];
  assert.ok(f, 'native field missing');
  assert.deepEqual(f.coverage.missingNodeIds, ['N1']);
  assert.equal(f.coverage.completeElements, 0);
  assert.ok(!f.quantities.some((q) => q.location.id === 'N1' && q.component === 'uz'));
});

test('exact native translations retain solver values independently of scoring samples', () => {
  for (const [id, node, component, value] of [
    ['STD-001', 'N1', 'uz', -0.00030339805825242727],
    ['INT-079', 'n1-1-2', 'ux', -6.557843789778417e-6],
    ['INT-081', 'n1-2-3', 'ux', 2.770752644210006e-6],
  ])
    assert.equal(
      extract(context(id))[0].quantities.find(
        (q) => q.location.id === node && q.component === component,
      ).value,
      value,
    );
});
test('combinations retain their own native receipt and cannot borrow a same-named basic case', () => {
  const fields = extract(context('STD-091'));
  assert.deepEqual(fields.map((f) => `${f.selection.kind}:${f.selection.id}`).sort(), [
    'combination:D',
    'combination:D+L',
  ]);
  assert.equal(new Set(fields.map((f) => f.receipt.source)).size, 2);
  assert.throws(
    () =>
      api.readNativeDisplacementFields({
        ...context('STD-091'),
        selections: [{ kind: 'case', id: 'D' }],
      }),
    /receipt/,
  );
  const combined = fields.find((f) => f.selection.id === 'D+L');
  assert.ok(
    combined.quantities.every(
      (q) => q.rawTrace.nativeBasicFactors.DL === 1 && q.rawTrace.nativeBasicFactors.LL === 1,
    ),
  );
});
function alteredPkpm(t, alter) {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'pkpm-field-gap-'));
  t.after(() => fs.rmSync(temp, { recursive: true, force: true }));
  const base = 'corpora/research-300/cases/INT-079';
  fs.mkdirSync(path.join(temp, base), { recursive: true });
  fs.cpSync(path.join(root, base), path.join(temp, base), { recursive: true });
  const c = context('INT-079', 1, temp),
    candidateFile = path.join(temp, base, 'native-commercial/candidate.json');
  const candidate = JSON.parse(fs.readFileSync(candidateFile)),
    entry = candidate.nativeArtifacts[candidate.states[0].nativeRun]['sdk-results.json'];
  const sdkPath = `native-commercial/evidence/${entry.path}`,
    sdkFile = path.join(temp, base, sdkPath),
    sdk = JSON.parse(fs.readFileSync(sdkFile));
  alter(sdk);
  fs.writeFileSync(sdkFile, JSON.stringify(sdk));
  entry.sha256 = hash(fs.readFileSync(sdkFile));
  fs.writeFileSync(candidateFile, JSON.stringify(candidate));
  c.receipts = c.receipts.map((receipt) => {
    const body = JSON.parse(fs.readFileSync(path.join(temp, receipt.source)));
    body.artifacts.find((a) => a.path === sdkPath).sha256 = entry.sha256;
    body.artifacts.find((a) => a.path === 'native-commercial/candidate.json').sha256 = hash(
      fs.readFileSync(candidateFile),
    );
    fs.writeFileSync(path.join(temp, receipt.source), JSON.stringify(body));
    return {
      ...body,
      source: receipt.source,
      sha256: hash(fs.readFileSync(path.join(temp, receipt.source))),
    };
  });
  c.reader = createResearchReader(temp);
  return c;
}
test('PKPM free sentinel and omitted fixed component stay unavailable', (t) => {
  const c = alteredPkpm(t, (sdk) => {
    sdk.nodes.find((n) => n.coordinates.join(',') === '6000,5000,7200').cases.DL[0] = -99999;
    sdk.nodes.find((n) => n.coordinates.join(',') === '0,5000,0').cases.DL[0] = null;
  });
  const f = extract(c)[0];
  assert.deepEqual(f.coverage.missingNodeIds, ['n0-1-0', 'n1-1-2']);
  assert.ok(f.quantities.every((q) => q.value !== -99999));
  assert.ok(!f.quantities.some((q) => q.location.id === 'n1-1-2' && q.component === 'ux'));
});
