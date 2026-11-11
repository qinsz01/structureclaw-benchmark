"""Source-derived resultant, location, edit and withholding checks for INT-B.

Force/moment totals below were calculated from source dimensions and load
statements, independently of the builders. They catch misplaced loads even when
a generated model is internally valid and its solver balances its own loads.
"""
from copy import deepcopy
import json
import math
from int_b_common import ROOT, PLAN, TASKS, MODELS, diff_paths


def read(i,f):return json.loads((ROOT/f'corpora/research-300/cases/INT-{i:03}'/f).read_text())
def state(i,s=1):return read(i,f'model-state-{s}.json')
def loads(m,case='D'):return next(c['loads'] for c in m['load_cases'] if c['id']==case)
def nd(m,id):return next(n for n in m['nodes'] if n['id']==id)
def ed(m,id):return next(e for e in m['elements'] if e['id']==id)
def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]


def resultant(m,case):
    nodes={n['id']:[n[k] for k in ('x','y','z')] for n in m['nodes']}
    es={e['id']:e for e in m['elements']};out=[0.]*6
    for l in loads(m,case):
        if l['type']=='nodal':
            pos=nodes[l['node']];force=[l.get(k,0) for k in ('fx','fy','fz')];moment=[l.get(k,0) for k in ('mx','my','mz')]
        else:
            a,b=[nodes[n] for n in es[l['element']]['nodes']];length=math.dist(a,b)
            if l['type']=='distributed':
                start,end=l.get('start',0),l.get('end',length);station=(start+end)/2
                force=[l.get(k,0)*(end-start) for k in ('wx','wy','wz')];moment=[0,0,0]
            else:
                station=l['position'];force=[l.get(k,0) for k in ('fx','fy','fz')];moment=[l.get(k,0) for k in ('mx','my','mz')]
            pos=[a[j]+(b[j]-a[j])*station/length for j in range(3)]
        r=cross(pos,force)
        for j in range(3):out[j]+=force[j];out[j+3]+=r[j]+moment[j]
    return out


def check():
    slope=math.hypot(9,1.5)
    # (case ID, state, load case): [global Fx,Fy,Fz,Mx,My,Mz about origin].
    expected={
        (51,1,'D'):[0,0,-10*slope-12,0,90*slope+108,0],
        (51,1,'W'):[0,0,4*slope,0,-54*slope,0],
        (52,1,'D'):[0,0,-154,0,1694,0],(52,2,'D'):[0,0,-154,0,1694,0],
        (53,1,'D'):[12,0,-100,0,872,0],
        (54,1,'D'):[0,0,-158,0,2163,0],(54,1,'W'):[18,0,0,0,126,0],
        (54,2,'D'):[0,0,-158,0,2163,0],(54,2,'W'):[14,0,-3,0,179,0],
        (54,3,'D'):[0,0,-158,0,2163,0],(54,3,'W'):[14,0,-3,0,179,0],
        (55,1,'D'):[0,0,-720,0,2160,0],(55,2,'W'):[25,0,0,0,144,0],
        (56,1,'D'):[24,0,-962,0,12924,0],(56,2,'D'):[24,0,-981.6,0,13394.4,0],
        (57,1,'D'):[45,0,-180,0,1980,0],
        (58,1,'D'):[50,0,-36,0,308,0],(58,2,'D'):[80,0,-36,0,428,0],
        (59,1,'D'):[0,0,-288,0,864,0],
        (60,1,'D'):[0,0,-228,0,1299.6,0],(60,1,'L'):[0,0,-182.4,0,1039.68,0],(60,2,'W'):[25,0,0,0,144,0],
        (61,1,'D'):[0,0,-240,0,1440,0],(62,1,'D'):[0,0,-198,0,1062,0],
        (63,1,'D'):[18,0,-120,0,489.6,0],
        (64,1,'D'):[0,0,-160,0,547.5,0],(64,2,'D'):[0,0,-163,0,570.75,0],
        (65,1,'D'):[0,0,-280,0,1400,0],(65,2,'D'):[0,0,-300,0,1500,0],
        (66,1,'D'):[18,0,-240,0,1571.4,0],(66,2,'D'):[18,0,-240,0,1571.4,0],
        (67,1,'D'):[0,0,-154,0,770,0],(68,1,'D'):[6,0,-120,0,361.8,0],
        (99,1,'D'):[25,0,-500,0,218,0],(99,2,'D'):[25,0,-500,0,218,0],
        (100,1,'D'):[16,10,-200,-50,240,10],(100,2,'D'):[16,10,-200,-250,40,0],(100,3,'D'):[16,10,-200,-50,240,10],
    }
    for key,target in expected.items():
        actual=resultant(state(*key[:2]),key[2]);assert all(math.isclose(x,y,rel_tol=1e-10,abs_tol=1e-8) for x,y in zip(actual,target)),(key,actual,target)
    # Source distinctions and non-target preservation: independently specified IDs.
    assert not nd(state(52),'leftBase')['restraints'][4]
    assert nd(state(52),'rightBase')['restraints']==[True]*6
    assert ed(state(52,2),'roofMiddle')['section']=='B4'
    assert len(diff_paths(state(52),state(52,2)))==1
    assert loads(state(54),'D')==loads(state(54,3),'D')
    assert len(diff_paths(state(54,2),state(54,3)))==1
    for i,old,new,factor in [(55,'B1','B2',.7),(59,'C1','C2',1.3),(60,'C1','C2',1.8),(65,'B1','B2',.6)]:
        ss={s['id']:s['properties'] for s in state(i)['sections']}
        assert ss[old]['A']==ss[new]['A']
        for axis in ('Iy','Iz'):assert math.isclose(ss[new][axis],factor*ss[old][axis])
    assert len(diff_paths(state(56),state(56,2)))==1
    assert len(diff_paths(state(58),state(58,2)))==1
    assert state(60)['load_combinations'][0]==state(60,2)['load_combinations'][0]
    assert not any(n['id']=='n2-2' for n in state(62)['nodes'])
    assert {e['id'] for e in state(63)['elements'] if e['type']=='truss'}=={'diagonalA','diagonalB'}
    assert diff_paths(state(64),state(64,2))==['/nodes/8/x']
    assert ed(state(66),'c1-1')['nodes'][1]=='columnMid'
    assert nd(state(66),'columnMid')['z']==1.8
    assert not any(e['id']=='c1-2' for e in state(67)['elements'])
    assert sum('n1-2' in e['nodes'] for e in state(67)['elements'])==2
    assert min(n['z'] for n in state(68)['nodes'])==-1.5
    assert nd(state(68),'leftMid')['z']==.3
    assert nd(state(99,2),'interface')['z']==4 and nd(state(99,2),'top')['z']==8
    assert state(100)==state(100,3) and loads(state(100))==loads(state(100,2))
    # Initial ambiguity must remain unresolved in every attachment released at t1.
    p=read(57,'input-t1.json');ls={l['id']:l for l in p['loadCaseTable'][0]['loads']}
    assert [ls[f'lateral-{j}']['fx'] for j in (1,2,3)]==[20,15,10]
    p=read(59,'input-t1.json');assert not p['loadCaseTable'][0]['loads'] and p['unresolvedRoofLoading']['relationship'] is None
    p=read(61,'input-t1.json');assert all(n['z'] is None for n in p['nodeTable'] if n['id'].endswith('-2'))
    p=read(63,'input-t1.json');assert all(e['type'] is None for e in p['memberTable'] if e['id'].startswith('diagonal'))
    # Every source row and per-case source snapshot must survive generation exactly.
    for i in range(51,101):
        cid=f'INT-{i:03}';c=read(i,'contract.json');a=read(i,'author-notes.json')
        assert c['sourcePlan']==PLAN[cid]['sourceRequirements']
        assert a['sourceTask']==TASKS[cid] and a['sourceModel']==MODELS[cid]
        assert len(c['turns'])==TASKS[cid]['turns']
    print(json.dumps({'sourceRowsRetained':50,'independentForceMomentTotals':len(expected),'result':'passed','review':'Author source checks only; independent blind/native gates pending.'}))


if __name__=='__main__':check()
