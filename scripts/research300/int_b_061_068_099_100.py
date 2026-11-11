"""Source-specific models and interaction sequences for the remaining INT-B cases."""
from int_b_common import *
from int_b_051_060 import split, scale_section, udl, ask_en, ask_zh, notes


def build():
    m=frame([0,4.5,12],[3.6,7.8])
    m['materials'][0].update(name='Elastic steel E200000',E=200000,G=200000/2.6)
    m2=deepcopy(m['materials'][0]);m2.update(id='M2',name='First-story beam steel',E=210000,G=210000/2.6);m['materials'].append(m2)
    for e in m['elements']:
        if e['type']=='beam':
            j=int(e['id'].split('-')[-1]);load(m,type='distributed',element=e['id'],wz=-8 if j==1 else -12)
            if j==1:e['material']='M2'
    p=public_input(m)
    for n in p['nodes']:
        if n['z']>3.6:n['z']=None
    p['heightStatements']={'storyHeightsM':[3.6,4.2],'roofElevationHeaderM':4.2,'precedence':None}
    emit('INT-061',[m],[turn('两跨4.5、7.5m，层高表为3.6、4.2m，但另一文字写屋顶总标高4.2m。附件将屋顶节点Z留空，待冲突解决。一层梁E=210000MPa，其余E=200000MPa，所有材料完整；一层梁向下8、二层12kN/m。请分析。'+ask_zh(),None,'clarify',['input-t1.json'],['geometry.roofElevation'],['屋顶总标高应按层高累加还是按4.2m总高文字？']),turn('确认屋顶标高7.8m；基础0m、一层3.6m。保持两跨4.5、7.5m、各层材料和荷载。计算。'+ask_zh(),1)],{'input-t1.json':p},notes('Source exact E grouping 210000 first-floor beams versus 200000 all other members. Initial roof coordinates withheld while both contradictory source statements retained; resolution supplies 7.8 only in T2.'))

    m=frame([0,6,12],[3.6,6.9]);m['nodes']=[n for n in m['nodes'] if n['id']!='n2-2'];m['elements']=[e for e in m['elements'] if 'n2-2' not in e['nodes']]
    split(m,'b1-1','equipment',9,3.6);udl(m,10);load(m,type='nodal',node='equipment',fz=-18)
    emit('INT-062',[m],[turn('Analyze the complete listed setback frame directly. The lower story has two 6 m spans; only the left upper span exists. Story heights are 3.6 and 3.3 m. Every actual beam carries 10 kN/m downward. A connected midpoint node at (9,0,3.6) m on the lower right beam carries an additional 18 kN downward. The upper right beam and column do not exist. '+ask_en(),1,attachments=['input-t1.json'])],{'input-t1.json':public_input(m,outputJoint='n1-2 at (6,0,6.9) m; highest real beam-column joint, not the lower-story rightmost node.')},notes('Upper-right node, beam and column removed; no orphaned elements. Lower right midpoint connects two beam pieces and receives 18 kN. Highest actual right joint is n1-2, not nonexistent n2-2.'))

    m=frame([0,6],[3.6,7.2]);udl(m,10);load(m,type='nodal',node='n1-2',fx=18)
    elem(m,'diagonalA','n0-0','n1-1','truss','A1');elem(m,'diagonalB','n1-0','n0-1','truss','A1')
    p=public_input(m)
    for e in p['elements']:
        if e['id'].startswith('diagonal'):e['type']=None
    p['diagonalIntersectionConnection']=None
    emit('INT-063',[m],[turn('两层单跨6m、各层高3.6m；梁柱刚接、各梁向下10kN/m，屋面右节点+X 18kN。首层两根斜杆只标为“杆件”，未说明单元类型及交叉连接。请建模计算。'+ask_zh(),None,'clarify',['input-t1.json'],['diagonalMember.type','diagonalIntersection.connection'],['两根斜杆是否只受轴力？交叉处是否连接？']),turn('确认首层两斜杆均为仅受轴力的桁架单元，交叉处不连接，只按各自端部节点连接；梁柱仍刚接梁柱单元。计算。'+ask_zh(),1)],{'input-t1.json':p},notes('Two axial-only diagonal trusses only at first story. Initial member types and crossing semantics unspecified; T2 resolves both. No crossing node and no duplicate nodal locations. Roof lateral force exactly 18 kN.'))

    m=frame([0,6],[3.6,7.2]);split(m,'b0-1','firstMid',3,3.6);udl(m,10)
    for j,z in [(1,3.6),(2,7.2)]:node(m,f'tip{j}',7.5,z);elem(m,f'overhang{j}',f'n1-{j}',f'tip{j}');load(m,type='distributed',element=f'overhang{j}',wz=-6)
    load(m,type='nodal',node='firstMid',fz=-22)
    b=deepcopy(m);next(n for n in b['nodes'] if n['id']=='tip2')['x']=8
    emit('INT-064',[m,b],[turn('Build the two-story single-span 6 m frame, levels 3.6 and 7.2 m, with a 1.5 m right overhang at each level. Main beams carry 10 kN/m downward and overhangs 6 kN/m downward. The lower main-beam midpoint at (3,0,3.6) m carries an extra 22 kN downward. '+ask_en(),1,attachments=['input-t1.json']),turn('Extend only the second-story right overhang from 1.5 to 2 m by moving tip2 to X=8 m. Keep its original 6 kN/m load intensity over the new actual length. Preserve the lower overhang and the lower-main-beam 22 kN force. Recompute. '+ask_en(),2)],{'input-t1.json':public_input(m,outputJoint='n1-2 at (6,0,7.2) m; the overhang tip is not a beam-column joint.')},notes('Only tip2.x changes. UDL has no frozen end parameter so covers new full length. Lower midpoint force and both main spans preserved.'))

    m=frame([0,5,10],[3.3,6.6,9.9]);scale_section(m,'B1','B2',.6)
    for e in m['elements']:
        if e['type']=='beam':
            j=int(e['id'].split('-')[-1]);load(m,type='distributed',element=e['id'],wz=-[12,10,6][j-1])
            if j==3:e['section']='B2'
    b=deepcopy(m)
    for l in b['load_cases'][0]['loads']:
        if l['element'].endswith('-3'):l['wz']=-8
    emit('INT-065',[m,b],[turn('三层各3.3m、两跨各5m框架；从下到上梁线载12、10、6kN/m向下。顶层梁B2的Iy/Iz为B1的0.6倍且面积相同，一二层梁仍B1。计算。'+ask_zh(),1,attachments=['input-t1.json']),turn('仅顶层两跨梁的向下线载由6改8kN/m；一二层12、10kN/m及顶层B2均保持。重算。'+ask_zh(),2)],{'input-t1.json':public_input(m)},notes('All three 3.3 m stories and two 5 m spans retained. Only top two load records change; custom B2 has exact inertia factor .6 at unchanged area.'))

    m=frame([0,6,12],[3.6,7.2]);split(m,'c1-1','columnMid',6,1.8)
    for e in m['elements']:
        if e['id'].startswith('c1-'):e['section']='C2'
        if e['id'].startswith('b1-'):e['section']='B-right-v1'
    v1=section('B-right-v1',.3,.65);v1['name']='B-right v1';v2=section('B-right-v2',.35,.7);v2['name']='B-right v2';m['sections'].append(v1)
    udl(m,10);load(m,type='nodal',node='columnMid',fx=-7,id='column-mid-side')
    for j,f in [(1,10),(2,15)]:load(m,type='nodal',node=f'n2-{j}',fx=f,id=f'story-side-{j}')
    b=deepcopy(m);b['sections'].append(v2)
    for e in b['elements']:
        if e['id'].startswith('b1-'):e['section']='B-right-v2'
    versions={'units':UNITS,'sameDisplayName':'B-right','records':[v1,v2],'effectiveRevision':None}
    emit('INT-066',[m,b],[turn('Build the 2-story, 2-bay frame with 6 m spans and 3.6 m stories. Outer and middle columns have distinct sections; left and right beams are separate groups. All beams carry -Z 10 kN/m, right-story nodes +X 10/15 kN, and the connected first-story middle-column node at Z=1.8 m has -X 7 kN. '+ask_en(),1,attachments=['input-t1.json']),turn('Revise B-right using the two attached property revisions. I have not specified which revision takes effect; report the revised result after resolving the revision.',None,'clarify',['section-revisions-t2.json'],['B-right.effectiveRevision'],['Should B-right revision v1 or v2 apply, and is its scope only the right-span beams?'],priorState=1),turn('Use v2 only for the two right-span beams b1-1 and b1-2. Keep left beams, both column groups, and all loads including -X 7 kN unchanged; recompute. '+ask_en(),2)],{'input-t1.json':public_input(m),'section-revisions-t2.json':versions},notes('First-story middle column is split at Z=1.8 with connected force node. Separate stable IDs preserve v1 history; explicit v2=350x700 mm versus v1=300x650 mm is author-supplied missing appendix. T2 does not choose an effective revision. Only right-beam assignments plus addition of v2 record change at T3.'))

    m=frame([0,5,10],[3.6,7.2]);m['elements']=[e for e in m['elements'] if e['id']!='c1-2']
    for e in m['elements']:
        if e['type']=='beam':
            if e['id'].endswith('-1'):load(m,type='distributed',element=e['id'],wz=-10)
            elif e['id']=='b0-2':load(m,type='distributed',element=e['id'],start=2,end=5,wz=-9)
            else:load(m,type='distributed',element=e['id'],start=0,end=3,wz=-9)
    p=public_input(m,conflictingLegacyDescription='Old schematic text retains the upper middle column c1-2 between n1-1 and n1-2, while the current connectivity table deletes it. Authority is unresolved.')
    emit('INT-067',[m],[turn('两层各3.6m、两跨各5m框架。附件连接表删除上层中柱c1-2，但旧示意文字说上层中柱保留；下层中柱保留。上层梁按两梁共用节点连续，局部x=2～8m向下9kN/m；下层全跨10kN/m。请计算。'+ask_zh(),None,'clarify',['input-t1.json'],['upperMiddleColumn.existence'],['上层中柱以删除连接表还是旧示意保留文字为准？']),turn('确认删除上层中柱，按附件完整连接表建模：上层两梁共用n1-2连续、无该层中柱，下层中柱保持。保留上层x=2～8m局部线载，计算。'+ask_zh(),1)],{'input-t1.json':p},notes('Upper middle column absent but shared roof node is connected to both roof beams. Partial loads converted to per-element local distances [2,5] and [0,3] along +X, preserving global x=2..8 only. Independent stiffness smoke check required for stability.'))

    m=frame([0,6],[3.6,7.2])
    for n in m['nodes']:n['z']-=1.5
    split(m,'c0-1','leftMid',0,.3);udl(m,10);load(m,type='nodal',node='leftMid',fx=6)
    emit('INT-068',[m],[turn('Analyze the complete frame directly using its absolute coordinates: bases Z=-1.5 m, floors Z=2.1 and 5.7 m, span 6 m, both bases fixed. Each beam carries 10 kN/m downward. A connected first-story left-column midpoint at Z=0.3 m carries +X 6 kN. Both story heights are positive 3.6 m; retain the negative base elevation. '+ask_en(),1,attachments=['input-t1.json'])],{'input-t1.json':public_input(m)},notes('Absolute base elevation remains -1.5; no translation to zero. First column split at actual Z=.3, exactly midway between -1.5 and 2.1. Loads and all node coordinates source checked.'))

    m=model()
    node(m,'base',0,0,restraint=[True]*6);node(m,'interface',0,3);node(m,'top',0,8)
    elem(m,'lowerColumn','base','interface','column','C1');elem(m,'upperColumn','interface','top','column','C2')
    load(m,type='nodal',node='top',fx=25,fz=-500,my=18,id='top-vector')
    b=deepcopy(m);next(n for n in b['nodes'] if n['id']=='interface')['z']=4
    emit('INT-099',[m,b],[turn('固定底柱高8m，下段0～3m用C1、上段3～8m用C2，共用分界节点连续。顶端荷载为全局Fx=25kN、Fz=-500kN、My=+18kN·m，完整属性按附件。报告柱顶Uz/Ux与柱底Rz=Fz/My。',1,attachments=['input-t1.json']),turn('仅把C1/C2分界从z=3m上移到z=4m，柱顶仍z=8m，底部固定；顶端力与18kN·m力矩不移动不改值。重算柱顶Uz/Ux和柱底Rz/My。',2)],{'input-t1.json':public_input(m)},notes('Two connected column segments C1 below/C2 above. Interface alone moves 3→4; all top-vector components and Z=8 preserved. Source unspecified elastic material completed with the documented steel record.'))

    m=model('3d');node(m,'base',0,0,0,[True]*6);node(m,'columnMid',0,2.5);node(m,'columnTop',0,5);node(m,'armTip',1,5)
    elem(m,'lowerColumn','base','columnMid','column','C1');elem(m,'upperColumn','columnMid','columnTop','column','C1');elem(m,'arm','columnTop','armTip')
    load(m,type='nodal',node='columnMid',fx=16,id='column-side');load(m,type='nodal',node='armTip',fy=10,fz=-200,id='arm-tip-vector')
    b=deepcopy(m);next(n for n in b['nodes'] if n['id']=='armTip').update(x=0,y=1)
    states=[m,b,deepcopy(m)]
    requests=[dict(state=i,model=f'model-state-{i}.json',quantities=quantities(s,components=[('armTip','ux'),('armTip','uy'),('armTip','uz'),('base','My'),('base','Mz')]),derived=[]) for i,s in enumerate(states,1)]
    emit('INT-100',states,[turn('Build the 5 m fixed-base spatial column with a real rigidly connected 1 m beam extending along global +X at its top. The arm tip carries global Fy=+10 kN and Fz=-200 kN. A connected column node at Z=2.5 m separately carries global Fx=+16 kN. Report armTip Ux/Uy/Uz and base global support My/Mz for D.',1,attachments=['input-t1.json']),turn('Change only the arm geometry from 1 m along +X to 1 m along +Y: armTip becomes (0,1,5) m. Retain the global arm-tip load vector Fy=+10, Fz=-200 kN and the column-midpoint +X 16 kN. Recompute armTip Ux/Uy/Uz and base My/Mz.',2),turn('Undo only the preceding arm geometry change, restoring armTip=(1,0,5) m and the original arm orientation. Keep both force vectors and column height unchanged. Recompute armTip Ux/Uy/Uz and base My/Mz.',3)],{'input-t1.json':public_input(m)},notes('True 1 m deformable beam with explicit section, not an undeclared rigid offset. Arm reference global +Z remains valid after X→Y reorientation. T3 is byte-equivalent physical state to T1; column midpoint remains connected at 2.5 m with +X 16 kN.'),requests=requests)


if __name__=='__main__':build()
