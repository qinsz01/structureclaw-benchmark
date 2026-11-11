"""Harmless local-process regressions; no solver or remote host is contacted.

Run: python3 -m unittest discover -s scripts/research300 -p native_process_test.py -v
The Windows Job Object checks explicitly skip on other platforms.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

import native_process
from native_process import OwnedProcess


TREE_FIXTURE = """\
import os
from pathlib import Path
import subprocess
import sys
import time

level = int(sys.argv[1])
directory = Path(sys.argv[2])
if level < 2:
    subprocess.Popen([sys.executable, __file__, str(level + 1), str(directory)],
                     stdin=subprocess.DEVNULL, close_fds=True)
(directory / ('pid-' + str(level))).write_text(str(os.getpid()))
if level == 0 and len(sys.argv) > 3:
    sys.exit(0)
time.sleep(20)
"""


def fixture_environment():
    environment = {"PYTHONIOENCODING": "utf-8"}
    if os.name == "nt":
        environment["SystemRoot"] = os.environ["SystemRoot"]
    return environment


def is_running(pid):
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        api = ctypes.WinDLL("kernel32", use_last_error=True)
        api.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        api.OpenProcess.restype = wintypes.HANDLE
        api.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        api.WaitForSingleObject.restype = wintypes.DWORD
        api.CloseHandle.argtypes = [wintypes.HANDLE]
        api.CloseHandle.restype = wintypes.BOOL
        handle = api.OpenProcess(0x100000, False, pid)  # SYNCHRONIZE
        if not handle:
            if ctypes.get_last_error() == 87:  # process no longer exists
                return False
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            status = api.WaitForSingleObject(handle, 0)
            if status not in (0, 258):
                raise ctypes.WinError(ctypes.get_last_error())
            return status == 258
        finally:
            api.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    # Container PID 1 may leave orphan zombies; they have terminated even when
    # kill(pid, 0) still succeeds. /proc is optional on other POSIX systems.
    status_file = Path(f"/proc/{pid}/stat")
    try:
        return status_file.read_text().rsplit(")", 1)[1].strip().split()[0] != "Z"
    except FileNotFoundError:
        if sys.platform.startswith("linux"):
            return False
        return True


class ProcessTestCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.stdout = self.directory / "stdout.txt"
        self.stderr = self.directory / "stderr.txt"
        self.addCleanup(self.temp.cleanup)

    def launch(self, arguments, env=None):
        process = OwnedProcess(
            [sys.executable, *arguments], self.directory,
            self.stdout, self.stderr,
            fixture_environment() if env is None else env,
        )
        self.addCleanup(process.close)
        return process

    def await_condition(self, condition, message):
        deadline = time.monotonic() + 6
        while not condition():
            if time.monotonic() >= deadline:
                self.fail(message)
            time.sleep(0.02)

    def launch_tree(self, parent_exits=False):
        fixture = self.directory / "fixture.py"
        fixture.write_text(TREE_FIXTURE)
        process = self.launch([str(fixture), "0", str(self.directory)]
                              + (["exit-parent"] if parent_exits else []))
        self.await_condition(
            lambda: all((self.directory / f"pid-{level}").exists()
                        and (self.directory / f"pid-{level}").stat().st_size
                        for level in range(3)),
            "fixture did not create all three processes",
        )
        pids = [int((self.directory / f"pid-{level}").read_text())
                for level in range(3)]
        self.assertEqual(pids[0], process.pid)
        return process, pids

    def assert_stopped(self, pids):
        self.await_condition(lambda: not any(is_running(pid) for pid in pids),
                             f"owned processes still running: {pids}")


class OwnedProcessTests(ProcessTestCase):
    def test_literal_argv_explicit_env_cwd_and_separate_output(self):
        literal = 'literal ; & $HOME "quoted" > should-not-exist'
        code = ("import json, os, sys; "
                "print(json.dumps([sys.argv[1:], os.getcwd(), "
                "os.environ.get('NATIVE_TEST'), "
                "os.environ.get('NATIVE_AMBIENT_SECRET'), sys.stdin.read()])); "
                "print('diagnostic', file=sys.stderr); sys.exit(7)")
        environment = fixture_environment()
        environment["NATIVE_TEST"] = "explicit value"
        with mock.patch.dict(os.environ, {"NATIVE_AMBIENT_SECRET": "must-not-leak"}):
            process = self.launch(["-c", code, literal, ""], env=environment)
        self.assertEqual(process.wait(timeout=5), 7)
        process.close()
        self.assertEqual(json.loads(self.stdout.read_text()),
                         [[literal, ""], str(self.directory), "explicit value", None, ""])
        self.assertEqual(self.stderr.read_text().strip(), "diagnostic")
        self.assertFalse((self.directory / "should-not-exist").exists())
        self.assertEqual(process.poll(), 7)
        self.assertEqual(process.wait(timeout=0), 7)
        process.close()
        process.cancel()

    def test_timeout_then_cancel_and_wait_from_another_thread(self):
        process = self.launch(["-c", "import time; time.sleep(20)"])
        self.assertIsNone(process.poll())
        with self.assertRaises(subprocess.TimeoutExpired):
            process.wait(timeout=0.03)
        results = []
        worker = threading.Thread(target=lambda: results.append(process.wait(timeout=5)))
        worker.start()
        process.cancel()
        worker.join(timeout=6)
        self.assertFalse(worker.is_alive(), "cancel blocked behind wait")
        self.assertEqual(len(results), 1)
        self.assertNotEqual(results[0], 0)
        if os.name == "posix":
            self.assertEqual(results[0], -signal.SIGKILL)
        process.close()

    def test_cancel_kills_descendants_and_preserves_unrelated_process(self):
        unrelated = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(20)"],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, close_fds=True,
        )
        try:
            process, pids = self.launch_tree()
            process.cancel()
            process.wait(timeout=5)
            process.close()
            self.assert_stopped(pids)
            self.assertIsNone(unrelated.poll(), "cancellation killed an unrelated process")
        finally:
            if unrelated.poll() is None:
                unrelated.terminate()
            unrelated.wait(timeout=5)

    def test_close_kills_descendants_after_launcher_success(self):
        process, pids = self.launch_tree(parent_exits=True)
        self.assertEqual(process.wait(timeout=5), 0)
        self.assertTrue(all(is_running(pid) for pid in pids[1:]))
        process.close()
        self.assert_stopped(pids)
        self.assertEqual(process.wait(timeout=0), 0)

    def test_close_of_running_process_releases_ownership(self):
        process = self.launch(["-c", "import time; time.sleep(20)"])
        process.close()
        self.assertIsInstance(process.poll(), int)
        self.assertFalse(is_running(process.pid))
        if os.name == "posix":
            with self.assertRaises(ChildProcessError):
                os.waitpid(process.pid, os.WNOHANG)

    def test_launch_failure_does_not_keep_log_files_open(self):
        with self.assertRaises(OSError):
            OwnedProcess([str(self.directory / "does-not-exist")], self.directory,
                         self.stdout, self.stderr, fixture_environment())
        self.stdout.unlink()
        self.stderr.unlink()

    def test_rejects_implicit_environment_and_string_commands(self):
        for argv, environment in (("python something", {}), ([sys.executable], None)):
            with self.subTest(argv=argv, env=environment):
                with self.assertRaises(ValueError):
                    OwnedProcess(argv, self.directory, self.stdout, self.stderr, environment)

    @unittest.skipUnless(os.name == "posix", "requires POSIX process groups")
    def test_interrupted_launch_cleans_up_the_recorded_child(self):
        original_init = subprocess.Popen.__init__
        launched = []

        def interrupt_after_launch(child, *args, **kwargs):
            original_init(child, *args, **kwargs)
            launched.append(child.pid)
            raise KeyboardInterrupt()

        with mock.patch.object(subprocess.Popen, "__init__", interrupt_after_launch):
            with self.assertRaises(KeyboardInterrupt):
                self.launch(["-c", "import time; time.sleep(20)"])
        self.assertEqual(len(launched), 1)
        self.assertFalse(is_running(launched[0]))
        with self.assertRaises(ChildProcessError):
            os.waitpid(launched[0], os.WNOHANG)


@unittest.skipUnless(os.name == "nt", "requires Windows Job Object APIs")
class WindowsJobTests(ProcessTestCase):
    def test_exit_code_259_is_not_mistaken_for_a_running_process(self):
        process = self.launch(["-c", "import sys; sys.exit(259)"])
        self.assertEqual(process.wait(timeout=5), 259)

    def test_assignment_failure_never_runs_the_suspended_child(self):
        import ctypes
        api = native_process._kernel_api()

        class RejectAssignment:
            def __getattr__(self, name):
                return getattr(api, name)

            @staticmethod
            def AssignProcessToJobObject(job, process):
                ctypes.set_last_error(5)  # ERROR_ACCESS_DENIED, e.g. nested job restriction.
                return 0

        marker = self.directory / "must-not-run"
        with mock.patch.object(native_process, "_kernel_api", return_value=RejectAssignment()):
            with self.assertRaisesRegex(OSError, "AssignProcessToJobObject"):
                self.launch(["-c", "from pathlib import Path; Path('must-not-run').touch()"])
        self.assertFalse(marker.exists(), "uncontained child was allowed to execute")

    def test_unlisted_inheritable_file_handle_is_not_passed(self):
        import msvcrt
        extra_file = self.directory / "unrelated-handle.txt"
        with extra_file.open("wb") as stream:
            os.set_inheritable(stream.fileno(), True)
            handle = msvcrt.get_osfhandle(stream.fileno())
            code = (
                "import ctypes, sys\n"
                "from ctypes import wintypes as w\n"
                "api = ctypes.WinDLL('kernel32', use_last_error=True)\n"
                "api.GetFinalPathNameByHandleW.argtypes = [w.HANDLE, w.LPWSTR, "
                "w.DWORD, w.DWORD]\n"
                "api.GetFinalPathNameByHandleW.restype = w.DWORD\n"
                "buffer = ctypes.create_unicode_buffer(32768)\n"
                "length = api.GetFinalPathNameByHandleW(int(sys.argv[1]), buffer, "
                "len(buffer), 0)\n"
                "print(buffer.value if length else '')\n"
            )
            process = self.launch(["-c", code, str(handle)])
            self.assertEqual(process.wait(timeout=5), 0)
            process.close()
        self.assertNotIn(extra_file.name, self.stdout.read_text())

    def test_job_close_kills_workers_when_owner_exits_without_cleanup(self):
        fixture = self.directory / "fixture.py"
        fixture.write_text(TREE_FIXTURE)
        module_path = str(Path(native_process.__file__).resolve().parent)
        wrapper = (
            "import os, pathlib, sys, time\n"
            f"sys.path.insert(0, {module_path!r})\n"
            "from native_process import OwnedProcess\n"
            f"directory = pathlib.Path({str(self.directory)!r})\n"
            f"owned = OwnedProcess([sys.executable, {str(fixture)!r}, '0', "
            "str(directory)], directory, directory / 'inner.out', "
            "directory / 'inner.err', dict(os.environ))\n"
            "deadline = time.monotonic() + 6\n"
            "while not all((directory / ('pid-' + str(level))).exists() "
            "and (directory / ('pid-' + str(level))).stat().st_size "
            "for level in range(3)):\n"
            "    if time.monotonic() >= deadline: raise RuntimeError('fixture timeout')\n"
            "    time.sleep(0.02)\n"
            "os._exit(0)\n"
        )
        result = subprocess.run([sys.executable, "-c", wrapper], cwd=self.directory,
                                capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace"))
        pids = [int((self.directory / f"pid-{level}").read_text())
                for level in range(3)]
        self.assert_stopped(pids)


if __name__ == "__main__":
    unittest.main()
