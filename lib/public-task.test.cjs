'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { toPublicTask } = require('./public-task.cjs');

test('public task contains the instruction and safe delivery names without evaluator metadata', () => {
  const input = {
    id: 'MM-001', turnId: 't1', instruction: 'Analyse the supplied drawing.',
    inputBinding: { sourceHash: 'a'.repeat(64) }, responseContract: { reference: 'PRIVATE' },
    acceptance: { score: 99 },
    attachments: [{ name: 'drawing.png', path: '/private/author/drawing.png', relPath: 'author/drawing.png', source: 'edition', sha256: 'b'.repeat(64) }],
  };
  assert.deepEqual(toPublicTask(input), {
    id: 'MM-001', turnId: 't1', instruction: 'Analyse the supplied drawing.',
    attachments: [{ name: 'drawing.png', path: 'drawing.png', mimeType: 'image/png' }],
  });
  assert.equal(input.attachments[0].path, '/private/author/drawing.png');
});

test('public task supports text and DXF while retaining an empty turn attachment list', () => {
  const base = { id: 'INT-001', turnId: 't2', instruction: 'Use millimetres.' };
  assert.deepEqual(toPublicTask({ ...base, attachments: [] }), { ...base, attachments: [] });
  assert.deepEqual(toPublicTask({ ...base, attachments: [{ name: 'input.md' }, { name: 'drawing.dxf' }] }).attachments, [
    { name: 'input.md', path: 'input.md', mimeType: 'text/markdown' },
    { name: 'drawing.dxf', path: 'drawing.dxf', mimeType: 'image/vnd.dxf' },
  ]);
});

test('public task rejects unsafe or private delivery names and duplicate names', () => {
  const input = { id: 'STD-001', turnId: 't1', instruction: 'Analyse.', attachments: [] };
  for (const name of ['../drawing.png', '/tmp/input.txt', 'a/b.txt', 'a\\b.txt', '%2e%2e.txt', 'C:input.txt', '.hidden.txt', 'contract.json', 'author-audit.json', 'reference-requests.json']) {
    assert.throws(() => toPublicTask({ ...input, attachments: [{ name }] }), /attachment|name|path/i, name);
  }
  assert.throws(() => toPublicTask({ ...input, attachments: [{ name: 'drawing.png' }, { name: 'drawing.png' }] }), /duplicate/i);
});

test('public task refuses invalid task identity or missing instruction', () => {
  const valid = { id: 'STD-001', turnId: 't1', instruction: 'Analyse.', attachments: [] };
  for (const update of [{ id: '../STD-001' }, { turnId: '../t1' }, { instruction: '' }, { attachments: null }]) {
    assert.throws(() => toPublicTask({ ...valid, ...update }), /id|turn|instruction|attachment/i);
  }
});
