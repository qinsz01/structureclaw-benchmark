"""Independent stiffness evidence for a fully restrained planar 3D embedding."""
import copy
import json
import os
from pathlib import Path
import sys
import unittest

for name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[name] = '1'
import numpy as np
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/research300'))
from reference_solver import axes, local_stiffness, solve
from reference_io import selection_factors


class PlanarEmbeddingChecks(unittest.TestCase):
    def test_member_active_stiffness_and_all_global_requested_results(self):
        ref = json.loads((ROOT / 'corpora/challenge-6-v1/cases/CH-002/private/t1.json').read_text())
        plane = ref['model']
        spatial = copy.deepcopy(plane)
        spatial['coordinate_system'].update(dimension='3d', plane=None)
        spatial['metadata']['elementReferenceVectors'] = {
            e['id']: [1., 0., 0.] if e['type'] == 'column' else [0., 0., 1.] for e in spatial['elements']}
        nodes = {n['id']: np.array([n[k] for k in 'xyz']) for n in plane['nodes']}
        sections = {s['id']: s for s in plane['sections']}
        materials = {m['id']: m for m in plane['materials']}
        active = [0, 2, 4, 6, 8, 10]
        for element in plane['elements']:
            a, b = [nodes[n] for n in element['nodes']]
            k = local_stiffness(element, materials[element['material']], sections[element['section']], np.linalg.norm(b-a))
            blocks = []
            for model in (plane, spatial):
                r = axes(model, element, a, b)
                transform = np.zeros((12, 12))
                for start in range(0, 12, 3):
                    transform[start:start+3, start:start+3] = r
                global_k = transform.T @ k @ transform
                blocks.append(global_k[np.ix_(active, active)])
            np.testing.assert_allclose(blocks[0], blocks[1], rtol=1e-12, atol=1e-10, err_msg=element['id'])
        for kind, identifier in [('case', 'D'), ('combination', 'D'), ('combination', 'SERVICE'), ('combination', 'REVERSE')]:
            selection = {'kind': kind, 'id': identifier}
            calculators = [solve(model, selection_factors(model, selection), [q['location'] for q in ref['requests']])[0]
                           for model in (plane, spatial)]
            for q in ref['requests']:
                values = [calc(q['location'], q['component']) for calc in calculators]
                self.assertLessEqual(abs(values[0]-values[1]), 1e-10+1e-10*abs(values[0]))


if __name__ == '__main__':
    unittest.main()
