"""Explicit STD-051..060 source-based inputs and output requests; no result values."""
from std_b_common import (
    model, node, elem, load, section, frame, beams_udl, Requests, emit, source,
)


PLANE_DISP = ('ux', 'uz', 'ry')
PLANE_FORCE = ('N', 'V3', 'M2')
PIN = [True, True, True, True, False, True]


def steel(m, sections=None):
    """Freeze the source's missing numerical property appendix explicitly."""
    m['sections'] = sections or [section('B1', .30, .60), section('C1', .50, .50)]
    return m


def roof(m, xs, z, section_ids, prefix='roof'):
    """Add real connected roof observation/section-boundary nodes."""
    ids = []
    for i, x in enumerate(xs):
        nid = f'{prefix}-n{i}'
        node(m, nid, x, z)
        ids.append(nid)
    members = []
    for i, sec in enumerate(section_ids):
        members.append(elem(m, f'{prefix}-{i+1}', ids[i], ids[i+1], sec=sec))
    return ids, members


def planar_portal(xs, z, secs):
    m = steel(model())
    tops, members = roof(m, xs, z, secs)
    node(m, 'base-L', xs[0], 0, restraint=[True]*6)
    node(m, 'base-R', xs[-1], 0, restraint=[True]*6)
    elem(m, 'column-L', 'base-L', tops[0], kind='column', sec='C1')
    elem(m, 'column-R', 'base-R', tops[-1], kind='column', sec='C1')
    return m, tops, members


def output_nodes(req, ids, selections, components=PLANE_DISP):
    for selection in selections:
        for nid in ids:
            req.node(nid, components, selection)


def output_members(req, ids, selections, components=PLANE_FORCE):
    for selection in selections:
        for eid in ids:
            req.ends(eid, components, selection)


def output_supports(req, selections):
    for selection in selections:
        req.supports(selection)


def finish(number, m, prompt, req, decisions, *, interactions=()):
    row, task, original_model = source(number)
    assert row['sourceRequirements']['task.scenario'] == task['scenario']
    assert row['sourceRequirements']['model.topologyKey'] == original_model['topologyKey']
    en = row['language'] == '英文'
    physical = (
        'The source plan left material and section appendices unspecified. The supplied appendix freezes '
        'Q355 steel with E = 206000 MPa, nu = 0.30, G = E/[2(1+nu)] and density = 7850 kg/m^3. '
        'Sections are solid rectangles: B is the local-y width and H the local-z depth. '
        'A, Iy, Iz and J are explicitly tabulated; use these properties, with Euler-Bernoulli bending '
        '(no shear deformation). Every member uses M1. Unless a case-specific decision below states '
        'otherwise, beam B1 is 0.30 m by 0.60 m and column C1 is 0.50 m by 0.50 m. '
        'Planar local x points from the first node to the second, local y = global +Y, '
        'local z = local x cross local y. In-plane member forces are N, V3 and M2. '
        'Report in-plane translations ux and uz and rotation ry when a displacement vector is requested. '
        'Member forces are signed section resultants at the limiting cut specified in output-requests.json. '
        'The additional midpoint nodes are connected through split members, with the same section '
        'and line-load intensity on both parts. All joints are rigid except the explicitly declared support release.\n'
        if en else
        '源规划未给定材料及截面数值，现将属性附表明确冻结：Q355钢，E=206000 MPa，'
        'nu=0.30，G=E/[2(1+nu)]，密度7850 kg/m^3。实心矩形截面，B为局部y方向宽度、'
        'H为局部z方向高度；A、Iy、Iz、J采用附表明示值。采用Euler-Bernoulli弯曲，不计剪切变形；'
        '全部构件材料M1。除下列逐题说明另有规定外，梁B1宽0.30m、高0.60m；柱C1为0.50m方形。'
        '平面杆局部x由首节点指向末节点，局部y为全局+Y，局部z=x叉乘y；平面内力分量为N、V3、M2。'
        '未指定分量的节点位移向量报告ux、uz及转角ry；杆件内力为output-requests.json指定侧的有符号截面合力。'
        '跨中观测点通过分段构件真实接入，分段保持原截面和线载强度。除明确支座释放外，全部节点刚接。\n'
    )
    appendix = physical + '\n' + '\n'.join(decisions)
    notes = [
        'Missing source material/section appendix completed with explicit solid-rectangle steel properties; '
        'this is an author decision, not a recovered source value or a numerical reference.',
        *decisions,
    ]
    emit(number, m, prompt, req, notes=notes,
         extra_attachments={'input-decisions.txt': appendix}, interactions=interactions)


def case_051():
    m = steel(model())
    for nid, x, z in [('base-L',0,0),('eave-L',0,6),('ridge',9,7.5),
                      ('eave-R',18,6),('base-R',18,0)]:
        node(m, nid, x, z, restraint=[True]*6 if nid.startswith('base') else None)
    elem(m,'column-L','base-L','eave-L','column','C1')
    elem(m,'slope-L','eave-L','ridge',sec='B1')
    elem(m,'slope-R','ridge','eave-R',sec='B1')
    elem(m,'column-R','base-R','eave-R','column','C1')
    for eid in ['slope-L','slope-R']:
        load(m,'D',type='distributed',element=eid,wz=-6)
    load(m,'W',type='distributed',element='slope-R',wz=8)
    m['load_combinations']=[dict(id='C0',factors={'D':1}),dict(id='C1',factors={'D':1,'W':1})]
    req=Requests(m)
    output_nodes(req,['ridge'],['C0','C1'])
    output_supports(req,['C0','C1'])
    output_members(req,['slope-R'],['C0','C1'])
    finish(51,m,
        '使用OpenSees建立18m跨对称双坡门架。两柱脚固定；檐高6m，屋脊在x=9m、z=7.5m。'
        'D在两坡全长施加全局-Z向6kN/m；W仅在右坡全长施加全局+Z向8kN/m，均按实际坡长计。'
        '分别分析C0=D和C1=D+W。逐组合报告屋脊ux、uz、ry，两个柱脚Fx、Fz、My，'
        '以及右坡在屋脊端和右檐端的N、V3、M2。保持正负号、截面侧及组合标签；'
        '右坡构件方向为ridge到eave-R。材料、截面和轴约定见公开附表。', req,
        ['屋面梁采用B1，柱采用C1。位移向量补充约定为ux、uz、ry；右坡端力明确为平面内N、V3、M2，'
         '输出位置覆盖其两端。均布载荷按坡长，不按水平投影折算。'])


def case_052():
    m,tops,members=planar_portal([0,5,11,17,22],7,['B1','B2','B2','B3'])
    m['sections']=[section('B1',.30,.80),section('B2',.30,.60),
                   section('B3',.30,.70),section('C1',.50,.50)]
    for eid in members: load(m,type='distributed',element=eid,wz=-6)
    req=Requests(m)
    output_nodes(req,[tops[1],tops[2],tops[3]],['D'])
    req.member('roof-1',5,PLANE_FORCE,side='left')
    req.member('roof-2',0,PLANE_FORCE,side='right')
    req.member('roof-3',6,PLANE_FORCE,side='left')
    req.member('roof-4',0,PLANE_FORCE,side='right')
    req.supports()
    finish(52,m,
        'Use OpenSees to analyze a 22 m single-bay portal with a horizontal roof at z = 7 m '
        'and two fixed column bases. The roof has three piecewise constant sections: B1 over '
        'x = 0–5 m, B2 over x = 5–17 m, and B3 over x = 17–22 m. Apply a global downward '
        '6 kN/m load to the entire roof in case D. The x = 11 m midpoint is a connected '
        'observation node splitting B2 into two identical segments. Report ux, uz and ry '
        'at x = 5, 11 and 17 m; N, V3 and M2 immediately on both sides of each section '
        'boundary at x = 5 and 17 m; and Fx, Fz and My at both column bases. Include a '
        'section-segmentation table showing each roof segment, x limits and assigned section. '
        'Use the piecewise constant properties and rigid joints in the public appendices.', req,
        ['B1 is 0.30 m wide by 0.80 m deep, B2 is 0.30 m by 0.60 m, B3 is 0.30 m by '
         '0.70 m, and C1 is 0.50 m square. These are explicit missing-appendix choices.',
         'roof-n1 and roof-n3 are shared section-boundary nodes, with no release. roof-n2 '
         'at x = 11 m is connected to roof-2 and roof-3. Both sides of each property '
         'boundary are separately requested using member-end limiting cuts.'],
        interactions=['Provide the roof section-segmentation table: roof-1, x 0–5 m, B1; '
                      'roof-2, x 5–11 m, B2; roof-3, x 11–17 m, B2; roof-4, x 17–22 m, B3.'])


def case_053():
    m,tops,_=planar_portal([0,16],6,['B1'])
    next(n for n in m['nodes'] if n['id']=='base-L')['restraints']=PIN.copy()
    load(m,type='distributed',element='roof-1',wz=-5)
    load(m,type='nodal',node=tops[-1],fx=20)
    req=Requests(m)
    output_nodes(req,tops,['D'])
    req.node('base-L',('ry',))
    req.supports()
    finish(53,m,
        '使用OpenSees分析16m跨、6m高的平屋面门架。左柱脚约束X/Z平移、绕Y转动自由；'
        '右柱脚固定。屋面全跨施加全局-Z向5kN/m，右柱顶施加全局+X向20kN，均属工况D。'
        '报告左右柱顶ux、uz、ry，左柱脚自由转角ry，以及两个柱脚Fx、Fz、My。'
        '按附表逐项保留两侧不同约束，梁柱节点刚接。',req,
        ['屋面梁B1，左右柱C1；左柱脚仅平面转角ry自由，其My反力也必须报告以检查铰支。'
         '平面外自由度依二维约定约束，不形成空间结构。'])


def case_054():
    m=steel(frame([0,12,27],[7]))
    m['sections']=[section('B1',.30,.70),section('C-outer',.45,.60),section('C-middle',.60,.60)]
    for e in m['elements']:
        if e['type']=='column': e['section']='C-middle' if e['id']=='c1-1' else 'C-outer'
    beams_udl(m,6)
    for nid in ['n0-1','n2-1']: load(m,'W',type='nodal',node=nid,fx=10)
    m['load_combinations']=[dict(id='C0',factors={'D':1}),dict(id='C1',factors={'D':1,'W':1})]
    req=Requests(m)
    selections=['D','W','C0','C1']
    output_nodes(req,['n0-1','n1-1','n2-1'],selections)
    output_supports(req,selections)
    output_members(req,[e['id'] for e in m['elements']],selections)
    finish(54,m,
        'Use OpenSees to analyze a one-story portal with two unequal spans of 12 m and '
        '15 m, height 7 m and all three column bases fixed. Assign three distinct section '
        'groups: outer columns C-outer, middle column C-middle and roof beams B1. '
        'D applies 6 kN/m downward to both roof spans. W applies +X 10 kN at each of '
        'the two outer column tops, with no lateral force at the middle top. Keep D and W '
        'separate and define C0 = D and C1 = D + W. Report ux, uz and ry at all column tops, '
        'Fx, Fz and My at every base, and N, V3 and M2 at both ends of all two beams and '
        'all three columns, for D, W, C0 and C1. Include the member-group assignment '
        'table and case/combination IDs and factors.',req,
        ['The missing appendix is completed with B1 = 0.30 m by 0.70 m, C-outer = '
         '0.45 m by 0.60 m, and C-middle = 0.60 m square. B is local-y width and H '
         'is local-z depth, including for vertical columns.',
         'The unspecified representative beam/column end-force set is frozen to all '
         'five physical members. D and W are also reported to make combination indexing explicit.'],
        interactions=['Report the member-group table (b0-1 and b1-1: B1; c0-1 and c2-1: '
                      'C-outer; c1-1: C-middle) and selections D, W, C0 = D, C1 = D + W.'])


def case_055():
    m=steel(frame([0,6],[3.6,7.2]));beams_udl(m,60)
    req=Requests(m)
    output_nodes(req,[f'n{i}-{j}' for j in [1,2] for i in [0,1]],['D'],('ux','uz'))
    for i in [0,1]:
        for j in [1,2]: req.drift(f'n{i}-{j-1}',f'n{i}-{j}',('ux','uz'))
    req.supports()
    finish(55,m,
        '使用OpenSees建立两层单跨钢框架，跨6m，两层层高各3.6m，柱脚固定。'
        '每层面载10kN/m²按6m受荷宽度已折算为梁线载60kN/m；工况D仅在每层梁上'
        '施加全局-Z向60kN/m。分别报告每层左、右梁柱节点ux和uz，左右柱列每层'
        '相对于下一层同列节点的有符号位移差Δux和Δuz（首层以固定柱脚为下节点），'
        '以及两柱脚Fx、Fz、My。每个节点独立响应；楼层无刚性平移耦合。',req,
        ['梁B1、柱C1；层间位移差定义为同列上节点减下节点，单位m，X和Z分量均列出；'
         '它不是层间位移角。面载说明仅用于交代60kN/m的来源，不另施加面载。'])


def case_056():
    m,tops,members=planar_portal([0,12,24],12,['B1','B1'])
    m['sections']=[section('B1',.40,1.20),section('C1',.60,.80)]
    for eid in members: load(m,type='distributed',element=eid,wz=-36)
    load(m,type='nodal',node=tops[-1],fx=10,fz=-98)
    req=Requests(m)
    output_nodes(req,tops,['D']);req.supports();req.ends('column-R',('M2',))
    finish(56,m,
        'Use OpenSees to analyze a single-bay industrial frame with span 24 m, roof '
        'height 12 m and both column bases fixed. Case D applies global downward '
        '36 kN/m over the roof and one crane-equivalent nodal force at the right column '
        'top with Fx = +10 kN and Fz = -98 kN. The 36 kN/m line load is already converted '
        'from a 1.5 kN/m² source roof pressure over 24 m tributary width. Report ux, uz and '
        'ry at both column tops and at the connected roof midpoint (x = 12 m, z = 12 m), '
        'Fx, Fz and My at both bases, and M2 at both ends of the right column. Use the '
        'full properties and member directions in the public appendix.',req,
        ['The unspecified heavy-frame sections are frozen as beam B1 = 0.40 m wide by '
         '1.20 m deep and column C1 = 0.60 m by 0.80 m. The public section properties '
         'define the physical stiffness; these values are author-completed inputs.',
         'Only the converted 36 kN/m roof load enters the model. Its two 12 m segments '
         'share a connected midpoint, and the 98/10 kN nodal force acts only at roof-n2.'])


def case_057():
    m=steel(frame([0,6,12],[3.6,7.2,10.8]));beams_udl(m,10)
    for j,force in enumerate([10,15,20],1): load(m,'W',type='nodal',node=f'n2-{j}',fx=force)
    m['load_combinations']=[dict(id='C1',factors={'D':1,'W':1})]
    req=Requests(m)
    selections=['D','W','C1']
    for selection in selections:
        for i in [0,1,2]:
            for j in [1,2,3]: req.drift(f'n{i}-{j-1}',f'n{i}-{j}',('ux',),selection)
    output_supports(req,selections)
    output_members(req,[f'c{i}-1' for i in [0,1,2]],selections,('M2',))
    finish(57,m,
        '使用OpenSees分析三层两跨钢框架：两跨各6m，三层各高3.6m，全部柱脚固定。'
        'D对每层每跨梁施加全局-Z向10kN/m；W仅对右柱线一、二、三层节点分别施加'
        '全局+X向10、15、20kN。分别求D、W和C1=D+W。报告每层三条柱线节点ux、'
        '同柱线上层减下层的有符号Δux（首层以下部柱脚为基准）、三个柱脚Fx/Fz/My，'
        '及首层三根柱每根两端的M2。保留逐层逐列索引及独立工况/组合标签。',req,
        ['梁B1、柱C1；“下层柱”明确为第一层c0-1、c1-1、c2-1，分别报告两端弯矩。'
         '层间位移差为位移差而非层间位移角，三条柱线各自计算，不设刚性楼板。'])


def case_058():
    m=steel(frame([0,6],[4]));load(m,type='nodal',node='n1-1',fx=50)
    req=Requests(m)
    output_nodes(req,['n0-1','n1-1'],['D'],('ux',))
    req.ends('b0-1',PLANE_FORCE)
    for nid in ['n0-0','n1-0']: req.node(nid,('Fx','My'))
    finish(58,m,
        'Use OpenSees to analyze a rigid-jointed one-story steel frame with span 6 m, '
        'height 4 m and both column bases fixed. Case D has only one nodal load: +X '
        '50 kN at the right roof joint n1-1. The two roof joints retain independent '
        'degrees of freedom. Report ux at each column top, N, V3 and M2 at both '
        'ends of roof beam b0-1, and horizontal shear reaction Fx and bending reaction '
        'My at both column bases. Use the complete geometry and properties in the appendices.',req,
        ['Beam B1 is 0.30 m by 0.60 m and columns C1 are 0.50 m square. The single '
         'static case is named D as a case label even though its only load is lateral. '
         'There is no gravitational load or roof diaphragm.'])


def case_059():
    m=steel(frame([0,6],[2.25,4.5]))
    m['sections']=[section('B1',.30,.60),section('T1',.25,.40),section('C1',.50,.50)]
    next(e for e in m['elements'] if e['id']=='b0-1')['section']='T1'
    roof_beam=next(e for e in m['elements'] if e['id']=='b0-2')
    roof_beam['nodes']=['n0-2','roof-mid']
    node(m,'roof-mid',3,4.5)
    elem(m,'b0-2-right','roof-mid','n1-2',sec='B1')
    for eid in ['b0-2','b0-2-right']: load(m,type='distributed',element=eid,wz=-48)
    req=Requests(m)
    output_nodes(req,[f'n{i}-{j}' for j in [1,2] for i in [0,1]]+['roof-mid'],['D'],('ux','uz'))
    req.ends('b0-1',PLANE_FORCE);req.supports()
    finish(59,m,
        '使用OpenSees分析单层单跨钢框架：跨6m、屋面高4.5m，两柱脚固定；在z=2.25m'
        '增设全跨水平连系梁，两端与柱刚接。两柱在连系梁节点处分段，连系梁无外荷载但参与刚度。'
        '屋面8kN/m²按6m受荷宽度已折算为48kN/m；D仅对屋面全跨施加全局-Z向48kN/m。'
        '报告屋面两端和连系梁两端ux/uz、接入屋面梁的跨中节点ux/uz、连系梁两端N/V3/M2，'
        '以及柱脚Fx/Fz/My。屋面跨中由两段同截面梁连接，所有连接均为刚接。',req,
        ['屋面B1宽0.30m高0.60m，连系梁T1宽0.25m高0.40m，柱C1为0.50m方形。'
         'z=2.25m是柱上真实连接高度，不代表增加建筑楼层；不加载连系梁。'
         '屋面荷载合计288kN，不重复施加原面载。'])


def case_060():
    m=steel(frame([0,5.4,11.4],[3.6,7.2]));beams_udl(m,10);beams_udl(m,8,'L')
    m['load_combinations']=[dict(id='C1',factors={'D':1.2,'L':1.4})]
    req=Requests(m)
    selections=['D','L','C1']
    output_nodes(req,[f'n{i}-{j}' for j in [1,2] for i in [0,1,2]],selections)
    output_supports(req,selections)
    output_members(req,[e['id'] for e in m['elements'] if e['type']=='beam'],selections,('M2',))
    finish(60,m,
        'Use OpenSees to analyze a two-story steel frame with 3.6 m story heights and '
        'two unequal spans of 5.4 m and 6.0 m. All three column bases are fixed. The '
        'geometry/member tables in the public input replace the source drawing. D applies '
        'global downward 10 kN/m and L applies global downward 8 kN/m to every beam on '
        'both floors as separate load cases. Define C1 = 1.2D + 1.4L. Report ux, uz and '
        'ry at every beam-column joint on each floor, Fx, Fz and My at all column bases, '
        'and M2 at both ends of all four floor beams, separately for D, L and C1. '
        'Retain the original case loads and the explicit combination factors.',req,
        ['Beam B1 is 0.30 m by 0.60 m and columns C1 are 0.50 m square. The unspecified '
         'representative beam-end set is frozen to every beam (b0-1, b1-1, b0-2, b1-2), '
         'both ends. The combined line-load intensity is 23.2 kN/m on each beam, computed '
         'from 1.2*10 + 1.4*8; this is an input-combination identity, not a solved result.'])


def main():
    for build in [case_051,case_052,case_053,case_054,case_055,
                  case_056,case_057,case_058,case_059,case_060]:
        build()


if __name__=='__main__':
    main()
