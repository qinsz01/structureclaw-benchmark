"""Wait for a sealed full capture and finish independent deterministic checks."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    with path.open('x') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write('\n')


def alive(pid):
    file = Path('/proc') / str(pid) / 'stat'
    return file.exists() and file.read_text().rsplit(')', 1)[1].strip().split()[0] != 'Z'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('edition', 'work', 'report', 'cold-root'):
        parser.add_argument('--' + name, type=Path, required=True)
    a = parser.parse_args()
    edition, work, report, cold = [getattr(a, k).resolve() for k in ('edition', 'work', 'report', 'cold_root')]
    pin = work.with_name(work.name + '-operator-pin.json')
    launch = read(work.with_name(work.name + '-launch.json'))
    source = {p.name: sha(p) for p in [HERE / n for n in ('finish_codex_full_v32.py', 'grade_codex_full_v32.cjs',
              'audit_codex_full_controls_v32.cjs', 'controls-v32.cjs', 'summarize_codex_full_v32.py',
              'summarize_candidate.py', 'replay_codex_full_v32.py', 'inspect_codex_full_case_v32.cjs')]}
    write(report / 'postprocess-source-binding.json', source)
    while not pin.exists():
        if not alive(launch['pid']):
            raise RuntimeError('Candidate controller stopped before sealing; capture preserved')
        time.sleep(10)
    for name, digest in source.items():
        if sha(HERE / name) != digest:
            raise RuntimeError('Postprocessing source changed while waiting: ' + name)
    digest = sha(pin)
    write(report / 'operator-pin-record.json', {'path': str(pin), 'sha256': digest, 'capturedAt': time.time()})
    stages = []

    def run(name, command):
        print(json.dumps({'stageStarted': name}), flush=True)
        start = time.monotonic()
        with (report / (name + '.stdout')).open('x') as out, (report / (name + '.stderr')).open('x') as err:
            proc = subprocess.run(command, cwd=ROOT, stdout=out, stderr=err,
                                  env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1'})
        row = {'stage': name, 'exitCode': proc.returncode, 'elapsedSeconds': time.monotonic() - start, 'command': command}
        write(report / (name + '-execution.json'), row)
        print(json.dumps({'stageFinished': name, 'exitCode': proc.returncode}), flush=True)
        return row

    diagnostic = report / 'diagnostic.json'
    stages.append(run('grading', ['node', str(HERE / 'grade_codex_full_v32.cjs'), '--edition', str(edition),
                     '--control-root', str(work), '--pin', str(pin), '--pin-sha256', digest, '--output', str(diagnostic)]))
    if stages[-1]['exitCode']:
        write(report / 'postprocess-incomplete.json', {'stages': stages, 'reason': 'Independent grading could not complete'})
        return 1
    controls = report / 'controls'
    controls.mkdir()

    def control(i):
        return run('controls-' + str(i), ['node', str(HERE / 'audit_codex_full_controls_v32.cjs'), str(edition), str(work),
                   str(pin), digest, str(diagnostic), str(i) + '/4', str(controls / ('shard-' + str(i) + '.json'))])

    with ThreadPoolExecutor(max_workers=4) as pool:
        stages.extend(pool.map(control, range(4)))
    stages.append(run('human-export', ['python3', '-m', 'scripts.research300_v3.summarize_codex_full_v32',
                     '--edition', str(edition), '--work', str(work), '--diagnostic', str(diagnostic), '--output', str(report / 'review')]))
    stages.append(run('archive-and-cold-replay', ['python3', '-m', 'scripts.research300_v3.replay_codex_full_v32',
                     '--edition', str(edition), '--work', str(work), '--pin', str(pin), '--diagnostic', str(diagnostic),
                     '--output', str(report / 'replay'), '--cold-root', str(cold)]))
    inspector = read(report / 'native-inspection-launch.json')
    summary_path = report / 'native-inspection/watch-summary.json'
    while not summary_path.exists() and alive(inspector['pid']):
        time.sleep(10)
    watch = read(summary_path) if summary_path.exists() else {'errors': [{'inspectionStoppedWithoutSummary': True}]}
    inspections = [read(p) for p in sorted((report / 'native-inspection').glob('V3-*.json')) if not p.name.endswith('.error.json')]
    cases = [read(p) for p in sorted((controls).glob('shard-*.json'))]
    control_rows = [row for shard in cases for case in shard['caseRows'] for row in case['rows']]
    control_rows += [row for shard in cases for row in shard['tamper'] if not row.get('skipped')]
    write(report / 'controls-summary.json', {'shards': len(cases), 'cases': sum(s['cases'] for s in cases),
          'controls': len(control_rows), 'controlsPassed': sum(r['passed'] for r in control_rows),
          'allPassed': len(cases) == 4 and all(r['passed'] for r in control_rows),
          'unexpected': [r for r in control_rows if not r['passed']],
          'kinds': {name: {'controls': sum(r['name'] == name for r in control_rows),
                         'passed': sum(r['name'] == name and r['passed'] for r in control_rows)}
                    for name in sorted({r['name'] for r in control_rows})}})
    native = {'cases': len(inspections), 'issuedTurns': sum(sum(t['issued'] for t in r['turns']) for r in inspections),
              'nativeAttempts': sum(r['nativeAttempts'] for r in inspections),
              'nativeSuccessful': sum(r['nativeSucceeded'] for r in inspections), 'nativeFailed': sum(r['nativeFailed'] for r in inspections),
              'allSuccessfulNativeProofsValid': all(r['allSuccessfulNativeProofsValid'] for r in inspections),
              'isolationChecks': sum(sum(t.get('isolationChecks', 0) for t in r['turns']) for r in inspections),
              'rawImageDeliveries': sum(sum(t.get('rawImages', 0) for t in r['turns']) for r in inspections),
              'inspectionErrors': watch['errors'],
              'failedAttempts': [{k: v for k, v in j.items() if k != 'originalFiles'} for r in inspections for j in r['jobs'] if not j['ok']]}
    write(report / 'native-inspection-summary.json', native)
    summary = {'kind': 'research300-v32-full-postprocess', 'formalComparisonScore': False, 'operatorPinSha256': digest,
               'candidateInvocations': 0, 'nativeSolverInvocations': 0, 'stages': stages,
               'deterministicStagesCompleted': all(s['exitCode'] == 0 for s in stages),
               'independentFailureReview': 'pending', 'nativeInspectionErrors': watch['errors'], 'postprocessSource': source}
    write(report / 'postprocess-summary.json', summary)
    print(json.dumps({k: v for k, v in summary.items() if k not in ('stages', 'postprocessSource')}), flush=True)
    return 0 if summary['deterministicStagesCompleted'] and not watch['errors'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
