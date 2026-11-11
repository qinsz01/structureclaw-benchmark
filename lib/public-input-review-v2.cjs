'use strict';
// v1 remains immutable for historical replay. v2 never rewrites submissions.
const fs=require('node:fs'),path=require('node:path');
const legacy=require('./public-input-review.cjs');
const {schema,validate}=require('./input-review-schema.cjs');
const {compareLoads,ABSOLUTE,RELATIVE}=require('./input-review-loads.cjs');
const {releasedConventions}=require('./input-review-conventions.cjs');
const VERSION='physical-readback-v2.1';
// Bug fixes version the grader independently of the public packet contract.
const PROTOCOL_VERSION='physical-readback-v2';
const clone=v=>JSON.parse(JSON.stringify(v));
const fail=message=>{throw Error(`Public input review v2: ${message}`);};
const controls=['first_order','linear_elastic','stiffness_reductions','automatic_combinations','full_explicit_stiffness'];
const status=findings=>findings.some(f=>!['missing','missing-clarification','missing-observation','missing-turn-review','unverifiable-extent'].includes(f.code))?'failed':findings.length?'partial':'passed';
function identity(s){
  if(!s||s.schemaVersion!==1||!/^MM-\d{3}$/.test(s.caseId)||!/^t\d+$/.test(s.turnId)||!/^[a-f0-9]{64}$/.test(s.packetSha256||'')||s.method!==legacy.METHOD)fail('invalid submission identity');
  if(!s.reviewer||typeof s.reviewer.id!=='string'||!s.reviewer.id.trim()||!['agent','human'].includes(s.reviewer.kind)||s.reviewer.independent!==true)fail('independent reviewer identity required');
  return s;
}
function prepare(s,context){
  const model=clone(s.model),notes=[],issues=[];
  for(const section of model.sections||[]){
    if(section.shape_units!==undefined){notes.push({path:`/model/sections/${section.id}/shape_units`,code:'descriptive-unit',detail:'Applies only to ungraded shape dimensions; stiffness properties retain m2/m4'});delete section.shape_units;}
    // Shape is explicitly outside physical-stiffness grading. Its units must
    // never rescale A/I/J or escape into the physical model.
    delete section.shape;
  }
  if(model.analysis){
    model.analysis_control??={};const assign=(key,v)=>{
      if(model.analysis_control[key]!==undefined&&model.analysis_control[key]!==v)issues.push({path:`/model/analysis_control/${key}`,code:'conflicting-alias',actual:model.analysis_control[key],alias:v});
      else model.analysis_control[key]=v;
    };
    if(model.analysis.type){assign('first_order',true);assign('linear_elastic',true);}
    if(model.analysis.full_explicit_stiffness!==undefined)assign('full_explicit_stiffness',model.analysis.full_explicit_stiffness);
    if(model.analysis.automatic_reduction!==undefined)assign('stiffness_reductions',model.analysis.automatic_reduction);
    notes.push({path:'/model/analysis',code:'analysis-alias',detail:'Known settings compared against released conventions'});delete model.analysis;
  }
  for(const key of controls)if(model.analysis_control?.[key]!=null&&!Object.hasOwn(context.conventions?.controls||{},key))issues.push({path:`/model/analysis_control/${key}`,code:'unverified-convention',detail:'No released convention establishes this optional setting'});
  const unresolved=clone(s.unresolved);
  for(const u of unresolved)if(u.kind==='element-section'&&u.component==='section'){delete u.component;notes.push({path:'/unresolved',code:'clarification-alias',detail:'element-section already identifies the section component'});}
  return {submission:{...s,model,unresolved},notes,issues};
}
function maskedForLoads(model,context){
  const out=clone(model);
  if(context.turn.expectation!=='clarify')return out;
  if(context.id==='MM-007')for(const lc of out.load_cases||[])for(const load of lc.loads||[])if(load.node==='n1')delete load.fz;
  const unknown=context.id==='MM-072'?['C2','C4','C6','R1','R2','R3','obsR']:context.id==='MM-032'?['U1','U2','U3','U4']:[];
  for(const n of out.nodes||[])if(unknown.includes(n.id))delete n.z;
  return out;
}
function aggregate(dimensions){
  const states=Object.values(dimensions).map(d=>d.status);
  return states.some(s=>['failed','ungradable'].includes(s))?'failed':states.some(s=>s==='partial')?'partial':'passed';
}
function valueAt(model,category,p){
  const [,group,id,...keys]=p.split('/');let v;
  if(group==='properties')v=(category==='sections'?model.sections:model.materials)?.find(r=>r.id===id);
  if(category==='sections'&&group==='properties')v=v?.properties;
  if(group==='nodes')v=model.nodes?.find(r=>r.id===id);
  if(category==='restraints')v=v?.restraints;
  if(category==='settings'&&group==='analysis_control')return model.analysis_control?.[id];
  if(category==='axes'&&group==='rolls')return model.elements?.find(r=>r.id===id)?.rotation_angle??model.axes?.rotationDefaultDegrees;
  for(const key of keys)v=v?.[key];return v;
}
function compareReconstruction(submission,expected,context,packet){
  identity(submission);
  if(submission.caseId!==context.id||packet.caseId&&packet.caseId!==submission.caseId||packet.turnId&&packet.turnId!==submission.turnId)fail('case/turn identity mismatch');
  const protocolFindings=validate(submission),notes=[];
  for(const key of ['load_combinations','nodeOverrides']){
    const ids=new Set();
    for(const [i,row]of (Array.isArray(submission.model?.[key])?submission.model[key]:[]).entries()){
      if(row&&ids.has(row.id))protocolFindings.push({path:`/model/${key}/${i}/id`,code:'duplicate-id',detail:'IDs must be unique; definitions cannot override one another'});
      if(row)ids.add(row.id);
    }
  }
  for(const [i,lc]of (Array.isArray(submission.model?.load_cases)?submission.model.load_cases:[]).entries())for(const [j,l]of (Array.isArray(lc?.loads)?lc.loads:[]).entries()){
    if(l?.extent==='full-member'&&(Object.hasOwn(l,'start')||Object.hasOwn(l,'end')))protocolFindings.push({path:`/model/load_cases/${i}/loads/${j}`,code:'conflicting-extent',detail:'Use extent=full-member without numeric/null start or end'});
  }
  // A legacy packet keeps its original protocol verdict even when the new
  // physical projection can safely interpret an explicitly descriptive field.
  if(packet.protocolVersion!==PROTOCOL_VERSION){
    try{legacy.validateSubmission(submission);}catch(e){protocolFindings.push({path:'/',code:'legacy-protocol',detail:e.message});}
  }
  const empty={physical:{status:'ungradable',findings:[]},protocol:{status:protocolFindings.length?'failed':'passed',findings:protocolFindings},clarification:{status:'ungradable',findings:[]},observations:{status:'ungradable',findings:[]}};
  if(protocolFindings.some(f=>f.path==='/model'||f.path.startsWith('/model/')))return {status:'failed',dimensions:empty,coverage:{},findings:protocolFindings.map(f=>({category:'protocol',...f})),normalizations:notes};
  // Observation/clarification formatting failures must not erase an otherwise
  // interpretable physical readback. Invalid evidence is excluded, not repaired.
  const observationRule=schema.properties.observations.items,unresolvedRule=schema.properties.unresolved.items;
  const projected={...submission,observations:(Array.isArray(submission.observations)?submission.observations:[]).filter(o=>!validate(o,observationRule).length),unresolved:(Array.isArray(submission.unresolved)?submission.unresolved:[]).filter(u=>!validate(u,unresolvedRule).length)};
  const prepared=prepare(projected,context);notes.push(...prepared.notes);protocolFindings.push(...prepared.issues);
  let base;
  const e=clone(expected);
  for(const key of controls)if(prepared.submission.model.analysis_control?.[key]!=null&&Object.hasOwn(context.conventions?.controls||{},key)){
    e.analysis_control??={};e.analysis_control[key]=context.conventions.controls[key];
  }
  let physicalSubmission;
  try{
    physicalSubmission={...prepared.submission,model:legacy.expandReconstruction(prepared.submission.model)};
    base=legacy.compareReconstruction(physicalSubmission,e,context,packet);
  }catch(error){
    protocolFindings.push({path:'/model',code:'unsupported-physical-schema',detail:error.message});
    empty.protocol={status:'failed',findings:protocolFindings};return {status:'failed',dimensions:empty,coverage:{},findings:protocolFindings.map(f=>({category:'protocol',...f})),normalizations:notes};
  }
  const loads=compareLoads(maskedForLoads(physicalSubmission.model,context),maskedForLoads(e,context),context.conventions?.constraints||[]);
  const findings=base.findings.filter(f=>f.category!=='loads'||f.code==='missing-observation');findings.push(...loads.findings);
  for(const f of findings)if(f.code==='mismatch'&&f.category!=='loads'){
    const actual=valueAt(physicalSubmission.model,f.category,f.path),expected=valueAt(e,f.category,f.path);
    if(actual!==undefined&&expected!==undefined){Object.assign(f,{actual,expected});if(typeof actual==='number'&&typeof expected==='number')Object.assign(f,{absoluteError:Math.abs(actual-expected),relativeError:expected===0?null:Math.abs((actual-expected)/expected),tolerance:Math.max(ABSOLUTE,Math.abs(expected)*RELATIVE)});}
  }
  const constraints=context.conventions?.constraints||[];
  for(const c of constraints){
    const known=physicalSubmission.model.nodes.filter(n=>c.nodes.includes(n.id)&&Number.isFinite(n[c.axis]));
    if(known.some(n=>known[0]&&Math.abs(n[c.axis]-known[0][c.axis])>Math.max(ABSOLUTE,Math.abs(known[0][c.axis])*RELATIVE)))findings.push({category:'geometry',path:`/equalCoordinates/${c.axis}/${c.nodes.join(',')}`,code:'mismatch',detail:'Contradicts source-bound equal-coordinate relation'});
  }
  const physical=findings.filter(f=>f.category!=='clarification'&&f.code!=='missing-observation');
  const clarification=findings.filter(f=>f.category==='clarification'),observations=findings.filter(f=>f.code==='missing-observation');
  const dimensions={physical:{status:prepared.issues.some(f=>f.code==='unverified-convention')?'ungradable':status(physical),findings:physical},protocol:{status:protocolFindings.length?'failed':'passed',findings:protocolFindings},clarification:{status:protocolFindings.some(f=>f.path.startsWith('/unresolved'))?'failed':status(clarification),findings:clarification},observations:{status:protocolFindings.some(f=>f.path.startsWith('/observations'))?'failed':status(observations),findings:observations}};
  const coverage={...base.coverage,loads:{...loads.coverage,observation:base.coverage.loads.observation}};
  return {status:aggregate(dimensions),dimensions,coverage,findings:[...findings,...protocolFindings.map(f=>({category:'protocol',...f}))],normalizations:notes,
    numericPolicy:{absolute:ABSOLUTE,relative:RELATIVE,scope:'Input transcription only; solver-result tolerances unchanged'},
    scope:'Disclosed physical facts, source-bound relative geometry, signed load multiset, settings, targeted clarification, protocol and source observations. Descriptive shape dimensions excluded; A/I/J units remain fixed.'};
}
function buildPacketFiles(turns,turnIndex){
  const built=legacy.buildPacketFiles(turns,turnIndex);
  built.files.set('README.md',fs.readFileSync(path.join(__dirname,'../docs/public-input-review-protocol-v2.md')));
  built.files.set('submission-schema.json',legacy.jsonBytes(schema));
  built.descriptor.protocolVersion=PROTOCOL_VERSION;
  built.descriptor.files=[...built.files].map(([p,b])=>({path:p,sha256:legacy.sha256(b),bytes:b.length})).sort((a,b)=>a.path.localeCompare(b.path));
  return built;
}
const publicTurns=record=>record.contract.turns.map((_,i)=>require('./corpus-provider.cjs').getPublicTurnInput(record,i));
function exportPacket(record,index,outDir){
  const built=buildPacketFiles(publicTurns(record),index);if(fs.existsSync(outDir))fail('packet destination already exists');
  fs.mkdirSync(outDir,{recursive:true});for(const [name,b]of built.files){const f=path.join(outDir,name);fs.mkdirSync(path.dirname(f),{recursive:true});fs.writeFileSync(f,b,{flag:'wx'});}
  fs.writeFileSync(path.join(outDir,'packet.json'),legacy.jsonBytes(built.descriptor),{flag:'wx'});
  return {caseId:record.id,turnId:built.descriptor.turnId,path:outDir,packetSha256:legacy.sha256(fs.readFileSync(path.join(outDir,'packet.json')))};
}
function provenanceCheck(p,s){
  if(p.schemaVersion!==1||!legacy.equal(p.reviewer,s.reviewer)||p.method!==legacy.METHOD||p.packetSha256!==s.packetSha256||p.inputScope!=='packet-only'||p.authoringParticipation!==false||p.hiddenAccess!==false||p.freshContext!==true||typeof p.dispatchEvidence!=='string'||!p.dispatchEvidence.trim())fail('independent dispatch provenance incomplete');
}
function sealSubmission({packetDir,submissionFile,provenanceFile,outDir}){
  const {packet,packetSha256}=legacy.verifyPacket(packetDir),bytes=fs.readFileSync(submissionFile),pbytes=fs.readFileSync(provenanceFile),s=identity(JSON.parse(bytes)),p=JSON.parse(pbytes);provenanceCheck(p,s);
  if(packet.protocolVersion!==PROTOCOL_VERSION)fail('Use v2 export for new seals; legacy raw submissions are diagnostic only');
  if(s.caseId!==packet.caseId||s.turnId!==packet.turnId||s.packetSha256!==packetSha256)fail('submission packet binding mismatch');
  if(fs.existsSync(outDir))fail('sealed evidence destination already exists');
  const receipt={schemaVersion:1,protocolVersion:PROTOCOL_VERSION,method:legacy.METHOD,caseId:s.caseId,turnId:s.turnId,inputBinding:packet.inputBinding,packetSha256,submissionSha256:legacy.sha256(bytes),provenanceSha256:legacy.sha256(pbytes),reviewer:s.reviewer,sealedAt:new Date().toISOString()};
  fs.mkdirSync(outDir,{recursive:true});fs.cpSync(packetDir,path.join(outDir,'packet'),{recursive:true,dereference:false,errorOnExist:true});
  fs.writeFileSync(path.join(outDir,'submission.json'),bytes,{flag:'wx'});fs.writeFileSync(path.join(outDir,'provenance.json'),pbytes,{flag:'wx'});fs.writeFileSync(path.join(outDir,'receipt.json'),legacy.jsonBytes(receipt),{flag:'wx'});
  verifySeal(outDir);return receipt;
}
function verifySeal(dir){
  const r=legacy.readJson(legacy.safeFile(dir,'receipt.json')),{packet,packetSha256}=legacy.verifyPacket(path.join(dir,'packet'));
  if(r.schemaVersion!==1||r.protocolVersion!==PROTOCOL_VERSION||packet.protocolVersion!==PROTOCOL_VERSION||r.method!==legacy.METHOD||!Number.isFinite(Date.parse(r.sealedAt))||r.packetSha256!==packetSha256||r.caseId!==packet.caseId||r.turnId!==packet.turnId||!legacy.equal(r.inputBinding,packet.inputBinding))fail('seal packet binding mismatch');
  const b=fs.readFileSync(legacy.safeFile(dir,'submission.json')),pb=fs.readFileSync(legacy.safeFile(dir,'provenance.json'));
  if(legacy.sha256(b)!==r.submissionSha256||legacy.sha256(pb)!==r.provenanceSha256)fail('submission/provenance hash mismatch');
  const s=identity(JSON.parse(b)),p=JSON.parse(pb);provenanceCheck(p,s);
  if(s.caseId!==packet.caseId||s.turnId!==packet.turnId||s.packetSha256!==packetSha256||!legacy.equal(r.reviewer,s.reviewer))fail('sealed identity mismatch');
  return {receipt:r,packet,submission:s,provenance:p};
}
function sourceHashes(){
  return ['lib/public-input-review-v2.cjs','lib/public-input-review.cjs','lib/input-review-schema.cjs','lib/input-review-loads.cjs','lib/input-review-conventions.cjs','lib/input-review-public-facts.json','scripts/research300/blind_input_review_v2.cjs','docs/public-input-review-protocol-v2.md'].map(p=>({path:p,sha256:legacy.sha256(fs.readFileSync(path.join(__dirname,'..',p)))}));
}
function contextFor(record,index,packet){
  const provider=require('./corpus-provider.cjs'),released=record.contract.turns.slice(0,index+1).map((_,i)=>provider.getFrozenPublicTurnInput(record,i));
  const conventions=releasedConventions(released,index,packet);
  return {id:record.id,turn:record.contract.turns[index],conventions,analysisConventions:conventions};
}
function expectedFor(record,index){
  const turn=record.contract.turns[index],state=turn.state??record.contract.turns.slice(index+1).find(t=>t.state!==null)?.state;
  if(!Number.isInteger(state)||!record.contract.modelStates[state-1])fail('missing frozen physical state');
  return legacy.readJson(legacy.safeFile(record.caseDir,record.contract.modelStates[state-1]));
}
function gradeEvidence(record,receiptPaths){
  if(!receiptPaths.length)fail('sealed evidence required');
  const inputs=publicTurns(record),turns=[],seen=new Set();
  for(const relative of receiptPaths){
    const file=legacy.safeFile(record.root,relative),dir=path.dirname(file),sealed=verifySeal(dir),i=inputs.findIndex(t=>t.turnId===sealed.packet.turnId);
    if(path.basename(file)!=='receipt.json'||sealed.packet.caseId!==record.id||i<0||seen.has(sealed.packet.turnId))fail('wrong/duplicate turn evidence');seen.add(sealed.packet.turnId);
    const built=buildPacketFiles(inputs,i);if(!legacy.equal(sealed.packet,built.descriptor))fail('packet differs from current authoritative input/protocol');
    const context=contextFor(record,i,sealed.packet),g=compareReconstruction(sealed.submission,expectedFor(record,i),context,sealed.packet);
    const evidence=Object.fromEntries([['receipt','receipt.json'],['packet','packet/packet.json'],['submission','submission.json'],['provenance','provenance.json']].map(([key,name])=>{const f=legacy.safeFile(dir,name);return [key,{path:path.relative(record.root,f).split(path.sep).join('/'),sha256:legacy.sha256(fs.readFileSync(f))}];}));
    for(const [j,source]of context.conventions.sources.entries())evidence[`publicConvention${j+1}`]={path:path.relative(record.root,source.path).split(path.sep).join('/'),sha256:source.sha256};
    turns.push({turnId:sealed.packet.turnId,...g,reviewer:sealed.submission.reviewer,evidence,relativeGeometrySources:context.conventions.geometrySources});
  }
  turns.sort((a,b)=>inputs.findIndex(i=>i.turnId===a.turnId)-inputs.findIndex(i=>i.turnId===b.turnId));
  const missing=inputs.filter(i=>!seen.has(i.turnId)).map(i=>({turnId:i.turnId,code:'missing-turn-review'}));
  const findings=[...turns.flatMap(t=>t.findings.map(f=>({turnId:t.turnId,...f}))),...missing];
  const dimensions=Object.fromEntries(['physical','protocol','clarification','observations'].map(key=>{
    const states=turns.map(t=>t.dimensions[key].status);return [key,{status:states.some(s=>['failed','ungradable'].includes(s))?'failed':missing.length||states.includes('partial')?'partial':'passed'}];
  }));
  return {schemaVersion:1,caseId:record.id,inputEdition:'current',inputBinding:inputs[0].inputBinding,method:legacy.METHOD,grader:{version:VERSION,sources:sourceHashes()},status:aggregate(dimensions),dimensions,findings,turns};
}
function getPublicInputReview(record,binding){
  const base={schemaVersion:1,caseId:record.id,status:'pending',verified:false};
  const file=legacy.reviewPath(record,binding);if(!file||!fs.existsSync(file))return base;
  try{
    const report=legacy.readJson(file);if(report.grader?.version!==VERSION||!legacy.equal(report.inputBinding,binding)||!Array.isArray(report.turns))fail('version or input binding mismatch');
    const replay=gradeEvidence(record,report.turns.map(t=>t.evidence.receipt.path));if(!legacy.equal(replay,report))fail('report differs from sealed replay');
    return {...report,verified:true};
  }catch(error){return {...base,status:'invalid',findings:[{code:'invalid-evidence',detail:error.message}]};}
}
module.exports={...legacy,VERSION,PROTOCOL_VERSION,compareReconstruction,buildPacketFiles,exportPacket,sealSubmission,verifySeal,gradeEvidence,getPublicInputReview,contextFor,expectedFor,sourceHashes,schema};
