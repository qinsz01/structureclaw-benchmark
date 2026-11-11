#!/usr/bin/env node
'use strict';
// Input routing for the frozen legacy replay. Its source bytes stay unchanged.
const fs=require('node:fs'),path=require('node:path');
const {main:replay}=require('./replay_input_precheck_v2.cjs');
function main(argv=process.argv.slice(2)){
  const args=[...argv],index=args.indexOf('--archive-root');
  let archive=process.env.SCLAW_BENCH_ARCHIVE;
  if(index>=0){if(!args[index+1])throw Error('--archive-root requires a directory');archive=args[index+1];args.splice(index,2);}
  if(!archive)throw Error('Set --archive-root or SCLAW_BENCH_ARCHIVE');
  archive=path.resolve(archive);
  const out=args.indexOf('--out');
  if(out>=0){
    if(!args[out+1])throw Error('--out requires a file');
    const output=path.resolve(args[out+1]);
    const resolved=path.join(fs.realpathSync(path.dirname(output)),path.basename(output));
    const relative=path.relative(fs.realpathSync(archive),resolved);
    if(relative===''||(!relative.startsWith('..'+path.sep)&&relative!=='..'&&!path.isAbsolute(relative)))throw Error('Output must be outside the read-only archive');
  }
  const root=path.resolve(__dirname,'../..'),prefix=path.join(root,'docs/implementation/reviews/backend-and-codex-precheck-20261026');
  const original=fs.readFileSync;
  fs.readFileSync=function(file,...options){
    if(typeof file==='string'){
      const relative=path.relative(prefix,path.resolve(file));
      if(relative===''||(!relative.startsWith('..'+path.sep)&&relative!=='..'&&!path.isAbsolute(relative)))file=path.join(archive,path.relative(root,prefix),relative);
    }
    return original.call(this,file,...options);
  };
  try{return replay(args);}finally{fs.readFileSync=original;}
}
if(require.main===module)try{
  const result=main();console.log(JSON.stringify({scope:result.scope,summary:result.summary,acceptanceWritten:false,modelCalls:0},null,2));
}catch(error){console.error(error.message);process.exitCode=1;}
module.exports={main};
