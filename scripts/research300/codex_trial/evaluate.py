"""Collect completed real cases and invoke the existing unified offline evaluator."""
import argparse,hashlib,json,shutil,subprocess,time,uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--base',type=Path,required=True);p.add_argument('--revision',default='r1');p.add_argument('--watch',action='store_true');p.add_argument('--workers',type=int,choices=range(1,9),default=1);p.add_argument('--cases',help='Optional comma-separated case IDs for a focused regrade');a=p.parse_args()
R=Path(__file__).resolve().parents[3];W=a.work.resolve();BASE=a.base.resolve();plan=json.loads((W/'plan.json').read_text());collected=W/'collected';collected.mkdir(exist_ok=True);assessments=W/'assessments';assessments.mkdir(exist_ok=True)
binding_file=W/'corpus-binding.json';CORPUS=Path(json.loads(binding_file.read_text())['root']).resolve() if binding_file.exists() else R
if a.cases:
 selected=set(a.cases.split(','));known={c['caseId'] for c in plan}
 if selected-known:raise ValueError('Unknown requested cases: '+','.join(sorted(selected-known)))
 plan=[c for c in plan if c['caseId'] in selected]
def evaluate(case):
 caseid=case['caseId'];run=W/'runs'/caseid;receipt=run/'case-execution.json';report=assessments/(caseid+'-'+a.revision+'.json')
 if report.exists() or not receipt.exists():return
 ex=json.loads(receipt.read_text())
 if ex['status']!='captured' or ex['capturedTurns']!=ex['expectedTurns']:
  report.write_text(json.dumps({'caseId':caseid,'status':'execution_incomplete','candidateScore':None,'receipt':str(receipt),'note':'No candidate ability score is inferred from incomplete execution'},indent=2)+'\n');return
 out=collected/caseid
 if out.exists() and not (out/'states.json').exists():
  failed=W/'collection-failures';failed.mkdir(exist_ok=True);out.rename(failed/(caseid+'-'+uuid.uuid4().hex))
 if not out.exists():
  out.mkdir();events=b'';states=[]
  for turn in case['turns']:
   folder=run/turn['id'];events+=(folder/'events.jsonl').read_bytes();states.append({'turnId':turn['id'],'state':json.loads((folder/'state.json').read_text()) if (folder/'state.json').exists() else {}})
  (out/'events.jsonl').write_bytes(events);artifactroot=out/'artifacts';artifactroot.mkdir();scratch=BASE/caseid/'scratch'
  # Figure descriptors use candidate paths. Copy original bytes to the private
  # collector root; the candidate never gains access to this scoring package.
  for f in scratch.rglob('*'):
   if f.is_file() and not f.is_symlink() and f.resolve().is_relative_to(scratch.resolve()) and f.suffix.lower() in ['.png','.svg','.jpg','.jpeg','.pdf']:
    dest=artifactroot/f.relative_to(scratch);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,dest)
  cap=out/'native-captures';cap.mkdir()
  commercial={}
  for job in sorted((W/'solver-jobs'/caseid).glob('*')):
   for source in (job/'captures').glob('*'):
    if source.is_dir():shutil.copytree(source,cap/source.name)
   mapping=job/'artifact-mapping.json'
   if mapping.exists():
    m=json.loads(mapping.read_text());rid=m['runId'];commercial[rid]={}
    for key,relative in m['files'].items():
     source=job/relative;dest=artifactroot/'native'/job.name/relative;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest);commercial[rid][key]=dest.relative_to(artifactroot).as_posix()
  for turn in states:
   state=turn['state'];analysis=state.get('analysisResult') if isinstance(state,dict) else None
   analysis=analysis if isinstance(analysis,dict) else {};entries=analysis.get('results') or {};entries=entries if isinstance(entries,dict) else {}
   ids={analysis.get('runId'),*(entry.get('meta',{}).get('runId') for entry in entries.values() if isinstance(entry,dict) and isinstance(entry.get('meta',{}),dict))};mapping={key:commercial[key] for key in ids if key in commercial}
   if mapping:turn['artifacts']=mapping
  (out/'states.json').write_text(json.dumps(states,ensure_ascii=False,indent=2)+'\n')
  (out/'collection.json').write_text(json.dumps({'caseId':caseid,'stateSources':[{ 'turnId':t['id'],'path':str(run/t['id']/'state.json'),'stateEmitted':(run/t['id']/'state.json').exists()} for t in case['turns']],'eventsSha256':hashlib.sha256(events).hexdigest(),'candidateFilesCopiedWithoutEditing':True},indent=2)+'\n')
 cmd=['node',str(R/'scripts/evaluate-results.cjs'),'--root',str(CORPUS),'--format','codex','--input',str(out/'events.jsonl'),'--states',str(out/'states.json'),'--artifact-root',str(out/'artifacts'),'--context',case['turns'][0]['context'],'--capture-root',str(out/'native-captures'),'--output',str(report)]
 semantic=W/'semantic-reviews'/f'{caseid}.json'
 if semantic.exists():cmd+=['--assessments',str(semantic)]
 (out/('command-'+a.revision+'.json')).write_text(json.dumps(cmd,indent=2)+'\n')
 try:
  result=subprocess.run(cmd,capture_output=True,text=True,timeout=180);(out/('evaluation-'+a.revision+'.log')).write_text(result.stdout+result.stderr)
  if not report.exists():report.write_text(json.dumps({'caseId':caseid,'status':'import_error','candidateScore':None,'stdout':result.stdout,'stderr':result.stderr},indent=2)+'\n')
  d=json.loads(report.read_text());print(json.dumps({'caseId':caseid,'status':d['status'],'exitCode':result.returncode,'reviewRequests':len(d.get('reviewRequests',[]))}),flush=True)
 except Exception as e:print(json.dumps({'caseId':caseid,'harnessError':str(e)}),flush=True)
while True:
 with ThreadPoolExecutor(max_workers=a.workers) as pool:list(pool.map(evaluate,plan))
 rows=[]
 for c in plan:
  report=assessments/(c['caseId']+'-'+a.revision+'.json');receipt=W/'runs'/c['caseId']/'case-execution.json'
  if report.exists():
   d=json.loads(report.read_text());rows.append({'caseId':c['caseId'],'engine':c['engine'],'status':d['status'],'reviewRequests':len(d.get('reviewRequests',[])),'report':str(report)})
  elif receipt.exists():rows.append({'caseId':c['caseId'],'engine':c['engine'],'status':'captured-awaiting-evaluation'})
 summary={'casesExpected':len(plan),'turnsExpected':sum(len(c['turns']) for c in plan),'revision':a.revision,'cases':rows,'count':len(rows),'updatedAt':time.time()};tmp=W/('progress-'+a.revision+'.json.tmp');tmp.write_text(json.dumps(summary,indent=2)+'\n');tmp.replace(W/('progress-'+a.revision+'.json'))
 if not a.watch or len(rows)==len(plan):break
 time.sleep(5)
