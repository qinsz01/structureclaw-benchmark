import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from setup_public import install


class PublicToolPreflight(unittest.TestCase):
    def test_install_is_pinned_and_tampering_stops_before_any_model_dispatch(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);sut=root/'sut';api=sut/'backend'/'structure_model_v2.py'
            api.parent.mkdir(parents=True);api.write_text('"""Public model schema."""\n')
            base=root/'public';manifest=install(base,sut)
            self.assertEqual(install(base,sut),manifest)
            self.assertEqual({r['path'] for r in manifest['files']},{'analyze.py','structure_model_v2.py'})
            (base/'public-tools/analyze.py').write_text('tampered')
            with self.assertRaisesRegex(ValueError,'differs'):
                install(base,sut)
            work=root/'work';work.mkdir()
            result=subprocess.run([sys.executable,str(Path(__file__).with_name('run.py')),'--work',str(work),'--base',str(base)],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('Public tool source changed',result.stderr)
            self.assertEqual(list(work.iterdir()),[])


if __name__=='__main__':unittest.main()
