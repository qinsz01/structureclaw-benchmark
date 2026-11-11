"""Offline archive tests, including two genuinely evaluated clarification cases.

The synthetic failed receipt exercises preservation only; it is never counted as
a successful native job. No native solver/network call is made by these tests.
"""
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

from scripts.research300_v2.archive import archive, evaluator_closure, inspect_file, SplitWriter, write
from scripts.research300_v2.verify_archive import SplitReader, verify

ROOT = Path(__file__).resolve().parents[2]


class ArchiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.edition = cls.root / 'edition'
        cls.edition.mkdir()
        cases, files = [], []
        for i in range(2):
            cid = f'CLARIFY-{i}'
            ref = cls.edition / f'{cid}.json'
            write(ref, {'kind': 'clarify', 'requests': [], 'clarificationFields': ['parameters:groundMotionUnit']})
            files.append({'path': ref.name, 'sha256': hashlib.sha256(ref.read_bytes()).hexdigest()})
            cases.append({'id': cid, 'family': 'INT', 'engine': 'OpenSees',
                          'turns': [{'id': 't1', 'public': 'unused', 'private': ref.name}]})
        write(cls.edition / 'manifest.json', {'edition': 'archive-test-clarification-only', 'cases': cases,
                                             'files': files, 'sutCommit': 'no-native-jobs'})
        checksum = hashlib.sha256((cls.edition / 'manifest.json').read_bytes()).hexdigest()
        cls.works = []
        for case in cases:
            work = cls.root / case['id']
            folder = work / 'runs' / case['id'] / 't1'
            folder.mkdir(parents=True)
            write(folder / 'capture.json', {'caseId': case['id'], 'turnId': 't1', 'manifestSha256': checksum,
                'jobIds': [], 'currentJobIds': [], 'maintainerOracle': True, 'candidateCall': False})
            write(work / 'execution-summary.json', {'manifestSha256': checksum, 'allSucceeded': True,
                'candidateCalls': 0, 'caseIds': [case['id']],
                'turns': [{'caseId': case['id'], 'turnId': 't1', 'executionPrepared': True}], 'nativeJobs': 0})
            cls.works.append(work)
        # Build a canary without putting its complete value into archived source.
        cls.secret = ''.join(['ARCHIVE', '_CANARY_', 'PRIVATE', '_2026'])
        write(cls.works[0] / 'remote-setup.json', {'host': 'test.invalid', 'password': cls.secret})
        cls.failed = cls.root / 'failed-attempt'
        cls.failed.mkdir()
        write(cls.failed / 'broker-receipt.json', {'ok': False, 'error': 'synthetic failed attempt fixture'})
        write(cls.failed / 'failure.json', {'fixture': True, 'executionPrepared': False})
        cls.qualification = cls.root / 'qualification'
        process = subprocess.run(['node', str(ROOT / 'scripts/research300_v2/qualify.cjs'), '--edition', str(cls.edition),
            '--work', ','.join(map(str, cls.works)), '--output', str(cls.qualification)], capture_output=True, text=True)
        if process.returncode:
            raise RuntimeError(process.stderr + process.stdout)
        cls.output = cls.root / 'archive'
        cls.summary = archive(cls.edition, cls.works, cls.qualification, cls.output,
                              attempts=[cls.failed], part_bytes=64 * 1024)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_complete_multiwork_archive_replays_every_output_byte(self):
        result = verify(self.output, replay=True)
        self.assertEqual(result['caseCount'], 2)
        self.assertEqual(result['volumesVerified'], len(json.loads((self.output / 'archive.json').read_text())['parts']))
        self.assertEqual(result['turnCount'], 2)
        self.assertEqual(result['nativeJobs'], 0)
        self.assertEqual(result['failedJobsRetained'], 1)
        self.assertEqual(result['offlineReplay']['identicalFiles'], 5)
        self.assertFalse(result['offlineReplay']['nativeSolversInvoked'])
        self.assertGreater(result['volumesVerified'], 1)

    def test_configuration_secret_is_excluded_and_recorded(self):
        metadata = json.loads((self.output / 'archive.json').read_text())
        self.assertEqual(metadata['excludedFiles'], [{'path': 'works/001/remote-setup.json',
                            'reason': 'credential/configuration file excluded'}])
        parts = [self.output / row['file'] for row in metadata['parts']]
        with SplitReader(parts) as reader, zipfile.ZipFile(reader) as bundle:
            self.assertFalse(any(name.endswith('remote-setup.json') for name in bundle.namelist()))
            for name in bundle.namelist():
                self.assertNotIn(self.secret.encode(), bundle.read(name), name)

    def test_changed_volume_is_rejected_before_replay(self):
        copied = self.root / 'corrupt'
        shutil.copytree(self.output, copied)
        part = copied / 'evidence.zip.part001.bin'
        data = bytearray(part.read_bytes())
        data[10] ^= 1
        part.write_bytes(data)
        with self.assertRaisesRegex(ValueError, 'checksum/size differs'):
            verify(copied)

    def test_missing_or_duplicated_batch_never_certifies_full_coverage(self):
        with self.assertRaisesRegex(ValueError, 'do not cover'):
            archive(self.edition, self.works[:1], self.qualification, self.root / 'incomplete')
        with self.assertRaisesRegex(ValueError, 'unique'):
            archive(self.edition, [self.works[0], self.works[0]], self.qualification, self.root / 'duplicated')

    def test_secret_in_json_or_embedded_zip_is_rejected(self):
        unsafe = self.root / 'unsafe.json'
        write(unsafe, {'password': self.secret})
        with self.assertRaisesRegex(ValueError, 'Credential'):
            inspect_file(unsafe, 'unsafe.json', [])
        zipped = self.root / 'unsafe.zip'
        with zipfile.ZipFile(zipped, 'w') as bundle:
            bundle.writestr('stdout.txt', self.secret)
        with self.assertRaisesRegex(ValueError, 'Credential'):
            inspect_file(zipped, 'unsafe.zip', [self.secret])

    def test_split_stream_reconstitutes_an_ordinary_zip(self):
        folder = self.root / 'small-volumes'
        folder.mkdir()
        payload = os.urandom(6000)
        stream = SplitWriter(folder, 1024)
        with zipfile.ZipFile(stream, 'w') as bundle:
            bundle.writestr('payload.bin', payload)
        stream.close()
        self.assertTrue(all(part.stat().st_size <= 1024 for part in stream.parts))
        with zipfile.ZipFile(io.BytesIO(b''.join(part.read_bytes() for part in stream.parts))) as bundle:
            self.assertEqual(bundle.read('payload.bin'), payload)
        with SplitReader(stream.parts) as reader, zipfile.ZipFile(reader) as bundle:
            self.assertEqual(bundle.read('payload.bin'), payload)

    def test_offline_dependency_closure_is_explicit_and_local(self):
        closure = evaluator_closure()
        self.assertIn(ROOT / 'scripts/research300_v2/qualify.cjs', closure)
        self.assertIn(ROOT / 'lib/reference-precision.cjs', closure)
        self.assertTrue(all(file.is_relative_to(ROOT) for file in closure))


class RetryArchiveTests(unittest.TestCase):
    """Three-turn recovery uses whole cases and preserves a sealed old runner.

    Clarification turns run the real qualifier. The failed broker receipt and
    old runner are explicit synthetic provenance fixtures, not native results.
    """
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.edition = cls.root / 'edition'
        cls.edition.mkdir()
        cases, files = [], []
        for cid, count in [('LOCAL', 1), ('RETRY', 3)]:
            turns = []
            for ordinal in range(1, count + 1):
                file = cls.edition / f'{cid}-t{ordinal}.json'
                write(file, {'kind': 'clarify', 'engine': 'PKPM' if cid == 'RETRY' else 'OpenSees',
                             'requests': [], 'clarificationFields': ['parameters:groundMotionUnit']})
                files.append({'path': file.name, 'sha256': hashlib.sha256(file.read_bytes()).hexdigest()})
                turns.append({'id': f't{ordinal}', 'private': file.name, 'public': 'unused'})
            cases.append({'id': cid, 'family': 'INT', 'engine': 'PKPM' if cid == 'RETRY' else 'OpenSees', 'turns': turns})
        write(cls.edition / 'manifest.json', {'edition': 'three-turn-retry-test', 'sutCommit': 'no-native-jobs',
                                             'cases': cases, 'files': files})
        cls.checksum = hashlib.sha256((cls.edition / 'manifest.json').read_bytes()).hexdigest()
        cls.works = [cls.root / name for name in ['local', 'commercial-original', 'commercial-retry']]
        cls.runner_path = 'scripts/research300_v2/run_oracle.py'
        current_hash = hashlib.sha256((ROOT / cls.runner_path).read_bytes()).hexdigest()
        old_bytes = b'# Explicit synthetic earlier runner source used only in archive tests.\n'
        cls.old_hash = hashlib.sha256(old_bytes).hexdigest()
        for index, work in enumerate(cls.works):
            work.mkdir()
            cid, count = ('LOCAL', 1) if index == 0 else ('RETRY', 3)
            rows = []
            for ordinal in range(1, count + 1):
                completed = index != 1 or ordinal == 1
                rows.append({'caseId': cid, 'turnId': f't{ordinal}', 'kind': 'clarify', 'jobs': 0,
                             'executionPrepared': completed})
                if completed:
                    folder = work / 'runs' / cid / f't{ordinal}'
                    folder.mkdir(parents=True)
                    write(folder / 'capture.json', {'caseId': cid, 'turnId': f't{ordinal}', 'manifestSha256': cls.checksum,
                        'jobIds': [], 'currentJobIds': [], 'maintainerOracle': True, 'candidateCall': False})
            summary = {'manifestSha256': cls.checksum, 'allSucceeded': index != 1, 'candidateCalls': 0,
                       'caseIds': [cid], 'turns': rows, 'nativeJobs': 0, 'finishedAt': '2026-10-28T10:00:00Z'}
            if index == 1:
                (work / 'execution-attempts').mkdir()
                write(work / 'execution-attempts/failure.json', summary)
                job = work / 'solver-jobs/RETRY' / ('a' * 32)
                job.mkdir(parents=True)
                write(job / 'broker-receipt.json', {'caseId': 'RETRY', 'engine': 'PKPM', 'role': 'oracle',
                    'ok': False, 'error': 'synthetic backend failure fixture', 'fixture': True})
                snapshot = work / 'implementation-snapshots' / cls.old_hash / cls.runner_path
                snapshot.parent.mkdir(parents=True)
                snapshot.write_bytes(old_bytes)
            else:
                write(work / 'execution-summary.json', summary)
            write(work / 'runtime-binding.json', {'manifestSha256': cls.checksum, 'sutCommit': 'no-native-jobs',
                'plan': [{'caseId': cid, 'engine': 'PKPM' if cid == 'RETRY' else 'OpenSees'}],
                'implementation': {cls.runner_path: cls.old_hash if index == 1 else current_hash}})
        cls.qualification = cls.root / 'qualification'
        process = cls.qualify(cls.works, cls.qualification)
        if process.returncode:
            raise RuntimeError(process.stderr + process.stdout)
        cls.output = cls.root / 'archive'
        archive(cls.edition, cls.works, cls.qualification, cls.output, part_bytes=64 * 1024)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    @classmethod
    def qualify(cls, works, output):
        return subprocess.run(['node', str(ROOT / 'scripts/research300_v2/qualify.cjs'), '--edition', str(cls.edition),
            '--work', ','.join(map(str, works)), '--output', str(output)], capture_output=True, text=True)

    def test_whole_case_retry_replays_with_stable_batch_indices_and_retains_failure(self):
        summary = json.loads((self.qualification / 'summary.json').read_text())
        self.assertEqual(summary['recoveredCases'], [{'caseId': 'RETRY', 'completedBatch': 3, 'incompleteBatches': [2]}])
        self.assertEqual(summary['executionBatches'][1]['incompleteCases'],
                         [{'caseId': 'RETRY', 'completedTurns': ['t1'], 'incompleteTurns': ['t2', 't3']}])
        self.assertEqual(summary['unfinishedAttempts'][0]['batch'], 2)
        self.assertNotIn(str(self.root), (self.qualification / 'summary.json').read_text())
        result = verify(self.output, replay=True)
        self.assertEqual(result['turnCount'], 4)
        self.assertEqual(result['volumesVerified'], len(json.loads((self.output / 'archive.json').read_text())['parts']))
        self.assertEqual(result['failedJobsRetained'], 1)
        self.assertEqual(result['recoveredCases'], summary['recoveredCases'])
        self.assertEqual(result['offlineReplay']['identicalFiles'], 9)

    def test_unrecovered_case_and_duplicate_complete_retry_are_rejected(self):
        missing = self.qualify(self.works[:2], self.root / 'no-retry')
        self.assertNotEqual(missing.returncode, 0)
        self.assertIn('No complete execution batch recovered case: RETRY', missing.stderr)
        copied = self.root / 'duplicate-retry'
        shutil.copytree(self.works[2], copied)
        duplicated = self.qualify([*self.works, copied], self.root / 'duplicate-output')
        self.assertNotEqual(duplicated.returncode, 0)
        self.assertIn('duplicate complete execution batches', duplicated.stderr)

    def test_turns_from_two_partial_batches_are_never_spliced(self):
        partial = self.root / 'partial-retry'
        shutil.copytree(self.works[2], partial)
        (partial / 'runs/RETRY/t1/capture.json').unlink()
        summary = json.loads((partial / 'execution-summary.json').read_text())
        (partial / 'execution-summary.json').unlink()
        summary['allSucceeded'] = False
        summary['turns'][0]['executionPrepared'] = False
        (partial / 'execution-attempts').mkdir()
        write(partial / 'execution-attempts/partial.json', summary)
        process = self.qualify([*self.works[:2], partial], self.root / 'spliced-output')
        self.assertNotEqual(process.returncode, 0)
        self.assertIn('No complete execution batch recovered case: RETRY', process.stderr)

    def test_wrong_manifest_in_discarded_failure_is_still_rejected(self):
        wrong = self.root / 'wrong-manifest'
        shutil.copytree(self.works[1], wrong)
        file = wrong / 'execution-attempts/failure.json'
        summary = json.loads(file.read_text())
        summary['manifestSha256'] = '0' * 64
        file.write_text(json.dumps(summary))
        process = self.qualify([self.works[0], wrong, self.works[2]], self.root / 'wrong-manifest-output')
        self.assertNotEqual(process.returncode, 0)
        self.assertIn('Attempt manifest/time binding differs', process.stderr)

    def test_old_runner_snapshot_is_hash_bound_and_cannot_be_replaced_by_current_code(self):
        metadata = json.loads((self.output / 'archive.json').read_text())
        old = next(row for row in metadata['runtimeSources'] if row['batch'] == 2)
        self.assertEqual(old['sha256'], self.old_hash)
        self.assertEqual(old['archivePath'], 'works/002/implementation-snapshots/' + self.old_hash + '/' + self.runner_path)
        corrupted = self.root / 'wrong-source-binding'
        shutil.copytree(self.output, corrupted)
        old['archivePath'] = 'implementation/' + self.runner_path
        (corrupted / 'archive.json').write_text(json.dumps(metadata))
        with self.assertRaisesRegex(ValueError, 'Executed implementation bytes differ'):
            verify(corrupted)

    def test_changed_snapshot_prevents_archival(self):
        wrong = self.root / 'changed-snapshot'
        shutil.copytree(self.works[1], wrong)
        (wrong / 'implementation-snapshots' / self.old_hash / self.runner_path).write_text('# wrong bytes\n')
        with self.assertRaisesRegex(ValueError, 'matching work snapshot'):
            archive(self.edition, [self.works[0], wrong, self.works[2]], self.qualification, self.root / 'bad-source-archive')

    def test_latest_closed_attempt_is_selected_and_open_batch_is_rejected(self):
        copied = self.root / 'later-closed-attempt'
        shutil.copytree(self.works[1], copied)
        summary = json.loads((copied / 'execution-attempts/failure.json').read_text())
        summary['finishedAt'] = '2026-10-28T11:00:00Z'
        write(copied / 'execution-attempts/later.json', summary)
        output = self.root / 'later-output'
        process = self.qualify([self.works[0], copied, self.works[2]], output)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(json.loads((output / 'summary.json').read_text())['executionBatches'][1]['summaryFile'],
                         'execution-attempts/later.json')
        shutil.rmtree(copied / 'execution-attempts')
        process = self.qualify([self.works[0], copied, self.works[2]], self.root / 'still-running-output')
        self.assertNotEqual(process.returncode, 0)
        self.assertIn('No closed execution attempt is available', process.stderr)

    def test_closed_attempt_with_nonterminal_or_missing_turn_is_rejected(self):
        for variant in ['nonterminal', 'missing']:
            copied = self.root / ('bad-terminal-' + variant)
            shutil.copytree(self.works[1], copied)
            file = copied / 'execution-attempts/failure.json'
            summary = json.loads(file.read_text())
            if variant == 'nonterminal':
                del summary['turns'][1]['executionPrepared']
            else:
                summary['turns'].pop()
            file.write_text(json.dumps(summary))
            process = self.qualify([self.works[0], copied, self.works[2]], self.root / ('bad-terminal-output-' + variant))
            self.assertNotEqual(process.returncode, 0)
            self.assertIn('nonterminal turn' if variant == 'nonterminal' else 'omits a planned turn', process.stderr)


if __name__ == '__main__':
    unittest.main()
