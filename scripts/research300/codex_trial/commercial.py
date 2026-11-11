"""Trusted numeric-only native commercial execution. No gold model or expected values are read."""
import argparse,base64,fcntl,hashlib,io,json,re,subprocess,time,zipfile
from pathlib import Path
from remote import powershell,quote,upload,download
from native_error import native_error
p=argparse.ArgumentParser();p.add_argument('--job',type=Path,required=True);p.add_argument('--engine',choices=['PKPM','YJK'],required=True);p.add_argument('--sut',type=Path,required=True);p.add_argument('--reference-binding',type=Path);p.add_argument('--native-lock',type=Path);a=p.parse_args()
job=a.job.resolve();work=job.parents[2];case=job.parent.name;helpers=Path(__file__).resolve().parent;remote=json.loads((work/'remote-setup.json').read_text())['root'];lower=a.engine.lower();remotejob=remote+'\\jobs\\'+job.name;task='SClawCodex300-'+job.name
with (a.native_lock or work/'commercial-native.lock').open('a') as lease:
 fcntl.flock(lease,fcntl.LOCK_EX)
 # Each case has one sequentially active turn. Capture only its identity/state
 # binding, not any hidden model, output request or expected response.
 if a.reference_binding:
  binding=json.loads(a.reference_binding.read_text())
  if binding.get('caseId')!=case or binding.get('engine')!=a.engine or binding.get('executionRole')!='reference-verification' or type(binding.get('state')) is not int or binding['state']<1 or not re.fullmatch('[a-f0-9]{64}',binding.get('sourceHash','')):raise ValueError('Invalid reference execution binding')
 else:
  active=[p for p in (work/'runs'/case).glob('t*') if (p/'dispatch.json').exists() and not (p/'execution.json').exists()]
  if len(active)!=1:raise RuntimeError('Ambiguous active commercial turn')
  plan=json.loads((work/'plan.json').read_text());entry=next(c for c in plan if c['caseId']==case);turn=next(t for t in entry['turns'] if t['id']==active[0].name);context=json.loads(Path(turn['context']).read_text());state=next(t['state'] for t in context['turns'] if t['turnId']==turn['id'])
  binding={'caseId':case,'turnId':turn['id'],'state':state,'sourceHash':context['sourceHash'],'engine':a.engine,'executionRole':'candidate-tool-call'}
 with (job/'binding.json').open('x') as f:f.write(json.dumps(binding,indent=2)+'\n')
 model=json.loads((job/'model.json').read_text());parameters=json.loads((job/'worker-request.json').read_text())['input']['parameters'];request={'model':model,'parameters':parameters};stream=io.BytesIO()
 with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as z:
  z.writestr('request.json',json.dumps(request,ensure_ascii=False)+'\n');z.write(helpers/'windows_engine.py','engine.py');z.write(helpers/'windows_controller.py','controller.py')
 payload=stream.getvalue();(job/'remote-job-payload.zip.bin').write_bytes(payload);digest=upload(payload,remotejob+'\\payload.zip');assert digest.lower()==hashlib.sha256(payload).hexdigest()
 python=r'C:\PKPM2027R1.0.1\Ribbon\PythonEnv\python.exe' if lower=='pkpm' else r'D:\bench-native\yjk-fa71b3bfa4\runtime\python310\python.exe'
 script='$j='+quote(remotejob)+'; Expand-Archive -LiteralPath ($j+"\\payload.zip") -DestinationPath $j; $action=New-ScheduledTaskAction -Execute '+quote(python)+' -Argument '+quote('-B "'+remotejob+'\\controller.py" '+lower)+' -WorkingDirectory $j; $principal=New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Highest; Register-ScheduledTask -TaskName '+quote(task)+' -Action $action -Principal $principal -Description "Isolated Codex benchmark candidate native execution" | Out-Null; Start-ScheduledTask -TaskName '+quote(task)+'; [ordered]@{task='+quote(task)+';root=$j;started=$true} | ConvertTo-Json -Compress'
 (job/'remote-launch.json').write_text(powershell(script)+'\n');deadline=time.monotonic()+1100
 try:
  while True:
   status=powershell('$p='+quote(remotejob+'\\process-receipt.json')+'; if(Test-Path -LiteralPath $p){Get-Content -Raw -LiteralPath $p}else{"PENDING"}')
   if status!='PENDING':receipt=json.loads(status);break
   if time.monotonic()>deadline:raise TimeoutError('Native scheduled task timed out')
   time.sleep(3)
  (job/'remote-process-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
  # Collect original numeric inputs, native files, errors and logs even on failure.
  collect=r'''import hashlib,json,zipfile,sys
from pathlib import Path
root=Path(sys.argv[1]);files=[]
for p in root.rglob('*'):
 if p.is_file() and not any(s in ['temp','__pycache__'] for s in p.relative_to(root).parts) and p.name not in ['payload.zip','evidence.zip','evidence-manifest.json'] and p.suffix.lower() not in ['.exe','.dll','.pyd','.pyc']:
  files.append(p)
manifest=[{'path':p.relative_to(root).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]
(root/'evidence-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
with zipfile.ZipFile(root/'evidence.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in files:z.write(p,p.relative_to(root).as_posix())
 z.write(root/'evidence-manifest.json','evidence-manifest.json')
print(hashlib.sha256((root/'evidence.zip').read_bytes()).hexdigest())
'''
  encoded=base64.b64encode(collect.encode()).decode();script='$code=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('+quote(encoded)+')); & '+quote(python)+' -c $code '+quote(remotejob)+'; if($LASTEXITCODE -ne 0){throw "Native collection failed"}'
  expected=powershell(script).splitlines()[-1].strip();data=download(remotejob+'\\evidence.zip');assert hashlib.sha256(data).hexdigest()==expected.lower();(job/'remote-evidence.zip.bin').write_bytes(data)
  native=job/'native';native.mkdir()
  with zipfile.ZipFile(io.BytesIO(data)) as z:
   for name in z.namelist():
    if Path(name).is_absolute() or '..' in Path(name).parts:raise RuntimeError('Unsafe native archive path')
   z.extractall(native)
  for row in json.loads((native/'evidence-manifest.json').read_text()):assert hashlib.sha256((native/row['path']).read_bytes()).hexdigest()==row['sha256']
  if receipt.get('returncode')!=0 or not receipt.get('ownedJobClosed'):
   diagnostic=json.loads((native/'adapter-receipt.json').read_text()) if (native/'adapter-receipt.json').exists() else {}
   # Return the actual adapter's actionable error, not an unreadable private path.
   # This is normal solver/API feedback, never grading or reference feedback.
   error=native_error(native,diagnostic,receipt)
   (job/'public-native-error.json').write_text(json.dumps(error,ensure_ascii=False,indent=2)+'\n')
   raise RuntimeError(json.dumps(error,ensure_ascii=False))
  result=subprocess.run(['node',str(helpers/'package-commercial.cjs'),str(job),str(a.sut.resolve())],capture_output=True,text=True,timeout=60);(job/'commercial-packaging.log').write_text(result.stdout+result.stderr)
  if result.returncode:raise RuntimeError('Native packaging/verification failed: '+result.stderr[-4000:])
 finally:
  # Stop/delete only this task. Its controller owns only this job's child tree.
  cleanup=powershell('$t=Get-ScheduledTask -TaskName '+quote(task)+' -ErrorAction SilentlyContinue; if($t){if($t.State -eq "Running"){Stop-ScheduledTask -TaskName '+quote(task)+'};Unregister-ScheduledTask -TaskName '+quote(task)+' -Confirm:$false}; "OWN_TASK_REMOVED"')
  (job/'remote-task-cleanup.txt').write_text(cleanup+'\n')
print(json.dumps({'ok':True,'jobId':job.name,'engine':a.engine,'nativeEvidence':str(job/'native')}))
