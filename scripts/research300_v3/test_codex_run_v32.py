"""Process/budget controls use a local fake event producer, never a model."""
from pathlib import Path
import sys
import tempfile
import unittest

from .run_codex_v32 import invoke


class InvocationTests(unittest.TestCase):
    def run_events(self, program, wall=5, tools=10):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            command = [sys.executable, '-u', '-c', 'import sys,json,time;sys.stdin.read();' + program]
            result = invoke(command, 'synthetic process test', root, wall, tools)
            self.assertTrue((root / 'events.jsonl').exists())
            return result

    def test_started_and_completed_tool_count_only_once(self):
        result = self.run_events('print(json.dumps({"type":"item.started","item":{"type":"command_execution","id":"x"}}));'
            'print(json.dumps({"type":"item.completed","item":{"type":"command_execution","id":"x"}}));'
            'print(json.dumps({"type":"turn.completed"}))')
        self.assertEqual(result['toolCallsObserved'], 1)
        self.assertEqual(result['exitCode'], 0)
        self.assertEqual(result['events'][-1]['type'], 'turn.completed')

    def test_observed_tool_overflow_stops_process(self):
        result = self.run_events('[print(json.dumps({"type":"item.started","item":{"type":"command_execution","id":str(i)}})) for i in range(3)];time.sleep(30)', tools=2)
        self.assertEqual(result['stopReason'], 'tool_budget_observed_overflow')
        self.assertEqual(result['toolCallsObserved'], 3)
        self.assertLess(result['elapsedSeconds'], 3)

    def test_wall_budget_stops_process(self):
        result = self.run_events('time.sleep(30)', wall=.15)
        self.assertEqual(result['stopReason'], 'wall_time_limit')
        self.assertLess(result['elapsedSeconds'], 3)

    def test_invalid_event_bytes_are_not_silently_dropped(self):
        result = self.run_events('print("not-json")')
        self.assertEqual(result['malformedEvents'], ['not-json'])


if __name__ == '__main__':
    unittest.main()
