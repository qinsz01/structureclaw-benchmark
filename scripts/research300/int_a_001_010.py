"""Explicit INT-001..010 source-based case authoring; no numerical truth values."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import int_a_common as C

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location('representative_primitives', ROOT/'scripts/representative-models.py')
P = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(P)


def beam(stations, supports, sections=None, second_inertia_ratio=None):
    """Stations are explicit source/observation locations; supports never inferred."""
    m = P.model()
    m['sections'] = [P.section('B1', .3, .6)]
    if second_inertia_ratio is not None:
        b2 = deepcopy(m['sections'][0])
        b2.update(id='B2', name='B2', type='general')
        b2.pop('shape')
        b2['properties']['Iy'] *= second_inertia_ratio
        b2['properties']['Iz'] *= second_inertia_ratio
        m['sections'].append(b2)
    for i, x in enumerate(stations):
        restraint = [False, True, False, True, False, True]
        if supports.get(x) == 'pin':
            restraint[0] = restraint[2] = True
        elif supports.get(x) == 'roller':
            restraint[2] = True
        elif supports.get(x) == 'fixed':
            restraint = [True]*6
        P.node(m, f'n{i}', x, 0, restraint=restraint)
    for i in range(len(stations)-1):
        P.elem(m, f'b{i+1}', f'n{i}', f'n{i+1}', sec=(sections or ['B1']*(len(stations)-1))[i])
    return m


def at(m, x):
    return next(n['id'] for n in m['nodes'] if n['x'] == x)


def nodal(m, name, x, case='D', **components):
    P.load(m, case, id=name, type='nodal', node=at(m, x), **components)


def udl(m, name, a, b, q, case='D'):
    ns = {n['id']: n for n in m['nodes']}
    for e in m['elements']:
        x1, x2 = [ns[n]['x'] for n in e['nodes']]
        lo, hi = max(a,x1), min(b,x2)
        if hi > lo:
            P.load(m, case, id=f'{name}-{e["id"]}', type='distributed', element=e['id'],
                   start=lo-x1, end=hi-x1, wz=-q)


def quantity(m, x, component, case='D'):
    unit = 'm' if component in ['ux','uy','uz'] else ('kN*m' if component.startswith('M') else 'kN')
    return dict(id=f'{case}-x{str(x).replace(".","p").replace("-","minus")}-{component}',
                selection=dict(kind='case', id=case), location=dict(kind='node',id=at(m,x)),
                component=component, unit=unit, tolerance=dict(absolute=1e-8,relative=1e-6))


def turn(instruction, state, expectation='analyze', unresolved=(), questions=(), changed=(), preserved=()):
    out = dict(instruction=instruction,state=state,expectation=expectation,attachments=[],
               unresolvedFields=list(unresolved),expectedQuestions=list(questions))
    if changed: out['changedFields']=list(changed)
    if preserved: out['preservedFields']=list(preserved)
    return out


def cases():
    out = []
    m = beam([0,1.5,3,6],{0:'pin',6:'roller'})
    udl(m,'uniform',0,6,20); nodal(m,'near-support-point',1.5,fz=-12)
    m2=deepcopy(m); nodal(m2,'added-midpoint',3,fz=-30)
    out.append(dict(number=1,models=[m,m2,deepcopy(m)],
        initial='跨度6 m，梁沿全局X轴，x=0铰支、x=6 m竖向滚支。工况D含全跨向下20 kN/m及x=1.5 m向下12 kN点力。x=3 m是连通观测节点。',
        turns=[turn('按附件建立并分析梁。报告x=3 m的Uz及左支座Rz。',1),
               turn('在工况D的x=3 m跨中追加向下30 kN点力，保留原荷载，重新分析并报告相同位置的Uz及Rz。',2,changed=['/load_cases/0/loads/4'],preserved=['/nodes','/elements','/materials','/sections','/load_cases/0/loads/0','/load_cases/0/loads/1','/load_cases/0/loads/2','/load_cases/0/loads/3']),
               turn('只撤销上一轮追加的跨中30 kN点力，保留20 kN/m及x=1.5 m的12 kN力，重新分析并报告相同输出。',3,changed=['/load_cases/0/loads/4'],preserved=['/nodes','/elements','/materials','/sections','/load_cases/0/loads/0','/load_cases/0/loads/1','/load_cases/0/loads/2','/load_cases/0/loads/3'])],
        requests=[[quantity(x,3,'uz'),quantity(x,0,'Fz')] for x in [m,m2,m]],
        outputs=[(1,'工况D，x=3 m的Uz及左支座Rz。'),(2,'工况D，x=3 m的Uz及左支座Rz。'),(3,'工况D，x=3 m的Uz及左支座Rz。')]))

    m=beam([0,3],{0:'fixed'}); nodal(m,'axial-tip',3,fx=5); nodal(m,'vertical-tip',3,fz=-10)
    out.append(dict(number=2,models=[m],
        initial='A 3 m cantilever lies on global X. The left end x=0 is fixed and the right end x=3 m is free. At the free end, an independent axial force is +5 kN in global X. A separate downward point force is written as 10, with its force unit omitted. No unit convention in this appendix applies to that unresolved value.',
        redact='loads',
        turns=[turn('Build the cantilever from the attachment and report free-end Ux/Uz and fixed-end reaction My. The downward tip-force entry is 10 with no unit. Request only the missing force unit before solving.',None,'clarify',['/load_cases/0/loads/1/forceUnit'],['What is the force unit for the downward tip-force value 10?']),
               turn('The downward tip force is 10 kN. Keep the independent +5 kN axial force, the left fixed end and the 3 m length. Analyze and report Ux and Uz at x=3 m and reaction My at x=0.',1)],
        requests=[[quantity(m,3,'ux'),quantity(m,3,'uz'),quantity(m,0,'My')]],
        outputs=[(1,'Case D: Ux and Uz at the free end x=3 m, and fixed-end support reaction My at x=0.')]))

    m=beam([0,2.5,3.25,5,6.5],{0:'pin',5:'roller'},['B1','B1','B1','B2'],.5)
    udl(m,'uniform',0,6.5,15)
    out.append(dict(number=3,models=[m],
        initial='右外伸梁沿全局X轴；x=0铰支、x=5 m竖向滚支，右自由端x=6.5 m。全长0～6.5 m向下15 kN/m，工况D。0～5 m用B1，5～6.5 m用B2；B2的Iy及Iz为B1一半，其余属性相同。x=2.5、3.25、5 m均为连通节点。',
        turns=[turn('建立并分析附件梁，报告x=3.25 m与外伸自由端x=6.5 m的Uz。',1),
               turn('把第一个位移观测位置改为支承跨中x=2.5 m，外伸自由端x=6.5 m保持。结构、截面分界和全部荷载不变；可复用当前有效结果，报告这两个位置的Uz。',1,'query',preserved=['/nodes','/elements','/materials','/sections','/load_cases','/load_combinations'])],
        requests=[[quantity(m,3.25,'uz'),quantity(m,6.5,'uz'),quantity(m,2.5,'uz')]],
        outputs=[(1,'第1轮工况D：x=3.25 m与x=6.5 m的Uz。',[0,1]),(1,'第2轮工况D：x=2.5 m与x=6.5 m的Uz。',[2,1])]))

    m=beam([0,4,6,9,12],{0:'pin',12:'roller'});udl(m,'partial',0,9,15);nodal(m,'eccentric-point',4,fz=-50)
    out.append(dict(number=4,models=[m],redact='supports',
        initial='A 12 m beam lies on global X. One support note says both ends fixed. A conflicting note says a pin at x=0 and a vertical roller at x=12 m. Both notes are unresolved; neither takes precedence. Case D has a downward 15 kN/m load only from x=0 to 9 m and a separate downward 50 kN point force at x=4 m. The displacement observation point is x=6 m.',
        turns=[turn('Review the attachment and calculate Uz at x=6 m and left support Rz. Resolve the contradictory support notes before calculating; retain all load information.',None,'clarify',['/nodes/0/restraints','/nodes/4/restraints'],['Should the beam use both ends fixed or a left pin and right vertical roller?']),
               turn('Use a pin at x=0 and a vertical roller at x=12 m. Keep the 15 kN/m load on x=0 to 9 m, the 50 kN point force at x=4 m, and the observation point at x=6 m. Analyze and report Uz there and Rz at x=0.',1)],
        requests=[[quantity(m,6,'uz'),quantity(m,0,'Fz')]],
        outputs=[(1,'Case D: Uz at x=6 m and left support reaction Rz at x=0.')]))

    m=beam([0,2,4],{0:'pin',4:'roller'});nodal(m,'midpoint-force',2,fz=-25);nodal(m,'left-moment',0,my=10)
    m2=deepcopy(m);m2['load_cases'][0]['loads'][0]['fz']=-40
    out.append(dict(number=5,models=[m,m2],
        initial='4 m梁沿全局X轴，x=0铰支、x=4 m竖向滚支。工况D在跨中x=2 m施加向下25 kN点力，在左支座节点另施加全局+Y方向10 kN·m外力矩（右手定则）。跨中节点连接左右两段梁。',
        turns=[turn('建立并分析附件梁，报告跨中x=2 m的Uz及左支座Rz。',1),
               turn('将跨中向下25 kN替换为40 kN，保留左支座外力矩10 kN·m及全部几何、材料、支承。重新分析并报告相同输出。',2,changed=['/load_cases/0/loads/0/fz'],preserved=['/nodes','/elements','/materials','/sections','/load_cases/0/loads/1'])],
        requests=[[quantity(x,2,'uz'),quantity(x,0,'Fz')] for x in [m,m2]],
        outputs=[(1,'工况D：x=2 m的Uz及左支座Rz。'),(2,'工况D：x=2 m的Uz及左支座Rz。')]))

    m=beam([0,4,8],{0:'pin',8:'roller'},['B1','B2'],1.5);udl(m,'uniform',0,8,18)
    m2=beam([0,5,10],{0:'pin',10:'roller'},['B1','B2'],1.5);udl(m2,'uniform',0,10,18)
    out.append(dict(number=6,models=[m,m2],
        initial='An 8 m beam lies on global X with a left pin at x=0 and a vertical roller at x=8 m. Case D is a full-length downward 18 kN/m UDL. The left half uses B1 and the right half B2; B2 has 1.5 times B1 Iy and Iz, with all other properties identical. The section boundary and connected midpoint observation node are at x=4 m.',
        turns=[turn('Analyze the attached 8 m beam. Report midpoint Uz at x=4 m and both support Rz values.',1),
               turn('Change the span to 10 m. Move the right roller to x=10 m and the section boundary and connected midpoint to x=5 m. Keep the UDL intensity 18 kN/m over the entire new span and retain the section property relationship. Analyze the updated model and report current midpoint Uz and both Rz values; label the earlier 8 m results as historical.',2,changed=['/nodes/1/x','/nodes/2/x','/load_cases/0/loads/0/end','/load_cases/0/loads/1/end','/metadata/elementReferenceVectors/b1','/metadata/elementReferenceVectors/b2'],preserved=['/elements','/materials','/sections','/nodes/0','/nodes/1/restraints','/nodes/2/restraints','/load_cases/0/loads/0/wz','/load_cases/0/loads/1/wz'])],
        requests=[[quantity(m,4,'uz'),quantity(m,0,'Fz'),quantity(m,8,'Fz')],[quantity(m2,5,'uz'),quantity(m2,0,'Fz'),quantity(m2,10,'Fz')]],
        outputs=[(1,'Case D: midpoint Uz at x=4 m and Rz at x=0 and 8 m.'),(2,'Case D: current midpoint Uz at x=5 m and Rz at x=0 and 10 m.')]))

    m=beam([-2,0,4,8],{0:'pin',8:'roller'});udl(m,'uniform',-2,8,15)
    out.append(dict(number=7,models=[m],redact='loads',
        initial='梁沿全局X轴；支座在x=0（铰）及x=8 m（竖向滚支），左自由端延至x=-2 m。支承跨长8 m，左外伸长2 m。x=4 m为连通观测节点。材料及截面见完整附表。外荷载信息暂缺，不能解释为零载，也无默认荷载。',
        turns=[turn('根据附件建立梁，需报告支承跨中x=4 m及左自由端x=-2 m的Uz。目前尚未给外荷载；请仅澄清缺少的荷载信息。',None,'clarify',['/load_cases'],['请给出外荷载的类型、大小、方向、单位及作用位置或区间。']),
               turn('补全工况D：整根梁x=-2～8 m均施加竖直向下15 kN/m。保留左外伸2 m、支座、材料及截面，完成静力分析，报告x=4 m及左自由端x=-2 m的Uz。',1)],
        requests=[[quantity(m,4,'uz'),quantity(m,-2,'uz')]],
        outputs=[(1,'工况D：支承跨中x=4 m及左自由端x=-2 m的Uz。')]))

    m=beam([0,2,3,4.5,7,8,9],{0:'fixed',9:'roller'});udl(m,'partial',2,7,12)
    m2=deepcopy(m);m2['load_cases'][0]['loads']=[];udl(m2,'partial',3,8,12)
    out.append(dict(number=8,models=[m,m2],
        initial='A 9 m beam lies on global X, fixed at x=0 and supported by a vertical roller at x=9 m. In case D, a downward 12 kN/m UDL acts only on x=2 to 7 m. The observation point is x=4.5 m. Connected stations at x=2, 3, 4.5, 7 and 8 m carry no extra supports.',
        turns=[turn('Analyze the attached beam. Report Uz at x=4.5 m and the left fixed-support reaction My.',1),
               turn('Move the UDL interval from x=2–7 m to x=3–8 m, retaining 12 kN/m downward intensity. Apply it only to the new 5 m interval. Keep the 9 m length, left fixed end and right vertical roller. Reanalyze and report Uz at x=4.5 m and left-support My.',2,changed=['/load_cases/0/loads'],preserved=['/nodes','/elements','/materials','/sections','/analysis_control'])],
        requests=[[quantity(x,4.5,'uz'),quantity(x,0,'My')] for x in [m,m2]],
        outputs=[(1,'Case D: Uz at x=4.5 m and fixed-support reaction My at x=0.'),(2,'Case D after moving the UDL: Uz at x=4.5 m and fixed-support reaction My at x=0.')]))

    m=beam([0,2,5,7,8,10],{0:'fixed',10:'fixed'});nodal(m,'left-point',2,fz=-30);nodal(m,'right-point',7,fz=-45)
    m2=deepcopy(m);m2['load_cases'][0]['loads'][0]['fz']=-35
    m3=deepcopy(m2);m3['load_cases'][0]['loads'][1]['node']=at(m3,8)
    m4=deepcopy(m2)
    out.append(dict(number=9,models=[m,m2,m3,m4],
        initial='10 m梁沿全局X轴，两端x=0和10 m均固定。工况D含两个向下点力：x=2 m处30 kN、x=7 m处45 kN；x=5 m为连通观测节点。x=8 m也是连接左右单元的无支承节点。',
        turns=[turn('建立并分析附件梁，报告x=5 m的Uz及两固定支座My。',1),
               turn('仅把左侧x=2 m处的30 kN改为35 kN。重新分析并报告x=5 m的Uz及两固端My。',2,changed=['/load_cases/0/loads/0/fz'],preserved=['/nodes','/elements','/materials','/sections','/load_cases/0/loads/1']),
               turn('仅把右侧45 kN点力从x=7 m移到x=8 m，左侧35 kN保持。重新分析并报告相同输出。',3,changed=['/load_cases/0/loads/1/node'],preserved=['/nodes','/elements','/materials','/sections','/load_cases/0/loads/0','/load_cases/0/loads/1/fz']),
               turn('只撤销最近一次位置修改，将右侧45 kN移回x=7 m，保留左侧x=2 m的35 kN。重新分析并报告相同输出。',4,changed=['/load_cases/0/loads/1/node'],preserved=['/nodes','/elements','/materials','/sections','/load_cases/0/loads/0','/load_cases/0/loads/1/fz'])],
        requests=[[quantity(x,5,'uz'),quantity(x,0,'My'),quantity(x,10,'My')] for x in [m,m2,m3,m4]],
        outputs=[(i,'工况D：x=5 m的Uz及两固定支座My。') for i in range(1,5)]))

    m=beam([0,4,8],{0:'fixed',8:'fixed'},['B1','B2'],2);udl(m,'full',0,8,8);udl(m,'left-half',0,4,6,'L')
    out.append(dict(number=10,models=[m],redact='loads',
        initial='An 8 m beam lies on global X with both ends fixed. The left half x=0–4 m uses B1 and the right half x=4–8 m uses B2. B2 Iy and Iz are twice B1, with all other properties identical. A full-span downward 8 kN/m UDL is labelled D. A separate downward 6 kN/m UDL on the left half is inconsistently labelled both D and L. Those two labels refer to one physical left-half load entry, whose case assignment remains unresolved.',
        turns=[turn('Review the attachment. Report Uz at x=4 m and left fixed-support My separately for cases D and L. Resolve the conflicting case labels for the 6 kN/m left-half load before calculating.',None,'clarify',['/load_cases/left-half-load/case'],['Does the single 6 kN/m left-half load belong to D or L?']),
               turn('The 6 kN/m left-half load belongs only to L. The full-span 8 kN/m load belongs only to D. Keep both fixed ends and both section groups. Analyze D and L independently and report Uz at x=4 m and left fixed-support My for each case.',1)],
        requests=[[quantity(m,4,'uz','D'),quantity(m,0,'My','D'),quantity(m,4,'uz','L'),quantity(m,0,'My','L')]],
        outputs=[(1,'For D and L separately: Uz at x=4 m and fixed-support reaction My at x=0.')]))
    return out


def author():
    for c in cases():
        case_id=f'INT-{c["number"]:03}'
        coverage, task, sm = C.sources(case_id)
        en=coverage['language']=='英文'
        locale='en' if en else 'zh'
        public=C.finalize(c['models'][0])
        if c.get('redact')=='loads':
            # Never let a final-state case table reveal a withheld load or its unit.
            public.pop('load_cases')
            public.pop('load_combinations')
            if c['number']==2:
                public.pop('unit_system')
        if c.get('redact')=='supports':
            # Neither of the contradictory boundary descriptions takes precedence.
            for n in public['nodes']:
                if n['x'] in (0,12):
                    n['restraints']='Unresolved: both-fixed note conflicts with pin/vertical-roller note.'
        extra=(
            'Section shape dimensions B and H are in mm; all section properties use the explicit SI units stated above. '
            'Use OpenSees. Report signed values with node/location, global direction, unit, load case and current turn. '
            'Rz means the support reaction in global +Z; fixed-end My means support reaction moment about global +Y by the right-hand rule. '
            'Each change to a physical model requires a fresh run. Save input, model snapshot, version/settings, run ID, successful log and result mapping. '
            'Reuse results for a query only when traceable to the same unchanged state. Do not produce numerical answers while essential input is unresolved. '
            'Do not introduce releases, extra supports, masses, rigid zones, automatic combinations or additional loads. '
            'Connected internal nodes have no added translational support. Only explicit later edits change this input.\n'
        ) if en else (
            '截面shape内B和H尺寸单位为mm，其余截面properties按上述明确单位。使用OpenSees，输出带符号数值并注明节点/位置、全局方向、单位、工况及当前轮次。Rz表示全局+Z支反力；固端My指按右手定则绕全局+Y的支座反力矩。'
            '物理模型修改后必须重新运行；保存输入、模型快照、软件版本/设置、运行ID、成功日志及结果位置映射。'
            '纯查询仅可复用可追溯至同一未变状态的有效结果；必要信息未解决时不得编造数值。'
            '不得额外引入释放、支承、质量、刚域、自动组合或附加载荷。内部连通节点不增加平移支承。后续只执行明确修改。\n'
        )
        rendered=C.tables(public,locale,extra+c['initial'])
        if c['number']==2:
            rendered=rendered.replace('nodal forces kN; ', 'known force units are explicit in each prose entry; the downward tip-force value has NO supplied force unit; ')
            rendered=rendered.replace('All omitted load components are zero.', 'Unspecified components of fully specified loads are zero; the unresolved downward force remains unknown and is not zero.')
        if c['number']==7:
            rendered=rendered.replace('未列荷载分量为零。','当前全部外荷载待补充，未提供的外荷载不能视为零；补齐后已定义荷载的未列分量为零。')
        if c['number']==10:
            rendered=rendered.replace('All omitted load components are zero.', 'Components other than the stated downward direction are zero; the left-half load case assignment is unresolved.')
        file='input-tables.txt'
        c['turns'][0]['attachments']=[file]
        c['turns'][0]['instruction'] += (' Use the attached input tables and OpenSees; include signed values, location, direction, units, case and current turn.' if en else ' 使用所附输入表与OpenSees，输出须注明符号、位置、方向、单位、工况和当前轮次。')
        outputs=[]
        for oi,o in enumerate(c['outputs'],1):
            state, description = o[:2]
            indexes=o[2] if len(o)>2 else list(range(len(c['requests'][state-1])))
            outputs.append(dict(id=f'requested-output-{oi}',description=description,state=state,
                                quantityIds=[c['requests'][state-1][i]['id'] for i in indexes],kind='numerical'))
            if c['number']==3:outputs[-1]['turnIds']=[f't{oi}']
        decisions=[
            dict(id='missing-property-appendix',description='The source omits absolute section/material properties. This authored appendix freezes Q355 steel E=206000 MPa, nu=0.3, G=E/[2(1+nu)] MPa, rho=7850 kg/m3, and B1 solid rectangle 0.3 m by 0.6 m with explicit A/Iy/Iz/J. They are inputs, not engine defaults.'),
            dict(id='axes-and-fixed-end-moment',description='Horizontal members run in +X; local y is global +Y. Uz is global +Z displacement; Rz is global +Z support reaction. Requested fixed-end My is the global +Y support reaction moment, signed by the right-hand rule.'),
            dict(id='observation-connectivity',description='All point-load and displacement observation locations use connected beam nodes. Extra internal stations have no added planar support or mass.'),
            dict(id='native-and-reference-status',description='Only source/structural authoring checks have run. Independent numerical reference, native engine execution, adapter acceptance and blind input review remain pending.'),
        ]
        if c['number'] in (3,6,10):
            ratio={3:.5,6:1.5,10:2}[c['number']]
            decisions.append(dict(id='specified-inertia-ratio',description=f'B2 is an explicit general section. Its Iy and Iz are {ratio} times those of B1 as required by the source; A and J are unchanged. No inconsistent derived shape is supplied for B2.'))
        if c['number']==3:
            decisions.append(dict(id='query-without-remeshing',description='Both x=2.5 m and x=3.25 m are preconnected observation nodes in state 1, so the second turn is a pure query of the same physical model.'))
        C.write_case(case_id,c['models'],c['turns'],c['requests'],{file:rendered},decisions=decisions,outputs=outputs,
                     source_audit=[dict(field=f,source=source,review='Mapped to explicit public inputs, turn semantics, output requests or pending acceptance gates; no native acceptance asserted.') for f,source in coverage['sourceRequirements'].items()])
        print(f'{case_id}: {len(c["turns"])} turns, {len(c["models"])} model states, {sum(map(len,c["requests"]))} requested quantities')


if __name__=='__main__':
    author()
