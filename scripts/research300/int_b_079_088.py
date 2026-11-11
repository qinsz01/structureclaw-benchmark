"""Deterministic source-specific authoring for INT-079 through INT-088.

Produces candidate inputs only. Native execution and independent input/reference
reviews remain separate pending gates. No numerical truth is calculated.
"""
from copy import deepcopy
import json
import math
from int_b_common import (ROOT, PLAN, TASKS, spatial, node, elem, load, section,
                          public_input, turn, emit, write_json)


BASE_NOTES = [
    'Full planning, task and model rows reviewed; sourceRequirements copied without alteration.',
    'Missing appendix completion: steel M1 has E=200000 MPa, nu=0.3, G=E/[2(1+nu)], rho=7850 kg/m3; concrete C30 has E=30000 MPa, nu=0.2, G=12500 MPa, rho=2500 kg/m3. These are explicit author choices, not solver defaults.',
    'Missing section appendix completion: B1 is a solid 0.3 by 0.6 m rectangle; C1 is a solid 0.5 by 0.5 m rectangle. The complete A/Iy/Iz/J records are supplied publicly. Modified-I sections are general elastic sections with explicit properties rather than conflicting rectangle dimensions.',
    'My means global support reaction moment about Y at the leftmost first-story base; Rz means global support force Fz. Highest/rightmost/Y-largest joint is ordered by (Z,X,Y) among real column joints. These conventions are explicit publicly.',
    'Every case and every explicitly listed combination receives separate signed quantity requests. Requests contain no numerical truth values.',
    'Euler-Bernoulli linear elasticity, full actual-member-length global loads, zero self-weight, no P-delta, no rigid floor/offsets, no automatic loads or combinations. Shared contract tolerances remain frozen at absolute 1e-8 plus relative 1e-6.',
]


def grid(xs, ys, levels=(3.6, 7.2), concrete=False, **kwargs):
    m = spatial(xs, ys, list(levels), concrete=concrete, **kwargs)
    E, nu, rho = (30000, .2, 2500) if concrete else (200000, .3, 7850)
    m['materials'] = [dict(id='M1', name='C30' if concrete else 'Elastic steel',
                           type='concrete' if concrete else 'steel', E=E,
                           G=E/(2*(1+nu)), nu=nu, rho=rho)]
    m['sections'] = [section('B1', .3, .6), section('C1', .5, .5)]
    for e in m['elements']:
        if e['type'] == 'beam':
            e['section'] = 'B1'
        else:
            # The same explicit reference is used for upright and inclined columns.
            m['metadata']['elementReferenceVectors'][e['id']] = [1, 0, 0]
    return m


def scaled_section(original, new_id, scale):
    out = deepcopy(original)
    out.update(id=new_id, name=new_id, type='general')
    out.pop('shape', None)
    for key in ('Iy', 'Iz'):
        out['properties'][key] *= scale
    return out


def beam_loads(m, magnitudes, area=False, ys=None):
    """One magnitude per story; area loads are transferred only to X beams."""
    for e in m['elements']:
        if e['type'] != 'beam' or (area and not e['id'].startswith('x')):
            continue
        floor = int(e['id'].split('-')[-1])
        q = magnitudes[floor-1]
        if area:
            iy = int(e['id'].split('-')[1])
            width = (ys[iy]-ys[iy-1])/2 if iy else 0
            width += (ys[iy+1]-ys[iy])/2 if iy+1 < len(ys) else 0
            q *= width
        load(m, type='distributed', element=e['id'], wz=-q,
             id='D-'+e['id'])


def input_data(m, english=False, **extra):
    out = public_input(m, **extra)
    out['outputDefinition'] = (
        'For every listed case and combination, report Ux, Uz and Uy at the highest real beam-column joint, selecting largest X then largest Y on that level; report global support reaction My and vertical reaction Rz=Fz at the base with smallest X then smallest Y. Use signed m, kN.m and kN values, identify the node, direction, selection and current turn. Overhang free ends are not beam-column joints.'
        if english else
        '逐一报告全部明示工况及组合：最高层实际梁柱节点中先取X最大、再取Y最大的节点Ux、Uz、Uy；最底层先取X最小、再取Y最小的柱底全局支反力矩My及竖向反力Rz=Fz。采用带符号的m、kN.m、kN，标明节点、方向、工况或组合及当前轮次；外挑自由端不是梁柱节点。')
    out['executionEvidence'] = (
        'Retain the actual named-engine input/project, software version, effective settings, run ID, successful log and raw result-to-node/member/selection mapping for each changed state. A screenshot or another engine is not execution evidence. Keep original load cases and evaluate listed combinations separately.'
        if english else
        '各变更状态保存题定引擎的实际输入或原生工程、软件版本、有效设置、运行ID、成功日志以及原始结果到节点/构件/工况的映射；截屏或其他引擎结果不能替代执行证据。保留原始工况并单独执行明示组合。')
    return out


def area_rules(english=False):
    return ('Floor pressure acts globally downward. Transfer it only to X beams using the sum of adjacent Y half-spans as tributary width; Y beams receive no floor-pressure load. Do not duplicate pressure as a slab load. No rigid diaphragm.'
            if english else '楼面面载全局向下，仅按相邻Y半跨之和作为受荷宽度传给X梁；Y梁不承接该面载，不另以板面荷载重复施加，不设刚性楼板。')


def save(i, states, turns, attachments, notes):
    return emit(f'INT-{i:03d}', states, turns, attachments, BASE_NOTES+notes)


def commercial_cases():
    # INT-079: missing Y span; no initial derivative may disclose the span.
    m = grid([0, 6], [0, 5])
    m['nodes'][0]['restraints'] = [True]*3 + [False]*3
    beam_loads(m, [10, 10], area=True, ys=[0, 5])
    p = input_data(m, floorPressure=[dict(story=1, pressure=10), dict(story=2, pressure=10)],
                   floorPressureUnit='kN/m2', loadTransfer=area_rules())
    for n in p['nodes']:
        if n['y']:
            n['y'] = None
    for ld in p['load_cases'][0]['loads']:
        ld['wz'] = None
        ld['wzExpression'] = '-10 * unknown_Y_span / 2, in kN/m'
    p['unresolvedInput'] = 'Y向仅一跨，跨度未给出；远侧节点Y坐标及X梁线载应待跨度确认后生成。'
    save(79, [m], [
        turn('按附件建立双向空间框架，X向一跨6m，两层各3.6m；Y向一跨长度暂缺。角柱n0-0-0三平移固定、三转动自由，其他三柱脚固定。先核对缺项，再分析并报告附件指定结果。', None, 'clarify', ['input-t1.json'], ['/geometry/ySpan'], ['Y向一跨长度是多少？']),
        turn('确认Y向跨度为5m。补齐对应坐标和仅X梁承接的面载后，以PKPM计算当前状态并报告指定结果；角柱铰脚及其他数据保持。', 1)
    ], {'input-t1.json': p}, ['Initial Y coordinates are null and all dependent X-beam line-load magnitudes are withheld; the initial attachment never contains the completed 5 m span or 25 kN/m derivative.'])

    # INT-080: only second-story pressure missing; BX/BY grouping fixed.
    m = grid([0, 6, 12], [0, 5])
    bx = section('BX', .3, .6)
    m['sections'] = [bx, scaled_section(bx, 'BY', .6), section('C1', .5, .5)]
    for e in m['elements']:
        if e['type'] == 'beam': e['section'] = 'BX' if e['id'].startswith('x') else 'BY'
    beam_loads(m, [8, 8], area=True, ys=[0, 5])
    p = input_data(m, True, floorPressure=[dict(story=1, pressure=8), dict(story=2, pressure=None)],
                   floorPressureUnit='kN/m2', loadTransfer=area_rules(True))
    for ld in p['load_cases'][0]['loads']:
        if ld['element'].endswith('-2'):
            ld['wz'] = None
            ld['wzExpression'] = '-unknown_story_2_pressure * 2.5, in kN/m'
    save(80, [m], [
        turn('Build the attached three-dimensional frame using PKPM. Story 1 floor pressure is 8 kN/m2; story 2 pressure is unspecified. Resolve that missing magnitude, then report the specified responses. Retain the distinct BX and BY sections; the geometry determines all tributary widths.', None, 'clarify', ['input-t1.json'], ['/floorPressure/1/pressure'], ['What is the floor pressure on story 2 in kN/m2?']),
        turn('Story 2 pressure is 8 kN/m2 downward. Apply it only to the story 2 X beams using the stated tributary-width rule, then analyze and report all requested responses. Keep the first-story load and BX/BY properties.', 1)
    ], {'input-t1.json': p}, ['All second-story pressure and dependent beam-load values withheld initially; the first-story 8 kN/m2 value is not a statement of the missing roof value. BY has exactly 0.6 times BX Iy and Iz, equal A, and unchanged explicitly supplied J.'])

    # INT-081: full coordinate table conflicts with the verbal bay counts.
    m = grid([0, 6], [0, 5, 10], (3.3, 6.6, 9.9))
    beam_loads(m, [10, 10, 10], area=True, ys=[0, 5, 10])
    for iy in (0, 2):
        tip = f'tip-{iy}'
        node(m, tip, 7.2, 9.9, 5*iy)
        elem(m, f'overhang-{iy}', f'n1-{iy}-3', tip)
        load(m, type='nodal', node=tip, fz=-5, id='tip-force-'+str(iy))
    p = input_data(m, loadTransfer=area_rules(), floorPressureUnit='kN/m2', floorPressure=[10, 10, 10])
    p['verbalBayStatement'] = 'X向两跨、Y向一跨。此文字与节点坐标表不一致，尚未确认优先项。'
    save(81, [m], [
        turn('用YJK建立附件空间框架。文字说明是X向两跨、Y向一跨，但坐标表是X向一跨6m、Y向两跨各5m；两种说明尚未确认优先级。先澄清该冲突。保留三层各3.3m及屋面两根沿+X的1.2m短梁，其自由端各向下5kN。', None, 'clarify', ['input-t1.json'], ['/geometry/authoritativeBayLayout'], ['X/Y跨数应以坐标表还是文字说明为准？']),
        turn('确认以坐标表为准：X一跨6m、Y两跨各5m。保持坐标和连接、荷载方向、屋面短梁及端力，以YJK计算并报告指定结果。', 1)
    ], {'input-t1.json': p}, ['Overhang completion places the two +X arms at roof x=6,y=0 and x=6,y=10; tips x=7.2. Their only loads are the stated 5 kN downward tip forces; floor pressure acts on grid X beams. The target remains real beam-column joint n1-2-3, not a tip.'])

    # INT-082: local material grouping survives a roof-pressure edit.
    m = grid([0, 6, 12], [0, 5, 10])
    m2 = deepcopy(m['materials'][0]); m2.update(id='M2', name='Elastic steel E210000', E=210000, G=210000/2.6)
    m['materials'].append(m2)
    for e in m['elements']:
        if e['id'] in ('c0-0-1', 'c2-0-1'): e['material'] = 'M2'
    beam_loads(m, [10, 8], area=True, ys=[0, 5, 10])
    b = deepcopy(m)
    for ld in b['load_cases'][0]['loads']:
        if ld['element'].endswith('-2'): ld['wz'] *= 9/8
    p = input_data(m, True, loadTransfer=area_rules(True), floorPressureUnit='kN/m2', floorPressure=[10, 8])
    save(82, [m, b], [
        turn('Build and analyze the attached frame in PKPM. Story 1 pressure is 10 kN/m2 and story 2 pressure is 8 kN/m2. Only the two first-story corner columns on y=0, at x=0 and x=12 m, use E=210000 MPa; every other member uses E=200000 MPa. Report the specified responses.', 1, attachments=['input-t1.json']),
        turn('Replace only the story 2 floor pressure by 9 kN/m2 downward and rerun PKPM. Recompute its X-beam line loads without accumulating the old loads. Keep story 1 at 10 kN/m2, preserve both special first-story column materials, all sections, supports and topology, and report current responses.', 2)
    ], {'input-t1.json': p}, ['State 2 differs only in roof X-beam wz values. Exactly c0-0-1 and c2-0-1 retain M2; first-story middle y=0 column remains M1.'])

    # INT-083: geometry complete, analysis dimension contradictory until T2.
    m = grid([0, 6, 12], [0, 5], concrete=True)
    m['sections'].append(section('C_corner', .4, .7))
    for e in m['elements']:
        if e['id'] in ('c0-0-1', 'c0-0-2'): e['section'] = 'C_corner'
    beam_loads(m, [12, 12], area=True, ys=[0, 5])
    p = input_data(m, loadTransfer=area_rules(), floorPressureUnit='kN/m2', floorPressure=[12, 12])
    p['analysisDimensionDecision'] = None
    p['sectionOrientation'] = '角柱局部x向上、局部y沿全局-Y、局部z沿全局+X；矩形局部y向尺寸0.4m、局部z向尺寸0.7m，Iy为强轴惯性矩；其余柱为0.5m正方形。'
    save(83, [m], [
        turn('附件给出C30混凝土框架完整三轴几何，两层各3.6m、每层面载12kN/m²。我同时要求按2D平面模型和3D空间模型分析，请先澄清应采用的唯一维度，再用PKPM完成。x=0,y=0角柱各层400×700mm，其余柱500×500mm。', None, 'clarify', ['input-t1.json'], ['/analysis/dimension'], ['本题应采用2D平面还是3D空间分析？']),
        turn('确认采用唯一的3D空间模型。保留完整Y向构件、C30记录、角柱矩形强弱轴、各层12kN/m²与仅X梁受荷规则，使用PKPM计算并报告指定结果。', 1)
    ], {'input-t1.json': p}, ['Initial attachment supplies full three-axis geometry but leaves analysisDimensionDecision null; geometry dimension does not override the contradictory user analysis instruction. C_corner Iy=.4*.7^3/12 and Iz=.7*.4^3/12; its strong local y axis is global -Y.'])

    # INT-084: global C30 -> C35 material edit, separate equipment case.
    m = grid([0, 6, 12], [0, 5], concrete=True)
    beam_loads(m, [12, 10], area=True, ys=[0, 5])
    load(m, 'D_eq', type='nodal', node='n1-1-2', fz=-30, id='equipment')
    m['load_combinations'] = [dict(id='TOTAL', factors={'D': 1, 'D_eq': 1})]
    c35 = deepcopy(m['materials'][0]); c35.update(name='C35', E=31500, G=13125)
    b = deepcopy(m); b['materials'] = [c35]
    p = input_data(m, True, loadTransfer=area_rules(True), floorPressureUnit='kN/m2', floorPressure=[12, 10])
    save(84, [m, b], [
        turn('Use YJK to build and analyze the attached C30 spatial frame. Story 1 and story 2 pressures are 12 and 10 kN/m2. Keep the additional downward 30 kN force at roof node (6,5,7.2) m in the separate D_eq case. Report D, D_eq and TOTAL=D+D_eq responses as specified.', 1, attachments=['input-t1.json']),
        turn('Replace the elastic material of every beam and column with the complete C35 record in the newly attached table, then rerun YJK and report the current results. Preserve every section, floor pressure and load-transfer rule, the 30 kN equipment force, case identities and TOTAL factors.', 2, attachments=['material-t2.json'])
    ], {'input-t1.json': p, 'material-t2.json': dict(units=dict(E='MPa', G='MPa', rho='kg/m3'), material=c35)}, ['C35 appendix completion uses E=31500 MPa, G=13125 MPa, nu=.2, rho=2500 kg/m3. TOTAL is an explicit unit-factor reporting combination, documented to remove unspecified aggregate selection; D and D_eq remain separate and each is requested.'])

    # INT-086: real L-shaped graph; no northeast corner or duplicate lateral load.
    m = grid([0, 6, 12], [0, 5, 10], keep=lambda x, y, j: not (x == 2 and y == 2))
    beam_loads(m, [6, 6])
    load(m, type='nodal', node='n2-0-2', fy=12, id='eccentric-lateral')
    p = input_data(m, True)
    p['floorBoundaries'] = [dict(story=j, polygonXY=[[0,0],[12,0],[12,5],[6,5],[6,10],[0,10]], unit='m') for j in (1,2)]
    p['topologyInstruction'] = 'The northeast cell 6<X<12, 5<Y<10 and corner (12,10) do not exist. The listed nodes and members are the complete actual structure. Each actual floor beam carries only its listed 6 kN/m downward load; there is exactly one additional 12 kN global +Y roof force at (12,0,7.2) m.'
    p['targetNode'] = 'n2-1-2 at (12,5,7.2) m: select highest Z, then largest X, then largest Y among the remaining beam-column joints.'
    save(86, [m], [turn('Analyze the complete attached L-shaped frame directly in YJK. The northeast corner region is intentionally absent. Use only the supplied real nodes, columns, beams and floor boundaries. Preserve the single eccentric +Y force of 12 kN and all actual-beam gravity loads. Report Ux, Uz and Uy at n2-1-2, and global support My and Rz=Fz at n0-0-0.', 1, attachments=['input-t1.json'])], {'input-t1.json': p}, ['The remaining three-cell union has 8 nodes per elevation, 8 columns per story, and 10 real beams per floor. The missing NE corner has no nodes, columns, beams or loads. The source mentions the same 12 kN lateral force twice; it is applied exactly once. The ambiguous spatial superlative is resolved explicitly to real node (12,5,7.2), following the common (Z,X,Y) selection rule.'])

    # INT-087: author-specified missing Appendix B, independent review still pending.
    m = grid([0, 6, 12], [0, 5, 10], keep=lambda x,y,j: j < 2 or x < 2)
    c1 = next(s for s in m['sections'] if s['id'] == 'C1')
    m['sections'].append(scaled_section(c1, 'C_edge', 1.5))
    for e in m['elements']:
        if e['type'] == 'column':
            ix, iy, story = map(int, e['id'][1:].split('-'))
            if story == 1 and (ix in (0,2) or iy in (0,2)): e['section'] = 'C_edge'
    beam_loads(m, [8, 6])
    b = deepcopy(m)
    removed = {'n0-2-2', 'n1-2-2'}
    b['nodes'] = [n for n in b['nodes'] if n['id'] not in removed]
    b['elements'] = [e for e in b['elements'] if not (set(e['nodes']) & removed)]
    kept = {e['id'] for e in b['elements']}
    b['metadata']['elementReferenceVectors'] = {k:v for k,v in b['metadata']['elementReferenceVectors'].items() if k in kept}
    b['load_cases'][0]['loads'] = [ld for ld in b['load_cases'][0]['loads'] if ld['element'] in kept]
    p = input_data(m)
    p['floorBoundaries'] = [dict(story=1, polygonXY=[[0,0],[12,0],[12,10],[0,10]], unit='m'), dict(story=2, polygonXY=[[0,0],[6,0],[6,10],[0,10]], unit='m')]
    pb = input_data(b)
    pb['floorBoundaries'] = [deepcopy(p['floorBoundaries'][0]), dict(story=2, polygonXY=[[0,0],[6,0],[6,5],[0,5]], unit='m')]
    pb['changeInstruction'] = '附件B为第二轮完整替换表：仅将屋面Y上边界由10m缩至5m，删除屋面y=10两节点、接至它们的上层柱及屋面梁，并删除这些梁的6kN/m线载。首层全部节点梁柱、8kN/m线载及外边柱加强截面保持。'
    folder = save(87, [m, b], [
        turn('使用PKPM建立附件A退台框架并报告指定结果：首层2×2跨，屋面仅1×2跨；首层实际梁向下8kN/m，屋面实际梁向下6kN/m。首层全部8根外边柱采用C_edge，其Iy/Iz为C1的1.5倍且面积相同，首层中柱采用C1。', 1, attachments=['appendix-a.json']),
        turn('按本轮附件B更换上层边界和全部对应节点、梁柱、荷载分配记录，再用PKPM计算。屋面Y上边界从10m缩至5m；被删除杆件的荷载同时删除。首层模型、荷载及外边柱加强分组保持。报告当前最高最右且Y最大的实际梁柱节点及原柱底结果。', 2, attachments=['appendix-b.json'])
    ], {'appendix-a.json': p, 'appendix-b.json': pb}, ['Source Appendix B is absent. Frozen author completion changes only the roof north boundary from Y=10 m to Y=5 m; removes roof nodes n0-2-2,n1-2-2, upper columns c0-2-2,c1-2-2 and roof beams x0-2-2,y0-1-2,y1-1-2, including those beam loads. The complete replacement tables and actual load-domain polygons are public only at T2.', 'The source specifically requires independent Appendix B verification before case finalization. This has NOT occurred: candidate emission is provisional and the explicit appendix-b-independent-review gate must pass before acceptance.'])
    contract = json.loads((folder/'contract.json').read_text())
    contract['acceptanceGates'].append(dict(id='appendix-b-independent-review', status='pending', description='Independently verify the author-completed Appendix B against the source, real topology, load removal and unchanged lower-story strengthening before finalizing this candidate. The author has not performed or claimed that independent review.'))
    for coverage in contract['requirementCoverage']:
        if coverage['sourceField'] in ('task.scenario', 'task.gradingFocus'):
            coverage['targets'].append('gate:appendix-b-independent-review')
    write_json(folder/'contract.json', contract)


def opensees_cases():
    # INT-085: coordinate units missing, including all otherwise revealing heights.
    m = grid([0, 4, 11], [0, 3, 9], (3.4, 7.5), shift=lambda ix,iy,j,x,y: (4.5 if j == 2 and ix == 1 else x, y))
    beam_loads(m, [6, 6])
    p = input_data(m)
    p.pop('unit_system')
    p['units']['coordinates'] = None
    for n in p['nodes']:
        for axis in ('x','y','z'): n[axis] = round(n[axis]*1000)
    for story in p['stories']:
        story['elevation'] = round(story['elevation']*1000)
        story['height'] = round(story['height']*1000)
    p['storyCoordinateUnits'] = None
    p['unresolvedInput'] = '节点x/y/z及层高、标高数列单位未注明；所有截面属性、材料、力和线载单位已各自明确，不能据常见尺寸猜定坐标单位。连接表完整。'
    save(85, [m], [
        turn('按附件节点数列及显式梁柱连接表建立空间框架。节点表含4000、11000等数值，但坐标单位漏写；材料、截面和力单位另已给出。请只澄清坐标及层高数列单位，再用OpenSees分析并报告指定结果。保留屋面中间柱线的实际错位连接。', None, 'clarify', ['input-t1.json'], ['/units/coordinates'], ['节点坐标、标高和层高数列的长度单位是什么？']),
        turn('确认节点x/y/z、标高和层高数列全部为mm。仅这些长度数值换算成m；荷载、线载及已经SI的截面属性不再缩放。保留屋面中间柱线x=4.5m、一层x=4m形成的0.5m错位斜柱，用OpenSees计算并报告结果。', 1)
    ], {'input-t1.json': p}, ['All initial node coordinates, story elevations and heights are raw millimetre-number values without a coordinate-unit declaration; no metre-valued geometry, member length or 0.5 m shift appears initially. Material and section units remain known and are not scaled. Actual floor beams only carry 6 kN/m, including Y beams; the three inclined upper columns have no such line load.'])

    # INT-088: disjoint X/Y case edits, followed by undo of T3 only.
    m = grid([0, 6, 12], [0, 5])
    b1 = next(s for s in m['sections'] if s['id'] == 'B1')
    m['sections'].append(scaled_section(b1, 'B2', .8))
    for e in m['elements']:
        if e['type'] == 'beam' and e['id'].endswith('-2'): e['section'] = 'B2'
    beam_loads(m, [8, 8])
    for j, fx, fy in ((1,10,8), (2,15,12)):
        for iy in (0,1):
            load(m, 'W-X', type='nodal', node=f'n2-{iy}-{j}', fx=fx, id=f'WX-{iy}-{j}')
            load(m, 'W-Y', type='nodal', node=f'n2-{iy}-{j}', fy=fy, id=f'WY-{iy}-{j}')
    m['load_combinations'] = [dict(id='D', factors={'D':1}), dict(id='D+WX', factors={'D':1, 'W-X':1}), dict(id='D+WY', factors={'D':1, 'W-Y':1})]
    b = deepcopy(m)
    for c in b['load_cases']:
        if c['id'] == 'W-X':
            for ld in c['loads']: ld['fx'] *= 1.2
    c = deepcopy(b)
    for lc in c['load_cases']:
        if lc['id'] == 'W-Y':
            for ld in lc['loads']: ld['fy'] *= -1
    d = deepcopy(b)
    p = input_data(m, True)
    p['lateralForceInterpretation'] = 'Each right-edge node at x=12 m, y=0 or 5 m receives the listed force: W-X gives +10 kN per node on story 1 and +15 kN per node at the roof; W-Y gives +8 and +12 kN per node respectively. They are node forces, not whole-story totals. D as a case and D as a combination are separate selections.'
    save(88, [m,b,c,d], [
        turn('Analyze the attached three-dimensional frame in OpenSees. Keep D, W-X and W-Y as separate cases, and evaluate combinations D, D+WX and D+WY with the listed unit factors. All first-story beams use B1; all roof beams use B2 with the same area and 0.8 times B1 Iy and Iz. Report the specified responses for every case and combination.', 1, attachments=['input-t1.json']),
        turn('Increase only every W-X nodal force by 20% from its current initial value. Preserve W-Y, gravity loads, all three combination factors, materials and section groups. Rerun and report the current responses for every selection.', 2),
        turn('Reverse only every W-Y nodal force. Retain the 20% W-X increase, gravity and all combination factors and properties. Rerun and report current responses.', 3),
        turn('Undo only the immediately preceding W-Y reversal from turn 3. Keep the W-X increase from turn 2, retain gravity, combinations and section groups, and rerun the restored current state. Report every requested response.', 4)
    ], {'input-t1.json': p}, ['The underspecified right-edge lateral distribution is frozen explicitly as the stated force at each of the two x=12 m nodes per story, not a floor total. D case and D combination intentionally share the name but have distinct kind+id selection identities.', 'T2 changes only W-X fx; T3 changes only W-Y fy; T4 exactly restores the complete T2 model, with a separate state snapshot for the required fresh undo analysis.'])


def validate():
    counts = dict(cases=0, states=0, turns=0, quantities=0)
    for i in range(79,89):
        case_id = f'INT-{i:03d}'
        folder = ROOT/'corpora/research-300/cases'/case_id
        contract = json.loads((folder/'contract.json').read_text())
        refs = json.loads((folder/'reference-requests.json').read_text())
        assert contract['sourcePlan'] == PLAN[case_id]['sourceRequirements']
        assert len(contract['turns']) == TASKS[case_id]['turns']
        assert {rid for c in contract['requirementCoverage'] for rid in c['requirementIds']} == {r['id'] for r in PLAN[case_id]['requirements']}
        assert all(g['status']=='pending' for g in contract['acceptanceGates'])
        for t in contract['turns']:
            assert t['expectation'] != 'clarify' or t['state'] is None
            assert all(a in contract['attachments'] and not a.startswith('model-state-') for a in t['attachments'])
        for s, request in zip(contract['modelStates'], refs['states']):
            m = json.loads((folder/s).read_text())
            ns = {n['id']:n for n in m['nodes']}; es = {e['id']:e for e in m['elements']}
            assert len(ns) == len(m['nodes']) and len(es) == len(m['elements'])
            mats = {a['id'] for a in m['materials']}; sections = {a['id'] for a in m['sections']}
            for e in es.values():
                assert all(n in ns for n in e['nodes']) and e['material'] in mats and e['section'] in sections
                a,b = (ns[n] for n in e['nodes'])
                vec = [b[k]-a[k] for k in ('x','y','z')]
                assert sum(v*v for v in vec)>0
                ref = m['metadata']['elementReferenceVectors'][e['id']]
                cross = [ref[1]*vec[2]-ref[2]*vec[1], ref[2]*vec[0]-ref[0]*vec[2], ref[0]*vec[1]-ref[1]*vec[0]]
                assert sum(v*v for v in cross)>1e-12
            for c in m['load_cases']:
                for ld in c['loads']:
                    assert ld.get('element') in es if 'element' in ld else ld['node'] in ns
                    assert not any(v is None for v in ld.values())
            assert len({q['id'] for q in request['quantities']}) == len(request['quantities'])
            for q in request['quantities']:
                assert 'value' not in q and q['location']['id'] in ns
                candidates = m['load_cases'] if q['selection']['kind']=='case' else m['load_combinations']
                assert q['selection']['id'] in {x['id'] for x in candidates}
            counts['states'] += 1; counts['quantities'] += len(request['quantities'])
        counts['cases'] += 1; counts['turns'] += len(contract['turns'])
    print(json.dumps(counts, sort_keys=True))


if __name__ == '__main__':
    commercial_cases()
    opensees_cases()
    validate()
