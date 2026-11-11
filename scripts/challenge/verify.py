"""Verify pilot sources and all determined turns through the pinned SUT backend.

This is a maintainer oracle/control experiment, never a candidate model trial.
Original native worker outputs and captures are retained for every selection.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write('\n')


def command(argv, **kwargs):
    result = subprocess.run(argv, capture_output=True, text=True, timeout=300, **kwargs)
    if result.returncode:
        raise RuntimeError(f'{argv[0]} failed: {result.stderr[-3000:]} {result.stdout[-1000:]}')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--edition', type=Path, required=True)
    parser.add_argument('--sut', type=Path, required=True)
    parser.add_argument('--work', type=Path, required=True)
    args = parser.parse_args()
    edition, sut, work = args.edition.resolve(), args.sut.resolve(), args.work.resolve()
    if work.exists():
        raise FileExistsError('Verification work directory must not exist')
    manifest = read(edition / 'manifest.json')
    for entry in manifest['files']:
        blob = (edition / entry['path']).read_bytes()
        if len(blob) != entry['bytes'] or hashlib.sha256(blob).hexdigest() != entry['sha256']:
            raise ValueError('Edition input changed: ' + entry['path'])
    work.mkdir(parents=True)
    commit = command(['git', '-c', 'safe.directory=*', '-C', str(sut), 'rev-parse', 'HEAD']).stdout.strip()
    if command(['git', '-c', 'safe.directory=*', '-C', str(sut), 'status', '--porcelain']).stdout.strip():
        raise ValueError('Oracle backend checkout must be clean')
    results, native_runs = [], 0
    for case in manifest['cases']:
        previous = None
        for turn in case['turns']:
            reference = read(edition / turn['private'])
            target = work / case['id'] / turn['id']
            target.mkdir(parents=True)
            trusted = []
            if reference['kind'] == 'clarify':
                answer = {'clarifications': [{'field': f, 'question': 'Please confirm the unresolved field ' + f}
                                              for f in reference['clarificationFields']]}
                write(target / 'answer.json', answer)
            else:
                if reference['kind'] == 'query':
                    state, trusted = copy.deepcopy(previous[0]), copy.deepcopy(previous[1])
                else:
                    selections = {json.dumps(q['selection'], sort_keys=True): q['selection'] for q in reference['requests']}
                    for ordinal, selection in enumerate(selections.values(), 1):
                        job = target / f'job-{ordinal}'
                        job.mkdir()
                        request = {'model': reference['model'], 'selection': selection}
                        write(job / 'request.json', request)
                        env = {**os.environ, 'PYTHONPATH': str(sut / 'backend/src/skill-shared/python'),
                               'SCLAW_BENCH_CAPTURE_ROOT': str(job / 'captures'),
                               'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1'}
                        normalize = 'import json,sys;from structure_protocol.structure_model_v2 import StructureModelV2;print(json.dumps(StructureModelV2.model_validate(json.load(sys.stdin)).model_dump(mode="json",exclude_unset=True),allow_nan=False))'
                        normalized = command([sys.executable, '-c', normalize], input=json.dumps(reference['model']), env=env)
                        model = json.loads(normalized.stdout)
                        write(job / 'model.json', model)
                        parameters = {'loadCaseIds': [selection['id']]} if selection['kind'] == 'case' else {'loadCombinationId': selection['id']}
                        worker = {'action': 'analyze', 'input': {'type': 'static', 'engineId': 'builtin-opensees',
                                                               'model': model, 'parameters': parameters}}
                        write(job / 'worker-request.json', worker)
                        actual = command([sys.executable, str(ROOT / 'scripts/research300/capture_structureclaw_worker.py'),
                                          str(sut / 'backend/src/agent-skills/analysis/runtime/worker.py')],
                                         input=json.dumps(worker), env=env)
                        (job / 'worker.stdout.json').write_text(actual.stdout)
                        (job / 'worker.stderr.log').write_text(actual.stderr)
                        command(['node', str(ROOT / 'scripts/research300/codex_trial/package-analysis.cjs'), str(job), str(sut)])
                        trusted.append(read(job / 'state.json'))
                        native_runs += 1
                    state = copy.deepcopy(trusted[-1])
                    state['analysisResult']['results'] = {key: value for s in trusted for key, value in s['analysisResult']['results'].items()}
                write(target / 'state.json', state)
                write(target / 'trusted.json', trusted)
                previous = (state, trusted)
            output = command(['node', str(ROOT / 'scripts/challenge/verify-oracle.cjs'), str(edition / turn['private']), str(target)])
            report = json.loads(output.stdout)
            results.append({'caseId': case['id'], 'turnId': turn['id'], **report})
            print(json.dumps(results[-1]), flush=True)
    summary = {'schemaVersion': 1, 'edition': manifest['edition'], 'actualCandidateRuns': 0,
               'experimentRole': 'maintainer-oracle-and-negative-controls', 'sutCommit': commit,
               'sourceManifestSha256': hashlib.sha256((edition / 'manifest.json').read_bytes()).hexdigest(),
               'turns': results, 'nativeBackendExecutions': native_runs,
               'allPassed': all(r['passed'] and r['negativeControlsPassed'] for r in results)}
    write(work / 'summary.json', summary)
    if not summary['allPassed']:
        raise ValueError('One or more oracle/negative controls failed')


if __name__ == '__main__':
    main()
