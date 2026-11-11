"""Full-scope routing/lifecycle and transport classification; no model/solver."""
import json
from pathlib import Path
import tempfile
import unittest
import uuid

from .codex_full_broker_v32 import FullBroker
from .codex_broker_v32 import write
from .codex_full_status_v32 import classify


class StatusTests(unittest.TestCase):
    def test_recovered_transport_warning_does_not_retry_completed_turn(self):
        status = classify({'exitCode': 0}, [{'type': 'error', 'message': '429'}, {'type': 'turn.completed'}])
        self.assertEqual(status, ('completed', False, None))

    def test_only_known_transport_errors_allow_recovery(self):
        for message in ('429 Too Many Requests', 'Selected model is at capacity', 'stream disconnected', 'status: 503'):
            self.assertEqual(classify({'exitCode': 1}, [{'type': 'turn.failed', 'error': {'message': message}}])[:2], ('service_blocked', True))

    def test_context_limit_is_candidate_failure_without_retry(self):
        self.assertEqual(classify({'exitCode': 1}, [{'type': 'turn.failed', 'error': {'message': 'context_length_exceeded'}}])[:2], ('candidate_failed', False))

    def test_authentication_is_blocked_without_retry(self):
        self.assertEqual(classify({'exitCode': 1}, [{'type': 'error', 'message': '401 unauthorized'}])[:2], ('service_blocked', False))

    def test_budget_and_unknown_failures_are_not_transport_retries(self):
        self.assertEqual(classify({'exitCode': -15, 'stopReason': 'wall_time_limit'}, [])[:2], ('candidate_failed', False))
        self.assertEqual(classify({'exitCode': 1}, [{'type': 'turn.failed', 'error': 'unknown'}])[:2], ('interrupted', False))

    def test_corrupt_event_stream_is_ungradable(self):
        self.assertEqual(classify({'exitCode': 0, 'malformedEvents': ['broken']}, [{'type': 'turn.completed'}])[:2], ('interrupted', False))


class FullBrokerTests(unittest.TestCase):
    def test_designated_engine_and_retired_ledger_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            calls = []

            def executor(request, job, sut, engine, role):
                calls.append((engine, role))
                write(job / 'state.json', {'model': request})
                return {'ok': True}

            engines = {'V3-STD-001': 'OpenSees', 'V3-STD-002': 'PKPM', 'V3-STD-003': 'YJK'}
            broker = FullBroker(root / 'work', root / 'base', root, {'sutCommit': 'a' * 40,
                                'executionSpecificationSha256': 'b' * 64}, 2, engines=engines, executor=executor)
            broker.start()
            try:
                for cid, engine in engines.items():
                    broker.open_turn(cid, 't1')
                    write(root / 'base' / cid / 'scratch/requests/t1' / (uuid.uuid4().hex + '.json'), {'value': 1})
                    broker.close_turn(cid, 't1')
                    identity = broker.attempts(cid, 't1')[0]['evidenceId']
                    broker.retire_case(cid)
                    self.assertEqual(broker.attempts(cid, 't1')[0]['evidenceId'], identity)
                    self.assertNotIn((cid, 't1'), broker.turns)
                    receipt = json.loads((root / 'work/solver-jobs' / cid / identity / 'broker-receipt.json').read_bytes())
                    self.assertEqual(receipt['engine'], engine)
                    with self.assertRaises(ValueError):
                        broker.open_turn(cid, 't1')
                self.assertCountEqual(calls, [(e, 'candidate') for e in engines.values()])
            finally:
                broker.close()

    def test_open_turn_cannot_be_retired(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            broker = FullBroker(root / 'work', root / 'base', root, {}, 1, engines={'V3-STD-001': 'OpenSees'})
            broker.start()
            try:
                broker.open_turn('V3-STD-001', 't1')
                with self.assertRaises(ValueError):
                    broker.retire_case('V3-STD-001')
                broker.close_turn('V3-STD-001', 't1')
                broker.retire_case('V3-STD-001')
            finally:
                broker.close()


if __name__ == '__main__':
    unittest.main()
