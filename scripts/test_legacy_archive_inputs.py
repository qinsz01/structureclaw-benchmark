import os
from pathlib import Path
import tempfile
import unittest

from scripts.legacy_archive_inputs import ArchiveInputRoot, load, writable, ROOT


class LegacyArchiveInputsTests(unittest.TestCase):
    def test_retained_inputs_move_while_source_and_corpora_stay_local(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = ArchiveInputRoot(base / 'repo', base / 'archive')
            for name in ['docs/implementation/reviews/run/input.json',
                         '.bench-work/retained/input.json', '.worktrees/retained/file.py']:
                self.assertEqual(root / name, base / 'archive' / name)
            for name in ['corpora/edition/manifest.json', 'scripts/pilot30/archive.py',
                         'lib/native-job.cjs', 'docs/other.md']:
                self.assertEqual(root / name, base / 'repo' / name)
            self.assertEqual(os.fspath(root), str(base / 'repo'))
            self.assertEqual((base / 'repo/scripts/tool.py').relative_to(root), Path('scripts/tool.py'))

    def test_legacy_module_source_is_unmodified_and_only_root_is_adapted(self):
        source = ROOT / 'scripts/pilot30/audit.py'
        before = source.read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory)
            module = load('scripts/pilot30/audit.py', archive)
            self.assertEqual(module.ROOT / 'docs/implementation/reviews/input.json',
                             archive / 'docs/implementation/reviews/input.json')
            self.assertEqual(module.ROOT / 'scripts/pilot30/audit.py', source)
            self.assertEqual(source.read_bytes(), before)

    def test_outputs_in_archive_or_via_symlink_are_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            archive = base / 'archive'
            archive.mkdir()
            link = base / 'link'
            link.symlink_to(archive, target_is_directory=True)
            for path in [archive, archive / 'new.json', link / 'new.json']:
                with self.assertRaises(ValueError):
                    writable(path, archive)
            self.assertEqual(writable(base / 'output.json', archive), base / 'output.json')


if __name__ == '__main__':
    unittest.main()
