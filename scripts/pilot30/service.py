"""Reference-free numeric broker; only submitted models reach the pinned SUT."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
import uuid

ROOT=Path(__file__).resolve().parents[2]
HELPERS=ROOT/'scripts/research300/codex_trial'


def read(p):return json.loads(p.read_text())
def save(p,v):
    with p.open('x') as f:f.write(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def digest(v):return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def command(args,job,label,**kwargs):
    p=subprocess.run(args,capture_output=True,text=True,timeout=kwargs.pop('timeout',300),**kwargs)
    (job/(label+'.stdout')).write_text(p.stdout);(job/(label+'.stderr')).write_text(p.stderr)
    if p.returncode:raise RuntimeError(label+' failed: '+p.stderr[-2500:]+' '+p.stdout[-3000:])
    return p


def execute(request,job,sut,engine,role='oracle',binding=None):
    if set(request)-{'model','analysis','selection','parameters'}:raise ValueError('Unknown request fields')
    analysis=request.get('analysis','static')
    if analysis not in ['static','modal','transient']:raise ValueError('Unknown analysis')
    if engine!='OpenSees' and analysis!='static':raise ValueError('Commercial pilot supports static only')
    save(job/'request.json',request)
    env={**os.environ,'PYTHONPATH':str(sut/'backend/src/skill-shared/python'),
         'SCLAW_BENCH_CAPTURE_ROOT':str(job/'captures'),'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','PYTHONDONTWRITEBYTECODE':'1'}
    code='import json,sys;from structure_protocol.structure_model_v2 import StructureModelV2;print(json.dumps(StructureModelV2.model_validate(json.load(sys.stdin)).model_dump(mode="json",exclude_unset=True),allow_nan=False))'
    norm=command([sys.executable,'-c',code],job,'normalization',input=json.dumps(request['model']),env=env)
    model=json.loads(norm.stdout);save(job/'model.json',model)
    if analysis=='static':
        selection=request.get('selection')
        if not isinstance(selection,dict) or set(selection)!={'kind','id'} or selection['kind'] not in ['case','combination']:raise ValueError('Explicit static selection required')
        if request.get('parameters'):raise ValueError('Static parameters are determined by explicit selection')
        parameters={'loadCaseIds':[selection['id']]} if selection['kind']=='case' else {'loadCombinationId':selection['id']}
    else:
        parameters=request.get('parameters',{})
        if request.get('selection') is not None:raise ValueError('Dynamic request has no static selection')
        expected='modal' if analysis=='modal' else 'time_history'
        if parameters.get('analysisType')!=expected:raise ValueError('Explicit analysisType required')
    worker={'action':'analyze','input':{'type':'static' if analysis=='static' else 'dynamic',
              'engineId':{'OpenSees':'builtin-opensees','PKPM':'pkpm','YJK':'yjk'}[engine], 'model':model,'parameters':parameters}}
    save(job/'worker-request.json',worker)
    if engine=='OpenSees':
        run=command([sys.executable,str(ROOT/'scripts/research300/capture_structureclaw_worker.py'),
                     str(sut/'backend/src/agent-skills/analysis/runtime/worker.py')],job,'worker',input=json.dumps(worker),env=env)
        raw=json.loads(run.stdout)
        if not raw.get('ok') or not raw.get('data',{}).get('success'):raise ValueError('Production worker rejected request: '+run.stdout[-5000:])
        (job/'worker.stdout.json').write_text(run.stdout)
        if analysis=='static':
            command(['node',str(HELPERS/'package-analysis.cjs'),str(job),str(sut)],job,'packaging',timeout=60)
        else:
            state={'model':model,'dynamicResult':{'analysis':analysis,'parameters':parameters,'data':raw['data']['data'],
                    'meta':{'runId':uuid.uuid4().hex,'engineId':'builtin-opensees','modelHash':digest(model),'settingsHash':digest(parameters)}}}
            save(job/'state.json',state)
    else:
        args=[sys.executable,str(HELPERS/'commercial.py'),'--job',str(job),'--engine',engine,'--sut',str(sut)]
        if role=='oracle':
            # Only execution identity is bound here; never any expected values.
            ref={'caseId':job.parent.name,'engine':engine,'executionRole':'reference-verification',
                 'state':binding['state'],'sourceHash':binding['sourceHash']}
            save(job/'reference-binding.json',ref);args+=['--reference-binding',str(job/'reference-binding.json')]
        command(args,job,'commercial',timeout=1500)
    state=read(job/'state.json')
    return {'ok':True,'jobId':job.name,'state':state}


def serve(work,base,sut,role,workers):
    plan=read(work/'plan.json');engines={c['caseId']:c['engine'] for c in plan};seen=set();pending={};stop=False
    def ending(*_):nonlocal stop;stop=True
    signal.signal(signal.SIGTERM,ending);signal.signal(signal.SIGINT,ending)
    def one(cid,file):
        job=work/'solver-jobs'/cid/file.stem;job.mkdir(parents=True,exist_ok=False)
        try:
            if file.is_symlink() or file.stat().st_size>8*1024*1024 or not re.fullmatch('[a-f0-9]{32}',file.stem):raise ValueError('Invalid spool envelope')
            binding=read(work/'active'/f'{cid}.json')
            reply=execute(read(file),job,sut,engines[cid],role,binding)
        except Exception as e:reply={'ok':False,'jobId':file.stem,'error':str(e)}
        save(job/'broker-receipt.json',{'caseId':cid,'engine':engines[cid],'role':role,'requestSha256':hashlib.sha256(file.read_bytes()).hexdigest(),
                                       'stateSha256':hashlib.sha256((job/'state.json').read_bytes()).hexdigest() if reply['ok'] else None,
                                       'ok':reply['ok'],'error':reply.get('error')})
        target=base/cid/'solver-replies'/file.name
        if target.exists():raise ValueError('Published replies are immutable')
        temp=target.with_suffix('.tmp');temp.write_text(json.dumps(reply,ensure_ascii=False,allow_nan=False)+'\n');temp.replace(target)
        print(json.dumps({'case':cid,'job':file.stem,'ok':reply['ok'],'error':reply.get('error')}),flush=True)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        while not stop or pending:
            for f in list(pending):
                if f.done():f.result();del pending[f]
            if not stop:
                for cid in engines:
                    for file in sorted((base/cid/'scratch/requests').glob('*.json')):
                        if (base/cid/'solver-replies'/file.name).exists():
                            seen.add(str(file));continue
                        if str(file) not in seen and len(pending)<workers:
                            seen.add(str(file));pending[pool.submit(one,cid,file)]=file
            time.sleep(.1)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--base',type=Path,required=True)
    p.add_argument('--sut',type=Path,required=True);p.add_argument('--role',choices=['oracle','candidate'],default='oracle');p.add_argument('--workers',type=int,default=2)
    a=p.parse_args();serve(a.work.resolve(),a.base.resolve(),a.sut.resolve(),a.role,a.workers)
