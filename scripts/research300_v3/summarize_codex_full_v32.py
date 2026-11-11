"""Export all 300 cases / 560 outcomes and byte-preserved candidate answers."""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import shutil

from .summarize_candidate import answer_chunks, literal_append


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    with path.open('x') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write('\n')


def summarize(edition, work, diagnostic, output):
    from openpyxl import Workbook, load_workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    edition, work, diagnostic, output = [Path(p).resolve() for p in (edition, work, diagnostic, output)]
    if output.exists():
        raise FileExistsError('A fresh export directory is required')
    manifest, spec, index, grade = map(read, (edition / 'manifest.json', work / 'execution-specification.json',
                                            work / 'index.json', diagnostic))
    if (grade['plannedTurns'] != 560 or grade['cases'] != 300 or grade['formalComparisonScore'] is not False
            or grade['indexSha256'] != sha(work / 'index.json') or grade['manifestSha256'] != sha(edition / 'manifest.json')
            or grade['executionSpecificationSha256'] != sha(work / 'execution-specification.json')):
        raise ValueError('Sealed diagnostic bindings differ')
    expected = {(c['id'], t['id']) for c in manifest['cases'] for t in c['turns']}
    grades = {(r['caseId'], r['turnId']): r for r in grade['rows']}
    collected = {(r['caseId'], r['turnId']): r for r in index['turns']}
    if set(grades) != expected or set(collected) != expected or len(grade['rows']) != len(expected):
        raise ValueError('The complete denominator must be retained')
    output.mkdir(parents=True)
    workbook = Workbook()
    workbook.remove(workbook.active)
    sheets = {}
    for title, header in [
        ('300题索引', ['caseId', '形态', '难度', '引擎', '题名', 'split', '轮次', '通过轮次', '全题通过', '未决轮次']),
        ('560轮题面', ['caseId', 'turnId', '原始签发消息', '公开附件目录', '题目JSON']),
        ('560轮评分', ['caseId', 'turnId', '形态', '难度', '引擎', '评分状态', '本轮原生尝试数', 'CLI工具调用数', '实际模型调用次数', '耗时秒', '失败指标或错误']),
        ('Codex原始作答', ['caseId', 'turnId', '原始文件', 'SHA256', '编码', '片段', '总片段', '完整内容；按片段顺序拼接']),
        ('说明', ['项目', '值']),
    ]:
        sheets[title] = workbook.create_sheet(title)
        sheets[title].append(header)
    for row in [
        ('范围', '300题／560轮完整冻结题库回归；不是独立留出集成绩，也不授予论文比较资格。'),
        ('状态', 'passed / candidate_failure / blocked_configuration / ungradable_evidence / needs_review；五种状态全部保留在固定分母。'),
        ('候选', f'{spec["model"]}; high; {spec["cliVersion"]}'),
        ('SUT', spec['sutCommit']), ('题库SHA256', grade['manifestSha256']),
        ('原始交付', '答案逐字节复制并校验SHA256。Excel按12000字符分片，不截断；字符串不作为公式执行。'),
        ('评分', json.dumps(grade['counts'], ensure_ascii=False)),
        ('人工查看', '先按评分表筛选；原始答案、签发消息可点击。完整证据与独立失败复核另见报告。'),
        ('归因', 'candidate_failure是冻结评分器的判定，不自动证明模型能力差或评价器无缺陷；逐项归因另行复核。'),
    ]:
        literal_append(sheets['说明'], row)
    answer_index, executions, failures = [], [], []
    groups = {dimension: {} for dimension in ('family', 'level', 'engine', 'split', 'analysis')}
    call_count = tool_count = recovery_count = 0
    for c in manifest['cases']:
        rows = [grades[(c['id'], t['id'])] for t in c['turns']]
        statuses = Counter(r['outcome'] for r in rows)
        literal_append(sheets['300题索引'], [c['id'], c['family'], c['level'], c['engine'], c['title'], c['split'],
                                            len(rows), statuses['passed'], statuses['passed'] == len(rows),
                                            sum(v for k, v in statuses.items() if k not in ('passed', 'candidate_failure'))])
        for t in c['turns']:
            cid, tid = c['id'], t['id']
            row, capture = grades[(cid, tid)], collected[(cid, tid)]
            directory = work / 'runs' / cid / tid
            execution = read(directory / 'execution.json') if (directory / 'execution.json').exists() else {}
            call_count += execution.get('actualModelCalls', 0)
            tool_count += execution.get('toolCallsObserved', 0)
            recovery_count += max(0, execution.get('actualModelCalls', 0) - 1)
            executions.append({'caseId': cid, 'turnId': tid, 'captureComplete': capture['captureComplete'],
                               'candidateStatus': capture['candidateStatus'], 'environmentStatus': capture['environmentStatus'],
                               'currentJobIds': capture['currentJobIds'], 'elapsedSeconds': execution.get('elapsedSeconds'),
                               'actualModelCalls': execution.get('actualModelCalls', 0), 'toolCallsObserved': execution.get('toolCallsObserved', 0),
                               'threadId': execution.get('threadId'), 'attempts': execution.get('attempts', [])})
            message = directory / 'issued-packet' / tid / 'user-message.txt'
            message_relative = Path('issued-messages') / cid / (tid + '.txt')
            if message.exists():
                target = output / message_relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(message, target)
                if sha(target) != sha(message):
                    raise ValueError('Message copy differs')
            task = json.dumps(read(edition / t['public'] / 'task.json'), ensure_ascii=False)
            if len(task) > 30000:
                raise ValueError('Task needs explicit Excel chunking')
            literal_append(sheets['560轮题面'], [cid, tid, message_relative.as_posix() if message.exists() else '未签发',
                                               os.path.relpath(edition / t['public'], output), task])
            if message.exists():
                sheets['560轮题面'].cell(sheets['560轮题面'].max_row, 3).hyperlink = message_relative.as_posix()
            failure = row.get('failures') or {'reasonCodes': row.get('reasonCodes', []), 'detail': row.get('detail')}
            failure_text = json.dumps(failure, ensure_ascii=False)
            if len(failure_text) > 30000:
                failure_text = failure_text[:29000] + '\n完整指标见 failures.json'
            literal_append(sheets['560轮评分'], [cid, tid, c['family'], c['level'], c['engine'], row['outcome'],
                                               len(capture['currentJobIds']), execution.get('toolCallsObserved', 0),
                                               execution.get('actualModelCalls', 0), execution.get('elapsedSeconds'), failure_text])
            if row['outcome'] != 'passed':
                failures.append({**row, 'attribution': 'requires-independent-review'})
            source = directory / 'answer.json'
            record = {'caseId': cid, 'turnId': tid, 'present': source.is_file()}
            if source.is_file():
                if source.is_symlink() or not capture.get('answer') or sha(source) != capture['answer']['sha256']:
                    raise ValueError('Original answer seal differs')
                relative = Path('codex-answers') / cid / (tid + '.json')
                target = output / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
                if sha(target) != sha(source):
                    raise ValueError('Original answer copy differs')
                record.update(path=relative.as_posix(), sha256=sha(source), bytes=source.stat().st_size)
                encoding, chunks = answer_chunks(source.read_bytes())
                for number, chunk in enumerate(chunks, 1):
                    literal_append(sheets['Codex原始作答'], [cid, tid, relative.as_posix(), record['sha256'], encoding, number, len(chunks), chunk])
                    sheets['Codex原始作答'].cell(sheets['Codex原始作答'].max_row, 3).hyperlink = relative.as_posix()
            else:
                literal_append(sheets['Codex原始作答'], [cid, tid, '', '', '', 0, 0, '未交付结构化答案；状态与原始CLI记录保留。'])
            answer_index.append(record)
            for dimension, values in groups.items():
                group = values.setdefault(c[dimension], {'turns': 0, 'outcomes': {k: 0 for k in grade['counts']}})
                group['turns'] += 1
                group['outcomes'][row['outcome']] += 1
    for sheet in workbook:
        sheet.freeze_panes = 'A2'
        sheet.auto_filter.ref = sheet.dimensions
        for cell in sheet[1]:
            cell.font = Font(bold=True, color='FFFFFF')
            cell.fill = PatternFill('solid', fgColor='215E68')
        for column in sheet.columns:
            sheet.column_dimensions[column[0].column_letter].width = 24
        for line in sheet.iter_rows(min_row=2):
            for cell in line:
                cell.alignment = Alignment(vertical='top', wrap_text=True)
    workbook.save(output / 'catalogue.xlsx')
    # Check the actual exported workbook reconstructs every answer byte-for-byte.
    check = load_workbook(output / 'catalogue.xlsx', read_only=True, data_only=False)
    assembled = {}
    for line in check['Codex原始作答'].iter_rows(min_row=2, values_only=True):
        if not line[2]:
            continue
        entry = assembled.setdefault((line[0], line[1]), {'encoding': line[4], 'parts': [], 'sha256': line[3]})
        if line[5] != len(entry['parts']) + 1:
            raise ValueError('Workbook answer chunks reordered')
        entry['parts'].append(line[7] or '')
    import base64
    for entry in assembled.values():
        text = ''.join(entry['parts'])
        data = text.encode('utf-8') if entry['encoding'] == 'utf-8' else base64.b64decode(text)
        if hashlib.sha256(data).hexdigest() != entry['sha256']:
            raise ValueError('Workbook answer bytes differ')
    check.close()
    summary = {'kind': 'research300-v32-full-human-review-export', 'formalComparisonScore': False,
               'manifestSha256': grade['manifestSha256'], 'diagnosticSha256': sha(diagnostic),
               'cases': 300, 'plannedTurns': 560, 'outcomes': grade['counts'], 'caseCounts': grade['caseCounts'],
               'groups': groups, 'structuredAnswers': sum(r['present'] for r in answer_index),
               'actualModelCalls': call_count, 'transportRecoveryCalls': recovery_count, 'cliToolCalls': tool_count,
               'allNativeAttempts': sum(len(r['currentJobIds']) for r in executions),
               'workbookAnswerHashesVerified': len(assembled), 'sourceSha256': sha(Path(__file__)), 'localOnly': True}
    write(output / 'answer-integrity.json', {'files': answer_index})
    write(output / 'execution-index.json', {'rows': executions})
    write(output / 'failures.json', {'rows': failures})
    write(output / 'summary.json', summary)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('edition', 'work', 'diagnostic', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    a = parser.parse_args()
    print(json.dumps(summarize(a.edition, a.work, a.diagnostic, a.output), ensure_ascii=False, indent=2))
