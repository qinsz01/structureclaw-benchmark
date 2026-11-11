"""Explicit INT-037..040 truss appendices; authoring only, no numeric oracle values."""
from copy import deepcopy
import json
import math

from int_a_common import (ROOT, model, node, elem, load, section, quantity,
                          member_quantity, turn, tables, finalize, write_case)


TRUSS_FREE = [False, True, False, True, True, True]
TRUSS_PIN = [True, True, True, True, True, True]
TRUSS_ROLLER = [False, True, True, True, True, True]


def planar_grid(xs, heights, diagonals, upper='A1', lower='A1', web='A1'):
    """Populate the explicitly supplied panel list and diagonal endpoint table."""
    m = model()
    m['sections'] = [section('A1', .1, .1)]
    for i, (x, height) in enumerate(zip(xs, heights)):
        restraint = TRUSS_PIN if i == 0 else TRUSS_ROLLER if i == len(xs)-1 else TRUSS_FREE
        node(m, f'L{i}', x, 0, restraint=restraint)
        node(m, f'U{i}', x, height, restraint=TRUSS_FREE)
    for i in range(len(xs)-1):
        elem(m, f'BC{i+1}', f'L{i}', f'L{i+1}', 'truss', lower)
        elem(m, f'TC{i+1}', f'U{i}', f'U{i+1}', 'truss', upper)
    for i in range(len(xs)):
        elem(m, f'V{i}', f'L{i}', f'U{i}', 'truss', web)
    for i, (a, b) in enumerate(diagonals, 1):
        elem(m, f'DG{i}', a, b, 'truss', web)
    return m


def requests(observation, support='L0', first='BC1', selection='D', kind='case', spatial=False):
    displacements = ['ux', 'uz', 'uy'] if spatial else ['ux', 'uz']
    reactions = ['Fx', 'Fy', 'Fz'] if spatial else ['Fx', 'Fz']
    return ([quantity(observation, c, selection, kind) for c in displacements]
            + [quantity(support, c, selection, kind) for c in reactions]
            + [member_quantity(first, 'N', 0, 'right', selection, kind)])


def public(m, locale, extra=''):
    note = ('Author-completed appendix: the listed connectivity and all absolute section properties '
            'complete the source attachment. All elements are pin-ended, axial-only trusses; '
            'member axial force N is positive in tension. No nodal masses are added. '
            'E and G are in MPa; density is kg/m3; all section properties are explicit. '
            'Unused rotational degrees of freedom are fixed only as bookkeeping for axial elements. ')
    if locale == 'zh':
        note = ('编题补齐附件：明确连接表与截面绝对属性补齐源规划的待编附表。所有单元为两端铰接、仅轴向受力的桁架杆；'
                '轴力N以受拉为正。不添加节点质量。E/G单位MPa，密度kg/m3，截面属性完整明列。'
                '转动自由度约束仅消除轴力单元未激活的记账自由度，不提供抗弯刚度。')
    return tables(m, locale, note + extra)


def build_037():
    m = planar_grid([0, 2, 5, 9, 12], [2.2]*5,
                    [('L0','U1'), ('L1','U2'), ('U2','L3'), ('U3','L4')])
    for label, force in [('U1',8), ('U2',12), ('U3',10)]:
        load(m, id=f'vertical-{label}', type='nodal', node=label, fz=-force)
    load(m, id='horizontal-U2', type='nodal', node='U2', fx=4)
    visible = deepcopy(m)
    for n in visible['nodes']:
        if int(n['id'][1:]) >= 2:
            n['x'] = None
    visible['panelLengthsM'] = [2, None, 4, 3]
    visible['coordinateStatus'] = '第二节间长度未给出；U2/L2及其右侧节点的X坐标待补齐'
    turns = [
        turn('按附件建立不等节间桁架，高2.2 m。四节间从左到右，第1、3、4节间为2、4、3 m，第2节间长度空缺；连接和荷载均用节点标签。U1/U2/U3分别向下8/12/10 kN，U2另有全局+X的4 kN。请给U2的Ux/Uz、左下L0支座Fx/Fz及首根下弦BC1(L0→L1)的轴力N。必要几何缺失时先澄清，禁止编造数值。', None, 'clarify', ['input-t1.txt'], ['geometry.panelLengthsM[1]'], ['第二节间长度是多少？']),
        turn('补充第二节间为3 m，累计X依次为0、2、5、9、12 m，完整节点坐标表见本轮附件。U2位于x=5 m。分析并给U2的Ux/Uz、L0反力Fx/Fz及BC1轴力N，注明位置、方向、单位、D工况和第2轮。保持所有节点标签、连接、竖向力与U2的+X 4 kN不变。', 1, attachments=['coordinates-t2.json'])
    ]
    return write_case('INT-037', [m], turns, [requests('U2')],
        {'input-t1.txt': public(visible, 'zh', '首根下弦输出杆为BC1，按L0→L1方向定义；截面A1为0.10×0.10 m实心方形。所有null X坐标均未提供，不表示0。'),
         'coordinates-t2.json': {'单位': 'm', '节点': m['nodes']}},
        decisions=['Source did not supply the complete connectivity appendix: the explicit 10-node,17-member topology has upper/lower chords, five verticals, and four listed inward-oriented diagonals.',
                   'A1 is authored as a 0.10x0.10 m solid square; M1 E=206000 MPa, nu=0.3, G=E/[2(1+nu)], rho=7850 kg/m3.',
                   'First-turn total span, all cumulative X coordinates at and after U2/L2, requested global observation X, and derived member vectors are withheld. Loads are specified only by node labels.',
                   'Source permits uniquely justified direct inference; authored T1 contains no other information fixing the missing panel length.'],
        source_audit=['2,3,4,3 m panels; z=2.2; U1/U2/U3 Fz=-8/-12/-10; U2 Fx=+4; left pin and right horizontal-free vertical roller; BC1 force requested.'])


def build_038():
    m = planar_grid([0, 3, 6, 9, 12, 15], [1.5, 1.8, 2.1, 2.4, 2.7, 3],
                    [('L0','U1'), ('U1','L2'), ('L2','U3'), ('L3','U4'), ('U4','L5')])
    m['materials'] = [dict(id='M1', name='lower-and-web', type='steel', E=200000, G=200000/2.6, nu=.3, rho=7850),
                      dict(id='M2', name='upper-chord', type='steel', E=210000, G=210000/2.6, nu=.3, rho=7850)]
    for e in m['elements']:
        if e['id'].startswith('TC'):
            e['material'] = 'M2'
    for label, force in [('U1',8), ('U3',12), ('U5',6)]:
        load(m, id=f'force-{label}', type='nodal', node=label, fz=-force)
    modified = deepcopy(m)
    modified['nodes'][11]['z'] = 3.3
    turns = [
        turn('Analyze the single-slope 15 m truss using the explicit attachment. The lower chord is horizontal; the upper height increases from 1.5 to 3 m. Upper-chord E=210000 MPa; lower-chord and web E=200000 MPa. Downward loads of 8, 12 and 6 kN act at upper nodes x=3,9,15 m. Report Ux/Uz at U5, the upper x=15 m node; Fx/Fz at left support L0; and axial N in first lower-chord member BC1 (L0 to L1). Include signed direction, units, D case and turn 1.', 1, attachments=['input-t1.txt']),
        turn('Move only upper node U5 at x=15 m from z=3 to z=3.3 m. Keep every other node, connection, load ID, force vector and material role unchanged. Update member geometry from its endpoints and reanalyze. Report U5 Ux/Uz, L0 reactions Fx/Fz and BC1 axial N with location, direction, units, D case and turn 2.', 2,
             changedFields=['/nodes/11/z', '/metadata/elementReferenceVectors/TC5/0', '/metadata/elementReferenceVectors/V5/0'],
             preservedFields=['/elements', '/materials', '/sections', '/load_cases', '/load_combinations', '/analysis_control'])
    ]
    qq = requests('U5')
    return write_case('INT-038', [m, modified], turns, [qq, deepcopy(qq)],
        {'input-t1.txt': public(m, 'en', 'The appended panel layout is x=0,3,6,9,12,15 m, with top heights 1.5,1.8,2.1,2.4,2.7,3 m. The diagonal endpoints are explicitly listed and are not a mirrored template. A1 is a 0.10 by 0.10 m solid square. BC1 is the first lower member, L0 to L1.')},
        decisions=['The missing connectivity appendix is completed by the explicit12-node,21-member single-slope truss; its five diagonals follow the listed asymmetric endpoint table.',
                   'Source E=210000 MPa applies only to upper-chord elements; E=200000 MPa applies to all lower-chord and web elements. Author fixes nu=0.3,rho=7850 kg/m3 and A1=0.10x0.10 m.',
                   'Only U5 z changes physically; the dependent local reference vectors of TC5 and V5 are recomputed from the changed endpoints.'],
        source_audit=['15 m span; initial top z1.5..3; U5 rises only0.3; Fz U1/U3/U5=-8/-12/-6; upper/lower/web E role mapping unchanged.'])


def build_039():
    m = planar_grid([0, 4, 8, 12, 16, 20], [3]*6,
                    [('L0','U1'), ('L1','U2'), ('U2','L3'), ('U3','L4'), ('U4','L5')],
                    upper='A1', lower='A2', web='A3')
    m['sections'] = [section('A1', .1, .12), section('A2', .12, .12), section('A3', .08, .08)]
    for i in [1,2,3,4]:
        load(m, id=f'D-U{i}', type='nodal', node=f'U{i}', fz=-10)
    for i in [2,3]:
        load(m, 'W', id=f'W-U{i}', type='nodal', node=f'U{i}', fz=5)
    m['load_combinations'] = [dict(id='D+W', factors={'D': 1, 'W': 1})]
    visible = deepcopy(m)
    for e in visible['elements']:
        if e['id'].startswith('TC'):
            e['section'] = None
    visible['conflictingSectionLabels'] = {'A2': ['upper chord', 'lower chord'], 'upperChordAuthority': None}
    modified = deepcopy(m)
    a4 = section('A4', .1, .1)
    modified['sections'].append(a4)
    changed = []
    for i, e in enumerate(modified['elements']):
        if e['id'].startswith(('V','DG')):
            e['section'] = 'A4'
            changed.append(f'/elements/{i}/section')
    turns = [
        turn('按附件建立跨度20 m、高3 m、5节间桁架；属性表将A2同时标为上弦和下弦，分组引用存在冲突。D在U1/U2/U3/U4各向下10 kN；独立W只在U2、U3各向上5 kN；分析组合D+W。请给U2(x=8 m)的Ux/Uz、左支座L0的Fx/Fz及首根下弦BC1轴力N。请先澄清截面组映射，不编造数值。', None, 'clarify', ['input-t1.txt'], ['sectionAssignment.upperChord'], ['请确认上弦、下弦与腹杆分别应引用哪一条截面属性记录？']),
        turn('确认上弦A1、下弦A2、腹杆A3。请分析D+W并报告U2(x=8 m)的Ux/Uz、L0反力Fx/Fz及BC1轴力N，注明位置、方向、单位、组合和第2轮。保留D与W两个独立工况及节点、拓扑。', 1),
        turn('仅将全部腹杆（竖杆与斜杆）改用本轮附件A4实体截面记录，上弦仍A1、下弦仍A2。重新分析D+W并报告U2的Ux/Uz、L0反力Fx/Fz与BC1轴力N，注明第3轮和方向、单位。所有节点与荷载保持，W仍只在U2/U3向上。', 2,
             attachments=['section-a4-t3.json'], changedFields=['/sections/3', *changed],
             preservedFields=['/nodes', '/materials', '/load_cases', '/load_combinations', '/analysis_control', '/sections/0', '/sections/1', '/sections/2'])
    ]
    qq = requests('U2', selection='D+W', kind='combination')
    return write_case('INT-039', [m, modified], turns, [qq, deepcopy(qq)],
        {'input-t1.txt': public(visible, 'zh', 'A1/A2/A3为截面记录，材料统一M1；上弦截面null表示冲突未解，不表示零截面。首根下弦输出杆BC1由L0指向L1。'),
         'section-a4-t3.json': {'单位': {'shape':'mm','A':'m2','Iy':'m4','Iz':'m4','J':'m4'}, '截面': a4}},
        decisions=['The source title mentions material-table references, but its scenario and grading specify A1/A2/A3/A4 physical-area groups; these are authored as section references, with one common material M1.',
                   'The complete12-node,21-member connection table is an author completion; 5 panels are each4 m and height3 m.',
                   'Source omitted absolute sections: A1=0.10x0.12 m,A2=0.12x0.12 m,A3=0.08x0.08 m,A4=0.10x0.10 m solid rectangles. M1 E206000 MPa,nu0.3,rho7850 kg/m3 with explicit G.',
                   'A4 is introduced only at turn3; upper-chord assignment remains unresolved in turn1 despite the availability of all other property records.'],
        source_audit=['Upper/lower/web mapping A1/A2/A3 confirmed t2, only web toA4 t3; D=-10 atU1..U4; W=+5 onlyU2/U3; requested combinationD+W.'])


def build_040():
    m = model('3d')
    m['sections'] = [section('A1', .1, .1)]
    enhanced = deepcopy(m['sections'][0])
    enhanced.update(id='A_AD', name='A_AD', type='general')
    enhanced.pop('shape')
    enhanced['properties'] = {key: value*1.5 for key,value in enhanced['properties'].items()}
    m['sections'].append(enhanced)
    node(m, 'A', 0, 0, 0, [True,True,True,True,True,True])
    node(m, 'B', 4, 0, 0, [False,True,True,True,True,True])
    node(m, 'C', 2, 0, 2*math.sqrt(3), [False,False,True,True,True,True])
    node(m, 'D', 2, 3, 2*math.sqrt(3)/3, [False,False,False,True,True,True])
    for label, a, b in [('AB','A','B'), ('BC','B','C'), ('CA','C','A'), ('AD','A','D'), ('BD','B','D'), ('CD','C','D')]:
        elem(m, label, a, b, 'truss', 'A_AD' if label=='AD' else 'A1')
    load(m, id='apex-force', type='nodal', node='D', fz=-20)
    visible = deepcopy(m)
    visible['nodes'][1]['restraints'][1] = None
    turns = [
        turn('Model the four-node, six-member tetrahedral truss in the attachment, with the exact coordinate expressions A=(0,0,0), B=(4,0,0), C=(2,2*sqrt(3),0), D=(2,2*sqrt(3)/3,3) m. A has X,Y,Z translations fixed; B has Z fixed but its Y restraint field is blank; C has Z fixed. Other unlisted translations are free. AD has 1.5 times the area of the other members. A 20 kN global downward force acts at D. Request D Ux/Uz/Uy, reactions Fx/Fy/Fz at A, and axial N in the first bottom-edge member AB. Clarify any essential missing restraint.', None, 'clarify', ['input-t1.txt'], ['supports.B.uy'], ['Is translation in global Y restrained or free at B?']),
        turn('Confirm that B translation in global Y is fixed. Retain all other stated restraints and free translations. Analyze the current truss and report D Ux/Uz/Uy, A reactions Fx/Fy/Fz and AB axial N, with signed direction, locations, units, D load case and turn 2. Retain the reinforced AD area and the 20 kN downward apex force.', 1)
    ]
    return write_case('INT-040', [m], turns, [requests('D', support='A', first='AB', spatial=True)],
        {'input-t1.txt': public(visible, 'en', 'The coordinate expressions in the instruction define the exact geometry; the table uses their floating-point values. B restraint uy=null is unspecified, not free or fixed. A1 area is 0.01 m2; AD area is 0.015 m2. The first bottom-edge member AB is directed A to B. Rotations are inactive for all truss members.')},
        decisions=['Use exact equilateral-base expressions with floating-point sqrt(3) evaluations in hidden/public coordinate tables. No apex or support geometry is invented.',
                   'M1 E206000 MPa,nu0.3,G=E/[2(1+nu)],rho7850 kg/m3; ordinary A1 is0.10x0.10 m. AD area ratio1.5 is source-prescribed; unused Iy,Iz,J are completed at1.5 times A1.',
                   'Initial B uy is null everywhere in public inputs and the total support-translation count is not disclosed. Final translations are A XYZ,B YZ,C Z. Fixed rotational bookkeeping does not create physical bending constraints.',
                   'Left-support reaction is interpreted as all three translational reaction components at A; bottom-edge axial output is explicitly AB.'],
        source_audit=['Four exact spatial nodes,six axial elements,AD only strengthened; apexFz=-20; six independent final translation constraints, all truss rotations inactive.'])


def validate():
    stats = {'cases': 4, 'states': 0, 'turns': 0, 'quantities': 0}
    for number in [37,38,39,40]:
        p = ROOT / f'corpora/research-300/cases/INT-{number:03d}'
        c = json.loads((p/'contract.json').read_text())
        rr = json.loads((p/'reference-requests.json').read_text())
        assert len(c['turns']) == c['sourceMetadata']['task']['turns']
        assert {r['id'] for r in c['sourceMetadata']['requirements']} == {i for row in c['requirementCoverage'] for i in row['requirementIds']}
        for s in rr['states']:
            m = json.loads((p/s['model']).read_text())
            ns = {n['id']:n for n in m['nodes']}
            es = {e['id']:e for e in m['elements']}
            assert all(e['type']=='truss' for e in m['elements'])
            assert len(s['quantities']) == (7 if number==40 else 5)
            for q in s['quantities']:
                assert 'value' not in q
                assert q['location']['id'] in (ns if q['location']['kind']=='node' else es)
            if number==40:
                assert sum(sum(n['restraints'][:3]) for n in m['nodes']) == 6
                a = {s['id']:s['properties']['A'] for s in m['sections']}
                assert math.isclose(a['A_AD']/a['A1'],1.5)
            if number==38:
                materials = {x['id']:x['E'] for x in m['materials']}
                assert all(materials[e['material']] == (210000 if e['id'].startswith('TC') else 200000) for e in m['elements'])
            if number==39:
                assert [(q['node'],q['fz']) for q in m['load_cases'][1]['loads']] == [('U2',5),('U3',5)]
                assert m['load_combinations']==[dict(id='D+W',factors={'D':1,'W':1})]
            stats['quantities'] += len(s['quantities'])
        if c['locale']=='en':
            for name in ['prompt.txt',*c['attachments']]:
                assert not any('\u4e00'<=ch<='\u9fff' for ch in (p/name).read_text())
        stats['states'] += len(rr['states'])
        stats['turns'] += len(c['turns'])
    p = ROOT/'corpora/research-300/cases/INT-037/input-t1.txt'
    text = p.read_text()
    visible = json.loads(text[text.index('{'):])
    assert visible['panelLengthsM'] == [2,None,4,3]
    assert all(n['x'] is None for n in visible['nodes'] if int(n['id'][1:])>=2)
    assert visible.get('metadata',{}) == {}
    assert all(p['node'] in ['U1','U2','U3'] for p in visible['load_cases'][0]['loads'])
    p = ROOT/'corpora/research-300/cases/INT-040/input-t1.txt'
    text = p.read_text()
    visible = json.loads(text[text.index('{'):])
    assert visible['nodes'][1]['restraints'][1] is None
    for word in ['six independent','six constraints','six restraints','six translation']:
        assert word not in text.lower()
    print(json.dumps(stats,sort_keys=True))


if __name__=='__main__':
    for number in [37,38,39,40]:
        globals()[f'build_{number:03d}']()
    validate()
