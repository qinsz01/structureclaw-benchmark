"""Prepare committed native source and Git handoff locally; never deploy or run it."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]
BASE = '00ecd812a315a75b7714d5fc030ec3652bfaf869'
PREFIXES = ('backend/src/agent-skills/analysis/', 'backend/src/skill-shared/python/')


def git(sut, *args):
    return subprocess.check_output(['git', '-c', 'safe.directory=*', '-C', str(sut), *args])


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--sut', required=True, type=Path)
    p.add_argument('--commit', required=True)
    p.add_argument('--output', required=True, type=Path)
    a = p.parse_args()
    sut = a.sut.resolve(strict=True)
    if git(sut, 'rev-parse', 'HEAD').decode().strip() != a.commit:
        p.error('SUT HEAD must be the explicitly selected commit')
    git(sut, 'diff', '--exit-code', 'HEAD', '--', *PREFIXES)
    out = a.output.resolve()
    if out.is_relative_to(sut) or out == ROOT:
        p.error('Output must be separate from SUT source')
    out.mkdir(parents=True, exist_ok=False)
    payload = git(sut, 'archive', a.commit, '--', *PREFIXES, 'backend/src/providers/catalog.yaml')
    files = {}
    with tarfile.open(fileobj=io.BytesIO(payload)) as archive:
        for member in archive.getmembers():
            path = Path(member.name)
            if (member.isfile() and '__tests__' not in path.parts and '__pycache__' not in path.parts
                    and (path.suffix == '.py' or member.name == 'backend/src/providers/catalog.yaml')):
                files[member.name] = archive.extractfile(member).read()
    worker = 'backend/src/agent-skills/analysis/runtime/worker.py'
    if worker not in files or 'backend/src/agent-skills/analysis/runtime/section_audit.py' not in files:
        p.error('Selected source lacks the native worker or audit compatibility fix')
    native_count = len(files)
    for name in ('capture_structureclaw_worker_v32.py', 'CaptureWorkerLauncher.cs', 'Build-CaptureLauncher.ps1'):
        files['collector/' + name] = Path(__file__).with_name(name).read_bytes()
    manifest = {'kind': 'research300-native-source-manifest', 'schemaVersion': 1,
                'sutCommit': a.commit, 'sutTree': git(sut, 'rev-parse', a.commit + '^{tree}').decode().strip(),
                'publishedBase': BASE, 'workerPath': worker,
                'nativeSourceFiles': native_count,
                'instrumentation': {'captureWorkerSha256': sha(files['collector/capture_structureclaw_worker_v32.py']),
                                    'windowsLauncherBuilt': False, 'runtimeQualified': False},
                'files': [{'path': k, 'sha256': sha(v), 'bytes': len(v)} for k, v in sorted(files.items())],
                'preparationOnly': True, 'installed': False, 'runtimeQualified': False}
    encoded = (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode()
    (out / 'source-manifest.json').write_bytes(encoded)
    with zipfile.ZipFile(out / 'native-source.zip', 'w', zipfile.ZIP_DEFLATED) as z:
        for name, data in sorted({**files, 'source-manifest.json': encoded}.items()):
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, data)
    (out / 'published-to-local.patch').write_bytes(git(sut, 'diff', '--binary', BASE, a.commit))
    # The receiving Git repository needs the published base, then can import
    # the exact local commit. No remote is contacted or modified here.
    git(sut, 'bundle', 'create', str(out / 'sclaw-local.bundle'), 'HEAD', '^' + BASE)
    index = {'kind': 'research300-native-local-handoff', 'sutCommit': a.commit,
             'nativeSourceFiles': native_count, 'packagedFiles': len(files), 'sourceManifestSha256': sha(encoded),
             'files': {f.name: {'bytes': f.stat().st_size, 'sha256': sha(f.read_bytes())}
                       for f in sorted(out.iterdir()) if f.is_file()},
             'candidateInvocations': 0, 'nativeSolverInvocations': 0, 'testSuitesInvoked': 0,
             'uploaded': False, 'deployed': False}
    (out / 'handoff.json').write_text(json.dumps(index, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'output': str(out), 'sutCommit': a.commit, 'nativeSourceFiles': native_count, 'packagedFiles': len(files),
                      'uploaded': False, 'runtimeQualified': False}))


if __name__ == '__main__':
    main()
