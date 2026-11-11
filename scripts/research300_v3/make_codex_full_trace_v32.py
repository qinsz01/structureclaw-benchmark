"""Build a compact worked evidence chain from the new sealed full regression."""
import argparse
import hashlib
import json
import os
from pathlib import Path


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('edition', 'work', 'diagnostic', 'report'):
        parser.add_argument('--' + name, type=Path, required=True)
    a = parser.parse_args()
    edition, work, diagnostic, report = [getattr(a, k).resolve() for k in ('edition', 'work', 'diagnostic', 'report')]
    grade, index, manifest = read(diagnostic), read(work / 'index.json'), read(edition / 'manifest.json')
    if grade['indexSha256'] != sha(work / 'index.json') or grade['manifestSha256'] != sha(edition / 'manifest.json'):
        raise ValueError('Diagnostic source bindings differ')
    inventory = {f['path']: f for f in read(work / 'artifact-inventory.json')['files']}

    def original(path):
        relative = path.relative_to(work).as_posix()
        if path.is_symlink() or inventory[relative]['sha256'] != sha(path):
            raise ValueError('Original evidence changed')
        return {'path': os.path.relpath(path, report), 'sha256': sha(path)}

    case = next(c for c in manifest['cases'] if c['id'] == 'V3-INT-006')
    rows = []
    for turn in case['turns']:
        cid, tid = case['id'], turn['id']
        score = next(r for r in grade['rows'] if r['caseId'] == cid and r['turnId'] == tid)
        if score['outcome'] != 'passed':
            raise ValueError('Worked passing example is not a verified passing delivery')
        run = work / 'runs' / cid / tid
        answer, execution = read(run / 'answer.json'), read(run / 'execution.json')
        if len(answer['jobIds']) != 1 or execution['currentJobIds'] != answer['jobIds']:
            raise ValueError('Expected one fresh actual native job per turn')
        job = work / 'solver-jobs' / cid / answer['jobIds'][0]
        model, worker, receipt = read(job / 'model.json'), read(job / 'worker.stdout.json'), read(job / 'broker-receipt.json')
        if not receipt['ok'] or not worker['ok'] or not worker['data']['success']:
            raise ValueError('Native software did not succeed')
        native = worker['data']['data']['displacements']['J003']['uz']
        reference = read(edition / turn['private'])
        request = next(q for q in reference['requests'] if q['id'] == 'case:D:J003:uz')
        delivered = next(q for q in answer['quantities'] if q['id'] == request['id'])
        tolerance = request['tolerance']['absolute'] + request['tolerance']['relative'] * abs(request['value'])
        if delivered['unit'] != 'm' or delivered['value'] != native or abs(native - request['value']) > tolerance:
            raise ValueError('Native, reference and delivered values do not agree')
        files = {name: original(path) for name, path in {
            'issuedMessage': run / 'issued-packet' / tid / 'user-message.txt',
            'submittedRequest': job / 'submitted-request.json', 'executedModel': job / 'model.json',
            'softwareStdout': job / 'worker.stdout.json', 'receipt': job / 'broker-receipt.json',
            'answer': run / 'answer.json', 'execution': run / 'execution.json',
        }.items()}
        files['reference'] = {'path': os.path.relpath(edition / turn['private'], report), 'sha256': sha(edition / turn['private'])}
        rows.append({'caseId': cid, 'turnId': tid, 'jobId': answer['jobIds'][0], 'threadId': execution['threadId'],
                     'issuedMessage': (run / 'issued-packet' / tid / 'user-message.txt').read_text(),
                     'deadLoads': next(c['loads'] for c in model['load_cases'] if c['id'] == 'D'),
                     'softwareJsonPointer': '/data/data/displacements/J003/uz', 'nativeValueM': native,
                     'reportedValueM': delivered['value'], 'referenceValueM': request['value'],
                     'nativeReferenceAbsoluteErrorM': abs(native - request['value']), 'allowedErrorM': tolerance,
                     'files': files})
    if len(rows) != 2 or rows[0]['threadId'] != rows[1]['threadId'] or rows[0]['jobId'] == rows[1]['jobId']:
        raise ValueError('Expected same-thread revision with distinct native execution identities')
    result = {'kind': 'research300-v32-full-worked-trace', 'formalComparisonScore': False,
              'diagnosticSha256': sha(diagnostic), 'sourceSha256': sha(Path(__file__)),
              'candidateInvocations': 0, 'nativeSolverInvocations': 0, 'rows': rows,
              'scope': 'This trace demonstrates the checked structured displacement and revised native input, not all free-text claims or general engineering safety.'}
    with (report / 'worked-trace.json').open('x') as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    lines = ['# 一道题的完整证据链：V3-INT-006', '',
             '本例来自这次 300 题全量运行。第二轮要求把 D 工况荷载乘以 1.2；候选沿用同一会话，提交新模型并产生新的原生作业。', '',
             '| 轮次 | 两根梁的 D 线荷载 | 软件直出 J003 的 uz | 原样报告 | 独立参考 |',
             '| --- | --- | --- | --- | --- |']
    for row in rows:
        loads = ', '.join(str(load['wz']) for load in row['deadLoads'])
        lines.append(f"| {row['turnId']} | {loads} kN/m | {row['nativeValueM']:.17g} m | {row['reportedValueM']:.17g} m | {row['referenceValueM']:.17g} m |")
    lines += ['', '每个交付值直接对应原生输出的 `/data/data/displacements/J003/uz`；与独立参考的差异和容差见 [机器可读记录](worked-trace.json)。原生回执、输入与输出均按原始封存清单校验。', '']
    for row in rows:
        links = ' · '.join(f"[{label}](<{row['files'][key]['path']}>)" for key, label in
                           [('issuedMessage', '签发消息'), ('submittedRequest', '候选原始请求'), ('executedModel', '实际模型'),
                            ('softwareStdout', '原生软件输出'), ('receipt', '控制端回执'), ('answer', '原始交付')])
        lines += [f"{row['turnId']}，作业 `{row['jobId']}`：{links}。", '']
    lines += ['这是对已检查结构化字段的具体证据；不能由此推断任意自由文本均无幻觉，也不替代工程师对适用范围的判断。', '']
    with (report / 'worked-trace.md').open('x') as handle:
        handle.write('\n'.join(lines))
    print(json.dumps({'turns': len(rows), 'report': str(report / 'worked-trace.md')}))


if __name__ == '__main__':
    main()
