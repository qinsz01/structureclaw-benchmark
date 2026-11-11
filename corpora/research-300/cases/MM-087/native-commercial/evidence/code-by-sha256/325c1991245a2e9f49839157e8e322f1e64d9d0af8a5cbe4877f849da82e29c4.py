"""Own one broker-launched process group or Windows Job Object.

The broker, not this module, validates executable and argument allowlists. No
shell is used. Always call close(), including after a successful wait(): a
launcher may exit while leaving workers running. POSIX workers must stay in
their inherited process group (this is not a sandbox for hostile executables).
Windows workers cannot opt out of the Job Object; unsupported containment fails
before the initially suspended process is allowed to run.
"""

from __future__ import annotations

from contextlib import ExitStack
import os
import signal
import subprocess
import threading
import time
from collections.abc import Mapping, Sequence


class OwnedProcess:
    """Launch argv with explicit environment and own its descendant lifetime.

    poll()/wait() report the initial process's exit status. cancel() requests
    immediate termination of the whole owned group/job. close() cancels any
    remaining workers, reaps the initial process, and releases OS resources.
    The environment is used as supplied, without merging the broker's secrets.
    """

    def __init__(self, argv: Sequence[str], cwd: os.PathLike | str,
                 stdout_path: os.PathLike | str, stderr_path: os.PathLike | str,
                 env: Mapping[str, str]):
        if isinstance(argv, (str, bytes)) or not argv:
            raise ValueError("argv must be a nonempty sequence of strings")
        self.argv = list(argv)
        if any(not isinstance(arg, str) or "\0" in arg for arg in self.argv):
            raise ValueError("argv must contain strings without NUL characters")
        if not self.argv[0]:
            raise ValueError("argv[0] must name an executable")
        if not isinstance(env, Mapping):
            raise ValueError("an explicit environment mapping is required")
        environment = dict(env)
        if any(not isinstance(key, str) or not key or "=" in key or "\0" in key
               or not isinstance(value, str) or "\0" in value
               for key, value in environment.items()):
            raise ValueError("environment keys and values must be valid strings")
        self._lock = threading.RLock()
        self._closed = False
        self._cancelled = False
        self._returncode = None
        if os.name == "nt":
            backend = _WindowsProcess
        elif os.name == "posix":
            backend = _PosixProcess
        else:
            raise RuntimeError("owned process containment is unsupported on this OS")
        self._process = backend()
        try:
            with ExitStack() as stack:
                stdin = stack.enter_context(open(os.devnull, "rb"))
                stdout = stack.enter_context(open(stdout_path, "wb"))
                stderr = stack.enter_context(open(stderr_path, "wb"))
                self._process.launch(self.argv, os.fspath(cwd), stdin, stdout,
                                     stderr, environment)
            self.pid = self._process.pid
        except BaseException:
            self._process.abort()
            raise

    def poll(self) -> int | None:
        with self._lock:
            if self._returncode is None:
                self._returncode = self._process.poll()
            return self._returncode

    def wait(self, timeout: float | None = None) -> int:
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            result = self.poll()
            if result is not None:
                return result
            if deadline is not None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise subprocess.TimeoutExpired(self.argv, timeout)
                time.sleep(min(0.02, remaining))
            else:
                time.sleep(0.02)

    def cancel(self) -> None:
        with self._lock:
            if not self._closed and not self._cancelled:
                self._process.cancel()
                self._cancelled = True

    def close(self) -> None:
        with self._lock:
            if not self._closed:
                self.cancel()
                self._returncode = self._process.close()
                self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


class _PosixProcess:
    def __init__(self):
        # Retain the exited leader until close(): reaping during poll()/wait()
        # would allow its numeric PGID to be recycled before worker cleanup.
        if not all(hasattr(os, name) for name in
                   ("waitid", "WNOWAIT", "WEXITED", "WNOHANG", "P_PID")):
            raise RuntimeError("safe POSIX process ownership requires waitid/WNOWAIT")
        self._child = None

    def launch(self, argv, cwd, stdin, stdout, stderr, env):
        # Keep the Popen object reachable even if its __init__ is interrupted
        # after recording the child PID. Broker signal handlers should defer
        # shutdown to normal control flow, rather than interrupt process launch.
        self._child = subprocess.Popen.__new__(subprocess.Popen)
        subprocess.Popen.__init__(
            self._child,
            argv, cwd=cwd, env=env, stdin=stdin, stdout=stdout, stderr=stderr,
            shell=False, close_fds=True, start_new_session=True,
        )
        self.pid = self._child.pid

    def abort(self):
        pid = getattr(self._child, "pid", None)
        if pid is not None and self._child.returncode is None:
            try:
                os.killpg(pid, signal.SIGKILL)
            except ProcessLookupError:
                # An interrupted Popen may not have reached setsid yet. This
                # PID is our unreaped direct child, never an externally found PID.
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            _, status = os.waitpid(pid, 0)
            self._child.returncode = os.waitstatus_to_exitcode(status)

    def poll(self):
        info = os.waitid(os.P_PID, self.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
        if info is None:
            return None
        return info.si_status if info.si_code == os.CLD_EXITED else -info.si_status

    def cancel(self):
        try:
            os.killpg(self.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass

    def close(self):
        _, status = os.waitpid(self.pid, 0)
        self._child.returncode = os.waitstatus_to_exitcode(status)
        return self._child.returncode


if os.name == "nt":
    import ctypes
    from ctypes import wintypes as w
    import msvcrt

    class _StartupInfo(ctypes.Structure):
        _fields_ = [
            ("cb", w.DWORD), ("lpReserved", w.LPWSTR),
            ("lpDesktop", w.LPWSTR), ("lpTitle", w.LPWSTR),
            ("dwX", w.DWORD), ("dwY", w.DWORD), ("dwXSize", w.DWORD),
            ("dwYSize", w.DWORD), ("dwXCountChars", w.DWORD),
            ("dwYCountChars", w.DWORD), ("dwFillAttribute", w.DWORD),
            ("dwFlags", w.DWORD), ("wShowWindow", w.WORD),
            ("cbReserved2", w.WORD), ("lpReserved2", ctypes.POINTER(w.BYTE)),
            ("hStdInput", w.HANDLE), ("hStdOutput", w.HANDLE),
            ("hStdError", w.HANDLE),
        ]

    class _StartupInfoEx(ctypes.Structure):
        _fields_ = [("StartupInfo", _StartupInfo), ("lpAttributeList", w.LPVOID)]

    class _ProcessInfo(ctypes.Structure):
        _fields_ = [("hProcess", w.HANDLE), ("hThread", w.HANDLE),
                    ("dwProcessId", w.DWORD), ("dwThreadId", w.DWORD)]

    class _BasicLimitInfo(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_longlong),
            ("PerJobUserTimeLimit", ctypes.c_longlong), ("LimitFlags", w.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", w.DWORD), ("Affinity", ctypes.c_size_t),
            ("PriorityClass", w.DWORD), ("SchedulingClass", w.DWORD),
        ]

    class _IoCounters(ctypes.Structure):
        _fields_ = [(name, ctypes.c_ulonglong) for name in (
            "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
            "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]

    class _ExtendedLimitInfo(ctypes.Structure):
        _fields_ = [("BasicLimitInformation", _BasicLimitInfo),
                    ("IoInfo", _IoCounters),
                    ("ProcessMemoryLimit", ctypes.c_size_t),
                    ("JobMemoryLimit", ctypes.c_size_t),
                    ("PeakProcessMemoryUsed", ctypes.c_size_t),
                    ("PeakJobMemoryUsed", ctypes.c_size_t)]

    class _AccountingInfo(ctypes.Structure):
        _fields_ = [(name, ctypes.c_longlong) for name in (
            "TotalUserTime", "TotalKernelTime", "ThisPeriodTotalUserTime",
            "ThisPeriodTotalKernelTime")] + [(name, w.DWORD) for name in (
            "TotalPageFaultCount", "TotalProcesses", "ActiveProcesses",
            "TotalTerminatedProcesses")]

    def _kernel_api():
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        signatures = {
            "CreateJobObjectW": (w.HANDLE, [w.LPVOID, w.LPCWSTR]),
            "SetInformationJobObject": (w.BOOL, [w.HANDLE, ctypes.c_int,
                                               w.LPVOID, w.DWORD]),
            "QueryInformationJobObject": (w.BOOL, [w.HANDLE, ctypes.c_int,
                w.LPVOID, w.DWORD, ctypes.POINTER(w.DWORD)]),
            "GetCurrentProcess": (w.HANDLE, []),
            "DuplicateHandle": (w.BOOL, [w.HANDLE, w.HANDLE, w.HANDLE,
                                          ctypes.POINTER(w.HANDLE), w.DWORD,
                                          w.BOOL, w.DWORD]),
            "InitializeProcThreadAttributeList": (w.BOOL, [
                w.LPVOID, w.DWORD, w.DWORD, ctypes.POINTER(ctypes.c_size_t)]),
            "UpdateProcThreadAttribute": (w.BOOL, [w.LPVOID, w.DWORD,
                ctypes.c_size_t, w.LPVOID, ctypes.c_size_t, w.LPVOID, w.LPVOID]),
            "DeleteProcThreadAttributeList": (None, [w.LPVOID]),
            "CreateProcessW": (w.BOOL, [w.LPCWSTR, w.LPWSTR, w.LPVOID,
                w.LPVOID, w.BOOL, w.DWORD, w.LPVOID, w.LPCWSTR,
                ctypes.POINTER(_StartupInfo), ctypes.POINTER(_ProcessInfo)]),
            "AssignProcessToJobObject": (w.BOOL, [w.HANDLE, w.HANDLE]),
            "ResumeThread": (w.DWORD, [w.HANDLE]),
            "TerminateProcess": (w.BOOL, [w.HANDLE, w.UINT]),
            "TerminateJobObject": (w.BOOL, [w.HANDLE, w.UINT]),
            "WaitForSingleObject": (w.DWORD, [w.HANDLE, w.DWORD]),
            "GetExitCodeProcess": (w.BOOL, [w.HANDLE, ctypes.POINTER(w.DWORD)]),
            "CloseHandle": (w.BOOL, [w.HANDLE]),
        }
        try:
            for name, (result, arguments) in signatures.items():
                function = getattr(kernel, name)
                function.restype, function.argtypes = result, arguments
        except AttributeError as error:
            raise RuntimeError("Windows Job Object containment APIs are unavailable") from error
        return kernel

    class _WindowsProcess:
        def __init__(self):
            self._api = _kernel_api()
            self._job = None
            self._handle = None

        def launch(self, argv, cwd, stdin, stdout, stderr, env):
            api = self._api
            process = _ProcessInfo()
            inherited = []
            attributes = None
            assigned = False
            try:
                self._job = api.CreateJobObjectW(None, None)
                self._require(self._job, "CreateJobObjectW")
                limits = _ExtendedLimitInfo()
                limits.BasicLimitInformation.LimitFlags = 0x2000  # KILL_ON_JOB_CLOSE
                self._require(api.SetInformationJobObject(
                    self._job, 9, ctypes.byref(limits), ctypes.sizeof(limits)),
                    "SetInformationJobObject(KILL_ON_JOB_CLOSE)")
                current = api.GetCurrentProcess()
                for stream in (stdin, stdout, stderr):
                    handle = w.HANDLE()
                    self._require(api.DuplicateHandle(
                        current, msvcrt.get_osfhandle(stream.fileno()), current,
                        ctypes.byref(handle), 0, True, 2), "DuplicateHandle")
                    inherited.append(handle.value)
                # Restrict inheritance to the three stdio handles. In
                # particular, the child must never inherit our job handle.
                size = ctypes.c_size_t()
                api.InitializeProcThreadAttributeList(None, 1, 0, ctypes.byref(size))
                if ctypes.get_last_error() != 122 or not size.value:
                    raise RuntimeError("Windows restricted handle inheritance is unavailable")
                storage = ctypes.create_string_buffer(size.value)
                self._require(api.InitializeProcThreadAttributeList(
                    storage, 1, 0, ctypes.byref(size)),
                    "InitializeProcThreadAttributeList")
                attributes = storage
                handles = (w.HANDLE * len(inherited))(*inherited)
                self._require(api.UpdateProcThreadAttribute(
                    attributes, 0, 0x20002, handles, ctypes.sizeof(handles),
                    None, None), "UpdateProcThreadAttribute(HANDLE_LIST)")
                startup = _StartupInfoEx()
                startup.StartupInfo.cb = ctypes.sizeof(startup)
                startup.StartupInfo.dwFlags = 0x100  # STARTF_USESTDHANDLES
                (startup.StartupInfo.hStdInput, startup.StartupInfo.hStdOutput,
                 startup.StartupInfo.hStdError) = inherited
                startup.lpAttributeList = ctypes.cast(attributes, w.LPVOID)
                environment = ctypes.create_unicode_buffer(
                    "\0".join(f"{key}={value}" for key, value in
                              sorted(env.items(), key=lambda item: item[0].upper()))
                    + "\0\0")
                command = ctypes.create_unicode_buffer(subprocess.list2cmdline(argv))
                # CREATE_SUSPENDED | CREATE_UNICODE_ENVIRONMENT |
                # EXTENDED_STARTUPINFO_PRESENT | CREATE_NEW_PROCESS_GROUP.
                self._require(api.CreateProcessW(
                    argv[0], command, None, None, True, 0x4 | 0x400 | 0x80000 | 0x200,
                    environment, cwd, ctypes.byref(startup.StartupInfo),
                    ctypes.byref(process)), "CreateProcessW(suspended)")
                self._handle = process.hProcess
                self.pid = process.dwProcessId
                self._require(api.AssignProcessToJobObject(self._job, self._handle),
                              "AssignProcessToJobObject; refusing uncontained execution")
                assigned = True
                if api.ResumeThread(process.hThread) == 0xFFFFFFFF:
                    self._require(False, "ResumeThread")
            except BaseException:
                # The initial process is still suspended when assignment fails.
                # Never resume it as a fallback for restricted/nested jobs.
                if process.hProcess:
                    if assigned:
                        api.TerminateJobObject(self._job, 1)
                    api.TerminateProcess(process.hProcess, 1)
                    api.WaitForSingleObject(process.hProcess, 0xFFFFFFFF)
                    api.CloseHandle(process.hProcess)
                    self._handle = None
                if self._job:
                    api.CloseHandle(self._job)
                    self._job = None
                raise
            finally:
                if process.hThread:
                    api.CloseHandle(process.hThread)
                if attributes is not None:
                    api.DeleteProcThreadAttributeList(attributes)
                for handle in inherited:
                    api.CloseHandle(handle)

        @staticmethod
        def _require(success, operation):
            if not success:
                error = ctypes.get_last_error()
                raise OSError(error, f"{operation}: {ctypes.FormatError(error)}")

        def poll(self):
            status = self._api.WaitForSingleObject(self._handle, 0)
            if status == 258:  # WAIT_TIMEOUT
                return None
            self._require(status == 0, "WaitForSingleObject")
            code = w.DWORD()
            self._require(self._api.GetExitCodeProcess(self._handle, ctypes.byref(code)),
                          "GetExitCodeProcess")
            return code.value  # A real exit code of STILL_ACTIVE (259) is valid.

        def cancel(self):
            self._require(self._api.TerminateJobObject(self._job, 1),
                          "TerminateJobObject")

        def abort(self):
            if self._handle:
                self.cancel()
                self.close()

        def close(self):
            self._require(self._api.WaitForSingleObject(self._handle, 0xFFFFFFFF) == 0,
                          "WaitForSingleObject")
            result = self.poll()
            accounting = _AccountingInfo()
            while True:
                self._require(self._api.QueryInformationJobObject(
                    self._job, 1, ctypes.byref(accounting), ctypes.sizeof(accounting),
                    None), "QueryInformationJobObject")
                if accounting.ActiveProcesses == 0:
                    break
                time.sleep(0.01)
            self._require(self._api.CloseHandle(self._handle), "CloseHandle(process)")
            self._handle = None
            self._require(self._api.CloseHandle(self._job), "CloseHandle(job)")
            self._job = None
            return result
