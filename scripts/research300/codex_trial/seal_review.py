"""Bind explicitly written operator decisions to the exact inspected review requests."""
import argparse,datetime,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--case',required=True);p.add_argument('--revision',required=True);p.add_argument('--decisions',type=Path,required=True);a=p.parse_args();W=a.work.resolve();report=json.loads((W/'assessments'/f'{a.case}-{a.revision}.json').read_text());decisions=json.loads(a.decisions.read_text());requests={(q['turnId'],q['outputId']):q for q in report.get('reviewRequests',[])};assessments=[]
if not requests or not isinstance(decisions,list) or not decisions:raise ValueError('No pending semantic requests or explicit decisions to seal')
keys=[(d.get('turnId'),d.get('outputId')) for d in decisions]
if len(keys)!=len(set(keys)) or set(keys)!=set(requests):raise ValueError('Exactly one explicit decision is required for every pending semantic request')
for decision in decisions:
 key=(decision['turnId'],decision['outputId']);q=requests[key]
 if not isinstance(decision['pass'],bool) or not isinstance(decision['reason'],str) or len(decision['reason'].strip())<20:raise ValueError('Explicit substantive operator decision required')
 fields=['caseId','turnId','outputId','state','sourceHash','inputBinding','currentResponseSha256','activitySha256','figureSha256'];assessments.append({**{k:q[k] for k in fields if k in q},'pass':decision['pass'],'reason':decision['reason'],'reviewerId':'codex-root-operator-review-20261027','reviewedAt':datetime.datetime.now(datetime.timezone.utc).isoformat()})
folder=W/'semantic-reviews';folder.mkdir(exist_ok=True);out=folder/f'{a.case}.json'
if out.exists():raise ValueError('Review already sealed; choose explicit versioned review recovery rather than replacing decisions')
out.write_text(json.dumps({'schemaVersion':1,'corpus':'research-300','assessments':assessments},ensure_ascii=False,indent=2)+'\n');print(json.dumps({'caseId':a.case,'operatorDecisionsBound':len(assessments),'pending':len(requests)-len(assessments)}))
