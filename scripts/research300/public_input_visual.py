#!/usr/bin/env python3
"""Public-only visual-v2 authoring and deterministic correspondence checker.

Only public instructions and attachments are used. The checker regenerates
visible SVG semantics, reruns the pinned local raster pipeline, and compares
every byte, including PNGs, independently of editable manifests and audits.
Python imports are stdlib only; rendering uses the repository's existing sharp.
"""
from __future__ import annotations

import argparse
import base64
import collections
import copy
import csv
import hashlib
import importlib.util
import io
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('visual_public_editorial', HERE / 'public_input_editorial.py')
editorial = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(editorial)
digest, json_text = editorial.digest, editorial.json_text
EDITION = 'visual-v2'
EDITION_REL = Path('corpora/research-300/public-inputs') / EDITION
INVENTORY_REL = Path('docs/implementation/reviews/mm-visual-v2-20261016')
NS = 'http://www.w3.org/2000/svg'
ET.register_namespace('', NS)
FONT = 'DejaVu Sans, Noto Sans CJK SC, sans-serif'
ALLOWED_TAGS = {'svg', 'rect', 'text', 'line', 'polyline', 'circle'}


def tag(element):
    return element.tag.rsplit('}', 1)[-1]


def label(element):
    return ''.join(element.itertext())


def number(value):
    return f'{value:.3f}'.rstrip('0').rstrip('.')


def element(kind, **attrs):
    return ET.Element('{' + NS + '}' + kind, {k.replace('_', '-'): str(v) for k, v in attrs.items()})


def text_node(text, x, y, size=22, fill='#172b3a'):
    node = element('text', x=number(x), y=number(y), font_family=FONT, font_size=number(size), fill=fill)
    node.text = text
    return node


def rewrite_references(text):
    return re.sub(r'([\w-]+)\.(json|txt)\b', r'\1.md', text)


def text_width(text, size=22):
    # Conservative font bounds, used for layout only; labels are never truncated.
    return sum(1.02 if ord(c) > 255 else .66 if c.isupper() else .59 for c in text) * size


def wrap(text, width, size=22):
    result, line = [], ''
    for token in re.findall(r'\S+\s*|\s+', text):
        if text_width(line + token, size) <= width:
            line += token
            continue
        if line.strip():
            result.append(line.rstrip())
            line = ''
        # Chinese text and long IDs may contain no whitespace.
        for char in token:
            if line and text_width(line + char, size) > width:
                result.append(line)
                line = ''
            line += char
    if line.strip():
        result.append(line.rstrip())
    return result or ['']


def xy_points(node):
    kind = tag(node)
    a = node.attrib
    if kind == 'line':
        return [(float(a['x1']), float(a['y1'])), (float(a['x2']), float(a['y2']))]
    if kind == 'polyline':
        pairs = [float(x) for x in re.split(r'[ ,]+', a['points'].strip())]
        return list(zip(pairs[::2], pairs[1::2]))
    if kind == 'circle':
        x, y, r = float(a['cx']), float(a['cy']), float(a['r'])
        return [(x-r, y-r), (x+r, y+r)]
    if kind == 'text':
        x, y, size = float(a.get('x', 0)), float(a.get('y', 0)), float(a.get('font-size', 22))
        return [(x, y-size*1.12), (x+text_width(label(node), size), y+size*.3)]
    if kind == 'rect' and '%' not in a.get('width', ''):
        x, y = float(a.get('x', 0)), float(a.get('y', 0))
        return [(x, y), (x+float(a['width']), y+float(a['height']))]
    return []


def bounds(nodes):
    points = [point for node in nodes for point in xy_points(node)]
    if not points:
        return (0, 0, 100, 100)
    return min(p[0] for p in points), min(p[1] for p in points), max(p[0] for p in points), max(p[1] for p in points)


def transform(node, sx=1, sy=1, dx=0, dy=0, font_scale=1, min_font=20):
    node = copy.deepcopy(node)
    a, kind = node.attrib, tag(node)
    for x in ['x', 'x1', 'x2', 'cx']:
        if x in a:
            a[x] = number(float(a[x])*sx + dx)
    for y in ['y', 'y1', 'y2', 'cy']:
        if y in a:
            a[y] = number(float(a[y])*sy + dy)
    if kind == 'polyline':
        original = xy_points(node)
        a['points'] = ' '.join(number(x*sx+dx)+','+number(y*sy+dy) for x, y in original)
    if kind == 'text':
        a['font-size'] = number(max(min_font, float(a.get('font-size', 22))*font_scale))
        a['font-family'] = FONT
        node.text = rewrite_references(label(node))
    if kind == 'circle':
        a['r'] = number(float(a['r'])*min(sx, sy))
    return node


def svg_bytes(nodes, width, height):
    root = element('svg', width=math.ceil(width), height=math.ceil(height), viewBox=f'0 0 {math.ceil(width)} {math.ceil(height)}')
    root.append(element('rect', width='100%', height='100%', fill='white'))
    root.extend(nodes)
    return (ET.tostring(root, encoding='unicode')+'\n').encode()


def parse_svg(raw):
    if b'<!DOCTYPE' in raw or b'<!ENTITY' in raw:
        raise ValueError('Public SVG entities are not supported')
    root = ET.fromstring(raw)
    for node in root.iter():
        if tag(node) not in ALLOWED_TAGS:
            raise ValueError(f'Unsupported public SVG primitive {tag(node)}')
        if any('href' in key.lower() or key.lower().startswith('on') for key in node.attrib):
            raise ValueError('External or executable public SVG attribute')
    return root


def legend_page(case_id, turn_id, entries):
    # Only identical visible public strings are deduplicated, within one turn.
    entries = list(dict.fromkeys(rewrite_references(t) for t in entries))
    members, loads, headings, notes = [], [], [], []
    for text in entries:
        if text.startswith(('Member key:', '构件索引：')):
            headings.append(text)
        elif re.match(r'^\S+:\s*\S+\s*->', text):
            members.append(text)
        elif re.match(r'^[\w/+-]+\s*\|', text) or re.match(r'^[^ ]+/[^:]+:', text):
            loads.append(text)
        else:
            notes.append(text)
    width = 1680
    nodes = [text_node(f'{case_id} | {turn_id} | DIAGRAM LEGEND / LOAD KEY', 28, 42, 28)]
    y = 82
    for note in notes:
        for line in wrap(note, width-56):
            nodes.append(text_node(line, 28, y))
            y += 31
        y += 8
    for headings_here, rows in [(['LOADS / 荷载'] if loads else [], loads), (headings, members)]:
        if not rows and not headings_here:
            continue
        y += 16
        for heading in headings_here:
            for line in wrap(heading, width-56):
                nodes.append(text_node(line, 28, y, fill='#15648c'))
                y += 32
        if not rows:
            continue
        max_width = max(text_width(t) for t in rows)
        columns = max(1, min(3, int((width-56)//(max_width+36))))
        column_width = (width-56)/columns
        for i, text in enumerate(rows):
            nodes.append(text_node(text, 28+(i % columns)*column_width, y+(i//columns)*32))
        y += math.ceil(len(rows)/columns)*32
    return svg_bytes(nodes, width, y+24), entries


def section_page(root):
    title = next((n for n in root if tag(n) == 'text'), None)
    content = [n for n in root if n is not title and tag(n) != 'rect']
    cards = collections.OrderedDict()
    for node in content:
        pts = xy_points(node)
        if not pts:
            continue
        # Public source cards are 590 x 330, starting at x=50, y=90.
        x, y = pts[0]
        col = max(0, int((x-40)//590))
        row = max(0, int((y-80)//330))
        cards.setdefault((row, col), []).append(node)
    keys = sorted(cards)
    scale, card_w, card_h = 1.32, 790, 440
    columns = min(2, len(keys)) or 1
    width = columns*card_w+40
    nodes = []
    y_header = 38
    for line in wrap(rewrite_references(label(title)) if title is not None else 'SECTION DETAILS', width-48, 24):
        nodes.append(text_node(line, 24, y_header, 24))
        y_header += 33
    origin_y = y_header+24
    for i, key in enumerate(keys):
        row, col = key
        dest_x, dest_y = 24+(i % columns)*card_w, origin_y+(i//columns)*card_h
        for node in cards[key]:
            nodes.append(transform(node, scale, scale, dest_x-(50+col*590)*scale,
                                   dest_y-(90+row*330)*scale, scale, 18))
    _, _, right, bottom = bounds(nodes)
    return svg_bytes(nodes, max(width, right+24), bottom+30)


def draw_page(root, filename, legend, special=False):
    children = list(root)
    title = next((n for n in children if tag(n) == 'text'), None)
    width = float(root.get('width', 1800))
    texts = [n for n in children if tag(n) == 'text']
    member_heading = next((float(n.get('y', 0)) for n in texts if label(n).startswith(('Member key:', '构件索引：'))), None)
    modern = any(label(n).startswith('LOAD KEY:') for n in texts)
    kept = []
    for node in children:
        if node is title or (tag(node) == 'rect' and node.get('width') == '100%'):
            continue
        if tag(node) == 'text':
            text, y = label(node), float(node.get('y', 0))
            # Position alone cannot distinguish common prose from axis labels
            # or intentionally missing-datum warnings near the top of a view.
            common_header = text.startswith(('Schematic;', 'Schematic:', '示意图，', '示意图：',
                                              'Length m;', '长度 m；', 'Orthographic input.'))
            if width == 2700 and y < 270:
                common_header = True
            bottom = (modern and y >= 1160) or (member_heading is not None and y >= member_heading-1)
            # MM-042 aliases have panel-local meaning and stay beside each face.
            if special:
                bottom = y >= 1950
            if common_header or bottom:
                legend.append(text)
                continue
            force = re.match(r'^([^ :]+/[^:]+):\s*(.+)$', text)
            pipe_force = re.match(r'^([^ |]+/[^ |]+)\s*\|\s*([^|]+?)\s*\|\s*(.+)$', text)
            if force:
                legend.append(text)
                node = copy.deepcopy(node)
                node.text = force.group(1)
            elif pipe_force:
                legend.append(text)
                node = copy.deepcopy(node)
                node.text = pipe_force.group(1)+' | '+pipe_force.group(2)
            if re.match(r'^\S+ \[[XYZ]=', text):
                # First-generation support hatch extends below the node; its
                # original baseline can touch a now more readable node label.
                circle_y = [float(c.get('cy')) for c in children if tag(c) == 'circle'
                            and abs(float(c.get('cx'))-float(node.get('x'))-40) < 1]
                if any(35 <= y-cy <= 45 for cy in circle_y):
                    node = copy.deepcopy(node)
                    node.set('y', number(y+12))
        kept.append(node)
    if not kept:
        kept = [text_node('No additional drawing primitives', 20, 100)]
    left, top, right, bottom = bounds(kept)
    # Compress blank margins and horizontal drafting spacing; text itself is
    # never scaled down. A schematic does not authorize reading pixel lengths.
    sx = min(1, 1550/max(right-left, 1)) if not special else 1
    nodes = []
    title_text = rewrite_references(label(title)) if title is not None else filename
    for i, line in enumerate(wrap(title_text, 1540, 26)):
        nodes.append(text_node(line, 24, 36+i*34, 26))
    title_bottom = 44+max(0, len(nodes)-1)*34
    for node in kept:
        nodes.append(transform(node, sx, 1, 30-left*sx, title_bottom+34-top, min_font=20))
    _, _, right, bottom = bounds(nodes)
    return svg_bytes(nodes, right+32, bottom+28)


def ring_panel_pages(root, filename, legend):
    """Split the already public MM-042 panels, keeping each alias key local.

    These are source drawing page coordinates, not structural coordinates or a
    reconstructed model. No primitive can cross a source panel boundary.
    """
    title = next(n for n in root if tag(n) == 'text')
    plan = 'XY ORTHOGRAPHIC' in label(title)
    count = 4 if plan else 3
    panels = [[] for _ in range(count)]
    for node in root:
        if node is title or tag(node) == 'rect':
            continue
        pts = xy_points(node)
        if not pts:
            continue
        x = float(node.get('x', pts[0][0]))
        y = float(node.get('y', pts[0][1]))
        if tag(node) == 'text' and (y < 240 or y >= 1950):
            legend.append(label(node))
            continue
        index = (int(y >= 1060)*2 + int(x >= 1490)) if plan else min(2, int(x//990))
        panels[index].append(node)
    result = {}
    for i, nodes in enumerate(panels):
        panel = element('svg', width=1500 if plan else 990)
        panel.append(text_node(label(title)+f' | panel {i+1}', 24, 38, 26))
        panel.extend(nodes)
        name = filename if i == 0 else str(Path(filename).with_name(Path(filename).stem+f'-panel-{i+1}.png'))
        result[name] = draw_page(panel, name, legend)
    return result


def render(pages):
    node = '/opt/lab-node/bin/node' if Path('/opt/lab-node/bin/node').exists() else shutil.which('node')
    if not node:
        raise ValueError('Local Node is required for canonical public PNG verification')
    result = subprocess.run([node, str(HERE/'render_public_visual.cjs')], input=json.dumps({'pages': {n: b.decode() for n, b in pages.items()}}),
                            text=True, capture_output=True, timeout=60, check=False)
    if result.returncode:
        raise ValueError('Canonical raster pipeline failed: '+result.stderr.strip())
    data = json.loads(result.stdout)
    return {name: base64.b64decode(value) for name, value in data['pages'].items()}, data['renderer']


def read_case(root, case_id):
    # Reuse only concise-v1's public-source reader, not its author inventory.
    contract, row, files = editorial.read_case(Path(root), case_id)
    # Original public byte hashes are a separate trust boundary.
    hashes = {r['path']: r['sha256'] for r in row.get('publicFiles', [])}
    for name, raw in files.items():
        if name in hashes and digest(raw) != hashes[name]:
            raise ValueError(f'{case_id}/{name}: frozen public source hash mismatch')
    return contract, row, files


def build_case(contract, manifest_row, public_files):
    concise, appendix_files, edits = editorial.build_case(contract, manifest_row, public_files)
    bundle = copy.deepcopy(concise)
    bundle['edition'] = EDITION
    files = {name: value.encode() for name, value in appendix_files.items()}
    initial_text = '\n'.join(appendix_files.get(a['path'], '')
                             for a in concise['turns'][0]['attachments'] if a['source'] == 'edition')
    # Blind reconstruction found an implicit setup convention in the earlier
    # text-only property format. Make the benchmark's un-staged static-analysis
    # policy explicit; this is an authored clarification, not a source quote or
    # a reconstruction from a hidden model. No physical/result values change.
    policy_clarifications = [] if re.search(r'construction_stage|施工阶段|construction stages?', initial_text, re.I) else ['construction_stage=false']
    pages, turns_audit, all_source_labels = {}, [], []
    for original_turn, turn in zip(contract['turns'], bundle['turns']):
        legend, page_map, descriptors, additional_pages = [], [], [], {}
        original_names = original_turn.get('attachments', [])
        svg_names = [name for name in original_names if name.endswith('.svg')]
        png_stems = {str(Path(name).with_suffix('.png')) for name in svg_names}
        for name in svg_names:
            root = parse_svg(public_files[name])
            labels = [rewrite_references(label(n)) for n in root if tag(n) == 'text']
            all_source_labels.extend(labels)
            target = str(Path(name).with_suffix('.png'))
            if float(root.get('width', 0)) == 3000:
                split_pages = ring_panel_pages(root, target, legend)
                pages.update(split_pages)
                additional_pages[target] = [n for n in split_pages if n != target]
                kind = 'existing-public-panel-with-contextual-alias-key'
            elif name.startswith('section-detail'):
                page = section_page(root)
                pages[target] = page
                kind = 'section-shape-roll-axes-and-assignment'
            else:
                page = draw_page(root, name, legend)
                pages[target] = page
                kind = 'public-geometry-supports-dimensions-and-load-positions'
            page_map.append({'source': name, 'sourceSha256': digest(public_files[name]), 'output': target,
                             'role': kind, 'sharedLegend': f'diagram-legend-{turn["id"]}.png' if not name.startswith('section-detail') else None})
            for extra_name in additional_pages.get(target, []):
                page_map.append({'source': name, 'sourceSha256': digest(public_files[name]), 'output': extra_name,
                                 'role': kind, 'sharedLegend': f'diagram-legend-{turn["id"]}.png'})
        if legend:
            target = f'diagram-legend-{turn["id"]}.png'
            pages[target], kept_legend = legend_page(contract['id'], turn['id'], legend)
            page_map.append({'source': svg_names, 'output': target, 'role': 'deduplicated-visible-public-labels',
                             'sourceOccurrences': len(legend), 'retainedUniqueLabels': len(kept_legend)})
        delivered = set()
        for descriptor in turn['attachments']:
            name = descriptor['name']
            if name.endswith('.svg'):
                name = str(Path(name).with_suffix('.png'))
            elif name.endswith('.png') and name not in png_stems:
                # No SVG counterpart: original raster is authoritative.
                pass
            if name in delivered:
                continue
            delivered.add(name)
            if name in pages:
                descriptors.append({'name': name, 'source': 'edition', 'path': name, 'sha256': ''})
                for extra_name in additional_pages.get(name, []):
                    descriptors.append({'name': extra_name, 'source': 'edition', 'path': extra_name, 'sha256': ''})
            else:
                descriptors.append(descriptor)
        if legend:
            name = f'diagram-legend-{turn["id"]}.png'
            descriptors.append({'name': name, 'source': 'edition', 'path': name, 'sha256': ''})
        for original_name in original_names:
            if original_name.endswith('.svg'):
                continue
            mapped_name = str(Path(original_name).with_suffix('.md')) if original_name.endswith(('.json', '.txt')) else original_name
            role = 'public-appendix-complete-roundtrip' if original_name.endswith(('.json', '.txt')) else 'original-CAD-retained' if original_name.endswith('.dxf') else 'canonical-raster-from-public-SVG' if original_name in png_stems else 'original-public-attachment-retained'
            page_map.append({'source': original_name, 'sourceSha256': digest(public_files[original_name]),
                             'output': mapped_name, 'role': role})
        turn['attachments'] = descriptors
        instruction = turn['instruction']
        for name in original_names:
            replacement = str(Path(name).with_suffix('.png')) if name.endswith('.svg') else str(Path(name).with_suffix('.md')) if name.endswith(('.json', '.txt')) else name
            instruction = instruction.replace(name, replacement)
        # The attachment list already names every view. Keep the task concise
        # and point only to the consolidated key for this release turn.
        names = [a['name'] for a in descriptors]
        zh = contract.get('locale') == 'zh'
        if turn['id'] == bundle['turns'][0]['id'] and policy_clarifications:
            instruction += '\n\n' + ('不考虑施工阶段。' if zh else 'Do not model construction stages.')
        if legend:
            key = f'diagram-legend-{turn["id"]}.png'
            instruction += '\n\n' + (f'图例与荷载索引见 {key}。' if zh else f'See {key} for the drawing legend and load key.')
        turn['instruction'] = instruction
        turns_audit.append({'id': turn['id'], 'sourceNames': original_names, 'deliveredNames': names,
                            'pageMap': page_map, 'legendSourceOccurrences': len(legend),
                            'legendUniqueLabels': len(set(legend))})
    pngs, renderer = render(pages)
    for name, svg in pages.items():
        files['authoring/'+str(Path(name).with_suffix('.svg'))] = svg
        files[name] = pngs[name]
    for turn in bundle['turns']:
        for descriptor in turn['attachments']:
            if descriptor['source'] == 'edition':
                descriptor['sha256'] = digest(files[descriptor['path']])
    # This author audit is explicitly not independent input-blind validation.
    labels_after = [label(n) for raw in pages.values() for n in ET.fromstring(raw) if tag(n) == 'text']
    preserved = True
    joined_after = re.sub(r'\s+', '', ''.join(labels_after))
    for source_label in set(all_source_labels):
        if re.sub(r'\s+', '', source_label) not in joined_after:
            preserved = False
            raise ValueError(f'{contract["id"]}: visible label was lost: {source_label}')
    for turn, original_turn in zip(turns_audit, contract['turns']):
        visible = ''.join(label(n) for name in turn['deliveredNames'] if name in pages
                          for n in ET.fromstring(pages[name]) if tag(n) == 'text')
        visible = re.sub(r'\s+', '', visible)
        turn_labels = [rewrite_references(label(n)) for name in original_turn.get('attachments', []) if name.endswith('.svg')
                       for n in parse_svg(public_files[name]) if tag(n) == 'text']
        if any(re.sub(r'\s+', '', source_label) not in visible for source_label in turn_labels):
            raise ValueError(f'{contract["id"]}/{turn["id"]}: visible label crossed its release boundary')
        turn['allSourceLabelsPreservedAtRelease'] = True
    png_metrics = []
    for name, raw in pages.items():
        tree = ET.fromstring(raw)
        sizes = [float(n.get('font-size')) for n in tree if n.get('font-size')]
        png_metrics.append({'name': name, 'width': int(tree.get('width')), 'height': int(tree.get('height')),
                            'minimumFontPixels': min(sizes) if sizes else None,
                            'svgSha256': digest(raw), 'pngSha256': digest(pngs[name])})
    audit = {'schemaVersion': 1, 'edition': EDITION, 'caseId': contract['id'],
             'kind': 'deterministic-public-author-audit-not-independent-blind-review', 'renderer': renderer,
             'analysisPolicyClarifications': policy_clarifications,
             'sourcePublicFiles': [{'name': name, 'sha256': digest(raw)} for name, raw in public_files.items()],
             'turns': turns_audit, 'pages': png_metrics,
             'sourceModalities': dict(sorted(collections.Counter(Path(name).suffix.lstrip('.') for name in public_files).items())),
             'sourceRasterPixels': sum(int.from_bytes(raw[16:20], 'big')*int.from_bytes(raw[20:24], 'big')
                                       for name, raw in public_files.items() if name.endswith('.png') and raw.startswith(b'\x89PNG')),
             'publicFactAudit': {'allSourceLabelsPreserved': preserved, 'sourceLabelOccurrences': len(all_source_labels),
                                 'outputLabelOccurrences': len(labels_after),
                                 'sourceVisibleLabelSha256': digest(json_text(all_source_labels).encode()),
                                 'appendices': [e['verification']['kind'] for e in edits],
                                 'basis': 'visible source SVG primitives and public appendix roundtrips only'},
             'releaseBoundaries': [t['id'] for t in bundle['turns']]}
    files['author-audit.json'] = json_text(audit).encode()
    return bundle, files, audit


def check_case(root, case_id):
    root = Path(root)
    contract, row, public = read_case(root, case_id)
    expected, files, _ = build_case(contract, row, public)
    folder = root/EDITION_REL/case_id
    files['input.json'] = json_text(expected).encode()
    errors = []
    for name, raw in files.items():
        path = folder/name
        try:
            if path.read_bytes() != raw:
                errors.append(f'{case_id}/{name}: differs from deterministic public-source canonical bytes')
        except OSError as exc:
            errors.append(f'{case_id}/{name}: {exc}')
    if folder.exists():
        extra = sorted(p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file() and p.relative_to(folder).as_posix() not in files)
        errors.extend(f'{case_id}/{name}: unexpected edition file' for name in extra)
    try:
        manifest = json.loads((root/EDITION_REL/'manifest.json').read_text())
        if manifest.get('schemaVersion') != 1 or manifest.get('edition') != EDITION:
            errors.append('visual-v2/manifest.json: invalid edition schema')
        rows = [r for r in manifest['cases'] if r['id'] == case_id]
        wanted = manifest_record(case_id, row, files['input.json'])
        if rows != [wanted]:
            errors.append(f'{case_id}: edition manifest binding differs from public-source reconstruction')
        source_ids = sorted(r['id'] for r in json.loads((root/'corpora/research-300/manifest.json').read_text())['cases'] if r['id'].startswith('MM-'))
        if sorted(r['id'] for r in manifest['cases']) != source_ids:
            errors.append('visual-v2/manifest.json: must cover every frozen MM case exactly once')
    except (OSError, ValueError, KeyError) as exc:
        errors.append(f'visual-v2/manifest.json: {exc}')
    return errors


def manifest_record(case_id, row, encoded):
    return {'id': case_id, 'baseSourceHash': row['sourceHash'], 'basePublicSha256': row['publicSha256'],
            'path': case_id+'/input.json', 'sha256': digest(encoded)}


def write_inventory(root, audits):
    folder = root/INVENTORY_REL
    folder.mkdir(parents=True, exist_ok=True)
    before = sum(a['publicFactAudit']['sourceLabelOccurrences'] for a in audits)
    after = sum(a['publicFactAudit']['outputLabelOccurrences'] for a in audits)
    summary = {'cases': len(audits), 'turns': sum(len(a['turns']) for a in audits),
               'sourceDrawingLabelOccurrences': before, 'outputDrawingLabelOccurrences': after,
               'labelOccurrenceReduction': before-after,
               'pngPages': sum(len(a['pages']) for a in audits),
               'originalPNGPages': sum(a['sourceModalities'].get('png', 0) for a in audits),
               'originalSVGPages': sum(a['sourceModalities'].get('svg', 0) for a in audits),
               'retainedOriginalDXFs': sum(a['sourceModalities'].get('dxf', 0) for a in audits),
               'sourceRasterPixels': sum(a['sourceRasterPixels'] for a in audits),
               'outputRasterPixels': sum(p['width']*p['height'] for a in audits for p in a['pages']),
               'independentBlindReview': False, 'allSourceLabelsPreserved': all(a['publicFactAudit']['allSourceLabelsPreserved'] for a in audits)}
    (folder/'visual-inventory.json').write_text(json_text({'summary': summary, 'cases': audits}))
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow(['caseId', 'turn', 'source', 'output', 'role', 'sourceLabelOccurrences', 'outputLabelOccurrences'])
    for audit in audits:
        for turn in audit['turns']:
            for page in turn['pageMap']:
                writer.writerow([audit['caseId'], turn['id'], ';'.join(page['source']) if isinstance(page['source'], list) else page['source'], page['output'], page['role'], audit['publicFactAudit']['sourceLabelOccurrences'], audit['publicFactAudit']['outputLabelOccurrences']])
    (folder/'visual-inventory.csv').write_text(stream.getvalue())
    lines = ['# Visual-v2 public author inventory', '',
             'This is a deterministic author correspondence audit. It is not an independent blind reconstruction, and does not change frozen acceptance or inputBlindReview.', '',
             f"Cases: {summary['cases']}; turns: {summary['turns']}; PNG pages: {summary['pngPages']}. Source visible drawing labels: {before}; output labels: {after}; reduction: {before-after}.", '',
             f"Original delivered image formats: {summary['originalPNGPages']} PNG + {summary['originalSVGPages']} SVG; visual-v2: {summary['pngPages']} canonical PNG. Original DXFs retained: {summary['retainedOriginalDXFs']}. Total raster area: {summary['sourceRasterPixels']} → {summary['outputRasterPixels']} pixels.", '',
             'PNG is the delivered raster authority. SVG is authoring/checker material only. Original DXF is retained. Every source visible label is checked after exact filename substitution; public appendix JSON/TXT roundtrips are inherited from concise-v1. Geometry primitives, signed loads, section shape/roll/axes and staged clarification packets are regenerated solely from public sources.', '',
             '|Case|Turns|Source labels|Output labels|PNG pages|Minimum label px|', '|---|---:|---:|---:|---:|---:|']
    for audit in audits:
        sizes = [p['minimumFontPixels'] for p in audit['pages'] if p['minimumFontPixels'] is not None]
        lines.append(f"|{audit['caseId']}|{len(audit['turns'])}|{audit['publicFactAudit']['sourceLabelOccurrences']}|{audit['publicFactAudit']['outputLabelOccurrences']}|{len(audit['pages'])}|{min(sizes) if sizes else '—'}|")
    lines.extend(['', 'The JSON and CSV contain the per-turn source-to-output map. Raster font sizes and exact bytes are mechanical checks; manual raster inspection and independent blind reconstruction remain separate evidence.'])
    (folder/'visual-inventory.md').write_text('\n'.join(lines)+'\n')
    return summary


def generate(root, case_ids=None, inventory=True):
    root = Path(root)
    source_rows = [r for r in json.loads((root/'corpora/research-300/manifest.json').read_text())['cases'] if r['id'].startswith('MM-')]
    selected = set(case_ids or [r['id'] for r in source_rows])
    audits, records = [], []
    for row in sorted(source_rows, key=lambda r: r['id']):
        case_id = row['id']
        folder = root/EDITION_REL/case_id
        if case_id in selected:
            contract, row, public = read_case(root, case_id)
            bundle, files, audit = build_case(contract, row, public)
            files['input.json'] = json_text(bundle).encode()
            folder.mkdir(parents=True, exist_ok=True)
            for old in folder.rglob('*'):
                if old.is_file() and old.relative_to(folder).as_posix() not in files:
                    old.unlink()
            for name, raw in files.items():
                path = folder/name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
        if (folder/'input.json').exists():
            records.append(manifest_record(case_id, row, (folder/'input.json').read_bytes()))
            audits.append(json.loads((folder/'author-audit.json').read_text()))
    # Development case builds never publish a misleading partial manifest.
    complete = len(records) == len(source_rows)
    if complete:
        (root/EDITION_REL/'manifest.json').write_text(json_text({'schemaVersion': 1, 'edition': EDITION, 'cases': records}))
    summary = write_inventory(root, audits) if inventory else {'cases': len(audits)}
    summary['completeManifest'] = complete
    return summary


def main(argv=None):
    print('This historical public-input CLI has been retired. '
          'Use python3 scripts/research300/public_input_clean.py --check to validate '
          'the current inputs, or python3 scripts/research300/public_input_clean.py '
          'to build them.', file=sys.stderr)
    return 2


if __name__ == '__main__':
    sys.exit(main())
