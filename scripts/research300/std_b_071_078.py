"""Source-faithful, explicit concrete-frame candidates STD-071 through STD-078.

Only writes this shard's candidate files. No solver, numerical truth, native
acceptance, legacy mutation, production imports or network access.
"""
from std_b_common import (
    Requests, beams_udl, elem, emit, frame, load, model, node, section, source,
)


def concrete_material(name='C30'):
    elastic = {'C30': 30000, 'C40': 32500}[name]
    return dict(id=name, name=name, type='concrete', E=elastic,
                G=elastic / 2.4, nu=0.2, rho=2500)


def concrete_frame(xs, levels):
    m = frame(xs, levels, concrete=True)
    m['materials'] = [concrete_material()]
    m['sections'] = [section('B1', .3, .6), section('C1', .5, .5)]
    for e in m['elements']:
        e['material'] = 'C30'
    return m


def floor_nodes(m):
    return [n['id'] for n in m['nodes'] if n['z'] > 0 and n['id'].startswith('n')]


def request_floors(r, components=('ux', 'uz', 'ry'), selection='D'):
    for nid in floor_nodes(r.model):
        r.node(nid, components, selection)


def request_drifts(r, selection='D'):
    """Only real columns define a story pair, including setback edge columns."""
    for e in r.model['elements']:
        if e['type'] == 'column':
            r.drift(e['nodes'][0], e['nodes'][1], ('ux',), selection)


def request_ends(r, kind=None, selection='D', components=('N', 'V3', 'M2')):
    for e in r.model['elements']:
        if kind is None or e['type'] == kind:
            r.ends(e['id'], components, selection)


def beam_midpoint(m, eid):
    """A connected, unreleased, mass-free observation node; no load duplication."""
    e = next(e for e in m['elements'] if e['id'] == eid)
    ns = {n['id']: n for n in m['nodes']}
    a, b = [ns[n] for n in e['nodes']]
    mid = 'mid-' + eid
    node(m, mid, (a['x'] + b['x']) / 2, (a['z'] + b['z']) / 2)
    i = m['elements'].index(e)
    left = dict(e, id=eid + '-a', nodes=[e['nodes'][0], mid])
    right = dict(e, id=eid + '-b', nodes=[mid, e['nodes'][1]])
    m['elements'][i:i + 1] = [left, right]
    m.setdefault('metadata', {}).setdefault('physicalBeams', {})[eid] = dict(
        nodes=e['nodes'], segments=[left['id'], right['id']], midpointNode=mid,
        joint='continuous-rigid', addedMass=0,
    )
    return mid


def case_071():
    m = concrete_frame([0, 6, 12], [3.6, 7.2])
    beams_udl(m, 10)
    r = Requests(m)
    request_floors(r)
    request_ends(r)
    r.supports()
    emit(71, m,
         '建立两层两跨平面混凝土框架：两跨各6m，两层各3.6m，三个柱脚均固定。'
         '柱C1为500×500mm，梁B1为300×600mm；全部为C30，E=30000MPa、ν=0.2、'
         'G=12500MPa、ρ=2500kg/m³。每层两根梁均承受全跨向下10kN/m线载，工况D。'
         '仅对初始C30模型作一次OpenSees一阶线弹性Euler-Bernoulli分析，自重关闭。'
         '输出两层三个柱线节点的ux、uz、ry，所有梁柱两端N、V3、M2，以及三个柱脚Fx、Fz、My；'
         '全部保留工况、位置、局部轴符号和单位。后续C40材料更新不属于本题。', r,
         notes=[
             'The archived first turn was inspected read-only: C30 E=30000 MPa, nu=0.2, rho=2500 kg/m3 and the stated 500x500/300x600 mm sections are retained.',
             'The new plan specifies one initial C30 analysis and forbids undeclared default combinations; requests select case D directly, without importing the old ULS alias or C40 update.',
             'Representative member end-force positions are made unambiguous by requesting every physical beam and column end. Supports are all fixed; no steel reinforcement stiffness is added.',
         ])


def case_072():
    m = concrete_frame([0, 5, 12], [3.3, 7.3, 10.4])
    for e in m['elements']:
        if e['type'] == 'beam':
            floor = int(e['id'].split('-')[-1])
            load(m, type='distributed', element=e['id'], wz=-[12, 10, 8][floor - 1])
    r = Requests(m)
    request_floors(r)
    request_drifts(r)
    r.supports()
    for e in m['elements']:
        if e['type'] == 'column' and e['id'].endswith('-1'):
            r.ends(e['id'], ('M2',))
    emit(72, m,
         'Build a planar concrete frame with bays 5 m and 7 m and story heights 3.3 m, 4.0 m '
         'and 3.1 m. The floor elevations are 3.3 m, 7.3 m and 10.4 m. Fix all three column bases. '
         'Both beams on floors 1, 2 and 3 carry downward full-span loads of 12, 10 and 8 kN/m, '
         'respectively, in case D. The completed property appendix specifies C30 concrete '
         '(E=30000 MPa, nu=0.2, G=12500 MPa, density=2500 kg/m^3), 500x500 mm columns C1 '
         'and 300x600 mm beams B1. Run a first-order linear elastic Euler-Bernoulli analysis '
         'in OpenSees with self weight off. Report ux, uz and ry at every column line on '
         'every floor; signed horizontal story displacement differences ux(upper)-ux(lower) '
         'at all nine column segments; Fx, Fz and My at all three bases; and local M2 at both '
         'ends of every first-story column. Use the exact cumulative elevations.', r,
         notes=[
             'The source leaves concrete grade and section sizes to an appendix. Freeze C30 E=30000 MPa, nu=0.2, rho=2500 kg/m3, columns 500x500 mm and beams 300x600 mm.',
             'Story displacement difference is explicitly the signed horizontal ux difference across each actual column segment, not a drift ratio or an absolute value.',
         ])


def case_073():
    m = concrete_frame([0, 6, 12], [3.6, 7.2])
    m['materials'].append(concrete_material('C40'))
    for e in m['elements']:
        e['material'] = 'C40' if e['type'] == 'column' else 'C30'
    beams_udl(m, 10)
    load(m, type='nodal', node='n2-2', fx=20)
    r = Requests(m)
    request_floors(r, ('ux',))
    request_ends(r)
    r.supports()
    emit(73, m,
         '两层两跨平面混凝土框架：两跨各6m，两层各3.6m，三个柱脚固定。柱使用C40 '
         '(E=32500MPa、ν=0.2、G=32500/2.4MPa)，梁使用C30 '
         '(E=30000MPa、ν=0.2、G=12500MPa)，两种材料ρ均为2500kg/m³。'
         '完整附表规定柱C1为500×500mm、梁B1为300×600mm。D工况中所有梁均布向下10kN/m，'
         '顶层最右节点n2-2另受全局+X向20kN水平力。使用OpenSees一阶线弹性Euler-Bernoulli分析，'
         '不做材料非线性，自重关闭。报告各层三柱线ux、所有梁柱两端N/V3/M2、三个柱脚Fx/Fz/My，'
         '并提交逐构件材料分配记录，列明构件ID、角色、材料等级、实际E与ν。', r,
         notes=[
             'Role-specific grade assignments are source requirements. The missing property appendix freezes C30 E=30000 MPa and C40 E=32500 MPa, both nu=0.2 and rho=2500 kg/m3.',
             'Unspecified column and beam sizes are completed as 500x500 mm C1 and 300x600 mm B1; all member ends are selected to make representative force coverage explicit.',
             'Gravity and the stated top-right +X nodal force are both in the single D case; the source specifies no separate combinations.',
         ],
         interactions=['逐构件材料分配记录：构件ID、梁/柱角色、材料等级、实际E（MPa）与ν；所有柱为C40，所有梁为C30。'])


def case_074():
    m = concrete_frame([0, 7], [3.6, 7.2])
    m['sections'] = [section('B1', .3, .6), section('CR', .35, .5)]
    for e in m['elements']:
        if e['type'] == 'column':
            e['section'] = 'CR'
            e['rotation_angle'] = 90 if e['id'].startswith('c1-') else 0
    beams_udl(m, 10)
    load(m, type='nodal', node='n1-2', fx=20)
    r = Requests(m)
    request_floors(r, ('ux',))
    request_drifts(r)
    request_ends(r, 'column', components=('M2', 'M3'))
    r.supports()
    axes = (
        'RECTANGULAR COLUMN ORIENTATION APPENDIX\n'
        'All axes below are global XYZ unit vectors. Positive roll angles are in degrees.\n'
        'For every member, local x points from the first listed node to the second.\n'
        'At zero roll in the XZ plane, local y=(0,1,0) and local z=local x cross local y.\n'
        'Roll theta transforms y_new=cos(theta)*y+sin(theta)*z and '
        'z_new=-sin(theta)*y+cos(theta)*z.\n'
        'Both column lines use the identical CR section: B=350 mm along local y, H=500 mm '
        'along local z; A=0.175 m^2, Iy=0.003645833333333333 m^4, '
        'Iz=0.001786458333333333 m^4. J is listed in input-data.json.\n'
        'Left columns c0-1 and c0-2: roll=0; x=(0,0,1), y=(0,1,0), z=(-1,0,0). '
        'Planar bending uses Iy about local y (strong axis); global My equals local M2.\n'
        'Right columns c1-1 and c1-2: roll=90; x=(0,0,1), y=(-1,0,0), z=(0,-1,0). '
        'Planar bending uses Iz about local z (weak axis); global My equals minus local M3.\n'
        'Beams b0-1 and b0-2: roll=0; x=(1,0,0), y=(0,1,0), z=(0,0,1).\n'
        'Report both local M2 and M3 at both ends of every column and identify the '
        'nonzero in-plane component. Moment signs follow the cut convention in the '
        'general analysis appendix. No extra nodal couple is applied.\n'
    )
    emit(74, m,
         'Build a two-story, single-bay planar concrete frame: span 7 m, story heights '
         '3.6 m and 3.6 m, both bases fixed. Each beam carries 10 kN/m downward and the '
         'top-right node n1-2 carries 20 kN in global +X, all in case D. The explicit '
         'appendix supplies C30 (E=30000 MPa, nu=0.2, G=12500 MPa, density=2500 kg/m^3), '
         '300x600 mm beams and identical 350x500 mm rectangular columns CR. The left '
         'columns have roll 0 degrees; the right columns have roll 90 degrees. Use '
         'column-orientations.txt to preserve the different strong/weak bending directions '
         'and exact local axes. Run first-order linear elastic Euler-Bernoulli analysis '
         'in OpenSees, self weight off. Report ux at both column tops on each story, '
         'the four signed ux(upper)-ux(lower) story displacement differences, local M2 '
         'and M3 at both ends of all four columns, and Fx/Fz/My at both bases.', r,
         notes=[
             'The source specifies different strong/weak directions but leaves rectangle dimensions and actual axis vectors to the appendix. Freeze one CR 350x500 mm section with left roll 0 degrees and right roll 90 degrees, rather than silently swapping section names.',
             'C30 E=30000 MPa, nu=0.2, rho=2500 kg/m3 and 300x600 mm beams complete the missing material/beam appendix.',
             'The two-dimensional protocol uses initial local y=global +Y, z=x cross y, with roll applied afterwards. Right-column in-plane bending is local M3; both M2 and M3 are requested so a roll omission cannot be concealed.',
         ], extra_attachments={'column-orientations.txt': axes})


def case_075():
    m = model(concrete=True)
    m['materials'] = [concrete_material()]
    m['sections'] = [section('B1', .3, .6), section('B2', .3, .5),
                     section('C1', .6, .6), section('C2', .5, .5)]
    for level, z, count in [(0, 0, 4), (1, 3.6, 4), (2, 7.2, 3)]:
        for line in range(count):
            node(m, f'n{line}-{level}', line * 5, z,
                 restraint=[True] * 6 if level == 0 else None)
    for level, count in [(1, 4), (2, 3)]:
        for line in range(count):
            elem(m, f'c{line}-{level}', f'n{line}-{level-1}', f'n{line}-{level}',
                 'column', 'C1' if level == 1 else 'C2')
        for bay in range(count - 1):
            eid = elem(m, f'b{bay}-{level}', f'n{bay}-{level}', f'n{bay+1}-{level}',
                       sec='B1' if level == 1 else 'B2')
            load(m, type='distributed', element=eid, wz=-12 if level == 1 else -8)
    for e in m['elements']:
        e['material'] = 'C30'
    r = Requests(m)
    for nid in ['n3-1', 'n2-1', 'n2-2']:
        r.node(nid, ('ux', 'uz', 'ry'))
    request_drifts(r)
    request_ends(r)
    r.supports()
    emit(75, m,
         '建立两层平面混凝土退台框架，两层均高3.6m。下层三跨各5m，柱线X=0、5、10、15m；'
         '上层仅保留左侧两跨，即X=0、5、10m三条柱线。四个实际柱脚全部固定。'
         'D工况：下层三根梁均向下12kN/m，上层左侧两根梁均向下8kN/m；上层X=10至15m区域'
         '没有节点、梁、柱或荷载。完整属性附表冻结全部C30，E=30000MPa、ν=0.2、G=12500MPa、'
         'ρ=2500kg/m³；第一层柱C1=600×600mm、第二层柱C2=500×500mm，'
         '第一层梁B1=300×600mm、第二层梁B2=300×500mm。'
         '使用OpenSees作一阶线弹性Euler-Bernoulli分析，自重关闭。输出三处退台轮廓转接节点'
         'n3-1=(15,0,3.6)m、n2-1=(10,0,3.6)m与n2-2=(10,0,7.2)m的ux、uz、ry；所有实际柱线逐层'
         'ux上节点减下节点的有符号层间位移差（第一层四组、第二层三组）；'
         '全部梁柱两端N/V3/M2和四柱脚Fx/Fz/My。', r,
         notes=[
             'The plan requires section groups but gives no group dimensions. Freeze C30 throughout; story-1 columns 600x600 mm, story-2 columns 500x500 mm, story-1 beams 300x600 mm, story-2 beams 300x500 mm.',
             'Setback endpoint wording is resolved conservatively by requesting all three outline transition nodes: (15,0,3.6), (10,0,3.6) and (10,0,7.2) m, including the re-entrant connection.',
             'There is no n3-2, c3-2 or b2-2. Story differences use seven actual column segments; no fictitious upper story is introduced at x=15 m.',
         ])


def case_076():
    m = concrete_frame([0, 5, 12], [3.6, 7.2])
    mids = []
    for eid in ['b0-1', 'b1-1', 'b0-2', 'b1-2']:
        mids.append(beam_midpoint(m, eid))
    for e in m['elements']:
        if e['type'] == 'beam':
            load(m, type='distributed', element=e['id'], wz=-40 if e['id'].startswith('b0-') else -60)
    r = Requests(m)
    request_floors(r)
    for nid in mids:
        r.node(nid, ('ux', 'uz', 'ry'))
    r.supports()
    emit(76, m,
         'Build a two-story planar concrete frame with bays 5 m and 7 m, both story heights '
         '3.6 m, and all three column bases fixed. Each floor has a downward area load of '
         '10 kN/m^2. The left beam tributary width is 4 m and the right beam width is 6 m, '
         'so apply only the converted full-span line loads: left 40 kN/m and right 60 kN/m '
         'in case D on both stories. The area load is conversion input, not an additional '
         'applied load. The completed appendix supplies C30 (E=30000 MPa, nu=0.2, '
         'G=12500 MPa, density=2500 kg/m^3), 500x500 mm columns C1 and 300x600 mm beams B1. '
         'Each physical beam has a connected, unreleased midpoint observation node and two '
         'continuous halves; each half receives its own span line-load intensity once. '
         'Run first-order linear elastic Euler-Bernoulli analysis in OpenSees with self '
         'weight off. Report ux, uz and ry at all four beam midpoints and at every column '
         'top on both stories, plus Fx/Fz/My at the three bases.', r,
         notes=[
             'The source leaves the material and sizes to an appendix: C30 E=30000 MPa, nu=0.2, rho=2500 kg/m3, columns 500x500 mm, beams 300x600 mm.',
             'Each span midpoint is an actual connected node without added mass, release or restraint beyond the common planar constraints. Distributed loading is divided between physical half-spans without changing intensity.',
             'Per floor, the applied gravity resultant is 40*5+60*7=620 kN; both floors total 1240 kN. No separate area load or self-weight load is applied.',
         ])


def case_077():
    m = concrete_frame([0, 6, 12], [3.3, 6.6, 9.9])
    m['sections'] = [section('B1', .3, .6), section('B2', .3, .7),
                     section('C1', .6, .6), section('C2', .5, .5)]
    for e in m['elements']:
        floor = int(e['id'].split('-')[-1])
        e['section'] = ('C1' if floor == 1 else 'C2') if e['type'] == 'column' else ('B2' if floor == 3 else 'B1')
    mids = [beam_midpoint(m, eid) for eid in ['b0-3', 'b1-3']]
    beams_udl(m, 10)
    r = Requests(m)
    request_floors(r)
    request_ends(r, 'column')
    for eid in ['b0-3', 'b1-3']:
        r.member(eid + '-a', 0, ('N', 'V3', 'M2'), side='right')
        r.member(eid + '-b', 3, ('N', 'V3', 'M2'), side='left')
        r.member(eid + '-a', 3, ('N', 'V3', 'M2'), side='left')
    for nid in mids:
        r.node(nid, ('ux', 'uz', 'ry'))
    r.supports()
    emit(77, m,
         '三层两跨平面混凝土框架，两跨各6m，三层层高均为3.3m，标高3.3、6.6、9.9m；'
         '三个柱脚固定。第一层柱C1=600×600mm，第二、三层柱C2=500×500mm。'
         '完整附表规定一、二层梁B1=300×600mm，顶层梁单独分组B2=300×700mm；全部为C30 '
         '(E=30000MPa、ν=0.2、G=12500MPa、ρ=2500kg/m³)。D工况中全部六根物理梁'
         '均为全跨向下10kN/m。顶层两根物理梁各设真实连接跨中观测节点，两半刚接且均保持B2属性，'
         '不增加集中质量。使用OpenSees一阶线弹性Euler-Bernoulli分析，自重关闭。'
         '报告各层三柱线节点ux/uz/ry、所有九根分层柱两端N/V3/M2、两根顶层梁的'
         '物理端部与跨中N/V3/M2以及跨中ux/uz/ry，并输出三个柱脚Fx/Fz/My。', r,
         notes=[
             'Source-specified first-story 600x600 mm and upper-story 500x500 mm columns are preserved. The missing B1/B2 appendix is frozen as 300x600 mm for floors 1-2 and 300x700 mm for the top floor.',
             'The missing concrete grade/properties are frozen as C30 E=30000 MPa, nu=0.2 and rho=2500 kg/m3.',
             'Top-beam response is resolved as both physical end forces, midpoint forces, and actual connected midpoint-node displacement/rotation. Both halves retain B2 and the same 10 kN/m load intensity.',
         ])


def case_078():
    m = concrete_frame([0, 6], [3.3, 6.6, 9.9])
    for floor, q, wind in [(1, 12, 10), (2, 10, 15), (3, 8, 20)]:
        load(m, type='distributed', element=f'b0-{floor}', wz=-q)
        load(m, 'W+', type='nodal', node=f'n1-{floor}', fx=wind)
        load(m, 'W-', type='nodal', node=f'n1-{floor}', fx=-wind)
    m['load_combinations'] = [dict(id='C0', factors={'D': 1}),
                              dict(id='C+', factors={'D': 1, 'W+': 1}),
                              dict(id='C-', factors={'D': 1, 'W-': 1})]
    r = Requests(m)
    for selection in ['C0', 'C+', 'C-']:
        request_floors(r, ('ux',), selection)
        request_drifts(r, selection)
        r.supports(selection)
        for eid in ['c0-1', 'c1-1']:
            r.ends(eid, ('M2',), selection)
    emit(78, m,
         'Build a three-story, single-bay planar concrete frame with span 6 m, three '
         'story heights of 3.3 m and both bases fixed. The completed appendix specifies '
         'C30 (E=30000 MPa, nu=0.2, G=12500 MPa, density=2500 kg/m^3), 500x500 mm columns '
         'C1 and 300x600 mm beams B1. D applies downward full-span line loads of 12, 10 '
         'and 8 kN/m to floors 1, 2 and 3. W+ applies global +X forces of 10, 15 and '
         '20 kN at the right node of floors 1, 2 and 3. W- is a separate case with '
         'the same positions and exactly opposite forces. Analyze precisely these three '
         'linear combinations: C0=D; C+=D+W+; C-=D+W-. Run first-order linear elastic '
         'Euler-Bernoulli analysis in OpenSees, self weight off. For each combination '
         'separately, report signed ux at both column lines on all three floors, all '
         'six signed story displacement differences ux(upper)-ux(lower), Fx/Fz/My at '
         'both bases and M2 at both ends of both first-story columns. Preserve the '
         'original signs and the distinct case and combination labels.', r,
         notes=[
             'The missing appendix is completed by C30 E=30000 MPa, nu=0.2, rho=2500 kg/m3, columns 500x500 mm and beams 300x600 mm.',
             'W+ and W- are independent load cases with signed +10/+15/+20 and -10/-15/-20 kN forces; C0, C+ and C- are the three exact source combinations with unit coefficients.',
             'All requested floor responses, story differences, support reactions and bottom-column end moments are enumerated separately for every one of the three combinations. Independent linear-superposition checks remain pending.',
         ])


def main():
    builders = [case_071, case_072, case_073, case_074, case_075, case_076, case_077, case_078]
    for number, builder in zip(range(71, 79), builders):
        row, task, original_model = source(number)
        assert row['id'] == task['id'] == original_model['taskId']
        assert row['plannedEngine'] == 'OpenSees'
        builder()


if __name__ == '__main__':
    main()
