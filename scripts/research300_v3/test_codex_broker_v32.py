"""Synthetic transport controls; these are never candidate/native results."""
import json
from pathlib import Path
import tempfile
import unittest
import uuid

from .codex_broker_v32 import Broker, write


class BrokerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.calls = []

        def executor(request, job, sut, engine, role):
            self.calls.append(request)
            if request.get('fail'):
                raise ValueError('synthetic native failure')
            write(job / 'state.json', {'model': request})
            return {'ok': True, 'data': request}

        self.broker = Broker(self.root / 'work', self.root / 'base', self.root,
                             {'sutCommit': 'b' * 40, 'executionSpecificationSha256': 'a' * 64},
                             2, executor=executor)
        self.broker.start()
        self.addCleanup(self.broker.close)
        self.broker.open_turn('V3-INT-006', 't1')

    def submit(self, value, turn='t1'):
        path = self.root / 'base/V3-INT-006/scratch/requests' / turn / (uuid.uuid4().hex + '.json')
        write(path, value)
        self.broker._scan()
        return path

    def test_request_snapshot_and_controller_identity(self):
        path = self.submit({'marker': 1})
        original = path.read_bytes()
        path.write_text('{"marker":2}')
        self.broker.close_turn('V3-INT-006', 't1')
        attempt = self.broker.attempts('V3-INT-006', 't1')[0]
        self.assertNotEqual(attempt['evidenceId'], path.stem)
        job = self.root / 'work/solver-jobs/V3-INT-006' / attempt['evidenceId']
        self.assertEqual((job / 'submitted-request.json').read_bytes(), original)
        self.assertEqual(self.calls, [{'marker': 1}])
        reply = self.root / 'base/V3-INT-006/solver-replies/t1' / path.name
        self.assertEqual(json.loads(reply.read_bytes())['jobId'], attempt['evidenceId'])

    def test_failed_and_unreported_attempts_count_towards_budget(self):
        self.submit({'fail': True})
        self.submit({'unused': True})
        self.submit({'mustNotExecute': True})
        self.broker.close_turn('V3-INT-006', 't1')
        attempts = self.broker.attempts('V3-INT-006', 't1')
        self.assertEqual(len(attempts), 3)
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(attempts[-1]['preExecutionRejection'], 'NATIVE_ATTEMPT_BUDGET_EXCEEDED')

    def test_late_request_retains_old_turn_and_cannot_execute(self):
        self.submit({'initial': True})
        self.broker.close_turn('V3-INT-006', 't1')
        self.broker.open_turn('V3-INT-006', 't2')
        self.submit({'late': True})
        self.submit({'current': True}, 't2')
        self.broker.close_turn('V3-INT-006', 't1')
        self.broker.close_turn('V3-INT-006', 't2')
        self.assertEqual(self.broker.attempts('V3-INT-006', 't1')[-1]['preExecutionRejection'], 'TURN_CLOSED')
        self.assertEqual(len(self.calls), 2)

    def test_future_request_not_executed(self):
        self.submit({'future': True}, 't2')
        self.broker.close_turn('V3-INT-006', 't1')
        self.assertEqual(self.calls, [])
        self.assertEqual(self.broker.attempts('V3-INT-006', 't2'), [])

    def test_symlink_cannot_read_controller_bytes(self):
        secret = self.root / 'private.json'
        secret.write_text('{"secret":true}')
        folder = self.root / 'base/V3-INT-006/scratch/requests/t1'
        folder.mkdir(parents=True)
        (folder / (uuid.uuid4().hex + '.json')).symlink_to(secret)
        self.broker.close_turn('V3-INT-006', 't1')
        self.assertEqual(self.calls, [])
        self.assertEqual(self.broker.attempts('V3-INT-006', 't1')[0]['preExecutionRejection'], 'UNSAFE_REQUEST_PATH')


if __name__ == '__main__':
    unittest.main()
