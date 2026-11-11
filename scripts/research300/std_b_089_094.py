"""Explicit source-authoring appendix for STD-089..094; no solver or truth values."""
import math

from std_b_common import Requests, beams_udl, elem, emit, length, load, node, section, source, spatial


def steel_frame(xs, ys, levels):
    m = spatial(xs, ys, levels)
    m['sections'] = [section('BX', .3, .6), section('BY', .25, .5), section('C1', .4, .5)]
    for e in m['elements']:
        e['section'] = 'C1' if e['type'] == 'column' else ('BX' if e['id'].startswith('x') else 'BY')
    return m


def roof_nodes(m):
    zmax = max(n['z'] for n in m['nodes'])
    return [n['id'] for n in m['nodes'] if n['z'] == zmax]


def native_mapping(m, *, live=False):
    return {
        '引擎': 'PKPM', '原生执行状态': 'pending',
        '坐标映射要求': '协议全局(X,Y,Z)与原生工程全局(X,Y,Z)同向，Z向上；若原生内部轴不同，交付显式变换表。',
        '单位映射要求': '协议坐标m、力kN、弯矩kN*m、线载kN/m、E/G MPa、截面尺寸mm、惯性矩m^4；原生内部单位逐字段转换并记录。',
        '工况映射要求': [
            {'协议类型': 'case', '协议ID': c['id'], '原生目标类型': 'DL' if c['id'] == 'D' else 'LL',
             '加载方式': '逐构件线载及明确节点向量；不得用整层面载覆盖、自动传载或重复添加。',
             '原生实际工况标识': '待运行记录'} for c in m['load_cases']
        ],
        '组合映射要求': [dict(协议类型='combination', 协议ID=c['id'], 系数=c['factors'], 原生实际组合标识='待运行记录') for c in m['load_combinations']],
        '逐构件属性和节点荷载': '保留input-data.json的全部节点、连接、材料、截面组、局部轴、支座与荷载；记录到原生ID的完整双向映射。',
        '设置要求': '一阶线弹性Euler-Bernoulli杆系；关闭自重、刚性楼板、刚域、P-Delta、施工阶段及默认规范组合。',
        '结果要求': '各协议节点/构件、端点、局部轴分量、工况/组合、符号和单位逐项关联原生结果；不得省略柱脚六分量反力。',
        '待验收缺口': '实际原生接口、逐梁/节点加载、原生求解与结果索引均待验收；本附表是执行契约，不是原生计算证据。',
    }


def case_089():
    m = steel_frame([0, 6, 12], [0, 5, 10], [3.6, 7.2])
    m['sections'] = [section('BX', .3, .6), section('BY', .25, .5),
                     section('C_CORNER', .4, .4), section('C_EDGE', .45, .5), section('C_INTERIOR', .55, .55)]
    ns = {n['id']: n for n in m['nodes']}
    for e in m['elements']:
        if e['type'] == 'column':
            a = ns[e['nodes'][0]]
            edges = int(a['x'] in (0, 12)) + int(a['y'] in (0, 10))
            e['section'] = {2: 'C_CORNER', 1: 'C_EDGE', 0: 'C_INTERIOR'}[edges]
    beams_udl(m, 8)
    load(m, type='nodal', node='n2-2-2', fx=20, fy=15)
    r = Requests(m)
    for nid in roof_nodes(m):
        r.node(nid, ('ux', 'uy', 'uz'))
    # One explicit member per group per story, including both local member ends.
    representatives = [f'{eid}-{level}' for level in (1, 2)
                       for eid in ['c0-0', 'c1-0', 'c1-1', 'x0-0', 'y0-0']]
    for eid in representatives:
        r.ends(eid)
    r.supports()
    emit(89, m,
         '使用PKPM原生建立两层空间框架：X=0、6、12m，Y=0、5、10m，两层均高3.6m；'
         '九个柱脚六自由度固定。完整附表明确一个钢材料Q355，E=206000MPa、ν=0.3、'
         'G=206000/2.6MPa、ρ=7850kg/m³。各层角柱C_CORNER为400×400mm，边柱C_EDGE为450×500mm，'
         '中柱C_INTERIOR为550×550mm；X向梁BX为300×600mm，Y向梁BY为250×500mm。'
         '以上为实体矩形弹性分析截面，B沿局部y、H沿局部z，完整A/Iy/Iz/J及局部轴见附表。'
         '角柱位于平面四角，边柱位于四边中点，中柱位于(6,5)m；两层均按空间位置分组。'
         'D工况中全部24根梁按真实杆长向下8kN/m，屋顶右后角(12,10,7.2)m另施加全局'
         'X向20kN及Y向15kN节点力。进行一阶线弹性Euler-Bernoulli静力分析，自重和刚性楼板关闭。'
         '输出屋顶九节点ux/uy/uz、九柱脚Fx/Fy/Fz/Mx/My/Mz，以及每层指定角柱c0-0、边柱c1-0、'
         '中柱c1-1、X梁x0-0、Y梁y0-0的两端N/V2/V3/T/M2/M3（完整ID加-1或-2）。'
         '执行engine-mapping.json的原生DL、轴系、单位、属性及节点力映射要求，保存项目、原生日志与带索引结果。', r,
         notes=[
             'The missing material/section appendix is frozen as one Q355 steel material, E=206000 MPa, nu=0.3, rho=7850 kg/m3; five distinct solid rectangular analysis sections are explicitly listed.',
             'Corner columns have both X and Y on a boundary; edge columns have exactly one boundary coordinate; the interior column has neither. Both stories keep the resulting 4/4/1 column-line grouping.',
             'One corner, edge and interior column and one X/Y beam are selected on each story, with all six local end components; all nine roof nodes and base reactions are covered.',
             'PKPM native DL mapping includes the explicit roof corner node force. Interface capability, same-engine independent truth and native execution remain pending; cross-engine results cannot substitute.',
         ], extra_attachments={'engine-mapping.json': native_mapping(m)})


def case_091():
    m = steel_frame([0, 6, 12], [0, 5, 10], [3.6, 7.2])
    beams_udl(m, 8)
    live_edges = ['x0-0-2', 'x0-1-2', 'y0-0-2', 'y1-0-2']
    for eid in live_edges:
        load(m, 'L', type='distributed', element=eid, wz=-6)
    m['load_combinations'] = [dict(id='D', factors={'D': 1}), dict(id='D+L', factors={'D': 1, 'L': 1})]
    r = Requests(m)
    roof_points = ['n0-0-2', 'n1-0-2', 'n0-1-2', 'n1-1-2', 'n2-1-2', 'n1-2-2', 'n2-2-2']
    for selection in ('D', 'D+L'):
        for nid in roof_points:
            r.node(nid, ('ux', 'uy', 'uz'), selection)
        for eid in live_edges:
            r.ends(eid, selection=selection)
        r.supports(selection)
    emit(91, m,
         '使用PKPM原生建立两层2×2跨空间钢框架：X=0/6/12m、Y=0/5/10m，层高均3.6m，'
         '九柱脚六自由度固定；前侧为Y=0，左侧为X=0。完整附表规定Q355钢，E=206000MPa、'
         'ν=0.3、G=206000/2.6MPa、ρ=7850kg/m³，柱C1=400×500mm、X梁BX=300×600mm、'
         'Y梁BY=250×500mm，均为实体矩形弹性分析截面，局部轴与全截面属性明列。'
         'D工况给全部24根梁施加向下8kN/m线载；L工况仅给屋顶左前格'
         '[0,6]×[0,5]m的四条边梁x0-0-2、x0-1-2、y0-0-2、y1-0-2各施加向下6kN/m，'
         '共享边也仅加载一次，不给其他梁、下层或面区域施加L。计算两个显式组合：'
         '组合D=1×工况D，组合D+L=1×工况D+1×工况L；同名工况D与组合D的类型必须区分。'
         '一阶线弹性Euler-Bernoulli静力分析，自重、刚性楼板与自动双向传载关闭。'
         '逐组合输出加载格四角和对角格[6,12]×[5,10]m四角的三向位移（共七个唯一屋顶节点），'
         '四条L加载梁两端六分量内力，以及全部九柱脚六分量反力；附完整工况/组合和原生结果索引表。', r,
         notes=[
             'The source specifies one steel material but leaves its properties and member sizes open. Freeze Q355 E=206000 MPa, nu=0.3, rho=7850 kg/m3; C1 400x500, BX 300x600, BY 250x500 mm.',
             'Left-front is explicitly X in [0,6], Y in [0,5]. The four listed roof perimeter beams alone receive L; total L=6*(6+6+5+5)=132 kN.',
             'The loaded cell and diagonally opposite cell share n1-1-2, giving seven unique requested roof nodes. Both explicit combinations enumerate all requested outputs.',
             'Combination D and load case D intentionally share a label but have distinct selection kinds; all requested results select combination D or D+L. Native PKPM DL/LL and result IDs remain pending.',
         ], interactions=['工况/组合索引表：明确区分case D、case L、combination D和combination D+L，并关联各原生工况/组合结果标识。'],
         extra_attachments={'engine-mapping.json': native_mapping(m, live=True)})


def case_090():
    m = steel_frame([0, 6], [0, 5, 10], [3.6, 7.2])
    ns = {n['id']: n for n in m['nodes']}
    for e in m['elements']:
        e['rotation_angle'] = 90 if e['type'] == 'column' and ns[e['nodes'][0]]['y'] == 0 else 0
    load(m, type='nodal', node='n1-2-2', fx=20, fy=15)
    r = Requests(m)
    r.node('n1-2-2', ('ux', 'uy'))
    for e in m['elements']:
        if e['type'] == 'column':
            r.ends(e['id'])
    r.supports()
    axes = (
        'LOCAL AXIS APPENDIX\n'
        'All vectors are in global XYZ. B is along local y; H is along local z. '
        'Section rolls are in degrees, result rotations in radians.\n'
        'Local x follows the ordered endpoints. Before roll, y=unit(reference cross x), '
        'z=x cross y. Positive roll theta gives y_new=cos(theta)*y+sin(theta)*z and '
        'z_new=-sin(theta)*y+cos(theta)*z.\n'
        'All vertical columns use reference=(1,0,0). The unrolled basis is '
        'x=(0,0,1), y=(0,-1,0), z=(1,0,0).\n'
        'Only c0-0-1, c1-0-1, c0-0-2 and c1-0-2 have roll=90, hence '
        'x=(0,0,1), y=(1,0,0), z=(0,1,0). All other columns have roll=0.\n'
        'C1 is the same 400x500 mm rectangle on every column; Iy=0.004166666666666667 m^4 '
        'and Iz=0.002666666666666667 m^4. Do not swap these section values in addition to rolling.\n'
        'X beams: reference=(0,0,1), roll=0, x=(1,0,0), y=(0,1,0), z=(0,0,1).\n'
        'Y beams: reference=(0,0,1), roll=0, x=(0,1,0), y=(-1,0,0), z=(0,0,1).\n'
        'There is no gravity line load, area load or self-weight load in this task.\n'
    )
    emit(90, m,
         'Build a two-story spatial steel frame with X span 6 m, two Y spans of 5 m '
         'and story heights 3.6 m. Fix all six bases in all six degrees of freedom. '
         'The complete appendix supplies Q355 steel (E=206000 MPa, nu=0.3, '
         'G=206000/2.6 MPa, density=7850 kg/m^3), solid rectangular columns '
         'C1=400x500 mm, X beams BX=300x600 mm and Y beams BY=250x500 mm. '
         'Rotate the local section axes by exactly 90 degrees only for the two column '
         'lines at Y=0, on both stories: c0-0-1, c1-0-1, c0-0-2 and c1-0-2. '
         'Every other column and every beam remains at roll 0. The single load case D '
         'contains only a roof-corner force at (6,10,7.2) m with Fx=20 kN and Fy=15 kN. '
         'Use OpenSees for first-order linear elastic Euler-Bernoulli static analysis, '
         'self weight off. Report ux/uy at that loaded corner, all six local end-force '
         'components at both ends of every rotated and unrotated column, all six '
         'reaction components at every base, and a member-by-member local-axis record.', r,
         notes=[
             'The source leaves material, rectangle dimensions and initial axis convention to the appendix. Freeze Q355 E=206000 MPa, nu=0.3, rho=7850 kg/m3; columns 400x500, X beams 300x600, Y beams 250x500 mm.',
             'Exactly the four column segments on the two Y=0 lines are rolled 90 degrees; the other eight columns and fourteen beams remain unrolled. The source specifies only the roof corner lateral force, so no gravity load is added.',
             'All twelve columns are selected for end-force outputs to cover both rotated and unrotated groups without an ambiguous representative subset.',
         ], interactions=['Report each member ID, ordered endpoints, reference vector, roll angle in degrees and final local x/y/z unit vectors in global XYZ.'],
         extra_attachments={'local-axes.txt': axes})


def split_midpoint(m, eid):
    e = next(e for e in m['elements'] if e['id'] == eid)
    ns = {n['id']: n for n in m['nodes']}
    a, b = [ns[nid] for nid in e['nodes']]
    nid = 'mid-' + eid
    node(m, nid, (a['x'] + b['x']) / 2, (a['z'] + b['z']) / 2, (a['y'] + b['y']) / 2)
    parts = [dict(e, id=eid + '-a', nodes=[e['nodes'][0], nid]),
             dict(e, id=eid + '-b', nodes=[nid, e['nodes'][1]])]
    idx = m['elements'].index(e)
    m['elements'][idx:idx + 1] = parts
    ref = m['metadata']['elementReferenceVectors'].pop(eid)
    for part in parts:
        m['metadata']['elementReferenceVectors'][part['id']] = ref[:]
    m['metadata'].setdefault('physicalBeams', {})[eid] = dict(nodes=e['nodes'], segments=[p['id'] for p in parts], midpointNode=nid, addedMass=0, joint='continuous-rigid')
    return nid


def case_092():
    m = steel_frame([0, 6, 12], [0, 5], [6])
    for n in m['nodes']:
        if n['z'] > 0 and n['y'] == 5:
            n['z'] = 8
    # Roof elevation varies continuously; a uniform story record would be false.
    m.pop('stories', None)
    slopes = [f'y{i}-0-1' for i in range(3)]
    mids = [split_midpoint(m, eid) for eid in slopes]
    beams_udl(m, 5)
    r = Requests(m)
    for n in m['nodes']:
        if n['z'] > 0:
            r.node(n['id'], ('ux', 'uy', 'uz'))
    for eid in slopes:
        r.member(eid + '-a', 0)
        r.member(eid + '-b', length(m, eid + '-b'), side='left')
    r.supports()
    emit(92, m,
         'Build a single-story spatial steel frame with X bays 6+6 m and one Y bay 5 m. '
         'The roof edge at Y=0 is at Z=6 m; the edge at Y=5 is at Z=8 m. Fix all six '
         'column bases in all six degrees of freedom. Roof beams follow the actual '
         'single-slope surface: four horizontal X beams of length 6 m and three sloping '
         'Y beams of length sqrt(29) m. Use Q355 steel (E=206000 MPa, nu=0.3, '
         'G=206000/2.6 MPa, density=7850 kg/m^3), solid rectangular columns '
         'C1=400x500 mm, X beams BX=300x600 mm and sloping Y beams BY=250x500 mm. '
         'D applies global downward 5 kN/m per actual member length to every roof beam. '
         'Each sloping beam has a connected, unreleased midpoint node at Y=2.5, Z=7 m; '
         'its two halves have the same section and load intensity, without added mass. '
         'Use OpenSees for first-order linear elastic Euler-Bernoulli analysis, self '
         'weight off. Report ux/uy/uz at the four roof corners, both edge nodes on '
         'X=6 and all three slope midline nodes at Y=2.5 (nine nodes in total), all '
         'six local end-force components at both physical ends of each of the three '
         'sloping beams, and all six reaction components at every base.', r,
         notes=[
             'Material and section appendix frozen as Q355 E=206000 MPa, nu=0.3, rho=7850 kg/m3; C1 400x500, BX 300x600, BY 250x500 mm.',
             'Slope midline wording is made explicit by including both X=6 edge nodes and three connected Y=2.5 roof midpoint nodes, in addition to all four corners. These observation nodes do not create additional beams across the roof.',
             'The true sloping-beam length is sqrt(5^2+2^2)=sqrt(29) m. Gravity load is global -Z at 5 kN/m of actual length, including its local axial and transverse projections; no horizontal-projection rescaling is applied.',
             'Total downward input load is 5*(24+3*sqrt(29)) kN. This is an input-load audit, not a solved response or native acceptance result.',
         ])


def case_093():
    m = steel_frame([0, 6], [0, 5], [3.6, 7.2])
    m['sections'].append(section('A_BRACE', .1, .1))
    for level in (1, 2):
        elem(m, f'brace-{level}', f'n0-0-{level-1}', f'n1-0-{level}', 'truss', 'A_BRACE')
    beams_udl(m, 8)
    load(m, type='nodal', node='n1-1-2', fx=20, fy=20)
    r = Requests(m)
    for nid in roof_nodes(m):
        r.node(nid, ('ux', 'uy'))
    for e in m['elements']:
        r.ends(e['id'], ('N',) if e['type'] == 'truss' else ('N', 'V2', 'V3', 'T', 'M2', 'M3'))
    r.supports()
    emit(93, m,
         '两层空间钢框架，X跨6m、Y跨5m、两层均高3.6m；四柱脚六自由度固定。'
         '仅Y=0立面每层一根轴力斜撑：brace-1从(0,0,0)到(6,0,3.6)m，'
         'brace-2从(0,0,3.6)到(6,0,7.2)m。斜撑用空间桁架单元，仅传轴力、端铰接；'
         '其他立面不设支撑，所有梁柱共节点刚接。完整附表规定Q355钢，E=206000MPa、ν=0.3、'
         'G=206000/2.6MPa、ρ=7850kg/m³；实体矩形柱C1=400×500mm、X梁BX=300×600mm、'
         'Y梁BY=250×500mm、斜撑A_BRACE=100×100mm（轴向面积0.01m²，弯曲及扭转刚度不参与）。'
         'D工况中全部八根梁向下8kN/m，屋顶右后角(6,5,7.2)m有全局X/Y各+20kN节点力。'
         '用OpenSees一阶线弹性Euler-Bernoulli梁柱与轴力杆混合分析，自重关闭。'
         '输出屋顶四角ux/uy、两斜撑各自两端的有符号轴力N、全部梁柱两端六分量内力，'
         '以及全部四柱脚六分量反力；斜撑不得输出虚构弯矩。', r,
         notes=[
             'Missing properties are completed as Q355 E=206000 MPa, nu=0.3, rho=7850 kg/m3; C1 400x500, BX 300x600, BY 250x500 mm and a 100x100 mm axial-only brace area 0.01 m2.',
             'The two exact source endpoints are retained; no X brace, additional face brace or moment-transmitting brace is introduced. Truss type expresses hinged axial-only behavior while the frame joint remains rigid.',
             'All beams and columns have both ends requested with all six components; each brace is requested for signed N only at both ends.',
         ])


def map_source(v):
    return [v[0], -v[2], v[1]]


def unmap_global(v):
    return [v[0], v[2], -v[1]]


def cross(a, b):
    return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]


def unit(v):
    magnitude = math.sqrt(sum(x*x for x in v))
    return [x / magnitude for x in v]


def case_094():
    m = steel_frame([0, 6, 10], [0, -5], [3, 7])
    load(m, type='nodal', node='n2-1-2', fx=20, fy=-10, fz=-30)
    ns = {n['id']: n for n in m['nodes']}
    transform = dict(
        sourceUpAxis='Y', globalUpAxis='Z', sourceToGlobal=[[1, 0, 0], [0, 0, -1], [0, 1, 0]],
        equation='(global X, global Y, global Z)=(source X, -source Z, source Y)',
        vectorUnits=dict(coordinates='m', forces='kN', displacements='m', rotations='rad'),
        sourceDofOrder=['ux_source', 'uy_source', 'uz_source', 'rx_source', 'ry_source', 'rz_source'],
        globalDofOrder=['ux', 'uy', 'uz', 'rx', 'ry', 'rz'],
        nodes=[], members=[],
        sourceLoads=[dict(case='D', node='n2-1-2', sourceCoordinates=[10, 7, 5], forceSource=[20, -30, 10], momentSource=[0, 0, 0])],
        globalLoads=[dict(case='D', node='n2-1-2', globalCoordinates=[10, -5, 7], forceGlobal=[20, -10, -30], momentGlobal=[0, 0, 0])],
        displacementInverse='ux_source=ux; uy_source=uz; uz_source=-uy',
        analysis='First-order linear elastic Euler-Bernoulli; no self weight, diaphragm, rigid offsets or P-Delta.',
    )
    for n in m['nodes']:
        xyz = [n[k] for k in 'xyz']
        transform['nodes'].append(dict(id=n['id'], sourceCoordinates=unmap_global(xyz), globalCoordinates=xyz,
                                       sourceRestraints=n['restraints'], globalRestraints=n['restraints']))
    for e in m['elements']:
        a, b = [ns[nid] for nid in e['nodes']]
        xsource = unit([unmap_global([b[k] for k in 'xyz'])[i]-unmap_global([a[k] for k in 'xyz'])[i] for i in range(3)])
        refsource = [1, 0, 0] if e['type'] == 'column' else [0, 1, 0]
        ysource = unit(cross(refsource, xsource)); zsource = cross(xsource, ysource)
        m['metadata']['elementReferenceVectors'][e['id']] = map_source(refsource)
        transform['members'].append(dict(id=e['id'], orderedNodes=e['nodes'], material=e['material'], section=e['section'],
                                         referenceSource=refsource, referenceGlobal=map_source(refsource), rollDegrees=0,
                                         axesSource=dict(x=xsource, y=ysource, z=zsource),
                                         axesGlobal=dict(x=map_source(xsource), y=map_source(ysource), z=map_source(zsource))))
    r = Requests(m)
    top = r.node('n2-1-2', ('ux', 'uy', 'uz'))
    zero = r.node('n0-0-0', ('ux', 'uy', 'uz'))
    r.derive('case-D-source-displacement-X', 'difference', [top[0], zero[0]], 'Source X displacement at source (10,7,5) m = global ux; subtract fixed base ux=0.')
    r.derive('case-D-source-displacement-Y', 'difference', [top[2], zero[2]], 'Source Y displacement at source (10,7,5) m = global uz; subtract fixed base uz=0.')
    r.derive('case-D-source-displacement-Z', 'difference', [zero[1], top[1]], 'Source Z displacement at source (10,7,5) m = -global uy; fixed base uy=0 minus top uy.')
    for eid in ['c0-0-1', 'c2-1-1', 'c2-1-2', 'x0-0-2', 'x1-1-2', 'y2-0-2']:
        r.ends(eid)
    r.supports()
    emit(94, m,
         'Build the spatial steel frame from the source coordinates, where source Y is up. '
         'Source X grid lines are 0, 6 and 10 m; source Z grid lines are 0 and 5 m; '
         'source Y levels are 0, 3 and 7 m (story heights 3 and 4 m). Use the exact '
         'right-handed orthogonal mapping (global X,Y,Z)=(source X,-source Z,source Y). '
         'Fix all six base nodes in all six degrees of freedom, transformed consistently '
         'with the coordinates. The only load is a nodal force at source (10,7,5) m '
         'with source components (20,-30,10) kN. It maps to global (10,-5,7) m and '
         'global force (20,-10,-30) kN in case D. Use the complete source/global node, '
         'restraint, member-axis and load tables in coordinate-transform.json. The '
         'appendix supplies Q355 steel (E=206000 MPa, nu=0.3, G=206000/2.6 MPa, '
         'density=7850 kg/m^3), solid rectangular columns C1=400x500 mm, source-X '
         'beams BX=300x600 mm and source-Z beams BY=250x500 mm. Section axes transform '
         'with the geometry; B and H remain attached to local y and z. Run OpenSees '
         'first-order linear elastic Euler-Bernoulli static analysis with self weight '
         'off. Report the loaded top corner displacement in both source and global '
         'three-component systems, all six global reaction components at every base, '
         'and all six local end-force components at both ends of c0-0-1, c2-1-1, '
         'c2-1-2, x0-0-2, x1-1-2 and y2-0-2. Supply transformed coordinate, load, '
         'restraint and local-axis tables with the result.', r,
         notes=[
             'The prescribed proper orthogonal mapping is applied to all coordinates, polar force/displacement vectors, restraints and section reference/local-axis vectors. Six fully fixed base supports remain fully fixed under that map.',
             'The source leaves steel/section values unspecified. Freeze Q355 E=206000 MPa, nu=0.3, rho=7850 kg/m3; C1 400x500, source-X BX 300x600 and source-Z BY 250x500 mm.',
             'Source displacement components are explicit derived records: global ux, global uz and negative global uy. Difference against an actually restrained zero displacement implements the signed mapping without adding a fabricated reference value.',
             'The representative members cover bottom and top columns, both 6 m and 4 m X spans, and the source-Z/global-negative-Y beam. No gravity line load is added to the stated single nodal load.',
         ], interactions=['Supply the transformed coordinate and nodal-load tables, including original source IDs and values, together with transformed restraints and section local axes.'],
         extra_attachments={'coordinate-transform.json': transform})


def main():
    # Commercial source rows are authored first; all native evidence stays pending.
    for number, builder in [(89, case_089), (91, case_091), (90, case_090),
                            (92, case_092), (93, case_093), (94, case_094)]:
        row, task, original_model = source(number)
        assert row['id'] == task['id'] == original_model['taskId']
        assert row['plannedEngine'] == ('PKPM' if number in (89, 91) else 'OpenSees')
        builder()


if __name__ == '__main__':
    main()
