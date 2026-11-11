"""Independent analytical and retained-response regressions; no solver is run."""
import importlib.util
import pathlib
import unittest

HERE = pathlib.Path(__file__).resolve().parent


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, file)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


audit = module('native_audit_constitutive_subject', HERE / 'audit_native_evidence.py')
fixtures = module('native_audit_constitutive_fixture', HERE / 'test_native_audit.py')


class ConstitutiveAnalyticalTests(unittest.TestCase):
    def setUp(self):
        self.axes = [[1., 0., 0.], [0., 1., 0.], [0., 0., 1.]]
        self.properties = {'E': 200., 'A': 3., 'G': 80., 'J': 7., 'Iy': 5., 'Iz': 11.}

    def response(self, u, loads=(), truss=False, axes=None):
        return audit.elastic_local_response(u, axes or self.axes, self.properties, 2., truss, loads)

    def assertVector(self, actual, expected):
        self.assertEqual(len(actual), len(expected))
        for a, b in zip(actual, expected):
            self.assertAlmostEqual(a, b, places=9)

    def test_axial_extension_obeys_ea_over_length(self):
        u = [0.] * 12; u[6] = .01
        self.assertVector(self.response(u), [-3., 0., 0., 0., 0., 0., 3., 0., 0., 0., 0., 0.])

    def test_torsion_obeys_gj_over_length(self):
        u = [0.] * 12; u[9] = .02
        self.assertVector(self.response(u), [0., 0., 0., -5.6, 0., 0., 0., 0., 0., 5.6, 0., 0.])

    def test_independent_bending_planes_preserve_rotation_sign(self):
        for index, expected in [(7, [0., -330., 0., 0., 0., -330., 0., 330., 0., 0., 0., -330.]),
                                (8, [0., 0., -150., 0., 150., 0., 0., 0., 150., 0., 150., 0.])]:
            u = [0.] * 12; u[index] = .1
            self.assertVector(self.response(u), expected)

    def test_midspan_point_load_has_hermite_fixed_end_actions(self):
        self.assertVector(self.response([0.] * 12, [{'globalForce': [0., 4., 0.], 'fraction': .5}]),
                          [0., -2., 0., 0., 0., -1., 0., -2., 0., 0., 0., 1.])

    def test_inclined_truss_uses_projected_strain(self):
        axes = [[0., .6, .8], [1., 0., 0.], [0., .8, -.6]]
        u = [0.] * 12; u[7] = .006; u[8] = .008
        self.assertVector(self.response(u, truss=True, axes=axes),
                          [-3., 0., 0., 0., 0., 0., 3., 0., 0., 0., 0., 0.])

    def test_rigid_translation_and_rotation_have_zero_elastic_force(self):
        # Rotation (0,.02,.03) about the first end of a two-metre x-axis beam.
        u = [1., 2., 3., 0., .02, .03, 1., 2.06, 2.96, 0., .02, .03]
        self.assertVector(self.response(u), [0.] * 12)


class RetainedConstitutiveTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.AuditTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def test_rehashed_unrequested_free_rotation_is_rejected(self):
        f = self.fixture
        raw = f.read('native-raw-responses.json')
        raw['runs'][0]['responses']['nodes']['N0']['displacement'][4] = 1.
        f.write('native-raw-responses.json', raw); f.rehash()
        run, report = f.cli()
        self.assertEqual(run.returncode, 1)
        self.assertFalse(report['valid'])
        self.assertTrue(any('constitutive' in e['check'] for e in report['cases'][0]['errors']))


if __name__ == '__main__':
    unittest.main()
