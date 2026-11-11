"""INT-A authoring utilities; no production or oracle imports and no answer values."""
from pathlib import Path
from copy import deepcopy
from collections import defaultdict
import importlib.util,json,math
ROOT=Path(__file__).resolve().parents[2]
SHARED=Path('/mnt/nas/qsz/01research/02structureclaw-bench')
spec=importlib.util.spec_from_file_location('representative_primitives',ROOT/'scripts/representative-models.py')
pr=importlib.util.module_from_spec(spec);spec.loader.exec_module(pr)
model,node,elem,load,section=pr.model,pr.node,pr.elem,pr.load,pr.section
PIN=[True,True,True,True,False,True]
ROLLER=[False,True,True,True,False,True]
FIXED=[True]*6
FREE=[False,True,False,True,False,True]

def sources(case_id):
    coverage=next(x for x in json.loads((ROOT/'planning/capability-coverage-300.json').read_text())['cases'] if x['id']==case_id)
    source_dir=ROOT/'planning/sources'
    if not source_dir.exists(): source_dir=SHARED/'planning/sources'
    task=next(x for x in json.loads((source_dir/'all-tasks-engines-v2.json').read_text()) if x['id']==case_id)
    source_model=next(x for x in json.loads((source_dir/'all-models-engines-v2.json').read_text()) if x['taskId']==case_id)
    return coverage,task,source_model

def quantity(node_id,component,selection='D',kind='case',unit=None):
    if unit is None: unit='m' if component in ('ux','uy','uz') else 'rad' if component in ('rx','ry','rz') else 'kN*m' if component.startswith('M') else 'kN'
    return dict(id=f'{kind}:{selection}:node:{node_id}:{component}',selection=dict(kind=kind,id=selection),location=dict(kind='node',id=node_id),component=component,unit=unit,tolerance=dict(absolute=1e-8,relative=1e-6))

def member_quantity(member_id,component,position=0,side='right',selection='D',kind='case',unit=None):
    q=quantity(member_id,component,selection,kind,unit)
    q['id']=f'{kind}:{selection}:member:{member_id}:{position:g}:{side}:{component}'
    q['location']=dict(kind='member',id=member_id,positionM=position,side=side)
    return q

def turn(instruction,state,expectation='analyze',attachments=None,unresolved=None,questions=None,**extra):
    return dict(instruction=instruction,state=state,expectation=expectation,attachments=attachments or [],unresolvedFields=unresolved or [],expectedQuestions=questions or [],**extra)

def tables(m,locale='en',extra=''):
    # Caller must remove/redact ALL withheld fields before calling this renderer.
    en=locale=='en'
    header=('Input tables. X horizontal, Z upward; Y completes the right-handed system. '
      'Section shape dimensions B,H are mm; listed section properties are authoritative. Coordinates m; nodal forces kN; nodal moments kN*m; line loads kN/m; E,G MPa; A m2; Iy,Iz,J m4; density kg/m3. '
      'Restraints ordered ux,uy,uz,rx,ry,rz; true=fixed. Member local x follows the ordered end nodes. '
      'For planar XZ members local y is global +Y and local z=x cross y; bending about local y uses Iy. '
      'For spatial members the explicit reference vector defines local z by its projection normal to local x, local y=z cross x. '
      'Linear elastic first-order static analysis, self-weight OFF, no automatic loads/combinations, diaphragm, rigid offsets or P-delta. '
      'Distributed load intervals are measured in m along the actual member unless this turn explicitly leaves that basis unresolved. '
      'All omitted load components are zero. Beam-column joints are rigid unless explicitly restrained; truss elements are axial-only. '
      'Truss rotational restraints eliminate inactive bookkeeping DOFs and do not add rotational stiffness. Use OpenSees for every calculable state; rerun after a physical edit, and reuse a result for a pure query only when its state is unchanged. Retain solver version/settings, run ID, successful log, model snapshot and raw result mapping.\n') if en else (
      '输入表。截面shape的B、H尺寸为mm，截面properties数值为输入依据。全局X水平、Z向上，Y补成右手系。坐标m；节点力kN；节点力矩kN*m；线载kN/m；E、G为MPa；A为m2；Iy、Iz、J为m4；密度kg/m3。'
      '约束顺序ux,uy,uz,rx,ry,rz；true表示固定。构件局部x沿起点到终点。平面XZ构件局部y为全局+Y，局部z=x叉乘y，绕局部y弯曲采用Iy。'
      '空间杆局部z取明示参考向量在垂直局部x平面的投影，局部y=z叉乘x。'
      '一阶线弹性静力，自重关闭；不自动添加荷载、组合、楼板、刚域或二阶效应。分布载荷区间按实际杆长以m计，除非本轮明确待确认该基准。'
      '未列荷载分量为零。梁柱共节点刚接；桁架仅轴向受力，转动约束只消除未激活自由度。每个可计算状态使用OpenSees；物理修改后重新计算，纯查询仅在状态未变时复用可追溯结果。保存软件版本/设置、运行ID、成功日志、模型快照和原始结果映射。\n')
    return header+extra+'\n'+json.dumps(m,ensure_ascii=False,indent=2)+'\n'

def finalize(m):
    # Axes are explicit for all elements, including planar members.
    m=deepcopy(m);ns={n['id']:n for n in m['nodes']}
    refs=m.setdefault('metadata',{}).setdefault('elementReferenceVectors',{})
    for e in m['elements']:
        a,b=(ns[i] for i in e['nodes']);v=[b[k]-a[k] for k in ('x','y','z')]
        if m['coordinate_system']['dimension']=='2d':refs[e['id']]=[-v[2],0,v[0]]
        elif e['id'] not in refs:refs[e['id']]=[1,0,0] if abs(v[0])+abs(v[1])<1e-12 else [0,0,1]
    return m

def write_case(case_id,states,turns,requests,public_files,decisions=None,outputs=None,derived=None,source_audit=None,reported_quantities=None,output_turns=None):
    coverage,task,sm=sources(case_id)
    assert len(turns)==task['turns'],(case_id,len(turns),task['turns'])
    assert len(states)==len(requests)
    derived=derived or [[] for _ in states]
    out=ROOT/'corpora/research-300/cases'/case_id;out.mkdir(parents=True,exist_ok=True)
    def write(name,value):
        path=out/name;path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(value if isinstance(value,str) else json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    filenames=[]
    for i,m in enumerate(states,1):
        filenames.append(f'model-state-{i}.json');write(filenames[-1],finalize(m))
    for name,value in public_files.items():write(name,value)
    for i,t in enumerate(turns,1): t['id']=f't{i}'
    write('prompt.txt',turns[0]['instruction']+'\n')
    outputs=deepcopy(outputs or [])
    resolved_turns={i:[t['id'] for t in turns if t['state']==i and t['expectation']!='clarify'] for i in range(1,len(states)+1)}
    for output in outputs:
        output.setdefault('turnIds',resolved_turns[output['state']])
    for i,qq in enumerate(requests,1):
        for q in qq:
            if reported_quantities is not None and q['id'] not in reported_quantities[i-1]:continue
            # Explicit report groups can narrow a query without changing its model.
            scoped=[o for o in outputs if o['state']==i and q['id'] in o['quantityIds']]
            turn_ids=[t for t in resolved_turns[i] if any(t in o['turnIds'] for o in scoped)] if scoped else resolved_turns[i]
            outputs.append(dict(id=f's{i}:{q["id"]}',description=f'{q["selection"]["kind"]} {q["selection"]["id"]}: {q["location"]}; {q["component"]} [{q["unit"]}], signed',state=i,quantityIds=[q['id']],kind='numerical',turnIds=turn_ids))
        for d in derived[i-1]:outputs.append(dict(id=f's{i}:{d["id"]}',description=d['description'],state=i,quantityIds=[d['id']],kind='derived',turnIds=resolved_turns[i]))
    for t in turns:
        outputs.append(dict(id=f'{t["id"]}:interaction',description=t['instruction'],state=t['state'],quantityIds=[],kind='interaction',turnIds=[t['id']]))
    for output_id,turn_ids in (output_turns or {}).items():
        matches=[o for o in outputs if o['id']==output_id]
        assert len(matches)==1,(case_id,output_id)
        matches[0]['turnIds']=turn_ids
    gates=[dict(id='native-execution',status='pending',description='Fresh successful planned-engine execution for every changed state; version/settings/run ID/raw mapping required.'),dict(id='independent-reference',status='pending',description='Independently authored same-engine truth plus equilibrium and independent numerical review.'),dict(id='input-blind-review',status='pending',description='Blind recovery of each visible input without hidden state or future-turn input.'),dict(id='state-diff',status='pending',description='Only explicitly authorized fields change; undo and query semantics checked against snapshots.')]
    grouped=defaultdict(list)
    for r in coverage['requirements']:grouped[r['sourceField']].append(r['id'])
    rc=[]
    for field,ids in grouped.items():
        if field in ('engine.executionRequirement','engine.requiredEvidence'):targets=['gate:native-execution','gate:state-diff']
        elif field in ('engine.truthPlan','engine.adapterGap','task.prerequisite'):targets=['gate:independent-reference','gate:input-blind-review']
        elif field=='task.expectedOutput':targets=[f'output:{o["id"]}' for o in outputs]
        elif field in ('task.scenario','task.inputForm','task.gradingFocus'):targets=[f'turn:{t["id"]}' for t in turns]+['gate:state-diff']
        else:targets=[f'attachment:{name}' for name in public_files]+[f'turn:{t["id"]}' for t in turns]+['gate:input-blind-review']
        rc.append(dict(sourceField=field,requirementIds=ids,targets=targets,notes='Authored mapping only; execution, numerical truth and blind input acceptance remain pending.'))
    c=dict(schemaVersion=1,evaluationProfile='engineering-v2.3',id=case_id,modelId=coverage['modelId'],family=coverage['family'],language=coverage['language'],locale='en' if coverage['language']=='英文' else 'zh',plannedEngine=coverage['plannedEngine'],sourcePlan=coverage['sourceRequirements'],sourceMetadata=dict(requirements=coverage['requirements'],task=task,model=sm),modelStates=filenames,attachments=list(public_files),turns=turns,requiredOutputs=outputs,requirementCoverage=rc,acceptanceGates=gates,status='authored-candidate',sameEngineTruthStatus='pending',inputBlindReview='pending',llmEndToEnd='not-run',authorDecisions=decisions or [])
    write('contract.json',c)
    write('reference-requests.json',dict(schemaVersion=1,states=[dict(state=i,model=filenames[i-1],quantities=qq,derived=derived[i-1]) for i,qq in enumerate(requests,1)]))
    write('author-review.json',dict(caseId=case_id,sourceRowsRead=True,sourceAudit=source_audit or [],decisions=decisions or [],status='author-checked; independent input blind review pending',native='pending',llm='not-run'))
    return c
