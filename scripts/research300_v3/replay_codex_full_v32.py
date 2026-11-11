"""Archive a full run and regrade an independently extracted copy, without calls."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time
import zipfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        while chunk := handle.read(4 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def write(path, value):
    with path.open('x') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write('\n')


def archive_files(target, root, files, prefix=''):
    with zipfile.ZipFile(target, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=3) as archive:
        for number, row in enumerate(files, 1):
            relative = Path(row['path'])
            if relative.is_absolute() or '..' in relative.parts:
                raise ValueError('Archive path escapes root')
            source = root / relative
            if source.is_symlink() or sha(source) != row['sha256']:
                raise ValueError('Source changed before archival: ' + row['path'])
            archive.write(source, prefix + relative.as_posix())
            if number % 5000 == 0:
                print(json.dumps({'archive': target.name, 'filesArchived': number, 'totalFiles': len(files)}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('edition', 'work', 'pin', 'diagnostic', 'output', 'cold-root'):
        parser.add_argument('--' + name, type=Path, required=True)
    a = parser.parse_args()
    edition, work, pin, diagnostic, output, cold = [getattr(a, k).resolve() for k in ('edition', 'work', 'pin', 'diagnostic', 'output', 'cold_root')]
    for destination in (output, cold):
        if destination.exists():
            raise FileExistsError('Fresh archive and replay directories required')
        if destination.is_relative_to(edition) or destination.is_relative_to(work):
            raise ValueError('Replay must be outside original input/evidence')
    if cold.is_relative_to(output) or output.is_relative_to(cold):
        raise ValueError('Keep independent extraction separate from archive output')
    started = time.monotonic()
    bound, spec, grade, operator = map(read, (work / 'source-binding.json', work / 'execution-specification.json', diagnostic, pin))
    if (grade['operatorPinSha256'] != sha(pin) or grade['indexSha256'] != sha(work / operator['index']['path'])
            or grade['executionSpecificationSha256'] != sha(work / 'execution-specification.json')
            or grade['manifestSha256'] != sha(edition / 'manifest.json') or grade['plannedTurns'] != 560):
        raise ValueError('The prior full diagnostic does not match the original capture')
    output.mkdir(parents=True)
    cold.mkdir(parents=True)
    sources = {**bound['evaluationCode'], **bound['controllerCode']}
    for relative, digest in sources.items():
        if sha(ROOT / relative) != digest or sha(work / 'source-snapshot' / relative) != digest:
            raise ValueError('Bound source differs from pre-run snapshot: ' + relative)
    for name in ('inspect_codex_full_case_v32.cjs', 'watch_codex_full_evidence_v32.py',
                 'audit_codex_full_controls_v32.cjs', 'summarize_codex_full_v32.py',
                 'controls-v32.cjs', 'finish_codex_full_v32.py',
                 'summarize_candidate.py', 'replay_codex_full_v32.py',
                 'test_codex_full_v32.py', 'test_grade_codex_full_v32.cjs'):
        file = HERE / name
        sources[file.relative_to(ROOT).as_posix()] = sha(file)
    source_zip = output / 'source-snapshot.zip'
    archive_files(source_zip, ROOT, [{'path': k, 'sha256': v} for k, v in sorted(sources.items())])
    manifest = read(edition / 'manifest.json')
    frozen_files = [{'path': 'manifest.json', 'sha256': sha(edition / 'manifest.json')}, *manifest['files']]
    edition_zip = output / 'frozen-edition.zip'
    archive_files(edition_zip, edition, frozen_files)
    tools = work / 'issued-public-tools'
    if sha(tools / 'manifest.json') != spec['publicToolManifestSha256']:
        raise ValueError('Issued public tools differ')
    tools_zip = output / 'issued-public-tools.zip'
    archive_files(tools_zip, tools, [{'path': 'manifest.json', 'sha256': sha(tools / 'manifest.json')}, *read(tools / 'manifest.json')['files']])
    inventory = read(work / 'artifact-inventory.json')
    if sha(work / 'artifact-inventory.json') != operator['inventory']['sha256']:
        raise ValueError('Inventory differs from outside operator pin')
    evidence_files = [*inventory['files'], {'path': 'artifact-inventory.json', 'sha256': sha(work / 'artifact-inventory.json')}]
    evidence_zip = output / 'candidate-evidence.zip'
    archive_files(evidence_zip, work, evidence_files)
    shutil.copyfile(pin, output / 'operator-pin.json')
    for archive, destination in ((source_zip, cold / 'source'), (edition_zip, cold / 'edition'), (evidence_zip, cold / 'capture')):
        with zipfile.ZipFile(archive) as container:
            container.extractall(destination)
        print(json.dumps({'extracted': archive.name, 'destination': str(destination)}), flush=True)
    shutil.copyfile(output / 'operator-pin.json', cold / 'operator-pin.json')
    command = ['node', str(cold / 'source/scripts/research300_v3/grade_codex_full_v32.cjs'),
               '--edition', str(cold / 'edition'), '--control-root', str(cold / 'capture'),
               '--pin', str(cold / 'operator-pin.json'), '--pin-sha256', sha(pin), '--output', str(cold / 'diagnostic.json')]
    with (output / 'cold-replay.stdout').open('x') as stdout, (output / 'cold-replay.stderr').open('x') as stderr:
        process = subprocess.run(command, cwd=cold / 'source', stdout=stdout, stderr=stderr, timeout=7200)
    if process.returncode:
        raise RuntimeError('Cold replay failed; see retained stderr')
    shutil.copyfile(cold / 'diagnostic.json', output / 'cold-replay-diagnostic.json')
    actual = read(cold / 'diagnostic.json')
    result = {'kind': 'research300-v32-codex-full-cold-replay', 'formalComparisonScore': False,
              'candidateInvocations': 0, 'nativeSolverInvocations': 0, 'originalAnswersModified': False,
              'allFieldsIdentical': actual == grade, 'diagnosticBytesIdentical': sha(cold / 'diagnostic.json') == sha(diagnostic),
              'rowsIdentical': actual['rows'] == grade['rows'], 'cases': 300, 'plannedTurns': 560, 'counts': actual['counts'],
              'sourceFiles': len(sources), 'evidenceFiles': len(evidence_files), 'frozenFiles': len(frozen_files),
              'operatorPinSha256': sha(pin), 'originalDiagnosticSha256': sha(diagnostic),
              'coldDiagnosticSha256': sha(cold / 'diagnostic.json'), 'elapsedSeconds': time.monotonic() - started,
              'archives': [{'path': p.name, 'sha256': sha(p), 'bytes': p.stat().st_size}
                           for p in (source_zip, edition_zip, tools_zip, evidence_zip)],
              'sourceSnapshot': sources, 'command': command, 'replayScriptSha256': sha(Path(__file__)),
              'nodeVersion': subprocess.check_output(['node', '--version'], text=True).strip(),
              'coldRoot': str(cold), 'scope': 'Independent extracted path, same host and Node runtime; no model or solver rerun'}
    write(output / 'cold-replay.json', result)
    if not result['allFieldsIdentical'] or not result['diagnosticBytesIdentical']:
        raise RuntimeError('Cold diagnostic differs; original and replay remain available')
    print(json.dumps({k: v for k, v in result.items() if k not in ('sourceSnapshot', 'command')}), flush=True)


if __name__ == '__main__':
    main()
