"""Fresh authoring of 300 tasks; candidate outcomes never enter this process."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import argparse
from collections import Counter
from copy import deepcopy
import csv
import hashlib
import io
import json
from pathlib import Path
import shutil

from .support import ROOT,V2,legacy_tasks,legacy_refs,load
from .documents import write,write_public
from .projects import reference as project_reference
from .mechanics import revised_project_rules
from .analyses import area_rules,revised_rules,static_reference,dynamic_reference

SUT='db3c0b1da44fe668a6037a6c2e7f068d14354539'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def revision(base,case,ordinal,project=False):
    rules=deepcopy(base)
    if ordinal in [2,3]:rules=(revised_project_rules(base,case['seed']) if project else revised_rules(case['model'],base,case['seed']))
    if ordinal in [3,4]:
        xmin=min(z['startX'] for z in base['zones']);xmax=max(z['endX'] for z in base['zones'])
        rules['addedEquipment']={'weightKN':round(15+case['seed']%13,3),**({'upperJoint':'U1-2'} if project else {'positionX':round(xmin+.67*(xmax-xmin),8)}),'case':'D'}
    if ordinal==1:return rules,'依据首轮完整工程资料建立物理模型、转换荷载并完成 task.json 的全部设计/分析要求。'
    if ordinal==2:
        r=rules['liveRevision']
        return rules,f"调整使用分区：仅 Q 改为 X={r['splitX']:.12g} m 分界，西/东面压比 {r['westEastPressureRatio']:.12g}，总活荷载仍为 {r['totalLiveKN']:.12g} kN。根据受荷几何重新分配，不提供接收节点或构件荷载。原 D、W、自重和所有结构输入保留。"
    equipment=rules['addedEquipment']
    location='上部分配梁中跨的中间节点 U1-2' if project else f"屋面离 X={equipment['positionX']:.12g} m 最近的节点（相同距离取 Z 最高，再取 |Y| 最小）"
    if ordinal==3:return rules,f"在{location}增加设备恒载 {equipment['weightKN']:.12g} kN，沿全局 -Z，仅计入 D。保留上一轮 Q 重分布，其他已签发输入不变。"
    return rules,'仅撤销第2轮的 Q 分区调整，将 Q 恢复为第1轮的面压分区；保留第3轮设备恒载以及其他未撤销输入，重新计算当前状态。'

def high_turns(case):
    project=case['analysis']=='project'
    base=json.loads(Path(case['projectCache']).read_text()) if project else None
    rules=base['loadRules'] if project else area_rules(case['model'],case['seed'])
    for ordinal in range(1,case['rounds']+1):
        current,instruction=revision(rules,case,ordinal,project)
        if project:
            ref=base if ordinal==1 else project_reference(case['model'],case['seed'],load_rules=current,fixed_constraints=base['constraints'],integration=base['integration'])
        elif case['analysis'] in ['modal','transient']:
            ref=dynamic_reference(case['model'],current,case['analysis'],case['seed'])
            instruction+=' 由本轮 D 与规定比例 Q 重新推导参与 X 向质量；即使总活荷载不变也不能沿用原质量分布。'
        else:
            scenarios=[{'id':'current',**static_reference(case['model'],current)}]
            if case['family']!='INT':
                scenarios=[{'id':'baseline',**static_reference(case['model'],rules)},
                           {'id':'relocated',**static_reference(case['model'],revised_rules(case['model'],rules,case['seed']))}]
                instruction+=' 比较 baseline 和 relocated 两种使用分区的全局控制指标及其相对变化；总 Q 不变，需重算分配和控制位置。'
            ref={'kind':'analysis','engine':'OpenSees','scenarios':scenarios,'tolerance':{'relative':1e-6,'displacementAbsolute':1e-8,'forceAbsolute':1e-6}}
        yield ordinal,ref,instruction

def build(output,assignment):
    if output.exists():raise FileExistsError('A new edition directory is required')
    output.mkdir(parents=True)
    payload=json.loads(assignment.read_text());rows=payload.get('cases',payload.get('rows')) if isinstance(payload,dict) else payload
    old_public=load('v3_frozen_public',V2/'public.py');items=[]
    assert len(rows)==300
    for i,case in enumerate(rows,1):
        item={k:deepcopy(v) for k,v in case.items() if k not in ['model','states','sourceBasis','loadRecipe','schemes','constraint','projectCache']}
        item['inputMode']='engineering-grid-raster' if case['family']=='MM' and case['level'] in ['L3','L4'] else 'construction-documents' if case['level'] in ['L3','L4'] else 'png' if case['family']=='MM' else 'tables'
        item['turns']=[]
        if case['level'] in ['L1','L2']:
            turns=[(n,legacy_refs.reference(t),t) for n,t in enumerate(legacy_tasks.make_turns(case),1)]
        else:turns=high_turns(case)
        for ordinal,ref,source in turns:
            folder=output/'cases'/case['id'];pub=folder/'public'/f't{ordinal}';private=folder/'private'/f't{ordinal}.json'
            if case['level'] in ['L1','L2']:
                old_public.write_public(pub,{**case,'inputMode':'png' if case['family']=='MM' else 'tables'},source,ordinal,ref)
            else:write_public(pub,case,ref,ordinal,source)
            write(private,ref)
            item['turns'].append({'id':f't{ordinal}','public':pub.relative_to(output).as_posix(),'private':private.relative_to(output).as_posix()})
            if ordinal==1:
                item['difficultyEvidence']=ref.get('difficultyEvidence',{'constructionReconstruction':case['level']=='L3','scenarioCount':len(ref.get('scenarios',[])),'gravityDerivedMass':case['analysis'] in ['modal','transient']})
        if case['origin']=='legacy-commercial':
            src=legacy_tasks.OLD/case['legacyId'];contract=json.loads((src/'contract.json').read_text())
            for name in ['contract.json','independent-reference.json',*contract['modelStates']]:
                dest=output/'legacy-source'/case['legacyId']/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src/name,dest)
        items.append(item);print(json.dumps({'authored':i,'id':case['id'],'level':case['level'],'integration':case.get('integration'),'turns':len(item['turns'])}),flush=True)
    summary={'cases':300,'turns':sum(len(c['turns']) for c in items),
             **{key:dict(Counter(c.get(key) for c in items)) for key in ['level','family','engine','analysis','origin','split','inputMode']},
             'projectIntegration':dict(Counter(c['integration'] for c in items if c['level']=='L4')),
             'uniqueTopologyFingerprints':len({c['topologyFingerprint'] for c in items}),
             'sourceProjects':len({c['sourceId'] for c in items if c.get('sourceId')}),'candidateRunsAtAuthoring':0}
    assert summary['turns']==560,summary
    write(output/'catalogue.json',{'schemaVersion':3,'summary':summary,'cases':items})
    buffer=io.StringIO();w=csv.writer(buffer,lineterminator='\n');keys=['id','family','level','engine','analysis','integration','origin','sourceProjectGroup','baseModelGroup','split','inputMode','title'];w.writerow(keys+['turns'])
    for c in items:w.writerow([c.get(k,'') for k in keys]+[len(c['turns'])])
    write(output/'catalogue.csv',buffer.getvalue())
    lines=['# Research300 v3：工程建模与综合决策版','','300题，560轮；难度分布30/60/120/90。难度为设计标签，实际候选表现另行校准。真实文献/工程事实与作者补充模型分开签发。','',
           '| 题目 | 类别 | 分析 | 连接 | 来源 | 分组 |','| --- | --- | --- | --- | --- | --- |']
    for c in items:lines.append(f"| [{c['id']}]({c['turns'][0]['public']}/task.json) {c['title']} | {c['family']}/{c['level']} | {c['analysis']} | {c.get('integration','')} | {c.get('sourceId',c['origin'])} | {c['split']} |")
    write(output/'catalogue.md','\n'.join(lines)+'\n')
    shutil.copyfile(V2/'source_registry.json',output/'source_registry.json')
    write(output/'authoring-selection.json',{'assignmentSha256':sha(assignment),'rejectedProjectCandidates':payload.get('rejected',[]) if isinstance(payload,dict) else [],'selectionPolicy':'Fixed before any v3 candidate run; all failed attempts retained in authoring work directory.'})
    write(output/'manifest.json',{'schemaVersion':3,'edition':'research300-v3-v1','status':'authored-pending-native-input-and-candidate-qualification','sutCommit':SUT,'summary':summary,'cases':items,'files':[{'path':p.relative_to(output).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(output.rglob('*')) if p.is_file()]})
    return summary

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--assignment',type=Path,required=True);a=p.parse_args();print(json.dumps(build(a.output.resolve(),a.assignment.resolve()),ensure_ascii=False))
