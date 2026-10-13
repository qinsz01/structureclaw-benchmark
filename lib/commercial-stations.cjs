/** Native signed cuts. Never turn an envelope or a plotted interpolation into evidence. */
const COMPONENTS=['N','Vy','Vz','T','My','Mz'];
const finite=value=>typeof value==='number'&&Number.isFinite(value);
const dot=(a,b)=>a.reduce((s,v,i)=>s+v*b[i],0);
// Only absorb arithmetic roundoff; a nearby physical cut can have a different force.
const samePosition=(a,b)=>finite(a)&&finite(b)&&Math.abs(a-b)<=8*Number.EPSILON*Math.max(1,Math.abs(a),Math.abs(b));
function axes(value) {
  if(!Array.isArray(value)||value.length!==3||value.some(a=>!Array.isArray(a)||a.length!==3||!a.every(finite))
    ||value.some((a,i)=>value.some((b,j)=>Math.abs(dot(a,b)-(i===j?1:0))>1e-9))) throw Error('Verified orthonormal station axes required');
  const [x,y,z]=value,cross=[x[1]*y[2]-x[2]*y[1],x[2]*y[0]-x[0]*y[2],x[0]*y[1]-x[1]*y[0]];
  if(Math.abs(dot(cross,z)-1)>1e-9) throw Error('Right-handed station axes required');
  return value;
}
function requireNativeStations(data) {
  const context=data?.nativeContext;
  if(data?.forceSemantics!=='simultaneous-signed-stations'||context?.effectiveSettingsVerified!==true
    ||context?.stationConventionsVerified!==true||context?.linearStatic!==true
    ||['engine','engineVersion','physicalModelHash','stiffnessHash','settingsHash'].some(key=>typeof context?.[key]!=='string'||!context[key])
    ||!data.memberStations) throw Error('Verified simultaneous native stations required');
}
function transformCut(row,targetAxes,reverse=false) {
  const source=axes(row.localAxes),target=axes(targetAxes),c=row.components;
  if(row.referenceFrame!=='element-local'||!COMPONENTS.every(k=>finite(c?.[k]))) throw Error('Six signed cut components required');
  // Section convention: N is tension-positive, shear follows the cut face;
  // moments have the opposite cut-face sign. Reverse the face with endpoint order.
  const vector=values=>target.map(axis=>dot(axis,[0,1,2].map(i=>
    values.reduce((sum,v,j)=>sum+v*source[j][i],0)*(reverse?-1:1))));
  const f=vector([-c.N,c.Vy,c.Vz]),m=vector([-c.T,-c.My,-c.Mz]);
  return {N:-f[0],Vy:f[1],Vz:f[2],T:-m[0],My:-m[1],Mz:-m[2]};
}
function validateStationRows(rows) {
  if(!Array.isArray(rows)||!rows.length) throw Error('Native signed station rows required');
  const cuts=new Map();
  for(const row of rows) {
    if(!finite(row?.positionM)||row.positionM<0||!['left','right','continuous'].includes(row.side)
      ||row.referenceFrame!=='element-local'||!COMPONENTS.every(key=>finite(row.components?.[key])))
      throw Error('Valid physical position, side and six signed native components required');
    const sides=cuts.get(row.positionM)||new Set();
    if(sides.has(row.side)||sides.has('continuous')||(row.side==='continuous'&&sides.size))
      throw Error('Native cut is duplicate or has conflicting continuous/one-sided rows');
    sides.add(row.side);cuts.set(row.positionM,sides);
    axes(row.localAxes);
  }
}
function readNativeStation(data,memberId,positionM,side,mappings={},targetAxes) {
  if(!finite(positionM)||!['left','right','continuous'].includes(side)) throw Error('Exact station and cut side required');
  let id=mappings.elementMapping?.[memberId]??memberId,x=positionM,reverse=false;
  const segments=mappings.elementSegments?.[memberId];
  if(segments?.length) {
    const matches=segments.filter(s=>finite(s.start)&&finite(s.end)
      &&(x>=s.start||samePosition(x,s.start))&&(x<=s.end||samePosition(x,s.end)));
    const segment=side==='left'?matches[0]:matches.at(-1);
    if(!segment) throw Error('Requested station is outside mapped physical member');
    id=segment.id;reverse=segment.orientation==='reversed';x=reverse?segment.end-x:x-segment.start;
  } else if(mappings.elementOrientation?.[memberId]==='reversed') {
    const length=data.memberLengths?.[id];
    if(!finite(length)) throw Error('Reversed member requires its physical length');
    reverse=true;x=length-x;
  }
  const localSide=reverse?({left:'right',right:'left',continuous:'continuous'}[side]):side;
  const sourceRows=data.memberStations?.[id]||[];
  validateStationRows(sourceRows);
  const rows=sourceRows.filter(row=>samePosition(row.positionM,x));
  if(rows.some(row=>row.side==='continuous')&&rows.length>1)
    throw Error('Native cut has conflicting continuous/one-sided rows');
  // Continuous cuts may serve either side only if there is no explicit jump.
  const exact=rows.filter(row=>row.side===localSide);
  const candidates=exact.length?exact:rows.every(row=>row.side==='continuous')?rows:[];
  if(candidates.length!==1) throw Error(`Exact native cut ${memberId}@${positionM}:${side} unavailable or ambiguous`);
  const row=candidates[0],target=targetAxes||mappings.physicalAxes?.[memberId]||(!reverse?row.localAxes:null);
  return transformCut(row,target,reverse);
}
module.exports={COMPONENTS,axes,requireNativeStations,readNativeStation,transformCut,validateStationRows,samePosition};
