"""Freeze final numerical evidence and relevant failed maintainer attempts."""
import argparse
import os
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[2]
def sha(data):return hashlib.sha256(data).hexdigest()
def read(p):return json.loads(p.read_text())
def write(p,v):
    with p.open('x') as f:f.write(json.dumps(v,ensure_ascii=False,indent=2)+'\n')


def archive(review):
    review.mkdir(parents=True,exist_ok=True);files={}
    def add(file,name):
        assert name not in files,name
        files[name]=file
    def tree(folder,prefix):
        for p in sorted(folder.rglob('*')):
            if p.is_file() and '__pycache__' not in p.parts:add(p,prefix+'/'+p.relative_to(folder).as_posix())
    work=ROOT/'.bench-work';final=read(review/'qualification-summary.json')
    assert final['allPassed'] and final['candidateCalls']==0
    tree(ROOT/'corpora/research300-v2-pilot30-v1','edition')
    tree(work/'pilot30-authoring-r3-20261028','executed-edition')
    tree(work/'pilot30-oracle-r3-20261028','oracle')
    tree(work/'pilot30-qualification-final-r5-20261028','qualification')
    tree(work/'pilot30-final-tools-r2-20261028/public-tools','public-tools')
    for name in ['pilot30-authoring-r1-20261028','pilot30-authoring-r2-20261028','pilot30-authoring-r4-20261028',
                 'pilot30-qualification-r1-20261028','pilot30-qualification-r2-20261028','pilot30-qualification-final-20261028','pilot30-qualification-final-r2-20261028','pilot30-qualification-final-r3-20261028','pilot30-qualification-final-r4-20261028']:
        folder=work/name
        if folder.exists():tree(folder,'attempts/'+name)
    # Retain both initial failures in full; successful R1 jobs duplicate R3 physics.
    old=work/'pilot30-oracle-r1-20261028';failed=[]
    for p in sorted((old/'solver-jobs').glob('*/*/broker-receipt.json')):
        if not read(p)['ok']:
            tree(p.parent,'attempts/oracle-r1/solver-jobs/'+p.parent.parent.name+'/'+p.parent.name)
            failed.append(p.parent.parent.name)
    for cid in set(failed):tree(old/'runs'/cid,'attempts/oracle-r1/runs/'+cid)
    for name in ['execution-summary.json','broker.log','broker.stderr','remote-setup.json','remote-source-manifest.json']:
        add(old/name,'attempts/oracle-r1/'+name)
    for name in ['pilot30-input-review-final-20261028.json','pilot30-physics-final-r5-20261028.log','pilot30-public-schema-final-20261028.json','pilot30-packaging-final-r2-20261028.json']:
        add(work/name,'reviews/'+name)
    guarded=read(Path(os.environ.get('SCLAW_BENCH_ARCHIVE', ROOT)).expanduser()/'docs/implementation/reviews/codex-diversity300-20261027/source-integrity.json')['files']
    paths={f['path'] for f in guarded}
    paths.update(p.relative_to(ROOT).as_posix() for p in (ROOT/'scripts/pilot30').iterdir() if p.is_file())
    implementation=[]
    for name in sorted(paths):
        p=ROOT/name;add(p,'implementation/'+name);implementation.append({'path':name,'sha256':sha(p.read_bytes())})
    sut=ROOT/'.worktrees/structureclaw-pkpm-shear-fix-20261027'
    for f in read(work/'pilot30-oracle-r3-20261028/remote-source-manifest.json'):
        name=f['path'].removeprefix('upstream/')
        p=sut/name if f['path'].startswith('upstream/') else ROOT/'scripts/research300/codex_trial'/name
        assert sha(p.read_bytes())==f['sha256'];add(p,'sut/'+name)
    # Production recovery code is generated JS and separately byte-bound.
    for p in sorted((sut/'backend/dist/engineering').rglob('*')):
        if p.is_file():add(p,'sut/'+p.relative_to(sut).as_posix())
    rows=[];target=review/'evidence.zip.bin'
    with zipfile.ZipFile(target,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for name,p in sorted(files.items()):
            data=p.read_bytes();z.writestr(name,data);rows.append({'path':name,'sha256':sha(data),'bytes':len(data)})
    write(review/'archive-manifest.json',{'schemaVersion':1,'files':rows})
    write(review/'archive.json',{'schemaVersion':1,'file':target.name,'bytes':target.stat().st_size,'sha256':sha(target.read_bytes()),
          'manifestSha256':sha((review/'archive-manifest.json').read_bytes()),'implementationFiles':implementation,
          'failedMaintainerJobsRetained':len(failed),'candidateCalls':0})
    return {'files':len(rows),'bytes':target.stat().st_size,'failedJobs':len(failed)}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--review',type=Path,required=True);a=p.parse_args();print(json.dumps(archive(a.review.resolve())))
