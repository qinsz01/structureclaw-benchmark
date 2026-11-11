"""Per-case explicit topology/data for remaining root-owned MM-B tasks."""
from mm_b_common import p, midpoint, rq, mq, export_specs
from mm_b_61_70 import concrete,node_at,remove,spec

def build_specs():
 out=[]
 m=concrete(p.frame([0,4,10,14],[3.6,7.2],True));midpoint(m,'b1-1','obs')
 for e in m['elements']:
  if e['type']=='beam' and e['id'] not in ('b1-1','b1-1b'):p.load(m,type='distributed',element=e['id'],wz=-10 if e['id'].endswith('-1') else -12)
 out.append(spec(71,m,'Three-bay concrete frame with an unloaded central bay',[rq('obs','uz','首层中央跨连通中点Uz'),mq(m,'c1-1','N','第二根底柱下端N'),mq(m,'c1-1','N','第二根底柱上端N',True)],decisions=['Axial-force station expanded to both ends of the second bottom column.']))
 # 072: every left/right floor connection splits shared centre column; no duplicate nodes.
 m=concrete(p.model(concrete=True));levelsL=[0,3.3,7.3,10.4];levelsR=[0,3.8,7.8,10.9];levelsC=sorted(set(levelsL+levelsR))
 for line,x,levels in [('L',0,levelsL),('C',5,levelsC),('R',12,levelsR)]:
  for i,z in enumerate(levels):p.node(m,f'{line}{i}',x,z,restraint=[True]*6 if i==0 else None)
  for i in range(1,len(levels)):p.elem(m,f'{line}c{i}',f'{line}{i-1}',f'{line}{i}','column','C1')
 for i in range(1,4):
  p.elem(m,f'Lb{i}',f'L{i}',f'C{2*i-1}');p.elem(m,f'Rb{i}',f'C{2*i}',f'R{i}')
 midpoint(m,'Lb3','obsL');midpoint(m,'Rb3','obsR');p.beams_udl(m,10)
 s=spec(72,m,'Staggered-level concrete frame: incomplete elevation',[rq('obsL','uz','Top left beam connected midpoint: Uz'),rq('obsR','uz','Top right beam connected midpoint: Uz'),mq(m,'Cc4','M2','Central column middle short segment at lower end: M2'),mq(m,'Cc4','M2','Central column middle short segment at upper end: M2',True)],['In the initial image the unknown right-bay offset is deliberately schematic, not measurable from pixels.'],['The middle short centre-column segment is the second level pair (7.3 to 7.8 m); request both ends. First-turn display uses a nonphysical schematic gap; neither dimensions nor appendices reveal the true 0.5 m.'])
 out.append(s)
 # 073: three material records, assigned by member function and storey.
 m=concrete(p.frame([0,6,12],[3.6,7.2],True),'C40');m['materials']=[dict(id=k,name=k,type='concrete',E=E,G=E/2.4,nu=.2,rho=2500) for k,E in [('C30',30000),('C35',31500),('C40',32500)]];m['sections'].append(p.section('BC',.25,.5))
 p.node(m,'tip',-1.5,7.2);p.elem(m,'cant','tip','n0-2',sec='BC')
 for e in m['elements']:
  e['material']='C40' if e['type']=='column' else 'C30' if e['id'].endswith('-1') else 'C35'
  if e['type']=='beam':p.load(m,type='distributed',element=e['id'],wz=-8 if e['id']=='cant' else -10)
 out.append(spec(73,m,'Storey-dependent concrete grades and a top cantilever',[rq('tip','uz','顶层左悬端Uz'),mq(m,'c0-1','N','左底柱下端N'),mq(m,'c0-1','N','左底柱上端N',True)]))
 # 074: rectangular principal axes and physical 90 degree roll on right columns.
 m=concrete(p.frame([0,7,11],[3.6,7.2],True));m['sections']=[p.section('Crect',.4,.7),p.section('C1',.5,.5),p.section('B1',.3,.6)]
 for e in m['elements']:
  if e['id'].startswith(('c0-','c2-')):e['section']='Crect'
  if e['id'].startswith('c2-'):e['rotation_angle']=90
 p.beams_udl(m,12);p.load(m,type='nodal',node='n2-2',fx=25)
 s=spec(74,m,'Concrete frame with three column section orientations',[rq('n2-2','ux','Top right joint: Ux'),mq(m,'c0-1','M2','Left base column at bottom: local M2'),mq(m,'c2-1','M3','Right rolled base column at bottom: local M3')],['Section detail sheets define the left rectangular strong bending direction in XZ and the right 90-degree roll. Right-column global-Y bending is local M3 after roll. Report the sign using the stated local basis.'],['Right 90-degree rolled column in-plane moment requested as local M3; left is M2. Complete inertia and rotation retained.'])
 s['section_details']=True;out.append(s)
 # 075: top middle beam absent while all four columns remain, two real midpoints.
 m=concrete(p.frame([0,5,10,15],[3.6,7.2],True));remove(m,'b1-2');midpoint(m,'b0-2','obsL');midpoint(m,'b2-2','obsR')
 for e in m['elements']:
  if e['type']=='beam':p.load(m,type='distributed',element=e['id'],wz=-10 if e['id'].endswith('-1') else -8)
 req=[rq('obsL','uz','顶层左外跨中点Uz'),rq('obsR','uz','顶层右外跨中点Uz')]
 for n in ('n1-0','n2-0'):
  for c in ('Fx','Fz','My'):req.append(rq(n,c,f'内侧底柱脚{n}的{c}'))
 out.append(spec(75,m,'Two upper wings with the middle beam absent',req,decisions=['Inner base reactions expanded to all three active planar components at both inner supports.']))
 # 076: actual tributary width table, four different line load assignments.
 m=concrete(p.frame([0,5,12],[3.6,7.2],True));node_at(m,'n1-0')['restraints']=[True,True,True,True,False,True];midpoint(m,'b0-1','obs1');midpoint(m,'b0-2','obs2')
 widths={'b0-1':4,'b0-1b':4,'b1-1':6,'b0-2':6,'b0-2b':6,'b1-2':4}
 for eid,width in widths.items():p.load(m,type='distributed',element=eid,wz=-10*width)
 m.setdefault('metadata',{})['floorAreaLoads']={'pressureKNM2':10,'tributaryWidthMByMember':widths,'method':'line load = pressure times specified tributary width; no additional surface load'}
 out.append(spec(76,m,'Pinned middle base and storey-specific tributary widths',[rq('obs1','uz','First-storey left beam midpoint: Uz'),rq('obs2','uz','Second-storey left beam midpoint: Uz')]+[rq('n1-0',c,'Middle base reaction '+c) for c in ('Fx','Fz','My')],['The floor load is 10 kN/m2. The load appendix gives the specified tributary widths and converted line loads; apply only the converted lines.'],['Pinned middle support moment is explicitly requested as zero reaction in addition to force components.']))
 # 077: only second right beam omitted; lower two storeys larger columns, roof smaller beams.
 m=concrete(p.frame([0,6,12],[3.3,6.6,9.9,13.2],True));remove(m,'b1-2');m['sections']=[p.section('C1',.5,.5),p.section('Cbig',.6,.6),p.section('B1',.3,.6),p.section('Btop',.25,.5)]
 for e in m['elements']:
  j=int(e['id'].split('-')[-1])
  if e['type']=='column' and j<=2:e['section']='Cbig'
  if e['type']=='beam' and j==4:e['section']='Btop'
 p.beams_udl(m,10)
 out.append(spec(77,m,'Four-storey frame with a missing second-floor beam',[rq('n2-4','ux','顶层右节点Ux'),mq(m,'c1-2','M2','第二层中柱下端M2'),mq(m,'c1-2','M2','第二层中柱上端M2',True)],decisions=['Source middle-column moment expanded to both ends of the second-storey member.']))
 # 078: each independent lateral case and all three explicit combinations.
 m=concrete(p.frame([0,6],[3.3,6.6,9.9],True));m['sections'].append(p.section('BC',.25,.5));p.node(m,'tip',7,9.9);p.elem(m,'cant','n1-3','tip',sec='BC')
 for eid,q in [('b0-1',10),('b0-2',8),('b0-3',6),('cant',4)]:p.load(m,type='distributed',element=eid,wz=-q)
 p.load(m,'W+',type='nodal',node='tip',fx=20);p.load(m,'W-',type='nodal',node='tip',fx=-20)
 m['load_combinations']=[{'id':'D','factors':{'D':1}},{'id':'D+W+','factors':{'D':1,'W+':1}},{'id':'D+W-','factors':{'D':1,'W-':1}}]
 req=[]
 for co in m['load_combinations']:
  sel={'kind':'combination','id':co['id']};req += [rq('tip',c,f"{co['id']}: free tip {c}",sel) for c in ('ux','uz')];req.append(mq(m,'c1-1','M2',f"{co['id']}: right base column at bottom M2",selection=sel))
 out.append(spec(78,m,'Concrete frame with reversed tip lateral forces',req))
 # 099: elastic kinked column, distinct lower and inclined upper sections.
 m=p.model();p.node(m,'base',0,0,restraint=[True]*6);p.node(m,'kink',0,3);p.node(m,'top',1,8);p.elem(m,'lower','base','kink','column','C1');p.elem(m,'upper','kink','top','column','C2');p.load(m,type='nodal',node='top',fx=20,fz=-300)
 out.append(spec(99,m,'Kinked column with an inclined upper segment',[rq('top','ux','柱顶Ux'),rq('top','uz','柱顶Uz'),mq(m,'lower','M2','折点下侧截面M2',True),mq(m,'upper','M2','折点上侧截面M2')],['折点为刚接真实连接；斜段局部x沿杆由kink指向top，局部y为全局+Y。'],['Kink moment requested on both incident member sides to preserve sign mapping.']))
 # 100: two orthogonal elastic arms; forces stay on different free ends.
 m=p.model('3d');p.node(m,'base',0,0,0,[True]*6);p.node(m,'top',0,5);p.node(m,'tipX',2,5);p.node(m,'tipY',0,5,-1.5)
 p.elem(m,'column','base','top','column','C1');p.elem(m,'armX','top','tipX');p.elem(m,'armY','top','tipY',sec='B2');p.load(m,type='nodal',node='tipX',fz=-200);p.load(m,type='nodal',node='tipY',fx=10,fz=-100)
 out.append(spec(100,m,'Spatial bracket with two orthogonal elastic arms',[rq('tipX','uz','X-arm free end: Uz'),rq('tipY','uz','Y-arm free end: Uz')]+[rq('base',c,'Column-base support reaction '+c) for c in ('Mx','My','Mz')],['Both arms use their actual elastic sections. The applied end forces stay at their own labelled free joints.']))
 return out
if __name__=='__main__':export_specs(build_specs())
