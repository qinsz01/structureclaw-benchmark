"""Prepare or execute isolated Codex trials with the challenge's shorter prompt.

No candidate sees the edition root or evaluator. The existing numeric-only
broker executes its model. --execute runs candidates; default only prepares.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/research300/codex_trial'))
from setup_public import install


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write('\n')


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def toml(value):
    return '{' + ','.join(json.dumps(k)+'='+json.dumps(v) for k, v in value.items()) + '}'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--edition', type=Path, required=True)
    p.add_argument('--work', type=Path, required=True)
    p.add_argument('--base', type=Path, required=True)
    p.add_argument('--sut', type=Path, required=True)
    p.add_argument('--python', type=Path, default=Path(sys.executable))
    p.add_argument('--cases', help='Comma-separated explicit case selection; defaults to all six')
    p.add_argument('--execute', action='store_true')
    p.add_argument('--model', default='gpt-6.1-sol')
    p.add_argument('--timeout', type=int, default=1800)
    a = p.parse_args()
    edition, work, base, sut = [x.resolve() for x in (a.edition, a.work, a.base, a.sut)]
    for folder in (work, base):
        if folder.exists():
            raise FileExistsError('Trial directories must be new; prior attempts are retained: ' + str(folder))
    manifest = read(edition / 'manifest.json')
    for entry in manifest['files']:
        if digest(edition / entry['path']) != entry['sha256']:
            raise ValueError('Edition changed: ' + entry['path'])
    selected = a.cases.split(',') if a.cases else [c['id'] for c in manifest['cases']]
    if len(set(selected)) != len(selected) or set(selected) - {c['id'] for c in manifest['cases']}:
        raise ValueError('Invalid/duplicate case selection')
    work.mkdir(parents=True)
    base.mkdir(parents=True)
    public_tools = install(base, sut)
    tools = base / 'public-tools'
    contract = (Path(__file__).parent / 'tool-contract.md').read_text()
    plan = []
    for case in manifest['cases']:
        if case['id'] not in selected:
            continue
        session = base / case['id']
        scratch = session / 'scratch'
        (scratch / 'requests').mkdir(parents=True)
        (session / 'solver-replies').mkdir()
        turns = []
        for turn in case['turns']:
            public = session / turn['id']
            shutil.copytree(edition / turn['public'], public)
            text = contract
            for token, value in {'TOOLS': tools, 'SCRATCH': scratch, 'SESSION': session, 'TURN': turn['id']}.items():
                text = text.replace('@'+token+'@', str(value))
            (public / 'README.md').write_text(text)
            turns.append({'id': turn['id'], 'publicDir': str(public)})
        plan.append({'caseId': case['id'], 'engine': 'OpenSees', 'turns': turns})
    write(work / 'plan.json', plan)
    def revision(folder):
        return subprocess.run(['git', '-c', 'safe.directory=*', '-C', str(folder), 'rev-parse', 'HEAD'],
                              check=True, capture_output=True, text=True).stdout.strip()
    write(work / 'source-binding.json', {'edition': manifest['edition'], 'manifestSha256': digest(edition / 'manifest.json'),
                                       'toolContractSha256': digest(Path(__file__).parent / 'tool-contract.md'),
                                       'model': a.model, 'reasoningEffort': 'high', 'actualCandidateRun': a.execute,
                                       'sutCommit': revision(sut), 'benchmarkCommit': revision(ROOT),
                                       'runnerSha256': digest(Path(__file__)), 'publicTools': public_tools})
    if not a.execute:
        print(json.dumps({'preparedCases': len(plan), 'turns': sum(len(c['turns']) for c in plan), 'actualCandidateRun': False}))
        return
    broker_log = (work / 'broker.log').open('w')
    broker = subprocess.Popen([str(a.python), str(ROOT / 'scripts/research300/codex_trial/broker.py'),
                               '--work', str(work), '--base', str(base), '--sut', str(sut),
                               '--python', str(a.python), '--workers', '2'], stdout=broker_log, stderr=subprocess.STDOUT)
    results = []
    install_root = '/home/openclaw/.npm-global/lib/node_modules/@openai/codex'
    try:
        for case in plan:
            cid, thread = case['caseId'], None
            for turn in case['turns']:
                tid, public = turn['id'], Path(turn['publicDir'])
                session, scratch = base / cid, base / cid / 'scratch'
                target = work / 'runs' / cid / tid
                target.mkdir(parents=True)
                access = {':root': 'deny', ':minimal': 'read', install_root: 'read',
                          str(a.python.parent.parent): 'read', str(tools): 'read', str(public): 'read',
                          str(scratch): 'write', str(session / 'solver-replies'): 'read'}
                # Previously released drawings/documents remain available. Only
                # future stages and private evidence are hidden.
                for prior in case['turns']:
                    if int(prior['id'][1:]) <= int(tid[1:]):
                        access[prior['publicDir']] = 'read'
                config = ['-c', 'default_permissions="bench-candidate"', '-c', 'permissions.bench-candidate.filesystem='+toml(access),
                          '-c', 'permissions.bench-candidate.network.enabled=false', '-c', 'approval_policy="never"',
                          '-c', 'project_doc_max_bytes=0', '-c', 'web_search="disabled"', '-c', 'model_reasoning_effort="high"',
                          '-c', 'shell_environment_policy.inherit="core"', '-c', 'shell_environment_policy.include_only=["PATH","LANG","LC_ALL","TMPDIR"]',
                          '-c', 'shell_environment_policy.set='+toml({'LANG': 'C.UTF-8', 'PYTHONNOUSERSITE': '1'})]
                future = next((t['publicDir']+'/task.json' for t in case['turns'] if int(t['id'][1:]) > int(tid[1:])), str(edition / 'manifest.json'))
                forbidden = [str(edition / 'manifest.json'), str(edition / 'cases' / cid / 'private' / (tid+'.json')),
                             str(work / 'plan.json'), future, str(Path.home() / '.codex/config.toml')]
                allowed = [str(public / 'task.json'), str(public / 'README.md'), str(tools / 'analyze.py')]
                probe_code = 'import json,socket;from pathlib import Path;out=[]\nfor p in '+repr(allowed+forbidden)+':\n try:Path(p).read_bytes();out.append(True)\n except OSError:out.append(False)\ntry:\n socket.create_connection(("1.1.1.1",443),timeout=1);out.append(True)\nexcept OSError:out.append(False)\nprint(json.dumps(out))'
                probe = subprocess.run(['codex', 'sandbox', '-C', str(public), '-P', 'bench-candidate', *config,
                                        '/usr/bin/python3', '-c', probe_code], capture_output=True, text=True, timeout=30)
                write(target / 'isolation.json', {'exitCode': probe.returncode, 'stdout': probe.stdout, 'stderr': probe.stderr})
                checks = json.loads(probe.stdout) if probe.returncode == 0 else []
                if not checks or not all(checks[:len(allowed)]) or any(checks[len(allowed):]):
                    raise RuntimeError('Candidate isolation preflight failed')
                before = {p.stem for p in (scratch / 'requests').glob('*.json')}
                prompt = f'Read README.md, task.json and the supplied public documents. Complete the current engineering request, using earlier conversation when relevant. Save the current files required by README.md. Case {cid}, turn {tid}.'
                (target / 'prompt.txt').write_text(prompt+'\n')
                options = ['--ignore-user-config', '--ignore-rules', '--skip-git-repo-check', *config,
                           '--disable', 'multi_agent', '--disable', 'hooks', '--disable', 'apps', '--disable', 'plugins',
                           '--enable', 'skip_host_skill_discovery', '--model', a.model, '--json', '-o', str(target / 'answer.txt')]
                command = ['codex', '--no-daemon', 'exec', '-C', str(public)] + (['resume', *options, thread] if thread else options)
                command += [item for image in sorted(public.glob('*.png')) for item in ('--image', str(image))]
                command.append('-')
                write(target / 'dispatch.json', {'model': a.model, 'reasoningEffort': 'high', 'command': command,
                                                'parentThread': thread, 'promptSha256': digest(target / 'prompt.txt'),
                                                'actualModelCall': True, 'publicOnly': True,
                                                'startedAt': datetime.datetime.now(datetime.timezone.utc).isoformat()})
                with (target / 'events.jsonl').open('wb') as stdout, (target / 'stderr.log').open('wb') as stderr:
                    proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=stdout, stderr=stderr, start_new_session=True)
                    try:
                        proc.communicate(prompt.encode(), timeout=a.timeout)
                    except subprocess.TimeoutExpired:
                        os.killpg(proc.pid, signal.SIGTERM)
                        proc.wait(timeout=20)
                        raise
                events = [json.loads(line) for line in (target / 'events.jsonl').read_text().splitlines() if line]
                current = next((e['thread_id'] for e in events if e.get('type') == 'thread.started'), thread)
                if proc.returncode or not current or not any(e.get('type') == 'turn.completed' for e in events) or thread and current != thread:
                    raise RuntimeError('Candidate execution incomplete; retained without score-based retry')
                thread = current
                after = {p.stem for p in (scratch / 'requests').glob('*.json')}
                created = sorted(after-before)
                current_ids = []
                for jobid in created:
                    file = work / 'solver-jobs' / cid / jobid / 'state.json'
                    if file.exists():
                        current_ids.append(read(file)['analysisResult']['runId'])
                for source, destination in [(scratch / f'state-{tid}.json', target / 'state.json'),
                                             (scratch / f'answer-{tid}.json', target / 'answer.json')]:
                    if source.exists():
                        shutil.copyfile(source, destination)
                write(target / 'capture.json', {'manifestSha256': digest(edition / 'manifest.json'), 'threadId': thread,
                                                'requestsCreated': created, 'allJobIds': sorted(after), 'currentRunIds': current_ids})
                scored = subprocess.run(['node', str(ROOT / 'scripts/challenge/evaluate.cjs'), '--edition', str(edition),
                                         '--run', str(work), '--case', cid, '--turn', tid,
                                         '--output', str(target / 'evaluation.json')], capture_output=True, text=True, timeout=60)
                if scored.returncode not in (0, 1):
                    raise RuntimeError('Evaluator infrastructure failure: '+scored.stderr)
                value = read(target / 'evaluation.json')
                results.append(value)
                print(json.dumps({'caseId': cid, 'turnId': tid, 'passed': value['passed']}), flush=True)
        write(work / 'summary.json', {'edition': manifest['edition'], 'model': a.model, 'reasoningEffort': 'high',
                                      'manifestSha256': digest(edition / 'manifest.json'), 'actualCandidateRuns': len(plan),
                                      'turns': results, 'passedTurns': sum(r['passed'] for r in results)})
    finally:
        broker.terminate()
        broker.wait(timeout=30)
        broker_log.close()


if __name__ == '__main__':
    main()
