#!/usr/bin/env node
'use strict';
// Prepare reviewed commercial reference trees offline. The active corpus is
// read-only; the caller reviews and installs the explicit output separately.
const fs=require('node:fs'),path=require('node:path');
const {isDeepStrictEqual:equal}=require('node:util');
const {resolveCaseFile,listFiles,sha256}=require('../lib/corpus-provider.cjs');
const {sourceHash,validateReference}=require('../lib/research300-validation.cjs');
const {parseStrictJson}=require('./check-research300-references.cjs');
const requireTrue=(ok,message)=>{if(!ok)throw new Error(message);};
function stringify(value,depth=0){
  if(value===null||typeof value!=='object')return Object.is(value,-0)?'-0.0':JSON.stringify(value);
  const array=Array.isArray(value),entries=array?value.map(v=>[null,v]):Object.entries(value).filter(([,v])=>v!==undefined);
  const [open,close]=array?['[',']']:['{','}'];
  if(!entries.length)return open+close;
  const indent='  '.repeat(depth+1);
  return open+'\n'+entries.map(([k,v])=>indent+(array?'':JSON.stringify(k)+': ')+(stringify(v,depth+1)??'null')).join(',\n')+'\n'+'  '.repeat(depth)+close;
}
// Preserve native/Python -0.0 in retained raw axes and arrays. Ordinary
// JSON.stringify would rewrite it to +0 and break exact candidate comparison.
const serialize=value=>Buffer.from(stringify(value)+'\n');
const key=q=>JSON.stringify([q.id,q.selection]);
function safeOutput(output,activeRoot){
  requireTrue(!fs.existsSync(output),'Output already exists');
  // Reject existing aliases before mkdir/write; a lexical prefix test alone
  // could redirect a seemingly separate destination back into the corpus.
  for(let parent=path.dirname(output);;parent=path.dirname(parent)){
    try{const stat=fs.lstatSync(parent);requireTrue(!stat.isSymbolicLink()&&stat.isDirectory(),'Output parent is a symlink or not a directory');}
    catch(error){if(error.code!=='ENOENT')throw error;}
    if(parent===path.dirname(parent))break;
  }
  requireTrue(output!==activeRoot&&!output.startsWith(activeRoot+path.sep),'Output must be outside the active corpus');
}

function prepareCase({caseDir,bundleRoot,entry,output}) {
  caseDir=path.resolve(caseDir);bundleRoot=path.resolve(bundleRoot);output=path.resolve(output);
  safeOutput(output,path.dirname(fs.realpathSync(caseDir)));
  const snapshots=[],files=new Map();
  function read(root,name,digest) {
    const filename=resolveCaseFile(root,name),bytes=fs.readFileSync(filename),actual=sha256(bytes);
    requireTrue(digest===undefined||digest===actual,`Evidence hash mismatch: ${name}`);
    snapshots.push({filename,sha256:actual});return bytes;
  }
  function bound(root,descriptor) {
    requireTrue(descriptor&&/^[a-f0-9]{64}$/.test(descriptor.sha256),'Missing evidence SHA-256');
    return read(root,descriptor.path,descriptor.sha256);
  }
  for(const name of listFiles(caseDir))files.set(name,read(caseDir,name));
  const contract=parseStrictJson(files.get('contract.json')),requests=parseStrictJson(files.get('reference-requests.json'));
  const engine=contract.plannedEngine,digest=sourceHash(caseDir,contract);
  requireTrue(['PKPM','YJK'].includes(engine)&&entry.id===contract.id,'Commercial case/engine mismatch');
  const candidateBytes=bound(bundleRoot,entry.candidate),candidate=parseStrictJson(candidateBytes);
  const reviewBytes=bound(bundleRoot,entry.review),review=parseStrictJson(reviewBytes);
  const rows=(review.cases||[]).filter(row=>row.id===entry.id);
  requireTrue(review.schemaVersion===1&&typeof review.reviewer==='string'&&review.reviewer.trim()&&
    rows.length===1&&rows[0].status==='qualified'&&rows[0].sourceHash===digest&&
    rows[0].candidateSha256===entry.candidate.sha256,'Review does not qualify this source and candidate');
  requireTrue(candidate.id===entry.id&&candidate.referenceKind===`native-${engine.toLowerCase()}-candidate`,
    'Candidate case/engine mismatch');
  const matrixBytes=files.get('independent-reference.json'),matrix=parseStrictJson(matrixBytes);
  requireTrue(matrix.referenceKind==='independent-elastic-matrix'&&matrix.sourceHash===digest,'Current matrix diagnostic is missing or stale');
  const reference={...candidate,toleranceFrozenBeforeCandidate:true};
  const errors=[];validateReference(reference,requests,errors,caseDir,contract);
  requireTrue(!errors.length,'Invalid candidate reference: '+errors.join('; '));
  for(const wanted of requests.states) {
    const actual=candidate.states.find(state=>state.state===wanted.state);
    requireTrue(actual.model===wanted.model,'Candidate state model differs from frozen requests');
    requireTrue(equal(actual.quantities.map(key).sort(),wanted.quantities.map(key).sort())&&
      equal((actual.derived||[]).map(q=>q.id).sort(),(wanted.derived||[]).map(q=>q.id).sort()),
      'Candidate quantity set differs from frozen requests');
  }
  const evidenceRoot=path.resolve(bundleRoot,entry.evidenceRoot);
  requireTrue(evidenceRoot===bundleRoot||evidenceRoot.startsWith(bundleRoot+path.sep),'Evidence root escapes bundle');
  const artifacts=new Map();
  for(const descriptor of entry.artifacts||[]) {
    requireTrue(!artifacts.has(descriptor.path),'Duplicate native artifact');
    const bytes=bound(evidenceRoot,descriptor),target='native-commercial/evidence/'+descriptor.path;
    files.set(target,bytes);artifacts.set(descriptor.path,{path:target,sha256:descriptor.sha256});
  }
  function remap(descriptor) {
    const result=artifacts.get(descriptor.path);
    requireTrue(result&&result.sha256===descriptor.sha256,'Native artifact missing from installation: '+descriptor.path);
    return result;
  }
  function mapArtifacts(value) {
    if(Array.isArray(value))return value.map(mapArtifacts);
    requireTrue(value&&typeof value==='object','Invalid native artifact container');
    if(Object.hasOwn(value,'path'))return remap(value);
    return Object.fromEntries(Object.entries(value).map(([id,child])=>[id,mapArtifacts(child)]));
  }
  for(const state of reference.states)(state.evidenceArtifacts||[]).forEach(remap);
  if(reference.nativeArtifacts)reference.nativeArtifacts=mapArtifacts(reference.nativeArtifacts);
  for(const state of reference.states){
    if(state.evidenceArtifacts)state.evidenceArtifacts=state.evidenceArtifacts.map(remap);
    if(state.nativeInputStatus)state.nativeInputStatus='independently-qualified';
    for(const quantity of state.quantities)if(quantity.nativeStatus==='candidate-pending-review')quantity.nativeStatus='independently-qualified';
  }
  const store=(name,bytes)=>{files.set(name,bytes);return {path:name,sha256:sha256(bytes)};};
  const candidateArtifact=store('native-commercial/candidate.json',candidateBytes);
  const independentReview=store('native-commercial/qualification.json',reviewBytes);
  const matrixDiagnostic=store('independent-reference-matrix-diagnostic.json',matrixBytes);
  const supplemental=(entry.supplementalArtifacts||[]).map(descriptor=>
    store('native-commercial/supplements/'+descriptor.path,bound(bundleRoot,descriptor)));
  Object.assign(reference,{referenceKind:`native-${engine.toLowerCase()}`,status:'native-reference-qualified',
    notCommercialScoringTruth:false,sameEngineTruthStatus:'verified',nativeIndependentReview:'passed',
    nativeVerified:true,accepted:false,llmEndToEnd:'not-run',candidateArtifact,independentReview,matrixDiagnostic,
    evidencePathBase:'native-commercial/evidence',
    qualificationScope:'Same-engine numerical truth; input blind review and candidate-model trials remain separate.'});
  const expected=new Map();
  for(const state of requests.states)for(const q of state.quantities){
    const identity=JSON.stringify([state.state,q.selection]);expected.set(identity,{state:state.state,selection:q.selection,model:state.model});
  }
  requireTrue(Array.isArray(entry.receipts)&&entry.receipts.length===expected.size,'Missing or extra native execution receipts');
  const receipts=[];
  for(const receipt of entry.receipts) {
    const identity=JSON.stringify([receipt.state,receipt.selection]),wanted=expected.get(identity);
    requireTrue(wanted&&typeof receipt.runId==='string'&&receipt.runId.trim()&&
      typeof receipt.engineVersion==='string'&&receipt.engineVersion.trim()&&receipt.artifacts?.length,'Invalid native execution receipt');
    expected.delete(identity);
    const body={...receipt,engine,modelSha256:sha256(files.get(wanted.model)),status:'succeeded',
      artifacts:[...receipt.artifacts.map(remap),...supplemental,candidateArtifact,independentReview],
      receiptRole:'Offline wrapper of retained reviewed native execution; no new solve performed.'};
    const name=`native-commercial/receipt-${receipts.length+1}.json`;
    receipts.push({...store(name,serialize(body)),state:receipt.state,selection:receipt.selection});
  }
  const installed=store('independent-reference.json',serialize(reference));
  store('acceptance.json',serialize({schemaVersion:1,sourceHash:digest,independentReferenceSha256:installed.sha256,
    inputBlindReview:{status:'pending'},sameEngineTruth:{status:'verified',engine,independentlyReviewed:true,
      reviewer:review.reviewer,evidence:independentReview,receipts}}));
  for(const snapshot of snapshots)requireTrue(sha256(fs.readFileSync(snapshot.filename))===snapshot.sha256,'Input changed during preparation');
  requireTrue(sourceHash(caseDir,contract)===digest,'Authored source changed during preparation');
  // All validation precedes any output creation. Never overwrite an existing
  // staged file or follow a destination alias.
  fs.mkdirSync(path.dirname(output),{recursive:true});
  const temporary=fs.mkdtempSync(path.join(path.dirname(output),'.commercial-case-'));
  try{
    for(const [name,bytes] of files){const target=path.join(temporary,name);fs.mkdirSync(path.dirname(target),{recursive:true});fs.writeFileSync(target,bytes,{flag:'wx'});}
    safeOutput(output,path.dirname(fs.realpathSync(caseDir)));
    fs.renameSync(temporary,output);
  }catch(error){fs.rmSync(temporary,{recursive:true,force:true});throw error;}
  return {id:entry.id,sourceHash:digest,independentReferenceSha256:installed.sha256,receipts:receipts.length,
    nativeVerified:true,inputReviewed:false,accepted:false};
}

function main(argv=process.argv.slice(2)){
  const options={};for(let i=0;i<argv.length;i+=2){
    requireTrue(['--bundle','--cases-root','--output'].includes(argv[i])&&argv[i+1]&&!options[argv[i]],'Expected --bundle FILE --cases-root DIR --output NEWDIR');options[argv[i]]=argv[i+1];
  }
  requireTrue(Object.keys(options).length===3,'All three options are required');
  const bundlePath=path.resolve(options['--bundle']),bundleBytes=fs.readFileSync(bundlePath),bundleSha256=sha256(bundleBytes),bundle=parseStrictJson(bundleBytes);
  const root=path.resolve(options['--cases-root']),output=path.resolve(options['--output']);
  safeOutput(output,fs.realpathSync(root));
  requireTrue(bundle.schemaVersion===1&&Array.isArray(bundle.cases),'Invalid installation bundle');
  requireTrue(new Set(bundle.cases.map(row=>row.id)).size===bundle.cases.length,'Duplicate installation case');
  fs.mkdirSync(path.dirname(output),{recursive:true});
  const temporary=fs.mkdtempSync(path.join(path.dirname(output),'.commercial-batch-'));
  let cases;
  try{
    cases=bundle.cases.map(entry=>{requireTrue(/^(INT|STD|MM)-\d{3}$/.test(entry.id),'Invalid case ID');return prepareCase({caseDir:path.join(root,entry.id),bundleRoot:path.dirname(bundlePath),entry,output:path.join(temporary,entry.id)});});
    requireTrue(sha256(fs.readFileSync(bundlePath))===bundleSha256,'Installation bundle changed during preparation');
    fs.writeFileSync(path.join(temporary,'installation-receipt.json'),serialize({schemaVersion:1,bundleSha256,cases}),{flag:'wx'});
    safeOutput(output,fs.realpathSync(root));fs.renameSync(temporary,output);
  }catch(error){fs.rmSync(temporary,{recursive:true,force:true});throw error;}
  process.stdout.write(JSON.stringify({prepared:cases.length,output})+'\n');
}
module.exports={prepareCase,main};
if(require.main===module){try{main();}catch(error){process.stderr.write(error.message+'\n');process.exitCode=1;}}
