"""Seal full-suite candidate captures and their exact offline grading closure.

Raw failed jobs and submitted answers are retained. Native solvers and models
are never invoked here. Private installation files and symlinks are excluded.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import zipfile

from .archive import base
from .support import ROOT
from .verify_candidate_archive import dispatch_path, receipt_path


def inspect_bytes(data, name):
    """Apply the frozen inspection policy without reopening small NAS files."""
    base.inspect_stream(io.BytesIO(data), name, ())
    if zipfile.is_zipfile(io.BytesIO(data)):
        with zipfile.ZipFile(io.BytesIO(data)) as bundle:
            for row in bundle.infolist():
                nested = row.filename.rstrip('/')
                base.safe_name(nested)
                if base.private_path(nested) or (row.external_attr >> 16) & 0o170000 == 0o120000:
                    raise ValueError('Private file/symlink inside retained ZIP: ' + name)
                if not row.is_dir():
                    with bundle.open(row) as source:
                        base.inspect_stream(source, name + '!' + nested, ())


def collect(folder, prefix, files, excluded):
    folder = Path(folder).resolve()
    for file in sorted(folder.rglob('*')):
        name = base.safe_name(prefix + '/' + file.relative_to(folder).as_posix())
        if file.is_symlink():
            excluded.append({'path': name, 'reason': 'symlink-not-followed'})
        elif file.is_file():
            if base.private_path(name) or '__pycache__' in file.parts or file.suffix == '.pyc':
                excluded.append({'path': name, 'reason': 'private-installation-or-generated-cache'})
            else:
                if name in files:
                    raise ValueError('Repeated archive identity: ' + name)
                files[name] = file


def archive(edition, work, sessions, grade, output, reviews=(), part_bytes=89 * base.CHUNK, reviewed_grade=None):
    edition, work, sessions, grade, output = map(lambda p: Path(p).resolve(),
                                               (edition, work, sessions, grade, output))
    if output.exists() or any(output.is_relative_to(p) for p in (edition, work, sessions)):
        raise ValueError('A fresh archive directory outside the input trees is required')
    manifest = base.read(edition / 'manifest.json')
    binding = base.read(work / 'candidate-binding.json')
    execution = base.read(work / 'execution-summary.json')
    expected = base.read(grade)
    edition_hash = base.sha(edition / 'manifest.json')
    if not binding.get('fullSuite') or set(binding['cases']) != {c['id'] for c in manifest['cases']}:
        raise ValueError('Full-suite candidate selection is required')
    if any(v.get('manifestSha256') != edition_hash for v in (binding, execution, expected)):
        raise ValueError('Candidate edition binding differs')
    if expected.get('developmentOnly') or expected['turns'] != sum(len(c['turns']) for c in manifest['cases']):
        raise ValueError('Full-suite grade inventory differs')
    for row in manifest['files']:
        path = edition / base.safe_name(row['path'])
        if path.is_symlink() or base.sha(path) != row['sha256']:
            raise ValueError('Frozen edition bytes changed: ' + row['path'])
    for name, checksum in binding['evaluationCode'].items():
        if base.sha(Path(__file__).with_name(name)) != checksum:
            raise ValueError('Frozen evaluator changed during candidate capture: ' + name)
    runtime = [Path(__file__).with_name(n) for n in ('run_candidate.py', 'setup_public.py', 'grade_candidate.cjs')]
    runtime += [ROOT / 'scripts/pilot30/service.py', ROOT / 'scripts/research300/codex_trial/commercial.py']
    for file in runtime:
        if base.sha(file) != binding['implementation'][file.name]:
            raise ValueError('Executed candidate harness changed: ' + file.name)

    reviewed_meta = None
    if reviewed_grade is not None:
        reviewed_grade = Path(reviewed_grade).resolve()
        revised = base.read(reviewed_grade)
        if revised.get('evaluationRevision') != 'v3.1' or not revised.get('frozenFirstGradeSourcesVerified'):
            raise ValueError('Unsupported reviewed grading revision')
        if any(revised[k] != expected[k] for k in ('manifestSha256', 'cases', 'turns')) or [(r['caseId'], r['turnId']) for r in revised['rows']] != [(r['caseId'], r['turnId']) for r in expected['rows']]:
            raise ValueError('Reviewed grade inventory differs from the same captured answers')
        for name, checksum in revised['reviewedEvaluationCode'].items():
            if base.sha(Path(__file__).with_name(base.safe_name(name))) != checksum:
                raise ValueError('Reviewed evaluator changed: ' + name)
        reviewed_meta = {'entry': 'implementation/scripts/research300_v3/grade_candidate_v31.cjs',
                         'gradePath': 'reviewed-grade.json', 'gradeSha256': base.sha(reviewed_grade),
                         'evaluationRevision': 'v3.1', 'codeBinding': revised['reviewedEvaluationCode'],
                         'passedTurns': revised['passed'], 'failedTurns': revised['failed']}
    files, excluded = {}, []
    for folder, prefix in ((edition, 'edition'), (work, 'work'), (sessions, 'sessions')):
        collect(folder, prefix, files, excluded)
    files['grade.json'] = grade
    if reviewed_grade is not None:
        files['reviewed-grade.json'] = reviewed_grade
    closure = base.evaluator_closure(ROOT)
    for file in closure:
        files['implementation/' + file.relative_to(ROOT).as_posix()] = file
    for index, file in enumerate(reviews, 1):
        file = Path(file).resolve()
        if not file.is_file() or file.is_symlink():
            raise ValueError('Review attachment must be a regular file')
        files[f'review/{index:03}-' + file.name] = file
    output.mkdir(parents=True)
    rows, receipts, stream = [], [], base.SplitWriter(output, part_bytes)
    try:
        with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=1) as bundle:
            for index, (name, file) in enumerate(sorted(files.items()), 1):
                before, digest, size = file.stat(), hashlib.sha256(), 0
                cached = file.read_bytes() if before.st_size <= 16 * base.CHUNK else None
                if cached is None:
                    base.inspect_file(file, name, ())
                else:
                    inspect_bytes(cached, name)
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type, info.external_attr = zipfile.ZIP_DEFLATED, 0o100644 << 16
                info._compresslevel = 1
                with bundle.open(info, 'w', force_zip64=True) as target:
                    if cached is not None:
                        target.write(cached)
                        digest.update(cached)
                        size = len(cached)
                    else:
                        with file.open('rb') as source:
                            while data := source.read(base.CHUNK):
                                target.write(data)
                                digest.update(data)
                                size += len(data)
                after = file.stat()
                if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns) or size != after.st_size:
                    raise ValueError('Input changed while sealing: ' + name)
                rows.append({'path': name, 'bytes': size, 'sha256': digest.hexdigest()})
                if receipt_path(name):
                    receipts.append(base.read(file))
                if index % 1000 == 0:
                    print(json.dumps({'sealed': index, 'expected': len(files)}), flush=True)
    finally:
        stream.close()
    base.write(output / 'archive-manifest.json', {'schemaVersion': 1, 'files': rows})
    meta = {
        'schemaVersion': 1, 'kind': 'research300-v3-full-candidate',
        'format': 'concatenated-standard-zip',
        'compression': {'method': 'deflate', 'level': 1, 'lossless': True},
        'parts': [{'file': p.name, 'bytes': p.stat().st_size, 'sha256': base.sha(p)} for p in stream.parts],
        'manifestSha256': base.sha(output / 'archive-manifest.json'),
        'editionManifestSha256': edition_hash,
        'candidateBindingSha256': base.sha(work / 'candidate-binding.json'),
        'gradeSha256': base.sha(grade),
        'caseCount': expected['cases'], 'turnCount': expected['turns'],
        'capturedTurns': len(execution['turns']), 'passedTurns': expected['passed'],
        'failedTurns': expected['failed'], 'nativeJobsRetained': len(receipts),
        'successfulNativeJobsRetained': sum(r['ok'] is True for r in receipts),
        'failedNativeJobsRetained': sum(r['ok'] is False for r in receipts),
        'sutCommit': manifest['sutCommit'], 'runnerCommit': binding['runnerCommit'],
        'nodeVersion': subprocess.check_output(['node', '--version'], text=True).strip(),
        'archivePythonVersion': sys.version.split()[0],
        'originalRoots': {'edition': str(edition), 'work': str(work)},
        'offlineEntry': 'implementation/scripts/research300_v3/grade_candidate.cjs',
        'offlineDependencyClosure': ['implementation/' + p.relative_to(ROOT).as_posix() for p in closure],
        'excludedFiles': excluded, 'candidateRole': True, 'nativeOracleRole': False,
        'candidateDispatchesDeclaredReal': sum(dispatch_path(name) for name in files),
        'formalComparisonScore': False, 'localOnly': True,
    }
    if reviewed_meta is not None:
        meta['reviewedGrading'] = reviewed_meta
    base.write(output / 'archive.json', meta)
    return {'files': len(rows), 'parts': len(stream.parts), 'bytes': sum(r['bytes'] for r in meta['parts']),
            'cases': expected['cases'], 'turns': expected['turns'], 'nativeJobs': len(receipts)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('edition', 'work', 'sessions', 'grade', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--review-file', type=Path, action='append', default=[])
    parser.add_argument('--reviewed-grade', type=Path)
    args = parser.parse_args()
    print(json.dumps(archive(args.edition, args.work, args.sessions, args.grade, args.output, args.review_file, reviewed_grade=args.reviewed_grade), indent=2))
