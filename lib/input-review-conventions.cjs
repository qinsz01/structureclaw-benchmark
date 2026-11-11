'use strict';
const fs=require('node:fs');
const legacy=require('./public-input-review.cjs');
const publicFacts=require('./input-review-public-facts.json');
function releasedConventions(turns,turnIndex,packet) {
  const controls={},sources=[];
  const assign=(key,value)=>{if(Object.hasOwn(controls,key)&&controls[key]!==value)throw Error(`Conflicting released analysis convention: ${key}`);controls[key]=value;};
  for(const turn of turns.slice(0,turnIndex+1))for(const a of turn.attachments){
    if(!/\.(txt|md|json)$/i.test(a.name))continue;
    const bytes=fs.readFileSync(a.path),hash=legacy.sha256(bytes);
    if(a.sha256&&a.sha256!==hash)throw Error('Released public convention hash mismatch');
    const text=bytes.toString('utf8');let recognized=false;
    if(/First-order linear elastic static analysis|first-order linear elastic static;|一阶线弹性静力/.test(text)){
      assign('first_order',true);assign('linear_elastic',true);recognized=true;
    }
    if(/No P-delta, (?:rigid )?diaphragm, rigid offsets, stiffness reductions, or automatic combinations\.|不开启 P-delta、刚性楼板、刚域、刚度折减或默认组合。/.test(text)){
      assign('stiffness_reductions',false);assign('automatic_combinations',false);recognized=true;
    }
    if(/use full explicit stiffness; no automatic reduction/.test(text)){
      assign('full_explicit_stiffness',true);assign('stiffness_reductions',false);recognized=true;
    }
    if(recognized)sources.push({turnId:turn.turnId,path:a.path,sha256:hash});
  }
  const constraints=[],geometrySources=[];
  for(const record of publicFacts.records){
    if(!packet.files.some(f=>f.path===record.sourcePath&&f.sha256===record.sourceSha256))continue;
    for(const c of record.equalCoordinates){
      if(!['x','y','z'].includes(c.axis)||!Array.isArray(c.nodes)||c.nodes.length<2||new Set(c.nodes).size!==c.nodes.length)throw Error('Invalid source-bound relative geometry');
      constraints.push(c);
    }
    geometrySources.push({path:record.sourcePath,sha256:record.sourceSha256,basis:record.basis});
  }
  return {controls,sources,constraints,geometrySources,...legacy.getReleasedAnalysisConventions(turns,turnIndex)};
}
module.exports={releasedConventions};
