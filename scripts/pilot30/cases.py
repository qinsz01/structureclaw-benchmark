"""Twelve new, explicitly bounded tasks; source facts and authored assumptions differ."""
from copy import deepcopy
import math


def model(nodes,elements,loads=None):
    return {'schema_version':'2.2.0','unit_system':'SI',
        'coordinate_system':{'semantics':'global-z-up','version':1,'dimension':'2d','plane':'xz',
                             'dof_order':['ux','uy','uz','rx','ry','rz']},
        'nodes':nodes,'elements':elements,
        'materials':[{'id':'S','name':'Explicit elastic steel','type':'steel','E':206000.,'G':79230.76923076923,'nu':.3,'rho':7850.}],
        'sections':[{'id':'C','name':'column','type':'custom','properties':{'A':.024,'Iy':.0003,'Iz':.0001,'J':.00004}},
                    {'id':'B','name':'beam','type':'custom','properties':{'A':.016,'Iy':.00015,'Iz':.00006,'J':.00002}}],
        'load_cases':[{'id':'D','type':'dead','loads':loads or []}], 'load_combinations':[],
        'analysis_control':{k:False for k in ['self_weight','rigid_floor','p_delta','rigid_offsets','construction_stage']}}


def node(name,x,z,fixed=False,vertical=False):
    return {'id':name,'x':x,'y':0.,'z':z,
            'restraints':[fixed,True,fixed or vertical,True,fixed,True]}


def member(name,a,b,kind='beam',section='B'):
    return {'id':name,'nodes':[a,b],'type':kind,'material':'S','section':section}


def rect(m,section,b,h):
    p={'A':b*h,'Iy':b*h**3/12,'Iz':h*b**3/12,'J':b*h**3*(1/3-.21*(b/h)*(1-b**4/(12*h**4)))}
    next(s for s in m['sections'] if s['id']==section)['properties']=p


def q(nid,component,selection=None):
    return {'id':f'{nid}-{component}', 'selection':selection or {'kind':'case','id':'D'},
            'location':{'kind':'node','id':nid},'component':component,
            'unit':'m' if component.startswith('u') else 'rad' if component.startswith('r') else 'kN.m' if component.startswith('M') else 'kN',
            'tolerance':{'absolute':1e-8,'relative':1e-6}}


def turn(m,instruction,requests=None,kind='static',**extra):
    return {'model':deepcopy(m),'instruction':instruction,'kind':kind,
            'requests':requests or [], **extra}


def pv():
    # Public coordinate precision is the actual reference input, not hidden math.
    slope=math.tan(math.radians(15));z=lambda x:round(1.5+slope*x,6)
    m=model([node('A',0,0,True),node('B',2.6,0,True),node('P',0,z(0)),node('M',1.3,z(1.3)),node('Q',2.6,z(2.6))],
        [member('CP','A','P','column','C'),member('CQ','B','Q','column','C'),member('R1','P','M'),member('R2','M','Q')])
    for e in m['elements'][:2]: e['releases']={'j':{'ry':True}}
    rect(m,'C',.06,.1);rect(m,'B',.06,.12)
    m['load_cases']=[{'id':'D','type':'dead','loads':[{'type':'distributed','element':r,'wz':-.35*3.4} for r in ['R1','R2']]},
       {'id':'W','type':'wind','loads':[{'type':'distributed','element':r,'wx':-.8*3.4*math.sin(math.radians(15)),
                                     'wz':.8*3.4*math.cos(math.radians(15))} for r in ['R1','R2']]},
       {'id':'Q','type':'live','loads':[{'type':'distributed','element':r,'wz':-.7*3.4} for r in ['R1','R2']]}]
    m['load_combinations']=[{'id':'UP','factors':{'D':1,'W':1}},{'id':'DOWN','factors':{'D':1,'Q':1}}]
    return m


def cold():
    xs=[0,11.805,23.61,39.715,55.82]
    ns=[node('A'+str(i),x,0,True) for i,x in enumerate([0,23.61,55.82])]
    ns += [node('R'+str(i),x,31.2) for i,x in enumerate(xs)]
    es=[member('C'+str(i),'A'+str(i),'R'+str(j),'column','C') for i,j in enumerate([0,2,4])]
    es += [member('B'+str(i),'R'+str(i),'R'+str(i+1)) for i in range(4)]
    m=model(ns,es);rect(m,'C',.5,1.2);rect(m,'B',.4,.9)
    def dist(ids,w): return [{'type':'distributed','element':i,'wz':w} for i in ids]
    m['load_cases']=[{'id':'D','type':'dead','loads':dist(['B0','B1','B2','B3'],-2.*7.5)},
        {'id':'SL','type':'other','loads':dist(['B0','B1'],-.5*7.5)},
        {'id':'SR','type':'other','loads':dist(['B2','B3'],-.5*7.5)},
        {'id':'L','type':'live','loads':dist(['B0','B1','B2','B3'],-.5*7.5)}]
    m['load_combinations']=[{'id':'LEFT','factors':{'D':1,'SL':1}},
        {'id':'RIGHT','factors':{'D':1,'SR':1}},{'id':'LIVE','factors':{'D':1,'L':1}}]
    return m


def oscillator(two=False):
    m=model([node('A',0,0,True),node('F1',0,3,vertical=True)], [member('C1','A','F1','column','C')])
    m['nodes'][1]['mass']=10.
    if two:
        m['nodes'].append({**node('F2',0,6.8,vertical=True),'mass':7.})
        m['elements'].append(member('C2','F1','F2','column','C'))
    m['analysis_control'].update(mass_source='nodal',mass_directions=['x'])
    return m


SOURCES={
 'S02':{'url':'https://www.yjk.cn/article/1869/','title':'Y-PV 刚性支架算例，李焘，2023',
        'facts':'双桩双立柱，倾角15°，纵向间距3400mm，上部平面图两排间距2600mm。',
        'adaptation':'仅截取一个平面支架，底部刚固、柱顶弯曲释放；高度、弹性定截面、荷载强度和约束均为本题明确编制。不复现桩土、节点设计、完整空间支撑或原工程规范验算。'},
 'S03':{'url':'https://www.yjk.cn/article/1892/','title':'单层钢结构冷库结构设计，柴浩，2023',
        'facts':'柱中心跨距23.61m与32.21m，檐口31.2m，部分纵向间距7.5m，附加恒载2.0kPa、雪/活载各0.5kPa，雪活载互斥。',
        'adaptation':'明确编制平顶定截面二维裸框架及固定柱脚，按7.5m受荷宽度折算。原工程的坡度、变截面、单拉支撑、温度及完整三维设计不在此子问题内。截面、组合系数和响应限值是本题分析设定，非现行规范结论。'},
}


def definitions():
    cases=[]
    def add(cid,title,family,turns,source=None,schemes=None,visual=False,notes=''):
        cases.append({'id':cid,'title':title,'family':family,'engine':'OpenSees','origin':'new',
                      'turns':turns,'sourceId':source,'schemes':schemes,'visual':visual,'notes':notes})
    # A midspan node is an actual connected observation point, not a hinge.
    m=model([node('A',0,0,vertical=True),node('M',3,0),node('B',6,0,vertical=True)],
        [member('L','A','M'),member('R','M','B')],[{'type':'distributed','element':i,'wz':-10} for i in ['L','R']])
    m['nodes'][0]['restraints'][0]=True
    m['elements'][0]['releases']={'i':{'ry':True}};m['elements'][1]['releases']={'j':{'ry':True}}
    add('P30-STD-007','弯曲端释放与连通跨中节点','STD',
        [turn(m,'两个物理端铰接，跨中转角连续；按题定弯曲释放分析，不报告未定义的端节点转角。',[q('M','uz'),q('A','Fz'),q('B','Fz')])])
    m=oscillator()
    add('P30-STD-008','显式节点质量与第一周期','STD',[turn(m,'求第一阶周期、频率和X向有效质量；不得再叠加密度质量。',kind='modal',
        parameters={'analysisType':'modal','numModes':1,'direction':'x'})])
    m=pv();sel={'kind':'combination','id':'UP'}
    add('P30-STD-009','光伏平面支架的法向风压传递','STD',
        [turn(m,'按source-basis.json和荷载传递约定，将法向面压一次折算为实际斜梁线载。分析UP组合。',
              [q('M','ux',sel),q('M','uz',sel),q('A','Fx',sel),q('B','Fz',sel)])],source='S02',
        notes='Public facts give pressures and tributary width; candidate must derive line vectors.')
    m=cold();schemes=[{'id':'A','section':'B','b':.4,'h':.75},{'id':'B','section':'B','b':.4,'h':.9},{'id':'C','section':'B','b':.4,'h':1.05}]
    add('P30-STD-010','冷库横向分析子模型的有限截面方案比较','STD',
        [turn(m,'分别计算给定三种梁截面方案的LEFT、RIGHT、LIVE组合；按公开位移约束筛选，并选总体积最小的可行方案。',kind='scheme',
              constraint={'nodes':['R1','R3'],'component':'uz','absoluteLimit':.018},schemeSelections=['LEFT','RIGHT','LIVE'])],
        source='S03',schemes=schemes)
    # Explicit support motion is a prescribed displacement, not an extra force.
    m=model([node('A',0,0,vertical=True),node('C',4,0,vertical=True),node('B',9,0,vertical=True)],
        [member('L','A','C'),member('R','C','B')],[{'type':'displacement','node':'C','uz':-.006}])
    m['nodes'][0]['restraints'][0]=True
    add('P30-MM-007','连续梁支座变位图的约束重建','MM',
        [turn(m,'仅据geometry.png识别几何和支承，根据位移表施加已知支座变位。无其他荷载。',[q('C','uz'),q('A','Fz'),q('C','Fz'),q('B','Fz')])],visual=True)
    m=oscillator(True)
    add('P30-MM-008','两段柱型支架的图纸与质量表模态重建','MM',
        [turn(m,'从图纸与质量表重建模型，求前两阶周期、有效质量并交付F1/F2的X向振型；符号和归一化可不同。',kind='modal',
              parameters={'analysisType':'modal','numModes':2,'direction':'x'},requireShapes=True)],visual=True)
    m=cold();sel={'kind':'combination','id':'LEFT'}
    add('P30-MM-009','冷库横向子问题的偏雪载图表联合','MM',
        [turn(m,'从几何图和来源约定重建裸框架，按给定受荷宽度一次折算雪载；LEFT不含活载。',
            [q('R1','uz',sel),q('R3','uz',sel),q('A0','Fz',sel),q('A2','Fz',sel)])],source='S03',visual=True)
    m=pv();schemes=[{'id':'A','section':'B','b':.06,'h':.12},{'id':'B','section':'B','b':.07,'h':.14},{'id':'C','section':'B','b':.08,'h':.16}]
    add('P30-MM-010','光伏斜梁方案图表与挠度约束','MM',
        [turn(m,'从图纸重建同一支架，在DOWN组合下比较完整目录三种梁截面；选满足位移约束且总体积最小的方案。',kind='scheme',
              constraint={'nodes':['M'],'component':'uz','absoluteLimit':.001},schemeSelections=['DOWN'])],source='S02',schemes=schemes,visual=True)
    m=model([node('A',0,0,True),node('T',0,3)], [member('C1','A','T','column','C')],[{'node':'T','fz':-10}])
    m['load_cases'].append({'id':'W','type':'wind','loads':[{'node':'T','fx':8}]})
    m['load_combinations']=[{'id':'C','factors':{'D':1.2,'W':1}}]
    m['analysis_control'].update(self_weight=True,self_weight_case_id='D')
    sel={'kind':'combination','id':'C'};qs=[q('T','ux',sel),q('T','uz',sel),q('A','Fz',sel),q('A','My',sel)]
    ts=[turn(m,'自动自重只归属D；计算C组合，不能给W重复加自重。',qs)]
    sec=next(s for s in m['sections'] if s['id']=='C');sec['properties']['A']*=1.25
    ts.append(turn(m,'只把柱截面积A增加25%，其余刚度常数按题定独立属性保持，自动自重随A更新。',qs))
    sec['properties']['A']/=1.25;m['load_cases'][1]['loads'][0]['fx']=11
    ts.append(turn(m,'恢复最初面积A；同时只将W的Fx改为11kN，保留D及自重归属。',qs))
    add('P30-INT-007','自动自重归属与局部属性修订','INT',ts)
    m=oscillator(True);dt=.02;motion=[round(.025*math.sin(i*dt*7)*math.sin(math.pi*i/60)**2,10) for i in range(62)]
    par={'analysisType':'time_history','timeStep':dt,'duration':1.2,'dampingRatio':.05,'direction':'x',
         'groundMotion':motion,'groundMotionUnit':'g','monitorNodeIds':['F1','F2'],'monitorElementIds':['C1','C2'],'monitorSupportNodeIds':['A']}
    ts=[turn(m,'激励数据文件的加速度单位尚未确定。先询问groundMotionUnit，不计算或猜测。',kind='clarify',
             clarificationFields=['parameters:groundMotionUnit'],parameters={k:v for k,v in par.items() if k!='groundMotionUnit'})]
    ts.append(turn(m,'确认激励单位为g。采用给定记录、步长与阻尼，执行线弹性时程。该记录是显式编制的验证激励，不是真实地震记录。',kind='transient',parameters=par))
    par=deepcopy(par);par['groundMotionUnit']='m/s2';par['groundMotion']=[v*9.80665*1.25 for v in motion]
    ts.append(turn(m,'将同一激励强度提高25%，此次明确用m/s2给数据。模型、质量、步长和阻尼保持。',kind='transient',parameters=par))
    add('P30-INT-008','时程激励单位澄清与强度修订','INT',ts)
    m=cold();sel={'kind':'combination','id':'LEFT'};qs=[q('R1','uz',sel),q('R3','uz',sel),q('A0','Fz',sel)]
    ts=[turn(m,'按来源与明确的定截面子问题建立模型，计算LEFT。',qs)]
    for load in m['load_cases'][1]['loads']:load['wz']*=1.2
    ts.append(turn(m,'只将SL雪载增加20%，保留D、SR、L。',qs))
    rect(m,'B',.4,1.0);ts.append(turn(m,'只改梁截面为B=0.4m、H=1.0m矩形，按公开公式重算其A/I/J，保留增雪。',qs))
    for load in m['load_cases'][1]['loads']:load['wz']/=1.2
    ts.append(turn(m,'只撤销第2轮增雪，保留第3轮梁截面。',qs))
    add('P30-INT-009','冷库子模型的局部荷载与选择性撤销','INT',ts,source='S03')
    m=pv();schemes=[{'id':'A','section':'B','b':.06,'h':.12},{'id':'B','section':'B','b':.07,'h':.14},{'id':'C','section':'B','b':.08,'h':.16}]
    ts=[]
    for i,limit in enumerate([.001,.0006,.001,.0008,.0006,.001]):
        if i==1:
            for load in m['load_cases'][2]['loads']:load['wz']*=1.15
        if i==3:
            for load in m['load_cases'][2]['loads']:load['wz']/=1.15
        instructions=['比较三方案，按当前限值选择最轻可行者。','只将Q提高15%，并采用本轮更严格限值。',
            '保留增载，只恢复初始位移限值。','只撤销第2轮增载，采用本轮限值，其他输入不变。',
            '只收紧限值，模型和载荷保持。','只恢复初始限值；保留最后确认的荷载和方案目录。']
        ts.append(turn(m,instructions[i],kind='scheme',constraint={'nodes':['M'],'component':'uz','absoluteLimit':limit},schemeSelections=['DOWN']))
    add('P30-INT-010','光伏子问题的六轮方案与限值更新','INT',ts,source='S02',schemes=schemes)
    return cases
