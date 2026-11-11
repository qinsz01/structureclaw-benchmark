"""Export and independently replay the explicit post-hoc v3.3 diagnostic."""
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


def read(p):
    return json.loads(p.read_bytes())


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write(p, value):
    with p.open('x') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for n in ('edition', 'work', 'report', 'cold-root'):
        parser.add_argument('--' + n, type=Path, required=True)
    a = parser.parse_args()
    edition, work, report, cold = [getattr(a, k).resolve() for k in ('edition', 'work', 'report', 'cold_root')]
    out = report / 'policy-v33'
    names = ['evaluate-v33.cjs', 'test_evaluate_v33.cjs', 'regrade_codex_full_v33.cjs', 'measure_codex_full_v33.cjs',
             'review_codex_full_edge_cases_v33.py', 'finish_codex_policy_v33.py', 'POLICY-V33.md',
             'test-support-v32.cjs', 'audit_project_q_density_v32.py', 'summarize_codex_full_v32.py',
             'clarify_codex_full_cost_v32.py']
    sources = {n: sha(HERE / n) for n in names}
    write(out / 'completion-source-binding.json', sources)
    launch = read(out / 'regrade-launch.json')
    diagnostic = out / 'diagnostic-v33.json'
    while not diagnostic.exists():
        if not alive(launch['pid']):
            raise RuntimeError('Policy regrade stopped without an output')
        time.sleep(10)
    for n, h in sources.items():
        if sha(HERE / n) != h:
            raise RuntimeError('Policy completion source changed: ' + n)
    grade = read(diagnostic)
    if not grade['policyRevision']['allControlsPassed']:
        raise RuntimeError('Policy controls failed; original outputs preserved')
    stages = []

    def run(name, command, cwd=ROOT):
        print(json.dumps({'policyStageStarted': name}), flush=True)
        start = time.monotonic()
        with (out / (name + '.stdout')).open('x') as stdout, (out / (name + '.stderr')).open('x') as stderr:
            p = subprocess.run(command, cwd=cwd, stdout=stdout, stderr=stderr,
                               env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
        row = {'stage': name, 'command': command, 'exitCode': p.returncode, 'elapsedSeconds': time.monotonic() - start}
        write(out / (name + '-execution.json'), row)
        stages.append(row)
        print(json.dumps({'policyStageFinished': name, 'exitCode': p.returncode}), flush=True)
        if p.returncode:
            raise RuntimeError('Policy completion stage failed: ' + name)

    run('policy-tests', ['node', '--test', str(HERE / 'test_evaluate_v33.cjs')])
    export = out / 'review'
    run('policy-export', ['python3', '-m', 'scripts.research300_v3.summarize_codex_full_v32', '--edition', str(edition),
                         '--work', str(work), '--diagnostic', str(diagnostic), '--output', str(export)])
    from openpyxl import load_workbook
    wb = load_workbook(export / 'catalogue.xlsx')
    wb['说明'].append(['评分修订', 'v3.3：事后建立的线弹性静力依赖复用政策；输入和执行仍为原 v3.2 协议。'])
    wb['说明'].append(['旧评分保留', '原 v3.2 为 464/560 轮通过；本表不得作为原预注册评分，也不授予论文比较资格。'])
    wb.save(export / 'catalogue.xlsx')
    wb.close()
    run('policy-cost-clarification', ['python3', '-m', 'scripts.research300_v3.clarify_codex_full_cost_v32', '--export', str(export)])
    pin = work.with_name(work.name + '-operator-pin.json')
    measured = out / 'continuous-observations-v33.json'
    run('policy-continuous-observations', ['node', str(HERE / 'measure_codex_full_v33.cjs'), str(edition), str(work),
                                         str(pin), sha(pin), str(diagnostic), str(measured)])
    archive = out / 'source-snapshot.zip'
    with zipfile.ZipFile(archive, 'x', zipfile.ZIP_DEFLATED) as container:
        for n, digest in sources.items():
            p = HERE / n
            if sha(p) != digest:
                raise RuntimeError('Policy source changed before archive: ' + n)
            container.write(p, p.relative_to(ROOT).as_posix())
    raw_parent = read(report / 'postprocess-launch.json')['pid']
    review_parent = read(report / 'final-review-launch.json')['pid']
    while not (report / 'review-cold-replay.json').exists():
        if not alive(review_parent):
            raise RuntimeError('Original reviewed cold replay did not finish')
        time.sleep(10)
    if not read(report / 'review-cold-replay.json')['allBytesIdentical']:
        raise RuntimeError('Original reviewed replay differs')
    with zipfile.ZipFile(archive) as container:
        for name in container.namelist():
            destination = cold / 'source' / name
            if destination.exists():
                if destination.read_bytes() != container.read(name):
                    raise RuntimeError('Refuse to overwrite different archived source: ' + name)
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(container.read(name))
    cold_grade = cold / 'diagnostic-v33.json'
    run('policy-cold-regrade', ['node', str(cold / 'source/scripts/research300_v3/regrade_codex_full_v33.cjs'),
                              str(cold / 'edition'), str(cold / 'capture'), str(cold / 'operator-pin.json'), sha(pin),
                              str(cold / 'diagnostic.json'), grade['policyRevision']['predecessorRawDiagnosticSha256'],
                              str(cold / 'diagnostic-reviewed.json'), grade['policyRevision']['predecessorDiagnosticSha256'],
                              str(cold_grade)], cold / 'source')
    cold_measured = cold / 'continuous-observations-v33.json'
    run('policy-cold-measurements', ['node', str(cold / 'source/scripts/research300_v3/measure_codex_full_v33.cjs'),
                                   str(cold / 'edition'), str(cold / 'capture'), str(cold / 'operator-pin.json'), sha(pin),
                                   str(cold_grade), str(cold_measured)], cold / 'source')
    cold_review = cold / 'edge-review'
    cold_review.mkdir()
    shutil.copyfile(cold / 'diagnostic-reviewed.json', cold_review / 'diagnostic-reviewed.json')
    shutil.copyfile(report / 'independent-project-Q-witnesses.json', cold_review / 'independent-project-Q-witnesses.json')
    run('edge-review-cold-replay', ['python3', '-m', 'scripts.research300_v3.review_codex_full_edge_cases_v33',
                                  '--edition', str(cold / 'edition'), '--work', str(cold / 'capture'), '--report', str(cold_review)], cold / 'source')
    checks = []
    for original, replica in [(diagnostic, cold_grade), (measured, cold_measured),
                              (report / 'edge-case-failure-review.json', cold_review / 'edge-case-failure-review.json')]:
        checks.append({'artifact': original.name, 'originalSha256': sha(original), 'coldSha256': sha(replica),
                       'bytesIdentical': sha(original) == sha(replica)})
        shutil.copyfile(replica, out / ('cold-' + replica.name))
    result = {'kind': 'codex-full-v33-policy-completion', 'formalComparisonScore': False, 'postHoc': True,
              'candidateInvocations': 0, 'nativeSolverInvocations': 0, 'originalAnswersModified': False,
              'counts': grade['counts'], 'caseCounts': grade['caseCounts'], 'checks': checks,
              'allBytesIdentical': all(c['bytesIdentical'] for c in checks), 'sources': sources,
              'sourceArchiveSha256': sha(archive), 'stages': stages}
    write(out / 'completion-summary.json', result)
    if not result['allBytesIdentical']:
        raise RuntimeError('Policy cold replay differs')
    print(json.dumps({'policyCompletionFinished': True, 'counts': grade['counts']}), flush=True)


if __name__ == '__main__':
    main()
