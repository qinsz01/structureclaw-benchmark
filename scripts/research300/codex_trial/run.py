"""Run public-only Codex candidates with real persistent conversations and immutable snapshots."""
import argparse,concurrent.futures,datetime,hashlib,json,os,shutil,signal,subprocess,threading,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--base',type=Path,required=True);p.add_argument('--engines',default='OpenSees');p.add_argument('--cases');p.add_argument('--workers',type=int,default=6);p.add_argument('--timeout',type=int,default=1800);p.add_argument('--model',default='gpt-6.1-sol');p.add_argument('--image-python',default='/tmp/structureclaw-bench-readiness-20261026/bin/python');a=p.parse_args()
ROOT=Path(__file__).resolve().parents[3];WORK=a.work.resolve();BASE=a.base.resolve();TOOLS=BASE/'public-tools';INSTALL=Path('/home/openclaw/.npm-global/lib/node_modules/@openai/codex')
public_tools=json.loads((TOOLS/'manifest.json').read_text())
assert {r['path'] for r in public_tools['files']}=={'analyze.py','structure_model_v2.py'},'Public tool installation incomplete'
for row in public_tools['files']:
 assert hashlib.sha256((TOOLS/row['path']).read_bytes()).hexdigest()==row['sha256'],'Public tool source changed'
binding_file=WORK/'corpus-binding.json'
corpus_binding=json.loads(binding_file.read_text()) if binding_file.exists() else {'root':str(ROOT),'contexts':[]}
CORPUS=Path(corpus_binding['root']).resolve()
for bound in corpus_binding['contexts']:
 context=BASE/bound['caseId']/'t1/capture-context.json'
 assert hashlib.sha256(context.read_bytes()).hexdigest()==bound['sha256'],'Prepared context changed'
plan=json.loads((WORK/'plan.json').read_text());chosen=[c for c in plan if c['engine'] in a.engines.split(',') and (not a.cases or c['caseId'] in a.cases.split(','))];(WORK/'runs').mkdir(exist_ok=True);lock=threading.Lock();stop=threading.Event();processes={}
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def write(path,value):
 tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');tmp.replace(path)
def emit(value):
 with lock:
  value={'at':now(),**value}
  with (WORK/('dispatch-'+a.engines.replace(',','-')+'.jsonl')).open('a') as f:f.write(json.dumps(value)+'\n')
  print(json.dumps(value),flush=True)
def onstop(*_):
 stop.set()
 with lock:
  for proc in processes.values():
   if proc.poll() is None:os.killpg(proc.pid,signal.SIGTERM)
signal.signal(signal.SIGTERM,onstop);signal.signal(signal.SIGINT,onstop)
def toml(value):return '{'+','.join(json.dumps(k)+'='+json.dumps(v) for k,v in value.items())+'}'
def run_case(case):
 caseid=case['caseId'];destination=WORK/'runs'/caseid;destination.mkdir(exist_ok=True);case_receipt=destination/'case-execution.json'
 if case_receipt.exists():emit({'event':'already-captured','caseId':caseid});return
 if any(destination.glob('t*/dispatch.json')):emit({'event':'needs-explicit-recovery','caseId':caseid,'reason':'Prior incomplete case capture is retained; no silent rerun'});return
 thread=None;results=[];status='captured';case_started=now()
 for turn in case['turns']:
  if stop.is_set():status='interrupted';break
  turnid=turn['id'];public=Path(turn['publicDir']);directory=destination/turnid
  # The separate coordinator prepares all stages, each mounted only on release.
  deadline=time.monotonic()+3600
  while not (public/'index.json').exists():
   if stop.is_set() or time.monotonic()>deadline:raise RuntimeError('Current public task not prepared: '+str(public))
   time.sleep(.5)
  scratch=BASE/caseid/'scratch';(scratch/'requests').mkdir(parents=True,exist_ok=True);(BASE/caseid/'solver-replies').mkdir(exist_ok=True);directory.mkdir()
  access={':root':'deny',':minimal':'read',str(INSTALL):'read',str(Path(a.image_python).parent.parent):'read',str(public):'read',str(TOOLS):'read',str(scratch):'write',str(BASE/caseid/'solver-replies'):'read'}
  config=['-c','default_permissions="bench-candidate"','-c','permissions.bench-candidate.filesystem='+toml(access),'-c','permissions.bench-candidate.network.enabled=false','-c','approval_policy="never"','-c','project_doc_max_bytes=0','-c','web_search="disabled"','-c','model_reasoning_effort="high"','-c','shell_environment_policy.inherit="core"','-c','shell_environment_policy.include_only=["PATH","LANG","LC_ALL","TMPDIR"]','-c','shell_environment_policy.set='+toml({'LANG':'C.UTF-8','PYTHONNOUSERSITE':'1'})]
  future=next((t['publicDir']+'/index.json' for t in case['turns'] if t['id']!=turnid and case['turns'].index(t)>case['turns'].index(turn)),str(BASE/'another-case/index.json'))
  blocked=[str(CORPUS/'corpora/research-300/cases'/caseid/'model-state-1.json'),str(ROOT/'corpora/research-300/cases'/caseid/'model-state-1.json'),turn['context'],future,'/home/openclaw/.codex/config.toml']
  readable=[str(public/'index.json'),str(TOOLS/'analyze.py'),str(TOOLS/'structure_model_v2.py')]
  code='import json,socket;from pathlib import Path;r=[]\nfor p in '+repr([*readable,*blocked])+':\n try:r.append({"path":p,"readable":bool(Path(p).read_bytes())})\n except OSError:r.append({"path":p,"readable":False})\ntry:\n socket.create_connection(("1.1.1.1",443),timeout=1);r.append({"networkAccessible":True})\nexcept OSError:r.append({"networkAccessible":False})\nprint(json.dumps(r))'
  probe=subprocess.run(['codex','sandbox','-C',str(public),'-P','bench-candidate',*config,'/usr/bin/python3','-c',code],capture_output=True,text=True,timeout=30)
  write(directory/'isolation.json',{'exitCode':probe.returncode,'stdout':probe.stdout,'stderr':probe.stderr});assert probe.returncode==0,probe.stderr
  checked=json.loads(probe.stdout);assert all(r['readable'] for r in checked[:len(readable)]) and not any(r.get('readable',False) for r in checked[len(readable):]) and not checked[-1]['networkAccessible']
  prompt=f'''You are the candidate structural engineering agent in a real engineering task, case {caseid}, turn {turnid}. Read README.md, cases/{caseid}/task.json and the supplied public attachments. Follow the CURRENT turn while retaining the earlier conversation. Do not read later tasks, hidden models, references, evaluation contexts or scoring code. No benchmark answer or feedback is available to you.
Use only {scratch} for files. The designated real solver is {case['engine']}. Invoke the provided tool:
python3 {TOOLS}/analyze.py --model YOUR_MODEL_JSON --selection case:CASE_ID --session {BASE/caseid} --output-state {scratch}/state-{turnid}.json
Use combination:ID for a combination. The tool validates YOUR model and executes the actual designated engine; it supplies no model, answer table or figures. Inspect its actual results, then produce your engineering answer. Each execution has its own runId, retained native evidence and selection. Multiple calls writing the SAME output-state retain other selections only for an identical physical model. Changing the model invalidates old selections. Run all cases/combinations requested on this turn. If a task explicitly permits reusing unchanged results, copy the previous actual state to the current state file and query that state; do not fabricate a new run.
Save your own model at {scratch}/model-{turnid}.json and the final current model/result at {scratch}/state-{turnid}.json. Preserve the actual tool output's model, analysisResult and native execution metadata. Parsing helpers should select needed fields/samples rather than print entire raw result arrays.
Model API: StructureModelV2 schema_version="2.2.0", unit_system="SI". Global-z-up coordinate_system; 2d plane="xz", 3d plane=null; dof_order=["ux","uy","uz","rx","ry","rz"]. Use nodes[id,x,y,z,restraints], elements[id,type,nodes:[start,end],material,section], materials[id,name,E,G,nu,rho], sections[id,name,type,properties:{{A,Iy,Iz,J}}], load_cases[id,loads], load_combinations[id,factors], analysis_control and 3D element reference vectors as required. Units: coordinates m, E/G MPa, forces kN, moments kN.m, A m2, I/J m4; optional shape dimensions mm. Element-local axes and signs follow the public task. Full API documentation may be read at {TOOLS}/structure_model_v2.py; it is NOT a solver or case template. Use {a.image_python} for PIL/DXF/numerical helper scripts.
If essential data are missing or conflicting, ask a targeted clarification BEFORE analysis and do not invent the value. Read actual images/DXF where supplied. A later stage supplies its own correction. Preserve original unrelated loads/geometry during edits and undo only the requested edit.
Deliver ALL CURRENT requested signed results, units, locations and case/combination selections using README.md's Markdown table. Include required derived quantities with their signed governing operand and selection, in the specified JSON/table format. Check equilibrium. A query/unit conversion does not change physical loads or geometry.
If the current task requests figures, generate actual PNG files from YOUR model and actual results in scratch, with supports, loads, IDs, units and signs. Add figures to the current state with descriptors {{"outputId":OUTPUT_ID,"state":1,"runId":"ACTUAL_RUN_ID","path":"relative-figure.png"}}. The applicable figure output IDs, when a figure is requested, are {json.dumps(case['figureOutputIds'])}. Generate a separate turn-specific filename. A descriptor is not a substitute for an actual image. Do not generate figures for tasks that do not request them.
Return the current engineering answer; keep the final state and files for collection. Do not claim a benchmark pass or modify grading.\n'''
  (directory/'prompt.txt').write_text(prompt)
  common=['--ignore-user-config','--ignore-rules','--skip-git-repo-check',*config,'--disable','multi_agent','--disable','hooks','--disable','apps','--disable','plugins','--enable','skip_host_skill_discovery','--model',a.model,'--json','-o',str(directory/'answer.txt')]
  command=['codex','--no-daemon','exec','-C',str(public)]+(['resume',*common,thread,'-'] if thread else [*common,'-'])
  images=sorted(str(f) for f in public.rglob('*.png'));command=command[:-1]+sum((['--image',f] for f in images),[])+command[-1:]
  dispatch={'caseId':caseid,'turnId':turnid,'engine':case['engine'],'parentThread':thread,'command':command,'promptSha256':hashlib.sha256(prompt.encode()).hexdigest(),'model':a.model,'reasoningEffort':'high','actualModelCall':True,'publicOnly':True,'startedAt':now()};write(directory/'dispatch.json',dispatch);emit({'event':'started','caseId':caseid,'turnId':turnid,'engine':case['engine']})
  start=time.monotonic();timed=False
  with (directory/'events.jsonl').open('wb') as stdout,(directory/'stderr.log').open('wb') as stderr:
   proc=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=stdout,stderr=stderr,start_new_session=True)
   with lock:processes[caseid]=proc
   try:proc.communicate(prompt.encode(),timeout=a.timeout)
   except subprocess.TimeoutExpired:
    timed=True;os.killpg(proc.pid,signal.SIGTERM)
    try:proc.wait(timeout=10)
    except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
   finally:
    with lock:processes.pop(caseid,None)
  events=[];invalid=[]
  for i,line in enumerate((directory/'events.jsonl').read_text().splitlines(),1):
   try:events.append(json.loads(line))
   except ValueError:invalid.append(i)
  current=next((e.get('thread_id') for e in events if e.get('type')=='thread.started'),thread)
  if thread and current!=thread:raise RuntimeError('Resumed thread identity differs')
  thread=current;state=scratch/f'state-{turnid}.json'
  if state.exists():shutil.copyfile(state,directory/'state.json')
  execution={'caseId':caseid,'turnId':turnid,'engine':case['engine'],'threadId':thread,'exitCode':proc.returncode,'timedOut':timed,'elapsedSeconds':round(time.monotonic()-start,2),'usage':[e.get('usage') for e in events if e.get('type')=='turn.completed'],'completedTurn':any(e.get('type')=='turn.completed' for e in events),'invalidJsonLines':invalid,'statePresent':state.exists(),'stateSha256':hashlib.sha256(state.read_bytes()).hexdigest() if state.exists() else None,'completedAt':now()};write(directory/'execution.json',execution);results.append(execution);emit({'event':'finished',**execution})
  if proc.returncode or timed or not thread or not execution['completedTurn']:status='execution_incomplete';break
 write(case_receipt,{'caseId':caseid,'engine':case['engine'],'status':status,'startedAt':case_started,'completedAt':now(),'expectedTurns':len(case['turns']),'capturedTurns':len(results),'turns':results})
 return caseid
with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as pool:
 jobs={pool.submit(run_case,c):c['caseId'] for c in chosen}
 for f in concurrent.futures.as_completed(jobs):
  try:f.result()
  except Exception as e:emit({'event':'harness_error','caseId':jobs[f],'error':str(e)})
emit({'event':'batch_complete','engines':a.engines,'casesScheduled':len(chosen),'interrupted':stop.is_set()})
