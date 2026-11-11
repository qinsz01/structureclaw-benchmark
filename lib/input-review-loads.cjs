'use strict';
const {equal}=require('./public-input-review.cjs');
const ABSOLUTE=1e-10,RELATIVE=1e-7;
const numericEqual=(a,b)=>typeof a==='number'&&typeof b==='number'
  ? Number.isFinite(a)&&Number.isFinite(b)&&Math.abs(a-b)<=Math.max(ABSOLUTE,Math.abs(b)*RELATIVE):equal(a,b);
function leaves(value,prefix='',output={}) {
  if(value===undefined||value===null)return output;
  if(value&&typeof value==='object'&&Object.keys(value).length)for(const [k,v]of Object.entries(value))leaves(v,`${prefix}/${k}`,output);
  else if(typeof value!=='object'||Array.isArray(value))output[prefix]=value;
  return output;
}
function difference(actual,expected,prefix='') {
  const a=leaves(actual),e=leaves(expected),findings=[];let matched=0;
  for(const [k,v]of Object.entries(e)){
    if(!Object.hasOwn(a,k))findings.push({path:prefix+k,code:'missing',expected:v});
    else if(!numericEqual(a[k],v)){
      if(k==='/end'&&(a[k]==='full-member'||v==='full-member')){
        findings.push({path:prefix+k,code:'unverifiable-extent',actual:a[k],expected:v,detail:'Insufficient disclosed relative geometry to compare the numeric span; needs public-fact review'});continue;
      }
      const f={path:prefix+k,code:'mismatch',actual:a[k],expected:v};
      if(typeof a[k]==='number'&&typeof v==='number')Object.assign(f,{absoluteError:Math.abs(a[k]-v),relativeError:v===0?null:Math.abs((a[k]-v)/v),tolerance:Math.max(ABSOLUTE,Math.abs(v)*RELATIVE)});
      findings.push(f);
    }else matched++;
  }
  for(const [k,v]of Object.entries(a))if(!Object.hasOwn(e,k))findings.push({path:prefix+k,code:'unexpected',actual:v});
  return {required:Object.keys(e).length,matched,findings};
}
function knownDelta(model,a,b,axis,constraints) {
  const na=model.nodes?.find(n=>n.id===a),nb=model.nodes?.find(n=>n.id===b);
  if(Number.isFinite(na?.[axis])&&Number.isFinite(nb?.[axis]))return nb[axis]-na[axis];
  // Only source-verified relative coordinates can survive an absolute-coordinate mask.
  const groups=constraints.filter(c=>c.axis===axis).map(c=>c.nodes),visited=new Set([a]);
  let changed=true;while(changed){changed=false;for(const group of groups)if(group.some(id=>visited.has(id)))for(const id of group)if(!visited.has(id)){visited.add(id);changed=true;}}
  return visited.has(b)?0:undefined;
}
function memberLength(model,id,constraints=[]) {
  const e=model.elements?.find(e=>e.id===id);if(e?.nodes?.length!==2)return undefined;
  const d=['x','y','z'].map(axis=>knownDelta(model,...e.nodes,axis,constraints));
  if(d.every(Number.isFinite)){const length=Math.hypot(...d);if(length>0)return length;}
}
function normalizedLoads(model,constraints=[]) {
  return Object.fromEntries((model.load_cases||[]).map(lc=>[lc.id,(lc.loads||[]).map(l=>{
    const n={...l};delete n.id;
    for(const k of ['fx','fy','fz','mx','my','mz','wx','wy','wz'])if(n[k]===0)delete n[k];
    if(l.type==='distributed'){
      if(!Object.hasOwn(l,'start'))n.start=0;
      if(!Object.hasOwn(l,'end'))n.end=memberLength(model,l.element,constraints)??'full-member';
      if(l.extent==='full-member'){delete n.extent;n.start=0;n.end=memberLength(model,l.element,constraints)??'full-member';}
    }
    return n;
  })]));
}
const selector=l=>JSON.stringify([l.type,l.reference_frame,l.node??null,l.element??null]);
function compareLoads(actual,expected,constraints=[]) {
  const a=normalizedLoads(actual,constraints),e=normalizedLoads(expected,constraints);
  const findings=[];let required=0,matched=0;
  for(const id of [...new Set([...Object.keys(e),...Object.keys(a)])].sort()){
    const ar=Object.hasOwn(a,id)?a[id]:[],er=Object.hasOwn(e,id)?e[id]:[],paired=new Map();
    const candidates=er.map(exp=>ar.map((act,i)=>({i,d:difference(act,exp)})).filter(({i,d})=>selector(ar[i])===selector(exp)&&!d.findings.some(f=>!['missing','unverifiable-extent'].includes(f.code))).sort((x,y)=>x.d.findings.length-y.d.findings.length||x.i-y.i));
    function augment(j,seen){for(const {i}of candidates[j])if(!seen.has(i)){seen.add(i);if(!paired.has(i)||augment(paired.get(i),seen)){paired.set(i,j);return true;}}return false;}
    er.forEach((_,j)=>augment(j,new Set()));
    const usedA=new Set(paired.keys()),usedE=new Set(paired.values());
    // Remaining pairs cannot form a complete compatible multiset; select a
    // deterministic close pair for actionable diagnostics, never for acceptance.
    for(let j=0;j<er.length;j++)if(!usedE.has(j)){
      const choices=ar.map((act,i)=>({i,d:difference(act,er[j])})).filter(({i})=>!usedA.has(i)&&selector(ar[i])===selector(er[j])).sort((x,y)=>x.d.findings.length-y.d.findings.length||x.i-y.i);
      if(choices.length){paired.set(choices[0].i,j);usedA.add(choices[0].i);usedE.add(j);}
    }
    for(let j=0;j<er.length;j++){
      const i=[...paired].find(([,v])=>v===j)?.[0],diff=difference(i===undefined?{}:ar[i],er[j],`/cases/${id}/${j}`);
      required+=diff.required;matched+=diff.matched;findings.push(...diff.findings.map(f=>({category:'loads',...f})));
    }
    ar.forEach((v,i)=>{if(!paired.has(i))for(const [key,value]of Object.entries(leaves(v)))findings.push({category:'loads',path:`/cases/${id}/extra-${i}${key}`,code:'unexpected',actual:value});});
    if(!Object.hasOwn(e,id)&&Object.hasOwn(a,id)&&!ar.length)findings.push({category:'loads',path:`/cases/${id}`,code:'unexpected',actual:[]});
    if(Object.hasOwn(e,id)&&!Object.hasOwn(a,id)&&!er.length)findings.push({category:'loads',path:`/cases/${id}`,code:'missing',expected:[]});
  }
  if(expected.load_combinations!==undefined){
    // Combination order is bookkeeping; factor names and case namespace remain exact.
    const byId=rows=>Object.fromEntries((rows||[]).map(r=>[r.id,{present:true,factors:r.factors}]));
    const d=difference(actual.load_combinations===undefined?undefined:byId(actual.load_combinations),byId(expected.load_combinations),'/combinations');
    required+=d.required;matched+=d.matched;findings.push(...d.findings.map(f=>({category:'loads',...f})));
    if(actual.load_combinations===undefined&&!expected.load_combinations.length){required++;findings.push({category:'loads',path:'/combinations',code:'missing',expected:[]});}
  }else if(actual.load_combinations?.length)findings.push({category:'loads',path:'/combinations',code:'unexpected',actual:actual.load_combinations});
  return {coverage:{required,matched,missing:findings.filter(f=>f.code==='missing').length,mismatched:findings.filter(f=>f.code==='mismatch').length,unexpected:findings.filter(f=>f.code==='unexpected').length,deferred:findings.filter(f=>f.code==='unverifiable-extent').length},findings};
}
module.exports={ABSOLUTE,RELATIVE,numericEqual,difference,memberLength,compareLoads,normalizedLoads};
