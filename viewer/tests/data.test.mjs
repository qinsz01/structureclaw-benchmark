import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import { exportData, corpusRoot } from '../scripts/export-data.mjs';

const hash = (file) => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
test('all cases export their exact inputs, turn-scoped references and byte-identical attachments', () => {
  const out = fs.mkdtempSync(path.join(os.tmpdir(), 'sclaw-viewer-test-'));
  try {
    const originalFiles = [
      'benchmark.json',
      ...fs
        .readdirSync(path.join(corpusRoot, 'scenarios'), { recursive: true })
        .filter((f) => f.endsWith('.json'))
        .map((f) => path.join('scenarios', f)),
      ...fs
        .readdirSync(path.join(corpusRoot, 'fixtures'), { recursive: true })
        .filter((f) => fs.statSync(path.join(corpusRoot, 'fixtures', f)).isFile())
        .map((f) => path.join('fixtures', f)),
    ];
    const before = Object.fromEntries(
      originalFiles.map((f) => [f, hash(path.join(corpusRoot, f))]),
    );
    const { cases, manifest } = exportData(out);
    const read = (p) => JSON.parse(fs.readFileSync(path.join(out, p), 'utf8'));
    const models = JSON.parse(
      fs.readFileSync(path.join(corpusRoot, 'fixtures/ground-truth-models.json'), 'utf8'),
    );
    const numerical = JSON.parse(
      fs.readFileSync(path.join(corpusRoot, 'fixtures/opensees-ground-truth.json'), 'utf8'),
    );
    assert.equal(cases.length, 150);
    assert.equal(new Set(cases.map((c) => c.id)).size, 150);
    for (const c of cases) {
      const original = JSON.parse(fs.readFileSync(path.join(corpusRoot, c.source), 'utf8'));
      const detail = read(`cases/${c.id}.json`);
      assert.deepEqual(detail.scenario, original, c.id);
      assert.equal(detail.sourceSha256, before[path.normalize(c.source)]);
      const turns = original.turns || [
        {
          message: original.message,
          engineeringSpecification: original.engineeringSpecification,
          assertions: original.expect?.assertions || [],
        },
      ];
      detail.turns.forEach((t, i) => {
        assert.equal(t.message, turns[i].message);
        assert.deepEqual(t.assertions, turns[i].assertions);
        assert.deepEqual(detail.references[i], [
          ...new Set(turns[i].assertions.map((a) => a.groundTruthId).filter(Boolean)),
        ]);
      });
      for (const attachment of original.attachments || [])
        assert.equal(
          hash(path.join(out, attachment.relPath)),
          before[attachment.relPath.replaceAll('/', path.sep)] ||
            hash(path.join(corpusRoot, attachment.relPath)),
        );
      for (const id of c.referenceIds) {
        const reference = read(`models/${id}.json`);
        assert.deepEqual(reference.model, models.find((m) => m.id === id).model);
        assert.deepEqual(
          reference.numerical,
          numerical.models.find((m) => m.modelId === id) || null,
        );
        const model = reference.model;
        for (const element of model.elements)
          assert.ok(
            element.nodes.every((id) => model.nodes.some((n) => n.id === id)),
            `${id}/${element.id}`,
          );
        for (const load of model.load_cases.flatMap((c) => c.loads)) {
          assert.equal(
            load.reference_frame,
            'global',
            'viewer arrows currently support explicit global loads',
          );
          if (load.node) assert.ok(model.nodes.some((n) => n.id === load.node));
          if (load.element) assert.ok(model.elements.some((e) => e.id === load.element));
        }
      }
      for (const t of turns)
        for (const a of t.assertions.filter((a) => a.type === 'numerical_matches')) {
          const engine = (
            a.engineId ||
            original.analysisEngineTarget ||
            'builtin-opensees'
          ).replace('builtin-', '');
          const r = read(`models/${a.groundTruthId}.json`);
          assert.ok(
            engine === 'opensees' ? r.numerical?.result : r.commercial?.engines[engine]?.response,
            `${c.id} missing ${engine} reference`,
          );
        }
    }
    const incomplete = read('cases/beam-multi-turn-incomplete.json');
    assert.deepEqual(incomplete.references[0], []);
    assert.deepEqual(incomplete.references[1], ['beam-simple-6m']);
    assert.ok(manifest.every((m) => !m.source.startsWith('results/')));
    for (const [file, digest] of Object.entries(before))
      assert.equal(hash(path.join(corpusRoot, file)), digest, `Original changed: ${file}`);
    assert.equal(cases.filter((c) => c.referenceIds.length).length, 106);
  } finally {
    assert.ok(path.resolve(out).startsWith(path.join(os.tmpdir(), 'sclaw-viewer-test-')));
    fs.rmSync(out, { recursive: true, force: true });
  }
});
