"""Static case-by-case source review. Never executes SUTs, models or tests.

Only JSON/CSV/PNG/text inputs, retained authoring records and Git source blobs
are read. Statements describe code reachability and prerequisites, not measured
candidate performance or new solver qualification.
"""
from pathlib import Path
from collections import Counter, defaultdict
import csv
import hashlib
import json
import math
import argparse
import os
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE_ROOT = Path(os.environ.get('SCLAW_BENCH_ARCHIVE', ROOT)).expanduser()
EDITION = Path('/home/openclaw/.cache/structureclaw-bench/research300-v3-codex-full-r1-20261028/edition')
OUT = ROOT / '.bench-work/research300-v3-static-scope-20261029'
PRIMARY = '00ecd812a315a75b7714d5fc030ec3652bfaf869'
LOCAL = '0a17bfdcd1a6cfa827a0aa15c05856fa3bd0e2d1'
SNAPSHOTS = Path('/home/openclaw/.cache/structureclaw-bench/sclaw-static-scope-20261029')
REVIEW = ROOT / 'docs/implementation/reviews/research300-v3-sclaw-static-scope-20261029'
GIT_SOURCE = ROOT / '.worktrees/structureclaw-pkpm-shear-fix-20261027'

# Manually inspected source paths. Anchors bind the review to exact source lines.
EVIDENCE = [
    ('model', 'backend/src/agent-runtime/explicit-model.ts', 'export function buildExplicitDraftModel', '显式二维/三维节点、构件、材料、截面和工况模型入口'),
    ('files', 'backend/src/agent-langgraph/file-tools.ts', 'export async function analyzeUploadedFile', '完整读取CSV/JSON/文本；模型导入只接受真实上传附件'),
    ('vision', 'backend/src/agent-langgraph/attachment-vision.ts', 'export async function summarizeImageAttachment', 'PNG等图纸依赖已配置视觉模型，缺失时明确拒绝'),
    ('edit', 'backend/src/agent-langgraph/model-tools.ts', 'export function createEditModelTool', '按版本批量原子编辑对象与荷载，修改后使旧结果失效'),
    ('undo', 'backend/src/agent-langgraph/model-tools.ts', 'export function createUndoModelTool', '事务与历史；选择性撤销，保留无关后续修改'),
    ('analysis', 'backend/src/agent-langgraph/tools/run-analysis.ts', "name: 'run_analysis'", '指定引擎，批量工况/组合，显式动力参数'),
    ('line-model', 'backend/src/agent-skills/analysis/runtime/opensees_shared/model.py', 'def build(', '二维XZ/三维线弹性梁柱、轴力杆；非零偏心及未支持控制会拒绝'),
    ('loads', 'backend/src/agent-skills/analysis/runtime/opensees_shared/mesh.py', "if kind == 'displacement':", '节点力、分布荷载、支座给定位移及真实端点/区间'),
    ('release', 'backend/src/agent-skills/analysis/runtime/opensees_shared/releases.py', 'def bending_releases', '原生弹性梁柱弯曲端释放；当前题仅需要局部ry'),
    ('mass', 'backend/src/agent-skills/analysis/runtime/opensees_shared/mass.py', 'def resolve_mass_options', '显式节点质量与质量方向，不隐式叠加其他质量来源'),
    ('modal', 'backend/src/agent-skills/analysis/runtime/opensees_shared/modal.py', 'def extract_modal', '周期、频率、有效质量、完整节点振型'),
    ('transient', 'backend/src/agent-skills/analysis/opensees-dynamic/opensees_dynamic_analysis.py', 'def time_history_analysis', '线弹性一致步长时程、g单位、Rayleigh阻尼及所选节点/端部记录'),
    ('results', 'backend/src/engineering/result-selection.ts', 'export const resultSelectionSchema', '有符号节点量、物理构件截面、振型与时程；可读取完整结果集合'),
    ('query', 'backend/src/agent-langgraph/model-tools.ts', 'export function createQueryResultsTool', '按工况/组合/历史run取数；内部网格节点须映射到物理构件位置'),
    ('arithmetic', 'backend/src/agent-langgraph/calc-tool.ts', 'const MAX_EXPRESSION_LENGTH', '标量计算；每个表达式至多500字符，不是原生设计优化器'),
    ('shell', 'backend/src/agent-langgraph/shell-tool.ts', 'export function createShellTool', '已有受限编程入口；需要allowShell且命令在白名单'),
    ('defaults', 'backend/src/config/index.ts', 'const AGENT_DEFAULTS', '默认关闭shell；不能把Codex的外部编程环境默认为sclaw默认能力'),
    ('budget', 'backend/src/runtime/limits.ts', 'export const DEFAULT_MAX_TOOL_CALLS_PER_TURN', '默认和服务端上限均为每轮200个工具调用'),
    ('section-rules', 'backend/src/engineering/section-user-evidence.ts', 'const rule = isRecord(extra.rules)', '比例规则须绑定有证据的源截面；statement须来自真实用户文本且包含factor'),
    ('section-geometry', 'backend/src/skill-shared/python/structure_protocol/section_properties.py', 'def geometry_properties', '从给定矩形尺寸派生A/Iy/Iz/J；无需增加新求解功能'),
    ('boundary', 'backend/src/engineering/model-boundary.ts', 'export async function normalizeEngineeringModel', '建模、导入、修改共用来源证据与物理模型边界'),
    ('pkpm', 'backend/src/agent-skills/analysis/pkpm-static/runtime.py', 'def run_analysis', '原生PKPM静力入口；依赖可用的Windows安装、SDK和许可'),
    ('pkpm-grade', 'backend/src/agent-skills/analysis/pkpm-static/pkpm_converter.py', 'def _resolve_steel_grade', '发布分支仍要求可识别名义牌号，描述性弹性材料名称存在实现阻塞'),
    ('pkpm-version', 'backend/src/agent-skills/analysis/pkpm-static/native_materials.py', 'path = Path(api.__file__).parent', '发布分支材料库同目录与单一2025指纹假设不覆盖既有2027安装'),
    ('pkpm-section', 'backend/src/agent-skills/analysis/runtime/native_model_contract.py', 'def pkpm_numeric_section_properties', '发布分支识别custom数值截面；general字面别名仅在未上传修复中增加'),
    ('yjk', 'backend/src/agent-skills/analysis/yjk-static/model_contract.py', 'def validate_building_model', '真实三维楼层杆系、毫米坐标与原生支承/拓扑映射边界'),
    ('providers', 'backend/src/providers/catalog.yaml', '- id: opensees-static', '公开分析范围：线弹性杆系；本题集不要求壳、实体、塑性或P-Delta'),
]

ISSUES = [
    ('PKPM-2027', '发布分支与已记录的PKPM 2027安装不兼容', 'engine-environment',
     '发布分支材料库采用与APIPyInterface同目录及2025单一指纹假设，转换器还假设工程已有首个标准层。已记录的246机器是2027R1.0.1。',
     '使用与发布代码匹配的已校准安装，或明确选择包含既有2027修复的本地开发版本并冻结；不降低题目要求。', ['pkpm-version', 'pkpm']),
    ('PKPM-DESCRIPTIVE-GRADE', '描述性弹性材料名称仍被强制当作标准牌号', 'published-implementation',
     '6题已给定E/nu/rho，但名称为Elastic steel或Steel M1。发布分支仍无条件调用标准牌号枚举；本地未上传修复增加了纯弹性分析路径。',
     '采用包含既有修复的明确系统版本；不捏造Q235等题面未给出的设计牌号。', ['pkpm-grade']),
    ('PKPM-GENERAL-ALIAS', 'general数值截面的字面映射条件', 'input-canonicalization',
     '2题使用general和完整A/Iy/Iz/J。发布分支数值编译器只直接识别custom；相同机械属性可规范化为custom，但不能改变属性或伪造几何。本地分支已加入general别名。',
     '记录合法的general→custom规范化或采用已有别名修复；该项不等于缺少数值截面求解能力。', ['pkpm-section']),
    ('PROJECT-RULE-EVIDENCE', '设计目录比例规则必须进入可核验输入', 'input-delivery',
     '90题要求由名义截面和宽/高系数推导候选截面。系统支持extra.rules，但要求有证据的源截面，且statement属于真实用户文本并含factor。只把新数值标为user或导入助手生成JSON不是合规路径。',
     '在正式输入约定中保留原始设计目录/规则为真实输入，绑定名义源截面和规则，按几何派生属性；此交付约定尚未冻结。', ['section-rules', 'section-geometry', 'boundary']),
    ('PROJECT-COMPUTATION-POLICY', '有限设计搜索的工具配置与成本须明确', 'run-policy',
     '90题每轮27种离散设计，没有要求逐一提交全部原生求解。已有模型编辑、分析、计算与受限shell；默认shell关闭，每轮工具默认和上限均为200，标量表达式最多500字符。未证明默认配置下所有完整搜索均在预算内。',
     '明确是否使用已有编程辅助及统一预算，并把脚本中的求解调用计入资源；不能用Codex外部编程条件替代默认sclaw条件。', ['edit', 'analysis', 'arithmetic', 'shell', 'defaults', 'budget']),
    ('VISION-CONFIG', '图纸题依赖视觉模型和原始图片入口', 'configuration',
     '100道MM题需要读取PNG。框架提供真实图像分析，未配置视觉模型会明确拒绝。本轮只读取图像文件及已有图面复核记录，不调用视觉模型。',
     '正式运行前冻结视觉模型和附件交付设置；静态支持不代表模型已经正确读图。', ['files', 'vision']),
    ('SCLAW-V3-EVIDENCE-ADAPTER', '原生Agent运行与v3交付/作业绑定尚未冻结', 'benchmark-integration',
     'v3评分入口读取broker封存的jobId、state/model回执及answer.json。sclaw默认工具返回runId、查询量与运行归档；需要保留真实原生证据的采集/转换约定，不能把ID换名就当成完整执行证明。',
     '完成基于原始归档/worker采集的v3接入设计并冻结，保持实际输入、引擎、哈希和工况绑定；本轮不运行接入测试。', ['analysis', 'query', 'bench-job-binding', 'bench-sclaw-import']),
    ('SCLAW-METADATA-COMPARISON', '合法截面来源元数据的比较存在静态接入风险', 'evaluator-integration',
     'sclaw模型边界可保留extra.provenance/evidence/rules/derived_properties。平面/纯轴力比较另有投影视图；三维梁柱比较路径只消去空extra，合法非空来源记录仍可能进入物理字段比较。按实际模型维度及构件类型逐题标记风险，未提交Sclaw运行，不能报告已复现误判。',
     '在接入层审查可证明非物理的来源字段，完整保留受保护原件；不得整体删除未知extra或改变刚度/荷载。本轮仅记录风险，不修改冻结评分器。', ['boundary', 'section-rules', 'bench-empty-extra', 'bench-section-fields']),
]

def read(path):
    return json.loads(path.read_text())

def models(value, path='private'):
    if isinstance(value, dict):
        if value.get('kind') == 'project' and isinstance(value.get('truths'), list):
            # Read every retained design appendix, not just its unloaded base
            # geometry. These dictionary views perform no load calculation,
            # model construction in the SUT, analysis, or reference generation.
            for role in ['primary', 'upper', 'combined']:
                template = value.get(role + 'Template')
                if isinstance(template, dict):
                    yield from models(template, path + '.' + role + 'Template')
            roles = ['combined'] if value.get('integration') == 'rigid' else ['upper', 'primary']
            for index, truth in enumerate(value['truths']):
                for role in roles:
                    template = value[role + 'Template']
                    sections, cases = truth[role + 'Sections'], truth[role + 'LoadCases']
                    view = {**template, 'sections': sections, 'load_cases': cases}
                    yield path + '.truths[' + str(index) + '].' + role, view
            return
        if all(isinstance(value.get(k), list) for k in ('nodes', 'elements', 'materials', 'sections')):
            yield path, value
            return
        for key, child in value.items():
            yield from models(child, path + '.' + key)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from models(child, path + '[' + str(index) + ']')

def unique(values):
    return sorted(set(values), key=str)

def summarize_model(m):
    nodes, elements = m['nodes'], m['elements']
    loads = [x for c in m.get('load_cases', []) for x in c.get('loads', [])]
    return {
        'dimension': m.get('coordinate_system', {}),
        'nodes': len(nodes), 'elements': len(elements),
        'elementTypes': unique(x.get('type') for x in elements),
        'sectionTypes': unique(x.get('type') for x in m['sections']),
        'sectionPropertyKeys': unique(k for x in m['sections'] for k in x.get('properties', {})),
        'loadTypes': unique(x.get('type') for x in loads),
        'loadFrames': unique(x.get('reference_frame', '<default>') for x in loads),
        'loadKeys': unique(k for x in loads for k in x),
        'controls': m.get('analysis_control', {}),
        'releases': [dict(id=x['id'], releases=x['releases']) for x in elements if x.get('releases')],
        'nonzeroOffsets': [x['id'] for x in elements if any(v for v in (x.get('offsets') or {}).values())],
        'masses': [dict(id=n['id'], mass=n['mass']) for n in nodes if n.get('mass') is not None],
        'stories': len(m.get('stories') or []),
        'materialNames': [x.get('name') for x in m['materials']],
        'groundedComponents': grounded_components(nodes, elements),
    }

def grounded_components(nodes, elements):
    edges = {n['id']: set() for n in nodes}
    for e in elements:
        ids = e.get('nodes', [])
        for a in ids:
            for b in ids:
                if a in edges and b in edges: edges[a].add(b)
    remaining, result = set(edges), []
    by_id = {n['id']: n for n in nodes}
    while remaining:
        stack, visited = [min(remaining)], set()
        while stack:
            node = stack.pop()
            if node in visited: continue
            visited.add(node)
            stack.extend(edges[node] - visited)
        remaining -= visited
        restraints = [by_id[n].get('restraints', [False] * 6) for n in visited]
        result.append({'nodes': len(visited), 'restrainedDofs': sum(sum(v) for v in restraints),
                       'fullyFixedNodes': sum(all(v) for v in restraints)})
    return result

def case_row(c):
    turns, all_models, source_files = [], [], []
    for t in c['turns']:
        public, private = EDITION / t['public'], EDITION / t['private']
        task, ref = read(public / 'task.json'), read(private)
        model_rows = []
        for location, model in models(ref):
            feature = summarize_model(model)
            model_rows.append({'location': location, **feature})
        all_models.extend(model_rows)
        missing, attachments = [], []
        for name in task.get('attachments', []):
            f = public / name
            if not f.is_file(): missing.append(name)
            else: attachments.append({'path': name, 'bytes': f.stat().st_size})
        files = [f for f in sorted(public.rglob('*')) if f.is_file()]
        source_files.extend(str(f.relative_to(EDITION)) for f in files)
        queries = task.get('requests', [])
        turns.append({
            'id': t['id'], 'kind': ref.get('kind'), 'public': t['public'], 'private': t['private'],
            'instruction': task.get('instruction'), 'requestCount': len(queries),
            'requestComponents': unique(q.get('component') for q in queries if 'component' in q),
            'requestLocations': unique(q.get('location', {}).get('kind') for q in queries if 'location' in q),
            'requestPaths': [q['path'] for q in queries if 'path' in q],
            'attachments': attachments, 'missingAttachments': missing,
            'selections': task.get('selections'), 'requirements': task.get('requirements'),
            'parameters': ref.get('parameters'), 'referenceChecksCount': len(ref.get('referenceChecks', [])),
            'optimalDesigns': ref.get('optimalDesigns'), 'leastViolationDesigns': ref.get('leastViolationDesigns'),
            'designCombinations': len(ref.get('truths', [])), 'modelCount': len(model_rows),
            'primaryTemplateProperties': {k: len(v) for k, v in ref.get('primaryTemplate', {}).items() if isinstance(v, list)},
        })
    aggregated = {}
    for key in ['elementTypes', 'sectionTypes', 'sectionPropertyKeys', 'loadTypes', 'loadFrames', 'loadKeys']:
        aggregated[key] = unique(v for m in all_models for v in m[key])
    aggregated['maxNodes'] = max((m['nodes'] for m in all_models), default=0)
    aggregated['maxElements'] = max((m['elements'] for m in all_models), default=0)
    aggregated['modelRecords'] = len(all_models)
    aggregated['spatialFrameModelRecords'] = sum(m['dimension'].get('dimension') == '3d' and bool(set(m['elementTypes']) & {'beam', 'column'}) for m in all_models)
    aggregated['dimensions'] = unique(json.dumps(m['dimension'], sort_keys=True) for m in all_models)
    aggregated['controls'] = unique(json.dumps(m['controls'], sort_keys=True) for m in all_models)
    aggregated['nonzeroOffsets'] = unique(v for m in all_models for v in m['nonzeroOffsets'])
    aggregated['releases'] = unique(json.dumps(r['releases'], sort_keys=True) for m in all_models for r in m['releases'])
    aggregated['ungroundedModels'] = sum(any(x['restrainedDofs'] == 0 for x in m['groundedComponents']) for m in all_models)
    return {'id': c['id'], 'engine': c['engine'], 'family': c['family'], 'level': c['level'],
            'analysis': c['analysis'], 'title': c['title'], 'inputMode': c['inputMode'],
            'integration': c.get('integration'), 'manifest': c, 'features': aggregated,
            'turns': turns, 'sourceFiles': source_files, 'models': all_models}

def inventory():
    manifest = read(EDITION / 'manifest.json')
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for index, c in enumerate(manifest['cases'], 1):
        row = case_row(c)
        rows.append(row)
        if index % 25 == 0: print(json.dumps({'casesInventoried': index, 'turns': sum(len(r['turns']) for r in rows)}), flush=True)
    (OUT / 'inventory.json').write_text(json.dumps({'cases': rows}, ensure_ascii=False, indent=2) + '\n')
    compact = [{k: v for k, v in row.items() if k not in ['models', 'sourceFiles', 'manifest']} for row in rows]
    (OUT / 'compact.json').write_text(json.dumps(compact, ensure_ascii=False, indent=2) + '\n')
    stats = {'cases': len(rows), 'turns': sum(len(r['turns']) for r in rows),
             'modelsRead': sum(r['features']['modelRecords'] for r in rows),
             'publicFilesReadInventory': sum(len(r['sourceFiles']) for r in rows),
             'missingAttachments': {r['id']: [x for t in r['turns'] for x in t['missingAttachments']] for r in rows if any(t['missingAttachments'] for t in r['turns'])}}
    for key in ['elementTypes', 'sectionTypes', 'loadTypes', 'loadFrames', 'nonzeroOffsets', 'controls', 'releases']:
        counts = Counter(v for r in rows for v in r['features'][key])
        stats[key] = dict(counts)
    (OUT / 'inventory-summary.json').write_text(json.dumps(stats, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(stats, ensure_ascii=False), flush=True)
    return rows, stats

def sha(data):
    return hashlib.sha256(data).hexdigest()


def source_evidence():
    entries = []
    for key, path, anchor, description in EVIDENCE:
        data = (SNAPSHOTS / PRIMARY / path).read_bytes()
        original = subprocess.check_output(['git', '-c', 'safe.directory=*', '-C', str(GIT_SOURCE), 'show', PRIMARY + ':' + path])
        if data != original:
            raise ValueError('Review source differs from the pinned Git blob: ' + path)
        lines = data.decode().splitlines()
        line = next(i for i, text in enumerate(lines, 1) if anchor in text)
        entries.append({'id': key, 'path': path, 'line': line, 'sha256': sha(data), 'description': description,
                        'repository': 'qinsz01/structureclaw', 'commit': PRIMARY,
                        'url': f'https://github.com/qinsz01/structureclaw/blob/{PRIMARY}/{path}#L{line}',
                        'excerpt': '\n'.join(lines[max(0, line - 2):line + 8])})
    benchmark_commit = 'f07eb3f8bf8b497d7f1076cbdb9e6a95c36f9a0d'
    for key, path, anchor, description in [
        ('bench-job-binding', 'scripts/research300_v3/grade_candidate_v31.cjs', 'const jobs=e.loadJobs', '当前v3入口读取broker封存作业、答卷与当前轮作业绑定'),
        ('bench-empty-extra', 'scripts/research300_v3/physical-v31.cjs', 'Object.keys(row.extra).length===0', '当前比较视图仅消去明确为空的extra'),
        ('bench-section-fields', 'scripts/research300_v3/fidelity.cjs', 'comparePhysicalFields(normalizedPropertyRecord(as,true', '截面记录的非空extra仍进入字段比较'),
        ('bench-sclaw-import', 'lib/import-structureclaw.cjs', 'function normalizeToolEvents', '既有sclaw归档/工具事件入口不等于v3候选接入已完成'),
    ]:
        data = (ROOT / path).read_bytes()
        original = subprocess.check_output(['git', '-c', 'safe.directory=*', '-C', str(ROOT), 'show', benchmark_commit + ':' + path])
        if data != original: raise ValueError('Frozen benchmark implementation changed: ' + path)
        lines = data.decode().splitlines(); line = next(i for i, text in enumerate(lines,1) if anchor in text)
        entries.append({'id': key, 'path': path, 'line': line, 'sha256': sha(data), 'description': description,
                        'repository': 'qinsz01/structureclaw-benchmark', 'commit': benchmark_commit,
                        'url': str(ROOT / path) + ':' + str(line),
                        'excerpt': '\n'.join(lines[max(0,line-2):line+8]), 'commitPublished': False})
    return entries


def public_sources(rows, manifest):
    expected = {r['path']: r['sha256'] for r in manifest['files']}
    sources, by_case, issues = [], defaultdict(list), []
    for row in rows:
        for name in row['sourceFiles']:
            data = (EDITION / name).read_bytes()
            item = {'path': name, 'bytes': len(data), 'sha256': sha(data), 'caseId': row['id']}
            if item['sha256'] != expected.get(name):
                issues.append({'caseId': row['id'], 'path': name, 'issue': 'Frozen public bytes differ'})
            suffix = Path(name).suffix.lower()
            if suffix == '.json':
                json.loads(data)
            elif suffix == '.csv':
                table = list(csv.reader(data.decode('utf-8-sig').splitlines()))
                item.update(rows=max(0, len(table) - 1), columns=len(table[0]) if table else 0)
            elif suffix == '.png':
                if data[:8] != b'\x89PNG\r\n\x1a\n' or data[12:16] != b'IHDR':
                    issues.append({'caseId': row['id'], 'path': name, 'issue': 'Invalid PNG header'})
                else:
                    item['width'], item['height'] = struct.unpack('>II', data[16:24])
                    if len(data) > 4 * 1024 * 1024:
                        issues.append({'caseId': row['id'], 'path': name, 'issue': 'Exceeds native vision data-URI size boundary'})
            else:
                data.decode('utf-8')
            sources.append(item)
            by_case[row['id']].append(item)
    return sources, by_case, issues


def static_model_notes(model, engine):
    notes = []
    nodes = {str(n['id']): n for n in model['nodes']}
    mats = {str(m['id']): m for m in model['materials']}
    secs = {str(s['id']): s for s in model['sections']}
    if len(nodes) != len(model['nodes']): notes.append('重复节点ID')
    for node in nodes.values():
        if any(not isinstance(node.get(a), (int, float)) or not math.isfinite(node[a]) for a in ('x', 'y', 'z')): notes.append('非有限坐标')
        if len(node.get('restraints', [])) != 6: notes.append('未明确六自由度支承')
    for element in model['elements']:
        if element.get('type') not in {'beam', 'column', 'truss', 'brace'}: notes.append('未覆盖构件类型')
        ids = [str(x) for x in element.get('nodes', [])]
        if len(ids) != 2 or any(n not in nodes for n in ids):
            notes.append('构件节点引用不完整'); continue
        length = math.dist([nodes[ids[0]][a] for a in ('x', 'y', 'z')], [nodes[ids[1]][a] for a in ('x', 'y', 'z')])
        if length <= 0: notes.append('零长度杆件')
        material, section = mats.get(str(element.get('material'))), secs.get(str(element.get('section')))
        if material is None or section is None:
            notes.append('材料或截面引用缺失'); continue
        if not isinstance(material.get('E'), (int, float)) or material['E'] <= 0: notes.append('弹性模量未明确或非正')
        for key in (['A', 'Iy', 'Iz', 'J'] if element['type'] in {'beam', 'column'} else ['A']):
            if not isinstance(section.get('properties', {}).get(key), (int, float)) or section['properties'][key] <= 0: notes.append('截面刚度参数未明确或非正: ' + key)
        if any((element.get('offsets') or {}).values()): notes.append('需要未覆盖的非零偏心')
    control = model.get('analysis_control', {})
    if any(control.get(k) is True for k in ['p_delta', 'rigid_offsets', 'construction_stage']): notes.append('需要未覆盖的控制项')
    if engine == 'YJK':
        positions = [tuple(round(n[a] * 1000) for a in ('x', 'y', 'z')) for n in nodes.values()]
        if len(set(positions)) != len(positions): notes.append('YJK毫米坐标重复')
        if any(abs(n[a] * 1000 - round(n[a] * 1000)) > 1e-6 for n in nodes.values() for a in ('x', 'y', 'z')): notes.append('YJK输入并非毫米整点')
    return unique(notes)


def retained_reference_notes(value):
    """Describe existing algebra records; do not recompute or certify them anew."""
    pivots, residuals = [], []
    def visit(item):
        if isinstance(item, dict):
            pivot, residual = item.get('minimumScaledPivot'), item.get('freeResidual')
            if isinstance(pivot, (int, float)): pivots.append(pivot)
            if isinstance(residual, (int, float)): residuals.append(abs(residual))
            for child in item.values(): visit(child)
        elif isinstance(item, list):
            for child in item: visit(child)
    visit(value)
    return {'source': 'Retained authoring/reference appendix; no new numeric verification',
            'factorizationRecords': len(pivots), 'minimumRetainedScaledPivot': min(pivots, default=None),
            'nonPositiveRetainedPivotRecords': sum(p <= 0 for p in pivots),
            'maximumRetainedFreeResidual': max(residuals, default=None),
            'nativeReferenceBindingPresent': isinstance(value.get('nativeReferenceBinding'), dict)}


def case_assessment(row, input_row, sources):
    ids = ['model', 'files', 'edit', 'analysis', 'results', 'query', 'boundary', 'budget']
    if row['engine'] == 'OpenSees': ids += ['line-model', 'loads', 'providers']
    elif row['engine'] == 'PKPM': ids += ['pkpm', 'pkpm-grade', 'pkpm-version', 'pkpm-section']
    else: ids += ['yjk']
    if row['family'] == 'INT': ids += ['undo']
    if row['family'] == 'MM': ids += ['vision']
    if row['features']['releases']: ids += ['release']
    if row['analysis'] in {'modal', 'transient'}: ids += ['mass', 'modal']
    if row['analysis'] == 'transient': ids += ['transient']
    if row['analysis'] in {'scenario', 'project'}: ids += ['arithmetic']
    if row['analysis'] == 'project': ids += ['section-rules', 'section-geometry', 'shell', 'defaults']

    notes, turns, material_names, general = [], [], set(), False
    for t in row['turns']:
        data = (EDITION / t['private']).read_bytes()
        ref = json.loads(data)
        local_notes = []
        for location, model in models(ref):
            local_notes += [location + ': ' + n for n in static_model_notes(model, row['engine'])]
            material_names.update(str(m.get('name', '')) for m in model['materials'])
            general |= any(str(s.get('type')).lower() == 'general' for s in model['sections'])
        notes.extend(local_notes)
        turns.append({'caseId': row['id'], 'turnId': t['id'], 'kind': t['kind'],
                      'public': t['public'], 'privateReferencePath': t['private'], 'privateReferenceSha256': sha(data),
                      'instruction': t['instruction'], 'requestCount': t['requestCount'],
                      'requestComponents': t['requestComponents'], 'requestPaths': t['requestPaths'],
                      'attachments': [f['path'] for f in t['attachments']],
                      'missingAttachments': t['missingAttachments'], 'parameters': {k: (len(v) if isinstance(v, list) else v) for k, v in (t['parameters'] or {}).items()},
                      'referenceInputNotes': unique(local_notes),
                      'retainedReferenceEvidence': retained_reference_notes(ref),
                      'finiteDesignCount': t['designCombinations'] or None,
                      'hasFeasibleDesign': bool(t['optimalDesigns']) if t['kind'] == 'project' else None,
                      'hasLeastViolationWitness': bool(t['leastViolationDesigns']) if t['kind'] == 'project' else None})

    prerequisites = ['给定求解器及依赖可用；冻结本次工具配置、预算和输入交付方式']
    issues = []
    if row['family'] == 'MM':
        prerequisites.append('配置视觉模型；所有图纸作为原始图片进入analyze_file并保留字段证据')
        issues.append('VISION-CONFIG')
    if row['features']['spatialFrameModelRecords']:
        issues.append('SCLAW-METADATA-COMPARISON')
    if row['family'] == 'INT':
        prerequisites.append('同一题保持会话和稳定ID，局部变更后重新分析；恢复Q时保留新增D')
    engine_status = '静态覆盖；依赖运行环境'
    recorded_environment = '未做运行核验'
    if row['engine'] in {'PKPM', 'YJK'}:
        prerequisites.append('兼容的Windows原生软件、SDK和许可；本轮不联网探测安装')
    if row['engine'] == 'PKPM':
        recorded_environment = '当前已记录2027安装与发布分支不兼容'
        engine_status = '发布分支在已记录2027环境下阻塞'
        issues.append('PKPM-2027')
        if any('steel' in name.lower() and not any(token in name.upper() for token in ('Q235', 'Q345', 'Q355', 'Q390', 'Q420', 'S235', 'S355')) for name in material_names):
            issues.append('PKPM-DESCRIPTIVE-GRADE')
        if general: issues.append('PKPM-GENERAL-ALIAS')
    agent_status = '已有建模、修改、分析和取数入口'
    if row['analysis'] == 'project':
        agent_status = '条件覆盖：规则证据与编程/预算须明确'
        issues += ['PROJECT-RULE-EVIDENCE', 'PROJECT-COMPUTATION-POLICY']
        prerequisites.append('设计目录比例规则须进入可核验的真实输入；保留名义截面作为规则来源，按几何重算属性')
        prerequisites.append('如使用程序搜索，明确开启已有受限shell与Python；默认shell关闭、每轮工具上限200，未证明默认配置下的完整搜索成本')
    if notes or any(t['missingAttachments'] for t in turns):
        agent_status = '有待人工核对的输入项'
        issues.append('INPUT-REVIEW')
    paths = {
        'static': '读取图表→显式建模→按指定引擎分析各工况/组合→查询指定带符号量',
        'modal': '重建几何→按D与规定比例Q/g推导节点质量→显式X向nodal质量→模态分析→周期/频率/有效质量/振型',
        'transient': '重建几何与显式X向质量→读取原始激励与单位→按给定步长/阻尼执行线弹性时程→查询记录样本与峰值',
        'scenario': '从受荷几何换算各工况→分别构成指定场景→分析全部组合→检索全部规定节点与端截面→带控制位置报告相对变化',
        'project': ('两个子模型逐工况分析→读取上部四支点反力并反号传给主体→检查全部组合和全局约束→有限截面方案搜索'
                    if row['manifest'].get('integration') == 'one-way' or any(t.get('requirements', {}).get('oneWayTransfer') for t in row['turns'] if t.get('requirements'))
                    else '按接口表合并共有节点与转角自由度→求解整体模型全部组合→核对接口相容和全局约束→有限截面方案搜索'),
    }
    if row['analysis'] == 'project':
        initial_infeasible = not turns[0]['hasFeasibleDesign']
        task_answer = '可作答：报告无可行设计及最小最大利用率见证' if initial_infeasible else '可作答：有限方案中比较约束和最小体积'
    else:
        task_answer = '题设完整、模型形式可计算；静态范围结论'
    return {'caseId': row['id'], 'family': row['family'], 'level': row['level'], 'engine': row['engine'],
            'analysis': row['analysis'], 'title': row['title'], 'inputMode': row['inputMode'],
            'turnCount': len(turns), 'taskAnswerability': task_answer,
            'publicInputRecord': input_row, 'features': row['features'],
            'publishedForkScope': engine_status, 'agentWorkflow': agent_status,
            'recordedEnvironment': recorded_environment,
            'localBranchComparison': '同一物理功能；本地7个提交补足2027、描述性材料和general映射' if row['engine'] == 'PKPM' else '相关分析实现未因这7个提交增加求解能力',
            'completionPath': paths[row['analysis']], 'prerequisites': prerequisites,
            'issueIds': unique(issues), 'sourceEvidenceIds': unique(ids), 'referenceInputNotes': unique(notes),
            'publicFiles': len(sources), 'pngFiles': sum(Path(s['path']).suffix == '.png' for s in sources),
            'allOriginalPublicFilesByteBound': True, 'turns': turns,
            'benchmarkDelivery': '既有runId/归档与v3 broker jobId/answer.json的接入约定仍须单独冻结；不作为模型错误',
            'notAnExecutionResult': True}


def write_reports(rows, stats):
    manifest_data = (EDITION / 'manifest.json').read_bytes()
    binding = read(ARCHIVE_ROOT / 'docs/implementation/reviews/research300-v3-sclaw-static-scope-20261029/fork-binding.json')
    if sha(manifest_data) != binding['editionManifestSha256'] or sha((ROOT / 'corpora/research300-v3-v1/manifest.json').read_bytes()) != binding['editionManifestSha256']:
        raise ValueError('Published/cached edition manifest differs from the reviewed edition')
    manifest = json.loads(manifest_data)
    old = read(ARCHIVE_ROOT / 'docs/implementation/reviews/research300-v3-20261028/input-audit.json')
    if old['manifestSha256'] != sha(manifest_data): raise ValueError('Historical input record has another edition binding')
    previous = {r['caseId']: r for r in old['rows']}
    sources, by_case, source_issues = public_sources(rows, manifest)
    evidence = source_evidence()
    assessments = [case_assessment(r, previous[r['id']], by_case[r['id']]) for r in rows]
    turns = [t for r in assessments for t in r['turns']]
    expected_files = {r['path']: r['sha256'] for r in manifest['files']}
    if any(expected_files.get(t['privateReferencePath']) != t['privateReferenceSha256'] for t in turns):
        raise ValueError('Retained reference bytes differ from the frozen edition')
    if len(assessments) != 300 or len({r['caseId'] for r in assessments}) != 300 or len(turns) != 560:
        raise ValueError('Static review does not cover the exact 300-case/560-turn inventory')
    if source_issues: raise ValueError('Original public artifacts require review: ' + json.dumps(source_issues))
    REVIEW.mkdir(parents=True, exist_ok=True)
    def write(name, value):
        (REVIEW / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    write('source-evidence.json', {'primarySclawCommit': PRIMARY,
          'benchmarkReadOnlyCommit': 'f07eb3f8bf8b497d7f1076cbdb9e6a95c36f9a0d',
          'scope': 'Selected manually inspected source paths, exact Git blob bytes; each row records its own repository/commit', 'rows': evidence})
    write('public-artifact-integrity.json', {'manifestSha256': sha(manifest_data), 'filesReadAndByteBound': len(sources),
          'allOriginalPublicBytesMatch': not source_issues, 'formatReadOnly': True, 'rows': sources})
    write('case-assessments.json', {'reviewMode': 'static-only', 'baseline': PRIMARY, 'cases': assessments})
    write('turn-requirements.json', {'reviewMode': 'static-only', 'baseline': PRIMARY, 'rows': turns})
    groups = {key: dict(Counter(r[key] for r in assessments)) for key in ['engine', 'analysis', 'publishedForkScope', 'agentWorkflow']}
    issues = {key: [r['caseId'] for r in assessments if key in r['issueIds']] for key in sorted({k for r in assessments for k in r['issueIds']})}
    summary = {'reviewMode': 'static-only', 'primaryRepository': 'qinsz01/structureclaw', 'branch': 'work/research-next',
               'publishedCommit': PRIMARY, 'localComparisonCommit': LOCAL,
               'manifestSha256': sha(manifest_data), 'casesIndividuallyAssessed': len(assessments),
               'turnsIndividuallyRecorded': len(turns), 'publicFilesReadAndByteBound': len(sources),
               'retainedReferenceModelRecordsInspected': stats['modelsRead'],
               'historicalInputRecordsMatched': len(previous), 'historicalInputReviewWasBlind': False,
               'newCandidateInvocations': 0, 'newNativeSolverInvocations': 0, 'testSuitesInvoked': 0,
               'privateReferenceFilesByteBound': len(turns),
               'sourceFeatureGroups': groups, 'caseIssues': issues,
               'globalIntegrationConditions': ['SCLAW-V3-EVIDENCE-ADAPTER', 'SCLAW-METADATA-COMPARISON'],
               'referenceInputNotes': {r['caseId']: r['referenceInputNotes'] for r in assessments if r['referenceInputNotes']},
               'initialNoFeasibleDesignButAnswerable': [r['caseId'] for r in assessments if r['analysis'] == 'project' and not r['turns'][0]['hasFeasibleDesign']],
               'all300UnconditionallyExecutableOnPublishedFork': False,
               'frameworkScopeIsNotCandidateSuccessRate': True,
               'productionSourceChanged': False, 'editionChanged': False, 'pushed': False, 'deployed': False}
    write('summary.json', summary)
    issue_rows = []
    for key, title, layer, finding, action, evidence_ids in ISSUES:
        affected = issues.get(key, [r['caseId'] for r in assessments] if key.startswith('SCLAW-') else [])
        issue_rows.append({'id': key, 'title': title, 'layer': layer, 'finding': finding, 'nextAction': action,
                           'affectedCases': affected, 'caseCount': len(affected), 'sourceEvidenceIds': evidence_ids,
                           'status': '静态条件/风险；未运行测试', 'doesNotMeanQuestionHasNoAnswer': True})
    write('issue-details.json', {'reviewMode': 'static-only', 'rows': issue_rows})
    columns = ['caseId', 'family', 'level', 'engine', 'analysis', 'turnCount', 'taskAnswerability', 'publishedForkScope', 'agentWorkflow', 'completionPath', 'prerequisites', 'issueIds', 'sourceEvidenceIds']
    with (REVIEW / 'case-assessments.csv').open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=columns); writer.writeheader()
        for r in assessments: writer.writerow({k: '; '.join(r[k]) if isinstance(r[k], list) else r[k] for k in columns})
    (REVIEW / 'case-matrix.md').write_text('# 300题逐题静态能力审查\n\n仅对照源码和题设，未运行候选、求解器或测试套件。主基线为个人fork `work/research-next@'+PRIMARY+'`。\n\n|题号|等级|引擎|轮数|发布分支/已记录环境|Agent流程|条件/问题编号|\n|---|---|---|---:|---|---|---|\n' + '\n'.join('|'+ '|'.join([r['caseId'],r['level'],r['engine'],str(r['turnCount']),r['publishedForkScope'],r['agentWorkflow'],', '.join(r['issueIds']) or '常规依赖/输入配置'])+'|' for r in assessments) + '\n', encoding='utf-8')
    write_overview(summary, assessments, evidence, issue_rows)
    return summary


def write_overview(summary, assessments, evidence, issues):
    n = summary['retainedReferenceModelRecordsInspected']
    no_design = ', '.join(summary['initialNoFeasibleDesignButAnswerable'])
    issue_text = '\n\n'.join('### ' + r['id'] + '：' + r['title'] + '\n\n' + r['finding'] + '\n\n处理方向：' + r['nextAction'] for r in issues)
    text = f'''# Research300 v3：个人fork最新分支逐题静态能力审查

**300题、560轮均已逐项整理；本轮未调用候选、求解器或测试套件。不能把全部300题直接认定为发布分支在当前已记录环境下无条件可完成。**

[逐题Excel](capability-review.xlsx) · [300题矩阵](case-matrix.md) · [逐题JSON](case-assessments.json) · [560轮要求](turn-requirements.json) · [源码依据](source-evidence.json) · [问题清单](issue-details.json)。

## 审查版本

主基线为用户个人fork [qinsz01/structureclaw 的 work/research-next](https://github.com/qinsz01/structureclaw/tree/{PRIMARY})，提交`{PRIMARY}`。GitHub四条分支头的提交时间已读取，该分支最新；没有使用旧master或官方上游替代。

本地同名开发分支为`{LOCAL}`，比GitHub多7个未上传提交。此前Codex使用的`db3c0b1da44fe668a6037a6c2e7f068d14354539`另含一项显式矩形剪切面积兼容修复。三者分别记录在[fork绑定](fork-binding.json)，没有合并成同一能力声明。本轮没有修改、提交或上传StructureClaw源代码。

## 逐题结论

|范围|静态结论|必要条件/限制|
|---|---|---|
|全部300题|公开资料与参考模型对应，每题有明确分析或决策交付路径|静态审查与既有参考记录不构成新的执行验收|
|OpenSees 270题|所需二维XZ/三维线弹性杆系、模态和线弹性时程均有源码入口|工程搜索、视觉输入和证据交付条件另列|
|YJK 15题|所需真实三维楼层框架及结果类型位于现有映射内|兼容Windows安装、SDK与许可，本轮不探测环境|
|PKPM 15题|数学模型可表达；发布分支在已记录2027安装下存在版本阻塞|6题另有描述性材料牌号入口问题，2题有general字面映射条件；本地未上传版本已含相关修复|
|工程综合90题|给定目录的27方案有限比较、接口传力/共节点及线弹性响应可由现有功能组成|比例规则的来源证据、已有编程入口和200次工具预算须明确；不标为默认配置无条件完成|
|MM 100题|框架有PNG读取及视觉字段证据入口|需要配置视觉模型；本轮未验证读图成功率|
|全部300题的评测接入|题目功能与运行证据转换分别记录|v3 jobId/answer.json与sclaw runId/归档的接入、合法非物理来源元数据比较仍须冻结|

类别存在交叠，不能把表中题数相加。300题的每个条目均列出规模、构件/荷载类型、各轮要求、完成路径、源码证据编号、版本条件和原始题目位置。

## 可完成性的依据与边界

当前逐项读取并绑定原始字节：5854份公开文件、560份私有参考附录。共静态展开`{n}`个基础模型/保留设计视图；工程题包括每轮全部27种方案的截面和荷载附录，不只检查空载初始模板。未导入或执行SUT、编题求解器或评价模块。源码证据的选定文件与固定Git提交blob逐字节一致。

所需构件仅beam/column/truss，最大96节点、200杆件；二维均为XZ、坐标约定为global-z-up。未发现题设要求非零端偏心、P-Delta、施工阶段、壳/实体、塑性或通用非线性动力。3题有已知支座位移，3题有弯曲端释放，3题启用既有自重入口；这些边界均单独对照了源码。30道动力题使用显式X向节点质量，时程为给定一致时间步、g单位激励和已支持的响应类型。

正参数、几何连通和有支承只是静态必要条件；稳定性及参考数值的存档依据来自编制阶段的独立参考记录，本轮仅阅读其记录，没有重算或把它们包装成新测试。公开几何的既有300题复核记录与本版manifest一致；图像部分采用字体模板转写，属于源引导复核，不是外部盲审。

九道首态没有可行设计的题仍有合法答案：按题意报告不可行，并提交最大约束利用率最小的见证方案。它们是：`{no_design}`。逐轮记录另外列出后续状态是否仍有可行设计；不把“没有满足限值的设计”混同为“题目无法作答”。

## 具体条件与待处理项

{issue_text}

## 使用本记录

本记录确认的是题目需求、现有接口与必要条件之间的对应关系，不预测语言模型一定答对，不引用Codex通过率证明sclaw能力。当前应先明确采用哪个系统提交、商业端安装、视觉/编程配置及原始输入/证据交付约定，再开展用户后续明确授权的运行工作。本轮没有开展该工作。

仅本地保存和提交；题库、参考答案、数值容差、历史成绩与SUT均保持原版本，未push或部署。
'''
    (REVIEW / 'README.md').write_text(text, encoding='utf-8')
    export_workbook(assessments, evidence, issues, summary)


def export_workbook(assessments, evidence, issues, summary):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    book = Workbook(); book.remove(book.active)
    sheets = [
        ('逐题结论', ['题号', '形态', '等级', '引擎', '分析', '轮数', '题目可作答性', '发布fork/已记录环境', 'Agent路径', '最大节点/构件', '完成路径', '必要条件', '条件编号', '源码编号', '原始题面'],
         [[r['caseId'], r['family'], r['level'], r['engine'], r['analysis'], r['turnCount'], r['taskAnswerability'], r['publishedForkScope'], r['agentWorkflow'], str(r['features']['maxNodes'])+'/'+str(r['features']['maxElements']), r['completionPath'], '\n'.join(r['prerequisites']), ', '.join(r['issueIds']), ', '.join(r['sourceEvidenceIds']), 'corpora/research300-v3-v1/'+r['turns'][0]['public']] for r in assessments]),
        ('逐轮要求', ['题号', '轮次', '类型', '原始任务要求', '请求分量', '请求路径', '附件', '动力参数/数组长度', '有限设计数', '有可行设计', '有最小违反见证', '原始题面', '参考SHA256', '存档参考记录'],
         [[r['caseId'], t['turnId'], t['kind'], t['instruction'], ', '.join(t['requestComponents']), json.dumps(t['requestPaths'],ensure_ascii=False), '\n'.join(t['attachments']), json.dumps(t['parameters'],ensure_ascii=False), t['finiteDesignCount'], t['hasFeasibleDesign'], t['hasLeastViolationWitness'], t['public'], t['privateReferenceSha256'], json.dumps(t['retainedReferenceEvidence'],ensure_ascii=False)] for r in assessments for t in r['turns']]),
        ('源码依据', ['编号', '能力/限制', '固定源码', '行', '源码SHA256', '固定提交链接', '源码摘录'],
         [[r['id'], r['description'], r['path'], r['line'], r['sha256'], r['url'], r['excerpt']] for r in evidence]),
        ('条件与问题', ['编号', '说明', '层次', '题数', '具体发现', '处理方向', '题号', '源码编号'],
         [[r['id'], r['title'], r['layer'], r['caseCount'], r['finding'], r['nextAction'], '\n'.join(r['affectedCases']), ', '.join(r['sourceEvidenceIds'])] for r in issues]),
        ('版本与范围', ['字段', '内容'], [[k, json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v] for k,v in summary.items()]),
    ]
    for title, headers, rows in sheets:
        sheet = book.create_sheet(title); sheet.append(headers)
        for row in rows:
            if any(isinstance(v,str) and len(v)>32767 for v in row): raise ValueError('Workbook text requires explicit chunks')
            sheet.append(row)
        sheet.freeze_panes = 'A2'; sheet.auto_filter.ref = sheet.dimensions
        for cell in sheet[1]:
            cell.font = Font(bold=True, color='FFFFFF'); cell.fill = PatternFill('solid',fgColor='294D66')
        for cells in sheet.iter_rows(min_row=2):
            for cell in cells:
                if isinstance(cell.value,str): cell.data_type = 's'
                cell.alignment = Alignment(vertical='top',wrap_text=True)
        for index in range(1,len(headers)+1): sheet.column_dimensions[get_column_letter(index)].width = 25 if index<7 else 48
    book.save(REVIEW / 'capability-review.xlsx')


def main():
    global EDITION, OUT, REVIEW
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--edition', type=Path, default=EDITION)
    parser.add_argument('--scratch', type=Path, default=OUT)
    parser.add_argument('--report', type=Path, default=REVIEW)
    args = parser.parse_args()
    EDITION, OUT, REVIEW = args.edition.resolve(), args.scratch.resolve(), args.report.resolve()
    rows, stats = inventory()
    summary = write_reports(rows, stats)
    print(json.dumps({k: v for k, v in summary.items() if k != 'caseIssues'}, ensure_ascii=False, indent=2), flush=True)


if __name__ == '__main__': main()
