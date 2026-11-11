'use strict';
// Current public review evidence is separate from the original acceptance record.
const fs = require('node:fs');
const path = require('node:path');
const { createHash } = require('node:crypto');
const METHOD = 'public-only-reconstruction';
const VERSION = 'physical-readback-v1';
const CATEGORIES = ['geometry','topology','restraints','materials','sections','loads','axes','settings'];
const HASH = /^[a-f0-9]{64}$/;
const sha256 = bytes => createHash('sha256').update(bytes).digest('hex');
const canonical = v => Array.isArray(v) ? v.map(canonical) : v && typeof v === 'object' ? Object.fromEntries(Object.keys(v).sort().map(k=>[k,canonical(v[k])])) : v;
const equal = (a,b) => JSON.stringify(canonical(a)) === JSON.stringify(canonical(b));
const clone = v => JSON.parse(JSON.stringify(v));
const fail = message => { throw Error(`Public input review: ${message}`); };
const jsonBytes = v => Buffer.from(`${JSON.stringify(v,null,2)}\n`);
const readJson = file => JSON.parse(fs.readFileSync(file,'utf8'));
const pick = (v,keys) => Object.fromEntries(keys.filter(k=>v?.[k]!==undefined).map(k=>[k,v[k]]));
function safeFile(root,relative) {
  if(typeof relative!=='string'||!relative||path.isAbsolute(relative)||relative.includes('\\')||relative.split('/').some(p=>p==='..'||p==='.'||!p)) fail('unsafe evidence path');
  const base=fs.realpathSync(root), file=fs.realpathSync(path.join(root,relative));
  if(!file.startsWith(`${base}${path.sep}`)||!fs.statSync(file).isFile()) fail('evidence escapes its root');
  return file;
}
function listFiles(root,prefix='') {
  return fs.readdirSync(path.join(root,prefix),{withFileTypes:true}).flatMap(e=>{
    const rel=prefix?`${prefix}/${e.name}`:e.name;
    if(e.isSymbolicLink()) fail('evidence symlinks are forbidden');
    return e.isDirectory()?listFiles(root,rel):[rel];
  }).sort();
}
function unique(rows,label) {
  if(!Array.isArray(rows)) fail(`${label} must be an array`);
  const ids=new Set();for(const row of rows){if(!row||typeof row.id!=='string'||!row.id||ids.has(row.id)||['__proto__','constructor','prototype'].includes(row.id))fail(`invalid or duplicate ${label} ID`);ids.add(row.id);}
  return rows;
}
function substitute(template,index) {
  if(typeof template!=='string'||!template.trim()) fail('grid requires an observed ID template');
  return template.replace(/\{([ijk])\}/g,(_,axis)=>index['ijk'.indexOf(axis)]);
}
function expandReconstruction(input) {
  if(!input||typeof input!=='object'||Array.isArray(input)) fail('model must be an object');
  const out=clone(input);out.nodes??=[];out.elements??=[];
  for(const grid of out.grids||[]) {
    const stations=['x','y','z'].map(axis=>grid.stations?.[axis]);
    if(stations.some(a=>!Array.isArray(a)||!a.length||a.some(n=>typeof n!=='number'||!Number.isFinite(n)))) fail('grid requires actual observed stations');
    if(stations.reduce((v,a)=>v*a.length,1)>10000) fail('grid is too large');
    const omitted=new Set((grid.omit||[]).map(v=>JSON.stringify(v)));
    for(let i=0;i<stations[0].length;i++)for(let j=0;j<stations[1].length;j++)for(let k=0;k<stations[2].length;k++) {
      const index=[i,j,k];if(omitted.has(JSON.stringify(index)))continue;
      out.nodes.push({id:substitute(grid.idTemplate,index),x:stations[0][i],y:stations[1][j],z:stations[2][k],...(grid.restraints?{restraints:clone(grid.restraints)}:{})});
    }
    for(const group of grid.members||[])for(const start of group.starts||[]) {
      const axis='xyz'.indexOf(group.axis),end=[...start];if(axis<0||start.length!==3||start.some((v,i)=>!Number.isInteger(v)||v<0||v>=stations[i].length))fail('invalid grid member start');
      end[axis]++;if(end[axis]>=stations[axis].length||omitted.has(JSON.stringify(start))||omitted.has(JSON.stringify(end)))fail('grid member outside observed nodes');
      out.elements.push({...pick(group,['type','material','section','rotation_angle']),id:substitute(group.idTemplate,start),nodes:[substitute(grid.idTemplate,start),substitute(grid.idTemplate,end)]});
    }
  }
  for(const chain of out.memberChains||[]) {
    if(!Array.isArray(chain.nodes)||!Array.isArray(chain.ids)||chain.ids.length!==chain.nodes.length-1)fail('member chain needs one observed ID per segment');
    chain.ids.forEach((id,i)=>out.elements.push({...pick(chain,['type','material','section','rotation_angle']),id,nodes:chain.nodes.slice(i,i+2)}));
  }
  for(const override of out.nodeOverrides||[]) {
    const node=out.nodes.find(n=>n.id===override.id);if(!node)fail('node override does not identify an observed node');Object.assign(node,override);
  }
  unique(out.nodes,'node');unique(out.elements,'element');
  for(const key of ['materials','sections','load_cases'])if(out[key]!==undefined)unique(out[key],key);
  delete out.grids;delete out.memberChains;delete out.nodeOverrides;
  return out;
}
function validateSubmission(s) {
  if(!s||s.schemaVersion!==1||!/^MM-\d{3}$/.test(s.caseId)||!/^t\d+$/.test(s.turnId)||!HASH.test(s.packetSha256||'')||s.method!==METHOD) fail('invalid submission identity or method');
  if(!s.reviewer||typeof s.reviewer.id!=='string'||!s.reviewer.id.trim()||!['human','agent'].includes(s.reviewer.kind)||s.reviewer.independent!==true)fail('independent reviewer identity is required');
  if(!Array.isArray(s.observations)||!Array.isArray(s.unresolved))fail('observations and unresolved fields are required');
  for(const observation of s.observations)if(!CATEGORIES.includes(observation.category)||!Array.isArray(observation.files)||typeof observation.observation!=='string'||!observation.observation.trim())fail('invalid observation');
  for(const u of s.unresolved)if(!['load-component','node-coordinate','element-section','node-restraints'].includes(u.kind)||!Array.isArray(u.ids)||!u.ids.length||u.ids.some(id=>typeof id!=='string')||!u.reason?.trim()||!u.question?.trim())fail('invalid unresolved observation');
  // The protocol fixes m/kN/kN*m, MPa, kg/m3, m2/m4 and degree units.
  // Preserve the corpus's optional SI tag, but never silently discard a unit
  // override, including one inside an expansion rule that would be projected out.
  const fixedUnits=(value,location='model')=>{
    if(!value||typeof value!=='object')return;
    for(const [key,child]of Object.entries(value)){
      if(/(?:units?|unit[_-]?system)$/i.test(key)){
        if(location!=='model'||key!=='unit_system'||child!=='SI')fail(`unsupported unit declaration at ${location}.${key}; use the protocol's fixed engineering units`);
      }else fixedUnits(child,`${location}.${key}`);
    }
  };
  fixedUnits(s.model);
  const model=expandReconstruction(s.model);
  const closed=(value,keys,label)=>{if(value&&Object.keys(value).some(key=>!keys.includes(key)))fail(`unsupported ${label} field`);};
  closed(model,['schema_version','unit_system','coordinate_system','nodes','elements','materials','sections','load_cases','load_combinations','analysis_control','metadata','axes'],'model');
  for(const node of model.nodes)closed(node,['id','x','y','z','restraints'],'node');
  for(const element of model.elements)closed(element,['id','type','nodes','material','section','rotation_angle'],'element');
  for(const material of model.materials||[])closed(material,['id','name','type','E','G','nu','rho'],'material');
  for(const section of model.sections||[])closed(section,['id','name','type','shape','properties'],'section');
  closed(model.metadata,['elementReferenceVectors'],'metadata');
  closed(model.axes,['mode','elementDirection','rotationDefaultDegrees','elementReferenceVectors','referenceVectorRule'],'axes');
  return s;
}
function ambiguityGroups(context,model) {
  if(context.turn.expectation!=='clarify') return [];
  const groups={
    'MM-007':[{kind:'load-component',ids:['n1'],component:'fz'}],
    'MM-021':[{kind:'element-section',ids:[model.elements[2]?.id]}],
    'MM-032':[{kind:'node-coordinate',ids:['U1','U2','U3','U4'],component:'z',primary:['U2']}],
    'MM-058':[{kind:'node-restraints',ids:['A0','B0'],components:[0,2,4],requireAll:true}],
    'MM-072':[{kind:'node-coordinate',ids:['C2','C4','C6','R1','R2','R3','obsR'],component:'z'}],
  };
  if(!groups[context.id])fail('unsupported clarification mask');return groups[context.id];
}
function maskUnknown(model,groups,check=false) {
  const output=clone(model),assertions=[];
  for(const group of groups) {
    const rows=group.kind==='load-component'?output.load_cases?.flatMap(c=>c.loads||[]):group.kind==='element-section'?output.elements:output.nodes;
    for(const row of rows||[])if(group.ids.includes(group.kind==='load-component'?row.node:row.id)) {
      const key=group.kind==='node-restraints'?'restraints':group.kind==='element-section'?'section':group.component;
      if(group.components){for(const index of group.components){if(check&&row[key]?.[index]!=null)assertions.push(`${row.id}/${key}/${index}`);if(row[key])row[key][index]=null;}}
      else {if(check&&row[key]!=null)assertions.push(`${row.id||row.node}/${key}`);delete row[key];}
    }
  }
  return {model:output,assertions};
}
function clarificationMatches(group,observation) {
  if(group.kind!==observation.kind)return false;
  if(group.kind!=='node-restraints'||observation.component===undefined)return observation.component===group.component;
  const components=Array.isArray(observation.component)?observation.component
    :typeof observation.component==='string'?observation.component.split(/[,/\s]+/).filter(Boolean):[];
  if(!components.length||components.some(component=>typeof component!=='string'))return false;
  const actual=[...new Set(components.map(component=>component.trim().toLowerCase()))].sort();
  const expected=group.components.map(index=>['ux','uy','uz','rx','ry','rz'][index]).sort();
  return equal(actual,expected);
}
function getReleasedAnalysisConventions(turns,turnIndex) {
  if(!Number.isInteger(turnIndex)||turnIndex<0||turnIndex>=turns.length)fail('analysis convention turn out of range');
  const conventions={};
  for(const turn of turns.slice(0,turnIndex+1))for(const attachment of turn.attachments){
    if(!/^analysis-conventions-v2\.(?:md|txt)$/.test(attachment.name))continue;
    const bytes=fs.readFileSync(attachment.path),text=bytes.toString('utf8');
    if(attachment.sha256&&attachment.sha256!==sha256(bytes))fail('public analysis convention hash mismatch');
    if(!text.includes('commercial-linear-static-v2')||!/Asy\s*=\s*Asz\s*=\s*5\s*\*\s*A\s*\/\s*6/.test(text))fail('unsupported public analysis convention');
    conventions.effectiveShearAreas='5*A/6';
  }
  return conventions;
}
function facts(model,{expected=false,analysisConventions={}}={}) {
  const byId=(rows,fn)=>Object.fromEntries((rows||[]).map(row=>[row.id,fn(row)]));
  const bendingMembers=(model.elements||[]).filter(element=>!['truss','brace'].includes(element.type));
  const bendingSections=new Set(bendingMembers.map(element=>element.section));
  const result=Object.fromEntries(CATEGORIES.map(k=>[k,{}]));
  result.geometry.nodes=byId(model.nodes,n=>pick(n,['x','y','z']));
  result.topology.nodes=byId(model.nodes,()=>true);
  result.topology.elements=byId(model.elements,e=>pick(e,['type','nodes']));
  result.restraints.nodes=byId(model.nodes,n=>n.restraints);
  result.materials.properties=byId(model.materials,m=>pick(m,['E','G','nu','rho']));
  result.materials.assignments=byId(model.elements,e=>e.material);
  result.sections.properties=byId(model.sections,s=>{
    if(!expected||analysisConventions.effectiveShearAreas!=='5*A/6'||!bendingSections.has(s.id))return s.properties;
    const area=s.properties?.A;if(typeof area!=='number'||!Number.isFinite(area)||area<=0)fail('prescribed shear areas require positive finite section A');
    return {...s.properties,Asy:5*area/6,Asz:5*area/6};
  });
  result.sections.assignments=byId(model.elements,e=>e.section);
  // IDs assigned to load records are bookkeeping; physical target/components are compared.
  if(model.load_cases!==undefined)result.loads.cases=byId(model.load_cases,lc=>(lc.loads||[]).map(l=>{
    const normalized={...l};delete normalized.id;
    // Match the solver's full-member distributed-load defaults. Use this
    // side's own geometry, never a gold member length for the reconstruction.
    // Explicit null denotes unknown, rather than an omitted/default interval.
    if(l.type==='distributed'&&!Object.hasOwn(l,'points')&&!Object.hasOwn(l,'segments')){
      if(!Object.hasOwn(l,'start'))normalized.start=0;
      if(!Object.hasOwn(l,'end')){
        const element=model.elements?.find(e=>e.id===l.element),ends=element?.nodes?.map(id=>model.nodes?.find(n=>n.id===id));
        if(ends?.length===2&&ends.every(node=>node&&['x','y','z'].every(axis=>typeof node[axis]==='number'&&Number.isFinite(node[axis])))){
          const length=Math.hypot(...['x','y','z'].map(axis=>ends[1][axis]-ends[0][axis]));if(length>0)normalized.end=length;
        }
      }
    }
    for(const k of ['fx','fy','fz','mx','my','mz','wx','wy','wz'])if(normalized[k]===0)delete normalized[k];
    return normalized;
  }).sort((a,b)=>JSON.stringify(canonical(a)).localeCompare(JSON.stringify(canonical(b)))));
  if(model.load_combinations!==undefined)result.loads.combinations=model.load_combinations;
  if(model.analysis_control!==undefined)result.settings.analysis_control=model.analysis_control;
  if(model.coordinate_system!==undefined)result.axes.coordinate_system=pick(model.coordinate_system,['dimension','plane','semantics','dof_order']);
  const axes=model.axes;
  if(expected){result.axes.mode=model.coordinate_system?.dimension==='2d'?'xz':'reference-vectors';result.axes.elementDirection='listed-node-order';}
  else if(axes){Object.assign(result.axes,pick(axes,['mode','elementDirection']));}
  result.axes.rolls=byId(model.elements,e=>e.rotation_angle??(expected?0:axes?.rotationDefaultDegrees));
  // Pure axial members have no transverse bending/shear axes. Their signed
  // endpoint order remains part of topology; beam/column references stay strict.
  if(model.coordinate_system?.dimension==='3d')result.axes.referenceVectors=byId(bendingMembers,e=>{
    const explicit=model.metadata?.elementReferenceVectors?.[e.id]??axes?.elementReferenceVectors?.[e.id];if(explicit)return explicit;
    const rule=expected?{vertical:[1,0,0],other:[0,0,1],verticalThreshold:0.9}:axes?.referenceVectorRule;if(!rule)return undefined;
    const a=model.nodes?.find(n=>n.id===e.nodes?.[0]),b=model.nodes?.find(n=>n.id===e.nodes?.[1]);if(!a||!b)return undefined;
    const delta=['x','y','z'].map(k=>b[k]-a[k]),length=Math.hypot(...delta);if(!Number.isFinite(length)||length===0)return undefined;
    return Math.abs(delta[2]/length)>rule.verticalThreshold?rule.vertical:rule.other;
  });
  return result;
}
function leaves(value,prefix='',output={}) {
  if(value===undefined||value===null||(!Array.isArray(value)&&typeof value==='object'&&!Object.keys(value).length))return output;
  if(value&&typeof value==='object'&&Object.keys(value).length){for(const [key,v]of Object.entries(value))leaves(v,`${prefix}/${key}`,output);}
  else output[prefix]=value;return output;
}
function numericEqual(a,b){return typeof a==='number'&&typeof b==='number'?Number.isFinite(a)&&Number.isFinite(b)&&Math.abs(a-b)<=Math.max(1e-10,Math.abs(b)*1e-7):equal(a,b);}
function compareReconstruction(submission,expected,context,packet) {
  validateSubmission(submission);
  const actual=expandReconstruction(submission.model),groups=ambiguityGroups(context,expected);
  const aMasked=maskUnknown(actual,groups,true),eMasked=maskUnknown(expected,groups);
  const af=facts(aMasked.model),ef=facts(eMasked.model,{expected:true,analysisConventions:context.analysisConventions});
  const coverage={},findings=[];
  for(const category of CATEGORIES){
    const a=leaves(af[category]),e=leaves(ef[category]);
    const row={required:Object.keys(e).length,matched:0,missing:0,mismatched:0,unexpected:0,observation:false};
    for(const [key,value]of Object.entries(e)){
      if(!Object.hasOwn(a,key)){row.missing++;findings.push({category,path:key,code:'missing'});}
      else if(!numericEqual(a[key],value)){row.mismatched++;findings.push({category,path:key,code:'mismatch'});}
      else row.matched++;
    }
    for(const key of Object.keys(a))if(!Object.hasOwn(e,key)){row.unexpected++;findings.push({category,path:key,code:'unexpected'});}
    const observations=submission.observations.filter(o=>o.category===category);
    row.observation=observations.some(o=>o.files.length&&o.files.every(file=>/^t\d+\//.test(file)&&packet.files.some(f=>f.path===file))&&(!['geometry','topology','restraints'].includes(category)||o.files.some(file=>/\.(png|dxf)$/i.test(file))));
    if(!row.observation)findings.push({category,code:'missing-observation'});
    coverage[category]=row;
  }
  for(const assertion of aMasked.assertions)findings.push({category:'clarification',path:assertion,code:'unsupported-resolution'});
  for(const group of groups){
    if(!submission.unresolved.some(u=>clarificationMatches(group,u)&&(group.requireAll?group.ids.every(id=>submission.unresolved.some(other=>clarificationMatches(group,other)&&other.ids.includes(id))):(group.primary||group.ids).some(id=>u.ids.includes(id)))))findings.push({category:'clarification',code:'missing-clarification'});
  }
  if(submission.unresolved.some(u=>!groups.some(g=>clarificationMatches(g,u)&&u.ids.every(id=>g.ids.includes(id)))))findings.push({category:'clarification',code:'unexpected-clarification'});
  const failed=findings.some(f=>['mismatch','unexpected','unsupported-resolution','unexpected-clarification'].includes(f.code));
  const status=failed?'failed':findings.length?'partial':'passed';
  return {status,coverage,findings,scope:'All disclosed physical geometry, topology, restraints, stiffness and assignment, signed loads, local axes and analysis settings. Effective shear areas are required where the released public v2 convention prescribes them. Pure axial truss/brace transverse reference vectors, descriptive labels, solver results and undisclosed clarification values are excluded; signed member endpoint orientation remains checked.'};
}
function reviewPath(record,binding) {
  if(binding?.inputEdition!=='current'||!/^MM-\d{3}$/.test(record.id))return null;
  return path.join(record.root,'corpora/research-300/input-reviews',record.id,'review.json');
}
function getPublicInputReview(record,inputBinding) {
  const base={schemaVersion:1,caseId:record.id,inputEdition:inputBinding?.inputEdition||'current',status:'pending',verified:false,coverage:{},findings:[],evidence:[]};
  const file=reviewPath(record,inputBinding);if(!file||!fs.existsSync(file))return base;
  try {
    const report=readJson(file);
    if(report.schemaVersion!==1||report.caseId!==record.id||report.method!==METHOD||!equal(report.inputBinding,inputBinding)||!Array.isArray(report.turns))fail('review binding or schema mismatch');
    const replay=gradeEvidence(record,report.turns.map(t=>t.evidence.receipt.path));
    if(!equal(replay,report))fail('review verdict does not match replayed sealed evidence');
    return {...base,status:report.status,verified:true,coverage:report.coverage,findings:report.findings,evidence:[{path:path.relative(record.root,file).split(path.sep).join('/'),sha256:sha256(fs.readFileSync(file))},...report.grader.sources,...report.turns.flatMap(t=>{const packet=readJson(safeFile(record.root,t.evidence.packet.path));return [...Object.values(t.evidence),...packet.files.map(f=>({path:path.posix.join(path.posix.dirname(t.evidence.packet.path),f.path),sha256:f.sha256}))];})],turns:report.turns.map(t=>({turnId:t.turnId,status:t.status,coverage:t.coverage,findings:t.findings})),scope:report.scope};
  } catch(error){return {...base,status:'invalid',findings:[{code:'invalid-evidence',message:error.message}]};}
}
module.exports={CATEGORIES,METHOD,VERSION,sha256,canonical,equal,jsonBytes,safeFile,listFiles,readJson,expandReconstruction,validateSubmission,compareReconstruction,getReleasedAnalysisConventions,reviewPath,getPublicInputReview};

const PROTOCOL=path.resolve(__dirname,'../docs/public-input-review-protocol.md');
const DECODER=path.resolve(__dirname,'../scripts/research300/blind-input-review-public.cjs');
const CLI=path.resolve(__dirname,'../scripts/research300/blind_input_review.cjs');
function buildPacketFiles(turns,turnIndex) {
  if(!Number.isInteger(turnIndex)||turnIndex<0||turnIndex>=turns.length)fail('packet turn out of range');
  const current=turns[turnIndex],files=new Map(),history=[];
  if(!/^MM-\d{3}$/.test(current.id))fail('independent reconstruction currently supports MM cases only');
  if(current.inputBinding?.inputEdition!=='current')fail('blind packet requires the current public input binding');
  files.set('README.md',fs.readFileSync(PROTOCOL));files.set('decoder.cjs',fs.readFileSync(DECODER));
  files.set('submission-schema.json',jsonBytes({schemaVersion:1,required:['caseId','turnId','packetSha256','reviewer','method','model','unresolved','observations'],categories:CATEGORIES,method:METHOD,notes:'See README.md. Run decoder.cjs to obtain a partial public-table scaffold. No case-specific answer template is provided.'}));
  for(const input of turns.slice(0,turnIndex+1)) {
    if(!equal(input.inputBinding,current.inputBinding))fail('history input binding mismatch');
    const messagePath=`${input.turnId}/message.json`;
    files.set(messagePath,jsonBytes({turnId:input.turnId,instruction:input.instruction,responseContract:input.responseContract}));
    const attachments=[];
    for(const a of input.attachments){
      if(typeof a.name!=='string'||a.name!==path.basename(a.name)||!/^[-\w.]+$/.test(a.name)||!['.png','.dxf','.json','.txt','.md','.csv'].includes(path.extname(a.name).toLowerCase()))fail('SVG/authoring or unsupported attachment in blind packet');
      const relative=`${input.turnId}/${a.name}`;if(files.has(relative))fail('duplicate packet attachment');
      const bytes=fs.readFileSync(a.path);files.set(relative,bytes);attachments.push({name:a.name,path:relative,sha256:sha256(bytes)});
    }
    history.push({turnId:input.turnId,messagePath,attachments});
  }
  const descriptor={schemaVersion:1,caseId:current.id,turnId:current.turnId,inputBinding:current.inputBinding,history,files:[...files].map(([relative,bytes])=>({path:relative,sha256:sha256(bytes),bytes:bytes.length})).sort((a,b)=>a.path.localeCompare(b.path))};
  return {descriptor,files};
}
function publicTurns(record) {
  if(!/^MM-\d{3}$/.test(record.id))fail('independent reconstruction currently supports MM cases only');
  const {getPublicTurnInput}=require('./corpus-provider.cjs');
  return record.contract.turns.map((_,index)=>getPublicTurnInput(record,index));
}
function exportPacket(record,turnIndex,outDir) {
  const built=buildPacketFiles(publicTurns(record),turnIndex);
  if(fs.existsSync(outDir))fail('packet destination already exists');
  fs.mkdirSync(outDir,{recursive:true});
  for(const [relative,bytes]of built.files){const file=path.join(outDir,relative);fs.mkdirSync(path.dirname(file),{recursive:true});fs.writeFileSync(file,bytes,{flag:'wx'});}
  fs.writeFileSync(path.join(outDir,'packet.json'),jsonBytes(built.descriptor),{flag:'wx'});
  return {caseId:record.id,turnId:built.descriptor.turnId,path:outDir,packetSha256:sha256(fs.readFileSync(path.join(outDir,'packet.json')))};
}
function verifyPacket(directory) {
  const bytes=fs.readFileSync(safeFile(directory,'packet.json')),packet=JSON.parse(bytes);
  if(packet.schemaVersion!==1||!/^MM-\d{3}$/.test(packet.caseId)||!/^t\d+$/.test(packet.turnId)||packet.inputBinding?.inputEdition!=='current'||!Array.isArray(packet.files)||!Array.isArray(packet.history))fail('invalid packet schema');
  const declared=packet.files.map(f=>f.path);
  if(new Set(declared).size!==declared.length||!equal([...declared,'packet.json'].sort(),listFiles(directory)))fail('undeclared or missing packet files');
  for(const item of packet.files){
    if(!HASH.test(item.sha256||'')||!Number.isSafeInteger(item.bytes)||item.bytes<0||/\.svg$/i.test(item.path)||/(?:^|\/)(?:model-state|contract\.json|acceptance\.json|native-|reference-)/i.test(item.path))fail('unsafe/private packet file');
    const data=fs.readFileSync(safeFile(directory,item.path));if(sha256(data)!==item.sha256||data.length!==item.bytes)fail('packet file hash mismatch');
  }
  return {packet,packetSha256:sha256(bytes)};
}
function checkProvenance(provenance,submission) {
  if(provenance.schemaVersion!==1||!equal(provenance.reviewer,submission.reviewer)||provenance.method!==METHOD||provenance.packetSha256!==submission.packetSha256||provenance.inputScope!=='packet-only'||provenance.authoringParticipation!==false||provenance.hiddenAccess!==false||provenance.freshContext!==true||typeof provenance.dispatchEvidence!=='string'||!provenance.dispatchEvidence.trim())fail('independent dispatch provenance is incomplete');
}
function sealSubmission({packetDir,submissionFile,provenanceFile,outDir}) {
  const {packet,packetSha256}=verifyPacket(packetDir),submissionBytes=fs.readFileSync(submissionFile),provenanceBytes=fs.readFileSync(provenanceFile);
  const submission=validateSubmission(JSON.parse(submissionBytes)),provenance=JSON.parse(provenanceBytes);checkProvenance(provenance,submission);
  if(submission.caseId!==packet.caseId||submission.turnId!==packet.turnId||submission.packetSha256!==packetSha256)fail('submission packet binding mismatch');
  if(fs.existsSync(outDir))fail('sealed evidence destination already exists');
  const receipt={schemaVersion:1,method:METHOD,caseId:packet.caseId,turnId:packet.turnId,inputBinding:packet.inputBinding,packetSha256,submissionSha256:sha256(submissionBytes),provenanceSha256:sha256(provenanceBytes),reviewer:submission.reviewer,sealedAt:new Date().toISOString()};
  fs.mkdirSync(outDir,{recursive:true});fs.cpSync(packetDir,path.join(outDir,'packet'),{recursive:true,dereference:false,errorOnExist:true});
  fs.writeFileSync(path.join(outDir,'submission.json'),submissionBytes,{flag:'wx'});fs.writeFileSync(path.join(outDir,'provenance.json'),provenanceBytes,{flag:'wx'});fs.writeFileSync(path.join(outDir,'receipt.json'),jsonBytes(receipt),{flag:'wx'});
  verifySeal(outDir);return receipt;
}
function verifySeal(directory) {
  const receipt=readJson(safeFile(directory,'receipt.json')),{packet,packetSha256}=verifyPacket(path.join(directory,'packet'));
  if(receipt.schemaVersion!==1||receipt.method!==METHOD||!Number.isFinite(Date.parse(receipt.sealedAt))||receipt.packetSha256!==packetSha256||!equal(receipt.inputBinding,packet.inputBinding)||receipt.caseId!==packet.caseId||receipt.turnId!==packet.turnId)fail('seal packet binding mismatch');
  const bytes=fs.readFileSync(safeFile(directory,'submission.json')),provenanceBytes=fs.readFileSync(safeFile(directory,'provenance.json'));
  if(sha256(bytes)!==receipt.submissionSha256)fail('submission hash mismatch');if(sha256(provenanceBytes)!==receipt.provenanceSha256)fail('provenance hash mismatch');
  const submission=validateSubmission(JSON.parse(bytes)),provenance=JSON.parse(provenanceBytes);checkProvenance(provenance,submission);
  if(submission.caseId!==packet.caseId||submission.turnId!==packet.turnId||submission.packetSha256!==packetSha256||!equal(receipt.reviewer,submission.reviewer))fail('sealed submission identity mismatch');
  return {receipt,packet,submission,provenance};
}
function graderSources(root) {
  return [[__filename,'lib/public-input-review.cjs'],[CLI,'scripts/research300/blind_input_review.cjs']].map(([file,relative])=>({path:relative,sha256:sha256(fs.readFileSync(file))}));
}
function gradeEvidence(record,receiptPaths) {
  if(!Array.isArray(receiptPaths)||!receiptPaths.length)fail('sealed evidence is required before grading');
  const inputs=publicTurns(record),inputBinding=inputs[0].inputBinding,turns=[],seen=new Set();
  for(const receiptPath of receiptPaths){
    const receiptFile=safeFile(record.root,receiptPath),directory=path.dirname(receiptFile),sealed=verifySeal(directory),turnId=sealed.packet.turnId;
    if(path.basename(receiptFile)!=='receipt.json'||sealed.packet.caseId!==record.id||!equal(sealed.packet.inputBinding,inputBinding)||seen.has(turnId))fail('old/different/duplicate review input binding');seen.add(turnId);
    const index=inputs.findIndex(t=>t.turnId===turnId);if(index<0)fail('review turn absent from current input');
    const authoritative=buildPacketFiles(inputs,index);
    if(!equal(sealed.packet,authoritative.descriptor))fail('packet differs from authoritative public-only input');
    const turn=record.contract.turns[index],state=turn.state??record.contract.turns.slice(index+1).find(t=>t.state!==null)?.state;
    if(!Number.isInteger(state)||state<1||!record.contract.modelStates[state-1])fail('no frozen physical state for this turn');
    const expected=readJson(safeFile(record.caseDir,record.contract.modelStates[state-1]));
    // The validated current provider regenerates PNG/DXF from these exact
    // released public sources. Recover textual conventions for grading from
    // their original public files, never from model truth or future releases.
    const {getFrozenPublicTurnInput}=require('./corpus-provider.cjs');
    const releasedSources=record.contract.turns.slice(0,index+1).map((_,i)=>getFrozenPublicTurnInput(record,i));
    const analysisConventions=getReleasedAnalysisConventions(releasedSources,index);
    const result=compareReconstruction(sealed.submission,expected,{id:record.id,turn,analysisConventions},sealed.packet);
    const evidence=Object.fromEntries([['receipt','receipt.json'],['packet','packet/packet.json'],['submission','submission.json'],['provenance','provenance.json']].map(([key,name])=>{
      const file=safeFile(directory,name);return[key,{path:path.relative(record.root,file).split(path.sep).join('/'),sha256:sha256(fs.readFileSync(file))}];}));
    for(const [i,attachment]of releasedSources.flatMap(t=>t.attachments).filter(a=>/^analysis-conventions-v2\.(?:md|txt)$/.test(a.name)).entries())
      evidence[`publicConvention${i+1}`]={path:path.relative(record.root,attachment.path).split(path.sep).join('/'),sha256:sha256(fs.readFileSync(attachment.path))};
    turns.push({turnId,...result,reviewer:sealed.submission.reviewer,evidence});
  }
  turns.sort((a,b)=>inputs.findIndex(i=>i.turnId===a.turnId)-inputs.findIndex(i=>i.turnId===b.turnId));
  const coverage=Object.fromEntries(CATEGORIES.map(category=>[category,{required:0,matched:0,missing:0,mismatched:0,unexpected:0,observation:true}]));
  for(const turn of turns)for(const category of CATEGORIES){const row=turn.coverage[category];for(const field of ['required','matched','missing','mismatched','unexpected'])coverage[category][field]+=row[field];coverage[category].observation&&=row.observation;}
  const findings=turns.flatMap(t=>t.findings.map(f=>({turnId:t.turnId,...f})));
  for(const input of inputs)if(!seen.has(input.turnId))findings.push({turnId:input.turnId,code:'missing-turn-review'});
  const status=turns.some(t=>t.status==='failed')?'failed':findings.length?'partial':'passed';
  return {schemaVersion:1,caseId:record.id,inputEdition:'current',inputBinding,method:METHOD,grader:{version:VERSION,sources:graderSources(record.root)},status,coverage,findings,scope:turns[0].scope,turns};
}
Object.assign(module.exports,{buildPacketFiles,exportPacket,verifyPacket,sealSubmission,verifySeal,gradeEvidence});
