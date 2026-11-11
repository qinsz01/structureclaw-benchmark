'use strict';
const {unloadedAxialMember}=require('./requested-quantities.cjs');
const {samePosition}=require('./commercial-stations.cjs');

const NUMBER = '[+-]?(?:\\d+(?:\\.\\d*)?|\\.\\d+)(?:[eE][+-]?\\d+)?';
const MEMBER_LOCATION = new RegExp(`^(.*)@(${NUMBER}):(left|right)$`);
const object = value => value && typeof value === 'object' && !Array.isArray(value);
function numericSpelling(value) {
  const zeroNote=/^(.*?)\s*(?:[（(]\s*(?:≈\s*0|约\s*(?:0|零)|数值零)\s*[)）]|≈\s*0)$/.exec(value);
  if(zeroNote) {
    const base=numericSpelling(zeroNote[1].trim());
    if(new RegExp(`^${NUMBER}$`).test(base)&&Math.abs(Number(base))<=1e-8)return base;
  }
  const text=value.replace(/−/g,'-').replace(/＋/g,'+');
  if(new RegExp(`^${NUMBER}$`).test(text)) return text;
  const scientific=new RegExp(`^(${NUMBER})\\s*×\\s*10(?:\\^([+-]?\\d+)|([⁺⁻⁰¹²³⁴⁵⁶⁷⁸⁹]+))$`).exec(text);
  if(!scientific)return value;
  const superscripts={'⁺':'+','⁻':'-','⁰':'0','¹':'1','²':'2','³':'3','⁴':'4','⁵':'5','⁶':'6','⁷':'7','⁸':'8','⁹':'9'};
  const exponent=scientific[2]??[...scientific[3]].map(c=>superscripts[c]).join('');
  return /^[+-]?\d+$/.test(exponent)?`${scientific[1]}e${exponent}`:value;
}

function annotatedComponent(quantity,component,model,context,value) {
  let text=component.trim().replace(/＝/g,'=');
  if(quantity?.location?.kind==='member'&&quantity.component==='N')
    text=text.replace(/^轴力\s*(?=N)/i,'').replace(/^axial force(?=\s*[,，;；(（])/i,'N');
  const turn=/^(t\d+)\s*[:：]?\s+/i.exec(text);
  if(turn) {
    if(turn[1]!==context?.currentTurnId)return component;
    text=text.slice(turn[0].length);
  }
  if(quantity?.location?.kind==='node') {
    if(quantity.component==='Fz')text=text.replace(/^竖向支(?:座)?反力\s+(?=[FR]z(?:\b|[（(]))/i,'');
    text=text.replace(/^(?:global\s+|全局\s*)(?=(?:(?:support\s+(?:reaction\s+)?|reaction\s+|支座\s*))?[uFrM][xyz](?:\b|[（(]))/i,'');
    if(/^M[xyz]$/.test(quantity.component))text=text.replace(/^(?:全局)?(?:支座|支)?反力矩\s+/,'');
    if(/^F[xyz]$/.test(quantity.component))text=text.replace(/^(?:全局)?(?:支座|支)?反力\s+/,'');
    if(/^[FM][xyz]$/.test(quantity.component))text=text.replace(/^支座\s+/,'');
    if(/^F[xyz]$/.test(quantity.component)) {
      const alias=/^R([xyz])\s*(?:[（(]\s*=?\s*F([xyz])\s*[)）]|(?:\/|=)\s*F([xyz]))/i.exec(text);
      if(alias&&alias[1].toLowerCase()===(alias[2]||alias[3]).toLowerCase()
        &&alias[1].toLowerCase()===quantity.component.at(-1))text=quantity.component+text.slice(alias[0].length);
    }
  }
  const match=/^(?:(?:support\s+(?:reaction\s+)?|reaction\s+|axial\s+))?([uFrM][xyz]|N)(?=$|\s|[,，;；(（])/i.exec(text);
  if(!match)return component;
  const token=match[1],nodal=quantity?.location?.kind==='node',axial=quantity?.location?.kind==='member'&&quantity.component==='N';
  const reaction=nodal&&/^F[xyz]$/.test(quantity.component)&&/^R[xyz]$/.test(token);
  if(!(nodal||axial)||!(token.toLowerCase()===quantity.component?.toLowerCase()||reaction))return component;
  if(/^(?:support|reaction)\s/i.test(text)&&!reaction&&!/^[FM][xyz]$/.test(quantity.component))return component;
  let tail=text.slice(match[0].length).trim();
  if(!tail)return text===component?component:quantity.component;
  if(nodal&&/^[FM][xyz]$/.test(quantity.component)&&/^(?:support\s+)?reaction$/i.test(tail))return quantity.component;
  if(!/^[,，;；(（]/.test(tail))return component;
  // Parentheses may delimit individual clauses; every clause must validate.
  const clauses=tail.replace(/[()（）]/g,',').split(/[,，;；]/).map(s=>s.trim()).filter(Boolean);
  const nodeId=context?.physicalMappingVerified?context.nodeAliases?.[quantity.location.id]??quantity.location.id:quantity.location.id;
  const node=model?.nodes?.find(n=>n.id===nodeId);
  const member=axial?model?.elements?.find(e=>e.id===quantity.location.id):undefined;
  const inheritedUnit=clauses.map(c=>/(mm|m)$/.exec(c)?.[1]).filter(Boolean).at(-1);
  const n=Number(numericSpelling(String(value)));
  for(const clause of clauses) {
    if(/^t\d+$/.test(clause)) {if(clause!==context?.currentTurnId)return component;continue;}
    if(nodal&&/^(?:global|全局)$/i.test(clause))continue;
    if(nodal&&/^[FM][xyz]$/.test(quantity.component)) {
      if(/^support reaction$/i.test(clause))continue;
      if(quantity.component.startsWith('M')&&/^支(?:座)?反力矩$/.test(clause))continue;
      if(quantity.component==='Fz'&&/^竖向支(?:座)?反力$/.test(clause))continue;
      const forceAlias=/^=?\s*(?:global\s+)?([FR][xyz])(?:\s+(?:support\s+)?reaction)?$/i.exec(clause);
      if(quantity.component.startsWith('F')&&forceAlias) {
        if(forceAlias[1].at(-1).toLowerCase()!==quantity.component.at(-1))return component;
        continue;
      }
      if(quantity.component.startsWith('F')&&(/^支(?:座)?反力$/.test(clause)||clause.replace(/^=\s*/,'')===quantity.component
        ||clause===quantity.component.replace(/^F/,'R')))continue;
    }
    const rightHand=/^(?:右手绕\+([XYZ])为正|绕全局\s*\+?([XYZ])(?:为正)?|about\s+global\s*\+?([XYZ]))$/i.exec(clause);
    if(rightHand&&nodal&&/^M[xyz]$/.test(quantity.component)) {
      if((rightHand[1]||rightHand[2]||rightHand[3]).toLowerCase()!==quantity.component.at(-1))return component;
      continue;
    }
    const namedAxis=/^全局\s*\+?([XYZ])\s*(?:方向\s*)?(位移|转角|支(?:座)?反力矩|支(?:座)?反力)$/i.exec(clause);
    if(namedAxis&&nodal) {
      const kind={位移:'u',转角:'r',支反力:'F',支座反力:'F',支反力矩:'M',支座反力矩:'M'}[namedAxis[2]];
      if(quantity.component!==kind+namedAxis[1].toLowerCase())return component;
      continue;
    }
    const axis=/^(?:global\s*|全局\s*)?\+?([XYZ])\s*(为正|向上(?:为正)?|向右(?:为正)?)?$/i.exec(clause);
    if(axis&&nodal) {
      if(axis[1].toLowerCase()!==quantity.component.at(-1).toLowerCase()
        ||axis[2]?.startsWith('向上')&&axis[1].toLowerCase()!=='z'||axis[2]?.startsWith('向右')&&axis[1].toLowerCase()!=='x')return component;
      continue;
    }
    const coordinate=new RegExp(`^((?:[xyz]\\s*=\\s*)+)(${NUMBER})\\s*(mm|m)?$`,'i').exec(clause);
    if(coordinate&&nodal) {
      const unit=coordinate[3]||inheritedUnit;
      if(!node||!unit)return component;
      const v=Number(coordinate[2])*(unit==='mm'?.001:1);
      if([...coordinate[1].matchAll(/[xyz]/gi)].some(([a])=>!Number.isFinite(node[a.toLowerCase()])||Math.abs(node[a.toLowerCase()]-v)>1e-9))return component;
      continue;
    }
    if(axial) {
      if(/^(下端|上端)$/.test(clause)&&context?.physicalMappingVerified===true) {
        const ends=member?.nodes?.map(id=>model.nodes.find(n=>n.id===id));
        if(ends?.length!==2||ends.some(n=>!n))return component;
        const length=Math.hypot(...['x','y','z'].map(a=>ends[1][a]-ends[0][a]));
        const index=samePosition(quantity.location.positionM,0)&&quantity.location.side==='right'?0:
          samePosition(quantity.location.positionM,length)&&quantity.location.side==='left'?1:null;
        if(index===null||clause==='下端'&&ends[index].z>=ends[1-index].z||clause==='上端'&&ends[index].z<=ends[1-index].z)return component;
        continue;
      }
      if(/^(?:局部\s*x|local\s+x)$/i.test(clause))continue;
      const endpoints=/^(?:沿\s*)?(\S+)\s*(?:→|->)\s*(\S+)$/.exec(clause);
      if(endpoints) {
        if(member?.nodes?.[0]!==endpoints[1]||member?.nodes?.[1]!==endpoints[2])return component;
        continue;
      }
      if(clause==='截面轴力')continue;
      if(clause==='全杆恒定'&&context?.physicalMappingVerified===true) {
        const id=context.elementAliases?.[quantity.location.id]??quantity.location.id;
        const selection={...quantity.selection,id:(quantity.selection.kind==='case'?context.caseAliases:context.combinationAliases)?.[quantity.selection.id]??quantity.selection.id};
        if(unloadedAxialMember(model,id,selection))continue;
        return component;
      }
      if(/^(?:受?拉(?:力)?(?:为)?正(?:[、，,]?受?压(?:力)?(?:为)?负)?|(?:positive[\s-]+tension|tension(?:[\s-]+positive)?))$/i.test(clause))continue;
      if(/^(?:拉|拉力|受拉)$/.test(clause)&&Number.isFinite(n)&&n>0)continue;
      if(/^(?:压|受压)$/.test(clause)&&Number.isFinite(n)&&n<0)continue;
      if(/^零力$/.test(clause)&&Number.isFinite(n)&&n===0)continue;
      const length=new RegExp(`^constant over (${NUMBER}) m$`,'i').exec(clause);
      if(length) {
        const ends=member?.nodes?.map(id=>model.nodes.find(n=>n.id===id));
        if(ends?.length!==2||ends.some(n=>!n)||Math.abs(Math.hypot(...['x','y','z'].map(a=>ends[1][a]-ends[0][a]))-Number(length[1]))>1e-9)return component;
        continue;
      }
    }
    return component;
  }
  return quantity.component;
}
function componentSpelling(quantity,component,unit,model,context,value) {
  if(quantity?.location?.kind==='member'&&/^(?:N|V2|V3|T|M2|M3)$/.test(quantity.component)) {
    const local=/^(?:local|局部|截面内力)\s+(N|V2|V3|T|M2|M3)$/i.exec(component.trim());
    const moment=/^截面内力矩\s+(T|M2|M3)$/i.exec(component.trim());
    if((local||moment)?.[1].toUpperCase()===quantity.component)component=quantity.component;
    const localSuffix=/^(N|V2|V3|T|M2|M3)\s*[（(]\s*(?:local|局部)\s*[)）]$/i.exec(component.trim());
    if(localSuffix?.[1].toUpperCase()===quantity.component)component=quantity.component;
    const cut=/^(?:(?:local\s+)?section\s+)(N|V2|V3|T|M2|M3)$/i.exec(component.trim());
    if(cut&&cut[1].toUpperCase()===quantity.component)component=quantity.component;
    const internal=/^(?:local\s+)?(N|V2|V3|T|M2|M3)\s*[,，—-]\s*internal (?:section|cut)$/i.exec(component.trim());
    if(internal&&internal[1].toUpperCase()===quantity.component)component=quantity.component;
    const zeroCut=/^(N|V2|V3|T|M2|M3)\s*[,，]\s*section cut at 0\+$/i.exec(component.trim());
    if(zeroCut?.[1].toUpperCase()===quantity.component&&context?.physicalMappingVerified===true
      &&samePosition(quantity.location.positionM,0)&&quantity.location.side==='right')component=quantity.component;
    const described=/^(N|V2|V3|T|M2|M3)\s*(?:[（(]\s*(底端截面|顶端截面|下端截面内弯矩|上端截面内弯矩|根部截面内力|折点下侧|折点上侧)\s*[)）]|[—-]\s*(section immediately above base))$/i.exec(component.trim());
    if(described&&described[1].toUpperCase()===quantity.component&&context?.physicalMappingVerified===true) {
      const id=context.elementAliases?.[quantity.location.id]??quantity.location.id;
      const element=model?.elements?.find(e=>e.id===id),ends=element?.nodes?.map(id=>model.nodes.find(n=>n.id===id));
      if(ends?.length===2&&ends.every(Boolean)) {
        const length=Math.hypot(...['x','y','z'].map(a=>ends[1][a]-ends[0][a]));
        const index=quantity.location.side==='right'&&samePosition(quantity.location.positionM,0)?0:
          quantity.location.side==='left'&&samePosition(quantity.location.positionM,length)?1:null;
        const note=described[2]||described[3],lower=index!==null&&ends[index].z<ends[1-index].z;
        const root=index!==null&&model.elements.filter(e=>e.nodes?.includes(ends[index].id)).length>1
          &&model.elements.filter(e=>e.nodes?.includes(ends[1-index].id)).length===1;
        const connected=index===null?[]:model.elements.filter(e=>e.nodes?.includes(ends[index].id));
        const other=connected.length===2?connected.find(e=>e.id!==element.id):null;
        const otherEnd=other&&model.nodes.find(n=>n.id===other.nodes.find(id=>id!==ends[index].id));
        const bend=element.type==='column'&&other?.type==='column'&&otherEnd;
        if(note==='底端截面'&&lower||note==='顶端截面'&&index!==null&&ends[index].z>ends[1-index].z
          ||note==='下端截面内弯矩'&&/^M[23]$/.test(quantity.component)&&lower
          ||note==='上端截面内弯矩'&&/^M[23]$/.test(quantity.component)&&index!==null&&ends[index].z>ends[1-index].z
          ||note==='根部截面内力'&&root||note==='section immediately above base'&&lower&&ends[index].restraints?.[2]===true
          ||note==='折点下侧'&&bend&&ends[1-index].z<ends[index].z&&otherEnd.z>ends[index].z
          ||note==='折点上侧'&&bend&&ends[1-index].z>ends[index].z&&otherEnd.z<ends[index].z)component=quantity.component;
      }
    }
  }
  component=annotatedComponent(quantity,component,model,context,value);
  // Redundant global-axis notes are accepted only for a nodal component and
  // only when the named positive axis agrees with that component. Conflicting
  // directions remain visible to the strict scorer.
  const nodalAction=quantity?.location?.kind==='node'&&/^[FM][xyz]$/.test(quantity.component);
  if(nodalAction)component=component.replace(/^(?:support\s+(?:reaction\s+)?|reaction\s+)/i,'');
  const decorated=/^([A-Za-z][A-Za-z0-9]*)\s*(?:[,，]\s*([^()（）]+)|[（(]\s*([^()（）]+)\s*[)）])$/i.exec(component);
  if(decorated&&quantity?.location?.kind==='node'&&/^[uFrM][xyz]$/i.test(quantity.component)
    &&(!/^Reaction\s/i.test(component)||/^[FM][xyz]$/.test(quantity.component))) {
    let note=(decorated[2]??decorated[3]).trim();
    if(nodalAction&&quantity.component.startsWith('M'))note=note.replace(/^支座反力矩\s*[,，]\s*/,'');
    if(nodalAction&&quantity.component.startsWith('F'))note=note.replace(/^支座反力\s*[,，]\s*/,'');
    const axis=/^(?:global|全局)\s*\+?([XYZ])\s*(?:为正)?$/i.exec(note)?.[1];
    if(axis?.toLowerCase()===quantity.component.at(-1).toLowerCase())component=decorated[1];
  }
  // Public engineering prompts call a support reaction Rx/Ry/Rz. Distinguish
  // that force from rotational rx/ry/rz by the node selector and force unit.
  if(quantity?.location?.kind==='node'&&/^F[xyz]$/.test(quantity.component)
    &&/^r[xyz]$/i.test(component)&&component.slice(1).toLowerCase()===quantity.component.slice(1).toLowerCase()
    &&['kN','N'].includes(unit))return quantity.component;
  return component;
}
function mappedAlias(id,mapping,publicIds,context) {
  const alias=context?.physicalMappingVerified===true?mapping?.[id]:undefined;
  return typeof alias==='string'&&alias!==id&&Array.isArray(publicIds)&&!publicIds.includes(alias)?alias:undefined;
}
function selectionSpelling(quantity,selection,context) {
  const annotated=/^(.*?)\s*[（(](t\d+)[)）]$/.exec(selection);
  if(annotated&&annotated[2]===context?.currentTurnId)selection=annotated[1].trim();
  const kind=quantity?.selection?.kind,id=quantity?.selection?.id;
  if(context?.physicalMappingVerified===true&&context.selectionEquivalences?.[`${kind}:${id}`]?.includes(selection))return `${kind}:${id}`;
  const alias=kind==='case'?mappedAlias(id,context?.caseAliases,context?.publicCaseIds,context)
    :mappedAlias(id,context?.combinationAliases,context?.publicCombinationIds,context);
  return alias&&selection===`${kind}:${alias}`?`${kind}:${id}`:selection;
}
function locationSpelling(quantity,location,model,context) {
  if(quantity?.location?.kind!=='node')return location;
  const alias=mappedAlias(quantity.location.id,context?.nodeAliases,context?.publicNodeIds,context);
  if(alias&&location===alias)return quantity.location.id;
  if(!model)return location;
  const annotated=/^(.+?)\s*[（(]([^()（）]+)[)）]$/.exec(location);
  if(!annotated||![quantity.location.id,alias].filter(Boolean).includes(annotated[1].trim()))return location;
  const actualId=alias||quantity.location.id;
  const node=model.nodes?.find(n=>n.id===actualId);
  if(!node)return location;
  const connected=model.elements?.filter(e=>e.nodes?.includes(actualId))||[],truss=connected.every(e=>['truss','brace'].includes(e.type));
  const active=model.coordinate_system?.dimension==='2d'?[0,2,...(truss?[]:[4])]:[0,1,2,...(truss?[]:[3,4,5])];
  const support=n=>active.some(i=>i<3&&n.restraints?.[i]===true);
  // Only a connected, horizontal beam chain proves a left/right support or
  // span midpoint. A distant support in another frame is not such evidence.
  function spanNodes() {
    const ids=new Set([actualId]);let changed=true;
    while(changed) {
      changed=false;
      for(const e of model.elements||[]) {
        const ends=e.nodes?.map(id=>model.nodes.find(n=>n.id===id));
        if(e.type!=='beam'||ends?.length!==2||ends.some(n=>!n||Math.abs(n.y-node.y)>1e-9||Math.abs(n.z-node.z)>1e-9))continue;
        if(ends.some(n=>ids.has(n.id)))for(const n of ends)if(!ids.has(n.id)){ids.add(n.id);changed=true;}
      }
    }
    return model.nodes.filter(n=>ids.has(n.id));
  }
  for(const clause of annotated[2].split(/[,，;；]/).map(s=>s.trim())) {
    const coordinate=new RegExp(`^([xyz])\\s*=\\s*(${NUMBER})\\s*(mm|m)?$`,'i').exec(clause.replace(/−/g,'-'));
    if(coordinate) {
      // Zero has the same physical coordinate in either length unit. Nonzero
      // bare numbers retain the strict requirement for an explicit unit.
      const value=Number(coordinate[2])*(coordinate[3]?.toLowerCase()==='mm'?.001:1);
      if(!coordinate[3]&&value!==0||!Number.isFinite(node[coordinate[1].toLowerCase()])
        ||Math.abs(node[coordinate[1].toLowerCase()]-value)>1e-9)return location;
      continue;
    }
    const free=/^(左|右)?自由端$/.exec(clause)||/^(left |right )?free end$/i.exec(clause);
    if(free) {
      if(connected.length!==1||active.some(i=>node.restraints?.[i]===true))return location;
      const nodes=spanNodes(),direction=free[1]?.trim().toLowerCase();
      if(direction&&(nodes.length<2||((direction==='左'||direction==='left')
        ?nodes.some(n=>n.x<node.x-1e-9):nodes.some(n=>n.x>node.x+1e-9))))return location;
      continue;
    }
    const supported=/^(左|右)?支座$/.exec(clause)||/^(left |right )?support$/i.exec(clause);
    if(supported) {
      if(!support(node))return location;
      const nodes=spanNodes().filter(support),direction=supported[1]?.trim().toLowerCase();
      if(direction&&(nodes.length<2||((direction==='左'||direction==='left')
        ?nodes.some(n=>n.x<node.x-1e-9):nodes.some(n=>n.x>node.x+1e-9))))return location;
      continue;
    }
    if(/^(?:支承)?跨中$|^midspan$/i.test(clause)) {
      const supports=spanNodes().filter(support),left=supports.filter(n=>n.x<node.x-1e-9).sort((a,b)=>b.x-a.x)[0],right=supports.filter(n=>n.x>node.x+1e-9).sort((a,b)=>a.x-b.x)[0];
      if(!left||!right||support(node)||Math.abs(node.x-(left.x+right.x)/2)>1e-9)return location;
      continue;
    }
    return location;
  }
  return quantity.location.id;
}

function verifiedHistoricalRows(markdown,context={}) {
  const priorIds=new Set(context.priorTurnIds||[]),rowsByTurn=new Map();
  const rowKey=line=>{
    if(!line.trim().startsWith('|')||!line.trim().endsWith('|'))return null;
    const cells=line.trim().split('|').slice(1,-1).map(v=>v.trim());
    if(![5,6].includes(cells.length)||!cells.some(c=>/^(?:case|combination):/.test(c)))return null;
    const index=cells.length-2,numeric=numericSpelling(cells[index]);
    if(!new RegExp(`^${NUMBER}$`).test(numeric)||!Number.isFinite(Number(numeric)))return null;
    cells[index]=Number(numeric);return JSON.stringify(cells);
  };
  for(const id of priorIds) {
    const rows=new Set(),messages=context.priorResponsesByTurn?.[id]
      ||(priorIds.size===1?context.priorAssistantMessages:[])||[];
    for(const content of messages)if(typeof content==='string')for(const line of content.split(/\r?\n/)) {
      const key=rowKey(line);if(key)rows.add(key);
    }
    rowsByTurn.set(id,rows);
  }
  let historical=null,tableStarted=false;
  return markdown.split(/\r?\n/).map(line=>{
    const heading=line.trim().replace(/^[#*\s]+|[*\s]+$/g,'');
    const match=/^(?:historical(?:\s+only)?|历史(?:结果|记录|数值)?)[^|\r\n]*\b(t\d+)\b[^|\r\n]*$/i.exec(heading);
    if(match){historical=rowsByTurn.get(match[1]);tableStarted=false;return line;}
    if(historical&&line.trim().startsWith('|')) {
      tableStarted=true;const key=rowKey(line);
      return key&&historical.has(key)?'[Verified captured historical row] '+line:line;
    }
    if(historical&&(tableStarted||line.trim())){historical=false;tableStarted=false;}
    return line;
  }).join('\n');
}
function sameSelector(quantity, selection, location, component,unit,model,context,value,allowConstantAxial=true) {
  if (!['case', 'combination'].includes(quantity?.selection?.kind)
      || selectionSpelling(quantity,selection,context) !== `${quantity.selection.kind}:${quantity.selection.id}`
      || typeof quantity.component !== 'string' || componentSpelling(quantity,component,unit,model,context,value).toLowerCase() !== quantity.component.toLowerCase()) return false;
  if (quantity.location?.kind === 'node') return locationSpelling(quantity,location,model,context) === quantity.location.id;
  if (quantity.location?.kind !== 'member') return false;
  const station = MEMBER_LOCATION.exec(location);
  if(allowConstantAxial&&station&&quantity.component==='N'&&context?.physicalMappingVerified===true&&station[1]===quantity.location.id) {
    const segments=context.elementSegments?.[quantity.location.id];
    const id=context.elementAliases?.[quantity.location.id]??quantity.location.id;
    const selection={...quantity.selection,id:(quantity.selection.kind==='case'?context.caseAliases:context.combinationAliases)?.[quantity.selection.id]??quantity.selection.id};
    const proof=(!segments||segments.length===1)&&unloadedAxialMember(model,id,selection);
    // Coordinates in prose may round an endpoint to a nanometre. The signed
    // force and its frozen numerical tolerance are never rounded or changed.
    if(proof&&[Number(station[2]),quantity.location.positionM].every(x=>Number.isFinite(x)&&x>=-1e-9&&x<=proof.length+1e-9))return true;
  }
  if(station===null||station[1]!==quantity.location.id||!Number.isFinite(Number(station[2]))||station[3]!==quantity.location.side)return false;
  if(samePosition(Number(station[2]),quantity.location.positionM))return true;
  // Public endpoint coordinates can be printed to twelve significant digits.
  // Prove both expressions describe the actual member end; never snap an
  // interior cut to a neighbouring plotted sample.
  if(context?.physicalMappingVerified!==true||station[3]!=='left')return false;
  const id=context.elementAliases?.[quantity.location.id]??quantity.location.id;
  const segments=context.elementSegments?.[quantity.location.id];
  if(segments&&segments.length!==1)return false;
  const e=model?.elements?.find(e=>e.id===id),ends=e?.nodes?.map(id=>model.nodes.find(n=>n.id===id));
  if(ends?.length!==2||ends.some(n=>!n))return false;
  const length=Math.hypot(...['x','y','z'].map(a=>ends[1][a]-ends[0][a]));
  const endpoint=value=>{
    if(samePosition(Number(value),length))return true;
    const digits=String(value).split(/[eE]/)[0].replace(/\D/g,'').replace(/^0+/,'').length;
    const step=10**(Math.floor(Math.log10(Number(value)))-digits+1);
    return digits>=12&&Math.abs(Number(value)-length)<=step/2+8*Number.EPSILON*length;
  };
  return endpoint(quantity.location.positionM)&&endpoint(station[2]);
}

function normalizeEndActionRows(markdown,quantities,model,context) {
  if(context?.physicalMappingVerified!==true||!context.endActionCompatibleMembers?.length)return {markdown,conversions:[]};
  const lines=markdown.split(/\r?\n/),rows=lines.map(line=>{
    if(!line.trim().startsWith('|')||!line.trim().endsWith('|'))return null;
    const cells=line.trim().split('|').slice(1,-1).map(c=>c.trim());
    return [5,6].includes(cells.length)?cells:null;
  });
  const directives=new Set();
  for(const line of lines.filter((_,i)=>!rows[i])) {
    const plain=line.replace(/\*\*/g,'');
    for(const m of plain.matchAll(/\b(N|V2|V3|T|M2|M3)\s*(?:按(?:求解器)?局部(?:轴向)?端部(?:抗力|抵抗力)(?:符号)?报告|为局部端部抗力|uses the solver[’']s element-end resisting-action convention about local)/g))directives.add(m[1]);
    if(/Bottom moments use the solver[’']s end-resisting-action convention\./i.test(plain))for(const token of ['M2','M3'])directives.add(token);
  }
  const conversions=[];
  rows.forEach((row,index)=>{
    if(!row)return;
    const offset=row.length-5,[selection,location,component,value,unit]=row.slice(offset);
    const labelled=/^(N|V2|V3|T|M2|M3)\s*(?:[（(](?:柱)?(底端|顶端|下端|上端|起端|末端)(?:杆端)?(?:抵抗力(?:矩)?|抗力(?:矩)?)[)）]|[,，]\s*(lower|upper|start|end|i|j) end action|[,，—-]\s*(?:local )?end resisting action)$/i.exec(component);
    const bare=/^(?:local\s+)?(N|V2|V3|T|M2|M3)$/i.exec(component)?.[1].toUpperCase();
    const token=labelled?.[1].toUpperCase()??(directives.has(bare)?bare:null);
    const station=MEMBER_LOCATION.exec(location),numeric=numericSpelling(value);
    if(!token||!station||!new RegExp(`^${NUMBER}$`).test(numeric)||!Number.isFinite(Number(numeric)))return;
    const matches=quantities.filter(q=>q.component===token&&q.location?.kind==='member'
      &&context.endActionCompatibleMembers.includes(q.location.id)&&station[1]===q.location.id
      &&samePosition(Number(station[2]),q.location.positionM)&&station[3]===q.location.side
      &&selectionSpelling(q,selection,context)===`${q.selection.kind}:${q.selection.id}`);
    if(matches.length!==1)return;
    const q=matches[0],id=context.elementAliases?.[q.location.id]??q.location.id;
    if(offset===1&&row[0]!==q.id)return;
    const element=model.elements.find(e=>e.id===id),ends=element?.nodes?.map(id=>model.nodes.find(n=>n.id===id));
    if(ends?.length!==2||ends.some(n=>!n))return;
    const length=Math.hypot(...['x','y','z'].map(a=>ends[1][a]-ends[0][a]));
    const end=samePosition(Number(station[2]),0)&&station[3]==='right'?0:
      samePosition(Number(station[2]),length)&&station[3]==='left'?1:null;
    if(end===null)return;
    const note=labelled?.[2]??labelled?.[3];
    if(note&&(/^(底端|下端|lower)$/.test(note)&&ends[end].z>=ends[1-end].z
      ||/^(顶端|上端|upper)$/.test(note)&&ends[end].z<=ends[1-end].z
      ||/^(起端|start|i)$/.test(note)&&end!==0||/^(末端|end|j)$/.test(note)&&end!==1))return;
    const firstSign=['V2','V3'].includes(token)?1:-1;
    const normalized=String((end===0?firstSign:-firstSign)*Number(numeric));
    // A separately declared section row delivers the quantity. Check the two
    // stated conventions against each other, then keep the end action distinct.
    const explicit=rows.find((other,j)=>j!==index&&other&&(()=>{
      const [s,l,c,v,u]=other.slice(other.length-5);
      const b=/^(?:local\s+)?(N|V2|V3|T|M2|M3)$/i.exec(c)?.[1].toUpperCase();
      return !directives.has(b)&&sameSelector(q,s,l,c,u,model,context,v);
    })());
    if(explicit) {
      const v=numericSpelling(explicit.at(-2)),u=explicit.at(-1);
      if(u.replace(/[·*]/g,'.')!==unit.replace(/[·*]/g,'.')||!new RegExp(`^${NUMBER}$`).test(v)
        ||Math.abs(Number(v)-Number(normalized))>1e-12*Math.max(1,Math.abs(Number(v))))throw new Error('Declared end action conflicts with its explicitly stated section result');
      const separate=row.slice();separate[offset+2]=`${token} [local end resisting action]`;
      lines[index]=`| ${separate.join(' | ')} |`;
      return;
    }
    // The corpus defines positive shear on the opposite cut face from axial
    // force/torsion/bending; use its public section convention for all six.
    const output=row.slice();output[offset+2]=token;output[offset+3]=normalized;
    lines[index]=`| ${output.join(' | ')} |`;
    conversions.push({line:index+1,quantityId:q.id,from:'local-element-end-resisting-action',to:'internal-section-action',end:end===0?'i':'j',originalValue:value,value:normalized,unit});
  });
  return {markdown:lines.join('\n'),conversions};
}

function normalizeRows(markdown, quantities,model,context) {
  const knownIds = new Set(quantities.map(quantity => quantity.id));
  return markdown.split(/\r?\n/).map(line => {
    const text = line.trim();
    if (!text.startsWith('|') || !text.endsWith('|')) return line;
    const row = text.split('|').slice(1, -1).map(cell => cell.trim());
    if (row.length !== 5 && row.length !== 6) return line;
    if(row.length===6&&row[0]==='derived')return line;
    if(row.length===6&&knownIds.has(row[0])) {
      const q=quantities.find(q=>q.id===row[0]);
      if(sameSelector(q,row[1],row[2],row[3],row[5],model,context,row[4])) {
        row[1]=selectionSpelling(q,row[1],context);row[2]=locationSpelling(q,row[2],model,context);row[3]=componentSpelling(q,row[3],row[5],model,context,row[4]);
      }
      row[4]=numericSpelling(row[4]);return `| ${row.join(' | ')} |`;
    }
    const cells = row.length === 5 ? row : row.slice(1);
    const [selection, location, component, value, unit] = cells;
    let matches = quantities.filter(quantity => sameSelector(quantity, selection, location, component,unit,model,context,value));
    // A proved equivalent identity is a fallback. A report containing both
    // case:D and combination:D must retain the author's exact selection.
    const selected=matches.filter(q=>selection.startsWith(q.selection.kind+':'));
    if(selected.length)matches=selected;
    // The same applies to constant axial force: prefer the stated cut before
    // considering an equivalent station elsewhere on the unloaded member.
    const station=MEMBER_LOCATION.exec(location);
    if(station) {
      const exact=matches.filter(q=>sameSelector(q,selection,location,component,unit,model,context,value,false));
      if(exact.length)matches=exact;
    }
    if (matches.length > 1) throw new Error(`Ambiguous clean report selector ${selection} / ${location} / ${component}; candidates: ${matches.map(q=>q.id).join(', ')}. Use an explicit published quantity ID`);
    if (matches.length !== 1) return line;
    const quantity = matches[0];
    const canonicalLocation = quantity.location.kind === 'node' ? quantity.location.id
      : `${quantity.location.id}@${quantity.location.positionM}:${quantity.location.side}`;
    // Canonicalize identity and unambiguous mathematical typography only. Never
    // compute an answer from expected values or change units or magnitudes.
    // Every repeated row remains available to the strict scorer.
    return `| ${quantity.id} | ${selectionSpelling(quantity,selection,context)} | ${canonicalLocation} | ${quantity.component} | ${numericSpelling(value)} | ${unit} |`;
  }).join('\n');
}

function operandSelector(operand, quantity) {
  if (!object(operand) || Object.keys(operand).some(key => !['selection', 'location', 'component'].includes(key))
      || !object(operand.selection) || !object(operand.location) || typeof operand.component !== 'string'
      || !['case', 'combination'].includes(operand.selection.kind)
      || Object.keys(operand.selection).some(key => !['kind', 'id'].includes(key))) return false;
  const location = operand.location;
  const locationFields = location.kind === 'node' ? ['kind', 'id'] : ['kind', 'id', 'positionM', 'side'];
  if (!['node', 'member'].includes(location.kind) || Object.keys(location).some(key => !locationFields.includes(key))) return false;
  return operand.selection.kind === quantity.selection?.kind && operand.selection.id === quantity.selection.id
    && location.kind === quantity.location?.kind && location.id === quantity.location.id
    && typeof quantity.component === 'string' && operand.component.toLowerCase() === quantity.component.toLowerCase()
    && (location.kind === 'node' || (Number.isFinite(location.positionM) && location.positionM === quantity.location.positionM
      && ['left', 'right'].includes(location.side) && location.side === quantity.location.side));
}

function operandId(operand, quantities, definitions) {
  const matches = quantities.filter(quantity => typeof operand === 'string'
    ? operand === quantity.id || operand === quantity.location?.id : operandSelector(operand, quantity)).map(quantity => quantity.id);
  // Published derived IDs may be operands of a nested public definition. A
  // descriptive alias never invents an intermediate calculation identity.
  if (typeof operand === 'string') matches.push(...definitions.filter(definition => definition.id === operand).map(definition => definition.id));
  if (matches.length > 1) throw new Error('Ambiguous public derived operand; provide exact selection, location and component');
  if (matches.length !== 1) throw new Error('Unknown or inconsistent public derived operand selector');
  return matches[0];
}

function sameOperands(operation, left, right) {
  if (!Array.isArray(left) || left.length !== right.length) return false;
  const a = operation === 'difference' ? left : [...left].sort();
  const b = operation === 'difference' ? right : [...right].sort();
  return a.every((id, index) => id === b[index]);
}

function normalizeDerived(rows, quantities, definitions, requiredIds,context) {
  if (rows === undefined) return rows;
  if (!Array.isArray(rows)) throw new Error('Clean derived report must be an array');
  // Additional calculations are not requested outputs. With no published
  // derived definition, retain them unchanged without invalidating the
  // independently checked primitive result table.
  if(!definitions.length&&!requiredIds.length)return rows;
  const known = new Set(definitions.map(definition => definition.id));
  const required = [...new Set(requiredIds)].filter(id => known.has(id));
  return rows.map(row => {
    if (!object(row) || !['unit', 'governingOperand', 'governingSelection'].every(key => Object.hasOwn(row, key))) {
      throw new Error('Clean derived report requires unit and governing identity/selection fields');
    }
    if (Object.hasOwn(row, 'operation') || Object.hasOwn(row, 'operands')) {
      if (!['difference', 'sum', 'max', 'min', 'max_abs'].includes(row.operation) || !Array.isArray(row.operands) || !row.operands.length) {
        throw new Error('Derived semantic selector requires a supported operation and public operands');
      }
      const operands = row.operands.map(operand => operandId(operand, quantities, definitions));
      const matches = definitions.filter(definition => (known.has(row.id) ? definition.id === row.id : required.includes(definition.id))
        && definition.operation === row.operation && (sameOperands(row.operation, definition.operands, operands)
          ||context?.physicalMappingVerified===true&&context.equilibriumDifferenceIds?.includes(definition.id)
          &&row.operation==='difference'&&sameOperands('sum',definition.operands,operands)));
      if (matches.length > 1) throw new Error('Ambiguous derived semantic definition; provide an explicit published ID');
      if (matches.length !== 1) throw new Error('Derived operation/operand selector conflicts with its required definition or ID');
      return { ...row, id: matches[0].id };
    }
    if (known.has(row.id)) return { ...row };
    if (required.length !== 1 || rows.length !== 1) throw new Error('Ambiguous derived ID alias; supply explicit published derived IDs');
    return { ...row, id: required[0] };
  });
}

/** Public response adapter. It never reads independently expected response values. */
function normalizeCleanReport(report, quantities = [], derived = [], requiredDerivedIds = derived.map(definition => definition.id),model,context) {
  if (!object(report)) throw new Error('Clean report must be an object');
  const converted=normalizeEndActionRows(verifiedHistoricalRows(typeof report.markdown === 'string' ? report.markdown : '',context),quantities,model,context);
  const markdown = normalizeRows(converted.markdown, quantities,model,context);
  const known=new Set(derived.map(d=>d.id)),rows=report.derivedQuantities;
  // Explicitly separate supplementary calculations only when every requested
  // derived ID is delivered. Missing, ambiguous and duplicate required rows
  // still fail their existing strict checks; no result is invented or filled.
  const complete=Array.isArray(rows)&&requiredDerivedIds.length>0&&requiredDerivedIds.every(id=>rows.some(r=>r?.id===id));
  const supplemental=r=>complete&&object(r)&&typeof r.id==='string'&&r.id&&!known.has(r.id)&&!Object.hasOwn(r,'operands');
  const additionalCalculations=Array.isArray(rows)?rows.filter(supplemental):[];
  const derivedQuantities = normalizeDerived(Array.isArray(rows)?rows.filter(r=>!supplemental(r)):rows, quantities, derived, requiredDerivedIds,context);
  return { ...report, markdown, ...(additionalCalculations.length?{unrequestedDerivedQuantities:additionalCalculations}:{}),...(converted.conversions.length?{conventionNormalizations:converted.conversions}:{}),...(derivedQuantities === undefined ? {} : { derivedQuantities }) };
}

module.exports = { normalizeCleanReport };
