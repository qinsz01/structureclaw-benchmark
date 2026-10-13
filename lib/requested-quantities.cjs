const {selectAnalysisResult,selectionKey}=require('./result-selection.cjs');
const {requireNativeStations,readNativeStation,samePosition}=require('./commercial-stations.cjs');
const finite=value=>typeof value==='number'&&Number.isFinite(value);
const UNITS={ux:'m',uy:'m',uz:'m',rx:'rad',ry:'rad',rz:'rad',fx:'kN',fy:'kN',fz:'kN',mx:'kN.m',my:'kN.m',mz:'kN.m',N:'kN',V2:'kN',V3:'kN',T:'kN.m',M2:'kN.m',M3:'kN.m'};
const UNIT_FACTORS={m:{m:1,mm:.001},rad:{rad:1},kN:{kN:1,N:.001},'kN.m':{'kN.m':1,'N.m':.001}};
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
    const value=data[key]?.[id]?.[quantity.component];
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
  const failures=[];let comparedValues=0;
  if(!Array.isArray(quantities)||!quantities.length) return {pass:false,comparedValues,failures:['No independently frozen requested quantities']};
  for(const q of quantities) {
    try {
      if(!q.id||!finite(q.value)||!finite(q.tolerance?.absolute)||!finite(q.tolerance?.relative)||q.tolerance.absolute<0||q.tolerance.relative<0) throw Error('Frozen value and explicit nonnegative tolerances required');
      const actual=readQuantity(analysis,q,mappings);comparedValues++;
      if(!CLOSE(actual,q.value,q.tolerance)) failures.push(`${q.id}: ${actual} != ${q.value} ${q.unit}`);
    } catch(error) {failures.push(`${q.id||'quantity'}: ${error.message}`);}
  }
  return {pass:!failures.length,comparedValues,failures};
}

/** Requested values are rendered as a stable Markdown table, so wording cannot hide a wrong unit or case. */
function compareReportQuantities(report, quantities) {
  const rows=String(report?.markdown||'').split(/\r?\n/).filter(line=>line.trim().startsWith('|'))
    .map(line=>line.trim().split('|').slice(1,-1).map(x=>x.trim()));
  const failures=[];
  for(const q of quantities||[]) {
    const row=rows.find(r=>r[0]===q.id);
    const loc=q.location.kind==='node'?q.location.id:`${q.location.id}@${q.location.positionM}:${q.location.side}`;
    if(!row||row[1]!==selectionKey(q.selection)||row[2]!==loc||row[3]!==q.component||row[5]!==q.unit||!CLOSE(Number(row[4]),q.value,q.tolerance)) failures.push(`${q.id}: missing or inconsistent body row (case, location, component, signed value, unit)`);
  }
  if(!quantities?.length) failures.push('No requested report quantities');
  return {pass:!failures.length,comparedValues:quantities?.length||0,failures};
}
module.exports={readQuantity,compareRequestedQuantities,compareReportQuantities,UNITS};
