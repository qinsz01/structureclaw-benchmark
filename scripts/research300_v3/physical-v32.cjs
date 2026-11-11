'use strict';
const frozen=require('./physical-v31.cjs');
const audit=require('./audit-metadata-v32.cjs');
function compare(actual,expected,dynamic){
 const a=audit.comparisonView(actual),b=audit.comparisonView(expected);
 const result=(dynamic?frozen.physical:frozen.staticPhysical)(a.model,b.model);
 result.diagnostics={...result.diagnostics,comparisonMetadata:{policy:audit.policyId,
  actualAuditFields:a.removed,expectedAuditFields:b.removed,
  unhandledAuditFields:[...a.unhandled,...b.unhandled],
  physicalValuesChanged:false,nativeEvidenceChanged:false}};
 return result;
}
module.exports={physical:(a,b)=>compare(a,b,true),staticPhysical:(a,b)=>compare(a,b,false)};
