"""Install only generic public client, protocol and pinned schema sources."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def install(base,sut):
    base=Path(base).resolve();sut=Path(sut).resolve()
    commit=subprocess.check_output(['git','-c','safe.directory=*','-C',str(sut),'rev-parse','HEAD'],text=True).strip()
    assert commit=='db3c0b1da44fe668a6037a6c2e7f068d14354539'
    assert not subprocess.check_output(['git','-c','safe.directory=*','-C',str(sut),'status','--porcelain','--untracked-files=no'],text=True).strip()
    folder=base/'public-tools';folder.mkdir(parents=True,exist_ok=False)
    here=Path(__file__).resolve().parent;schema=sut/'backend/src/skill-shared/python/structure_protocol'
    files={'analyze.py':(here/'analyze.py').read_bytes(),'tool-contract.md':(here/'tool-contract.md').read_bytes(),
           'structure_protocol/__init__.py':b''}
    for name in ['structure_model_v2.py','design_properties.py','section_properties.py','load_contract.py']:
        files['structure_protocol/'+name]=(schema/name).read_bytes()
    rows=[]
    for name,raw in files.items():
        p=folder/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
        rows.append({'path':name,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)})
    manifest={'sutCommit':commit,'role':'generic-public-tools-only','files':rows}
    (folder/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--sut',type=Path,required=True);a=p.parse_args()
    print(json.dumps(install(a.base,a.sut)))
