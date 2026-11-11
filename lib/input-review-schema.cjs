'use strict';
// Shared by the exported machine-readable schema and runtime validation.
const nullable = type => ({type:[type,'null']});
const number = nullable('number'), string = {type:'string'}, boolean = nullable('boolean');
const array = items => ({type:'array',items});
const object = (properties,required=[]) => ({type:'object',properties,required,additionalProperties:false});
const id = {type:'string',minLength:1,pattern:'^(?!__proto__$|constructor$|prototype$).+$'};
const vector = {type:'array',items:{type:'number'},minItems:3,maxItems:3};
const controls = Object.fromEntries(['self_weight','rigid_floor','p_delta','rigid_offsets','construction_stage',
  'first_order','linear_elastic','stiffness_reductions','automatic_combinations','full_explicit_stiffness'].map(k=>[k,boolean]));
const member = {id,type:{enum:['beam','column','truss','brace']},nodes:{...array(id),minItems:2,maxItems:2},material:id,section:nullable('string'),rotation_angle:number};
const stations = object({x:array({type:'number'}),y:array({type:'number'}),z:array({type:'number'})},['x','y','z']);
const model = object({
  schema_version:{type:['string','number']},unit_system:{const:'SI'},
  coordinate_system:object({dimension:{enum:['2d','3d']},plane:{enum:['xz',null]},semantics:{const:'global-z-up'},dof_order:array(string),version:{type:'number'}}),
  nodes:array(object({id,x:number,y:number,z:number,restraints:{...array(boolean),minItems:6,maxItems:6}},['id'])),
  elements:array(object(member,['id'])),
  materials:array(object({id,name:string,type:string,E:number,G:number,nu:number,rho:number},['id'])),
  sections:array(object({id,name:string,type:string,shape:{type:['object','string']},shape_units:{enum:['m','mm']},properties:{type:'object',additionalProperties:number}},['id'])),
  load_cases:array(object({id,type:string,loads:array(object({id,type:{enum:['nodal','distributed','point']},node:id,element:id,reference_frame:{enum:['global','local']},
    ...Object.fromEntries(['fx','fy','fz','mx','my','mz','wx','wy','wz','start','end','position'].map(k=>[k,number])),extent:{const:'full-member'}},['type','reference_frame']))},['id','loads'])),
  load_combinations:array(object({id,name:string,type:string,factors:{type:'object',additionalProperties:{type:'number'}}},['id','factors'])),
  analysis_control:object(controls),
  analysis:object({type:{enum:['first-order linear elastic static','first-order linear elastic static analysis']},full_explicit_stiffness:boolean,automatic_reduction:boolean}),
  metadata:object({elementReferenceVectors:{type:'object',additionalProperties:vector}}),
  axes:object({mode:{enum:['xz','reference-vectors']},elementDirection:{const:'listed-node-order'},rotationDefaultDegrees:number,
    elementReferenceVectors:{type:'object',additionalProperties:vector},referenceVectorRule:object({vertical:vector,other:vector,verticalThreshold:{type:'number',minimum:0,maximum:1}},['vertical','other','verticalThreshold'])}),
  grids:array(object({stations,idTemplate:string,restraints:{...array(boolean),minItems:6,maxItems:6},omit:array(array({type:'integer'})),members:array(object({axis:{enum:['x','y','z']},starts:array(array({type:'integer'})),idTemplate:string,...Object.fromEntries(['type','material','section','rotation_angle'].map(k=>[k,member[k]]))},['axis','starts','idTemplate']))},['stations','idTemplate'])),
  nodeOverrides:array(object({id,x:number,y:number,z:number,restraints:{...array(boolean),minItems:6,maxItems:6}},['id'])),
  memberChains:array(object({nodes:array(id),ids:array(id),...Object.fromEntries(['type','material','section','rotation_angle'].map(k=>[k,member[k]]))},['nodes','ids'])),
});
const schema = {$schema:'https://json-schema.org/draft/2020-12/schema',title:'Public structural input reconstruction v2',
  ...object({schemaVersion:{const:1},caseId:{type:'string',pattern:'^MM-[0-9]{3}$'},turnId:{type:'string',pattern:'^t[0-9]+$'},packetSha256:{type:'string',pattern:'^[a-f0-9]{64}$'},
    reviewer:object({id,kind:{enum:['agent','human']},independent:{const:true}},['id','kind','independent']),method:{const:'public-only-reconstruction'},model,
    unresolved:array(object({kind:{enum:['load-component','node-coordinate','element-section','node-restraints']},ids:{...array(id),minItems:1,uniqueItems:true},component:{type:['string','array'],items:string},reason:{type:'string',minLength:1},question:{type:'string',minLength:1}},['kind','ids','reason','question'])),
    observations:array(object({category:{enum:['geometry','topology','restraints','materials','sections','loads','axes','settings']},files:{...array(string),minItems:1},observation:{type:'string',minLength:1}},['category','files','observation'])),
    decoderSources:array(string)},['schemaVersion','caseId','turnId','packetSha256','reviewer','method','model','unresolved','observations'])};
function validate(value,rule=schema,location='') {
  const errors=[],type=value===null?'null':Array.isArray(value)?'array':typeof value;
  const add=(code,detail)=>errors.push({path:location||'/',code,detail});
  if(rule.type&&!([rule.type].flat().some(t=>t===type||(t==='integer'&&Number.isInteger(value))))) {add('type',`Expected ${[rule.type].flat().join('|')}`);return errors;}
  if(type==='number'&&!Number.isFinite(value))add('non-finite','Expected finite number');
  if(Object.hasOwn(rule,'const')&&JSON.stringify(value)!==JSON.stringify(rule.const))add('const',`Expected ${JSON.stringify(rule.const)}`);
  if(rule.enum&&!rule.enum.some(v=>JSON.stringify(v)===JSON.stringify(value)))add('enum',`Expected one of ${JSON.stringify(rule.enum)}`);
  if(type==='string'){
    if(rule.minLength!==undefined&&value.trim().length<rule.minLength)add('empty','Expected nonempty text');
    if(rule.pattern&&!new RegExp(rule.pattern).test(value))add('pattern','Invalid identifier or binding');
  }
  if(type==='number')for(const [key,invalid]of [['minimum',value<rule.minimum],['maximum',value>rule.maximum]])if(invalid)add(key,`Expected ${key} ${rule[key]}`);
  if(type==='array'){
    if(rule.minItems!==undefined&&value.length<rule.minItems||rule.maxItems!==undefined&&value.length>rule.maxItems)add('length','Wrong array length');
    if(rule.uniqueItems&&new Set(value.map(v=>JSON.stringify(v))).size!==value.length)add('duplicate','Duplicate array entries');
    if(rule.items)value.forEach((v,i)=>errors.push(...validate(v,rule.items,`${location}/${i}`)));
  }
  if(type==='object'){
    for(const k of rule.required||[])if(!Object.hasOwn(value,k))errors.push({path:`${location}/${k}`,code:'required',detail:'Missing field'});
    for(const [k,v]of Object.entries(value)){
      const child=rule.properties&&Object.hasOwn(rule.properties,k)?rule.properties[k]:undefined,p=`${location}/${k.replace(/~/g,'~0').replace(/\//g,'~1')}`;
      if(['__proto__','prototype','constructor'].includes(k))errors.push({path:p,code:'unsafe-key',detail:'Unsafe object key'});
      else if(child)errors.push(...validate(v,child,p));
      else if(rule.additionalProperties===false)errors.push({path:p,code:'unsupported-field',detail:'Field is not in the public schema'});
      else if(rule.additionalProperties&&typeof rule.additionalProperties==='object')errors.push(...validate(v,rule.additionalProperties,p));
    }
  }
  return errors;
}
module.exports={schema,validate,controls};
