#!/usr/bin/env python3
"""Build/check current solely from released public instructions and attachments.

MM releases contain one PNG sheet or one annotated original DXF. STD/INT releases
contain one readable Markdown document when new public files are supplied.
Authoring SVGs and correspondence audits are maintenance material, never inputs.
"""
from __future__ import annotations

import argparse
import collections
import copy
import csv
import html
import importlib.util
import io
import json
import math
import os
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('clean_public_visual', HERE / 'public_input_visual.py')
visual = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(visual)
editorial = visual.editorial
digest, json_text = editorial.digest, editorial.json_text
EDITION = 'current'
EDITION_REL = Path('corpora/research-300/public-inputs')

# Reviewed public wording amendment after the first full candidate trial.
# Match the exact released source as well as case/turn, never hidden grading
# fields. Keep the historical source/native identity; the delivered input and
# validator hashes identify this new revision. No future clarification leaks.
INSTRUCTION_CLARIFICATIONS = {
    ('INT-056', 't2', 'Increase the crane load by 20% and give the revised response.'):
        'The crane load is to increase by 20%, but it has not yet been decided '
        'whether this applies to both components or only the vertical component. '
        'Ask me to confirm the scope before updating or analysing the frame.',
}


def read_case(root, case_id):
    """Public reader: no model, reference, response contract or author decisions."""
    contract, row, public = visual.read_case(Path(root), case_id)
    safe = {key: contract[key] for key in ('id', 'locale', 'plannedEngine') if key in contract}
    safe['turns'] = [{key: turn[key] for key in ('id', 'instruction', 'attachments') if key in turn}
                     for turn in contract['turns']]
    return safe, row, public


def clean_text(text):
    # Remove only execution bookkeeping labels, retaining actual native runs,
    # runnable inputs, settings, logs, result mappings and model snapshots.
    text = re.sub(r'(?:current[- ]model hash|current model hash|model hash)\s*,\s*', '', text, flags=re.I)
    text = re.sub(r'\b(?:run[ -]?ID)\s*(?:,\s*|and\s+)?', '', text, flags=re.I)
    text = re.sub(r'(?:当前模型哈希|模型哈希|运行ID)[、，,及]*', '', text, flags=re.I)
    return text.strip()


def drawing_references(text):
    text = clean_text(text)
    return re.sub(r'[A-Za-z0-9_.-]+\.(?:json|txt|md|png|svg|dxf)', 'drawing notes', text)


def public_references(text, bindings):
    # Explicit released filenames also work next to Chinese text; a regex word
    # boundary does not. Unreleased/future filenames are never introduced.
    for source in sorted(bindings, key=len, reverse=True):
        text = text.replace(source, bindings[source])
    return text


def human(key):
    names = {'nodeTable': 'Nodes', 'memberTable': 'Members', 'loadingCases': 'Load cases',
             'linearCombinations': 'Load combinations', 'coordinateConvention': 'Coordinate convention',
             'analysisSettings': 'Analysis settings', 'node': 'Node', 'id': 'ID',
             'geometry': 'Geometry', 'properties': 'Properties', 'loads': 'Loads',
             'output-requests': 'Requested outputs', 'input-data': 'Numerical inputs',
             'input-tables': 'Input tables', 'analysis-conventions': 'Analysis conventions',
             'analysis-conventions-v2': 'Native analysis conventions', 'appendix-decisions': 'Physical definitions',
             'output-scope': 'Output scope'}
    return names.get(key, re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', key).replace('_', ' ').replace('-', ' ').capitalize())


def value_text(value):
    if isinstance(value, str):
        return clean_text(value)
    return json.dumps(clean_values(value), ensure_ascii=False, separators=(', ', ': '))


def clean_values(value):
    if isinstance(value, str):
        return clean_text(value)
    if isinstance(value, dict):
        return {k: clean_values(v) for k, v in value.items()}
    if isinstance(value, list):
        return [clean_values(v) for v in value]
    return value


def cell(value):
    return value_text(value).replace('&', '&amp;').replace('|', '&#124;').replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br>')


def flatten(record, prefix=''):
    result = {}
    for key, value in record.items():
        title = prefix + key
        if isinstance(value, dict) and value:
            result.update(flatten(value, title + ' · '))
        else:
            result[title] = value
    return result


def structured_blocks(data, title):
    """Readable, lossless tables; headings use field names, never JSON paths."""
    blocks = []

    def emit(value, name):
        if isinstance(value, dict):
            if set(value) == {'columns', 'rows'} and isinstance(value['columns'], list):
                blocks.append((name, editorial.table([str(x) for x in value['columns']],
                                                    [[cell(x) for x in row] for row in value['rows']])))
                return
            simple, nested = [], []
            for key, child in value.items():
                if key == 'notes' and isinstance(child, list) and all(isinstance(x, str) for x in child):
                    nested.append((key, '\n'.join(clean_text(x) for x in child)))
                elif isinstance(child, dict) and child or isinstance(child, list) and any(isinstance(x, (dict, list)) for x in child):
                    nested.append((key, child))
                else:
                    simple.append([key, cell(child)])
            if simple or not value:
                blocks.append((name, editorial.table(['Field', 'Value'], simple) if simple else '{}'))
            for key, child in nested:
                emit(child, name + ' — ' + human(key))
        elif isinstance(value, list) and value and all(isinstance(x, dict) for x in value):
            if any(any(isinstance(v, list) and any(isinstance(x, dict) for x in v) for v in row.values()) for row in value):
                for index, row in enumerate(value):
                    emit(row, name + ' — ' + str(row.get('id', index + 1)))
                return
            records = [flatten(row) for row in value]
            keys = list(dict.fromkeys(k for row in records for k in row))
            # Name=ID and section shape kind=type are explicit duplicate fields,
            # not additional input facts. State the equality once below.
            equalities = []
            for duplicate, original in [('name', 'id'), ('shape · kind', 'type')]:
                if all(duplicate in row and original in row and row[duplicate] == row[original] for row in records):
                    for row in records:
                        row.pop(duplicate)
                    keys.remove(duplicate)
                    equalities.append(duplicate + ' = ' + original)
            if 'Loads' in name and all('id' in row and ('element' in row or 'node' in row) for row in records):
                groups = collections.OrderedDict()
                for row in records:
                    attributes = {k: v for k, v in row.items() if k not in ('id', 'element', 'node')}
                    key = json.dumps(attributes, sort_keys=True)
                    groups.setdefault(key, (attributes, []))[1].append(str(row['id']) + ' → ' + str(row.get('element', row.get('node'))))
                target = 'Load ID → element / node'
                records = [dict({target: ', '.join(targets)}, **attributes) for attributes, targets in groups.values()]
                keys = [target] + [k for k in keys if k not in ('id', 'element', 'node')]
            elif title == 'Member assignments' and all('id' in row for row in records):
                groups = collections.OrderedDict()
                for row in records:
                    key = json.dumps({k: v for k, v in row.items() if k != 'id'}, sort_keys=True)
                    groups.setdefault(key, (row, []))[1].append(row['id'])
                records = [dict(row, id=', '.join(ids)) for row, ids in groups.values()]
            elif 'Loads' in name and all('member' in row for row in records):
                groups = collections.OrderedDict()
                for row in records:
                    key = json.dumps({k: v for k, v in row.items() if k != 'member'}, sort_keys=True)
                    groups.setdefault(key, (row, []))[1].append(row['member'])
                records = [dict(row, member=', '.join(ids)) for row, ids in groups.values()]
            common = []
            if len(records) > 1:
                for key in list(keys):
                    if key != 'id' and all(key in row and row[key] == records[0].get(key) for row in records):
                        common.append(key + ' = ' + cell(records[0][key]))
                        keys.remove(key)
            rendered = editorial.table(keys or ['Value'], [[cell(row[k]) if k in row else '—' for k in keys] for row in records])
            if common or equalities:
                rendered += '\n\nApplies to every listed row: ' + '; '.join(common + equalities) + '.'
            blocks.append((name, rendered))
        else:
            blocks.append((name, value_text(value)))

    emit(data, title)
    return blocks


def appendix_blocks(name, raw):
    text = raw.decode('utf-8')
    title = 'Member assignments' if Path(name).stem == 'assignments' else human(Path(name).stem)
    if name.endswith('.csv'):
        rows = list(csv.reader(io.StringIO(text)))
        return [(title, editorial.table(rows[0], [[cell(x) for x in row] for row in rows[1:]]))] if rows else []
    if name.endswith('.json'):
        return structured_blocks(json.loads(text), title)
    # Several public input-tables TXT packets contain prose followed by a full
    # JSON model. Parse that public JSON instead of reproducing a code dump.
    match = re.search(r'(?m)^\{\s*$', text)
    if match:
        try:
            data = json.loads(text[match.start():])
        except ValueError:
            pass
        else:
            prose = clean_text(text[:match.start()])
            return ([(title, prose)] if prose else []) + structured_blocks(data, title)
    return [(title, clean_text(text))]


def md_document(blocks):
    return '\n\n'.join('## ' + title + '\n\n' + body for title, body in blocks) + '\n'


def text_card(title, lines, width=1640):
    """One typeset card, including real table rows rather than Markdown syntax."""
    nodes, y = [], 36
    for line in visual.wrap(drawing_references(title), width - 48, 25):
        nodes.append(visual.text_node(line, 24, y, 25, '#125d80'))
        y += 34
    for text, heading in lines:
        for line in visual.wrap(drawing_references(html.unescape(text)), width - 48, 22):
            nodes.append(visual.text_node(line, 24, y, 22, '#125d80' if heading else '#172b3a'))
            y += 30
        y += 7 if heading else 2
    return visual.svg_bytes(nodes, width, y + 14)


def block_cards(blocks, width=1640):
    """Break lengthy notes/tables into bounded cards with repeated headers."""
    grouped = collections.OrderedDict()
    for title, body in blocks:
        root, separator, subtitle = title.partition(' — ')
        section = ('### ' + subtitle + '\n\n' if separator else '') + body
        grouped.setdefault(root, []).append(section)
    cards = []
    for title, sections in grouped.items():
        body = '\n\n'.join(sections)
        rows = body.strip().splitlines()
        lines, header, line_budget = [], None, 0
        normalized, i = [], 0
        while i < len(rows):
            row = rows[i].strip()
            if i + 1 < len(rows) and row.startswith('|') and re.fullmatch(r'\|[| :\-]+\|', rows[i+1].strip()):
                columns = row[1:-1].split('|')
                if columns == ['Field', 'Value']:
                    pairs = []
                    i += 2
                    while i < len(rows) and rows[i].strip().startswith('|'):
                        cells = rows[i].strip()[1:-1].split('|')
                        pairs.append(cells[0] + ': ' + cells[1])
                        i += 1
                    normalized.append(('; '.join(pairs), False))
                    continue
                normalized.append((' | '.join(columns), True))
                i += 2
                continue
            if row.startswith('### '):
                normalized.append((row[4:], True))
            elif row.startswith('|'):
                normalized.append((' | '.join(row[1:-1].split('|')), False))
            elif row:
                normalized.append((row, False))
            i += 1
        for row, heading in normalized:
            if not row.strip():
                continue
            if heading:
                header = row
            size = len(visual.wrap(html.unescape(row.replace('<br>', ' ')), width - 48, 22))
            if lines and line_budget + size > 35:
                cards.append(text_card(title, lines, width))
                lines = [(header, True)] if header else []
                line_budget = 0
            lines.append((row.replace('<br>', ' '), heading))
            line_budget += size
        if lines:
            cards.append(text_card(title, lines, width))
    return cards


def shift_page(raw, dx, dy):
    root = ET.fromstring(raw)
    return [visual.transform(n, dx=dx, dy=dy, min_font=18)
            for n in root if not (visual.tag(n) == 'rect' and n.get('width') == '100%')]


def sheet(case_id, turn_id, cards):
    """Pack drawing and note cards in balanced columns without reducing labels."""
    if not cards:
        cards = [text_card('Released instruction', [('No new drawing geometry supplied.', False)])]
    max_width = max(int(ET.fromstring(c).get('width')) for c in cards)
    columns = 2 if len(cards) < 10 else 3
    # Keep the principal released view first, then balance the remaining cards
    # by height. This avoids a late, long load table making one column huge.
    cards = cards[:1] + sorted(cards[1:], key=lambda raw: int(ET.fromstring(raw).get('height')), reverse=True)
    # Wide section cards remain intact. Other columns have comfortable reading
    # width; each view is kept as a single drawing region.
    column_width = max(1680, max_width + 24)
    heights, placements = [84] * columns, []
    for raw in cards:
        tree = ET.fromstring(raw)
        index = min(range(columns), key=lambda i: heights[i])
        x, y = 24 + index * column_width, heights[index]
        width, height = int(tree.get('width')), int(tree.get('height'))
        placements.append((raw, x, y, width, height))
        heights[index] += height + 24
    width, height = columns * column_width + 24, max(heights)
    if width * height > 32_000_000:
        # Four columns make unusually detailed sheets less tall. Text and view
        # geometry keep their full scale; no hidden model simplification occurs.
        columns = 4
        heights, placements = [84] * columns, []
        for raw in cards:
            tree = ET.fromstring(raw)
            index = min(range(columns), key=lambda i: heights[i])
            x, y = 24 + index * column_width, heights[index]
            w, h = int(tree.get('width')), int(tree.get('height'))
            placements.append((raw, x, y, w, h))
            heights[index] += h + 24
        width, height = columns * column_width + 24, max(heights)
    if width * height > 32_000_000:
        raise ValueError(f'{case_id}/{turn_id}: legible sheet exceeds local raster pixel budget ({width}x{height})')
    nodes = [visual.text_node(f'{case_id} | {turn_id} | STRUCTURAL INPUT / 结构输入', 26, 45, 30)]
    for raw, x, y, w, h in placements:
        nodes.append(visual.element('rect', x=x-4, y=y-4, width=w+8, height=h+8,
                                    fill='white', stroke='#b5c7d2', stroke_width=1))
        nodes.extend(shift_page(raw, x, y))
    result = visual.svg_bytes(nodes, width, height)
    fonts = [float(n.get('font-size')) for n in ET.fromstring(result).iter() if n.get('font-size')]
    return result, {'columns': columns, 'width': width, 'height': height,
                    'cards': len(cards), 'minimumFontPixels': min(fonts)}


def canonical_load_label(text, names, public):
    """Prove that a visible magnitude row already exists in public load tables."""
    match = re.match(r'^([^|]+)\|([^|]+)\|(.+)$', text)
    if not match:
        return None
    selection, target, body = (part.strip() for part in match.groups())
    case_id = selection.split('/', 1)[0]
    values = {key.lower(): float(value) for key, value in re.findall(
        r'([A-Za-z]+)\s*=\s*([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)', body)}
    if not values:
        return None
    for name in names:
        if not name.endswith('.json'):
            continue
        data = json.loads(public[name])
        if not isinstance(data, dict):
            continue
        for case in data.get('load_cases', []):
            if case.get('id') != case_id:
                continue
            for load in case.get('loads', []):
                if load.get('element', load.get('node')) != target:
                    continue
                actual = {k.lower(): v for k, v in load.items()}
                if all(isinstance(actual.get(k), (int, float)) and actual[k] == v for k, v in values.items()):
                    return {'sourceLabel': text, 'sourceFile': name, 'case': case_id,
                            'loadId': load.get('id'), 'target': target, 'components': values}
    return None


def public_drawing_cards(names, public, canonicalized=None, note_width=1640):
    cards, legends, labels = [], [], []
    for name in names:
        if not name.endswith('.svg'):
            continue
        root = visual.parse_svg(public[name])
        # Reference substitutions are editorial only; every physical label is
        # retained and then checked in the delivered sheet semantics below.
        for node in root.iter():
            if visual.tag(node) == 'text':
                node.text = drawing_references(visual.label(node))
                labels.append(node.text)
        if float(root.get('width', 0)) == 3000:
            cards.extend(compact_drawing(card) for card in visual.ring_panel_pages(root, name, legends).values())
        elif name.startswith('section-detail'):
            cards.append(visual.section_page(root))
        else:
            cards.append(compact_drawing(visual.draw_page(root, name, legends)))
    if legends:
        distinct = []
        for text in dict.fromkeys(legends):
            binding = canonical_load_label(text, names, public)
            if binding:
                if canonicalized is not None:
                    canonicalized.append(binding)
                labels = [label for label in labels if label != text]
            else:
                distinct.append(text)
        if distinct:
            cards.extend(block_cards([('Drawing legend', '\n'.join(distinct))], note_width))
    pngs = [name for name in names if name.endswith('.png') and str(Path(name).with_suffix('.svg')) not in names]
    if pngs:
        raise ValueError('Standalone public raster requires an explicit source-only layout adapter: ' + ', '.join(pngs))
    return cards, labels


def compact_drawing(raw):
    # Dimensioned schematics contain generous drafting gaps. Compact those gaps
    # uniformly while retaining every label's original readable font size.
    nodes = [visual.transform(n, sx=.85, sy=.85, min_font=20)
             for n in ET.fromstring(raw)
             if not (visual.tag(n) == 'rect' and n.get('width') == '100%')]
    _, _, right, bottom = visual.bounds(nodes)
    return visual.svg_bytes(nodes, right + 20, bottom + 20)


def dxf_pairs(raw):
    lines = raw.decode('utf-8').splitlines()
    if len(lines) % 2:
        raise ValueError('DXF has an incomplete group pair')
    return [(int(lines[i]), lines[i+1]) for i in range(0, len(lines), 2)]


def dxf_entity(kind, layer, values):
    return [(0, kind), (8, layer)] + values


def encode_dxf_text(text):
    """AC1009/R12 text: ASCII plus DXF UTF-16 Unicode escapes, max 255 bytes.

    https://ezdxf.readthedocs.io/en/stable/dxfinternals/fileencoding.html
    """
    pieces = []
    for char in text:
        if ord(char) < 128:
            pieces.append(char)
        else:
            raw = char.encode('utf-16-be')
            pieces.extend('\\U+' + raw[i:i+2].hex().upper() for i in range(0, len(raw), 2))
    result = ''.join(pieces)
    if len(result.encode('ascii')) > 255:
        raise ValueError('A DXF TEXT line exceeds 255 encoded bytes; reflow its public annotation card')
    return result


def decode_dxf_text(text):
    text = re.sub(r'\\U\+([0-9A-Fa-f]{4})', lambda m: chr(int(m.group(1), 16)), text)
    return text.encode('utf-16-be', 'surrogatepass').decode('utf-16-be')


def annotate_dxf(raw, names, public, blocks, canonicalized=None):
    """Append annotations; the original ENTITIES byte sequence stays unchanged."""
    pairs = dxf_pairs(raw)
    xs = [float(v) for code, v in pairs if code in (10, 11)]
    ys = [float(v) for code, v in pairs if code in (20, 21)]
    origin_x, origin_y = min(xs, default=0), min(ys, default=0) - 12
    additions = []
    drawings, labels = public_drawing_cards([name for name in names if name.endswith('.svg')], public, canonicalized, note_width=600)
    cards = drawings + block_cards(blocks, width=600)
    # Drawing coordinates stay in metres. The annotation scale maps 22-pixel
    # lettering to 0.22 m, matching the existing source CAD text scale.
    scale, col_w, row_bottom = .01, 18, [origin_y] * 4
    for index, card in enumerate(cards):
        tree = ET.fromstring(card)
        col = max(range(4), key=lambda i: row_bottom[i])
        dx, top = origin_x + col * col_w, row_bottom[col]
        is_section = index < len(drawings)
        layer = 'A-CLEAN-SECTION' if is_section else 'A-CLEAN-NOTES'
        for node in tree:
            kind, a = visual.tag(node), node.attrib
            x = lambda value: float(value) * scale + dx
            y = lambda value: top - float(value) * scale
            if kind == 'text':
                additions += dxf_entity('TEXT', layer, [(10, x(a.get('x', 0))), (20, y(a.get('y', 0))),
                                                       (30, 0), (40, float(a.get('font-size', 22))*scale),
                                                       (1, encode_dxf_text(drawing_references(visual.label(node))))])
            elif kind == 'line':
                additions += dxf_entity('LINE', layer, [(10, x(a['x1'])), (20, y(a['y1'])), (30, 0),
                                                       (11, x(a['x2'])), (21, y(a['y2'])), (31, 0)])
            elif kind == 'polyline':
                points = visual.xy_points(node)
                for p, q in zip(points, points[1:]):
                    additions += dxf_entity('LINE', layer, [(10, x(p[0])), (20, y(p[1])), (30, 0),
                                                           (11, x(q[0])), (21, y(q[1])), (31, 0)])
            elif kind == 'circle':
                additions += dxf_entity('CIRCLE', layer, [(10, x(a['cx'])), (20, y(a['cy'])), (30, 0),
                                                         (40, float(a['r'])*scale)])
            elif kind == 'rect' and '%' not in a.get('width', ''):
                x0, y0 = float(a.get('x', 0)), float(a.get('y', 0))
                w, h = float(a['width']), float(a['height'])
                points = [(x0,y0),(x0+w,y0),(x0+w,y0+h),(x0,y0+h),(x0,y0)]
                for p, q in zip(points, points[1:]):
                    additions += dxf_entity('LINE', layer, [(10, x(p[0])), (20, y(p[1])), (30, 0),
                                                           (11, x(q[0])), (21, y(q[1])), (31, 0)])
        row_bottom[col] -= float(tree.get('height')) * scale + 2
    original = raw.decode('utf-8')
    end = list(re.finditer(r'(?m)^0\r?\nENDSEC\r?$', original))[-1].start()
    inserted = ''.join(f'{code}\n{value}\n' for code, value in additions)
    return (original[:end] + inserted + original[end:]).encode(), labels


def short_instruction(contract, turn, followup=False, document='input.md'):
    engine, zh = contract['plannedEngine'], contract.get('locale') == 'zh'
    instruction = clean_text(turn['instruction'])
    if not contract['id'].startswith('MM-'):
        parts = instruction.split('\n\n', 1)
        if len(parts) == 2 and parts[1].startswith(('完整输入见附件。', 'Use the complete attached input tables.')):
            lead, notes = parts
            extra = (f'实际运行 {engine}，按 {document} 完成全部指定输出，并检查平衡；必要信息缺失或冲突时先澄清。' if zh else
                     f'Execute {engine}; complete every output in {document} and check equilibrium. Clarify essential gaps or conflicts first.')
            return lead + '\n\n' + extra, [('Analysis and reporting conventions', notes)]
        return instruction, []
    prefix, outputs, tail = editorial.split_instruction(instruction)
    if followup:
        prompt = (f'依据本轮补图，使用 {engine} 实际分析并完成前述全部输出；必要缺项或冲突先澄清。' if zh else
                  f'Use this released supplement for an actual {engine} analysis and all previously requested outputs. Clarify essential gaps or conflicts first.')
        return prompt, [('Released supplement', instruction)]
    prompt = (f'从所附图纸重建结构并使用 {engine} 实际分析；必要缺项或冲突先澄清。报告带符号、单位及工况/组合的下列结果，并附一致的模型/结果图：' if zh else
              f'Reconstruct from the drawing and execute {engine}. Clarify essential gaps or conflicts first. Report the following signed results with units and cases/combinations; include consistent model/result figures:')
    if '\n\n' in prefix:
        prompt = prefix.split('\n\n', 1)[0] + '\n\n' + prompt
    extra_tail = tail
    for common in editorial.COMMON_TAILS:
        if extra_tail == common or extra_tail.startswith(common + '\n'):
            extra_tail = extra_tail[len(common):].strip()
            break
    if outputs:
        prompt += '\n' + '\n'.join('- ' + re.sub(r' \[[^\[\]]+\]$', '', x) for x in outputs)
    else:
        prompt += '\n' + instruction
    if extra_tail:
        prompt += '\n\n' + drawing_references(extra_tail)
    # The short prompt carries the task, requested results and clarification
    # action. Distinct physical conventions are in the released property/load
    # appendices; do not put the same task prose on the drawing again.
    known = prefix.startswith(('请依据所附图纸', 'Reconstruct the model')) or any(
        marker in prefix for marker in ['\n\n从所附尺寸图', '\n\nReconstruct the structure',
                                        '\n\n从建筑图 input.dxf', '\n\nReconstruct geometry and connectivity from the architectural input.dxf'])
    evidence = []
    if '\n\n' in prefix:
        evidence = [('Run records', 'Preserve drawing-to-model IDs; retain native input, engine/version/settings, solver logs, raw results and figure data.')]
    return prompt, evidence if known else [('Additional drawing instructions', prefix)]


def build_case(contract, manifest_row, public_files):
    """Pure public-input builder; hidden contract fields cannot affect output."""
    bundle = {'schemaVersion': 1, 'edition': EDITION, 'caseId': contract['id'],
              'baseSourceHash': manifest_row['sourceHash'], 'turns': []}
    files, audits, pages, bindings = {}, [], {}, {}
    initial = '\n'.join(public_files[n].decode('utf-8') for n in contract['turns'][0].get('attachments', [])
                        if n.endswith(('.json', '.txt')))
    policy = (['construction_stage=false'] if contract['id'].startswith('MM-') and
              not re.search(r'construction_stage|construction stages?|施工阶段', initial, re.I) else [])
    for index, turn in enumerate(contract['turns']):
        names = turn.get('attachments', [])
        document = 'input.md' if index == 0 else f'input-{turn["id"]}.md'
        bindings.update({n: document for n in names if n.endswith(('.json', '.txt', '.csv'))})
        instruction, notes = short_instruction(contract, turn, index > 0, document)
        clarification = INSTRUCTION_CLARIFICATIONS.get((contract['id'], turn['id'], turn['instruction']))
        if clarification is not None:
            instruction = clarification
        if not contract['id'].startswith('MM-'):
            instruction = public_references(instruction, bindings)
        blocks = []
        for name in names:
            if name.endswith(('.json', '.txt', '.csv')):
                blocks.extend(appendix_blocks(name, public_files[name]))
        blocks += [(title, drawing_references(body) if contract['id'].startswith('MM-') else clean_text(body))
                   for title, body in notes if body.strip()]
        if not contract['id'].startswith('MM-'):
            blocks = [(title, public_references(body, bindings)) for title, body in blocks]
        if index == 0 and policy:
            blocks.append(('Properties — Analysis settings', '不考虑施工阶段。' if contract.get('locale') == 'zh' else 'Do not model construction stages.'))
        name, layout, preserved = None, None, True
        canonicalized = []
        cad = [n for n in names if n.endswith('.dxf')]
        if contract['id'].startswith('MM-'):
            suffix = '' if index == 0 else '-' + turn['id']
            if cad:
                if len(cad) != 1:
                    raise ValueError('One original CAD source is required per release')
                name = f'drawing{suffix}.dxf'
                blocks.append(('CAD annotation layers', 'A-CLEAN-NOTES and A-CLEAN-SECTION contain annotations and published drawing details; they do not add structural centre lines. Preserve the original layer conventions for structure, supports, loads and dimensions; retain architectural distractors where supplied.'))
                files[name], labels = annotate_dxf(public_files[cad[0]], names, public_files, blocks, canonicalized)
                visible = ''.join(decode_dxf_text(value) for code, value in dxf_pairs(files[name]) if code == 1)
                compact = re.sub(r'\s+', '', visible)
                preserved = all(re.sub(r'\s+', '', t) in compact for t in labels)
            else:
                cards, labels = public_drawing_cards(names, public_files, canonicalized)
                cards += block_cards(blocks)
                name = f'drawing{suffix}.png'
                svg, layout = sheet(contract['id'], turn['id'], cards)
                files['authoring/' + str(Path(name).with_suffix('.svg'))] = svg
                pages[name] = svg
                visible = ''.join(visual.label(n) for n in ET.fromstring(svg).iter() if visual.tag(n) == 'text')
                compact = re.sub(r'\s+', '', visible)
                preserved = all(re.sub(r'\s+', '', t) in compact for t in labels)
            if not preserved:
                raise ValueError(f'{contract["id"]}/{turn["id"]}: public drawing label lost at release')
        elif names or blocks:
            name = 'input.md' if index == 0 else f'input-{turn["id"]}.md'
            files[name] = md_document(blocks).encode()
        descriptors = [{'name': name, 'source': 'edition', 'path': name, 'sha256': ''}] if name else []
        bundle['turns'].append({'id': turn['id'], 'instruction': instruction, 'attachments': descriptors})
        audits.append({'id': turn['id'], 'sourceNames': names, 'deliveredNames': [name] if name else [],
                       'allPublicDrawingLabelsPreserved': preserved, 'originalDXFEntitiesPreserved': bool(cad),
                       'canonicalizedDrawingLabels': canonicalized,
                       'layout': layout, 'publicSourceBindings': [{'name': n, 'sha256': digest(public_files[n])} for n in names]})
        if clarification is not None:
            audits[-1]['instructionClarification'] = {
                'sourceInstruction': turn['instruction'], 'releasedInstruction': clarification,
                'reason': 'Make unresolved component scope explicit; preserve the later user decision.',
                'review': 'post300-fixes-20261027',
            }
    renderer = None
    if pages:
        rendered, renderer = visual.render(pages)
        files.update(rendered)
    for turn in bundle['turns']:
        for a in turn['attachments']:
            a['sha256'] = digest(files[a['path']])
    audit = {'schemaVersion': 1, 'edition': EDITION, 'caseId': contract['id'],
             'kind': 'public-source-correspondence-not-independent-blind-review',
             'renderer': renderer, 'analysisPolicyClarifications': policy, 'turns': audits}
    files['author-audit.json'] = json_text(audit).encode()
    return bundle, files, audit


def source_ids(root):
    return sorted(r['id'] for r in json.loads((Path(root)/'corpora/research-300/manifest.json').read_text())['cases'])


def manifest_record(case_id, row, encoded):
    return {'id': case_id, 'baseSourceHash': row['sourceHash'], 'basePublicSha256': row['publicSha256'],
            'path': case_id+'/input.json', 'sha256': digest(encoded)}


def check_case(root, case_id):
    root = Path(root)
    contract, row, public = read_case(root, case_id)
    bundle, files, _ = build_case(contract, row, public)
    files['input.json'] = json_text(bundle).encode()
    folder, errors = root/EDITION_REL/case_id, []
    for name, expected in files.items():
        try:
            if (folder/name).read_bytes() != expected:
                errors.append(f'{case_id}/{name}: differs from deterministic public-source canonical bytes')
        except OSError as exc:
            errors.append(f'{case_id}/{name}: {exc}')
    if folder.exists():
        errors += [f'{case_id}/{p.relative_to(folder).as_posix()}: unexpected edition file'
                   for p in folder.rglob('*') if p.is_file() and p.relative_to(folder).as_posix() not in files]
    try:
        manifest = json.loads((root/EDITION_REL/'manifest.json').read_text())
        if set(manifest) != {'schemaVersion', 'edition', 'cases'} or manifest['schemaVersion'] != 1 or manifest['edition'] != EDITION:
            errors.append('public-inputs/manifest.json: invalid edition schema')
        if [r for r in manifest['cases'] if r['id'] == case_id] != [manifest_record(case_id, row, files['input.json'])]:
            errors.append(f'{case_id}: edition manifest binding differs from public-source reconstruction')
        if sorted(r['id'] for r in manifest['cases']) != source_ids(root):
            errors.append('public-inputs/manifest.json: must cover every frozen case exactly once')
    except (OSError, ValueError, KeyError) as exc:
        errors.append(f'public-inputs/manifest.json: {exc}')
    return errors


def generate(root, case_ids=None):
    root = Path(root)
    edition = root/EDITION_REL
    require_plain_output(edition, inspect_tree=True)
    edition.mkdir(parents=True, exist_ok=True)
    wanted = case_ids or source_ids(root)
    previous = {}
    if (edition/'manifest.json').exists():
        previous = {r['id']: r for r in json.loads((edition/'manifest.json').read_text())['cases']}
    turns, attachments = 0, 0
    for case_id in wanted:
        contract, row, public = read_case(root, case_id)
        bundle, files, _ = build_case(contract, row, public)
        files['input.json'] = json_text(bundle).encode()
        folder = edition/case_id
        require_plain_output(folder, inspect_tree=True)
        folder.mkdir(parents=True, exist_ok=True)
        for name, raw in files.items():
            target = folder/name
            require_plain_output(target)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        previous[case_id] = manifest_record(case_id, row, files['input.json'])
        turns += len(bundle['turns'])
        attachments += sum(len(t['attachments']) for t in bundle['turns'])
    records = [previous[i] for i in source_ids(root) if i in previous]
    require_plain_output(edition/'manifest.json')
    (edition/'manifest.json').write_text(json_text({'schemaVersion': 1, 'edition': EDITION, 'cases': records}))
    return {'valid': True, 'edition': EDITION, 'cases': len(wanted), 'turns': turns, 'attachments': attachments}


def require_plain_output(path, inspect_tree=False):
    """Reject existing symlinks before creating, replacing or traversing output."""
    path = Path(path).absolute()
    for parent in list(reversed(path.parents)) + [path]:
        if parent.is_symlink():
            raise ValueError(f'Symlink is not allowed in generated edition output: {parent}')
    if inspect_tree and path.is_dir():
        for folder, directories, files in os.walk(path, followlinks=False):
            for name in directories + files:
                candidate = Path(folder)/name
                if candidate.is_symlink():
                    raise ValueError(f'Symlink is not allowed in generated edition output: {candidate}')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=HERE.parents[1])
    parser.add_argument('--case', action='append', dest='case_ids')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    try:
        if args.check:
            ids = args.case_ids or source_ids(args.root)
            errors = [e for case_id in ids for e in check_case(args.root, case_id)]
            print(json.dumps({'valid': not errors, 'edition': EDITION, 'cases': len(ids), 'errors': errors}, ensure_ascii=False))
            return int(bool(errors))
        print(json.dumps(generate(args.root, args.case_ids), ensure_ascii=False))
        return 0
    except (OSError, ValueError, KeyError, ET.ParseError) as exc:
        print(json.dumps({'valid': False, 'errors': [str(exc)]}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    sys.exit(main())
