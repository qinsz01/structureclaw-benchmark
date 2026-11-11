'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { createHash } = require('node:crypto');
const { normalizeCleanReport } = require('./clean-report.cjs');
const { compareReportQuantities } = require('./requested-quantities.cjs');
const { evaluateResearchTurn } = require('./research300-evaluation.cjs');
const { modelFingerprint, resultFingerprint } = require('./analysis-evidence.cjs');

const tolerance = { absolute: 1e-8, relative: 1e-6 };
const quantities = [
  { id: 'private-displacement', selection: { kind: 'case', id: 'D' }, location: { kind: 'node', id: 'n2' }, component: 'uz', unit: 'm', value: -.001, tolerance },
  { id: 'private-combination', selection: { kind: 'combination', id: 'D' }, location: { kind: 'node', id: 'n2' }, component: 'uz', unit: 'm', value: -.002, tolerance },
  { id: 'private-moment', selection: { kind: 'case', id: 'D' }, location: { kind: 'member', id: 'm1', positionM: 2, side: 'left' }, component: 'M2', unit: 'kN.m', value: -5, tolerance },
];
const normalize = (markdown, requested = quantities) => normalizeCleanReport({ markdown }, requested, [], []);
test('member local and section moment labels never turn nodal or wrong-kind components into a match',()=>{
  const q=quantities[2],check=(label,quantity=q)=>compareReportQuantities(normalize(`| case:D | m1@2:left | ${label} | -5 | kN.m |`,[quantity]),[quantity]).pass;
  for(const label of ['局部 M2','local M2','截面内力 M2','截面内力矩 M2'])assert.equal(check(label),true,label);
  for(const label of ['全局 M2','local M3','截面内力矩 V3','支座 M2'])assert.equal(check(label),false,label);
  const force={...q,component:'V3',unit:'kN'};
  assert.equal(compareReportQuantities(normalize('| case:D | m1@2:left | 截面内力矩 V3 | -5 | kN |',[force]),[force]).pass,false);
});
test('current-turn, global-axis and actual coordinate clauses have a restricted annotation grammar',()=>{
  const q=quantities[0],model={nodes:[{id:'n2',x:8,y:0,z:2.4}]},ctx={currentTurnId:'t2'};
  const check=(component,value='-0.001',context=ctx)=>compareReportQuantities(normalizeCleanReport({markdown:`| case:D | n2 | ${component} | ${value} | m |`},[q],[],[],model,context),[q]).pass;
  for(const label of ['t2: Uz, global Z','Uz, global +Z (t2)','t2 Uz, x=8 m, z=2.4 m','t2 Uz, global +Z; x=8, z=2.4 m','Uz（+Z向上）'])assert.equal(check(label),true,label);
  for(const label of ['t1: Uz, global Z','Uz, global +Z (t1)','t2 Uz, x=9, z=2.4 m','Uz（+Z向右）','Uz（-Z向上）','t2 Uz, x=8','Uz, local Z','Uz, global Z, probably'])assert.equal(check(label),false,label);
  assert.equal(check('t2: Uz, global Z','-0.001',{}),false);
  assert.equal(check('t2: Uz, global Z','+0.001'),false);
});
test('axial sign conventions and constant-length notes validate rather than erase conflicting claims',()=>{
  const q={...quantities[0],location:{kind:'member',id:'bar',positionM:0,side:'right'},component:'N',unit:'kN',value:-30};
  const model={nodes:[{id:'a',x:0,y:0,z:0},{id:'b',x:4,y:0,z:0}],elements:[{id:'bar',nodes:['a','b']}]};
  const check=label=>compareReportQuantities(normalizeCleanReport({markdown:`| case:D | bar@0:right | ${label} | -30 | kN |`},[q],[],[],model,{currentTurnId:'t2'}),[q]).pass;
  for(const label of ['N（拉正）','N（拉为正）','N（拉力为正）','N（拉力为正、压力为负）','N（拉正、压负）','N, tension-positive','N, tension-positive (t2)','N, tension positive (t2)','t2 axial N, positive tension','N, tension; constant over 4 m','N（受压）'])assert.equal(check(label),true,label);
  for(const label of ['N（受拉）','N（拉力）','N（压为正）','N, compression-positive','N, tension; constant over 5 m','N, tension positive (t1)','N, approximate force'])assert.equal(check(label),false,label);
});
test('a selection turn annotation must name the actual current turn and preserve the namespace',()=>{
  const q=quantities[0],context={currentTurnId:'t2'};
  const check=(selection,ctx=context)=>compareReportQuantities(normalizeCleanReport(
    {markdown:`| ${selection} | n2 | Uz | -0.001 | m |`},[q],[],[],undefined,ctx),[q]).pass;
  assert.equal(check('case:D (t2)'),true);
  assert.equal(check('case:D（t2）'),true);
  for(const label of ['case:D (t1)','combination:D (t2)','case:L (t2)','case:D (t2, estimated)'])assert.equal(check(label),false,label);
  assert.equal(check('case:D (t2)',{}),false);
});
test('near-zero notes retain the original signed numeral and cannot hide nonzero values or duplicates',()=>{
  const q={...quantities[0],component:'Fx',unit:'kN',value:0};
  for(const value of ['−7.1×10⁻¹⁴（约0）','+2.13×10⁻¹⁴（约零）','+9.2×10⁻¹⁴（≈0）','−1.8e−13 ≈ 0','+8.8×10⁻¹⁴（数值零）']) {
    const row=`| case:D | n2 | Fx | ${value} | kN |`,r=normalize(row,[q]);
    assert.equal(compareReportQuantities(r,[q]).pass,true,value);
    assert.notEqual(Number(r.markdown.split('|')[5].trim()),0);
    assert.equal(compareReportQuantities(normalize(row+'\n'+row,[q]),[q]).pass,false);
  }
  for(const value of ['30（约0）','30（约零）','0.0001 ≈ 0','0 (estimated)','≈ 0','NaN（数值零）'])assert.equal(compareReportQuantities(normalize(`| case:D | n2 | Fx | ${value} | kN |`,[q]),[q]).pass,false,value);
});
test('reaction equalities, right-hand moment notes and member endpoints retain checked physical meanings',()=>{
  const model={nodes:[{id:'n2',x:0,y:0,z:0},{id:'b',x:4,y:0,z:0}],elements:[{id:'bar',nodes:['n2','b']}]};
  const check=(q,label)=>compareReportQuantities(normalizeCleanReport({markdown:`| case:D | ${q.location.kind==='node'?'n2':'bar@0:right'} | ${label} | -30 | ${q.unit} |`},[q],[],[],model),[q]).pass;
  const f={...quantities[0],component:'Fz',unit:'kN',value:-30};
  for(const label of ['Rz（Fz）','Rz (=Fz)','Rz (= global Fz reaction)','Rz (=Fz reaction)','Rz（Fz，竖向支座反力）','Rz / Fz（+Z为正）','Rz=Fz','Rz＝Fz','Rz（Fz，支座反力）','Rz (=Fz), support reaction','Fz (Rz)','支座 Fz（Rz）','全局支座 Fz（Rz）'])assert.equal(check(f,label),true,label);
  for(const label of ['Rz（Fx）','Rx / Fz','Rz (= global Fx reaction)','Rz / Fz（-Z为正）'])assert.equal(check(f,label),false,label);
  const m={...f,component:'My',unit:'kN.m'};
  for(const label of ['global My','global My reaction','全局支座反力矩 My（右手绕+Y为正）','全局 My（支座反力矩）','global My, support reaction','global support My','全局支反力矩 My','My（绕全局Y）'])assert.equal(check(m,label),true,label);
  for(const label of ['全局支座反力矩 My（右手绕+Z为正）','local My'])assert.equal(check(m,label),false,label);
  assert.equal(check(m,'My（支座反力）'),false);
  assert.equal(check(f,'Rz（Fx，支座反力）'),false);
  assert.equal(check(f,'Fz (Rx)'),false);
  assert.equal(check(f,'全局支反力 Rz（Fz）'),true);
  assert.equal(check(f,'Rz＝Fz（支反力）'),true);
  assert.equal(check(m,'My（支反力矩）'),true);
  assert.equal(check(f,'Fz（支反力矩）'),false);
  assert.equal(check(m,'My（支反力）'),false);
  assert.equal(check(f,'Rz＝Fx（支反力）'),false);
  const n={...f,component:'N',location:{kind:'member',id:'bar',positionM:0,side:'right'}};
  assert.equal(check(n,'N（局部 x，n2→b）'),true);
  assert.equal(check(n,'N（沿 n2→b）'),true);
  assert.equal(check(n,'N（沿 b→n2）'),false);
  assert.equal(check(n,'N（局部 x，b→n2）'),false);
});
test('redundant global direction and measured node annotations retain exact selectors',()=>{
  const model={nodes:[{id:'n2',x:3,y:0,z:0}]},q=quantities[0];
  for(const [location,component] of [['n2','Uz（全局 +Z 为正）'],['n2','uz, global Z'],['n2 (x=3 m)','Uz, global +Z'],['n2（x=3000 mm）','uz(global +Z)']]) {
    const r=normalizeCleanReport({markdown:`| case:D | ${location} | ${component} | −0.001 | m |`},[q],[],[],model);
    assert.equal(compareReportQuantities(r,[q]).pass,true);
  }
  const reaction={...q,component:'Fz',unit:'kN',value:69};
  assert.equal(compareReportQuantities(normalizeCleanReport({markdown:'| case:D | n2 | Rz（全局 +Z 为正） | +69 | kN |'},[reaction],[],[],model),[reaction]).pass,true);
  const moment={...q,component:'My',unit:'kN.m',value:-30};
  assert.equal(compareReportQuantities(normalizeCleanReport({markdown:'| case:D | n2 (x=3 m) | Reaction My, global +Y | -30 | kN.m |'},[moment],[],[],model),[moment]).pass,true);
});
test('decorations cannot hide contradictory axes, coordinates, units or arbitrary prose',()=>{
  const model={nodes:[{id:'n2',x:3,y:0,z:0}]},q=quantities[0];
  for(const [location,component] of [['n2','uz（全局 +X 为正）'],['n2','uz（全局 -Z 为正）'],['n2 (x=4 m)','uz'],['n2 (z=3 m)','uz'],['n2 (x=3000 m)','uz'],['n2 (x=3)','uz'],['n2','probably uz'],['n2','uz(local +Z)'],['n2','Reaction uz, global +Z']]) {
    const r=normalizeCleanReport({markdown:`| case:D | ${location} | ${component} | -0.001 | m |`},[q],[],[],model);
    assert.equal(compareReportQuantities(r,[q]).pass,false,location+' '+component);
  }
  const row='| case:D | n2 | uz(global +Z) | -0.001 | m |';
  assert.equal(compareReportQuantities(normalizeCleanReport({markdown:row+'\n'+row},[q],[],[],model),[q]).pass,false);
});
test('natural coordinate, support, midpoint and component notes require physical proof',()=>{
  const nodes=[-2,0,4,8].map((x,i)=>({id:`n${i}`,x,y:0,z:0,restraints:[false,true,i===1||i===3,true,false,true]}));
  const model={coordinate_system:{dimension:'2d'},nodes,elements:[0,1,2].map(i=>({id:`b${i}`,type:'beam',nodes:[`n${i}`,`n${i+1}`]}))};
  const q=quantities[0];
  const check=(location,component='Uz（全局Z位移）',wanted=q)=>compareReportQuantities(normalizeCleanReport(
    {markdown:`| case:D | ${location} | ${component} | -0.001 | ${wanted.unit} |`},[wanted],[],[],model),[wanted]).pass;
  for(const loc of ['n2（x=4 m，支承跨中）','n2（跨中，x=4000 mm）'])assert.equal(check(loc),true,loc);
  for(const loc of ['n2（x=4 m，左支座）','n2（跨中，x=3 m）','n2（x=4 m，右自由端）','n2（x=4 m，probably）'])assert.equal(check(loc),false,loc);
  for(const component of ['Uz（全局X位移）','Uz（全局Z支反力）','Uz（全局-Z位移）'])assert.equal(check('n2',component),false,component);
  const force={...q,location:{kind:'node',id:'n1'},component:'Fz',unit:'kN'};
  assert.equal(check('n1（左支座，x=0）','Rz（全局Z支反力）',force),true);
  assert.equal(check('n1（右支座，x=0）','Rz（全局Z支反力）',force),false);
  const free={...q,location:{kind:'node',id:'n0'}};
  assert.equal(check('n0（x=−2 m，左自由端）',undefined,free),true);
  assert.equal(check('n0（x=−2 m，右自由端）',undefined,free),false);
  const moment={...force,component:'My',unit:'kN.m'};
  assert.equal(check('n1','reaction My, about global +Y',moment),true);
  assert.equal(check('n1','reaction My, about global +Z',moment),false);
});
test('support moment labels and free-end notes require the matching actual quantity and topology',()=>{
  const model={coordinate_system:{dimension:'2d'},nodes:[{id:'n2',x:3,y:0,z:0,restraints:[false,true,false,true,false,true]}],elements:[{id:'m1',type:'beam',nodes:['n1','n2']}]};
  const displacement=quantities[0];
  assert.equal(compareReportQuantities(normalizeCleanReport({markdown:'| case:D | n2（x=3 m，自由端） | Uz | -0.001 | m |'},[displacement],[],[],model),[displacement]).pass,true);
  for(const change of [m=>m.nodes[0].restraints[2]=true,m=>m.elements.push({id:'m2',type:'beam',nodes:['n2','n3']})]) {
    const bad=structuredClone(model);change(bad);
    assert.equal(compareReportQuantities(normalizeCleanReport({markdown:'| case:D | n2（x=3 m，自由端） | Uz | -0.001 | m |'},[displacement],[],[],bad),[displacement]).pass,false);
  }
  const moment={...displacement,component:'My',unit:'kN.m',value:-30};
  for(const component of ['support My','Support reaction My, global +Y','My（支座反力矩，全局 Y）'])
    assert.equal(compareReportQuantities(normalizeCleanReport({markdown:`| case:D | n2 | ${component} | -30 | kN.m |`},[moment],[],[],model),[moment]).pass,true);
  assert.equal(compareReportQuantities(normalizeCleanReport({markdown:'| case:D | n2 | support uz | -0.001 | m |'},[displacement],[],[],model),[displacement]).pass,false);
});
test('explicit historical tables exclude only rows verified against captured prior answers',()=>{
  const current='| case:D | n2 | uz | -0.001 | m |',old='| case:D | n2 | uz | -0.002 | m |',context={priorTurnIds:['t1'],priorAssistantMessages:[old]};
  const heading='\n\n**Historical only — turn t1, 8 m span:**\n\n| selection | location | component | value | unit |\n| --- | --- | --- | --- | --- |\n';
  const report=normalizeCleanReport({markdown:current+heading+old},[quantities[0]],[],[],undefined,context);
  assert.equal(compareReportQuantities(report,[quantities[0]]).pass,true);
  assert.match(report.markdown,/Verified captured historical row/);
  for(const [markdown,ctx] of [
    [current+heading+old.replace('-0.002','-0.003'),context],
    [current+heading.replace('t1','t2')+old,context],
    [current+heading+old,{...context,priorAssistantMessages:[]}],
    [current+'\n'+old,context],
    [current+heading+old+'\n\n'+current,context],
    [heading+old,context],
  ]) assert.equal(compareReportQuantities(normalizeCleanReport({markdown},[quantities[0]],[],[],undefined,ctx),[quantities[0]]).pass,false);
});
test('a historical row must belong to the specifically named captured turn',()=>{
  const current='| case:D | n2 | uz | -0.001 | m |',old1='| case:D | n2 | uz | -0.002 | m |',old2='| case:D | n2 | uz | -0.003 | m |';
  const context={priorTurnIds:['t1','t2'],priorResponsesByTurn:{t1:[old1],t2:[old2]},priorAssistantMessages:[old1,old2]};
  for(const [heading,pass] of [['Historical t1',false],['Historical t2',true]]) {
    const r=normalizeCleanReport({markdown:current+'\n\n'+heading+'\n\n'+old2},[quantities[0]],[],[],undefined,context);
    assert.equal(compareReportQuantities(r,[quantities[0]]).pass,pass);
  }
  delete context.priorResponsesByTurn;
  assert.equal(compareReportQuantities(normalizeCleanReport({markdown:current+'\n\nHistorical t1\n\n'+old2},[quantities[0]],[],[],undefined,context),[quantities[0]]).pass,false);
});
test('report node and case aliases require a verified unique physical mapping and preserve namespaces',()=>{
  const q=quantities[0],model={nodes:[{id:'midpoint',x:3,y:0,z:0}]};
  const context={physicalMappingVerified:true,nodeAliases:{n2:'midpoint'},publicNodeIds:['n2'],caseAliases:{D:'dead1'},publicCaseIds:['D'],combinationAliases:{D:'uls1'},publicCombinationIds:['D']};
  for(const line of ['| case:dead1 | midpoint | Uz | -0.001 | m |','| case:D | midpoint (x=3 m) | uz | -0.001 | m |','| private-displacement | case:dead1 | midpoint | uz | -0.001 | m |']) {
    assert.equal(compareReportQuantities(normalizeCleanReport({markdown:line},[q],[],[],model,context),[q]).pass,true);
  }
  for(const [line,ctx] of [
    ['| combination:dead1 | midpoint | uz | -0.001 | m |',context],
    ['| case:dead1 | midpoint | uz | 0.001 | m |',context],
    ['| case:dead1 | midpoint | uz | -0.001 | mm |',context],
    ['| case:dead1 | midpoint (x=4 m) | uz | -0.001 | m |',context],
    ['| case:dead1 | midpoint | uz | -0.001 | m |',{...context,physicalMappingVerified:false}],
    ['| case:D | n1 | uz | -0.001 | m |',{...context,nodeAliases:{n2:'n1'},publicNodeIds:['n1','n2']}],
  ])assert.equal(compareReportQuantities(normalizeCleanReport({markdown:line},[q],[],[],model,ctx),[q]).pass,false);
  const q2={...q,id:'another',location:{kind:'node',id:'n3'}};
  assert.throws(()=>normalizeCleanReport({markdown:'| case:D | midpoint | uz | -0.001 | m |'},[q,q2],[],[],model,{...context,nodeAliases:{n2:'midpoint',n3:'midpoint'}}),/Ambiguous/);
});

test('Unicode signs and superscript scientific notation retain the submitted signed value',()=>{
  for(const value of ['−0.001','−1×10⁻³','−1 × 10^-3','-1e-3']) {
    for(const id of ['', 'private-displacement | ']) {
      const report=normalize(`| ${id}case:D | n2 | uz | ${value} | m |`,[quantities[0]]);
      assert.equal(compareReportQuantities(report,[quantities[0]]).pass,true,value);
    }
  }
});
test('typographic normalization cannot repair wrong magnitudes, signs, units, selectors or duplicates',()=>{
  for(const [value,unit,selection] of [['+1×10⁻³','m','case:D'],['−2×10⁻³','m','case:D'],
    ['−1×10⁻³','mm','case:D'],['−1×10⁻³','m','combination:D'],['−1×10⁻⁺³','m','case:D'],['−1×10^999','m','case:D'],['1-2','m','case:D']]) {
    assert.equal(compareReportQuantities(normalize(`| ${selection} | n2 | uz | ${value} | ${unit} |`,[quantities[0]]),[quantities[0]]).pass,false);
  }
  const row='| case:D | n2 | uz | −1×10⁻³ | m |';
  assert.equal(compareReportQuantities(normalize(row+'\n'+row,[quantities[0]]),[quantities[0]]).pass,false);
});
test('public Rx/Ry/Rz support force names are unambiguous only with node selectors and force units',()=>{
  for(const axis of ['x','y','z']) {
    const q={...quantities[0],component:'F'+axis,unit:'kN',value:69};
    for(const id of ['',q.id+' | '])assert.equal(compareReportQuantities(normalize(`| ${id}case:D | n2 | R${axis} | +69 | kN |`,[q]),[q]).pass,true);
    for(const [component,unit] of [['R'+axis,'rad'],['R'+axis,'m'],['R'+(axis==='z'?'x':'z'),'kN']])
      assert.equal(compareReportQuantities(normalize(`| case:D | n2 | ${component} | +69 | ${unit} |`,[q]),[q]).pass,false);
    const member={...q,location:{kind:'member',id:'m1',positionM:2,side:'left'}};
    assert.equal(compareReportQuantities(normalize(`| case:D | m1@2:left | R${axis} | +69 | kN |`,[member]),[member]).pass,false);
  }
});

test('five-column results bind exact public selectors without requiring private quantity IDs', () => {
  const original = { markdown: '| selection | location | component | value | unit |\n| --- | --- | --- | --- | --- |\n'
    + '| case:D | n2 | Uz | -0.001 | m |\n| combination:D | n2 | UZ | -0.002 | m |\n| case:D | m1@2.0:left | m2 | -5 | kN.m |',
    title: 'Current results' };
  const result = normalizeCleanReport(original, quantities, [], []);
  assert.equal(compareReportQuantities(result, quantities).pass, true);
  assert.match(result.markdown, /\| private-moment \| case:D \| m1@2:left \| M2 \| -5 \| kN\.m \|/);
  assert.equal(original.markdown.includes('private-displacement'), false);
  assert.equal(result.title, 'Current results');
});

test('human labels in six-column rows use selectors while explicit known IDs keep strict spelling', () => {
  const alias = '| Midspan displacement | case:D | n2 | UZ | -0.001 | m |';
  assert.equal(compareReportQuantities(normalize(alias, [quantities[0]]), [quantities[0]]).pass, true);
  const explicit = '| private-displacement | case:D | n2 | UZ | -0.001 | m |';
  assert.equal(normalize(explicit, [quantities[0]]).markdown, explicit);
  assert.equal(compareReportQuantities(normalize(explicit, [quantities[0]]), [quantities[0]]).pass, false);
});

test('normalization never reads expected response values or tolerances to identify rows', () => {
  const selectors = quantities.map(q => {
    const row = { id: q.id, selection: q.selection, location: q.location, component: q.component };
    Object.defineProperty(row, 'value', { get() { throw new Error('Expected value accessed'); } });
    Object.defineProperty(row, 'tolerance', { get() { throw new Error('Tolerance accessed'); } });
    return row;
  });
  const result = normalize('| case:D | n2 | uz | 987654 | m |', selectors);
  assert.match(result.markdown, /\| private-displacement \| case:D \| n2 \| uz \| 987654 \| m \|/);
});

test('ambiguous public selectors are rejected independently of the submitted value', () => {
  const sameSelector = { ...quantities[0], id: 'another-private-id', value: -999 };
  assert.throws(() => normalize('| case:D | n2 | uz | -0.001 | m |', [quantities[0], sameSelector]), /ambiguous/i);
});

test('duplicate and conflicting rows survive normalization and fail the existing comparator', () => {
  for (const second of ['| case:D | n2 | uz | -0.001 | m |', '| Alias | case:D | n2 | uz | 0.001 | m |',
    '| private-displacement | case:D | n2 | uz | -0.001 | m |']) {
    const result = normalize('| case:D | n2 | uz | -0.001 | m |\n' + second, [quantities[0]]);
    assert.equal(result.markdown.split('\n').length, 2);
    assert.equal(compareReportQuantities(result, [quantities[0]]).pass, false);
  }
});

for (const [name, markdown, requested] of [
  ['wrong case kind', '| combination:D | n2 | uz | -0.001 | m |', quantities[0]],
  ['wrong case ID', '| case:d | n2 | uz | -0.001 | m |', quantities[0]],
  ['wrong unit', '| case:D | n2 | uz | -0.001 | mm |', quantities[0]],
  ['missing unit', '| case:D | n2 | uz | -0.001 | |', quantities[0]],
  ['wrong sign', '| case:D | n2 | uz | 0.001 | m |', quantities[0]],
  ['missing numeric value', '| case:D | n2 | uz | | m |', quantities[0]],
  ['nonfinite numeric value', '| case:D | n2 | uz | Infinity | m |', quantities[0]],
  ['wrong member station', '| case:D | m1@2.000000001:left | M2 | -5 | kN.m |', quantities[2]],
  ['wrong discontinuity side', '| case:D | m1@2:right | M2 | -5 | kN.m |', quantities[2]],
  ['missing member station', '| case:D | m1 | M2 | -5 | kN.m |', quantities[2]],
]) test(`clean normalization cannot repair ${name}`, () => {
  assert.equal(compareReportQuantities(normalize(markdown, [requested]), [requested]).pass, false);
});

test('a single required derived result permits an omitted or descriptive ID without filling any fields', () => {
  const definitions = [{ id: 'intermediate-sum' }, { id: 'private-envelope' }];
  for (const id of [undefined, 'maximum absolute deflection']) {
    const row = { value: -.001, unit: 'm', governingOperand: 'n2', governingSelection: { kind: 'case', id: 'D' }, ...(id ? { id } : {}) };
    const input = { markdown: '', derivedQuantities: [row] };
    const result = normalizeCleanReport(input, quantities, definitions, ['private-envelope']);
    assert.deepEqual(result.derivedQuantities, [{ ...row, id: 'private-envelope' }]);
    assert.equal(input.derivedQuantities[0], row);
    assert.equal(row.id, id);
  }
});

test('derived ID aliases cannot resolve multiple required definitions or multiple submitted rows', () => {
  const row = { value: -.001, unit: 'm', governingOperand: 'n2', governingSelection: { kind: 'case', id: 'D' } };
  const definitions = [{ id: 'first', value: -.001 }, { id: 'second', value: 999 }];
  assert.throws(() => normalizeCleanReport({ derivedQuantities: [row] }, quantities, definitions, ['first', 'second']), /ambiguous|explicit|derived.*id/i);
  assert.throws(() => normalizeCleanReport({ derivedQuantities: [row, { ...row, value: 999 }] }, quantities, definitions, ['first']), /ambiguous|explicit|derived.*id/i);
  const known = { ...row, id: 'second' };
  assert.deepEqual(normalizeCleanReport({ derivedQuantities: [known] }, quantities, definitions, ['first']).derivedQuantities, [known]);
});

test('derived reports retain duplicate explicit IDs and require supplied unit and governing fields', () => {
  const row = { id: 'total', value: -2, unit: 'kN', governingOperand: null, governingSelection: null };
  const result = normalizeCleanReport({ derivedQuantities: [row, { ...row, value: 2 }] }, [], [{ id: 'total' }], ['total']);
  assert.equal(result.derivedQuantities.length, 2);
  assert.deepEqual(result.derivedQuantities.map(r => r.value), [-2, 2]);
  for (const key of ['unit', 'governingOperand', 'governingSelection']) {
    const missing = { ...row }; delete missing[key];
    assert.throws(() => normalizeCleanReport({ derivedQuantities: [missing] }, [], [{ id: 'total' }], ['total']), /unit|governing|field/i);
  }
});

function diagonalDifferences() {
  const qs = ['X0BL', 'X0TR', 'X0TL', 'X0BR'].map((id, index) => ({
    id: `private-force-${index}`, selection: { kind: 'case', id: 'D' },
    location: { kind: 'member', id, positionM: 0, side: 'right' }, component: 'N',
  }));
  const definitions = [
    { id: 'private-diagonal-one', operation: 'difference', operands: ['private-force-0', 'private-force-1'], unit: 'kN' },
    { id: 'private-diagonal-two', operation: 'difference', operands: ['private-force-2', 'private-force-3'], unit: 'kN' },
  ];
  const rows = [
    { operation: 'difference', operands: ['X0BL', 'X0TR'], value: -17, unit: 'kN', governingOperand: null, governingSelection: null },
    { operation: 'difference', operands: ['X0TL', 'X0BR'], value: 23, unit: 'kN', governingOperand: null, governingSelection: null },
  ];
  return { qs, definitions, rows, required: ['private-diagonal-one', 'private-diagonal-two'] };
}

test('MM036 diagonal differences identify both derived results from public member operands without hidden IDs', () => {
  const f = diagonalDifferences();
  for (const definition of [...f.qs, ...f.definitions]) {
    Object.defineProperty(definition, 'value', { get() { throw new Error('Expected value accessed'); } });
  }
  const report = { derivedQuantities: f.rows };
  const result = normalizeCleanReport(report, f.qs, f.definitions, f.required);
  assert.deepEqual(result.derivedQuantities.map(({ id, value, operands }) => ({ id, value, operands })), [
    { id: 'private-diagonal-one', value: -17, operands: ['X0BL', 'X0TR'] },
    { id: 'private-diagonal-two', value: 23, operands: ['X0TL', 'X0BR'] },
  ]);
  assert.equal(f.rows[0].id, undefined);
});

test('derived semantic operands retain difference order and cannot fall back around a wrong selector', () => {
  for (const operands of [['X0TR', 'X0BL'], ['X0BL', 'X0BR'], ['X0BL', 'missing-member']]) {
    const f = diagonalDifferences();
    f.rows[0].operands = operands;
    assert.throws(() => normalizeCleanReport({ derivedQuantities: [f.rows[0]] }, f.qs, f.definitions, ['private-diagonal-one']), /operand|selector|definition/i);
  }
  const f = diagonalDifferences();
  f.rows[0].id = 'private-diagonal-two';
  assert.throws(() => normalizeCleanReport({ derivedQuantities: f.rows }, f.qs, f.definitions, f.required), /id|selector|definition/i);
});

test('full operand selectors distinguish public case, component and exact member station', () => {
  const f = diagonalDifferences();
  const selector = q => ({ selection: { ...q.selection }, location: { ...q.location }, component: q.component });
  f.rows[0].operands = f.qs.slice(0, 2).map(selector);
  assert.equal(normalizeCleanReport({ derivedQuantities: f.rows }, f.qs, f.definitions, f.required).derivedQuantities[0].id, 'private-diagonal-one');
  for (const change of [operand => operand.selection.kind = 'combination', operand => operand.selection.id = 'L',
    operand => operand.component = 'M2', operand => operand.location.positionM = 1e-9,
    operand => operand.location.side = 'left']) {
    const rows = structuredClone(f.rows);
    change(rows[0].operands[0]);
    assert.throws(() => normalizeCleanReport({ derivedQuantities: rows }, f.qs, f.definitions, f.required), /operand|selector/i);
  }
});

test('ambiguous bare member operands require full selectors and ambiguous definitions never use values to choose', () => {
  const f = diagonalDifferences();
  f.qs.push({ ...f.qs[0], id: 'private-other-case', selection: { kind: 'combination', id: 'D' } });
  assert.throws(() => normalizeCleanReport({ derivedQuantities: f.rows }, f.qs, f.definitions, f.required), /ambiguous.*operand/i);
  f.rows[0].operands[0] = { selection: f.qs[0].selection, location: f.qs[0].location, component: 'N' };
  assert.equal(normalizeCleanReport({ derivedQuantities: f.rows }, f.qs, f.definitions, f.required).derivedQuantities[0].id, 'private-diagonal-one');
  f.definitions.push({ ...f.definitions[0], id: 'private-duplicate-definition', value: -999 });
  f.required.push('private-duplicate-definition');
  assert.throws(() => normalizeCleanReport({ derivedQuantities: f.rows }, f.qs, f.definitions, f.required), /ambiguous.*derived|ambiguous.*definition/i);
});

test('a derived semantic selector must supply both operation and operands', () => {
  const f = diagonalDifferences();
  for (const key of ['operation', 'operands']) {
    const row = { ...f.rows[0] }; delete row[key];
    assert.throws(() => normalizeCleanReport({ derivedQuantities: [row] }, f.qs, f.definitions, ['private-diagonal-one']), /operation|operand|selector/i);
  }
});

test('commutative derived selectors preserve operand multiplicity while difference order remains explicit', () => {
  const f = diagonalDifferences();
  for (const row of f.rows) { row.operation = 'sum'; row.operands.reverse(); }
  for (const definition of f.definitions) definition.operation = 'sum';
  assert.deepEqual(normalizeCleanReport({ derivedQuantities: f.rows }, f.qs, f.definitions, f.required).derivedQuantities.map(row => row.id), f.required);
  f.rows[0].operands = ['X0BL', 'X0BL'];
  assert.throws(() => normalizeCleanReport({ derivedQuantities: f.rows }, f.qs, f.definitions, f.required), /operand|selector|definition/i);
});

function evaluatedFixture() {
  const expectedModel = structuredClone(require('../fixtures/ground-truth-models.json').find(m => m.id === 'beam-simple-6m').model);
  const selection = { kind: 'case', id: expectedModel.load_cases[0].id };
  const key = `case:${selection.id}`;
  const quantity = { id: 'private-deflection', selection, location: { kind: 'node', id: expectedModel.nodes[1].id }, component: 'uz', unit: 'm', value: -.001, tolerance };
  const digest = bytes => createHash('sha256').update(bytes).digest('hex');
  const sourceHash = digest('frozen clean normalization fixture');
  const input = Buffer.from('bound solver input'), output = Buffer.from('bound native solver output');
  const data = { displacements: { [quantity.location.id]: { uz: quantity.value } }, execution: { executed: true,
    solver: 'OpenSees', solverVersion: '3.7.1', analysisReturnCode: 0,
    artifacts: { normalizedInputSha256: digest(input), solverResponseSha256: digest(output) } } };
  const report = { markdown: `| ${key} | ${quantity.location.id} | UZ | -0.001 | m |` };
  const state = { model: structuredClone(expectedModel), messages: [], report, analysisResult: { results: {
    [key]: { selection, status: 'success', meta: { engineId: 'builtin-opensees', state: 1, sourceHash,
      modelHash: modelFingerprint(expectedModel), runId: 'run-1' }, data },
  } } };
  const evidence = { sourceHash, inputBinding: { inputEdition: 'current' },
    referenceEvidence: { engineId: 'opensees', state: 1, sourceHash, modelHash: modelFingerprint(expectedModel), status: 'validated' },
    turnEvidence: { turnId: 't1', state: 1, messageStartIndex: 0, analysisRunIds: ['run-1'], reportHash: resultFingerprint(report) },
    artifactEvidence: { 'run-1': { selection, modelHash: modelFingerprint(expectedModel), resultHash: resultFingerprint(data),
      artifactBytes: { normalizedInput: input, solverResponse: output } } } };
  const { value, ...request } = quantity;
  const caseRecord = { id: 'MM-test', models: [expectedModel], referenceRequests: { states: [{ state: 1, quantities: [request], derived: [] }] },
    reference: { toleranceFrozenBeforeCandidate: true, states: [{ state: 1, quantities: [quantity] }] },
    contract: { evaluationProfile: 'engineering-v2.3', plannedEngine: 'opensees', modelStates: ['model-state-1.json'],
      turns: [{ id: 't1', state: 1, expectation: 'analyze' }],
      requiredOutputs: [{ id: 'deflection-output', state: 1, kind: 'numerical', quantityIds: [quantity.id] }] } };
  return { state, evidence, caseRecord, quantity, selection };
}

test('current public input evaluation accepts the public five-column protocol', () => {
  for (const edition of [undefined, 'frozen', 'concise-v1', 'visual-v2', 'current']) {
    const f = evaluatedFixture();
    f.evidence.inputBinding = edition ? { inputEdition: edition } : undefined;
    const result = evaluateResearchTurn(f);
    assert.equal(result.allPassed, edition === 'current', `${edition}: ${JSON.stringify(result)}`);
    assert.equal(f.state.report.markdown.includes('private-deflection'), false);
  }
});

test('explicit known-ID reports remain valid for all input editions', () => {
  for (const edition of [undefined, 'frozen', 'concise-v1', 'visual-v2', 'current']) {
    const f = evaluatedFixture();
    f.evidence.inputBinding = edition ? { inputEdition: edition } : undefined;
    f.state.report.markdown = `| ${f.quantity.id} | case:${f.selection.id} | ${f.quantity.location.id} | uz | -0.001 | m |`;
    f.evidence.turnEvidence.reportHash = resultFingerprint(f.state.report);
    assert.equal(evaluateResearchTurn(f).allPassed, true, edition);
  }
});

test('clean report normalization preserves execution gates and current-turn report boundaries', () => {
  const f = evaluatedFixture();
  f.evidence.artifactEvidence = {};
  const unbound = evaluateResearchTurn(f);
  assert.equal(unbound.allPassed, false);
  assert.equal(unbound.metrics.some(metric => metric.metric.startsWith('execution:') && !metric.pass), true);
  const historical = evaluatedFixture();
  historical.state.messages = [{ role: 'assistant', content: historical.state.report.markdown }];
  historical.evidence.turnEvidence.messageStartIndex = 1;
  delete historical.evidence.turnEvidence.reportHash;
  assert.equal(evaluateResearchTurn(historical).allPassed, false);
});

test('clean evaluation accepts a single unlabelled derived result with its exact public governor', () => {
  const f = evaluatedFixture();
  f.caseRecord.referenceRequests.states[0].derived = [{ id: 'private-envelope', operation: 'max_abs', operands: [f.quantity.id], unit: 'm' }];
  f.caseRecord.contract.requiredOutputs.push({ id: 'envelope-output', state: 1, kind: 'derived', quantityIds: ['private-envelope'] });
  f.state.report.derivedQuantities = [{ value: -.001, unit: 'm', governingOperand: f.quantity.location.id, governingSelection: f.selection }];
  f.evidence.turnEvidence.reportHash = resultFingerprint(f.state.report);
  assert.equal(evaluateResearchTurn(f).allPassed, true);
  f.state.report.derivedQuantities[0].value = .001;
  f.evidence.turnEvidence.reportHash = resultFingerprint(f.state.report);
  assert.equal(evaluateResearchTurn(f).allPassed, false);
});

test('public table and unlabelled derived JSON work in the current answer without a persisted report', () => {
  const f = evaluatedFixture();
  f.caseRecord.referenceRequests.states[0].derived = [{ id: 'private-envelope', operation: 'max_abs', operands: [f.quantity.id], unit: 'm' }];
  f.caseRecord.contract.requiredOutputs.push({ id: 'envelope-output', state: 1, kind: 'derived', quantityIds: ['private-envelope'] });
  const row = { value: -.001, unit: 'm', governingOperand: f.quantity.location.id, governingSelection: f.selection };
  const answer = () => {
    f.state.messages = [{ role: 'assistant', content: f.state.report.markdown + '\n```json\n' + JSON.stringify({ derivedQuantities: [row] }) + '\n```' }];
  };
  delete f.evidence.turnEvidence.reportHash;
  answer();
  assert.equal(evaluateResearchTurn(f).allPassed, true);
  delete row.value;
  answer();
  assert.equal(evaluateResearchTurn(f).allPassed, false);
  row.value = -.001;
  row.governingSelection = { kind: 'combination', id: f.selection.id };
  answer();
  assert.equal(evaluateResearchTurn(f).allPassed, false);
});

test('multiple derived public operand reports pass full evaluation without private IDs and retain all numerical gates', () => {
  const setup = () => {
    const f = evaluatedFixture();
    const model = f.caseRecord.models[0];
    const extra = [model.nodes[0], model.nodes[2]].map((node, index) => ({ ...f.quantity, id: `private-support-${index}`,
      location: { kind: 'node', id: node.id }, value: 0 }));
    for (const q of extra) {
      const { value, ...request } = q;
      f.caseRecord.referenceRequests.states[0].quantities.push(request);
      f.caseRecord.reference.states[0].quantities.push(q);
      f.state.analysisResult.results[`case:${f.selection.id}`].data.displacements[q.location.id] = { uz: 0 };
    }
    const definitions = extra.map((q, index) => ({ id: `private-difference-${index}`, operation: 'difference', operands: [f.quantity.id, q.id], unit: 'm' }));
    f.caseRecord.referenceRequests.states[0].derived = definitions;
    f.caseRecord.contract.requiredOutputs.push(...definitions.map(d => ({ id: d.id, state: 1, kind: 'derived', quantityIds: [d.id] })));
    f.state.report.derivedQuantities = extra.map(q => ({ operation: 'difference', operands: [f.quantity.location.id, q.location.id],
      value: -.001, unit: 'm', governingOperand: null, governingSelection: null }));
    f.evidence.artifactEvidence['run-1'].resultHash = resultFingerprint(f.state.analysisResult.results[`case:${f.selection.id}`].data);
    return f;
  };
  const correct = setup();
  correct.evidence.turnEvidence.reportHash = resultFingerprint(correct.state.report);
  assert.equal(evaluateResearchTurn(correct).allPassed, true);
  for (const change of [rows => rows[0].value = .001, rows => rows[0].unit = 'kN', rows => rows[0].operands.reverse(),
    rows => rows[1] = { ...rows[0], value: 999 }]) {
    const f = setup();
    change(f.state.report.derivedQuantities);
    f.evidence.turnEvidence.reportHash = resultFingerprint(f.state.report);
    assert.equal(evaluateResearchTurn(f).allPassed, false);
  }
});

test('ambiguous clean derived aliases fail as candidate reports while execution evidence remains checked', () => {
  const f = evaluatedFixture();
  f.caseRecord.referenceRequests.states[0].derived = ['first-envelope', 'second-envelope'].map(id => ({ id, operation: 'max_abs', operands: [f.quantity.id], unit: 'm' }));
  f.caseRecord.contract.requiredOutputs.push(...['first-envelope', 'second-envelope'].map(id => ({ id, state: 1, kind: 'derived', quantityIds: [id] })));
  f.state.report.derivedQuantities = [{ value: -.001, unit: 'm', governingOperand: f.quantity.location.id, governingSelection: f.selection }];
  f.evidence.turnEvidence.reportHash = resultFingerprint(f.state.report);
  const result = evaluateResearchTurn(f);
  assert.equal(result.status, 'agent_failure');
  assert.equal(result.metrics.find(metric => metric.metric === 'clean_report_format').pass, false);
  assert.equal(result.metrics.find(metric => metric.metric.startsWith('execution:')).pass, true);
});

test('verified unloaded truss N accepts any in-member cut while preserving the reported value and unit',()=>{
  const model={analysis_control:{self_weight:false},nodes:[{id:'a',x:0,y:0,z:0},{id:'b',x:4,y:0,z:0}],elements:[{id:'bar',type:'truss',nodes:['a','b']}],load_cases:[{id:'D',loads:[]}]};
  const q={...quantities[0],location:{kind:'member',id:'bar',positionM:2,side:'left'},component:'N',unit:'kN',value:-30};
  const check=(location,label='轴力 N（受拉为正）',value='-30',unit='kN',m=model,verified=true)=>compareReportQuantities(normalizeCleanReport({markdown:`| case:D | ${location} | ${label} | ${value} | ${unit} |`},[q],[],[],m,{physicalMappingVerified:verified}),[q]).pass;
  for(const label of ['轴力 N（受拉为正）','N（受拉为正）','Axial force, tension positive'])assert.equal(check('bar@0:right',label),true,label);
  assert.equal(check('bar@4:left'),true);
  assert.equal(check('bar@4.1:left'),false);
  assert.equal(check('bar@0:right','N','30'),false);
  assert.equal(check('bar@0:right','N','-30','N'),false);
  assert.equal(check('bar@0:right','N','-30','kN',model,false),false);
  const changed=structuredClone(model);changed.elements[0].type='beam';assert.equal(check('bar@0:right','N','-30','kN',changed),false);
  assert.equal(compareReportQuantities(normalizeCleanReport({markdown:'| case:D | n2 | Uz（全局） | -0.001 | m |'},[quantities[0]],[],[]),[quantities[0]]).pass,true);
});

test('zero equilibrium residual orientation requires a verified geometrical authorization',()=>{
  const qs=['a','b'].map((id,i)=>({...quantities[0],id,location:{kind:'member',id,positionM:0,side:'right'},component:'N',unit:'kN',value:10}));
  const ds=[{id:'balance',operation:'difference',operands:['a','b'],unit:'kN'}];
  const report={markdown:'',derivedQuantities:[{operation:'difference',operands:['b','a'],value:-1e-14,unit:'kN',governingOperand:null,governingSelection:null}]};
  const context={physicalMappingVerified:true,equilibriumDifferenceIds:['balance']};
  const normalized=normalizeCleanReport(report,qs,ds,['balance'],null,context);
  assert.equal(normalized.derivedQuantities[0].id,'balance');assert.equal(normalized.derivedQuantities[0].value,-1e-14);
  for(const ctx of [{},{physicalMappingVerified:false,equilibriumDifferenceIds:['balance']},{physicalMappingVerified:true,equilibriumDifferenceIds:[]}])assert.throws(()=>normalizeCleanReport(report,qs,ds,['balance'],null,ctx),/conflicts/);
});

test('section action labels retain their local component identity',()=>{
  const q=quantities[2];
  for(const component of ['Section M2','Local section M2'])assert.equal(compareReportQuantities(normalize(`| case:D | m1@2:left | ${component} | -5 | kN.m |`,[q]),[q]).pass,true);
  for(const component of ['Global section M2','Section M3','Reaction M2'])assert.equal(compareReportQuantities(normalize(`| case:D | m1@2:left | ${component} | -5 | kN.m |`,[q]),[q]).pass,false);
});

test('section annotations prove endpoint geometry and never turn resisting end actions into cuts',()=>{
  const model={nodes:[{id:'a',x:0,y:0,z:0,restraints:[true,true,true,true,true,true]},{id:'b',x:0,y:0,z:3.3}],elements:[{id:'col',type:'column',nodes:['a','b']}]};
  const q={...quantities[2],location:{kind:'member',id:'col',positionM:0,side:'right'}};
  const check=(component,requested=q)=>compareReportQuantities(normalizeCleanReport({markdown:`| case:D | col@${requested.location.positionM}:${requested.location.side} | ${component} | -5 | kN.m |`},[requested],[],[],model,{physicalMappingVerified:true}),[requested]).pass;
  assert.equal(check('M2 — section immediately above base'),true);
  assert.equal(check('M2（底端截面）'),true);
  assert.equal(check('M2（顶端截面）'),false);
  assert.equal(check('M2（底端抵抗力矩）'),false);
  const upper={...q,location:{...q.location,positionM:3.3,side:'left'}};
  assert.equal(check('M2（顶端截面）',upper),true);assert.equal(check('M2 — section immediately above base',upper),false);
  const floatEnd={...q,location:{...q.location,positionM:3.3000000000000003,side:'left'}};
  assert.equal(compareReportQuantities(normalizeCleanReport({markdown:'| case:D | col@3.3:left | M2 | -5 | kN.m |'},[floatEnd]),[floatEnd]).pass,true);
  assert.equal(compareReportQuantities(normalizeCleanReport({markdown:'| case:D | col@3.300000001:left | M2 | -5 | kN.m |'},[floatEnd]),[floatEnd]).pass,false);
});

test('exact case and combination rows take precedence over proved identity equivalences',()=>{
  const q=quantities.slice(0,2).map(q=>({...q,value:-.001}));
  const context={physicalMappingVerified:true,selectionEquivalences:{'case:D':['combination:D'],'combination:D':['case:D']}};
  const markdown='| case:D | n2 | uz | -.001 | m |\n| combination:D | n2 | uz | -.001 | m |';
  const normalized=normalizeCleanReport({markdown},q,[],[],undefined,context);
  assert.equal(compareReportQuantities(normalized,q).pass,true);
  assert.equal(compareReportQuantities(normalizeCleanReport({markdown:markdown+'\n'+markdown},q,[],[],undefined,context),q).pass,false);
});
test('two constant-axial endpoint rows retain their exact cuts before station equivalence',()=>{
  const model={analysis_control:{self_weight:false},nodes:[{id:'a',x:0,y:0,z:0},{id:'b',x:4,y:0,z:0}],elements:[{id:'bar',type:'truss',nodes:['a','b']}],load_cases:[{id:'D',loads:[]}]};
  const q=[0,4].map((x,i)=>({...quantities[0],id:'N'+i,component:'N',unit:'kN',value:30,location:{kind:'member',id:'bar',positionM:x,side:i?'left':'right'}}));
  const markdown='| case:D | bar@0:right | N | 30 | kN |\n| case:D | bar@4:left | N | 30 | kN |';
  assert.equal(compareReportQuantities(normalizeCleanReport({markdown},q,[],[],model,{physicalMappingVerified:true}),q).pass,true);
  assert.throws(()=>normalizeCleanReport({markdown:'| case:D | bar@2:right | N | 30 | kN |'},q,[],[],model,{physicalMappingVerified:true}),/Ambiguous/);
});
test('constant axial rows prefer a proved rounded endpoint before equivalent other cuts',()=>{
  const length=Math.hypot(6,3.6),model={analysis_control:{self_weight:false},nodes:[{id:'a',x:0,y:0,z:0},{id:'b',x:6,y:0,z:3.6}],elements:[{id:'bar',type:'truss',nodes:['a','b']}],load_cases:[{id:'D',loads:[]}]};
  const q=[0,length].map((x,i)=>({...quantities[0],id:'N'+i,component:'N',unit:'kN',value:30,location:{kind:'member',id:'bar',positionM:x,side:i?'left':'right'}}));
  const row=`| case:D | bar@${length.toPrecision(12)}:left | N | 30 | kN |`,markdown='| case:D | bar@0:right | N | 30 | kN |\n'+row;
  const context={physicalMappingVerified:true};
  assert.equal(compareReportQuantities(normalizeCleanReport({markdown},q,[],[],model,context),q).pass,true);
  assert.equal(compareReportQuantities(normalizeCleanReport({markdown:markdown+'\n'+row},q,[],[],model,context),q).pass,false);
  assert.throws(()=>normalizeCleanReport({markdown:row.replace(length.toPrecision(12),(length-1e-9).toPrecision(12))},q,[],[],model,context),/Ambiguous/);
});
test('axial classification annotations check the displayed sign and exact zero',()=>{
  for(const [label,value,pass] of [['拉',30,true],['压',-30,true],['零力',0,true],['拉',-30,false],['压',30,false],['零力',1,false]]) {
    const q={...quantities[0],component:'N',unit:'kN',value,location:{kind:'member',id:'bar',positionM:0,side:'right'}};
    assert.equal(compareReportQuantities(normalizeCleanReport({markdown:`| case:D | bar@0:right | N（${label}） | ${value} | kN |`},[q]),[q]).pass,pass);
  }
});
test('rounded public endpoint coordinates accept only the exact actual endpoint and side',()=>{
  const length=Math.hypot(10,2),model={nodes:[{id:'a',x:0,y:0,z:0},{id:'b',x:10,y:0,z:2}],elements:[{id:'bar',type:'beam',nodes:['a','b']}]};
  const q={...quantities[2],location:{kind:'member',id:'bar',positionM:10.1980390272,side:'left'}};
  const check=(x,side='left',context={physicalMappingVerified:true})=>compareReportQuantities(normalizeCleanReport({markdown:`| case:D | bar@${x}:${side} | M2 | -5 | kN.m |`},[q],[],[],model,context),[q]).pass;
  assert.equal(check(length),true);assert.equal(check(length-1e-9),false);assert.equal(check(length,'right'),false);assert.equal(check(length,'left',{}),false);
});

test('an actual endpoint printed to fourteen significant digits remains the same proved endpoint',()=>{
  const length=Math.hypot(10,2),model={nodes:[{id:'a',x:0,y:0,z:0},{id:'b',x:10,y:0,z:2}],elements:[{id:'bar',type:'beam',nodes:['a','b']}]};
  const q={...quantities[2],location:{kind:'member',id:'bar',positionM:length,side:'left'}};
  const check=x=>compareReportQuantities(normalizeCleanReport({markdown:`| case:D | bar@${x}:left | M2 | -5 | kN.m |`},[q],[],[],model,{physicalMappingVerified:true}),[q]).pass;
  assert.equal(check(length.toPrecision(14)),true);assert.equal(check((length-1e-9).toPrecision(14)),false);
});

test('an additional unrequested calculation cannot invalidate an otherwise complete primitive table',()=>{
  const report={markdown:'| case:D | n2 | uz | -.001 | m |',derivedQuantities:[{operation:'difference',operands:['right','left'],value:-60,unit:'kN',governingOperand:null,governingSelection:null}]};
  const normalized=normalizeCleanReport(report,[quantities[0]],[],[]);
  assert.equal(compareReportQuantities(normalized,[quantities[0]]).pass,true);
  assert.deepEqual(normalized.derivedQuantities,report.derivedQuantities);
  const definition={id:'required',operation:'sum',operands:[quantities[0].id]};
  assert.throws(()=>normalizeCleanReport(report,[quantities[0]],[definition],['required']),/operand|definition/i);
});


test('local suffix annotations preserve section axes and reject global or different components',()=>{
  const q=quantities[2];
  for(const component of ['M2（局部）','M2 (local)'])assert.equal(compareReportQuantities(normalize(`| case:D | m1@2:left | ${component} | -5 | kN.m |`,[q]),[q]).pass,true);
  for(const component of ['M2（全局）','M3（局部）','M2 (local, reversed)','M2（局部端反力）'])assert.equal(compareReportQuantities(normalize(`| case:D | m1@2:left | ${component} | -5 | kN.m |`,[q]),[q]).pass,false);
});

test('explicit end-action conventions normalize only verified inner endpoints with matching local axes',()=>{
  const model={nodes:[{id:'a',x:0,y:0,z:0},{id:'b',x:0,y:0,z:3}],elements:[{id:'col',type:'column',nodes:['a','b']}]};
  const context={physicalMappingVerified:true,endActionCompatibleMembers:['col']};
  const qs=[0,3].map((x,i)=>({...quantities[2],id:'cut-'+i,value:i?8:5,location:{kind:'member',id:'col',positionM:x,side:i?'left':'right'}}));
  const text='| case:D | col@0:right | M2, lower end action | -5 | kN.m |\n| case:D | col@3:left | M2, upper end action | 8 | kN.m |';
  const check=(markdown=text,c=context)=>normalizeCleanReport({markdown},qs,[],[],model,c);
  assert.equal(compareReportQuantities(check(),qs).pass,true);
  assert.equal(check().conventionNormalizations.length,2);
  assert.equal(compareReportQuantities(check(text,{}),qs).pass,false);
  assert.equal(compareReportQuantities(check(text,{...context,endActionCompatibleMembers:[]}),qs).pass,false);
  for(const bad of [text.replace('lower','upper'),text.replace('@0:right','@1:right'),text.replace('-5','5'),text+'\n'+text,text.replace('lower end action','global end action')])assert.equal(compareReportQuantities(check(bad),qs).pass,false);
  const withCuts=text+'\n| case:D | col@0:right | M2 — internal section | 5 | kN.m |\n| case:D | col@3:left | M2 — internal section | 8 | kN.m |';
  assert.equal(compareReportQuantities(check(withCuts),qs).pass,true);
  const axial=qs.map(q=>({...q,component:'N',unit:'kN',value:-7}));
  const body='N 按求解器局部端部抗力符号报告。\n| case:D | col@0:right | N | 7 | kN |\n| case:D | col@3:left | N | -7 | kN |';
  assert.equal(compareReportQuantities(normalizeCleanReport({markdown:body},axial,[],[],model,context),axial).pass,true);
  assert.equal(compareReportQuantities(normalizeCleanReport({markdown:body.replace('N 按求解器局部端部抗力符号报告。','')},axial,[],[],model,context),axial).pass,false);
});

test('section shear and mixed explicit moment tables retain their stated conventions',()=>{
  const model={nodes:[{id:'a',x:0,y:0,z:0},{id:'b',x:0,y:0,z:3}],elements:[{id:'col',type:'column',nodes:['a','b']}]};
  const context={physicalMappingVerified:true,endActionCompatibleMembers:['col']};
  for(const component of ['N','V2','V3','T','M2','M3']){
    const signs=['V2','V3'].includes(component)?[1,-1]:[-1,1];
    const qs=[0,3].map((x,i)=>({...quantities[2],id:'cut-'+i,component,unit:['N','V2','V3'].includes(component)?'kN':'kN.m',value:signs[i]*5,location:{kind:'member',id:'col',positionM:x,side:i?'left':'right'}}));
    const markdown=qs.map((q,i)=>`| case:D | col@${i?3:0}:${i?'left':'right'} | ${component}, ${i?'upper':'lower'} end action | 5 | ${q.unit} |`).join('\n');
    assert.equal(compareReportQuantities(normalizeCleanReport({markdown},qs,[],[],model,context),qs).pass,true,component);
  }
  const q={...quantities[2],id:'cut',value:5,location:{kind:'member',id:'col',positionM:0,side:'right'}};
  const markdown='Bottom moments use the solver’s **end-resisting-action convention**.\n| case:D | col@0:right | local M2 | -5 | kN.m |\n| case:D | col@0:right | local M2, internal cut | 5 | kN.m |';
  assert.equal(compareReportQuantities(normalizeCleanReport({markdown},[q],[],[],model,context),[q]).pass,true);
  assert.throws(()=>normalizeCleanReport({markdown:markdown.replace('internal cut | 5','internal cut | -5')},[q],[],[],model,context),/conflicts/);
});

test('upper and lower end actions and zero-plus section cuts require consistent geometry and values',()=>{
  const model={nodes:[{id:'a',x:0,y:0,z:0},{id:'b',x:0,y:0,z:3}],elements:[{id:'col',type:'column',nodes:['a','b']}]};
  const context={physicalMappingVerified:true,endActionCompatibleMembers:['col']};
  const qs=[0,3].map((x,i)=>({...quantities[2],id:'cut-'+i,value:i?8:5,location:{kind:'member',id:'col',positionM:x,side:i?'left':'right'}}));
  const markdown='| case:D | col@0:right | M2（下端杆端抗力矩） | -5 | kN.m |\n| case:D | col@3:left | M2（上端杆端抗力矩） | 8 | kN.m |\n| case:D | col@0:right | M2（下端截面内弯矩） | 5 | kN.m |\n| case:D | col@3:left | M2（上端截面内弯矩） | 8 | kN.m |';
  const check=(body,q=qs,c=context)=>compareReportQuantities(normalizeCleanReport({markdown:body},q,[],[],model,c),q).pass;
  assert.equal(check(markdown),true);
  assert.equal(check(markdown,qs,{}),false);
  assert.equal(check(markdown.replaceAll('下端','上端')),false);
  const english='| case:D | col@0:right | M2, end resisting action | -5 | kN.m |\n| case:D | col@0:right | M2, section cut at 0+ | 5 | kN.m |';
  assert.equal(check(english,[qs[0]]),true);
  assert.throws(()=>check(english.replace('0+ | 5','0+ | -5'),[qs[0]]),/conflicts/);
  assert.equal(check(english.replaceAll('@0:right','@3:left'),[qs[1]]),false);
  assert.equal(check(english.replaceAll('@0:right','@0:left'),[{...qs[0],location:{...qs[0].location,side:'left'}}]),false);
  const axial=qs.map(q=>({...q,component:'N',unit:'kN',value:-7}));
  const axialBody='| case:D | col@0:right | N（下端，拉正压负） | -7 | kN |\n| case:D | col@3:left | N（上端，拉正压负） | -7 | kN |';
  assert.equal(check(axialBody,axial),true);
  assert.equal(check(axialBody.replace('下端','上端'),axial),false);
  assert.equal(check(axialBody,axial,{}),false);
});

test('positive upward annotation validates the global Z component',()=>{
  const q=quantities[0];
  assert.equal(compareReportQuantities(normalizeCleanReport({markdown:'| case:D | n2 | Uz（全局+Z向上为正） | -.001 | m |'},[q]),[q]).pass,true);
  for(const c of ['Uz（全局+X向上为正）','Uz（全局+Z向右为正）'])assert.equal(compareReportQuantities(normalizeCleanReport({markdown:`| case:D | n2 | ${c} | -.001 | m |`},[q]),[q]).pass,false);
});
test('a whole-member constant axial annotation requires physical load proof',()=>{
  const q={...quantities[0],component:'N',unit:'kN',value:30,location:{kind:'member',id:'bar',positionM:0,side:'right'}};
  const model={analysis_control:{self_weight:false},nodes:[{id:'a',x:0,y:0,z:0},{id:'b',x:4,y:0,z:0}],elements:[{id:'bar',type:'truss',nodes:['a','b']}],load_cases:[{id:'D',loads:[]}]};
  const markdown='| case:D | bar@0:right | N（受拉，全杆恒定） | 30 | kN |';
  const check=context=>compareReportQuantities(normalizeCleanReport({markdown},[q],[],[],model,context),[q]).pass;
  assert.equal(check({physicalMappingVerified:true}),true);assert.equal(check({}),false);
  model.load_cases[0].loads.push({id:'axial',type:'distributed',element:'bar',wx:1,wy:0,wz:0,reference_frame:'global'});
  assert.equal(check({physicalMappingVerified:true}),false);
});

test('complete requested derived rows keep supplementary named calculations separate and ungraded',()=>{
  const definitions=[{id:'required',operation:'sum',operands:[quantities[0].id]}];
  const row={id:'required',value:-.001,unit:'m',governingOperand:null,governingSelection:null};
  const extra={id:'additional-max',operation:'max_abs',value:42,unit:'m',governingOperand:quantities[0].id,governingSelection:{kind:'case',id:'D'}};
  const report={markdown:'| case:D | n2 | uz | -.001 | m |',derivedQuantities:[row,extra]};
  const result=normalizeCleanReport(report,[quantities[0]],definitions,['required']);
  assert.deepEqual(result.derivedQuantities,[row]);assert.deepEqual(result.unrequestedDerivedQuantities,[extra]);
  assert.equal(compareReportQuantities(result,[quantities[0]]).pass,true);
  assert.throws(()=>normalizeCleanReport({...report,derivedQuantities:[extra]},[quantities[0]],definitions,['required']),/operand|selector/);
  const duplicate=normalizeCleanReport({...report,derivedQuantities:[row,row,extra]},[quantities[0]],definitions,['required']);
  assert.equal(duplicate.derivedQuantities.length,2);
});
