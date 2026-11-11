// v3.1 review of full-suite evidence; frozen predecessor grade_candidate.cjs SHA256 79ad453cac39126a2be6607874a7c908cc5af0ef55297cec4f935bce955288a0.
'use strict';
// Call after capture; no output from this process is ever supplied to candidates.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),e=require('./evaluate-v31.cjs');
const read=p=>JSON.parse(fs.readFileSync(p)),sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
function grade(edition,work){
 const manifest=read(path.join(edition,'manifest.json')),binding=read(path.join(work,'candidate-binding.json'));if(binding.manifestSha256!==sha(path.join(edition,'manifest.json')))throw Error('Candidate input edition changed');const rows=[];
 for(const [name,digest]of Object.entries(binding.evaluationCode||{}))if(sha(path.join(__dirname,name))!==digest)throw Error('Frozen first-grade source changed: '+name);
 for(const row of manifest.files){const file=path.resolve(edition,row.path);if(!file.startsWith(edition+path.sep)||sha(file)!==row.sha256)throw Error('Frozen edition bytes changed: '+row.path);}
 if(new Set(binding.cases).size!==binding.cases.length)throw Error('Candidate case selection repeats');
 for(const cid of binding.cases){const c=manifest.cases.find(c=>c.id===cid);if(!c||(!binding.fullSuite&&c.split!=='dev'))throw Error('Calibration selection differs');
  for(const t of c.turns){const dir=path.join(work,'runs',cid,t.id);if(!fs.existsSync(path.join(dir,'execution.json'))) {rows.push({caseId:cid,turnId:t.id,passed:false,status:'uncaptured'});continue;}
   const execution=read(path.join(dir,'execution.json'));try{
    const answer=read(path.join(dir,'answer.json')),ids=answer.jobIds||Object.values(answer.jobIdsByModel||answer.jobIdsByScenario||{}).flat();
    const jobs=e.loadJobs(work,cid,ids),result=e.evaluate(read(path.join(edition,t.private)),answer,jobs,execution.currentJobIds);
    rows.push({caseId:cid,turnId:t.id,level:c.level,family:c.family,kind:c.analysis,passed:result.passed,jobIds:ids,currentNativeJobs:execution.currentJobIds.length,elapsedSeconds:execution.elapsedSeconds,failures:result.metrics.filter(m=>!m.pass)});
   }catch(error){rows.push({caseId:cid,turnId:t.id,level:c.level,family:c.family,passed:false,status:'invalid-or-missing-evidence',error:error.message});}
  }
 }
 return {evaluationRevision:'v3.1',frozenFirstGradeSourcesVerified:true,
  reviewedEvaluationCode:Object.fromEntries(['grade_candidate_v31.cjs','evaluate-v31.cjs','physical-v31.cjs'].map(n=>[n,sha(path.join(__dirname,n))])),
  developmentOnly:!binding.fullSuite,...(binding.fullSuite?{validationScope:'full-suite',formalComparisonScore:false,fullEditionCoverage:binding.cases.length===manifest.cases.length}:{}),model:binding.model,manifestSha256:binding.manifestSha256,cases:binding.cases.length,turns:rows.length,passed:rows.filter(r=>r.passed).length,failed:rows.filter(r=>!r.passed).length,completeCases:binding.cases.filter(cid=>rows.filter(r=>r.caseId===cid).every(r=>r.passed)).length,rows};
}
if(require.main===module){const [edition,work,output]=process.argv.slice(2).map(p=>path.resolve(p)),result=grade(edition,work);fs.writeFileSync(output,JSON.stringify(result,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify({...result,rows:undefined}));}module.exports={grade};
