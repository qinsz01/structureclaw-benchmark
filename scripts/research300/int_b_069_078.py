"""Deterministic source-specific authoring for INT-069 through INT-078.

These are explicit input appendices and interaction states, not numerical truth.
The shared emitter preserves the original planning requirements and pending gates.
"""
from copy import deepcopy
import argparse
import json
import math
import re

from int_b_common import (
    ROOT, PLAN, TASKS, MODELS, P, emit, public_input, turn, quantities,
)


def concrete(grade='C30', identifier='M1'):
    E = {'C30': 30000, 'C35': 31500, 'C40': 32500}[grade]
    return dict(id=identifier, name=grade, type='concrete', E=E,
                G=E/2.4, nu=0.2, rho=2500)


def frame(xs, levels, grade='C30'):
    m = P.frame(xs, levels, concrete=True)
    m['materials'] = [concrete(grade)]
    m['sections'] = [P.section('B1', .3, .6), P.section('C1', .5, .5)]
    # All element i-j directions and zero initial rolls are explicit.
    for e in m['elements']:
        e['rotation_angle'] = 0
    return m


def section_assign(m, predicate, sid):
    for e in m['elements']:
        if predicate(e):
            e['section'] = sid


def split_beam(m, eid, nid):
    """Insert a real connected midpoint before loads are assigned."""
    assert not any(c['loads'] for c in m['load_cases'])
    e = next(e for e in m['elements'] if e['id'] == eid)
    ns = {n['id']: n for n in m['nodes']}
    a, b = [ns[n] for n in e['nodes']]
    P.node(m, nid, (a['x']+b['x'])/2, (a['z']+b['z'])/2)
    left, right = deepcopy(e), deepcopy(e)
    left.update(id=eid+'a', nodes=[e['nodes'][0], nid])
    right.update(id=eid+'b', nodes=[nid, e['nodes'][1]])
    i = m['elements'].index(e)
    m['elements'][i:i+1] = [left, right]


def udl(m, q, predicate=lambda e: True, case='D'):
    for e in m['elements']:
        if e['type'] == 'beam' and predicate(e):
            P.load(m, case, id=f'{case}-udl-{e["id"]}', type='distributed',
                   element=e['id'], wz=-q)


def notes(*decisions):
    return dict(
        appendixDecisions=list(decisions),
        physicalConventions=[
            'XZ plane, XYZ Z-up, Euler-Bernoulli linear elasticity, rigid beam-column joints.',
            'All column bases restrain ux/uz/ry. Planar nodes restrain uy/rx/rz; supports are fully fixed.',
            'No self-weight, rigid diaphragms, rigid offsets, P-delta or construction stages.',
            'Rectangular sections use A=B*H, Iy=B*H^3/12, Iz=H*B^3/12 in metres. The explicit Saint-Venant J from the primitive is the frozen appendix value.',
            'At zero roll, local x points i-to-j, local y=global +Y, local z=x cross y. Positive roll uses the supplied right-hand local-axis transform.',
            'Rz in the source denotes vertical support force Fz; My is global support moment about +Y.',
        ],
        pending=['Independent input-blind review', 'Native OpenSees execution and adapter acceptance',
                 'Independent same-engine numerical truth', 'LLM end-to-end execution'],
    )


def output_en():
    return ('Report global Ux and Uz at the highest-storey rightmost beam-column joint, '
            'and global support My and Rz (=Fz) at the leftmost ground-level column base '
            'for every original load case and every listed combination, with signs and units.')


def output_zh():
    return '分别报告每个原始工况及每个明示组合的最高层最右梁柱节点全局Ux/Uz、最左首层柱底全局支反力矩My及竖向支反力Rz（即Fz），保留正负号和单位。'


def case069():
    m = frame([0, 6], [3.6, 7.2])
    m['sections'].append(P.section('B-roof', .3, .5))
    section_assign(m, lambda e: e['id'] == 'b0-2', 'B-roof')
    udl(m, 72)
    initial = public_input(m)
    initial['materials'][0].update(name='Concrete material; elastic modulus not supplied', E=None, G=None)
    initial['materialRelation'] = 'G=E/[2*(1+nu)]; nu=0.2. No grade-to-modulus mapping is supplied.'
    completion = dict(material=deepcopy(m['materials'][0]), relation='G=E/[2*(1+nu)]')
    turns = [
        turn('请按附件检查并分析这个两层单跨混凝土框架。材料记录的E和G均未提供，nu=0.2；请明确尚需补齐的必要信息，有唯一依据时可说明推导。'+output_zh(),
             None, 'clarify', ['input-t1.json'], unresolved=['materials.M1.E', 'materials.M1.G'],
             questions=['请给出材料弹性模量E，或可唯一确定E和G的完整弹性参数。']),
        turn('补充：该材料E=30000MPa，nu=0.2；按G=E/[2(1+nu)]取G=12500MPa。材料称C30。其他内容不改，完成分析并报告当前轮结果。'+output_zh(),
             1, attachments=['material-t2.json']),
    ]
    return emit('INT-069', [m], turns, {'input-t1.json': initial, 'material-t2.json': completion},
                notes('Source geometry: two 3.6 m storeys and one 6 m bay; columns 500x500 mm, floor-1 beam 300x600 mm, roof beam 300x500 mm, both beams 72 kN/m downward.',
                      'Initial public input removes E, G and C30 grade name; it includes no material lookup table or completed-state attachment.',
                      'Only the second turn supplies E=30000 MPa, G=12500 MPa. nu=0.2 and density=2500 kg/m3 are unchanged.'))


def case070():
    m = frame([0, 6], [3.3, 6.6, 9.9], grade='C35')
    split_beam(m, 'b0-2', 'floor2-mid')
    udl(m, 60)
    P.load(m, id='floor2-midpoint-30', type='nodal', node='floor2-mid', fz=-30)
    initial = public_input(m)
    for n in initial['nodes']:
        n['level'] = 2 if n['id'] == 'floor2-mid' else int(n['id'].split('-')[-1])
        del n['z']
    initial['storeyHeightsM'] = [3.3, -3.3, 3.3]
    initial['elevationRule'] = 'Ground level=0. Node z is the sum of storeyHeightsM through node.level; review invalid dimensions before constructing a solvable geometry.'
    initial['loadInterpretation'] = '60 kN/m downward on all three storey beams, once only. The 30 kN downward nodal load is at the middle-storey midpoint and follows that storey elevation.'
    turns = [
        turn('Build and analyze the three-storey C35 frame using the supplied height schedule. The second storey height is entered as -3.3 m. Check the dimensions and identify any necessary correction before reporting results. '+output_en(),
             None, 'clarify', ['input-t1.json'], unresolved=['storeyHeightsM[1]'],
             questions=['Is the second storey height -3.3 m intentional, or is it a sign error? Please confirm the correct positive height.']),
        turn('The second storey height was a sign error: change only that height to +3.3 m. Rebuild the elevations as 3.3, 6.6 and 9.9 m. Keep C35, the 60 kN/m beam loads and the 30 kN load at the second-storey midpoint. '+output_en(),
             1, attachments=['geometry-t2.json']),
    ]
    return emit('INT-070', [m], turns, {'input-t1.json': initial,
                'geometry-t2.json': dict(storeyHeightsM=[3.3, 3.3, 3.3], nodes=m['nodes'])},
                notes('Source: one 6 m bay, three final 3.3 m storeys; 500x500 mm columns, 300x600 mm beams; C35 E=31500 MPa, G=13125 MPa, nu=0.2, rho=2500 kg/m3.',
                      'First attachment uses node level indices and the erroneous second-storey height -3.3 m; it withholds corrected elevations so a complete geometry cannot silently resolve the contradiction.',
                      'A real connected midpoint node on the middle-storey beam receives the additional -30 kN force. Splitting preserves the full 60 kN/m load and adds no mass or support.'))


def case071():
    a = frame([0, 6, 12], [3.6, 7.2])
    a['sections'].append(P.section('C-outer', .6, .5))
    for e in a['elements']:
        if e['type'] == 'column' and e['id'].startswith(('c0-', 'c2-')):
            e.update(section='C-outer', rotation_angle=90)
    udl(a, 10)
    b = deepcopy(a)
    b['materials'][0] = concrete('C40')
    initial = public_input(a, sectionOrientation='The 600x500 mm exterior columns have rotation_angle=90 degrees, putting their stronger Iz axis into global-Y in-plane bending. Middle columns are 500x500 mm; beams are 300x600 mm.')
    turns = [turn('建立并分析附件中的两层两跨C30框架。两侧外柱600×500mm按明示强轴方向布置，中柱500×500mm，梁300×600mm，各梁向下10kN/m。'+output_zh(), 1, attachments=['input-t1.json']),
             turn('将每根梁柱的材料全部替换为本轮附件C40完整记录，并重新分析。只改变材料，不改变外柱与中柱尺寸差异、局部轴方向、几何或荷载。'+output_zh(), 2, attachments=['material-t2.json'])]
    return emit('INT-071', [a, b], turns, {'input-t1.json': initial, 'material-t2.json': dict(material=b['materials'][0])},
                notes('Source geometry: two 6 m bays, two 3.6 m storeys. Exterior columns 600x500 mm, middle columns 500x500 mm, beams 300x600 mm; all beams -10 kN/m.',
                      'Exterior rectangular columns have explicit 90-degree roll so in-plane global-Y bending uses Iz, the stronger inertia for B=600,H=500 mm. This remains identical in both states.',
                      'Frozen appendix material records: C30 E=30000 MPa/G=12500 MPa; C40 E=32500 MPa/G=32500/2.4 MPa. Both nu=0.2, rho=2500 kg/m3. Only name,E,G change.'))


def case072():
    m = frame([0, 5, 12], [3.3, 7.3, 10.4])
    udl(m, 8)
    udl(m, 6, predicate=lambda e: e['id'].startswith('b1-'), case='L')
    m['load_combinations'] = [dict(id='D+L', factors={'D': 1, 'L': 1})]
    initial = public_input(m)
    for key in ('nodes', 'elements', 'load_cases'):
        del initial[key]
    initial['geometry'] = dict(storeyHeightsM=[3.3, 4.0, 3.1], firstBayLengthM=5,
                               totalBays=None, subsequentBayLengthsM=None,
                               connectivity=None, supports='All ground-level columns fixed in ux,uz,ry.')
    initial['memberAssignmentRules'] = dict(columns='C1, material M1', beams='B1, material M1', jointType='rigid', initialRollDegrees=0)
    initial['loadRules'] = dict(D='Every beam: downward 8 kN/m.',
                                L='No live load on the first (leftmost) bay. Load group R has downward 6 kN/m on every storey; its span membership and connectivity remain to be supplied with the missing bay geometry.')
    turns = [turn('The attachment supplies three storey heights and a first bay of 5 m, but omits the total number of bays, subsequent bay lengths and their connectivity. Determine whether the frame is defined well enough to analyze; request essential missing geometry if it cannot be derived uniquely. '+output_en(),
                  None, 'clarify', ['input-t1.json'], unresolved=['geometry.totalBays', 'geometry.subsequentBayLengthsM', 'geometry.connectivity'],
                  questions=['How many bays are there, what are the remaining bay lengths, and how do the storey beams and columns connect?']),
             turn('There are exactly two bays, 5 m and 7 m, with column lines x=0,5,12 m and storey elevations z=3.3,7.3,10.4 m. Use the supplied connectivity. Group R is the right bay at every storey: D=8 kN/m and L=6 kN/m downward; the left bay has D only. All column bases are fixed. Analyze D, L and combination D+L separately. '+output_en(),
                  1, attachments=['geometry-t2.json'])]
    supplement = dict(nodes=m['nodes'], elements=m['elements'], load_cases=m['load_cases'],
                      totalBays=2, bayLengthsM=[5, 7], groupR='b1-1, b1-2, b1-3')
    return emit('INT-072', [m], turns, {'input-t1.json': initial, 'geometry-t2.json': supplement},
                notes('Source geometry: three storeys 3.3/4.0/3.1 m, two bays 5/7 m. D=-8 kN/m on all beams; L=-6 kN/m on right-bay beams only; explicit D+L combination.',
                      'Missing source appendix completed with C30 E=30000 MPa,G=12500 MPa,nu=0.2,rho=2500 kg/m3; 500x500 mm columns, 300x600 mm beams.',
                      'Initial public input contains no completed nodes, elements, member IDs, column count, right span length or full load assignments. R is a load-group rule, not an implicit total-bay count. Connectivity and load-to-member assignments arrive only in turn 2.'))


def case073():
    m = frame([0, 6, 12], [3.6, 7.2])
    m['materials'] = [concrete('C30', 'M-beam'), concrete('C40', 'M-column')]
    for e in m['elements']:
        e['material'] = 'M-column' if e['type'] == 'column' else 'M-beam'
    udl(m, 10, predicate=lambda e: e['id'].endswith('-1'))
    udl(m, 14, predicate=lambda e: e['id'] == 'b0-2')
    initial = public_input(m, zeroLoadMembers=['b1-2'], materialAssignment='Columns use M-column (C40); beams use M-beam (C30). This is a linear elastic role assignment.')
    return emit('INT-073', [m], [turn('按完整附件直接进行线性静力分析：柱使用C40，梁使用C30，两者各有完整弹性参数。首层两跨梁均向下10kN/m，屋面仅左梁向下14kN/m，屋面右梁零线载。不同构件使用不同材料是明确分组，无需合并材料；不做钢筋设计或非线性分析。'+output_zh(), 1, attachments=['input-t1.json'])],
                {'input-t1.json': initial}, notes('Source complete two-storey/two-bay frame: x=0/6/12 m and z=0/3.6/7.2 m; first floor both beams -10 kN/m, roof-left -14 kN/m, roof-right no line load.',
                                                  'Missing section appendix completed with 500x500 mm columns and 300x600 mm beams. C40 columns E=32500 MPa/G=32500/2.4 MPa; C30 beams E=30000 MPa/G=12500 MPa; both nu=0.2,rho=2500 kg/m3.'))


def case074():
    a = frame([0, 7], [3.6, 7.2])
    a['sections'] = [P.section('B1', .3, .6), P.section('C-left', .5, .35), P.section('C-right', .35, .5)]
    for e in a['elements']:
        if e['type'] == 'column':
            e['section'] = 'C-left' if e['id'].startswith('c0-') else 'C-right'
    udl(a, 10)
    P.load(a, id='roof-right-force-and-moment', type='nodal', node='n1-2', fx=20, my=12)
    b = deepcopy(a)
    for e in b['elements']:
        if e['id'].startswith('c0-'):
            e['rotation_angle'] = 90
    c = deepcopy(a)
    initial = public_input(a, sectionRotationDefinition='Keep each section A,Iy,Iz,J and displayed B,H unchanged. Rotate the local basis using sectionRoll and rotation_angle. At zero roll in-plane bending uses Iy; at +90 degrees it uses Iz. Left columns initially use the weaker in-plane inertia; right columns initially use the stronger inertia.')
    turns = [turn('Build the two-storey one-bay frame in the attachment. Left columns are 500x350 mm, right columns 350x500 mm, with the explicit section axes. Preserve the downward 10 kN/m beam loads and the roof-right +X 20 kN force plus global +Y 12 kN.m moment. '+output_en(), 1, attachments=['input-t1.json']),
             turn('Rotate only the two left-column local section bases by +90 degrees about their i-to-j axes using the attachment transformation, then rerun. Keep the section property records unchanged and use the rotated bending stiffness. Do not rotate the global nodal load or moment. '+output_en(), 2),
             turn('Undo only the preceding left-column rotation: restore both left-column rotation angles to their original zero-degree values and rerun. The two right columns, all other properties, and every load remain unchanged. '+output_en(), 3)]
    return emit('INT-074', [a, b, c], turns, {'input-t1.json': initial},
                notes('Source frame: x=0/7 m, z=0/3.6/7.2 m; left columns 500x350 mm, right columns 350x500 mm; every beam -10 kN/m, roof-right fx=+20 kN and my=+12 kN.m.',
                      'Missing appendix completed with C30 elastic record and 300x600 mm beam section. All initial column rolls are zero; source left/right size order therefore gives different in-plane Iy.',
                      'State 2 changes only c0-1 and c0-2 rotation_angle from 0 to 90 degrees. State 3 is byte-equivalent data to state 1. The source requires actual rotated stiffness; planar roll adapter/evaluator acceptance remains pending.'))


def case075():
    a = frame([0, 5, 10, 15], [3.6, 7.2])
    a['nodes'] = [n for n in a['nodes'] if n['id'] != 'n3-2']
    a['elements'] = [e for e in a['elements'] if 'n3-2' not in e['nodes']]
    a['sections'].extend([P.section('C-upper', .45, .45), P.section('B-roof', .3, .5)])
    section_assign(a, lambda e: e['type'] == 'column' and e['id'].endswith('-2'), 'C-upper')
    section_assign(a, lambda e: e['type'] == 'beam' and e['id'].endswith('-2'), 'B-roof')
    split_beam(a, 'b1-1', 'floor1-middle-bay-mid')
    udl(a, 10)
    P.load(a, id='floor1-middle-bay-point', type='nodal', node='floor1-middle-bay-mid', fz=-24)
    b = deepcopy(a)
    next(l for l in b['load_cases'][0]['loads'] if l.get('element') == 'b1-2')['wz'] = -12
    turns = [turn('建立并分析附件退台框架：下层三跨5m，上层只保留左侧两跨；所有实际梁向下10kN/m，下层中跨连通跨中节点另向下24kN。'+output_zh(), 1, attachments=['input-t1.json']),
             turn('仅把上层最右侧实际梁（上层保留两跨中的第二跨，x=5～10m、z=7.2m，构件b1-2）的向下线载改为12kN/m并重算。下层全部荷载及24kN集中力保持；不新增上层第三跨。'+output_zh(), 2)]
    return emit('INT-075', [a, b], turns, {'input-t1.json': public_input(a)},
                notes('Source setback topology: lower column lines x=0/5/10/15 m, upper only x=0/5/10 m, floor heights 3.6 m; all actual beams -10 kN/m initially.',
                      'Missing grouped section appendix completed with lower columns 500x500 mm, upper columns 450x450 mm, lower beams 300x600 mm and roof beams 300x500 mm, all C30.',
                      'Connected midpoint node x=7.5,z=3.6 m carries -24 kN. Turn 2 changes only the upper-right real beam b1-2 line load from -10 to -12 kN/m; no upper third bay exists.'))


def case076():
    m = frame([0, 5, 12], [3.6, 7.2])
    p = next(s for s in m['sections'] if s['id'] == 'C1')['properties']
    m['sections'].append(dict(id='C2', name='C2 effective elastic section', type='general',
                              properties=dict(A=p['A'], Iy=.7*p['Iy'], Iz=.7*p['Iz'], J=p['J'])))
    section_assign(m, lambda e: e['type'] == 'column' and e['id'] in ('c0-2', 'c2-2'), 'C2')
    udl(m, 40, predicate=lambda e: e['id'].startswith('b0-'))
    udl(m, 60, predicate=lambda e: e['id'].startswith('b1-'))
    initial = public_input(m, floorPressureKNPerM2=10,
                           tributaryWidthM=dict(left=4, right=None),
                           loadConversion='Both floors: downward line load = 10 kN/m2 times that bay tributary width; apply this conversion once only. The listed beam loads represent the converted floor pressure, not an additional load.',
                           sectionDefinition='C2 is an effective elastic section: same A and J as C1, Iy and Iz each 0.7 times C1. C1 is 500x500 mm. Both upper exterior columns use C2; all other columns use C1.')
    for l in initial['load_cases'][0]['loads']:
        if l['element'].startswith('b1-'):
            l['wz'] = None
    turns = [turn('The two-storey frame has 5 m and 7 m bays, floor pressure 10 kN/m2 on both floors, and left tributary width 4 m. The right tributary width is missing. Check the load conversion and request the essential missing parameter if it is not uniquely determined. '+output_en(),
                  None, 'clarify', ['input-t1.json'], unresolved=['tributaryWidthM.right', 'right-bay line loads'],
                  questions=['What tributary width should be used for the right bay on both floors?']),
             turn('The right tributary width is 6 m on both floors. Keep the pressure at 10 kN/m2 and the left width at 4 m, giving left and right downward line loads of 40 and 60 kN/m respectively. Apply the floor pressure conversion once, preserve the C1/C2 column assignments, and analyze. '+output_en(), 1, attachments=['width-t2.json'])]
    return emit('INT-076', [m], turns, {'input-t1.json': initial,
                'width-t2.json': dict(tributaryWidthM=dict(left=4, right=6), floorPressureKNPerM2=10, load_cases=m['load_cases'])},
                notes('Source: column lines x=0/5/12 m, two 3.6 m storeys, floor pressure 10 kN/m2, tributary widths 4/6 m. Hidden load model contains only the converted beam UDLs 40/60 kN/m, no duplicate floor load.',
                      'Missing appendix completed with C30, C1=500x500 mm, beams=300x600 mm. C2 has exactly equal A, Iy/Iz multiplied by 0.7; unspecified J is frozen equal to C1. It is explicitly an effective general section, without a contradictory rectangular shape.',
                      'Upper exterior columns alone use C2. First-turn input redacts both the right width and all derived right UDL values; the numeric width and converted loads are released only in turn 2.'))


def case077():
    a = frame([0, 6, 12], [3.6, 7.2, 10.8])
    a['sections'].extend([P.section('C-lower', .6, .6), P.section('C-new', .65, .65),
                          P.section('B3', .3, .5), P.section('B4', .35, .65)])
    section_assign(a, lambda e: e['type'] == 'column' and e['id'].endswith('-1'), 'C-lower')
    section_assign(a, lambda e: e['type'] == 'beam' and e['id'].endswith('-3'), 'B3')
    split_beam(a, 'b0-3', 'roof-left-mid')
    udl(a, 10)
    P.load(a, id='roof-left-point', type='nodal', node='roof-left-mid', fz=-15)
    b = deepcopy(a)
    section_assign(b, lambda e: e['type'] == 'column' and e['id'].endswith('-1'), 'C-new')
    c = deepcopy(b)
    section_assign(c, lambda e: e['type'] == 'beam' and e['section'] == 'B3', 'B4')
    initial = public_input(a, sectionGroups='Lower columns are ground-to-first-storey only; columns in storeys 2 and 3 remain C1=500x500 mm. B3 is the initial roof beam record. C-new=650x650 mm and B4=350x650 mm are complete alternative records, not initial assignments.')
    turns = [turn('建立并分析三层两跨混凝土框架。首层柱600×600mm、以上两层柱500×500mm，顶层梁按B3；每根实际梁向下10kN/m，顶层左跨x=3m处连通节点另向下15kN。附件还列出后续可用完整截面记录。'+output_zh(), 1, attachments=['input-t1.json']),
             turn('仅把下层柱（地面至首层，c0-1/c1-1/c2-1）截面改为附件C-new的650×650mm记录并重新分析。上层柱、全部梁、几何和荷载保持。'+output_zh(), 2),
             turn('在当前状态基础上，仅将顶层梁截面改为附件B4完整记录，包括顶层左跨的两个连通梁段。下层柱保持上轮650×650mm，上层柱仍500×500mm，下层梁及全部荷载保持。'+output_zh(), 3)]
    return emit('INT-077', [a, b, c], turns, {'input-t1.json': initial},
                notes('Source: three 3.6 m storeys, column lines x=0/6/12 m. Lowest-storey columns 600x600 mm, upper two storeys 500x500 mm, all beams -10 kN/m; roof-left midpoint x=3 m adds -15 kN.',
                      'Missing appendix completed with C30, non-roof beams B1=300x600 mm, initial roof B3=300x500 mm, replacement B4=350x650 mm. C-new is source-specified 650x650 mm. All records supplied in full.',
                      'Turn 2 changes only the three lowest-storey column section assignments. Turn 3 changes only the roof beam assignments (both roof-left segments and roof-right beam), preserving the prior column change and 15 kN load.'))


def case078():
    a = frame([0, 6], [3.6, 7.2, 10.8])
    for storey, q in enumerate([12, 10, 8], 1):
        udl(a, q, predicate=lambda e, j=storey: e['id'] == f'b0-{j}')
    P.load(a, id='middle-left-half-additional', type='distributed', element='b0-2', start=0, end=3, wz=-5)
    for j, force in enumerate([10, 15, 20], 1):
        P.load(a, 'W+', id=f'Wplus-storey-{j}', type='nodal', node=f'n1-{j}', fx=force)
        P.load(a, 'W-', id=f'Wminus-storey-{j}', type='nodal', node=f'n1-{j}', fx=-force)
    a['load_combinations'] = [dict(id='D', factors={'D': 1}),
                              dict(id='D+W+', factors={'D': 1, 'W+': 1}),
                              dict(id='D+W-', factors={'D': 1, 'W-': 1})]
    b = deepcopy(a)
    for l in next(c for c in b['load_cases'] if c['id'] == 'W-')['loads']:
        l['fx'] *= 1.2
    turns = [turn('Build the three-storey single-bay frame from the attachment. Keep D, W+ and W- as independent signed cases, and evaluate the three explicitly listed combinations D, D+W+ and D+W-. D includes an additional downward 5 kN/m on the left half of the second-storey beam, in addition to its baseline 10 kN/m. Distinguish case D from combination D in labels. '+output_en(), 1, attachments=['input-t1.json']),
             turn('Increase only the magnitude of each W- storey force by 20 percent, retaining its negative global-X direction. The new W- forces from bottom to top are -12, -18 and -24 kN. Preserve W+, D (including the second-storey partial UDL), geometry, sections and all combination factors. Rerun the current state. '+output_en(), 2)]
    return emit('INT-078', [a, b], turns, {'input-t1.json': public_input(a)},
                notes('Source: three 3.6 m storeys, one 6 m bay. D UDLs bottom-to-top -12/-10/-8 kN/m; additional second-storey left-half -5 kN/m from x=0 to 3 m. W+ right-node forces +10/+15/+20 kN; W- initially their negatives.',
                      'Missing appendix completed with C30, 500x500 mm columns and 300x600 mm beams.',
                      'Source combination IDs are retained literally: D, D+W+, D+W-. Case D and combination D are independently requested using different selection kinds.',
                      'Turn 2 changes only W- fx values by factor 1.2; all remain negative. Neither gravity loads nor W+ nor combination coefficients change.'))


def check():
    """Structural and source-review checks; deliberately does not solve models."""
    expected = {
        69: (6, 6, {'D': (0, -864)}),
        70: (9, 10, {'D': (0, -1110)}),
        71: (9, 10, {'D': (0, -240)}),
        72: (12, 15, {'D': (0, -288), 'L': (0, -126)}),
        73: (9, 10, {'D': (0, -204)}),
        74: (6, 6, {'D': (20, -140)}),
        75: (12, 13, {'D': (0, -274)}),
        76: (9, 10, {'D': (0, -1240)}),
        77: (13, 16, {'D': (0, -375)}),
        78: (8, 9, {'D': (0, -195), 'W+': (45, 0), 'W-': (-45, 0)}),
    }
    state_count = quantity_count = requirement_count = 0
    for number in range(69, 79):
        cid = f'INT-{number:03}'
        folder = ROOT/'corpora/research-300/cases'/cid
        read = lambda name: json.loads((folder/name).read_text())
        c, ref = read('contract.json'), read('reference-requests.json')
        assert c['sourcePlan'] == PLAN[cid]['sourceRequirements']
        assert len(c['turns']) == TASKS[cid]['turns']
        covered = [n for r in c['requirementCoverage'] for n in r['requirementIds']]
        assert sorted(covered) == sorted(r['id'] for r in PLAN[cid]['requirements'])
        requirement_count += len(covered)
        assert c['plannedEngine'] == 'OpenSees'
        assert c['status'] == 'authored-candidate' and c['sameEngineTruthStatus'] == 'pending'
        assert c['inputBlindReview'] == 'pending' and c['llmEndToEnd'] == 'not-run'
        assert (folder/'prompt.txt').read_text().strip() == c['turns'][0]['instruction']
        assert not set(c['attachments']) & set(c['modelStates'])
        assert set(c['attachments']) == {f for t in c['turns'] for f in t['attachments']}
        if c['locale'] == 'en':
            for name in ['prompt.txt'] + c['attachments']:
                assert not re.search('[\u3400-\u9fff]', (folder/name).read_text()), (cid, name)
        models = [read(name) for name in c['modelStates']]
        assert len(ref['states']) == len(models)
        for state, m in enumerate(models, 1):
            state_count += 1
            assert m['schema_version'] == '2.2.0'
            ns = {n['id']: n for n in m['nodes']}
            es = {e['id']: e for e in m['elements']}
            assert len(ns) == len(m['nodes']) == expected[number][0]
            assert len(es) == len(m['elements']) == expected[number][1]
            assert len({(n['x'], n['y'], n['z']) for n in ns.values()}) == len(ns)
            materials = {v['id']: v for v in m['materials']}
            sections = {v['id']: v for v in m['sections']}
            for n in ns.values():
                assert n['y'] == 0
                assert n['restraints'] == ([True]*6 if n['z'] == 0 else [False, True, False, True, False, True])
            for e in es.values():
                assert e['material'] in materials and e['section'] in sections
                assert all(n in ns for n in e['nodes']) and e['nodes'][0] != e['nodes'][1]
            assert {n for e in es.values() for n in e['nodes']} == set(ns)
            for material in materials.values():
                assert material['E'] > 0 and material['G'] > 0
                assert math.isclose(material['G'], material['E']/(2*(1+material['nu'])))
            for section in sections.values():
                assert all(section['properties'][k] > 0 for k in ('A', 'Iy', 'Iz', 'J'))
            assert all(value is False for value in m['analysis_control'].values())
            totals = {}
            for lc in m['load_cases']:
                assert len({l['id'] for l in lc['loads']}) == len(lc['loads'])
                fx = fz = 0
                for load in lc['loads']:
                    assert load['reference_frame'] == 'global'
                    if load['type'] == 'nodal':
                        assert load['node'] in ns
                        fx += load.get('fx', 0)
                        fz += load.get('fz', 0)
                    else:
                        element = es[load['element']]
                        a, b = [ns[n] for n in element['nodes']]
                        length = math.dist([a[k] for k in 'xyz'], [b[k] for k in 'xyz'])
                        start, end = load.get('start', 0), load.get('end', length)
                        assert 0 <= start < end <= length+1e-10
                        fx += load.get('wx', 0)*(end-start)
                        fz += load.get('wz', 0)*(end-start)
                totals[lc['id']] = (fx, fz)
            target = dict(expected[number][2])
            if number == 75 and state == 2:
                target['D'] = (0, -284)
            if number == 78 and state == 2:
                target['W-'] = (-54, 0)
            assert totals.keys() == target.keys()
            for lc, values in target.items():
                assert all(math.isclose(a, b, abs_tol=1e-9) for a, b in zip(totals[lc], values)), (cid, state, lc)
            case_ids = {lc['id'] for lc in m['load_cases']}
            for combo in m['load_combinations']:
                assert set(combo['factors']) <= case_ids
            r = ref['states'][state-1]
            assert r['state'] == state and r['model'] == c['modelStates'][state-1]
            qids = {q['id'] for q in r['quantities']}
            assert len(qids) == len(r['quantities'])
            for q in r['quantities']:
                assert 'value' not in q and q['location']['id'] in ns
                key = 'load_cases' if q['selection']['kind'] == 'case' else 'load_combinations'
                assert q['selection']['id'] in {s['id'] for s in m[key]}
                assert q['tolerance'] == dict(absolute=1e-8, relative=1e-6)
            for output in c['requiredOutputs']:
                if output['state'] == state and output['kind'] == 'numerical':
                    assert set(output['quantityIds']) <= qids
            quantity_count += len(qids)
        initial = read('input-t1.json')
        assert initial['documentType'] == 'Public engineering input tables'
        assert not {'schema_version', 'unit_system', 'nodes', 'elements', 'materials',
                    'sections', 'load_cases', 'analysis_control'} & set(initial)
        if number in (69, 70, 72, 76):
            assert c['turns'][0]['state'] is None and c['turns'][0]['expectation'] == 'clarify'
            assert c['turns'][0]['attachments'] == ['input-t1.json']
        if number == 69:
            mat = initial['materialTable'][0]
            assert mat['E'] is None and mat['G'] is None and 'C30' not in mat['name']
        if number == 70:
            assert initial['storeyHeightsM'] == [3.3, -3.3, 3.3]
            assert all('z' not in n for n in initial['nodeTable'])
            assert next(n for n in models[0]['nodes'] if n['id'] == 'floor2-mid')['z'] == 6.6
        if number == 71:
            assert models[0]['elements'] == models[1]['elements']
            assert all(e['rotation_angle'] == 90 for e in models[0]['elements'] if e['section'] == 'C-outer')
        if number == 72:
            assert not {'nodeTable', 'memberTable', 'loadCaseTable'} & set(initial)
            assert initial['geometry']['totalBays'] is None and initial['geometry']['subsequentBayLengthsM'] is None
            assert {l['element'] for l in models[0]['load_cases'][1]['loads']} == {'b1-1', 'b1-2', 'b1-3'}
        if number == 73:
            assert all(e['material'] == ('M-column' if e['type'] == 'column' else 'M-beam') for e in models[0]['elements'])
            assert all(l.get('element') != 'b1-2' for l in models[0]['load_cases'][0]['loads'])
        if number == 74:
            assert models[0] == models[2]
            assert all(m['load_cases'][0]['loads'][-1]['my'] == 12 for m in models)
        if number == 75:
            assert all(not (n['x'] == 15 and n['z'] == 7.2) for n in models[0]['nodes'])
        if number == 76:
            assert initial['tributaryWidthM']['right'] is None
            assert all(l['wz'] is None for l in initial['loadCaseTable'][0]['loads'] if l['element'].startswith('b1-'))
            c1, c2 = [next(s for s in models[0]['sections'] if s['id'] == sid)['properties'] for sid in ('C1', 'C2')]
            assert c2['A'] == c1['A'] and c2['Iy'] == .7*c1['Iy'] and c2['Iz'] == .7*c1['Iz']
        if number == 77:
            assert models[0]['load_cases'] == models[1]['load_cases'] == models[2]['load_cases']
            assert len([e for e in models[2]['elements'] if e['section'] == 'C-new']) == 3
            assert len([e for e in models[2]['elements'] if e['section'] == 'B4']) == 3
        if number == 78:
            assert models[0]['load_cases'][:2] == models[1]['load_cases'][:2]
            assert models[0]['load_combinations'] == models[1]['load_combinations']
            assert {q['selection']['kind'] for q in ref['states'][0]['quantities'] if q['selection']['id'] == 'D'} == {'case', 'combination'}
    print(f'PASS: 10 cases, {state_count} states, {quantity_count} quantities, {requirement_count} source requirement IDs; structural/source checks only.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Check existing artifacts without writing.')
    args = parser.parse_args()
    if not args.check:
        for build in (case069, case070, case071, case072, case073,
                      case074, case075, case076, case077, case078):
            folder = build()
            print(folder.relative_to(ROOT))
    check()


if __name__ == '__main__':
    main()
