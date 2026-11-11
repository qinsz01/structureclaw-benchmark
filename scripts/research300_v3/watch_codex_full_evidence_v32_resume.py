"""Resume the unchanged native inspector after the original 180 s audit timeout.

Two independent read-only case audits may run concurrently. This changes no
candidate budgets, native executions, original evidence, or inspection rules.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess
import time

from .finish_codex_full_v32 import alive

ROOT = Path(__file__).resolve().parents[2]
INSPECTOR = Path(__file__).with_name('inspect_codex_full_case_v32.cjs')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('edition', 'work', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--inspector-sha256', required=True)
    a = parser.parse_args()
    edition, work, output = [getattr(a, k).resolve() for k in ('edition', 'work', 'output')]
    if sha(INSPECTOR) != a.inspector_sha256:
        raise ValueError('Original inspection source changed')
    seen, errors, pending = set(), [], {}
    launch = read(work.with_name(work.name + '-launch.json'))
    timeout = 1800

    def inspect(cid):
        target = output / (cid + '.json')
        if sha(INSPECTOR) != a.inspector_sha256:
            raise ValueError('Inspection source changed during resume')
        try:
            result = subprocess.run(['node', str(INSPECTOR), str(edition), str(work), cid, str(target)],
                                    cwd=ROOT, capture_output=True, text=True, timeout=timeout)
            if result.returncode:
                return {'caseId': cid, 'exitCode': result.returncode, 'stderr': result.stderr, 'stdout': result.stdout}
            record = read(target)
            if record['inspectionCodeSha256'] != a.inspector_sha256:
                raise ValueError('Completed inspection source binding differs')
            print(json.dumps({'inspected': cid, 'nativeAttempts': record['nativeAttempts']}), flush=True)
            return None
        except subprocess.TimeoutExpired as error:
            return {'caseId': cid, 'inspectionTimeoutSeconds': timeout, 'detail': str(error)}

    with ThreadPoolExecutor(max_workers=2) as pool:
        while True:
            for cid, future in list(pending.items()):
                if not future.done():
                    continue
                error = future.result()
                if error:
                    errors.append(error)
                    with (output / (cid + '.resume.error.json')).open('x') as handle:
                        json.dump(error, handle, ensure_ascii=False, indent=2)
                    print(json.dumps({'inspectionError': error}), flush=True)
                del pending[cid]
            for marker in sorted((work / 'completed-cases').glob('*.json')):
                cid = marker.stem
                if cid in seen:
                    continue
                target = output / (cid + '.json')
                if target.exists():
                    if read(target)['inspectionCodeSha256'] != a.inspector_sha256:
                        raise ValueError('Prior completed inspection source binding differs')
                    seen.add(cid)
                elif len(pending) < 2:
                    seen.add(cid)
                    pending[cid] = pool.submit(inspect, cid)
            marker_count = len(list((work / 'completed-cases').glob('*.json')))
            if work.with_name(work.name + '-operator-pin.json').exists() and not pending and len(seen) == marker_count:
                break
            if not alive(launch['pid']) and not work.with_name(work.name + '-operator-pin.json').exists():
                errors.append({'runnerStoppedWithoutSeal': True})
                break
            time.sleep(5)
    summary = {'kind': 'research300-v32-full-evidence-watch', 'candidateInvocations': 0, 'nativeSolverInvocations': 0,
               'inspectedCases': len(seen) - len(errors), 'errors': errors,
               'inspectorSha256': a.inspector_sha256, 'watcherSha256': sha(Path(__file__)),
               'formalComparisonScore': False, 'resumeAfterOriginalAuditTimeout': True,
               'auditTimeoutSeconds': timeout, 'parallelReadOnlyAudits': 2}
    with (output / 'watch-summary.json').open('x') as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    print(json.dumps(summary), flush=True)
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
