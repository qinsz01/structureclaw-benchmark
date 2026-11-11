#!/usr/bin/env python3
"""Numeric-only native solver broker. No SUT imports or enabled engine defaults."""
import argparse
import base64
import binascii
import hashlib
import json
import math
import os
from pathlib import Path
import re
import signal
import stat
import sys
import threading
import time
import uuid

from native_process import OwnedProcess

ENGINES = {"OpenSees": "native-opensees-worker", "YJK": "native-yjk-worker", "PKPM": "native-pkpm-worker"}
TABLES = {"nodes", "elements", "materials", "sections", "supports", "loads", "loadCases", "loadCombinations", "settings", "outputRequests"}
ARTIFACTS = {"model.json", "result.json", "stdout.log", "stderr.log", "native-input.dat", "native-output.dat", "settings.json", "solver-version.json"}
INPUT_LIMIT = 8 * 1024 * 1024
ARTIFACT_LIMIT = 32 * 1024 * 1024
WIRE_LIMIT = 48 * 1024 * 1024
HASH_RE = re.compile(r"[0-9a-f]{64}\Z")
JOB_RE = re.compile(r"[0-9a-f]{32}\Z")
TERMINAL = {"succeeded", "failed", "cancelled"}


class BrokerError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def require(condition, code="invalid-request", message="Invalid native job request"):
    if not condition:
        raise BrokerError(code, message)


def exact(value, keys):
    require(type(value) is dict and set(value) == set(keys))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def strict_json(raw):
    def pairs(items):
        out = {}
        for key, value in items:
            require(key not in out, message="Duplicate JSON key")
            out[key] = value
        return out
    try:
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="strict")
        return json.loads(raw, object_pairs_hook=pairs, parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (ValueError, UnicodeError, RecursionError):
        raise BrokerError("invalid-request", "Invalid strict JSON") from None


def numeric(value, depth=0):
    require(depth <= 32, message="Numeric table nesting exceeds limit")
    if type(value) is list:
        for item in value:
            numeric(item, depth + 1)
    else:
        require(value is None or type(value) is bool or (type(value) in (int, float) and abs(value) <= 1e100 and math.isfinite(value)), message="Numeric tables cannot contain text or objects")


def validate_payload(payload):
    exact(payload, {"schemaVersion", "engine", "modelSha256", "files"})
    require(type(payload["schemaVersion"]) is int and payload["schemaVersion"] == 1)
    require(payload["engine"] in ENGINES if type(payload["engine"]) is str else False)
    require(type(payload["modelSha256"]) is str and HASH_RE.fullmatch(payload["modelSha256"]))
    require(type(payload["files"]) is list and len(payload["files"]) == 1)
    entry = payload["files"][0]
    exact(entry, {"path", "sha256", "size", "contentBase64"})
    require(entry["path"] == "model.json")
    require(type(entry["size"]) is int and 0 < entry["size"] <= INPUT_LIMIT)
    require(type(entry["contentBase64"]) is str and len(entry["contentBase64"]) <= (INPUT_LIMIT + 2) // 3 * 4)
    try:
        raw = base64.b64decode(entry["contentBase64"], validate=True)
    except (ValueError, binascii.Error):
        raise BrokerError("invalid-request", "Invalid base64 input") from None
    require(base64.b64encode(raw).decode("ascii") == entry["contentBase64"])
    require(len(raw) == entry["size"] and sha(raw) == entry["sha256"] == payload["modelSha256"], "hash-mismatch", "Input bytes do not match manifest")
    model = strict_json(raw)
    exact(model, {"format", "tables"})
    require(model["format"] == "native-numeric-v1")
    tables = model["tables"]
    require(type(tables) is dict and {"nodes", "elements", "settings"} <= set(tables) <= TABLES)
    for values in tables.values():
        require(type(values) is list)
        numeric(values)
    manifest = {**payload, "files": [{key: entry[key] for key in ("path", "sha256", "size")}]}
    return raw, manifest, sha(canonical(manifest))


def safe_existing(path, directory=False):
    """Reject symlinks/reparse points in every existing ancestor, including root."""
    path = Path(os.path.abspath(path))
    for part in (path, *path.parents):
        try:
            info = part.lstat()
        except FileNotFoundError:
            continue
        require(not stat.S_ISLNK(info.st_mode) and not (getattr(info, "st_file_attributes", 0) & 0x400), "unsafe-path", "Symlinks and reparse points are not allowed")
    if path.exists():
        require(path.is_dir() if directory else path.is_file(), "unsafe-path", "Unexpected file type")
    return path


def read_file(path, limit=ARTIFACT_LIMIT):
    path = safe_existing(path)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except OSError:
        raise BrokerError("missing-artifact", "Required local artifact unavailable") from None
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, "unsafe-path", "Artifact must be a private regular file")
        require(info.st_size <= limit, "size-limit", "Artifact size exceeds limit")
        raw = stream.read(limit + 1)
        require(len(raw) <= limit, "size-limit", "Artifact size exceeds limit")
        return raw


def write_private(path, raw):
    with open(path, "xb") as stream:
        os.chmod(path, 0o600)
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def atomic_json(path, value):
    temp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    write_private(temp, canonical(value))
    os.replace(temp, path)


class Broker:
    def __init__(self, root, registry):
        self.root = safe_existing(root, directory=True)
        # No accidental nested deployment inside either protected Windows tree.
        normalized = str(self.root).replace("\\", "/").lower()
        require(not any(normalized == p or normalized.startswith(p + "/") for p in ("g:/structureclaw-all/structureclaw", "g:/structureclaw-all/sclaw_data")), "unsafe-path", "Job root must be outside protected trees")
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        safe_existing(self.root, directory=True)
        self.registry = safe_existing(registry)
        self.jobs = {}
        self.mutex = threading.RLock()
        self.owner = uuid.uuid4().hex
        self.closed = False
        self.request_ids = set()

    def _job(self, job_id):
        require(type(job_id) is str and JOB_RE.fullmatch(job_id))
        path = self.root / job_id
        require(path.is_dir(), "not-found", "Unknown native job")
        safe_existing(path, directory=True)
        state = strict_json(read_file(path / "state.json", INPUT_LIMIT))
        require(state.get("jobId") == job_id, "hash-mismatch", "Job state identity mismatch")
        return path, state

    def _engine(self, engine):
        try:
            registry = strict_json(read_file(self.registry, INPUT_LIMIT))
        except BrokerError:
            raise BrokerError("resource-busy", "Reviewed host registry unavailable") from None
        exact(registry, {"schemaVersion", "engines"})
        require(registry["schemaVersion"] == 1 and type(registry["engines"]) is dict and set(registry["engines"]) <= set(ENGINES))
        entry = registry["engines"].get(engine)
        require(type(entry) is dict, "resource-busy", "Engine has no reviewed isolated driver")
        exact(entry, {"enabled", "executable", "sha256", "independentCompilerReviewed", "isolationVerified", "isolationLease"})
        require(entry["enabled"] is True and entry["independentCompilerReviewed"] is True and entry["isolationVerified"] is True, "resource-busy", "Independent compiler and process isolation approval required")
        require(type(entry["executable"]) is str and Path(entry["executable"]).is_absolute(), "unsafe-path", "Executable must be host-owned absolute path")
        executable = safe_existing(entry["executable"])
        require(executable.name in {ENGINES[engine], ENGINES[engine] + ".exe"}, "executable-not-allowed", "Executable is not in fixed engine whitelist")
        require(type(entry["sha256"]) is str and HASH_RE.fullmatch(entry["sha256"]))
        require(sha(read_file(executable, 256 * 1024 * 1024)) == entry["sha256"], "hash-mismatch", "Host driver hash changed")
        require(type(entry["isolationLease"]) is str and Path(entry["isolationLease"]).is_absolute(), "resource-busy", "Host isolation lease required")
        try:
            lease = strict_json(read_file(entry["isolationLease"], INPUT_LIMIT))
        except BrokerError:
            raise BrokerError("resource-busy", "Host isolation lease unavailable") from None
        exact(lease, {"schemaVersion", "engine", "executableSha256", "isolated", "expiresAt"})
        require(lease["schemaVersion"] == 1 and lease["engine"] == engine and lease["executableSha256"] == entry["sha256"] and lease["isolated"] is True and type(lease["expiresAt"]) in (int, float) and time.time() < lease["expiresAt"] <= time.time() + 300, "resource-busy", "Current exclusive host isolation lease required")
        return entry

    def submit(self, payload):
        raw, manifest, manifest_hash = validate_payload(payload)
        with self.mutex:
            require(not self.closed, "resource-busy", "Broker is closing")
            engine = payload["engine"]
            entry = self._engine(engine)
            lock = self.root / (engine.lower() + ".lock")
            try:
                lock.mkdir(mode=0o700)
            except FileExistsError:
                raise BrokerError("resource-busy", "Engine is already reserved; stale locks require operator inspection") from None
            job_id = uuid.uuid4().hex
            path = self.root / job_id
            try:
                write_private(lock / "owner.json", canonical({"owner": self.owner, "jobId": job_id}))
                path.mkdir(mode=0o700)
                write_private(path / "model.json", raw)
                write_private(path / "manifest.json", canonical(manifest))
                state = {"jobId": job_id, "engine": engine, "manifestSha256": manifest_hash, "modelSha256": payload["modelSha256"], "state": "running", "executed": False, "exitCode": None, "executableSha256": entry["sha256"]}
                atomic_json(path / "state.json", state)
                # Environment never carries SSH keys, API keys, prompts or user profiles.
                env = {key: os.environ[key] for key in ("SYSTEMROOT", "WINDIR") if key in os.environ}
                env.update({"PATH": os.defpath, "TEMP": str(path), "TMP": str(path), "TMPDIR": str(path), "HOME": str(path), "USERPROFILE": str(path)})
                process = OwnedProcess([entry["executable"], "--input", "model.json", "--output", "result.json"], str(path), str(path / "stdout.log"), str(path / "stderr.log"), env)
                state["executed"] = True
                atomic_json(path / "state.json", state)
                job = {"process": process, "lock": lock, "path": path, "state": state, "cancelled": False}
                self.jobs[job_id] = job
                thread = threading.Thread(target=self._monitor, args=(job_id,), daemon=True)
                job["thread"] = thread
                thread.start()
                return dict(state)
            except BaseException:
                if path.exists():
                    # Keep failed staging evidence, but no untracked process may survive.
                    if "process" in locals():
                        process.cancel()
                        process.close()
                self._unlock(lock, job_id)
                raise

    def _unlock(self, lock, job_id):
        if lock.exists():
            owner = strict_json(read_file(lock / "owner.json", INPUT_LIMIT))
            require(owner == {"owner": self.owner, "jobId": job_id}, "resource-busy", "Engine lock belongs to another worker")
            (lock / "owner.json").unlink()
            lock.rmdir()

    def _monitor(self, job_id):
        job = self.jobs[job_id]
        try:
            code = job["process"].wait()
            # close kills any descendants that outlive the main driver before hashing.
            job["process"].close()
            with self.mutex:
                state = job["state"]
                state["exitCode"] = code
                state["state"] = "cancelled" if job["cancelled"] else ("succeeded" if code == 0 else "failed")
                if state["state"] == "succeeded" and not (job["path"] / "result.json").is_file():
                    state["state"] = "failed"
                atomic_json(job["path"] / "state.json", state)
                try:
                    self._seal(job["path"], state)
                except BrokerError:
                    state["state"] = "failed"
                    atomic_json(job["path"] / "state.json", state)
                self._unlock(job["lock"], job_id)
        except Exception:
            # Never reclaim a lock if process ownership or sealing failed unexpectedly.
            with self.mutex:
                job["state"]["state"] = "failed"
                atomic_json(job["path"] / "state.json", job["state"])

    def _seal(self, path, state):
        manifest = strict_json(read_file(path / "manifest.json", INPUT_LIMIT))
        require(sha(canonical(manifest)) == state["manifestSha256"], "hash-mismatch", "Manifest changed")
        require(manifest["engine"] == state["engine"] and manifest["modelSha256"] == state["modelSha256"], "hash-mismatch", "Manifest identity changed")
        names = ["model.json", "stdout.log", "stderr.log"]
        for name in sorted(ARTIFACTS - set(names)):
            if (path / name).exists() or (path / name).is_symlink():
                names.append(name)
        require(state["state"] != "succeeded" or "result.json" in names, "missing-artifact", "Successful job requires result artifact")
        artifacts = []
        total = 0
        for name in sorted(names):
            raw = read_file(path / name, ARTIFACT_LIMIT - total)
            total += len(raw)
            artifacts.append({"path": name, "size": len(raw), "sha256": sha(raw)})
            if name == "model.json":
                require(sha(raw) == state["modelSha256"], "hash-mismatch", "Solver modified model input")
        receipt = {"schemaVersion": 1, **{key: state[key] for key in ("jobId", "engine", "manifestSha256", "modelSha256", "state", "executed", "exitCode", "executableSha256")}, "artifacts": artifacts, "nativeTruthStatus": "pending-independent-review"}
        write_private(path / "receipt.json", canonical(receipt))
        return receipt

    def status(self, job_id):
        with self.mutex:
            _, state = self._job(job_id)
            if state["state"] == "running" and job_id not in self.jobs:
                return {**state, "state": "resource-busy", "reason": "orphaned-owner"}
            return state

    def cancel(self, job_id):
        with self.mutex:
            _, state = self._job(job_id)
            if state["state"] in TERMINAL:
                return state
            require(job_id in self.jobs, "resource-busy", "Cannot cancel a process owned by a different broker")
            job = self.jobs[job_id]
            job["cancelled"] = True
            job["process"].cancel()
        job["thread"].join(timeout=10)
        return self.status(job_id)

    def collect(self, job_id):
        with self.mutex:
            path, state = self._job(job_id)
            require(state["state"] in TERMINAL, "not-ready", "Job has not finished")
            receipt_raw = read_file(path / "receipt.json", INPUT_LIMIT)
            receipt = strict_json(receipt_raw)
            require(receipt_raw == canonical(receipt), "hash-mismatch", "Receipt bytes changed")
            for key in ("jobId", "engine", "manifestSha256", "modelSha256", "state", "executed", "exitCode", "executableSha256"):
                require(receipt.get(key) == state[key], "hash-mismatch", "Receipt identity changed")
            manifest = strict_json(read_file(path / "manifest.json", INPUT_LIMIT))
            require(sha(canonical(manifest)) == state["manifestSha256"], "hash-mismatch", "Manifest changed after execution")
            sealed_names = {item["path"] for item in receipt["artifacts"]}
            present_names = {name for name in ARTIFACTS if os.path.lexists(path / name)}
            require(len(sealed_names) == len(receipt["artifacts"]) and sealed_names == present_names, "hash-mismatch", "Artifact set changed after execution")
            artifacts = []
            total = 0
            for item in receipt["artifacts"]:
                require(item["path"] in ARTIFACTS, "unsafe-path", "Unexpected artifact path")
                raw = read_file(path / item["path"], ARTIFACT_LIMIT - total)
                total += len(raw)
                require(sha(raw) == item["sha256"] and len(raw) == item["size"], "hash-mismatch", "Artifact changed after execution")
                artifacts.append({**item, "contentBase64": base64.b64encode(raw).decode("ascii")})
            return {"receipt": receipt, "receiptSha256": sha(receipt_raw), "artifacts": artifacts}

    def cleanup(self, job_id, receipt_hash):
        require(type(receipt_hash) is str and HASH_RE.fullmatch(receipt_hash))
        with self.mutex:
            bundle = self.collect(job_id)
            require(bundle["receiptSha256"] == receipt_hash, "hash-mismatch", "Cleanup requires locally verified receipt hash")
            path, _ = self._job(job_id)
            # Explicit known files only; a driver-created link/directory is never followed.
            allowed = ARTIFACTS | {"manifest.json", "state.json", "receipt.json"}
            require(all(p.name in allowed and not p.is_symlink() and p.is_file() for p in path.iterdir()), "unsafe-path", "Unexpected job files require operator inspection")
            for item in path.iterdir():
                safe_existing(item)
                item.unlink()
            path.rmdir()
            self.jobs.pop(job_id, None)
            return {"jobId": job_id, "cleaned": True}

    def close(self):
        with self.mutex:
            self.closed = True
            ids = [job_id for job_id, job in self.jobs.items() if job["state"]["state"] == "running"]
        for job_id in ids:
            self.cancel(job_id)

    def dispatch(self, request):
        require(type(request) is dict)
        op = request.get("op")
        require(type(op) is str and op in {"submit", "status", "collect", "cancel", "cleanup"})
        exact(request, {"schemaVersion", "requestId", "op"} | ({"payload"} if op == "submit" else {"jobId"}) | ({"receiptSha256"} if op == "cleanup" else set()))
        require(type(request["schemaVersion"]) is int and request["schemaVersion"] == 1)
        require(type(request["requestId"]) is int and 0 < request["requestId"] <= 9007199254740991)
        require(request["requestId"] not in self.request_ids, "duplicate-request", "Request ID has already been used in this session")
        self.request_ids.add(request["requestId"])
        if op == "submit":
            return self.submit(request["payload"])
        if op == "cleanup":
            return self.cleanup(request["jobId"], request["receiptSha256"])
        return getattr(self, op)(request["jobId"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    serve = commands.add_parser("serve")
    serve.add_argument("--root", required=True)
    serve.add_argument("--registry", required=True)
    commands.add_parser("inspect")
    args = parser.parse_args()
    if args.command == "inspect":
        try:
            payload = strict_json(sys.stdin.buffer.read(WIRE_LIMIT + 1))
            _, manifest, manifest_hash = validate_payload(payload)
            print(json.dumps({"schemaVersion": 1, "dryRun": True, "engine": manifest["engine"], "modelSha256": manifest["modelSha256"], "manifestSha256": manifest_hash, "files": manifest["files"], "executed": False}))
            return 0
        except BrokerError as exc:
            print(json.dumps({"ok": False, "error": {"code": exc.code, "message": str(exc)}}))
            return 1
    broker = Broker(args.root, args.registry)
    processing = False
    stop_pending = False
    def stop(signum, _frame):
        nonlocal stop_pending
        if processing:
            stop_pending = True
        else:
            raise SystemExit(128 + signum)
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        while True:
            raw = sys.stdin.buffer.readline(WIRE_LIMIT + 1)
            if not raw:
                break
            request_id = None
            processing = True
            try:
                require(len(raw) <= WIRE_LIMIT and raw.endswith(b"\n"), "size-limit", "Wire request exceeds limit")
                request = strict_json(raw)
                if type(request) is dict and type(request.get("requestId")) is int:
                    request_id = request["requestId"]
                result = broker.dispatch(request)
                response = {"schemaVersion": 1, "requestId": request_id, "ok": True, "result": result}
            except BrokerError as exc:
                response = {"schemaVersion": 1, "requestId": request_id, "ok": False, "error": {"code": exc.code, "message": str(exc)}}
            except Exception:
                response = {"schemaVersion": 1, "requestId": request_id, "ok": False, "error": {"code": "broker-error", "message": "Broker operation failed; inspect host locally"}}
            print(json.dumps(response, separators=(",", ":")), flush=True)
            processing = False
            if stop_pending or len(raw) > WIRE_LIMIT:
                break
    finally:
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        broker.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
