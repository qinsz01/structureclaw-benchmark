"""Install generic client/schema with this edition's public delivery contract."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('frozen_pilot_installer',HERE.parent/'pilot30/setup_public.py')
pilot=importlib.util.module_from_spec(spec);spec.loader.exec_module(pilot)

def install(base,sut):
    # The inherited installer requires a fresh destination and a clean pinned
    # SUT; schema and client bytes are exactly the known public tool closure.
    manifest=pilot.install(base,sut)
    folder=Path(base).resolve()/'public-tools'
    contract=(HERE/'tool-contract.md').read_bytes()
    (folder/'tool-contract.md').write_bytes(contract)
    for row in manifest['files']:
        if row['path']=='tool-contract.md':
            row.update(sha256=hashlib.sha256(contract).hexdigest(),bytes=len(contract))
    notes=(HERE/'native-input-notes.md').read_bytes()
    (folder/'native-input-notes.md').write_bytes(notes)
    manifest['files'].append({'path':'native-input-notes.md','sha256':hashlib.sha256(notes).hexdigest(),'bytes':len(notes)})
    manifest['edition']='research300-v2-v1'
    (folder/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--sut',type=Path,required=True)
    a=p.parse_args();print(json.dumps(install(a.base,a.sut)))
