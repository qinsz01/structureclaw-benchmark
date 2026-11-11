"""Independent sign, provenance and precision controls for the diagnostic."""
import copy
import hashlib
import json
import unittest

from diagnose_pkpm_precision import (Evidence, endpoint_location, f32, recovery,
                                     strict, sums, variant_model)


def beam():
    return {'coordinate_system': {'dimension': '3d'},
            'metadata': {'elementReferenceVectors': {'e': [0., 0., 1.]}},
            'nodes': [{'id': 'a', 'x': 0., 'y': 0., 'z': 0., 'restraints': [True] * 6},
                      {'id': 'b', 'x': 2., 'y': 0., 'z': 0., 'restraints': [True] * 6}],
            'elements': [{'id': 'e', 'type': 'beam', 'nodes': ['a', 'b'], 'section': 's', 'material': 'm'}],
            'materials': [{'id': 'm', 'E': 200000., 'G': 80000., 'nu': .25}],
            'sections': [{'id': 's', 'properties': {'A': .01, 'J': .00001, 'Iy': .00002, 'Iz': .00003}}],
            'load_cases': [{'id': 'D', 'loads': []}]}


def native(ux=0.):
    return {'caseResults': {'D': {'displacements': {
        n: {d: ux if n == 'b' and d == 'ux' else 0. for d in ('ux', 'uy', 'uz', 'rx', 'ry', 'rz')}
        for n in ('a', 'b')}}}}


def request(location, component):
    return {'selection': {'kind': 'case', 'id': 'D'}, 'location': location, 'component': component}


class PrecisionDiagnosticTests(unittest.TestCase):
    def test_cancellation_does_not_preserve_double_result(self):
        value = sums([1e8, 1., -1e8])
        self.assertEqual(value['recoveredF64'], 1.)
        self.assertEqual(value['sequentialF32Sum'], 0.)
        self.assertEqual(value['recoveryScale'], 200000001.)

    def test_float32_wrong_answer_still_fails_strict_check(self):
        tolerance = {'absolute': 1e-8, 'relative': 1e-6}
        # Being exactly representable by the native output type is not evidence
        # that a force is correct, and grants no acceptance allowance.
        self.assertEqual(f32(.5), .5)
        self.assertFalse(strict(.5, 1., tolerance)['pass'])
        self.assertFalse(strict(-.5, .5, tolerance)['pass'])
        with self.assertRaises(ValueError):
            strict(float('nan'), 0., tolerance)

    def test_input_experiments_preserve_public_input_and_materials(self):
        source = beam()
        original = copy.deepcopy(source)
        source['nodes'][1]['x'] = 3.6
        changed = variant_model(source, 'section-geometry-f32')
        self.assertEqual(changed['materials'], source['materials'])
        self.assertNotEqual(changed['nodes'][1]['x'], source['nodes'][1]['x'])
        self.assertEqual(source['sections'], original['sections'])
        self.assertEqual(source['nodes'][1]['x'], 3.6)
        with self.assertRaises(ValueError):
            variant_model(source, 'choose-the-closest-result')

    def test_round_geometry_maps_only_real_endpoint(self):
        source = beam()
        source['nodes'][1]['x'] = 3.6
        changed = variant_model(source, 'geometry-f32')
        location = {'kind': 'member', 'id': 'e', 'positionM': 3.6, 'side': 'left'}
        self.assertEqual(endpoint_location(source, changed, location)['positionM'], f32(3.6))
        with self.assertRaises(ValueError):
            endpoint_location(source, changed, {**location, 'positionM': 1.8})

    def test_axial_extension_has_same_signed_cut_at_both_ends(self):
        model = beam()
        # EA/L * delta = 200e6 * .01 / 2 * .001 = 1000 kN.
        for position, side in ((0., 'right'), (2., 'left')):
            q = request({'kind': 'member', 'id': 'e', 'positionM': position, 'side': side}, 'N')
            self.assertAlmostEqual(recovery(model, q, native(.001))['recoveredFromNativeDisp'], 1000.)
        for nid, expected in (('a', -1000.), ('b', 1000.)):
            q = request({'kind': 'node', 'id': nid}, 'Fx')
            self.assertAlmostEqual(recovery(model, q, native(.001))['recoveredFromNativeDisp'], expected)

    def test_fixed_beam_uniform_load_reactions_match_analytic_solution(self):
        model = beam()
        model['load_cases'][0]['loads'] = [{'type': 'distributed', 'element': 'e', 'wz': -10., 'reference_frame': 'global'}]
        for nid, moment in (('a', -10. / 3.), ('b', 10. / 3.)):
            for component, expected in (('Fz', 10.), ('My', moment)):
                q = request({'kind': 'node', 'id': nid}, component)
                self.assertAlmostEqual(recovery(model, q, native())['recoveredFromNativeDisp'], expected)

    def test_support_applied_load_is_subtracted_from_reaction(self):
        model = beam()
        model['load_cases'][0]['loads'] = [{'type': 'nodal', 'node': 'a', 'fx': 3.}]
        q = request({'kind': 'node', 'id': 'a'}, 'Fx')
        self.assertAlmostEqual(recovery(model, q, native())['recoveredFromNativeDisp'], -3.)

    def test_evidence_tampering_is_rejected(self):
        data = json.dumps({'value': 1.}).encode()
        digest = hashlib.sha256(data).hexdigest()
        class Archive:
            def read(self, name):
                return data + b' '
        evidence = Evidence(Archive(), {'source.json': {'path': 'source.json', 'sha256': digest, 'bytes': len(data)}})
        with self.assertRaises(ValueError):
            evidence.json('source.json')
        self.assertEqual(evidence.used, {})


if __name__ == '__main__':
    unittest.main()
