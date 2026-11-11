import unittest
try:
 from .pkpm_results import source_actions,end_wrench
except ImportError:
 from pkpm_results import source_actions,end_wrench
COLUMN=[[0,0,1],[0,-1,0],[1,0,0]]
class NativeSlots(unittest.TestCase):
 def test_beam_signed_cut_slots(self):self.assertEqual(source_actions('beam',[1,2,3,4,5,6]),[1,-2,-3,4,5,6])
 def test_column_axis_swap(self):self.assertEqual(source_actions('column',[1,2,3,4,5,6]),[1,3,-2,4,-6,5])
 def test_vertical_column_horizontal_x_balance(self):self.assertEqual(end_wrench('column',COLUMN,0,[0,11,0,0,0,22]),[-11,0,0,0,-22,0])
 def test_vertical_column_horizontal_y_balance(self):self.assertEqual(end_wrench('column',COLUMN,0,[0,0,17,0,-34,0]),[0,-17,0,34,0,0])
 def test_vertical_axial_and_torque(self):self.assertEqual(end_wrench('column',COLUMN,0,[-23,0,0,13,0,0]),[0,0,23,0,0,-13])
 def test_far_end_sign(self):self.assertEqual(end_wrench('beam',[[1,0,0],[0,1,0],[0,0,1]],1,[1,2,3,4,5,6]),[1,2,3,4,5,6])
 def test_sentinel_fail_closed(self):
  with self.assertRaises(ValueError):source_actions('beam',[-99999]*6)


import hashlib,json,tempfile
from pathlib import Path
try:
 from .pkpm_candidates import export_candidates
except ImportError:
 from pkpm_candidates import export_candidates

class CandidateExport(unittest.TestCase):
 def test_captured_sdk_metadata_selection_and_missing(self):
  with tempfile.TemporaryDirectory() as tmp:
   evidence,corpus=self.fixture(Path(tmp));out=Path(tmp)/'out';export_candidates(evidence,corpus,out)
   d=json.loads((out/'STD-091/native-reference.json').read_text());q=d['states'][0]['quantities']
   self.assertEqual([v['selection']['kind'] for v in q],['case','combination','case'])
   self.assertEqual(q[0]['value'],-0.0007526911645072687)
   self.assertEqual(q[1]['value'],-82.4861831665039)
   self.assertIsNone(q[2]['value']);self.assertEqual(q[2]['rawTrace']['rawValue'],-99999.)
   self.assertEqual(q[0]['unit'],'mm');self.assertEqual(q[0]['tolerance'],{'absolute':1e-8,'relative':1e-6})
   self.assertFalse(d['accepted']);self.assertFalse(d['nativeVerified']);self.assertTrue(d['notCommercialScoringTruth'])
 def test_modified_native_hash_fails_before_candidate(self):
  with tempfile.TemporaryDirectory() as tmp:
   evidence,corpus=self.fixture(Path(tmp));p=evidence/'run/remote-evidence/c30-test/sdk-results.json';p.write_text(p.read_text()+' ')
   with self.assertRaisesRegex(ValueError,'SHA|hash'):export_candidates(evidence,corpus,Path(tmp)/'out')
 def test_modified_source_hash_fails(self):
  with tempfile.TemporaryDirectory() as tmp:
   evidence,corpus=self.fixture(Path(tmp));p=corpus/'STD-091/model-state-1.json';p.write_text(p.read_text()+' ')
   with self.assertRaisesRegex(ValueError,'SHA|hash|source'):export_candidates(evidence,corpus,Path(tmp)/'out')
 def test_native_mutation_during_extraction_is_detected(self):
  from unittest.mock import patch
  import sys
  module=sys.modules[export_candidates.__module__];original=module.Run.quantity
  with tempfile.TemporaryDirectory() as tmp:
   evidence,corpus=self.fixture(Path(tmp));target=evidence/'run/remote-evidence/c30-test/sdk-results.json'
   def mutate(run,request):
    result=original(run,request);target.write_text(target.read_text()+' ');return result
   with patch.object(module.Run,'quantity',mutate):
    with self.assertRaisesRegex(ValueError,'SHA'):export_candidates(evidence,corpus,Path(tmp)/'out')
 def test_unbound_boundary_review_does_not_fill_missing(self):
  with tempfile.TemporaryDirectory() as tmp:
   evidence,corpus=self.fixture(Path(tmp));review=Path(tmp)/'review.json';review.write_text('{}');out=Path(tmp)/'out'
   export_candidates(evidence,corpus,out,boundary_review=review)
   d=json.loads((out/'STD-091/native-reference.json').read_text());self.assertIsNone(d['states'][0]['quantities'][2]['value'])
 def fixture(self,root):
  # Captured SDK values from executed STD091 DL (calibration evidence),
  # reduced to a single record for I/O tests; this is not a solvable submodel.
  import sys
  sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
  from reference_io import load_case
  evidence=root/'evidence';corpus=root/'cases';case=corpus/'STD-091';run=evidence/'run/remote-evidence/c30-test';case.mkdir(parents=True);run.mkdir(parents=True)
  dump=lambda p,v:p.write_text(json.dumps(v));digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
  model={'schema_version':'2.2.0','nodes':[{'id':'a','x':0,'y':0,'z':0,'restraints':[True]*6},{'id':'b','x':0,'y':0,'z':3.6,'restraints':[False]*6}],'elements':[{'id':'c','type':'column','nodes':['a','b'],'rotation_angle':0}],'load_cases':[{'id':'D','loads':[]}],'load_combinations':[{'id':'D','factors':{'D':1}}]}
  q=lambda id,kind,loc,comp,unit:{'id':id,'selection':{'kind':kind,'id':'D'},'location':loc,'component':comp,'unit':unit,'tolerance':{'absolute':1e-8,'relative':1e-6}}
  quantities=[q('u','case',{'kind':'node','id':'b'},'ux','mm'),q('n','combination',{'kind':'member','id':'c','positionM':0,'side':'right'},'N','kN'),q('base','case',{'kind':'node','id':'a'},'ux','m')]
  dump(case/'model-state-1.json',model);dump(case/'reference-requests.json',{'schemaVersion':1,'states':[{'state':1,'model':'model-state-1.json','quantities':quantities,'derived':[]}]});dump(case/'contract.json',{'schemaVersion':1,'id':'STD-091','modelId':'M-STD-091','modelStates':['model-state-1.json'],'attachments':[],'analysisConvention':{'version':'commercial-linear-static-v2'}});(case/'prompt.txt').write_text('Captured native-record extraction fixture.')
  packet={'selection':{'kind':'basic-cases','nativeCases':{'D':{'id':1,'name':'DL'}}},'members':[{'id':'c','type':'column','nodes':['a','b'],'lengthM':3.6,'basisGlobal':[[0,0,1],[0,-1,0],[1,0,0]]}]}
  dump(run/'physical-input.json',packet);dump(run/'frame-input-receipt.json',{'inputSha256':digest(run/'physical-input.json')});dump(run/'frame-after-solve-input-audit.json',{'parametersMatchBefore':True});dump(run/'native-output-audit.json',{'sourceMembersCovered':1});dump(run/'frame-numeric-output.json',{'SDATA.SAT':{'allMechanicalRecordsMatch':True}})
  dump(run/'sdk-results.json',{'nodes':[{'floor':0,'coordinates':[0,0,0],'cases':{'DL':[-99999.]*3}},{'floor':1,'coordinates':[0,0,3600],'cases':{'DL':[-7.526911645072687e-07,-6.661925340267771e-07,-7.207530416053487e-06]}}],'members':[{'sourceId':'c','kind':'column','forces':{'DL':{'0':[-82.4861831665039,-2.9903764724731445,-2.075918197631836,-1.084273177669286e-16,2.499600410461426,-3.5801663398742676],'1':[-82.4861831665039,-2.9903764724731445,-2.075918197631836,-1.084273177669286e-16,-4.973704814910889,7.185187339782715]}}}]})
  dump(run/'native-material-input-audit.json',{});dump(run/'frame-numeric-input.json',{'solverSha256':'333b010d067f820c453972833e18bc9db2328059cbba83e456effd0dc79d9a4d'})
  for n in ['SDATA.SAT','DATA.SAT','DISP.SAT','MESH.SAT','NODEINDEX.SAT','UserMaterial.SAT']:(run/n).write_bytes(b'captured-record-fixture-no-binary-decoding')
  loaded=load_case(case);artifacts={p.name:{'path':str(p.relative_to(evidence)),'sha256':digest(p)} for p in run.iterdir()}
  stage=evidence/'captured-stage.json';dump(stage,{'status':'completed','returncode':0,'executableSha256':'043f0682116f728e9b2b4d41bd79d8f646e227b1c2d3d664004090cdc99abdd1'})
  dump(evidence/'pkpm-candidate-evidence-manifest.json',{'schemaVersion':1,'runs':[{'caseId':'STD-091','state':1,'sourceHash':loaded['sourceHash'],'sourceModelSha256':loaded['hashes']['model-state-1.json'],'runRoot':'run','nativeIdentity':'c30-test','engineVersion':'PKPM 2027R1.0.1','solverBinarySha256':'333b010d067f820c453972833e18bc9db2328059cbba83e456effd0dc79d9a4d','stages':[{'stage':'analysis','path':'captured-stage.json','sha256':digest(stage)}],'artifacts':artifacts}]})
  return evidence,corpus

if __name__=='__main__':unittest.main()
