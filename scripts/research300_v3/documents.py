"""Engineering construction records, not ready StructureModelV2 arrays.

Coordinates are issued as named axes and joint locations, connectivity as
construction runs, supports as detail references. MM locates joints on
dimensioned grid drawings instead of rasterising a complete node CSV.
"""
from collections import defaultdict
from copy import deepcopy
import csv
import io
import json
import math
from pathlib import Path

from PIL import Image,ImageDraw,ImageFont
from .mechanics import COMBINATIONS

HERE=Path(__file__).resolve().parent
DOFS=['ux','uy','uz','rx','ry','rz']

def write(p,value):
    p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists():raise FileExistsError(str(p))
    p.write_text(value if isinstance(value,str) else json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n')

def table(headers,rows):
    out=io.StringIO();w=csv.writer(out,lineterminator='\n');w.writerow(headers);w.writerows(rows);return out.getvalue()

def font(size,mono=False):return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/'+('DejaVuSansMono.ttf' if mono else 'DejaVuSans.ttf'),size)

def axes(model):
    out={}
    for key in 'xyz':out[key]={v:f'{key.upper()}{i+1:02}' for i,v in enumerate(sorted({n[key] for n in model['nodes']}))}
    return out

def runs(model):
    # Chains retain every issued joint and member mark. Their endpoint arrays
    # are engineering construction records; no complete solver model is issued.
    nodes={n['id']:n for n in model['nodes']};remaining={e['id']:e for e in model['elements']};result=[]
    while remaining:
        eid=min(remaining);e=remaining.pop(eid);path=list(e['nodes']);marks=[eid]
        signature=lambda x:(x['type'],x['material'],x['section'],x.get('rotation_angle',0),json.dumps(x.get('releases'),sort_keys=True))
        for end in [0,-1]:
            while True:
                joint=path[end];near=path[1] if end==0 else path[-2];a=nodes[joint];b=nodes[near]
                matches=[]
                for candidate in remaining.values():
                    if signature(candidate)!=signature(e) or joint not in candidate['nodes']:continue
                    other=next(n for n in candidate['nodes'] if n!=joint);c=nodes[other]
                    v=[b[k]-a[k] for k in 'xyz'];w=[c[k]-a[k] for k in 'xyz'];nv=math.sqrt(sum(t*t for t in v));nw=math.sqrt(sum(t*t for t in w))
                    if abs(sum(x*y for x,y in zip(v,w))+nv*nw)<1e-9*max(nv*nw,1.):matches.append((candidate,other))
                if len(matches)!=1:break
                candidate,other=matches[0];remaining.pop(candidate['id'])
                if end==0:path.insert(0,other);marks.insert(0,candidate['id'])
                else:path.append(other);marks.append(candidate['id'])
        original={v['id']:v for v in model['elements']}
        result.append({'id':f'R{len(result)+1:03}','jointPath':path,'segmentMarks':marks,'segmentDirections':['forward' if original[mid]['nodes']==[a,b] else 'reverse' for mid,a,b in zip(marks,path,path[1:])],'type':e['type'],'material':e['material'],'section':e['section'],'rotationDeg':e.get('rotation_angle',0)})
    return result

def raster_layout(model,folder,title,grid):
    nodes=model['nodes'];lookup={n['id']:n for n in nodes};width,height=2400,1600
    data=[(code,value,key.upper()) for key,values in grid.items() for value,code in values.items()]
    for page in range(math.ceil(len(data)/30)):
        im=Image.new('RGB',(width,height),'white');d=ImageDraw.Draw(im)
        d.text((60,30),title+' | dimension key '+str(page+1),font=font(34),fill='black')
        d.text((60,105),'Axis codes are construction dimensions, in m. Layouts are schematic, not to scale.',font=font(25),fill='#334155')
        for j,(code,value,key) in enumerate(data[page*30:(page+1)*30]):d.text((90,195+j*43),f'{code:5}  {value:.12g} m   ({key})',font=font(28,True),fill='#0f172a')
        im.save(folder/f'dimensions-{page+1:02}.png')
    spatial=model['coordinate_system']['dimension']=='3d';views=[]
    if spatial:
        for z in sorted(grid['z']):views.append(('x','y','z',z))
    else:views=[('x','z','y',0.)]
    page=0;index=[]
    for hx,vy,fixed,value in views:
        selected=[n for n in nodes if abs(n[fixed]-value)<1e-8];xvals=sorted({n[hx] for n in selected});yvals=sorted({n[vy] for n in selected})
        for start in range(0,len(xvals),12):
            xs=xvals[start:start+12];ys=yvals;page+=1
            im=Image.new('RGB',(width,height),'white');d=ImageDraw.Draw(im)
            d.text((55,25),title+f' | {hx.upper()}-{vy.upper()} layout | {grid[fixed][value]} | sheet {page}',font=font(32),fill='#0f172a')
            d.text((55,93),'Circled joint marks define connectivity. Read exact coordinates from the axis dimension key.',font=font(23),fill='#334155')
            d.text((55,132),'No joint is created by an unmarked crossing. Construction runs define the complete member chains.',font=font(23),fill='#334155')
            xmap={x:180+i*2020/max(len(xs)-1,1) for i,x in enumerate(xs)};ymap={y:1380-i*1120/max(len(ys)-1,1) for i,y in enumerate(ys)}
            for x in xs:
                d.line((xmap[x],220,xmap[x],1430),fill='#cbd5e1',width=1);d.text((xmap[x]-35,1450),grid[hx][x],font=font(25),fill='#475569')
            for y in ys:
                d.line((140,ymap[y],2250,ymap[y]),fill='#cbd5e1',width=1);d.text((35,ymap[y]-15),grid[vy][y],font=font(25),fill='#475569')
            visible={n['id'] for n in selected if n[hx] in xmap}
            for e in model['elements']:
                if all(nid in visible for nid in e['nodes']):
                    a,b=[lookup[nid] for nid in e['nodes']];pa=(xmap[a[hx]],ymap[a[vy]]);pb=(xmap[b[hx]],ymap[b[vy]])
                    d.line((pa,pb),fill='#64748b',width=4)
            positions=defaultdict(list)
            for n in selected:
                if n['id'] not in visible:continue
                px,py=xmap[n[hx]],ymap[n[vy]];positions[(px,py)].append(n['id']);d.ellipse((px-6,py-6,px+6,py+6),fill='#075985')
            for (px,py),ids in positions.items():d.text((px+8,py-34),'/'.join(ids),font=font(22),fill='#075985')
            name=f'layout-{page:02}.png';im.save(folder/name)
            index.append([name,hx,vy,grid[fixed][value],' > '.join(grid[hx][x] for x in xs),' > '.join(grid[vy][y] for y in ys)])
    write(folder/'drawing-index.csv',table(['sheet','horizontal_axis','vertical_axis','fixed_axis','column_axes','row_axes'],index))

def geometry(folder,model,mode,title):
    folder.mkdir(parents=True,exist_ok=True);grid=axes(model)
    if mode=='raster':raster_layout(model,folder,title,grid)
    else:
        write(folder/'grid-dimensions.csv',table(['axis','coordinate_m'],[(code,value) for values in grid.values() for value,code in values.items()]))
        write(folder/'joint-locations.csv',table(['joint_mark','X_axis','Y_axis','Z_level'],[(n['id'],*[grid[k][n[k]] for k in 'xyz']) for n in model['nodes']]))
    detail_ids={};seatings=[]
    for n in model['nodes']:
        mask=tuple(n['restraints'])
        if mask not in detail_ids:detail_ids[mask]=f'K{len(detail_ids)+1:02}'
        seatings.append([n['id'],detail_ids[mask]])
    write(folder/'joint-details.csv',table(['joint_mark','detail'],seatings))
    write(folder/'connection-details.json',{'restrainedGlobalDofs':{code:[d for d,on in zip(DOFS,mask) if on] for mask,code in detail_ids.items()},'beamColumnJoints':'Rigid unless an issued member end-release detail says otherwise. Axial bars carry both signs of axial force.','analysisMesh':'Every issued joint mark is an analysis node. Observation and force-transfer points are retained without adding restraints.','coordinateSystem':model['coordinate_system']})
    rows=runs(model)
    write(folder/'construction-runs.csv',table(['run','joint_path','ordered_segment_marks','segment_directions','member_type','material_family','section_family','rotation_deg'],[[r['id'],' > '.join(r['jointPath']),' > '.join(r['segmentMarks']),' > '.join(r['segmentDirections']),r['type'],r['material'],r['section'],r['rotationDeg']] for r in rows]))
    write(folder/'materials.json',model['materials']);write(folder/'section-families.json',model['sections'])
    if model.get('metadata',{}).get('elementReferenceVectors'):write(folder/'section-reference-planes.json',model['metadata']['elementReferenceVectors'])
    write(folder/'model-conventions.json',{'schema_version':model['schema_version'],'unit_system':model['unit_system'],'coordinate_system':model['coordinate_system'],'analysis_control':model['analysis_control'],'stories':model.get('stories',[]),'units':{'coordinates':'m','E/G':'MPa','loads':'kN, kN.m','sectionProperties':'m^2, m^4','shapeB/H':'mm','mass':'tonne'}})
    return {'axes':sum(len(v) for v in grid.values()),'joints':len(model['nodes']),'members':len(model['elements']),'constructionRuns':len(rows)}

def write_public(folder,case,ref,ordinal,instruction):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    if any(folder.iterdir()):raise FileExistsError('Fresh packet required')
    task={'caseId':case['id'],'turnId':'t'+str(ordinal),'family':case['family'],'designedLevel':case['level'],'engine':case['engine'],'kind':ref['kind'],'title':case['title'],'instruction':instruction,'sourceId':case.get('sourceId'),'answerFile':'answer.json'}
    if ordinal==1:
        mode='raster' if case['family']=='MM' else 'construction-documents'
        if ref['kind']=='project':
            geometry(folder/'primary',ref['primaryTemplate'],mode,case['id']+' primary')
            upper=deepcopy(ref['upperTemplate'])
            if ref['integration']=='rigid':
                for n in upper['nodes']:n['restraints']=[False,True,False,True,False,True]
            geometry(folder/'upper',upper,mode,case['id']+' distribution beam')
            coupling='shared global translations and rotations, no added ground support' if ref['integration']=='rigid' else 'negative global support reaction, Fx and Fz'
            write(folder/'interface-details.csv',table(['distribution_support','primary_joint','connection'],[[r['upperSupport'],r['primaryJoint'],coupling] for r in ref['interface']]))
            write(folder/'design-catalog.json',{'catalog':ref['catalog'],'groups':ref['designGroups'],'dimensions':'Multiply each nominal rectangular B/H in the chosen group by the catalog factors. Round updated b,h in m to 6 decimal places, then compute A=b*h, Iy=b*h^3/12, Iz=h*b^3/12; let a=max(b,h),t=min(b,h), J=a*t^3*(1/3-0.21*t/a*(1-t^4/(12*a^4))). Update both shape B/H in mm and properties. Do not change E/G or coordinates.','objective':'Minimize total upper+primary material volume among feasible designs; if none feasible, report the design minimizing maximum constraint utilization.','completeEnumerationRequired':False})
            write(folder/'load-zones.json',ref['loadRules'])
            write(folder/'engineering-brief.md',project_brief(ref))
        elif ref['kind']=='analysis':
            geometry(folder/'structure',ref['scenarios'][0]['model'],mode,case['id'])
            write(folder/'load-zones.json',ref['scenarios'][0]['loadRules'])
            if len(ref['scenarios'])>1:write(folder/'proposed-revision.json',ref['scenarios'][1]['loadRules']['liveRevision'])
        else:
            geometry(folder/'structure',ref['model'],mode,case['id'])
            write(folder/'load-zones.json',ref['loadRules']);write(folder/'mass-source.json',ref['massRule'])
        write(folder/'combinations.json',COMBINATIONS)
        write(folder/'load-units.json',{'zonePressure':'kN/m^2','stripWidth':'m','pointForce':'kN','materialDensity':'kg/m^3','gravity':'m/s^2','lineLoad':'kN/m','globalAxes':'X/Y horizontal; Z upward','scope':'Linear elastic members. These authored service limits are analysis constraints, not a code compliance or ultimate strength conclusion.'})
        if case.get('sourceBasis'):write(folder/'source-basis.json',{'source':case['sourceBasis'],'authoredAssumptions':case.get('authoringBasis',[]),'adaptation':'This is an explicitly authored engineering subproblem, including a new distribution beam where applicable, not the original full building or its design certification.'})
        write(folder/'tool-contract.md',(HERE/'tool-contract.md').read_text())
    else:write(folder/'engineering-revision.md',instruction+'\n\nRetain all other issued geometry, material, section-family, support and load data. No full updated model is supplied.\n')
    if ref['kind']=='project':
        task.update(integration=ref['integration'],constraints=ref['constraints'],requirements=ref['requirements'],report=['design','feasible','volume','metrics','transfers','jobIdsByModel'])
    elif ref['kind']=='analysis':
        task.update(scenarios=[s['id'] for s in ref['scenarios']],selections=ref['scenarios'][0]['selections'],report=['jobIdsByScenario','metrics','relativeChangeWhenRequested'])
    else:
        task.update(requests=[{k:v for k,v in q.items() if k in ['id','path','operation','unit']} for q in ref['requests']],reportIds=ref['reportIds'],requireShapes=ref.get('requireShapes',False),reportMassTotal=True)
        params=deepcopy(ref['parameters'])
        if 'groundMotion' in params:
            motion=params.pop('groundMotion');write(folder/'excitation.csv',table(['time_s','acceleration'],[(i*params['timeStep'],v) for i,v in enumerate(motion)]));params['groundMotionFile']='excitation.csv'
        write(folder/'analysis-parameters.json',params)
    task['attachments']=sorted(str(p.relative_to(folder)) for p in folder.rglob('*') if p.is_file());write(folder/'task.json',task)


def project_brief(ref):
    common='''依据施工轴网、构件分段、材料和名义截面建立工程子结构。每个标注节点均保留；不得在未标注交点新增连接。支承约束采用 connection-details.json 的全局自由度。二维分析位于 X-Z 平面。梁柱刚接，truss/brace 仅传轴力且允许受拉受压。

上部三跨分配梁的 OUTER、MIDDLE 截面组以及全部主体截面族构成三个独立设计组；每组选择 A/B/C。按 design-catalog.json 更新几何与全部截面性质。自重随所选截面重新计算，显式施加到 D；不要开启自动 self_weight。实体体积等于所有杆件 A*L 之和，单位 m^3。

上部梁承受 load-zones.json 的分区面荷载。D/Q 按水平投影面积；W 按实际斜面面积并沿向上的表面法线。分区在 X 坐标截断，宽度保持各原区域值，不得把每区合力重复施加到每根构件。上部自重和主体自重各计一次。equipmentAction 是施加给主体的独立 W 工况水平力，按其 X 位置在相邻两个接口间线性分配。

必须覆盖所有下发的三个组合，搜索全部分析节点和全部主体梁柱端截面，报告真实控制位置；纯轴力主体仅比较 N，含梁柱主体比较 M2/M3。横向指标为 sqrt(ux^2+uy^2)。可行性取全部约束，目标为可行设计中总体积最小。若全部不可行，提交最大约束利用率最小的实际设计及其作业证据。相同最优值均可接受。无需提交所有试探方案的完整模型，只提交最终选择及其真实求解记录。
'''
    if ref['integration']=='one-way':
        return common+'''\n连接方式：单向荷载传递。上部单独按其图纸支承求解 D/Q/W 三个基本工况，将四个支座的全局 Fx/Fz 反力各取负值施加给接口表对应主体节点，分工况传递，保留主体自身荷载。主体变形不反馈上部。上部组合响应可由基本工况线性叠加；主体求解所有组合。不得把上部支座反力作为正向节点力，也不得对已传递的荷载再做一次面荷载转换。transfers 报告上部支座反力，非取负后的主体力。\n'''
    return common+'''\n连接方式：四个接口刚接，位移和转角相容。把上下部合成一个结构模型，接口表每对节点合并为同一节点，其他节点保持独立。上部位于四个主体接口相同的 Y 平面，按其 X/Z 轴网放置；平面上部嵌入空间主体时内部节点六个自由度均开放。上部接口不是对地支承，唯一对地支承来自主体。二维主体纯轴力节点原来为消除无刚度自由度而固定的 ry，在接入上部梁的接口处应开放；其他主体约束保持。可用 P-/U- 前缀消除名称冲突，接口保留 P- 名称。空间上部构件局部参考向量取全局 [0,0,1]，主体按签发参考平面。合并后自重一次计入 D，全部面荷载直接作用上部，不再通过单独支座反力二次加载。求解三个组合，transfers 报告四个共同接口的 ux/uz。\n'''
