"""Seal an explicitly selected, source-bound edition from original whole-case trials.

Canonical paths are an index onto original bytes, never rewritten candidate
contexts. All excluded attempts, original dispatch plans, and old reports remain
under their trial IDs. Offline replay uses each trial's exact corpus/context.
"""
import argparse
import json
import subprocess
import zipfile
from pathlib import Path
from archive import sha, file_sha, split_archive


def read(p):
    return json.loads(Path(p).read_text())


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--selection',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();root=Path(__file__).resolve().parents[3]
    selection=read(args.selection);trials={t['id']:t for t in selection['trials']}
    assert len(trials)==len(selection['trials'])
    selected=selection['selected'];assert len(selected)==300 and len({s['caseId'] for s in selected})==300
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    archive=out/'evidence.zip.bin';assert not archive.exists()
    files={};plan=[]
    def tree(folder,prefix):
        for p in sorted(Path(folder).rglob('*')):
            if p.is_file() and not p.is_symlink() and not any(x.endswith('.capture') or x=='__pycache__' for x in p.parts):
                files[prefix+'/'+p.relative_to(folder).as_posix()]=p
    def trial_tree(t):
        work=Path(t['work']);prefix='trials/'+t['id']+'/work'
        for name in ('runs','collected','semantic-reviews','operator-decisions','operator-inspected-files','harness-snapshots','infrastructure-attempts','semantic-review-recoveries'):
            if (work/name).exists():tree(work/name,prefix+'/'+name)
        for p in (work/'assessments').glob('*.json'):files[prefix+'/assessments/'+p.name]=p
        for p in work.iterdir():
            if p.is_file() and p.suffix in ('.json','.jsonl','.log','.tap','.txt'):files[prefix+'/'+p.name]=p
        for p in (work/'solver-jobs').glob('*/*/*'):
            if p.is_file() and p.name!='state.json' and p.suffix in ('.json','.log'):files[prefix+'/'+p.relative_to(work).as_posix()]=p
        tree(Path(t['base']),'trials/'+t['id']+'/public-environment')
        tree(Path(t['corpusRoot']),'corpora/'+t['id'])
    for t in trials.values():trial_tree(t)
    for s in selected:
        t=trials[s['trialId']];work=Path(t['work']);base=Path(t['base']);cid=s['caseId']
        entry=next(c for c in read(work/'plan.json') if c['caseId']==cid)
        receipt=read(work/'runs'/cid/'case-execution.json')
        report=work/'assessments'/f"{cid}-{selection['revision']}.json";grade=read(report)
        assert receipt['status']=='captured' and receipt['capturedTurns']==len(entry['turns'])
        assert grade['status'] in ('passed','agent_failure') and not grade.get('reviewRequests')
        context=base/cid/entry['turns'][0]['id']/'capture-context.json'
        assert read(context)['sourceHash']==s['sourceHash']
        assert file_sha(context)==s['captureContextSha256']
        plan.append(entry)
        for name in ('runs','collected'):tree(work/name/cid,'work/'+name+'/'+cid)
        for name in ('semantic-reviews','operator-decisions','operator-inspected-files'):
            p=work/name/(cid+'.json')
            if p.exists():files['work/'+name+'/'+p.name]=p
        files['work/assessments/'+report.name]=report
        tree(base/cid,'public-environment/'+cid)
    assert sum(len(c['turns']) for c in plan)==420
    plan.sort(key=lambda c:c['caseId'])
    plan_file=out/'selected-plan.json';plan_file.write_text(json.dumps(plan,indent=2)+'\n')
    files['work/plan.json']=plan_file;files['work/selection.json']=args.selection
    for name in ('summary.json','failure-attribution.json','readiness.json','test-verification.json'):
        files['work/'+name]=out/name
    tree(Path(selection['editionRoot']),'edition')
    for a in selection.get('audits',[]):
        p=Path(a['path'])
        if p.is_dir():tree(p,'audits/'+a['id'])
        else:files['audits/'+a['id']+'/'+p.name]=p
    names=subprocess.check_output(['git','-c','safe.directory=*','ls-files','-z','--cached','--others','--exclude-standard','--','lib','scripts','schemas','package.json','package-lock.json'],cwd=root).decode().split('\0')
    guard=[]
    for name in sorted(set(n for n in names if n)):
        p=root/name
        if p.is_file():guard.append({'path':name,'sha256':file_sha(p)});files['implementation/'+name]=p
    manifest=[];blobs=set()
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as z:
        for i,(name,p) in enumerate(sorted(files.items()),1):
            data=p.read_bytes();digest=sha(data)
            if digest not in blobs:z.writestr('blobs/'+digest,data);blobs.add(digest)
            manifest.append({'path':name,'sha256':digest,'bytes':len(data)})
            if i%1000==0:print(json.dumps({'sealed':i,'expected':len(files)}),flush=True)
    (out/'archive-manifest.json').write_text(json.dumps({'schemaVersion':2,'storage':'sha256-addressed-blobs','files':manifest},indent=2)+'\n')
    (out/'source-integrity.json').write_text(json.dumps({'files':guard},indent=2)+'\n')
    meta={'schemaVersion':3,'archive':archive.name,'parts':split_archive(archive),'sha256':file_sha(archive),'bytes':archive.stat().st_size,
          'archiveManifestSha256':file_sha(out/'archive-manifest.json'),'sourceIntegritySha256':file_sha(out/'source-integrity.json'),
          'files':len(manifest),'uniqueBlobs':len(blobs),'revision':selection['revision'],'cases':300,'turns':420,
          'edition':selection['edition'],'selectedTrials':{tid:sum(s['trialId']==tid for s in selected) for tid in trials},
          'scope':'Selected original whole-case calls plus all original trial dispatches, candidate files, prior reports, corpus roots and reference/evaluator amendments. Canonical paths contain unchanged original bytes. Full reference native evidence and numerical audits retained.',
          'repositoryUpload':False}
    (out/'evidence-meta.json').write_text(json.dumps(meta,indent=2)+'\n');print(json.dumps({k:meta[k] for k in ['cases','turns','files','uniqueBlobs','bytes','sha256']}),flush=True)


if __name__=='__main__':main()
