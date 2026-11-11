"""Author an isolated six-case challenge pilot; never edit research-300."""
import argparse
import copy
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path
import sys

for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '1'
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/research300'))
from reference_io import selection_factors, quantity_unit, convert_value
from reference_solver import solve as matrix_solve
from opensees_native import solve as native_solve


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as handle:
        if isinstance(value, str):
            handle.write(value)
        else:
            json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
            handle.write('\n')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def table(headers, rows):
    stream = io.StringIO(newline='')
    writer = csv.writer(stream)
    writer.writerow(headers)
    writer.writerows(rows)
    return stream.getvalue()


def frame(spatial):
    xs = [0., 3.8, 8.4, 13.5] if spatial else [0., 3.7, 8.1, 13.6, 17.9]
    ys = [0., 4.6, 10.2] if spatial else [0.]
    zs = [0., 3.2, 6.9, 10.7]
    model = {'schema_version': '2.2.0', 'unit_system': 'SI',
             'coordinate_system': {'dimension': '3d' if spatial else '2d', 'plane': None if spatial else 'xz',
                                   'semantics': 'global-z-up', 'version': 1,
                                   'dof_order': ['ux', 'uy', 'uz', 'rx', 'ry', 'rz']},
             'nodes': [], 'elements': [],
             'materials': [{'id': 'M1', 'name': 'Elastic steel', 'type': 'steel', 'E': 206000., 'G': 79230.76923, 'nu': .3, 'rho': 7850.},
                           {'id': 'M2', 'name': 'Elastic concrete', 'type': 'concrete', 'E': 33000., 'G': 13750., 'nu': .2, 'rho': 2500.}],
             'sections': [{'id': sid, 'name': sid, 'type': 'custom',
                           'properties': dict(zip(('A', 'Iy', 'Iz', 'J'), values))}
                          for sid, values in [('C1', (.05, .00042, .00023, .00002)),
                                              ('C2', (.062, .00061, .00035, .00004)),
                                              ('B1', (.02, .0002, .00007, .00001)),
                                              ('B2', (.024, .00026, .00011, .000015)),
                                              ('R1', (.006, .000009, .000008, .000003))]],
             'load_cases': [], 'load_combinations': [
                 {'id': 'D', 'factors': {'D': 1.2, 'L': 1.5}},
                 {'id': 'SERVICE', 'factors': {'D': 1., 'L': .6, 'WX': 1.}},
                 {'id': 'REVERSE', 'factors': {'D': 1., 'L': .3, 'WX': -1.}}],
             'analysis_control': {k: False for k in ('self_weight', 'rigid_floor', 'p_delta', 'rigid_offsets', 'construction_stage')},
             'metadata': {'elementReferenceVectors': {}} if spatial else {}}
    def node_id(i, j, k):
        return f'N{i}-{j}-{k}'
    for k, z in enumerate(zs):
        for j, y in enumerate(ys):
            for i, x in enumerate(xs):
                fixed = [k == 0] * 6 if spatial else [k == 0, True, k == 0, True, k == 0, True]
                model['nodes'].append({'id': node_id(i, j, k), 'x': x, 'y': y, 'z': z, 'restraints': fixed})
    def element(eid, kind, start, end, section, roll=0.):
        model['elements'].append({'id': eid, 'type': kind, 'nodes': [start, end], 'material': 'M1',
                                  'section': section, 'rotation_angle': roll})
        if spatial:
            model['metadata']['elementReferenceVectors'][eid] = [1., 0., 0.] if kind == 'column' else [0., 0., 1.]
    for k in range(1, 4):
        for j in range(len(ys)):
            for i in range(len(xs)):
                element(f'C{i}-{j}-{k}', 'column', node_id(i, j, k-1), node_id(i, j, k),
                        'C2' if (i+j) % 2 else 'C1', 90. if spatial and i == 2 and k == 2 else 0.)
            for i in range(len(xs)-1):
                # A missing upper edge bay makes the spatial frame nonuniform.
                if spatial and (i, j, k) == (2, 2, 3):
                    continue
                element(f'X{i}-{j}-{k}', 'beam', node_id(i, j, k), node_id(i+1, j, k), 'B2' if i % 2 else 'B1')
        if spatial:
            for j in range(len(ys)-1):
                for i in range(len(xs)):
                    element(f'Y{i}-{j}-{k}', 'beam', node_id(i, j, k), node_id(i, j+1, k), 'B2' if j else 'B1')
    for k in (1, 3):
        element(f'R{k}', 'truss', node_id(1, 0, k-1), node_id(2, 0, k), 'R1')
    dead, live = [], []
    for e in model['elements']:
        if e['type'] != 'beam':
            continue
        dead.append({'id': 'G-' + e['id'], 'type': 'distributed', 'element': e['id'],
                     'reference_frame': 'global', 'wz': -7.5})
        if e['id'].endswith('-3'):
            live.append({'id': 'Q-' + e['id'], 'type': 'distributed', 'element': e['id'],
                         'reference_frame': 'global', 'wz': -4.2})
    if not spatial:
        load = next(l for l in dead if l['element'] == 'X1-0-2')
        load.update(start=.44, end=3.96)
        live.append({'id': 'P-local', 'type': 'point', 'element': 'X2-0-3',
                     'position': 1.925, 'reference_frame': 'global', 'fz': -15.})
    model['load_cases'] = [{'id': 'D', 'loads': dead}, {'id': 'L', 'loads': live},
                           {'id': 'WX', 'loads': [{'id': 'W-top', 'type': 'nodal', 'node': node_id(len(xs)-1, len(ys)-1, 3),
                                                 'reference_frame': 'global', 'fx': 24., 'fy': 7. if spatial else 0., 'mz': 5. if spatial else 0.}]}]
    return model


def requests(model, selections, mm=False):
    top = model['nodes'][-1]['id']
    first = model['nodes'][0]['id']
    spatial = model['coordinate_system']['dimension'] == '3d'
    specs = [(top, 'ux'), (top, 'uz'), (first, 'Fx'), (first, 'My')]
    if spatial:
        specs += [(top, 'uy'), (first, 'Mz')]
    return [{'id': f'{s["kind"]}-{s["id"]}-{nid}-{component}', 'selection': s,
             'location': {'kind': 'node', 'id': nid}, 'component': component,
             'unit': 'mm' if mm and component.startswith('u') else quantity_unit(component),
             'tolerance': {'absolute': 1e-5 if mm and component.startswith('u') else 1e-8, 'relative': 1e-6}}
            for s in selections for nid, component in specs]


def initial_documents(model, *, raster=False, missing_support=False, conflict=False, revision=False):
    docs = {}
    nodes = [[n['id'], *(round(n[k]*1000, 7) for k in 'xyz'),
              *('?' if missing_support and n['id'] == 'N4-0-0' and i == 0 else int(v)
                for i, v in enumerate(n['restraints']))] for n in model['nodes']]
    if not raster:
        docs['geometry.csv'] = table(['node', 'X_mm', 'Y_mm', 'Z_mm', 'ux_fixed', 'uy_fixed', 'uz_fixed', 'rx_fixed', 'ry_fixed', 'rz_fixed'], nodes)
    docs['members.csv'] = table(['member', 'start_node', 'end_node', 'element_type', 'material', 'section', 'roll_deg'],
                                [[e['id'], *e['nodes'], e['type'], e['material'],
                                  'B1' if revision and e['id'] == 'X1-0-2' else e['section'], e['rotation_angle']]
                                 for e in model['elements']])
    docs['sections.csv'] = table(['section', 'A_mm2', 'Iy_mm4', 'Iz_mm4', 'J_mm4'],
                                 [[s['id'], *(round(s['properties'][k]*factor, 4) for k, factor in [('A', 1e6), ('Iy', 1e12), ('Iz', 1e12), ('J', 1e12)])]
                                  for s in model['sections']])
    docs['materials.csv'] = table(['material', 'E_GPa', 'G_GPa', 'nu', 'rho_kg_per_m3'],
                                  [[m['id'], m['E']/1000, m['G']/1000, m['nu'], m['rho']] for m in model['materials']])
    rows = []
    for case in model['load_cases']:
        for load in case['loads']:
            revised = revision and case['id'] == 'D' and load.get('element') == 'X1-0-2'
            rows.append([case['id'], load['id'], load['type'], load.get('node', load.get('element')),
                         load['reference_frame'], load.get('position', ''), .44 if revised else load.get('start', ''), 3.96 if revised else load.get('end', ''),
                         *(load.get(k, 0)*1000 for k in ('wx', 'wy', 'wz', 'fx', 'fy', 'fz', 'mx', 'my', 'mz'))])
    docs['loads.csv'] = table(['case', 'load_id', 'type', 'target', 'frame', 'position_m', 'start_m', 'end_m',
                               'wx_N_per_m', 'wy_N_per_m', 'wz_N_per_m', 'fx_N', 'fy_N', 'fz_N', 'mx_Nm', 'my_Nm', 'mz_Nm'], rows)
    docs['combinations.csv'] = table(['combination', 'D', 'L', 'WX'],
                                    [[c['id'], *(c['factors'].get(k, 0) for k in ('D', 'L', 'WX'))] for c in model['load_combinations']])
    docs['design-basis.md'] = '''# Analysis basis / 分析依据
Global Z is vertical. Coordinates in geometry.csv, where supplied, are millimetres; the raster drawing has its own printed coordinate units. loads.csv uses N, N/m and N·m, with member positions in metres. Blank distributed start/end means the full physical member. Roll is in degrees. Properties are the supplied uncoupled centroidal elastic constants, without fillets or further section deductions.
Perform first-order small-displacement elastic Euler–Bernoulli analysis. Self weight, rigid floor, P-delta, rigid offsets and construction stages are OFF. Columns use reference vector (1,0,0); other 3D frame members use (0,0,1). Trusses carry axial force only and have no tension-only restriction. Public member start/end order defines the local axes; roll is about its positive local X.
Use every explicitly listed member; geometrical line crossings introduce no extra joints. The selected engine is OpenSees. Both case:D and combination:D exist and have different physical meaning.
全局 Z 向上。毫米、牛顿制的原始资料需按各列单位解释。所有列出的杆件均为实际构件，线条相交不自动增加节点。仅采用公开给定的弹性性质；工况 D 与组合 D 是不同选择。
'''
    if raster:
        docs['drawing-notes.md'] = '''Geometry is supplied only in geometry.png. Coordinate labels are (X,Z) in metres; all Y=0. Every node with Z=0 is fully fixed. Other nodes have only the inactive planar DOFs uy/rx/rz fixed. Member connectivity and properties come from the schedules, not from guessing line crossings. The drawing has no embedded text/coordinate metadata or SVG counterpart.
几何只见附图；标注坐标为米。底层节点全固定，其余节点仅固定平面外自由度。杆件连接按构件表核对。
'''
    if revision:
        docs['issued-revision.md'] = '''Issued revision B supersedes the members.csv section assignment ONLY for X1-0-2: use B2. It also changes its dead line-load interval to start=0.88 m, end=2.64 m, keeping the listed intensity. All other fields remain as issued in the schedules. This is the only authoritative revision.
正式 B 版仅覆盖 X1-0-2 的截面及恒载区间：截面 B2，起点 0.88 m、终点 2.64 m，强度不变。其余资料沿用原表。
'''
    if missing_support:
        docs['open-issue.md'] = '''The support designer has not confirmed N4-0-0's global ux restraint; '?' is unknown, not free or fixed. Other restraints are confirmed. Obtain the missing decision before issuing any analysis. Ask for the missing field; do not invent a restraint.
节点 N4-0-0 的 ux 约束尚未确认，问号不代表自由或固定。其余约束均已确认。计算前需澄清。
'''
    if conflict:
        docs['coordination-memo.md'] = '''Two documents with equal issue status conflict: members.csv lists C0-0-1 roll=0 degrees, while the structural orientation memo lists roll=90 degrees. Neither document has precedence. Ask which is intended before issuing an analysis; all other member orientations are confirmed.
同等签发状态的两份资料对 C0-0-1 的截面转角存在 0°/90° 冲突，没有优先级，需先澄清。
'''
    return docs


def raster_geometry(model, path):
    from PIL import Image, ImageDraw, ImageFont
    image = Image.new('RGB', (1800, 1300), 'white')
    draw = ImageDraw.Draw(image)
    font_path = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    font = ImageFont.truetype(font_path, 19)
    small = ImageFont.truetype(font_path, 17)
    def pos(n):
        return 90+n['x']*88, 1160-n['z']*90
    nodes = {n['id']: n for n in model['nodes']}
    for e in model['elements']:
        draw.line([pos(nodes[n]) for n in e['nodes']], fill='#334155', width=4)
    for n in model['nodes']:
        x, y = pos(n)
        draw.ellipse((x-5, y-5, x+5, y+5), fill='#111827')
        draw.text((x-25, y-55), n['id'], fill='black', font=font)
        draw.text((x-25, y-30), f"({n['x']:g},{n['z']:g})", fill='#1d4ed8', font=small)
        if n['z'] == 0:
            draw.line((x-25, y+10, x+25, y+10), fill='black', width=6)
    draw.text((70, 30), 'Geometry / Global X-Z plane / coordinates in metres', font=font, fill='black')
    image.save(path)  # Pixels only; no text chunks or model metadata.


def definitions():
    a, b = frame(True), frame(False)
    cases = []
    case = {'id': 'CH-001', 'title': '三层不规则空间框架：六轮独立修改与局部撤销', 'category': 'long-workflow',
            'documents': initial_documents(a), 'turns': []}
    instructions = [
        '按签发资料建立模型，分析 SERVICE 组合。保留所有构件和荷载分组。',
        '只把 L 工况下所有屋面均布荷载的强度提高 15%；其他工况、点荷载和节点荷载不变。重新分析 SERVICE。',
        '只把下层柱 C0-0-1 的截面转角改为 90°，保留上层柱与此前的荷载调整。重新分析 SERVICE。',
        '撤销第 2 轮的屋面活载增幅，恢复签发强度；保留第 3 轮的柱转角。重新分析 SERVICE。',
        '只把 C0-0-1 的材料改为 M2；同时在 WX 工况既有 W-top 节点荷载中增加全局 Fz=+4 kN。保留该荷载的 Fx/Fy/Mz，以及此前其余修改。重新分析 SERVICE。',
        '只撤销第 3 轮对 C0-0-1 转角的修改；保留第 5 轮的材料和全局竖向力、其余全部已确认修改。重新分析 SERVICE。']
    for i, instruction in enumerate(instructions):
        if i == 1:
            for load in a['load_cases'][1]['loads']:
                if load['type'] == 'distributed':
                    load['wz'] *= 1.15
        if i == 2:
            a['elements'][0]['rotation_angle'] = 90.
        if i == 3:
            for load in a['load_cases'][1]['loads']:
                if load['type'] == 'distributed':
                    load['wz'] = -4.2
        if i == 4:
            a['elements'][0]['material'] = 'M2'
            a['load_cases'][2]['loads'][0]['fz'] = 4.
        if i == 5:
            a['elements'][0]['rotation_angle'] = 0.
        case['turns'].append({'instruction': instruction, 'kind': 'analyze', 'model': copy.deepcopy(a),
                              'requests': requests(a, [{'kind': 'combination', 'id': 'SERVICE'}])})
    cases.append(case)
    case = {'id': 'CH-002', 'title': '三层平面框架：局部荷载、同名工况组合与查询复用', 'category': 'long-workflow',
            'documents': initial_documents(b), 'turns': []}
    instructions = [
        '建立模型，分别报告 case:D 和 combination:D。二者不能合并。',
        '仅将 L 工况的 P-local 改为全局 Fz=-19 kN，位置改为 X2-0-3 起端后 3.575 m；其余荷载不变。分别重算 D 工况和 D 组合。',
        '仅将 D 工况 X1-0-2 上的均布荷载作用区间改为起点 0.88 m、终点 2.64 m，线强度不变。保留点荷载修改。分别重算 D 工况和 D 组合。',
        '物理模型不变，不要重新求解。复用上一轮两种选择的实际结果，将请求的位移改用 mm 报告；力、力矩仍用原单位。',
        '仅撤销 P-local 的位置修改，恢复起端后 1.925 m；保留 -19 kN 的力值和第 3 轮恒载区间。分别重算 D 工况和 D 组合。',
        '仅撤销第 3 轮的恒载区间修改，恢复 0.44 m 至 3.96 m；保留当前点荷载力值、位置及其他字段。分别重算 D 工况和 D 组合。']
    for i, instruction in enumerate(instructions):
        if i == 1:
            b['load_cases'][1]['loads'][-1].update(fz=-19., position=3.575)
        if i == 2:
            next(l for l in b['load_cases'][0]['loads'] if l['element'] == 'X1-0-2').update(start=.88, end=2.64)
        if i == 4:
            b['load_cases'][1]['loads'][-1]['position'] = 1.925
        if i == 5:
            next(l for l in b['load_cases'][0]['loads'] if l['element'] == 'X1-0-2').update(start=.44, end=3.96)
        case['turns'].append({'instruction': instruction, 'kind': 'query' if i == 3 else 'analyze', 'model': copy.deepcopy(b),
                              'requests': requests(b, [{'kind': 'case', 'id': 'D'}, {'kind': 'combination', 'id': 'D'}], mm=i == 3)})
    cases.append(case)
    c = frame(False)
    cases.append({'id': 'CH-003', 'title': '仅栅格几何图与构件、材料、荷载清单联合建模', 'category': 'multi-source',
                  'raster': True, 'documents': initial_documents(c, raster=True),
                  'turns': [{'instruction': '联合几何图及各清单建立实际结构，分别分析 SERVICE 与 REVERSE 组合。',
                             'kind': 'analyze', 'model': c, 'requests': requests(c, [{'kind': 'combination', 'id': x} for x in ('SERVICE', 'REVERSE')])}]})
    d = frame(False)
    next(e for e in d['elements'] if e['id'] == 'X1-0-2')['section'] = 'B2'
    next(l for l in d['load_cases'][0]['loads'] if l['element'] == 'X1-0-2').update(start=.88, end=2.64)
    cases.append({'id': 'CH-004', 'title': '签发清单与正式修订单的局部覆盖', 'category': 'multi-source',
                  'documents': initial_documents(d, revision=True),
                  'turns': [{'instruction': '按各资料的签发状态建立最终模型，分析 D 工况、D 组合和 SERVICE 组合。',
                             'kind': 'analyze', 'model': d, 'requests': requests(d, [{'kind': 'case', 'id': 'D'}, {'kind': 'combination', 'id': 'D'}, {'kind': 'combination', 'id': 'SERVICE'}])}]})
    e = frame(False)
    cases.append({'id': 'CH-005', 'title': '关键支座信息缺失：先澄清再分析', 'category': 'decision',
                  'documents': initial_documents(e, missing_support=True),
                  'turns': [{'instruction': '审查资料是否足以计算；若有必要缺项，先提出针对性问题。', 'kind': 'clarify',
                             'clarificationFields': ['node:N4-0-0:ux']},
                            {'instruction': '设计方确认 N4-0-0 的全局 ux 固定；其余资料不变。现在分析 SERVICE。',
                             'kind': 'analyze', 'model': e, 'requests': requests(e, [{'kind': 'combination', 'id': 'SERVICE'}])}]})
    f = frame(True)
    f['elements'][0]['rotation_angle'] = 90.
    docs_model = copy.deepcopy(f)
    docs_model['elements'][0]['rotation_angle'] = 0.
    cases.append({'id': 'CH-006', 'title': '同等签发资料转角冲突：不擅自选择', 'category': 'decision',
                  'documents': initial_documents(docs_model, conflict=True),
                  'turns': [{'instruction': '审查资料并判断是否能发布计算结果。若有必要冲突，先请求确认。', 'kind': 'clarify',
                             'clarificationFields': ['member:C0-0-1:rotation_angle']},
                            {'instruction': '设计方确认 C0-0-1 的转角为 90°，其他构件以原清单为准。分析 SERVICE 与 REVERSE。',
                             'kind': 'analyze', 'model': f, 'requests': requests(f, [{'kind': 'combination', 'id': x} for x in ('SERVICE', 'REVERSE')])}]})
    return cases


def build(output):
    if output.exists():
        raise FileExistsError('New edition directory must not exist')
    output.mkdir(parents=True)
    manifest = {'schemaVersion': 1, 'edition': 'challenge-6-v1', 'status': 'candidate-pilot-not-difficulty-calibrated',
                'interfaceTrack': 'documented-common-backend', 'engine': 'OpenSees',
                'candidateRuns': 0, 'externalBlindReviews': 0, 'cases': []}
    for case in definitions():
        cid = case['id']
        folder = output / 'cases' / cid
        public = folder / 'public' / 't1'
        public.mkdir(parents=True)
        for name, text in case['documents'].items():
            write(public / name, text)
        if case.get('raster'):
            raster_geometry(case['turns'][0]['model'], public / 'geometry.png')
        turns, checks = [], []
        for i, turn in enumerate(case['turns'], 1):
            tid = f't{i}'
            target = folder / 'public' / tid
            target.mkdir(parents=True, exist_ok=True)
            requests_public = [{k: v for k, v in q.items() if k not in ('value', 'tolerance')} for q in turn.get('requests', [])]
            write(target / 'task.json', {'caseId': cid, 'turnId': tid, 'instruction': turn['instruction'],
                                        'requests': requests_public})
            if i == 1:
                write(target / 'documents.json', sorted(case['documents']) + (['geometry.png'] if case.get('raster') else []))
            hidden = {k: v for k, v in turn.items() if k != 'instruction'}
            hidden['id'] = tid
            if turn['kind'] != 'clarify':
                model, qs = turn['model'], turn['requests']
                native_quantities = []
                selections = {json.dumps(q['selection'], sort_keys=True): q['selection'] for q in qs}
                for selection in selections.values():
                    selected = [q for q in qs if q['selection'] == selection]
                    factors = selection_factors(model, selection)
                    locations = [q['location'] for q in selected]
                    matrix, matrix_checks = matrix_solve(model, factors, locations)
                    native, native_checks, raw = native_solve(model, factors, locations)
                    quantities = []
                    for q in selected:
                        actual = convert_value(native(q['location'], q['component']), quantity_unit(q['component']), q['unit'])
                        independent = convert_value(matrix(q['location'], q['component']), quantity_unit(q['component']), q['unit'])
                        limit = q['tolerance']['absolute'] + q['tolerance']['relative']*abs(actual)
                        if abs(actual-independent) > limit:
                            raise ValueError(f'{cid}/{tid}/{q["id"]}: native/matrix disagreement')
                        quantities.append({**q, 'value': actual})
                    native_quantities += quantities
                    label = selection['kind'] + '-' + selection['id']
                    write(folder / 'private' / 'native' / f'{tid}-{label}.json', raw)
                    checks.append({'turn': tid, 'selection': selection, 'quantities': len(quantities),
                                   'matrix': matrix_checks, 'native': native_checks})
                hidden['requests'] = native_quantities
            write(folder / 'private' / f'{tid}.json', hidden)
            turns.append({'id': tid, 'public': f'cases/{cid}/public/{tid}', 'private': f'cases/{cid}/private/{tid}.json'})
        write(folder / 'private' / 'reference-checks.json', checks)
        manifest['cases'].append({'id': cid, 'title': case['title'], 'category': case['category'], 'turns': turns})
        print(json.dumps({'case': cid, 'turns': len(turns), 'nativeRuns': len(checks)}), flush=True)
    # Hash every authored public and private byte. The manifest is not a model input.
    manifest['files'] = [{'path': p.relative_to(output).as_posix(), 'sha256': sha(p), 'bytes': p.stat().st_size}
                         for p in sorted(output.rglob('*')) if p.is_file()]
    write(output / 'manifest.json', manifest)
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = build(args.output)
    print(json.dumps({'cases': len(result['cases']), 'turns': sum(len(c['turns']) for c in result['cases']),
                      'files': len(result['files']), 'candidateRuns': 0}))
