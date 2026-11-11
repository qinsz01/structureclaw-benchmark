"""Reproducible authoring utilities owned exclusively by the STD-A shard.

This module writes inputs and requests, never reference values or acceptance claims.
Run individual std_a_NNN_NNN.py scripts from any working directory.
"""
from copy import deepcopy
import csv
import importlib.util
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / 'corpora/research-300/cases'
PLAN = {r['id']: r for r in json.loads((ROOT / 'planning/capability-coverage-300.json').read_text())['cases']}
spec = importlib.util.spec_from_file_location('std_a_primitives', ROOT / 'scripts/representative-models.py')
primitives = importlib.util.module_from_spec(spec)
spec.loader.exec_module(primitives)
TOL = {'absolute': 1e-8, 'relative': 1e-6}


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def length(model, member):
    e = next(e for e in model['elements'] if e['id'] == member)
    ns = {n['id']: n for n in model['nodes']}
    return math.dist([ns[e['nodes'][0]][k] for k in ('x','y','z')], [ns[e['nodes'][1]][k] for k in ('x','y','z')])


def quantity(location, component, selection=None, unit=None):
    selection = selection or {'kind': 'case', 'id': 'D'}
    if unit is None:
        unit = 'm' if component.startswith('u') else 'rad' if component.startswith('r') else 'kN.m' if component[0] in 'MT' else 'kN'
    suffix = f"@{location['positionM']:.12g}:{location['side']}" if location['kind'] == 'member' else ''
    return dict(id=f"{selection['kind']}:{selection['id']}:{location['kind']}:{location['id']}:{component}{suffix}", selection=deepcopy(selection), location=location, component=component, unit=unit, tolerance=deepcopy(TOL))


def qnode(model, node, component, selection=None, unit=None):
    assert node in {n['id'] for n in model['nodes']}, node
    return quantity(dict(kind='node', id=node), component, selection, unit)


def qmember(model, member, positionM, component, selection=None, side='right', unit=None):
    assert -1e-10 <= positionM <= length(model, member) + 1e-10, (member, positionM)
    return quantity(dict(kind='member', id=member, positionM=positionM, side=side), component, selection, unit)


def emit(case_number, model, prompt, quantities, derived=None, extra_outputs=None, notes=None, mixed_units=False):
    case_id = f'STD-{case_number:03d}'
    assert 1 <= case_number <= 50
    row = PLAN[case_id]
    en = row['language'] == '英文'
    folder = DEST / case_id
    folder.mkdir(parents=True, exist_ok=True)
    model = deepcopy(model)
    # Unused appendix groups must not obscure the actual assignments.
    model['sections'] = [s for s in model['sections'] if s['id'] in {e['section'] for e in model['elements']}]
    model['materials'] = [s for s in model['materials'] if s['id'] in {e['material'] for e in model['elements']}]
    derived = derived or []
    ids = [q['id'] for q in quantities] + [d['id'] for d in derived]
    assert len(ids) == len(set(ids)), (case_id, 'duplicate quantities')
    write_json(folder / 'model-state-1.json', model)
    write_json(folder / 'reference-requests.json', dict(schemaVersion=1, states=[dict(state=1, model='model-state-1.json', quantities=quantities, derived=derived)]))
    geometry = dict(units='mm' if mixed_units else 'm', nodes=deepcopy(model['nodes']), elements=deepcopy(model['elements']))
    properties = dict(units=dict(E='MPa',G='MPa',rho='kg/m3',shape='mm',A='mm2' if mixed_units else 'm2',Iy='mm4' if mixed_units else 'm4',Iz='mm4' if mixed_units else 'm4',J='mm4' if mixed_units else 'm4'),coordinate_system=model['coordinate_system'],materials=deepcopy(model['materials']),sections=deepcopy(model['sections']),analysis_control=model['analysis_control'],load_combinations=model['load_combinations'],localAxes=model.get('metadata',{}),analysis='first-order linear elastic Euler-Bernoulli frame and axial-only truss',restraintConvention='[ux,uy,uz,rx,ry,rz]; true = zero prescribed displacement; false = free active DOF; planar inactive DOFs and truss rotations are explicitly suppressed',sectionRollConvention='ey_new=cos(theta)*ey+sin(theta)*ez; ez_new=-sin(theta)*ey+cos(theta)*ez; theta in degrees about i-to-j')
    load_data = dict(units=dict(force='N' if mixed_units else 'kN',moment='N.mm' if mixed_units else 'kN.m',lineLoad='N/mm' if mixed_units else 'kN/m',position='mm' if mixed_units else 'm'),load_cases=deepcopy(model['load_cases']),load_combinations=model['load_combinations'],distributedLoadMeasure='per actual member length, global vector; start/end in metres from i unless units above specify mm')
    if mixed_units:
        for n in geometry['nodes']:
            for k in ('x','y','z'): n[k] *= 1000
        for s in properties['sections']:
            for k in ('A','Iy','Iz','J'): s['properties'][k] *= 1e6 if k == 'A' else 1e12
        for c in load_data['load_cases']:
            for l in c['loads']:
                for k in ('fx','fy','fz'):
                    if k in l: l[k] *= 1000
                for k in ('mx','my','mz'):
                    if k in l: l[k] *= 1e6
                for k in ('start','end','position'):
                    if k in l: l[k] *= 1000
    write_json(folder / 'geometry.json', geometry)
    write_json(folder / 'properties.json', properties)
    write_json(folder / 'loads.json', load_data)
    public_requests = [{k: deepcopy(q[k]) for k in ('id','selection','location','component','unit')} for q in quantities]
    write_json(folder / 'output-requests.json', dict(quantities=public_requests,derived=derived))
    attachments = ['geometry.json', 'properties.json', 'loads.json', 'output-requests.json']
    convention_en = ('Use the complete attached input tables. Global XYZ is right handed with Z upward; any planar model uses the XZ plane. All nodes listed are connected physical joints. Member local x points from i to j. In 2D local y=global +Y and local z=x cross y. In 3D local y=normalize(reference cross x), local z=x cross y; reference vectors are explicit. N is positive in tension. Signed section N/T/M2/M3 equal minus the i-end resisting action at the start and plus the j-end action at the end; V2/V3 use plus i-end and minus j-end action. Report global nodal displacements and support reactions; rotations follow the right-hand rule. Distributed loads act per actual member length, including inclined members. Use first-order linear elasticity with self-weight, rigid floors, rigid offsets, P-delta and construction stages off. Use only the specified cases and combinations. Compute every request in output-requests.json, retaining its location, side, signed component, unit and case/combination. Interior forces must include applied-load terms. Execute OpenSees and retain version, runnable input, current-model hash, run ID, actual solver log and raw result/case mapping. Report the requested results in the response body as well as structured results; independently check equilibrium. No numerical answer or native execution evidence is supplied.')
    convention_zh = ('完整输入见附件。全局XYZ为右手系，Z向上；平面结构位于XZ面。表列节点均为实际连通节点。构件局部x由i端指向j端；二维局部y为全局+Y，局部z=x×y；三维局部y=归一化(reference×x)，局部z=x×y，参考向量逐杆给出。N拉为正；截面N/T/M2/M3在i端取节点抵抗力的负值，在j端取正值；V2/V3在i端取正值、j端取负值。节点位移和支反力按全局分量，转角服从右手定则。线载按构件实际长度计，斜杆亦然。一阶线弹性，自重、刚性楼板、刚域、二阶和施工阶段关闭；仅使用题定工况及组合。逐项完成output-requests.json中所有请求，保留位置、截面侧别、正负号、分量、单位、工况/组合。跨内内力恢复须计入荷载项。实际运行OpenSees，保留版本、可运行输入、当前模型哈希、运行ID、实际求解日志及原始结果/工况对应关系。正文和结构化结果均须给出题定结果，并独立检查平衡。附件不提供数值答案或原生执行证据。')
    final_prompt = prompt.strip() + '\n\n' + (convention_en if en else convention_zh)
    (folder / 'prompt.txt').write_text(final_prompt + '\n', encoding='utf-8')
    outputs = [dict(id=f'output-{i+1:03d}', description=(f"Report {q['id']} in {q['unit']}" if en else f"报告 {q['id']}，单位 {q['unit']}"), state=1, quantityIds=[q['id']], kind='numerical') for i,q in enumerate(quantities)]
    outputs += [dict(id=f"output-derived-{d['id']}", description=d['description'], state=1, quantityIds=[d['id']], kind='derived') for d in derived]
    for i, item in enumerate(extra_outputs or []):
        kind = item.get('kind','interaction')
        outputs.append(dict(id=item.get('id',f'output-extra-{i+1}'),description=item['description'],state=1,quantityIds=[] if kind == 'interaction' else item.get('quantityIds',[]),kind=kind))
    for output in outputs:
        output['turnIds'] = ['t1']
    gates = [dict(id=g,status='pending') for g in ('physical-model-review','input-blind-review','native-execution-every-selection','independent-same-engine-truth','all-requested-output-scoring','report-body-consistency','adapter-capability-acceptance')]
    coverage = []
    target_map = {
        'task.inputForm': attachments,
        'task.scenario': ['turns:t1','geometry.json','loads.json','properties.json'],
        'task.modelingFocus': ['geometry.json','loads.json','gate:physical-model-review'],
        'task.expectedOutput': ['output-requests.json'] + [f"requiredOutputs:{o['id']}" for o in outputs],
        'task.gradingFocus': ['output-requests.json','gate:all-requested-output-scoring','gate:report-body-consistency'],
        'task.prerequisite': ['properties.json','gate:input-blind-review','gate:adapter-capability-acceptance'],
        'model.topologyKey': ['geometry.json','gate:physical-model-review'],
        'model.boundaryKey': ['geometry.json','gate:physical-model-review'],
        'model.loadKey': ['loads.json','gate:physical-model-review'],
        'model.propertyKey': ['properties.json','geometry.json'],
        'engine.analysisContract': ['turns:t1','properties.json','loads.json','output-requests.json'],
        'engine.executionRequirement': ['turns:t1','gate:native-execution-every-selection'],
        'engine.requiredEvidence': ['turns:t1','gate:native-execution-every-selection','gate:independent-same-engine-truth'],
        'engine.adapterGap': ['gate:adapter-capability-acceptance'],
        'engine.truthPlan': ['reference-requests.json','gate:independent-same-engine-truth','gate:all-requested-output-scoring'],
    }
    for field in row['sourceRequirements']:
        coverage.append(dict(sourceField=field,requirementIds=[r['id'] for r in row['requirements'] if r['sourceField']==field],targets=target_map[field],notes='Mapping identifies authored evidence and pending acceptance gates; mapping alone does not validate execution, fidelity, output scoring or independent review.'))
    contract = dict(schemaVersion=1,evaluationProfile='engineering-v2.3',id=case_id,modelId=row['modelId'],family=row['family'],language=row['language'],locale='en' if en else 'zh',plannedEngine=row['plannedEngine'],sourcePlan=row['sourceRequirements'],modelStates=['model-state-1.json'],attachments=attachments,turns=[dict(id='t1',instruction=final_prompt,state=1,expectation='analyze',attachments=attachments,unresolvedFields=[],expectedQuestions=[])],requiredOutputs=outputs,requirementCoverage=coverage,acceptanceGates=gates,status='authored-candidate',sameEngineTruthStatus='pending',inputBlindReview='pending',llmEndToEnd='not-run')
    write_json(folder / 'contract.json', contract)
    write_json(folder / 'authoring-decisions.json', dict(schemaVersion=1,case=case_id,notes=notes or [],appendixPolicy='Numerical properties and any missing source connection table are explicit author decisions. They are inputs, not solver defaults or validated answers.',tolerancePolicy='Absolute 1e-8 plus relative 1e-6 in each declared output unit, frozen before candidate runs.',sourceReview='Author source comparison recorded separately; independent input-blind review pending.',referenceStatus='Requests only; no reference values authored.'))
    return folder
