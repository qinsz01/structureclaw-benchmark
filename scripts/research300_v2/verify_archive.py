"""Verify every archived byte and replay the archived evaluator without solvers.

No installed repository evaluator is used for --replay. Only Python's standard
library and Node.js are needed. Native result files are read, never recomputed.
"""
import argparse
from bisect import bisect_right
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import tempfile
import zipfile

CHUNK = 1024 * 1024


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as file:
        while data := file.read(CHUNK):
            digest.update(data)
    return digest.hexdigest()


def safe_name(name):
    if not isinstance(name, str) or not name or '\\' in name or '\0' in name:
        raise ValueError('Unsafe archive path')
    parts = PurePosixPath(name).parts
    if ':' in parts[0] or PurePosixPath(name).is_absolute() or '..' in parts or str(PurePosixPath(name)) != name:
        raise ValueError('Unsafe archive path')
    return name


def require(condition, message):
    if not condition:
        raise ValueError(message)


class SplitReader(io.RawIOBase):
    def __init__(self, parts):
        super().__init__()
        self.parts, self.offsets, self.position = parts, [0], 0
        self.file, self.index = None, None
        for part in parts:
            self.offsets.append(self.offsets[-1] + part.stat().st_size)

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.position

    def seek(self, offset, whence=0):
        target = offset if whence == 0 else self.position + offset if whence == 1 else self.offsets[-1] + offset
        if whence not in [0, 1, 2] or target < 0:
            raise ValueError('Invalid seek')
        self.position = target
        return target

    def read(self, size=-1):
        remaining = min(size, self.offsets[-1] - self.position) if size >= 0 else self.offsets[-1] - self.position
        output = bytearray()
        while remaining > 0:
            index = bisect_right(self.offsets, self.position) - 1
            if self.index != index:
                if self.file:
                    self.file.close()
                self.file, self.index = self.parts[index].open('rb'), index
            self.file.seek(self.position - self.offsets[index])
            data = self.file.read(min(remaining, self.offsets[index + 1] - self.position))
            if not data:
                raise ValueError('Truncated ZIP volume')
            output.extend(data)
            self.position += len(data)
            remaining -= len(data)
        return bytes(output)

    def close(self):
        if self.file:
            self.file.close()
        super().close()


def verify(review, replay=False, timeout=1200):
    review = Path(review).resolve()
    meta = json.loads((review / 'archive.json').read_text())
    manifest = json.loads((review / 'archive-manifest.json').read_text())
    require(meta.get('schemaVersion') == manifest.get('schemaVersion') == 2, 'Unsupported archive schema')
    require(meta.get('format') == 'concatenated-standard-zip', 'Unsupported volume format')
    require(sha(review / 'archive-manifest.json') == meta['manifestSha256'], 'Archive manifest checksum differs')
    parts = []
    for index, row in enumerate(meta['parts'], 1):
        name = safe_name(row['file'])
        require(name == f'evidence.zip.part{index:03}.bin', 'ZIP volume order/name differs')
        file = review / name
        require(not file.is_symlink() and file.is_file(), 'ZIP volume is missing or is a symlink')
        require(0 < file.stat().st_size == row['bytes'] < 90 * CHUNK and sha(file) == row['sha256'],
                'ZIP volume checksum/size differs: ' + name)
        parts.append(file)
    require(bool(parts), 'Archive has no volumes')
    files = {safe_name(row['path']): row for row in manifest['files']}
    require(len(files) == len(manifest['files']), 'Archive manifest repeats a path')
    require(not any(row['path'] in files for row in meta['excludedFiles']), 'Excluded private file was archived')
    with SplitReader(parts) as stream, zipfile.ZipFile(stream) as bundle:
        entries = bundle.infolist()
        require(len(entries) == len(files) and {row.filename for row in entries} == set(files), 'ZIP members differ from manifest')
        for row in entries:
            require(not row.is_dir() and (row.external_attr >> 16) & 0o170000 != 0o120000, 'Unexpected directory/symlink in ZIP')
            digest, size = hashlib.sha256(), 0
            with bundle.open(row) as file:
                while data := file.read(CHUNK):
                    digest.update(data)
                    size += len(data)
            expected = files[row.filename]
            require(size == expected['bytes'] and digest.hexdigest() == expected['sha256'], 'Archived file differs: ' + row.filename)

        def value(name):
            return json.loads(bundle.read(safe_name(name)))

        def digest(name):
            require(name in files, 'Missing required archive file: ' + name)
            return files[name]['sha256']

        edition = value('edition/manifest.json')
        edition_hash = digest('edition/manifest.json')
        require(edition_hash == meta['editionManifestSha256'], 'Edition manifest binding differs')
        for row in edition['files']:
            require(digest('edition/' + safe_name(row['path'])) == row['sha256'], 'Edition contents differ: ' + row['path'])
        expected = value('qualification/summary.json')
        require(digest('qualification/summary.json') == meta['qualificationSummarySha256'], 'Qualification binding differs')
        require(expected['manifestSha256'] == edition_hash and expected['allPassed'] and expected['fullEditionCoverage']
                and expected['failedControls'] == 0 and expected['candidateCalls'] == 0, 'Qualification was not a complete pass')
        cases = {case['id']: case for case in edition['cases']}
        require(len(cases) == len(edition['cases']), 'Duplicate edition case identity')
        work_for_case, works, case_attempts, batch_descriptors = {}, {}, {}, []
        runtime_sources = {(row['batch'], row['path']): row for row in meta.get('runtimeSources', [])}
        seen_runtime_sources = set()
        require(len(runtime_sources) == len(meta.get('runtimeSources', [])), 'Duplicate runtime source binding')
        for index, binding in enumerate(meta['workBatches'], 1):
            prefix = safe_name(binding['prefix'])
            require(prefix == f'works/{index:03}', 'Invalid work prefix/order')
            summary_file = safe_name(binding.get('summaryFile', 'execution-summary.json'))
            if prefix + '/execution-summary.json' in files:
                require(summary_file == 'execution-summary.json', 'Closed completion marker was not selected')
            else:
                attempts, plans = [], set()
                for name in files:
                    if name.startswith(prefix + '/execution-attempts/') and name.endswith('.json'):
                        attempt = value(name)
                        require(attempt['manifestSha256'] == edition_hash and isinstance(attempt.get('finishedAt'), str),
                                'Attempt manifest/time binding differs')
                        attempts.append((attempt['finishedAt'], name.removeprefix(prefix + '/')))
                        plans.add(tuple(sorted(attempt.get('caseIds') or {row['caseId'] for row in attempt['turns']})))
                require(attempts and max(attempts)[1] == summary_file, 'Latest closed execution attempt was not selected')
                require(len(plans) == 1, 'Closed attempts have different execution plans')
                require(sum(time == max(attempts)[0] for time, _ in attempts) == 1, 'Latest closed attempt is ambiguous')
            summary = value(prefix + '/' + summary_file)
            require(digest(prefix + '/' + summary_file) == binding['executionSummarySha256'], 'Execution summary binding differs')
            require(summary['manifestSha256'] == edition_hash and summary.get('candidateCalls') == 0, 'Wrong-edition/role batch')
            require(summary_file != 'execution-summary.json' or summary.get('allSucceeded') is not False, 'Invalid completion marker')
            ids = summary.get('caseIds') or sorted({row['caseId'] for row in summary['turns']})
            require(set(ids) == set(binding['caseIds']) and len(ids) == len(set(ids)), 'Execution case inventory differs')
            rows = {(row['caseId'], row['turnId']): row for row in summary['turns']}
            require(len(rows) == len(summary['turns']), 'Duplicate summary turn')
            require(all(cid in ids and cid in cases and any(t['id'] == tid for t in cases[cid]['turns']) for cid, tid in rows),
                    'Unknown summary turn')
            if 'caseBatches' in meta:
                require(all(type(row.get('executionPrepared')) is bool for row in rows.values()), 'Nonterminal execution summary row')
            complete, incomplete, closed_native = [], [], set()
            for cid in ids:
                require(cid in cases, 'Unknown executed case')
                case_attempts.setdefault(cid, []).append(index)
                completed_turns, incomplete_turns = [], []
                for turn in cases[cid]['turns']:
                    capture_file = f'{prefix}/runs/{cid}/{turn["id"]}/capture.json'
                    row = rows.get((cid, turn['id']))
                    if 'caseBatches' in meta:
                        require(row is not None, 'Closed summary omits a planned turn')
                    capture = value(capture_file) if capture_file in files else None
                    if capture:
                        require(capture['caseId'] == cid and capture['turnId'] == turn['id']
                                and capture['manifestSha256'] == edition_hash and capture['maintainerOracle'] is True
                                and capture['candidateCall'] is False, 'Capture identity/role differs')
                    closed = row and (row.get('executionPrepared') is True
                        or 'executionPrepared' not in row and summary.get('allSucceeded') is not False)
                    if closed and capture:
                        completed_turns.append(turn['id'])
                        for jid in capture['currentJobIds']:
                            require(jid not in closed_native, 'A batch repeats a fresh native job')
                            closed_native.add(jid)
                    else:
                        incomplete_turns.append(turn['id'])
                if incomplete_turns:
                    incomplete.append({'caseId': cid, 'completedTurns': completed_turns, 'incompleteTurns': incomplete_turns})
                else:
                    require(cid not in work_for_case, 'Case has duplicate complete execution batches')
                    work_for_case[cid] = prefix
                    complete.append(cid)
            require(len(closed_native) == summary['nativeJobs'], 'Execution native job count differs')
            require(summary.get('allSucceeded') is False or not incomplete, 'Completed batch has incomplete evidence')
            if 'completeCaseIds' in binding:
                require(binding['completeCaseIds'] == complete and binding['incompleteCases'] == incomplete,
                        'Whole-case completion inventory differs')
            batch_descriptors.append({'batch': index, 'summaryFile': summary_file,
                'summarySha256': binding['executionSummarySha256'], 'allSucceeded': summary.get('allSucceeded') is not False,
                'caseIds': ids, 'completeCaseIds': complete, 'incompleteCases': incomplete,
                'recordedNativeJobs': summary['nativeJobs']})
            require(prefix not in works, 'Repeated execution batch')
            works[prefix] = summary
            runtime_path = prefix + '/runtime-binding.json'
            if runtime_path in files:
                runtime = value(runtime_path)
                require(runtime['manifestSha256'] == edition_hash and runtime['sutCommit'] == edition['sutCommit'], 'Runtime binding differs')
                plan = runtime['plan']
                require(len(plan) == len(ids) and {row['caseId'] for row in plan} == set(ids)
                        and all(row['engine'] == cases[row['caseId']]['engine'] for row in plan), 'Runtime plan differs')
                for name, checksum in runtime['implementation'].items():
                    if 'runtimeSources' in meta:
                        source = runtime_sources.get((index, name))
                        require(source and source['sha256'] == checksum, 'Missing runtime implementation binding: ' + name)
                        seen_runtime_sources.add((index, name))
                        archived = safe_name(source['archivePath'])
                        permitted = ['implementation/' + safe_name(name),
                            prefix + '/implementation-snapshots/' + checksum + '/' + safe_name(name)]
                        require(archived in permitted, 'Runtime snapshot belongs to another execution batch')
                    else:
                        archived = 'implementation/' + safe_name(name)
                    require(digest(archived) == checksum, 'Executed implementation bytes differ: ' + name)
            remote_path = prefix + '/remote-source-manifest.json'
            if remote_path in files:
                for row in value(remote_path):
                    require(digest('sut/' + safe_name(row['path']).removeprefix('upstream/')) == row['sha256'],
                            'Remote source snapshot differs: ' + row['path'])
        require(set(work_for_case) == set(cases), 'Execution batches do not cover every case')
        require(seen_runtime_sources == set(runtime_sources), 'Unexpected runtime source binding')
        case_batches = {cid: int(work_for_case[cid].split('/')[1]) for cid in cases}
        recovered = [{'caseId': cid, 'completedBatch': case_batches[cid],
            'incompleteBatches': [index for index in case_attempts[cid] if index != case_batches[cid]]}
            for cid in cases if len(case_attempts[cid]) > 1]
        unfinished = [{key: row[key] for key in ['batch', 'summaryFile', 'summarySha256', 'incompleteCases']}
                      for row in batch_descriptors if row['incompleteCases']]
        if 'caseBatches' in meta:
            require(meta['caseBatches'] == case_batches and meta['recoveredCases'] == recovered, 'Recovered case binding differs')
        if 'executionBatches' in expected:
            require(expected['executionBatches'] == batch_descriptors and expected['recoveredCases'] == recovered,
                    'Qualified batch/recovery summary differs')
        if 'unfinishedAttempts' in meta or 'unfinishedAttempts' in expected:
            require(meta.get('unfinishedAttempts') == expected.get('unfinishedAttempts') == unfinished,
                    'Unfinished original-attempt inventory differs')
        job_ids, turn_count, engine_jobs = set(), 0, {}
        for cid, case in cases.items():
            prefix = work_for_case[cid]
            for turn in case['turns']:
                capture = value(f'{prefix}/runs/{cid}/{turn["id"]}/capture.json')
                require(capture['caseId'] == cid and capture['turnId'] == turn['id']
                        and capture['manifestSha256'] == edition_hash and capture['maintainerOracle'] is True
                        and capture['candidateCall'] is False, 'Capture identity/role differs')
                require(len(capture['jobIds']) == len(set(capture['jobIds']))
                        and set(capture['currentJobIds']) <= set(capture['jobIds']), 'Capture job inventory differs')
                for jid in capture['jobIds']:
                    require(re.fullmatch('[a-f0-9]{32}', jid) is not None, 'Unsafe native job identity')
                    root = f'{prefix}/solver-jobs/{cid}/{jid}'
                    receipt = value(root + '/broker-receipt.json')
                    # The public client spools compact, insertion-ordered JSON;
                    # the broker separately retains an indented request copy.
                    request_bytes = (json.dumps(value(root + '/request.json'), ensure_ascii=False,
                                                allow_nan=False) + '\n').encode()
                    request_hash = hashlib.sha256(request_bytes).hexdigest()
                    require(receipt['ok'] is True and receipt['caseId'] == cid and receipt['engine'] == case['engine']
                            and receipt['role'] == 'oracle' and receipt['stateSha256'] == digest(root + '/state.json')
                            and receipt['requestSha256'] == request_hash, 'Protected native receipt differs')
                    state = value(root + '/state.json')
                    require(state['model'] == value(root + '/model.json'), 'Protected state/model identity differs')
                for jid in capture['currentJobIds']:
                    require(jid not in job_ids, 'Native job counted as fresh on more than one turn')
                    job_ids.add(jid)
                    engine_jobs[case['engine']] = engine_jobs.get(case['engine'], 0) + 1
                turn_count += 1
        failed, retained_successful = 0, 0
        for name in files:
            if name.endswith('/broker-receipt.json'):
                receipt = value(name)
                if name.startswith('works/'):
                    require(receipt.get('role') == 'oracle', 'A retained final-batch job has a non-oracle role')
                    receipt_parts = PurePosixPath(name).parts
                    require(len(receipt_parts) == 6 and receipt_parts[2] == 'solver-jobs' and receipt_parts[3] in cases
                            and receipt.get('caseId') == receipt_parts[3] and receipt.get('engine') == cases[receipt_parts[3]]['engine'],
                            'Retained receipt case/engine identity differs')
                if not receipt['ok']:
                    failed += 1
                else:
                    retained_successful += 1
                    if name.startswith('works/'):
                        prefix = name.removesuffix('/broker-receipt.json')
                        require(receipt.get('stateSha256') == digest(prefix + '/state.json'), 'Retained successful job state seal differs')
                        request_bytes = (json.dumps(value(prefix + '/request.json'), ensure_ascii=False, allow_nan=False) + '\n').encode()
                        require(receipt['requestSha256'] == hashlib.sha256(request_bytes).hexdigest(), 'Retained request seal differs')
                        require(value(prefix + '/state.json')['model'] == value(prefix + '/model.json'), 'Retained state/model differs')
        require(len(job_ids) == meta['nativeJobs'], 'Selected native job count differs')
        if 'retainedSuccessfulJobs' in meta:
            require(retained_successful == meta['retainedSuccessfulJobs'], 'Retained successful-job inventory differs')
        require(failed == meta['failedMaintainerJobsRetained'], 'Failed attempt inventory differs')
        require(len(cases) == expected['cases'] == meta['caseCount'] and turn_count == expected['turns'] == meta['turnCount'],
                'Case/turn count differs')
        require(expected['passedTurns'] == turn_count, 'Not every retained turn passed')
        require(meta['candidateCalls'] == 0 and meta['fullEditionCoverage'], 'Archive scope differs')
        if job_ids:
            require(meta['sutCommit'] == edition['sutCommit'], 'Pinned SUT identity differs')
        for name in meta['offlineDependencyClosure']:
            require(safe_name(name).startswith('implementation/') and name in files, 'Missing offline source dependency')
        require(meta['offlineEntry'] in meta['offlineDependencyClosure'], 'Offline entry is not byte-bound')
        result = {'filesVerified': len(files), 'volumesVerified': len(parts), 'caseCount': len(cases),
                  'turnCount': turn_count, 'nativeJobs': len(job_ids), 'nativeJobsByEngine': engine_jobs,
                  'failedJobsRetained': failed, 'candidateCalls': 0, 'controls': expected['controls'],
                  'recoveredCases': recovered, 'retainedSuccessfulJobs': retained_successful,
                  'allPassed': True, 'offlineReplay': None}
        if replay:
            with tempfile.TemporaryDirectory(prefix='research300-v2-offline-') as temporary:
                root = Path(temporary)
                for name in files:
                    needed = name.startswith('edition/') or name in meta['offlineDependencyClosure']
                    needed = needed or any(name in [prefix + '/execution-summary.json', prefix + '/runtime-binding.json']
                        or name.startswith(prefix + '/execution-attempts/') for prefix in works)
                    needed = needed or name.startswith('works/') and (
                        '/runs/' in name and Path(name).name in ['capture.json', 'scheme-jobs.json']
                        or '/solver-jobs/' in name and Path(name).name in ['state.json', 'model.json', 'request.json', 'broker-receipt.json'])
                    if needed:
                        target = root / name
                        target.parent.mkdir(parents=True, exist_ok=True)
                        with bundle.open(name) as source, target.open('xb') as destination:
                            while data := source.read(CHUNK):
                                destination.write(data)
                environment = {key: value for key, value in os.environ.items()
                               if key not in ['NODE_OPTIONS', 'NODE_PATH'] and 'proxy' not in key.lower()}
                process = subprocess.run(['node', str(root / meta['offlineEntry']), '--edition', str(root / 'edition'),
                    '--work', ','.join(str(root / prefix) for prefix in works), '--output', str(root / 'replay')],
                    capture_output=True, text=True, cwd=root, env=environment, timeout=timeout)
                require(process.returncode == 0, 'Offline evaluator failed: ' + process.stderr[-1500:] + process.stdout[-1500:])
                actual_files = {file.relative_to(root / 'replay').as_posix(): file
                                for file in (root / 'replay').rglob('*') if file.is_file()}
                expected_files = {name.removeprefix('qualification/') for name in files if name.startswith('qualification/')}
                require(set(actual_files) == expected_files, 'Offline output file inventory differs')
                for name, file in actual_files.items():
                    require(file.read_bytes() == bundle.read('qualification/' + name), 'Offline result bytes differ: ' + name)
                result['offlineReplay'] = {'passedTurns': expected['passedTurns'], 'controls': expected['controls'],
                    'failedControls': expected['failedControls'], 'identicalFiles': len(actual_files),
                    'source': 'archived evaluator dependency closure', 'nativeSolversInvoked': False}
        return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review', type=Path, required=True)
    parser.add_argument('--replay', action='store_true')
    parser.add_argument('--timeout', type=int, default=1200)
    args = parser.parse_args()
    print(json.dumps(verify(args.review, args.replay, args.timeout), indent=2))
