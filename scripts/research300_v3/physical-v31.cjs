'use strict';
// The original v3 physical comparator remains available for exact first-grade
// replay. These are comparison views, never edits to protected solver states.
const frozen=require('./physical.cjs');
const clone=structuredClone;
const inertControls=m=>['self_weight','rigid_floor','p_delta','rigid_offsets','construction_stage']
 .every(k=>m.analysis_control?.[k]===false);
function defaults(model){
 const m=clone(model);
 for(const row of [m,m.analysis_control,...(m.nodes||[]),...(m.elements||[]),...(m.materials||[]),...(m.sections||[])]){
  if(row?.extra&&typeof row.extra==='object'&&!Array.isArray(row.extra)&&Object.keys(row.extra).length===0)delete row.extra;
 }
 for(const story of m.stories||[])if(Array.isArray(story.floor_loads)&&story.floor_loads.length===0)delete story.floor_loads;
 return m;
}
function physical(actual,expected){
 const a=defaults(actual),b=defaults(expected);
 // These exact SDK defaults also apply when automatic self-weight is active.
 // Removing the explicit default preserves its execution value; any other
 // acceleration or direction remains a physical difference.
 for(const m of [a,b]){
  if(m.analysis_control?.gravity_m_s2===9.80665)delete m.analysis_control.gravity_m_s2;
  if(m.analysis_control?.gravity_direction==='-z')delete m.analysis_control.gravity_direction;
 }
 if([a,b].every(inertControls))for(const [source,target]of [[a,b],[b,a]]){
  const stories=source.stories||[],entities=[...source.nodes,...source.elements],other=[...target.nodes,...target.elements];
  // With no floor loading, diaphragm, mass or automatic stage behavior, a
  // purely geometric native story table is a grouping aid. Actual positions,
  // connectivity, active controls and executed loads are still checked below.
  const known=new Set(['id','name','label','description','height','elevation','rigid_diaphragm']);
  if(stories.length&&!(target.stories||[]).length&&other.every(e=>e.story==null)
   &&stories.every(s=>s.rigid_diaphragm===false&&Number.isFinite(s.height)&&s.height>0&&Number.isFinite(s.elevation)&&Object.keys(s).every(k=>known.has(k)))
   &&entities.every(e=>e.story==null||stories.some(s=>String(s.id)===String(e.story)))){
   source.stories=[];for(const e of entities)delete e.story;
  }
 }
 return frozen.physical(a,b);
}
function staticPhysical(actual,expected){
 const a=clone(actual),b=clone(expected);
 if([a,b].every(m=>inertControls(m)&&(m.stories||[]).every(s=>s.rigid_diaphragm===false)))
  for(const m of [a,b])for(const n of m.nodes)delete n.mass;
 return physical(a,b);
}
module.exports={physical,staticPhysical,defaults};
