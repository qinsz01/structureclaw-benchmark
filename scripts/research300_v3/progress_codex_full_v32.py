"""Read only controller progress; completion does not mean a correct answer."""
import argparse
from collections import Counter
import json
from pathlib import Path
import time


def progress(work, edition):
    manifest = json.loads((edition / 'manifest.json').read_bytes())
    cases = {c['id']: c for c in manifest['cases']}
    started, finished, retries, errors = {}, {}, [], []
    log = work.with_name(work.name + '-runner.log')
    for line in log.read_text().splitlines() if log.exists() else []:
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if 'started' in row:
            started[(row['started'], row['turn'])] = row
        elif 'finished' in row:
            finished[(row['finished'], row['turn'])] = row
        elif 'transportRecovery' in row:
            retries.append(row)
        elif 'error' in row or 'collectorError' in row:
            errors.append(row)
    counts = Counter(row['status'] for row in finished.values())
    case_done = [cid for cid, c in cases.items() if all((cid, t['id']) in finished for t in c['turns'])]
    result = {'kind': 'research300-v32-full-live-progress', 'updatedAt': time.time(), 'formalComparisonScore': False,
              'plannedCases': 300, 'plannedTurns': 560, 'startedTurns': len(started), 'capturedTurns': len(finished),
              'completedAnswers': counts['completed'], 'caseWorkflowsCaptured': len(case_done),
              'candidateStatuses': dict(counts), 'nativeAttemptsInFinishedTurns': sum(r['jobs'] for r in finished.values()),
              'transportRecoveries': len(retries), 'controllerErrors': errors,
              'active': [{'caseId': cid, 'turnId': tid, 'engine': cases[cid]['engine']} for cid, tid in started if (cid, tid) not in finished],
              'byEngine': {e: {'completedAnswers': sum(r['status'] == 'completed' and cases[cid]['engine'] == e for (cid, _), r in finished.items()),
                               'plannedTurns': sum(len(c['turns']) for c in cases.values() if c['engine'] == e)} for e in ('OpenSees', 'PKPM', 'YJK')},
              'gradingStatus': 'not-run; live completion counts are not pass counts'}
    launch_path = work.with_name(work.name + '-launch.json')
    if launch_path.exists():
        launch = json.loads(launch_path.read_bytes())
        process = Path('/proc') / str(launch['pid']) / 'stat'
        result['runnerAlive'] = process.exists() and process.read_text().rsplit(')', 1)[1].strip().split()[0] != 'Z'
        result['elapsedSeconds'] = time.time() - launch['startedAt']
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work', type=Path, required=True)
    p.add_argument('--edition', type=Path, required=True)
    p.add_argument('--output', type=Path)
    a = p.parse_args()
    result = progress(a.work.resolve(), a.edition.resolve())
    if a.output:
        a.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = a.output.with_suffix('.tmp')
        temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
        temporary.replace(a.output)
    print(json.dumps(result, ensure_ascii=False))
