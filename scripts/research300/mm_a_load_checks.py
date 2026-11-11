"""Focused RI-005/006 checks of the actual MM-A public attachments.

Uses ezdxf's font-derived TEXT extents, rather than the author's placement
estimates. These checks supplement inspection of rendered DXFs; they are not
blind reconstruction, numerical validation, or independent case acceptance.
All rejection fixtures are edited in memory and never overwrite case files.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import re

import ezdxf
from ezdxf import bbox
from ezdxf.math import Vec2
from ezdxf.math.clipping import ClippingRect2d

ROOT = Path(__file__).resolve().parents[2]
CASES = ROOT / 'corpora/research-300/cases'
COMPONENTS = ('fx', 'fy', 'fz', 'mx', 'my', 'mz', 'wx', 'wy', 'wz')
CALLOUT = re.compile(r'^(\S+)/(\S+) @ (node|member) (\S+): (.+)$')


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def load_convention(text, locale):
    """Require the distinct force, moment and line-load meanings in public text."""
    marker = 'Load components' if locale == 'en' else '荷载分量'
    notes = [line for line in text.splitlines() if line.startswith(marker)]
    check(len(notes) == 1, 'missing or duplicated common public load convention')
    note = notes[0]
    if locale == 'en':
        requirements = {
            'global load frame': r'Load components use global XYZ axes:',
            'concentrated-force unit': r'fx/fy/fz are concentrated forces in kN;',
            'nodal-moment unit and sense': r'mx/my/mz are nodal moments in kN\*m \(right-hand rule\);',
            'distributed-force unit and actual-length basis': r'wx/wy/wz are distributed forces in kN/m per actual member length, not projected length\.',
            'negative global Z sense': r'A negative z component acts along global -Z\.',
        }
    else:
        requirements = {
            'global load frame': r'荷载分量按全局 XYZ 轴：',
            'concentrated-force unit': r'fx/fy/fz 为集中力，单位 kN；',
            'nodal-moment unit and sense': r'mx/my/mz 为节点力矩，单位 kN\*m（右手定则）；',
            'distributed-force unit and actual-length basis': r'wx/wy/wz 为线分布力，单位 kN/m，按杆件实际长度计，不按投影长度计。',
            'negative global Z sense': r'z 分量为负表示沿全局 -Z。',
        }
    for meaning, pattern in requirements.items():
        check(re.search(pattern, note) is not None, f'public load convention omits or changes {meaning}')
    return note


def slope_basis(text, locale):
    if locale == 'en':
        pattern = r'Both roof slopes: global -Z, 6 kN/m per actual slope length\.'
    else:
        pattern = r'两坡梁线载均沿全局 -Z，按实际坡长计 6 kN/m。'
    check(re.search(pattern, text) is not None,
          'MM-043 needs both slopes, global -Z and 6 kN/m per actual slope length')


def box_records(doc):
    for entity in doc.modelspace().query('TEXT'):
        if not entity.dxf.text.strip():
            continue
        extent = bbox.extents([entity])
        check(extent.has_data, f'no font extent for {entity.dxf.text!r}')
        yield (extent.extmin.x, extent.extmin.y, extent.extmax.x, extent.extmax.y), entity


def text_boxes(doc):
    """Reject overlapping real font extents, including differing insert points."""
    boxes = []
    for current, entity in box_records(doc):
        for other, previous in boxes:
            overlap_x = min(current[2], other[2]) - max(current[0], other[0])
            overlap_y = min(current[3], other[3]) - max(current[1], other[1])
            check(overlap_x <= 1e-6 or overlap_y <= 1e-6,
                  f'DXF text overlap: {previous!r} / {entity.dxf.text!r}')
        boxes.append((current, entity.dxf.text))
    return len(boxes)


def geometry_clearance(doc):
    """Check actual font boxes against every physical/context/annotation stroke."""
    lines = list(doc.modelspace().query('LINE'))
    circles = list(doc.modelspace().query('CIRCLE'))
    for (left, bottom, right, top), text in box_records(doc):
        # A microscopic inset distinguishes an edge touch from a through-stroke.
        clipper = ClippingRect2d(Vec2(left + 1e-7, bottom + 1e-7), Vec2(right - 1e-7, top - 1e-7))
        for line in lines:
            pieces = clipper.clip_line(Vec2(line.dxf.start), Vec2(line.dxf.end))
            check(not any(a.distance(b) > 1e-7 for a, b in pieces),
                  f'{line.dxf.layer} LINE crosses caption {text.dxf.text!r}')
        for circle in circles:
            x, y = circle.dxf.center.x, circle.dxf.center.y
            nearest = math.hypot(max(left - x, 0, x - right), max(bottom - y, 0, y - top))
            farthest = max(math.hypot(a - x, b - y) for a in (left, right) for b in (bottom, top))
            check(not (nearest + 1e-7 < circle.dxf.radius < farthest - 1e-7),
                  f'{circle.dxf.layer} CIRCLE crosses caption {text.dxf.text!r}')
    return len(lines), len(circles)


def expected_loads(model):
    nodes = {n['id']: n for n in model['nodes']}
    members = {e['id']: e for e in model['elements']}
    result = {}
    for case in model['load_cases']:
        for load in case['loads']:
            if 'node' in load:
                target_id = load['node']
                node = nodes[target_id]
                target = (node['x'], node['z'])
                kind = 'node'
            else:
                target_id = load['element']
                a, b = [nodes[n] for n in members[target_id]['nodes']]
                length = math.dist([a[k] for k in 'xyz'], [b[k] for k in 'xyz'])
                distance = (load.get('start', 0) + load.get('end', length)) / 2
                target = tuple(a[k] + distance / length * (b[k] - a[k]) for k in ('x', 'z'))
                kind = 'member'
            values = {k: load[k] for k in COMPONENTS if load.get(k)}
            result[(case['id'], load['id'])] = (kind, target_id, target, values)
    return result


def matching_leaders(doc, label, target):
    """Find a straight leader chain with only caption-related gaps.

    Glyph extents are used for collision rejection. Gap allowance is deliberately
    larger, so viewers with wider substituted fonts may reserve an ASCII cell
    per character without weakening the actual through-caption stroke check.
    """
    insertion = (label.dxf.insert.x, label.dxf.insert.y)
    lines = list(doc.modelspace().query('LINE[layer=="LOADS"]'))
    candidates = []
    for line in lines:
        ends = [(line.dxf.start.x, line.dxf.start.y), (line.dxf.end.x, line.dxf.end.y)]
        candidates.extend(point for point in ends if math.dist(point, insertion) <= .9 * label.dxf.height)
    for origin in candidates:
        dx, dy = target[0] - origin[0], target[1] - origin[1]
        squared = dx * dx + dy * dy
        if squared < 1e-10:
            continue
        def parameter(point):
            return ((point[0] - origin[0]) * dx + (point[1] - origin[1]) * dy) / squared
        segments = []
        for line in lines:
            points = [(line.dxf.start.x, line.dxf.start.y), (line.dxf.end.x, line.dxf.end.y)]
            if all(abs((p[0] - origin[0]) * dy - (p[1] - origin[1]) * dx) / math.sqrt(squared) < 1e-8 for p in points):
                a, b = sorted(parameter(p) for p in points)
                if a >= -1e-8 and b <= 1 + 1e-8:
                    segments.append((a, b, line))
        if not segments or min(a for a, _, _ in segments) > 1e-8 or max(b for _, b, _ in segments) < 1 - 1e-8:
            continue
        covered = [(a, b) for a, b, _ in segments]
        for (left, bottom, right, top), caption in box_records(doc):
            height = caption.dxf.height
            right = max(right, caption.dxf.insert.x + len(caption.dxf.text) * height)
            clipper = ClippingRect2d(Vec2(left - .5 * height, bottom - .5 * height),
                                     Vec2(right + .5 * height, top + .5 * height))
            for a, b in clipper.clip_line(Vec2(origin), Vec2(target)):
                covered.append(tuple(sorted((parameter(a), parameter(b)))))
        end = 0
        for a, b in sorted(covered):
            if a > end + 1e-8:
                break
            end = max(end, b)
        if end >= 1 - 1e-8:
            return [line for _, _, line in segments]
    return []


def load_associations(doc, model):
    expected = expected_loads(model)
    observed = {}
    for entity in doc.modelspace().query('TEXT[layer=="LOADS"]'):
        match = CALLOUT.fullmatch(entity.dxf.text)
        if match is None:
            continue
        case_id, load_id, kind, target_id, components = match.groups()
        identity = (case_id, load_id)
        check(identity not in observed, f'duplicate public load callout {identity}')
        observed[identity] = entity
        check(identity in expected, f'unknown public load callout {identity}')
        want_kind, want_id, target, want_values = expected[identity]
        check((kind, target_id) == (want_kind, want_id), f'wrong node/member identity for {identity}')
        tokens = components.split(', ')
        values = {}
        for token in tokens:
            pair = re.fullmatch(r'(fx|fy|fz|mx|my|mz|wx|wy|wz)=(-?\d+(?:\.\d+)?(?:e[+-]?\d+)?)', token)
            check(pair is not None, f'invalid component in {identity}: {token}')
            check(pair[1] not in values, f'duplicate component in {identity}')
            values[pair[1]] = float(pair[2])
        check(values.keys() == want_values.keys(), f'missing/extra public load component in {identity}')
        check(all(math.isclose(values[k], v, rel_tol=1e-8, abs_tol=1e-9) for k, v in want_values.items()),
              f'public load magnitude/sign differs for {identity}')
        check(matching_leaders(doc, entity, target),
              f'load callout needs a collinear leader chain to its actual {kind}: {identity}')
    check(observed.keys() == expected.keys(), 'missing or malformed explicit node/member load callout')
    return len(observed)


def reject(name, operation, controls):
    try:
        operation()
    except AssertionError as error:
        controls.append({'name': name, 'rejected': True, 'reason': str(error)})
    else:
        raise AssertionError(f'negative control unexpectedly passed: {name}')


def self_test(cases):
    controls = []
    for locale in ('en', 'zh'):
        sample = next(path for path in cases if json.loads((path / 'contract.json').read_text())['locale'] == locale)
        note = load_convention((sample / 'properties.txt').read_text(), locale)
        replacements = [
            ('frame', 'global XYZ', 'local XYZ'),
            ('line unit', 'kN/m per actual', 'kN per actual'),
            ('projected basis', 'actual member length, not projected length', 'projected member length, not actual length'),
            ('point-force unit', 'forces in kN;', 'forces in kN/m;'),
            ('moment unit', 'moments in kN*m', 'moments in kN'),
            ('negative Z', 'global -Z', 'global +Z'),
        ] if locale == 'en' else [
            ('frame', '全局 XYZ', '局部 XYZ'),
            ('line unit', '单位 kN/m', '单位 kN'),
            ('projected basis', '按杆件实际长度计，不按投影长度计', '按杆件投影长度计，不按实际长度计'),
            ('point-force unit', '集中力，单位 kN；', '集中力，单位 kN/m；'),
            ('moment unit', '节点力矩，单位 kN*m', '节点力矩，单位 kN'),
            ('negative Z', '全局 -Z', '全局 +Z'),
        ]
        reject(f'{locale}: removed common load convention', lambda: load_convention('', locale), controls)
        for name, before, after in replacements:
            check(before in note, f'negative fixture not applied: {name}')
            changed = note.replace(before, after)
            reject(f'{locale}: wrong {name}', lambda: load_convention(changed, locale), controls)

    case = next(path for path in cases if path.name == 'MM-013')
    model = json.loads((case / 'model-state-1.json').read_text())
    # Exact text/height/insertion values recorded by independent finding RI-005.
    # Isolate the pair so another annotation cannot mask the intended rejection.
    doc = ezdxf.new()
    for original in ('D/D-2 @ b2: wz=-12', 'D/D-5 @ n1: fz=-20'):
        doc.modelspace().add_text(original, dxfattribs={'height': .15, 'insert': (3.1, .65)})
    reject('MM-013: original D-2/D-5 coincident insertion', lambda: text_boxes(doc), controls)
    # A second fixture catches glyph overlap even when insertion points differ.
    doc = ezdxf.new()
    doc.modelspace().add_text('D/D-2 @ b2: wz=-12', dxfattribs={'height': .15, 'insert': (3.1, .65)})
    doc.modelspace().add_text('D/D-5 @ n1: fz=-20', dxfattribs={'height': .15, 'insert': (3.2, .65)})
    reject('DXF: partial text overlap at distinct insertions', lambda: text_boxes(doc), controls)

    for change in ('remove', 'wrong target', 'wrong identity'):
        doc = ezdxf.readfile(case / 'input.dxf')
        label = next(entity for entity in doc.modelspace().query('TEXT[layer=="LOADS"]')
                     if entity.dxf.text.startswith('D/D-2 @'))
        target = expected_loads(model)[('D', 'D-2')][2]
        leaders = matching_leaders(doc, label, target)
        check(leaders, 'positive fixture lacks leader')
        if change == 'remove':
            for line in leaders:
                doc.modelspace().delete_entity(line)
        elif change == 'wrong target':
            line = next(line for line in leaders if min(math.dist((line.dxf.end.x, line.dxf.end.y), target),
                                                       math.dist((line.dxf.start.x, line.dxf.start.y), target)) < 1e-8)
            if math.dist((line.dxf.end.x, line.dxf.end.y), target) < 1e-8:
                line.dxf.end = (target[0] + .314, target[1] + .271, 0)
            else:
                line.dxf.start = (target[0] + .314, target[1] + .271, 0)
        else:
            label.dxf.text = label.dxf.text.replace('@ member b2:', '@ node n1:')
        reject(f'MM-013: {change} leader/association', lambda: load_associations(doc, model), controls)

    for layer in ('LOADS', 'STRUCTURE', 'A_WALL'):
        doc = ezdxf.readfile(case / 'input.dxf')
        box, _ = next((box, text) for box, text in box_records(doc) if text.dxf.text.startswith('D/D-2 @'))
        left, bottom, right, top = box
        y = (bottom + top) / 2
        doc.modelspace().add_line((left - .1, y), (right + .1, y), dxfattribs={'layer': layer})
        reject(f'DXF: {layer} stroke through another caption', lambda: geometry_clearance(doc), controls)
    doc = ezdxf.readfile(case / 'input.dxf')
    box, _ = next(box_records(doc))
    left, bottom, right, top = box
    doc.modelspace().add_circle((left, (bottom + top) / 2), .05, dxfattribs={'layer': 'SUPPORTS'})
    reject('DXF: support circle through caption', lambda: geometry_clearance(doc), controls)

    case43 = next(path for path in cases if path.name == 'MM-043')
    text = (case43 / 'properties.txt').read_text()
    reject('MM-043: removed explicit slope note',
           lambda: slope_basis(text.replace('两坡梁线载均沿全局 -Z，按实际坡长计 6 kN/m。', ''), 'zh'), controls)
    doc = ezdxf.readfile(case43 / 'input.dxf')
    note = '\n'.join(entity.dxf.text for entity in doc.modelspace().query('TEXT'))
    reject('MM-043: DXF projected slope length',
           lambda: slope_basis(note.replace('actual slope length', 'projected slope length'), 'en'), controls)
    return controls


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases-root', type=Path, default=CASES)
    parser.add_argument('--self-test', action='store_true')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    cases = [args.cases_root / f'MM-{i:03d}' for i in range(1, 51)]
    report = {'scope': 'MM-A RI-005/006 public attachment checks; not case acceptance',
              'cases': 0, 'appendices': 0, 'dxf': [], 'sha256': {}}
    for case in cases:
        contract = json.loads((case / 'contract.json').read_text())
        for relative in contract['attachments']:
            path = case / relative
            if path.name.startswith('properties') and path.suffix == '.txt':
                text = path.read_text()
                load_convention(text, contract['locale'])
                if case.name == 'MM-043':
                    slope_basis(text, contract['locale'])
                report['appendices'] += 1
            elif path.suffix == '.dxf':
                doc = ezdxf.readfile(path)
                model = json.loads((case / 'model-state-1.json').read_text())
                boxes = text_boxes(doc)
                lines, circles = geometry_clearance(doc)
                loads = load_associations(doc, model)
                if case.name == 'MM-043':
                    slope_basis('\n'.join(t.dxf.text for t in doc.modelspace().query('TEXT')), 'en')
                report['dxf'].append({'case': case.name, 'textBoxes': boxes, 'clearLines': lines,
                                      'clearCircles': circles, 'loadCallouts': loads})
            else:
                continue
            report['sha256'][str(path.relative_to(args.cases_root))] = hashlib.sha256(path.read_bytes()).hexdigest()
        report['cases'] += 1
    if args.self_test:
        report['rejectionControls'] = self_test(cases)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(f"PASS {report['cases']} cases, {report['appendices']} public appendices, "
          f"{len(report['dxf'])} actual DXFs, {sum(d['loadCallouts'] for d in report['dxf'])} load associations; "
          f"{len(report.get('rejectionControls', []))} rejection controls")


if __name__ == '__main__':
    main()
