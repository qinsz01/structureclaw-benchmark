"""Clarify CLI invocations without rewriting frozen records or answer bytes.

The frozen runner's ``actualModelCalls`` is len(attempts): CLI process
invocations, not individual model API requests inside an agent turn.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def answer_hashes(workbook):
    assembled = {}
    for row in workbook['Codex原始作答'].iter_rows(min_row=2, values_only=True):
        if not row[2]:
            continue
        record = assembled.setdefault((row[0], row[1]), {'encoding': row[4], 'parts': [], 'sha256': row[3]})
        if row[5] != len(record['parts']) + 1:
            raise ValueError('Original answer chunks are not in order')
        record['parts'].append(row[7] or '')
    result = {}
    for key, record in assembled.items():
        text = ''.join(record['parts'])
        raw = text.encode('utf-8') if record['encoding'] == 'utf-8' else base64.b64decode(text, validate=True)
        digest = hashlib.sha256(raw).hexdigest()
        if digest != record['sha256']:
            raise ValueError('Exported answer differs from its sealed digest')
        result['/'.join(key)] = digest
    return result


def main():
    from openpyxl import load_workbook

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--export', required=True, type=Path)
    a = p.parse_args()
    root = a.export.resolve()
    source = root / 'catalogue.xlsx'
    output = root / 'catalogue-clarified.xlsx'
    report = root / 'cost-accounting-clarification.json'
    if output.exists() or report.exists():
        raise FileExistsError('Clarification artifacts already exist')
    source_digest = sha(source)
    summary = json.loads((root / 'summary.json').read_bytes())
    executions = json.loads((root / 'execution-index.json').read_bytes())['rows']
    invocation_count = sum(len(r['attempts']) for r in executions)
    if any(r['actualModelCalls'] != len(r['attempts']) for r in executions):
        raise ValueError('The observed counter no longer denotes CLI invocations')
    if summary['actualModelCalls'] != invocation_count:
        raise ValueError('CLI invocation count differs between export and execution records')
    workbook = load_workbook(source)
    original_answers = answer_hashes(workbook)
    sheet = workbook['560轮评分']
    if sheet.cell(1, 9).value != '实际模型调用次数':
        raise ValueError('Unexpected original workbook column')
    sheet.cell(1, 9).value = 'Codex CLI启动/续接次数'
    note = ('原始字段 actualModelCalls 等于 CLI 执行尝试数，包含服务恢复续接；'
            '不是 agent 内部模型 API 请求数。CLI 工具调用与原生求解请求分别统计。'
            '原始 usage 事件保留，不在未确认计数范围时相加推算费用。')
    workbook['说明'].append(['调用统计口径澄清', note])
    workbook.save(output)
    check = load_workbook(output, read_only=True, data_only=False)
    checked_answers = answer_hashes(check)
    check.close()
    if checked_answers != original_answers or sha(source) != source_digest:
        raise ValueError('Clarification changed original answer content or source export')
    record = {
        'kind': 'research300-v32-cli-count-clarification', 'formalComparisonScore': False,
        'sourceWorkbookSha256': source_digest, 'clarifiedWorkbookSha256': sha(output),
        'summarySha256': sha(root / 'summary.json'),
        'executionIndexSha256': sha(root / 'execution-index.json'), 'sourceSha256': sha(Path(__file__)),
        'cliInvocations': invocation_count, 'cliToolCalls': summary['cliToolCalls'],
        'allNativeAttempts': summary['allNativeAttempts'], 'individualModelApiRequests': None,
        'dollarCost': None, 'answerHashesUnchanged': len(checked_answers),
        'originalScoresChanged': False, 'originalWorkbookChanged': False,
        'legacyFieldMeaning': note,
    }
    with report.open('x') as handle:
        json.dump(record, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    print(json.dumps(record, ensure_ascii=False))


if __name__ == '__main__':
    main()
