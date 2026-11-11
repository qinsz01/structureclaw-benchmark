'use strict';
// Comparison labels only. Never edits protected states, physical fields, native
// receipts or hashes, and never uses provenance claims as execution evidence.
const {isDeepStrictEqual}=require('node:util');
const record=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);
const finite=x=>typeof x==='number'&&Number.isFinite(x);
const text=x=>typeof x==='string'&&x.trim().length>0;
const sources=new Set(['user','attachment','rule','geometry']);
const properties=new Set(['A','As','Asy','Asz','Iy','Iz','J','Wx','Wz','Wnx','S','Sz','tw','tz','b','t','imin']);
const powers={A:2,As:2,Asy:2,Asz:2,Iy:4,Iz:4,J:4,Wx:3,Wz:3,Wnx:3,S:3,Sz:3,tw:1,tz:1,b:1,t:1,imin:1};
const ownKeys=(x,allowed)=>record(x)&&Object.keys(x).every(k=>allowed.includes(k));
const scalarPath=/^(shape|dimensions|properties)\.([A-Za-z][A-Za-z0-9_]*)$/;
const diagnostics=new Set(['SECTION_CATALOG_LABEL','SECTION_TYPE_CONFLICT','SECTION_DIMENSION_CONFLICT',
 'SECTION_GEOMETRY_UNVERIFIED','SECTION_FILLET_IGNORED','SECTION_PROPERTY_GEOMETRY_DELTA','SECTION_PROVENANCE_CONFLICT']);
const numericRecord=x=>record(x)&&Object.keys(x).every(k=>properties.has(k)&&finite(x[k]));
function field(section,path){
 const match=scalarPath.exec(path);return match&&record(section[match[1]])?section[match[1]][match[2]]:undefined;
}
function provenance(value,section){
 if(!ownKeys(value,['shape','dimensions','properties','propertyFields'])||!Object.keys(value).length)return false;
 for(const [key,source]of Object.entries(value)){
  if(key==='propertyFields'){
   if(!record(source)||!Object.entries(source).every(([k,v])=>properties.has(k)&&sources.has(v)&&finite(section.properties?.[k])))return false;
  }else if(!sources.has(source))return false;
 }
 // The cache is checked as a separate audit field; an incomplete cache claim
 // remains visible to the strict physical comparison instead of being waived.
 return value.properties!=='geometry'||derived(section.extra?.derived_properties,section);
}
function evidence(value){
 return record(value)&&Object.entries(value).every(([key,row])=>scalarPath.test(key)
  &&ownKeys(row,['evidenceId','path','unit'])&&text(row.evidenceId)&&text(row.path)
  &&(row.unit===undefined||text(row.unit)));
}
function derived(value,section){
 return ownKeys(value,['method','fields','shape'])&&value.method==='section-geometry-v1'
  &&Array.isArray(value.fields)&&value.fields.length>0&&new Set(value.fields).size===value.fields.length
  &&value.fields.every(k=>['A','Iy','Iz','J'].includes(k)&&finite(section.properties?.[k]))
  &&record(value.shape)&&record(section.shape)&&isDeepStrictEqual(value.shape,section.shape)
  &&['rectangular','circular','pipe','hollow-circular','I','H','built-up-I','box','built-up-box'].includes(value.shape.kind)
  &&(!['box','built-up-box'].includes(value.shape.kind)||!value.fields.includes('J'));
}
function rules(value,section,model){
 return record(value)&&Object.entries(value).every(([key,row])=>{
  if(!scalarPath.test(key)||!ownKeys(row,['sourceSectionId','sourceField','factor','statement'])
   ||!text(row.sourceSectionId)||!text(row.sourceField)||!text(row.statement)||!finite(row.factor))return false;
  const a=scalarPath.exec(key),b=scalarPath.exec(row.sourceField);
  if(!b||a[1]!==b[1]||(a[1]==='properties'&&(!properties.has(a[2])||powers[a[2]]!==powers[b[2]])))return false;
  const source=model.sections.find(s=>s.id===row.sourceSectionId),before=source&&field(source,row.sourceField),after=field(section,key);
  if(!finite(before)||!finite(after))return false;
  const expected=before*row.factor;
  return finite(expected)&&Math.abs(expected-after)<=32*Number.EPSILON*Math.max(Math.abs(expected),Math.abs(after),Number.MIN_VALUE);
 });
}
function auditField(key,value,section,model){
 // Explicitly separated as an input label by the pinned SDK's
 // project_commercial_model; no other string extension is projected away.
 if(key==='source')return text(value);
 if(key==='provenance')return provenance(value,section);
 if(key==='evidence')return evidence(value);
 if(key==='rules')return rules(value,section,model);
 if(key==='derived_properties')return derived(value,section);
 if(key==='confirmation')return ownKeys(value,['clarificationId','candidateIds'])&&text(value.clarificationId)
  &&(value.candidateIds===undefined||Array.isArray(value.candidateIds)&&value.candidateIds.length>0&&value.candidateIds.every(text));
 if(key==='discarded_nonuser_properties'||key==='discarded_table_properties')return numericRecord(value);
 if(key==='property_geometry_delta')return numericRecord(value);
 if(key==='section_diagnostics')return Array.isArray(value)&&value.every(row=>ownKeys(row,['code','severity','message'])
  &&diagnostics.has(row.code)&&['info','warning'].includes(row.severity)
  &&ownKeys(row.message,['en','zh'])&&text(row.message.en)&&text(row.message.zh));
 return undefined; // Unknown extensions are kept. They may affect physics.
}
function comparisonView(original){
 const model=structuredClone(original),removed=[],unhandled=[],unhandledRecords=[];
 const used=new Set((model.elements||[]).filter(e=>['beam','column'].includes(e.type)).map(e=>e.section));
 // Frozen v3.1 already projects planar and pure-axial section annotations.
 // Do not add a new provenance gate to those previously accepted domains.
 if(model.coordinate_system?.dimension!=='3d')return {model,removed,unhandled,unhandledRecords};
 for(const [sectionIndex,section]of (model.sections||[]).entries()){
  if(!used.has(section.id)||!record(section.extra))continue;
  const before=structuredClone(section.extra);
  for(const [key,value]of Object.entries(before)){
   const accepted=auditField(key,value,{...section,extra:before},model),location=`sections.${section.id}.extra.${key}`;
   if(accepted===true){delete section.extra[key];removed.push(location);}
   else if(accepted===false){unhandled.push(location);unhandledRecords.push({sectionIndex,key});}
  }
 }
 return {model,removed,unhandled,unhandledRecords};
}
function reviewOnlyView(original){
 // Counterfactual attribution only: an evaluator may use this to distinguish
 // a metadata-only rejection from an independently wrong physical/result claim.
 // This view must never turn a rejected submission into a passing submission.
 const view=comparisonView(original);
 for(const {sectionIndex,key}of view.unhandledRecords)delete view.model.sections[sectionIndex].extra[key];
 return view;
}
module.exports={comparisonView,reviewOnlyView,policyId:'sclaw-audit-labels-v3.2',runtimeQualified:false};
