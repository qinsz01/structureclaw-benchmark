"""Evidence-guided reuse recommendations; never modifies a corpus or old score."""
from collections import Counter, defaultdict
import csv
import hashlib
import io
import json
from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[2]
EDITION = ROOT / '.bench-work/section-diversity-v1-final-20261027'
ARCHIVE = Path(os.environ.get('SCLAW_BENCH_ARCHIVE', ROOT)).expanduser() / 'docs/implementation/reviews/codex-diversity300-20261027'
DEST = ROOT / 'planning/research300-v2/reuse-review'

# Editorial selection after inspecting old task briefs, states, public input
# manifests and validation records. These are candidate pools, not v2 acceptance.
PRIORITY = {
 'STD': '1 2 5 8 12 15 19 24 48 50 60 62 74 27 29 30 32 34 35 36 37 38 39 79 80 81 82 83 84 85 86 87 89 90 91 40 41 42 63 93',
 'MM': '1 2 8 12 13 19 24 26 45 49 50 61 74 27 28 30 33 34 35 36 37 38 39 79 80 81 82 83 84 85 86 87 89 90 91 40 41 42 63 93',
 'INT': '1 9 12 19 26 49 54 66 74 33 34 38 39 84 88 89 90 42 93 100',
}
REGRESSION = {
 'STD': '3 4 6 7 9 10 16 18 20 23 25 28 31 33 43 45 55 71 95 96',
 'MM': '3 5 6 9 11 16 17 18 20 22 23 25 29 44 46 48 53 54 95 96',
 'INT': '2 7 15 17 18 24 25 29 36 37 44 51 62 68 69 70 72 73 86 95',
}
PILOT = [
 'STD-001','STD-008','STD-036','STD-040','STD-080','STD-088',
 'MM-001','MM-036','MM-039','MM-061','MM-081','MM-079',
 'INT-001','INT-009','INT-033','INT-074','INT-079','INT-084',
]
LABELS = {
 'retain-core': '优先保留题核',
 'reorganize': '复用素材并重组',
 'regression-only': '保留回归、不优先占计分名额',
}
SPECIAL = {
 'STD-080': '保留空间框架与受荷宽度题核；新交付改为正文摘要和完整机器表。旧正文缺全表仍是旧契约下的失败，不改历史分数。',
 'STD-088': '保留双向侧力与原生模型；重组交付为正文摘要和完整机器表，不把重复粘贴全表作为新题主要难点。',
 'STD-089': '保留边/角/中柱分组物理模型；同引擎参考与跨引擎微小弯矩精度诊断分开报告。',
 'STD-091': '保留分区加载题核；继续保存严格跨引擎差异，不能自动扩大所有新题容差。',
 'INT-033': '保留 query-only 与带符号控制轴力；Codex 的符号失败不构成删题理由。',
 'MM-015': '保留连续梁数值回归；重排参数表与工程单位，并在输入舍入改变时重算参考；不能仅因一次抄写失败而变更旧分数。',
 'MM-039': '保留三弦杆桁架与杆件类型区分；将轴力杆误建成梁是实质建模差异。',
 'MM-041': '保留空间杆系拓扑；轴向响应与逐字段重建分开报告，非作用参数 J 的抄写差异不能称为轴向响应错误。',
 'MM-070': '保留斜柱几何及分组属性；参数表以清晰工程单位和合理有效位数呈现，改变公开精度须重算参考。',
 'MM-090': '保留分层局部轴、角柱支座与双向弯曲；截面 J 是否起作用须按实际模型分析，不因它是抄写问题就忽略。',
}


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hash(case, contract):
    names = sorted(set(['contract.json','prompt.txt','reference-requests.json'] +
                       contract.get('attachments',[]) + contract.get('modelStates',[])), key=lambda s:s.encode())
    record = {'schemaVersion':1,'files':[{'path':n,'sha256':sha(case/n)} for n in names]}
    return hashlib.sha256(json.dumps(record,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()


def geometry_group(model):
    # A conservative same-geometry/support grouping, NOT a topology-isomorphism
    # or the proposed v2 180-topology acceptance check. No scale normalization.
    nodes = model['nodes']
    offset = [min(float(n.get(k,0)) for n in nodes) for k in ('x','y','z')]
    active = [0,2,4] if model['coordinate_system']['dimension']=='2d' else list(range(6))
    records = {str(n['id']): (tuple(round(float(n.get(k,0))-a,8) for k,a in zip(('x','y','z'),offset)),
                tuple(bool((n.get('restraints') or [False]*6)[i]) for i in active)) for n in nodes}
    edges = sorted((str(e['type']),tuple(sorted((records[str(e['nodes'][0])], records[str(e['nodes'][1])]))))
                   for e in model['elements'])
    value = [model['coordinate_system']['dimension'],sorted(records.values()),edges]
    return hashlib.sha256(json.dumps(value,separators=(',',':')).encode()).hexdigest()


def guidance(old, contract, model, decision):
    notes = []
    family = old['id'].split('-')[0]
    if decision=='retain-core':
        notes.append('覆盖有区分度的受力、连接、支承、属性或状态行为，作为优先迁移候选；不是原样放行。')
    elif decision=='regression-only':
        notes.append('压缩基础模板或单字段交互的重复配额，保留全部旧题、参考与成绩作回归；不是判定题目错误或精确重复。')
    else:
        notes.append('复用已有模型、资料制作方法和参考校验；需围绕新版任务目标重组后再决定是否占计分名额。')
    if family=='INT':
        if len(contract['turns'])<=2:
            notes.append('现有流程至多两轮，优先组合定向修改、保留项、局部撤销或结果复用；基础层可留少量两轮代表。')
        if all(t.get('expectation')=='analyze' for t in contract['turns']) and len(contract['modelStates'])>1:
            notes.append('已有多状态模型可作为交互起点；新增轮次不能只重复改同一数值。')
        if len(contract['turns'])==1:
            notes.append('合法输入直接执行的控制仍要在新交互题中保留；不必把每种合法值另占一题。')
    if family=='MM':
        notes.append('实际候选包按归档核验；不要把维护者 SVG 制图源误认为候选可见附件。')
        if len(contract['turns'])>1:
            notes.append('缺图/冲突后的补充资料流程可转入 INT；MM 若保留该题核，提供明确完整的单轮图纸包。')
    if old['engine']!='OpenSees':
        notes.append('保持原定商业引擎及原生参考；新尺寸、材料、荷载或输出须重新取得原生回执。')
    types = {e['type'] for e in model['elements']}
    if types <= {'truss','brace'}:
        notes.append('轴力杆题主要核验 E、A、连接、支承及荷载；附带 I/J 的字段重建与力学响应分开计。')
    if old['id'] in SPECIAL: notes.append(SPECIAL[old['id']])
    return notes


def build():
    selection=read(ARCHIVE/'selection.json')
    selected={r['caseId']:r for r in selection['selected']}
    results={r['caseId']:r for r in read(ARCHIVE/'summary.json')['caseResults']}
    catalogue=read(ROOT/'planning/releases/research300-catalogue.json')['cases']
    manifest=read(ARCHIVE/'archive-manifest.json')['files']
    assert sha(ARCHIVE/'archive-manifest.json')==read(ARCHIVE/'evidence-meta.json')['archiveManifestSha256']
    public=defaultdict(list)
    for e in manifest:
        parts=e['path'].split('/')
        if len(parts)>=7 and parts[0]=='public-environment' and parts[2]=='t1' and parts[3:5]==['agent-input','cases']:
            public[parts[1]].append(e)
    rows=[]
    for old in catalogue:
        cid=old['id'];family,number=cid.split('-')
        folder=EDITION/'corpora/research-300/cases'/cid
        contract=read(folder/'contract.json')
        assert source_hash(folder,contract)==selected[cid]['sourceHash'],cid
        model=read(folder/contract['modelStates'][0])
        assert cid in public,cid
        decision=('retain-core' if int(number) in {int(n) for n in PRIORITY[family].split()} else
                  'regression-only' if int(number) in {int(n) for n in REGRESSION[family].split()} else 'reorganize')
        suffixes=sorted({Path(e['path']).suffix for e in public[cid] if not e['path'].endswith('/task.json')})
        rows.append({
            'caseId':cid,'title':old['title'],'family':family,'category':old['category'],
            'oldDifficulty':old['difficulty'],'engine':old['engine'],
            'dimension':model['coordinate_system']['dimension'],
            'nodeCount':len(model['nodes']),'memberCount':len(model['elements']),
            'memberTypes':sorted({e['type'] for e in model['elements']}),
            'turns':len(contract['turns']),'states':len(contract['modelStates']),
            'firstTurnPublicExtensions':suffixes,
            'sourceHash':selected[cid]['sourceHash'],
            'modelFile':contract['modelStates'][0],'modelSha256':sha(folder/contract['modelStates'][0]),
            'geometrySupportGroup':geometry_group(model),
            'oldCodexStatus':results[cid]['status'],
            'recommendation':decision,'recommendationLabel':LABELS[decision],
            'reason':guidance(old,contract,model,decision),
            'firstPilotCandidate':cid in PILOT,
            'v2Slot':None,'v2Accepted':False,
            'referenceReuseRule':'Only unchanged physical input, requested quantity semantics, precision and engine/settings can reuse numerical truth; otherwise recompute.',
        })
    groups=Counter(r['geometrySupportGroup'] for r in rows)
    for r in rows: r['geometrySupportGroupSize']=groups[r['geometrySupportGroup']]
    v2=read(ROOT/'planning/research300-v2/catalogue.json')['cases']
    engineering={r['id'] for r in v2 if r['provenance']=='engineering-adaptation-target'}
    dynamics={r['id'] for r in v2 if r['analysis']!='linear-static'}
    reuse_slots=[r for r in v2 if r['id'] not in engineering|dynamics]
    old_dimensions=Counter(r['dimension'] for r in rows)
    reuse_dimensions=Counter(r['dimension'].lower() for r in reuse_slots)
    guarded=read(ARCHIVE/'source-integrity.json')['files']
    for e in guarded: assert sha(ROOT/e['path'])==e['sha256'],e['path']
    mm=[r for r in rows if r['family']=='MM']
    assert len(rows)==300 and Counter(r['recommendation'] for r in rows)=={'retain-core':100,'reorganize':140,'regression-only':60}
    assert all(r['firstTurnPublicExtensions'] in [['.png'],['.dxf']] for r in mm)
    assert len(engineering|dynamics)==111
    return {
        'schemaVersion':1,'status':'editorial-reuse-review-not-v2-acceptance',
        'oldEdition':'section-diversity-v1-final-20261027','oldEvaluationRevision':'r23',
        'reviewMethod':'Local evidence-guided editorial selection; not a new blind input review, model trial or proof of empirical difficulty.',
        'selectionUsesPassFailAlone':False,'reviewerWasBlindToScores':False,
        'cases':rows,
        'summary':{
            'oldCasesReviewed':300,'sourceBindingsVerified':300,'guardedEvaluatorFilesUnchanged':len(guarded),
            'recommendations':dict(Counter(r['recommendation'] for r in rows)),
            'byFamily':{f:dict(Counter(r['recommendation'] for r in rows if r['family']==f)) for f in PRIORITY},
            'actualMMFirstTurnBundles':dict(Counter(r['firstTurnPublicExtensions'][0] for r in mm)),
            'actualMMFirstTurnSvgBundles':0,
            'actualMMBundleEvidence':'Previously verified r23 archive manifest; raw authoring attachments are not the candidate visibility boundary.',
            'oldTurns':sum(r['turns'] for r in rows),'oldINTTurns':sum(r['turns'] for r in rows if r['family']=='INT'),
            'sameGeometrySupportGroups':len(groups),
            'groupingLimit':'Translation/IDs invariant exact geometry plus support/type grouping; not graph isomorphism, scale-invariant topology or the v2 topology gate.',
            'v2EngineeringTargets':len(engineering),'v2DynamicTargets':len(dynamics),
            'engineeringDynamicOverlap':len(engineering&dynamics),'minimumNewSlotsByProvenanceOrAnalysis':111,
            'maximumOldStaticNonEngineeringSlotPool':189,
            'oldDimensions':dict(old_dimensions),
            'v2StaticNonEngineeringSlotDimensions':dict(reuse_dimensions),
            'minimumNew3DPhysicsWithinNominalReuseSlots':max(0,reuse_dimensions['3d']-old_dimensions['3d']),
            'firstPilotExistingCases':PILOT,'newCandidateCalls':0,'newCaseAcceptances':0,
        },
        'sourceFiles':[{ 'path':str(p.relative_to(ROOT)),'sha256':sha(p)} for p in
                       [ARCHIVE/'summary.json',ARCHIVE/'selection.json',ARCHIVE/'archive-manifest.json',
                        ROOT/'planning/releases/research300-catalogue.json',ROOT/'planning/research300-v2/catalogue.json']],
    }


def write(data):
    DEST.mkdir(parents=True,exist_ok=True)
    (DEST/'review.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    fields=['caseId','title','family','oldDifficulty','engine','dimension','nodeCount','memberCount',
            'turns','states','recommendationLabel','oldCodexStatus','firstPilotCandidate','reason']
    stream=io.StringIO(newline=''); w=csv.DictWriter(stream,fieldnames=fields,extrasaction='ignore',lineterminator='\n')
    w.writeheader()
    for r in data['cases']: w.writerow({**r,'reason':'；'.join(r['reason'])})
    (DEST/'review.csv').write_text('\ufeff'+stream.getvalue())
    lines=['# 旧 300 题复用建议逐题表','','这是题核/素材候选池，未映射新版名额，也未通过新版验收。见 [结论与优先顺序](README.md)。','']
    for decision,label in LABELS.items():
        lines.extend([f'## {label}','','| 题号 | 题目 | 引擎 | 原轮数 | 复用/重组要点 |','| --- | --- | --- | ---: | --- |'])
        lines.extend(f"| {r['caseId']} | {r['title']} | {r['engine']} | {r['turns']} | {'；'.join(r['reason'])} |"
                     for r in data['cases'] if r['recommendation']==decision)
        lines.append('')
    (DEST/'review.md').write_text('\n'.join(lines).rstrip()+'\n')
    from openpyxl import Workbook
    from openpyxl.styles import Alignment,Font,PatternFill
    from openpyxl.worksheet.table import Table,TableStyleInfo
    wb=Workbook();info=wb.active;info.title='说明'
    for row in [
        ['内容','旧300题题核/素材的建议；不是新题验收结果'],
        ['优先保留题核',100],['重组复用',140],['回归保留',60],
        ['重要边界','240是候选池，不等于可迁移240；新版至少111项需新编，至多189个旧静力题名额可用'],
        ['实际MM首轮输入','77 PNG / 23 DXF；未向候选提供SVG制图源'],
        ['第一批建议','18个旧题迁移/重组 + 12个新题；还要落实数值、参考与评分'],
        ['注意','旧Codex结果用于归因与诊断，不按通过/失败一项筛选；旧成绩原样保存']]: info.append(row)
    info.column_dimensions['A'].width=28;info.column_dimensions['B'].width=108
    for decision,label in LABELS.items():
        sh=wb.create_sheet({'retain-core':'优先题核','reorganize':'重组复用','regression-only':'回归保留'}[decision])
        sh.append(fields)
        for r in data['cases']:
            if r['recommendation']==decision: sh.append(['；'.join(r[k]) if isinstance(r[k],list) else r[k] for k in fields])
        sh.freeze_panes='C2';sh.auto_filter.ref=sh.dimensions
        table=Table(displayName='Review'+decision.replace('-',''),ref=sh.dimensions)
        table.tableStyleInfo=TableStyleInfo(name='TableStyleMedium2',showRowStripes=True);sh.add_table(table)
        for col in sh.columns: sh.column_dimensions[col[0].column_letter].width=19
        sh.column_dimensions['B'].width=54;sh.column_dimensions['N'].width=110
        for cells in sh.iter_rows(min_row=2):
            for cell in cells: cell.alignment=Alignment(vertical='top',wrap_text=True)
            sh.row_dimensions[cells[0].row].height=58
    for sh in wb:
        for c in sh[1]: c.font=Font(color='FFFFFF',bold=True);c.fill=PatternFill('solid',fgColor='17365D')
    wb.save(DEST/'review.xlsx')


if __name__=='__main__':
    data=build();write(data)
    print(json.dumps(data['summary'],ensure_ascii=False,indent=2))
