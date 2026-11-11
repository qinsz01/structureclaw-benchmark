"""Public numeric client: request JSON contains only your model and analysis inputs."""
import argparse
import json
from pathlib import Path
import time
import uuid

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--request',type=Path,required=True);p.add_argument('--session',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--timeout',type=float,default=1500);a=p.parse_args()
    request=json.loads(a.request.read_text());job=uuid.uuid4().hex
    dest=a.session/'scratch/requests'/f'{job}.json';temp=dest.with_suffix('.tmp')
    temp.write_text(json.dumps(request,ensure_ascii=False,allow_nan=False)+'\n');temp.replace(dest)
    reply=a.session/'solver-replies'/f'{job}.json';deadline=time.monotonic()+a.timeout
    while not reply.exists():
        if time.monotonic()>deadline:raise TimeoutError('Actual analysis service timed out')
        time.sleep(.1)
    r=json.loads(reply.read_text())
    if not r['ok']:raise RuntimeError(r['error'])
    a.output.write_text(json.dumps(r,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'ok':True,'jobId':job,'output':str(a.output)}))
