"""Numeric-only transport to the already authorized Windows solver host."""
import base64,os,shlex,subprocess,tempfile,uuid
from pathlib import Path

# The Windows solver host is configured locally, never committed.
HOST=os.environ.get('SCLAW_NATIVE_HOST','sclaw-native-host')

def powershell(script,input_bytes=None,timeout=55):
 ps="[Console]::OutputEncoding=[System.Text.Encoding]::UTF8; $ProgressPreference='SilentlyContinue'; $ErrorActionPreference='Stop'; "+script
 command='powershell -NoProfile -NonInteractive -EncodedCommand '+base64.b64encode(ps.encode('utf-16le')).decode()
 inner=shlex.join(['ssh','-o','BatchMode=yes','-o','ClearAllForwardings=yes','-o','ConnectTimeout=12',HOST,command])
 r=subprocess.run(['ssh','-A','-o','ClearAllForwardings=yes','-o','BatchMode=yes','codex_qsz',inner],input=input_bytes,capture_output=True,timeout=timeout)
 if r.returncode:raise RuntimeError('Windows transport failed: '+r.stderr.decode(errors='replace')[-2000:]+' '+r.stdout.decode(errors='replace')[-2000:])
 return r.stdout.decode('utf-8-sig').strip()
def quote(value):return "'"+str(value).replace("'","''")+"'"
def transfer(path,data=None):
 jump='/tmp/scodex300-transfer-'+uuid.uuid4().hex
 def run(argv):
  r=subprocess.run(argv,capture_output=True,timeout=180)
  if r.returncode:raise RuntimeError('Numeric file transfer failed: '+r.stderr.decode(errors='replace')[-2000:])
 def hop(argv):run(['ssh','-A','-o','BatchMode=yes','-o','ClearAllForwardings=yes','codex_qsz',shlex.join(argv)])
 hop(['mkdir','-p',jump])
 try:
  with tempfile.TemporaryDirectory(prefix='scodex300-transfer-') as folder:
   local=Path(folder)/'payload.bin';target=HOST+':'+path.replace('\\','/')
   if data is not None:
    local.write_bytes(data)
    powershell('[IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName('+quote(path)+')) | Out-Null; "DIRECTORY_READY"')
    run(['scp','-q','-o','ClearAllForwardings=yes',str(local),'codex_qsz:'+jump+'/payload.bin'])
    hop(['scp','-q','-o','BatchMode=yes','-o','ClearAllForwardings=yes',jump+'/payload.bin',target])
    return powershell('(Get-FileHash -LiteralPath '+quote(path)+' -Algorithm SHA256).Hash')
   hop(['scp','-q','-o','BatchMode=yes','-o','ClearAllForwardings=yes',target,jump+'/payload.bin'])
   run(['scp','-q','-o','ClearAllForwardings=yes','codex_qsz:'+jump+'/payload.bin',str(local)])
   return local.read_bytes()
 finally:hop(['rm','-rf','--',jump])
def upload(data,path):return transfer(path,data)
def download(path):return transfer(path)
