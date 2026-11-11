"""Meaningful controls run on private temporary copies, never owner files."""
import json, tempfile, shutil, math
from pathlib import Path
import mm076_100_review as review
original=review.ROOT
models={x['taskId']:x for x in json.loads((original/'planning/sources/all-models-engines-v2.json').read_text())}
tasks={x['id']:x for x in json.loads((original/'planning/sources/all-tasks-engines-v2.json').read_text())}
def collapse_offset(m):
 for n in m['nodes']:
  if n['z']==7.2:n['x']-=1

def reverse_source_sign(m):
 for l in m['load_cases'][0]['loads']:
  if l['type']=='nodal':l['fy']=5

def wrong_roll(m):
 for e in m['elements']:
  if e['type']=='column':e['rotation_angle']=90

def projected_length(m):
 nodes={n['id']:n for n in m['nodes']};es={e['id']:e for e in m['elements']}
 for l in m['load_cases'][0]['loads']:
  a,b=[nodes[n]for n in es[l['element']]['nodes']]
  if a['z']!=b['z']:l['wz']*=6/math.sqrt(40)

def collapse_load(m):
 for l in m['load_cases'][0]['loads']:l['node']='top'

def wrong_midpoint(m):
 for n in m['nodes']:
  if n['id']=='obs1':n['x']=2

cases=[(76,'midpoint shifted',wrong_midpoint),(79,'offset flattened',collapse_offset),(90,'roll applied to every column',wrong_roll),(92,'projected instead of actual slope load',projected_length),(94,'source Fw sign not negated',reverse_source_sign),(100,'arm-tip forces moved to column top',collapse_load)]
results=[]
with tempfile.TemporaryDirectory(prefix='review-inputs-mm-controls-')as tmp:
 review.ROOT=Path(tmp)
 for i,desc,mut in cases:
  cid=f'MM-{i:03}';relative=Path('.worktrees/mm-b/corpora/research-300/cases')/cid;shutil.copytree(original/relative,review.ROOT/relative)
  path=review.ROOT/relative/'model-state-1.json';m=json.loads(path.read_text());mut(m);path.write_text(json.dumps(m))
  c=review.check_case(i,tasks[cid],models[cid]);results.append({'caseId':cid,'mutation':desc,'rejected':bool(c['issues']),'failedChecks':c['issues']})
(review.OUT/'mm076_100-mutations.json').write_text(json.dumps(results,indent=2)+'\n')
print(f'{sum(r["rejected"]for r in results)}/{len(results)} negative controls rejected')
assert all(r['rejected']for r in results)
