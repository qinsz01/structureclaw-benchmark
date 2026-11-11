"""Author INT-027..036 from the complete planning rows and original topology tables.

No solver/reference values are authored. --check performs independent planar truss
stiffness, equilibrium, topology and interaction checks using the Python stdlib.
"""
from copy import deepcopy
from pathlib import Path
import argparse
import json
import math
import sys

from int_a_common import (ROOT, model, node, elem, load, turn, tables, quantity,
                          member_quantity, sources, write_case)

TRUSS_FREE = [False, True, False, True, True, True]
TRUSS_PIN = [True] * 6
TRUSS_ROLLER = [False, True, True, True, True, True]
CASE_IDS = [f'INT-{i:03d}' for i in range(27, 37)]


def base(area_factors=None):
    m = model()
    m['materials'] = [dict(id='M1', name='steel', type='steel', E=205000,
                          G=205000 / 2.6, nu=.3, rho=7850)]
    m['sections'] = [dict(id=k, name=k, type='rod', properties=dict(
        A=round(.01 * factor, 12), Iy=1e-5, Iz=1e-5, J=2e-5))
        for k, factor in (area_factors or {'A': 1}).items()]
    return m


def n(m, name, x, z, support=None):
    node(m, name, x, z, restraint=deepcopy(support or TRUSS_FREE))


def e(m, name, start, end, sec='A'):
    elem(m, name, start, end, kind='truss', sec=sec)


def p(m, name, node_id, fz=0, fx=0):
    load(m, type='nodal', id=name, node=node_id, fx=fx, fy=0, fz=fz,
         mx=0, my=0, mz=0)


def parallel(m, width, heights, bottom_sec='A', top_sec='A', vertical_secs=None):
    panels = len(heights) - 1
    for i, z in enumerate(heights):
        n(m, f'B{i}', width * i, 0,
          TRUSS_PIN if i == 0 else TRUSS_ROLLER if i == panels else None)
        n(m, f'T{i}', width * i, z)
    for i in range(panels):
        e(m, f'BC{i}', f'B{i}', f'B{i+1}', bottom_sec)
        e(m, f'TC{i}', f'T{i}', f'T{i+1}', top_sec)
    for i in range(panels + 1):
        e(m, f'V{i}', f'B{i}', f'T{i}', (vertical_secs or {}).get(i, 'A'))


def outputs_at(node_id, all_members=None):
    out = [quantity(node_id, c) for c in ('ux', 'uz')]
    out += [quantity('B0', c) for c in ('Fx', 'Fz')]
    out.append(member_quantity('BC0', 'N'))
    if all_members:
        out += [member_quantity(x['id'], 'N') for x in all_members if x['id'] != 'BC0']
    return out


def output_text(at, en):
    if en:
        return (f'Report signed Ux and Uz at {at}, left support B0 reactions Fx and Fz, '
                'and axial force N in the first bottom chord BC0. Include the node/member ID, '
                'position, global direction or axial tension/compression sign, m or kN units, '
                'load case D and current turn for every result. Use positive N for tension. '
                'Use a fresh OpenSees run after each physical change and retain its input, '
                'version, settings, successful log, run ID and raw-result mapping. '
                'Ask about unresolved essential input before reporting numerical results.')
    return (f'报告{at}的带符号Ux、Uz，左支座B0反力Fx、Fz，以及首根下弦BC0轴力N。'
            '每个结果注明节点/杆件ID、位置、全局方向或轴力拉压符号、m或kN单位、工况D和当前轮次；轴力拉为正。'
            '物理状态修改后使用OpenSees重新计算，保留输入、版本、设置、成功日志、运行ID及原始结果对应关系。'
            '必需输入未明确前先澄清，不编造数值。')


def decisions(extra):
    return [
        'E=205000 MPa, nu=0.3, rho=7850 kg/m3 and base A=0.01 m2 retain the explicit property records for linked legacy trusses; these same values are frozen author completions for new trusses lacking an original property appendix. G=E/[2(1+nu)].',
        'The missing full section appendix is frozen as generic rod properties Iy=Iz=1e-5 m4 and J=2e-5 m4 for every section. These unused transverse properties do not supply bending stiffness to axial-only elements. Only A is multiplied by the source area factors.',
        'All nodes constrain inactive uy,rx,ry,rz. The left pin also constrains ux,uz; the right roller constrains uz. Rotations are bookkeeping constraints, not flexural member or joint stiffness.',
        'Load case D is the sole explicit source loading, with no automatic combinations or self-weight. Requested left reaction means its active in-plane Fx,Fz components; other reaction components are identically zero.',
        *extra,
    ]


def emit(index, states, turns, public, at, extra=None, derived=None, all_members=False):
    case_id = f'INT-{index:03d}'
    cov, task, sm = sources(case_id)
    # Every exact row, source requirement and requirement ID remains in the contract.
    assert cov['plannedEngine'] == 'OpenSees' and task['baseGroup'] == sm['id']
    requests = [outputs_at(at, m['elements'] if all_members else None) for m in states]
    return write_case(case_id, states, turns, requests, public,
                      decisions=decisions(extra or []), derived=derived,
                      reported_quantities=[[q['id'] for q in outputs_at(at)] for _ in states] if all_members else None,
                      output_turns={'s1:case:D:all-members:max-abs-N':['t2']} if index==33 else None,
                      source_audit=[dict(source='planning/capability-coverage-300.json', row=case_id),
                                    dict(source='planning/sources/all-tasks-engines-v2.json', row=case_id),
                                    dict(source='planning/sources/all-models-engines-v2.json', row=sm['id']),
                                    dict(sourceRequirementsRetained=True, requirementCount=len(cov['requirements']))])


def author():
    # INT-027: legacy table has its central falling diagonal T2-B3.
    m = base({'UP': 1, 'LOW': 1.4, 'WEB': .7})
    parallel(m, 3, [2.5] * 6, 'LOW', 'UP', {i: 'WEB' for i in range(6)})
    for i, (a, b) in enumerate([('T0', 'B1'), ('T1', 'B2'), ('T2', 'B3'), ('B3', 'T4'), ('B4', 'T5')]):
        e(m, f'DG{i}', a, b, 'WEB')
    for i in range(1, 5):
        p(m, f'top-{i}', f'T{i}', -10)
    m2 = deepcopy(m)
    for ld in m2['load_cases'][0]['loads']:
        ld['fz'] = -15
    instr = '按附件建立15m、5节间、高2.5m的M-INT-027；必须按明示端点表连接。' + output_text('x=6m上弦T2', False)
    ts = [turn(instr, 1, attachments=['input-tables.txt']),
          turn('仅把四个内部上弦T1、T2、T3、T4原各10kN向下力替换为各15kN；端部上下弦不加载，全部拓扑、支座和分组属性保持。' + output_text('x=6m上弦T2', False), 2,
               changedFields=[f'/load_cases/0/loads/{i}/fz' for i in range(4)],
               preservedFields=['/nodes', '/elements', '/materials', '/sections', '/analysis_control'])]
    emit(27, [m, m2], ts, {'input-tables.txt': tables(m, 'zh', '截面UP=A，LOW=1.4A，WEB=0.7A；A=0.01m2。')}, 'T2',
         ['Node and member endpoints preserve the original truss-pratt-static message: 12 nodes and 21 rods.',
          'Legacy inconsistency: fixtures/drawings/truss-pratt-15m-top10.dxf reverses all five diagonals relative to the named truss-pratt-static source message. This case follows the explicit endpoint sequence in that named source: T0-B1,T1-B2,T2-B3,B3-T4,B4-T5. The new attachment makes this frozen choice explicit; no old numerical truth is reused.'])

    # INT-028: never place resolved 15 kN in the first-turn force entries.
    m = base()
    parallel(m, 3, [1.6, 1.9, 2.2, 2.5, 2.2, 1.9, 1.6])
    for i in range(6):
        e(m, f'DG{i}', f'T{i}', f'B{i+1}')
    for i in range(1, 6):
        p(m, f'bottom-{i}', f'B{i}', -15)
    p(m, 'right-horizontal', 'T6', fx=-6)
    public = deepcopy(m)
    for ld in public['load_cases'][0]['loads'][:5]:
        ld['fz'] = '-15, unit unresolved: tonne-force or kN'
    instr = ('Build M-INT-028 using the attached 18 m trapezoidal truss tables. The five downward '
             'bottom-chord loads are recorded as "15 tonnes or 15 kN"; their force unit is unconfirmed. '
             'The separate force at T6 is confirmed as Fx=-6 kN. ' + output_text('B3 at x=9 m on the bottom chord', True))
    ts = [turn(instr, None, 'clarify', ['input-tables.txt'],
               unresolved=['/load_cases/0/loads/0:5/forceUnit'],
               questions=['Are the five downward bottom-chord forces 15 kN each or 15 tonne-force each?']),
          turn('The five bottom-chord loads are 15 kN downward each. Preserve their nodes B1 through B5 and the separate Fx=-6 kN force at T6. ' + output_text('B3 at x=9 m on the bottom chord', True), 1)]
    emit(28, [m], ts, {'input-tables.txt': tables(public, 'en', 'Exception to the force-unit header: bottom-1 through bottom-5 have unresolved units; only their downward direction and magnitude 15 are supplied. Other force entries use kN.')}, 'B3',
         ['The heights and all 25 rod endpoints retain truss-trapezoidal-static: upper slope magnitude 1/10 and verticals at every panel line. All five unresolved force entries are redacted, including their unit labels.'])

    # INT-029: special horizontal rod T1-T3 survives the zero-height correction.
    m = base({'UP': 1, 'LOW': 1.6, 'WEB': 1})
    for nid, x, z in [('B0', 0, 0), ('B1', 6, 0), ('B2', 12, 0), ('T1', 3, 1.5), ('T2', 6, 3), ('T3', 9, 1.5)]:
        n(m, nid, x, z, TRUSS_PIN if nid == 'B0' else TRUSS_ROLLER if nid == 'B2' else None)
    e(m, 'BC0', 'B0', 'B1', 'LOW'); e(m, 'BC1', 'B1', 'B2', 'LOW')
    for i, (a, b) in enumerate([('B0', 'T1'), ('T1', 'T2'), ('T2', 'T3'), ('T3', 'B2')]):
        e(m, f'TC{i}', a, b, 'UP')
    for i in range(1, 4):
        e(m, f'W{i}', 'B1', f'T{i}', 'WEB'); p(m, f'top-{i}', f'T{i}', -20)
    e(m, 'H1', 'T1', 'T3', 'WEB')
    public = deepcopy(m)
    for nd in public['nodes']:
        nd['z'] = 0
    instr = '按附件建立跨度12m的M-INT-029。当前记录总高H=0m；T1/T3高程为H/2，T2为H，完整6节点10杆表见附件。' + output_text('顶点T2', False)
    ts = [turn(instr, None, 'clarify', ['input-tables.txt'], unresolved=['/geometry/height'],
               questions=['总高记录为0m导致三角形退化且B1与T2重合；请确认正确高度。']),
          turn('总高度应为H=3m：T1=(3,0,1.5)m，T2=(6,0,3)m，T3=(9,0,1.5)m。其余6节点10杆连接、特殊水平连杆H1、下弦1.6A分组、支座和三个20kN荷载均保持。' + output_text('顶点T2', False), 1)]
    emit(29, [m], ts, {'input-tables.txt': tables(public, 'zh', '当前输入H=0m，表中退化节点坐标按该记录给出；不得自动补猜高度。水平连杆H1连接T1与T3。')}, 'T2',
         ['All six nodes and ten rods, including T1-T3 horizontal H1, preserve truss-triangle-static. The initial public table uses zero height throughout; no reference vector or valid-height copy is attached.'])

    # INT-030: explicit written conflict is not silently resolved by the author.
    m = base(); parallel(m, 2, [2] * 7)
    for i in range(6):
        e(m, f'DG{i}', f'B{i}' if i % 2 == 0 else f'T{i}', f'T{i+1}' if i % 2 == 0 else f'B{i+1}')
    for i in range(1, 6):
        p(m, f'bottom-{i}', f'B{i}', -8)
    p(m, 'additional-top', 'T3', -11)
    instr = ('Build M-INT-030, described in the text as a pure Warren truss with no vertical members. '
             'The attached connection table includes vertical members at every panel line. '
             + output_text('T3 at x=6 m on the top chord', True))
    ts = [turn(instr, None, 'clarify', ['input-tables.txt'], unresolved=['/topology/vertical-members'],
               questions=['Should the explicit table verticals be retained, or should the conflicting description with no verticals govern?']),
          turn('Retain every vertical and alternating diagonal in the attachment. Preserve the five 8 kN bottom-node forces and the independent 11 kN downward force at top node T3. ' + output_text('T3 at x=6 m on the top chord', True), 1)]
    emit(30, [m], ts, {'input-tables.txt': tables(m, 'en', 'The table lists V0 through V6, while the accompanying text says no verticals; the precedence of those conflicting statements is unresolved.')}, 'T3',
         ['All 14 nodes and 25 rods preserve the explicit truss-warren-en table. The first attachment retains the conflicting table without declaring it authoritative.'])

    # INT-031: end-panel web section membership is frozen in an explicit table.
    m = base({'A': 1, 'ENDWEB': 2})
    parallel(m, 3, [3] * 7, vertical_secs={i: 'ENDWEB' for i in [0, 1, 5, 6]})
    for i in range(6):
        e(m, f'DG{i}', f'B{i}' if i % 2 == 0 else f'T{i}', f'T{i+1}' if i % 2 == 0 else f'B{i+1}', 'ENDWEB' if i in [0, 5] else 'A')
    for i in range(1, 6):
        p(m, f'point-{i}', f'T{i}', -12)
    m2 = deepcopy(m)
    for i in range(4):
        m2['load_cases'][0]['loads'][i]['node'] = f'B{i+1}'
    instr = '按附件建立18m、6节间、高3m的M-INT-031；上弦T1至T5各向下12kN。' + output_text('x=9m上弦T3', False)
    ts = [turn(instr, 1, attachments=['input-tables.txt']),
          turn('将x=3、6、9、12m四个上弦T1至T4节点力移到同x下弦B1至B4，各12kN幅值方向不变；旧上弦点力删除，x=15m上弦T5的12kN保持。拓扑、支座与所有分组属性不变。' + output_text('x=9m上弦T3', False), 2,
               changedFields=[f'/load_cases/0/loads/{i}/node' for i in range(4)],
               preservedFields=['/nodes', '/elements', '/materials', '/sections', '/load_cases/0/loads/4', '/analysis_control'])]
    emit(31, [m, m2], ts, {'input-tables.txt': tables(m, 'zh', '端节间腹杆分组明确为V0、V1、DG0、V5、V6、DG5，均为2A；其他腹杆与全部弦杆均A。')}, 'T3',
         ['Original truss-roof-en endpoints retained (14 nodes,25 rods). The absent detailed area table is completed by assigning end-panel boundary verticals V0,V1,V5,V6 and end diagonals DG0,DG5 to 2A; shared boundary verticals are listed once.'])

    # INT-032: use the exact noninteger apex and omit one endpoint everywhere public.
    m = base()
    for i in range(6):
        n(m, f'B{i}', 3 * i, 0, TRUSS_PIN if i == 0 else TRUSS_ROLLER if i == 5 else None)
    for nid, x, z in [('T1', 3, 1), ('T2', 6, 2), ('AP', 7.5, 2.5), ('T3', 9, 2), ('T4', 12, 1)]:
        n(m, nid, x, z)
    for i in range(5):
        e(m, f'BC{i}', f'B{i}', f'B{i+1}')
    roof = ['B0', 'T1', 'T2', 'AP', 'T3', 'T4', 'B5']
    for i in range(6):
        e(m, f'TC{i}', roof[i], roof[i+1])
    for i in range(1, 5):
        e(m, f'V{i}', f'B{i}', f'T{i}')
    for i, (a, b) in enumerate([('B1', 'T2'), ('B2', 'AP'), ('B3', 'AP'), ('B4', 'T3')]):
        e(m, f'DG{i}', a, b)
    for nid in ['T1', 'T2', 'AP', 'T3', 'T4']:
        p(m, f'roof-{nid}', nid, -10)
    p(m, 'apex-horizontal', 'AP', fx=7)
    public = deepcopy(m)
    next(x for x in public['elements'] if x['id'] == 'DG1')['nodes'][1] = None
    instr = ('Build M-INT-032 using the tables. Member DG1 has only its start node B2 recorded; '
             'its end node is missing. Preserve the explicit geometry and loads. '
             + output_text('apex AP at (7.5,0,2.5) m', True))
    ts = [turn(instr, None, 'clarify', ['input-tables.txt'], unresolved=['/elements/16/nodes/1'],
               questions=['What is the missing end node of DG1, whose start node is B2?']),
          turn('The missing end of DG1 is the apex AP at (x,z)=(7.5,2.5) m. Fill only that endpoint. Keep the apex Fx=+7 kN and all five downward 10 kN roof-node forces. ' + output_text('apex AP at (7.5,0,2.5) m', True), 1)]
    emit(32, [m], ts, {'input-tables.txt': tables(public, 'en', 'null in DG1.nodes[1] means the endpoint has not been supplied; it is not permission to remove the member. There is no additional endpoint rule.')}, 'AP',
         ['The 11 nodes and 19 rods retain std-truss-tri-en, including B2-AP and B3-AP. The public initial DG1 endpoint is null; no derived local reference vector or resolved duplicate appears in attachments.'])

    # INT-033: same complete state, clarification only changes result scope.
    m = base(); parallel(m, 3, [2.5] * 6)
    for i in range(5):
        e(m, f'DG{i}', f'B{i+1}', f'T{i}')
    p(m, 'odd-1', 'B1', -10); p(m, 'odd-3', 'B3', -10)
    instr = ('按附件建立平行弦M-INT-033，另外报告“三角形的最大轴力”。'
             '现有物理模型及下列五项常规输出的输入已完整，请先分析并报告这五项结果；额外的最大轴力范围待澄清，先询问其具体含义，不猜测该项数值。'
             + output_text('x=6m上弦T2', False))
    ts = [turn(instr, 1, 'analyze', ['input-tables.txt'], unresolved=['/requestedOutputs/maximumAxialForce/scope'],
               questions=['“三角形的最大轴力”具体指哪些杆件，且按带符号最大还是轴力绝对值最大取值？'],
               clarificationBlocksAnalysis=False),
          turn('这里指本题连接表全部21根杆的轴力绝对值最大者。若有并列控制杆，可报告其中任意一根（或全部），并逐根注明控制杆ID、该杆的带符号轴力及拉/压、单位和工况D；保留平行弦12节点21杆及仅B1/B3各10kN向下力。模型未改变，可以复用可追溯的当前状态结果。' + output_text('x=6m上弦T2', False), 1, 'query',
               changedFields=[], preservedFields=['/nodes', '/elements', '/materials', '/sections', '/load_cases', '/analysis_control'])]
    ds = [[dict(id='case:D:all-members:max-abs-N', operation='max_abs', tiePolicy='any',
                operands=[member_quantity(x['id'], 'N')['id'] for x in m['elements']], unit='kN',
                description='全部21根杆轴力绝对值最大者；若有并列控制杆，可报告其中任意一根（或全部），并逐根注明控制杆ID、该杆的带符号轴力及拉/压、单位和工况D。')]]
    emit(33, [m], ts, {'input-tables.txt': tables(m, 'zh', '明确为12节点21杆的平行弦；BC0为B0至B1。仅B1和B3各向下10kN。')}, 'T2',
         ['All STRUCT line endpoints were read from fixtures/drawings/truss-simple-tri.dxf and retained. The original four-node loading is replaced only by the source-specified B1,B3 loads.',
          'T1 has a complete calculable model: analyze and report the five defined baseline quantities while asking the additional maximum-force scope question. clarificationBlocksAnalysis=false applies only to that unresolved output scope. T2 queries the same physical state after scope resolution and may reuse its traceable result; no physical edit or second hidden state is invented.',
          'All 21 member forces remain reference operands for the governing signed maximum. The report requires the five source baseline quantities and the derived maximum, not an additional table of every operand.',
          'The maximum-absolute-force request uses tiePolicy=any: any physically tied governing member (or all co-governors) may be reported with that member\'s signed force, tension/compression and exact case. Existing frozen tolerances and declared operand order are unchanged; signed values are not replaced by magnitudes.'], derived=ds, all_members=True)

    # INT-034: two exact replacements, with no duplicate diagonal left behind.
    m = base({'A': 1, 'VERT': .8, 'DIAG': 1.2})
    parallel(m, 4, [2.4] * 5, vertical_secs={i: 'VERT' for i in range(5)})
    for i, (a, b) in enumerate([('B0', 'T1'), ('B1', 'T2'), ('T2', 'B3'), ('T3', 'B4')]):
        e(m, f'DG{i}', a, b, 'DIAG')
    for i in range(1, 4):
        p(m, f'top-{i}', f'T{i}', -12)
    m2 = deepcopy(m)
    replacements = {'DG1': ['T1', 'B2'], 'DG2': ['B2', 'T3']}
    for rod in m2['elements']:
        if rod['id'] in replacements:
            rod['nodes'] = replacements[rod['id']]
    instr = 'Build M-INT-034 from attachment A: a 16 m, four-panel, 2.4 m-high truss. ' + output_text('T2 at x=8 m on the top chord', True)
    ts = [turn(instr, 1, attachments=['attachment-A.txt']),
          turn('Use attachment B to replace the diagonal in panels x=4..8 m and x=8..12 m. Delete the old endpoints and use the replacement endpoints under the same IDs; retain exactly one diagonal per panel. All other connections, loads, supports and section groups remain unchanged. ' + output_text('T2 at x=8 m on the top chord', True), 2,
               attachments=['attachment-B.txt'], changedFields=['/elements/14/nodes', '/elements/15/nodes',
                   '/metadata/elementReferenceVectors/DG1/0', '/metadata/elementReferenceVectors/DG2/0'],
               preservedFields=['/nodes', '/materials', '/sections', '/load_cases', '/analysis_control'])]
    btext = ('Attachment B. Applies in turn 2 only.\n'
             'Units m, kN, MPa; global X horizontal, Z upward.\n'
             'Replace DG1 old B1 -> T2 with T1 -> B2.\n'
             'Replace DG2 old T2 -> B3 with B2 -> T3.\n'
             'Both replacement rods use material M1 and section DIAG (A=0.012 m2); '
             'retain vertical section VERT (A=0.008 m2), chord section A (A=0.01 m2) '
             'and every other explicit property in attachment A. No additional rod remains on either old diagonal.\n')
    emit(34, [m, m2], ts, {'attachment-A.txt': tables(m, 'en', 'Chord A=0.01 m2; VERT=0.8A; DIAG=1.2A. Only T1,T2,T3 have the 12 kN downward loads; end top nodes have no load.'), 'attachment-B.txt': btext}, 'T2',
         ['Missing A/B topology appendices are explicitly frozen here. Initial diagonals B0-T1,B1-T2,T2-B3,T3-B4 are opposite the source Pratt orientation; B replaces only the middle two. Both 10-node/17-rod states are checked for positive reduced axial stiffness and equilibrium before author completion.',
          'The shorthand top-node loading is resolved by the original M-STD-034 anchor specifying three internal top nodes and unloaded end tops; this completion does not borrow reference values.'])

    # INT-035: K midpoints are real joints; the first input omits one join identity.
    m = base()
    for i in range(7):
        n(m, f'B{i}', 3 * i, 0, TRUSS_PIN if i == 0 else TRUSS_ROLLER if i == 6 else None)
        n(m, f'T{i}', 3 * i, 3)
    for i in range(1, 7):
        n(m, f'M{i}', 3 * i, 1.5)
    for i in range(6):
        e(m, f'BC{i}', f'B{i}', f'B{i+1}')
        e(m, f'TC{i}', f'T{i}', f'T{i+1}')
    e(m, 'V0', 'B0', 'T0')
    for i in range(1, 7):
        e(m, f'V{i}a', f'B{i}', f'M{i}'); e(m, f'V{i}b', f'M{i}', f'T{i}')
        e(m, f'K{i}a', f'B{i-1}', f'M{i}'); e(m, f'K{i}b', f'T{i-1}', f'M{i}')
    for i in range(4):
        p(m, f'left-top-{i}', f'T{i}', -8)
    p(m, 'midpoint-direct', 'M2', -9)
    public = deepcopy(m)
    public['nodes'] = [x for x in public['nodes'] if x['id'] != 'M2']
    public['elements'] = [x for x in public['elements'] if x['id'] not in ['V2a', 'V2b', 'K2a', 'K2b']]
    public['load_cases'][0]['loads'][-1]['node'] = 'P: geometric point (6,0,1.5); structural joint identity unresolved'
    unresolved_geometry = ('x=6m处的竖杆几何线段为B2至T2，K腹杆几何线段为B1至P、T1至P，'
                           'P=(6,0,1.5)m。P与竖杆是否共用结构节点尚未给定，故这些局部杆未在下面节点连接表中定案；'
                           '竖杆若在P连接则分成上下两段，若不连接则保持整根。各相关杆均截面A、材料M1。'
                           '9kN向下荷载位于P，其结构节点归属也待同一连接问题确认。其他K节点连接已明确。')
    instr = '按附件建立18m、6节间、高3m的M-INT-035；x=6m处K腹杆与竖杆的相交点P是否相连未说明。' + output_text('x=6m竖杆中点P', False)
    ts = [turn(instr, None, 'clarify', ['input-tables.txt'], unresolved=['/topology/x6-midpoint-junction'],
               questions=['P=(6,0,1.5)m是否与x=6m竖杆共用结构节点，并使到P的两根K腹杆与竖杆上下段在此连接？']),
          turn('明确P为共用节点M2=(6,0,1.5)m。局部连接为V2a:B2→M2、V2b:M2→T2、K2a:B1→M2、K2b:T1→M2，均为M1/A；四根杆真正共节点，9kN向下力直接施加M2。保持x=0/3/6/9m上弦T0/T1/T2/T3各8kN向下，其他上弦无此载。' + output_text('x=6m竖杆中点M2', False), 1)]
    emit(35, [m], ts, {'input-tables.txt': tables(public, 'zh', unresolved_geometry)}, 'M2',
         ['The missing K-topology appendix is frozen as 14 chord nodes plus six vertical midpoints M1..M6, 12 chord rods, unsplit V0, 12 split vertical rods and 12 K rods: 20 nodes/37 rods. In each panel the left top/bottom nodes connect to the right vertical midpoint. No unsupported collinear midpoint is introduced at x=0.',
          'The initial attachment omits M2 and all four incident resolved endpoint rows. It supplies only geometric P, an unresolved vertical intersection and pending 9kN load joint identity. The T2 instruction alone resolves shared connectivity.'])

    # INT-036: complete, legal crossing semantics; no clarification needed.
    m = base({'A': 1, 'DOWN': 1.5}); parallel(m, 3, [2.5] * 5)
    for i in range(4):
        e(m, f'UP{i}', f'B{i}', f'T{i+1}')
        e(m, f'DOWN{i}', f'T{i}', f'B{i+1}', 'DOWN')
    for i in range(1, 4):
        p(m, f'top-{i}', f'T{i}', -10)
    instr = ('Build M-INT-036 from the complete tables. The two X diagonals in every panel cross '
             'without a shared structural node: do not split them or create nodes at crossings. '
             'The endpoint table is authoritative. Rising diagonals have A; falling diagonals have 1.5A; '
             'all chords and verticals have A. ' + output_text('T2 at x=6 m on the top chord', True))
    ts = [turn(instr, 1, attachments=['input-tables.txt'])]
    emit(36, [m], ts, {'input-tables.txt': tables(m, 'en', 'Every diagonal is a two-end axial-only element. Crossings are not connections. Only internal top nodes T1,T2,T3 carry 10 kN downward each; T0 and T4 have no load.')}, 'T2',
         ['The initial input is complete and explicitly resolves every X crossing; there is one analyze turn and no invented clarification.',
          'The shorthand top-node loading is completed from the original M-STD-036 anchor: three internal top nodes, no end-top loads. The 10 nodes/21 rods preserve the four unsplit X panels.'])


def cholesky(a):
    n = len(a); out = [[0.] * n for _ in a]
    max_diag = max(a[i][i] for i in range(n))
    for i in range(n):
        for j in range(i + 1):
            v = a[i][j] - sum(out[i][k] * out[j][k] for k in range(j))
            if i == j:
                assert v > max_diag * 1e-12, ('mechanism or nonpositive pivot', i, v)
                out[i][j] = math.sqrt(v)
            else:
                out[i][j] = v / out[j][j]
    return out


def solve(l, f):
    n = len(l); y = [0.] * n; x = [0.] * n
    for i in range(n):
        y[i] = (f[i] - sum(l[i][j] * y[j] for j in range(i))) / l[i][i]
    for i in range(n - 1, -1, -1):
        x[i] = (y[i] - sum(l[j][i] * x[j] for j in range(i + 1, n))) / l[i][i]
    return x


def mechanical_check(m):
    """Independent axial stiffness check; not a truth generator or native receipt."""
    ns = m['nodes']; index = {n['id']: i for i, n in enumerate(ns)}
    assert len(index) == len(ns)
    sections = {s['id']: s for s in m['sections']}
    mats = {s['id']: s for s in m['materials']}
    k = [[0.] * (2 * len(ns)) for _ in range(2 * len(ns))]
    ends = set()
    for el in m['elements']:
        assert el['type'] == 'truss'
        assert frozenset(el['nodes']) not in ends, ('duplicate bar', el['id'])
        ends.add(frozenset(el['nodes']))
        i, j = (index[x] for x in el['nodes']); a, b = ns[i], ns[j]
        dx, dz = b['x'] - a['x'], b['z'] - a['z']; length = math.hypot(dx, dz)
        assert length > 1e-9, el['id']
        q = [-dx / length, -dz / length, dx / length, dz / length]
        dofs = [2 * i, 2 * i + 1, 2 * j, 2 * j + 1]
        ea_l = mats[el['material']]['E'] * 1000 * sections[el['section']]['properties']['A'] / length
        for ii, di in enumerate(dofs):
            for jj, dj in enumerate(dofs):
                k[di][dj] += ea_l * q[ii] * q[jj]
    free = []
    for i, nd in enumerate(ns):
        assert all(nd['restraints'][j] for j in [1, 3, 4, 5]), ('inactive DOF', nd['id'])
        for local, full in [(0, 0), (1, 2)]:
            if not nd['restraints'][full]:
                free.append(2 * i + local)
    reduced = [[k[i][j] for j in free] for i in free]; l = cholesky(reduced)
    for lc in m['load_cases']:
        f = [0.] * len(k)
        for ld in lc['loads']:
            i = index[ld['node']]; f[2 * i] += ld.get('fx', 0); f[2 * i + 1] += ld.get('fz', 0)
        uf = solve(l, [f[i] for i in free]); u = [0.] * len(k)
        for i, x in zip(free, uf):
            u[i] = x
        r = [sum(row[j] * u[j] for j in range(len(k))) - f[i] for i, row in enumerate(k)]
        assert max(abs(r[i]) for i in free) < 1e-8
        fx = sum(r[2*i] + f[2*i] for i in range(len(ns)))
        fz = sum(r[2*i+1] + f[2*i+1] for i in range(len(ns)))
        moment = sum(nd['x'] * (r[2*i+1]+f[2*i+1]) - nd['z'] * (r[2*i]+f[2*i]) for i, nd in enumerate(ns))
        assert max(abs(fx), abs(fz), abs(moment)) < 1e-7
    return dict(nodes=len(ns), rods=len(m['elements']), activeFreeDOFs=len(free),
                positiveDefinite=True, equilibriumChecked=True)


def diff(a, b, path=''):
    if type(a) != type(b):
        return [path]
    if isinstance(a, dict):
        out = []
        for key in a.keys() | b.keys():
            out += diff(a.get(key), b.get(key), path + '/' + key)
        return out
    if isinstance(a, list):
        if len(a) != len(b):
            return [path]
        return [p for i, (x, y) in enumerate(zip(a, b)) for p in diff(x, y, path + '/' + str(i))]
    return [] if a == b else [path]


def check():
    expected_counts = {27: (12, 21), 28: (14, 25), 29: (6, 10), 30: (14, 25),
                       31: (14, 25), 32: (11, 19), 33: (12, 21), 34: (10, 17),
                       35: (20, 37), 36: (10, 21)}
    for case_id in CASE_IDS:
        directory = ROOT / 'corpora/research-300/cases' / case_id
        contract = json.loads((directory / 'contract.json').read_text())
        cov, task, _ = sources(case_id)
        assert contract['sourcePlan'] == cov['sourceRequirements']
        assert contract['sourceMetadata']['requirements'] == cov['requirements']
        assert sorted(x for row in contract['requirementCoverage'] for x in row['requirementIds']) == sorted(x['id'] for x in cov['requirements'])
        assert len(contract['turns']) == task['turns']
        assert contract['status'] == 'authored-candidate' and contract['sameEngineTruthStatus'] == 'pending'
        states = [json.loads((directory / p).read_text()) for p in contract['modelStates']]
        reports = []
        for m in states:
            assert (len(m['nodes']), len(m['elements'])) == expected_counts[int(case_id[-3:])]
            assert m['schema_version'] == '2.2.0' and m['analysis_control']['self_weight'] is False
            reports.append(mechanical_check(m))
        rr = json.loads((directory / 'reference-requests.json').read_text())
        assert len(rr['states']) == len(states)
        for rs in rr['states']:
            assert all('value' not in q for q in rs['quantities'])
            assert len({q['id'] for q in rs['quantities']}) == len(rs['quantities'])
            for d in rs['derived']:
                assert set(d['operands']) <= {q['id'] for q in rs['quantities']}
        for t in contract['turns']:
            assert set(t['attachments']) <= set(contract['attachments'])
        if contract['locale'] == 'en':
            for filename in ['prompt.txt'] + contract['attachments']:
                assert not any('\u3400' <= c <= '\u9fff' for c in (directory / filename).read_text()), filename
        if len(states) == 2:
            changes = diff(states[0], states[1])
            # Explicit axes are derived from geometry, so topology replacement changes their vectors too.
            unexpected = [p for p in changes if not any(p == allowed or p.startswith(allowed + '/') for allowed in contract['turns'][1]['changedFields']) and not p.startswith('/metadata/elementReferenceVectors/')]
            assert not unexpected, unexpected
        if case_id == 'INT-028':
            pub = (directory / 'input-tables.txt').read_text()
            assert pub.count('"fz": "-15, unit unresolved: tonne-force or kN"') == 5
        if case_id == 'INT-029':
            pub = (directory / 'input-tables.txt').read_text()
            assert '1.5' not in pub and 'H=3' not in pub and '"z": 3' not in pub
        if case_id == 'INT-032':
            pub = (directory / 'input-tables.txt').read_text(); data = json.loads(pub[pub.index('{'):])
            assert next(x for x in data['elements'] if x['id'] == 'DG1')['nodes'] == ['B2', None]
            assert not data['metadata']
        if case_id == 'INT-035':
            pub = (directory / 'input-tables.txt').read_text()
            assert '"M2"' not in pub
            assert all('"' + x + '"' not in pub for x in ['V2a', 'V2b', 'K2a', 'K2b'])
        print(case_id, json.dumps(reports, separators=(',', ':')))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='Check existing authored files without rewriting')
    args = parser.parse_args()
    if not args.check:
        author()
    check()
