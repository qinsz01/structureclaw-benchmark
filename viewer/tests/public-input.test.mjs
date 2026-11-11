import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import ts from 'typescript';

const file = new URL('../src/public-input.ts', import.meta.url);
const api = fs.existsSync(file)
  ? await import(
      `data:text/javascript;base64,${Buffer.from(
        ts.transpileModule(fs.readFileSync(file, 'utf8'), {
          compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ES2022 },
        }).outputText,
      ).toString('base64')}`
    )
  : {};

test('a downloaded public turn contains the task and usable attachment links without answer hints or audit metadata', () => {
  assert.equal(typeof api.publicInputForDownload, 'function');
  const turn = {
    id: 't1',
    state: null,
    expectation: 'clarify',
    instruction: 'The load is 10 with no unit. Ask for the unit before analysis.',
    inputEdition: 'current',
    publicInputSha256: 'a'.repeat(64),
    inputBinding: { baseSourceHash: 'b'.repeat(64), source: '/private/frozen.json' },
    responseContract: { expectedQuestion: 'forceUnit' },
    unresolvedFields: ['forceUnit'],
    quantities: [{ value: -20 }],
    attachments: [
      {
        name: 'drawing.png',
        path: 'attachments/MM-001/t1/drawing.png',
        mimeType: 'image/png',
        source: '/private/corpus/drawing.png',
        sha256: 'c'.repeat(64),
        bytes: 1200,
      },
    ],
  };
  assert.deepEqual(api.publicInputForDownload('MM-001', turn), {
    caseId: 'MM-001',
    turnId: 't1',
    instruction: 'The load is 10 with no unit. Ask for the unit before analysis.',
    attachments: [
      {
        name: 'drawing.png',
        path: 'drawing.png',
        mimeType: 'image/png',
      },
    ],
  });
});

test('public downloads never expose an absolute repository path in attachment descriptors', () => {
  assert.equal(typeof api.publicInputForDownload, 'function');
  for (const privatePath of [
    '/mnt/private/input.md',
    'C:\\private\\input.md',
    '../private/input.md',
  ]) {
    assert.deepEqual(
      api.publicInputForDownload('STD-001', {
        id: 't2',
        instruction: 'Use the updated load.',
        attachments: [{ name: 'input.md', path: privatePath, mimeType: 'text/markdown' }],
      }),
      {
        caseId: 'STD-001',
        turnId: 't2',
        instruction: 'Use the updated load.',
        attachments: [{ name: 'input.md', path: 'input.md', mimeType: 'text/markdown' }],
      },
    );
  }
});
