"""Controller-owned, turn-scoped OpenSees broker for an explicitly local smoke.

The unchanged frozen executor receives only a once-captured request. The broker
has no reference-model inputs and registers failed/unreported attempts as well.
"""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import threading
import time
import uuid

from scripts.pilot30.service import execute as native_execute


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write('\n')


class Broker:
    def __init__(self, work, base, sut, binding, native_limit, workers=2, executor=native_execute):
        self.work, self.base, self.sut = [Path(p).resolve() for p in (work, base, sut)]
        if type(native_limit) is not int or native_limit < 1:
            raise ValueError('Positive native attempt budget required')
        self.binding, self.native_limit, self.executor = binding, native_limit, executor
        self.turns, self.seen, self.futures, self.errors = {}, set(), [], []
        self.lock = threading.RLock()
        self.pool = ThreadPoolExecutor(max_workers=workers)
        self.stopping = threading.Event()
        self.thread = threading.Thread(target=self._loop, daemon=True)

    def start(self):
        self.thread.start()

    def open_turn(self, case_id, turn_id):
        with self.lock:
            key = (case_id, turn_id)
            if key in self.turns:
                raise ValueError('Turn already issued')
            self.turns[key] = {'open': True, 'attempts': []}

    def _scan(self):
        with self.lock:
            for (case_id, turn_id), turn in self.turns.items():
                folder = self.base / case_id / 'scratch/requests' / turn_id
                for file in sorted(folder.glob('*.json')):
                    if file in self.seen:
                        continue
                    self.seen.add(file)
                    identity = uuid.uuid4().hex
                    job = self.work / 'solver-jobs' / case_id / identity
                    job.mkdir(parents=True, exist_ok=False)
                    error, raw = None, b''
                    # The containing scratch directory is mutable too. Reject
                    # symlink parents before opening any candidate submission.
                    if file.is_symlink() or folder.is_symlink() or folder.resolve() != folder:
                        error = 'UNSAFE_REQUEST_PATH'
                    elif not re.fullmatch(r'[a-f0-9]{32}\.json', file.name) or file.stat().st_size > 8 * 1024 * 1024:
                        error = 'INVALID_REQUEST_ENVELOPE'
                    else:
                        # Open each mutable path component without following
                        # symlinks; a check followed by read_bytes has a race.
                        fd = os.open(self.base / case_id, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
                        try:
                            for component in ('scratch', 'requests', turn_id):
                                child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                                os.close(fd)
                                fd = child
                            source = os.open(file.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
                            with os.fdopen(source, 'rb') as handle:
                                if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
                                    raise ValueError('Request must be a regular file')
                                raw = handle.read(8 * 1024 * 1024 + 1)
                            if len(raw) > 8 * 1024 * 1024:
                                error, raw = 'INVALID_REQUEST_ENVELOPE', b''
                        except (OSError, ValueError):
                            error, raw = 'UNSAFE_REQUEST_PATH', b''
                        finally:
                            os.close(fd)
                    (job / 'submitted-request.json').write_bytes(raw)
                    if not turn['open']:
                        error = error or 'TURN_CLOSED'
                    elif len(turn['attempts']) >= self.native_limit:
                        error = error or 'NATIVE_ATTEMPT_BUDGET_EXCEEDED'
                    attempt = {'caseId': case_id, 'turnId': turn_id, 'evidenceId': identity,
                               'requestNonce': file.stem, 'requestSha256': sha(raw),
                               'registeredAt': time.time(), 'preExecutionRejection': error}
                    turn['attempts'].append(attempt)
                    write(job / 'attempt.json', attempt)
                    future = self.pool.submit(self._execute, job, raw, attempt, error)
                    self.futures.append((case_id, turn_id, future))

    def _execute(self, job, raw, attempt, error):
        try:
            if error:
                raise ValueError(error)
            request = json.loads(raw)
            reply = self.executor(request, job, self.sut, 'OpenSees', role='candidate')
        except Exception as exc:
            reply = {'ok': False, 'jobId': attempt['evidenceId'], 'error': str(exc)}
        reply['jobId'] = attempt['evidenceId']
        receipt = {'role': 'candidate', 'caseId': attempt['caseId'], 'turnId': attempt['turnId'],
                   'engine': 'OpenSees', 'ok': reply['ok'], 'error': reply.get('error'),
                   'requestSha256': sha(raw), 'sutCommit': self.binding['sutCommit'],
                   'executionSpecificationSha256': self.binding['executionSpecificationSha256'],
                   'stateSha256': sha((job / 'state.json').read_bytes()) if reply['ok'] else None}
        write(job / 'broker-receipt.json', receipt)
        target = self.base / attempt['caseId'] / 'solver-replies' / attempt['turnId'] / (attempt['requestNonce'] + '.json')
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix('.tmp')
        write(temporary, reply)
        if target.exists():
            raise ValueError('Reply identity reused')
        temporary.replace(target)

    def _loop(self):
        while not self.stopping.is_set():
            try:
                self._scan()
            except Exception as exc:
                self.errors.append(repr(exc))
                self.stopping.set()
            self.stopping.wait(.05)

    def close_turn(self, case_id, turn_id):
        # Register already-submitted requests before closing; wait for all
        # accepted work to seal before a new user turn can begin.
        with self.lock:
            self._scan()
            self.turns[(case_id, turn_id)]['open'] = False
            pending = [f for c, t, f in self.futures if (c, t) == (case_id, turn_id)]
        for future in pending:
            future.result()
        if self.errors:
            raise RuntimeError('Controlled collection failed: ' + '; '.join(self.errors))

    def attempts(self, case_id, turn_id):
        with self.lock:
            return list(self.turns.get((case_id, turn_id), {}).get('attempts', []))

    def close(self):
        self.stopping.set()
        self.thread.join(timeout=5)
        with self.lock:
            for turn in self.turns.values():
                turn['open'] = False
        self._scan()
        self.pool.shutdown(wait=True)
        for _, _, future in self.futures:
            future.result()
        if self.errors:
            raise RuntimeError('Controlled collection failed: ' + '; '.join(self.errors))
