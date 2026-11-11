"""Recorded native arrays exercise mapping, traceability, and fail-closed guards."""
import copy,hashlib,json,math,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
try:
    from . import yjk_candidates as yc
except ImportError:
    import yjk_candidates as yc

FIXTURE=Path(__file__).parent/'fixtures/yjk_frame_a_endpoints.json'

class CandidateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.fixture=json.loads(FIXTURE.read_text());self.model=self.fixture['model_fragment']
        self.hash=hashlib.sha256(json.dumps(self.model).encode()).hexdigest()
        self.project=self.root/'project';self.project.mkdir()
        self.row={'source_model_sha256':self.hash,'project':'project','reading':'project','audits':['audit.json']}
        self.write('project/input.json',self.model)
        (self.project/'fea.dat').write_text(self.fixture['native_fe_fragment'],encoding='gb18030')
        self.write('project/mapping.json',{'load_cases':[{'source_case':'D','native_name':'LC1','native_kind':10001}]})
        self.write('project/results.json',{'cases':[self.fixture['sdk_case_fragment']]})
        self.write('audit.json',{'source_sha256':self.hash,'node_map':self.fixture['node_map'],'frame_map':self.fixture['frame_map'],'representation_failures':[]})
        self.bind()
    def tearDown(self):self.tmp.cleanup()
    def write(self,name,data):(self.root/name).write_text(json.dumps(data))
    def bind(self,update_audit=True):
        if update_audit:
            audit=json.loads((self.root/'audit.json').read_text())
            audit.update(native_input_sha256=yc.sha(self.project/'fea.dat'),native_result_sha256=yc.sha(self.root/self.row.get('resultsPath','project/results.json')))
            self.write('audit.json',audit)
        self.row['artifacts']=[{'path':str(p.relative_to(self.root)),'sha256':yc.sha(p)} for p in self.root.rglob('*') if p.is_file()]
    def evidence(self):return yc.StateEvidence(self.row,self.root,self.model,self.hash)
    def request(self,kind='case',unit='m'):
        return {'id':'q','selection':{'kind':kind,'id':'D'},'location':{'kind':'node','id':'n0-0-1'},'component':'uy','unit':unit}
    def export_input(self):
        case=self.root/'corpus'/'MM-080';case.mkdir(parents=True)
        contract={'schemaVersion':1,'id':'MM-080','plannedEngine':'YJK','modelStates':['model.json'],'attachments':[],
                  'analysisConvention':{'version':2,'beamTheory':'Timoshenko','shearAreaRatio':5/6}}
        (case/'contract.json').write_text(json.dumps(contract));(case/'prompt.txt').write_text('Fixture only')
        (case/'model.json').write_text(json.dumps(self.model))
        (case/'reference-requests.json').write_text(json.dumps({'schemaVersion':1,'states':[{'state':1,'model':'model.json','quantities':[self.request()],'derived':[]}]}))
        self.row.update(case='MM-080',state=1)
        self.write('index.json',{'states':[self.row]})
        return self.root/'index.json',self.root/'corpus',self.root/'candidates'
    def test_duplicate_source_case_is_rejected_even_when_native_name_matches(self):
        self.write('project/mapping.json',{'load_cases':[{'source_case':'D','native_name':'LC1','native_kind':10001}]*2});self.bind()
        with self.assertRaises(ValueError):self.evidence()
    def test_same_name_case_with_different_analysis_number_is_rejected(self):
        raw=copy.deepcopy(self.fixture['sdk_case_fragment']);raw['analysis_case']=10002
        self.write('project/results.json',{'cases':[raw]});self.bind()
        with self.assertRaises(ValueError):self.evidence()
    def test_audit_for_another_native_run_is_rejected_despite_valid_artifact_hashes(self):
        for field in ['native_input_sha256','native_result_sha256']:
            audit=json.loads((self.root/'audit.json').read_text());audit[field]='f'*64
            self.write('audit.json',audit);self.bind(update_audit=False)
            with self.subTest(field=field),self.assertRaises(ValueError):self.evidence()
            self.bind()
    def test_archive_results_path_and_trace_survive_directory_move(self):
        (self.project/'results.json').rename(self.project/'read-results.json')
        self.row['resultsPath']='project/read-results.json';self.bind()
        self.assertEqual(self.evidence().quantity(self.request())['value'],-1.024438233798719e-06)
        self.assertTrue(all(not Path(a['path']).is_absolute() for a in self.evidence().artifacts))
    def test_export_carries_current_convention_and_pending_truth_markers(self):
        args=self.export_input();yc.export_candidates(*args)
        candidate=json.loads((args[2]/'MM-080/native-yjk-candidate.json').read_text())
        self.assertEqual(candidate.get('analysisConvention'),{'version':2,'beamTheory':'Timoshenko','shearAreaRatio':5/6})
        self.assertIs(candidate.get('notCommercialScoringTruth'),True)
        self.assertEqual(candidate.get('sameEngineTruthStatus'),'pending')
        self.assertTrue(all(not Path(a['path']).is_absolute() for a in candidate['states'][0]['evidenceArtifacts']))
    def test_evidence_changed_during_export_is_rejected_before_writing(self):
        args=self.export_input();original=yc.StateEvidence.quantity
        def changed(evidence,request):
            value=original(evidence,request)
            path=self.project/'fea.dat';path.write_bytes(path.read_bytes()+b' ')
            return value
        with patch.object(yc.StateEvidence,'quantity',changed),self.assertRaises(ValueError):yc.export_candidates(*args)
        self.assertFalse((args[2]/'MM-080/native-yjk-candidate.json').exists())
    def test_same_name_case_and_combination_keep_kind_and_native_trace(self):
        e=self.evidence();case=e.quantity(self.request());combo=e.quantity(self.request('combination','mm'))
        native=self.fixture['sdk_case_fragment']['nodes'][str(self.fixture['node_map']['n0-0-1'])]['displacement'][1]
        self.assertEqual(case['value'],native);self.assertEqual(combo['value'],native*2000)
        self.assertEqual(combo['rawTrace'][0]['factor'],2);self.assertEqual(combo['rawTrace'][0]['trace']['api'],'dsnGetNodeDis')
        self.assertEqual(combo['rawTrace'][0]['trace']['nativeAnalysisCase'],10001)
        self.assertEqual(case['selection']['kind'],'case');self.assertEqual(combo['selection']['kind'],'combination')
    def test_source_and_native_bytes_must_remain_bound(self):
        with self.assertRaises(ValueError):yc.StateEvidence(self.row,self.root,self.model,'different')
        for filename in ['input.json','fea.dat','mapping.json','results.json']:
            p=self.project/filename;old=p.read_bytes();p.write_bytes(old+b' ')
            with self.subTest(filename=filename),self.assertRaises(ValueError):self.evidence()
            p.write_bytes(old)
    def test_missing_or_nonfinite_native_values_are_not_zero(self):
        for bad in (None,[0]*5,[0,float('nan'),0,0,0,0],[0,True,0,0,0,0]):
            raw=copy.deepcopy(self.fixture['sdk_case_fragment']);raw['nodes'][str(self.fixture['node_map']['n0-0-1'])]['displacement']=bad
            self.write('project/results.json',{'cases':[raw]});self.bind()
            with self.subTest(bad=bad),self.assertRaises(ValueError):self.evidence().quantity(self.request())
    def test_unrequested_brace_does_not_hide_node_result_but_direct_brace_stays_pending(self):
        p=self.project/'fea.dat';p.write_text(p.read_text(encoding='gb18030').replace('T=COLUMN','T=BRACE'),encoding='gb18030');self.bind();e=self.evidence()
        self.assertIn('value',e.quantity(self.request()))
        q={'id':'end','selection':{'kind':'case','id':'D'},'location':{'kind':'member','id':'c0-0-1','positionM':0,'side':'right'},'component':'M2','unit':'kN.m'}
        result=e.quantity(q);self.assertNotIn('value',result);self.assertEqual(result['nativeStatus'],'pending-output-family')
    def test_recorded_beam_and_column_end_signs_match_independent_control(self):
        e=self.evidence()
        for eid,ends in self.fixture['independent_endpoints'].items():
            for end in ends:
                for i,c in enumerate(yc.ACTIONS):
                    q={'id':'end','selection':{'kind':'case','id':'D'},'location':{'kind':'member','id':eid,'positionM':end['position_m'],'side':'right' if end['source_endpoint']==0 else 'left'},'component':c,'unit':'kN' if i<3 else 'kN.m'}
                    actual=e.quantity(q)
                    # Frozen fixture-regression residual, not a corpus acceptance tolerance.
                    self.assertLess(abs(actual['value']-end['independent_actual_FE'][i]),3e-6,(eid,end['source_endpoint'],c))
                    self.assertEqual(actual['rawTrace'][0]['trace']['nativeEndpoint'],end['native_endpoint'])
    def test_interior_position_is_not_inferred_from_section_count(self):
        with self.assertRaises(ValueError):yc.endpoint_index(3.,6.)
        self.assertEqual(yc.endpoint_index(math.nextafter(6.,math.inf),6.),1)

if __name__=='__main__':unittest.main()
