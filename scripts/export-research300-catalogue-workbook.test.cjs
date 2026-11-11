'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const script = path.join(__dirname, 'export-research300-catalogue-workbook.cjs');
const writer = () => require(script).writeCatalogueWorkbook;
const SECRET = 'PRIVATE_ANSWER_SENTINEL_731_924';

const choice = (key, zh, en, description = '', family) => ({ key, zh, en, description, ...(family ? { family } : {}) });
const bucket = (key, zh, en, cases, turns, states, attachmentFiles, attachmentUses, markdownFiles, pngFiles, dxfFiles, family) =>
  ({ key, zh, en, cases, turns, states, attachmentFiles, attachmentUses, markdownFiles, pngFiles, dxfFiles, ...(family ? { family } : {}) });

function catalogue() {
  return {
    schemaVersion: 1,
    edition: 'current',
    totals: { cases: 3, turns: 6, states: 5, attachmentFiles: 4, attachmentUses: 5, markdownFiles: 2, pngFiles: 1, dxfFiles: 1 },
    definitions: {
      family: [choice('standard', '标准分析', 'Standard'), choice('interaction', '交互分析', 'Interaction'), choice('multimodal', '多模态分析', 'Multimodal')],
      category: [choice('beam-skill', '梁分析', 'Beam analysis', '从 <表格> 与 "文字" 中提取条件 & 校核。', 'standard'), choice('revise-skill', '模型修订', 'Model revision', '', 'interaction'), choice('drawing-skill', '图纸重建', 'Drawing reconstruction', '', 'multimodal')],
      structure: [choice('梁', '梁', 'Beam'), choice('框架', '框架', 'Frame'), choice('桁架', '桁架', 'Truss')],
      dimension: [choice('2D', '二维', '2D'), choice('3D', '三维', '3D')],
      difficulty: [choice('L1', '基础', 'Basic'), choice('L2', '进阶', 'Intermediate'), choice('L3', '综合', 'Advanced')],
      modality: [choice('text', '文字', 'Text'), choice('image', '图像', 'Image'), choice('dxf', 'CAD 图纸', 'DXF')],
      engine: [choice('OpenSees', 'OpenSees', 'OpenSees'), choice('Abaqus', 'Abaqus', 'Abaqus')],
      language: [choice('zh', '中文', 'Chinese'), choice('en', '英文', 'English')],
    },
    breakdowns: {
      family: [bucket('standard', '标准分析', 'Standard', 1, 1, 1, 1, 1, 1, 0, 0), bucket('interaction', '交互分析', 'Interaction', 1, 3, 2, 1, 2, 1, 0, 0), bucket('multimodal', '多模态分析', 'Multimodal', 1, 2, 2, 2, 2, 0, 1, 1)],
      category: [bucket('beam-skill', '梁分析', 'Beam analysis', 1, 1, 1, 1, 1, 1, 0, 0, 'standard'), bucket('revise-skill', '模型修订', 'Model revision', 1, 3, 2, 1, 2, 1, 0, 0, 'interaction'), bucket('drawing-skill', '图纸重建', 'Drawing reconstruction', 1, 2, 2, 2, 2, 0, 1, 1, 'multimodal')],
      structure: [bucket('梁', '梁', 'Beam', 1, 1, 1, 1, 1, 1, 0, 0), bucket('框架', '框架', 'Frame', 1, 3, 2, 1, 2, 1, 0, 0), bucket('桁架', '桁架', 'Truss', 1, 2, 2, 2, 2, 0, 1, 1)],
      dimension: [bucket('2D', '二维', '2D', 2, 4, 3, 2, 3, 2, 0, 0), bucket('3D', '三维', '3D', 1, 2, 2, 2, 2, 0, 1, 1)],
      difficulty: [bucket('L1', '基础', 'Basic', 1, 1, 1, 1, 1, 1, 0, 0), bucket('L2', '进阶', 'Intermediate', 1, 3, 2, 1, 2, 1, 0, 0), bucket('L3', '综合', 'Advanced', 1, 2, 2, 2, 2, 0, 1, 1)],
      modality: [bucket('text', '文字', 'Text', 2, 4, 3, 2, 3, 2, 0, 0), bucket('image', '图像', 'Image', 0, 0, 0, 0, 0, 0, 0, 0), bucket('dxf', 'CAD 图纸', 'DXF', 1, 2, 2, 2, 2, 0, 1, 1)],
      engine: [bucket('OpenSees', 'OpenSees', 'OpenSees', 2, 3, 3, 3, 3, 1, 1, 1), bucket('Abaqus', 'Abaqus', 'Abaqus', 1, 3, 2, 1, 2, 1, 0, 0)],
      language: [bucket('zh', '中文', 'Chinese', 2, 3, 3, 3, 3, 1, 1, 1), bucket('en', '英文', 'English', 1, 3, 2, 1, 2, 1, 0, 0)],
    },
    cases: [
      { id: 'STD-900', title: '=HYPERLINK("https://invalid", "<梁> & 柱 _x0041_")', family: 'standard', category: 'beam-skill', focus: '表格与边界条件', structure: '梁', dimension: '2D', difficulty: 'L1', difficultyReason: '单步静力分析', engine: 'OpenSees', language: 'zh', modality: 'text', turns: 1, states: 1, attachmentFiles: 1, attachmentUses: 1, markdownFiles: 1, pngFiles: 0, dxfFiles: 0, authored: true, referenceReady: true, nativeVerified: true, inputReviewStatus: 'pending', accepted: false, modelTrialStatus: 'not-run', sourceHash: 'a'.repeat(64), expectedAnswer: SECRET },
      { id: 'INT-901', title: '+SUM(1,2) — 框架\n修订（\'引号\'）', family: 'interaction', category: 'revise-skill', focus: '按用户反馈修改模型', structure: '框架', dimension: '2D', difficulty: 'L2', difficultyReason: '三轮、两个模型状态', engine: 'Abaqus', language: 'en', modality: 'text', turns: 3, states: 2, attachmentFiles: 1, attachmentUses: 2, markdownFiles: 1, pngFiles: 0, dxfFiles: 0, authored: true, referenceReady: true, nativeVerified: false, inputReviewStatus: 'partial', accepted: false, modelTrialStatus: 'run' },
      { id: 'MM-902', title: '@标题：桁架 🏗️ \u000b', family: 'multimodal', category: 'drawing-skill', focus: '解读 CAD 及图像', structure: '桁架', dimension: '3D', difficulty: 'L3', difficultyReason: '含多个视图', engine: 'OpenSees', language: 'zh', modality: 'dxf', turns: 2, states: 2, attachmentFiles: 2, attachmentUses: 2, markdownFiles: 0, pngFiles: 1, dxfFiles: 1, authored: true, referenceReady: false, nativeVerified: false, inputReviewStatus: 'passed', accepted: true, modelTrialStatus: 'not-run' },
    ],
    provenance: SECRET,
  };
}

function directory(t) {
  const value = fs.mkdtempSync(path.join(os.tmpdir(), 'research300-workbook-'));
  t.after(() => fs.rmSync(value, { recursive: true, force: true }));
  return value;
}

// This reader uses only Python's ZIP/XML libraries and knows no writer internals.
function readWorkbook(file) {
  const result = spawnSync('python3', ['-I', '-c', String.raw`
import json, posixpath, re, sys, zipfile
from xml.etree import ElementTree as ET
N = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
def text_value(value):
    return re.sub(r'_x([0-9a-fA-F]{4})_', lambda m: chr(int(m.group(1), 16)), value)
with zipfile.ZipFile(sys.argv[1]) as z:
    roots = {name: ET.fromstring(z.read(name)) for name in z.namelist() if name.endswith(('.xml', '.rels'))}
    for item in roots['[Content_Types].xml']:
        if 'PartName' in item.attrib: assert item.attrib['PartName'].lstrip('/') in roots, 'missing package part'
    relationships = {r.attrib['Id']: r.attrib['Target'] for r in roots['xl/_rels/workbook.xml.rels']}
    styles = roots['xl/styles.xml'].find('s:cellXfs', N)
    sheets = {}
    for item in roots['xl/workbook.xml'].find('s:sheets', N):
        target = posixpath.normpath(posixpath.join('xl', relationships[item.attrib['{' + R + '}id']]))
        root = roots[target]
        rows = []
        for row in root.findall('s:sheetData/s:row', N):
            cells = {}
            for c in row.findall('s:c', N):
                typ = c.attrib.get('t', 'n')
                if typ == 'inlineStr':
                    value = text_value(''.join(c.find('s:is', N).itertext()))
                else:
                    value = c.findtext('s:v', default='', namespaces=N)
                    if typ == 'n': value = int(value)
                assert int(c.attrib.get('s', 0)) < len(styles), 'unknown cell style'
                cells[c.attrib['r']] = {'value': value, 'type': typ}
            rows.append(cells)
        pane = root.find('s:sheetViews/s:sheetView/s:pane', N)
        af = root.find('s:autoFilter', N)
        for merge in root.findall('s:mergeCells/s:mergeCell', N):
            start, end = merge.attrib['ref'].split(':')
            def position(value):
                match = re.fullmatch(r'([A-Z]+)([1-9][0-9]*)', value)
                assert match, 'invalid cell reference'
                number = 0
                for letter in match.group(1): number = 26 * number + ord(letter) - 64
                return number, int(match.group(2))
            left, top = position(start)
            right, bottom = position(end)
            max_column, max_row = position(root.find('s:dimension', N).attrib['ref'].split(':')[-1])
            assert left <= right <= max_column and top <= bottom <= max_row, 'invalid merged range'
        sheets[item.attrib['name']] = {'rows': rows, 'pane': None if pane is None else pane.attrib, 'filter': None if af is None else af.attrib['ref'], 'widths': len(root.findall('s:cols/s:col', N)), 'formulas': len(root.findall('.//s:f', N))}
    print(json.dumps({'sheets': sheets, 'files': z.namelist(), 'zipTimes': [i.date_time for i in z.infolist()], 'xmlText': '\n'.join(z.read(n).decode('utf-8') for n in roots)}, ensure_ascii=True))
`, file], { encoding: 'utf8', maxBuffer: 8 * 1024 * 1024 });
  assert.equal(result.status, 0, result.stderr);
  return JSON.parse(result.stdout);
}

function table(sheet) {
  const headers = Object.values(sheet.rows[0]).map(cell => cell.value);
  return sheet.rows.slice(1).map(row => Object.fromEntries(Object.values(row).map((cell, i) => [headers[i], cell.value])));
}

test('workbook preserves supplied case metadata and exact shared counts without private source fields', t => {
  const root = directory(t);
  const data = catalogue();
  const target = path.join(root, 'new', 'nested', '当前版.xlsx');
  assert.equal(writer()(data, target), target);
  const book = readWorkbook(target);
  assert.deepEqual(Object.keys(book.sheets), ['概览', '题目明细', '分类统计', '分类说明']);
  const details = table(book.sheets['题目明细']);
  assert.deepEqual(details.map(row => row['题目 ID']), ['STD-900', 'INT-901', 'MM-902']);
  assert.deepEqual(details.map(row => row['题目']), data.cases.map(row => row.title));
  assert.deepEqual(details.map(row => row['能力子类']), ['梁分析', '模型修订', '图纸重建']);
  assert.deepEqual(details.map(row => row['预设难度']), ['L1 · 基础', 'L2 · 进阶', 'L3 · 综合']);
  assert.deepEqual(details.map(row => [row['原生核验'], row['输入复核'], row['已验收'], row['模型试跑']]), [
    ['是', 'pending', '否', 'not-run'], ['否', 'partial', '否', 'run'], ['否', 'passed', '是', 'not-run'],
  ]);
  assert.deepEqual(details.map(row => [row['交互轮次'], row['模型状态数'], row['输入附件文件数'], row['附件引用次数']]), [[1, 1, 1, 1], [3, 2, 1, 2], [2, 2, 2, 2]]);
  const stats = table(book.sheets['分类统计']);
  assert.deepEqual(stats.find(row => row['分类维度'] === '输入模态' && row['分类键'] === 'image'), {
    '分类维度': '输入模态', '分类键': 'image', '分类名称': '图像', English: 'Image', '所属任务大类': '',
    '题目数': 0, '交互轮次': 0, '模型状态数': 0, '输入附件文件数': 0, '附件引用次数': 0, 'Markdown 文件数': 0, 'PNG 文件数': 0, 'DXF 文件数': 0,
  });
  assert.deepEqual(stats.find(row => row['分类维度'] === '求解器' && row['分类键'] === 'OpenSees'), {
    '分类维度': '求解器', '分类键': 'OpenSees', '分类名称': 'OpenSees', English: 'OpenSees', '所属任务大类': '',
    '题目数': 2, '交互轮次': 3, '模型状态数': 3, '输入附件文件数': 3, '附件引用次数': 3, 'Markdown 文件数': 1, 'PNG 文件数': 1, 'DXF 文件数': 1,
  });
  const overviewCells = book.sheets['概览'].rows.flatMap(row => Object.values(row));
  for (const [label, value] of [['题目数', 3], ['交互轮次', 6], ['模型状态数', 5], ['输入附件文件数', 4], ['附件引用次数', 5]]) {
    const row = book.sheets['概览'].rows.find(cells => Object.values(cells).some(cell => cell.value === label));
    assert.equal(Object.values(row)[1].value, value);
    assert.equal(Object.values(row)[1].type, 'n');
  }
  assert.ok(overviewCells.some(cell => cell.value === '预设难度，未按模型实测校准'));
  assert.ok(table(book.sheets['分类说明']).some(row => row['定义 / 说明'] === '从 <表格> 与 "文字" 中提取条件 & 校核。'));
  assert.doesNotMatch(book.xmlText, /PRIVATE_ANSWER_SENTINEL|a{64}|expectedAnswer|sourceHash|provenance/);
});

test('difficulty labels that already include their level keep exactly one level prefix', t => {
  const root = directory(t);
  const data = catalogue();
  const labels = ['L1 · 基本映射', 'L2 · 单项非直接映射', 'L3 · 多约束联合处理'];
  for (const [index, label] of labels.entries()) {
    data.definitions.difficulty[index].zh = label;
    data.breakdowns.difficulty[index].zh = label;
  }
  const target = path.join(root, 'prefixed-difficulty.xlsx');
  writer()(data, target);
  assert.deepEqual(table(readWorkbook(target).sheets['题目明细']).map(row => row['预设难度']), labels);
});

test('identical supplied data creates byte-identical styled workbooks with safe text cells', t => {
  const root = directory(t);
  const a = path.join(root, 'a.xlsx');
  const b = path.join(root, 'b.xlsx');
  writer()(catalogue(), a);
  writer()(catalogue(), b);
  assert.deepEqual(fs.readFileSync(a), fs.readFileSync(b));
  const book = readWorkbook(a);
  assert.ok(book.zipTimes.every(value => value.join(',') === '1980,1,1,0,0,0'));
  for (const [name, sheet] of Object.entries(book.sheets)) {
    assert.equal(sheet.formulas, 0, name);
    assert.equal(sheet.pane.state, 'frozen', name);
    assert.ok(sheet.widths >= 3, name);
  }
  for (const name of ['题目明细', '分类统计', '分类说明']) {
    assert.match(book.sheets[name].filter, /^A1:[A-Z]+\d+$/);
    assert.equal(book.sheets[name].pane.ySplit, '1');
  }
  assert.equal(book.sheets['题目明细'].rows[1].B2.type, 'inlineStr');
  assert.equal(book.sheets['题目明细'].rows[2].B3.type, 'inlineStr');
  assert.equal(book.sheets['题目明细'].rows[3].B4.type, 'inlineStr');
  assert.ok(book.files.includes('[Content_Types].xml'));
  assert.ok(book.files.includes('_rels/.rels'));
  assert.doesNotMatch(book.xmlText, /TargetMode="External"|<hyperlink/);
});

test('invalid catalogue data fails clearly and preserves the previous workbook', t => {
  const root = directory(t);
  const target = path.join(root, 'keep.xlsx');
  writer()(catalogue(), target);
  const previous = fs.readFileSync(target);
  for (const [change, expected] of [
    [data => { data.totals.cases = 4; }, /totals.cases/i],
    [data => { data.cases[0].turns = '1'; }, /cases\[0\].turns/i],
    [data => { data.breakdowns.family[0].cases = -1; }, /breakdowns.family\[0\].cases/i],
    [data => { data.cases[0].category = 'missing'; }, /category/i],
    [data => { data.cases[0].authored = 'true'; }, /authored/i],
    [data => { data.cases[0].inputReviewStatus = 'accepted'; }, /inputReviewStatus/i],
    [data => { data.cases[0].title = 'x'.repeat(32768); }, /title|32767/i],
    [data => { data.edition = 'frozen'; }, /edition/i],
  ]) {
    const data = catalogue();
    change(data);
    assert.throws(() => writer()(data, target), expected);
    assert.deepEqual(fs.readFileSync(target), previous);
  }
  assert.deepEqual(fs.readdirSync(root), ['keep.xlsx']);
});

test('CLI reads only the supplied JSON and rejects unsafe destinations without replacing files', t => {
  const root = directory(t);
  const input = path.join(root, 'input.json');
  const target = path.join(root, 'catalogue.xlsx');
  fs.writeFileSync(input, JSON.stringify(catalogue()));
  const result = spawnSync(process.execPath, [script, input, target], { encoding: 'utf8' });
  assert.equal(result.status, 0, result.stderr);
  assert.deepEqual(table(readWorkbook(target).sheets['题目明细']).map(row => row['题目 ID']), ['STD-900', 'INT-901', 'MM-902']);
  const previous = fs.readFileSync(target);
  fs.writeFileSync(input, '{invalid');
  const invalid = spawnSync(process.execPath, [script, input, target], { encoding: 'utf8' });
  assert.notEqual(invalid.status, 0);
  assert.match(invalid.stderr, /JSON/i);
  assert.deepEqual(fs.readFileSync(target), previous);
  fs.writeFileSync(input, JSON.stringify(catalogue()));
  const unavailablePython = spawnSync(process.execPath, [script, input, target], { encoding: 'utf8', env: { ...process.env, PATH: '' } });
  assert.notEqual(unavailablePython.status, 0);
  assert.match(unavailablePython.stderr, /Cannot generate catalogue workbook.*python3/i);
  assert.deepEqual(fs.readFileSync(target), previous);
  assert.deepEqual(fs.readdirSync(root).sort(), ['catalogue.xlsx', 'input.json']);
  const link = path.join(root, 'link.xlsx');
  fs.symlinkSync(target, link);
  assert.throws(() => writer()(catalogue(), link), /symlink/i);
  const parentLink = path.join(root, 'linked-parent');
  fs.symlinkSync(root, parentLink);
  assert.throws(() => writer()(catalogue(), path.join(parentLink, 'other.xlsx')), /symlink/i);
  assert.deepEqual(fs.readFileSync(target), previous);
});
