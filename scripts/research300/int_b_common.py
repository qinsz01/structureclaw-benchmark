"""INT-B authoring helpers only; explicit case specifications live in batch files.

No numerical truth is produced here. Public inputs are supplied separately so
an unresolved initial input cannot accidentally expose a completed hidden state.
"""
from pathlib import Path
from copy import deepcopy
from commercial.conventions import revise_authored_case
import importlib.util
import json
import math

ROOT = Path(__file__).resolve().parents[2]
SHARED = Path('/mnt/nas/qsz/01research/02structureclaw-bench')
PLAN = {x['id']: x for x in json.loads((ROOT/'planning/capability-coverage-300.json').read_text())['cases']}
SOURCE = ROOT/'planning/sources'
if not SOURCE.exists():
    SOURCE = SHARED/'planning/sources'
TASKS = {x['id']: x for x in json.loads((SOURCE/'all-tasks-engines-v2.json').read_text())}
MODELS = {x['taskId']: x for x in json.loads((SOURCE/'all-models-engines-v2.json').read_text())}
spec = importlib.util.spec_from_file_location('int_b_primitives', ROOT/'scripts/representative-models.py')
P = importlib.util.module_from_spec(spec)
spec.loader.exec_module(P)
model, node, elem, load, section, frame, spatial = P.model, P.node, P.elem, P.load, P.section, P.frame, P.spatial


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


UNITS = dict(coordinates='m', member_length='m', E='MPa', G='MPa', rho='kg/m3',
             A='m2', Iy='m4', Iz='m4', J='m4', shape='mm', force='kN', moment='kN.m',
             line_load='kN/m of actual member length', rotation_angle='degree', displacement='m')
AXES = dict(globalAxes='Right-handed XYZ; Z upward.',
            planarAxes='XZ plane: local x = i to j, local y = global +Y, local z = x cross y.',
            spatialAxes='local x = i to j; y = normalize(reference cross x); z = x cross y; reference vectors are explicit per member.',
            sectionRoll='y_new=cos(theta)*y+sin(theta)*z; z_new=-sin(theta)*y+cos(theta)*z; theta in degrees.',
            reactionNaming='Rz in the task means vertical support force Fz, not nodal rotation rz.')


def public_input(m, **extra):
    """Call before redaction; authors MUST remove unknown values and derivatives."""
    out = deepcopy(m)
    out['units'] = deepcopy(UNITS)
    out['axisDefinitions'] = deepcopy(AXES)
    out['analysisMethod'] = 'First-order linear elastic Euler-Bernoulli beam/column and axial-only truss analysis.'
    out.update(extra)
    return out


def public_tables(content):
    """Present declared inputs as tables, never as a runnable hidden-state file.

    Batch authors redact unresolved data before this presentation step. This
    changes neither numeric data nor release timing and introduces no answers.
    """
    if not isinstance(content,dict): return content
    out=deepcopy(content)
    if not any(k in out for k in ('nodes','elements','materials','sections','load_cases','analysis_control')): return out
    out.pop('schema_version',None)
    out.pop('unit_system',None)  # units are explicitly declared per field
    out['documentType']='Public engineering input tables'
    names={'nodes':'nodeTable','elements':'memberTable','materials':'materialTable','sections':'sectionTable',
           'load_cases':'loadCaseTable','load_combinations':'combinationTable',
           'analysis_control':'analysisSettings','coordinate_system':'coordinateContract','metadata':'memberAxisData'}
    for old,new in names.items():
        if old in out:out[new]=out.pop(old)
    return out


def turn(instruction, state, expectation='analyze', attachments=None, unresolved=None, questions=None, **extra):
    return dict(instruction=instruction, state=state, expectation=expectation,
                attachments=attachments or [], unresolvedFields=unresolved or [], expectedQuestions=questions or [], **extra)


def selections(m):
    return ([dict(kind='case', id=c['id']) for c in m['load_cases']]
            + [dict(kind='combination', id=c['id']) for c in m['load_combinations']])


def quantities(m, top=None, base=None, components=None, selected=None):
    """Explicit selectors may override the usual frame targets, e.g. arm tip."""
    ns=m['nodes']
    if top is None:
        # Beam/column joint, not an overhang endpoint or isolated roof ridge.
        colnodes={n for e in m['elements'] if e['type']=='column' for n in e['nodes']}
        candidates=[n for n in ns if n['id'] in colnodes] or ns
        top=max(candidates,key=lambda n:(n['z'],n['x'],n['y']))['id']
    if base is None:
        base=min(ns,key=lambda n:(n['z'],n['x'],n['y']))['id']
    if components is None:
        components=[(top,'ux'),(top,'uz')]+([(top,'uy')] if m['coordinate_system']['dimension']=='3d' else [])+[(base,'My'),(base,'Fz')]
    out=[]
    for s in (selected if selected is not None else selections(m)):
        for nid,c in components:
            unit='m' if c.startswith('u') else 'rad' if c.startswith('r') else 'kN.m' if c.startswith('M') else 'kN'
            out.append(dict(id=f"{s['kind']}-{s['id']}--{nid}--{c}", selection=deepcopy(s),location=dict(kind='node',id=nid),component=c,unit=unit,tolerance=dict(absolute=1e-8,relative=1e-6)))
    return out


def diff_paths(a,b,p=''):
    if type(a) != type(b): return [p or '/']
    if isinstance(a,dict):
        return [v for k in sorted(set(a)|set(b)) for v in ([p+'/'+k] if k not in a or k not in b else diff_paths(a[k],b[k],p+'/'+k))]
    if isinstance(a,list):
        if len(a)!=len(b): return [p]
        return [v for i,(x,y) in enumerate(zip(a,b)) for v in diff_paths(x,y,p+'/'+str(i))]
    return [] if a==b else [p]


def emit(case_id, states, turns, attachments, notes, requests=None, extra_outputs=None):
    assert 51<=int(case_id[-3:])<=100 and case_id.startswith('INT-')
    row=PLAN[case_id]
    assert len(turns)==TASKS[case_id]['turns'], (case_id, 'source turn count')
    folder=ROOT/'corpora/research-300/cases'/case_id
    folder.mkdir(parents=True,exist_ok=True)
    model_names=[f'model-state-{i}.json' for i in range(1,len(states)+1)]
    for name,m in zip(model_names,states): write_json(folder/name,m)
    for name,content in attachments.items():
        assert not name.startswith(('model-state','reference','independent','contract','author'))
        if isinstance(content,str): (folder/name).write_text(content,encoding='utf-8')
        else: write_json(folder/name,public_tables(content))
    english=row['language']=='英文'
    common_en=('Use the stated '+row['plannedEngine']+' engine for every computable changed state. First-order linear elastic analysis; self-weight, P-delta, rigid diaphragms, rigid offsets and construction stages are off. Preserve all fields not explicitly changed. Report every requested signed value with node/member, global direction, unit, case/combination, turn, model state and traceable run ID. Rz denotes the vertical support reaction Fz. Retain original cases and evaluate every listed combination separately. Resolve essential missing or contradictory inputs before reporting new numerical results.')
    common_zh=('每个可计算的新状态使用题定'+row['plannedEngine']+'引擎进行一阶线弹性分析；自重、P-delta、刚性楼板、刚域及施工阶段关闭。未明确更改的字段保持。每个数值附节点或构件、全局方向、单位、工况或组合、轮次、模型状态与可追溯运行ID。Rz表示竖向支反力Fz。保留原工况并分别计算所有明示组合。关键缺项或矛盾解决前不得编造新数值。')
    current=None
    for i,t in enumerate(turns):
        t['id']=f't{i+1}'
        if i==0: t['instruction']+='\n'+(common_en if english else common_zh)
        assert all(x in attachments for x in t['attachments'])
        if t['expectation']=='analyze' and t['state'] is not None:
            if current is not None:
                changes=diff_paths(states[current-1],states[t['state']-1])
                t.setdefault('changedFields',changes)
                t.setdefault('preservedFields',[f'/{key}' for key in states[current-1] if not any(p==f'/{key}' or p.startswith(f'/{key}/') for p in changes)])
            current=t['state']
    reqs=requests or [dict(state=i,model=name,quantities=quantities(m),derived=[]) for i,(name,m) in enumerate(zip(model_names,states),1)]
    write_json(folder/'reference-requests.json',dict(schemaVersion=1,states=reqs))
    outputs=[]
    for r in reqs:
        for q in r['quantities']:
            outputs.append(dict(id=f"s{r['state']}--{q['id']}",description=f"{q['selection']['kind']} {q['selection']['id']}: {q['location']['id']} {q['component']} [{q['unit']}]",state=r['state'],quantityIds=[q['id']],kind='numerical'))
        for d in r.get('derived',[]): outputs.append(dict(id=f"s{r['state']}--{d['id']}",description=d['description'],state=r['state'],quantityIds=[d['id']],kind='derived'))
    for t in turns:
        outputs.append(dict(id=t['id']+'-interaction',description=t['instruction'],state=t['state'],quantityIds=[],kind='interaction',turnIds=[t['id']]))
    outputs.extend(extra_outputs or [])
    for o in outputs:
        if 'turnIds' in o: continue
        rows=[q for r in reqs if r['state']==o['state'] for q in r['quantities'] if q['id'] in o['quantityIds']]
        o['turnIds']=[t['id'] for t in turns if t['state']==o['state'] and t['expectation']!='clarify'
                      and all(t.get('outputUnits',{}).get(q['component'],q['unit'])==q['unit'] for q in rows)]
    # Preserve the fixed requiredOutputs record shape. Turn records allow
    # additional explicit bindings, necessary when queries change only units.
    for t in turns:
        bound=[o for o in outputs if t['id'] in o['turnIds']]
        t['requiredOutputIds']=[o['id'] for o in bound]
        t['requiredQuantityIds']=list(dict.fromkeys(qid for o in bound for qid in o['quantityIds']))
    for o in outputs: o.pop('turnIds')
    gates=[dict(id=k,status='pending',description=v) for k,v in {
        'native-execution':'Execute the named engine independently for each changed computable state and each selection; retain software version, settings, native input, run ID, successful log and raw result mapping.',
        'independent-reference':'Generate and independently review same-engine reference values; check equilibrium, signs, units and stiffness without importing the SUT path.',
        'input-blind-review':'Independently reconstruct each turn from only its released public input and verify original source requirements.',
        'state-preservation':'Verify target field changes, all non-target fields, undo equivalence and query-only state identity.',
        'adapter-capability-review':'Exercise this case topology, loads, coordinates and selected engine; support in principle is not evidence of adapter acceptance.',
        'report-completeness':'Check signed quantities in the report body, locations, directions, units, selections and current turn against structured artifacts.'}.items()]
    coverage=[]
    for field in row['sourceRequirements']:
        ids=[r['id'] for r in row['requirements'] if r['sourceField']==field]
        if field=='engine.executionRequirement': targets=['gate:native-execution']
        elif field=='engine.truthPlan': targets=['gate:independent-reference']
        elif field in ('engine.adapterGap','task.prerequisite'): targets=['gate:adapter-capability-review']
        elif field=='engine.requiredEvidence': targets=['gate:native-execution','gate:state-preservation','gate:report-completeness']
        elif field=='task.expectedOutput': targets=[f"output:{o['id']}" for o in outputs]+['gate:report-completeness']
        elif field in ('task.scenario','task.gradingFocus','task.modelingFocus'): targets=[f"turn:{t['id']}" for t in turns]+['gate:state-preservation','gate:input-blind-review']
        else: targets=[f"turn:{t['id']}" for t in turns]+['attachment:'+a for a in attachments]+['gate:input-blind-review']
        coverage.append(dict(sourceField=field,requirementIds=ids,targets=targets,notes='Authored evidence mapping only; executable gates remain pending. See author-notes.json for case-specific source review and appendix choices.'))
    contract=dict(schemaVersion=1,evaluationProfile='engineering-v2.3',id=case_id,modelId=row['modelId'],family=row['family'],language=row['language'],locale='en' if english else 'zh',plannedEngine=row['plannedEngine'],sourcePlan=deepcopy(row['sourceRequirements']),modelStates=model_names,attachments=list(attachments),turns=turns,requiredOutputs=outputs,requirementCoverage=coverage,acceptanceGates=gates,status='authored-candidate',sameEngineTruthStatus='pending',inputBlindReview='pending',llmEndToEnd='not-run')
    write_json(folder/'contract.json',contract)
    (folder/'prompt.txt').write_text(turns[0]['instruction']+'\n',encoding='utf-8')
    write_json(folder/'author-notes.json',dict(sourceTask=TASKS[case_id],sourceModel=MODELS[case_id],authorReview=notes,validationStatus='Structural checks only; independent input review, numerical reference and native execution remain pending.'))
    revise_authored_case(folder)
    return folder
