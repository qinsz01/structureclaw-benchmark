"""Run selected maintainer cases through the frozen public numeric client.

OpenSees cases run concurrently, turns within each case remain sequential, and
commercial cases share one exclusive workflow. This is not a candidate runner.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from datetime import datetime, timezone
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
PILOT = ROOT / 'scripts/pilot30'
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
spec = importlib.util.spec_from_file_location('v2_oracle_models', Path(__file__).with_name('oracle_models.py'))
oracle_models = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oracle_models)


def read(path):
    return json.loads(path.read_text())


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as file:
        file.write(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def inside(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError('Edition path escapes its root: ' + relative)
    return path


def requests(ref):
    if ref['kind']=='project':
        from scripts.research300_v3.mechanics import selected_models
        choice=ref['optimalDesigns'][0] if ref['optimalDesigns'] else ref['leastViolationDesigns'][0]
        truth=next(t for t in ref['truths'] if t['id']==choice)
        return [(role,{'model':model,'analysis':'static','selection':selection})
                for role,model in selected_models(ref,truth).items()
                for selection in ref['requirements'][role+'Selections']]
    if ref['kind']=='analysis':
        return [(scenario['id'],{'model':scenario['model'],'analysis':'static','selection':selection})
                for scenario in ref['scenarios'] for selection in scenario['selections']]
    if ref['kind']=='query':return []
    if ref['kind']=='static':
        sels={json.dumps(q['selection'],sort_keys=True):q['selection'] for q in ref['requests']}
        return [(None,{'model':ref['model'],'analysis':'static','selection':s}) for s in sels.values()]
    if ref['kind'] not in ['modal','transient']:raise ValueError('Unsupported reference kind')
    return [(None,{'model':ref['model'],'analysis':ref['kind'],'parameters':ref['parameters']})]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('edition', 'work', 'base', 'sut'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--cases', help='Comma-separated case IDs; all if omitted')
    parser.add_argument('--engine', action='append', choices=('OpenSees', 'PKPM', 'YJK'))
    parser.add_argument('--local-workers', type=int, default=4)
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--plan-only', action='store_true')
    parser.add_argument('--commercial-lock', type=Path,
                        default=ROOT / '.bench-work/research300-v2-commercial.lock')
    args = parser.parse_args()
    edition, work, base, sut = [getattr(args, name).resolve()
                               for name in ('edition', 'work', 'base', 'sut')]
    if not 1 <= args.local_workers <= 16:
        raise ValueError('local-workers must be between 1 and 16')
    manifest = read(edition / 'manifest.json')
    manifest_hash = sha(edition / 'manifest.json')
    for item in manifest['files']:
        if sha(inside(edition, item['path'])) != item['sha256']:
            raise ValueError('Edition bytes changed: ' + item['path'])
    selected_ids = set(args.cases.split(',')) if args.cases else {c['id'] for c in manifest['cases']}
    unknown = selected_ids - {c['id'] for c in manifest['cases']}
    if unknown:
        raise ValueError('Unknown cases: ' + ', '.join(sorted(unknown)))
    cases = [c for c in manifest['cases'] if c['id'] in selected_ids
             and (not args.engine or c['engine'] in args.engine)]
    if not cases:
        raise ValueError('No selected cases')
    if args.cases and {c['id'] for c in cases} != selected_ids:
        raise ValueError('Explicit cases conflict with the engine filter')
    plan = [{'caseId': c['id'], 'engine': c['engine']} for c in cases]
    planned_jobs = sum(len(requests(read(inside(edition, t['private'])))) for c in cases for t in c['turns'])
    if args.plan_only:
        print(json.dumps({'manifestSha256': manifest_hash, 'selectedCases': len(cases),
              'editionCases': len(manifest['cases']), 'turns': sum(len(c['turns']) for c in cases),
              'plannedNativeJobs': planned_jobs, 'plan': plan}, ensure_ascii=False, indent=2))
        return 0
    commit = subprocess.check_output(['git', '-c', 'safe.directory=*', '-C', str(sut),
                                      'rev-parse', 'HEAD'], text=True).strip()
    if commit != manifest['sutCommit']:
        raise ValueError('SUT commit differs from the frozen edition')
    if subprocess.check_output(['git', '-c', 'safe.directory=*', '-C', str(sut),
                                'status', '--porcelain', '--untracked-files=no'], text=True).strip():
        raise ValueError('Tracked SUT source must remain clean')
    if any(c['engine'] != 'OpenSees' for c in cases):
        for name in ('remote-setup.json', 'remote-source-manifest.json'):
            if not (work / name).is_file():
                raise ValueError('Commercial run requires the verified installation record: ' + name)
    if not args.resume and (base.exists() or (work / 'solver-jobs').exists() or (work / 'plan.json').exists()):
        raise FileExistsError('Fresh oracle session/work directories required')
    base.mkdir(parents=True, exist_ok=args.resume)
    work.mkdir(parents=True, exist_ok=True)
    run_lock = (work / 'runner.lock').open('a')
    try:
        fcntl.flock(run_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as error:
        raise RuntimeError('Another oracle coordinator is using this work directory') from error
    for file in work.glob('broker-process-*.json'):
        pid = read(file)['pid']
        command_file = Path('/proc') / str(pid) / 'cmdline'
        if command_file.exists():
            command = command_file.read_bytes().split(b'\0')
            if str(PILOT / 'service.py').encode() in command and str(work).encode() in command:
                raise RuntimeError('The previous owned broker is still running; close it before resuming')
    (work / 'active').mkdir(exist_ok=args.resume)
    runtime = {'manifestSha256': manifest_hash, 'sutCommit': commit, 'plan': plan,
               'implementation': {str(p.relative_to(ROOT)): sha(p) for p in [
                   Path(__file__).resolve(), PILOT / 'service.py', PILOT / 'analyze.py',
                   Path(__file__).with_name('oracle_models.py'), Path(__file__).with_name('mechanics.py'), Path(__file__).with_name('support.py'), PILOT / 'oracle_models.py', ROOT / 'scripts/research300_v2/oracle_models.py',
                   ROOT / 'scripts/research300/commercial_reference_inputs.py', ROOT / 'scripts/research300/codex_trial/package-analysis.cjs',
                   ROOT / 'scripts/research300/codex_trial/package-commercial.cjs']}}
    for name, value in [('plan.json', plan), ('runtime-binding.json', runtime)]:
        path = work / name
        if path.exists():
            if not args.resume or read(path) != value:
                raise ValueError('Resume binding differs: ' + name)
        else:
            write(path, value)
    if (work / 'execution-summary.json').exists():
        summary = read(work / 'execution-summary.json')
        if summary['manifestSha256'] != manifest_hash or not summary['allSucceeded']:
            raise ValueError('Invalid prior completion marker')
        print(json.dumps({'alreadyCompleted': True, 'cases': len(cases),
                          'nativeJobs': summary['nativeJobs']}))
        return 0
    for case in cases:
        session = base / case['id']
        (session / 'scratch/requests').mkdir(parents=True, exist_ok=args.resume)
        (session / 'solver-replies').mkdir(exist_ok=args.resume)
        if args.resume:
            # Never replay an abandoned spool UUID into an existing job folder.
            # Failed attempts remain immutable; a new request gets a new UUID.
            for pending in (session / 'scratch/requests').glob('*.json'):
                if (session / 'solver-replies' / pending.name).exists():
                    continue
                prior_job = work / 'solver-jobs' / case['id'] / pending.stem
                if prior_job.exists() and not (prior_job / 'broker-receipt.json').exists():
                    raise RuntimeError('Unfinished owned job requires process closure before resume: ' + str(prior_job))
                archived = work / 'abandoned-spool' / case['id'] / pending.name
                archived.parent.mkdir(parents=True, exist_ok=True)
                if archived.exists():
                    raise ValueError('Duplicate abandoned request UUID')
                pending.rename(archived)
        for turn in case['turns']:
            source, dest = inside(edition, turn['public']), session / turn['id']
            if dest.exists():
                if not args.resume or {p.relative_to(dest).as_posix() for p in dest.rglob('*') if p.is_file()} != {p.relative_to(source).as_posix() for p in source.rglob('*') if p.is_file()}:
                    raise ValueError('Public oracle packet changed')
                for file in (p for p in source.rglob('*') if p.is_file()):
                    if (dest / file.relative_to(source)).read_bytes() != file.read_bytes():
                        raise ValueError('Public oracle input bytes changed: ' + str(file))
            else:
                shutil.copytree(source, dest)
    attempt = uuid.uuid4().hex
    environment = {**os.environ, 'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1',
                   'PYTHONDONTWRITEBYTECODE': '1'}
    stdout = (work / 'broker.log').open('a')
    stderr = (work / 'broker.stderr').open('a')
    broker = subprocess.Popen([sys.executable, str(PILOT / 'service.py'), '--work', str(work),
                              '--base', str(base), '--sut', str(sut), '--role', 'oracle',
                              '--workers', str(args.local_workers + 1)],
                              stdout=stdout, stderr=stderr, env=environment)
    write(work / ('broker-process-' + attempt + '.json'), {'pid': broker.pid, 'attempt': attempt,
          'manifestSha256': manifest_hash, 'work': str(work)})

    def workflow(case):
        cid, previous, rows = case['id'], [], []
        for ordinal, turn in enumerate(case['turns'], 1):
            target = work / 'runs' / cid / turn['id']
            target.mkdir(parents=True, exist_ok=True)
            ref = read(inside(edition, turn['private']))
            try:
                if (target / 'capture.json').exists():
                    capture = read(target / 'capture.json')
                    if not args.resume or capture['manifestSha256'] != manifest_hash:
                        raise ValueError('Prior capture belongs to another edition')
                    if ref['kind'] != 'clarify':
                        previous = capture['jobIds']
                    rows.append({'caseId': cid, 'turnId': turn['id'], 'kind': ref['kind'],
                                 'engine': case['engine'], 'jobs': len(capture['jobIds']),
                                 'executionPrepared': True, 'resumed': True})
                    continue
                active = work / 'active' / (cid + '.json')
                temporary = active.with_suffix('.tmp')
                temporary.write_text(json.dumps({'state': ordinal, 'sourceHash': manifest_hash}))
                temporary.replace(active)
                jobs, scheme_jobs = [], {}
                if ref['kind'] == 'query':
                    if not previous:
                        raise ValueError('Query turn has no previously executed results')
                    jobs = previous[:]
                elif ref['kind'] == 'clarify':
                    if not ref.get('clarificationFields'):
                        raise ValueError('Clarification turn lacks unresolved field identities')
                else:
                    for index, (scheme, request) in enumerate(requests(ref), 1):
                        request = deepcopy(request)
                        request['model'] = oracle_models.canonical(request['model'], case['engine'])
                        request_hash = digest(request)
                        checkpoint = target / ('completed-' + str(index) + '-' + request_hash + '.json')
                        if checkpoint.exists():
                            record = read(checkpoint)
                            if not args.resume or record['manifestSha256'] != manifest_hash or record['requestDigest'] != request_hash:
                                raise ValueError('Completed request binding differs')
                            job_id = record['jobId']
                            job = work / 'solver-jobs' / cid / job_id
                            receipt = read(job / 'broker-receipt.json')
                            if not receipt['ok'] or receipt['caseId'] != cid or receipt['engine'] != case['engine'] or receipt.get('stateSha256') != sha(job / 'state.json'):
                                raise ValueError('Completed job is not intact')
                            if digest(read(job / 'request.json')) != request_hash:
                                raise ValueError('Completed job request changed')
                        else:
                            suffix = str(index) + '-' + uuid.uuid4().hex[:12]
                            request_file, reply_file = target / ('request-' + suffix + '.json'), target / ('reply-' + suffix + '.json')
                            write(request_file, request)
                            process = subprocess.run([sys.executable, str(PILOT / 'analyze.py'),
                                '--request', str(request_file), '--session', str(base / cid),
                                '--output', str(reply_file)], capture_output=True, text=True,
                                env=environment, timeout=1600)
                            (target / ('client-' + suffix + '.stdout')).write_text(process.stdout)
                            (target / ('client-' + suffix + '.stderr')).write_text(process.stderr)
                            if process.returncode:
                                raise RuntimeError(process.stderr[-4000:])
                            reply = read(reply_file)
                            job_id = reply['jobId']
                            write(checkpoint, {'manifestSha256': manifest_hash, 'requestDigest': request_hash,
                                  'jobId': job_id, 'requestFile': request_file.name, 'replyFile': reply_file.name})
                        jobs.append(job_id)
                        if scheme is not None:
                            scheme_jobs.setdefault(scheme, []).append(job_id)
                    previous = jobs[:]
                if scheme_jobs:
                    scheme_file = target / 'job-groups.json'
                    if scheme_file.exists():
                        if not args.resume or read(scheme_file) != scheme_jobs:
                            raise ValueError('Prior scheme job mapping differs')
                    else:
                        write(scheme_file, scheme_jobs)
                write(target / 'capture.json', {'caseId': cid, 'turnId': turn['id'],
                      'manifestSha256': manifest_hash, 'jobIds': jobs,
                      'currentJobIds': [] if ref['kind'] == 'query' else jobs,
                      'maintainerOracle': True, 'candidateCall': False})
                row = {'caseId': cid, 'turnId': turn['id'], 'kind': ref['kind'], 'engine': case['engine'],
                       'jobs': len(jobs), 'executionPrepared': True}
                rows.append(row)
                print(json.dumps(row), flush=True)
            except Exception as error:
                row = {'caseId': cid, 'turnId': turn['id'], 'kind': ref['kind'], 'engine': case['engine'],
                       'jobs': 0, 'executionPrepared': False, 'error': str(error), 'attempt': attempt}
                write(target / ('failure-' + attempt + '.json'), row)
                rows.append(row)
                print(json.dumps(row), flush=True)
                for later in case['turns'][ordinal:]:
                    rows.append({'caseId': cid, 'turnId': later['id'], 'engine': case['engine'],
                                 'jobs': 0, 'executionPrepared': False, 'skippedAfterFailure': turn['id']})
                break
        return rows

    def commercial_group(selected):
        if not selected:
            return []
        args.commercial_lock.parent.mkdir(parents=True, exist_ok=True)
        with args.commercial_lock.open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            return [row for case in selected for row in workflow(case)]

    try:
        with ThreadPoolExecutor(max_workers=args.local_workers) as local_pool, ThreadPoolExecutor(max_workers=1) as commercial_pool:
            futures = [local_pool.submit(workflow, case) for case in cases if case['engine'] == 'OpenSees']
            futures.append(commercial_pool.submit(commercial_group, [case for case in cases if case['engine'] != 'OpenSees']))
            rows = [row for future in as_completed(futures) for row in future.result()]
        order = {(c['id'], t['id']): (i, j) for i, c in enumerate(cases) for j, t in enumerate(c['turns'])}
        rows.sort(key=lambda row: order[(row['caseId'], row['turnId'])])
        all_succeeded = all(row['executionPrepared'] for row in rows)
        receipts = [read(file) for file in (work / 'solver-jobs').glob('*/*/broker-receipt.json')]
        summary = {'manifestSha256': manifest_hash, 'sutCommit': commit, 'candidateCalls': 0,
                   'role': 'maintainer-public-tool-oracle', 'allSucceeded': all_succeeded,
                   'fullEditionCoverage': len(cases) == len(manifest['cases']), 'caseIds': [c['id'] for c in cases],
                   'cases': len(cases), 'editionCases': len(manifest['cases']), 'turns': rows,
                   'nativeJobs': sum(row['jobs'] for row in rows if row.get('kind') != 'query'),
                   'brokerJobs': {'receipts': len(receipts), 'successful': sum(bool(row['ok']) for row in receipts),
                                  'failed': sum(not row['ok'] for row in receipts)},
                   'failedCases': sorted({row['caseId'] for row in rows if not row['executionPrepared']}),
                   'finishedAt': datetime.now(timezone.utc).isoformat(), 'attempt': attempt}
        write(work / 'execution-attempts' / (attempt + '.json'), summary)
        if all_succeeded:
            write(work / 'execution-summary.json', summary)
        print(json.dumps({key: value for key, value in summary.items() if key != 'turns'}), flush=True)
        return 0 if all_succeeded else 1
    finally:
        broker.terminate()
        try:
            broker.wait(timeout=30)
        except subprocess.TimeoutExpired:
            broker.kill()
            broker.wait()
        stdout.close()
        stderr.close()


if __name__ == '__main__':
    sys.exit(main())
