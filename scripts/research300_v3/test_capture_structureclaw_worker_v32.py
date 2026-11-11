"""Hermetic subprocess tests; fixtures never invoke an engineering solver."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest


WRAPPER = Path(__file__).with_name('capture_structureclaw_worker_v32.py')


class WorkerCaptureTest(unittest.TestCase):
    def run_fixture(self, root, timeout=False):
        analysis = root / 'analysis'
        runtime = analysis / 'runtime'
        shared = runtime / 'opensees_shared'
        shared.mkdir(parents=True)
        (shared / '__init__.py').write_text('')
        (shared / 'evidence.py').write_text('artifact_sha256 = lambda value: None\nattach_execution_artifacts = lambda *args: None\n')
        probe = analysis / 'opensees-static' / 'opensees_runtime.py'
        probe.parent.mkdir()
        probe.write_text("import time, sys\n" + ("time.sleep(1)\n" if timeout else '')
                         + "print('{\"available\":true}')\nprint('probe stderr', file=sys.stderr)\n")
        worker = runtime / 'worker.py'
        worker.write_text(
            'import subprocess,sys\n'
            f'probe=subprocess.run([sys.executable,{str(probe)!r},"--json"],capture_output=True,text=True,timeout={.05 if timeout else 5})\n'
            'sys.stdout.write(probe.stdout)\nsys.stderr.write(probe.stderr)\n')
        output = root / 'capture'
        run = subprocess.run([sys.executable, str(WRAPPER), str(worker)], input=b'{}', capture_output=True,
                             env={**os.environ, 'SCLAW_BENCH_CAPTURE_ROOT': str(output),
                                  'SCLAW_BENCH_PYTHON': sys.executable, 'PYTHONDONTWRITEBYTECODE': '1'}, timeout=10)
        folder = next(output.iterdir())
        return run, folder, json.loads((folder / 'capture.json').read_bytes()), probe

    def test_real_subprocess_output_and_exit_status_are_preserved_and_sealed(self):
        with tempfile.TemporaryDirectory() as temporary:
            run, folder, metadata, probe = self.run_fixture(Path(temporary))
            self.assertEqual(run.returncode, 0)
            self.assertEqual(run.stdout, ('{"available":true}' + os.linesep).encode())
            self.assertEqual(run.stderr, ('probe stderr' + os.linesep).encode())
            self.assertEqual((folder / 'stdout.json').read_bytes(), run.stdout)
            self.assertEqual((folder / 'stderr.log').read_bytes(), run.stderr)
            self.assertEqual(metadata['exitCode'], 0)
            recorded, = metadata['availabilityProbes']
            self.assertEqual(recorded['sourceSha256'], hashlib.sha256(probe.read_bytes()).hexdigest())
            self.assertEqual(recorded['returnCode'], 0)
            for name, expected in [('stdout', b'{"available":true}\n'), ('stderr', b'probe stderr\n')]:
                artifact = recorded['artifacts'][name]
                self.assertEqual((folder / artifact['path']).read_bytes(), expected)
                self.assertEqual(artifact['sha256'], hashlib.sha256(expected).hexdigest())

    def test_probe_timeout_remains_a_failed_worker_and_retains_its_attempt(self):
        with tempfile.TemporaryDirectory() as temporary:
            run, folder, metadata, _ = self.run_fixture(Path(temporary), timeout=True)
            self.assertNotEqual(run.returncode, 0)
            self.assertEqual(metadata['exitCode'], 1)
            recorded, = metadata['availabilityProbes']
            self.assertEqual(recorded['exceptionType'], 'TimeoutExpired')
            self.assertNotIn('returnCode', recorded)
            self.assertIn(b'TimeoutExpired', run.stderr)
            self.assertTrue(all((folder / item['path']).is_file() for item in recorded['artifacts'].values()))


if __name__ == '__main__':
    unittest.main()
