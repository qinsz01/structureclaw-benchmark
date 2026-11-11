"""The candidate gets only generic protocol/schema/client documentation."""
import argparse
import hashlib
import json
from pathlib import Path
from .support import V2,load

def install(base,sut):
    manifest=load('v3_frozen_tool_installer',V2/'setup_public.py').install(base,sut)
    folder=Path(base).resolve()/'public-tools'
    (folder/'quantity-contract.md').write_bytes((folder/'tool-contract.md').read_bytes())
    (folder/'tool-contract.md').write_bytes(Path(__file__).with_name('tool-contract.md').read_bytes())
    manifest['files']=[{'path':p.relative_to(folder).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in sorted(folder.rglob('*')) if p.is_file() and p.name!='manifest.json']
    manifest['edition']='research300-v3-v1';(folder/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');return manifest

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--sut',type=Path,required=True);a=p.parse_args();print(json.dumps(install(a.base,a.sut)))
