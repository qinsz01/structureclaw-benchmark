'use strict';
// Metamorphic grading controls derived from sealed actual jobs. These clones
// are never claimed to be additional native executions or broker receipts.
const fs=require('node:fs'),path=require('node:path'),e=require('./evaluate.cjs');
const read=p=>JSON.parse(fs.readFileSync(p));
function renamed(job,prefix,selectionAliases=false){
 const m=job.state.model,names={};for(const n of m.nodes)names[n.id]=prefix+'joint_'+n.id;for(const element of m.elements)names[element.id]=prefix+'member_'+element.id;
 if(selectionAliases){for(const c of m.load_cases)names[c.id]=prefix+'case_'+c.id;for(const c of m.load_combinations)names[c.id]=prefix+'combo_'+c.id;}
 function text(value){if(names[value])return names[value];const match=/^(case|combination):(.+)$/.exec(value);return match&&names[match[2]]?match[1]+':'+names[match[2]]:value;}
 function visit(value){
  if(typeof value==='string')return text(value);
  if(Array.isArray(value))return value.map(visit);
  if(value&&typeof value==='object')return Object.fromEntries(Object.entries(value).map(([k,v])=>[text(k),visit(v)]));return value;
 }
 const result=visit(job);result.jobId=job.jobId;return result;
}
function main(){
 const [edition,candidateWork,rigidWork,nativeWork,output]=process.argv.slice(2).map(p=>path.resolve(p)),manifest=read(path.join(edition,'manifest.json')),rows=[];
 function check(cid,tid,ref,answer,jobs,current){
  const transforms=[['different-IDs-in-each-job',jobs.map((j,i)=>renamed(j,'job'+i+'_'))]];
  const inactive=jobs.every(j=>['self_weight','rigid_floor','p_delta','rigid_offsets','construction_stage'].every(k=>j.state.model.analysis_control[k]===false));
  if(inactive)transforms.push(['different-IDs-and-selection-aliases-per-job',jobs.map((j,i)=>renamed(j,'job'+i+'_',true))]);
  for(const [name,transformed]of transforms){const result=e.evaluate(ref,answer,transformed,current);rows.push({caseId:cid,turnId:tid,name,scope:'metamorphic-full-evaluator; transformed cloned evidence, no native solver call',passed:result.passed,failures:result.metrics.filter(m=>!m.pass)});}
 }
 for(const work of [candidateWork,rigidWork]){
  const binding=read(path.join(work,'candidate-binding.json'));
  for(const cid of binding.cases){const c=manifest.cases.find(c=>c.id===cid);for(const t of c.turns){
   const dir=path.join(work,'runs',cid,t.id),a=read(path.join(dir,'answer.json')),execution=read(path.join(dir,'execution.json')),ids=a.jobIds||Object.values(a.jobIdsByModel||a.jobIdsByScenario||{}).flat();
   check(cid,t.id,read(path.join(edition,t.private)),a,e.loadJobs(work,cid,ids),execution.currentJobIds);
  }}
 }
 for(const engine of ['PKPM','YJK']){
  const c=manifest.cases.find(c=>c.family==='STD'&&c.engine===engine),t=c.turns[0],dir=path.join(nativeWork,'runs',c.id,t.id),capture=read(path.join(dir,'capture.json')),ref=read(path.join(edition,t.private)),jobs=e.loadJobs(nativeWork,c.id,capture.jobIds),a=e.oracleAnswer(ref,jobs);
  check(c.id,t.id,ref,a,jobs,capture.currentJobIds);
 }
 const result={checks:rows.length,passed:rows.filter(r=>r.passed).length,failed:rows.filter(r=>!r.passed).length,nativeSolversInvoked:0,candidateModelCalls:0,rows};fs.writeFileSync(output,JSON.stringify(result,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify({...result,rows:undefined}));process.exitCode=result.failed?1:0;
}
if(require.main===module)main();module.exports={renamed};
