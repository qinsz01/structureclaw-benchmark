"""Trusted solver coordinator. Candidate receives replies read-only; native evidence stays private."""
import argparse,concurrent.futures,hashlib,json,os,re,signal,subprocess,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--base',type=Path,required=True);p.add_argument('--sut',type=Path,required=True);p.add_argument('--python',required=True);p.add_argument('--workers',type=int,default=4);p.add_argument('--commercial-command');a=p.parse_args()
ROOT=Path(__file__).resolve().parents[3];WORK=a.work.resolve();BASE=a.base.resolve();SUT=a.sut.resolve();HELPERS=Path(__file__).resolve().parent
plan=json.loads((WORK/'plan.json').read_text());engines={r['caseId']:r['engine'] for r in plan};stop=False;seen=set()
def ending(*_):
 global stop
 stop=True
signal.signal(signal.SIGTERM,ending);signal.signal(signal.SIGINT,ending)
def execute(case,file):
 start=time.monotonic();jobid=file.stem;outbox=BASE/case/'solver-replies';job=WORK/'solver-jobs'/case/jobid
 try:
  if not re.fullmatch('[a-f0-9]{32}',jobid) or file.is_symlink() or file.stat().st_size>8*1024*1024:raise ValueError('Invalid spool envelope')
  raw=file.read_bytes();request=json.loads(raw)
  if set(request)!={'model','selection'} or set(request['selection'])!={'kind','id'} or request['selection']['kind'] not in ['case','combination'] or not isinstance(request['selection']['id'],str):raise ValueError('Invalid numeric model selection')
  job.mkdir(parents=True,exist_ok=False);(job/'request.json').write_bytes(raw)
  normalize="import json,sys;from structure_protocol.structure_model_v2 import StructureModelV2;print(json.dumps(StructureModelV2.model_validate(json.load(sys.stdin)).model_dump(mode='json',exclude_unset=True),allow_nan=False))"
  env={**os.environ,'PYTHONPATH':str(SUT/'backend/src/skill-shared/python'),'SCLAW_BENCH_CAPTURE_ROOT':str(job/'captures')}
  norm=subprocess.run([a.python,'-c',normalize],input=json.dumps(request['model']),capture_output=True,text=True,env=env,timeout=60);(job/'normalization.stderr.log').write_text(norm.stderr)
  if norm.returncode:raise ValueError('Model validation failed: '+norm.stderr[-5000:])
  model=json.loads(norm.stdout);(job/'model.json').write_text(norm.stdout)
  sel=request['selection'];params={'loadCaseIds':[sel['id']]} if sel['kind']=='case' else {'loadCombinationId':sel['id']}
  engine=engines[case];worker={'action':'analyze','input':{'type':'static','engineId':{'OpenSees':'builtin-opensees','PKPM':'pkpm','YJK':'yjk'}[engine],'model':model,'parameters':params}};(job/'worker-request.json').write_text(json.dumps(worker)+'\n')
  if engine=='OpenSees':
   run=subprocess.run([a.python,str(ROOT/'scripts/research300/capture_structureclaw_worker.py'),str(SUT/'backend/src/agent-skills/analysis/runtime/worker.py')],input=json.dumps(worker),capture_output=True,text=True,env=env,timeout=300)
   (job/'worker.stdout.json').write_text(run.stdout);(job/'worker.stderr.log').write_text(run.stderr)
   if run.returncode:raise ValueError('Solver worker failed: '+run.stderr[-2500:]+' '+run.stdout[-4000:])
   pack=subprocess.run(['node',str(HELPERS/'package-analysis.cjs'),str(job),str(SUT)],capture_output=True,text=True,timeout=60);(job/'packaging.stderr.log').write_text(pack.stderr)
   if pack.returncode:raise ValueError('Broker packaging failed: '+pack.stderr[-4000:])
  else:
   if not a.commercial_command:raise RuntimeError('Commercial execution service is not configured; no substitute engine used')
   r=subprocess.run([a.python,a.commercial_command,'--job',str(job),'--engine',engine,'--sut',str(SUT)],capture_output=True,text=True,timeout=1500);(job/'commercial.stdout.log').write_text(r.stdout);(job/'commercial.stderr.log').write_text(r.stderr)
   if r.returncode:
    diagnostic=job/'public-native-error.json'
    if diagnostic.is_file():raise RuntimeError('Commercial execution failed: '+diagnostic.read_text())
    raise RuntimeError('Commercial execution failed: '+r.stdout[-2000:]+' '+r.stderr[-3000:])
  reply={'ok':True,'jobId':jobid,'requestSha256':hashlib.sha256(raw).hexdigest(),'state':json.loads((job/'state.json').read_text())}
 except Exception as e:reply={'ok':False,'jobId':jobid,'error':str(e)}
 # Existing published replies are immutable, including across broker restarts.
 dest=outbox/(jobid+'.json')
 if dest.exists():raise RuntimeError('Refusing to overwrite published reply '+str(dest))
 tmp=dest.with_suffix('.tmp');tmp.write_text(json.dumps(reply,ensure_ascii=False,allow_nan=False)+'\n');tmp.replace(dest)
 (job/'broker-receipt.json').write_text(json.dumps({'caseId':case,'engine':engines[case],'jobId':jobid,'ok':reply['ok'],'error':reply.get('error'),'elapsedSeconds':round(time.monotonic()-start,3)},indent=2)+'\n')
 print(json.dumps({'caseId':case,'jobId':jobid,'ok':reply['ok'],'seconds':round(time.monotonic()-start,3),'error':reply.get('error')}),flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as pool:
 pending={}
 while not stop or pending:
  for f in list(pending):
   if f.done():
    try:f.result()
    except Exception as e:print(json.dumps({'brokerError':str(e),'source':pending[f]}),flush=True)
    del pending[f]
  if not stop:
   for case in engines:
    for file in sorted((BASE/case/'scratch/requests').glob('*.json')):
     key=str(file)
     if key in seen:continue
     if (BASE/case/'solver-replies'/file.name).exists():seen.add(key);continue
     if len(pending)>=a.workers:break
     seen.add(key);pending[pool.submit(execute,case,file)]=key
  time.sleep(.2)
print(json.dumps({'brokerStopped':True,'requestsSeen':len(seen)}),flush=True)
