"""Check L3 load arithmetic from issued rules, without importing authoring loads.

Geometry/properties come from the reference models whose public reconstruction
was checked separately. This is independent load integration, not a blind new
geometry review. No candidate, native solver or authoring load helper is called.
"""
import argparse
from copy import deepcopy
import hashlib,json,math,re
from pathlib import Path

F=('fx','fy','fz','mx','my','mz')
def read(p):return json.loads(p.read_text())
def add(table,key,values):
 old=table.setdefault(key,[0.]*len(values))
 for i,v in enumerate(values):old[i]+=v
def roof_strips(m,rules):
 ys={}
 for n in m['nodes']:
  row=ys.setdefault(round(n['y'],8),{});x=round(n['x'],8)
  if x not in row or n['z']>row[x]['z']:row[x]=n
 lines=[sorted(v.values(),key=lambda n:n['x']) for _,v in sorted(ys.items()) if len(v)>1]
 if len(lines)==1:return [(lines[0],rules['stripWidthM'])]
 y=[v[0]['y'] for v in lines];edges=[rules['planEdgesY'][0],*[(a+b)/2 for a,b in zip(y,y[1:])],rules['planEdgesY'][1]]
 return [(row,edges[i+1]-edges[i]) for i,row in enumerate(lines)]
def reconstruct(m,rules):
 nodal={c:{} for c in 'DQW'};distributed={c:{} for c in 'DQW'}
 nodes={n['id']:n for n in m['nodes']};materials={v['id']:v for v in m['materials']};sections={v['id']:v for v in m['sections']}
 for el in m['elements']:
  ends=[nodes[i] for i in el['nodes']];length=math.dist([ends[0][k] for k in 'xyz'],[ends[1][k] for k in 'xyz'])
  q=materials[el['material']]['rho']*sections[el['section']]['properties']['A']*rules['gravityMPerS2']/1000
  if el['type'] in ['brace','truss']:
   for n in ends:add(nodal['D'],n['id'],[0,0,-q*length/2,0,0,0])
  else:add(distributed['D'],el['id'],[0,0,-q])
 strips=roof_strips(m,rules)
 if 'liveRevision' in rules:
  r=rules['liveRevision'];aw=ae=0.
  for row,width in strips:
   aw+=max(0,min(row[-1]['x'],r['splitX'])-row[0]['x'])*width
   ae+=max(0,row[-1]['x']-max(row[0]['x'],r['splitX']))*width
  east=r['totalLiveKN']/(aw*r['westEastPressureRatio']+ae)
  live=[{'startX':min(z['startX'] for z in rules['zones']),'endX':r['splitX'],'pressure':east*r['westEastPressureRatio']},
        {'startX':r['splitX'],'endX':max(z['endX'] for z in rules['zones']),'pressure':east}]
 for row,width in strips:
  for a,b in zip(row,row[1:]):
   dx=b['x']-a['x'];slope=(b['z']-a['z'])/dx
   for case in 'DQW':
    zones=live if case=='Q' and 'liveRevision'in rules else [{'startX':z['startX'],'endX':z['endX'],'pressure':z[case]} for z in rules['zones']]
    for zone in zones:
     lo=max(a['x'],zone['startX']);hi=min(b['x'],zone['endX'])
     if hi<=lo:continue
     mid=(lo+hi)/2;half=(hi-lo)/2;p=zone['pressure']*width
     # Two-point Gauss quadrature exactly integrates the issued linear bearing
     # weights, using a different arithmetic path from the authoring integrals.
     for x in [mid-half/math.sqrt(3),mid+half/math.sqrt(3)]:
      vector=[-p*slope,0,p,0,0,0] if case=='W' else [0,0,-p,0,0,0]
      for n,weight in [(a,(b['x']-x)/dx),(b,(x-a['x'])/dx)]:add(nodal[case],n['id'],[v*half*weight for v in vector])
 roof={n['id']:n for row,_ in strips for n in row};highest=max(n['z'] for n in roof.values());tops=[n for n in roof.values() if abs(n['z']-highest)<1e-9]
 action=rules['horizontalAction']
 for n in tops:add(nodal['W'],n['id'],[action['fxKN']/len(tops),action['fyKN']/len(tops),0,0,0,0])
 if rules.get('addedEquipment'):
  eq=rules['addedEquipment'];ordered=sorted(roof.values(),key=lambda n:(abs(n['x']-eq['positionX']),-n['z'],abs(n['y'])))
  key=lambda n:(abs(n['x']-eq['positionX']),-n['z'],abs(n['y']))
  if len(ordered)>1 and key(ordered[0])==key(ordered[1]):raise ValueError('Equipment placement has an unresolved issued tie')
  add(nodal['D'],ordered[0]['id'],[0,0,-eq['weightKN'],0,0,0])
 return nodal,distributed
def supplied(m):
 nodal={c:{} for c in 'DQW'};distributed={c:{} for c in 'DQW'}
 for case in m['load_cases']:
  for load in case['loads']:
   if load.get('reference_frame','global')!='global':raise ValueError('Reference loads are not global')
   if load['type']=='nodal':add(nodal[case['id']],load['node'],[load.get(k,0) for k in F])
   elif load['type']=='distributed' and not any(k in load for k in ['start','end','points','variation']):add(distributed[case['id']],load['element'],[load.get(k,0) for k in ['wx','wy','wz']])
   else:raise ValueError('Unexpected reference load representation')
 return nodal,distributed
def difference(a,b):
 maximum=0.;checks=0
 for x,y in zip(a,b):
  for case in 'DQW':
   for key in set(x[case])|set(y[case]):
    va=x[case].get(key,[0.]*len(next(iter(y[case].values()),[0,0,0])))
    vb=y[case].get(key,[0.]*len(va))
    for actual,expected in zip(va,vb):
     delta=abs(actual-expected);maximum=max(maximum,delta);checks+=1
     if delta>1e-9+1e-10*abs(expected):raise ValueError(f'Public load arithmetic differs: {case}/{key}: {actual} vs {expected}')
 return maximum,checks
def audit(edition,output):
 edition,output=map(Path,(edition,output));manifest=read(edition/'manifest.json');rows=[]
 for case in manifest['cases']:
  if case['level']!='L3':continue
  initial=edition/case['turns'][0]['public'];base=read(initial/'load-zones.json');state=deepcopy(base)
  for ordinal,turn in enumerate(case['turns'],1):
   public=edition/turn['public'];task=read(public/'task.json');text=task['instruction']
   if ordinal==2:
    v=re.search(r'X=([\d.e+\-]+) m 分界，西/东面压比 ([\d.e+\-]+)，总活荷载仍为 ([\d.e+\-]+) kN',text)
    if not v:raise ValueError('Missing public Q revision')
    state['liveRevision']=dict(zip(['splitX','westEastPressureRatio','totalLiveKN'],map(float,v.groups())))
   if ordinal==3:
    v=re.search(r'X=([\d.e+\-]+) m.*增加设备恒载 ([\d.e+\-]+) kN',text)
    if not v:raise ValueError('Missing public equipment position/weight')
    state['addedEquipment']=dict(zip(['positionX','weightKN'],map(float,v.groups())))
   if ordinal==4:state.pop('liveRevision',None)
   ref=read(edition/turn['private']);scenarios=ref.get('scenarios') or [{'id':'dynamic','model':ref['model'],'loadRules':ref['loadRules']}]
   for scenario in scenarios:
    rules=deepcopy(state)
    if scenario['id']=='relocated':rules['liveRevision']=read(public/'proposed-revision.json')
    actual_rules=scenario['loadRules']
    for key,value in rules.items():
     if key in ['liveRevision','addedEquipment']:
      for field,v in value.items():
       if field!='scope' and not math.isclose(actual_rules[key].get(field),v,rel_tol=1e-12,abs_tol=1e-10):raise ValueError(f'Private/public revision value differs: {case["id"]}/{turn["id"]}/{field}')
     elif actual_rules.get(key)!=value:raise ValueError('Private/public rule differs: '+key)
    if set(actual_rules)-set(rules):raise ValueError('Unissued private rule')
    m=scenario['model'];loads=reconstruct(m,rules);delta,checks=difference(loads,supplied(m));row={'caseId':case['id'],'turnId':turn['id'],'scenario':scenario['id'],'maxLoadDifference':delta,'componentsChecked':checks}
    if ref.get('massRule'):
     mass_rule=read(initial/'mass-source.json');mass={n['id']:0. for n in m['nodes']};lookup={n['id']:n for n in m['nodes']}
     for cid,factor in [('D',1),('Q',mass_rule['fractionQ'])]:
      for nid,vector in loads[0][cid].items():mass[nid]-=factor*vector[2]/mass_rule['gravityMPerS2']
      for eid,vector in loads[1][cid].items():
       el=next(e for e in m['elements'] if e['id']==eid);a,b=[lookup[n] for n in el['nodes']];value=-factor*vector[2]*math.dist([a[k] for k in 'xyz'],[b[k] for k in 'xyz'])/(2*mass_rule['gravityMPerS2'])
       for nid in el['nodes']:mass[nid]+=value
     maximum=0.
     for n in m['nodes']:
      expected=mass[n['id']] if not n['restraints'][0] else 0.;diff=abs(n.get('mass',0)-expected);maximum=max(maximum,diff)
      if diff>1e-10+1e-10*abs(expected):raise ValueError('Public participating mass differs: '+n['id'])
     row['maxNodalMassDifference']=maximum
    rows.append(row)
 result={'allPassed':True,'manifestSha256':hashlib.sha256((edition/'manifest.json').read_bytes()).hexdigest(),'cases':len(set(r['caseId'] for r in rows)),'turns':len(set((r['caseId'],r['turnId']) for r in rows)),'loadStates':len(rows),'componentsChecked':sum(r['componentsChecked'] for r in rows),'maxLoadDifference':max(r['maxLoadDifference'] for r in rows),'scope':'Independent Gauss load integration and gravity/mass arithmetic for all L3 states. Uses geometry/properties previously checked by source-guided public reconstruction; not a new external blind geometry review. No authoring load helper is imported.','candidateCalls':0,'nativeCalls':0,'rows':rows}
 with output.open('x') as f:f.write(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 return {k:v for k,v in result.items() if k!='rows'}
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--edition',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(audit(a.edition,a.output),indent=2))
