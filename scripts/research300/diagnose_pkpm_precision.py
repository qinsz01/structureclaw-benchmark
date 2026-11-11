"""Replay the two residual PKPM precision investigations from the frozen archive.

This is an offline diagnostic, not a tolerance policy or replacement reference.
Every experiment is applied to every primary request in both cases. In
particular, float32 compatibility never promotes a failed strict comparison.
"""
import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import struct
import tempfile

for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '1'

import numpy as np

from audit_commercial_edition import pkpm as audit_pkpm
from codex_trial import verify_selection as archive_reader
from reference_io import convert_value, quantity_unit, selection_factors
from reference_solver import axes, local_stiffness, solve, _consistent_load

ROOT = Path(__file__).resolve().parents[2]
PREFIX = 'audits/section-diversity-native-public-20261027'
ACTIONS = ('N', 'V2', 'V3', 'T', 'M2', 'M3')
NATIVE_ACTIONS = ('N', 'Vy', 'Vz', 'T', 'My', 'Mz')
DISP = ('ux', 'uy', 'uz', 'rx', 'ry', 'rz')
REACTIONS = ('fx', 'fy', 'fz', 'mx', 'my', 'mz')
VARIANTS = ('published', 'section-f32', 'geometry-f32', 'section-geometry-f32')


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def strict(native, independent, tolerance):
    if not all(math.isfinite(v) for v in (native, independent)):
        raise ValueError('Nonfinite comparison')
    limit = tolerance['absolute'] + tolerance['relative'] * abs(native)
    return {'native': native, 'independent': independent,
            'difference': native - independent, 'limit': limit,
            'pass': abs(native - independent) <= limit}


def sums(terms):
    """A specified float32 experiment, NOT a model of vendor operation order."""
    total = 0.
    for term in terms:
        total = f32(total + f32(term))
    return {'terms': terms, 'recoveredF64': math.fsum(terms),
            'sequentialF32Sum': total,
            'recoveryScale': math.fsum(abs(t) for t in terms)}


def variant_model(source, variant):
    if variant not in VARIANTS:
        raise ValueError('Unsupported experiment')
    model = copy.deepcopy(source)
    if 'section' in variant:
        for section in model['sections']:
            section['properties'] = {k: f32(v) for k, v in section['properties'].items()}
    if 'geometry' in variant:
        for node in model['nodes']:
            for key in 'xyz':
                node[key] = f32(node[key])
    return model


def endpoint_location(source, model, location):
    result = copy.deepcopy(location)
    if result['kind'] != 'member' or result['positionM'] == 0:
        return result
    element = next(e for e in model['elements'] if e['id'] == result['id'])
    lengths = []
    for item in (source, model):
        nodes = {n['id']: [n[c] for c in 'xyz'] for n in item['nodes']}
        lengths.append(math.dist(*(nodes[n] for n in element['nodes'])))
    if abs(result['positionM'] - lengths[0]) > 1e-10:
        raise ValueError('This investigation only supports member endpoints')
    result['positionM'] = lengths[1]
    return result


def native_quantity(result, quantity):
    selection, location = quantity['selection'], quantity['location']
    collection = 'caseResults' if selection['kind'] == 'case' else 'combinationResults'
    selected = result[collection][selection['id']]
    component = quantity['component']
    if location['kind'] == 'node':
        group = 'displacements' if component.lower() in DISP else 'reactions'
        return selected[group][location['id']][component.lower()]
    rows = [row for row in selected['memberStations'][location['id']]
            if abs(row['positionM'] - location['positionM']) < 1e-10
            and row['side'] == location['side']]
    if len(rows) != 1:
        raise ValueError('Ambiguous native requested station')
    return rows[0]['components'][NATIVE_ACTIONS[ACTIONS.index(component)]]


def recovery(model, quantity, native):
    """Canonical endpoint/reaction terms from observed native six-DOF vectors."""
    location, component = quantity['location'], quantity['component']
    if component.lower() in DISP:
        return None
    nodes = {n['id']: n for n in model['nodes']}
    sections = {s['id']: s['properties'] for s in model['sections']}
    materials = {m['id']: m for m in model['materials']}
    per_case = []
    for case_id, factor in selection_factors(model, quantity['selection']).items():
        case = next(c for c in model['load_cases'] if c['id'] == case_id)
        terms = []
        for element in model['elements']:
            if location['kind'] == 'member':
                if element['id'] != location['id']:
                    continue
                end = int(location['positionM'] != 0)
                index = ACTIONS.index(component)
                sign = ((-1, 1, 1, -1, -1, -1) if end == 0 else (1, -1, -1, 1, 1, 1))[index]
                selected_rows = [(6 * end + index, sign)]
            else:
                if location['id'] not in element['nodes']:
                    continue
                end = element['nodes'].index(location['id'])
                index = REACTIONS.index(component.lower())
                selected_rows = None
            a, b = [np.array([nodes[n][c] for c in 'xyz']) for n in element['nodes']]
            length = float(np.linalg.norm(b - a))
            rotation = axes(model, element, a, b)
            if selected_rows is None:
                selected_rows = [(6 * end + 3 * (index // 3) + j, rotation[j, index % 3])
                                 for j in range(3) if rotation[j, index % 3] != 0]
            prop = sections[element['section']]
            k = local_stiffness(element, materials[element['material']], {'properties': prop},
                                length, {key: 5 * prop['A'] / 6 for key in ('Asy', 'Asz')})
            displacement = np.concatenate([
                rotation @ np.array([native['caseResults'][case_id]['displacements'][n][d] for d in group])
                for n in element['nodes'] for group in (DISP[:3], DISP[3:])])
            for row, sign in selected_rows:
                terms.extend(float(sign * coefficient * d)
                             for coefficient, d in zip(k[row], displacement) if coefficient != 0)
                for load in case['loads']:
                    if load.get('element') != element['id']:
                        continue
                    if load['type'] != 'distributed' or load.get('reference_frame', 'global') != 'global':
                        raise ValueError('Unsupported endpoint load recovery')
                    local = rotation @ np.array([load.get('w' + c, 0) for c in 'xyz'])
                    fixed = float(-sign * _consistent_load(local, local, length)[row])
                    if fixed != 0:
                        terms.append(fixed)
        if location['kind'] == 'node':
            for load in case['loads']:
                if load.get('node') == location['id']:
                    if load['type'] != 'nodal' or load.get('reference_frame', 'global') != 'global':
                        raise ValueError('Unsupported reaction load recovery')
                    if load.get(component.lower(), 0) != 0:
                        terms.append(-load[component.lower()])
        per_case.append({'caseId': case_id, 'factor': factor, **sums(terms)})
    return {'recoveredFromNativeDisp': math.fsum(c['factor'] * c['recoveredF64'] for c in per_case),
            'sequentialF32Experiment': math.fsum(c['factor'] * c['sequentialF32Sum'] for c in per_case),
            'recoveryScale': math.fsum(abs(c['factor']) * c['recoveryScale'] for c in per_case),
            'operands': per_case}


class Evidence:
    def __init__(self, archive, files):
        self.archive, self.files, self.used = archive, files, {}

    def data(self, name):
        row = self.files[name]
        data = self.archive.read('blobs/' + row['sha256'])
        if len(data) != row['bytes'] or hashlib.sha256(data).hexdigest() != row['sha256']:
            raise ValueError('Evidence hash mismatch: ' + name)
        self.used[name] = row
        return data

    def json(self, name):
        return json.loads(self.data(name))

    def audit(self, prefix, model, native):
        names = [name for name in self.files if name.startswith(prefix + '/native/projects/')]
        roots = {name.split('/native/projects/', 1)[1].split('/')[0] for name in names}
        if len(roots) != 1:
            raise ValueError('Ambiguous native project')
        start = prefix + '/native/projects/' + roots.pop() + '/'
        with tempfile.TemporaryDirectory(prefix='pkpm-precision-audit-') as temp:
            project = Path(temp)
            # Only the files consumed by the independent binary/slot audit.
            required = ('native-section-compilation.json', 'SDATA.SAT', 'SDATA.SAT.compiled',
                        'UserMaterial.SAT', 'native-stage-evidence.json', 'MESH.SAT',
                        'NODEINDEX.SAT', 'ConstraintNodeNo.SAT', 'WDISPGKNO.OUT')
            selected = set(required)
            selected.update(name[len(start):] for name in names
                            if Path(name).name.startswith('DISP') and name.endswith('.SAT'))
            for name in sorted(selected):
                (project / name).write_bytes(self.data(start + name))
            return audit_pkpm(project, model, native)


def analyze_case(evidence, case_id):
    jobs = evidence.json(f'{PREFIX}/candidates/{case_id}/executions.json')
    quantities = evidence.json(f'edition/corpora/research-300/cases/{case_id}/independent-reference.json')['states'][0]['quantities']
    runs = []
    for job in jobs:
        prefix = f'{PREFIX}/solver-jobs/{case_id}/{PurePosixPath(job["job"]).name}'
        model = evidence.json(prefix + '/model.json')
        native = evidence.json(prefix + '/native/result.json')
        audit = evidence.audit(prefix, model, native)
        raw = [v for c in native['caseResults'].values() for rows in c['memberStations'].values()
               for row in rows for v in row['nativeComponents']]
        qs = [q for q in quantities if q['selection'] == job['selection']]
        if not qs:
            raise ValueError('No requests for native selection')
        for q in qs:
            if native_quantity(native, q) != q['value'] or q['unit'] != quantity_unit(q['component']):
                raise ValueError('Frozen reference differs from original native output or unit: ' + q['id'])
        experiments = []
        for variant in VARIANTS:
            current = variant_model(model, variant)
            props = {s['id']: s['properties'] for s in current['sections']}
            areas = {e['id']: {key: 5 * props[e['section']]['A'] / 6 for key in ('Asy', 'Asz')}
                     for e in current['elements']}
            locations = [endpoint_location(model, current, q['location']) for q in qs]
            calc, checks = solve(current, selection_factors(current, job['selection']), locations,
                                 effective_shear_areas=areas)
            rows = []
            for q, location in zip(qs, locations):
                value = convert_value(calc(location, q['component']), quantity_unit(q['component']), q['unit'])
                row = {'id': q['id'], 'unit': q['unit'], **strict(q['value'], value, q['tolerance'])}
                diagnostic = recovery(current, {**q, 'location': location}, native)
                if diagnostic is not None:
                    row.update(diagnostic)
                    row['nativeMinusRecovered'] = q['value'] - diagnostic['recoveredFromNativeDisp']
                    row['nativeVsRecoveredPass'] = strict(q['value'], diagnostic['recoveredFromNativeDisp'], q['tolerance'])['pass']
                    # The second check asks if double recovery from rounded native
                    # U would match the independent solve; it is never a new gold.
                    row['recoveredVsIndependentPass'] = abs(diagnostic['recoveredFromNativeDisp'] - value) <= row['limit']
                rows.append(row)
            # Final serialization alone is separately falsifiable: a vendor
            # vector differing from round32(matrix U) includes upstream effects.
            displacement = []
            for case_id_local in selection_factors(current, job['selection']):
                calc_u, _ = solve(current, {case_id_local: 1.}, [], effective_shear_areas=areas)
                pairs = [(native['caseResults'][case_id_local]['displacements'][n['id']][d],
                          calc_u({'kind': 'node', 'id': n['id']}, d), d)
                         for n in current['nodes'] if not all(n['restraints']) for d in DISP]
                displacement.append({'caseId': case_id_local, 'components': len(pairs),
                                     'differentFromRoundedIndependent': sum(a != f32(b) for a, b, _ in pairs),
                                     'maxTranslationDifferenceM': max(abs(a - b) for a, b, d in pairs if d in DISP[:3]),
                                     'maxRotationDifferenceRad': max(abs(a - b) for a, b, d in pairs if d in DISP[3:])})
            experiments.append({'variant': variant, 'comparisons': len(rows),
                                'failed': sum(not r['pass'] for r in rows),
                                'failedAfterDiagnosticRecovery': sum(not r.get('recoveredVsIndependentPass', r['pass']) for r in rows),
                                'checks': checks, 'nativeDisplacementComparison': displacement, 'rows': rows})
        runs.append({'selection': job['selection'], 'job': prefix, 'audit': audit,
                     'rawForceComponents': len(raw), 'exactlyFloat32ForceComponents': sum(f32(v) == v for v in raw),
                     'experiments': experiments})
    if sum(r['experiments'][0]['comparisons'] for r in runs) != len(quantities):
        raise ValueError('Native selection coverage mismatch')
    return {'caseId': case_id, 'runs': runs}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Output must not already exist')
    archive_reader.HERE = args.archive.resolve()
    meta = archive_reader.read(args.archive / 'evidence-meta.json')
    for filename, key in (('archive-manifest.json', 'archiveManifestSha256'), ('source-integrity.json', 'sourceIntegritySha256')):
        if archive_reader.file_sha(args.archive / filename) != meta[key]:
            raise ValueError('Archive metadata hash mismatch')
    guarded = archive_reader.read(args.archive / 'source-integrity.json')['files']
    for row in guarded:
        if archive_reader.file_sha(ROOT / row['path']) != row['sha256']:
            raise ValueError('Frozen implementation changed: ' + row['path'])
    entries = archive_reader.read(args.archive / 'archive-manifest.json')['files']
    files = {row['path']: row for row in entries}
    if len(files) != len(entries) or any(PurePosixPath(p).is_absolute() or '..' in PurePosixPath(p).parts for p in files):
        raise ValueError('Invalid evidence paths')
    with archive_reader.open_archive(meta) as archive:
        evidence = Evidence(archive, files)
        cases = [analyze_case(evidence, cid) for cid in ('STD-089', 'STD-091')]
    report = {'schemaVersion': 1, 'diagnosticOnly': True, 'nativeArithmeticBound': False,
              'scoringOrToleranceChanged': False, 'archiveSha256': meta['sha256'],
              'scriptSha256': archive_reader.file_sha(Path(__file__)),
              'guardedSourceFilesVerified': len(guarded), 'numpyVersion': np.__version__,
              'limitations': ['A float32-valued API does not prove all vendor arithmetic uses float32.',
                              'Sequential float32 term accumulation is an explicit experiment, not an observed vendor implementation.',
                              'Canonical recovery from rounded native displacements cannot reconstruct unavailable full precision displacements.',
                              'Input quantization and recovery experiments do not supply a vendor-wide error bound.',
                              'Original native values, strict failures, evaluator, candidates and scores are immutable.'],
              'inputs': [evidence.used[p] for p in sorted(evidence.used)], 'cases': cases}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write('\n')
    print(json.dumps({'output': str(args.output), 'cases': [
        {'caseId': c['caseId'], 'comparisons': sum(r['experiments'][0]['comparisons'] for r in c['runs']),
         'strictFailures': sum(r['experiments'][0]['failed'] for r in c['runs'])} for c in cases]}, indent=2))


if __name__ == '__main__':
    main()
