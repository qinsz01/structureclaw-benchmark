"""Twenty-seven coupled designs, with independently fixed multi-constraint truth."""
from copy import deepcopy
import math

from .mechanics import *

def metrics(truth):
    def winner(rows,key):
        row=max(rows,key=lambda r:abs(r[key]['value']));return {**row[key],'selection':row['selection']}
    return {'upperVertical':winner(truth['upperMetrics'],'uz'),
            'primaryVertical':winner(truth['primaryMetrics'],'uz'),
            'primaryLateral':winner(truth['primaryMetrics'],'lateral'),
            'primaryEndAction':winner(truth['primaryMetrics'],'force')}

def numbers(truth):return [abs(row['value']) for row in metrics(truth).values()]

def quality(truths,limits):
    feasible=[i for i,t in enumerate(truths) if all(v<=l for v,l in zip(numbers(t),limits))]
    if not feasible:return {'feasible':[],'optimal':[],'essentialConstraints':[],'essentialConstraintFamilies':[]}
    best=min(truths[i]['volume'] for i in feasible)
    optimal=[i for i in feasible if math.isclose(truths[i]['volume'],best,rel_tol=1e-9,abs_tol=1e-10)]
    essential=[]
    for removed in range(4):
        relaxed=[i for i,t in enumerate(truths) if all(j==removed or v<=l for j,(v,l) in enumerate(zip(numbers(t),limits)))]
        if min(truths[i]['volume'] for i in relaxed)<best*(1-1e-8):essential.append(removed)
    families=[]
    # Correlated primary drift bounds may be redundant one at a time. Remove
    # the complete engineering constraint family to test its independent role.
    for name,removed in [('upper-serviceability',[0]),('primary-serviceability',[1,2]),('primary-end-action',[3])]:
        relaxed=[i for i,t in enumerate(truths) if all(j in removed or v<=l for j,(v,l) in enumerate(zip(numbers(t),limits)))]
        if min(truths[i]['volume'] for i in relaxed)<best*(1-1e-8):families.append(name)
    return {'feasible':feasible,'optimal':optimal,'essentialConstraints':essential,'essentialConstraintFamilies':families}

def choose_limits(truths,seed,infeasible=False):
    if infeasible:
        mins=[min(numbers(t)[i] for t in truths) for i in range(4)]
        limits=[float(f'{v*f:.4g}') for v,f in zip(mins,[.82,1.30,1.30,1.30])]
        return limits,quality(truths,limits)
    scored=[];target_feasible=3+seed%8
    preferred=['A-B-B','B-A-C','A-C-B','C-A-B','B-C-C','C-B-B','A-B-C','B-A-B'][seed%8].split('-')
    for offset in range(27):
        index=(seed*7+offset)%27;t=truths[index]
        if len(set(t['choice'].values()))<2:continue
        for margin in [1.025,1.06,1.12]:
            limits=[float(f'{max(v*margin,1e-10):.4g}') for v in numbers(t)]
            q=quality(truths,limits)
            if not q['optimal']:continue
            mixtures=sum(len(set(truths[i]['choice'].values()))>=2 for i in q['optimal'])
            if not mixtures:continue
            if len(q['essentialConstraintFamilies'])<2:continue
            distance=min(sum(truths[i]['choice'][g]!=v for g,v in zip(['G0','G1','G2'],preferred)) for i in q['optimal'])
            scored.append(((-distance,-abs(len(q['feasible'])-target_feasible),len(q['essentialConstraintFamilies']),len(q['essentialConstraints']),-offset),limits,q))
    if not scored:raise ValueError('No substantive mixed engineering design trade-off')
    _,limits,q=max(scored,key=lambda row:row[0])
    if len(q['essentialConstraintFamilies'])<2:raise ValueError('At least two engineering constraint families must independently affect the optimum')
    return limits,q

def reference(primary,seed,infeasible=False,load_rules=None,fixed_constraints=None,integration='one-way'):
    p=prepare_primary(primary)
    if p is None:raise ValueError('A project requires an eligible primary structure')
    if integration=='rigid' and not rigid_eligible(primary):raise ValueError('Unqualified spatial rotational connection')
    u,interface=secondary(p,seed,cambered=integration=='rigid');rules=deepcopy(load_rules) if load_rules else rules_for(p,seed)
    truths=[(rigid_project if integration=='rigid' else project)(p,u,interface,rules,choice) for choice in DESIGNS]
    assert all(all(math.isfinite(v) and v>1e-12 for v in numbers(t)) for t in truths)
    if fixed_constraints:
        limits=[c['absoluteLimit'] for c in fixed_constraints];q=quality(truths,limits)
    else:limits,q=choose_limits(truths,seed,infeasible)
    ids=lambda t:'-'.join(t['choice'][g] for g in ['G0','G1','G2'])
    for t in truths:
        t['id']=ids(t);t['metrics']=metrics(t)
        t['utilizations']={name:abs(row['value'])/limit for (name,row),limit in zip(t['metrics'].items(),limits)}
        t['feasible']=max(t['utilizations'].values())<=1.
    best_util=min(max(t['utilizations'].values()) for t in truths)
    witnesses=[t['id'] for t in truths if math.isclose(max(t['utilizations'].values()),best_util,rel_tol=1e-9)]
    constraints=[{'id':name,'absoluteLimit':limit,'unit':truths[0]['metrics'][name]['unit'],'scope':scope}
                 for name,limit,scope in zip(truths[0]['metrics'],limits,
                  ['All secondary analysis joints, all issued combinations; signed max-abs uz',
                   'All primary analysis joints, all issued combinations; signed max-abs uz',
                   'All primary analysis joints, all issued combinations; max sqrt(ux^2+uy^2)',
                   'All beam/column end cuts and M2/M3 components, or all axial bars when no beam/column exists; signed max-abs'])]
    base=truths[0];changing=[t for t in truths if t['choice']['G2']==base['choice']['G2']]
    key='uz' if integration=='rigid' else 'fz'
    base_forces=[v[key] for block in base['transfer'] for v in block['values']]
    change=max(max(abs(a-b) for a,b in zip(base_forces,[v[key] for block in t['transfer'] for v in block['values']])) for t in changing)
    scale=max(max(map(abs,base_forces)),1e-9)
    assert change/scale>.01,'Secondary design must materially affect the connected primary structure'
    ref={'kind':'project','engine':'OpenSees','integration':integration,'primaryTemplate':p,'upperTemplate':u,'interface':interface,
            'loadRules':rules,'catalog':deepcopy(CATALOG),'designGroups':[
              {'id':'G0','model':'upper','sectionFamilies':['OUTER'],'meaning':'Outer spans of the distribution beam'},
              {'id':'G1','model':'upper','sectionFamilies':['MIDDLE'],'meaning':'Middle span of the distribution beam'},
              {'id':'G2','model':'primary','sectionFamilies':[s['id'] for s in p['sections']],'meaning':'All issued primary section families, preserving their separate nominal dimensions'}],
            'constraints':constraints,'truths':truths,'optimalDesigns':[truths[i]['id'] for i in q['optimal']],
            'leastViolationDesigns':witnesses,'minimumWorstUtilization':best_util,
            'requirements':{'upperSelections':[{'kind':'case','id':c} for c in ['D','Q','W']],
                            'primarySelections':deepcopy(SELECTIONS),'completeEnumerationRequired':False,
                            'gravityRecalculationRequired':True,'oneWayTransfer':integration=='one-way'},
            'difficultyEvidence':{'independentDesignGroups':3,'catalogCombinations':27,'structuralModels':2,
              'constraints':4,'essentialConstraints':q['essentialConstraints'],'essentialConstraintFamilies':q['essentialConstraintFamilies'],'reactionDesignCouplingRelative':change/scale,
              'noFeasibleDesign':not q['feasible'],'nonUniformOptimalDesign':any(len(set(truths[i]['choice'].values()))>=2 for i in q['optimal'])},
            'tolerance':{'displacementAbsolute':1e-8,'forceAbsolute':1e-6,'relative':1e-6}}
    if integration=='rigid':
        ref['combinedTemplate'],ref['combinedMapping']=combine_rigid(p,u,interface)
        ref['requirements'].update(upperSelections=[],primarySelections=[],combinedSelections=deepcopy(SELECTIONS),coupling='Shared translations and rotations at the four issued rigid connection joints; no extra restraints.')
    return ref
