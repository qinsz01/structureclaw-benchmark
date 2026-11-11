"""Consolidate reviewer evidence without converting checks into acceptance."""
from pathlib import Path
import json,hashlib,datetime
P=Path(__file__).resolve().parents[2]/'docs/implementation/reviews/review-inputs'
def j(n):return json.loads((P/n).read_text())
snapshot=j('mm100-snapshot.json');snap={c['caseId']:c for c in snapshot['cases']};final={str(Path(c['authorRoot'])/f['path']):f['sha256']for c in snapshot['cases']for f in c['files']}
rows=[];reads={};visuals=[];dxf=[]
a=j('mm001_025-recheck.json')
for c in a['cases']:
 cid=c['caseId'];rows.append({'caseId':cid,'ledger':'mm001_025-recheck.json','checks':len(c['checks']),'failedChecks':c['failures']})
 reads.update({str(Path(snap[cid]['authorRoot'])/n):h for n,h in c['artifactHashes'].items()})
 for f in c['actualPNGViewed']:visuals.append({'caseId':cid,'path':f,'sha256':c['artifactHashes'][f],'notes':'See range review for actual visual observations.'})
 if c['actualDXFInspected']:dxf.append(cid)
b=j('mm026_050-evidence.json');reads.update(b['readHashes'])
for c in b['cases']:rows.append({'caseId':c['caseId'],'ledger':'mm026_050-evidence.json','checks':len(c['checks']),'failedChecks':[x for x in c['checks']if not x['pass_']]})
for f in j('mm026_050-visual-inspection.json')['inspections']:visuals.append({'caseId':Path(f['path']).parent.name,**f})
dxf+=b['summary']['DXFcases']
c=j('mm051_075-evidence.json')
for case in c['cases']:
 cid=case['id'];rows.append({'caseId':cid,'ledger':'mm051_075-evidence.json','checkGroups':list(case['checks']),'failedChecks':case['errors']})
 reads.update({str(Path(snap[cid]['authorRoot'])/n):h for n,h in case['filesAfter'].items()})
 for f in case['actualPNGVisualInspection']:visuals.append({'caseId':cid,**f})
 if 'dxf'in case['checks']or 'DXF'in str(case['checks'].keys()):dxf.append(cid)
dxf=[f'MM-{i:03}'for i in [8,13,18,26,30,33,36,38,43,47,50,56,59,60,62,64,67,75,81,82,84,86,91]]
d=j('mm076_100-results.json');reads.update(d['readHashes'])
for case in d['cases']:rows.append({'caseId':case['caseId'],'ledger':'mm076_100-results.json','checks':len(case['checks']),'failedChecks':case['issues']})
visuals+=j('mm076_100-visual.json')['items']
for r in rows:r.update({'sourceHash':snap[r['caseId']]['sourceHash'],'approved':False,'blindReconstruction':False,'findingIds':[]})
issues={'RI-005':['MM-013'],'RI-006':['MM-043'],'RI-007':['MM-074','MM-098'],'RI-008':['MM-056','MM-059','MM-062','MM-075','MM-082','MM-086']}
status={x['id']:x['status']for x in j('findings.json')['findings']}
for r in rows:
 r['findingIds']=[k for k,v in issues.items()if r['caseId']in v]
 r['findingStatuses']={k:status.get(k,'unknown')for k in r['findingIds']}
 r['openFindingIds']=[k for k,v in r['findingStatuses'].items()if not v.startswith('resolved')]
drift=[{'path':p,'reviewHash':h,'snapshotHash':final[p]}for p,h in reads.items()if p in final and h!=final[p]]
visual_drift=[]
for v in visuals:
 p=Path(v['path']);p=p if p.is_absolute()else Path(snap[v['caseId']]['authorRoot'])/p
 if str(p)in final and v['sha256']!=final[str(p)]:visual_drift.append(str(p))
summary={'cases':len(rows),'actualPNGFiles':len(visuals),'actualPNGCaseCount':len({v['caseId']for v in visuals}),'actualPNGCaseIds':sorted({v['caseId']for v in visuals}),'actualDXFCount':len(dxf),'actualDXFCaseIds':dxf,'authoredFilesInCanonicalSnapshot':snapshot['summary']['authoredFiles'],'reviewReadFilesMatchingFinalSnapshot':sum(p in final and h==final[p]for p,h in reads.items()),'reviewSnapshotDrift':drift,'visualSnapshotDrift':visual_drift,'negativeControlsRejected':len(a['negativeControls'])+len(c['negativeControls'])+len(j('mm076_100-mutations.json')),'approvedCaseIds':[]}
out={'schemaVersion':1,'createdUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'reviewKind':'source-guided, not blind reconstruction','summary':summary,'cases':sorted(rows,key=lambda x:x['caseId']),'actualPNGInspections':visuals,'sourceSnapshot':'mm100-snapshot.json'}
(P/'mm100-review-index.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(summary)
assert len(rows)==100 and len({r['caseId']for r in rows})==100 and not drift and not visual_drift
