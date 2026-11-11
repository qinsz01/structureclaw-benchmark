#!/usr/bin/env python3
"""Independent MM051-075 source-field review; no author builder/check imports.

The hand-transcribed geometric expectations below come from the original task
and model rows. Collinear observation subdivisions are allowed, but complete
coverage, load placement, section/material families, supports and requested
locations are checked. This is source-guided review, never blind acceptance.
"""
import argparse
import copy
import hashlib
import json
import math
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path('/mnt/nas/qsz/01research/02structureclaw-bench')
HERE = Path(__file__).resolve().parents[2]
OUT = HERE / 'docs/implementation/reviews/review-inputs/mm051_075-evidence.json'
TOL = 1e-7
# Actual images opened with view_image during this review, not inferred from SVG.
VISUAL_REVIEWS = {
    (51,'drawing-elevation-XZ.png'):'Full 18m portal, 9m ridge, right slope extension to x20/z17/3; opposite D/W arrows and signed load key visible. Small overhang arrows are crowded but keyed values readable.',
    (53,'drawing-elevation-XZ.png'):'Roof-only -8kN/m and +X12kN roof-joint force visible; intermediate horizontal tie unloaded, left base LOCK X,Z and right FIXED. Prior PNG-only load defect stays closed.',
    (58,'initial-elevation-XZ.png'):'Both base labels [cropped]; no restraint symbol. 6m span,4m height,2m extension and free-end +X50kN are legible. This image does not disclose either missing support.',
    (60,'drawing-elevation-XZ.png'):'Top right slope rises7.2 to8.4m; midpoint8.4/7.8; three bases and member labels/loads readable. Explicit actual-member-length load note visible.',
    (67,'drawing-elevation-XZ.png'):'Bottom centre column absent; transfer joint at5/3.6 connects upper centre column; outer bases and full10m transfer beam legible.',
    (72,'initial-elevation-XZ.png'):'Visible NOT TO SCALE disclaimer; only left elevations0/3.3/7.3/10.4 and no0.5m gap. Graph and all labels remain legible with deliberately schematic right gap.',
    (72,'drawing-elevation-XZ.png'):'Complete drawing visibly labels right3.8/7.8/10.9 and left3.3/7.3/10.4. Short middle column Cc4 and both top connected midpoint nodes discernible.',
    (74,'section-details.png'):'Bounded latest recheck: left Crect roll0 and right roll90 sections show400x700 dimensions and member groups; centre500 square. Local3-before-roll labels are now below and clear of titles; local2-before-roll labels are clear of shifted inertia/property blocks. Prior collision resolved at this viewed PNG hash; original image evidence retained in first-evidence.',
    (75,'drawing-elevation-XZ.png'):'Top central bay is empty; both top external midpoint nodes, all four columns and bases visible. This clean PNG does not display the architectural DXF distractors.',
}
def pt(x, z): return (float(x), 0., float(z))
def near(a, b, tol=TOL): return abs(a-b) <= tol
def close(a, b, tol=TOL): return len(a) == len(b) and all(near(x,y,tol) for x,y in zip(a,b))
def xyz(n): return tuple(n[k] for k in ('x','y','z'))
def dist(a,b): return math.sqrt(sum((x-y)**2 for x,y in zip(a,b)))
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def need(test, text):
    if not test: raise AssertionError(text)

class Spec:
    def __init__(self):
        self.edges=[]; self.supports={}; self.points=[]; self.combos={}; self.outputs=[]
    def edge(self,a,b,section='B1',typ='beam',loads=None,material='M1',roll=0):
        e={'a':pt(*a),'b':pt(*b),'section':section,'type':typ,'loads':loads or {},'material':material,'roll':roll}
        self.edges.append(e); return e
    def col(self,x,levels,section='C1',material='M1',roll=0):
        return [self.edge((x,a),(x,b),section,'column',material=material,roll=roll) for a,b in zip(levels,levels[1:])]
    def fix(self,*points):
        for p in points:self.supports[pt(*p)]=(True,True,True)
    def point(self,x,z,fx=0,fz=0,case='D'):self.points.append({'at':pt(x,z),'case':case,'force':(fx,0,fz,0,0,0)})
    def nodeout(self,x,z,*components):
        for c in components:self.outputs.append({'kind':'node','at':pt(x,z),'component':c})
    def endout(self,edge,at,*components):
        for c in components:self.outputs.append({'kind':'member','edge':self.edges.index(edge),'at':pt(*at),'component':c})

def grid(s,xs,zs,omit_columns=(),omit_beams=(),column_sections=None,beam_sections=None,loads=None):
    """Source grid; omissions use zero-based column/bay and one-based storey."""
    columns={};beams={}
    for j in range(1,len(zs)):
        for i,x in enumerate(xs):
            if (i,j) not in omit_columns:
                columns[i,j]=s.edge((x,zs[j-1]),(x,zs[j]),(column_sections or {}).get((i,j),'C1'),'column')
        for i,(a,b) in enumerate(zip(xs,xs[1:])):
            if (i,j) not in omit_beams:
                beams[i,j]=s.edge((a,zs[j]),(b,zs[j]),(beam_sections or {}).get((i,j),'B1'),loads=(loads or {}).get((i,j),{}))
    s.fix(*[(x,zs[0]) for x in xs if (xs.index(x),1) not in omit_columns])
    return columns,beams

def source_specs():
    # Original model.spec/task.scenario/task.expectedOutput, all 25 rows.
    out={};s=Spec();out[51]=s
    s.col(0,[0,6]);s.col(18,[0,6]);s.fix((0,0),(18,0))
    s.edge((0,6),(9,7.5),loads={'D':-6});s.edge((9,7.5),(18,6),loads={'D':-6})
    s.edge((18,6),(20,6-2/6),loads={'D':-6,'W':10});s.combos={'D':{'D':1},'D+W':{'D':1,'W':1}}
    s.nodeout(20,6-2/6,'uz');s.nodeout(18,0,'Fx','Fz','My')
    s=Spec();out[52]=s
    for x in (0,22):s.edge((x,0),(x,3),'C1','column');s.edge((x,3),(x,7),'C2','column')
    for a,b,sec in [(0,6,'B1'),(6,16,'B2'),(16,22,'B1')]:s.edge((a,7),(b,7),sec,loads={'D':-8})
    s.fix((0,0),(22,0));s.point(22,7,fx=15);s.nodeout(11,7,'uz');s.nodeout(22,7,'ux')
    s=Spec();out[53]=s
    for x in (0,16):s.col(x,[0,3,6])
    s.fix((16,0));s.supports[pt(0,0)]=(True,True,False)
    s.edge((0,6),(16,6),loads={'D':-8});e=s.edge((0,3),(16,3),'B2');s.point(16,6,fx=12)
    s.nodeout(16,6,'ux');s.endout(e,(0,3),'M2')
    s=Spec();out[54]=s
    for x,sec in [(0,'C1'),(12,'C2'),(27,'C1')]:s.col(x,[0,7],sec)
    s.fix((0,0),(12,0),(27,0));s.edge((-2,7),(0,7),'B2',loads={'L':-7});s.edge((0,7),(12,7),loads={'D':-6});s.edge((12,7),(27,7),loads={'D':-6});s.edge((27,7),(30,7),'B2',loads={'L':-7});s.point(27,7,fx=12,case='W')
    s.combos={'D+L':{'D':1,'L':1},'D+W':{'D':1,'W':1}};s.nodeout(-2,7,'uz');s.nodeout(30,7,'uz');s.nodeout(27,7,'ux')
    s=Spec();out[55]=s
    c,b=grid(s,[0,6,10],[0,3.6,7.2],omit_columns=[(0,2)],omit_beams=[(0,2)],loads={(0,1):{'D':-60},(1,1):{'D':-60},(1,2):{'D':-48}})
    s.nodeout(8,7.2,'uz');s.endout(c[1,1],(6,0),'N');s.endout(c[1,1],(6,3.6),'N')
    s=Spec();out[56]=s
    s.col(0,[0,12]);s.col(24,[0,12]);s.fix((0,0),(24,0))
    a=s.edge((0,12),(12,12),loads={'D':-36});b=s.edge((12,12),(24,12),loads={'D':-18});s.edge((12,12),(12,9),'C2','column');s.point(12,9,fx=10,fz=-98)
    s.nodeout(12,9,'ux','uz');s.endout(a,(12,12),'M2');s.endout(b,(12,12),'M2')
    s=Spec();out[57]=s
    c,b=grid(s,[0,6,12],[0,3.6,7.2,10.8],omit_beams=[(1,2)],loads={(i,j):{'D':-10} for i in range(2) for j in range(1,4)})
    for z,f in [(3.6,10),(7.2,15),(10.8,20)]:s.point(12,z,fx=f)
    s.nodeout(12,10.8,'ux');s.endout(c[2,2],(12,3.6),'M2');s.endout(c[2,2],(12,7.2),'M2')
    s=Spec();out[58]=s
    s.col(0,[0,4]);s.col(6,[0,4]);s.fix((0,0),(6,0));s.edge((0,4),(6,4),loads={'D':-8});s.edge((6,4),(8,4),loads={'D':-8});s.point(8,4,fx=50);s.nodeout(8,4,'ux','uz');s.nodeout(6,0,'My')
    s=Spec();out[59]=s
    grid(s,[0,6,9],[0,4.5],loads={(0,1):{'D':-48}});s.nodeout(3,4.5,'uz');s.nodeout(9,4.5,'ux')
    s=Spec();out[60]=s
    for x,z in [(0,7.2),(5.4,7.2),(11.4,8.4)]:s.col(x,[0,3.6,z])
    s.fix((0,0),(5.4,0),(11.4,0))
    for a,b in [((0,3.6),(5.4,3.6)),((5.4,3.6),(11.4,3.6)),((0,7.2),(5.4,7.2)),((5.4,7.2),(11.4,8.4))]:s.edge(a,b,loads={'D':-10,'L':-8})
    s.combos={'1.2D+1.4L':{'D':1.2,'L':1.4}};s.nodeout(8.4,7.8,'uz');s.nodeout(11.4,8.4,'ux')
    s=Spec();out[61]=s
    c,b=grid(s,[0,4.5,12],[0,3.6,7.8],loads={(i,j):{'D':-10} for i in range(2) for j in (1,2)})
    s.supports[pt(0,0)]=(True,True,False);s.supports[pt(12,0)]=(False,True,False);s.point(12,7.8,fx=20);s.nodeout(12,7.8,'ux');s.nodeout(12,0,'ux');s.endout(c[1,1],(4.5,0),'M2')
    s=Spec();out[62]=s
    grid(s,[0,6,12],[0,3.6],loads={(0,1):{'D':-10},(1,1):{'D':-10}})
    c=s.col(0,[3.6,6.9])[0];s.col(6,[3.6,6.9]);s.edge((0,6.9),(6,6.9),loads={'D':-8});s.edge((-2,6.9),(0,6.9),'B2',loads={'D':-12});s.nodeout(-2,6.9,'uz');s.endout(c,(0,6.9),'M2')
    s=Spec();out[63]=s
    grid(s,[0,6],[0,3.6,7.2],loads={(0,1):{'D':-10},(0,2):{'D':-10}})
    a=s.edge((0,0),(6,3.6),'A1','truss');b=s.edge((6,3.6),(0,7.2),'A1','truss');s.point(6,7.2,fx=20);s.nodeout(6,7.2,'ux');s.endout(a,(0,0),'N');s.endout(b,(6,3.6),'N')
    s=Spec();out[64]=s
    grid(s,[0,6],[0,3.6,7.2],loads={(0,1):{'D':-10},(0,2):{'D':-10}})
    s.edge((6,3.6),(7.5,3.6),'B2',loads={'D':-6});e=s.edge((-2,7.2),(0,7.2),'B2',loads={'D':-12});s.nodeout(7.5,3.6,'uz');s.nodeout(-2,7.2,'uz');s.endout(e,(0,7.2),'M2')
    s=Spec();out[65]=s
    c,b=grid(s,[0,5,10],[0,3.3,6.6,9.9],omit_columns=[(1,3)],loads={(i,j):{'D':-v} for i in range(2) for j,v in [(1,12),(2,10),(3,6)]})
    s.point(5,9.9,fz=-25);s.nodeout(5,9.9,'uz');s.endout(c[1,2],(5,3.3),'N');s.endout(c[1,2],(5,6.6),'N')
    s=Spec();out[66]=s
    c,b=grid(s,[0,6,12],[0,3.6,7.2],omit_beams=[(0,1)],column_sections={(1,1):'C2',(1,2):'C2'},beam_sections={(1,1):'B3',(0,2):'B3'},loads={(i,j):{'D':-10} for i in range(2) for j in (1,2)})
    s.edge((0,3.6),(3,3.6),'B1',loads={'D':-10});s.edge((3,3.6),(6,3.6),'B2',loads={'D':-10});s.point(6,7.2,fx=30);s.nodeout(3,3.6,'uz');s.nodeout(6,7.2,'ux')
    s=Spec();out[67]=s
    c,b=grid(s,[0,5,10],[0,3.6,7.2],omit_columns=[(1,1)],beam_sections={(0,1):'B2',(1,1):'B2'},loads={(i,j):{'D':-10} for i in range(2) for j in (1,2)})
    s.nodeout(5,3.6,'uz');s.endout(c[1,2],(5,3.6),'N');s.endout(c[1,2],(5,7.2),'N')
    s=Spec();out[68]=s
    a=s.col(0,[-1.5,2.1,5.7]);b=s.col(6,[0,2.1,5.7]);s.fix((0,-1.5),(6,0))
    for z in (2.1,5.7):s.edge((0,z),(6,z),loads={'D':-10})
    s.nodeout(0,5.7,'ux');s.endout(a[0],(0,-1.5),'M2');s.endout(b[0],(6,0),'M2')
    s=Spec();out[69]=s
    grid(s,[0,6],[0,3.6,7.2],loads={(0,1):{'D':-72},(0,2):{'D':-72}})
    s.edge((-1.2,3.6),(0,3.6),'B2',loads={'D':-15});e=s.edge((6,3.6),(7.2,3.6),'B2',loads={'D':-20});s.nodeout(-1.2,3.6,'uz');s.nodeout(7.2,3.6,'uz');s.endout(e,(6,3.6),'M2')
    s=Spec();out[70]=s
    a=s.edge((0,0),(0,3.3),'C1','column');s.edge((0,3.3),(1,6.6),'C1','column');s.edge((1,6.6),(1,9.9),'C1','column');s.col(6,[0,3.3,6.6,9.9]);s.fix((0,0),(6,0))
    for x,z in [(0,3.3),(1,6.6),(1,9.9)]:s.edge((x,z),(6,z),loads={'D':-60})
    s.nodeout(1,6.6,'ux','uz');s.endout(a,(0,0),'M2')
    s=Spec();out[71]=s
    c,b=grid(s,[0,4,10,14],[0,3.6,7.2],loads={(0,1):{'D':-10},(2,1):{'D':-10},**{(i,2):{'D':-12} for i in range(3)}})
    s.nodeout(7,3.6,'uz');s.endout(c[1,1],(4,0),'N');s.endout(c[1,1],(4,3.6),'N')
    s=Spec();out[72]=s
    s.col(0,[0,3.3,7.3,10.4]);c=s.col(5,[0,3.3,3.8,7.3,7.8,10.4,10.9]);s.col(12,[0,3.8,7.8,10.9]);s.fix((0,0),(5,0),(12,0))
    for z in (3.3,7.3,10.4):s.edge((0,z),(5,z),loads={'D':-10});s.edge((5,z+.5),(12,z+.5),loads={'D':-10})
    s.nodeout(2.5,10.4,'uz');s.nodeout(8.5,10.9,'uz');s.endout(c[3],(5,7.3),'M2');s.endout(c[3],(5,7.8),'M2')
    s=Spec();out[73]=s
    c,b=grid(s,[0,6,12],[0,3.6,7.2],loads={(i,j):{'D':-10} for i in range(2) for j in (1,2)})
    for e in c.values():e['material']='C40'
    for (i,j),e in b.items():e['material']='C30' if j==1 else 'C35'
    s.edge((-1.5,7.2),(0,7.2),'BC',loads={'D':-8},material='C35');s.nodeout(-1.5,7.2,'uz');s.endout(c[0,1],(0,0),'N');s.endout(c[0,1],(0,3.6),'N')
    s=Spec();out[74]=s
    c,b=grid(s,[0,7,11],[0,3.6,7.2],column_sections={(i,j):'Crect' for i in (0,2) for j in (1,2)},loads={(i,j):{'D':-12} for i in range(2) for j in (1,2)})
    for j in (1,2):c[2,j]['roll']=90
    s.point(11,7.2,fx=25);s.nodeout(11,7.2,'ux');s.endout(c[0,1],(0,0),'M2');s.endout(c[2,1],(11,0),'M3')
    s=Spec();out[75]=s
    grid(s,[0,5,10,15],[0,3.6,7.2],omit_beams=[(1,2)],loads={(i,j):{'D':-v} for i in range(3) for j,v in [(1,10),(2,8)]})
    s.nodeout(2.5,7.2,'uz');s.nodeout(12.5,7.2,'uz');s.nodeout(5,0,'Fx','Fz','My');s.nodeout(10,0,'Fx','Fz','My')
    return out

def interval(a,b,e,tol=TOL):
    v=[y-x for x,y in zip(e['a'],e['b'])];l2=sum(x*x for x in v)
    values=[]
    for p in (a,b):
        t=sum((x-y)*z for x,y,z in zip(p,e['a'],v))/l2
        if t < -tol or t > 1+tol or dist(p,[x+t*y for x,y in zip(e['a'],v)])>tol:return None
        values.append(t)
    return tuple(values)

def check_graph(spec,segments,tol=TOL):
    covered=defaultdict(list);mapping={}
    for name,a,b in segments:
        candidates=[(i,interval(a,b,e,tol)) for i,e in enumerate(spec.edges) if interval(a,b,e,tol) is not None]
        need(len(candidates)==1,f'{name}: segment {a}->{b} is not one unique source member')
        i,ts=candidates[0];need(abs(ts[1]-ts[0])>tol,f'{name}: zero member');covered[i].append(sorted(ts));mapping[name]=i
    for i,e in enumerate(spec.edges):
        cursor=0
        for a,b in sorted(covered[i]):need(near(a,cursor,tol),f'source edge {i} gap/overlap at {cursor}: {a,b}');cursor=b
        need(near(cursor,1,tol),f'source edge {i} incomplete at {cursor}')
    return mapping

def model_check(spec,model,requests):
    ns={n['id']:n for n in model['nodes']};es={e['id']:e for e in model['elements']}
    need(len(ns)==len(model['nodes']) and len(es)==len(model['elements']),'duplicate IDs')
    seg=[(e['id'],xyz(ns[e['nodes'][0]]),xyz(ns[e['nodes'][1]])) for e in es.values()]
    mapping=check_graph(spec,seg)
    used=Counter(n for e in es.values() for n in e['nodes'])
    for n in ns.values():
        p=xyz(n);expect=spec.supports.get(p,(False,False,False))
        need(tuple(n['restraints'][i] for i in (0,2,4))==expect,f"{n['id']}: in-plane restraint differs from source")
        need(all(n['restraints'][i] for i in (1,3,5)),f"{n['id']}: planar restraint missing")
        need(used[n['id']]>0,f"{n['id']}: disconnected node")
    for p in spec.supports:need(any(close(xyz(n),p) for n in ns.values()),f'missing source support {p}')
    for e in es.values():
        want=spec.edges[mapping[e['id']]]
        for k in ('section','material','type'):need(e[k]==want[k],f"{e['id']}: {k} {e[k]} != source {want[k]}")
        need(near(e.get('rotation_angle',0),want['roll']),f"{e['id']}: source roll mismatch")
        need(not e.get('releases') and not e.get('offsets'),f"{e['id']}: unrequested release/offset")
    loadmap=defaultdict(list);points=[];resultants={}
    for lc in model['load_cases']:
        resultant=[0.]*6
        for l in lc['loads']:
            need(l.get('reference_frame')=='global',f"{l['id']}: non-global load axes")
            if l['type']=='distributed':
                e=es[l['element']];a,b=[xyz(ns[x]) for x in e['nodes']];L=dist(a,b)
                need(not any(l.get(k,0) for k in ['wx','wy','mx','my','mz']),f"{l['id']}: extra load component")
                need(not any(k in l for k in ['start','end','start_position','end_position']),f"{l['id']}: partial source full load")
                loadmap[(lc['id'],e['id'])].append(l.get('wz',0));force=(0,0,l.get('wz',0)*L,0,0,0);at=tuple((x+y)/2 for x,y in zip(a,b))
            elif l['type']=='nodal':
                at=xyz(ns[l['node']]);force=tuple(l.get(k,0) for k in ('fx','fy','fz','mx','my','mz'));points.append((lc['id'],at,force))
            else:raise AssertionError(f'unexpected source load type {l["type"]}')
            for i,f in enumerate(force):resultant[i]+=f
            resultant[3]+=at[1]*force[2]-at[2]*force[1];resultant[4]+=at[2]*force[0]-at[0]*force[2];resultant[5]+=at[0]*force[1]-at[1]*force[0]
        resultants[lc['id']]=resultant
    expected_cases=set(p['case'] for p in spec.points)|{c for e in spec.edges for c in e['loads']}
    need(set(resultants)==expected_cases,'source load-case set mismatch')
    for e in es.values():
        wants=spec.edges[mapping[e['id']]]['loads']
        for c in expected_cases:need(loadmap[c,e['id']]==([wants[c]] if c in wants else []),f"{c}:{e['id']}: load location/intensity mismatch")
    need(len(points)==len(spec.points),'extra/missing nodal loads')
    for p in spec.points:need(any(c==p['case'] and close(at,p['at']) and close(f,p['force']) for c,at,f in points),f'source nodal force missing {p}')
    need({c['id']:c['factors'] for c in model['load_combinations']}==spec.combos,'source combinations differ')
    need(model['coordinate_system']['plane']=='xz' and model['coordinate_system']['semantics']=='global-z-up','XZ to global XYZ convention differs')
    need(all(model['analysis_control'].get(k) is False for k in ['self_weight','p_delta','rigid_floor','rigid_offsets']),'source first-order/no selfweight/no rigid diaphragm changed')
    selectors=[('combination',c) for c in spec.combos] if spec.combos else [('case','D')]
    quantities=requests['states'][0]['quantities'];observations=[]
    for want in spec.outputs:
        for kind,selection in selectors:
            found=[]
            for q in quantities:
                if q['component']!=want['component'] or q['selection']!={'kind':kind,'id':selection}:continue
                loc=q['location']
                if want['kind']=='node' and loc['kind']=='node':
                    if close(xyz(ns[loc['id']]),want['at']):found.append(q)
                elif want['kind']=='member' and loc['kind']=='member' and mapping[loc['id']]==want['edge']:
                    e=es[loc['id']];a,b=[xyz(ns[x]) for x in e['nodes']];L=dist(a,b);t=loc['positionM']/L;p=tuple(x+t*(y-x) for x,y in zip(a,b))
                    if close(p,want['at']):
                        need(loc.get('side')==('right' if near(t,0) else 'left'),f"{q['id']}: wrong internal cut side")
                        found.append(q)
            need(found,f'missing source output {want} selection {selection}')
            for q in found:need(q['unit']==('m' if q['component'] in ('ux','uy','uz') else 'kN*m' if q['component'].startswith('M') else 'kN'),f"{q['id']}: units")
            observations.extend(q['id'] for q in found)
    return {'nodes':len(ns),'physicalElements':len(es),'sourceSegments':len(spec.edges),'resultantsFxFyFzMxMyMz':resultants,'sourceOutputRequestsChecked':observations},mapping

def svg_read(path):
    root=ET.parse(path).getroot();children=list(root);xticks=[];zticks=[]
    for a,b in zip(children,children[1:]):
        if a.tag.endswith('line') and a.get('stroke')=='#e2e7ed' and b.tag.endswith('text'):
            try:value=float(b.text)
            except (ValueError,TypeError):continue
            if a.get('x1')==a.get('x2'):xticks.append((float(a.get('x1')),value))
            if a.get('y1')==a.get('y2'):zticks.append((float(a.get('y1')),value))
    def inverse(ticks,p):
        a,b=ticks[0],ticks[-1];return a[1]+(p-a[0])*(b[1]-a[1])/(b[0]-a[0])
    def p(x,y):return (inverse(xticks,float(x)),0.,inverse(zticks,float(y)))
    segments=[];nodes={};supports={};lastnode=None
    for i,e in enumerate(children):
        if e.tag.endswith('line') and e.get('stroke-width')=='4' and e.get('stroke') in ('#24364b','#247a58'):
            label=next((t.text for t in children[i+1:] if t.tag.endswith('text')),None)
            label=label.split(' roll=')[0]
            segments.append((label,p(e.get('x1'),e.get('y1')),p(e.get('x2'),e.get('y2'))))
        if e.tag.endswith('circle') and e.get('fill')=='#004488':
            label=children[i+1].text;nodes[label]=p(e.get('cx'),e.get('cy'));lastnode=label
        if e.tag.endswith('text') and e.get('fill')=='#a03030':supports[lastnode]=e.text
    texts=[e.text or '' for e in root.iter() if e.tag.endswith('text')]
    return {'segments':segments,'nodes':nodes,'supports':supports,'texts':texts,'xticks':xticks,'zticks':zticks}

def public_check(spec,model,contract,casepath,number):
    props=json.loads((casepath/'properties.json').read_text());assign=json.loads((casepath/'assignments.json').read_text());es={e['id']:e for e in model['elements']};ns={n['id']:n for n in model['nodes']}
    for k in ('materials','sections','analysis_control','coordinate_system'):need(props[k]==model[k],f'public {k} inconsistent with hidden model')
    need(set(a['id'] for a in assign)==set(es),'public assignments missing members')
    for a in assign:
        need(not any(k in a for k in ('nodes','endpoints','x','y','z')),'public endpoint/coordinate bypass')
        for k in ('type','material','section'):need(a[k]==es[a['id']][k],f"assignment {a['id']} {k}")
        need(a['rotation_angle']==es[a['id']].get('rotation_angle',0),'public roll mismatch')
    for m in props['materials']:
        need(all(k in m and m[k]>0 for k in ('E','G','rho')) and 'nu' in m,'incomplete material appendix')
        need(near(m['G'],m['E']/(2*(1+m['nu'])),1e-6),'inconsistent isotropic material E/G/nu')
    for sec in props['sections']:
        pr=sec['properties'];need(all(pr[k]>0 for k in ('A','Iy','Iz','J')),'incomplete section appendix')
        if sec.get('shape',{}).get('kind')=='rectangular':
            b,h=[sec['shape'][k]/1000 for k in ('B','H')]
            for k,v in [('A',b*h),('Iy',b*h**3/12),('Iz',h*b**3/12)]:need(near(pr[k],v,1e-10),f'{sec["id"]}: rectangular {k} differs from dimensions')
    if number>=69:
        mats={m['id']:m for m in model['materials']};secs={s['id']:s for s in model['sections']}
        for e in model['elements']:
            mat=mats[e['material']];need(mat['type']=='concrete','source concrete material')
            expected_grade='C35' if number==70 else e['material'] if number==73 else 'C30'
            need(mat['name']==expected_grade,f'source concrete grade {expected_grade}')
            expected_shape=(500,500) if e['type']=='column' else (250,500) if e['section'] in ('BC','B2') else (300,600)
            if number==74 and e['section']=='Crect':expected_shape=(400,700)
            shape=secs[e['section']]['shape'];need((shape['B'],shape['H'])==expected_shape,f'source section dimensions {e["id"]}')
    if number in (56,59,62,75):
        # The ORIGINAL inputForm assigns geometry/connectivity to architectural
        # DXF. A source-required CAD-only correction must not be failed merely
        # because the formerly bypassing clean SVG was removed. Full independent
        # CAD graph, directed endpoints, label associations and layers remain
        # required by dxf_check, run separately for every such case.
        allowed={'section-details.png','section-details.svg','input.dxf','properties.json','assignments.json','loads.json'}
        need(set(contract['attachments'])==allowed,'architectural public attachment modality differs')
        need(set(contract['turns'][0]['attachments'])==allowed,'architectural first-turn clean geometry bypass')
        need(not any(casepath.glob('drawing-*.png')) and not any(casepath.glob('drawing-*.svg')),'architectural clean structural drawing still present')
        need('input.dxf' in contract['turns'][0]['attachments'],'architectural CAD geometry missing')
        need('DXF' in props['localAxes']['beam'] and 'LINE' in props['localAxes']['beam'],'CAD member direction contract missing')
        boundaries={b['node']:set(b['restrainedDOFs']) for b in props['boundaryConditions']}
        dofs=('ux','uy','uz','rx','ry','rz')
        need(boundaries=={n['id']:{d for d,v in zip(dofs,n['restraints']) if v} for n in ns.values()},'architectural explicit boundary appendix mismatch')
        loads=json.loads((casepath/'loads.json').read_text())
        need(loads['load_cases']==model['load_cases'] and loads['load_combinations']==model['load_combinations'],'architectural public load table inconsistent')
        return {'sourceGeometryModality':'architectural DXF only; separate full source-graph CAD check required','firstTurnCleanGeometryBypassAbsent':True,'publicPropertyConsistency':True,'publicNumericalMaterialDimensions':True,'publicBoundaryConsistency':True}
    full=svg_read(casepath/'drawing-elevation-XZ.svg');check_graph(spec,full['segments'],1e-4)
    need(set(full['nodes'])==set(ns),'SVG node labels differ')
    for name,p in full['nodes'].items():need(close(p,xyz(ns[name]),1e-4),f'SVG axis-calibrated node {name} disagrees with source-checked model')
    for name,a,b in full['segments']:
        need(name in es,f'SVG member label {name} absent')
        need(close(a,xyz(ns[es[name]['nodes'][0]]),1e-4) and close(b,xyz(ns[es[name]['nodes'][1]]),1e-4),f'SVG direction/endpoints {name}')
    for name,n in ns.items():
        expected=spec.supports.get(xyz(n),(False,False,False));mark=full['supports'].get(name,'')
        if expected==(True,True,True):need(mark=='FIXED',f'SVG fixed {name}')
        elif expected==(True,True,False):need(mark=='LOCK X,Z' or 'PIN' in mark,f'SVG pin {name}')
        elif expected==(False,True,False):need(mark=='LOCK Z' or 'ROLL' in mark,f'SVG roll {name}')
        else:need(not mark,f'SVG unsupported node {name} has support {mark}')
    visible='\n'.join(full['texts'])
    for lc in model['load_cases']:
        for l in lc['loads']:
            target=l.get('element',l.get('node'));prefix=f'{lc["id"]} | {target} | '
            matches=[t for t in full['texts'] if t.startswith(prefix)];need(matches,f'SVG load key missing {prefix}')
            for component in ('wx','wy','wz','fx','fy','fz','mx','my','mz'):
                if component in l:need(any(f'{component}={l[component]:g}' in text for text in matches),f'SVG load key {prefix}{component}')
    if number==53:need('loads.json' not in contract['attachments'],'PNG-only load source bypass')
    else:
        loads=json.loads((casepath/'loads.json').read_text())
        need(loads['load_cases']==model['load_cases'] and loads['load_combinations']==model['load_combinations'],'public load table inconsistent')
    return {'svgFullSourceGeometry':True,'svgDirectedMemberLabels':len(full['segments']),'publicPropertyConsistency':True,'publicNumericalMaterialDimensions':True}

def delayed_check(casepath,contract,number):
    t1,t2=contract['turns'];need(t1['state'] is None and t1['expectation']=='clarify' and t2['state']==1 and t2['expectation']=='analyze','delayed turn semantics')
    need('drawing-elevation-XZ.svg' not in t1['attachments'] and 'drawing-elevation-XZ.png' not in t1['attachments'],'completed delayed drawing exposed early')
    texts={p:(casepath/p).read_text() for p in ['prompt.txt']+[x for x in t1['attachments'] if x.endswith(('.json','.svg','.txt'))]}
    initial=svg_read(casepath/'initial-elevation-XZ.svg');props=json.loads(texts['properties.json']);need('boundaryConditions' not in props,'delayed geometry/support appendix leak')
    from PIL import Image
    for f in t1['attachments']:
        if f.endswith('.png'):
            with Image.open(casepath/f) as im:need(not im.info,f'delayed PNG contains unreviewed metadata: {f} {list(im.info)}')
    need(not re.search(r'<metadata|display="none"|visibility="hidden"|opacity="0"',texts['initial-elevation-XZ.svg']),'hidden SVG metadata channel')
    if number==58:
        need(not initial['supports'],'MM058 support symbols leaked')
        need(sum(t=='[cropped]' for t in initial['texts'])==2,'MM058 two cropped supports')
        for name,t in texts.items():need(not re.search(r'\bFIXED\b|\bfixed\b|LOCK:|restrainedDOFs',t),f'MM058 support leak in {name}')
    else:
        need([v for p,v in initial['zticks']]==[0,3.3,7.3,10.4],'MM072 right absolute elevation labels leaked')
        need(any('NOT TO SCALE' in t for t in initial['texts']),'MM072 schematic gap declaration')
        for name,t in texts.items():
            # Numeric JSON properties can legitimately include 0.5m section sizes;
            # search physical elevation disclosure, not every decimal substring.
            if name.endswith('.svg'):
                labels=svg_read(casepath/name)['texts'] if name.startswith('initial') else [e.text or '' for e in ET.parse(casepath/name).getroot().iter() if e.tag.endswith('text')]
                need(not any(t.strip() in ('0.5','3.8','7.8','10.9') for t in labels),f'MM072 hidden elevations in {name}')
        inferred=initial['nodes']['R2'][2]-initial['nodes']['L2'][2]
        need(abs(inferred-.5)>.05,f'MM072 pixels still reveal real 0.5 gap ({inferred})')
        need('0.5' not in t1['instruction'],'MM072 first instruction leak')
    return {'firstTurnAttachments':t1['attachments'],'secondTurnAttachments':t2['attachments'],'firstTurnPhysicalValueHidden':True,'scope':'cumulative public attachments, prompt and first instruction; SVG labels/geometry; actual PNGs separately visually inspected'}

def dxf_check(casepath,spec,number):
    try:import ezdxf
    except ImportError:
        sys.path.insert(0,str(ROOT/'.bench-work/venv/lib/python3.10/site-packages'));import ezdxf
    doc=ezdxf.readfile(casepath/'input.dxf');entities=list(doc.modelspace());arch=number in (56,59,62,75)
    lines=[e for e in entities if e.dxftype()=='LINE' and e.dxf.layer.startswith('S-')]
    segments=[(str(i),pt(e.dxf.start.x,e.dxf.start.y),pt(e.dxf.end.x,e.dxf.end.y)) for i,e in enumerate(lines)]
    check_graph(spec,segments)
    need(all(near(e.dxf.start.z,0) and near(e.dxf.end.z,0) for e in lines),'DXF 2D plane transform')
    model=json.loads((casepath/'model-state-1.json').read_text());ns={n['id']:n for n in model['nodes']};es={e['id']:e for e in model['elements']}
    tags=[e for e in entities if e.dxftype()=='TEXT' and e.dxf.layer==('S-MEMBER-TAG' if arch else 'ANNOTATION')]
    member_labels=[]
    for line in lines:
        midpoint=tuple((a+b)/2 for a,b in zip(line.dxf.start,line.dxf.end));labelpoint=(midpoint[0],midpoint[1]+(.2 if arch else 0),0)
        labels=[e.dxf.text for e in tags if close(tuple(e.dxf.insert),labelpoint)]
        need(len(labels)==1,'DXF ambiguous member label at midpoint')
        name=labels[0].split()[0];need(name in es,'DXF member label not in assignments')
        e=es[name];member_labels.append(name)
        need(close(pt(line.dxf.start.x,line.dxf.start.y),xyz(ns[e['nodes'][0]])) and close(pt(line.dxf.end.x,line.dxf.end.y),xyz(ns[e['nodes'][1]])),f'DXF directed endpoints {name}')
        need(line.dxf.layer==('S-COLUMN' if e['type']=='column' else 'S-BEAM'),'DXF member classification layer')
    need(set(member_labels)==set(es),'DXF source member labels incomplete')
    node_labels=[e for e in entities if e.dxftype()=='TEXT' and e.dxf.layer==('S-NODE-TAG' if arch else 'NODE')]
    need({e.dxf.text for e in node_labels}==set(ns),'DXF source node labels incomplete')
    for e in node_labels:
        offset=.25 if arch else 0;need(close(pt(e.dxf.insert.x-offset,e.dxf.insert.y-offset),xyz(ns[e.dxf.text])),'DXF node tag association')
    layers=Counter(e.dxf.layer for e in entities);a_lines=[e for e in entities if e.dxftype()=='LINE' and e.dxf.layer.startswith('A-')]
    if arch:need(all(layers[k]>0 for k in ['A-WALL','A-EQUIPMENT','S-COLUMN','S-BEAM','S-NODE-TAG','S-MEMBER-TAG']),'architectural distractor/structure layers missing')
    need(sum(e.dxftype()=='TEXT' and e.dxf.layer in ('SUPPORT','A-SUPPORT') for e in entities)==len(spec.supports),'DXF support symbol count')
    audit=doc.audit()
    return {'parser':'ezdxf '+ezdxf.__version__,'structuralSourceSegmentsChecked':len(lines),'directedMemberLabelsChecked':len(member_labels),'nodeLabelsChecked':len(node_labels),'architectural':arch,'distractorLines':len(a_lines),'entityLayerCounts':dict(layers),'declaredTableLayers':[x.dxf.name for x in doc.layers],'headerInsertionUnits':doc.units,'auditErrors':len(audit.errors),'auditFixes':len(audit.fixes),'note':'Source units m and CAD X/Y -> global X/Z mapping are explicit in public properties. This parses entities, not native CAD import or blinded extraction.'}

def run(case_root):
    srcfiles=[ROOT/'planning/sources/all-tasks-engines-v2.json',ROOT/'planning/sources/all-models-engines-v2.json']
    tasks={r['id']:r for r in json.loads(srcfiles[0].read_text())};models={r['taskId']:r for r in json.loads(srcfiles[1].read_text())}
    messages=[ROOT/'.bench-work/state/root-message.md',ROOT/'.bench-work/state/mm-b-message.md',ROOT/'.bench-work/reports/mm-b.md']
    evidence={'schemaVersion':1,'review':'source-guided MM051-075 independent review','approval':False,'blindReconstruction':False,'generatedAt':datetime.now(timezone.utc).isoformat(),'caseRoot':str(case_root),'reviewScript':{'path':str(Path(__file__).resolve()),'sha256':digest(Path(__file__))},'sources':{str(p):digest(p) for p in srcfiles},'authorMessagesBefore':{str(p):digest(p) for p in messages},'cases':[],'negativeControls':[]}
    specs=source_specs();stored={}
    for number,spec in specs.items():
        cid=f'MM-{number:03d}';p=case_root/cid;c=json.loads((p/'contract.json').read_text());m=json.loads((p/'model-state-1.json').read_text());q=json.loads((p/'reference-requests.json').read_text());stored[number]=(m,q)
        files=list(dict.fromkeys(['contract.json','prompt.txt','model-state-1.json','reference-requests.json']+c['attachments']))
        row={'id':cid,'sourceTask':tasks[cid],'sourceModel':models[cid],'expectedPhysicalSourceSegments':spec.edges,'expectedSourceSupports':[{'at':k,'uxUzRy':v} for k,v in spec.supports.items()],'expectedOutputs':spec.outputs,'filesBefore':{f:digest(p/f) for f in files},'checks':{},'errors':[]}
        for name,fn in [('sourcePhysicalModel',lambda:model_check(spec,m,q)[0]),('publicSVGAndProperties',lambda:public_check(spec,m,c,p,number))]:
            try:row['checks'][name]=fn()
            except Exception as exc:row['errors'].append({'check':name,'error':str(exc)})
        if number in (58,72):
            try:row['checks']['delayedInput']=delayed_check(p,c,number)
            except Exception as exc:row['errors'].append({'check':'delayedInput','error':str(exc)})
        if 'input.dxf' in c['attachments']:
            try:row['checks']['dxf']=dxf_check(p,spec,number)
            except Exception as exc:row['errors'].append({'check':'dxf','error':str(exc)})
        row['filesAfter']={f:digest(p/f) for f in files};row['changedDuringRead']=[f for f in files if row['filesBefore'][f]!=row['filesAfter'][f]]
        row['actualPNGVisualInspection']=[{'path':filename,'sha256':digest(p/filename),'finding':note} for (n,filename),note in VISUAL_REVIEWS.items() if n==number and (p/filename).exists()]
        row['removedFormerVisualInputs']=[{'path':filename,'priorEvidence':'mm051_075-first-evidence.json'} for (n,filename),note in VISUAL_REVIEWS.items() if n==number and not (p/filename).exists()]
        evidence['cases'].append(row)
    for number,label,mutate in [
        (60,'projected rather than actual slope load',lambda m:m['load_cases'][0]['loads'][-1].update(wz=-10*6/math.hypot(6,1.2))),
        (57,'missing third right column',lambda m:m['elements'].pop(8)),
        (74,'right-column roll erased',lambda m:m['elements'][2].update(rotation_angle=0)),
        (68,'stepped base lifted to common datum',lambda m:m['nodes'][0].update(z=0)),
        (56,'hanging free end incorrectly fixed',lambda m:m['nodes'][-1].update(restraints=[True]*6)),
        (65,'point force placed at wrong roof node',lambda m:m['load_cases'][0]['loads'][-1].update(node='n0-3')),
        (53,'horizontal source load mapped to local/vertical axes',lambda m:m['load_cases'][0]['loads'][-1].update(reference_frame='local')),
    ]:
        m,q=stored[number];bad=copy.deepcopy(m);mutate(bad)
        try:model_check(specs[number],bad,q);rejected=False;reason='unexpected pass'
        except AssertionError as exc:rejected=True;reason=str(exc)
        evidence['negativeControls'].append({'caseId':f'MM-{number:03d}','mutation':label,'rejected':rejected,'reason':reason})
    evidence['authorMessagesAfter']={str(p):digest(p) for p in messages}
    evidence['summary']={'cases':len(evidence['cases']),'sourcePhysicalPassed':sum('sourcePhysicalModel' in r['checks'] for r in evidence['cases']),'publicChecksPassed':sum('publicSVGAndProperties' in r['checks'] for r in evidence['cases']),'dxfCases':sum('dxf' in r['checks'] for r in evidence['cases']),'errors':sum(len(r['errors']) for r in evidence['cases']),'changedCaseFiles':sum(len(r['changedDuringRead']) for r in evidence['cases']),'negativeControlsRejected':sum(x['rejected'] for x in evidence['negativeControls'])}
    OUT.write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(evidence['summary']))
    for row in evidence['cases']:
        if row['errors']:print(row['id'],row['errors'])
    return evidence

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--case-root',type=Path,default=ROOT/'.worktrees/mm-b/corpora/research-300/cases');args=ap.parse_args();result=run(args.case_root)
    sys.exit(1 if result['summary']['errors'] or result['summary']['changedCaseFiles'] or not all(c['rejected'] for c in result['negativeControls']) else 0)
