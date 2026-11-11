"""Authoring invariants and source-specific regression checks for MM-B, no oracle values."""
from pathlib import Path
import json,math,re,hashlib,sys
import numpy as np
from PIL import Image
from mm_b_common import ROOT,ROWS,SOURCE_TASKS,length

def check_case(cid):
 d=ROOT/'corpora/research-300/cases'/cid;c=json.loads((d/'contract.json').read_text());m=json.loads((d/'model-state-1.json').read_text());r=json.loads((d/'reference-requests.json').read_text())['states'][0]
 assert c['id']==cid and c['sourcePlan']['sourceRequirements']==ROWS[cid]['sourceRequirements']
 for k in ('modelId','language','family','plannedEngine'):assert c[k]==ROWS[cid][k],(cid,k)
 assert c['status']=='authored-candidate' and c['sameEngineTruthStatus']=='pending' and c['inputBlindReview']=='pending' and c['llmEndToEnd']=='not-run'
 assert len(c['turns'])==SOURCE_TASKS[cid]['turns']
 expected={x['id'] for x in ROWS[cid]['requirements']};actual=[x for v in c['requirementCoverage'] for x in v['requirementIds']];assert expected==set(actual) and len(actual)==len(expected)
 assert len(c['attachments'])==len(set(c['attachments']))
 for f in c['attachments']:
  assert (d/f).is_file(),(cid,'missing',f)
  assert not any(w in f for w in ('model-state','reference','author-review'))
  if f.endswith('.png'):
   with Image.open(d/f) as im:im.verify()
  if f.endswith('.svg'):assert '<svg' in (d/f).read_text() and '<metadata' not in (d/f).read_text()
 for t in c['turns']:assert set(t['attachments'])<=set(c['attachments'])
 assert c['turns'][-1]['state']==1 and c['turns'][-1]['expectation']=='analyze'
 ns={n['id']:n for n in m['nodes']};es={e['id']:e for e in m['elements']};assert len(ns)==len(m['nodes']) and len(es)==len(m['elements'])
 points=[tuple(round(n[k],10) for k in ('x','y','z')) for n in m['nodes']];assert len(set(points))==len(points),(cid,'duplicate nodes')
 adjacency={n:set() for n in ns};pairs=[]
 mats={x['id']:x for x in m['materials']};secs={x['id']:x for x in m['sections']}
 for e in es.values():
  a,b=e['nodes'];assert a in ns and b in ns and a!=b and length(m,e)>1e-8;adjacency[a].add(b);adjacency[b].add(a);pairs.append(tuple(sorted((a,b))))
  assert e['material'] in mats and e['section'] in secs
  assert all(secs[e['section']]['properties'][k]>0 for k in ('A','Iy','Iz','J'))
  if m['coordinate_system']['dimension']=='3d':
   u=np.array([ns[b][k]-ns[a][k] for k in ('x','y','z')]);v=m['metadata']['elementReferenceVectors'][e['id']];assert np.linalg.norm(np.cross(u,v))>1e-8
 assert len(set(pairs))==len(pairs),(cid,'duplicate members')
 seen=set();stack=[next(iter(ns))]
 while stack:
  a=stack.pop()
  if a not in seen:seen.add(a);stack.extend(adjacency[a]-seen)
 assert seen==set(ns),(cid,'disconnected nodes')
 assert all(len(n['restraints'])==6 for n in ns.values())
 assert all(mat['E']>0 and abs(mat['G']-mat['E']/(2*(1+mat['nu'])))<1e-6 for mat in mats.values())
 assert m['coordinate_system']['semantics']=='global-z-up' and m['unit_system']=='SI'
 assert all(m['analysis_control'][k] is False for k in ('self_weight','rigid_floor','p_delta','rigid_offsets','construction_stage'))
 cases={x['id']:x for x in m['load_cases']};combos={x['id']:x for x in m['load_combinations']}
 for lc in cases.values():
  assert len({l['id'] for l in lc['loads']})==len(lc['loads'])
  for ld in lc['loads']:
   assert ld['reference_frame']=='global'
   if ld['type']=='nodal':assert ld['node'] in ns
   else:assert ld['element'] in es and es[ld['element']]['type']!='truss'
 for co in combos.values():assert set(co['factors'])<=set(cases)
 qids={q['id'] for q in r['quantities']};assert len(qids)==len(r['quantities'])
 for q in r['quantities']:
  assert 'value' not in q and q['selection']['id'] in (cases if q['selection']['kind']=='case' else combos)
  loc=q['location'];assert loc['id'] in (ns if loc['kind']=='node' else es)
  if loc['kind']=='member':assert 0<=loc['positionM']<=length(m,es[loc['id']])+1e-8 and loc['side'] in ('left','right')
 for der in r['derived']:assert set(der['operands'])<=qids
 allq=qids|{v['id'] for v in r['derived']};outputq={q for o in c['requiredOutputs'] for q in o['quantityIds']};assert allq==outputq
 assert any(x['kind']=='figure' for x in c['requiredOutputs'])
 # No public topology/coordinate table bypass.
 assignments=json.loads((d/'assignments.json').read_text());assert all(not any(k in a for k in ('ends','nodes','x','y','z')) for a in assignments)
 if c['locale']=='en':
  for text in [(d/'prompt.txt').read_text(),*[t['instruction'] for t in c['turns']]]:assert not re.search('[\u4e00-\u9fff]',text),(cid,'English text contains Chinese')
 if 'DXF' in ROWS[cid]['subcategory']:
  dx=(d/'input.dxf').read_text('ascii');assert '\nLINE\n' in dx and dx.endswith('0\nEOF\n')
  if ROWS[cid]['subcategory']=='建筑DXF':assert 'S-BEAM' in dx and 'A-EQUIPMENT' in dx and 'A-WALL' in dx
 if cid in ('MM-053','MM-095'):assert 'loads.json' not in c['attachments']
 if cid in ('MM-058','MM-072'):
  assert c['turns'][0]['state'] is None and c['turns'][0]['expectation']=='clarify'
  assert not (set(c['turns'][0]['attachments']) & set(c['turns'][1]['attachments']))
  svgs=''.join((d/f).read_text() for f in c['turns'][0]['attachments'] if f.endswith('.svg'))
  if cid=='MM-058':assert 'FIXED' not in svgs and 'LOCK ' not in svgs
  else:
   labels=re.findall(r'<text[^>]*>(.*?)</text>',svgs)
   assert not any(v in ('3.8','7.8','10.9','0.5') for v in labels)
   assert 'NOT TO SCALE' in svgs
 if cid=='MM-094':
  ld=json.loads((d/'loads.json').read_text());forces=[l for lc in ld['load_cases'] for l in lc['loads'] if l['type']=='nodal'];assert any((l.get('fu'),l.get('fv'),l.get('fw'))==(10,-20,5) for l in forces)
 return len(ns),len(es),len(qids),len(expected)

def source_specific():
 def get(i):return json.loads((ROOT/f'corpora/research-300/cases/MM-{i:03}/model-state-1.json').read_text())
 def n(m,id):return next(n for n in m['nodes'] if n['id']==id)
 def e(m,id):return next(e for e in m['elements'] if e['id']==id)
 def total(m,case='D'):return sum(l.get('fz',0)+l.get('wz',0)*length(m,e(m,l['element'])) if 'element' in l else l.get('fz',0) for c in m['load_cases'] if c['id']==case for l in c['loads'])
 # Frozen source totals calculated from source geometry/load values, independent of builder loops.
 expected={61:-240,62:-192,63:-120,64:-153,65:-305,66:-240,67:-200,68:-120,69:-906,70:-960,71:-248,72:-360,73:-252,74:-264,75:-230,76:-1200,77:-420,78:-148,99:-300,100:-300}
 for i,v in expected.items():assert math.isclose(total(get(i)),v,abs_tol=1e-8),(i,total(get(i)),v)
 assert n(get(61),'n2-0')['restraints']==[False,True,True,True,False,True]
 assert 'c1-3' not in {e['id'] for e in get(65)['elements']} and n(get(65),'n1-3')['z']==9.9
 assert 'n1-0' not in {n['id'] for n in get(67)['nodes']}
 assert n(get(68),'n0-0')['z']==-1.5
 assert n(get(70),'n0-2')['x']==n(get(70),'n0-3')['x']==1
 assert length(get(72),e(get(72),'Cc4'))==.5
 assert e(get(73),'c0-1')['material']=='C40' and e(get(73),'b0-1')['material']=='C30' and e(get(73),'cant')['material']=='C35'
 assert e(get(74),'c2-1')['rotation_angle']==90 and e(get(74),'c0-1').get('rotation_angle',0)==0
 assert 'b1-2' not in {e['id'] for e in get(75)['elements']}
 assert e(get(77),'c0-2')['section']=='Cbig' and e(get(77),'c0-3')['section']=='C1'
 assert {c['id'] for c in get(78)['load_combinations']}=={'D','D+W+','D+W-'}
 assert length(get(99),e(get(99),'upper'))==math.sqrt(26)
 assert n(get(100),'tipY')['y']==-1.5 and e(get(100),'armY')['section']=='B2'

if __name__=='__main__':
 ids=sys.argv[1:] or [f'MM-{i:03}' for i in range(51,101)];tot=[0,0,0,0]
 for cid in ids:
  counts=check_case(cid);tot=[a+b for a,b in zip(tot,counts)]
 if len(ids)==50:source_specific()
 print('PASS',len(ids),'cases; nodes/members/quantities/source requirements:',tot)
