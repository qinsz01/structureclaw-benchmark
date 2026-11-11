"""Publish captured full-suite answers and an Excel review without rewriting them."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import shutil


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    with Path(path).open('x') as file:
        file.write(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def answer_chunks(data, limit=12000):
    try:
        text, encoding = data.decode('utf-8'), 'utf-8'
    except UnicodeDecodeError:
        text, encoding = base64.b64encode(data).decode('ascii'), 'base64'
    return encoding, [text[i:i + limit] for i in range(0, len(text), limit)] or ['']


def literal_append(sheet, values):
    """Keep arbitrary submitted JSON chunks as literal strings, including '='."""
    sheet.append(values)
    for cell in sheet[sheet.max_row]:
        if isinstance(cell.value, str):
            cell.data_type = 's'


def summarize(edition, work, grade_path, output):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    edition, work, grade_path, output = map(lambda p: Path(p).resolve(), (edition, work, grade_path, output))
    if output.exists():
        raise FileExistsError('Fresh review directory required; retain earlier reports')
    manifest, binding, execution, grade = map(read, (edition / 'manifest.json', work / 'candidate-binding.json',
                                                   work / 'execution-summary.json', grade_path))
    manifest_hash = sha(edition / 'manifest.json')
    if any(r['manifestSha256'] != manifest_hash for r in (binding, execution, grade)):
        raise ValueError('Review edition binding differs')
    if not execution.get('allTurnsCaptured') or not all(r['completedTurn'] for r in execution['turns']):
        raise ValueError('Full capture has not finished; do not publish a partial run as complete')
    cases = {c['id']: c for c in manifest['cases']}
    pairs = {(cid, t['id']) for cid, c in cases.items() for t in c['turns']}
    grades = {(r['caseId'], r['turnId']): r for r in grade['rows']}
    executions = {(r['caseId'], r['turnId']): r for r in execution['turns']}
    if set(grades) != pairs or set(executions) != pairs or len(grades) != len(grade['rows']) or grade['developmentOnly']:
        raise ValueError('Full capture/grade turn inventory differs')
    output.mkdir(parents=True)
    workbook = Workbook()
    workbook.remove(workbook.active)
    questions = workbook.create_sheet('300题索引')
    questions.append(['caseId', '形态', '难度', '引擎', '题目', '来源类型', '来源组', 'split', '轮次', '通过轮次', '整题通过'])
    turns = workbook.create_sheet('560轮题面')
    turns.append(['caseId', 'turnId', '题目JSON', '公开附件', '公开题面路径'])
    scores = workbook.create_sheet('560轮评分')
    scores.append(['caseId', 'turnId', '形态', '难度', '引擎', '通过', '状态', '本轮工具作业', '耗时含传输重连秒', '失败指标或错误'])
    answers = workbook.create_sheet('Codex原始作答')
    answers.append(['caseId', 'turnId', '原始文件', 'SHA256', '编码', '片段', '总片段', '原始内容；同轮按片段顺序拼接'])
    info = workbook.create_sheet('说明')
    info.append(['项目', '值'])
    for row in [('范围', f'{len(cases)}题/{len(pairs)}轮；完整候选验证，非StructureClaw正式对比'),
                ('候选', f'{binding["model"]}; high; {binding["cliVersion"]}'),
                ('题库SHA256', manifest_hash), ('评分', f'{grade["passed"]}/{grade["turns"]}轮通过'),
                ('交付保真', '作答文件原样复制并逐文件保留SHA256。Excel按12000字符分片，不截断；字符串不作为公式执行。'),
                ('二进制交付', '若原始文件不是UTF-8，Excel片段为base64；原始文件字节仍保持不变。'),
                ('耗时', '包含原始调用与中断恢复的等待，不用于正式候选速度比较。'),
                ('失败解释', '评分未通过原因按原始评分记录保存；能力、题面、评价器或运行环境归因需另外复核。')]:
        literal_append(info, row)
    answer_index, execution_index, failures = [], [], []
    groups = {key: {} for key in ('family', 'level', 'engine', 'split')}
    for cid, case in cases.items():
        passed = sum(grades[(cid, t['id'])]['passed'] for t in case['turns'])
        literal_append(questions, [cid, case['family'], case['level'], case['engine'], case['title'], case['origin'],
                                   case.get('sourceId', ''), case['split'], len(case['turns']), passed, passed == len(case['turns'])])
        for turn in case['turns']:
            tid = turn['id']
            row, run = grades[(cid, tid)], executions[(cid, tid)]
            source = work / 'runs' / cid / tid / 'answer.json'
            index = {'caseId': cid, 'turnId': tid, 'present': source.exists()}
            execution_index.append({'caseId': cid, 'turnId': tid, 'elapsedSeconds': run['elapsedSeconds'],
                                    'currentNativeJobs': len(run['currentJobIds']), 'completedTurn': run['completedTurn'],
                                    'threadId': run['threadId'], 'priorAttempts': run.get('priorAttempts', [])})
            task = read(edition / turn['public'] / 'task.json')
            text = json.dumps(task, ensure_ascii=False)
            if len(text) > 30000:
                raise ValueError('Task text exceeds Excel cell limit; explicit task chunking required')
            literal_append(turns, [cid, tid, text, '\n'.join(task.get('attachments', [])), turn['public']])
            failure = row.get('failures') or row.get('error', '')
            failure_text = json.dumps(failure, ensure_ascii=False)
            visible_failure = failure_text if len(failure_text) <= 30000 else failure_text[:29500] + '\n…（完整指标见同目录failures.json）'
            literal_append(scores, [cid, tid, case['family'], case['level'], case['engine'], row['passed'], row.get('status', 'scored'),
                                   len(run['currentJobIds']), run['elapsedSeconds'], visible_failure])
            if not row['passed']:
                failures.append({**row, 'family': case['family'], 'level': case['level'], 'engine': case['engine'],
                                 'attribution': 'unreviewed', 'note': 'Scoring outcome retained; no automatic capability attribution'})
            if source.exists():
                if source.is_symlink():
                    raise ValueError('Candidate capture must be a regular answer file')
                relative = Path('codex-answers') / cid / (tid + '.json')
                target = output / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
                if source.read_bytes() != target.read_bytes():
                    raise ValueError('Candidate answer copy differs')
                index.update(path=relative.as_posix(), sha256=sha(source), bytes=source.stat().st_size)
                encoding, chunks = answer_chunks(source.read_bytes())
                for number, chunk in enumerate(chunks, 1):
                    literal_append(answers, [cid, tid, relative.as_posix(), index['sha256'], encoding, number, len(chunks), chunk])
                    answers.cell(answers.max_row, 3).hyperlink = relative.as_posix()
            else:
                literal_append(answers, [cid, tid, '', '', '', 0, 0, 'No structured answer file was delivered; see raw CLI final message in evidence.'])
            answer_index.append(index)
            for dimension, values in groups.items():
                key = case[dimension]
                entry = values.setdefault(key, {'turns': 0, 'passed': 0})
                entry['turns'] += 1
                entry['passed'] += bool(row['passed'])
    for sheet in workbook:
        sheet.freeze_panes = 'A2'
        sheet.auto_filter.ref = sheet.dimensions
        for cell in sheet[1]:
            cell.font = Font(bold=True, color='FFFFFF')
            cell.fill = PatternFill('solid', fgColor='215E68')
        for column in sheet.columns:
            sheet.column_dimensions[column[0].column_letter].width = 24
        for row in sheet.iter_rows(min_row=2):
            for cell in row:
                cell.alignment = Alignment(vertical='top', wrap_text=True)
    workbook.save(output / 'catalogue.xlsx')
    write(output / 'answer-integrity.json', {'manifestSha256': manifest_hash, 'files': answer_index})
    write(output / 'execution-index.json', {'manifestSha256': manifest_hash, 'rows': execution_index})
    write(output / 'failures.json', {'manifestSha256': manifest_hash, 'rows': failures})
    summary = {'manifestSha256': manifest_hash, 'model': binding['model'], 'reasoningEffort': 'high',
               'cases': len(cases), 'turns': len(pairs), 'completedTurns': len(executions),
               'structuredAnswerFiles': sum(r['present'] for r in answer_index), 'passedTurns': grade['passed'],
               'failedTurns': grade['failed'], 'fullyPassedCases': grade['completeCases'], 'groups': groups,
               'formalComparisonScore': False, 'graderFeedbackDuringRun': False, 'localOnly': True}
    write(output / 'summary.json', summary)
    shutil.copyfile(work / 'candidate-binding.json', output / 'candidate-binding.json')
    shutil.copyfile(work / 'execution-summary.json', output / 'execution-summary.json')
    # Publish this entry last so the viewer cannot consume a partially built review.
    ready = output / '.codex-full.json.tmp'
    shutil.copyfile(grade_path, ready)
    ready.replace(output / 'codex-full.json')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('edition', 'work', 'grade', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(summarize(args.edition, args.work, args.grade, args.output), ensure_ascii=False, indent=2))
