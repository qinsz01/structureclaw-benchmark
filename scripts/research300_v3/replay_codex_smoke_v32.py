"""Archive a sealed smoke and cold-regrade with copied source/input/evidence.

Uses Node only for deterministic grading. Never calls a model/native solver.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    with path.open('x') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('edition', 'work', 'pin', 'diagnostic', 'output', 'public-tools'):
        parser.add_argument('--' + name, type=Path, required=True)
    a = parser.parse_args()
    edition, work, pin, diagnostic, output = [getattr(a, k).resolve() for k in ('edition', 'work', 'pin', 'diagnostic', 'output')]
    if output.is_relative_to(edition) or output.is_relative_to(work):
        raise ValueError('Archive/replay output must be outside original inputs and evidence')
    output.mkdir(exist_ok=True)
    binding = read(work / 'source-binding.json')
    spec = read(work / 'execution-specification.json')
    public_tools = a.public_tools.resolve()
    if sha(public_tools / 'manifest.json') != spec['publicToolManifestSha256']:
        raise ValueError('Issued public tool manifest differs')
    tool_manifest = read(public_tools / 'manifest.json')
    tools_zip = output / 'public-tools-snapshot.zip'
    with zipfile.ZipFile(tools_zip, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(public_tools / 'manifest.json', 'manifest.json')
        for file in tool_manifest['files']:
            if sha(public_tools / file['path']) != file['sha256']:
                raise ValueError('Issued public tool changed')
            archive.write(public_tools / file['path'], file['path'])
    sources = {**binding['evaluationCode'], **binding['controllerCode']}
    for relative, digest in sources.items():
        if sha(ROOT / relative) != digest:
            raise ValueError('Bound source changed: ' + relative)
    # Helpers/docs/tests supplement the exact executable closure. The scoring
    # entry independently checks the bound source files after extraction.
    for file in (HERE / 'audit_codex_smoke_v32.cjs', HERE / 'controls-v32.cjs', HERE / 'replay_codex_smoke_v32.py',
                 HERE / 'test_codex_broker_v32.py', HERE / 'test_codex_run_v32.py',
                 HERE / 'test_grade_codex_smoke_v32.cjs', HERE / 'CODEX-V32-SMOKE.md'):
        sources[file.relative_to(ROOT).as_posix()] = sha(file)
    code_zip = output / 'source-snapshot.zip'
    with zipfile.ZipFile(code_zip, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for relative, digest in sorted(sources.items()):
            if sha(ROOT / relative) != digest:
                raise ValueError('Source changed during archival')
            archive.write(ROOT / relative, relative)
    evidence_zip = output / 'candidate-evidence.zip'
    inventory = read(work / 'artifact-inventory.json')
    files = [*inventory['files'], {'path': 'artifact-inventory.json', 'sha256': sha(work / 'artifact-inventory.json')}]
    with zipfile.ZipFile(evidence_zip, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for file in files:
            path = work / file['path']
            if sha(path) != file['sha256']:
                raise ValueError('Original evidence changed: ' + file['path'])
            archive.write(path, 'capture/' + file['path'])
        archive.write(pin, 'operator-pin.json')
    manifest = read(edition / 'manifest.json')
    with tempfile.TemporaryDirectory(prefix='research300-codex-cold-') as temporary:
        cold = Path(temporary)
        code = cold / 'source'
        with zipfile.ZipFile(code_zip) as archive:
            archive.extractall(code)
        with zipfile.ZipFile(evidence_zip) as archive:
            archive.extractall(cold)
        frozen = cold / 'edition'
        frozen.mkdir()
        shutil.copyfile(edition / 'manifest.json', frozen / 'manifest.json')
        for row in manifest['files']:
            target = frozen / row['path']
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(edition / row['path'], target)
            if sha(target) != row['sha256']:
                raise ValueError('Frozen corpus copy changed')
        cold_output = cold / 'diagnostic.json'
        command = ['node', str(code / 'scripts/research300_v3/grade_codex_smoke_v32.cjs'),
                   '--edition', str(frozen), '--control-root', str(cold / 'capture'),
                   '--pin', str(cold / 'operator-pin.json'), '--pin-sha256', sha(pin), '--output', str(cold_output)]
        run = subprocess.run(command, cwd=code, capture_output=True, text=True, timeout=180)
        (output / 'cold-replay.stdout').write_text(run.stdout)
        (output / 'cold-replay.stderr').write_text(run.stderr)
        if run.returncode:
            raise RuntimeError('Cold replay failed: ' + run.stderr[-2000:])
        actual, expected = read(cold_output), read(diagnostic)
        same = actual == expected
        shutil.copyfile(cold_output, output / 'cold-replay-diagnostic.json')
        result = {'kind': 'research300-v32-codex-cold-replay', 'formalComparisonScore': False,
                  'allFieldsIdentical': same, 'rowsIdentical': actual['rows'] == expected['rows'],
                  'candidateInvocations': 0, 'nativeSolverInvocations': 0,
                  'cases': actual['cases'], 'plannedTurns': actual['plannedTurns'], 'counts': actual['counts'],
                  'sourceFiles': len(sources), 'evidenceFiles': len(files), 'frozenFiles': len(manifest['files']) + 1,
                  'operatorPinSha256': sha(pin), 'originalDiagnosticSha256': sha(diagnostic),
                  'coldDiagnosticSha256': sha(output / 'cold-replay-diagnostic.json'),
                  'publicToolManifestSha256': spec['publicToolManifestSha256'],
                  'archives': [{'path': p.name, 'sha256': sha(p), 'bytes': p.stat().st_size} for p in (code_zip, evidence_zip, tools_zip)],
                  'sourceSnapshot': sources, 'replayScriptSha256': sha(Path(__file__)),
                  'nodeVersion': subprocess.check_output(['node', '--version'], text=True).strip()}
        write(output / 'cold-replay.json', result)
        if not same:
            raise RuntimeError('Cold replay is not identical to original diagnostic')
        print(json.dumps({k: v for k, v in result.items() if k != 'sourceSnapshot'}))


if __name__ == '__main__':
    main()
