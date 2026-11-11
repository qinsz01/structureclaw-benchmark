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
    from YJKAPI import DataFunc,BzcPara,Hi_AddToAndReadYjk,GKLoadDefCreateInfo,ControlConfig,YJKSControl
    from sdk_ipc import SdkPipe,verify_host
    d=DataFunc(); floor=d.StdFlr_Generate(L,0.,0.,'', 'CAL')
    p=BzcPara();p.setVal(1,0);p.setVal(24,356);p.setVal(25,356);floor.Para=p.GetValString()
    j=d.Joint_Generate(floor.ID,0.,0.,0.)
    s=d.ColSect_Def(5,1,'300,600','RECT')
    col=d.column_arrange(j,s,0,0,rotation,0)
    if coefficients is not None:
        if len(coefficients)!=6 or any(type(v) not in (int,float) or not math.isfinite(v) or v<=0 for v in coefficients): raise ValueError('invalid six rigidity coefficients')
        shapeval=','.join(format(v,'.17g') for v in coefficients)+','
        d.property_arrange(int(col.ID),'SpBarRig',27,shapeval)
    # vendor nodal load format: FdownZ,Mx,My,Fx,Fy,Mz,angle
    vals={'FX':[0,0,0,1,0,0,0],'FY':[0,0,0,0,1,0,0],'FZ':[-1,0,0,0,0,0,0],
          'MX':[0,1,0,0,0,0,0],'MY':[0,0,1,0,0,0,0],'MZ':[0,0,0,0,0,1,0]}
    ids={}
    for name,v in vals.items():
        info=GKLoadDefCreateInfo();info.SetDeadFacotr(0.);info.SetLiveFacotr(0,0.,0.,0.);info.SetName(name);info.SetData('0,1,1,1,1,1,1,1,1,')
        case=d.GKLoad_Def(info);load=d.Load_Def(-1,','.join(map(str,v)),name);d.load_arrange([j],load,case.kind);ids[name]=int(case.kind)
    for load in d.GetLoadSegList():
        load.strParas1='0,0,0,0,0,';load.strParasX='';load.strParasY='';load.strParasZ=''
    d.Floor_Assemb(floor,0,L,'L1');d.DbModel_Assign()
    bridge=Hi_AddToAndReadYjk(d.GetDbModelData()); ok=bridge.CreateYDB(str(RUN),'cal.ydb')
    dump('input.json',{'length_mm':L,'section_mm':[300,600],'material':'steel Q355 (356)','load_format':'FdownZ,Mx,My,Fx,Fy,Mz,angle','loads':vals,'kinds':ids,'ydb_created':bool(ok),'joint':int(j.ID),'column':int(col.ID),'rotation_degrees':rotation,'stiffness_request':request})
    if not ok: raise RuntimeError('CreateYDB returned false')
    if coefficients is not None:
        ydb=RUN/'cal.ydb'
        if list(RUN.glob('*.ymd')): raise RuntimeError('must repair before native import')
        shutil.copy2(ydb,RUN/'cal-sdk-original.ydb')
        before_hash=hashlib.sha256(ydb.read_bytes()).hexdigest()
        with sqlite3.connect(ydb) as db:
            rows=db.execute("SELECT ID,Type,ShapeVal FROM tblProperty WHERE Name='SpBarRig'").fetchall()
            if len(rows)!=1 or rows[0][:2]!=(int(col.ID),27):raise RuntimeError('ambiguous native property')
            original=rows[0][2]; rounded=[float(t) for t in original.split(',') if t.strip()]
            if len(rounded)!=6 or any(abs(a-b)>.005001 for a,b in zip(rounded,coefficients)): raise RuntimeError('unexpected serialization beyond rounding')
            db.execute("UPDATE tblProperty SET ShapeVal=? WHERE ID=? AND Name='SpBarRig' AND Type=27",(shapeval,int(col.ID)))
            after=db.execute("SELECT ShapeVal FROM tblProperty WHERE ID=? AND Name='SpBarRig' AND Type=27",(int(col.ID),)).fetchone()[0]
            if after!=shapeval:raise RuntimeError('precision readback mismatch')
        dump('input-precision.json',{'member':int(col.ID),'before':original,'after':after,'before_sha256':before_hash,'after_sha256':hashlib.sha256(ydb.read_bytes()).hexdigest(),'scope':'new exchange input prior to native import; only one tblProperty.ShapeVal value'})
    log('built',length_mm=L)
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
    callback=RUN/('native_cb_'+RUN.name.replace('-','_')+'.py');callback.write_text((ROOT/'callback.py').read_text(encoding='utf-8'),encoding='utf-8')
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
