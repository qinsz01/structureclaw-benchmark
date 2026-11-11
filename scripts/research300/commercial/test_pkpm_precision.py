"""The engineering policy must preserve raw truth and canonical zero terms."""
import copy
import hashlib
import importlib
import json
from pathlib import Path
import os
import shutil
import tempfile
import unittest

try:
    precision = importlib.import_module('scripts.research300.commercial.pkpm_precision')
except ModuleNotFoundError:
    precision = None


class CanonicalPrecision(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(precision, 'The precision-certificate implementation is missing')

    def parameters(self):
        return dict(length=2., E=12., G=36., A=1.2, J=1., Iy=1., Iz=1.)

    def test_zero_displacements_do_not_remove_structural_terms(self):
        terms, labels = precision.endpoint_terms('M3', 0, [0.] * 12, [], **self.parameters())
        self.assertEqual(terms, [0., 0., 0., 0.])
        self.assertEqual(labels, ['k[5,1]*d[1]', 'k[5,5]*d[5]',
                                  'k[5,7]*d[7]', 'k[5,11]*d[11]'])
        metadata = precision.precision_metadata(terms, 'kN.m')
        self.assertEqual(metadata['structuralTermCount'], 4)
        self.assertEqual(metadata['absoluteAllowance'], 0.)

    def test_end_signs_and_fixed_end_load_are_canonical(self):
        d = [0.] * 12
        d[1], d[7], d[11] = .1, .2, .3
        terms, _ = precision.endpoint_terms('M3', 0, d, [[0., 6., 0.]], **self.parameters())
        # phi=1, start moment row is [9,15,-9,3]; f_start=wy*L^2/12=2.
        for actual, expected in zip(terms, [-.9, 0., 1.8, -.9, 2.]):
            self.assertAlmostEqual(actual, expected)
        self.assertEqual(len(terms), 5)
        far, _ = precision.endpoint_terms('M3', 1, d, [[0., 6., 0.]], **self.parameters())
        for actual, expected in zip(far, [.9, 0., -1.8, 4.5, 2.]):
            self.assertAlmostEqual(actual, expected)

    def test_multiple_loads_remain_separate_even_when_they_cancel(self):
        terms, _ = precision.endpoint_terms('V2', 0, [0.] * 12,
                                             [[0., 6., 0.], [0., -6., 0.]], **self.parameters())
        self.assertEqual(terms[-2:], [-6., 6.])
        self.assertEqual(len(terms), 6)
        self.assertEqual(precision.precision_metadata(terms, 'kN')['recoveryScale'], 12.)

    def test_policy_is_independent_of_observed_error_and_keeps_small_terms(self):
        m = precision.precision_metadata([1., -1., 0., 1e-200], 'kN.m')
        self.assertEqual(m['structuralTermCount'], 4)
        self.assertEqual(m['terms'][-1], 1e-200)
        self.assertAlmostEqual(m['absoluteAllowance'], 8.344653750215545e-7, places=20)
        self.assertFalse(m['nativeArithmeticBound'])
        self.assertTrue(m['acceptanceRegionChanges'])

    def test_nonfinite_and_missing_displacements_fail_closed(self):
        for terms in ([], [float('nan')], [float('inf')]):
            with self.assertRaises(ValueError):
                precision.precision_metadata(terms, 'kN')
        d = [0.] * 12
        d[1] = -99999.
        with self.assertRaises(ValueError):
            precision.endpoint_terms('M3', 0, d, [], **self.parameters())


class CapturedEvidence(unittest.TestCase):
    ROOT = Path(__file__).resolve().parents[3]
    EVIDENCE = Path(os.environ.get('SCLAW_BENCH_ARCHIVE', ROOT)).expanduser() / 'docs/implementation/reviews/commercial-calibration-20261015/native-cases/pkpm/final-native-candidates'

    def setUp(self):
        self.assertIsNotNone(precision, 'The precision-certificate implementation is missing')
        # The repository's archived, hash-bound native run is the integration fixture.
        self.corpus = self.ROOT / 'corpora/research-300/cases'
        self.candidate = self.EVIDENCE / 'candidates/final03/STD-089/native-reference.json'
        self.assertTrue(self.candidate.exists(), 'Archived captured native fixture is required')

    def test_all_endpoint_requests_get_certificates_without_changing_truth(self):
        old = json.loads(self.candidate.read_text())
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'new'
            result = precision.generate(self.EVIDENCE, self.corpus, self.candidate, output)
            new = json.loads((output / 'native-reference.json').read_text())
            certpath = output / 'precision/certificate.json'
            cert = json.loads(certpath.read_text())
            digest = hashlib.sha256(certpath.read_bytes()).hexdigest()
            self.assertEqual(result['precisionQuantityCount'], 120)
            self.assertEqual(len(cert['quantities']), 120)
            for before, after in zip(old['states'][0]['quantities'], new['states'][0]['quantities']):
                restored = copy.deepcopy(after)
                metadata = restored.pop('engineeringPrecision', None)
                self.assertEqual(restored, before)
                if before['location']['kind'] == 'member':
                    self.assertEqual(metadata['certificateSha256'], digest)
                else:
                    self.assertIsNone(metadata)
            self.assertFalse(new['accepted'])
            self.assertFalse(new['nativeVerified'])
            self.assertEqual(cert['oldCandidateSha256'], hashlib.sha256(self.candidate.read_bytes()).hexdigest())
            m3 = next(q for q in cert['quantities'] if q['id'] == 'case-D-member-x0-0-1-s0-right-M3')
            self.assertAlmostEqual(m3['precision']['absoluteAllowance'], 3.77553940777974e-7, places=20)
            self.assertNotIn('certificateSha256', m3['precision'])

    def test_modified_candidate_value_is_rejected_before_output(self):
        with tempfile.TemporaryDirectory() as temp:
            bad = Path(temp) / 'bad.json'
            d = json.loads(self.candidate.read_text())
            next(q for q in d['states'][0]['quantities'] if q['location']['kind'] == 'member')['value'] += 1
            bad.write_text(json.dumps(d))
            output = Path(temp) / 'new'
            with self.assertRaisesRegex(ValueError, 'candidate|native|Native'):
                precision.generate(self.EVIDENCE, self.corpus, bad, output)
            self.assertFalse(output.exists())

    def copied_evidence(self, root):
        destination = root / 'evidence'
        manifest = self.EVIDENCE / 'pkpm-candidate-evidence-manifest.json'
        entry = next(e for e in json.loads(manifest.read_text())['runs'] if e['caseId'] == 'STD-089')
        for relative in [manifest.name] + [r['path'] for r in entry['artifacts'].values()] + [r['path'] for r in entry['stages']]:
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.EVIDENCE / relative, target)
        return destination, entry

    def test_changed_raw_displacement_hash_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            evidence, entry = self.copied_evidence(Path(temp))
            path = evidence / entry['artifacts']['DISP.SAT']['path']
            data = bytearray(path.read_bytes())
            data[0] ^= 1
            path.write_bytes(data)
            output = Path(temp) / 'new'
            with self.assertRaisesRegex(ValueError, 'SHA|hash'):
                precision.generate(evidence, self.corpus, self.candidate, output)
            self.assertFalse(output.exists())

    def test_duplicate_quantity_identity_cannot_replace_another_request(self):
        with tempfile.TemporaryDirectory() as temp:
            bad = Path(temp) / 'bad.json'
            d = json.loads(self.candidate.read_text())
            rows = d['states'][0]['quantities']
            rows[1] = copy.deepcopy(rows[0])
            bad.write_text(json.dumps(d))
            with self.assertRaisesRegex(ValueError, 'identity|request|duplicate'):
                precision.generate(self.EVIDENCE, self.corpus, bad, Path(temp) / 'new')


if __name__ == '__main__':
    unittest.main()
