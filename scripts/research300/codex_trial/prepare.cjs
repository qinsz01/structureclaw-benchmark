'use strict';
// Coordinator-only preparation. No hidden physical model or answer goes into a prompt.
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const ROOT=path.resolve(__dirname,'../../..'),{prepareEvaluation,caseContext}=require(path.join(ROOT,'lib/result-import.cjs'));
const work=path.resolve(process.argv[2]),base=path.resolve(process.argv[3]);
const corpusRoot=path.resolve(process.argv[4]||ROOT);
const extra=process.argv.slice(5);
if(extra.length&&(extra.length!==2||extra[0]!=='--cases'))throw Error('Optional arguments: --cases ID,ID');
const selected=extra.length?extra[1].split(','):null;
if(selected&&(!selected.length||selected.some(id=>!id)||new Set(selected).size!==selected.length))throw Error('Case selection must be nonempty and unique');
fs.mkdirSync(work,{recursive:true});fs.mkdirSync(base,{recursive:true});
const available=fs.readdirSync(path.join(corpusRoot,'corpora/research-300/cases')).filter(id=>/^(STD|INT|MM)-\d{3}$/.test(id)).sort();
if(selected?.some(id=>!available.includes(id)))throw Error('Unknown selected case');
const list=available.filter(id=>!selected||selected.includes(id));
const plan=[];
for(const caseId of list){
 const contract=JSON.parse(fs.readFileSync(path.join(corpusRoot,'corpora/research-300/cases',caseId,'contract.json')));
 const expected=caseContext(caseId,corpusRoot).context;
 fs.mkdirSync(path.join(base,caseId,'scratch','requests'),{recursive:true});fs.mkdirSync(path.join(base,caseId,'solver-replies'),{recursive:true});
 const turns=[];
 for(const t of contract.turns){
  const out=path.join(base,caseId,t.id);
  if(!fs.existsSync(out))prepareEvaluation({root:corpusRoot,caseId,turn:t.id,output:out});
  if(!require('node:util').isDeepStrictEqual(JSON.parse(fs.readFileSync(path.join(out,'capture-context.json'))),expected))throw Error('Existing prepared context belongs to a different corpus edition');
  turns.push({id:t.id,publicDir:path.join(out,'agent-input'),context:path.join(out,'capture-context.json')});
 }
 plan.push({caseId,engine:contract.plannedEngine,turns,figureOutputIds:contract.requiredOutputs.filter(o=>o.kind==='figure').map(o=>o.id)});
}
const bytes=JSON.stringify(plan,null,2)+'\n';if(fs.existsSync(path.join(work,'plan.json'))){if(JSON.stringify(JSON.parse(fs.readFileSync(path.join(work,'plan.json'))))!==JSON.stringify(plan))throw Error('Dispatch plan differs from prepared public metadata');}else fs.writeFileSync(path.join(work,'plan.json'),bytes,{flag:'wx'});
const binding={schemaVersion:1,root:corpusRoot,contexts:plan.map(c=>({caseId:c.caseId,sha256:crypto.createHash('sha256').update(fs.readFileSync(c.turns[0].context)).digest('hex')}))};
const bindingPath=path.join(work,'corpus-binding.json');
if(fs.existsSync(bindingPath)){if(JSON.stringify(JSON.parse(fs.readFileSync(bindingPath)))!==JSON.stringify(binding))throw Error('Trial corpus binding differs');}
else fs.writeFileSync(bindingPath,JSON.stringify(binding,null,2)+'\n',{flag:'wx'});
if(!fs.existsSync(path.join(work,'plan-sha256.txt')))fs.writeFileSync(path.join(work,'plan-sha256.txt'),crypto.createHash('sha256').update(bytes).digest('hex')+'\n',{flag:'wx'});
process.stdout.write(JSON.stringify({cases:plan.length,turns:plan.reduce((a,c)=>a+c.turns.length,0)})+'\n');
