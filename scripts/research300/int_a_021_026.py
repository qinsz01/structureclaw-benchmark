"""Source-specific INT-021..026 authoring. Numerical truth remains pending."""
from copy import deepcopy
import json
from pathlib import Path
import int_a_common as C


def beam(xs, supports, section_ids=None, section_table=None):
    m=C.model()
    m['sections']=section_table or [C.section('B1',.3,.6)]
    for i,x in enumerate(xs):
        C.node(m,f'n{i}',x,0,restraint=deepcopy(supports.get(x,C.FREE)))
    for i in range(len(xs)-1):
        C.elem(m,f'b{i+1}',f'n{i}',f'n{i+1}',sec=section_ids[i] if section_ids else 'B1')
    return m


def at(m,x):
    return next(n['id'] for n in m['nodes'] if n['x']==x)


def udl(m,name,start,end,wz,case='D'):
    ns={n['id']:n['x'] for n in m['nodes']}
    for e in m['elements']:
        a,b=[ns[n] for n in e['nodes']];lo,hi=max(start,a),min(end,b)
        if hi>lo:C.load(m,case,id=f'{name}-{e["id"]}',type='distributed',element=e['id'],start=lo-a,end=hi-a,wz=wz)


def point(m,name,x,case='D',**load):
    C.load(m,case,id=name,type='nodal',node=at(m,x),**load)


def requested(m,x,support,selection='D',kind='case',moment=False):
    return [C.quantity(at(m,x),'uz',selection,kind),C.quantity(at(m,support),'My' if moment else 'Fz',selection,kind)]


def section_set():
    return [C.section('B1',.3,.6),C.section('B2',.3,.7),C.section('B3',.35,.8)]


def cases():
    out=[]
    m=beam([0,6,9,12],{0:C.FIXED,6:C.ROLLER,12:C.ROLLER},['B1','B2','B2'],section_set());udl(m,'full',0,12,-10)
    m2=deepcopy(m)
    for e in m2['elements'][1:]:e['section']='B3'
    out.append(dict(id='INT-021',models=[m,m2],
        initial='连续梁沿全局X轴，两跨各6 m；x=0固定，x=6、12 m仅竖向滚支。第一跨0～6 m用B1，第二跨6～12 m用B2；B3为附表备用截面。工况D全长向下10 kN/m。中支座是同一个连续节点，跨中x=9 m节点连接左右梁段。',
        turns=[C.turn('按附件建立连续梁，分析并报告第二跨中点x=9 m的Uz及x=0固定端My。',1),
               C.turn('只将第二跨6～12 m的全部B2构件换成附件B3；第一跨B1、10 kN/m均布载和支承均保持。重新分析并报告第二跨中点Uz及左固端My。',2,changedFields=['/elements/1/section','/elements/2/section'],preservedFields=['/nodes','/materials','/sections','/elements/0','/load_cases','/load_combinations'])],
        requests=[requested(x,9,0,moment=True) for x in [m,m2]],
        descriptions=['工况D：x=9 m的Uz及x=0固定支座绕全局+Y的My。']*2,
        decisions=[dict(id='load-direction-completion',description='The source provides UDL magnitude but no explicit direction. The appendix freezes 10 kN/m in global -Z.')]))

    m=beam([0,5,10,12],{0:C.PIN,5:C.ROLLER,10:C.ROLLER});udl(m,'overhang',10,12,-8);point(m,'free-end-force',12,fz=-10)
    m2=deepcopy(m);m2['nodes'][-1]['x']=13;m2['load_cases'][0]['loads'][0]['end']=3
    out.append(dict(id='INT-022',models=[m,m2],
        initial='A continuous beam lies on global X with a pin at x=0 and vertical rollers at x=5 and 10 m. The free right end is initially x=12 m. In case D only the overhang x=10–12 m carries an 8 kN/m downward UDL, and a separate 10 kN downward point force acts at the free end. Both supported spans carry no UDL. All connected spans use B1.',
        turns=[C.turn('Analyze the attached continuous beam. Report Uz at the current free end x=12 m and Rz at the x=10 m support.',1),
               C.turn('Change the right overhang length from 2 m to 3 m, so its free end is x=13 m. Keep supports at x=0, 5 and 10 m. The 10 kN downward point force follows the new free end; the downward 8 kN/m UDL covers only the new x=10–13 m overhang. Reanalyze and report current free-end Uz and Rz at x=10 m.',2,changedFields=['/nodes/3/x','/load_cases/0/loads/0/end','/metadata/elementReferenceVectors/b3'],preservedFields=['/nodes/0','/nodes/1','/nodes/2','/nodes/3/restraints','/elements','/materials','/sections','/load_cases/0/loads/1','/load_cases/0/loads/0/wz'])],
        requests=[requested(m,12,10),requested(m2,13,10)],
        descriptions=['Case D: free-end Uz at x=12 m and support Rz at x=10 m.','Case D: current free-end Uz at x=13 m and support Rz at x=10 m.'],
        decisions=[dict(id='load-direction-completion',description='The source gives the overhang UDL and tip-force magnitudes without explicit signs. Both are frozen downward in global -Z in the public appendix.')]))

    m=beam([0,1,3,4,7,10],{0:C.PIN,4:C.ROLLER,10:C.ROLLER});udl(m,'upward-patch',1,3,4);point(m,'support-point',4,fz=-30);point(m,'span-point',7,fz=-20)
    m2=deepcopy(m);m2['load_cases'][0]['loads'][2]['fz']=-25
    out.append(dict(id='INT-023',models=[m,m2],
        initial='连续梁沿全局X轴，两跨4 m和6 m；x=0铰支，x=4、10 m竖向滚支。工况D含三项独立荷载：中支座x=4 m向下30 kN；第二跨中点x=7 m向下20 kN；首跨仅x=1～3 m向上4 kN/m。x=1、3、7 m均为无额外平移支承的连通节点。',
        turns=[C.turn('按附件建立并分析梁，报告第二跨中点x=7 m的Uz及中支座x=4 m的Rz。',1),
               C.turn('把那个点力改成25 kN，再报告相同结果。',None,'clarify',unresolved=['/pendingEdit/targetLoadId'],questions=['请确认要修改中支座x=4 m的30 kN点力，还是第二跨中点x=7 m的20 kN点力？']),
               C.turn('确认是第二跨中点x=7 m的那项，改为向下25 kN。中支座30 kN及首跨x=1～3 m上向4 kN/m均保持。重新分析并报告x=7 m的Uz及中支座Rz。',2,changedFields=['/load_cases/0/loads/2/fz'],preservedFields=['/nodes','/elements','/materials','/sections','/load_cases/0/loads/0','/load_cases/0/loads/1'])],
        requests=[requested(x,7,4) for x in [m,m2]],
        descriptions=['第1轮工况D：x=7 m的Uz及中支座x=4 m的Rz。','第3轮工况D：更新后x=7 m的Uz及中支座x=4 m的Rz。'],
        decisions=[dict(id='later-clarification',description='Turn 1 has a valid analyzed model. Turn 2 is an ambiguous new edit, so state is null and no updated numerical answer is requested; the historical state remains intact. Only turn 3 authorizes the load target and creates state 2.')]))

    b1=C.section('B1',.3,.6);b2=deepcopy(b1);b2.update(id='B2',name='B2',type='general');b2.pop('shape')
    for k in ['Iy','Iz']:b2['properties'][k]*=.5
    m=beam([0,5,7.5,10,15],{0:C.PIN,5:C.ROLLER,10:C.ROLLER,15:C.ROLLER},['B1','B2','B2','B1'],[b1,b2]);udl(m,'downward',0,15,-8);udl(m,'upward',5,10,6,'W')
    next(lc for lc in m['load_cases'] if lc['id']=='W')['type']='wind'
    m['load_combinations']=[dict(id='C0',factors={'D':1}),dict(id='C1',factors={'D':1,'W':1}),dict(id='C2',factors={'D':.9,'W':1.5})]
    out.append(dict(id='INT-024',models=[m],
        initial='A continuous beam has three 5 m spans on global X: a pin at x=0 and vertical rollers at x=5, 10 and 15 m. All roller restraints are bilateral, preventing either upward or downward motion and allowing signed reactions. End spans use B1 and the middle span uses B2; B2 has half B1 Iy and Iz, equal A, and unchanged J/material. Global +Z is upward. Case D is wz=-8 kN/m over the entire beam. Case W is wz=+6 kN/m only over the middle span x=5–10 m. The three explicitly prescribed linear combinations are C0=1.0D, C1=1.0D+1.0W and C2=0.9D+1.5W. These are task-defined coefficients, with no automatic code combination generation.',
        turns=[C.turn('Analyze the attached beam directly with its signed D and W loads and all three combinations C0, C1 and C2. Keep the original cases separate. For every combination report Uz at middle-span midpoint x=7.5 m and support Rz at x=5 m. Positive W acts upward.',1)],
        requests=[[q for comb in ['C0','C1','C2'] for q in requested(m,7.5,5,comb,'combination')]],
        descriptions=['For each of C0, C1 and C2: signed Uz at x=7.5 m and support Rz at x=5 m.'],
        decisions=[dict(id='missing-combination-appendix',description='INT-024 requests three combinations but omits their coefficients. The adjacent STD-024/M-STD-024 source anchor explicitly provides only C0=D and C1=D+W, which are retained. The missing third combination is explicitly frozen as C2=0.9D+1.5W before any candidate run. These are prescribed arithmetic coefficients, not a code rule. Bilateral roller restraints follow the explicit adjacent anchor convention.'),dict(id='middle-section-completion',description='B2 Iy and Iz are exactly 0.5 times B1, and A is equal as required. The otherwise unspecified J is explicitly kept equal to B1; B2 is general with no conflicting geometric shape.')]))

    m=beam([0,5,7.5,10],{0:C.PIN,5:C.ROLLER,10:C.ROLLER});udl(m,'right-span',5,10,-6);point(m,'right-end-moment',10,my=20)
    out.append(dict(id='INT-025',models=[m],redact='moment-unit',
        initial='连续梁沿全局X轴，两跨各5 m；x=0铰支，x=5、10 m竖向滚支。工况D仅右跨x=5～10 m向下6 kN/m，左跨没有均布载。右端x=10 m另有绕全局+Y的正向节点力矩，数值写作20，但力矩单位未提供；按右手规则约定方向。任何其他已知量的单位都不适用于这个待澄清数值。x=7.5 m是连通观测节点。',
        turns=[C.turn('根据附件建立梁，右端绕全局+Y的节点力矩数值为20、单位漏写。请仅确认力矩单位，然后报告右跨中点x=7.5 m的Uz及右支座x=10 m的Rz。',None,'clarify',unresolved=['/load_cases/0/loads/2/momentUnit'],questions=['右端绕全局Y的力矩数值20使用什么力矩单位？']),
               C.turn('右端力矩为20 kN·m，正向按全局+Y的右手规则。保留两跨5 m+5 m及仅右跨6 kN/m均布载，分析并报告x=7.5 m的Uz及x=10 m右支座Rz。',1)],
        requests=[requested(m,7.5,10)],
        descriptions=['第2轮工况D：右跨中点x=7.5 m的Uz及右支座x=10 m的Rz。'],
        decisions=[dict(id='unit-withholding',description='The initial public table omits the final nodal-moment load record, generic moment unit and model unit_system. Only the known right-span UDL is numeric. The final moment unit is revealed in turn 2 only.'),dict(id='load-direction-completion',description='The source omits the direction of the 6 kN/m right-span UDL. The appendix freezes downward global -Z; the positive-Y end moment follows the source right-hand-rule clarification.')]))

    m=beam([0,4,10,15,17,19],{0:C.PIN,4:C.ROLLER,10:C.ROLLER,15:C.ROLLER,19:C.ROLLER},['B1','B2','B2','B1','B1'],section_set());udl(m,'dead-full',0,19,-8);point(m,'dead-fourth-midpoint',17,fz=-16);udl(m,'live-second',4,10,-10,'L');udl(m,'live-fourth',15,19,-10,'L')
    m['load_combinations']=[dict(id='C1',factors={'D':1}),dict(id='C2',factors={'D':1,'L':1})]
    m2=deepcopy(m)
    for l in m2['load_cases'][1]['loads']:l['wz']=-12
    m3=deepcopy(m2)
    for e in m3['elements'][1:3]:e['section']='B3'
    m4=deepcopy(m3)
    for l in m4['load_cases'][1]['loads']:l['wz']=-10
    live_changed=[f'/load_cases/1/loads/{i}/wz' for i in range(3)]
    out.append(dict(id='INT-026',models=[m,m2,m3,m4],
        initial='A continuous beam lies on global X with spans 4, 6, 5 and 4 m. Supports are a pin at x=0 and vertical rollers at x=4, 10, 15 and 19 m. The middle two spans x=4–15 m use B2; the first and fourth spans use B1. B3 is provided as a separate available section. Case D has a downward 8 kN/m UDL over the entire beam plus a separate downward 16 kN point force at fourth-span midpoint x=17 m. Case L has downward 10 kN/m only on spans 2 and 4, x=4–10 m and x=15–19 m. Prescribed combinations remain C1=D and C2=D+L. The x=17 m observation/load node is connected to both adjacent members and has no extra support.',
        turns=[C.turn('Analyze the attached beam. For D, L, C1 and C2 separately, report Uz at fourth-span midpoint x=17 m and support Rz at x=15 m.',1),
               C.turn('Increase the live-load intensity on both the second and fourth spans from 10 to 12 kN/m downward. Keep D, geometry, section assignments and combination coefficients. Reanalyze and report the same outputs for D, L, C1 and C2.',2,changedFields=live_changed,preservedFields=['/nodes','/elements','/materials','/sections','/load_cases/0','/load_combinations']),
               C.turn('Replace B2 by the attached B3 on the middle two spans x=4–10 m and x=10–15 m. Retain the current 12 kN/m live loads, all D loads and combination coefficients. Reanalyze and report the same outputs for D, L, C1 and C2.',3,changedFields=['/elements/1/section','/elements/2/section'],preservedFields=['/nodes','/materials','/sections','/load_cases','/load_combinations','/elements/0','/elements/3','/elements/4']),
               C.turn('Undo only the turn-2 live-load adjustment: restore the second- and fourth-span live loads to 10 kN/m downward. Keep the turn-3 B3 sections on the middle two spans, the D point force of 16 kN at x=17 m, all other D loads and the combination coefficients. Reanalyze and report the same outputs for D, L, C1 and C2.',4,changedFields=live_changed,preservedFields=['/nodes','/elements','/materials','/sections','/load_cases/0','/load_combinations'])],
        requests=[[q for selection,kind in [('D','case'),('L','case'),('C1','combination'),('C2','combination')] for q in requested(x,17,15,selection,kind)] for x in [m,m2,m3,m4]],
        descriptions=['For D, L, C1 and C2 separately: Uz at x=17 m and support Rz at x=15 m.']*4,
        decisions=[dict(id='selective-undo',description='State 4 restores only live-load intensities from state 1 while retaining state 3 B3 section assignments. Neither D nor the source-defined C1/C2 factors changes in any turn.')]))
    return out


def author():
    for data in cases():
        coverage,task,source_model=C.sources(data['id']);en=coverage['language']=='英文';locale='en' if en else 'zh'
        public=C.finalize(data['models'][0])
        if data.get('redact')=='moment-unit':
            public.pop('unit_system')
            public['load_cases'][0]['loads']=[l for l in public['load_cases'][0]['loads'] if l['id']!='right-end-moment']
        common=('Section shape dimensions B and H are mm. Members are rigidly continuous at shared nodes; only listed supports restrain planar DOFs. '
                'Use OpenSees with the explicit properties and settings. Report signed values with location, global direction, unit, case/combination and current turn. '
                'Rz is support reaction in global +Z; fixed-end My is support reaction moment about global +Y by the right-hand rule. '
                'After a physical change, run the current state and retain input, snapshot, model differences, software version/settings, run ID, success log and result mapping. '
                'Do not guess essential missing input or present historical results as the updated result.\n') if en else (
                '截面shape中B和H尺寸单位为mm；共用节点连续刚接，只有明示支承约束平面自由度。使用OpenSees及明确给出的属性和设置。'
                '输出须有符号、位置、全局方向、单位、工况/组合及当前轮次。Rz是全局+Z支反力；固端My是按右手规则绕全局+Y的支座反力矩。'
                '物理模型修改后必须计算当前状态，保存输入、快照及字段差异、软件版本/设置、运行ID、成功日志和结果映射。'
                '不得猜测必要缺项，不得把历史结果当作更新结果。\n')
        rendered=C.tables(public,locale,common+data['initial'])
        if data.get('redact')=='moment-unit':
            rendered=rendered.replace('节点力矩kN*m；','节点力矩单位仅按各项明确注明，右端数值20的力矩单位待确认；')
            rendered=rendered.replace('未列荷载分量为零。','已明确荷载的未列分量为零；右端待澄清力矩不属于已完成输入，不可视为零。')
        data['turns'][0]['attachments']=['input-tables.txt']
        data['turns'][0]['instruction']+=(' Use the attached input tables and OpenSees, and label each result with location, direction, unit, case/combination and turn.' if en else ' 使用附件输入表与OpenSees，每项结果注明位置、方向、单位、工况/组合和轮次。')
        outputs=[dict(id=f'requested-state-{s}',description=description,state=s,quantityIds=[q['id'] for q in data['requests'][s-1]],kind='numerical') for s,description in enumerate(data['descriptions'],1)]
        decisions=[dict(id='missing-property-appendix',description='The source leaves absolute material and section values to the author appendix. Freeze Q355 E=206000 MPa, nu=0.3, G=E/[2(1+nu)] MPa and density=7850 kg/m3; B1 is 0.3 by 0.6 m. Where B2/B3 are unspecified rectangles, use 0.3 by 0.7 m and 0.35 by 0.8 m respectively, with every A/Iy/Iz/J explicitly supplied. Source-prescribed inertia ratios override these optional rectangle definitions.'),dict(id='connected-stations',description='Point-load and displacement observation stations are connected nodes, without additional planar restraints or masses.'),dict(id='acceptance-pending',description='Source and structural authoring checks do not establish native execution, independent numerical truth or blind input acceptance; all remain pending.')]+data['decisions']
        C.write_case(data['id'],data['models'],data['turns'],data['requests'],{'input-tables.txt':rendered},outputs=outputs,decisions=decisions,source_audit=[dict(field=k,source=v,review='Source reviewed against explicit turn sequence, public appendix, state snapshots, quantity selections and pending acceptance gates.') for k,v in coverage['sourceRequirements'].items()])
        print(data['id'],len(data['turns']),'turns',len(data['models']),'states',sum(map(len,data['requests'])),'quantities')


if __name__=='__main__':
    author()
