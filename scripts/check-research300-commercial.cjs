#!/usr/bin/env node
'use strict';

// Read-only commercial truth versus saved independent diagnostics. No solver,
// reference installer, acceptance writer, network client or native job is used.
const fs = require('node:fs');
const path = require('node:path');
const {isDeepStrictEqual: equal} = require('node:util');
const {sha256, resolveCaseFile} = require('../lib/corpus-provider.cjs');
const {validateResearchCase, sourceHash, PLAN_PATH, PLAN_SHA256} = require('../lib/research300-validation.cjs');
const {referenceAllowance, POLICY} = require('../lib/reference-precision.cjs');
const {parseStrictJson} = require('./check-research300-references.cjs');

const ROOT = path.resolve(__dirname, '..');
const DEFAULT_TOLERANCE = {absolute:1e-8,relative:1e-6};
const HASH = /^[a-f0-9]{64}$/;
const finite = value => typeof value === 'number' && Number.isFinite(value);
const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const nonempty = value => typeof value === 'string' && value.trim().length > 0;
const requireValue = (condition, message) => {if (!condition) throw new Error(message);};

function selectionKey(selection) {
  requireValue(object(selection) && ['case','combination'].includes(selection.kind) && nonempty(selection.id)
    && equal(Object.keys(selection).sort(), ['id','kind']), 'Invalid typed selection identity');
  return [selection.kind, selection.id];
}
function quantityKey(quantity) {
  requireValue(nonempty(quantity?.id), 'Missing quantity identity');
  return JSON.stringify([quantity.id, ...selectionKey(quantity.selection)]);
}
function index(records, key, label) {
  requireValue(Array.isArray(records), `${label} must be an array`);
  const result = new Map();
  for (const record of records) {
    requireValue(object(record), `Invalid ${label} record`);
    const id = key(record);
    requireValue(!result.has(id), `Duplicate ${label} identity: ${id}`);
    result.set(id,record);
  }
  return result;
}
function sameKeys(actual, expected, label) {
  for (const key of expected.keys()) requireValue(actual.has(key), `Missing ${label} identity: ${key}`);
  for (const key of actual.keys()) requireValue(expected.has(key), `Extra ${label} identity: ${key}`);
}
function stateKey(state) {
  requireValue(Number.isInteger(state.state) && state.state > 0, 'Invalid state identity');
  return state.state;
}
function tolerance(record) {
  const value = record.tolerance === undefined ? DEFAULT_TOLERANCE : record.tolerance;
  requireValue(object(value) && finite(value.absolute) && finite(value.relative)
    && value.absolute >= 0 && value.relative >= 0, `Invalid frozen tolerance: ${record.id}`);
  return value;
}
function validateResult(result, request, family, label) {
  requireValue(finite(result.value), `${label} has no finite value: ${request.id}`);
  const fields = family === 'quantities' ? ['selection','location','component','unit'] : ['operation','operands','unit'];
  for (const key of fields) requireValue(equal(result[key],request[key]), `${label} metadata ${key} differs: ${request.id}`);
  requireValue(equal(tolerance(result),tolerance(request)), `${label} tolerance differs from frozen request: ${request.id}`);
  if (family === 'derived') requireValue(result.engineeringPrecision === undefined, 'Derived precision is not supported');
}

/** Pure comparison; qualification and certificate bytes must be validated by the CLI. */
function compareDocuments(reference, diagnostic, requests) {
  requireValue(nonempty(reference?.id) && reference.id === diagnostic?.id, 'Reference/diagnostic case identity mismatch');
  requireValue(HASH.test(reference.sourceHash || '') && diagnostic.sourceHash === reference.sourceHash, 'Reference/diagnostic source hash mismatch');
  if (reference.inputHashes !== undefined) requireValue(equal(reference.inputHashes,diagnostic.inputHashes), 'Diagnostic source input hashes differ');
  const wantedStates = index(requests?.states,stateKey,'frozen state');
  const nativeStates = index(reference.states,stateKey,'native state');
  const diagnosticStates = index(diagnostic.states,stateKey,'diagnostic state');
  sameKeys(nativeStates,wantedStates,'native state');sameKeys(diagnosticStates,wantedStates,'diagnostic state');
  const result = {comparisons:0,precisionQuantities:0,
    strict:{passed:0,failed:0,failures:[]},engineering:{passed:0,failed:0,failures:[]}};
  for (const [state,wanted] of wantedStates) {
    for (const family of ['quantities','derived']) {
      const key = family === 'quantities' ? quantityKey : row => {
        requireValue(nonempty(row.id),'Missing derived identity');return row.id;
      };
      const definitions = index(wanted[family] || [],key,`frozen ${family}`);
      const native = index(nativeStates.get(state)[family] || [],key,`native ${family}`);
      const partner = index(diagnosticStates.get(state)[family] || [],key,`diagnostic ${family}`);
      sameKeys(native,definitions,`native ${family}`);sameKeys(partner,definitions,`diagnostic ${family}`);
      for (const [id,request] of definitions) {
        const left=native.get(id),right=partner.get(id);
        validateResult(left,request,family,'Native');validateResult(right,request,family,'Diagnostic');
        requireValue(right.engineeringPrecision === undefined, 'Diagnostic precision cannot enlarge a reference allowance');
        if (family === 'derived') {
          for (const field of ['selection','governingSelection','governingSelections','operandSelections'])
            requireValue(equal(left[field],right[field]), `Derived typed selection metadata differs: ${request.id}`);
        }
        const frozen=tolerance(request),delta=Math.abs(left.value-right.value);
        const frozenLimit=frozen.absolute+frozen.relative*Math.abs(left.value);
        const allowance=family==='quantities'?referenceAllowance(left):0;
        const engineeringLimit=frozenLimit+allowance;
        requireValue([delta,frozenLimit,engineeringLimit].every(finite),'Non-finite comparison arithmetic');
        const strictPass=delta<=frozenLimit,engineeringPass=delta<=engineeringLimit;
        result.comparisons++;
        if (left.engineeringPrecision !== undefined) result.precisionQuantities++;
        result.strict[strictPass?'passed':'failed']++;
        result.engineering[engineeringPass?'passed':'failed']++;
        if (!strictPass) {
          const failure={state,id:request.id,family,selection:left.selection || null,
            component:request.component || null,location:request.location || null,unit:request.unit,
            native:left.value,diagnostic:right.value,delta,frozenTolerance:{...frozen},frozenLimit,
            referenceAllowance:allowance,engineeringLimit,strictPass,engineeringPass};
          if (left.engineeringPrecision !== undefined) failure.engineeringPrecision=left.engineeringPrecision;
          result.strict.failures.push(failure);
          if (!engineeringPass) result.engineering.failures.push(failure);
        }
      }
    }
  }
  return result;
}

function emptySummary() {
  return {comparisons:0,precisionQuantities:0,strict:{passed:0,failed:0},engineering:{passed:0,failed:0}};
}
function accumulate(total, result) {
  total.comparisons+=result.comparisons;total.precisionQuantities+=result.precisionQuantities;
  for (const mode of ['strict','engineering']) for (const field of ['passed','failed']) total[mode][field]+=result[mode][field];
}
function displayPath(root, file) {
  const relative=path.relative(root,file);
  return relative.startsWith('..'+path.sep)||path.isAbsolute(relative)?file:relative.split(path.sep).join('/');
}

function auditCommercial({root=ROOT,casesDir,caseIds=[]}={}) {
  root=path.resolve(root);casesDir=path.resolve(casesDir || path.join(root,'corpora/research-300/cases'));
  const planFile=resolveCaseFile(root,PLAN_PATH),planBytes=fs.readFileSync(planFile);
  requireValue(sha256(planBytes)===PLAN_SHA256,'Source capability plan hash differs from approved original');
  const plan=parseStrictJson(planBytes),commercial=plan.cases.filter(row=>['PKPM','YJK'].includes(row.plannedEngine));
  requireValue(Array.isArray(caseIds)&&new Set(caseIds).size===caseIds.length,'Duplicate case selection');
  for (const id of caseIds) requireValue(commercial.some(row=>row.id===id),`Requested case is not a commercial source-plan case: ${id}`);
  const selected=commercial.filter(row=>!caseIds.length||caseIds.includes(row.id)).sort((a,b)=>a.id.localeCompare(b.id));
  const report={schemaVersion:2,role:'Cross-engine diagnostics only; no reference, native qualification, or benchmark acceptance is changed',
    comparisonPolicy:{default:'strict',engineeringDiagnosticOnly:true,reference:'qualified same-engine PKPM/YJK native value',
      strict:'abs(native-diagnostic) <= frozen absolute + frozen relative * abs(native)',
      engineering:'strict limit + certified referenceAllowance(native quantity)',
      policy:POLICY,acceptanceRegionChanges:true,nativeArithmeticBound:false,
      derived:'Frozen native derived value and tolerance; no precision allowance or propagation.',
      scope:'Only certified primary-reference quantities carry the engineering diagnostic. Frozen strict tolerance determines valid and CLI exit.'},
    roots:{root,casesDir},sourcePlan:{path:displayPath(root,planFile),sha256:PLAN_SHA256},
    selection:{plannedCommercialCases:commercial.length,selectedCases:selected.length,partial:caseIds.length>0},
    summary:{matrix:emptySummary(),OpenSees:emptySummary(),combined:emptySummary()},cases:[]};
  const reads=[];
  for (const planCase of selected) {
    const caseDir=resolveCaseFile(casesDir,planCase.id,{directory:true}),artifacts=[];
    function load(name,role) {
      const file=resolveCaseFile(caseDir,name),bytes=fs.readFileSync(file),digest=sha256(bytes);
      reads.push({file,digest});artifacts.push({role,path:displayPath(root,file),sha256:digest});
      return parseStrictJson(bytes);
    }
    const contract=load('contract.json','contract'),requests=load('reference-requests.json','frozen-requests');
    const native=load('independent-reference.json','native'),matrix=load('independent-reference-matrix-diagnostic.json','matrix');
    const opensees=load('native-opensees-reference.json','OpenSees');
    load('acceptance.json','native-qualification-binding');
    const validation=validateResearchCase({root,caseDir,planCase,stage:'reference-ready'});
    requireValue(validation.valid&&validation.referenceReady&&validation.nativeVerified,
      `${planCase.id}: native qualification/reference validation failed: ${[...validation.errors,...validation.acceptanceErrors].join('; ')}`);
    const digest=sourceHash(caseDir,contract);
    requireValue(native.sourceHash===digest,`${planCase.id}: Native source SHA is stale`);
    requireValue(native.referenceKind===`native-${planCase.plannedEngine.toLowerCase()}`&&native.notCommercialScoringTruth===false,
      `${planCase.id}: Primary reference is not qualified native truth`);
    requireValue(matrix.referenceKind==='independent-elastic-matrix'&&opensees.referenceKind==='native-opensees',
      `${planCase.id}: Diagnostic artifact roles differ`);
    const matrixDescriptor=artifacts.find(row=>row.role==='matrix');
    requireValue(native.matrixDiagnostic?.sha256===matrixDescriptor.sha256,
      `${planCase.id}: Saved matrix diagnostic SHA differs from native installation binding`);
    const item={id:planCase.id,engine:planCase.plannedEngine,sourceHash:digest,artifacts,
      qualification:{nativeVerified:validation.nativeVerified,referenceReady:validation.referenceReady,
        inputBlindReview:validation.inputReviewed?'passed':'pending'},comparisons:{}};
    for (const [partner,document] of [['matrix',matrix],['OpenSees',opensees]]) {
      item.comparisons[partner]=compareDocuments(native,document,requests);
      accumulate(report.summary[partner],item.comparisons[partner]);
      accumulate(report.summary.combined,item.comparisons[partner]);
    }
    requireValue(sourceHash(caseDir,contract)===digest,`${planCase.id}: Authored source changed during comparison`);
    report.cases.push(item);
  }
  for (const {file,digest} of reads) requireValue(sha256(fs.readFileSync(file))===digest,`Input changed during comparison: ${file}`);
  requireValue(sha256(fs.readFileSync(planFile))===PLAN_SHA256,'Source plan changed during comparison');
  report.strictPass=report.summary.combined.strict.failed===0;
  report.engineeringPass=report.summary.combined.engineering.failed===0;
  report.evidenceValid=true;
  report.valid=report.strictPass;
  return report;
}

function writeReport(file, report, {root=ROOT,casesDir}={}) {
  requireValue(nonempty(file)&&!file.split(/[\\/]/).includes('..'),'Unsafe explicit report path');
  const target=path.resolve(file),parent=path.dirname(target),realParent=fs.realpathSync(parent);
  requireValue(realParent===parent,'Report output parent must not contain a symlink');
  const protectedRoots=[path.resolve(root,'corpora/research-300/cases'),path.resolve(casesDir||path.join(root,'corpora/research-300/cases'))];
  for (const base of protectedRoots) {
    const realBase=fs.realpathSync(base),relative=path.relative(realBase,target);
    requireValue(relative!==''&&(relative.startsWith('..'+path.sep)||path.isAbsolute(relative)), 'Report output must be outside active and staging cases');
  }
  const fd=fs.openSync(target,fs.constants.O_WRONLY|fs.constants.O_CREAT|fs.constants.O_EXCL|fs.constants.O_NOFOLLOW,0o644);
  try {fs.writeFileSync(fd,JSON.stringify(report,null,2)+'\n');fs.fsyncSync(fd);} finally {fs.closeSync(fd);}
}

function main(argv=process.argv.slice(2)) {
  try {
    const options={caseIds:[]};
    for (let i=0;i<argv.length;i++) {
      if (argv[i]==='--help') {
        process.stdout.write('Usage: check-research300-commercial.cjs [--root ROOT] [--cases-dir DIR] [--case ID ...] [--output NEWFILE]\nRead-only schema2 diagnostics: strict frozen tolerance governs the result; engineering allowance is diagnostic only. JSON stdout unless output is explicit. Exit 0 strict agreement, 1 strict numerical disagreement, 2 invalid inputs/qualification/I/O.\n');return 0;
      }
      const keys={'--root':'root','--cases-dir':'casesDir','--case':'caseIds','--output':'output'},key=keys[argv[i]];
      requireValue(key&&nonempty(argv[i+1])&&!argv[i+1].startsWith('--'),`Unknown option or missing value: ${argv[i]}`);
      if (key==='caseIds') options.caseIds.push(argv[++i]);
      else {requireValue(options[key]===undefined,`Duplicate option ${argv[i]}`);options[key]=argv[++i];}
    }
    const report=auditCommercial(options);
    if (options.output) writeReport(options.output,report,options);
    else process.stdout.write(JSON.stringify(report,null,2)+'\n');
    return report.valid?0:1;
  } catch (error) {process.stderr.write(`Commercial diagnostic comparison failed: ${error.message}\n`);return 2;}
}

module.exports={compareDocuments,auditCommercial,writeReport,main};
if (require.main===module) process.exitCode=main();
