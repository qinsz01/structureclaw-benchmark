"""Own just one vendor process tree, in a separate Windows scheduled task."""
import hashlib,json,os,sys,time,traceback
from pathlib import Path
JOB=Path(__file__).resolve().parent;ROOT=JOB.parent.parent;sys.path.insert(0,str(ROOT));from owned_process import OwnedProcess
engine=sys.argv[1];python=r'C:\PKPM2027R1.0.1\Ribbon\PythonEnv\python.exe' if engine=='pkpm' else r'D:\bench-native\yjk-fa71b3bfa4\runtime\python310\python.exe'
args=[python,'-B',str(JOB/'engine.py'),engine];temp=JOB/'temp';temp.mkdir(exist_ok=False);env={**os.environ,'TEMP':str(temp),'TMP':str(temp),'PYTHONDONTWRITEBYTECODE':'1'}
r={'engine':engine,'argv':args,'startedAt':time.time(),'executableSha256':hashlib.sha256(Path(python).read_bytes()).hexdigest(),'containment':'new owned Windows Job Object'}
try:
 with OwnedProcess(args,JOB,JOB/'stdout.log',JOB/'stderr.log',env) as child:
  r['pid']=child.pid;(JOB/'running.json').write_text(json.dumps(r),encoding='utf8');r['returncode']=child.wait(timeout=900)
 r['status']='completed' if r['returncode']==0 else 'failed'
except BaseException:r.update(status='failed',error=traceback.format_exc())
finally:
 r.update(completedAt=time.time(),ownedJobClosed=True);(JOB/'process-receipt.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf8')
