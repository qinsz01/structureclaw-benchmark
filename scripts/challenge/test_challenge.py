"""Source sufficiency and state-transition checks for the authored pilot."""
import copy
import csv
import hashlib
import json
import os
from pathlib import Path
import sys
import unittest

for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
ROOT = Path(__file__).resolve().parents[2]
EDITION = ROOT / 'corpora/challenge-6-v1'
sys.path.insert(0, str(ROOT / 'scripts/research300'))
from reference_solver import solve
from reference_io import selection_factors


def hidden(cid, turn):
    return json.loads((EDITION / 'cases' / cid / 'private' / f't{turn}.json').read_text())


class ChallengeSourceTests(unittest.TestCase):
    def test_all_authored_bytes_are_sealed_and_no_candidate_score_is_invented(self):
        m = json.loads((EDITION / 'manifest.json').read_text())
        self.assertEqual(len(m['cases']), 6)
        self.assertEqual(sum(len(c['turns']) for c in m['cases']), 18)
        self.assertEqual(m['candidateRuns'], 0)
        self.assertEqual(m['status'], 'candidate-pilot-not-difficulty-calibrated')
        for row in m['files']:
            blob = (EDITION / row['path']).read_bytes()
            self.assertEqual(len(blob), row['bytes'])
            self.assertEqual(hashlib.sha256(blob).hexdigest(), row['sha256'])

    def test_public_schedules_reproduce_initial_models_after_issued_revision(self):
        for cid in ('CH-001', 'CH-002', 'CH-004'):
            public = EDITION / 'cases' / cid / 'public/t1'
            model = hidden(cid, 1)['model']
            def rows(name):
                with (public / name).open() as handle:
                    return list(csv.DictReader(handle))
            nodes = {r['node']: r for r in rows('geometry.csv')}
            for n in model['nodes']:
                for axis in 'xyz':
                    self.assertAlmostEqual(float(nodes[n['id']][axis.upper()+'_mm'])/1000, n[axis])
                self.assertEqual([nodes[n['id']][d+'_fixed'] == '1' for d in ('ux','uy','uz','rx','ry','rz')], n['restraints'])
            members = {r['member']: r for r in rows('members.csv')}
            if cid == 'CH-004':
                self.assertEqual(members['X1-0-2']['section'], 'B1')
                self.assertIn('use B2', (public / 'issued-revision.md').read_text())
                members['X1-0-2']['section'] = 'B2'
            for e in model['elements']:
                row = members[e['id']]
                self.assertEqual([row['start_node'], row['end_node']], e['nodes'])
                self.assertEqual(row['element_type'], e['type'])
                self.assertEqual(row['section'], e['section'])
                self.assertEqual(row['material'], e['material'])
                self.assertEqual(float(row['roll_deg']), e['rotation_angle'])
            sections = {r['section']: r for r in rows('sections.csv')}
            for s in model['sections']:
                self.assertAlmostEqual(float(sections[s['id']]['A_mm2'])/1e6, s['properties']['A'])
                for p in ('Iy', 'Iz', 'J'):
                    self.assertAlmostEqual(float(sections[s['id']][p+'_mm4'])/1e12, s['properties'][p])

    def test_raster_geometry_has_no_parallel_machine_readable_geometry(self):
        public = EDITION / 'cases/CH-003/public/t1'
        self.assertTrue((public / 'geometry.png').exists())
        self.assertFalse((public / 'geometry.csv').exists())
        self.assertFalse(any(public.glob('*.svg')))
        from PIL import Image
        with Image.open(public / 'geometry.png') as image:
            self.assertEqual(image.info, {})
            self.assertEqual(image.size, (1800, 1300))

    def test_undo_preserves_later_material_and_global_force(self):
        a, z = hidden('CH-001', 1)['model'], hidden('CH-001', 6)['model']
        self.assertEqual(z['elements'][0]['rotation_angle'], a['elements'][0]['rotation_angle'])
        self.assertEqual(z['elements'][0]['material'], 'M2')
        self.assertEqual(z['load_cases'][1], a['load_cases'][1])
        self.assertEqual(z['load_cases'][2]['loads'][0]['fz'], 4.)
        self.assertEqual(z['load_cases'][2]['loads'][0]['fx'], a['load_cases'][2]['loads'][0]['fx'])

    def test_query_changes_units_without_changing_the_physical_model(self):
        before, query = hidden('CH-002', 3), hidden('CH-002', 4)
        self.assertEqual(query['kind'], 'query')
        self.assertEqual(before['model'], query['model'])
        self.assertEqual({q['unit'] for q in query['requests'] if q['component'].startswith('u')}, {'mm'})
        last = hidden('CH-002', 6)['model']
        self.assertEqual(last['load_cases'][1]['loads'][-1]['fz'], -19.)
        self.assertEqual(last['load_cases'][1]['loads'][-1]['position'], 1.925)
        interval = next(l for l in last['load_cases'][0]['loads'] if l['element'] == 'X1-0-2')
        self.assertEqual((interval['start'], interval['end']), (.44, 3.96))

    def test_clarifications_concern_physics_not_optional_metadata(self):
        for cid in ('CH-005', 'CH-006'):
            self.assertEqual(hidden(cid, 1)['kind'], 'clarify')
            determined = hidden(cid, 2)
            model = copy.deepcopy(determined['model'])
            if cid == 'CH-005':
                next(n for n in model['nodes'] if n['id'] == 'N4-0-0')['restraints'][0] = False
            else:
                model['elements'][0]['rotation_angle'] = 0.
            q = next(q for q in determined['requests'] if q['component'] == 'ux')
            calc, _ = solve(model, selection_factors(model, q['selection']), [q['location']])
            difference = abs(calc(q['location'], q['component']) - q['value'])
            self.assertGreater(difference, q['tolerance']['absolute'] + q['tolerance']['relative']*abs(q['value']), cid)


if __name__ == '__main__':
    unittest.main()
