"""Behavioral regressions for the independently versioned MM public inputs."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
MODULE = Path(__file__).with_name('public_input_editorial.py')


class PublicInputEditorialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # The initial red run reports the missing behavior as an assertion.
        if MODULE.exists():
            spec = importlib.util.spec_from_file_location('public_input_editorial', MODULE)
            cls.editorial = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cls.editorial)

    def test_retired_cli_rejects_every_mode_without_creating_outputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for mode in [[], ['--check'], ['--build']]:
                with self.subTest(mode=mode):
                    result = subprocess.run(
                        [sys.executable, str(MODULE), '--root', str(root), *mode],
                        capture_output=True, text=True, check=False)
                    self.assertEqual(result.returncode, 2)
                    self.assertIn('retired', result.stderr)
                    self.assertIn('public_input_clean.py --check', result.stderr)
                    self.assertEqual(list(root.iterdir()), [])

    def require_editorial(self):
        self.assertTrue(MODULE.exists(), 'The public-input table generator is not implemented')
        return self.editorial

    def test_structured_tables_preserve_optional_fields_axes_signed_loads_and_order(self):
        editor = self.require_editorial()
        data = {
            'units': 'kN; m; kN/m of actual length',
            'assignments': [
                {'id': 'b1', 'material': 'M1', 'rotation_angle': 90, 'referenceVector': [0, 0, -1]},
                {'id': 'b2', 'material': 'M1', 'rotation_angle': 90, 'referenceVector': [0, 0, -1]},
                {'id': 'b3', 'material': 'M1', 'rotation_angle': 0, 'referenceVector': None},
            ],
            'load_cases': [{'id': 'D', 'loads': [
                {'id': 'q1', 'element': 'b1', 'wz': -8, 'start': 0.0, 'end': 3.5},
                {'id': 'q2', 'element': 'b2', 'wz': -8},
                {'id': 'p1', 'node': 'n2', 'fx': 10, 'my': -2.25},
            ]}],
            'load_combinations': [{'id': 'D', 'factors': {'D': 1}},
                                  {'id': 'D+L', 'factors': {'D': 1, 'L': 1}}],
            'notes': ['literal | pipe', 'multi\nline', 'missing is not null'],
            'empty': [],
        }
        rendered = editor.render_structured(data, 'en', 'loads.json')
        self.assertEqual(editor.parse_structured(rendered), data)
        self.assertIn('b1, b2', rendered)
        changed = rendered.replace('-2.25', '2.25')
        self.assertNotEqual(editor.parse_structured(changed), data)

    def test_text_compaction_keeps_intentional_duplicate_assignments_and_every_number(self):
        editor = self.require_editorial()
        source = ('Analysis and property appendix\n\n'
                  'Load components use global XYZ axes: fx/fy/fz are concentrated forces in kN; '
                  'mx/my/mz are nodal moments in kN*m (right-hand rule); wx/wy/wz are distributed '
                  'forces in kN/m per actual member length, not projected length. '
                  'A negative z component acts along global -Z.\n\n'
                  'Materials\nM1: E=206000, G=79230.7692, nu=0.3, rho=7850\n\n'
                  'Member property assignment by drawing ID\nb1: M1 / B1\nb3: M1 / B1\nb3: M1 / B2\n')
        rendered, facts = editor.render_text(source, 'en', 'properties.txt')
        self.assertEqual(editor.parse_text(rendered), editor.normalized_lines(source))
        self.assertIn('b3', rendered)
        self.assertIn('79230.7692', rendered)
        self.assertIn('actual member length', rendered)
        self.assertGreaterEqual(len(facts), 4)

    def test_public_builder_ignores_hidden_fields_and_preserves_delayed_release(self):
        editor = self.require_editorial()
        contract = {
            'id': 'MM-001', 'locale': 'en', 'plannedEngine': 'OpenSees',
            'turns': [
                {'id': 't1', 'instruction': 'Use the attached input; ask for missing essentials.\nRequested outputs:\nSigned left reaction Fz.', 'attachments': ['initial.svg', 'properties.json']},
                {'id': 't2', 'instruction': 'The new drawing confirms a -15 kN global Z force.', 'attachments': ['resolved.svg']},
            ],
            'sourcePlan': {'secret': 'HIDDEN_GEOMETRY_ANSWER'},
            'unresolvedFields': ['SECRET_MISSING_VALUE'],
        }
        files = {'initial.svg': b'<svg>initial</svg>', 'resolved.svg': b'<svg>resolved</svg>',
                 'properties.json': b'{"E":206000,"units":"MPa"}'}
        row = {'sourceHash': 'a' * 64, 'publicSha256': 'b' * 64}
        bundle, content, audit = editor.build_case(contract, row, files)
        first, second = bundle['turns']
        self.assertEqual([a['path'] for a in first['attachments'] if a['source'] == 'frozen'], ['initial.svg'])
        self.assertEqual([a['path'] for a in second['attachments'] if a['source'] == 'frozen'], ['resolved.svg'])
        self.assertNotIn('-15', first['instruction'])
        self.assertIn('-15', second['instruction'])
        all_public = json.dumps(bundle) + ''.join(content.values())
        self.assertNotIn('HIDDEN_GEOMETRY_ANSWER', all_public)
        self.assertNotIn('SECRET_MISSING_VALUE', all_public)
        poisoned = copy.deepcopy(contract)
        poisoned['sourcePlan'] = {'secret': 'OTHER_ANSWER'}
        poisoned['expectedQuestions'] = ['ASK_THIS_SECRET']
        self.assertEqual(editor.build_case(poisoned, row, files)[:2], (bundle, content))

    def test_real_mm_json_roundtrip_all_cases_and_reduced_appendix_payload(self):
        editor = self.require_editorial()
        before = after = count = 0
        for folder in sorted((ROOT / 'corpora/research-300/cases').glob('MM-*')):
            contract = json.loads((folder / 'contract.json').read_text())
            for name in contract['attachments']:
                if name.endswith('.json'):
                    source = (folder / name).read_text()
                    rendered = editor.render_structured(json.loads(source), contract['locale'], name)
                    self.assertEqual(editor.parse_structured(rendered), json.loads(source), f'{folder.name}/{name}')
                    before += len(source)
                    after += len(rendered)
                    count += 1
        self.assertGreater(count, 100)
        self.assertLess(after, before * .8)

    def test_simple_and_cad_prompts_shrink_without_inventing_supplied_modalities(self):
        editor = self.require_editorial()
        for case_id in ['MM-001', 'MM-002', 'MM-056', 'MM-059', 'MM-075', 'MM-096']:
            contract, row, files = editor.read_case(ROOT, case_id)
            bundle, content, _ = editor.build_case(contract, row, files)
            initial = bundle['turns'][0]['instruction']
            self.assertLess(len(initial), len(contract['turns'][0]['instruction']), case_id)
            if case_id == 'MM-001':
                self.assertNotIn('DXF', initial)
                self.assertLess(len(initial) + sum(map(len, content.values())),
                                len(contract['turns'][0]['instruction']) + len(files['properties.txt'].decode()))
            if case_id == 'MM-056':
                self.assertIn('input.dxf', initial)
                packet = initial + ''.join(content.values())
                for fact in ['S-*', 'A-*', 'dxfMapping', 'boundaryConditions', 'LINE', 'section']:
                    self.assertIn(fact, packet)
                self.assertNotIn('[case-D-D.', initial)
            self.assertFalse(any(a['path'].startswith('analysis-notes-') for a in bundle['turns'][0]['attachments']))

    def test_original_public_clarification_and_extra_tail_survive_visible_prompt(self):
        editor = self.require_editorial()
        for case_id, public_clause in [
            ('MM-058', 'Ask a targeted clarification about the two column-base restraints.'),
            ('MM-072', 'Reconstruct the available information and identify the missing essential datum.'),
        ]:
            contract, row, files = editor.read_case(ROOT, case_id)
            bundle, _, _ = editor.build_case(contract, row, files)
            first = bundle['turns'][0]['instruction']
            self.assertIn(public_clause, first, case_id)
            self.assertNotIn('0.5 m', first)
            self.assertNotIn('both column bases are fixed', first)
        contract, row, files = editor.read_case(ROOT, 'MM-001')
        public_exception = 'Keep the supplied named section groups separate in the model figure.'
        contract['turns'][0]['instruction'] += '\n\n' + public_exception
        bundle, _, _ = editor.build_case(contract, row, files)
        self.assertIn(public_exception, bundle['turns'][0]['instruction'])

    def test_checker_rejects_changed_public_fact_even_when_file_hashes_are_rebound(self):
        editor = self.require_editorial()
        source_root = ROOT / 'corpora/research-300'
        manifest = json.loads((source_root / 'manifest.json').read_text())
        row = next(r for r in manifest['cases'] if r['id'] == 'MM-001')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            case = root / 'corpora/research-300/cases/MM-001'
            case.mkdir(parents=True)
            source = source_root / 'cases/MM-001'
            contract = json.loads((source / 'contract.json').read_text())
            for name in ['contract.json'] + contract['attachments']:
                (case / name).write_bytes((source / name).read_bytes())
            (root / 'corpora/research-300/manifest.json').write_text(json.dumps({'cases': [row]}))
            editor.generate(root, ['MM-001'], inventory=False)
            edition = root / 'corpora/research-300/public-inputs/concise-v1/MM-001'
            append = edition / 'properties.md'
            append.write_text(append.read_text().replace('206000', '200000'))
            input_path = edition / 'input.json'
            payload = json.loads(input_path.read_text())
            descriptor = next(a for a in payload['turns'][0]['attachments'] if a['path'] == 'properties.md')
            descriptor['sha256'] = editor.digest(append.read_bytes())
            input_path.write_text(json.dumps(payload))
            errors = editor.check_case(root, 'MM-001')
            self.assertTrue(any('properties.md' in error for error in errors), errors)


if __name__ == '__main__':
    unittest.main()
