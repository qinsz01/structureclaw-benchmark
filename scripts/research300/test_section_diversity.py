import json
from pathlib import Path
import shutil
import tempfile
import unittest

import section_diversity as d


class SectionDiversityTest(unittest.TestCase):
    def section(self):
        return {'id': 'B1', 'type': 'rectangular',
                'shape': {'kind': 'rectangular', 'B': 300, 'H': 600},
                'properties': {'A': .18, 'Iy': .0054, 'Iz': .00135, 'J': .003707859375}}

    def test_similarity_preserves_rectangle_axes_and_relative_stiffness(self):
        a = self.section()
        b = {**a, 'id': 'B2', 'shape': None,
             'properties': {**a['properties'], 'Iy': a['properties']['Iy'] * .6,
                            'Iz': a['properties']['Iz'] * .6}}
        x, y = [d.scale_section(s, 84) for s in (a, b)]
        self.assertEqual(x['shape'], {'kind': 'rectangular', 'B': 252, 'H': 504})
        self.assertAlmostEqual(x['properties']['A'], .252 * .504)
        self.assertAlmostEqual(x['properties']['Iy'], .252 * .504**3 / 12)
        self.assertAlmostEqual(x['properties']['Iz'], .504 * .252**3 / 12)
        self.assertAlmostEqual(x['properties']['Iy']/x['properties']['Iz'], 4)
        self.assertAlmostEqual(y['properties']['Iy']/x['properties']['Iy'], .6)
        self.assertEqual(y['properties']['A'], x['properties']['A'])

    def test_no_change_to_loads_geometry_materials_or_future_schedule(self):
        model = {'sections': [self.section()], 'nodes': [{'id': 'n1', 'x': 300}],
                 'elements': [{'id': 'b', 'section': 'B1'}],
                 'load_cases': [{'id': 'D', 'loads': [{'fz': -.18}]}]}
        transformed = d.scale_model(model, 120)
        self.assertEqual(transformed['nodes'], model['nodes'])
        self.assertEqual(transformed['load_cases'], model['load_cases'])
        d.audit_models([model], [transformed], 120)
        transformed['nodes'][0]['x'] = 360
        with self.assertRaisesRegex(ValueError, 'non-section'):
            d.audit_models([model], [transformed], 120)
        self.assertEqual(model['sections'][0]['properties']['A'], .18)

    def test_mixed_units_and_conflicting_public_data(self):
        section = self.section()
        section['properties'] = {k: v * (1e6 if k == 'A' else 1e12)
                                 for k, v in section['properties'].items()}
        section['properties']['Iy'] *= 2  # Deliberately unresolved public conflict.
        public = {'units': {'A': 'mm2', 'Iy': 'mm4'}, 'sections': [section],
                  'futureFile': 'section-t2.json', 'loads': [{'fz': -.18}]}
        got = d.transform_json(public, 80)
        self.assertEqual(got['units'], public['units'])
        self.assertEqual(got['futureFile'], public['futureFile'])
        self.assertEqual(got['loads'], public['loads'])
        self.assertAlmostEqual(got['sections'][0]['properties']['A'], 115200)
        self.assertEqual(got['sections'][0]['properties']['Iy'], 4423680000)
        d.check_public_tree(public, got, 80)
        got['loads'][0]['fz'] *= 2
        with self.assertRaisesRegex(ValueError, 'Non-section numeric'):
            d.check_public_tree(public, got, 80)

    def test_public_prose_and_top_level_arrays(self):
        text = 'B1: A=0.18, Iy=0.0054, Iz=0.00135, J=0.00370785937\nFx=300 kN; node x=600 m\n'
        got = d.transform_public('properties.txt', text.encode(), 80).decode()
        self.assertIn('A=0.1152', got)
        self.assertIn('J=0.0015187392', got)
        self.assertIn('Fx=300 kN; node x=600 m', got)
        array = [{'id': 'e1', 'section': 'B1', 'nodes': ['n1', 'n2']}]
        self.assertEqual(json.loads(d.transform_public('assignments.json', d.encoded(array), 80)), array)
        self.assertEqual(d.transform_prose('B=300; H=600', 80), 'B=240; H=480')
        self.assertEqual(d.transform_prose('C1/B1 = 350x500/250x450 mm', 80), 'C1/B1 = 280x400/200x360 mm')

    def test_reject_unreviewed_shapes_and_nonfinite_numbers(self):
        for invalid in (float('inf'), float('nan'), True, 0, -1):
            with self.assertRaises(ValueError):
                d.scale_number(invalid, 80, 2)
        section = self.section()
        section['shape']['tw'] = 10
        with self.assertRaisesRegex(ValueError, 'Unreviewed shape'):
            d.scale_section(section, 80)

    def test_dimensioned_prose_in_plain_and_unicode_units_is_scaled_once(self):
        old = '截面A=0.01m2；Iy=0.001 m⁴; J=100 mm^4; Asy=20mm²\nB1: A=0.01 m^2, Iz=0.002m4\nFx=20 kN; x=4 m'
        got = d.transform_prose(old, 80)
        self.assertEqual(got, '截面A=0.0064m2；Iy=0.0004096 m⁴; J=40.96 mm^4; Asy=12.8mm²\nB1: A=0.0064 m^2, Iz=0.0008192m4\nFx=20 kN; x=4 m')
        self.assertEqual(d.audit_prose_properties(old, got, 80), 6)
        with self.assertRaisesRegex(ValueError, 'Unscaled or inconsistent'):
            d.audit_prose_properties(old, got.replace('0.0064m2', '0.01m2'), 80)
        with self.assertRaisesRegex(ValueError, 'Wrong dimension'):
            d.transform_prose('A=0.01m4', 80)

    def test_physical_similarity_against_analytic_axial_and_torsion_responses(self):
        # Genuine native execution; a missing runtime must fail this verification.
        import opensees_native as native
        from test_reference_native import model, loaded, node
        original = model(length=3, three_d=True)
        original['sections'] = [self.section()]
        original['elements'][0]['section'] = 'B1'
        loaded(original, type='nodal', node='b', fx=20, mx=5)
        for percent in (80, 120):
            changed = d.scale_model(original, percent)
            calculate, checks, _ = native.solve(changed, {'D': 1})
            section = changed['sections'][0]['properties']
            material = changed['materials'][0]
            self.assertAlmostEqual(calculate(node('b'), 'ux'), 20 * 3 / (material['E'] * 1000 * section['A']), places=12)
            self.assertAlmostEqual(calculate(node('b'), 'rx'), 5 * 3 / (material['G'] * 1000 * section['J']), places=12)
            self.assertTrue(checks['equilibriumPassed'])

    def test_english_area_and_shared_unit_square_prose_remains_consistent(self):
        old='A1 is a 0.10 by 0.10 m solid square. A1 area is 0.01 m2; AD area is 0.015 m2. Span 4 by 3 m.'
        got=d.transform_prose(old,84)
        self.assertEqual(got,'A1 is a 0.084 by 0.084 m solid square. A1 area is 0.007056 m2; AD area is 0.010584 m2. Span 4 by 3 m.')
        self.assertEqual(d.audit_prose_properties(old,got,84),4)
        for stale in [got.replace('0.007056','0.01'),got.replace('0.084 by','0.10 by')]:
            with self.assertRaisesRegex(ValueError,'Unscaled or inconsistent'):
                d.audit_prose_properties(old,stale,84)

    def test_case_counts_ignore_unused_sections_and_repeated_states(self):
        a = self.section()
        b = d.scale_section(a, 80); b['id'] = 'unused'
        model = {'sections': [a, b], 'elements': [{'section': 'B1'}]}
        row = {'caseId': 'MM-003', 'family': 'MM', 'engine': 'OpenSees'}
        got = d.inventory([(row, [model, model])])['all']
        self.assertEqual(got['distinctJ'], 1)
        self.assertEqual(got['maxJCases'], 1)

    def test_all_reviewed_dimensional_prose_forms_and_stale_negative_controls(self):
        examples = [
            ('截面A1为0.10×0.10 m实心方形', '截面A1为0.08×0.08 m实心方形'),
            ('400 by 500 mm rectangular sections', '320 by 400 mm rectangular sections'),
            ('C-middle = 0.60 m square', 'C-middle = 0.48 m square'),
            ('columns C1 are 0.50 m square', 'columns C1 are 0.4 m square'),
            ('屋面B1宽0.30m高0.60m，连系梁T1宽0.25m高0.40m，柱C1为0.50m方形',
             '屋面B1宽0.24m高0.48m，连系梁T1宽0.2m高0.32m，柱C1为0.4m方形'),
            ('斜撑A_BRACE=100×100mm（轴向面积0.01m²）', '斜撑A_BRACE=80×80mm（轴向面积0.0064m²）'),
        ]
        for old, expected in examples:
            with self.subTest(old=old):
                self.assertEqual(d.transform_prose(old,80), expected)
                self.assertGreater(d.audit_prose_properties(old,expected,80),0)
                with self.assertRaisesRegex(ValueError,'Unscaled or inconsistent'):
                    d.audit_prose_properties(old,old,80)
        geometry='2×2跨；8000 mm long; Span 4 by 3 m; 受荷宽6m；z=2.25m是连接高度；跨度15m、高2.5m；跨6m高4.5m'
        self.assertEqual(d.transform_prose(geometry,80),geometry)

    def test_public_turn_dimensions_change_without_changing_release_or_query(self):
        c={'id':'STD-093','turns':[{'id':'t1','instruction':'柱C1=400×500mm，Fx=20kN；斜撑轴向面积0.01m²',
            'state':1,'attachments':['properties.json']}], 'requiredOutputs':[{'id':'force','tolerance':1e-8}]}
        result=d.transform_contract(c,80)
        self.assertEqual(result['turns'][0]['instruction'],'柱C1=320×400mm，Fx=20kN；斜撑轴向面积0.0064m²')
        self.assertEqual(result['turns'][0]['attachments'],c['turns'][0]['attachments'])
        self.assertEqual(result['requiredOutputs'],c['requiredOutputs'])
        self.assertEqual(d.transform_contract(c,100),c)

    def test_numbered_area_groups_scale_quadratically_without_changing_geometry_ids(self):
        original='上弦A1=0.012 m²，下弦A2=0.010 m²，腹杆A3=0.006 m²。A1节点x=20 m；高3 m。'
        scaled=d.transform_prose(original,116)
        self.assertEqual(scaled,'上弦A1=0.0161472 m²，下弦A2=0.013456 m²，腹杆A3=0.0080736 m²。A1节点x=20 m；高3 m。')
        self.assertEqual(d.audit_prose_properties(original,scaled,116),3)
        with self.assertRaisesRegex(ValueError,'Unscaled or inconsistent'):
            d.audit_prose_properties(original,scaled.replace('0.0080736','0.006'),116)

    def test_committed_plan_covers_source_constraints_and_balances_engines(self):
        plan = d.read(d.ROOT/'planning/section-diversity-v1-r2.json')
        audit = d.audit_plan(d.ROOT, plan)
        self.assertEqual(len(plan['cases']), 300)
        for row in plan['cases']:
            if row['caseId'] in d.FIXED or row['caseId'] in d.SOURCE_CONSTRAINT_CORRECTIONS:
                self.assertEqual(row['percent'], 100)
        for family in ('STD', 'INT', 'MM'):
            for engine in ('OpenSees', 'PKPM', 'YJK'):
                counts = {scale: sum(row['family'] == family and row['engine'] == engine and row['percent'] == scale
                                     for row in plan['cases']) for scale in d.PALETTE}
                self.assertLessEqual(max(counts.values()) - min(counts.values()), 2)
        self.assertLessEqual(audit['after']['all']['maxJFraction'], .15)
        self.assertLessEqual(audit['maximumDisplayRelativeError'], 5e-8)
        original=d.read(d.ROOT/'planning/section-diversity-v1.json')
        changed=[a['caseId'] for a,b in zip(original['cases'],plan['cases']) if a!=b]
        self.assertEqual(changed,['INT-070'])
        self.assertEqual(plan['sourceConstraintCorrection']['basePlanSha256'],d.sha(d.encoded(original)))

    def test_stale_canonical_bytes_cannot_inherit_a_frozen_source_binding(self):
        plan = d.read(d.ROOT/'planning/section-diversity-v1.json')
        row = next(r for r in plan['cases'] if r['caseId'] == 'MM-003')
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)/'MM-003'
            shutil.copytree(d.ROOT/'corpora/research-300/cases/MM-003', target)
            d.assert_base_source(target, row)
            model = d.read(target/'model-state-1.json')
            model['nodes'][0]['x'] += .1
            d.write(target/'model-state-1.json', model)
            with self.assertRaisesRegex(ValueError, 'source bytes differ'):
                d.assert_base_source(target, row)


if __name__ == '__main__':
    unittest.main()
