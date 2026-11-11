"""Native reference evidence must not alter authored multimodal reproducibility."""
from pathlib import Path
import unittest
from mm_b_reproducibility import is_generated_evidence


class EvidenceClassification(unittest.TestCase):
    def test_only_reserved_commercial_evidence_namespace_is_generated(self):
        self.assertTrue(is_generated_evidence(Path('native-commercial/evidence/state-1/fea.dat')))
        self.assertTrue(is_generated_evidence(Path('native-commercial/qualification.json')))
        self.assertTrue(is_generated_evidence(Path('independent-reference-matrix-diagnostic.json')))
        self.assertFalse(is_generated_evidence(Path('drawings/fea.dat')))
        self.assertFalse(is_generated_evidence(Path('native-commercial-input/geometry.csv')))
        self.assertFalse(is_generated_evidence(Path('attachments/independent-reference.json')))


if __name__ == '__main__':
    unittest.main()
