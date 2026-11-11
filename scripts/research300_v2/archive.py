"""Freeze a completed edition, all execution batches and offline evaluator sources.

Volumes are consecutive bytes of one standard ZIP, each smaller than 90 MiB.
No native solver is invoked. The output must be a fresh directory. Failed jobs
inside the selected works and explicitly supplied earlier attempts are retained.
"""
from contextlib import ExitStack
import argparse
import fcntl
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[2]
ENTRY = 'scripts/research300_v2/qualify.cjs'
CHUNK = 1024 * 1024
SECRET_KEY = re.compile(r'(?i)^(?:password|passwd|passphrase|secret|token|client[_-]?secret|api[_-]?key|access[_-]?token|auth[_-]?token|private[_-]?key)$')
KEY_MARKER = re.compile(br'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----')


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    with Path(path).open('x') as file:
        file.write(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as file:
        while data := file.read(CHUNK):
            digest.update(data)
    return digest.hexdigest()


def safe_name(name):
    parts = PurePosixPath(name).parts
    if not isinstance(name, str) or not name or '\\' in name or '\0' in name or ':' in parts[0] \
            or PurePosixPath(name).is_absolute() or '..' in parts or str(PurePosixPath(name)) != name:
        raise ValueError('Unsafe archive path')
    return name


def private_path(name):
    parts = [part.lower() for part in PurePosixPath(name).parts]
    base = parts[-1]
    return (base == 'remote-setup.json' or base == '.env' or base.startswith('.env.')
            or base in {'credentials', 'credentials.json', 'secrets.json', 'id_rsa', 'id_ed25519'}
            or base.endswith(('.pem', '.key', '.p12', '.pfx')) or '.ssh' in parts)


def secret_values(value):
    result = []
    if isinstance(value, dict):
        for key, item in value.items():
            if SECRET_KEY.fullmatch(str(key)) and isinstance(item, str) and item:
                result.append(item)
            result.extend(secret_values(item))
    elif isinstance(value, list):
        for item in value:
            result.extend(secret_values(item))
    return result


def inspect_stream(stream, name, secrets=()):
    """Reject rather than silently rewrite evidence containing credentials."""
    overlap, prefix = b'', bytearray()
    patterns = [value.encode() for value in secrets if len(value) >= 4]
    patterns += [value.encode('utf-16-le') for value in secrets if len(value) >= 4]
    keep = max([2048, *[len(value) for value in patterns]])
    while data := stream.read(CHUNK):
        block = overlap + data
        if KEY_MARKER.search(block) or any(value in block for value in patterns):
            raise ValueError('Credential material in retained file: ' + name)
        if name.lower().endswith('.json'):
            prefix.extend(data)
        overlap = block[-keep:]
    if name.lower().endswith('.json'):
        try:
            values = secret_values(json.loads(prefix))
        except (ValueError, UnicodeError):
            values = []
        if values:
            raise ValueError('Credential field in retained JSON: ' + name)


def inspect_file(path, name, secrets):
    with path.open('rb') as file:
        inspect_stream(file, name, secrets)
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            for row in archive.infolist():
                nested = row.filename.rstrip('/')
                safe_name(nested)
                if private_path(nested) or (row.external_attr >> 16) & 0o170000 == 0o120000:
                    raise ValueError('Private file/symlink inside retained ZIP: ' + name)
                if not row.is_dir():
                    with archive.open(row) as file:
                        inspect_stream(file, name + '!' + nested, secrets)


class SplitWriter(io.RawIOBase):
    def __init__(self, folder, limit):
        super().__init__()
        self.folder, self.limit, self.position = folder, limit, 0
        self.parts, self.current, self.used = [], None, 0

    def writable(self):
        return True

    def tell(self):
        return self.position

    def write(self, data):
        total = len(data)
        while data:
            if self.current is None or self.used == self.limit:
                if self.current:
                    self.current.close()
                file = self.folder / f'evidence.zip.part{len(self.parts) + 1:03}.bin'
                self.parts.append(file)
                self.current, self.used = file.open('xb'), 0
            count = min(len(data), self.limit - self.used)
            self.current.write(data[:count])
            data = data[count:]
            self.position += count
            self.used += count
        return total

    def close(self):
        if self.current:
            self.current.close()
        super().close()


def evaluator_closure(root=ROOT):
    """Resolve every literal require used by the offline qualification entry."""
    pending, found = [root / ENTRY], set()
    builtins = set(json.loads(subprocess.check_output(
        ['node', '-e', 'process.stdout.write(JSON.stringify(require("module").builtinModules))'], text=True)))
    while pending:
        file = pending.pop().resolve()
        if file in found:
            continue
        if not file.is_relative_to(root) or not file.is_file():
            raise ValueError('Missing/outside evaluator dependency')
        found.add(file)
        source = file.read_text()
        calls = re.findall(r'\brequire\s*\(([^\n;]+?)\)', source)
        for call in calls:
            literal = re.fullmatch(r'\s*[\'"]([^\'"]+)[\'"]\s*', call)
            if not literal:
                raise ValueError('Unresolved dynamic evaluator dependency: ' + str(file.relative_to(root)))
            name = literal.group(1)
            if name.startswith('.'):
                dependency = file.parent / name
                if not dependency.is_file():
                    options = [Path(str(dependency) + suffix) for suffix in ['.cjs', '.js', '.json']]
                    dependency = next((p for p in options if p.is_file()), dependency)
                pending.append(dependency)
            elif name.removeprefix('node:') not in builtins:
                raise ValueError('External evaluator package is not archived: ' + name)
    return sorted(found)


def archive(edition, works, qualification, output, sut=None, attempts=(), reviews=(), part_bytes=89 * CHUNK):
    edition, qualification, output = [Path(p).resolve() for p in [edition, qualification, output]]
    works = [Path(p).resolve() for p in works]
    attempts = [Path(p).resolve() for p in attempts]
    reviews = [Path(p).resolve() for p in reviews]
    if not 1024 <= part_bytes < 90 * CHUNK:
        raise ValueError('Each ZIP volume must be at least 1 KiB and smaller than 90 MiB')
    if output.exists():
        raise FileExistsError('A fresh archive directory is required')
    if len(works) != len(set(works)) or not works:
        raise ValueError('Execution batches must be unique and nonempty')
    for source in [edition, qualification, *works, *attempts, *reviews]:
        if not source.exists() or output.is_relative_to(source) or source.is_relative_to(output):
            raise ValueError('Archive source/output paths overlap or source is absent')
    manifest, expected = read(edition / 'manifest.json'), read(qualification / 'summary.json')
    manifest_hash = sha(edition / 'manifest.json')
    if expected.get('manifestSha256') != manifest_hash or not expected.get('allPassed') \
            or not expected.get('fullEditionCoverage') or expected.get('failedControls') != 0 \
            or expected.get('candidateCalls') != 0 or expected.get('cases') != len(manifest['cases']):
        raise ValueError('Only a fully qualified complete edition can be archived as final')
    expected_ids = {case['id'] for case in manifest['cases']}
    if len(expected_ids) != len(manifest['cases']):
        raise ValueError('Edition repeats case IDs')
    for row in manifest['files']:
        name = safe_name(row['path'])
        if sha(edition / name) != row['sha256']:
            raise ValueError('Edition file binding differs: ' + name)
    bindings, native_ids = [], set()
    with ExitStack() as stack:
        for work in works:
            if (work / 'runner.lock').exists():
                lock = stack.enter_context((work / 'runner.lock').open('rb'))
                fcntl.flock(lock, fcntl.LOCK_SH | fcntl.LOCK_NB)
        resolved = subprocess.run(['node', str(ROOT / 'scripts/research300_v2/execution_batches.cjs'),
            '--edition', str(edition), '--work', ','.join(map(str, works))], capture_output=True, text=True)
        if resolved.returncode:
            raise ValueError('Execution batches do not cover every case uniquely: ' + resolved.stderr[-2000:])
        resolution = json.loads(resolved.stdout)
        for key in ['executionBatches', 'recoveredCases', 'unfinishedAttempts']:
            if key in expected and expected[key] != resolution[key]:
                raise ValueError('Qualification execution selection differs: ' + key)
        for row in resolution['executionBatches']:
            bindings.append({'prefix': f'works/{row["batch"]:03}', 'caseIds': row['caseIds'],
                'completeCaseIds': row['completeCaseIds'], 'incompleteCases': row['incompleteCases'],
                'summaryFile': row['summaryFile'], 'executionSummarySha256': row['summarySha256']})
        for case in manifest['cases']:
            work = works[resolution['caseBatches'][case['id']] - 1]
            for turn in case['turns']:
                capture = read(work / 'runs' / case['id'] / turn['id'] / 'capture.json')
                for identifier in capture['currentJobIds']:
                    if identifier in native_ids:
                        raise ValueError('Native job counted as fresh on multiple selected turns')
                    native_ids.add(identifier)
        native_jobs = len(native_ids)
        if native_jobs and sut is None:
            raise ValueError('Native evidence requires --sut for the pinned production source snapshot')
        files, excluded = {}, []
        secrets = []
        for source in [*works, *attempts]:
            for path in source.rglob('remote-setup.json') if source.is_dir() else []:
                secrets.extend(secret_values(read(path)))

        def add(file, name):
            name = safe_name(name)
            if file.is_symlink() or not file.is_file():
                raise ValueError('Only regular nonsymlink evidence files may be archived: ' + name)
            if private_path(name):
                excluded.append({'path': name, 'reason': 'credential/configuration file excluded'})
                return
            if name in files and files[name] != file:
                if sha(file) != sha(files[name]):
                    raise ValueError('Conflicting archive path: ' + name)
            files[name] = file

        def tree(folder, prefix, extensions=None):
            for file in sorted(folder.rglob('*')):
                if '__pycache__' in file.parts or file.suffix == '.pyc':
                    continue
                if file.is_symlink():
                    raise ValueError('Symlink in archive source: ' + prefix)
                if file.is_file() and (extensions is None or file.suffix in extensions):
                    add(file, prefix + '/' + file.relative_to(folder).as_posix())

        tree(edition, 'edition')
        tree(qualification, 'qualification')
        for work, binding in zip(works, bindings):
            tree(work, binding['prefix'])
        for index, attempt in enumerate(attempts, 1):
            if attempt.is_dir():
                tree(attempt, f'attempts/{index:03}')
            else:
                add(attempt, f'attempts/{index:03}/' + attempt.name)
        for index, review in enumerate(reviews, 1):
            if review.is_dir():
                tree(review, f'reviews/{index:03}')
            else:
                add(review, f'reviews/{index:03}/' + review.name)
        closure = evaluator_closure()
        for file in closure:
            add(file, 'implementation/' + file.relative_to(ROOT).as_posix())
        # Also retain authoring, independent reference and public execution code.
        for relative in ['scripts/research300_v2', 'scripts/pilot30', 'scripts/research300/codex_trial', 'lib']:
            tree(ROOT / relative, 'implementation/' + relative, {'.py', '.cjs', '.json', '.md'})
        for relative in ['scripts/research300/reference_solver.py', 'scripts/research300/capture_structureclaw_worker.py']:
            add(ROOT / relative, 'implementation/' + relative)
        sut_commit = None
        if sut is not None:
            sut = Path(sut).resolve()
            sut_commit = subprocess.check_output(['git', '-c', 'safe.directory=*', '-C', str(sut), 'rev-parse', 'HEAD'], text=True).strip()
            if sut_commit != manifest['sutCommit']:
                raise ValueError('Pinned SUT commit differs')
            if subprocess.check_output(['git', '-c', 'safe.directory=*', '-C', str(sut), 'status', '--porcelain', '--untracked-files=no'], text=True).strip():
                raise ValueError('Tracked SUT source is dirty')
            for relative in ['backend/src/agent-skills/analysis', 'backend/src/skill-shared/python', 'backend/dist/engineering']:
                tree(sut / relative, 'sut/' + relative, {'.py', '.js', '.ts', '.json', '.md'})
            for work in works:
                source_manifest = work / 'remote-source-manifest.json'
                if source_manifest.exists():
                    for row in read(source_manifest):
                        name = safe_name(row['path'])
                        source = sut / name.removeprefix('upstream/') if name.startswith('upstream/') \
                            else ROOT / 'scripts/research300/codex_trial' / name
                        if sha(source) != row['sha256']:
                            raise ValueError('Remote source snapshot differs: ' + name)
                        add(source, 'sut/' + name.removeprefix('upstream/'))
        # Source hashes recorded by execution are checked before the archive is emitted.
        runtime_sources = []
        for index, work in enumerate(works, 1):
            binding = work / 'runtime-binding.json'
            if binding.exists():
                for name, checksum in read(binding)['implementation'].items():
                    file = ROOT / safe_name(name)
                    archive_name = 'implementation/' + name
                    if not file.is_file() or sha(file) != checksum:
                        relative = 'implementation-snapshots/' + checksum + '/' + name
                        file = work / relative
                        archive_name = f'works/{index:03}/' + relative
                        if not file.is_file() or sha(file) != checksum:
                            raise ValueError('Executed implementation has changed without a matching work snapshot: ' + name)
                    add(file, archive_name)
                    runtime_sources.append({'batch': index, 'path': name, 'sha256': checksum, 'archivePath': archive_name})
        output.mkdir(parents=True)
        rows, failed, retained_successful = [], 0, 0
        stream = SplitWriter(output, part_bytes)
        try:
            with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
                for name, file in sorted(files.items()):
                    inspect_file(file, name, secrets)
                    before = file.stat()
                    digest, size = hashlib.sha256(), 0
                    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                    info.compress_type, info.external_attr = zipfile.ZIP_DEFLATED, 0o100644 << 16
                    with file.open('rb') as source, bundle.open(info, 'w', force_zip64=True) as destination:
                        while data := source.read(CHUNK):
                            destination.write(data)
                            digest.update(data)
                            size += len(data)
                    after = file.stat()
                    if before.st_size != size or (before.st_mtime_ns, before.st_size) != (after.st_mtime_ns, after.st_size):
                        raise ValueError('Source changed while archiving: ' + name)
                    rows.append({'path': name, 'bytes': size, 'sha256': digest.hexdigest()})
                    if name.endswith('/broker-receipt.json'):
                        if not read(file)['ok']:
                            failed += 1
                        else:
                            retained_successful += 1
        finally:
            stream.close()
        write(output / 'archive-manifest.json', {'schemaVersion': 2, 'files': rows})
        parts = [{'file': file.name, 'bytes': file.stat().st_size, 'sha256': sha(file)} for file in stream.parts]
        meta = {'schemaVersion': 2, 'format': 'concatenated-standard-zip', 'parts': parts,
                'manifestSha256': sha(output / 'archive-manifest.json'), 'editionManifestSha256': manifest_hash,
                'qualificationSummarySha256': sha(qualification / 'summary.json'), 'workBatches': bindings,
                'caseBatches': resolution['caseBatches'], 'recoveredCases': resolution['recoveredCases'],
                'unfinishedAttempts': resolution['unfinishedAttempts'],
                'runtimeSources': runtime_sources,
                'caseCount': len(manifest['cases']), 'turnCount': sum(len(c['turns']) for c in manifest['cases']),
                'nativeJobs': native_jobs, 'failedMaintainerJobsRetained': failed, 'candidateCalls': 0,
                'retainedSuccessfulJobs': retained_successful,
                'fullEditionCoverage': True, 'sutCommit': sut_commit,
                'offlineEntry': 'implementation/' + ENTRY,
                'offlineDependencyClosure': ['implementation/' + p.relative_to(ROOT).as_posix() for p in closure],
                'nodeVersion': subprocess.check_output(['node', '--version'], text=True).strip(),
                'excludedFiles': excluded,
                'replayScope': 'Recompute evaluator positives/controls from retained native results; does not rerun native solvers.'}
        write(output / 'archive.json', meta)
        return {'files': len(rows), 'parts': len(parts), 'bytes': sum(p['bytes'] for p in parts),
                'cases': meta['caseCount'], 'turns': meta['turnCount'], 'nativeJobs': native_jobs,
                'failedJobsRetained': failed, 'recoveredCases': resolution['recoveredCases'], 'excludedFiles': len(excluded)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['edition', 'work', 'qualification', 'output']:
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--sut', type=Path)
    parser.add_argument('--attempt', type=Path, action='append', default=[])
    parser.add_argument('--review-file', type=Path, action='append', default=[])
    parser.add_argument('--part-mib', type=int, default=89, choices=range(1, 90))
    args = parser.parse_args()
    print(json.dumps(archive(args.edition, args.work.split(','), args.qualification, args.output,
          args.sut, args.attempt, args.review_file, args.part_mib * CHUNK), indent=2))
