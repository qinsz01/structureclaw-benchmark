"""Source-specific INT-011..020 authoring. No solver calls or answer values."""
from copy import deepcopy
import json
import math
from pathlib import Path

from int_a_common import (ROOT, FIXED, PIN, ROLLER, FREE, model, node, elem,
                          load, section, turn, quantity, tables, write_case)


def base():
    m = model()
    m['sections'] = [section('B1', .3, .6)]
    return m


def proportional_section(name, area_factor=1., inertia_factor=1.):
    p = section('B1', .3, .6)['properties']
    return dict(id=name, name=name, type='general', properties={
        'A': p['A'] * area_factor, 'Iy': p['Iy'] * inertia_factor,
        'Iz': p['Iz'] * inertia_factor, 'J': p['J'] * inertia_factor})


def chain(xs, supports, assignments=None):
    m = base()
    for i, x in enumerate(xs):
        node(m, f'n{i}', x, 0, restraint=supports.get(x, FREE))
    for i in range(len(xs) - 1):
        elem(m, f'b{i+1}', f'n{i}', f'n{i+1}', sec=(assignments or ['B1'] * (len(xs)-1))[i])
    return m


def udl(m, magnitude, members=None, case='D'):
    for e in m['elements']:
        if members is None or e['id'] in members:
            load(m, case, id=f'{case}-udl-{e["id"]}', type='distributed', element=e['id'], wz=-magnitude)


def requested(node_id, support_id, selection='D', kind='case'):
    return [quantity(node_id, 'uz', selection, kind), quantity(support_id, 'Fz', selection, kind)]


def appendix(m, locale, extra=''):
    if locale == 'en':
        note = ('Author-completed physical appendix: elastic material M1 has E=206000 MPa, '
                'nu=0.3 and rho=7850 kg/m3; G is explicitly listed. The listed section '
                'properties are authoritative inputs. All members have zero roll and '
                'no end releases. Observation nodes share the connected beam, with no '
                'added support or mass. Input values complete the unspecified source appendix. ')
    else:
        note = ('编题补齐的实体属性附表：M1弹性模量E=206000 MPa、nu=0.3、rho=7850 kg/m3，G逐项明列。'
                '截面以列出的实体属性为准。各杆截面转角均为0，无杆端释放。观测节点接入连续梁，'
                '不新增支承或质量。上述值补齐源规划未给定的附表。')
    return tables(m, locale, note + extra)


def decision(*items):
    return ['Source appendix omitted absolute material/section values; the explicit public appendix freezes those author choices before candidate execution.',
            'All observation nodes are connected, massless beam subdivisions with unchanged continuity.',
            *items]


def build_011():
    m = chain([0, 3.5, 5, 7], {0: FIXED, 7: ROLLER}, ['B1', 'B1', 'B2'])
    m['sections'].append(proportional_section('B2', 1.8, 1.8))
    udl(m, 10)
    load(m, id='point-at-5', type='nodal', node='n2', fz=-20)
    visible = deepcopy(m)
    visible['nodes'][-1]['restraints'] = None
    visible['nodes'][-1]['supportDescription'] = '有支承，约束自由度待确认'
    turns = [
        turn('按附件建立7 m梁，左端固定，右端有支承。全梁向下10 kN/m，x=5 m另向下20 kN，0～5 m为B1、5～7 m为B2。请给x=3.5 m的Uz及右支座Rz；如必要信息缺失，先提出具体问题，不编造数值。', None, 'clarify', ['input-t1.txt'], ['rightSupport.restraints'], ['右端支承约束哪些自由度，是否释放水平位移及转角？']),
        turn('确认右端只约束全局竖向位移Uz，水平位移Ux与转角Ry自由；左端仍固定。请用当前模型分析并报告x=3.5 m的Uz及x=7 m右支座Rz，附位置、方向、单位、D工况和第2轮。其余几何、截面与荷载保持。', 1)
    ]
    return write_case('INT-011', [m], turns, [requested('n1', 'n3')],
                      {'input-t1.txt': appendix(visible, 'zh', 'B2的A、Iy、Iz均为B1的1.8倍，J同取1.8倍；B2是明示广义截面。右支承null表示待确认，不是自由或固定的默认值。')},
                      decisions=decision('B2 scales A, Iy and Iz by the source-specified 1.8; unspecified J is frozen at 1.8 times B1.', 'Initial right support mask withheld everywhere in public input; left fixed mask retained.'),
                      source_audit=['7 m propped cantilever; 20 kN at x=5 m; B2 only on 5..7 m; 2 turns clarify/analyze.'])


def build_012():
    m = base()
    node(m, 'n0', 0, 0, restraint=FIXED)
    node(m, 'n1', 3, 1.5)
    node(m, 'n2', 6, 3)
    elem(m, 'b1', 'n0', 'n1')
    elem(m, 'b2', 'n1', 'n2')
    load(m, id='main-point', type='nodal', node='n1', fz=-20)
    load(m, id='tip-horizontal', type='nodal', node='n2', fx=8)
    modified = deepcopy(m)
    modified['load_cases'][0]['loads'][0]['fz'] = -25
    visible = deepcopy(m)
    visible['load_cases'][0]['loads'][0] = dict(id='main-point', type='nodal', node='n1', magnitude=20,
        reference_frame=None, direction=None, fx=None, fy=None, fz=None)
    turns = [
        turn('Model the inclined cantilever from (x,z)=(0,0) to (6,3) m, fixed at the origin. The main point force is 20 kN at horizontal projection x=3 m; its direction has not been specified. A separate +X force of 8 kN acts at the free end. Request Ux and Uz at the main force location and fixed-end reaction My. Identify essential missing information before analysis.', None, 'clarify', ['input-t1.txt'], ['mainPoint.direction', 'mainPoint.referenceFrame'], ['In which coordinate system and direction does the 20 kN main point force act?']),
        turn('The 20 kN main point force acts in global negative Z at (x,z)=(3,1.5) m. Analyze and report Ux and Uz there and reaction My at (0,0), with signed direction, units, D load case and turn 2. Retain the separate +X 8 kN free-end force.', 1),
        turn('Replace only the main point-force magnitude by 25 kN, retaining its global negative-Z direction and location (3,1.5) m. Reanalyze and report the same Ux, Uz and fixed-end reaction My for D and turn 3. Keep the +X 8 kN free-end force and all properties unchanged.', 2,
             changedFields=['/load_cases/0/loads/0/fz'], preservedFields=['/nodes', '/elements', '/materials', '/sections', '/load_cases/0/loads/1', '/analysis_control'])
    ]
    qq = [quantity('n1', 'ux'), quantity('n1', 'uz'), quantity('n0', 'My')]
    return write_case('INT-012', [m, modified], turns, [qq, deepcopy(qq)],
                      {'input-t1.txt': appendix(visible, 'en', 'The main-point direction and reference frame are deliberately null and unresolved; its null components are not zeros. The location is defined by horizontal projection, not distance along the member.')},
                      decisions=decision('Global point-force direction is intentionally absent in turn 1; the separate +X 8 kN tip force is fully specified.', 'A connected observation/load node is exactly at (3,0,1.5) m.'),
                      source_audit=['20 to 25 kN replacement at horizontal x=3 m; 8 kN global X tip force unchanged; 3 turns clarify/analyze/analyze.'])


def build_013():
    m = chain([0, 3, 4.5, 6, 9], {0: PIN, 9: ROLLER}, ['B1', 'B2', 'B2', 'B3'])
    m['sections'] += [section('B2', .3, .7), section('B3', .35, .7)]
    udl(m, 12)
    load(m, id='left-support-point', type='nodal', node='n0', fz=-15)
    modified = deepcopy(m)
    b4 = section('B4', .35, .8)
    modified['sections'].append(b4)
    for e in modified['elements'][1:3]:
        e['section'] = 'B4'
    turns = [
        turn('按附件建立9 m简支连续梁：0～3 m用B1、3～6 m用B2、6～9 m用B3；全梁向下12 kN/m，左支座另有向下15 kN节点力，均为D工况。分析并给x=4.5 m的Uz及左支座Rz，附位置、方向、单位、工况和第1轮。', 1, attachments=['input-t1.txt']),
        turn('仅将3～6 m段改用本轮附件新增的B4实体属性。重新分析并报告x=4.5 m的Uz和左支座Rz，标明D工况及第2轮。两外段B1/B3、连通节点、12 kN/m与左支座15 kN节点力均保持。', 2, attachments=['section-b4-t2.json'],
             changedFields=['/sections/3', '/elements/1/section', '/elements/2/section'],
             preservedFields=['/nodes', '/materials', '/load_cases', '/load_combinations', '/analysis_control', '/sections/0', '/sections/1', '/sections/2', '/elements/0', '/elements/3'])
    ]
    return write_case('INT-013', [m, modified], turns, [requested('n2', 'n0'), requested('n2', 'n0')],
                      {'input-t1.txt': appendix(m, 'zh'), 'section-b4-t2.json': {'单位': {'shape': 'mm', 'A': 'm2', 'Iy': 'm4', 'Iz': 'm4', 'J': 'm4'}, '截面': b4}},
                      decisions=decision('Rectangular B1/B2/B3/B4 are respectively 0.30x0.60, 0.30x0.70, 0.35x0.70, 0.35x0.80 m; B4 is introduced only in turn 2.'),
                      source_audit=['B1/B2/B3 assignments retained by interval; only middle changes to B4; 15 kN remains at restrained left node, not in span.'])


def build_014():
    m = chain([0, 2, 4, 5, 6, 8, 10], {0: PIN, 10: ROLLER})
    m['materials'].append(dict(id='M2', name='M2', type='elastic', E=70000, G=70000/(2*1.33), nu=.33, rho=2700))
    for e in m['elements'][2:]:
        e['material'] = 'M2'
    udl(m, 9, ['b2', 'b3', 'b4', 'b5'])
    load(m, id='main-point', type='nodal', node='n4', fz=-25)
    load(m, id='right-end-moment', type='nodal', node='n6', my=-8)
    modified = deepcopy(m)
    modified['load_cases'][0]['loads'][4]['fz'] = -35
    visible = deepcopy(m)
    for e in visible['elements'][2:]:
        e['material'] = 'CONFLICT: M1 and M2 both referenced'
    turns = [
        turn('Model the 10 m beam with the attached properties. The 0–4 m region uses M1, but the 4–10 m region is simultaneously assigned M1 and M2 in the supplied records. A downward 9 kN/m load covers x=2–8 m, a downward 25 kN point force acts at x=6 m, and a global Y moment of -8 kN*m acts at the right end. Request Uz at x=5 m and right-support Rz. Resolve the conflicting material assignment before reporting numerical results.', None, 'clarify', ['input-t1.txt'], ['materialAssignment[4m:10m]'], ['Which material, M1 or M2, applies to x=4–10 m?']),
        turn('Confirm M1 on x=0–4 m and M2 on x=4–10 m. Analyze and report signed Uz at x=5 m and Rz at the right support x=10 m, with direction, units, D case and turn 2. Preserve the load interval, the 25 kN point force and the -8 kN*m global Y end moment.', 1),
        turn('Replace the 25 kN point force at x=6 m by 35 kN downward. Reanalyze and report the same Uz and right-support Rz for D, turn 3. Keep the material boundary at x=4 m, the 9 kN/m load on x=2–8 m, and the -8 kN*m global Y right-end moment unchanged.', 2,
             changedFields=['/load_cases/0/loads/4/fz'], preservedFields=['/nodes', '/elements', '/materials', '/sections', '/load_cases/0/loads/0', '/load_cases/0/loads/1', '/load_cases/0/loads/2', '/load_cases/0/loads/3', '/load_cases/0/loads/5', '/analysis_control'])
    ]
    return write_case('INT-014', [m, modified], turns, [requested('n3', 'n6'), requested('n3', 'n6')],
                      {'input-t1.txt': appendix(visible, 'en', 'M2 has E=70000 MPa, nu=0.33 and rho=2700 kg/m3, with explicit G=E/[2(1+nu)]. The CONFLICT field is unresolved, not an instruction to average materials.')},
                      decisions=decision('Absolute M2 properties are authored as E=70000 MPa, nu=0.33, G=26315.78947368421 MPa, rho=2700 kg/m3.', 'Main point forces are global negative Z; the source-specified right-end moment is global My=-8 kN*m.'),
                      source_audit=['10 m span; material division 4 m; load edges 2 and 8 m; point at 6 m changes 25 to 35; end My=-8 preserved.'])


def build_015():
    m = chain([0, 5, 7, 8, 11], {0: PIN, 5: ROLLER, 11: ROLLER})
    udl(m, 12)
    load(m, id='second-span-point', type='nodal', node='n2', fz=-18)
    # Use a symbolic public appendix: even the observation coordinate would disclose L2.
    visible = {k: deepcopy(v) for k, v in m.items() if k not in ('nodes', 'elements', 'load_cases', 'metadata')}
    visible['geometry'] = dict(firstSpanLengthM=5, secondSpanLengthM=None, axis='global X, y=z=0',
        supports=[dict(name='left', x=0, restraints=PIN), dict(name='middle', x=5, restraints=ROLLER),
                  dict(name='right', x='5 + secondSpanLengthM', restraints=ROLLER)],
        observation='second-span midpoint; x=5+secondSpanLengthM/2', connectivity='one continuous beam through the middle support; no hinge or end release')
    visible['assignments'] = dict(material='M1', section='B1', scope='whole beam')
    visible['load_cases'] = [dict(id='D', type='dead', loads=[
        dict(id='whole-beam-udl', type='distributed', interval='whole beam', wz=-12, reference_frame='global'),
        dict(id='second-span-point', type='point', location='2 m to the right of the middle support', fz=-18, reference_frame='global')])]
    turns = [
        turn('请建立两跨连续梁，首跨5 m，第二跨长度尚未给出。左端铰支，中支座和右支座均为竖向滚支；梁跨越中支座保持连续。全梁向下12 kN/m，第二跨距中支座向右2 m处另向下18 kN。属性见附件。求第二跨中点Uz及中支座Rz；必要输入不足时请先澄清。', None, 'clarify', ['input-t1.txt'], ['geometry.secondSpanLengthM'], ['第二跨的长度是多少？']),
        turn('补充第二跨长度为6 m，故右支座x=11 m，第二跨中点x=8 m，18 kN点力x=7 m。请分析并报告x=8 m的Uz及x=5 m中支座Rz，注明方向、单位、D工况和第2轮。保留中支座处连续性和全梁12 kN/m。', 1)
    ]
    return write_case('INT-015', [m], turns, [requested('n3', 'n1')],
                      {'input-t1.txt': appendix(visible, 'zh', '第二跨长度、右支座坐标与第二跨中点坐标均未给出；符号式不代表数值默认值。')},
                      decisions=decision('All first-turn public coordinates that could reveal the missing second-span length are symbolic; the 18 kN load location alone does not determine the length.', 'Source grading permits a justified direct inference only if information uniquely determines the missing value; these authored initial inputs do not.'),
                      source_audit=['5+6 m continuous beam; q=12 on both spans; 18 kN at x=7; observation x=8; no right-support or observation-coordinate leak in turn 1.'])


def build_016():
    m = chain([0, 4, 7.5, 11], {0: PIN, 4: ROLLER, 11: ROLLER}, ['B1', 'B2', 'B2'])
    m['sections'].append(proportional_section('B2', 1., .6))
    udl(m, 10)
    load(m, id='long-span-point', type='nodal', node='n2', fz=-30)
    visible = deepcopy(m)
    visible['load_cases'][0]['loads'][-1] = dict(id='long-span-point', type='point', span='second (long) span',
        distanceM=3.5, coordinateOrigin=None, measurementDirection=None, reference_frame='global', fz=-30)
    turns = [
        turn('Model the attached continuous beam with spans 4 m and 7 m. Both spans carry 10 kN/m downward; a downward 30 kN point force is located at "3.5 m within the long span" without a stated coordinate origin or measurement direction. The first span is B1 and the second B2. Request Uz at the long-span midpoint x=7.5 m and Rz at the middle support. Clarify the position convention if it is not uniquely determined; if you infer it uniquely, state the basis explicitly.', None, 'clarify', ['input-t1.txt'], ['longSpanPoint.coordinateOrigin', 'longSpanPoint.measurementDirection'], ['From which point and in which direction is the stated 3.5 m measured?'],
             clarificationPolicy='Source grading also permits direct analysis with a uniquely justified inference; the long-span midpoint query alone does not specify the point-load position.'),
        turn('The point-load distance is measured 3.5 m to the right from the middle support at x=4 m, giving global x=7.5 m. Analyze and report signed Uz at x=7.5 m and Rz at x=4 m with direction, units, D case and turn 2. Preserve B1 on the 4 m first span and B2 on the 7 m second span, as well as the full-beam 10 kN/m load.', 1)
    ]
    return write_case('INT-016', [m], turns, [requested('n2', 'n1')],
                      {'input-t1.txt': appendix(visible, 'en', 'B2 has the same A as B1 and 0.6 times both Iy and Iz; its explicitly completed J is 0.6 times B1. The point-load location is not linked to any observation node until the distance convention is resolved.')},
                      decisions=decision('B2 source ratios are exact; unspecified J is frozen at 0.6 times B1.', 'Source ambiguity: both end-based 3.5 m interpretations of a 7 m span coincide at its midpoint, but the source does not limit the possible origin/direction to span ends. A uniquely justified inference remains acceptable under the source grading policy.'),
                      source_audit=['Supports 0,4,11 m; second-span force30 at x7.5 after clarification; sections B1/B2 with I ratio0.6 and unchanged A.'])


def build_017():
    m = chain([0, 4, 6.5, 9, 13], {0: PIN, 4: ROLLER, 9: ROLLER, 13: ROLLER})
    udl(m, 15, ['b2', 'b3', 'b4'])
    visible = deepcopy(m)
    visible['nodes'][-1]['x'] = None
    visible['enteredSpanLengthsM'] = [4, 5, -4]
    visible['nodes'][-1]['coordinateStatus'] = '第三跨长度录入为-4 m，右端坐标暂不可确定'
    turns = [
        turn('三跨连续梁的跨度按从左到右录入为4 m、5 m、-4 m，左铰其余支座竖向滚支。首跨无均布荷载，中跨及末跨各向下15 kN/m。属性见附件。求中跨中点x=6.5 m的Uz及x=4 m支座Rz。请核对输入并处理必要问题。', None, 'clarify', ['input-t1.txt'], ['geometry.thirdSpanLengthM'], ['第三跨录入-4 m为无效长度；请确认正确的正跨度。']),
        turn('第三跨-4 m是录入笔误，正确长度为4 m，支座为x=0、4、9、13 m。请分析并报告中跨中点x=6.5 m的Uz及x=4 m支座Rz，注明方向、单位、D工况和第2轮。首跨仍无均布载，仅中、末两跨各15 kN/m，梁在中间支座处连续。', 1)
    ]
    return write_case('INT-017', [m], turns, [requested('n2', 'n1')],
                      {'input-t1.txt': appendix(visible, 'zh', '录入跨度按从左到右列出；右端坐标null表示不能由无效长度生成有效几何。不得自动取绝对值。')},
                      decisions=decision('Invalid negative third-span input is retained in turn 1; the final right-support coordinate is withheld until correction.', 'No distributed load is assigned to the first span in any valid state.'),
                      source_audit=['4+5+4 m; source t1 -4 is explicit invalid input; q15 only x4..13; observation6.5 support4.'])


def build_018():
    m = chain([0, 5, 8.5, 12], {0: PIN, 5: ROLLER, 12: ROLLER})
    udl(m, 16, ['b1'])
    load(m, id='middle-support-point', type='nodal', node='n1', fz=-25)
    turns = [turn('Analyze the complete two-span beam in the attachment: spans 5 m and 7 m, left pin and vertical rollers at x=5 and 12 m. Only the first span carries 16 kN/m downward. The middle support at x=5 m also receives a downward 25 kN nodal force in the same D case. The second span exists, is continuous through the middle support, and has exactly zero load within its span. Report signed Uz at its midpoint x=8.5 m and middle-support Rz, with location, direction, units, D case and turn 1.', 1, attachments=['input-t1.txt'])]
    return write_case('INT-018', [m], turns, [requested('n2', 'n1')],
                      {'input-t1.txt': appendix(m, 'en', 'The second span has zero externally applied span loads. This is complete input. The 25 kN force is applied exactly at the supported middle node.')},
                      decisions=decision('The zero-load second span is complete, valid input and must remain connected; it requires no clarification.'),
                      source_audit=['Single analyze turn; 5+7 m; only first q16; support node x5 receives25; x8.5 displacement.'])


def build_019():
    m = chain([0, 4, 7, 10, 14], {0: PIN, 4: ROLLER, 10: ROLLER, 14: ROLLER})
    udl(m, 8)
    load(m, id='D-middle-point', type='nodal', node='n2', fz=-20)
    udl(m, 10, ['b2', 'b3'], 'L1')
    udl(m, 10, ['b1', 'b4'], 'L2')
    m['load_combinations'] = [dict(id='C1', factors={'D': 1}), dict(id='C2', factors={'D': 1, 'L1': 1}), dict(id='C3', factors={'D': 1, 'L2': 1})]
    second = deepcopy(m)
    second['load_combinations'][1]['factors']['L1'] = 1.4
    third = deepcopy(second)
    third['load_combinations'][1]['factors']['D'] = 1.2
    turns = [
        turn('按附件建立4、6、4 m三跨连续梁。D全梁8 kN/m并在x=7 m另向下20 kN；L1仅中跨10 kN/m，L2仅两边跨各10 kN/m。初始C1=D、C2=D+L1、C3=D+L2。分析并逐组合报告x=7 m的Uz及x=4 m支座Rz，注明位置、方向、单位、组合和第1轮。', 1, attachments=['input-t1.txt']),
        turn('仅把C2中的L1系数从1改成1.4，C2现为D+1.4L1。按当前组合重新分析，并逐C1、C2、C3报告x=7 m的Uz和x=4 m支座Rz，注明第2轮及方向、单位。C1、C3和各原始工况荷载保持。', 2,
             changedFields=['/load_combinations/1/factors/L1'], preservedFields=['/nodes', '/elements', '/materials', '/sections', '/load_cases', '/analysis_control', '/load_combinations/0', '/load_combinations/2', '/load_combinations/1/factors/D']),
        turn('仅把C2中的D系数从1改成1.2，C2现为1.2D+1.4L1。按当前组合重新分析，逐C1、C2、C3报告x=7 m的Uz和x=4 m支座Rz，注明第3轮及方向、单位。原始D的8 kN/m及20 kN点力不改，L1、L2和其余组合保持。', 3,
             changedFields=['/load_combinations/1/factors/D'], preservedFields=['/nodes', '/elements', '/materials', '/sections', '/load_cases', '/analysis_control', '/load_combinations/0', '/load_combinations/2', '/load_combinations/1/factors/L1'])
    ]
    qq = [q for c in ['C1', 'C2', 'C3'] for q in requested('n2', 'n1', c, 'combination')]
    return write_case('INT-019', [m, second, third], turns, [deepcopy(qq) for _ in range(3)],
                      {'input-t1.txt': appendix(m, 'zh', '工况D、L1、L2独立保存。组合为原始工况响应的线性组合；修改组合系数不能覆盖原始载荷强度。')},
                      decisions=decision('Connected observation at x=7 m is also the D-only 20 kN nodal load location.', 'All three named combinations are requested in every state, including unchanged C1 and C3.'),
                      source_audit=['C1=D; C3=D+L2 invariant; C2 D+L1 to D+1.4L1 to1.2D+1.4L1; D point20 preserved only in D.'])


def build_020():
    m = chain([0, 3, 8, 11.5, 15], {0: PIN, 3: ROLLER, 8: ROLLER, 15: ROLLER}, ['B1', 'B2', 'B1', 'B1'])
    m['sections'].append(proportional_section('B2', 1., 1.5))
    udl(m, 8, ['b1'])
    udl(m, 10, ['b2'])
    udl(m, 12, ['b3', 'b4'])
    visible = deepcopy(m)
    visible['loadScheduleConflict'] = {'narrativeThirdSpanLoadKNPerM': 8, 'tableLoadsLeftToRightKNPerM': [8, 10, 12], 'authority': None}
    turns = [
        turn('Model the continuous beam with spans 3 m, 5 m and 7 m from left to right, and sections B1/B2/B1 respectively. The narrative says that the third-span downward load is 8 kN/m, while the attached load table lists 8, 10 and 12 kN/m from left to right. Request Uz at the third-span midpoint x=11.5 m and Rz at the support x=8 m. Resolve the conflicting load records before reporting numerical results.', None, 'clarify', ['input-t1.txt'], ['thirdSpan.uniformLoad'], ['Should the third-span load follow the narrative 8 kN/m or the table 12 kN/m?']),
        turn('Use the table: the downward uniform loads from left to right are 8, 10 and 12 kN/m on spans 3, 5 and 7 m respectively. Analyze and report signed Uz at x=11.5 m and support Rz at x=8 m, with location, direction, units, D case and turn 2. Preserve the span order and B1/B2/B1 section assignment.', 1)
    ]
    return write_case('INT-020', [m], turns, [requested('n3', 'n2')],
                      {'input-t1.txt': appendix(visible, 'en', 'The load_cases table is one of two conflicting input records. Its authority is not yet confirmed. B2 on the middle 5 m span has 1.5 times both B1 bending inertias; A remains equal, and its completed J is 1.5 times B1.')},
                      decisions=decision('Source supplies B2 Iy/Iz ratio1.5; unspecified A is frozen equal to B1 and J at1.5 times B1.', 'Turn1 exposes both conflicting loads without selecting either; turn2 confirms table authority.'),
                      source_audit=['3+5+7 m increasing spans, supports0,3,8,15; B2 only middle span; q8/10/12 after source clarification.'])


def validate_authored():
    """Check relationships with independent source facts, plus all public/state links."""
    stats = {'cases': 0, 'states': 0, 'turns': 0, 'quantities': 0}
    for number in range(11, 21):
        folder = ROOT / 'corpora/research-300/cases' / f'INT-{number:03d}'
        c = json.loads((folder / 'contract.json').read_text())
        rr = json.loads((folder / 'reference-requests.json').read_text())
        assert len(c['turns']) == c['sourceMetadata']['task']['turns']
        assert {r['id'] for r in c['sourceMetadata']['requirements']} == {rid for row in c['requirementCoverage'] for rid in row['requirementIds']}
        assert all(t['expectation'] != 'clarify' or t['state'] is None for t in c['turns'])
        for t in c['turns']:
            assert all(p in c['attachments'] and (folder / p).is_file() for p in t['attachments'])
        for state in rr['states']:
            m = json.loads((folder / state['model']).read_text())
            ns = {n['id']: n for n in m['nodes']}
            es = {e['id']: e for e in m['elements']}
            assert len(ns) == len(m['nodes']) and len(es) == len(m['elements'])
            assert all(math.dist([ns[e['nodes'][0]][k] for k in ('x','y','z')], [ns[e['nodes'][1]][k] for k in ('x','y','z')]) > 0 for e in es.values())
            assert all(e['material'] in {x['id'] for x in m['materials']} and e['section'] in {x['id'] for x in m['sections']} for e in es.values())
            assert all(n['id'] in {j for e in es.values() for j in e['nodes']} for n in ns.values())
            assert m['schema_version'] == '2.2.0' and not m['analysis_control']['self_weight']
            assert len({q['id'] for q in state['quantities']}) == len(state['quantities'])
            for q in state['quantities']:
                assert 'value' not in q and q['location']['id'] in ns
                assert q['selection']['id'] in {x['id'] for x in m['load_cases' if q['selection']['kind']=='case' else 'load_combinations']}
                if q['component'] == 'uz':
                    assert not ns[q['location']['id']]['restraints'][2]
                if q['component'] == 'Fz':
                    assert ns[q['location']['id']]['restraints'][2]
            stats['quantities'] += len(state['quantities'])
        if c['locale'] == 'en':
            for p in ['prompt.txt', *c['attachments']]:
                assert not any('\u4e00' <= ch <= '\u9fff' for ch in (folder / p).read_text()), (c['id'], p)
            assert all(not any('\u4e00' <= ch <= '\u9fff' for ch in t['instruction']) for t in c['turns'])
        stats['cases'] += 1
        stats['states'] += len(rr['states'])
        stats['turns'] += len(c['turns'])
    # Source-prescribed state edits must change only the specific target fields.
    for number, allowed in [(12, {'/load_cases/0/loads/0/fz'}), (13, {'/sections/3', '/elements/1/section', '/elements/2/section'}), (14, {'/load_cases/0/loads/4/fz'}), (19, {'/load_combinations/1/factors/L1', '/load_combinations/1/factors/D'})]:
        folder = ROOT / 'corpora/research-300/cases' / f'INT-{number:03d}'
        states = [json.loads((folder / p).read_text()) for p in json.loads((folder / 'contract.json').read_text())['modelStates']]
        for a, b in zip(states, states[1:]):
            assert set(diff_paths(a, b)) <= allowed
    # Incomplete-span public input must not disclose either missing result coordinate.
    text = (ROOT / 'corpora/research-300/cases/INT-015/input-t1.txt').read_text()
    public = json.loads(text[text.index('{'):])
    assert public['geometry']['secondSpanLengthM'] is None
    assert public['geometry']['supports'][-1]['x'] == '5 + secondSpanLengthM'
    # Source-specific reaction-bearing support loads stay exactly at their supports.
    for number, load_id, node_id, force in [(13, 'left-support-point', 'n0', -15), (18, 'middle-support-point', 'n1', -25)]:
        m = json.loads((ROOT / f'corpora/research-300/cases/INT-{number:03d}/model-state-1.json').read_text())
        p = next(p for p in m['load_cases'][0]['loads'] if p['id'] == load_id)
        assert p['node'] == node_id and p['fz'] == force
        assert next(n for n in m['nodes'] if n['id'] == node_id)['restraints'][2]
    # Independently integrated load resultants about the global origin, from source numbers.
    expected = {
        11: [[(0, -90, 345)]], 12: [[(8, -20, 84)], [(8, -25, 99)]],
        13: [[(0, -123, 486)], [(0, -123, 486)]],
        14: [[(0, -79, 412)], [(0, -89, 472)]],
        15: [[(0, -150, 852)]], 16: [[(0, -140, 830)]],
        17: [[(0, -135, 1147.5)]], 18: [[(0, -105, 325)]],
        19: [[(0, -132, 924), (0, -60, 420), (0, -80, 560)]] * 3,
        20: [[(0, -158, 1277)]]}
    for number, state_resultants in expected.items():
        for state_index, case_resultants in enumerate(state_resultants, 1):
            m = json.loads((ROOT / f'corpora/research-300/cases/INT-{number:03d}/model-state-{state_index}.json').read_text())
            ns = {n['id']: n for n in m['nodes']}
            es = {e['id']: e for e in m['elements']}
            for lc, wanted in zip(m['load_cases'], case_resultants):
                resultant = [0., 0., 0.]
                for p in lc['loads']:
                    if p['type'] == 'nodal':
                        n = ns[p['node']]
                        fx, fz = p.get('fx', 0), p.get('fz', 0)
                        moment = n['z']*fx - n['x']*fz + p.get('my', 0)
                    else:
                        a, b = (ns[n] for n in es[p['element']]['nodes'])
                        length = math.dist([a[k] for k in ('x','y','z')], [b[k] for k in ('x','y','z')])
                        fx, fz = p.get('wx', 0)*length, p.get('wz', 0)*length
                        moment = (a['z']+b['z'])/2*fx - (a['x']+b['x'])/2*fz
                    resultant = [v+w for v,w in zip(resultant, (fx,fz,moment))]
                assert all(math.isclose(a,b,abs_tol=1e-10) for a,b in zip(resultant,wanted)), (number,state_index,lc['id'],resultant,wanted)
    print(json.dumps(stats, sort_keys=True))


def diff_paths(a, b, path=''):
    if type(a) is not type(b):
        return [path]
    if isinstance(a, dict):
        out = []
        for key in a.keys() | b.keys():
            out += [path+'/'+key] if key not in a or key not in b else diff_paths(a[key], b[key], path+'/'+key)
        return out
    if isinstance(a, list):
        return [p for i in range(max(len(a), len(b))) for p in ([path+'/'+str(i)] if i >= min(len(a), len(b)) else diff_paths(a[i], b[i], path+'/'+str(i)))]
    return [] if a == b else [path]


if __name__ == '__main__':
    for number in range(11, 21):
        globals()[f'build_{number:03d}']()
    validate_authored()
