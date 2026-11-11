"""Independent source-directed MM026..050 review. No author/SUT modules imported.

Manual source transcription below is from original all-{tasks,models}-engines-v2.json
scenario/spec, not the author check function. This is NOT blind reconstruction.
Run: PYTHONPATH=<root>/.bench-work/venv/lib/python3.10/site-packages python3 <this-file>
Writes only this review's evidence JSON in the review-inputs worktree.
"""
from pathlib import Path
from collections import Counter
import datetime, hashlib, json, math, re, sys
import xml.etree.ElementTree as ET
import ezdxf
from PIL import Image

HERE = Path(__file__).resolve().parents[2]
ROOT = HERE.parents[1]
CASES = ROOT / '.worktrees/mm-a/corpora/research-300/cases'
OUT = HERE / 'docs/implementation/reviews/review-inputs/mm026_050-evidence.json'
HASHES = {}

def raw(p):
    b = p.read_bytes(); HASHES[str(p)] = hashlib.sha256(b).hexdigest(); return b

def doc(p): return json.loads(raw(p))
def coord(x,z,y=0): return (round(x,9),round(y,9),round(z,9))
def point(n): return tuple(round(n[a],9) for a in 'xyz')
def edge(a,b,s='A1'): return (*sorted((a,b)),s)
def chain(ps,s='A1'): return [edge(a,b,s) for a,b in zip(ps,ps[1:])]
def nodal(p,z,x=0,y=0): return ('D','nodal',p,(x,y,z))
def dist(a,b,z,case='D'): return (case,'distributed',tuple(sorted((a,b))),(0,0,z))

# Each row describes source geometry, per-member property groups, active support
# DOFs (ux,uy,uz,rx,ry,rz), and full load application, without author IDs.
def expectation(i):
    n=[];e=[];l=[];support={}; truss=27<=i<=42
    def pinroll(left,right):
        support[left]=(True,True,True,True,truss,True)
        support[right]=(False,True,True,True,truss,True)
    def fixed(p): support[p]=(True,)*6
    if i==26:
        n=[coord(x,0) for x in [0,4,10,12.5,15,19,22]]
        e=[edge(n[j],n[j+1], 'B1' if j in [0,5] else 'B2') for j in range(6)]
        pinroll(n[0],n[-1]); support.update({n[j]:(False,True,True,True,False,True) for j in [1,2,4,5]})
        l=[dist(a,b,-7) for a,b,_ in e]+[dist(n[1],n[2],-10,'L'),dist(n[4],n[5],-10,'L')]
    elif i in [27,28,31,33,38]:
        xs={27:[2.5*j for j in range(7)],28:list(range(0,19,3)),31:list(range(0,19,3)),33:list(range(0,16,3)),38:list(range(0,16,3))}[i]
        zs={27:[2.5]*7,28:[1.6,2,2.4,2.8,3,2.4,1.6],31:[3]*7,33:[2,2,3,3,2,2],38:[2+.3*j for j in range(6)]}[i]
        low=[coord(x,.1*x if i==38 else 0) for x in xs]; up=[coord(x,z) for x,z in zip(xs,zs)];n=low+up
        web='A2' if i==31 else 'A1';e=chain(low)+chain(up)+[edge(a,b,web) for a,b in zip(low,up)]
        if i==27: e += [edge(up[j],low[j+1]) if j<3 else edge(low[j],up[j+1]) for j in range(6)]
        else: e += [edge(low[j],up[j+1],web) for j in range(len(xs)-1)]
        if i==31:e += [edge(up[j],low[j+1],web) for j in range(6)]
        pinroll(low[0],low[-1])
        l={27:[nodal(up[j],-10) for j in range(1,6)],28:[nodal(low[j],-15) for j in [3,4,5]],31:[nodal(up[j],-12) for j in range(1,6)],33:[nodal(low[j],-10) for j in range(1,5)],38:[nodal(up[j],v) for j,v in [(2,-20),(3,-15),(4,-10)]]}[i]
    elif i in [29,32,34]:
        xs={29:[0,4,8,12],32:[0,3,6,9,12,15],34:[0,4,8,12,16]}[i]
        low=[coord(x,0) for x in xs]
        up=[coord(x,z) for x,z in {29:[(4,2),(6,3),(8,2)],32:[(3,1.25),(6,2.5),(9,5/3),(12,5/6)],34:[(4,2),(8,4),(12,2)]}[i]]
        n=low+up;e=chain(low)+chain([low[0]]+up+[low[-1]])
        e += [edge(p,q) for p in low for q in up if p[0]==q[0]]
        di={29:[(1,1),(2,1)],32:[(1,1),(2,2),(3,3)],34:[(1,1),(3,1)]}[i]
        e += [edge(low[j],up[k]) for j,k in di];pinroll(low[0],low[-1]);l=[nodal(p,{29:-20,32:-10,34:-12}[i]) for p in up]
    elif i in [30,37]:
        low=[coord(x,0) for x in (range(0,13,2) if i==30 else [0,2,5,9,12])]
        up=[coord(x,2 if i==30 else 2.2) for x in (range(1,12,2) if i==30 else [1,3.5,7,10.5])]
        n=low+up;e=chain(low)+chain(up)+[edge(up[j],low[k]) for j in range(len(up)) for k in [j,j+1]];pinroll(low[0],low[-1]);l=[nodal(p,v) for p,v in zip(up,[-8]*6 if i==30 else [-8,-12,-10,-6])]
    elif i==35:
        low=[coord(x,0) for x in range(0,19,3)];up=[coord(x,3) for x in range(0,19,3)];mid=[coord(x,1.5) for x in range(0,19,3)];n=low+up+mid
        # Original source intentionally delegates K endpoints to the public
        # per-member schedule. Do not assert an invented original K direction.
        e=chain(low)+chain(up)+[edge(a,b,'A2') for a,b in zip(low,mid)]+[edge(a,b,'A2') for a,b in zip(mid,up)]
        pinroll(low[0],up[-1]);l=[nodal(up[j],-12) for j in [1,2,3]]
    elif i==36:
        low=[coord(x,0) for x in range(0,13,3)];up=[coord(x,2.5) for x in range(0,13,3)];mid=[coord(x,1.25) for x in [1.5,4.5,7.5,10.5]];n=low+up+mid
        e=chain(low)+chain(up)+[edge(a,b,'A2') for a,b in zip(low,up)]+[edge(c,p,'A2') for j,c in enumerate(mid) for p in [low[j],up[j],low[j+1],up[j+1]]];pinroll(low[0],low[-1]);l=[nodal(up[j],-10) for j in [1,2,3]]
    elif i==39:
        levels=[[coord(x,z) for x in range(0,21,4)] for z in [0,1.5,3]];n=sum(levels,[])
        e=sum([chain(ps,s) for ps,s in zip(levels,['A3','A2','A1'])],[])
        for a,b in zip(levels,levels[1:]):e += [edge(x,y,'A4') for x,y in zip(a,b)]+[edge(a[j],b[j+1],'A4') for j in range(5)]
        pinroll(levels[0][0],levels[0][-1]);l=[nodal(levels[2][j],-12) for j in range(1,5)]
    elif i in [40,41]:
        s=4 if i==40 else 6;bottom=[coord(0,0,0),coord(s,0,0),coord(s,0,s),coord(0,0,s)];top=[coord(2,3,2)] if i==40 else [coord(4,3,2),coord(3,-2,3)]
        n=bottom+top;e=chain(bottom+[bottom[0]])+[edge(a,b) for a in bottom for b in top]
        if i==41:e += [edge(*top)]
        for p in bottom:fixed(p)
        l=[nodal(top[0],-30)] if i==40 else [nodal(top[0],-30,x=10),nodal(top[1],-20,y=8)]
    elif i==42:
        levels=[[coord(x,z,y) for x,y in [(0,0),(4,0),(2,2*math.sqrt(3))]] for z in [0,2.5,5,7.5]];n=sum(levels,[])
        e=sum([chain(ps+[ps[0]],'A2') for ps in levels],[])
        for a,b in zip(levels,levels[1:]):e += [edge(a[j],b[j],'A1') for j in range(3)]+[edge(a[j],b[(j+1)%3],'A3') for j in range(3)]
        for p in levels[0]:fixed(p)
        l=[nodal(levels[3][0],-10,x=12),nodal(levels[3][1],-10,y=8),nodal(levels[3][2],-10)]
    else:
        coords={43:[(0,0),(18,0),(0,7),(18,7),(9,9)],44:[(0,0),(0,9),(18,0),(18,9),(36,0),(36,9),(9,9),(27,11)],45:[(0,0),(21,0),(0,6),(21,7.5),(10.5,6.75)],46:[(0,0),(0,9),(18,3),(18,9),(36,0),(36,9),(18,6)],47:[(0,0),(0,3),(0,7),(18,0),(18,3),(18,7),(6,3),(12,3)],48:[(0,0),(0,6),(10,0),(10,8),(20,0),(20,6)],49:[(0,0),(24,0),(0,6),(6,8),(14,7),(18,9),(24,6)],50:[(0,0),(12,0),(30,0),(40,0),(0,6),(12,6),(12,8),(30,7),(30,8),(40,7),(6,6),(21,8),(35,7)]}[i]
        n=[coord(*p) for p in coords]
        columns={43:[(0,2),(1,3)],44:[(0,1),(2,3),(4,5)],45:[(0,2),(1,3)],46:[(0,1),(4,5),(2,6),(6,3)],47:[(0,1),(1,2),(3,4),(4,5)],48:[(0,1),(2,3),(4,5)],49:[(0,2),(1,6)],50:[(0,4),(1,5),(5,6),(2,7),(7,8),(3,9)]}[i]
        roofs={43:[(2,4,'B1',-6),(4,3,'B1',-6)],44:[(1,6,'B1',-6),(6,3,'B1',-6),(3,7,'B2',-6),(7,5,'B2',-6)],45:[(2,4,'B1',-8),(4,3,'B1',-8)],46:[(1,3,'B1',-6),(3,5,'B1',-6)],47:[(2,5,'B1',-6),(1,6,'B2',-4),(4,7,'B2',-8)],48:[(1,3,'B1',-6),(3,5,'B1',-6)],49:[(2,3,'B1',-5),(3,4,'B1',-5),(4,5,'B1',-7),(5,6,'B1',-7)],50:[(4,10,'B1',-5),(10,5,'B1',-5),(6,11,'B1',-7),(11,8,'B1',-7),(7,12,'B1',-6),(12,9,'B1',-6)]}[i]
        e=[edge(n[a],n[b],'C2' if i==48 and a==2 else 'C1') for a,b in columns]+[edge(n[a],n[b],s) for a,b,s,w in roofs]
        l=[dist(n[a],n[b],w) for a,b,s,w in roofs]
        for j in {43:[0,1],44:[0,2,4],45:[0,1],46:[0,2,4],47:[0,3],48:[0,2,4],49:[0,1],50:[0,1,2,3]}[i]:fixed(n[j])
        if i in [43,45]:support[n[0]]=(True,True,True,True,False,True)
        if i==46:l += [nodal(n[6],-49,x=4.9)]
    dim3=i in [40,41,42]
    default=(False,False,False,True,True,True) if dim3 else (False,True,False,True,truss,True)
    return dict(nodes=n,edges=e,loads=l,supports={p:support.get(p,default) for p in n},truss=truss,dim3=dim3)

# Source-requested observable sites. Member sites here use endpoint coordinates,
# not author quantity IDs. Sources sometimes permit extra explicit disambiguation.
OBS={
 26:[('n',(12.5,0),'uz'),('m',((15,0),(19,0)),'M2')],
 27:[('n',(7.5,2.5),'uz'),('m',((0,2.5),(2.5,0)),'N')],
 28:[('n',(12,3),'uz'),('m',((15,0),(18,1.6)),'N')],
 29:[('n',(6,3),'uz'),('m',((4,0),(6,3)),'N')],
 30:[('n',(5,2),'uz'),('m',((0,0),(1,2)),'N')],
 31:[('n',(9,3),'uz'),('m',((0,0),(3,3)),'N'),('m',((0,3),(3,0)),'N')],
 32:[('n',(6,2.5),'uz'),('m',((3,0),(6,2.5)),'N')],
 33:[('n',(6,0),'uz'),('m',((6,3),(9,3)),'N')],
 34:[('n',(8,4),'uz'),('m',((4,0),(8,4)),'N'),('m',((12,0),(8,4)),'N')],
 35:[('n',(9,3),'uz'),('n',(18,3),'Fz')],
 36:[('n',(6,2.5),'uz')]+[('m',(p,(1.5,1.25)),'N') for p in [(0,0),(0,2.5),(3,0),(3,2.5)]],
 37:[('n',(7,2.2),'uz'),('m',((10.5,2.2),(12,0)),'N')],
 38:[('n',(12,3.2),'uz'),('n',(0,0),'Fx')],
 39:[('n',(8,3),'uz'),('m',((0,1.5),(4,1.5)),'N')],
 40:[('n',(2,2,3),'uz'),('m',((0,0,0),(2,2,3)),'N'),('m',((4,0,0),(2,2,3)),'N')],
 41:[('n',p,c) for p in [(4,2,3),(3,3,-2)] for c in ['ux','uy','uz']]+[('m',((4,2,3),(3,3,-2)),'N')],
 42:[('n',(0,0,7.5),'ux'),('n',(4,0,7.5),'uy'),('m',((0,0,0),(4,0,2.5)),'N')],
 43:[('n',(9,9),'uz'),('n',(18,0),'My')],
 44:[('n',(9,9),'uz'),('n',(27,11),'uz'),('m',((18,0),(18,9)),'N')],
 45:[('n',(10.5,6.75),'uz'),('n',(21,0),'My')],
 46:[('n',(18,6),'ux'),('n',(18,3),'My')],
 47:[('n',(6,3),'uz'),('n',(12,3),'uz'),('m',((18,3),(12,3)),'M2')],
 48:[('n',(10,8),'uz'),('m',((10,0),(10,8)),'N'),('n',(10,0),'Fz')],
 49:[('n',(14,7),'uz'),('n',(18,9),'ux'),('n',(18,9),'uz')],
 50:[('n',p,'uz') for p in [(6,6),(21,8),(35,7)]]+[('n',p,'My') for p in [(12,0),(30,0)]]}

def normalize_site(p):return coord(*p) if len(p)==2 else tuple(round(x,9) for x in p)
def svg_text(b):return '\n'.join(''.join(e.itertext()) for e in ET.fromstring(b).iter() if e.tag.endswith('text'))

def main():
    tasks={t['id']:t for t in doc(ROOT/'planning/sources/all-tasks-engines-v2.json')};models={m['taskId']:m for m in doc(ROOT/'planning/sources/all-models-engines-v2.json')}
    author_message=raw(ROOT/'.bench-work/state/mm-a-message.md').decode();raw(ROOT/'.bench-work/state/root-message.md')
    entries=[]
    for i in range(26,51):
        case=f'MM-{i:03}';p=CASES/case;m=doc(p/'model-state-1.json');c=doc(p/'contract.json');rr=doc(p/'reference-requests.json');prompt=raw(p/'prompt.txt').decode();properties=raw(p/'properties.txt').decode();ex=expectation(i)
        n={v['id']:v for v in m['nodes']};ele={v['id']:v for v in m['elements']};checks=[]
        def check(name,ok,detail=None):checks.append(dict(check=name,pass_=bool(ok),**({'detail':detail} if detail is not None else {})))
        check('exact_source_node_coordinates', Counter(point(v) for v in n.values())==Counter(ex['nodes']))
        actual_edges=[edge(*(point(n[a]) for a in v['nodes']),v['section']) for v in ele.values()]
        if i!=35:check('exact_source_member_endpoints_and_property_groups',Counter(actual_edges)==Counter(ex['edges']))
        else:
            remain=Counter(actual_edges)-Counter(ex['edges']);check('source_chords_and_all_seven_split_verticals',not (Counter(ex['edges'])-Counter(actual_edges)))
            check('source_K_webs_terminate_at_vertical_midpoints',bool(remain) and all(s=='A2' and {a[2],b[2]} in [{0,1.5},{1.5,3}] and abs(a[0]-b[0])==3 for a,b,s in remain))
        check('source_supports_and_inactive_DOFs',all(tuple(v['restraints'])==ex['supports'].get(point(v)) for v in n.values()))
        check('source_material_and_axial_only_or_rigid_frame_members',all(v['material']=='M1' and (v['type']=='truss')==ex['truss'] for v in ele.values()))
        actual_load=[];resultants={};ends=[]
        for lc in m['load_cases']:
            resultants[lc['id']]=[0.,0.,0.]
            for v in lc['loads']:
                isnode=v['type']=='nodal';ref=v.get('reference_frame');check('global_load_frame:'+v['id'],ref=='global')
                if isnode:site=point(n[v['node']]);vec=tuple(v.get('f'+a,0) for a in 'xyz');length=1
                else:
                    ev=ele[v['element']];site=tuple(sorted(point(n[k]) for k in ev['nodes']));vec=tuple(v.get('w'+a,0) for a in 'xyz');length=math.dist(*site)
                    ends.append(math.isclose(v.get('start',0),0,abs_tol=1e-10) and math.isclose(v.get('end',length),length,abs_tol=1e-10))
                actual_load.append((lc['id'],v['type'],site,vec))
                resultants[lc['id']]=[a+length*b for a,b in zip(resultants[lc['id']],vec)]
        check('exact_source_load_sites_vectors_cases',Counter(actual_load)==Counter(ex['loads']))
        check('line_load_covers_actual_member_length',all(ends))
        check('source_combinations',m['load_combinations']==([{'id':'D','factors':{'D':1}},{'id':'D+L','factors':{'D':1,'L':1}}] if i==26 else []))
        check('no_unrequested_offset_release_roll',all(not any(v.get(k) for k in ['offsets','end_offsets','releases','rotation_angle']) for v in ele.values()))
        check('first_order_no_self_weight',not any(m['analysis_control'].values()))
        check('source_dimension',m['coordinate_system']['dimension']==('3d' if ex['dim3'] else '2d'))
        props_ok=True
        for row in m['materials']+m['sections']:
            line=next((s for s in properties.splitlines() if s.startswith(row['id']+':')),None)
            if line is None:props_ok=False;continue
            public={k:float(v) for k,v in re.findall(r'(E|G|nu|rho|A|Iy|Iz|J)=([0-9.eE+-]+)',line)}
            hidden=row.get('properties',row)
            props_ok &= all(k in public and math.isclose(public[k],hidden[k],rel_tol=1e-7) for k in (['E','G','nu','rho'] if 'E' in row else ['A','Iy','Iz','J']))
        check('public_numeric_properties_match_hidden_authored_completion',props_ok)
        check('public_local_axis_convention',('local 1' in properties and 'local 2' in properties) or ('局部 1' in properties and '局部 2' in properties) or ('局部1' in properties and '局部2' in properties))
        qactual=[]
        for q in rr['states'][0]['quantities']:
            loc=q['location'];site=point(n[loc['id']]) if loc['kind']=='node' else tuple(sorted(point(n[k]) for k in ele[loc['id']]['nodes']))
            qactual.append(('n' if loc['kind']=='node' else 'm',site,q['component']))
            if loc['kind']=='member':check('valid_observation_station:'+q['id'],0<=loc['positionM']<=math.dist(*site)+1e-10 and loc['side'] in ['left','right'])
        wanted=[(kind,normalize_site(site) if kind=='n' else tuple(sorted(normalize_site(x) for x in site)),comp) for kind,site,comp in OBS[i]]
        check('source_requested_observable_sites_components',set(wanted)<=set(qactual))
        if i==26:
            check('both_requested_combinations',Counter((q['selection']['kind'],q['selection']['id']) for q in rr['states'][0]['quantities'])==Counter({('combination','D'):2,('combination','D+L'):2}))
            mq=[q for q in rr['states'][0]['quantities'] if q['component']=='M2'];check('fourth_support_moment_station',all(q['location']['positionM']==0 and point(n[ele[q['location']['id']]['nodes'][0]])==coord(15,0) for q in mq))
        if i==47:
            mq=[q for q in rr['states'][0]['quantities'] if q['component']=='M2'];check('right_cantilever_root_not_free_end',all(q['location']['positionM']==0 and point(n[ele[q['location']['id']]['nodes'][0]])==coord(18,3) for q in mq))
        if i==36:check('center_four_force_balance_derived',len(rr['states'][0]['derived'])==2 and all(x['operation']=='difference' and len(x['operands'])==2 for x in rr['states'][0]['derived']))
        assets={};texts=[]
        for f in c['attachments']:
            b=raw(p/f);assets[f]=HASHES[str(p/f)]
            if f.endswith('.png'):
                with Image.open(p/f) as im: im.verify()
            if f.endswith('.svg'):texts.append(svg_text(b))
        if texts:
            check('all_member_start_end_and_properties_public', all(any(
                f"{v['id']}: {v['nodes'][0]} -> {v['nodes'][1]} / {v['material']} / {v['section']}" in t or
                (f"{v['id']}: {v['nodes'][0]} -> {v['nodes'][1]} / {v['section']}" in t and any(k in t for k in ['全部材料 M1','all M1','All members: M1']))
                for t in texts) for v in ele.values()))
        dxf_record=None
        if 'input.dxf' in c['attachments']:
            d=ezdxf.readfile(p/'input.dxf');space=list(d.modelspace());lines=[v for v in space if v.dxftype()=='LINE' and v.dxf.layer=='STRUCTURE'];dots=[v for v in space if v.dxftype()=='CIRCLE' and v.dxf.layer=='STRUCTURE'];dt=[v.dxf.text for v in space if v.dxftype()=='TEXT'];texts.extend(dt)
            converted=[tuple(sorted((coord(v.dxf.start.x,v.dxf.start.y),coord(v.dxf.end.x,v.dxf.end.y)))) for v in lines]
            check('DXF_metre_units',d.units==6)
            check('DXF_all_source_member_endpoints_after_XY_to_XZ',Counter(converted)==Counter((a,b) for a,b,s in ex['edges']))
            check('DXF_all_connected_joint_dots',Counter(coord(v.dxf.center.x,v.dxf.center.y) for v in dots)==Counter(ex['nodes']))
            check('DXF_directed_member_label_mapping',all(f"{v['id']} {v['nodes'][0]}->{v['nodes'][1]} {v['material']}/{v['section']}" in dt for v in ele.values()))
            check('DXF_explicit_source_coordinate_mapping',any('DXF X->global X, DXF Y->global Z; global Y=0' in t for t in dt))
            layer_counts=Counter(v.dxf.layer for v in space)
            if i in [43,47]:check('architectural_walls_equipment_separate_from_structure',layer_counts['A_WALL']>0 and layer_counts['A_EQUIPMENT']>0 and 'A_WALL' in properties and 'A_EQUIPMENT' in properties)
            dxf_record=dict(parser='ezdxf '+ezdxf.__version__,dxfVersion=d.dxfversion,units=d.units,layers=dict(layer_counts),lineCount=len(lines),jointDotCount=len(dots),allText=dt)
        allpublic='\n'.join(texts+[properties,prompt])
        check('public_load_ids_and_nonzero_components',all(
            v['id'] in allpublic and all(re.search(r'\b'+key+r'='+re.escape(format(val,'g'))+r'(?:\D|$)',allpublic)
            for key,val in v.items() if key in ['fx','fy','fz','wx','wy','wz'] and val)
            for lc in m['load_cases'] for v in lc['loads']))
        if i in [37,39]:
            check('joint_load_table_exact_label_values',all(
                f"{lc['id']}/{v['id']}: {v['node']}: fz={v['fz']:g}" in properties
                for lc in m['load_cases'] for v in lc['loads']))
        if i==32:
            t1=c['turns'][0];t2=c['turns'][1];initial=svg_text(raw(p/'input-initial.svg'));resolved=svg_text(raw(p/'input-resolved.svg'))
            check('delayed_height_t1_clarifies_without_resolved_assets',t1['expectation']=='clarify' and t1['state'] is None and set(t1['attachments'])=={'input-initial.png','input-initial.svg','properties.txt'})
            check('delayed_height_labels_hidden_and_X_chain_retained',all(s not in initial for s in ['Z=1.25','Z=2.5','Z=5/3','Z=5/6']) and initial.count('height ?')==4 and 'Ridge x is derivable' in initial)
            check('resolved_exact_roof_elevations',t2['state']==1 and all(s in resolved for s in ['Z=1.25','Z=2.5','Z=5/3','Z=5/6']))
            # Initial schematic is deliberately distorted and carries no world
            # coordinate metadata, so its pixels do not preserve exact roof rise.
            check('initial_svg_no_world_geometry_metadata',not any(k in raw(p/'input-initial.svg').decode() for k in ['data-z','data-y','data-node','metadata']))
        if i==43:
            public='\n'.join([prompt,properties,c['turns'][0]['instruction']]+texts)
            check('source_actual_slope_load_basis_explicit_in_public', bool(re.search(r'actual (member |slope )?length|实际.*长|沿.*杆.*长',public)), 'Original source requires an explicit public global downward6 kN/m per actual slope-length basis; hidden load range is checked separately.')
        entry=dict(caseId=case,approved=False,blindReconstruction=False,sourceFields={k:tasks[case][k] for k in ['title','scenario','inputForm','expectedOutput']},originalModelSpec=models[case]['spec'],checks=checks,passed=sum(x['pass_'] for x in checks),failed=sum(not x['pass_'] for x in checks),nodes=len(n),elements=len(ele),resultants=resultants,attachments=assets,dxf=dxf_record,expectedOriginalEdges=[list(x) for x in ex['edges']],propertyNumericsAuthority='Original source prescribes groups only; numeric appendix consistency checked, not claimed pre-existing source values')
        entries.append(entry)
    changed=[p for p,h in HASHES.items() if hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h]
    result=dict(schemaVersion=1,createdAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),scope='MM-026 through MM-050, original model/task guided; no author checker imported',approved=False,blindReconstruction=False,authorMessageAtStart=author_message[-1800:],cases=entries,readHashes=HASHES,changedDuringRead=changed,summary=dict(cases=len(entries),checks=sum(e['passed']+e['failed'] for e in entries),passed=sum(e['passed'] for e in entries),failed=sum(e['failed'] for e in entries),DXFcases=[e['caseId'] for e in entries if e['dxf']]))
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result['summary']));print('changedDuringRead',changed)
    for e in entries:
        for c in e['checks']:
            if not c['pass_']: print(e['caseId'],c)
    return 1 if result['summary']['failed'] or changed else 0

if __name__=='__main__':sys.exit(main())
