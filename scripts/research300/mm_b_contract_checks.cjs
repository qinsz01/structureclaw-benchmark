#!/usr/bin/env node
'use strict';

// Validate only this author shard. Mutation fixtures live in a temporary directory;
// neither the selected central validator nor authored case files are modified.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { createHash } = require('node:crypto');

const readJson = file => JSON.parse(fs.readFileSync(file, 'utf8'));
const writeJson = (file, value) => fs.writeFileSync(file, JSON.stringify(value, null, 2) + '\n');
const hashFile = file => createHash('sha256').update(fs.readFileSync(file)).digest('hex');
const options = { root: path.resolve(__dirname, '../..'), validator: process.env.RESEARCH300_VALIDATOR };
for (let i = 2; i < process.argv.length; i++) {
  const flag = process.argv[i];
  if (flag === '--help') {
    console.log('Usage: node mm_b_contract_checks.cjs [--root ROOT] [--validator FILE] [--output RECEIPT.json]');
    console.log('Validator defaults to RESEARCH300_VALIDATOR, then ROOT/lib/research300-validation.cjs.');
    process.exit(0);
  }
  if (!['--root', '--validator', '--output'].includes(flag) || !process.argv[i + 1] || process.argv[i + 1].startsWith('--')) {
    throw new Error(`Unknown option or missing value: ${flag}`);
  }
  options[flag.slice(2)] = process.argv[++i];
}
options.root = path.resolve(options.root);
options.validator = path.resolve(options.validator || path.join(options.root, 'lib/research300-validation.cjs'));
const validator = require(options.validator);
assert.equal(typeof validator.validateResearchCase, 'function', 'Validator must expose validateResearchCase');
const planFile = path.join(options.root, validator.PLAN_PATH || 'planning/capability-coverage-300.json');
const plan = readJson(planFile);
const ids = Array.from({ length: 50 }, (_, i) => `MM-${String(i + 51).padStart(3, '0')}`);
const sourceDir = id => path.join(options.root, 'corpora/research-300/cases', id);
const planCase = id => plan.cases.find(c => c.id === id);
const validate = (id, caseDir = sourceDir(id), stage = 'authored') => validator.validateResearchCase({
  root: options.root, caseDir, planCase: planCase(id), stage,
});
const cases = ids.map(id => {
  const result = validate(id);
  const row = {
    id, authored: result.authored, referenceReady: result.referenceReady,
    accepted: result.accepted, inputReviewed: result.inputReviewed,
    nativeVerified: result.nativeVerified, agentStatus: result.agentStatus,
    errors: result.errors, referenceErrors: result.referenceErrors,
    acceptanceErrors: result.acceptanceErrors,
  };
  if (result.authored && typeof validator.sourceHash === 'function') {
    row.sourceHash = validator.sourceHash(sourceDir(id), readJson(path.join(sourceDir(id), 'contract.json')));
  }
  return row;
});
const regressions = [];
const scratch = fs.mkdtempSync(path.join(os.tmpdir(), 'mm-b-contract-checks-'));

function fixture(label, id = 'MM-051') {
  const caseDir = path.join(scratch, label, id);
  fs.mkdirSync(path.dirname(caseDir), { recursive: true });
  fs.cpSync(sourceDir(id), caseDir, { recursive: true });
  return { id, caseDir };
}

function mutateContract(caseDir, change) {
  const filename = path.join(caseDir, 'contract.json');
  const contract = readJson(filename);
  change(contract);
  writeJson(filename, contract);
}

function regression(name, test) {
  try {
    const evidence = test();
    regressions.push({ name, passed: true, ...evidence });
  } catch (error) {
    regressions.push({ name, passed: false, error: error.message });
  }
}

function rejectMutation(name, mutate, expected, id = 'MM-051') {
  regression(name, () => {
    const f = fixture(name, id);
    mutate(f.caseDir);
    const result = validate(f.id, f.caseDir);
    assert.equal(result.authored, false, `${name}: mutation unexpectedly passed authored validation`);
    assert(result.errors.some(message => expected.test(message)), `${name}: expected ${expected}, got ${JSON.stringify(result.errors)}`);
    return { expectedError: expected.source, errors: result.errors };
  });
}

try {
  if (cases.every(c => c.authored)) {
    regression('unchanged-copy-remains-authored', () => {
      const f = fixture('control');
      const result = validate(f.id, f.caseDir);
      assert.equal(result.authored, true, JSON.stringify(result.errors));
      assert.equal(result.valid, true);
      return { errors: result.errors };
    });
    rejectMutation('unknown-turn-target', caseDir => mutateContract(caseDir, contract => {
      contract.requirementCoverage[0].targets.push('turn:t9999');
    }), /Unresolved coverage target "turn:t9999"/);
    rejectMutation('hidden-model-is-not-a-public-coverage-target', caseDir => mutateContract(caseDir, contract => {
      contract.requirementCoverage[0].targets.push('attachment:model-state-1.json');
    }), /Unresolved coverage target "attachment:model-state-1\.json"/);
    rejectMutation('missing-original-requirement-link', caseDir => mutateContract(caseDir, contract => {
      const missing = planCase('MM-051').requirements[0].id;
      contract.requirementCoverage = contract.requirementCoverage.map(row => ({
        ...row, requirementIds: row.requirementIds.filter(id => id !== missing),
      })).filter(row => row.requirementIds.length);
    }), /Missing coverage for original requirement /);
    rejectMutation('unlinked-required-figure', caseDir => mutateContract(caseDir, contract => {
      const figure = contract.requiredOutputs.find(o => o.kind === 'figure');
      assert(figure, 'Fixture must include a source-required figure');
      const linked = target => target === 'requiredOutputs'
        || (typeof target === 'string' && ['output:', 'requiredOutputs:'].some(prefix => target === prefix + figure.id))
        || (typeof target === 'object' && target.kind === 'output' && target.id === figure.id);
      for (const row of contract.requirementCoverage) {
        row.targets = row.targets.filter(target => !linked(target));
        // Retain a valid row if its only target was the now-unlinked figure.
        if (!row.targets.length) row.targets.push('turn:t1');
      }
    }), /Required output .+ is not linked from requirementCoverage/);
    rejectMutation('actual-coordinate-json-bypass', caseDir => {
      const filename = path.join(caseDir, 'properties.json');
      const properties = readJson(filename);
      const model = readJson(path.join(caseDir, 'model-state-1.json'));
      properties.coordinates = model.nodes.map(({ id, x, y, z }) => ({ id, x, y, z }));
      writeJson(filename, properties);
    }, /MM attachment properties\.json provides a coordinate\/connection JSON bypass/);
    rejectMutation('missing-declared-png', caseDir => {
      const contract = readJson(path.join(caseDir, 'contract.json'));
      const attachment = contract.attachments.find(name => name.endsWith('.png'));
      assert(attachment, 'Fixture must have an actual PNG input');
      fs.unlinkSync(path.join(caseDir, attachment));
    }, /ENOENT.*\.png/);
    regression('pending-gate-mappings-do-not-grant-acceptance', () => {
      const f = fixture('pending-acceptance');
      const contract = readJson(path.join(f.caseDir, 'contract.json'));
      assert(contract.acceptanceGates.length > 0);
      assert(contract.acceptanceGates.every(gate => gate.status === 'pending'));
      const authored = validate(f.id, f.caseDir);
      const accepted = validate(f.id, f.caseDir, 'accepted');
      assert.equal(authored.authored, true);
      assert.equal(accepted.authored, true);
      assert.equal(accepted.valid, false);
      for (const key of ['referenceReady', 'accepted', 'inputReviewed', 'nativeVerified']) {
        assert.equal(accepted[key], false, `${key} must require separate evidence`);
      }
      assert(accepted.referenceErrors.length > 0, 'Independent references must remain required');
      assert(accepted.acceptanceErrors.length > 0, 'Independent input/native receipts must remain required');
      return { referenceErrors: accepted.referenceErrors, acceptanceErrors: accepted.acceptanceErrors };
    });
  }
} finally {
  fs.rmSync(scratch, { recursive: true, force: true });
}

const validatorRoot = path.resolve(path.dirname(options.validator), '..');
const dependencies = [options.validator, path.join(path.dirname(options.validator), 'corpus-provider.cjs'),
  ...['contract', 'reference-requests', 'manifest'].map(name => path.join(validatorRoot, 'schemas', `research300-${name}.schema.json`))];
const summary = {
  discovered: cases.length, authored: cases.filter(c => c.authored).length,
  authoredErrors: cases.reduce((total, c) => total + c.errors.length, 0),
  referenceReady: cases.filter(c => c.referenceReady).length,
  accepted: cases.filter(c => c.accepted).length,
  inputReviewed: cases.filter(c => c.inputReviewed).length,
  nativeVerified: cases.filter(c => c.nativeVerified).length,
  agentNotRun: cases.filter(c => c.agentStatus === 'not-run').length,
  regressionsPassed: regressions.filter(r => r.passed).length,
  regressionsRun: regressions.length,
};
const receipt = {
  schemaVersion: 1, scope: 'MM-051..MM-100', root: options.root, stage: 'authored',
  valid: summary.authored === 50 && summary.authoredErrors === 0 && regressions.length === 8 && regressions.every(r => r.passed),
  validator: { path: options.validator, sha256: hashFile(options.validator),
    dependencies: dependencies.filter(file => fs.existsSync(file)).map(file => ({ path: file, sha256: hashFile(file) })) },
  sourcePlanSha256: hashFile(planFile), driverSha256: hashFile(__filename), summary, cases, regressions,
};
if (options.output) writeJson(path.resolve(options.output), receipt);
console.log(JSON.stringify({ valid: receipt.valid, ...summary }));
if (!receipt.valid) {
  for (const c of cases) for (const error of c.errors) console.error(`${c.id}: ${error}`);
  for (const r of regressions.filter(r => !r.passed)) console.error(`${r.name}: ${r.error}`);
  if (!regressions.length) console.error('Mutation regressions require an authored-valid baseline; none were run.');
  process.exitCode = 1;
}
