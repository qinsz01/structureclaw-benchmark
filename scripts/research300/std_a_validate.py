"""Structural/input integrity audit for the STD-A authored candidates.

This verifies data and authored source invariants, not native acceptance or truth.
The optional mechanics check uses the shard's independent stdlib matrix audit.
"""
import argparse
from copy import deepcopy
import json
import math
from pathlib import Path
import re

from std_a_core import ROOT, PLAN, length


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def original_source_rows():
    candidates=[ROOT/'planning/sources',ROOT.parents[1]/'planning/sources']
    source=next((p for p in candidates if (p/'all-tasks-engines-v2.json').is_file()),None)
    if source is None:
        raise FileNotFoundError('Original planning/sources JSON tables are required for source review')
    return ({r['id']:r for r in read(source/'all-tasks-engines-v2.json')},
            {r['taskId']:r for r in read(source/'all-models-engines-v2.json')})


TASK_ROWS, MODEL_ROWS = original_source_rows()


def close(a,b):
    return math.isclose(a,b,rel_tol=1e-11,abs_tol=1e-11)


def equal(a,b):
    if isinstance(a,dict):
        assert a.keys()==b.keys(), (a.keys(),b.keys())
        for k in a: equal(a[k],b[k])
    elif isinstance(a,list):
        assert len(a)==len(b)
        for x,y in zip(a,b): equal(x,y)
    elif isinstance(a,(int,float)) and not isinstance(a,bool): assert close(a,b),(a,b)
    else: assert a==b,(a,b)


def audit(number, mechanics=False):
    cid=f'STD-{number:03}'
    folder=ROOT/'corpora/research-300/cases'/cid
    c=read(folder/'contract.json');m=read(folder/'model-state-1.json')
    request=read(folder/'reference-requests.json')['states'][0]
    source=PLAN[cid]
    for k in ('id','modelId','family','language','plannedEngine'): assert c[k]==source[k],(cid,k)
    assert c['sourcePlan']==source['sourceRequirements']
    for field,value in c['sourcePlan'].items():
        category,key=field.split('.',1)
        original=TASK_ROWS[cid] if category=='task' else MODEL_ROWS[cid] if category=='model' else TASK_ROWS[cid]['enginePlan']
        assert value==original[key],(cid,field,'original source mismatch')
    assert c['status']=='authored-candidate' and c['inputBlindReview']=='pending' and c['sameEngineTruthStatus']=='pending' and c['llmEndToEnd']=='not-run'
    assert c['evaluationProfile']=='engineering-v2.3' and c['schemaVersion']==1
    assert len(c['turns'])==1 and c['turns'][0]['expectation']=='analyze' and c['turns'][0]['state']==1
    assert c['turns'][0]['instruction']+'\n'==(folder/'prompt.txt').read_text()
    expected={(r['sourceField'],r['id']) for r in source['requirements']}
    covered=[(r['sourceField'],rid) for r in c['requirementCoverage'] for rid in r['requirementIds']]
    assert len(covered)==len(set(covered)) and set(covered)==expected
    assert all(r['targets'] and r['notes'] for r in c['requirementCoverage'])
    assert set(c['attachments'])==set(c['turns'][0]['attachments'])
    for name in c['attachments']:
        assert (folder/name).is_file() and name not in ('contract.json','model-state-1.json','reference-requests.json','authoring-decisions.json')
        assert not (folder/name).is_symlink() and '..' not in Path(name).parts
    if c['locale']=='en':
        assert not re.search('[\u3400-\u9fff]',c['turns'][0]['instruction']),cid
        for name in c['attachments']:
            assert not re.search('[\u3400-\u9fff]',(folder/name).read_text()),(cid,name)
    assert m['schema_version']=='2.2.0' and m['unit_system']=='SI'
    assert m['coordinate_system']['semantics']=='global-z-up'
    assert m['coordinate_system']['dof_order']==['ux','uy','uz','rx','ry','rz']
    assert all(m['analysis_control'][k] is False for k in ('self_weight','rigid_floor','p_delta','rigid_offsets','construction_stage'))
    ns={n['id']:n for n in m['nodes']};es={e['id']:e for e in m['elements']}
    mats={a['id']:a for a in m['materials']};sects={a['id']:a for a in m['sections']}
    assert len(ns)==len(m['nodes']) and len(es)==len(m['elements'])
    xyz=[tuple(n[k] for k in ('x','y','z')) for n in m['nodes']]
    assert len(xyz)==len(set(xyz)),(cid,'duplicate physical nodes')
    adj={nid:set() for nid in ns}
    for n in ns.values():
        assert len(n['restraints'])==6 and all(type(r) is bool for r in n['restraints'])
        assert all(math.isfinite(n[k]) for k in ('x','y','z'))
        if m['coordinate_system']['dimension']=='2d':assert n['y']==0 and all(n['restraints'][i] for i in (1,3,5))
    for e in es.values():
        a,b=e['nodes'];assert a!=b and a in ns and b in ns
        assert length(m,e['id'])>1e-9
        adj[a].add(b);adj[b].add(a)
        assert e['material'] in mats and e['section'] in sects
        assert sects[e['section']]['properties']['A']>0
        if e['type'] not in ('truss','brace'):
            assert all(sects[e['section']]['properties'][k]>0 for k in ('Iy','Iz','J'))
        if m['coordinate_system']['dimension']=='3d':
            v=m['metadata']['elementReferenceVectors'][e['id']]
            d=[ns[b][k]-ns[a][k] for k in ('x','y','z')]
            cross=[v[1]*d[2]-v[2]*d[1],v[2]*d[0]-v[0]*d[2],v[0]*d[1]-v[1]*d[0]]
            assert sum(x*x for x in cross)>1e-12,(cid,e['id'],'invalid axes')
    seen={next(iter(ns))};todo=list(seen)
    while todo:
        n=todo.pop()
        for a in adj[n]-seen:seen.add(a);todo.append(a)
    assert seen==set(ns),(cid,'disconnected nodes')
    for mat in mats.values():
        assert mat['E']>0 and mat['G']>0 and mat['rho']>0 and -1<mat['nu']<.5
        assert close(mat['G'],mat['E']/(2*(1+mat['nu']))),(cid,'inconsistent isotropic constants')
    caseids={r['id'] for r in m['load_cases']};comboids={r['id'] for r in m['load_combinations']}
    for combo in m['load_combinations']:assert set(combo['factors'])<=caseids
    for case in m['load_cases']:
        assert len({l['id'] for l in case['loads']})==len(case['loads'])
        for load in case['loads']:
            assert load['reference_frame']=='global'
            if load['type']=='nodal':assert load['node'] in ns
            elif load['type']=='distributed':
                assert load['element'] in es and es[load['element']]['type'] not in ('truss','brace')
                assert 0<=load.get('start',0)<load.get('end',length(m,load['element']))<=length(m,load['element'])+1e-9
            else:raise AssertionError((cid,'unaudited load type',load['type']))
    # Public input tables must reconstruct the hidden physical input exactly,
    # including the one intentional mixed-unit case.
    geometry=read(folder/'geometry.json');properties=read(folder/'properties.json');loads=read(folder/'loads.json')
    if geometry['units']=='mm':
        for n in geometry['nodes']:
            for k in ('x','y','z'):n[k]/=1000
        for s in properties['sections']:
            for k in ('A','Iy','Iz','J'):s['properties'][k]/=1e6 if k=='A' else 1e12
        for case in loads['load_cases']:
            for l in case['loads']:
                for k in ('fx','fy','fz'):
                    if k in l:l[k]/=1000
                for k in ('mx','my','mz'):
                    if k in l:l[k]/=1e6
                for k in ('start','end','position'):
                    if k in l:l[k]/=1000
    equal(geometry['nodes'],m['nodes']);equal(geometry['elements'],m['elements'])
    for k in ('materials','sections','analysis_control','load_combinations'):equal(properties[k],m[k])
    equal(loads['load_cases'],m['load_cases']);equal(loads['load_combinations'],m['load_combinations'])
    equal(properties['localAxes'],m.get('metadata',{}))
    qs=request['quantities'];ds=request['derived'];ids={q['id'] for q in qs}|{d['id'] for d in ds}
    assert len(ids)==len(qs)+len(ds)
    assert ids=={qid for out in c['requiredOutputs'] for qid in out['quantityIds']}
    public=read(folder/'output-requests.json')
    equal(public['quantities'],[{k:q[k] for k in ('id','selection','location','component','unit')} for q in qs])
    equal(public['derived'],ds)
    for q in qs:
        assert 'value' not in q and q['tolerance']=={'absolute':1e-8,'relative':1e-6}
        assert q['selection']['kind'] in ('case','combination')
        assert q['selection']['id'] in (caseids if q['selection']['kind']=='case' else comboids)
        loc=q['location'];comp=q['component']
        if loc['kind']=='node':
            assert loc['id'] in ns and comp in ('ux','uy','uz','rx','ry','rz','Fx','Fy','Fz','Mx','My','Mz')
        else:
            assert loc['kind']=='member' and loc['id'] in es and loc['side'] in ('left','right')
            assert 0<=loc['positionM']<=length(m,loc['id'])+1e-9
            assert comp in ('N','V2','V3','T','M2','M3','ux','uy','uz')
        assert q['unit'] in ('m','mm','rad','kN','kN.m')
    for d in ds:
        assert d['operation'] in ('difference','sum','max','min','max_abs')
        assert set(d['operands'])<={q['id'] for q in qs}
    audit_beam_source(number,m,qs)
    result=dict(case=cid,nodes=len(ns),members=len(es),quantities=len(qs),derived=len(ds),sourceFieldsCompared=len(c['sourcePlan']),sourceRequirements=len(covered),structuralInputAudit='pass')
    if all(e['type'] in ('truss','brace') for e in es.values()):
        from std_a_031_040 import rigidity_check
        result['rigidity']=rigidity_check(m)
    if mechanics:
        from std_a_041_050 import check_model
        result['mechanics']=[]
        for kind, name in sorted({(q['selection']['kind'],q['selection']['id']) for q in qs}):
            factors={name:1} if kind=='case' else next(c['factors'] for c in m['load_combinations'] if c['id']==name)
            value, diagnostics=check_model(m,factors,with_values=True)
            for q in qs:
                if q['selection']==dict(kind=kind,id=name):
                    assert math.isfinite(value(q['location'],q['component'])),(cid,q['id'])
            result['mechanics'].append(dict(selection=dict(kind=kind,id=name),**diagnostics))
    return result


def audit_beam_source(number,m,qs):
    """Independently check source resultants and exact named observation requests.

    Expected totals below are integrated directly from the original planning rows,
    not copied from the generated element-load tables.
    """
    resultants={
        1:{'D':(0,-120,360)},2:{'D':(0,-10,30)},3:{'D':(0,-97.5,316.875)},
        4:{'D':(0,-230,1280)},5:{'D':(0,-25,50)},6:{'D':(0,-144,596)},
        7:{'D':(10,-120,480)},8:{'D':(0,-60,270)},9:{'D':(0,-75,375)},
        10:{'D':(0,-64,256),'L':(0,-24,48)},11:{'D':(0,-90,345)},
        12:{'D':(0,-20,60)},13:{'D':(0,-108,486)},14:{'D':(0,-79,420)},
        15:{'D':(0,-132,726)},16:{'D':(0,-140,830)},17:{'D':(0,-195,1267.5)},
        18:{'D':(0,-80,200)},19:{'D':(0,-112,784),'L1':(0,-60,420),'L2':(0,-80,560)},
        20:{'D':(0,-158,1277)},
    }
    observations={1:[3],2:[3],3:[3.25,6.5],4:[4,6],5:[2],6:[4],7:[4],8:[2,4.5,7],9:[2,7],10:[4],11:[3.5,5],12:[3,6],13:[3,4.5,6],14:[4,6],15:[2.5,8],16:[2,7.5],17:[2,6.5,11],18:[2.5,8.5],19:[2,7,12],20:[1.5,5.5,11.5]}
    if number not in resultants:return
    ns={n['id']:n for n in m['nodes']};es={e['id']:e for e in m['elements']}
    for case in m['load_cases']:
        totals=[0.,0.,0.]
        for l in case['loads']:
            if l['type']=='nodal':
                n=ns[l['node']];fx=l.get('fx',0);fz=l.get('fz',0)
                totals[0]+=fx;totals[1]+=fz;totals[2]+=l.get('my',0)+n['z']*fx-n['x']*fz
            else:
                e=es[l['element']];a,b=[ns[n] for n in e['nodes']];L=length(m,e['id']);start=l.get('start',0);end=l.get('end',L)
                t=(start+end)/(2*L);x=a['x']+(b['x']-a['x'])*t;z=a['z']+(b['z']-a['z'])*t
                fx=l.get('wx',0)*(end-start);fz=l.get('wz',0)*(end-start)
                totals[0]+=fx;totals[1]+=fz;totals[2]+=z*fx-x*fz
        assert all(close(a,b) for a,b in zip(totals,resultants[number][case['id']])),(number,case['id'],totals,resultants[number][case['id']])
    selections={(q['selection']['kind'],q['selection']['id']) for q in qs}
    for x in observations[number]:
        node=next(n for n in ns.values() if n['x']==x)
        got={(q['selection']['kind'],q['selection']['id']) for q in qs if q['location']=={'kind':'node','id':node['id']} and q['component']=='uz'}
        assert got==selections,(number,x,'omitted observation/selection')


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--start',type=int,default=1);ap.add_argument('--end',type=int,default=50);ap.add_argument('--mechanics',action='store_true');ap.add_argument('--json-output',type=Path)
    args=ap.parse_args()
    results=[audit(i,args.mechanics) for i in range(args.start,args.end+1)]
    if args.json_output:args.json_output.write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(cases=len(results),quantities=sum(r['quantities'] for r in results),derived=sum(r['derived'] for r in results),sourceRequirements=sum(r['sourceRequirements'] for r in results),structuralInputAudit='pass',mechanics='pass' if args.mechanics else 'not-run-by-this-command',native='pending',inputBlindReview='pending')))
