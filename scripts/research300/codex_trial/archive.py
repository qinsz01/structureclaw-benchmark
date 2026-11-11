"""Seal original full-trial evidence as deduplicated, hash-addressed local bytes."""
import argparse, hashlib, json, subprocess, zipfile
from pathlib import Path

def sha(data): return hashlib.sha256(data).hexdigest()
def file_sha(path):
    digest=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): digest.update(block)
    return digest.hexdigest()

def split_archive(archive,part_bytes=32*1024*1024):
    parts=[]
    with archive.open('rb') as f:
        while True:
            block=f.read(part_bytes)
            if not block: break
            p=archive.with_name(f'evidence.part{len(parts)+1:03}.bin')
            with p.open('xb') as target: target.write(block)
            parts.append({'file':p.name,'bytes':len(block),'sha256':sha(block)})
    return parts

def main():
    ap=argparse.ArgumentParser()
    for name in ('work','base','output'): ap.add_argument('--'+name,type=Path,required=True)
    ap.add_argument('--revision',required=True)
    a=ap.parse_args(); root=Path(__file__).resolve().parents[3]; w=a.work.resolve(); out=a.output.resolve(); out.mkdir(exist_ok=True)
    archive=out/'evidence.zip.bin'
    if archive.exists(): raise ValueError('Retain existing archive; use an explicit new evidence directory')
    plan=json.loads((w/'plan.json').read_text())
    assert len(plan)==300 and sum(len(c['turns']) for c in plan)==420
    for c in plan:
        receipt=json.loads((w/'runs'/c['caseId']/'case-execution.json').read_text())
        report=json.loads((w/'assessments'/f"{c['caseId']}-{a.revision}.json").read_text())
        assert receipt['status']=='captured' and all(t['completedTurn'] for t in receipt['turns'])
        assert not report.get('reviewRequests') and report['status'] in ('passed','agent_failure')
    files={}
    def addtree(folder,prefix):
        for p in sorted(folder.rglob('*')):
            if p.is_file() and not p.is_symlink() and not any(s.endswith('.capture') or s=='__pycache__' for s in p.parts):
                files[prefix+'/'+p.relative_to(folder).as_posix()]=p
    for name in ('runs','semantic-reviews','operator-decisions','operator-inspected-files','harness-snapshots','infrastructure-attempts','semantic-review-recoveries'):
        if (w/name).exists(): addtree(w/name,'work/'+name)
    for case in plan:
        folder=w/'collected'/case['caseId']
        for name in ('events.jsonl','states.json','collection.json'):
            files['work/collected/'+case['caseId']+'/'+name]=folder/name
        for name in ('native-captures','artifacts'): addtree(folder/name,'work/collected/'+case['caseId']+'/'+name)
    for p in sorted((w/'assessments').glob('*.json')): files['work/assessments/'+p.name]=p
    for p in sorted(w.iterdir()):
        if p.is_file() and p.suffix in ('.json','.jsonl','.log','.tap','.py','.txt'): files['work/'+p.name]=p
    # Canonical collection above includes original worker captures and the
    # native files used by every gate. Keep job dispatch/error/audit records;
    # large duplicate vendor projects remain in the original work directory.
    for p in sorted((w/'solver-jobs').glob('*/*/*')):
        if p.is_file() and not p.is_symlink() and p.name!='state.json' and p.suffix in ('.json','.log'):
            files['work/'+p.relative_to(w).as_posix()]=p
    for p in sorted((w/'solver-jobs').rglob('native-physics-audit.json')):
        files['work/'+p.relative_to(w).as_posix()]=p
    addtree(a.base.resolve(),'public-environment')
    manifest=[]; blobs=set()
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as z:
        for index,(name,p) in enumerate(sorted(files.items()),1):
            data=p.read_bytes(); digest=sha(data)
            if digest not in blobs: z.writestr('blobs/'+digest,data); blobs.add(digest)
            manifest.append({'path':name,'sha256':digest,'bytes':len(data)})
            if index%1000==0: print(json.dumps({'filesSealed':index,'filesExpected':len(files)}),flush=True)
    (out/'archive-manifest.json').write_text(json.dumps({'schemaVersion':2,'storage':'sha256-addressed-blobs','files':manifest},indent=2)+'\n')
    tracked=subprocess.check_output(['git','-c','safe.directory='+str(root),'ls-files','-z','--','lib','scripts','corpora/research-300','package.json','package-lock.json'],cwd=root).decode().split('\0')
    guarded=[]
    for name in sorted(set(n for n in tracked if n)):
        p=root/name
        if p.is_file(): guarded.append({'path':name,'sha256':sha(p.read_bytes())})
    (out/'source-integrity.json').write_text(json.dumps({'files':guarded},indent=2)+'\n')
    meta={'schemaVersion':2,'archive':archive.name,'parts':split_archive(archive),'sha256':file_sha(archive),'bytes':archive.stat().st_size,
          'archiveManifestSha256':file_sha(out/'archive-manifest.json'),'sourceIntegritySha256':file_sha(out/'source-integrity.json'),
          'files':len(manifest),'uniqueBlobs':len(blobs),'revision':a.revision,'cases':300,'turns':420,
          'scope':'All original candidate turns, public sandbox files, canonical offline inputs/native evidence, reviews, prior reports, harness revisions and job dispatch/diagnostics. Duplicate full vendor project directories retained in original work, outside this replay archive.',
          'repositoryUpload':False}
    (out/'evidence-meta.json').write_text(json.dumps(meta,indent=2)+'\n');print(json.dumps(meta),flush=True)

if __name__=='__main__': main()
