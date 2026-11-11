"""Continue captured Codex conversations after a transport interruption.

Completed turns are never retried. Interrupted attempts remain immutable, and
only transport failures receive continuation prompts without grading feedback.
The trusted concurrency file can reduce new calls without stopping active ones.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import uuid

from .run_candidate import INSTALL, PYTHON, read, sha, toml, write
from .support import ROOT

TRANSPORT = re.compile(r'429|too many requests|rate.limit|model is at capacity|stream.*disconnect|connection.*(?:reset|closed|refused)|temporar.*unavail|overload|status: 50[0234]', re.I)


def events(path):
    result, invalid = [], []
    if path.exists():
        for index, line in enumerate(path.read_text(errors='replace').splitlines(), 1):
            try:
                result.append(json.loads(line))
            except ValueError:
                invalid.append(index)
    return result, invalid


def alive(pid):
    path = Path('/proc') / str(pid) / 'stat'
    try:
        return path.read_text().rsplit(')', 1)[1].strip().split()[0] != 'Z'
    except FileNotFoundError:
        return False


def capture_interrupted(work, base, cases):
    """Close records from stopped processes using their original CLI events."""
    interruption = read(work / 'operator-interruption-001.json')
    if alive(interruption['originalRunnerPid']) or alive(interruption['brokerPidDraining']):
        raise RuntimeError('Original coordinator/broker must close before resuming')
    groups = {r['pgid'] for r in interruption['ownedCliGroupsSignaled']}
    for line in subprocess.check_output(['ps', '-eo', 'pid=,pgid=,stat='], text=True).splitlines():
        pid, group, state = line.split()
        if int(group) in groups and not state.startswith('Z'):
            raise RuntimeError('Original owned CLI process has not closed: ' + pid)
    closed = []
    for case in cases:
        prior = set()
        for turn in case['turns']:
            directory = work / 'runs' / case['id'] / turn['id']
            execution = directory / 'execution.json'
            if execution.exists():
                prior.update(read(execution).get('currentJobIds', []))
                continue
            dispatch = directory / 'dispatch.json'
            if not dispatch.exists():
                continue
            info = read(dispatch)
            stream, invalid = events(directory / 'events.jsonl')
            thread = next((e.get('thread_id') for e in stream if e.get('type') == 'thread.started'), info.get('parentThread'))
            scratch = base / case['id'] / 'scratch'
            answer = scratch / ('answer-' + turn['id'] + '.json')
            target = directory / 'answer.json'
            if answer.exists():
                if target.exists() and target.read_bytes() != answer.read_bytes():
                    target.rename(directory / 'answer-before-operator-copy.json')
                shutil.copyfile(answer, target)
            snapshot = directory / 'operator-scratch-snapshot'
            if not snapshot.exists():
                shutil.copytree(scratch, snapshot, ignore=shutil.ignore_patterns('requests'))
            current = {p.parent.name for p in (work / 'solver-jobs' / case['id']).glob('*/broker-receipt.json')} - prior
            result = {'caseId': case['id'], 'turnId': turn['id'], 'threadId': thread,
                      'exitCode': None, 'timedOut': False, 'operatorStopped': True,
                      'interruptionReason': interruption['reason'],
                      'elapsedSeconds': max(0, time.time() - info['startedAt']),
                      'elapsedMeasure': 'dispatch wall-time until operator capture',
                      'completedTurn': any(e.get('type') == 'turn.completed' for e in stream),
                      'answerPresent': answer.exists(), 'currentJobIds': sorted(current),
                      'invalidJsonLines': invalid,
                      'usage': [e.get('usage') for e in stream if e.get('type') == 'turn.completed']}
            write(execution, result)
            prior.update(current)
            closed.append({'caseId': case['id'], 'turnId': turn['id'], 'completedTurn': result['completedTurn']})
    return closed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('edition', 'work', 'base', 'sut'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--model-slots', type=int, default=2)
    parser.add_argument('--max-workers', type=int, default=8)
    parser.add_argument('--timeout', type=int, default=1800)
    parser.add_argument('--transport-retries', type=int, default=8)
    args = parser.parse_args()
    edition, work, base, sut = [getattr(args, name).resolve() for name in ('edition', 'work', 'base', 'sut')]
    lease = (work / 'recovery-runner.lock').open('a')
    try:
        fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as error:
        raise RuntimeError('Another recovery coordinator is using this work directory') from error
    binding, manifest = read(work / 'candidate-binding.json'), read(edition / 'manifest.json')
    if not binding.get('fullSuite') or sha(edition / 'manifest.json') != binding['manifestSha256']:
        raise ValueError('Wrong full-suite edition binding')
    if not 1 <= args.model_slots <= args.max_workers <= 16:
        raise ValueError('Invalid model concurrency')
    for row in manifest['files']:
        if sha(edition / row['path']) != row['sha256']:
            raise ValueError('Frozen edition changed: ' + row['path'])
    for name, checksum in binding['evaluationCode'].items():
        if sha(Path(__file__).with_name(name)) != checksum:
            raise ValueError('Frozen evaluator changed: ' + name)
    cases = [c for c in manifest['cases'] if c['id'] in binding['cases']]
    closed = capture_interrupted(work, base, cases)
    if (work / 'execution-summary.json').exists():
        old = read(work / 'execution-summary.json')
        if old.get('allTurnsCaptured'):
            print(json.dumps({'alreadyCaptured': True, 'turns': len(old['turns'])}), flush=True)
            return 0
        saved = work / 'recovery-summaries' / (uuid.uuid4().hex + '.json')
        saved.parent.mkdir(exist_ok=True)
        (work / 'execution-summary.json').rename(saved)
    tools = base / 'public-tools'
    for row in read(tools / 'manifest.json')['files']:
        if sha(tools / row['path']) != row['sha256']:
            raise ValueError('Public tool changed: ' + row['path'])
    source_hash = sha(Path(__file__))
    source = work / 'recovery-sources' / source_hash / 'resume_candidate.py'
    if not source.exists():
        source.parent.mkdir(parents=True)
        shutil.copyfile(Path(__file__), source)
    recovery_id = uuid.uuid4().hex
    write(work / 'recovery-bindings' / (recovery_id + '.json'), {
        'manifestSha256': binding['manifestSha256'], 'sourceSha256': source_hash,
        'sourceSnapshot': str(source.relative_to(work)), 'model': binding['model'],
        'initialModelSlots': args.model_slots, 'maxWorkers': args.max_workers,
        'timeoutSeconds': args.timeout, 'operatorClosedCaptures': closed,
        'retryCompletedTurns': False, 'graderFeedbackDuringRun': False,
        'startedAt': time.time(), 'pid': os.getpid()})
    control = work / 'candidate-concurrency.json'
    if not control.exists():
        write(control, {'maxConcurrentModelCalls': args.model_slots, 'cooldownUntil': 0,
                        'reason': 'HTTP429 recovery; completed turns preserved'})
    stop, condition, processes_lock = threading.Event(), threading.Condition(), threading.Lock()
    processes, active_count = {}, 0

    def acquire():
        nonlocal active_count
        with condition:
            while not stop.is_set():
                policy = read(control)
                limit = max(1, min(args.max_workers, int(policy['maxConcurrentModelCalls'])))
                if active_count < limit and time.time() >= policy.get('cooldownUntil', 0):
                    active_count += 1
                    return True
                condition.wait(1)
        return False

    def release():
        nonlocal active_count
        with condition:
            active_count -= 1
            condition.notify_all()

    def throttle(reason):
        with condition:
            policy = read(control)
            policy.update(maxConcurrentModelCalls=1, cooldownUntil=time.time() + 60, reason=reason)
            temporary = control.with_suffix('.tmp-' + uuid.uuid4().hex)
            temporary.write_text(json.dumps(policy, indent=2) + '\n')
            temporary.replace(control)
            with (work / 'concurrency-history.jsonl').open('a') as file:
                file.write(json.dumps({'at': time.time(), **policy}) + '\n')
            condition.notify_all()

    def ending(*_):
        stop.set()
        with condition:
            condition.notify_all()
        with processes_lock:
            for proc in processes.values():
                if proc.poll() is None:
                    os.killpg(proc.pid, signal.SIGTERM)

    signal.signal(signal.SIGTERM, ending)
    signal.signal(signal.SIGINT, ending)
    env = {**os.environ, 'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1', 'PYTHONDONTWRITEBYTECODE': '1'}
    brokerlog = (work / ('broker-recovery-' + recovery_id + '.log')).open('x')
    brokererr = (work / ('broker-recovery-' + recovery_id + '.stderr')).open('x')
    broker = subprocess.Popen([str(PYTHON), str(ROOT / 'scripts/pilot30/service.py'), '--work', str(work),
        '--base', str(base), '--sut', str(sut), '--role', 'candidate', '--workers', str(args.max_workers + 1)],
        stdout=brokerlog, stderr=brokererr, env=env)
    write(work / ('broker-process-recovery-' + recovery_id + '.json'), {'pid': broker.pid})

    def workflow(case):
        session, thread = base / case['id'], None
        for ordinal, turn in enumerate(case['turns'], 1):
            if stop.is_set():
                return
            directory = work / 'runs' / case['id'] / turn['id']
            prior = read(directory / 'execution.json') if (directory / 'execution.json').exists() else None
            if prior and prior['completedTurn']:
                thread = prior['threadId']
                continue
            if not acquire():
                return
            held = True
            try:
                attempts, old_jobs, prior_seconds, prompt = [], set(), 0, None
                if prior:
                    attempts = list(prior.get('priorAttempts', []))
                    thread = prior.get('threadId') or thread
                    old_jobs.update(prior.get('currentJobIds', []))
                    prior_seconds = prior.get('elapsedSeconds', 0)
                    prompt = (directory / 'prompt.txt').read_text()
                for retry in range(args.transport_retries + 1):
                    if stop.is_set():
                        return
                    if directory.exists():
                        saved = work / 'interrupted-attempts' / case['id'] / turn['id'] / uuid.uuid4().hex
                        saved.parent.mkdir(parents=True, exist_ok=True)
                        directory.rename(saved)
                        attempts.append(str(saved.relative_to(work)))
                    directory.mkdir(parents=True)
                    public, scratch = session / turn['id'], session / 'scratch'
                    active = work / 'active' / (case['id'] + '.json')
                    temporary = active.with_suffix('.tmp-' + uuid.uuid4().hex)
                    temporary.write_text(json.dumps({'state': ordinal, 'sourceHash': binding['manifestSha256']}))
                    temporary.replace(active)
                    released = [session / t['id'] for t in case['turns'][:ordinal]]
                    access = {':root': 'deny', ':minimal': 'read', str(INSTALL): 'read', str(PYTHON.parent.parent): 'read',
                        str(tools): 'read', str(scratch): 'write', str(session / 'solver-replies'): 'read',
                        **{str(p): 'read' for p in released}}
                    config = ['-c', 'default_permissions="bench-candidate"', '-c', 'permissions.bench-candidate.filesystem=' + toml(access),
                        '-c', 'permissions.bench-candidate.network.enabled=false', '-c', 'approval_policy="never"',
                        '-c', 'project_doc_max_bytes=0', '-c', 'web_search="disabled"', '-c', 'model_reasoning_effort="high"',
                        '-c', 'shell_environment_policy.inherit="core"', '-c', 'shell_environment_policy.include_only=["PATH","LANG","LC_ALL","TMPDIR"]',
                        '-c', 'shell_environment_policy.set=' + toml({'LANG': 'C.UTF-8', 'PYTHONNOUSERSITE': '1'})]
                    allowed = [public / 'task.json', tools / 'analyze.py', tools / 'structure_protocol/structure_model_v2.py']
                    future = session / case['turns'][ordinal]['id'] / 'task.json' if ordinal < len(case['turns']) else edition / 'manifest.json'
                    blocked = [edition / turn['private'], ROOT / 'corpora/research300-v3-v1' / turn['private'],
                        edition / 'manifest.json', ROOT / 'scripts/research300_v3/evaluate.cjs', future,
                        work / 'candidate-binding.json', work / 'remote-setup.json', Path('/home/openclaw/.codex/config.toml'),
                        Path('/proc/self/root') / str(edition / turn['private']).lstrip('/')]
                    other = next(c for c in cases if c['id'] != case['id'])
                    blocked.append(base / other['id'] / other['turns'][0]['id'] / 'task.json')
                    code = 'import json,socket;from pathlib import Path;out=[]\nfor p in ' + repr([str(p) for p in allowed + blocked]) + ':\n try:out.append(bool(Path(p).read_bytes()))\n except OSError:out.append(False)\ntry:\n socket.create_connection(("1.1.1.1",443),timeout=1);out.append(True)\nexcept OSError:out.append(False)\nprint(json.dumps(out))'
                    probe = subprocess.run(['codex', 'sandbox', '-C', str(public), '-P', 'bench-candidate', *config, '/usr/bin/python3', '-c', code], capture_output=True, text=True, timeout=30)
                    write(directory / 'isolation.json', {'exitCode': probe.returncode, 'stdout': probe.stdout, 'stderr': probe.stderr,
                        'readableExpected': [str(p) for p in allowed], 'blockedExpected': [str(p) for p in blocked]})
                    if probe.returncode or json.loads(probe.stdout) != [True] * len(allowed) + [False] * (len(blocked) + 1):
                        raise RuntimeError('Isolation probe failed; no model call permitted')
                    answer = scratch / ('answer-' + turn['id'] + '.json')
                    if prompt is None:
                        prompt = f'''你是结构工程评测的候选智能体。当前题 {case['id']}，第 {ordinal} 轮。请读取 {public}/task.json 及其当前公开附件，保留同一会话已签发资料，完成全部本轮要求。可编程，但不得读取未签发轮次、其他题、私有参考、评测程序或外网。
公开工具 TOOLS={tools}，SESSION={session}，SCRATCH={scratch}。文件只写入 SCRATCH。通用客户端为：{PYTHON} {tools}/analyze.py --request YOUR_REQUEST_JSON --session {session} --output YOUR_REPLY_JSON。工具真实运行指定 {case['engine']}，仅返回你提交模型的结果，不提供标准答案。完整 schema 在 TOOLS/structure_protocol，数量交付细节见 TOOLS/quantity-contract.md，新工程题格式见本轮 tool-contract.md 或 TOOLS/tool-contract.md。使用 {PYTHON} 可运行 Pillow、numpy、pydantic。不要安装依赖。图纸需要实际阅读；按工程资料推导荷载、质量、构件和连接，允许自行计算比较设计，但最终选择必须有真实工具作业。每次请求只输出需要的摘要，避免打印大型原始数组。
任务均在现有线弹性杆系框架内，不要求规范承载力认证。使用完整的显式 schema 数据。缺少必要物理资料时在答案中明确指出，不得编造。不要询问是否继续；独立完成本轮。
将本轮结构化交付保存为 {answer}（一个 JSON 对象），所有作业 ID 使用真实返回 UUID。L1/L2/动力格式 jobIds/quantities/derived；工程分析/项目格式 jobIdsByScenario 或 jobIdsByModel。动力另报 massTotal。控制量必须报告正确符号、单位、组合和实际控制位置。勿声称评测通过，不会收到评分反馈。完成后简短说明交付路径。'''
                    sent_prompt = prompt + ('\n调用服务或运行调度中断了当前轮；请沿用本会话与现有文件继续完成当前轮交付。没有评分反馈，也没有新增工程资料。' if prior or retry else '')
                    (directory / 'prompt.txt').write_text(sent_prompt)
                    common = ['--ignore-user-config', '--ignore-rules', '--skip-git-repo-check', *config, '--disable', 'multi_agent',
                        '--disable', 'hooks', '--disable', 'apps', '--disable', 'plugins', '--enable', 'skip_host_skill_discovery',
                        '--model', binding['model'], '--json', '-o', str(directory / 'answer.txt')]
                    command = ['codex', '--no-daemon', 'exec', '-C', str(public)] + (['resume', *common, thread, '-'] if thread else [*common, '-'])
                    images = sorted(str(p) for p in public.rglob('*.png'))
                    command = command[:-1] + [v for im in images for v in ('--image', im)] + command[-1:]
                    before = {p.parent.name for p in (work / 'solver-jobs' / case['id']).glob('*/broker-receipt.json')}
                    write(directory / 'dispatch.json', {'caseId': case['id'], 'turnId': turn['id'], 'model': binding['model'],
                        'parentThread': thread, 'actualModelCall': True, 'command': command, 'startedAt': time.time(),
                        'recoveryId': recovery_id, 'continuationAfterInterruption': bool(prior or retry), 'priorAttempts': attempts})
                    print(json.dumps({'started': case['id'], 'turn': turn['id'], 'continuation': bool(prior or retry)}), flush=True)
                    start, timed = time.monotonic(), False
                    with (directory / 'events.jsonl').open('xb') as stdout, (directory / 'stderr.log').open('xb') as stderr:
                        proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=stdout, stderr=stderr, start_new_session=True)
                        write(directory / 'process.json', {'pid': proc.pid, 'pgid': proc.pid, 'recoveryId': recovery_id})
                        with processes_lock:
                            processes[case['id']] = proc
                        try:
                            proc.communicate(sent_prompt.encode(), timeout=args.timeout)
                        except subprocess.TimeoutExpired:
                            timed = True
                            os.killpg(proc.pid, signal.SIGTERM)
                            try:
                                proc.wait(timeout=10)
                            except subprocess.TimeoutExpired:
                                os.killpg(proc.pid, signal.SIGKILL)
                                proc.wait()
                        finally:
                            with processes_lock:
                                processes.pop(case['id'], None)
                    stream, invalid = events(directory / 'events.jsonl')
                    next_thread = next((e.get('thread_id') for e in stream if e.get('type') == 'thread.started'), thread)
                    if thread and thread != next_thread:
                        raise RuntimeError('Persistent conversation identity changed')
                    thread = next_thread
                    current = old_jobs | ({p.parent.name for p in (work / 'solver-jobs' / case['id']).glob('*/broker-receipt.json')} - before)
                    if answer.exists():
                        shutil.copyfile(answer, directory / 'answer.json')
                    shutil.copytree(scratch, directory / 'scratch-snapshot', ignore=shutil.ignore_patterns('requests'))
                    complete = any(e.get('type') == 'turn.completed' for e in stream)
                    failures = [str(e) for e in stream if e.get('type') in ('error', 'turn.failed')]
                    transport = not complete and bool(TRANSPORT.search('\n'.join(failures) + (directory / 'stderr.log').read_text(errors='replace')))
                    result = {'caseId': case['id'], 'turnId': turn['id'], 'threadId': thread, 'exitCode': proc.returncode,
                        'timedOut': timed, 'elapsedSeconds': prior_seconds + time.monotonic() - start, 'completedTurn': complete,
                        'answerPresent': answer.exists(), 'currentJobIds': sorted(current), 'invalidJsonLines': invalid,
                        'usage': [e.get('usage') for e in stream if e.get('type') == 'turn.completed'],
                        'transportFailure': transport, 'priorAttempts': attempts, 'recoveryId': recovery_id}
                    write(directory / 'execution.json', result)
                    print(json.dumps({'finished': case['id'], 'turn': turn['id'], 'answer': answer.exists(),
                        'completedTurn': complete, 'jobs': len(current), 'transportFailure': transport}), flush=True)
                    if complete:
                        break
                    if stop.is_set() or not transport or retry == args.transport_retries:
                        if transport and retry == args.transport_retries:
                            stop.set()
                        raise RuntimeError('Unfinished candidate turn retained: ' + case['id'] + '/' + turn['id'])
                    old_jobs, prior_seconds, prior = current, result['elapsedSeconds'], result
                    throttle('CLI transport error; resume same conversation after cooldown')
                    release()
                    held = False
                    if not acquire():
                        return
                    held = True
            finally:
                if held:
                    release()

    try:
        errors = []
        cases.sort(key=lambda c: (not (work / 'runs' / c['id']).exists(), c['id']))
        with ThreadPoolExecutor(max_workers=args.max_workers) as pool:
            futures = {pool.submit(workflow, c): c['id'] for c in cases}
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as error:
                    errors.append({'caseId': futures[future], 'error': str(error)})
                    print(json.dumps(errors[-1]), flush=True)
        results = [read(work / 'runs' / c['id'] / t['id'] / 'execution.json') for c in cases for t in c['turns']
                   if (work / 'runs' / c['id'] / t['id'] / 'execution.json').exists()]
        summary = {'candidateCalls': len(list(work.glob('runs/*/*/dispatch.json'))) + len(list(work.glob('interrupted-attempts/*/*/*/dispatch.json'))),
            'turns': results, 'harnessErrors': errors, 'developmentOnly': False, 'validationScope': 'full-suite',
            'formalComparisonScore': False, 'expectedCases': len(cases), 'expectedTurns': sum(len(c['turns']) for c in cases),
            'allTurnsCaptured': len(results) == sum(len(c['turns']) for c in cases) and all(r['completedTurn'] for r in results),
            'manifestSha256': binding['manifestSha256'], 'recoveryId': recovery_id}
        write(work / 'execution-summary.json', summary)
        return 1 if errors or stop.is_set() else 0
    finally:
        broker.terminate()
        try:
            broker.wait(timeout=1500)
        except subprocess.TimeoutExpired:
            broker.kill()
            broker.wait()
        brokerlog.close()
        brokererr.close()


if __name__ == '__main__':
    sys.exit(main())
