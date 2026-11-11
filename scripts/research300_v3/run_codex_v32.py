"""Opt-in, local OpenSees development smoke; never a formal comparison run.

The controller delivers v3.2 public packets, retains every native attempt and
seals the original answer. It never reads private answers while Codex runs.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import stat
import subprocess
import sys
import time

from .codex_broker_v32 import Broker, write
from .prepare_readiness_v32 import HISTORICAL, PROTOCOL, code_binding, packet, public_delivery
from .setup_public import install
from scripts.pilot30.service import execute

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PYTHON = Path('/home/openclaw/.structureclaw/.venv/bin/python')
INSTALL = Path('/home/openclaw/.npm-global/lib/node_modules/@openai/codex')
TOOL_TYPES = {'command_execution', 'mcp_tool_call', 'web_search', 'file_change', 'collab_tool_call'}


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def descriptor(root, path):
    return {'path': path.relative_to(root).as_posix(), 'sha256': sha(path)}


def toml(values):
    return '{' + ','.join(json.dumps(k) + '=' + json.dumps(v) for k, v in values.items()) + '}'


def git(sut, *args):
    return subprocess.check_output(['git', '-c', 'safe.directory=*', '-C', str(sut), *args], text=True).strip()


def source_binding(sut):
    paths = set()
    for directory in (sut / 'backend/src/agent-skills', sut / 'backend/src/skill-shared', sut / 'backend/dist'):
        paths.update(p for p in directory.rglob('*') if p.is_file() and p.suffix in ('.py', '.js', '.json'))
    native = {p.relative_to(sut).as_posix(): sha(p) for p in sorted(paths)}
    controller = [HERE / n for n in ('run_codex_v32.py', 'codex_broker_v32.py', 'analyze_codex_v32.py',
                  'grade_codex_smoke_v32.cjs', 'setup_public.py', 'support.py', 'test-support-v32.cjs')]
    controller += [ROOT / n for n in ('scripts/pilot30/service.py', 'scripts/pilot30/setup_public.py',
                   'scripts/research300_v2/setup_public.py', 'scripts/research300/capture_structureclaw_worker.py',
                   'scripts/research300/codex_trial/package-analysis.cjs')]
    # Also bind generic helper imports, including modelFingerprint dependencies.
    controller += list((ROOT / 'lib').glob('*.cjs'))
    return {'sutCommit': git(sut, 'rev-parse', 'HEAD'), 'nativeFiles': native,
            'evaluationCode': code_binding(),
            'controllerCode': {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(set(controller))}}


def native_preflight(work, sut):
    job = work / 'preflight-native'
    job.mkdir()
    # Analytic two-metre cantilever, independent of all corpus reference data.
    fixture = json.loads(subprocess.check_output(['node', '-e',
        "process.stdout.write(JSON.stringify(require('./scripts/research300_v3/test-support-v32.cjs').example()))"], cwd=ROOT))
    request = {'model': fixture['ref']['model'], 'selection': {'kind': 'case', 'id': 'D'}}
    request['model']['materials'][0]['name'] = 'Analytic preflight steel'
    request['model']['sections'][0]['name'] = 'Analytic preflight section'
    reply = execute(request, job, sut, 'OpenSees', role='preflight')
    program = "const fs=require('fs');const {readQuantity}=require('./lib/requested-quantities.cjs');const x=require('./scripts/research300_v3/test-support-v32.cjs').example();const s=JSON.parse(fs.readFileSync(process.argv[1]));process.stdout.write(JSON.stringify(readQuantity(s.analysisResult,x.ref.requests[0])));"
    observed = json.loads(subprocess.check_output(['node', '-e', program, str(job / 'state.json')], cwd=ROOT))
    expected = fixture['ref']['requests'][0]['value']
    # readQuantity returns a numeric quantity in the requested unit.
    value = observed if isinstance(observed, (int, float)) else observed['value']
    result = {'role': 'preflight', 'candidateEvidence': False, 'ok': reply['ok'],
              'expectedTipUzM': expected, 'observedTipUzM': value,
              'passed': abs(value - expected) <= 1e-8,
              'nativeInvocations': 1, 'artifacts': [descriptor(work, p) for p in sorted(job.rglob('*')) if p.is_file()]}
    write(work / 'native-preflight.json', result)
    if not result['passed']:
        raise RuntimeError('Analytic native preflight failed; no model calls allowed')


def isolation_probe(config, public, scratch, tools, blocked, output):
    reads = [('current_task', public / 'task.json', True), ('public_client', tools / 'analyze.py', True),
             ('public_schema', tools / 'structure_protocol/structure_model_v2.py', True)]
    reads += [(name, p, False) for name, p in blocked]
    for _, file, _ in reads:
        if not file.is_file():
            raise RuntimeError('Isolation negative controls must exist outside the sandbox')
        with file.open('rb') as handle:
            handle.read(1)  # Empty but readable files are valid positive controls.
    writes = [('scratch_write', scratch / 'boundary-write.txt', True),
              ('public_write', public / 'boundary-write.txt', False),
              ('controller_write', output.parent / 'forbidden-write.txt', False)]
    server = socket.socket()
    server.bind(('127.0.0.1', 0))
    server.listen(4)
    with socket.create_connection(server.getsockname(), timeout=2):
        pass
    program = '''import errno,json,socket
from pathlib import Path
rows=[]
for mode,checks in [('read',READS),('write',WRITES)]:
 for name,file,expected in checks:
  error=None
  try:
   Path(file).read_bytes() if mode=='read' else Path(file).write_text('test')
   actual=True
  except OSError as exc:actual=False;error=exc.errno
  rows.append({'name':name,'access':actual,'expected':expected,'errno':error,'passed':actual==expected})
try:
 with socket.create_connection(('127.0.0.1',PORT),timeout=2):pass
 denied=False;error=None
except OSError as exc:denied=exc.errno in (errno.EPERM,errno.EACCES);error=exc.errno
rows.append({'name':'reachable_network','deniedByPolicy':denied,'errno':error,'passed':denied})
print(json.dumps(rows))
'''.replace('READS', repr([(n, str(p), e) for n, p, e in reads])).replace(
        'WRITES', repr([(n, str(p), e) for n, p, e in writes])).replace('PORT', str(server.getsockname()[1]))
    try:
        run = subprocess.run(['codex', 'sandbox', '-C', str(public), '-P', 'bench-candidate',
                              *config, '/usr/bin/python3', '-c', program], capture_output=True, text=True, timeout=30)
        rows = json.loads(run.stdout) if run.returncode == 0 else []
        result = {'allPassed': run.returncode == 0 and len(rows) == len(reads) + len(writes) + 1
                  and all(r['passed'] for r in rows), 'checks': rows, 'stderr': run.stderr,
                  'positiveControls': {'allFilesReadableOutsideSandbox': True, 'networkReachableOutsideSandbox': True}}
        write(output, result)
        if not result['allPassed']:
            raise RuntimeError('Isolation failed; no model call allowed: ' + str(output))
    finally:
        server.close()


def invoke(command, prompt, dest, wall_limit, tool_limit):
    started = time.monotonic()
    events, tool_ids, malformed = [], set(), []
    stop_reason = None
    with (dest / 'events.jsonl').open('xb') as stdout, (dest / 'stderr.log').open('xb') as stderr:
        proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=stdout, stderr=stderr, start_new_session=True)
        proc.stdin.write(prompt.encode())
        proc.stdin.close()
        with (dest / 'events.jsonl').open() as stream:
            pending = ''
            while True:
                pending += stream.read()
                pieces = pending.split('\n')
                pending = pieces.pop()
                for line in pieces:
                    if not line.strip():
                        continue
                    try:
                        event = json.loads(line)
                    except ValueError:
                        malformed.append(line)
                        continue
                    events.append(event)
                    item = event.get('item', {})
                    if item.get('type') in TOOL_TYPES:
                        tool_ids.add(item['id'])
                if proc.poll() is not None:
                    # Re-read once after process exit to include final flushed bytes.
                    tail = pending + stream.read()
                    for line in tail.splitlines():
                        try:
                            if line.strip():
                                event = json.loads(line)
                                events.append(event)
                                if event.get('item', {}).get('type') in TOOL_TYPES:
                                    tool_ids.add(event['item']['id'])
                        except ValueError:
                            malformed.append(line)
                    break
                if len(tool_ids) > tool_limit or time.monotonic() - started > wall_limit:
                    stop_reason = 'tool_budget_observed_overflow' if len(tool_ids) > tool_limit else 'wall_time_limit'
                    os.killpg(proc.pid, signal.SIGTERM)
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        os.killpg(proc.pid, signal.SIGKILL)
                        proc.wait()
                time.sleep(.1)
        # Do not leave background candidate processes running after a turn.
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    return {'events': events, 'exitCode': proc.returncode, 'stopReason': stop_reason,
            'toolCallsObserved': len(tool_ids), 'malformedEvents': malformed,
            'elapsedSeconds': time.monotonic() - started}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('edition', 'work', 'base', 'sut'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--cases', required=True)
    p.add_argument('--model', default='gpt-6.1-sol')
    p.add_argument('--workers', type=int, default=2)
    p.add_argument('--timeout', type=int, default=1800)
    p.add_argument('--native-limit', type=int, default=128)
    p.add_argument('--tool-limit', type=int, default=200)
    a = p.parse_args()
    edition, work, base, sut = [getattr(a, k).resolve() for k in ('edition', 'work', 'base', 'sut')]
    if work.exists() or base.exists():
        p.error('Fresh output/session directories required')
    if not (1 <= a.workers <= 2 and a.timeout > 0 and a.native_limit > 0 and a.tool_limit > 0):
        p.error('Invalid smoke budgets')
    if Path(sys.executable).absolute() != PYTHON:
        p.error('Run with the pinned native Python executable: ' + str(PYTHON))
    manifest = read(edition / 'manifest.json')
    ids = a.cases.split(',')
    cases = [next((c for c in manifest['cases'] if c['id'] == cid), None) for cid in ids]
    if len(set(ids)) != len(ids) or any(c is None or c['split'] != 'dev' or c['engine'] != 'OpenSees' for c in cases):
        p.error('Explicit distinct OpenSees development cases only')
    for row in manifest['files']:
        if sha(edition / row['path']) != row['sha256']:
            raise RuntimeError('Frozen edition changed')
    if git(sut, 'rev-parse', 'HEAD') != HISTORICAL or git(sut, 'status', '--porcelain', '--untracked-files=no'):
        raise RuntimeError('Clean pinned native SUT required')
    work.mkdir(parents=True)
    base.mkdir(parents=True)
    tools = base / 'public-tools'
    install(base, sut)
    shutil.copyfile(HERE / 'analyze_codex_v32.py', tools / 'analyze.py')
    public_manifest = read(tools / 'manifest.json')
    public_manifest['files'] = [descriptor(tools, f) for f in sorted(tools.rglob('*')) if f.is_file() and f.name != 'manifest.json']
    public_manifest['inputProtocol'] = PROTOCOL
    (tools / 'manifest.json').write_text(json.dumps(public_manifest, ensure_ascii=False, indent=2) + '\n')
    binding = source_binding(sut)
    write(work / 'source-binding.json', binding)
    native_packages = [Path(importlib.util.find_spec(name).origin).parent for name in ('openseespy', 'openseespylinux')]
    import openseespy.opensees as ops
    spec = {'kind': 'research300-v32-codex-smoke-specification', 'formalComparisonScore': False,
            'scope': 'selected-development-smoke', 'cases': ids, 'plannedTurns': sum(len(c['turns']) for c in cases),
            'model': a.model, 'reasoningEffort': 'high', 'inputProtocol': PROTOCOL,
            'editionManifestSha256': sha(edition / 'manifest.json'), 'sutCommit': HISTORICAL,
            'sourceBinding': descriptor(work, work / 'source-binding.json'), 'publicToolManifestSha256': sha(tools / 'manifest.json'),
            'cliVersion': subprocess.check_output(['codex', '--version'], text=True).strip(),
            'solverVersion': ops.version(), 'workers': a.workers,
            'budget': {'wallTimeSecondsPerTurn': a.timeout, 'nativeAttemptsPerTurn': a.native_limit,
                       'nativeEnforcement': 'reject-before-execution; all failed/unreported submissions counted',
                       'toolCallsPerTurn': a.tool_limit, 'toolEnforcement': 'terminate-on-observed-overflow; excess event may have started'},
            'outerRetries': 0, 'cliTransportRetries': 'CLI default; all stream errors retained', 'graderFeedbackDuringRun': False}
    write(work / 'execution-specification.json', spec)
    spec_sha = sha(work / 'execution-specification.json')
    native_preflight(work, sut)
    delivery = public_delivery(edition, manifest)
    canaries = work / 'boundary-canaries'
    canaries.mkdir()
    for name in ('future-turn', 'other-case'):
        (canaries / name).write_text('controller-only boundary control\n')
    broker = Broker(work, base, sut, {'sutCommit': HISTORICAL, 'executionSpecificationSha256': spec_sha}, a.native_limit)
    broker.start()

    def workflow(c):
        session = base / c['id']
        scratch = session / 'scratch'
        (scratch / 'requests').mkdir(parents=True)
        (session / 'solver-replies').mkdir()
        thread = None
        rows = []
        for ordinal, t in enumerate(c['turns'], 1):
            dest = work / 'runs' / c['id'] / t['id']
            dest.mkdir(parents=True)
            packet(edition, delivery, c['id'], t['id'], dest / 'issued-packet')
            public = session / t['id']
            shutil.copytree(dest / 'issued-packet' / t['id'], public)
            released = [session / x['id'] for x in c['turns'][:ordinal]]
            access = {':root': 'deny', ':minimal': 'read', str(INSTALL): 'read',
                      str(PYTHON.parent.parent): 'read', str(tools): 'read', str(scratch): 'write',
                      str(session / 'solver-replies'): 'read', **{str(x): 'read' for x in released},
                      **{str(x): 'deny' for x in native_packages}}
            config = ['-c', 'default_permissions="bench-candidate"', '-c', 'permissions.bench-candidate.filesystem=' + toml(access),
                      '-c', 'permissions.bench-candidate.network.enabled=false', '-c', 'approval_policy="never"',
                      '-c', 'project_doc_max_bytes=0', '-c', 'web_search="disabled"', '-c', 'model_reasoning_effort="high"',
                      '-c', 'shell_environment_policy.inherit="core"', '-c', 'shell_environment_policy.include_only=["PATH","LANG","LC_ALL","TMPDIR"]',
                      '-c', 'shell_environment_policy.set=' + toml({'LANG': 'C.UTF-8', 'PYTHONNOUSERSITE': '1'})]
            blocked = [('private_reference', edition / t['private']), ('scorer', HERE / 'evaluate-v32.cjs'),
                       ('controller_spec', work / 'execution-specification.json'), ('future_turn', canaries / 'future-turn'),
                       ('other_case', canaries / 'other-case')]
            blocked += [('unregistered_native_' + str(i), package / '__init__.py') for i, package in enumerate(native_packages)]
            isolation_probe(config, public, scratch, tools, blocked, dest / 'isolation.json')
            answer = scratch / ('answer-' + t['id'] + '.json')
            message = (public / 'user-message.txt').read_text()
            prompt = f'''你是结构工程评测的候选智能体。当前题 {c['id']}，第 {ordinal} 轮。当前公开目录 {public}，保留同一会话已签发资料，完成全部本轮要求。可编程，文件仅写入 SCRATCH；不得读取其他题、私有参考、评分程序或外网。
TOOLS={tools}，SESSION={session}，SCRATCH={scratch}。通用原生工具命令：{PYTHON} {tools}/analyze.py --request YOUR_REQUEST_JSON --session {session} --turn {t['id']} --output YOUR_REPLY_JSON。必须使用当前轮次 {t['id']}。仅此接口运行指定 OpenSees，返回你提交模型的实际结果。jobId 是控制端分配的真实作业编号。schema 在 TOOLS/structure_protocol，数量协议见 TOOLS/quantity-contract.md，工程项目格式见本轮 tool-contract.md 或 TOOLS/tool-contract.md。{PYTHON} 可运行 Pillow、numpy、pydantic；不要安装依赖。图纸需要实际阅读。允许自行计算比较设计，最终选择必须有真实工具证据；不要直接调用原生求解器。
每轮预算 {a.timeout} 秒、{a.native_limit} 次原生请求、{a.tool_limit} 次智能体工具调用；失败请求也计数。不要打印大型原始数组。题目范围是线弹性杆系，不要求规范承载力认证。按原公开资料建模，不得编造缺失物理资料。独立完成本轮，无评分反馈。
将结构化答案 JSON 保存到 {answer}。L1/L2/动力用 jobIds/quantities/derived；工程分析/项目用 jobIdsByScenario 或 jobIdsByModel。动力另报 massTotal。控制量须有正确符号、单位、组合和实际控制位置。真实引用此前已签发结果可以使用历史 jobId。最终简短说明交付路径。

以下是 v3.2 本轮原始用户资料投递文本：
{message}'''
            (dest / 'prompt.txt').write_text(prompt)
            write(dest / 'input-delivery.json', {'protocol': PROTOCOL, 'caseId': c['id'], 'turnId': t['id'],
                'messageSha256': sha(public / 'user-message.txt'), 'verbatimMessageIncluded': message in prompt,
                'files': [descriptor(public, f) for f in sorted(public.rglob('*')) if f.is_file()],
                'inlineAttachments': next(r['inlineVerbatim'] for r in delivery['turns'] if r['caseId'] == c['id'] and r['turnId'] == t['id'])})
            common = ['--ignore-user-config', '--ignore-rules', '--skip-git-repo-check', *config,
                      '--disable', 'multi_agent', '--disable', 'hooks', '--disable', 'apps', '--disable', 'plugins',
                      '--enable', 'skip_host_skill_discovery', '--model', a.model, '--json', '-o', str(dest / 'answer.txt')]
            command = ['codex', '--no-daemon', 'exec', '-C', str(public)] + (['resume', *common, thread, '-'] if thread else [*common, '-'])
            images = sorted(str(f) for f in public.rglob('*.png'))
            command = command[:-1] + [arg for f in images for arg in ('--image', f)] + command[-1:]
            broker.open_turn(c['id'], t['id'])
            write(dest / 'dispatch.json', {'caseId': c['id'], 'turnId': t['id'], 'parentThread': thread,
                  'actualModelCall': True, 'command': command, 'startedAt': time.time(), 'promptSha256': sha(dest / 'prompt.txt')})
            print(json.dumps({'started': c['id'], 'turn': t['id']}), flush=True)
            capture_error = None
            try:
                execution = invoke(command, prompt, dest, a.timeout, a.tool_limit)
            finally:
                try:
                    broker.close_turn(c['id'], t['id'])
                except Exception as exc:
                    capture_error = repr(exc)
            events = execution.pop('events')
            next_thread = next((e.get('thread_id') for e in events if e.get('type') == 'thread.started'), thread)
            if thread and thread != next_thread:
                capture_error = 'Persistent conversation identity changed'
            thread = next_thread
            completed = any(e.get('type') == 'turn.completed' for e in events)
            service_errors = [e for e in events if e.get('type') in ('error', 'turn.failed')]
            status = 'completed' if completed and execution['exitCode'] == 0 else 'service_blocked' if service_errors and not execution['stopReason'] else 'candidate_failed' if execution['stopReason'] else 'interrupted'
            answer_error = None
            if answer.exists() or answer.is_symlink():
                try:
                    fd = os.open(answer, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
                    with os.fdopen(fd, 'rb') as handle:
                        if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
                            raise ValueError('Answer is not a regular file')
                        raw = handle.read(8 * 1024 * 1024 + 1)
                    if len(raw) > 8 * 1024 * 1024:
                        raise ValueError('Answer exceeds 8 MiB')
                    (dest / 'answer.json').write_bytes(raw)
                except (OSError, ValueError) as exc:
                    answer_error, status = repr(exc), 'candidate_failed'
            result = {'caseId': c['id'], 'turnId': t['id'], 'threadId': thread, **execution,
                      'completedTurn': completed, 'candidateStatus': status, 'environmentStatus': 'ready',
                      'captureComplete': capture_error is None and not execution['malformedEvents'],
                      'captureError': capture_error, 'answerCaptureError': answer_error, 'serviceErrors': service_errors,
                      'usage': [e.get('usage') for e in events if e.get('type') == 'turn.completed']}
            write(dest / 'execution.json', result)
            rows.append(result)
            print(json.dumps({'finished': c['id'], 'turn': t['id'], 'status': status,
                              'answer': (dest / 'answer.json').exists(), 'jobs': len(broker.attempts(c['id'], t['id']))}), flush=True)
            if status != 'completed' or capture_error or not thread:
                break
        return rows

    results, errors = [], []
    try:
        with ThreadPoolExecutor(max_workers=a.workers) as pool:
            futures = {pool.submit(workflow, c): c['id'] for c in cases}
            for future in as_completed(futures):
                try:
                    results.extend(future.result())
                except Exception as exc:
                    errors.append({'caseId': futures[future], 'error': repr(exc)})
                    print(json.dumps(errors[-1]), flush=True)
    finally:
        try:
            broker.close()
        except Exception as exc:
            errors.append({'collectorError': repr(exc)})
    unchanged = source_binding(sut) == binding
    if not unchanged:
        errors.append({'sourceError': 'Execution source changed during run'})
    # Re-read completed records even when a later turn in the same case failed.
    captured = {(r['caseId'], r['turnId']): r for r in (read(f) for f in work.glob('runs/*/*/execution.json'))}
    turns, entries = [], []
    for c in cases:
        for t in c['turns']:
            dest = work / 'runs' / c['id'] / t['id']
            result = captured.get((c['id'], t['id']))
            row = {'caseId': c['id'], 'turnId': t['id'], 'captureComplete': bool(result and result['captureComplete'] and unchanged),
                   'environmentStatus': result['environmentStatus'] if result else 'ready',
                   'candidateStatus': result['candidateStatus'] if result else 'interrupted',
                   'currentJobIds': [x['evidenceId'] for x in broker.attempts(c['id'], t['id'])]}
            if (dest / 'answer.json').is_file():
                row['answer'] = descriptor(work, dest / 'answer.json')
            turns.append(row)
            for identity in row['currentJobIds']:
                job = work / 'solver-jobs' / c['id'] / identity
                if not (job / 'broker-receipt.json').is_file():
                    row['captureComplete'] = False
                    continue
                receipt = read(job / 'broker-receipt.json')
                if receipt['ok']:
                    entries.append({'caseId': c['id'], 'turnId': t['id'], 'evidenceId': identity, 'engine': 'OpenSees', 'origin': 'broker',
                        'files': {key: descriptor(work, job / name) for key, name in
                                  [('receipt', 'broker-receipt.json'), ('request', 'submitted-request.json'), ('state', 'state.json'), ('model', 'model.json')]}})
    index = {'schemaVersion': 1, 'kind': 'research300-v3-controlled-evidence-index',
             'editionManifestSha256': spec['editionManifestSha256'], 'sutCommit': HISTORICAL,
             'inputProtocol': PROTOCOL, 'executionSpecificationSha256': spec_sha, 'turns': turns, 'entries': entries}
    write(work / 'index.json', index)
    summary = {'formalComparisonScore': False, 'runtimeQualification': 'not-qualified', 'cases': len(cases),
               'plannedTurns': len(turns), 'candidateCalls': len(list(work.glob('runs/*/*/dispatch.json'))),
               'nativeCandidateAttempts': sum(len(t['currentJobIds']) for t in turns), 'nativeSuccessfulJobs': len(entries),
               'sourceUnchangedAfterRun': unchanged, 'harnessErrors': errors, 'turns': turns}
    write(work / 'execution-summary.json', summary)
    inventory = {'files': [descriptor(work, f) for f in sorted(work.rglob('*')) if f.is_file()]}
    write(work / 'artifact-inventory.json', inventory)
    # Pin is deliberately outside the candidate-controlled session and capture root.
    pin = {'kind': 'research300-v32-codex-smoke-operator-pin', 'formalComparisonScore': False,
           'index': descriptor(work, work / 'index.json'), 'specification': descriptor(work, work / 'execution-specification.json'),
           'sourceBinding': descriptor(work, work / 'source-binding.json'), 'inventory': descriptor(work, work / 'artifact-inventory.json')}
    write(work.with_name(work.name + '-operator-pin.json'), pin)
    print(json.dumps({k: v for k, v in summary.items() if k != 'turns'}), flush=True)
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
