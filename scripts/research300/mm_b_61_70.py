"""Explicit MM-061..070 source authoring; regenerate with python3 this_file.py."""
from mm_b_common import p, midpoint, rq, mq, export_specs

def concrete(m,grade='C30'):
 E={'C30':30000,'C35':31500,'C40':32500}[grade]
 m['materials']=[dict(id='M1',name=grade,type='concrete',E=E,G=E/2.4,nu=.2,rho=2500)]
 return m

def node_at(m,id):return next(n for n in m['nodes'] if n['id']==id)
def remove(m,*ids):m['elements']=[e for e in m['elements'] if e['id'] not in ids]
def allbeams(m,q):p.beams_udl(m,q)
def spec(i,m,title,requests,notes=(),decisions=()):
 return dict(id=f'MM-{i:03}',model=m,title_en=title,requests=requests,public_notes=list(notes),decisions=list(decisions))

def build_specs():
 out=[]
 # 061: three genuinely distinct supports, right support is free to move horizontally.
 m=p.frame([0,4.5,12],[3.6,7.8]);node_at(m,'n0-0')['restraints']=[True,True,True,True,False,True];node_at(m,'n2-0')['restraints']=[False,True,True,True,False,True]
 allbeams(m,10);p.load(m,type='nodal',node='n2-2',fx=20)
 out.append(spec(61,m,'Unequal-bay frame with three base restraint types',[rq('n2-2','ux','顶层右节点n2-2的Ux'),rq('n2-0','ux','右柱脚n2-0的Ux'),mq(m,'c1-1','M2','中底柱c1-1底端M2')]))
 # 062: upper setback, lower frame stays two bays, upper cantilever extends to left.
 m=p.frame([0,6,12],[3.6]);p.node(m,'u0',0,6.9);p.node(m,'u1',6,6.9);p.node(m,'tip',-2,6.9)
 p.elem(m,'uc0','n0-1','u0','column','C1');p.elem(m,'uc1','n1-1','u1','column','C1');p.elem(m,'upper','u0','u1');p.elem(m,'cant','tip','u0',sec='B2')
 for e,q in [('b0-1',10),('b1-1',10),('upper',8),('cant',12)]:p.load(m,type='distributed',element=e,wz=-q)
 out.append(spec(62,m,'Setback frame with an upper left cantilever',[rq('tip','uz','Upper left free tip: Uz'),mq(m,'uc0','M2','Upper left column at its top: M2',True)]))
 # 063: one diagonal in each storey, opposite inclinations, axial-only.
 m=p.frame([0,6],[3.6,7.2]);p.elem(m,'brace1','n0-0','n1-1','truss','A1');p.elem(m,'brace2','n1-1','n0-2','truss','A1');allbeams(m,10);p.load(m,type='nodal',node='n1-2',fx=20)
 out.append(spec(63,m,'Alternating single diagonals',[rq('n1-2','ux','顶层右节点Ux'),mq(m,'brace1','N','首层斜撑轴力N'),mq(m,'brace2','N','二层斜撑轴力N')],['绿色斜杆仅承轴力；与梁柱连接于图示端点。']))
 # 064: lower right overhang and upper left overhang, separate lengths and loads.
 m=p.frame([0,6],[3.6,7.2]);p.node(m,'tipR',7.5,3.6);p.node(m,'tipL',-2,7.2);p.elem(m,'cantR','n1-1','tipR',sec='B2');p.elem(m,'cantL','tipL','n0-2',sec='B2')
 for e in m['elements']:
  if e['type']=='beam':p.load(m,type='distributed',element=e['id'],wz=-({'cantR':6,'cantL':12}.get(e['id'],10)))
 out.append(spec(64,m,'Staggered cantilevers on opposite storeys',[rq('tipR','uz','Lower right cantilever tip: Uz'),rq('tipL','uz','Upper left cantilever tip: Uz'),mq(m,'cantL','M2','Upper left cantilever at its root: M2',True)]))
 # 065: keep roof midpoint node, remove upper central COLUMN only.
 m=p.frame([0,5,10],[3.3,6.6,9.9]);remove(m,'c1-3')
 for e in m['elements']:
  if e['type']=='beam':p.load(m,type='distributed',element=e['id'],wz=-{1:12,2:10,3:6}[int(e['id'].split('-')[-1])])
 p.load(m,type='nodal',node='n1-3',fz=-25)
 out.append(spec(65,m,'Roof without the upper centre column',[rq('n1-3','uz','顶层连续梁中点n1-3的Uz'),mq(m,'c1-2','N','第二层中柱底端轴力N'),mq(m,'c1-2','N','第二层中柱顶端轴力N',True)],decisions=['Unspecified axial-force station expanded to both ends of the second-storey middle column.']))
 # 066: section boundary is an actual connected node, with section on each half.
 m=p.frame([0,6,12],[3.6,7.2]);m['sections'].append(p.section('B3',.25,.5));midpoint(m,'b0-1','obs')
 for e in m['elements']:
  if e['id'].startswith('c1-'):e['section']='C2'
  if e['id']=='b0-1b':e['section']='B2'
  if e['id'] in ('b1-1','b0-2'):e['section']='B3'
 allbeams(m,10);p.load(m,type='nodal',node='n1-2',fx=30)
 out.append(spec(66,m,'Within-span section change in a steel frame',[rq('obs','uz','Lower left beam at its connected midpoint: Uz'),rq('n1-2','ux','Top central joint: Ux')],['B3 is the explicit 250 by 500 mm solid rectangular elastic section in the appendix.'],['B3 absent from source numeric appendix: frozen 0.25 by 0.50 m rectangle.']))
 # 067: no disconnected middle base node; transfer beam supports upper central column.
 m=p.frame([0,5,10],[3.6,7.2]);remove(m,'c1-1');m['nodes']=[n for n in m['nodes'] if n['id']!='n1-0']
 for e in m['elements']:
  if e['id'] in ('b0-1','b1-1'):e['section']='B2'
 allbeams(m,10)
 out.append(spec(67,m,'Transfer frame without a ground-storey middle column',[rq('n1-1','uz','转换梁中点n1-1的Uz'),mq(m,'c1-2','N','上层中柱底端轴力N'),mq(m,'c1-2','N','上层中柱顶端轴力N',True)],decisions=['Upper middle column axial force requested at both ends.']))
 # 068: absolute elevations, unequal base heights, same floor levels.
 m=p.frame([0,6],[2.1,5.7]);node_at(m,'n0-0')['z']=-1.5;allbeams(m,10)
 out.append(spec(68,m,'Steel frame with unequal foundation elevations',[rq('n0-2','ux','Top left joint: Ux'),mq(m,'c0-1','M2','Left base column at bottom: M2'),mq(m,'c1-1','M2','Right base column at bottom: M2')]))
 # 069: distinct left/right balcony loads and concrete properties.
 m=concrete(p.frame([0,6],[3.6,7.2],True));m['sections']=[p.section('B1',.3,.6),p.section('C1',.5,.5),p.section('B2',.25,.5)]
 p.node(m,'tipL',-1.2,3.6);p.node(m,'tipR',7.2,3.6);p.elem(m,'cantL','tipL','n0-1',sec='B2');p.elem(m,'cantR','n1-1','tipR',sec='B2')
 for e in m['elements']:
  if e['type']=='beam':p.load(m,type='distributed',element=e['id'],wz=-{'cantL':15,'cantR':20}.get(e['id'],72))
 out.append(spec(69,m,'Concrete frame with unequal balcony loads',[rq('tipL','uz','首层左悬挑端Uz'),rq('tipR','uz','首层右悬挑端Uz'),mq(m,'cantR','M2','首层右悬段根部M2')]))
 # 070: second-storey left column really inclined, no rigid offset.
 m=concrete(p.frame([0,6],[3.3,6.6,9.9],True,lefts=[0,0,1,1]),'C35');allbeams(m,60)
 out.append(spec(70,m,'Concrete frame with an inclined middle-storey column',[rq('n0-2','ux','Inclined column upper joint: Ux'),rq('n0-2','uz','Inclined column upper joint: Uz'),mq(m,'c0-1','M2','Left bottom column at its base: M2')]))
 return out

if __name__=='__main__':export_specs(build_specs())
