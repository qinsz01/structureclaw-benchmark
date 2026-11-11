"""Throwaway native SDK calibration: no benchmark source data or SUT execution."""
import sys, os, json, time, subprocess, traceback, sqlite3, hashlib, shutil, math
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
RUN=ROOT/sys.argv[1]
L=int(sys.argv[2]); RUN.mkdir(exist_ok=True)
RUNTIME=ROOT/'runtime'
request_path=ROOT/(RUN.name+'.request.json')
request=json.loads(request_path.read_text(encoding='utf-8')) if request_path.exists() else {}
rotation=float(request.get('rotation_degrees',0.))
coefficients=request.get('stiffness_coefficients')
sys.argv[:]=[str(Path(__file__).resolve()),'NDepend']
os.environ['PATH']=str(RUNTIME)+os.pathsep+os.environ['PATH']
_dll=os.add_dll_directory(str(RUNTIME))
def dump(name,value): (RUN/name).write_text(json.dumps(value,indent=2,ensure_ascii=False),encoding='utf-8')
def log(event,**kw):
    row={'time':time.time(),'event':event,**kw}
    with (RUN/'steps.jsonl').open('a',encoding='utf-8') as f: f.write(json.dumps(row,ensure_ascii=False)+'\n')
    print(json.dumps(row,ensure_ascii=False),flush=True)
try:
    from YJKAPI import ControlConfig,YJKSControl
    from sdk_ipc import SdkPipe,verify_host
    from frame_builder import build
    model=json.loads((ROOT/'frame-a.json').read_text(encoding='utf-8'))
    mapping=build(model,RUN)
    log('built',nodes=len(model['nodes']),members=len(model['elements']))
    exe=RUNTIME/'yjks.exe';verify_host(exe)
    # Existing authorization is observed only; never start/attach/reinvoke its launcher.
    launcher=None
    log('launcher_not_started',reason='existing licensed desktop session; no action on existing launcher')
    cfg=ControlConfig();cfg.Version='8.0.0';cfg.Invisible=True;YJKSControl.initConfig(cfg)
    os.chdir(RUNTIME);YJKSControl.RunYJK(str(exe))
    ps="Get-CimInstance Win32_Process -Filter \"ParentProcessId = %d\" | Select-Object ProcessId,ParentProcessId,ExecutablePath,CommandLine | ConvertTo-Json -Compress"%os.getpid()
    rows=json.loads(subprocess.check_output(['powershell','-NoProfile','-NonInteractive','-Command',ps],encoding='utf-8'))
    if isinstance(rows,dict): rows=[rows]
    hosts=[x for x in rows if os.path.normcase(str(x.get('ExecutablePath'))) == os.path.normcase(str(exe)) and '-yjkscontrol' in str(x.get('CommandLine'))]
    if len(hosts)!=1: raise RuntimeError('Cannot uniquely prove owned native host: '+repr(rows))
    host=hosts[0];cfg.Pid=int(host['ProcessId']);YJKSControl.initConfig(cfg);dump('owned-native.json',{'worker_pid':os.getpid(),'launcher_pid':None,'native':host})
    # callback locates this run via its own private copy.
    callback=RUN/('native_cb_'+RUN.name.replace('-','_')+'.py');callback.write_text((ROOT/'frame_callback.py').read_text(encoding='utf-8'),encoding='utf-8')
    with SdkPipe(cfg.Pid,connect_timeout_s=90,command_timeout_s=300) as pipe:
        def cmd(name,*args):
            log('command_start',command=name,args=args);value=pipe.command(name,*args);log('command_end',command=name,response=value)
        cmd('UINew',str(RUN/'cal.yjk'));cmd('yjk_importydb',str(RUN/'cal.ydb'))
        cmd('yjks_pyload',str(callback),'apply_controls')
        if not (RUN/'controls.json').exists(): raise RuntimeError('Native controls callback produced no receipt')
        for name in ('yjk_repair','yjk_save','yjk_setlayersupport','yjkspre_genmodrel','yjktransload_tlplan','yjktransload_tlvert'):
            cmd(name)
        cmd('SetCurrentLabel','IDSPRE_ROOT');cmd('yjkdesign_dsncalculating_all')
        cmd('yjks_pyload',str(callback),'extract')
        if not (RUN/'results.json').exists(): raise RuntimeError('Native results callback produced no receipt')
    log('finished')
except BaseException:
    try:
        if 'host' in globals():
            raw=subprocess.check_output([sys.executable,'-B',str(ROOT/'inspect_windows.py'),str(host['ProcessId'])],encoding='utf-8')
            (RUN/'startup-windows.json').write_text(raw,encoding='utf-8')
    except BaseException: pass
    (RUN/'error.txt').write_text(traceback.format_exc(),encoding='utf-8');traceback.print_exc();raise
