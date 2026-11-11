"""Reproducible STD-051..100 authoring helpers; no solver or reference values."""
from pathlib import Path
import importlib.util
import json
import math
from copy import deepcopy
from commercial.conventions import revise_authored_case

ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = ROOT / 'planning' / 'sources'
if not SOURCE_ROOT.exists():
    SOURCE_ROOT = Path('/mnt/nas/qsz/01research/02structureclaw-bench/planning/sources')
spec = importlib.util.spec_from_file_location('representative_primitives', ROOT/'scripts/representative-models.py')
rep = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rep)
model, node, elem, load, section = rep.model, rep.node, rep.elem, rep.load, rep.section
frame, spatial, beams_udl = rep.frame, rep.spatial, rep.beams_udl

def source(number):
    cid = f'STD-{number:03d}'
    row = next(r for r in json.loads((ROOT/'planning/capability-coverage-300.json').read_text())['cases'] if r['id']==cid)
    task = next(r for r in json.loads((SOURCE_ROOT/'all-tasks-engines-v2.json').read_text()) if r['id']==cid)
    original_model = next(r for r in json.loads((SOURCE_ROOT/'all-models-engines-v2.json').read_text()) if r['taskId']==cid)
    return row, task, original_model

def length(m, eid):
    e = next(e for e in m['elements'] if e['id']==eid)
    n = {n['id']:n for n in m['nodes']}
    return math.dist([n[e['nodes'][0]][k] for k in 'xyz'], [n[e['nodes'][1]][k] for k in 'xyz'])

class Requests:
    def __init__(self, m):
        self.model = m
        self.quantities = []
        self.derived = []
    def add(self, selection, location, component, unit=None):
        if isinstance(selection, str):
            selection={'kind':'combination' if any(c['id']==selection for c in self.model['load_combinations']) else 'case','id':selection}
        unit = unit or ('m' if component in ('ux','uy','uz') else 'rad' if component in ('rx','ry','rz') else 'kN*m' if component in ('Mx','My','Mz','T','M2','M3') else 'kN')
        station = '' if location['kind']=='node' else '-s'+format(location['positionM'],'.12g')+'-'+location['side']
        qid = f"{selection['kind']}-{selection['id']}-{location['kind']}-{location['id']}{station}-{component}"
        q = dict(id=qid, selection=deepcopy(selection), location=location, component=component, unit=unit, tolerance=dict(absolute=1e-8,relative=1e-6))
        old = next((x for x in self.quantities if x['id']==qid),None)
        if old is None: self.quantities.append(q)
        elif old!=q: raise ValueError('Conflicting request '+qid)
        return qid
    def node(self, nid, components=('ux','uy','uz'), selection='D'):
        return [self.add(selection,dict(kind='node',id=nid),c) for c in components]
    def member(self, eid, position, components=('N','V2','V3','T','M2','M3'), selection='D', side='right'):
        return [self.add(selection,dict(kind='member',id=eid,positionM=position,side=side),c) for c in components]
    def ends(self, eid, components=('N','V2','V3','T','M2','M3'), selection='D'):
        return self.member(eid,0,components,selection,'right')+self.member(eid,length(self.model,eid),components,selection,'left')
    def supports(self, selection='D'):
        out=[]
        planar=self.model['coordinate_system']['dimension']=='2d'
        components=('Fx','Fz','My') if planar else ('Fx','Fy','Fz','Mx','My','Mz')
        for n in self.model['nodes']:
            # Ignore planar out-of-plane restraints present at every free node.
            if any(n['restraints'][i] for i in ([0,2,4] if planar else range(6))):
                out += self.node(n['id'],components,selection)
        return out
    def derive(self, qid, operation, operands, description, unit='m'):
        self.derived.append(dict(id=qid,operation=operation,operands=operands,unit=unit,description=description))
        return qid
    def drift(self, lower, upper, components=('ux','uy'), selection='D'):
        for c in components:
            a=self.node(upper,(c,),selection)[0]; b=self.node(lower,(c,),selection)[0]
            self.derive(f'{selection}-drift-{lower}-{upper}-{c}','difference',[a,b],f'{upper} minus {lower}: {c}; signed story displacement difference')

def _json(path, data):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def public_tables(m, en):
    """Human-readable input tables, separately authored from private protocol state."""
    refs=m.get('metadata',{}).get('elementReferenceVectors',{})
    return dict(
        title='Complete numerical input appendix' if en else '完整数值输入附表',
        units=dict(coordinates='m',forces='kN',moments='kN.m',lineLoads='kN/m',E='MPa',G='MPa',density='kg/m^3',A='m^2',Iy='m^4',Iz='m^4',J='m^4',shapeDimensions='mm',rotations='rad',sectionRoll='degree'),
        coordinateConvention=deepcopy(m['coordinate_system']),
        nodeTable=dict(columns=['id','X_m','Y_m','Z_m','fixed_ux','fixed_uy','fixed_uz','fixed_rx','fixed_ry','fixed_rz'],
                       rows=[[n['id'],n['x'],n['y'],n['z'],*n['restraints']] for n in m['nodes']]),
        memberTable=dict(columns=['id','kind','start_node','end_node','material_id','section_id','roll_degrees','axis_reference_vector'],
                         rows=[[e['id'],e['type'],*e['nodes'],e['material'],e['section'],e.get('rotation_angle',0),refs.get(e['id'])] for e in m['elements']]),
        materials=deepcopy(m['materials']),sections=deepcopy(m['sections']),
        loadingCases=deepcopy(m['load_cases']),linearCombinations=deepcopy(m['load_combinations']),
        analysisSettings=deepcopy(m['analysis_control']),
        floorTable=deepcopy(m.get('stories',[])),
        continuityNotes={k:deepcopy(v) for k,v in m.get('metadata',{}).items() if k!='elementReferenceVectors'},
    )

def emit(number, m, prompt, requests, *, notes=(), figures=(), interactions=(), extra_attachments=None):
    """Emit a complete STD single-turn candidate from explicit model and output requests.

    notes: explicit appendix choices and unavoidable source ambiguities, English preferred.
    figures: locale-correct descriptions of genuinely required nonnumerical deliverables.
    extra_attachments: {filename: text or JSON-compatible object}.
    """
    row, task, original_model = source(number)
    cid=row['id']; path=ROOT/'corpora/research-300/cases'/cid; path.mkdir(parents=True,exist_ok=True)
    assert 51<=number<=100
    assert task['turns']==1
    en=row['language']=='英文'
    for record in [*requests.quantities,*requests.derived]:
        if record['unit']=='kN*m':record['unit']='kN.m'
    # Stable explicit reference vectors: x=i->j; y=reference cross x; z=x cross y.
    refs=m.setdefault('metadata',{}).setdefault('elementReferenceVectors',{})
    for e in m['elements']:
        if e['type']=='truss': continue
        if e['id'] not in refs:
            ns={n['id']:n for n in m['nodes']}; a,b=[ns[k] for k in e['nodes']]
            refs[e['id']]=[0,1,0] if m['coordinate_system']['dimension']=='2d' else ([1,0,0] if abs(a['x']-b['x'])+abs(a['y']-b['y'])<1e-10 else [0,0,1])
    # Public appendix is allowed for STD, and contains every model input without answers.
    attachments=['input-data.json','output-requests.json','analysis-conventions.txt']
    convention=(
        'Use the specified engine for first-order linear elastic static analysis with Euler-Bernoulli bending (no shear deformation). Self weight, P-Delta, rigid floors, rigid offsets and construction stages are OFF. Coordinates: global XYZ, Z upward; planar models lie in XZ. Length/displacement m; forces kN; moments kN*m; distributed force kN/m of actual member length; E/G MPa; density kg/m^3; A m^2; Iy/Iz/J m^4; shape dimensions mm; rotations rad. Restraint order ux,uy,uz,rx,ry,rz; true means fixed. All beam/column joints are rigid unless explicit supports say otherwise; truss members carry axial force only. Local x follows ordered member nodes. For 3D, local y = normalized(reference vector cross local x); local z = local x cross local y, then apply the stated rotation_angle about local x. For 2D before any section roll, local y = global +Y and local z = local x cross local y; apply rotation_angle about local x when present. Iy is the inertia about local y. Planar metadata reference vectors are not the 3D cross-product vectors. State local-to-global transforms in results. Member station is measured from the first node; side selects the limiting cut. Preserve signed results and case/combination labels. N is positive in tension. For local member-end resisting actions ordered N,V2,V3,T,M2,M3, the requested signed section resultants use multipliers (-1,+1,+1,-1,-1,-1) at the first-node end and (+1,-1,-1,+1,+1,+1) at the second-node end; do not replace section resultants by unsigned extrema. Report every item in output-requests.json, including derived quantities and governing signed operand/selection for max_abs. Save executable input, engine/version, current model hash, run ID/log and raw indexed results. These are execution requirements, not supplied evidence. The complete input-data.json is a public numerical appendix, not a result file.\n'
        if en else
        '按指定引擎进行一阶线弹性静力分析，采用Euler-Bernoulli弯曲（不计剪切变形）；关闭自重、P-Delta、刚性楼板、刚臂偏移及施工阶段。全局XYZ，Z向上；平面模型位于XZ平面。坐标/位移m，力kN，弯矩kN*m，线载kN/m（按真实杆长），E/G为MPa，密度kg/m^3，A为m^2，Iy/Iz/J为m^4，shape尺寸mm，转角rad。约束顺序ux,uy,uz,rx,ry,rz，true表示固定。梁柱共节点刚接，桁架杆仅传轴力；支座以输入表为准。局部x由构件首节点指向末节点；空间杆局部y为reference vector叉乘局部x的单位向量，局部z=x叉乘y，再按rotation_angle绕局部x转动；平面杆未转轴时局部y为全局+Y、局部z为局部x叉乘局部y，再绕局部x施加rotation_angle；Iy为绕局部y的惯性矩。平面metadata参考向量不采用上述空间叉乘公式。报告局部到全局的转换。杆件位置从首节点计量，side为截面左右极限。N以拉为正；对局部杆端抗力按N,V2,V3,T,M2,M3排序，首节点端乘(-1,+1,+1,-1,-1,-1)、末节点端乘(+1,-1,-1,+1,+1,+1)转换为要求的有符号截面内力，不能取无符号包络替代。逐项报告output-requests.json中数值及派生量，保留符号、单位、工况/组合；绝对值控制量同时给出原符号和控制项/组合。保存可运行输入、引擎版本、当前模型哈希、运行ID/日志及带索引原始结果；这些属于待执行要求，并非已有证据。input-data.json为完整公开输入附表，不含答案。\n')
    engine_line=('Required solver: ' if en else '规定求解引擎：')+row['plannedEngine']+'.\n'
    instructions=engine_line+prompt.rstrip()+'\n\n'+('Use all public appendices. Report the complete requested numerical table and the required summaries.' if en else '使用全部公开附表，输出完整指定数值表及要求的汇总。')
    required=[]
    for q in requests.quantities:
        required.append(dict(id='out-'+q['id'],description=q['id'],state=1,quantityIds=[q['id']],kind='numerical'))
    for d in requests.derived:
        required.append(dict(id='out-'+d['id'],description=d['description'],state=1,quantityIds=[d['id']],kind='derived'))
    for i,description in enumerate(figures,1):
        required.append(dict(id=f'figure-{i}',description=description,state=1,quantityIds=[],kind='figure'))
    for i,description in enumerate(interactions,1):
        required.append(dict(id=f'interaction-{i}',description=description,state=1,quantityIds=[],kind='interaction'))
    gates=[dict(id='native-execution',status='pending'),dict(id='independent-reference',status='pending'),dict(id='input-blind-review',status='pending'),dict(id='adapter-case-acceptance',status='pending'),dict(id='model-fidelity',status='pending'),dict(id='signed-output-completeness',status='pending')]
    coverage=[]
    for field in row['sourceRequirements']:
        ids=[r['id'] for r in row['requirements'] if r['sourceField']==field]
        if field in ('engine.executionRequirement','engine.requiredEvidence'): targets=['gate:native-execution']
        elif field=='engine.truthPlan': targets=['gate:independent-reference']
        elif field in ('engine.adapterGap','task.prerequisite'): targets=['gate:adapter-case-acceptance','gate:input-blind-review']
        elif field in ('task.expectedOutput','task.gradingFocus'): targets=['output:'+o['id'] for o in required]+['attachment:output-requests.json','gate:signed-output-completeness']
        else: targets=['turn:t1','attachment:input-data.json','attachment:analysis-conventions.txt','gate:model-fidelity']
        coverage.append(dict(sourceField=field,requirementIds=ids,targets=targets,notes='Authored evidence mapping only; executable and independent acceptance gates remain pending.'))
    contract=dict(schemaVersion=1,evaluationProfile='engineering-v2.3',id=cid,modelId=row['modelId'],family=row['family'],language=row['language'],locale='en' if en else 'zh',plannedEngine=row['plannedEngine'],sourcePlan=deepcopy(row['sourceRequirements']),modelStates=['model-state-1.json'],attachments=attachments,turns=[dict(id='t1',instruction=instructions,state=1,expectation='analyze',attachments=attachments.copy(),unresolvedFields=[],expectedQuestions=[])],requiredOutputs=required,requirementCoverage=coverage,status='authored-candidate',sameEngineTruthStatus='pending',inputBlindReview='pending',llmEndToEnd='not-run',acceptanceGates=gates,authoringNotes=list(notes))
    for name,content in (extra_attachments or {}).items():
        assert '/' not in name and name not in attachments
        attachments.append(name); contract['turns'][0]['attachments'].append(name)
        if isinstance(content,str): (path/name).write_text(content,encoding='utf-8')
        else: _json(path/name,content)
    _json(path/'contract.json',contract)
    (path/'prompt.txt').write_text(instructions+'\n',encoding='utf-8')
    _json(path/'model-state-1.json',m); _json(path/'input-data.json',public_tables(m,en))
    (path/'analysis-conventions.txt').write_text(convention,encoding='utf-8')
    _json(path/'reference-requests.json',dict(schemaVersion=1,states=[dict(state=1,model='model-state-1.json',quantities=requests.quantities,derived=requests.derived)]))
    _json(path/'output-requests.json',dict(quantities=[{k:v for k,v in q.items() if k!='tolerance'} for q in requests.quantities],derived=requests.derived,figures=list(figures),interactions=list(interactions)))
    _json(path/'author-review.json',dict(id=cid,sourceTask=task,sourceModel=original_model,appendixDecisions=list(notes),reviewStatus='author-inspected-independent-review-pending',native='pending',inputBlindReview='pending'))
    revise_authored_case(path)
    print(cid,len(m['nodes']),len(m['elements']),len(requests.quantities),len(requests.derived))
