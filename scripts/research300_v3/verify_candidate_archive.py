"""Verify candidate evidence and regrade using only the sealed Node sources."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import zipfile

if __package__:
    from .verify_archive import CHUNK, SplitReader, require, safe_name, sha
else:
    from verify_archive import CHUNK, SplitReader, require, safe_name, sha


def diagnostic_paths(grade, roots):
    """Only filesystem diagnostics may change when evidence is relocated."""
    result = json.loads(json.dumps(grade))
    for row in result['rows']:
        if isinstance(row.get('error'), str) and re.match(r'^(ENOENT|EACCES|ENOTDIR|EISDIR|EPERM|ELOOP|EBUSY|EROFS|ENOSPC|EMFILE|ENFILE)\b', row['error']):
            for kind, root in roots.items():
                row['error'] = row['error'].replace(str(root), '$' + kind.upper())
    return result


def dispatch_path(name):
    parts = name.split('/')
    return (parts[:2] == ['work', 'runs'] and len(parts) == 5 and parts[-1] == 'dispatch.json'
            or parts[:2] == ['work', 'interrupted-attempts'] and len(parts) == 6 and parts[-1] == 'dispatch.json')


def receipt_path(name):
    parts = name.split('/')
    return parts[:2] == ['work', 'solver-jobs'] and len(parts) == 5 and parts[-1] == 'broker-receipt.json'


def verify(review, replay=False, timeout=3600):
    review = Path(review).resolve()
    meta = json.loads((review / 'archive.json').read_text())
    manifest = json.loads((review / 'archive-manifest.json').read_text())
    require(meta.get('schemaVersion') == manifest.get('schemaVersion') == 1
            and meta.get('kind') == 'research300-v3-full-candidate', 'Unsupported candidate archive schema')
    require(meta.get('format') == 'concatenated-standard-zip', 'Unsupported candidate volume format')
    require(sha(review / 'archive-manifest.json') == meta['manifestSha256'], 'Candidate manifest checksum differs')
    parts = []
    for index, row in enumerate(meta['parts'], 1):
        name = safe_name(row['file'])
        require(name == f'evidence.zip.part{index:03}.bin', 'Candidate volume order/name differs')
        part = review / name
        require(not part.is_symlink() and part.is_file() and 0 < part.stat().st_size == row['bytes'] < 90 * CHUNK,
                'Candidate volume is missing, unsafe or has the wrong size')
        require(sha(part) == row['sha256'], 'Candidate volume checksum differs: ' + name)
        parts.append(part)
    require(bool(parts), 'Candidate archive has no volumes')
    files = {safe_name(row['path']): row for row in manifest['files']}
    require(len(files) == len(manifest['files']), 'Candidate manifest repeats a file')
    require(not any(r['path'] in files for r in meta['excludedFiles']), 'Excluded private file was retained')
    with SplitReader(parts) as stream, zipfile.ZipFile(stream) as bundle:
        entries = bundle.infolist()
        require(len(entries) == len(files) and {r.filename for r in entries} == set(files), 'Candidate ZIP inventory differs')
        for entry in entries:
            require(not entry.is_dir() and (entry.external_attr >> 16) & 0o170000 != 0o120000,
                    'Candidate ZIP contains a directory or symlink')
            digest, size = hashlib.sha256(), 0
            with bundle.open(entry) as source:
                while data := source.read(CHUNK):
                    digest.update(data)
                    size += len(data)
            expected_file = files[entry.filename]
            require(size == expected_file['bytes'] and digest.hexdigest() == expected_file['sha256'],
                    'Candidate archived file differs: ' + entry.filename)

        def read(name):
            return json.loads(bundle.read(safe_name(name)))

        def digest(name):
            require(name in files, 'Missing candidate archive dependency: ' + name)
            return files[name]['sha256']

        edition, binding, execution, grade = map(read, ('edition/manifest.json', 'work/candidate-binding.json',
                                                       'work/execution-summary.json', 'grade.json'))
        edition_hash = digest('edition/manifest.json')
        require(edition_hash == meta['editionManifestSha256'], 'Frozen candidate edition differs')
        for row in edition['files']:
            require(digest('edition/' + safe_name(row['path'])) == row['sha256'], 'Candidate edition file differs: ' + row['path'])
        require(digest('work/candidate-binding.json') == meta['candidateBindingSha256'], 'Candidate binding differs')
        require(digest('grade.json') == meta['gradeSha256'], 'Candidate expected grade differs')
        require(binding.get('fullSuite') is True and binding.get('graderFeedbackDuringRun') is False,
                'Wrong candidate scope or feedback policy')
        require(all(v['manifestSha256'] == edition_hash for v in (binding, execution, grade)), 'Candidate edition role binding differs')
        cases = {c['id']: c for c in edition['cases']}
        require(len(binding['cases']) == len(set(binding['cases'])) == len(cases)
                and set(binding['cases']) == set(cases), 'Candidate case selection differs')
        issued = {(cid, t['id']) for cid, c in cases.items() for t in c['turns']}
        expected_rows = [(cid, t['id']) for cid in binding['cases'] for t in cases[cid]['turns']]
        require([(r['caseId'], r['turnId']) for r in grade['rows']] == expected_rows, 'Candidate grade turn order/inventory differs')
        require(grade['cases'] == meta['caseCount'] == len(cases) and grade['turns'] == meta['turnCount'] == len(issued),
                'Candidate case/turn totals differ')
        require(grade['passed'] == meta['passedTurns'] == sum(r['passed'] is True for r in grade['rows'])
                and grade['failed'] == meta['failedTurns'] == len(issued) - grade['passed'], 'Candidate outcome totals differ')
        require(grade.get('formalComparisonScore') is False and grade.get('developmentOnly') is False,
                'Candidate experiment role differs')
        captured = [(r['caseId'], r['turnId']) for r in execution['turns']]
        require(len(captured) == len(set(captured)) == meta['capturedTurns'] and set(captured) <= issued,
                'Candidate execution inventory differs')
        for name, checksum in binding['evaluationCode'].items():
            require(digest('implementation/scripts/research300_v3/' + safe_name(name)) == checksum,
                    'Frozen candidate evaluator differs: ' + name)
        require(digest('implementation/scripts/research300_v3/grade_candidate.cjs') == binding['implementation']['grade_candidate.cjs'],
                'Candidate grader was changed after dispatch')
        for name in meta['offlineDependencyClosure']:
            require(safe_name(name).startswith('implementation/') and name in files, 'Missing candidate source closure')
        require(meta['offlineEntry'] in meta['offlineDependencyClosure'], 'Unbound candidate replay entry')
        reviewed = None
        if meta.get('reviewedGrading'):
            revision = meta['reviewedGrading']
            reviewed = read(revision['gradePath'])
            require(digest(revision['gradePath']) == revision['gradeSha256'], 'Reviewed grade checksum differs')
            require(reviewed.get('evaluationRevision') == revision['evaluationRevision'] == 'v3.1'
                    and reviewed.get('frozenFirstGradeSourcesVerified') is True, 'Wrong reviewed scoring revision')
            require(all(reviewed[k] == grade[k] for k in ('manifestSha256', 'cases', 'turns'))
                    and [(r['caseId'], r['turnId']) for r in reviewed['rows']] == expected_rows,
                    'Reviewed candidate turn inventory differs')
            require(reviewed['passed'] == revision['passedTurns'] == sum(r['passed'] is True for r in reviewed['rows'])
                    and reviewed['failed'] == revision['failedTurns'] == len(issued) - reviewed['passed'],
                    'Reviewed outcome totals differ')
            require(reviewed['reviewedEvaluationCode'] == revision['codeBinding']
                    and revision['entry'] in meta['offlineDependencyClosure'], 'Unbound reviewed replay entry')
            for name, checksum in revision['codeBinding'].items():
                require(digest('implementation/scripts/research300_v3/' + safe_name(name)) == checksum,
                        'Reviewed evaluator source differs: ' + name)
        successes = failures = dispatches = 0
        for name in files:
            if dispatch_path(name):
                dispatch = read(name)
                require(dispatch.get('actualModelCall') is True and (dispatch['caseId'], dispatch['turnId']) in issued,
                        'Candidate dispatch role/identity differs')
                dispatches += 1
            if not receipt_path(name):
                continue
            receipt = read(name)
            prefix = name.removesuffix('/broker-receipt.json')
            cid, job = prefix.split('/')[-2:]
            require(receipt['caseId'] == cid and receipt['role'] == 'candidate' and type(receipt['ok']) is bool,
                    'Native job is not a same-case candidate execution')
            require(cid in cases and receipt['engine'] == cases[cid]['engine'], 'Candidate used the wrong native engine')
            if receipt['ok']:
                successes += 1
                require(digest(prefix + '/state.json') == receipt['stateSha256'], 'Candidate protected state seal differs')
                require(read(prefix + '/state.json')['model'] == read(prefix + '/model.json'), 'Candidate native state/model differs')
            else:
                failures += 1
        require(successes + failures == meta['nativeJobsRetained'] and successes == meta['successfulNativeJobsRetained']
                and failures == meta['failedNativeJobsRetained'], 'Candidate native job inventory differs')
        for name in files:
            if name.startswith('work/recovery-bindings/') and name.endswith('.json'):
                recovery = read(name)
                require(recovery['manifestSha256'] == edition_hash and recovery['graderFeedbackDuringRun'] is False
                        and recovery['retryCompletedTurns'] is False, 'Candidate recovery policy differs')
                require(digest('work/' + safe_name(recovery['sourceSnapshot'])) == recovery['sourceSha256'],
                        'Executed recovery source snapshot differs')
        require(dispatches == meta['candidateDispatchesDeclaredReal'] == execution['candidateCalls'],
                'Candidate model dispatch inventory differs')
        result = {'allPassed': True, 'filesVerified': len(files), 'volumesVerified': len(parts),
                  'cases': len(cases), 'turns': len(issued), 'capturedTurns': len(captured),
                  'passedTurns': grade['passed'], 'failedTurns': grade['failed'],
                  'actualModelDispatchesRetained': dispatches, 'nativeJobsRetained': successes + failures,
                  'successfulNativeJobsRetained': successes, 'failedNativeJobsRetained': failures,
                  'offlineReplay': None, 'candidateModelsInvoked': False, 'nativeSolversInvoked': False}
        if replay:
            with tempfile.TemporaryDirectory(prefix='research300-v3-candidate-offline-') as temporary:
                root = Path(temporary)
                used_jobs = set()
                for cid, tid in issued:
                    answer_path = f'work/runs/{cid}/{tid}/answer.json'
                    if answer_path not in files:
                        continue
                    try:
                        answer = read(answer_path)
                    except (ValueError, UnicodeError):
                        continue
                    if not isinstance(answer, dict):
                        continue
                    candidates = answer.get('jobIds', [])
                    candidates = list(candidates) if isinstance(candidates, list) else []
                    for field in ('jobIdsByModel', 'jobIdsByScenario'):
                        groups = answer.get(field)
                        if isinstance(groups, dict):
                            for ids in groups.values():
                                if isinstance(ids, list):
                                    candidates.extend(ids)
                    for job in candidates:
                        if isinstance(job, str) and re.fullmatch('[a-f0-9]{32}', job):
                            used_jobs.add(f'work/solver-jobs/{cid}/{job}')
                for name in files:
                    needed = name.startswith('edition/') or name in meta['offlineDependencyClosure']
                    needed = needed or name == 'work/candidate-binding.json'
                    needed = needed or name.startswith('work/runs/') and Path(name).name in ('execution.json', 'answer.json')
                    needed = needed or name.rsplit('/', 1)[0] in used_jobs and Path(name).name in ('state.json', 'model.json', 'broker-receipt.json')
                    if needed:
                        target = root / name
                        target.parent.mkdir(parents=True, exist_ok=True)
                        with bundle.open(name) as source, target.open('xb') as destination:
                            while data := source.read(CHUNK):
                                destination.write(data)
                target = root / 'replayed-grade.json'
                environment = {key: value for key, value in os.environ.items()
                               if key not in ('NODE_OPTIONS', 'NODE_PATH') and 'proxy' not in key.lower()}
                process = subprocess.run(['node', '--max-old-space-size=4096', str(root / meta['offlineEntry']),
                    str(root / 'edition'), str(root / 'work'), str(target)], cwd=root, env=environment,
                    capture_output=True, text=True, timeout=timeout)
                require(process.returncode == 0, 'Archived candidate grader failed: ' + process.stderr[-2000:])
                actual_bytes = target.read_bytes()
                expected_bytes = bundle.read('grade.json')
                actual = json.loads(actual_bytes)
                roots = meta['originalRoots']
                canonical_expected = diagnostic_paths(grade, roots)
                canonical_actual = diagnostic_paths(actual, {'edition': root / 'edition', 'work': root / 'work'})
                require(canonical_actual == canonical_expected,
                        'Candidate regrade differs beyond diagnostic path relocation')
                result['offlineReplay'] = {
                    'cases': actual['cases'], 'turns': actual['turns'], 'passedTurns': actual['passed'],
                    'failedTurns': actual['failed'], 'byteIdenticalGrade': actual_bytes == expected_bytes,
                    'identicalAfterDiagnosticPathRelocation': True,
                    'diagnosticRowsWithRelocatedPaths': sum(a.get('error') != b.get('error') for a, b in zip(actual['rows'], grade['rows'])),
                    'quantitiesOrMetricTolerancesChanged': False,
                    'protectedJobsExtractedForRegrade': len(used_jobs),
                    'allRetainedJobsVerifiedBeforeSelectiveExtraction': True,
                    'source': 'archived candidate submissions, sealed native states and grading closure'}
                if reviewed is not None:
                    target = root / 'replayed-reviewed-grade.json'
                    process = subprocess.run(['node', '--max-old-space-size=4096', str(root / revision['entry']),
                        str(root / 'edition'), str(root / 'work'), str(target)], cwd=root, env=environment,
                        capture_output=True, text=True, timeout=timeout)
                    require(process.returncode == 0, 'Reviewed archived grader failed: ' + process.stderr[-2000:])
                    actual_bytes = target.read_bytes()
                    expected_bytes = bundle.read(revision['gradePath'])
                    actual = json.loads(actual_bytes)
                    require(diagnostic_paths(actual, {'edition': root / 'edition', 'work': root / 'work'}) == diagnostic_paths(reviewed, roots),
                            'Reviewed candidate regrade differs beyond diagnostic path relocation')
                    result['reviewedOfflineReplay'] = {'evaluationRevision': 'v3.1', 'cases': actual['cases'],
                        'turns': actual['turns'], 'passedTurns': actual['passed'], 'failedTurns': actual['failed'],
                        'byteIdenticalGrade': actual_bytes == expected_bytes,
                        'identicalAfterDiagnosticPathRelocation': True, 'sameOriginalCandidateAnswers': True,
                        'quantitiesOrMetricTolerancesChanged': False}
        return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review', type=Path, required=True)
    parser.add_argument('--replay', action='store_true')
    parser.add_argument('--timeout', type=int, default=3600)
    args = parser.parse_args()
    print(json.dumps(verify(args.review, args.replay, args.timeout), indent=2))
