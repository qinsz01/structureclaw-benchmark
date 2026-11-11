#!/usr/bin/env node
'use strict';
const path = require('node:path');
const { validateResearchCorpus, STAGES } = require('../lib/research300-validation.cjs');
function parseArgs(args) {
  const options = {}; let json = false;
  for (let i = 0; i < args.length; i++) {
    const flag = args[i];
    if (flag === '--allow-partial') options.allowPartial = true;
    else if (flag === '--json') json = true;
    else if (['--root', '--case', '--stage'].includes(flag)) {
      const value = args[++i];
      if (!value || value.startsWith('--')) throw new Error(`Missing value for ${flag}`);
      options[{ '--root': 'root', '--case': 'caseId', '--stage': 'stage' }[flag]] = value;
    } else if (flag === '--help') return { help: true };
    else throw new Error(`Unknown option: ${flag}`);
  }
  if (options.root) options.root = path.resolve(options.root);
  if (options.stage && !STAGES.includes(options.stage)) throw new Error(`Unknown stage: ${options.stage}`);
  return { options, json };
}
function main(args = process.argv.slice(2)) {
  try {
    const parsed = parseArgs(args);
    if (parsed.help) { process.stdout.write('Usage: node scripts/validate-research300.cjs [--root DIR] [--case ID | --allow-partial] [--stage authored|reference-ready|accepted] [--json]\n'); return; }
    const result = validateResearchCorpus(parsed.options);
    process.stdout.write(parsed.json ? JSON.stringify(result, null, 2) + '\n' : `${result.valid ? 'PASS' : 'FAIL'} research-300 ${result.stage}: ${JSON.stringify(result.summary)}\n${result.errors.map(e => '- ' + e + '\n').join('')}${result.warnings.map(e => 'Note: ' + e + '\n').join('')}`);
    if (!result.valid) process.exitCode = 1;
  } catch (e) { process.stderr.write(e.message + '\n'); process.exitCode = 1; }
}
if (require.main === module) main();
module.exports = { parseArgs, main };
