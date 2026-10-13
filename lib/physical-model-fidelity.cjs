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

function close(a,b,tolerance=1e-8,absolute=1e-9) {
  return typeof a==='number' && Number.isFinite(a) && typeof b==='number' && Number.isFinite(b)
    && Math.abs(a-b)<=Math.max(absolute,Math.abs(b)*tolerance);
}

function axesFor(model, element) {
  const nodes=mapById(model.nodes), a=xyz(nodes.get(String(element.nodes[0]))), b=xyz(nodes.get(String(element.nodes[1])));
  const x=unit(sub(b,a));
  if(model.coordinate_system.dimension==='2d') return [x,[0,1,0],cross(x,[0,1,0])];
  let reference=model.metadata?.elementReferenceVectors?.[element.id];
  if(!reference) reference=Math.abs(x[2])>.9?[1,0,0]:[0,0,1];
  const y=unit(cross(unit(reference),x)), z=unit(cross(x,y));
  const angle=Number(element.rotation_angle||0)*Math.PI/180, c=Math.cos(angle), s=Math.sin(angle);
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
          if(load.distribution==='piecewise_linear') {
            if(!Array.isArray(load.points)||load.points.length<2) throw Error('Invalid piecewise-linear load');
            points=load.points.map(p=>({position:position(p.position*length),values:globalVector(components(p,qfields),axes,load.reference_frame)}));
          } else if(load.distribution===undefined||load.distribution==='uniform') {
            const values=globalVector(components(load,qfields),axes,load.reference_frame);
            points=[{position:position(load.start??0),values},{position:position(load.end??length),values}];
          } else throw Error(`Unsupported distribution ${load.distribution}`);
          if(segment.orientation==='reversed') points.reverse();
          for(let i=1;i<points.length;i++) {
            if(points[i].position<=points[i-1].position) throw Error('Distributed load positions are not increasing');
            distributed.push({member:segment.physicalElementId,a:points[i-1].position,b:points[i].position,
              qa:points[i-1].values,qb:points[i].values});
          }
        } else throw Error(`Unsupported member load type ${kind}`);
      }
    }
    return {id:String(loadCase.id),type:loadCase.type,nodal,prescribed,point,distributed};
  });
}

function caseEqual(actual,expected,relative,positionTolerance) {
  if(actual.type!==expected.type) return false;
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

function comparePhysicalModels(actual,expected,options={}) {
  const tolerance=options.coordinate??options.span??1e-6, relative=options.property??.005, failures=[];
  try {
    for(const [label,model] of [['candidate',actual],['reference',expected]]) {
      const integrity=legacy.inspectModelIntegrity(model), coordinate=legacy.inspectCoordinateContract(model);
      if(!integrity.ok||!coordinate.ok) throw Error(`${label}: ${!integrity.ok?integrity.reason:coordinate.reason}`);
    }
    const mapping=prepareMapping(actual,expected,tolerance), expectedMapping=prepareMapping(expected,expected,tolerance);
    const actualElements=mapById(actual.elements), actualNodes=mapById(actual.nodes), expectedSections=mapById(expected.sections);
    const collapsed=clone(actual); collapsed.nodes=expected.nodes.map(n=>actualNodes.get(mapping.nodeMapping[n.id]));
    for(const n of expected.nodes) {
      const candidate=actualNodes.get(mapping.nodeMapping[n.id]);
      if(n.mass!==undefined&&n.mass!==null ? !close(candidate.mass,n.mass,relative) : candidate.mass!==undefined&&candidate.mass!==null)
        failures.push(`node ${n.id}: mass`);
    }
    collapsed.elements=expected.elements.map(ref=>{
      const records=mapping.elementSegments[ref.id], first=actualElements.get(records[0].id);
      for(const segment of records) {
        failures.push(...legacy.compareAssignedProperties(expected,actual,new Map([[String(ref.id),segment.id]]),relative));
        const e=actualElements.get(segment.id), expectedAxes=axesFor(expected,ref), actualAxes=axesFor(actual,e);
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
    const reference=clone(expected);
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
      const candidates=ac.filter(c=>!used.has(c.id)&&caseEqual(c,expectedCase,options.load??.005,tolerance));
      const selected=candidates.find(c=>c.id===expectedCase.id)||candidates[0];
      if(!selected) failures.push(`load case ${expectedCase.id}: signed loads or physical positions differ`);
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
    for(const key of ['self_weight','rigid_floor','p_delta','rigid_offsets','construction_stage','mass_source']) {
      const e=expected.analysis_control?.[key], a=actual.analysis_control?.[key];
      if(e!==undefined&&e!==null ? a!==e : a===true) failures.push(`analysis_control.${key}`);
    }
    const diagnostics={...mapping,caseMapping,combinationMapping,
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
