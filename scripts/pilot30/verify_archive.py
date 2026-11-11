"""Verify retained pilot bytes and optionally replay maintainer qualification offline."""
import argparse
import hashlib
import json
from pathlib import Path,PurePosixPath
import subprocess
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parents[2]
def sha(data):return hashlib.sha256(data).hexdigest()
def read(p):return json.loads(p.read_text())


def verify(review,replay=False):
    meta=read(review/'archive.json');manifest=read(review/'archive-manifest.json')
    assert sha((review/'archive-manifest.json').read_bytes())==meta['manifestSha256']
    bundle=review/meta['file'];assert bundle.name==meta['file']
    assert sha(bundle.read_bytes())==meta['sha256']
    names=[r['path'] for r in manifest['files']]
    assert len(names)==len(set(names)) and all(not PurePosixPath(n).is_absolute() and '..' not in PurePosixPath(n).parts for n in names)
    with zipfile.ZipFile(bundle) as z:
        assert sorted(z.namelist())==sorted(names)
        for r in manifest['files']:
            data=z.read(r['path']);assert len(data)==r['bytes'] and sha(data)==r['sha256'],r['path']
        def value(n):return json.loads(z.read(n))
        ed=value('edition/manifest.json');expected=value('qualification/summary.json')
        execution=value('oracle/execution-summary.json');oldhash=sha(z.read('executed-edition/manifest.json'))
        assert expected['manifestSha256']==sha(z.read('edition/manifest.json'))
        assert expected['executionManifestSha256']==execution['manifestSha256']==oldhash
        calls=0;turns=0;ids=set();engine_jobs={}
        for c in ed['cases']:
            for t in c['turns']:
                capture=value(f'oracle/runs/{c["id"]}/{t["id"]}/capture.json')
                assert capture['maintainerOracle'] and not capture['candidateCall'] and capture['manifestSha256']==oldhash
                for jid in capture['currentJobIds']:
                    assert jid not in ids;ids.add(jid)
                    prefix=f'oracle/solver-jobs/{c["id"]}/{jid}/'
                    receipt=value(prefix+'broker-receipt.json');assert receipt['ok'] and receipt['role']=='oracle'
                    assert receipt['stateSha256']==sha(z.read(prefix+'state.json'))
                    engine_jobs[c['engine']]=engine_jobs.get(c['engine'],0)+1
                turns+=1
        assert len(ids)==execution['nativeJobs'] and turns==expected['turns']==52 and len(ed['cases'])==30
        assert expected['allPassed'] and expected['failedControls']==0 and expected['candidateCalls']==0
        for f in meta['implementationFiles']:
            assert sha((ROOT/f['path']).read_bytes())==f['sha256'],f['path']
        result={'filesVerified':len(names),'caseCount':30,'turnCount':turns,'nativeJobs':len(ids),'nativeJobsByEngine':engine_jobs,
                'candidateCalls':calls,'controls':expected['controls'],'allPassed':True}
        if replay:
            with tempfile.TemporaryDirectory(prefix='pilot30-offline-') as tmp:
                tmp=Path(tmp)
                for n in names:
                    needed=n.startswith(('edition/','executed-edition/')) or n=='oracle/execution-summary.json'
                    needed=needed or n.startswith('oracle/runs/') and Path(n).name in ['capture.json','scheme-jobs.json']
                    needed=needed or n.startswith('oracle/solver-jobs/') and Path(n).name in ['state.json','model.json','request.json','broker-receipt.json']
                    if needed:
                        p=tmp/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(n))
                p=subprocess.run(['node',str(ROOT/'scripts/pilot30/qualify.cjs'),'--edition',str(tmp/'edition'),
                    '--execution-edition',str(tmp/'executed-edition'),'--work',str(tmp/'oracle'),'--output',str(tmp/'replay')],
                    capture_output=True,text=True,timeout=600)
                assert p.returncode==0,p.stderr+p.stdout[-2000:]
                actual=read(tmp/'replay/summary.json');assert actual==expected,'Offline qualification summary differs'
                for file in (tmp/'replay').iterdir():
                    assert file.read_bytes()==z.read('qualification/'+file.name),'Offline result differs: '+file.name
                result['offlineReplay']={'passedTurns':actual['passedTurns'],'controls':actual['controls'],'failedControls':actual['failedControls'],'identicalFiles':len(list((tmp/'replay').iterdir()))}
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--review',type=Path,required=True);p.add_argument('--replay',action='store_true');a=p.parse_args()
    print(json.dumps(verify(a.review.resolve(),a.replay),indent=2))
