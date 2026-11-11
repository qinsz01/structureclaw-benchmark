"""Long submissions must survive Excel export without truncation or formulas."""
import base64
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from openpyxl import Workbook, load_workbook
from .summarize_candidate import answer_chunks, literal_append, summarize


class CandidateSummaryTest(unittest.TestCase):
    def test_long_unicode_submission_round_trips_as_literal_chunks(self):
        data = ('A' * 12000 + '=1+1\n' + '结构😀' * 14000).encode('utf-8')
        encoding, chunks = answer_chunks(data)
        self.assertEqual(encoding, 'utf-8')
        self.assertTrue(chunks[1].startswith('='))
        self.assertGreater(len(chunks), 3)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'answers.xlsx'
            workbook = Workbook()
            sheet = workbook.active
            for chunk in chunks:
                literal_append(sheet, [chunk])
            workbook.save(path)
            reopened = load_workbook(path, read_only=True, data_only=False)
            cells = [row[0] for row in reopened.active.iter_rows()]
            self.assertTrue(all(cell.data_type == 's' for cell in cells))
            self.assertEqual(''.join(cell.value for cell in cells).encode('utf-8'), data)
            reopened.close()

    def test_invalid_utf8_submission_is_preserved_as_base64(self):
        data = b'\x00\xff\xfe\x01'
        encoding, chunks = answer_chunks(data)
        self.assertEqual(encoding, 'base64')
        self.assertEqual(base64.b64decode(''.join(chunks)), data)

    def test_unfinished_capture_cannot_be_published_as_a_full_review(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            edition, work, output = root / 'edition', root / 'work', root / 'review'
            edition.mkdir()
            work.mkdir()
            data = json.dumps({'cases': [], 'files': []}).encode()
            (edition / 'manifest.json').write_bytes(data)
            binding = hashlib.sha256(data).hexdigest()
            for name, value in [('candidate-binding.json', {'manifestSha256': binding}),
                                ('execution-summary.json', {'manifestSha256': binding, 'allTurnsCaptured': False, 'turns': []})]:
                (work / name).write_text(json.dumps(value))
            grade = root / 'grade.json'
            grade.write_text(json.dumps({'manifestSha256': binding}))
            with self.assertRaisesRegex(ValueError, 'Full capture has not finished'):
                summarize(edition, work, grade, output)
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
