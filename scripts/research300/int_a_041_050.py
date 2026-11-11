"""Explicit source-row compilation for INT-041..050. Run with Python 3."""
from int_a_common import *


def base(dimension='2d'):
    m=model(dimension);m['sections']=[section('B1',.30,.60),section('C1',.50,.50)]
    return m


def scaled(m,source,name,factor):
    s=deepcopy(next(s for s in m['sections'] if s['id']==source));s.update(id=name,name=name,type='general');s.pop('shape',None)
    for k in ('Iy','Iz'):s['properties'][k]*=factor
    m['sections'].append(s)


def frame_nodes(m,rows):
    for nid,x,z,rest in rows:node(m,nid,x,z,restraint=rest)


def frame_members(m,rows):
    for eid,a,b,sec in rows:elem(m,eid,a,b,'column' if eid.startswith('c') else 'beam',sec)


def roofload(m,e,q):load(m,type='distributed',element=e,wz=-q,id='q-'+e)


def req_frame():return [quantity('R','ux'),quantity('R','uz'),quantity('A','My'),quantity('A','Fz')]


def requirements(en=False):
    return ('Report current-state Ux and Uz at rightmost upper beam-column joint R, and global My and Rz (=Fz) at left base A; give signed values, locations, units, load case D and turn number. Run OpenSees after every model edit; retain traceable raw results, version and run ID. Ask for unresolved essential input before numerical analysis.' if en else '输出当前状态最右上部梁柱节点R的Ux、Uz及最左柱脚A的全局My、Rz（Fz）；各值注明位置、正负方向、单位、D工况和当前轮次。每次模型修改后重新运行OpenSees，保存版本、运行ID及原始结果映射。必要数据未确定时先澄清，不编造数值。')


def emit(n,states,turns,pubs,decisions=(),requests=None,audit=()):
    cid=f'INT-{n:03}';c,t,s=sources(cid) # Read every complete source row, not a title-derived template.
    default=['The source leaves absolute section/material appendix unspecified. Freeze explicit E=206000 MPa, nu=0.3, G=E/(2*(1+nu)), density=7850 kg/m3; B1=0.30x0.60m, C1=0.50x0.50m solid rectangles; proportional I sections are general sections with unchanged A,J. All values are public inputs, not tuned reference values.']
    write_case(cid,states,turns,requests or [req_frame() for _ in states],pubs,decisions=default+list(decisions),source_audit=list(audit)+[dict(sourceField='task.scenario',check='Exact original turn count, edits, and delayed clarification retained.'),dict(sourceField='model.spec',check=s['spec']),dict(sourceField='task.expectedOutput',check=t['expectedOutput'])])


def author():
    # 041: eccentric spatial square pyramid, one doubled diagonal.
    m=base('3d');m['sections']=[dict(id='A1',name='A1',type='general',properties=dict(A=.01,Iy=1e-5,Iz=1e-5,J=2e-5)),dict(id='A2',name='A2',type='general',properties=dict(A=.02,Iy=1e-5,Iz=1e-5,J=2e-5))]
    for nid,x,y,z in [('A',0,0,0),('B',6,0,0),('C',6,6,0),('D',0,6,0),('P',2,3,3)]:node(m,nid,x,z,y,FIXED if nid!='P' else [False]*3+[True]*3)
    for eid,a,b in [('AB','A','B'),('BC','B','C'),('CD','C','D'),('DA','D','A'),('AP','A','P'),('BP','B','P'),('CP','C','P'),('DP','D','P')]:elem(m,eid,a,b,'truss','A2' if eid=='CP' else 'A1')
    load(m,type='nodal',node='P',fx=20,fz=-30,id='apex')
    p=deepcopy(m);p['load_cases'][0]['loads'][0].pop('fx');p['pendingInput']={'node':'P','horizontalForceMagnitude_kN':20,'globalAxis':None,'positiveSense':None}
    qr=[quantity('P',c) for c in ['ux','uz','uy']]+[quantity('A',c) for c in ['Fx','Fy','Fz']]+[member_quantity('AB','N')]
    out='输出顶点P=(2,3,3)m的Ux、Uz、Uy，左支点A三向反力，以及底边首杆AB的有符号轴力；各值给出位置、方向、单位、D工况及轮次。'
    emit(41,[m],[turn('按附件建立偏心方锥杆系。顶点20kN标为水平但未说明X或Y；另一项为全局Z负向30kN。先澄清所缺方向。'+out,None,'clarify',['input-t1.txt'],['apex.horizontalForce.axis'],['顶点20kN沿全局哪个水平轴和正负方向？']),turn('确认20kN为全局X正向，30kN为全局Z负向。保持偏心几何、四底点平移固定及CP面积2A，用OpenSees分析。'+out,1,'analyze',['input-t2.txt'])],{'input-t1.txt':tables(p,'zh'),'input-t2.txt':tables(m,'zh')},decisions=['A=0.01 m2; CP=0.02 m2. All unused truss rotations fixed only as inactive DOFs; only translations carry truss stiffness. Left support is A=(0,0,0), first base rod AB.'],requests=[qr])

    # 042: two-story triangular prism. Explicit A/B topology, restoring only two diagonals.
    m=base('3d');m['sections']=[dict(id='A1',name='A1',type='general',properties=dict(A=.01,Iy=1e-5,Iz=1e-5,J=2e-5)),dict(id='A2',name='A2',type='general',properties=dict(A=.02,Iy=1e-5,Iz=1e-5,J=2e-5))]
    for j in range(3):
        for nid,x,y in [('A',0,0),('B',4,0),('C',2,2*math.sqrt(3))]:node(m,f'{nid}{j}',x,3*j,y,FIXED if j==0 else [False]*3+[True]*3)
    for j in range(3):
        for a,b in [('A','B'),('B','C'),('C','A')]:elem(m,f'h{a}{b}{j}',f'{a}{j}',f'{b}{j}','truss','A1')
    for j in (1,2):
        for a in ('A','B','C'):elem(m,f'v{a}{j}',f'{a}{j-1}',f'{a}{j}','truss','A2' if j==1 else 'A1')
        for a,b in [('A','B'),('B','C'),('C','A')]:elem(m,f'd{a}{b}{j}',f'{a}{j-1}',f'{b}{j}','truss','A1')
    for a in ('A','B','C'):load(m,type='nodal',node=a+'2',fx=10)
    b=deepcopy(m)
    for e in b['elements']:
        if e['id']=='dAB2':e['nodes']=['B1','A2']
        if e['id']=='dBC2':e['nodes']=['C1','B2']
    # Geometry-dependent reference vectors are recomputed after these explicit replacements.
    b['metadata']['elementReferenceVectors']={}
    qr=[quantity('A2',c) for c in ['ux','uz','uy']]+[quantity('A0',c) for c in ['Fx','Fy','Fz']]+[member_quantity('hAB0','N')]
    out=' Report Ux, Uz, Uy at A2=(0,0,6)m, all three reactions at A0, and signed axial force in first base rod hAB0. Include node/member location, signs, units, case D and turn. Preserve raw OpenSees run evidence for each state.'
    emit(42,[m,b,deepcopy(m)],[turn('Build the two-story triangular prism using connection table A and analyze.'+out,1,attachments=['table-A.txt']),turn('Replace only upper-tier diagonals dAB2 and dBC2 using table B: dAB2 becomes B1-A2; dBC2 becomes C1-B2. Keep every other member, section, restraint and load, then rerun.'+out,2,attachments=['table-B.txt'],changedFields=['/elements/18/nodes','/elements/19/nodes']),turn('Undo only the two diagonal replacements. Restore connection table A exactly and rerun.'+out,3)],{'table-A.txt':tables(m),'table-B.txt':'Connection replacement B (all coordinates m, forces kN). Only dAB2: B1 -> A2 and dBC2: C1 -> B2 change. Both remain section A1, material M1, axial-only. Other records in table A remain active.\n'},decisions=['Source did not provide topology tables A/B. Frozen appendix: each level has triangle AB/BC/CA; each tier has three verticals and three cyclic face diagonals. B reverses two upper face diagonals. Pure-Python assembled axial stiffness rank checks both states before acceptance as authored data; independent native analysis remains pending. A=0.01 m2; lower verticals 2A.'],requests=[qr,qr,qr])

    # 043: asymmetric pin/fix portal.
    m=base();frame_nodes(m,[('A',0,0,PIN),('B',18,0,FIXED),('L',0,7,FREE),('R',18,7,FREE)]);frame_members(m,[('cL','A','L','C1'),('cR','B','R','C1'),('roof','L','R','B1')]);roofload(m,'roof',6)
    b=deepcopy(m)
    for n in b['nodes']:
        if n['id'] in ['L','R']:n['z']=9
    emit(43,[m,b],[turn('建立附件18m跨门架：左柱脚铰、右柱脚固定，屋面高7m，全屋面向下6kN/m。'+requirements(),1,attachments=['input.txt']),turn('仅将两柱高和两屋面端节点标高从7m改为9m；跨度、左铰右固及6kN/m保持，重算。'+requirements(),2,changedFields=['/nodes/2/z','/nodes/3/z','/metadata/elementReferenceVectors/cL/0','/metadata/elementReferenceVectors/cR/0'])],{'input.txt':tables(m,'zh')})

    # 044: contradictory overall dimension; right span point node is genuinely connected.
    m=base();frame_nodes(m,[('A',0,0,FIXED),('B',18,0,FIXED),('C',36,0,FIXED),('L',0,9,FREE),('M',18,9,FREE),('P',27,9,FREE),('R',36,9,FREE)]);frame_members(m,[('cL','A','L','C1'),('cM','B','M','C1'),('cR','C','R','C1'),('roofL','L','M','B1'),('roofRa','M','P','B1'),('roofRb','P','R','B1')])
    for e in ['roofL','roofRa','roofRb']:roofload(m,e,6)
    load(m,type='nodal',node='P',fz=-24,id='hoist')
    emit(44,[m],[turn('The dimension schedule says two bays of 18 m each, while the overall-width note says 30 m. The attached coordinate schedule follows the two-bay dimensions; these statements conflict and neither is designated authoritative yet. Ask which controls before analysis. The roof is 9 m high; retain the 24 kN downward load only at the right-bay midpoint.'+requirements(True),None,'clarify',['input-t1.txt'],['overallWidthVsBays'],['Should the two 18 m bays or the 30 m overall note govern?']),turn('The individual bay dimensions govern: 18+18=36 m overall. Use column lines x=0,18,36 m and the right-bay point load at x=27 m. Analyze.'+requirements(True),1)],{'input-t1.txt':tables(m,extra='Unresolved conflicting dimension note: overall width=30 m; individual bay schedule=18 m+18 m. Coordinates below are the bay-schedule alternative, not a resolution.\n')},decisions=['T1 legitimately contains contradictory geometric records. Coordinates identify the supplied bay-table alternative; they do not designate precedence. No numeric results until user selects the bay schedule.'])

    # 045: unknown roof load units; connected left-column lateral load.
    m=base();frame_nodes(m,[('A',0,0,FIXED),('B',21,0,FIXED),('P',0,3,FREE),('L',0,7.5,FREE),('R',21,7.5,FREE)]);frame_members(m,[('cLa','A','P','C1'),('cLb','P','L','C1'),('cR','B','R','C1'),('roof','L','R','B1')]);roofload(m,'roof',8);load(m,type='nodal',node='P',fx=9,id='column-side')
    p=deepcopy(m);p['load_cases'][0]['loads']=p['load_cases'][0]['loads'][1:];p['pendingRoofLoad']={'member':'roof','downwardMagnitude':8,'unit':None,'loadKind':None}
    pub=tables(p,'zh').replace('线载kN/m；','').replace('分布载荷区间按实际杆长以m计，除非本轮明确待确认该基准。','本轮屋面数值8的单位及荷载种类待确认。')
    emit(45,[m],[turn('21m跨、7.5m高门架，柱脚固定。屋面向下荷载仅写数值8、单位漏写。左柱z=3m节点另有X正向9kN。先确认屋面荷载单位及类型。'+requirements(),None,'clarify',['input-t1.txt'],['roofLoad.unit','roofLoad.kind'],['屋面数值8是何种荷载、单位是什么，是否已经折算？']),turn('确认屋面为已折算的8kN/m线载，按屋面梁实际长度均布向下，直接使用，不再乘受荷宽度。保留左柱9kN。'+requirements(),1,attachments=['input-t2.txt'])],{'input-t1.txt':pub,'input-t2.txt':tables(m,'zh')})

    # 046: replacement of horizontal hoist component, not increment.
    m=base();scaled(m,'C1','C2',1.7);frame_nodes(m,[('A',0,0,FIXED),('B',18,0,FIXED),('C',36,0,FIXED),('L',0,9,FREE),('M',18,9,FREE),('R',36,9,FREE)]);frame_members(m,[('cL','A','L','C1'),('cM','B','M','C2'),('cR','C','R','C1'),('roofL','L','M','B1'),('roofR','M','R','B1')])
    for e in ['roofL','roofR']:roofload(m,e,6)
    load(m,type='nodal',node='M',fx=4.9,fz=-49,id='hoist');b=deepcopy(m);b['load_cases'][0]['loads'][-1]['fx']=-7
    emit(46,[m,b],[turn('Build the two-bay 18+18 m portal in the appendix; the middle column has section C2 with Iy and Iz 1.7 times C1 and the same area. Analyze the roof loads and middle-column top Fx=+4.9 kN, Fz=-49 kN.'+requirements(True),1,attachments=['input.txt']),turn('Replace only the middle-column top X component by -7 kN. Keep Fz=-49 kN, both 6 kN/m roof loads, geometry, supports and section assignments. Rerun.'+requirements(True),2,changedFields=['/load_cases/0/loads/2/fx'])],{'input.txt':tables(m)})

    # 047: left-side mezzanine and independent right stub.
    m=base();frame_nodes(m,[('A',0,0,FIXED),('B',18,0,FIXED),('ML',0,3,FREE),('TL',6,3,FREE),('SR',18,5,FREE),('TR',20,5,FREE),('L',0,7,FREE),('R',18,7,FREE)]);frame_members(m,[('cLa','A','ML','C1'),('cLb','ML','L','C1'),('cRa','B','SR','C1'),('cRb','SR','R','C1'),('roof','L','R','B1'),('mezz','ML','TL','B1'),('stub','SR','TR','B1')])
    for e,q in [('roof',6),('mezz',4),('stub',3)]:roofload(m,e,q)
    b=deepcopy(m)
    for n in b['nodes']:
        if n['id'] in ['ML','TL']:n['z']=4
    emit(47,[m,b],[turn('按附件建立18m跨7m高门架。左柱z=3m向跨内+X悬挑6m夹层梁，向下4kN/m；右柱z=5m向右短挑2m，向下3kN/m；屋面向下6kN/m。'+requirements(),1,attachments=['input.txt']),turn('仅将左夹层的两端ML和TL标高从3m移到4m，柱分段随共节点更新；夹层仍长6m、4kN/m。右短挑z=5m、2m及3kN/m，屋面7m和6kN/m不变。'+requirements(),2,changedFields=['/nodes/2/z','/nodes/3/z','/metadata/elementReferenceVectors/cLa/0','/metadata/elementReferenceVectors/cLb/0'])],{'input.txt':tables(m,'zh')},decisions=['Source says a mezzanine on the left without explicit horizontal direction. Freeze the appendix as extending from the left column x=0 inward to x=6 (not outward); roof and separate right stub are unchanged.'])

    # 048: slope actual-length basis intentionally unavailable on turn 1.
    m=base();frame_nodes(m,[('A',0,0,FIXED),('B',20,0,FIXED),('L',0,6,FREE),('P',20,3,FREE),('R',20,6,FREE),('K',10,8,FREE)]);frame_members(m,[('cL','A','L','C1'),('cRa','B','P','C1'),('cRb','P','R','C1'),('slopeL','L','K','B1'),('slopeR','K','R','B1')]);roofload(m,'slopeL',6);roofload(m,'slopeR',6);load(m,type='nodal',node='P',fx=-8,id='column-side')
    p=deepcopy(m);p['load_cases'][0]['loads']=p['load_cases'][0]['loads'][2:];p['pendingRoofLoads']=[dict(member=e,globalDirection='-Z',magnitude=6,unit='kN/m',lengthBasis=None) for e in ['slopeL','slopeR']]
    pub=tables(p).replace('Distributed load intervals are measured in m along the actual member unless this turn explicitly leaves that basis unresolved.','The roof load length basis is unresolved: actual slope length versus horizontal projection. No roof load resultant or normalized member density has been supplied.')
    emit(48,[m],[turn('Build the 20 m span portal with 6 m eaves and 8 m ridge. Roof loads are globally downward 6 kN/m, but the length basis is unspecified. Ask for that basis. Keep the separate -8 kN global-X load at the right-column z=3 m node.'+requirements(True),None,'clarify',['input-t1.txt'],['roofLoad.lengthBasis'],['Is 6 kN/m per actual sloping member length or per horizontal projected length?']),turn('Use 6 kN/m per actual sloping roof-member length, globally downward. Do not project the load a second time; retain the right-column -8 kN horizontal force. Analyze.'+requirements(True),1,attachments=['input-t2.txt'])],{'input-t1.txt':pub,'input-t2.txt':tables(m)})

    # 049: asymmetric roof geometry followed by right load-only change.
    m=base();scaled(m,'B1','B2',1.4);frame_nodes(m,[('A',0,0,FIXED),('B',24,0,FIXED),('L',0,6,FREE),('R',24,6,FREE),('K',10,8,FREE)]);frame_members(m,[('cL','A','L','C1'),('cR','B','R','C1'),('slopeL','L','K','B1'),('slopeR','K','R','B2')]);roofload(m,'slopeL',4);roofload(m,'slopeR',6)
    b=deepcopy(m);b['nodes'][4]['x']=11;c=deepcopy(b);c['load_cases'][0]['loads'][1]['wz']=-7
    emit(49,[m,b,c],[turn('建立24m跨不对称门架：檐高6m，屋脊(10,8)m；左坡B1、右坡B2且B2的Iy、Iz均为B1的1.4倍。左坡4、右坡6kN/m均按实际坡长全局向下。'+requirements(),1,attachments=['input.txt']),turn('仅将屋脊K从x=10m移到x=11m，z=8m不变；两坡共用同一屋脊，截面、各坡线载强度和柱脚保持，重算。'+requirements(),2,changedFields=['/nodes/4/x','/metadata/elementReferenceVectors/slopeL/2','/metadata/elementReferenceVectors/slopeR/2']),turn('保持新屋脊位置，只把右坡线载改为向下7kN/m；左坡仍4kN/m，重算。'+requirements(),3,changedFields=['/load_cases/0/loads/1/wz'])],{'input.txt':tables(m,'zh')})

    # 050: later clarification must not invalidate or modify T1 state.
    m=base();scaled(m,'C1','C2',.5);frame_nodes(m,[('A',0,0,FIXED),('B',12,0,FIXED),('C',30,0,FIXED),('L',0,6,FREE),('M6',12,6,FREE),('M8',12,8,FREE),('R',30,8,FREE)]);frame_members(m,[('cL','A','L','C1'),('cMa','B','M6','C1'),('cMb','M6','M8','C2'),('cR','C','R','C1'),('roofL','L','M6','B1'),('roofR','M8','R','B1')]);roofload(m,'roofL',5);roofload(m,'roofR',7);b=deepcopy(m);load(b,type='nodal',node='M6',fx=10,id='added-horizontal')
    emit(50,[m,b],[turn('Build the stepped portal: bays 12 and 18 m, roof elevations 6 and 8 m, separate middle-column nodes M6 and M8. The middle-column upper segment has half the Iy and Iz of C1 with the same area. Analyze the 5 and 7 kN/m roof loads.'+requirements(True),1,attachments=['input.txt']),turn('Add a 10 kN horizontal force to the middle-column node. The elevation and horizontal sign have not been specified; ask which node and direction before applying this edit.',None,'clarify',unresolved=['newForce.nodeElevation','newForce.horizontalDirection'],questions=['Should the force act at z=6 m or z=8 m, and in which signed global horizontal direction?'],preservedFields=['/nodes','/elements','/load_cases']),turn('Use node M6 at z=6 m, global +X. Add one +10 kN nodal force there, preserving M8, both column sections and both roof loads. Rerun.'+requirements(True),2,changedFields=['/load_cases/0/loads/2'])],{'input.txt':tables(m)})


if __name__=='__main__':author()
