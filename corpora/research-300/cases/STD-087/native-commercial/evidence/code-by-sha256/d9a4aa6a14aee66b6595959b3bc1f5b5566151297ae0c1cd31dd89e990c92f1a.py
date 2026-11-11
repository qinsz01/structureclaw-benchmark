import os,sys,json,time,traceback,hashlib,shutil
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from native_process import OwnedProcess
root=Path(__file__).resolve().parent
label=sys.argv[1]; length=sys.argv[2]; run=root/label
entry=sys.argv[3] if len(sys.argv)>3 else 'worker'
if entry not in ('worker','reader','frame_worker','frame_reader'): raise ValueError('invalid entry')
run.mkdir(exist_ok=True)
for name in ('worker.py','callback.py','controller.py','sdk_ipc.py','native_process.py','reader.py','frame_worker.py','frame_builder.py','frame_callback.py','frame_reader.py'):
    shutil.copy2(root/name,run/('source-'+name))
env=dict(os.environ);env.update({'PYTHONDONTWRITEBYTECODE':'1','TEMP':str(root/'temp'),'TMP':str(root/'temp')})
(root/'temp').mkdir(exist_ok=True)
receipt={'started':time.time(),'length_mm':length,'argv':[str(root/'runtime/python310/python.exe'),'-B',str(root/(entry+'.py')),label,length]}
try:
    with OwnedProcess(receipt['argv'],root,run/'stdout.log',run/'stderr.log',env) as p:
        receipt['worker_pid']=p.pid
        deadline=time.monotonic()+900
        while p.poll() is None:
            if (run/'cancel.request').exists():
                receipt['cancelledByOwnedRequest']=True;p.cancel();break
            if time.monotonic()>deadline:
                receipt['timeout']=True;p.cancel();break
            time.sleep(.2)
        receipt['returncode']=p.wait(timeout=30)
except BaseException:
    receipt['exception']=traceback.format_exc()
finally:
    receipt['ended']=time.time();receipt['containment']='Windows Job Object owned child tree; closed on all paths'
    receipt['files']=[{'path':str(p.relative_to(run)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in run.rglob('*') if p.is_file()]
    (run/'receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print(json.dumps(receipt,indent=2))
