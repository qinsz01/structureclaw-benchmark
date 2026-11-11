"""Exercise both factorization backends using analytical cantilever responses."""
from copy import deepcopy
import unittest
from unittest.mock import patch

import reference_solver as reference
from test_reference_solver import beam, add_load, E, IY


class FactorizationBackends(unittest.TestCase):
    def test_numpy_fallback_batches_load_selections(self):
        model = beam(4, cantilever=True)
        add_load(model, type="nodal", node="b", fz=-10)
        with patch.object(reference, "sparse", None):
            results = reference.solve_many(model, [{"D": 1}, {"D": -2}], [])
        for factor, (value, checks) in zip((1, -2), results):
            self.assertAlmostEqual(value(dict(kind="node", id="b"), "uz"), -factor*10*4**3/(3*E*IY), places=12)
            self.assertEqual(checks["factorizationCount"], 1)
            self.assertEqual(checks["rightHandSides"], 2)

    @unittest.skipIf(reference.sparse is None, "SciPy is required for the large sparse regression")
    def test_sparse_large_model_batches_three_physical_load_selections(self):
        model = beam(4, cantilever=True)
        original_nodes = deepcopy(model["nodes"])
        original_element = deepcopy(model["elements"][0])
        model["nodes"], model["elements"] = [], []
        # 2640 global DOFs exceeds the deliberate dense fallback size limit.
        # These independent cantilevers have exact, readily checked responses.
        for i in range(220):
            names = [f"a{i}", f"b{i}"]
            for name, original in zip(names, original_nodes):
                model["nodes"].append(dict(original, id=name, x=original["x"]+5*i))
            model["elements"].append(dict(original_element, id=f"e{i}", nodes=names))
            add_load(model, type="nodal", node=names[1], fz=-(i+1)/100)
        factors = (1., -2., .25)
        results = reference.solve_many(model, [{"D": f} for f in factors], [])
        for factor, (value, checks) in zip(factors, results):
            for i in (0, 99, 219):
                force = factor*(i+1)/100
                self.assertAlmostEqual(value(dict(kind="node", id=f"b{i}"), "uz"), -force*4**3/(3*E*IY), places=12)
                self.assertAlmostEqual(value(dict(kind="node", id=f"a{i}"), "Fz"), force, places=10)
            self.assertEqual(checks["dofs"], 2640)
            self.assertEqual(checks["factorization"], "scipy-sparse-superlu")
            self.assertEqual(checks["factorizationCount"], 1)
            self.assertEqual(checks["rightHandSides"], 3)


if __name__ == "__main__":
    unittest.main()
