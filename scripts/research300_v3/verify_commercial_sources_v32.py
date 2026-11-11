"""Read-only source/install checks on the existing authorized native host."""
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def verify(remote_state, sut):
    remote_state, sut = Path(remote_state), Path(sut)
    setup = json.loads((remote_state / 'remote-setup.json').read_bytes())
    source = remote_state / 'remote-source-manifest.json'
    rows = json.loads(source.read_bytes())
    for row in rows:
        if row['path'].startswith('upstream/'):
            local = sut / row['path'][len('upstream/'):]
        elif row['path'] == 'owned_process.py':
            local = ROOT / 'scripts/research300/codex_trial/owned_process.py'
        else:
            raise ValueError('Unknown remote source path')
        if hashlib.sha256(local.read_bytes()).hexdigest() != row['sha256']:
            raise ValueError('Remote pin differs from local frozen source: ' + row['path'])
    spec = importlib.util.spec_from_file_location('v32_numeric_remote', ROOT / 'scripts/research300/codex_trial/remote.py')
    transport = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(transport)
    quote = transport.quote
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    script = ('$r=' + quote(setup['root']) + '; $m=Join-Path $r "source-manifest.json"; '
              '$mh=(Get-FileHash -Algorithm SHA256 -LiteralPath $m).Hash.ToLower(); '
              'if($mh -ne ' + quote(digest) + '){throw "Remote source manifest changed"}; '
              '$files=Get-Content -Raw -LiteralPath $m | ConvertFrom-Json; $bad=@(); '
              'foreach($f in $files){$p=Join-Path $r $f.path; '
              'if(!(Test-Path -LiteralPath $p) -or (Get-FileHash -Algorithm SHA256 -LiteralPath $p).Hash.ToLower() -ne $f.sha256){$bad+=$f.path}}; '
              '[ordered]@{host=$env:COMPUTERNAME;root=$r;sourceCount=$files.Count;sourceManifestSha256=$mh;sourceMismatches=$bad;'
              'pkpmPython=(Test-Path "C:\\PKPM2027R1.0.1\\Ribbon\\PythonEnv\\python.exe");'
              'yjkPython=(Test-Path "D:\\bench-native\\yjk-fa71b3bfa4\\runtime\\python310\\python.exe")} | ConvertTo-Json -Depth 5 -Compress')
    result = json.loads(transport.powershell(script, timeout=55))
    result['allPassed'] = (not result['sourceMismatches'] and result['sourceCount'] == len(rows)
                           and result['pkpmPython'] and result['yjkPython'])
    result['localSourceHashesMatched'] = True
    return result
