#!/usr/bin/env node
'use strict';
const fs=require('node:fs'),path=require('node:path');
const review=require('../../lib/public-input-review.cjs');
function main(argv=process.argv.slice(2)) {
  const command=argv.shift(),args={};for(let i=0;i<argv.length;i+=2){if(!argv[i].startsWith('--')||!argv[i+1]||argv[i+1].startsWith('--'))throw Error('Every option needs a value');args[argv[i].slice(2)]=argv[i+1];}
  const root=path.resolve(args.root||path.resolve(__dirname,'../..'));
  if(command==='seal')return review.sealSubmission({packetDir:args.packet,submissionFile:args.submission,provenanceFile:args.provenance,outDir:args.out});
  if(!['export','grade','verify'].includes(command))throw Error('Usage: blind_input_review.cjs export|seal|grade|verify --ids MM-001,... [--turn t1|t2|all] [--out PATH] [--root ROOT]');
  const provider=require('../../lib/corpus-provider.cjs'),corpus=provider.loadCorpus({corpus:'research-300',root});
  const ids=args.ids?args.ids.split(','):corpus.cases.filter(c=>c.id.startsWith('MM-')).map(c=>c.id);
  if(!ids.length||new Set(ids).size!==ids.length||ids.some(id=>!/^MM-(00[1-9]|0[1-9][0-9]|100)$/.test(id)))throw Error('Invalid or duplicate --ids');
  if(command==='grade'&&ids.length!==1)throw Error('Grade one case at a time with all its sealed turn evidence');
  return ids.flatMap(id=>{
    const record=provider.loadCase(corpus,id);
    if(command==='export'){
      if(!args.out)throw Error('Export requires --out');const selected=args.turn||'t1';
      const indices=record.contract.turns.flatMap((turn,i)=>selected==='all'||turn.id===selected?[i]:[]);
      if(!indices.length)throw Error(`No ${selected} for ${id}`);
      return indices.map(i=>review.exportPacket(record,i,path.join(path.resolve(args.out),id,record.contract.turns[i].id)));
    }
    if(command==='grade'){
      if(!args.evidence)throw Error('Grade requires --evidence directory[,directory]');
      const receipts=args.evidence.split(',').map(dir=>path.relative(root,path.resolve(dir.endsWith('receipt.json')?dir:path.join(dir,'receipt.json'))).split(path.sep).join('/'));
      const report=review.gradeEvidence(record,receipts),out=args.out?path.resolve(args.out):review.reviewPath(record,report.inputBinding);
      fs.mkdirSync(path.dirname(out),{recursive:true});fs.writeFileSync(out,review.jsonBytes(report));return {caseId:id,status:report.status,report:out,coverage:report.coverage,findings:report.findings};
    }
    const input=provider.getPublicTurnInput(record,0);return review.getPublicInputReview(record,input.inputBinding);
  });
}
if(require.main===module)try{process.stdout.write(`${JSON.stringify(main(),null,2)}\n`);}catch(error){process.stderr.write(`${error.message}\n`);process.exitCode=1;}
module.exports={main};
