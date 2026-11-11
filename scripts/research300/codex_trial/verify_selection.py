"""Verify all 420 actual calls and optionally replay all 300 offline evaluations."""
import argparse, hashlib, json, subprocess, tempfile, zipfile
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path, PurePosixPath

ROOT=Path(__file__).resolve().parents[3]
HERE=None
def sha(data): return hashlib.sha256(data).hexdigest()
def file_sha(path):
    digest=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): digest.update(block)
    return digest.hexdigest()
def read(path): return json.loads(path.read_text())

@contextmanager
def open_archive(meta):
    if not meta.get('parts'):
        archive=HERE/meta['archive']; assert file_sha(archive)==meta['sha256']
        with zipfile.ZipFile(archive) as z: yield z
        return
    # The original joined archive need not exist. Reconstruct exactly the same
    # bytes from individually checked small parts into an unnamed temp file.
    with tempfile.TemporaryFile() as raw:
        whole=hashlib.sha256(); total=0
        for part in meta['parts']:
            assert Path(part['file']).name==part['file']
            data=(HERE/part['file']).read_bytes()
            assert len(data)==part['bytes'] and sha(data)==part['sha256']
            raw.write(data); whole.update(data); total+=len(data)
        assert total==meta['bytes'] and whole.hexdigest()==meta['sha256']
        raw.seek(0)
        with zipfile.ZipFile(raw) as z: yield z

def main():
    global HERE
    ap=argparse.ArgumentParser(); ap.add_argument('--archive',type=Path,required=True); ap.add_argument('--extract-edition',type=Path); ap.add_argument('--replay',action='store_true'); ap.add_argument('--workers',type=int,choices=range(1,9),default=4); a=ap.parse_args();HERE=a.archive.resolve()
    meta=read(HERE/'evidence-meta.json')
    assert file_sha(HERE/'archive-manifest.json')==meta['archiveManifestSha256']
    assert file_sha(HERE/'source-integrity.json')==meta['sourceIntegritySha256']
    entries=read(HERE/'archive-manifest.json')['files']; files={e['path']:e for e in entries}; assert len(files)==len(entries)
    for e in entries:
        p=PurePosixPath(e['path']); assert not p.is_absolute() and '..' not in p.parts
    with open_archive(meta) as z:
        blobs={e['sha256'] for e in entries}; assert set(z.namelist())=={'blobs/'+h for h in blobs}
        sizes={}
        for h in sorted(blobs):
            data=z.read('blobs/'+h); assert sha(data)==h; sizes[h]=len(data)
        assert all(sizes[e['sha256']]==e['bytes'] for e in entries)
        def data(name): return z.read('blobs/'+files[name]['sha256'])
        def obj(name): return json.loads(data(name))
        plan=obj('work/plan.json'); selection=obj('work/selection.json'); selected={r['caseId']:r for r in selection['selected']}; assert len(plan)==len(selected)==300; calls=0; threads=set()
        def source_hash(prefix):
            contract=obj(prefix+'/contract.json')
            names=sorted(set(['contract.json','prompt.txt','reference-requests.json']+contract.get('attachments',[])+contract.get('modelStates',[])),key=lambda s:s.encode())
            record={'schemaVersion':1,'files':[{'path':n,'sha256':sha(data(prefix+'/'+n))} for n in names]}
            return sha(json.dumps(record,separators=(',',':'),ensure_ascii=False).encode())
        for case in plan:
            cid=case['caseId']; receipt=obj(f'work/runs/{cid}/case-execution.json')
            origin='corpora/'+selected[cid]['trialId']
            assert source_hash(origin+'/corpora/research-300/cases/'+cid)==selected[cid]['sourceHash']
            assert source_hash('edition/corpora/research-300/cases/'+cid)==selected[cid]['sourceHash']
            def public_hashes(prefix):
                prefix+='/corpora/research-300/public-inputs/'+cid+'/'
                return {n[len(prefix):]:e['sha256'] for n,e in files.items() if n.startswith(prefix)}
            assert public_hashes(origin) and public_hashes(origin)==public_hashes('edition'),cid
            assert receipt['status']=='captured' and receipt['capturedTurns']==len(case['turns'])
            thread=None
            for t in case['turns']:
                prefix=f"work/runs/{cid}/{t['id']}"; ex=obj(prefix+'/execution.json'); dispatch=obj(prefix+'/dispatch.json')
                events=[json.loads(line) for line in data(prefix+'/events.jsonl').splitlines() if line.strip()]
                assert ex['completedTurn'] and ex['exitCode']==0 and not ex['timedOut'] and not ex['invalidJsonLines']
                assert dispatch['actualModelCall'] and dispatch['publicOnly'] and dispatch['model']=='gpt-6.1-sol' and dispatch['reasoningEffort']=='high'
                assert sha(data(prefix+'/prompt.txt'))==dispatch['promptSha256']
                assert any(e.get('type')=='turn.completed' for e in events)
                assert any(e.get('type')=='thread.started' and e.get('thread_id')==ex['threadId'] for e in events)
                answers=[e['item']['text'] for e in events if e.get('type')=='item.completed' and e.get('item',{}).get('type')=='agent_message']
                assert answers and data(prefix+'/answer.txt').decode().rstrip('\n')==answers[-1].rstrip('\n')
                if thread is not None: assert dispatch['parentThread']==thread==ex['threadId']
                else: assert dispatch['parentThread'] is None and ex['threadId'] not in threads
                thread=ex['threadId']; threads.add(thread)
                isolation=obj(prefix+'/isolation.json'); assert isolation['exitCode']==0
                probes=json.loads(isolation['stdout']); assert len(probes)>=4 and all(p['readable'] for p in probes[:3]) and not any(p.get('readable',False) for p in probes[3:]) and not probes[-1].get('networkAccessible')
                if ex['statePresent']: assert sha(data(prefix+'/state.json'))==ex['stateSha256']
                context=data(f'public-environment/{cid}/{t["id"]}/capture-context.json')
                assert json.loads(context)['sourceHash']==selected[cid]['sourceHash']
                if t['id']==case['turns'][0]['id']:assert sha(context)==selected[cid]['captureContextSha256']
                original=f'trials/{selected[cid]["trialId"]}/work/runs/{cid}/{t["id"]}'
                for name in ['events.jsonl','answer.txt','dispatch.json','execution.json','prompt.txt','isolation.json']:assert data(prefix+'/'+name)==data(original+'/'+name)
                calls+=1
        assert calls==420 and len(threads)==300
        result={'archiveSha256':meta['sha256'],'filesVerified':len(entries),'uniqueBlobsVerified':len(blobs),'actualCallsVerified':calls,'actualCaseThreadsVerified':len(threads)}
        if a.extract_edition:
            assert not a.extract_edition.exists()
            for name in files:
                if name.startswith('edition/'):
                    dest=a.extract_edition/name[len('edition/'):];dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data(name))
            result['editionExtracted']=str(a.extract_edition)
        if a.replay:
            guarded=read(HERE/'source-integrity.json')['files']
            for e in guarded: assert sha((ROOT/e['path']).read_bytes())==e['sha256'],e['path']
            with tempfile.TemporaryDirectory(prefix='codex-diversity-offline-') as tmp:
                tmp=Path(tmp)
                for name in files:
                    if name.startswith(('work/collected/','work/semantic-reviews/','corpora/')) or name.startswith('public-environment/') and name.endswith('/capture-context.json'):
                        dest=tmp/name; dest.parent.mkdir(parents=True,exist_ok=True); dest.write_bytes(data(name))
                def replay(case):
                    cid=case['caseId']; c=tmp/'work/collected'/cid
                    # File-only archives do not contain empty directories;
                    # text-only cases legitimately have no figure artifacts.
                    for name in ('artifacts','native-captures'): (c/name).mkdir(parents=True,exist_ok=True)
                    cmd=['node',str(ROOT/'scripts/evaluate-results.cjs'),'--root',str(tmp/'corpora'/selected[cid]['trialId']),'--format','codex','--input',str(c/'events.jsonl'),'--states',str(c/'states.json'),'--context',str(tmp/'public-environment'/cid/case['turns'][0]['id']/'capture-context.json'),'--artifact-root',str(c/'artifacts'),'--capture-root',str(c/'native-captures'),'--output',str(tmp/(cid+'-replay.json'))]
                    assessment=tmp/'work/semantic-reviews'/f'{cid}.json'
                    if assessment.exists():cmd+=['--assessments',str(assessment)]
                    process=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,timeout=240)
                    assert (tmp/(cid+'-replay.json')).exists(),(cid,process.returncode,process.stdout,process.stderr)
                    actual=read(tmp/(cid+'-replay.json')); expected=obj(f"work/assessments/{cid}-{meta['revision']}.json")
                    assert actual['status']==expected['status'] and not actual.get('reviewRequests'),(cid,process.returncode,actual.get('status'),expected['status'],process.stderr)
                    def gates(report):
                        return [(t['turnId'],[(m['metric'],m['pass'],m.get('status')) for m in t['evaluation']['metrics']]) for c in report['cases'] for t in c['evaluation']['turns']]
                    assert gates(actual)==gates(expected),(cid,'gate decisions changed')
                    return {'caseId':cid,'status':actual['status'],'turns':len(actual['cases'][0]['evaluation']['turns'])}
                # Read archive reports before concurrent work: ZipFile reads are
                # internally synchronized, and each evaluator has a new output.
                with ThreadPoolExecutor(max_workers=a.workers) as pool: result['offlineReplay']=list(pool.map(replay,plan))
                assert len(result['offlineReplay'])==300 and sum(c['turns'] for c in result['offlineReplay'])==420
            result['sourceFilesVerified']=len(guarded)
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
