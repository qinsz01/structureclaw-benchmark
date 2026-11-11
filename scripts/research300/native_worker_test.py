#!/usr/bin/env python3
"""Local protocol regressions with harmless fake drivers, never native solvers."""
import base64
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

from native_worker import Broker, BrokerError, canonical, sha, validate_payload, strict_json


def payload(settings=None, engine="OpenSees"):
    raw = canonical({"format": "native-numeric-v1", "tables": {"nodes": [[1, 0, 0, 0]], "elements": [], "settings": settings or []}})
    digest = sha(raw)
    return {"schemaVersion": 1, "engine": engine, "modelSha256": digest, "files": [{"path": "model.json", "sha256": digest, "size": len(raw), "contentBase64": base64.b64encode(raw).decode()}]}


@unittest.skipIf(os.name == "nt", "POSIX fake executable fixture; Windows process support tested separately")
class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="native-broker-test-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.driver = self.base / "native-opensees-worker"
        self.driver.write_text("#!" + sys.executable + "\n" + '''import json,time,sys,os
from pathlib import Path
model=json.loads(Path("model.json").read_text())
settings=model["tables"]["settings"]
if settings:
    time.sleep(settings[0])
Path("result.json").write_text(json.dumps({"sum":sum(row[1] for row in model["tables"]["nodes"])}))
print("numeric fixture complete", flush=True)
''')
        self.driver.chmod(0o700)
        self.lease = self.base / "isolation.json"
        self.driver_hash = sha(self.driver.read_bytes())
        self.lease.write_bytes(canonical({"schemaVersion": 1, "engine": "OpenSees", "executableSha256": self.driver_hash, "isolated": True, "expiresAt": time.time() + 120}))
        self.registry = self.base / "registry.json"
        self.config = {"schemaVersion": 1, "engines": {"OpenSees": {"enabled": True, "executable": str(self.driver), "sha256": self.driver_hash, "independentCompilerReviewed": True, "isolationVerified": True, "isolationLease": str(self.lease)}}}
        self.save_registry()
        self.broker = Broker(self.base / "jobs", self.registry)
        self.addCleanup(self.broker.close)

    def save_registry(self):
        self.registry.write_bytes(canonical(self.config))

    def done(self, job):
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            state = self.broker.status(job["jobId"])
            if state["state"] != "running":
                return state
            time.sleep(.01)
        self.fail("fixture did not finish")

    def assert_code(self, code, call):
        with self.assertRaises(BrokerError) as caught:
            call()
        self.assertEqual(caught.exception.code, code)

    def test_lifecycle_binds_input_manifest_raw_outputs_and_cleanup(self):
        envelope = payload()
        _, _, digest = validate_payload(envelope)
        job = self.broker.submit(envelope)
        self.assertRegex(job["jobId"], r"^[0-9a-f]{32}$")
        self.assertEqual(job["manifestSha256"], digest)
        self.assertEqual(self.done(job)["state"], "succeeded")
        bundle = self.broker.collect(job["jobId"])
        receipt = bundle["receipt"]
        self.assertEqual(receipt["nativeTruthStatus"], "pending-independent-review")
        self.assertTrue(receipt["executed"])
        self.assertEqual(receipt["exitCode"], 0)
        self.assertEqual(bundle["receiptSha256"], sha(canonical(receipt)))
        self.assertEqual({x["path"] for x in bundle["artifacts"]}, {"model.json", "result.json", "stdout.log", "stderr.log"})
        for item in bundle["artifacts"]:
            raw = base64.b64decode(item["contentBase64"])
            self.assertEqual(item["sha256"], sha(raw))
            self.assertEqual(item["size"], len(raw))
        self.assert_code("hash-mismatch", lambda: self.broker.cleanup(job["jobId"], "0" * 64))
        self.assertTrue(self.broker.cleanup(job["jobId"], bundle["receiptSha256"])["cleaned"])
        self.assert_code("not-found", lambda: self.broker.status(job["jobId"]))

    def test_random_identity_not_model_or_benchmark_id(self):
        first = self.broker.submit(payload())
        self.done(first)
        second = self.broker.submit(payload())
        self.done(second)
        self.assertNotEqual(first["jobId"], second["jobId"])
        self.assertEqual(first["modelSha256"], second["modelSha256"])
        self.assert_code("invalid-request", lambda: self.broker.status("STD-001"))

    def test_concurrent_brokers_share_exclusive_engine_lock(self):
        job = self.broker.submit(payload([2]))
        other = Broker(self.base / "jobs", self.registry)
        self.addCleanup(other.close)
        self.assert_code("resource-busy", lambda: other.submit(payload()))
        self.assertEqual(other.status(job["jobId"])["state"], "resource-busy")
        self.assert_code("resource-busy", lambda: other.cancel(job["jobId"]))
        self.assertEqual(self.broker.cancel(job["jobId"])["state"], "cancelled")
        next_job = other.submit(payload())
        other.cancel(next_job["jobId"])

    def test_cancel_only_own_child_and_collect_cancelled_evidence(self):
        unrelated = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(10)"])
        self.addCleanup(lambda: unrelated.poll() is None and unrelated.kill())
        job = self.broker.submit(payload([10]))
        self.assert_code("not-ready", lambda: self.broker.collect(job["jobId"]))
        self.assertEqual(self.broker.cancel(job["jobId"])["state"], "cancelled")
        self.assertIsNone(unrelated.poll())
        self.assertEqual(self.broker.collect(job["jobId"])["receipt"]["state"], "cancelled")
        unrelated.terminate()
        unrelated.wait()

    def test_eof_close_cancels_jobs(self):
        job = self.broker.submit(payload([10]))
        self.broker.close()
        self.assertEqual(self.broker.status(job["jobId"])["state"], "cancelled")

    def test_artifact_change_after_completion_rejected(self):
        job = self.broker.submit(payload())
        self.done(job)
        (self.base / "jobs" / job["jobId"] / "result.json").write_text('{"sum":999}')
        self.assert_code("hash-mismatch", lambda: self.broker.collect(job["jobId"]))

    def test_new_artifact_after_sealing_is_not_silently_deleted(self):
        job = self.broker.submit(payload())
        self.done(job)
        path = self.base / "jobs" / job["jobId"]
        original = self.broker.collect(job["jobId"])
        (path / "native-input.dat").write_text("late native evidence")
        self.assert_code("hash-mismatch", lambda: self.broker.collect(job["jobId"]))
        self.assert_code("hash-mismatch", lambda: self.broker.cleanup(job["jobId"], original["receiptSha256"]))
        self.assertTrue((path / "native-input.dat").exists())

    def test_unknown_extra_file_blocks_cleanup_without_deleting_evidence(self):
        job = self.broker.submit(payload())
        self.done(job)
        bundle = self.broker.collect(job["jobId"])
        path = self.base / "jobs" / job["jobId"]
        (path / "extra-native-file.dat").write_text("retain for inspection")
        self.assert_code("unsafe-path", lambda: self.broker.cleanup(job["jobId"], bundle["receiptSha256"]))
        self.assertTrue((path / "model.json").exists())

    def test_duplicate_request_id_never_submits_twice(self):
        req = {"schemaVersion": 1, "requestId": 1, "op": "submit", "payload": payload()}
        job = self.broker.dispatch(req)
        self.done(job)
        self.assert_code("duplicate-request", lambda: self.broker.dispatch(req))
        self.assertEqual(len([p for p in (self.base / "jobs").iterdir() if len(p.name) == 32]), 1)

    def test_sigterm_of_cli_cancels_owned_job_before_exit(self):
        worker = subprocess.Popen([sys.executable, str(Path(__file__).with_name("native_worker.py")), "serve", "--root", str(self.base / "jobs"), "--registry", str(self.registry)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.addCleanup(lambda: worker.poll() is None and worker.kill())
        worker.stdin.write(json.dumps({"schemaVersion": 1, "requestId": 1, "op": "submit", "payload": payload([10])}) + "\n")
        worker.stdin.flush()
        response = json.loads(worker.stdout.readline())
        self.assertTrue(response["ok"], response)
        job_id = response["result"]["jobId"]
        worker.terminate()
        worker.wait(timeout=5)
        worker.stdin.close()
        worker.stdout.close()
        worker.stderr.close()
        state = self.broker.status(job_id)
        self.assertEqual(state["state"], "cancelled")
        self.assertFalse((self.base / "jobs" / "opensees.lock").exists())

    def test_manifest_change_after_completion_rejected(self):
        job = self.broker.submit(payload())
        self.done(job)
        path = self.base / "jobs" / job["jobId"] / "manifest.json"
        manifest = json.loads(path.read_text())
        manifest["engine"] = "YJK"
        path.write_bytes(canonical(manifest))
        self.assert_code("hash-mismatch", lambda: self.broker.collect(job["jobId"]))

    def test_input_change_after_completion_rejected(self):
        job = self.broker.submit(payload())
        self.done(job)
        (self.base / "jobs" / job["jobId"] / "model.json").write_text('{}')
        self.assert_code("hash-mismatch", lambda: self.broker.collect(job["jobId"]))

    def test_artifact_symlink_rejected_and_cleanup_keeps_target(self):
        job = self.broker.submit(payload())
        self.done(job)
        target = self.base / "unrelated.txt"
        target.write_text("must survive")
        path = self.base / "jobs" / job["jobId"] / "result.json"
        path.unlink()
        path.symlink_to(target)
        self.assert_code("unsafe-path", lambda: self.broker.collect(job["jobId"]))
        self.assertEqual(target.read_text(), "must survive")

    def test_job_symlink_and_root_symlink_rejected(self):
        target = self.base / "outside"
        target.mkdir()
        alias = self.base / "alias"
        alias.symlink_to(target, target_is_directory=True)
        self.assert_code("unsafe-path", lambda: Broker(alias, self.registry))
        (self.base / "jobs" / ("a" * 32)).symlink_to(target, target_is_directory=True)
        self.assert_code("unsafe-path", lambda: self.broker.status("a" * 32))

    def test_missing_disabled_unreviewed_busy_or_expired_isolation_fail_closed(self):
        for key in ("enabled", "independentCompilerReviewed", "isolationVerified"):
            self.config["engines"]["OpenSees"][key] = False
            self.save_registry()
            self.assert_code("resource-busy", lambda: self.broker.submit(payload()))
            self.config["engines"]["OpenSees"][key] = True
        self.save_registry()
        self.lease.write_bytes(canonical({"schemaVersion": 1, "engine": "OpenSees", "executableSha256": self.driver_hash, "isolated": True, "expiresAt": time.time() - 1}))
        self.assert_code("resource-busy", lambda: self.broker.submit(payload()))
        self.assert_code("resource-busy", lambda: self.broker.submit(payload(engine="YJK")))
        self.assertFalse(list((self.base / "jobs").iterdir()))

    def test_stale_lock_is_never_reclaimed_by_pid(self):
        lock = self.base / "jobs" / "opensees.lock"
        lock.mkdir()
        (lock / "owner.json").write_text('{"pid":1}')
        self.assert_code("resource-busy", lambda: self.broker.submit(payload()))
        self.assertTrue(lock.exists())

    def test_pin_and_fixed_executable_whitelist(self):
        self.driver.write_text(self.driver.read_text() + "# changed\n")
        self.assert_code("hash-mismatch", lambda: self.broker.submit(payload()))
        other = self.base / "arbitrary-command"
        other.write_text("not an approved driver")
        self.config["engines"]["OpenSees"]["executable"] = str(other)
        self.save_registry()
        self.assert_code("executable-not-allowed", lambda: self.broker.submit(payload()))

    def test_wire_request_rejects_command_pid_paths_and_wrong_version(self):
        for additions in ({"command": "touch x"}, {"pid": 1}, {"cwd": "/tmp"}, {"schemaVersion": 2}):
            req = {"schemaVersion": 1, "requestId": 1, "op": "submit", "payload": payload(), **additions}
            self.assert_code("invalid-request", lambda: self.broker.dispatch(req))
        self.assert_code("invalid-request", lambda: self.broker.status("../outside"))

    def test_cli_inspection_is_offline_and_redacts_raw_model(self):
        result = subprocess.run([sys.executable, str(Path(__file__).with_name("native_worker.py")), "inspect"], input=json.dumps(payload()), text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        info = json.loads(result.stdout)
        self.assertTrue(info["dryRun"])
        self.assertFalse(info["executed"])
        self.assertNotIn("contentBase64", result.stdout)
        self.assertNotIn("nodes", result.stdout)
        self.assertFalse(list((self.base / "jobs").iterdir()))


class PayloadTests(unittest.TestCase):
    def invalid(self, value, code="invalid-request"):
        with self.assertRaises(BrokerError) as caught:
            validate_payload(value)
        self.assertEqual(caught.exception.code, code)

    def test_numeric_only_and_exact_keys(self):
        for model in (
            {"format": "native-numeric-v1", "tables": {"nodes": [["STD-001"]], "elements": [], "settings": []}},
            {"format": "native-numeric-v1", "tables": {"nodes": [], "elements": [], "settings": [{"expected": 3}]}},
            {"format": "native-numeric-v1", "tables": {"nodes": [], "elements": [], "settings": [], "prompt": []}},
            {"format": "native-numeric-v1", "tables": {"nodes": [], "elements": [], "settings": []}, "expected": 1},
        ):
            raw = canonical(model)
            value = payload()
            value["modelSha256"] = sha(raw)
            value["files"][0].update(sha256=sha(raw), size=len(raw), contentBase64=base64.b64encode(raw).decode())
            self.invalid(value)

    def test_tampered_size_hash_base64_traversal_extra_file(self):
        for key, changed, code in (("path", "../model.json", "invalid-request"), ("size", 1, "hash-mismatch"), ("sha256", "0" * 64, "hash-mismatch"), ("contentBase64", "???", "invalid-request")):
            value = payload()
            value["files"][0][key] = changed
            self.invalid(value, code)
        value = payload()
        value["files"].append(copy.deepcopy(value["files"][0]))
        self.invalid(value)

    def test_duplicate_keys_nonfinite_and_deep_tables_rejected(self):
        for raw in (b'{"x":1,"x":2}', b'{"x":NaN}'):
            with self.assertRaises(BrokerError):
                strict_json(raw)
        value = payload()
        raw = b'{"format":"native-numeric-v1","tables":{"nodes":[],"elements":[],"settings":[1e999]}}'
        value["modelSha256"] = sha(raw)
        value["files"][0].update(sha256=sha(raw), size=len(raw), contentBase64=base64.b64encode(raw).decode())
        self.invalid(value)


if __name__ == "__main__":
    unittest.main()
