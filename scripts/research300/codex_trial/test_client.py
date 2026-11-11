"""Check result retention/invalidation at the real candidate-facing file boundary."""
import json,subprocess,sys,tempfile,time,unittest
from pathlib import Path
CLIENT=Path(__file__).with_name('analyze.py')
class ClientBoundary(unittest.TestCase):
 def call(self,root,selection,model_hash,ok=True):
  model=root/'model.json';model.write_text('{}');state=root/'state.json';before=set((root/'scratch/requests').glob('*.json'))
  p=subprocess.Popen([sys.executable,str(CLIENT),'--model',str(model),'--selection',selection,'--session',str(root),'--output-state',str(state),'--timeout','5'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
  deadline=time.monotonic()+3;request=None
  while time.monotonic()<deadline:
   new=set((root/'scratch/requests').glob('*.json'))-before
   if new:request=new.pop();break
   time.sleep(.01)
  self.assertIsNotNone(request);self.assertEqual(json.loads(request.read_text())['selection']['id'],selection.split(':',1)[1])
  entry={'meta':{'modelHash':model_hash,'runId':request.stem},'data':{'actual_fixture_value':42}}
  reply={'ok':ok,'jobId':request.stem,'error':'real service failed','state':{'model':{'identity':model_hash},'analysisResult':{**entry,'runId':request.stem,'results':{selection:entry}}}}
  (root/'solver-replies'/request.name).write_text(json.dumps(reply));stdout,stderr=p.communicate(timeout=5)
  return p.returncode,state,stdout,stderr
 def test_selected_runs_accumulate_only_for_the_same_model_and_repeat_replaces(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);(root/'scratch/requests').mkdir(parents=True);(root/'solver-replies').mkdir()
   status,state,_,_=self.call(root,'case:D','model-A');self.assertEqual(status,0);first=json.loads(state.read_text())['analysisResult']['results']['case:D']['meta']['runId']
   status,state,_,_=self.call(root,'case:L','model-A');self.assertEqual(status,0);self.assertEqual(set(json.loads(state.read_text())['analysisResult']['results']),{'case:D','case:L'})
   status,state,_,_=self.call(root,'case:D','model-A');self.assertEqual(status,0);new=json.loads(state.read_text());self.assertNotEqual(new['analysisResult']['results']['case:D']['meta']['runId'],first)
   status,state,_,_=self.call(root,'case:D','model-B');self.assertEqual(status,0);self.assertEqual(set(json.loads(state.read_text())['analysisResult']['results']),{'case:D'})
   original=state.read_bytes();status,state,_,_=self.call(root,'case:L','model-B',ok=False);self.assertNotEqual(status,0);self.assertEqual(state.read_bytes(),original,'failed execution cannot synthesize or replace any result')
if __name__=='__main__':unittest.main()
