#!/usr/bin/env python3
"""Author an isolated section-diversity edition; never rewrite the scored corpus.

Similarity transforms preserve shape, principal axes, section/stiffness ratios,
and every interaction update. Only author-completed section sizes may vary.
The committed plan is independent of candidate answers, scores and failures.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
EDITION = 'section-diversity-v1'
PALETTE = [80, 84, 88, 92, 96, 104, 108, 112, 116, 120]
POWERS = {'A': 2, 'Asy': 2, 'Asz': 2, 'Iy': 4, 'Iz': 4, 'J': 4}
NUMBER = r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?'
# Deliberate source review, not runtime keyword classification. Fixed dimensions
# in source plans/turns and named or asymmetric sections remain control cases.
FIXED = {
    'INT-069': 'Source specifies floor/roof/column dimensions.',
    'INT-071': 'Source specifies outer/inner columns and beam dimensions.',
    'INT-074': 'Source specifies the two transposed rectangular columns.',
    'INT-077': 'Source specifies initial and revised column dimensions.',
    'INT-083': 'Source specifies corner and other column dimensions.',
    'INT-095': 'Source explicitly retains a 400 x 400 mm column.',
    'INT-096': 'Source specifies lower/upper column dimensions.',
    'INT-097': 'Source specifies the HW300 section.',
    'INT-098': 'Clarification explicitly fixes B=300 mm and H=500 mm.',
    'STD-069': 'Source specifies column and beam dimensions.',
    'STD-070': 'Source specifies column and beam dimensions.',
    'STD-071': 'Source specifies column and beam dimensions.',
    'STD-077': 'Source specifies lower and upper column dimensions.',
    'STD-095': 'Source specifies the column dimensions.',
    'STD-096': 'Source specifies the column dimensions.',
    'STD-097': 'Source specifies the HW300 section.',
    'STD-098': 'Keep the independently authored asymmetric welded section as a control.',
    'MM-097': 'Keep the named H-section and its detailed drawing as a control.',
    'MM-098': 'Keep the asymmetric section and its detailed drawing as a control.',
    **{f'MM-{i:03d}': 'Source explicitly specifies rectangular beam/column dimensions.'
       for i in [*range(69, 79), 83, 84, 95, 96]},
}
SOURCE_CONSTRAINT_CORRECTIONS = {
    'INT-070': 'The original model.loadKey explicitly fixes 500 x 500 mm columns and 300 x 600 mm beams.'
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encoded(value))


def used_sections(model):
    used = {e['section'] for e in model['elements']}
    return [s for s in model['sections'] if s['id'] in used]


def scale_number(value, percent, power, digits=15):
    require(type(value) in (int, float) and math.isfinite(value) and value > 0,
            'Section dimensions/properties must be finite and positive')
    result = Decimal(str(value)) * (Decimal(percent) / 100) ** power
    return float(format(result, f'.{digits}g'))


def scale_section(section, percent, digits=15):
    result = deepcopy(section)
    props = result['properties']
    require(set(props) <= set(POWERS), f'Unreviewed section property: {set(props) - set(POWERS)}')
    for name, value in props.items():
        props[name] = scale_number(value, percent, POWERS[name], digits)
    shape = result.get('shape')
    if shape:
        require(shape.get('kind') == 'rectangular' and set(shape) == {'kind', 'B', 'H'},
                f'Unreviewed shape: {shape}')
        shape.update({k: scale_number(shape[k], percent, 1, digits) for k in ('B', 'H')})
    return result


def scale_model(model, percent):
    if percent == 100:
        return deepcopy(model)
    result = deepcopy(model)
    result['sections'] = [scale_section(s, percent) for s in result['sections']]
    return result


def make_plan(root):
    root = Path(root)
    manifest = read(root / 'corpora/research-300/manifest.json')
    strata = defaultdict(list)
    rows = []
    for base in manifest['cases']:
        folder = root / 'corpora/research-300/cases' / base['id']
        contract = read(folder / 'contract.json')
        models = [read(folder / n) for n in contract['modelStates']]
        roles = sorted({e['type'] for m in models for e in m['elements']})
        row = {'caseId': base['id'], 'baseSourceHash': base['sourceHash'],
               'engine': contract['plannedEngine'], 'family': base['id'].split('-')[0],
               'elementRoles': roles, 'percent': 100,
               'reason': FIXED.get(base['id'], 'Author-completed section dimensions; preserve all source requirements.')}
        if base['id'] not in FIXED:
            # Exercise all shapes before publishing an assignment; unknowns stop
            # the build instead of silently becoming new control cases.
            for model in models:
                scale_model(model, PALETTE[0])
            strata[(row['family'], row['engine'])].append(row)
        rows.append(row)
    # Balance each family/engine separately. A stable hash breaks adjacent case
    # number/template correlations; answers and solver outcomes are never read.
    for key, group in sorted(strata.items()):
        group.sort(key=lambda row: sha((EDITION + '/' + row['caseId']).encode()))
        offset = int(sha('/'.join(key).encode())[:8], 16) % len(PALETTE)
        for index, row in enumerate(group):
            row['percent'] = PALETTE[(index + offset) % len(PALETTE)]
    return {'schemaVersion': 1, 'edition': EDITION,
            'baseManifestSha256': sha((root / 'corpora/research-300/manifest.json').read_bytes()),
            'status': 'authored-variant-not-a-replacement-for-historical-scores',
            'policy': {'linearScalePercent': PALETTE, 'publicSignificantDigits': 8,
                       'maximumDisplayRelativeError': 5e-8,
                       'scalePowers': POWERS, 'preserveWithinCaseSimilarity': True,
                       'maximumJCaseFraction': .15, 'maximumJFamilyFraction': .20,
                       'maximumJEngineFraction': .25,
                       'candidateResultsUsed': False},
            'cases': sorted(rows, key=lambda row: row['caseId'])}


def transform_json(value, percent):
    """Transform only public section records, without consulting hidden states.

    Multipliers are dimensionless: mixed mm2/mm4 and SI tables retain their units.
    Conflicting initial data and future releases retain their original schedule.
    """
    if isinstance(value, dict):
        if isinstance(value.get('properties'), dict) and 'A' in value['properties']:
            if percent == 100:
                result = deepcopy(value)
                result['properties'] = {k: float(format(v, '.8g')) for k, v in value['properties'].items()}
                return result
            return scale_section(value, percent, 8)
        return {k: transform_json(v, percent) for k, v in value.items()}
    if isinstance(value, list):
        return [transform_json(v, percent) for v in value]
    if isinstance(value, str):
        return transform_prose(value, percent)
    return value


def corrected_plan(plan):
    """Preserve the published assignments except a newly found source constraint.

    The first plan remains immutable evidence. Do not reshuffle other cases
    after candidate execution; the correction depends only on source wording.
    """
    result = deepcopy(plan)
    result['sourceConstraintCorrection'] = {
        'basePlanSha256': sha(encoded(plan)), 'candidateResultsUsed': False,
        'cases': SOURCE_CONSTRAINT_CORRECTIONS,
        'assignmentPolicy': 'Retain every other published assignment; maximum per-stratum palette imbalance is two.'}
    for row in result['cases']:
        if row['caseId'] in SOURCE_CONSTRAINT_CORRECTIONS:
            row['percent'] = 100
            row['reason'] = SOURCE_CONSTRAINT_CORRECTIONS[row['caseId']]
    return result


def transform_prose(text, percent):
    # Reviewed, narrowly dimensional public authoring forms, not global numeric
    # substitution. Coordinates, forces, material moduli and IDs stay untouched.
    def dim(match):
        return match[1] + format(scale_number(float(match[2]), percent, 1, 8), '.8g') + match[3]
    text = re.sub(r'(\b[BH]\s*=\s*)(' + NUMBER + r')(\s*(?:mm|;|$))', dim, text, flags=re.M)
    def pair(match):
        a, sep, b = match[1], match[2], match[3]
        return (format(scale_number(float(a), percent, 1, 8), '.8g') + sep +
                format(scale_number(float(b), percent, 1, 8), '.8g') + match[4])
    # Includes a shared unit in e.g. C1/B1 = 350x500/250x450 mm.
    text = re.sub(r'(' + NUMBER + r')(\s*(?:[x×]|by)\s*)(' + NUMBER + r')()'
                  r'(?=(?:\s*/\s*' + NUMBER + r'\s*(?:[x×]|by)\s*' + NUMBER + r')*\s*mm)', pair, text)
    text = re.sub(r'(' + NUMBER + r')(\s*[x×]\s*)(' + NUMBER + r')(\s*m(?=实心(?:方形|矩形)))', pair, text)
    text = re.sub(r'(' + NUMBER + r')(\s*m(?: wide)? by\s*)(' + NUMBER + r')(\s*m(?: deep)?)', pair, text)
    text = re.sub(r'(\b[A-Za-z][\w-]* is (?:a )?)(' + NUMBER + r')( by )(' + NUMBER + r')( m (?:solid )?(?:square|rectangle))',
                  lambda m: m[1]+format(scale_number(float(m[2]),percent,1,8),'.8g')+m[3]+
                  format(scale_number(float(m[4]),percent,1,8),'.8g')+m[5], text)
    text = re.sub(r'(\bC[\w-]*\s+(?:is|are|=)\s*)(' + NUMBER + r')( m square)', dim, text)
    text = re.sub(r'((?:梁B1|屋面B1|连系梁T1)宽)(' + NUMBER + r')(m、?高)(' + NUMBER + r')(m)',
                  lambda m:m[1]+format(scale_number(float(m[2]),percent,1,8),'.8g')+m[3]+
                  format(scale_number(float(m[4]),percent,1,8),'.8g')+m[5],text)
    text = re.sub(r'(柱C1为)(' + NUMBER + r')(m方形)', dim, text)
    text = re.sub(r'(\b[A-Za-z][\w-]* area (?:is|=)\s*)(' + NUMBER + r')(\s*(?:mm|m)(?:\^2|[2²])(?![A-Za-z0-9]))',
                  lambda m:m[1]+format(scale_number(float(m[2]),percent,2,8),'.8g')+m[3],text)
    text = re.sub(r'((?:轴向|截面)面积\s*)(' + NUMBER + r')(\s*m[²2])',
                  lambda m:m[1]+format(scale_number(float(m[2]),percent,2,8),'.8g')+m[3],text)
    text = re.sub(r'(?<![A-Za-z0-9_])(A\d+\s*=\s*)(' + NUMBER + r')(\s*(?:mm|m)(?:\^2|[2²])(?![A-Za-z0-9]))',
                  lambda m:m[1]+format(scale_number(float(m[2]),percent,2,8),'.8g')+m[3],text)
    # Standalone numerical property statements have an explicit dimensional unit.
    def prop(match):
        key = match[1]
        return key + match[2] + format(scale_number(float(match[3]), percent, POWERS[key], 8), '.8g') + (match[4] or '')
    # MM-001..050 compact section rows. Preserve the displayed public rounding;
    # no canonical property value is supplied to this function.
    lines = text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        compact = bool(re.match(r'^[\w-]+: A=', line))
        def property_value(match):
            unit = match[4]
            if not compact and not unit:
                return match[0]
            if unit:
                power = int(unit.strip().replace('mm', '').replace('m', '').replace('^', '')
                            .replace('²', '2').replace('⁴', '4'))
                require(power == POWERS[match[1]], f'Wrong dimension for section property: {match[0]}')
            return prop(match)
        # One pass also covers compact rows with units; a value is scaled exactly
        # once. ASCII boundaries allow a property immediately after Chinese text.
        lines[i] = re.sub(r'(?<![A-Za-z0-9_])(Asy|Asz|A|Iy|Iz|J)(\s*=\s*)(' + NUMBER +
                          r')(\s*(?:mm|m)(?:\^[24]|[24²⁴])(?![A-Za-z0-9]))?', property_value, line)
    return ''.join(lines)


def audit_prose_properties(old, new, percent):
    """Independent dimensional check, including prose inside public JSON strings.

    Read assignments without invoking the transformer. Preserve intentional
    conflicting source values in the same ratio, rather than replacing them by
    a hidden canonical value.
    """
    pattern = re.compile(r'(?<![A-Za-z0-9_])(Asy|Asz|A|Iy|Iz|J)\s*=\s*(' + NUMBER +
                         r')\s*(mm|m)(?:\^([24])|([24²⁴]))(?![A-Za-z0-9])')
    def records(text):
        result=[(m[1], float(m[2]), m[3], int((m[4] or m[5]).replace('²', '2').replace('⁴', '4')))
                for m in pattern.finditer(text)]
        for m in re.finditer(r'\b([A-Za-z][\w-]*) area (?:is|=)\s*('+NUMBER+r')\s*(mm|m)(?:\^2|[2²])(?![A-Za-z0-9])',text):
            result.append(('A',float(m[2]),m[3],2))
        for m in re.finditer(r'(?:轴向|截面)面积\s*('+NUMBER+r')\s*m[²2]',text):
            result.append(('A',float(m[1]),'m',2))
        for m in re.finditer(r'(?<![A-Za-z0-9_])A\d+\s*=\s*('+NUMBER+r')\s*(mm|m)(?:\^2|[2²])(?![A-Za-z0-9])',text):
            result.append(('A',float(m[1]),m[2],2))
        return result
    before, after = records(old), records(new)
    require(len(before) == len(after), 'Dimensioned prose property inventory changed')
    for a, b in zip(before, after):
        key, value, unit, power = a
        require((key, unit, power) == (b[0], b[2], b[3]) and power == POWERS[key],
                'Dimensioned prose property identity/unit changed')
        expected = value * (percent / 100) ** power
        require(math.isclose(b[1], expected, rel_tol=5e-8),
                f'Unscaled or inconsistent prose property: {key}={b[1]} {unit}^{power}; expected {expected}')
    # Independent reader of the reviewed dimensional vocabulary. In particular,
    # include shared units, Chinese annotations and plural/hyphenated groups;
    # a changed first dimension cannot hide an unchanged second dimension.
    def dimensions(text):
        patterns = [
            (r'('+NUMBER+r')\s*(?:[x×]|by)\s*('+NUMBER+r')(?=(?:\s*/\s*'+NUMBER+r'\s*[x×]\s*'+NUMBER+r')*\s*mm)', (1,2)),
            (r'('+NUMBER+r')\s*[x×]\s*('+NUMBER+r')\s*m实心(?:方形|矩形)', (1,2)),
            (r'('+NUMBER+r')\s*m(?: wide)? by\s*('+NUMBER+r')\s*m', (1,2)),
            (r'\b[A-Za-z][\w-]* is (?:a )?('+NUMBER+r') by ('+NUMBER+r') m (?:solid )?(?:square|rectangle)', (1,2)),
            (r'\bC[\w-]*\s+(?:is|are|=)\s*('+NUMBER+r') m square', (1,)),
            (r'(?:梁B1|屋面B1|连系梁T1)宽('+NUMBER+r')m、?高('+NUMBER+r')m', (1,2)),
            (r'柱C1为('+NUMBER+r')m方形', (1,)),
            (r'\b[BH]\s*=\s*('+NUMBER+r')(?=\s*(?:mm|;|$))', (1,)),
        ]
        return [(i, float(m[g])) for i,(pattern,groups) in enumerate(patterns)
                for m in re.finditer(pattern,text,re.M) for g in groups]
    first,last=dimensions(old),dimensions(new)
    require(len(first)==len(last),'Solid section dimension inventory changed')
    for (kind,a),(new_kind,b) in zip(first,last):
        require(kind==new_kind and math.isclose(b,a*percent/100,rel_tol=5e-8),
                f'Unscaled or inconsistent prose section dimension: {b}; expected {a*percent/100}')
    return len(before)+len(first)


def transform_contract(contract, percent):
    """Publish the same authored dimensions in prompts and scheduled turns.

    Source requirements, attachment release times, requested quantities and
    tolerances stay frozen. This edits only the public instruction string.
    """
    result = correct_inference_contract(contract)
    if percent != 100:
        for turn in result['turns']:
            turn['instruction'] = transform_prose(turn['instruction'], percent)
        for output in result['requiredOutputs']:
            if isinstance(output.get('description'),str):
                output['description'] = transform_prose(output['description'], percent)
    return result


def correct_inference_contract(contract):
    """Reviewed rubric correction, independent of the section assignment plan.

    INT-016's original source and public instruction already permit a uniquely
    justified inference. Give that path the same state-1 numerical gates, while
    keeping clarification available and requiring a semantic justification.
    The baseline corpus and prior scores are never edited.
    """
    result = deepcopy(contract)
    if contract['id'] != 'INT-016':
        return result
    turn = result['turns'][0]
    require(turn['expectation'] == 'clarify' and turn['state'] is None and
            'uniquely justified inference' in turn.get('clarificationPolicy', '') and
            'if you infer it uniquely' in turn['instruction'], 'INT-016 policy correction no longer matches its source')
    turn.update(expectation='clarify-or-analyze', state=1)
    for output in result['requiredOutputs']:
        if output['kind'] == 'numerical' and output['state'] == 1:
            require(output['turnIds'] == ['t2'], 'Unexpected INT-016 numerical scope')
            output['turnIds'] = ['t1', 't2']
        elif output['id'] == 't1:interaction':
            output['state'] = 1
    return result


def transform_public(name, raw, percent):
    if name.endswith(('.png', '.dxf')):
        return raw
    if name.endswith('.svg'):
        # Only section schematics contain section dimensions. Other SVGs encode
        # the structural geometry and are copied byte for byte.
        if percent == 100 or not Path(name).name.startswith('section-detail'):
            return raw
        tree = ET.fromstring(raw)
        for node in tree.iter():
            if node.tag.rsplit('}', 1)[-1] == 'text' and node.text:
                node.text = transform_prose(node.text, percent)
        ET.register_namespace('', 'http://www.w3.org/2000/svg')
        return ET.tostring(tree, encoding='utf-8') + b'\n'
    text = raw.decode('utf-8')
    if name.endswith('.json'):
        return encoded(transform_json(json.loads(text), percent))
    # JSON public tables also occur after a prose introduction in .txt files.
    start = text.find('{')
    if start >= 0:
        try:
            data = json.loads(text[start:])
        except ValueError:
            pass
        else:
            return transform_prose(text[:start], percent).encode() + encoded(transform_json(data, percent))
    return transform_prose(text, percent).encode()


def audit_models(base, variant, percent):
    require(len(base) == len(variant), 'Changed state count')
    maximum_rounding = 0.
    for old, new in zip(base, variant):
        require({k: v for k, v in old.items() if k != 'sections'} ==
                {k: v for k, v in new.items() if k != 'sections'}, 'Changed a non-section physical input')
        require(new == scale_model(old, percent), 'Variant differs from the declared similarity transform')
        for section in used_sections(new):
            for value in section['properties'].values():
                maximum_rounding = max(maximum_rounding, abs(float(format(value, '.8g')) / value - 1))
            shape = section.get('shape', {})
            if percent != 100 and shape:
                b, h = shape['B'] / 1000, shape['H'] / 1000
                a, c = max(b, h), min(b, h)
                expected = {'A': b*h, 'Iy': b*h**3/12, 'Iz': h*b**3/12,
                            'J': a*c**3*(1/3-.21*c/a*(1-c**4/(12*a**4)))}
                for key, value in expected.items():
                    require(math.isclose(section['properties'][key], value, rel_tol=1e-6),
                            f'Inconsistent rectangular geometry: {section["id"]}/{key}')
    require(maximum_rounding <= 5e-8, '8 significant digits exceed the presentation budget')
    return maximum_rounding


def inventory(cases):
    """Count cases, not repeated states or unused appendix entries."""
    groups = defaultdict(list)
    for row, models in cases:
        for group in ('all', row['family'], row['engine']):
            groups[group].append((row, models))
    result = {}
    for group, items in sorted(groups.items()):
        js = defaultdict(list)
        signatures = defaultdict(list)
        shape_dimensions = set()
        for row, models in items:
            values = set()
            signatures_case = set()
            for model in models:
                sections = used_sections(model)
                values.update(format(s['properties']['J'], '.8g') for s in sections)
                signatures_case.add(tuple(sorted(tuple(format(s['properties'][k], '.8g') for k in ('A', 'Iy', 'Iz', 'J')) for s in sections)))
                for s in sections:
                    shape = s.get('shape', {})
                    if shape.get('kind') == 'rectangular':
                        shape_dimensions.add((shape['B'], shape['H']))
            for value in values:
                js[value].append(row['caseId'])
            for value in signatures_case:
                signatures[value].append(row['caseId'])
        top = sorted(js.items(), key=lambda item: (-len(item[1]), item[0]))
        count = len(items)
        result[group] = {'cases': count, 'distinctJ': len(js), 'distinctRectangles': len(shape_dimensions),
                         'maxJCases': len(top[0][1]), 'maxJFraction': len(top[0][1])/count,
                         'mostRepeatedJ': [{'value': key, 'count': len(ids), 'caseIds': ids} for key, ids in top[:5]],
                         'distinctSectionSets': len(signatures),
                         'maxRepeatedSectionSetCases': max(map(len, signatures.values()))}
    return result


def audit_plan(root, plan):
    manifest_path = Path(root) / 'corpora/research-300/manifest.json'
    require(plan['edition'] == EDITION and plan['baseManifestSha256'] == sha(manifest_path.read_bytes()), 'Stale edition/base manifest')
    expected = make_plan(root)
    if 'sourceConstraintCorrection' in plan:
        expected = corrected_plan(expected)
    require(plan == expected, 'Plan differs from the reviewed policy or source binding')
    before, after, cases = [], [], []
    for row in plan['cases']:
        folder = Path(root) / 'corpora/research-300/cases' / row['caseId']
        contract = read(folder / 'contract.json')
        assert_base_source(folder, row)
        models = [read(folder / name) for name in contract['modelStates']]
        variants = [scale_model(m, row['percent']) for m in models]
        rounding = audit_models(models, variants, row['percent'])
        if row['engine'] == 'PKPM' and row['percent'] != 100:
            for model in variants:
                for s in used_sections(model):
                    if s.get('shape'):
                        require(all(float(s['shape'][k]).is_integer() for k in ('B', 'H')), 'PKPM requires integer-mm dimensions')
        before.append((row, models)); after.append((row, variants))
        cases.append({**row, 'states': len(models), 'maximumDisplayRelativeError': rounding})
    old, new = inventory(before), inventory(after)
    require(new['all']['maxJFraction'] <= plan['policy']['maximumJCaseFraction'], 'Global J concentration exceeds policy')
    for family in ('STD', 'INT', 'MM'):
        require(new[family]['maxJFraction'] <= plan['policy']['maximumJFamilyFraction'], 'Family J concentration exceeds policy')
    for engine in ('OpenSees', 'PKPM', 'YJK'):
        require(new[engine]['maxJFraction'] <= plan['policy']['maximumJEngineFraction'], 'Engine J concentration exceeds policy')
    return {'schemaVersion': 1, 'edition': EDITION, 'planSha256': sha(encoded(plan)),
            'changedCases': sum(row['percent'] != 100 for row in cases),
            'fixedCases': sum(row['percent'] == 100 for row in cases),
            'states': sum(row['states'] for row in cases), 'before': old, 'after': new,
            'maximumDisplayRelativeError': max(row['maximumDisplayRelativeError'] for row in cases),
            'scope': 'Section-parameter diversity; not new topology or material coverage.',
            'cases': cases}


def assert_base_source(folder, row):
    from reference_io import build_source_binding
    binding = build_source_binding(folder, read(Path(folder)/'contract.json'), {})
    require(binding['sourceHash'] == row['baseSourceHash'], f'{row["caseId"]}: source bytes differ from the frozen base')


def public_sections(name, raw):
    """Read actual published property records, retaining their release boundary."""
    result = []
    if not name.endswith(('.json', '.txt')):
        return result
    text = raw.decode()
    data = None
    try:
        data = json.loads(text if name.endswith('.json') else text[text.index('{'):])
    except (ValueError, json.JSONDecodeError):
        pass
    if data is not None:
        units = data.get('units', {}) if isinstance(data, dict) else {}
        units = units if isinstance(units, dict) else {}
        def visit(value):
            if isinstance(value, dict):
                if isinstance(value.get('properties'), dict) and 'A' in value['properties']:
                    props = {k: v / (1e6 if units.get(k) == 'mm2' else 1e12 if units.get(k) == 'mm4' else 1)
                             for k, v in value['properties'].items()}
                    result.append((value.get('id'), props))
                else:
                    for child in value.values():
                        visit(child)
            elif isinstance(value, list):
                for child in value:
                    visit(child)
        visit(data)
    else:
        for line in text.splitlines():
            match = re.match(r'^([\w-]+): A=', line)
            if match:
                props = {m[1]: float(m[2]) for m in re.finditer(r'\b(A|Iy|Iz|J)=(' + NUMBER + r')', line)}
                result.append((match[1], props))
    return result


def check_public_tree(old, new, percent, path=''):
    """Reject changes to public loads/topology/settings outside section records."""
    if isinstance(old, dict):
        require(isinstance(new, dict) and old.keys() == new.keys(), f'Public fields changed at {path}')
        if isinstance(old.get('properties'), dict) and 'A' in old['properties']:
            require({k: v for k, v in old.items() if k not in ('shape', 'properties')} ==
                    {k: v for k, v in new.items() if k not in ('shape', 'properties')}, 'Public section identity changed')
            old_shape, new_shape = old.get('shape'), new.get('shape')
            if percent == 100:
                require(old_shape == new_shape, 'Fixed public shape changed')
            elif old_shape:
                require(new_shape['kind'] == old_shape['kind'] and new_shape.keys() == old_shape.keys(), 'Public shape changed')
                for key in ('B', 'H'):
                    require(math.isclose(new_shape[key], old_shape[key]*percent/100, rel_tol=5e-8), 'Public shape scale mismatch')
            else:
                require(old_shape == new_shape, 'Added a shape to an effective numerical section')
        else:
            for key, value in old.items():
                check_public_tree(value, new[key], percent, path+'/'+key)
    elif isinstance(old, list):
        require(isinstance(new, list) and len(old) == len(new), f'Public array changed at {path}')
        for i, (a, b) in enumerate(zip(old, new)):
            check_public_tree(a, b, percent, path+'/'+str(i))
    elif isinstance(old, str):
        require(new == transform_prose(old, percent), f'Unexpected public prose edit at {path}')
    else:
        require(type(old) == type(new) and old == new, f'Non-section numeric input changed at {path}')


def audit_public_sources(root, destination, plan):
    """Check the generated public records against unchanged scope and new models.

    Original mismatches (intentional conflicts/unused public revisions) are
    recorded separately. They must retain the same dimensionless discrepancy;
    authoring does not silently resolve an interaction task's ambiguity.
    """
    cases, maximum = [], 0.
    for row in plan['cases']:
        base = Path(root)/'corpora/research-300/cases'/row['caseId']
        target = Path(destination)/'corpora/research-300/cases'/row['caseId']
        c, new_c = read(base/'contract.json'), read(target/'contract.json')
        reviewed_contract = transform_contract(c, row['percent'])
        for key in ('sourcePlan', 'turns', 'requiredOutputs', 'attachments', 'plannedEngine', 'modelStates'):
            require(reviewed_contract[key] == new_c[key], f'{row["caseId"]}: changed source/turn/output scope: {key}')
        require((base/'reference-requests.json').read_bytes() == (target/'reference-requests.json').read_bytes(), 'Changed requests/tolerances')
        old_models, new_models = [[read(folder/n) for n in c['modelStates']] for folder in (base, target)]
        audit_models(old_models, new_models, row['percent'])
        old_sections = [s for m in old_models for s in m['sections']]
        new_sections = [s for m in new_models for s in m['sections']]
        count, bound, mismatches, dimensions, prose = 0, 0, [], 0, 0
        for old_turn, new_turn in zip(c['turns'], new_c['turns']):
            prose += audit_prose_properties(old_turn['instruction'], new_turn['instruction'], row['percent'])
        for old_output, new_output in zip(c['requiredOutputs'], new_c['requiredOutputs']):
            if 'description' in old_output:
                prose += audit_prose_properties(old_output['description'], new_output['description'], row['percent'])
        for name in ['prompt.txt', *c['attachments']]:
            old_raw, new_raw = (base/name).read_bytes(), (target/name).read_bytes()
            if not name.endswith(('.png', '.dxf')):
                prose += audit_prose_properties(old_raw.decode(), new_raw.decode(), row['percent'])
            if name.endswith(('.json', '.txt')):
                try:
                    a, b = old_raw.decode(), new_raw.decode()
                    if name.endswith('.txt'):
                        a, b = a[a.index('{'):], b[b.index('{'):]
                    old_data, new_data = json.loads(a), json.loads(b)
                except ValueError:
                    require(not name.endswith('.json'), f'Unreadable public JSON: {name}')
                else:
                    check_public_tree(old_data, new_data, row['percent'])
            if name.endswith('.dxf') or name.endswith('.svg') and not name.startswith('section-detail'):
                require(old_raw == new_raw, 'Changed structural drawing entities')
            old_records, new_records = public_sections(name, old_raw), public_sections(name, new_raw)
            require([s[0] for s in old_records] == [s[0] for s in new_records], 'Changed public section inventory/order')
            for (sid, a), (_, b) in zip(old_records, new_records):
                count += 1
                require(set(a) == set(b), 'Changed public property fields')
                for key in a:
                    expected = scale_number(a[key], row['percent'], POWERS[key])
                    error = abs(b[key]/expected - 1)
                    require(error <= 5e-8, 'Public transform exceeds display rounding budget')
                matching = [i for i, s in enumerate(old_sections) if s['id'] == sid and
                            all(math.isclose(s['properties'].get(k, 0), v, rel_tol=1e-6, abs_tol=1e-12) for k, v in a.items())]
                if matching:
                    bound += 1
                    errors = [max(abs(b[k]/new_sections[i]['properties'][k] - 1) for k in b) for i in matching]
                    maximum = max(maximum, min(errors))
                    require(min(errors) <= 1e-7, f'Public/model property mismatch: {row["caseId"]}/{name}/{sid}')
                else:
                    mismatches.append({'file': name, 'section': sid,
                                       'reason': 'Original public record differs from/does not occur in solved states; preserved, not resolved.'})
            if name.startswith('section-detail') and name.endswith('.svg'):
                sid = None
                for node in ET.fromstring(new_raw).iter():
                    if node.tag.rsplit('}', 1)[-1] != 'text':
                        continue
                    text = ''.join(node.itertext())
                    if ' | roll ' in text:
                        sid = text.split(' | roll ')[0]
                    match = re.fullmatch(r'B=(' + NUMBER + r'); H=(' + NUMBER + r')', text)
                    if match:
                        shapes = [s['shape'] for s in new_sections if s['id'] == sid and
                                  'B' in s.get('shape', {}) and 'H' in s.get('shape', {})]
                        if not shapes and row['percent'] == 100:
                            require(new_raw == old_raw, 'Fixed detailed shape drawing changed')
                            continue
                        require(any(math.isclose(shape['B'], float(match[1]), rel_tol=1e-7) and
                                    math.isclose(shape['H'], float(match[2]), rel_tol=1e-7) for shape in shapes),
                                f'Section drawing/model dimensions differ: {row["caseId"]}/{sid}')
                        dimensions += 1
        require(count > 0, f'{row["caseId"]}: no public section records inspected')
        cases.append({'caseId': row['caseId'], 'publicSectionRecords': count, 'matchedModelRecords': bound,
                      'originalUnmatchedRecords': mismatches, 'checkedSectionDrawings': dimensions,
                      'checkedDimensionedProseProperties': prose})
    return {'edition': EDITION, 'cases': cases, 'maximumPublicModelRelativeError': maximum,
            'turnAndOutputScopePreserved': False,
            'reviewedPolicyCorrections': [{'caseId': 'INT-016', 'turnId': 't1',
                'reason': 'Implement the existing source permission for a uniquely justified inference; retain independent semantic and state-1 numerical gates.'}],
            'structuralDrawingEntitiesPreserved': True,
            'tolerancesUnchanged': True, 'futureSectionRecordsNotMovedBetweenFiles': True}


def build(root, plan, destination):
    root, destination = Path(root).resolve(), Path(destination).resolve()
    require(not destination.exists(), 'Output must be a new directory')
    require('sourceConstraintCorrection' in plan,
            'Use planning/section-diversity-v1-r2.json; the historical plan misses an explicit source dimension.')
    require(not root.is_relative_to(destination), 'Output must not contain source root')
    require(not destination.is_relative_to(root) or any(destination.is_relative_to(root/name)
            for name in ('.bench-work', 'benchmark-dist')), 'In-repository output must be in .bench-work or benchmark-dist')
    audit = audit_plan(root, plan)
    destination.mkdir(parents=True)
    # Copy the source requirements needed by the existing corpus validator.
    shutil.copytree(root / 'planning', destination / 'planning')
    base_manifest = read(root / 'corpora/research-300/manifest.json')
    for source in base_manifest['originalSources']:
        path = source['path']
        if (root/path).is_file() and not (destination/path).exists():
            (destination/path).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root/path, destination/path)
    modified = []
    render_pages = {}
    for row in plan['cases']:
        case_id, percent = row['caseId'], row['percent']
        base = root / 'corpora/research-300/cases' / case_id
        target = destination / 'corpora/research-300/cases' / case_id
        contract = read(base / 'contract.json')
        # Explicit whitelist: never copy old references, approvals or solver receipts.
        for name in ['contract.json', 'prompt.txt', 'reference-requests.json', *contract['modelStates'], *contract['attachments']]:
            raw = (base/name).read_bytes()
            if name in contract['modelStates']:
                changed = encoded(scale_model(json.loads(raw), percent)) if percent != 100 else raw
            elif name == 'contract.json':
                changed = raw
            elif name == 'reference-requests.json':
                changed = raw
            else:
                changed = transform_public(name, raw, percent)
            (target/name).parent.mkdir(parents=True, exist_ok=True)
            (target/name).write_bytes(changed)
            if changed != raw:
                modified.append({'caseId': case_id, 'path': name, 'oldSha256': sha(raw), 'sha256': sha(changed)})
                if name.endswith('.svg') and str(Path(name).with_suffix('.png')) in contract['attachments']:
                    render_pages[str((target/name).with_suffix('.png'))] = changed
        if percent != 100:
            contract['authoringNotes'] = [
                f'{EDITION}: author-completed section linear dimensions scaled by {percent}/100; '
                'A and explicit shear areas scale quadratically, Iy/Iz/J quartically. '
                'Source geometry, loads, materials, axes, section ratios and turn schedule retained. '
                'Public section numbers use eight significant digits; unchanged historical results do not apply.'
            ]
            write(target/'contract.json', contract)
        reviewed_contract = transform_contract(contract, percent)
        if reviewed_contract != contract:
            write(target/'contract.json', reviewed_contract)
    if render_pages:
        import public_input_visual as visual
        rendered, _ = visual.render(render_pages)
        for name, raw in rendered.items():
            Path(name).write_bytes(raw)
    write(destination/'diversity-plan.json', plan)
    write(destination/'diversity-audit.json', audit)
    write(destination/'public-source-audit.json', audit_public_sources(root, destination, plan))
    write(destination/'diversity-build.json', {'edition': EDITION, 'buildRevision': 7,
          'builderSha256': sha(Path(__file__).read_bytes()), 'modifiedPublicAndModels': modified,
          'historicalReferencesCopied': False, 'formalScoringReady': False,
          'requiredBeforePromotion': ['same-engine references for all prescribed engines',
                                     'new input correspondence and independent review', 'new candidate trial']})
    return audit


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('plan', 'audit', 'build'))
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--plan', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == 'plan':
        require(not args.output.exists(), 'Refusing to overwrite a plan')
        result = corrected_plan(make_plan(args.root))
        audit_plan(args.root, result)
        write(args.output, result)
    else:
        require(args.plan is not None, '--plan is required')
        plan = read(args.plan)
        result = build(args.root, plan, args.output) if args.command == 'build' else audit_plan(args.root, plan)
        if args.command == 'audit':
            write(args.output, result)
    print(json.dumps({k: result[k] for k in ('edition', 'changedCases', 'fixedCases', 'states') if k in result}))


if __name__ == '__main__':
    main()
