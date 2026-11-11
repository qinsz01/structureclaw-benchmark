'use strict';
// All positives are assembled from actual broker results. No candidate calls.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {evaluate,oracleAnswer,loadJobs,physical,parametersMatch}=require('./evaluate.cjs');
const {verifiedManifest,deliveryAmendment}=require('./amendment.cjs');
const {closedPlanarDomain,liftPlanar}=require('../challenge/physical-view-v3.cjs');
const clone=v=>JSON.parse(JSON.stringify(v)),read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const args=Object.fromEntries(process.argv.slice(2).reduce((r,v,i,a)=>i%2?r:[...r,[v.slice(2),a[i+1]]],[]));
const edition=path.resolve(args.edition),work=path.resolve(args.work),output=path.resolve(args.output);
if(!fs.existsSync(path.join(work,'execution-summary.json')))throw Error('Complete the oracle run before qualification');
if(fs.existsSync(output))throw Error('New qualification directory required');fs.mkdirSync(output,{recursive:true});
const manifest=verifiedManifest(edition),hash=crypto.createHash('sha256').update(fs.readFileSync(path.join(edition,'manifest.json'))).digest('hex');
const amendment=args['execution-edition']?deliveryAmendment(path.resolve(args['execution-edition']),edition):null;
const executionHash=amendment?.executionManifestSha256||hash;
if(amendment)fs.writeFileSync(path.join(output,'delivery-amendment.json'),JSON.stringify(amendment,null,2)+'\n');
const rows=[];
for(const item of manifest.cases)for(const t of item.turns){
 const folder=path.join(work,'runs',item.id,t.id),ref=read(path.join(edition,t.private)),record={caseId:item.id,turnId:t.id,kind:ref.kind,controls:[]};
 try{
  const capture=read(path.join(folder,'capture.json'));if(capture.manifestSha256!==executionHash)throw Error('Wrong execution edition');
  const jobs=loadJobs(work,item.id,capture.jobIds),schemeFile=path.join(folder,'scheme-jobs.json');
  const answer=oracleAnswer(ref,jobs,fs.existsSync(schemeFile)?read(schemeFile):{});
  const result=evaluate(ref,answer,jobs,capture.currentJobIds);record.positive=result;
  const test=(name,r,a,j,current,expected)=>{const x=evaluate(r,a,j,current);record.controls.push({name,passed:x.passed===expected,expected,actual:x.passed,metrics:x.metrics});};
  if(result.passed){
   if(ref.kind==='clarify'){
    const bad=clone(answer);bad.clarifications[0].field='wrong';test('wrong-clarification',ref,bad,jobs,[],false);
    test('premature-execution',ref,answer,[{jobId:'fake'}],['fake'],false);
   }else{
    test('missing-execution',ref,answer,[],[],false);
    const altered=clone(jobs);altered[0].state.model.materials[0].E*=1.2;
    test('wrong-stiffness',ref,answer,altered,capture.currentJobIds,false);
    const bad=clone(answer);
    if(bad.quantities.length){bad.quantities[0].value+=Math.max(1,Math.abs(bad.quantities[0].value));}
    else if(bad.schemes?.length)bad.schemes[0].maximum+=1;
    test('wrong-reported-number',ref,bad,jobs,capture.currentJobIds,false);
    if(ref.model.coordinate_system.dimension==='2d'){
     const alternative=clone(ref.model);for(const s of alternative.sections)if(s.properties.J)s.properties.J*=1.05;
     record.controls.push({name:'inactive-2d-J-physical-only',scope:'physical-comparator-only',passed:physical(alternative,ref.model).pass});
     if(closedPlanarDomain(ref.model)&&ref.model.elements.every(e=>!e.releases&&!e.offsets)){
      const embedded=liftPlanar(ref.model);
      record.controls.push({name:'canonical-restrained-spatial-embedding',scope:'physical-comparator-only',passed:physical(embedded,ref.model).pass});
      const free=clone(embedded);free.nodes[0].restraints[1]=false;
      record.controls.push({name:'spatial-embedding-free-transverse-dof',scope:'physical-comparator-only',passed:!physical(free,ref.model).pass});
     }
    }else if(ref.model.elements.every(e=>['truss','brace'].includes(e.type))){
     const alternative=clone(ref.model);for(const s of alternative.sections)if(s.properties.J)s.properties.J*=1.05;
     record.controls.push({name:'inactive-truss-J-physical-only',scope:'physical-comparator-only',passed:physical(alternative,ref.model).pass});
     const bad=clone(ref.model);for(const e of bad.elements)e.type='beam';
     record.controls.push({name:'truss-as-beams-rejected',scope:'physical-comparator-only',passed:!physical(bad,ref.model).pass});
    }
    const length=answer.quantities.find(q=>q.unit==='m');
    if(length){const alternative=clone(answer),q=alternative.quantities.find(q=>q.id===length.id);q.value*=1000;q.unit='mm';test('equivalent-mm',ref,alternative,jobs,capture.currentJobIds,true);}
    if(ref.kind==='query')test('query-new-execution',ref,answer,jobs,capture.jobIds,false);
    if(ref.model.analysis_control.self_weight){
     const explicit=clone(ref.model);explicit.analysis_control.gravity_direction='-z';
     record.controls.push({name:'explicit-default-gravity-direction',scope:'physical-comparator-only',passed:physical(explicit,ref.model).pass});
     const wrong=clone(ref.model);wrong.analysis_control.gravity_direction='x';
     record.controls.push({name:'wrong-gravity-direction',scope:'physical-comparator-only',passed:!physical(wrong,ref.model).pass});
    }
    if(item.id==='P30-STD-001'){
     const refined=clone(ref.model),e=refined.elements[0],ends=e.nodes.map(id=>refined.nodes.find(n=>n.id===id));
     const nid='equivalent-cut',eid='equivalent-part';
     refined.nodes.push({id:nid,x:(ends[0].x+ends[1].x)/2,y:0,z:(ends[0].z+ends[1].z)/2,restraints:[false,true,false,true,false,true]});
     e.nodes=[ends[0].id,nid];refined.elements.push({...clone(e),id:eid,nodes:[nid,ends[1].id]});
     const half=Math.hypot(ends[1].x-ends[0].x,ends[1].y-ends[0].y,ends[1].z-ends[0].z)/2;
     for(const c of refined.load_cases)c.loads=c.loads.flatMap(l=>l.element===e.id?
      [{...clone(l),start:0,end:half},{...clone(l),id:l.id+'-part',element:eid,start:0,end:half}]:[l]);
     record.controls.push({name:'canonical-2d-collinear-refinement',scope:'physical-comparator-only',passed:physical(refined,ref.model).pass});
     refined.nodes.find(n=>n.id===nid).restraints[2]=true;
     record.controls.push({name:'refinement-added-active-support',scope:'physical-comparator-only',passed:!physical(refined,ref.model).pass});
    }
    if(ref.derived?.length){const bad=clone(answer);
     bad.derived[0].value=Math.abs(bad.derived[0].value)>1e-6?-bad.derived[0].value:1;
     test('wrong-derived-value-or-sign',ref,bad,jobs,capture.currentJobIds,false);}
    if(ref.requireShapes){
     const equivalent=clone(answer);for(const m of equivalent.modeShapes)for(const n in m.values)m.values[n]*=-3;
     test('shape-sign-and-scale',ref,equivalent,jobs,capture.currentJobIds,true);
     const zero=clone(answer);for(const m of zero.modeShapes)for(const n in m.values)m.values[n]=0;
     test('zero-modal-shape',ref,zero,jobs,capture.currentJobIds,false);
     const broken=clone(jobs);for(const mode of broken[0].state.dynamicResult.data.modes)for(const value of Object.values(mode.modeShape))value[0]=0;
     test('broken-native-modal-shape',ref,answer,broken,capture.currentJobIds,false);
    }
    if(ref.requests.some(q=>q.time!==undefined)){
     const bad=clone(answer);bad.quantities.find(q=>q.time!==undefined).time+=.02;
     test('wrong-reported-peak-time',ref,bad,jobs,capture.currentJobIds,false);
     const broken=clone(jobs);for(const row of broken[0].state.dynamicResult.data.timeHistory)row.time+=.02;
     test('wrong-native-peak-time',ref,answer,broken,capture.currentJobIds,false);
    }
    if(ref.kind==='scheme'){
     const wrong=clone(answer);wrong.selectedScheme='nonexistent';test('invalid-scheme-choice',ref,wrong,jobs,capture.currentJobIds,false);
     const impossible=clone(ref);impossible.constraint.absoluteLimit=0;
     const alternative=oracleAnswer(impossible,jobs,read(schemeFile));
     test('explicit-no-feasible-scheme',impossible,alternative,jobs,capture.currentJobIds,true);
    }
   }
  }
  fs.writeFileSync(path.join(output,item.id+'-'+t.id+'-answer.json'),JSON.stringify(answer,null,2)+'\n');
 }catch(e){record.error=e.stack;}
 record.passed=!!record.positive?.passed&&record.controls.every(c=>c.passed);
 fs.writeFileSync(path.join(output,item.id+'-'+t.id+'.json'),JSON.stringify(record,null,2)+'\n');rows.push(record);
 console.log(JSON.stringify({caseId:item.id,turnId:t.id,passed:record.passed,error:record.error||record.positive?.metrics.filter(m=>!m.pass)}));
}
const summary={edition:manifest.edition,manifestSha256:hash,executionManifestSha256:executionHash,
 publicDeliveryAmended:!!amendment,role:'maintainer-oracle-and-counterexamples',candidateCalls:0,
 cases:manifest.cases.length,turns:rows.length,passedTurns:rows.filter(r=>r.passed).length,
 controls:rows.reduce((n,r)=>n+r.controls.length,0),failedControls:rows.flatMap(r=>r.controls).filter(c=>!c.passed).length,
 allPassed:rows.every(r=>r.passed),rows:rows.map(({positive,controls,error,...r})=>({...r,error:error?.split('\n')[0]}))};
fs.writeFileSync(path.join(output,'summary.json'),JSON.stringify(summary,null,2)+'\n');
console.log(JSON.stringify({summary:{...summary,rows:undefined}}));process.exitCode=summary.allPassed?0:1;
