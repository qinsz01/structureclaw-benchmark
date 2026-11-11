"""Independent structural/data audit of authored INT-A inputs, not numerical truth."""
from pathlib import Path
import json,math,sys,hashlib
from int_a_common import ROOT,sources

def rank(a,tol=1e-9):
    a=[r[:] for r in a];r=0;n=len(a)
    for c in range(n):
        p=max(range(r,n),key=lambda k:abs(a[k][c]),default=r)
        if p>=n or abs(a[p][c])<tol:continue
        a[r],a[p]=a[p],a[r];v=a[r][c]
        for j in range(c,n):a[r][j]/=v
        for i in range(r+1,n):
            v=a[i][c]
            if abs(v)>tol:
                for j in range(c,n):a[i][j]-=v*a[r][j]
        r+=1
        if r==n:break
    return r

def stiffness_rank(m):
    nodes=m['nodes'];ns={n['id']:n for n in nodes};idx={n['id']:i for i,n in enumerate(nodes)}
    truss=all(e['type']=='truss' for e in m['elements'])
    if not truss and m['coordinate_system']['dimension']!='2d':return None
    dofs=(0,1,2) if truss else (0,2,4);nd=3*len(nodes);K=[[0.0]*nd for _ in range(nd)]
    mats={x['id']:x for x in m['materials']};secs={x['id']:x['properties'] for x in m['sections']}
    for e in m['elements']:
        a,b=(ns[i] for i in e['nodes']);d=[b[k]-a[k] for k in ('x','y','z')];L=math.sqrt(sum(v*v for v in d));E=mats[e['material']]['E']*1000;sec=secs[e['section']];A=sec['A']
        ii=[3*idx[a['id']]+k for k in range(3)]+[3*idx[b['id']]+k for k in range(3)]
        if truss:
            v=[x/L for x in d];t=[-x for x in v]+v;kg=[[E*A/L*x*y for y in t] for x in t]
        else:
            c,s=d[0]/L,d[2]/L;ea=E*A/L;ei=E*sec['Iy'];b12=12*ei/L**3;b6=6*ei/L**2;b4=4*ei/L;b2=2*ei/L
            kl=[[ea,0,0,-ea,0,0],[0,b12,b6,0,-b12,b6],[0,b6,b4,0,-b6,b2],[-ea,0,0,ea,0,0],[0,-b12,-b6,0,b12,-b6],[0,b6,b2,0,-b6,b4]]
            T=[[c,s,0,0,0,0],[-s,c,0,0,0,0],[0,0,-1,0,0,0],[0,0,0,c,s,0],[0,0,0,-s,c,0],[0,0,0,0,0,-1]]
            kg=[[sum(T[k][i]*kl[k][l]*T[l][j] for k in range(6) for l in range(6)) for j in range(6)] for i in range(6)]
        for i in range(6):
            for j in range(6):K[ii[i]][ii[j]]+=kg[i][j]
    free=[3*i+k for i,n in enumerate(nodes) for k,d in enumerate(dofs) if not n['restraints'][d]]
    scales=[math.sqrt(max(K[i][i],1e-30)) for i in free]
    kf=[[K[i][j]/(scales[a]*scales[b]) for b,j in enumerate(free)] for a,i in enumerate(free)]
    return rank(kf),len(free)

def check_model(m):
    ns={n['id']:n for n in m['nodes']};es={e['id']:e for e in m['elements']};mats={x['id']:x for x in m['materials']};secs={x['id']:x for x in m['sections']}
    assert len(ns)==len(m['nodes']) and len(es)==len(m['elements']),'duplicate IDs'
    coords=[(n['x'],n['y'],n['z']) for n in ns.values()];assert len(coords)==len(set(coords)),'disconnected duplicate coordinate node'
    used=set();adj={i:set() for i in ns}
    for n in ns.values():
        assert len(n['restraints'])==6 and all(type(r) is bool for r in n['restraints'])
        if all(e['type']=='truss' for e in es.values()):assert all(n['restraints'][3:]),'unrestrained inactive truss rotation'
        if m['coordinate_system']['dimension']=='2d':assert all(n['restraints'][i] for i in (1,3,5)),'unrestrained out-of-plane DOF'
    for e in es.values():
        a,b=e['nodes'];assert a!=b and a in ns and b in ns;used|={a,b};adj[a].add(b);adj[b].add(a)
        assert e['material'] in mats and e['section'] in secs
        d=[ns[b][k]-ns[a][k] for k in ('x','y','z')];assert sum(x*x for x in d)>0
        ref=m['metadata']['elementReferenceVectors'][e['id']];cross=[d[1]*ref[2]-d[2]*ref[1],d[2]*ref[0]-d[0]*ref[2],d[0]*ref[1]-d[1]*ref[0]];assert sum(x*x for x in cross)>1e-14,'parallel reference axis'
    assert used==set(ns),'unconnected node'
    reached=set();stack=[next(iter(ns))]
    while stack:
        n=stack.pop()
        if n not in reached:reached.add(n);stack.extend(adj[n]-reached)
    assert reached==set(ns),'disconnected topology'
    for mat in mats.values():
        assert mat['E']>0 and mat['G']>0 and -1<mat['nu']<.5 and mat['rho']>=0
        assert abs(mat['G']-mat['E']/(2*(1+mat['nu'])))<1e-6*mat['G'],'inconsistent isotropic constants'
    for sec in secs.values():assert all(sec['properties'][k]>0 for k in ['A','Iy','Iz','J'])
    caseids={c['id'] for c in m['load_cases']}
    for c in m['load_cases']:
        ids=[]
        for l in c['loads']:
            assert l['reference_frame']=='global';ids.append(l['id'])
            if l['type']=='nodal':assert l['node'] in ns
            else:
                e=es[l['element']];a,b=(ns[x] for x in e['nodes']);L=math.dist([a[k] for k in ['x','y','z']],[b[k] for k in ['x','y','z']]);assert e['type']!='truss'
                if l['type']=='point':assert 0<=l['position']<=L+1e-10
                if l['type']=='distributed':assert 0<=l.get('start',0)<l.get('end',L)<=L+1e-10
        assert len(ids)==len(set(ids))
    for c in m['load_combinations']:assert set(c['factors'])<=caseids
    assert all(m['analysis_control'][k] is False for k in ['self_weight','rigid_floor','p_delta','rigid_offsets','construction_stage'])
    r=stiffness_rank(m);assert r is None or r[0]==r[1],f'structural mechanism rank {r}'
    return r

def check_source_and_outputs(c,r,coverage,task,sm):
    """Check source fidelity and which answers are actually due in each turn."""
    assert c['sourcePlan']==coverage['sourceRequirements'],'sourcePlan must be the exact flat sourceRequirements'
    metadata=c['sourceMetadata']
    assert metadata['requirements']==coverage['requirements'],'original requirement IDs/ranges/semantics changed'
    assert metadata['task']==task and metadata['model']==sm,'original task/model metadata changed'
    assert c['family']==coverage['family'] and c['language']==coverage['language'] and c['plannedEngine']==coverage['plannedEngine']
    assert len(c['turns'])==task['turns']
    assert sorted(x for a in c['requirementCoverage'] for x in a['requirementIds'])==sorted(a['id'] for a in coverage['requirements'])
    source_fields={a['id']:a['sourceField'] for a in coverage['requirements']}
    for row in c['requirementCoverage']:
        assert row['requirementIds'] and all(source_fields[i]==row['sourceField'] for i in row['requirementIds']),'coverage requirement/sourceField mismatch'
    turns={t['id']:t for t in c['turns']}
    assert list(turns)==[f't{i}' for i in range(1,len(c['turns'])+1)],'duplicate or nonsequential turn IDs'
    for t in turns.values():
        if 'clarificationBlocksAnalysis' in t:
            assert type(t['clarificationBlocksAnalysis']) is bool,'clarificationBlocksAnalysis must be boolean'
        if t.get('clarificationBlocksAnalysis') is False:
            assert t['expectation'] in ['analyze','query'] and t['state'] is not None,'nonblocking clarification requires a calculable turn'
            assert t['unresolvedFields'] and t['expectedQuestions'],'nonblocking clarification must retain its pending question'
            assert all(f.startswith('/requestedOutputs/') for f in t['unresolvedFields']),'missing physical input cannot be declared nonblocking'
        elif t['expectation'] in ['analyze','query']:
            assert not t['unresolvedFields'] and not t['expectedQuestions'],'analysis with a pending question requires explicit nonblocking output clarification'
        if t['expectation']=='clarify' and t['state'] is not None:
            assert t['unresolvedFields'] and all(f.startswith('/requestedOutputs/') for f in t['unresolvedFields']),'essential missing physical input requires null state'
    request_states={rr['state']:rr for rr in r['states']}
    assert len(request_states)==len(r['states'])==len(c['modelStates']),'duplicate or missing request state'
    assert set(request_states)==set(range(1,len(c['modelStates'])+1)),'request state numbering differs from models'
    by_state={}
    for state,rr in request_states.items():
        assert rr['model']==c['modelStates'][state-1],'request model/state mismatch'
        quantities={q['id']:q for q in rr['quantities']};derived={d['id']:d for d in rr['derived']}
        assert len(quantities)==len(rr['quantities']) and len(derived)==len(rr['derived']) and not quantities.keys()&derived.keys(),'duplicate quantity/derived ID'
        for d in derived.values():
            assert d['operation'] in ['difference','sum','max','min','max_abs'] and d['operands'],'invalid derived operation/operands'
            assert set(d['operands'])<=quantities.keys()|derived.keys(),'unknown derived operand'
        by_state[state]=(quantities,derived)
    output_ids=set();needed={state:set() for state in request_states}
    for out in c['requiredOutputs']:
        assert out['id'] not in output_ids,'duplicate output ID';output_ids.add(out['id'])
        tids=out.get('turnIds')
        assert isinstance(tids,list) and tids and len(tids)==len(set(tids)),'output needs explicit unique turnIds'
        assert all(tid in turns and turns[tid]['state']==out['state'] for tid in tids),'output turnIds/state mismatch'
        assert out['kind'] in ['numerical','derived','figure','interaction'],'invalid output kind'
        if out['kind']=='interaction':assert not out['quantityIds'],'interaction cannot replace a quantity output'
        if out['kind'] in ['numerical','derived']:
            assert out['quantityIds'] and out['state'] in by_state,'numerical/derived output needs state and quantities'
            assert all(turns[tid]['expectation']!='clarify' for tid in tids),'numerical/derived output is due during clarification'
        quantities,derived=by_state.get(out['state'],({},{}))
        for qid in out['quantityIds']:
            assert qid in quantities or qid in derived,'output refers to an unknown quantity'
            if out['kind']=='numerical':assert qid in quantities,'numerical output refers to a derived quantity'
            if out['kind']=='derived':assert qid in derived,'derived output refers to a primitive quantity'
            needed[out['state']].add(qid)
    for state,(quantities,derived) in by_state.items():
        reached=set();visiting=set()
        def visit(qid):
            assert qid not in visiting,'cyclic derived request'
            if qid in reached:return
            visiting.add(qid)
            if qid in derived:
                for operand in derived[qid]['operands']:visit(operand)
            visiting.remove(qid);reached.add(qid)
        for qid in needed[state]:visit(qid)
        assert quantities.keys()|derived.keys()<=reached,'reference request is neither a reported quantity nor a required derived operand'
    def report_ids(turn_id,kind):
        return {qid for out in c['requiredOutputs'] if out['kind']==kind and turn_id in out['turnIds'] for qid in out['quantityIds']}
    if c['id']=='INT-003':
        assert report_ids('t1','numerical')=={'D-x3p25-uz','D-x6p5-uz'},'INT003 initial query positions changed'
        assert report_ids('t2','numerical')=={'D-x2p5-uz','D-x6p5-uz'},'INT003 replacement query includes obsolete/future positions'
    if c['id']=='INT-033':
        assert [(t['expectation'],t['state']) for t in c['turns']]==[('analyze',1),('query',1)],'INT033 must analyze known outputs then query the unchanged physical state'
        assert c['turns'][0].get('clarificationBlocksAnalysis') is False,'INT033 extra-output scope must not block known-output analysis'
        assert c['turns'][0]['unresolvedFields']==['/requestedOutputs/maximumAxialForce/scope'],'INT033 unresolved field is not report scope'
        assert 'clarificationBlocksAnalysis' not in c['turns'][1] and not c['turns'][1]['unresolvedFields'] and not c['turns'][1]['expectedQuestions'],'INT033 second-turn scope must be resolved'
        baseline={'case:D:node:T2:ux','case:D:node:T2:uz','case:D:node:B0:Fx','case:D:node:B0:Fz','case:D:member:BC0:0:right:N'}
        assert all(report_ids(tid,'numerical')==baseline for tid in ['t1','t2']),'INT033 should report five known quantities in both turns, not all envelope operands'
        envelope='case:D:all-members:max-abs-N'
        assert not report_ids('t1','derived'),'INT033 maximum scope is unresolved in the first turn'
        assert report_ids('t2','derived')=={envelope},'INT033 governing maximum is missing'
        quantities,derived=by_state[1]
        member_ids={qid for qid,q in quantities.items() if q['location']['kind']=='member' and q['component']=='N'}
        assert len(member_ids)==21 and derived[envelope]['operation']=='max_abs','INT033 must compare all 21 axial forces'
        assert len(derived[envelope]['operands'])==21 and set(derived[envelope]['operands'])==member_ids,'INT033 maximum omits or duplicates a member operand'
        assert derived[envelope].get('tiePolicy')=='any','INT033 must accept any physically tied governing member'
        expected_members=[member for i in range(5) for member in (f'BC{i}',f'TC{i}')]+[f'V{i}' for i in range(6)]+[f'DG{i}' for i in range(5)]
        assert derived[envelope]['operands']==[f'case:D:member:{member}:0:right:N' for member in expected_members],'INT033 frozen operand order changed'
        public_texts=[c['turns'][1]['instruction'],derived[envelope]['description']]
        public_texts += [out['description'] for out in c['requiredOutputs'] if out['kind']=='derived']
        for text in public_texts:
            assert '并列' in text and '任意一根' in text,'INT033 public T2 must permit any tied governing member'
            assert all(term in text for term in ['控制杆ID','带符号轴力','拉/压','单位','工况D']),'INT033 tied governor must retain its signed force, tension/compression, unit and case'
            assert not any(qid in text for qid in member_ids),'INT033 public instructions expose private operand IDs'


def check_case(cid):
    p=ROOT/'corpora/research-300/cases'/cid;c=json.loads((p/'contract.json').read_text());r=json.loads((p/'reference-requests.json').read_text());coverage,task,sm=sources(cid)
    check_source_and_outputs(c,r,coverage,task,sm)
    assert c['status']=='authored-candidate' and c['sameEngineTruthStatus']=='pending' and c['inputBlindReview']=='pending' and c['llmEndToEnd']=='not-run'
    public=set(c['attachments']);assert public.isdisjoint(c['modelStates'])
    for name in public:assert (p/name).is_file() and '..' not in name and not name.startswith('/')
    seen=set()
    for t in c['turns']:
        assert t['expectation'] in ['analyze','clarify','query']
        assert set(t['attachments'])<=public and not set(t['attachments'])&seen;seen.update(t['attachments'])
        if t['expectation']=='clarify':
            assert t['unresolvedFields'] and t['expectedQuestions']
            assert t['state'] is None or 1<=t['state']<=len(c['modelStates'])
        else:assert 1<=t['state']<=len(c['modelStates'])
    assert seen==public
    results=[]
    for rr in r['states']:
        m=json.loads((p/rr['model']).read_text());results.append(check_model(m));ns={x['id']:x for x in m['nodes']};es={x['id']:x for x in m['elements']};ids=set()
        for q in rr['quantities']:
            assert 'value' not in q and q['id'] not in ids;ids.add(q['id'])
            assert q['selection']['id'] in [x['id'] for x in m['load_cases' if q['selection']['kind']=='case' else 'load_combinations']]
            loc=q['location'];assert loc['kind'] in ['node','member']
            if loc['kind']=='node':assert loc['id'] in ns
            else:
                e=es[loc['id']];a,b=(ns[x] for x in e['nodes']);L=math.dist([a[k] for k in ['x','y','z']],[b[k] for k in ['x','y','z']]);assert 0<=loc['positionM']<=L+1e-10 and loc['side'] in ['left','right']
        if cid=='INT-033':assert {q['location']['id'] for q in rr['quantities'] if q['location']['kind']=='member'}==set(es),'INT033 envelope must span the actual model members'
    if c['locale']=='en':
        import re
        for text in [(p/'prompt.txt').read_text()]+[t['instruction'] for t in c['turns']]+[(p/f).read_text() for f in public]:assert not re.search('[\u3400-\u9fff]',text),'Chinese visible text in English case'
    return dict(id=cid,states=len(r['states']),rankChecks=results,quantities=sum(len(x['quantities']) for x in r['states']))

def mutation_smoke():
    from int_a_common import model,node,elem,load,finalize,FIXED,FREE
    m=model();node(m,'a',0,0,restraint=FIXED);node(m,'b',1,0,restraint=FREE);elem(m,'e','a','b');load(m,type='nodal',node='b',fz=-1);m=finalize(m);check_model(m)
    from copy import deepcopy
    bad=deepcopy(m);bad['nodes'][0]['restraints']=FREE[:]
    try:check_model(bad)
    except AssertionError:pass
    else:raise AssertionError('mechanism mutation escaped')
    bad=deepcopy(m);bad['nodes'].append(dict(id='ghost',x=.5,y=0,z=0,restraints=FREE))
    try:check_model(bad)
    except AssertionError:pass
    else:raise AssertionError('unconnected observation node escaped')
    bad=deepcopy(m);bad['metadata']['elementReferenceVectors']['e']=[1,0,0]
    try:check_model(bad)
    except AssertionError:pass
    else:raise AssertionError('parallel axis mutation escaped')
    return 3+contract_mutation_smoke()


def contract_mutation_smoke():
    """Reject regressions which a structurally valid model would not reveal."""
    from copy import deepcopy
    def fixture(cid):
        p=ROOT/'corpora/research-300/cases'/cid
        return (json.loads((p/'contract.json').read_text()),json.loads((p/'reference-requests.json').read_text()),*sources(cid))
    def reject(data,mutate,label):
        bad=deepcopy(data);mutate(bad[0],bad[1])
        try:check_source_and_outputs(*bad)
        except AssertionError:return
        raise AssertionError(label+' mutation escaped')
    beam=fixture('INT-003');truss=fixture('INT-033')
    check_source_and_outputs(*beam);check_source_and_outputs(*truss)
    reject(beam,lambda c,r:c['requiredOutputs'][0].pop('turnIds'),'missing output turn binding')
    reject(beam,lambda c,r:c['requirementCoverage'][0].update(sourceField='model.loadKey'),'wrong source-field mapping')
    reject(beam,lambda c,r:c['sourceMetadata']['requirements'][0].update(sourceRange=[0,1]),'altered original requirement range')
    def obsolete_position(c,r):
        out=next(o for o in c['requiredOutputs'] if 'D-x3p25-uz' in o['quantityIds'])
        out['turnIds']=['t1','t2']
    reject(beam,obsolete_position,'obsolete INT003 query position')
    def premature_answer(c,r):
        out=next(o for o in c['requiredOutputs'] if o['kind']=='derived')
        out['turnIds']=['t1','t2']
    reject(truss,premature_answer,'maximum-force report before scope clarification')
    reject(truss,lambda c,r:c['turns'][0].update(unresolvedFields=['/load_cases/0/loads/0/fz']),'physical input falsely declared nonblocking')
    reject(truss,lambda c,r:r['states'][0]['derived'][0]['operands'].pop(),'missing maximum-force operand')
    reject(truss,lambda c,r:r['states'][0]['derived'][0].pop('tiePolicy'),'implicit first governing member')
    reject(truss,lambda c,r:r['states'][0]['derived'][0].update(tiePolicy='first'),'first-only governing member')
    reject(truss,lambda c,r:r['states'][0]['derived'][0]['operands'].reverse(),'changed frozen operand order')
    reject(truss,lambda c,r:c['turns'][1].update(instruction=c['turns'][1]['instruction'].replace('任意一根','第一根')),'public first-only tie rule')
    reject(truss,lambda c,r:r['states'][0]['derived'][0].update(description=r['states'][0]['derived'][0]['description'].replace('带符号轴力','轴力绝对值')),'unsigned tied force')
    reject(truss,lambda c,r:c['turns'][1].update(instruction=c['turns'][1]['instruction'].replace('工况D','')),'missing tied force case')
    def mandatory_private_operand(c,r):
        out=deepcopy(next(o for o in c['requiredOutputs'] if o['kind']=='numerical'))
        out.update(id='unexpected-member-output',quantityIds=['case:D:member:TC0:0:right:N'])
        c['requiredOutputs'].append(out)
    reject(truss,mandatory_private_operand,'private operand becomes mandatory report')
    return 14


def check_distinct_initial():
    """Reject copies masked only by node/member IDs or section names."""
    seen={}
    for i in range(1,51):
        m=json.loads((ROOT/f'corpora/research-300/cases/INT-{i:03}/model-state-1.json').read_text())
        ns={n['id']:[n[k] for k in ('x','y','z')] for n in m['nodes']}
        secs={s['id']:s['properties'] for s in m['sections']}
        mats={v['id']:{k:v[k] for k in ('E','G','nu','rho')} for v in m['materials']}
        es={e['id']:[e['type'],[ns[n] for n in e['nodes']],secs[e['section']],mats[e['material']]] for e in m['elements']}
        sig={'nodes':sorted([[ns[n['id']],n['restraints']] for n in m['nodes']]),'elements':sorted(es.values(),key=str),'loads':[],'combos':m['load_combinations']}
        for c in m['load_cases']:
            loads=[]
            for l in c['loads']:
                r={k:v for k,v in l.items() if k not in ('id','node','element')}
                if 'node' in l:r['position']=ns[l['node']]
                if 'element' in l:r['member']=es[l['element']]
                loads.append(r)
            sig['loads'].append([c['id'],sorted(loads,key=str)])
        h=hashlib.sha256(json.dumps(sig,sort_keys=True).encode()).hexdigest()
        assert h not in seen,('duplicate physical model',i,seen.get(h))
        seen[h]=i
    return len(seen)

if __name__=='__main__':
    nums=list(map(int,sys.argv[1:])) or list(range(1,51));results=[]
    for n in nums:
        cid=f'INT-{n:03}'
        try:results.append(check_case(cid))
        except Exception as e:raise RuntimeError(f'{cid}: {e}') from e
    print(json.dumps(dict(cases=len(results),states=sum(x['states'] for x in results),quantities=sum(x['quantities'] for x in results),rejectedMutations=mutation_smoke(),results=results),indent=2))
