import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';

const viewer=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const root=path.dirname(viewer),edition=path.join(root,'corpora/research300-v3-v1');
const legacyReview=path.join(root,'docs/implementation/reviews/research300-v3-20261028');
const fullReview=path.join(root,'docs/implementation/reviews/research300-v3-codex-full-20261028');
const full=fs.existsSync(path.join(fullReview,'codex-full.json'))&&fs.existsSync(path.join(fullReview,'catalogue.xlsx'));
const review=full?fullReview:legacyReview;
const reviewed=full&&fs.existsSync(path.join(review,'codex-full-reviewed.json'));
const output=path.join(viewer,'public/research300-v3');
const read=file=>JSON.parse(fs.readFileSync(file,'utf8'));
const manifest=read(path.join(edition,'manifest.json'));
const hashes=new Map(manifest.files.map(r=>[r.path,r.sha256]));
const reports=(full?[reviewed?'codex-full-reviewed.json':'codex-full.json']:['codex-development12.json','codex-rigid-supplement.json']).map(n=>read(path.join(review,n)));
if(reviewed&&reports[0].evaluationRevision!=='v3.1')throw Error('Unknown full-suite scoring revision');
const manifestHash=crypto.createHash('sha256').update(fs.readFileSync(path.join(edition,'manifest.json'))).digest('hex');
if(reports.some(r=>r.manifestSha256!==manifestHash))throw Error('Candidate grade belongs to another edition');
const grades=reports.flatMap(r=>r.rows);
const byTurn=new Map(grades.map(r=>[r.caseId+'/'+r.turnId,r]));
const executions=full?new Map(read(path.join(review,'execution-index.json')).rows.map(r=>[r.caseId+'/'+r.turnId,r])):new Map();
const integrity=full?new Map(read(path.join(review,'answer-integrity.json')).files.filter(r=>r.present).map(r=>[r.caseId+'/'+r.turnId,r])):new Map();
const issuedTurns=new Set(manifest.cases.flatMap(c=>c.turns.map(t=>c.id+'/'+t.id)));
if(grades.some(r=>!issuedTurns.has(r.caseId+'/'+r.turnId)))throw Error('Candidate grade references an unknown turn');
const copies=[];
const answerCopies=[];
function submission(file,key){
 if(!fs.existsSync(file)){if(full&&integrity.has(key))throw Error('Recorded candidate answer is missing: '+key);return {answer:null,answerPresent:false};}
 if(fs.lstatSync(file).isSymbolicLink())throw Error('Symlink in candidate answer');
 const bytes=fs.readFileSync(file),raw=bytes.toString('utf8'),digest=crypto.createHash('sha256').update(bytes).digest('hex');
 if(full&&integrity.get(key)?.sha256!==digest)throw Error('Candidate answer binding differs: '+key);
 let answer=null,validJson=true;try{answer=JSON.parse(raw);}catch{validJson=false;}
 const target='codex-answers/'+key+'.json';answerCopies.push([file,target]);
 return {answer,answerRaw:raw,answerPresent:true,answerValidJson:validJson,answerFile:target};
}
function collect(folder,relative){
 for(const entry of fs.readdirSync(folder,{withFileTypes:true})){
  const source=path.join(folder,entry.name),name=relative+'/'+entry.name;
  if(entry.isSymbolicLink())throw Error('Symlink in public packet');
  if(entry.isDirectory())collect(source,name);
  else{const expected=hashes.get(name),actual=crypto.createHash('sha256').update(fs.readFileSync(source)).digest('hex');if(!expected||actual!==expected)throw Error('Public packet binding differs: '+name);copies.push([source,name]);}
 }
}
const cases=manifest.cases.map(c=>{
 const turns=c.turns.map(t=>{
  collect(path.join(edition,t.public),t.public);const key=c.id+'/'+t.id,grade=byTurn.get(key),run=executions.get(key),answerFile=path.join(review,'codex-answers',c.id,t.id+'.json');
  return {id:t.id,base:t.public,task:read(path.join(edition,t.public,'task.json')),
   candidate:grade?{passed:grade.passed,seconds:run?.elapsedSeconds??grade.elapsedSeconds??0,jobs:run?.currentNativeJobs??grade.currentNativeJobs??0,
    status:grade.status||(grade.passed?'passed':'scored-failure'),failures:grade.failures||[],error:grade.error||'',
    ...submission(answerFile,key)}:null};
 });
 return {id:c.id,family:c.family,level:c.level,engine:c.engine,analysis:c.analysis,
  integration:c.integration||'',origin:c.origin,sourceId:c.sourceId||'',title:c.title,split:c.split,turns};
});
if(cases.length!==300||cases.reduce((n,c)=>n+c.turns.length,0)!==560||grades.length!==(full?560:22)||byTurn.size!==grades.length)throw Error('V3 review counts differ');
if(fs.existsSync(output)&&fs.lstatSync(output).isSymbolicLink())throw Error('Unsafe review output');
fs.rmSync(output,{recursive:true,force:true});fs.mkdirSync(output,{recursive:true});
for(const [source,name]of copies){const target=path.join(output,name);fs.mkdirSync(path.dirname(target),{recursive:true});fs.copyFileSync(source,target);}
for(const [source,name]of answerCopies){const target=path.join(output,name);fs.mkdirSync(path.dirname(target),{recursive:true});fs.copyFileSync(source,target);}
for(const name of ['index.html','app.js','style.css'])fs.copyFileSync(path.join(viewer,'v3',name),path.join(output,name));
fs.copyFileSync(path.join(review,'catalogue.xlsx'),path.join(output,'catalogue.xlsx'));
fs.writeFileSync(path.join(output,'catalogue.json'),JSON.stringify({summary:manifest.summary,cases,
 candidate:{cases:new Set(grades.map(r=>r.caseId)).size,turns:grades.length,passed:grades.filter(r=>r.passed).length,
  validationScope:full?'full-suite':'development',evaluationRevision:reports[0].evaluationRevision||'frozen-first-grade',
  initialPassed:full?read(path.join(review,'codex-full.json')).passed:grades.filter(r=>r.passed).length,
  formalComparisonScore:false},preflight:{turns:560,passed:560,jobs:1993},
 reviewerOnly:true,note:'维护者浏览页面，包含全部轮次与候选作答；不得用作候选模型输入。'}));
console.log(JSON.stringify({v3Cases:cases.length,turns:560,candidateTurns:grades.length,publicFiles:copies.length}));
