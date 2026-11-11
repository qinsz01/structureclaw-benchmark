"""Separate recovery experiment for cases with recorded SSH transport loss.

The original full run is never overwritten or assigned these additional scores.
This driver is an explicit source copy of the frozen full driver, with subset
scope and parent-failure checks. The candidate input/protocol/budgets are unchanged.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import time

from .run_codex_v32 import (ROOT, HERE, PYTHON, INSTALL, read, sha, descriptor, toml,
                            git, source_binding, native_preflight, isolation_probe, invoke)
from .prepare_readiness_v32 import HISTORICAL, PROTOCOL, public_delivery, packet
from .setup_public import install
from .codex_broker_v32 import write
from .codex_full_broker_v32 import FullBroker
from .codex_full_status_v32 import classify
from .verify_commercial_sources_v32 import verify as verify_commercial
from .run_codex_full_v32 import full_binding as original_full_binding


def full_binding(sut):
    binding = original_full_binding(sut)
    for name in ('run_codex_recovery_v32.py', 'grade_codex_recovery_v32.cjs'):
        path = HERE / name
        binding['controllerCode'][path.relative_to(ROOT).as_posix()] = sha(path)
    return binding


def capture_answer(source, target):
    if not source.exists() and not source.is_symlink():
        return None
    try:
        fd = os.open(source, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, 'rb') as handle:
            if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
                raise ValueError('Answer is not a regular file')
            raw = handle.read(8 * 1024 * 1024 + 1)
        if len(raw) > 8 * 1024 * 1024:
            raise ValueError('Answer exceeds 8 MiB')
        target.write_bytes(raw)
        return None
    except (OSError, ValueError) as exc:
        return repr(exc)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('edition', 'work', 'base', 'sut', 'remote-state', 'parent-work'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--scope', choices=['transport-recovery'], required=True)
    p.add_argument('--cases', nargs='+', required=True)
    p.add_argument('--model', default='gpt-6.1-sol')
    p.add_argument('--workers', type=int, default=4)
    p.add_argument('--commercial-workers', type=int, default=1)
    p.add_argument('--timeout', type=int, default=1800)
    p.add_argument('--native-limit', type=int, default=128)
    p.add_argument('--tool-limit', type=int, default=200)
    p.add_argument('--transport-retries', type=int, default=3)
    a = p.parse_args()
    edition, work, base, sut, remote = [getattr(a, k).resolve() for k in ('edition', 'work', 'base', 'sut', 'remote_state')]
    if work.exists() or base.exists():
        p.error('Fresh capture and candidate session directories required')
    if not (1 <= a.workers <= 8 and 1 <= a.commercial_workers <= 2 and a.timeout > 0
            and a.native_limit > 0 and a.tool_limit > 0 and 0 <= a.transport_retries <= 8):
        p.error('Invalid fixed budgets')
    if Path(sys.executable).absolute() != PYTHON:
        p.error('Use the pinned native Python: ' + str(PYTHON))
    parent = a.parent_work.resolve()
    manifest = read(edition / 'manifest.json')
    original_spec = read(parent / 'execution-specification.json')
    if (original_spec['editionManifestSha256'] != sha(edition / 'manifest.json')
            or original_spec['sutCommit'] != HISTORICAL or original_spec['inputProtocol'] != PROTOCOL
            or original_spec['model'] != a.model):
        raise RuntimeError('Original experiment source, edition or candidate differs')
    cases = manifest['cases']
    if len(cases) != 300 or sum(len(c['turns']) for c in cases) != 560:
        raise RuntimeError('Full scope requires the exact frozen 300-case/560-turn edition')
    all_cases = cases
    if len(set(a.cases)) != len(a.cases) or not set(a.cases) <= {c['id'] for c in all_cases}:
        raise RuntimeError('Explicit unique issued recovery cases required')
    # Never overlap commercial native executions with the primary experiment.
    commercial_cases = [c for c in all_cases if c['engine'] != 'OpenSees']
    if not all((parent / 'completed-cases' / (c['id'] + '.json')).is_file() for c in commercial_cases):
        raise RuntimeError('Wait for every original commercial workflow to close')
    cases = [c for c in all_cases if c['id'] in a.cases]
    parent_faults = []
    for case in cases:
        faults = []
        for file in sorted((parent / 'solver-jobs' / case['id']).glob('*/broker-receipt.json')):
            receipt = read(file)
            error = receipt.get('error') or ''
            if (receipt['ok'] is False and 'codex_trial/remote.py' in error
                    and 'Permission denied (publickey)' in error):
                faults.append(descriptor(parent, file))
        if case['engine'] == 'OpenSees' or not faults:
            raise RuntimeError('Recovery selection must have an original collector-recorded SSH failure')
        parent_faults.append({'caseId': case['id'], 'faultReceipts': faults})
    for file in manifest['files']:
        if sha(edition / file['path']) != file['sha256']:
            raise RuntimeError('Frozen input changed: ' + file['path'])
    if git(sut, 'rev-parse', 'HEAD') != HISTORICAL or git(sut, 'status', '--porcelain', '--untracked-files=no'):
        raise RuntimeError('Clean historical native baseline required')
    probe = read(remote / 'remote-readonly-probe.json')
    if probe['sourceMismatches'] or not probe['pkpmPython'] or not probe['yjkPython']:
        raise RuntimeError('Commercial source/install preflight failed')
    for engine in ('pkpm', 'yjk'):
        if read(remote / (engine + '-native-preflight.json')).get('passed') is not True:
            raise RuntimeError('Successful actual commercial native preflight required: ' + engine)
    work.mkdir(parents=True)
    base.mkdir(parents=True)
    for row in parent_faults:
        row['capturedFaultReceipts'] = []
        for original in row['faultReceipts']:
            source = parent / original['path']
            if sha(source) != original['sha256']:
                raise RuntimeError('Original transport receipt changed')
            target = work / 'parent-original' / original['path']
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            row['capturedFaultReceipts'].append(descriptor(work, target))
    write(work / 'parent-experiment.json', {'parentWork': str(parent),
          'parentSpecificationSha256': sha(parent / 'execution-specification.json'),
          'faults': parent_faults, 'replacesOriginalScores': False})
    for name in ('remote-setup.json', 'remote-source-manifest.json', 'remote-readonly-probe.json',
                 'pkpm-native-preflight.json', 'yjk-native-preflight.json'):
        shutil.copyfile(remote / name, work / name)
    fresh_remote = verify_commercial(work, sut)
    write(work / 'remote-source-reverification-pre.json', fresh_remote)
    if not fresh_remote['allPassed']:
        raise RuntimeError('Fresh remote source verification failed')
    if sha(work / 'remote-source-manifest.json') != probe['sourceManifestSha256']:
        raise RuntimeError('Remote manifest pin differs')
    install(base, sut)
    tools = base / 'public-tools'
    shutil.copyfile(HERE / 'analyze_codex_v32.py', tools / 'analyze.py')
    public_manifest = read(tools / 'manifest.json')
    public_manifest.update(inputProtocol=PROTOCOL,
        files=[descriptor(tools, f) for f in sorted(tools.rglob('*')) if f.is_file() and f.name != 'manifest.json'])
    (tools / 'manifest.json').write_text(json.dumps(public_manifest, ensure_ascii=False, indent=2) + '\n')
    shutil.copytree(tools, work / 'issued-public-tools')
    binding = full_binding(sut)
    write(work / 'source-binding.json', binding)
    # Preserve execution source bytes before any candidate invocation.
    for name, digest in {**binding['controllerCode'], **binding['evaluationCode']}.items():
        source = ROOT / name
        if sha(source) != digest:
            raise RuntimeError('Source changed before archival')
        dest = work / 'source-snapshot' / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest)
    import openseespy.opensees as ops
    spec = {'kind': 'research300-v32-codex-recovery-specification', 'formalComparisonScore': False,
            'scope': 'environment-recovery-supplement', 'cases': [c['id'] for c in cases],
            'plannedTurns': sum(len(c['turns']) for c in cases),
            'parentExperiment': descriptor(work, work / 'parent-experiment.json'),
            'replacesOriginalScores': False,
            'model': a.model, 'reasoningEffort': 'high', 'inputProtocol': PROTOCOL,
            'editionManifestSha256': sha(edition / 'manifest.json'), 'sutCommit': HISTORICAL,
            'sourceBinding': descriptor(work, work / 'source-binding.json'),
            'publicToolManifestSha256': sha(tools / 'manifest.json'),
            'remoteSourceManifestSha256': sha(work / 'remote-source-manifest.json'),
            'remotePreflightFiles': [descriptor(work, work / n) for n in ('remote-readonly-probe.json', 'remote-source-reverification-pre.json', 'pkpm-native-preflight.json', 'yjk-native-preflight.json')],
            'cliVersion': subprocess.check_output(['codex', '--version'], text=True).strip(), 'solverVersion': ops.version(),
            'workers': a.workers, 'commercialWorkers': a.commercial_workers,
            'commercialNativeConcurrency': 1, 'commercialNativeLease': 'single work-root flock in frozen commercial executor',
            'budget': {'wallTimeSecondsPerTurn': a.timeout, 'nativeAttemptsPerTurn': a.native_limit,
                       'toolCallsPerTurn': a.tool_limit, 'nativeEnforcement': 'reject-before-execution; all submissions counted',
                       'toolEnforcement': 'terminate-on-observed-overflow; first excess event may have started'},
            'transportRecovery': {'maxRetries': a.transport_retries, 'cooldownSeconds': 30,
                                  'sameThread': True, 'budgetsReset': False, 'retryCompletedOrCandidateFailedTurns': False},
            'graderFeedbackDuringRun': False, 'historicalTestSplitUsedForDevelopment': True}
    write(work / 'execution-specification.json', spec)
    spec_sha = sha(work / 'execution-specification.json')
    plan = []
    for c in cases:
        context = work / 'candidate-context' / (c['id'] + '.json')
        write(context, {'sourceHash': spec['editionManifestSha256'],
                        'turns': [{'turnId': t['id'], 'state': i} for i, t in enumerate(c['turns'], 1)]})
        plan.append({'caseId': c['id'], 'engine': c['engine'],
                     'turns': [{'id': t['id'], 'context': str(context)} for t in c['turns']]})
    write(work / 'plan.json', plan)
    native_preflight(work, sut)
    delivery = public_delivery(edition, manifest)
    canaries = work / 'boundary-canaries'
    canaries.mkdir()
    for name in ('future-turn', 'other-case'):
        (canaries / name).write_text('controller-only boundary control\n')
    native_packages = [Path(importlib.util.find_spec(n).origin).parent for n in ('openseespy', 'openseespylinux')]
    broker = FullBroker(work, base, sut, {'sutCommit': HISTORICAL, 'executionSpecificationSha256': spec_sha},
                        a.native_limit, workers=a.workers + a.commercial_workers + 1,
                        engines={c['id']: c['engine'] for c in cases})
    broker.start()

    def workflow(c):
        session = base / c['id']
        scratch = session / 'scratch'
        (scratch / 'requests').mkdir(parents=True)
        (session / 'solver-replies').mkdir()
        thread = None
        try:
            for ordinal, t in enumerate(c['turns'], 1):
                dest = work / 'runs' / c['id'] / t['id']
                dest.mkdir(parents=True)
                packet(edition, delivery, c['id'], t['id'], dest / 'issued-packet')
                public = session / t['id']
                shutil.copytree(dest / 'issued-packet' / t['id'], public)
                access = {':root': 'deny', ':minimal': 'read', str(INSTALL): 'read', str(PYTHON.parent.parent): 'read',
                          str(tools): 'read', str(scratch): 'write', str(session / 'solver-replies'): 'read',
                          **{str(session / turn['id']): 'read' for turn in c['turns'][:ordinal]},
                          **{str(package): 'deny' for package in native_packages}}
                config = ['-c', 'default_permissions="bench-candidate"', '-c', 'permissions.bench-candidate.filesystem=' + toml(access),
                          '-c', 'permissions.bench-candidate.network.enabled=false', '-c', 'approval_policy="never"',
                          '-c', 'project_doc_max_bytes=0', '-c', 'web_search="disabled"', '-c', 'model_reasoning_effort="high"',
                          '-c', 'shell_environment_policy.inherit="core"', '-c', 'shell_environment_policy.include_only=["PATH","LANG","LC_ALL","TMPDIR"]',
                          '-c', 'shell_environment_policy.set=' + toml({'LANG': 'C.UTF-8', 'PYTHONNOUSERSITE': '1'})]
                blocked = [('private_reference', edition / t['private']), ('scorer', HERE / 'evaluate-v32.cjs'),
                           ('controller_spec', work / 'execution-specification.json'), ('future_turn', canaries / 'future-turn'),
                           ('other_case', canaries / 'other-case'), ('remote_control', work / 'remote-setup.json')]
                blocked += [('unregistered_native_' + str(i), package / '__init__.py') for i, package in enumerate(native_packages)]
                isolation_probe(config, public, scratch, tools, blocked, dest / 'isolation.json')
                answer = scratch / ('answer-' + t['id'] + '.json')
                message = (public / 'user-message.txt').read_text()
                prompt = f'''你是结构工程评测的候选智能体。当前题 {c['id']}，第 {ordinal} 轮。公开目录 {public}；保留本题此前已签发资料与会话，独立完成全部本轮要求。可编程，文件仅写入 SCRATCH；不得读取其他题、私有参考、评分程序或外网。
TOOLS={tools}，SESSION={session}，SCRATCH={scratch}。唯一原生分析接口为：{PYTHON} {tools}/analyze.py --request YOUR_REQUEST_JSON --session {session} --turn {t['id']} --timeout 1500 --output YOUR_REPLY_JSON。本题指定 {c['engine']}，由控制端固定选择；jobId 是控制端返回的真实作业编号。schema 在 TOOLS/structure_protocol，数量协议见 TOOLS/quantity-contract.md，工程格式见本轮 tool-contract.md 或 TOOLS/tool-contract.md。{PYTHON} 可用 Pillow、numpy、pydantic；不要安装依赖。图纸需要实际阅读。允许自行计算比较设计，最终选择须有真实原生证据。商业引擎可能等待较久，请等待已提交作业，不要用重复提交代替等待。
每轮总预算 {a.timeout} 秒、{a.native_limit} 次原生请求、{a.tool_limit} 次观测工具调用，失败请求也计数。不要打印大型原始数组。范围为线弹性杆系，不要求规范承载力认证。按原公开资料建模，不得编造缺失物理资料。不会收到评分反馈，不询问是否继续。
将本轮结构化答案保存为 {answer}，一个 JSON 对象。L1/L2/动力用 jobIds/quantities/derived，工程分析/项目用 jobIdsByScenario 或 jobIdsByModel；动力另报 massTotal。控制量须有正确符号、单位、组合和实际位置。有效历史结果可引用先前真实 jobId；物理输入已变时应提供相应新证据。只查询历史结果的轮次遵循原题要求。完成后简短说明交付路径。

以下为本轮 v3.2 原始用户资料投递文本：
{message}'''
                (dest / 'prompt.txt').write_text(prompt)
                delivery_row = next(r for r in delivery['turns'] if r['caseId'] == c['id'] and r['turnId'] == t['id'])
                write(dest / 'input-delivery.json', {'protocol': PROTOCOL, 'caseId': c['id'], 'turnId': t['id'],
                      'messageSha256': sha(public / 'user-message.txt'), 'verbatimMessageIncluded': message in prompt,
                      'files': [descriptor(public, f) for f in sorted(public.rglob('*')) if f.is_file()],
                      'inlineAttachments': delivery_row['inlineVerbatim']})
                broker.open_turn(c['id'], t['id'])
                turn_start = time.monotonic()
                attempts = []
                tool_count, capture_error = 0, None
                print(json.dumps({'started': c['id'], 'turn': t['id'], 'engine': c['engine']}), flush=True)
                try:
                    for attempt_number in range(a.transport_retries + 1):
                        attempt_dir = dest / 'attempts' / ('a%02d' % (attempt_number + 1))
                        attempt_dir.mkdir(parents=True)
                        common = ['--ignore-user-config', '--ignore-rules', '--skip-git-repo-check', *config,
                                  '--disable', 'multi_agent', '--disable', 'hooks', '--disable', 'apps', '--disable', 'plugins',
                                  '--enable', 'skip_host_skill_discovery', '--model', a.model, '--json', '-o', str(attempt_dir / 'answer.txt')]
                        command = ['codex', '--no-daemon', 'exec', '-C', str(public)] + (['resume', *common, thread, '-'] if thread else [*common, '-'])
                        if attempt_number == 0 or not thread:
                            images = sorted(str(f) for f in public.rglob('*.png'))
                            command = command[:-1] + [arg for image in images for arg in ('--image', image)] + command[-1:]
                        actual_prompt = prompt if attempt_number == 0 or not thread else f'模型服务中断后继续当前 {c["id"]}/{t["id"]} 未完成任务。保留已完成工作、文件和真实作业，不重做已完成步骤。仍将本轮答案保存到 {answer}。题目和预算没有改变。'
                        (attempt_dir / 'prompt.txt').write_text(actual_prompt)
                        dispatch = {'caseId': c['id'], 'turnId': t['id'], 'attempt': attempt_number + 1,
                                    'parentThread': thread, 'actualModelCall': True, 'command': command,
                                    'startedAt': time.time(), 'promptSha256': sha(attempt_dir / 'prompt.txt')}
                        write(attempt_dir / 'dispatch.json', dispatch)
                        if attempt_number == 0:
                            write(dest / 'dispatch.json', dispatch)
                        execution = invoke(command, actual_prompt, attempt_dir,
                                           max(.1, a.timeout - (time.monotonic() - turn_start)), max(0, a.tool_limit - tool_count))
                        events = execution.pop('events')
                        new_thread = next((e.get('thread_id') for e in events if e.get('type') == 'thread.started'), thread)
                        if thread and new_thread != thread:
                            capture_error = 'Persistent conversation identity changed'
                        thread = new_thread
                        status, retry, reason = classify(execution, events)
                        tool_count += execution['toolCallsObserved']
                        record = {**execution, 'threadId': thread, 'candidateStatus': status, 'reasonCode': reason,
                                  'transportRetryEligible': retry,
                                  'serviceErrors': [e for e in events if e.get('type') in ('error', 'turn.failed')],
                                  'usage': [e.get('usage') for e in events if e.get('type') == 'turn.completed']}
                        write(attempt_dir / 'execution.json', record)
                        capture_answer(answer, attempt_dir / 'submitted-answer.json')
                        attempts.append(record)
                        if capture_error or not retry or attempt_number == a.transport_retries or time.monotonic() - turn_start + 31 >= a.timeout or tool_count >= a.tool_limit:
                            break
                        print(json.dumps({'transportRecovery': c['id'], 'turn': t['id'], 'attempt': attempt_number + 1, 'reason': reason}), flush=True)
                        time.sleep(30)
                finally:
                    try:
                        broker.close_turn(c['id'], t['id'])
                    except Exception as exc:
                        capture_error = repr(exc)
                answer_error = capture_answer(answer, dest / 'answer.json')
                if answer_error:
                    status = 'candidate_failed'
                result = {'caseId': c['id'], 'turnId': t['id'], 'engine': c['engine'], 'threadId': thread,
                          'candidateStatus': status, 'environmentStatus': 'ready',
                          'captureComplete': capture_error is None and all(not x['malformedEvents'] for x in attempts),
                          'captureError': capture_error, 'answerCaptureError': answer_error,
                          'completedTurn': status == 'completed', 'elapsedSeconds': time.monotonic() - turn_start,
                          'toolCallsObserved': tool_count, 'actualModelCalls': len(attempts),
                          'reasonCode': reason, 'attempts': attempts,
                          'currentJobIds': [x['evidenceId'] for x in broker.attempts(c['id'], t['id'])]}
                write(dest / 'execution.json', result)
                print(json.dumps({'finished': c['id'], 'turn': t['id'], 'status': status, 'answer': (dest / 'answer.json').exists(),
                                  'jobs': len(result['currentJobIds']), 'attempts': len(attempts)}), flush=True)
                if status != 'completed' or capture_error or not thread:
                    break
        finally:
            broker.retire_case(c['id'])

    errors = []
    try:
        with ThreadPoolExecutor(max_workers=a.workers) as local, ThreadPoolExecutor(max_workers=a.commercial_workers) as commercial:
            futures = {(local if c['engine'] == 'OpenSees' else commercial).submit(workflow, c): c['id'] for c in cases}
            for future in as_completed(futures):
                cid = futures[future]
                try:
                    future.result()
                    write(work / 'completed-cases' / (cid + '.json'), {'caseId': cid, 'sealedAt': time.time()})
                except Exception as exc:
                    error = {'caseId': cid, 'error': repr(exc)}
                    errors.append(error)
                    write(work / 'case-errors' / (cid + '.json'), error)
                    print(json.dumps(error), flush=True)
    finally:
        try:
            broker.close()
        except Exception as exc:
            errors.append({'collectorError': repr(exc)})
    unchanged = full_binding(sut) == binding
    if not unchanged:
        errors.append({'sourceError': 'Bound execution source changed during run'})
    try:
        remote_post = verify_commercial(work, sut)
    except Exception as exc:
        remote_post = {'allPassed': False, 'error': repr(exc)}
    write(work / 'remote-source-reverification-post.json', remote_post)
    if not remote_post['allPassed']:
        errors.append({'remoteSourceError': remote_post})
    turns, entries = [], []
    for c in cases:
        for t in c['turns']:
            dest = work / 'runs' / c['id'] / t['id']
            result = read(dest / 'execution.json') if (dest / 'execution.json').exists() else None
            row = {'caseId': c['id'], 'turnId': t['id'],
                   'captureComplete': bool(result and result['captureComplete'] and unchanged
                                           and (c['engine'] == 'OpenSees' or remote_post['allPassed'])),
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
                if read(job / 'broker-receipt.json')['ok']:
                    entries.append({'caseId': c['id'], 'turnId': t['id'], 'evidenceId': identity, 'engine': c['engine'], 'origin': 'broker',
                        'files': {key: descriptor(work, job / name) for key, name in
                                  [('receipt', 'broker-receipt.json'), ('request', 'submitted-request.json'), ('state', 'state.json'), ('model', 'model.json')]}})
    write(work / 'index.json', {'schemaVersion': 1, 'kind': 'research300-v3-controlled-evidence-index',
          'editionManifestSha256': spec['editionManifestSha256'], 'sutCommit': HISTORICAL, 'inputProtocol': PROTOCOL,
          'executionSpecificationSha256': spec_sha, 'turns': turns, 'entries': entries})
    summary = {'formalComparisonScore': False, 'runtimeQualification': 'not-qualified', 'cases': len(cases),
               'plannedTurns': sum(len(c['turns']) for c in cases), 'replacesOriginalScores': False, 'candidateCalls': len(list(work.glob('runs/*/*/attempts/*/dispatch.json'))),
               'completedTurns': sum(t['candidateStatus'] == 'completed' for t in turns),
               'nativeCandidateAttempts': sum(len(t['currentJobIds']) for t in turns), 'nativeSuccessfulJobs': len(entries),
               'sourceUnchangedAfterRun': unchanged, 'remoteSourceVerifiedAfterRun': remote_post['allPassed'],
               'harnessErrors': errors, 'turns': turns}
    write(work / 'execution-summary.json', summary)
    write(work / 'artifact-inventory.json', {'files': [descriptor(work, f) for f in sorted(work.rglob('*')) if f.is_file()]})
    write(work.with_name(work.name + '-operator-pin.json'), {'kind': 'research300-v32-codex-recovery-operator-pin', 'formalComparisonScore': False,
          'index': descriptor(work, work / 'index.json'), 'specification': descriptor(work, work / 'execution-specification.json'),
          'sourceBinding': descriptor(work, work / 'source-binding.json'), 'inventory': descriptor(work, work / 'artifact-inventory.json')})
    print(json.dumps({k: v for k, v in summary.items() if k != 'turns'}), flush=True)
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
