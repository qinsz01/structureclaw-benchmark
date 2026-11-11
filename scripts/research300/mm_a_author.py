"""Deterministic MM-A authoring, image/DXF generation and contract compilation.

Run with Python 3 and Pillow; source tables are read, never modified.
No solver results or independent-reference artifacts are authored here.
"""
from pathlib import Path
from copy import deepcopy
import argparse, importlib.util, json, math, textwrap, xml.sax.saxutils as xml
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[2]
SHARED=ROOT.parent.parent
OUT=ROOT/'corpora/research-300/cases'
FONT='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
if not Path(FONT).exists(): FONT='/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc'

def dump(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def num(v):
    if abs(v-5/3)<1e-10:return '5/3'
    if abs(v-5/6)<1e-10:return '5/6'
    if abs(v-2*math.sqrt(3))<1e-10:return '2*sqrt(3)'
    return f'{v:.9g}'
def local(en,a,b):return a if en else b

class Canvas:
    def __init__(self,w=2400,h=1450):
        self.w,self.h=w,h;self.im=Image.new('RGB',(w,h),'white');self.d=ImageDraw.Draw(self.im)
        self.svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">','<rect width="100%" height="100%" fill="white"/>']
    def line(self,pts,color='#24394b',width=4):
        self.d.line(pts,fill=color,width=width)
        self.svg.append(f'<polyline points="'+ ' '.join(f'{x:.3f},{y:.3f}' for x,y in pts)+f'" fill="none" stroke="{color}" stroke-width="{width}"/>')
    def text(self,x,y,s,size=24,color='#172b3a'):
        s=str(s);f=ImageFont.truetype(FONT,size);self.d.text((x,y),s,font=f,fill=color)
        self.svg.append(f'<text x="{x:.3f}" y="{y+size:.3f}" font-family="Noto Sans CJK SC, sans-serif" font-size="{size}" fill="{color}">{xml.escape(s)}</text>')
    def circle(self,x,y,r=6,color='#24394b'):
        self.d.ellipse((x-r,y-r,x+r,y+r),fill=color);self.svg.append(f'<circle cx="{x:.3f}" cy="{y:.3f}" r="{r}" fill="{color}"/>')
    def arrow(self,a,b,color='#b8342b'):
        self.line([a,b],color,3);dx=b[0]-a[0];dy=b[1]-a[1];L=math.hypot(dx,dy)
        if L:
            u,v=dx/L,dy/L
            self.line([(b[0]-14*u-6*v,b[1]-14*v+6*u),b,(b[0]-14*u+6*v,b[1]-14*v-6*u)],color,3)
    def save(self,path):
        # Append extensions: decimal-elevation basenames must remain intact.
        self.im.save(Path(str(path)+'.png'),compress_level=9)
        Path(str(path)+'.svg').write_text('\n'.join(self.svg+['</svg>'])+'\n')

def support(n,truss,en):
    r=n['restraints']
    if truss:
        if r[:3]==[True,True,True]:return local(en,'PIN xyz' if not r[1] is False else 'PIN','铰 xyz')
        if r[2]:return local(en,'ROLLER Z','滚支 Z')
        return ''
    if all(r):return local(en,'FIXED','固支')
    if r[0] and r[2]:return local(en,'PIN XZ','铰 XZ')
    if r[2]:return local(en,'ROLLER Z','滚支 Z')
    return ''

def loads_text(m,hide_force=False):
    rows=[]
    for c in m['load_cases']:
        for l in c['loads']:
            vals=[]
            for k in ['fx','fy','fz','mx','my','mz','wx','wy','wz']:
                if k in l and l[k]:vals.append(f'{k}='+('?' if hide_force and k=='fz' else num(l[k])))
            rows.append((c['id'],l,l.get('node') or l.get('element'),', '.join(vals)))
    return rows

def draw(path,case,desc,en,view=('x','z'),initial=False,detail=False):
    if case in ('MM-042','MM-049'):
        from mm_a_41_50 import render_multiview
        if render_multiview(path,case,desc,en,view,Canvas,num):return
    m=desc['model'];nodes={n['id']:deepcopy(n) for n in m['nodes']};truss=all(e['type'] in ['truss','brace'] for e in m['elements'])
    missing_height=case=='MM-032' and initial
    if missing_height:
        # Deliberately distort roof heights: no pixel ratio can reconstruct H.
        for n in nodes.values():
            if n['z']>0:n['z']=1.3+(0.7 if n['x']==6 else .15*(int(n['x'])%4))
    a,b=view;xs=[n[a] for n in nodes.values()];zs=[n[b] for n in nodes.values()]
    xmin,xmax=min(xs),max(xs);zmin,zmax=min(zs),max(zs)
    W,H=2400,1650+max(0,len(m['elements'])-20)*18
    cv=Canvas(W,H)
    cv.text(55,25,f'{case} | '+local(en,'ENGINEERING INPUT','工程输入')+f' | {a.upper()}{b.upper()}'+local(en,' view','视图'),36)
    cv.text(55,85,local(en,'Schematic; use dimensions, do not scale. Filled dots = connected joints. Crossings without dots are not joints.','示意图，以标注尺寸为准，禁止量图。实心点为连接节点，无点交叉不连接。'),25)
    cv.text(55,130,local(en,'Length m; force kN; moment kN*m; line load kN/m along actual member length. Global Z up.','长度 m；力 kN；力矩 kN*m；线载 kN/m 按杆件实际长度。全局 Z 向上。'),24)
    def xy(n):return (170+(n[a]-xmin)/max(xmax-xmin,1)*2000,850-(n[b]-zmin)/max(zmax-zmin,1)*490)
    member_labels={};member_label_groups={}
    for j,e in enumerate(m['elements']):
        u,v=[xy(nodes[n]) for n in e['nodes']]
        label_t=.25 if case=='MM-035' and e['id'].startswith('KE') else .5
        if math.dist(u,v)>25:
            anchor=(u[0]+(v[0]-u[0])*label_t+5,u[1]+(v[1]-u[1])*label_t-28+(j%2)*25)
            member_labels[e['id']]=anchor
            member_label_groups.setdefault(anchor,[]).append(e['id'])
    for j,e in enumerate(m['elements']):
        u,v=[xy(nodes[n]) for n in e['nodes']]
        cv.line([u,v],width=5)
        label_t=.25 if case=='MM-035' and e['id'].startswith('KE') else .5
        if e['id'] in member_labels:
            anchor=member_labels[e['id']]
            if len(member_label_groups[anchor])==1:cv.text(*anchor,e['id'],21,'#15648c')
    # Coincident projections remain separate members. A combined ID callout
    # refers to the same projected line; the endpoint key retains connectivity.
    # Singleton annotations keep their original coordinates and drawing order.
    for (x,y),identities in member_label_groups.items():
        if len(identities)>1:
            e=next(e for e in m['elements'] if e['id']==identities[0])
            u,v=[xy(nodes[n]) for n in e['nodes']]
            target=((u[0]+v[0])/2,(u[1]+v[1])/2)
            cv.line([(x+12,y-57),target],'#15648c',2)
            cv.text(x,y-90,' / '.join(identities),21,'#15648c')
    # Dimension chains along the projected horizontal axis.
    ticks=sorted(set(xs))
    for x in ticks:
        px=170+(x-xmin)/max(xmax-xmin,1)*2000
        cv.line([(px,945),(px,985)],'#7e8a91',2);cv.text(px-24,990,num(x),22)
    cv.line([(170,965),(2170,965)],'#7e8a91',2);cv.text(2200,950,a.upper()+' (m)',23)
    projected_groups={}
    for n in nodes.values():projected_groups.setdefault(xy(n),[]).append(n['id'])
    for j,n in enumerate(nodes.values()):
        x,y=xy(n);cv.circle(x,y)
        peers=projected_groups[(x,y)];stack=peers.index(n['id'])
        offset=(22 if n[b]==zmin else -60-len(peers)*22)+stack*27
        label=n['id']
        if not(missing_height and n['z']>0):label+=f' [{b.upper()}={num(n[b])}]'
        elif missing_height:label+=' [height ?]'
        cv.text(max(15,min(x-40,2150)),y+offset,label,22)
        s=support(n,truss,en)
        if s:
            if not truss and all(n['restraints']):
                cv.line([(x-21,y+8),(x+21,y+8),(x+21,y+28),(x-21,y+28),(x-21,y+8)],'#328044',3)
                for dx in [-16,-5,6,17]:cv.line([(x+dx,y+9),(x+dx-10,y+27)],'#328044',2)
            else:
                cv.line([(x,y+8),(x-17,y+35),(x+17,y+35),(x,y+8)],'#328044',3)
                if not n['restraints'][0]:
                    for dx in [-11,11]:cv.circle(x+dx,y+41,4,'#328044')
                else:cv.line([(x-24,y+40),(x+24,y+40)],'#328044',2)
            cv.text(max(15,min(x-65,2150)),y+66,s,21,'#24683a')
    table_mode='图表联合' in desc['category']
    load_rows=loads_text(m,case=='MM-007' and initial)
    load_labels={};load_label_groups={}
    for j,(cid,l,target,values) in enumerate(load_rows):
        if 'node' in l:
            x,y=xy(nodes[target]);anchor=(max(10,min(x-85,2050)),y-135-(j%2)*30);size=21
        else:
            e=next(e for e in m['elements'] if e['id']==target);u,v=[xy(nodes[n]) for n in e['nodes']]
            anchor=((u[0]+v[0])/2-55,(u[1]+v[1])/2-110-(j%2)*25);size=20
        label=f'{cid}/{l["id"]}'+('' if table_mode else ': '+values)
        load_labels[j]=(anchor,label,size)
        load_label_groups.setdefault(anchor,[]).append(j)
    for j,(cid,l,target,values) in enumerate(load_rows):
        if 'node' in l:
            n=nodes[target];x,y=xy(n);fx=l.get('f'+a,0);fy=l.get('f'+b,0)
            if fx:cv.arrow((x-75*(1 if fx>0 else -1),y-6),(x,y-6))
            if fy:cv.arrow((x,y-90*(1 if fy<0 else -1)),(x,y))
            if any(l.get(k) for k in ['mx','my','mz']):
                pts=[(x+36*math.cos(t*.15),y+36*math.sin(t*.15)) for t in range(-16,14)]
                cv.line(pts,'#b8342b',3);cv.arrow(pts[-2],pts[-1])
        else:
            e=next(e for e in m['elements'] if e['id']==target);u,v=[xy(nodes[n]) for n in e['nodes']]
            if not table_mode and (l.get('w'+a) or l.get('w'+b)):
                for t in [.15,.5,.85]:
                    x,y=u[0]+(v[0]-u[0])*t,u[1]+(v[1]-u[1])*t
                    if l.get('w'+b):
                        sign=-1 if l.get('w'+b,0)>0 else 1
                        cv.arrow((x,y-70*sign),(x,y-8*sign))
                    elif l.get('w'+a):
                        sign=1 if l.get('w'+a,0)>0 else -1
                        cv.arrow((x-70*sign,y),(x-8*sign,y))
        anchor,label,size=load_labels[j];peers=load_label_groups[anchor]
        if len(peers)==1:
            cv.text(*anchor,label,size,'#a62c23')
        else:
            # Separate cases sharing an exact annotation anchor into distinct
            # rows. The original table/drawing division of load data is kept.
            x,y=anchor;row=peers.index(j)
            cv.text(x,y-35*(len(peers)-1-row),label,size,'#a62c23')
    y=1060
    if missing_height:cv.text(55,y,'Roof elevations and slopes omitted. Ridge x is derivable from the bottom chain; roof height needs confirmation.',23);y+=40
    cv.text(55,y,local(en,'Member key: ID : start -> end / material / section','构件索引：ID : 起点 -> 终点 / 材料 / 截面'),24);y+=38
    for j,e in enumerate(m['elements']):
        col=j%3;row=j//3
        cv.text(55+col*780,y+row*32,f'{e["id"]}: {e["nodes"][0]} -> {e["nodes"][1]} / {e["material"]} / {e["section"]}',19)
    y+=math.ceil(len(m['elements'])/3)*32+20
    drawing_notes=list(desc.get('drawingNotes',[]))
    if case=='MM-032' and not initial:drawing_notes+=desc.get('clarification',{}).get('supplementDrawingNotes',[])
    for note in drawing_notes:
        for line in textwrap.wrap(note,110 if en else 65):cv.text(55,y,line,22);y+=31
    if y>cv.h-10:
        raise ValueError(f'{case} drawing footer overflow {y}>{cv.h}; increase canvas')
    cv.save(path)

def dxf(path,case,desc,en,architectural=False):
    m=desc['model'];nodes={n['id']:n for n in m['nodes']};rows=[];text_boxes=[];pending=[];leaders=[];fixed_lines=[];fixed_boxes=[]
    def pairs(*args):rows.extend(str(a) for a in args)
    def line(layer,x1,y1,x2,y2,obstacle=True):
        pairs(0,'LINE',8,layer,10,x1,20,y1,30,0,11,x2,21,y2,31,0)
        if obstacle:fixed_lines.append((x1,y1,x2,y2))
    def circle(layer,x,y,r):
        pairs(0,'CIRCLE',8,layer,10,x,20,y,30,0,40,r)
        fixed_boxes.append((x-r,y-r,x+r,y+r))
    def text(layer,x,y,value,h=.15):
        pairs(0,'TEXT',8,layer,10,x,20,y,30,0,40,h,1,value)
        # Conservative ASCII extents, independent of a viewer's substituted font.
        text_boxes.append((x-.04,y-.35*h,x+len(value)*h,y+1.1*h))
    def callout(layer,x,y,value,anchor,step=.35,always_leader=False):
        pending.append((layer,x,y,value,anchor,step,always_leader))
    def segment_box(segment,box):
        """Return the segment parameter interval inside an axis-aligned box."""
        x,y,x2,y2=segment;left,bottom,right,top=box;lo,hi=0.,1.
        for p,q in [(-(x2-x),x-left),(x2-x,right-x),(-(y2-y),y-bottom),(y2-y,top-y)]:
            if abs(p)<1e-12:
                if q<0:return None
            elif p<0:lo=max(lo,q/p)
            else:hi=min(hi,q/p)
            if lo>hi:return None
        return lo,hi
    pairs(0,'SECTION',2,'HEADER',9,'$ACADVER',1,'AC1009',9,'$INSUNITS',70,6,0,'ENDSEC',0,'SECTION',2,'TABLES',0,'TABLE',2,'LAYER',70,6)
    for name,color in [('STRUCTURE',7),('SUPPORTS',3),('LOADS',1),('DIMENSIONS',4),('A_WALL',8),('A_EQUIPMENT',9)]:pairs(0,'LAYER',2,name,70,0,62,color,6,'CONTINUOUS')
    pairs(0,'ENDTAB',0,'ENDSEC',0,'SECTION',2,'ENTITIES')
    truss=all(e['type']=='truss' for e in m['elements'])
    for e in m['elements']:
        a,b=[nodes[n] for n in e['nodes']];line('STRUCTURE',a['x'],a['z'],b['x'],b['z'])
    for n in nodes.values():
        circle('STRUCTURE',n['x'],n['z'],.045)
        callout('DIMENSIONS',n['x'],n['z']-.3,f'{n["id"]} X={num(n["x"])} Z={num(n["z"])}',(n['x'],n['z']),step=-.35)
        s=support(n,truss,True)
        if s:
            x,z=n['x'],n['z']
            if not truss and all(n['restraints']):
                line('SUPPORTS',x-.2,z-.03,x+.2,z-.03)
                for dx in [-.16,-.05,.06,.17]:line('SUPPORTS',x+dx,z-.03,x+dx-.1,z-.17)
            else:
                line('SUPPORTS',x,z,x-.15,z-.2);line('SUPPORTS',x-.15,z-.2,x+.15,z-.2);line('SUPPORTS',x+.15,z-.2,x,z)
                if not n['restraints'][0]:
                    for dx in [-.08,.08]:circle('SUPPORTS',x+dx,z-.25,.035)
            callout('SUPPORTS',x,z-.6,s,(x,z),step=-.35)
    for e in m['elements']:
        a,b=[nodes[n] for n in e['nodes']];anchor=((a['x']+b['x'])/2,(a['z']+b['z'])/2)
        callout('DIMENSIONS',anchor[0],anchor[1]+.18,f'{e["id"]} {e["nodes"][0]}->{e["nodes"][1]} {e["material"]}/{e["section"]}',anchor,always_leader=True)
    if architectural:
        xs=[n['x'] for n in nodes.values()];zs=[n['z'] for n in nodes.values()];x0,x1=min(xs)-.5,max(xs)+.5;z0,z1=min(zs)-.5,max(zs)+.5
        for d in [0,.18]:
            for a,b in [((x0-d,z0-d),(x1+d,z0-d)),((x1+d,z0-d),(x1+d,z1+d)),((x1+d,z1+d),(x0-d,z1+d)),((x0-d,z1+d),(x0-d,z0-d))]:line('A_WALL',*a,*b)
        for a,b in [((x0+2,z0+1),(x0+4,z0+1)),((x0+4,z0+1),(x0+4,z0+2)),((x0+4,z0+2),(x0+2,z0+2)),((x0+2,z0+2),(x0+2,z0+1))]:line('A_EQUIPMENT',*a,*b)
        text('A_EQUIPMENT',x0+2,z0+1.3,'AHU / equipment',.18)
    for cid,l,target,value in loads_text(m):
        if 'node' in l:
            n=nodes[target];anchor=(n['x'],n['z']);kind='node'
        else:
            e=next(e for e in m['elements'] if e['id']==target)
            a,b=[nodes[n] for n in e['nodes']]
            length=math.dist([a[k] for k in 'xyz'],[b[k] for k in 'xyz'])
            fraction=(l.get('start',0)+l.get('end',length))/(2*length)
            anchor=tuple(a[k]+fraction*(b[k]-a[k]) for k in ['x','z']);kind='member'
        label=f'{cid}/{l["id"]} @ {kind} {target}: {value}'
        # Every load has its own row; reserve complete text extents rather than
        # cycling offsets, which previously put D-2 and D-5 at the same anchor.
        callout('LOADS',anchor[0]+.1,anchor[1]+.65,label,anchor,always_leader=True)
    # Place captions after all physical/context geometry is known. Their text
    # must not lie on member, support or architectural wall lines either.
    for layer,x,y,value,anchor,step,always_leader in pending:
        original=(x,y)
        while True:
            box=(x-.08,y-.10,x+len(value)*.15+.04,y+.20)
            overlap=any(box[0]<r and box[2]>left and box[1]<top and box[3]>bottom
                        for left,bottom,r,top in text_boxes+fixed_boxes)
            if not overlap and not any(segment_box(s,box) for s in fixed_lines):break
            y+=step
        if always_leader or (x,y)!=original:leaders.append((layer,x,y-.08,*anchor))
        text(layer,x,y,value)
    # Keep the convention notes below the lowest relocated annotation.
    footer_x=min(n['x'] for n in nodes.values())
    footer_y=min(-2,min(b[1] for b in text_boxes+fixed_boxes)-.6)
    text('DIMENSIONS',footer_x,footer_y,'Units m; DXF X->global X, DXF Y->global Z; global Y=0.',.18)
    text('LOADS',footer_x,footer_y-.45,'Load components: global XYZ; forces kN; nodal moments kN*m; line loads kN/m per actual member length.',.15)
    text('LOADS',footer_x,footer_y-.8,'LOADS leaders identify the loaded node/member; negative z acts along global -Z.',.15)
    if case=='MM-043':
        text('LOADS',footer_x,footer_y-1.15,'Both roof slopes: global -Z, 6 kN/m per actual slope length.',.15)
    # Keep leader gaps over captions, rather than drawing a line through text.
    # Only annotation leaders are clipped: structural/context entities are exact.
    for layer,x,y,x2,y2 in leaders:
        visible=[(0.,1.)]
        for left,bottom,right,top in text_boxes:
            interval=segment_box((x,y,x2,y2),(left-.02,bottom-.02,right+.02,top+.02))
            if interval is None:continue
            lo,hi=interval;remaining=[]
            for start,end in visible:
                if hi<=start or lo>=end:remaining.append((start,end))
                else:
                    if start<lo:remaining.append((start,lo))
                    if hi<end:remaining.append((hi,end))
            visible=remaining
        for start,end in visible:
            if end-start>1e-10:line(layer,x+start*(x2-x),y+start*(y2-y),x+end*(x2-x),y+end*(y2-y),obstacle=False)
    pairs(0,'ENDSEC',0,'EOF');path.write_text('\n'.join(rows)+'\n',encoding='ascii')

def properties(desc,en,case,conflict=False):
    m=desc['model'];lines=[local(en,'Analysis and property appendix','分析与属性附录'),'']
    lines += [local(en,'First-order linear elastic static analysis; self-weight OFF. No P-delta, rigid diaphragm, rigid offsets, stiffness reductions, or automatic combinations.','一阶线弹性静力；自重关闭。不开启 P-delta、刚性楼板、刚域、刚度折减或默认组合。'),local(en,'Global XYZ, Z up. Units: m, kN, kN*m; E/G MPa, density kg/m3, A m2, Iy/Iz/J m4. Displacements m, rotations rad.','全局 XYZ，Z 向上。单位：m、kN、kN*m；E/G 为 MPa，密度 kg/m3，A 为 m2，Iy/Iz/J 为 m4；位移 m，转角 rad。')]
    lines += [local(en,'Load components use global XYZ axes: fx/fy/fz are concentrated forces in kN; mx/my/mz are nodal moments in kN*m (right-hand rule); wx/wy/wz are distributed forces in kN/m per actual member length, not projected length. A negative z component acts along global -Z.','荷载分量按全局 XYZ 轴：fx/fy/fz 为集中力，单位 kN；mx/my/mz 为节点力矩，单位 kN*m（右手定则）；wx/wy/wz 为线分布力，单位 kN/m，按杆件实际长度计，不按投影长度计。z 分量为负表示沿全局 -Z。')]
    if case=='MM-043':
        lines += [local(en,'Both roof slopes: global -Z, 6 kN/m per actual slope length.','两坡梁线载均沿全局 -Z，按实际坡长计 6 kN/m。')]
    if m['coordinate_system']['dimension']=='2d':
        lines += [local(en,'XZ plane. Inactive uy/rx/rz are restrained. Local 1 runs from the labelled start to end; local 2 is global +Y; local 3 = local 1 cross local 2. Positive Ry/My follows the right-hand rule about global +Y.','XZ 平面，非作用自由度 uy/rx/rz 约束。局部 1 轴由图示起点指向终点，局部 2 为全局 +Y，局部 3=局部1叉乘局部2。Ry/My 按全局 +Y 右手定则。')]
    else:
        lines += [local(en,'3D geometry is defined jointly by the labelled orthographic views. All rotations of axial-only joints are inactive and restrained; these are not physical moment supports. Local 1 follows member start to end; local 2 = normalized(reference cross local 1); local 3 = local 1 cross local 2. Reference is global +X for vertical rods and global +Z otherwise.','空间几何由各正交视图共同确定。纯轴力杆节点转动为非作用自由度并约束，不代表抗弯支承。局部1由起点到终点；局部2=归一化(参考向量叉乘局部1)；局部3=局部1叉乘局部2。竖杆参考向量为全局+X，其余为全局+Z。')]
    if all(e['type']=='truss' for e in m['elements']):lines += [local(en,'All members are axial-only pin-jointed truss rods. Rotations are inactive. Do not add bending stiffness.','全部为铰接纯轴力杆，转动非作用，不添加弯曲刚度。')]
    else:lines += [local(en,'Beam/column joints are rigid and continuous unless a physical support is shown; observation nodes do not create hinges.','梁柱节点刚接连续，观测节点不产生内铰，支座按图。')]
    lines += ['',local(en,'Materials','材料')]
    for mat in m['materials']:lines += [f'{mat["id"]}: '+', '.join(f'{k}={num(mat[k])}' for k in ['E','G','nu','rho'])]
    lines += ['',local(en,'Sections (solid rectangular appendix; local y width B and local z depth H)','截面（附录采用实心矩形；局部 y 宽 B、局部 z 高 H）')]
    for s in m['sections']:lines += [f'{s["id"]}: '+', '.join(f'{k}={num(v)}' for k,v in s['properties'].items())]
    if '图表联合' in desc['category'] or case=='MM-021':
        lines += ['',local(en,'Member property assignment by drawing ID','按图中 ID 关联的属性表')]
        for e in m['elements']:lines += [f'{e["id"]}: {e["material"]} / '+('B1' if conflict and e['section']=='B2' else e['section'])]
    if '图表联合' in desc['category']:
        lines += ['',local(en,'Load table; positions/regions are defined by drawing labels','荷载表；位置/区域以图内标签为准')]
        for c,l,target,values in loads_text(m):lines += [f'{c}/{l["id"]}: {target}: {values}']
    if '正交' in desc.get('inputForm','') or '建筑DXF' in desc['category']:
        lines += ['',local(en,'Explicit constraints and load vectors by drawing ID','按图中 ID 给出的约束及荷载向量')]
        truss=all(e['type']=='truss' for e in m['elements'])
        for n in m['nodes']:
            if support(n,truss,en):lines += [n['id']+': '+local(en,'restrained DOFs ','约束自由度 ')+', '.join(k for k,r in zip(['ux','uy','uz','rx','ry','rz'],n['restraints']) if r)]
        for c,l,target,values in loads_text(m):lines += [f'{c}/{l["id"]}: {target}: {values}']
    if m['load_combinations']:
        lines += ['',local(en,'Execute each named combination separately (case and combination namespaces are distinct):','逐一执行以下组合（工况和组合命名空间不同）：')]
        for c in m['load_combinations']:lines += [c['id']+': '+json.dumps(c['factors'],ensure_ascii=False)]
    else:lines += ['',local(en,'Analyze the explicitly labelled basic case D.','分析图示基本工况 D。')]
    if 'DXF' in desc['category']:
        lines += ['',local(en,'DXF units are metres. DXF X maps to global X; DXF Y maps to global Z; global Y=0. STRUCTURE contains physical centre lines and joint dots. SUPPORTS, LOADS and DIMENSIONS are annotation layers.','DXF 源单位为 m，DXF X 对应全局 X，DXF Y 对应全局 Z，全局 Y=0。STRUCTURE 为结构中心线与节点，SUPPORTS/LOADS/DIMENSIONS 为支承、荷载与标注层。')]
        if '建筑' in desc['category']:lines += [local(en,'A_WALL and A_EQUIPMENT are architectural context only; they are not structural members or supports.','A_WALL、A_EQUIPMENT 仅为建筑围护及设备干扰层，不作为杆件或支座。')]
    lines += ['',local(en,'Report section forces using local axes; support forces/moments use global axes. Preserve signs, selected cases/combinations and section sides.','截面力使用局部轴，支座力及力矩使用全局轴。保留正负号、工况/组合及截面左右侧。')]
    return '\n'.join(lines)+'\n'

def source_rows():
    plan=json.loads((ROOT/'planning/capability-coverage-300.json').read_text())
    source=ROOT/'planning/sources'
    if not source.exists():source=SHARED/'planning/sources'
    tasks={r['id']:r for r in json.loads((source/'all-tasks-engines-v2.json').read_text())}
    models={r['taskId']:r for r in json.loads((source/'all-models-engines-v2.json').read_text())}
    return {r['id']:r for r in plan['cases']},tasks,models

def compile_case(case,desc,row,task,source_model):
    en=row['language']=='英文';desc['category']=row['subcategory'];desc['inputForm']=row['sourceRequirements']['task.inputForm'];path=OUT/case;path.mkdir(parents=True,exist_ok=True)
    m=desc['model'];dump(path/'model-state-1.json',m)
    clarification=case in ['MM-007','MM-021','MM-032']
    attachments=[];initial=[];later=[]
    # Modality-specific public attachments. Source diagrams contain the geometry;
    # the text appendix never contains a coordinate or connectivity table.
    if 'DXF' in row['subcategory']:
        dxf(path/'input.dxf',case,desc,en,'建筑' in row['subcategory']);attachments=['input.dxf']
    elif '多视图' in row['subcategory'] or '正交' in row['sourceRequirements']['task.inputForm']:
        for a,b in [('x','y'),('x','z'),('y','z')]:
            stem=f'view-{a}{b}';draw(path/stem,case,desc,en,(a,b));attachments += [stem+'.png',stem+'.svg']
    else:
        stem='input-initial' if clarification else 'input'
        draw(path/stem,case,desc,en,initial=clarification);attachments=[stem+'.png',stem+'.svg']
        if clarification:
            draw(path/'input-resolved',case,desc,en);later=['input-resolved.png','input-resolved.svg']
        elif row['subcategory']=='工程标注图':
            # Genuine local detail around a requested observation joint, with
            # retained original coordinates, not a duplicate overview image.
            q=next((q for o in desc['outputs'] for q in o.get('quantities',[]) if q['location']['kind']=='node'),None)
            focus=q['location']['id'] if q else m['nodes'][0]['id']
            keep_e=[e for e in m['elements'] if focus in e['nodes']]
            keep_n={n for e in keep_e for n in e['nodes']}
            dm=deepcopy(m);dm['nodes']=[n for n in m['nodes'] if n['id'] in keep_n];dm['elements']=keep_e
            for c in dm['load_cases']:c['loads']=[l for l in c['loads'] if l.get('node') in keep_n or l.get('element') in {e['id'] for e in keep_e}]
            dd=dict(desc,model=dm,drawingNotes=[local(en,'Local joint detail; member IDs and dimensions refer to the overview. This is a crop, not a separate structure.','节点局部详图：构件 ID 与尺寸对应总图。此为局部，不是独立结构。')])
            draw(path/'joint-detail',case,dd,en,detail=True);attachments+=['joint-detail.png','joint-detail.svg']
    (path/'properties.txt').write_text(properties(desc,en,case,conflict=case=='MM-021'))
    attachments+=['properties.txt'];initial=attachments[:]
    if case=='MM-021':
        (path/'properties-confirmed.txt').write_text(properties(desc,en,case));later+=['properties-confirmed.txt']
    requests=[];derived=[];outputs=[]
    for i,o in enumerate(desc['outputs'],1):
        requests+=o.get('quantities',[]);derived+=o.get('derived',[])
        outputs.append(dict(id=f'output-{i}',description=o['description'],state=1,quantityIds=[q['id'] for q in o.get('quantities',[])]+[d['id'] for d in o.get('derived',[])],kind=o.get('kind','numerical')))
    outputs.append(dict(id='model-result-figure',description=local(en,'Provide a model/result figure consistent with the numerical table, including support/load/ID mapping and signed result units.','给出与数值表一致的模型/结果图，包含支座、荷载、ID 对应及结果正负号与单位。'),state=1,quantityIds=[],kind='figure'))
    heading=local(en,f'Reconstruct the model from the supplied {row["plannedEngine"]} input drawings and property appendix. Use {row["plannedEngine"]} for the actual analysis. ',f'请依据所附图纸与属性附录恢复模型，使用 {row["plannedEngine"]} 实际分析。')
    heading+=local(en,'Resolve missing or contradictory essential data before analysis. Preserve the drawing connectivity, supports, load positions and property groups.\n','分析前先澄清缺失或冲突的必要信息；保留图示连通关系、支座、载荷位置及属性组。\n')
    prompt=heading+'\n'+local(en,'Requested outputs:\n','要求输出：\n')+'\n'.join(o['description'] for o in outputs)
    (path/'prompt.txt').write_text(prompt+'\n')
    turn=dict(id='t1',instruction=prompt,state=None if clarification else 1,expectation='clarify' if clarification else 'analyze',attachments=initial,unresolvedFields=[],expectedQuestions=[])
    turns=[turn]
    if clarification:
        missing={'MM-007':('/load_cases/0/loads/0/fz','请确认图中模糊的中点竖向集中力数值。','补图明确中点力为全局 Z 向 -15 kN。请完成所要求的分析。'),
                 'MM-021':('/elements/2/section','第二跨图中为 B2，关联表为 B1，请确认采用哪组截面。','确认第二跨采用 B2。请按修正附录与补图完成所要求的分析。'),
                 'MM-032':('/nodes/7/z','What is the ridge elevation H above the bottom chord? The ridge horizontal coordinate can be derived from the dimension chain.','The supplement provides ridge height 2.5 m and all roof elevations. Complete the requested analysis.')}
        field,question,resolve=missing[case];turn['unresolvedFields']=[field];turn['expectedQuestions']=[question]
        turns.append(dict(id='t2',instruction=resolve,state=1,expectation='analyze',attachments=later,unresolvedFields=[],expectedQuestions=[]))
        outputs.append(dict(id='clarification',description=question,state=None,quantityIds=[],kind='interaction'))
    assert len(turns)==task['turns'],(case,task['turns'])
    for output in outputs:
        output['turnIds']=['t1' if output['kind']=='interaction' or not clarification else 't2']
    allatt=initial+later
    gates=[dict(id=x,status='pending',description=d) for x,d in [
        ('input-blind-review','Independent input reconstruction and modality/legibility review.'),('model-source-review','Independent review against every original source requirement.'),('native-execution','Actual prescribed engine version, input, configuration, logs, raw results and observation mapping.'),('same-engine-truth','Independently reviewed same-engine reference and separate equilibrium/stiffness cross-check.'),('figure-consistency','Requested model/result figures and their underlying numeric data match.'),('adapter-preflight','Case-specific conversion and readback tests, including axes and load jumps.')]]
    coverage=[]
    for field in row['sourceRequirements']:
        ids=[r['id'] for r in row['requirements'] if r['sourceField']==field]
        if field in ['engine.executionRequirement','engine.requiredEvidence']:targets=['gate:native-execution']
        elif field in ['engine.truthPlan','task.prerequisite']:targets=['gate:same-engine-truth','gate:input-blind-review']
        elif field=='engine.adapterGap':targets=['gate:adapter-preflight']
        elif field in ['task.expectedOutput','task.gradingFocus']:targets=['output:'+o['id'] for o in outputs]+['gate:figure-consistency']
        elif field=='engine.analysisContract':targets=['attachment:properties.txt','turn:'+turns[-1]['id'],'gate:native-execution']
        else:targets=['attachment:'+f for f in allatt]+['gate:model-source-review']
        coverage.append(dict(sourceField=field,requirementIds=ids,targets=targets,notes='Authored evidence/gate mapping only; native execution and independent validation remain pending.'))
    contract=dict(schemaVersion=1,evaluationProfile='engineering-v2.3',id=case,modelId=row['modelId'],family=row['family'],language=row['language'],locale='en' if en else 'zh',plannedEngine=row['plannedEngine'],sourcePlan=deepcopy(row['sourceRequirements']),modelStates=['model-state-1.json'],attachments=allatt,turns=turns,requiredOutputs=outputs,requirementCoverage=coverage,status='authored-candidate',sameEngineTruthStatus='pending',inputBlindReview='pending',llmEndToEnd='not-run',acceptanceGates=gates,authoringNotes=desc.get('notes',[]))
    dump(path/'contract.json',contract)
    # A request is not a computed answer. Duplicate output references share one request.
    unique={}
    for q in requests:
        if q['id'] in unique:assert unique[q['id']]==q
        unique[q['id']]=q
    dump(path/'reference-requests.json',dict(schemaVersion=1,states=[dict(state=1,model='model-state-1.json',quantities=list(unique.values()),derived=derived)]))

def build_all():
    data={}
    for file in ['mm_a_01_20.py','mm_a_21_30.py','mm_a_31_40.py','mm_a_41_50.py']:
        p=Path(__file__).with_name(file)
        if not p.exists():continue
        spec=importlib.util.spec_from_file_location(p.stem,p);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);data.update(mod.build())
    return data

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--start',type=int,default=1);ap.add_argument('--end',type=int,default=50);args=ap.parse_args()
    rows,tasks,models=source_rows();data=build_all()
    for i in range(args.start,args.end+1):
        cid=f'MM-{i:03d}'
        if cid not in data:raise ValueError('No authored specification for '+cid)
        compile_case(cid,data[cid],rows[cid],tasks[cid],models[cid]);print(cid)

if __name__=='__main__':main()
