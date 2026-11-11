"""Closed-form/scale invariants for independent references; no SUT calls."""
from __future__ import annotations

import os
for _name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[_name] = '1'
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from references import reference, solve
from tasks import make_turns, original_specs, requested


def cantilever(rotation_angle=0., **loads):
    """Independent 4.5 m +X member; local y=+Y, z=+Z before roll.

    MPa moduli and m^4 inertias deliberately require the 1000 conversion to
    kN/m^2. Unequal Iy/Iz make a mistaken roll or bending axis observable.
    """
    return {
        'schema_version': '2.2.0', 'unit_system': 'SI',
        'coordinate_system': {'dimension': '3d', 'plane': None,
            'semantics': 'global-z-up', 'version': 1,
            'dof_order': ['ux', 'uy', 'uz', 'rx', 'ry', 'rz']},
        'nodes': [
            {'id': 'BASE', 'x': 0., 'y': 0., 'z': 0., 'restraints': [True]*6},
            {'id': 'TIP', 'x': 4.5, 'y': 0., 'z': 0., 'restraints': [False]*6}],
        'elements': [{'id': 'BEAM', 'type': 'beam', 'nodes': ['BASE', 'TIP'],
                      'material': 'STEEL', 'section': 'UNEQUAL', 'rotation_angle': rotation_angle}],
        'materials': [{'id': 'STEEL', 'type': 'steel', 'E': 206000.,
                       'G': 206000./2.6, 'nu': .3, 'rho': 7850.}],
        'sections': [{'id': 'UNEQUAL', 'type': 'custom',
                      'properties': {'A': .12, 'Iy': .0036, 'Iz': .0004, 'J': .0007}}],
        'load_cases': [{'id': 'D', 'type': 'dead',
                        'loads': [{'type': 'nodal', 'node': 'TIP', **loads}]}],
        'load_combinations': [],
        'analysis_control': {k: False for k in ('self_weight', 'rigid_floor', 'p_delta',
                                               'rigid_offsets', 'construction_stage')},
        'metadata': {'elementReferenceVectors': {'BEAM': [0., 0., 1.]}}}


class ReferenceMechanicsRegressions(unittest.TestCase):
    def test_spatial_torsion_twist_reaction_and_public_torque_unit(self):
        length, shear_modulus, torsion_constant = 4.5, 206000./2.6, .0007
        for roll in (0., 90.):
            for moment in (-7.25, 7.25):
                with self.subTest(roll=roll, moment=moment):
                    model = cantilever(roll, mx=moment)
                    selection = {'kind': 'case', 'id': 'D'}
                    requests = requested(model, [selection])
                    requests.extend([
                        {'id': 'tip-twist', 'selection': selection,
                         'location': {'kind': 'node', 'id': 'TIP'}, 'component': 'rx', 'unit': 'rad'},
                        {'id': 'base-torque', 'selection': selection,
                         'location': {'kind': 'node', 'id': 'BASE'}, 'component': 'Mx', 'unit': 'kN.m'}])
                    truth = reference({'kind': 'static', 'model': model, 'requests': requests})
                    values = {q['id']: q['value'] for q in truth['requests']}
                    expected = moment*length/(1000*shear_modulus*torsion_constant)
                    self.assertAlmostEqual(values['tip-twist'], expected, delta=abs(expected)*1e-11)
                    self.assertAlmostEqual(values['base-torque'], -moment, delta=1e-10)
                    torque = [q for q in truth['requests'] if q['component'] == 'T']
                    self.assertEqual(len(torque), 1)
                    self.assertEqual(torque[0]['unit'], 'kN.m')
                    self.assertAlmostEqual(torque[0]['value'], moment, delta=1e-10)
                    self.assertLess(max(map(abs, truth['referenceChecks'][0]['forceMomentBalance'])), 1e-10)

    def test_ninety_degree_roll_swaps_bending_flexibility_and_local_moment_axis(self):
        length, force, elastic_modulus = 4.5, -10., 206000.
        base = {'kind': 'node', 'id': 'BASE'}
        tip = {'kind': 'node', 'id': 'TIP'}
        root_cut = {'kind': 'member', 'id': 'BEAM', 'positionM': 0., 'side': 'right'}
        displacements = []
        for roll, inertia, m2, m3 in [(0., .0036, -force*length, 0.),
                                      (90., .0004, 0., force*length)]:
            with self.subTest(roll=roll):
                model = cantilever(roll, fz=force)
                ((value, check),) = solve(model, [{'kind': 'case', 'id': 'D'}],
                                          [{'location': root_cut}])
                expected = force*length**3/(3*1000*elastic_modulus*inertia)
                uz = value(tip, 'uz'); displacements.append(uz)
                self.assertAlmostEqual(uz, expected, delta=abs(expected)*1e-10)
                self.assertAlmostEqual(value(tip, 'uy'), 0., delta=1e-12)
                self.assertAlmostEqual(value(base, 'Fz'), -force, delta=1e-10)
                self.assertAlmostEqual(value(base, 'My'), force*length, delta=1e-10)
                self.assertAlmostEqual(value(root_cut, 'M2'), m2, delta=1e-10)
                self.assertAlmostEqual(value(root_cut, 'M3'), m3, delta=1e-10)
                self.assertAlmostEqual(value(root_cut, 'T'), 0., delta=1e-12)
                self.assertLess(max(map(abs, check['forceMomentBalance'])), 1e-10)
        self.assertAlmostEqual(displacements[1]/displacements[0], 9., delta=1e-10)

    def test_representative_modal_mass_changes_scale_periods_not_stiffness(self):
        originals = original_specs()
        # Two representative actual interactive tasks, rather than repeating
        # the existing full 30-model dynamic authoring audit.
        for family in ('frame', 'mixed'):
            case = next(c for c in originals if c['family'] == 'INT'
                        and c['modelFamily'] == family and c.get('analysis') == 'modal')
            with self.subTest(family=family, variant=case['variant']):
                first, second = [reference(t) for t in make_turns(case)[:2]]
                before = {q['id']: q for q in first['requests']}
                after = {q['id']: q for q in second['requests']}
                self.assertEqual(before.keys(), after.keys())
                scales = {'period': math.sqrt(1.2), 'frequency': 1/math.sqrt(1.2),
                          'effectiveMass': 1.2}
                for key, q in before.items():
                    factor = scales[q['path'][-1]]
                    self.assertAlmostEqual(after[key]['value'], factor*q['value'],
                                           delta=1e-9*max(1., abs(q['value'])))
                for truth in (first, second):
                    check = truth['referenceChecks'][0]
                    self.assertAlmostEqual(check['effectiveMassSum'], check['totalMass'], delta=1e-8)


if __name__ == '__main__':
    unittest.main()
