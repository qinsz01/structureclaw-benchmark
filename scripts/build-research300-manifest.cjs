#!/usr/bin/env node
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const { resolveCaseFile, listFiles, sha256, CASE_ID, getResponseContract, RESPONSE_CONTRACT_VERSION } = require('../lib/corpus-provider.cjs');
const { validateResearchCorpus, validateSchema, schemas, PLAN_PATH, sourceHash } = require('../lib/research300-validation.cjs');
const ROOT = path.resolve(__dirname, '..');
const fileEntry = (base, name) => { const bytes = fs.readFileSync(resolveCaseFile(base, name)); return { path: name, sha256: sha256(bytes), bytes: bytes.length }; };
const digest = files => sha256(Buffer.from(JSON.stringify(files)));

// Pure builder: the caller chooses when/where to persist. No timestamp, absolute
// paths or directory enumeration order enters the reproducible manifest.
function buildManifest({ root = ROOT, allowPartial = false } = {}) {
  root = path.resolve(root);
  const planBytes = fs.readFileSync(resolveCaseFile(root, PLAN_PATH));
  const plan = JSON.parse(planBytes);
  const validation = validateResearchCorpus({ root, allowPartial });
  const responseErrors = [];
  const base = resolveCaseFile(root, 'corpora/research-300/cases', { directory: true });
  const originalSources = Object.entries(plan.sources).map(([role, source]) => {
    const relative = role === 'capabilityRegistry' ? source.file : `planning/sources/${source.file}`;
    let actual = null;
    try { actual = sha256(fs.readFileSync(resolveCaseFile(root, relative))); } catch (e) { if (e.code !== 'ENOENT') throw e; }
    return { role, path: relative, expectedSha256: source.sha256, sha256: actual, present: actual !== null, verified: actual === source.sha256 };
  }).sort((a, b) => a.role < b.role ? -1 : a.role > b.role ? 1 : 0);
  const cases = fs.readdirSync(base).sort().map(id => {
    if (!CASE_ID.test(id)) throw new Error(`Invalid case ID: ${id}`);
    const caseDir = resolveCaseFile(base, id, { directory: true });
    const contract = JSON.parse(fs.readFileSync(resolveCaseFile(caseDir, 'contract.json')));
    const publicNames = new Set(['prompt.txt', ...(contract.attachments || [])]);
    const files = listFiles(caseDir).sort().map(name => fileEntry(caseDir, name));
    const publicFiles = files.filter(f => publicNames.has(f.path));
    const privateFiles = files.filter(f => !publicNames.has(f.path));
    // Instructions and release schedules live in the private contract file but
    // are also part of the actual public input. Bind them without exposing the
    // remaining evaluator-only fields in the public projection.
    let referenceRequests;
    try { referenceRequests = JSON.parse(fs.readFileSync(resolveCaseFile(caseDir, 'reference-requests.json'))); } catch (_) { /* Record a sanitized per-turn projection failure below. */ }
    const projectionErrors = [];
    const publicTurns = (contract.turns || []).map((t, index) => {
      let responseContract = null;
      try { responseContract = getResponseContract({ contract, referenceRequests }, index); }
      catch (_) {
        // The provider may explain a rejected private selector in its exception.
        // A manifest diagnostic needs only the public turn index, never private
        // request contents or a partially generated public contract.
        projectionErrors.push(`Public response contract unavailable for turn ${index + 1}; correct authored response scope`);
      }
      return { id: t.id, instruction: t.instruction, attachments: t.attachments, responseContract };
    });
    responseErrors.push(...projectionErrors.map(error => `${id}: ${error}`));
    const responseContractTurnHashes = publicTurns.map(t => ({ turnId: t.id, sha256: t.responseContract === null ? null : digest(t.responseContract) }));
    const responseContractSha256 = projectionErrors.length ? null : digest(publicTurns.map(t => ({ turnId: t.id, responseContract: t.responseContract })));
    const result = validation.cases.find(c => c.id === id);
    const authored = Boolean(result?.authored && !projectionErrors.length), referenceReady = Boolean(result?.referenceReady && authored), accepted = Boolean(result?.accepted && authored);
    return { id, modelId: contract.modelId, family: contract.family, language: contract.language, plannedEngine: contract.plannedEngine,
      contract: `cases/${id}/contract.json`, publicFiles, privateFiles,
      responseContractSha256, responseContractTurnHashes,
      sourceHash: sourceHash(caseDir, contract), publicSha256: digest({ files: publicFiles, turns: publicTurns }), privateSha256: digest(privateFiles), filesSha256: digest(files),
      statuses: { authorship: authored ? 'authored-candidate' : 'invalid', inputReview: result?.inputReviewed ? 'independently-reviewed' : 'pending', reference: referenceReady ? 'reference-ready' : 'pending', native: result?.nativeVerified ? 'native-verified' : 'pending', acceptance: accepted ? 'accepted' : 'not-accepted', agent: contract.llmEndToEnd },
      validation: { authored, referenceReady, accepted, errors: [...(result?.errors || ['Case validation unavailable']), ...projectionErrors], referenceErrors: result?.referenceErrors || [], acceptanceErrors: result?.acceptanceErrors || [] } };
  });
  const counts = field => Object.fromEntries([...new Set(cases.map(c => c[field]))].sort().map(key => [key, cases.filter(c => c[field] === key).length]));
  const manifest = { schemaVersion: 1, corpusId: 'research-300', evaluationProfile: 'engineering-v2.3', modelProtocol: '2.2.0', responseContractVersion: RESPONSE_CONTRACT_VERSION,
    sourcePlan: { path: PLAN_PATH, sha256: sha256(planBytes) }, originalSources, cases,
    summary: { ...validation.summary, authored: cases.filter(c => c.validation.authored).length, referenceReady: cases.filter(c => c.validation.referenceReady).length, accepted: cases.filter(c => c.validation.accepted).length, byFamily: counts('family'), byLanguage: counts('language'), byEngine: counts('plannedEngine'), originalSourcesVerified: originalSources.every(s => s.verified) },
    validation: { valid: validation.valid && responseErrors.length === 0, partial: allowPartial, errors: [...validation.errors, ...responseErrors], warnings: validation.warnings } };
  const schemaErrors = validateSchema(manifest, schemas.manifest);
  if (schemaErrors.length) throw new Error(schemaErrors.join('; '));
  return manifest;
}
function main(args = process.argv.slice(2)) {
  try {
    const options = {}; let output;
    for (let i = 0; i < args.length; i++) {
      if (args[i] === '--allow-partial') options.allowPartial = true;
      else if (['--root', '--output'].includes(args[i])) {
        const flag = args[i], value = args[++i];
        if (!value || value.startsWith('--')) throw new Error(`Missing value for ${flag}`);
        if (flag === '--root') options.root = value; else output = value;
      } else if (args[i] === '--help') { process.stdout.write('Usage: node scripts/build-research300-manifest.cjs [--root DIR] [--allow-partial] --output FILE\nNo default output path; build centrally after integration.\n'); return; }
      else throw new Error(`Unknown option: ${args[i]}`);
    }
    if (!output) throw new Error('--output is required; manifest is only written explicitly');
    const manifest = buildManifest(options);
    if (!manifest.validation.valid) throw new Error(`Refusing invalid authored manifest: ${manifest.validation.errors.join('; ')}`);
    const outputPath = path.resolve(output);
    const caseRoot = path.resolve(options.root || ROOT, 'corpora/research-300/cases');
    if (outputPath === caseRoot || outputPath.startsWith(caseRoot + path.sep)) throw new Error('Manifest output must be outside authored case directories');
    // Exclusive creation prevents accidental clobbering of an existing artifact.
    fs.writeFileSync(outputPath, JSON.stringify(manifest, null, 2) + '\n', { flag: 'wx' });
    process.stdout.write(JSON.stringify(manifest.summary) + '\n');
  } catch (e) { process.stderr.write(e.message + '\n'); process.exitCode = 1; }
}
if (require.main === module) main();
module.exports = { buildManifest, main };
