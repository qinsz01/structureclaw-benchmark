"""Structural/source-contract checks; does not generate reference truth or native receipts."""
import argparse
import importlib.util
import json
import math
import re
from collections import defaultdict
from int_b_common import ROOT, PLAN, TASKS


def check_model(m):
    assert m['schema_version']=='2.2.0'
    ns={n['id']:n for n in m['nodes']};es={e['id']:e for e in m['elements']}
    mats={v['id']:v for v in m['materials']};secs={v['id']:v for v in m['sections']}
    assert len(ns)==len(m['nodes']) and len(es)==len(m['elements'])
    xyz={n:tuple(ns[n][k] for k in ('x','y','z')) for n in ns}
    assert len(set(xyz.values()))==len(xyz), 'duplicate coordinates'
    graph=defaultdict(set)
    for n in ns.values():
        assert len(n['restraints'])==6 and all(type(v) is bool for v in n['restraints'])
        assert all(isinstance(n[k],(int,float)) and math.isfinite(n[k]) for k in ('x','y','z'))
    for mat in mats.values():
        assert mat['E']>0 and mat['G']>0 and -1<mat['nu']<.5
        assert math.isclose(mat['G'],mat['E']/(2*(1+mat['nu'])),rel_tol=1e-8)
    for s in secs.values():
        assert all(s['properties'][p]>0 for p in ('A','Iy','Iz','J'))
    lengths={}
    for e in es.values():
        a,b=e['nodes'];assert a in ns and b in ns and a!=b
        assert e['material'] in mats and e['section'] in secs
        assert e['type'] in ('beam','column','truss','brace')
        v=[xyz[b][j]-xyz[a][j] for j in range(3)]
        length=math.sqrt(sum(x*x for x in v));assert length>1e-9
        lengths[e['id']]=length;graph[a].add(b);graph[b].add(a)
        if m['coordinate_system']['dimension']=='3d':
            r=m['metadata']['elementReferenceVectors'][e['id']]
            cross=[r[1]*v[2]-r[2]*v[1],r[2]*v[0]-r[0]*v[2],r[0]*v[1]-r[1]*v[0]]
            assert sum(x*x for x in cross)>1e-12, 'parallel reference vector'
    seen=set();todo=[next(iter(ns))]
    while todo:
        n=todo.pop()
        if n in seen:continue
        seen.add(n);todo.extend(graph[n]-seen)
    assert seen==set(ns), 'disconnected nodes'
    cases={c['id']:c for c in m['load_cases']};assert len(cases)==len(m['load_cases'])
    for c in cases.values():
        assert len({l['id'] for l in c['loads']})==len(c['loads'])
        for l in c['loads']:
            assert l['reference_frame']=='global'
            if l['type']=='nodal':assert l['node'] in ns
            else:
                assert l['element'] in es and es[l['element']]['type'] not in ('truss','brace')
                length=lengths[l['element']]
                if l['type']=='point':assert 0<=l['position']<=length+1e-9
                elif l['type']=='distributed':assert 0<=l.get('start',0)<l.get('end',length)<=length+1e-9
                else:raise AssertionError(l['type'])
    for c in m['load_combinations']:
        assert set(c['factors'])<=set(cases)
    assert not any(m['analysis_control'].get(k) for k in ('self_weight','p_delta','rigid_floor','rigid_offsets','construction_stage'))


def run(ids,stiffness=False):
    oracle=None
    if stiffness:
        spec=importlib.util.spec_from_file_location('int_b_stability',ROOT/'scripts/independent-frame-reference.py')
        oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)
    count=0;statecount=0;selectioncount=0
    for number in ids:
        cid=f'INT-{number:03}';folder=ROOT/'corpora/research-300/cases'/cid
        c=json.loads((folder/'contract.json').read_text());row=PLAN[cid]
        assert c['sourcePlan']==row['sourceRequirements'],cid
        assert c['family']==row['family'] and c['language']==row['language'] and c['plannedEngine']==row['plannedEngine']
        assert len(c['turns'])==TASKS[cid]['turns']
        assert c['status']=='authored-candidate' and c['sameEngineTruthStatus']=='pending' and c['inputBlindReview']=='pending' and c['llmEndToEnd']=='not-run'
        covered=[v for x in c['requirementCoverage'] for v in x['requirementIds']]
        assert sorted(covered)==sorted(r['id'] for r in row['requirements'])
        assert (folder/'prompt.txt').read_text().strip()==c['turns'][0]['instruction'].strip()
        public=set(c['attachments']);models=[json.loads((folder/f).read_text()) for f in c['modelStates']]
        assert not public.intersection(c['modelStates']+['reference-requests.json','author-notes.json'])
        released=set()
        for i,t in enumerate(c['turns'],1):
            assert t['id']==f't{i}' and set(t['attachments'])<=public
            assert not released.intersection(t['attachments']), 'attachment is not newly visible'
            released.update(t['attachments'])
            if t['expectation']=='clarify':assert t['state'] is None and t['unresolvedFields'] and t['expectedQuestions']
            else:assert 1<=t['state']<=len(models) and not t['unresolvedFields']
            assert not re.search(r'model-state-|reference-requests|author-notes',t['instruction'])
        assert released==public
        for out in c['requiredOutputs']:
            bound=[t for t in c['turns'] if out['id'] in t.get('requiredOutputIds',[])]
            assert bound and all(t['state']==out['state'] for t in bound)
            assert all(set(out['quantityIds'])<=set(t['requiredQuantityIds']) for t in bound)
        for name in public:
            if name.endswith('.json'):
                p=json.loads((folder/name).read_text())
                assert not ('nodes' in p and 'elements' in p), 'canonical hidden-state presentation in public input'
        if c['locale']=='en':
            for text in [t['instruction'] for t in c['turns']]+[(folder/f).read_text() for f in public]:
                assert not re.search('[\u4e00-\u9fff]',text),cid+' Chinese public text'
        refs=json.loads((folder/'reference-requests.json').read_text())['states']
        assert len(refs)==len(models)
        for i,(m,r) in enumerate(zip(models,refs),1):
            check_model(m);statecount+=1
            assert r['state']==i and r['model']==c['modelStates'][i-1]
            qs=r['quantities'];assert qs and len({q['id'] for q in qs})==len(qs)
            nodeids={n['id'] for n in m['nodes']};elementids={e['id'] for e in m['elements']}
            sels={(s['kind'],s['id']) for s in [q['selection'] for q in qs]}
            valid={('case',x['id']) for x in m['load_cases']}|{('combination',x['id']) for x in m['load_combinations']}
            assert sels==valid, (cid,i,'missing selections',sels,valid)
            for q in qs:
                assert 'value' not in q and 'tolerance' in q
                assert q['location']['id'] in (nodeids if q['location']['kind']=='node' else elementids)
                assert q['component'] in ('ux','uy','uz','rx','ry','rz','Fx','Fy','Fz','Mx','My','Mz','N','V2','V3','T','M2','M3')
                assert any(o['state']==i and q['id'] in o['quantityIds'] for o in c['requiredOutputs'])
            if oracle:
                for kind,sel in sorted(sels):
                    factors={sel:1} if kind=='case' else next(x['factors'] for x in m['load_combinations'] if x['id']==sel)
                    _,checks=oracle.solve(m,factors,[])
                    assert max(abs(x) for x in checks['forceMomentBalance'])<1e-5,(cid,i,sel,checks)
                    selectioncount+=1
            for d in r.get('derived',[]):assert set(d['operands'])<={q['id'] for q in qs}
        count+=1
    print(json.dumps(dict(cases=count,states=statecount,stiffnessSelections=selectioncount,result='passed',scope='Author structural/contract checks and optional independent stiffness/equilibrium smoke checks; no native or blind-review acceptance.')))


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--start',type=int,default=51);ap.add_argument('--end',type=int,default=100);ap.add_argument('--stiffness',action='store_true');args=ap.parse_args()
    run(range(args.start,args.end+1),args.stiffness)
