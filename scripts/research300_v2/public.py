"""Write issued candidate inputs without references or future-state snapshots.

MM geometry, boundary masks and story elevations appear only in raster/DXF
documents. Tables of materials, sections, members and loads remain explicit.
"""
from copy import deepcopy
import csv
import io
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
DOFS = ['ux', 'uy', 'uz', 'rx', 'ry', 'rz']
REQUEST_FIELDS = {'id', 'selection', 'location', 'component', 'unit', 'path', 'operation', 'description'}
DERIVED_FIELDS = {'id', 'operation', 'operands', 'unit', 'tiePolicy'}


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as file:
        file.write(value if isinstance(value, str) else json.dumps(value, ensure_ascii=False,
                                                                 indent=2, allow_nan=False) + '\n')


def table(headers, rows):
    output = io.StringIO(newline='')
    writer = csv.writer(output, lineterminator='\n')
    writer.writerow(headers)
    writer.writerows(rows)
    return output.getvalue()


def number(value):
    return format(float(value), '.12g')


def font(size, mono=False):
    name = 'DejaVuSansMono.ttf' if mono else 'DejaVuSans.ttf'
    return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/' + name, size)


def mask(node):
    values = node.get('restraints')
    if not isinstance(values, list) or len(values) != 6 or any(type(value) is not bool for value in values):
        raise ValueError('Issued node masks must be six explicit booleans: ' + node['id'])
    return ''.join(str(int(value)) for value in values)


def geometry_pages(model, folder, case_id, multiview=False):
    """All three coordinates and all six boundary flags remain legible in tables."""
    nodes = model['nodes']
    if not 1 <= len(nodes) <= 96:
        raise ValueError('Reviewed raster layout supports 1–96 nodes')
    generated = []
    spatial = model['coordinate_system']['dimension'] == '3d'
    views = [('X', 'Z'), ('Y', 'Z'), ('X', 'Y')] if spatial or multiview else [('X', 'Z')]
    width, height = 2400, 1320
    picture = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(picture)
    draw.text((45, 25), case_id + ' | issued geometry overview', font=font(36), fill='#0f172a')
    draw.text((45, 88), 'Global Z-up; coordinates in m. Tables on following sheets define exact geometry and restraints.', font=font(23), fill='#334155')
    draw.text((45, 126), 'Projected crossings are not joints unless the member schedule shares the same node ID.', font=font(23), fill='#334155')
    lookup = {node['id']: node for node in nodes}
    panels = []
    gap = 40
    panel_width = (width - 2 * gap - (len(views) - 1) * gap) / len(views)
    for index, (horizontal, vertical) in enumerate(views):
        left, top = gap + index * (panel_width + gap), 215
        right, bottom = left + panel_width, height - 105
        draw.rectangle((left, top, right, bottom), outline='#cbd5e1', width=2)
        draw.text((left + 15, top + 12), horizontal + '-' + vertical + ' view', font=font(26), fill='#0f172a')
        xkey, ykey = horizontal.lower(), vertical.lower()
        xs, ys = [n[xkey] for n in nodes], [n[ykey] for n in nodes]
        xmin, xmax, ymin, ymax = min(xs), max(xs), min(ys), max(ys)
        scale = min((panel_width - 100) / max(xmax - xmin, 1), (bottom - top - 150) / max(ymax - ymin, 1))
        center_x, center_y = (left + right) / 2, (top + bottom + 45) / 2
        def xy(node):
            return center_x + (node[xkey] - (xmin + xmax) / 2) * scale, center_y - (node[ykey] - (ymin + ymax) / 2) * scale
        # Dense layouts retain full connectivity in members.csv. Representative
        # member labels avoid covering all node symbols with overlapping text.
        every = max(1, math.ceil(len(model['elements']) / (45 if len(views) == 1 else 18)))
        for j, element in enumerate(model['elements']):
            a, b = [xy(lookup[nid]) for nid in element['nodes']]
            draw.line((a, b), fill='#94a3b8' if element['type'] in ('truss', 'brace') else '#475569', width=3)
            if j % every == 0 and math.dist(a, b) > 25:
                draw.text(((a[0] + b[0]) / 2 + 3, (a[1] + b[1]) / 2 + 3), element['id'], font=font(13), fill='#64748b')
        positions = {}
        for node in nodes:
            x, y = xy(node)
            key = (round(x), round(y))
            positions.setdefault(key, []).append(node['id'])
            draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill='#0369a1')
        for (x, y), identifiers in positions.items():
            label = '/'.join(identifiers)
            if len(label) > 25:
                label = identifiers[0] + ' +' + str(len(identifiers) - 1)
            label_font = font(13 if len(views) > 1 else 17)
            label_x = max(left + 5, min(x + 6, right - label_font.getlength(label) - 5))
            draw.text((label_x, y - 17), label, font=label_font, fill='#075985')
        panels.append((left, top, right, bottom))
    draw.text((45, height - 62), 'Dense/overlapping labels: use the exact node sheets and the complete members.csv connectivity schedule.', font=font(22), fill='#334155')
    overview = folder / 'geometry-overview.png'
    picture.save(overview)
    generated.append(overview.name)
    node_width = max(14, max(len(str(n['id'])) for n in nodes))
    rows = [f"{n['id']:<{node_width}}  {number(n['x']):>13}  {number(n['y']):>13}  {number(n['z']):>13}  {mask(n):>6}  {n.get('story', '-') or '-'}" for n in nodes]
    header = f"{'NODE':<{node_width}}  {'X (m)':>13}  {'Y (m)':>13}  {'Z (m)':>13}  {'FIXED':>6}  STORY"
    fontsize = 28
    while max(font(fontsize, True).getlength(row) for row in [header, *rows]) > width - 120:
        fontsize -= 1
        if fontsize < 17:
            raise ValueError('Node identifiers exceed the reviewed sheet width')
    body_font = font(fontsize, True)
    pages = math.ceil(len(nodes) / 20)
    for page in range(pages):
        picture = Image.new('RGB', (width, 1520), 'white')
        draw = ImageDraw.Draw(picture)
        draw.text((50, 30), f'{case_id} | node geometry {page + 1}/{pages}', font=font(38), fill='#0f172a')
        draw.text((50, 95), 'FIXED bit order: ux uy uz rx ry rz. 1 = restrained; 0 = free. All coordinates are global, in metres.', font=font(25), fill='#334155')
        draw.text((50, 139), 'This is the issued geometry/boundary table. The model must be reconstructed from these sheets.', font=font(25), fill='#334155')
        draw.rectangle((42, 201, width - 42, 255), fill='#e2e8f0')
        draw.text((55, 214), header, font=body_font, fill='#0f172a')
        for i, row in enumerate(rows[page * 20:(page + 1) * 20]):
            y = 280 + i * 55
            if i % 2 == 0:
                draw.rectangle((42, y - 6, width - 42, y + 40), fill='#f8fafc')
            draw.text((55, y), row, font=body_font, fill='#0f172a')
        draw.text((50, 1450), 'Node mass, material/section properties and member endpoints are supplied in separate schedules.', font=font(24), fill='#334155')
        filename = f'geometry-nodes-{page + 1:02}.png'
        picture.save(folder / filename)
        generated.append(filename)
    if model.get('stories'):
        story_rows = [json.dumps(story, ensure_ascii=True, sort_keys=True) for story in model['stories']]
        story_sheets, lines = [], []
        for row in story_rows:
            chunks = [row[i:i + 132] for i in range(0, len(row), 132)] + ['']
            if len(chunks) > 26:
                raise ValueError('A story record exceeds the reviewed page layout')
            if len(lines) + len(chunks) > 26:
                story_sheets.append(lines)
                lines = []
            lines.extend(chunks)
        if lines:
            story_sheets.append(lines)
        for page, lines in enumerate(story_sheets):
            picture = Image.new('RGB', (width, 1250), 'white')
            draw = ImageDraw.Draw(picture)
            draw.text((50, 30), f'{case_id} | story schedule {page + 1}/{len(story_sheets)}', font=font(38), fill='#0f172a')
            draw.text((50, 92), 'Elevation and height in m. Reconstruct the stories list from the complete records below.', font=font(25), fill='#334155')
            y = 180
            for line in lines:
                draw.text((55, y), line, font=font(24, True), fill='#0f172a')
                y += 37
            filename = f'geometry-stories-{page + 1:02}.png'
            picture.save(folder / filename)
            generated.append(filename)
    return generated


def write_dxf(model, folder):
    """Small ASCII DXF with explicit geometry layers and human-readable labels."""
    output = []
    def codes(*pairs):
        for code, value in pairs:
            output.extend([str(code), str(value)])
    def text(layer, point, value, height=.15):
        codes((0, 'TEXT'), (8, layer), (10, number(point[0])), (20, number(point[1])),
              (30, number(point[2])), (40, height), (1, value))
    codes((0, 'SECTION'), (2, 'HEADER'), (9, '$ACADVER'), (1, 'AC1009'),
          (9, '$INSUNITS'), (70, 6), (0, 'ENDSEC'), (0, 'SECTION'), (2, 'ENTITIES'))
    lookup = {n['id']: n for n in model['nodes']}
    for element in model['elements']:
        a, b = [lookup[nid] for nid in element['nodes']]
        codes((0, 'LINE'), (8, 'STRUCT'), (10, number(a['x'])), (20, number(a['y'])), (30, number(a['z'])),
              (11, number(b['x'])), (21, number(b['y'])), (31, number(b['z'])))
        text('MEMBER_ID', [(a[k] + b[k]) / 2 for k in ('x', 'y', 'z')], element['id'])
    for node in model['nodes']:
        point = [node[k] for k in ('x', 'y', 'z')]
        codes((0, 'POINT'), (8, 'NODE'), (10, number(point[0])), (20, number(point[1])), (30, number(point[2])))
        text('NODE_ID', point, node['id'])
        text('RESTRAINT', point, node['id'] + ' FIXED=' + mask(node))
        text('NODE_COORD', point, node['id'] + ' XYZ_m=' + ','.join(number(v) for v in point))
        if node.get('story'):
            text('NODE_STORY', point, node['id'] + ' STORY=' + node['story'])
    left = min(n['x'] for n in model['nodes'])
    y = min(n['y'] for n in model['nodes'])
    top = max(n['z'] for n in model['nodes']) + 3
    text('DRAWING_NOTE', [left, y, top], 'SI metres; global XYZ, Z-up; FIXED order ux uy uz rx ry rz; 1=fixed,0=free.', .2)
    for i, story in enumerate(model.get('stories', [])):
        text('STORY', [left, y, top + 1 + i * .5], json.dumps(story, sort_keys=True, ensure_ascii=True), .2)
    codes((0, 'ENDSEC'), (0, 'EOF'))
    write(folder / 'geometry.dxf', '\n'.join(output) + '\n')
    write(folder / 'drawing-layers.json', {'format': 'ASCII DXF', 'lengthUnit': 'm', 'coordinateFrame': 'global Z-up',
        'STRUCT': 'Only these LINE entities are structural members. Exact member endpoint IDs are in members.csv.',
        'NODE': 'POINT entities are issued physical nodes.', 'NODE_ID': 'TEXT at node coordinates identifies each node.',
        'RESTRAINT': 'TEXT NODE FIXED=xxxxxx; bits ux,uy,uz,rx,ry,rz; 1 restrained, 0 free.',
        'NODE_COORD': 'Readable exact global XYZ coordinate text.', 'NODE_STORY': 'Node story IDs.',
        'STORY': 'Full story records; elevation/height in m.', 'MEMBER_ID': 'Member labels at projected midpoints.',
        'note': 'Other text is annotation. Intersecting LINE entities are not automatically connected.'})


def parameters(folder, values):
    values = deepcopy(values)
    if 'groundMotion' in values:
        motion = values.pop('groundMotion')
        write(folder / 'excitation.csv', table(['sample', 'acceleration'], enumerate(motion)))
        values['groundMotionFile'] = 'excitation.csv'
    write(folder / 'analysis-parameters.json', values)


def write_public(folder: Path, case: dict, turn: dict, ordinal: int, ref: dict) -> None:
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    if any(folder.iterdir()):
        raise FileExistsError('Public turn directory must be fresh')
    if ordinal < 1:
        raise ValueError('ordinal is one-based')
    public = {'caseId': case['id'], 'turnId': 't' + str(ordinal), 'family': case['family'],
        'title': case['title'], 'designLevel': case.get('level'), 'engine': case.get('engine', ref.get('engine', 'OpenSees')),
        'analysis': turn['kind'], 'instruction': turn['instruction'],
        'requests': [{key: value for key, value in q.items() if key in REQUEST_FIELDS} for q in ref.get('requests', [])],
        'derived': [{key: value for key, value in q.items() if key in DERIVED_FIELDS} for q in ref.get('derived', [])],
        'reportIds': ref.get('reportIds', [q['id'] for q in ref.get('requests', [])]),
        'requireShapes': bool(ref.get('requireShapes', False)), 'sourceId': case.get('sourceId')}
    if ref.get('requireFreshExecution') is not None:
        public['requireFreshExecution'] = bool(ref['requireFreshExecution'])
    for name in ('constraint', 'schemeSelections'):
        if turn.get(name) is not None:
            public[name] = turn[name]
    basis = [value for value in [case.get('authoringBasis'), turn.get('authoringBasis')] if value]
    if basis:
        public['authoringBasis'] = basis
    if ordinal == 1:
        model = turn['model']
        write(folder / 'model-convention.json', {key: model[key] for key in ['schema_version', 'unit_system', 'coordinate_system']})
        visual = case['family'] == 'MM'
        if visual:
            mode = case.get('inputMode', 'png-tables')
            if mode == 'dxf':
                write_dxf(model, folder)
            else:
                geometry_pages(model, folder, case['id'], mode == 'multiview')
        else:
            write(folder / 'nodes.csv', table(['node', 'x_m', 'y_m', 'z_m', *[key + '_fixed' for key in DOFS], 'mass_tonne', 'story'],
                [[n['id'], n['x'], n['y'], n['z'], *map(int, n['restraints']), n.get('mass', ''), n.get('story', '')] for n in model['nodes']]))
            if model.get('stories'):
                write(folder / 'stories.json', model['stories'])
        write(folder / 'members.csv', table(['member', 'i', 'j', 'kind', 'material', 'section', 'roll_deg', 'local_bending_releases', 'offsets', 'story'],
            [[e['id'], *e['nodes'], e['type'], e['material'], e['section'], e.get('rotation_angle', 0),
              json.dumps(e.get('releases', {}), separators=(',', ':')), json.dumps(e.get('offsets', {}), separators=(',', ':')),
              e.get('story', '')] for e in model['elements']]))
        write(folder / 'materials.csv', table(['id', 'name', 'type', 'E_MPa', 'G_MPa', 'nu', 'rho_kg_per_m3'],
            [[m['id'], m.get('name', ''), m.get('type', ''), m['E'], m.get('G', ''), m.get('nu', ''), m.get('rho', '')] for m in model['materials']]))
        write(folder / 'materials.json', model['materials'])
        for filename, key in [('sections.json', 'sections'), ('combinations.json', 'load_combinations'),
                              ('analysis-control.json', 'analysis_control')]:
            write(folder / filename, model.get(key, []))
        if case.get('loadRecipe') is not None:
            write(folder / 'load-recipe.json', case['loadRecipe'])
            public['loadInput'] = 'Build load_cases from load-recipe.json. Convert surface pressure to member line vectors exactly once.'
        else:
            write(folder / 'loads.json', model['load_cases'])
        if model.get('metadata'):
            write(folder / 'metadata.json', model['metadata'])
        if any('mass' in n for n in model['nodes']):
            write(folder / 'mass.csv', table(['node', 'mass_tonne'], [[n['id'], n.get('mass', '')] for n in model['nodes']]))
        node_keys = {'id', 'x', 'y', 'z', 'restraints', 'mass', 'story', 'name'}
        node_extra = {n['id']: {k: v for k, v in n.items() if k not in node_keys} for n in model['nodes']}
        node_extra = {k: v for k, v in node_extra.items() if v}
        if node_extra:
            write(folder / 'node-extra.json', node_extra)
        element_keys = {'id', 'nodes', 'type', 'material', 'section', 'rotation_angle', 'releases', 'offsets', 'story', 'name'}
        element_extra = {e['id']: {k: v for k, v in e.items() if k not in element_keys} for e in model['elements']}
        element_extra = {k: v for k, v in element_extra.items() if v}
        if element_extra:
            write(folder / 'element-extra.json', element_extra)
        root_keys = {'schema_version', 'unit_system', 'coordinate_system', 'nodes', 'elements', 'materials', 'sections',
                     'load_cases', 'load_combinations', 'analysis_control', 'metadata', 'stories'}
        extras = {k: v for k, v in model.items() if k not in root_keys}
        if extras:
            write(folder / 'model-extra.json', extras)
        schemes = turn.get('schemes', case.get('schemes'))
        if schemes:
            allowed = {'id', 'name', 'section', 'sectionId', 'b', 'h', 'widthM', 'depthM', 'properties', 'shape', 'description'}
            write(folder / 'schemes.json', [{k: v for k, v in scheme.items() if k in allowed} for scheme in schemes])
        if case.get('sourceBasis') is not None:
            write(folder / 'source-basis.json', case['sourceBasis'])
        if visual and turn.get('suspectModel') is not None:
            raise ValueError('MM cannot expose a full suspect model that bypasses geometry reconstruction')
        if turn.get('suspectModel') is not None:
            write(folder / 'model-to-review.json', turn['suspectModel'])
        if turn.get('suspectExcerpt') is not None:
            def geometry_keys(value):
                if isinstance(value, dict):
                    return bool(set(value) & {'nodes', 'x', 'y', 'z', 'restraints'}) or any(geometry_keys(v) for v in value.values())
                return isinstance(value, list) and any(geometry_keys(v) for v in value)
            if visual and geometry_keys(turn['suspectExcerpt']):
                raise ValueError('MM review excerpts must not disclose geometry or boundary masks')
            write(folder / 'review-excerpt.json', turn['suspectExcerpt'])
        write(folder / 'tool-contract.md', (HERE / 'tool-contract.md').read_text())
    else:
        if turn.get('changeOrder') is not None:
            write(folder / 'change-order.json', turn['changeOrder'])
        public['interactionRule'] = 'Apply only this issued change order to the last confirmed state; retain all other prior inputs. Initial restores refer to t1.'
    if turn.get('parameters') is not None:
        parameters(folder, turn['parameters'])
    public['attachments'] = sorted(p.name for p in folder.iterdir())
    write(folder / 'task.json', public)
