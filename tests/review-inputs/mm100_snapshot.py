"""Freeze canonical authored-file hashes, live author revisions, and integration lag.
Only reads author/root cases and writes reviewer evidence. No acceptance status.
"""
from pathlib import Path
import json,hashlib,datetime,os
ROOT=Path(os.environ.get('REVIEW_INPUTS_SHARED_ROOT','/mnt/nas/qsz/01research/02structureclaw-bench'))
OUT=Path(__file__).resolve().parents[2]/'docs/implementation/reviews/review-inputs'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def case_manifest(p):
 c=json.loads((p/'contract.json').read_text());names=set(['contract.json','prompt.txt','reference-requests.json']+c['modelStates']+c['attachments']);files=[{'path':n,'sha256':digest(p/n)}for n in sorted(names,key=lambda v:v.encode('utf8'))]
 payload={'schemaVersion':1,'files':files};h=hashlib.sha256(json.dumps(payload,ensure_ascii=False,separators=(',',':')).encode()).hexdigest();return h,files
cases=[]
for i in range(1,101):
 cid=f'MM-{i:03}';author='mm-a'if i<=50 else'mm-b';p=ROOT/f'.worktrees/{author}/corpora/research-300/cases'/cid
 h,files=case_manifest(p);rootp=ROOT/'corpora/research-300/cases'/cid;root_hash,root_files=case_manifest(rootp);root_map={x['path']:x['sha256']for x in root_files};author_map={x['path']:x['sha256']for x in files}
 cases.append({'caseId':cid,'authorRoot':str(p),'sourceHash':h,'files':files,'integratedRootSourceHash':root_hash,'rootDifferentFiles':sorted(k for k in author_map.keys()|root_map.keys()if author_map.get(k)!=root_map.get(k)),'approved':False})
messages={}
for n in ['root-message.md','mm-a-message.md','mm-b-message.md','mm-asset-review-message.md']:
 p=ROOT/'.bench-work/state'/n;messages[n]={'sha256':digest(p),'text':p.read_text()}
out={'schemaVersion':1,'createdUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'reviewKind':'source-directed non-blind review','approved':False,'sourceFiles':{str(p):digest(p)for p in (ROOT/'planning/sources').iterdir()if p.is_file()},'authorMessages':messages,'cases':cases,'summary':{'cases':len(cases),'authoredFiles':sum(len(c['files'])for c in cases),'rootDifferentCases':[c['caseId']for c in cases if c['rootDifferentFiles']]}}
out['summary']['changedDuringSnapshot']=[str(Path(c['authorRoot'])/f['path']) for c in cases for f in c['files'] if digest(Path(c['authorRoot'])/f['path'])!=f['sha256']]
assert not out['summary']['changedDuringSnapshot'], out['summary']['changedDuringSnapshot']
(OUT/'mm100-snapshot.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(out['summary'])
