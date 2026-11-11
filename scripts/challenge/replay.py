"""Replay unchanged challenge answers with the explicit v3 equivalence profile."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_or_verify(path, value):
    if path.exists():
        if read(path) != value:
            raise ValueError('Refusing to change a retained evaluation: ' + str(path))
    else:
        with path.open('x') as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write('\n')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--edition', type=Path, required=True)
    p.add_argument('--run', type=Path, required=True)
    a = p.parse_args()
    edition, run = a.edition.resolve(), a.run.resolve()
    manifest, binding, plan = read(edition / 'manifest.json'), read(run / 'source-binding.json'), read(run / 'plan.json')
    if binding['manifestSha256'] != sha(edition / 'manifest.json') or not binding['actualCandidateRun']:
        raise ValueError('Candidate trial edition/role mismatch')
    cases = {c['id']: c for c in manifest['cases']}
    for case in plan:
        if case['caseId'] not in cases or [t['id'] for t in case['turns']] != [t['id'] for t in cases[case['caseId']]['turns']]:
            raise ValueError('Candidate plan/edition mismatch')
        for turn in case['turns']:
            if not (run / 'runs' / case['caseId'] / turn['id'] / 'capture.json').exists():
                raise ValueError('Trial is incomplete; no complete score will be reported')
    results, previous, case_results, threads = [], [], [], set()
    for case in plan:
        current = []
        thread = None
        for turn in case['turns']:
            directory = run / 'runs' / case['caseId'] / turn['id']
            dispatch, capture = read(directory / 'dispatch.json'), read(directory / 'capture.json')
            events = [json.loads(line) for line in (directory / 'events.jsonl').read_text().splitlines() if line]
            if not dispatch['actualModelCall'] or dispatch['model'] != binding['model'] or not any(e.get('type') == 'turn.completed' for e in events):
                raise ValueError('A completed actual candidate call is missing')
            if thread is None:
                if dispatch['parentThread'] is not None or capture['threadId'] in threads:
                    raise ValueError('Candidate cases do not have independent conversations')
                threads.add(capture['threadId'])
            elif dispatch['parentThread'] != thread or capture['threadId'] != thread:
                raise ValueError('Candidate conversation continuity differs')
            thread = capture['threadId']
            with tempfile.TemporaryDirectory(prefix='challenge-v3-replay-') as tmp:
                output = Path(tmp) / 'result.json'
                proc = subprocess.run(['node', str(ROOT / 'scripts/challenge/evaluate-v3.cjs'),
                                       '--edition', str(edition), '--run', str(run), '--case', case['caseId'],
                                       '--turn', turn['id'], '--output', str(output)],
                                      capture_output=True, text=True, timeout=90)
                if proc.returncode not in (0, 1):
                    raise RuntimeError(proc.stderr)
                value = read(output)
            save_or_verify(directory / 'evaluation-v3.json', value)
            previous.append(read(directory / 'evaluation.json'))
            results.append(value)
            current.append(value)
        case_results.append({'caseId': case['caseId'], 'category': cases[case['caseId']]['category'],
                             'passed': all(r['passed'] for r in current), 'passedTurns': sum(r['passed'] for r in current),
                             'turns': len(current)})
    implementation = [ROOT / 'scripts/challenge' / name for name in
                      ('evaluate.cjs', 'evaluate-v2.cjs', 'evaluate-v3.cjs', 'physical-view-v2.cjs', 'physical-view-v3.cjs')]
    summary = {'schemaVersion': 1, 'edition': manifest['edition'], 'model': binding['model'],
               'reasoningEffort': binding['reasoningEffort'], 'evaluatorVersion': 'challenge-v3-physical-equivalence',
               'manifestSha256': binding['manifestSha256'], 'candidateAnswersChanged': False,
               'requestsOrNumericalTolerancesChanged': False, 'postHocEvaluatorCorrections': True,
               'feedbackToCandidate': False, 'partial': len(plan) != len(cases),
               'caseResults': case_results, 'passedCases': sum(c['passed'] for c in case_results),
               'cases': len(case_results), 'passedTurns': sum(r['passed'] for r in results), 'turns': len(results),
               'originalEvaluatorPassedTurns': sum(r['passed'] for r in previous),
               'actualCallsVerified': len(results), 'independentCaseThreadsVerified': len(threads),
               'implementationFiles': [{'path': str(f.relative_to(ROOT)), 'sha256': sha(f)} for f in implementation],
               'failures': [r for r in results if not r['passed']]}
    save_or_verify(run / 'summary-v3.json', summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
