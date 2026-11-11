"""Candidate-facing client. Every result comes from a broker execution, never a reference."""
import argparse,json,time,uuid
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--model',required=True);p.add_argument('--selection',required=True);p.add_argument('--session',required=True);p.add_argument('--output-state',required=True);p.add_argument('--timeout',type=int,default=1800)
a=p.parse_args();kind,identifier=a.selection.split(':',1)
if kind not in ['case','combination']:raise ValueError('Use case:ID or combination:ID')
session=Path(a.session);job=uuid.uuid4().hex
request={'model':json.loads(Path(a.model).read_text()),'selection':{'kind':kind,'id':identifier}}
file=session/'scratch/requests'/(job+'.json');tmp=file.with_suffix('.tmp');tmp.write_text(json.dumps(request,allow_nan=False)+'\n');tmp.replace(file)
reply=session/'solver-replies'/(job+'.json');end=time.monotonic()+a.timeout
while not reply.exists():
 if time.monotonic()>end:raise TimeoutError('Actual solver service timed out; no result or execution inferred')
 time.sleep(.2)
r=json.loads(reply.read_text())
if not r['ok']:raise RuntimeError(r['error'])
state=r['state'];output=Path(a.output_state)
# Retain other actually executed selections only for this exact physical model.
# A repeated selection replaces its old run with the newly executed run.
if output.exists():
 previous=json.loads(output.read_text());old=previous.get('analysisResult',{});new=state['analysisResult']
 if old.get('meta',{}).get('modelHash')==new.get('meta',{}).get('modelHash'):
  new['results']={**old.get('results',{}),**new['results']}
output.write_text(json.dumps(state,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
print(json.dumps({'ok':True,'jobId':job,'state':str(output),'runId':state['analysisResult']['runId'],'selection':a.selection,'capturedSelections':list(state['analysisResult']['results']),'message':'Inspect actual analysisResult results/data. No answer or figure has been generated.'}))
