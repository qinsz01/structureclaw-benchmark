"""Exercise split archives, failed-score replay and confidential-file exclusion."""
import json
from pathlib import Path
import secrets
import subprocess
import tempfile
import unittest
import zipfile

from .archive_candidate import archive
from .support import ROOT
from .verify_archive import sha
from .verify_candidate_archive import diagnostic_paths, verify


class CandidateArchiveTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.edition, self.work, self.sessions = [self.root / name for name in ('edition', 'work', 'sessions')]
        for folder in (self.edition, self.work, self.sessions):
            folder.mkdir()
        self.write(self.edition / 'manifest.json', {'files': [], 'sutCommit': 'fixture-pinned-commit', 'cases': [
            {'id': 'unanswered', 'split': 'test', 'engine': 'OpenSees', 'turns': [{'id': 't1'}]}]})
        runtime = [ROOT / 'scripts/research300_v3' / name for name in ('run_candidate.py', 'setup_public.py', 'grade_candidate.cjs')]
        runtime += [ROOT / 'scripts/pilot30/service.py', ROOT / 'scripts/research300/codex_trial/commercial.py']
        self.write(self.work / 'candidate-binding.json', {
            'fullSuite': True, 'manifestSha256': sha(self.edition / 'manifest.json'), 'cases': ['unanswered'],
            'model': 'fixture-no-model-calls', 'runnerCommit': 'fixture', 'graderFeedbackDuringRun': False,
            'evaluationCode': {name: sha(ROOT / 'scripts/research300_v3' / name) for name in
                               ('evaluate.cjs', 'qualify.cjs', 'physical.cjs', 'fidelity.cjs')},
            'implementation': {p.name: sha(p) for p in runtime}})
        self.write(self.work / 'execution-summary.json', {'manifestSha256': sha(self.edition / 'manifest.json'),
                                                         'turns': [], 'candidateCalls': 0})
        self.grade = self.root / 'grade.json'
        subprocess.run(['node', str(ROOT / 'scripts/research300_v3/grade_candidate.cjs'),
                        str(self.edition), str(self.work), str(self.grade)], check=True, capture_output=True, timeout=30)

    @staticmethod
    def write(path, value):
        path.write_text(json.dumps(value, indent=2) + '\n')

    def test_replay_preserves_an_uncaptured_failure_and_excludes_private_files(self):
        value = secrets.token_hex(24)
        self.write(self.work / 'remote-setup.json', {'password': value})
        outside = self.root / 'outside.json'
        self.write(outside, {'password': value})
        (self.sessions / 'link-to-outside.json').symlink_to(outside)
        incidental = self.work / 'runs/unanswered/t1/scratch-snapshot/dispatch.json'
        incidental.parent.mkdir(parents=True)
        self.write(incidental, {'note': 'ordinary scratch file, not a model dispatch'})
        nested = self.work / 'solver-jobs/unanswered' / ('a' * 32) / 'native/broker-receipt.json'
        nested.parent.mkdir(parents=True)
        self.write(nested, {'note': 'native artifact, not a trusted broker receipt'})
        output = self.root / 'evidence'
        archive(self.edition, self.work, self.sessions, self.grade, output, part_bytes=16 * 1024)
        result = verify(output, replay=True, timeout=60)
        self.assertTrue(result['allPassed'])
        self.assertGreater(result['volumesVerified'], 1)
        self.assertEqual((result['passedTurns'], result['failedTurns']), (0, 1))
        self.assertEqual(result['actualModelDispatchesRetained'], 0)
        self.assertEqual(result['nativeJobsRetained'], 0)
        self.assertTrue(result['offlineReplay']['byteIdenticalGrade'])
        self.assertFalse(result['candidateModelsInvoked'])
        self.assertFalse(result['nativeSolversInvoked'])
        meta = json.loads((output / 'archive.json').read_text())
        self.assertEqual(meta['compression'], {'method':'deflate','level':1,'lossless':True})
        excluded = {row['path'] for row in meta['excludedFiles']}
        self.assertIn('work/remote-setup.json', excluded)
        self.assertIn('sessions/link-to-outside.json', excluded)

    def test_changed_volume_is_rejected_before_replay(self):
        output = self.root / 'evidence'
        archive(self.edition, self.work, self.sessions, self.grade, output)
        part = output / 'evidence.zip.part001.bin'
        data = bytearray(part.read_bytes())
        data[20] ^= 1
        part.write_bytes(data)
        with self.assertRaisesRegex(ValueError, 'volume checksum differs'):
            verify(output, replay=True)

    def test_first_and_reviewed_grades_replay_from_the_same_archived_answers(self):
        reviewed = self.root / 'reviewed.json'
        subprocess.run(['node', str(ROOT / 'scripts/research300_v3/grade_candidate_v31.cjs'),
                        str(self.edition), str(self.work), str(reviewed)], check=True, capture_output=True, timeout=30)
        output = self.root / 'evidence'
        archive(self.edition, self.work, self.sessions, self.grade, output, reviewed_grade=reviewed)
        result = verify(output, replay=True, timeout=60)
        self.assertTrue(result['offlineReplay']['byteIdenticalGrade'])
        self.assertTrue(result['reviewedOfflineReplay']['byteIdenticalGrade'])
        self.assertTrue(result['reviewedOfflineReplay']['sameOriginalCandidateAnswers'])
        self.assertEqual(result['reviewedOfflineReplay']['failedTurns'], 1)

    def test_reviewed_source_checksum_must_match_executed_revision(self):
        reviewed = self.root / 'reviewed.json'
        subprocess.run(['node', str(ROOT / 'scripts/research300_v3/grade_candidate_v31.cjs'),
                        str(self.edition), str(self.work), str(reviewed)], check=True, capture_output=True, timeout=30)
        value=json.loads(reviewed.read_text());value['reviewedEvaluationCode']['physical-v31.cjs']='0'*64
        self.write(reviewed,value)
        with self.assertRaisesRegex(ValueError,'Reviewed evaluator changed'):
            archive(self.edition,self.work,self.sessions,self.grade,self.root/'evidence',reviewed_grade=reviewed)

    def test_credential_fields_in_regular_json_are_rejected(self):
        self.write(self.work / 'ordinary.json', {'password': secrets.token_hex(24)})
        with self.assertRaisesRegex(ValueError, 'Credential field'):
            archive(self.edition, self.work, self.sessions, self.grade, self.root / 'evidence')

    def test_cached_zip_inspection_rejects_private_nested_paths(self):
        with zipfile.ZipFile(self.work / 'nested.zip.bin', 'w') as bundle:
            bundle.writestr('credentials.json', json.dumps({'password': secrets.token_hex(24)}))
        with self.assertRaisesRegex(ValueError, 'Private file/symlink inside retained ZIP'):
            archive(self.edition, self.work, self.sessions, self.grade, self.root / 'evidence')

    def test_unused_job_with_a_wrong_original_state_seal_is_rejected(self):
        job = self.work / 'solver-jobs/unanswered' / ('b' * 32)
        job.mkdir(parents=True)
        self.write(job / 'model.json', {})
        self.write(job / 'state.json', {'model': {}})
        self.write(job / 'broker-receipt.json', {'caseId': 'unanswered', 'engine': 'OpenSees',
                    'role': 'candidate', 'ok': True, 'stateSha256': '0' * 64})
        output = self.root / 'evidence'
        archive(self.edition, self.work, self.sessions, self.grade, output)
        with self.assertRaisesRegex(ValueError, 'protected state seal differs'):
            verify(output, replay=True)

    def test_diagnostic_relocation_cannot_change_quantities_or_metrics(self):
        original = {'rows': [{'error': 'ENOENT /original/work/answer.json', 'passed': False,
                              'failures': [{'value': '/original/work/quantity', 'actual': 1.0, 'expected': -1.0}]}]}
        result = diagnostic_paths(original, {'work': '/original/work'})
        self.assertEqual(result['rows'][0]['error'], 'ENOENT $WORK/answer.json')
        self.assertEqual(result['rows'][0]['failures'], original['rows'][0]['failures'])
        self.assertEqual(original['rows'][0]['error'], 'ENOENT /original/work/answer.json')
        semantic = {'rows': [{'error': 'Unknown quantity /original/work/quantity', 'passed': False}]}
        self.assertEqual(diagnostic_paths(semantic, {'work': '/original/work'}), semantic)


if __name__ == '__main__':
    unittest.main()
