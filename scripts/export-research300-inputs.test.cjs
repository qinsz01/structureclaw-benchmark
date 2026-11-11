'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { sha256 } = require('../lib/corpus-provider.cjs');
const { exportResearch300Inputs } = require('./export-research300-inputs.cjs');

const PNG = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4//8/AAX+Av4N70a4AAAAAElFTkSuQmCC', 'base64');
const DXF = Buffer.from('0\nSECTION\n2\nENTITIES\n0\nLINE\n10\n0\n20\n0\n11\n6\n21\n0\n0\nENDSEC\n0\nEOF\n');
const SECRET = 'PRIVATE_ANSWER_SENTINEL_731_924';
const write = (file, bytes) => { fs.mkdirSync(path.dirname(file), { recursive: true }); fs.writeFileSync(file, bytes); };
const json = (file, value) => write(file, JSON.stringify(value, null, 2) + '\n');
const read = file => JSON.parse(fs.readFileSync(file, 'utf8'));
const files = (dir, prefix = '') => fs.readdirSync(path.join(dir, prefix), { withFileTypes: true }).flatMap(entry => {
  const name = prefix ? `${prefix}/${entry.name}` : entry.name;
  return entry.isDirectory() ? files(dir, name) : [name];
}).sort();

// The provider double supplies authenticated turn envelopes. The exporter uses
// real files, source allowlists, public-file guards, hashes and publication code.
function fixture(t) {
  const base = fs.mkdtempSync(path.join(os.tmpdir(), 'research300-export-'));
  t.after(() => fs.rmSync(base, { recursive: true, force: true }));
  const root = path.join(base, 'repo');
  const output = path.join(base, 'delivery');
  const definitions = [
    { id: 'STD-001', family: 'standard', turns: [['Analyse the beam in the input table.', 'input.md', Buffer.from('# Beam\nSpan: 6 m.\n')]] },
    { id: 'INT-001', family: 'interaction', turns: [['Analyse this column.', 'input.md', Buffer.from('# Column\nHeight: 5 m.\n')], ['Keep the model; report displacement in mm.']] },
    { id: 'MM-001', family: 'multimodal', turns: [['Analyse this drawing.', 'drawing.png', PNG], ['Use the revised CAD drawing.', 'revised.dxf', DXF]] },
  ];
  const records = new Map();
  for (const definition of definitions) {
    const caseDir = path.join(root, 'corpora/research-300/cases', definition.id);
    const editionDir = path.join(root, 'corpora/research-300/public-inputs', definition.id);
    write(path.join(caseDir, 'model-state-1.json'), JSON.stringify({ schema_version: '2.2.0', nodes: [], elements: [], load_cases: [], secret: SECRET }));
    write(path.join(caseDir, 'independent-reference.json'), SECRET);
    write(path.join(editionDir, 'author-audit.json'), SECRET);
    const turns = definition.turns.map(([instruction, name, bytes], index) => {
      const attachments = [];
      if (name) {
        write(path.join(editionDir, name), bytes);
        attachments.push({ name, relPath: name, path: path.join(editionDir, name), source: 'edition', sha256: sha256(bytes) });
      }
      return { id: definition.id, turnId: `t${index + 1}`, instruction, attachments,
        inputEdition: 'current', inputBinding: { sourceHash: 'a'.repeat(64), private: SECRET },
        responseContract: { quantities: [{ id: SECRET, value: 731.924 }] },
        reference: SECRET, rubric: SECRET, acceptance: { score: 1 } };
    });
    const record = { id: definition.id, corpus: 'research-300', root, caseDir, editionDir,
      contract: { id: definition.id, family: definition.family, language: 'English', plannedEngine: 'OpenSees', attachments: [], modelStates: ['model-state-1.json'], turns: turns.map(turn => ({ id: turn.turnId, attachments: [] })) }, turns };
    records.set(record.id, record);
  }
  const syncBundles = () => {
    for (const record of records.values()) json(path.join(record.editionDir, 'input.json'), {
      schemaVersion: 1, edition: 'current', caseId: record.id,
      turns: record.turns.map(turn => ({ id: turn.turnId, instruction: turn.instruction, attachments: turn.attachments.map(a => ({ name: a.name, source: a.source, path: a.relPath, sha256: a.sha256 })) })),
    });
  };
  syncBundles();
  const provider = {
    loadCorpus: () => ({ id: 'research-300', root, cases: [...records.values()].map(({ id, caseDir }) => ({ id, caseDir })) }),
    loadCase: (_corpus, id) => records.get(id),
    getPublicTurnInput: (record, index) => record.turns[index],
  };
  const run = (options = {}) => exportResearch300Inputs({ root, output, provider, expectedCounts: { cases: 3, turns: 5 }, ...options });
  return { root, output, records, provider, run, syncBundles, base };
}

function assertCleanJSON(value) {
  if (typeof value === 'string') {
    assert.doesNotMatch(value, /[a-f0-9]{64}|PRIVATE_ANSWER_SENTINEL|^\/|[A-Za-z]:[\\/]/);
    return;
  }
  if (!value || typeof value !== 'object') return;
  for (const [key, child] of Object.entries(value)) {
    assert.doesNotMatch(key, /hash|sha256|binding|reference|rubric|score|acceptance|responseContract|provenance/i);
    assertCleanJSON(child);
  }
}

test('standalone export delivers minimal tasks, exact binary bytes and no hidden files', t => {
  const f = fixture(t);
  const result = f.run();
  assert.equal(result.cases, 3);
  assert.equal(result.turns, 5);
  assert.deepEqual(files(f.output), [
    'README.md', 'cases/INT-001/input.md', 'cases/INT-001/task.json',
    'cases/MM-001/drawing.png', 'cases/MM-001/revised.dxf', 'cases/MM-001/task.json',
    'cases/STD-001/input.md', 'cases/STD-001/task.json', 'index.json',
  ]);
  assert.deepEqual(read(path.join(f.output, 'index.json')), { cases: [
    { id: 'INT-001', family: 'interaction', language: 'English', engine: 'OpenSees', turns: 2 },
    { id: 'MM-001', family: 'multimodal', language: 'English', engine: 'OpenSees', turns: 2 },
    { id: 'STD-001', family: 'standard', language: 'English', engine: 'OpenSees', turns: 1 },
  ] });
  assert.deepEqual(fs.readFileSync(path.join(f.output, 'cases/MM-001/drawing.png')), PNG);
  assert.deepEqual(fs.readFileSync(path.join(f.output, 'cases/MM-001/revised.dxf')), DXF);
  for (const name of files(f.output)) {
    const bytes = fs.readFileSync(path.join(f.output, name));
    assert.equal(bytes.includes(Buffer.from(SECRET)), false, name);
    assert.doesNotMatch(name, /[a-f0-9]{64}/i);
    if (!name.endsWith('.png')) assert.doesNotMatch(bytes.toString('utf8'), /[a-f0-9]{64}|sha256|inputBinding|responseContract/i, name);
    if (name.endsWith('.json')) assertCleanJSON(read(path.join(f.output, name)));
  }
});

test('later turn attachments are never listed in an earlier task turn', t => {
  const f = fixture(t);
  f.run();
  assert.deepEqual(read(path.join(f.output, 'cases/MM-001/task.json')), { caseId: 'MM-001', turns: [
    { id: 't1', instruction: 'Analyse this drawing.', attachments: ['drawing.png'] },
    { id: 't2', instruction: 'Use the revised CAD drawing.', attachments: ['revised.dxf'] },
  ] });
  assert.deepEqual(read(path.join(f.output, 'cases/INT-001/task.json')).turns[1].attachments, []);
});

test('single-case released-turn export omits all future instructions and attachment files', t => {
  const f = fixture(t);
  const provider = { ...f.provider, loadCorpus: () => ({ ...f.provider.loadCorpus(), cases: [{ id: 'MM-001' }] }) };
  f.run({ provider, throughTurn: 't1', expectedCounts: { cases: 1, turns: 1 } });
  assert.deepEqual(files(f.output), ['README.md', 'cases/MM-001/drawing.png', 'cases/MM-001/task.json', 'index.json']);
  assert.deepEqual(read(path.join(f.output, 'cases/MM-001/task.json')), { caseId: 'MM-001', turns: [
    { id: 't1', instruction: 'Analyse this drawing.', attachments: ['drawing.png'] },
  ] });
  assert.equal(read(path.join(f.output, 'index.json')).cases[0].turns, 1);
  f.run({ provider, throughTurn: 't2', expectedCounts: { cases: 1, turns: 2 } });
  assert.equal(read(path.join(f.output, 'cases/MM-001/task.json')).turns.length, 2);
  assert.ok(fs.existsSync(path.join(f.output, 'cases/MM-001/revised.dxf')));
});

test('released-turn export rejects ambiguous case selections and unknown turns without output residue', t => {
  const f = fixture(t);
  assert.throws(() => f.run({ throughTurn: 't1' }), /single-case selection/);
  const provider = { ...f.provider, loadCorpus: () => ({ ...f.provider.loadCorpus(), cases: [{ id: 'MM-001' }] }) };
  assert.throws(() => f.run({ provider, throughTurn: 't9', expectedCounts: { cases: 1, turns: 1 } }), /Unknown released turn/);
  assert.equal(fs.existsSync(f.output), false);
  assert.deepEqual(fs.readdirSync(f.base), ['repo']);
});

test('re-export replaces a recognized dirty delivery and preserves the previous delivery on validation failure', t => {
  const f = fixture(t);
  f.run();
  write(path.join(f.output, 'forgotten-private.txt'), SECRET);
  f.run();
  assert.equal(fs.existsSync(path.join(f.output, 'forgotten-private.txt')), false);
  const previous = fs.readFileSync(path.join(f.output, 'cases/STD-001/input.md'));
  write(f.records.get('STD-001').turns[0].attachments[0].path, '# Modified without rebinding\n');
  assert.throws(() => f.run(), /hash|digest|mismatch/i);
  assert.deepEqual(fs.readFileSync(path.join(f.output, 'cases/STD-001/input.md')), previous);
  assert.deepEqual(fs.readdirSync(f.base).sort(), ['delivery', 'repo']);
});

test('unrecognized existing output and all corpus source destinations are protected', t => {
  const f = fixture(t);
  fs.mkdirSync(f.output);
  write(path.join(f.output, 'keep.txt'), 'User file');
  assert.throws(() => f.run(), /owned|recogniz|existing|export/i);
  assert.equal(fs.readFileSync(path.join(f.output, 'keep.txt'), 'utf8'), 'User file');
  for (const output of [f.root, f.base, path.join(f.root, 'corpora/research-300/new-delivery'), f.records.get('MM-001').editionDir]) {
    assert.throws(() => f.run({ output }), /source|root|ancestor|destination|owned|export/i, output);
  }
});

test('source or destination symlinks cannot escape the export boundary', t => {
  const f = fixture(t);
  const attachment = f.records.get('STD-001').turns[0].attachments[0];
  const outside = path.join(f.base, 'outside.md');
  fs.copyFileSync(attachment.path, outside);
  fs.unlinkSync(attachment.path);
  fs.symlinkSync(outside, attachment.path);
  assert.throws(() => f.run(), /symlink/i);
  fs.unlinkSync(attachment.path);
  fs.copyFileSync(outside, attachment.path);
  fs.symlinkSync(path.join(f.base, 'outside-delivery'), f.output);
  assert.throws(() => f.run(), /symlink/i);
  fs.unlinkSync(f.output);
  f.run();
  fs.symlinkSync(outside, path.join(f.output, 'stray-link.md'));
  assert.throws(() => f.run(), /symlink/i);
  assert.equal(fs.readFileSync(outside, 'utf8'), '# Beam\nSpan: 6 m.\n');
});

test('attachment traversal, arbitrary source files and unapproved bundle entries are rejected', t => {
  const f = fixture(t);
  const attachment = f.records.get('STD-001').turns[0].attachments[0];
  const original = { ...attachment };
  for (const relPath of ['../input.md', '/tmp/input.md', 'a\\b.md', '%2e%2e/input.md']) {
    attachment.relPath = relPath;
    f.syncBundles();
    assert.throws(() => f.run(), /relative|path|attachment|source/i, relPath);
  }
  Object.assign(attachment, original);
  attachment.path = path.join(f.base, 'elsewhere.md');
  write(attachment.path, '# Beam\nSpan: 6 m.\n');
  f.syncBundles();
  assert.throws(() => f.run(), /source|path|attachment/i);
  Object.assign(attachment, original);
  f.syncBundles();
  const bundleFile = path.join(f.records.get('STD-001').editionDir, 'input.json');
  const bundle = read(bundleFile);
  bundle.turns[0].attachments = [];
  json(bundleFile, bundle);
  assert.throws(() => f.run(), /allowlist|bundle|public|attachment/i);
});

test('a hardlinked private file and hash clutter cannot become public input', t => {
  const f = fixture(t);
  const record = f.records.get('STD-001');
  const attachment = record.turns[0].attachments[0];
  fs.unlinkSync(attachment.path);
  fs.linkSync(path.join(record.caseDir, 'independent-reference.json'), attachment.path);
  attachment.sha256 = sha256(fs.readFileSync(attachment.path));
  f.syncBundles();
  assert.throws(() => f.run(), /private/i);
  fs.unlinkSync(attachment.path);
  write(attachment.path, '# Beam\nSpan: 6 m.\n');
  attachment.sha256 = sha256(fs.readFileSync(attachment.path));
  record.turns[0].instruction += ' sha256=' + 'a'.repeat(64);
  f.syncBundles();
  assert.throws(() => f.run(), /hash|digest|metadata|checksum/i);
});

test('an instruction cannot copy a private answer file', t => {
  const f = fixture(t);
  f.records.get('STD-001').turns[0].instruction = SECRET;
  f.syncBundles();
  assert.throws(() => f.run(), /private/i);
  assert.equal(fs.existsSync(f.output), false);
});

test('clean edition and one file per turn are enforced before publication', t => {
  const f = fixture(t);
  const record = f.records.get('MM-001');
  record.turns[0].inputEdition = 'visual-v2';
  assert.throws(() => f.run(), /current|edition/i);
  record.turns[0].inputEdition = 'current';
  record.turns[0].attachments.push(record.turns[1].attachments[0]);
  f.syncBundles();
  assert.throws(() => f.run(), /one|single|attachment/i);
  assert.equal(fs.existsSync(f.output), false);
});

test('a later MM turn also requires exactly one drawing', t => {
  const f = fixture(t);
  f.records.get('MM-001').turns[1].attachments = [];
  f.syncBundles();
  assert.throws(() => f.run(), /one|single|drawing|attachment/i);
  assert.equal(fs.existsSync(f.output), false);
});

test('public text attachment bytes cannot carry internal hashes even when their bindings match', t => {
  const f = fixture(t);
  const attachment = f.records.get('STD-001').turns[0].attachments[0];
  write(attachment.path, '# Beam\nSpan: 6 m.\nsourceHash: ' + 'f'.repeat(64) + '\n');
  attachment.sha256 = sha256(fs.readFileSync(attachment.path));
  f.syncBundles();
  assert.throws(() => f.run(), /hash|digest|metadata|checksum/i);
  assert.equal(fs.existsSync(f.output), false);
});

test('original DXF copies cannot bypass the sole canonical input allowlist', t => {
  const f = fixture(t);
  const record = f.records.get('MM-001');
  const attachment = record.turns[1].attachments[0];
  attachment.source = 'frozen';
  attachment.path = path.join(record.caseDir, attachment.relPath);
  write(attachment.path, DXF);
  record.contract.attachments.push(attachment.relPath);
  record.contract.turns[1].attachments.push(attachment.relPath);
  f.syncBundles();
  assert.throws(() => f.run(), /source/i);
  assert.equal(fs.existsSync(f.output), false);
});

test('a later drawing cannot overwrite an earlier drawing with the same delivery name', t => {
  const f = fixture(t);
  const record = f.records.get('MM-001');
  record.turns[1].attachments = [{ name: 'drawing.png', relPath: 'revised/drawing.png', source: 'edition',
    path: path.join(record.editionDir, 'revised/drawing.png'), sha256: sha256(PNG) }];
  write(record.turns[1].attachments[0].path, PNG);
  f.syncBundles();
  assert.throws(() => f.run(), /delivery name|different.*source/i);
  assert.equal(fs.existsSync(f.output), false);
});

test('default export refuses an incomplete corpus and the CLI requires an explicit output', t => {
  const f = fixture(t);
  assert.throws(() => exportResearch300Inputs({ root: f.root, output: f.output, provider: f.provider }), /300|complete|count/i);
  assert.equal(fs.existsSync(f.output), false);
  const script = path.resolve(__dirname, 'export-research300-inputs.cjs');
  const missing = spawnSync(process.execPath, [script, '--root', f.root], { encoding: 'utf8' });
  assert.notEqual(missing.status, 0);
  assert.match(missing.stderr, /--output/);
  const help = spawnSync(process.execPath, [script, '--help'], { encoding: 'utf8' });
  assert.equal(help.status, 0, help.stderr);
  assert.match(help.stdout, /--output/);
});
