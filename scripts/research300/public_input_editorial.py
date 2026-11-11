#!/usr/bin/env python3
"""Deterministic public-only MM concise edition and separate editorial inventory.

The builder sees only original public instructions/attachments. The inventory
alone reads sourcePlan's intended-skill description. Frozen corpus bytes never
change. Table decoders check complete facts, including absence versus null.
"""
from __future__ import annotations

import argparse
import collections
import copy
import csv
import hashlib
import html
import json
from pathlib import Path
import re
import struct
import sys
import xml.etree.ElementTree as ET

EDITION = 'concise-v1'
EDITION_REL = Path('corpora/research-300/public-inputs') / EDITION
INVENTORY_REL = Path('docs/implementation/reviews/mm-inputs-20261016')
JSON_KW = dict(ensure_ascii=False, separators=(',', ':'))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def json_text(data):
    return json.dumps(data, ensure_ascii=False, indent=2) + '\n'


def scalar(value):
    if isinstance(value, str):
        # Ordinary labels remain readable; quote strings that look like JSON or
        # contain escaping/formatting syntax so the inverse remains unambiguous.
        try:
            json.loads(value)
            looks_json = True
        except (ValueError, TypeError):
            looks_json = False
        if looks_json or value != value.strip() or any(c in value for c in '\n\r\\"') or value == '—' or not value:
            value = json.dumps(value, **JSON_KW)
    else:
        value = json.dumps(value, **JSON_KW)
    return value.replace('&', '&amp;').replace('|', '&#124;').replace('<', '&lt;').replace('>', '&gt;')


def unscalar(value):
    value = html.unescape(value.strip())
    try:
        return json.loads(value)
    except ValueError:
        return value


def table(headers, rows):
    return '\n'.join(['|' + '|'.join(headers) + '|', '|' + '|'.join('---' for _ in headers) + '|'] +
                     ['|' + '|'.join(row) + '|' for row in rows])


def path_part(value):
    return str(value).replace('~', '~0').replace('/', '~1')


def unpath(value):
    return value.replace('~1', '/').replace('~0', '~')


def flatten(record, prefix=''):
    result = {}
    for key, value in record.items():
        label = prefix + path_part(key)
        if isinstance(value, dict) and value:
            result.update(flatten(value, label + '/'))
        else:
            result[label] = value
    return result


def unflatten(record):
    result = {}
    for key, value in record.items():
        cursor = result
        parts = [unpath(p) for p in key.split('/')]
        for part in parts[:-1]:
            cursor = cursor.setdefault(part, {})
        cursor[parts[-1]] = value
    return result


LABELS = {
    'units': ('单位', 'Units'), 'materials': ('材料', 'Materials'),
    'sections': ('截面', 'Sections'), 'analysis_control': ('分析设置', 'Analysis settings'),
    'coordinate_system': ('坐标', 'Coordinates'), 'localAxes': ('局部轴', 'Local axes'),
    'boundaryConditions': ('约束', 'Restraints'), 'dxfMapping': ('DXF映射', 'DXF mapping'),
    'sourceCoordinateMapping': ('源坐标映射', 'Source coordinate mapping'),
    'loads': ('荷载', 'Loads'), 'load_cases': ('工况', 'Load cases'),
    'load_combinations': ('组合', 'Combinations'), 'floorAreaLoads': ('楼面荷载', 'Floor loads'),
    'assignments': ('构件分配', 'Member assignments'), 'properties': ('属性与约定', 'Properties and conventions'),
}


def heading(path, locale, default='Parameters'):
    key = path.rsplit('/', 1)[-1] if path else default
    label = LABELS.get(key, (key, key))[locale != 'zh']
    return f'## {label} [{path or "/"}]'


def render_structured(data, locale='en', source_name='appendix.json'):
    """Render nested public JSON as tables, grouping identical adjacent IDs.

    Visible heading paths are the original public field names, not hidden
    metadata. An em dash denotes an absent field; null remains explicit.
    """
    title = source_name.removesuffix('.json')
    note = ('空格“—”表示未给定字段；null 保持原义；同一行的 ID 逐个适用，顺序不变。'
            if locale == 'zh' else
            '— means an absent field; null stays explicit. Grouped IDs each receive the row values in the listed order.')
    blocks = [f'# {LABELS.get(title, (title, title))[locale != "zh"]}']
    if title == 'properties':
        blocks.append(note)

    def emit(value, path=''):
        if isinstance(value, dict):
            simple = [(k, v) for k, v in value.items()
                      if not isinstance(v, dict) and not (isinstance(v, list) and any(isinstance(x, dict) for x in v))]
            if simple or not value:
                blocks.extend([heading(path, locale, title), table(['field', 'value'], [[scalar(k), scalar(v)] for k, v in simple])])
            for key, child in value.items():
                if isinstance(child, dict) or isinstance(child, list) and any(isinstance(x, dict) for x in child):
                    emit(child, path + '/' + path_part(key))
        elif isinstance(value, list) and all(isinstance(x, dict) for x in value):
            # Lists containing nested record arrays (load cases) receive separate
            # case tables so their loads never become raw JSON blobs.
            if any(any(isinstance(x, list) and any(isinstance(y, dict) for y in x) for x in item.values()) for item in value):
                blocks.extend([heading(path, locale, title), table(['index'], [[str(i)] for i in range(len(value))])])
                for i, item in enumerate(value):
                    emit(item, path + '/' + str(i))
                return
            records = [flatten(item) for item in value]
            columns = list(dict.fromkeys(key for record in records for key in record))
            if not columns:
                columns = ['@empty']
            group = bool(records) and all(isinstance(r.get('id'), str) and re.fullmatch(r'[\w.+:-]+', r['id']) for r in records)
            rows = []
            for record in records:
                if group and rows and {k: v for k, v in rows[-1][0].items() if k != 'id'} == {k: v for k, v in record.items() if k != 'id'}:
                    rows[-1][1].append(record['id'])
                else:
                    rows.append((record, [record['id']] if group else []))
            output = []
            for record, ids in rows:
                output.append([', '.join(ids) if group and key == 'id' else scalar(record[key]) if key in record else '—' for key in columns])
            headers = ['id (each)' if group and key == 'id' else key for key in columns]
            blocks.extend([heading(path, locale, title), table(headers, output)])
        else:
            blocks.extend([heading(path, locale, title), table(['value'], [[scalar(value)]])])

    emit(data)
    return '\n\n'.join(blocks) + '\n'


def parse_structured(text):
    """Decode the public table representation into its complete original JSON."""
    pieces = re.split(r'^## .*? \[(.*?)\]\s*$', text, flags=re.M)
    entries = {}
    for i in range(1, len(pieces), 2):
        path = pieces[i]
        section = pieces[i + 1].split('\n## ', 1)[0]
        rows = [line.strip()[1:-1].split('|') for line in section.splitlines() if line.strip().startswith('|')]
        if len(rows) < 2:
            raise ValueError(f'Missing table at {path}')
        headers = [c.strip() for c in rows[0]]
        cells = [[c.strip() for c in row] for row in rows[2:]]
        if any(len(row) != len(headers) for row in cells):
            raise ValueError(f'Table width differs at {path}')
        if headers == ['field', 'value']:
            value = {unscalar(row[0]): unscalar(row[1]) for row in cells}
        elif headers == ['index']:
            if [int(row[0]) for row in cells] != list(range(len(cells))):
                raise ValueError('Nonsequential array indexes')
            value = [{} for _ in cells]
        elif headers == ['value']:
            value = unscalar(cells[0][0])
        else:
            value = []
            for row in cells:
                record = {('id' if h == 'id (each)' else h): unscalar(c) for h, c in zip(headers, row) if c != '—' and h != '@empty'}
                ids = row[headers.index('id (each)')].split(', ') if 'id (each)' in headers else [None]
                for identity in ids:
                    item = copy.deepcopy(record)
                    if identity is not None:
                        item['id'] = html.unescape(identity)
                    value.append(unflatten(item))
        entries[path if path != '/' else ''] = value
    result = entries.get('', {})
    for path, value in entries.items():
        if not path:
            continue
        parts = [unpath(x) for x in path.lstrip('/').split('/')]
        cursor = result
        for part in parts[:-1]:
            if isinstance(cursor, list):
                cursor = cursor[int(part)]
            else:
                cursor = cursor.setdefault(part, {})
        if isinstance(cursor, list):
            cursor[int(parts[-1])] = value
        else:
            cursor[parts[-1]] = value
    return result


# Every replacement below lists its source clause explicitly and has an inverse.
# This is a public fact-preservation map, not a heuristic sentence summarizer.
TEXT_REWRITES = {
    '分析与属性附录': '# 属性与约定',
    'Analysis and property appendix': '# Properties and conventions',
    '材料': '## 材料',
    '截面（附录采用实心矩形；局部 y 宽 B、局部 z 高 H）':
        '## 截面：实心矩形；B为局部y宽，H为局部z高',
    'Sections (solid rectangular appendix; local y width B and local z depth H)':
        '## Sections: solid rectangles; B: local-y width, H: local-z depth',
    '空间几何由各正交视图共同确定。纯轴力杆节点转动为非作用自由度并约束，不代表抗弯支承。局部1由起点到终点；局部2=归一化(参考向量叉乘局部1)；局部3=局部1叉乘局部2。竖杆参考向量为全局+X，其余为全局+Z。':
        '空间几何按正交视图；纯轴杆节点转动约束为非作用处理，非抗弯支承。局部1:起点→终点；局部2=归一化(参考向量叉乘1)；局部3=1叉乘2。参考向量:竖杆全局+X，其余全局+Z。',
    'Materials': '## Materials',
    '全局 XYZ，Z 向上。单位：m、kN、kN*m；E/G 为 MPa，密度 kg/m3，A 为 m2，Iy/Iz/J 为 m4；位移 m，转角 rad。':
        '全局 XYZ，Z 向上。单位：m/kN/kN*m；E/G:MPa，密度:kg/m3，A:m2，Iy/Iz/J:m4；位移:m，转角:rad。',
    'XZ 平面，非作用自由度 uy/rx/rz 约束。局部 1 轴由图示起点指向终点，局部 2 为全局 +Y，局部 3=局部1叉乘局部2。Ry/My 按全局 +Y 右手定则。':
        'XZ 平面；约束非作用 uy/rx/rz。局部1:图示起点→终点，局部2:全局+Y，局部3=1叉乘2；Ry/My:全局+Y右手。',
    'Global XYZ, Z up. Units: m, kN, kN*m; E/G MPa, density kg/m3, A m2, Iy/Iz/J m4. Displacements m, rotations rad.':
        'Global XYZ, Z up. Units: m/kN/kN*m; E/G:MPa; density:kg/m3; A:m2; Iy/Iz/J:m4; displacement:m; rotation:rad.',
    '一阶线弹性静力；自重关闭。不开启 P-delta、刚性楼板、刚域、刚度折减或默认组合。':
        '一阶线弹性静力；自重、P-delta、刚性楼板、刚域、刚度折减、默认组合均关闭。',
    'First-order linear elastic static analysis; self-weight OFF. No P-delta, rigid diaphragm, rigid offsets, stiffness reductions, or automatic combinations.':
        'First-order linear elastic static; self-weight, P-delta, rigid diaphragm, rigid offsets, stiffness reductions and automatic combinations OFF.',
    '荷载分量按全局 XYZ 轴：fx/fy/fz 为集中力，单位 kN；mx/my/mz 为节点力矩，单位 kN*m（右手定则）；wx/wy/wz 为线分布力，单位 kN/m，按杆件实际长度计，不按投影长度计。z 分量为负表示沿全局 -Z。':
        '全局 XYZ 荷载：fx/fy/fz 集中力 kN；mx/my/mz 节点力矩 kN*m（右手）；wx/wy/wz 线载 kN/m，按实际杆长而非投影长。负 z 沿全局 -Z。',
    'Load components use global XYZ axes: fx/fy/fz are concentrated forces in kN; mx/my/mz are nodal moments in kN*m (right-hand rule); wx/wy/wz are distributed forces in kN/m per actual member length, not projected length. A negative z component acts along global -Z.':
        'Global XYZ loads: fx/fy/fz concentrated forces [kN]; mx/my/mz nodal moments [kN*m, right-hand]; wx/wy/wz line loads [kN/m of actual member length, not projected length]. Negative z acts along global -Z.',
    'XZ plane. Inactive uy/rx/rz are restrained. Local 1 runs from the labelled start to end; local 2 is global +Y; local 3 = local 1 cross local 2. Positive Ry/My follows the right-hand rule about global +Y.':
        'XZ plane; restrain inactive uy/rx/rz. Local 1: labelled start→end; local 2: global +Y; local 3=1 cross 2. Positive Ry/My: right-hand about global +Y.',
    'Beam/column joints are rigid and continuous unless a physical support is shown; observation nodes do not create hinges.':
        'Beam/column joints: rigid and continuous unless a physical support is shown; observation nodes create no hinges.',
    'Report section forces using local axes; support forces/moments use global axes. Preserve signs, selected cases/combinations and section sides.':
        'Section forces: local axes; support forces/moments: global axes. Keep signs, cases/combinations and section sides.',
    'DXF units are metres. DXF X maps to global X; DXF Y maps to global Z; global Y=0. STRUCTURE contains physical centre lines and joint dots. SUPPORTS, LOADS and DIMENSIONS are annotation layers.':
        'DXF: m; X→global X, Y→global Z, global Y=0. STRUCTURE: physical centre lines/joint dots. SUPPORTS, LOADS, DIMENSIONS: annotations.',
}
TEXT_INVERSE = {v: k for k, v in TEXT_REWRITES.items()}


def normalized_lines(source):
    return [' '.join(line.split()) for line in source.splitlines() if line.strip()]


def record_line(line):
    match = re.fullmatch(r'([^:：]+): (.+)', line)
    if not match:
        return None
    key, body = match.groups()
    if re.fullmatch(r'[A-Za-z][\w.-]*', key) and re.fullmatch(r'[A-Za-z][\w.-]* / [A-Za-z][\w.-]*', body):
        material, section = body.split(' / ')
        return 'assignment', key, {'material': material, 'section': section}
    if re.fullmatch(r'[A-Za-z][\w.-]*', key) and re.fullmatch(r'[\w]+=[+\-0-9.eE]+(?:, [\w]+=[+\-0-9.eE]+)*', body):
        return 'properties', key, dict(pair.split('=') for pair in body.split(', '))
    return None


def render_text(source, locale='en', source_name='appendix.txt'):
    lines = normalized_lines(source)
    blocks, facts = [], []
    i = 0
    while i < len(lines):
        line = lines[i]
        record = record_line(line)
        if record:
            kind, identity, values = record
            columns = list(values)
            group = []
            while i < len(lines):
                item = record_line(lines[i])
                if not item or item[0] != kind or list(item[2]) != columns:
                    break
                group.append(item)
                facts.append({'source': lines[i], 'treatment': 'explicit-ID table', 'fields': list(item[2])})
                i += 1
            rows = []
            for _, identity, values in group:
                if rows and rows[-1][1] == values:
                    rows[-1][0].append(identity)
                else:
                    rows.append(([identity], values))
            blocks.append(table(['ID'] + columns, [[', '.join(ids)] + [values[k] for k in columns] for ids, values in rows]))
            continue
        edited = TEXT_REWRITES.get(line, line)
        blocks.append(edited)
        facts.append({'source': line, 'edited': edited, 'treatment': 'clause-preserving wording' if edited != line else 'unchanged public clause'})
        i += 1
    return '\n\n'.join(blocks) + '\n', facts


def parse_text(text):
    """Invert known wording changes and compact tables, preserving conflicts."""
    lines = text.splitlines()
    result = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if line.startswith('|') and line.split('|')[1].strip() == 'ID':
            headers = [x.strip() for x in line[1:-1].split('|')][1:]
            i += 2
            while i < len(lines) and lines[i].strip().startswith('|'):
                cells = [x.strip() for x in lines[i].strip()[1:-1].split('|')]
                for identity in cells[0].split(', '):
                    body = ' / '.join(cells[1:]) if headers == ['material', 'section'] else ', '.join(f'{k}={v}' for k, v in zip(headers, cells[1:]))
                    result.append(identity + ': ' + body)
                i += 1
            continue
        result.append(TEXT_INVERSE.get(line, line))
        i += 1
    return result


MAIN_ZH = ('依据{inputs}用 {engine} 建模求解，保留连通、支座、荷载位置、属性组及编号；必要缺项/冲突先澄清。'
           '按附表报告带符号、单位和工况/组合的结果，并附数值一致的模型/结果图。')
MAIN_EN = ('Reconstruct from {inputs}. Analyze in {engine}, preserving connectivity, supports, load positions and property groups. '
           'Clarify essential gaps/conflicts first. Follow the appendix conventions; report signed values with units, '
           'cases/combinations and section sides. Include consistent model/result figures showing supports, loads and IDs.')

COMMON_NOTES_ZH = ('一阶线弹性；保存自重关闭、无刚性楼板设置；采用明示完整材料/截面刚度；全局右手坐标 Z 向上；'
                   '保留真实分布荷载及位置。保存输入→模型编号映射、引擎版本/设置、本次执行日志、原始结果表与绘图数据。')
COMMON_NOTES_EN = ('First-order linear elasticity; save self-weight OFF and no-rigid-diaphragm settings. '
                   'Use explicit full material/section stiffness, right-handed global axes (Z up), actual load positions and distributed loads. '
                   'Keep input-to-model IDs, engine/version/settings, current run log, raw result tables and figure data.')

CAD_NOTES_ZH = ('input.dxf：S-* 为结构线/编号；筛除 A-* 墙线、柱轮廓、设备干扰。按 properties.md 的 dxfMapping '
                '合并正投影视图；支承按 boundaryConditions 与 CAD 标注；编号对应 assignments.md/loads.md。'
                '截面详图仅给属性/转角，不给结构几何；局部方向按 properties.md 规定取 DXF LINE 起点→终点。')
CAD_NOTES_EN = ('input.dxf: use S-* structural lines/labels; filter A-* wall, column-footprint and equipment distractors. '
                'Reconcile orthographic views with properties.md dxfMapping; read supports from boundaryConditions and CAD annotations; '
                'match labels in assignments.md/loads.md. Section-detail images give section properties/roll only; no structural geometry image '
                'is supplied. Local direction follows DXF LINE start-to-end as specified in properties.md.')


def split_instruction(instruction):
    markers = ['\n\n要求输出：\n', '\n\nRequested outputs:\n', '\n\n逐项输出以下带符号、单位和荷载选择的结果：\n', '\n\nReport all of the following for each stated selection, with signs and units:\n']
    for marker in markers:
        if marker in instruction:
            prefix, rest = instruction.split(marker, 1)
            lines = rest.strip().splitlines()
            outputs, tail = [], []
            for line in lines:
                if tail or line.startswith(('给出与数值表一致', 'Provide a model/result figure', '附带编号模型图', 'Provide labelled model')):
                    tail.append(line)
                elif line.strip():
                    outputs.append(line.removeprefix('- ').strip())
            return prefix, outputs, '\n'.join(tail).strip()
    return instruction.strip(), [], ''


# Only these exact public boilerplate clauses are represented by the concise
# main text/common notes. Any additional tail clause remains visible verbatim;
# it may carry a case-specific first-turn action or physical exception.
COMMON_TAILS = (
    '给出与数值表一致的模型/结果图，包含支座、荷载、ID 对应及结果正负号与单位。',
    'Provide a model/result figure consistent with the numerical table, including support/load/ID mapping and signed result units.',
    '附带编号模型图及与数值一致的结果图，保存图纸编号到计算模型的映射、引擎版本及设置、当前执行日志、原始结果表和绘图数据。必要信息缺失时先针对缺项询问。',
    'Provide labelled model and result figures consistent with the numerical values. Preserve the input-to-model ID mapping, engine version/settings, current execution log, original result tables and figure data. If an essential datum is missing, ask specifically for it before analysis.',
)


def concise_instruction(instruction, locale, engine, followup=False, attachments=()):
    prefix, outputs, tail = split_instruction(instruction)
    if followup or not outputs:
        # Unknown prompt shapes retain their public clauses rather than guessing
        # what can be removed. The five authored followups are already concise.
        short = {
            '补图明确中点力为全局 Z 向 -15 kN。请完成所要求的分析。':
                '补图确认中点力：全局 Z 向 -15 kN。完成前述分析和输出。',
            '确认第二跨采用 B2。请按修正附录与补图完成所要求的分析。':
                '第二跨确认用 B2；依修正附录和补图完成前述分析及输出。',
            'The supplement provides ridge height 2.5 m and all roof elevations. Complete the requested analysis.':
                'Use the supplemental ridge height 2.5 m and all roof elevations to complete the OpenSees analysis and requested outputs.',
            'The completed drawing confirms that both column bases are fixed. Use the newly supplied drawing to analyze case D and report the requested displacements and right-base moment.':
                'Both column bases are fixed, as confirmed in the new drawing. Analyze case D in OpenSees; report the requested displacements and right-base moment.',
            'The right bay is 0.5 m above the left bay at each storey. The complete elevation is attached. Analyze and report all requested outputs.':
                'At each storey the right bay is 0.5 m above the left bay. Use the complete elevation for the OpenSees analysis and all requested outputs.',
        }
        return short.get(instruction.strip(), instruction.strip()), '', []
    known = prefix.startswith(('请依据所附图纸', 'Reconstruct the model')) or any(marker in prefix for marker in ['\n\n从所附尺寸图', '\n\nReconstruct the structure', '\n\n从建筑图 input.dxf', '\n\nReconstruct geometry and connectivity from the architectural input.dxf'])
    if not known:
        return instruction.strip(), '', outputs
    title = prefix.split('\n\n')[0] if '\n\n' in prefix else ''
    cad = any(name.endswith('.dxf') for name in attachments)
    geometry_images = any(name.endswith(('.png', '.svg')) and 'section-detail' not in name for name in attachments)
    if locale == 'zh':
        inputs = '所附图纸和属性表' if geometry_images else 'input.dxf和附表' if cad else '所附输入和附表'
        if cad and geometry_images:
            inputs = '所附图纸、input.dxf和附表'
    else:
        inputs = 'drawings and property/load tables' if geometry_images else 'input.dxf and its appendices' if cad else 'the supplied inputs and appendices'
        if cad and geometry_images:
            inputs = 'the supplied drawings, input.dxf and appendices'
    main = (MAIN_ZH if locale == 'zh' else MAIN_EN).format(engine=engine, inputs=inputs)
    if title:
        main = title + '\n\n' + main
    extra_tail = tail
    for common_tail in COMMON_TAILS:
        if tail == common_tail or tail.startswith(common_tail + '\n'):
            extra_tail = tail[len(common_tail):].strip()
            break
    if extra_tail:
        main += '\n\n' + extra_tail
    clean_outputs = [re.sub(r' \[[^\[\]]+\]$', '', output) for output in outputs]
    output_table = table(['输出要求' if locale == 'zh' else 'Requested output'], [[scalar(output)] for output in clean_outputs])
    notes = ''
    if title:
        notes = COMMON_NOTES_ZH if locale == 'zh' else COMMON_NOTES_EN
        if 'architectural input.dxf' in prefix or '从建筑图 input.dxf' in prefix:
            notes = (CAD_NOTES_ZH if locale == 'zh' else CAD_NOTES_EN) + '\n\n' + notes
        else:
            notes = ('几何和支承从图纸读取，构件编号对应属性、分配及荷载附表。' if locale == 'zh' else
                     'Read geometry and supports from the drawings; match member labels in the property, assignment and load tables.') + '\n\n' + notes
    return main + '\n\n' + output_table, notes, outputs


def build_case(contract, manifest_row, public_files):
    """Pure builder. Private author/evaluator fields are never consulted."""
    locale = contract.get('locale', 'zh' if contract.get('language') == '中文' else 'en')
    files, turns, edits = {}, [], []
    for index, turn in enumerate(contract['turns']):
        instruction, notes, outputs = concise_instruction(turn['instruction'], locale, contract['plannedEngine'], index > 0, turn.get('attachments', []))
        descriptors = []
        for name in turn.get('attachments', []):
            raw = public_files[name]
            suffix = Path(name).suffix.lower()
            if suffix in ('.json', '.txt'):
                target = str(Path(name).with_suffix('.md'))
                source = raw.decode('utf-8')
                if suffix == '.json':
                    data = json.loads(source)
                    edited = render_structured(data, locale, name)
                    if parse_structured(edited) != data:
                        raise ValueError(f'{contract["id"]}/{name}: structured facts changed')
                    fact_audit = {'kind': 'complete-JSON-roundtrip', 'equal': True}
                else:
                    edited, clauses = render_text(source, locale, name)
                    if parse_text(edited) != normalized_lines(source):
                        raise ValueError(f'{contract["id"]}/{name}: public TXT clause changed')
                    fact_audit = {'kind': 'complete-TXT-clause-roundtrip', 'equal': True, 'clauses': clauses}
                if target in files and files[target] != edited:
                    raise ValueError('Two source appendices collide')
                files[target] = edited
                descriptors.append({'name': target, 'source': 'edition', 'path': target, 'sha256': digest(edited.encode())})
                instruction = instruction.replace(name, target)
                edits.append({'turn': turn['id'], 'original': name, 'edition': target,
                              'beforeCharacters': len(source), 'afterCharacters': len(edited), 'verification': fact_audit})
            else:
                descriptors.append({'name': name, 'source': 'frozen', 'path': name, 'sha256': digest(raw)})
        if notes:
            # Consolidate prompt conventions into the existing property packet;
            # the inverse table decoder ignores this independently audited prose.
            name = next((a['path'] for a in descriptors if a['source'] == 'edition' and Path(a['path']).stem == 'properties'), None)
            if name is None:
                name = f'analysis-notes-{turn["id"]}.md'
                files[name] = ''
                descriptors.append({'name': name, 'source': 'edition', 'path': name, 'sha256': ''})
            note_heading = '\n## 分析与报告\n\n' if locale == 'zh' else '\n## Analysis and reporting\n\n'
            files[name] += note_heading + notes + '\n'
            for descriptor in descriptors:
                if descriptor['source'] == 'edition' and descriptor['path'] == name:
                    descriptor['sha256'] = digest(files[name].encode())
            edits.append({'turn': turn['id'], 'original': 'turn.instruction/common-clauses', 'edition': name,
                          'beforeCharacters': len(split_instruction(turn['instruction'])[0]) + len(split_instruction(turn['instruction'])[2]),
                          'afterCharacters': len(note_heading + notes + '\n'),
                          'verification': {'kind': 'explicit-prompt-clause-map', 'source': turn['instruction'],
                                           'preservedFacts': ['drawing/CAD/table responsibilities', 'specified engine', 'first-order linear elasticity',
                                                              'self-weight OFF', 'no rigid diaphragm', 'explicit stiffness', 'right-handed Z-up axes',
                                                              'actual load positions and distributions', 'ID mapping', 'engine/version/settings',
                                                              'current log', 'raw result tables', 'figure data', 'clarify missing essentials']}})
        turns.append({'id': turn['id'], 'instruction': instruction, 'attachments': descriptors})
    bundle = {'schemaVersion': 1, 'edition': EDITION, 'caseId': contract['id'],
              'baseSourceHash': manifest_row['sourceHash'], 'turns': turns}
    return bundle, files, edits


def read_case(root, case_id):
    corpus = root / 'corpora/research-300'
    manifest = json.loads((corpus / 'manifest.json').read_text())
    row = next((r for r in manifest['cases'] if r['id'] == case_id), None)
    if not row or not row.get('sourceHash') or not row.get('publicSha256'):
        raise ValueError(f'{case_id}: missing frozen manifest binding')
    folder = corpus / 'cases' / case_id
    contract = json.loads((folder / 'contract.json').read_text())
    names = list(dict.fromkeys(name for turn in contract['turns'] for name in turn.get('attachments', [])))
    files = {name: (folder / name).read_bytes() for name in names}
    return contract, row, files


def check_case(root, case_id):
    """Read-only reconstruction, independent of edition hashes and prose."""
    contract, row, public_files = read_case(root, case_id)
    expected, files, _ = build_case(contract, row, public_files)
    folder = root / EDITION_REL / case_id
    errors = []
    try:
        actual = json.loads((folder / 'input.json').read_text())
        if actual != expected:
            errors.append(f'{case_id}/input.json: differs from deterministic public-source edition')
    except (OSError, ValueError) as exc:
        errors.append(f'{case_id}/input.json: {exc}')
    for name, content in files.items():
        try:
            if (folder / name).read_bytes() != content.encode():
                errors.append(f'{case_id}/{name}: public facts or deterministic formatting differ')
        except OSError as exc:
            errors.append(f'{case_id}/{name}: {exc}')
    return errors


def visual_inventory(public_files):
    result = []
    for name, raw in public_files.items():
        suffix = Path(name).suffix.lower()
        if suffix == '.svg':
            element = ET.fromstring(raw)
            labels = [''.join(node.itertext()) for node in element.iter() if node.tag.rsplit('}', 1)[-1] == 'text']
            sizes = [float(node.attrib['font-size']) for node in element.iter() if node.attrib.get('font-size', '').replace('.', '').isdigit()]
            result.append({'name': name, 'width': element.attrib.get('width'), 'height': element.attrib.get('height'),
                           'labelCount': len(labels), 'minimumFontSize': min(sizes) if sizes else None,
                           'annotationSample': labels[:3]})
        elif suffix == '.png' and raw[:8] == b'\x89PNG\r\n\x1a\n':
            width, height = struct.unpack('>II', raw[16:24])
            result.append({'name': name, 'width': width, 'height': height})
        elif suffix == '.dxf':
            result.append({'name': name, 'bytes': len(raw), 'kind': 'CAD; no visual redraw in this edition'})
    return result


def audit_case(contract, before, bundle, files, edits):
    # Deliberately separate from build_case: these author-skill descriptions are
    # editorial reviewer notes and are NEVER included in agent-visible inputs.
    plan = contract.get('sourcePlan', {})
    source = plan.get('sourceRequirements', plan)
    skill = source.get('task.modelingFocus', '')
    modality = source.get('task.inputForm', '')
    category = plan.get('subcategory') or ('建筑DXF' if any(n.endswith('.dxf') for n in before) else
               '多视图重建' if '正交' in modality else '图表联合' if '荷载表' in modality else
               '工程标注图' if '详图' in modality else '单图重建')
    visuals = visual_inventory(before)
    svg = [v for v in visuals if v['name'].endswith('.svg')]
    pairs = [v['name'].removesuffix('.svg') for v in svg if v['name'].removesuffix('.svg') + '.png' in before]
    outputs = [o for turn in contract['turns'] for o in split_instruction(turn['instruction'])[1]]
    text_files = [name for name in before if Path(name).suffix in ('.txt', '.json')]
    prompt_before = sum(len(t['instruction']) for t in contract['turns'])
    prompt_after = sum(len(t['instruction']) for t in bundle['turns'])
    appendix_before = sum(len(before[name].decode()) for name in text_files)
    appendix_after = sum(len(value) for value in files.values())
    duplicates = []
    for name in text_files:
        if name.endswith('.txt'):
            assignments = collections.defaultdict(list)
            for line in normalized_lines(before[name].decode()):
                item = record_line(line)
                if item and item[0] == 'assignment':
                    assignments[item[1]].append(item[2])
            for identity, records in assignments.items():
                if len(records) > 1:
                    duplicates.append(f'{name}: {identity} appears {len(records)} times: {records}; retained until later confirmation')
    if pairs:
        duplicates.append(f'{len(pairs)} PNG/SVG pairs retained: ' + ', '.join(pairs))
    if len(contract['turns']) > 1:
        duplicates.append('Delayed public clarification retained verbatim in substance: ' + ' / '.join(t['instruction'] for t in contract['turns'][1:]))
    if not duplicates:
        duplicates.append('Drawing/property scope retained; no wording conflict detected by clause/record checks. Independent visual review pending.')
    drawing_work = f'{len(svg)} SVG views, {sum(v["labelCount"] for v in svg)} text labels; retain all current files. '
    drawing_work += 'Next drawing review must check ' + skill
    drawing_work += ' PNG/SVG modality choice and visual legibility remain pending step 4; no blind reconstruction was performed.'
    necessary = [f'{name} → {Path(name).with_suffix(".md")}' for name in text_files]
    necessary += ['Requested signed outputs: ' + ' / '.join(outputs)]
    return {
        'caseId': contract['id'], 'category': category, 'engine': contract['plannedEngine'],
        'language': contract.get('language', contract.get('locale')), 'turns': len(contract['turns']),
        'testedSkill': skill, 'factsRequiringVisualInput': {'responsibility': modality, 'caseSpecificReading': skill, 'views': visuals},
        'necessaryText': necessary, 'duplicatedOrAmbiguousContent': duplicates,
        'performedEdits': [f'{e["original"]} → {e["edition"]}: {e["verification"]["kind"]}' for e in edits] +
                          ['Concise modality-specific goal/engine/output prompts; numerical requests retained; common notes consolidated into the property packet at the original turn'],
        'remainingDrawingWork': drawing_work,
        'lengths': {'promptBefore': prompt_before, 'promptAfter': prompt_after,
                    'appendixBefore': appendix_before, 'appendixAfter': appendix_after,
                    'totalBefore': prompt_before + appendix_before, 'totalAfter': prompt_after + appendix_after},
        'turnRelease': [{'id': t['id'], 'originalAttachments': t.get('attachments', []),
                         'editionAttachments': [a['name'] for a in bundle['turns'][i]['attachments']]} for i, t in enumerate(contract['turns'])],
        'verification': {'structuredFacts': 'exact full-object decode comparison passed',
                         'textFacts': 'every source clause/record recovered; explicit wording inverse checked',
                         'frozenVisuals': 'SHA-256 unchanged; release turns unchanged',
                         'blindReview': 'pending', 'physicalAcceptance': 'unchanged', 'agentRun': 'not-run'},
        'textFactPreservation': edits,
    }


def write_inventory(root, rows):
    folder = root / INVENTORY_REL
    folder.mkdir(parents=True, exist_ok=True)
    before = sum(r['lengths']['totalBefore'] for r in rows)
    after = sum(r['lengths']['totalAfter'] for r in rows)
    summary = {'cases': len(rows), 'turns': sum(r['turns'] for r in rows), 'charactersBefore': before, 'charactersAfter': after,
               'reductionPercent': round((before - after) / before * 100, 2), 'blindReview': 'pending',
               'scope': 'Editorial inventory and public text edition only; drawings, modality and physical acceptance unchanged'}
    (folder / 'inventory.json').write_text(json_text({'schemaVersion': 1, 'edition': EDITION, 'summary': summary, 'cases': rows}))
    columns = ['caseId', 'category', 'engine', 'language', 'turns', 'testedSkill', 'factsRequiringVisualInput', 'necessaryText',
               'duplicatedOrAmbiguousContent', 'performedEdits', 'remainingDrawingWork', 'lengths', 'verification']
    with (folder / 'inventory.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json.dumps(row[key], ensure_ascii=False) if isinstance(row[key], (dict, list)) else row[key] for key in columns})
    lines = ['# MM100 public-input editorial inventory', '',
             f'{len(rows)} cases / {summary["turns"]} turns. Public prompt plus text appendix characters: {before:,} → {after:,} ({summary["reductionPercent"]}% reduction).', '',
             'Scope: individual source/input inventory, concise actual prompt packets and reversible appendix tables. All PNG/SVG/DXF bytes and their release turns remain frozen. This is not an independent blind reconstruction or physical acceptance. Drawing legibility, duplicate modality decisions and future drawings remain pending.', '',
             'The JSON and CSV contain all required audit fields, source-to-edition clause records and individual drawing statistics. Intended skills come from author metadata only in this review; the public edition generator never uses them.', '',
             '| Case | Category / engine / language / turns | Tested skill and visual reading | Necessary text / requested outputs | Duplicate or ambiguous content | Edits | Remaining drawing work | Characters before → after | Verification |',
             '| --- | --- | --- | --- | --- | --- | --- | --- | --- |']
    escape = lambda text: str(text).replace('|', '&#124;').replace('\n', ' ')
    for row in rows:
        length = row['lengths']
        cells = [row['caseId'], f'{row["category"]} / {row["engine"]} / {row["language"]} / {row["turns"]}', row['testedSkill'],
                 '; '.join(row['necessaryText']), '; '.join(row['duplicatedOrAmbiguousContent']), '; '.join(row['performedEdits']),
                 row['remainingDrawingWork'], f'{length["totalBefore"]} → {length["totalAfter"]} (prompts {length["promptBefore"]} → {length["promptAfter"]})',
                 'Public clauses/JSON exact roundtrip; frozen visual hashes; blind review pending']
        lines.append('| ' + ' | '.join(escape(cell) for cell in cells) + ' |')
    (folder / 'inventory.md').write_text('\n'.join(lines) + '\n')
    return summary


def generate(root, case_ids=None, inventory=True):
    root = Path(root)
    source_manifest = json.loads((root / 'corpora/research-300/manifest.json').read_text())
    case_ids = case_ids or sorted(r['id'] for r in source_manifest['cases'] if r['id'].startswith('MM-'))
    edition = root / EDITION_REL
    edition.mkdir(parents=True, exist_ok=True)
    manifest_rows, audit_rows = [], []
    for case_id in case_ids:
        contract, row, public_files = read_case(root, case_id)
        bundle, files, edits = build_case(contract, row, public_files)
        folder = edition / case_id
        folder.mkdir(parents=True, exist_ok=True)
        for obsolete in folder.glob('analysis-notes-*.md'):
            if obsolete.name not in files:
                obsolete.unlink()
        for name, value in files.items():
            target = folder / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(value)
        encoded = json_text(bundle).encode()
        (folder / 'input.json').write_bytes(encoded)
        manifest_rows.append({'id': case_id, 'baseSourceHash': row['sourceHash'], 'basePublicSha256': row['publicSha256'],
                              'path': case_id + '/input.json', 'sha256': digest(encoded)})
        if inventory:
            audit_rows.append(audit_case(contract, public_files, bundle, files, edits))
    (edition / 'manifest.json').write_text(json_text({'schemaVersion': 1, 'edition': EDITION, 'cases': manifest_rows}))
    summary = write_inventory(root, audit_rows) if inventory else {'cases': len(manifest_rows)}
    return summary


def main(argv=None):
    print('This historical public-input CLI has been retired. '
          'Use python3 scripts/research300/public_input_clean.py --check to validate '
          'the current inputs, or python3 scripts/research300/public_input_clean.py '
          'to build them.', file=sys.stderr)
    return 2


if __name__ == '__main__':
    sys.exit(main())
