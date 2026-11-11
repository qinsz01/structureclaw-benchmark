"""Independent L4 live-load density checks, not a replacement grader.

Reconstructs Q from public zone widths and revisions. A different force-density
projection proves a different load; an equal projection does not prove full
model equivalence. Geometry is the frozen, source-reviewed upper template,
not a new blind engineering reconstruction. No authoring load helper is used.
"""
import argparse
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import re


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sealed(root, desc):
    path = root / desc['path']
    if path.is_symlink() or sha(path) != desc['sha256']:
        raise ValueError('Sealed evidence changed: ' + desc['path'])
    return read(path)


def issued_density(upper, rules):
    lo, hi = min(n['x'] for n in upper['nodes']), max(n['x'] for n in upper['nodes'])
    intervals = []
    revision = rules.get('liveRevision')
    if revision:
        split = revision['splitX']
        west = sum(max(0, min(hi, z['endX'], split) - max(lo, z['startX'])) * z['widthM'] for z in rules['zones'])
        east = sum(max(0, min(hi, z['endX']) - max(lo, z['startX'], split)) * z['widthM'] for z in rules['zones'])
        east_pressure = revision['totalLiveKN'] / (west * revision['westEastPressureRatio'] + east)
    for zone in rules['zones']:
        start, end = max(lo, zone['startX']), min(hi, zone['endX'])
        edges = sorted({start, end, *([revision['splitX']] if revision and start < revision['splitX'] < end else [])})
        for a, b in zip(edges, edges[1:]):
            if b <= a:
                continue
            pressure = zone['Q'] if not revision else east_pressure * (revision['westEastPressureRatio'] if (a + b) / 2 < revision['splitX'] else 1)
            intervals.append((a, b, [0., 0., -pressure * zone['widthM']]))
    return intervals, {}


def executed_density(model, selection):
    if model['unit_system'] != 'SI' or model['analysis_control'].get('self_weight') is not False:
        raise ValueError('Requires SI and explicitly disabled automatic gravity')
    factors = {selection['id']: 1} if selection['kind'] == 'case' else next(c['factors'] for c in model['load_combinations'] if c['id'] == selection['id'])
    nodes = {n['id']: n for n in model['nodes']}
    members = {e['id']: e for e in model['elements']}
    intervals, points = [], {}
    for cid, factor in factors.items():
        if not factor:
            continue
        case = next(c for c in model['load_cases'] if c['id'] == cid)
        for load in case['loads']:
            if load.get('reference_frame', 'global') != 'global':
                raise ValueError('Local-load representation needs separate review')
            if load['type'] == 'nodal':
                node = nodes[load['node']]
                key = tuple(node[k] for k in 'xyz')
                values = points.setdefault(key, [0.] * 6)
                for i, k in enumerate(('fx', 'fy', 'fz', 'mx', 'my', 'mz')):
                    values[i] += factor * load.get(k, 0)
            elif load['type'] == 'distributed':
                if any(k in load for k in ('points', 'wx_start', 'wx_end', 'wy_start', 'wy_end', 'wz_start', 'wz_end')) or load.get('variation', 'uniform') != 'uniform':
                    raise ValueError('Nonuniform distributed representation needs separate review')
                a, b = [nodes[n] for n in members[load['element']]['nodes']]
                length = math.dist([a[k] for k in 'xyz'], [b[k] for k in 'xyz'])
                dx = b['x'] - a['x']
                if abs(dx) < 1e-10:
                    raise ValueError('Vertical projected member requires separate measure review')
                start, end = load.get('start', 0), load.get('end', length)
                if not (0 <= start < end <= length + 1e-8):
                    raise ValueError('Invalid distributed interval')
                x0, x1 = sorted((a['x'] + dx * start / length, a['x'] + dx * end / length))
                intervals.append((x0, x1, [factor * load.get(k, 0) * length / abs(dx) for k in ('wx', 'wy', 'wz')]))
            else:
                raise ValueError('Unsupported independent load representation')
    return intervals, points


def compare(actual, expected):
    breaks = sorted({x for rows in (actual[0], expected[0]) for row in rows for x in row[:2]})
    worst = {'absoluteDifference': 0., 'ratioToConservativeThreshold': 0.}
    for lo, hi in zip(breaks, breaks[1:]):
        if hi - lo < 1e-9:
            continue
        x = (lo + hi) / 2
        vectors = [[sum(v[i] for a, b, v in rows if a < x < b) for i in range(3)] for rows in (actual[0], expected[0])]
        for i, component in enumerate(('fx', 'fy', 'fz')):
            observed, issued = vectors[0][i], vectors[1][i]
            delta, threshold = abs(observed - issued), 1e-4 * (1 + abs(issued))
            if delta / threshold > worst['ratioToConservativeThreshold']:
                worst = {'kind': 'projected-continuous-force-density', 'positionX': x, 'component': component,
                         'candidate': observed, 'independentlyIssued': issued, 'unit': 'kN/m-horizontal',
                         'absoluteDifference': delta, 'conservativeThreshold': threshold, 'ratioToConservativeThreshold': delta / threshold}
    for position, vector in actual[1].items():
        for i, value in enumerate(vector):
            ratio = abs(value) / 1e-4
            if ratio > worst['ratioToConservativeThreshold']:
                worst = {'kind': 'unissued-concentrated-load', 'position': position, 'component': ('fx', 'fy', 'fz', 'mx', 'my', 'mz')[i],
                         'candidate': value, 'independentlyIssued': 0., 'unit': 'kN' if i < 3 else 'kN.m',
                         'absoluteDifference': abs(value), 'conservativeThreshold': 1e-4, 'ratioToConservativeThreshold': ratio}
    resultants = []
    for intervals, points in (actual, expected):
        resultants.append([sum((b - a) * v[i] for a, b, v in intervals) + sum(v[i] for v in points.values()) for i in range(3)])
    return {'worstDifference': worst, 'actualForceResultantKN': resultants[0], 'issuedForceResultantKN': resultants[1]}


def audit(edition, output, work=None, diagnostic=None):
    manifest = read(edition / 'manifest.json')
    file_map = {f['path']: f for f in manifest['files']}
    rows, candidate_rows = [], []
    if diagnostic:
        grade, index = read(diagnostic), read(work / 'index.json')
        if grade['manifestSha256'] != sha(edition / 'manifest.json') or grade['indexSha256'] != sha(work / 'index.json'):
            raise ValueError('Diagnostic corpus/index bindings differ')
        scores = {(r['caseId'], r['turnId']): r for r in grade['rows']}
        entries = {r['evidenceId']: r for r in index['entries']}
    for case in manifest['cases']:
        if case['level'] != 'L4':
            continue
        initial = edition / case['turns'][0]['public']
        rules = read(initial / 'load-zones.json')
        for ordinal, turn in enumerate(case['turns'], 1):
            task = read(edition / turn['public'] / 'task.json')
            if ordinal == 2:
                match = re.search(r'X=([\d.e+\-]+) m 分界，西/东面压比 ([\d.e+\-]+)，总活荷载仍为 ([\d.e+\-]+) kN', task['instruction'])
                if not match:
                    raise ValueError('Missing issued Q revision')
                rules['liveRevision'] = dict(zip(('splitX', 'westEastPressureRatio', 'totalLiveKN'), map(float, match.groups())))
            if ordinal == 4:
                rules.pop('liveRevision', None)
            ref = sealed(edition, file_map[turn['private']])
            if rules['zones'] != ref['loadRules']['zones']:
                raise ValueError('Reference changed the issued zone geometry or base pressure')
            revision = rules.get('liveRevision', {})
            if bool(revision) != bool(ref['loadRules'].get('liveRevision')) or any(not math.isclose(v, ref['loadRules']['liveRevision'][k], rel_tol=1e-12, abs_tol=1e-10) for k, v in revision.items()):
                raise ValueError('Reference Q revision differs from public instructions')
            expected = issued_density(ref['upperTemplate'], rules)
            role = 'combined' if ref['integration'] == 'rigid' else 'upper'
            maximum = 0.
            for truth in ref['truths']:
                model = {**ref[role + 'Template'], 'load_cases': truth[role + 'LoadCases']}
                comparison = compare(executed_density(model, {'kind': 'case', 'id': 'Q'}), expected)
                maximum = max(maximum, comparison['worstDifference']['absoluteDifference'])
                if maximum > 1e-8:
                    raise ValueError(f'Reference Q density differs: {case["id"]}/{turn["id"]}/{truth["id"]}')
            rows.append({'caseId': case['id'], 'turnId': turn['id'], 'designsChecked': len(ref['truths']), 'maxDensityDifference': maximum})
            if not diagnostic or scores[(case['id'], turn['id'])]['outcome'] == 'passed':
                continue
            score = scores[(case['id'], turn['id'])]
            row = {'caseId': case['id'], 'turnId': turn['id'], 'outcome': score['outcome'], 'comparisons': [], 'limitations': [], 'independentInputMismatchDemonstrated': False}
            candidate_rows.append(row)
            if role != 'upper' or not score.get('evidenceMapping'):
                row['limitations'].append('This candidate witness is limited to resolved one-way upper-model deliveries')
                continue
            capture = next(t for t in index['turns'] if t['caseId'] == case['id'] and t['turnId'] == turn['id'])
            answer = sealed(work, capture['answer'])
            mapping = {m['reported']: m['evidenceId'] for m in score['evidenceMapping']}
            for reported in answer.get('jobIdsByModel', {}).get('upper', []):
                identity = mapping[reported]
                entry = entries[identity]
                receipt, state = sealed(work, entry['files']['receipt']), sealed(work, entry['files']['state'])
                if not receipt['ok'] or receipt['role'] != 'candidate' or receipt['stateSha256'] != entry['files']['state']['sha256']:
                    raise ValueError('Candidate native state is not bound to a successful protected receipt')
                for key in state.get('analysisResult', {}).get('results', {}):
                    kind, sid = key.split(':', 1)
                    try:
                        comparison = compare(executed_density(state['model'], {'kind': kind, 'id': sid}), expected)
                        row['comparisons'].append({'jobId': identity, 'nativeSelection': key, **comparison})
                    except (ValueError, KeyError, StopIteration) as error:
                        row['limitations'].append({'jobId': identity, 'nativeSelection': key, 'reason': str(error)})
            if row['comparisons'] and not row['limitations']:
                closest = min(row['comparisons'], key=lambda r: r['worstDifference']['ratioToConservativeThreshold'])
                row['closestReportedExecution'] = closest
                row['independentInputMismatchDemonstrated'] = closest['worstDifference']['ratioToConservativeThreshold'] > 1
    result = {'kind': 'research300-v32-independent-project-Q-density-review', 'formalComparisonScore': False,
              'candidateInvocations': 0, 'nativeSolverInvocations': 0, 'originalScoresChanged': False,
              'manifestSha256': sha(edition / 'manifest.json'), 'sourceSha256': sha(Path(__file__)),
              'referenceCases': len({r['caseId'] for r in rows}), 'referenceTurns': len(rows),
              'referenceDesignsChecked': sum(r['designsChecked'] for r in rows),
              'maxReferenceDensityDifference': max(r['maxDensityDifference'] for r in rows),
              'referenceChecksAllPassed': True, 'referenceRows': rows, 'candidateRows': candidate_rows,
              'turnsWithIndependentInputWitness': sum(r['independentInputMismatchDemonstrated'] for r in candidate_rows),
              'scope': __doc__}
    if diagnostic:
        result['diagnosticSha256'] = sha(diagnostic)
    with output.open('x') as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write('\n')
    return {k: v for k, v in result.items() if k not in ('referenceRows', 'candidateRows')}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('edition', 'output', 'work', 'diagnostic'):
        parser.add_argument('--' + name, type=Path, required=name in ('edition', 'output'))
    a = parser.parse_args()
    if bool(a.work) != bool(a.diagnostic):
        parser.error('--work and --diagnostic must be supplied together')
    print(json.dumps(audit(a.edition, a.output, a.work, a.diagnostic), ensure_ascii=False, indent=2))
