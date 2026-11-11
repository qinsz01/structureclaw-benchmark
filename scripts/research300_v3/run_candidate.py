"""Codex validation with enforced public/current-turn isolation.

The default remains OpenSees development calibration. --scope full explicitly
allows the complete edition, including held-out cases and commercial engines.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor,as_completed
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

from .support import ROOT
from .setup_public import install

PYTHON=Path('/home/openclaw/.structureclaw/.venv/bin/python')
INSTALL=Path('/home/openclaw/.npm-global/lib/node_modules/@openai/codex')
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x') as f:f.write(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def toml(v):return '{'+','.join(json.dumps(k)+'='+json.dumps(x) for k,x in v.items())+'}'

def main():
    p=argparse.ArgumentParser();p.add_argument('--edition',type=Path,required=True);p.add_argument('--work',type=Path,required=True);p.add_argument('--base',type=Path,required=True);p.add_argument('--sut',type=Path,required=True);p.add_argument('--cases');p.add_argument('--scope',choices=['dev','full'],default='dev');p.add_argument('--remote-state',type=Path);p.add_argument('--workers',type=int,default=3);p.add_argument('--commercial-workers',type=int,default=2);p.add_argument('--timeout',type=int,default=1800);p.add_argument('--model',default='gpt-6.1-sol');a=p.parse_args()
    edition,work,base,sut=[getattr(a,k).resolve() for k in ['edition','work','base','sut']]
    assert not work.exists() and not base.exists(),'Fresh candidate work/session directories required'
    assert 1<=a.workers<=16 and 1<=a.commercial_workers<=4 and a.timeout>0,'Invalid worker count or timeout'
    assert a.scope=='full' or a.cases,'Development calibration requires explicitly selected cases'
    full=a.scope=='full'
    manifest=read(edition/'manifest.json');binding=sha(edition/'manifest.json');ids=set(a.cases.split(',')) if a.cases else {c['id'] for c in manifest['cases']};cases=[c for c in manifest['cases'] if c['id'] in ids]
    assert {c['id'] for c in cases}==ids and (full or all(c['split']=='dev' and c['engine']=='OpenSees' for c in cases)),'Selected cases are outside the requested scope'
    for r in manifest['files']:assert sha(edition/r['path'])==r['sha256']
    work.mkdir();base.mkdir();install(base,sut);tools=base/'public-tools'
    plan=[]
    for c in cases:
        row={'caseId':c['id'],'engine':c['engine']}
        if full:
            context=work/'candidate-context'/f'{c["id"]}.json'
            write(context,{'sourceHash':binding,'turns':[{'turnId':t['id'],'state':i} for i,t in enumerate(c['turns'],1)]})
            row['turns']=[{'id':t['id'],'context':str(context)} for t in c['turns']]
        plan.append(row)
    write(work/'plan.json',plan);(work/'active').mkdir()
    if any(c['engine']!='OpenSees' for c in cases):
        assert a.remote_state,'Commercial validation requires a verified --remote-state directory'
        for name in ['remote-setup.json','remote-source-manifest.json']:
            shutil.copyfile(a.remote_state/name,work/name)
        receipt=read(work/'remote-setup.json')
        assert receipt['sourceHashesVerified'] and receipt['pkpmPython'] and receipt['yjkPython']
    write(work/'candidate-binding.json',{'manifestSha256':binding,'cases':[c['id'] for c in cases],'model':a.model,'reasoningEffort':'high','cliVersion':subprocess.check_output(['codex','--version'],text=True).strip(),'developmentOnly':not full,**({'fullSuite':True,'validationScope':'full-suite','formalComparisonScore':False,'runnerCommit':subprocess.check_output(['git','-c','safe.directory=*','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),'workers':a.workers,'commercialWorkers':a.commercial_workers,'timeoutSeconds':a.timeout,'sutCommit':manifest['sutCommit'],'evaluationCode':{n:sha(Path(__file__).with_name(n)) for n in ['evaluate.cjs','qualify.cjs','physical.cjs','fidelity.cjs']}} if full else {}),'graderFeedbackDuringRun':False,'officialReference':'https://learn.chatgpt.com/docs/non-interactive-mode','implementation':{p.name:sha(p) for p in [Path(__file__),Path(__file__).with_name('setup_public.py'),ROOT/'scripts/pilot30/service.py',*([Path(__file__).with_name('grade_candidate.cjs'),ROOT/'scripts/research300/codex_trial/commercial.py'] if full else [])]}})
    for c in cases:
        session=base/c['id'];(session/'scratch/requests').mkdir(parents=True);(session/'solver-replies').mkdir()
        for t in c['turns']:shutil.copytree(edition/t['public'],session/t['id'])
    env={**os.environ,'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','PYTHONDONTWRITEBYTECODE':'1'}
    brokerlog=(work/'broker.log').open('x');brokererr=(work/'broker.stderr').open('x')
    broker=subprocess.Popen([str(PYTHON),str(ROOT/'scripts/pilot30/service.py'),'--work',str(work),'--base',str(base),'--sut',str(sut),'--role','candidate','--workers',str(a.workers+(a.commercial_workers if full else 0)+1)],stdout=brokerlog,stderr=brokererr,env=env)
    write(work/'broker-process.json',{'pid':broker.pid})
    def workflow(c):
        session=base/c['id'];scratch=session/'scratch';thread=None;results=[]
        for ordinal,t in enumerate(c['turns'],1):
            dest=work/'runs'/c['id']/t['id'];dest.mkdir(parents=True);public=session/t['id']
            active=work/'active'/(c['id']+'.json');temporary=active.with_suffix('.tmp');temporary.write_text(json.dumps({'state':ordinal,'sourceHash':binding}));temporary.replace(active)
            released=[session/x['id'] for x in c['turns'][:ordinal]]
            access={':root':'deny',':minimal':'read',str(INSTALL):'read',str(PYTHON.parent.parent):'read',str(tools):'read',str(scratch):'write',str(session/'solver-replies'):'read',**{str(x):'read' for x in released}}
            config=['-c','default_permissions="bench-candidate"','-c','permissions.bench-candidate.filesystem='+toml(access),'-c','permissions.bench-candidate.network.enabled=false','-c','approval_policy="never"','-c','project_doc_max_bytes=0','-c','web_search="disabled"','-c','model_reasoning_effort="high"','-c','shell_environment_policy.inherit="core"','-c','shell_environment_policy.include_only=["PATH","LANG","LC_ALL","TMPDIR"]','-c','shell_environment_policy.set='+toml({'LANG':'C.UTF-8','PYTHONNOUSERSITE':'1'})]
            allowed=[public/'task.json',tools/'analyze.py',tools/'structure_protocol/structure_model_v2.py']
            future=session/c['turns'][ordinal]['id']/'task.json' if ordinal<len(c['turns']) else edition/'manifest.json'
            blocked=[edition/t['private'],edition/'manifest.json',ROOT/'scripts/research300_v3/evaluate.cjs',future,Path('/home/openclaw/.codex/config.toml')]
            if full:
                other=next(x for x in cases if x['id']!=c['id']) if len(cases)>1 else None
                blocked += [work/'candidate-binding.json',work/'candidate-context'/f'{c["id"]}.json',work/'remote-setup.json',Path('/proc/self/root')/str(edition/t['private']).lstrip('/')]
                if other:blocked += [base/other['id']/other['turns'][0]['id']/'task.json']
            code='import json,socket;from pathlib import Path;out=[]\nfor s in '+repr([str(x) for x in allowed+blocked])+':\n try:out.append(bool(Path(s).read_bytes()))\n except OSError:out.append(False)\ntry:\n socket.create_connection(("1.1.1.1",443),timeout=1);out.append(True)\nexcept OSError:out.append(False)\nprint(json.dumps(out))'
            probe=subprocess.run(['codex','sandbox','-C',str(public),'-P','bench-candidate',*config,'/usr/bin/python3','-c',code],capture_output=True,text=True,timeout=30)
            write(dest/'isolation.json',{'exitCode':probe.returncode,'stdout':probe.stdout,'stderr':probe.stderr,'readableExpected':[str(x) for x in allowed],'blockedExpected':[str(x) for x in blocked]})
            assert probe.returncode==0,probe.stderr
            observed=json.loads(probe.stdout);assert observed==[True]*len(allowed)+[False]*(len(blocked)+1),'Candidate isolation failed; no model call permitted'
            answer=scratch/f'answer-{t["id"]}.json'
            prompt=f'''你是结构工程评测的候选智能体。当前题 {c['id']}，第 {ordinal} 轮。请读取 {public}/task.json 及其当前公开附件，保留同一会话已签发资料，完成全部本轮要求。可编程，但不得读取未签发轮次、其他题、私有参考、评测程序或外网。
公开工具 TOOLS={tools}，SESSION={session}，SCRATCH={scratch}。文件只写入 SCRATCH。通用客户端为：{PYTHON} {tools}/analyze.py --request YOUR_REQUEST_JSON --session {session} --output YOUR_REPLY_JSON。工具真实运行指定 {c['engine']}，仅返回你提交模型的结果，不提供标准答案。完整 schema 在 TOOLS/structure_protocol，数量交付细节见 TOOLS/quantity-contract.md，新工程题格式见本轮 tool-contract.md 或 TOOLS/tool-contract.md。使用 {PYTHON} 可运行 Pillow、numpy、pydantic。不要安装依赖。图纸需要实际阅读；按工程资料推导荷载、质量、构件和连接，允许自行计算比较设计，但最终选择必须有真实工具作业。每次请求只输出需要的摘要，避免打印大型原始数组。
任务均在现有线弹性杆系框架内，不要求规范承载力认证。使用完整的显式 schema 数据。缺少必要物理资料时在答案中明确指出，不得编造。不要询问是否继续；独立完成本轮。
将本轮结构化交付保存为 {answer}（一个 JSON 对象），所有作业 ID 使用真实返回 UUID。L1/L2/动力格式 jobIds/quantities/derived；工程分析/项目格式 jobIdsByScenario 或 jobIdsByModel。动力另报 massTotal。控制量必须报告正确符号、单位、组合和实际控制位置。勿声称评测通过，不会收到评分反馈。完成后简短说明交付路径。'''
            (dest/'prompt.txt').write_text(prompt)
            common=['--ignore-user-config','--ignore-rules','--skip-git-repo-check',*config,'--disable','multi_agent','--disable','hooks','--disable','apps','--disable','plugins','--enable','skip_host_skill_discovery','--model',a.model,'--json','-o',str(dest/'answer.txt')]
            command=['codex','--no-daemon','exec','-C',str(public)]+(['resume',*common,thread,'-'] if thread else [*common,'-'])
            images=sorted(str(p) for p in public.rglob('*.png'));command=command[:-1]+[x for im in images for x in ['--image',im]]+command[-1:]
            before={p.parent.name for p in (work/'solver-jobs'/c['id']).glob('*/broker-receipt.json')}
            write(dest/'dispatch.json',{'caseId':c['id'],'turnId':t['id'],'model':a.model,'parentThread':thread,'actualModelCall':True,'command':command,'startedAt':time.time()});print(json.dumps({'started':c['id'],'turn':t['id']}),flush=True)
            started=time.monotonic();timed=False
            with (dest/'events.jsonl').open('xb') as stdout,(dest/'stderr.log').open('xb') as stderr:
                proc=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=stdout,stderr=stderr,start_new_session=True)
                try:proc.communicate(prompt.encode(),timeout=a.timeout)
                except subprocess.TimeoutExpired:
                    timed=True;os.killpg(proc.pid,signal.SIGTERM)
                    try:proc.wait(timeout=10)
                    except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
            events=[json.loads(line) for line in (dest/'events.jsonl').read_text().splitlines()]
            next_thread=next((e.get('thread_id') for e in events if e.get('type')=='thread.started'),thread)
            assert not thread or thread==next_thread,'Persistent conversation identity changed';thread=next_thread
            current={p.parent.name for p in (work/'solver-jobs'/c['id']).glob('*/broker-receipt.json')}-before
            if answer.exists():shutil.copyfile(answer,dest/'answer.json')
            shutil.copytree(scratch,dest/'scratch-snapshot',ignore=shutil.ignore_patterns('requests'))
            result={'caseId':c['id'],'turnId':t['id'],'threadId':thread,'exitCode':proc.returncode,'timedOut':timed,'elapsedSeconds':time.monotonic()-started,'completedTurn':any(e.get('type')=='turn.completed' for e in events),'answerPresent':answer.is_file(),'currentJobIds':sorted(current),'usage':[e.get('usage') for e in events if e.get('type')=='turn.completed']};write(dest/'execution.json',result);results.append(result);print(json.dumps({'finished':c['id'],'turn':t['id'],'answer':answer.exists(),'jobs':len(current)}),flush=True)
            if proc.returncode or timed or not thread or not result['completedTurn']:break
        return results
    try:
        results=[];errors=[]
        with ThreadPoolExecutor(max_workers=a.workers) as pool,ThreadPoolExecutor(max_workers=a.commercial_workers) as commercial_pool:
            futures={(pool if c['engine']=='OpenSees' else commercial_pool).submit(workflow,c):c['id'] for c in cases}
            for future in as_completed(futures):
                try:results+=future.result()
                except Exception as e:errors.append({'caseId':futures[future],'error':str(e)});print(json.dumps(errors[-1]),flush=True)
        write(work/'execution-summary.json',{'candidateCalls':len(list(work.glob('runs/*/*/dispatch.json'))),'turns':results,'harnessErrors':errors,'developmentOnly':not full,**({'validationScope':'full-suite','formalComparisonScore':False,'expectedCases':len(cases),'expectedTurns':sum(len(c['turns']) for c in cases),'allTurnsCaptured':len(results)==sum(len(c['turns']) for c in cases)} if full else {}),'manifestSha256':binding});return 1 if errors else 0
    finally:
        broker.terminate()
        try:broker.wait(timeout=20)
        except subprocess.TimeoutExpired:broker.kill();broker.wait()
        brokerlog.close();brokererr.close()

if __name__=='__main__':sys.exit(main())
