"""Explicit source-row specifications for MM-001..020; no reference answers."""
import importlib.util
from pathlib import Path
import math

_s=importlib.util.spec_from_file_location('mm_a_primitives',Path(__file__).resolve().parents[1]/'representative-models.py')
p=importlib.util.module_from_spec(_s);_s.loader.exec_module(p)
FREE=[False,True,False,True,False,True]
PIN=[True,True,True,True,False,True]
ROLL=[False,True,True,True,False,True]
FIX=[True]*6

def beam(points,supports,sections=None,materials=None):
    m=p.model();m['sections']=[p.section('B1',.3,.6),p.section('B2',.3,.7)]
    if materials and 'M2' in materials:
        m['materials'].append(dict(id='M2',name='Steel E180',type='steel',E=180000,G=180000/2.6,nu=.3,rho=7850))
    for i,point in enumerate(points):
        x,z=(point,0) if isinstance(point,(int,float)) else point
        p.node(m,f'n{i}',x,z,restraint=supports.get(i,FREE)[:])
    for i in range(len(points)-1):
        p.elem(m,f'b{i+1}',f'n{i}',f'n{i+1}',sec=(sections or ['B1']*(len(points)-1))[i])
        m['elements'][-1]['material']=(materials or ['M1']*(len(points)-1))[i]
    return m

def udl(m,ids,q,case='D'):
    for i in ids:p.load(m,case,type='distributed',element=f'b{i}',wz=q)

def point(m,n,case='D',**v):p.load(m,case,type='nodal',node=f'n{n}',**v)

def combos(m,rows):m['load_combinations']=[dict(id=k,factors=v) for k,v in rows]

def quantity(m,target,component,selection='D',combination=False):
    if isinstance(target,tuple):
        eid,which=target; e=next(e for e in m['elements'] if e['id']==eid)
        ns={n['id']:n for n in m['nodes']};a,b=[ns[n] for n in e['nodes']]
        L=math.dist([a[k] for k in 'xyz'],[b[k] for k in 'xyz'])
        loc=dict(kind='member',id=eid,positionM=0 if which=='start' else L,side='right' if which=='start' else 'left')
        suffix=f'{eid}-{which}'
    else:loc=dict(kind='node',id=f'n{target}');suffix=f'n{target}'
    unit='m' if component.startswith('u') else 'rad' if component.startswith('r') else 'kN.m' if component.startswith(('M','T')) else 'kN'
    return dict(id=f'{selection}-{suffix}-{component}',selection=dict(kind='combination' if combination else 'case',id=selection),location=loc,component=component,unit=unit,tolerance=dict(absolute=1e-8,relative=1e-6))

def pack(m,desc,req,selections=None):
    selections=selections or [('D',False)]
    qs=[quantity(m,target,component,s,c) for s,c in selections for target,component in req]
    return dict(model=m,outputs=[dict(description=desc,quantities=qs,derived=[],kind='numerical')],notes=['Unspecified property appendix frozen before candidate runs: steel M1 E=206000 MPa, nu=0.3, rho=7850 kg/m3; B1 solid 0.30 x 0.60 m, B2 solid 0.30 x 0.70 m; M2, where assigned, E=180000 MPa. Saint-Venant J stated explicitly.'],drawingNotes=[])

def build():
    out={}
    m=beam([0,3,6],{0:FIX,2:FIX});udl(m,[1,2],-20)
    out['MM-001']=pack(m,'x=3 m 节点竖向位移 Uz、左端截面弯矩 M2。',[(1,'uz'),(('b1','start'),'M2')])
    m=beam([0,3],{0:FIX});point(m,1,my=12)
    out['MM-002']=pack(m,'Free-end Uz and Ry; fixed-end section bending moment M2.',[(1,'uz'),(1,'ry'),(('b1','start'),'M2')])
    m=beam([0,1,6,8],{1:PIN,2:ROLL});udl(m,[2],-15);point(m,3,fz=-10)
    out['MM-003']=pack(m,'左右自由端 Uz；x=6 m 支座 Fz。',[(0,'uz'),(3,'uz'),(2,'Fz')])
    m=beam([0,3,4,6,8,12],{0:PIN,5:ROLL});udl(m,[1],-15);udl(m,[5],-9);point(m,2,fz=-50)
    out['MM-004']=pack(m,'Uz at x=6 m; V3 immediately left and right of x=4 m.',[(3,'uz'),(('b2','end'),'V3'),(('b3','start'),'V3')])
    m=beam([0,2,4],{0:FIX,2:ROLL});point(m,1,fz=-25)
    out['MM-005']=pack(m,'跨中 Uz、左端截面 M2、右支反力 Fz。',[(1,'uz'),(('b1','start'),'M2'),(2,'Fz')])
    m=beam([0,2,4,6,8],{0:PIN,4:ROLL})
    for n,f in [(1,-18),(2,-30),(3,-12)]:point(m,n,fz=f)
    out['MM-006']=pack(m,'Uz at x=2 m and x=4 m; left support Fz.',[(1,'uz'),(2,'uz'),(0,'Fz')])
    m=beam([(0,0),(3,1),(6,2)],{0:PIN,2:ROLL});point(m,1,fz=-15)
    out['MM-007']=pack(m,'补图后：几何中点 Ux、Uz，右支座 Fz。',[(1,'ux'),(1,'uz'),(2,'Fz')])
    m=beam([0,3,4.5,6,9],{0:PIN,4:ROLL});udl(m,[1],-12);udl(m,[4],-6)
    out['MM-008']=pack(m,'Uz at x=4.5 m; vertical reaction Fz at both supports.',[(2,'uz'),(0,'Fz'),(4,'Fz')])
    m=beam([0,2,5,7,10],{0:PIN,4:ROLL});point(m,1,fz=30);point(m,3,fz=-45);point(m,2,my=15)
    out['MM-009']=pack(m,'x=5 m 处 Uz 及该点左、右截面弯矩 M2。',[(2,'uz'),(('b2','end'),'M2'),(('b3','start'),'M2')])
    m=beam([0,2,4,6,8],{0:FIX,4:FIX},['B1','B2','B2','B1']);udl(m,[2,3],-8);udl(m,[1,4],-6,'L');combos(m,[('D',{'D':1}),('D+L',{'D':1,'L':1})])
    out['MM-010']=pack(m,'For each combination D and D+L: Uz at x=4 m and left-end section M2.',[(2,'uz'),(('b1','start'),'M2')],[('D',True),('D+L',True)])
    m=beam([0,4,7],{0:FIX,1:ROLL});udl(m,[1,2],-10);point(m,2,fz=-20)
    out['MM-011']=pack(m,'右端 Uz、x=4 m 支座 Fz、左端截面 M2。',[(2,'uz'),(1,'Fz'),(('b1','start'),'M2')])
    m=beam([(0,0),(4,0),(6,3)],{0:FIX});point(m,2,fz=-20)
    out['MM-012']=pack(m,'Free-end Ux and Uz; N, V3 and M2 at both sides of the rigid kink.',[(2,'ux'),(2,'uz')]+[(t,c) for t in [('b1','end'),('b2','start')] for c in ['N','V3','M2']])
    m=beam([0,3,4.5,6,9],{0:PIN,4:ROLL},materials=['M1','M2','M2','M1']);udl(m,[1,2,3,4],-12);point(m,1,fz=-20)
    out['MM-013']=pack(m,'x=4.5 m 处 Uz；x=3 m 两侧剪力 V3。',[(2,'uz'),(('b1','end'),'V3'),(('b2','start'),'V3')])
    m=beam([0,2,5,8,10],{0:PIN,4:ROLL},['B1','B1','B2','B2'],['M1','M2','M2','M1']);udl(m,[1,2],-9);point(m,3,my=25)
    out['MM-014']=pack(m,'Uz at x=5 m; section M2 immediately left and right of x=8 m.',[(2,'uz'),(('b3','end'),'M2'),(('b4','start'),'M2')])
    m=beam([0,2.5,5,8,11],{0:FIX,2:ROLL,4:ROLL});udl(m,[1,2,3,4],-12)
    out['MM-015']=pack(m,'x=2.5 m、8 m 处 Uz，左端截面 M2。',[(1,'uz'),(3,'uz'),(('b1','start'),'M2')])
    m=beam([0,4,7.5,11,13],{0:PIN,1:ROLL,3:ROLL});udl(m,[1,2,3],-10);udl(m,[4],-6);point(m,2,fz=-30)
    out['MM-016']=pack(m,'Uz at x=7.5 m and the free end; section M2 at x=11 m (both adjacent sides).',[(2,'uz'),(4,'uz'),(('b3','end'),'M2'),(('b4','start'),'M2')])
    m=beam([0,4,6.5,9,13],{0:PIN,1:ROLL,3:ROLL,4:FIX});udl(m,[1,2,3,4],-15)
    out['MM-017']=pack(m,'中跨中点 Uz、右端截面 M2。',[(2,'uz'),(('b4','end'),'M2')])
    m=beam([0,5,8.5,12,15],{0:PIN,1:ROLL,3:ROLL,4:ROLL});udl(m,[1],-16);udl(m,[4],-9)
    out['MM-018']=pack(m,'Middle-span midpoint Uz; section M2 at both internal supports, using the section on their left.',[(2,'uz'),(('b1','end'),'M2'),(('b3','end'),'M2')])
    m=beam([0,4,7,10,14],{0:PIN,1:ROLL,3:ROLL,4:ROLL});udl(m,[1,2,3,4],-8);udl(m,[2,3],-10,'L');udl(m,[1],4,'W');combos(m,[('D',{'D':1}),('D+L',{'D':1,'L':1}),('D+W',{'D':1,'W':1})])
    out['MM-019']=pack(m,'D、D+L、D+W 各组合：中跨中点 Uz，左支反力 Fz（保留正负号）。',[(2,'uz'),(0,'Fz')],[(x,True) for x in ['D','D+L','D+W']])
    m=beam([0,3,8,15,16],{0:PIN,1:ROLL,2:ROLL,3:ROLL});udl(m,[1],-8);udl(m,[2],-10);udl(m,[3],-12);point(m,4,fz=-8)
    out['MM-020']=pack(m,'Free-end Uz; section M2 at x=15 m (left and right).',[(4,'uz'),(('b3','end'),'M2'),(('b4','start'),'M2')])
    return out
