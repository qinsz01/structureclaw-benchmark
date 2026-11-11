"""Regressions for observed task blind spots, using independent mechanics only.

These checks do not qualify a SUT. Twelve cases previously requested only zero
translations; the separate simply supported beam is an analytic counterexample.
"""
from __future__ import annotations

import os
for _name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[_name] = '1'
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from models import _member, _model, _node
from references import reference
from tasks import make_turns, original_specs, requested


class TaskMechanicsRegressions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.originals = original_specs()

    def test_twelve_historical_zero_observation_cases_measure_deformation(self):
        # Original factory identities, including the later release/settlement
        # substitutions. These are the twelve actual pre-fix failures.
        historical = [
            ('MM', 1), ('INT', 2), ('INT', 14), ('STD', 18),
            ('MM', 22), ('INT', 26), ('INT', 29), ('STD', 30),
            ('MM', 31), ('INT', 32), ('STD', 33), ('MM', 34),
        ]
        for family, variant in historical:
            with self.subTest(family=family, variant=variant):
                case = next(c for c in self.originals if c['family'] == family
                            and c['modelFamily'] == 'beam' and c['variant'] == variant)
                turn = make_turns(case)[0]
                truth = reference(turn)
                measured = [q['value'] for q in truth['requests']
                            if q['selection'] == {'kind': 'case', 'id': 'D'}
                            and q['component'] in ('ux', 'uy', 'uz')]
                self.assertTrue(measured)
                self.assertGreater(max(map(abs, measured)), 1e-8,
                                   'A deformed model must not be scored only at zero-response stations')
                # A prescribed support movement is a displacement result too;
                # restricting all observations to free DOFs hides this input.
                for lc in turn['model']['load_cases']:
                    if lc['id'] != 'D':
                        continue
                    for load in lc['loads']:
                        if load.get('type') != 'displacement' or not load.get('uz'):
                            continue
                        observed = [q['value'] for q in truth['requests']
                                    if q['selection'] == {'kind': 'case', 'id': 'D'}
                                    and q['location'] == {'kind': 'node', 'id': load['node']}
                                    and q['component'] == 'uz']
                        self.assertEqual(len(observed), 1)
                        self.assertAlmostEqual(observed[0], load['uz'], delta=1e-12)

    def test_roller_beam_requests_actual_midspan_deflection(self):
        # A roller is free in ux but fixed in uz. Selecting it as the vertical
        # observation used to report zero, despite this nonzero exact solution.
        model = _model('2d')
        length, load = 8., -12.
        _node(model, 'PIN', 0., 0., support='P')
        _node(model, 'MID', length/2, 0.)
        _node(model, 'ROLLER', length, 0., support='R')
        _member(model, 'LEFT', 'PIN', 'MID')
        _member(model, 'RIGHT', 'MID', 'ROLLER')
        model['load_cases'][0]['loads'] = [
            {'type': 'nodal', 'node': 'MID', 'fz': load}]
        selection = {'kind': 'case', 'id': 'D'}
        truth = reference({'kind': 'static', 'model': model,
                           'requests': requested(model, [selection])})
        observed = [q for q in truth['requests'] if q['component'] == 'uz'
                    and q['location'] == {'kind': 'node', 'id': 'MID'}]
        self.assertEqual(len(observed), 1)
        e = model['materials'][0]['E']
        iy = model['sections'][0]['properties']['Iy']
        expected = load*length**3/(48*1000*e*iy)
        self.assertAlmostEqual(observed[0]['value'], expected, delta=abs(expected)*1e-10)
        self.assertGreater(abs(expected), 1e-5)

    def test_all_fifteen_original_l1_interactions_change_actual_d_response(self):
        cases = [c for c in self.originals if c['family'] == 'INT' and c['level'] == 'L1']
        self.assertEqual(len(cases), 15)
        for case in cases:
            with self.subTest(model=case['modelFamily'], variant=case['variant']):
                initial, changed = (reference(t) for t in make_turns(case))
                before = {q['id']: q for q in initial['requests']}
                after = {q['id']: q for q in changed['requests']}
                self.assertEqual(before.keys(), after.keys())
                changed_translations = []
                for key, q in before.items():
                    # This is a linear-response invariant, rather than an
                    # assertion that a change-order field has a certain value.
                    self.assertAlmostEqual(after[key]['value'], 1.2*q['value'],
                                           delta=1e-10*max(1., abs(q['value'])))
                    if q['component'] in ('ux', 'uy', 'uz'):
                        changed_translations.append(abs(after[key]['value']-q['value']))
                self.assertGreater(max(changed_translations), 1e-10,
                                   'An unchanged D response cannot test stateful load modification')


if __name__ == '__main__':
    unittest.main()
