"""Inspect only sealed cases while the independent candidate run continues."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
INSPECTOR = Path(__file__).with_name('inspect_codex_full_case_v32.cjs')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('edition', 'work', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    edition, work, output = [getattr(a, k).resolve() for k in ('edition', 'work', 'output')]
    output.mkdir(parents=True, exist_ok=True)
    inspector_hash = hashlib.sha256(INSPECTOR.read_bytes()).hexdigest()
    seen, errors = set(), []
    while True:
        if hashlib.sha256(INSPECTOR.read_bytes()).hexdigest() != inspector_hash:
            raise RuntimeError('Inspection source changed during monitoring')
        for marker in sorted((work / 'completed-cases').glob('*.json')):
            cid = marker.stem
            if cid in seen:
                continue
            seen.add(cid)
            target = output / (cid + '.json')
            if target.exists():
                row = json.loads(target.read_bytes())
                if row['inspectionCodeSha256'] != inspector_hash:
                    raise RuntimeError('Prior inspection has a different source binding')
                continue
            result = subprocess.run(['node', str(INSPECTOR), str(edition), str(work), cid, str(target)],
                                    cwd=ROOT, capture_output=True, text=True, timeout=180)
            if result.returncode:
                record = {'caseId': cid, 'exitCode': result.returncode, 'stderr': result.stderr, 'stdout': result.stdout}
                errors.append(record)
                (output / (cid + '.error.json')).write_text(json.dumps(record, indent=2) + '\n')
                print(json.dumps({'inspectionError': cid, 'error': result.stderr[-1000:]}), flush=True)
            else:
                print(result.stdout.strip(), flush=True)
        if (work.with_name(work.name + '-operator-pin.json')).exists():
            break
        launch = json.loads(work.with_name(work.name + '-launch.json').read_bytes())
        process = Path('/proc') / str(launch['pid']) / 'stat'
        alive = process.exists() and process.read_text().rsplit(')', 1)[1].strip().split()[0] != 'Z'
        if not alive:
            errors.append({'runnerStoppedWithoutSeal': True})
            break
        time.sleep(10)
    summary = {'kind': 'research300-v32-full-evidence-watch', 'candidateInvocations': 0, 'nativeSolverInvocations': 0,
               'inspectedCases': len(seen), 'errors': errors, 'inspectorSha256': inspector_hash,
               'formalComparisonScore': False}
    with (output / 'watch-summary.json').open('x') as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    print(json.dumps(summary), flush=True)
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
