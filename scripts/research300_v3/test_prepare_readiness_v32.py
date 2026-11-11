"""Offline contract tests; no model, application or native solver is invoked."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from scripts.research300_v3 import prepare_readiness_v32 as p


class PublicDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='research300-v32-input-test-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.edition = self.root / 'edition'
        self.edition.mkdir()
        self.manifest = {'cases': [], 'files': []}
        for cid, level, turns in [('V3-INT-071', 'L4', 4), ('V3-MM-001', 'L1', 1)]:
            case = {'id': cid, 'level': level, 'turns': []}
            for n in range(1, turns + 1):
                base = f'cases/{cid}/public/t{n}'
                turn = {'id': f't{n}', 'public': base}
                files = {'drawing.png': b'original-image-bytes', 'note.txt': f'public revision {n}'.encode()}
                if level == 'L4' and n == 1:
                    files.update({name: ('原始公开规则：' + name + '\n  keep spacing\n').encode() for name in p.INLINE})
                files['task.json'] = json.dumps({'attachments': list(files), 'task': 'Read original sources'}).encode()
                for name, data in files.items():
                    target = self.edition / base / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(data)
                    self.manifest['files'].append({'path': base + '/' + name, 'sha256': p.sha(data)})
                case['turns'].append(turn)
            self.manifest['cases'].append(case)
        (self.edition / 'manifest.json').write_text(json.dumps(self.manifest))
        (self.edition / 'private-answer.json').write_text('{"secret":true}')

    def test_packet_contains_only_issued_case_history_and_unchanged_sources(self):
        delivery = p.public_delivery(self.edition, self.manifest)
        output = self.root / 'candidate'
        p.packet(self.edition, delivery, 'V3-INT-071', 't2', output)
        self.assertEqual({x.name for x in output.iterdir()}, {'t1', 't2'})
        for row in delivery['turns'][:2]:
            for file in row['files']:
                self.assertEqual((output / row['turnId'] / file['packetPath']).read_bytes(),
                                 (self.edition / file['editionPath']).read_bytes())
        self.assertFalse(list(output.rglob('*private*')))
        self.assertFalse(list(output.rglob('manifest.json')))

    def test_l4_rules_are_verbatim_real_user_text_without_future_changes(self):
        delivery = p.public_delivery(self.edition, self.manifest)
        output = self.root / 'candidate'
        p.packet(self.edition, delivery, 'V3-INT-071', 't1', output)
        message = (output / 't1/user-message.txt').read_text()
        for name in p.INLINE:
            self.assertIn((self.edition / 'cases/V3-INT-071/public/t1' / name).read_text(), message)
        self.assertNotIn('revision 2', message)

    def test_image_bytes_are_copied_without_ocr_or_reencoding(self):
        delivery = p.public_delivery(self.edition, self.manifest)
        output = self.root / 'candidate'
        p.packet(self.edition, delivery, 'V3-MM-001', 't1', output)
        self.assertEqual((output / 't1/drawing.png').read_bytes(), b'original-image-bytes')
        self.assertEqual({x.name for x in (output / 't1').iterdir()},
                         {'drawing.png', 'note.txt', 'task.json', 'user-message.txt'})

    def test_changed_frozen_file_and_postpreparation_changes_fail(self):
        delivery = p.public_delivery(self.edition, self.manifest)
        source = self.edition / self.manifest['files'][0]['path']
        source.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'Frozen public input changed'):
            p.public_delivery(self.edition, self.manifest)
        with self.assertRaisesRegex(ValueError, 'Public input changed'):
            p.packet(self.edition, delivery, 'V3-INT-071', 't1', self.root / 'candidate')

    def test_symlinks_and_parent_traversal_are_rejected(self):
        (self.edition / 'link').symlink_to(self.edition / 'manifest.json')
        for name in ('../manifest.json', './manifest.json', 'a\\manifest.json', 'link'):
            with self.assertRaises(ValueError):
                p.relative_file(self.edition, name)

    def test_python_and_node_pin_the_same_scoring_source_closure(self):
        source = "process.stdout.write(JSON.stringify(require('./scripts/research300_v3/code-closure-v32.cjs').codeBinding()))"
        result = subprocess.run(['node', '-e', source], cwd=p.ROOT, text=True, capture_output=True, check=True)
        self.assertEqual(p.code_binding(), json.loads(result.stdout))


if __name__ == '__main__':
    unittest.main()
