"""Clean public packets preserve physical facts and release boundaries."""
import copy
import functools
import importlib.util
import json
from pathlib import Path
import re
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
MODULE = Path(__file__).with_name('public_input_clean.py')


class CleanInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if MODULE.exists():
            spec = importlib.util.spec_from_file_location('public_input_clean', MODULE)
            cls.clean = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cls.clean)

    def require_clean(self):
        self.assertTrue(MODULE.exists(), 'Clean public-source generator is not implemented')
        return self.clean

    @functools.lru_cache(maxsize=None)
    def packet(self, case_id):
        v = self.require_clean()
        c, row, public = v.read_case(ROOT, case_id)
        return c, row, public, v.build_case(c, row, public)

    def test_std_input_is_one_readable_document_with_exact_public_values(self):
        c, row, public, (bundle, files, audit) = self.packet('STD-001')
        delivered = bundle['turns'][0]['attachments']
        self.assertEqual([a['name'] for a in delivered], ['input.md'])
        text = files['input.md'].decode()
        for name in c['turns'][0]['attachments']:
            data = json.loads(public[name])
            def leaves(value):
                if isinstance(value, dict):
                    return [x for child in value.values() for x in leaves(child)]
                if isinstance(value, list):
                    return [x for child in value for x in leaves(child)]
                return [json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value]
            for fact in leaves(data):
                self.assertIn(fact, text, (name, fact))
        self.assertIn('OpenSees', bundle['turns'][0]['instruction'])
        self.assertIn('V2/V3', text)
        self.assertIn('output', text.lower())
        self.assertNotRegex(text + bundle['turns'][0]['instruction'], r'(?i)hash|run[ -]?id|哈希|运行ID|author-audit')

    def test_interactive_query_and_correction_remain_in_their_own_turn(self):
        c, row, public, (bundle, files, audit) = self.packet('INT-010')
        self.assertEqual(len(bundle['turns']), 2)
        self.assertEqual(len(bundle['turns'][0]['attachments']), 1)
        self.assertEqual(bundle['turns'][1]['attachments'], [])
        self.assertIn('Resolve the conflicting case labels', bundle['turns'][0]['instruction'])
        self.assertNotIn('belongs only to L', files['input.md'].decode())
        self.assertIn('belongs only to L', bundle['turns'][1]['instruction'])

    def test_crane_scope_is_publicly_unresolved_without_releasing_the_next_answer(self):
        c, row, public, (bundle, files, audit) = self.packet('INT-056')
        instruction = bundle['turns'][1]['instruction']
        self.assertIn('20%', instruction)
        self.assertIn('not yet been decided', instruction)
        self.assertIn('both components or only the vertical component', instruction)
        self.assertIn('confirm the scope before', instruction)
        self.assertNotIn('117.6', instruction)
        self.assertEqual(bundle['turns'][1]['attachments'], [])
        self.assertNotIn('not yet been decided', bundle['turns'][0]['instruction'])
        self.assertIn('117.6', bundle['turns'][2]['instruction'])
        self.assertEqual(audit['turns'][1]['instructionClarification']['sourceInstruction'],
                         c['turns'][1]['instruction'])
        # A different public request must not inherit a case-ID-only override.
        changed = copy.deepcopy(c)
        changed['turns'][1]['instruction'] = 'Increase both crane components by 20%.'
        altered, _, _ = self.clean.build_case(changed, row, public)
        self.assertEqual(altered['turns'][1]['instruction'], changed['turns'][1]['instruction'])
        # No private expectation or future numerical state drives the amendment.
        changed = copy.deepcopy(c)
        changed['turns'][1].update(expectation='analyze', state=999, expectedQuestions=['private'])
        same, _, _ = self.clean.build_case(changed, row, public)
        self.assertEqual(same, bundle)

    def test_public_csv_is_rendered_as_an_input_table(self):
        v = self.require_clean()
        contract = {'id': 'STD-X', 'plannedEngine': 'OpenSees', 'turns': [
            {'id': 't1', 'instruction': 'Analyze the attached member.', 'attachments': ['geometry.csv']}]}
        bundle, files, _ = v.build_case(contract, {'sourceHash': 'source'},
                                      {'geometry.csv': b'id,x,y,z\nN0,0,0,0\nN1,6,0,0\n'})
        self.assertIn('|id|x|y|z|', files['input.md'].decode())
        self.assertIn('|N1|6|0|0|', files['input.md'].decode())

    def test_implicit_mm_stage_policy_and_specific_clarification_are_visible(self):
        _, _, _, (bundle, files, audit) = self.packet('MM-001')
        self.assertIn('不考虑施工阶段', files['authoring/drawing.svg'].decode())
        self.assertEqual(audit['analysisPolicyClarifications'], ['construction_stage=false'])
        _, _, _, (bundle, _, _) = self.packet('MM-058')
        self.assertIn('two column-base restraints', bundle['turns'][0]['instruction'])

    def test_mm_has_one_canonical_grouped_load_table_and_no_repeated_task_cards(self):
        _, _, _, (bundle, files, audit) = self.packet('MM-089')
        svg = files['authoring/drawing.svg'].decode()
        self.assertNotIn('Analysis and drawing instructions', svg)
        self.assertNotIn('Reporting conventions', svg)
        self.assertIn('D-x0-0-1 → x0-0-1', svg)
        self.assertLess(audit['turns'][0]['layout']['width'] * audit['turns'][0]['layout']['height'], 28_000_000)
        self.assertLessEqual(audit['turns'][0]['layout']['cards'], 18)
        self.assertGreater(len(audit['turns'][0]['canonicalizedDrawingLabels']), 10)

    def test_execution_bookkeeping_is_cleaned_inside_structured_string_values(self):
        _, _, _, (bundle, files, _) = self.packet('INT-087')
        text = ''.join(t['instruction'] for t in bundle['turns'])
        text += ''.join(raw.decode() for name, raw in files.items() if name.endswith('.md'))
        self.assertNotRegex(text, r'(?i)run[ -]?id|运行ID|哈希|model hash')

    def test_followup_references_its_current_release_document(self):
        _, _, _, (bundle, _, _) = self.packet('INT-054')
        turn = bundle['turns'][1]
        self.assertEqual(turn['attachments'][0]['name'], 'input-t2.md')
        self.assertIn('input-t2.md', turn['instruction'])
        _, _, _, (bundle, files, _) = self.packet('INT-091')
        self.assertIn('input.md', bundle['turns'][1]['instruction'])
        self.assertEqual(bundle['turns'][1]['attachments'], [])
        self.assertNotIn('regions.json', bundle['turns'][1]['instruction'])
        _, _, _, (_, files, _) = self.packet('STD-001')
        self.assertNotIn('output-requests.json', files['input.md'].decode())

    def test_generator_rejects_case_folder_and_file_symlinks_before_any_write(self):
        v = self.require_clean()
        c, row, public, _ = self.packet('STD-001')
        for link_kind in ['directory', 'file']:
            with self.subTest(link_kind=link_kind), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                source = root / 'corpora/research-300/cases/STD-001'
                source.mkdir(parents=True)
                (source / 'contract.json').write_text(json.dumps(c))
                for name, raw in public.items():
                    (source / name).write_bytes(raw)
                (source.parent.parent / 'manifest.json').write_text(json.dumps({'cases': [row]}))
                outside = root / 'unowned'
                outside.mkdir()
                keep = outside / 'keep.txt'
                keep.write_text('keep')
                edition = root / v.EDITION_REL
                edition.mkdir(parents=True)
                if link_kind == 'directory':
                    (edition / 'STD-001').symlink_to(outside, target_is_directory=True)
                else:
                    (edition / 'STD-001').mkdir()
                    (edition / 'STD-001/input.md').symlink_to(keep)
                with self.assertRaisesRegex(ValueError, '[Ss]ymlink'):
                    v.generate(root)
                self.assertEqual(keep.read_text(), 'keep')
                self.assertFalse((edition / 'manifest.json').exists())

    def test_mm_sheet_has_one_attachment_and_all_public_labels_and_facts(self):
        v = self.require_clean()
        c, row, public, (bundle, files, audit) = self.packet('MM-040')
        self.assertEqual([a['name'] for a in bundle['turns'][0]['attachments']], ['drawing.png'])
        self.assertEqual(files['drawing.png'][:8], b'\x89PNG\r\n\x1a\n')
        svg = ET.fromstring(files['authoring/drawing.svg'])
        visible = re.sub(r'\s+', '', ''.join(''.join(n.itertext()) for n in svg.iter() if n.tag.endswith('text')))
        for name, raw in public.items():
            if name.endswith('.svg'):
                for node in ET.fromstring(raw).iter():
                    if node.tag.endswith('text'):
                        fact = v.drawing_references(''.join(node.itertext()))
                        self.assertIn(re.sub(r'\s+', '', fact), visible)
        self.assertGreaterEqual(audit['turns'][0]['layout']['columns'], 2)
        self.assertTrue(audit['turns'][0]['allPublicDrawingLabelsPreserved'])

    def test_multiview_sheet_is_legible_without_one_column_stitching(self):
        _, _, _, (bundle, files, audit) = self.packet('MM-089')
        layout = audit['turns'][0]['layout']
        self.assertGreaterEqual(layout['columns'], 3)
        self.assertLessEqual(layout['width'] * layout['height'], 32_000_000)
        self.assertGreaterEqual(layout['minimumFontPixels'], 18)
        self.assertEqual(len(bundle['turns'][0]['attachments']), 1)
        self.assertIn('before roll', files['authoring/drawing.svg'].decode())
        instruction = bundle['turns'][0]['instruction']
        self.assertIn('PKPM', instruction)
        self.assertIn('n3-2-2', instruction)
        self.assertNotIn('properties.json', instruction)

    def test_dxf_keeps_original_entities_and_adds_section_geometry_and_notes(self):
        _, _, public, (bundle, files, audit) = self.packet('MM-082')
        self.assertEqual([a['name'] for a in bundle['turns'][0]['attachments']], ['drawing.dxf'])
        original = public['input.dxf'].decode()
        result = files['drawing.dxf'].decode()
        source_entities = original.split('2\nENTITIES\n', 1)[1].rsplit('0\nENDSEC', 1)[0]
        self.assertIn(source_entities, result)
        self.assertIn('A-CLEAN-SECTION', result)
        self.assertIn('A-CLEAN-NOTES', result)
        self.assertIn('Asy', result)
        self.assertIn('before roll', result)
        self.assertIn('G', result)
        self.assertTrue(audit['turns'][0]['originalDXFEntitiesPreserved'])

    def test_r12_dxf_annotations_use_ascii_unicode_escapes_and_bounded_text(self):
        v = self.require_clean()
        _, _, _, (_, files, _) = self.packet('MM-081')
        raw = files['drawing.dxf']
        self.assertTrue(raw.isascii())
        self.assertIn(b'\\U+', raw)
        texts = [value for code, value in v.dxf_pairs(raw) if code == 1]
        self.assertTrue(all(len(value.encode('ascii')) <= 255 for value in texts))
        decoded = '\n'.join(v.decode_dxf_text(text) for text in texts)
        self.assertIn('截面', decoded)

    def test_early_dxf_uses_its_original_structure_layer_conventions(self):
        v = self.require_clean()
        _, _, public, (_, files, _) = self.packet('MM-008')
        self.assertIn(b'\nSTRUCTURE\n', public['input.dxf'])
        text = ''.join(v.decode_dxf_text(value) for code, value in v.dxf_pairs(files['drawing.dxf']) if code == 1)
        compact = re.sub(r'\s+', '', text)
        self.assertNotIn('UsetheoriginalS-*', compact)
        self.assertIn('originallayerconventions', compact)

    def test_ambiguous_mm_drawing_is_not_resolved_until_public_correction(self):
        for case_id in ['MM-007', 'MM-021', 'MM-032', 'MM-058', 'MM-072']:
            with self.subTest(case_id=case_id):
                c, row, public, (bundle, files, audit) = self.packet(case_id)
                self.assertEqual([len(t['attachments']) for t in bundle['turns']], [1, 1])
                self.assertNotEqual(bundle['turns'][0]['attachments'][0]['path'], bundle['turns'][1]['attachments'][0]['path'])
                first = files['authoring/drawing.svg'].decode()
                self.assertNotIn(c['turns'][1]['instruction'], first)
                self.assertEqual(audit['turns'][0]['sourceNames'], c['turns'][0]['attachments'])
                self.assertEqual(audit['turns'][1]['sourceNames'], c['turns'][1]['attachments'])
        _, _, _, (_, files, _) = self.packet('MM-007')
        self.assertNotIn('fz=-15', files['authoring/drawing.svg'].decode())
        self.assertIn('fz=-15', files['authoring/drawing-t2.svg'].decode())

    def test_hidden_fields_do_not_influence_inputs_or_audit(self):
        v = self.require_clean()
        c, row, public, expected = self.packet('STD-001')
        poisoned = copy.deepcopy(c)
        poisoned.update(sourcePlan={'answer': 'SECRET'}, modelStates=[{'answer': 98765}], requiredOutputs=[{'answer': 45678}])
        for t in poisoned['turns']:
            t['expectedQuestions'] = ['SECRET_QUESTION']
            t['unresolvedFields'] = ['/hidden/answer']
        self.assertEqual(v.build_case(poisoned, row, public), expected)

    def test_checker_rejects_rebound_input_and_extra_delivered_file(self):
        v = self.require_clean()
        c, row, public, _ = self.packet('STD-001')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / 'corpora/research-300/cases/STD-001'
            folder.mkdir(parents=True)
            (folder / 'contract.json').write_text(json.dumps(c))
            for name, raw in public.items():
                (folder / name).write_bytes(raw)
            (folder.parent.parent / 'manifest.json').write_text(json.dumps({'cases': [row]}))
            v.generate(root)
            self.assertEqual(v.check_case(root, 'STD-001'), [])
            edition = root / v.EDITION_REL
            p = edition / 'STD-001/input.md'
            p.write_text(p.read_text().replace('206000', '206001'))
            packet = json.loads((edition / 'STD-001/input.json').read_text())
            packet['turns'][0]['attachments'][0]['sha256'] = v.digest(p.read_bytes())
            (edition / 'STD-001/input.json').write_text(v.json_text(packet))
            manifest = json.loads((edition / 'manifest.json').read_text())
            manifest['cases'][0]['sha256'] = v.digest((edition / 'STD-001/input.json').read_bytes())
            (edition / 'manifest.json').write_text(v.json_text(manifest))
            (edition / 'STD-001/answer.txt').write_text('extra')
            errors = v.check_case(root, 'STD-001')
            self.assertTrue(any('input.md' in e for e in errors), errors)
            self.assertTrue(any('answer.txt' in e for e in errors), errors)


if __name__ == '__main__':
    unittest.main()
