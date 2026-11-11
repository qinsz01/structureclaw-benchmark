"""Run one separate recovery experiment after the original commercial queue."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

from .finish_codex_full_v32 import alive

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PYTHON = '/home/openclaw/.structureclaw/.venv/bin/python'


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, data):
    with path.open('x') as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write('\n')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('edition', 'parent-work', 'work', 'base', 'sut', 'remote-state', 'report', 'cold-root'):
        p.add_argument('--' + name, required=True, type=Path)
    p.add_argument('--cases', nargs='+', required=True)
    a = p.parse_args()
    edition, parent, work, base, sut, remote, report, cold = [getattr(a, k).resolve() for k in
        ('edition', 'parent_work', 'work', 'base', 'sut', 'remote_state', 'report', 'cold_root')]
    report.mkdir(parents=True, exist_ok=True)
    names = ('wait_codex_recovery_v32.py', 'run_codex_recovery_v32.py', 'grade_codex_recovery_v32.cjs',
             'replay_codex_recovery_v32.py', 'inspect_codex_full_case_v32.cjs')
    binding = {name: sha(HERE / name) for name in names}
    write(report / 'scheduled-recovery.json', {'cases': a.cases, 'source': binding, 'time': time.time(), 'replacesOriginalScores': False})
    commercial = [c['id'] for c in read(edition / 'manifest.json')['cases'] if c['engine'] != 'OpenSees']
    parent_launch = read(parent.with_name(parent.name + '-launch.json'))
    while not all((parent / 'completed-cases' / (cid + '.json')).is_file() for cid in commercial):
        if not alive(parent_launch['pid']):
            raise RuntimeError('Original commercial workflows did not all close')
        time.sleep(10)
    if any(sha(HERE / name) != digest for name, digest in binding.items()):
        raise RuntimeError('Recovery source changed while waiting')
    command = [PYTHON, '-m', 'scripts.research300_v3.run_codex_recovery_v32', '--scope', 'transport-recovery',
               '--edition', str(edition), '--parent-work', str(parent), '--work', str(work), '--base', str(base),
               '--sut', str(sut), '--remote-state', str(remote), '--cases', *a.cases]
    with (report / 'runner.stdout').open('x') as out, (report / 'runner.stderr').open('x') as err:
        proc = subprocess.Popen(command, cwd=ROOT, stdout=out, stderr=err,
                                env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1'})
        write(work.with_name(work.name + '-launch.json'), {'pid': proc.pid, 'startedAt': time.time(), 'command': command})
        print(json.dumps({'recoveryStarted': True, 'pid': proc.pid, 'cases': a.cases}), flush=True)
        status = proc.wait()
    if status:
        raise RuntimeError('Recovery controller failed; original records preserved')
    pin = work.with_name(work.name + '-operator-pin.json')
    digest = sha(pin)
    write(report / 'operator-pin-record.json', {'path': str(pin), 'sha256': digest})

    def run(name, args):
        print(json.dumps({'stageStarted': name}), flush=True)
        start = time.monotonic()
        with (report / (name + '.stdout')).open('x') as out, (report / (name + '.stderr')).open('x') as err:
            process = subprocess.run(args, cwd=ROOT, stdout=out, stderr=err)
        write(report / (name + '-execution.json'), {'command': args, 'exitCode': process.returncode, 'elapsedSeconds': time.monotonic() - start})
        if process.returncode:
            raise RuntimeError('Recovery stage failed: ' + name)

    diagnostic = report / 'diagnostic.json'
    run('grading', ['node', str(HERE / 'grade_codex_recovery_v32.cjs'), '--edition', str(edition), '--control-root', str(work),
                    '--pin', str(pin), '--pin-sha256', digest, '--output', str(diagnostic)])
    for cid in a.cases:
        run('inspect-' + cid, ['node', str(HERE / 'inspect_codex_full_case_v32.cjs'), str(edition), str(work), cid, str(report / (cid + '-inspection.json'))])
    run('cold-replay', ['python3', '-m', 'scripts.research300_v3.replay_codex_recovery_v32', '--edition', str(edition),
                       '--work', str(work), '--pin', str(pin), '--diagnostic', str(diagnostic), '--output', str(report / 'replay'), '--cold-root', str(cold)])
    write(report / 'recovery-complete.json', {'cases': a.cases, 'counts': read(diagnostic)['counts'], 'formalComparisonScore': False,
          'replacesOriginalScores': False, 'coldReplayIdentical': read(report / 'replay/cold-replay.json')['diagnosticBytesIdentical']})
    print(json.dumps({'recoveryVerificationComplete': True, 'counts': read(diagnostic)['counts']}), flush=True)


if __name__ == '__main__':
    main()
