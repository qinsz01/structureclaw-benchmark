"""MM-B deterministic authoring utilities; only MM-051..100, no solver/truth code."""
from pathlib import Path
from copy import deepcopy
from commercial.conventions import revise_authored_case
import importlib.util, json, math, html, csv, io, hashlib
from fractions import Fraction
from PIL import Image, ImageDraw, ImageFont
ROOT=Path(__file__).resolve().parents[2]
_spec=importlib.util.spec_from_file_location('mm_b_primitives',ROOT/'scripts/representative-models.py')
p=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(p)
PLAN=json.loads((ROOT/'planning/capability-coverage-300.json').read_text())
ROWS={x['id']:x for x in PLAN['cases']}
SOURCE_DIR=ROOT/'planning/sources'
if not SOURCE_DIR.exists(): SOURCE_DIR=Path('/mnt/nas/qsz/01research/02structureclaw-bench/planning/sources')
SOURCE_TASKS={x['id']:x for x in json.loads((SOURCE_DIR/'all-tasks-engines-v2.json').read_text())}
SOURCE_MODELS={x['taskId']:x for x in json.loads((SOURCE_DIR/'all-models-engines-v2.json').read_text())}
TOL={'absolute':1e-8,'relative':1e-6}
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
CJK='/home/codex_xjk/.local/share/fonts/NotoSansCJKsc-Regular.otf'

def dump(path,data): path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def dim(v):
 f=Fraction(v).limit_denominator(1000)
 return str(f) if abs(float(f)-v)<1e-10 and len(f'{v:.10g}')>9 else f'{v:.10g}'
def length(m,e):
 n={x['id']:x for x in m['nodes']}; a,b=[n[x] for x in e['nodes']]
 return math.sqrt(sum((a[k]-b[k])**2 for k in ('x','y','z')))

def midpoint(m,eid,nid):
 """Split physical beam with a genuinely connected observation node and preserve loads."""
 e=next(x for x in m['elements'] if x['id']==eid); ns={x['id']:x for x in m['nodes']};a,b=[ns[x] for x in e['nodes']]
 p.node(m,nid,(a['x']+b['x'])/2,(a['z']+b['z'])/2,(a['y']+b['y'])/2)
 old_end=e['nodes'][1]; e['nodes'][1]=nid
 e2=deepcopy(e);e2['id']=eid+'b';e2['nodes']=[nid,old_end];m['elements'].append(e2)
 if m['coordinate_system']['dimension']=='3d': m['metadata']['elementReferenceVectors'][e2['id']]=m['metadata']['elementReferenceVectors'][eid]
 for c in m['load_cases']:
  for load in list(c['loads']):
   if load.get('element')==eid:
    assert load['type']=='distributed' and not any(k in load for k in ('start','end')), 'split before nonuniform loads'
    other=deepcopy(load);other['id']+='b';other['element']=e2['id'];c['loads'].append(other)
 return nid

def rq(nid,component,description,selection=None):
 return {'id':nid+'-'+component,'location':{'kind':'node','id':nid},'component':component,'unit':'m' if component.startswith('u') else 'kN*m' if component.startswith('M') else 'kN','description':description,**({'selection':selection} if selection else {})}
def mq(m,eid,component,description,end=False,selection=None):
 e=next(x for x in m['elements'] if x['id']==eid)
 return {'id':eid+'-'+('j' if end else 'i')+'-'+component,'location':{'kind':'member','id':eid,'positionM':length(m,e) if end else 0,'side':'left' if end else 'right'},'component':component,'unit':'kN*m' if component.startswith(('M','T')) else 'kN','description':description,**({'selection':selection} if selection else {})}

class Canvas:
 def __init__(self,w,h):
  self.w=w;self.h=h;self.svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">','<rect width="100%" height="100%" fill="white"/>'];self.im=Image.new('RGB',(w,h),'white');self.d=ImageDraw.Draw(self.im)
 def line(self,a,b,color='#24364b',width=3):
  self.svg.append(f'<line x1="{a[0]:.3f}" y1="{a[1]:.3f}" x2="{b[0]:.3f}" y2="{b[1]:.3f}" stroke="{color}" stroke-width="{width}"/>');self.d.line((a,b),fill=color,width=width)
 def text(self,pos,s,size=18,color='#102030'):
  s=str(s);self.svg.append(f'<text x="{pos[0]:.3f}" y="{pos[1]+size:.3f}" font-family="DejaVu Sans, Noto Sans CJK SC, sans-serif" font-size="{size}" fill="{color}">{html.escape(s)}</text>')
  font=ImageFont.truetype(CJK if any(ord(c)>127 for c in s) and Path(CJK).exists() else FONT,size);self.d.text(pos,s,font=font,fill=color)
 def circle(self,pos,r=4,color='#004488'):
  x,y=pos;self.svg.append(f'<circle cx="{x:.3f}" cy="{y:.3f}" r="{r}" fill="{color}"/>');self.d.ellipse((x-r,y-r,x+r,y+r),fill=color)
 def save(self,path):
  Path(str(path)+'.svg').write_text('\n'.join(self.svg+['</svg>'])+'\n');self.im.save(Path(str(path)+'.png'),optimize=False)

def views(m):
 """Separate plans and section lines prevent coincident projections hiding members."""
 ns=m['nodes'];els=m['elements'];nd={n['id']:n for n in ns}
 if m['coordinate_system']['dimension']=='2d':return [('elevation-XZ','x','z',ns,els)]
 out=[]
 for j,z in enumerate(sorted({round(n['z'],8) for n in ns})):
  ids={n['id'] for n in ns if abs(n['z']-z)<1e-7}
  if len(ids)>1:
   out.append((f'plan-{j}-Z{z:g}','x','y',[n for n in ns if n['id'] in ids],[e for e in els if all(v in ids for v in e['nodes'])]))
 # Each column line's Y station gives a readable XZ projection; include inclined members from that station.
 ys=sorted({round(n['y'],8) for n in ns})
 for j,y in enumerate(ys):
  es=[e for e in els if any(abs(nd[v]['y']-y)<1e-7 for v in e['nodes']) and (e['type']=='column' or all(abs(nd[v]['y']-y)<1e-7 for v in e['nodes']))]
  ids={v for e in es for v in e['nodes']}
  if es:out.append((f'elevation-{j}-Y{y:g}','x','z',[n for n in ns if n['id'] in ids],es))
 # Separate X stations in the orthogonal YZ direction too. A whole-frame
 # projection collapses different X lines into identical node/member labels.
 # Incident inclined columns stay visible even when their top X shifts.
 for j,x in enumerate(sorted({round(n['x'],8) for n in ns})):
  es=[e for e in els if any(abs(nd[v]['x']-x)<1e-7 for v in e['nodes']) and (e['type']=='column' or all(abs(nd[v]['x']-x)<1e-7 for v in e['nodes']))]
  ids={v for e in es for v in e['nodes']}
  if es:out.append((f'elevation-YZ-{j}-X{x:g}','y','z',[n for n in ns if n['id'] in ids],es))
 return out

def draw_view(path,m,view,caseid,stage='complete'):
 name,ax,ay,ns,es=view; nd={n['id']:n for n in ns};xy={n['id']:(n[ax],n[ay]) for n in ns}
 axes=m.get('_renderAxisLabels',{'x':'X','y':'Y','z':'Z'})
 hidden=caseid=='MM-072' and stage=='incomplete'
 if hidden:
  # Schematic offset 0.9 is NOT the hidden physical 0.5; no scale inference is possible.
  xy={n['id']:(n[ax],n[ay]+(.4 if n['z']>0 and (n['x']>5 or (n['x']==5 and any(abs(n['z']-v)<1e-7 for v in (3.8,7.8,10.9)))) else 0)) for n in ns}
 xs=[v[0] for v in xy.values()];ys=[v[1] for v in xy.values()];xmin,xmax=min(xs),max(xs);ymin,ymax=min(ys),max(ys)
 loads=[(lc['id'],load) for lc in m['load_cases'] for load in lc['loads']]
 w,h=1800,1330+26*math.ceil(len(loads)/2);c=Canvas(w,h);c.text((35,20),f'{caseid} | {name} | dimensions in m',26)
 c.text((35,60),'Orthographic input. Member intersections connect only at labelled nodes. All shown joints rigid except truss ends.',19)
 if hidden:c.text((35,92),'SCHEMATIC / NOT TO SCALE: right-bay level offset = ?; do not measure pixels to infer it.',20,'#b22222')
 if m['coordinate_system']['dimension']=='3d':c.text((35,92),'Axis elevations include incident inclined columns; plan views locate their other ends.',19)
 left,top=190,180;pw,ph=1400,850
 def pos(n):
  x,y=xy[n];return (left+(x-xmin)/max(xmax-xmin,1)*pw,top+ph-(y-ymin)/max(ymax-ymin,1)*ph)
 # Coordinate datum ticks are drawing dimensions, never a coordinate table.
 for x in sorted(set(xs)):
  px=left+(x-xmin)/max(xmax-xmin,1)*pw;c.line((px,top-25),(px,top+ph+30),'#e2e7ed',1);c.text((px-18,top+ph+45),dim(x),18)
 for y in sorted(set(ys)):
  if hidden and not any(abs(y-v)<1e-7 for v in (0,3.3,7.3,10.4)):continue
  py=top+ph-(y-ymin)/max(ymax-ymin,1)*ph;c.line((left-30,py),(left+pw+25,py),'#e2e7ed',1);c.text((70,py-12),dim(y),18)
 c.text((left+pw+45,top+ph+40),axes[ax]+' [m]',20);c.text((45,top-50),axes[ay]+' [m]',20)
 for j,e in enumerate(es):
  a,b=[pos(n) for n in e['nodes']]
  if math.dist(a,b)<1:continue
  c.line(a,b,'#247a58' if e['type']=='truss' else '#24364b',4)
  # A visible arrow defines first-to-second end orientation without a public topology table.
  dx,dy=b[0]-a[0],b[1]-a[1];ll=math.hypot(dx,dy);ux,uy=dx/ll,dy/ll
  tip=(a[0]+.63*dx,a[1]+.63*dy)
  for side in (-1,1):c.line(tip,(tip[0]-12*ux+side*5*uy,tip[1]-12*uy-side*5*ux),'#24364b',2)
  # Crossed diagonal members have the same midpoint. Place their IDs away
  # from the crossing, on their own first-to-second member direction.
  fraction=.38 if abs(dx)>10 and abs(dy)>10 else .5
  mx,my=a[0]+fraction*dx,a[1]+fraction*dy
  elabel=e['id']+(f" roll={e['rotation_angle']:g}deg" if e.get('rotation_angle') else '')
  c.text((mx-80 if abs(a[0]-b[0])<10 else mx+7,my-24 if abs(a[1]-b[1])<10 else my-10),elabel,16,'#186b50' if e['type']=='truss' else '#364d6b')
  for ci,load in loads:
   if load.get('element')==e['id']:
    for frac in (.25,.5,.75):
     target=(a[0]+frac*dx,a[1]+frac*dy)
     va=load.get('w'+ax,0);vb=load.get('w'+ay,0)
     if va or vb:
      norm=math.hypot(va,vb);vx,vy=va/norm,-vb/norm;start=(target[0]-30*vx,target[1]-30*vy)
      c.line(start,target,'#c75a20',2)
      for side in (-1,1):c.line(target,(target[0]-8*vx+side*3*vy,target[1]-8*vy-side*3*vx),'#c75a20',2)
 for n in ns:
  pt=pos(n['id']);c.circle(pt);c.text((pt[0]+8,pt[1]-23),n['id'],17)
  r=n['restraints'];active=[0,2,4] if m['coordinate_system']['dimension']=='2d' else range(6)
  if any(r[k] for k in active):
   if caseid=='MM-058' and stage=='incomplete':
    c.text((pt[0]-30,pt[1]+15),'[cropped]',16,'#a14422');continue
   dofs=[axes['x'],axes['y'],axes['z'],'R'+axes['x'],'R'+axes['y'],'R'+axes['z']];label='FIXED' if all(r[k] for k in active) else 'LOCK '+','.join(dofs[k] for k in active if r[k])
   c.line((pt[0]-18,pt[1]+7),(pt[0]+18,pt[1]+7),'#b04040',4);c.text((pt[0]-25,pt[1]+17),label,15,'#a03030')
 c.text((35,1160),'Blue dots = physical joints / connected observation nodes; green members = axial-only braces.',19)
 c.text((35,1190),'Thin member arrows define local first-to-second direction. Orange arrows indicate load direction in this projection.',18)
 c.text((35,1235),'LOAD KEY: rows add within each case; kN, kN*m, kN/m of actual length; vector components use named axes.',18)
 for i,(case,load) in enumerate(loads):
  vals='; '.join(f"{(k[0]+axes[k[-1]].lower()) if len(k)==2 and k[-1] in axes else k}={v:g}" for k,v in load.items() if k in ('fx','fy','fz','mx','my','mz','wx','wy','wz','fu','fv','fw','wu','wv','ww','position','start','end'))
  label=f"{case} | {load.get('node',load.get('element'))} | {vals}"
  c.text((35+(i%2)*880,1270+(i//2)*26),label,17,'#9b4418')
  if 'node' in load and load['node'] in nd:
   target=pos(load['node']);va=load.get('f'+ax,0);vb=load.get('f'+ay,0)
   if va or vb:
    norm=math.hypot(va,vb);vx,vy=va/norm,-vb/norm;start=(target[0]-50*vx,target[1]-50*vy)
    c.line(start,target,'#c75a20',3)
    for side in (-1,1):c.line(target,(target[0]-12*vx+side*5*vy,target[1]-12*vy-side*5*vx),'#c75a20',3)
 c.save(path)

def dxf(path,m,architectural=False):
 """ASCII AC1009 entities: architectural orthographic plans vs structural 3D wire geometry."""
 out=['0','SECTION','2','HEADER','9','$ACADVER','1','AC1009','0','ENDSEC','0','SECTION','2','ENTITIES']
 def line(a,b,layer):
  out.extend(['0','LINE','8',layer,'10',str(a[0]),'20',str(a[1]),'30',str(a[2]),'11',str(b[0]),'21',str(b[1]),'31',str(b[2])])
 def txt(a,s,layer='ANNOTATION',height=.16):out.extend(['0','TEXT','8',layer,'10',str(a[0]),'20',str(a[1]),'30',str(a[2]),'40',str(height),'1',s])
 nd={n['id']:n for n in m['nodes']}
 if architectural:
  # Actual dimensioned floor/elevation drawing, with wall faces / column footprints,
  # separate views in CAD paper plane. No hidden structural node/element JSON.
  for j,(name,ax,ay,ns,es) in enumerate(views(m)):
   off=40*j;txt((off,-4,0),name+' | units m | S-* structural; A-* nonstructural',height=.3)
   for e in es:
    a,b=[nd[k] for k in e['nodes']];u=(off+a[ax],a[ay],0);v=(off+b[ax],b[ay],0);dx,dy=v[0]-u[0],v[1]-u[1];L=math.hypot(dx,dy)
    if L<1e-8:continue
    line(u,v,'S-'+e['type'].upper())
    nx,ny=-dy/L*.12,dx/L*.12
    for sign in [-1,1]:line((u[0]+sign*nx,u[1]+sign*ny,0),(v[0]+sign*nx,v[1]+sign*ny,0),'A-WALL')
    txt(((u[0]+v[0])/2,(u[1]+v[1])/2+.2,0),e['id'],'S-MEMBER-TAG')
   # Actual nonstructural equipment outlines, spatially separated from structural centre lines.
   if ns:
    ex=off+min(n[ax] for n in ns)+.8;ey=min(n[ay] for n in ns)+.6
    for a,b in [((0,0),(1,0)),((1,0),(1,.6)),((1,.6),(0,.6)),((0,.6),(0,0))]:line((ex+a[0],ey+a[1],0),(ex+b[0],ey+b[1],0),'A-EQUIPMENT')
    txt((ex,ey+.7,0),'EQUIPMENT - NO STRUCTURAL CONNECTION','A-EQUIPMENT-TAG',.13)
   for n in ns:
    x,y=off+n[ax],n[ay];s=.22
    for a,b in [((-s,-s),(s,-s)),((s,-s),(s,s)),((s,s),(-s,s)),((-s,s),(-s,-s))]:line((x+a[0],y+a[1],0),(x+b[0],y+b[1],0),'A-COLUMN')
    txt((x+.25,y+.25,0),n['id'],'S-NODE-TAG')
    if any(n['restraints'][k] for k in ([0,2,4] if m['coordinate_system']['dimension']=='2d' else range(6))):txt((x+.25,y-.4,0),'LOCK:'+','.join(['X','Y','Z','RX','RY','RZ'][k] for k,v in enumerate(n['restraints']) if v),'A-SUPPORT')
   for v in sorted({n[ax] for n in ns}):txt((off+v,-2,0),ax.upper()+'='+f'{v:g}','A-DIM')
   for v in sorted({n[ay] for n in ns}):txt((off-3,v,0),ay.upper()+'='+f'{v:g}','A-DIM')
 else:
  def pt(n):return (n['x'],n['z'],0) if m['coordinate_system']['dimension']=='2d' else (n['x'],n['y'],n['z'])
  for e in m['elements']:
   a,b=[pt(nd[k]) for k in e['nodes']];line(a,b,'S-'+e['type'].upper());txt(tuple((a[i]+b[i])/2 for i in range(3)),e['id']+' '+e['section'])
  for n in m['nodes']:
   a=pt(n);txt(a,n['id'],'NODE')
   if any(n['restraints'][k] for k in ([0,2,4] if m['coordinate_system']['dimension']=='2d' else range(6))):txt((a[0],a[1]-.25,a[2]),'LOCK:'+','.join(['X','Y','Z','RX','RY','RZ'][k] for k,v in enumerate(n['restraints']) if v),'SUPPORT')
 out.extend(['0','ENDSEC','0','EOF']);path.write_text('\n'.join(out)+'\n',encoding='ascii')

def export_specs(specs):
 for s in specs:export(s)

def section_sheet(path,m):
 groups={}
 for e in m['elements']:groups.setdefault((e['section'],e.get('rotation_angle',0)),[]).append(e['id'])
 c=Canvas(1800,160+330*math.ceil(len(groups)/3));c.text((30,20),'SECTION AND ROLL DETAILS | dimensions mm; principal inertias and torsion in properties.json',25)
 secs={s['id']:s for s in m['sections']}
 for i,((sid,roll),ids) in enumerate(groups.items()):
  x=50+(i%3)*590;y=100+(i//3)*330;sec=secs[sid];shape=sec.get('shape',{})
  B=shape.get('B',shape.get('Bpositive3',shape.get('b',300)));H=shape.get('H',shape.get('h',500));scale=110/max(B,H)
  c.text((x,y),sid+f' | roll {roll:g} deg',21)
  # Cross-section viewed along positive local 1. Rotated outline is visible.
  cx,cy=x+115,y+115;a=math.radians(roll)
  outline=[(-B/2,-H/2),(B/2,-H/2),(B/2,H/2),(-B/2,H/2)]
  if shape.get('kind') in ('H','unequal-flange-I'):
   bp=shape.get('Bpositive3',B);bn=shape.get('Bnegative3',B);tw=shape['tw'];tf=shape['tf'];z0=-shape.get('centroidFromNegative3Edge',H/2);z1=z0+H
   outline=[(-bn/2,z0),(bn/2,z0),(bn/2,z0+tf),(tw/2,z0+tf),(tw/2,z1-tf),(bp/2,z1-tf),(bp/2,z1),(-bp/2,z1),(-bp/2,z1-tf),(-tw/2,z1-tf),(-tw/2,z0+tf),(-bn/2,z0+tf)]
  pts=[]
  for yy,zz in outline:
   pts.append((cx+scale*(yy*math.cos(a)-zz*math.sin(a)),cy-scale*(yy*math.sin(a)+zz*math.cos(a))))
  for j in range(len(pts)):c.line(pts[j],pts[(j+1)%len(pts)],'#294966',3)
  c.line((cx,cy),(cx+90,cy),'#207050',2);c.text((cx+95,cy-12),'2 before roll',14)
  # Keep axis captions below the roll title and reserve a separate right-hand
  # column for properties; both labels previously overprinted other text.
  c.line((cx,cy),(cx,cy-90),'#207050',2);c.text((cx+12,cy-80),'3 before roll',14)
  c.text((x+330,y+65),f'B={B:g}; H={H:g}',18)
  c.text((x+330,y+92),'Iy about local 2',17);c.text((x+330,y+118),'Iz about local 3',17)
  if shape.get('kind')!='rectangular':c.text((x,y+185),'Exact flange/web sizes and centroid in appendix.',16)
  # Wrap visible assignment labels without encoding hidden topology.
  labels=', '.join(ids)
  import textwrap
  for j,line in enumerate(textwrap.wrap(labels,60)):c.text((x,y+215+j*20),line,14)
 c.save(path)

def export(s):
 cid=s['id'];assert 51<=int(cid[3:])<=100;row=ROWS[cid];en=row['locale']=='en' if 'locale' in row else row['language']=='英文';m=s['model'];out=ROOT/'corpora/research-300/cases'/cid;out.mkdir(parents=True,exist_ok=True)
 for old in list(out.glob('drawing-*.png'))+list(out.glob('drawing-*.svg'))+list(out.glob('initial-*.png'))+list(out.glob('initial-*.svg')):old.unlink()
 # Drop unassigned placeholder properties: the appendix is the actual material/section state.
 mids={e['material'] for e in m['elements']};sids={e['section'] for e in m['elements']};m['materials']=[x for x in m['materials'] if x['id'] in mids];m['sections']=[x for x in m['sections'] if x['id'] in sids]
 dump(out/'model-state-1.json',m)
 clarify=cid in ('MM-058','MM-072');architectural=row['subcategory']=='建筑DXF';public=[];complete=[]
 drawing_model=m
 if cid=='MM-094':
  drawing_model=deepcopy(m);drawing_model['_renderAxisLabels']={'x':'u','y':'w','z':'v'}
  for n in drawing_model['nodes']:n['y']=-n['y']
  for lc in drawing_model['load_cases']:
   for ld in lc['loads']:
    for key in ('fy','wy','my'):
     if key in ld:ld[key]=-ld[key]
 # Architectural geometry stays in the original DXF, including its A-* layers.
 # An extracted structural drawing would bypass the required filtering task.
 for v in ([] if architectural else views(drawing_model)):
  if cid=='MM-094':v=(v[0].replace('XZ','uv').replace('YZ','wv').replace('X','u').replace('Y','w').replace('Z','v'),*v[1:])
  name='drawing-'+v[0];draw_view(out/name,drawing_model,v,cid);complete += [name+'.png',name+'.svg']
  if clarify:
   first='initial-'+v[0];draw_view(out/first,m,v,cid,'incomplete');public += [first+'.png',first+'.svg']
 if not clarify:public+=complete
 section_sheet(out/'section-details',m);public+=['section-details.png','section-details.svg']
 if 'DXF' in row['subcategory']:
  dxf(out/'input.dxf',m,row['subcategory']=='建筑DXF');public.append('input.dxf')
 props={'units':{'length':'m','force':'kN','moment':'kN*m','E':'MPa','G':'MPa','density':'kg/m3','A':'m2','Iy':'m4','Iz':'m4','J':'m4','rotation_angle':'deg'},'materials':m['materials'],'sections':m['sections'],'analysis_control':m['analysis_control'],'coordinate_system':m['coordinate_system'],'analysis':'first-order linear elastic static; use full explicit stiffness; no automatic reduction','localAxes':{'beam':'local x follows the thin arrow on each drawn member from first to second end','2d':'XZ plane; before roll local y = global +Y, local z = local x cross local y; Iy controls unrolled in-plane bending; M2 is about local y','3d':'local y = reference cross local x; local z = local x cross local y; rotation_angle applies right-hand roll about local x'},'notes':s.get('public_notes',[])}
 if m['coordinate_system']['dimension']=='2d':props['planarConstraints']='All nodes restrain uy, rx, rz. In-plane ux, uz, ry restraints follow the support symbols; unmarked in-plane DOFs are free.'
 if row['subcategory'] in ('建筑DXF','多视图重建'):
  props['boundaryConditions']=[{'node':n['id'],'restrainedDOFs':[d for d,r in zip(['ux','uy','uz','rx','ry','rz'],n['restraints']) if r]} for n in m['nodes']]
 if 'DXF' in row['subcategory']:
  props['dxfMapping']={'units':'m','structuralLayers':'architectural S-* layers are the structural geometry; A-* layers are nonstructural interference' if row['subcategory']=='建筑DXF' else 'S-* lines are physical members; NODE labels identify connections','viewTransform':'Architectural orthographic view j has CAD horizontal offset 40*j m; subtract that offset and use the named drawing axes. Structural 2D DXF maps (CAD X,CAD Y,CAD Z)=(global X,global Z,0). Structural 3D DXF uses global XYZ.'}
 if architectural:
  props['localAxes']['beam']='local x follows each structural DXF LINE from its start point (group codes 10/20/30) to its end point (11/21/31), reconciled across the labelled orthographic views'
  props['dxfMapping']['structuralLayers']='Read physical members from S-BEAM/S-COLUMN lines and match S-MEMBER-TAG/S-NODE-TAG labels. A-WALL, A-COLUMN and A-EQUIPMENT outlines are nonstructural distractors, not members or connections. A-DIM and A-SUPPORT are annotations; support DOFs are specified in boundaryConditions.'
  props['dxfMapping']['connectivity']='Reconcile repeated node/member labels across views into one physical graph; intersections connect only at labelled nodes. Section-detail sheets show properties and member assignments, not structural geometry.'
 if cid=='MM-094':props['sourceCoordinateMapping']={'source':'right-handed (u,v,w), v upward','global':'(X,Y,Z)=(u,-w,v)','force':'(Fx,Fy,Fz)=(Fu,-Fw,Fv)'}
 # IDs/end labels refer to the drawing, never expose coordinates in a table.
 assignments=[]
 for e in m['elements']:
  assignments.append({'id':e['id'],'type':e['type'],'material':e['material'],'section':e['section'],'rotation_angle':e.get('rotation_angle',0),'referenceVector':m.get('metadata',{}).get('elementReferenceVectors',{}).get(e['id'])})
 dump(out/'properties.json',props);dump(out/'assignments.json',assignments)
 loads={'units':'forces kN; moments kN*m; line loads kN/m of actual member length; positions m from first end; global axes','load_cases':m['load_cases'],'load_combinations':m['load_combinations']}
 if 'floorAreaLoads' in m.get('metadata',{}):loads['floorAreaLoads']=m['metadata']['floorAreaLoads']
 if cid=='MM-094':
  loads['units']='Source-coordinate vectors: forces kN, line loads kN/m, (X,Y,Z)=(u,-w,v).';loads['load_cases']=deepcopy(drawing_model['load_cases'])
  for lc in loads['load_cases']:
   for ld in lc['loads']:
    ld['reference_frame']='source-uvw'
    for key in list(ld):
     if len(key)==2 and key[0] in 'fwm' and key[1] in 'xyz':ld[key[0]+{'x':'u','y':'w','z':'v'}[key[1]]]=ld.pop(key)
 dump(out/'loads.json',loads)
 public+=['properties.json','assignments.json']
 if row['subcategory']!='力学简图':public.append('loads.json')
 qs=[];reqs=[]
 for i,q0 in enumerate(s['requests']):
  q=deepcopy(q0);desc=q.pop('description');q.setdefault('selection',{'kind':'case','id':'D'});old=q['id'];prefix=q['selection']['kind']+'-'+q['selection']['id']+'-';q['id']=old if old.startswith(prefix) else prefix+old;q.setdefault('tolerance',TOL.copy());qs.append(q)
  reqs.append({'id':'o'+str(i+1),'description':desc,'state':1,'quantityIds':[q['id']],'kind':'numerical'})
 derived=deepcopy(s.get('derived',[]))
 for d in derived:
  # Support raw unique operand IDs as a convenience, while file IDs always include selection.
  d['operands']=[next((q['id'] for q in qs if q['id']==op or q['id'].endswith('-'+op)),op) for op in d['operands']]
  reqs.append({'id':d['id'],'description':d['description'],'state':1,'quantityIds':[d['id']],'kind':'derived'})
 reqs.append({'id':'figures','description':'Provide a labelled model view and result/deformed-shape figures consistent with the reported signed values and selected loads.' if en else '提供带节点和构件编号的模型图、与所报符号数值及荷载选择一致的结果图或变形图。','state':1,'quantityIds':[],'kind':'figure'})
 dump(out/'reference-requests.json',{'schemaVersion':1,'states':[{'state':1,'model':'model-state-1.json','quantities':qs,'derived':derived}]})
 numerical='\n'.join(f"- {o['description']} [{', '.join(o['quantityIds'])}]" for o in reqs if o['kind'] in ('numerical','derived'))
 if en:
  prompt=f"{s['title_en']}\n\nReconstruct the structure from the attached dimensioned drawings and, where supplied, DXF. Use the matching member labels in the property, assignment and load appendices. Geometry and support evidence must be read from the drawings. Perform first-order linear elastic analysis using {row['plannedEngine']}; save the self-weight OFF and no-rigid-diaphragm settings. Use explicit section/material stiffness and signed right-handed global axes, Z upward. Retain actual load positions and distributed loads.\n\nReport all of the following for each stated selection, with signs and units:\n{numerical}\n\nProvide labelled model and result figures consistent with the numerical values. Preserve the input-to-model ID mapping, engine version/settings, current execution log, original result tables and figure data. If an essential datum is missing, ask specifically for it before analysis.\n"
 else:
  prompt=f"{row['title']}\n\n从所附尺寸图及提供时的DXF重建结构，利用图中编号对应属性、分配和荷载附表；几何与支承必须从图纸识别。采用{row['plannedEngine']}作一阶线弹性计算，保存自重关闭、无刚性楼板的设置，使用明示完整材料与截面刚度。全局右手坐标Z向上，保留真实分布荷载及作用位置。\n\n逐项输出以下带符号、单位和荷载选择的结果：\n{numerical}\n\n附带编号模型图及与数值一致的结果图，保存图纸编号到计算模型的映射、引擎版本及设置、当前执行日志、原始结果表和绘图数据。必要信息缺失时先针对缺项询问。\n"
 if architectural:
  if en:
   prompt=prompt.replace('Reconstruct the structure from the attached dimensioned drawings and, where supplied, DXF. Use the matching member labels in the property, assignment and load appendices. Geometry and support evidence must be read from the drawings.',
    'Reconstruct geometry and connectivity from the architectural input.dxf, interpreting its S-* structural lines and labels while filtering the A-* wall, column-footprint and equipment distractors. Reconcile the labelled orthographic views using properties.json dxfMapping. Read supports from properties.json boundaryConditions and the CAD annotations; use the matching member labels in assignments.json and loads.json. Section-detail images describe section properties and roll only. Member local direction follows DXF LINE start-to-end as specified in properties.json; no structural geometry image is supplied.')
  else:
   prompt=prompt.replace('从所附尺寸图及提供时的DXF重建结构，利用图中编号对应属性、分配和荷载附表；几何与支承必须从图纸识别。',
    '从建筑图 input.dxf 识别几何与连接关系，读取 S-* 结构线及编号，筛除 A-* 墙线、柱轮廓及设备干扰；按 properties.json 的 dxfMapping 合并各正投影视图。支承按 properties.json 的 boundaryConditions 及CAD标注读取，利用编号对应 assignments.json 与 loads.json；截面详图仅说明截面属性和转角，不提供结构几何图。构件局部方向按 properties.json 说明取DXF LINE起点至终点。')
 (out/'prompt.txt').write_text(prompt)
 if clarify:
  cf=s.get('clarify',{});field=cf.get('field','column-base restraints' if cid=='MM-058' else 'right-bay vertical offset')
  question=cf.get('question','What are the restraints at both cropped column bases?' if cid=='MM-058' else 'What is the right-bay vertical level offset relative to each left-bay beam?')
  instruction=cf.get('instruction','The first image is incomplete. Reconstruct the available information and identify the missing essential datum.')
  resolution=cf.get('resolution','The complete support drawing is now attached; both column bases are fixed. Analyze and report all requested outputs.' if cid=='MM-058' else 'The right bay is 0.5 m above the left bay at each storey. The complete elevation is attached. Analyze and report all requested outputs.')
  turns=[{'id':'t1','instruction':prompt+'\n'+instruction,'state':None,'expectation':'clarify','attachments':public,'unresolvedFields':[field],'expectedQuestions':[question]},{'id':'t2','instruction':resolution,'state':1,'expectation':'analyze','attachments':complete,'unresolvedFields':[],'expectedQuestions':[]}]
  reqs.append({'id':'clarification','description':question,'state':None,'quantityIds':[],'kind':'interaction'})
 else:turns=[{'id':'t1','instruction':prompt,'state':1,'expectation':'analyze','attachments':public,'unresolvedFields':[],'expectedQuestions':[]}]
 allpublic=public+(complete if clarify else [])
 gates=[{'id':key,'status':'pending','description':desc} for key,desc in [('inputBlindReview','Independent reconstruction from public modality inputs'),('nativeExecution','Fresh prescribed-engine execution, original outputs and input/settings hashes'),('independentReference','Independent numerical references for every selection and requested position'),('adapterMapping','Prescribed-engine mapping of topology, loads, units, axes and outputs'),('figureConsistency','Figures checked against model and result data')]]
 # Resolve source requirements to individual public inputs, turns, outputs and
 # pending acceptance gates. Collection/property names are not evidence IDs.
 coverage=[];load_target='attachment:loads.json' if 'loads.json' in allpublic else 'attachment:drawing-elevation-XZ.png'
 turn_targets=['turn:'+t['id'] for t in turns]
 attachment_targets=['attachment:'+name for name in allpublic]
 output_targets=['output:'+o['id'] for o in reqs]
 quantity_targets=['quantity:'+q['id'] for q in qs+derived]
 for field in row['sourceRequirements']:
  ids=[r['id'] for r in row['requirements'] if r['sourceField']==field]
  if field in ('engine.truthPlan','task.prerequisite'):targets=['gate:independentReference','gate:inputBlindReview','attachment:properties.json']
  elif field in ('engine.executionRequirement','engine.requiredEvidence','engine.adapterGap'):targets=['gate:nativeExecution','gate:adapterMapping']+output_targets
  elif field in ('task.expectedOutput','task.gradingFocus'):targets=output_targets+quantity_targets+['gate:figureConsistency']
  elif field=='engine.analysisContract':targets=['attachment:properties.json',load_target,'gate:adapterMapping']
  elif field=='model.propertyKey':targets=['attachment:properties.json','attachment:assignments.json']+turn_targets
  elif field=='model.loadKey':targets=[load_target]
  else:targets=turn_targets+attachment_targets+['gate:inputBlindReview']
  coverage.append({'sourceField':field,'requirementIds':ids,'targets':targets,'notes':'Authored evidence mapping only; independent input, native execution and reference acceptance remain pending.'})
 contract={'schemaVersion':1,'evaluationProfile':'engineering-v2.3','id':cid,'modelId':row['modelId'],'family':row['family'],'language':row['language'],'locale':'en' if en else 'zh','plannedEngine':row['plannedEngine'],'sourcePlan':{'sourceRequirements':row['sourceRequirements'],'requirements':row['requirements'],'sourceTaskTurns':SOURCE_TASKS[cid]['turns'],'subcategory':row['subcategory']},'modelStates':['model-state-1.json'],'attachments':allpublic,'turns':turns,'requiredOutputs':reqs,'requirementCoverage':coverage,'acceptanceGates':gates,'status':'authored-candidate','sameEngineTruthStatus':'pending','inputBlindReview':'pending','llmEndToEnd':'not-run'}
 dump(out/'contract.json',contract)
 decisions=s.get('decisions',[])+['Unspecified M1 steel frozen as E=206000 MPa, nu=0.3, rho=7850 kg/m3; any explicitly named concrete grade overrides it. Unspecified section aliases use the complete appendix values, not a solver default.','A requested unspecified member end moment is expanded to both ends where applicable; section result sign follows the explicit local-axis convention.','Default tolerance frozen at absolute 1e-8 plus relative 1e-6 before candidate runs. No numerical reference values authored here.']
 dump(out/'author-review.json',{'sourceModel':SOURCE_MODELS[cid],'sourceTask':SOURCE_TASKS[cid],'decisions':decisions,'status':'author-source-check-only','inputBlindReview':'pending','nativeExecution':'pending','independentReference':'pending'})
 revise_authored_case(out)
 print(cid,len(m['nodes']),'nodes',len(m['elements']),'members',len(qs),'requests')
