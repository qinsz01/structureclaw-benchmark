import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';

export const viewerRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
export const corpusRoot = path.resolve(viewerRoot, '..');
const read = (p) => JSON.parse(fs.readFileSync(path.join(corpusRoot, p), 'utf8'));
const hash = (p) =>
  crypto
    .createHash('sha256')
    .update(fs.readFileSync(path.join(corpusRoot, p)))
    .digest('hex');
export function exportData(output = path.join(viewerRoot, 'public/data')) {
  const sources = new Set([
    'benchmark.json',
    'fixtures/ground-truth-models.json',
    'fixtures/opensees-ground-truth.json',
    'fixtures/cross-engine-ground-truth-validation.json',
  ]);
  const corpus = read('benchmark.json');
  const models = read('fixtures/ground-truth-models.json');
  const numerical = read('fixtures/opensees-ground-truth.json');
  const commercial = read('fixtures/cross-engine-ground-truth-validation.json');
  const write = (p, value) => {
    const target = path.join(output, p);
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.writeFileSync(target, JSON.stringify(value));
  };
  const copy = (p) => {
    const absolute = path.resolve(corpusRoot, p);
    if (!absolute.startsWith(corpusRoot + path.sep) || !p.startsWith('fixtures/'))
      throw new Error(`Invalid attachment: ${p}`);
    const target = path.join(output, p);
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.copyFileSync(absolute, target);
    sources.add(p);
  };
  const cases = [];
  for (const family of Object.keys(corpus.taskFamilies)) {
    for (const filename of fs
      .readdirSync(path.join(corpusRoot, 'scenarios', family))
      .filter((f) => f.endsWith('.json'))
      .sort()) {
      const source = `scenarios/${family}/${filename}`;
      sources.add(source);
      const scenario = read(source);
      if (scenario.taskFamily !== family) throw new Error(`Family mismatch: ${source}`);
      const turns = scenario.turns || [
        {
          message: scenario.message,
          engineeringSpecification: scenario.engineeringSpecification,
          assertions: scenario.expect?.assertions || [],
        },
      ];
      const references = turns.map((turn) => [
        ...new Set((turn.assertions || []).map((a) => a.groundTruthId).filter(Boolean)),
      ]);
      for (const id of references.flat())
        if (!models.some((m) => m.id === id)) throw new Error(`Missing model ${id}`);
      for (const attachment of scenario.attachments || []) copy(attachment.relPath);
      const details = { scenario, source, sourceSha256: hash(source), turns, references };
      write(`cases/${scenario.id}.json`, details);
      const text = [
        scenario.id,
        scenario.description,
        scenario.engineeringSpecification,
        ...turns.flatMap((t) => [t.message, t.engineeringSpecification]),
      ]
        .filter(Boolean)
        .join(' ');
      cases.push({
        id: scenario.id,
        description: scenario.description,
        family,
        locale: scenario.locale,
        structure: scenario.benchmarkStructureType,
        modality: scenario.inputModality,
        difficulty: scenario.difficulty,
        turnCount: turns.length,
        referenceIds: [...new Set(references.flat())],
        source,
        search: text,
      });
    }
  }
  for (const [family, counts] of Object.entries(corpus.taskFamilies)) {
    for (const locale of ['en', 'zh'])
      if (cases.filter((c) => c.family === family && c.locale === locale).length !== counts[locale])
        throw new Error(`Count mismatch: ${family}/${locale}`);
  }
  if (new Set(cases.map((c) => c.id)).size !== cases.length) throw new Error('Duplicate case ID');
  const referenced = new Set(cases.flatMap((c) => c.referenceIds));
  for (const model of models.filter((m) => referenced.has(m.id))) {
    const cross = commercial.cases.find((c) => c.provenance.sourceModelId === model.id);
    write(`models/${model.id}.json`, {
      ...model,
      numerical: numerical.models.find((n) => n.modelId === model.id) || null,
      commercial: cross || null,
    });
  }
  write(
    'thumbnails.json',
    Object.fromEntries(
      models
        .filter((m) => referenced.has(m.id))
        .map((m) => [
          m.id,
          {
            nodes: m.model.nodes,
            elements: m.model.elements,
            coordinate_system: m.model.coordinate_system,
          },
        ]),
    ),
  );
  const manifest = [...sources].sort().map((source) => ({ source, sha256: hash(source) }));
  write('index.json', { corpus, cases, modelCount: referenced.size, sources: manifest });
  console.log(
    `Exported ${cases.length} cases, ${referenced.size} referenced models, ${sources.size} hashed source files.`,
  );
  return { cases, manifest };
}
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url))
  exportData();
