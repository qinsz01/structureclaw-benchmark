"""Public visual edition regressions: missing facts, release leakage and rebound rasters."""
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
MODULE = Path(__file__).with_name('public_input_visual.py')


class VisualInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if MODULE.exists():
            spec = importlib.util.spec_from_file_location('public_input_visual', MODULE)
            cls.visual = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cls.visual)

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

    def require_visual(self):
        self.assertTrue(MODULE.exists(), 'Public-only visual builder is not implemented')
        return self.visual

    def test_implicit_analysis_policy_is_explicit_without_changing_frozen_sources(self):
        v = self.require_visual()
        for case_id, phrase in [('MM-001', '不考虑施工阶段'), ('MM-010', 'construction stages')]:
            c, row, public = v.read_case(ROOT, case_id)
            before = copy.deepcopy(public)
            bundle, _, audit = v.build_case(c, row, public)
            self.assertIn(phrase, bundle['turns'][0]['instruction'])
            self.assertEqual(audit['analysisPolicyClarifications'], ['construction_stage=false'])
            self.assertEqual(public, before)

    def test_multiview_instruction_does_not_repeat_the_attachment_inventory(self):
        v = self.require_visual()
        c, row, public = v.read_case(ROOT, 'MM-089')
        bundle, _, _ = v.build_case(c, row, public)
        instruction = bundle['turns'][0]['instruction']
        self.assertNotIn('阅读顺序：', instruction)
        self.assertNotIn('Reading order:', instruction)
        self.assertLessEqual(instruction.count('.png'), 1)

    def test_drawing_facts_are_once_in_legend_and_arrows_keep_ids(self):
        v = self.require_visual()
        contract, row, public = v.read_case(ROOT, 'MM-040')
        bundle, files, audit = v.build_case(contract, row, public)
        delivered = bundle['turns'][0]['attachments']
        self.assertFalse(any(a['name'].endswith('.svg') for a in delivered))
        legends = [a['name'] for a in delivered if a['name'].startswith('diagram-legend')]
        self.assertEqual(legends, ['diagram-legend-t1.png'])
        svg_text = '\n'.join(raw.decode() for name, raw in files.items() if name.endswith('.svg'))
        self.assertEqual(svg_text.count('D/D-T: fz=-30'), 1)
        self.assertIn('S0: B0 -&gt; T / M1 / A1', svg_text)
        for name in ['view-xy.svg', 'view-xz.svg', 'view-yz.svg']:
            self.assertIn('D/D-T', files['authoring/' + name].decode())
        self.assertTrue(audit['publicFactAudit']['allSourceLabelsPreserved'])

    def test_small_beam_loses_blank_space_without_shrinking_labels(self):
        v = self.require_visual()
        c, row, public = v.read_case(ROOT, 'MM-001')
        _, files, _ = v.build_case(c, row, public)
        svg = ET.fromstring(files['authoring/input.svg'])
        self.assertLess(int(svg.get('height')), 650)
        sizes = [float(e.get('font-size')) for e in svg.iter() if e.get('font-size')]
        self.assertGreaterEqual(min(sizes), 20)
        self.assertIn('3', [e.text for e in svg.iter() if e.tag.endswith('text')])

    def test_section_shape_roll_axes_and_referenced_filename_are_preserved(self):
        v = self.require_visual()
        c, row, public = v.read_case(ROOT, 'MM-089')
        _, files, audit = v.build_case(c, row, public)
        section = files['authoring/section-details.svg'].decode()
        self.assertIn('properties.md', section)
        self.assertNotIn('properties.json', section)
        self.assertIn('before roll', section)
        self.assertTrue(audit['publicFactAudit']['allSourceLabelsPreserved'])
        sizes = [float(e.get('font-size')) for e in ET.fromstring(section).iter() if e.get('font-size')]
        self.assertGreaterEqual(min(sizes), 18)

    def test_view_axes_and_missing_dimension_warning_remain_on_their_view(self):
        v = self.require_visual()
        for case_id, name, expected in [
            ('MM-058', 'initial-elevation-XZ.svg', ['X [m]', 'Z [m]']),
            ('MM-089', 'drawing-plan-1-Z3.6.svg', ['X [m]', 'Y [m]']),
            ('MM-094', 'drawing-elevation-0-w-6.svg', ['u [m]', 'v [m]']),
            ('MM-072', 'initial-elevation-XZ.svg', ['Z [m]', 'SCHEMATIC / NOT TO SCALE: right-bay level offset = ?; do not measure pixels to infer it.']),
        ]:
            with self.subTest(case_id=case_id):
                c, row, public = v.read_case(ROOT, case_id)
                _, files, _ = v.build_case(c, row, public)
                labels = [e.text for e in ET.fromstring(files['authoring/'+name]) if e.tag.endswith('text')]
                for value in expected:
                    self.assertIn(value, labels)

    def test_legend_member_heading_precedes_member_rows_as_full_width_text(self):
        v = self.require_visual()
        c, row, public = v.read_case(ROOT, 'MM-001')
        _, files, _ = v.build_case(c, row, public)
        texts = [e for e in ET.fromstring(files['authoring/diagram-legend-t1.svg']) if e.tag.endswith('text')]
        heading = next(e for e in texts if '构件索引' in e.text)
        member = next(e for e in texts if e.text.startswith('b1:'))
        load = next(e for e in texts if 'wz=-20' in e.text)
        self.assertLess(float(load.get('y')), float(heading.get('y')))
        self.assertLess(float(heading.get('y')), float(member.get('y')))
        self.assertEqual(float(heading.get('x')), 28)

    def test_existing_ring_collage_is_split_without_losing_panel_local_aliases(self):
        v = self.require_visual()
        c, row, public = v.read_case(ROOT, 'MM-042')
        bundle, files, audit = v.build_case(c, row, public)
        self.assertLessEqual(max(p['width'] for p in audit['pages']), 1800)
        self.assertIn('view-xy-panel-4.png', {a['name'] for a in bundle['turns'][0]['attachments']})
        panel = files['authoring/view-xz-panel-2.svg'].decode()
        self.assertIn('Side V2 -&gt; V3', panel)
        self.assertIn('R0 = ring_0_2: L0V2 -&gt; L0V3 / A2', panel)
        self.assertNotIn('R0 = ring_0_1', panel)

    def test_pipe_style_load_callouts_keep_location_but_values_occur_once(self):
        v = self.require_visual()
        c, row, public = v.read_case(ROOT, 'MM-049')
        _, files, _ = v.build_case(c, row, public)
        pages = '\n'.join(raw.decode() for name, raw in files.items() if name.endswith('.svg'))
        self.assertEqual(pages.count('D/D-1 | roof1 | wz=-5 kN/m'), 1)
        self.assertIn('D/D-1 | roof1', files['authoring/view-xz.svg'].decode())

    def test_inventory_maps_every_released_file_and_counts_input_modalities(self):
        v = self.require_visual()
        c, row, public = v.read_case(ROOT, 'MM-058')
        _, _, audit = v.build_case(c, row, public)
        for turn, source in zip(audit['turns'], c['turns']):
            mapped = {n for entry in turn['pageMap'] for n in (entry['source'] if isinstance(entry['source'], list) else [entry['source']])}
            self.assertEqual(mapped, set(source['attachments']))
        self.assertEqual(audit['sourceModalities']['svg'], 3)
        self.assertEqual(audit['sourceModalities']['png'], 3)

    def test_hidden_fields_never_influence_public_packet_or_audit(self):
        v = self.require_visual()
        c, row, public = v.read_case(ROOT, 'MM-001')
        expected = v.build_case(c, row, public)
        poisoned = {k: copy.deepcopy(c[k]) for k in ['id', 'locale', 'plannedEngine', 'turns']}
        poisoned['sourcePlan'] = {'secret': 'HIDDEN_ANSWER'}
        poisoned['modelStates'] = [{'hidden': 'OTHER_ANSWER'}]
        self.assertEqual(v.build_case(poisoned, row, public), expected)

    def test_five_clarification_boundaries_keep_new_drawings_in_second_turn(self):
        v = self.require_visual()
        for case_id in ['MM-007', 'MM-021', 'MM-032', 'MM-058', 'MM-072']:
            c, row, public = v.read_case(ROOT, case_id)
            bundle, files, audit = v.build_case(c, row, public)
            self.assertEqual([t['id'] for t in bundle['turns']], ['t1', 't2'])
            first_names = {a['name'] for a in bundle['turns'][0]['attachments']}
            second_names = {a['name'] for a in bundle['turns'][1]['attachments']}
            for original in c['turns'][1]['attachments']:
                if original.endswith('.svg'):
                    self.assertNotIn(original.replace('.svg', '.png'), first_names)
                    self.assertIn(original.replace('.svg', '.png'), second_names)
            self.assertNotEqual(audit['turns'][0]['sourceNames'], audit['turns'][1]['sourceNames'])

    def fixture(self, case_id='MM-001'):
        v = self.require_visual()
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        c, row, public = v.read_case(ROOT, case_id)
        case = root / 'corpora/research-300/cases' / case_id
        case.mkdir(parents=True)
        (case / 'contract.json').write_text(json.dumps(c))
        for name, raw in public.items():
            (case / name).write_bytes(raw)
        (case.parent.parent / 'manifest.json').write_text(json.dumps({'cases': [row]}))
        v.generate(root, [case_id], inventory=False)
        return v, root, root / v.EDITION_REL / case_id

    def rebind(self, v, root, folder, attachment):
        p = folder / 'input.json'
        bundle = json.loads(p.read_text())
        for turn in bundle['turns']:
            for a in turn['attachments']:
                if a['path'] == attachment:
                    a['sha256'] = v.digest((folder / attachment).read_bytes())
        p.write_text(v.json_text(bundle))
        manifest_path = root / v.EDITION_REL / 'manifest.json'
        m = json.loads(manifest_path.read_text())
        m['cases'][0]['sha256'] = v.digest(p.read_bytes())
        manifest_path.write_text(v.json_text(m))

    def test_checker_accepts_generated_png_with_only_public_chunks(self):
        v, root, folder = self.fixture()
        self.assertEqual(v.check_case(root, 'MM-001'), [])
        raw = (folder / 'input.png').read_bytes()
        offset = 8
        chunks = []
        while offset < len(raw):
            n = int.from_bytes(raw[offset:offset+4], 'big')
            chunks.append(raw[offset+4:offset+8])
            offset += n + 12
        self.assertEqual(set(chunks), {b'IHDR', b'IDAT', b'IEND'})

    def test_checker_rejects_rebound_png_even_if_audit_is_rebound(self):
        v, root, folder = self.fixture()
        original = (folder / 'input.png').read_bytes()
        (folder / 'input.png').write_bytes(original[:-12] + b'changed')
        self.rebind(v, root, folder, 'input.png')
        audit = json.loads((folder / 'author-audit.json').read_text())
        audit['selfClaim'] = 'all correct'
        (folder / 'author-audit.json').write_text(json.dumps(audit))
        errors = v.check_case(root, 'MM-001')
        self.assertTrue(any('input.png' in e for e in errors), errors)

    def test_checker_rejects_deleted_dimension_force_and_section_labels(self):
        for case_id, name, old, new in [
            ('MM-001', 'authoring/input.svg', '>3<', '>4<'),
            ('MM-001', 'authoring/diagram-legend-t1.svg', 'wz=-20', 'wz=-2'),
            ('MM-089', 'authoring/section-details.svg', 'before roll', 'after roll'),
        ]:
            with self.subTest(case_id=case_id, fact=old):
                v, root, folder = self.fixture(case_id)
                p = folder / name
                original = p.read_text()
                self.assertIn(old, original)
                p.write_text(original.replace(old, new))
                errors = v.check_case(root, case_id)
                self.assertTrue(any(name in e for e in errors), errors)

    def test_checker_rejects_release_boundary_rebinding(self):
        v, root, folder = self.fixture('MM-007')
        p = folder / 'input.json'
        bundle = json.loads(p.read_text())
        bundle['turns'][0]['attachments'].extend(bundle['turns'][1]['attachments'])
        p.write_text(v.json_text(bundle))
        self.assertTrue(v.check_case(root, 'MM-007'))

    def test_checker_rejects_omitted_original_dxf_and_unlisted_files(self):
        v, root, folder = self.fixture('MM-082')
        p = folder / 'input.json'
        bundle = json.loads(p.read_text())
        bundle['turns'][0]['attachments'] = [a for a in bundle['turns'][0]['attachments'] if not a['name'].endswith('.dxf')]
        p.write_text(v.json_text(bundle))
        (folder / 'unlisted-answer.txt').write_text('not allowed')
        self.assertTrue(v.check_case(root, 'MM-082'))


if __name__ == '__main__':
    unittest.main()
