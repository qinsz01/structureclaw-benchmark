"""Recover the CLI's own interrupted records without inventing completed turns."""
import json
from pathlib import Path
import tempfile
import unittest

from .resume_candidate import TRANSPORT, capture_interrupted


class RecoveryCaptureTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.work, self.base = self.root / 'work', self.root / 'sessions'
        self.work.mkdir()
        self.directory = self.work / 'runs/C/t1'
        self.directory.mkdir(parents=True)
        self.scratch = self.base / 'C/scratch'
        self.scratch.mkdir(parents=True)
        self.cases = [{'id': 'C', 'turns': [{'id': 't1'}]}]
        self.save(self.work / 'operator-interruption-001.json', {
            'originalRunnerPid': 2147483646, 'brokerPidDraining': 2147483645,
            'ownedCliGroupsSignaled': [], 'reason': 'fixture transport interruption'})

    @staticmethod
    def save(path, value):
        path.write_text(json.dumps(value) + '\n')

    def test_completed_execution_is_preserved_byte_for_byte(self):
        path = self.directory / 'execution.json'
        self.save(path, {'completedTurn': True, 'threadId': 'original-thread', 'currentJobIds': []})
        before = path.read_bytes()
        self.assertEqual(capture_interrupted(self.work, self.base, self.cases), [])
        self.assertEqual(path.read_bytes(), before)

    def test_provider_capacity_is_transport_but_context_exhaustion_is_not(self):
        self.assertIsNotNone(TRANSPORT.search('Selected model is at capacity. Please try a different model.'))
        self.assertIsNotNone(TRANSPORT.search('HTTP 429 Too Many Requests'))
        self.assertIsNone(TRANSPORT.search('Model context window exceeded'))
        self.assertIsNone(TRANSPORT.search('Invalid model input: section properties are missing'))

    def test_interrupted_thread_and_delivered_bytes_are_not_invented(self):
        self.save(self.directory / 'dispatch.json', {'startedAt': 1, 'parentThread': None})
        (self.directory / 'events.jsonl').write_text('{"type":"thread.started","thread_id":"original-thread"}\n{"type":"turn.started"}\n{"partial":')
        answer = b'{"value":-0.0,"note":"original candidate bytes"}\n'
        (self.scratch / 'answer-t1.json').write_bytes(answer)
        job = self.work / 'solver-jobs/C' / ('a' * 32)
        job.mkdir(parents=True)
        self.save(job / 'broker-receipt.json', {})
        closed = capture_interrupted(self.work, self.base, self.cases)
        record = json.loads((self.directory / 'execution.json').read_text())
        self.assertEqual(closed[0]['completedTurn'], False)
        self.assertEqual(record['threadId'], 'original-thread')
        self.assertIsNone(record['exitCode'])
        self.assertFalse(record['completedTurn'])
        self.assertEqual(record['invalidJsonLines'], [3])
        self.assertEqual(record['currentJobIds'], ['a' * 32])
        self.assertEqual((self.directory / 'answer.json').read_bytes(), answer)
        self.assertEqual((self.scratch / 'answer-t1.json').read_bytes(), answer)
        self.assertEqual(capture_interrupted(self.work, self.base, self.cases), [])


if __name__ == '__main__':
    unittest.main()
