"""Captured pin residuals exercise the offline proof gate, not a solver mock."""
import copy
import ctypes
import errno
import hashlib
import importlib
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reference_io import evaluate_derived, load_case

MODULE = Path(__file__).with_name('pkpm_boundary_repair.py')
FLAGS = ('zeroRotationStiffness', 'noCoupling', 'noAdditionalConstraint',
         'freeDofsRetained', 'noSupportNodalLoad')
QID = 'case-D--n0-0-0--My'


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class BoundaryRepair(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.corpus = self.root / 'cases'
        self.output = self.root / 'out'
        self.review = self.root / 'review.json'
        self.document = self.fixture()
        dump(self.review, self.document)

    def descriptor(self, path):
        return {'path': path.relative_to(self.root).as_posix(), 'sha256': digest(path)}

    def fixture(self):
        cases, rows = [], []
        for case_id, residuals in [('INT-079', [1.9073486328125e-6]),
                                   ('INT-089', [4.76837158203125e-7, 0.0])]:
            case = self.corpus / case_id
            requests = []
            model_paths = []
            for i, value in enumerate(residuals, 1):
                model_path = f'model-state-{i}.json'
                model_paths.append(model_path)
                model = {'schema_version': '2.2.0', 'nodes': [
                    {'id': 'n0-0-0', 'x': 0, 'y': 0, 'z': 0,
                     'restraints': [True, True, True, False, False, False]},
                    {'id': 'roof', 'x': 0, 'y': 0, 'z': 3, 'restraints': [False]*6}],
                    'elements': [{'id': 'c0-0-1', 'nodes': ['n0-0-0', 'roof'], 'type': 'column'}],
                    'load_cases': [{'id': 'D', 'loads': []}], 'load_combinations': []}
                dump(case / model_path, model)
                quantities = [dict(id=QID, selection={'kind': 'case', 'id': 'D'},
                    location={'kind': 'node', 'id': 'n0-0-0'}, component='My', unit='kN.m',
                    tolerance={'absolute': 1e-8, 'relative': 1e-6}),
                    dict(id='member-M3', selection={'kind': 'case', 'id': 'D'},
                    location={'kind': 'member', 'id': 'c0-0-1', 'positionM': 0, 'side': 'right'},
                    component='M3', unit='kN.m', tolerance={'absolute': 1e-8, 'relative': 1e-6})]
                requests.append(dict(state=i, model=model_path, quantities=quantities,
                    derived=[dict(id='sum', operation='sum', operands=[QID, 'member-M3'], unit='kN.m')]))
            dump(case / 'reference-requests.json', {'schemaVersion': 1, 'states': requests})
            dump(case / 'contract.json', dict(schemaVersion=1, id=case_id, modelId='M-'+case_id,
                modelStates=model_paths, attachments=[], analysisConvention={'id': 'commercial-linear-static-v2'}))
            (case / 'prompt.txt').write_text('Captured numerical pin-boundary fixture.\n')
            loaded = load_case(case)
            candidate = dict(schemaVersion=1, id=case_id, modelId='M-'+case_id,
                referenceKind='native-pkpm-candidate', sameEngineTruthStatus='pending',
                nativeIndependentReview='pending', notCommercialScoringTruth=True, accepted=False,
                nativeVerified=False, analysisConvention=loaded['contract']['analysisConvention'],
                sourceHash=loaded['sourceHash'], sourceManifest=loaded['sourceManifest'],
                inputHashes=loaded['hashes'], nativeArtifacts={'unchanged': {'raw': 'binding'}}, states=[])
            case_rows = []
            for state, residual in zip(loaded['states'], residuals):
                n = state['state']; run = f'c30-{case_id}-{n}'
                trace = dict(nativeRun=run, sourceModelSha256=loaded['hashes'][state['modelPath']],
                    sourceSelection={'kind': 'case', 'id': 'D'}, sourceFactors={'D': 1.0},
                    nativeBasicFactors={'DL': 1.0}, origin='raw-member-end-equilibrium',
                    contributions=[{'member': 'c0-0-1', 'end': 0,
                        'raw': [{'rawSixSlots': [-82., -1., -1., 0., -0., -residual]}],
                        'globalEndWrench': [1., 1., 82., 0., residual, 0.]}],
                    externalNodalLoadAtSupport=[0.]*6, externalNodalLoadSources=[],
                    globalReactionComponents=['Fx','Fy','Fz','Mx','My','Mz'],
                    globalReaction=[1.,1.,82.,0.,residual,0.],
                    sourceRestraints=[True,True,True,False,False,False], nativeUnit='kN.m',
                    requestedUnit='kN.m', nativeValue=residual)
                quantities = copy.deepcopy(state['quantities'])
                quantities[0].update(value=residual, rawTrace=trace)
                quantities[1].update(value=7., rawTrace={'origin': 'raw-sdk-member-end-cut', 'raw': [7.]})
                candidate['states'].append(dict(state=n, model=state['modelPath'],
                    originalModelSha256=loaded['hashes'][state['modelPath']], nativeRun=run,
                    quantities=quantities, derived=evaluate_derived(quantities, state['derived'])))
                sources, blocks = [], []
                for name, offset, values in [('ConstraintNode.SAT',88,[1e14]*3+[0.]*3),
                        ('ConstraintNodeSK.SAT',16,[1e14,0.,1e14,0.,0.,1e14]+[0.]*6)]:
                    path = self.root / 'raw' / run / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(bytes(offset)+struct.pack('<%dd'%len(values), *values))
                    compiled=path.with_name(name+'.compiled-pin');compiled.write_bytes(path.read_bytes())
                    sources.extend([self.descriptor(path), self.descriptor(compiled)])
                    blocks.append(dict(artifact=name, offsetBytes=offset, executedValues=values,
                        postsolveEqualsCompiled=True, definitionId=1014, sourceMemberId='c0-0-1'))
                row = dict(caseId=case_id, state=n, model=state['modelPath'], quantityId=QID,
                    node='n0-0-0', component='My', selection={'kind':'case','id':'D'}, unit='kN.m',
                    derivedValue=0., sourceHash=loaded['sourceHash'],
                    modelSha256=loaded['hashes'][state['modelPath']],
                    requestSha256=loaded['hashes']['reference-requests.json'], nativeRun=run,
                    oldValue=residual, oldRawTrace=copy.deepcopy(trace), facts=dict.fromkeys(FLAGS,True),
                    proof=dict(executedConstraintBlocks=blocks, nativeTotalAndExitDOFs=[12,12],
                        retainedSixDofNodes=2, rawSixDOF=[0.,0.,0.,1e-6,1e-5,-1e-6],
                        nativeMemberEndResidual=residual, externalNodalLoadAtSupport=[0.]*6), sources=sources)
                row.update(dict.fromkeys(FLAGS, True)); case_rows.append(row)
            candidate_path=self.root/'old'/case_id/'native-reference.json';dump(candidate_path,candidate)
            candidate_desc=self.descriptor(candidate_path)
            qualification_path=self.root/'old'/case_id/'qualification.json'
            dump(qualification_path, dict(schemaVersion=1, reviewer='codex:independent', engine='PKPM', cases=[
                dict(id=case_id, sourceHash=loaded['sourceHash'], candidateSha256=candidate_desc['sha256'],
                     status='qualified')]))
            for row in case_rows:row['oldCandidateSha256']=candidate_desc['sha256']
            rows.extend(case_rows)
            cases.append(dict(id=case_id,sourceHash=loaded['sourceHash'],candidate=candidate_desc,
                qualification=self.descriptor(qualification_path),
                quantities=[dict(state=row['state'],quantityId=QID) for row in case_rows]))
        return dict(schemaVersion=1, ruleVersion='pkpm-free-rotation-reaction-v1',
            reviewer='codex:independent', engine='PKPM',status='qualified-boundary-derivation',
            valueKind='derived-from-native-free-boundary', quantities=rows, cases=cases, sources=[])

    def run_repair(self):
        self.assertTrue(MODULE.exists(), 'offline boundary repair implementation is absent')
        module=importlib.import_module('pkpm_boundary_repair')
        return module.repair_candidates(self.review,self.root,self.corpus,self.output)

    def reject(self, pattern='.'):
        dump(self.review,self.document)
        with self.assertRaisesRegex((ValueError,OSError),pattern):self.run_repair()
        self.assertFalse(self.output.exists())
        self.assertFalse(list(self.root.glob('.pkpm-boundary-repair-*')))

    def test_repairs_three_authorized_values_preserves_raw_and_recomputes_derived(self):
        before={c['candidate']['path']:(self.root/c['candidate']['path']).read_bytes() for c in self.document['cases']}
        result=self.run_repair();self.assertEqual(result['repairedQuantities'],3)
        for case in self.document['cases']:
            old=json.loads(before[case['candidate']['path']]);new=json.loads((self.output/case['id']/'native-reference.json').read_text())
            self.assertEqual(new['nativeArtifacts'],old['nativeArtifacts'])
            self.assertEqual(new['sourceHash'],old['sourceHash']);self.assertTrue(new['notCommercialScoringTruth'])
            self.assertEqual(new['sameEngineTruthStatus'],'pending');self.assertFalse(new['accepted']);self.assertFalse(new['nativeVerified'])
            for a,b in zip(old['states'],new['states']):
                q=b['quantities'][0];self.assertEqual(q['value'],0.)
                self.assertEqual(q['quantityStatus'],'derived-from-native-free-boundary')
                self.assertEqual(q['rawTrace']['rawMemberEndEquilibrium'],
                    {'value':a['quantities'][0]['value'],'rawTrace':a['quantities'][0]['rawTrace']})
                self.assertEqual(q['tolerance'],a['quantities'][0]['tolerance'])
                self.assertEqual(b['quantities'][1],a['quantities'][1]);self.assertEqual(b['derived'][0]['value'],7.)
            self.assertEqual((self.root/case['candidate']['path']).read_bytes(),before[case['candidate']['path']])

    def test_missing_or_nonboolean_proof_rejected(self):
        for location in ['top','facts']:
            for value in [None,False,1,'true']:
                with self.subTest(location=location,value=value):
                    row=self.document['quantities'][0];target=row if location=='top' else row['facts']
                    target['noCoupling']=value;self.reject();target['noCoupling']=True

    def test_nonzero_rotation_stiffness_rejected_even_with_true_boolean(self):
        self.document['quantities'][0]['proof']['executedConstraintBlocks'][0]['executedValues'][4]=1e-30
        self.reject()

    def test_missing_or_changed_evidence_hash_rejected(self):
        desc=self.document['quantities'][0]['sources'][0]
        (self.root/desc['path']).write_bytes(b'changed');self.reject('SHA|hash')

    def test_wrong_selection_component_node_or_run_rejected(self):
        row=self.document['quantities'][0]
        for key,value in [('component','M3'),('node','roof'),('selection',{'kind':'combination','id':'D'}),('nativeRun','other')]:
            with self.subTest(key=key):
                old=row[key];row[key]=value;self.reject();row[key]=old

    def test_source_restraint_load_or_tolerance_mutation_rejected(self):
        case=self.corpus/'INT-079';path=case/'model-state-1.json';old=path.read_bytes()
        for modify in [lambda d:d['nodes'][0]['restraints'].__setitem__(4,True),
                       lambda d:d['load_cases'][0]['loads'].append({'type':'nodal','node':'n0-0-0','values':[0,0,0,0,1,0]})]:
            d=json.loads(old);modify(d);dump(path,d);self.reject();path.write_bytes(old)
        path=case/'reference-requests.json';d=json.loads(path.read_text());d['states'][0]['quantities'][0]['tolerance']['absolute']=1
        dump(path,d);self.reject()

    def test_old_trace_missing_or_nonzero_external_moment_rejected(self):
        row=self.document['quantities'][0];trace=row['oldRawTrace']
        row['oldRawTrace']={};self.reject();row['oldRawTrace']=trace
        row['proof']['externalNodalLoadAtSupport'][4]=1e-20;self.reject()

    def test_candidate_or_qualification_hash_mutation_rejected(self):
        for key in ['candidate','qualification']:
            with self.subTest(key=key):
                path=self.root/self.document['cases'][0][key]['path'];old=path.read_bytes()
                path.write_bytes(old+b' ');self.reject('SHA|hash');path.write_bytes(old)

    def test_second_case_error_leaves_no_partial_output(self):
        self.document['quantities'][2]['facts']['freeDofsRetained']=False;self.reject()

    def test_output_existing_or_symlink_parent_rejected(self):
        self.output.mkdir()
        with self.assertRaises((ValueError,OSError)):self.run_repair()
        self.output.rmdir();(self.root/'link').symlink_to(self.root,target_is_directory=True)
        self.output=self.root/'link'/'out';self.reject()

    def test_evidence_symlink_and_escape_rejected(self):
        row=self.document['quantities'][0];desc=row['sources'][0];original=desc['path']
        desc['path']='../escape';self.reject();desc['path']=original
        path=self.root/original;content=path.read_bytes();path.unlink();target=self.root/'outside';target.write_bytes(content);path.symlink_to(target)
        self.reject()

    def test_mutation_before_publication_is_detected(self):
        self.assertTrue(MODULE.exists(), 'offline boundary repair implementation is absent')
        module=importlib.import_module('pkpm_boundary_repair');original=module.evaluate_derived
        target=self.root/self.document['quantities'][0]['sources'][0]['path']
        def changed(*args,**kwargs):
            value=original(*args,**kwargs);target.write_bytes(target.read_bytes()+b' ');return value
        with patch.object(module,'evaluate_derived',changed):self.reject('SHA|hash')

    def test_filesystem_without_rename_noreplace_publishes_complete_batch(self):
        self.assertTrue(MODULE.exists(), 'offline boundary repair implementation is absent')
        module=importlib.import_module('pkpm_boundary_repair')
        class UnsupportedRename:
            def __call__(self,*args):
                ctypes.set_errno(errno.EINVAL)
                return -1
        class Library:
            renameat2=UnsupportedRename()
        with patch.object(module.ctypes,'CDLL',return_value=Library()):
            self.run_repair()
        self.assertTrue((self.output/'INT-079/native-reference.json').is_file())
        self.assertTrue((self.output/'INT-089/native-reference.json').is_file())
        self.assertTrue((self.output/'manifest.json').is_file())

    def test_fallback_rename_failure_removes_only_owned_empty_reservation(self):
        self.assertTrue(MODULE.exists(), 'offline boundary repair implementation is absent')
        module=importlib.import_module('pkpm_boundary_repair')
        class UnsupportedRename:
            def __call__(self,*args):
                ctypes.set_errno(errno.EINVAL)
                return -1
        class Library:
            renameat2=UnsupportedRename()
        with patch.object(module.ctypes,'CDLL',return_value=Library()), \
             patch.object(module.os,'rename',side_effect=OSError(errno.EIO,'controlled publication failure')):
            self.reject('controlled publication failure')


if __name__=='__main__':unittest.main()
