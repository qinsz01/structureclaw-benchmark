/** Physical line-model comparison, independent of solver tags and approved refinement.
 * Refined nodes must be unrestrained degree-two points on exactly one original member.
 * This is deliberately not a generic geometry-similarity score.
 */
const legacy = require('./model-fidelity.cjs');
const AXES = ['x', 'y', 'z'];
const DOFS = ['ux', 'uy', 'uz', 'rx', 'ry', 'rz'];
const FORCE = ['fx', 'fy', 'fz', 'mx', 'my', 'mz'];
const qfields = ['wx', 'wy', 'wz'];
const dot = (a,b) => a.reduce((v,x,i) => v+x*b[i],0);
const sub = (a,b) => a.map((v,i) => v-b[i]);
const scale = (a,b) => a.map(v => v*b);
const cross = (a,b) => [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
const xyz = n => AXES.map(k=>Number(n[k]));
const norm = v => Math.sqrt(dot(v,v));
const unit = v => {const length=norm(v); if (!(length>1e-12)) throw Error('Degenerate member/local axes'); return scale(v,1/length);};
const mapById = rows => new Map((rows||[]).map(r=>[String(r.id),r]));
const clone = value => JSON.parse(JSON.stringify(value));
const meaningful = value => value && (typeof value==='object' ? Object.values(value).some(meaningful) : value!==0);
const LABEL_FIELDS = ['id','name','label','description'];
const inactiveControlPair=(a,b)=>['self_weight','rigid_floor','p_delta','rigid_offsets','construction_stage']
  .every(key=>a.analysis_control?.[key]===false&&b.analysis_control?.[key]===false);
const geometryOnlyStory=s=>s&&s.rigid_diaphragm===false&&Object.keys(s)
  .every(k=>[...LABEL_FIELDS,'height','elevation','rigid_diaphragm'].includes(k));

// A decorative floor outline is redundant only when its edges are covered by
// actual floor beams and every floor node lies on or inside it. This includes
// concave outlines; a bounding rectangle cannot erase a missing frame bay.
function verifiedFloorOutline(polygon,story,model,tolerance) {
  if(!Array.isArray(polygon)||polygon.length<3||polygon.some(p=>!Array.isArray(p)||p.length!==2||p.some(v=>!Number.isFinite(v))))return false;
  const points=polygon.map(p=>p.slice());
  if(norm(sub(points[0],points.at(-1)))<=tolerance)points.pop();
  if(points.length<3||new Set(points.map(p=>JSON.stringify(p))).size!==points.length)return false;
  const nodes=model.nodes.filter(n=>close(n.z,story.elevation+story.height,0,tolerance));
  const edges=points.map((a,i)=>[a,points[(i+1)%points.length]]);
  const orient=(a,b,c)=>(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]);
  for(let i=0;i<edges.length;i++)for(let j=i+2;j<edges.length;j++) {
    if(i===0&&j===edges.length-1)continue;
    const [a,b]=edges[i],[c,d]=edges[j];
    const overlap=[0,1].every(k=>Math.max(Math.min(a[k],b[k]),Math.min(c[k],d[k]))<=Math.min(Math.max(a[k],b[k]),Math.max(c[k],d[k]))+tolerance);
    if(overlap&&orient(a,b,c)*orient(a,b,d)<=0&&orient(c,d,a)*orient(c,d,b)<=0)return false;
  }
  if(Math.abs(edges.reduce((s,[a,b])=>s+a[0]*b[1]-a[1]*b[0],0))<=tolerance*tolerance)return false;
  const parameters=(p,a,b)=>{const d=sub(b,a),v=sub(p,a),l=dot(d,d);return {t:dot(v,d)/l,distance:Math.abs(d[0]*v[1]-d[1]*v[0])/Math.sqrt(l)};};
  for(const [a,b] of edges) {
    if(norm(sub(b,a))<=tolerance||!nodes.some(n=>norm(sub([n.x,n.y],a))<=tolerance))return false;
    const spans=[];
    for(const e of model.elements.filter(e=>e.type==='beam')) {
      const ends=e.nodes.map(id=>nodes.find(n=>n.id===id));if(ends.some(n=>!n))continue;
      const values=ends.map(n=>parameters([n.x,n.y],a,b));
      if(values.every(v=>v.distance<=tolerance))spans.push(values.map(v=>v.t).sort((x,y)=>x-y));
    }
    spans.sort((x,y)=>x[0]-y[0]);let covered=0;
    for(const [start,end] of spans)if(start<=covered+tolerance&&end>=0)covered=Math.max(covered,end);
    if(covered<1-tolerance)return false;
  }
  return nodes.every(n=>{
    const p=[n.x,n.y];
    if(edges.some(([a,b])=>{const v=parameters(p,a,b);return v.distance<=tolerance&&v.t>=-tolerance&&v.t<=1+tolerance;}))return true;
    let inside=false;
    for(const [a,b] of edges)if((a[1]>p[1])!==(b[1]>p[1])&&p[0]<(b[0]-a[0])*(p[1]-a[1])/(b[1]-a[1])+a[0])inside=!inside;
    return inside;
  });
}

function close(a,b,tolerance=1e-8,absolute=1e-9) {
  return typeof a==='number' && Number.isFinite(a) && typeof b==='number' && Number.isFinite(b)
    && Math.abs(a-b)<=Math.max(absolute,Math.abs(b)*tolerance);
}

// Compare both sides: optional candidate properties can change the physics too.
// Null denotes an unset optional field, as in the legacy material-strength inputs.
function physicalValueEqual(actual,expected,tolerance) {
  if(actual==null || expected==null) return actual==null && expected==null;
  if(typeof actual==='number' || typeof expected==='number') return close(actual,expected,tolerance,1e-12);
  if(Array.isArray(actual) || Array.isArray(expected)) return Array.isArray(actual)&&Array.isArray(expected)
    &&actual.length===expected.length&&actual.every((value,i)=>physicalValueEqual(value,expected[i],tolerance));
  if(typeof actual==='object' || typeof expected==='object') return typeof actual==='object'&&typeof expected==='object'
    &&[...new Set([...Object.keys(actual),...Object.keys(expected)])].every(key=>physicalValueEqual(actual[key],expected[key],tolerance));
  return actual===expected;
}

function comparePhysicalFields(actual,expected,ignored,path,tolerance,failures) {
  for(const key of new Set([...Object.keys(actual),...Object.keys(expected)])) {
    if(!ignored.includes(key)&&!physicalValueEqual(actual[key],expected[key],tolerance)) failures.push(`${path}.${key}`);
  }
}

function normalizedPropertyRecord(record,section=false,counterpart,explicit=false,tolerance=1e-6,staticTheory) {
  const result={...record};
  if(section&&explicit&&result.type==='custom'&&result.shape==null&&counterpart?.shape?.kind==='rectangular') {
    const source=result.extra?.sourceShape;
    if(source&&Object.keys(source).every(k=>['kind','B_mm','H_mm'].includes(k))
      &&physicalValueEqual({kind:source.kind,B:source.B_mm,H:source.H_mm},counterpart.shape,tolerance)) {
      result.extra={...result.extra};delete result.extra.sourceShape;
      if(typeof result.extra.representation==='string')delete result.extra.representation;
      result.properties={...result.properties};
      for(const key of ['Asy','Asz'])if(close(result.properties[key],5*result.properties.A/6,1e-12,1e-14))delete result.properties[key];
    }
  }
  if(section&&explicit&&result.type==='custom'&&counterpart?.shape?.kind==='custom'
    &&(result.shape==null||result.shape.kind==='custom'&&Object.keys(result.shape).every(k=>k==='kind'))&&result.extra) {
    const fields=Object.keys(counterpart.shape).filter(k=>!['kind','description'].includes(k));
    if(fields.length&&fields.every(k=>physicalValueEqual(result.extra[k],counterpart.shape[k],tolerance))) {
      result.shape={kind:'custom',...Object.fromEntries(fields.map(k=>[k,result.extra[k]]))};
      result.extra={...result.extra};for(const k of fields)delete result.extra[k];
      // A centered welded H has a centroidal symmetry axis, hence Iyz=0.
      // This annotation is redundant only for the fully matched stated shape.
      if(result.extra.Iyz_m4===0&&counterpart.shape.description==='Welded H with unequal centered flange widths and thicknesses; no fillets'
        &&['total_depth_mm','bottom_flange_width_mm','bottom_flange_thickness_mm','top_flange_width_mm','top_flange_thickness_mm','web_thickness_mm'].every(k=>Number.isFinite(counterpart.shape[k])&&counterpart.shape[k]>0))delete result.extra.Iyz_m4;
      if(typeof result.extra.description==='string')delete result.extra.description;
      const diagnostics=result.extra.section_diagnostics;
      if(Array.isArray(diagnostics)&&diagnostics.length===1&&diagnostics[0]?.code==='SECTION_GEOMETRY_UNVERIFIED'
        &&diagnostics[0]?.severity==='warning'&&Object.keys(diagnostics[0]).every(k=>['code','severity','message'].includes(k))
        &&typeof diagnostics[0].message?.en==='string'&&typeof diagnostics[0].message?.zh==='string')delete result.extra.section_diagnostics;
    }
  }
  if(section&&explicit&&typeof result.shape?.description==='string') {
    result.shape={...result.shape};delete result.shape.description;
  }
  if(section&&explicit&&result.extra?.drawing_geometry_mm&&counterpart?.shape
    &&physicalValueEqual(result.extra.drawing_geometry_mm,counterpart.shape,tolerance)) {
    result.extra={...result.extra};delete result.extra.drawing_geometry_mm;
    if(typeof result.extra.source==='string')delete result.extra.source;
  }
  if(section&&explicit&&result.type==='custom'&&result.shape==null&&result.extra?.geometry_mm
    &&result.extra.drawingType===counterpart?.type&&counterpart?.shape?.kind==='unequal-flange-I'
    &&physicalValueEqual(result.extra.geometry_mm,Object.fromEntries(Object.entries(counterpart.shape).filter(([k])=>!['kind','description'].includes(k))),tolerance)) {
    result.extra={...result.extra};delete result.extra.geometry_mm;delete result.extra.drawingType;
    if(staticTheory==='Euler-Bernoulli'&&result.extra.formulation==='Supplied centroidal uncoupled Euler-Bernoulli A/Iy/Iz/J; no offsets')delete result.extra.formulation;
  }
  for(const key of ['type','category','grade','purpose','standard_steel_name']) if(typeof result[key]==='string') result[key]=result[key].toLowerCase();
  // StructureModelV2 migrates the historical material type to category.
  // Match only its documented aliases; conflicting/unknown values stay errors.
  if(!section&&['steel','concrete','rebar','other'].includes(result.type)) {
    if(result.category!=null&&result.category!==result.type) throw Error('Material category/type conflict');
    result.category=result.type;
    delete result.type;
  }
  if(result.extra&&typeof result.extra==='object'&&!Array.isArray(result.extra)&&Object.keys(result.extra).length===0) delete result.extra;
  if(section) {
    if(['rect','rectangle','rectangular'].includes(result.type)) result.type='rectangular';
    if(['circ','circle','circular'].includes(result.type)) result.type='circular';
  }
  return result;
}

function axesFor(model, element) {
  const nodes=mapById(model.nodes), a=xyz(nodes.get(String(element.nodes[0]))), b=xyz(nodes.get(String(element.nodes[1])));
  const x=unit(sub(b,a));
  let y,z;
  if(model.coordinate_system.dimension==='2d') {y=[0,1,0];z=cross(x,y);}
  else {
    let reference=model.metadata?.elementReferenceVectors?.[element.id];
    if(!reference) reference=Math.abs(x[2])>.9?[1,0,0]:[0,0,1];
    y=unit(cross(unit(reference),x));z=unit(cross(x,y));
  }
  const rotation=element.rotation_angle??0;
  if(typeof rotation!=='number'||!Number.isFinite(rotation)) throw Error('Non-finite section rotation');
  const angle=rotation*Math.PI/180, c=Math.cos(angle), s=Math.sin(angle);
  return [x,y.map((v,i)=>c*v+s*z[i]),z.map((v,i)=>-s*y[i]+c*v)];
}

function globalVector(values,axes,reference) {
  if(reference==='global' || reference===undefined) return values;
  if(reference!=='element-local') throw Error('Unknown load reference_frame');
  return [0,1,2].map(i=>values.reduce((sum,v,j)=>sum+v*axes[j][i],0));
}

function components(load,fields) {
  let values=fields.map((key,i)=>load[key]??(fields===FORCE?load.forces?.[i]:undefined)??0);
  if(!values.every(v=>typeof v==='number' && Number.isFinite(v))) throw Error('Non-finite load component');
  if(load.direction!==undefined || load.axis!==undefined) {
    const direction=String(load.direction??load.axis).replace(/^local-/,'');
    const index=fields===qfields?{x:0,y:1,z:2}[direction]:{x:0,y:1,z:2,fx:0,fy:1,fz:2,mx:3,my:4,mz:5,rx:3,ry:4,rz:5}[direction];
    if(index===undefined) throw Error(`Unknown load direction ${direction}`);
    const aliases=['magnitude','value',...(fields===qfields?['q','w']:[])].filter(k=>load[k]!==undefined);
    const candidates=aliases.map(k=>load[k]);
    if(load[fields[index]]!==undefined) candidates.push(load[fields[index]]);
    if(!candidates.length || candidates.some(v=>!close(v,candidates[0]))) throw Error('Conflicting or missing directional load value');
    values[index]=candidates[0];
  } else if(['magnitude','value','q','w'].some(k=>load[k]!==undefined)) throw Error('Scalar load requires an explicit direction');
  return values;
}

function distributedEndpointValues(load) {
  const hasEndpoints=qfields.some(key=>load[`${key}_start`]!==undefined||load[`${key}_end`]!==undefined);
  if(hasEndpoints&&['direction','axis','magnitude','value','q','w'].some(key=>load[key]!==undefined))
    throw Error('Endpoint intensities cannot be mixed with directional load aliases');
  const start=components(load,qfields),end=start.slice();
  for(const [index,key] of qfields.entries()) {
    const a=load[`${key}_start`],b=load[`${key}_end`];
    if(a===undefined&&b===undefined) continue;
    if(a===undefined||b===undefined||load[key]!==undefined) throw Error(`Specify both ${key}_start and ${key}_end without ${key}`);
    if(![a,b].every(value=>typeof value==='number'&&Number.isFinite(value))) throw Error('Non-finite distributed endpoint intensity');
    start[index]=a;end[index]=b;
  }
  return {start,end,hasEndpoints};
}

function prepareMapping(actual,expected,tolerance) {
  const an=mapById(actual.nodes), en=mapById(expected.nodes);
  const nodeMapping={}, reverseNodes={}, elementSegments={}, segmentMap={}, interiors={};
  for(const n of expected.nodes) {
    const candidates=actual.nodes.filter(a=>norm(sub(xyz(a),xyz(n)))<=tolerance);
    if(candidates.length!==1 || reverseNodes[candidates[0]?.id]) throw Error(`Ambiguous/missing physical node ${n.id}`);
    nodeMapping[n.id]=String(candidates[0].id); reverseNodes[candidates[0].id]=String(n.id);
  }
  const incidence={};
  for(const e of actual.elements) for(const n of e.nodes) (incidence[n]??=[]).push(String(e.id));
  for(const element of actual.elements) {
    const points=element.nodes.map(id=>xyz(an.get(String(id))));
    const candidates=[];
    for(const ref of expected.elements) {
      if(String(ref.type)!==String(element.type)) continue;
      const a=xyz(en.get(String(ref.nodes[0]))), b=xyz(en.get(String(ref.nodes[1]))), delta=sub(b,a), length=norm(delta), x=unit(delta);
      const positions=points.map(p=>dot(sub(p,a),x));
      if(positions.every((v,i)=>v>=-tolerance && v<=length+tolerance && norm(sub(sub(points[i],a),scale(x,v)))<=tolerance))
        candidates.push({ref,positions,length});
    }
    if(candidates.length!==1) throw Error(`Element ${element.id} is not an unambiguous subdivision of one physical member`);
    const {ref,positions,length}=candidates[0];
    const start=Math.max(0,Math.min(...positions)), end=Math.min(length,Math.max(...positions));
    if(end-start<=tolerance) throw Error(`Zero-length segment ${element.id}`);
    const record={id:String(element.id),physicalElementId:String(ref.id),start,end,
      orientation:positions[0]<=positions[1]?'same':'reversed',nodes:element.nodes.map(String),localAxes:axesFor(actual,element)};
    (elementSegments[ref.id]??=[]).push(record); segmentMap[element.id]=record;
    for(let i=0;i<2;i++) if(!reverseNodes[element.nodes[i]]) {
      const node=an.get(String(element.nodes[i]));
      if((node.restraints||[]).some(Boolean) || (incidence[node.id]||[]).length!==2) throw Error(`Refinement node ${node.id} changes support/connectivity`);
      if(node.mass!=null&&node.mass!==0) throw Error(`Refinement node ${node.id} adds mass`);
      // Only the original physical nodes may carry lumped properties. A new
      // degree-two mesh point cannot acquire springs, constraints or other state.
      const extra=[];
      comparePhysicalFields(node,{},[...LABEL_FIELDS,...AXES,'restraints','mass','story'],`refinement node ${node.id}`,0,extra);
      if(extra.length) throw Error(`Refinement node adds physical attributes: ${extra.join(', ')}`);
      if(node.story!=null&&String(node.story)!==String(element.story)) throw Error(`Refinement node ${node.id} changes story assignment`);
      if(interiors[node.id] && interiors[node.id].member!==ref.id) throw Error(`Refinement node ${node.id} joins originally separate members`);
      interiors[node.id]={member:String(ref.id),position:positions[i]};
    }
  }
  for(const node of actual.nodes) if(!reverseNodes[node.id] && !interiors[node.id]) throw Error(`Unexpected disconnected node ${node.id}`);
  for(const ref of expected.elements) {
    const records=(elementSegments[ref.id]||[]).sort((a,b)=>a.start-b.start);
    const length=norm(sub(xyz(en.get(String(ref.nodes[1]))),xyz(en.get(String(ref.nodes[0])))));
    if(!records.length || Math.abs(records[0].start)>tolerance || Math.abs(records.at(-1).end-length)>tolerance) throw Error(`Incomplete member ${ref.id}`);
    for(let i=1;i<records.length;i++) {
      if(Math.abs(records[i].start-records[i-1].end)>tolerance) throw Error(`Gap/overlap in member ${ref.id}`);
      const previous=records[i-1], current=records[i];
      const prevEnd=previous.nodes[previous.orientation==='same'?1:0], nextStart=current.nodes[current.orientation==='same'?0:1];
      if(prevEnd!==nextStart) throw Error(`Disconnected coincident mesh nodes in member ${ref.id}`);
    }
  }
  return {nodeMapping,reverseNodes,elementSegments,segmentMap,interiors};
}

function canonicalCases(model,mapping) {
  const elements=mapById(model.elements), nodes=mapById(model.nodes);
  return (model.load_cases||[]).map(loadCase=>{
    const nodal={}, prescribed={}, point=[], distributed=[];
    function add(target,values,table) {
      const previous=table[target]??values.map(()=>0); table[target]=previous.map((v,i)=>v+values[i]);
    }
    for(const load of legacy.comparableCaseLoads(model,loadCase)) {
      const node=load.node??load.nodeId??load.node_id, eid=load.element??load.elementId??load.element_id;
      const kind=load.type||(node!==undefined?'nodal':'distributed');
      if(['displacement','settlement'].includes(kind)) {
        const target=mapping.reverseNodes[node]; if(!target) throw Error('Prescribed motion on a refinement node changes the model');
        for(const key of DOFS) if(load[key]!==undefined) {
          if(typeof load[key]!=='number'||!Number.isFinite(load[key])) throw Error('Prescribed displacement must be finite');
          prescribed[`${target}.${key}`]=(prescribed[`${target}.${key}`]??0)+load[key];
        }
      } else if(node!==undefined) {
        if(kind!=='nodal') throw Error(`Unsupported nodal load type ${kind}`);
        if(load.reference_frame && load.reference_frame!=='global') throw Error('Nodal forces must be global');
        const values=components(load,FORCE), target=mapping.reverseNodes[node];
        if(target) add(target,values,nodal);
        else {const at=mapping.interiors[node]; if(!at) throw Error('Unknown nodal load target'); point.push({...at,values});}
      } else {
        const e=elements.get(String(eid)), segment=mapping.segmentMap[eid];
        if(!e || !segment) throw Error('Unknown member load target');
        const length=norm(sub(xyz(nodes.get(String(e.nodes[1]))),xyz(nodes.get(String(e.nodes[0])))));
        const axes=axesFor(model,e), position=x=>{
          if(typeof x!=='number' || !Number.isFinite(x) || x<0 || x>length+1e-9) throw Error('Member load position is outside the member');
          return segment.orientation==='same'?segment.start+x:segment.end-x;
        };
        if(kind==='point') {
          const values=components(load,FORCE), at=position(load.position);
          point.push({member:segment.physicalElementId,position:at,values:[
            ...globalVector(values.slice(0,3),axes,load.reference_frame),...globalVector(values.slice(3),axes,load.reference_frame)]});
        } else if(kind==='distributed') {
          let points;
          const variation=load.variation??load.distribution;
          if(load.variation!==undefined&&load.distribution!==undefined&&load.variation!==load.distribution)
            throw Error('Conflicting load variation/distribution');
          const intensities=distributedEndpointValues(load);
          if(variation==='piecewise_linear') {
            if(intensities.hasEndpoints) throw Error('Piecewise points cannot be mixed with endpoint intensities');
            if(!Array.isArray(load.points)||load.points.length<2) throw Error('Invalid piecewise-linear load');
            points=load.points.map(p=>({position:position(p.position*length),values:globalVector(components(p,qfields),axes,load.reference_frame)}));
          } else if(variation===undefined||variation==='uniform'||variation==='linear') {
            if(load.points!==undefined||load.segments!==undefined) throw Error('Unsupported or mixed piecewise distributed load');
            if(variation==='uniform'&&intensities.start.some((value,i)=>value!==intensities.end[i]))
              throw Error('Uniform load has unequal endpoint intensities');
            points=[{position:position(load.start??0),values:globalVector(intensities.start,axes,load.reference_frame)},
              {position:position(load.end??length),values:globalVector(intensities.end,axes,load.reference_frame)}];
          } else throw Error(`Unsupported distribution ${variation}`);
          if(segment.orientation==='reversed') points.reverse();
          for(let i=1;i<points.length;i++) {
            if(points[i].position<=points[i-1].position) throw Error('Distributed load positions are not increasing');
            distributed.push({member:segment.physicalElementId,a:points[i-1].position,b:points[i].position,
              qa:points[i-1].values,qb:points[i].values});
          }
        } else throw Error(`Unsupported member load type ${kind}`);
      }
    }
    const attributes=Object.fromEntries(Object.entries(loadCase).filter(([key])=>![...LABEL_FIELDS,'type','loads'].includes(key)));
    return {id:String(loadCase.id),type:loadCase.type,attributes,nodal,prescribed,point,distributed};
  });
}

function caseEqual(actual,expected,relative,positionTolerance) {
  if(actual.type!==expected.type||!physicalValueEqual(actual.attributes,expected.attributes,relative)) return false;
  const vectorEqual=(a,b)=>a.length===b.length&&a.every((v,i)=>close(v,b[i],relative));
  for(const table of ['nodal','prescribed']) {
    const keys=new Set([...Object.keys(actual[table]),...Object.keys(expected[table])]);
    for(const key of keys) {
      if(table==='prescribed') {if(!close(actual[table][key],expected[table][key],relative)) return false;}
      else if(!vectorEqual(actual[table][key]||Array(6).fill(0),expected[table][key]||Array(6).fill(0))) return false;
    }
  }
  const groupPoints=points=>{
    const result=[];
    for(const p of points) {
      let found=result.find(q=>q.member===p.member&&Math.abs(q.position-p.position)<=positionTolerance);
      if(!found) result.push(found={...p,values:Array(6).fill(0)});
      found.values=found.values.map((v,i)=>v+p.values[i]);
    }
    return result.filter(p=>p.values.some(v=>Math.abs(v)>1e-12));
  };
  const ap=groupPoints(actual.point), ep=groupPoints(expected.point);
  if(ap.length!==ep.length) return false;
  if(ep.some(p=>!ap.some(q=>q.member===p.member&&Math.abs(q.position-p.position)<=positionTolerance&&vectorEqual(q.values,p.values)))) return false;
  const members=new Set([...actual.distributed,...expected.distributed].map(l=>l.member));
  for(const member of members) {
    const all=[...actual.distributed,...expected.distributed].filter(l=>l.member===member);
    const cuts=[...new Set(all.flatMap(l=>[l.a,l.b]))].sort((a,b)=>a-b);
    const value=(rows,x)=>rows.filter(l=>l.member===member&&l.a<x&&l.b>x).reduce((sum,l)=>sum.map((v,i)=>v+l.qa[i]+(l.qb[i]-l.qa[i])*(x-l.a)/(l.b-l.a)),[0,0,0]);
    for(let i=1;i<cuts.length;i++) for(const ratio of [1/3,2/3]) {
      const x=cuts[i-1]+ratio*(cuts[i]-cuts[i-1]);
      if(!vectorEqual(value(actual.distributed,x),value(expected.distributed,x))) return false;
    }
  }
  return true;
}

function compareStoryAttributes(actual,expected,mapping,relative,coordinateTolerance,failures,options={}) {
  const candidates=new Map((expected.stories||[]).map(story=>[String(story.id),new Set()]));
  const redundantActual=new Set(),redundantExpected=new Set();
  const redundant=(entity,model,other)=>{
    if(options.explicitElasticProperties!==true||!inactiveControlPair(model,other))return false;
    const story=model.stories?.find(s=>String(s.id)===String(entity.story));
    if(!geometryOnlyStory(story)||!Number.isFinite(story.height)||story.height<=0||!Number.isFinite(story.elevation))return false;
    const matches=other.stories?.filter(s=>geometryOnlyStory(s)&&close(s.height,story.height,0,coordinateTolerance)&&close(s.elevation,story.elevation,0,coordinateTolerance));
    if(matches?.length!==1)return false;
    const top=story.elevation+story.height,z=id=>model.nodes.find(n=>n.id===id)?.z;
    if(!entity.nodes)return close(entity.z,top,0,coordinateTolerance)
      ||close(entity.z,story.elevation,0,coordinateTolerance)
        &&entity.restraints?.length===6&&entity.restraints.every(value=>value===true);
    const zs=entity.nodes.map(z);
    return entity.type==='beam'?zs.every(v=>close(v,top,0,coordinateTolerance))
      :entity.type==='column'&&close(Math.min(...zs),story.elevation,0,coordinateTolerance)&&close(Math.max(...zs),top,0,coordinateTolerance);
  };
  const collect=(reference,candidate)=>{
    if(reference.story==null) {
      if(candidate.story!=null) {
        if(redundant(candidate,actual,expected))redundantActual.add(candidate);
        else failures.push(`${reference.id}: unexpected story assignment`);
      }
    } else if(candidate.story!=null) candidates.get(String(reference.story))?.add(String(candidate.story));
    else if(redundant(reference,expected,actual))redundantExpected.add(reference);
    else failures.push(`${reference.id}: missing story assignment`);
  };
  const nodes=mapById(actual.nodes),elements=mapById(actual.elements),stories=mapById(actual.stories);
  for(const node of expected.nodes) collect(node,nodes.get(mapping.nodeMapping[node.id]));
  for(const element of expected.elements) for(const segment of mapping.elementSegments[element.id]) collect(element,elements.get(segment.id));
  for(const [id,interior] of Object.entries(mapping.interiors)) {
    const node=nodes.get(id);if(node.story==null)continue;
    const parent=expected.elements.find(e=>e.id===interior.member);
    if(parent.story!=null)collect(parent,node);
    else {
      const incident=actual.elements.filter(e=>e.nodes.includes(id));
      if(incident.length===2&&incident.every(e=>e.story===node.story&&redundant(e,actual,expected)))redundantActual.add(node);
      else failures.push(`refinement node ${id}: unverified story assignment`);
    }
  }
  const assignedStories=(model,ignored)=>new Set([...model.nodes,...model.elements].filter(entity=>entity.story!=null&&!ignored.has(entity)).map(entity=>String(entity.story)));
  const expectedAssigned=assignedStories(expected,redundantExpected),actualAssigned=assignedStories(actual,redundantActual);
  const unassignedExpected=new Set((expected.stories||[]).map(story=>String(story.id)).filter(id=>!expectedAssigned.has(id)));
  const unassignedActual=new Set((actual.stories||[]).map(story=>String(story.id)).filter(id=>!actualAssigned.has(id)));
  if(stories.size!==(expected.stories||[]).length) failures.push('missing/extra stories');
  const used=new Set(),storyMapping={};
  for(const story of expected.stories||[]) {
    if(unassignedExpected.has(String(story.id))) {
      // An unassigned floor record remains physical metadata. Match its geometry,
      // loads and diaphragm declaration without inventing entity assignments.
      const matches=[...stories.values()].filter(candidate=>{
        if(!unassignedActual.has(String(candidate.id))||used.has(String(candidate.id))) return false;
        if(['height','elevation'].some(key=>!(candidate[key]==null&&story[key]==null)
          &&!close(candidate[key],story[key],0,coordinateTolerance))) return false;
        const differences=[];
        comparePhysicalFields(candidate,story,[...LABEL_FIELDS,'height','elevation'],`story ${story.id}`,relative,differences);
        return differences.length===0;
      });
      const match=matches.find(candidate=>String(candidate.id)===String(story.id))||matches[0];
      if(!match) failures.push(`story ${story.id}: physical metadata differs`);
      else {used.add(String(match.id));storyMapping[story.id]=String(match.id);}
      continue;
    }
    const ids=candidates.get(String(story.id)),candidate=ids.size===1?stories.get([...ids][0]):undefined;
    if(!candidate||used.has(String(candidate.id))) {failures.push(`story ${story.id}: missing or inconsistent physical assignment`);continue;}
    used.add(String(candidate.id));storyMapping[story.id]=String(candidate.id);
    // Legacy comparison already maps geometry and equivalent floor/line loads.
    // Diaphragms and any other declared story behavior still require comparison.
    comparePhysicalFields(candidate,story,[...LABEL_FIELDS,'height','elevation','dead_load','live_load','floorLoad','liveLoad',
      'floor_loads','tributaryWidthM','equivalentLineLoad'],`story ${story.id}`,relative,failures);
  }
  return {unassignedExpected,unassignedActual,storyMapping};
}

function comparePhysicalModels(actual,expected,options={}) {
  const tolerance=options.coordinate??options.span??1e-6, relative=options.property??.005, failures=[];
  try {
    for(const [label,model] of [['candidate',actual],['reference',expected]]) {
      const integrity=legacy.inspectModelIntegrity(model), coordinate=legacy.inspectCoordinateContract(model);
      if(!integrity.ok||!coordinate.ok) throw Error(`${label}: ${!integrity.ok?integrity.reason:coordinate.reason}`);
      for(const node of model.nodes) if(node.mass!=null&&(typeof node.mass!=='number'||!Number.isFinite(node.mass)||node.mass<0))
        throw Error(`${label}: node ${node.id} has invalid mass`);
    }
    // Apply aliases on copies for both the legacy property checks and the
    // symmetric checks. Never rewrite the submitted/native model evidence.
    const originals=[actual,expected];
    const properties=(model,counterpart)=>({...model,materials:model.materials.map(r=>normalizedPropertyRecord(r)),
      sections:model.sections.map(r=>normalizedPropertyRecord(r,true,counterpart.sections.find(s=>s.id===r.id),options.explicitElasticProperties===true,relative,options.staticTheory))});
    actual=properties(originals[0],originals[1]);expected=properties(originals[1],originals[0]);
    if(options.explicitElasticProperties===true)for(const m of [actual,expected])m.elements=m.elements.map(e=>{
      const material=m.materials.find(r=>r.id===e.material);
      if(material?.category==='concrete'&&typeof e.concrete_grade==='string'
        &&e.concrete_grade.toLowerCase()===String(material.grade??material.name).toLowerCase()
        &&/^c\d+$/i.test(e.concrete_grade)) {
        const copy={...e};delete copy.concrete_grade;return copy;
      }
      return e;
    });
    if(options.openSeesStaticDefaults===true)for(const m of [actual,expected]) {
      m.analysis_control={...m.analysis_control};
      // Pinned OpenSees _control_evidence records these unset controls as
      // legacy-engine-default false. Never infer self weight or diaphragm.
      for(const k of ['rigid_offsets','construction_stage'])if(m.analysis_control[k]==null)m.analysis_control[k]=false;
      if(m.analysis_control.consideration_torsion==null)m.analysis_control.consideration_torsion=true;
      m.elements=m.elements.map(e=>{
        if(m.coordinate_system.dimension!=='2d'||!e.extra)return e;
        // A reference vector is defined before section roll. The rolled axes
        // are checked independently when comparing the actual member stiffness.
        const extra={...e.extra},axis=axesFor(m,{...e,rotation_angle:0})[1];
        for(const key of ['axis_reference_vector','public_axis_reference_vector']) {
          const vector=extra[key];
          if(Array.isArray(vector)&&vector.length===3&&vector.every((v,i)=>close(v,axis[i],0,1e-12)))delete extra[key];
        }
        const copy={...e};if(Object.keys(extra).length)copy.extra=extra;else delete copy.extra;return copy;
      });
    }
    if(options.explicitElasticProperties===true) {
      for(const m of [actual,expected])if(m.coordinate_system.dimension==='3d')m.elements=m.elements.map(e=>{
        if(!e.extra)return e;
        const ends=e.nodes.map(id=>m.nodes.find(n=>n.id===id)),x=unit(sub(xyz(ends[1]),xyz(ends[0])));
        const reference=m.metadata?.elementReferenceVectors?.[e.id]??(Math.abs(x[2])>.9?[1,0,0]:[0,0,1]);
        const extra={...e.extra};
        for(const key of ['axis_reference_vector','public_axis_reference_vector'])if(physicalValueEqual(extra[key],reference,1e-12))delete extra[key];
        const out={...e};if(Object.keys(extra).length)out.extra=extra;else delete out.extra;return out;
      });
      if(inactiveControlPair(actual,expected))for(const m of [actual,expected])m.elements=m.elements.map(e=>{
        if(typeof e.extra?.group!=='string'||!e.extra.group.trim())return e;
        // Public grouping labels describe already explicit member assignments.
        // Other extra fields, including numerical overrides, remain compared.
        const extra={...e.extra};delete extra.group;
        const out={...e};if(Object.keys(extra).length)out.extra=extra;else delete out.extra;return out;
      });
      if(['Euler-Bernoulli','Timoshenko'].includes(options.staticTheory)&&inactiveControlPair(actual,expected))for(const m of [actual,expected]) {
        const extra=m.analysis_control?.extra;
        if(extra&&typeof extra==='object'&&!Array.isArray(extra)) {
          const copy={...extra};
          if(copy.analysis_type==='linear_static')delete copy.analysis_type;
          if(copy.beam_theory===options.staticTheory)delete copy.beam_theory;
          if(copy.shear_area_rule==='Asy=Asz=5*A/6'&&options.staticTheory==='Timoshenko'
            &&options.prescribedShearAreaRatio===5/6&&m.sections.every(s=>['Asy','Asz'].every(k=>s.properties[k]==null
              ||close(s.properties[k],5*s.properties.A/6,1e-12,1e-14))))delete copy.shear_area_rule;
          if(copy.automatic_code_combinations===false)delete copy.automatic_code_combinations;
          if(copy.automatic_load_transfer===false&&(m.stories||[]).every(s=>!s.floor_loads?.length
            &&!(s.dead_load||s.live_load||s.floorLoad||s.liveLoad)))delete copy.automatic_load_transfer;
          m.analysis_control={...m.analysis_control};
          if(Object.keys(copy).length)m.analysis_control.extra=copy;else delete m.analysis_control.extra;
        }
      }
      if(inactiveControlPair(actual,expected))for(const m of [actual,expected])m.stories=(m.stories||[]).map(story=>{
        const s={...story};
        if(Array.isArray(s.floor_loads)&&s.floor_loads.length===0)delete s.floor_loads;
        if(!s.floor_loads)for(const field of ['dead_load','live_load'])if(s[field]===0)delete s[field];
        if(s.rigid_diaphragm===false&&!s.floor_loads&&!s.dead_load&&!s.live_load&&!s.floorLoad&&!s.liveLoad
          &&s.extra&&Object.keys(s.extra).length===1&&verifiedFloorOutline(s.extra.polygonXY,s,m,tolerance))delete s.extra;
        if(Number.isFinite(s.load_area_m2)&&s.load_area_m2>0&&!s.floor_loads
          &&geometryOnlyStory(Object.fromEntries(Object.entries(s).filter(([k])=>k!=='load_area_m2')))) {
          const nodes=m.nodes.filter(n=>close(n.z,s.elevation+s.height,0,tolerance));
          const xs=nodes.map(n=>n.x),ys=nodes.map(n=>n.y),bounds=[Math.min(...xs),Math.max(...xs),Math.min(...ys),Math.max(...ys)];
          const [x0,x1,y0,y1]=bounds,area=(x1-x0)*(y1-y0);
          if(bounds.every(Number.isFinite)&&area>0&&close(s.load_area_m2,area,1e-12,1e-9)
            &&[x0,x1].every(x=>[y0,y1].every(y=>nodes.some(n=>close(n.x,x,0,tolerance)&&close(n.y,y,0,tolerance)))))delete s.load_area_m2;
        }
        return s;
      });
      for(const m of [actual,expected])for(const section of m.sections) {
        const aliases=['i','i-section'];
        // An explicitly dimensioned H section uses the same web/flange fields
        // as an I section. Keep all dimensions, axes and properties compared.
        if(['B','H','tw','tf'].every(k=>Number.isFinite(section.shape?.[k])&&section.shape[k]>0))aliases.push('h','h-section','h_section');
        if(aliases.includes(String(section.type).toLowerCase()))section.type='i_section';
        if(aliases.includes(String(section.shape?.kind).toLowerCase()))section.shape={...section.shape,kind:'i_section'};
        const assigned=m.elements.filter(e=>String(e.section)===String(section.id));
        if(['beam','column'].includes(section.purpose)&&assigned.length&&assigned.every(e=>e.type===section.purpose))delete section.purpose;
        const prescribed=options.staticTheory==='Timoshenko'&&options.prescribedShearAreaRatio===5/6;
        if((section.shape?.kind==='rectangular'||prescribed)&&Number.isFinite(section.properties?.A)) {
          const p={...section.properties};
          for(const key of ['Asy','Asz'])if(close(p[key],5*p.A/6,1e-12,1e-14))delete p[key];
          section.properties=p;
        }
      }
      // A completely omitted floor table is redundant only when it contains
      // inactive geometry already present in both explicit nodal models. Floor
      // loads, diaphragms and unknown metadata stay bound. Native grouping tags
      // may be omitted only when their geometry lies within the checked floors.
      for(const [source,target] of [[actual,expected],[expected,actual]]) {
        const stories=source.stories||[],entities=[...source.nodes,...source.elements],targetEntities=[...target.nodes,...target.elements];
        const level=z=>[source,target].every(m=>m.nodes.some(n=>close(n.z,z,0,tolerance)));
        const contained=entity=>{
          if(entity.story==null)return true;
          const story=stories.find(s=>String(s.id)===String(entity.story));
          if(!story)return false;
          const values=entity.nodes?entity.nodes.map(id=>source.nodes.find(n=>n.id===id)?.z):[entity.z];
          return values.every(z=>Number.isFinite(z)&&z>=story.elevation-tolerance&&z<=story.elevation+story.height+tolerance);
        };
        if(stories.length&&!(target.stories||[]).length&&inactiveControlPair(source,target)
          &&targetEntities.every(e=>e.story==null)&&entities.every(contained)&&stories.every(s=>geometryOnlyStory(s)&&Number.isFinite(s.height)&&s.height>0
            &&Number.isFinite(s.elevation)&&level(s.elevation)&&level(s.elevation+s.height))) {
          source.stories=[];
          for(const field of ['nodes','elements'])source[field]=source[field].map(entity=>{const out={...entity};delete out.story;return out;});
        }
      }
      // Project names add no physical data. Keep design standards, importance,
      // seismic settings and unknown fields strictly compared.
      const optionalRecord=(record,ignored=[])=>{
        if(record==null)return undefined;
        if(typeof record!=='object'||Array.isArray(record))return record;
        const entries=Object.entries(record).filter(([key,value])=>!ignored.includes(key)&&value!=null
          &&!(key==='extra'&&typeof value==='object'&&!Array.isArray(value)&&Object.keys(value).length===0));
        return entries.length?Object.fromEntries(entries):undefined;
      };
      actual={...actual,project:optionalRecord(actual.project,LABEL_FIELDS)};
      expected={...expected,project:optionalRecord(expected.project,LABEL_FIELDS)};
      // An optional frame label is redundant only when the explicit topology
      // on both sides consists entirely of beams and columns, including both.
      const frame=m=>['beam','column'].every(t=>m.elements.some(e=>e.type===t))
        &&m.elements.every(e=>['beam','column'].includes(e.type));
      const types=[actual.structure_system?.type,expected.structure_system?.type];
      if(frame(actual)&&frame(expected)&&types.includes('frame')&&types.some(t=>t==null)) {
        actual={...actual,structure_system:optionalRecord(actual.structure_system,['type'])};
        expected={...expected,structure_system:optionalRecord(expected.structure_system,['type'])};
      }
    }
    const mapping=prepareMapping(actual,expected,tolerance), expectedMapping=prepareMapping(expected,expected,tolerance);
    comparePhysicalFields(actual,expected,[...LABEL_FIELDS,'schema_version','unit_system','coordinate_system','nodes','elements','materials','sections',
      'load_cases','load_combinations','stories','analysis_control','metadata'],'model',relative,failures);
    const storyComparison=compareStoryAttributes(actual,expected,mapping,relative,tolerance,failures,options);
    const actualElements=mapById(actual.elements), actualNodes=mapById(actual.nodes), expectedSections=mapById(expected.sections);
    const actualSections=mapById(actual.sections),actualMaterials=mapById(actual.materials),expectedMaterials=mapById(expected.materials);
    const collapsed=clone(actual); collapsed.nodes=expected.nodes.map(n=>({...actualNodes.get(mapping.nodeMapping[n.id])}));
    for(const n of expected.nodes) {
      const candidate=actualNodes.get(mapping.nodeMapping[n.id]);
      if(n.mass!==undefined&&n.mass!==null ? !close(candidate.mass,n.mass,relative) : candidate.mass!==undefined&&candidate.mass!==null)
        failures.push(`node ${n.id}: mass`);
      comparePhysicalFields(candidate,n,[...LABEL_FIELDS,...AXES,'restraints','mass','story'],`node ${n.id}`,relative,failures);
    }
    collapsed.elements=expected.elements.map(ref=>{
      const records=mapping.elementSegments[ref.id], first=actualElements.get(records[0].id);
      for(const segment of records) {
        const e=actualElements.get(segment.id), expectedAxes=axesFor(expected,ref), actualAxes=axesFor(actual,e);
        const am=actualMaterials.get(String(e.material)),em=expectedMaterials.get(String(ref.material)),
          as=actualSections.get(String(e.section)),es=expectedSections.get(String(ref.section));
        const explicit=options.explicitElasticProperties===true&&legacy.explicitElasticPair(am,em,as,es);
        if(explicit)for(const [missing,declared] of [[am,em],[em,am]]) {
          if(missing.grade==null&&typeof declared.grade==='string'&&typeof missing.name==='string'
            &&declared.grade.toLowerCase()===missing.name.toLowerCase())missing.grade=declared.grade;
        }
        failures.push(...legacy.compareAssignedProperties(expected,actual,new Map([[String(ref.id),segment.id]]),relative,options));
        // Some authored legacy categories (e.g. aluminium) have no literal in
        // MaterialV2's four-category enum and are omitted by its validator.
        // Complete explicit elasticity may omit that legacy description, but a
        // contradictory specific category or two differing descriptions fail.
        const missingLegacyType=explicit&&[[am,em],[em,am]].some(([missing,described])=>missing.type==null
          &&typeof described.type==='string'&&described.category==null
          &&(missing.category==null||missing.category==='other'));
        comparePhysicalFields(normalizedPropertyRecord(actualMaterials.get(String(e.material))),normalizedPropertyRecord(expectedMaterials.get(String(ref.material))),
          [...LABEL_FIELDS,...(explicit&&(am.category==null||em.category==null)?['category']:[]),...(missingLegacyType?['type']:[])],`${ref.id}: material`,relative,failures);
        comparePhysicalFields(normalizedPropertyRecord(as,true,es,explicit,relative),normalizedPropertyRecord(es,true,as,explicit,relative),
          [...LABEL_FIELDS,...(explicit&&(as.shape==null||es.shape==null)?['shape']:[]),
            ...(explicit&&(legacy.genericExplicitSection(as)||legacy.genericExplicitSection(es))?['type']:[])],`${ref.id}: section`,relative,failures);
        comparePhysicalFields(e,ref,[...LABEL_FIELDS,'type','nodes','material','section','rotation_angle','story','releases','offsets'],
          `${ref.id}: element`,relative,failures);
        for(const field of ['releases','offsets']) if((meaningful(e[field])||meaningful(ref[field]))&&!physicalValueEqual(e[field],ref[field],relative))
          failures.push(`${ref.id}: ${field}`);
        if(String(e.story??'')!==String(first.story??'')) failures.push(`${ref.id}: inconsistent segment story`);
        const prop=expectedSections.get(String(ref.section)).properties;
        if(['beam','column'].includes(ref.type)) for(let i=0;i<3;i++) for(let j=0;j<3;j++) {
          const tensor=axes=>(prop.Iy??0)*axes[1][i]*axes[1][j]+(prop.Iz??0)*axes[2][i]*axes[2][j];
          if(!close(tensor(actualAxes),tensor(expectedAxes),relative,1e-12)) failures.push(`${ref.id}: section axes`);
        }
        if(records.length>1 && (meaningful(ref.releases)||meaningful(ref.offsets)||meaningful(e.releases)||meaningful(e.offsets)))
          throw Error('Refinement of members with releases/offsets requires an independently reviewed mapping');
        for(const field of ['concrete_grade','steel_grade','rebar_grade','seismic_grade']) if(ref[field]!==undefined&&e[field]!==ref[field]) failures.push(`${ref.id}: ${field}`);
      }
      const out={...first,id:String(ref.id),nodes:ref.nodes.map(n=>mapping.nodeMapping[n]),rotation_angle:ref.rotation_angle??0};
      if(records.length===1 && records[0].orientation==='reversed') {
        if(meaningful(out.releases)||meaningful(out.offsets)) throw Error('Reversed releases/offsets need an explicit endpoint mapping');
      }
      return out;
    });
    collapsed.materials=clone(actual.materials);
    const reference=clone(expected);
    // The legacy matcher requires entity assignments for every story. Unassigned
    // metadata has already been checked above; retain assigned stories for its
    // geometry, floor-load equivalence and assignment checks.
    collapsed.stories=(collapsed.stories||[]).filter(story=>!storyComparison.unassignedActual.has(String(story.id)));
    reference.stories=(reference.stories||[]).filter(story=>!storyComparison.unassignedExpected.has(String(story.id)));
    for(const entity of [...collapsed.nodes,...collapsed.elements])if(storyComparison.unassignedActual.has(String(entity.story)))delete entity.story;
    for(const entity of [...reference.nodes,...reference.elements])if(storyComparison.unassignedExpected.has(String(entity.story)))delete entity.story;
    // Minor-version additions preserve the same declared physics; frozen 2.0 inputs
    // remain valid references without rewriting them as 2.1 artifacts.
    if(['2.0.0','2.1.0'].includes(collapsed.schema_version)&&['2.0.0','2.1.0'].includes(reference.schema_version)) {
      collapsed.schema_version='2.1.0';reference.schema_version='2.1.0';
    }
    collapsed.load_cases=[]; collapsed.load_combinations=[]; reference.load_cases=[]; reference.load_combinations=[];
    if(collapsed.metadata) delete collapsed.metadata.elementReferenceVectors;
    if(reference.metadata) delete reference.metadata.elementReferenceVectors;
    const structure=legacy.compareStructuralModels(collapsed,reference,{...options,coordinate:tolerance});
    failures.push(...structure.failures);
    const ac=canonicalCases(actual,mapping), ec=canonicalCases(expected,expectedMapping), caseMapping={}, used=new Set();
    if(ac.length!==ec.length) failures.push('missing/extra load cases');
    for(const expectedCase of ec) {
      // In first-order explicit-load OpenSees analysis, an omitted/default
      // category does not change loads or explicit combination coefficients.
      // Engine-specific category effects and all other case attributes remain
      // strict; this option is enabled only by the OpenSees evaluator caller.
      const comparable=c=>{
        const generic=t=>t==null||t==='other';
        const inactive=options.inactiveLoadCaseClassification===true&&inactiveControlPair(actual,expected)
          &&((generic(c.type)&&['dead','live'].includes(expectedCase.type))
            ||generic(expectedCase.type)&&['dead','live'].includes(c.type));
        return inactive?{...c,type:expectedCase.type}:c;
      };
      const candidates=ac.filter(c=>!used.has(c.id)&&caseEqual(comparable(c),expectedCase,options.load??.005,tolerance));
      const selected=candidates.find(c=>c.id===expectedCase.id)||candidates[0];
      if(!selected) {
        const sameLoads=ac.find(c=>!used.has(c.id)&&caseEqual({...c,type:expectedCase.type,attributes:expectedCase.attributes},expectedCase,options.load??.005,tolerance));
        failures.push(sameLoads?`load case ${expectedCase.id}: case type or attributes differ (candidate ${sameLoads.id}, type ${sameLoads.type}; expected ${expectedCase.type})`
          :`load case ${expectedCase.id}: signed loads or physical positions differ`);
      }
      else {caseMapping[expectedCase.id]=selected.id;used.add(selected.id);}
    }
    const combinations=actual.load_combinations||[], combinationMapping={}, usedCombinations=new Set();
    if(combinations.length!==(expected.load_combinations||[]).length) failures.push('missing/extra combinations');
    for(const combination of expected.load_combinations||[]) {
      const factors=Object.fromEntries(Object.entries(combination.factors).map(([id,f])=>[caseMapping[id],f]));
      const match=combinations.find(c=>!usedCombinations.has(c.id)&&Object.keys(c.factors).length===Object.keys(factors).length&&
        Object.entries(factors).every(([id,f])=>close(c.factors[id],f,0)));
      if(!match) failures.push(`load combination ${combination.id}: case factors differ`);
      else {combinationMapping[combination.id]=match.id;usedCombinations.add(match.id);}
    }
    for(const key of new Set([...Object.keys(expected.analysis_control||{}),...Object.keys(actual.analysis_control||{})])) {
      const e=expected.analysis_control?.[key], a=actual.analysis_control?.[key];
      const inactiveDefault=e==null&&a===false&&(['self_weight','rigid_floor','p_delta','rigid_offsets','construction_stage'].includes(key)
        ||options.explicitElasticProperties===true&&key==='live_load_reduction');
      if(!inactiveDefault&&!physicalValueEqual(a,e,0)) failures.push(`analysis_control.${key}`);
    }
    const diagnostics={...mapping,caseMapping,combinationMapping,storyMapping:storyComparison.storyMapping,
      elementMapping:Object.fromEntries(Object.entries(mapping.elementSegments).map(([id,rows])=>[id,rows[0].id])),
      elementOrientation:Object.fromEntries(Object.entries(mapping.elementSegments).map(([id,rows])=>[id,rows[0].orientation])),
      physicalAxes:Object.fromEntries(expected.elements.map(e=>[e.id,axesFor(expected,e)]))};
    return {pass:failures.length===0,summary:`physical members ${expected.elements.length}; solver members ${actual.elements.length}; independently matched cases ${Object.keys(caseMapping).length}/${ec.length}`,
      metrics:{...structure.metrics,physicalMembers:expected.elements.length,solverMembers:actual.elements.length},failures:[...new Set(failures)],diagnostics,
      matcherVersion:'physical-v1'};
  } catch(error) {
    return {pass:false,summary:error.message,failures:[error.message],metrics:{},diagnostics:{},matcherVersion:'physical-v1'};
  }
}

module.exports={comparePhysicalModels,axesFor};
