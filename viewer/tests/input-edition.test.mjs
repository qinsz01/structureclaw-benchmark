import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import provider from '../../lib/corpus-provider.cjs';
import {
  createResearchReader,
  readResearchCase,
  summarizePublicInputReviews,
} from '../scripts/research-data.mjs';

const root = path.resolve(new URL('../..', import.meta.url).pathname);
const manifest = JSON.parse(fs.readFileSync(path.join(root, 'corpora/research-300/manifest.json')));
const plan = JSON.parse(fs.readFileSync(path.join(root, manifest.sourcePlan.path)));

test('current edition review counts exclude historical and invalid evidence from reviewed totals', () => {
  const cases = [
    { inputEdition: 'current', status: 'passed', verified: true },
    { inputEdition: 'current', status: 'failed', verified: true },
    { inputEdition: 'current', status: 'partial', verified: true },
    { inputEdition: 'current', status: 'pending', verified: false },
    { inputEdition: 'current', status: 'invalid', verified: false },
    { inputEdition: 'concise-v1', status: 'passed', verified: true },
  ].map((publicInputReview) => ({ detail: { publicInputReview } }));
  cases.push({ detail: {} });
  assert.deepEqual(summarizePublicInputReviews(cases), {
    edition: 'current',
    total: 5,
    reviewed: 3,
    passed: 1,
    failed: 1,
    partial: 1,
    pending: 1,
    invalid: 1,
  });
});

test('current input never inherits archived review passes', () => {
  const cases = Array.from({ length: 100 }, () => ({
    detail: { turns: [{ inputEdition: 'visual-v2' }], publicInputReview: { inputEdition: 'visual-v2', status: 'passed', verified: true } },
  }));
  cases.unshift({
    detail: {
      turns: [{ inputEdition: 'current' }],
      publicInputReview: { inputEdition: 'current', status: 'pending', verified: false },
    },
  });
  assert.deepEqual(summarizePublicInputReviews(cases), {
    edition: 'current',
    total: 1,
    reviewed: 0,
    passed: 0,
    failed: 0,
    partial: 0,
    pending: 1,
    invalid: 0,
  });
});

test('viewer verifies original sources and uses the sole current input for every family', () => {
  const reader = createResearchReader(root);
  const corpus = provider.loadCorpus({ corpus: 'research-300', root });
  const evidence = (name) => {
    const source = `corpora/research-300/evidence/${name}`;
    const document = reader.json(source);
    return { document, source, sha256: reader.sources.get(source).sha256 };
  };
  const diagnostics = evidence('commercial-native-diagnostic-comparison.json');
  diagnostics.openSees = evidence('reference-cross-check.json');
  for (const id of ['STD-001', 'INT-002', 'MM-001', 'MM-021']) {
    const entry = manifest.cases.find((item) => item.id === id);
    const record = provider.loadCase(corpus, id);
    let result;
    assert.doesNotThrow(() => {
      result = readResearchCase(
        reader,
        corpus,
        entry,
        plan.cases.find((item) => item.id === id),
        diagnostics,
      );
    }, `${id}: current edition must not invalidate frozen native source provenance`);
    assert.equal(result.detail.sourceHash, entry.sourceHash);
    for (const [index, turn] of result.detail.turns.entries()) {
      const input = provider.getPublicTurnInput(record, index);
      assert.equal(turn.inputEdition, 'current');
      assert.deepEqual(turn.inputBinding, input.inputBinding);
      assert.equal(turn.publicInputSha256, input.publicInputSha256);
      assert.equal(turn.instruction, input.instruction);
      assert.equal(
        turn.attachments.some((attachment) => attachment.name.endsWith('.svg')),
        false,
      );
      assert.equal(turn.attachments.length, input.attachments.length);
      assert.ok(turn.attachments.length <= 1);
      if (id.startsWith('MM-')) {
        assert.equal(turn.attachments.length, 1);
        assert.match(turn.attachments[0].name, /^drawing(?:-t\d+)?\.(png|dxf)$/);
      }
      assert.deepEqual(
        turn.responseContract,
        provider.getFrozenPublicTurnInput(record, index).responseContract,
      );
      for (const [i, attachment] of turn.attachments.entries()) {
        assert.equal(
          attachment.source,
          path.relative(root, input.attachments[i].path).split(path.sep).join('/'),
        );
        assert.equal(attachment.sha256, input.attachments[i].sha256);
        assert.deepEqual(
          reader.bytes(attachment.source, attachment.sha256).bytes,
          fs.readFileSync(input.attachments[i].path),
        );
      }
    }
    if (id === 'MM-021') {
      assert.equal(result.detail.turns[0].state, null);
      assert.equal(result.detail.turns[0].quantities.length, 0);
      assert.ok(
        result.detail.turns[0].attachments.every((a) => !/confirmed|resolved/.test(a.name)),
      );
      assert.equal(result.detail.turns[0].attachments[0].name, 'drawing.png');
      assert.equal(result.detail.turns[1].attachments[0].name, 'drawing-t2.png');
    }
    assert.ok(
      result.detail.sources.some((source) =>
        source.source.includes('public-inputs/manifest.json'),
      ),
    );
    assert.ok(
      result.detail.sources.some(
        (source) => source.source === 'scripts/research300/public_input_clean.py',
      ),
    );
    assert.ok(
      result.detail.sources.some(
        (source) => source.source === 'scripts/research300/render_public_visual.cjs',
      ),
    );
    assert.ok(
      result.detail.sources.some((source) => source.source.endsWith(`${id}/author-audit.json`)),
    );
    assert.equal(result.detail.publicInputReview.inputEdition, 'current');
    assert.equal(result.detail.publicInputReview.status, 'pending');
    assert.deepEqual(result.detail.status, result.summary.status);
  }
});
