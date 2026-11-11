#!/usr/bin/env python3
"""v3.2 opt-in Python-worker capture for StructureClaw's analysis.pythonBin.

Set SCLAW_BENCH_CAPTURE_ROOT to a new benchmark capture directory and optionally
SCLAW_BENCH_PYTHON to StructureClaw's existing Python interpreter. The wrapper
executes the original worker and preserves its native Python receipt bytes before
JavaScript parsing can discard float or negative-zero representations. It does
not change solver inputs, outputs, receipt hashes, or upstream source files.
"""
from __future__ import annotations
import hashlib
import io
import json
import time
import os
from pathlib import Path
import runpy
import sys
import uuid


def sha(data):
    return hashlib.sha256(data).hexdigest()


class Tee:
    def __init__(self, original, file):
        self.original, self.file = original, file

    def write(self, value):
        self.file.write(value)
        self.file.flush()
        return self.original.write(value)

    def flush(self):
        self.file.flush()
        self.original.flush()

    def __getattr__(self, name):
        return getattr(self.original, name)


def main():
    interpreter = os.environ.get('SCLAW_BENCH_PYTHON')
    # A venv executable often symlinks to the system binary. Resolve lexical
    # paths only: realpath equality loses the environment selected by Python.
    if interpreter and os.path.normcase(os.path.abspath(interpreter)) != os.path.normcase(os.path.abspath(sys.executable)):
        os.execv(interpreter, [interpreter, str(Path(__file__).resolve()), *sys.argv[1:]])
    if len(sys.argv) != 2:
        raise ValueError('Expected the original StructureClaw worker.py path')
    worker = Path(sys.argv[1]).resolve()
    # The configured interpreter also serves non-analysis workers. Pass them
    # through without importing an analysis module or intercepting their input.
    if worker.name != 'worker.py' or worker.parent.name != 'runtime' or worker.parent.parent.name != 'analysis':
        os.execv(sys.executable, [sys.executable, str(worker)])
    output = os.environ.get('SCLAW_BENCH_CAPTURE_ROOT')
    if not output:
        raise ValueError('SCLAW_BENCH_CAPTURE_ROOT must name the benchmark capture output directory')
    capture_id = str(uuid.uuid4())
    started_at = time.time()
    folder = Path(output).resolve() / capture_id
    folder.mkdir(parents=True, exist_ok=False)
    (folder / 'canonical').mkdir()
    request = sys.stdin.buffer.read()
    (folder / 'request.json').write_bytes(request)
    sys.stdin = io.TextIOWrapper(io.BytesIO(request), encoding='utf8')
    sys.path.insert(0, str(worker.parent))
    from opensees_shared import evidence
    original_hash = evidence.artifact_sha256
    original_attach = evidence.attach_execution_artifacts
    captured = {}
    receipts = []

    def capture_hash(value):
        result = original_hash(value)
        data = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf8')
        if sha(data) != result:
            raise ValueError('Native artifact hash serialization changed')
        filename = 'canonical/' + result + '.json'
        artifact = folder / filename
        if not artifact.exists():
            artifact.write_bytes(data)
        captured[result] = filename
        return result

    def capture_attach(result, model, parameters):
        value = original_attach(result, model, parameters)
        execution = value.get('execution') or {}
        receipt = execution.get('artifacts') or {}
        paths = {name[:-6]: captured[digest] for name, digest in receipt.items()
                 if name.endswith('Sha256') and isinstance(digest, str) and digest in captured}
        if paths:
            receipts.append({'parameters': parameters, 'solver': execution.get('solver'),
                             'solverVersion': execution.get('solverVersion'), 'artifacts': paths,
                             'receipt': receipt})
        return value

    evidence.artifact_sha256 = capture_hash
    evidence.attach_execution_artifacts = capture_attach
    previous_stdout, previous_stderr = sys.stdout, sys.stderr
    exit_code = 0
    try:
        with (folder / 'stdout.json').open('w', encoding='utf8') as stdout, (folder / 'stderr.log').open('w', encoding='utf8') as stderr:
            sys.stdout, sys.stderr = Tee(previous_stdout, stdout), Tee(previous_stderr, stderr)
            sys.argv = [str(worker)]
            try:
                runpy.run_path(str(worker), run_name='__main__')
            except SystemExit as error:
                exit_code = error.code if isinstance(error.code, int) else 1 if error.code else 0
            except BaseException:
                exit_code = 1
                raise
            finally:
                sys.stdout, sys.stderr = previous_stdout, previous_stderr
    finally:
        index = {'schemaVersion': 2, 'kind': 'structureclaw-python-worker-capture',
                 'captureId': capture_id, 'workerPid': os.getpid(),
                 'startedAt': started_at, 'completedAt': time.time(),
                 'wrapperSha256': sha(Path(__file__).read_bytes()),
                 'worker': str(worker), 'workerSha256': sha(worker.read_bytes()),
                 'requestSha256': sha(request), 'exitCode': exit_code, 'receipts': receipts,
                 'files': {name: sha((folder / name).read_bytes()) for name in ('request.json', 'stdout.json', 'stderr.log') if (folder / name).is_file()}}
        (folder / 'capture.json').write_text(json.dumps(index, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    return exit_code


if __name__ == '__main__':
    raise SystemExit(main())
