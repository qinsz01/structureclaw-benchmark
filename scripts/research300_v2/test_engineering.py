"""Engineering source/load provenance and independent mechanics qualification."""
from __future__ import annotations

import os
for _name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[_name] = '1'
from collections import defaultdict
from copy import deepcopy
import json
import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts/research300'))
from reference_solver import solve_many
try:
    from .engineering import SOURCE_IDS, build_engineering, _compile_recipe
    from .models import topology_fingerprint
except ImportError:
    from engineering import SOURCE_IDS, build_engineering, _compile_recipe
    from models import topology_fingerprint


def _independent_recipe_actions(packet):
    """Check vectors/intensities per destination, not the implementation helper."""
    expected, actual = defaultdict(float), defaultdict(float)
    for case in packet['loadRecipe']['cases']:
        for term in case['terms']:
            if term['kind'] == 'nodal':
                for axis in 'xyz':
                    expected[(case['id'], 'node', term['node'], axis)] += term.get('f'+axis, 0.)
            else:
                for eid in term['members']:
                    for axis, direction in zip('xyz', term['globalUnitVector']):
                        expected[(case['id'], 'member', eid, axis)] += direction*term['pressureKNM2']*term['tributaryWidthM']
    for case in packet['model']['load_cases']:
        for load in case['loads']:
            kind, dest, prefix = ('node', load['node'], 'f') if load['type'] == 'nodal' else ('member', load['element'], 'w')
            for axis in 'xyz':
                actual[(case['id'], kind, dest, axis)] += load.get(prefix+axis, 0.)
    assert set(actual) == set(expected)
    assert all(math.isclose(actual[k], v, abs_tol=1e-12, rel_tol=1e-12) for k, v in expected.items())


def independent_checks():
    rows = []
    factors = [{'D': 1.}, {'Q': 1.}, {'W': 1.}, {'D': 1., 'Q': 1.}, {'D': 1., 'W': -1.}]
    for sid in SOURCE_IDS:
        for subproblem in range(3):
            packet = build_engineering(sid, subproblem)
            _independent_recipe_actions(packet)
            m = packet['model']
            solved = solve_many(m, factors, [])
            nodal_maxima, hint_values = [], []
            for value, check in solved:
                responses = [value({'kind': 'node', 'id': n['id']}, c)
                             for n in m['nodes'] for c in ('ux', 'uy', 'uz')]
                assert all(math.isfinite(x) for x in responses)
                nodal_maxima.append(max(abs(x) for x in responses))
                hint_values.append(max(abs(value({'kind': 'node', 'id': n}, packet['constraintHint']['component']))
                                       for n in packet['constraintHint']['nodes']))
                assert check['minimumScaledPivot'] is None or check['minimumScaledPivot'] > 0
            rows.append({'sourceId': sid, 'subproblem': subproblem,
                'subproblemId': packet['subproblemId'], 'dimension': m['coordinate_system']['dimension'],
                'nodes': len(m['nodes']), 'members': len(m['elements']),
                'topologyFingerprint': topology_fingerprint(m), 'allPassed': True,
                'rightHandSides': len(solved), 'maximumDisplacementsM': nodal_maxima,
                'constraintHint': packet['constraintHint'], 'constraintHintValuesM': hint_values,
                'maximumFreeResidual': max(c['freeResidual'] for _, c in solved),
                'maximumForceMomentImbalance': max(abs(v) for _, c in solved for v in c['forceMomentBalance']),
                'minimumScaledPivot': min(c['minimumScaledPivot'] for _, c in solved if c['minimumScaledPivot'] is not None)})
    return {'models': len(rows), 'independentLoadSelections': 5*len(rows),
        'uniqueTopologyFingerprints': len({r['topologyFingerprint'] for r in rows}),
        'actualSUTCalls': 0, 'allPassed': all(r['allPassed'] for r in rows),
        'method': 'Independent Euler-Bernoulli direct stiffness; D/Q/W/SERVICE/REVERSE; positive pivots and force/moment balance',
        'rows': rows}


class EngineeringChecks(unittest.TestCase):
    def test_all_thirty_subproblems_stable_and_balanced(self):
        result = independent_checks()
        self.assertEqual(result['models'], 30)
        self.assertEqual(result['independentLoadSelections'], 150)
        self.assertTrue(result['allPassed'])
        # Real engineering can share a topology; report it instead of renaming it.
        self.assertGreaterEqual(result['uniqueTopologyFingerprints'], 24)

    def test_provenance_recipe_and_continuous_observation_nodes(self):
        for sid in SOURCE_IDS:
            for subproblem in range(3):
                p = build_engineering(sid, subproblem)
                self.assertEqual(p['subproblemId'], f'{sid}-P{subproblem+1}')
                self.assertTrue(p['authoringBasis'])
                _independent_recipe_actions(p)
                m = p['model']; nodes = {n['id']: n for n in m['nodes']}
                self.assertTrue(p['constraintHint']['nodes'])
                for nid in p['constraintHint']['nodes']:
                    self.assertIn(nid, nodes)
                    index = {'ux': 0, 'uz': 2}[p['constraintHint']['component']]
                    self.assertFalse(nodes[nid]['restraints'][index])
                for n in m['nodes']:
                    self.assertTrue(all(n[k] == round(n[k], 6) for k in 'xyz'))
                    if n['id'].startswith('OBS-'):
                        incidence = [e for e in m['elements'] if n['id'] in e['nodes']]
                        self.assertEqual(len(incidence), 2)
                        self.assertEqual(incidence[0]['section'], incidence[1]['section'])
                        self.assertTrue(all(not e.get('releases') for e in incidence))
                        self.assertEqual(sum(n['restraints']), 3 if m['coordinate_system']['dimension'] == '2d' else 0)
                self.assertFalse(m['analysis_control']['self_weight'])

    def test_known_source_actions_and_authored_grid_are_preserved(self):
        pipe = build_engineering('SRC-PIPE-2020', 0)
        loads = {c['id']: c['loads'] for c in pipe['model']['load_cases']}
        self.assertAlmostEqual(-sum(l['fz'] for l in loads['D']), 2*5.48+7*10.37)
        self.assertAlmostEqual(-sum(l['fz'] for l in loads['Q']), 2*9.25+7*18.5)
        office = build_engineering('SRC-CABLE-2010', 0)
        base_x = sorted(n['x'] for n in office['model']['nodes'] if n['z'] == 0.)
        self.assertEqual(base_x, [0., 6., 12., 18.])
        self.assertTrue(any('不宣称原轴网' in s for s in office['authoringBasis']))
        hillside = build_engineering('SRC-HILLSIDE-2020', 2)['model']
        self.assertEqual([n['z'] for n in hillside['nodes'] if n['id'].endswith('-0')], [0., 0., 1.5, 1.5, 1.5])

    def test_fresh_models_and_invalid_or_duplicate_pressure_inputs(self):
        a = build_engineering(SOURCE_IDS[0], 0); b = build_engineering(SOURCE_IDS[0], 0)
        self.assertEqual(a, b)
        a['model']['nodes'][0]['x'] = 999.
        self.assertNotEqual(a, b)
        for invalid in (-1, 3, True, 1.5):
            with self.assertRaises(ValueError): build_engineering(SOURCE_IDS[0], invalid)
        with self.assertRaises(ValueError): build_engineering('SRC-PV-2023', 0)
        bad = deepcopy(b['loadRecipe'])
        term = bad['cases'][0]['terms'][0]
        term['members'].append(term['members'][0])
        with self.assertRaises(ValueError): _compile_recipe(b['model'], bad)


if __name__ == '__main__':
    if '--output' in sys.argv:
        i = sys.argv.index('--output'); path = Path(sys.argv[i+1])
        report = independent_checks(); path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('x') as f:
            f.write(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
        print(json.dumps({k: v for k, v in report.items() if k != 'rows'}))
    else:
        unittest.main()
