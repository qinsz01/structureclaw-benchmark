'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const ROOT=path.resolve(__dirname,'../..');
function codeBinding(){
 const pending=['grade_candidate_v32.cjs','evaluate-v32.cjs','physical-v32.cjs','audit-metadata-v32.cjs','controlled-evidence-v32.cjs',
  'prepare_readiness_v32.py','run-configuration-v32.template.json','publish_capture_v32.cjs',
  'prepare_native_bundle_v32.py','capture_structureclaw_worker_v32.py','CaptureWorkerLauncher.cs','Build-CaptureLauncher.ps1']
  .map(name=>path.join(__dirname,name)),seen=new Map();
 while(pending.length){
  const file=fs.realpathSync(pending.pop());
  if(!file.startsWith(ROOT+path.sep))throw Error('SCORING_DEPENDENCY_OUTSIDE_REPOSITORY');
  const relative=path.relative(ROOT,file).split(path.sep).join('/');if(seen.has(relative))continue;
  const bytes=fs.readFileSync(file);seen.set(relative,crypto.createHash('sha256').update(bytes).digest('hex'));
  if(!file.endsWith('.cjs')&&!file.endsWith('.js'))continue;
  for(const match of bytes.toString('utf8').matchAll(/require\(\s*['"]([^'"]+)['"]\s*\)/g)){
   if(!match[1].startsWith('.'))continue;
   let child=path.resolve(path.dirname(file),match[1]);
   if(!fs.existsSync(child)&&fs.existsSync(child+'.cjs'))child+='.cjs';
   if(!fs.existsSync(child)&&fs.existsSync(child+'.js'))child+='.js';
   pending.push(child);
  }
 }
 return Object.fromEntries([...seen].sort(([a],[b])=>a<b?-1:a>b?1:0));
}
module.exports={codeBinding};
