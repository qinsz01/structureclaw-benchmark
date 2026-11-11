'use strict';

// An explicitly versioned engineering diagnostic, not a bound on an opaque
// vendor solver's arithmetic. It never expands the default scoring tolerance.
const POLICY='native-f32-recovery-scale-v1';
const UNIT_ROUNDOFF=2**-24;
const finite=x=>typeof x==='number'&&Number.isFinite(x);
const {isDeepStrictEqual:equal}=require('node:util');
function validatePrecisionScope(quantity,model){
  if(quantity.engineeringPrecision===undefined)return;
  const t=quantity.rawTrace,l=quantity.location,s=quantity.selection;
  const basic=Object.entries(t?.nativeBasicFactors||{}),sources=Object.entries(t?.sourceFactors||{});
  if(l?.kind!=='member'||s?.kind!=='case'||t?.origin!=='raw-sdk-member-end-cut'||
    typeof t.nativeRun!=='string'||!t.nativeRun||!/^[a-f0-9]{64}$/.test(t.sourceModelSha256||'')||
    !equal(t.sourceSelection,s)||sources.length!==1||sources[0][0]!==s.id||sources[0][1]!==1||
    basic.length!==1||!basic[0][0]||basic[0][1]!==1||!Array.isArray(t.raw)||t.raw.length!==1||
    t.raw[0]?.nativeCase!==basic[0][0]||t.raw[0]?.factor!==1||
    !Array.isArray(t.sourceEndNodes)||t.sourceEndNodes.length!==2||
    !t.sourceEndNodes.every(id=>typeof id==='string'&&id)||t.sourceEndNodes[0]===t.sourceEndNodes[1]||
    !((t.end===0&&l.positionM===0&&l.side==='right')||
      (t.end===1&&finite(l.positionM)&&l.positionM>0&&l.side==='left')))
    throw Error('Certified recovery precision requires an original native basic-case endpoint trace');
  if(model!==undefined){
    const member=model?.elements?.find(e=>e.id===l.id),nodes=member?.nodes?.map(id=>model.nodes.find(n=>n.id===id));
    if(!member||!equal(member.nodes,t.sourceEndNodes)||nodes?.length!==2||nodes.some(n=>!n))
      throw Error('Certified recovery precision endpoint differs from the frozen model');
    const [a,b]=nodes,length=Math.hypot(a.x-b.x,a.y-b.y,a.z-b.z),station=t.end===0?0:length;
    if(!finite(length)||length<=0||Math.abs(l.positionM-station)>1e-10)
      throw Error('Certified recovery precision requires a frozen member endpoint');
  }
}
function sumAbsolute(terms){
  let sum=0,correction=0;
  for(const term of terms){const x=Math.abs(term),next=sum+x;correction+=sum>=x?(sum-next)+x:(x-next)+sum;sum=next;}
  return sum+correction;
}
const sameNumber=(a,b)=>finite(a)&&finite(b)&&Math.abs(a-b)<=16*Number.EPSILON*Math.max(Math.abs(a),Math.abs(b),Number.MIN_VALUE);
function referenceAllowance(quantity){
  const p=quantity.engineeringPrecision;
  if(p===undefined)return 0;
  validatePrecisionScope(quantity);
  const fail=()=>{throw new Error('Invalid or unsupported certified reference precision policy');};
  if(!p||p.policy!==POLICY||p.kind!=='analytical-recovery-scale'||p.nativeArithmeticBound!==false||
    p.acceptanceRegionChanges!==true||p.unitRoundoff!==UNIT_ROUNDOFF||p.unit!==quantity.unit||
    quantity.location?.kind!=='member'||!['N','V2','V3','T','M2','M3'].includes(quantity.component)||
    quantity.selection?.kind!=='case'||!Number.isInteger(p.structuralTermCount)||
    p.structuralTermCount<1||p.structuralTermCount>13||!Array.isArray(p.terms)||
    p.terms.length!==p.structuralTermCount||!p.terms.every(finite)||
    !/^[a-f0-9]{64}$/.test(p.certificateSha256||''))fail();
  const scale=sumAbsolute(p.terms),operations=2*p.structuralTermCount-1;
  const allowance=operations*UNIT_ROUNDOFF/(1-operations*UNIT_ROUNDOFF)*scale;
  if(!finite(scale)||!finite(allowance)||p.recoveryScale<0||p.absoluteAllowance<0||
    !sameNumber(p.recoveryScale,scale)||!sameNumber(p.absoluteAllowance,allowance))fail();
  return allowance;
}
function comparisonTolerance(quantity){
  referenceAllowance(quantity);
  return {...quantity.tolerance};
}
function engineeringComparisonTolerance(quantity){
  return {...quantity.tolerance,absolute:quantity.tolerance.absolute+referenceAllowance(quantity)};
}
function convertPrecision(quantity,unit,factor){
  if(quantity.engineeringPrecision===undefined)return undefined;
  referenceAllowance(quantity);
  const p=quantity.engineeringPrecision,terms=p.terms.map(x=>x*factor),scale=sumAbsolute(terms),operations=2*terms.length-1;
  return {...p,unit,terms,recoveryScale:scale,absoluteAllowance:operations*UNIT_ROUNDOFF/(1-operations*UNIT_ROUNDOFF)*scale};
}
function precisionSummary(quantities,strictFailures,engineeringFailures){
  const count=quantities.filter(q=>q?.engineeringPrecision!==undefined).length;
  return count?{policy:POLICY,quantities:count,acceptanceRegionChanges:true,nativeArithmeticBound:false,
    diagnosticOnly:true,strictPass:strictFailures.length===0,strictFailures,
    engineeringPass:engineeringFailures.length===0,engineeringFailures}:undefined;
}
module.exports={POLICY,UNIT_ROUNDOFF,validatePrecisionScope,referenceAllowance,comparisonTolerance,engineeringComparisonTolerance,convertPrecision,precisionSummary};
