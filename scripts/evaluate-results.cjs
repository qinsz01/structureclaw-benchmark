#!/usr/bin/env node
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const { importResult, prepareEvaluation, protectOutput, sourceIdentity } = require('../lib/result-import.cjs');
const { runResearch300, researchExitCode } = require('./run-research300.cjs');

const HELP = `Usage:
  npm run prepare:evaluation -- --case STD-001 --output /tmp/task
  npm run prepare:evaluation -- --case INT-001 --turn t2 --output /tmp/task-t2
  npm run evaluate -- --input result.json --case STD-001 --output /tmp/report.json

  --format auto|codex|structureclaw|capture   Default auto
  --turn ID               Prepare only: release history through this turn (default first turn)
  --context FILE          Context from prepare:evaluation (instead of --case)
  --state FILE            Codex single-turn physical state sidecar
  --states FILE           Codex ordered per-turn physical states JSON array
  --artifact-root DIR     Root of paths in supplied artifact/figure mappings
  --runs-root DIR         StructureClaw runtime/runs directory
  --capture-root DIR      Original Python worker evidence capture directory
  --structureclaw-root DIR Upstream checkout for optional canonical reconstruction
  --python PATH           Python with upstream dependencies, when needed
  --assessments FILE      Independent semantic review receipts
  --root DIR              Benchmark checkout (default this checkout)

Report and adjacent .capture directory must be new. No model calls are made.
Preparation releases only the first turn unless --turn selects a later public turn.
Keep capture-context.json and future packets outside the agent's accessible workspace.
Without --context, --case declares current inputs; the report records this assumption.
Exit: 0 passed, 1 candidate failure, 2 invalid input/configuration, 3 pending.
`;
function parse(args) {
  const options = { format: 'auto' };
  const fields = { '--input': 'input', '--case': 'caseId', '--output': 'output', '--format': 'format', '--root': 'root',
    '--context': 'context', '--state': 'state', '--states': 'states', '--artifact-root': 'artifactRoot',
    '--runs-root': 'runsRoot', '--capture-root': 'captureRoot', '--structureclaw-root': 'structureclawRoot',
    '--python': 'python', '--assessments': 'assessments', '--turn': 'turn' };
  for (let index = 0; index < args.length; index++) {
    const flag = args[index];
    if (flag === '--help' || flag === '-h') { options.help = true; continue; }
    if (flag === '--prepare') { options.prepare = true; continue; }
    if (!fields[flag] || !args[index + 1] || args[index + 1].startsWith('--')) throw new Error(`Invalid or incomplete option: ${flag}`);
    options[fields[flag]] = args[++index];
  }
  if (!options.help && (!options.output || (!options.prepare && !options.input))) throw new Error('--output and --input are required (prepare requires --case and --output)');
  if (!options.help && options.turn !== undefined && !options.prepare) throw new Error('--turn is only supported with --prepare');
  return options;
}
function verifyAssessmentLocation(options) {
  if (!options.assessments) return;
  const file = fs.realpathSync(options.assessments), stat = fs.statSync(file);
  const roots = [options.artifactRoot || path.dirname(path.resolve(options.input)), options.runsRoot, options.captureRoot].filter(Boolean);
  for (const root of roots) {
    const actual = fs.realpathSync(root);
    if (file === actual || file.startsWith(actual + path.sep)) throw new Error('Independent assessments must be outside original candidate evidence roots');
  }
  for (const source of [options.input, options.state, options.states, options.context].filter(Boolean)) {
    const actual = fs.realpathSync(source), sourceStat = fs.statSync(actual);
    if (file === actual || stat.dev === sourceStat.dev && stat.ino === sourceStat.ino) {
      throw new Error('Independent assessments cannot be a candidate or capture context source file');
    }
  }
}
async function main(args = process.argv.slice(2)) {
  try {
    const options = parse(args);
    if (options.help) { process.stdout.write(HELP); return 0; }
    if (options.prepare) { process.stdout.write(JSON.stringify(prepareEvaluation(options), null, 2) + '\n'); return 0; }
    const output = path.resolve(options.output);
    protectOutput(output, options.root);
    if (!fs.statSync(path.dirname(output)).isDirectory()) throw new Error('Output parent must exist');
    verifyAssessmentLocation(options);
    const imported = importResult({ ...options, outputRoot: output + '.capture' });
    const command = ['--execution', 'evaluate-artifacts', '--artifacts', imported.artifactsPath, '--artifact-root', imported.artifactRoot];
    if (options.root) command.push('--root', options.root);
    const caseId = imported.caseId;
    if (caseId) command.push('--case', caseId);
    else if (imported.caseIds?.length) command.push('--cases', imported.caseIds.join(','));
    const assessmentSource = options.assessments ? sourceIdentity(options.assessments, 'assessments') : undefined;
    if (options.assessments) command.push('--assessments', options.assessments);
    const report = await runResearch300(command, { stdout() {} });
    report.import = { ...imported.provenance, capture: imported.artifactsPath };
    if (assessmentSource) {
      if (sourceIdentity(options.assessments, 'assessments').sha256 !== assessmentSource.sha256) throw new Error('Assessment source changed during evaluation');
      report.import.sources = [...(report.import.sources || []), assessmentSource];
    }
    protectOutput(output, options.root);
    fs.writeFileSync(output, JSON.stringify(report, null, 2) + '\n', { flag: 'wx' });
    process.stdout.write(JSON.stringify({ status: report.status, output, capture: imported.artifactsPath,
      cases: report.cases.map(item => ({ caseId: item.caseId, status: item.status })),
      reviewRequests: report.reviewRequests?.length || 0, warnings: imported.provenance.warnings }, null, 2) + '\n');
    return researchExitCode(report);
  } catch (error) {
    process.stderr.write(JSON.stringify({ status: 'import_error', code: error.code || 'usage_error', message: error.message }) + '\n');
    return 2;
  }
}
if (require.main === module) main().then(code => { process.exitCode = code; });
module.exports = { main, parse, verifyAssessmentLocation };
