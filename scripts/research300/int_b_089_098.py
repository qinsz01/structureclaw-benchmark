"""Deterministic source-faithful INT-089..098 candidate authoring; no truth values."""
from copy import deepcopy
import json
from int_b_common import (ROOT, P, model, node, elem, load, section, spatial,
                          public_input, turn, quantities, emit)


def props(m, columns=None):
    """Explicit missing appendix choices, never inferred software defaults."""
    m['sections'] = [section('BX', .30, .60), section('BY', .30, .50)] + (columns or [section('C1', .40, .50)])
    for e in m['elements']:
        e['section'] = 'C1' if e['type'] == 'column' else ('BX' if e['id'].startswith('x') else 'BY')
    return m


def grid(xs, ys, levels=(3.6, 7.2)):
    return props(spatial(xs, ys, list(levels), concrete=True))


def udl(m, q, case='D', ids=None):
    for e in m['elements']:
        if e['type'] == 'beam' and (ids is None or e['id'] in ids):
            load(m, case, type='distributed', element=e['id'], wz=-q, id=f'{case}-{e["id"]}')


def requests(states, top, base, components=None):
    return [dict(state=i, model=f'model-state-{i}.json', quantities=quantities(m, top=top, base=base, components=components), derived=[])
            for i, m in enumerate(states, 1)]


def target_en(top, base):
    return f'Report global Ux, Uz and Uy at {top}, and global support My and Rz (=Fz) at {base}, for every listed case and combination.'


def target_zh(top, base):
    return f'逐工况及组合报告最高层最右且Y最大的梁柱节点{top}的全局Ux、Uz、Uy，以及最左首层柱底{base}的全局My、Rz（即Fz）。'


def standard_notes(*items):
    return ['Read the exact task row, model row and all numbered planning requirements before authoring.',
            'Missing material appendix is explicitly completed: C35 E=31500 MPa, nu=0.2, G=13125 MPa, rho=2500 kg/m3 for concrete frames/columns unless a case says steel. All A/Iy/Iz/J and dimensions are public explicit inputs.',
            'Standard rectangles use B along local y and H along local z. The frozen Saint-Venant J approximation is the representative primitive formula. Explicit section properties govern.',
            'All model/result acceptance gates remain pending. No native execution, independent numerical truth, or LLM trial is claimed.'] + list(items)


def case089():
    cols = [section('C1', .45, .45), section('C2', .40, .50), section('C3', .50, .50), section('C4', .45, .60)]
    m = props(spatial([0, 6, 12], [0, 5, 10], [3.6, 7.2], concrete=True), cols)
    groups = {'corner': [], 'edge_non_corner': [], 'interior': []}
    for e in m['elements']:
        if e['type'] != 'column':
            continue
        ix, iy, _ = map(int, e['id'][1:].split('-'))
        nedge = int(ix in (0, 2)) + int(iy in (0, 2))
        group = ('interior', 'edge_non_corner', 'corner')[nedge]
        e['section'] = {'corner': 'C1', 'edge_non_corner': 'C2', 'interior': 'C3'}[group]
        groups[group].append(e['id'])
    for n in m['nodes']:
        if n['id'] in ('n0-0-0', 'n2-2-0'):
            n['restraints'] = [True]*3 + [False]*3
    udl(m, 8)
    b = deepcopy(m)
    for e in b['elements']:
        if e['id'] in groups['edge_non_corner']:
            e['section'] = 'C4'
    aim = target_zh('n2-2-2 (12,10,7.2)m', 'n0-0-0 (0,0,0)m')
    emit('INT-089', [m, b], [
        turn('按完整附件建立两层2×2跨空间框架并用PKPM分析。角柱C1、非角边柱C2、中柱C3，X梁BX、Y梁BY。仅两个对角柱脚n0-0-0、n2-2-0三平移固定、三转动自由。'+aim, 1, attachments=['input.json']),
        turn('把周边柱都换为C4，但角柱不动。请先核实这一构件组指代，其他字段保持。', None, 'clarify', unresolved=['column_group_to_change'], questions=['“周边柱都换”是否仅指非角边柱，角柱与中柱均保持原截面？'], priorState=1),
        turn('确认仅非角边柱改C4；角柱、中柱及所有梁保持，两个对角铰脚约束也保持。更新后重新分析。'+aim, 2)
    ], {'input.json': public_input(m, columnGroups=groups, appendixDecision='C1=corner, C2=edge excluding corners, C3=interior, C4=replacement section; all are explicit elastic sections.')},
         standard_notes('Exactly 27 nodes, 18 columns and 24 beams. Corner/edge/interior membership is geometric on every storey; only eight edge columns change to C4.',
                        'T2 is a later clarification: prior analyzed state 1 remains valid but no new changed state is accepted before T3.',
                        'Leftmost base tie is frozen at X=0,Y=0. Its My is a requested released-support component; preserve the request even if zero.',
                        'PKPM native member-load, explicit section/axis/hinge mapping and native support-reaction access are pending, not accepted.'), requests([m, b], 'n2-2-2', 'n0-0-0'))


def case091():
    m = grid([0, 6, 12], [0, 5, 10])
    region_a = ['x0-0-2', 'x0-1-2', 'y0-0-2', 'y1-0-2']
    region_b = ['x1-0-2', 'x1-1-2', 'y1-0-2', 'y2-0-2']
    udl(m, 6)
    udl(m, 4, 'L', region_a)
    load(m, 'W', id='W-edge', type='nodal', node='n2-0-2', fy=-9)
    m['load_combinations'] = [dict(id='TOTAL', factors={'D': 1, 'L': 1, 'W': 1})]
    b = deepcopy(m)
    next(c for c in b['load_cases'] if c['id'] == 'L')['loads'] = []
    udl(b, 4, 'L', region_b)
    aim = target_zh('n2-2-2 (12,10,7.2)m', 'n0-0-0 (0,0,0)m')
    emit('INT-091', [m, b], [
        turn('用YJK建立附件两层框架。D全梁向下6kN/m；L初始位于二层西南格区域A，四条边梁各向下4kN/m；W在n2-0-2沿全局-Y施加9kN。组合TOTAL=D+L+W。'+aim, 1, attachments=['input.json', 'regions.json']),
        turn('将L从区域A整体移动到东南格区域B，严格按regions.json的B梁ID表施加同样4kN/m向下线载。删除旧A独有边上的L，共享边只保留一次L。D、W及组合系数保持。重新分析。'+aim, 2)
    ], {'input.json': public_input(m), 'regions.json': {'units': 'm; kN/m of actual member length', 'A': {'z': 7.2, 'xRange': [0, 6], 'yRange': [0, 5], 'beamIds': region_a}, 'B': {'z': 7.2, 'xRange': [6, 12], 'yRange': [0, 5], 'beamIds': region_b}, 'sharedBeam': 'y1-0-2', 'distribution': 'Each listed boundary beam receives wz=-4 exactly once; these are line loads, not floor pressure.'}},
         standard_notes('D is present on all 24 floor beams. Each region contains exactly four beams; shared beam y1-0-2 occurs once in each L state.',
                        'Roof edge W is a distinct case at (12,0,7.2), fy=-9 kN. It is identical before and after relocation.',
                        'Independent raw D/L/W cases and TOTAL combination are requested, retaining load identity.',
                        'YJK arbitrary member loads, regional update, explicit analysis settings and reaction mapping remain pending native gates.'), requests([m, b], 'n2-2-2', 'n0-0-0'))


def case092():
    m = model('3d', concrete=True)
    m['sections'] = [section('BX', .30, .60), section('BY', .30, .50), section('C1', .40, .50)]
    for ix, x in enumerate([0, 6, 12]):
        for iy, y in enumerate([0, 5]):
            if (ix, iy) != (1, 0):
                node(m, f'n{ix}-{iy}-0', x, 0, y, [True]*6)
            node(m, f'n{ix}-{iy}-1', x, 6 if iy == 0 else 8, y)
            if (ix, iy) != (1, 0):
                elem(m, f'c{ix}-{iy}-1', f'n{ix}-{iy}-0', f'n{ix}-{iy}-1', 'column', 'C1')
    for ix in range(3):
        elem(m, f'y{ix}-0-1', f'n{ix}-0-1', f'n{ix}-1-1', sec='BY')
        if ix < 2:
            for iy in range(2):
                elem(m, f'x{ix}-{iy}-1', f'n{ix}-{iy}-1', f'n{ix+1}-{iy}-1', sec='BX')
    slopes = [f'y{i}-0-1' for i in range(3)]
    udl(m, 5, ids=slopes)
    b = deepcopy(m)
    for n in b['nodes']:
        if n['y'] == 5 and n['z'] == 8:
            n['z'] = 9
    aim = target_en('n2-1-1 (12,5,roof-high-Z) m', 'n0-0-0 (0,0,0) m')
    emit('INT-092', [m, b], [
        turn('Build and analyze the attached sloped-roof frame in YJK. Low roof edge Y=0 is Z=6 m; high edge Y=5 is Z=8 m. The front middle column at X=6,Y=0 is absent; its roof joint connects both neighboring X beams and its sloped Y beam. Apply global -Z 5 kN/m to each of the three sloped Y beams per actual member length. '+aim, 1, attachments=['input.json']),
        turn('Raise only the high roof edge at Y=5 from Z=8 m to Z=9 m. Keep the low edge at 6 m and keep the front middle column absent. All connected member endpoints follow their shared roof joints. Keep the original global downward line intensity 5 kN/m per actual sloped length, then reanalyze. '+aim, 2)
    ], {'input.json': public_input(m, roofLoadMembers=slopes, loadBasis='Global -Z 5 kN/m of actual member length on the three sloping Y beams; X roof edge beams have no added line load.', missingColumn={'x': 6, 'y': 0, 'roofJoint': 'n1-0-1'})},
         standard_notes('Source says actual sloped beams carry 5 kN/m. This appendix applies that load to all three sloped Y beams; horizontal X beams are not described as loaded. Interpretation is frozen before candidate runs and awaits blind source review.',
                        'There are five column bases, six roof nodes, five columns, four X beams and three sloped Y beams. No isolated base node is retained under the missing column.',
                        'All three high-side roof node elevations change; distributed load vectors and intensities remain byte-identical. Their resultant changes because physical lengths change.',
                        'YJK arbitrary/sloped member geometry, missing column and actual-length global load mapping remain unverified native capabilities.'), requests([m, b], 'n2-1-1', 'n0-0-0'))


def case090():
    m = grid([0, 6], [0, 5, 10])
    for e in m['elements']:
        if e['id'] in ('c0-0-1', 'c0-0-2'):
            e['rotation_angle'] = 90
    udl(m, 8)
    load(m, id='roof-X', type='nodal', node='n1-2-2', fx=15)
    load(m, id='roof-Y', type='nodal', node='n1-2-2', fy=10)
    load(m, id='roof-torque', type='nodal', node='n1-2-2', mz=8)
    b = deepcopy(m)
    next(e for e in b['elements'] if e['id'] == 'c0-0-1')['rotation_angle'] = 0
    c = deepcopy(b)
    next(l for l in c['load_cases'][0]['loads'] if l['id'] == 'roof-Y')['fy'] = 11
    aim = target_en('n1-2-2 (6,10,7.2) m', 'n0-0-0 (0,0,0) m')
    emit('INT-090', [m, b, c], [
        turn('Build the attached two-storey 1 by 2 bay frame in OpenSees. All columns have asymmetric 400 by 500 mm rectangular sections. Both (0,0) column segments initially have a 90-degree local section roll. Roof loads are global Fx=15 kN, Fy=10 kN and Mz=+8 kN.m at (6,10,7.2); all beams carry downward 8 kN/m. '+aim, 1, attachments=['input.json']),
        turn('Remove the 90-degree local-axis roll only from first-storey column c0-0-1 at X=Y=0, Z=0 to 3.6 m. Its roll is now zero. Keep the upper segment and every other column orientation unchanged; preserve all global load vectors including the +8 kN.m Z torque. Reanalyze. '+aim, 2),
        turn('Increase only the global Y lateral-force group by 10%, so roof-Y becomes Fy=+11 kN. Preserve the current local axes, Fx=15 kN, Mz=+8 kN.m and beam loads. Reanalyze. '+aim, 3)
    ], {'input.json': public_input(m, lateralLoadGroup={'X': ['roof-X'], 'Y': ['roof-Y']}, appendixDecision='The stated roof-right-edge lateral forces act at the specified outer corner (6,10,7.2), shared with the specified torque.')},
         standard_notes('Only first-storey (0,0) segment roll changes in state 2; upper segment remains 90 degrees. State 3 only changes roof-Y fy=10 to 11.',
                        'The specified roof-right-edge lateral force location is completed at the explicitly named torque corner, not distributed over multiple nodes. All loads are global vectors, independent of member section roll.'), requests([m, b, c], 'n1-2-2', 'n0-0-0'))


def case093():
    m = grid([0, 6], [0, 5])
    b1 = section('B1', .30, .60)
    b2 = {'id': 'B2', 'name': 'B2', 'type': 'general', 'properties': deepcopy(b1['properties'])}
    b2['properties']['Iy'] *= 1.5
    b2['properties']['Iz'] *= 1.5
    m['sections'] = [b1, b2, section('C1', .40, .50), section('A1', .10, .10)]
    for e in m['elements']:
        if e['type'] == 'beam':
            e['section'] = 'B2' if e['id'].startswith('x0-0-') else 'B1'
    m['materials'].append(dict(id='M2', name='Q355', type='steel', E=206000, nu=.3, G=206000/2.6, rho=7850))
    elem(m, 'brace1', 'n0-0-0', 'n1-0-1', 'truss', 'A1')
    elem(m, 'brace2', 'n1-0-0', 'n0-0-1', 'truss', 'A1')
    for e in m['elements']:
        if e['type'] == 'truss':
            e['material'] = 'M2'
    udl(m, 6)
    load(m, id='roof-lateral', type='nodal', node='n1-1-2', fx=12, fy=9)
    initial = public_input(m)
    initial['elements'] = [e for e in initial['elements'] if e['type'] != 'truss']
    for name in ['brace1', 'brace2']:
        del initial['metadata']['elementReferenceVectors'][name]
    initial['unresolvedBracing'] = {'description': 'Two axial-only first-storey crossing braces on the left elevation; observer viewpoint unspecified. No node at their crossing.', 'material': 'M2', 'section': 'A1', 'endpoints': None}
    aim = target_zh('n1-1-2 (6,5,7.2)m', 'n0-0-0 (0,0,0)m')
    emit('INT-093', [m], [
        turn('附件为两层1×1跨空间框架，左侧立面首层设两根只受轴力的交叉斜撑，交点不连接；观察方向尚未提供。Y=0立面两层梁为加强B2，其余梁B1。请先确定斜撑实际立面；确认后用OpenSees分析。'+aim, None, 'clarify', attachments=['input.json'], unresolved=['brace_elevation', 'brace_end_node_ids'], questions=['“左侧”指哪个全局坐标立面？请给两根斜撑的端点节点ID。']),
        turn('确认斜撑仅在Y=0立面首层：brace1连接n0-0-0与n1-0-1，brace2连接n1-0-0与n0-0-1；交叉处不相连。按补充表建轴力单元，其他三面无斜撑；原梁截面与全局侧力保持。现在分析。'+aim, 1, attachments=['bracing.json'])
    ], {'input.json': initial, 'bracing.json': {'elements': [e for e in m['elements'] if e['type'] == 'truss'], 'referenceVectors': {k: v for k, v in m['metadata']['elementReferenceVectors'].items() if k.startswith('brace')}, 'intersectionConnection': False}},
         standard_notes('B2 is an explicitly generalized elastic section: same A and J as B1, Iy and Iz each exactly 1.5 times B1; no incompatible rectangular shape is asserted for B2.',
                        'Initial input includes the concrete frame and steel brace properties but removes both brace connectivities and their reference vectors. B2 at Y=0 is not stated to imply brace placement.',
                        'Source permits supported deduction if existing information uniquely resolves a missing item. Here observer direction is absent and no equivalence between strengthened beams and bracing location is asserted, so T1 clarification is expected.'), requests([m], 'n1-1-2', 'n0-0-0'))


def case094():
    m = grid([0, 4, 10], [0, -5], [3.5, 7])
    udl(m, 6)
    load(m, id='roof-force', type='nodal', node='n2-1-2', fx=12)
    load(m, id='equipment-moment', type='nodal', node='n2-1-2', mz=6)
    p = public_input(m)
    source_nodes = [{'id': n['id'], 'Xs': n['x'], 'Ys': n['z'], 'Zs': -n['y'], 'sourceRestraints': n['restraints']} for n in m['nodes']]
    source_loads = []
    for l in m['load_cases'][0]['loads']:
        d = {k: deepcopy(v) for k, v in l.items() if k not in ['reference_frame', 'fx', 'fy', 'fz', 'mx', 'my', 'mz', 'wx', 'wy', 'wz']}
        if l['type'] == 'distributed':
            d['wYs'] = -6
        elif l['id'] == 'roof-force':
            d['FXs'] = 12
        else:
            d['MYs'] = 6
        source_loads.append(d)
    initial = {'units': p['units'], 'sourceCoordinateSystem': {'verticalAxis': 'Ys', 'sourceDOFOrder': ['uXs', 'uYs', 'uZs', 'rXs', 'rYs', 'rZs'], 'mappingToGlobal': {'Xg': 'Xs', 'Yg': 'SIGN * Zs', 'Zg': 'Ys'}, 'SIGN': None},
               'nodes': source_nodes, 'elements': m['elements'], 'materials': m['materials'], 'sections': m['sections'],
               'load_cases': [{'id': 'D', 'type': 'dead', 'loads': source_loads}], 'load_combinations': [], 'analysis_control': m['analysis_control'], 'analysisMethod': p['analysisMethod'],
               'sourceReferenceVectors': {e['id']: ([1, 0, 0] if e['type'] == 'column' else [0, 1, 0]) for e in m['elements']},
               'localAxes': 'Transform the source reference vector and each i-to-j member vector with the confirmed mapping; local x=i-to-j, local y=normalize(reference cross x), local z=x cross y; all section rolls zero.',
               'sourceLoadPlacement': 'The roof force and equipment moment act at source (Xs,Ys,Zs)=(10,7,5) m. The moment is about +Ys, not +Zs.',
               'outputLocations': 'Roof joint: largest global Z, then largest global X, then largest global Y. Base: source origin (0,0,0), on the leftmost column line.'}
    # source all-fixed / all-free restraints are invariant under every axis permutation.
    aim = 'Report global Ux, Uz and Uy at the highest roof beam-column joint with largest X and then largest Y; report global support My and Rz at the source-origin column base.'
    emit('INT-094', [m], [
        turn('Use OpenSees for the attached two-storey source-coordinate frame. Source Y is vertical. The conversion is Xg=Xs and Zg=Ys, but the sign in Yg=±Zs is missing. Confirm the mapping and local-axis interpretation before numerical reporting; transform geometry, supports, all force vectors and the equipment moment consistently. '+aim, None, 'clarify', attachments=['source-input.json'], unresolved=['source_to_global_Y_sign'], questions=['Is the remaining mapping Yg=-Zs or Yg=+Zs, and which right-handed source-to-global orientation is intended?'], acceptableAlternatives=[{'expectation': 'analyze', 'state': 1, 'condition': 'A unique right-handed mapping is established from supplied information and its derivation is explicitly stated; do not guess the missing sign.'}]),
        turn('Confirm Yg=-Zs. Use the right-handed mapping (Xg,Yg,Zg)=(Xs,-Zs,Ys); apply it to force and moment vectors and reference directions as well as node positions and restraints. Thus the source +Ys equipment moment is global +Z, 6 kN.m. Analyze the confirmed model. '+aim, 1, attachments=['mapping-confirmed.json'])
    ], {'source-input.json': initial, 'mapping-confirmed.json': {'mapping': {'Xg': 'Xs', 'Yg': '-Zs', 'Zg': 'Ys'}, 'matrix': [[1, 0, 0], [0, 0, -1], [0, 1, 0]], 'localAxes': p['axisDefinitions'], 'globalOutputNodes': {'roof': 'n2-0-2', 'base': 'n0-0-0'}}},
         standard_notes('Initial public input contains only source coordinates/vectors and unresolved SIGN; no hidden global node coordinates, completed transformation matrix, global output-node resolution or completed geometry is attached.',
                        'The source roof external corner is explicitly completed as (10,7,5). It maps to (10,-5,7), while the requested global largest-Y roof joint is (10,0,7). These are deliberately distinct.',
                        'Source initial missing-sign scenario is preserved. Its grading allowance for uniquely justified deduction is retained as an acceptableAlternative, without asserting that all missing signs require guessing.',
                        'Source base restraint permutations are immaterial because every base has all six DOFs fixed. Source reference [0,1,0] on beams becomes global [0,0,1]; vertical-column reference [1,0,0] is unchanged.'), requests([m], 'n2-0-2', 'n0-0-0'))


def column(zs, sections, dimension='2d', concrete=True):
    m = model(dimension, concrete=concrete)
    m['sections'] = sections
    for name, z in zip(['base', 'mid', 'top'], zs):
        node(m, name, 0, z, restraint=[True]*6 if name == 'base' else None)
    for i, ends in enumerate([('base', 'mid'), ('mid', 'top')]):
        elem(m, f'column{i+1}', *ends, 'column', sections[min(i, len(sections)-1)]['id'])
    return m


def case095():
    m = column([0, 2.25, 4.5], [section('C1', .4, .4)])
    load(m, id='top-compression', type='nodal', node='top', fz=-500)
    load(m, id='mid-compression', type='nodal', node='mid', fz=-100)
    initial = public_input(m)
    initial['reportedHeight'] = {'value': 0, 'unit': 'm', 'status': 'requires correction'}
    initial['nodes'][1]['z'] = 'H/2'
    initial['nodes'][2]['z'] = 'H'
    aim = '报告柱顶top的Uz、Ux及柱底base的Rz、My。'
    emit('INT-095', [m], [
        turn('建立400×400mm混凝土柱，题面总高度写为0m；柱底固定，柱顶向下500kN，连续中点节点另向下100kN，保持上下柱段连续。用OpenSees作一阶弹性分析。'+aim, None, 'clarify', attachments=['input.json'], unresolved=['valid_positive_column_height'], questions=['柱高度0m会产生零长柱段，请给出正确的正高度；中点是否继续位于总高一半？']),
        turn('确认柱总高4.5m，中点z=2.25m。截面仍400×400mm，柱顶向下500kN，中点向下100kN，柱底固定。现在完成一阶弹性分析，不追加侧力或稳定验算。'+aim, 1, attachments=['height-confirmed.json'])
    ], {'input.json': initial, 'height-confirmed.json': {'heightM': 4.5, 'midpointZM': 2.25}},
         standard_notes('No zero-length hidden model is authored. T1 specifies invalid H=0 with symbolic mid/top coordinates; neither corrected 4.5 m nor implied midpoint 2.25 m leaks into the initial attachment.',
                        'Valid hidden state has two continuous column segments; both nodal axial loads are retained. No lateral load or stability/P-delta analysis is added.'), requests([m], 'top', 'base'))


def case096():
    m = column([0, 2.1, 4.2], [section('C1', .45, .45), section('C2', .35, .45)])
    load(m, id='top-load', type='nodal', node='top', fx=30, fz=-600)
    b = deepcopy(m)
    b['load_cases'][0]['loads'][0]['fx'] = -30
    aim = 'Report global top Uz and Ux and base support Rz and My, including signed units and case D.'
    emit('INT-096', [m, b], [
        turn('Build the attached 4.2 m cantilever column in OpenSees, fixed at its base. The lower 0–2.1 m segment is 450 by 450 mm and the upper 2.1–4.2 m segment is 350 by 450 mm. Top loads are global Fx=+30 kN and Fz=-600 kN. '+aim, 1, attachments=['input.json']),
        turn('Reverse only the 30 kN X-direction load: final Fx=-30 kN; retain Fz=-600 kN. Preserve the 2.1 m section boundary, both sections, their local axes, material and total height. Reanalyze the current model using first-order elasticity. '+aim, 2)
    ], {'input.json': public_input(m, sectionAxisExplanation='Columns run from bottom to top: local x=global +Z, local y=global +Y, local z=global -X. Rectangular B is along local y; H is along local z. Upper C2 B=350 mm, H=450 mm; lower C1 B=H=450 mm.')},
         standard_notes('C35 concrete completes the source material appendix. Upper width 350 mm is along local y and height 450 mm along local z; the public axis definition makes the non-square stiffness direction explicit.',
                        'The sole state change is the top load fx component +30 to -30. Axial force, section boundary, material and restraints are preserved exactly.'), requests([m, b], 'top', 'base'))


def case097():
    # Explicit idealized HW300x300 appendix: source omits plate thicknesses/fillets.
    B, H, tw, tf = .3, .3, .01, .015
    hw = H-2*tf
    sec = {'id': 'HW300', 'name': 'HW300x300', 'type': 'i_section', 'shape': {'kind': 'i_section', 'B': 300, 'H': 300, 'tw': 10, 'tf': 15},
           'properties': {'A': 2*B*tf+hw*tw, 'Iy': (B*H**3-(B-tw)*hw**3)/12, 'Iz': (2*tf*B**3+hw*tw**3)/12, 'J': (2*B*tf**3+hw*tw**3)/3}}
    m = column([0, 2, 5], [sec], concrete=False)
    load(m, id='top-compression', type='nodal', node='top', fz=-700)
    load(m, id='mid-lateral', type='nodal', node='mid', fx=12)
    qs = quantities(m, components=[('top', 'uz'), ('top', 'ux')])
    for q in deepcopy(qs):
        q['id'] += '--mm'
        q['unit'] = 'mm'
        qs.append(q)
    reqs = [dict(state=1, model='model-state-1.json', quantities=qs, derived=[])]
    emit('INT-097', [m], [
        turn('用OpenSees建立附件5m钢柱，柱底固定，柱顶向下700kN，z=2m连续节点沿全局+X施加12kN。采用附件HW300×300完整属性。先用m报告柱顶Uz和Ux，附符号、位置和工况D。仅作一阶弹性静力分析。', 1, attachments=['input.json'], outputUnits={'uz': 'm', 'ux': 'm'}),
        turn('把同一分析状态、同一柱顶位置及工况D的Uz和Ux都改用mm表示；保留符号。仅转换输出单位，模型与荷载保持，不重复追加12kN或700kN，也不将本静力结果表述为稳定验算通过。', 1, 'query', outputUnits={'uz': 'mm', 'ux': 'mm'}, preservedFields=['/'])
    ], {'input.json': public_input(m, appendixDecision='Idealized HW300x300: B=300,H=300,tw=10,tf=15 mm, sharp corners without fillets. Explicit A/Iy/Iz/J govern; dimensions and thicknesses complete the omitted appendix. Q355 E=206000 MPa, nu=0.3, G=206000/2.6 MPa, rho=7850 kg/m3.', sectionAxisExplanation='Vertical 2D column local x=global +Z, local y=global +Y, local z=global -X; flange width B is local y and section depth H is local z.')},
         standard_notes('The source specifies HW300x300 but omits thicknesses/fillets. Author completion is the explicit idealized 300x300x10x15 mm H section, with geometric formulas and no fillet contribution; this is not an inferred library default.',
                        'Only two displacement components are requested; no extra support reaction requirement is introduced. Both m and mm requests refer to one unchanged hidden model and same case D. mm values must be converted by 1000, not rerun or relabeled.',
                        'Q355 steel is used here, not the concrete appendix. No stability acceptance is claimed.'), reqs,
         extra_outputs=[dict(id='t1-displacements-m', description='T1: top Uz and Ux in m, signed, case D, state 1.', state=1, quantityIds=[q['id'] for q in qs if q['unit']=='m'], kind='numerical'),
                        dict(id='t2-displacements-mm', description='T2: same top Uz and Ux in mm, signed, case D, same state 1; numerical values are 1000 times the m values.', state=1, quantityIds=[q['id'] for q in qs if q['unit']=='mm'], kind='numerical')])


def case098():
    sec = section('C1', .30, .50)
    m = column([0, 3, 6], [sec], dimension='3d')
    load(m, id='top-load', type='nodal', node='top', fx=20, fy=15, fz=-400)
    load(m, id='mid-lateral', type='nodal', node='mid', fx=-8)
    initial = public_input(m)
    # Preserve the contradictory table, but remove the authoritative orientation/shape.
    p = initial['sections'][0]['properties']
    p['Iy'], p['Iz'] = p['Iz'], p['Iy']
    initial['sections'][0].pop('shape')
    initial['sections'][0]['type'] = 'general'
    initial['metadata'].pop('elementReferenceVectors')
    initial['axisDefinitions'] = {'globalAxes': 'Right-handed XYZ, Z upward.', 'conflict': 'The Iy/Iz table and the local-axis annotation have interchanged labels. Which assignment and reference direction is authoritative has not yet been confirmed.', 'reactionNaming': 'Rz means vertical support reaction Fz.'}
    initial['sectionAxisAnnotation'] = {'candidateIy': sec['properties']['Iy'], 'candidateIz': sec['properties']['Iz'], 'unit': 'm4', 'authoritative': None}
    aim = 'Report top global Uz, Ux and Uy and base support Rz and My, with signed units, case D and current turn.'
    emit('INT-098', [m], [
        turn('Build the 6 m spatial cantilever column in OpenSees using the attached input. Its Iy/Iz table conflicts with the local-axis annotation: the two labels are interchanged. Confirm which table and axis orientation govern before giving numerical results. Keep the top global force (20,15,-400) kN and the separate mid-height global X force -8 kN at Z=3 m. '+aim, None, 'clarify', attachments=['input.json'], unresolved=['authoritative_Iy_Iz_assignment', 'section_local_axis_definition'], questions=['Which Iy/Iz assignment is authoritative, and what are the complete local x/y/z directions and section dimensions?']),
        turn('Use the corrected attachment. Both column segments point upward: local x=+global Z, local y=-global Y, local z=+global X, with reference vector +global X and zero roll. Rectangle B=300 mm along local y, H=500 mm along local z; use the corrected complete A/Iy/Iz/J table. Preserve all support and global load vectors and the separate -8 kN load at Z=3 m. Now analyze. '+aim, 1, attachments=['corrected-properties.json'])
    ], {'input.json': initial, 'corrected-properties.json': {'sections': m['sections'], 'referenceVectors': m['metadata']['elementReferenceVectors'], 'axes': {'localX': [0,0,1], 'localY': [0,-1,0], 'localZ': [1,0,0], 'rollDegrees': 0}, 'units': {'B': 'mm', 'H': 'mm', 'A': 'm2', 'Iy': 'm4', 'Iz': 'm4', 'J': 'm4'}}},
         standard_notes('The source omits exact non-square dimensions. The corrected appendix freezes B=300,H=500 mm and C35 material. Both distinct inertia magnitudes are visible initially as conflicting alternatives, but authoritative dimensions/orientation/reference vectors are released only in T2.',
                        'T1 is deliberately unresolved: do not average the inertias or resolve by a hidden completed section shape. T2 confirms local x=+Z,y=-Y,z=+X, consistent with representative reference-vector convention.',
                        'Top (20,15,-400) kN remains global and the -8 kN X load remains at the connected Z=3 m node.'), requests([m], 'top', 'base'))


def build():
    # Commercial cases first, as requested.
    for build_case in (case089, case091, case092, case090, case093, case094, case095, case096, case097, case098):
        build_case()


if __name__ == '__main__':
    build()
    print('Authored INT-089..098: 10 candidate cases; numerical/native gates pending.')
