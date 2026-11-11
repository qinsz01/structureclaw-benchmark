// Retain pure math regression coverage without exporting any legacy case into
// the research-only site. These fixtures are read only by Node tests.
import fs from 'node:fs';
import crypto from 'node:crypto';
const read = (relative) => JSON.parse(fs.readFileSync(new URL(relative, import.meta.url), 'utf8'));
const models = read('../../fixtures/ground-truth-models.json');
const numerical = read('../../fixtures/opensees-ground-truth.json');
const commercial = read('../../fixtures/cross-engine-ground-truth-validation.json');
const derived = read('../derived/member-responses.json');
export const referenceIds = models.filter((m) => derived.entries[m.id]).map((m) => m.id);
export function legacyReference(id) {
  const model = models.find((m) => m.id === id);
  if (!model) throw Error(`Missing legacy test fixture ${id}`);
  const reference = {
    ...model,
    numerical: numerical.models.find((n) => n.modelId === id) || null,
    commercial: commercial.cases.find((c) => c.provenance.sourceModelId === id) || null,
  };
  const sourceSnapshot = JSON.stringify({
    model: reference.model,
    result: reference.numerical?.result,
    factors: reference.numerical?.analysisSelection?.factors,
  });
  const entry = derived.entries[id];
  if (entry?.inputSha256 !== crypto.createHash('sha256').update(sourceSnapshot).digest('hex'))
    throw Error(`Stale legacy math fixture ${id}`);
  return structuredClone({
    ...reference,
    derivedMemberResponses: { ...entry, sourceSnapshot, algorithm: derived.algorithm },
  });
}
