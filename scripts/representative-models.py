"""Explicit authoring appendix for the 18 candidate cases. Never imported by production.
These numerical properties complete the previously unspecified planning appendix;
they are case inputs, not solver defaults. Independent review is still required.
"""
from copy import deepcopy
import math


def section(name, b, h):
    # Solid rectangle, metres. Saint-Venant series approximation is frozen as explicit J.
    a, c = max(b, h), min(b, h)
    return dict(id=name, name=name, type='rectangular', shape=dict(kind='rectangular',B=b*1000,H=h*1000), properties=dict(A=b*h, Iy=b*h**3/12, Iz=h*b**3/12,
        J=a*c**3*(1/3-.21*c/a*(1-c**4/(12*a**4)))))


def model(dimension='2d', concrete=False):
    E, nu, rho = (31500, .2, 2500) if concrete else (206000, .3, 7850)
    return dict(schema_version='2.2.0', unit_system='SI', coordinate_system=dict(dimension=dimension,
        plane='xz' if dimension=='2d' else None, semantics='global-z-up', version=1,
        dof_order=['ux','uy','uz','rx','ry','rz']), nodes=[], elements=[],
        materials=[dict(id='M1', name='C35' if concrete else 'Q355', type='concrete' if concrete else 'steel', E=E, G=E/(2*(1+nu)), nu=nu, rho=rho)],
        sections=[section('B1',.3,.6),section('B2',.3,.7),section('C1',.5,.5),section('C2',.35,.5),section('A1',.1,.1)],
        load_cases=[dict(id='D',type='dead',loads=[])], load_combinations=[],
        analysis_control=dict(self_weight=False,rigid_floor=False,p_delta=False,rigid_offsets=False,construction_stage=False),
        metadata=dict(elementReferenceVectors={}) if dimension=='3d' else {})


def node(m, name, x, z, y=0, restraint=None):
    if restraint is None: restraint=[False,True,False,True,False,True] if m['coordinate_system']['dimension']=='2d' else [False]*6
    m['nodes'].append(dict(id=name,x=x,y=y,z=z,restraints=restraint)); return name


def elem(m, name, a, b, kind='beam', sec='B1'):
    m['elements'].append(dict(id=name,type=kind,nodes=[a,b],material='M1',section=sec))
    if m['coordinate_system']['dimension']=='3d':
        n={n['id']:n for n in m['nodes']}; u=n[a];v=n[b]
        # Reference plane vector: global +X for vertical columns, global +Z otherwise.
        ref=[1,0,0] if abs(v['x']-u['x'])+abs(v['y']-u['y'])<1e-10 else [0,0,1]
        m['metadata']['elementReferenceVectors'][name]=ref
    return name


def load(m, case='D', **values):
    c=next((c for c in m['load_cases'] if c['id']==case),None)
    if c is None: c=dict(id=case,type='live' if case.startswith('L') else 'wind' if case.startswith('W') else 'dead',loads=[]);m['load_cases'].append(c)
    c['loads'].append(dict(id=values.pop('id',f'{case}-{len(c["loads"])+1}'),reference_frame='global',**values))


def beam(lengths, fixed=False, sections=None):
    m=model();x=0
    for i in range(len(lengths)+1):
        node(m,f'n{i}',x,0,restraint=[True]*6 if i==0 and fixed else [i==0,True,True,True,False,True])
        if i<len(lengths):x+=lengths[i]
    for i,_ in enumerate(lengths):elem(m,f'b{i+1}',f'n{i}',f'n{i+1}',sec=(sections or ['B1']*len(lengths))[i])
    return m


def frame(xs, levels, concrete=False, lefts=None):
    m=model(concrete=concrete)
    for j,z in enumerate([0]+levels):
        for i,x in enumerate(xs):node(m,f'n{i}-{j}',lefts[j] if i==0 and lefts else x,z,restraint=[True]*6 if j==0 else None)
    for j in range(1,len(levels)+1):
        for i in range(len(xs)):elem(m,f'c{i}-{j}',f'n{i}-{j-1}',f'n{i}-{j}','column','C1')
        for i in range(len(xs)-1):elem(m,f'b{i}-{j}',f'n{i}-{j}',f'n{i+1}-{j}')
    return m


def spatial(xs,ys,levels,keep=None,shift=None,concrete=False):
    m=model('3d',concrete); floorids=[]
    for j,z in enumerate([0]+levels):
        for ix,x in enumerate(xs):
            for iy,y in enumerate(ys):
                if keep and not keep(ix,iy,j):continue
                xx,yy=shift(ix,iy,j,x,y) if shift else (x,y)
                node(m,f'n{ix}-{iy}-{j}',xx,z,yy,[True]*6 if j==0 else None)
    ids={n['id'] for n in m['nodes']}
    for j,z in enumerate(levels,1):
        members=[]
        for ix in range(len(xs)):
            for iy in range(len(ys)):
                a=f'n{ix}-{iy}-{j}'
                if a not in ids:continue
                lower=f'n{ix}-{iy}-{j-1}'
                if lower in ids:members.append(elem(m,f'c{ix}-{iy}-{j}',lower,a,'column','C1'))
                for axis,b in [('x',f'n{ix+1}-{iy}-{j}'),('y',f'n{ix}-{iy+1}-{j}')]:
                    if b in ids:members.append(elem(m,f'{axis}{ix}-{iy}-{j}',a,b,sec='B1' if axis=='x' else 'B2'))
        floorids.append(dict(id=f's{j}',elevation=levels[j-2] if j>1 else 0,height=z-(levels[j-2] if j>1 else 0),rigid_diaphragm=False))
    m['stories']=floorids
    return m


def beams_udl(m,q,case='D',only_x=False):
    for e in m['elements']:
        if e['type']=='beam' and (not only_x or e['id'].startswith('x')):load(m,case,type='distributed',element=e['id'],wz=-q)


def states():
    out={}
    m=beam([9]);load(m,type='distributed',element='b1',start=2,end=7,wz=-12,id='q');out['STD-008']=[m]
    m=beam([4,6,5,4],sections=['B1','B2','B2','B1']);beams_udl(m,8)
    for b in ['b2','b4']:load(m,'L',type='distributed',element=b,wz=-10)
    m['load_combinations']=[dict(id='C0',factors={'D':1}),dict(id='C1',factors={'D':1.2,'L':1.4})];out['STD-026']=[m]
    m=model()
    for i in range(5):
        for top in [0,1]:node(m,f'n{i}-{top}',3*i,2.5*top,restraint=[i==0,True,True,True,False,True] if top==0 and i in [0,4] else None)
    for i in range(5):elem(m,f'v{i}',f'n{i}-0',f'n{i}-1','truss','A1')
    for i in range(4):
        for top in [0,1]:elem(m,f'h{i}-{top}',f'n{i}-{top}',f'n{i+1}-{top}','truss','A1')
        elem(m,f'd{i}-up',f'n{i}-0',f'n{i+1}-1','truss','A1');elem(m,f'd{i}-down',f'n{i}-1',f'n{i+1}-0','truss','A1')
    for i in range(1,4):load(m,type='nodal',node=f'n{i}-1',fz=-10)
    out['STD-036']=[m]
    m=frame([0,6],[3.6,7.2]);beams_udl(m,10);load(m,type='nodal',node='n1-2',fx=30)
    elem(m,'brace1','n0-0','n1-1','truss','A1');elem(m,'brace2','n1-0','n0-1','truss','A1');out['STD-063']=[m]
    m=spatial([0,6,12],[0,5,10],[3.6,7.2],keep=lambda x,y,j:not(x==2 and y==2));beams_udl(m,8);out['STD-086']=[m]
    m=spatial([0,6,12],[0,5],[3.6,7.2]);beams_udl(m,8)
    for j in [1,2]:load(m,'Wx',type='nodal',node=f'n2-1-{j}',fx=10*j);load(m,'Wy',type='nodal',node=f'n2-1-{j}',fy=8*j)
    m['load_combinations']=[dict(id='C0',factors={'D':1}),dict(id='CX',factors={'D':1,'Wx':1}),dict(id='CY',factors={'D':1,'Wy':1})];out['STD-088']=[m]
    m=beam([6]);beams_udl(m,20);load(m,type='point',element='b1',position=1.5,fz=-12,id='near');b=deepcopy(m);load(b,type='point',element='b1',position=3,fz=-30,id='added');out['INT-001']=[m,b,deepcopy(m)]
    m=beam([9],True);load(m,type='distributed',element='b1',start=2,end=7,wz=-12,id='q');b=deepcopy(m);b['load_cases'][0]['loads'][0].update(start=3,end=8);out['INT-008']=[m,b]
    m=beam([4,6,4]);beams_udl(m,8);load(m,type='point',element='b2',position=3,fz=-20,id='constant-point');load(m,'L1',type='distributed',element='b2',wz=-10)
    for e in ['b1','b3']:load(m,'L2',type='distributed',element=e,wz=-10)
    m['load_combinations']=[dict(id='C1',factors={'D':1}),dict(id='C2',factors={'D':1,'L1':1}),dict(id='C3',factors={'D':1,'L2':1})];b=deepcopy(m);b['load_combinations'][1]['factors']['L1']=1.4;c=deepcopy(b);c['load_combinations'][1]['factors']['D']=1.2;out['INT-019']=[m,b,c]
    m=frame([0,7],[3.6,7.2],True);m['sections']=[section('B1',.3,.6),section('C1',.5,.35),section('C2',.35,.5)]
    for e in m['elements']:
        if e['id'].startswith('c1-'):e['section']='C2'
    beams_udl(m,10);load(m,type='nodal',node='n1-2',fx=20,my=12);b=deepcopy(m)
    # A 90-degree roll swaps principal stiffness in a planar equivalent; preserve explicit operation.
    for e in b['elements']:
        if e['id'].startswith('c0-'):e['rotation_angle']=90
    out['INT-074']=[m,b,deepcopy(m)]
    m=spatial([0,6],[0,5],[3.6,7.2]);m['nodes'][0]['restraints']=[True]*3+[False]*3;beams_udl(m,25,only_x=True);out['INT-079']=[m]
    m=spatial([0,6,12],[0,5],[3.6,7.2],concrete=True);m['materials'][0].update(name='C30',E=30000,G=12500)
    for e in m['elements']:
        if e['id'].startswith('x'):load(m,type='distributed',element=e['id'],wz=-30 if e['id'].endswith('-1') else -25)
    load(m,'D_eq',type='nodal',node='n1-1-2',fz=-30,id='equipment');m['load_combinations']=[dict(id='TOTAL',factors={'D':1,'D_eq':1})];b=deepcopy(m);b['materials'][0].update(name='C35',E=31500,G=13125);out['INT-084']=[m,b]
    m=beam([12]);load(m,type='distributed',element='b1',start=0,end=3,wz=-15,id='q1');load(m,type='distributed',element='b1',start=8,end=12,wz=-9,id='q2');load(m,type='point',element='b1',position=4,fz=-50,id='point');out['MM-004']=[m]
    m=frame([0,6],[4]);node(m,'tip',8,4);elem(m,'overhang','n1-1','tip');beams_udl(m,8);load(m,type='nodal',node='tip',fx=50);out['MM-058']=[m]
    m=frame([0,6],[3.3,6.6,9.9],True,lefts=[0,0,1,1]);beams_udl(m,60);out['MM-070']=[m]
    m=spatial([0,6],[0,5,10],[3.3,6.6,9.9],keep=lambda x,y,j:j<3 or y<2)
    for e in m['elements']:
        if e['id'].startswith('x'):
            j=int(e['id'].split('-')[-1]);iy=int(e['id'].split('-')[1]);q=50 if j<3 and iy==1 else 25;load(m,type='distributed',element=e['id'],wz=-q)
    out['MM-081']=[m]
    m=spatial([0,4,11],[0,3,9],[3.4,7.5],shift=lambda ix,iy,j,x,y:(1,1) if j==2 and ix==iy==0 else (x,y))
    for e in m['elements']:
        if e['type']=='beam':e['section']='B1'
    beams_udl(m,8);load(m,type='nodal',node='n0-0-2',fx=10);out['MM-085']=[m]
    m=model('3d');node(m,'base',0,0,0,[True]*6);node(m,'top',0,5);node(m,'tipX',2,5);node(m,'tipY',0,5,-1.5)
    elem(m,'column','base','top','column','C1');elem(m,'armX','top','tipX');elem(m,'armY','top','tipY',sec='B2');load(m,type='nodal',node='tipX',fz=-200);load(m,type='nodal',node='tipY',fx=10,fz=-100);out['MM-100']=[m]
    return out
