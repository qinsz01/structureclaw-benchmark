"""Account for every nonpassing original delivery with explicit review evidence."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import statistics


def read(p):
    return json.loads(p.read_bytes())


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write(p, data):
    with p.open('x') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for n in ('edition', 'work', 'report'):
        parser.add_argument('--' + n, type=Path, required=True)
    a = parser.parse_args()
    report = a.report
    sources = ['diagnostic.json', 'diagnostic-reviewed.json', 'policy-v33/diagnostic-v33.json',
               'independent-load-witnesses.json', 'independent-project-Q-witnesses.json', 'edge-case-failure-review.json']
    raw, reviewed, final, nodal, q, edge = [read(report / p) for p in sources]
    assert final['policyRevision']['predecessorDiagnosticSha256'] == sha(report / sources[1])
    assert final['policyRevision']['all560LegacyRowsReplayed'] and final['policyRevision']['allPreviouslyPassingRowsRetained']
    assert final['policyRevision']['allControlsPassed']
    key = lambda r: (r['caseId'], r['turnId'])
    new = {key(r): r for r in final['rows']}
    assert len(raw['rows']) == len(new) == 560
    tables = [
        ('candidate_nodal_load_error', {key(r): ('independent-load-witnesses.json', r) for r in nodal['rows'] if r['independentInputMismatchDemonstrated']}),
        ('candidate_project_Q_density_error', {key(r): ('independent-project-Q-witnesses.json', r) for r in q['candidateRows'] if r['independentInputMismatchDemonstrated']}),
        ('candidate_rigid_project_Q_density_error', {key(r): ('edge-case-failure-review.json', r) for r in edge['rigidLoadFailures']}),
        ('candidate_signed_report_error', {key(r): ('edge-case-failure-review.json', r) for r in edge['signedReportFailures']}),
        ('native_environment_block', {key(r): ('diagnostic-reviewed.json', r) for r in reviewed['rows'] if r['outcome'] == 'blocked_configuration'}),
        ('evaluator_inactive_load_false_rejection', {key(r): ('policy-v33/diagnostic-v33.json', r) for r in final['policyRevision']['changes']}),
    ]
    rows = []
    for original in raw['rows']:
        k = key(original)
        if original['outcome'] == 'passed':
            assert new[k]['outcome'] == 'passed'
            continue
        matches = [(category, table[k]) for category, table in tables if k in table]
        assert len(matches) == 1, f'Every original failure needs exactly one final supported attribution: {k}'
        category, (source, witness) = matches[0]
        expected = 'passed' if category.startswith('evaluator_') else 'blocked_configuration' if category == 'native_environment_block' else 'candidate_failure'
        assert new[k]['outcome'] == expected
        example = None
        if category == 'candidate_nodal_load_error':
            choices = [r['closestReportedExecution']['worstDifference'] for r in witness['witnesses']]
            assert choices and all(r['ratioToConservativeThreshold'] > 1 for r in choices)
            example = max(choices, key=lambda r: r['ratioToConservativeThreshold'])
        elif category in ('candidate_project_Q_density_error', 'candidate_rigid_project_Q_density_error'):
            example = witness['closestReportedExecution']['worstDifference']
            assert example['ratioToConservativeThreshold'] > 1
        elif category == 'candidate_signed_report_error':
            example = [r for r in witness['rows'] if not r['reportMatches']]
            assert example
        elif category == 'native_environment_block':
            assert witness['environmentReview']['sourceFaults']
        else:
            assert witness['from'] == 'candidate_failure' and witness['to'] == 'passed'
        rows.append({'caseId': k[0], 'turnId': k[1], 'originalV32Outcome': original['outcome'],
                     'reviewedV33Outcome': new[k]['outcome'], 'attribution': category,
                     'evidenceFile': source, 'evidenceSha256': sha(report / source), 'example': example,
                     'originalAnswerSha256': original['originalAnswerSha256']})
    assert len(rows) == sum(r['outcome'] != 'passed' for r in raw['rows'])
    failure_review = {'kind': 'codex-full-exhaustive-failure-review', 'formalComparisonScore': False,
                      'externalEngineerReview': False, 'originalAnswersModified': False,
                      'originalNonpassedTurns': len(rows), 'unresolvedAttributions': 0,
                      'counts': dict(Counter(r['attribution'] for r in rows)), 'rows': rows,
                      'sourceBindings': {p: sha(report / p) for p in sources}, 'reviewScriptSha256': sha(Path(__file__)),
                      'scope': 'All original nonpasses assigned from explicit sealed evidence, conservative independently implemented load witnesses, or the versioned full-policy regrade. This is not independent external engineering adjudication and does not certify arbitrary free text.'}
    write(report / 'failure-review.json', failure_review)
    manifest = read(a.edition / 'manifest.json')
    execution = read(a.work / 'execution-summary.json')
    spec = read(a.work / 'execution-specification.json')
    records = []
    for c in manifest['cases']:
        for t in c['turns']:
            e = read(a.work / 'runs' / c['id'] / t['id'] / 'execution.json')
            records.append({'caseId': c['id'], 'turnId': t['id'], 'family': c['family'], 'level': c['level'], 'engine': c['engine'],
                            'outcome': new[(c['id'], t['id'])]['outcome'], 'cliInvocations': e['actualModelCalls'],
                            'cliToolCalls': e['toolCallsObserved'], 'nativeRequests': len(e['currentJobIds']), 'elapsedSeconds': e['elapsedSeconds']})
    assert len(records) == 560 and sum(r['nativeRequests'] for r in records) == execution['nativeCandidateAttempts']
    def aggregate(rs):
        return {'turns': len(rs), 'outcomes': dict(Counter(r['outcome'] for r in rs)),
                'cliInvocations': sum(r['cliInvocations'] for r in rs), 'cliToolCalls': sum(r['cliToolCalls'] for r in rs),
                'nativeRequests': sum(r['nativeRequests'] for r in rs),
                'meanNativeRequests': statistics.mean(r['nativeRequests'] for r in rs),
                'medianNativeRequests': statistics.median(r['nativeRequests'] for r in rs),
                'meanTurnSeconds': statistics.mean(r['elapsedSeconds'] for r in rs),
                'medianTurnSeconds': statistics.median(r['elapsedSeconds'] for r in rs)}
    groups = {k: {v: aggregate([r for r in records if r[k] == v]) for v in sorted({r[k] for r in records})}
              for k in ('family', 'level', 'engine')}
    summary = {'kind': 'codex-full-v33-results-and-execution-cost', 'formalComparisonScore': False, 'postHocPolicyRevision': True,
               'cases': 300, 'turns': 560, 'v32Counts': reviewed['counts'], 'v33Counts': final['counts'],
               'v32CaseCounts': reviewed['caseCounts'], 'v33CaseCounts': final['caseCounts'],
               'totals': aggregate(records), 'groups': groups,
               'individualModelApiRequests': None, 'dollarCost': None,
               'costNote': 'CLI invocations count starts/resumes; tool calls and native requests are distinct. Per-turn elapsed averages include parallel execution and are not total wall-clock duration.',
               'sourceUnchangedAfterRun': execution['sourceUnchangedAfterRun'], 'remoteSourceVerifiedAfterRun': execution['remoteSourceVerifiedAfterRun'],
               'harnessErrors': execution['harnessErrors'], 'sourceBinding': {p: sha(report / p) for p in sources[:3]},
               'executionSpecificationSha256': sha(a.work / 'execution-specification.json'), 'sutCommit': spec['sutCommit'],
               'sourceSha256': sha(Path(__file__))}
    write(report / 'results-summary.json', summary)
    print(json.dumps({'allOriginalFailuresReviewed': len(rows), 'attributionCounts': failure_review['counts'],
                      'v33Counts': final['counts'], 'cost': summary['totals']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
