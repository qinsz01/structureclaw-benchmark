"""Install and pin the candidate's public solver client and model API docs."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


def install(base, sut):
    target=Path(base).resolve()/'public-tools';target.mkdir(parents=True,exist_ok=True)
    candidates=list((Path(sut)/'backend').rglob('structure_model_v2.py'))
    if len(candidates)!=1:
        raise ValueError('Expected exactly one pinned SUT model API source')
    sources={'analyze.py':Path(__file__).with_name('analyze.py'),'structure_model_v2.py':candidates[0]}
    files=[]
    for name,source in sources.items():
        raw=source.read_bytes();destination=target/name
        if destination.exists() and destination.read_bytes()!=raw:
            raise ValueError('Existing public tool differs from its pinned source: '+name)
        if not destination.exists():shutil.copyfile(source,destination)
        files.append({'path':name,'source':str(source.resolve()),'sha256':hashlib.sha256(raw).hexdigest()})
    manifest=target/'manifest.json';value={'schemaVersion':1,'files':files}
    if manifest.exists() and json.loads(manifest.read_text())!=value:
        raise ValueError('Existing public tool manifest differs')
    if not manifest.exists():manifest.write_text(json.dumps(value,indent=2)+'\n')
    return value


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--base',required=True);p.add_argument('--sut',required=True);a=p.parse_args()
    print(json.dumps(install(a.base,a.sut)))
