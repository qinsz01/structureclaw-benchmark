"""Closed-form mechanics regressions for the independent research-300 oracle.

Run from the repository root with:
    python3 -m unittest discover -s scripts/research300 -p test_reference_solver.py

These fixtures use metres, kN and radians; E/G are supplied in MPa as required
by model protocol 2.2.0. Expected values come from statics, Euler--Bernoulli
beam formulas and Macaulay integration, independently of matrix assembly.
"""

from copy import deepcopy
import math
import unittest

import reference_solver as reference


E_MPA = 200000.0
G_MPA = 80000.0
A = 0.012
IY = 8.0e-5
IZ = 2.0e-5
J = 1.5e-5
E = E_MPA * 1000.0
G = G_MPA * 1000.0
PLANAR_FREE = [False, True, False, True, False, True]


def node(identifier, xyz, restraints):
    return dict(id=identifier, x=xyz[0], y=xyz[1], z=xyz[2],
                restraints=list(restraints))


def model(dimension="2d"):
    return dict(
        schema_version="2.2.0", unit_system="SI",
        coordinate_system=dict(dimension=dimension,
                               plane="xz" if dimension == "2d" else None,
                               semantics="global-z-up", version=1,
                               dof_order=["ux", "uy", "uz", "rx", "ry", "rz"]),
        nodes=[], elements=[],
        materials=[dict(id="mat", name="steel", type="steel", E=E_MPA,
                        G=G_MPA, nu=0.25, rho=7850)],
        sections=[dict(id="sec", name="explicit section", type="general",
                       properties=dict(A=A, Iy=IY, Iz=IZ, J=J))],
        load_cases=[dict(id="D", type="dead", loads=[])],
        load_combinations=[],
        analysis_control=dict(self_weight=False, rigid_floor=False,
                              p_delta=False, rigid_offsets=False,
                              construction_stage=False),
        metadata=dict(elementReferenceVectors={}),
    )


def beam(length=6.0, cantilever=False, dimension="2d"):
    result = model(dimension)
    root_restraints = [True] * 6 if cantilever else [True, True, True, True, False, True]
    tip_restraints = ([False] * 6 if dimension == "3d" else PLANAR_FREE) if cantilever else [False, True, True, True, False, True]
    result["nodes"] = [node("a", (0, 0, 0), root_restraints),
                       node("b", (length, 0, 0), tip_restraints)]
    result["elements"] = [dict(id="beam", type="beam", nodes=["a", "b"],
                               material="mat", section="sec")]
    if dimension == "3d":
        result["metadata"]["elementReferenceVectors"]["beam"] = [0, 0, 1]
    return result


def add_load(structure, case="D", **load):
    load_case = next((entry for entry in structure["load_cases"] if entry["id"] == case), None)
    if load_case is None:
        load_case = dict(id=case, type="live", loads=[])
        structure["load_cases"].append(load_case)
    load_case["loads"].append(dict(id=f"{case}-{len(load_case['loads']) + 1}",
                                   reference_frame="global", **load))


def station(position, side="right", member="beam"):
    return dict(kind="member", id=member, positionM=position, side=side)


def at_node(identifier):
    return dict(kind="node", id=identifier)


def distributed_theory(length, intervals, position):
    """Integrate positive-downward linear load intervals analytically.

    An interval (a, b, qa, qb) is represented by four singularity terms.
    Integrating those terms gives shear, moment, slope and displacement;
    zero displacement at both supports supplies the integration constant.
    No finite elements or numerical quadrature are used.
    """
    total = first_moment = 0.0
    terms = []
    for start, end, qa, qb in intervals:
        span = end - start
        slope = (qb - qa) / span
        force = (qa + qb) * span / 2
        total += force
        first_moment += start * force + qa * span**2 / 2 + slope * span**3 / 3
        terms.extend([(start, qa, 0), (start, slope, 1),
                      (end, -qb, 0), (end, -slope, 1)])
    right = first_moment / length
    left = total - right

    def integrated(x, count):
        return sum(coefficient * max(0.0, x - origin)**(power + count)
                   * math.factorial(power) / math.factorial(power + count)
                   for origin, coefficient, power in terms)

    constant = (integrated(length, 4) - left * length**3 / 6) / length
    return dict(left=left, right=right,
                V3=left - integrated(position, 1),
                M2=-left * position + integrated(position, 2),
                uz=(left * position**3 / 6 - integrated(position, 4)
                    + constant * position) / (E * IY),
                ry=-(left * position**2 / 2 - integrated(position, 3)
                     + constant) / (E * IY))


class AnalyticalMechanics(unittest.TestCase):
    def assert_close(self, actual, expected):
        self.assertTrue(math.isfinite(actual), f"Nonfinite result: {actual}")
        self.assertAlmostEqual(actual, expected,
                               delta=2e-9 + 2e-8 * abs(expected))

    def assert_equilibrium(self, checks):
        self.assertLess(abs(checks["freeResidual"]), 1e-7)
        self.assertEqual(len(checks["forceMomentBalance"]), 6)
        self.assertLess(max(abs(value) for value in checks["forceMomentBalance"]), 1e-7)

    def test_uniform_simply_supported_exact_station_displacement_and_rotation(self):
        length, q = 6.0, 20.0
        structure = beam(length)
        add_load(structure, type="distributed", element="beam", wz=-q)
        stations = [station(x) for x in (0.0, 0.7, 2.1, 3.0, 4.8, length)]
        value, checks = reference.solve(structure, {"D": 1}, stations)
        for location in stations:
            x = location["positionM"]
            with self.subTest(x=x):
                self.assert_close(value(location, "V3"), q * (length / 2 - x))
                self.assert_close(value(location, "M2"), -q * x * (length - x) / 2)
                self.assert_close(value(location, "uz"),
                                  -q * x * (length**3 - 2 * length * x**2 + x**3) / (24 * E * IY))
                self.assert_close(value(location, "ry"),
                                  q * (length**3 - 6 * length * x**2 + 4 * x**3) / (24 * E * IY))
        for support in ("a", "b"):
            self.assert_close(value(at_node(support), "Fz"), q * length / 2)
            self.assert_close(value(at_node(support), "My"), 0.0)
        self.assert_equilibrium(checks)

    def test_off_center_point_load_has_correct_left_and_right_shear(self):
        length, load, a = 6.0, 18.0, 1.5
        b = length - a
        structure = beam(length)
        add_load(structure, type="point", element="beam", position=a, fz=-load)
        left, right = station(a, "left"), station(a, "right")
        value, checks = reference.solve(structure, {"D": 1}, [left, right])
        self.assert_close(value(left, "V3"), load * b / length)
        self.assert_close(value(right, "V3"), -load * a / length)
        self.assert_close(value(left, "V3") - value(right, "V3"), load)
        for location in (left, right):
            self.assert_close(value(location, "M2"), -load * a * b / length)
            self.assert_close(value(location, "uz"), -load * a**2 * b**2 / (3 * E * IY * length))
            self.assert_close(value(location, "ry"), load * a * b * (b - a) / (3 * E * IY * length))
        self.assert_close(value(at_node("a"), "Fz"), load * b / length)
        self.assert_close(value(at_node("b"), "Fz"), load * a / length)
        self.assert_equilibrium(checks)

    def test_cantilever_axial_bending_and_torsion(self):
        length, force, transverse, torque = 4.0, 15.0, 11.0, 7.0
        structure = beam(length, cantilever=True, dimension="3d")
        add_load(structure, type="nodal", node="b", fx=force, fz=-transverse, mx=torque)
        locations = [station(length / 3), station(length)]
        value, checks = reference.solve(structure, {"D": 1}, locations)
        for location in locations:
            x = location["positionM"]
            self.assert_close(value(location, "ux"), force * x / (E * A))
            self.assert_close(value(location, "uz"), -transverse * x**2 * (3 * length - x) / (6 * E * IY))
            self.assert_close(value(location, "ry"), transverse * x * (2 * length - x) / (2 * E * IY))
            self.assert_close(value(location, "rx"), torque * x / (G * J))
            self.assert_close(value(location, "N"), force)
            self.assert_close(value(location, "T"), torque)
            self.assert_close(value(location, "V3"), transverse)
            self.assert_close(value(location, "M2"), transverse * (length - x))
        for component, expected in (("Fx", -force), ("Fz", transverse),
                                    ("Mx", -torque), ("My", -transverse * length)):
            self.assert_close(value(at_node("a"), component), expected)
        self.assert_equilibrium(checks)

    def test_cantilever_uniform_load_tip_response(self):
        length, q = 5.0, 9.0
        structure = beam(length, cantilever=True)
        add_load(structure, type="distributed", element="beam", wz=-q)
        value, checks = reference.solve(structure, {"D": 1}, [])
        self.assert_close(value(at_node("b"), "uz"), -q * length**4 / (8 * E * IY))
        self.assert_close(value(at_node("b"), "ry"), q * length**3 / (6 * E * IY))
        self.assert_close(value(at_node("a"), "Fz"), q * length)
        self.assert_close(value(at_node("a"), "My"), -q * length**2 / 2)
        self.assert_equilibrium(checks)

    def test_two_bar_truss_compression_and_apex_displacement(self):
        half_width, height, load = 3.0, 4.0, 24.0
        length = 5.0
        structure = model()
        structure["nodes"] = [node("left", (-half_width, 0, 0), [True] * 6),
                               node("right", (half_width, 0, 0), [True] * 6),
                               node("apex", (0, 0, height), PLANAR_FREE)]
        structure["elements"] = [dict(id=identifier, type="truss", nodes=[support, "apex"],
                                       material="mat", section="sec")
                                 for identifier, support in (("left-bar", "left"), ("right-bar", "right"))]
        add_load(structure, type="nodal", node="apex", fz=-load)
        locations = [station(2.5, member=identifier) for identifier in ("left-bar", "right-bar")]
        value, checks = reference.solve(structure, {"D": 1}, locations)
        for location in locations:
            self.assert_close(value(location, "N"), -load * length / (2 * height))
        self.assert_close(value(at_node("apex"), "uz"), -load * length**3 / (2 * E * A * height**2))
        self.assert_close(value(at_node("apex"), "ux"), 0.0)
        self.assert_close(value(at_node("left"), "Fx"), load * half_width / (2 * height))
        self.assert_close(value(at_node("right"), "Fx"), -load * half_width / (2 * height))
        for support in ("left", "right"):
            self.assert_close(value(at_node(support), "Fz"), load / 2)
        self.assert_equilibrium(checks)

    def test_section_roll_exchanges_principal_bending_stiffness(self):
        length, force = 4.0, 12.0
        unrolled = beam(length, cantilever=True)
        add_load(unrolled, type="nodal", node="b", fz=-force)
        rolled = deepcopy(unrolled)
        rolled["elements"][0]["rotation_angle"] = 90
        straight_value, _ = reference.solve(unrolled, {"D": 1}, [])
        rolled_value, checks = reference.solve(rolled, {"D": 1}, [])
        self.assert_close(straight_value(at_node("b"), "uz"), -force * length**3 / (3 * E * IY))
        self.assert_close(rolled_value(at_node("b"), "uz"), -force * length**3 / (3 * E * IZ))
        self.assert_close(rolled_value(at_node("b"), "ry"), force * length**2 / (2 * E * IZ))
        self.assert_equilibrium(checks)

    def test_arbitrary_spatial_axes_transform_all_six_dofs(self):
        length = 4.5
        ex = (1 / 3, 2 / 3, 2 / 3)
        ey = (-2 / math.sqrt(5), 1 / math.sqrt(5), 0)
        ez = (-2 / (3 * math.sqrt(5)), -4 / (3 * math.sqrt(5)), math.sqrt(5) / 3)
        basis = (ex, ey, ez)

        def global_vector(local):
            return [sum(local[j] * basis[j][i] for j in range(3)) for i in range(3)]

        origin = (1.0, -2.0, 0.5)
        structure = beam(length, cantilever=True, dimension="3d")
        structure["nodes"] = [node("a", origin, [True] * 6),
                               node("b", tuple(origin[i] + length * ex[i] for i in range(3)), [False] * 6)]
        axial, fy, fz, torque = 8.0, -11.0, -17.0, 6.0
        force = global_vector((axial, fy, fz))
        applied_moment = global_vector((torque, 0, 0))
        add_load(structure, type="nodal", node="b",
                 **dict(zip(("fx", "fy", "fz", "mx", "my", "mz"), force + applied_moment)))
        middle = station(length / 2)
        value, checks = reference.solve(structure, {"D": 1}, [middle])
        expected_displacement = global_vector((axial * length / (E * A),
                                               fy * length**3 / (3 * E * IZ),
                                               fz * length**3 / (3 * E * IY)))
        expected_rotation = global_vector((torque * length / (G * J),
                                           -fz * length**2 / (2 * E * IY),
                                           fy * length**2 / (2 * E * IZ)))
        expected_base_moment = global_vector((-torque, fz * length, -fy * length))
        for component, expected in zip(("ux", "uy", "uz", "rx", "ry", "rz"),
                                       expected_displacement + expected_rotation):
            self.assert_close(value(at_node("b"), component), expected)
        for component, expected in zip(("Fx", "Fy", "Fz", "Mx", "My", "Mz"),
                                       [-f for f in force] + expected_base_moment):
            self.assert_close(value(at_node("a"), component), expected)
        for component, expected in (("N", axial), ("V2", -fy), ("V3", -fz),
                                    ("T", torque), ("M2", -fz * length / 2), ("M3", fy * length / 2)):
            self.assert_close(value(middle, component), expected)
        self.assert_equilibrium(checks)

    def test_local_and_global_distributed_loads_on_vertical_spatial_member(self):
        length, q = 4.0, 7.0
        local_model = beam(length, cantilever=True, dimension="3d")
        local_model["nodes"][1].update(x=0.0, z=length)
        local_model["metadata"]["elementReferenceVectors"]["beam"] = [1, 0, 0]
        add_load(local_model, type="distributed", element="beam", wz=-q)
        local_model["load_cases"][0]["loads"][0]["reference_frame"] = "local"
        global_model = deepcopy(local_model)
        global_model["load_cases"][0]["loads"][0].update(reference_frame="global", wz=0, wx=-q)
        canonical_model = deepcopy(local_model)
        canonical_model["load_cases"][0]["loads"][0]["reference_frame"] = "element-local"
        for structure in (local_model, canonical_model, global_model):
            with self.subTest(frame=structure["load_cases"][0]["loads"][0]["reference_frame"]):
                value, checks = reference.solve(structure, {"D": 1}, [])
                self.assert_close(value(at_node("b"), "ux"), -q * length**4 / (8 * E * IY))
                self.assert_close(value(at_node("a"), "Fx"), q * length)
                self.assert_close(value(at_node("a"), "My"), q * length**2 / 2)
                self.assert_equilibrium(checks)

    def test_element_local_point_force_and_moment_transform_with_signed_jumps(self):
        length, a = 5.0, 2.0
        # Vertical member: local x=global Z, local y=-global Y, local z=global X.
        # A local -z force and +y couple both bend the tip toward global -X.
        for frame in ("element-local", "local"):
            for force, moment in ((11.0, 0.0), (0.0, 7.0), (11.0, 7.0)):
                with self.subTest(frame=frame, force=force, moment=moment):
                    structure = beam(length, cantilever=True, dimension="3d")
                    structure["nodes"][1].update(x=0.0, z=length)
                    structure["metadata"]["elementReferenceVectors"]["beam"] = [1, 0, 0]
                    add_load(structure, type="point", element="beam", position=a,
                             fz=-force, my=moment)
                    structure["load_cases"][0]["loads"][0]["reference_frame"] = frame
                    left, right = station(a, "left"), station(a, "right")
                    value, checks = reference.solve(structure, {"D": 1}, [left, right])
                    self.assert_close(value(at_node("b"), "ux"),
                                      -force * a**2 * (3 * length - a) / (6 * E * IY)
                                      -moment * a * (2 * length - a) / (2 * E * IY))
                    self.assert_close(value(at_node("b"), "ry"),
                                      -force * a**2 / (2 * E * IY) - moment * a / (E * IY))
                    self.assert_close(value(at_node("a"), "Fx"), force)
                    self.assert_close(value(at_node("a"), "My"), force * a + moment)
                    self.assert_close(value(left, "V3"), force)
                    self.assert_close(value(left, "M2"), moment)
                    self.assert_close(value(right, "V3"), 0.0)
                    self.assert_close(value(right, "M2"), 0.0)
                    self.assert_close(value(at_node("b"), "uy"), 0.0)
                    self.assert_close(value(at_node("b"), "uz"), 0.0)
                    self.assert_equilibrium(checks)

    def test_element_local_linear_distributed_load_on_vertical_member(self):
        length, q = 4.0, 9.0
        for frame in ("element-local", "local"):
            with self.subTest(frame=frame):
                structure = beam(length, cantilever=True, dimension="3d")
                structure["nodes"][1].update(x=0.0, z=length)
                structure["metadata"]["elementReferenceVectors"]["beam"] = [1, 0, 0]
                add_load(structure, type="distributed", element="beam",
                         wz_start=0.0, wz_end=-q)
                structure["load_cases"][0]["loads"][0]["reference_frame"] = frame
                middle = station(length / 2)
                value, checks = reference.solve(structure, {"D": 1}, [middle])
                self.assert_close(value(at_node("b"), "ux"), -11 * q * length**4 / (120 * E * IY))
                self.assert_close(value(at_node("b"), "ry"), -q * length**3 / (8 * E * IY))
                self.assert_close(value(at_node("a"), "Fx"), q * length / 2)
                self.assert_close(value(at_node("a"), "My"), q * length**2 / 3)
                self.assert_close(value(middle, "V3"), 3 * q * length / 8)
                self.assert_close(value(middle, "M2"), 5 * q * length**2 / 48)
                self.assert_equilibrium(checks)

    def check_distributed_intervals(self, structure, length, intervals, positions):
        locations = [station(x) for x in positions]
        value, checks = reference.solve(structure, {"D": 1}, locations)
        for location in locations:
            expected = distributed_theory(length, intervals, location["positionM"])
            for component in ("V3", "M2", "uz", "ry"):
                with self.subTest(position=location["positionM"], component=component):
                    self.assert_close(value(location, component), expected[component])
        expected = distributed_theory(length, intervals, 0)
        self.assert_close(value(at_node("a"), "Fz"), expected["left"])
        self.assert_close(value(at_node("b"), "Fz"), expected["right"])
        self.assert_equilibrium(checks)

    def test_partial_uniform_load_boundaries_and_unloaded_intervals(self):
        structure = beam(10.0)
        add_load(structure, type="distributed", element="beam", start=2.0, end=7.0, wz=-12.0)
        self.check_distributed_intervals(structure, 10.0, [(2.0, 7.0, 12.0, 12.0)],
                                         (0.0, 1.0, 2.0, 4.1, 7.0, 9.0, 10.0))

    def test_triangular_load_closed_form(self):
        length, q = 6.0, 18.0
        structure = beam(length)
        add_load(structure, type="distributed", element="beam", start=0.0, end=length,
                 wz_start=0.0, wz_end=-q)
        middle = station(length / 2)
        value, checks = reference.solve(structure, {"D": 1}, [middle])
        self.assert_close(value(at_node("a"), "Fz"), q * length / 6)
        self.assert_close(value(at_node("b"), "Fz"), q * length / 3)
        self.assert_close(value(middle, "V3"), q * length / 24)
        self.assert_close(value(middle, "M2"), -q * length**2 / 16)
        self.assert_close(value(middle, "uz"), -5 * q * length**4 / (768 * E * IY))
        self.assert_equilibrium(checks)

    def test_partial_linear_and_trapezoidal_load_aliases(self):
        for load_type in ("distributed", "linear", "trapezoidal"):
            with self.subTest(load_type=load_type):
                structure = beam(9.0)
                add_load(structure, type=load_type, element="beam", start=1.5, end=7.0,
                         wz_start=-3.0, wz_end=-19.0)
                self.check_distributed_intervals(structure, 9.0, [(1.5, 7.0, 3.0, 19.0)],
                                                 (0.0, 0.5, 1.5, 3.2, 5.1, 7.0, 8.0, 9.0))

    def test_symmetric_piecewise_triangle_closed_form(self):
        length, q = 8.0, 15.0
        structure = beam(length)
        add_load(structure, type="piecewise", element="beam", points=[
            dict(position=0.0, wz=0.0), dict(position=length / 2, wz=-q),
            dict(position=length, wz=0.0)])
        middle = station(length / 2)
        value, checks = reference.solve(structure, {"D": 1}, [middle])
        self.assert_close(value(at_node("a"), "Fz"), q * length / 4)
        self.assert_close(value(at_node("b"), "Fz"), q * length / 4)
        self.assert_close(value(middle, "M2"), -q * length**2 / 12)
        self.assert_close(value(middle, "uz"), -q * length**4 / (120 * E * IY))
        self.assert_close(value(middle, "ry"), 0.0)
        self.assert_equilibrium(checks)

    def test_irregular_piecewise_load_and_overlapping_uniform_load(self):
        structure = beam(9.0)
        points = [(1.0, 3.0), (3.0, 11.0), (5.0, 4.0), (8.0, 0.0)]
        add_load(structure, type="piecewise", element="beam",
                 points=[dict(position=x, wz=-q) for x, q in points])
        add_load(structure, type="distributed", element="beam", start=2.0, end=6.0, wz=-5.0)
        intervals = [(a, b, qa, qb) for (a, qa), (b, qb) in zip(points, points[1:])]
        intervals.append((2.0, 6.0, 5.0, 5.0))
        self.check_distributed_intervals(structure, 9.0, intervals,
                                         (0.0, 0.4, 1.0, 2.5, 3.0, 4.6, 5.0, 6.0, 8.0, 8.5, 9.0))

    def test_piecewise_segments_preserve_gaps_and_intensity_discontinuities(self):
        intervals = [(0.0, 1.5, 3.0, 3.0), (3.0, 5.0, 11.0, 4.0),
                     (5.0, 7.0, 9.0, 2.0)]
        segments = [dict(start=0.0, end=1.5, wz=-3.0),
                    dict(start=3.0, end=5.0, wz_start=-11.0, wz_end=-4.0),
                    dict(start=5.0, end=7.0, wz_start=-9.0, wz_end=-2.0)]
        for encoding in (dict(type="piecewise"),
                         dict(type="distributed", variation="piecewise")):
            with self.subTest(encoding=encoding):
                structure = beam(8.0)
                add_load(structure, element="beam", segments=deepcopy(segments), **encoding)
                self.check_distributed_intervals(
                    structure, 8.0, intervals,
                    (0.0, 0.5, 1.5, 2.2, 3.0, 4.2, 5.0, 6.0, 7.0, 8.0))
                # Separate loads may overlap, but one piecewise specification
                # must not ambiguously assign two intensities to one interval.
                structure["load_cases"][0]["loads"][0]["segments"][1]["start"] = 1.0
                with self.assertRaises(ValueError):
                    reference.solve(structure, {"D": 1}, [])

    def test_signed_case_factors_batched_and_same_name_combination(self):
        length, q, load = 6.0, 5.0, 13.0
        structure = beam(length)
        add_load(structure, type="distributed", element="beam", wz=-q)
        add_load(structure, case="L", type="point", element="beam", position=length / 2, fz=-load)
        structure["load_combinations"] = [dict(id="D", factors={"L": 20})]
        locations = [station(length / 2, "left"), station(length / 2, "right")]
        factors = [{"D": 1}, {"L": 1}, {"D": 1.2, "L": 1.4}, {"D": 0, "L": -0.7}, {}]
        results = reference.solve_many(structure, factors, locations)
        self.assertEqual(len(results), len(factors))
        for coefficients, (value, checks) in zip(factors, results):
            d, live = coefficients.get("D", 0), coefficients.get("L", 0)
            with self.subTest(factors=coefficients):
                self.assert_close(value(at_node("a"), "Fz"), d * q * length / 2 + live * load / 2)
                self.assert_close(value(locations[0], "M2"), -d * q * length**2 / 8 - live * load * length / 4)
                self.assert_close(value(locations[0], "uz"), -d * 5 * q * length**4 / (384 * E * IY)
                                  - live * load * length**3 / (48 * E * IY))
                self.assert_close(value(locations[0], "V3"), live * load / 2)
                self.assert_close(value(locations[1], "V3"), -live * load / 2)
                self.assert_equilibrium(checks)

    def test_station_subdivision_preserves_response_and_model(self):
        structure = beam(7.0, cantilever=True)
        add_load(structure, type="distributed", element="beam", wz=-6.0)
        saved = deepcopy(structure)
        coarse, _ = reference.solve(structure, {"D": 1}, [])
        refined, checks = reference.solve(structure, {"D": 1}, [station(x / 10) for x in range(71)])
        for component in ("uz", "ry"):
            self.assert_close(refined(at_node("b"), component), coarse(at_node("b"), component))
        self.assert_close(refined(at_node("b"), "uz"), -6 * 7**4 / (8 * E * IY))
        self.assert_close(refined(at_node("a"), "Fz"), 42.0)
        self.assertEqual(structure, saved)
        self.assert_equilibrium(checks)

    def test_endpoint_one_ulp_below_geometric_length_does_not_create_segment(self):
        length, load = 4.337049688440288, 17.0
        structure = beam(length, cantilever=True)
        add_load(structure, type="nodal", node="b", fz=-load)
        exact = station(length)
        adjacent = station(math.nextafter(length, 0.0))
        exact_value, exact_checks = reference.solve(structure, {"D": 1}, [exact])
        for locations in ([adjacent], [adjacent, exact]):
            with self.subTest(requested_positions=[item["positionM"] for item in locations]):
                value, checks = reference.solve(structure, {"D": 1}, locations)
                self.assertEqual(checks["dofs"], exact_checks["dofs"])
                self.assertEqual(checks["dofs"], 12)
                self.assert_close(value(adjacent, "uz"), -load * length**3 / (3 * E * IY))
                self.assert_close(value(adjacent, "ry"), load * length**2 / (2 * E * IY))
                for component in ("uz", "ry", "V3", "M2"):
                    self.assert_close(value(adjacent, component), exact_value(exact, component))
                self.assert_equilibrium(checks)

    def test_roundoff_equivalent_point_load_and_stations_preserve_both_sides(self):
        load = 10.0
        for point in (0.3, 0.1 + 0.2):
            with self.subTest(load_position=point):
                structure = beam(4.0, cantilever=True)
                add_load(structure, type="point", element="beam", position=point, fz=-load)
                locations = [station(x, side) for x in (0.3, 0.1 + 0.2)
                             for side in ("left", "right")]
                value, checks = reference.solve(structure, {"D": 1}, locations)
                self.assertEqual(checks["dofs"], 18)
                self.assertEqual(checks["observationNodes"], 1)
                self.assert_close(value(at_node("a"), "Fz"), load)
                for location in locations:
                    self.assert_close(value(location, "V3"), load if location["side"] == "left" else 0.0)
                    self.assert_close(value(location, "M2"), 0.0)
                    self.assert_close(value(location, "uz"), -load * 0.3**3 / (3 * E * IY))
                    self.assert_close(value(location, "ry"), load * 0.3**2 / (2 * E * IY))
                self.assert_equilibrium(checks)


class RejectUnsupportedAndInvalidModels(unittest.TestCase):
    def assert_rejected(self, structure, factors=None, stations=None):
        with self.assertRaises((ValueError, NotImplementedError)):
            reference.solve(structure, {"D": 1} if factors is None else factors,
                            [] if stations is None else stations)

    def test_unsupported_analysis_physics_are_never_silently_ignored(self):
        for control in ("self_weight", "rigid_floor", "p_delta", "rigid_offsets", "construction_stage"):
            with self.subTest(control=control):
                structure = beam()
                structure["analysis_control"][control] = True
                self.assert_rejected(structure)

    def test_unsupported_element_and_load_types_rejected(self):
        for element_type in ("shell", "cable", "solid"):
            with self.subTest(element_type=element_type):
                structure = beam()
                structure["elements"][0]["type"] = element_type
                self.assert_rejected(structure)
        for load_type in ("temperature", "prestress", "settlement"):
            with self.subTest(load_type=load_type):
                structure = beam()
                add_load(structure, type=load_type, element="beam", value=5.0)
                self.assert_rejected(structure)

    def test_member_release_is_not_treated_as_rigid_connection(self):
        structure = beam(cantilever=True)
        structure["elements"][0]["releases"] = [False] * 11 + [True]
        self.assert_rejected(structure)

    def test_unknown_case_factor_rejected(self):
        self.assert_rejected(beam(), factors={"missing": 1.0})

    def test_unknown_and_nodal_local_load_frames_are_rejected(self):
        for load_type in ("nodal", "point", "distributed"):
            frames = ("element", "element-local ", "LOCAL", "world", "", None)
            if load_type == "nodal":
                frames += ("local", "element-local")
            for frame in frames:
                with self.subTest(load_type=load_type, frame=frame):
                    structure = beam(cantilever=True, dimension="3d")
                    if load_type == "nodal":
                        add_load(structure, type=load_type, node="b", fz=-5.0)
                    elif load_type == "point":
                        add_load(structure, type=load_type, element="beam", position=2.0, fz=-5.0)
                    else:
                        add_load(structure, type=load_type, element="beam", wz=-5.0)
                    structure["load_cases"][0]["loads"][0]["reference_frame"] = frame
                    with self.assertRaisesRegex(ValueError, "Unsupported load reference_frame"):
                        reference.solve(structure, {"D": 1}, [])

    def test_invalid_station_or_load_extent_rejected(self):
        for location in (station(-0.1), station(6.1), station(2.0, "average"),
                         station(2.0, member="missing")):
            with self.subTest(location=location):
                self.assert_rejected(beam(), stations=[location])
        for start, end in ((-0.1, 2.0), (2.0, 6.1), (4.0, 3.0)):
            with self.subTest(start=start, end=end):
                structure = beam()
                add_load(structure, type="distributed", element="beam", start=start, end=end, wz=-3.0)
                self.assert_rejected(structure)

    def test_nonfinite_input_values_rejected(self):
        for invalid in (float("nan"), float("inf")):
            with self.subTest(invalid=invalid):
                structure = beam()
                structure["materials"][0]["E"] = invalid
                self.assert_rejected(structure)
                self.assert_rejected(beam(), factors={"D": invalid})
                structure = beam()
                add_load(structure, type="distributed", element="beam", wz=invalid)
                self.assert_rejected(structure)

    def test_unrestrained_frame_is_rejected_even_without_load(self):
        for loaded in (False, True):
            with self.subTest(loaded=loaded):
                structure = beam()
                for item in structure["nodes"]:
                    item["restraints"] = list(PLANAR_FREE)
                if loaded:
                    add_load(structure, type="nodal", node="b", fz=-10.0)
                self.assert_rejected(structure)

    def test_transverse_truss_mechanism_is_rejected(self):
        structure = beam(cantilever=True)
        structure["elements"][0]["type"] = "truss"
        add_load(structure, type="nodal", node="b", fz=-5.0)
        self.assert_rejected(structure)


if __name__ == "__main__":
    unittest.main()
