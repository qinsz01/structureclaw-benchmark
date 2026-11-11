"""Source-directed MM076-100 review. Does not import author builders or checks.
Expected geometry/load/property maps below are manually transcribed from ORIGINAL
planning model.spec/task.scenario. Public appendix consistency is a separate gate.
No solver, blind reconstruction or acceptance claim. Run python3 this_file.py.
"""
from pathlib import Path
import json, hashlib, math, collections, datetime, sys, os
ROOT=Path(os.environ.get('REVIEW_INPUTS_SHARED_ROOT','/mnt/nas/qsz/01research/02structureclaw-bench'))
OUT=Path(__file__).resolve().parents[2]/'docs/implementation/reviews/review-inputs'
HASH={}
def read(p):
 b=p.read_bytes();HASH[str(p)]=hashlib.sha256(b).hexdigest();return b
def js(p):return json.loads(read(p))
def pt(p):return tuple(round(float(v),8) for v in p)
def edge(a,b):return tuple(sorted((pt(a),pt(b))))
def xyz(n):return pt([n[k] for k in 'xyz'])
def grid(xs,ys,zs,transform=lambda x,y,z:(x,y,z),keep=lambda x,y,z:True):
 nodes={(x,y,z):pt(transform(x,y,z)) for z in zs for y in ys for x in xs if keep(x,y,z)}
 edges={}
 for (x,y,z),p in nodes.items():
  if z==zs[0]:continue
  for tag,q in [('column',(x,y,zs[zs.index(z)-1])),('beam',(xs[xs.index(x)-1],y,z) if xs.index(x) else None),('beam',(x,ys[ys.index(y)-1],z) if ys.index(y) else None)]:
   if q in nodes:edges[edge(nodes[q],p)]=tag
 return set(nodes.values()),edges

def expected(i):
 # Source-only expected physical endpoints. Beam subdivision is explicit for076.
 if i in (76,77,78):
  xs,zs={76:([0,5,12],[0,3.6,7.2]),77:([0,6,12],[0,3.3,6.6,9.9,13.2]),78:([0,6],[0,3.3,6.6,9.9])}[i]
  n,e=grid(xs,[0],zs)
  if i==76:
   for z in zs[1:]:
    e.pop(edge((0,0,z),(5,0,z)));n.add((2.5,0,z));e[edge((0,0,z),(2.5,0,z))]='beam';e[edge((2.5,0,z),(5,0,z))]='beam'
  if i==77:e.pop(edge((6,0,6.6),(12,0,6.6)))
  if i==78:n.add((7,0,9.9));e[edge((6,0,9.9),(7,0,9.9))]='beam'
 elif i==79:n,e=grid([0,6],[0,5],[0,3.6,7.2],lambda x,y,z:(x+(1 if z==7.2 else 0),y,z))
 elif i in (80,84,88):
  n,e=grid([0,6,12],[0,5],[0,3.6,7.2])
  if i==80:e.pop(edge((6,0,7.2),(6,5,7.2)))
  if i==84:e.pop(edge((6,0,3.6),(6,0,7.2)))
  if i==88:e[edge((0,0,7.2),(12,5,7.2))]='truss'
 elif i==81:n,e=grid([0,6],[0,5,10],[0,3.3,6.6,9.9],keep=lambda x,y,z:not(z==9.9 and y==10))
 elif i in (82,91):
  n,e=grid([0,6,12],[0,5,10],[0,3.6,7.2]);e.pop(edge((6,0,7.2),(6,5,7.2)))
  if i==82:e.pop(edge((6,5,7.2),(6,10,7.2)))
 elif i==83:n,e=grid([0,6,12],[0,5],[0,3.6,7.2,10.8],keep=lambda x,y,z:not(z==10.8 and x==12))
 elif i==85:n,e=grid([0,4,11],[0,3,9],[0,3.4,7.5],lambda x,y,z:(1,1,z)if(x,y,z)==(0,0,7.5)else(x,y,z))
 elif i==86:
  n,e=grid([0,4,8,12],[0,5,10],[0,3.6,7.2])
  for z in (3.6,7.2):e.pop(edge((4,10,z),(8,10,z)))
 elif i==87:
  n,e=grid([0,6,12],[0,5,10],[0,3.6,7.2],keep=lambda x,y,z:z<7.2 or (x<=6 and y<=5)or(x>=6 and y>=5))
  # Surviving grid vertices alone could falsely create two absent connecting edges.
  for a,b in [((0,5,7.2),(0,10,7.2)),((6,0,7.2),(12,0,7.2))]:e.pop(edge(a,b),None)
 elif i==89:n,e=grid([0,4,8,12],[0,5,10],[0,3.6,7.2])
 elif i==90:n,e=grid([0,6],[0,5,10],[0,3.6,7.2])
 elif i==92:n,e=grid([0,6,12],[0,5],[0,6],lambda x,y,z:(x,y,8 if x==6 and z else z))
 elif i==93:
  n,e=grid([0,6],[0,5],[0,3.6,7.2])
  for y,lo,hi in [(0,0,3.6),(5,3.6,7.2)]:
   e[edge((0,y,lo),(6,y,hi))]='truss';e[edge((6,y,lo),(0,y,hi))]='truss'
 elif i==94:n,e=grid([0,4,11],[0,6],[0,3.5,7.5],lambda x,y,z:(x,y,-1 if y==6 and z==0 else z))
 else:
  ps={95:[(0,0,0),(0,0,2),(0,0,4.5)],96:[(0,0,0),(0,0,2.1),(0,0,4.2)],97:[(0,0,0),(0,0,2.5),(0,0,5)],98:[(0,0,0),(0,0,3),(0,0,6),(0,2,3)],99:[(0,0,0),(0,0,3),(1,0,8)],100:[(0,0,0),(0,0,5),(2,0,5),(0,-1.5,5)]}[i]
  n=set(ps);e={edge(ps[0],ps[1]):'column',edge(ps[1],ps[2]):'column' if i!=100 else 'beam'}
  if len(ps)==4:e[edge(ps[1],ps[3])]='beam'
 return n,e

def section_for(i,ab,kind):
 a,b=ab
 if kind=='truss':return 'A1'
 if kind=='column':
  if i==77:return 'Cbig' if max(a[2],b[2])<=6.6 else 'C1'
  if i==89:
   outerx=a[0]in(0,12);outery=a[1]in(0,10)
   return 'C1' if outerx and outery else 'C2' if outerx or outery else 'C3'
  if i==99:return 'C1'if max(a[2],b[2])==3 else'C2'
  return 'C1'
 if i==77:return 'Btop' if a[2]==13.2 else 'B1'
 if i==78:return 'BC' if min(a[0],b[0])==6 else'B1'
 if i in (79,80,81,82,92):return 'B2' if a[0]==b[0] else'B1'
 if i==84 and a[2]==7.2 and a[1]==b[1]==0:return 'BT'
 if i==89:return 'B1'if a[0]==b[0] else'B3'if a[1]==5 else'B2'
 if i==100:return 'B2'if a[0]==b[0] else'B1'
 return 'B1'

def expected_lines(i,edges):
 d={};l={}
 for ab,kind in edges.items():
  if kind!='beam':continue
  a,b=ab;z=a[2]
  if i==76:w=(40 if max(a[0],b[0])<=5 else 60) if z==3.6 else (60 if max(a[0],b[0])<=5 else 40)
  elif i==77:w=10
  elif i==78:w=4 if min(a[0],b[0])==6 else {3.3:10,6.6:8,9.9:6}[z]
  elif i in (79,80,81,82,83,84):
   if a[0]==b[0]:continue
   width=2.5
   if i in (81,82) and a[1]==5 and not(i==81 and z==9.9):width=5
   pressure={79:10,80:8,81:10,82:(10 if z==3.6 else 8),83:(6 if z==10.8 else 12),84:(12 if z==3.6 else 10)}[i];w=pressure*width
  elif i==86:w=8+(4 if z==7.2 and max(a[0],b[0])<=4 else 0)
  elif i==87:w=10 if z==3.6 else 8 if max(a[0],b[0])<=6 and max(a[1],b[1])<=5 else 6
  elif i==92:w=6
  elif i>=95:continue
  else:w=8
  d[ab]=(0,0,-w)
  if i==91 and z==7.2 and min(a[0],b[0])>=6 and min(a[1],b[1])>=5:l[ab]=(0,0,-6)
 return {'D':d,**({'L':l}if i==91 else{}),**({'W+':{},'W-':{}}if i==78 else{}),**({'WX':{},'WY':{}}if i==88 else{})}

def expected_points(i):
 # xyz location and Fx,Fy,Fz; no invented equivalent nodal replacement.
 p={78:{'W+':{(7,0,9.9):(20,0,0)},'W-':{(7,0,9.9):(-20,0,0)}},80:{'D':{(12,5,7.2):(0,20,0)}},82:{'D':{(12,10,7.2):(15,10,0)}},85:{'D':{(1,1,7.5):(10,0,0)}},88:{'WX':{(12,5,7.2):(20,0,0)},'WY':{(0,5,7.2):(0,15,0)}},89:{'D':{(12,10,7.2):(20,10,0)}},90:{'D':{(6,10,7.2):(20,15,0)}},93:{'D':{(6,5,7.2):(20,15,0)}},94:{'D':{(11,0,7.5):(10,-5,-20)}},95:{'D':{(0,0,4.5):(0,0,-500)}},96:{'D':{(0,0,4.2):(30,0,-600)}},97:{'D':{(0,0,5):(0,0,-700),(0,0,2.5):(10,0,0)}},98:{'D':{(0,0,6):(20,15,-400),(0,2,3):(0,0,-80)}},99:{'D':{(1,0,8):(20,0,-300)}},100:{'D':{(2,0,5):(0,0,-200),(0,-1.5,5):(10,0,-100)}}}
 return p.get(i,{})

def supports(i,p):
 planar=i in (76,77,78,95,96,97,99)
 r=[False,planar,False,planar,False,planar]
 base=p[2]<=0
 if base:r=[True]*6
 if i==76 and p==(5,0,0):r[4]=False
 if i==89 and p in [(4,5,0),(8,5,0)]:r=[True]*3+[False]*3
 if i==90 and p==(0,0,0):r=[True]*3+[False]*3
 if i==96 and p==(0,0,2.1):r[0]=True
 if i==97:
  if p==(0,0,0):r[4]=False
  if p==(0,0,5):r[0]=True
 return r

# Source-required nodal observations; broad original requests may be concretized
# by additional publicly requested endpoints/reaction components.
NODE_OUTPUTS={
 76:{(2.5,0,3.6):['uz'],(2.5,0,7.2):['uz'],(5,0,0):['Fx','Fz','My']},
 77:{(12,0,13.2):['ux']},78:{(7,0,9.9):['ux','uz']},
 79:{(7,5,7.2):['ux','uz']},80:{(12,5,7.2):['uy'],(6,0,7.2):['uy'],(6,5,7.2):['uy']},
 81:{(6,5,9.9):['uz'],(0,10,6.6):['uz'],(6,10,6.6):['uz']},
 82:{(12,10,7.2):['ux','uy'],(6,5,7.2):['uy']},83:{(6,5,10.8):['uz']},84:{(6,0,7.2):['uz']},
 85:{(1,1,7.5):['ux','uz']},86:{(4,10,7.2):['uz'],(8,10,7.2):['uz'],(0,0,0):['Fz']},
 87:{(0,0,7.2):['uz'],(12,10,7.2):['uz'],(6,5,7.2):['ux']},88:{(12,5,7.2):['ux','uy']},
 89:{(12,10,7.2):['ux','uy']},90:{(6,10,7.2):['ux','uy']},91:{(12,10,7.2):['uz'],(6,5,7.2):['uz']},
 92:{(6,0,8):['uz'],(6,5,8):['uz'],(0,0,0):['Mx','My']},93:{(6,5,7.2):['ux','uy']},
 94:{(11,0,7.5):['ux','uy','uz'],(11,6,-1):['Fx','Fy','Fz','Mx','My','Mz']},
 95:{(0,0,4.5):['uz'],(0,0,2):['uz']},96:{(0,0,4.2):['ux'],(0,0,2.1):['Fx']},
 97:{(0,0,2.5):['ux'],(0,0,5):['uz','Fx'],(0,0,0):['Fx']},
 98:{(0,0,6):['ux','uy'],(0,2,3):['uz'],(0,0,0):['Mx','My','Mz']},
 99:{(1,0,8):['ux','uz']},100:{(2,0,5):['uz'],(0,-1.5,5):['uz'],(0,0,0):['Mx','My','Mz']}}
MEMBER_OUTPUTS={
 77:[((6,0,3.3),(6,0,6.6),['M2'])],78:[((6,0,0),(6,0,3.3),['M2'])],
 79:[((6,0,0),(6,0,3.6),['M2','M3'])],83:[((12,0,0),(12,0,3.6),['N']),((12,5,0),(12,5,3.6),['N'])],
 84:[((0,0,7.2),(6,0,7.2),['M2']),((6,0,7.2),(12,0,7.2),['M2'])],
 85:[((0,0,0),(0,0,3.4),['M2','M3'])],88:[((0,0,7.2),(12,5,7.2),['N'])],
 89:[((4,5,0),(4,5,3.6),['N']),((8,5,0),(8,5,3.6),['N'])],90:[((0,0,3.6),(0,0,7.2),['M2','M3'])],
 93:[((0,0,0),(6,0,3.6),['N']),((6,0,0),(0,0,3.6),['N'])],95:[((0,0,0),(0,0,2),['N'])],
 99:[((0,0,0),(0,0,3),['M2']),((0,0,3),(1,0,8),['M2'])]}

def check_case(i,t,morig):
 cid=f'MM-{i:03}';folder=ROOT/'.worktrees/mm-b/corpora/research-300/cases'/cid
 c=js(folder/'contract.json');m=js(folder/'model-state-1.json');p=js(folder/'properties.json');ass=js(folder/'assignments.json');req=js(folder/'reference-requests.json')['states'][0]
 for f in sorted(set(c['attachments']+['prompt.txt'])):read(folder/f)
 issues=[];checks=[]
 def ck(name,ok,detail=None):
  checks.append({'check':name,'pass':bool(ok),**({'detail':detail}if not ok else{})})
  if not ok:issues.append(name)
 nodes={v['id']:v for v in m['nodes']};es={v['id']:v for v in m['elements']};obsedges={edge(xyz(nodes[e['nodes'][0]]),xyz(nodes[e['nodes'][1]])):e for e in es.values()};en,ee=expected(i)
 ck('source exact node coordinates (including observation/offset joints)',set(map(xyz,nodes.values()))==en,{'expected':sorted(en),'actual':sorted(map(xyz,nodes.values()))})
 ck('source exact endpoint connectivity, no duplicate members',set(obsedges)==set(ee)and len(obsedges)==len(es),{'missing':list(set(ee)-set(obsedges)),'extra':list(set(obsedges)-set(ee))})
 ck('source element type and section assignment',all(ab in obsedges and obsedges[ab]['type']==kind and obsedges[ab]['section']==section_for(i,ab,kind)for ab,kind in ee.items()))
 ck('source support DOFs (planar inactive DOFs distinguished)',all(n['restraints']==supports(i,xyz(n))for n in nodes.values()))
 lines=expected_lines(i,ee);points=expected_points(i);lc={q['id']:q for q in m['load_cases']}
 ck('source exact basic load case set',set(lc)==set(lines))
 resultants={}
 for sel,loads in lc.items():
  actual_line=collections.defaultdict(lambda:[0,0,0]);actual_point=collections.defaultdict(lambda:[0,0,0]);forces=[0,0,0];moments=[0,0,0]
  for l in loads['loads']:
   ck(f'{sel}/{l["id"]}: global axes and no hidden moment',l.get('reference_frame')=='global' and all(l.get(k,0)==0 for k in ('mx','my','mz')))
   if l['type']=='distributed':
    e=es[l['element']];a,b=[xyz(nodes[n])for n in e['nodes']];ab=edge(a,b);length=math.dist(a,b);f=[l.get(k,0)for k in ('wx','wy','wz')];center=[(x+y)/2 for x,y in zip(a,b)]
    ck(f'{sel}/{l["id"]}: actual full member length',l.get('start',0)==0 and math.isclose(l.get('end',length),length,abs_tol=1e-8))
    for j,v in enumerate(f):actual_line[ab][j]+=v
    f=[v*length for v in f]
   elif l['type']=='nodal':
    center=xyz(nodes[l['node']]);f=[l.get(k,0)for k in ('fx','fy','fz')]
    for j,v in enumerate(f):actual_point[center][j]+=v
   else:ck('unreviewed load type',False,l);continue
   for j in range(3):forces[j]+=f[j]
   cross=[center[1]*f[2]-center[2]*f[1],center[2]*f[0]-center[0]*f[2],center[0]*f[1]-center[1]*f[0]]
   for j in range(3):moments[j]+=cross[j]
  ck(f'{sel}: source per-member distributed vectors',dict(actual_line)=={k:list(v)for k,v in lines.get(sel,{}).items()})
  ck(f'{sel}: source nodal locations/vectors',dict(actual_point)=={k:list(v)for k,v in points.get(sel,{}).items()})
  resultants[sel]={'force_kN':forces,'moment_about_origin_kNm':moments}
 expected_comb={78:{'D':{'D':1},'D+W+':{'D':1,'W+':1},'D+W-':{'D':1,'W-':1}},88:{'D':{'D':1},'D+WX':{'D':1,'WX':1},'D+WY':{'D':1,'WY':1}},91:{'D':{'D':1},'D+L':{'D':1,'L':1}}}.get(i,{})
 ck('source combination factors', {v['id']:v['factors']for v in m['load_combinations']}==expected_comb)
 expected_material='concrete' if i in (76,77,78,83,84,95,96) else 'steel'
 ck('source material family and C30 identity where specified',all(v['type']==expected_material and (v['name']=='C30' if i in(76,77,78,83,84,96) else True)for v in m['materials']))
 ck('public material and section numeric records equal hidden model',p['materials']==m['materials']and p['sections']==m['sections'])
 ck('public assignments preserve material/section/roll without endpoint table',all('nodes'not in a and a['material']==es[a['id']]['material']and a['section']==es[a['id']]['section']and a.get('rotation_angle',0)==es[a['id']].get('rotation_angle',0)for a in ass))
 ck('only source-requested roll on upper front-left/rear-right090 columns',all(e.get('rotation_angle',0)==(90 if i==90 and ab in [edge((0,0,3.6),(0,0,7.2)),edge((6,10,3.6),(6,10,7.2))]else 0)for ab,e in obsedges.items()))
 ck('no default weight/diaphragm/offset/nonlinear additions',all(m['analysis_control'].get(k)is False for k in ('self_weight','rigid_floor','p_delta','rigid_offsets')))
 # Exact source sizes exist where fixed in original row; other complete values are authored appendices.
 size_expect={76:{'C1':(500,500),'B1':(300,600)},77:{'Cbig':(600,600),'C1':(500,500),'B1':(300,600),'Btop':(250,500)},78:{'C1':(500,500),'B1':(300,600),'BC':(250,500)},83:{'C1':(500,500),'B1':(300,600)},84:{'C1':(500,500),'B1':(300,600),'BT':(400,800)},95:{'C1':(400,400)},96:{'C1':(450,450)}}.get(i,{})
 ss={s['id']:s for s in m['sections']}
 ck('source fixed section dimensions',all((ss[k]['shape']['B'],ss[k]['shape']['H'])==v for k,v in size_expect.items()))
 for s in m['sections']:
  sh=s['shape'];pr=s['properties']
  if sh['kind']=='rectangular':
   b,h=sh['B']/1000,sh['H']/1000
   ck(f'{s["id"]}: independently integrated rectangle A/Iy/Iz',all(math.isclose(pr[k],v,rel_tol=1e-10)for k,v in {'A':b*h,'Iy':b*h**3/12,'Iz':h*b**3/12}.items()))
 if i==95:
  mats={v['id']:v for v in m['materials']}
  ck('source C40 lower/C30 upper material interface',all(mats[e['material']]['name']==('C40'if max(p[2]for p in ab)==2 else'C30')for ab,e in obsedges.items()))
 # Public transformed load map is checked numerically, independently of author conversion.
 if 'loads.json'in c['attachments']:
  pub=js(folder/'loads.json')
  for pcl in pub['load_cases']:
   hidden={v['id']:v for v in lc[pcl['id']]['loads']}
   for l in pcl['loads']:
    target=hidden[l['id']]
    if i==94:
     prefix='f'if l['type']=='nodal'else'w';f=[l.get(prefix+'u',0),-l.get(prefix+'w',0),l.get(prefix+'v',0)]
     ck(f'public source uvw transform {l["id"]}',l['reference_frame']=='source-uvw'and f==[target.get(prefix+a,0)for a in 'xyz'])
    else:ck(f'public load record {l["id"]}',l==target)
  ck('public load case/combination set',len(pub['load_cases'])==len(lc)and pub['load_combinations']==m['load_combinations'])
 if i==95:ck('PNG-only source load has no public load table','loads.json'not in c['attachments'])
 for q in req['quantities']:
  loc=q['location'];sel=q['selection'];valid=sel['id']in(lc if sel['kind']=='case'else expected_comb)
  if loc['kind']=='node':valid &= loc['id']in nodes and any(loc['id']in e['nodes']for e in es.values())
  else:
   e=es[loc['id']];length=math.dist(*[xyz(nodes[n])for n in e['nodes']]);valid &= 0<=loc['positionM']<=length+1e-8
  ck(f'observation connected/in-bounds {q["id"]}',valid)
 selections={78:['D','D+W+','D+W-'],88:['D+WX','D+WY'],91:['D','D+L']}.get(i,['D'])
 for sel in selections:
  qnodes={(xyz(nodes[q['location']['id']]),q['component'])for q in req['quantities']if q['selection']['id']==sel and q['location']['kind']=='node'}
  ck(f'{sel}: source requested node positions/components',all((pt(p),comp)in qnodes for p,comps in NODE_OUTPUTS[i].items()for comp in comps))
  qmembers={(edge(*[xyz(nodes[n])for n in es[q['location']['id']]['nodes']]),q['component'])for q in req['quantities']if q['selection']['id']==sel and q['location']['kind']=='member'}
  ck(f'{sel}: source requested member positions/components',all((edge(a,b),comp)in qmembers for a,b,comps in MEMBER_OUTPUTS.get(i,[])for comp in comps))
 if i==80:
  der=req['derived'][0];qmap={q['id']:q for q in req['quantities']}
  ck('source relative Uy across missing beam preserved as signed difference',der['operation']=='difference' and [xyz(nodes[qmap[k]['location']['id']])for k in der['operands']]==[(6,5,7.2),(6,0,7.2)])
 if 'boundaryConditions'in p:
  order=['ux','uy','uz','rx','ry','rz'];bound={q['node']:q['restrainedDOFs']for q in p['boundaryConditions']}
  ck('public support DOFs equal source-tested model',set(bound)==set(nodes)and all(bound[k]==[d for d,b in zip(order,n['restraints'])if b]for k,n in nodes.items()))
 if i==98:
  # Three rectangles independently integrated about the computed centroid.
  shapes=[(.2,.02,.01),(.012,.46,.25),(.3,.02,.49)];area=sum(b*h for b,h,c in shapes);centroid=sum(b*h*c for b,h,c in shapes)/area
  iy=sum(b*h**3/12+b*h*(c-centroid)**2 for b,h,c in shapes);iz=sum(h*b**3/12 for b,h,c in shapes);sec=ss['C1']
  ck('asymmetric section independent area/centroid/principal inertias',all(math.isclose(v,w,rel_tol=1e-10)for v,w in [(area,sec['properties']['A']),(centroid*1000,sec['shape']['centroidFromNegative3Edge']),(iy,sec['properties']['Iy']),(iz,sec['properties']['Iz'])]))
 return {'caseId':cid,'approved':False,'sourceTask':{k:t[k]for k in ('inputForm','scenario','expectedOutput')},'sourceModel':morig['spec'],'checks':checks,'issues':issues,'loadResultants':resultants,'requestCount':len(req['quantities']),'modelHash':HASH[str(folder/'model-state-1.json')]}

def main():
 tasks={x['id']:x for x in js(ROOT/'planning/sources/all-tasks-engines-v2.json')};models={x['taskId']:x for x in js(ROOT/'planning/sources/all-models-engines-v2.json')}
 cases=[]
 for i in range(76,101):
  case=check_case(i,tasks[f'MM-{i:03}'],models[f'MM-{i:03}']);cases.append(case);print(case['caseId'],len(case['checks']),'checks',case['issues'])
 changed=[p for p,h in HASH.items()if hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h]
 out={'schemaVersion':1,'createdUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'reviewKind':'source-guided, not blind reconstruction','approved':False,'cases':cases,'readHashes':HASH,'changedDuringRun':changed,'limitations':['No solver/native run.','Generic request bounds are supplemented by manual original-output mapping in report.','PNG inspections are stratified and individually recorded, not all images.']}
 (OUT/'mm076_100-results.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
 return 1 if any(c['issues']for c in cases)or changed else 0
if __name__=='__main__':sys.exit(main())
