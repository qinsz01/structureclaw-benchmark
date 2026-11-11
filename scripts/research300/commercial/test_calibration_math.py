"""Independent hand calculations for the local cantilever calibration oracle.

No benchmark solver or commercial adapter is imported.  The numerical fixture
has EA=4,000,000 kN, EIy=16,000 kN m², EIz=4,000 kN m² and GJ=800 kN m².
Its small integer tip loads give the hand-integrated values below.
"""

import importlib.util
import math
from pathlib import Path
import unittest


MODULE_PATH = Path(__file__).with_name("calibration_math.py")
if MODULE_PATH.exists():
    SPEC = importlib.util.spec_from_file_location("calibration_math", MODULE_PATH)
    CALIBRATION = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(CALIBRATION)
else:
    CALIBRATION = None


class CantileverCalibrationTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(CALIBRATION, "Independent calibration module is missing")
        self.properties = dict(length=2.0, E=200e6, G=80e6,
                               A=.02, Iy=8e-5, Iz=2e-5, J=1e-5)
        self.loads = dict(Fx=10., Fy=12., Fz=-9., Mx=8., My=-16., Mz=20.)

    def solve(self, *, timoshenko=False, properties=None, loads=None, **extra):
        arguments = dict(self.properties if properties is None else properties)
        arguments.update(self.loads if loads is None else loads)
        arguments.update(extra)
        function = (CALIBRATION.timoshenko_cantilever if timoshenko
                    else CALIBRATION.euler_bernoulli_cantilever)
        return function(**arguments)

    def assert_components(self, actual, expected):
        self.assertEqual(actual.keys(), expected.keys())
        for key, value in expected.items():
            with self.subTest(component=key):
                self.assertTrue(math.isclose(actual[key], value, rel_tol=2e-13,
                                             abs_tol=1e-15), (actual[key], value))

    def test_each_load_has_hand_calculated_magnitude_and_right_hand_sign(self):
        # A swapped inertia, force/moment sign or kN/MPa conversion breaks this.
        fixtures = (
            ("Fx", 10., (5e-6, 0., 0., 0., 0., 0.), (-10., 0., 0., 0., 0., 0.)),
            ("Fy", 12., (0., .008, 0., 0., 0., .006), (0., -12., 0., 0., 0., -24.)),
            ("Fz", -9., (0., 0., -.0015, 0., .001125, 0.), (0., 0., 9., 0., -18., 0.)),
            ("Mx", 8., (0., 0., 0., .02, 0., 0.), (0., 0., 0., -8., 0., 0.)),
            ("My", -16., (0., 0., .002, 0., -.002, 0.), (0., 0., 0., 0., 16., 0.)),
            ("Mz", 20., (0., .01, 0., 0., 0., .01), (0., 0., 0., 0., 0., -20.)),
        )
        for axis, magnitude, displacement, reaction in fixtures:
            with self.subTest(load=axis):
                loads = dict.fromkeys(self.loads, 0.)
                loads[axis] = magnitude
                result = self.solve(loads=loads)
                self.assert_components(result["displacement"],
                                       dict(zip(("ux", "uy", "uz", "rx", "ry", "rz"), displacement)))
                self.assert_components(result["reaction"], dict(zip(self.loads, reaction)))

    def test_combined_loads_obey_independent_hand_integral(self):
        result = self.solve()
        self.assert_components(result["displacement"],
                               dict(ux=5e-6, uy=.018, uz=.0005, rx=.02, ry=-.000875, rz=.016))
        self.assert_components(result["reaction"],
                               dict(Fx=-10., Fy=-12., Fz=9., Mx=-8., My=-2., Mz=-44.))

    def test_finite_directional_shear_area_changes_only_transverse_displacement(self):
        # Additional shear movements are +0.030 mm and -0.045 mm, respectively.
        result = self.solve(timoshenko=True, Asy=.01, Asz=.005)
        self.assert_components(result["displacement"],
                               dict(ux=5e-6, uy=.01803, uz=.000455, rx=.02, ry=-.000875, rz=.016))
        self.assert_components(result["reaction"],
                               dict(Fx=-10., Fy=-12., Fz=9., Mx=-8., My=-2., Mz=-44.))

    def test_pure_tip_moments_have_no_transverse_shear_deformation(self):
        loads = dict(Fx=0., Fy=0., Fz=0., Mx=8., My=-16., Mz=20.)
        expected = dict(ux=0., uy=.01, uz=.002, rx=.02, ry=-.002, rz=.01)
        for areas in ((.01, .005), (.001, .05)):
            self.assert_components(self.solve(timoshenko=True, loads=loads,
                                              Asy=areas[0], Asz=areas[1])["displacement"], expected)

    def test_reversed_loading_reverses_all_displacements_and_reactions(self):
        reverse = {key: -value for key, value in self.loads.items()}
        for shear in ({}, dict(timoshenko=True, Asy=.01, Asz=.005)):
            positive = self.solve(**shear)
            negative = self.solve(loads=reverse, **shear)
            for field in ("displacement", "reaction"):
                self.assert_components(negative[field],
                                       {key: -value for key, value in positive[field].items()})

    def test_support_balances_full_force_and_moment_about_fixed_end(self):
        # r=(2,0,0) m; independently, r cross F=(0,18,24) kN m.
        for shear in ({}, dict(timoshenko=True, Asy=.01, Asz=.005)):
            reaction = self.solve(**shear)["reaction"]
            residuals = (reaction["Fx"] + 10., reaction["Fy"] + 12.,
                         reaction["Fz"] - 9., reaction["Mx"] + 8.,
                         reaction["My"] - 16. + 18., reaction["Mz"] + 20. + 24.)
            self.assertEqual(residuals, (0.,) * 6)

    def test_doubling_length_distinguishes_cubic_bending_and_linear_shear(self):
        # For Fy=12 kN at L=4m: v=64 mm, rz=24 mrad, shear=0.060 mm.
        properties = dict(self.properties, length=4.)
        loads = dict(Fx=0., Fy=12., Fz=0., Mx=0., My=0., Mz=0.)
        result = self.solve(properties=properties, loads=loads)
        self.assert_components(result["displacement"],
                               dict(ux=0., uy=.064, uz=0., rx=0., ry=0., rz=.024))
        shear_result = self.solve(properties=properties, loads=loads,
                                  timoshenko=True, Asy=.01, Asz=.005)
        self.assert_components(shear_result["displacement"],
                               dict(ux=0., uy=.06406, uz=0., rx=0., ry=0., rz=.024))
        self.assertEqual(shear_result["reaction"]["Mz"], -48.)

    def test_geometric_similarity_preserves_physical_dimensions(self):
        # A tenfold specimen has A*100 and I,J*10000. Under fixed forces,
        # translations scale by 1/10 and rotations by 1/100, including shear.
        properties = dict(length=20., E=200e6, G=80e6, A=2., Iy=.8, Iz=.2, J=.1)
        loads = dict(Fx=10., Fy=12., Fz=-9., Mx=0., My=0., Mz=0.)
        result = self.solve(properties=properties, loads=loads,
                            timoshenko=True, Asy=1., Asz=.5)
        self.assert_components(result["displacement"],
                               dict(ux=5e-7, uy=.000803, uz=-.0001545,
                                    rx=0., ry=.00001125, rz=.00006))

    def test_tip_moment_scaling_with_length_and_material_stiffness(self):
        properties = dict(self.properties, length=4., E=600e6, G=240e6)
        loads = dict(Fx=0., Fy=0., Fz=0., Mx=12., My=-24., Mz=30.)
        self.assert_components(self.solve(properties=properties, loads=loads)["displacement"],
                               dict(ux=0., uy=.02, uz=.004, rx=.02, ry=-.002, rz=.01))

    def test_zero_loads_produce_zero_response(self):
        result = self.solve(loads=dict.fromkeys(self.loads, 0.))
        self.assertEqual(set(result["displacement"].values()), {0.})
        self.assertEqual(set(result["reaction"].values()), {0.})

    def test_result_retains_explicit_physics_and_si_inputs(self):
        result = self.solve()
        self.assertEqual(result["theory"], "Euler-Bernoulli")
        self.assertEqual(result["inputs"], dict(self.properties, **self.loads))
        self.assertEqual(result["units"], dict(length="m", force="kN", moment="kN*m",
                                               modulus="kN/m^2", area="m^2",
                                               inertia="m^4", rotation="rad"))
        shear_result = self.solve(timoshenko=True, Asy=.01, Asz=.005)
        self.assertEqual(shear_result["theory"], "Timoshenko")
        self.assertEqual(shear_result["inputs"], dict(self.properties, **self.loads, Asy=.01, Asz=.005))

    def test_shear_areas_are_required_explicitly_and_not_an_eb_option(self):
        with self.assertRaises(TypeError):
            self.solve(timoshenko=True)
        with self.assertRaises(TypeError):
            self.solve(timoshenko=True, Asy=.01)
        with self.assertRaises(TypeError):
            self.solve(Asy=.01, Asz=.005)

    def test_invalid_geometry_and_material_values_are_rejected(self):
        for name in self.properties:
            for bad in (0., -1., math.nan, math.inf, -math.inf, True, "2", None):
                with self.subTest(property=name, value=bad):
                    with self.assertRaises(ValueError):
                        self.solve(properties=dict(self.properties, **{name: bad}))

    def test_invalid_shear_areas_are_rejected_without_silent_eb_fallback(self):
        for name in ("Asy", "Asz"):
            for bad in (0., -1., math.nan, math.inf, True, "2", None):
                arguments = dict(Asy=.01, Asz=.005)
                arguments[name] = bad
                with self.subTest(property=name, value=bad):
                    with self.assertRaises(ValueError):
                        self.solve(timoshenko=True, **arguments)

    def test_nonfinite_and_nonnumeric_loads_are_rejected(self):
        for name in self.loads:
            for bad in (math.nan, math.inf, -math.inf, True, "2", None):
                with self.subTest(load=name, value=bad):
                    with self.assertRaises(ValueError):
                        self.solve(loads=dict(self.loads, **{name: bad}))

    def test_numeric_overflow_and_underflow_cannot_escape_as_valid_response(self):
        for properties in (dict(self.properties, length=1e308),
                           dict(self.properties, E=1e-300, Iy=1e-300),
                           dict(self.properties, E=1e308, A=1e308)):
            with self.subTest(properties=properties):
                with self.assertRaises(ValueError):
                    self.solve(properties=properties)


if __name__ == "__main__":
    unittest.main()
