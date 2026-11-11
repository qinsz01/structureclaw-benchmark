import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';

test(
  'sealed 300-case trial projects original questions, actual answers, gates and distinct repair checks',
  { timeout: 180000 },
  () => {
    const root = path.resolve(import.meta.dirname, '../..');
    const output = fs.mkdtempSync(path.join(os.tmpdir(), 'codex-viewer-trial-'));
    const read = (name) => JSON.parse(fs.readFileSync(path.join(output, 'trials', name)));
    try {
      const p = spawnSync(
        'python3',
        [
          'viewer/scripts/trial-data.py',
          '--root',
          root,
          '--output',
          output,
          '--edition',
          'historical',
        ],
        { cwd: root, encoding: 'utf8', timeout: 180000 },
      );
      assert.equal(p.status, 0, p.stderr);
      const index = read('index.json');
      assert.equal(index.caseResults.length, 300);
      assert.equal(
        index.caseResults.reduce((n, c) => n + c.turns, 0),
        420,
      );
      assert.equal(index.caseResults.filter((c) => c.status === 'passed').length, 282);
      let turns = 0;
      for (const row of index.caseResults) {
        const detail = read(`cases/${row.caseId}.json`);
        assert.equal(detail.status, row.status);
        for (const turn of detail.turns) {
          turns++;
          assert.equal(turn.execution.completedTurn, true);
          assert.ok(turn.instruction.trim());
          assert.ok(turn.answer.trim());
          assert.equal(createHash('sha256').update(turn.answer).digest('hex'), turn.answerSha256);
          assert.equal(
            fs.readFileSync(path.join(output, turn.answerFile.path), 'utf8'),
            turn.answer,
          );
          assert.ok(turn.metrics.length);
          for (const a of [...turn.attachments, ...turn.artifacts]) {
            assert.match(a.path, /^trials\/files\/[a-f0-9]{64}\.[a-z]+$/);
            assert.equal(
              createHash('sha256')
                .update(fs.readFileSync(path.join(output, a.path)))
                .digest('hex'),
              a.sha256,
            );
          }
        }
      }
      assert.equal(turns, 420);
      const original = read('cases/INT-056.json');
      const repair = read('repair-INT-056.json');
      assert.equal(original.status, 'agent_failure');
      assert.equal(repair.status, 'passed');
      assert.equal(repair.sutCommit, 'db3c0b1da44fe668a6037a6c2e7f068d14354539');
      assert.notEqual(repair.sutCommit, index.sutCommit);
      assert.equal(
        original.turns[1].instruction,
        'Increase the crane load by 20% and give the revised response.',
      );
      assert.match(repair.turns[1].instruction, /not yet been decided/);
      assert.match(repair.turns[1].answer, /Both components/i);
      assert.equal(repair.artifacts.length, 3);
      for (const a of repair.artifacts) {
        const b = fs.readFileSync(path.join(output, a.path));
        assert.equal(createHash('sha256').update(b).digest('hex'), a.sha256);
      }
      assert.equal(index.repairs['STD-080'].kind, 'adapter-regression');
      assert.equal(index.repairs['STD-080'].quantities, 396);
      assert.equal(read('cases/STD-080.json').status, 'agent_failure');
      assert.ok(read('cases/STD-088.json').artifacts.some((a) => a.name === 'report-t1.md'));
      assert.ok(read('cases/MM-061.json').turns[0].artifacts.some((a) => a.name.endsWith('.png')));
    } finally {
      fs.rmSync(output, { recursive: true, force: true });
    }
  },
);

test(
  'diversity release exports all 420 original calls with source-specific retests and separate baseline',
  { timeout: 240000 },
  () => {
    const root = path.resolve(import.meta.dirname, '../..');
    const output = fs.mkdtempSync(path.join(os.tmpdir(), 'codex-diversity-viewer-'));
    const read = (name) => JSON.parse(fs.readFileSync(path.join(output, 'trials', name)));
    try {
      const p = spawnSync(
        'python3',
        ['viewer/scripts/trial-data.py', '--root', root, '--output', output],
        { cwd: root, encoding: 'utf8', timeout: 240000 },
      );
      assert.equal(p.status, 0, p.stderr);
      const index = read('index.json');
      assert.equal(index.edition, 'section-diversity-v1');
      assert.deepEqual(index.cases, { completed: 300, passed: 292, notPassed: 8 });
      assert.deepEqual(index.turns, { completed: 420, passed: 412, notPassed: 8 });
      assert.equal(index.diversity.maximumJCases, 26);
      assert.equal(index.diversity.distinctJ, 146);
      assert.equal(index.historical.cases.passed, 282);
      assert.equal(read('historical/index.json').cases.passed, 282);
      const trials = {};
      let turns = 0;
      for (const row of index.caseResults) {
        const detail = read(`cases/${row.caseId}.json`);
        trials[detail.sourceTrial] = (trials[detail.sourceTrial] || 0) + 1;
        assert.equal(detail.revision, 'r23');
        assert.equal(detail.status, row.status);
        for (const t of detail.turns) {
          turns++;
          assert.ok(t.execution.completedTurn && t.instruction.trim() && t.answer.trim());
          assert.equal(createHash('sha256').update(t.answer).digest('hex'), t.answerSha256);
          assert.equal(fs.readFileSync(path.join(output, t.answerFile.path), 'utf8'), t.answer);
          for (const a of [...t.attachments, ...t.artifacts]) {
            assert.equal(
              createHash('sha256')
                .update(fs.readFileSync(path.join(output, a.path)))
                .digest('hex'),
              a.sha256,
            );
          }
        }
      }
      assert.equal(turns, 420);
      assert.deepEqual(trials, { r2: 270, r6: 29, r7: 1 });
      assert.match(read('cases/STD-039.json').turns[0].instruction, /0\.0161472/);
      assert.match(read('historical/cases/STD-039.json').turns[0].instruction, /0\.012/);
      assert.equal(read('cases/MM-090.json').sourceTrial, 'r6');
      assert.equal(read('cases/MM-090.json').attribution.category, 'candidate_input_transcription');
      assert.equal(read('cases/STD-089.json').status, 'passed');
      assert.equal(read('cases/STD-091.json').status, 'passed');
    } finally {
      fs.rmSync(output, { recursive: true, force: true });
    }
  },
);
