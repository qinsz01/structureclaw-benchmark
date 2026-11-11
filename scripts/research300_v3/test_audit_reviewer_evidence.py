import copy
import unittest
from scripts.research300_v3.audit_reviewer_evidence import summarize


class EvidenceSummaryTests(unittest.TestCase):
    def setUp(self):
        self.manifest = {'cases': [{'id': 'case1', 'turns': [{'id': 't1'}, {'id': 't2'}],
                                   'family': 'INT', 'level': 'L3', 'engine': 'OpenSees', 'analysis': 'scenario',
                                   'origin': 'original', 'split': 'test', 'topologyFingerprint': 'topology'}]}
        self.grade = {'rows': [{'caseId': 'case1', 'turnId': 't1', 'passed': True},
                               {'caseId': 'case1', 'turnId': 't2', 'passed': False}]}

    def test_partial_turn_success_is_not_complete_case_success_or_formal_evidence(self):
        result = summarize(self.manifest, self.grade)
        self.assertEqual((result['cases'], result['turns'], result['passedCases'], result['passedTurns']), (1, 2, 0, 1))
        self.assertFalse(result['formalComparisonScore'])
        self.assertEqual(result['groups']['split']['test']['passedTurns'], 1)

    def test_missing_duplicate_and_unknown_outcomes_cannot_shrink_denominator(self):
        for rows in [self.grade['rows'][:1], self.grade['rows'] * 2,
                     self.grade['rows'] + [{'caseId': 'unknown', 'turnId': 't1', 'passed': True}]]:
            with self.assertRaises(ValueError):
                summarize(self.manifest, {'rows': rows})

    def test_unresolved_rows_are_not_silently_counted_as_candidate_failure(self):
        grade = copy.deepcopy(self.grade)
        grade['rows'][1]['passed'] = None
        with self.assertRaises(ValueError):
            summarize(self.manifest, grade)


if __name__ == '__main__':
    unittest.main()
