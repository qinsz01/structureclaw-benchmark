"""Source-number and interaction regressions for spatial/portal INT-A batch."""
import json,math
from int_a_common import ROOT
from int_a_check import check_case

def states(n):
    p=ROOT/f'corpora/research-300/cases/INT-{n:03}';c=json.loads((p/'contract.json').read_text())
    return p,c,[json.loads((p/f).read_text()) for f in c['modelStates']]

def byid(rows,key):return next(r for r in rows if r['id']==key)

def resultant(m):
    ns={n['id']:n for n in m['nodes']};es={e['id']:e for e in m['elements']};out=[0.]*6
    for lc in m['load_cases']:
        for l in lc['loads']:
            if l['type']=='nodal':
                n=ns[l['node']];pos=[n[k] for k in ('x','y','z')];f=[l.get(k,0) for k in ('fx','fy','fz')];moment=[l.get(k,0) for k in ('mx','my','mz')]
            else:
                a,b=(ns[k] for k in es[l['element']]['nodes']);L=math.dist([a[k] for k in ('x','y','z')],[b[k] for k in ('x','y','z')]);pos=[(a[k]+b[k])/2 for k in ('x','y','z')];f=[l.get(k,0)*L for k in ('wx','wy','wz')];moment=[0]*3
            cross=[pos[1]*f[2]-pos[2]*f[1],pos[2]*f[0]-pos[0]*f[2],pos[0]*f[1]-pos[1]*f[0]]
            out=[a+b for a,b in zip(out,f+[a+b for a,b in zip(moment,cross)])]
    return out

def diff(a,b,path=''):
    if type(a)!=type(b):return [path]
    if isinstance(a,dict):return [p for k in a.keys()|b.keys() for p in ([path+'/'+k] if k not in a or k not in b else diff(a[k],b[k],path+'/'+k))]
    if isinstance(a,list):return [p for k in range(max(len(a),len(b))) for p in ([path+'/'+str(k)] if k>=min(len(a),len(b)) else diff(a[k],b[k],path+'/'+str(k)))]
    return [] if a==b else [path]

def main():
    expected={41:[(20,-30,120)],42:[(30,0,180)]*3,43:[(0,-108,972)]*2,44:[(0,-240,4536)],45:[(9,-168,1791)],46:[(4.9,-265,4814.1),(-7,-265,4707)],47:[(0,-138,1158)]*2,48:[(-8,-12*math.sqrt(104),120*math.sqrt(104)-24)],49:[(0,-4*math.sqrt(104)-6*math.sqrt(200),20*math.sqrt(104)+102*math.sqrt(200)),(0,-4*math.sqrt(125)-6*math.sqrt(173),22*math.sqrt(125)+105*math.sqrt(173)),(0,-4*math.sqrt(125)-7*math.sqrt(173),22*math.sqrt(125)+122.5*math.sqrt(173))],50:[(0,-186,3006),(10,-186,3066)]}
    for n,wants in expected.items():
        p,c,ss=states(n);check_case(c['id'])
        for m,w in zip(ss,wants):
            r=resultant(m);assert all(math.isclose(a,b,abs_tol=1e-9) for a,b in zip((r[0],r[2],r[4]),w)),(n,r,w)
        print(c['id'],'source resultants, stability, data and output linkage PASS')
    p,c,ss=states(41);pub=(p/'input-t1.txt').read_text();assert '"fx": 20' not in pub and '"globalAxis": null' in pub
    assert byid(ss[0]['sections'],'A2')['properties']['A']==2*byid(ss[0]['sections'],'A1')['properties']['A']
    p,c,ss=states(42);assert ss[0]==ss[2];changes=diff(ss[0],ss[1]);assert changes and all(x.startswith(('/elements/18/nodes/','/elements/19/nodes/')) for x in changes),changes
    for m in ss:assert len(m['nodes'])==9 and len(m['elements'])==21
    p,c,ss=states(43);assert not byid(ss[0]['nodes'],'A')['restraints'][4] and all(byid(ss[0]['nodes'],'B')['restraints']);assert {byid(ss[1]['nodes'],x)['z'] for x in ['L','R']}=={9}
    p,c,ss=states(44);assert c['turns'][0]['state'] is None and '30 m' in c['turns'][0]['instruction'] and '18 m' in c['turns'][0]['instruction'];assert byid(ss[0]['nodes'],'P')['x']==27
    p,c,ss=states(45);pub=(p/'input-t1.txt').read_text();assert '"wz": -8' not in pub and '"unit": null' in pub and '"fx": 9' in pub
    p,c,ss=states(46);assert diff(ss[0],ss[1])==['/load_cases/0/loads/2/fx'];assert math.isclose(byid(ss[0]['sections'],'C2')['properties']['Iy']/byid(ss[0]['sections'],'C1')['properties']['Iy'],1.7)
    p,c,ss=states(47);changes=diff(ss[0],ss[1]);assert set(changes)<= {'/nodes/2/z','/nodes/3/z','/metadata/elementReferenceVectors/cLa/0','/metadata/elementReferenceVectors/cLb/0'};assert byid(ss[1]['nodes'],'TR')==byid(ss[0]['nodes'],'TR') and byid(ss[1]['nodes'],'SR')==byid(ss[0]['nodes'],'SR')
    p,c,ss=states(48);pub=(p/'input-t1.txt').read_text();assert '"lengthBasis": null' in pub and '"wz": -6' not in pub;assert byid(ss[0]['nodes'],'P')['z']==3
    p,c,ss=states(49);assert byid(ss[1]['nodes'],'K')['x']==11 and byid(ss[2]['nodes'],'K')['x']==11;assert ss[0]['load_cases']==ss[1]['load_cases'];assert diff(ss[1],ss[2])==['/load_cases/0/loads/1/wz']
    p,c,ss=states(50);assert [t['expectation'] for t in c['turns']]==['analyze','clarify','analyze'];assert c['turns'][1]['state'] is None;assert diff(ss[0],ss[1])==['/load_cases/0/loads/2'];assert ss[1]['load_cases'][0]['loads'][-1]['node']=='M6'
    print('Source-specific geometry/section/load, undo, later clarification, hidden-input and exact edit checks PASS')

if __name__=='__main__':main()
