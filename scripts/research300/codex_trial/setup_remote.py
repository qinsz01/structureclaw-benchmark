"""Install only pinned source copies into a new isolated trial directory; no vendor/config edits."""
import argparse,hashlib,io,json,uuid,zipfile
from pathlib import Path
from remote import powershell,quote,upload
p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--sut',type=Path,required=True);a=p.parse_args();w=a.work.resolve();sut=a.sut.resolve();here=Path(__file__).resolve().parent
remote=r'D:\bench-native\codex-full300-20261027-'+uuid.uuid4().hex[:12];files=[]
for base in [sut/'backend/src/agent-skills/analysis',sut/'backend/src/skill-shared/python']:
 for f in base.rglob('*.py'):
  if '__tests__' not in f.parts and '__pycache__' not in f.parts:files.append((f,'upstream/'+f.relative_to(sut).as_posix()))
files.append((here/'owned_process.py','owned_process.py'));stream=io.BytesIO();sources=[]
with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as z:
 for file,name in files:
  b=file.read_bytes();z.writestr(name,b);sources.append({'path':name,'sha256':hashlib.sha256(b).hexdigest()})
 z.writestr('source-manifest.json',json.dumps(sources,indent=2)+'\n')
data=stream.getvalue();(w/'remote-source-payload.zip.bin').write_bytes(data);digest=upload(data,remote+r'\payload.zip');assert digest.lower()==hashlib.sha256(data).hexdigest()
script='$r='+quote(remote)+'; Expand-Archive -LiteralPath ($r+"\\payload.zip") -DestinationPath $r; $bad=@(); foreach($f in (Get-Content -Raw -LiteralPath ($r+"\\source-manifest.json") | ConvertFrom-Json)){if((Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $r $f.path)).Hash.ToLower() -ne $f.sha256){$bad+=$f.path}}; if($bad.Count){throw "Source hash mismatch"}; [ordered]@{host=$env:COMPUTERNAME;user=$env:USERNAME;root=$r;sources='+str(len(sources))+';sourceHashesVerified=$true;pkpmPython=(Test-Path "C:\\PKPM2027R1.0.1\\Ribbon\\PythonEnv\\python.exe");yjkPython=(Test-Path "D:\\bench-native\\yjk-fa71b3bfa4\\runtime\\python310\\python.exe")} | ConvertTo-Json -Compress'
receipt=json.loads(powershell(script));assert receipt['sourceHashesVerified'] and receipt['pkpmPython'] and receipt['yjkPython'];(w/'remote-setup.json').write_text(json.dumps(receipt,indent=2)+'\n');(w/'remote-source-manifest.json').write_text(json.dumps(sources,indent=2)+'\n');print(json.dumps(receipt))
