'use strict';
// Re-evaluate retained maintainer originals and all frozen mutation controls.
// No candidate, solver, or collector is invoked. This is NOT a qualification
// receipt for the new capture path and cannot grant a formal comparison score.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const e=require('./evaluate-v33.cjs'),{controls}=require('./controls-v33.cjs');
const {codeBinding}=require('./code-closure-v32.cjs');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const read=p=>JSON.parse(fs.readFileSync(p));
function replay({edition,work,answers,output,caseIds,onProgress=()=>{}}){
 [edition,work,answers]=[edition,work,answers].map(p=>fs.realpathSync(p));output=path.resolve(output);
 for(const root of [edition,work,answers])if(output===root||output.startsWith(root+path.sep)||root.startsWith(output+path.sep))throw Error('Replay output overlaps retained originals');
 const manifestBytes=fs.readFileSync(path.join(edition,'manifest.json')),manifest=JSON.parse(manifestBytes);
 for(const row of manifest.files){const file=path.resolve(edition,row.path);
  if(!file.startsWith(edition+path.sep)||fs.realpathSync(file)!==file||sha(fs.readFileSync(file))!==row.sha256)throw Error('Frozen edition changed: '+row.path);}
 if(caseIds&&(!Array.isArray(caseIds)||new Set(caseIds).size!==caseIds.length||caseIds.some(id=>!manifest.cases.some(c=>c.id===id))))throw Error('Unknown or repeated replay case');
 const cases=manifest.cases.filter(c=>!caseIds||caseIds.includes(c.id)),rows=[];
 fs.mkdirSync(output,{recursive:false});
 const write=(name,value)=>fs.writeFileSync(path.join(output,name),JSON.stringify(value,null,2)+'\n',{flag:'wx'});
 const sourceCode={...codeBinding(),...Object.fromEntries(['evaluate-v33.cjs','controls-v33.cjs','replay_retained_v33.cjs'].map(name=>[
  'scripts/research300_v3/'+name,sha(fs.readFileSync(path.join(__dirname,name)))]))};
 for(const c of cases)for(const t of c.turns){
  const base={caseId:c.id,turnId:t.id,kind:c.analysis};let row;
  try{
   const capture=read(path.join(work,'runs',c.id,t.id,'capture.json'));
   const jobs=e.loadJobs(work,c.id,capture.jobIds),ref=read(path.join(edition,t.private));
   const bytes=fs.readFileSync(path.join(answers,c.id,t.id,'answer.json')),answer=JSON.parse(bytes);
   const result=e.evaluate(ref,answer,jobs,capture.currentJobIds),checks=controls(ref,answer,jobs,capture.currentJobIds);
   const name=c.id+'-'+t.id+'.json';write(name,{answerSha256:sha(bytes),result,controls:checks});
   row={...base,passed:result.passed,outcome:result.outcome,controls:checks.length,
    controlsPassed:checks.filter(r=>r.passed).length,failures:result.metrics.filter(m=>!m.pass),
    controlFailures:checks.filter(r=>!r.passed).map(r=>r.name),answerSha256:sha(bytes),details:name};
  }catch(error){row={...base,passed:false,controls:0,controlsPassed:0,error:error.stack};}
  rows.push(row);onProgress({caseId:c.id,turnId:t.id,passed:row.passed,done:rows.length});
 }
 const result={kind:'research300-v3-offline-regression',revision:'v3.3',manifestSha256:sha(manifestBytes),
  cases:cases.length,turns:rows.length,positivePassed:rows.filter(r=>r.passed).length,
  controls:rows.reduce((s,r)=>s+r.controls,0),controlsPassed:rows.reduce((s,r)=>s+r.controlsPassed,0),
  fullEditionCoverage:cases.length===manifest.cases.length,
  allPassed:rows.length>0&&rows.every(r=>r.passed&&r.controls>0&&r.controlsPassed===r.controls),
  runtimeQualified:false,formalComparisonScore:false,candidateInvocations:0,nativeSolverInvocations:0,
  evidenceScope:'Retained maintainer broker originals and saved answers; does not validate current native deployment, collector or input delivery',
  numericalTolerancesChanged:false,sourceCode,rows};
 write('summary.json',result);return result;
}
if(require.main===module){
 try{
  const args=process.argv.slice(2),opts={},fields={'--edition':'edition','--work':'work','--answers':'answers','--output':'output','--case-list':'caseList'};
  for(let i=0;i<args.length;i++){if(!fields[args[i]]||!args[i+1])throw Error('Invalid replay option');opts[fields[args[i]]]=args[++i];}
  if(['edition','work','answers','output'].some(k=>!opts[k]))throw Error('Explicit edition, retained work, answers and new output required');
  if(opts.caseList)opts.caseIds=read(opts.caseList);
  opts.onProgress=row=>process.stdout.write(JSON.stringify(row)+'\n');
  const result=replay(opts);process.stdout.write(JSON.stringify({...result,rows:undefined})+'\n');process.exitCode=result.allPassed?0:1;
 }catch(error){process.stderr.write(error.stack+'\n');process.exitCode=2;}
}
module.exports={replay};
