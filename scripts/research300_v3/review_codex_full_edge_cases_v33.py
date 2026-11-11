"""Review signed end actions and remaining rigid-project load-density failures.

This reads original sealed evidence; it changes neither answers nor scores.
The rigid-project witness independently integrates public Q and uses the frozen
reference D distribution, checking candidate D against it. It compares only the
absolutely continuous part of projected loads; nodal/vertical-member measures
cannot cancel a discrepancy over an open horizontal interval.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from .audit_project_q_density_v32 import read, sha, sealed, issued_density, executed_density, compare


def continuous(model, selection):
    model = deepcopy(model)
    nodes = {n['id']: n for n in model['nodes']}
    members = {e['id']: e for e in model['elements']}
    for case in model['load_cases']:
        retained = []
        for load in case['loads']:
            if load['type'] == 'nodal':
                continue
            if load['type'] != 'distributed':
                raise ValueError('Unreviewed continuous load representation')
            a, b = [nodes[n] for n in members[load['element']]['nodes']]
            if abs(a['x'] - b['x']) > 1e-10:
                retained.append(load)
        case['loads'] = retained
    intervals, _ = executed_density(model, selection)
    return intervals, {}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('edition', 'work', 'report'):
        parser.add_argument('--' + name, type=Path, required=True)
    a = parser.parse_args()
    manifest, index = read(a.edition / 'manifest.json'), read(a.work / 'index.json')
    grade = read(a.report / 'diagnostic-reviewed.json')
    assert grade['manifestSha256'] == sha(a.edition / 'manifest.json')
    assert grade['indexSha256'] == sha(a.work / 'index.json')
    files = {r['path']: r for r in manifest['files']}
    entries = {r['evidenceId']: r for r in index['entries']}
    inventory = {r['path']: r for r in read(a.work / 'artifact-inventory.json')['files']}

    def state(identity):
        entry = entries[identity]
        receipt = sealed(a.work, entry['files']['receipt'])
        assert receipt['ok'] and receipt['role'] == 'candidate'
        assert receipt['stateSha256'] == entry['files']['state']['sha256']
        return sealed(a.work, entry['files']['state'])

    def turn(case_id, turn_id):
        case = next(c for c in manifest['cases'] if c['id'] == case_id)
        t = next(t for t in case['turns'] if t['id'] == turn_id)
        capture = next(t for t in index['turns'] if t['caseId'] == case_id and t['turnId'] == turn_id)
        score = next(t for t in grade['rows'] if t['caseId'] == case_id and t['turnId'] == turn_id)
        return sealed(a.edition, files[t['private']]), sealed(a.work, capture['answer']), score, t

    signs = []
    for tid in ('t1', 't2'):
        ref, answer, score, t = turn('V3-INT-006', tid)
        assert score['outcome'] == 'candidate_failure' and len(answer['jobIds']) == 1
        identity = answer['jobIds'][0]
        job = state(identity)
        raw_path = f'solver-jobs/V3-INT-006/{identity}/worker.stdout.json'
        native = sealed(a.work, inventory[raw_path])['data']['data']
        assert native['execution']['constitutiveModel'] == 'linear-elastic'
        assert native['execution']['executed'] and native['execution']['analysisReturnCode'] == 0
        rows = []
        for q in ref['requests']:
            report = next(r for r in answer['quantities'] if r['id'] == q['id'])
            if q['location']['kind'] == 'member':
                assert q['component'] == 'M2' and q['location']['positionM'] == 0 and q['location']['side'] == 'right'
                raw = native['forces'][q['location']['id']]['n1']['M2']
                observed = -raw
                pointer = f"/data/data/forces/{q['location']['id']}/n1/M2"
                interpretation = 'i-end resisting action negated to obtain the right-face section action'
            elif q['component'] == 'uz':
                raw = observed = native['displacements'][q['location']['id']]['uz']
                pointer = f"/data/data/displacements/{q['location']['id']}/uz"
                interpretation = 'native global displacement, unchanged'
            else:
                continue
            tolerance = q['tolerance']['absolute'] + q['tolerance']['relative'] * abs(q['value'])
            assert abs(observed - q['value']) <= tolerance
            rows.append({'requestId': q['id'], 'nativeRawValue': raw, 'physicalRequestedValue': observed,
                         'reportedValue': report['value'], 'referenceValue': q['value'], 'unit': q['unit'],
                         'absoluteReportError': abs(report['value'] - observed), 'tolerance': tolerance,
                         'reportMatches': abs(report['value'] - observed) <= tolerance,
                         'rawJsonPointer': pointer, 'interpretation': interpretation})
        assert len([r for r in rows if not r['reportMatches']]) == 2
        signs.append({'caseId': 'V3-INT-006', 'turnId': tid, 'jobId': identity, 'outcome': score['outcome'],
                      'nativeFile': raw_path, 'nativeFileSha256': inventory[raw_path]['sha256'],
                      'answerSha256': score['originalAnswerSha256'], 'rows': rows})

    density = []
    prior = read(a.report / 'independent-project-Q-witnesses.json')
    for remaining in prior['candidateRows']:
        if remaining['independentInputMismatchDemonstrated']:
            continue
        cid, tid = remaining['caseId'], remaining['turnId']
        ref, answer, score, _ = turn(cid, tid)
        assert ref['integration'] == 'rigid'
        truth = next(t for t in ref['truths'] if t['choice'] == answer['design'])
        reference_model = {**ref['combinedTemplate'], 'load_cases': truth['combinedLoadCases']}
        q = issued_density(ref['upperTemplate'], ref['loadRules'])
        # Public rule identity was checked from verbatim task revisions by the
        # independently bound Q audit; this verifies the selected reference too.
        assert prior['referenceChecksAllPassed']
        assert compare(continuous(reference_model, {'kind': 'case', 'id': 'Q'}), q)['worstDifference']['absoluteDifference'] < 1e-8
        d = continuous(reference_model, {'kind': 'case', 'id': 'D'})
        factors = next(c['factors'] for c in reference_model['load_combinations'] if c['id'] == 'SERVICE')
        assert factors == {'D': 1, 'Q': 1}
        expected = (d[0] + q[0], {})
        comparisons, q_checks = [], []
        for identity in answer['jobIdsByModel']['combined']:
            job = state(identity)
            delta_d = compare(continuous(job['model'], {'kind': 'case', 'id': 'D'}), d)
            assert delta_d['worstDifference']['ratioToConservativeThreshold'] <= 1
            delta_q = compare(continuous(job['model'], {'kind': 'case', 'id': 'Q'}), q)
            q_checks.append({'jobId': identity, 'DMatchesFrozenReference': True, **delta_q})
            for key in job['analysisResult']['results']:
                kind, sid = key.split(':', 1)
                comparisons.append({'jobId': identity, 'nativeSelection': key,
                                    **compare(continuous(job['model'], {'kind': kind, 'id': sid}), expected)})
        closest = min(comparisons, key=lambda r: r['worstDifference']['ratioToConservativeThreshold'])
        assert closest['worstDifference']['ratioToConservativeThreshold'] > 1
        density.append({'caseId': cid, 'turnId': tid, 'independentInputMismatchDemonstrated': True,
                        'requiredSelection': {'kind': 'combination', 'id': 'SERVICE'},
                        'closestReportedExecution': closest, 'comparisons': comparisons, 'QChecks': q_checks})
    result = {'kind': 'codex-full-signed-report-and-rigid-load-review', 'formalComparisonScore': False,
              'candidateInvocations': 0, 'nativeSolverInvocations': 0, 'originalAnswersModified': False,
              'diagnosticSha256': sha(a.report / 'diagnostic-reviewed.json'), 'sourceSha256': sha(Path(__file__)),
              'baseDensityHelperSha256': sha(Path(__file__).with_name('audit_project_q_density_v32.py')),
              'priorPublicQAuditSha256': sha(a.report / 'independent-project-Q-witnesses.json'),
              'signedReportFailures': signs, 'rigidLoadFailures': density, 'scope': __doc__}
    with (a.report / 'edge-case-failure-review.json').open('x') as f:
        json.dump(result, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write('\n')
    lines = ['# 实际交付中的正确字段与错误字段', '',
             'V3-INT-006 两轮均被判为失败。下表展示同一原生作业中的位移正确、弯矩符号错误；不能因为一个位移吻合就把整份交付标为可靠。', '',
             '| 轮次 | 请求 | 软件原字段 | 约定下的物理量 | 候选报告 | 单位 | 判定 |',
             '| --- | --- | ---: | ---: | ---: | --- | --- |']
    for t in signs:
        for r in t['rows']:
            lines.append(f"| {t['turnId']} | {r['requestId']} | {r['nativeRawValue']:.12g} | {r['physicalRequestedValue']:.12g} | {r['reportedValue']:.12g} | {r['unit']} | {'通过' if r['reportMatches'] else '符号错误'} |")
    lines += ['', '公共接口约定要求带符号的物理截面内力，并明确提示原始杆端抵抗力的符号约定不同。这里 i 端原生抵抗弯矩取反，才是 x=0、right 面的 M2；原始字段直接照抄仍会交付错误的物理量。', '',
              '逐字段 JSON 指针、原始文件哈希、容差及四轮刚接综合题的荷载差异见 [完整复核](edge-case-failure-review.json)。', '',
              '原先预设为通过案例的展示脚本因整题未通过而停止；原失败日志保留。本文件如实展示失败，不修改评分。']
    (a.report / 'worked-trace-v2.md').write_text('\n'.join(lines) + '\n')
    print(json.dumps({'signedReportFailureTurns': len(signs), 'rigidLoadFailureTurns': len(density)}))


if __name__ == '__main__':
    main()
