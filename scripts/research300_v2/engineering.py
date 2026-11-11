"""Thirty bounded, source-audited engineering adaptations.

Source facts, added assumptions and load recipes are public.  None of these
models claims to reproduce a complete project, its design checks or its native
software results.  Units: m, kN, MPa.  Self weight is off; D is explicit.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

try:
    from .models import _model, _node, _member, _section
except ImportError:
    from models import _model, _node, _member, _section


SOURCE_IDS = (
    'SRC-COLD-2023', 'SRC-JIANGSU-2023', 'SRC-LUOYANG-2022',
    'SRC-PIPE-2020', 'SRC-SH-STEEL-2020', 'SRC-SPORT-2023',
    'SRC-CABLE-2010', 'SRC-SH-RC-2020', 'SRC-CQ-SCHOOL1-2020',
    'SRC-HILLSIDE-2020',
)

# Deliberately authored rectangular equivalent sections, NOT as-built members.
# Each tuple is beam B/H, column B/H and two-way axial bar B/H in metres.
_DIMENSIONS = (
    (.28, .65, .45, .75, .10, .12),
    (.22, .48, .32, .55, .07, .10),
    (.24, .56, .36, .60, .08, .11),
    (.12, .24, .18, .30, .06, .08),
    (.30, .70, .50, .85, .12, .14),
    (.20, .42, .35, .55, .08, .12),
    (.30, .60, .50, .60, .07, .09),
    (.32, .65, .50, .65, .09, .11),
    (.35, .75, .55, .65, .08, .10),
    (.32, .68, .50, .70, .09, .12),
)


def _new(source_id, dimension='2d', concrete=False):
    m = _model(dimension)
    dims = _DIMENSIONS[SOURCE_IDS.index(source_id)]
    m['sections'] = [_section(name, dims[2*i], dims[2*i+1])
                     for i, name in enumerate(('B', 'C', 'A'))]
    if concrete:
        m['materials'] = [{'id': 'S', 'name': 'Authored uncracked linear concrete',
            'type': 'concrete', 'E': 30000., 'G': 12500., 'nu': .2, 'rho': 2500.}]
    return m


def _frame(m, spans, heights, *, offsets=None, braces=False, gable=None):
    xs = [0.]
    for span in spans:
        xs.append(xs[-1] + span)
    zs = [0.]
    for height in heights:
        zs.append(zs[-1] + height)
    for j, z in enumerate(zs):
        for i, x in enumerate(xs):
            _node(m, f'N{i}-{j}', x, offsets[i] if j == 0 and offsets else z,
                  support='F' if j == 0 else None)
    loaded = []
    for j in range(1, len(zs)):
        for i in range(len(xs)):
            _member(m, f'C{i}-{j}', f'N{i}-{j-1}', f'N{i}-{j}', 'column', 'C')
        for i, span in enumerate(spans):
            if gable is not None and j == len(zs)-1:
                ridge = _node(m, f'RIDGE{i}', xs[i]+span/2, zs[j]+span*gable/2)
                for suffix, a, b in [('a', f'N{i}-{j}', ridge), ('b', ridge, f'N{i+1}-{j}')]:
                    eid = f'B{i}-{j}{suffix}'
                    _member(m, eid, a, b)
                    loaded.append(eid)
            else:
                eid = f'B{i}-{j}'
                _member(m, eid, f'N{i}-{j}', f'N{i+1}-{j}')
                loaded.append(eid)
            if braces:
                _member(m, f'D{i}-{j}', f'N{i}-{j-1}', f'N{i+1}-{j}', 'truss', 'A')
    return loaded


def _continuous(m, spans):
    x = 0.
    _node(m, 'N0', x, 0., support='P')
    loaded = []
    for i, span in enumerate(spans):
        # Physical midspan observation/load point, not topology padding.
        _node(m, f'M{i}', x+span/2, 0.)
        x += span
        _node(m, f'N{i+1}', x, 0., support='R')
        for suffix, a, b in [('a', f'N{i}', f'M{i}'), ('b', f'M{i}', f'N{i+1}')]:
            eid = f'B{i}{suffix}'
            _member(m, eid, a, b)
            loaded.append(eid)
    return loaded


def _truss(m, span, depth, panels, *, mixed=False, elevation=0., columns=False):
    for i in range(panels+1):
        support = None if columns else 'P' if i == 0 else 'R' if i == panels else None
        _node(m, f'L{i}', span*i/panels, elevation, support=support,
              axial=not mixed and not (columns and i in (0, panels)))
        _node(m, f'U{i}', span*i/panels, elevation+depth, axial=not mixed)
        _member(m, f'V{i}', f'L{i}', f'U{i}', 'truss', 'A')
    for i in range(panels):
        for level in ('L', 'U'):
            _member(m, f'{level}C{i}', f'{level}{i}', f'{level}{i+1}',
                    'beam' if mixed else 'truss', 'B' if mixed else 'A')
        # Symmetric Pratt web; one diagonal per panel, no tension-only behavior.
        a, b = (f'L{i}', f'U{i+1}') if i < panels/2 else (f'U{i}', f'L{i+1}')
        _member(m, f'D{i}', a, b, 'truss', 'A')
    if columns:
        for i in (0, panels):
            _node(m, f'BASE{i}', span*i/panels, 0., support='F')
            _member(m, f'COL{i}', f'BASE{i}', f'L{i}', 'column', 'C')
    return [f'U{i}' for i in range(panels+1)]


def _double_truss(m, span, depth, panels, width, *, middle=False):
    """Beam chords/crossbeams and bilateral axial webs, on four pin bearings."""
    levels = ('L', 'M', 'U') if middle else ('L', 'U')
    for side, y in enumerate((0., width)):
        for i in range(panels+1):
            for level in levels:
                fraction = {'L': 0., 'M': .5, 'U': 1.}[level]
                _node(m, f'{side}{level}{i}', span*i/panels, depth*fraction, y,
                      support='T' if level == 'L' and i in (0, panels) else None)
            for a, b in zip(levels, levels[1:]):
                # End posts retain bending stiffness, giving explicit transverse
                # end frames instead of an unbraced lateral rigid-body mode.
                end = i in (0, panels)
                _member(m, f'{side}V{i}{a}', f'{side}{a}{i}', f'{side}{b}{i}',
                        'column' if end else 'truss', 'C' if end else 'A')
        for i in range(panels):
            # Middle longitudinals are explicit added collector beams. They
            # remove rotational mechanisms at the middle crossbeam junctions.
            for level in levels:
                _member(m, f'{side}{level}C{i}', f'{side}{level}{i}', f'{side}{level}{i+1}')
            a, b = (f'{side}L{i}', f'{side}U{i+1}') if i < panels/2 else (f'{side}U{i}', f'{side}L{i+1}')
            _member(m, f'{side}D{i}', a, b, 'truss', 'A')
    cross = []
    for i in range(panels+1):
        for level in levels:
            eid = f'X{level}{i}'
            _member(m, eid, f'0{level}{i}', f'1{level}{i}')
            cross.append(eid)
    return cross


def _space_strip(m, longitudinal, transverse, height):
    xs = [0.]
    for span in longitudinal:
        xs.append(xs[-1]+span)
    loaded = []
    for k, y in enumerate((0., transverse)):
        for i, x in enumerate(xs):
            _node(m, f'BASE{i}-{k}', x, 0., y, support='F')
            _node(m, f'TOP{i}-{k}', x, height, y)
            _member(m, f'C{i}-{k}', f'BASE{i}-{k}', f'TOP{i}-{k}', 'column', 'C')
        for i in range(len(longitudinal)):
            eid = f'L{i}-{k}'
            _member(m, eid, f'TOP{i}-{k}', f'TOP{i+1}-{k}')
            loaded.append(eid)
    for i in range(len(xs)):
        _member(m, f'X{i}', f'TOP{i}-0', f'TOP{i}-1')
    return loaded


def _surface(members, pressure, width):
    return {'kind': 'surface-on-members', 'members': list(members),
            'pressureKNM2': pressure, 'tributaryWidthM': width,
            'globalUnitVector': [0., 0., -1.]}


def _nodal(node, **components):
    return {'kind': 'nodal', 'node': node, **components}


def _compile_recipe(m, recipe):
    """Compile exactly once: each pressure term becomes q=p*b per member."""
    members = {e['id']: e for e in m['elements']}
    nodes = {n['id'] for n in m['nodes']}
    cases = []
    for case in recipe['cases']:
        loads = []
        for term in case['terms']:
            if term['kind'] == 'surface-on-members':
                vec = term['globalUnitVector']
                if len(vec) != 3 or not math.isclose(sum(v*v for v in vec), 1., abs_tol=1e-12):
                    raise ValueError('A surface action requires a global unit vector')
                q = term['pressureKNM2'] * term['tributaryWidthM']
                if not math.isfinite(q) or term['tributaryWidthM'] <= 0:
                    raise ValueError('Invalid pressure/tributary width')
                if len(term['members']) != len(set(term['members'])):
                    raise ValueError('A surface term repeats a member')
                for eid in term['members']:
                    if eid not in members or members[eid]['type'] in ('truss', 'brace'):
                        raise ValueError('Distributed load needs a bending member')
                    loads.append({'type': 'distributed', 'element': eid,
                                  **{f'w{a}': q*v for a, v in zip('xyz', vec) if v}})
            elif term['kind'] == 'nodal':
                if term['node'] not in nodes or set(term)-{'kind', 'node', 'fx', 'fy', 'fz'}:
                    raise ValueError('Invalid nodal recipe term')
                loads.append({'type': 'nodal', **{k: v for k, v in term.items() if k != 'kind'}})
            else:
                raise ValueError('Unsupported engineering load recipe')
        for i, load in enumerate(loads):
            load.update(id=f'{case["id"]}-{i+1}', reference_frame='global')
        cases.append({'id': case['id'], 'type': case['type'], 'loads': loads})
    m['load_cases'] = cases


def _midspan_observations(m, recipe):
    """Insert continuous EB beam stations; never add a hinge or new support."""
    nodes = {n['id']: n for n in m['nodes']}
    replacements, observations = {}, []
    for e in list(m['elements']):
        if e['type'] != 'beam':
            continue
        a, b = (nodes[n] for n in e['nodes'])
        if math.dist([a[k] for k in 'xyz'], [b[k] for k in 'xyz']) < 4.:
            continue
        nid = 'OBS-'+e['id']
        _node(m, nid, (a['x']+b['x'])/2, (a['z']+b['z'])/2, (a['y']+b['y'])/2)
        m['elements'].remove(e)
        if m['coordinate_system']['dimension'] == '3d':
            del m['metadata']['elementReferenceVectors'][e['id']]
        children = []
        for suffix, x, y in [('i', e['nodes'][0], nid), ('j', nid, e['nodes'][1])]:
            child = _member(m, e['id']+'-'+suffix, x, y, e['type'], e['section'])
            child['material'] = e['material']
            children.append(child['id'])
        replacements[e['id']] = children
        observations.append(nid)
    for case in recipe['cases']:
        for term in case['terms']:
            if term['kind'] == 'surface-on-members':
                term['members'] = [child for eid in term['members'] for child in replacements.get(eid, [eid])]
    return observations


def build_engineering(source_id: str, subproblem: int) -> dict:
    """Return a fresh model, public load recipe and its explicit authoring basis."""
    if source_id not in SOURCE_IDS:
        raise ValueError('Unknown or not selected real-project source: '+str(source_id))
    if type(subproblem) is not int or not 0 <= subproblem <= 2:
        raise ValueError('subproblem must be an integer from 0 through 2')
    source = next(s for s in json.loads(Path(__file__).with_name('source_registry.json').read_text())['sources']
                  if s['sourceId'] == source_id)
    concrete = source_id in ('SRC-CABLE-2010', 'SRC-SH-RC-2020', 'SRC-CQ-SCHOOL1-2020', 'SRC-HILLSIDE-2020')
    if source_id == 'SRC-CABLE-2010' and subproblem == 1:
        concrete = False
    dimension = '3d' if (source_id, subproblem) in {
        ('SRC-LUOYANG-2022', 1), ('SRC-PIPE-2020', 2), ('SRC-SPORT-2023', 2)} else '2d'
    m = _new(source_id, dimension, concrete)
    basis = [
        f'来源 {source_id}；'+source['subproblemProposals'][subproblem]['description'],
        '来源事实：'+'；'.join(f['factId']+' '+f['statement'] for f in source['facts']),
        '仅线弹性小位移杆系；刚接梁柱、双向轴力杆及题给支座。所有截面、连接简化与新增边界属于作者设定，不是原工程图纸复现或规范设计结论。',
        ('作者材料：未开裂线弹性RC，E=30000MPa，nu=0.2，G=12500MPa，rho=2500kg/m³。'
         if concrete else '作者材料：线弹性钢，E=206000MPa，nu=0.3，G=E/[2(1+nu)]，rho=7850kg/m³。'),
        '作者截面：B/C/A均为等效实心矩形，截面尺寸及由矩形公式计算的A/Iy/Iz/J以model.sections为准；不代表原工程型钢或实配筋。',
        '自重自动生成关闭。D/Q/W均显式给定；荷载recipe是唯一编译输入，面载只按q=p×分担宽度折算一次，沿杆实际长度作用。SERVICE=D+Q，REVERSE=D-W。',
    ]
    loaded, nodal_top = [], None
    d_terms = q_terms = w_terms = None
    pressure, live, width = .8, .5, 3.

    if source_id == 'SRC-COLD-2023':
        pressure, live, width = 2., .5, 7.5
        if subproblem == 0:
            loaded = _frame(m, [23.61, 32.21], [31.2])
            basis.append('保留不等双跨及31.2m檐高；作者将坡屋面等效为同标高横梁，屋面恒活载按来源2.0/0.5kN/m²、7.5m分担宽度作用。')
        elif subproblem == 1:
            loaded = _frame(m, [6.8, 7.5, 7.5], [31.2])
            width = 4.
            basis.append('保留纵向边部三柱距；作者采用刚接等效纵向柱列、4m分担宽度，不能视作原纵向支撑系统。')
        else:
            loaded = _continuous(m, [6.8, 7.5, 7.5, 7.4])
            width = 1.5
            basis.append('屋面四跨传力梁；两端取6.8/7.4m边跨及两个7.5m标准跨，属于重新排列的明确连续梁理想化；作者支座P-R-R-R-R，受荷带宽1.5m。')

    elif source_id == 'SRC-JIANGSU-2023':
        width = 8.
        if subproblem == 0:
            loaded = _frame(m, [8., 8.], [11.35])
            basis.append('8m是纵向柱距，不是五个横向跨度；作者采用纵向两跨刚接框架，屋面受荷带宽8m。')
        elif subproblem == 1:
            _node(m, 'BASE', 0., 0., support='F')
            _node(m, 'CRANE', 0., 7.5)
            _node(m, 'TOP', 0., 11.35)
            _member(m, 'LOWER', 'BASE', 'CRANE', 'column', 'C')
            _member(m, 'UPPER', 'CRANE', 'TOP', 'column', 'B')
            d_terms = [_nodal('CRANE', fz=-30.), _nodal('TOP', fz=-12.)]
            q_terms = [_nodal('CRANE', fz=-25.)]
            w_terms = [_nodal('CRANE', fx=8.), _nodal('TOP', fx=6.)]
            basis.append('吊车作用点7.5m、柱顶11.35m；30/12/25kN竖向等效作用及8/6kN横向作用均为作者给定，不从5t吊车吨位推算轮压。')
        else:
            _node(m, 'BASE', 0., 0., support='P')
            _node(m, 'MID', 0., 11.35/2)
            _node(m, 'TOP', 0., 11.35)
            m['nodes'][-1]['restraints'][0] = True
            _member(m, 'LOWER', 'BASE', 'MID', 'column', 'C')
            _member(m, 'UPPER', 'MID', 'TOP', 'column', 'C')
            d_terms = [_nodal('TOP', fz=-18.)]
            q_terms = [_nodal('MID', fz=-6.)]
            w_terms = [_nodal('MID', fx=12.)]
            basis.append('抗风柱高11.35m；底铰为来源事实，作者增设顶部水平约束、竖向自由，形成稳定风柱子问题；中点风力12kN为题给。')

    elif source_id == 'SRC-LUOYANG-2022':
        width = 7.7
        if subproblem == 0:
            loaded = _frame(m, [24.46, 25., 24.46], [8.5], gable=.05)
            basis.append('三跨及柱顶8.5m来自项目；每跨双坡5%屋面为作者设定，压力作用面积定义为杆件实际长度×7.7m。')
        elif subproblem == 1:
            loaded = _space_strip(m, [7.7, 7.7], 24.46, 8.5)
            width = 2.5
            basis.append('截取首横跨24.46m内的两列纵向柱及7.7+7.7m两柱距；作者将纵横顶梁均设刚接，纵向每列受荷带宽2.5m，横梁不重复分配该面荷载。')
        else:
            loaded = _continuous(m, [7.7, 7.7])
            width = 1.8
            basis.append('作者两跨连续檩条子问题，柱距7.7m来自来源，连续性及1.8m受荷带宽为题设。')

    elif source_id == 'SRC-PIPE-2020':
        if subproblem == 0:
            nodal_top = _truss(m, 20., 2.5, 8)
            d_terms = [_nodal(n, fz=-5.48 if i in (0, 8) else -10.37) for i, n in enumerate(nodal_top)]
            q_terms = [_nodal(n, fz=-9.25 if i in (0, 8) else -18.50) for i, n in enumerate(nodal_top)]
            basis.append('采用论文20m×2.5m研究方案，8节间各2.5m；单片节点恒/活载直接取表3端点5.48/9.25kN、内部10.37/18.50kN，不能再次平分。上弦受荷、铰结腹杆为作者理想化。')
        elif subproblem == 1:
            loaded = _frame(m, [2.5], [1.25, 1.25])
            _node(m, 'LOW-MID', 1.25, 0.)
            _member(m, 'LOW-a', 'N0-0', 'LOW-MID')
            _member(m, 'LOW-b', 'LOW-MID', 'N1-0')
            # Total support length of pipes = 2.5m, explicitly tributary here.
            d_terms = [_nodal('LOW-MID', fz=-7.)]
            q_terms = [_nodal('LOW-MID', fz=-14.75)]
            for j, dg, qg in ((1, 5.25, 7.5), (2, 7., 14.75)):
                # The row resultant is an explicit central point idealization.
                e = next(e for e in m['elements'] if e['id'] == f'B0-{j}')
                m['elements'].remove(e)
                mid = _node(m, f'ROW{j}-MID', 1.25, 1.25*j)
                _member(m, f'ROW{j}-a', f'N0-{j}', mid)
                _member(m, f'ROW{j}-b', mid, f'N1-{j}')
                d_terms.append(_nodal(mid, fz=-dg))
                q_terms.append(_nodal(mid, fz=-qg))
            basis.append('横向宽2.5m来自来源；三层高度0/1.25/2.5m和2.5m管道分担长度为作者设定。表2线重：气管0.4/0.5、煤气管2.0/4.9、水管0.7/1.0kN/m；上/下排总G/Q=7/14.75kN、中排5.25/7.5kN。')
            basis.append('各排多管道作用以该排横梁跨中合力代替；这是明确作者理想化，不声称管道实际落点。横梁跨中连续，无铰释放。')
        else:
            loaded = _double_truss(m, 20., 2.5, 8, 2.5, middle=True)
            pressure, live, width = 1.2, .8, 2.5
            basis.append('双片间距2.5m、20m研究跨度、三排横梁来自来源；作者三排高程0/1.25/2.5m、梁式弦杆及中排纵向集力梁、四角平移固定支座；各横梁G/Q=1.2/0.8kN/m²×2.5m，均为独立题设，不使用表3再叠加。')

    elif source_id == 'SRC-SH-STEEL-2020':
        width = 13.5
        if subproblem == 0:
            nodal_top = _truss(m, 29., 3., 12)
            basis.append('AB跨29m及平行弦屋架来自来源；作者桁高3m、12等节间、双向Pratt腹杆与支座。')
        elif subproblem == 1:
            loaded = _frame(m, [22.], [33.6])
            basis.append('BC跨22m实腹屋面梁来自来源；统一柱顶33.6m是选取报告一个标高并作等高理想化，格构柱为作者等效常截面，不声称原各柱相同。')
        else:
            loaded = _frame(m, [13.5], [20.086, 12.884], braces=True)
            width = 4.
            basis.append('来源纵向13.5m支撑跨与20.086/32.970m柱段标高；作者每柱段单根双向斜杆、两层刚接连系梁、4m受荷宽度。')

    elif source_id == 'SRC-SPORT-2023':
        width = 6.
        if subproblem == 0:
            nodal_top = _truss(m, 38., 2.3, 10)
            basis.append('楼盖跨度38m、桁高2.3m来自来源；作者10节间纯双向轴力桁架，6m榀距。')
        elif subproblem == 1:
            nodal_top = _truss(m, 38., 2.3, 8, mixed=True)
            basis.append('来源采用梁弦杆/轴力腹杆；作者8节间及6m榀距，只保留裸杆系，删除楼板后的结果不与原舒适度周期直接比较。')
        else:
            loaded = _double_truss(m, 38., 2.3, 10, 6.)
            width = 3.8
            basis.append('两榀38m×2.3m楼盖桁架；作者榀距6m、10节间、横梁受荷带宽3.8m，四角固定平移支座；板刚度及人致舒适度均排除。')

    elif source_id == 'SRC-CABLE-2010':
        if subproblem == 0:
            loaded = _frame(m, [6., 6., 6.], [4.5, 3.9, 3.9, 3.9, 3.9])
            pressure, live, width = 4., 2., 4.
            basis.append('综合楼18m外宽仅用作作者6+6+6m分跨总宽，不宣称原轴网；首层4.5m其余3.9m为来源事实，楼面G/Q=4/2kN/m²及4m分担宽度为题设。')
        elif subproblem == 1:
            nodal_top = _truss(m, 24., 2.4, 6)
            width = 9.
            basis.append('厂房24m屋架跨度及9m柱距来自来源；作者桁高2.4m、6节间、双向腹杆，不模拟吊车与全厂房。')
        else:
            loaded = _frame(m, [9., 9.], [3., 3., 3., 3.])
            pressure, live, width = 3.5, 2., 3.
            basis.append('宿舍4×3m层高来自同一可研；18m外宽由作者分为9+9m，不宣称原柱网；G/Q=3.5/2kN/m²及3m分担宽度为题设。')

    elif source_id == 'SRC-SH-RC-2020':
        if subproblem == 0:
            nodal_top = _truss(m, 18., 2.4, 6, elevation=7.7, columns=True)
            width = 6.
            basis.append('18m横跨、7.7m主体高度来自来源；作者将带天窗复杂屋盖简化为2.4m平行弦轴力桁架，6节间，固定柱脚；未开裂RC等效杆件，不含原屋面板。')
        elif subproblem == 1:
            loaded = _frame(m, [6., 6., 6.], [3.85, 3.85])
            pressure, live, width = 4., 2., 4.
            basis.append('3.85m新增楼层及7.7m主体来自来源；新增柱位置由作者取6+6+6m，两个层高均3.85m，忽略原表7.68m的不同基准。')
        else:
            loaded = _frame(m, [6., 6.], [3.85, 3.85], braces=True)
            # Steel braces are explicitly distinct from uncracked RC frame.
            m['materials'].append({'id': 'BRACE-STEEL', 'name': 'Authored bilateral elastic steel brace',
                'type': 'steel', 'E': 206000., 'G': 206000/2.6, 'nu': .3, 'rho': 7850.})
            for e in m['elements']:
                if e['type'] == 'truss':
                    e['material'] = 'BRACE-STEEL'
            pressure, live, width = 3., 1.5, 3.
            basis.append('来源有新增柱间支撑；作者截取6+6m两跨两层，3.85m层高，RC裸框架加双向钢斜杆。钢杆E206000MPa、nu0.3、rho7850；连接、杆截面与横梁为题设。')

    elif source_id == 'SRC-CQ-SCHOOL1-2020':
        spans = [9.6, 9.6, 9.45] if subproblem != 1 else [6.6]
        stories = 3 if subproblem == 2 else 6
        loaded = _frame(m, spans, [3.9]*stories)
        pressure, live, width = 4., 2.5, 3.2
        basis.append('纵向9.6/9.6/9.45m是建筑开间，作者按其建立等效柱轴线；横向6.6m为明确作者设定。来源层高3.9m；不跨越变形缝、不含填充墙和空心板。')
        if subproblem == 2:
            basis.append('仅截取上部三层，以截面处固定端作为公开人工边界；结果只属于该截断模型，不当作完整六层建筑顶三层响应。')

    elif source_id == 'SRC-HILLSIDE-2020':
        spans = [8.4]*8 if subproblem == 0 else [8.4, 2.1, 8.4] if subproblem == 1 else [8.4]*4
        offsets = [0., 0., 1.5, 1.5, 1.5] if subproblem == 2 else None
        loaded = _frame(m, spans, [3.8]*5, offsets=offsets)
        pressure, live, width = 4.5, 2., 8.4
        basis.append('5层、标准3.8m及8.4m/2.1m轴网来自来源；作者以首层楼面3.8m为基准，不纳入原图额外嵌固段；G/Q=4.5/2kN/m²、分担宽8.4m为题设。')
        if subproblem == 2:
            basis.append('取纵向连续四跨；作者基节点高程[0,0,1.5,1.5,1.5]m，对应来源研究Δh=1.5m，底层短柱净高2.3m，固定支点不视为沉降。')

    if d_terms is None:
        if nodal_top is not None:
            nodes = {n['id']: n for n in m['nodes']}
            dx = (nodes[nodal_top[-1]]['x']-nodes[nodal_top[0]]['x'])/(len(nodal_top)-1)
            # Horizontal strip pressure; coordinates may be rounded to 6 places.
            d_terms = [_nodal(n, fz=-pressure*width*dx*(.5 if i in (0, len(nodal_top)-1) else 1.))
                       for i, n in enumerate(nodal_top)]
            q_terms = [_nodal(n, fz=-live*width*dx*(.5 if i in (0, len(nodal_top)-1) else 1.))
                       for i, n in enumerate(nodal_top)]
            basis.append(f'作者屋面等效节点作用：G/Q={pressure}/{live}kN/m²，分担宽{width}m，等节间水平长度{dx:.9g}m；内部p×b×节间，端点取半。')
        else:
            if not loaded:
                raise AssertionError('Missing load-bearing substructure')
            d_terms = [_surface(loaded, pressure, width)]
            # Partial occupancy is a stated load pattern, not hidden dead load.
            q_terms = [_surface(loaded[::2], live, width)]
            basis.append(f'公开受荷：D对recipe中全部指定梁，p={pressure}kN/m²；Q对列出的交替梁，p={live}kN/m²；分担宽{width}m。未列构件不重复分配面载。')
    if w_terms is None:
        free = [n for n in m['nodes'] if not n['restraints'][0]]
        target = max(free, key=lambda n: (n['z'], n['x'], n['y']))
        w_terms = [_nodal(target['id'], fx=10., **({'fy': 4.} if dimension == '3d' else {}))]
        basis.append('W为最高自由节点上题给等效横力10kN；3D另加全局y向4kN，不声称原工程风压规范计算结果。')
    recipe = {'cases': [
        {'id': 'D', 'type': 'dead', 'terms': d_terms},
        {'id': 'Q', 'type': 'live', 'terms': q_terms},
        {'id': 'W', 'type': 'wind', 'terms': w_terms},
    ]}
    observed = _midspan_observations(m, recipe)
    if source_id == 'SRC-JIANGSU-2023' and subproblem in (1, 2):
        hint = {'nodes': ['TOP' if subproblem == 1 else 'MID'], 'component': 'ux'}
    elif source_id in ('SRC-PIPE-2020', 'SRC-SPORT-2023') and subproblem == 2:
        middle = 4 if source_id == 'SRC-PIPE-2020' else 5
        hint = {'nodes': [f'0U{middle}', f'1U{middle}'], 'component': 'uz'}
        basis.append('空间子结构两端四根竖杆保留梁柱弯曲刚度，与横梁形成刚接横向端框，内部竖腹杆仍为双向轴力杆；这是公开的端部稳定理想化，不是单靠约束掩盖侧移机构。')
    elif nodal_top:
        hint = {'nodes': [nodal_top[len(nodal_top)//2]], 'component': 'uz'}
    else:
        # Existing midpoint stations precede subdivisions, when available.
        mids = [n['id'] for n in m['nodes'] if n['id'].startswith('M') or n['id'].endswith('-MID')]
        hint = {'nodes': mids or observed, 'component': 'uz'}
    if not hint['nodes']:
        raise AssertionError('Every engineering model requires a physical observation station')
    basis.append('观测跨中节点与两侧梁连续连接，无新增铰、质量或约束；细分段保持原截面及同一荷载强度。constraintHint指向实际模型节点。')
    _compile_recipe(m, recipe)
    # State actual numbers, so public basis remains readable without inference.
    basis.append('截面尺寸(m)：'+', '.join(f'{s["id"]}={s["shape"]["B"]/1000:g}×{s["shape"]["H"]/1000:g}' for s in m['sections']))
    return {'model': m, 'loadRecipe': recipe, 'authoringBasis': basis,
            'subproblemId': source['subproblemProposals'][subproblem]['subproblemId'],
            'constraintHint': hint}
