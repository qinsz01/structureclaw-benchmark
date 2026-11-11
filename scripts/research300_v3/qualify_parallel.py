"""Run disjoint v3.1 qualification case groups and verify full aggregate coverage."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib,json,subprocess
from pathlib import Path

def read(p):return json.loads(p.read_text())
def write(p,v):
 with p.open('x') as f:f.write(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def run(edition,work,output,workers=6):
 edition,work,output=[Path(p).resolve() for p in (edition,work,output)]
 if output.exists() or not 1<=workers<=16:raise ValueError('Fresh output and 1..16 workers required')
 manifest=read(edition/'manifest.json');output.mkdir(parents=True)
 groups=[[] for _ in range(workers)];cost=[0]*workers
 for c in sorted(manifest['cases'],key=lambda c:-len(c['turns'])*(5 if c['analysis']=='project' else 3 if c['analysis']=='scenario' else 1)):
  k=min(range(workers),key=cost.__getitem__);groups[k].append(c['id']);cost[k]+=len(c['turns'])*(5 if c['analysis']=='project' else 3 if c['analysis']=='scenario' else 1)
 entry=Path(__file__).with_name('qualify-v31.cjs')
 def execute(i,ids):
  selection=output/f'selection-{i:02}.json';write(selection,ids)
  target=output/f'chunk-{i:02}'
  command=['node','--max-old-space-size=4096',str(entry),'--edition',str(edition),'--work',str(work),'--output',str(target),'--case-list',str(selection)]
  with (output/f'chunk-{i:02}.log').open('x') as log:
   code=subprocess.call(command,stdout=log,stderr=subprocess.STDOUT)
  if not (target/'summary.json').exists():raise RuntimeError(f'Qualification chunk {i} ended without a summary ({code})')
  return i,read(target/'summary.json'),code
 summaries=[]
 with ThreadPoolExecutor(max_workers=workers) as pool:
  futures=[pool.submit(execute,i,ids) for i,ids in enumerate(groups) if ids]
  for future in as_completed(futures):
   i,s,code=future.result();summaries.append((i,s,code));print(json.dumps({'chunk':i,'turns':s['turns'],'allPassed':s['allPassed']}),flush=True)
 expected=[(c['id'],t['id']) for c in manifest['cases'] for t in c['turns']]
 rows=[{**r,'qualificationChunk':f'chunk-{i:02}'} for i,s,_ in summaries for r in s['rows']]
 keyed={(r['caseId'],r['turnId']):r for r in rows}
 if len(keyed)!=len(rows) or set(keyed)!=set(expected):raise ValueError('Missing or repeated qualification turn in aggregate')
 binding=summaries[0][1]['codeBinding'];edition_hash=hashlib.sha256((edition/'manifest.json').read_bytes()).hexdigest()
 if any(s['codeBinding']!=binding or s['manifestSha256']!=edition_hash for _,s,_ in summaries):raise ValueError('Qualification code/edition changed across chunks')
 result={'evaluationRevision':'v3.1','cases':len(manifest['cases']),'turns':len(rows),'passedTurns':sum(r.get('positive',False) for r in rows),
  'controls':sum(s['controls'] for _,s,_ in summaries),'controlFailed':sum(s['controlFailed'] for _,s,_ in summaries),
  'positiveFailed':sum(s['positiveFailed'] for _,s,_ in summaries),'fullEditionCoverage':True,'allPassed':all(s['allPassed'] and code==0 for _,s,code in summaries),
  'candidateCalls':0,'newNativeJobs':0,'chunks':len(summaries),'manifestSha256':edition_hash,'codeBinding':binding,'rows':[keyed[p] for p in expected]}
 write(output/'summary.json',result);return {k:v for k,v in result.items() if k!='rows'}

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for name in ['edition','work','output']:p.add_argument('--'+name,required=True,type=Path)
 p.add_argument('--workers',type=int,default=6);a=p.parse_args();r=run(a.edition,a.work,a.output,a.workers);print(json.dumps(r,indent=2));raise SystemExit(0 if r['allPassed'] else 1)
