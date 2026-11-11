"""Run additional review exports after the original full diagnostic is sealed."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import zipfile

from .finish_codex_full_v32 import alive

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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('edition', 'work', 'report'):
        parser.add_argument('--' + name, type=Path, required=True)
    a = parser.parse_args()
    edition, work, report = [getattr(a, k).resolve() for k in ('edition', 'work', 'report')]
    names = ['finish_codex_full_extras_v32.py', 'clarify_codex_full_cost_v32.py', 'audit_project_q_density_v32.py',
             'test_project_q_density_v32.py', 'make_codex_full_trace_v32.py', 'review_failed_native_inputs_v32.cjs',
             'watch_codex_full_evidence_v32.py', 'watch_codex_full_evidence_v32_resume.py',
             'wait_codex_recovery_v32.py', 'replay_codex_recovery_v32.py']
    sources = {name: sha(HERE / name) for name in names}
    write(report / 'extra-review-source-binding.json', sources)
    parent = read(report / 'final-review-launch.json')
    export = report / 'review-adjudicated'
    while not (export / 'summary.json').exists():
        if not alive(parent['pid']):
            raise RuntimeError('Reviewed diagnostic/export stopped before completion')
        time.sleep(10)
    if any(sha(HERE / name) != digest for name, digest in sources.items()):
        raise RuntimeError('Additional review source changed before execution')
    diagnostic = report / 'diagnostic-reviewed.json'
    stages = []
    commands = [
        ('project-Q-review', ['python3', '-m', 'scripts.research300_v3.audit_project_q_density_v32',
                            '--edition', str(edition), '--work', str(work), '--diagnostic', str(diagnostic),
                            '--output', str(report / 'independent-project-Q-witnesses.json')]),
        ('cost-clarification', ['python3', '-m', 'scripts.research300_v3.clarify_codex_full_cost_v32', '--export', str(export)]),
        ('worked-trace', ['python3', '-m', 'scripts.research300_v3.make_codex_full_trace_v32', '--edition', str(edition),
                          '--work', str(work), '--diagnostic', str(diagnostic), '--report', str(report)]),
    ]
    for name, command in commands:
        print(json.dumps({'extraReviewStarted': name}), flush=True)
        start = time.monotonic()
        with (report / (name + '.stdout')).open('x') as out, (report / (name + '.stderr')).open('x') as err:
            result = subprocess.run(command, cwd=ROOT, stdout=out, stderr=err,
                                    env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
        stage = {'stage': name, 'command': command, 'exitCode': result.returncode, 'elapsedSeconds': time.monotonic() - start}
        write(report / (name + '-execution.json'), stage)
        stages.append(stage)
        print(json.dumps({'extraReviewFinished': name, 'exitCode': result.returncode}), flush=True)
    archive = report / 'extra-review-source-snapshot.zip'
    with zipfile.ZipFile(archive, 'x', zipfile.ZIP_DEFLATED) as container:
        for name, digest in sources.items():
            source = HERE / name
            if sha(source) != digest:
                raise RuntimeError('Additional review source changed before archival')
            container.write(source, source.relative_to(ROOT).as_posix())
    result = {'kind': 'research300-v32-full-extra-review', 'formalComparisonScore': False,
              'candidateInvocations': 0, 'nativeSolverInvocations': 0, 'originalScoresChanged': False,
              'diagnosticSha256': sha(diagnostic), 'sources': sources, 'sourceArchiveSha256': sha(archive),
              'stages': stages, 'allStagesCompleted': all(r['exitCode'] == 0 for r in stages),
              'remainingFailureReview': 'Every nonpassed delivery still needs final attribution; automatic witnesses cover only their declared scope.'}
    write(report / 'extra-review-summary.json', result)
    return 0 if result['allStagesCompleted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
