'use strict';
// Standalone PUBLIC-ONLY table decoder copied into each packet. No repository
// imports, case-ID recipes, geometry reconstruction or hidden-answer access.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const sha256=b=>crypto.createHash('sha256').update(b).digest('hex');
const unescape=value=>value.replace(/&#(\d+);/g,(_,n)=>String.fromCodePoint(Number(n))).replace(/&quot;/g,'"').replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&amp;/g,'&');
function scalar(cell){const text=unescape(cell);try{return JSON.parse(text);}catch{return text;}}
function assign(object,parts,value){
  if(parts.some(k=>['__proto__','constructor','prototype'].includes(k)))throw Error('Unsafe public table key');
  let cursor=object;for(const key of parts.slice(0,-1)){cursor[key]??={};cursor=cursor[key];}cursor[parts.at(-1)]=value;
}
function tables(text){
  const result=[];let heading='';const lines=text.split(/\r?\n/);
  for(let i=0;i<lines.length;i++){
    if(lines[i].startsWith('## '))heading=lines[i];
    if(!lines[i].trim().startsWith('|'))continue;
    const rows=[];while(i<lines.length&&lines[i].trim().startsWith('|'))rows.push(lines[i++].trim().slice(1,-1).split('|').map(c=>c.trim()));i--;
    if(rows.length<2)throw Error('Public table lacks separator');const headers=rows[0],data=rows.slice(2);
    if(data.some(row=>row.length!==headers.length))throw Error('Public table width differs');result.push({heading,headers,rows:data});
  }return result;
}
function parseMarkdown(text){
  const parsed=tables(text),entries=[];const simple={materials:[],sections:[],elements:[]};
  for(const table of parsed){
    const {headers,rows}=table,match=table.heading.match(/\[(\/.*?)\]\s*$/);
    if(!match){
      if(headers[0]!=='ID')continue;
      for(const row of rows)for(const id of unescape(row[0]).split(', ')){
        const fields=Object.fromEntries(headers.slice(1).flatMap((h,i)=>row[i+1]==='—'?[]:[[h,scalar(row[i+1])]]));
        if(headers.includes('E'))simple.materials.push({id,...fields});
        else if(headers.includes('A'))simple.sections.push({id,properties:fields});
        else if(headers.includes('material')&&headers.includes('section'))simple.elements.push({id,...fields});
      }continue;
    }
    let value;
    if(headers.join(',')==='field,value')value=Object.fromEntries(rows.map(row=>[unescape(row[0]),scalar(row[1])]));
    else if(headers.join(',')==='index'){
      if(rows.some((row,i)=>Number(row[0])!==i))throw Error('Nonsequential public table indexes');value=rows.map(()=>({}));
    }else if(headers.join(',')==='value')value=scalar(rows[0][0]);
    else {
      value=[];for(const row of rows){const idIndex=headers.indexOf('id (each)'),ids=idIndex<0?[null]:unescape(row[idIndex]).split(', ');
        for(const id of ids){const record={};headers.forEach((header,i)=>{if(row[i]==='—'||header==='@empty')return;const field=header==='id (each)'?'id':header;assign(record,field.split('/').map(k=>k.replace(/~1/g,'/').replace(/~0/g,'~')),header==='id (each)'?id:scalar(row[i]));});value.push(record);}
      }
    }
    entries.push({path:match[1],value});
  }
  if(!entries.length)return simple;
  const result=entries.find(e=>e.path==='/')?.value||{};
  for(const entry of entries)if(entry.path!=='/')assign(result,entry.path.slice(1).split('/').map(k=>k.replace(/~1/g,'/').replace(/~0/g,'~')),entry.value);
  return result;
}
function decodePacket(directory,reviewerId,kind='agent') {
  const root=fs.realpathSync(directory),bytes=fs.readFileSync(path.join(root,'packet.json')),packet=JSON.parse(bytes);
  const model={nodes:[],elements:[],materials:[],sections:[]},sources=[];
  const read=relative=>{
    if(typeof relative!=='string'||path.isAbsolute(relative)||relative.includes('\\')||relative.split('/').some(s=>s==='..'||s==='.'||!s))throw Error('Unsafe packet path');
    const file=fs.realpathSync(path.join(root,relative));if(!file.startsWith(root+path.sep))throw Error('Packet path escapes root');
    const data=fs.readFileSync(file),entry=packet.files.find(f=>f.path===relative);
    if(!entry||entry.sha256!==sha256(data)||entry.bytes!==data.length)throw Error('Public packet file hash mismatch');return data.toString('utf8');
  };
  const mergeRows=(key,rows)=>{if(!Array.isArray(rows))return;for(const row of rows){const index=model[key].findIndex(r=>r.id===row.id);if(index<0)model[key].push(row);else model[key][index]={...model[key][index],...row};}};
  const ingestElements=rows=>{
    if(!Array.isArray(rows))return;mergeRows('elements',rows.map(v=>{
      const e={};for(const key of ['id','type','material','section','rotation_angle'])if(v[key]!==undefined)e[key]=v[key];
      if(v.referenceVector){model.metadata??={};model.metadata.elementReferenceVectors??={};model.metadata.elementReferenceVectors[v.id]=v.referenceVector;}return e;
    }));
  };
  const ingest=value=>{
    if(Array.isArray(value)){if(value.every(v=>v.id&&v.material&&v.section))ingestElements(value);return;}
    mergeRows('materials',value.materials);mergeRows('sections',value.sections);ingestElements(value.elements);
    for(const key of ['coordinate_system','analysis_control','load_cases','load_combinations'])if(value[key]!==undefined)model[key]=value[key];
    if(value.localAxes&&value.coordinate_system)model.axes={mode:value.coordinate_system.dimension==='2d'?'xz':'reference-vectors',elementDirection:'listed-node-order'};
  };
  for(const turn of packet.history)for(const file of turn.attachments){
    if(!/\.(json|txt|md|csv)$/i.test(file.path))continue;
    const text=read(file.path);sources.push(file.path);
    if(/\.json$/i.test(file.path))ingest(JSON.parse(text));
    else {
      if(/\.md$/i.test(file.path))ingest(parseMarkdown(text));
      for(const line of text.split(/\r?\n/)){
        const match=line.match(/^([\w-]+):\s*(.*)$/);if(!match)continue;
        const values={};for(const item of match[2].matchAll(/\b(E|G|nu|rho|A|Iy|Iz|J)\s*=\s*(-?\d+(?:\.\d+)?(?:e[+-]?\d+)?)/gi))values[item[1]]=Number(item[2]);
        if(values.E!==undefined)mergeRows('materials',[{id:match[1],...values}]);if(values.A!==undefined)mergeRows('sections',[{id:match[1],properties:values}]);
      }
      if(!model.coordinate_system&&/XZ (?:plane|平面)/.test(text)&&/(?:Z up|Z 向上)/.test(text))model.coordinate_system={dimension:'2d',plane:'xz',semantics:'global-z-up',dof_order:['ux','uy','uz','rx','ry','rz']};
      if(!model.axes&&/(?:local 2: global \+Y|局部2:全局\+Y)/.test(text))model.axes={mode:'xz',elementDirection:'listed-node-order',rotationDefaultDegrees:0};
      if(!model.analysis_control&&/(?:self-weight, P-delta, rigid diaphragm, rigid offsets, stiffness reductions and automatic combinations OFF|自重、P-delta、刚性楼板、刚域、刚度折减、默认组合均关闭)/.test(text))model.analysis_control={self_weight:false,rigid_floor:false,p_delta:false,rigid_offsets:false};
      if(model.analysis_control&&/(?:施工阶段保持关闭|construction.stage.*OFF)/i.test(text))model.analysis_control.construction_stage=false;
    }
  }
  return {schemaVersion:1,caseId:packet.caseId,turnId:packet.turnId,packetSha256:sha256(bytes),reviewer:{id:reviewerId,kind,independent:true},method:'public-only-reconstruction',model,unresolved:[],observations:[],decoderSources:sources};
}
if(require.main===module){
  const args=process.argv.slice(2),get=key=>args[args.indexOf(key)+1];
  if(!args.includes('--reviewer')){process.stderr.write('Usage: node decoder.cjs --reviewer SESSION_ID [--kind human|agent] [--packet DIRECTORY]\n');process.exitCode=1;}
  else try{process.stdout.write(`${JSON.stringify(decodePacket(args.includes('--packet')?get('--packet'):__dirname,get('--reviewer'),args.includes('--kind')?get('--kind'):'agent'),null,2)}\n`);}catch(error){process.stderr.write(`${error.message}\n`);process.exitCode=1;}
}
module.exports={decodePacket,parseMarkdown};
