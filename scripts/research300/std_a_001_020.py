"""Explicit source-specific beam specifications for STD-001 through STD-020.

Source geometry, supports, load locations and requests are transcribed individually;
the builder only joins shared physical stations and distributes specified line loads.
"""
from copy import deepcopy
from std_a_core import emit, primitives as p, qnode, qmember, length


# x positions in metres; load intervals in metres; forces kN, moments kN.m.
SPECS = {
1: dict(xs=[0,3,6], supports={0:'pin',6:'roller'}, udl=[('D',0,6,-20)], disp=[3], moments=[3], prompt='建立6m简支梁：左端铰支、右端竖向滚支，全长向下20kN/m。x=3m为两梁段共享的连通观测节点。报告左右支反力、跨中Z位移及跨中截面弯矩。'),
2: dict(xs=[0,3], supports={0:'fixed'}, point=[(3,0,-10,0)], disp=[3], rotations=[3], prompt='Analyze a 3 m horizontal cantilever fixed at its left end. Apply only a downward 10 kN force at the right free end, whose rotation is free. Report the free-end Z displacement and global Y rotation, and the fixed-end reaction forces and Y moment.'),
3: dict(xs=[0,3.25,5,6.5], supports={0:'pin',5:'roller'}, udl=[('D',0,6.5,-15)], disp=[3.25,6.5], moments=[5], prompt='梁左端x=0m铰支，x=5m竖向滚支，梁延伸至x=6.5m自由端；全长向下15kN/m。x=3.25m是全长中点，5m支承跨的跨中为x=2.5m。报告x=3.25及6.5m的Z位移、两支座反力及右支座x=5m截面两侧弯矩。'),
4: dict(xs=[0,4,6,12], supports={0:'pin',12:'roller'}, udl=[('D',0,12,-15)], point=[(4,0,-50,0)], disp=[4,6], moments=[4], prompt='Analyze a 12 m horizontal beam with a left pin and right vertical roller. Apply 15 kN/m downward over its full length and a downward 50 kN point load at x=4 m. The load joint at x=4 m and observation joint at x=6 m are separate connected joints. Report both support reactions, Z displacements at x=4 and 6 m, and the bending moment on both sides of x=4 m.'),
5: dict(xs=[0,2,4], supports={0:'pin',4:'roller'}, point=[(2,0,-25,0)], disp=[2], moments=[2], prompt='建立4m简支梁，左铰右竖向滚支；唯一外荷载为跨中x=2m向下25kN集中力。两梁段在力点共享同一节点。报告跨中Z位移、弯矩及左右竖向支反力。'),
6: dict(xs=[0,4,8], supports={0:'pin',8:'roller'}, udl=[('D',0,8,-18)], point=[(8,0,0,20)], disp=[4], rotations=[8], moments=[4], prompt='Prepare a one-page calculation summary for an 8 m horizontal simply supported beam, with a left pin and right vertical roller. Apply 18 kN/m downward along the entire beam and a +20 kN.m moment about global Y at the right end. Keep the right-end Y rotation free. Report midpoint Z displacement and bending moment, right-end Y rotation and both support reactions. The summary and structured table must agree in sign, units, position and load selection.', extra='Provide the one-page calculation summary and check its signed values against the result table.'),
7: dict(xs=[0,4,8], supports={0:'pin',8:'roller'}, udl=[('D',0,8,-15)], point=[(8,10,0,0)], disp=[4], axial_disp=[8], moments=[4], mixed_units=True, prompt='The horizontal beam is 8000 mm long. Its left end is pinned and its right end is a vertical roller with X translation free. Apply 15 N/mm downward along the full length and +10000 N in global X at the right end. Input section areas are in mm2, second moments and torsion constants in mm4, E and G in MPa. Report right-end X displacement and midpoint Z displacement in mm, midpoint bending moment in kN.m, and both support reaction vectors in kN (moments in kN.m). Include a unit-conversion record for geometry, loads and section properties.', extra='Record conversions mm to m, N to kN, N/mm to kN/m, mm2 to m2, mm4 to m4, and output displacement m to mm.'),
8: dict(xs=[0,2,4.5,7,9], supports={0:'pin',9:'roller'}, udl=[('D',2,7,-12)], disp=[2,4.5,7], moments=[2,7], prompt='9m梁左铰右竖向滚支，仅x=2至7m向下12kN/m，两端无载段保持完整。x=2、4.5、7m均为连通观测节点。报告两支反力、三处Z位移，以及加载区间两端x=2、7m截面弯矩。'),
9: dict(xs=[0,2,7,10], supports={0:'pin',10:'roller'}, point=[(2,0,-30,0),(7,0,-45,0)], disp=[2,7], moments=[2,7], prompt='10m简支梁左铰右竖向滚支；x=2m的N1节点向下30kN，x=7m的N2节点向下45kN。其余节点无外荷载，无均布载。报告两支反力、两个力点Z位移及各力点两侧截面弯矩。'),
10: dict(xs=[0,4,8], supports={0:'fixed',8:'fixed'}, udl=[('D',0,8,-8),('L',0,4,-6)], disp=[4], combinations=[('D+L',{'D':1,'L':1})], selections=[('case','D'),('case','L'),('combination','D+L')], prompt='Analyze an 8 m beam fixed at both ends. Case D is a full-span downward 8 kN/m load; independent case L is a downward 6 kN/m load only on the left half. The connected midpoint x=4 m is the live-load boundary. Analyze D, L and the explicit combination D+L separately. For each selection report both fixed-end reaction forces and Y moments, and midpoint Z displacement. Compare the combination results with the sum of the two separate cases.', extra='Compare the D+L result with signed superposition of the separate D and L results at every requested position.'),
11: dict(xs=[0,3.5,5,7], supports={0:'fixed',7:'roller'}, udl=[('D',0,7,-10)], point=[(5,0,-20,0)], disp=[3.5,5], prompt='7m梁左端固支、右端仅竖向滚支，全长向下10kN/m，x=5m连通节点另施加向下20kN。右端X平移和Y转角自由。报告左固端反力与弯矩、右支座竖向反力，以及x=5m和跨中x=3.5m的Z位移。'),
12: dict(xs=[0,3,6], zs=[0,1.5,3], supports={0:'fixed'}, point=[(3,0,-20,0)], disp=[3,6], axial_disp=[3,6], axial_forces=True, prompt='Analyze the inclined straight cantilever from (X,Z)=(0,0) to (6,3) m, fixed at the left endpoint. Apply a downward global Z force of 20 kN at horizontal projection x=3 m, the connected midpoint (3,1.5) m. The right endpoint is free. Report global X and Z displacements at the load point and free end, fixed-end reaction forces and Y moment, and signed local axial force in both member segments. Distinguish global vertical loading from local transverse and axial components.'),
13: dict(xs=[0,3,4.5,6,9], supports={0:'pin',9:'roller'}, udl=[('D',0,9,-12)], disp=[3,4.5,6], moments=[3,6], section_intervals=[(0,3,'B1'),(3,6,'B2'),(6,9,'B3')], prompt='9m简支梁左铰右竖向滚支，向下12kN/m全跨加载。0至3m为B1，3至6m为B2，6至9m为B3；各截面A/I/J见属性表。x=3、6m为材料相同、截面改变的共享节点，x=4.5m为连通观测点。报告跨中和两个截面分界的Z位移、两支反力及分界截面两侧弯矩。'),
14: dict(xs=[0,2,4,6,8,10], supports={0:'pin',10:'roller'}, udl=[('D',2,8,-9)], point=[(6,0,-25,0)], disp=[4,6], moments=[6], two_materials=True, prompt='Analyze a 10 m simply supported beam with a left pin and right vertical roller. Material M1 applies over x=0 to 4 m and M2 over x=4 to 10 m; the section is B1 throughout. Apply 9 kN/m downward only from x=2 to 8 m and a downward 25 kN force at x=6 m. Use shared joints at the material interface and all load boundaries. Report Z displacement at x=4 and 6 m, both support reactions, bending moment on both sides of the point load, and the element-to-material assignment table.', extra='Provide the element-to-material assignment table, identifying the shared interface at x=4 m.'),
15: dict(xs=[0,2.5,5,8,11], supports={0:'pin',5:'roller',11:'roller'}, udl=[('D',0,11,-12)], disp=[2.5,8], moments=[5], prompt='双跨连续梁支座x=0、5、11m，左端铰支，其余竖向滚支；全梁向下12kN/m。中支座仅约束竖向位移，两侧梁共享节点和转角，无内铰。报告三支反力、x=2.5、8m的跨中Z位移以及中支座两侧截面弯矩。'),
16: dict(xs=[0,2,4,7.5,11], supports={0:'pin',4:'roller',11:'roller'}, udl=[('D',0,11,-10)], point=[(7.5,0,-30,0)], disp=[2,7.5], moments=[4], prompt='Analyze a continuous two-span beam with spans 4 m and 7 m. Use a left pin and vertical rollers at x=4 and 11 m, retaining continuity at the middle support. Apply 10 kN/m downward over both spans and a downward 30 kN force at the longer span midpoint, global x=7.5 m. Report all three support reactions, Z displacements at x=2 and 7.5 m, and the middle-support bending moment on both sides.'),
17: dict(xs=[0,2,4,6.5,9,11,13], supports={0:'pin',4:'roller',9:'roller',13:'roller'}, udl=[('D',0,13,-15)], disp=[2,6.5,11], moments=[4,9], prompt='三跨连续梁支座位于x=0、4、9、13m；左铰，其余竖向滚支。全长向下15kN/m，每个支座处转角连续。报告四支反力、各跨中x=2、6.5、11m的Z位移以及两个中支座的两侧截面弯矩。'),
18: dict(xs=[0,2.5,5,8.5,12], supports={0:'pin',5:'roller',12:'roller'}, udl=[('D',0,5,-16)], disp=[2.5,8.5], moments=[5], prompt='Analyze a continuous beam with 5 m and 7 m spans, a left pin and vertical rollers at x=5 and 12 m. Apply 16 kN/m downward only to the first span. Keep all members and restraints of the unloaded second span. Report all three support reactions, midpoint Z displacements at x=2.5 and 8.5 m, and the middle-support bending moment. Explain the response of the span without external loading.', extra='Explain the signed response in the second span, which has no external applied load but remains continuous with the loaded span.'),
19: dict(xs=[0,2,4,7,10,12,14], supports={0:'pin',4:'roller',10:'roller',14:'roller'}, udl=[('D',0,14,-8),('L1',4,10,-10),('L2',0,4,-10),('L2',10,14,-10)], disp=[2,7,12], moments=[4,10], combinations=[('C0',{'D':1}),('C1',{'D':1,'L1':1}),('C2',{'D':1,'L2':1})], selections=[('combination','C0'),('combination','C1'),('combination','C2')], governing=True, prompt='三跨连续梁跨度4、6、4m，支座x=0、4、10、14m，左铰其余竖向滚支。D为全梁向下8kN/m；独立工况L1仅中跨向下10kN/m，L2仅两边跨向下10kN/m。仅使用C0=D、C1=D+L1、C2=D+L2，不自动加入规范系数。每组合报告四支反力、三跨中Z位移及两个中支座弯矩；逐位置逐分量比较三个组合的绝对值最大值，保留带符号结果和控制组合标识。绝对值相等时，按C0、C1、C2顺序选取首个控制组合。'),
20: dict(xs=[0,1.5,3,5.5,8,11.5,15], supports={0:'pin',3:'roller',8:'roller',15:'roller'}, udl=[('D',0,3,-8),('D',3,8,-10),('D',8,15,-12)], disp=[1.5,5.5,11.5], moments=[3,8], prompt='Analyze a continuous three-span beam with spans 3, 5 and 7 m in that order. Supports are at x=0, 3, 8 and 15 m: a left pin and three vertical rollers. Apply downward line loads of 8, 10 and 12 kN/m respectively to the first, second and third spans. Report all four support reactions, the three midpoint Z displacements, the two interior-support bending moments, and a span-by-span load table preserving the given order.', extra='Provide a span-by-span table with span index, endpoints, length and signed downward line load.'),
}


def build(number):
    s = SPECS[number]
    m = p.model()
    m['sections'] = [p.section('B1',.3,.6),p.section('B2',.3,.7),p.section('B3',.25,.5)]
    if s.get('two_materials'):
        mat = deepcopy(m['materials'][0]); mat.update(id='M2',name='Elastic-steel-M2',E=180000,G=180000/2.6)
        m['materials'].append(mat)
    node_at = {}
    for i,(x,z) in enumerate(zip(s['xs'],s.get('zs',[0]*len(s['xs'])))):
        support=s['supports'].get(x)
        r={'fixed':[True]*6,'pin':[True,True,True,True,False,True],'roller':[False,True,True,True,False,True]}.get(support)
        node_at[x]=p.node(m,f'N{i}',x,z,restraint=r)
    for i,(a,b) in enumerate(zip(s['xs'],s['xs'][1:])):
        section=next((v for lo,hi,v in s.get('section_intervals',[]) if lo<=(a+b)/2<=hi),'B1')
        name=p.elem(m,f'E{i+1:02}',node_at[a],node_at[b],sec=section)
        if s.get('two_materials') and a>=4: m['elements'][-1]['material']='M2'
        for case,lo,hi,wz in s.get('udl',[]):
            if lo <= a and b <= hi:
                p.load(m,case,type='distributed',element=name,start=0,end=length(m,name),wz=wz)
    for x,fx,fz,my in s.get('point',[]):
        p.load(m,type='nodal',node=node_at[x],fx=fx,fz=fz,my=my)
    m['load_combinations']=[dict(id=name,factors=factors) for name,factors in s.get('combinations',[])]
    qs=[]
    unit='mm' if s.get('mixed_units') else 'm'
    for kind,case in s.get('selections',[('case','D')]):
        selection=dict(kind=kind,id=case)
        for x, support in s['supports'].items():
            comps=['Fx','Fy','Fz','Mx','My','Mz'] if s.get('mixed_units') else ['Fx','Fz','My'] if support=='fixed' else ['Fx','Fz']
            qs += [qnode(m,node_at[x],c,selection) for c in comps]
        for x in s.get('disp',[]): qs.append(qnode(m,node_at[x],'uz',selection,unit))
        for x in s.get('axial_disp',[]): qs.append(qnode(m,node_at[x],'ux',selection,unit))
        for x in s.get('rotations',[]): qs.append(qnode(m,node_at[x],'ry',selection))
        for x in s.get('moments',[]):
            for e in m['elements']:
                if e['nodes'][1]==node_at[x]:qs.append(qmember(m,e['id'],length(m,e['id']),'M2',selection,side='left'))
                if e['nodes'][0]==node_at[x]:qs.append(qmember(m,e['id'],0,'M2',selection,side='right'))
        if s.get('axial_forces'):
            for e in m['elements']:
                for pos,side in [(0,'right'),(length(m,e['id']),'left')]: qs.append(qmember(m,e['id'],pos,'N',selection,side=side))
    derived=[]
    if s.get('governing'):
        groups={}
        for q in qs: groups.setdefault(q['id'].split(':',2)[2],[]).append(q)
        for key,values in groups.items():
            derived.append(dict(id='governing:'+key,operation='max_abs',operands=[v['id'] for v in values],unit=values[0]['unit'],description=f'{key} 三个组合中绝对值最大的带符号值及控制组合；绝对值相等时按C0、C1、C2顺序取首个。'))
    extras=[dict(id='source-report-requirement',description=s['extra'],quantityIds=[q['id'] for q in qs],kind='interaction')] if s.get('extra') else []
    notes=[
        'Read exact source row and compared geometry, boundary, loads, observation stations, expected outputs and engine requirements. All source requirements are retained in contract.sourcePlan; independent input-blind review remains pending.',
        'The planning row leaves the numerical material/section appendix unspecified. Frozen author appendix: M1 elastic steel E=206000 MPa, nu=.3, G=E/[2(1+nu)], rho=7850 kg/m3; solid B1=.3 by .6 m. No strength design is requested. Self-weight is OFF.',
        'Beam subdivisions share nodes and rotations at supports, load points, section/material interfaces and observation stations. Rollers are bilateral vertical restraints with X and Y rotation free. No member end releases.',
    ]
    if number==13: notes.append('B2=.3 by .7 m; B3=.25 by .5 m. Areas, both principal moments and J are explicitly tabulated; source provides section groups but no dimensions.')
    if number==14: notes.append('M2 is an explicitly defined elastic material with E=180000 MPa, nu=.3, G=E/2.6 and rho=7850 kg/m3. Its grade is intentionally not asserted; source gives two groups without constants. Uniform B1 section across the material interface.')
    if number==7: notes.append('Only public input uses mm/N/mm2/mm4. Hidden model is canonical m/kN/m2/m4. Displacement requests use mm as required; reference worker must convert numerical units before scoring.')
    if number==19: notes.append('Source does not state which response governs. Frozen interpretation compares each explicitly requested response across C0/C1/C2 with max_abs retaining its sign and selection; exact ties select the first operand in C0/C1/C2 order, matching the derived-request convention.')
    emit(number,m,s['prompt'],qs,derived=derived,extra_outputs=extras,notes=notes,mixed_units=s.get('mixed_units',False))


def check_analytical():
    """Independent beam identities; diagnoses sign, units and load mapping bugs."""
    import json
    import math
    from std_a_core import ROOT
    from std_a_041_050 import check_model
    checked=[]
    for number in (1,2,4,5,6,7,10,12):
        folder=ROOT/'corpora/research-300/cases'/f'STD-{number:03}'
        m=json.loads((folder/'model-state-1.json').read_text())
        value,_=check_model(m,with_values=True)
        ns={n['x']:n['id'] for n in m['nodes']}
        E=m['materials'][0]['E']*1000
        A=m['sections'][0]['properties']['A'];I=m['sections'][0]['properties']['Iy']
        def eq(x,component,target):
            actual=value(dict(kind='node',id=ns[x]),component)
            assert math.isclose(actual,target,rel_tol=1e-9,abs_tol=1e-10),(number,x,component,actual,target)
        if number==1:
            eq(0,'Fz',60);eq(6,'Fz',60);eq(3,'uz',-5*20*6**4/(384*E*I))
        if number==2:
            eq(0,'Fz',10);eq(0,'My',-30);eq(3,'uz',-10*3**3/(3*E*I));eq(3,'ry',10*3**2/(2*E*I))
        if number==4:
            eq(0,'Fz',370/3);eq(12,'Fz',320/3)
        if number==5:
            eq(0,'Fz',12.5);eq(4,'Fz',12.5);eq(2,'uz',-25*4**3/(48*E*I))
        if number==6:
            eq(0,'Fz',69.5);eq(8,'Fz',74.5)
        if number==7:
            eq(8,'ux',10*8/(E*A));eq(4,'uz',-5*15*8**4/(384*E*I));eq(0,'Fx',-10)
            public=json.loads((folder/'geometry.json').read_text());assert public['nodes'][-1]['x']==8000
            assert all(q['unit']=='mm' for q in json.loads((folder/'reference-requests.json').read_text())['states'][0]['quantities'] if q['component'].startswith('u'))
        if number==10:
            d,_=check_model(m,{'D':1},with_values=True);l,_=check_model(m,{'L':1},with_values=True)
            both,_=check_model(m,{'D':1,'L':1},with_values=True)
            for x,component in [(0,'Fz'),(0,'My'),(8,'Fz'),(8,'My'),(4,'uz')]:
                loc=dict(kind='node',id=ns[x]);assert math.isclose(both(loc,component),d(loc,component)+l(loc,component),rel_tol=1e-10,abs_tol=1e-10)
        if number==12:
            eq(0,'Fz',20);eq(0,'My',-60);eq(0,'Fx',0)
            # The vertical load has an axial component along the inclined beam.
            assert abs(value(dict(kind='member',id='E01',positionM=0,side='right'),'N'))>1
            assert abs(value(dict(kind='member',id='E02',positionM=0,side='right'),'N'))<1e-9
        checked.append(f'STD-{number:03}')
    print('Analytical/source-unit checks passed: '+', '.join(checked))


if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--start',type=int,default=1);ap.add_argument('--end',type=int,default=20);ap.add_argument('--check',action='store_true')
    args=ap.parse_args()
    if args.check:check_analytical()
    else:
        for number in range(args.start,args.end+1):build(number)
        print(f'Authored STD-{args.start:03} through STD-{args.end:03}; references and acceptance pending.')
