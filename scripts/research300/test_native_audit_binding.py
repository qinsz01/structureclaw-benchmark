"""Native evidence completeness regressions using retained, isolated fixtures.

No solver is invoked. NATIVE_AUDIT_EVIDENCE_ROOT and NATIVE_AUDIT_BINARY
select the same evidence and binary as test_native_audit.py.
"""
import copy
import unittest

if __package__:
    from . import test_native_audit as fixture
else:
    import test_native_audit as fixture


class NativeAuditBindingTests(unittest.TestCase):
    # Reuse the fixture without discovering its original tests a second time.
    setUp = fixture.AuditTests.setUp
    read = fixture.AuditTests.read
    write = fixture.AuditTests.write
    rehash = fixture.AuditTests.rehash
    cli = fixture.AuditTests.cli

    def assert_failed_case_report(self):
        process, report = self.cli()
        self.assertEqual(process.returncode, 1, process.stderr)
        self.assertIsNotNone(report, "Invalid evidence must retain a failed per-case report: " + process.stderr)
        self.assertIs(report['valid'], False)
        self.assertEqual(report['summary']['failed'], 1)
        self.assertEqual([case['caseId'] for case in report['cases']], ['STD-003'])
        case = report['cases'][0]
        self.assertIs(case['pass'], False)
        self.assertIs(case['nativeVerified'], False)
        self.assertIs(case['accepted'], False)
        self.assertTrue(case['errors'], 'Failed cases must explain the evidence failure')

    def test_extra_reference_state_is_rejected(self):
        reference = self.read('native-opensees-reference.json')
        extra = copy.deepcopy(reference['states'][0])
        extra['state'] = 999
        reference['states'].append(extra)
        self.write('native-opensees-reference.json', reference)
        self.assert_failed_case_report()

    def test_reference_state_model_must_match_authored_state(self):
        reference = self.read('native-opensees-reference.json')
        reference['states'][0]['model'] = 'not-an-authored-model.json'
        self.write('native-opensees-reference.json', reference)
        self.assert_failed_case_report()

    def test_nested_reference_checks_must_match_retained_checks(self):
        reference = self.read('native-opensees-reference.json')
        reference['states'][0]['checks'][0]['equilibriumPassed'] = False
        self.write('native-opensees-reference.json', reference)
        self.assert_failed_case_report()

    def test_malformed_solver_retains_failed_case_report(self):
        for name in ('native-opensees-reference.json', 'native-solver-receipt.json'):
            document = self.read(name)
            document['solver'] = []
            self.write(name, document)
        self.rehash()
        self.assert_failed_case_report()

    def test_extra_raw_state_retains_failed_case_report(self):
        raw = self.read('native-raw-responses.json')
        extra = copy.deepcopy(raw['runs'][0])
        extra['state'] = 999
        raw['runs'].append(extra)
        self.write('native-raw-responses.json', raw)
        self.rehash()
        self.assert_failed_case_report()


if __name__ == '__main__':
    unittest.main()
