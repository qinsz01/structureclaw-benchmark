"""Run the pinned production commercial adapter; only numeric candidate input is accepted."""
import hashlib,importlib.util,json,os,sys,time,traceback
from pathlib import Path
JOB=Path(__file__).resolve().parent;ROOT=JOB.parent.parent;engine=sys.argv[1];src=ROOT/'upstream/backend/src';paths=[src/'skill-shared/python',src/'agent-skills/analysis/runtime',src/('agent-skills/analysis/'+engine+'-static')]
for directory in paths:sys.path.insert(0,str(directory))
request=json.loads((JOB/'request.json').read_text(encoding='utf8'));receipt={'engine':engine,'startedAt':time.time(),'interpreter':sys.executable,'requestSha256':hashlib.sha256((JOB/'request.json').read_bytes()).hexdigest()}
try:
 if engine=='pkpm':
  base=Path(r'C:\PKPM2027R1.0.1');dirs=[base/'Ribbon/PM',base/'Ribbon',base/'CFG',base/'Ribbon/SAT'];handles=[os.add_dll_directory(str(d)) for d in dirs if d.is_dir()]
  os.environ['PATH']=os.pathsep.join(map(str,dirs))+os.pathsep+os.environ.get('PATH','');os.environ['PKPM_CYCLE_PATH']=str(base/'PkpmCycle/JWSCYCLE.exe');os.environ['PKPM_WORK_DIR']=str(JOB/'projects')
 else:
  os.environ['YJKS_ROOT']=os.environ['YJK_PATH']=r'D:\bench-native\yjk-fa71b3bfa4\runtime';os.environ['YJK_PYTHON_BIN']=r'D:\bench-native\yjk-fa71b3bfa4\runtime\python310\python.exe';os.environ['YJK_WORK_DIR']=str(JOB/'projects');os.environ['YJK_TIMEOUT_S']='300';os.environ['YJK_STARTUP_TIMEOUT_S']='90';os.environ['YJK_COMMAND_TIMEOUT_S']='90'
 spec=importlib.util.spec_from_file_location('trial_'+engine,paths[-1]/'runtime.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 raw=module.run_analysis(request['model'],request['parameters']);(JOB/'result.json').write_text(json.dumps(raw,ensure_ascii=False,indent=2),encoding='utf8');receipt.update(status='completed',resultStatus=raw.get('status'))
except BaseException as e:receipt.update(status='failed',error=str(e),traceback=traceback.format_exc(),errorCode=getattr(e,'error_code',None),detail=getattr(e,'detail',None))
finally:
 receipt['completedAt']=time.time();(JOB/'adapter-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2,default=str),encoding='utf8')
sys.exit(0 if receipt.get('status')=='completed' else 1)
