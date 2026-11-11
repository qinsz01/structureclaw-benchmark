"""Find conservative independent L3 nodal-load witnesses in failed deliveries.

This is not a new grader. Nonmatching representations and other failure kinds
remain explicitly unresolved. No candidate, solver or authoring load helper runs.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

from .audit_load_arithmetic import reconstruct, supplied, difference


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sealed(root, descriptor):
    path = root / descriptor['path']
    if path.is_symlink() or sha(path) != descriptor['sha256']:
        raise ValueError('Bound file changed: ' + descriptor['path'])
    return read(path)


def active_factors(model, selection):
    if selection['kind'] == 'case':
        return {selection['id']: 1}
    return next(c['factors'] for c in model['load_combinations'] if c['id'] == selection['id'])


def vectors(model, selection, node_map):
    if model.get('unit_system') != 'SI' or model['analysis_control'].get('self_weight') is not False:
        raise ValueError('Independent nodal comparison requires SI and explicit gravity')
    table = {target: [0.0] * 6 for target in node_map.values()}
    for cid, factor in active_factors(model, selection).items():
        if not factor:
            continue
        case = next(c for c in model['load_cases'] if c['id'] == cid)
        for load in case['loads']:
            if load['type'] != 'nodal' or load.get('reference_frame', 'global') != 'global':
                raise ValueError('Independent witness is limited to global nodal-load representations')
            values = table[node_map[load['node']]]
            for i, component in enumerate(('fx', 'fy', 'fz', 'mx', 'my', 'mz')):
                values[i] += factor * load.get(component, 0)
    return table


def node_mapping(actual, expected):
    if len(actual['nodes']) != len(expected['nodes']):
        raise ValueError('Node refinement or differing geometry requires a separate review')
    mapping = {}
    for node in actual['nodes']:
        matches = [n for n in expected['nodes'] if math.dist([node[k] for k in 'xyz'], [n[k] for k in 'xyz']) <= 1e-8]
        if len(matches) != 1:
            raise ValueError('No unique geometric node correspondence')
        mapping[node['id']] = matches[0]['id']
    if len(set(mapping.values())) != len(expected['nodes']):
        raise ValueError('Geometric node correspondence is not bijective')
    return mapping


def run(edition, work, diagnostic, public_audit, output):
    manifest, grade, prior = read(edition / 'manifest.json'), read(diagnostic), read(public_audit)
    manifest_sha = sha(edition / 'manifest.json')
    if (grade['manifestSha256'] != manifest_sha or prior['manifestSha256'] != manifest_sha or not prior['allPassed']
            or grade['indexSha256'] != sha(work / 'index.json')):
        raise ValueError('Frozen corpus/index/public arithmetic audit binding differs')
    index = read(work / 'index.json')
    entries = {r['evidenceId']: r for r in index['entries']}
    rows = []
    for score in grade['rows']:
        if score['outcome'] == 'passed':
            continue
        c = next(c for c in manifest['cases'] if c['id'] == score['caseId'])
        t = next(t for t in c['turns'] if t['id'] == score['turnId'])
        result = {'caseId': c['id'], 'turnId': t['id'], 'outcome': score['outcome'],
                  'independentInputMismatchDemonstrated': False, 'witnesses': [], 'limitations': []}
        rows.append(result)
        ref = sealed(edition, next(f for f in manifest['files'] if f['path'] == t['private']))
        if ref['kind'] != 'analysis' or c['level'] != 'L3' or not score.get('evidenceMapping'):
            result['limitations'].append('Not a resolved L3 static final delivery; requires separate review')
            continue
        capture = next(r for r in index['turns'] if r['caseId'] == c['id'] and r['turnId'] == t['id'])
        answer = sealed(work, capture['answer'])
        state_by_id = {}
        for mapping in score['evidenceMapping']:
            identity = mapping['evidenceId']
            entry = entries[identity]
            if entry['caseId'] != c['id'] or int(entry['turnId'][1:]) > int(t['id'][1:]):
                raise ValueError('Wrong-case/future evidence in diagnostic')
            receipt, state = sealed(work, entry['files']['receipt']), sealed(work, entry['files']['state'])
            if not receipt['ok'] or receipt['role'] != 'candidate' or receipt['stateSha256'] != entry['files']['state']['sha256']:
                raise ValueError('Native receipt binding differs')
            state_by_id[identity] = state
        # Reported native identities are already canonical broker IDs in this
        # full-run protocol; the independent grade records their exact mapping.
        reported_to_id = {m['reported']: m['evidenceId'] for m in score['evidenceMapping']}
        groups = answer.get('jobIdsByScenario') or answer.get('runIdsByScenario') or {}
        for scenario in ref['scenarios']:
            model = scenario['model']
            integrated = reconstruct(model, scenario['loadRules'])
            difference(integrated, supplied(model))
            # Distributed-member models need density/first-moment witnesses,
            # so this conservative nodal-only diagnostic does not judge them.
            if any(integrated[1][cid] for cid in ('D', 'Q', 'W')):
                result['limitations'].append(scenario['id'] + ': distributed loads need separate density review')
                continue
            identities = [reported_to_id[i] for i in groups.get(scenario['id'], [])]
            for selection in scenario['selections']:
                expected = {n['id']: [0.0] * 6 for n in model['nodes']}
                for cid, factor in active_factors(model, selection).items():
                    for nid, values in integrated[0][cid].items():
                        for i, value in enumerate(values):
                            expected[nid][i] += factor * value
                comparisons, unsupported = [], []
                for identity in identities:
                    state = state_by_id[identity]
                    for native_key in state.get('analysisResult', {}).get('results', {}):
                        kind, native_id = native_key.split(':', 1)
                        try:
                            actual = vectors(state['model'], {'kind': kind, 'id': native_id}, node_mapping(state['model'], model))
                            mismatch = []
                            for nid, values in expected.items():
                                for i, issued in enumerate(values):
                                    observed = actual[nid][i]
                                    # This threshold is deliberately much looser
                                    # than evaluator tolerance. Tiny rounding is
                                    # never used to claim an independent error.
                                    scale = 1e-4 * (1 + abs(issued))
                                    mismatch.append({'joint': nid, 'component': ('fx', 'fy', 'fz', 'mx', 'my', 'mz')[i],
                                                     'candidate': observed, 'independentlyIntegrated': issued,
                                                     'absoluteDifference': abs(observed - issued), 'conservativeThreshold': scale,
                                                     'ratioToConservativeThreshold': abs(observed - issued) / scale,
                                                     'unit': 'kN' if i < 3 else 'kN.m'})
                            worst = max(mismatch, key=lambda r: r['ratioToConservativeThreshold'])
                            comparisons.append({'jobId': identity, 'nativeSelection': {'kind': kind, 'id': native_id}, 'worstDifference': worst})
                        except (ValueError, KeyError, StopIteration) as error:
                            unsupported.append({'jobId': identity, 'nativeSelection': native_key, 'reason': str(error)})
                if comparisons and not unsupported:
                    closest = min(comparisons, key=lambda r: r['worstDifference']['ratioToConservativeThreshold'])
                    if closest['worstDifference']['ratioToConservativeThreshold'] > 1:
                        result['witnesses'].append({'scenario': scenario['id'], 'requiredSelection': selection,
                                                   'allReportedExecutionsCompared': len(comparisons),
                                                   'closestReportedExecution': closest, 'comparisons': comparisons})
                elif unsupported:
                    result['limitations'].append({'scenario': scenario['id'], 'selection': selection, 'unresolvedRepresentations': unsupported})
        result['independentInputMismatchDemonstrated'] = bool(result['witnesses'])
    summary = {'kind': 'research300-v32-full-independent-nodal-load-review', 'formalComparisonScore': False,
               'candidateInvocations': 0, 'nativeSolverInvocations': 0, 'originalAnswersModified': False,
               'manifestSha256': manifest_sha, 'diagnosticSha256': sha(diagnostic),
               'sourceSha256': sha(Path(__file__)), 'publicArithmeticAudit': {'path': str(public_audit), 'sha256': sha(public_audit)},
               'nonpassedTurns': len(rows), 'turnsWithIndependentInputWitness': sum(r['independentInputMismatchDemonstrated'] for r in rows),
               'remainingSeparateReview': sum(not r['independentInputMismatchDemonstrated'] for r in rows), 'rows': rows,
               'scope': 'Final reported L3 static evidence with unique geometric node matching and only global nodal loads. Uses independent Gauss integration; frozen public-rule correspondence was checked in the linked earlier audit. Not a new external blind geometry review. Other failures and alternative representations remain unresolved.'}
    with output.open('x') as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write('\n')
    return {k: v for k, v in summary.items() if k != 'rows'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('edition', 'work', 'diagnostic', 'public-audit', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    a = parser.parse_args()
    print(json.dumps(run(a.edition, a.work, a.diagnostic, a.public_audit, a.output), ensure_ascii=False, indent=2))
