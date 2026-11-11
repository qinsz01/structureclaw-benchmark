import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import provider from '../../lib/corpus-provider.cjs';
import { exportData } from '../scripts/export-data.mjs';

test('exports only the complete research-300 corpus and removes previous generated legacy data', () => {
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), 'research-viewer-data-'));
  const output = path.join(temporary, 'data');
  fs.mkdirSync(output);
  try {
    fs.mkdirSync(path.join(output, 'cases'));
    fs.writeFileSync(path.join(output, 'cases/beam-simple.json'), '{}');
    fs.mkdirSync(path.join(output, 'fixtures'));
    fs.writeFileSync(path.join(output, 'fixtures/old-input.png'), 'old');
    fs.writeFileSync(path.join(output, 'keep.txt'), 'caller-owned');
    exportData(output);
    assert.deepEqual(fs.readdirSync(temporary), ['data'], 'a data export must stay inside its requested directory');
    const index = JSON.parse(fs.readFileSync(path.join(output, 'index.json'), 'utf8'));
    assert.equal(index.corpusId, 'research-300');
    assert.equal(index.cases.length, 300);
    assert.equal(index.summary.turns, 420);
    assert.equal(index.summary.states, 364);
    assert.ok(index.cases.every((c) => /^(STD|INT|MM)-\d{3}$/.test(c.id)));
    assert.equal(fs.existsSync(path.join(output, 'cases/beam-simple.json')), false);
    assert.equal(fs.readdirSync(path.join(output, 'cases')).length, 300);
    assert.equal(fs.readdirSync(path.join(output, 'models')).length, 364);
    assert.equal(fs.existsSync(path.join(output, 'fixtures')), false);
    assert.equal(fs.readFileSync(path.join(output, 'keep.txt'), 'utf8'), 'caller-owned');
    const hash = (file) => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
    const read = (relative) => readJson(path.join(output, relative));
    assert.deepEqual(index.catalogue, read('catalogue.json'), 'the page and downloadable classification use one projection');
    assert.deepEqual(index.catalogue.totals, {
      cases: 300, turns: 420, states: 364, attachmentFiles: 326,
      attachmentUses: 326, markdownFiles: 221, pngFiles: 82, dxfFiles: 23,
    });
    assert.equal(index.catalogue.cases.length, 300);
    for (const buckets of Object.values(index.catalogue.breakdowns))
      assert.equal(buckets.reduce((total, bucket) => total + bucket.cases, 0), 300);
    assert.equal(index.catalogue.breakdowns.modality.find((row) => row.key === 'image').cases, 77);
    assert.equal(index.catalogue.breakdowns.modality.find((row) => row.key === 'image').pngFiles, 82);
    assert.ok(fs.statSync(path.join(output, 'benchmark-catalogue.xlsx')).size > 10000);
    const corpus = provider.loadCorpus({ corpus: 'research-300', root: repo });
    const thumbnails = read('thumbnails.json');
    assert.equal(Object.keys(thumbnails).length, 364);
    assert.deepEqual(index.summary.byEngine, { OpenSees: 267, PKPM: 16, YJK: 17 });
    assert.equal(index.summary.nativeVerified, 300);
    assert.equal(index.summary.accepted, 0);
    assert.equal(index.summary.inputReviewed, 0);
    assert.equal(index.summary.agentNotRun, 300);
    assert.equal(index.evaluatorVersion, 'research300-evaluator');
    for (const summary of index.cases) {
      const record = provider.loadCase(corpus, summary.id);
      const detail = read(`cases/${summary.id}.json`);
      const frozen = readJson(path.join(record.caseDir, 'independent-reference.json'));
      const acceptance = readJson(path.join(record.caseDir, 'acceptance.json'));
      const manifestCase = frozenManifest.cases.find((c) => c.id === summary.id);
      assert.equal(detail.sourceHash, manifestCase.sourceHash, summary.id);
      assert.deepEqual(detail.contract, record.contract, summary.id);
      assert.deepEqual(detail.acceptance, acceptance, summary.id);
      assert.equal(detail.status.nativeVerified, true, summary.id);
      assert.equal(detail.status.accepted, false, summary.id);
      assert.equal(detail.status.inputReviewed, false, summary.id);
      assert.equal(detail.turns.length, record.contract.turns.length, summary.id);
      for (const [i, turn] of detail.turns.entries()) {
        const visible = provider.getPublicTurnInput(record, i);
        assert.equal(turn.instruction, visible.instruction, `${summary.id}/${turn.id}`);
        assert.deepEqual(turn.responseContract, visible.responseContract);
        assert.deepEqual(turn.requiredOutputs, visible.responseContract.outputs);
        assert.deepEqual(
          turn.attachments.map((a) => a.name),
          visible.attachments.map((a) => a.name),
        );
        for (const [j, attachment] of turn.attachments.entries()) {
          assert.deepEqual(
            fs.readFileSync(path.join(output, attachment.path)),
            fs.readFileSync(visible.attachments[j].path),
          );
          assert.equal(attachment.sha256, hash(visible.attachments[j].path));
          assert.equal(attachment.bytes, fs.statSync(visible.attachments[j].path).size);
          if (attachment.name.endsWith('.dxf'))
            assert.ok(read(`${attachment.path}.json`).entities.length > 0);
        }
        assert.deepEqual(
          turn.quantities.map((q) => q.id),
          visible.responseContract.quantities.map((q) => q.id),
          `${summary.id}/${turn.id}: quantity scope`,
        );
        assert.deepEqual(
          turn.derived.map((q) => q.id),
          visible.responseContract.derived.map((q) => q.id),
          `${summary.id}/${turn.id}: derived scope`,
        );
        if (turn.expectation === 'clarify') {
          assert.equal(turn.state, null);
          assert.deepEqual(turn.quantities, []);
          assert.deepEqual(turn.derived, []);
          continue;
        }
        assert.equal(turn.state, record.contract.turns[i].state);
        const referenceState = frozen.states.find((s) => s.state === turn.state);
        for (const family of ['quantities', 'derived']) {
          for (const displayed of turn[family]) {
            const original = referenceState[family].find((q) => q.id === displayed.id);
            const requested = visible.responseContract[family].find((q) => q.id === displayed.id);
            const factors = {
              m: 1,
              mm: 0.001,
              rad: 1,
              N: 1,
              kN: 1000,
              'N.m': 1,
              'N*m': 1,
              'kN.m': 1000,
              'kN*m': 1000,
              'kN·m': 1000,
            };
            const factor = factors[original.unit] / factors[requested.unit];
            assert.equal(
              displayed.value,
              original.value * factor,
              `${summary.id}/${turn.id}/${displayed.id}`,
            );
            assert.equal(displayed.unit, requested.unit);
            assert.equal(displayed.sourceValue, original.value);
            assert.equal(displayed.sourceUnit, original.unit);
            if (original.tolerance)
              assert.deepEqual(displayed.tolerance, {
                absolute: original.tolerance.absolute * factor,
                relative: original.tolerance.relative,
              });
            assert.deepEqual(displayed.rawTrace, original.rawTrace);
          }
        }
      }
      for (const state of detail.states) {
        const original = frozen.states.find((s) => s.state === state.state);
        assert.deepEqual(state.quantities, original.quantities);
        assert.deepEqual(state.derived, original.derived || []);
        assert.equal(state.reference.kind, frozen.referenceKind);
        assert.equal(
          state.reference.sha256,
          hash(path.join(record.caseDir, 'independent-reference.json')),
        );
        assert.equal(state.nativeReference.kind, `native-${detail.engine.toLowerCase()}`);
        assert.equal(
          state.nativeReference.source,
          `corpora/research-300/cases/${summary.id}/${detail.engine === 'OpenSees' ? 'native-opensees-reference.json' : 'independent-reference.json'}`,
        );
        const sourceModel = path.join(record.caseDir, record.contract.modelStates[state.state - 1]);
        assert.deepEqual(read(state.modelPath).model, readJson(sourceModel));
        assert.equal(read(state.modelPath).sha256, hash(sourceModel));
        assert.deepEqual(
          thumbnails[`${summary.id}-s${state.state}`].nodes,
          readJson(sourceModel).nodes,
        );
        assert.equal(state.receipts.length, state.selections.length);
        for (const receipt of state.receipts) {
          const { source, sha256, ...body } = receipt;
          assert.deepEqual(body, readJson(path.join(repo, source)));
          assert.equal(sha256, hash(path.join(repo, source)));
          assert.equal(body.engine, detail.engine);
          assert.equal(body.state, state.state);
          assert.equal(body.modelSha256, state.modelSha256);
        }
      }
    }
    const units = read('cases/INT-097.json');
    assert.equal(units.turns[0].state, units.turns[1].state);
    assert.deepEqual(
      units.turns[0].quantities.map((q) => q.unit),
      ['m', 'm'],
    );
    assert.deepEqual(
      units.turns[1].quantities.map((q) => q.unit),
      ['mm', 'mm'],
    );
    assert.ok(units.turns[0].quantities.every((q) => !q.id.endsWith('--mm')));
    const difference = read('cases/STD-089.json');
    assert.equal(index.cases.find((c) => c.id === 'STD-089').strictComparison, 'difference');
    assert.deepEqual(
      difference.diagnostics.comparisons.matrix.strict.failures.map((f) => f.id),
      ['case-D-member-x0-0-1-s0-right-M3', 'case-D-member-x0-0-2-s0-right-M3'],
    );
    assert.equal(difference.diagnostics.comparisons.matrix.engineering.failed, 0);
    assert.equal(difference.diagnostics.comparisonPolicy.default, 'strict');
    assert.ok(
      index.sources.every(
        (source) => !/^(fixtures|scenarios|results|viewer\/derived)\//.test(source.source),
      ),
    );
    for (const source of index.sources)
      assert.equal(source.sha256, hash(path.join(repo, source.source)), source.source);
  } finally {
    fs.rmSync(temporary, { recursive: true, force: true });
  }
});

test('requested output units convert signed values and frozen tolerances without changing source metadata', async () => {
  const { requestedUnit } = await import('../scripts/research-data.mjs');
  const quantity = {
    id: 'ux',
    component: 'ux',
    value: -0.002,
    unit: 'm',
    tolerance: { absolute: 1e-8, relative: 1e-6 },
    rawTrace: { value: -0.002 },
  };
  const before = structuredClone(quantity);
  const displayed = requestedUnit(quantity, 'mm');
  assert.equal(displayed.value, -2);
  assert.equal(displayed.unit, 'mm');
  assert.equal(displayed.sourceValue, -0.002);
  assert.equal(displayed.sourceUnit, 'm');
  assert.equal(displayed.tolerance.absolute, 0.00001);
  assert.deepEqual(displayed.rawTrace, quantity.rawTrace);
  assert.deepEqual(quantity, before);
  assert.throws(() => requestedUnit(quantity, 'kN'), /Incompatible requested unit/);
});

test('engineering diagnostic allowances retain their own units when a frozen moment is displayed in new units', async () => {
  const { requestedUnit } = await import('../scripts/research-data.mjs');
  const base = path.resolve(import.meta.dirname, '../../corpora/research-300/cases/STD-089');
  const reference = JSON.parse(fs.readFileSync(path.join(base, 'independent-reference.json')));
  const frozen = reference.states[0].quantities.find(
    (q) => q.id === 'case-D-member-x0-0-1-s0-right-M3',
  );
  const displayed = requestedUnit(frozen, 'N.m');
  assert.ok(
    displayed.engineeringPrecision,
    'The engineering diagnostic must survive unit conversion',
  );
  assert.equal(displayed.engineeringPrecision.unit, 'N.m');
  assert.equal(
    displayed.engineeringPrecision.terms[0],
    frozen.engineeringPrecision.terms[0] * 1000,
  );
  assert.equal(displayed.value, frozen.value * 1000);
  assert.equal(displayed.tolerance.absolute, frozen.tolerance.absolute * 1000);
  assert.equal(frozen.engineeringPrecision.unit, 'kN.m');
});

const repo = path.resolve(import.meta.dirname, '../..');
const readJson = (file) => JSON.parse(fs.readFileSync(file, 'utf8'));
const frozenManifest = readJson(path.join(repo, 'corpora/research-300/manifest.json'));
const plan = readJson(path.join(repo, 'planning/benchmark-plan.json'));

async function caseFixture(id, run) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'research-viewer-fixture-'));
  try {
    const base = path.join(root, 'corpora/research-300/cases', id);
    fs.cpSync(path.join(repo, 'corpora/research-300/cases', id), base, { recursive: true });
    const entry = structuredClone(frozenManifest.cases.find((c) => c.id === id));
    for (const name of ['public_input_clean.py', 'public_input_visual.py', 'render_public_visual.cjs', 'public_input_editorial.py']) {
      const relative = path.join('scripts/research300', name);
      fs.mkdirSync(path.dirname(path.join(root, relative)), { recursive: true });
      fs.copyFileSync(path.join(repo, relative), path.join(root, relative));
    }
    const corpusDir = path.join(root, 'corpora/research-300');
    fs.writeFileSync(path.join(corpusDir, 'manifest.json'), JSON.stringify({ ...frozenManifest, cases: [entry] }));
    const inputs = path.join(corpusDir, 'public-inputs');
    fs.cpSync(path.join(repo, 'corpora/research-300/public-inputs', id), path.join(inputs, id), { recursive: true });
    const publicManifest = readJson(path.join(repo, 'corpora/research-300/public-inputs/manifest.json'));
    fs.writeFileSync(path.join(inputs, 'manifest.json'), JSON.stringify({ ...publicManifest, cases: publicManifest.cases.filter((row) => row.id === id) }));

    const { createResearchReader, readResearchCase } = await import('../scripts/research-data.mjs');
    const { default: provider } = await import('../../lib/corpus-provider.cjs');
    const { createHash } = await import('node:crypto');
    const sha = (bytes) => createHash('sha256').update(bytes).digest('hex');
    const refresh = (name) => {
      const bytes = fs.readFileSync(path.join(base, name));
      const descriptor = [...entry.publicFiles, ...entry.privateFiles].find((f) => f.path === name);
      Object.assign(descriptor, { sha256: sha(bytes), bytes: bytes.length });
    };
    const load = (alter = () => {}) => {
      const reader = createResearchReader(root);
      const loadEvidence = (name) => {
        const source = `corpora/research-300/evidence/${name}`;
        fs.mkdirSync(path.dirname(path.join(root, source)), { recursive: true });
        fs.copyFileSync(path.join(repo, source), path.join(root, source));
        const document = reader.json(source);
        return { document, source, sha256: reader.sources.get(source).sha256 };
      };
      const evidence = loadEvidence('commercial-native-diagnostic-comparison.json');
      evidence.openSees = loadEvidence('reference-cross-check.json');
      alter(evidence);
      return readResearchCase(
        reader,
        provider.loadCorpus({ corpus: 'research-300', root }),
        entry,
        plan.cases.find((c) => c.id === id),
        evidence,
      );
    };
    await run({ root, base, entry, load, refresh });
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
}

test('rejects changed or missing frozen references without borrowing another engine', async () => {
  await caseFixture('INT-001', ({ base, load }) => {
    assert.equal(load().detail.id, 'INT-001');
    const file = path.join(base, 'independent-reference.json');
    const bytes = fs.readFileSync(file);
    fs.appendFileSync(file, '\n');
    assert.throws(load, /Stale source hash.*independent-reference/);
    fs.writeFileSync(file, bytes);
    fs.unlinkSync(file);
    assert.throws(load, /frozen file inventory differs/);
  });
  await caseFixture('STD-089', ({ base, load, refresh }) => {
    fs.copyFileSync(
      path.join(base, 'native-opensees-reference.json'),
      path.join(base, 'independent-reference.json'),
    );
    refresh('independent-reference.json');
    assert.throws(load, /native qualification|invalid research source|scoring reference engine/);
  });
});

test('rejects a stale sourceHash and a native receipt for the wrong engine or physical state', async () => {
  await caseFixture('INT-001', ({ base, entry, load, refresh }) => {
    const originalHash = entry.sourceHash;
    entry.sourceHash = '0'.repeat(64);
    assert.throws(load, /stale manifest sourceHash/);
    entry.sourceHash = originalHash;
    const name = 'native-run-1-case-D.json';
    const receipt = readJson(path.join(base, name));
    fs.writeFileSync(path.join(base, name), JSON.stringify({ ...receipt, engine: 'PKPM' }));
    refresh(name);
    assert.throws(load, /native qualification|native receipt/);
    fs.writeFileSync(path.join(base, name), JSON.stringify({ ...receipt, state: 2 }));
    refresh(name);
    assert.throws(load, /native qualification|native receipt/);
    fs.unlinkSync(path.join(base, name));
    assert.throws(load, /frozen file inventory differs/);
  });
});

test('rejects traversal and symbolic links instead of copying outside the corpus', async () => {
  const { createResearchReader } = await import('../scripts/research-data.mjs');
  assert.throws(() => createResearchReader(repo).bytes('../outside.json'), /Unsafe relative path/);
  assert.throws(
    () => exportData(path.join(repo, 'corpora/research-300')),
    /must not overwrite corpus/,
  );
  await caseFixture('INT-001', ({ base, load }) => {
    const attachment = path.join(base, 'input-tables.txt');
    fs.unlinkSync(attachment);
    fs.symlinkSync(path.join(base, 'contract.json'), attachment);
    assert.throws(load, /Symlink path is forbidden/);
  });
});

test('rejects stale diagnostic artifacts and edited strict results', async () => {
  await caseFixture('STD-089', ({ load }) => {
    assert.throws(
      () =>
        load((evidence) => {
          evidence.document.cases.find((c) => c.id === 'STD-089').artifacts[0].sha256 = '0'.repeat(
            64,
          );
        }),
      /Stale source hash/,
    );
    assert.throws(
      () =>
        load((evidence) => {
          const row = evidence.document.cases.find((c) => c.id === 'STD-089');
          row.comparisons.matrix.strict.failed = 0;
        }),
      /stale matrix diagnostic comparison/,
    );
  });
});
