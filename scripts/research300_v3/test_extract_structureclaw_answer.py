import hashlib
import unittest

from scripts.research300_v3.extract_structureclaw_answer import extract_fenced_answer


class LiteralFinalAnswerTests(unittest.TestCase):
    def test_prose_and_unicode_preserve_every_answer_byte(self):
        literal = '{"runIds":["original-run"],"quantities":[{"value":-0.00000000000000001,"unit":"m"}],"clarifications":[]}'
        original = '原始说明。\n\n```json\n  ' + literal + ' \n```\nAfterword.'
        result = extract_fenced_answer(original)
        self.assertEqual(result['answer'], literal.encode())
        receipt = result['receipt']
        self.assertEqual(original.encode()[receipt['byteStart']:receipt['byteEnd']], result['answer'])
        self.assertEqual(receipt['originalUtf8Sha256'], hashlib.sha256(original.encode()).hexdigest())
        self.assertEqual(receipt['answerSha256'], hashlib.sha256(literal.encode()).hexdigest())
        self.assertEqual((receipt['fieldsAdded'], receipt['valuesChanged']), (0, 0))

    def test_clarification_empty_references_and_crlf_are_not_filled(self):
        literal = '{"runIds":[],"quantities":[],"clarifications":[{"field":"given-field","question":"confirm?"}]}'
        result = extract_fenced_answer('Explanation\r\n```JSON\r\n'+literal+'\r\n```')
        self.assertEqual(result['answer'], literal.encode())

    def test_multiple_blocks_or_reference_families_are_refused(self):
        block = '```json\n{"runIds":[],"quantities":[]}\n```'
        self.assertIsNone(extract_fenced_answer(block+'\n'+block))
        self.assertIsNone(extract_fenced_answer('```json\n{"runIds":[],"jobIds":[],"quantities":[]}\n```'))

    def test_invalid_truncated_duplicate_or_non_json_values_are_refused(self):
        for literal in ['{"runIds":[],"quantities":[', '{"runIds":[],"runIds":["other"],"quantities":[]}',
                        '{"runIds":[],"quantities":[NaN]}', '{"runIds":[],"quantities":[Infinity]}',
                        '[{"runIds":[],"quantities":[]}]', '{"message":"no answer"}']:
            with self.subTest(literal=literal):
                self.assertIsNone(extract_fenced_answer('```json\n'+literal+'\n```'))
        self.assertIsNone(extract_fenced_answer('{"runIds":[],"quantities":[]}'))
        self.assertIsNone(extract_fenced_answer(None))


if __name__ == '__main__':
    unittest.main()
