"""Build a fresh numerical YDB through the installed YJK SDK.

Input is the numeric packet retained in the native evidence: SI node/property/
load values, section shape B/H in mm, explicit reference_vectors and stories.
No host is started and no analysis is run here. The caller owns output_dir and
must run the native input audit before using a result. Native beam subdivision,
material-family E/nu, six rigidity coefficients, and text precision are audited
separately; nominal dimensions alone do not certify equivalent stiffness.

Current native controls cover steel and C30/C35, full six-DOF fixed bases,
vertical columns, isotropic inclined columns, and planar/sloping beams with
zero authored roll and full-span global-Z uniform plus six-DOF nodal loads.
The SDK's inclined-column class may add free beam subdivision nodes. All
returned actual coordinates, segments, properties and constraints need checking.
Unsupported features fail; they are never converted to another physical model.
"""
import json,math,sqlite3,hashlib,shutil
from pathlib import Path

def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def unit(a):
 n=math.sqrt(dot(a,a))
 if n<=1e-12:raise ValueError('degenerate axis')
 return [v/n for v in a]
def mm(x):
 v=x*1000
 if abs(v-round(v))>1e-8:raise ValueError('coordinate not exact integer mm')
 return round(v)
def validate_packet(model):
 if model['analysis_control']!={'self_weight':False,'rigid_floor':False,'p_delta':False,'rigid_offsets':False,'construction_stage':False}:raise ValueError('unsupported control')
 nodes={n['id']:n for n in model['nodes']};materials={m['id']:m for m in model['materials']};sections={s['id']:s for s in model['sections']}
 for n in nodes.values():
  if n['restraints']!=[n['z']==0]*6:raise ValueError('unsupported support')
 for m in materials.values():
  for key in ('E','G','nu'):
   if type(m[key]) not in (int,float) or not math.isfinite(m[key]):raise ValueError('invalid material '+key)
  if m['E']<=0 or m['G']<=0 or not -1<m['nu']<.5:raise ValueError('nonphysical elastic material')
  if m['type'] not in ('steel','concrete'):raise ValueError('unsupported native material family')
  if m['type']=='concrete' and m.get('native_reference_grade') not in ('C30','C35'):raise ValueError('unmapped concrete reference grade')
 for section in sections.values():
  if section['type']!='rectangular':raise ValueError('unsupported section')
  for key in ('A','Iy','Iz','J','Asy','Asz'):
   value=section['properties'].get(key,1.)
   if type(value) not in (int,float) or not math.isfinite(value) or value<=0:raise ValueError('nonpositive/nonfinite section property '+key)
  for key in ('B','H'):
   if section['shape'][key]<=0:raise ValueError('nonpositive section dimension')
 for e in model['elements']:
  a,b=[nodes[k] for k in e['nodes']]
  if e.get('rotation_angle',0)!=0:raise ValueError('nonzero authored roll is not qualified by this builder')
  if e['type']=='column':
   if a['z']>=b['z']:raise ValueError('column source order must be upward')
   if a['x']!=b['x'] or a['y']!=b['y']:
    prop=sections[e['section']]['properties']
    if prop['Iy']!=prop['Iz'] or prop.get('Asy',5*prop['A']/6)!=prop.get('Asz',5*prop['A']/6):raise ValueError('inclined-column anisotropic roll requires separate native qualification')
  elif e['type']=='beam':
   if a['x']==b['x'] and a['y']==b['y']:raise ValueError('vertical beam unsupported')
  else:raise ValueError('unsupported member')
  if any(k in e for k in ('releases','offsets','rigid_offsets')):raise ValueError('unsupported special member')
 return nodes,materials,sections

def build(model,RUN):
 nodes,materials,sections=validate_packet(model)
 RUN=Path(RUN)
 RUN.mkdir(parents=True,exist_ok=True)
 if (RUN/'cal.ydb').exists() or (RUN/'cal-sdk-original.ydb').exists():raise ValueError('refusing an existing YDB exchange')
 from YJKAPI import DataFunc,BzcPara,Hi_AddToAndReadYjk,GKLoadDefCreateInfo,Property
 def dump(n,v):(RUN/n).write_text(json.dumps(v,indent=2),encoding='utf-8')
 d=DataFunc();sn={};brace_sections={};native_nodes={};members={};mapping={'nodes':{},'members':{},'load_cases':[],'shear_area_assumption':'rectangular effective Asy=Asz=5A/6; native Timoshenko numerical probe; authored files unchanged'}
 for e in model['elements']:
  key=(e['section'],e['type'],e['material'])
  if key in sn:continue
  s=sections[e['section']]
  if s['type']!='rectangular':raise ValueError('unsupported section')
  shape=s['shape'];f=d.ColSect_Def if e['type']=='column' else d.BeamSect_Def
  sn[key]=f(5 if materials[e['material']]['type']=='steel' else 6,1,','.join(format(shape[k],'.17g') for k in ['B','H']),s['id'])
  if e['type']=='column':brace_sections[key]=d.BraceSect_Def(5 if materials[e['material']]['type']=='steel' else 6,1,','.join(format(shape[k],'.17g') for k in ['B','H']),s['id'])
 for i,story in enumerate(sorted(model['stories'],key=lambda s:s['elevation']),1):
  base=story['elevation'];height=story['height'];top=base+height
  floor=d.StdFlr_Generate(mm(height),0.,0.,'','F'+str(i));p=BzcPara();p.setVal(1,0);p.setVal(24,356);p.setVal(25,356);floor.Para=p.GetValString();plan_nodes={}
  for nid,n in nodes.items():
   if abs(n['z']-top)<1e-8 or nid in story.get('top_nodes',[]):
    j=d.Joint_Generate(floor.ID,mm(n['x']),mm(n['y']),mm(n['z']-top));native_nodes[nid]=j;plan_nodes[(n['x'],n['y'])]=j;mapping['nodes'][nid]={'sdk_id':int(j.ID),'floor':i,'coordinates':[n[k] for k in 'xyz']}
  for e in model['elements']:
   a,b=[nodes[k] for k in e['nodes']]
   if not(abs(b['z']-top)<1e-8 or e['nodes'][1] in story.get('top_nodes',[])):continue
   sec=sections[e['section']];mat=materials[e['material']];x=unit([b[k]-a[k] for k in 'xyz']);ref=model['reference_vectors'][e['id']];y=unit(cross(ref,x));z=cross(x,y)
   if e['type']=='column':
    if abs(a['z']-base)>1e-8:raise ValueError('column crosses represented story')
    if a['x']==b['x'] and a['y']==b['y']:
     rotation=math.degrees(math.atan2(y[1],y[0]))%180
     native=d.column_arrange(native_nodes[e['nodes'][1]],sn[(e['section'],'column',e['material'])],0,0,rotation,0)
    else:
     up=[0,0,1];projected=unit([up[j]-dot(up,x)*x[j] for j in range(3)])
     rotation=math.degrees(math.atan2(dot(x,cross(projected,z)),dot(projected,z)))%180
     lower=plan_nodes.get((a['x'],a['y']))
     if lower is None:lower=d.Joint_Generate(floor.ID,mm(a['x']),mm(a['y']),mm(base-top));plan_nodes[(a['x'],a['y'])]=lower
     native=d.brace_arrange(lower,native_nodes[e['nodes'][1]],brace_sections[(e['section'],'column',e['material'])],0,0,0,0,0,mm(b['z']-base),rotation)
     fixed=Property('SpBrac');fixed.setVal(0,0);fixed.setVal(1,0);d.property_arrange(int(native.ID),'SpBrac',27,fixed.GetValString())
   else:
    if not(abs(a['z']-top)<1e-8 or e['nodes'][0] in story.get('top_nodes',[])):raise ValueError('beam crosses represented story')
    native_x=x if (x[0]>1e-9 or (abs(x[0])<=1e-9 and x[1]>=0)) else [-v for v in x]
    up=[0,0,1];projected=unit([up[j]-dot(up,native_x)*native_x[j] for j in range(3)])
    rotation=math.degrees(math.atan2(dot(native_x,cross(projected,z)),dot(projected,z)))%180
    axis=d.Axis_Generate(floor.ID,native_nodes[e['nodes'][0]].ID,native_nodes[e['nodes'][1]].ID)
    grid=d.Grid_Generate(floor.ID,native_nodes[e['nodes'][0]].ID,native_nodes[e['nodes'][1]].ID,axis.ID)
    native=d.beam_arrange(grid,sn[(e['section'],'beam',e['material'])],0,0,0,rotation);native.NoSlab=1
   B,H=[sec['shape'][k]/1000 for k in ['B','H']];wide,narrow=max(B,H),min(B,H)
   native_props={'A':B*H,'Iy':B*H**3/12,'Iz':H*B**3/12,'J':wide*narrow**3*(1/3-.21*narrow/wide*(1-narrow**4/(12*wide**4))),'Asy':5*B*H/6,'Asz':5*B*H/6}
   prop=dict(sec['properties']);prop.setdefault('Asy',5*prop['A']/6);prop.setdefault('Asz',5*prop['A']/6)
   E=mat['E']*1000;G=mat['G']*1000;E0=206000000. if mat['type']=='steel' else {'C30':30000000.,'C35':31500000.}[mat['native_reference_grade']];G0=E0/(2.6 if mat['type']=='steel' else 2.5)
   if mat['type']=='concrete':d.property_arrange(int(native.ID),'HNTDJ',5,mat['native_reference_grade'][1:])
   keys=['A','Asz','Asy','J','Iz','Iy'];scales=[E/E0,G/G0,G/G0,G/G0,E/E0,E/E0];coeff=[scales[j]*prop[k]/native_props[k] for j,k in enumerate(keys)]
   shapeval=','.join(format(v,'.17g') for v in coeff)+',';d.property_arrange(int(native.ID),'SpBarRig',27,shapeval)
   members[e['id']]=native;mapping['members'][e['id']]={'sdk_id':int(native.ID),'floor':i,'kind':e['type'],'source_nodes':e['nodes'],'native_rotation_degrees':rotation,'source_axes_rows':[x,y,z],'source_material':mat,'source_section':sec,'native_baseline_section':native_props,'requested_effective_section':prop,'coefficients':coeff,'shapeval':shapeval,'expected_RF':[coeff[k] for k in [0,5,4,3,1,2]]}
  d.Floor_Assemb(floor,mm(base),mm(height),'F'+str(i))
 if len(members)!=len(model['elements']):raise ValueError('missing source member mapping')
 for ci,case in enumerate(model['load_cases'],1):
  info=GKLoadDefCreateInfo();info.SetDeadFacotr(0.);info.SetLiveFacotr(0,0.,0.,0.);info.SetName('LC'+str(ci));info.SetData('0,1,1,1,1,1,1,1,1,');nativecase=d.GKLoad_Def(info)
  cr={'source_case':case['id'],'native_name':'LC'+str(ci),'native_kind':int(nativecase.kind),'loads':[]}
  for load in case['loads']:
   if load.get('reference_frame')!='global':raise ValueError('load frame must be explicit global')
   if load['type']=='nodal':
    if load['node'] not in native_nodes:raise ValueError('load on unmapped/base node')
    vals=[-load.get('fz',0),load.get('mx',0),load.get('my',0),load.get('fx',0),load.get('fy',0),load.get('mz',0),0];kind=-1;target=native_nodes[load['node']]
   elif load['type']=='distributed':
    if any(load.get(k,0)!=0 for k in ['wx','wy']) or any(k in load for k in ['start','end','position']):raise ValueError('pilot only full-span vertical uniform loads')
    if load['element'] not in members:raise ValueError('unknown loaded member')
    eid=load['element'];element=next(e for e in model['elements'] if e['id']==eid);points=[[nodes[n][k] for k in 'xyz'] for n in element['nodes']];factor=math.dist(*points)/math.dist(points[0][:2],points[1][:2])
    vals=[1,-load['wz']*factor,0,0,0,0,0];kind=12;target=members[eid]
   else:raise ValueError('unsupported load')
   shapeval=','.join(format(v,'.17g') for v in vals);ld=d.Load_Def(kind,shapeval,load['id']);d.load_arrange([target],ld,nativecase.kind)
   cr['loads'].append({'source':load,'native_target':int(target.ID),'native_definition':int(ld.ID),'shapeval':shapeval})
  mapping['load_cases'].append(cr)
 for load in d.GetLoadSegList():load.strParas1='0,0,0,0,0,';load.strParasX='';load.strParasY='';load.strParasZ=''
 d.DbModel_Assign();bridge=Hi_AddToAndReadYjk(d.GetDbModelData())
 if not bridge.CreateYDB(str(RUN),'cal.ydb'):raise RuntimeError('CreateYDB false')
 ydb=RUN/'cal.ydb';shutil.copy2(ydb,RUN/'cal-sdk-original.ydb');changes=[]
 with sqlite3.connect(ydb) as db:
  if db.execute("SELECT COUNT(*) FROM tblProperty WHERE Name='SpBarRig'").fetchone()[0]!=len(members):raise RuntimeError('property count mismatch')
  for eid,row in mapping['members'].items():
   v=db.execute("SELECT Type,ShapeVal FROM tblProperty WHERE ID=? AND Name='SpBarRig'",(row['sdk_id'],)).fetchall()
   if len(v)!=1 or v[0][0]!=27:raise RuntimeError('property identity mismatch')
   actual=[float(t) for t in v[0][1].split(',') if t.strip()]
   if len(actual)!=6 or any(abs(a-b)>.005001 for a,b in zip(actual,row['coefficients'])):raise RuntimeError('unexpected SDK property distortion')
   db.execute("UPDATE tblProperty SET ShapeVal=? WHERE ID=? AND Name='SpBarRig' AND Type=27",(row['shapeval'],row['sdk_id']))
   changes.append({'member':eid,'before':v[0][1],'after':row['shapeval']})
 # Restore only validated source numeric load strings in this fresh pre-import exchange.
 load_changes=[]
 with sqlite3.connect(ydb) as db:
  for case in mapping['load_cases']:
   for load in case['loads']:
    row=db.execute('SELECT ShapeVal FROM tblLoadSect WHERE ID=?',(load['native_definition'],)).fetchone()
    if row is None:raise RuntimeError('missing native load definition')
    old=[float(t) for t in row[0].split(',') if t.strip()];want=[float(t) for t in load['shapeval'].split(',') if t.strip()]
    if len(old)!=len(want) or any(abs(a-b)>.00050001 for a,b in zip(old,want)):raise RuntimeError('unexpected load serialization')
    db.execute('UPDATE tblLoadSect SET ShapeVal=? WHERE ID=?',(load['shapeval']+',',load['native_definition']))
    load_changes.append({'native_definition':load['native_definition'],'before':row[0],'after':load['shapeval']+','})
 dump('load-input-precision.json',load_changes)
 dump('input-precision.json',{'scope':'new YDB exchange only before import; SpBarRig ShapeVal','changes':changes,'before_sha256':hashlib.sha256((RUN/'cal-sdk-original.ydb').read_bytes()).hexdigest(),'after_sha256':hashlib.sha256(ydb.read_bytes()).hexdigest()})
 dump('mapping.json',mapping);dump('input.json',model)
 return mapping
