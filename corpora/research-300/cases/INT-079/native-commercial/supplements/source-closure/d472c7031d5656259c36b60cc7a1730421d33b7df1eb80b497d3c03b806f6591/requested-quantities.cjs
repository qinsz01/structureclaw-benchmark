const {selectAnalysisResult,selectionKey}=require('./result-selection.cjs');
const {requireNativeStations,readNativeStation,samePosition}=require('./commercial-stations.cjs');
const {referenceAllowance,comparisonTolerance,precisionSummary}=require('./reference-precision.cjs');
const finite=value=>typeof value==='number'&&Number.isFinite(value);
const UNITS={ux:'m',uy:'m',uz:'m',rx:'rad',ry:'rad',rz:'rad',fx:'kN',fy:'kN',fz:'kN',mx:'kN.m',my:'kN.m',mz:'kN.m',Fx:'kN',Fy:'kN',Fz:'kN',Mx:'kN.m',My:'kN.m',Mz:'kN.m',N:'kN',V2:'kN',V3:'kN',T:'kN.m',M2:'kN.m',M3:'kN.m'};
const UNIT_FACTORS={m:{m:1,mm:.001},rad:{rad:1},kN:{kN:1,N:.001},
  'kN.m':{'kN.m':1,'kN*m':1,'kN·m':1,'N.m':.001,'N*m':.001}};
const DEFAULT_TIE_TOLERANCE={absolute:1e-8,relative:1e-6};
const CLOSE=(a,b,t)=>finite(a)&&finite(b)&&Math.abs(a-b)<=t.absolute+t.relative*Math.abs(b);

function readQuantity(analysis, quantity, mappings={}) {
  const selection=quantity.selection;
  if(!selection?.id||!['case','combination'].includes(selection.kind)) throw Error('Exact case/combination required');
  const mapping=selection.kind==='case'?mappings.caseMapping:mappings.combinationMapping;
  const actualSelection={...selection,id:mapping?.[selection.id]??selection.id};
  const {data,record}=selectAnalysisResult(analysis,actualSelection);
  const canonical=UNITS[quantity.component],factors=UNIT_FACTORS[canonical];
  if(!factors||!factors[quantity.unit])throw Error(`Incompatible unit ${quantity.unit} for ${quantity.component}`);
  const dimension={m:'displacement',rad:'rotation',kN:'force','kN.m':'moment'}[canonical];
  const declared=data.units||data.meta?.units||record.meta?.units;
  if(data.memberStations&&!declared?.[dimension]) throw Error(`Explicit native ${dimension} unit required`);
  const sourceUnit=declared?.[dimension]||canonical;
  if(!factors[sourceUnit])throw Error(`Incompatible source unit ${sourceUnit} for ${quantity.component}`);
  const convert=value=>value*factors[sourceUnit]/factors[quantity.unit];
  const location=quantity.location;
  if(location.kind==='node') {
    const id=mappings.nodeMapping?.[location.id]??location.id;
    const key=quantity.component.startsWith('u')||quantity.component.startsWith('r')?'displacements':'reactions';
    const components=data[key]?.[id];
    const value=components?.[quantity.component]??components?.[quantity.component.toLowerCase()];
    if(!finite(value)) throw Error('Required node response is missing');
    return convert(value);
  }
  if(location.kind!=='member'||!finite(location.positionM)||!['left','right'].includes(location.side)) throw Error('Member station requires positionM and side');
  if(data.memberStations) {
    requireNativeStations(data);
    const nativeKey={N:'N',V2:'Vy',V3:'Vz',T:'T',M2:'My',M3:'Mz'}[quantity.component];
    if(!nativeKey) throw Error('Native signed cuts do not supply internal displacement');
    const cut=readNativeStation(data,location.id,location.positionM,location.side,mappings);
    return convert(cut[nativeKey]);
  }
  let id=mappings.elementMapping?.[location.id]??location.id, x=location.positionM, reverse=false;
  const segments=mappings.elementSegments?.[location.id];
  if(segments?.length) {
    const matches=segments.filter(s=>(x>=s.start||samePosition(x,s.start))&&(x<=s.end||samePosition(x,s.end)));
    const segment=location.side==='left'?matches[0]:matches.at(-1);
    if(!segment) throw Error('Station is outside the mapped physical member');
    id=segment.id;reverse=segment.orientation==='reversed';x=reverse?segment.end-x:x-segment.start;
  }
  const row=data.memberResponses?.find(r=>r.id===id);
  if(!row||!['recovered','truss'].includes(row.state)) throw Error('Mechanical member response missing; display interpolation is not numerical evidence');
  const side=reverse?(location.side==='left'?'right':'left'):location.side;
  const points=row.samples.filter(s=>samePosition(s.x,x)&&s.side===side);
  const sample=side==='left'?points[0]:points.at(-1);
  if(!sample) throw Error('Exact requested station was not evaluated; nearest plotted sample is insufficient');
  if(quantity.component.startsWith('u')) {
    const value=sample.displacement?.[{ux:0,uy:1,uz:2}[quantity.component]];
    if(!finite(value)) throw Error('Requested displacement component missing');
    return convert(value);
  }
  if(reverse) throw Error('Reversed internal action station needs an audited axis/sign transform');
  const value=sample[quantity.component];
  if(!finite(value)) throw Error('Requested signed action component missing');
  return convert(value);
}

function compareRequestedQuantities(analysis, quantities, mappings={}) {
  const failures=[],strictFailures=[],ids=new Set();let comparedValues=0;
  if(!Array.isArray(quantities)||!quantities.length) return {pass:false,comparedValues,failures:['No independently frozen requested quantities']};
  for(const q of quantities) {
    try {
      validateFrozenQuantity(q);
      const key=JSON.stringify([q.selection.kind,q.selection.id,q.id]);
      if(ids.has(key)) throw Error('Duplicate quantity ID within selection');
      ids.add(key);
      const actual=readQuantity(analysis,q,mappings);comparedValues++;
      const message=`${q.id}: ${actual} != ${q.value} ${q.unit}`;
      if(!CLOSE(actual,q.value,q.tolerance))strictFailures.push(message);
      if(!CLOSE(actual,q.value,comparisonTolerance(q)))failures.push(message);
    } catch(error) {const message=`${q?.id||'quantity'}: ${error.message}`;failures.push(message);strictFailures.push(message);}
  }
  const precision=precisionSummary(quantities,strictFailures);
  return {pass:!failures.length,comparedValues,failures,...(precision?{precision}:{})};
}

const record=value=>value&&typeof value==='object'&&!Array.isArray(value);
const identifier=value=>typeof value==='string'&&value.trim().length>0;
const validTolerance=t=>record(t)&&finite(t.absolute)&&finite(t.relative)&&t.absolute>=0&&t.relative>=0;
function unitConversion(from,to) {
  const factors=Object.values(UNIT_FACTORS).find(f=>Object.hasOwn(f,from)&&Object.hasOwn(f,to));
  if(!factors) throw Error(`Incompatible units ${from} and ${to}`);
  return factors[from]/factors[to];
}
function validateFrozenQuantity(q) {
  if(!record(q)||!identifier(q.id)||!finite(q.value)||!validTolerance(q.tolerance))
    throw Error('Frozen value, ID, and explicit nonnegative tolerances required');
  if(!identifier(q.selection?.id)||!['case','combination'].includes(q.selection.kind)) throw Error('Exact case/combination required');
  unitConversion(q.unit,q.unit);
  referenceAllowance(q);
}
function compensatedSum(values) {
  let sum=0,correction=0;
  for(const value of values) {
    const next=sum+value;
    // Neumaier compensation retains small reaction totals after large cancellation.
    correction+=Math.abs(sum)>=Math.abs(value)?(sum-next)+value:(value-next)+sum;
    sum=next;
  }
  return sum+correction;
}

/** Evaluate only independently frozen primitives; candidate-provided derived values are never inputs. */
function evaluateDerivedQuantities(quantities,derived) {
  const failures=[],primitives=new Map(),definitions=new Map(),resolved=new Map(),visiting=new Set(),primitiveKeys=new Set();
  if(derived?.length&&quantities?.some(q=>q?.engineeringPrecision!==undefined))
    return {pass:false,values:[],failures:['The certified recovery precision policy does not authorize derived propagation']};
  if(!Array.isArray(quantities)||!quantities.length) failures.push('No independently frozen requested quantities');
  else for(const q of quantities) {
    try {
      validateFrozenQuantity(q);
      const key=JSON.stringify([q.selection.kind,q.selection.id,q.id]);
      if(primitiveKeys.has(key)) throw Error('Duplicate quantity ID within selection');
      primitiveKeys.add(key);
      primitives.set(q.id,[...(primitives.get(q.id)||[]),q]);
    } catch(error) {failures.push(`${q?.id||'quantity'}: ${error.message}`);}
  }
  if(!Array.isArray(derived)) failures.push('Derived requirements must be an array');
  else for(const d of derived) {
    try {
      if(!record(d)||!identifier(d.id)) throw Error('Derived requirement ID is missing');
      if(definitions.has(d.id)||primitives.has(d.id)) throw Error('Duplicate derived or primitive ID');
      if(!['difference','sum','max','min','max_abs'].includes(d.operation)) throw Error('Unsupported derived operation');
      if(d.tiePolicy!==undefined&&(!['first','any'].includes(d.tiePolicy)||!['max','min','max_abs'].includes(d.operation)))
        throw Error('Tie policy must be first or any and applies only to extrema');
      if(!Array.isArray(d.operands)||!d.operands.length||!d.operands.every(identifier)) throw Error('Nonempty operand IDs required');
      if(d.operation==='difference'&&d.operands.length!==2) throw Error('Difference requires exactly two operands');
      if(d.tolerance!==undefined&&!validTolerance(d.tolerance)) throw Error('Invalid explicit derived tolerance');
      unitConversion(d.unit,d.unit);
      definitions.set(d.id,d);
    } catch(error) {failures.push(`${d?.id||'derived'}: ${error.message}`);}
  }
  if(failures.length) return {pass:false,values:[],failures};
  function resolve(id) {
    if(resolved.has(id)) return resolved.get(id);
    if(primitives.has(id)) {
      const matches=primitives.get(id);
      if(matches.length!==1) throw Error(`Ambiguous operand ${id} occurs in multiple selections`);
      return matches[0];
    }
    const d=definitions.get(id);
    if(!d) throw Error(`Missing operand ${id}`);
    if(visiting.has(id)) throw Error(`Cyclic derived dependency at ${id}`);
    visiting.add(id);
    try {
      const operands=d.operands.map(operand=>{
        const source=resolve(operand),factor=unitConversion(source.unit,d.unit);
        const value=source.value*factor;
        const error=(source.tolerance.absolute+source.tolerance.relative*Math.abs(source.value))*factor;
        if(!finite(value)||!finite(error)) throw Error(`Nonfinite converted operand ${operand}`);
        return {id:operand,value,error,selection:source.selection??source.governingSelection??null};
      });
      let value,governor=null,absolute,selection,coGoverningOperands;
      if(d.operation==='difference'||d.operation==='sum') {
        value=d.operation==='difference'?operands[0].value-operands[1].value:compensatedSum(operands.map(o=>o.value));
        absolute=compensatedSum(operands.map(o=>o.error));
        const first=operands[0].selection;
        if(first&&operands.every(o=>o.selection?.kind===first.kind&&o.selection?.id===first.id)) selection={...first};
      } else {
        const score=operand=>d.operation==='max_abs'?Math.abs(operand.value):operand.value;
        const best=d.operation==='min'?Math.min(...operands.map(score)):Math.max(...operands.map(score));
        const coGovernors=operands.filter(operand=>CLOSE(score(operand),best,d.tolerance||DEFAULT_TIE_TOLERANCE));
        // Canonical references retain the first tolerance co-governor, including its sign.
        governor=coGovernors[0];coGoverningOperands=coGovernors.map(operand=>operand.id);
        if(d.coGoverningOperands!==undefined&&(!Array.isArray(d.coGoverningOperands)||
          d.coGoverningOperands.length!==coGoverningOperands.length||d.coGoverningOperands.some((id,index)=>id!==coGoverningOperands[index])))
          throw Error('Recorded coGoverningOperands differ from the independently computed frozen co-set');
        value=governor.value;absolute=Math.max(...operands.map(o=>o.error));
      }
      if(!finite(value)||!finite(absolute)) throw Error(`Nonfinite derived value or tolerance for ${id}`);
      const result={id,value,unit:d.unit,governingOperand:governor?.id??null,
        governingSelection:governor?.selection?{...governor.selection}:null,
        ...(selection?{selection}:{}),
        ...(coGoverningOperands?{coGoverningOperands}:{}),
        tolerance:d.tolerance?{...d.tolerance}:{absolute,relative:0}};
      resolved.set(id,result);return result;
    } finally {visiting.delete(id);}
  }
  for(const d of derived) try {resolve(d.id);} catch(error) {failures.push(`${d.id}: ${error.message}`);}
  return {pass:!failures.length,values:failures.length?[]:derived.map(d=>resolved.get(d.id)),failures};
}

function sameGovernor(actual,expected) {
  return actual.governingOperand===expected.governingOperand&&
    (expected.governingSelection===null?actual.governingSelection===null:
      actual.governingSelection?.kind===expected.governingSelection.kind&&actual.governingSelection?.id===expected.governingSelection.id);
}
const sameSelection=(a,b)=>a?.kind===b?.kind&&a?.id===b?.id;
const sameLocation=(a,b)=>record(a)&&record(b)&&a.kind===b.kind&&a.id===b.id&&a.positionM===b.positionM&&a.side===b.side;
const primitiveIdentity=q=>JSON.stringify([q.selection.kind,q.selection.id,q.id]);
/**
 * Public reports can identify a governing physical node/member without private
 * quantity IDs. Multiple candidate stations require governingLocation with the
 * exact kind/id/positionM/side; a nearest station or arbitrary drift endpoint is
 * not an identity. A selection key can identify a nested arithmetic governor
 * only when exactly one immediate operand has that selection. This affects
 * report aliases only, never computed governors.
 */
function verifyReportedGovernor(row,frozen,quantities,derived,values) {
  if(frozen.governingOperand===null) {
    if(row.governingOperand!=null||row.governingSelection!=null||row.governingLocation!=null)
      throw Error('Arithmetic output cannot invent a governing operand or selection');
    return;
  }
  if(frozen.governingSelection===null?row.governingSelection!==null:!sameSelection(row.governingSelection,frozen.governingSelection))
    throw Error('Reported governing operand or selection differs');
  const definitions=new Map(derived.map(d=>[d.id,d])),computed=new Map(values.map(value=>[value.id,value]));
  if(frozen.governingSelection&&row.governingOperand===selectionKey(frozen.governingSelection)) {
    const operands=definitions.get(frozen.id).operands.filter(id=>{
      const source=computed.get(id)||quantities.find(q=>q.id===id);
      return sameSelection(source?.selection??source?.governingSelection,frozen.governingSelection);
    });
    if(operands.length!==1||operands[0]!==frozen.governingOperand||row.governingLocation!==undefined)
      throw Error('Reported governing selection is ambiguous or has an inconsistent governingLocation');
    return;
  }
  function sources(id,governingOnly) {
    const primitives=quantities.filter(q=>q.id===id);
    if(primitives.length) return primitives;
    const definition=definitions.get(id),value=computed.get(id);
    if(!definition) return [];
    const operands=governingOnly&&value?.governingOperand!=null?[value.governingOperand]:definition.operands;
    const found=operands.flatMap(operand=>sources(operand,governingOnly));
    return [...new Map(found.map(q=>[primitiveIdentity(q),q])).values()];
  }
  const winners=sources(frozen.governingOperand,true);
  const hasLocation=row.governingLocation!==undefined;
  if(row.governingOperand===frozen.governingOperand||winners.length===1&&row.governingOperand===winners[0].id) {
    if(hasLocation&&(winners.length!==1||!sameLocation(row.governingLocation,winners[0].location)))
      throw Error('Reported governingLocation differs from the governing source');
    return;
  }
  let candidates=sources(frozen.id,false).filter(q=>q.location?.id===row.governingOperand&&sameSelection(q.selection,row.governingSelection));
  if(!hasLocation&&candidates.length>1) throw Error('Ambiguous public governing operand; provide exact governingLocation (kind, id, positionM, side)');
  if(hasLocation) candidates=candidates.filter(q=>sameLocation(row.governingLocation,q.location));
  if(candidates.length!==1||winners.length!==1||primitiveIdentity(candidates[0])!==primitiveIdentity(winners[0]))
    throw Error('Reported governing operand or governingLocation differs or is ambiguous');
}
function compareDerivedQuantities(analysis,quantities,derived,mappings={},reportedDerived,reportedIds) {
  const expected=evaluateDerivedQuantities(quantities,derived),primitiveComparison=compareRequestedQuantities(analysis,quantities,mappings);
  const failures=[...expected.failures,...primitiveComparison.failures];
  const result={pass:false,values:expected.values,actualValues:[],comparedValues:primitiveComparison.comparedValues,
    comparedDerived:0,primitiveComparison,failures};
  if(failures.length) return result;
  const actual=evaluateDerivedQuantities(quantities.map(q=>({...q,value:readQuantity(analysis,q,mappings)})),
    derived.map(({coGoverningOperands,...definition})=>definition));
  result.actualValues=actual.values;failures.push(...actual.failures);
  for(let i=0;i<expected.values.length&&actual.pass;i++) {
    const frozen=expected.values[i],observed=actual.values[i];result.comparedDerived++;
    if(!CLOSE(observed.value,frozen.value,frozen.tolerance)) failures.push(`${frozen.id}: derived ${observed.value} != ${frozen.value} ${frozen.unit}`);
    if(!sameGovernor(observed,frozen)) failures.push(`${frozen.id}: derived governing operand or selection differs`);
  }
  if(reportedDerived!==undefined) {
    if(!Array.isArray(reportedDerived)) failures.push('Reported derived quantities must be an array');
    else {
      const reports=new Map();
      for(const row of reportedDerived) {
        if(!record(row)||!identifier(row.id)||!finite(row.value)||reports.has(row.id)) failures.push('Malformed or duplicate reported derived quantity');
        else if(!expected.values.some(value=>value.id===row.id)) failures.push(`Unexpected reported derived quantity ${row.id}`);
        else reports.set(row.id,row);
      }
      const required=reportedIds===undefined?expected.values:expected.values.filter(value=>reportedIds.includes(value.id));
      for(const frozen of required) {
        const row=reports.get(frozen.id);
        try {
          if(!row||!finite(row.value)) throw Error('Reported derived quantity is missing or nonfinite');
          const value=row.value*unitConversion(row.unit,frozen.unit);
          const definition=derived.find(d=>d.id===frozen.id);
          const eligible=definition.tiePolicy==='any'?frozen.coGoverningOperands.map(id=>{
            const source=expected.values.find(v=>v.id===id)||quantities.find(q=>q.id===id);
            return {...frozen,value:source.value*unitConversion(source.unit,frozen.unit),governingOperand:id,
              governingSelection:source.selection??source.governingSelection??null};
          }):[frozen];
          const matches=[],governorFailures=[];
          for(const candidate of eligible) {
            try {verifyReportedGovernor(row,candidate,quantities,derived,expected.values);matches.push(candidate);}
            catch(error) {governorFailures.push(error.message);}
          }
          if(matches.length!==1) throw Error(matches.length?'Reported governing identity is ambiguous':governorFailures[0]);
          if(!CLOSE(value,matches[0].value,frozen.tolerance)) throw Error('Reported signed derived value differs for the selected governing operand');
        } catch(error) {failures.push(`${frozen.id}: ${error.message}`);}
      }
    }
  }
  result.pass=!failures.length;return result;
}

/** Requested values are rendered as a stable Markdown table, so wording cannot hide a wrong unit or case. */
function compareReportQuantities(report, quantities) {
  const rows=String(report?.markdown||'').split(/\r?\n/).filter(line=>line.trim().startsWith('|'))
    .map(line=>line.trim().split('|').slice(1,-1).map(x=>x.trim()));
  const failures=[],strictFailures=[],ids=new Set();
  for(const q of Array.isArray(quantities)?quantities:[]) {
    try {
      validateFrozenQuantity(q);
      const key=JSON.stringify([q.selection.kind,q.selection.id,q.id]);
      if(ids.has(key)) throw Error('Duplicate requested report quantity within selection');
      ids.add(key);
      const matches=rows.filter(r=>r[0]===q.id&&r[1]===selectionKey(q.selection));
      const row=matches[0];
      const loc=q.location.kind==='node'?q.location.id:`${q.location.id}@${q.location.positionM}:${q.location.side}`;
      const numeric=/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/;
      if(matches.length!==1||row[2]!==loc||row[3]!==q.component||unitConversion(row[5],q.unit)!==1||!numeric.test(row[4]))
        throw Error('missing, duplicate, or inconsistent body row (case, location, component, signed value, unit)');
      if(!CLOSE(Number(row[4]),q.value,q.tolerance))strictFailures.push(`${q.id}: body differs at original frozen tolerance`);
      if(!CLOSE(Number(row[4]),q.value,comparisonTolerance(q)))throw Error('inconsistent signed body value');
    } catch(error) {const message=`${q?.id||'quantity'}: ${error.message}`;failures.push(message);if(!strictFailures.some(x=>x.startsWith(`${q?.id}:`)))strictFailures.push(message);}
  }
  if(!Array.isArray(quantities)||!quantities.length) failures.push('No requested report quantities');
  const precision=precisionSummary(Array.isArray(quantities)?quantities:[],strictFailures);
  return {pass:!failures.length,comparedValues:Array.isArray(quantities)?quantities.length:0,failures,...(precision?{precision}:{})};
}
module.exports={readQuantity,compareRequestedQuantities,compareReportQuantities,evaluateDerivedQuantities,compareDerivedQuantities,UNITS};
