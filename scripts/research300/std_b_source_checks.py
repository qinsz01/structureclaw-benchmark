"""Source-derived physical invariants independent of the case generators.

Checks prescribed load resultants, actual topology, load locations, section/material
roles and essential observations. No response truth or solver defaults are used.
"""
from copy import deepcopy
import json
import math
import sys
from std_b_common import ROOT

# Original source loads integrated over actual physical lengths, Fx/Fy/Fz in kN.
FORCES={
51:{'D':(0,0,-12*math.hypot(9,1.5)),'W':(0,0,8*math.hypot(9,1.5))},
52:{'D':(0,0,-132)},53:{'D':(20,0,-80)},54:{'D':(0,0,-162),'W':(20,0,0)},
55:{'D':(0,0,-720)},56:{'D':(10,0,-962)},57:{'D':(0,0,-360),'W':(45,0,0)},
58:{'D':(50,0,0)},59:{'D':(0,0,-288)},60:{'D':(0,0,-228),'L':(0,0,-182.4)},
61:{'D':(0,0,-228)},62:{'D':(0,0,-180)},63:{'D':(30,0,-120)},64:{'D':(0,0,-135)},
65:{'D':(0,0,-280)},66:{'D':(25,0,-192)},67:{'D':(0,0,-200)},68:{'D':(0,0,-120)},
69:{'D':(0,0,-864)},70:{'D':(0,0,-1080)},71:{'D':(0,0,-240)},72:{'D':(0,0,-360)},
73:{'D':(20,0,-240)},74:{'D':(20,0,-140)},75:{'D':(0,0,-260)},76:{'D':(0,0,-1240)},
77:{'D':(0,0,-360)},78:{'D':(0,0,-180),'W+':(45,0,0),'W-':(-45,0,0)},
79:{'D':(0,0,-600)},80:{'D':(0,0,-960)},81:{'D':(0,0,-1800)},82:{'D':(0,0,-2160)},
83:{'D':(0,0,-1440)},84:{'D':(0,0,-1320)},85:{'D':(0,0,-984)},86:{'D':(0,0,-880)},
87:{'D':(0,0,-1040)},88:{'D':(0,0,-624),'Wx':(30,0,0),'Wy':(0,24,0)},
89:{'D':(20,15,-1056)},90:{'D':(20,15,0)},91:{'D':(0,0,-1056),'L':(0,0,-132)},
92:{'D':(0,0,-5*(24+3*math.hypot(5,2)))},93:{'D':(20,20,-352)},94:{'D':(20,-10,-30)},
95:{'D':(0,0,-500)},96:{'D':(30,0,-600)},97:{'D':(0,0,-900)},98:{'D':(20,15,-400)},
99:{'D':(25,0,-500)},100:{'D':(0,10,-200)},
}
# Original physical grid (observation-node subdivision may increase counts).
BOUNDS={
51:(18,7.5),52:(22,7),53:(16,6),54:(27,7),55:(6,7.2),56:(24,12),57:(12,10.8),
58:(6,4),59:(6,4.5),60:(11.4,7.2),61:(12,7.8),62:(12,6.9),63:(6,7.2),64:(7.5,7.2),
65:(10,9.9),66:(12,7.2),67:(10,7.2),68:(6,5.7),69:(6,7.2),70:(6,9.9),71:(12,7.2),
72:(12,10.4),73:(12,7.2),74:(7,7.2),75:(15,7.2),76:(12,7.2),77:(12,9.9),78:(6,9.9),
79:(6,7.2),80:(12,7.2),81:(6,9.9),82:(12,7.2),83:(12,7.2),84:(12,7.2),85:(11,7.5),
86:(12,7.2),87:(12,7.2),88:(12,7.2),89:(12,7.2),90:(6,7.2),91:(12,7.2),92:(12,8),
93:(6,7.2),94:(10,7),95:(0,4.5),96:(0,4.2),97:(0,5),98:(0,6),99:(0,8),100:(1,5),
}

def close(a,b):return math.isclose(a,b,abs_tol=1e-8,rel_tol=1e-10)
def xyz(n):return tuple(n[k] for k in 'xyz')
def at(m,p):
    return next(n for n in m['nodes'] if all(close(x,y) for x,y in zip(xyz(n),p)))
def endpoints(m,e):
    ns={n['id']:n for n in m['nodes']};return [xyz(ns[k]) for k in e['nodes']]
def nodal(m,case,p,force):
    ns={n['id']:n for n in m['nodes']}
    loads=next(c['loads'] for c in m['load_cases'] if c['id']==case)
    assert any(l['type']=='nodal' and all(close(x,y) for x,y in zip(xyz(ns[l['node']]),p)) and all(close(l.get(k,0),v) for k,v in zip(('fx','fy','fz'),force)) for l in loads),('nodal source load',p,force)
def observation(m,r,p,components):
    n=at(m,p)
    for c in components:
        assert any(q['location']=={'kind':'node','id':n['id']} and q['component']==c for q in r['quantities']),('missing observation',p,c)

def check(number,m,r):
    maxx,maxz=BOUNDS[number]
    assert close(max(n['x'] for n in m['nodes']),maxx) and close(max(n['z'] for n in m['nodes']),maxz), 'source extents'
    actual={}
    for case in m['load_cases']:
        force=[0.,0.,0.]
        for l in case['loads']:
            if l['type']=='nodal':part=[l.get(k,0) for k in ('fx','fy','fz')]
            elif l['type']=='distributed':
                e=next(e for e in m['elements'] if e['id']==l['element']);a,b=endpoints(m,e)
                L=l.get('end',math.dist(a,b))-l.get('start',0)
                part=[l.get(k,0)*L for k in ('wx','wy','wz')]
            else:raise AssertionError('Unexpected load type for STD051–100')
            force=[a+b for a,b in zip(force,part)]
        actual[case['id']]=force
    assert set(actual)==set(FORCES[number]),('case identity',number,actual)
    for sid,expect in FORCES[number].items():assert all(close(a,b) for a,b in zip(actual[sid],expect)),('source load resultant',number,sid,actual[sid],expect)
    columns=[e for e in m['elements'] if e['type']=='column'];beams=[e for e in m['elements'] if e['type']=='beam']
    if number in (53,69):
        n=at(m,(0,0,0));assert n['restraints']==[True,True,True,True,False,True]
    if number in (62,75,87):
        lim={62:6,75:10,87:6}[number]
        assert not any(n['z']>3.6+1e-9 and n['x']>lim+1e-9 for n in m['nodes']),'invented setback bay'
    if number==51:
        assert xyz(at(m,(9,0,7.5)))==(9,0,7.5)
        wind=next(c['loads'] for c in m['load_cases'] if c['id']=='W')
        for l in wind:
            assert l['wz']==8
            assert all(p[0]>=9 for p in endpoints(m,next(e for e in beams if e['id']==l['element'])))
    if number==52:
        for x in (5,11,17):observation(m,r,(x,0,7),('ux','uz'))
        assert len({e['section'] for e in beams})==3
    if number==54:
        assert len({e['section'] for e in columns})==2
        nodal(m,'W',(0,0,7),(10,0,0));nodal(m,'W',(27,0,7),(10,0,0))
    if number==56:
        observation(m,r,(12,0,12),('uz',));nodal(m,'D',(24,0,12),(10,0,-98))
    if number==57:
        for z,f in [(3.6,10),(7.2,15),(10.8,20)]:nodal(m,'W',(12,0,z),(f,0,0))
    if number==59:
        assert any(all(close(p[2],2.25) for p in endpoints(m,e)) for e in beams)
        loaded={l['element'] for c in m['load_cases'] for l in c['loads']}
        assert all(all(close(p[2],4.5) for p in endpoints(m,e)) for e in beams if e['id'] in loaded)
        observation(m,r,(3,0,4.5),('uz',))
    if number==60:assert any(c['factors']=={'D':1.2,'L':1.4} for c in m['load_combinations'])
    if number==63:
        braces=[e for e in m['elements'] if e['type']=='truss']
        assert len(braces)==2 and not any(all(close(a,b) for a,b in zip(xyz(n),(3,0,1.8))) for n in m['nodes'])
        assert {tuple(endpoints(m,e)) for e in braces}=={((0,0,0),(6,0,3.6)),((6,0,0),(0,0,3.6))}
    if number==64:
        for z in (3.6,7.2):observation(m,r,(7.5,0,z),('uz',));assert not any(at(m,(7.5,0,z))['restraints'][i] for i in (0,2,4))
    if number==65:
        for z in (3.3,6.6,9.9):
            for x in (2.5,7.5):observation(m,r,(x,0,z),('uz',))
    if number==66:assert len({e['section'] for e in m['elements']})==4
    if number==67:
        assert not any(all(close(p[0],5) for p in endpoints(m,e)) and max(p[2] for p in endpoints(m,e))>3.6+1e-9 for e in columns)
        observation(m,r,(5,0,7.2),('uz',));assert not any(at(m,(5,0,7.2))['restraints'][i] for i in (0,2,4))
    if number==68:
        assert min(n['z'] for n in m['nodes'])==-1.5
        for x in (0,6):assert not any(at(m,(x,0,0))['restraints'][i] for i in (0,2,4))
    if number==70:assert m['materials'][0]['name']=='C35' and m['materials'][0]['E']==31500
    if number==71:assert len(m['materials'])==1 and m['materials'][0]['name']=='C30'
    if number==73:
        mats={p['id']:p['name'] for p in m['materials']}
        assert all(mats[e['material']]==('C40' if e['type']=='column' else 'C30') for e in m['elements'])
    if number==74:assert all(e.get('rotation_angle',0)==(90 if endpoints(m,e)[0][0]==7 else 0) for e in columns)
    if number==75:
        for p in [(15,0,3.6),(10,0,3.6),(10,0,7.2)]:observation(m,r,p,('ux','uz','ry'))
    if number==76:
        for z in (3.6,7.2):
            for x in (2.5,8.5):observation(m,r,(x,0,z),('uz',))
    if number==77:
        sec={p['id']:p for p in m['sections']}
        for e in columns:
            expected=.36 if min(p[2] for p in endpoints(m,e))<1e-9 else .25
            assert close(sec[e['section']]['properties']['A'],expected)
    if number==78:
        for case,sgn in [('W+',1),('W-',-1)]:
            for z,f in [(3.3,10),(6.6,15),(9.9,20)]:nodal(m,case,(6,0,z),(sgn*f,0,0))
    if 79<=number<=84:
        for l in m['load_cases'][0]['loads']:
            a,b=endpoints(m,next(e for e in beams if e['id']==l['element']))
            assert close(a[1],b[1]) and not close(a[0],b[0]),'duplicate Y beam area load'
    if number==83:
        mats={p['id']:p['name'] for p in m['materials']}
        for e in m['elements']:assert mats[e['material']]==('C40' if e['type']=='column' and min(p[2] for p in endpoints(m,e))<1e-9 else 'C30')
    if number==86:
        assert not any(close(n['x'],12) and close(n['y'],10) for n in m['nodes'])
        for z in (3.6,7.2):observation(m,r,(6,5,z),('ux','uy','uz'))
    if number==88:
        for z,fx,fy in [(3.6,10,8),(7.2,20,16)]:
            nodal(m,'Wx',(12,5,z),(fx,0,0));nodal(m,'Wy',(12,5,z),(0,fy,0))
        assert len(m['load_combinations'])==3 and any(d['operation']=='max_abs' for d in r['derived'])
    if number==89:assert len({e['section'] for e in columns})==3 and len({e['section'] for e in beams})==2
    if number==90:assert all(e.get('rotation_angle',0)==(90 if close(endpoints(m,e)[0][1],0) else 0) for e in columns)
    if number==91:
        live=next(c for c in m['load_cases'] if c['id']=='L')['loads'];assert len(live)==4
        for l in live:
            a,b=endpoints(m,next(e for e in beams if e['id']==l['element']))
            assert all(close(p[2],7.2) and p[0]<=6 and p[1]<=5 for p in (a,b)) and l['wz']==-6
    if number==92:
        for x in (0,6,12):observation(m,r,(x,2.5,7),('ux','uy','uz'))
    if number==93:
        braces=[e for e in m['elements'] if e['type']=='truss'];assert len(braces)==2
        assert {tuple(endpoints(m,e)) for e in braces}=={((0,0,0),(6,0,3.6)),((0,0,3.6),(6,0,7.2))}
    if number==94:nodal(m,'D',(10,-5,7),(20,-10,-30))
    if number in (95,96):
        sec=next(s for s in m['sections'] if s['id']==m['elements'][0]['section'])
        assert close(sec['properties']['A'],(.4 if number==95 else .45)**2)
    if number==97:
        nodal(m,'D',(0,0,2.5),(0,0,-200));nodal(m,'D',(0,0,5),(0,0,-700))
        observation(m,r,(0,0,2.5),('uz',));assert len(columns)==2
    if number==98:
        p=next(s['properties'] for s in m['sections'] if s['id']==m['elements'][0]['section']);assert not close(p['Iy'],p['Iz'])
        observation(m,r,(0,0,6),('ux','uy','uz','rx','ry','rz'))
    if number==99:
        observation(m,r,(0,0,3),('ux','uz','ry'));assert len({e['section'] for e in columns})==2
        assert not any(at(m,(0,0,3))['restraints'][i] for i in (0,2,4))
    if number==100:
        assert len(beams)==1 and endpoints(m,beams[0])==[(0,0,5),(1,0,5)]
        nodal(m,'D',(1,0,5),(0,10,-200));observation(m,r,(1,0,5),('ux','uy','uz','rx','ry','rz'))

def run(numbers):
    for i in numbers:
        path=ROOT/'corpora/research-300/cases'/f'STD-{i:03d}'
        m=json.loads((path/'model-state-1.json').read_text());r=json.loads((path/'reference-requests.json').read_text())['states'][0]
        check(i,m,r);print(f'STD-{i:03d}: source physical invariants PASS',flush=True)

if __name__=='__main__':run([int(x) for x in sys.argv[1:]] or range(51,101))
