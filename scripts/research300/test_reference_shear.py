"""Finite-shear audit controls; expectations are integrated beam formulas.

These tests would fail if shear is omitted, the two shear areas are swapped,
the MPa conversion is lost, or subdivision changes a uniform-load solution.
They exercise an explicitly selected diagnostic mode, not corpus promotion.
"""

from copy import deepcopy
import math
import unittest
from unittest.mock import patch

import reference_solver as reference
from test_reference_solver import (A, E, G, IY, IZ, J, add_load, at_node,
                                   beam, node, station)


AREAS = {"beam": {"Asy": 0.007, "Asz": 0.004}}


class FiniteShearAudit(unittest.TestCase):
    def close(self, actual, expected):
        self.assertTrue(math.isfinite(actual))
        self.assertAlmostEqual(actual, expected, delta=1e-10 + 2e-8 * abs(expected))

    def test_six_load_components_and_signed_superposition(self):
        L = 3.5
        vectors = [[float(i == j) for i in range(6)] for j in range(6)]
        vectors.append([-2, 3.5, -7, 11, -13, 17])
        for load in vectors:
            with self.subTest(load=load):
                model = beam(L, cantilever=True, dimension="3d")
                add_load(model, type="nodal", node="b",
                         **dict(zip(reference.REACTIONS, load)))
                value, checks = reference.solve(model, {"D": 1}, [],
                                               effective_shear_areas=AREAS)
                Fx, Fy, Fz, Mx, My, Mz = load
                expected = [Fx*L/(E*A),
                            (Fy*L**3/3 + Mz*L**2/2)/(E*IZ) + Fy*L/(G*.007),
                            (Fz*L**3/3 - My*L**2/2)/(E*IY) + Fz*L/(G*.004),
                            Mx*L/(G*J), (My*L-Fz*L**2/2)/(E*IY),
                            (Mz*L+Fy*L**2/2)/(E*IZ)]
                for component, wanted in zip(reference.DISPLACEMENTS, expected):
                    self.close(value(at_node("b"), component), wanted)
                reactions = [-Fx, -Fy, -Fz, -Mx, -My+L*Fz, -Mz-L*Fy]
                for component, wanted in zip(reference.REACTIONS, reactions):
                    self.close(value(at_node("a"), component), wanted)
                self.assertEqual(checks["theory"], "Timoshenko")
                self.assertEqual(checks["effectiveShearAreasM2"], AREAS)
                self.assertLess(max(map(abs, checks["forceMomentBalance"])), 1e-8)

    def test_uniform_load_particular_solution_at_actual_stations(self):
        L, q = 6., 17.
        model = beam(L)
        add_load(model, type="distributed", element="beam", wz=-q)
        locations = [station(x) for x in [0, .7, 2.1, 3, 4.8, L]]
        value, _ = reference.solve(model, {"D": 1}, locations,
                                   effective_shear_areas=AREAS)
        for location in locations:
            x = location["positionM"]
            with self.subTest(x=x):
                bend = -q*x*(L**3-2*L*x*x+x**3)/(24*E*IY)
                shear = -q*x*(L-x)/(2*G*.004)
                self.close(value(location, "uz"), bend+shear)
                self.close(value(location, "ry"), q*(L**3-6*L*x*x+4*x**3)/(24*E*IY))
                self.close(value(location, "V3"), q*(L/2-x))
                self.close(value(location, "M2"), -q*x*(L-x)/2)

    def test_distinct_members_do_not_share_a_default_shear_area(self):
        model = beam(2, cantilever=True, dimension="3d")
        model["nodes"] += [node("c", [0, 5, 0], [True]*6),
                            node("d", [4, 5, 0], [False]*6)]
        second = dict(model["elements"][0], id="second", nodes=["c", "d"])
        model["elements"].append(second)
        model["metadata"]["elementReferenceVectors"]["second"] = [0, 0, 1]
        add_load(model, type="nodal", node="b", fy=5)
        add_load(model, type="nodal", node="d", fy=5)
        areas = dict(AREAS, second={"Asy": .002, "Asz": .009})
        original = deepcopy(model)
        value, checks = reference.solve(model, {"D": 1}, [], effective_shear_areas=areas)
        self.close(value(at_node("b"), "uy"), 5*2**3/(3*E*IZ)+5*2/(G*.007))
        self.close(value(at_node("d"), "uy"), 5*4**3/(3*E*IZ)+5*4/(G*.002))
        self.assertEqual(model, original)
        areas["second"]["Asy"] = 99
        self.assertEqual(checks["effectiveShearAreasM2"]["second"]["Asy"], .002)

    def test_batched_signed_case_factors_keep_one_factorization(self):
        model = beam(3, cantilever=True, dimension="3d")
        add_load(model, case="D", type="nodal", node="b", fy=2)
        add_load(model, case="L", type="nodal", node="b", fy=-7)
        solutions = reference.solve_many(model, [{"D": 1}, {"L": 1}, {"D": 2, "L": -.5}], [],
                                         effective_shear_areas=AREAS)
        for (value, check), force in zip(solutions, [2, -7, 7.5]):
            self.close(value(at_node("b"), "uy"), force*27/(3*E*IZ)+force*3/(G*.007))
            self.assertEqual(check["factorizationCount"], 1)
            self.assertEqual(check["rightHandSides"], 3)

    def test_default_corpus_solver_retains_euler_bernoulli(self):
        model = beam(2, cantilever=True, dimension="3d")
        add_load(model, type="nodal", node="b", fy=1)
        value, checks = reference.solve(model, {"D": 1}, [])
        self.close(value(at_node("b"), "uy"), 8/(3*E*IZ))
        self.assertEqual(checks["theory"], "Euler-Bernoulli")
        self.assertNotIn("effectiveShearAreasM2", checks)

    def test_missing_extra_and_invalid_area_records_are_rejected(self):
        model = beam(2, cantilever=True, dimension="3d")
        records = [{}, [], {"other": dict(AREAS["beam"])},
                   {"beam": {"Asy": .007}},
                   {"beam": dict(AREAS["beam"], extra=1)}]
        records += [{"beam": dict(AREAS["beam"], Asz=x)}
                    for x in [0, -1, True, None, "0.004", float("inf"), float("nan")]]
        for record in records:
            with self.subTest(record=record), self.assertRaises(ValueError):
                reference.solve(model, {"D": 1}, [], effective_shear_areas=record)

    def test_varying_distributed_load_cannot_use_hermite_load_vector(self):
        model = beam(2, cantilever=True, dimension="3d")
        add_load(model, type="distributed", element="beam", distribution="linear",
                 wz_start=0, wz_end=-10)
        with self.assertRaisesRegex(ValueError, "piecewise-constant"):
            reference.solve(model, {"D": 1}, [], effective_shear_areas=AREAS)

    def test_subdivided_point_load_has_shear_jump_and_exact_displacement(self):
        model = beam(6)
        add_load(model, type="point", element="beam", position=2, fz=-18)
        left, right = station(2, "left"), station(2, "right")
        # Independent flexibility: bending P*a²*b²/(3*EI*L), shear P*a*b/(GA*L).
        for backend in (reference.sparse, None):
            with self.subTest(sparse=backend is not None), patch.object(reference, "sparse", backend):
                value, _ = reference.solve(model, {"D": 1}, [left, right],
                                           effective_shear_areas=AREAS)
                expected = -18*2**2*4**2/(3*E*IY*6)-18*2*4/(G*.004*6)
                self.close(value(left, "uz"), expected)
                self.close(value(right, "uz"), expected)
                self.close(value(left, "V3"), 12)
                self.close(value(right, "V3"), -6)

    def test_area_numeric_overflow_is_not_an_implicit_eb_switch(self):
        model = beam(2, cantilever=True, dimension="3d")
        with self.assertRaisesRegex(ValueError, "numeric range"):
            reference.solve(model, {"D": 1}, [],
                            effective_shear_areas={"beam": {"Asy": 1e308, "Asz": .004}})


class NativeFiniteShearFrame(unittest.TestCase):
    close = FiniteShearAudit.close
    # API: https://openseespydoc.readthedocs.io/en/latest/src/ElasticTimoshenkoBeam.html
    def test_space_frame_roll_unequal_areas_and_uniform_load_against_real_opensees(self):
        try:
            import openseespy.opensees as ops
        except ImportError as exc:
            self.skipTest(f"Real OpenSees unavailable; no numerical fallback: {exc}")
        model = beam(3, cantilever=True, dimension="3d")
        model["nodes"] = [node("a", [0, 0, 0], [True]*6),
                          node("b", [0, 0, 3], [False]*6),
                          node("c", [4, 0, 4], [False]*6),
                          node("d", [4, 0, 0], [True]*6)]
        model["elements"] = [dict(id=eid, type=kind, nodes=ends, material="mat", section="sec", rotation_angle=roll)
                             for eid, kind, ends, roll in [("left", "column", ["a", "b"], 0),
                                                          ("beam", "beam", ["b", "c"], 27),
                                                          ("right", "column", ["d", "c"], 0)]]
        model["metadata"]["elementReferenceVectors"] = {"left": [0, 1, 0], "beam": [0, 0, 1], "right": [1, 0, 0]}
        areas = {"left": {"Asy": .004, "Asz": .007}, "beam": {"Asy": .006, "Asz": .002},
                 "right": {"Asy": .009, "Asz": .005}}
        for case, target, force in [("D", "b", [4, -7, -11, 2, 3, -5]),
                                     ("L", "c", [-3, 5, -13, -2, 7, 11])]:
            add_load(model, case=case, type="nodal", node=target, **dict(zip(reference.REACTIONS, force)))
        add_load(model, type="distributed", element="beam", wx=2, wy=3, wz=-5)
        model["load_cases"][0]["loads"][-1]["reference_frame"] = "element-local"
        selections = [{"D": 1}, {"L": 1}, {"D": 1, "L": -.6}]
        stations = [station(x, member=eid) for eid, length in [("left", 3), ("beam", math.sqrt(17)), ("right", 4)]
                    for x in [0, length*.37, length]]
        solutions = reference.solve_many(model, selections, stations, effective_shear_areas=areas)
        # These transformation vectors are independently constructed from the
        # fixture geometry, including the 27° rolled beam's local z direction.
        angle = math.radians(27)
        vectors = [[0, 1, 0], [-math.cos(angle)/math.sqrt(17), -math.sin(angle),
                               4*math.cos(angle)/math.sqrt(17)], [1, 0, 0]]
        node_tags = {name: i+1 for i, name in enumerate("abcd")}
        try:
            for factors, (value, _) in zip(selections, solutions):
                ops.wipe()
                ops.model("basic", "-ndm", 3, "-ndf", 6)
                for n in model["nodes"]:
                    ops.node(node_tags[n["id"]], n["x"], n["y"], n["z"])
                    ops.fix(node_tags[n["id"]], *map(int, n["restraints"]))
                for tag, (e, vector) in enumerate(zip(model["elements"], vectors), 1):
                    ops.geomTransf("Linear", tag, *vector)
                    a = areas[e["id"]]
                    ops.element("ElasticTimoshenkoBeam", tag, *[node_tags[n] for n in e["nodes"]],
                                E, G, A, J, IY, IZ, a["Asy"], a["Asz"], tag)
                ops.timeSeries("Constant", 1)
                ops.pattern("Plain", 1, 1)
                for case in model["load_cases"]:
                    factor = factors.get(case["id"], 0)
                    for load in case["loads"]:
                        if load["type"] == "nodal":
                            ops.load(node_tags[load["node"]], *[factor*load.get(k, 0) for k in reference.REACTIONS])
                        else:
                            ops.eleLoad("-ele", 2, "-type", "-beamUniform", factor*3, factor*-5, factor*2)
                ops.constraints("Plain")
                ops.numberer("Plain")
                ops.system("BandGeneral")
                ops.algorithm("Linear")
                ops.integrator("LoadControl", 1.)
                ops.analysis("Static")
                self.assertEqual(ops.analyze(1), 0)
                ops.reactions()
                for name, tag in node_tags.items():
                    for component, expected in zip(reference.DISPLACEMENTS, ops.nodeDisp(tag)):
                        self.close(value(at_node(name), component), expected)
                    for component, expected in zip(reference.REACTIONS, ops.nodeReaction(tag)):
                        self.close(value(at_node(name), component), expected)
                for tag, (eid, length) in enumerate([("left", 3), ("beam", math.sqrt(17)), ("right", 4)], 1):
                    force = ops.eleResponse(tag, "localForce")
                    self.assertEqual(len(force), 12)
                    for x, offset, signs in [(0, 0, [-1, 1, 1, -1, -1, -1]),
                                              (length, 6, [1, -1, -1, 1, 1, 1])]:
                        for i, component in enumerate(reference.ACTIONS):
                            self.close(value(station(x, member=eid), component), signs[i]*force[offset+i])
        finally:
            ops.wipe()


if __name__ == "__main__":
    unittest.main()
