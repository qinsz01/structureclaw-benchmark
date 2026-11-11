"""Regression tests for fields that must never silently change oracle physics."""
import unittest
import math

from test_reference_solver import beam, add_load, station
from reference_solver import solve


class UnsupportedFields(unittest.TestCase):
    def test_endpoint_one_ulp_above_geometry_is_roundoff(self):
        length = 4.337049688440288
        model = beam(length, cantilever=True)
        add_load(model, type="nodal", node="b", fz=-10)
        location = station(math.nextafter(length, math.inf))
        value, checks = solve(model, {"D": 1}, [location])
        self.assertEqual(checks["dofs"], 12)
        self.assertEqual(value(location, "uz"), value(dict(kind="node", id="b"), "uz"))

    def test_unknown_physical_fields_are_rejected(self):
        for target, field, value in (
            ("model", "multi_point_constraints", [{"master": "a", "slave": "b"}]),
            ("node", "spring_stiffness", [0, 0, 10, 0, 0, 0]),
            ("element", "release_i", [False, False, False, False, True, False]),
            ("section", "tapered", True),
            ("properties", "warping_constant", .001),
            ("material", "stress_strain_curve", [[0, 0], [.001, 10]]),
        ):
            with self.subTest(field=field):
                model = beam(cantilever=True)
                record = {"model": model, "node": model["nodes"][1],
                          "element": model["elements"][0], "section": model["sections"][0],
                          "properties": model["sections"][0]["properties"],
                          "material": model["materials"][0]}[target]
                record[field] = value
                with self.assertRaises(ValueError):
                    solve(model, {"D": 1}, [])

    def test_out_of_plane_load_cannot_be_absorbed_by_artificial_2d_restraint(self):
        for load in (dict(type="nodal", node="b", fy=5),
                     dict(type="point", element="beam", position=2, mz=5),
                     dict(type="distributed", element="beam", wy=5)):
            with self.subTest(load=load):
                model = beam(cantilever=True)
                add_load(model, **load)
                with self.assertRaises(ValueError):
                    solve(model, {"D": 1}, [])

    def test_explicit_uniform_label_cannot_hide_variable_end_values(self):
        model = beam()
        add_load(model, type="distributed", element="beam", distribution="uniform", wz_start=0, wz_end=-10)
        with self.assertRaises(ValueError):
            solve(model, {"D": 1}, [])


if __name__ == "__main__":
    unittest.main()
