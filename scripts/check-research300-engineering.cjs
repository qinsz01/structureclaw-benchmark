#!/usr/bin/env node
'use strict';

// New opt-in entry point. The old strict checker and frozen scores are intact.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const {isDeepStrictEqual: equal} = require('node:util');
const {auditCommercial} = require('./check-research300-commercial.cjs');
const {POLICY, engineeringComparison} = require('../lib/cross-engine-engineering-policy.cjs');
const ROOT = path.resolve(__dirname, '..');
const hash = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const read = file => JSON.parse(fs.readFileSync(file, 'utf8'));
const check = (condition, message) => {if (!condition) throw new Error(message);};

function applyPolicy(comparison) {
  check(comparison.comparisons === comparison.strict.passed + comparison.strict.failed
    && comparison.strict.failed === comparison.strict.failures.length, 'Incomplete strict comparison');
  const changed = [], failures = [];
  for (const failure of comparison.strict.failures) {
    const result = engineeringComparison({value: failure.native, component: failure.component,
      unit: failure.unit, location: failure.location, tolerance: failure.frozenTolerance},
    failure.diagnostic, {family: failure.family});
    check(!result.strictPass && result.strictLimit === failure.frozenLimit && result.delta === failure.delta,
      'Strict result does not reproduce');
    const row = {...failure, ...result};
    if (result.engineeringPass) changed.push(row);
    else failures.push(row);
  }
  // The new limit is never narrower. Every strict pass therefore also passes
  // the engineering check, including noneligible quantities and derived rows.
  return {comparisons: comparison.comparisons, strict: comparison.strict,
    engineering: {passed: comparison.comparisons - failures.length, failed: failures.length, failures},
    newlyAccepted: changed};
}

function publicInputs(root, filename) {
  const bytes = fs.readFileSync(filename), report = JSON.parse(bytes);
  check(report.diagnosticOnly === true && report.scoringOrToleranceChanged === false,
    'Expected the retained diagnostic-only public-input experiment');
  // Bind to the original frozen archive and implementation, not candidate data.
  const archiveDir = path.join(path.resolve(process.env.SCLAW_BENCH_ARCHIVE || ROOT), 'docs/implementation/reviews/codex-diversity300-20261027');
  const meta = read(path.join(archiveDir, 'evidence-meta.json'));
  check(report.archiveSha256 === meta.sha256, 'Public-input experiment archive mismatch');
  const manifestBytes = fs.readFileSync(path.join(archiveDir, 'archive-manifest.json'));
  check(hash(manifestBytes) === meta.archiveManifestSha256, 'Archive manifest changed');
  const manifest = new Map(JSON.parse(manifestBytes).files.map(row => [row.path, row]));
  check(report.inputs.length > 0 && report.inputs.every(row => equal(row, manifest.get(row.path))),
    'Public-input experiment input provenance mismatch');
  const sourceBytes = fs.readFileSync(path.join(archiveDir, 'source-integrity.json'));
  check(hash(sourceBytes) === meta.sourceIntegritySha256, 'Frozen source manifest changed');
  for (const row of JSON.parse(sourceBytes).files) {
    check(hash(fs.readFileSync(path.join(ROOT, row.path))) === row.sha256, 'Frozen implementation changed: ' + row.path);
  }
  check(hash(fs.readFileSync(path.join(ROOT, 'scripts/research300/diagnose_pkpm_precision.py'))) === report.scriptSha256,
    'Public-input investigation implementation changed');
  const cases = [];
  for (const item of report.cases) {
    const file = path.join(root, 'corpora/research-300/cases', item.caseId, 'independent-reference.json');
    const nativeBytes = fs.readFileSync(file);
    const binding = report.inputs.find(row => row.path === `edition/corpora/research-300/cases/${item.caseId}/independent-reference.json`);
    check(binding && binding.sha256 === hash(nativeBytes), 'Public-input experiment native reference mismatch');
    const reference = JSON.parse(nativeBytes);
    check(reference.states.length === 1, 'Unexpected public-input experiment state coverage');
    const quantities = new Map(reference.states[0].quantities.map(q => [q.id, q]));
    const seen = new Set(), strict = {passed: 0, failed: 0, failures: []};
    for (const run of item.runs) {
      const experiment = run.experiments.find(row => row.variant === 'published');
      check(experiment && experiment.comparisons === experiment.rows.length, 'Incomplete public-input comparison');
      for (const row of experiment.rows) {
        const q = quantities.get(row.id);
        check(q && q.value === row.native && q.unit === row.unit && equal(q.selection, run.selection)
          && !seen.has(q.id), 'Public-input request identity mismatch');
        seen.add(q.id);
        const result = engineeringComparison(q, row.independent);
        check(result.strictPass === row.pass && result.strictLimit === row.limit
          && result.delta === Math.abs(row.difference), 'Public-input strict comparison mismatch');
        strict[result.strictPass ? 'passed' : 'failed']++;
        if (!result.strictPass) strict.failures.push({state: 1, id: q.id, family: 'quantities',
          selection: q.selection, component: q.component, location: q.location, unit: q.unit,
          native: q.value, diagnostic: row.independent, delta: result.delta,
          frozenTolerance: q.tolerance, frozenLimit: result.strictLimit});
      }
    }
    check(seen.size === quantities.size, 'Missing public-input requests');
    cases.push({id: item.caseId, ...applyPolicy({comparisons: seen.size, strict})});
  }
  check(equal(cases.map(c => c.id).sort(), ['STD-089', 'STD-091']), 'Unexpected public-input experiment case coverage');
  return {path: path.relative(ROOT, filename), sha256: hash(bytes),
    scope: 'Both parties use the exact released section properties; primary requests only', cases,
    summary: sum(cases)};
}

function sum(comparisons) {
  const result = {comparisons: 0, strict: {passed: 0, failed: 0}, engineering: {passed: 0, failed: 0}, newlyAccepted: 0};
  for (const row of comparisons) {
    result.comparisons += row.comparisons;
    for (const mode of ['strict', 'engineering']) for (const key of ['passed', 'failed']) result[mode][key] += row[mode][key];
    result.newlyAccepted += row.newlyAccepted.length;
  }
  return result;
}

function audit({root, publicDiagnostic}) {
  const strict = auditCommercial({root});
  const cases = strict.cases.map(item => ({...item, comparisons:
    Object.fromEntries(Object.entries(item.comparisons).map(([key, value]) => [key, applyPolicy(value)]))}));
  const report = {schemaVersion: 1, policy: POLICY,
    decisionBasis: 'engineering', originalStrictCheckerUnchanged: true,
    evidenceValid: strict.evidenceValid, sourcePlan: strict.sourcePlan, selection: strict.selection,
    inputScope: 'Retained authored matrix/OpenSees diagnostics; see publicInputs for exact released-property controls',
    policyImplementation: {path: 'lib/cross-engine-engineering-policy.cjs',
      sha256: hash(fs.readFileSync(path.join(ROOT, 'lib/cross-engine-engineering-policy.cjs')))},
    cases, summary: {}};
  for (const engine of ['matrix', 'OpenSees']) report.summary[engine] = sum(cases.map(c => c.comparisons[engine]));
  report.summary.combined = sum(cases.flatMap(c => Object.values(c.comparisons)));
  report.strictPass = report.summary.combined.strict.failed === 0;
  report.engineeringPass = report.summary.combined.engineering.failed === 0;
  if (publicDiagnostic) {
    report.publicInputs = publicInputs(root, publicDiagnostic);
    report.engineeringPass &&= report.publicInputs.summary.engineering.failed === 0;
    report.strictPass &&= report.publicInputs.summary.strict.failed === 0;
  }
  return report;
}

function main(argv = process.argv.slice(2)) {
  try {
    const options = {};
    for (let i = 0; i < argv.length; i++) {
      if (argv[i] === '--help') {
        process.stdout.write('Usage: check-research300-engineering.cjs --root EDITION [--public-diagnostic FILE] [--output NEWFILE]\nChecks all commercial cases with the versioned engineering moment budget. Preserves strict failures. Exit 0 engineering agreement, 1 disagreement, 2 invalid evidence/I/O. No scoring or reference changes.\n');
        return 0;
      }
      const key = {'--root': 'root', '--output': 'output', '--public-diagnostic': 'publicDiagnostic'}[argv[i]];
      check(key && options[key] === undefined && argv[i + 1] && !argv[i + 1].startsWith('--'), 'Invalid command option');
      options[key] = path.resolve(argv[++i]);
    }
    check(options.root, 'An explicit edition --root is required');
    const report = audit(options);
    if (options.output) {
      // New files only, outside source cases; never overwrite captured evidence.
      const relative = path.relative(path.join(options.root, 'corpora/research-300/cases'), options.output);
      check(relative.startsWith('..' + path.sep) || path.isAbsolute(relative), 'Report cannot be written in case sources');
      fs.writeFileSync(options.output, JSON.stringify(report, null, 2) + '\n', {flag: 'wx'});
    } else process.stdout.write(JSON.stringify(report, null, 2) + '\n');
    return report.engineeringPass ? 0 : 1;
  } catch (error) {
    process.stderr.write(`Engineering comparison failed: ${error.message}\n`);
    return 2;
  }
}

module.exports = {applyPolicy, publicInputs, sum, audit, main};
if (require.main === module) process.exitCode = main();
