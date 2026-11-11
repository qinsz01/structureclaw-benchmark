'use strict';
const test = require('node:test'), assert = require('node:assert/strict'), fs = require('node:fs'), path = require('node:path');
const zlib = require('node:zlib');
const {fixture,clone,authoredResponseRecord}=require('./research300-test-fixtures.cjs');
const {loadCorpus,loadCase,getPublicTurnInput,getFrozenPublicTurnInput,getResponseContract,RESPONSE_CONTRACT_VERSION,validatePublicAttachments,resolveCaseFile}=require('./corpus-provider.cjs');
const load=f=>loadCase(loadCorpus({corpus:'research-300',root:f.root}),f.contract.id);
test('the default provider loads the current research corpus and its canonical input',()=>{const c=loadCorpus();assert.equal(c.id,'research-300');assert.equal(c.cases.length,300);const r=loadCase(c,c.cases[0].id);assert.equal(getPublicTurnInput(r,0).inputEdition,'current');});
test('explicit historical corpus loading remains available for provenance checks',()=>{const c=loadCorpus({corpus:'legacy-150'});assert.equal(c.cases.length,150);const r=loadCase(c,c.cases[0].id);assert.equal(typeof getPublicTurnInput(r,0).instruction,'string');});
test('original public turn boundary includes only current instruction and newly released source files',t=>{
 const f=fixture(t);f.contract.attachments.push('late.csv');f.write('late.csv','span_m\n6\n');f.contract.turns.push({...f.contract.turns[0],id:'t2',attachments:['late.csv'],requiredOutputIds:[]});for(const output of f.contract.requiredOutputs)output.turnIds=['t1'];f.save();const record=load(f);
 const first=getFrozenPublicTurnInput(record,0),second=getFrozenPublicTurnInput(record,1);
 assert.deepEqual(Object.keys(first).sort(),['attachments','id','instruction','responseContract','turnId']);assert.equal(first.attachments.some(a=>a.name==='late.csv'),false);assert.deepEqual(second.attachments.map(a=>a.name),['late.csv']);assert.doesNotMatch(JSON.stringify(first),/model-state|reference-requests|expectedQuestions|requiredOutputs/);
 assert.throws(()=>getPublicTurnInput(record,-1));assert.throws(()=>getPublicTurnInput(record,2));
});
test('traversal, encoded paths, backslashes and absolute paths are rejected',t=>{const f=fixture(t);for(const value of ['../model.json','a/../../model.json','/tmp/a','a\\b.json','%2e%2e/a','C:/a.json','a//b','./properties.json'])assert.throws(()=>resolveCaseFile(f.caseDir,value),/Unsafe/);});
test('top-level whitelist does not permit a hidden model or reference turn attachment',t=>{
 const f=fixture(t);f.contract.turns[0].attachments.push('model-state-1.json');assert.match(validatePublicAttachments(f.caseDir,f.contract).join('\n'),/not whitelisted|Not an allowed/);
 f.contract.attachments.push('model-state-1.json');assert.match(validatePublicAttachments(f.caseDir,f.contract).join('\n'),/Not an allowed/);
});
test('native commercial evidence stays private under nested paths and after renaming', t => {
 const f=fixture(t),name='native-commercial/evidence/state-1/result.txt';
 f.write(name,'synthetic raw force: 123\n');
 const c=clone(f.contract);c.attachments.push(name);c.turns[0].attachments.push(name);
 assert.match(validatePublicAttachments(f.caseDir,c).join('\n'),/Not an allowed public attachment/);
 f.write('renamed-result.txt','synthetic raw force: 123\n');
 c.attachments[c.attachments.length-1]='renamed-result.txt';c.turns[0].attachments[c.turns[0].attachments.length-1]='renamed-result.txt';
 assert.match(validatePublicAttachments(f.caseDir,c).join('\n'),/copies a private file/);
});
test('symlinks, hardlinks and renamed structured answer copies cannot become public',t=>{
 const f=fixture(t);for(const type of ['symlink','hardlink','copy']){
  const name=`${type}.json`,dest=path.join(f.caseDir,name);if(type==='symlink')fs.symlinkSync('/etc/passwd',dest);else if(type==='hardlink')fs.linkSync(path.join(f.caseDir,'model-state-1.json'),dest);else f.write(name,{wrapper:f.model});
  const c={...f.contract,attachments:[...f.contract.attachments,name],turns:[{...f.contract.turns[0],attachments:[...f.contract.attachments,name]}]};assert.ok(validatePublicAttachments(f.caseDir,c).length,type);fs.unlinkSync(dest);
 }
});
test('public validation runs again after load to reject changed files',t=>{const f=fixture(t),record=load(f);f.write('properties.json',{states:[{quantities:[{value:123}]}]});assert.throws(()=>getPublicTurnInput(record,0),/Private/);});
test('ordinary public geometry JSON is allowed; hidden SVG metadata is not',t=>{const f=fixture(t);f.write('geometry.csv',JSON.stringify({nodes:[{id:'a',x:0,y:0,z:0}],elements:[{id:'am',nodes:['a','m']}]}));assert.deepEqual(validatePublicAttachments(f.caseDir,f.contract),[]);f.write('drawing.svg','<svg><metadata>answer</metadata><text>6m</text></svg>');f.contract.attachments.push('drawing.svg');f.contract.turns[0].attachments.push('drawing.svg');assert.match(validatePublicAttachments(f.caseDir,f.contract).join('\n'),/SVG/);});
test('case directory symlink escape is rejected before loading',t=>{const f=fixture(t);fs.symlinkSync('/tmp',path.join(f.root,'corpora/research-300/cases/STD-002'));assert.throws(()=>loadCorpus({corpus:'research-300',root:f.root}),/Symlink/);});
test('public requested output definitions are allowed but hidden values and tolerances are rejected',t=>{const f=fixture(t),q={id:'left',selection:{kind:'case',id:'D'},location:{kind:'node',id:'a'},component:'Fz',unit:'kN'};f.contract.attachments.push('output-requests.json');f.contract.turns[0].attachments.push('output-requests.json');f.write('output-requests.json',{quantities:[q],derived:[]});assert.deepEqual(validatePublicAttachments(f.caseDir,f.contract),[]);q.value=60;f.write('output-requests.json',{quantities:[q]});assert.match(validatePublicAttachments(f.caseDir,f.contract).join('\n'),/Private/);delete q.value;q.tolerance={absolute:1e-8,relative:1e-6};f.write('output-requests.json',{quantities:[q]});assert.match(validatePublicAttachments(f.caseDir,f.contract).join('\n'),/Private/);});
test('renaming JSON to a binary attachment extension does not bypass inspection',t=>{const f=fixture(t);for(const ext of ['png','jpg','pdf']){const file='input.'+ext;f.write(file,JSON.stringify({wrapped:f.model}));const c={...f.contract,attachments:[file],turns:[{...f.contract.turns[0],attachments:[file]}]};assert.match(validatePublicAttachments(f.caseDir,c).join('\n'),/Invalid/);}});
test('DXF must contain actual paired ASCII entity sections and end marker',t=>{const f=fixture(t);f.write('input.dxf','this is not a CAD document');const c={...f.contract,attachments:['input.dxf'],turns:[{...f.contract.turns[0],attachments:['input.dxf']}]};assert.match(validatePublicAttachments(f.caseDir,c).join('\n'),/DXF/);f.write('input.dxf','0\nSECTION\n2\nENTITIES\n0\nLINE\n10\n0\n20\n0\n11\n6\n21\n0\n0\nENDSEC\n0\nEOF\n');assert.deepEqual(validatePublicAttachments(f.caseDir,c),[]);});
test('SVG relative includes and XML entities cannot escape attachment confinement',t=>{const f=fixture(t),c={...f.contract,attachments:['drawing.svg'],turns:[{...f.contract.turns[0],attachments:['drawing.svg']}]};for(const text of ['<svg><image href="../../outside.png"/></svg>','<!DOCTYPE svg [<!ENTITY leak SYSTEM "file:///etc/passwd">]><svg>&leak;</svg>','<svg><style>text{fill:url(../../outside.svg)}</style></svg>']){f.write('drawing.svg',text);assert.match(validatePublicAttachments(f.caseDir,c).join('\n'),/SVG/);}f.write('drawing.svg','<svg><defs><marker id="arrow"/></defs><line marker-end="url(#arrow)"/><style>line{marker-end:url("#arrow")}</style></svg>');assert.deepEqual(validatePublicAttachments(f.caseDir,c),[]);});

const responseIds = response => response.quantities.map(q=>q.id).sort();
const publicQuantity = q => ({id:q.id,selection:{kind:q.selection.kind,id:q.selection.id},location:{kind:q.location.kind,id:q.location.id,...(q.location.positionM===undefined?{}:{positionM:q.location.positionM}),...(q.location.side===undefined?{}:{side:q.location.side})},component:q.component,unit:q.unit});

test('response contract discloses the signed table and derived reporting protocols',t=>{
 const f=fixture(t),record=load(f),response=getResponseContract(record,0);
 assert.equal(RESPONSE_CONTRACT_VERSION,'research300-response-v1');
 assert.equal(response.version,RESPONSE_CONTRACT_VERSION);
 assert.deepEqual(response,getResponseContract(record,0));
 assert.equal(response.format.type,'markdown-table');
 assert.equal(response.format.target,'report.markdown');
 assert.deepEqual(response.format.columns,['quantityId','selection','location','component','value','unit']);
 for(const name of response.format.columns)assert.ok(response.format.header.includes(name),name);
 assert.match(response.format.selection,/case/);assert.match(response.format.selection,/combination/);
 assert.match(response.format.location,/node/);assert.match(response.format.location,/member/);
 assert.match(response.format.location,/position|station|positionM/);assert.match(response.format.location,/left|right|side/);
 assert.match(response.format.value,/sign/i);
 assert.equal(typeof response.format.rowTemplate,'string');assert.ok(response.format.rowTemplate.includes('|'));
 assert.equal(response.format.derived.target,'report.derivedQuantities');
 assert.deepEqual(response.format.derived.fields,['id','value','unit']);
 assert.match(response.format.derived.messageFormat,/fenced json/i);
 assert.match(response.format.derived.messageFormat,/derivedQuantities/);
 assert.match(response.format.derived.messageFormat,/difference and sum.*null/);
 assert.deepEqual(response.format.derived.governingFields,['governingOperand','governingSelection']);
 assert.match(response.format.derived.governingOperand,/member|node/);
 assert.match(response.format.derived.governingSelection,/case|combination/);
 assert.match(response.format.derived.governingLocation,/governingLocation.*kind.*node.*member.*positionM.*side/);
 assert.match(response.format.derived.governingLocation,/governingOperand as the bare ID/);
 assert.deepEqual(response.quantities,record.referenceRequests.states[0].quantities.map(publicQuantity));
 assert.deepEqual(response.derived,[]);
});

test('actual INT003 keeps x3.25 and x2.5 report selectors in their respective turns',()=>{
 const record=authoredResponseRecord('INT-003'),first=getResponseContract(record,0),second=getResponseContract(record,1);
 assert.deepEqual(responseIds(first),['D-x3p25-uz','D-x6p5-uz']);
 assert.deepEqual(responseIds(second),['D-x2p5-uz','D-x6p5-uz']);
 assert.deepEqual(first.quantities.find(q=>q.id==='D-x3p25-uz').location,{kind:'node',id:'n2'});
 assert.deepEqual(second.quantities.find(q=>q.id==='D-x2p5-uz').location,{kind:'node',id:'n1'});
 assert.doesNotMatch(JSON.stringify(first),/D-x2p5-uz|requested-output-2|t2:interaction|"id":"n1"/);
 assert.doesNotMatch(JSON.stringify(second),/D-x3p25-uz|requested-output-1|t1:interaction|"id":"n2"/);
 assert.deepEqual(first.outputs.map(o=>o.id).sort(),['requested-output-1','s1:D-x3p25-uz','s1:D-x6p5-uz','t1:interaction']);
 assert.deepEqual(second.outputs.map(o=>o.id).sort(),['requested-output-2','s1:D-x2p5-uz','s1:D-x6p5-uz','t2:interaction']);
 const interaction=first.outputs.find(o=>o.kind==='interaction');
 assert.equal(interaction.description,record.contract.requiredOutputs.find(o=>o.id===interaction.id).description);
});

test('actual INT097 publishes only current m or mm quantities and report units',()=>{
 const record=authoredResponseRecord('INT-097'),before=clone(record);
 for(const [turnIndex,unit] of [[0,'m'],[1,'mm']]){
  const response=getResponseContract(record,turnIndex),turn=record.contract.turns[turnIndex];
  assert.deepEqual(responseIds(response),[...turn.requiredQuantityIds].sort());
  assert.deepEqual(response.outputs.map(o=>o.id).sort(),[...turn.requiredOutputIds].sort());
  assert.ok(response.quantities.every(q=>q.unit===unit));
  assert.deepEqual(response.quantities.map(q=>q.location),[{kind:'node',id:'top'},{kind:'node',id:'top'}]);
 }
 assert.deepEqual(record,before,'display-unit conversion must not rewrite hidden reference requests');
});

test('actual INT033 reports five known values before clarification and max only after clarification',()=>{
 const record=authoredResponseRecord('INT-033'),first=getResponseContract(record,0),second=getResponseContract(record,1);
 const ordinary=['case:D:node:T2:ux','case:D:node:T2:uz','case:D:node:B0:Fx','case:D:node:B0:Fz','case:D:member:BC0:0:right:N'].sort();
 assert.equal(record.contract.turns[0].clarificationBlocksAnalysis,false);
 assert.deepEqual(responseIds(first),ordinary);assert.deepEqual(first.derived,[]);
 assert.deepEqual(responseIds(second),ordinary);
 assert.equal(second.derived.length,1);assert.equal(second.derived[0].id,'case:D:all-members:max-abs-N');
 assert.equal(second.derived[0].operation,'max_abs');assert.equal(second.derived[0].unit,'kN');
 assert.equal(second.derived[0].tiePolicy,'any');
 assert.match(second.derived[0].description,/21/);assert.equal(Object.hasOwn(second.derived[0],'operands'),false);
 assert.doesNotMatch(JSON.stringify(first),/case:D:all-members:max-abs-N/);
 const privateIds=record.referenceRequests.states[0].quantities.filter(q=>!ordinary.includes(q.id)).map(q=>q.id);
 assert.equal(privateIds.length,20);
 for(const id of privateIds){assert.equal(JSON.stringify(first).includes(id),false,id);assert.equal(JSON.stringify(second).includes(id),false,id);}
 assert.doesNotMatch(JSON.stringify(second),/tolerance|expectedQuestions|model-state|requirementCoverage/);
});

test('response projection strips nested truth, tolerance and model metadata without mutating sources',t=>{
 const f=fixture(t),record=load(f),q=record.referenceRequests.states[0].quantities[0];
 Object.assign(q,{value:987654321,scoring:{hidden:'SECRET_SCORE'},model:{nodes:['SECRET_MODEL']}});
 Object.assign(q.selection,{value:987654322,tolerance:{secret:'SECRET_SELECTION'},model:{secret:'SECRET_SELECTION_MODEL'}});
 Object.assign(q.location,{value:987654323,tolerance:{secret:'SECRET_LOCATION'},model:{secret:'SECRET_LOCATION_MODEL'}});
 Object.assign(record.contract.requiredOutputs[0],{value:987654324,expectedAnswer:'SECRET_EXPECTED',scoring:{secret:'SECRET_OUTPUT'}});
 record.contract.turns[0].expectedQuestions=['SECRET_QUESTION'];
 record.contract.requirementCoverage=[{sourceField:'SECRET_COVERAGE',targets:['SECRET_TARGET']}];
 record.referenceRequests.states[0].model='SECRET_MODEL_FILE';
 const before=clone(record),response=getResponseContract(record,0);
 assert.deepEqual(response.quantities[0],publicQuantity(q));
 assert.doesNotMatch(JSON.stringify(response),/98765432|SECRET_|tolerance|expectedQuestions|requirementCoverage|scoring|expectedAnswer/);
 assert.deepEqual(record,before);
 response.quantities[0].selection.id='mutated';response.quantities[0].location.id='mutated';response.outputs[0].quantityIds.push('mutated');
 assert.deepEqual(record,before,'public objects and nested arrays must be detached from hidden inputs');
});

test('explicit output and quantity IDs intersect and explicit empty lists never mean every answer',t=>{
 const f=fixture(t),record=load(f),turn=record.contract.turns[0];
 turn.requiredOutputIds=['reactions'];turn.requiredQuantityIds=['D:left'];
 let response=getResponseContract(record,0);
 assert.deepEqual(responseIds(response),['D:left']);assert.deepEqual(response.outputs.map(o=>o.id),['reactions']);
 assert.deepEqual(response.outputs[0].quantityIds,['D:left']);
 turn.requiredOutputIds=[];delete turn.requiredQuantityIds;
 response=getResponseContract(record,0);assert.deepEqual(response.quantities,[]);assert.deepEqual(response.derived,[]);assert.deepEqual(response.outputs,[]);
 turn.requiredOutputIds=['reactions'];turn.requiredQuantityIds=[];
 response=getResponseContract(record,0);assert.deepEqual(response.quantities,[]);assert.deepEqual(response.derived,[]);
 assert.ok(response.outputs.every(o=>o.quantityIds.length===0));
});

test('quantity-only scope does not reveal unrelated unscoped same-state output IDs',t=>{
 const f=fixture(t),record=load(f),turn=record.contract.turns[0];
 turn.requiredQuantityIds=['D:left'];record.contract.turns.push({...clone(turn),id:'t2',expectation:'query',requiredQuantityIds:['D:right']});
 const first=getResponseContract(record,0),second=getResponseContract(record,1);
 assert.deepEqual(responseIds(first),['D:left']);assert.deepEqual(responseIds(second),['D:right']);
 assert.deepEqual(first.outputs,[]);assert.deepEqual(second.outputs,[]);
 assert.doesNotMatch(JSON.stringify(first),/D:right|D:mid|midpoint|reactions/);
});

test('same-state answer turns without explicit scope fail closed instead of revealing future requests',t=>{
 const f=fixture(t),record=load(f);record.contract.turns.push({...clone(record.contract.turns[0]),id:'t2',expectation:'query'});
 assert.throws(()=>getResponseContract(record,0),/scope|ambig|turn/i);
 assert.throws(()=>getResponseContract(record,1),/scope|ambig|turn/i);
});

test('current turn output IDs cannot override another output turn binding',()=>{
 const record=authoredResponseRecord('INT-003');record.contract.turns[0].requiredOutputIds=['requested-output-2'];
 assert.throws(()=>getResponseContract(record,0),/scope|turn|output/i);
});

test('blocking clarification exposes no numerical definitions even when an earlier state is known',t=>{
 const f=fixture(t),record=load(f),turn=record.contract.turns[0];
 turn.expectation='clarify';turn.unresolvedFields=['/load_cases/0/loads/0/wz'];turn.expectedQuestions=['SECRET_PHYSICAL_INPUT'];
 turn.requiredOutputIds=['clarification'];
 for(const output of record.contract.requiredOutputs)output.turnIds=['t2'];
 const clarification={id:'clarification',kind:'interaction',state:null,quantityIds:[],turnIds:['t1'],description:'Ask for the missing physical input.'};
 record.contract.requiredOutputs.push(clarification);
 record.contract.turns.push({...clone(turn),id:'t2',state:1,expectation:'analyze',unresolvedFields:[],expectedQuestions:[],requiredOutputIds:['reactions','midpoint']});
 for(const state of [null,1]){
  turn.state=state;clarification.state=state;const response=getResponseContract(record,0);
  assert.deepEqual(response.quantities,[]);assert.deepEqual(response.derived,[]);
  assert.ok(response.outputs.every(o=>o.kind==='interaction'));
  assert.doesNotMatch(JSON.stringify(response),/D:left|D:right|D:mid|SECRET_PHYSICAL_INPUT/);
 }
 record.contract.requiredOutputs[0].turnIds=['t1'];turn.requiredOutputIds=['reactions'];
 assert.throws(()=>getResponseContract(record,0),/clarif|numerical/i);
});

test('per-quantity outputUnits override component outputUnits without changing source units',t=>{
 const f=fixture(t),record=load(f),turn=record.contract.turns[0];
 turn.outputUnits={Fz:'N',uz:'mm','D:left':'kN'};const response=getResponseContract(record,0);
 assert.deepEqual(Object.fromEntries(response.quantities.map(q=>[q.id,q.unit])),{'D:left':'kN','D:right':'N','D:mid-u':'mm','D:mid-M':'kN.m'});
 assert.equal(record.referenceRequests.states[0].quantities.find(q=>q.id==='D:mid-u').unit,'m');
});

test('derived operands are public only when every operand is independently requested now',t=>{
 const f=fixture(t),record=load(f),state=record.referenceRequests.states[0],turn=record.contract.turns[0];
 state.derived=[{id:'reaction-total',operation:'sum',operands:['D:left','D:right'],unit:'kN',description:'Signed total support reaction.'}];
 record.contract.requiredOutputs.push({id:'total',kind:'derived',state:1,quantityIds:['reaction-total'],description:'Signed total support reaction.'});
 turn.requiredOutputIds=['reactions','total'];turn.requiredQuantityIds=['D:left','D:right','reaction-total'];
 let response=getResponseContract(record,0);assert.deepEqual(response.derived[0].operands,['D:left','D:right']);
 turn.requiredQuantityIds=['D:left','reaction-total'];response=getResponseContract(record,0);
 assert.deepEqual(responseIds(response),['D:left']);assert.equal(Object.hasOwn(response.derived[0],'operands'),false);
 assert.doesNotMatch(JSON.stringify(response),/D:right/);
 turn.requiredOutputIds=['total'];turn.requiredQuantityIds=['reaction-total'];response=getResponseContract(record,0);
 assert.deepEqual(response.quantities,[]);assert.equal(Object.hasOwn(response.derived[0],'operands'),false);
 assert.doesNotMatch(JSON.stringify(response),/D:left|D:right/);
});

test('a requested derived result never expands private recursive calculation operands',t=>{
 const f=fixture(t),record=load(f),state=record.referenceRequests.states[0],turn=record.contract.turns[0];
 state.quantities.push({id:'PRIVATE_Q',selection:{kind:'combination',id:'PRIVATE_SELECTION'},location:{kind:'member',id:'PRIVATE_MEMBER',positionM:17.25,side:'right'},component:'N',unit:'kN',value:998877,tolerance:{absolute:1,relative:2}});
 state.derived=[{id:'PRIVATE_SUM',operation:'sum',operands:['D:left','PRIVATE_Q'],unit:'kN',description:'PRIVATE_DESCRIPTION'},{id:'public-max',operation:'max_abs',operands:['PRIVATE_SUM','D:right'],unit:'kN',description:'Maximum absolute support-group force, with its signed value.',value:998878,tolerance:{absolute:3,relative:4},model:{secret:'PRIVATE_MODEL'}}];
 record.contract.requiredOutputs=[{id:'current-max',kind:'derived',state:1,quantityIds:['public-max'],description:'Maximum support-group force.'}];
 turn.requiredOutputIds=['current-max'];turn.requiredQuantityIds=['public-max'];
 const response=getResponseContract(record,0);
 assert.deepEqual(response.quantities,[]);
 assert.deepEqual(response.derived,[{id:'public-max',operation:'max_abs',unit:'kN',description:'Maximum absolute support-group force, with its signed value.',tiePolicy:'first'}]);
 assert.doesNotMatch(JSON.stringify(response),/PRIVATE_|99887|17\.25|D:left|D:right|tolerance/);
});

test('partial figure bundles fail closed before descriptions can disclose excluded selectors',t=>{
 const record=load(fixture(t));
 record.contract.requiredOutputs=[{id:'plot',kind:'figure',state:1,quantityIds:['D:left','D:right'],description:'Plot the left reaction and future-only RIGHT_STATION.'}];
 record.contract.turns[0].requiredQuantityIds=['D:left'];
 assert.throws(()=>getResponseContract(record,0),/partially excludes a figure/);
 record.contract.turns[0].requiredQuantityIds.push('D:right');
 assert.equal(getResponseContract(record,0).outputs[0].description,'Plot the left reaction and future-only RIGHT_STATION.');
});

test('provider rejects malformed output metadata and force-as-displacement reporting without a validator call',t=>{
 const record=load(fixture(t)),turn=record.contract.turns[0];
 turn.outputUnits=null;assert.throws(()=>getResponseContract(record,0),/outputUnits/);delete turn.outputUnits;
 const outputs=record.contract.requiredOutputs;record.contract.requiredOutputs=null;
 assert.throws(()=>getResponseContract(record,0),/requiredOutputs/);record.contract.requiredOutputs=outputs;
 record.referenceRequests.states[0].quantities[0].unit='m';turn.outputUnits={'D:left':'mm'};
 assert.throws(()=>getResponseContract(record,0),/component\/unit/);
});

test('public descriptions cannot reintroduce private intermediate or future quantity IDs',t=>{
 const record=load(fixture(t));
 record.referenceRequests.states[0].derived=[{id:'total',operation:'sum',operands:['D:left','D:right'],unit:'kN',description:'Sum of D:left and D:right.'}];
 record.contract.requiredOutputs=[{id:'total-output',kind:'derived',state:1,quantityIds:['total'],description:'Signed total support reaction.'}];
 assert.throws(()=>getResponseContract(record,0),/non-current quantity ID/);
 record.referenceRequests.states[0].derived[0].description='Signed total support reaction.';
 assert.equal(getResponseContract(record,0).derived[0].description,'Signed total support reaction.');
 record.contract.requiredOutputs.push({id:'discussion',kind:'interaction',state:1,quantityIds:[],description:'Discuss D:mid-u.'});
 assert.throws(()=>getResponseContract(record,0),/non-current quantity ID/);
});

test('unrequested same-name private quantities stay hidden while ambiguous requested IDs fail closed',t=>{
 const record=load(fixture(t)),state=record.referenceRequests.states[0],q=clone(state.quantities[0]);
 q.id='PRIVATE_DUPLICATE';state.quantities.push(q,{...clone(q),selection:{kind:'combination',id:'D'}});
 assert.doesNotMatch(JSON.stringify(getResponseContract(record,0)),/PRIVATE_DUPLICATE/);
 record.contract.requiredOutputs[0].quantityIds.push(q.id);
 assert.throws(()=>getResponseContract(record,0),/Ambiguous response quantity ID/);
});

test('malformed requested derived definitions cannot silently omit missing operands',t=>{
 const record=load(fixture(t)),state=record.referenceRequests.states[0];
 record.contract.requiredOutputs=[{id:'total-output',kind:'derived',state:1,quantityIds:['total'],description:'Total reaction.'}];
 state.derived=[{id:'total',operation:'sum',unit:'kN',description:'Total reaction.'}];
 assert.throws(()=>getResponseContract(record,0),/derived operands/);
 state.derived[0].operands=['DOES_NOT_EXIST'];
 assert.throws(()=>getResponseContract(record,0),/derived operands/);
 state.derived[0].operands=['D:left','D:right'];
 assert.equal(Object.hasOwn(getResponseContract(record,0).derived[0],'operands'),false);
});

test('extrema disclose frozen tie policy without publishing co-governors or calculation truth',t=>{
 const record=load(fixture(t)),state=record.referenceRequests.states[0];
 record.contract.requiredOutputs=[{id:'extreme-output',kind:'derived',state:1,quantityIds:['extreme'],description:'Governing support reaction.'}];
 for(const operation of ['max','min','max_abs'])for(const tiePolicy of [undefined,'first','any']){
  const request={id:'extreme',operation,operands:['D:left','D:right'],unit:'kN',description:'Governing support reaction.',coGoverningOperands:['D:left','D:right'],value:987654321,tolerance:{absolute:7654321,relative:654321},governingOperand:'D:right',governingSelection:{kind:'case',id:'PRIVATE_GOVERNOR_CASE'},model:{nodes:['PRIVATE_NODE']},expectedQuestions:['PRIVATE_QUESTION']};
  if(tiePolicy!==undefined)request.tiePolicy=tiePolicy;
  state.derived=[request];const before=clone(state),response=getResponseContract(record,0);
  assert.deepEqual(response.derived,[{id:'extreme',operation,unit:'kN',description:'Governing support reaction.',tiePolicy:tiePolicy??'first'}]);
  assert.deepEqual(response.quantities,[]);
  assert.doesNotMatch(JSON.stringify(response),/coGoverningOperands|D:left|D:right|987654321|7654321|654321|PRIVATE_|tolerance|expectedQuestions/);
  assert.deepEqual(state,before,'defaulting the public policy must not mutate frozen hidden requests');
 }
});

test('sum and difference omit tie policy while malformed or inapplicable policies reject',t=>{
 const record=load(fixture(t)),state=record.referenceRequests.states[0];
 record.contract.requiredOutputs=[{id:'derived-output',kind:'derived',state:1,quantityIds:['result'],description:'Requested reaction calculation.'}];
 const request={id:'result',operation:'sum',operands:['D:left','D:right'],unit:'kN',description:'Requested reaction calculation.'};
 state.derived=[request];
 for(const operation of ['sum','difference']){
  request.operation=operation;delete request.tiePolicy;
  assert.equal(Object.hasOwn(getResponseContract(record,0).derived[0],'tiePolicy'),false,operation);
  for(const tiePolicy of ['first','any']){
   request.tiePolicy=tiePolicy;assert.throws(()=>getResponseContract(record,0),/tie.?policy|extrem/i,`${operation} must reject ${tiePolicy}`);
  }
 }
 for(const operation of ['max','min','max_abs'])for(const tiePolicy of ['last','ALL','',null,0,true,{},['any']]){
  request.operation=operation;request.tiePolicy=tiePolicy;
  assert.throws(()=>getResponseContract(record,0),/tie.?policy/i,`${operation} must reject ${JSON.stringify(tiePolicy)}`);
 }
});

// Real 2x2 Pillow PNGs, generated independently of the parser/CRC helpers here.
const pillowRGB = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAFklEQVR4nGP4z8DA8J+BkYHh////DAAe9gT9Ce00PgAAAABJRU5ErkJggg==','base64');
const pillowRGBA = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAYAAABytg0kAAAAGUlEQVR4nAXBAQEAAAjDIKI9ms0niOTQKg9AGAe6dfu8vgAAAABJRU5ErkJggg==','base64');
const pngSignature=Buffer.from([137,80,78,71,13,10,26,10]);
function pngChunk(type,body=Buffer.alloc(0)) {
 const tagged=Buffer.concat([Buffer.from(type),body]),prefix=Buffer.alloc(4),suffix=Buffer.alloc(4);
 let crc=0xffffffff;for(const byte of tagged){crc^=byte;for(let i=0;i<8;i++)crc=(crc>>>1)^((crc&1)?0xedb88320:0);}
 prefix.writeUInt32BE(body.length);suffix.writeUInt32BE((crc^0xffffffff)>>>0);return Buffer.concat([prefix,tagged,suffix]);
}
function pngHeader(width=1,height=1,color=2) {const header=Buffer.alloc(13);header.writeUInt32BE(width);header.writeUInt32BE(height,4);header[8]=8;header[9]=color;return header;}
function pngBytes({header=pngHeader(),compressed=zlib.deflateSync(Buffer.from([0,255,255,255])),before=[],after=[]}={}) {
 return Buffer.concat([pngSignature,pngChunk('IHDR',header),...before,...(compressed===null?[]:[pngChunk('IDAT',compressed)]),...after,pngChunk('IEND')]);
}
function binaryFixture(t,bytes,name='drawing.png') {
 const f=fixture(t);f.contract.attachments.push(name);f.contract.turns[0].attachments.push(name);f.save();fs.writeFileSync(path.join(f.caseDir,name),bytes);return f;
}
function assertBinaryRejected(t,bytes,name='drawing.png',pattern=/PNG|Invalid.*(?:format|attachment)/i) {
 const f=binaryFixture(t,bytes,name);assert.throws(()=>getPublicTurnInput(load(f),0),pattern);
}
const hiddenImagePayload=Buffer.from(JSON.stringify({referenceKind:'synthetic-private-reference',states:[{state:1,quantities:[{id:'SECRET',value:42,tolerance:{absolute:1e-8,relative:1e-6}}]}]}));

test('actual Pillow RGB and RGBA PNGs remain valid, including split IDAT streams',t=>{
 const idat=pillowRGB.subarray(41,41+pillowRGB.readUInt32BE(33)),split=Buffer.concat([pillowRGB.subarray(0,33),pngChunk('IDAT',idat.subarray(0,5)),pngChunk('IDAT'),pngChunk('IDAT',idat.subarray(5)),pngChunk('IEND')]);
 for(const bytes of [pillowRGB,pillowRGBA,split]){const f=binaryFixture(t,bytes),result=getFrozenPublicTurnInput(load(f),0),attachment=result.attachments.find(a=>a.relPath==='drawing.png');assert.ok(attachment);assert.deepEqual(fs.readFileSync(attachment.path),bytes);}
});
test('PNG rejects a valid-CRC private ancillary chunk containing hidden reference JSON',t=>{
 assertBinaryRejected(t,pngBytes({before:[pngChunk('ruSt',hiddenImagePayload)]}));
});
test('PNG rejects raw private JSON masquerading as a compressed IDAT',t=>{
 assertBinaryRejected(t,pngBytes({compressed:hiddenImagePayload}));
});
test('PNG verifies CRC for header, image data and ending chunks',t=>{
 for(const offset of [29,55,pillowRGB.length-1]){const corrupted=Buffer.from(pillowRGB);corrupted[offset]^=1;assertBinaryRejected(t,corrupted);}
});
test('PNG rejects missing IDAT even with valid signature, header and IEND',t=>{
 assertBinaryRejected(t,pngBytes({compressed:null}));
});
test('research rejects JPEG containers even with correct start and end signatures',t=>{
 for(const extension of ['jpg','jpeg'])assertBinaryRejected(t,Buffer.concat([Buffer.from([255,216]),hiddenImagePayload,Buffer.from([255,217])]),'drawing.'+extension);
});
test('research rejects PDF containers even with a correct magic prefix and EOF marker',t=>{
 assertBinaryRejected(t,Buffer.concat([Buffer.from('%PDF-1.7\n'),hiddenImagePayload,Buffer.from('\n%%EOF\n')]),'drawing.pdf');
});
test('PNG inflation consumes exactly one image stream and rejects hidden trailing data',t=>{
 const compressed=zlib.deflateSync(Buffer.from([0,255,255,255]));
 for(const extra of [hiddenImagePayload,zlib.deflateSync(hiddenImagePayload)])assertBinaryRejected(t,pngBytes({compressed:Buffer.concat([compressed,extra])}));
});
test('PNG scanline validation accepts all five row filters and rejects invalid filters or pixel lengths',t=>{
 const rows=Buffer.concat([0,1,2,3,4].map(filter=>Buffer.from([filter,10,20,30,40,50,60]))),valid=pngBytes({header:pngHeader(2,5),compressed:zlib.deflateSync(rows)});
 assert.equal(getFrozenPublicTurnInput(load(binaryFixture(t,valid)),0).attachments.some(a=>a.relPath==='drawing.png'),true);
 for(const raw of [Buffer.from([5,255,255,255]),Buffer.from([0,255,255]),Buffer.from([0,255,255,255,0]),Buffer.alloc(1024*1024)])assertBinaryRejected(t,pngBytes({compressed:zlib.deflateSync(raw)}));
});
test('PNG rejects unsupported IHDR modes, dimensions, chunk order and ancillary channels',t=>{
 for(const [offset,value] of [[8,16],[9,0],[9,3],[10,1],[11,1],[12,1]]){const header=pngHeader();header[offset]=value;assertBinaryRejected(t,pngBytes({header}));}
 for(const dimensions of [[0,1],[1,0],[0x80000000,1],[0x7fffffff,0x7fffffff]])assertBinaryRejected(t,pngBytes({header:pngHeader(...dimensions)}));
 for(const type of ['tEXt','zTXt','iTXt','eXIf','ruSt','PLTE'])assertBinaryRejected(t,pngBytes({before:[pngChunk(type,hiddenImagePayload)]}));
 assertBinaryRejected(t,Buffer.concat([pngSignature,pngChunk(Buffer.from([0xc9,0x48,0x44,0x52]),pngHeader()),pngChunk('IDAT',zlib.deflateSync(Buffer.from([0,255,255,255]))),pngChunk('IEND')]));
 for(const bytes of [pngBytes({before:[pngChunk('IHDR',pngHeader())]}),Buffer.concat([pngSignature,pngChunk('IDAT',zlib.deflateSync(Buffer.from([0,255,255,255]))),pngChunk('IHDR',pngHeader()),pngChunk('IEND')]),Buffer.concat([pngBytes(),hiddenImagePayload]),pngBytes().subarray(0,-1)])assertBinaryRejected(t,bytes);
});
test('legacy public attachment resolution retains JPEG and PDF support',t=>{
 const f=fixture(t);for(const extension of ['jpg','jpeg','pdf']){
  const relPath='legacy-attachment.'+extension,bytes=Buffer.from('Legacy attachment routing is unchanged.');fs.writeFileSync(path.join(f.root,relPath),bytes);
  const record={id:'legacy-case',corpus:'legacy-150',root:f.root,contract:{turns:[{message:'Inspect the supplied file.',attachments:[{relPath}]}]}};
  const input=getPublicTurnInput(record,0);assert.equal(input.attachments[0].path,path.join(f.root,relPath));assert.equal(Object.hasOwn(input,'responseContract'),false);
 }
});
