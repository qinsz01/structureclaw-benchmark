"""Reproduce INT-051..060 from their individual source model and task rows."""
from copy import deepcopy
from int_b_common import *


def split(m,eid,nid,x,z):
    e=next(e for e in m['elements'] if e['id']==eid)
    node(m,nid,x,z)
    end=e['nodes'][1];e['nodes'][1]=nid
    other=deepcopy(e);other['id']=eid+'b';other['nodes']=[nid,end];m['elements'].insert(m['elements'].index(e)+1,other)
    return other['id']


def scale_section(m,original,new,factor):
    s=deepcopy(next(s for s in m['sections'] if s['id']==original))
    s.update(id=new,name=new,type='general');s.pop('shape',None)
    for k in ('Iy','Iz'):s['properties'][k]*=factor
    m['sections']=[x for x in m['sections'] if x['id']!=new]+[s]


def udl(m,q,case='D',where=lambda e:True):
    for e in m['elements']:
        if e['type']=='beam' and where(e):load(m,case,type='distributed',element=e['id'],wz=-q)


def ask_en():
    return 'Report global Ux and Uz at the highest-story rightmost beam-column joint, and global support moment My and vertical reaction Fz at the left base, for every listed case and combination.'


def ask_zh():
    return '按每个明示工况与组合，报告最高层最右梁柱节点全局Ux、Uz，及最左柱脚全局支座弯矩My和竖向反力Fz（Rz）。'


def notes(text):
    return dict(sourceInspection=text,appendixCompletion='Source supplies no complete numerical section/material appendix. Explicit steel E=206000 MPa, nu=0.3, G=E/2.6, rho=7850 kg/m3; base B1=300x600 mm, C1=500x500 mm solid rectangles, unless the case-specific public table overrides. A/Iy/Iz/J are explicit, not engine defaults. UDL uses actual member length; sections are linear elastic engineering inputs, not design-code defaults.',reviewStatus='Author checked source topology, supports, load magnitudes/locations and turn sequence. Independent blind reconstruction and native execution pending.')


def build():
    # Every case reads the exact source row through emit; no source prose is used as a model.
    m=model()
    for n,x,z,r in [('leftBase',0,0,[True]*6),('leftEave',0,6,None),('ridge',9,7.5,None),('rightEave',18,6,None),('rightBase',18,0,[True]*6)]:node(m,n,x,z,restraint=r)
    elem(m,'leftColumn','leftBase','leftEave','column','C1');elem(m,'rightColumn','rightBase','rightEave','column','C1')
    elem(m,'leftSlope','leftEave','ridge');elem(m,'rightSlope','ridge','rightEave')
    udl(m,5);load(m,type='nodal',node='ridge',fz=-12,id='ridge-dead')
    load(m,'W',type='distributed',element='rightSlope',wz=4,id='right-uplift')
    m['load_combinations']=[dict(id='D',factors={'D':1}),dict(id='D+W',factors={'D':1,'W':1})]
    emit('INT-051',[m],[turn('建立18m跨、檐高6m、脊高7.5m门架，柱脚固定。附件给全屋面D向下5kN/m与屋脊D向下12kN；W仅右坡向上4kN/m（全局+Z），组合D及D+W，线载以坡梁实际长度计。合法上拔荷载直接分析。'+ask_zh(),1,attachments=['input-t1.json'])],{'input-t1.json':public_input(m)},notes('18m pitched portal; right-only uplift, separate ridge dead point load and all D/W selections checked. Same-name D case and D combination are deliberately distinct selectors.'))

    m=model()
    for n,x,z,r in [('leftBase',0,0,[True,True,True,True,False,True]),('leftTop',0,7,None),('cut6',6,7,None),('cut16',16,7,None),('rightTop',22,7,None),('rightBase',22,0,[True]*6)]:node(m,n,x,z,restraint=r)
    m['sections'] += [section('B3',.3,.5),section('B4',.35,.8)]
    elem(m,'leftColumn','leftBase','leftTop','column','C1');elem(m,'rightColumn','rightBase','rightTop','column','C1')
    for e,a,b,s in [('roofLeft','leftTop','cut6','B1'),('roofMiddle','cut6','cut16','B2'),('roofRight','cut16','rightTop','B3')]:elem(m,e,a,b,sec=s)
    udl(m,7);m2=deepcopy(m);next(e for e in m2['elements'] if e['id']=='roofMiddle')['section']='B4'
    emit('INT-052',[m,m2],[turn('Build the 22 m span, 7 m high portal. The left base is pinned in-plane and the right base fixed. Three roof segments at X=0/6/16/22 m use B1/B2/B3; each carries 7 kN/m downward. '+ask_en(),1,attachments=['input-t1.json']),turn('Replace only roofMiddle section B2 by the supplied B4 record. Keep both end segments, cuts, loads and supports; recompute. '+ask_en(),2)],{'input-t1.json':public_input(m)},notes('Left pin/right fix, three true constant-section roof elements, cuts 0/6/16/22, 7 kN/m invariant. B3=300x500 and future B4=350x800 mm completed explicitly.'))

    m=frame([0,16],[6]);m['nodes'][0]['restraints']=[True,True,True,True,False,True]
    split(m,'b0-1','roofMid',8,6);udl(m,5);load(m,type='nodal',node='n1-1',fx=12);load(m,type='nodal',node='roofMid',fz=-20)
    emit('INT-053',[m],[turn('边界表见附件：左柱脚铰支、右固定。但文字说明写“左固定、右铰支”。跨16m高6m，屋面5kN/m向下、右柱顶+X 12kN、屋面中点向下20kN。请建立模型并给出结果。'+ask_zh(),None,'clarify',['input-t1.json'],['supports.left/right'],['柱脚以边界表还是文字为准？']),turn('确认以边界表为准：左柱脚面内转角自由、右柱脚固定；其他输入不变。计算。'+ask_zh(),1)],{'input-t1.json':public_input(m,conflictingNarrative='Left base fixed; right base pinned. This conflicts with the boundary table; precedence is unspecified.')},notes('Source intentionally provides conflicting support statements. Initial table preserves left pin/right fix but has no precedence authorization. T2 resolves only that conflict. Roof midpoint is connected by two beam pieces.'))

    m=frame([0,12,27],[7]);split(m,'b0-1','leftMid',6,7)
    m['sections'] += [section('C4',.65,.65)]
    next(e for e in m['elements'] if e['id']=='c1-1')['section']='C2'
    udl(m,4,where=lambda e:e['id'].startswith('b0-'));udl(m,6,where=lambda e:e['id'].startswith('b1-'))
    load(m,type='nodal',node='leftMid',fz=-20,id='equipment-D')
    for i,f in enumerate([5,8,5]):load(m,'W',type='nodal',node=f'n{i}-1',fx=f,id=f'W-{i}')
    m['load_combinations']=[dict(id='D+W',factors={'D':1,'W':1})]
    replacement=[dict(id='W-new-left',type='nodal',node='n0-1',fx=-6,reference_frame='global'),dict(id='W-new-middle',type='nodal',node='n1-1',fx=9,reference_frame='global'),dict(id='W-new-right',type='nodal',node='n2-1',fx=11,fz=-3,reference_frame='global')]
    m2=deepcopy(m);m2['load_cases'][1]['loads']=replacement
    m3=deepcopy(m2);next(e for e in m3['elements'] if e['id']=='c1-1')['section']='C4'
    emit('INT-054',[m,m2,m3],[turn('Build the 12+15 m, 7 m high portal with fixed bases and separate outer-column, middle-column and roof groups. D includes left/right roof 4/6 kN/m downward and the connected left-span midpoint -Z 20 kN. W initially has +X 5/8/5 kN at the three column tops. '+ask_en(),1,attachments=['input-t1.json']),turn('Replace the entire W load list with wind-replacement-t2.json, preserving all D loads and properties. Recompute. '+ask_en(),2,attachments=['wind-replacement-t2.json']),turn('Assign C4 only to the middle column c1-1 and recompute. '+ask_en(),3)],{'input-t1.json':public_input(m),'wind-replacement-t2.json':dict(units=UNITS,case='W',replacementLoads=replacement)},notes('Connected x=6 D point preserved. T2 replacement W list is absent from source appendix: author completes explicit global nodal vectors (-6,0,0), (9,0,0), (11,0,-3) kN; these replace rather than append old W. C4=650x650 mm. Author-defined reporting combination D+W is explicit alongside independent D/W cases.'))

    m=frame([0,6],[3.6,7.2]);scale_section(m,'B1','B2',.7)
    next(e for e in m['elements'] if e['id']=='b0-2')['section']='B2';udl(m,60)
    m2=deepcopy(m)
    for j,f in [(1,10),(2,15)]:load(m2,'W',type='nodal',node=f'n1-{j}',fx=f)
    m2['load_combinations']=[dict(id='D+W',factors={'D':1,'W':1})]
    emit('INT-055',[m,m2],[turn('两层各3.6m、单跨6m框架；10kN/m²按6m受荷宽已折算成D线载60kN/m，仅施加一次。屋面B2的Iy/Iz为一层B1的0.7倍且面积相同，柱C1。按附件计算。'+ask_zh(),1,attachments=['input-t1.json']),turn('新增W：一层右节点+X 10kN，屋面右节点+X 15kN，新增组合D+W。保留D=60kN/m及所有属性。'+ask_zh(),2)],{'input-t1.json':public_input(m,areaLoadContext={'areaIntensity':10,'areaUnit':'kN/m2','tributaryWidthM':6,'alreadyConvertedLineIntensity':60,'applyLineLoadOnce':True})},notes('Exact floor-specific stiffness ratio 0.7 with equal area; custom general section avoids inconsistent rectangular dimensions. All gravity stays 60 kN/m once. T2 changes only W and combination.'))

    m=frame([0,24],[12]);split(m,'c0-1','leftEquipment',0,6);udl(m,36)
    load(m,type='nodal',node='leftEquipment',fx=14,id='equipment-side');load(m,type='nodal',node='n1-1',fx=10,id='crane-horizontal');load(m,type='nodal',node='n1-1',fz=-98,id='crane-vertical')
    m2=deepcopy(m);next(l for l in m2['load_cases'][0]['loads'] if l['id']=='crane-vertical')['fz']=-117.6
    emit('INT-056',[m,m2],[turn('Build the industrial frame, span 24 m and height 12 m. Roof gravity is 36 kN/m. The right column top has crane +X 10 kN and -Z 98 kN; the left column has a connected node at Z=6 m with equipment +X 14 kN. '+ask_en(),1,attachments=['input-t1.json']),turn('Increase the crane load by 20% and give the revised response.',None,'clarify',unresolved=['craneLoad.componentScope'],questions=['Does the 20% increase apply to both crane components or only the vertical component?'],priorState=1),turn('Increase only the right-top vertical crane force from 98 to 117.6 kN downward. Keep its +X 10 kN, the separate left equipment +X 14 kN, and roof 36 kN/m unchanged. Recompute. '+ask_en(),2)],{'input-t1.json':public_input(m)},notes('Crane components separate IDs, equipment connected at Z=6. T2 is a later unresolved edit, with no new state. Only one vertical-force field changes at T3.'))

    m=frame([0,6,12],[3.6,7.2,10.8]);udl(m,10,where=lambda e:e['id'].startswith('b1-'))
    for j,f in [(1,10),(2,15),(3,20)]:load(m,type='nodal',node=f'n2-{j}',fx=f,id=f'lateral-{j}')
    p=public_input(m)
    for l in p['load_cases'][0]['loads']:
        if l['id']=='lateral-1':l['fx']=20
        if l['id']=='lateral-3':l['fx']=10
    p['conflictingNarrative']='Text states +X story forces 10,15,20 kN bottom to top; this table states 20,15,10. No priority is specified.'
    emit('INT-057',[m],[turn('三层各3.6m、两跨各6m。只有各层第二跨x=6～12m梁有向下10kN/m，第一跨无竖向线载。侧力文字规定从低到高+X 10、15、20kN，附件表却是20、15、10kN，作用在各层右节点。请计算。'+ask_zh(),None,'clarify',['input-t1.json'],['storyLateralForce.order'],['侧力以文字顺序还是表格为准？']),turn('确认以文字为准：从低到高10、15、20kN，其他输入不变。'+ask_zh(),1)],{'input-t1.json':p},notes('Initial attachment intentionally contains reversed force table, not silently resolved state. T2 resolves order. Three and only three second-span beams carry 10 kN/m.'))

    m=frame([0,6],[4]);udl(m,6);load(m,type='nodal',node='n1-1',fx=50,id='horizontal')
    m2=deepcopy(m);next(l for l in m2['load_cases'][0]['loads'] if l['id']=='horizontal')['fx']=80
    emit('INT-058',[m,m2],[turn('Analyze the fixed-base frame, 6 m span and 4 m height, roof -Z 6 kN/m and right-top +X 50 kN. '+ask_en(),1,attachments=['input-t1.json']),turn('Replace the right-top +X 50 kN force with +X 80 kN. Preserve all gravity and other inputs; recompute. '+ask_en(),2)],{'input-t1.json':public_input(m)},notes('One field 50→80; no accumulation. Gravity -6 remains.'))

    m=frame([0,6],[4.5]);scale_section(m,'C1','C2',1.3);next(e for e in m['elements'] if e['id']=='c1-1')['section']='C2';udl(m,48)
    p=public_input(m);p['load_cases'][0]['loads']=[]
    p['unresolvedRoofLoading']=dict(areaLoad=8,areaUnit='kN/m2',lineLoad=48,lineUnit='kN/m',tributaryWidthM=6,relationship=None,direction='global -Z',members=['b0-1'])
    emit('INT-059',[m],[turn('跨6m高4.5m固定脚框架，左右柱面积相同但右柱Iy/Iz为左柱1.3倍。屋面输入列出8kN/m²、受荷宽6m及48kN/m，但未说明是否同一荷载。请计算。'+ask_zh(),None,'clarify',['input-t1.json'],['roofLoads.relationship'],['48kN/m是否由8kN/m²乘6m折算的同一荷载？'],acceptedAlternative='若说明已给数据足以唯一确定二者为同一荷载，可直接采用48kN/m一次；不得叠加。'),turn('确认48kN/m就是8kN/m²×6m的同一荷载，只施加一次，其他输入保持。'+ask_zh(),1)],{'input-t1.json':p},notes('Initial public load relationship is null and contains both original intensities without author resolution. Source permits a justified unique inference; explicit acceptance alternative records it. Final gravity only 48 kN/m; right-column inertia ratio 1.3 retained.'))

    m=frame([0,5.4,11.4],[3.6,7.2]);scale_section(m,'C1','C2',1.8)
    for e in m['elements']:
        if e['id'].startswith('c1-'):e['section']='C2'
    udl(m,10);udl(m,8,'L');m['load_combinations']=[dict(id='1.2D+1.4L',factors={'D':1.2,'L':1.4})]
    m2=deepcopy(m)
    for j,f in [(1,10),(2,15)]:load(m2,'W',type='nodal',node=f'n2-{j}',fx=f)
    m2['load_combinations'].append(dict(id='1.2D+1.4L+W',factors={'D':1.2,'L':1.4,'W':1}))
    emit('INT-060',[m,m2],[turn('Build the two-story frame with 3.6 m story heights, 5.4+6 m spans, D=10 and L=8 kN/m downward on every beam, and combination 1.2D+1.4L. Middle-column Iy/Iz are 1.8 times outer columns with equal area. '+ask_en(),1,attachments=['input-t1.json']),turn('Add W: +X 10 kN at the first-story right node and +X 15 kN at the second-story right node, both X=11.4 m. Add combination 1.2D+1.4L+W and retain the old combination, D, L and properties. Recompute. '+ask_en(),2)],{'input-t1.json':public_input(m)},notes('Unequal spans 5.4+6, middle-column-only ratio 1.8. Old 1.2D+1.4L combination is preserved with original D/L; new W and combination added.'))


if __name__=='__main__':build()
