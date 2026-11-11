"""Mechanical positive/negative controls for the independent density witness."""
import math
import unittest

from .audit_project_q_density_v32 import compare, executed_density, issued_density


class DensityControls(unittest.TestCase):
    def model(self, loads):
        return {'unit_system': 'SI', 'analysis_control': {'self_weight': False},
                'nodes': [{'id': 'a', 'x': 0., 'y': 0., 'z': 0.}, {'id': 'b', 'x': 10., 'y': 0., 'z': 5.}],
                'elements': [{'id': 'bar', 'nodes': ['a', 'b']}],
                'load_cases': [{'id': 'renamed', 'loads': loads}], 'load_combinations': []}

    def test_inclined_member_and_uniform_subdivision_preserve_projected_load(self):
        length = math.hypot(10, 5)
        loads = [{'type': 'distributed', 'element': 'bar', 'wz': -20 / length, 'start': a, 'end': b}
                 for a, b in [(0., length / 3), (length / 3, length)]]
        actual = executed_density(self.model(loads), {'kind': 'case', 'id': 'renamed'})
        check = compare(actual, ([(0., 10., [0., 0., -2.])], {}))
        self.assertLess(check['worstDifference']['absoluteDifference'], 1e-12)
        self.assertAlmostEqual(check['actualForceResultantKN'][2], -20.)

    def test_equal_resultant_does_not_hide_wrong_density(self):
        actual = ([(0., 5., [0., 0., -1.]), (5., 10., [0., 0., -3.])], {})
        check = compare(actual, ([(0., 10., [0., 0., -2.])], {}))
        self.assertEqual(check['actualForceResultantKN'], check['issuedForceResultantKN'])
        self.assertGreater(check['worstDifference']['ratioToConservativeThreshold'], 1)

    def test_revision_keeps_original_width_break(self):
        upper = self.model([])
        rules = {'zones': [{'startX': 0., 'endX': 4., 'widthM': 2., 'Q': 9.},
                           {'startX': 4., 'endX': 10., 'widthM': 3., 'Q': 8.}],
                 'liveRevision': {'splitX': 6., 'westEastPressureRatio': 2., 'totalLiveKN': 80.}}
        intervals, points = issued_density(upper, rules)
        self.assertFalse(points)
        # West/east areas are 14/12 m²: pressures are 4/2 kN/m².
        self.assertEqual(intervals, [(0., 4., [0., 0., -8.]), (4., 6., [0., 0., -12.]), (6., 10., [0., 0., -6.])])
        self.assertAlmostEqual(sum(-(b - a) * v[2] for a, b, v in intervals), 80.)


if __name__ == '__main__':
    unittest.main()
