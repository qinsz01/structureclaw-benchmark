"""Author STD-041..050 from their retained planning rows, never numerical truth.

Only the explicit case directories below are written. Missing source appendices are
completed by frozen author choices recorded in each public input and contract.
Run with --check for source-specific topology and independent mechanical checks.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def import_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


P = import_file('std_a_041_050_primitives', ROOT / 'scripts/representative-models.py')

FIXED = [True] * 6
TRUSS_FREE = [False, False, False, True, True, True]


def new_frame():
    m = P.model()
    # Explicit idealized solid sections, not unstated catalogue substitutions.
    m['sections'] = [P.section('ROOF', .30, .60),
                     P.section('COLUMN', .50, .50),
                     P.section('MEZZ', .25, .50)]
    m['metadata'] = {
        'localAxes': 'Local 1 points from the first listed node to the second; '
                     'local 2 is global +Y; local 3 = local 1 cross local 2.',
        'kinematics': 'Euler-Bernoulli, axial and flexural deformation included; '
                      'shear deformation excluded; no end releases.',
        'inactiveDofs': ['uy', 'rx', 'rz'],
    }
    return m


def add_nodes(m, rows):
    """Rows have explicit global X,Y,Z and optional six-DOF restraints."""
    for row in rows:
        name, x, y, z, *restraint = row
        P.node(m, name, x, z, y,
               restraint[0] if restraint else None)


def add_elements(m, rows):
    for name, start, end, kind, section in rows:
        P.elem(m, name, start, end, kind, section)


def length(m, member):
    e = next(e for e in m['elements'] if e['id'] == member)
    n = {n['id']: n for n in m['nodes']}
    return math.dist([n[e['nodes'][0]][k] for k in ('x', 'y', 'z')],
                     [n[e['nodes'][1]][k] for k in ('x', 'y', 'z')])


def uniform(m, member, intensity):
    P.load(m, type='distributed', element=member, wz=-intensity,
           start=0.0, end=length(m, member))


def truss_041():
    m = P.model('3d')
    m['sections'] = [P.section('A1', .10, .04)]
    add_nodes(m, [
        ('A', 0, 0, 0, FIXED), ('B', 6, 0, 0, FIXED),
        ('C', 6, 6, 0, FIXED), ('D', 0, 6, 0, FIXED),
        ('P', 2, 3, 3, TRUSS_FREE),
    ])
    add_elements(m, [
        ('AB', 'A', 'B', 'truss', 'A1'),
        ('BC', 'B', 'C', 'truss', 'A1'),
        ('CD', 'C', 'D', 'truss', 'A1'),
        ('DA', 'D', 'A', 'truss', 'A1'),
        ('AP', 'A', 'P', 'truss', 'A1'),
        ('BP', 'B', 'P', 'truss', 'A1'),
        ('CP', 'C', 'P', 'truss', 'A1'),
        ('DP', 'D', 'P', 'truss', 'A1'),
    ])
    P.load(m, type='nodal', node='P', fx=15.0, fz=-40.0)
    m['metadata']['memberGroups'] = {
        'base-perimeter': ['AB', 'BC', 'CD', 'DA'],
        'inclined': ['AP', 'BP', 'CP', 'DP'],
    }
    m['metadata']['inactiveDofs'] = ['rx', 'ry', 'rz']
    return m


def truss_042():
    m = P.model('3d')
    m['sections'] = [P.section('CHORD', .08, .08),
                     P.section('HORIZONTAL', .07, .07),
                     P.section('DIAGONAL', .06, .06)]
    y = 2 * math.sqrt(3)
    add_nodes(m, [
        ('A0', 0, 0, 0, FIXED), ('B0', 4, 0, 0, FIXED),
        ('C0', 2, y, 0, FIXED),
        ('A1', 0, 0, 3, TRUSS_FREE), ('B1', 4, 0, 3, TRUSS_FREE),
        ('C1', 2, y, 3, TRUSS_FREE),
        ('A2', 0, 0, 6, TRUSS_FREE), ('B2', 4, 0, 6, TRUSS_FREE),
        ('C2', 2, y, 6, TRUSS_FREE),
    ])
    # This is the complete author-supplied connection appendix. X crossings
    # have no node. Each inclined bar spans one explicitly identified tier.
    add_elements(m, [
        ('CH1', 'A0', 'A1', 'truss', 'CHORD'),
        ('CH2', 'B0', 'B1', 'truss', 'CHORD'),
        ('CH3', 'C0', 'C1', 'truss', 'CHORD'),
        ('CH4', 'A1', 'A2', 'truss', 'CHORD'),
        ('CH5', 'B1', 'B2', 'truss', 'CHORD'),
        ('CH6', 'C1', 'C2', 'truss', 'CHORD'),
        ('H1', 'A0', 'B0', 'truss', 'HORIZONTAL'),
        ('H2', 'B0', 'C0', 'truss', 'HORIZONTAL'),
        ('H3', 'C0', 'A0', 'truss', 'HORIZONTAL'),
        ('H4', 'A1', 'B1', 'truss', 'HORIZONTAL'),
        ('H5', 'B1', 'C1', 'truss', 'HORIZONTAL'),
        ('H6', 'C1', 'A1', 'truss', 'HORIZONTAL'),
        ('H7', 'A2', 'B2', 'truss', 'HORIZONTAL'),
        ('H8', 'B2', 'C2', 'truss', 'HORIZONTAL'),
        ('H9', 'C2', 'A2', 'truss', 'HORIZONTAL'),
        ('D1', 'A0', 'B1', 'truss', 'DIAGONAL'),
        ('D2', 'B0', 'A1', 'truss', 'DIAGONAL'),
        ('D3', 'B0', 'C1', 'truss', 'DIAGONAL'),
        ('D4', 'C0', 'B1', 'truss', 'DIAGONAL'),
        ('D5', 'C0', 'A1', 'truss', 'DIAGONAL'),
        ('D6', 'A0', 'C1', 'truss', 'DIAGONAL'),
        ('D7', 'A1', 'B2', 'truss', 'DIAGONAL'),
        ('D8', 'B1', 'A2', 'truss', 'DIAGONAL'),
        ('D9', 'B1', 'C2', 'truss', 'DIAGONAL'),
        ('D10', 'C1', 'B2', 'truss', 'DIAGONAL'),
        ('D11', 'C1', 'A2', 'truss', 'DIAGONAL'),
        ('D12', 'A1', 'C2', 'truss', 'DIAGONAL'),
    ])
    for top in ('A2', 'B2', 'C2'):
        P.load(m, type='nodal', node=top, fx=10.0)
    m['metadata']['memberGroups'] = {
        'inter-level-chords': [f'CH{i}' for i in range(1, 7)],
        'horizontal-ties': [f'H{i}' for i in range(1, 10)],
        'inter-level-diagonals': [f'D{i}' for i in range(1, 13)],
    }
    m['metadata']['inactiveDofs'] = ['rx', 'ry', 'rz']
    m['metadata']['crossingConnectivity'] = (
        'Members connect only at listed endpoints; all diagonal X crossings are unconnected.')
    return m


def frame_043():
    m = new_frame()
    add_nodes(m, [('A', 0, 0, 0, FIXED), ('B', 18, 0, 0, FIXED),
                  ('L', 0, 0, 7), ('M', 9, 0, 7), ('R', 18, 0, 7)])
    add_elements(m, [('CL', 'A', 'L', 'column', 'COLUMN'),
                     ('CR', 'B', 'R', 'column', 'COLUMN'),
                     ('RL', 'L', 'M', 'beam', 'ROOF'),
                     ('RR', 'M', 'R', 'beam', 'ROOF')])
    for member in ('RL', 'RR'):
        uniform(m, member, 6)
    return m


def frame_044():
    m = new_frame()
    add_nodes(m, [('A', 0, 0, 0, FIXED), ('B', 18, 0, 0, FIXED),
                  ('C', 36, 0, 0, FIXED), ('L', 0, 0, 9),
                  ('M1', 9, 0, 9), ('J', 18, 0, 9),
                  ('M2', 27, 0, 9), ('R', 36, 0, 9)])
    add_elements(m, [('CL', 'A', 'L', 'column', 'COLUMN'),
                     ('CM', 'B', 'J', 'column', 'COLUMN'),
                     ('CR', 'C', 'R', 'column', 'COLUMN'),
                     ('R1a', 'L', 'M1', 'beam', 'ROOF'),
                     ('R1b', 'M1', 'J', 'beam', 'ROOF'),
                     ('R2a', 'J', 'M2', 'beam', 'ROOF'),
                     ('R2b', 'M2', 'R', 'beam', 'ROOF')])
    for member in ('R1a', 'R1b', 'R2a', 'R2b'):
        uniform(m, member, 6)
    return m


def frame_045():
    m = new_frame()
    add_nodes(m, [('A', 0, 0, 0, FIXED), ('B', 21, 0, 0, FIXED),
                  ('L', 0, 0, 7.5), ('M', 10.5, 0, 7.5),
                  ('R', 21, 0, 7.5)])
    add_elements(m, [('CL', 'A', 'L', 'column', 'COLUMN'),
                     ('CR', 'B', 'R', 'column', 'COLUMN'),
                     ('RL', 'L', 'M', 'beam', 'ROOF'),
                     ('RR', 'M', 'R', 'beam', 'ROOF')])
    for member in ('RL', 'RR'):
        uniform(m, member, 8)
    P.load(m, type='nodal', node='M', fz=-60.0, id='equipment')
    return m


def frame_046():
    m = new_frame()
    add_nodes(m, [('A', 0, 0, 0, FIXED), ('B', 18, 0, 0, FIXED),
                  ('C', 36, 0, 0, FIXED), ('L', 0, 0, 9),
                  ('J', 18, 0, 9), ('R', 36, 0, 9)])
    add_elements(m, [('CL', 'A', 'L', 'column', 'COLUMN'),
                     ('CM', 'B', 'J', 'column', 'COLUMN'),
                     ('CR', 'C', 'R', 'column', 'COLUMN'),
                     ('R1', 'L', 'J', 'beam', 'ROOF'),
                     ('R2', 'J', 'R', 'beam', 'ROOF')])
    for member in ('R1', 'R2'):
        uniform(m, member, 6)
    P.load(m, type='nodal', node='J', fx=4.9, fz=-49.0, id='crane')
    return m


def frame_047():
    m = new_frame()
    add_nodes(m, [('A', 0, 0, 0, FIXED), ('B', 18, 0, 0, FIXED),
                  ('J', 0, 0, 3), ('T', 6, 0, 3),
                  ('L', 0, 0, 7), ('R', 18, 0, 7)])
    add_elements(m, [('CL1', 'A', 'J', 'column', 'COLUMN'),
                     ('CL2', 'J', 'L', 'column', 'COLUMN'),
                     ('CR', 'B', 'R', 'column', 'COLUMN'),
                     ('ROOF', 'L', 'R', 'beam', 'ROOF'),
                     ('MEZZ', 'J', 'T', 'beam', 'MEZZ')])
    uniform(m, 'ROOF', 6)
    uniform(m, 'MEZZ', 4)
    return m


def frame_048():
    m = new_frame()
    add_nodes(m, [('A', 0, 0, 0, FIXED), ('B', 20, 0, 0, FIXED),
                  ('L', 0, 0, 6), ('P', 10, 0, 8), ('R', 20, 0, 6)])
    add_elements(m, [('CL', 'A', 'L', 'column', 'COLUMN'),
                     ('CR', 'B', 'R', 'column', 'COLUMN'),
                     ('SL', 'L', 'P', 'beam', 'ROOF'),
                     ('SR', 'P', 'R', 'beam', 'ROOF')])
    uniform(m, 'SL', 6)
    uniform(m, 'SR', 6)
    return m


def frame_049():
    m = new_frame()
    add_nodes(m, [('A', 0, 0, 0, FIXED), ('B', 24, 0, 0, FIXED),
                  ('L', 0, 0, 6), ('P', 10, 0, 8), ('R', 24, 0, 6)])
    add_elements(m, [('CL', 'A', 'L', 'column', 'COLUMN'),
                     ('CR', 'B', 'R', 'column', 'COLUMN'),
                     ('SL', 'L', 'P', 'beam', 'ROOF'),
                     ('SR', 'P', 'R', 'beam', 'ROOF')])
    uniform(m, 'SL', 5)
    uniform(m, 'SR', 7)
    return m


def frame_050():
    m = new_frame()
    add_nodes(m, [('A', 0, 0, 0, FIXED), ('B', 12, 0, 0, FIXED),
                  ('C', 30, 0, 0, FIXED), ('L', 0, 0, 6),
                  ('M1', 6, 0, 6), ('J6', 12, 0, 6),
                  ('J8', 12, 0, 8), ('M2', 21, 0, 8), ('R', 30, 0, 8)])
    add_elements(m, [('CL', 'A', 'L', 'column', 'COLUMN'),
                     ('CM1', 'B', 'J6', 'column', 'COLUMN'),
                     ('CM2', 'J6', 'J8', 'column', 'COLUMN'),
                     ('CR', 'C', 'R', 'column', 'COLUMN'),
                     ('R1a', 'L', 'M1', 'beam', 'ROOF'),
                     ('R1b', 'M1', 'J6', 'beam', 'ROOF'),
                     ('R2a', 'J8', 'M2', 'beam', 'ROOF'),
                     ('R2b', 'M2', 'R', 'beam', 'ROOF')])
    for member in ('R1a', 'R1b'):
        uniform(m, member, 5)
    for member in ('R2a', 'R2b'):
        uniform(m, member, 7)
    return m


BUILDERS = {41: truss_041, 42: truss_042, 43: frame_043, 44: frame_044,
            45: frame_045, 46: frame_046, 47: frame_047, 48: frame_048,
            49: frame_049, 50: frame_050}

PROMPTS = {
    41: '建立并用 OpenSees 分析偏心方锥空间桁架。底面为 6 m × 6 m，'
        '四角 A(0,0,0)、B(6,0,0)、C(6,6,0)、D(0,6,0) 的平移固定；'
        '顶点 P(2,3,3) m。保留四条底边杆 AB、BC、CD、DA 及四条斜杆 AP、BP、CP、DP。'
        '在唯一工况 D 中于 P 施加全局 Fx=+15 kN、Fz=-40 kN。所有杆件只传轴力，'
        '节点均铰接，转动自由度仅因轴力杆不使用而数值锁定。使用附件给定的唯一材料和唯一面积。'
        '报告 P 的 ux、uy、uz，全部八根杆的轴力（拉为正），以及 A、B、C、D 各自的 Fx、Fy、Fz 支座反力。',
    42: 'Build and analyze the two-tier triangular-prism space truss using OpenSees. '
        'The equilateral base has side length 4 m: A=(0,0), B=(4,0), '
        'C=(2,2*sqrt(3)) in the global XY plane. Levels 0, 1 and 2 have Z=0, 3 and 6 m. '
        'Use every node and member endpoint in the attached schedule: six inter-level chords, '
        'nine horizontal ties and twelve diagonals. Each side face of each tier has two '
        'crossing diagonals with no connection at their crossing. Fix the three base-node '
        'translations. All members are axial-only and all joints are pinned; rotational '
        'DOFs are inactive and may be numerically suppressed. In load case D, apply '
        'global Fx=+10 kN separately at A2, B2 and C2. Report ux, uy and uz at each top '
        'node, tension-positive axial forces in every chord and web member (include the '
        'horizontal ties), each base node\'s signed Fx/Fy/Fz reaction, and the signed sum '
        'of the three base reactions for each global direction.',
    43: '采用 OpenSees 分析跨度 18 m、柱高 7 m 的平屋面刚架。两个柱脚 A、B 固定，'
        '梁柱刚接，屋面水平。屋面跨中 M(9,0,7) 为两梁段的共享观测节点。唯一工况 D '
        '仅在整个水平屋面施加全局向下 6 kN/m 均布荷载。报告 L、R 两柱顶的 ux、uz，'
        '屋面跨中 M 的 uz，以及 A、B 各自的 Fx、Fz、My 支座反力及反力矩。',
    44: 'Use OpenSees to analyze a flat-roof portal frame with two 18 m spans and '
        '9 m high columns. Fix all three column bases A, B and C. Provide exactly one '
        'shared middle column CM and one rigid joint J at (18,0,9) m connecting both '
        'roof spans. Keep connected roof-midpoint observation nodes M1=(9,0,9) and '
        'M2=(27,0,9) m. In the sole load case D, apply a global downward uniform load '
        'of 6 kN/m on both entire roof spans. Report ux and uz at the three column '
        'tops L, J and R, ux and uz at both roof midpoints M1 and M2, and Fx, Fz '
        'and My reactions at each of the three fixed bases.',
    45: '采用 OpenSees 分析单跨 21 m、柱高 7.5 m 的平屋面刚架。两柱脚固定，梁柱刚接。'
        '屋面中点 M(10.5,0,7.5) 必须为左右两梁段的共享连通节点。唯一工况 D 包含全跨'
        '全局向下 8 kN/m 均布线载，并在 M 另加全局向下 60 kN 设备集中力。'
        '报告 M 的 uz、两柱顶 L/R 的 ux/uz、跨中左右邻接截面的 M2 弯矩，以及两柱脚 '
        'A/B 的 Fx、Fz、My。为核查设备力点的剪力跳跃，同时报告 RL 末端与 RR 首端的 V3；'
        '端截面取构件内部极限，明确构件名、位置及左右侧。',
    46: 'Analyze the two-span flat-roof portal frame using OpenSees. Both spans '
        'are 18 m and all three columns are 9 m high with fixed bases. The middle '
        'column has one shared roof joint J=(18,0,9) m. In load case D, apply '
        'global downward 6 kN/m to both whole roof spans and apply Fx=+4.9 kN '
        'and Fz=-49 kN together at J. All beam-column joints are rigid. Report '
        'ux and uz at L, J and R; Fx, Fz and My at every base A, B and C; '
        'and the local M2 bending moment at the lower and upper ends of the '
        'middle column CM, using sections immediately inside that member.',
    47: '用 OpenSees 分析跨度 18 m、柱高 7 m 的平屋面刚架，两柱脚固定。左柱在 '
        'J(0,0,3) m 处分段，从该实际连通节点向右悬挑 6 m 夹层梁至 T(6,0,3) m；'
        '夹层自由端无支座，全部连接刚接。唯一工况 D 在屋面施加全局向下 6 kN/m，'
        '在夹层梁施加全局向下 4 kN/m，各按各自实际梁长加载。报告夹层自由端 T '
        '和两屋面柱顶 L/R 的 ux、uz，夹层梁 MEZZ 根部构件内侧截面的 M2，'
        '以及两柱脚 A/B 的 Fx、Fz、My。',
    48: 'Use OpenSees to analyze the symmetric pitched-roof portal frame: span '
        '20 m, eaves height 6 m and ridge P=(10,0,8) m. Both bases are fixed '
        'and the eaves and ridge joints are rigid. In load case D, apply '
        'global downward 6 kN/m separately to both inclined roof members, '
        'measured per metre of actual sloping member length. Report ux and uz '
        'at the ridge P and both eaves L/R, all six local section-force '
        'components N/V2/V3/T/M2/M3 immediately inside both ends of both '
        'inclined roof members SL/SR, and Fx/Fz/My at each fixed base A/B. '
        'Keep the distributed loads vertical in global axes.',
    49: '用 OpenSees 分析跨度 24 m、檐高 6 m、偏置屋脊 P(10,0,8) m 的刚架。'
        '两柱脚固定，檐口及屋脊刚接。唯一工况 D 中左坡 SL 按实际坡长施加 '
        '5 kN/m、右坡 SR 按实际坡长施加 7 kN/m，方向均为全局向下。'
        '报告屋脊 P 和两柱顶 L/R 的 ux、uz，左右坡梁各自两端构件内侧截面的 '
        'M2 弯矩，以及两柱脚 A/B 的 Fx、Fz、My。',
    50: 'Use OpenSees to analyze the stepped-roof portal frame with a 12 m '
        'left span at Z=6 m and an 18 m right span at Z=8 m. Fix the three '
        'bases at X=0,12,30 m. The single middle column has separate rigid '
        'joints J6=(12,0,6) and J8=(12,0,8) m connected by the 2 m column '
        'segment CM2. The left roof joins J6 and the right roof joins J8. '
        'Preserve the connected roof-midpoint nodes M1=(6,0,6) and '
        'M2=(21,0,8) m. Load case D applies global downward 5 kN/m over '
        'the entire left roof and 7 kN/m over the entire right roof. Report '
        'ux and uz at both middle-column roof joints J6/J8, both outer column '
        'tops L/R and both roof midpoints M1/M2, plus Fx/Fz/My at each base A/B/C.',
}

FRAME_NOTES = [
    'The source leaves the material/section appendix unspecified. Frozen author choice: '
    'one idealized linear-elastic steel material, E=206000 MPa, nu=0.30, '
    'G=E/[2(1+nu)], rho=7850 kg/m3; solid rectangular roof section 0.30 m by '
    '0.60 m, column section 0.50 m by 0.50 m, and, where present, '
    'mezzanine section 0.25 m by 0.50 m. Tabulated A/Iy/Iz/J are explicit inputs.',
    'Member axes: local 1 is i-to-j, local 2 is global +Y, and local 3 is '
    'local 1 cross local 2. In-plane bending is M2. Euler-Bernoulli '
    'kinematics include axial deformation but exclude shear deformation. '
    'Unspecified node displacements mean both in-plane translations ux/uz; '
    'base reactions include in-plane force components Fx/Fz and moment My.',
    'Load case D contains the stated simultaneously applied loads with unit factors. '
    'It does not add self-weight. No additional load combinations are supplied.',
]


def requests(number, m, core):
    qs = []
    ds = []
    extras = []

    def nodes(ids, components):
        for n in ids:
            for c in components:
                qs.append(core.qnode(m, n, c))

    def ends(member, components):
        for x, side in ((0.0, 'right'), (length(m, member), 'left')):
            for c in components:
                qs.append(core.qmember(m, member, x, c, side=side))

    if number in (41, 42):
        nodes(['P'] if number == 41 else ['A2', 'B2', 'C2'], ['ux', 'uy', 'uz'])
        for e in m['elements']:
            qs.append(core.qmember(m, e['id'], length(m, e['id']) / 2, 'N'))
        bases = ['A', 'B', 'C', 'D'] if number == 41 else ['A0', 'B0', 'C0']
        nodes(bases, ['Fx', 'Fy', 'Fz'])
        if number == 42:
            # Signed directional totals retain the individual support operands.
            for component in ('Fx', 'Fy', 'Fz'):
                ids = [q['id'] for q in qs if q['location']['kind'] == 'node'
                       and q['location']['id'] in bases and q['component'] == component]
                ds.append(dict(id=f'case:D:total-base:{component}', operation='sum',
                               operands=ids, unit='kN',
                               description=f'Signed sum of {component} reactions at A0, B0 and C0 in load case D.'))
    else:
        observation = {43: ['L', 'R'], 44: ['L', 'J', 'R', 'M1', 'M2'],
                       45: ['L', 'R'], 46: ['L', 'J', 'R'],
                       47: ['T', 'L', 'R'], 48: ['P', 'L', 'R'],
                       49: ['P', 'L', 'R'], 50: ['J6', 'J8', 'L', 'R', 'M1', 'M2']}
        nodes(observation[number], ['ux', 'uz'])
        if number in (43, 45):
            nodes(['M'], ['uz'])
        nodes(['A', 'B', 'C'] if number in (44, 46, 50) else ['A', 'B'],
              ['Fx', 'Fz', 'My'])
        if number == 45:
            qs.append(core.qmember(m, 'RL', 10.5, 'M2', side='left'))
            qs.append(core.qmember(m, 'RR', 0.0, 'M2', side='right'))
            qs.append(core.qmember(m, 'RL', 10.5, 'V3', side='left'))
            qs.append(core.qmember(m, 'RR', 0.0, 'V3', side='right'))
        elif number == 46:
            ends('CM', ['M2'])
        elif number == 47:
            qs.append(core.qmember(m, 'MEZZ', 0.0, 'M2', side='right'))
        elif number in (48, 49):
            for member in ('SL', 'SR'):
                ends(member, ['N', 'V2', 'V3', 'T', 'M2', 'M3'] if number == 48 else ['M2'])
    return qs, ds, extras


def author(core):
    for number, builder in BUILDERS.items():
        m = builder()
        used = {e['section'] for e in m['elements']}
        m['sections'] = [s for s in m['sections'] if s['id'] in used]
        notes = FRAME_NOTES[:]
        if number == 41:
            notes = [
                'The missing appendix is completed with one linear-elastic steel material: '
                'E=206000 MPa, nu=0.30, G=E/[2(1+nu)], rho=7850 kg/m3. '
                'Every axial-only member has A=0.004 m2. The 0.10 by 0.04 m '
                'rectangular section supplies this area; its bending properties are inactive.',
                'All truss rotations are suppressed as inactive DOFs. Only the four base '
                'translations are structural supports; no rotational moment transfer exists.',
            ]
        elif number == 42:
            notes = [
                'The source promises a connection/property table but supplies none. '
                'Frozen author completion: nine nodes on three equilateral triangular '
                'levels (Z=0,3,6 m), six vertical chords, nine horizontal ties, and '
                'two unconnected crossing diagonals on every side face of each tier. '
                'The explicit endpoint table defines all 27 bars. Cross-level bars '
                'span adjacent levels, with distinct nodes retained at every elevation.',
                'One steel material has E=206000 MPa, nu=0.30, G=E/[2(1+nu)], '
                'rho=7850 kg/m3. CHORD, HORIZONTAL and DIAGONAL areas are respectively '
                '0.0064, 0.0049 and 0.0036 m2 (solid square 0.08, 0.07 and 0.06 m '
                'sections). Only axial stiffness is active. Rotations are inactive '
                'DOFs suppressed numerically; all physical joints are pinned.',
                'Each directional base reaction total is the signed sum of the three '
                'same-case, same-component reactions at A0, B0 and C0. The three sum '
                'requests name their operands explicitly and use kN throughout.',
            ]
        if number in (43, 44, 45, 50):
            notes.append('Roof midpoints are actual shared nodes between collinear beam '
                         'segments with identical properties and rigid continuity; no '
                         'additional support, mass, release or concentrated load is '
                         'introduced by an observation node. STD-045 alone has its '
                         'explicitly specified 60 kN equipment load at that node.')
        if number in (48, 49):
            notes.append('Global vertical line loads are specified per metre of actual '
                         'inclined member length, not per metre of horizontal projection.')
        if number == 47:
            notes.append('The left column is split at the 3 m mezzanine connection. '
                         'The 6 m cantilever free end has no in-plane restraints.')
        if number == 50:
            notes.append('The middle column has a 6 m lower segment and a 2 m upper '
                         'segment; the Z=6 m and Z=8 m roof joints are different nodes.')
        qs, ds, extras = requests(number, m, core)
        tail = (' 使用附件中的完整节点、构件、材料、截面和荷载表。采用一阶线弹性静力，'
                '关闭自重、P-Delta、刚性楼板及刚臂。所有结果注明工况、位置、分量、符号和单位；'
                '位移为 m、力为 kN、力矩为 kN·m。保存实际 OpenSees 版本、可运行输入、'
                '日志和原始结果，核查整体平衡。' if number % 2 else
                ' Use the complete attached node, member, property and load tables. '
                'Use first-order linear-elastic static analysis with self-weight, '
                'P-Delta, rigid diaphragms and rigid offsets disabled. State the load '
                'case, location, component, sign and unit for every result: m for '
                'displacements, kN for forces and kN.m for moments. Preserve the '
                'actual OpenSees version, runnable input, execution log and raw '
                'results, and check global equilibrium.')
        core.emit(number, m, PROMPTS[number] + tail, qs, derived=ds,
                  extra_outputs=extras, notes=notes)


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0]]


def normalize(v):
    magnitude = math.sqrt(dot(v, v))
    assert magnitude > 1e-14
    return [x / magnitude for x in v]


def cholesky_solve(K, F):
    """Symmetric positive definiteness and solve, using only the stdlib."""
    n = len(F)
    if not n:
        return [], 1.0
    diagonal_scale = max(K[i][i] for i in range(n))
    L = [[0.0] * n for _ in range(n)]
    min_pivot = math.inf
    for i in range(n):
        for j in range(i + 1):
            remaining = K[i][j] - dot(L[i][:j], L[j][:j])
            if i == j:
                assert remaining > diagonal_scale * 1e-12, (
                    'Mechanism or ill-conditioned constrained stiffness', i, remaining, diagonal_scale)
                min_pivot = min(min_pivot, remaining)
                L[i][j] = math.sqrt(remaining)
            else:
                L[i][j] = remaining / L[j][j]
    y = [0.0] * n
    for i in range(n):
        y[i] = (F[i] - dot(L[i][:i], y[:i])) / L[i][i]
    u = [0.0] * n
    for i in range(n - 1, -1, -1):
        u[i] = (y[i] - sum(L[j][i] * u[j] for j in range(i + 1, n))) / L[i][i]
    return u, min_pivot / diagonal_scale


def check_model(m, factors=None, with_values=False):
    """Small independent elastic author audit; never a scoring reference.

    Supports 2D/3D frame and axial-only elements, global nodal forces and
    constant global member line loads (including partial spans). The return
    value contains only stability/equilibrium diagnostics unless the internal
    author checks explicitly request an in-memory quantity reader.
    """
    ns = {n['id']: n for n in m['nodes']}
    ix = {name: 6 * i for i, name in enumerate(ns)}
    ndof = 6 * len(ns)
    K = [[0.0] * ndof for _ in range(ndof)]
    F = [0.0] * ndof
    materials = {p['id']: p for p in m['materials']}
    sections = {p['id']: p['properties'] for p in m['sections']}
    factors = factors or {m['load_cases'][0]['id']: 1.0}
    loads = [(l, factors.get(c['id'], 0)) for c in m['load_cases'] for l in c['loads']
             if factors.get(c['id'], 0)]
    for load, factor in loads:
        if load['type'] == 'nodal':
            for j, key in enumerate(('fx', 'fy', 'fz', 'mx', 'my', 'mz')):
                F[ix[load['node']] + j] += factor * load.get(key, 0)
        elif load['type'] not in ('distributed', 'point'):
            raise ValueError(f"Unsupported author-check load type: {load['type']}")
    member_data = {}
    for e in m['elements']:
        a, b = (ns[name] for name in e['nodes'])
        displacement = [b[k] - a[k] for k in ('x', 'y', 'z')]
        L = math.sqrt(dot(displacement, displacement))
        ex = normalize(displacement)
        if m['coordinate_system']['dimension'] == '2d':
            ey = [0.0, 1.0, 0.0]
        else:
            ey = normalize(cross(m['metadata']['elementReferenceVectors'][e['id']], ex))
        ez = cross(ex, ey)
        angle = math.radians(e.get('rotation_angle', 0))
        ey, ez = ([math.cos(angle) * y + math.sin(angle) * z for y, z in zip(ey, ez)],
                  [-math.sin(angle) * y + math.cos(angle) * z for y, z in zip(ey, ez)])
        R = [ex, ey, ez]
        T = [[0.0] * 12 for _ in range(12)]
        for block in range(4):
            for i in range(3):
                for j in range(3):
                    T[block * 3 + i][block * 3 + j] = R[i][j]
        p = sections[e['section']]
        material = materials[e['material']]
        E, G = 1000 * material['E'], 1000 * material['G']
        k = [[0.0] * 12 for _ in range(12)]

        def add_block(dofs, values, scale):
            for i, di in enumerate(dofs):
                for j, dj in enumerate(dofs):
                    k[di][dj] += scale * values[i][j]

        add_block([0, 6], [[1, -1], [-1, 1]], E * p['A'] / L)
        if e['type'] not in ('truss', 'brace'):
            assert not e.get('releases'), 'Released members require a separate author check'
            add_block([3, 9], [[1, -1], [-1, 1]], G * p['J'] / L)
            for dofs, inertia, sign in (([1, 5, 7, 11], p['Iz'], 1),
                                        ([2, 4, 8, 10], p['Iy'], -1)):
                c = sign * 6 * L
                add_block(dofs, [[12, c, -12, c], [c, 4 * L * L, -c, 2 * L * L],
                                 [-12, -c, 12, -c], [c, 2 * L * L, -c, 4 * L * L]],
                          E * inertia / L ** 3)
        f = [0.0] * 12

        def equivalent(x, force, moment, weight):
            """Exact virtual-work interpolation for a force/moment station."""
            t = x / L
            axial = [1 - t, t]
            h = [1 - 3*t*t + 2*t*t*t, L*(t - 2*t*t + t*t*t),
                 3*t*t - 2*t*t*t, L*(-t*t + t*t*t)]
            dh = [(-6*t + 6*t*t)/L, 1 - 4*t + 3*t*t,
                  (6*t - 6*t*t)/L, -2*t + 3*t*t]
            for di, v in zip((0, 6), axial):
                f[di] += weight * force[0] * v
            for di, v in zip((3, 9), axial):
                f[di] += weight * moment[0] * v
            for di, v, dv in zip((1, 5, 7, 11), h, dh):
                f[di] += weight * (force[1] * v + moment[2] * dv)
            for di, v, dv, sign in zip((2, 4, 8, 10), h, dh, (1, -1, 1, -1)):
                f[di] += weight * sign * (force[2] * v - moment[1] * dv)

        for load, factor in loads:
            if load.get('element') != e['id']:
                continue
            assert load.get('reference_frame', 'global') == 'global'
            if load['type'] == 'distributed':
                assert e['type'] not in ('truss', 'brace'), 'Line load on axial-only bar'
                assert not any(k.endswith(('_start', '_end')) for k in load), 'Varying line load needs explicit segmentation'
                start, end = load.get('start', 0), load.get('end', L)
                assert 0 <= start < end <= L + 1e-10
                force = [factor * dot(row, [load.get(k, 0) for k in ('wx', 'wy', 'wz')]) for row in R]
                # Three-point Gauss integrates all cubic shape functions exactly.
                for xi, wi in ((-math.sqrt(3/5), 5/9), (0, 8/9), (math.sqrt(3/5), 5/9)):
                    equivalent((start + end)/2 + (end - start)/2 * xi, force,
                               [0, 0, 0], wi * (end - start)/2)
            elif load['type'] == 'point':
                force = [factor * dot(row, [load.get(k, 0) for k in ('fx', 'fy', 'fz')]) for row in R]
                moment = [factor * dot(row, [load.get(k, 0) for k in ('mx', 'my', 'mz')]) for row in R]
                equivalent(load['position'], force, moment, 1)
        dofs = [ix[name] + j for name in e['nodes'] for j in range(6)]
        kT = [[dot(row, [T[j][column] for j in range(12)]) for column in range(12)] for row in k]
        for i, di in enumerate(dofs):
            F[di] += dot([T[j][i] for j in range(12)], f)
            for j, dj in enumerate(dofs):
                K[di][dj] += sum(T[a][i] * kT[a][j] for a in range(12))
        member_data[e['id']] = dict(k=k, T=T, f=f, dofs=dofs, length=L, kind=e['type'])
    free = [ix[n['id']] + j for n in m['nodes'] for j in range(6) if not n['restraints'][j]]
    reduced = [[K[i][j] for j in free] for i in free]
    active, pivot_ratio = cholesky_solve(reduced, [F[i] for i in free])
    u = [0.0] * ndof
    for i, v in zip(free, active):
        u[i] = v
    reactions = [dot(row, u) - f for row, f in zip(K, F)]
    residual = max((abs(reactions[i]) for i in free), default=0)
    balance = [0.0] * 6
    for n in m['nodes']:
        i = ix[n['id']]
        force = [F[i+j] + reactions[i+j] for j in range(3)]
        moment = cross([n[k] for k in ('x', 'y', 'z')], force)
        for j in range(3):
            balance[j] += force[j]
            balance[j+3] += F[i+j+3] + reactions[i+j+3] + moment[j]
    assert residual < 1e-7 * (1 + max(abs(f) for f in F)), ('Free DOF equilibrium', residual)
    assert max(abs(v) for v in balance) < 1e-6 * (1 + max(abs(f) for f in F)), ('Overall force/moment equilibrium', balance)

    def quantity(location, component):
        if location['kind'] == 'node':
            order = ('ux', 'uy', 'uz', 'rx', 'ry', 'rz') if component[0] in 'ur' else ('fx', 'fy', 'fz', 'mx', 'my', 'mz')
            return (u if component[0] in 'ur' else reactions)[ix[location['id']] + order.index(component.lower())]
        data = member_data[location['id']]
        v = [dot(row, [u[i] for i in data['dofs']]) for row in data['T']]
        action = [dot(row, v) - f for row, f in zip(data['k'], data['f'])]
        if data['kind'] in ('truss', 'brace'):
            assert component == 'N'
            return action[6]
        x = location['positionM']
        assert math.isclose(x, 0, abs_tol=1e-10) or math.isclose(x, data['length'], abs_tol=1e-10), 'Author check reads beam end sections only'
        start = math.isclose(x, 0, abs_tol=1e-10)
        i = ('N', 'V2', 'V3', 'T', 'M2', 'M3').index(component)
        sign = (-1, 1, 1, -1, -1, -1)[i] if start else (1, -1, -1, 1, 1, 1)[i]
        return sign * action[i if start else i + 6]

    result = dict(method='stdlib-direct-stiffness-author-audit', freeResidual=residual,
                  forceMomentBalance=balance, activeStiffnessRank=len(free),
                  minimumCholeskyPivotRatio=pivot_ratio, dofs=ndof)
    return (quantity, result) if with_values else result


def check():
    """Mechanical author checks only; no reference answers or native claims."""
    plan = {r['id']: r for r in json.loads(
        (ROOT / 'planning/capability-coverage-300.json').read_text())['cases']}
    source_dir = ROOT / 'planning/sources'
    if not source_dir.exists():
        source_dir = ROOT.parents[1] / 'planning/sources'
    tasks = {r['id']: r for r in json.loads(
        (source_dir / 'all-tasks-engines-v2.json').read_text())}
    models = {r['taskId']: r for r in json.loads(
        (source_dir / 'all-models-engines-v2.json').read_text())}
    expected = {
        41: (5, 8, [15, 0, -40]), 42: (9, 27, [30, 0, 0]),
        43: (5, 4, [0, 0, -108]), 44: (8, 7, [0, 0, -216]),
        45: (5, 4, [0, 0, -228]), 46: (6, 5, [4.9, 0, -265]),
        47: (6, 5, [0, 0, -132]),
        48: (5, 4, [0, 0, -12 * math.sqrt(104)]),
        49: (5, 4, [0, 0, -5 * math.sqrt(104) - 7 * math.sqrt(200)]),
        50: (9, 8, [0, 0, -186]),
    }
    reports = []
    for number, builder in BUILDERS.items():
        case_id = f'STD-{number:03d}'
        for field, retained in plan[case_id]['sourceRequirements'].items():
            group, key = field.split('.')
            original = (tasks[case_id][key] if group == 'task' else
                        models[case_id][key] if group == 'model' else
                        tasks[case_id]['enginePlan'][key])
            assert retained == original, (case_id, 'source mismatch', field)
        m = builder()
        assert (len(m['nodes']), len(m['elements'])) == expected[number][:2]
        node_ids = {n['id'] for n in m['nodes']}
        assert len(node_ids) == len(m['nodes'])
        edge_ids = {e['id'] for e in m['elements']}
        assert len(edge_ids) == len(m['elements'])
        assert all(set(e['nodes']) <= node_ids and length(m, e['id']) > 0
                   for e in m['elements'])
        adjacency = {n: set() for n in node_ids}
        for e in m['elements']:
            a, b = e['nodes']; adjacency[a].add(b); adjacency[b].add(a)
        seen = {next(iter(node_ids))}
        todo = list(seen)
        while todo:
            for n in adjacency[todo.pop()] - seen:
                seen.add(n); todo.append(n)
        assert seen == node_ids
        force = [0.0] * 3
        for load in m['load_cases'][0]['loads']:
            if load['type'] == 'nodal':
                for i, k in enumerate(('fx', 'fy', 'fz')):
                    force[i] += load.get(k, 0)
            else:
                for i, k in enumerate(('wx', 'wy', 'wz')):
                    force[i] += load.get(k, 0) * length(m, load['element'])
        assert all(math.isclose(a, b, abs_tol=1e-11, rel_tol=0) for a, b in zip(force, expected[number][2]))
        value, result = check_model(m, {'D': 1}, with_values=True)
        assert max(abs(v) for v in result['forceMomentBalance']) < 1e-7
        if number == 41:
            for member in ('AB', 'BC', 'CD', 'DA'):
                assert abs(value(dict(kind='member', id=member, positionM=0, side='right'), 'N')) < 1e-10
            assert math.isclose(value(dict(kind='node', id='P'), 'uy'), 0, abs_tol=1e-12)
        if number in (43, 44, 45, 48):
            assert math.isclose(value(dict(kind='node', id='L'), 'uz'),
                                value(dict(kind='node', id='R'), 'uz'), abs_tol=1e-12)
            assert math.isclose(value(dict(kind='node', id='L'), 'ux'),
                                -value(dict(kind='node', id='R'), 'ux'), abs_tol=1e-12)
        if number == 45:
            vl = value(dict(kind='member', id='RL', positionM=10.5, side='left'), 'V3')
            vr = value(dict(kind='member', id='RR', positionM=0, side='right'), 'V3')
            assert math.isclose(abs(vr - vl), 60, abs_tol=1e-8)
            assert adjacency['M'] == {'L', 'R'}
        if number == 47:
            assert adjacency['T'] == {'J'}
            tip = next(n for n in m['nodes'] if n['id'] == 'T')
            assert not any(tip['restraints'][i] for i in (0, 2, 4))
            assert math.isclose(abs(value(dict(kind='member', id='MEZZ', positionM=0,
                                              side='right'), 'M2')), 72, abs_tol=1e-8)
        if number == 50:
            assert adjacency['J6'] == {'B', 'J8', 'M1'}
            assert adjacency['J8'] == {'J6', 'M2'}
            assert length(m, 'CM2') == 2
        reports.append(dict(id=case_id, status='author-mechanical-check-only',
                            nativeExecution='pending', exactSourceFieldsCompared=15,
                            sourceRequirementCount=len(plan[case_id]['requirements']), **result))
    print(json.dumps(reports, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Run mechanical/source checks without writing cases')
    args = parser.parse_args()
    if args.check:
        check()
    else:
        import std_a_core
        author(std_a_core)
