"""Author structural audit; verifies inputs and numerical solvability, never writes truth.

Usage: python3 scripts/research300/std_b_check.py [case numbers ...]
The matrix solve is a diagnostic only; it cannot provide native acceptance.
"""
import importlib.util
import json
import math
from pathlib import Path
import sys
import numpy as np
from std_b_common import ROOT, source

spec=importlib.util.spec_from_file_location('readonly_independent_matrix',ROOT/'scripts/independent-frame-reference.py')
matrix=importlib.util.module_from_spec(spec);spec.loader.exec_module(matrix)

def validate(number, solve=True):
    case=ROOT/'corpora/research-300/cases'/f'STD-{number:03d}'
    c=json.loads((case/'contract.json').read_text());m=json.loads((case/'model-state-1.json').read_text())
    r=json.loads((case/'reference-requests.json').read_text())['states'][0]
    row,task,src=source(number)
    assert c['sourcePlan']==row['sourceRequirements'], 'source requirement drift'
    for field in ('id','modelId','family','language','plannedEngine'):assert c[field]==row[field],field
    assert c['status']=='authored-candidate' and c['sameEngineTruthStatus']=='pending' and c['inputBlindReview']=='pending' and c['llmEndToEnd']=='not-run'
    assert len(c['turns'])==task['turns']==1
    assert c['turns'][0]['instruction'].strip()==(case/'prompt.txt').read_text().strip()
    public=json.loads((case/'input-data.json').read_text())
    assert [[n['id'],n['x'],n['y'],n['z'],*n['restraints']] for n in m['nodes']]==public['nodeTable']['rows'],'public node/support mismatch'
    for el,rowdata in zip(m['elements'],public['memberTable']['rows']):
        assert rowdata[:6]==[el['id'],el['type'],*el['nodes'],el['material'],el['section']]
        assert rowdata[6]==el.get('rotation_angle',0)
        assert rowdata[7]==m['metadata']['elementReferenceVectors'].get(el['id'])
    assert len(public['memberTable']['rows'])==len(m['elements'])
    for hidden_key,public_key in [('materials','materials'),('sections','sections'),('coordinate_system','coordinateConvention'),('load_cases','loadingCases'),('load_combinations','linearCombinations'),('analysis_control','analysisSettings')]:
        assert m[hidden_key]==public[public_key],('public-hidden input mismatch',hidden_key)
    public_requests=json.loads((case/'output-requests.json').read_text())
    assert all('tolerance' not in q and 'value' not in q for q in public_requests['quantities'])
    assert public_requests['quantities']==[{k:v for k,v in q.items() if k!='tolerance'} for q in r['quantities']]
    mapped=[i for cov in c['requirementCoverage'] for i in cov['requirementIds']]
    assert sorted(mapped)==sorted(q['id'] for q in row['requirements']), 'requirements omitted/duplicated'
    for f in c['attachments']:
        assert (case/f).is_file() and f not in c['modelStates'] and f not in ('contract.json','reference-requests.json','author-review.json')
        if c['locale']=='en':
            assert not any('\u4e00'<=s<='\u9fff' for s in (case/f).read_text()),f'non-English public attachment {f}'
    if c['locale']=='en':assert not any('\u4e00'<=s<='\u9fff' for s in (case/'prompt.txt').read_text()),'non-English prompt'
    n={n['id']:n for n in m['nodes']};e={e['id']:e for e in m['elements']}
    assert len(n)==len(m['nodes']) and len(e)==len(m['elements'])
    coords=[tuple(v[a] for a in 'xyz') for v in n.values()]
    assert len(coords)==len(set(coords)),'duplicate-coordinate disconnected nodes'
    adjacency={k:set() for k in n}
    sections={s['id']:s for s in m['sections']};materials={x['id']:x for x in m['materials']}
    for x in materials.values():
        assert x['E']>0 and x['G']>0 and x['rho']>0 and -1<x['nu']<.5
        assert math.isclose(x['G'],x['E']/(2*(1+x['nu'])),rel_tol=1e-8)
    for x in sections.values():assert all(x['properties'][a]>0 for a in ('A','Iy','Iz','J'))
    for el in e.values():
        a,b=el['nodes'];assert a in n and b in n and a!=b
        adjacency[a].add(b);adjacency[b].add(a)
        assert el['section'] in sections and el['material'] in materials
        assert math.dist([n[a][k] for k in 'xyz'],[n[b][k] for k in 'xyz'])>1e-8
        if el['type']!='truss':
            A=np.array([n[a][k] for k in 'xyz']);B=np.array([n[b][k] for k in 'xyz']);R=matrix.axes(m,el,A,B)
            assert np.isfinite(R).all() and np.allclose(R@R.T,np.eye(3),atol=1e-10),'invalid local axes'
    assert all(adjacency.values()),'isolated observation node'
    seen=set();queue=[next(iter(n))]
    while queue:
        p=queue.pop()
        if p in seen:continue
        seen.add(p);queue.extend(adjacency[p]-seen)
    assert seen==set(n),'disconnected topology'
    assert all(not m['analysis_control'][k] for k in ('self_weight','rigid_floor','p_delta','rigid_offsets','construction_stage'))
    cs={x['id']:x for x in m['load_cases']};comb={x['id']:x for x in m['load_combinations']}
    for lc in cs.values():
        for l in lc['loads']:
            assert l['reference_frame']=='global'
            if l['type']=='nodal':assert l['node'] in n
            else:
                assert l['element'] in e and e[l['element']]['type']!='truss'
                el=e[l['element']];a,b=[n[k] for k in el['nodes']];L=math.dist([a[k] for k in 'xyz'],[b[k] for k in 'xyz'])
                if l['type']=='point':assert 0<=l['position']<=L
                else:assert 0<=l.get('start',0)<l.get('end',L)<=L+1e-9
    for x in comb.values():assert set(x['factors'])<=set(cs)
    qids=set();selections={}
    for q in r['quantities']:
        assert 'value' not in q and q['id'] not in qids
        qids.add(q['id']);loc=q['location'];sel=q['selection'];selections[sel['kind'],sel['id']]=sel
        assert sel['id'] in (cs if sel['kind']=='case' else comb)
        if loc['kind']=='node':assert loc['id'] in n
        else:
            assert loc['id'] in e
            el=e[loc['id']];a,b=[n[k] for k in el['nodes']];L=math.dist([a[k] for k in 'xyz'],[b[k] for k in 'xyz'])
            assert 0<=loc['positionM']<=L+1e-8 and loc['side'] in ('left','right')
    for d in r['derived']:
        assert d['operation'] in ('difference','max','min','max_abs') and d['id'] not in qids
        assert d['operands'] and all(k in qids for k in d['operands']),'unresolved/cyclic derived operand'
        if d['operation']=='difference':assert len(d['operands'])==2
        qids.add(d['id'])
    outids={q for o in c['requiredOutputs'] for q in o['quantityIds']}
    assert outids==qids,'unscored or missing quantity'
    checks=[]
    if solve:
        stations=[q['location'] for q in r['quantities'] if q['location']['kind']=='member']
        for (kind,sid),sel in selections.items():
            factors={sid:1} if kind=='case' else comb[sid]['factors']
            _,audit=matrix.solve(m,factors,stations)
            assert max(abs(x) for x in audit['forceMomentBalance'])<1e-6,'global force/moment imbalance'
            checks.append(dict(selection=sel,freeResidual=audit['freeResidual'],maxForceMomentResidual=max(abs(x) for x in audit['forceMomentBalance'])))
    return dict(id=c['id'],nodes=len(n),elements=len(e),quantities=len(r['quantities']),derived=len(r['derived']),matrixDiagnostic=checks,nativeAcceptance='pending')

if __name__=='__main__':
    numbers=[int(x) for x in sys.argv[1:]] or list(range(51,101))
    for i in numbers:
        print(json.dumps(validate(i),ensure_ascii=False),flush=True)
