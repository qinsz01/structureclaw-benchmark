"""Recompute reviewer-facing evidence from retained files; never run candidates."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EDITION = ROOT / 'corpora/research300-v3-v1'
REVIEWS = ROOT / 'docs/implementation/reviews'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def summarize(manifest, grade):
    cases = {c['id']: c for c in manifest['cases']}
    expected = {(c['id'], t['id']) for c in cases.values() for t in c['turns']}
    rows = grade['rows']
    observed = {(r['caseId'], r['turnId']) for r in rows}
    if len(cases) != len(manifest['cases']) or len(expected) != sum(len(c['turns']) for c in cases.values()):
        raise ValueError('Duplicate issued identity')
    if len(observed) != len(rows) or observed != expected:
        raise ValueError('Missing, duplicated or unissued grade rows')
    if any(type(r.get('passed')) is not bool for r in rows):
        raise ValueError('Retained development grade must have explicit Boolean outcomes')
    passed = {(r['caseId'], r['turnId']) for r in rows if r['passed']}
    complete = {cid for cid, c in cases.items() if all((cid, t['id']) in passed for t in c['turns'])}
    def group(field):
        result = {}
        for key in sorted({str(c[field]) for c in cases.values()}):
            selected = [c for c in cases.values() if str(c[field]) == key]
            pairs = {(c['id'], t['id']) for c in selected for t in c['turns']}
            result[key] = {'cases': len(selected), 'turns': len(pairs),
                           'passedCases': sum(c['id'] in complete for c in selected),
                           'passedTurns': len(pairs & passed)}
        return result
    return {'cases': len(cases), 'turns': len(expected), 'passedCases': len(complete), 'passedTurns': len(passed),
            'groups': {field: group(field) for field in ('family', 'level', 'engine', 'analysis', 'origin', 'split')},
            'uniqueTopologyFingerprints': len({c['topologyFingerprint'] for c in cases.values()}),
            'formalComparisonScore': False,
            'scope': 'Retained development answers, rescored after full-suite evaluator repair; not untouched holdout evidence'}


def audit(replay_path=None):
    sources = {}
    def read(file):
        data = file.read_bytes()
        sources[str(file.relative_to(ROOT)) if file.is_relative_to(ROOT) else str(file)] = sha(data)
        return json.loads(data)
    manifest = read(EDITION / 'manifest.json')
    manifest_sha = sources[str((EDITION / 'manifest.json').relative_to(ROOT))]
    retained = read(REVIEWS / 'research300-v3-codex-full-20261028/codex-full-reviewed.json')
    if retained['manifestSha256'] != manifest_sha or retained.get('formalComparisonScore') is not False:
        raise ValueError('Development evidence edition/eligibility mismatch')
    qualification = read(REVIEWS / 'research300-v3-codex-full-20261028/qualification-v31-summary.json')
    expected = {(c['id'], t['id']) for c in manifest['cases'] for t in c['turns']}
    qrows = qualification['rows']
    if (qualification['manifestSha256'] != manifest_sha or len(qrows) != len(expected)
            or {(r['caseId'], r['turnId']) for r in qrows} != expected):
        raise ValueError('Historical qualification coverage mismatch')
    historical = {'revision': 'v3.1', 'turns': len(qrows),
                  'positivePassed': sum(r['positive'] for r in qrows),
                  'controls': sum(r['controls'] for r in qrows),
                  'controlFailures': sum(len(r.get('controlFailures', [])) for r in qrows),
                  'evidenceType': 'Retained maintainer qualification, not new execution or external expert review'}
    for name, expected_sha in qualification['codeBinding'].items():
        if sha((ROOT / 'scripts/research300_v3' / name).read_bytes()) != expected_sha:
            raise ValueError('Historical scoring source changed: ' + name)
    historical['frozenScoringSourcesVerified'] = True
    stats = summarize(manifest, retained)
    tolerances = Counter()
    for c in manifest['cases']:
        for t in c['turns']:
            ref = json.loads((EDITION / t['private']).read_bytes())
            for q in ref.get('requests', []):
                tol = q.get('tolerance', {})
                quantity = q.get('component') or '.'.join('[]' if isinstance(x, int) else x for x in q.get('path', [])) or 'unspecified'
                tolerances[(quantity, q.get('unit'),
                            tol.get('absolute'), tol.get('relative'))] += 1
    replay = read(replay_path) if replay_path else None
    if replay and (replay.get('kind') != 'research300-v3-offline-regression' or replay.get('manifestSha256') != manifest_sha):
        raise ValueError('Offline replay edition/type mismatch')
    return {'kind': 'research300-v3-reviewer-evidence-audit', 'manifestSha256': manifest_sha,
            'development': stats, 'historicalQualification': historical,
            'requestToleranceInventory': [{'component': k[0], 'unit': k[1], 'absolute': k[2], 'relative': k[3], 'requests': n}
                                          for k, n in sorted(tolerances.items(), key=lambda item: json.dumps(item[0]))],
            'offlineV32Regression': {k: v for k, v in replay.items() if k not in ('rows', 'sourceCode')} if replay else None,
            'externalExpertReviewVerifiedByThisAudit': False, 'matchedAblationsVerifiedByThisAudit': False,
            'formalExternalBaselineVerifiedByThisAudit': False, 'currentNativeCollectorQualifiedByThisAudit': False,
            'formalComparisonScore': False, 'candidateInvocations': 0, 'nativeSolverInvocations': 0, 'sourceSha256': sources}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--replay-summary', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.replay_summary.resolve() if args.replay_summary else None)
    with args.output.open('x') as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    print(json.dumps({k: result['development'][k] for k in ('cases', 'turns', 'passedCases', 'passedTurns')}))
