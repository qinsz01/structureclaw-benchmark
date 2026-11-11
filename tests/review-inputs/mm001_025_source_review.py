#!/usr/bin/env python3
"""Independent source-directed MM001--025 audit; no author/solver imports.

Fixtures below were transcribed from ORIGINAL model.spec and task.expectedOutput,
not from author builders/checks. Numerical appendix values are author completions;
they are checked for public/private consistency, not called original source facts.
Run with the main venv site-packages on PYTHONPATH (ezdxf and Pillow).
"""
import argparse
import collections
import datetime
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path('/mnt/nas/qsz/01research/02structureclaw-bench')
SOURCE_HASHES = {
    'all-tasks-engines-v2.json': '0ad39e467a2a86f0cbdafbaa688b29863d0de657b186d9757b6f403cb3e36dc5',
    'all-models-engines-v2.json': 'ca7b1683b31ed62c3b5de1940c7d6590708fe25421e410c3a3d7b9a0d309f700',
}

# x stations include source-required connected load/observation points. Unless
# specified below all z=0, material=M1, section=B1, case=D, load axes global.
# Supports are physical active-plane (Ux,Uz,Ry): F=111,P=110,R=010.
# Distributed regions are (case,x_start,x_end,wz); nodal actions (x,component,value).
SPEC = {
 1: ([0,3,6], {0:'F',6:'F'}, [('D',0,6,-20)], []),
 2: ([0,3], {0:'F'}, [], [(3,'my',12)]),
 3: ([0,1,6,8], {1:'P',6:'R'}, [('D',1,6,-15)], [(8,'fz',-10)]),
 4: ([0,3,4,6,8,12], {0:'P',12:'R'}, [('D',0,3,-15),('D',8,12,-9)], [(4,'fz',-50)]),
 5: ([0,2,4], {0:'F',4:'R'}, [], [(2,'fz',-25)]),
 6: ([0,2,4,6,8], {0:'P',8:'R'}, [], [(2,'fz',-18),(4,'fz',-30),(6,'fz',-12)]),
 7: ([0,3,6], {0:'P',6:'R'}, [], [(3,'fz',-15)]),
 8: ([0,3,4.5,6,9], {0:'P',9:'R'}, [('D',0,3,-12),('D',6,9,-6)], []),
 9: ([0,2,5,7,10], {0:'P',10:'R'}, [], [(2,'fz',30),(7,'fz',-45),(5,'my',15)]),
 10: ([0,2,4,6,8], {0:'F',8:'F'}, [('D',2,6,-8),('L',0,2,-6),('L',6,8,-6)], []),
 11: ([0,4,7], {0:'F',4:'R'}, [('D',0,7,-10)], [(7,'fz',-20)]),
 12: ([0,4,6], {0:'F'}, [], [(6,'fz',-20)]),
 13: ([0,3,4.5,6,9], {0:'P',9:'R'}, [('D',0,9,-12)], [(3,'fz',-20)]),
 14: ([0,2,5,8,10], {0:'P',10:'R'}, [('D',0,5,-9)], [(8,'my',25)]),
 15: ([0,2.5,5,8,11], {0:'F',5:'R',11:'R'}, [('D',0,11,-12)], []),
 16: ([0,4,7.5,11,13], {0:'P',4:'R',11:'R'}, [('D',0,11,-10),('D',11,13,-6)], [(7.5,'fz',-30)]),
 17: ([0,4,6.5,9,13], {0:'P',4:'R',9:'R',13:'F'}, [('D',0,13,-15)], []),
 18: ([0,5,8.5,12,15], {0:'P',5:'R',12:'R',15:'R'}, [('D',0,5,-16),('D',12,15,-9)], []),
 19: ([0,4,7,10,14], {0:'P',4:'R',10:'R',14:'R'}, [('D',0,14,-8),('L',4,10,-10),('W',0,4,4)], []),
 20: ([0,3,8,15,16], {0:'P',3:'R',8:'R',15:'R'}, [('D',0,3,-8),('D',3,8,-10),('D',8,15,-12)], [(16,'fz',-8)]),
 21: ([0,3,6,12], {0:'F',6:'R',12:'R'}, [('D',0,12,-10)], [(3,'fz',-22)]),
 22: ([-2,0,5,10,12], {0:'P',5:'R',10:'R'}, [('D',-2,12,-8)], [(-2,'fz',-6),(12,'fz',-10)]),
 23: ([0,4,7,10], {0:'P',4:'R',10:'F'}, [], [(4,'fz',-30),(7,'fz',-20)]),
 24: ([0,5,7,9,15,16.5,18], {0:'P',5:'R',9:'R',15:'R',18:'R'}, [('D',0,18,-8),('W',5,9,6),('W',15,18,6)], []),
 25: ([0,5,10], {0:'F',5:'R',10:'F'}, [('D',0,10,-6)], [(5,'my',20)]),
}
OBS = {
 1:[(3,'uz'),(0,'M2')], 2:[(3,'uz'),(3,'ry'),(0,'M2')],
 3:[(0,'uz'),(8,'uz'),(6,'Fz')], 4:[(6,'uz'),(4,'V3','left'),(4,'V3','right')],
 5:[(2,'uz'),(0,'M2'),(4,'Fz')], 6:[(2,'uz'),(4,'uz'),(0,'Fz')],
 7:[(3,'ux'),(3,'uz'),(6,'Fz')], 8:[(4.5,'uz'),(0,'Fz'),(9,'Fz')],
 9:[(5,'uz'),(5,'M2','left'),(5,'M2','right')], 10:[(4,'uz'),(0,'M2')],
 11:[(7,'uz'),(4,'Fz'),(0,'M2')],
 12:[(6,'ux'),(6,'uz')]+[(4,c,s) for c in ['N','V3','M2'] for s in ['left','right']],
 13:[(4.5,'uz'),(3,'V3','left'),(3,'V3','right')],
 14:[(5,'uz'),(8,'M2','left'),(8,'M2','right')],
 15:[(2.5,'uz'),(8,'uz'),(0,'M2')], 16:[(7.5,'uz'),(13,'uz'),(11,'M2')],
 17:[(6.5,'uz'),(13,'M2')],18:[(8.5,'uz'),(5,'M2'),(12,'M2')],
 19:[(7,'uz'),(0,'Fz')],20:[(16,'uz'),(15,'M2')],
 21:[(3,'uz'),(3,'V3','left'),(3,'V3','right'),(0,'M2')],
 22:[(-2,'uz'),(12,'uz'),(5,'Fz')],23:[(7,'uz'),(4,'Fz'),(10,'M2')],
 24:[(7,'uz'),(16.5,'uz'),(18,'Fz')],25:[(5,'ry'),(0,'M2'),(10,'M2')],
}
COMBOS = {10:['D','D+L'],19:['D','D+L','D+W'],24:['D','D+W']}
DXF_CASES = {8,13,18}
TABLE_CASES = {10,14,19,24}
VIEWED = {
 2:['input.png'],4:['input.png'],7:['input-initial.png','input-resolved.png'],
 12:['input.png','joint-detail.png'],14:['input.png'],19:['input.png'],21:['input-initial.png','input-resolved.png'],
 24:['input.png'],25:['input.png'],
}

def sha(b): return hashlib.sha256(b).hexdigest()
def z_at(n,x): return x/3 if n==7 else (3 if n==12 and x==6 else 0)
def assignment(n,a,b):
    mid=(a+b)/2
    return ('M2' if (n==13 and 3<mid<6) or (n==14 and 2<mid<8) else 'M1',
            'B2' if (n==10 and 2<mid<6) or (n==14 and mid>5) or (n==21 and mid>6) else 'B1')

def audit(n,case_root):
    case_id=f'MM-{n:03}'; p=case_root/case_id
    checks=[]; read_hashes={}
    def read(name):
        b=(p/name).read_bytes(); read_hashes[name]=sha(b); return b
    def check(label,ok,observed=None):
        checks.append({'check':label,'pass':bool(ok),'observed':observed})
    m=json.loads(read('model-state-1.json')); c=json.loads(read('contract.json'))
    rr=json.loads(read('reference-requests.json'))['states'][0]
    props=read('properties.txt').decode(); read('prompt.txt')
    for a in c['attachments']: read(a)
    xs,supports,regions,pointloads=SPEC[n]
    byid={v['id']:v for v in m['nodes']}; elems={v['id']:v for v in m['elements']}
    xyz=sorted((v['x'],v['y'],v['z']) for v in byid.values())
    check('source geometry and connected observation/load stations',xyz==[(x,0,z_at(n,x)) for x in xs],xyz)
    edge_data=[]
    for e in elems.values():
        a,b=[byid[i] for i in e['nodes']]
        edge_data.append((a['x'],b['x'],e['material'],e['section']))
    expected_edges=[(a,b,*assignment(n,a,b)) for a,b in zip(xs,xs[1:])]
    check('source member endpoints and property regions', sorted(edge_data)==expected_edges,edge_data)
    restraint_map={'F':[True,True,True],'P':[True,True,False],'R':[False,True,False]}
    check('source support DOFs and inactive plane DOFs',all(
        [v['restraints'][i] for i in [0,2,4]]==restraint_map.get(supports.get(v['x']),[False]*3)
        and all(v['restraints'][i] for i in [1,3,5]) for v in byid.values()))
    check('no invented releases offsets or roll',all(
        e.get('rotation_angle',0)==0 and not e.get('releases') and not e.get('offsets')
        and not e.get('rigid_offsets') for e in elems.values()))
    check('source first-order self-weight-off settings',all(m['analysis_control'].get(k) is False for k in
        ['self_weight','p_delta','rigid_floor','rigid_offsets','construction_stage']))
    check('XZ coordinate convention',m['coordinate_system']['plane']=='xz' and
          m['coordinate_system']['semantics']=='global-z-up')
    actual_dist=[];actual_point=[];frames=[]
    for lc in m['load_cases']:
        for v in lc['loads']:
            frames.append(v.get('reference_frame'))
            components={k:v[k] for k in ['fx','fy','fz','mx','my','mz','wx','wy','wz'] if v.get(k)}
            if v['type']=='distributed':
                a,b=[byid[i]['x'] for i in elems[v['element']]['nodes']]
                actual_dist.append((lc['id'],a,b,components))
            elif v['type']=='nodal':actual_point.append((lc['id'],byid[v['node']]['x'],components))
            else:check('source-supported load type',False,v)
    expected_dist=[(lc,a,b,{'wz':w}) for lc,left,right,w in regions
                   for a,b in zip(xs,xs[1:]) if left<=a and b<=right]
    expected_point=[('D',x,{component:value}) for x,component,value in pointloads]
    key=lambda v:json.dumps(v,sort_keys=True)
    check('source exact load regions components signs and no extra loads',
          sorted(actual_dist,key=key)==sorted(expected_dist,key=key) and
          sorted(actual_point,key=key)==sorted(expected_point,key=key) and set(frames)=={'global'},
          {'distributed':actual_dist,'nodal':actual_point})
    expected_combos=[{'id':k,'factors':{j:1 for j in k.split('+')}} for k in COMBOS.get(n,[])]
    check('source case combinations factors',m['load_combinations']==expected_combos,m['load_combinations'])
    observed=[]
    for q in rr['quantities']:
        loc=q['location']
        if loc['kind']=='node':v=byid[loc['id']];x=v['x'];z=v['z'];side=None
        else:
            a,b=[byid[i] for i in elems[loc['id']]['nodes']]
            length=math.dist((a['x'],a['y'],a['z']),(b['x'],b['y'],b['z']))
            f=loc['positionM']/length;x=a['x']+f*(b['x']-a['x']);z=a['z']+f*(b['z']-a['z']);side=loc.get('side')
        observed.append((q['selection']['kind'],q['selection']['id'],round(x,9),round(z,9),q['component'],side))
    selections=[('combination',v) for v in COMBOS[n]] if n in COMBOS else [('case','D')]
    expected=[(kind,s,x,z_at(n,x),comp,side[0] if side else None) for kind,s in selections for x,comp,*side in OBS[n]]
    def matches(a,b):return a[:5]==b[:5] and (b[5] is None or a[5]==b[5])
    check('all source observations components sides selections covered',all(any(matches(a,b) for a in observed) for b in expected),observed)
    check('no unrelated observation requested',all(any(matches(a,b) for b in expected) for a in observed))
    check('source figure output retained',any(o['kind']=='figure' for o in c['requiredOutputs']))
    check('approval remains pending',c['inputBlindReview']=='pending' and c['sameEngineTruthStatus']=='pending' and c['llmEndToEnd']=='not-run')
    # Public property values are completed by author, independently match every
    # private numeric value (rounding tolerance only), without adopting builders.
    numeric={}
    for line in props.splitlines():
        ma=re.match(r'([MB]\d+):\s*([A-Za-z].*=.*)',line)
        if ma:numeric[ma[1]]={k:float(v) for k,v in re.findall(r'(E|G|nu|rho|A|Iy|Iz|J)=([-+\deE.]+)',ma[2])}
    check('public complete material numeric values match authored completion',all(
        all(k in numeric.get(v['id'],{}) and math.isclose(numeric[v['id']][k],v[k],rel_tol=1e-8)
            for k in ['E','G','nu','rho']) for v in m['materials']))
    check('public complete section numeric values match authored completion',all(
        all(k in numeric.get(v['id'],{}) and math.isclose(numeric[v['id']][k],v['properties'][k],rel_tol=1e-8)
            for k in ['A','Iy','Iz','J']) for v in m['sections']))
    check('appendix local-axis and moment convention explicit',
          ('局部 2 为全局 +Y' in props or 'local 2 is global +Y' in props) and
          ('局部 3=局部1叉乘局部2' in props or 'local 3 = local 1 cross local 2' in props) and
          ('Ry/My' in props))
    check('public load axes force/moment/line units and actual-length basis explicit',
          ('Load components use global XYZ axes' in props or '荷载分量按全局 XYZ 轴' in props) and
          all(k in props for k in ['fx/fy/fz','mx/my/mz','wx/wy/wz','kN/m','kN*m']) and
          ('per actual member length' in props or '按杆件实际长度计' in props))
    check('appendix contains no separate full node/endpoints table',not re.search(r'n\d+\s*(?:->|→)\s*n\d+',props))
    if n not in DXF_CASES:
        names=['input-initial.svg','input-resolved.svg'] if n in [7,21] else ['input.svg']
        for name in names:
            tree=ET.fromstring(read(name));texts=[''.join(e.itertext()) for e in tree.iter() if e.tag.endswith('}text')]
            combined='\n'.join(texts)
            dots=sorted((float(e.attrib['cx']),float(e.attrib['cy'])) for e in tree.iter()
                        if e.tag.endswith('}circle') and e.attrib.get('fill')=='#24394b')
            def points(e):return [tuple(map(float,t.split(','))) for t in e.attrib['points'].split()]
            physical_lines=[points(e) for e in tree.iter() if e.tag.endswith('}polyline')
                            and e.attrib.get('stroke')=='#24394b' and e.attrib.get('stroke-width')=='5']
            check(name+': actual drawn segments join all source stations in order',
                  len(dots)==len(xs) and sorted(physical_lines)==sorted([a,b] for a,b in zip(dots,dots[1:])))
            # Dimensions are authoritative; the schematic may scale X and Z
            # differently. Check the actual elevation sequence, not an angle
            # measured from the raster.
            check(name+': drawn source elevation order',len(dots)==len(xs) and all(
                (b[1]==a[1]) if z_at(n,x)==z_at(n,y) else (b[1]<a[1])
                for (a,b),(x,y) in zip(zip(dots,dots[1:]),zip(xs,xs[1:]))))
            if len(dots)==len(xs):
                red_shafts=[points(e) for e in tree.iter() if e.tag.endswith('}polyline')
                            and e.attrib.get('stroke')=='#b8342b' and len(points(e))==2]
                for x,component,value in pointloads:
                    if component=='fz':
                        tip=dots[xs.index(x)]
                        check(name+': global Z point-force arrow at '+str(x),any(
                            end==tip and start[0]==end[0] and (end[1]-start[1])*value<0
                            for start,end in red_shafts))
            # Visible labels only; no SVG metadata/author comments are oracles.
            check(name+': source X stations and Z elevations visible',all(f'{x:g}' in texts for x in xs)
                  and all(f"{v['id']} [Z={v['z']:g}]" in texts for v in byid.values()))
            for e in elems.values():
                a,b=e['nodes'];mat,sec=assignment(n,byid[a]['x'],byid[b]['x'])
                check(name+': member '+e['id']+' endpoint/property label',f"{e['id']}: {a} -> {b} / {mat} / {sec}" in texts)
            # Load labels belong to actual drawing for PNG-only, to public table
            # for explicit table cases. At t1 MM007 masks exactly the value.
            for lc in m['load_cases']:
                for v in lc['loads']:
                    label=f"{lc['id']}/{v['id']}"
                    values=[f'{k}={value:g}' for k,value in v.items() if k in ['fz','my','wz']]
                    if n==7 and name=='input-initial.svg':values=['fz=?']
                    location=props if n in TABLE_CASES else combined
                    check(name+': visible source load '+label,any(label in t and all(value in t for value in values) for t in location.splitlines()))
        from PIL import Image
        for a in c['attachments']:
            if a.endswith('.png'):
                with Image.open(p/a) as im:im.verify()
    else:
        import ezdxf
        d=ezdxf.readfile(p/'input.dxf');entities=list(d.modelspace())
        lines=[e for e in entities if e.dxftype()=='LINE' and e.dxf.layer=='STRUCTURE']
        endpoints=sorted((tuple(e.dxf.start),tuple(e.dxf.end)) for e in lines)
        check('DXF source physical endpoints and metres',d.header.get('$INSUNITS')==6 and endpoints==[
            ((a,z_at(n,a),0),(b,z_at(n,b),0)) for a,b in zip(xs,xs[1:])],endpoints)
        circles=[tuple(e.dxf.center) for e in entities if e.dxftype()=='CIRCLE' and e.dxf.layer=='STRUCTURE']
        check('DXF connected joints',sorted(circles)==[(x,z_at(n,x),0) for x in xs])
        support_text=[(e.dxf.insert.x,e.dxf.text) for e in entities if e.dxftype()=='TEXT' and e.dxf.layer=='SUPPORTS']
        check('DXF source support labels',sorted(support_text)==sorted((x,{'P':'PIN XZ','R':'ROLLER Z','F':'FIXED'}[k]) for x,k in supports.items()),support_text)
        texts=[e.dxf.text for e in entities if e.dxftype()=='TEXT']
        check('DXF coordinate transform disclosed','DXF X->global X, DXF Y->global Z; global Y=0.' in '\n'.join(texts))
        for e in elems.values():
            a,b=e['nodes'];mat,sec=assignment(n,byid[a]['x'],byid[b]['x'])
            check('DXF source material assignment '+e['id'],f"{e['id']} {a}->{b} {mat}/{sec}" in texts)
        loadtexts=[e for e in entities if e.dxftype()=='TEXT' and e.dxf.layer=='LOADS']
        leader_lines=[e for e in entities if e.dxftype()=='LINE' and e.dxf.layer=='LOADS']
        for lc in m['load_cases']:
            for v in lc['loads']:
                component=next(k for k in ['wz','fz','my'] if k in v)
                target=v.get('element',v.get('node'));target_kind='member' if 'element' in v else 'node'
                # The correction adds explicit node/member target nouns. Accept
                # only that matching noun or the old short label, preserving all
                # numeric/component/location checks rather than exact prose.
                pattern=(re.escape(f"{lc['id']}/{v['id']} @ ")+f'(?:{target_kind} )?'+
                         re.escape(f'{target}: {component}={v[component]:g}'))
                matches_label=[e for e in loadtexts if re.fullmatch(pattern,e.dxf.text)]
                check('DXF source load label '+v['id'],len(matches_label)==1)
                if matches_label and f'@ {target_kind} ' in matches_label[0].dxf.text:
                    text=matches_label[0];px,py,pz=tuple(text.dxf.insert)
                    associated=[e for e in leader_lines if math.isclose(e.dxf.start.x,px,abs_tol=1e-8)
                                and 0<py-e.dxf.start.y<text.dxf.height]
                    if target_kind=='node':
                        node=byid[target];want=(node['x'],node['z'],0)
                    else:
                        a,b=[byid[i] for i in elems[target]['nodes']]
                        want=((a['x']+b['x'])/2,(a['z']+b['z'])/2,0)
                    # Leaders may have visible gaps where they pass behind text.
                    # Verify the start ray AND a terminal segment at the exact
                    # source node/member midpoint, preserving target identity.
                    aligned=[]
                    if len(associated)==1:
                        start=tuple(associated[0].dxf.start);dx=want[0]-start[0];dy=want[1]-start[1]
                        def on_ray(point):
                            return abs((point[0]-start[0])*dy-(point[1]-start[1])*dx)<1e-8 and abs(point[2])<1e-8
                        aligned=[e for e in leader_lines if on_ray(tuple(e.dxf.start)) and on_ray(tuple(e.dxf.end))
                                 and math.dist(tuple(e.dxf.start),want)>math.dist(tuple(e.dxf.end),want)]
                    check('DXF leader source target '+v['id'],len(associated)==1 and associated[0] in aligned and
                          any(math.dist(tuple(e.dxf.end),want)<1e-8 for e in aligned),
                          {'targetKind':target_kind,'target':target,'expectedEndpoint':want,
                           'collinearLeaderSegments':[(tuple(e.dxf.start),tuple(e.dxf.end)) for e in aligned]})
        groups=collections.defaultdict(list)
        for e in loadtexts:groups[(tuple(e.dxf.insert),e.dxf.height,e.dxf.halign,e.dxf.valign)].append(e.dxf.text)
        collisions=[{'placement':k,'texts':v} for k,v in groups.items() if len(v)>1]
        check('DXF load labels do not share exact insertion and alignment',not collisions,collisions)
    if n in [7,21]:
        t1,t2=c['turns'];check('delayed execution gated before resolution',t1['state'] is None and t1['expectation']=='clarify' and t2['state']==1 and t2['expectation']=='analyze')
        check('resolved artifacts absent from first turn',not any('resolved' in a or 'confirmed' in a for a in t1['attachments']))
        if n==7:
            public='\n'.join(read(a).decode() for a in t1['attachments'] if not a.endswith('.png'))+'\n'+t1['instruction']
            check('MM007 first-turn -15 magnitude remains hidden',not re.search(r'(?<![\d.])15(?![\d.])',public))
        else:
            confirmed=read('properties-confirmed.txt').decode()
            check('MM021 conflicting B1 then confirmed B2 table', 'b3: M1 / B1' in props and 'b3: M1 / B2' in confirmed)
    changed=[name for name,digest in read_hashes.items() if sha((p/name).read_bytes())!=digest]
    return {'caseId':case_id,'approved':False,'sourceGuided':True,'checks':checks,
            'failures':[v for v in checks if not v['pass']], 'artifactHashes':read_hashes,
            'changedDuringCaseRead':changed,'actualPNGViewed':VIEWED.get(n,[]),
            'actualDXFInspected':n in DXF_CASES,
            'sourceFixtures':{'stations':xs,'supports':supports,'distributedRegions':regions,'nodalLoads':pointloads,'observations':OBS[n]},
            'sourceDirectedLoadResultants':{lc:sum((b-a)*w for c,a,b,w in regions if c==lc)+
                (sum(v for x,k,v in pointloads if k=='fz') if lc=='D' else 0) for lc in {r[0] for r in regions}|{'D'}}}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--case-root',type=Path,default=ROOT/'.worktrees/mm-a/corpora/research-300/cases')
    ap.add_argument('--out',type=Path,default=Path('docs/implementation/reviews/review-inputs/mm001_025-results.json'));args=ap.parse_args()
    sources={};hashes={}
    for name,want in SOURCE_HASHES.items():
        p=ROOT/'planning/sources'/name;b=p.read_bytes();hashes[str(p)]=sha(b)
        if sha(b)!=want:raise RuntimeError('Original source hash changed: '+str(p))
        sources[name]=json.loads(b)
    tasks={v['id']:v for v in sources['all-tasks-engines-v2.json']}
    models={v['taskId']:v for v in sources['all-models-engines-v2.json']}
    results=[audit(n,args.case_root) for n in range(1,26)]
    for v in results:
        v['originalSourceTask']=tasks[v['caseId']];v['originalSourceModel']=models[v['caseId']]
    # Reviewer-owned mutation controls exercise substantive requirements. They
    # mutate only disposable copies, never the author's worktree.
    negative_controls=[]
    mutations=[
        (7,'global vertical load replaced by local/axial load','model-state-1.json',
         lambda m:m['load_cases'][0]['loads'][0].update(fz=0,fx=-15,reference_frame='local'),
         'source exact load regions components signs and no extra loads'),
        (12,'kink endpoint moved down','model-state-1.json',lambda m:m['nodes'][-1].update(z=0),
         'source geometry and connected observation/load stations'),
        (14,'middle material assignment lost','model-state-1.json',lambda m:m['elements'][1].update(material='M1'),
         'source member endpoints and property regions'),
        (25,'middle roller incorrectly restrains rotation','model-state-1.json',
         lambda m:m['nodes'][1]['restraints'].__setitem__(4,True),'source support DOFs and inactive plane DOFs'),
        (8,'unloaded middle region receives load','model-state-1.json',lambda m:m['load_cases'][0]['loads'].append(
         {'id':'review-mutation','type':'distributed','reference_frame':'global','element':'b2','wz':-12}),
         'source exact load regions components signs and no extra loads'),
        (18,'middle observation reads support instead','reference-requests.json',
         lambda m:m['states'][0]['quantities'][0]['location'].update(id='n1'),
         'all source observations components sides selections covered'),
        (7,'resolved image disclosed on first turn','contract.json',
         lambda m:m['turns'][0]['attachments'].append('input-resolved.png'),
         'resolved artifacts absent from first turn'),
    ]
    with tempfile.TemporaryDirectory(prefix='review-mm001-025-') as tmp:
        for n,description,file,mutate,expected in mutations:
            tmp_root=Path(tmp)/str(len(negative_controls));target=tmp_root/f'MM-{n:03}'
            shutil.copytree(args.case_root/f'MM-{n:03}',target)
            obj=json.loads((target/file).read_text());mutate(obj);(target/file).write_text(json.dumps(obj))
            failures=audit(n,tmp_root)['failures']
            negative_controls.append({'caseId':f'MM-{n:03}','mutation':description,
                'rejectedByExpectedCheck':any(v['check']==expected for v in failures),'expectedCheck':expected})
        import ezdxf
        for label in ['wrong leader target','reintroduced load label collision']:
            tmp_root=Path(tmp)/str(len(negative_controls));target=tmp_root/'MM-013'
            shutil.copytree(args.case_root/'MM-013',target)
            d=ezdxf.readfile(target/'input.dxf')
            if label=='wrong leader target':
                leaders=[e for e in d.modelspace().query('LINE[layer=="LOADS"]') if tuple(e.dxf.end)==(3,0,0)]
                if not leaders:continue  # Earlier source snapshots had no leaders.
                leaders[0].dxf.end=(0,0,0);expected='DXF leader source target D-5'
            else:
                texts=list(d.modelspace().query('TEXT[layer=="LOADS"]'))
                a=next(e for e in texts if e.dxf.text.startswith('D/D-2 @'))
                b=next(e for e in texts if e.dxf.text.startswith('D/D-5 @'))
                b.dxf.insert=a.dxf.insert;expected='DXF load labels do not share exact insertion and alignment'
            # ezdxf suppresses INSUNITS when serializing these minimal R12
            # inputs. Use a modern DXF encoding in disposable mutation copies
            # so the geometry-only mutation does not also drop the unit header.
            d.dxfversion='AC1024';d.header['$INSUNITS']=6
            d.saveas(target/'input.dxf');failures=audit(13,tmp_root)['failures']
            negative_controls.append({'caseId':'MM-013','mutation':label,
                'rejectedByExpectedCheck':any(v['check']==expected for v in failures),'expectedCheck':expected})
    changed_during_run=[f"{v['caseId']}/{name}" for v in results for name,digest in v['artifactHashes'].items()
                        if sha((args.case_root/v['caseId']/name).read_bytes())!=digest]
    message_path=ROOT/'.bench-work/state/mm-a-message.md'
    status={'schemaVersion':1,'reviewedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'caseRoot':str(args.case_root),'approved':False,'blindReconstruction':False,
            'sourceHashes':hashes,'scriptSha256':sha(Path(__file__).read_bytes()),'cases':results,
            'checks':sum(len(v['checks']) for v in results),'failures':sum(len(v['failures']) for v in results),
            'negativeControls':negative_controls,
            'changedDuringRun':changed_during_run,
            'authorMessageAtFinalRead':{'path':str(message_path),'sha256':sha(message_path.read_bytes()),'text':message_path.read_text()},
            'limitations':['Source-directed review, not a blind reconstruction or automatic acceptance.',
                'No Windows, solver, native, LLM trial or numerical reference-value review.',
                'PNG visual sample is explicit; other PNGs decode but were not individually visually inspected.',
                'DXF entities and exact label collisions inspected; no native CAD application viewport used.',
                'All 25 are planar beam cases: architectural distractions, nonzero roll and rigid offsets not source features here.']}
    args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:status[k] for k in ['checks','failures','approved']},indent=2))
    for v in results:
        for f in v['failures']:print(v['caseId'],f['check'],f['observed'])
    print('Negative controls rejected:',sum(v['rejectedByExpectedCheck'] for v in negative_controls),'/',len(negative_controls))
    return bool(status['failures']) or bool(changed_during_run) or not all(v['rejectedByExpectedCheck'] for v in negative_controls)

if __name__=='__main__':raise SystemExit(main())
