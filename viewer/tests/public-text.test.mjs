import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import ts from 'typescript';

const file = new URL('../src/public-text.ts', import.meta.url);
const api = fs.existsSync(file)
  ? await import(
      `data:text/javascript;base64,${Buffer.from(
        ts.transpileModule(fs.readFileSync(file, 'utf8'), {
          compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ES2022 },
        }).outputText,
      ).toString('base64')}`
    )
  : {};

test('public appendix tables retain exact signed numbers, units and escaped cells', () => {
  assert.equal(typeof api.parsePublicText, 'function');
  const blocks = api.parsePublicText(
    '# 材料\n\n| id | E [MPa] | note |\n| --- | ---: | --- |\n| M1 | 206000.00000000003 | A\\|B |\n| M2 | -0 | x\\\\y |\n\n其余条件按图。',
  );
  assert.deepEqual(blocks, [
    { type: 'heading', level: 1, text: '材料' },
    {
      type: 'table',
      headers: ['id', 'E [MPa]', 'note'],
      rows: [
        ['M1', '206000.00000000003', 'A|B'],
        ['M2', '-0', 'x\\y'],
      ],
    },
    { type: 'paragraph', text: '其余条件按图。' },
  ]);
});

test('ordinary pipes, malformed tables and HTML remain literal public text', () => {
  assert.equal(typeof api.parsePublicText, 'function');
  const value =
    'Use case:D | combination:D\n<script>throw new Error("unsafe")</script>\n\n| a | b |\n| --- |\n| 1 | 2 |';
  const blocks = api.parsePublicText(value);
  assert.deepEqual(blocks, [
    {
      type: 'paragraph',
      text: 'Use case:D | combination:D\n<script>throw new Error("unsafe")</script>',
    },
    { type: 'paragraph', text: '| a | b |\n| --- |\n| 1 | 2 |' },
  ]);
});

test('editorial table escapes decode once into safe text, without changing literal entity strings', () => {
  const blocks = api.parsePublicText(
    '| norm | note | literal |\n| --- | --- | --- |\n| &#124;r×1&#124; | &lt;script&gt; &amp; x | &amp;#124; |',
  );
  assert.deepEqual(blocks, [
    {
      type: 'table',
      headers: ['norm', 'note', 'literal'],
      rows: [['|r×1|', '<script> & x', '&#124;']],
    },
  ]);
});

test('public requests preserve list order, line breaks and an incomplete table row', () => {
  assert.equal(typeof api.parsePublicText, 'function');
  const blocks = api.parsePublicText(
    '任务\r\n条件\r\n\r\n- 左侧 V3\r\n- 右侧 V3\r\n\r\n| id | value |\r\n| --- | --- |\r\n| first | 1 |\r\n| missing |',
  );
  assert.deepEqual(blocks, [
    { type: 'paragraph', text: '任务\n条件' },
    { type: 'list', items: ['左侧 V3', '右侧 V3'] },
    { type: 'table', headers: ['id', 'value'], rows: [['first', '1']] },
    { type: 'paragraph', text: '| missing |' },
  ]);
});
