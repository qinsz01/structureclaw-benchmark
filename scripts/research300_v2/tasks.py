"""Concrete task construction, declared difficulty and stateful issued changes."""
from copy import deepcopy
from collections import Counter
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
from models import FAMILIES,VARIANTS,build_model,variant_info,topology_fingerprint
from references import reference,module

ROOT=Path(__file__).resolve().parents[2]
PILOT=module('v2_pilot_cases',ROOT/'scripts/pilot30/cases.py')
OLD=Path(os.environ['RESEARCH300_LEGACY_ROOT']).resolve() if os.environ.get('RESEARCH300_LEGACY_ROOT') else next(
    (p for p in [ROOT/'corpora/research300-v2-v1/legacy-source',ROOT/'.bench-work/section-diversity-v1-final-20261027/corpora/research-300/cases'] if p.is_dir()),
    ROOT/'corpora/research300-v2-v1/legacy-source')
ROUNDS={'L1':2,'L2':3,'L3':4,'L4':6}
NAMES={'beam':'连续与支承梁系','frame':'多跨裸框架','truss':'平面轴力桁架','space_frame':'空间裸框架','space_truss':'空间轴力杆系','mixed':'梁柱与双向轴力杆混合体系'}
def read(p):return json.loads(p.read_text())
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def resize(model,sid,width_factor=1.,depth_factor=1.,properties_factor=None):
    s=next(s for s in model['sections'] if s['id']==sid)
    if properties_factor is not None:
        s.pop('shape',None)
        for k in ['A','Iy','Iz','J']:
            if k in s['properties']:s['properties'][k]*=properties_factor
        return
    shape=s.get('shape');assert shape and shape['kind']=='rectangular'
    b=round(shape['B']/1000*width_factor,6);h=round(shape['H']/1000*depth_factor,6)
    large,small=max(b,h),min(b,h);shape.update(B=b*1000,H=h*1000)
    s['properties']={'A':b*h,'Iy':b*h**3/12,'Iz':h*b**3/12,'J':large*small**3*(1/3-.21*small/large*(1-small**4/(12*large**4)))}


def apply_order(model,order,initial):
    for op in order['operations']:
        if op['op']=='scale-load-case':
            case=next(c for c in model['load_cases'] if c['id']==op['caseId'])
            for l in case['loads']:
                if l.get('type')=='displacement':continue
                for k in ['fx','fy','fz','mx','my','mz','wx','wy','wz','wx_start','wx_end','wy_start','wy_end','wz_start','wz_end']:
                    if k in l:l[k]*=op['factor']
        elif op['op']=='restore-load-case':
            idx=next(i for i,c in enumerate(model['load_cases']) if c['id']==op['caseId'])
            model['load_cases'][idx]=deepcopy(next(c for c in initial['load_cases'] if c['id']==op['caseId']))
        elif op['op']=='resize-section':resize(model,op['sectionId'],op.get('widthFactor',1),op.get('depthFactor',1),op.get('propertiesFactor'))
        elif op['op']=='scale-nodal-masses':
            for n in model['nodes']:
                if n.get('mass'):n['mass']*=op['factor']
        elif op['op']=='restore-nodal-masses':
            ns={n['id']:n for n in initial['nodes']}
            for n in model['nodes']:
                if ns[n['id']].get('mass'):n['mass']=ns[n['id']]['mass']
        elif op['op']=='set-constraint-limit':pass
        else:raise ValueError(op)


def requested(model,selections,special=False):
    free=sorted([n for n in model['nodes'] if not all(n['restraints'][i] for i in [0,2])],key=lambda n:(n['z'],n['x'],n['y'],n['id']))
    if not free:free=model['nodes'][1:]
    top=free[-1];middle=free[len(free)//2];support=next(n for n in model['nodes'] if n['restraints'][2])
    vertical=[n for n in free if not n['restraints'][2]]
    vertical_target=vertical[len(vertical)//2] if vertical else top
    vertical_other=vertical[-1] if vertical else middle
    stations=[({'kind':'node','id':top['id']},'ux'),({'kind':'node','id':vertical_target['id']},'uz'),
              ({'kind':'node','id':support['id']},'Fx'),({'kind':'node','id':support['id']},'Fz')]
    if vertical_other['id']!=vertical_target['id']:stations.append(({'kind':'node','id':vertical_other['id']},'uz'))
    imposed={l['node'] for c in model['load_cases'] for l in c['loads'] if l.get('type')=='displacement' and l.get('uz')}
    known={(loc['id'],comp) for loc,comp in stations}
    for nid in sorted(imposed):
        if (nid,'uz') not in known:stations.append(({'kind':'node','id':nid},'uz'))
    if model['coordinate_system']['dimension']=='3d':
        lateral=next((n for n in reversed(free) if not n['restraints'][1]),top)
        lateral_support=next((n for n in model['nodes'] if n['restraints'][1]),support)
        stations.extend([({'kind':'node','id':lateral['id']},'uy'),({'kind':'node','id':lateral_support['id']},'Fy')])
    if not special:
        for e in model['elements'][:2]:stations.append(({'kind':'member','id':e['id'],'positionM':0.,'side':'right'},'N' if e['type'] in ['truss','brace'] else 'M2'))
        if model['coordinate_system']['dimension']=='3d':
            beam=next((e for e in model['elements'] if e['type']=='beam'),None)
            if beam:stations.append(({'kind':'member','id':beam['id'],'positionM':0.,'side':'right'},'T'))
    qs=[]
    for sel in selections:
        for loc,comp in stations:
            unit='m' if comp.startswith('u') else 'kN.m' if comp.startswith('M') or comp=='T' else 'kN'
            qs.append({'id':sel['kind']+':'+sel['id']+':'+loc['id']+':'+comp,'selection':deepcopy(sel),'location':deepcopy(loc),
                       'component':comp,'unit':unit,'tolerance':{'absolute':1e-8 if unit=='m' else 1e-6,'relative':1e-6}})
    return qs


def derived(requests,level):
    if level not in ['L3','L4']:return []
    displacement=[q['id'] for q in requests if q['component']=='uz']
    return [{'id':'signed-governing-vertical-response','operation':'max_abs','operands':displacement,'unit':'m','tiePolicy':'any'}]


def original_specs():
    rows=[]
    for fi,f in enumerate(FAMILIES):
        for v in range(VARIANTS):
            family=['STD','MM','INT'][(v+fi)%3];model=build_model(f,v)
            rows.append({'family':family,'origin':'original','modelFamily':f,'variant':v,'model':model,'baseModelGroup':f'factory:{f}:{v}',
                         'title':NAMES[f]+f'：构造{v+1:02}','structuralVariation':variant_info(f,v)['structuralVariation']})
    for family in ['STD','MM','INT']:
        chosen=sorted([r for r in rows if r['family']==family],key=lambda r:(len(r['model']['nodes'])+len(r['model']['elements'])/3,r['modelFamily'],r['variant']))
        assert len(chosen)==70
        for i,r in enumerate(chosen):r['level']='L1' if i<15 else 'L2' if i<50 else 'L3'
    # Thirty different planar frames/mixed systems carry dynamic tasks. Their
    # mass distributions are explicit; distinct topology remains measured.
    dynamic=sorted([r for r in rows if r['modelFamily'] in ['frame','mixed'] and r['level']!='L1'],key=lambda r:(r['variant'],r['modelFamily']))
    for i,r in enumerate(dynamic[:30]):
        r['analysis']='modal' if i<20 else 'transient';r['title']+='：显式节点质量'+('模态' if i<20 else '线弹性时程')
        m=r['model'];m['analysis_control'].update(mass_source='nodal',mass_directions=['x'])
        for j,n in enumerate(m['nodes']):
            if not n['restraints'][0]:n['mass']=round(4+.35*(j%7)+.1*(r['variant']%5),3)
        # Loads remain as supplied schedules but are inactive for this explicitly
        # requested modal/uniform-base-excitation analysis.
    specials={'release':'P30-STD-007','settlement':'P30-MM-007','selfweight':'P30-INT-007'}
    prototypes={c['id']:c for c in PILOT.definitions()}
    for family in ['STD','MM','INT']:
        pool=[r for r in rows if r['family']==family and r['level']=='L2' and not r.get('analysis') and r['modelFamily'] in ['beam','truss']]
        assert len(pool)>=3
        for r,(feature,pid) in zip(pool,specials.items()):
            m=deepcopy(prototypes[pid]['turns'][0]['model']);r.update(model=m,special=feature,baseModelGroup='special:'+feature,
                title={'release':'端部弯曲释放与连续观测节点','settlement':'连续梁已知支座变位','selfweight':'指定工况自动自重与荷载保持'}[feature])
            for c in m['load_cases']:
                for l in c['loads']:l.setdefault('type','nodal')
            if not any(c['id']=='Q' for c in m['load_cases']):
                loads=[{'type':'nodal','node':m['nodes'][1]['id'],'my':2.}] if feature=='settlement' else deepcopy(m['load_cases'][0]['loads'])
                m['load_cases'].append({'id':'Q','type':'live','loads':loads})
            if not any(c['id']=='W' for c in m['load_cases']):m['load_cases'].append({'id':'W','type':'wind','loads':[{'type':'nodal','node':m['nodes'][-1]['id'],'fx':3.}]})
            m['load_combinations']=[{'id':'SERVICE','factors':{'D':1,'Q':1}},{'id':'REVERSE','factors':{'D':1,'W':-1}}]
    # Ten additional repair tasks; five more reside in the real-source L4 set.
    for family,n in [('STD',4),('MM',3),('INT',3)]:
        candidates=[r for r in rows if r['family']==family and r['level']=='L3' and not r.get('analysis')]
        for r in candidates[:n]:r['audit']=1;r['title']+='：模型审查与重算'
    for i,r in enumerate(rows):
        if r.get('analysis') or r.get('special') or r['level']=='L1':continue
        m=r['model'];beams=[e for e in m['elements'] if e['type']=='beam']
        if beams and i%4==0:
            e=beams[0];ns={n['id']:n for n in m['nodes']};L=math.dist([ns[e['nodes'][0]][k] for k in 'xyz'],[ns[e['nodes'][1]][k] for k in 'xyz'])
            m['load_cases'][1]['loads'].append({'id':'Q-interior','type':'point','element':e['id'],'position':round(.37*L,6),'reference_frame':'global','fz':-7.5})
            r['additionalFeature']='interior-point-load'
        elif beams and i%4==1:
            e=beams[0];e['rotation_angle']=90.;r['additionalFeature']='section-axis-rotation'
    return rows


def commercial_specs():
    inventory=[]
    for f in sorted(OLD.glob('*/contract.json')):
        c=read(f)
        if c['plannedEngine'] in ['PKPM','YJK']:inventory.append((f.parent,c,read(f.parent/'independent-reference.json')))
    selected=[];used=set()
    for family in ['INT','MM','STD']:
        for engine in ['PKPM','YJK']:
            pool=sorted([x for x in inventory if x[1]['plannedEngine']==engine and x[0].name not in used],key=lambda x:(x[1]['family']!=family,x[0].name))
            assert len(pool)>=5
            for j,(folder,c,truth) in enumerate(pool[:5]):
                level='L1' if j<(3 if engine=='PKPM' else 2) else 'L2'
                used.add(folder.name);states=[]
                for state in truth['states']:
                    m=read(folder/c['modelStates'][state['state']-1]);qs=state['quantities']
                    # Use qualified node quantities, retaining exact same-engine
                    # values/tolerances. Selection count is bounded for latency.
                    selections=list(dict.fromkeys(q['selection']['kind']+':'+q['selection']['id'] for q in qs))
                    chosen=selections[0];available=[q for q in qs if q['selection']['kind']+':'+q['selection']['id']==chosen]
                    ns={n['id']:n for n in m['nodes']};free=next(n['id'] for n in m['nodes'] if not all(n['restraints'][:3]));base=next(n['id'] for n in m['nodes'] if all(n['restraints'][:3]))
                    subset=[deepcopy(q) for q in available if q['location']['kind']=='node' and
                        (q['location']['id']==free and q['component'] in ['ux','uy','uz'] or q['location']['id']==base and q['component'] in ['Fx','Fy','Fz','Mx','My','Mz'])]
                    if len(subset)<4:subset=[deepcopy(q) for q in available if q['location']['kind']=='node'][:8]
                    derived_requests=[]
                    if level=='L2':
                        # A genuine multi-response decision is added without
                        # replacing native reference values with beam theory.
                        candidates=available
                        groups=[[q for q in candidates if q['component']==comp] for comp in ['uz','ux','uy','Fz','Fx','Fy','N','M2','M3']]
                        groups += [[q for q in candidates if q['unit']==unit] for unit in ['m','kN','kN.m','kN*m']]
                        decision=next((g[:6] for g in groups if len(g)>=2),None)
                        assert decision is not None,(folder.name,'needs a multi-response decision')
                        ids={q['id'] for q in subset}
                        subset.extend(deepcopy(q) for q in decision if q['id'] not in ids)
                        derived_requests=[{'id':'signed-response-governor','operation':'max_abs','operands':[q['id'] for q in decision],
                                           'unit':decision[0]['unit'],'tiePolicy':'any'}]
                    assert subset
                    binding={'legacyId':folder.name,'legacyState':state['state'],'modelSha256':digest(folder/c['modelStates'][state['state']-1]),
                        'referenceSha256':digest(folder/'independent-reference.json'),'sourceHash':truth['sourceHash'],'engine':engine,
                        'scope':'Exact same physical state, selected previously qualified quantities; public delivery reorganized.'}
                    states.append({'model':m,'requests':subset,'nativeReferenceBinding':binding,'derived':derived_requests})
                selected.append({'family':family,'origin':'legacy-commercial','engine':engine,'level':level,'title':folder.name+'商业原生模型重组',
                    'legacyId':folder.name,'states':states,'model':states[0]['model'],'baseModelGroup':'legacy:'+folder.name,'modelFamily':'space_frame'})
    assert len(selected)==30;return selected


def json_patch(before,after,path=''):
    if type(before)!=type(after):return [{'op':'replace','path':path,'value':deepcopy(after)}]
    if isinstance(before,dict):
        out=[]
        for k in sorted(before.keys()-after.keys()):out.append({'op':'remove','path':path+'/'+k})
        for k in sorted(after):
            p=path+'/'+k.replace('~','~0').replace('/','~1')
            out.extend(json_patch(before[k],after[k],p) if k in before else [{'op':'add','path':p,'value':deepcopy(after[k])}])
        return out
    if isinstance(before,list):
        out=[p for i,(a,b) in enumerate(zip(before,after)) for p in json_patch(a,b,path+'/'+str(i))]
        out.extend({'op':'remove','path':path+'/'+str(i)} for i in range(len(before)-1,len(after)-1,-1))
        out.extend({'op':'add','path':path+'/'+str(i),'value':deepcopy(after[i])} for i in range(len(before),len(after)))
        return out
    return [] if before==after else [{'op':'replace','path':path,'value':deepcopy(after)}]


def selectors(model,level):
    if level=='L1':return [{'kind':'case','id':'D'}]
    combos=[{'kind':'combination','id':c['id']} for c in model['load_combinations']]
    return ([{'kind':'case','id':'D'}]+combos)[:2 if level=='L2' else 3]


def make_turns(case):
    count=ROUNDS[case['level']] if case['family']=='INT' else 1
    if case['origin']=='legacy-commercial':
        out=[];previous=None
        for i in range(count):
            state=case['states'][min(i,len(case['states'])-1)];m=deepcopy(state['model'])
            turn={**deepcopy(state),'kind':'static' if previous!=m else 'query','engine':case['engine'],
                'instruction':'按本轮签发资料建立裸框架，使用指定商业引擎计算所列带符号响应。结构化交付即可。' if i==0 else '按本轮局部修订单更新；未变更输入保持。若本轮仅查询，复用前轮真实作业并重新报告指定结果。'}
            if i:turn['changeOrder']={'schemaVersion':1,'schema':'json-patch','operations':json_patch(previous,m)}
            if i==count-1 and i and turn['kind']=='query' and not turn['derived']:
                qs=turn['requests'];vertical=[q['id'] for q in qs if q['component']=='uz']
                if vertical:turn['derived']=[{'id':'signed-current-vertical-envelope','operation':'max_abs','operands':vertical,'unit':'m','tiePolicy':'any'}]
            turn['reportIds']=[q['id'] for q in turn['requests']];out.append(turn);previous=deepcopy(m)
        return out
    initial=deepcopy(case['model']);model=deepcopy(initial);kind=case.get('analysis','scheme' if case.get('schemes') else 'static');out=[]
    primary=next((s['id'] for s in model['sections'] if s['id']=='B' and any(e['section']=='B' for e in model['elements'])),model['elements'][0]['section'])
    limit=case.get('constraint',{}).get('absoluteLimit');base_limit=limit
    for i in range(count):
        ops=[];instruction='依据签发图表和约定重建物理模型，执行指定分析并交付带符号结果、单位及真实作业标识。'
        if i:
            dynamic=kind in ['modal','transient']
            if i==1:
                changed_case='D' if case['level']=='L1' else 'Q'
                ops=[{'op':'scale-nodal-masses','factor':1.2}] if dynamic else [{'op':'scale-load-case','caseId':changed_case,'factor':1.2}]
                instruction='仅将全部显式节点质量增加20%，保留截面、连接和所有其他输入。' if dynamic else f'仅将{changed_case}内的机械荷载增大20%，保留其他荷载、连接、支承、材料和截面。'
            elif i==2:
                sec=next(s for s in model['sections'] if s['id']==primary)
                op={'op':'resize-section','sectionId':primary,'widthFactor':1.,'depthFactor':1.08} if sec.get('shape',{}).get('kind')=='rectangular' else {'op':'resize-section','sectionId':primary,'propertiesFactor':1.12}
                if kind=='scheme':
                    limit=base_limit*.8;ops=[{'op':'set-constraint-limit','absoluteLimit':limit}];instruction='仅将当前位移限值收紧为签发值，保留此前增载和完整方案目录。'
                else:ops=[op];instruction='仅按修订单更新指定截面；保留上一轮已更新的荷载/质量及其余构件。'
            elif i==3:
                if case['level']=='L4':ops=[{'op':'scale-load-case','caseId':'D','factor':1.1}];instruction='仅将D内机械荷载增加10%，保留Q增载以及最近截面/限值。'
                else:
                    ops=[{'op':'restore-nodal-masses','fromTurn':'t1'}] if dynamic else [{'op':'restore-load-case','caseId':'Q','fromTurn':'t1'}]
                    instruction='只撤销第2轮质量/荷载修改，保留第3轮截面修改，重新分析。'
            elif i==4:ops=[{'op':'restore-load-case','caseId':'Q','fromTurn':'t1'}];instruction='只撤销第2轮Q增载，保留第4轮D增载和其他最近输入。'
            elif i==5:
                if kind=='scheme':limit=base_limit;ops=[{'op':'set-constraint-limit','absoluteLimit':limit}];instruction='只恢复初始位移限值；保留最近确认的D/Q和方案目录，再选最优可行方案。'
                else:instruction='本轮仅查询当前已计算状态的带符号控制结果；不修改模型，不新增求解。'
            apply_order(model,{'operations':ops},initial)
        turn={'model':deepcopy(model),'kind':'query' if i==5 and kind=='static' else kind,'engine':'OpenSees','instruction':instruction,'derived':[]}
        if i:turn['changeOrder']={'schemaVersion':1,'operations':ops}
        if kind in ['static','query']:
            turn['requests']=requested(model,selectors(model,case['level']),bool(case.get('special')));turn['derived']=derived(turn['requests'],case['level'])
        elif kind=='modal':turn.update(parameters={'analysisType':'modal','numModes':2,'direction':'x'},requireShapes=True,requests=[])
        elif kind=='transient':
            dt=.01;duration=1.2;seed=case.get('variant',0)
            motion=[round(.02*(1+.05*(seed%5))*math.sin((4+.15*(seed%7))*j*dt)*math.sin(math.pi*j*dt/duration)**2,10) for j in range(round(duration/dt)+2)]
            nodes=sorted([n for n in model['nodes'] if n.get('mass')],key=lambda n:(n['z'],n['x']))
            turn.update(parameters={'analysisType':'time_history','timeStep':dt,'duration':duration,'dampingRatio':.03+.005*(seed%5),'direction':'x',
                'groundMotion':motion,'groundMotionUnit':'g','monitorNodeIds':[n['id'] for n in nodes],
                'monitorElementIds':[model['elements'][0]['id']],'monitorSupportNodeIds':[n['id'] for n in model['nodes'] if n['restraints'][0]]},
                monitorNode=nodes[-1]['id'],requests=[])
        elif kind=='scheme':turn.update(schemes=deepcopy(case['schemes']),constraint={**deepcopy(case['constraint']),'absoluteLimit':limit},schemeSelections=['SERVICE','REVERSE'],requests=[])
        if i==0 and case.get('audit'):
            bad=deepcopy(model);paths=['/materials/0/E'];bad['materials'][0]['E']*=.8
            if case['audit']>=3:
                paths+=['/analysis_control/self_weight'];bad['analysis_control']['self_weight']=not bad['analysis_control']['self_weight']
                if case['family']=='MM':
                    # Review excerpt may contain wrong load values, but must
                    # never supply the geometry/restraints being tested in MM.
                    found=False
                    for ci,lc in enumerate(bad['load_cases']):
                        for li,load in enumerate(lc['loads']):
                            for key in ('fx','fy','fz','mx','my','mz','wx','wy','wz'):
                                if isinstance(load.get(key),(int,float)) and load[key]:
                                    load[key]*=1.25;paths.append(f'/load_cases/{ci}/loads/{li}/{key}');found=True;break
                            if found:break
                        if found:break
                    assert found,'Audit needs an explicit nonzero mechanical load'
                else:paths+=['/nodes/0/restraints'];bad['nodes'][0]['restraints']=[False]*6
            turn['expectedIssuePaths']=paths
            if case['family']=='MM':turn['suspectExcerpt']={k:bad[k] for k in (['materials','analysis_control','load_cases'] if case['audit']>=3 else ['materials','analysis_control'])}
            else:turn['suspectModel']=bad
            turn['instruction']+=' 附件审查稿存在物理输入错误；以正式图表为准定位每项错误的JSON路径与原因，修复后求解。'
        out.append(turn)
    return out


def difficulty_evidence(case):
    level=case['level'];e=['明确资料到物理模型；必须真实求解并正确读取指定有符号输出']
    if level!='L1':e+=['多个指定工况/组合、显式质量动力分析或跨响应主控判定；输入变换与分析选择均需正确']
    if level in ['L3','L4']:e+=['多工况的带符号控制量及主控身份，或模态/时程质量、记录与输出语义联合核对']
    if case['family']=='MM':e+=[('工程原文事实辅助图纸/DXF与清单联合重建；不提供完整坐标表，但原文可能给出部分尺寸与支承事实' if case.get('sourceId') else '完整几何/支承由图纸或DXF签发，清单不含完整坐标表')]
    if case['family']=='INT':e+=[f'{ROUNDS[level]}轮逐步签发，后续仅变更单；保留未修改项'+('并执行选择性撤销' if level in ['L3','L4'] else '')]
    if case.get('sourceId'):e+=['工程原文事实与作者补充设定分开；将面压/受荷宽度一次转换或采用明确节点荷载']
    if case.get('schemes'):e+=['穷举3个合法截面方案及全部组合；检查位移可行性和材料体积最优性，允许无可行方案']
    if case.get('audit'):e+=[f'审查并定位{case["audit"]}类物理输入错误，修复并实际重算']
    if case.get('additionalFeature'):e+=[case['additionalFeature']]
    return e
