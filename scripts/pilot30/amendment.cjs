'use strict';
// Audit presentation-only changes against the edition actually executed.
// Never relabel an old capture or accept changed numerical/model references.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
function verifiedManifest(dir){
 const m=read(path.join(dir,'manifest.json'));
 for(const f of m.files)if(sha(path.join(dir,f.path))!==f.sha256)throw Error('Edition changed: '+f.path);
 return m;
}
function deliveryAmendment(executed,edition){
 const a=verifiedManifest(executed),b=verifiedManifest(edition),same=(x,y)=>JSON.stringify(x)===JSON.stringify(y);
 const {files:af,...am}=a,{files:bf,...bm}=b;
 if(!same(am,bm)||!same(af.map(f=>f.path),bf.map(f=>f.path)))throw Error('Edition metadata or file set changed');
 const changed=[];
 for(let i=0;i<af.length;i++)if(af[i].sha256!==bf[i].sha256){
  const name=af[i].path;
  if(!/^cases\/[^/]+\/public\/[^/]+\/delivery\.md$/.test(name)){
   if(name!=='cases/P30-STD-009/public/t1/task.json')throw Error('Non-delivery file changed: '+name);
   const before=read(path.join(executed,name)),after=read(path.join(edition,name));
   before.instruction=before.instruction.replace('source-basis.md','source-basis.json');
   if(!same(before,after))throw Error('Unexpected task amendment');
  }
  changed.push({path:name,before:af[i].sha256,after:bf[i].sha256});
 }
 return {kind:'public-delivery-only',executionManifestSha256:sha(path.join(executed,'manifest.json')),
  qualificationManifestSha256:sha(path.join(edition,'manifest.json')),privateReferencesIdentical:true,
  numericalInputsIdentical:true,changedFiles:changed};
}
module.exports={verifiedManifest,deliveryAmendment};
