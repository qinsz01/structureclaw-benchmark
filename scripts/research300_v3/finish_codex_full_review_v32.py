"""Complete explicit environment review and diagnostic replay after raw grading."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import zipfile

from .finish_codex_full_v32 import alive

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def write(path, data):
    with path.open('x') as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write('\n')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('edition', 'work', 'report', 'cold-root'):
        p.add_argument('--' + name, required=True, type=Path)
    a = p.parse_args()
    edition, work, report, cold = [getattr(a, k).resolve() for k in ('edition', 'work', 'report', 'cold_root')]
    names = ['finish_codex_full_review_v32.py', 'review_native_environment_v32.cjs', 'test_review_native_environment_v32.cjs',
             'measure_codex_full_v32.cjs', 'test_measure_codex_full_v32.cjs', 'review_codex_full_loads_v32.py',
             'audit_load_arithmetic.py', 'run_codex_recovery_v32.py', 'grade_codex_recovery_v32.cjs',
             'test_grade_codex_recovery_v32.cjs', 'CODEX-V32-FULL.md']
    sources = {name: sha(HERE / name) for name in names}
    write(report / 'review-source-binding.json', sources)
    parent = read(report / 'postprocess-launch.json')
    raw, reviewed = report / 'diagnostic.json', report / 'diagnostic-reviewed.json'
    while not raw.exists():
        if not alive(parent['pid']):
            raise RuntimeError('Raw grading pipeline stopped; do not invent outcomes')
        time.sleep(10)
    for name, digest in sources.items():
        if sha(HERE / name) != digest:
            raise RuntimeError('Review source changed before execution: ' + name)
    pin = work.with_name(work.name + '-operator-pin.json')
    stages = []

    def run(name, command, cwd=ROOT):
        print(json.dumps({'reviewStageStarted': name}), flush=True)
        start = time.monotonic()
        with (report / (name + '.stdout')).open('x') as out, (report / (name + '.stderr')).open('x') as err:
            process = subprocess.run(command, cwd=cwd, stdout=out, stderr=err,
                                     env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
        row = {'stage': name, 'command': command, 'exitCode': process.returncode, 'elapsedSeconds': time.monotonic() - start}
        write(report / (name + '-execution.json'), row)
        stages.append(row)
        print(json.dumps({'reviewStageFinished': name, 'exitCode': process.returncode}), flush=True)
        if process.returncode:
            raise RuntimeError('Review stage failed: ' + name)

    run('environment-review', ['node', str(HERE / 'review_native_environment_v32.cjs'), str(edition), str(work),
                              str(pin), sha(pin), str(raw), str(reviewed)])
    run('reviewed-human-export', ['python3', '-m', 'scripts.research300_v3.summarize_codex_full_v32', '--edition', str(edition),
                                 '--work', str(work), '--diagnostic', str(reviewed), '--output', str(report / 'review-adjudicated')])
    measured = report / 'continuous-observations.json'
    run('continuous-observations', ['node', str(HERE / 'measure_codex_full_v32.cjs'), str(edition), str(work), str(pin), sha(pin), str(reviewed), str(measured)])
    run('independent-load-witnesses', ['python3', '-m', 'scripts.research300_v3.review_codex_full_loads_v32',
                                    '--edition', str(edition), '--work', str(work), '--diagnostic', str(reviewed),
                                    '--public-audit', str(ROOT / 'docs/implementation/reviews/research300-v3-codex-full-20261028/public-load-arithmetic.json'),
                                    '--output', str(report / 'independent-load-witnesses.json')])
    while not (report / 'replay/cold-replay.json').exists():
        if not alive(parent['pid']):
            raise RuntimeError('Raw cold replay did not complete; review artifacts preserved')
        time.sleep(10)
    archive = report / 'review-source-snapshot.zip'
    with zipfile.ZipFile(archive, 'x', zipfile.ZIP_DEFLATED) as container:
        for name, digest in sources.items():
            source = HERE / name
            if sha(source) != digest:
                raise RuntimeError('Review source changed before archival')
            container.write(source, source.relative_to(ROOT).as_posix())
    # Copy only additional diagnostic helpers; exact bound scoring/execution
    # files already extracted by the raw replay are left unchanged.
    with zipfile.ZipFile(archive) as container:
        for name in container.namelist():
            destination = cold / 'source' / name
            if destination.exists():
                if destination.read_bytes() != container.read(name):
                    raise RuntimeError('Refuse to overwrite a differing archived source')
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(container.read(name))
    cold_reviewed = cold / 'diagnostic-reviewed.json'
    run('reviewed-cold-replay', ['node', str(cold / 'source/scripts/research300_v3/review_native_environment_v32.cjs'),
                               str(cold / 'edition'), str(cold / 'capture'), str(cold / 'operator-pin.json'), sha(pin),
                               str(cold / 'diagnostic.json'), str(cold_reviewed)], cwd=cold / 'source')
    cold_measured = cold / 'continuous-observations.json'
    run('measurements-cold-replay', ['node', str(cold / 'source/scripts/research300_v3/measure_codex_full_v32.cjs'),
                                   str(cold / 'edition'), str(cold / 'capture'), str(cold / 'operator-pin.json'), sha(pin),
                                   str(cold_reviewed), str(cold_measured)], cwd=cold / 'source')
    checks = []
    for original, replica in [(reviewed, cold_reviewed), (measured, cold_measured)]:
        checks.append({'artifact': original.name, 'originalSha256': sha(original), 'coldSha256': sha(replica),
                       'bytesIdentical': sha(original) == sha(replica)})
        shutil.copyfile(replica, report / ('cold-' + replica.name))
    write(report / 'review-cold-replay.json', {'kind': 'research300-v32-reviewed-diagnostic-cold-replay',
          'formalComparisonScore': False, 'candidateInvocations': 0, 'nativeSolverInvocations': 0,
          'checks': checks, 'allBytesIdentical': all(r['bytesIdentical'] for r in checks),
          'sourceArchiveSha256': sha(archive), 'sources': sources, 'stages': stages,
          'independentFailureReview': 'Pending final review of every remaining candidate failure'})
    if not all(r['bytesIdentical'] for r in checks):
        raise RuntimeError('Reviewed diagnostic or measurements changed under cold replay')
    print(json.dumps({'reviewAndMeasurementReplayComplete': True}), flush=True)


if __name__ == '__main__':
    main()
