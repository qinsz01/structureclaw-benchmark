"""Maintainer inputs through the public client; not a language-model trial."""
import argparse
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid
from oracle_models import canonical

ROOT=Path(__file__).resolve().parents[2]


def read(p):return json.loads(p.read_text())
def write(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x') as f:f.write(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n')


def main():
    p=argparse.ArgumentParser();p.add_argument('--edition',type=Path,required=True);p.add_argument('--work',type=Path,required=True)
    p.add_argument('--base',type=Path,required=True);p.add_argument('--sut',type=Path,required=True);p.add_argument('--resume',action='store_true');a=p.parse_args()
    edition,work,base,sut=[x.resolve() for x in [a.edition,a.work,a.base,a.sut]]
    manifest=read(edition/'manifest.json');manifest_hash=hashlib.sha256((edition/'manifest.json').read_bytes()).hexdigest()
    for f in manifest['files']:assert hashlib.sha256((edition/f['path']).read_bytes()).hexdigest()==f['sha256']
    commit=subprocess.check_output(['git','-c','safe.directory=*','-C',str(sut),'rev-parse','HEAD'],text=True).strip()
    assert commit==manifest['sutCommit']
    assert not subprocess.check_output(['git','-c','safe.directory=*','-C',str(sut),'status','--porcelain','--untracked-files=no'],text=True).strip()
    if not a.resume and (base.exists() or (work/'solver-jobs').exists()):raise FileExistsError('Fresh oracle directories required')
    base.mkdir(parents=True,exist_ok=a.resume);work.mkdir(parents=True,exist_ok=True)
    (work/'active').mkdir(exist_ok=a.resume)
    plan=[{'caseId':c['id'],'engine':c['engine']} for c in manifest['cases']]
    if (work/'plan.json').exists():assert a.resume and read(work/'plan.json')==plan
    else:write(work/'plan.json',plan)
    for c in manifest['cases']:
        (base/c['id']/'scratch/requests').mkdir(parents=True,exist_ok=a.resume);(base/c['id']/'solver-replies').mkdir(exist_ok=a.resume)
        for t in c['turns']:
            dest=base/c['id']/t['id']
            if dest.exists():
                assert a.resume
                for f in (edition/t['public']).iterdir():assert (dest/f.name).read_bytes()==f.read_bytes()
            else:shutil.copytree(edition/t['public'],dest)
    env={**os.environ,'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','PYTHONDONTWRITEBYTECODE':'1'}
    out=(work/'broker.log').open('a');err=(work/'broker.stderr').open('a')
    broker=subprocess.Popen([sys.executable,str(Path(__file__).with_name('service.py')),'--work',str(work),'--base',str(base),
        '--sut',str(sut),'--role','oracle','--workers','3'],stdout=out,stderr=err,env=env)
    def workflow(case):
        cid=case['id'];previous=[];rows=[]
        for ordinal,t in enumerate(case['turns'],1):
            ref=read(edition/t['private']);target=work/'runs'/cid/t['id'];target.mkdir(parents=True,exist_ok=a.resume)
            if (target/'capture.json').exists():
                prior=read(target/'capture.json');assert a.resume and prior['manifestSha256']==manifest_hash
                previous=prior['jobIds'];rows.append({'caseId':cid,'turnId':t['id'],'kind':ref['kind'],'engine':case['engine'],'jobs':len(previous),'executionPrepared':True,'resumed':True})
                continue
            # Active binding contains identities only. Broker cannot read truths.
            active=work/'active'/f'{cid}.json';temp=active.with_suffix('.tmp')
            temp.write_text(json.dumps({'state':ordinal,'sourceHash':manifest_hash}));temp.replace(active)
            jobs=[];groups=[]
            if ref['kind']=='query': jobs=previous[:]
            elif ref['kind']=='clarify':pass
            else:
                if ref['kind']=='scheme':
                    for s in ref['schemeTruth']:
                        for sel in ref['schemeSelections']:
                            groups.append((s['id'],{'model':s['model'],'analysis':'static','selection':{'kind':'combination','id':sel}}))
                elif ref['kind']=='static':
                    selections={json.dumps(q['selection'],sort_keys=True):q['selection'] for q in ref['requests']}
                    for sel in selections.values():groups.append((None,{'model':ref['model'],'analysis':'static','selection':sel}))
                else:groups=[(None,{'model':ref['model'],'analysis':ref['kind'],'parameters':ref['parameters']})]
                scheme_jobs={}
                for index,(scheme,request) in enumerate(groups,1):
                    request=deepcopy(request)
                    # Historical author models may retain 3-D axis annotations
                    # in an XZ model. They are not physical axes in that plane;
                    # the public canonical schema explicitly forbids them.
                    request['model']=canonical(request['model'],case['engine'])
                    suffix=f'{index}-{uuid.uuid4().hex[:8]}'
                    request_file=target/f'request-{suffix}.json';reply_file=target/f'reply-{suffix}.json';write(request_file,request)
                    command=[sys.executable,str(Path(__file__).with_name('analyze.py')),'--request',str(request_file),
                             '--session',str(base/cid),'--output',str(reply_file)]
                    proc=subprocess.run(command,capture_output=True,text=True,env=env,timeout=1600)
                    (target/f'client-{suffix}.stdout').write_text(proc.stdout);(target/f'client-{suffix}.stderr').write_text(proc.stderr)
                    if proc.returncode:raise RuntimeError(cid+'/'+t['id']+': '+proc.stderr[-4000:])
                    reply=read(reply_file);jobs.append(reply['jobId'])
                    if scheme:scheme_jobs.setdefault(scheme,[]).append(reply['jobId'])
                if scheme_jobs:write(target/'scheme-jobs.json',scheme_jobs)
                previous=jobs[:]
            write(target/'capture.json',{'caseId':cid,'turnId':t['id'],'manifestSha256':manifest_hash,'jobIds':jobs,
                  'currentJobIds':[] if ref['kind']=='query' else jobs,'maintainerOracle':True,'candidateCall':False})
            row={'caseId':cid,'turnId':t['id'],'kind':ref['kind'],'engine':case['engine'],'jobs':len(jobs),'executionPrepared':True}
            rows.append(row);print(json.dumps(row),flush=True)
        return rows
    # One serial commercial workflow prevents vendor process contention; local
    # OpenSees uses its own fresh subprocesses in parallel with the remote group.
    def group(cases):
        rows=[]
        for c in cases:rows.extend(workflow(c))
        return rows
    groups=[[c for c in manifest['cases'] if c['engine']=='OpenSees'],[c for c in manifest['cases'] if c['engine']!='OpenSees']]
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(group,g) for g in groups]
            rows=[r for f in futures for r in f.result()]
        write(work/'execution-summary.json',{'manifestSha256':manifest_hash,'sutCommit':commit,'candidateCalls':0,
            'role':'maintainer-public-tool-oracle','turns':rows,'nativeJobs':sum(r['jobs'] for r in rows if r['kind']!='query')})
    finally:
        broker.terminate()
        try:broker.wait(timeout=30)
        except subprocess.TimeoutExpired:broker.kill();broker.wait()
        out.close();err.close()


if __name__=='__main__':main()
